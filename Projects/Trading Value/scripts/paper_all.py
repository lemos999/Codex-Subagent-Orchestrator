"""Unified Paper Trading - All Assets, One Dashboard.

ETH:  CMA-ES + XGBoost hybrid (15m, crypto)
BTC:  4H MA200 + RSI pullback (4h, crypto)
NVDA: Regime MA30/50 leveraged (daily, stock)
AMZN: Regime MA30/50 leveraged (daily, stock)

All with auto-evolution engine.
Dashboard: http://localhost:8895

Usage:
    cd "Projects/Trading Value"
    py -3.12 scripts/paper_all.py
"""
from __future__ import annotations
import json, sys, threading, time, http.server
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd

try:
    import ccxt
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, "-m", "pip", "install", "ccxt"]); import ccxt
try:
    import yfinance as yf
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"]); import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from strategy_deploy import HybridStrategy, DEFAULT_MODEL_PATH

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DASH_PORT = 8895
INITIAL = 10_000.0
CYCLE_SEC = 60


@dataclass
class AssetState:
    symbol: str = ""
    asset_type: str = ""
    strategy_name: str = ""
    balance: float = INITIAL
    position: str = "FLAT"
    entry_price: float = 0.0
    stop_price: float = 0.0
    tp_price: float = 0.0
    current_leverage: float = 0.0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    peak_balance: float = INITIAL
    max_drawdown_pct: float = 0.0
    current_price: float = 0.0
    current_pnl_pct: float = 0.0
    regime: str = ""
    last_update: str = ""
    started_at: str = ""
    total_checks: int = 0
    last_analysis_at: int = 0
    leverage: float = 1.6
    confidence_threshold: float = 0.55
    paused: bool = False
    evolution_log: list = field(default_factory=list)
    trades: list = field(default_factory=list)
    activity_log: list = field(default_factory=list)


def sma(arr, w):
    n = len(arr); out = np.full(n, np.nan)
    cs = np.cumsum(arr); cs = np.insert(cs, 0, 0)
    if n >= w: out[w-1:] = (cs[w:] - cs[:-w]) / w
    return out


class UnifiedTrader:
    def __init__(self):
        self.exchange = ccxt.binance({"options": {"defaultType": "future"}, "timeout": 10000})
        self.exchange.load_markets()
        self.states: dict[str, AssetState] = {}
        self._last_ts = {}  # per-asset dedup
        self._eth_strategy = None

        # Load XGBoost for ETH
        if Path(DEFAULT_MODEL_PATH).exists():
            self._eth_strategy = HybridStrategy(model_path=DEFAULT_MODEL_PATH)
            print("  [ETH] XGBoost model loaded")

        # Init states
        for sym, cfg in [
            ("ETH", {"type": "crypto", "strategy": "CMA-ES+XGB", "leverage": 1.6}),
            ("BTC", {"type": "crypto", "strategy": "4H MA200+RSI", "leverage": 1.5}),
            ("NVDA", {"type": "stock", "strategy": "Regime 3x", "leverage": 3.0}),
            ("AMZN", {"type": "stock", "strategy": "Regime 2x", "leverage": 2.0}),
        ]:
            sf = DATA_DIR / f"paper_unified_{sym.lower()}.json"
            if sf.exists():
                try:
                    data = json.loads(sf.read_text(encoding="utf-8"))
                    for k in ["trades", "activity_log", "evolution_log"]:
                        data.pop(k, None)
                    s = AssetState(**{k: v for k, v in data.items() if k in AssetState.__dataclass_fields__})
                    s.trades = json.loads(sf.read_text(encoding="utf-8")).get("trades", [])
                    s.activity_log = json.loads(sf.read_text(encoding="utf-8")).get("activity_log", [])
                    s.evolution_log = json.loads(sf.read_text(encoding="utf-8")).get("evolution_log", [])
                    self.states[sym] = s
                except Exception:
                    self.states[sym] = AssetState(symbol=sym, asset_type=cfg["type"],
                                                  strategy_name=cfg["strategy"], leverage=cfg["leverage"])
            else:
                self.states[sym] = AssetState(symbol=sym, asset_type=cfg["type"],
                                              strategy_name=cfg["strategy"], leverage=cfg["leverage"])
            if not self.states[sym].started_at:
                self.states[sym].started_at = datetime.now(tz=timezone.utc).isoformat()
            self._last_ts[sym] = 0
            s = self.states[sym]
            wr = s.wins / max(s.total_trades, 1) * 100
            print(f"  [{sym:4s}] {cfg['strategy']:15s} | ${s.balance:,.0f} | {s.position} | {s.total_trades} trades")

    def save(self, sym):
        sf = DATA_DIR / f"paper_unified_{sym.lower()}.json"
        sf.write_text(json.dumps(asdict(self.states[sym]), indent=2, default=str), encoding="utf-8")

    def _dedup(self, sym, interval_sec):
        now = int(datetime.now(tz=timezone.utc).timestamp())
        bar = now // interval_sec * interval_sec
        if bar == self._last_ts.get(sym, 0): return False
        self._last_ts[sym] = bar
        return True

    def _is_us_market_open(self):
        from zoneinfo import ZoneInfo
        now = datetime.now(tz=ZoneInfo("America/New_York"))
        if now.weekday() >= 5: return False
        return 9 <= now.hour < 16

    def _close_pos(self, s, price, reason, comm):
        if s.position == "FLAT": return
        pnl = (price / s.entry_price - 1) * s.current_leverage
        dd = (s.peak_balance - s.balance) / s.peak_balance * 100 if s.peak_balance > 0 else 0
        sz = 0.25 if dd > 25 else (0.5 if dd > 15 else 1.0)
        pnl = pnl * sz - comm * s.current_leverage * sz
        s.balance *= (1 + pnl)
        if s.balance < 0: s.balance = 0
        s.total_trades += 1
        if pnl > 0: s.wins += 1
        else: s.losses += 1
        if s.balance > s.peak_balance: s.peak_balance = s.balance
        dd_new = (s.peak_balance - s.balance) / s.peak_balance * 100
        if dd_new > s.max_drawdown_pct: s.max_drawdown_pct = dd_new
        s.trades.append({"time": datetime.now(tz=timezone.utc).isoformat(), "entry": s.entry_price,
                         "exit": price, "pnl_pct": round(pnl * 100, 2), "balance": round(s.balance, 2), "reason": reason})
        s.position = "FLAT"; s.entry_price = 0; s.stop_price = 0; s.tp_price = 0; s.current_pnl_pct = 0
        print(f"  [{s.symbol}] EXIT ${price:,.2f} | {reason} | PnL={pnl*100:+.1f}% | Bal=${s.balance:,.0f}")

    def _log_activity(self, s, price, action):
        s.activity_log.append({"time": datetime.now(tz=timezone.utc).strftime("%m-%d %H:%M"),
                               "price": round(float(price), 2), "action": action, "regime": s.regime})
        if len(s.activity_log) > 80: s.activity_log = s.activity_log[-80:]

    def _auto_evolve(self, s):
        if s.total_trades - s.last_analysis_at < 5: return
        s.last_analysis_at = s.total_trades
        rets = [t.get("pnl_pct", 0) for t in s.trades]
        total_ret = (s.balance / INITIAL - 1) * 100
        wr = s.wins / max(s.total_trades, 1) * 100
        recent = [t.get("pnl_pct", 0) for t in s.trades[-10:]]
        recent_wr = sum(1 for r in recent if r > 0) / max(len(recent), 1) * 100
        dd = s.max_drawdown_pct
        decision = "CONTINUE"; adj = []
        if total_ret > 10 and s.total_trades >= 20 and wr >= 50:
            decision = "GOAL_APPROACHING"; adj.append("Target zone!")
        max_lev = 2.5 if s.asset_type == "crypto" else 3.0
        if dd > 30:
            s.paused = True; decision = "PAUSE"; adj.append(f"DD {dd:.1f}%")
        elif recent_wr < 35 and len(recent) >= 5:
            old = s.leverage; s.leverage = max(old - 0.3, 1.0)
            if s.leverage != old: adj.append(f"Lev {old:.1f}->{s.leverage:.1f}")
            decision = "ADJUSTED"
        elif total_ret > 5 and wr >= 55 and dd < 20:
            old = s.leverage; s.leverage = min(old + 0.2, max_lev)
            if s.leverage != old: adj.append(f"Lev {old:.1f}->{s.leverage:.1f}")
            decision = "ADJUSTED"
        if not adj: adj.append("No changes")
        s.evolution_log.append({"time": datetime.now(tz=timezone.utc).isoformat(), "decision": decision,
                                "adjustments": adj, "ret": round(total_ret, 2), "trades": s.total_trades})
        if len(s.evolution_log) > 30: s.evolution_log = s.evolution_log[-30:]
        print(f"  [{s.symbol}] EVOLVE: {decision} | Ret={total_ret:+.1f}% | {'; '.join(adj)}")

    # ── ETH: CMA-ES + XGBoost ──────────────────────────────────────────
    def cycle_eth(self):
        now = datetime.now(tz=timezone.utc)
        if now.minute % 15 != 0 or not self._dedup("ETH", 900): return
        s = self.states["ETH"]
        if s.paused: return
        try:
            df = pd.DataFrame(self.exchange.fetch_ohlcv("ETH/USDT:USDT", "15m", limit=250),
                              columns=["ts", "open", "high", "low", "close", "volume"])
            df["datetime"] = pd.to_datetime(df["ts"], unit="ms"); df.set_index("datetime", inplace=True)
            df.drop(columns=["ts"], inplace=True)
        except Exception as e:
            print(f"  [ETH] Fetch: {e}"); return
        price = float(df["close"].iloc[-1])
        s.current_price = price; s.last_update = now.isoformat(); s.total_checks += 1
        if s.position == "LONG" and s.entry_price > 0:
            s.current_pnl_pct = (price / s.entry_price - 1) * 100
        else: s.current_pnl_pct = 0
        if self._eth_strategy:
            sig = self._eth_strategy.update(df)
            s.regime = sig["signal"]
            conf = float(sig.get("confidence", 0))
            if s.position != "FLAT" and sig["signal"] == "FLAT":
                self._close_pos(s, price, sig.get("reason", "Signal FLAT"), 0.0005)
            elif s.position == "FLAT" and sig["signal"] == "LONG" and sig.get("stop_loss", 0) > 0:
                s.position = "LONG"; s.entry_price = price; s.current_leverage = s.leverage
                s.stop_price = sig["stop_loss"]; s.tp_price = sig["take_profit"]
                self._eth_strategy._position = "LONG"; self._eth_strategy._entry_price = price
                self._eth_strategy._stop_price = sig["stop_loss"]; self._eth_strategy._tp_price = sig["take_profit"]
                print(f"  [ETH] ENTER ${price:,.2f} | Conf={conf:.3f}")
            action = sig["signal"]
        else:
            action = "NO_MODEL"; s.regime = "NO_MODEL"
        self._log_activity(s, price, action)
        self._auto_evolve(s); self.save("ETH")

    # ── BTC: 4H MA200 + RSI ────────────────────────────────────────────
    def cycle_btc(self):
        now = datetime.now(tz=timezone.utc)
        if now.minute % 15 != 0 or not self._dedup("BTC", 900): return
        s = self.states["BTC"]
        if s.paused: return
        try:
            df = pd.DataFrame(self.exchange.fetch_ohlcv("BTC/USDT:USDT", "4h", limit=250),
                              columns=["ts", "open", "high", "low", "close", "volume"])
        except Exception as e:
            print(f"  [BTC] Fetch: {e}"); return
        c = df["close"].values; h = df["high"].values; lo = df["low"].values; n = len(c)
        price = float(c[-1]); s.current_price = price; s.last_update = now.isoformat(); s.total_checks += 1
        ma200 = sma(c, 200); delta = np.diff(c, prepend=c[0])
        gain = np.where(delta > 0, delta, 0.0); loss = np.where(delta < 0, -delta, 0.0)
        rsi = np.full(n, 50.0); avg_g = sma(gain, 14); avg_l = sma(loss, 14)
        v = avg_l > 0; rsi[v] = 100 - 100 / (1 + avg_g[v] / avg_l[v])
        tr = np.insert(np.maximum(h[1:]-lo[1:], np.maximum(np.abs(h[1:]-c[:-1]), np.abs(lo[1:]-c[:-1]))), 0, h[0]-lo[0])
        atr = sma(tr, 14); i = n - 1
        if np.isnan(ma200[i]) or np.isnan(atr[i]) or atr[i] <= 0: return
        uptrend = c[i] > ma200[i]; s.regime = "BULL" if uptrend else "BEAR"
        if s.position == "LONG" and s.entry_price > 0:
            s.current_pnl_pct = (price / s.entry_price - 1) * s.current_leverage * 100
        else: s.current_pnl_pct = 0
        if s.position == "LONG":
            new_trail = price - 2.0 * atr[i]; s.stop_price = max(s.stop_price, new_trail)
            if price <= s.stop_price or price >= s.tp_price or not uptrend:
                reason = "Stop" if price <= s.stop_price else ("TP" if price >= s.tp_price else "Bear")
                self._close_pos(s, price, reason, 0.0005)
        if s.position == "FLAT" and uptrend and rsi[i] < 30:
            s.position = "LONG"; s.entry_price = price; s.current_leverage = s.leverage
            s.stop_price = price - 2.0 * atr[i]; s.tp_price = price + 5.0 * atr[i]
            print(f"  [BTC] ENTER ${price:,.0f} | RSI={rsi[i]:.1f}")
        self._log_activity(s, price, s.position); self._auto_evolve(s); self.save("BTC")

    # ── NVDA/AMZN: Daily Regime ─────────────────────────────────────────
    def cycle_stock(self, sym, yf_sym, ma_f_period=30, ma_s_period=50, lev_bull=3.0, lev_mild=0.5, stop_pct=0.05):
        now = datetime.now(tz=timezone.utc)
        today = now.strftime("%Y-%m-%d")
        if not self._dedup(sym, 86400): return  # once per day
        if not self._is_us_market_open(): return
        s = self.states[sym]
        if s.paused: return
        try:
            df = yf.Ticker(yf_sym).history(period="120d", interval="1d")
            if df is None or len(df) < 60: return
        except Exception as e:
            print(f"  [{sym}] Fetch: {e}"); return
        c = df["Close"].values; price = float(c[-1])
        s.current_price = price; s.last_update = now.isoformat(); s.total_checks += 1
        ma_f = c[-ma_f_period:].mean() if len(c) >= ma_f_period else np.nan
        ma_s = c[-ma_s_period:].mean() if len(c) >= ma_s_period else np.nan
        if np.isnan(ma_f) or np.isnan(ma_s): return
        bull = ma_f > ma_s and price > ma_f; mild = ma_f > ma_s and price <= ma_f; bear = ma_f <= ma_s
        s.regime = "BULL" if bull else ("MILD" if mild else "BEAR")
        if s.position == "LONG" and s.entry_price > 0:
            s.current_pnl_pct = (price / s.entry_price - 1) * s.current_leverage * 100
        else: s.current_pnl_pct = 0
        if s.position == "LONG":
            new_stop = price * (1 - stop_pct); s.stop_price = max(s.stop_price, new_stop)
            if bear or price <= s.stop_price:
                self._close_pos(s, price, "Bear" if bear else "Stop", 0.001)
        if s.position == "FLAT":
            if bull:
                s.position = "LONG"; s.entry_price = price; s.current_leverage = lev_bull
                s.stop_price = price * (1 - stop_pct)
                print(f"  [{sym}] ENTER BULL ${price:,.2f} | {lev_bull}x")
            elif mild:
                s.position = "LONG"; s.entry_price = price; s.current_leverage = lev_mild
                s.stop_price = price * (1 - stop_pct)
        self._log_activity(s, price, f"{s.position} ({s.regime})")
        self._auto_evolve(s); self.save(sym)

    def _stagnation_check(self, s):
        """If no trades after 100 checks, log why and relax ETH threshold."""
        if s.total_checks > 0 and s.total_checks % 100 == 0 and s.total_trades == 0:
            if s.symbol == "ETH" and self._eth_strategy:
                old = self._eth_strategy.params.get("confidence_threshold", 0.55)
                new = max(old - 0.02, 0.50)
                self._eth_strategy.params["confidence_threshold"] = new
                s.confidence_threshold = new
                msg = f"Stagnation: {s.total_checks} checks, 0 trades. Conf {old:.2f}->{new:.2f}"
                s.evolution_log.append({"time": datetime.now(tz=timezone.utc).isoformat(),
                                        "decision": "STAGNATION", "adjustments": [msg],
                                        "ret": 0, "trades": 0})
                print(f"  [{s.symbol}] {msg}")

    def cycle_all(self):
        now = datetime.now(tz=timezone.utc)
        if now.minute % 15 != 0: return
        try: self.cycle_eth()
        except Exception as e: print(f"  [ETH err] {e}")
        try: self.cycle_btc()
        except Exception as e: print(f"  [BTC err] {e}")
        try: self.cycle_stock("NVDA", "NVDA", 30, 50, 3.0, 0.5, 0.05)
        except Exception as e: print(f"  [NVDA err] {e}")
        try: self.cycle_stock("AMZN", "AMZN", 30, 50, 2.0, 0.5, 0.05)
        except Exception as e: print(f"  [AMZN err] {e}")
        # Stagnation checks
        for s in self.states.values():
            self._stagnation_check(s)


_trader: UnifiedTrader | None = None

DASH_HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><title>Trading Value - All Assets</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e0e0;font-family:'Segoe UI',system-ui,monospace}
.hdr{background:#141926;padding:12px 24px;border-bottom:1px solid #2a3040;display:flex;justify-content:space-between;align-items:center}
.hdr h1{font-size:15px;color:#ff9800;letter-spacing:1px}
.hdr .ts{font-size:10px;color:#555}
.wrap{padding:14px 24px;max-width:1100px;margin:0 auto}
.gn{color:#00d4aa}.rd{color:#ff4d6a}.yl{color:#ffd700}.bl{color:#4dabf7}.gy{color:#555}
.summary{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}
.sum-card{background:#0a0e17;border:1px solid #2a3040;border-radius:6px;padding:12px;text-align:center}
.sum-card .label{font-size:9px;color:#555;margin-bottom:4px}
.sum-card .value{font-size:22px;font-weight:bold}
.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:14px}
.card{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:14px}
.card h3{font-size:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center}
.card .tag{font-size:8px;padding:2px 6px;border-radius:3px;background:#2a3040}
.tag-crypto{color:#ffd700}.tag-stock{color:#4dabf7}
.row{display:flex;justify-content:space-between;font-size:11px;padding:2px 0;border-bottom:1px solid #1a2030}
.row .k{color:#555}.row .v{font-weight:bold}
.regime{padding:2px 6px;border-radius:3px;font-size:9px;font-weight:bold}
.regime-BULL{background:#00d4aa22;color:#00d4aa}
.regime-MILD{background:#ffd70022;color:#ffd700}
.regime-BEAR{background:#ff4d6a22;color:#ff4d6a}
.regime-FLAT{background:#55555522;color:#888}
.section{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:14px;margin-bottom:14px}
.section h2{font-size:10px;color:#555;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px}
table{width:100%;border-collapse:collapse;font-size:10px}
th{text-align:left;color:#555;padding:4px 6px;border-bottom:1px solid #2a3040;font-size:9px}
td{padding:4px 6px;border-bottom:1px solid #1a2030}
.log-entry{display:flex;gap:6px;padding:3px 0;border-bottom:1px solid #1a2030;font-size:10px}
.evo-card{background:#0a0e17;border:1px solid #2a3040;border-radius:6px;padding:8px;margin-bottom:6px;font-size:10px}
</style></head><body>
<div class="hdr"><h1>Trading Value - Unified Dashboard</h1><div class="ts" id="clock"></div></div>
<div class="wrap">
  <div class="summary" id="summary"></div>
  <div class="cards" id="cards"></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
    <div class="section"><h2>All Trades</h2>
      <table><thead><tr><th>Asset</th><th>Time</th><th>Entry</th><th>Exit</th><th>PnL%</th><th>Bal</th><th>Reason</th></tr></thead>
      <tbody id="trades"></tbody></table></div>
    <div class="section"><h2>Evolution Log</h2><div id="evo" style="max-height:300px;overflow-y:auto"></div></div>
  </div>
</div>
<script>
const INIT=10000;
function fmt(v){return v>=0?'+'+v.toFixed(2):v.toFixed(2)}
async function refresh(){
  document.getElementById('clock').textContent=new Date().toLocaleString('ko-KR');
  try{
    const r=await fetch('/api/status?'+Date.now());if(!r.ok)return;
    const d=await r.json();
    let totalBal=0,totalTrades=0,totalWins=0,allT=[],allEvo=[];
    let ch='';
    for(const[sym,a]of Object.entries(d)){
      totalBal+=a.balance;totalTrades+=a.total_trades;totalWins+=a.wins;
      const ret=((a.balance/INIT-1)*100);
      const wr=a.total_trades>0?(a.wins/a.total_trades*100).toFixed(0)+'%':'--';
      const pnl=a.current_pnl_pct||0;
      const tagCls=a.asset_type==='crypto'?'tag-crypto':'tag-stock';
      const posHtml=a.position!=='FLAT'
        ?`<span class="gn">${a.position} ${a.current_leverage||''}x</span> <span class="${pnl>=0?'gn':'rd'}">(${fmt(pnl)}%)</span>`
        :'<span class="gy">FLAT</span>';
      ch+=`<div class="card">
        <h3>${sym} <span><span class="tag ${tagCls}">${a.asset_type}</span> <span class="regime regime-${a.regime||'FLAT'}">${a.regime||'--'}</span></span></h3>
        <div class="row"><span class="k">Strategy</span><span class="v" style="font-size:9px;color:#888">${a.strategy_name||'--'}</span></div>
        <div class="row"><span class="k">Price</span><span class="v bl">$${parseFloat(a.current_price||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}</span></div>
        <div class="row"><span class="k">Balance</span><span class="v ${a.balance>=INIT?'gn':'rd'}">$${Math.round(a.balance).toLocaleString()}</span></div>
        <div class="row"><span class="k">Return</span><span class="v ${ret>=0?'gn':'rd'}">${fmt(ret)}%</span></div>
        <div class="row"><span class="k">Position</span><span class="v">${posHtml}</span></div>
        <div class="row"><span class="k">Trades</span><span class="v">${a.total_trades} (${wr})</span></div>
        <div class="row"><span class="k">Leverage</span><span class="v yl">${(a.leverage||0).toFixed(1)}x</span></div>
        <div class="row"><span class="k">Max DD</span><span class="v rd">${a.max_drawdown_pct>0?'-'+a.max_drawdown_pct.toFixed(1)+'%':'0%'}</span></div>
        <div class="row"><span class="k">Checks</span><span class="v gy">${a.total_checks||0}</span></div>
      </div>`;
      for(const t of(a.trades||[]).slice(-10)){t._s=sym;allT.push(t)}
      for(const e of(a.evolution_log||[]).slice(-5)){e._s=sym;allEvo.push(e)}
    }
    document.getElementById('cards').innerHTML=ch;
    const totalInit=Object.keys(d).length*INIT;
    const totalRet=((totalBal/totalInit-1)*100);
    const totalWR=totalTrades>0?(totalWins/totalTrades*100).toFixed(0)+'%':'--';
    const started=Object.values(d)[0]?.started_at||'';
    let uptime='--';
    if(started){const ms=Date.now()-new Date(started).getTime();const h=Math.floor(ms/3600000);const m=Math.floor((ms%3600000)/60000);uptime=`${h}h ${m}m`;}
    document.getElementById('summary').innerHTML=`
      <div class="sum-card"><div class="label">Portfolio</div><div class="value ${totalBal>=totalInit?'gn':'rd'}">$${Math.round(totalBal).toLocaleString()}</div></div>
      <div class="sum-card"><div class="label">Total Return</div><div class="value ${totalRet>=0?'gn':'rd'}">${fmt(totalRet)}%</div></div>
      <div class="sum-card"><div class="label">Trades / WR</div><div class="value">${totalTrades} / ${totalWR}</div></div>
      <div class="sum-card"><div class="label">Uptime</div><div class="value bl">${uptime}</div></div>`;
    allT.sort((a,b)=>(b.time||'').localeCompare(a.time||''));
    let th='';for(const t of allT.slice(0,20)){const p=t.pnl_pct||0;
      th+=`<tr><td class="yl">${t._s}</td><td>${(t.time||'').slice(5,16)}</td>
        <td>$${parseFloat(t.entry||0).toFixed(2)}</td><td>$${parseFloat(t.exit||0).toFixed(2)}</td>
        <td class="${p>=0?'gn':'rd'}">${fmt(p)}%</td><td>$${Math.round(t.balance||0).toLocaleString()}</td>
        <td class="gy">${(t.reason||'').slice(0,25)}</td></tr>`;}
    if(!th)th='<tr><td colspan="7" class="gy" style="text-align:center;padding:16px">Waiting for first trade...</td></tr>';
    document.getElementById('trades').innerHTML=th;
    allEvo.sort((a,b)=>(b.time||'').localeCompare(a.time||''));
    let eh='';for(const e of allEvo.slice(0,10)){
      const cls=e.decision==='GOAL_APPROACHING'?'gn':e.decision==='PAUSE'?'rd':e.decision==='ADJUSTED'?'yl':'gy';
      eh+=`<div class="evo-card"><span class="${cls}" style="font-weight:bold">${e._s} ${e.decision}</span>
        <span class="gy"> | ${(e.time||'').slice(5,16)} | ${e.trades||0} trades | Ret ${fmt(e.ret||0)}%</span>
        <div style="color:#666;margin-top:2px">${(e.adjustments||[]).join('; ')}</div></div>`;}
    if(!eh)eh='<div class="gy" style="text-align:center;padding:16px">Evolution engine activates after 5 trades per asset</div>';
    document.getElementById('evo').innerHTML=eh;
  }catch(e){console.error(e)}
}
refresh();setInterval(refresh,5000);
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/status"):
            data = {sym: asdict(s) for sym, s in _trader.states.items()} if _trader else {}
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
    print("  Trading Value - Unified Paper Trading")
    print("  ETH | BTC | NVDA | AMZN")
    print(f"  Dashboard: http://localhost:{DASH_PORT}")
    print("=" * 60)
    _trader = UnifiedTrader()
    server = http.server.HTTPServer(("0.0.0.0", DASH_PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"\n  Dashboard: http://localhost:{DASH_PORT}")
    print("  Running... (Ctrl+C to stop)\n")
    try:
        while True:
            try: _trader.cycle_all()
            except KeyboardInterrupt: raise
            except Exception as e: print(f"  [error] {e}")
            time.sleep(CYCLE_SEC)
    except KeyboardInterrupt:
        print("\n  Stopping...")
        for sym in _trader.states: _trader.save(sym)


if __name__ == "__main__":
    main()
