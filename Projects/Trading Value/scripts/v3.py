"""V3 — Parker Brooks Rule Engine + Self-Learning Context Memory.

Design:
  1. Parker Brooks rule engine (VWAP/EMA9/Volume Profile) — deterministic entry gate
  2. Context Memory (k-NN based EV tracking) — learns good/bad contexts
  3. Kill Switch — auto-blacklist bad context clusters
  4. Multi-variant paper trading (5 variants concurrently)

Core principle (user requirement):
  "안 좋은 건 소거, 좋은 건 받아들임. 스스로 발전하는 알고리즘."

Usage:
    py -3.12 scripts/v3.py [--assets ETH,BTC,SOL,XRP] [--port 8898]

Dashboard:
    http://localhost:8898
"""
from __future__ import annotations

import argparse
import http.server
import json
import math
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

for _pkg, _imp in [("ccxt", "ccxt")]:
    try:
        __import__(_imp)
    except ImportError:
        import subprocess as _sp
        _sp.check_call([sys.executable, "-m", "pip", "install", _pkg])

import ccxt

# ===================================================================
# Constants
# ===================================================================
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATE_PATH = DATA_DIR / "v3_state.npz"
LOG_PATH = DATA_DIR / "v3.jsonl"
MEMORY_PATH = DATA_DIR / "v3_memory.json"
DASH_PORT = 8898
TICK_SEC = 60
HISTORY_BARS = 500
INITIAL_CAPITAL = 10_000.0
SAVE_INTERVAL = 1800

# Cost model (Bybit USDT perp)
TAKER_FEE = 0.00055
SLIPPAGE = 0.0005
ROUND_TRIP_COST = (TAKER_FEE * 2) + (SLIPPAGE * 2)  # ~0.21%

# Context Memory policy
CTX_DIM = 6
KNN_K = 5
MEMORY_MIN_SAMPLES_FOR_BLACKLIST = 20
MEMORY_BLACKLIST_EV_THRESHOLD = -0.5   # in R units
MEMORY_BOOST_EV_THRESHOLD = 0.3        # in R units
MEMORY_WARMUP_TRADES = 30              # trades before memory activates
MEMORY_FULL_ACTIVATION = 100           # trades before memory at full weight

# Risk
RISK_PER_TRADE = 0.005  # 0.5% of equity per trade (hard stop distance)

# Variants — user said: "다양하게 모델을 만들어서 병행 페이퍼 트레이딩 테스트"
VARIANTS_CONFIG = {
    "v3-baseline":     dict(rr_min=1.5, chop_strict=1.0, memory=True,  timeframe="5m"),
    "v3-aggressive":   dict(rr_min=1.2, chop_strict=0.8, memory=True,  timeframe="5m"),
    "v3-conservative": dict(rr_min=2.0, chop_strict=1.2, memory=True,  timeframe="5m"),
    "v3-15m":          dict(rr_min=1.5, chop_strict=1.0, memory=True,  timeframe="15m"),
    "v3-control":      dict(rr_min=1.5, chop_strict=1.0, memory=False, timeframe="5m"),
}


# ===================================================================
# Indicator Engine
# ===================================================================
class IndicatorEngine:
    """Computes VWAP (session-anchored UTC 00:00), EMA9, ATR14, Volume Profile."""

    @staticmethod
    def session_vwap(df: pd.DataFrame) -> np.ndarray:
        """VWAP anchored at UTC 00:00 (daily reset)."""
        # Ensure ts is datetime
        ts = pd.to_datetime(df["ts"])
        date = ts.dt.date
        tp = (df["high"] + df["low"] + df["close"]) / 3.0
        vol = df["volume"]
        tpv = tp * vol
        # Cumulative within each day
        cum_tpv = tpv.groupby(date).cumsum()
        cum_vol = vol.groupby(date).cumsum()
        vwap = cum_tpv / cum_vol.replace(0, np.nan)
        return vwap.ffill().bfill().values.astype(float)

    @staticmethod
    def ema(values: np.ndarray, period: int) -> np.ndarray:
        s = pd.Series(values)
        return s.ewm(span=period, adjust=False).mean().values.astype(float)

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> np.ndarray:
        h = df["high"].values.astype(float)
        lo = df["low"].values.astype(float)
        c = df["close"].values.astype(float)
        if len(c) < 2:
            return np.zeros_like(c)
        prev_c = np.concatenate([[c[0]], c[:-1]])
        tr = np.maximum.reduce([
            h - lo,
            np.abs(h - prev_c),
            np.abs(lo - prev_c),
        ])
        return pd.Series(tr).rolling(period, min_periods=1).mean().values.astype(float)

    @staticmethod
    def volume_profile(df: pd.DataFrame, lookback: int = 120, nbins: int = 30) -> tuple[np.ndarray, np.ndarray]:
        """Fixed-range volume profile. Returns (price_midpoints, volumes)."""
        if len(df) < lookback:
            return np.array([]), np.array([])
        recent = df.iloc[-lookback:]
        lo = float(recent["low"].min())
        hi = float(recent["high"].max())
        if hi <= lo:
            return np.array([]), np.array([])
        bins = np.linspace(lo, hi, nbins + 1)
        mids = (bins[:-1] + bins[1:]) / 2.0
        volumes = np.zeros(nbins)
        for _, row in recent.iterrows():
            bar_lo, bar_hi = float(row["low"]), float(row["high"])
            bar_vol = float(row["volume"])
            if bar_hi <= bar_lo:
                continue
            # distribute bar volume across overlapping bins
            for i in range(nbins):
                b_lo, b_hi = bins[i], bins[i + 1]
                overlap = max(0.0, min(bar_hi, b_hi) - max(bar_lo, b_lo))
                if overlap > 0:
                    volumes[i] += bar_vol * overlap / (bar_hi - bar_lo)
        return mids, volumes

    @staticmethod
    def hvn_indices(volumes: np.ndarray, percentile: float = 70.0) -> np.ndarray:
        """Returns indices of bins with volume >= given percentile. HVN = top 30%."""
        if len(volumes) == 0:
            return np.array([], dtype=int)
        threshold = np.percentile(volumes, percentile)
        return np.where(volumes >= threshold)[0]


# ===================================================================
# Market State Classifier (Parker Brooks rule sections A/B/C)
# ===================================================================
@dataclass
class MarketSnapshot:
    close: float
    vwap: float
    ema9: float
    atr14: float
    vwap_slope_3: float       # vwap_now - vwap_3bars_ago
    ema_dist_atr: float       # (close - ema9) / atr14
    recent_vwap_crosses: int  # count in last 20 bars
    close_vwap_dist_atr: float  # abs(close - vwap) / atr14
    session_hour: int
    vol_regime: float         # atr14 / atr60


def classify_state(df: pd.DataFrame, snap: MarketSnapshot, chop_strict: float) -> str:
    """A/B/C classification. chop_strict>1.0 = stricter chop detection."""
    if len(df) < 20:
        return "INSUFFICIENT_DATA"

    c = df["close"].values
    vwap_arr = IndicatorEngine.session_vwap(df)
    atr_val = snap.atr14
    if atr_val <= 0:
        return "INSUFFICIENT_DATA"

    # A. VWAP_CHOP — any of these conditions
    # (1) > 3 VWAP crosses in last 20 bars  (tightened by chop_strict)
    max_crosses = max(1, int(round(3 / chop_strict)))
    if snap.recent_vwap_crosses > max_crosses:
        return "VWAP_CHOP"

    # (2) 4+ of last 10 bars have abs(close - vwap) <= 0.15 * ATR
    hug_threshold = 0.15 * atr_val * chop_strict
    last10 = min(10, len(c))
    hug_count = sum(
        1 for i in range(-last10, 0)
        if abs(c[i] - vwap_arr[i]) <= hug_threshold
    )
    if hug_count >= 4:
        return "VWAP_CHOP"

    # (3) ema9/vwap distance <= 0.10 * ATR for 3+ of last 5 bars
    ema_arr = IndicatorEngine.ema(c, 9)
    close_threshold = 0.10 * atr_val * chop_strict
    close_count = sum(
        1 for i in range(-min(5, len(c)), 0)
        if abs(ema_arr[i] - vwap_arr[i]) <= close_threshold
    )
    if close_count >= 3:
        return "VWAP_CHOP"

    # B/C bias
    last2_above = all(c[i] > vwap_arr[i] for i in [-1, -2])
    last2_below = all(c[i] < vwap_arr[i] for i in [-1, -2])
    vwap_rising = snap.vwap_slope_3 > 0
    vwap_falling = snap.vwap_slope_3 < 0
    ema_above_vwap = snap.ema9 > snap.vwap
    ema_below_vwap = snap.ema9 < snap.vwap

    if last2_above and vwap_rising and ema_above_vwap:
        return "LONG_BIAS"
    if last2_below and vwap_falling and ema_below_vwap:
        return "SHORT_BIAS"
    return "NEUTRAL"


# ===================================================================
# Pullback Validator (Parker Brooks D/E)
# ===================================================================
def long_pullback_valid(df: pd.DataFrame, snap: MarketSnapshot) -> tuple[bool, float]:
    """Check D. Returns (valid, recent_pullback_low)."""
    if len(df) < 7:
        return False, 0.0
    c = df["close"].values
    lo = df["low"].values
    ema_arr = IndicatorEngine.ema(c, 9)
    atr_val = snap.atr14
    if atr_val <= 0:
        return False, 0.0

    # (1) any bar in last 1-6 had low <= EMA9 + 0.10*ATR
    touch_threshold = 0.10 * atr_val
    pullback_bars = []
    for i in range(-6, 0):
        if abs(i) > len(c):
            continue
        if lo[i] <= ema_arr[i] + touch_threshold:
            pullback_bars.append(i)
    if not pullback_bars:
        return False, 0.0

    # (2) current close >= EMA9 + 0.05*ATR
    if c[-1] < ema_arr[-1] + 0.05 * atr_val:
        return False, 0.0

    # (3) current close > VWAP
    if c[-1] <= snap.vwap:
        return False, 0.0

    # (4) recent pullback low is real (at or near the lowest of recent bars)
    pullback_low = float(min(lo[i] for i in pullback_bars))
    return True, pullback_low


def short_pullback_valid(df: pd.DataFrame, snap: MarketSnapshot) -> tuple[bool, float]:
    """Check E. Returns (valid, recent_pullback_high)."""
    if len(df) < 7:
        return False, 0.0
    c = df["close"].values
    h = df["high"].values
    ema_arr = IndicatorEngine.ema(c, 9)
    atr_val = snap.atr14
    if atr_val <= 0:
        return False, 0.0

    touch_threshold = 0.10 * atr_val
    pullback_bars = []
    for i in range(-6, 0):
        if abs(i) > len(c):
            continue
        if h[i] >= ema_arr[i] - touch_threshold:
            pullback_bars.append(i)
    if not pullback_bars:
        return False, 0.0

    if c[-1] > ema_arr[-1] - 0.05 * atr_val:
        return False, 0.0
    if c[-1] >= snap.vwap:
        return False, 0.0

    pullback_high = float(max(h[i] for i in pullback_bars))
    return True, pullback_high


# ===================================================================
# Volume Profile Clearance (Parker Brooks G/H)
# ===================================================================
def vp_clearance(df: pd.DataFrame, entry: float, direction: str, atr_val: float,
                 hard_stop_dist: float, rr_min: float) -> tuple[bool, float, float]:
    """Returns (clear, first_hvn_price, rr_estimate)."""
    mids, vols = IndicatorEngine.volume_profile(df)
    if len(mids) == 0:
        return False, 0.0, 0.0
    hvn_idx = IndicatorEngine.hvn_indices(vols, percentile=70.0)
    if len(hvn_idx) == 0:
        return False, 0.0, 0.0
    hvn_prices = mids[hvn_idx]

    if direction == "long":
        ahead = hvn_prices[hvn_prices > entry]
    else:
        ahead = hvn_prices[hvn_prices < entry]

    if len(ahead) == 0:
        return False, 0.0, 0.0

    first_hvn = float(ahead.min()) if direction == "long" else float(ahead.max())
    distance = abs(first_hvn - entry)

    # (1) distance >= 0.75 * ATR
    if distance < 0.75 * atr_val:
        return False, first_hvn, 0.0

    # (2) distance / hard_stop_dist >= rr_min
    if hard_stop_dist <= 0:
        return False, first_hvn, 0.0
    rr = distance / hard_stop_dist
    if rr < rr_min:
        return False, first_hvn, rr

    return True, first_hvn, rr


# ===================================================================
# Context Vector + Memory Store (자기학습 — 안 좋은 건 소거, 좋은 건 받아들임)
# ===================================================================
@dataclass
class ContextVector:
    vwap_slope: float           # normalized by ATR
    ema_dist_atr: float         # (close - ema9) / ATR
    vp_clearance_atr: float     # distance to first HVN / ATR
    rr_estimate: float
    session_hour_bucket: int    # 0..5 (6 buckets of 4h each)
    vol_regime: float           # atr14 / atr60

    def to_array(self) -> np.ndarray:
        return np.array([
            self.vwap_slope, self.ema_dist_atr, self.vp_clearance_atr,
            self.rr_estimate, float(self.session_hour_bucket), self.vol_regime,
        ])


@dataclass
class TradeRecord:
    context: list[float]        # ContextVector as array
    direction: str              # "long"/"short"
    entry_price: float
    exit_price: float
    r_multiple: float           # PnL in R units (hard stop distance)
    net_pct: float              # net return % after fees
    asset: str
    timestamp: str


class ContextMemory:
    """Stores past trades and scores new contexts via k-NN EV.

    The self-improving core:
      - Bad contexts (EV < threshold with enough samples) → blacklist
      - Good contexts (EV > threshold) → position size boost
    """

    def __init__(self, variant_name: str):
        self.variant_name = variant_name
        self.records: list[TradeRecord] = []
        self._blacklist_cache: set[int] | None = None  # hash-based

    def add(self, record: TradeRecord):
        self.records.append(record)
        self._blacklist_cache = None  # invalidate

    def _distance(self, a: np.ndarray, b: np.ndarray) -> float:
        # Weighted Euclidean: numeric dims use standard, hour_bucket uses 0/1 mismatch
        diff = a - b
        # hour_bucket at index 4 — treat as categorical (0 if same, 2 if diff)
        diff[4] = 0.0 if a[4] == b[4] else 2.0
        return float(np.linalg.norm(diff))

    def _neighbors(self, ctx: ContextVector, direction: str, k: int) -> list[TradeRecord]:
        if not self.records:
            return []
        target = ctx.to_array()
        same_dir = [r for r in self.records if r.direction == direction]
        if not same_dir:
            return []
        distances = [(self._distance(target, np.array(r.context)), r) for r in same_dir]
        distances.sort(key=lambda x: x[0])
        k = min(k, len(distances))
        return [r for _, r in distances[:k]]

    def query_ev(self, ctx: ContextVector, direction: str) -> tuple[float, int]:
        """Top-k EV estimate for position sizing."""
        neighbors = self._neighbors(ctx, direction, KNN_K)
        if not neighbors:
            return 0.0, 0
        ev = float(np.mean([r.r_multiple for r in neighbors]))
        return ev, len(neighbors)

    def is_blacklisted(self, ctx: ContextVector, direction: str) -> bool:
        """Blacklist check uses a larger neighborhood for statistical significance."""
        cluster = self._neighbors(ctx, direction, MEMORY_MIN_SAMPLES_FOR_BLACKLIST)
        if len(cluster) < MEMORY_MIN_SAMPLES_FOR_BLACKLIST:
            return False
        cluster_ev = float(np.mean([r.r_multiple for r in cluster]))
        return cluster_ev < MEMORY_BLACKLIST_EV_THRESHOLD

    def size_multiplier(self, ctx: ContextVector, direction: str, total_trades: int) -> float:
        """Returns position size multiplier in [0, 1.5] based on context EV.

        Warmup: no memory effect until MEMORY_WARMUP_TRADES.
        Gradual activation between warmup and full-activation.
        """
        if total_trades < MEMORY_WARMUP_TRADES:
            return 1.0

        ev, n = self.query_ev(ctx, direction)
        if n == 0:
            return 1.0

        # Activation weight ramps 0->1 between WARMUP and FULL
        if total_trades >= MEMORY_FULL_ACTIVATION:
            weight = 1.0
        else:
            span = MEMORY_FULL_ACTIVATION - MEMORY_WARMUP_TRADES
            weight = (total_trades - MEMORY_WARMUP_TRADES) / span

        # Base multiplier: 1.0. Scale by EV with clip.
        if ev > MEMORY_BOOST_EV_THRESHOLD:
            boost = min((ev - MEMORY_BOOST_EV_THRESHOLD) * 1.0, 0.5)  # max +50%
            return 1.0 + boost * weight
        elif ev < 0:
            # Soft penalty before blacklist threshold
            penalty = min(abs(ev) * 0.5, 0.5)  # max -50%
            return max(0.5, 1.0 - penalty * weight)
        return 1.0

    def snapshot(self) -> dict:
        if not self.records:
            return {
                "n_trades": 0,
                "ev_long": 0.0,
                "ev_short": 0.0,
                "win_rate": 0.0,
                "avg_r": 0.0,
                "blacklisted_clusters": 0,
            }
        rs = [r.r_multiple for r in self.records]
        longs = [r.r_multiple for r in self.records if r.direction == "long"]
        shorts = [r.r_multiple for r in self.records if r.direction == "short"]
        wins = sum(1 for r in rs if r > 0)
        # Rough blacklist count: sample centers of each record and test
        bl_count = 0
        # Sample-based: count how many past contexts ARE currently blacklisted
        for r in self.records[-50:]:  # recent only for efficiency
            arr = np.array(r.context)
            ctx = ContextVector(
                vwap_slope=arr[0], ema_dist_atr=arr[1], vp_clearance_atr=arr[2],
                rr_estimate=arr[3], session_hour_bucket=int(arr[4]), vol_regime=arr[5],
            )
            if self.is_blacklisted(ctx, r.direction):
                bl_count += 1
        return {
            "n_trades": len(self.records),
            "ev_long": float(np.mean(longs)) if longs else 0.0,
            "ev_short": float(np.mean(shorts)) if shorts else 0.0,
            "win_rate": wins / len(rs),
            "avg_r": float(np.mean(rs)),
            "blacklisted_clusters": bl_count,
        }


# ===================================================================
# Position + Position Manager (per-variant)
# ===================================================================
@dataclass
class V3Position:
    asset: str
    direction: str
    entry_price: float
    hard_stop: float
    soft_stop_ref: float        # EMA9 +/- buffer
    target_price: float         # first HVN
    size: float                 # margin fraction
    leverage: float
    entry_time: str
    entry_context: ContextVector
    r_distance: float           # abs(entry - hard_stop), in price


class VariantPM:
    """Position manager per variant."""

    def __init__(self, variant_name: str, config: dict):
        self.name = variant_name
        self.config = config
        self.capital = INITIAL_CAPITAL
        self.initial_capital = INITIAL_CAPITAL
        self.positions: dict[str, V3Position] = {}
        self.trade_log: list[dict] = []
        self.pnl_history: list[float] = [INITIAL_CAPITAL]
        self.peak_capital = INITIAL_CAPITAL
        self.memory = ContextMemory(variant_name)
        self.signals_considered = 0
        self.signals_blocked_chop = 0
        self.signals_blocked_rr = 0
        self.signals_blocked_memory = 0
        self.signals_executed = 0

    def try_open(self, asset: str, direction: str, entry: float, hard_stop: float,
                 target: float, soft_stop_ref: float, ctx: ContextVector) -> str | None:
        """Returns None on success, error reason string on block."""
        if asset in self.positions:
            return "already_open"

        # Memory blacklist check (only if memory enabled)
        if self.config["memory"] and self.memory.is_blacklisted(ctx, direction):
            self.signals_blocked_memory += 1
            return "memory_blacklist"

        r_dist = abs(entry - hard_stop)
        if r_dist <= 0:
            return "zero_r_distance"

        # Position sizing: risk RISK_PER_TRADE of capital across hard stop distance
        # size * leverage * r_dist/entry = RISK_PER_TRADE
        # → margin_notional_pct = RISK_PER_TRADE / (r_dist/entry)
        risk_fraction = r_dist / entry
        if risk_fraction <= 0:
            return "invalid_risk"

        # Memory multiplier adjusts base risk
        mult = 1.0
        if self.config["memory"]:
            mult = self.memory.size_multiplier(ctx, direction,
                                               len(self.memory.records))
        target_notional_pct = (RISK_PER_TRADE * mult) / risk_fraction
        # Cap total capital exposure
        target_notional_pct = min(target_notional_pct, 1.0)
        # Use leverage to achieve target notional with small margin
        # Default: leverage 5x, size = notional / leverage
        leverage = 5.0
        size = target_notional_pct / leverage
        size = max(0.001, min(size, 0.5))  # safety caps

        self.positions[asset] = V3Position(
            asset=asset, direction=direction, entry_price=entry,
            hard_stop=hard_stop, soft_stop_ref=soft_stop_ref, target_price=target,
            size=size, leverage=leverage,
            entry_time=datetime.now(timezone.utc).strftime("%H:%M:%S"),
            entry_context=ctx,
            r_distance=r_dist,
        )
        self.signals_executed += 1
        return None

    def check_exits(self, asset: str, bar: dict, ema9_now: float, atr_now: float) -> str | None:
        """Returns exit_reason if closed, else None."""
        if asset not in self.positions:
            return None
        pos = self.positions[asset]
        h = float(bar["high"])
        lo = float(bar["low"])
        close = float(bar["close"])

        # 1) Hard stop (intrabar immediate)
        if pos.direction == "long" and lo <= pos.hard_stop:
            self._close(asset, pos.hard_stop, "hard_stop")
            return "hard_stop"
        if pos.direction == "short" and h >= pos.hard_stop:
            self._close(asset, pos.hard_stop, "hard_stop")
            return "hard_stop"

        # 2) Target hit (partial — take it all at first HVN for simplicity)
        if pos.direction == "long" and h >= pos.target_price:
            self._close(asset, pos.target_price, "target")
            return "target"
        if pos.direction == "short" and lo <= pos.target_price:
            self._close(asset, pos.target_price, "target")
            return "target"

        # 3) Soft stop — close below (long) or above (short) EMA9 +/- 0.05 ATR
        buffer = 0.05 * atr_now
        if pos.direction == "long" and close < ema9_now - buffer:
            self._close(asset, close, "soft_stop")
            return "soft_stop"
        if pos.direction == "short" and close > ema9_now + buffer:
            self._close(asset, close, "soft_stop")
            return "soft_stop"

        return None

    def _close(self, asset: str, exit_price: float, reason: str):
        pos = self.positions.pop(asset)
        if pos.direction == "long":
            raw_ret = (exit_price / pos.entry_price - 1) * pos.leverage
        else:
            raw_ret = (1 - exit_price / pos.entry_price) * pos.leverage
        net_pct = raw_ret - ROUND_TRIP_COST
        sized_ret = net_pct * pos.size
        self.capital += sized_ret * self.capital
        self.peak_capital = max(self.peak_capital, self.capital)
        self.pnl_history.append(self.capital)

        # R-multiple (before fees, absolute price move vs hard stop distance)
        if pos.direction == "long":
            price_move = exit_price - pos.entry_price
        else:
            price_move = pos.entry_price - exit_price
        r_mult = price_move / pos.r_distance if pos.r_distance > 0 else 0.0

        record = TradeRecord(
            context=pos.entry_context.to_array().tolist(),
            direction=pos.direction,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            r_multiple=r_mult,
            net_pct=net_pct,
            asset=asset,
            timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
        )
        self.memory.add(record)

        self.trade_log.append({
            "asset": asset, "dir": pos.direction,
            "entry": round(pos.entry_price, 4),
            "exit": round(exit_price, 4),
            "target": round(pos.target_price, 4),
            "hard_stop": round(pos.hard_stop, 4),
            "size": round(pos.size, 4),
            "lev": round(pos.leverage, 1),
            "r_mult": round(r_mult, 3),
            "net": round(sized_ret, 6),
            "net_pct": round(net_pct, 6),
            "capital": round(self.capital, 2),
            "reason": reason,
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        })

    def total_return(self) -> float:
        return self.capital / self.initial_capital - 1

    def drawdown(self) -> float:
        if self.peak_capital == 0:
            return 0
        return 1 - self.capital / self.peak_capital

    def win_rate(self) -> float:
        if not self.trade_log:
            return 0.0
        wins = sum(1 for t in self.trade_log if t["net"] > 0)
        return wins / len(self.trade_log)


# ===================================================================
# V3 Engine (main loop, manages all variants)
# ===================================================================
class V3Engine:
    def __init__(self, assets: list[str], port: int = DASH_PORT):
        self.assets = assets
        self.port = port
        self.exchange = ccxt.bybit({"enableRateLimit": True})
        self.history_5m: dict[str, pd.DataFrame] = {}
        self.history_15m: dict[str, pd.DataFrame] = {}
        self.variants: dict[str, VariantPM] = {
            name: VariantPM(name, cfg) for name, cfg in VARIANTS_CONFIG.items()
        }
        self.tick_count = 0
        self.last_save = time.time()
        self.last_15m_check: dict[str, str] = {}  # asset -> last 15m bar ts

    def _symbol(self, asset: str) -> str:
        return f"{asset}/USDT:USDT"

    def _fetch_history(self, asset: str, timeframe: str = "5m",
                       limit: int = HISTORY_BARS) -> pd.DataFrame | None:
        try:
            ohlcv = self.exchange.fetch_ohlcv(self._symbol(asset), timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
            df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
            return df
        except Exception as e:
            print(f"  [{asset} {timeframe}] fetch error: {e}")
            return None

    def _compute_snapshot(self, df: pd.DataFrame) -> MarketSnapshot | None:
        if len(df) < 60:
            return None
        c = df["close"].values
        vwap_arr = IndicatorEngine.session_vwap(df)
        ema_arr = IndicatorEngine.ema(c, 9)
        atr14_arr = IndicatorEngine.atr(df, 14)
        atr60_arr = IndicatorEngine.atr(df, 60)

        atr14_now = float(atr14_arr[-1])
        atr60_now = float(atr60_arr[-1]) if len(atr60_arr) > 0 else atr14_now
        if atr14_now <= 0:
            return None

        # VWAP crosses in last 20 bars
        lb = min(20, len(c) - 1)
        crosses = 0
        for i in range(-lb, 0):
            prev = c[i - 1] - vwap_arr[i - 1]
            curr = c[i] - vwap_arr[i]
            if prev * curr < 0:
                crosses += 1

        vwap_slope_3 = 0.0
        if len(vwap_arr) >= 4:
            vwap_slope_3 = float(vwap_arr[-1] - vwap_arr[-4])

        ts_now = df["ts"].iloc[-1]
        hour = int(ts_now.hour) if hasattr(ts_now, "hour") else 0

        return MarketSnapshot(
            close=float(c[-1]),
            vwap=float(vwap_arr[-1]),
            ema9=float(ema_arr[-1]),
            atr14=atr14_now,
            vwap_slope_3=vwap_slope_3,
            ema_dist_atr=(float(c[-1]) - float(ema_arr[-1])) / atr14_now,
            recent_vwap_crosses=crosses,
            close_vwap_dist_atr=abs(float(c[-1]) - float(vwap_arr[-1])) / atr14_now,
            session_hour=hour,
            vol_regime=atr14_now / max(atr60_now, 1e-9),
        )

    def _make_context(self, snap: MarketSnapshot, vp_distance: float, rr: float) -> ContextVector:
        return ContextVector(
            vwap_slope=snap.vwap_slope_3 / max(snap.atr14, 1e-9),
            ema_dist_atr=snap.ema_dist_atr,
            vp_clearance_atr=vp_distance / max(snap.atr14, 1e-9),
            rr_estimate=rr,
            session_hour_bucket=snap.session_hour // 4,
            vol_regime=snap.vol_regime,
        )

    def _process_variant_on_bar(self, variant_name: str, asset: str,
                                df: pd.DataFrame, bar: dict):
        """Evaluate entries+exits for one variant on a new bar."""
        pm = self.variants[variant_name]
        cfg = pm.config

        snap = self._compute_snapshot(df)
        if snap is None:
            return

        # Exits first (use latest bar's HL and close + current EMA9/ATR)
        pm.check_exits(asset, bar, snap.ema9, snap.atr14)

        # Then entries (only if no existing position)
        if asset in pm.positions:
            return

        # 1. Market state classification
        state = classify_state(df, snap, cfg["chop_strict"])
        if state not in ("LONG_BIAS", "SHORT_BIAS"):
            if state == "VWAP_CHOP":
                pm.signals_blocked_chop += 1
            pm.signals_considered += 1
            return

        # 2. Pullback validity
        if state == "LONG_BIAS":
            valid, pullback_low = long_pullback_valid(df, snap)
            if not valid:
                pm.signals_considered += 1
                return
            entry_price = snap.close  # signal bar close triggers next-bar breakout
            hard_stop = pullback_low - 0.15 * snap.atr14
            soft_stop_ref = snap.ema9 - 0.05 * snap.atr14
            direction = "long"
        else:  # SHORT_BIAS
            valid, pullback_high = short_pullback_valid(df, snap)
            if not valid:
                pm.signals_considered += 1
                return
            entry_price = snap.close
            hard_stop = pullback_high + 0.15 * snap.atr14
            soft_stop_ref = snap.ema9 + 0.05 * snap.atr14
            direction = "short"

        hard_stop_dist = abs(entry_price - hard_stop)
        if hard_stop_dist <= 0:
            return

        # 3. Volume profile clearance + RR
        clear, first_hvn, rr = vp_clearance(
            df, entry_price, direction, snap.atr14, hard_stop_dist, cfg["rr_min"]
        )
        if not clear:
            pm.signals_blocked_rr += 1
            pm.signals_considered += 1
            return

        vp_distance = abs(first_hvn - entry_price)
        ctx = self._make_context(snap, vp_distance, rr)

        # 4. Execute
        result = pm.try_open(
            asset=asset, direction=direction, entry=entry_price,
            hard_stop=hard_stop, target=first_hvn, soft_stop_ref=soft_stop_ref,
            ctx=ctx,
        )
        pm.signals_considered += 1
        if result is None:
            print(f"  [{variant_name} {asset}] {direction.upper()} @{entry_price:.2f} "
                  f"stop={hard_stop:.2f} tgt={first_hvn:.2f} RR={rr:.2f}")

    def init(self):
        print(f"[V3] Parker Brooks + Context Memory | {len(self.assets)} assets "
              f"| {len(VARIANTS_CONFIG)} variants")
        print(f"[V3] Cost: {ROUND_TRIP_COST*100:.2f}% RT | Risk/trade: {RISK_PER_TRADE*100:.1f}%")
        print(f"[V3] Memory warmup: {MEMORY_WARMUP_TRADES} trades")
        for asset in self.assets:
            df5 = self._fetch_history(asset, "5m", HISTORY_BARS)
            df15 = self._fetch_history(asset, "15m", HISTORY_BARS)
            if df5 is not None:
                self.history_5m[asset] = df5
            if df15 is not None:
                self.history_15m[asset] = df15
                self.last_15m_check[asset] = ""
            if df5 is not None:
                print(f"  [{asset}] 5m={len(df5)} 15m={len(df15) if df15 is not None else 0} "
                      f"price=${float(df5['close'].iloc[-1]):,.2f}")
        print(f"[V3] Dashboard API: http://localhost:{self.port}/api/state")

    def tick(self):
        self.tick_count += 1
        for asset in self.assets:
            # --- 5m refresh ---
            if asset in self.history_5m:
                new5 = self._fetch_history(asset, "5m", 5)
                if new5 is not None and len(new5) >= 2:
                    latest = new5.iloc[-2]  # closed bar
                    prev_ts = self.history_5m[asset]["ts"].iloc[-1]
                    if latest["ts"] != prev_ts:
                        # new closed 5m bar available
                        row = new5.iloc[-2:-1]
                        self.history_5m[asset] = pd.concat(
                            [self.history_5m[asset], row], ignore_index=True
                        ).tail(HISTORY_BARS)
                        bar = {
                            "ts": latest["ts"], "open": float(latest["open"]),
                            "high": float(latest["high"]), "low": float(latest["low"]),
                            "close": float(latest["close"]), "volume": float(latest["volume"]),
                        }
                        for name, cfg in VARIANTS_CONFIG.items():
                            if cfg["timeframe"] == "5m":
                                self._process_variant_on_bar(name, asset, self.history_5m[asset], bar)

            # --- 15m refresh (less frequent) ---
            if asset in self.history_15m and self.tick_count % 3 == 0:
                new15 = self._fetch_history(asset, "15m", 5)
                if new15 is not None and len(new15) >= 2:
                    latest = new15.iloc[-2]
                    ts_key = str(latest["ts"])
                    if ts_key != self.last_15m_check.get(asset, ""):
                        self.last_15m_check[asset] = ts_key
                        prev_ts = self.history_15m[asset]["ts"].iloc[-1]
                        if latest["ts"] != prev_ts:
                            row = new15.iloc[-2:-1]
                            self.history_15m[asset] = pd.concat(
                                [self.history_15m[asset], row], ignore_index=True
                            ).tail(HISTORY_BARS)
                            bar = {
                                "ts": latest["ts"], "open": float(latest["open"]),
                                "high": float(latest["high"]), "low": float(latest["low"]),
                                "close": float(latest["close"]), "volume": float(latest["volume"]),
                            }
                            for name, cfg in VARIANTS_CONFIG.items():
                                if cfg["timeframe"] == "15m":
                                    self._process_variant_on_bar(name, asset, self.history_15m[asset], bar)

        if self.tick_count % 5 == 0:
            self._log_tick()
        if time.time() - self.last_save > SAVE_INTERVAL:
            self._save_state()
            self.last_save = time.time()

    def _log_tick(self):
        log_entry: dict[str, Any] = {
            "tick": self.tick_count,
            "t": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "variants": {},
        }
        for name, pm in self.variants.items():
            log_entry["variants"][name] = {
                "ret": round(pm.total_return(), 6),
                "cap": round(pm.capital, 2),
                "trades": len(pm.trade_log),
                "win_rate": round(pm.win_rate(), 3),
                "mem_trades": len(pm.memory.records),
                "blocked_chop": pm.signals_blocked_chop,
                "blocked_rr": pm.signals_blocked_rr,
                "blocked_mem": pm.signals_blocked_memory,
                "positions": len(pm.positions),
            }
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        # Console summary
        parts = []
        for name, pm in self.variants.items():
            parts.append(f"{name.replace('v3-','')}={pm.total_return()*100:+.1f}%/{len(pm.trade_log)}t")
        print(f"  [tick {self.tick_count}] " + " | ".join(parts))

    def snapshot(self) -> dict:
        variants_data = {}
        for name, pm in self.variants.items():
            ms = pm.memory.snapshot()
            variants_data[name] = {
                "name": name,
                "config": pm.config,
                "total_return": pm.total_return(),
                "capital": pm.capital,
                "initial_capital": pm.initial_capital,
                "drawdown": pm.drawdown(),
                "win_rate": pm.win_rate(),
                "total_trades": len(pm.trade_log),
                "positions": [
                    {
                        "asset": p.asset, "dir": p.direction,
                        "entry": p.entry_price, "target": p.target_price,
                        "hard_stop": p.hard_stop, "size": p.size,
                        "lev": p.leverage, "time": p.entry_time,
                    }
                    for p in pm.positions.values()
                ],
                "pnl_history": pm.pnl_history[-300:],
                "trade_log": pm.trade_log[-30:],
                "memory": ms,
                "signals": {
                    "considered": pm.signals_considered,
                    "blocked_chop": pm.signals_blocked_chop,
                    "blocked_rr": pm.signals_blocked_rr,
                    "blocked_memory": pm.signals_blocked_memory,
                    "executed": pm.signals_executed,
                },
            }
        return {
            "tick": self.tick_count,
            "variants": variants_data,
            "assets": self.assets,
            "variant_configs": VARIANTS_CONFIG,
            "memory_warmup": MEMORY_WARMUP_TRADES,
            "memory_full_activation": MEMORY_FULL_ACTIVATION,
        }

    def _save_state(self):
        try:
            state: dict[str, Any] = {
                "tick_count": np.array([self.tick_count]),
            }
            for name, pm in self.variants.items():
                state[f"{name}_capital"] = np.array([pm.capital])
                state[f"{name}_peak"] = np.array([pm.peak_capital])
                state[f"{name}_pnl"] = np.array(pm.pnl_history[-1000:])
            np.savez_compressed(STATE_PATH, **state)
            # Memory saved separately as JSON
            memory_blob = {}
            trade_logs = {}
            for name, pm in self.variants.items():
                memory_blob[name] = [asdict(r) for r in pm.memory.records[-500:]]
                trade_logs[name] = pm.trade_log[-200:]
            with open(MEMORY_PATH, "w") as f:
                json.dump({"memory": memory_blob, "trade_logs": trade_logs}, f)
            print(f"  [save] state + memory persisted")
        except Exception as e:
            print(f"  [save] error: {e}")

    def _load_state(self):
        if not STATE_PATH.exists():
            return
        try:
            d = np.load(STATE_PATH, allow_pickle=True)
            self.tick_count = int(d["tick_count"][0])
            for name, pm in self.variants.items():
                key_cap = f"{name}_capital"
                key_peak = f"{name}_peak"
                key_pnl = f"{name}_pnl"
                if key_cap in d:
                    pm.capital = float(d[key_cap][0])
                if key_peak in d:
                    pm.peak_capital = float(d[key_peak][0])
                if key_pnl in d:
                    pm.pnl_history = d[key_pnl].tolist()
            if MEMORY_PATH.exists():
                with open(MEMORY_PATH) as f:
                    blob = json.load(f)
                mem = blob.get("memory", {})
                tlogs = blob.get("trade_logs", {})
                for name, pm in self.variants.items():
                    for rec in mem.get(name, []):
                        pm.memory.records.append(TradeRecord(**rec))
                    pm.trade_log = tlogs.get(name, [])
            print(f"  [load] tick={self.tick_count} variants restored")
        except Exception as e:
            print(f"  [load] error: {e}")

    def run(self):
        self._load_state()
        self.init()

        DashboardHandler.engine = self
        server = http.server.HTTPServer(("0.0.0.0", self.port), DashboardHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        while True:
            try:
                self.tick()
            except KeyboardInterrupt:
                self._save_state()
                print("\n[V3] Stopped. State saved.")
                break
            except Exception as e:
                print(f"  [error] {e}")
                import traceback
                traceback.print_exc()
            time.sleep(TICK_SEC)


# ===================================================================
# Dashboard (API only — unified dashboard on 8900 renders UI)
# ===================================================================
class DashboardHandler(http.server.BaseHTTPRequestHandler):
    engine: Any = None

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/api/state"):
            body = json.dumps(self.engine.snapshot()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            msg = b"V3 API running. Use /api/state."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", len(msg))
            self.end_headers()
            self.wfile.write(msg)


def main():
    parser = argparse.ArgumentParser(description="V3 Parker Brooks + Context Memory")
    parser.add_argument("--assets", default="ETH,BTC,SOL,XRP")
    parser.add_argument("--port", type=int, default=DASH_PORT)
    args = parser.parse_args()
    assets = [a.strip().upper() for a in args.assets.split(",")]
    V3Engine(assets=assets, port=args.port).run()


if __name__ == "__main__":
    main()
