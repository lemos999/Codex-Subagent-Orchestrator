"""V2 — Prediction Engine.

3 Rules:
  1. Predict what happens next accurately
  2. Use memory space evenly
  3. Goal is maximum profit

NOT contrarian. Pure prediction → trade in predicted direction.

Usage:
    py -3.12 scripts/v2.py [--assets ETH,BTC,SOL,XRP] [--port 8897]

Dashboard:
    http://localhost:8897
"""
from __future__ import annotations

import argparse
import http.server
import json
import math
import sys
import threading
import time
from dataclasses import dataclass
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
STATE_PATH = DATA_DIR / "v2_state.npz"
LOG_PATH = DATA_DIR / "v2.jsonl"
DASH_PORT = 8897
TICK_SEC = 60
HISTORY_BARS = 500
INITIAL_CAPITAL = 10_000.0
SAVE_INTERVAL = 1800

# Cost model (Bybit USDT perp)
TAKER_FEE = 0.00055        # 0.055% per side
SLIPPAGE = 0.0005           # 0.05% estimated
ROUND_TRIP_COST = (TAKER_FEE * 2) + (SLIPPAGE * 2)  # ~0.21%

# Rule 3: profit maximization with safety
KELLY_CAP = 0.25            # fractional Kelly cap
MAX_LEVERAGE = 100           # 1~100x leverage range
TOTAL_EXPOSURE_CAP = 1.0    # max 100% margin across all assets
MIN_EDGE_THRESHOLD = ROUND_TRIP_COST * 1.5  # prediction must exceed 1.5x costs

# Feature config: 28 unique features, 0 duplicates
FEATURE_NAMES = [
    # Price dynamics (6)
    "ret_1", "ret_5", "ret_15", "ret_60", "ret_240", "price_accel",
    # Trend (4)
    "sma_r5", "sma_r20", "sma_r60", "sma_r200",
    # Momentum (4)
    "rsi_14", "rsi_6", "macd_hist", "roc_20",
    # Volatility (4)
    "atr_ratio", "bb_width", "real_vol", "hl_range",
    # Volume (4)
    "vol_ratio", "obv_slope", "vwap_dist", "vol_trend",
    # Microstructure (3)
    "consec_dir", "body_wick", "range_rank",
    # Market structure (3)
    "funding_rate", "hour_sin", "hour_cos",
]
N_FEATURES = len(FEATURE_NAMES)  # 28


# ===================================================================
# EMA Normalizer (replaces Welford — adapts to regime changes)
# ===================================================================
class EMANormalizer:
    """Exponential moving average normalizer. Adapts to non-stationarity."""

    def __init__(self, n: int, alpha: float = 0.01):
        self.n = n
        self.alpha = alpha
        self.mean = np.zeros(n)
        self.var = np.ones(n)
        self.warm = 0

    def update(self, x: np.ndarray):
        self.warm += 1
        a = max(self.alpha, 1.0 / self.warm)  # warm-up: higher alpha early
        self.mean = (1 - a) * self.mean + a * x
        diff = x - self.mean
        self.var = (1 - a) * self.var + a * diff * diff

    def normalize(self, x: np.ndarray) -> np.ndarray:
        return (x - self.mean) / (np.sqrt(self.var) + 1e-8)

    def is_warm(self) -> bool:
        return self.warm >= 50


# ===================================================================
# Feature Engine (28 features, 0 duplicates)
# ===================================================================
class FeatureEngine:
    """Compute 28 unique features from OHLCV."""

    def __init__(self):
        self._prev_ret1 = 0.0  # for price acceleration

    def compute(self, df: pd.DataFrame, funding: float = 0.0) -> np.ndarray | None:
        if len(df) < 250:
            return None
        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        lo = df["low"].values.astype(float)
        v = df["volume"].values.astype(float)
        o = df["open"].values.astype(float)
        ts = df["ts"].iloc[-1]

        feat = np.zeros(N_FEATURES, dtype=np.float64)

        # --- Price dynamics (6) ---
        ret1 = c[-1] / c[-2] - 1 if c[-2] != 0 else 0
        feat[0] = ret1
        feat[1] = c[-1] / c[-6] - 1 if c[-6] != 0 else 0
        feat[2] = c[-1] / c[-16] - 1 if c[-16] != 0 else 0
        feat[3] = c[-1] / c[-61] - 1 if c[-61] != 0 else 0
        feat[4] = c[-1] / c[-241] - 1 if len(c) > 241 and c[-241] != 0 else 0
        feat[5] = ret1 - self._prev_ret1  # acceleration
        self._prev_ret1 = ret1

        # --- Trend (4) ---
        for i, period in enumerate([5, 20, 60, 200]):
            sma = c[-period:].mean() if len(c) >= period else c.mean()
            feat[6 + i] = c[-1] / sma - 1 if sma != 0 else 0

        # --- Momentum (4) ---
        feat[10] = self._rsi_norm(c, 14)
        feat[11] = self._rsi_norm(c, 6)
        feat[12] = self._macd_hist(c)
        feat[13] = c[-1] / c[-21] - 1 if len(c) > 21 and c[-21] != 0 else 0

        # --- Volatility (4) ---
        atr14 = self._atr(h, lo, c, 14)
        atr60 = self._atr(h, lo, c, 60)
        feat[14] = atr14 / atr60 - 1 if atr60 > 0 else 0
        sma20 = c[-20:].mean()
        std20 = c[-20:].std()
        feat[15] = (2 * std20 / sma20) if sma20 > 0 else 0
        rets_20 = np.diff(c[-21:]) / (c[-21:-1] + 1e-10)
        feat[16] = np.std(rets_20) if len(rets_20) > 0 else 0
        feat[17] = (h[-1] - lo[-1]) / c[-1] if c[-1] > 0 else 0

        # --- Volume (4) ---
        vol_sma20 = v[-20:].mean()
        feat[18] = v[-1] / vol_sma20 if vol_sma20 > 0 else 1.0
        obv = np.cumsum(np.sign(np.diff(c[-21:])) * v[-20:])
        feat[19] = (obv[-1] - obv[0]) / (abs(obv[0]) + 1e-10) if len(obv) > 1 else 0
        vwap = np.sum(c[-20:] * v[-20:]) / (np.sum(v[-20:]) + 1e-10)
        feat[20] = c[-1] / vwap - 1 if vwap > 0 else 0
        vol_sma5 = v[-5:].mean()
        vol_sma60 = v[-60:].mean()
        feat[21] = vol_sma5 / vol_sma60 if vol_sma60 > 0 else 1.0

        # --- Microstructure (3) ---
        consec = 0
        for k in range(1, min(20, len(c) - 1)):
            if c[-k] > c[-k - 1]:
                if consec >= 0:
                    consec += 1
                else:
                    break
            elif c[-k] < c[-k - 1]:
                if consec <= 0:
                    consec -= 1
                else:
                    break
            else:
                break
        feat[22] = np.tanh(consec / 5.0)
        body = abs(c[-1] - o[-1])
        wick = h[-1] - lo[-1]
        feat[23] = body / wick if wick > 0 else 0.5
        ranges = h[-50:] - lo[-50:]
        feat[24] = np.searchsorted(np.sort(ranges), h[-1] - lo[-1]) / len(ranges)

        # --- Market structure (3) ---
        feat[25] = funding  # funding rate (from exchange API, cached)
        # Hour cycle: sin+cos encoding for full 24h representation
        hour = ts.hour if hasattr(ts, "hour") else 0
        feat[26] = math.sin(2 * math.pi * hour / 24)
        feat[27] = math.cos(2 * math.pi * hour / 24)

        return feat

    def _rsi_norm(self, c: np.ndarray, period: int) -> float:
        """RSI normalized to [-1, 1]."""
        if len(c) < period + 1:
            return 0.0
        delta = np.diff(c[-(period + 1):])
        gain = np.mean(np.maximum(delta, 0))
        loss = np.mean(np.maximum(-delta, 0))
        if loss == 0:
            return 1.0
        rs = gain / loss
        rsi = 100.0 - 100.0 / (1.0 + rs)
        return (rsi - 50) / 50

    def _macd_hist(self, c: np.ndarray) -> float:
        if len(c) < 35:
            return 0.0
        s = pd.Series(c)
        macd_line = s.ewm(span=12).mean().iloc[-1] - s.ewm(span=26).mean().iloc[-1]
        macd_series = s.ewm(span=12).mean() - s.ewm(span=26).mean()
        signal_line = macd_series.ewm(span=9).mean().iloc[-1]
        return (macd_line - signal_line) / c[-1] if c[-1] > 0 else 0.0

    def _atr(self, h, lo, c, period: int) -> float:
        if len(h) < period + 1:
            return 0.0
        tr = np.maximum(
            h[-period:] - lo[-period:],
            np.maximum(
                np.abs(h[-period:] - c[-period - 1:-1]),
                np.abs(lo[-period:] - c[-period - 1:-1]),
            ),
        )
        return float(tr.mean())


# ===================================================================
# Rule 1+2: Online Predictor (per-asset, entropy memory balancing)
# ===================================================================
class OnlinePredictor:
    """SGD ridge with EMA normalization + entropy-based memory balancing.

    Rule 1: Predict accurately (tracks direction accuracy, calibration).
    Rule 2: Use memory evenly (adaptive L2 via feature importance entropy).
    """

    def __init__(self, n: int = N_FEATURES, lr: float = 0.003,
                 base_l2: float = 0.001, memory_alpha: float = 2.0):
        self.n = n
        self.w = np.random.randn(n) * 0.0001
        self.b = 0.0
        self.lr = lr
        self.base_l2 = base_l2
        self.memory_alpha = memory_alpha
        self.l2_per_feat = np.full(n, base_l2)
        self.norm = EMANormalizer(n)

        # Tracking
        self.predictions: list[float] = []
        self.actuals: list[float] = []
        self.accuracy_history: list[float] = []
        self.entropy_history: list[float] = []
        self.feature_importance = np.ones(n) / n

    def predict(self, x: np.ndarray) -> float:
        """Predict next-bar return."""
        x_n = self.norm.normalize(x)
        return float(np.dot(self.w, x_n) + self.b)

    def update(self, x_prev: np.ndarray, y_true: float):
        """Learn from previous features → actual return. Proper t+1 labeling."""
        # Update normalizer with previous features
        self.norm.update(x_prev)
        x_n = self.norm.normalize(x_prev)

        y_pred = float(np.dot(self.w, x_n) + self.b)
        error = y_pred - y_true

        # SGD with per-feature L2
        grad_w = error * x_n + self.l2_per_feat * self.w
        grad_b = error

        # Gradient clipping (protect against outliers)
        grad_norm = np.linalg.norm(grad_w)
        if grad_norm > 1.0:
            grad_w = grad_w / grad_norm
        grad_b = np.clip(grad_b, -1.0, 1.0)  # clip bias gradient too

        self.w -= self.lr * grad_w
        self.b -= self.lr * grad_b

        # Track
        self.predictions.append(y_pred)
        self.actuals.append(y_true)

        # Rule 2: rebalance memory
        self._rebalance_memory()

        # Direction accuracy (rolling 50)
        if len(self.predictions) >= 10:
            recent_p = self.predictions[-50:]
            recent_a = self.actuals[-50:]
            correct = sum(
                1 for p, a in zip(recent_p, recent_a)
                if (p > 0) == (a > 0)
            )
            self.accuracy_history.append(correct / len(recent_p))

    def _rebalance_memory(self):
        """Rule 2: Adaptive L2 + exploration noise to keep entropy high."""
        # FIX: importance = |w| only (normalized model, sqrt(var) was wrong)
        imp = np.abs(self.w)
        imp_sum = imp.sum()
        if imp_sum < 1e-10:
            self.feature_importance = np.ones(self.n) / self.n
            self.entropy_history.append(1.0)
            return

        p = imp / imp_sum
        self.feature_importance = p

        # Entropy (NaN-safe)
        safe_p = np.clip(p, 1e-10, 1.0)
        entropy = -np.sum(safe_p * np.log(safe_p))
        max_entropy = np.log(self.n)
        self.entropy_history.append(entropy / max_entropy)

        # Adaptive L2: penalize overused features
        uniform = 1.0 / self.n
        excess = np.maximum(p - uniform, 0)
        self.l2_per_feat = self.base_l2 * (1.0 + self.memory_alpha * excess * self.n)

        # FIX: exploration noise for underused features (L2 only shrinks, can't grow)
        deficit = np.maximum(uniform - p, 0)
        if deficit.sum() > 0:
            noise_scale = self.lr * 0.1 * deficit * self.n
            self.w += np.random.randn(self.n) * noise_scale

    def memory_entropy(self) -> float:
        if not self.entropy_history:
            return 1.0
        return self.entropy_history[-1]

    def direction_accuracy(self) -> float:
        if not self.accuracy_history:
            return 0.5
        return self.accuracy_history[-1]

    def calibration(self) -> float:
        """Trust score [0, 1]. High accuracy + high entropy + enough data = high trust."""
        acc = self.direction_accuracy()
        ent = self.memory_entropy()
        # FIX: entropy floor to prevent deadlock (low ent → no trade → no learn → ent stays low)
        ent_factor = max(ent, 0.3)
        n_samples = min(len(self.predictions), 200)
        warmup = min(n_samples / 50, 1.0)
        return acc * ent_factor * warmup


# ===================================================================
# Rule 3: Position Manager (cost-aware, Kelly-capped, exposure-capped)
# ===================================================================
@dataclass
class Position:
    direction: str
    entry_price: float
    size: float          # margin fraction (0~1)
    leverage: float      # 1~100x
    entry_time: str
    asset: str
    entry_prediction: float


class PositionManager:
    """Fractional Kelly sizing with costs. Maximum profit within safety bounds."""

    def __init__(self, capital: float = INITIAL_CAPITAL):
        self.capital = capital
        self.initial_capital = capital
        self.positions: dict[str, Position] = {}
        self.trade_returns: list[float] = []
        self.trade_log: list[dict] = []
        self.pnl_history: list[float] = [capital]
        self.peak_capital = capital

    def kelly_fraction(self) -> float:
        if len(self.trade_returns) < 30:
            return 0.05  # very conservative until enough data
        rets = np.array(self.trade_returns[-200:])
        wins = rets[rets > 0]
        losses = rets[rets < 0]
        if len(wins) == 0:
            return 0.02
        if len(losses) == 0:
            return 0.15
        win_rate = len(wins) / len(rets)
        avg_win = float(wins.mean())
        avg_loss = float(abs(losses.mean()))
        if avg_loss < 1e-10:
            return 0.15
        payoff = avg_win / avg_loss
        kelly = (win_rate * payoff - (1 - win_rate)) / payoff
        return float(np.clip(kelly, 0.01, KELLY_CAP))

    def current_exposure(self) -> float:
        """Total margin usage across all assets."""
        return sum(p.size for p in self.positions.values())

    def current_notional(self) -> float:
        """Total leveraged notional exposure."""
        return sum(p.size * p.leverage for p in self.positions.values())

    def open_position(self, asset: str, direction: str, price: float,
                      prediction_strength: float, calibration: float):
        if asset in self.positions:
            return
        # Check total exposure cap
        if self.current_exposure() >= TOTAL_EXPOSURE_CAP:
            return
        kelly = self.kelly_fraction()
        size = kelly * min(prediction_strength, 1.0) * calibration
        size = np.clip(size, 0.01, TOTAL_EXPOSURE_CAP - self.current_exposure())
        # Leverage: scales with calibration. Low confidence → 1x, high → up to MAX
        leverage = max(1.0, round(calibration * prediction_strength * MAX_LEVERAGE))
        leverage = min(leverage, MAX_LEVERAGE)
        self.positions[asset] = Position(
            direction=direction, entry_price=price, size=size,
            leverage=leverage,
            entry_time=datetime.now(timezone.utc).strftime("%H:%M:%S"),
            asset=asset, entry_prediction=prediction_strength,
        )

    def close_position(self, asset: str, price: float) -> float | None:
        if asset not in self.positions:
            return None
        pos = self.positions.pop(asset)
        # Raw return with leverage
        if pos.direction == "long":
            raw_ret = (price / pos.entry_price - 1) * pos.leverage
        else:
            raw_ret = (1 - price / pos.entry_price) * pos.leverage
        # Deduct round-trip cost — store RAW return for Kelly (not size-weighted)
        net_pct = raw_ret - ROUND_TRIP_COST  # net return percentage (unweighted)
        self.trade_returns.append(net_pct)     # Kelly uses unweighted returns
        sized_ret = net_pct * pos.size         # actual capital impact
        self.capital += sized_ret * self.capital
        self.pnl_history.append(self.capital)
        self.peak_capital = max(self.peak_capital, self.capital)
        self.trade_log.append({
            "asset": asset, "dir": pos.direction,
            "entry": round(pos.entry_price, 2),
            "exit": round(price, 2),
            "size": round(pos.size, 4),
            "lev": round(pos.leverage, 1),
            "raw": round(raw_ret, 6),
            "cost": round(ROUND_TRIP_COST, 6),
            "net": round(sized_ret, 6),
            "capital": round(self.capital, 2),
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        })
        return sized_ret

    def total_return(self) -> float:
        return self.capital / self.initial_capital - 1

    def drawdown(self) -> float:
        if self.peak_capital == 0:
            return 0
        return 1 - self.capital / self.peak_capital


# ===================================================================
# Dashboard
# ===================================================================
class DashboardHandler(http.server.BaseHTTPRequestHandler):
    engine: Any = None

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/api/state":
            body = json.dumps(self.engine.snapshot()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            body = DASHBOARD_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)


DASHBOARD_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>V2 Prediction Engine</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Courier New',monospace;background:#0a0a0a;color:#e0e0e0;padding:16px}
h1{color:#00ccff;font-size:22px;margin-bottom:4px}
.sub{font-size:11px;color:#555;margin-bottom:16px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:12px}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.c{background:#111;border:1px solid #222;border-radius:6px;padding:12px}
.c h2{font-size:11px;color:#666;text-transform:uppercase;margin-bottom:6px}
.big{font-size:26px;font-weight:bold}
.grn{color:#00ff88}.red{color:#ff4466}.ylw{color:#ffcc00}.cyn{color:#00ccff}
canvas{width:100%;height:160px;background:#0a0a0a;border-radius:4px}
.bars{display:flex;flex-wrap:wrap;gap:1px;margin-top:6px}
.bar{width:18px;border-radius:2px;position:relative}
.bar-l{font-size:6px;color:#444;text-align:center;margin-top:2px}
.log{max-height:180px;overflow-y:auto;font-size:10px;line-height:1.5}
.log-e{border-bottom:1px solid #1a1a1a;padding:1px 0}
.cost-tag{background:#331100;color:#ff8800;font-size:9px;padding:1px 4px;border-radius:3px}
</style></head><body>
<h1>V2 PREDICTION ENGINE</h1>
<div class="sub">Rule 1: Predict | Rule 2: Even Memory | Rule 3: Max Profit | Cost: """ + f"{ROUND_TRIP_COST*100:.2f}%" + """ round-trip</div>
<div class="g3">
  <div class="c"><h2>Rule 1: Prediction Accuracy</h2><div id="acc" class="big cyn">--</div>
    <div id="acc-d" style="font-size:10px;color:#555;margin-top:4px"></div></div>
  <div class="c"><h2>Rule 2: Memory Entropy</h2><div id="ent" class="big ylw">--</div>
    <div id="ent-d" style="font-size:10px;color:#555;margin-top:4px"></div></div>
  <div class="c"><h2>Rule 3: Net Return</h2><div id="ret" class="big grn">--</div>
    <div id="ret-d" style="font-size:10px;color:#555;margin-top:4px"></div></div>
</div>
<div class="g2">
  <div class="c"><h2>Memory Map (28 features)</h2><div id="mm" class="bars"></div></div>
  <div class="c"><h2>Positions (exposure cap """ + f"{TOTAL_EXPOSURE_CAP*100:.0f}%" + """)</h2>
    <div id="pos"></div><div id="kelly" style="margin-top:6px;font-size:11px;color:#555"></div></div>
</div>
<div class="g2">
  <div class="c"><h2>PnL (net of costs)</h2><canvas id="cv-pnl"></canvas></div>
  <div class="c"><h2>Accuracy</h2><canvas id="cv-acc"></canvas></div>
</div>
<div class="c" style="margin-top:10px"><h2>Trade Log (cost-adjusted)</h2><div id="log" class="log"></div></div>
<script>
const q=s=>document.querySelector(s);
const fmt=(v,d=2)=>(v*100).toFixed(d)+'%';
function line(id,data,color,bl){
  const cv=q('#'+id),ctx=cv.getContext('2d');
  const W=cv.width=cv.offsetWidth,H=cv.height=160;
  ctx.clearRect(0,0,W,H);
  if(!data||data.length<2)return;
  const mn=Math.min(...data),mx=Math.max(...data),r=mx-mn||1;
  if(bl!==undefined){ctx.strokeStyle='#222';ctx.lineWidth=1;ctx.beginPath();
    const by=H-(bl-mn)/r*H;ctx.moveTo(0,by);ctx.lineTo(W,by);ctx.stroke();}
  ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();
  data.forEach((v,i)=>{const x=i/(data.length-1)*W,y=H-(v-mn)/r*H;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
  ctx.stroke();
}
function renderMM(imp,names){
  const el=q('#mm');if(!imp||!imp.length){el.innerHTML='warming up...';return;}
  const mx=Math.max(...imp);
  el.innerHTML=imp.map((v,i)=>{
    const h=Math.max(3,(v/mx)*36);
    const hue=120*(1-v*imp.length);
    return `<div><div class="bar" style="height:${h}px;width:18px;background:hsl(${Math.max(0,hue)},70%,45%)" title="${names[i]}: ${(v*100).toFixed(1)}%"></div><div class="bar-l">${names[i].slice(0,3)}</div></div>`;
  }).join('');
}
async function tick(){
  try{
    const d=await(await fetch('/api/state')).json();
    q('#acc').textContent=fmt(d.accuracy);
    q('#acc').className='big '+(d.accuracy>0.52?'grn':d.accuracy>0.48?'ylw':'red');
    q('#acc-d').textContent=d.total_predictions+' predictions';
    q('#ent').textContent=fmt(d.entropy,1);
    q('#ent').className='big '+(d.entropy>0.8?'grn':d.entropy>0.6?'ylw':'red');
    q('#ent-d').textContent=d.entropy>0.8?'balanced':'rebalancing...';
    q('#ret').textContent=fmt(d.total_return);
    q('#ret').className='big '+(d.total_return>0?'grn':'red');
    q('#ret-d').textContent=`$${d.capital.toFixed(0)} | DD ${fmt(d.drawdown)} | Kelly ${fmt(d.kelly)} | Exp ${fmt(d.exposure)}`;
    renderMM(d.feature_importance,d.feature_names);
    let ph='';
    if(!d.positions.length)ph='<span style="color:#444">no positions</span>';
    else d.positions.forEach(p=>{
      ph+=`<div><span class="${p.dir==='long'?'grn':'red'}">${p.dir.toUpperCase()}</span> ${p.asset} @${p.entry} (${(p.size*100).toFixed(1)}%) ${p.time}</div>`;
    });
    q('#pos').innerHTML=ph;
    q('#kelly').textContent=`Kelly: ${fmt(d.kelly)} | Exposure: ${fmt(d.exposure)} / ${fmt(d.exposure_cap)}`;
    line('cv-pnl',d.pnl_history,'#00ff88',d.initial_capital);
    line('cv-acc',d.accuracy_history,'#00ccff',0.5);
    let lh='';
    (d.trade_log||[]).slice(-30).reverse().forEach(t=>{
      lh+=`<div class="log-e"><span class="${t.net>0?'grn':'red'}">${t.dir}</span> ${t.asset} ${t.entry}->${t.exit} sz=${(t.size*100).toFixed(1)}% raw=${fmt(t.raw)} <span class="cost-tag">-${fmt(t.cost)}</span> net=${fmt(t.net)} $${t.capital.toFixed(0)}</div>`;
    });
    q('#log').innerHTML=lh||'<span style="color:#444">no trades yet</span>';
  }catch(e){}
}
setInterval(tick,5000);tick();
</script></body></html>"""


# ===================================================================
# V2 Engine (main loop)
# ===================================================================
class V2Engine:
    def __init__(self, assets: list[str], port: int = DASH_PORT):
        self.assets = assets
        self.port = port
        self.exchange = ccxt.bybit({"enableRateLimit": True})
        self.feature_engines: dict[str, FeatureEngine] = {
            a: FeatureEngine() for a in assets
        }
        # Per-asset predictors (Rule 1: each asset gets its own model)
        self.predictors: dict[str, OnlinePredictor] = {
            a: OnlinePredictor() for a in assets
        }
        self.pm = PositionManager()
        self.history: dict[str, pd.DataFrame] = {}
        self.prices: dict[str, float] = {}
        self.tick_count = 0
        self.last_save = time.time()

        # t+1 labeling: store previous tick's features per asset
        self.prev_features: dict[str, np.ndarray] = {}
        # Cache funding rates between fetches
        self._last_funding: dict[str, float] = {a: 0.0 for a in assets}

    def _symbol(self, asset: str) -> str:
        return f"{asset}/USDT:USDT"

    def _fetch_funding(self, asset: str) -> float:
        """Fetch funding rate. Returns 0 on failure."""
        try:
            info = self.exchange.fetch_funding_rate(self._symbol(asset))
            return float(info.get("fundingRate", 0) or 0)
        except Exception:
            return 0.0

    def _fetch_history(self, asset: str) -> pd.DataFrame | None:
        try:
            ohlcv = self.exchange.fetch_ohlcv(self._symbol(asset), "1m", limit=HISTORY_BARS)
            df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
            df["ts"] = pd.to_datetime(df["ts"], unit="ms")
            return df
        except Exception as e:
            print(f"  [{asset}] fetch error: {e}")
            return None

    def _fetch_latest(self, asset: str) -> dict | None:
        """Fetch the most recent CLOSED bar (not the open candle)."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(self._symbol(asset), "1m", limit=3)
            if len(ohlcv) < 2:
                return None
            # Use [-2] = last fully closed bar. [-1] may be an open candle.
            bar = ohlcv[-2]
            return {
                "ts": pd.Timestamp(bar[0], unit="ms"),
                "open": bar[1], "high": bar[2], "low": bar[3],
                "close": bar[4], "volume": bar[5],
            }
        except Exception:
            return None

    def init(self):
        print(f"[V2] Initializing {len(self.assets)} assets...")
        print(f"[V2] Cost model: {ROUND_TRIP_COST*100:.2f}% round-trip")
        print(f"[V2] Kelly cap: {KELLY_CAP*100:.0f}% | Exposure cap: {TOTAL_EXPOSURE_CAP*100:.0f}%")
        for asset in self.assets:
            df = self._fetch_history(asset)
            if df is not None:
                self.history[asset] = df
                self.prices[asset] = float(df["close"].iloc[-1])
                print(f"  [{asset}] {len(df)} bars, ${self.prices[asset]:,.2f}")
        print(f"[V2] Dashboard: http://localhost:{self.port}")

    def tick(self):
        self.tick_count += 1

        for asset in self.assets:
            if asset not in self.history:
                continue

            # Fetch new bar
            bar = self._fetch_latest(asset)
            if bar is None:
                # API error — do NOT skip position management
                # Close positions if we can't get price (safety)
                if asset in self.pm.positions and self.tick_count % 5 == 0:
                    print(f"  [{asset}] WARNING: API error, keeping position")
                continue

            # Update history
            new_row = pd.DataFrame([bar])
            self.history[asset] = pd.concat(
                [self.history[asset], new_row], ignore_index=True
            ).tail(HISTORY_BARS)

            price = float(bar["close"])
            self.prices[asset] = price

            # Fetch funding (every 30 ticks to avoid rate limits), cache between fetches
            if self.tick_count % 30 == 1:
                fr = self._fetch_funding(asset)
                if fr != 0.0:
                    self._last_funding[asset] = fr
            funding = self._last_funding.get(asset, 0.0)

            # Compute features
            fe = self.feature_engines[asset]
            features = fe.compute(self.history[asset], funding)
            if features is None:
                continue

            predictor = self.predictors[asset]

            # === PROPER t+1 LABELING ===
            # Update model: previous features → current return (features[0])
            if asset in self.prev_features:
                actual_return = features[0]  # ret_1 of current bar
                predictor.update(self.prev_features[asset], actual_return)

            # Predict NEXT bar's return from current features
            prediction = predictor.predict(features)

            # Store for next tick's update
            self.prev_features[asset] = features.copy()

            # === POSITION MANAGEMENT ===
            if asset in self.pm.positions:
                pos = self.pm.positions[asset]
                should_exit = False

                # Exit if prediction flips direction
                if pos.direction == "long" and prediction < -MIN_EDGE_THRESHOLD:
                    should_exit = True
                elif pos.direction == "short" and prediction > MIN_EDGE_THRESHOLD:
                    should_exit = True
                # Exit if prediction drops to noise level
                elif abs(prediction) < MIN_EDGE_THRESHOLD * 0.5:
                    should_exit = True

                if should_exit:
                    ret = self.pm.close_position(asset, price)
                    if ret is not None:
                        tag = "WIN" if ret > 0 else "LOSS"
                        print(f"  [{asset}] CLOSE {tag} net={ret:+.4%} cap=${self.pm.capital:,.0f}")

            # === ENTRY: pure prediction-based ===
            elif abs(prediction) > MIN_EDGE_THRESHOLD and predictor.norm.is_warm():
                direction = "long" if prediction > 0 else "short"
                cal = predictor.calibration()
                if cal > 0.05:  # minimum trust
                    pred_strength = min(abs(prediction) / MIN_EDGE_THRESHOLD, 3.0) / 3.0
                    self.pm.open_position(asset, direction, price, pred_strength, cal)
                    pos = self.pm.positions.get(asset)
                    lev = pos.leverage if pos else 1
                    print(f"  [{asset}] OPEN {direction} @${price:,.2f} "
                          f"pred={prediction:+.6f} cal={cal:.2f} "
                          f"lev={lev:.0f}x kelly={self.pm.kelly_fraction():.2f}")

        # Periodic log
        if self.tick_count % 5 == 0:
            self._log_tick()

        # Save state
        if time.time() - self.last_save > SAVE_INTERVAL:
            self._save_state()
            self.last_save = time.time()

    def _log_tick(self):
        # Aggregate metrics across all asset predictors
        accs = [p.direction_accuracy() for p in self.predictors.values()]
        ents = [p.memory_entropy() for p in self.predictors.values()]
        avg_acc = np.mean(accs) if accs else 0.5
        avg_ent = np.mean(ents) if ents else 1.0
        total_preds = sum(len(p.predictions) for p in self.predictors.values())

        log_entry = {
            "tick": self.tick_count,
            "t": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "acc": round(avg_acc, 4),
            "entropy": round(avg_ent, 4),
            "ret": round(self.pm.total_return(), 6),
            "capital": round(self.pm.capital, 2),
            "trades": len(self.pm.trade_returns),
            "positions": len(self.pm.positions),
            "exposure": round(self.pm.current_exposure(), 4),
            "predictions": total_preds,
        }
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        print(f"  [tick {self.tick_count}] acc={avg_acc:.1%} ent={avg_ent:.1%} "
              f"ret={self.pm.total_return():+.2%} trades={len(self.pm.trade_returns)} "
              f"exp={self.pm.current_exposure():.1%}")

    def snapshot(self) -> dict:
        accs = [p.direction_accuracy() for p in self.predictors.values()]
        ents = [p.memory_entropy() for p in self.predictors.values()]
        # Use first predictor's feature importance for display (or average)
        fi = np.mean(
            [p.feature_importance for p in self.predictors.values()], axis=0
        ).tolist() if self.predictors else [1 / N_FEATURES] * N_FEATURES

        # Aggregate accuracy history: average across assets per time step
        max_len = max((len(p.accuracy_history) for p in self.predictors.values()), default=0)
        all_acc = []
        for i in range(max(0, max_len - 500), max_len):
            vals = [p.accuracy_history[i] for p in self.predictors.values()
                    if i < len(p.accuracy_history)]
            if vals:
                all_acc.append(float(np.mean(vals)))

        return {
            "tick": self.tick_count,
            "accuracy": float(np.mean(accs)) if accs else 0.5,
            "entropy": float(np.mean(ents)) if ents else 1.0,
            "total_return": self.pm.total_return(),
            "capital": self.pm.capital,
            "initial_capital": self.pm.initial_capital,
            "drawdown": self.pm.drawdown(),
            "kelly": self.pm.kelly_fraction(),
            "exposure": self.pm.current_exposure(),
            "exposure_cap": TOTAL_EXPOSURE_CAP,
            "total_predictions": sum(len(p.predictions) for p in self.predictors.values()),
            "feature_names": FEATURE_NAMES,
            "feature_importance": fi,
            "pnl_history": self.pm.pnl_history[-500:],
            "accuracy_history": all_acc[-500:],
            "notional": self.pm.current_notional(),
            "max_leverage": MAX_LEVERAGE,
            "total_trades": len(self.pm.trade_returns),
            "positions": [
                {"asset": p.asset, "dir": p.direction,
                 "entry": p.entry_price, "size": p.size,
                 "lev": p.leverage, "time": p.entry_time}
                for p in self.pm.positions.values()
            ],
            "trade_log": self.pm.trade_log[-50:],
        }

    def _save_state(self):
        try:
            state = {"tick_count": np.array([self.tick_count]),
                     "capital": np.array([self.pm.capital]),
                     "trade_returns": np.array(self.pm.trade_returns[-1000:])}
            for asset, pred in self.predictors.items():
                state[f"{asset}_w"] = pred.w
                state[f"{asset}_b"] = np.array([pred.b])
                state[f"{asset}_mean"] = pred.norm.mean
                state[f"{asset}_var"] = pred.norm.var
                state[f"{asset}_warm"] = np.array([pred.norm.warm])
            np.savez_compressed(STATE_PATH, **state)
            print(f"  [save] state → {STATE_PATH}")
        except Exception as e:
            print(f"  [save] error: {e}")

    def _load_state(self):
        if not STATE_PATH.exists():
            return
        try:
            d = np.load(STATE_PATH, allow_pickle=True)
            self.tick_count = int(d["tick_count"][0])
            self.pm.capital = float(d["capital"][0])
            self.pm.trade_returns = d["trade_returns"].tolist()
            for asset in self.assets:
                if f"{asset}_w" in d:
                    pred = self.predictors[asset]
                    pred.w = d[f"{asset}_w"]
                    pred.b = float(d[f"{asset}_b"][0])
                    pred.norm.mean = d[f"{asset}_mean"]
                    pred.norm.var = d[f"{asset}_var"]
                    pred.norm.warm = int(d[f"{asset}_warm"][0])
            print(f"  [load] tick={self.tick_count} cap=${self.pm.capital:,.0f}")
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
                print("\n[V2] Stopped. State saved.")
                break
            except Exception as e:
                print(f"  [error] {e}")
            time.sleep(TICK_SEC)


def main():
    parser = argparse.ArgumentParser(description="V2 Prediction Engine")
    parser.add_argument("--assets", default="ETH,BTC,SOL,XRP")
    parser.add_argument("--port", type=int, default=DASH_PORT)
    args = parser.parse_args()
    assets = [a.strip().upper() for a in args.assets.split(",")]
    V2Engine(assets=assets, port=args.port).run()


if __name__ == "__main__":
    main()
