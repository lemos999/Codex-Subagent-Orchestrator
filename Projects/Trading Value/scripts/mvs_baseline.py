"""MVS (Minimum Viable Strategy) 베이스라인 테스트

단순 전략들이 실제로 수익을 낼 수 있는지 검증.
커미션 포함, walk-forward 최적화 적용.

Usage:
    cd "Projects/Trading Value"
    py -3.12 scripts/mvs_baseline.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sim_1m.sqlite"
SYMBOL = "ETHUSDT"
COMMISSION = 0.0004  # 0.04% per trade (0.08% round trip)
INITIAL_BALANCE = 10_000.0

# Walk-forward periods
TRAIN_START = "2021-01-01"
TRAIN_END = "2024-01-01"
TEST_START = "2024-01-01"
TEST_END = "2026-01-01"


# ── Data Loading ──────────────────────────────────────────────────────────────
def load_1h_data() -> pd.DataFrame:
    """Load 1m data and resample to 1H."""
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query(
        "SELECT datetime, open, high, low, close, volume "
        "FROM ohlcv_1m WHERE symbol=? ORDER BY datetime",
        conn, params=(SYMBOL,),
    )
    conn.close()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)

    df_1h = df.resample("1h").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()

    print(f"[데이터] {len(df_1h):,}개 1시간봉 로드 ({df_1h.index[0]} ~ {df_1h.index[-1]})")
    return df_1h


# ── Strategy Engine ───────────────────────────────────────────────────────────
class StrategyResult:
    """Holds backtest results for one strategy."""

    def __init__(self, name: str):
        self.name = name
        self.equity_curve: list[float] = []
        self.trades: int = 0
        self.wins: int = 0
        self.losses: int = 0

    @property
    def total_return(self) -> float:
        if not self.equity_curve:
            return 0.0
        return (self.equity_curve[-1] / self.equity_curve[0] - 1) * 100

    @property
    def annual_return(self) -> float:
        if not self.equity_curve or len(self.equity_curve) < 2:
            return 0.0
        total_r = self.equity_curve[-1] / self.equity_curve[0]
        years = len(self.equity_curve) / (365.25 * 24)  # hourly bars
        if years <= 0:
            return 0.0
        return (total_r ** (1 / years) - 1) * 100

    @property
    def sharpe_ratio(self) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
        if returns.std() == 0:
            return 0.0
        # Annualized (hourly → yearly: sqrt(8760))
        return returns.mean() / returns.std() * np.sqrt(8760)

    @property
    def max_drawdown(self) -> float:
        if not self.equity_curve:
            return 0.0
        eq = np.array(self.equity_curve)
        peak = np.maximum.accumulate(eq)
        dd = (eq - peak) / peak * 100
        return dd.min()

    @property
    def win_rate(self) -> float:
        if self.trades == 0:
            return 0.0
        return self.wins / self.trades * 100


def backtest(
    df: pd.DataFrame,
    signals: pd.Series,
    name: str,
) -> StrategyResult:
    """Run backtest with commission.

    signals: +1 = long, 0 = flat, -1 = short (unused here, all long-only).
    """
    result = StrategyResult(name)
    balance = INITIAL_BALANCE
    position = 0  # 0 or 1
    entry_price = 0.0

    closes = df["close"].values
    sig = signals.values

    result.equity_curve.append(balance)

    for i in range(1, len(closes)):
        price = closes[i]
        prev_price = closes[i - 1]

        # If in position, update equity
        if position == 1:
            pnl_pct = (price - prev_price) / prev_price
            balance *= (1 + pnl_pct)

        # Signal change → trade
        new_sig = sig[i] if not np.isnan(sig[i]) else 0
        old_sig = sig[i - 1] if not np.isnan(sig[i - 1]) else 0

        if new_sig != old_sig:
            # Exit existing position
            if position == 1 and new_sig == 0:
                balance *= (1 - COMMISSION)  # exit cost
                trade_return = price / entry_price - 1 - COMMISSION * 2
                result.trades += 1
                if trade_return > 0:
                    result.wins += 1
                else:
                    result.losses += 1
                position = 0

            # Enter new position
            if new_sig == 1 and position == 0:
                balance *= (1 - COMMISSION)  # entry cost
                entry_price = price
                position = 1

            # Exit short-like → flat transition when signal drops
            if position == 1 and new_sig != 1:
                balance *= (1 - COMMISSION)
                trade_return = price / entry_price - 1 - COMMISSION * 2
                result.trades += 1
                if trade_return > 0:
                    result.wins += 1
                else:
                    result.losses += 1
                position = 0

                # If new_sig is 1 again (won't happen in this branch but safeguard)
                if new_sig == 1:
                    balance *= (1 - COMMISSION)
                    entry_price = price
                    position = 1

        result.equity_curve.append(balance)

    return result


# ── Strategy Definitions ──────────────────────────────────────────────────────
def strategy_buy_hold(df: pd.DataFrame) -> pd.Series:
    """Buy & Hold: always long."""
    return pd.Series(1, index=df.index)


def strategy_ma_cross(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.Series:
    """MA Crossover: long when fast > slow, flat otherwise."""
    ma_fast = df["close"].rolling(fast).mean()
    ma_slow = df["close"].rolling(slow).mean()
    sig = (ma_fast > ma_slow).astype(int)
    return sig


def strategy_ma_cross_volume(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.Series:
    """MA Cross + Volume filter (volume > 1.5x 20-period avg)."""
    ma_fast = df["close"].rolling(fast).mean()
    ma_slow = df["close"].rolling(slow).mean()
    vol_ma = df["volume"].rolling(20).mean()
    vol_ok = df["volume"] > vol_ma * 1.5

    sig = ((ma_fast > ma_slow) & vol_ok).astype(int)
    return sig


def strategy_ma_cross_session(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.Series:
    """MA Cross + Session filter (UTC 08:00-20:00 only)."""
    ma_fast = df["close"].rolling(fast).mean()
    ma_slow = df["close"].rolling(slow).mean()
    session_ok = (df.index.hour >= 8) & (df.index.hour < 20)

    sig = ((ma_fast > ma_slow) & session_ok).astype(int)
    return sig


def strategy_rsi_reversion(df: pd.DataFrame) -> pd.Series:
    """RSI Mean Reversion: buy when RSI<30, sell when RSI>70."""
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    sig = pd.Series(0, index=df.index)
    position = 0
    for i in range(len(rsi)):
        r = rsi.iloc[i]
        if np.isnan(r):
            sig.iloc[i] = position
            continue
        if r < 30 and position == 0:
            position = 1
        elif r > 70 and position == 1:
            position = 0
        sig.iloc[i] = position

    return sig


def strategy_random(df: pd.DataFrame, n_sims: int = 1000) -> StrategyResult:
    """Random strategy: average over n_sims simulations."""
    rng = np.random.default_rng(42)
    all_returns = []
    all_sharpes = []
    all_dds = []
    all_trades = []

    for _ in range(n_sims):
        # Random signal flips (average hold ~24h)
        sig_arr = np.zeros(len(df))
        pos = 0
        for i in range(len(df)):
            if rng.random() < 1 / 24:  # flip ~once per day
                pos = 1 - pos
            sig_arr[i] = pos

        sig = pd.Series(sig_arr, index=df.index)
        r = backtest(df, sig, "random")
        all_returns.append(r.total_return)
        all_sharpes.append(r.sharpe_ratio)
        all_dds.append(r.max_drawdown)
        all_trades.append(r.trades)

    avg_result = StrategyResult("랜덤 (1000 시뮬)")
    # Create a synthetic equity curve for display
    avg_result.equity_curve = [INITIAL_BALANCE, INITIAL_BALANCE * (1 + np.mean(all_returns) / 100)]
    avg_result.trades = int(np.mean(all_trades))
    avg_result._avg_return = np.mean(all_returns)
    avg_result._avg_sharpe = np.mean(all_sharpes)
    avg_result._avg_dd = np.mean(all_dds)
    avg_result._std_return = np.std(all_returns)
    return avg_result


# ── MA Optimization ───────────────────────────────────────────────────────────
def optimize_ma_params(df_train: pd.DataFrame) -> tuple[int, int]:
    """Grid search for best fast/slow MA params on training data."""
    best_sharpe = -999
    best_params = (20, 50)

    for fast in [5, 10, 15, 20, 30]:
        for slow in [30, 50, 75, 100, 150, 200]:
            if fast >= slow:
                continue
            sig = strategy_ma_cross(df_train, fast, slow)
            r = backtest(df_train, sig, f"MA({fast},{slow})")
            if r.sharpe_ratio > best_sharpe:
                best_sharpe = r.sharpe_ratio
                best_params = (fast, slow)

    print(f"  [최적화] MA 최적 파라미터: fast={best_params[0]}, slow={best_params[1]} (학습 Sharpe={best_sharpe:.2f})")
    return best_params


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 80)
    print("  MVS (Minimum Viable Strategy) 베이스라인 테스트")
    print(f"  커미션: {COMMISSION*100:.2f}% per trade ({COMMISSION*2*100:.2f}% round trip)")
    print(f"  학습 기간: {TRAIN_START} ~ {TRAIN_END}")
    print(f"  테스트 기간: {TEST_START} ~ {TEST_END}")
    print("=" * 80)

    df_1h = load_1h_data()

    # Split train/test
    df_train = df_1h[(df_1h.index >= TRAIN_START) & (df_1h.index < TRAIN_END)]
    df_test = df_1h[(df_1h.index >= TEST_START) & (df_1h.index < TEST_END)]

    print(f"\n학습: {len(df_train):,}개 봉 ({df_train.index[0]} ~ {df_train.index[-1]})")
    print(f"테스트: {len(df_test):,}개 봉 ({df_test.index[0]} ~ {df_test.index[-1]})")

    if len(df_test) < 100:
        print("테스트 데이터 부족! 기간을 확인하세요.")
        # Fall back: use last 25% as test
        split = int(len(df_1h) * 0.75)
        df_train = df_1h.iloc[:split]
        df_test = df_1h.iloc[split:]
        print(f"대안: 학습 {len(df_train):,}봉, 테스트 {len(df_test):,}봉")

    # Optimize MA params on train
    print("\n--- MA 파라미터 최적화 (학습 기간) ---")
    opt_fast, opt_slow = optimize_ma_params(df_train)

    # Run all strategies on TEST period
    print("\n--- 테스트 기간 전략 실행 ---")
    results: list[StrategyResult] = []

    # a. Buy & Hold
    sig = strategy_buy_hold(df_test)
    r = backtest(df_test, sig, "바이앤홀드")
    results.append(r)
    print(f"  [1] 바이앤홀드 완료")

    # b. MA Crossover (optimized)
    sig = strategy_ma_cross(df_test, opt_fast, opt_slow)
    r = backtest(df_test, sig, f"MA크로스({opt_fast}/{opt_slow})")
    results.append(r)
    print(f"  [2] MA크로스 완료")

    # c. MA Cross + Volume
    sig = strategy_ma_cross_volume(df_test, opt_fast, opt_slow)
    r = backtest(df_test, sig, f"MA+볼륨필터")
    results.append(r)
    print(f"  [3] MA+볼륨필터 완료")

    # d. MA Cross + Session
    sig = strategy_ma_cross_session(df_test, opt_fast, opt_slow)
    r = backtest(df_test, sig, f"MA+세션필터")
    results.append(r)
    print(f"  [4] MA+세션필터 완료")

    # e. RSI Mean Reversion
    sig = strategy_rsi_reversion(df_test)
    r = backtest(df_test, sig, "RSI반전(30/70)")
    results.append(r)
    print(f"  [5] RSI반전 완료")

    # f. Random
    print(f"  [6] 랜덤 시뮬레이션 1000회 실행 중...")
    r_random = strategy_random(df_test, n_sims=1000)
    results.append(r_random)
    print(f"  [6] 랜덤 완료")

    # ── Results Table ─────────────────────────────────────────────────────────
    print("\n" + "=" * 110)
    print("  결과 비교 테이블 (테스트 기간)")
    print("=" * 110)
    header = (f"{'전략':20s} {'총수익률%':>10s} {'연수익률%':>10s} {'샤프비율':>8s} "
              f"{'최대DD%':>10s} {'거래수':>8s} {'승률%':>8s}")
    print(header)
    print("-" * 110)

    for r in results:
        # Handle random strategy's special attributes
        if hasattr(r, "_avg_return"):
            total_r = r._avg_return
            annual_r = total_r  # approximate (test period ~1-2 years)
            sharpe = r._avg_sharpe
            dd = r._avg_dd
            extra = f"  (std={r._std_return:.1f}%)"
        else:
            total_r = r.total_return
            annual_r = r.annual_return
            sharpe = r.sharpe_ratio
            dd = r.max_drawdown
            extra = ""

        print(f"{r.name:20s} {total_r:>10.2f} {annual_r:>10.2f} {sharpe:>8.2f} "
              f"{dd:>10.2f} {r.trades:>8d} {r.win_rate:>8.1f}{extra}")

    # ── Verdict ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  판정: 이 데이터에서 단순 전략으로 돈을 벌 수 있는가?")
    print("=" * 80)

    # Find best non-random, non-buy-hold strategy
    active_results = [r for r in results if not hasattr(r, "_avg_return") and r.name != "바이앤홀드"]
    bh = results[0]  # buy & hold

    best_active = max(active_results, key=lambda r: r.sharpe_ratio) if active_results else None

    # Random baseline
    random_r = results[-1]
    random_return = random_r._avg_return if hasattr(random_r, "_avg_return") else random_r.total_return

    print(f"\n  바이앤홀드 수익률: {bh.total_return:.2f}%")
    if best_active:
        print(f"  최고 액티브 전략: {best_active.name} → 수익률 {best_active.total_return:.2f}%, 샤프 {best_active.sharpe_ratio:.2f}")
    print(f"  랜덤 평균 수익률: {random_return:.2f}%")

    print()
    if best_active and best_active.sharpe_ratio > 0.5 and best_active.total_return > 0:
        print("  ✓ 결론: 단순 전략으로도 수익 가능성 있음.")
        print(f"    → {best_active.name} 전략이 양의 샤프비율과 수익률을 보임.")
        if best_active.total_return > bh.total_return:
            print(f"    → 바이앤홀드 대비 초과수익 {best_active.total_return - bh.total_return:+.2f}%p")
        else:
            print(f"    → 단, 바이앤홀드 대비 미달 ({best_active.total_return - bh.total_return:+.2f}%p)")
    elif best_active and best_active.total_return > 0:
        print("  △ 결론: 미약한 수익 가능성. 커미션 후 의미있는 알파 확보 어려움.")
        print(f"    → 최고 전략 수익률 {best_active.total_return:.2f}%이나 샤프비율 {best_active.sharpe_ratio:.2f}로 불안정.")
    else:
        print("  ✗ 결론: 단순 전략으로는 커미션 포함 시 수익 불가.")
        print("    → 기술적 지표 기반 단순 룰만으로는 알파 없음.")
        print("    → ML/RL 접근이 필요하거나, 시장 자체에 예측 가능한 패턴이 약함.")

    print()
    if random_return > -5:
        print(f"  참고: 랜덤 전략 평균 수익률 {random_return:.2f}%")
        print("    → 커미션 빈도에 따른 자연 마모 수준 확인.")


if __name__ == "__main__":
    main()
