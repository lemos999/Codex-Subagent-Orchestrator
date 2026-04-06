"""Multi-Asset Paper Trading - Crypto + Stocks.

Runs parallel paper traders for multiple assets:
- Crypto: via ccxt (Binance Futures, 24/7)
- Stocks: via yfinance (US market hours only)

Same CMA-ES + XGBoost hybrid strategy adapted per asset class.
Dashboard on http://localhost:8896.

Usage:
    cd "Projects/Trading Value"
    py -3.12 scripts/paper_multi.py
"""
from __future__ import annotations

import json
import sys
import threading
import time
import http.server
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import ccxt
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ccxt"])
    import ccxt

try:
    import yfinance as yf
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DASH_PORT = 8896
INITIAL_BALANCE = 10_000.0
CYCLE_SECONDS = 60

# CMA-ES params (ETH-proven, applied to all with per-asset leverage)
BASE_PARAMS = {
    "ma_fast": 21, "ma_slow": 95,
    "rsi_oversold": 28.3, "rsi_overbought": 67.5,
    "vol_filter": 2.89,
    "atr_stop_mult": 3.89, "atr_tp_mult": 3.75,
    "trail_start": 4.89, "trail_step": 0.31,
    "cooldown_bars": 5, "risk_per_trade": 0.019,
    "confidence_threshold": 0.55,
}

ASSETS = [
    {"symbol": "BTC", "type": "crypto", "ccxt_symbol": "BTC/USDT:USDT",
     "yf_symbol": None, "leverage": 1.6, "timeframe": "15m"},
    {"symbol": "NVDA", "type": "stock", "ccxt_symbol": None,
     "yf_symbol": "NVDA", "leverage": 1.0, "timeframe": "15m"},
    {"symbol": "AMZN", "type": "stock", "ccxt_symbol": None,
     "yf_symbol": "AMZN", "leverage": 1.0, "timeframe": "15m"},
]


@dataclass
class AssetState:
    symbol: str = ""
    asset_type: str = ""
    balance: float = INITIAL_BALANCE
    position: str = "FLAT"
    entry_price: float = 0.0
    stop_price: float = 0.0
    tp_price: float = 0.0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    peak_balance: float = INITIAL_BALANCE
    max_drawdown_pct: float = 0.0
    current_pnl_pct: float = 0.0
    current_price: float = 0.0
    last_update: str = ""
    last_reason: str = ""
    started_at: str = ""
    total_signals_checked: int = 0
    last_analysis_at_trade: int = 0
    confidence_threshold: float = 0.55
    leverage: float = 1.6
    paused: bool = False
    pause_reason: str = ""
    evolution_log: list = field(default_factory=list)
    trades: list = field(default_factory=list)


def compute_features(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    c = df["close"]; h = df["high"]; lo = df["low"]; v = df["volume"]
    feat = pd.DataFrame(index=df.index)
    for w in [5, 20, 50, 200]:
        ma = c.rolling(w).mean()
        feat[f"ma{w}_pos"] = (c - ma) / ma.where(ma > 0, 1.0)
    ma5 = c.rolling(5).mean(); ma20 = c.rolling(20).mean()
    ma50 = c.rolling(50).mean(); ma200 = c.rolling(200).mean()
    feat["cross_5_20"] = (ma5 - ma20) / ma20.where(ma20 > 0, 1.0)
    feat["cross_20_50"] = (ma20 - ma50) / ma50.where(ma50 > 0, 1.0)
    feat["cross_50_200"] = (ma50 - ma200) / ma200.where(ma200 > 0, 1.0)
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    feat["rsi14"] = 100 - (100 / (1 + rs))
    tr = pd.concat([h - lo, (h - c.shift(1)).abs(), (lo - c.shift(1)).abs()], axis=1).max(axis=1)
    feat["atr_norm"] = tr.rolling(14).mean() / c.where(c > 0, 1.0)
    dc_high = h.rolling(20).max(); dc_low = lo.rolling(20).min()
    dc_range = dc_high - dc_low
    feat["donchian_pos"] = (c - dc_low) / dc_range.where(dc_range > 0, 1.0)
    vol_ma20 = v.rolling(20).mean()
    feat["vol_ratio"] = v / vol_ma20.where(vol_ma20 > 0, 1.0)
    feat["mom_1"] = c.pct_change(1)
    feat["mom_4"] = c.pct_change(4)
    feat["mom_12"] = c.pct_change(12)
    hour = df.index.hour + df.index.minute / 60.0
    feat["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    feat["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    dow = df.index.dayofweek.astype(float)
    feat["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    feat["dow_cos"] = np.cos(2 * np.pi * dow / 7)
    return feat.values, list(feat.columns)


class AssetTrader:
    """Paper trader for a single asset."""

    def __init__(self, config: dict, exchange: ccxt.binance | None):
        self.config = config
        self.exchange = exchange
        self.state = AssetState(
            symbol=config["symbol"], asset_type=config["type"],
            leverage=config["leverage"],
        )
        self._last_bar_ts = 0
        self._bars_since_trade = 999

        # Load saved state
        state_file = DATA_DIR / f"paper_{config['symbol'].lower()}_state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                trades = data.pop("trades", [])
                self.state = AssetState(**{k: v for k, v in data.items()
                                          if k in AssetState.__dataclass_fields__})
                self.state.trades = trades
            except Exception:
                pass
        if not self.state.started_at:
            self.state.started_at = datetime.now(tz=timezone.utc).isoformat()

    def save_state(self):
        state_file = DATA_DIR / f"paper_{self.config['symbol'].lower()}_state.json"
        state_file.write_text(json.dumps(asdict(self.state), indent=2, default=str),
                              encoding="utf-8")

    def fetch_candles(self) -> pd.DataFrame | None:
        """Fetch 15m candles from appropriate source."""
        try:
            if self.config["type"] == "crypto":
                ohlcv = self.exchange.fetch_ohlcv(
                    self.config["ccxt_symbol"], "15m", limit=250)
                df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
                df["datetime"] = pd.to_datetime(df["ts"], unit="ms")
                df.set_index("datetime", inplace=True)
                df.drop(columns=["ts"], inplace=True)
                return df
            else:
                # Stock: use yfinance
                ticker = yf.Ticker(self.config["yf_symbol"])
                df = ticker.history(period="60d", interval="15m")
                if df is None or len(df) < 50:
                    return None
                df = df.rename(columns={
                    "Open": "open", "High": "high", "Low": "low",
                    "Close": "close", "Volume": "volume"
                })
                df = df[["open", "high", "low", "close", "volume"]].dropna()
                return df
        except Exception as e:
            print(f"  [{self.config['symbol']}] Fetch error: {e}")
            return None

    def is_market_open(self) -> bool:
        """Check if market is open for this asset."""
        if self.config["type"] == "crypto":
            return True  # 24/7
        # US stock market: Mon-Fri 9:30-16:00 ET
        from zoneinfo import ZoneInfo
        now_et = datetime.now(tz=ZoneInfo("America/New_York"))
        if now_et.weekday() >= 5:  # weekend
            return False
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= now_et <= market_close

    def cycle(self):
        """One trading cycle."""
        now = datetime.now(tz=timezone.utc)

        if now.minute % 15 != 0:
            return
        bar_ts = int(now.timestamp()) // 900 * 900
        if bar_ts == self._last_bar_ts:
            return
        self._last_bar_ts = bar_ts

        if not self.is_market_open():
            return

        df = self.fetch_candles()
        if df is None or len(df) < 200:
            return

        price = df["close"].iloc[-1]
        self.state.current_price = float(price)
        self.state.last_update = now.isoformat()
        self.state.total_signals_checked += 1
        self._bars_since_trade += 1

        # Update unrealized PnL
        if self.state.position == "LONG" and self.state.entry_price > 0:
            self.state.current_pnl_pct = (price / self.state.entry_price - 1) * 100
        else:
            self.state.current_pnl_pct = 0.0

        # Paused? Skip trading
        if self.state.paused:
            self.state.last_reason = f"PAUSED: {self.state.pause_reason}"
            self.save_state()
            return

        # Compute indicators
        c = df["close"].values
        h = df["high"].values
        lo = df["low"].values
        v = df["volume"].values
        n = len(c)

        def sma(arr, w):
            out = np.full(n, np.nan)
            cs = np.cumsum(arr); cs = np.insert(cs, 0, 0)
            if n >= w: out[w-1:] = (cs[w:] - cs[:-w]) / w
            return out

        p = BASE_PARAMS
        ma_f = sma(c, p["ma_fast"])
        ma_s = sma(c, p["ma_slow"])
        delta = np.diff(c, prepend=c[0])
        gain = np.where(delta > 0, delta, 0.0)
        loss_arr = np.where(delta < 0, -delta, 0.0)
        avg_g = sma(gain, 14); avg_l = sma(loss_arr, 14)
        rsi = np.full(n, 50.0)
        valid = avg_l > 0
        rsi[valid] = 100 - 100 / (1 + avg_g[valid] / avg_l[valid])
        tr = np.maximum(h[1:] - lo[1:],
                        np.maximum(np.abs(h[1:] - c[:-1]), np.abs(lo[1:] - c[:-1])))
        tr = np.insert(tr, 0, h[0] - lo[0])
        atr = sma(tr, 14)
        vol_ma = sma(v, 20)

        i = n - 1  # latest bar
        mf = ma_f[i]; ms = ma_s[i]
        if np.isnan(mf) or np.isnan(ms):
            self.state.last_reason = "Insufficient data for MA"
            return

        cur_atr = atr[i] if not np.isnan(atr[i]) else 0
        cur_rsi = rsi[i]
        cur_vm = vol_ma[i] if not np.isnan(vol_ma[i]) else 0
        vol_ok = v[i] > p["vol_filter"] * cur_vm if cur_vm > 0 else False
        uptrend = mf > ms
        leverage = self.state.leverage

        # Exit logic
        if self.state.position == "LONG":
            exited = False
            exit_price = price
            reason = ""

            if price <= self.state.stop_price:
                exited = True; reason = "Stop loss"
            elif price >= self.state.tp_price:
                exited = True; reason = "Take profit"

            if exited:
                pnl_pct = (exit_price / self.state.entry_price - 1) * leverage
                comm = 0.001 if self.config["type"] == "stock" else 0.0005
                pnl_pct -= comm * leverage
                self.state.balance *= (1.0 + pnl_pct)
                if self.state.balance < 0:
                    self.state.balance = 0.0
                self.state.total_trades += 1
                if pnl_pct > 0:
                    self.state.wins += 1
                else:
                    self.state.losses += 1
                if self.state.balance > self.state.peak_balance:
                    self.state.peak_balance = self.state.balance
                dd = (self.state.peak_balance - self.state.balance) / self.state.peak_balance * 100
                if dd > self.state.max_drawdown_pct:
                    self.state.max_drawdown_pct = dd
                self.state.trades.append({
                    "time": now.isoformat(), "side": "LONG",
                    "entry": self.state.entry_price, "exit": float(exit_price),
                    "pnl_pct": round(pnl_pct * 100, 2),
                    "balance": round(self.state.balance, 2), "reason": reason,
                })
                self.state.position = "FLAT"
                self.state.entry_price = 0.0
                self._bars_since_trade = 0
                self.state.last_reason = f"EXIT: {reason}"
                print(f"  [{self.config['symbol']}] EXIT ${exit_price:,.2f} | {reason} | Bal=${self.state.balance:,.0f}")

        # Entry logic
        if self.state.position == "FLAT" and self._bars_since_trade >= p["cooldown_bars"]:
            if uptrend and cur_rsi < p["rsi_oversold"] and vol_ok and cur_atr > 0:
                self.state.position = "LONG"
                self.state.entry_price = float(price)
                self.state.stop_price = float(price - p["atr_stop_mult"] * cur_atr)
                self.state.tp_price = float(price + p["atr_tp_mult"] * cur_atr)
                self._bars_since_trade = 0
                self.state.last_reason = f"ENTRY: RSI={cur_rsi:.1f}, ATR={cur_atr:.2f}"
                print(f"  [{self.config['symbol']}] ENTER LONG ${price:,.2f} | RSI={cur_rsi:.1f}")
            else:
                reasons = []
                if not uptrend: reasons.append("No uptrend")
                if cur_rsi >= p["rsi_oversold"]: reasons.append(f"RSI={cur_rsi:.1f}")
                if not vol_ok: reasons.append("Low vol")
                self.state.last_reason = "No entry: " + "; ".join(reasons)

        # Auto-analysis trigger
        self._auto_evolve()
        self.save_state()

    def _auto_evolve(self):
        """Auto-analysis every 5 trades - adjust leverage and threshold."""
        trades_since = self.state.total_trades - self.state.last_analysis_at_trade
        if trades_since < 5:
            return
        self.state.last_analysis_at_trade = self.state.total_trades
        sym = self.config["symbol"]

        rets = [t.get("pnl_pct", 0) for t in self.state.trades]
        recent = [t.get("pnl_pct", 0) for t in self.state.trades[-10:]]
        total_ret = (self.state.balance / INITIAL_BALANCE - 1) * 100
        wr = self.state.wins / max(self.state.total_trades, 1) * 100
        recent_wr = sum(1 for r in recent if r > 0) / max(len(recent), 1) * 100
        avg_win = np.mean([r for r in rets if r > 0]) if any(r > 0 for r in rets) else 0
        avg_loss = np.mean([r for r in rets if r < 0]) if any(r < 0 for r in rets) else 0
        dd = self.state.max_drawdown_pct

        decision = "CONTINUE"
        adjustments = []

        # GOAL
        if total_ret > 10 and self.state.total_trades >= 20 and wr >= 50:
            decision = "GOAL_APPROACHING"
            adjustments.append("Target zone!")

        # PAUSE on heavy DD
        if dd > 30:
            self.state.paused = True
            self.state.pause_reason = f"DD {dd:.1f}% > 30%"
            decision = "PAUSE"
            adjustments.append(f"PAUSED: DD {dd:.1f}%")

        # Underperforming - tighten
        elif len(recent) >= 5 and recent_wr < 35:
            old = self.state.confidence_threshold
            new = min(old + 0.02, 0.65)
            if new != old:
                self.state.confidence_threshold = new
                adjustments.append(f"Conf: {old:.2f}->{new:.2f}")
                decision = "ADJUSTED"

        # Leverage adjust
        max_lev = 2.5 if self.config["type"] == "crypto" else 1.5
        if self.state.total_trades >= 10 and decision != "PAUSE":
            old_lev = self.state.leverage
            pf = abs(avg_win / avg_loss) if avg_loss != 0 else 1.0
            if total_ret > 5 and wr >= 55 and pf >= 1.2 and dd < 20:
                new_lev = min(old_lev + 0.2, max_lev)
            elif total_ret < -5 or dd > 20:
                new_lev = max(old_lev - 0.3, 1.0)
            else:
                new_lev = old_lev
            new_lev = round(new_lev, 1)
            if new_lev != old_lev:
                self.state.leverage = new_lev
                adjustments.append(f"Lev: {old_lev}x->{new_lev}x")
                if decision == "CONTINUE":
                    decision = "ADJUSTED"

        if not adjustments:
            adjustments.append("No changes")

        self.state.evolution_log.append({
            "time": datetime.now(tz=timezone.utc).isoformat(),
            "decision": decision, "adjustments": adjustments,
            "total_trades": self.state.total_trades,
            "total_return": round(total_ret, 2),
            "leverage": self.state.leverage,
        })
        if len(self.state.evolution_log) > 30:
            self.state.evolution_log = self.state.evolution_log[-30:]

        print(f"  [{sym}] EVOLVE: {decision} | Ret={total_ret:+.1f}% WR={wr:.0f}% | {'; '.join(adjustments)}")


# ── Global state ──────────────────────────────────────────────────────────────
_traders: list[AssetTrader] = []

# ── Dashboard ─────────────────────────────────────────────────────────────────
DASH_HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<title>Multi-Asset Paper Trading</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e0e0;font-family:'Segoe UI',system-ui,monospace;min-height:100vh}
.hdr{background:#141926;padding:14px 24px;border-bottom:1px solid #2a3040;display:flex;justify-content:space-between;align-items:center}
.hdr h1{font-size:16px;color:#ff9800;letter-spacing:1px}
.wrap{padding:16px 24px;max-width:1100px;margin:0 auto}
.gn{color:#00d4aa}.rd{color:#ff4d6a}.yl{color:#ffd700}.bl{color:#4dabf7}.gy{color:#555}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px;margin-bottom:14px}
.card{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:16px}
.card h3{font-size:13px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center}
.card .tag{font-size:9px;padding:2px 6px;border-radius:3px;background:#2a3040}
.card .tag.crypto{color:#ffd700}.card .tag.stock{color:#4dabf7}
.row{display:flex;justify-content:space-between;font-size:11px;padding:3px 0;border-bottom:1px solid #1a2030}
.row .k{color:#555}.row .v{font-weight:bold}
.summary{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:16px;margin-bottom:14px}
.summary h2{font-size:11px;color:#555;margin-bottom:10px;text-transform:uppercase}
table{width:100%;border-collapse:collapse;font-size:11px}
th{text-align:left;color:#555;padding:5px 6px;border-bottom:1px solid #2a3040;font-size:10px}
td{padding:5px 6px;border-bottom:1px solid #1a2030}
</style></head><body>
<div class="hdr"><h1>Multi-Asset Paper Trading</h1><div id="clock" style="font-size:11px;color:#555">--</div></div>
<div class="wrap">
  <div class="summary" id="totalSummary"></div>
  <div class="cards" id="cards"></div>
  <div class="summary"><h2>Recent Trades (All Assets)</h2>
    <table><thead><tr><th>Asset</th><th>Time</th><th>Side</th><th>Entry</th><th>Exit</th><th>PnL%</th><th>Balance</th></tr></thead>
    <tbody id="allTrades"></tbody></table>
  </div>
</div>
<script>
function fmt(v){return v>=0?'+'+v.toFixed(2):v.toFixed(2)}
async function refresh(){
  document.getElementById('clock').textContent=new Date().toLocaleString('ko-KR');
  try{
    const r=await fetch('/api/status?'+Date.now());
    if(!r.ok)return;
    const assets=await r.json();
    let totalBal=0,totalInit=0,totalTrades=0,totalWins=0;
    let cardsHtml='';
    let allTrades=[];
    for(const a of assets){
      totalBal+=a.balance;totalInit+=10000;
      totalTrades+=a.total_trades;totalWins+=a.wins;
      const ret=((a.balance/10000-1)*100);
      const wr=a.total_trades>0?(a.wins/a.total_trades*100).toFixed(0)+'%':'--';
      const posHtml=a.position!=='FLAT'
        ?`<span class="gn">${a.position} @$${parseFloat(a.entry_price).toFixed(2)} (${fmt(a.current_pnl_pct)}%)</span>`
        :'<span class="gy">FLAT</span>';
      cardsHtml+=`<div class="card">
        <h3>${a.symbol} <span class="tag ${a.asset_type}">${a.asset_type}</span></h3>
        <div class="row"><span class="k">Price</span><span class="v">$${parseFloat(a.current_price||0).toLocaleString(undefined,{minimumFractionDigits:2})}</span></div>
        <div class="row"><span class="k">Balance</span><span class="v ${a.balance>=10000?'gn':'rd'}">$${Math.round(a.balance).toLocaleString()}</span></div>
        <div class="row"><span class="k">Return</span><span class="v ${ret>=0?'gn':'rd'}">${fmt(ret)}%</span></div>
        <div class="row"><span class="k">Trades</span><span class="v">${a.total_trades} (WR ${wr})</span></div>
        <div class="row"><span class="k">Max DD</span><span class="v rd">${a.max_drawdown_pct>0?'-'+a.max_drawdown_pct.toFixed(1)+'%':'0%'}</span></div>
        <div class="row"><span class="k">Position</span><span class="v">${posHtml}</span></div>
        <div style="font-size:10px;color:#444;margin-top:6px">${a.last_reason||'--'}</div>
      </div>`;
      for(const t of (a.trades||[]).slice(-5)){t._symbol=a.symbol;allTrades.push(t)}
    }
    document.getElementById('cards').innerHTML=cardsHtml;
    const totalRet=((totalBal/totalInit-1)*100);
    const totalWR=totalTrades>0?(totalWins/totalTrades*100).toFixed(0)+'%':'--';
    document.getElementById('totalSummary').innerHTML=`<h2>Portfolio Summary</h2>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px">
        <div style="text-align:center"><div style="font-size:9px;color:#555">Total Balance</div><div style="font-size:20px;font-weight:bold" class="${totalBal>=totalInit?'gn':'rd'}">$${Math.round(totalBal).toLocaleString()}</div></div>
        <div style="text-align:center"><div style="font-size:9px;color:#555">Total Return</div><div style="font-size:20px;font-weight:bold" class="${totalRet>=0?'gn':'rd'}">${fmt(totalRet)}%</div></div>
        <div style="text-align:center"><div style="font-size:9px;color:#555">Trades</div><div style="font-size:20px;font-weight:bold">${totalTrades}</div></div>
        <div style="text-align:center"><div style="font-size:9px;color:#555">Win Rate</div><div style="font-size:20px;font-weight:bold">${totalWR}</div></div>
      </div>`;
    allTrades.sort((a,b)=>(b.time||'').localeCompare(a.time||''));
    let tRows='';
    for(const t of allTrades.slice(0,20)){
      const pnl=t.pnl_pct||0;
      tRows+=`<tr><td class="yl">${t._symbol}</td><td>${(t.time||'').slice(5,16)}</td>
        <td class="gn">${t.side}</td><td>$${parseFloat(t.entry||0).toFixed(2)}</td>
        <td>$${parseFloat(t.exit||0).toFixed(2)}</td>
        <td class="${pnl>=0?'gn':'rd'}">${fmt(pnl)}%</td>
        <td>$${Math.round(t.balance||0).toLocaleString()}</td></tr>`;
    }
    if(!tRows)tRows='<tr><td colspan="7" class="gy" style="text-align:center">No trades yet</td></tr>';
    document.getElementById('allTrades').innerHTML=tRows;
  }catch(e){}
}
refresh();setInterval(refresh,5000);
</script></body></html>"""


class MultiDashHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/status"):
            data = [asdict(t.state) for t in _traders]
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
    global _traders

    print("=" * 60)
    print("  Multi-Asset Paper Trading")
    print(f"  Assets: {', '.join(a['symbol'] for a in ASSETS)}")
    print(f"  Dashboard: http://localhost:{DASH_PORT}")
    print("=" * 60)

    # Shared exchange for crypto
    exchange = ccxt.binance({"options": {"defaultType": "future"}})
    exchange.load_markets()

    for cfg in ASSETS:
        trader = AssetTrader(cfg, exchange if cfg["type"] == "crypto" else None)
        _traders.append(trader)
        wr = trader.state.wins / max(trader.state.total_trades, 1) * 100
        print(f"  [{cfg['symbol']}] Bal=${trader.state.balance:,.0f} | "
              f"Trades={trader.state.total_trades} | "
              f"{'Crypto 24/7' if cfg['type'] == 'crypto' else 'Stock US hours'}")

    # Start dashboard
    server = http.server.HTTPServer(("0.0.0.0", DASH_PORT), MultiDashHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"\n  Dashboard: http://localhost:{DASH_PORT}")
    print(f"  Running... (Ctrl+C to stop)\n")

    try:
        while True:
            for trader in _traders:
                try:
                    trader.cycle()
                except Exception as e:
                    print(f"  [{trader.config['symbol']}] Error: {e}")
            time.sleep(CYCLE_SECONDS)
    except KeyboardInterrupt:
        print("\n  Stopped.")
        for t in _traders:
            t.save_state()


if __name__ == "__main__":
    main()
