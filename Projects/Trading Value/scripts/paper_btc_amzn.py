"""BTC + AMZN Paper Trading with auto-evolution.

BTC: 4H MA200 + RSI pullback (best so far: beat B&H by 5.7%p)
AMZN: Daily regime MA30/50 (same structure as NVDA)

Both with auto-evolution engine: every 5 trades, analyze and adjust.

Dashboard: http://localhost:8898

Usage:
    py -3.12 scripts/paper_btc_amzn.py
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
DASH_PORT = 8898
INITIAL = 10_000.0
CYCLE_SECONDS = 60

CONFIGS = {
    "BTC": {
        "type": "crypto", "symbol": "BTC/USDT:USDT",
        "ma_period": 200, "rsi_entry": 30, "stop_atr": 2.0, "tp_atr": 5.0,
        "leverage": 1.5, "timeframe": "4h",
    },
    "AMZN": {
        "type": "stock", "yf_symbol": "AMZN",
        "ma_fast": 30, "ma_slow": 50, "lev_bull": 2.0, "lev_mild": 0.5,
        "stop_pct": 0.05, "timeframe": "1d",
    },
}


@dataclass
class AssetState:
    symbol: str = ""
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
    leverage: float = 1.5
    evolution_log: list = field(default_factory=list)
    trades: list = field(default_factory=list)
    activity_log: list = field(default_factory=list)


def sma_calc(arr, w):
    n = len(arr); out = np.full(n, np.nan)
    cs = np.cumsum(arr); cs = np.insert(cs, 0, 0)
    if n >= w: out[w-1:] = (cs[w:] - cs[:-w]) / w
    return out


class MultiTrader:
    def __init__(self):
        self.exchange = ccxt.binance({"options": {"defaultType": "future"}})
        self.exchange.load_markets()
        self.states = {}
        self._last_btc_ts = 0
        self._last_amzn_date = ""

        for sym in ["BTC", "AMZN"]:
            sf = DATA_DIR / f"paper_{sym.lower()}_v2_state.json"
            if sf.exists():
                try:
                    data = json.loads(sf.read_text(encoding="utf-8"))
                    trades = data.pop("trades", [])
                    activity = data.pop("activity_log", [])
                    evo = data.pop("evolution_log", [])
                    s = AssetState(**{k: v for k, v in data.items() if k in AssetState.__dataclass_fields__})
                    s.trades = trades; s.activity_log = activity; s.evolution_log = evo
                    self.states[sym] = s
                except Exception:
                    self.states[sym] = AssetState(symbol=sym)
            else:
                self.states[sym] = AssetState(symbol=sym, leverage=CONFIGS[sym].get("leverage", 1.5))
            if not self.states[sym].started_at:
                self.states[sym].started_at = datetime.now(tz=timezone.utc).isoformat()
            print(f"  [{sym}] Bal=${self.states[sym].balance:,.0f} | {self.states[sym].position}")

    def save(self, sym):
        sf = DATA_DIR / f"paper_{sym.lower()}_v2_state.json"
        sf.write_text(json.dumps(asdict(self.states[sym]), indent=2, default=str), encoding="utf-8")

    def cycle_btc(self):
        now = datetime.now(tz=timezone.utc)
        # Check every 15 minutes, act on latest 4H bar
        if now.minute % 15 != 0: return
        bar_ts = int(now.timestamp()) // 900 * 900
        if bar_ts == self._last_btc_ts: return
        self._last_btc_ts = bar_ts

        try:
            ohlcv = self.exchange.fetch_ohlcv("BTC/USDT:USDT", "4h", limit=250)
            df = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","volume"])
        except Exception as e:
            print(f"  [BTC] Fetch error: {e}"); return

        c = df["close"].values; h = df["high"].values; lo = df["low"].values
        n = len(c); price = float(c[-1])
        cfg = CONFIGS["BTC"]; s = self.states["BTC"]
        s.current_price = price; s.last_update = now.isoformat(); s.total_checks += 1

        ma = sma_calc(c, cfg["ma_period"])
        delta = np.diff(c, prepend=c[0])
        gain = np.where(delta>0,delta,0.0); loss = np.where(delta<0,-delta,0.0)
        avg_g = sma_calc(gain,14); avg_l = sma_calc(loss,14)
        rsi = np.full(n,50.0); valid = avg_l>0
        rsi[valid] = 100-100/(1+avg_g[valid]/avg_l[valid])
        tr = np.maximum(h[1:]-lo[1:],np.maximum(np.abs(h[1:]-c[:-1]),np.abs(lo[1:]-c[:-1])))
        tr = np.insert(tr,0,h[0]-lo[0]); atr = sma_calc(tr,14)

        i = n-1
        if np.isnan(ma[i]) or np.isnan(atr[i]) or atr[i]<=0: return
        uptrend = c[i] > ma[i]
        s.regime = "BULL" if uptrend else "BEAR"

        if s.position != "FLAT" and s.entry_price > 0:
            s.current_pnl_pct = (price/s.entry_price-1)*s.current_leverage*100

        # Exit
        if s.position == "LONG":
            if price <= s.stop_price or price >= s.tp_price or not uptrend:
                reason = "Stop" if price<=s.stop_price else ("TP" if price>=s.tp_price else "Trend reversal")
                self._close(s, price, reason, 0.0005)

        # Entry
        if s.position == "FLAT" and uptrend and rsi[i] < cfg["rsi_entry"] and atr[i] > 0:
            s.position = "LONG"; s.entry_price = price
            s.current_leverage = s.leverage
            s.stop_price = price - cfg["stop_atr"]*atr[i]
            s.tp_price = price + cfg["tp_atr"]*atr[i]
            s.regime = "ENTRY"
            print(f"  [BTC {now:%m-%d %H:%M}] ENTER ${price:,.0f} | RSI={rsi[i]:.1f}")

        s.activity_log.append({"time":now.strftime("%m-%d %H:%M"),"price":round(price,2),"action":s.position,"regime":s.regime})
        if len(s.activity_log) > 100: s.activity_log = s.activity_log[-100:]
        self._auto_evolve(s, "BTC")
        self.save("BTC")

    def cycle_amzn(self):
        now = datetime.now(tz=timezone.utc)
        today = now.strftime("%Y-%m-%d")
        if today == self._last_amzn_date: return
        from zoneinfo import ZoneInfo
        now_et = datetime.now(tz=ZoneInfo("America/New_York"))
        if now_et.weekday() >= 5 or now_et.hour < 16: return  # wait for market close
        self._last_amzn_date = today

        try:
            df = yf.Ticker("AMZN").history(period="120d", interval="1d")
            if df is None or len(df) < 60: return
        except Exception as e:
            print(f"  [AMZN] Fetch error: {e}"); return

        c = df["Close"].values; price = float(c[-1])
        cfg = CONFIGS["AMZN"]; s = self.states["AMZN"]
        s.current_price = price; s.last_update = now.isoformat(); s.total_checks += 1

        ma_f = c[-cfg["ma_fast"]:].mean() if len(c)>=cfg["ma_fast"] else np.nan
        ma_s = c[-cfg["ma_slow"]:].mean() if len(c)>=cfg["ma_slow"] else np.nan
        if np.isnan(ma_f) or np.isnan(ma_s): return

        bull = ma_f > ma_s and price > ma_f
        mild = ma_f > ma_s and price <= ma_f
        bear = ma_f <= ma_s
        s.regime = "BULL" if bull else ("MILD" if mild else "BEAR")

        if s.position != "FLAT" and s.entry_price > 0:
            s.current_pnl_pct = (price/s.entry_price-1)*s.current_leverage*100

        # Exit
        if s.position == "LONG":
            new_stop = price*(1-cfg["stop_pct"])
            if new_stop > s.stop_price: s.stop_price = new_stop
            if bear or price <= s.stop_price:
                reason = "Bear regime" if bear else "Stop loss"
                self._close(s, price, reason, 0.001)

        # Entry
        if s.position == "FLAT":
            if bull:
                s.position="LONG"; s.entry_price=price; s.current_leverage=cfg["lev_bull"]
                s.stop_price=price*(1-cfg["stop_pct"])
                print(f"  [AMZN {today}] ENTER BULL ${price:,.2f} | {cfg['lev_bull']}x")
            elif mild:
                s.position="LONG"; s.entry_price=price; s.current_leverage=cfg["lev_mild"]
                s.stop_price=price*(1-cfg["stop_pct"])

        s.activity_log.append({"time":today,"price":round(price,2),"action":s.position,"regime":s.regime})
        if len(s.activity_log) > 100: s.activity_log = s.activity_log[-100:]
        self._auto_evolve(s, "AMZN")
        self.save("AMZN")

    def _close(self, s, price, reason, comm):
        pnl = (price/s.entry_price-1)*s.current_leverage
        dd = (s.peak_balance-s.balance)/s.peak_balance*100 if s.peak_balance>0 else 0
        sz = 0.25 if dd>25 else (0.5 if dd>15 else 1.0)
        pnl = pnl*sz - comm*s.current_leverage*sz
        s.balance *= (1+pnl)
        if s.balance < 0: s.balance = 0
        s.total_trades += 1
        if pnl > 0: s.wins += 1
        else: s.losses += 1
        if s.balance > s.peak_balance: s.peak_balance = s.balance
        dd_new = (s.peak_balance-s.balance)/s.peak_balance*100
        if dd_new > s.max_drawdown_pct: s.max_drawdown_pct = dd_new
        s.trades.append({"time":datetime.now(tz=timezone.utc).isoformat(),"entry":s.entry_price,
                         "exit":price,"pnl_pct":round(pnl*100,2),"balance":round(s.balance,2),"reason":reason})
        print(f"  [{s.symbol}] EXIT ${price:,.2f} | {reason} | PnL={pnl*100:+.1f}% | Bal=${s.balance:,.0f}")
        s.position="FLAT"; s.entry_price=0; s.stop_price=0; s.tp_price=0; s.current_pnl_pct=0

    def _auto_evolve(self, s, sym):
        if s.total_trades - s.last_analysis_at < 5: return
        s.last_analysis_at = s.total_trades
        rets = [t.get("pnl_pct",0) for t in s.trades]
        total_ret = (s.balance/INITIAL-1)*100
        wr = s.wins/max(s.total_trades,1)*100
        recent = [t.get("pnl_pct",0) for t in s.trades[-10:]]
        recent_wr = sum(1 for r in recent if r>0)/max(len(recent),1)*100
        dd = s.max_drawdown_pct

        decision = "CONTINUE"; adjustments = []
        if total_ret > 10 and s.total_trades >= 20 and wr >= 50:
            decision = "GOAL_APPROACHING"
            adjustments.append("Target zone!")
        max_lev = 2.5 if CONFIGS[sym].get("type")=="crypto" else 2.0
        if dd > 30:
            decision = "PAUSE"; adjustments.append(f"DD {dd:.1f}% > 30%")
        elif recent_wr < 35 and len(recent) >= 5:
            old = s.leverage; s.leverage = max(old-0.3, 1.0)
            if s.leverage != old: adjustments.append(f"Lev {old}->{s.leverage}")
            decision = "ADJUSTED"
        elif total_ret > 5 and wr >= 55 and dd < 20:
            old = s.leverage; s.leverage = min(old+0.2, max_lev)
            if s.leverage != old: adjustments.append(f"Lev {old}->{s.leverage}")
            decision = "ADJUSTED"

        if not adjustments: adjustments.append("No changes")
        s.evolution_log.append({"time":datetime.now(tz=timezone.utc).isoformat(),"decision":decision,
                                "adjustments":adjustments,"ret":round(total_ret,2),"trades":s.total_trades})
        if len(s.evolution_log) > 30: s.evolution_log = s.evolution_log[-30:]
        print(f"  [{sym}] EVOLVE: {decision} | Ret={total_ret:+.1f}% WR={wr:.0f}% | {'; '.join(adjustments)}")


_trader = None

DASH_HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><title>BTC+AMZN Paper</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e0e0;font-family:'Segoe UI',system-ui,monospace}
.hdr{background:#141926;padding:14px 24px;border-bottom:1px solid #2a3040;display:flex;justify-content:space-between}
.hdr h1{font-size:16px;color:#f7931a}
.wrap{padding:16px 24px;max-width:1000px;margin:0 auto}
.gn{color:#00d4aa}.rd{color:#ff4d6a}.yl{color:#ffd700}.bl{color:#4dabf7}.gy{color:#555}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
.card{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:16px}
.card h3{font-size:13px;margin-bottom:8px}
.row{display:flex;justify-content:space-between;font-size:11px;padding:3px 0;border-bottom:1px solid #1a2030}
.row .k{color:#555}.row .v{font-weight:bold}
.section{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:16px;margin-bottom:14px}
.section h2{font-size:11px;color:#555;margin-bottom:8px;text-transform:uppercase}
table{width:100%;border-collapse:collapse;font-size:11px}
th{text-align:left;color:#555;padding:4px 6px;border-bottom:1px solid #2a3040}
td{padding:4px 6px;border-bottom:1px solid #1a2030}
</style></head><body>
<div class="hdr"><h1>BTC + AMZN Paper Trading</h1><div id="clock" style="font-size:11px;color:#555"></div></div>
<div class="wrap">
  <div class="cards" id="cards"></div>
  <div class="section"><h2>All Trades</h2>
    <table><thead><tr><th>Asset</th><th>Time</th><th>Entry</th><th>Exit</th><th>PnL%</th><th>Balance</th><th>Reason</th></tr></thead>
    <tbody id="trades"></tbody></table></div>
</div>
<script>
function fmt(v){return v>=0?'+'+v.toFixed(2):v.toFixed(2)}
async function refresh(){
  document.getElementById('clock').textContent=new Date().toLocaleString('ko-KR');
  try{const r=await fetch('/api/status?'+Date.now());if(!r.ok)return;
  const d=await r.json();let ch='';let allT=[];
  for(const[sym,a]of Object.entries(d)){
    const ret=((a.balance/10000-1)*100);const wr=a.total_trades>0?(a.wins/a.total_trades*100).toFixed(0)+'%':'--';
    ch+=`<div class="card"><h3>${sym}</h3>
      <div class="row"><span class="k">Price</span><span class="v bl">$${parseFloat(a.current_price||0).toLocaleString(undefined,{minimumFractionDigits:2})}</span></div>
      <div class="row"><span class="k">Balance</span><span class="v ${a.balance>=10000?'gn':'rd'}">$${Math.round(a.balance).toLocaleString()}</span></div>
      <div class="row"><span class="k">Return</span><span class="v ${ret>=0?'gn':'rd'}">${fmt(ret)}%</span></div>
      <div class="row"><span class="k">Position</span><span class="v">${a.position} ${a.current_leverage?a.current_leverage+'x':''}</span></div>
      <div class="row"><span class="k">Regime</span><span class="v yl">${a.regime||'--'}</span></div>
      <div class="row"><span class="k">Trades</span><span class="v">${a.total_trades} (${wr})</span></div>
      <div class="row"><span class="k">Leverage</span><span class="v">${(a.leverage||0).toFixed(1)}x</span></div>
    </div>`;
    for(const t of(a.trades||[]).slice(-10)){t._s=sym;allT.push(t)}}
  document.getElementById('cards').innerHTML=ch;
  allT.sort((a,b)=>(b.time||'').localeCompare(a.time||''));
  let th='';for(const t of allT.slice(0,20)){const p=t.pnl_pct||0;
    th+=`<tr><td class="yl">${t._s}</td><td>${(t.time||'').slice(5,16)}</td><td>$${parseFloat(t.entry||0).toFixed(2)}</td>
      <td>$${parseFloat(t.exit||0).toFixed(2)}</td><td class="${p>=0?'gn':'rd'}">${fmt(p)}%</td>
      <td>$${Math.round(t.balance||0).toLocaleString()}</td><td class="gy">${(t.reason||'').slice(0,30)}</td></tr>`;}
  if(!th)th='<tr><td colspan="7" class="gy" style="text-align:center">No trades yet</td></tr>';
  document.getElementById('trades').innerHTML=th;
  }catch(e){}}
refresh();setInterval(refresh,5000);
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/status"):
            data = {sym: asdict(s) for sym, s in _trader.states.items()} if _trader else {}
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(json.dumps(data, default=str).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASH_HTML.encode())
    def log_message(self, *a): pass


def main():
    global _trader
    print("="*60)
    print("  BTC + AMZN Paper Trading")
    print("  BTC: 4H MA200+RSI pullback | AMZN: Regime MA30/50")
    print(f"  Dashboard: http://localhost:{DASH_PORT}")
    print("="*60)
    _trader = MultiTrader()
    server = http.server.HTTPServer(("0.0.0.0", DASH_PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"  Dashboard: http://localhost:{DASH_PORT}\n  Running...\n")
    try:
        while True:
            try:
                _trader.cycle_btc()
                _trader.cycle_amzn()
            except KeyboardInterrupt: raise
            except Exception as e: print(f"  [error] {e}")
            time.sleep(CYCLE_SECONDS)
    except KeyboardInterrupt:
        for sym in _trader.states: _trader.save(sym)


if __name__ == "__main__":
    main()
