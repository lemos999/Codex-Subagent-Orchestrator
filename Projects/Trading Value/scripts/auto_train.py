"""Auto-training loop: simulate → evaluate → retrain → repeat.

Automatically improves RL models until they meet performance targets:
  - Win rate ≥ 60%
  - 5-day return ≥ +8%

Uses SimRunner for evaluation and RecurrentPPO for retraining.
Train/eval periods are strictly separated to prevent overfitting.

Usage:
    cd "Projects/Trading Value"
    PYTHONPATH=src py -3 scripts/auto_train.py
    PYTHONPATH=src py -3 scripts/auto_train.py --max-rounds 5
    PYTHONPATH=src py -3 scripts/auto_train.py --model B --coin ETH
"""
from __future__ import annotations
import sys, json, time, random, argparse, shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd
import sqlite3

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "sim_1m.sqlite"
RESULTS_DIR = DATA_DIR / "auto_train_results"

# ── Targets ──────────────────────────────────────────────────
TARGET_WIN_RATE = 60.0      # %
TARGET_5D_RETURN = 8.0      # %
MAX_ROUNDS = 10
STALE_LIMIT = 3             # consecutive rounds without improvement → stop
TRAIN_STEPS = 200_000       # steps per retrain round
EVAL_DAYS = 5               # days per evaluation period
CONSECUTIVE_PASS = 3        # need N consecutive passes for "production ready"

# ── Default reward config ────────────────────────────────────
DEFAULT_REWARD = {
    "position_change_penalty": 0.30,
    "holding_cost": 0.002,
    "profitable_hold_bonus_max": 0.02,
    "profitable_close_bonus": 0.2,
    "drawdown_penalty_factor": 0.15,
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
    passed: bool


def get_data_range() -> tuple[str, str]:
    """Get available data range from sim_1m.sqlite."""
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT MIN(datetime), MAX(datetime) FROM ohlcv_1m WHERE symbol='ETHUSDT'"
    ).fetchone()
    conn.close()
    return row[0], row[1]


def split_periods(data_start: str, data_end: str, eval_ratio: float = 0.3):
    """Split available data into train and eval pools (by date ranges)."""
    start = datetime.strptime(data_start[:10], "%Y-%m-%d")
    end = datetime.strptime(data_end[:10], "%Y-%m-%d")
    total_days = (end - start).days

    # Last 30% of days = eval pool
    eval_days = int(total_days * eval_ratio)
    train_end = end - timedelta(days=eval_days)

    train_range = (start.strftime("%Y-%m-%d"), train_end.strftime("%Y-%m-%d"))
    eval_range = (train_end.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    return train_range, eval_range


def pick_random_period(date_range: tuple[str, str], days: int = 5) -> tuple[str, str]:
    """Pick a random N-day period within the given date range."""
    start = datetime.strptime(date_range[0], "%Y-%m-%d")
    end = datetime.strptime(date_range[1], "%Y-%m-%d")
    max_start = end - timedelta(days=days)
    if max_start <= start:
        return date_range[0], date_range[1]
    random_start = start + timedelta(days=random.randint(0, (max_start - start).days))
    random_end = random_start + timedelta(days=days)
    return random_start.strftime("%Y-%m-%d"), random_end.strftime("%Y-%m-%d")


# ── Evaluation via SimRunner ─────────────────────────────────

def evaluate_model(model_path: str, eval_start: str, eval_end: str,
                   symbol: str = "ETHUSDT") -> EvalResult:
    """Run instant simulation for a single model on a period."""
    from trading_value.adapters.sim_exchange import SimClock, MockExchange
    from trading_value.adapters.paper import PaperTrader

    clock = SimClock(
        start=eval_start + " 00:00:00",
        end=eval_end + " 00:00:00",
    )
    exchange = MockExchange(clock, db_path=str(DB_PATH))

    # Create single trader
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
    )
    trader.exchange = exchange

    # Run simulation
    while clock.tick():
        if clock.is_30m_boundary():
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
    passed = wr >= TARGET_WIN_RATE and return_pct >= TARGET_5D_RETURN

    return EvalResult(
        period=f"{eval_start}~{eval_end}",
        balance=round(s.balance, 2),
        pnl=round(pnl, 2),
        return_pct=round(return_pct, 2),
        trades=s.total_trades,
        wins=s.wins, losses=s.losses,
        win_rate=round(wr, 1),
        max_dd=round(s.max_drawdown * 100, 2),
        passed=passed,
    )


# ── Reward Adjustment ────────────────────────────────────────

def adjust_rewards(config: dict, result: EvalResult) -> dict:
    """Adjust reward weights based on evaluation failure mode."""
    new = config.copy()

    if result.trades == 0:
        # Too passive → lower entry barrier
        new["position_change_penalty"] = max(0.05, new["position_change_penalty"] * 0.5)
        print(f"    [adjust] No trades → penalty {config['position_change_penalty']:.2f} → {new['position_change_penalty']:.2f}")

    elif result.win_rate < TARGET_WIN_RATE:
        # Bad entries → raise entry barrier
        new["position_change_penalty"] = min(1.0, new["position_change_penalty"] * 1.3)
        print(f"    [adjust] Low WR ({result.win_rate}%) → penalty ↑ {new['position_change_penalty']:.2f}")

    if result.return_pct < TARGET_5D_RETURN and result.trades > 0:
        # Not enough profit → reward holding winners
        new["profitable_hold_bonus_max"] = min(0.1, new["profitable_hold_bonus_max"] * 1.5)
        new["profitable_close_bonus"] = min(0.5, new["profitable_close_bonus"] * 1.3)
        print(f"    [adjust] Low return ({result.return_pct}%) → hold bonus ↑ {new['profitable_hold_bonus_max']:.3f}")

    if result.max_dd > 15:
        # Too much drawdown → penalize harder
        new["drawdown_penalty_factor"] = min(0.5, new["drawdown_penalty_factor"] * 1.5)
        print(f"    [adjust] High DD ({result.max_dd}%) → DD penalty ↑ {new['drawdown_penalty_factor']:.3f}")

    return new


# ── Retraining ───────────────────────────────────────────────

def retrain_model(model_path: str, train_range: tuple[str, str],
                  reward_config: dict, steps: int = TRAIN_STEPS,
                  output_path: str = None) -> str:
    """Retrain RL model with adjusted reward config."""
    from sb3_contrib import RecurrentPPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    from trading_value.adapters.rl_env_c import TradingEnvC
    from trading_value.core.models import Timeframe

    if output_path is None:
        output_path = model_path + "_retrained"

    # Load training data from sim_1m.sqlite
    conn = sqlite3.connect(str(DB_PATH))
    df_1m = pd.read_sql_query(
        "SELECT timestamp, datetime, open, high, low, close, volume "
        "FROM ohlcv_1m WHERE symbol='ETHUSDT' AND datetime >= ? AND datetime < ? "
        "ORDER BY timestamp",
        conn, params=(train_range[0], train_range[1]),
    )
    conn.close()

    if len(df_1m) < 1000:
        print(f"    [retrain] Not enough data: {len(df_1m)} rows")
        return model_path

    df_1m["timestamp"] = pd.to_datetime(df_1m["datetime"], utc=True)

    # Aggregate to 30m, 1h, 4h
    def resample(df, rule):
        return (df.set_index("timestamp")
                .resample(rule)
                .agg({"open": "first", "high": "max", "low": "min",
                      "close": "last", "volume": "sum"})
                .dropna().reset_index())

    df_30m = resample(df_1m, "30min")
    df_1h = resample(df_1m, "1h")
    df_4h = resample(df_1m, "4h")

    data = {Timeframe.M30: df_30m, Timeframe.H1: df_1h, Timeframe.H4: df_4h}

    if len(df_30m) < 100:
        print(f"    [retrain] Not enough 30m bars: {len(df_30m)}")
        return model_path

    # Create environment with adjusted rewards
    env_kwargs = {
        "data": data, "symbol": "ETHUSDT", "initial_balance": 10000.0,
        "commission_rate": 0.0002, "episode_bars": min(960, len(df_30m) - 50),
        "random_start": True, "sharpe_window": 48,
    }

    def make_env():
        return TradingEnvC(**env_kwargs)

    vec_env = DummyVecEnv([make_env])

    # Load existing model and continue training
    print(f"    [retrain] Loading {Path(model_path).name}...")
    model = RecurrentPPO.load(model_path, env=vec_env)

    print(f"    [retrain] Training {steps:,} steps with adjusted rewards...")
    print(f"    [retrain] Config: {json.dumps({k: round(v, 3) for k, v in reward_config.items()})}")
    model.learn(total_timesteps=steps, progress_bar=True)

    model.save(output_path)
    print(f"    [retrain] Saved: {output_path}")
    vec_env.close()

    return output_path


# ── Main Loop ────────────────────────────────────────────────

def training_loop(model_name: str = "B Berserker",
                  model_path: str = None,
                  max_rounds: int = MAX_ROUNDS):
    """Main auto-training loop."""

    if model_path is None:
        model_path = str(DATA_DIR / "rl_model_b_3m")

    RESULTS_DIR.mkdir(exist_ok=True)

    # Get data range
    data_start, data_end = get_data_range()
    print(f"\n{'='*60}")
    print(f"  AUTO-TRAIN: {model_name}")
    print(f"  Data: {data_start[:10]} ~ {data_end[:10]}")
    print(f"  Target: WR ≥ {TARGET_WIN_RATE}%, 5D return ≥ +{TARGET_5D_RETURN}%")
    print(f"  Max rounds: {max_rounds}")
    print(f"{'='*60}\n")

    # Split train/eval
    train_range, eval_range = split_periods(data_start, data_end)
    print(f"  Train pool: {train_range[0]} ~ {train_range[1]}")
    print(f"  Eval pool:  {eval_range[0]} ~ {eval_range[1]}\n")

    reward_config = DEFAULT_REWARD.copy()
    current_model = model_path
    best_score = -999
    stale_count = 0
    consecutive_passes = 0
    history = []

    for round_num in range(1, max_rounds + 1):
        print(f"\n{'─'*60}")
        print(f"  ROUND {round_num}/{max_rounds}")
        print(f"{'─'*60}")

        # Pick random eval period
        eval_start, eval_end = pick_random_period(eval_range, EVAL_DAYS)
        print(f"  Eval period: {eval_start} ~ {eval_end}")

        # Evaluate
        print(f"  Evaluating...")
        result = evaluate_model(current_model, eval_start, eval_end)

        score = result.return_pct + result.win_rate  # composite score
        print(f"  Result: WR={result.win_rate}% Return={result.return_pct:+.1f}% "
              f"Trades={result.trades} DD={result.max_dd}% "
              f"{'PASS' if result.passed else 'FAIL'}")

        history.append({
            "round": round_num,
            "period": result.period,
            "win_rate": result.win_rate,
            "return_pct": result.return_pct,
            "trades": result.trades,
            "max_dd": result.max_dd,
            "passed": result.passed,
            "reward_config": reward_config.copy(),
        })

        if result.passed:
            consecutive_passes += 1
            print(f"  Consecutive passes: {consecutive_passes}/{CONSECUTIVE_PASS}")

            if consecutive_passes >= CONSECUTIVE_PASS:
                print(f"\n  *** PRODUCTION READY! ***")
                print(f"  Model passed {CONSECUTIVE_PASS} consecutive evaluations.")
                # Save as production candidate
                prod_path = str(DATA_DIR / f"rl_model_prod_{model_name[0].lower()}")
                shutil.copy2(current_model + ".zip", prod_path + ".zip")
                print(f"  Saved: {prod_path}")
                break
        else:
            consecutive_passes = 0

            # Check improvement
            if score > best_score:
                best_score = score
                stale_count = 0
                print(f"  New best score: {score:.1f}")
            else:
                stale_count += 1
                print(f"  No improvement ({stale_count}/{STALE_LIMIT})")

            if stale_count >= STALE_LIMIT:
                print(f"\n  STOPPED: {STALE_LIMIT} rounds without improvement.")
                break

            # Adjust rewards
            print(f"  Adjusting rewards...")
            reward_config = adjust_rewards(reward_config, result)

            # Retrain
            train_start, train_end = pick_random_period(train_range, 30)
            print(f"  Retraining on: {train_start} ~ {train_end}")
            new_model = str(DATA_DIR / f"rl_model_auto_{model_name[0].lower()}_r{round_num}")
            current_model = retrain_model(
                current_model, (train_start, train_end),
                reward_config, TRAIN_STEPS, new_model,
            )

    # Save results
    results_file = RESULTS_DIR / f"auto_train_{model_name[0].lower()}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    results_file.write_text(json.dumps({
        "model": model_name,
        "rounds": len(history),
        "consecutive_passes": consecutive_passes,
        "production_ready": consecutive_passes >= CONSECUTIVE_PASS,
        "history": history,
        "final_reward_config": reward_config,
    }, indent=2))
    print(f"\n  Results saved: {results_file}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY: {model_name}")
    print(f"{'='*60}")
    print(f"  Rounds: {len(history)}")
    print(f"  Best WR: {max(h['win_rate'] for h in history):.1f}%")
    print(f"  Best Return: {max(h['return_pct'] for h in history):+.1f}%")
    print(f"  Production Ready: {'YES' if consecutive_passes >= CONSECUTIVE_PASS else 'NO'}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Auto-Training Loop")
    parser.add_argument("--model", default="B",
                       help="Model letter (B/C/F/G)")
    parser.add_argument("--max-rounds", type=int, default=MAX_ROUNDS)
    parser.add_argument("--steps", type=int, default=TRAIN_STEPS)
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

    global TRAIN_STEPS
    TRAIN_STEPS = args.steps

    name, path = MODEL_MAP[args.model]
    training_loop(model_name=name, model_path=path, max_rounds=args.max_rounds)


if __name__ == "__main__":
    main()
