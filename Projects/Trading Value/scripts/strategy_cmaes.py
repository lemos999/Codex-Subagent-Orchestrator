"""CMA-ES Parametric Strategy Optimizer

CMA-ES (Covariance Matrix Adaptation Evolution Strategy) to directly optimize
a parametric trading strategy on 15m ETHUSDT candles.

Walk-forward validation:
  Train:      2021-03 ~ 2023-12
  Validation: 2024-01 ~ 2024-12
  Test:       2025-01 ~ 2026-03

Usage:
    cd "Projects/Trading Value"
    py -3.12 scripts/strategy_cmaes.py
"""
from __future__ import annotations

import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

# ── Ensure cma is installed ──────────────────────────────────────────────────
try:
    import cma
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cma"])
    import cma

# ── Config ───────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sim_1m.sqlite"
SYMBOL = "ETHUSDT"
COMMISSION = 0.0004     # 0.04% per trade
SLIPPAGE = 0.0001       # 0.01% per trade
INITIAL_BALANCE = 10_000.0

# Walk-forward periods
TRAIN_START = "2021-03-01"
TRAIN_END = "2024-01-01"
VAL_START = "2024-01-01"
VAL_END = "2025-01-01"
TEST_START = "2025-01-01"
TEST_END = "2026-04-01"

# CMA-ES settings
POPSIZE = 40
MAXITER = 200
SIGMA0 = 0.3
MIN_TRADES = 20  # penalty if fewer


# ── Strategy Parameters ──────────────────────────────────────────────────────
@dataclass
class StrategyParams:
    # Trend filter
    ma_fast: int            # 5~60
    ma_slow: int            # 50~300
    # Entry conditions
    rsi_oversold: float     # 15~45
    rsi_overbought: float   # 55~85
    vol_filter: float       # 1.0~3.0
    # Exit / risk management
    atr_stop_mult: float    # 1.0~4.0
    atr_tp_mult: float      # 1.5~8.0
    trail_start: float      # 1.0~5.0
    trail_step: float       # 0.3~2.0
    # Timing
    cooldown_bars: int      # 1~20
    # Position sizing
    risk_per_trade: float   # 0.005~0.03
    leverage: float         # 1.0~5.0
    # Direction
    allow_short: bool


# Bounds: [lower, upper] per parameter (13 dimensions)
PARAM_NAMES = [
    "ma_fast", "ma_slow", "rsi_oversold", "rsi_overbought", "vol_filter",
    "atr_stop_mult", "atr_tp_mult", "trail_start", "trail_step",
    "cooldown_bars", "risk_per_trade", "leverage", "allow_short",
]
LOWER_BOUNDS = [5, 50, 15, 55, 1.0, 1.0, 1.5, 1.0, 0.3, 1, 0.005, 1.0, 0]
UPPER_BOUNDS = [60, 300, 45, 85, 3.0, 4.0, 8.0, 5.0, 2.0, 20, 0.03, 5.0, 1]

# Initial guess (inspired by MVS MA(5/200) success)
X0 = [20, 100, 30, 70, 1.5, 2.0, 3.0, 2.5, 0.5, 5, 0.02, 2.0, 0]


def vector_to_params(v: np.ndarray) -> StrategyParams:
    """Clamp and convert a CMA-ES vector into StrategyParams."""
    clamped = np.clip(v, LOWER_BOUNDS, UPPER_BOUNDS)
    return StrategyParams(
        ma_fast=int(round(clamped[0])),
        ma_slow=int(round(clamped[1])),
        rsi_oversold=float(clamped[2]),
        rsi_overbought=float(clamped[3]),
        vol_filter=float(clamped[4]),
        atr_stop_mult=float(clamped[5]),
        atr_tp_mult=float(clamped[6]),
        trail_start=float(clamped[7]),
        trail_step=float(clamped[8]),
        cooldown_bars=int(round(clamped[9])),
        risk_per_trade=float(clamped[10]),
        leverage=float(clamped[11]),
        allow_short=bool(round(clamped[12])),
    )


# ── Data Loading ─────────────────────────────────────────────────────────────
def load_15m_data() -> pd.DataFrame:
    """Load 1m data from sqlite and resample to 15m candles."""
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query(
        "SELECT datetime, open, high, low, close, volume "
        "FROM ohlcv_1m WHERE symbol=? ORDER BY datetime",
        conn, params=(SYMBOL,),
    )
    conn.close()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)

    df_15m = df.resample("15min").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()

    print(f"[데이터] {len(df_15m):,}개 15분봉 로드 ({df_15m.index[0]} ~ {df_15m.index[-1]})")
    return df_15m


# ── Indicator Computation (vectorized) ───────────────────────────────────────
def compute_indicators(df: pd.DataFrame, ma_fast: int, ma_slow: int) -> dict:
    """Precompute all indicators as numpy arrays for speed."""
    close = df["close"].values.astype(np.float64)
    high = df["high"].values.astype(np.float64)
    low = df["low"].values.astype(np.float64)
    volume = df["volume"].values.astype(np.float64)
    n = len(close)

    # MA fast / slow
    ma_f = pd.Series(close).rolling(ma_fast).mean().values
    ma_s = pd.Series(close).rolling(ma_slow).mean().values

    # RSI(14)
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss_arr = np.where(delta < 0, -delta, 0.0)
    avg_gain = pd.Series(gain).rolling(14).mean().values
    avg_loss = pd.Series(loss_arr).rolling(14).mean().values
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = avg_gain / np.where(avg_loss == 0, np.nan, avg_loss)
        rsi = 100.0 - 100.0 / (1.0 + rs)
    rsi = np.nan_to_num(rsi, nan=50.0)

    # ATR(14)
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.roll(close, 1)),
            np.abs(low - np.roll(close, 1)),
        ),
    )
    tr[0] = high[0] - low[0]
    atr = pd.Series(tr).rolling(14).mean().values

    # Volume MA(20)
    vol_ma = pd.Series(volume).rolling(20).mean().values

    return {
        "close": close,
        "high": high,
        "low": low,
        "volume": volume,
        "ma_fast": ma_f,
        "ma_slow": ma_s,
        "rsi": rsi,
        "atr": atr,
        "vol_ma": vol_ma,
        "n": n,
    }


# ── Simulation Result ────────────────────────────────────────────────────────
@dataclass
class SimResult:
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    trades: int
    wins: int
    losses: int
    win_rate: float
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    final_balance: float


# ── Fast Simulation Engine ───────────────────────────────────────────────────
def simulate(params: StrategyParams, ind: dict) -> SimResult:
    """Run a fast simulation loop over precomputed indicators.

    Returns SimResult with all statistics.
    """
    close = ind["close"]
    high = ind["high"]
    low = ind["low"]
    volume = ind["volume"]
    ma_f = ind["ma_fast"]
    ma_s = ind["ma_slow"]
    rsi = ind["rsi"]
    atr = ind["atr"]
    vol_ma = ind["vol_ma"]
    n = ind["n"]

    balance = INITIAL_BALANCE
    position = 0       # 0=flat, 1=long, -1=short
    entry_price = 0.0
    stop_price = 0.0
    tp_price = 0.0
    trail_active = False
    trail_price = 0.0
    last_trade_bar = -999
    cost_mult = 1.0 - COMMISSION - SLIPPAGE

    equity = np.empty(n, dtype=np.float64)
    equity[0] = balance
    trade_returns: list[float] = []

    # Warmup: need max(ma_slow, 14, 20) bars
    warmup = max(params.ma_slow, 20) + 1

    for i in range(1, n):
        price = close[i]
        bar_high = high[i]
        bar_low = low[i]

        # ── Check exit conditions if in position ─────────────────────────
        if position != 0:
            exited = False
            exit_price = 0.0

            if position == 1:  # long
                # Stop loss hit?
                if bar_low <= stop_price:
                    exit_price = stop_price
                    exited = True
                # Take profit hit?
                elif bar_high >= tp_price:
                    exit_price = tp_price
                    exited = True
                else:
                    # Trailing stop update
                    profit_dist = price - entry_price
                    trail_threshold = params.trail_start * atr[i] if not np.isnan(atr[i]) else 1e9
                    if profit_dist >= trail_threshold:
                        trail_active = True
                    if trail_active:
                        new_trail = price - params.trail_step * (atr[i] if not np.isnan(atr[i]) else 0)
                        if new_trail > trail_price:
                            trail_price = new_trail
                        if bar_low <= trail_price:
                            exit_price = trail_price
                            exited = True

            elif position == -1:  # short
                if bar_high >= stop_price:
                    exit_price = stop_price
                    exited = True
                elif bar_low <= tp_price:
                    exit_price = tp_price
                    exited = True
                else:
                    profit_dist = entry_price - price
                    trail_threshold = params.trail_start * atr[i] if not np.isnan(atr[i]) else 1e9
                    if profit_dist >= trail_threshold:
                        trail_active = True
                    if trail_active:
                        new_trail = price + params.trail_step * (atr[i] if not np.isnan(atr[i]) else 0)
                        if new_trail < trail_price or trail_price == 0:
                            trail_price = new_trail
                        if bar_high >= trail_price:
                            exit_price = trail_price
                            exited = True

            if exited:
                if position == 1:
                    pnl_pct = (exit_price / entry_price - 1.0) * params.leverage
                else:
                    pnl_pct = (1.0 - exit_price / entry_price) * params.leverage
                # Subtract commission on exit
                pnl_pct -= (COMMISSION + SLIPPAGE) * params.leverage
                trade_returns.append(pnl_pct)
                balance *= (1.0 + pnl_pct)
                if balance <= 0:
                    balance = 0.0
                    equity[i:] = 0.0
                    break
                position = 0
                last_trade_bar = i

        # ── Check entry conditions if flat ────────────────────────────────
        if position == 0 and i >= warmup:
            bars_since = i - last_trade_bar
            if bars_since < params.cooldown_bars:
                equity[i] = balance
                continue

            cur_atr = atr[i] if not np.isnan(atr[i]) else 0.0
            if cur_atr <= 0:
                equity[i] = balance
                continue

            # Volume filter
            cur_vol_ma = vol_ma[i] if not np.isnan(vol_ma[i]) else 0.0
            vol_ok = volume[i] > params.vol_filter * cur_vol_ma if cur_vol_ma > 0 else False

            ma_f_val = ma_f[i]
            ma_s_val = ma_s[i]
            if np.isnan(ma_f_val) or np.isnan(ma_s_val):
                equity[i] = balance
                continue

            # LONG signal
            if ma_f_val > ma_s_val and rsi[i] < params.rsi_oversold and vol_ok:
                position = 1
                entry_price = price * (1.0 + COMMISSION + SLIPPAGE)  # buy higher
                stop_dist = params.atr_stop_mult * cur_atr
                stop_price = price - stop_dist
                tp_price = price + params.atr_tp_mult * cur_atr
                trail_active = False
                trail_price = stop_price
                last_trade_bar = i

                # Position sizing (risk-based)
                risk_amount = balance * params.risk_per_trade
                pos_size_usd = risk_amount / (stop_dist / price) if stop_dist > 0 else 0
                pos_size_usd = min(pos_size_usd, balance * params.leverage)
                # For our simplified sim, leverage is accounted in pnl_pct

            # SHORT signal
            elif (params.allow_short and
                  ma_f_val < ma_s_val and rsi[i] > params.rsi_overbought and vol_ok):
                position = -1
                entry_price = price * (1.0 - COMMISSION - SLIPPAGE)  # sell lower
                stop_dist = params.atr_stop_mult * cur_atr
                stop_price = price + stop_dist
                tp_price = price - params.atr_tp_mult * cur_atr
                trail_active = False
                trail_price = stop_price
                last_trade_bar = i

        equity[i] = balance

    # ── Compute statistics ────────────────────────────────────────────────
    equity = equity[:n]  # ensure correct size
    total_return_pct = (balance / INITIAL_BALANCE - 1.0) * 100.0

    # Sharpe ratio (annualized from 15m bars; ~35040 bars/year)
    if len(equity) > 1 and equity[0] > 0:
        returns = np.diff(equity) / np.where(equity[:-1] > 0, equity[:-1], 1.0)
        ret_std = returns.std()
        if ret_std > 0:
            sharpe = returns.mean() / ret_std * np.sqrt(35040)
        else:
            sharpe = 0.0
    else:
        sharpe = 0.0

    # Max drawdown
    if len(equity) > 0 and equity.max() > 0:
        peak = np.maximum.accumulate(equity)
        dd = (equity - peak) / np.where(peak > 0, peak, 1.0)
        max_dd = dd.min() * 100.0
    else:
        max_dd = -100.0

    # Trade stats
    n_trades = len(trade_returns)
    if n_trades > 0:
        wins_arr = [r for r in trade_returns if r > 0]
        losses_arr = [r for r in trade_returns if r <= 0]
        n_wins = len(wins_arr)
        n_losses = len(losses_arr)
        win_rate = n_wins / n_trades * 100.0
        avg_win = np.mean(wins_arr) * 100.0 if wins_arr else 0.0
        avg_loss = np.mean(losses_arr) * 100.0 if losses_arr else 0.0
        gross_profit = sum(wins_arr) if wins_arr else 0.0
        gross_loss = abs(sum(losses_arr)) if losses_arr else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    else:
        n_wins = n_losses = 0
        win_rate = avg_win = avg_loss = 0.0
        profit_factor = 0.0

    return SimResult(
        total_return_pct=total_return_pct,
        sharpe_ratio=sharpe,
        max_drawdown_pct=max_dd,
        trades=n_trades,
        wins=n_wins,
        losses=n_losses,
        win_rate=win_rate,
        avg_win_pct=avg_win,
        avg_loss_pct=avg_loss,
        profit_factor=profit_factor,
        final_balance=balance,
    )


# ── CMA-ES Objective ────────────────────────────────────────────────────────
def make_objective(ind_cache: dict):
    """Create an objective closure that uses precomputed indicators."""
    def objective(params_vector):
        params = vector_to_params(params_vector)
        # Ensure ma_fast < ma_slow
        if params.ma_fast >= params.ma_slow:
            return 10.0
        # Get or compute indicators for this MA pair
        key = (params.ma_fast, params.ma_slow)
        if key not in ind_cache:
            ind_cache[key] = compute_indicators(ind_cache["_df"], params.ma_fast, params.ma_slow)
        ind = ind_cache[key]
        result = simulate(params, ind)
        # Penalize too few trades
        if result.trades < MIN_TRADES:
            return 10.0
        # Penalize large drawdowns
        dd_penalty = max(0, (-result.max_drawdown_pct - 50)) * 0.01
        return -result.sharpe_ratio + dd_penalty
    return objective


# ── Walk-Forward ─────────────────────────────────────────────────────────────
def run_on_period(params: StrategyParams, df: pd.DataFrame, label: str) -> SimResult:
    """Run simulation on a specific period."""
    ind = compute_indicators(df, params.ma_fast, params.ma_slow)
    result = simulate(params, ind)
    return result


def print_result(label: str, r: SimResult):
    """Pretty-print a simulation result."""
    print(f"  [{label}]")
    print(f"    수익률: {r.total_return_pct:+.2f}%  |  샤프: {r.sharpe_ratio:.2f}  |  최대DD: {r.max_drawdown_pct:.2f}%")
    print(f"    거래: {r.trades}건  |  승률: {r.win_rate:.1f}%  |  평균승: {r.avg_win_pct:+.2f}%  |  평균패: {r.avg_loss_pct:.2f}%")
    print(f"    Profit Factor: {r.profit_factor:.2f}  |  최종잔고: ${r.final_balance:,.0f}")


def print_params(p: StrategyParams):
    """Pretty-print strategy parameters."""
    print(f"    MA: {p.ma_fast}/{p.ma_slow}")
    print(f"    RSI 진입: 과매도<{p.rsi_oversold:.1f} / 과매수>{p.rsi_overbought:.1f}")
    print(f"    볼륨필터: {p.vol_filter:.2f}x")
    print(f"    손절: {p.atr_stop_mult:.2f}*ATR  |  익절: {p.atr_tp_mult:.2f}*ATR")
    print(f"    트레일: 시작 {p.trail_start:.2f}*ATR, 스텝 {p.trail_step:.2f}*ATR")
    print(f"    쿨다운: {p.cooldown_bars}봉  |  리스크: {p.risk_per_trade*100:.1f}%  |  레버리지: {p.leverage:.1f}x")
    print(f"    숏 허용: {'예' if p.allow_short else '아니오'}")


# ── Stability Check ──────────────────────────────────────────────────────────
def stability_check(best_vector: np.ndarray, df: pd.DataFrame, n_perturbations: int = 20) -> dict:
    """Check if best params +/- 10% still profitable."""
    base_params = vector_to_params(best_vector)
    base_ind = compute_indicators(df, base_params.ma_fast, base_params.ma_slow)
    base_result = simulate(base_params, base_ind)

    rng = np.random.default_rng(42)
    profitable_count = 0
    sharpe_list = []

    for _ in range(n_perturbations):
        # Perturb by +/- 10%
        noise = rng.uniform(0.9, 1.1, size=len(best_vector))
        perturbed = best_vector * noise
        perturbed = np.clip(perturbed, LOWER_BOUNDS, UPPER_BOUNDS)
        p = vector_to_params(perturbed)
        if p.ma_fast >= p.ma_slow:
            continue
        ind = compute_indicators(df, p.ma_fast, p.ma_slow)
        r = simulate(p, ind)
        sharpe_list.append(r.sharpe_ratio)
        if r.total_return_pct > 0:
            profitable_count += 1

    n_tested = len(sharpe_list)
    return {
        "n_tested": n_tested,
        "profitable_pct": profitable_count / n_tested * 100 if n_tested > 0 else 0,
        "avg_sharpe": np.mean(sharpe_list) if sharpe_list else 0,
        "std_sharpe": np.std(sharpe_list) if sharpe_list else 0,
        "min_sharpe": np.min(sharpe_list) if sharpe_list else 0,
        "base_sharpe": base_result.sharpe_ratio,
    }


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 80)
    print("  CMA-ES 파라메트릭 전략 최적화기")
    print(f"  심볼: {SYMBOL} | 타임프레임: 15m")
    print(f"  커미션: {COMMISSION*100:.2f}% + 슬리피지: {SLIPPAGE*100:.2f}%")
    print(f"  학습: {TRAIN_START} ~ {TRAIN_END}")
    print(f"  검증: {VAL_START} ~ {VAL_END}")
    print(f"  테스트: {TEST_START} ~ {TEST_END}")
    print(f"  CMA-ES: popsize={POPSIZE}, maxiter={MAXITER}")
    print("=" * 80)

    # ── Load data ─────────────────────────────────────────────────────────
    t0 = time.time()
    df_all = load_15m_data()
    load_time = time.time() - t0
    print(f"  데이터 로드: {load_time:.1f}초")

    df_train = df_all[(df_all.index >= TRAIN_START) & (df_all.index < TRAIN_END)]
    df_val = df_all[(df_all.index >= VAL_START) & (df_all.index < VAL_END)]
    df_test = df_all[(df_all.index >= TEST_START) & (df_all.index < TEST_END)]

    print(f"  학습: {len(df_train):,}봉  |  검증: {len(df_val):,}봉  |  테스트: {len(df_test):,}봉")

    if len(df_train) < 1000:
        print("  학습 데이터 부족! 종료.")
        return
    if len(df_val) < 100:
        print("  검증 데이터 부족! 종료.")
        return

    # ── CMA-ES Optimization on Train ──────────────────────────────────────
    print("\n" + "-" * 80)
    print("  [1/4] CMA-ES 최적화 (학습 기간)")
    print("-" * 80)

    ind_cache: dict = {"_df": df_train}
    objective = make_objective(ind_cache)

    t_opt = time.time()
    es = cma.CMAEvolutionStrategy(X0, SIGMA0, {
        "popsize": POPSIZE,
        "maxiter": MAXITER,
        "bounds": [LOWER_BOUNDS, UPPER_BOUNDS],
        "verbose": -1,  # suppress cma output; we print our own
        "seed": 42,
    })

    gen = 0
    while not es.stop():
        solutions = es.ask()
        fitnesses = [objective(s) for s in solutions]
        es.tell(solutions, fitnesses)
        gen += 1

        if gen % 20 == 0:
            best_fit = min(fitnesses)
            best_p = vector_to_params(solutions[np.argmin(fitnesses)])
            elapsed = time.time() - t_opt
            print(f"    세대 {gen:4d} | 최고 Sharpe: {-best_fit:.3f} | "
                  f"MA: {best_p.ma_fast}/{best_p.ma_slow} | "
                  f"경과: {elapsed:.0f}초")

    opt_time = time.time() - t_opt
    best_vector = es.result.xbest
    best_fitness = es.result.fbest
    best_params = vector_to_params(best_vector)

    print(f"\n  최적화 완료! ({opt_time:.0f}초, {gen}세대)")
    print(f"  최고 적합도: {best_fitness:.4f} (Sharpe ~ {-best_fitness:.3f})")

    # ── Evaluate on all periods ───────────────────────────────────────────
    print("\n" + "-" * 80)
    print("  [2/4] Walk-Forward 검증")
    print("-" * 80)

    print("\n  최적 파라미터:")
    print_params(best_params)

    print()
    r_train = run_on_period(best_params, df_train, "학습")
    print_result("학습 (In-Sample)", r_train)

    print()
    r_val = run_on_period(best_params, df_val, "검증")
    print_result("검증 (Out-of-Sample 1)", r_val)

    print()
    if len(df_test) > 50:
        r_test = run_on_period(best_params, df_test, "테스트")
        print_result("테스트 (Out-of-Sample 2)", r_test)
    else:
        r_test = None
        print("  [테스트] 데이터 부족으로 스킵")

    # ── Top-N Candidates on Validation ────────────────────────────────────
    print("\n" + "-" * 80)
    print("  [3/4] 상위 후보 검증기간 성과")
    print("-" * 80)

    # Collect top-5 from CMA-ES final population
    final_pop = es.result.xfavorite  # single best
    # Also test a few nearby solutions
    candidates = [best_vector]
    rng = np.random.default_rng(123)
    for _ in range(4):
        noise = rng.uniform(0.95, 1.05, size=len(best_vector))
        cand = best_vector * noise
        cand = np.clip(cand, LOWER_BOUNDS, UPPER_BOUNDS)
        candidates.append(cand)

    print(f"  {'#':>3s} {'검증Sharpe':>10s} {'검증수익%':>10s} {'검증DD%':>10s} {'거래수':>6s} {'승률%':>6s}")
    print("  " + "-" * 50)

    best_val_sharpe = -999
    best_val_idx = 0
    for idx, cand in enumerate(candidates):
        cp = vector_to_params(cand)
        if cp.ma_fast >= cp.ma_slow:
            continue
        cr = run_on_period(cp, df_val, f"후보{idx}")
        print(f"  {idx:3d} {cr.sharpe_ratio:10.3f} {cr.total_return_pct:+10.2f} "
              f"{cr.max_drawdown_pct:10.2f} {cr.trades:6d} {cr.win_rate:6.1f}")
        if cr.sharpe_ratio > best_val_sharpe:
            best_val_sharpe = cr.sharpe_ratio
            best_val_idx = idx

    # Use the best on validation
    final_vector = candidates[best_val_idx]
    final_params = vector_to_params(final_vector)
    print(f"\n  검증 기준 최종 선택: 후보 #{best_val_idx}")

    # Re-evaluate final on test
    if r_test is None and len(df_test) <= 50:
        r_test_final = None
    else:
        r_test_final = run_on_period(final_params, df_test, "최종테스트")

    # ── Stability Check ───────────────────────────────────────────────────
    print("\n" + "-" * 80)
    print("  [4/4] 파라미터 안정성 검증 (+-10% 섭동)")
    print("-" * 80)

    stab_train = stability_check(final_vector, df_train)
    stab_val = stability_check(final_vector, df_val)

    print(f"  학습 기간: {stab_train['profitable_pct']:.0f}% 수익 | "
          f"Sharpe 평균: {stab_train['avg_sharpe']:.3f} +/- {stab_train['std_sharpe']:.3f} "
          f"(기준: {stab_train['base_sharpe']:.3f})")
    print(f"  검증 기간: {stab_val['profitable_pct']:.0f}% 수익 | "
          f"Sharpe 평균: {stab_val['avg_sharpe']:.3f} +/- {stab_val['std_sharpe']:.3f} "
          f"(기준: {stab_val['base_sharpe']:.3f})")

    # ── Final Report ──────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  최종 결과 요약")
    print("=" * 80)

    print("\n  최적 파라미터:")
    print_params(final_params)

    print(f"\n  {'기간':10s} {'수익률%':>10s} {'샤프':>8s} {'최대DD%':>10s} {'거래':>6s} {'승률%':>6s} {'PF':>6s}")
    print("  " + "-" * 60)

    for label, r in [("학습", r_train), ("검증", r_val), ("테스트", r_test_final)]:
        if r is None:
            print(f"  {label:10s} {'N/A':>10s}")
            continue
        print(f"  {label:10s} {r.total_return_pct:>+10.2f} {r.sharpe_ratio:>8.2f} "
              f"{r.max_drawdown_pct:>10.2f} {r.trades:>6d} {r.win_rate:>6.1f} {r.profit_factor:>6.2f}")

    # ── Verdict ───────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  실전 배포 가능 여부 판정")
    print("=" * 80)

    issues = []
    goods = []

    # Check validation performance
    if r_val.sharpe_ratio > 0.5:
        goods.append(f"검증 Sharpe {r_val.sharpe_ratio:.2f} > 0.5")
    else:
        issues.append(f"검증 Sharpe {r_val.sharpe_ratio:.2f} < 0.5 (낮음)")

    if r_val.total_return_pct > 0:
        goods.append(f"검증 수익률 {r_val.total_return_pct:+.2f}%")
    else:
        issues.append(f"검증 손실 {r_val.total_return_pct:.2f}%")

    if r_val.max_drawdown_pct > -30:
        goods.append(f"검증 DD {r_val.max_drawdown_pct:.1f}% (통제됨)")
    else:
        issues.append(f"검증 DD {r_val.max_drawdown_pct:.1f}% (과대)")

    # Check test performance
    if r_test_final is not None:
        if r_test_final.sharpe_ratio > 0:
            goods.append(f"테스트 Sharpe {r_test_final.sharpe_ratio:.2f} > 0")
        else:
            issues.append(f"테스트 Sharpe {r_test_final.sharpe_ratio:.2f} <= 0 (OOS 실패)")

        if r_test_final.total_return_pct > 0:
            goods.append(f"테스트 수익률 {r_test_final.total_return_pct:+.2f}%")
        else:
            issues.append(f"테스트 손실 {r_test_final.total_return_pct:.2f}%")

    # Check stability
    if stab_val["profitable_pct"] >= 70:
        goods.append(f"안정성: 섭동 {stab_val['profitable_pct']:.0f}% 수익")
    else:
        issues.append(f"안정성: 섭동 {stab_val['profitable_pct']:.0f}% 수익 (불안정)")

    # Check overfitting
    if r_test_final is not None:
        overfit_ratio = r_train.sharpe_ratio / max(r_test_final.sharpe_ratio, 0.01)
        if overfit_ratio > 5:
            issues.append(f"과적합 의심: 학습/테스트 Sharpe 비율 {overfit_ratio:.1f}x")
        elif overfit_ratio < 3:
            goods.append(f"과적합 통제: 비율 {overfit_ratio:.1f}x")

    print()
    for g in goods:
        print(f"  [PASS] {g}")
    for issue in issues:
        print(f"  [FAIL] {issue}")

    print()
    if len(issues) == 0:
        print("  >>> 판정: 실전 배포 가능 (모든 기준 통과)")
    elif len(issues) <= 2 and len(goods) >= 3:
        print("  >>> 판정: 조건부 배포 가능 (소규모 실전 테스트 권장)")
        print(f"       문제: {', '.join(issues)}")
    else:
        print("  >>> 판정: 실전 배포 불가 (추가 개선 필요)")
        print(f"       문제: {', '.join(issues)}")

    total_time = time.time() - t0
    print(f"\n  총 소요 시간: {total_time:.0f}초 ({total_time/60:.1f}분)")


if __name__ == "__main__":
    main()
