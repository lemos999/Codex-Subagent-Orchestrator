"""Auto-training loop v2: walk-forward evaluation -> retrain -> repeat.

Implements the 3-engine discussion consensus (2026-03-26):
  - Walk-forward 3 sets (train 60d / val 20d / holdout 20d)
  - Dual gate: internal 55%/+5%, external 60%/+8%
  - Max 3 retrain attempts per cycle, early stop on 2 consecutive <1% improvement
  - Reward auto-adjust: after 2 failures, 1 auto-adjust within pre-defined grid
  - JSON state persistence for restart capability
  - Phase A: common base model (single coin)

Usage:
    cd "Projects/Trading Value"
    PYTHONPATH=src py -3 scripts/auto_train.py
    PYTHONPATH=src py -3 scripts/auto_train.py --model C --max-cycles 5
    PYTHONPATH=src py -3 scripts/auto_train.py --resume   # resume from saved state
"""
from __future__ import annotations
import sys, json, time, random, argparse, shutil, threading, http.server
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, field
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import sqlite3

# Heavy imports deferred to first use
np = None

def _ensure_numpy():
    global np
    if np is None:
        print("  Loading numpy...", flush=True)
        import numpy as _np
        np = _np
        print("  numpy loaded.", flush=True)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "sim_1m.sqlite"
RESULTS_DIR = DATA_DIR / "auto_train_results"
STATE_FILE = DATA_DIR / "auto_train_loop_state.json"

# -- Dual Gate Targets ----------------------------------------
# Internal gate (loop pass): easier threshold
GATE_INTERNAL_WR = 55.0       # %
GATE_INTERNAL_RET = 5.0       # %
# External gate (deploy approval): final target
GATE_EXTERNAL_WR = 60.0       # %
GATE_EXTERNAL_RET = 8.0       # %

# -- Loop Parameters ------------------------------------------
MAX_RETRAIN_PER_CYCLE = 3     # max retrain attempts per walk-forward set
STALE_THRESHOLD = 1.0         # improvement < 1% -> stale
MAX_CYCLES = 10               # max walk-forward cycles
TRAIN_STEPS = 200_000         # steps per retrain round
EVAL_DAYS_VAL = 20            # validation window (days)
EVAL_DAYS_HOLDOUT = 20        # holdout window (days)
TRAIN_DAYS = 60               # training window (days)
DEPLOY_CONSECUTIVE = 2        # consecutive holdout passes for deploy candidate

# -- Reward Config & Grid -------------------------------------
DEFAULT_REWARD = {
    "position_change_penalty": 0.30,
    "holding_cost": 0.002,
    "profitable_hold_bonus_max": 0.02,
    "profitable_close_bonus": 0.2,
    "drawdown_penalty_factor": 0.15,
}

# Pre-defined grid for auto-adjustment (+/-range from current value)
REWARD_GRID = {
    "position_change_penalty": {"min": 0.05, "max": 0.60, "step": 0.05},
    "holding_cost":            {"min": 0.001, "max": 0.005, "step": 0.001},
    "profitable_hold_bonus_max": {"min": 0.01, "max": 0.08, "step": 0.01},
    "profitable_close_bonus":  {"min": 0.1, "max": 0.5, "step": 0.05},
    "drawdown_penalty_factor": {"min": 0.05, "max": 0.40, "step": 0.05},
}


@dataclass
class EvalResult:
    period: str
    balance: float
    pnl: float
    return_pct: float
    trades: int
    wins: int
    losses: int
    win_rate: float
    max_dd: float
    passed_internal: bool
    passed_external: bool


@dataclass
class WalkForwardSet:
    """One walk-forward window: train / val / holdout."""
    train_start: str
    train_end: str
    val_start: str
    val_end: str
    holdout_start: str
    holdout_end: str


# -- Data Utilities -------------------------------------------

def get_data_range(symbol: str = "ETHUSDT") -> tuple[str, str]:
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT MIN(datetime), MAX(datetime) FROM ohlcv_1m WHERE symbol=?",
        (symbol,),
    ).fetchone()
    conn.close()
    return row[0], row[1]


def build_walk_forward_sets(data_start: str, data_end: str,
                            n_sets: int = 3) -> list[WalkForwardSet]:
    """Build N walk-forward sets (train 60d / val 20d / holdout 20d = 100d each)."""
    start = datetime.strptime(data_start[:10], "%Y-%m-%d")
    end = datetime.strptime(data_end[:10], "%Y-%m-%d")
    total_days = (end - start).days
    window = TRAIN_DAYS + EVAL_DAYS_VAL + EVAL_DAYS_HOLDOUT  # 100 days

    if total_days < window:
        raise ValueError(f"Not enough data: {total_days} days < {window} required")

    # Space sets evenly across available data, leaving room for all sets
    usable = total_days - window
    if n_sets > 1:
        stride = usable // (n_sets - 1) if usable > 0 else 0
    else:
        stride = 0

    sets = []
    for i in range(n_sets):
        offset = min(i * stride, usable)
        t_start = start + timedelta(days=offset)
        t_end = t_start + timedelta(days=TRAIN_DAYS)
        v_start = t_end
        v_end = v_start + timedelta(days=EVAL_DAYS_VAL)
        h_start = v_end
        h_end = h_start + timedelta(days=EVAL_DAYS_HOLDOUT)

        sets.append(WalkForwardSet(
            train_start=t_start.strftime("%Y-%m-%d"),
            train_end=t_end.strftime("%Y-%m-%d"),
            val_start=v_start.strftime("%Y-%m-%d"),
            val_end=v_end.strftime("%Y-%m-%d"),
            holdout_start=h_start.strftime("%Y-%m-%d"),
            holdout_end=h_end.strftime("%Y-%m-%d"),
        ))

    return sets


# -- Evaluation -----------------------------------------------

def evaluate_model(model_path: str, eval_start: str, eval_end: str,
                   symbol: str = "ETHUSDT") -> EvalResult:
    """Run instant simulation for a single model on a period."""
    _ensure_numpy()
    print("    Loading sim modules...", flush=True)
    from trading_value.adapters.sim_exchange import SimClock, MockExchange
    print("    Loading PaperTrader (torch)...", flush=True)
    from trading_value.adapters.paper import PaperTrader
    print("    Modules loaded.", flush=True)

    clock = SimClock(
        start=eval_start + " 00:00:00",
        end=eval_end + " 00:00:00",
    )
    exchange = MockExchange(clock, db_path=str(DB_PATH))

    state_file = str(DATA_DIR / "auto_train_eval_state.json")
    log_file = str(DATA_DIR / "auto_train_eval_log.jsonl")
    Path(state_file).unlink(missing_ok=True)
    Path(log_file).unlink(missing_ok=True)

    sym_ccxt = symbol.replace("USDT", "/USDT:USDT")
    trader = PaperTrader(
        model_path=model_path, symbol=sym_ccxt,
        leverage=10, risk_pct=0.0035, commission_rate=0.0004,
        state_file=state_file, log_file=log_file,
        time_func=clock.now,
        enable_pullback_entry=False,
    )
    trader.exchange = exchange

    while clock.tick():
        if clock.is_15m_boundary():
            try:
                trader.run_once()
            except Exception:
                pass
        try:
            trader.fast_check()
        except Exception:
            pass

    s = trader.state
    pnl = s.balance - 10000
    return_pct = pnl / 10000 * 100
    wr = (s.wins / s.total_trades * 100) if s.total_trades > 0 else 0

    return EvalResult(
        period=f"{eval_start}~{eval_end}",
        balance=round(s.balance, 2),
        pnl=round(pnl, 2),
        return_pct=round(return_pct, 2),
        trades=s.total_trades,
        wins=s.wins, losses=s.losses,
        win_rate=round(wr, 1),
        max_dd=round(s.max_drawdown * 100, 2),
        passed_internal=wr >= GATE_INTERNAL_WR and return_pct >= GATE_INTERNAL_RET,
        passed_external=wr >= GATE_EXTERNAL_WR and return_pct >= GATE_EXTERNAL_RET,
    )


# -- Reward Adjustment (within grid) -------------------------

def adjust_rewards_auto(config: dict, result: EvalResult) -> dict:
    """Adjust reward weights within pre-defined grid. Returns new config."""
    new = config.copy()

    def clamp(key, value):
        g = REWARD_GRID[key]
        return max(g["min"], min(g["max"], round(value, 4)))

    if result.trades == 0:
        new["position_change_penalty"] = clamp(
            "position_change_penalty", new["position_change_penalty"] * 0.5)
        print(f"    [auto-adjust] No trades -> penalty {config['position_change_penalty']:.3f} -> {new['position_change_penalty']:.3f}")

    elif result.win_rate < GATE_INTERNAL_WR:
        new["position_change_penalty"] = clamp(
            "position_change_penalty", new["position_change_penalty"] + 0.05)
        print(f"    [auto-adjust] Low WR ({result.win_rate}%) -> penalty +0.05 = {new['position_change_penalty']:.3f}")

    if 0 < result.return_pct < GATE_INTERNAL_RET and result.trades > 0:
        new["profitable_hold_bonus_max"] = clamp(
            "profitable_hold_bonus_max", new["profitable_hold_bonus_max"] + 0.01)
        print(f"    [auto-adjust] Low return ({result.return_pct}%) -> hold bonus +0.01 = {new['profitable_hold_bonus_max']:.3f}")

    if result.max_dd > 15:
        new["drawdown_penalty_factor"] = clamp(
            "drawdown_penalty_factor", new["drawdown_penalty_factor"] + 0.05)
        print(f"    [auto-adjust] High DD ({result.max_dd}%) -> DD penalty +0.05 = {new['drawdown_penalty_factor']:.3f}")

    return new


# -- Retraining -----------------------------------------------

def retrain_model(model_path: str, train_start: str, train_end: str,
                  reward_config: dict, steps: int = TRAIN_STEPS,
                  output_path: str = None) -> str:
    """Retrain RL model with adjusted reward config."""
    _ensure_numpy()
    import pandas as pd
    from sb3_contrib import RecurrentPPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    from trading_value.adapters.rl_env_c import TradingEnvC
    from trading_value.core.models import Timeframe

    if output_path is None:
        output_path = model_path + "_retrained"

    conn = sqlite3.connect(str(DB_PATH))
    df_1m = pd.read_sql_query(
        "SELECT timestamp, datetime, open, high, low, close, volume "
        "FROM ohlcv_1m WHERE symbol='ETHUSDT' AND datetime >= ? AND datetime < ? "
        "ORDER BY timestamp",
        conn, params=(train_start, train_end),
    )
    conn.close()

    if len(df_1m) < 1000:
        print(f"    [retrain] Not enough data: {len(df_1m)} rows")
        return model_path

    df_1m["timestamp"] = pd.to_datetime(df_1m["datetime"], utc=True)

    def resample(df, rule):
        return (df.set_index("timestamp")
                .resample(rule)
                .agg({"open": "first", "high": "max", "low": "min",
                      "close": "last", "volume": "sum"})
                .dropna().reset_index())

    df_15m = resample(df_1m, "15min")
    df_30m = resample(df_1m, "30min")
    df_1h = resample(df_1m, "1h")
    df_4h = resample(df_1m, "4h")

    data = {Timeframe.M15: df_15m, Timeframe.M30: df_30m, Timeframe.H1: df_1h, Timeframe.H4: df_4h}

    if len(df_15m) < 200:
        print(f"    [retrain] Not enough 15m bars: {len(df_15m)}")
        return model_path

    env_kwargs = {
        "data": data, "symbol": "ETHUSDT", "initial_balance": 10000.0,
        "commission_rate": 0.0002, "episode_bars": min(1920, len(df_15m) - 100),
        "random_start": True, "sharpe_window": 96,
        "primary_tf": Timeframe.M15,
        **reward_config,
    }

    def make_env():
        return TradingEnvC(**env_kwargs)

    vec_env = DummyVecEnv([make_env])

    # Try loading existing model; if obs dimension mismatch, create new
    try:
        print(f"    [retrain] Loading {Path(model_path).name}...")
        model = RecurrentPPO.load(model_path, env=vec_env)
    except Exception as e:
        if "observation" in str(e).lower() or "shape" in str(e).lower() or "size" in str(e).lower():
            print(f"    [retrain] Obs dimension mismatch - creating new model from scratch")
            model = RecurrentPPO(
                "MlpLstmPolicy", vec_env,
                learning_rate=3e-4, n_steps=512, batch_size=64,
                n_epochs=10, gamma=0.99, gae_lambda=0.95,
                clip_range=0.2, ent_coef=0.01, verbose=1,
            )
        else:
            raise

    print(f"    [retrain] Training {steps:,} steps...")
    print(f"    [retrain] Reward: {json.dumps({k: round(v, 3) for k, v in reward_config.items()})}")
    try:
        model.learn(total_timesteps=steps, progress_bar=True)
    except ImportError:
        print("    [retrain] progress_bar unavailable, training without it...", flush=True)
        model.learn(total_timesteps=steps, progress_bar=False)

    model.save(output_path)
    print(f"    [retrain] Saved: {output_path}")
    vec_env.close()

    return output_path


# -- State Persistence ----------------------------------------

def save_loop_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))

def load_loop_state() -> Optional[dict]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return None


# -- Main Loop ------------------------------------------------

def training_loop(model_name: str = "C Castle",
                  model_path: str = None,
                  max_cycles: int = MAX_CYCLES,
                  resume_state: dict = None,
                  train_steps: int = TRAIN_STEPS):
    """Main auto-training loop with walk-forward evaluation."""

    if model_path is None:
        model_path = str(DATA_DIR / "rl_model_c_b_1350k")

    RESULTS_DIR.mkdir(exist_ok=True)

    data_start, data_end = get_data_range()
    wf_sets = build_walk_forward_sets(data_start, data_end, n_sets=3)

    print(f"\n{'='*70}")
    print(f"  AUTO-TRAIN v2: {model_name}")
    print(f"  Data: {data_start[:10]} ~ {data_end[:10]}")
    print(f"  Internal gate: WR >= {GATE_INTERNAL_WR}%, Return >= +{GATE_INTERNAL_RET}%")
    print(f"  External gate: WR >= {GATE_EXTERNAL_WR}%, Return >= +{GATE_EXTERNAL_RET}%")
    print(f"  Walk-forward sets: {len(wf_sets)}")
    print(f"  Max retrain per set: {MAX_RETRAIN_PER_CYCLE}")
    print(f"  Max cycles: {max_cycles}")
    print(f"{'='*70}")

    for i, wf in enumerate(wf_sets):
        print(f"  Set {i+1}: train {wf.train_start}~{wf.train_end} | "
              f"val {wf.val_start}~{wf.val_end} | "
              f"holdout {wf.holdout_start}~{wf.holdout_end}")

    # Initialize or resume state
    if resume_state:
        current_model = resume_state["current_model"]
        reward_config = resume_state["reward_config"]
        history = resume_state["history"]
        cycle_start = resume_state.get("cycle", 0)
        holdout_passes = resume_state.get("holdout_passes", 0)
        print(f"\n  Resuming from cycle {cycle_start + 1}, holdout passes: {holdout_passes}")
    else:
        current_model = model_path
        reward_config = DEFAULT_REWARD.copy()
        history = []
        cycle_start = 0
        holdout_passes = 0

    best_score = -999
    total_reward_adjustments = 0

    update_dash = lambda phase, extra=None: dashboard_state.update({
        "model": model_name, "cycle": len(history),
        "max_cycles": max_cycles, "phase": phase,
        "holdout_passes": holdout_passes,
        "gate_internal": {"wr": GATE_INTERNAL_WR, "ret": GATE_INTERNAL_RET},
        "gate_external": {"wr": GATE_EXTERNAL_WR, "ret": GATE_EXTERNAL_RET},
        "reward_config": {k: round(v, 4) for k, v in reward_config.items()},
        "history": history, "status": "running",
        "wf_sets": [asdict(w) for w in wf_sets],
        "extra": extra or {},
    })

    update_dash("init")

    for cycle in range(cycle_start, max_cycles):
        wf = wf_sets[cycle % len(wf_sets)]

        print(f"\n{'-'*70}")
        print(f"  CYCLE {cycle + 1}/{max_cycles} -Walk-Forward Set {(cycle % len(wf_sets)) + 1}")
        print(f"  Train: {wf.train_start} ~ {wf.train_end}")
        print(f"  Val:   {wf.val_start} ~ {wf.val_end}")
        print(f"  Holdout: {wf.holdout_start} ~ {wf.holdout_end}")
        print(f"{'-'*70}")

        # -- Phase 1: Evaluate on validation set ------------------
        print(f"\n  [1/3] Evaluating on validation set...")
        update_dash("evaluating", {"period": f"{wf.val_start}~{wf.val_end}"})

        val_result = evaluate_model(current_model, wf.val_start, wf.val_end)
        val_score = val_result.return_pct + val_result.win_rate

        print(f"  Val Result: WR={val_result.win_rate}% Return={val_result.return_pct:+.1f}% "
              f"Trades={val_result.trades} DD={val_result.max_dd}% "
              f"{'PASS(internal)' if val_result.passed_internal else 'FAIL'}")

        cycle_record = {
            "cycle": cycle + 1,
            "wf_set": (cycle % len(wf_sets)) + 1,
            "val_result": asdict(val_result),
            "retrain_attempts": 0,
            "holdout_result": None,
            "reward_adjusted": False,
        }

        # -- Phase 2: Retrain loop (if validation fails) ----------
        retrain_count = 0
        prev_score = val_score
        consecutive_stale = 0

        while not val_result.passed_internal and retrain_count < MAX_RETRAIN_PER_CYCLE:
            retrain_count += 1
            print(f"\n  [2/3] Retrain attempt {retrain_count}/{MAX_RETRAIN_PER_CYCLE}")

            # Check if we should auto-adjust rewards (after 2 failures)
            if retrain_count == 2 and total_reward_adjustments == 0:
                print(f"  2 consecutive failures -> auto-adjusting rewards (1 allowed)")
                reward_config = adjust_rewards_auto(reward_config, val_result)
                cycle_record["reward_adjusted"] = True
                total_reward_adjustments += 1

            # Retrain
            update_dash("retraining", {
                "attempt": retrain_count,
                "period": f"{wf.train_start}~{wf.train_end}",
            })

            new_model_path = str(
                DATA_DIR / f"rl_model_auto_{model_name[0].lower()}_c{cycle+1}_r{retrain_count}"
            )
            current_model = retrain_model(
                current_model, wf.train_start, wf.train_end,
                reward_config, train_steps, new_model_path,
            )

            # Re-evaluate on validation
            print(f"  Re-evaluating on validation set...")
            update_dash("evaluating", {"period": f"{wf.val_start}~{wf.val_end}"})
            val_result = evaluate_model(current_model, wf.val_start, wf.val_end)
            val_score = val_result.return_pct + val_result.win_rate

            improvement = val_score - prev_score
            print(f"  Val Result: WR={val_result.win_rate}% Return={val_result.return_pct:+.1f}% "
                  f"Trades={val_result.trades} "
                  f"{'PASS(internal)' if val_result.passed_internal else 'FAIL'} "
                  f"(improvement: {improvement:+.1f})")

            # Early stop: 2 consecutive improvements < 1%
            if improvement < STALE_THRESHOLD:
                consecutive_stale += 1
                if consecutive_stale >= 2:
                    print(f"  Early stop: 2 consecutive improvements < {STALE_THRESHOLD}%")
                    break
            else:
                consecutive_stale = 0

            prev_score = val_score

        cycle_record["retrain_attempts"] = retrain_count
        cycle_record["val_result"] = asdict(val_result)

        # -- Phase 3: Holdout evaluation (if validation passed) ---
        if val_result.passed_internal:
            print(f"\n  [3/3] Evaluating on HOLDOUT set (never seen during training)...")
            update_dash("holdout", {"period": f"{wf.holdout_start}~{wf.holdout_end}"})

            holdout_result = evaluate_model(current_model, wf.holdout_start, wf.holdout_end)
            cycle_record["holdout_result"] = asdict(holdout_result)

            print(f"  Holdout Result: WR={holdout_result.win_rate}% "
                  f"Return={holdout_result.return_pct:+.1f}% "
                  f"Trades={holdout_result.trades} DD={holdout_result.max_dd}% "
                  f"Internal={'PASS' if holdout_result.passed_internal else 'FAIL'} "
                  f"External={'PASS' if holdout_result.passed_external else 'FAIL'}")

            if holdout_result.passed_internal:
                holdout_passes += 1
                print(f"  Holdout passes: {holdout_passes}/{DEPLOY_CONSECUTIVE}")

                if holdout_result.passed_external:
                    print(f"  ** External gate PASSED on holdout!")

                if holdout_passes >= DEPLOY_CONSECUTIVE:
                    print(f"\n  *** DEPLOY CANDIDATE! {holdout_passes} consecutive holdout passes ***")
                    prod_path = str(DATA_DIR / f"rl_model_prod_{model_name[0].lower()}")
                    shutil.copy2(current_model + ".zip", prod_path + ".zip")
                    print(f"  Saved: {prod_path}.zip")
                    dashboard_state["status"] = "deploy_candidate"

                    cycle_record["deploy_candidate"] = True
                    history.append(cycle_record)
                    save_loop_state({
                        "model_name": model_name, "current_model": current_model,
                        "reward_config": reward_config, "history": history,
                        "cycle": cycle + 1, "holdout_passes": holdout_passes,
                        "status": "deploy_candidate",
                    })
                    break
            else:
                holdout_passes = 0
                print(f"  Holdout FAIL -> resetting consecutive passes")
        else:
            print(f"\n  [3/3] Skipped holdout (validation not passed)")
            holdout_passes = 0

        history.append(cycle_record)
        update_dash("cycle_done")

        # Save state for resume
        save_loop_state({
            "model_name": model_name, "current_model": current_model,
            "reward_config": reward_config, "history": history,
            "cycle": cycle + 1, "holdout_passes": holdout_passes,
            "status": "running",
        })

        # Reset reward adjustment counter per cycle
        total_reward_adjustments = 0

    # -- Final Summary --------------------------------------------
    results_file = RESULTS_DIR / f"auto_train_{model_name[0].lower()}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    RESULTS_DIR.mkdir(exist_ok=True)
    results_file.write_text(json.dumps({
        "model": model_name,
        "cycles": len(history),
        "holdout_passes": holdout_passes,
        "deploy_candidate": holdout_passes >= DEPLOY_CONSECUTIVE,
        "history": history,
        "final_reward_config": reward_config,
        "walk_forward_sets": [asdict(w) for w in wf_sets],
        "gates": {
            "internal": {"wr": GATE_INTERNAL_WR, "ret": GATE_INTERNAL_RET},
            "external": {"wr": GATE_EXTERNAL_WR, "ret": GATE_EXTERNAL_RET},
        },
    }, indent=2, default=str))
    print(f"\n  Results saved: {results_file}")

    # Summary table
    print(f"\n{'='*70}")
    print(f"  SUMMARY: {model_name}")
    print(f"{'='*70}")
    print(f"  Cycles completed: {len(history)}")

    val_wrs = [h["val_result"]["win_rate"] for h in history]
    val_rets = [h["val_result"]["return_pct"] for h in history]
    print(f"  Best Val WR: {max(val_wrs):.1f}%")
    print(f"  Best Val Return: {max(val_rets):+.1f}%")

    holdout_results = [h["holdout_result"] for h in history if h["holdout_result"]]
    if holdout_results:
        print(f"  Holdout evaluations: {len(holdout_results)}")
        ho_wrs = [h["win_rate"] for h in holdout_results]
        ho_rets = [h["return_pct"] for h in holdout_results]
        print(f"  Best Holdout WR: {max(ho_wrs):.1f}%")
        print(f"  Best Holdout Return: {max(ho_rets):+.1f}%")

    print(f"  Deploy Candidate: {'YES' if holdout_passes >= DEPLOY_CONSECUTIVE else 'NO'}")
    print(f"{'='*70}\n")

    dashboard_state["status"] = dashboard_state.get("status", "completed")


# -- Dashboard ------------------------------------------------

dashboard_state = {"status": "loading", "history": []}

DASH_HTML = r"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<title>Auto-Train v2 Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e0e0;font-family:'Segoe UI',system-ui,monospace;min-height:100vh}
.hdr{background:#141926;padding:14px 24px;border-bottom:1px solid #2a3040;display:flex;justify-content:space-between;align-items:center}
.hdr h1{font-size:16px;color:#ff6b35;letter-spacing:1px}
.badge{padding:3px 10px;border-radius:4px;font-size:11px;font-weight:bold}
.badge-run{background:#ff6b3522;color:#ff6b35}
.badge-pass{background:#00d4aa22;color:#00d4aa}
.badge-fail{background:#ff4d6a22;color:#ff4d6a}
.badge-train{background:#ffd70022;color:#ffd700}
.wrap{padding:16px 24px;max-width:1100px;margin:0 auto}
.section{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:16px;margin-bottom:14px}
.section h2{font-size:13px;color:#888;margin-bottom:10px;text-transform:uppercase;letter-spacing:1px}
.gn{color:#00d4aa}.rd{color:#ff4d6a}.gy{color:#555}.yl{color:#ffd700}
.metrics{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:14px}
.metric{background:#0a0e17;padding:12px;border-radius:6px;border:1px solid #2a3040;text-align:center}
.metric .label{font-size:11px;color:#666;margin-bottom:4px}
.metric .value{font-size:20px;font-weight:bold}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;color:#666;padding:6px 8px;border-bottom:1px solid #2a3040}
td{padding:6px 8px;border-bottom:1px solid #1a2030}
.reward-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;font-size:11px}
.reward-item{background:#0a0e17;padding:6px 8px;border-radius:4px}
.reward-item .name{color:#666}
.reward-item .val{color:#ddd;font-weight:bold}
.gates{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:10px}
.gate{background:#0a0e17;padding:10px 14px;border-radius:6px;border:1px solid #2a3040}
.gate .title{font-size:11px;color:#666;margin-bottom:4px}
.gate .vals{font-size:14px;font-weight:bold}
.progress-bar{height:8px;background:#1a2030;border-radius:4px;margin:6px 0;overflow:hidden}
.progress-bar .fill{height:100%;border-radius:4px;transition:width .5s}
</style></head><body>
<div class="hdr">
  <div style="display:flex;align-items:center;gap:12px">
    <h1>AUTO-TRAIN v2</h1>
    <span class="badge badge-run" id="statusBadge">LOADING</span>
  </div>
  <div style="font-size:12px;color:#666" id="modelName">--</div>
</div>
<div class="wrap">
  <div class="metrics" id="metrics"></div>
  <div class="section">
    <h2>DUAL GATE TARGETS</h2>
    <div class="gates">
      <div class="gate"><div class="title">Internal Gate (loop pass)</div>
        <div class="vals" id="gateInt">WR >= 55% | Return >= +5%</div></div>
      <div class="gate"><div class="title">External Gate (deploy approval)</div>
        <div class="vals" id="gateExt">WR >= 60% | Return >= +8%</div></div>
    </div>
    <div style="display:flex;gap:20px">
      <div style="flex:1"><div style="font-size:11px;color:#666">Last Val WR</div>
        <div class="progress-bar"><div class="fill" id="wrBar" style="width:0%;background:#00d4aa"></div></div>
        <div style="font-size:12px" id="wrText">--</div></div>
      <div style="flex:1"><div style="font-size:11px;color:#666">Last Val Return</div>
        <div class="progress-bar"><div class="fill" id="retBar" style="width:0%;background:#ff9800"></div></div>
        <div style="font-size:12px" id="retText">--</div></div>
    </div>
  </div>
  <div class="section">
    <h2>REWARD CONFIG</h2>
    <div class="reward-grid" id="rewardConfig"></div>
  </div>
  <div class="section">
    <h2>CYCLE HISTORY</h2>
    <table><thead><tr><th>Cycle</th><th>WF Set</th><th>Val WR</th><th>Val Ret</th><th>Trades</th><th>Retrains</th><th>Holdout</th><th>Status</th></tr></thead>
    <tbody id="historyTable"></tbody></table>
  </div>
  <div class="section" id="phaseInfo" style="display:none">
    <h2>CURRENT PHASE</h2>
    <div id="phaseText" style="font-size:13px"></div>
  </div>
</div>
<script>
function fmt(v){return v>=0?'+'+v.toFixed(1):v.toFixed(1)}
async function refresh(){
  try{
    const r=await fetch('/api/status?'+Date.now());
    if(!r.ok)return;
    const d=await r.json();
    const badge=document.getElementById('statusBadge');
    const statusMap={loading:['LOADING','badge-run'],running:['RUNNING','badge-run'],
      evaluating:['EVALUATING','badge-run'],retraining:['RETRAINING','badge-train'],
      holdout:['HOLDOUT','badge-run'],
      deploy_candidate:['DEPLOY CANDIDATE','badge-pass'],
      stopped_stale:['STOPPED','badge-fail'],completed:['COMPLETED','badge-run'],
      cycle_done:['CYCLE DONE','badge-run'],init:['INIT','badge-run']};
    const phase=d.phase||d.status||'loading';
    const sm=statusMap[phase]||statusMap[d.status]||['?','badge-run'];
    badge.textContent=sm[0];badge.className='badge '+sm[1];
    document.getElementById('modelName').textContent=d.model||'--';

    const h=d.history||[];
    const lastH=h.length>0?h[h.length-1]:{};
    const lastVal=lastH.val_result||{};
    const bestWR=h.length>0?Math.max(...h.map(x=>(x.val_result||{}).win_rate||0)):0;
    const bestRet=h.length>0?Math.max(...h.map(x=>(x.val_result||{}).return_pct||0)):0;
    const passes=d.holdout_passes||0;
    document.getElementById('metrics').innerHTML=`
      <div class="metric"><div class="label">Cycle</div><div class="value">${h.length}/${d.max_cycles||10}</div></div>
      <div class="metric"><div class="label">Best Val WR</div><div class="value ${bestWR>=55?'gn':'rd'}">${bestWR.toFixed(0)}%</div></div>
      <div class="metric"><div class="label">Best Val Return</div><div class="value ${bestRet>=5?'gn':'rd'}">${fmt(bestRet)}%</div></div>
      <div class="metric"><div class="label">Holdout Pass</div><div class="value ${passes>=2?'gn':'yl'}">${passes}/2</div></div>
      <div class="metric"><div class="label">Retrains</div><div class="value">${lastH.retrain_attempts||0}</div></div>`;

    const wr=lastVal.win_rate||0;
    document.getElementById('wrBar').style.width=Math.min(100,wr/55*100)+'%';
    document.getElementById('wrBar').style.background=wr>=55?'#00d4aa':'#ff4d6a';
    document.getElementById('wrText').innerHTML=`<span class="${wr>=55?'gn':'rd'}">${wr.toFixed(1)}%</span>`;
    const ret=lastVal.return_pct||0;
    document.getElementById('retBar').style.width=Math.min(100,Math.max(0,ret)/5*100)+'%';
    document.getElementById('retBar').style.background=ret>=5?'#00d4aa':'#ff4d6a';
    document.getElementById('retText').innerHTML=`<span class="${ret>=5?'gn':'rd'}">${fmt(ret)}%</span>`;

    const rc=d.reward_config||{};
    let rcHtml='';
    for(const[k,v]of Object.entries(rc)){
      rcHtml+=`<div class="reward-item"><div class="name">${k}</div><div class="val">${v}</div></div>`;
    }
    document.getElementById('rewardConfig').innerHTML=rcHtml;

    let rows='';
    for(const c of h){
      const vr=c.val_result||{};
      const hr=c.holdout_result;
      const hoText=hr?`WR:${hr.win_rate}% Ret:${fmt(hr.return_pct)}%`:'--';
      const hoCls=hr?(hr.passed_internal?'gn':'rd'):'gy';
      const valCls=vr.passed_internal?'gn':'rd';
      const adj=c.reward_adjusted?'*':'';
      rows+=`<tr>
        <td>#${c.cycle}</td><td>Set ${c.wf_set}</td>
        <td class="${vr.win_rate>=55?'gn':'rd'}">${(vr.win_rate||0).toFixed(0)}%</td>
        <td class="${vr.return_pct>=5?'gn':'rd'}">${fmt(vr.return_pct||0)}%</td>
        <td>${vr.trades||0}</td>
        <td>${c.retrain_attempts}${adj}</td>
        <td class="${hoCls}">${hoText}</td>
        <td class="${valCls}">${vr.passed_internal?'PASS':'FAIL'}</td></tr>`;
    }
    document.getElementById('historyTable').innerHTML=rows||'<tr><td colspan="8" style="color:#555;text-align:center">Waiting for first cycle...</td></tr>';

    const extra=d.extra||{};
    if(['evaluating','retraining','holdout'].includes(phase)){
      document.getElementById('phaseInfo').style.display='block';
      const texts={evaluating:'Evaluating: ',retraining:`Retrain attempt ${extra.attempt||'?'}: `,holdout:'Holdout: '};
      document.getElementById('phaseText').textContent=(texts[phase]||'')+(extra.period||extra.train_period||'...');
    } else {
      document.getElementById('phaseInfo').style.display='none';
    }
  }catch(e){}
}
refresh();setInterval(refresh,2000);
</script></body></html>"""


class DashHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/status"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(dashboard_state, default=str).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASH_HTML.encode())
    def log_message(self, *a): pass


def start_dashboard(port=8891):
    server = http.server.HTTPServer(("0.0.0.0", port), DashHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"  Dashboard: http://localhost:{port}")


def main():
    parser = argparse.ArgumentParser(description="Auto-Training Loop v2")
    parser.add_argument("--model", default="C",
                       help="Model letter (B/C/F/G)")
    parser.add_argument("--max-cycles", type=int, default=MAX_CYCLES)
    parser.add_argument("--steps", type=int, default=TRAIN_STEPS)
    parser.add_argument("--port", type=int, default=8891)
    parser.add_argument("--resume", action="store_true",
                       help="Resume from saved state")
    args = parser.parse_args()

    MODEL_MAP = {
        "B": ("B Berserker", str(DATA_DIR / "rl_model_b_3m")),
        "C": ("C Castle", str(DATA_DIR / "rl_model_c_b_1350k")),
        "F": ("F Fortress", str(DATA_DIR / "rl_model_c_v2_200k_validation")),
        "G": ("G Gladiator", str(DATA_DIR / "rl_model_c_v2_r2_p30")),
    }

    if args.model not in MODEL_MAP:
        print(f"Unknown model: {args.model}. Available: {list(MODEL_MAP.keys())}")
        sys.exit(1)

    _train_steps_override = args.steps

    resume_state = None
    if args.resume:
        resume_state = load_loop_state()
        if resume_state:
            print(f"  Loaded saved state: {STATE_FILE}")
        else:
            print(f"  No saved state found, starting fresh")

    start_dashboard(args.port)

    name, path = MODEL_MAP[args.model]
    training_loop(model_name=name, model_path=path,
                  max_cycles=args.max_cycles, resume_state=resume_state,
                  train_steps=_train_steps_override)


if __name__ == "__main__":
    main()
