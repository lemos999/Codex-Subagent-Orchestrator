"""Conviction Engine - No binary limits. Continuous positioning.

Instead of: "enter when ALL conditions met" (waits forever)
This does:  "always express a view, size = conviction level"

Each signal contributes to a conviction score (0 to 1).
Position size = conviction * max_leverage.
Rebalance every cycle. No waiting.

Usage:
    py -3.12 scripts/conviction_engine.py
"""
from __future__ import annotations
import json, sys, threading, time, http.server
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd

# DL integration (graceful fallback if not available)
_dl_predictor = None
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from dl_integration import DLPredictor
except ImportError:
    DLPredictor = None

try:
    import ccxt
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, "-m", "pip", "install", "ccxt"]); import ccxt
try:
    import yfinance as yf
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"]); import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DASH_PORT = 8895
INITIAL = 10_000.0
CYCLE_SEC = 60
REBALANCE_THRESHOLD = 0.05  # rebalance if conviction changes > 5%


def sma(arr, w):
    n = len(arr); out = np.full(n, np.nan)
    cs = np.cumsum(arr); cs = np.insert(cs, 0, 0)
    if n >= w: out[w-1:] = (cs[w:] - cs[:-w]) / w
    return out


def compute_conviction(c, h, lo, v, max_leverage):
    """Compute conviction score from multiple signals. Returns 0 to 1."""
    n = len(c)
    if n < 200: return 0.0, {}

    # 1. Trend alignment (MA20 > MA50 > MA200)
    ma20 = sma(c, 20); ma50 = sma(c, 50); ma200 = sma(c, 200)
    i = n - 1
    if any(np.isnan(x[i]) for x in [ma20, ma50, ma200]):
        return 0.0, {}

    trend_score = 0.0
    if c[i] > ma20[i]: trend_score += 0.15
    if ma20[i] > ma50[i]: trend_score += 0.15
    if ma50[i] > ma200[i]: trend_score += 0.10
    if c[i] > ma200[i]: trend_score += 0.10
    # Trend strength: distance from MA200
    trend_dist = (c[i] - ma200[i]) / ma200[i]
    trend_score += max(0, min(0.10, trend_dist * 2))  # up to +0.10 for strong trend

    # 2. RSI mean reversion opportunity
    delta = np.diff(c, prepend=c[0])
    gain = np.where(delta > 0, delta, 0.0); loss_arr = np.where(delta < 0, -delta, 0.0)
    avg_g = sma(gain, 14); avg_l = sma(loss_arr, 14)
    rsi = 50.0
    if avg_l[i] > 0: rsi = 100 - 100 / (1 + avg_g[i] / avg_l[i])

    rsi_score = 0.0
    if rsi < 30: rsi_score = 0.20      # extreme oversold - strong buy
    elif rsi < 40: rsi_score = 0.12    # moderate oversold
    elif rsi < 50: rsi_score = 0.05    # slight pullback
    elif rsi > 70: rsi_score = -0.15   # overbought - reduce
    elif rsi > 60: rsi_score = -0.05   # slightly overbought

    # 3. Volume confirmation
    vol_ma = sma(v, 20)
    vol_score = 0.0
    if not np.isnan(vol_ma[i]) and vol_ma[i] > 0:
        vol_ratio = v[i] / vol_ma[i]
        if vol_ratio > 2.0: vol_score = 0.10
        elif vol_ratio > 1.5: vol_score = 0.05
        elif vol_ratio < 0.5: vol_score = -0.05  # low volume = less conviction

    # 4. Momentum (multi-timeframe)
    mom_score = 0.0
    for lookback in [4, 12, 48]:
        if i >= lookback:
            ret = (c[i] / c[i - lookback] - 1)
            if ret > 0.02: mom_score += 0.03
            elif ret > 0: mom_score += 0.01
            elif ret < -0.02: mom_score -= 0.03

    # 5. ATR regime (low vol = trend continuation likely)
    tr = np.maximum(h[1:] - lo[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(lo[1:] - c[:-1])))
    tr = np.insert(tr, 0, h[0] - lo[0])
    atr = sma(tr, 14)
    atr_score = 0.0
    if not np.isnan(atr[i]) and c[i] > 0:
        atr_pct = atr[i] / c[i] * 100
        if atr_pct < 1.5: atr_score = 0.05  # low vol, trend mode
        elif atr_pct > 4.0: atr_score = -0.05  # high vol, risky

    # Total conviction (clamp 0 to 1)
    raw = trend_score + rsi_score + vol_score + mom_score + atr_score
    # Rules-based max 0.60; DL boost can add up to 0.40
    conviction = max(0.0, min(0.60, raw))

    details = {
        "trend": round(trend_score, 3), "rsi": round(rsi_score, 3),
        "volume": round(vol_score, 3), "momentum": round(mom_score, 3),
        "volatility": round(atr_score, 3), "raw": round(raw, 3),
        "conviction": round(conviction, 3),
        "rsi_value": round(rsi, 1),
        "ma20": round(float(ma20[i]), 2), "ma50": round(float(ma50[i]), 2),
        "ma200": round(float(ma200[i]), 2),
    }
    return conviction, details


@dataclass
class AssetState:
    symbol: str = ""
    asset_type: str = ""
    balance: float = INITIAL
    position: str = "FLAT"
    conviction: float = 0.0
    target_size: float = 0.0  # 0 to max_leverage
    current_size: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    current_pnl_pct: float = 0.0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    peak_balance: float = INITIAL
    max_drawdown_pct: float = 0.0
    max_leverage: float = 2.0
    last_update: str = ""
    started_at: str = ""
    total_checks: int = 0
    conviction_details: dict = field(default_factory=dict)
    trades: list = field(default_factory=list)
    activity_log: list = field(default_factory=list)
    evolution_log: list = field(default_factory=list)
    last_analysis_at: int = 0


ASSETS = {
    "ETH": {"type": "crypto", "ccxt": "ETH/USDT:USDT", "tf": "15m", "max_lev": 2.0},
    "BTC": {"type": "crypto", "ccxt": "BTC/USDT:USDT", "tf": "15m", "max_lev": 1.5},
    "NVDA": {"type": "stock", "yf": "NVDA", "tf": "1d", "max_lev": 3.0},
    "AMZN": {"type": "stock", "yf": "AMZN", "tf": "1d", "max_lev": 2.0},
}


class ConvictionTrader:
    def __init__(self):
        self.exchange = ccxt.binance({"options": {"defaultType": "future"}, "timeout": 10000})
        self.exchange.load_markets()
        self.states: dict[str, AssetState] = {}
        self._last_ts = {}

        # DL predictor (graceful: works without models)
        global _dl_predictor
        if DLPredictor is not None:
            try:
                _dl_predictor = DLPredictor(str(DATA_DIR))
                models = _dl_predictor.available_models()
                print(f"  [DL] Models loaded: {models if models else 'none yet'}")
            except Exception as e:
                print(f"  [DL] Init failed (will use rules only): {e}")
                _dl_predictor = None
        else:
            print("  [DL] dl_integration not available, rules only")

        for sym, cfg in ASSETS.items():
            sf = DATA_DIR / f"conviction_{sym.lower()}.json"
            if sf.exists():
                try:
                    data = json.loads(sf.read_text(encoding="utf-8"))
                    for k in ["trades", "activity_log", "evolution_log", "conviction_details"]:
                        locals()[f"_{k}"] = data.pop(k, [] if k != "conviction_details" else {})
                    s = AssetState(**{k: v for k, v in data.items() if k in AssetState.__dataclass_fields__})
                    s.trades = _trades; s.activity_log = _activity_log
                    s.evolution_log = _evolution_log; s.conviction_details = _conviction_details
                    self.states[sym] = s
                except Exception:
                    self.states[sym] = AssetState(symbol=sym, asset_type=cfg["type"], max_leverage=cfg["max_lev"])
            else:
                self.states[sym] = AssetState(symbol=sym, asset_type=cfg["type"], max_leverage=cfg["max_lev"])
            if not self.states[sym].started_at:
                self.states[sym].started_at = datetime.now(tz=timezone.utc).isoformat()
            self._last_ts[sym] = 0
            s = self.states[sym]
            print(f"  [{sym:4s}] ${s.balance:,.0f} | conv={s.conviction:.2f} | size={s.current_size:.2f}")

    def save(self, sym):
        sf = DATA_DIR / f"conviction_{sym.lower()}.json"
        sf.write_text(json.dumps(asdict(self.states[sym]), indent=2, default=str), encoding="utf-8")

    def _dedup(self, sym, sec):
        now = int(datetime.now(tz=timezone.utc).timestamp())
        bar = now // sec * sec
        if bar == self._last_ts.get(sym, 0): return False
        self._last_ts[sym] = bar; return True

    def _is_us_open(self):
        from zoneinfo import ZoneInfo
        now = datetime.now(tz=ZoneInfo("America/New_York"))
        if now.weekday() >= 5: return False
        return 9 <= now.hour < 16

    def _fetch_crypto(self, symbol, tf, limit=300):
        ohlcv = self.exchange.fetch_ohlcv(symbol, tf, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
        return df["close"].values, df["high"].values, df["low"].values, df["volume"].values

    def _fetch_stock(self, yf_sym):
        df = yf.Ticker(yf_sym).history(period="120d", interval="1d")
        if df is None or len(df) < 60: return None, None, None, None
        return df["Close"].values, df["High"].values, df["Low"].values, df["Volume"].values

    def cycle_asset(self, sym):
        now = datetime.now(tz=timezone.utc)
        cfg = ASSETS[sym]
        s = self.states[sym]

        # Timing
        if cfg["type"] == "crypto":
            if now.minute % 15 != 0 or not self._dedup(sym, 900): return
        else:
            # Stock: check market open FIRST, then dedup
            if not self._is_us_open(): return
            if not self._dedup(sym, 3600): return  # check hourly during market hours

        # Fetch data
        try:
            if cfg["type"] == "crypto":
                c, h, lo, v = self._fetch_crypto(cfg["ccxt"], cfg["tf"])
            else:
                c, h, lo, v = self._fetch_stock(cfg["yf"])
                if c is None: return
        except Exception as e:
            print(f"  [{sym}] Fetch: {e}"); return

        price = float(c[-1])
        s.current_price = price; s.last_update = now.isoformat(); s.total_checks += 1

        # Compute conviction (rules: max 0.60)
        conviction, details = compute_conviction(c, h, lo, v, cfg["max_lev"])

        # DL boost (up to +0.40)
        if _dl_predictor is not None:
            try:
                dl_boost = _dl_predictor.predict(sym, c, h, lo, v)
                conviction = max(0.0, min(1.0, conviction + dl_boost))
                details["dl_boost"] = round(dl_boost, 3)
            except Exception:
                details["dl_boost"] = 0.0
        else:
            details["dl_boost"] = 0.0

        s.conviction = conviction
        s.conviction_details = details
        target_size = conviction * cfg["max_lev"]

        # DD-based scaling
        dd = (s.peak_balance - s.balance) / s.peak_balance * 100 if s.peak_balance > 0 else 0
        if dd > 25: target_size *= 0.25
        elif dd > 15: target_size *= 0.50

        s.target_size = round(target_size, 3)

        # Current unrealized PnL
        if s.current_size > 0 and s.entry_price > 0:
            s.current_pnl_pct = (price / s.entry_price - 1) * s.current_size * 100
        else:
            s.current_pnl_pct = 0.0

        # Rebalance if conviction changed significantly
        size_diff = abs(target_size - s.current_size)
        if size_diff > REBALANCE_THRESHOLD or (target_size == 0 and s.current_size > 0):
            comm = 0.0005 if cfg["type"] == "crypto" else 0.001

            # Close existing position (realize PnL)
            if s.current_size > 0 and s.entry_price > 0:
                pnl = (price / s.entry_price - 1) * s.current_size - comm * s.current_size
                s.balance *= (1 + pnl)
                if s.balance < 0: s.balance = 0
                s.total_trades += 1
                if pnl > 0: s.wins += 1
                else: s.losses += 1
                if s.balance > s.peak_balance: s.peak_balance = s.balance
                dd_new = (s.peak_balance - s.balance) / s.peak_balance * 100
                if dd_new > s.max_drawdown_pct: s.max_drawdown_pct = dd_new
                direction = "UP" if target_size > s.current_size else "DOWN"
                s.trades.append({
                    "time": now.isoformat(), "entry": s.entry_price, "exit": price,
                    "old_size": round(s.current_size, 3), "new_size": round(target_size, 3),
                    "pnl_pct": round(pnl * 100, 2), "balance": round(s.balance, 2),
                    "conviction": round(conviction, 3), "reason": f"Rebalance {direction}",
                })
                print(f"  [{sym}] REBALANCE {s.current_size:.2f}->{target_size:.2f} | "
                      f"Conv={conviction:.2f} | PnL={pnl*100:+.1f}% | Bal=${s.balance:,.0f}")

            # Open new position at target size
            if target_size > 0:
                s.position = "LONG"
                s.entry_price = price
                s.current_size = target_size
            else:
                s.position = "FLAT"
                s.entry_price = 0
                s.current_size = 0
        elif s.current_size > 0:
            s.position = "LONG"

        # Activity log
        s.activity_log.append({
            "time": now.strftime("%m-%d %H:%M"), "price": round(price, 2),
            "conv": round(conviction, 3), "size": round(s.current_size, 3),
            "details": f"T={details.get('trend',0):.2f} R={details.get('rsi',0):.2f} V={details.get('volume',0):.2f} M={details.get('momentum',0):.2f}",
        })
        if len(s.activity_log) > 80: s.activity_log = s.activity_log[-80:]

        # Auto-evolve
        if s.total_trades - s.last_analysis_at >= 5:
            s.last_analysis_at = s.total_trades
            total_ret = (s.balance / INITIAL - 1) * 100
            wr = s.wins / max(s.total_trades, 1) * 100
            decision = "CONTINUE"
            if total_ret > 10 and s.total_trades >= 20: decision = "GOAL_APPROACHING"
            elif dd > 30: decision = "REDUCE_MAX_LEV"; s.max_leverage = max(s.max_leverage * 0.8, 0.5)
            s.evolution_log.append({"time": now.isoformat(), "decision": decision,
                                    "ret": round(total_ret, 2), "trades": s.total_trades, "wr": round(wr, 1)})
            if len(s.evolution_log) > 30: s.evolution_log = s.evolution_log[-30:]
            print(f"  [{sym}] EVOLVE: {decision} | Ret={total_ret:+.1f}% WR={wr:.0f}%")

        self.save(sym)

    def _health_check(self):
        """Self-diagnosis: detect and fix problems autonomously."""
        now = datetime.now(tz=timezone.utc)
        for sym, s in self.states.items():
            cfg = ASSETS[sym]

            # Problem 1: No checks at all after significant uptime
            if not s.last_update and s.started_at:
                started = datetime.fromisoformat(s.started_at)
                hours_up = (now - started).total_seconds() / 3600
                expected_checks = hours_up * 4 if cfg["type"] == "crypto" else max(0, hours_up - 14)  # stock: only during market
                if expected_checks > 5 and s.total_checks == 0:
                    print(f"  [{sym}] HEALTH: 0 checks after {hours_up:.0f}h. Resetting dedup.")
                    self._last_ts[sym] = 0  # reset dedup to allow next check
                    s.activity_log.append({"time": now.strftime("%m-%d %H:%M"), "price": 0,
                                           "conv": 0, "size": 0, "details": "HEALTH: reset dedup, 0 checks"})

            # Problem 2: Checks happening but last_update stale (stuck fetch)
            if s.last_update:
                last = datetime.fromisoformat(s.last_update)
                stale_hours = (now - last).total_seconds() / 3600
                expected_gap = 0.5 if cfg["type"] == "crypto" else 18  # crypto: 30min max, stock: overnight ok
                if stale_hours > expected_gap * 2:
                    print(f"  [{sym}] HEALTH: stale {stale_hours:.1f}h. Resetting dedup.")
                    self._last_ts[sym] = 0
                    s.activity_log.append({"time": now.strftime("%m-%d %H:%M"), "price": 0,
                                           "conv": 0, "size": 0, "details": f"HEALTH: reset, stale {stale_hours:.0f}h"})

            # Problem 3: Many checks but 0 trades (conviction never high enough)
            if s.total_checks >= 50 and s.total_trades == 0 and s.conviction == 0:
                # Something is wrong with data or conviction calc
                print(f"  [{sym}] HEALTH: {s.total_checks} checks, 0 conviction ever. Testing fetch...")
                try:
                    if cfg["type"] == "crypto":
                        c, h, lo, v = self._fetch_crypto(cfg["ccxt"], cfg["tf"], limit=10)
                        print(f"  [{sym}] HEALTH: fetch OK, price=${c[-1]:,.2f}, {len(c)} bars")
                    else:
                        c, h, lo, v = self._fetch_stock(cfg["yf"])
                        if c is not None:
                            print(f"  [{sym}] HEALTH: fetch OK, price=${c[-1]:,.2f}, {len(c)} bars")
                        else:
                            print(f"  [{sym}] HEALTH: fetch returned None!")
                except Exception as e:
                    print(f"  [{sym}] HEALTH: fetch FAILED: {e}")

            # Problem 4: Conviction > 0 but size = 0 (rebalance threshold too high?)
            if s.conviction > 0.1 and s.current_size == 0 and s.total_checks > 10:
                target = s.conviction * cfg["max_lev"]
                if target > REBALANCE_THRESHOLD:
                    print(f"  [{sym}] HEALTH: conv={s.conviction:.2f} but size=0. Forcing rebalance next cycle.")
                    self._last_ts[sym] = 0  # allow next cycle to rebalance

    def cycle_all(self):
        now = datetime.now(tz=timezone.utc)
        if now.minute % 15 != 0: return
        for sym in ASSETS:
            try: self.cycle_asset(sym)
            except Exception as e: print(f"  [{sym} err] {e}")
        # Health check every hour
        if now.minute == 0 and now.hour % 1 == 0:
            try: self._health_check()
            except Exception as e: print(f"  [HEALTH err] {e}")


_trader: ConvictionTrader | None = None

DASH_HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><title>Conviction Engine</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e0e0;font-family:'Segoe UI',system-ui,monospace}
.hdr{background:#141926;padding:12px 24px;border-bottom:1px solid #2a3040;display:flex;justify-content:space-between}
.hdr h1{font-size:15px;color:#ff9800}
.wrap{padding:14px 24px;max-width:1100px;margin:0 auto}
.gn{color:#00d4aa}.rd{color:#ff4d6a}.yl{color:#ffd700}.bl{color:#4dabf7}.gy{color:#555}
.summary{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:14px}
.sum-card{background:#0a0e17;border:1px solid #2a3040;border-radius:6px;padding:12px;text-align:center}
.sum-card .label{font-size:9px;color:#555;margin-bottom:4px}
.sum-card .value{font-size:22px;font-weight:bold}
.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:14px}
.card{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:14px}
.card h3{font-size:12px;margin-bottom:6px;display:flex;justify-content:space-between}
.row{display:flex;justify-content:space-between;font-size:11px;padding:2px 0;border-bottom:1px solid #1a2030}
.row .k{color:#555}.row .v{font-weight:bold}
.conv-bar{height:8px;background:#1a2030;border-radius:4px;overflow:hidden;margin:4px 0}
.conv-fill{height:100%;border-radius:4px;transition:width 1s}
.section{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:14px;margin-bottom:14px}
.section h2{font-size:10px;color:#555;margin-bottom:8px;text-transform:uppercase}
table{width:100%;border-collapse:collapse;font-size:10px}
th{text-align:left;color:#555;padding:4px 6px;border-bottom:1px solid #2a3040}
td{padding:4px 6px;border-bottom:1px solid #1a2030}
.signal-row{display:flex;gap:4px;margin:2px 0}
.signal-chip{padding:1px 5px;border-radius:3px;font-size:9px}
</style></head><body>
<div class="hdr"><h1>Conviction Engine - No Limits</h1><div id="clock" style="font-size:10px;color:#555"></div></div>
<div class="wrap">
  <div class="summary" id="summary"></div>
  <div class="cards" id="cards"></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
    <div class="section"><h2>Rebalance History</h2>
      <table><thead><tr><th>Asset</th><th>Time</th><th>Position</th><th>Conv</th><th>PnL%</th><th>Bal</th></tr></thead>
      <tbody id="trades"></tbody></table></div>
    <div class="section"><h2>Signal Details</h2><div id="signals" style="max-height:300px;overflow-y:auto"></div></div>
  </div>
</div>
<script>
const INIT=10000;
function fmt(v){return v>=0?'+'+v.toFixed(2):v.toFixed(2)}
function convColor(v){return v>0.5?'#00d4aa':v>0.3?'#ffd700':v>0.1?'#ff9800':'#555'}
async function refresh(){
  document.getElementById('clock').textContent=new Date().toLocaleString('ko-KR');
  try{
    const r=await fetch('/api/status?'+Date.now());if(!r.ok)return;
    const d=await r.json();
    let totalBal=0,totalTrades=0,totalWins=0,allT=[],n=0;
    let ch='';
    for(const[sym,a]of Object.entries(d)){
      n++;totalBal+=a.balance;totalTrades+=a.total_trades;totalWins+=a.wins;
      const ret=((a.balance/INIT-1)*100);
      const conv=a.conviction||0;const size=a.current_size||0;
      const pnl=a.current_pnl_pct||0;
      const det=a.conviction_details||{};
      const cc=convColor(conv);
      ch+=`<div class="card">
        <h3>${sym} <span style="color:${cc};font-size:11px">${(conv*100).toFixed(0)}% conviction</span></h3>
        <div class="conv-bar"><div class="conv-fill" style="width:${conv*100}%;background:${cc}"></div></div>
        <div class="row"><span class="k">Price</span><span class="v bl">$${parseFloat(a.current_price||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}</span></div>
        <div class="row"><span class="k">Balance</span><span class="v ${a.balance>=INIT?'gn':'rd'}">$${Math.round(a.balance).toLocaleString()}</span></div>
        <div class="row"><span class="k">Return</span><span class="v ${ret>=0?'gn':'rd'}">${fmt(ret)}%</span></div>
        <div class="row"><span class="k">Position</span><span class="v yl">${size>=1?size.toFixed(1)+'x lev':(size*100).toFixed(0)+'% invested'}</span></div>
        <div class="row"><span class="k">Unreal PnL</span><span class="v ${pnl>=0?'gn':'rd'}">${fmt(pnl)}%</span></div>
        <div class="row"><span class="k">Trades</span><span class="v">${a.total_trades}</span></div>
        <div class="row"><span class="k">Running</span><span class="v gy">${(()=>{if(!a.started_at)return'--';const ms=Date.now()-new Date(a.started_at).getTime();const d=Math.floor(ms/86400000);const h=Math.floor((ms%86400000)/3600000);const m=Math.floor((ms%3600000)/60000);return d>0?d+'d '+h+'h':h+'h '+m+'m'})()}</span></div>
        <div class="signal-row">
          <span class="signal-chip" style="background:${(det.trend||0)>0?'#00d4aa33':'#ff4d6a22'};color:${(det.trend||0)>0?'#00d4aa':'#ff4d6a'}">T${fmt(det.trend||0)}</span>
          <span class="signal-chip" style="background:${(det.rsi||0)>0?'#00d4aa33':'#ff4d6a22'};color:${(det.rsi||0)>0?'#00d4aa':'#ff4d6a'}">R${fmt(det.rsi||0)}</span>
          <span class="signal-chip" style="background:${(det.volume||0)>0?'#00d4aa33':'#55555533'};color:${(det.volume||0)>0?'#00d4aa':'#888'}">V${fmt(det.volume||0)}</span>
          <span class="signal-chip" style="background:${(det.momentum||0)>0?'#00d4aa33':'#ff4d6a22'};color:${(det.momentum||0)>0?'#00d4aa':'#ff4d6a'}">M${fmt(det.momentum||0)}</span>
        </div>
      </div>`;
      for(const t of(a.trades||[]).slice(-10)){t._s=sym;allT.push(t)}
    }
    document.getElementById('cards').innerHTML=ch;
    const totalInit=n*INIT;const totalRet=((totalBal/totalInit-1)*100);
    const wr=totalTrades>0?(totalWins/totalTrades*100).toFixed(0)+'%':'--';
    document.getElementById('summary').innerHTML=`
      <div class="sum-card"><div class="label">Portfolio</div><div class="value ${totalBal>=totalInit?'gn':'rd'}">$${Math.round(totalBal).toLocaleString()}</div></div>
      <div class="sum-card"><div class="label">Return</div><div class="value ${totalRet>=0?'gn':'rd'}">${fmt(totalRet)}%</div></div>
      <div class="sum-card"><div class="label">Trades / WR</div><div class="value">${totalTrades} / ${wr}</div></div>
      <div class="sum-card"><div class="label">Elapsed</div><div class="value bl" id="elapsed">--</div></div>`;
    // Compute elapsed from earliest started_at
    let earliest=null;
    for(const a of Object.values(d)){
      if(a.started_at){const t=new Date(a.started_at);if(!earliest||t<earliest)earliest=t;}}
    if(earliest){
      const ms=Date.now()-earliest.getTime();
      const days=Math.floor(ms/86400000);const hrs=Math.floor((ms%86400000)/3600000);const mins=Math.floor((ms%3600000)/60000);
      document.getElementById('elapsed').textContent=days>0?days+'d '+hrs+'h':hrs+'h '+mins+'m';
    }
    allT.sort((a,b)=>(b.time||'').localeCompare(a.time||''));
    let th='';for(const t of allT.slice(0,20)){const p=t.pnl_pct||0;
      th+=`<tr><td class="yl">${t._s}</td><td>${(t.time||'').slice(5,16)}</td>
        <td>${((t.old_size||0)>=1?(t.old_size).toFixed(1)+'x':((t.old_size)*100).toFixed(0)+'%')}->${((t.new_size||0)>=1?(t.new_size).toFixed(1)+'x':((t.new_size)*100).toFixed(0)+'%')}</td>
        <td>${(t.conviction||0).toFixed(2)}</td>
        <td class="${p>=0?'gn':'rd'}">${fmt(p)}%</td>
        <td>$${Math.round(t.balance||0).toLocaleString()}</td></tr>`;}
    if(!th)th='<tr><td colspan="6" class="gy" style="text-align:center;padding:16px">Conviction building...</td></tr>';
    document.getElementById('trades').innerHTML=th;
    let sh='';for(const[sym,a]of Object.entries(d)){
      const logs=(a.activity_log||[]).slice(-5).reverse();
      for(const l of logs){
        sh+=`<div style="display:flex;gap:6px;padding:2px 0;border-bottom:1px solid #1a2030;font-size:9px">
          <span class="yl" style="min-width:35px">${sym}</span>
          <span class="gy" style="min-width:75px">${l.time||''}</span>
          <span style="min-width:60px">$${l.price||0}</span>
          <span style="min-width:40px;color:${convColor(l.conv||0)}">${((l.conv||0)*100).toFixed(0)}%</span>
          <span class="gy">${l.details||''}</span>
        </div>`;}}
    if(!sh)sh='<div class="gy" style="padding:16px;text-align:center">Waiting for first check...</div>';
    document.getElementById('signals').innerHTML=sh;
  }catch(e){console.error(e)}
}
refresh();setInterval(refresh,5000);
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/status"):
            data = {s: asdict(st) for s, st in _trader.states.items()} if _trader else {}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, default=str).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASH_HTML.encode())
    def log_message(self, *a): pass


def main():
    global _trader
    print("=" * 60)
    print("  Conviction Engine - No Binary Limits")
    print("  Continuous positioning based on signal strength")
    print("  ETH | BTC | NVDA | AMZN")
    print(f"  Dashboard: http://localhost:{DASH_PORT}")
    print("=" * 60)
    _trader = ConvictionTrader()
    server = http.server.HTTPServer(("0.0.0.0", DASH_PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"\n  Dashboard: http://localhost:{DASH_PORT}")
    print("  Running...\n")
    try:
        while True:
            try: _trader.cycle_all()
            except KeyboardInterrupt: raise
            except Exception as e: print(f"  [err] {e}")
            time.sleep(CYCLE_SEC)
    except KeyboardInterrupt:
        print("\n  Saving..."); [_trader.save(s) for s in _trader.states]


if __name__ == "__main__":
    main()
