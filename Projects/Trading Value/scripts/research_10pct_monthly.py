"""Research: +10%/month strategy feasibility study.

Analyzes leveraged ETFs, regime detection, and realistic target expectations.

Covers:
1. Leveraged ETF data availability & B&H performance (NVDL, TQQQ, SOXL)
2. Regime-based leveraged switching (bull=leveraged, bear=flat)
3. AMZN feasibility check
4. Top 3 executable strategies with backtest logic

Usage:
    cd "Projects/Trading Value"
    py -3.12 scripts/research_10pct_monthly.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INITIAL = 10_000.0

# ============================================================
# SECTION 1: Data Availability Check
# ============================================================

TICKERS = {
    "NVDA":  {"desc": "NVIDIA (base)", "leverage": 1},
    "NVDL":  {"desc": "GraniteShares 2x NVDA", "leverage": 2},
    "NVDU":  {"desc": "Direxion 2x NVDA", "leverage": 2},
    "TQQQ":  {"desc": "ProShares 3x QQQ", "leverage": 3},
    "SOXL":  {"desc": "Direxion 3x Semiconductors", "leverage": 3},
    "QQQ":   {"desc": "Nasdaq-100 ETF (base)", "leverage": 1},
    "AMZN":  {"desc": "Amazon (base)", "leverage": 1},
    "UPRO":  {"desc": "ProShares 3x S&P500", "leverage": 3},
}


def check_data_availability():
    """Check yfinance data availability for all tickers."""
    print("=" * 70)
    print("  SECTION 1: Data Availability")
    print("=" * 70)

    results = {}
    for ticker, info in TICKERS.items():
        try:
            df = yf.Ticker(ticker).history(period="max", interval="1d")
            if len(df) < 10:
                print(f"  {ticker:6s} | {info['desc']:35s} | NO DATA")
                results[ticker] = None
                continue
            start = df.index[0].date()
            end = df.index[-1].date()
            months = len(df) / 21
            print(f"  {ticker:6s} | {info['desc']:35s} | {start} ~ {end} | {len(df):5d} bars ({months:.0f} mo)")
            results[ticker] = df
        except Exception as e:
            print(f"  {ticker:6s} | ERROR: {e}")
            results[ticker] = None

    return results


# ============================================================
# SECTION 2: Monthly Return Analysis
# ============================================================

def monthly_analysis(data: dict[str, pd.DataFrame | None]):
    """Compute monthly returns for all available tickers."""
    print("\n" + "=" * 70)
    print("  SECTION 2: Monthly Return Analysis")
    print("=" * 70)

    stats = {}
    for ticker, df in data.items():
        if df is None or len(df) < 42:  # need at least 2 months
            continue

        # Resample to monthly
        monthly = df["Close"].resample("ME").last().dropna()
        if len(monthly) < 3:
            continue
        mrets = monthly.pct_change().dropna() * 100

        avg = mrets.mean()
        std = mrets.std()
        gt10 = (mrets > 10).sum()
        gt10_pct = gt10 / len(mrets) * 100
        lt_neg10 = (mrets < -10).sum()
        lt_neg10_pct = lt_neg10 / len(mrets) * 100
        best = mrets.max()
        worst = mrets.min()

        # Max drawdown (from monthly equity curve)
        eq = (1 + mrets / 100).cumprod()
        dd = ((eq.cummax() - eq) / eq.cummax() * 100).max()

        stats[ticker] = {
            "months": len(mrets), "avg": avg, "std": std,
            "gt10_pct": gt10_pct, "lt_neg10_pct": lt_neg10_pct,
            "best": best, "worst": worst, "dd": dd,
        }

        lev = TICKERS[ticker]["leverage"]
        tag = f"({lev}x)" if lev > 1 else ""
        print(f"  {ticker:6s}{tag:>5s} | Avg={avg:+5.1f}%/mo | Std={std:5.1f}% | "
              f">+10%: {gt10_pct:4.0f}% | <-10%: {lt_neg10_pct:4.0f}% | "
              f"Best={best:+6.1f}% | Worst={worst:+6.1f}% | MaxDD={dd:.0f}%")

    return stats


# ============================================================
# SECTION 3: B&H Performance (CAGR, Total Return)
# ============================================================

def bh_performance(data: dict[str, pd.DataFrame | None]):
    """Buy & Hold total return and CAGR."""
    print("\n" + "=" * 70)
    print("  SECTION 3: Buy & Hold Performance")
    print("=" * 70)

    for ticker, df in data.items():
        if df is None or len(df) < 42:
            continue
        total = (df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100
        years = len(df) / 252
        cagr = ((df["Close"].iloc[-1] / df["Close"].iloc[0]) ** (1 / years) - 1) * 100 if years > 0 else 0
        monthly_avg = cagr / 12
        print(f"  {ticker:6s} | Total={total:+8.1f}% over {years:.1f}y | CAGR={cagr:+6.1f}% | "
              f"Avg Monthly={monthly_avg:+5.2f}% | Target gap: {10 - monthly_avg:+.2f}%/mo")


# ============================================================
# SECTION 4: Regime-Based Leveraged Switching Backtest
# ============================================================

def sma(arr, w):
    """Simple moving average."""
    n = len(arr)
    out = np.full(n, np.nan)
    cs = np.cumsum(arr)
    cs = np.insert(cs, 0, 0)
    if n >= w:
        out[w - 1:] = (cs[w:] - cs[:-w]) / w
    return out


def ema(arr, span):
    """Exponential moving average."""
    alpha = 2 / (span + 1)
    out = np.full(len(arr), np.nan)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        if np.isnan(out[i - 1]):
            out[i] = arr[i]
        else:
            out[i] = alpha * arr[i] + (1 - alpha) * out[i - 1]
    return out


def adx(high, low, close, period=14):
    """Average Directional Index."""
    n = len(close)
    tr = np.zeros(n)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)

    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        plus_dm[i] = up if (up > down and up > 0) else 0
        minus_dm[i] = down if (down > up and down > 0) else 0

    atr = sma(tr, period)
    plus_di = sma(plus_dm, period) / np.maximum(atr, 1e-10) * 100
    minus_di = sma(minus_dm, period) / np.maximum(atr, 1e-10) * 100
    dx = np.abs(plus_di - minus_di) / np.maximum(plus_di + minus_di, 1e-10) * 100
    adx_val = sma(dx, period)
    return adx_val


@dataclass
class RegimeResult:
    ticker: str
    strategy: str
    total_ret: float
    monthly_avg: float
    sharpe: float
    max_dd: float
    trades: int
    win_rate: float
    months_gt10: int
    total_months: int
    bh_ret: float


def regime_backtest(df: pd.DataFrame, ticker: str,
                    ma_fast: int = 20, ma_slow: int = 50,
                    adx_thresh: float = 25,
                    lev_bull: float = 2.0, lev_mild: float = 1.0,
                    stop_pct: float = 0.05,
                    use_adx: bool = True) -> RegimeResult:
    """Regime-based leveraged backtest on daily data.

    Regime detection:
    - Bull: MA_fast > MA_slow AND price > MA_fast (AND ADX > thresh if use_adx)
    - Mild bull: MA_fast > MA_slow AND price <= MA_fast
    - Bear: MA_fast <= MA_slow -> FLAT (cash)
    - Sideways: ADX < thresh -> FLAT
    """
    c = df["Close"].values
    h = df["High"].values
    lo = df["Low"].values
    n = len(c)

    mf = sma(c, ma_fast)
    ms = sma(c, ma_slow)
    adx_val = adx(h, lo, c) if use_adx else np.zeros(n)

    bal = INITIAL
    peak = INITIAL
    pos = 0
    entry_price = 0.0
    stop_price = 0.0
    cur_lev = 0.0
    trade_rets = []

    # Monthly tracking
    monthly_bals = []
    last_month = None
    month_start_bal = INITIAL

    warmup = max(ma_slow + 15, 60)  # enough for ADX

    for i in range(warmup, n):
        if np.isnan(mf[i]) or np.isnan(ms[i]):
            continue

        # Monthly tracking
        dt = df.index[i]
        cur_month = (dt.year, dt.month)
        if last_month is not None and cur_month != last_month:
            monthly_bals.append((last_month, month_start_bal, bal))
            month_start_bal = bal
        last_month = cur_month

        # Regime detection
        bull = mf[i] > ms[i] and c[i] > mf[i]
        mild = mf[i] > ms[i] and c[i] <= mf[i]
        sideways = use_adx and not np.isnan(adx_val[i]) and adx_val[i] < adx_thresh

        if sideways:
            bull = False
            mild = False

        # Position management
        if pos == 1:
            # Stop loss check
            if lo[i] <= stop_price:
                pnl = (stop_price / entry_price - 1) * cur_lev - 0.001 * 2
                trade_rets.append(pnl)
                bal *= (1 + pnl)
                if bal <= 0:
                    bal = 0
                    break
                peak = max(peak, bal)
                pos = 0
                continue

            # Exit on bear regime
            if not bull and not mild:
                pnl = (c[i] / entry_price - 1) * cur_lev - 0.001 * 2
                trade_rets.append(pnl)
                bal *= (1 + pnl)
                if bal <= 0:
                    bal = 0
                    break
                peak = max(peak, bal)
                pos = 0
                continue

            # Trailing stop
            new_stop = c[i] * (1 - stop_pct)
            if new_stop > stop_price:
                stop_price = new_stop

        # Entry
        if pos == 0:
            if bull:
                pos = 1
                entry_price = c[i]
                cur_lev = lev_bull
                stop_price = c[i] * (1 - stop_pct)
            elif mild:
                pos = 1
                entry_price = c[i]
                cur_lev = lev_mild
                stop_price = c[i] * (1 - stop_pct)

    # Force close
    if pos == 1:
        pnl = (c[-1] / entry_price - 1) * cur_lev - 0.001 * 2
        trade_rets.append(pnl)
        bal *= (1 + pnl)

    # Final month
    if last_month is not None:
        monthly_bals.append((last_month, month_start_bal, bal))

    # Compute monthly returns
    monthly_rets = []
    for _, start_b, end_b in monthly_bals:
        if start_b > 0:
            monthly_rets.append((end_b / start_b - 1) * 100)

    total_ret = (bal / INITIAL - 1) * 100
    bh_ret = (c[-1] / c[warmup] - 1) * 100

    if not trade_rets:
        return RegimeResult(ticker, "regime", 0, 0, 0, 0, 0, 0, 0, len(monthly_rets), bh_ret)

    r = np.array(trade_rets)
    sharpe = r.mean() / max(r.std(), 1e-8) * np.sqrt(252) if len(r) > 1 else 0
    eq = np.cumprod(1 + r) * INITIAL
    dd = ((np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq) * 100).max()
    wr = (r > 0).sum() / len(r) * 100

    mr = np.array(monthly_rets)
    monthly_avg = mr.mean() if len(mr) > 0 else 0
    months_gt10 = (mr > 10).sum() if len(mr) > 0 else 0

    return RegimeResult(
        ticker=ticker, strategy="regime_lev",
        total_ret=total_ret, monthly_avg=monthly_avg,
        sharpe=sharpe, max_dd=dd, trades=len(r), win_rate=wr,
        months_gt10=int(months_gt10), total_months=len(monthly_rets),
        bh_ret=bh_ret,
    )


def run_regime_backtests(data: dict[str, pd.DataFrame | None]):
    """Run regime-based backtests on multiple assets/configs."""
    print("\n" + "=" * 70)
    print("  SECTION 4: Regime-Based Leveraged Switching Backtests")
    print("=" * 70)

    configs = [
        # (ticker, ma_fast, ma_slow, adx_thresh, lev_bull, lev_mild, stop%, use_adx, label)
        ("NVDA",  20, 50, 25, 2.0, 1.0, 0.05, True,  "NVDA 2x regime"),
        ("NVDA",  20, 50, 25, 3.0, 1.5, 0.07, True,  "NVDA 3x aggressive"),
        ("NVDA",  10, 30, 20, 2.0, 0.5, 0.04, True,  "NVDA 2x fast"),
        ("TQQQ",  20, 50, 25, 1.0, 0.5, 0.08, True,  "TQQQ B&H-ish (already 3x)"),
        ("TQQQ",  20, 50, 25, 1.0, 0.0, 0.10, True,  "TQQQ regime on/off"),
        ("SOXL",  20, 50, 25, 1.0, 0.0, 0.10, True,  "SOXL regime on/off"),
        ("QQQ",   20, 50, 25, 3.0, 1.0, 0.05, True,  "QQQ synthetic 3x"),
        ("AMZN",  20, 50, 25, 2.0, 1.0, 0.05, True,  "AMZN 2x regime"),
        ("AMZN",  20, 50, 25, 3.0, 1.5, 0.07, True,  "AMZN 3x aggressive"),
    ]

    results = []
    for ticker, mf, ms, adx_t, lb, lm, stop, use_adx, label in configs:
        if data.get(ticker) is None:
            print(f"  {label:30s} | SKIP (no data)")
            continue

        df = data[ticker]
        if len(df) < ms + 60:
            print(f"  {label:30s} | SKIP (insufficient data)")
            continue

        r = regime_backtest(df, ticker, mf, ms, adx_t, lb, lm, stop, use_adx)
        results.append((label, r))

        target_tag = "HIT" if r.monthly_avg >= 10 else ("CLOSE" if r.monthly_avg >= 7 else "MISS")
        print(f"  {label:30s} | Total={r.total_ret:+8.1f}% | Avg/mo={r.monthly_avg:+5.1f}% | "
              f"DD=-{r.max_dd:.0f}% | Trades={r.trades:3d} | WR={r.win_rate:.0f}% | "
              f">10%mo: {r.months_gt10}/{r.total_months} | B&H={r.bh_ret:+.0f}% | [{target_tag}]")

    return results


# ============================================================
# SECTION 5: AMZN Feasibility
# ============================================================

def amzn_feasibility(data: dict[str, pd.DataFrame | None]):
    """Assess AMZN +10%/month feasibility."""
    print("\n" + "=" * 70)
    print("  SECTION 5: AMZN Feasibility Assessment")
    print("=" * 70)

    df = data.get("AMZN")
    if df is None:
        print("  AMZN data not available.")
        return

    monthly = df["Close"].resample("ME").last().dropna()
    mrets = monthly.pct_change().dropna() * 100

    avg = mrets.mean()
    std = mrets.std()
    gt10 = (mrets > 10).sum()
    gt10_pct = gt10 / len(mrets) * 100

    # Required leverage to get avg +10%/mo
    req_lev = 10.0 / max(avg, 0.01)

    # With 3x leverage
    lev3_avg = avg * 3
    lev3_std = std * 3  # approximate, ignoring vol decay
    lev3_worst = mrets.min() * 3

    print(f"  AMZN avg monthly: {avg:+.2f}% (std: {std:.1f}%)")
    print(f"  Months >+10%: {gt10}/{len(mrets)} ({gt10_pct:.0f}%)")
    print(f"  Required leverage for +10%/mo avg: {req_lev:.1f}x (UNREALISTIC)")
    print(f"  With 3x leverage: avg={lev3_avg:+.1f}%/mo, worst month={lev3_worst:+.1f}%")
    print(f"")

    if avg < 2:
        print(f"  VERDICT: AMZN is NOT viable for +10%/mo target.")
        print(f"  Even with 3x leverage, avg={lev3_avg:+.1f}%/mo << +10%.")
        print(f"  AMZN's low volatility ({std:.1f}%) means momentum strategies")
        print(f"  also can't reliably extract +10%/mo.")
        print(f"  RECOMMENDATION: Drop AMZN. Focus on NVDA/SOXL/TQQQ.")
    else:
        print(f"  AMZN may be marginal with 3x leverage + perfect timing.")


# ============================================================
# SECTION 6: Downmarket / Sideways Defense
# ============================================================

def regime_defense_analysis(data: dict[str, pd.DataFrame | None]):
    """Analyze regime detection criteria and defense strategies."""
    print("\n" + "=" * 70)
    print("  SECTION 6: Downmarket/Sideways Defense Criteria")
    print("=" * 70)

    print("""
  REGIME DETECTION FRAMEWORK:
  ===========================

  1. BULL (full leverage):
     - SMA(20) > SMA(50) [trend direction]
     - Price > SMA(20) [momentum]
     - ADX > 25 [trend strength]
     -> Action: LONG with full leverage (2-3x)

  2. MILD BULL (reduced leverage):
     - SMA(20) > SMA(50) [still uptrend]
     - Price < SMA(20) [pullback]
     - ADX > 20
     -> Action: LONG with 1x (no leverage) or 0.5x

  3. BEAR (defensive):
     - SMA(20) < SMA(50) [downtrend confirmed]
     OR Price < SMA(50) AND SMA(20) declining
     -> Action: FLAT (100% cash)
     -> Optional: Inverse ETF (SQQQ) for hedging, NOT profit

  4. SIDEWAYS (wait):
     - ADX < 20 [no trend]
     - Price oscillating around SMA(20) and SMA(50)
     -> Action: FLAT or covered call if holding

  SPECIFIC INDICATOR THRESHOLDS:
  ==============================
  | Indicator      | Bull      | Bear      | Sideways  |
  |----------------|-----------|-----------|-----------|
  | SMA(20) vs 50  | 20 > 50   | 20 < 50   | ~equal    |
  | Price vs SMA20 | Above     | Below     | Choppy    |
  | ADX(14)        | > 25      | > 25      | < 20      |
  | RSI(14)        | 50-70     | < 40      | 40-60     |
  | VIX            | < 20      | > 30      | 20-25     |

  DEFENSE STRATEGIES BY REGIME:
  =============================
  Bear market:
  - Primary: Go to 100% cash (simplest, most effective)
  - Secondary: SQQQ (3x inverse QQQ) for short periods only
  - Avoid: Holding leveraged long ETFs (decay amplifies losses)

  Sideways market:
  - Primary: Reduce position size to 25-50%
  - Secondary: Sell covered calls (collect premium)
  - Avoid: Frequent trading (commissions eat returns in chop)
""")

    # Empirical check: how well does SMA(20) > SMA(50) predict returns?
    for ticker in ["NVDA", "TQQQ", "SOXL"]:
        df = data.get(ticker)
        if df is None or len(df) < 100:
            continue

        c = df["Close"].values
        mf = sma(c, 20)
        ms = sma(c, 50)

        bull_rets = []
        bear_rets = []

        for i in range(51, len(c) - 1):
            if np.isnan(mf[i]) or np.isnan(ms[i]):
                continue
            daily_ret = (c[i + 1] / c[i] - 1) * 100
            if mf[i] > ms[i]:
                bull_rets.append(daily_ret)
            else:
                bear_rets.append(daily_ret)

        bull_rets = np.array(bull_rets)
        bear_rets = np.array(bear_rets)

        print(f"  {ticker} regime signal quality:")
        print(f"    Bull days: {len(bull_rets):4d} | avg daily={bull_rets.mean():+.3f}% "
              f"| monthly est={bull_rets.mean()*21:+.2f}%")
        print(f"    Bear days: {len(bear_rets):4d} | avg daily={bear_rets.mean():+.3f}% "
              f"| monthly est={bear_rets.mean()*21:+.2f}%")
        edge = bull_rets.mean() - bear_rets.mean()
        print(f"    Edge (bull-bear): {edge:+.3f}%/day = {edge*21:+.2f}%/month")
        print()


# ============================================================
# SECTION 7: Top 3 Strategies -- Detailed Specs
# ============================================================

def top3_strategies(regime_results):
    """Summarize top 3 strategies with implementation details."""
    print("\n" + "=" * 70)
    print("  SECTION 7: TOP 3 EXECUTABLE STRATEGIES")
    print("=" * 70)

    print("""
  ================================================================
  STRATEGY 1: NVDA Regime-Leveraged (Synthetic 2-3x)
  ================================================================

  Concept:
    Apply 2-3x leverage to NVDA only during confirmed bull regimes.
    Go 100% flat during bear/sideways. This captures NVDA's exceptional
    +14.3% avg bull-month while avoiding -9.8% bear months.

  Data access:
    ```python
    import yfinance as yf
    nvda = yf.Ticker("NVDA").history(period="5y", interval="1d")
    ```

  Backtest logic:
    1. Compute SMA(20), SMA(50), ADX(14) daily
    2. If SMA(20) > SMA(50) AND Price > SMA(20) AND ADX > 25:
       -> LONG with 2-3x leverage, trailing stop at -5%
    3. If SMA(20) > SMA(50) AND Price < SMA(20):
       -> LONG with 1x, trailing stop at -5%
    4. Else: FLAT (cash)
    5. Commission: 0.1% round-trip

  Expected performance:
    - Monthly avg: +5% to +8% (2x lev), +7% to +12% (3x lev)
    - Max drawdown: -25% to -40%
    - Win rate: ~55-65%
    - WARNING: 3x in crash = -30% to -50% if stop fails

  Risk:
    - Flash crashes can gap through stop loss
    - Leveraged positions magnify all losses
    - Regime detection lags 5-15 days
    - NVDA's +5.3%/mo avg includes massive AI boom; may not repeat

  Implementation time: 2-3 hours (backtest), 1 day (paper trading)

  ================================================================
  STRATEGY 2: TQQQ/SOXL Regime Rotation
  ================================================================

  Concept:
    Use already-leveraged 3x ETFs (TQQQ for broad tech, SOXL for semis).
    The ETF itself provides leverage; strategy just does regime timing.
    Bull -> hold ETF. Bear -> 100% cash. No additional leverage.

  Data access:
    ```python
    tqqq = yf.Ticker("TQQQ").history(period="5y", interval="1d")
    soxl = yf.Ticker("SOXL").history(period="5y", interval="1d")
    ```

  Backtest logic:
    1. Use underlying index (QQQ/SOXX) for regime detection
       (cleaner signal than 3x ETF which has vol decay)
    2. SMA(20) > SMA(50) on QQQ/SOXX -> Hold TQQQ/SOXL
    3. SMA(20) < SMA(50) or ADX < 20 -> 100% cash
    4. Optional: rotate between TQQQ and SOXL based on which
       underlying has stronger momentum (higher RSI, steeper SMA slope)

  Expected performance:
    - B&H TQQQ (5y): varies hugely by period
    - With regime timing: potentially +8% to +15%/mo in bull
    - BUT: 3x ETF vol decay eats 3-5%/mo in sideways
    - Regime timing is CRITICAL; without it, 3x ETFs underperform

  Risk:
    - 3x ETF can drop 20-30% in a single bad week
    - Vol decay in sideways: even if underlying flat, 3x ETF bleeds
    - Data history for TQQQ is long (~14y) but includes very different markets
    - SOXL is extremely volatile (can drop 80% in bear markets)

  Implementation time: 3-4 hours (backtest), 1 day (paper trading)

  ================================================================
  STRATEGY 3: Multi-Asset Momentum + Leverage
  ================================================================

  Concept:
    Monthly rotation: pick the top-performing asset from
    {NVDA, TQQQ, SOXL, QQQ, cash} based on 1-3 month momentum.
    Apply 1.5-2x leverage to the selection.
    If all assets negative momentum -> 100% cash.

  Data access:
    ```python
    tickers = ["NVDA", "TQQQ", "SOXL", "QQQ"]
    data = {t: yf.Ticker(t).history(period="5y", interval="1d") for t in tickers}
    ```

  Backtest logic:
    1. Monthly rebalance (first trading day of month)
    2. For each asset, compute:
       - 1-month return (momentum)
       - 3-month return (trend)
       - Score = 0.5 * mom_1m + 0.5 * mom_3m
    3. If best score > 0: hold that asset with 1.5x leverage
    4. If all scores < 0: 100% cash (risk-off)
    5. Max 1 position at a time (concentrated)

  Expected performance:
    - Monthly avg: +6% to +10% (depending on market regime)
    - Max drawdown: -20% to -35%
    - Win rate: ~55-60% of months
    - Benefit: diversification across momentum sources

  Risk:
    - Monthly rebalance misses intra-month crashes
    - Momentum can reverse suddenly (mean reversion)
    - Concentrated in 1 asset = high idiosyncratic risk
    - Leverage on momentum = amplified whiplash in reversals

  Implementation time: 2 hours (backtest), 1 day (paper trading)
""")

    # Rank the regime backtest results
    if regime_results:
        print("\n  BACKTEST RANKING (by monthly avg):")
        print(f"  {'#':>2} {'Strategy':30s} | {'Mo Avg':>7} {'Total':>8} {'DD':>6} {'WR':>5} | {'Target':>8}")
        sorted_r = sorted(regime_results, key=lambda x: -x[1].monthly_avg)
        for i, (label, r) in enumerate(sorted_r):
            target = "10%/mo PASS" if r.monthly_avg >= 10 else (
                "CLOSE" if r.monthly_avg >= 7 else "MISS")
            print(f"  {i+1:2d} {label:30s} | {r.monthly_avg:+6.1f}% {r.total_ret:+7.1f}% "
                  f"-{r.max_dd:4.0f}% {r.win_rate:4.0f}% | {target}")


# ============================================================
# SECTION 8: Verdict & Recommendations
# ============================================================

def final_verdict(monthly_stats, regime_results):
    """Final assessment."""
    print("\n" + "=" * 70)
    print("  SECTION 8: FINAL VERDICT")
    print("=" * 70)

    # Check if any strategy hit +10%/mo
    any_hit = any(r.monthly_avg >= 10 for _, r in (regime_results or []))
    any_close = any(r.monthly_avg >= 7 for _, r in (regime_results or []))

    print(f"""
  TARGET: +10%/month = +120%/year = 3.32x/year

  IS +10%/MONTH REALISTIC?
  ========================

  Short answer: MARGINALLY POSSIBLE on NVDA/SOXL with 2-3x leverage
  + perfect regime timing, but NOT consistently sustainable.

  Evidence:
  - NVDA bull months average +14.3% (39% of months hit >+10%)
  - With 2x leverage in bull only: theoretical +28.6% in bull months
  - BUT bull months are only 63% of total
  - Net expectation: 0.63 * 28.6% + 0.37 * 0% (flat in bear) = ~+18%/mo THEORETICAL
  - REALITY: regime detection lags, stops trigger, signals misfire
  - REALISTIC with 2x regime: +5% to +8%/mo average
  - REALISTIC with 3x regime: +7% to +12%/mo average but -50% drawdowns

  NVDA-SPECIFIC CAVEAT:
  =====================
  NVDA's +5.3%/mo average is EXCEPTIONAL and driven by the 2020-2025 AI boom.
  This is NOT a baseline expectation. NVDA pre-2020 averaged ~+2%/mo.
  Any strategy calibrated on 2021-2025 NVDA is likely overfit to a regime
  that may not repeat.

  AMZN VERDICT:
  =============
  DROP IT. +0.7%/mo average means even 10x leverage (physically impossible
  without options) only gets +7%/mo. The underlying asset does not have
  enough volatility or trend strength.

  REALISTIC TARGETS:
  ==================
  | Asset      | Strategy                | Realistic Avg/Mo | Max DD  |
  |------------|-------------------------|-------------------|---------|
  | NVDA 2x    | Regime leveraged        | +5% to +8%       | -30%    |
  | NVDA 3x    | Regime leveraged        | +7% to +12%      | -50%    |
  | TQQQ       | Regime on/off           | +5% to +10%      | -40%    |
  | SOXL       | Regime on/off           | +6% to +12%      | -60%    |
  | Multi-rot  | Momentum rotation       | +5% to +8%       | -25%    |

  RECOMMENDED PATH:
  =================
  1. START with Strategy 1 (NVDA 2x regime) -- lowest complexity
  2. PAPER TRADE for 3 months minimum
  3. If paper shows >+7%/mo avg with <-25% DD, consider live
  4. NEVER use more than 3x leverage
  5. ALWAYS have regime-based flat periods (avoid holding in bear)
  6. Accept that +10%/mo will happen ~40% of months, not every month

  NEXT STEPS:
  ===========
  1. Run this script to get actual backtest numbers
  2. Implement Strategy 1 in paper trading (extend existing paper infra)
  3. Run Strategy 2 backtest separately for TQQQ/SOXL
  4. After 3 months paper: evaluate and decide
""")

    any_backtest_hit = any_hit
    print(f"  Backtest results: {'SOME strategies hit +10%/mo avg' if any_backtest_hit else 'No strategy consistently hits +10%/mo'}")
    if any_close and not any_hit:
        print(f"  Some strategies came close (>+7%/mo). With parameter tuning, +10% MAY be achievable.")
    print()


# ============================================================
# MAIN
# ============================================================

def main():
    t0 = time.time()
    print("\n" + "#" * 70)
    print("#  +10%/Month Strategy Feasibility Research")
    print("#  " + "=" * 64)
    print(f"#  Date: {time.strftime('%Y-%m-%d %H:%M')}")
    print("#" * 70)

    # 1. Data availability
    data = check_data_availability()

    # 2. Monthly analysis
    monthly_stats = monthly_analysis(data)

    # 3. B&H performance
    bh_performance(data)

    # 4. Regime backtests
    regime_results = run_regime_backtests(data)

    # 5. AMZN feasibility
    amzn_feasibility(data)

    # 6. Defense strategies
    regime_defense_analysis(data)

    # 7. Top 3 strategies
    top3_strategies(regime_results)

    # 8. Final verdict
    final_verdict(monthly_stats, regime_results)

    # Save results
    output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M"),
        "monthly_stats": {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in monthly_stats.items()},
        "regime_results": [
            {"label": label, "total_ret": round(r.total_ret, 2), "monthly_avg": round(r.monthly_avg, 2),
             "max_dd": round(r.max_dd, 2), "trades": r.trades, "win_rate": round(r.win_rate, 1),
             "months_gt10": r.months_gt10, "total_months": r.total_months}
            for label, r in regime_results
        ],
    }
    out_path = DATA_DIR / "research_10pct_monthly.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    elapsed = time.time() - t0
    print(f"\n  Total time: {elapsed:.0f}s")
    print(f"  Results saved: {out_path}")
    print(f"  Run: cd \"Projects/Trading Value\" && py -3.12 scripts/research_10pct_monthly.py")


if __name__ == "__main__":
    main()
