"""5,000-Variant Multi-Timeframe 7-Strategy Real-Time Tournament.

Single process, shared data fetch, vectorized evaluation of 5,000 parameter
variants across 6 timeframes and 7 strategy types.  Every 2 weeks the bottom
20 % are replaced by CMA-ES mutations of the top 20 %, keeping 10 % pure
random for exploration.

Usage:
    py -3.12 scripts/tournament.py

Dashboard:
    http://localhost:8895
"""
from __future__ import annotations

import http.server
import json
import math
import sys
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Auto-install dependencies
# ---------------------------------------------------------------------------
for _pkg, _imp in [("ccxt", "ccxt"), ("yfinance", "yfinance"),
                    ("scipy", "scipy")]:
    try:
        __import__(_imp)
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", _pkg])

import ccxt
import yfinance as yf
from scipy.stats.qmc import Sobol

# ---------------------------------------------------------------------------
# DL Integration (graceful fallback)
# ---------------------------------------------------------------------------
_dl_predictor = None
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from dl_integration import DLPredictor
except ImportError:
    DLPredictor = None

# ---------------------------------------------------------------------------
# Paths & Constants
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "sim_1m.sqlite"
STATE_PATH = DATA_DIR / "tournament_state.npz"
DASH_PORT = 8895
N_VARIANTS = 5000
INITIAL_BALANCE = 10_000.0
TOURNAMENT_INTERVAL_DAYS = 14
EXPLORATION_PHASE_WEEKS = 4
SAVE_INTERVAL_SEC = 3600  # save state every hour
TICK_INTERVAL_SEC = 69     # effectiveness tick every 69 seconds
MAX_TICK_HISTORY = 100     # keep last 100 ticks in memory (chart)
TICK_LOG_PATH = DATA_DIR / "effectiveness.jsonl"  # permanent log

# Timeframe definitions
TIMEFRAME_CHOICES = {0: "1m", 1: "5m", 2: "15m", 3: "1h", 4: "4h", 5: "1d"}
TIMEFRAME_MINUTES = {0: 1, 1: 5, 2: 15, 3: 60, 4: 240, 5: 1440}
TIMEFRAME_INDICES = np.arange(len(TIMEFRAME_CHOICES))

# Parameter space definition (15 dims)
PARAM_NAMES = [
    "trend_weight", "rsi_weight", "volume_weight", "momentum_weight",
    "volatility_weight", "rebalance_threshold", "max_leverage",
    "dl_weight", "check_interval", "dd_limit",
    "strategy_type", "asset_idx", "timeframe_idx",
    "grid_spacing", "pair_partner_idx",
]
# Continuous bounds (7 dims + grid_spacing = 8 continuous)
CONT_BOUNDS = np.array([
    [0.0, 0.5],   # trend_weight
    [0.0, 0.5],   # rsi_weight
    [0.0, 0.3],   # volume_weight
    [0.0, 0.5],   # momentum_weight
    [0.0, 0.3],   # volatility_weight
    [0.02, 0.15], # rebalance_threshold
    [0.5, 3.0],   # max_leverage
])
# Grid spacing bounds (continuous, separate)
GRID_SPACING_BOUNDS = [0.005, 0.05]

# Discrete choices
DL_WEIGHT_CHOICES = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
CHECK_INTERVAL_CHOICES = np.array([15, 30, 60])
DD_LIMIT_CHOICES = np.array([15, 20, 25, 30])
# Strategy types: 0-6
STRATEGY_CHOICES = np.array([0, 1, 2, 3, 4, 5, 6])
STRATEGY_NAMES = ["trend_long", "trend_both", "mean_revert", "breakout",
                  "grid", "mom_rotation", "pair"]

ASSETS = {
    # Crypto (24/7)
    "ETH": {"type": "crypto", "ccxt": "ETH/USDT:USDT", "max_lev": 2.0},
    "BTC": {"type": "crypto", "ccxt": "BTC/USDT:USDT", "max_lev": 1.5},
    "SOL": {"type": "crypto", "ccxt": "SOL/USDT:USDT", "max_lev": 2.0},
    "XRP": {"type": "crypto", "ccxt": "XRP/USDT:USDT", "max_lev": 1.5},
    # Stocks (US hours)
    "NVDA": {"type": "stock", "yf": "NVDA", "max_lev": 3.0},
    "AMZN": {"type": "stock", "yf": "AMZN", "max_lev": 2.0},
    "TSLA": {"type": "stock", "yf": "TSLA", "max_lev": 2.5},
    "GOOGL": {"type": "stock", "yf": "GOOGL", "max_lev": 2.0},
    # ETFs
    "QQQ": {"type": "stock", "yf": "QQQ", "max_lev": 2.0},
}
ASSET_NAMES = list(ASSETS.keys())
ASSET_CHOICES = np.arange(len(ASSET_NAMES))


# ===================================================================
# Signal Computation (shared, computed once per asset per timeframe)
# ===================================================================

def sma(arr: np.ndarray, w: int) -> np.ndarray:
    n = len(arr)
    out = np.full(n, np.nan)
    cs = np.cumsum(arr)
    cs = np.insert(cs, 0, 0)
    if n >= w:
        out[w - 1:] = (cs[w:] - cs[:-w]) / w
    return out


def compute_signals(c: np.ndarray, h: np.ndarray, lo: np.ndarray,
                    v: np.ndarray) -> np.ndarray | None:
    """Compute 5 signal scores from OHLCV. Returns (5,) array or None."""
    n = len(c)
    if n < 200:
        return None

    i = n - 1

    # 1. Trend alignment
    ma20 = sma(c, 20)
    ma50 = sma(c, 50)
    ma200 = sma(c, 200)
    if any(np.isnan(x[i]) for x in [ma20, ma50, ma200]):
        return None

    trend_score = 0.0
    if c[i] > ma20[i]:
        trend_score += 0.15
    if ma20[i] > ma50[i]:
        trend_score += 0.15
    if ma50[i] > ma200[i]:
        trend_score += 0.10
    if c[i] > ma200[i]:
        trend_score += 0.10
    trend_dist = (c[i] - ma200[i]) / ma200[i]
    trend_score += max(0, min(0.10, trend_dist * 2))

    # 2. RSI
    delta = np.diff(c, prepend=c[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss_arr = np.where(delta < 0, -delta, 0.0)
    avg_g = sma(gain, 14)
    avg_l = sma(loss_arr, 14)
    rsi = 50.0
    if avg_l[i] > 0:
        rsi = 100 - 100 / (1 + avg_g[i] / avg_l[i])

    rsi_score = 0.0
    if rsi < 30:
        rsi_score = 0.20
    elif rsi < 40:
        rsi_score = 0.12
    elif rsi < 50:
        rsi_score = 0.05
    elif rsi > 70:
        rsi_score = -0.15
    elif rsi > 60:
        rsi_score = -0.05

    # 3. Volume
    vol_ma = sma(v, 20)
    vol_score = 0.0
    if not np.isnan(vol_ma[i]) and vol_ma[i] > 0:
        vol_ratio = v[i] / vol_ma[i]
        if vol_ratio > 2.0:
            vol_score = 0.10
        elif vol_ratio > 1.5:
            vol_score = 0.05
        elif vol_ratio < 0.5:
            vol_score = -0.05

    # 4. Momentum
    mom_score = 0.0
    for lookback in [4, 12, 48]:
        if i >= lookback:
            ret = c[i] / c[i - lookback] - 1
            if ret > 0.02:
                mom_score += 0.03
            elif ret > 0:
                mom_score += 0.01
            elif ret < -0.02:
                mom_score -= 0.03

    # 5. ATR regime
    tr = np.maximum(h[1:] - lo[1:],
                    np.maximum(np.abs(h[1:] - c[:-1]), np.abs(lo[1:] - c[:-1])))
    tr = np.insert(tr, 0, h[0] - lo[0])
    atr = sma(tr, 14)
    atr_score = 0.0
    if not np.isnan(atr[i]) and c[i] > 0:
        atr_pct = atr[i] / c[i] * 100
        if atr_pct < 1.5:
            atr_score = 0.05
        elif atr_pct > 4.0:
            atr_score = -0.05

    return np.array([trend_score, rsi_score, vol_score, mom_score, atr_score],
                    dtype=np.float64)


def _resample_ohlcv(df_1m: pd.DataFrame, tf_minutes: int) -> pd.DataFrame:
    """Resample 1-minute OHLCV DataFrame to a higher timeframe."""
    if tf_minutes <= 1:
        return df_1m
    rule = f"{tf_minutes}min" if tf_minutes < 60 else f"{tf_minutes // 60}h"
    df = df_1m.copy()
    df.index = pd.to_datetime(df["ts"], unit="ms")
    resampled = df.resample(rule).agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum",
    }).dropna()
    return resampled.reset_index(drop=True)


# ===================================================================
# Multi-Timeframe Cache
# ===================================================================

class MultiTimeframeCache:
    """1-minute candle fetch -> auto-resample to higher timeframes."""

    def __init__(self):
        # {symbol: {tf_idx: (close, high, low, volume)}}
        self._cache: dict[str, dict[int, tuple]] = {}
        self._prices: dict[str, float] = {}
        self._last_fetch: dict[str, dict[str, int]] = {}  # {symbol: {fetch_key: ts}}

    def _should_fetch(self, symbol: str, fetch_key: str, interval_sec: int) -> bool:
        now = int(datetime.now(tz=timezone.utc).timestamp())
        bar = now // interval_sec * interval_sec
        last = self._last_fetch.get(symbol, {}).get(fetch_key, 0)
        if bar == last:
            return False
        self._last_fetch.setdefault(symbol, {})[fetch_key] = bar
        return True

    def update_crypto(self, symbol: str, ccxt_symbol: str, exchange) -> None:
        """Fetch crypto candles for multiple timeframes via resample."""
        if symbol not in self._cache:
            self._cache[symbol] = {}

        # 1m candles -> resample to 5m, 15m (fetch every minute)
        if self._should_fetch(symbol, "1m", 60):
            try:
                ohlcv = exchange.fetch_ohlcv(ccxt_symbol, "1m", limit=300)
                df = pd.DataFrame(ohlcv,
                                  columns=["ts", "open", "high", "low", "close", "volume"])
                if len(df) > 0:
                    self._prices[symbol] = float(df["close"].values[-1])
                    # tf_idx=0: 1m
                    c, h, lo, v = (df["close"].values, df["high"].values,
                                   df["low"].values, df["volume"].values)
                    self._cache[symbol][0] = (c, h, lo, v)
                    # tf_idx=1: 5m (resample)
                    df5 = _resample_ohlcv(df, 5)
                    if len(df5) >= 10:
                        self._cache[symbol][1] = (
                            df5["close"].values, df5["high"].values,
                            df5["low"].values, df5["volume"].values)
                    # tf_idx=2: 15m (resample)
                    df15 = _resample_ohlcv(df, 15)
                    if len(df15) >= 10:
                        self._cache[symbol][2] = (
                            df15["close"].values, df15["high"].values,
                            df15["low"].values, df15["volume"].values)
            except Exception as e:
                print(f"  [MTF] {symbol} 1m fetch: {e}")

        # 1h candles (fetch every hour)
        if self._should_fetch(symbol, "1h", 3600):
            try:
                ohlcv = exchange.fetch_ohlcv(ccxt_symbol, "1h", limit=300)
                df = pd.DataFrame(ohlcv,
                                  columns=["ts", "open", "high", "low", "close", "volume"])
                if len(df) > 0:
                    self._cache[symbol][3] = (
                        df["close"].values, df["high"].values,
                        df["low"].values, df["volume"].values)
            except Exception as e:
                print(f"  [MTF] {symbol} 1h fetch: {e}")

        # 4h candles (fetch every 4 hours)
        if self._should_fetch(symbol, "4h", 14400):
            try:
                ohlcv = exchange.fetch_ohlcv(ccxt_symbol, "4h", limit=300)
                df = pd.DataFrame(ohlcv,
                                  columns=["ts", "open", "high", "low", "close", "volume"])
                if len(df) > 0:
                    self._cache[symbol][4] = (
                        df["close"].values, df["high"].values,
                        df["low"].values, df["volume"].values)
            except Exception as e:
                print(f"  [MTF] {symbol} 4h fetch: {e}")

        # 1d candles (fetch every day)
        if self._should_fetch(symbol, "1d", 86400):
            try:
                ohlcv = exchange.fetch_ohlcv(ccxt_symbol, "1d", limit=300)
                df = pd.DataFrame(ohlcv,
                                  columns=["ts", "open", "high", "low", "close", "volume"])
                if len(df) > 0:
                    self._cache[symbol][5] = (
                        df["close"].values, df["high"].values,
                        df["low"].values, df["volume"].values)
            except Exception as e:
                print(f"  [MTF] {symbol} 1d fetch: {e}")

    def update_stock(self, symbol: str, yf_symbol: str) -> None:
        """Fetch stock candles (daily only)."""
        if symbol not in self._cache:
            self._cache[symbol] = {}
        try:
            df = yf.Ticker(yf_symbol).history(period="120d", interval="1d")
            if df is not None and len(df) >= 60:
                c = df["Close"].values
                h = df["High"].values
                lo = df["Low"].values
                v = df["Volume"].values
                self._prices[symbol] = float(c[-1])
                self._cache[symbol][5] = (c, h, lo, v)  # tf_idx=5 (1d)
        except Exception as e:
            print(f"  [MTF] {symbol} stock fetch: {e}")

    def get_signals(self, symbol: str, tf_idx: int) -> np.ndarray | None:
        """Compute signals for a specific symbol/timeframe. Returns (5,) or None."""
        data = self._cache.get(symbol, {}).get(tf_idx)
        if data is None:
            return None
        c, h, lo, v = data
        return compute_signals(c, h, lo, v)

    def get_price(self, symbol: str) -> float | None:
        return self._prices.get(symbol)

    def get_ohlcv(self, symbol: str, tf_idx: int) -> tuple | None:
        return self._cache.get(symbol, {}).get(tf_idx)


# ===================================================================
# Parameter Initialization (Sobol sequence)
# ===================================================================

def _generate_sobol_params() -> np.ndarray:
    """Generate (N_VARIANTS, 15) parameter matrix via Sobol sequence.

    15 dims: 7 continuous + grid_spacing(1 continuous) +
             6 discrete (dl_weight, check_interval, dd_limit, strategy_type,
                         asset_idx, timeframe_idx) + pair_partner_idx
    """
    rng = np.random.default_rng(42)

    # Sobol for 7 continuous dims
    sobol = Sobol(d=7, scramble=True, seed=42)
    raw = sobol.random(N_VARIANTS)  # (N, 7) in [0,1]

    # Scale continuous to actual bounds
    low = CONT_BOUNDS[:, 0]
    high = CONT_BOUNDS[:, 1]
    cont_params = raw * (high - low) + low  # (N, 7)

    # Build full 15-dim matrix
    params = np.zeros((N_VARIANTS, 15), dtype=np.float64)
    params[:, :7] = cont_params

    # Discrete dims: random assignment (ensures diversity)
    params[:, 7] = rng.choice(DL_WEIGHT_CHOICES, N_VARIANTS)       # dl_weight
    params[:, 8] = rng.choice(CHECK_INTERVAL_CHOICES, N_VARIANTS)  # check_interval
    params[:, 9] = rng.choice(DD_LIMIT_CHOICES, N_VARIANTS)        # dd_limit
    params[:, 10] = rng.choice(STRATEGY_CHOICES, N_VARIANTS)       # strategy_type
    params[:, 11] = rng.choice(ASSET_CHOICES, N_VARIANTS)          # asset_idx
    params[:, 12] = rng.choice(TIMEFRAME_INDICES, N_VARIANTS)      # timeframe_idx

    # Force stocks to daily only (tf_idx=5)
    for i in range(N_VARIANTS):
        asset_idx = int(params[i, 11])
        sym = ASSET_NAMES[asset_idx]
        if ASSETS[sym]["type"] == "stock":
            params[i, 12] = 5  # 1d

    # grid_spacing: continuous [0.005, 0.05]
    params[:, 13] = rng.uniform(GRID_SPACING_BOUNDS[0], GRID_SPACING_BOUNDS[1],
                                N_VARIANTS)
    # pair_partner_idx: discrete [0, len(ASSETS)-1]
    params[:, 14] = rng.integers(0, len(ASSET_NAMES), N_VARIANTS)

    return params


# ===================================================================
# Virtual Portfolio (Struct of Arrays)
# ===================================================================

@dataclass
class VirtualPortfolio:
    """Tracks 5,000 virtual portfolios using struct-of-arrays."""

    balances: np.ndarray = field(default=None)
    positions: np.ndarray = field(default=None)     # current size (0 = flat)
    entry_prices: np.ndarray = field(default=None)
    peak_balances: np.ndarray = field(default=None)
    trade_counts: np.ndarray = field(default=None)
    win_counts: np.ndarray = field(default=None)
    trade_pnls: list = field(default=None)           # list[list[float]]
    recent_pnls: list = field(default=None)          # last 50 trades per variant

    def __post_init__(self):
        if self.balances is None:
            self.reset()

    def reset(self):
        self.balances = np.full(N_VARIANTS, INITIAL_BALANCE)
        self.positions = np.zeros(N_VARIANTS)
        self.entry_prices = np.zeros(N_VARIANTS)
        self.peak_balances = np.full(N_VARIANTS, INITIAL_BALANCE)
        self.trade_counts = np.zeros(N_VARIANTS, dtype=np.int32)
        self.win_counts = np.zeros(N_VARIANTS, dtype=np.int32)
        self.trade_pnls = [[] for _ in range(N_VARIANTS)]
        self.recent_pnls = [[] for _ in range(N_VARIANTS)]

    def update_subset(self, indices: np.ndarray, target_sizes: np.ndarray,
                      price: float, rebalance_thresholds: np.ndarray,
                      dd_limits: np.ndarray, comm: float = 0.0005):
        """Update a SUBSET of variants (those assigned to a specific asset)."""
        idx = indices
        if len(idx) == 0:
            return
        # DD-based scaling
        dd_pct = np.where(
            self.peak_balances[idx] > 0,
            (self.peak_balances[idx] - self.balances[idx]) / self.peak_balances[idx] * 100,
            0.0,
        )
        scale = np.ones(len(idx))
        scale = np.where(dd_pct > dd_limits, 0.25, scale)
        scale = np.where((dd_pct > dd_limits * 0.6) & (scale == 1.0), 0.50, scale)
        target_sizes = target_sizes * scale

        size_diff = np.abs(target_sizes - self.positions[idx])
        needs_rebal = (size_diff > rebalance_thresholds) | (
            (target_sizes == 0) & (self.positions[idx] > 0)
        )

        has_pos = (np.abs(self.positions[idx]) > 0) & (self.entry_prices[idx] > 0) & needs_rebal
        if np.any(has_pos):
            pnl = np.where(
                has_pos,
                (price / np.where(self.entry_prices[idx] > 0, self.entry_prices[idx], 1.0) - 1)
                * self.positions[idx] - comm * np.abs(self.positions[idx]),
                0.0,
            )
            self.balances[idx] = np.where(has_pos, self.balances[idx] * (1 + pnl), self.balances[idx])
            self.balances[idx] = np.maximum(self.balances[idx], 0.0)
            closed_local = np.where(has_pos)[0]
            for ci in closed_local:
                pnl_val = float(pnl[ci])
                self.trade_pnls[idx[ci]].append(pnl_val)
                # Track recent pnls (last 50)
                self.recent_pnls[idx[ci]].append(pnl_val)
                if len(self.recent_pnls[idx[ci]]) > 50:
                    self.recent_pnls[idx[ci]] = self.recent_pnls[idx[ci]][-50:]
            self.trade_counts[idx] += has_pos.astype(np.int32)
            self.win_counts[idx] += (has_pos & (pnl > 0)).astype(np.int32)
            self.peak_balances[idx] = np.maximum(self.peak_balances[idx], self.balances[idx])

        opening = needs_rebal & (np.abs(target_sizes) > 0)
        self.positions[idx] = np.where(needs_rebal, target_sizes, self.positions[idx])
        self.entry_prices[idx] = np.where(opening, price, self.entry_prices[idx])
        self.entry_prices[idx] = np.where(
            needs_rebal & (target_sizes == 0), 0.0, self.entry_prices[idx]
        )

    def returns_pct(self) -> np.ndarray:
        """Per-variant return %."""
        return (self.balances / INITIAL_BALANCE - 1) * 100

    def drawdowns_pct(self) -> np.ndarray:
        return np.where(
            self.peak_balances > 0,
            (self.peak_balances - self.balances) / self.peak_balances * 100,
            0.0,
        )

    def win_rates(self) -> np.ndarray:
        return np.where(self.trade_counts > 0,
                        self.win_counts / self.trade_counts * 100, 0.0)


# ===================================================================
# Deflated Sharpe Ratio (kept for reference, CTS is primary now)
# ===================================================================

def deflated_sharpe_ratios(portfolio: VirtualPortfolio) -> np.ndarray:
    """Compute DSR for ranking.  Penalizes low trade count & short history."""
    n = N_VARIANTS
    dsr = np.zeros(n)
    for i in range(n):
        pnls = portfolio.trade_pnls[i]
        if len(pnls) < 5:
            dsr[i] = -999.0
            continue
        arr = np.array(pnls)
        mu = arr.mean()
        std = arr.std()
        if std < 1e-12:
            dsr[i] = 0.0
            continue
        sr = mu / std
        # Bailey & Lopez de Prado haircut
        T = len(arr)
        skew = float(((arr - mu) ** 3).mean() / std ** 3) if std > 0 else 0.0
        kurt = float(((arr - mu) ** 4).mean() / std ** 4) if std > 0 else 3.0
        sr_std = np.sqrt((1 + 0.5 * sr ** 2 - skew * sr
                          + (kurt - 3) / 4 * sr ** 2) / max(T, 1))
        # DSR = SR - penalty
        dsr[i] = sr - sr_std * 1.0  # 1-sigma haircut
    return dsr


# ===================================================================
# Composite Tournament Score (CTS)
# ===================================================================

def composite_tournament_scores(portfolio: VirtualPortfolio) -> np.ndarray:
    """CTS = 0.35*Calmar_norm + 0.25*Sortino_norm + 0.20*Consistency
           + 0.10*DSR_norm + 0.10*Freq_bonus"""
    n = N_VARIANTS
    calmar = np.zeros(n)
    sortino = np.zeros(n)
    consistency = np.zeros(n)
    dsr_raw = np.zeros(n)
    freq = np.zeros(n)

    rets = portfolio.returns_pct()
    dds = portfolio.drawdowns_pct()

    for i in range(n):
        pnls = portfolio.trade_pnls[i]
        tc = int(portfolio.trade_counts[i])

        if tc < 5:
            calmar[i] = -999.0
            sortino[i] = -999.0
            consistency[i] = -999.0
            dsr_raw[i] = -999.0
            freq[i] = 0.0
            continue

        arr = np.array(pnls)
        mu = arr.mean()

        # Calmar = annualized_return / max(max_drawdown, 0.01)
        ann_ret = rets[i]  # already in %
        max_dd = max(float(dds[i]), 0.01)
        calmar[i] = ann_ret / max_dd

        # Sortino = mean(pnls) / downside_std
        neg = arr[arr < 0]
        down_std = float(neg.std()) if len(neg) > 1 else 1e-6
        down_std = max(down_std, 1e-6)
        sortino[i] = mu / down_std

        # Consistency = recent_wr * 0.6 + total_wr * 0.4 - abs(diff) * 0.5
        total_wr = float(portfolio.win_counts[i]) / max(tc, 1)
        recent = portfolio.recent_pnls[i]
        if len(recent) > 0:
            recent_wins = sum(1 for p in recent if p > 0)
            recent_wr = recent_wins / len(recent)
        else:
            recent_wr = total_wr
        consistency[i] = recent_wr * 0.6 + total_wr * 0.4 - abs(recent_wr - total_wr) * 0.5

        # DSR
        std = arr.std()
        if std > 1e-12:
            sr = mu / std
            T = len(arr)
            skew = float(((arr - mu) ** 3).mean() / std ** 3)
            kurt = float(((arr - mu) ** 4).mean() / std ** 4)
            sr_std = np.sqrt((1 + 0.5 * sr ** 2 - skew * sr
                              + (kurt - 3) / 4 * sr ** 2) / max(T, 1))
            dsr_raw[i] = sr - sr_std
        else:
            dsr_raw[i] = 0.0

        # Freq bonus
        freq[i] = min(tc / 100.0, 1.0)

    # Normalize each component to [0, 1] among eligible
    def _norm(arr: np.ndarray) -> np.ndarray:
        eligible = arr > -900
        if eligible.sum() < 2:
            return np.zeros_like(arr)
        lo = arr[eligible].min()
        hi = arr[eligible].max()
        if hi - lo < 1e-12:
            return np.where(eligible, 0.5, 0.0)
        normed = np.where(eligible, (arr - lo) / (hi - lo), 0.0)
        return normed

    calmar_n = _norm(calmar)
    sortino_n = _norm(sortino)
    consist_n = _norm(consistency)
    dsr_n = _norm(dsr_raw)

    cts = (0.35 * calmar_n + 0.25 * sortino_n + 0.20 * consist_n
           + 0.10 * dsr_n + 0.10 * freq)
    return cts


# ===================================================================
# CMA-ES Mutation (15-dim)
# ===================================================================

def cma_es_mutate(elite_params: np.ndarray, n_children: int,
                  rng: np.random.Generator) -> np.ndarray:
    """Generate children from elite parents via simplified CMA-ES (15 dims)."""
    mean = elite_params.mean(axis=0)
    if len(elite_params) < 2:
        cov = np.eye(7) * 0.01
    else:
        cov = np.cov(elite_params[:, :7].T)
        cov += np.eye(7) * 1e-6  # regularize

    children = np.zeros((n_children, 15))
    # Continuous dims: sample from N(mean, cov)
    children[:, :7] = rng.multivariate_normal(mean[:7], cov, size=n_children)
    # Clamp to bounds
    for j in range(7):
        children[:, j] = np.clip(children[:, j],
                                 CONT_BOUNDS[j, 0], CONT_BOUNDS[j, 1])

    # Discrete dims: inherit from random parent + small mutation chance
    parent_idx = rng.integers(0, len(elite_params), size=n_children)
    children[:, 7] = elite_params[parent_idx, 7]    # dl_weight
    children[:, 8] = elite_params[parent_idx, 8]    # check_interval
    children[:, 9] = elite_params[parent_idx, 9]    # dd_limit
    children[:, 10] = elite_params[parent_idx, 10]  # strategy_type
    children[:, 11] = elite_params[parent_idx, 11]  # asset_idx
    children[:, 12] = elite_params[parent_idx, 12]  # timeframe_idx

    # grid_spacing: inherit + Gaussian noise
    children[:, 13] = elite_params[parent_idx, 13]
    children[:, 13] += rng.normal(0, 0.005, n_children)
    children[:, 13] = np.clip(children[:, 13], GRID_SPACING_BOUNDS[0],
                               GRID_SPACING_BOUNDS[1])

    # pair_partner_idx: inherit
    children[:, 14] = elite_params[parent_idx, 14]

    # 20% chance to mutate each discrete dim
    for ci in range(n_children):
        if rng.random() < 0.2:
            children[ci, 7] = rng.choice(DL_WEIGHT_CHOICES)
        if rng.random() < 0.2:
            children[ci, 8] = rng.choice(CHECK_INTERVAL_CHOICES)
        if rng.random() < 0.2:
            children[ci, 9] = rng.choice(DD_LIMIT_CHOICES)
        if rng.random() < 0.2:
            children[ci, 10] = rng.choice(STRATEGY_CHOICES)
        if rng.random() < 0.2:
            children[ci, 11] = rng.choice(ASSET_CHOICES)
        if rng.random() < 0.2:
            children[ci, 12] = rng.choice(TIMEFRAME_INDICES)
        if rng.random() < 0.2:
            children[ci, 14] = rng.integers(0, len(ASSET_NAMES))

        # Force stocks to daily
        asset_idx = int(children[ci, 11])
        sym = ASSET_NAMES[asset_idx]
        if ASSETS[sym]["type"] == "stock":
            children[ci, 12] = 5

    return children


# ===================================================================
# Tournament Manager
# ===================================================================

class TournamentManager:
    def __init__(self):
        self.rng = np.random.default_rng(2026)
        self.generation = 0
        self.started_at = datetime.now(tz=timezone.utc)
        self.last_tournament = self.started_at
        self.params = _generate_sobol_params()       # (5000, 15)
        self.portfolio = VirtualPortfolio()
        self.ensemble_top_idx: np.ndarray = np.arange(10)  # top-10 indices
        self.ensemble_signal: float = 0.0
        self._last_save = time.monotonic()
        self._last_tick = time.monotonic()
        self.tick_history: list[dict] = []  # 69-second effectiveness ticks

        # Multi-timeframe cache
        self.mtf_cache = MultiTimeframeCache()

        # DL predictor
        self._dl_prob: dict[str, float] = {}
        global _dl_predictor
        if DLPredictor is not None:
            try:
                _dl_predictor = DLPredictor(str(DATA_DIR))
                models = _dl_predictor.available_models()
                print(f"  [DL] Models loaded: {models if models else 'none yet'}")
            except Exception as e:
                print(f"  [DL] Init failed (rules only): {e}")
                _dl_predictor = None
        else:
            print("  [DL] dl_integration not available, rules only")

        # Exchange
        self.exchange = ccxt.binance(
            {"options": {"defaultType": "future"}, "timeout": 10000}
        )
        self.exchange.load_markets()

        # Try resume
        self._try_resume()

    # ---- State persistence ----

    def _try_resume(self):
        if not STATE_PATH.exists():
            print(f"[Tournament] Fresh start: {N_VARIANTS} variants")
            return
        try:
            data = np.load(str(STATE_PATH), allow_pickle=True)
            loaded_params = data["params"]
            # Handle dimension migration (12 -> 15)
            if loaded_params.shape[1] < 15:
                old_n = loaded_params.shape[0]
                new_params = np.zeros((old_n, 15), dtype=np.float64)
                new_params[:, :loaded_params.shape[1]] = loaded_params
                # Initialize new dims with defaults
                rng = np.random.default_rng(99)
                if loaded_params.shape[1] <= 12:
                    new_params[:, 12] = rng.choice(TIMEFRAME_INDICES, old_n)
                if loaded_params.shape[1] <= 13:
                    new_params[:, 13] = rng.uniform(
                        GRID_SPACING_BOUNDS[0], GRID_SPACING_BOUNDS[1], old_n)
                if loaded_params.shape[1] <= 14:
                    new_params[:, 14] = rng.integers(0, len(ASSET_NAMES), old_n)
                # Force stocks to daily
                for i in range(old_n):
                    aidx = int(new_params[i, 11])
                    if aidx < len(ASSET_NAMES) and ASSETS[ASSET_NAMES[aidx]]["type"] == "stock":
                        new_params[i, 12] = 5
                loaded_params = new_params
                print(f"[Tournament] Migrated params {data['params'].shape[1]} -> 15 dims")

            # Handle N_VARIANTS change
            old_n = loaded_params.shape[0]
            if old_n != N_VARIANTS:
                print(f"[Tournament] Resizing {old_n} -> {N_VARIANTS} variants")
                new_params = _generate_sobol_params()
                copy_n = min(old_n, N_VARIANTS)
                new_params[:copy_n] = loaded_params[:copy_n]
                self.params = new_params
                # Resize portfolio arrays
                self.portfolio.reset()
                for attr in ["balances", "positions", "entry_prices",
                             "peak_balances", "trade_counts", "win_counts"]:
                    old_arr = data.get(attr)
                    if old_arr is not None:
                        new_arr = getattr(self.portfolio, attr)
                        new_arr[:copy_n] = old_arr[:copy_n]
                if "trade_pnls" in data:
                    pnls_obj = data["trade_pnls"]
                    for i in range(min(copy_n, len(pnls_obj))):
                        self.portfolio.trade_pnls[i] = list(pnls_obj[i])
                        # Populate recent_pnls from last 50
                        self.portfolio.recent_pnls[i] = list(pnls_obj[i])[-50:]
            else:
                self.params = loaded_params
                self.portfolio.balances = data["balances"]
                self.portfolio.positions = data["positions"]
                self.portfolio.entry_prices = data["entry_prices"]
                self.portfolio.peak_balances = data["peak_balances"]
                self.portfolio.trade_counts = data["trade_counts"]
                self.portfolio.win_counts = data["win_counts"]
                if "trade_pnls" in data:
                    pnls_obj = data["trade_pnls"]
                    self.portfolio.trade_pnls = [list(p) for p in pnls_obj]
                    self.portfolio.recent_pnls = [list(p)[-50:] for p in pnls_obj]
                else:
                    self.portfolio.recent_pnls = [[] for _ in range(N_VARIANTS)]

            self.generation = int(data.get("generation", 0))
            ts = data.get("started_at", None)
            if ts is not None:
                self.started_at = datetime.fromisoformat(str(ts))
            lt = data.get("last_tournament", None)
            if lt is not None:
                self.last_tournament = datetime.fromisoformat(str(lt))
            if "ensemble_top_idx" in data:
                self.ensemble_top_idx = data["ensemble_top_idx"]
            print(f"[Tournament] Resumed gen={self.generation}, "
                  f"avg_ret={self.portfolio.returns_pct().mean():.1f}%")
        except Exception as e:
            print(f"[Tournament] Resume failed ({e}), fresh start")
            self.params = _generate_sobol_params()
            self.portfolio.reset()

    def save_state(self):
        pnls_arr = np.empty(N_VARIANTS, dtype=object)
        for i in range(N_VARIANTS):
            pnls_arr[i] = np.array(self.portfolio.trade_pnls[i], dtype=np.float64)
        np.savez_compressed(
            str(STATE_PATH),
            params=self.params,
            balances=self.portfolio.balances,
            positions=self.portfolio.positions,
            entry_prices=self.portfolio.entry_prices,
            peak_balances=self.portfolio.peak_balances,
            trade_counts=self.portfolio.trade_counts,
            win_counts=self.portfolio.win_counts,
            trade_pnls=pnls_arr,
            generation=self.generation,
            started_at=self.started_at.isoformat(),
            last_tournament=self.last_tournament.isoformat(),
            ensemble_top_idx=self.ensemble_top_idx,
        )

    def _maybe_save(self):
        now = time.monotonic()
        if now - self._last_save >= SAVE_INTERVAL_SEC:
            self.save_state()
            self._last_save = now
            print(f"[Tournament] State saved (gen={self.generation})")

    def _maybe_tick(self):
        """Record a 69-second effectiveness tick."""
        now = time.monotonic()
        if now - self._last_tick < TICK_INTERVAL_SEC:
            return
        self._last_tick = now

        rets = self.portfolio.returns_pct()
        top_rets = rets[self.ensemble_top_idx] if len(self.ensemble_top_idx) > 0 else rets[:10]
        total_trades = int(self.portfolio.trade_counts.sum())

        tick = {
            "t": datetime.now(tz=timezone.utc).strftime("%H:%M:%S"),
            "best": round(float(rets.max()), 3),
            "top10_avg": round(float(top_rets.mean()), 3),
            "avg": round(float(rets.mean()), 3),
            "worst": round(float(rets.min()), 3),
            "trades": total_trades,
            "positive_pct": round(float((rets > 0).sum() / max(len(rets), 1) * 100), 1),
        }
        self.tick_history.append(tick)
        if len(self.tick_history) > MAX_TICK_HISTORY:
            self.tick_history = self.tick_history[-MAX_TICK_HISTORY:]

        # Permanent log (append)
        try:
            with open(TICK_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(tick) + "\n")
        except Exception:
            pass

    # ---- Data fetching ----

    def _is_us_open(self) -> bool:
        from zoneinfo import ZoneInfo
        now = datetime.now(tz=ZoneInfo("America/New_York"))
        if now.weekday() >= 5:
            return False
        return 9 <= now.hour < 16

    def fetch_all(self):
        """Fetch data for all assets using multi-timeframe cache."""
        for sym, cfg in ASSETS.items():
            if cfg["type"] == "crypto":
                self.mtf_cache.update_crypto(sym, cfg["ccxt"], self.exchange)
            else:
                if not self._is_us_open():
                    continue
                self.mtf_cache.update_stock(sym, cfg["yf"])

            # DL probability (use best available OHLCV)
            price = self.mtf_cache.get_price(sym)
            if price is not None:
                dl_prob = 0.0
                if _dl_predictor is not None:
                    # Use 15m or 1d data for DL
                    tf_for_dl = 2 if cfg["type"] == "crypto" else 5
                    ohlcv = self.mtf_cache.get_ohlcv(sym, tf_for_dl)
                    if ohlcv is not None:
                        c, h, lo, v = ohlcv
                        try:
                            dl_prob = _dl_predictor.predict(sym, c, h, lo, v)
                        except Exception:
                            pass
                self._dl_prob[sym] = dl_prob
                print(f"  [{sym}] price=${price:,.2f}")

    # ---- Vectorized evaluation ----

    def evaluate_all(self):
        """Evaluate all 5,000 variants. Each variant uses its assigned asset+timeframe."""
        asset_indices = self.params[:, 11].astype(int)   # (5000,)
        strategy_types = self.params[:, 10].astype(int)  # (5000,)
        tf_indices = self.params[:, 12].astype(int)      # (5000,)

        # Pre-compute momentum rankings for mom_rotation strategy (5)
        mom_rankings = self._compute_momentum_rankings()

        for asset_idx, sym in enumerate(ASSET_NAMES):
            price = self.mtf_cache.get_price(sym)
            if price is None:
                continue

            cfg = ASSETS[sym]
            comm = 0.0005 if cfg["type"] == "crypto" else 0.001
            dl_prob = self._dl_prob.get(sym, 0.0)

            # Mask: only variants assigned to this asset
            asset_mask = asset_indices == asset_idx
            if not asset_mask.any():
                continue

            # Group by timeframe within this asset
            unique_tfs = np.unique(tf_indices[asset_mask])
            for tf_idx in unique_tfs:
                tf_idx = int(tf_idx)
                signals = self.mtf_cache.get_signals(sym, tf_idx)
                if signals is None:
                    continue

                # Mask: variants for this asset AND this timeframe
                mask = asset_mask & (tf_indices == tf_idx)
                if not mask.any():
                    continue

                indices = np.where(mask)[0]
                n_sub = len(indices)
                strats = strategy_types[indices]
                weight_matrix = self.params[indices, :5]  # (n_sub, 5)

                # Base conviction from weighted signals
                raw_convictions = weight_matrix @ signals

                # === Strategy type modifiers ===

                # mean_reversion (type 2): invert RSI and momentum
                mr_mask = strats == 2
                if mr_mask.any():
                    raw_convictions[mr_mask] = (
                        weight_matrix[mr_mask] @ (signals * np.array([1, -1, 1, -1, 1]))
                    )

                # breakout (type 3): boost momentum, reduce RSI
                bo_mask = strats == 3
                if bo_mask.any():
                    raw_convictions[bo_mask] = (
                        weight_matrix[bo_mask] @ (signals * np.array([1.5, 0.5, 1.5, 1.5, 0.5]))
                    )

                # grid (type 4): sideways detection -> grid trading
                grid_mask = strats == 4
                if grid_mask.any():
                    grid_conv = self._eval_grid_strategy(
                        indices[grid_mask], signals, price)
                    raw_convictions[grid_mask] = grid_conv

                # momentum_rotation (type 5): rank-based
                mr5_mask = strats == 5
                if mr5_mask.any():
                    mom_conv = self._eval_mom_rotation(
                        sym, mom_rankings, indices[mr5_mask])
                    raw_convictions[mr5_mask] = mom_conv

                # pair (type 6): pair Z-score mean reversion
                pair_mask = strats == 6
                if pair_mask.any():
                    pair_conv = self._eval_pair_strategy(
                        sym, indices[pair_mask])
                    raw_convictions[pair_mask] = pair_conv

                # DL boost
                dl_boost = self.params[indices, 7] * dl_prob
                convictions = np.clip(raw_convictions + dl_boost, 0.0, 1.0)

                # Short allowed (type 1): allow negative conviction
                short_mask = strats == 1
                if short_mask.any():
                    short_conv = (weight_matrix[short_mask] @ signals
                                  + self.params[indices[short_mask], 7] * dl_prob)
                    convictions[short_mask] = np.clip(short_conv, -1.0, 1.0)

                target_sizes = convictions * self.params[indices, 6]

                self.portfolio.update_subset(
                    indices, target_sizes, price,
                    rebalance_thresholds=self.params[indices, 5],
                    dd_limits=self.params[indices, 9],
                    comm=comm,
                )

        self._update_ensemble()

    def _compute_momentum_rankings(self) -> dict[str, int]:
        """Compute momentum ranking across all assets. Returns {sym: rank}."""
        mom_scores = {}
        for sym in ASSET_NAMES:
            # Use daily or 1h data for ranking
            tf = 5 if ASSETS[sym]["type"] == "stock" else 3
            ohlcv = self.mtf_cache.get_ohlcv(sym, tf)
            if ohlcv is None:
                # Try 15m
                ohlcv = self.mtf_cache.get_ohlcv(sym, 2)
            if ohlcv is not None:
                c = ohlcv[0]
                if len(c) >= 20:
                    mom_scores[sym] = float(c[-1] / c[-20] - 1)
                else:
                    mom_scores[sym] = 0.0
            else:
                mom_scores[sym] = 0.0

        # Rank: higher momentum = lower rank number (1=best)
        sorted_syms = sorted(mom_scores.keys(), key=lambda s: mom_scores[s], reverse=True)
        rankings = {s: rank for rank, s in enumerate(sorted_syms)}
        return rankings

    def _eval_grid_strategy(self, grid_indices: np.ndarray,
                            signals: np.ndarray, price: float) -> np.ndarray:
        """Grid strategy: trade reversals at grid_spacing from entry.
        Low trend + low momentum = sideways = grid trading opportunity."""
        n = len(grid_indices)
        # Sideways detection: low absolute trend and momentum signals
        sideways_score = 1.0 - abs(signals[0]) - abs(signals[3])
        sideways_score = max(0.0, min(1.0, sideways_score))

        convictions = np.zeros(n)
        grid_spacings = self.params[grid_indices, 13]
        entry_prices = self.portfolio.entry_prices[grid_indices]

        for j in range(n):
            gs = grid_spacings[j]
            ep = entry_prices[j]
            if ep > 0 and price > 0:
                price_move = (price - ep) / ep
                if price_move > gs:
                    # Price moved up past grid -> sell (negative conviction)
                    convictions[j] = -sideways_score * 0.5
                elif price_move < -gs:
                    # Price moved down past grid -> buy
                    convictions[j] = sideways_score * 0.5
                else:
                    convictions[j] = 0.0
            else:
                # No position: enter with mild conviction if sideways
                convictions[j] = sideways_score * 0.3

        return convictions

    def _eval_mom_rotation(self, symbol: str, rankings: dict[str, int],
                           indices: np.ndarray) -> np.ndarray:
        """Momentum rotation: top 3 ranked symbols get positive conviction."""
        rank = rankings.get(symbol, len(ASSET_NAMES))
        n = len(indices)
        if rank < 3:
            # Top 3: conviction based on rank
            return np.full(n, 0.5 - rank * 0.1)
        else:
            return np.zeros(n)

    def _eval_pair_strategy(self, symbol: str,
                            pair_indices: np.ndarray) -> np.ndarray:
        """Pair trading: Z-score of price ratio between asset and partner."""
        n = len(pair_indices)
        convictions = np.zeros(n)
        cfg = ASSETS[symbol]
        asset_type = cfg["type"]

        for j in range(n):
            global_idx = pair_indices[j]
            partner_idx = int(self.params[global_idx, 14]) % len(ASSET_NAMES)
            partner_sym = ASSET_NAMES[partner_idx]

            # Only pair within same type (crypto-crypto, stock-stock)
            if ASSETS[partner_sym]["type"] != asset_type:
                convictions[j] = 0.0
                continue
            if partner_sym == symbol:
                convictions[j] = 0.0
                continue

            price_a = self.mtf_cache.get_price(symbol)
            price_b = self.mtf_cache.get_price(partner_sym)
            if price_a is None or price_b is None or price_b == 0:
                continue

            # Get historical close data for ratio computation
            tf = 5 if asset_type == "stock" else 3  # 1d or 1h
            ohlcv_a = self.mtf_cache.get_ohlcv(symbol, tf)
            ohlcv_b = self.mtf_cache.get_ohlcv(partner_sym, tf)
            if ohlcv_a is None or ohlcv_b is None:
                continue

            c_a, c_b = ohlcv_a[0], ohlcv_b[0]
            min_len = min(len(c_a), len(c_b))
            if min_len < 20:
                continue

            ratio = c_a[-min_len:] / np.where(c_b[-min_len:] > 0, c_b[-min_len:], 1.0)
            r_mean = ratio.mean()
            r_std = ratio.std()
            if r_std < 1e-12:
                continue

            z = (ratio[-1] - r_mean) / r_std
            # Mean reversion: if |Z| > 2, trade towards the mean
            if z > 2.0:
                convictions[j] = -0.5  # ratio too high -> short A
            elif z < -2.0:
                convictions[j] = 0.5   # ratio too low -> long A
            elif abs(z) > 1.0:
                convictions[j] = -0.2 * np.sign(z)

        return convictions

    def _update_ensemble(self):
        """Compute ensemble signal from top-10 variants."""
        if len(self.ensemble_top_idx) == 0:
            self.ensemble_signal = 0.0
            return
        top_positions = self.portfolio.positions[self.ensemble_top_idx]
        self.ensemble_signal = float(np.mean(top_positions))

    # ---- Tournament round ----

    def maybe_run_tournament(self):
        """Check if it's time for a tournament round."""
        now = datetime.now(tz=timezone.utc)
        weeks_elapsed = (now - self.started_at).days / 7

        # Phase 1: exploration (no elimination)
        if weeks_elapsed < EXPLORATION_PHASE_WEEKS:
            return

        # Phase 2: biweekly tournament
        days_since = (now - self.last_tournament).days
        if days_since < TOURNAMENT_INTERVAL_DAYS:
            return

        self._run_tournament_round()
        self.last_tournament = now

    def _run_tournament_round(self):
        """Execute one tournament round: rank by CTS, eliminate, mutate, replenish."""
        self.generation += 1
        print(f"\n{'='*60}")
        print(f"[Tournament] Round {self.generation}")
        print(f"{'='*60}")

        cts = composite_tournament_scores(self.portfolio)

        # Only consider variants with >= 30 trades
        eligible = self.portfolio.trade_counts >= 30
        n_eligible = eligible.sum()
        if n_eligible < 50:
            print(f"  Only {n_eligible} eligible (need 50+). Skipping round.")
            return

        # Rank eligible by CTS
        eligible_idx = np.where(eligible)[0]
        eligible_cts = cts[eligible_idx]
        sorted_order = np.argsort(eligible_cts)[::-1]
        ranked_idx = eligible_idx[sorted_order]

        n_elig = len(ranked_idx)
        n_eliminate = int(n_elig * 0.20)
        n_elite = int(n_elig * 0.20)
        n_random = max(1, int(N_VARIANTS * 0.10))

        # Top 10 -> ensemble
        self.ensemble_top_idx = ranked_idx[:10].copy()
        top_rets = self.portfolio.returns_pct()[self.ensemble_top_idx]
        print(f"  Top 10 avg return: {top_rets.mean():.1f}%")

        # Bottom 20% to eliminate
        eliminate_idx = ranked_idx[-n_eliminate:]

        # Elite parents for CMA-ES
        elite_idx = ranked_idx[:n_elite]
        elite_params = self.params[elite_idx]

        # Generate children
        n_children = n_eliminate - n_random
        if n_children > 0:
            children = cma_es_mutate(elite_params, n_children, self.rng)
            self.params[eliminate_idx[:n_children]] = children

        # Fill remaining with pure random
        if n_random > 0:
            random_idx = eliminate_idx[n_children:n_children + n_random]
            for ri in random_idx:
                for j in range(7):
                    self.params[ri, j] = self.rng.uniform(
                        CONT_BOUNDS[j, 0], CONT_BOUNDS[j, 1]
                    )
                self.params[ri, 7] = self.rng.choice(DL_WEIGHT_CHOICES)
                self.params[ri, 8] = self.rng.choice(CHECK_INTERVAL_CHOICES)
                self.params[ri, 9] = self.rng.choice(DD_LIMIT_CHOICES)
                self.params[ri, 10] = self.rng.choice(STRATEGY_CHOICES)
                self.params[ri, 11] = self.rng.choice(ASSET_CHOICES)
                self.params[ri, 12] = self.rng.choice(TIMEFRAME_INDICES)
                self.params[ri, 13] = self.rng.uniform(
                    GRID_SPACING_BOUNDS[0], GRID_SPACING_BOUNDS[1])
                self.params[ri, 14] = self.rng.integers(0, len(ASSET_NAMES))
                # Force stocks to daily
                asset_idx = int(self.params[ri, 11])
                if ASSETS[ASSET_NAMES[asset_idx]]["type"] == "stock":
                    self.params[ri, 12] = 5

        # Reset replaced variants' portfolios
        for ri in eliminate_idx:
            self.portfolio.balances[ri] = INITIAL_BALANCE
            self.portfolio.positions[ri] = 0.0
            self.portfolio.entry_prices[ri] = 0.0
            self.portfolio.peak_balances[ri] = INITIAL_BALANCE
            self.portfolio.trade_counts[ri] = 0
            self.portfolio.win_counts[ri] = 0
            self.portfolio.trade_pnls[ri] = []
            self.portfolio.recent_pnls[ri] = []

        rets = self.portfolio.returns_pct()
        print(f"  Eliminated {n_eliminate} | "
              f"Avg ret: {rets.mean():.1f}% | "
              f"Best: {rets.max():.1f}% | Worst: {rets.min():.1f}%")
        print(f"{'='*60}\n")

        self.save_state()

    # ---- Main loop ----

    def run_forever(self):
        print(f"[Tournament] {N_VARIANTS} variants | Dashboard: "
              f"http://localhost:{DASH_PORT}")
        print(f"[Tournament] Gen={self.generation}, "
              f"avg_ret={self.portfolio.returns_pct().mean():.1f}%")

        while True:
            try:
                self.fetch_all()
                self.evaluate_all()
                self.maybe_run_tournament()
                self._maybe_save()
                self._maybe_tick()
            except KeyboardInterrupt:
                print("\n[Tournament] Shutting down, saving state...")
                self.save_state()
                break
            except Exception as e:
                print(f"[Tournament] Error: {e}")

            time.sleep(60)  # check every minute, MTF cache handles timing


# ===================================================================
# Dashboard (localhost:8895)
# ===================================================================

_manager: TournamentManager | None = None

DASH_HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<title>Strategy Tournament (5,000)</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e0e0;font-family:'Segoe UI',system-ui,monospace;font-size:12px}
.hdr{background:#141926;padding:12px 24px;border-bottom:1px solid #2a3040;display:flex;justify-content:space-between;align-items:center}
.hdr h1{font-size:15px;color:#ff9800}
.wrap{padding:14px 24px;max-width:1400px;margin:0 auto}
.gn{color:#00d4aa}.rd{color:#ff4d6a}.yl{color:#ffd700}.bl{color:#4dabf7}.gy{color:#555}
.summary{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-bottom:14px}
.sum-card{background:#141926;border:1px solid #2a3040;border-radius:6px;padding:10px;text-align:center}
.sum-card .label{font-size:9px;color:#555;margin-bottom:3px}
.sum-card .value{font-size:18px;font-weight:bold}
.section{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:14px;margin-bottom:12px}
.section h2{font-size:10px;color:#555;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px}
table{width:100%;border-collapse:collapse;font-size:10px}
th{text-align:left;color:#555;padding:4px 6px;border-bottom:1px solid #2a3040;font-size:9px}
td{padding:4px 6px;border-bottom:1px solid #1a2030}
.hist-bar{height:12px;background:#4dabf7;border-radius:2px;display:inline-block;vertical-align:middle}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.heatmap-row{display:flex;gap:2px;margin:1px 0}
.heatmap-cell{width:18px;height:18px;border-radius:2px;display:inline-flex;align-items:center;justify-content:center;font-size:7px}
.dist-bar{height:16px;border-radius:3px;display:flex;align-items:center;padding-left:6px;margin:2px 0;font-size:9px;color:#fff}
canvas{width:100%;height:200px}
</style>
</head><body>
<div class="hdr">
  <h1>5,000 Strategy Tournament</h1>
  <div id="clock" class="gy"></div>
</div>
<div class="wrap">
  <div id="notification" style="display:none;margin-bottom:12px"></div>

  <div class="section" id="progress">로딩 중...</div>

  <div class="summary" id="summary"></div>

  <div class="section" style="position:relative">
    <h2>목표 근접도 (69초 틱)</h2>
    <canvas id="tickChart" style="width:100%;height:200px"></canvas>
    <div id="tickLegend" style="display:flex;gap:16px;margin-top:6px;font-size:9px">
      <span style="color:#00d4aa">&#9632; 최고 변형</span>
      <span style="color:#ffd700">&#9632; 상위10 평균</span>
      <span style="color:#4dabf7">&#9632; 전체 평균</span>
      <span style="color:#ff4d6a">&#9632; 최저 변형</span>
      <span style="color:#555">&#9632; 수익 비율(%)</span>
    </div>
  </div>

  <div class="section">
    <h2>토너먼트 현황</h2>
    <div id="ensemble"></div>
  </div>

  <div class="grid3" id="distributions">
    <div class="section"><h2>종목 분포</h2><div id="asset-dist"></div></div>
    <div class="section"><h2>전략 분포</h2><div id="strategy-dist"></div></div>
    <div class="section"><h2>시간축 분포</h2><div id="tf-dist"></div></div>
  </div>

  <div class="grid2">
    <div class="section"><h2>수익률 분포</h2><div id="histogram"></div></div>
    <div class="section"><h2>파라미터 상관관계</h2><div id="heatmap"></div></div>
  </div>

  <div class="grid2">
    <div class="section">
      <h2>상위 10</h2>
      <table id="top10"><thead><tr>
        <th>#</th><th>수익%</th><th>승률%</th><th>CTS</th><th>거래</th><th>DD%</th>
        <th>종목</th><th>전략</th><th>시간축</th>
        <th>추세</th><th>RSI</th><th>모멘텀</th><th>레버리지</th>
      </tr></thead><tbody></tbody></table>
    </div>
    <div class="section">
      <h2>하위 10</h2>
      <table id="bot10"><thead><tr>
        <th>#</th><th>수익%</th><th>승률%</th><th>CTS</th><th>거래</th><th>DD%</th>
        <th>종목</th><th>전략</th><th>시간축</th>
        <th>추세</th><th>RSI</th><th>모멘텀</th><th>레버리지</th>
      </tr></thead><tbody></tbody></table>
    </div>
  </div>

  <div class="section" style="color:#555;font-size:10px;text-align:center;padding:10px">
    READY 상태가 되면 녹색 배너가 표시됩니다. 그때 결과를 검토하고 다음 단계를 결정하세요.
  </div>
</div>
<script>
function fmt(v, d=1){ return v !== null && v !== undefined ? v.toFixed(d) : '-'; }
function cls(v){ return v > 0 ? 'gn' : v < 0 ? 'rd' : 'gy'; }
const COLORS = ['#4dabf7','#ff9800','#00d4aa','#ff4d6a','#ffd700','#a855f7','#38bdf8','#f472b6','#34d399'];

function renderDist(elId, items) {
  const el = document.getElementById(elId);
  const maxV = Math.max(...items.map(i=>i.count), 1);
  el.innerHTML = items.map((it,i)=>{
    const w = Math.max(30, it.count / maxV * 100);
    const bg = COLORS[i % COLORS.length];
    return `<div class="dist-bar" style="width:${w}%;background:${bg}80">${it.name}: ${it.count} (${it.avg_ret}%)</div>`;
  }).join('');
}

async function refresh(){
  try {
    const r = await fetch('/api/state');
    const d = await r.json();

    document.getElementById('clock').textContent = new Date().toLocaleTimeString();

    const s = d.summary;
    document.getElementById('summary').innerHTML = [
      ['변형 수', s.n_variants, 'bl'],
      ['평균 수익', fmt(s.avg_ret)+'%', cls(s.avg_ret)],
      ['최고', fmt(s.best_ret)+'%', 'gn'],
      ['최저', fmt(s.worst_ret)+'%', 'rd'],
      ['세대', s.generation, 'yl'],
      ['앙상블', fmt(s.ensemble_signal, 2), 'bl'],
    ].map(([l,v,c])=>`<div class="sum-card"><div class="label">${l}</div><div class="value ${c}">${v}</div></div>`).join('');

    // Distributions
    if(d.asset_dist) renderDist('asset-dist', d.asset_dist);
    if(d.strategy_dist) renderDist('strategy-dist', d.strategy_dist);
    if(d.tf_dist) renderDist('tf-dist', d.tf_dist);

    // Histogram
    const hist = d.histogram;
    const maxC = Math.max(...hist.counts, 1);
    document.getElementById('histogram').innerHTML = hist.bins.map((b,i)=>{
      const w = Math.max(1, hist.counts[i] / maxC * 300);
      return `<div style="margin:1px 0"><span class="gy" style="display:inline-block;width:70px;text-align:right;margin-right:6px">${b}</span><span class="hist-bar" style="width:${w}px"></span> <span class="gy">${hist.counts[i]}</span></div>`;
    }).join('');

    // Top / Bottom tables
    function fillTable(id, rows){
      const tb = document.querySelector('#'+id+' tbody');
      tb.innerHTML = rows.map(r=>`<tr>
        <td>${r.idx}</td>
        <td class="${cls(r.ret)}">${fmt(r.ret)}</td>
        <td>${fmt(r.wr)}</td><td>${fmt(r.cts,3)}</td><td>${r.trades}</td><td class="rd">${fmt(r.dd)}</td>
        <td class="bl">${r.asset||'-'}</td><td class="yl">${r.strategy||'-'}</td><td>${r.tf||'-'}</td>
        <td>${fmt(r.trend,2)}</td><td>${fmt(r.rsi,2)}</td>
        <td>${fmt(r.mom,2)}</td><td>${fmt(r.lev,1)}</td>
      </tr>`).join('');
    }
    fillTable('top10', d.top10);
    fillTable('bot10', d.bot10);

    // Heatmap
    const hm = d.heatmap;
    document.getElementById('heatmap').innerHTML =
      '<div style="font-size:8px;color:#555;margin-bottom:4px">Param vs Return correlation</div>' +
      hm.map(h=>{
        const c = h.corr;
        const bg = c > 0 ? `rgba(0,212,170,${Math.abs(c).toFixed(2)})` :
                           `rgba(255,77,106,${Math.abs(c).toFixed(2)})`;
        return `<div style="margin:2px 0"><span class="gy" style="display:inline-block;width:140px">${h.name}</span><div class="heatmap-cell" style="background:${bg};display:inline-block;padding:2px 8px">${c.toFixed(3)}</div></div>`;
      }).join('');

    // Tournament status
    const e = d.tournament;
    document.getElementById('ensemble').innerHTML = `
      <div style="margin:4px 0">단계: <span class="yl">${e.phase}</span> | 세대: <span class="bl">${e.generation}</span></div>
      <div style="margin:4px 0">다음 라운드: <span class="gy">${e.next_round}</span></div>
      <div style="margin:4px 0">앙상블 시그널: <span class="bl">${fmt(s.ensemble_signal,3)}</span> (상위 10개 평균 포지션)</div>
    `;

    // Progress & ETA
    const p = d.progress || {};
    const pct30 = p.pct_30 || 0;
    const pct100 = p.pct_100 || 0;
    const rdColor = p.readiness==='READY'?'gn':p.readiness==='APPROACHING'?'yl':'gy';
    let progEl = document.getElementById('progress');
    if(progEl) progEl.innerHTML = `
      <h2>진행 상황</h2>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div>
          <div style="margin:4px 0;font-size:10px;color:#555">경과 시간</div>
          <div style="font-size:20px;font-weight:bold" class="bl">${(p.elapsed_days||0).toFixed(1)}일</div>
          <div style="margin:4px 0">총 거래: <b>${(p.total_trades||0).toLocaleString()}</b>건 (일 ${(p.trades_per_day||0).toFixed(0)}건)</div>
          <div style="margin:4px 0">변형당 평균: <b>${(p.avg_trades||0).toFixed(1)}</b> / 30건 필요</div>
        </div>
        <div>
          <div style="margin:4px 0;font-size:10px;color:#555">검증 상태</div>
          <div style="font-size:20px;font-weight:bold" class="${rdColor}">${p.readiness||'--'}</div>
          <div style="margin:4px 0">${p.readiness_msg||''}</div>
          <div style="margin:4px 0">30건 도달 예상: <b class="yl">${p.eta_to_30||'--'}</b></div>
        </div>
      </div>
      <div style="margin:10px 0">
        <div style="font-size:9px;color:#555;margin-bottom:3px">30건+ 거래 변형: ${p.variants_30plus||0} / ${s.n_variants} (${pct30}%)</div>
        <div style="height:10px;background:#1a2030;border-radius:5px;overflow:hidden">
          <div style="height:100%;width:${pct30}%;background:linear-gradient(90deg,#ffd700,#ff9800);border-radius:5px;transition:width 2s"></div>
        </div>
      </div>
      <div style="margin:8px 0">
        <div style="font-size:9px;color:#555;margin-bottom:3px">100건+ 거래 변형: ${p.variants_100plus||0} / ${s.n_variants} (${pct100}%)</div>
        <div style="height:10px;background:#1a2030;border-radius:5px;overflow:hidden">
          <div style="height:100%;width:${pct100}%;background:linear-gradient(90deg,#00d4aa,#00d4aa88);border-radius:5px;transition:width 2s"></div>
        </div>
      </div>
    `;

    // 69-second tick chart
    const ticks = d.ticks || [];
    if(ticks.length > 1){
      const canvas = document.getElementById('tickChart');
      if(canvas){
        const ctx = canvas.getContext('2d');
        const W = canvas.width = canvas.offsetWidth;
        const H = canvas.height = 200;
        ctx.clearRect(0,0,W,H);

        const series = {
          best: {data:ticks.map(t=>t.best), color:'#00d4aa'},
          top10: {data:ticks.map(t=>t.top10_avg), color:'#ffd700'},
          avg: {data:ticks.map(t=>t.avg), color:'#4dabf7'},
          worst: {data:ticks.map(t=>t.worst), color:'#ff4d6a'},
        };

        // Find global min/max
        let allVals = [];
        for(const s of Object.values(series)) allVals.push(...s.data);
        let yMin = Math.min(...allVals, 0);
        let yMax = Math.max(...allVals, 0.1);
        const yPad = (yMax - yMin) * 0.1 || 0.5;
        yMin -= yPad; yMax += yPad;

        const n = ticks.length;
        const xStep = W / Math.max(n-1, 1);

        // Zero line (0% baseline - prominent)
        const zeroY = H - (0 - yMin) / (yMax - yMin) * H;
        // Background band to highlight 0%
        ctx.fillStyle = 'rgba(255,255,255,0.03)';
        ctx.fillRect(0, zeroY - 1, W, 2);
        // Dashed line
        ctx.strokeStyle = 'rgba(255,255,255,0.25)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([8,4]);
        ctx.beginPath(); ctx.moveTo(0, zeroY); ctx.lineTo(W, zeroY); ctx.stroke();
        ctx.setLineDash([]);
        // Label
        ctx.fillStyle = 'rgba(255,255,255,0.4)';
        ctx.font = 'bold 10px monospace';
        ctx.fillText('0%', 4, zeroY - 5);

        // Draw each series
        for(const [name, s] of Object.entries(series)){
          ctx.strokeStyle = s.color;
          ctx.lineWidth = name==='top10' ? 2.5 : 1.2;
          ctx.globalAlpha = name==='top10' ? 1 : 0.7;
          ctx.beginPath();
          for(let i=0; i<n; i++){
            const x = i * xStep;
            const y = H - (s.data[i] - yMin) / (yMax - yMin) * H;
            if(i===0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          }
          ctx.stroke();
          ctx.globalAlpha = 1;
        }

        // Positive % area (subtle)
        const posData = ticks.map(t=>t.positive_pct);
        ctx.fillStyle = 'rgba(85,85,85,0.15)';
        ctx.beginPath();
        ctx.moveTo(0, H);
        for(let i=0; i<n; i++){
          const x = i * xStep;
          const y = H - posData[i] / 100 * H;
          ctx.lineTo(x, y);
        }
        ctx.lineTo(W, H); ctx.closePath(); ctx.fill();

        // Labels
        ctx.fillStyle = '#555'; ctx.font = '9px monospace';
        ctx.fillText(yMax.toFixed(1)+'%', 4, 12);
        ctx.fillText(yMin.toFixed(1)+'%', 4, H-4);
        ctx.fillStyle='rgba(255,255,255,0.3)'; ctx.font='bold 10px monospace'; ctx.fillText('0%', W-30, zeroY-5);
        if(ticks.length > 0){
          ctx.fillText(ticks[0].t, 4, H-14);
          ctx.fillText(ticks[ticks.length-1].t, W-55, H-14);
        }
        // Latest values on right edge
        const last = ticks[ticks.length-1];
        ctx.fillStyle='#00d4aa'; ctx.fillText(last.best.toFixed(2)+'%', W-60, 12);
        ctx.fillStyle='#ffd700'; ctx.fillText(last.top10_avg.toFixed(2)+'%', W-60, 24);
        ctx.fillStyle='#4dabf7'; ctx.fillText(last.avg.toFixed(2)+'%', W-60, 36);
      }
    }

    // Notification banner
    const notify = d.notify;
    let notifEl = document.getElementById('notification');
    if(notifEl){
      if(notify){
        const nc = notify.level==='success'?'#00d4aa':notify.level==='warning'?'#ffd700':'#555';
        notifEl.style.display='block';
        notifEl.innerHTML=`<div style="padding:12px 20px;background:${nc}22;border:1px solid ${nc};border-radius:8px;color:${nc};font-weight:bold;font-size:13px;text-align:center">${notify.msg}</div>`;
      } else {
        notifEl.style.display='none';
      }
    }
  } catch(e){ console.error(e); }
}
refresh();
setInterval(refresh, 15000);
</script>
</body></html>"""


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # suppress logs

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASH_HTML.encode("utf-8"))
        elif self.path == "/api/state":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(self._build_state()).encode("utf-8"))
        else:
            self.send_error(404)

    def _build_state(self) -> dict:
        m = _manager
        if m is None:
            return {"error": "not ready"}

        rets = m.portfolio.returns_pct()
        dds = m.portfolio.drawdowns_pct()
        wrs = m.portfolio.win_rates()
        cts = composite_tournament_scores(m.portfolio)

        # Summary
        summary = {
            "n_variants": N_VARIANTS,
            "avg_ret": float(rets.mean()),
            "best_ret": float(rets.max()),
            "worst_ret": float(rets.min()),
            "generation": m.generation,
            "ensemble_signal": m.ensemble_signal,
        }

        # Histogram (20 bins)
        n_bins = 20
        r_min, r_max = float(rets.min()), float(rets.max())
        if r_min == r_max:
            r_min -= 1
            r_max += 1
        edges = np.linspace(r_min, r_max, n_bins + 1)
        counts, _ = np.histogram(rets, bins=edges)
        histogram = {
            "bins": [f"{edges[i]:.1f}~{edges[i+1]:.1f}%" for i in range(n_bins)],
            "counts": counts.tolist(),
        }

        # Asset distribution
        asset_indices = m.params[:, 11].astype(int)
        asset_dist = []
        for ai, name in enumerate(ASSET_NAMES):
            mask = asset_indices == ai
            cnt = int(mask.sum())
            avg_r = float(rets[mask].mean()) if cnt > 0 else 0.0
            asset_dist.append({"name": name, "count": cnt,
                               "avg_ret": f"{avg_r:.1f}"})

        # Strategy distribution
        strat_indices = m.params[:, 10].astype(int)
        strategy_dist = []
        for si, name in enumerate(STRATEGY_NAMES):
            mask = strat_indices == si
            cnt = int(mask.sum())
            avg_r = float(rets[mask].mean()) if cnt > 0 else 0.0
            strategy_dist.append({"name": name, "count": cnt,
                                  "avg_ret": f"{avg_r:.1f}"})

        # Timeframe distribution
        tf_indices = m.params[:, 12].astype(int)
        tf_dist = []
        for ti, name in TIMEFRAME_CHOICES.items():
            mask = tf_indices == ti
            cnt = int(mask.sum())
            avg_r = float(rets[mask].mean()) if cnt > 0 else 0.0
            tf_dist.append({"name": name, "count": cnt,
                            "avg_ret": f"{avg_r:.1f}"})

        # Top / Bottom 10
        sorted_idx = np.argsort(rets)[::-1]

        def make_row(idx):
            i = int(idx)
            p = m.params[i]
            ai = int(p[11]) % len(ASSET_NAMES)
            si = int(p[10]) % len(STRATEGY_NAMES)
            ti = int(p[12]) % len(TIMEFRAME_CHOICES)
            return {
                "idx": i, "ret": float(rets[i]),
                "wr": float(wrs[i]),
                "cts": float(cts[i]),
                "trades": int(m.portfolio.trade_counts[i]),
                "dd": float(dds[i]),
                "asset": ASSET_NAMES[ai],
                "strategy": STRATEGY_NAMES[si],
                "tf": TIMEFRAME_CHOICES[ti],
                "trend": float(p[0]), "rsi": float(p[1]),
                "mom": float(p[3]), "lev": float(p[6]),
            }

        top10 = [make_row(sorted_idx[i]) for i in range(min(10, len(sorted_idx)))]
        bot10 = [make_row(sorted_idx[-(i+1)])
                 for i in range(min(10, len(sorted_idx)))]

        # Heatmap: correlation of each param with return
        heatmap = []
        for j, name in enumerate(PARAM_NAMES):
            if np.std(m.params[:, j]) < 1e-12 or np.std(rets) < 1e-12:
                corr = 0.0
            else:
                corr = float(np.corrcoef(m.params[:, j], rets)[0, 1])
                if np.isnan(corr):
                    corr = 0.0
            heatmap.append({"name": name, "corr": corr})

        # Tournament status
        now = datetime.now(tz=timezone.utc)
        weeks_elapsed = (now - m.started_at).days / 7
        phase = ("Exploration (no elimination)"
                 if weeks_elapsed < EXPLORATION_PHASE_WEEKS
                 else "Tournament (biweekly)")
        days_until = max(0, TOURNAMENT_INTERVAL_DAYS
                         - (now - m.last_tournament).days)
        tournament = {
            "phase": phase,
            "generation": m.generation,
            "next_round": f"{days_until}d remaining",
            "top10_idx": m.ensemble_top_idx.tolist(),
        }

        # Progress & ETA
        total_trades = int(m.portfolio.trade_counts.sum())
        avg_trades_per_variant = float(m.portfolio.trade_counts.mean())
        variants_with_30 = int((m.portfolio.trade_counts >= 30).sum())
        variants_with_100 = int((m.portfolio.trade_counts >= 100).sum())
        elapsed_days = max((now - m.started_at).total_seconds() / 86400, 0.01)
        trades_per_day = total_trades / elapsed_days if elapsed_days > 0.1 else 0
        # ETA: when will avg variant reach 30 trades?
        if avg_trades_per_variant < 30 and trades_per_day > 0:
            remaining_trades = (30 - avg_trades_per_variant) * N_VARIANTS
            eta_days = remaining_trades / trades_per_day
            eta_str = f"{eta_days:.0f}d" if eta_days > 1 else f"{eta_days*24:.0f}h"
        else:
            eta_str = "Ready"

        # Readiness level
        if variants_with_100 >= N_VARIANTS * 0.5:
            readiness = "READY"
            readiness_msg = "Data sufficient. Ready for review."
        elif variants_with_30 >= N_VARIANTS * 0.5:
            readiness = "APPROACHING"
            readiness_msg = f"50%+ variants have 30+ trades. {variants_with_100} have 100+."
        elif variants_with_30 >= N_VARIANTS * 0.1:
            readiness = "BUILDING"
            readiness_msg = f"{variants_with_30} variants have 30+ trades ({variants_with_30*100//N_VARIANTS}%)"
        else:
            readiness = "EARLY"
            readiness_msg = f"Avg {avg_trades_per_variant:.1f} trades/variant. Need 30 minimum."

        # Notification flags
        notify = None
        if readiness == "READY":
            notify = {"level": "success", "msg": "Data sufficient! Review recommended."}
        elif readiness == "APPROACHING":
            notify = {"level": "warning", "msg": "Approaching readiness. Almost there."}

        progress = {
            "elapsed_days": round(elapsed_days, 1),
            "total_trades": total_trades,
            "avg_trades": round(avg_trades_per_variant, 1),
            "trades_per_day": round(trades_per_day, 0),
            "variants_30plus": variants_with_30,
            "variants_100plus": variants_with_100,
            "eta_to_30": eta_str,
            "readiness": readiness,
            "readiness_msg": readiness_msg,
            "pct_30": round(variants_with_30 / N_VARIANTS * 100, 1),
            "pct_100": round(variants_with_100 / N_VARIANTS * 100, 1),
        }

        return {
            "summary": summary,
            "histogram": histogram,
            "asset_dist": asset_dist,
            "strategy_dist": strategy_dist,
            "tf_dist": tf_dist,
            "top10": top10,
            "bot10": bot10,
            "heatmap": heatmap,
            "tournament": tournament,
            "progress": progress,
            "notify": notify,
            "ticks": m.tick_history[-100:],  # last 100 ticks for chart
        }


def start_dashboard():
    server = http.server.HTTPServer(("0.0.0.0", DASH_PORT), DashboardHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"[Dashboard] http://localhost:{DASH_PORT}")


# ===================================================================
# Main
# ===================================================================

def main():
    global _manager
    _manager = TournamentManager()
    start_dashboard()
    _manager.run_forever()


if __name__ == "__main__":
    main()
