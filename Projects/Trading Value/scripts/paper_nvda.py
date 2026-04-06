"""NVDA Regime-Based Paper Trading.

Strategy: MA 30/50 regime detection + leveraged positioning.
- Bull (MA30 > MA50 AND price > MA30): 3x leverage
- Mild bull (MA30 > MA50 but price < MA30): 0.5x
- Bear (MA30 < MA50): FLAT
- Trailing stop: 5%

Data: yfinance real-time daily bars.
Dashboard: http://localhost:8897

Usage:
    cd "Projects/Trading Value"
    py -3.12 scripts/paper_nvda.py
"""
from __future__ import annotations
import json, sys, threading, time, http.server
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd

try:
    import yfinance as yf
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATE_FILE = DATA_DIR / "paper_nvda_state.json"
LOG_FILE = DATA_DIR / "paper_nvda_log.jsonl"
DASH_PORT = 8897
INITIAL = 10_000.0
CYCLE_SECONDS = 300  # check every 5 min (daily strategy, no rush)

PARAMS = {"ma_fast": 30, "ma_slow": 50, "lev_bull": 3.0, "lev_mild": 0.5, "stop_pct": 0.05}


@dataclass
class NvdaState:
    balance: float = INITIAL
    position: str = "FLAT"
    entry_price: float = 0.0
    stop_price: float = 0.0
    current_leverage: float = 0.0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    peak_balance: float = INITIAL
    max_drawdown_pct: float = 0.0
    current_price: float = 0.0
    current_pnl_pct: float = 0.0
    regime: str = "UNKNOWN"
    last_update: str = ""
    started_at: str = ""
    total_checks: int = 0
    trades: list = field(default_factory=list)
    activity_log: list = field(default_factory=list)


class NvdaPaperTrader:
    def __init__(self):
        self.state = self._load_state()
        if not self.state.started_at:
            self.state.started_at = datetime.now(tz=timezone.utc).isoformat()
        self._last_date = ""
        print(f"  [init] NVDA Regime | Bal=${self.state.balance:,.0f} | {self.state.position}")

    def _load_state(self) -> NvdaState:
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                trades = data.pop("trades", [])
                activity = data.pop("activity_log", [])
                s = NvdaState(**{k: v for k, v in data.items() if k in NvdaState.__dataclass_fields__})
                s.trades = trades; s.activity_log = activity
                return s
            except Exception:
                pass
        return NvdaState()

    def _save(self):
        STATE_FILE.write_text(json.dumps(asdict(self.state), indent=2, default=str), encoding="utf-8")

    def _is_market_open(self):
        from zoneinfo import ZoneInfo
        now = datetime.now(tz=ZoneInfo("America/New_York"))
        if now.weekday() >= 5: return False
        return now.hour >= 9 and (now.hour < 16 or (now.hour == 9 and now.minute >= 30))

    def cycle(self):
        now = datetime.now(tz=timezone.utc)
        today = now.strftime("%Y-%m-%d")

        # Only check once per day (at market close)
        if today == self._last_date:
            return
        if not self._is_market_open():
            return

        try:
            df = yf.Ticker("NVDA").history(period="120d", interval="1d")
            if df is None or len(df) < 60:
                return
        except Exception as e:
            print(f"  [{now:%H:%M}] Fetch error: {e}")
            return

        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low",
                                "Close": "close", "Volume": "volume"})
        c = df["close"].values
        price = float(c[-1])

        self._last_date = today
        self.state.current_price = price
        self.state.last_update = now.isoformat()
        self.state.total_checks += 1

        # Compute MAs
        p = PARAMS
        n = len(c)
        def sma(arr, w):
            if len(arr) < w: return np.nan
            return arr[-w:].mean()
        ma_f = sma(c, p["ma_fast"])
        ma_s = sma(c, p["ma_slow"])

        # Regime
        if np.isnan(ma_f) or np.isnan(ma_s):
            self.state.regime = "UNKNOWN"
            return

        bull = ma_f > ma_s and price > ma_f
        mild = ma_f > ma_s and price <= ma_f
        bear = ma_f <= ma_s
        self.state.regime = "BULL" if bull else ("MILD" if mild else "BEAR")

        # Unrealized PnL
        if self.state.position != "FLAT" and self.state.entry_price > 0:
            self.state.current_pnl_pct = (price / self.state.entry_price - 1) * self.state.current_leverage * 100
        else:
            self.state.current_pnl_pct = 0.0

        action = self.state.position

        # Exit logic
        if self.state.position != "FLAT":
            exit_reason = ""
            if bear:
                exit_reason = "Regime -> BEAR"
            elif price <= self.state.stop_price:
                exit_reason = "Stop loss"

            if exit_reason:
                pnl_pct = (price / self.state.entry_price - 1) * self.state.current_leverage
                dd = (self.state.peak_balance - self.state.balance) / self.state.peak_balance * 100 if self.state.peak_balance > 0 else 0
                sz = 0.25 if dd > 25 else (0.5 if dd > 15 else 1.0)
                pnl_pct *= sz
                pnl_pct -= 0.001 * self.state.current_leverage * sz
                self.state.balance *= (1 + pnl_pct)
                if self.state.balance < 0: self.state.balance = 0
                self.state.total_trades += 1
                if pnl_pct > 0: self.state.wins += 1
                else: self.state.losses += 1
                if self.state.balance > self.state.peak_balance:
                    self.state.peak_balance = self.state.balance
                dd_new = (self.state.peak_balance - self.state.balance) / self.state.peak_balance * 100
                if dd_new > self.state.max_drawdown_pct:
                    self.state.max_drawdown_pct = dd_new
                self.state.trades.append({
                    "time": now.isoformat(), "side": "LONG", "entry": self.state.entry_price,
                    "exit": price, "pnl_pct": round(pnl_pct * 100, 2),
                    "balance": round(self.state.balance, 2), "reason": exit_reason,
                })
                self.state.position = "FLAT"
                self.state.entry_price = 0.0
                action = f"EXIT ({exit_reason})"
                print(f"  [NVDA {today}] EXIT ${price:,.2f} | {exit_reason} | Bal=${self.state.balance:,.0f}")

        # Entry logic
        if self.state.position == "FLAT":
            if bull:
                self.state.position = "LONG"
                self.state.entry_price = price
                self.state.current_leverage = p["lev_bull"]
                self.state.stop_price = price * (1 - p["stop_pct"])
                action = f"ENTER BULL {p['lev_bull']}x"
                print(f"  [NVDA {today}] ENTER BULL ${price:,.2f} | {p['lev_bull']}x | Stop=${self.state.stop_price:,.2f}")
            elif mild:
                self.state.position = "LONG"
                self.state.entry_price = price
                self.state.current_leverage = p["lev_mild"]
                self.state.stop_price = price * (1 - p["stop_pct"])
                action = f"ENTER MILD {p['lev_mild']}x"
                print(f"  [NVDA {today}] ENTER MILD ${price:,.2f} | {p['lev_mild']}x")
        elif self.state.position != "FLAT":
            # Update trailing stop
            new_stop = price * (1 - p["stop_pct"])
            if new_stop > self.state.stop_price:
                self.state.stop_price = new_stop

        self.state.activity_log.append({
            "time": today, "price": round(price, 2), "action": action,
            "regime": self.state.regime, "ma_f": round(ma_f, 2), "ma_s": round(ma_s, 2),
        })
        if len(self.state.activity_log) > 100:
            self.state.activity_log = self.state.activity_log[-100:]

        self._save()


_trader = None

DASH_HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><title>NVDA Paper Trading</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e0e0;font-family:'Segoe UI',system-ui,monospace}
.hdr{background:#141926;padding:14px 24px;border-bottom:1px solid #2a3040;display:flex;justify-content:space-between}
.hdr h1{font-size:16px;color:#76b900}
.wrap{padding:16px 24px;max-width:900px;margin:0 auto}
.gn{color:#00d4aa}.rd{color:#ff4d6a}.yl{color:#ffd700}.bl{color:#4dabf7}.gy{color:#555}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}
.metric{background:#0a0e17;padding:12px;border-radius:6px;border:1px solid #2a3040;text-align:center}
.metric .label{font-size:9px;color:#555;margin-bottom:4px}
.metric .value{font-size:18px;font-weight:bold}
.section{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:16px;margin-bottom:14px}
.section h2{font-size:11px;color:#555;margin-bottom:10px;text-transform:uppercase}
table{width:100%;border-collapse:collapse;font-size:11px}
th{text-align:left;color:#555;padding:5px 6px;border-bottom:1px solid #2a3040}
td{padding:5px 6px;border-bottom:1px solid #1a2030}
.regime-badge{padding:3px 8px;border-radius:4px;font-size:10px;font-weight:bold}
.regime-BULL{background:#00d4aa22;color:#00d4aa}
.regime-MILD{background:#ffd70022;color:#ffd700}
.regime-BEAR{background:#ff4d6a22;color:#ff4d6a}
</style></head><body>
<div class="hdr"><h1>NVDA Regime Paper Trading</h1><div id="clock" style="font-size:11px;color:#555"></div></div>
<div class="wrap">
  <div class="metrics" id="metrics"></div>
  <div class="section" id="pos"></div>
  <div class="section"><h2>Activity Log</h2><div id="log" style="max-height:300px;overflow-y:auto"></div></div>
  <div class="section"><h2>Trades</h2>
    <table><thead><tr><th>Date</th><th>Entry</th><th>Exit</th><th>PnL%</th><th>Balance</th><th>Reason</th></tr></thead>
    <tbody id="trades"></tbody></table>
  </div>
</div>
<script>
function fmt(v){return v>=0?'+'+v.toFixed(2):v.toFixed(2)}
async function refresh(){
  document.getElementById('clock').textContent=new Date().toLocaleString('ko-KR');
  try{
    const r=await fetch('/api/status?'+Date.now());if(!r.ok)return;
    const d=await r.json();
    const ret=((d.balance/10000-1)*100);
    const wr=d.total_trades>0?(d.wins/d.total_trades*100).toFixed(0)+'%':'--';
    document.getElementById('metrics').innerHTML=`
      <div class="metric"><div class="label">Balance</div><div class="value ${d.balance>=10000?'gn':'rd'}">$${Math.round(d.balance).toLocaleString()}</div></div>
      <div class="metric"><div class="label">Return</div><div class="value ${ret>=0?'gn':'rd'}">${fmt(ret)}%</div></div>
      <div class="metric"><div class="label">Regime</div><div class="value"><span class="regime-badge regime-${d.regime||'UNKNOWN'}">${d.regime||'--'}</span></div></div>
      <div class="metric"><div class="label">NVDA Price</div><div class="value bl">$${parseFloat(d.current_price||0).toFixed(2)}</div></div>`;
    let posH='';
    if(d.position!=='FLAT'){
      posH=`<h2>Position</h2><div style="font-size:14px;font-weight:bold" class="gn">LONG ${d.current_leverage||0}x @ $${parseFloat(d.entry_price).toFixed(2)}</div>
        <div style="margin-top:6px">Stop: $${parseFloat(d.stop_price).toFixed(2)} | Unrealized: <span class="${(d.current_pnl_pct||0)>=0?'gn':'rd'}">${fmt(d.current_pnl_pct||0)}%</span></div>`;
    } else { posH='<h2>Position</h2><div class="gy">FLAT - Waiting for regime signal</div>'; }
    document.getElementById('pos').innerHTML=posH;
    const logs=(d.activity_log||[]).slice(-20).reverse();
    let lH='';for(const l of logs){
      lH+=`<div style="display:flex;gap:8px;padding:3px 0;border-bottom:1px solid #1a2030;font-size:10px">
        <span class="gy" style="min-width:70px">${l.time}</span>
        <span style="min-width:60px">$${l.price}</span>
        <span class="regime-badge regime-${l.regime}" style="min-width:40px">${l.regime}</span>
        <span>${l.action}</span></div>`;}
    document.getElementById('log').innerHTML=lH||'<div class="gy" style="padding:20px;text-align:center">Waiting for market open...</div>';
    const trades=(d.trades||[]).slice(-10).reverse();
    let tH='';for(const t of trades){const p=t.pnl_pct||0;
      tH+=`<tr><td>${(t.time||'').slice(0,10)}</td><td>$${parseFloat(t.entry).toFixed(2)}</td><td>$${parseFloat(t.exit).toFixed(2)}</td>
        <td class="${p>=0?'gn':'rd'}">${fmt(p)}%</td><td>$${Math.round(t.balance).toLocaleString()}</td><td class="gy">${t.reason}</td></tr>`;}
    if(!tH)tH='<tr><td colspan="6" class="gy" style="text-align:center">No trades yet</td></tr>';
    document.getElementById('trades').innerHTML=tH;
  }catch(e){}
}
refresh();setInterval(refresh,10000);
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/status"):
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(json.dumps(asdict(_trader.state) if _trader else {}, default=str).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASH_HTML.encode())
    def log_message(self, *a): pass


def main():
    global _trader
    print("="*60)
    print("  NVDA Regime Paper Trading")
    print("  Strategy: MA 30/50 + Bull 3x / Mild 0.5x / Bear FLAT")
    print(f"  Dashboard: http://localhost:{DASH_PORT}")
    print("="*60)
    _trader = NvdaPaperTrader()
    server = http.server.HTTPServer(("0.0.0.0", DASH_PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"  Dashboard: http://localhost:{DASH_PORT}")
    print("  Running... (Ctrl+C to stop)\n")
    try:
        while True:
            try: _trader.cycle()
            except KeyboardInterrupt: raise
            except Exception as e: print(f"  [error] {e}")
            time.sleep(CYCLE_SECONDS)
    except KeyboardInterrupt:
        print("\n  Stopped."); _trader._save()


if __name__ == "__main__":
    main()
