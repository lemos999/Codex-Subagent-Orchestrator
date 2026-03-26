"""Simulation dashboard — serves UI + runs simulation in background thread.

Single process: HTTP server (dashboard) + simulation thread.
Browser controls speed (1x/10x/100x/MAX), shows live price, PnL curves.

Usage:
    cd "Projects/Trading Value"
    PYTHONPATH=src py -3 scripts/sim_dashboard.py --start 2026-02-01 --days 14
    PYTHONPATH=src py -3 scripts/sim_dashboard.py --start 2026-01-01 --days 30 --port 8890

Then open http://localhost:8890
"""
from __future__ import annotations
import sys, json, time, argparse, threading
import http.server, urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
from trading_value.adapters.paper import PaperTrader
from trading_value.adapters.fvg_trader import FVGTrader
from trading_value.adapters.sim_exchange import SimClock, MockExchange

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "sim_1m.sqlite"

COINS = [
    {"symbol": "ETH/USDT:USDT", "short": "ETH"},
    {"symbol": "BTC/USDT:USDT", "short": "BTC"},
    {"symbol": "SOL/USDT:USDT", "short": "SOL"},
    {"symbol": "XRP/USDT:USDT", "short": "XRP"},
]

RL_MODELS = [
    {"name": "B Berserker", "path": str(DATA_DIR / "rl_model_b_3m")},
    {"name": "C Castle",    "path": str(DATA_DIR / "rl_model_c_b_1350k")},
    {"name": "F Fortress",  "path": str(DATA_DIR / "rl_model_c_v2_200k_validation")},
    {"name": "G Gladiator", "path": str(DATA_DIR / "rl_model_c_v2_r2_p30")},
]

ENSEMBLE_CONFIGS = [
    {"name": "D Diplomat", "m1": str(DATA_DIR / "rl_model_c_1100k"),
                           "m2": str(DATA_DIR / "rl_model_c_b_1350k")},
    {"name": "E Eagle",    "m1": str(DATA_DIR / "rl_model_c_1350_v1"),
                           "m2": str(DATA_DIR / "rl_model_c_1100k")},
]

FVG_ANCHORS = [
    {"name": "H FVG-KR", "anchor_utc": (0, 30)},
    {"name": "I FVG-PM", "anchor_utc": (8, 0)},
    {"name": "J FVG-US", "anchor_utc": (13, 30)},
]


class EnsembleTrader:
    def __init__(self, model1, model2):
        from sb3_contrib import RecurrentPPO
        self.m1 = RecurrentPPO.load(model1)
        self.m2 = RecurrentPPO.load(model2)
        self._ls1 = None; self._ls2 = None
        self._es = np.ones((1,), dtype=bool)

    def predict(self, obs, **kwargs):
        a1, self._ls1 = self.m1.predict(obs, state=self._ls1, episode_start=self._es, deterministic=True)
        a2, self._ls2 = self.m2.predict(obs, state=self._ls2, episode_start=self._es, deterministic=True)
        self._es = np.zeros((1,), dtype=bool)
        a1i, a2i = int(a1), int(a2)
        if a1i == a2i: return np.array(a1i), None
        if a1i == 0: return np.array(a2i), None
        if a2i == 0: return np.array(a1i), None
        return np.array(0), None


def _display_name(cs, name):
    return name if cs == "ETH" else f"{cs}-{name}"

def _sim_path(cs, letter, prefix, ext):
    c = "" if cs == "ETH" else f"{cs}_"
    return str(DATA_DIR / f"sim_{prefix}_{c}{letter}.{ext}")


def _clone_trader(src, symbol, state_file, log_file, exchange, time_func):
    t = PaperTrader.__new__(PaperTrader)
    t._now = time_func
    t.model = src.model; t._is_lstm = src._is_lstm
    if t._is_lstm:
        t._lstm_states = None; t._episode_start = np.ones((1,), dtype=bool)
    t.symbol = symbol
    t.symbol_short = symbol.replace("/", "").replace(":USDT", "")
    t.leverage = src.leverage; t.risk_pct = src.risk_pct
    t.commission_rate = src.commission_rate
    t.state_file = Path(state_file); t.log_file = Path(log_file)
    t.exchange = exchange; t.state = t._load_state()
    t.bars_30m = []; t.bars_1h = []; t.bars_4h = []; t._snapshot_cache = {}
    return t


# ══════════════════════════════════════════════════════════════
# Simulation Engine (runs in background thread)
# ══════════════════════════════════════════════════════════════

class SimEngine:
    def __init__(self, clock: SimClock, exchange: MockExchange):
        self.clock = clock
        self.exchange = exchange
        self.traders: list[tuple[str, object]] = []
        self.speed = 1.0       # seconds per sim-minute
        self.paused = False
        self.running = False
        self.status_data = {}  # latest status for dashboard
        self.pnl_history = []  # [(sim_time, total_pnl), ...]
        self._prices = {}      # coin -> current price
        self._lock = threading.Lock()

        self._build_models()

    def _build_models(self):
        eth_sym = "ETH/USDT:USDT"
        eth_traders = {}
        tf = self.clock.now

        for m in RL_MODELS:
            t = PaperTrader(model_path=m["path"], symbol=eth_sym,
                leverage=10, risk_pct=0.0035, commission_rate=0.0004,
                state_file=_sim_path("ETH", m["name"][0], "state", "json"),
                log_file=_sim_path("ETH", m["name"][0], "log", "jsonl"),
                time_func=tf)
            t.exchange = self.exchange
            eth_traders[m["name"]] = t
            self.traders.append((m["name"], t))

        for cfg in ENSEMBLE_CONFIGS:
            t = PaperTrader(model_path=cfg["m2"], symbol=eth_sym,
                leverage=10, risk_pct=0.0035, commission_rate=0.0004,
                state_file=_sim_path("ETH", cfg["name"][0], "state", "json"),
                log_file=_sim_path("ETH", cfg["name"][0], "log", "jsonl"),
                time_func=tf)
            t.model = EnsembleTrader(cfg["m1"], cfg["m2"])
            t._is_lstm = False; t.exchange = self.exchange
            eth_traders[cfg["name"]] = t
            self.traders.append((cfg["name"], t))

        for fvg in FVG_ANCHORS:
            h, mn = fvg["anchor_utc"]
            t = FVGTrader(h, mn, symbol=eth_sym, leverage=10,
                risk_pct=0.005, commission_rate=0.0004,
                state_file=_sim_path("ETH", fvg["name"][0], "state", "json"),
                log_file=_sim_path("ETH", fvg["name"][0], "log", "jsonl"),
                time_func=tf)
            t.exchange = self.exchange
            self.traders.append((fvg["name"], t))

        for coin in COINS[1:]:
            cs, sym = coin["short"], coin["symbol"]
            for m in RL_MODELS:
                clone = _clone_trader(eth_traders[m["name"]], sym,
                    _sim_path(cs, m["name"][0], "state", "json"),
                    _sim_path(cs, m["name"][0], "log", "jsonl"),
                    self.exchange, tf)
                self.traders.append((_display_name(cs, m["name"]), clone))
            for cfg in ENSEMBLE_CONFIGS:
                clone = _clone_trader(eth_traders[cfg["name"]], sym,
                    _sim_path(cs, cfg["name"][0], "state", "json"),
                    _sim_path(cs, cfg["name"][0], "log", "jsonl"),
                    self.exchange, tf)
                clone.model = eth_traders[cfg["name"]].model; clone._is_lstm = False
                self.traders.append((_display_name(cs, cfg["name"]), clone))
            for fvg in FVG_ANCHORS:
                h, mn = fvg["anchor_utc"]
                t = FVGTrader(h, mn, symbol=sym, leverage=10,
                    risk_pct=0.005, commission_rate=0.0004,
                    state_file=_sim_path(cs, fvg["name"][0], "state", "json"),
                    log_file=_sim_path(cs, fvg["name"][0], "log", "jsonl"),
                    time_func=tf)
                t.exchange = self.exchange
                self.traders.append((_display_name(cs, fvg["name"]), t))

        print(f"  [sim] {len(self.traders)} models ready")

    def _update_prices(self):
        for coin in COINS:
            try:
                ticker = self.exchange.fetch_ticker(coin["symbol"])
                self._prices[coin["short"]] = ticker["last"]
            except Exception:
                pass

    def _update_status(self):
        now = self.clock.now()
        self._update_prices()
        models = {}
        for name, t in self.traders:
            s = t.state
            coin = "ETH"
            for c in COINS[1:]:
                if name.startswith(c["short"] + "-"): coin = c["short"]; break
            models[name] = {
                "coin": coin, "balance": s.balance, "pnl": s.balance - 10000,
                "position": s.position, "entry_price": s.entry_price,
                "stop_price": s.stop_price, "position_qty": s.position_qty,
                "total_trades": s.total_trades, "wins": s.wins, "losses": s.losses,
                "peak_balance": s.peak_balance, "max_drawdown": s.max_drawdown,
                "target_price": getattr(t, '_fvg', {}).get("target_price", 0.0),
                "fvg_phase": getattr(t, '_fvg', {}).get("phase", ""),
                "pending_intent": s.pending_intent, "intent_price": s.intent_price,
            }

        total_pnl = sum(m["pnl"] for m in models.values())
        self.pnl_history.append((now.isoformat(), round(total_pnl, 2)))
        if len(self.pnl_history) > 5000:
            self.pnl_history = self.pnl_history[-5000:]

        with self._lock:
            self.status_data = {
                "timestamp": now.isoformat(),
                "sim_progress": round(self.clock.progress() * 100, 1),
                "speed": self.speed,
                "paused": self.paused,
                "prices": self._prices,
                "models": models,
                "pnl_history": self.pnl_history[-200:],
            }

    def run(self):
        # Clean old sim files
        for f in DATA_DIR.glob("sim_state_*.json"): f.unlink()
        for f in DATA_DIR.glob("sim_log_*.jsonl"): f.unlink()

        self.running = True
        print(f"  [sim] Running: {self.clock.start} -> {self.clock.end}")

        while self.running and self.clock.tick():
            if self.paused:
                time.sleep(0.1)
                continue

            if self.clock.is_30m_boundary():
                for _, t in self.traders:
                    try: t.run_once()
                    except Exception: pass
                self._update_status()

            for _, t in self.traders:
                try:
                    t.fast_check()
                    t._save_state()
                except Exception:
                    pass

            if self.speed > 0:
                time.sleep(self.speed)

        self.running = False
        self._update_status()
        print(f"\n  [sim] Complete!")


# ══════════════════════════════════════════════════════════════
# Dashboard HTML
# ══════════════════════════════════════════════════════════════

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Simulation Dashboard</title>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e0e0;font-family:'Segoe UI',system-ui,monospace;min-height:100vh}
.hdr{background:#141926;padding:12px 24px;border-bottom:1px solid #2a3040;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
.hdr h1{font-size:16px;color:#ff9800;letter-spacing:1px}
.hdr .meta{font-size:12px;color:#666;display:flex;gap:14px;align-items:center}
.hdr .price{font-size:16px;font-weight:bold;color:#fff}
.sim-badge{background:#ff980022;color:#ff9800;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:bold}
.wrap{padding:14px 24px;max-width:1400px;margin:0 auto}

/* Controls */
.controls{display:flex;gap:8px;margin-bottom:14px;align-items:center;flex-wrap:wrap}
.speed-btn{background:#1a2030;border:1px solid #2a3040;color:#888;padding:6px 16px;border-radius:5px;cursor:pointer;font-size:12px;font-weight:bold;font-family:inherit}
.speed-btn:hover{border-color:#ff980055;color:#ccc}
.speed-btn.active{background:#ff980022;border-color:#ff9800;color:#ff9800}
.pause-btn{background:#ff4d6a22;border:1px solid #ff4d6a;color:#ff4d6a;padding:6px 16px;border-radius:5px;cursor:pointer;font-size:12px;font-weight:bold;font-family:inherit}
.pause-btn.paused{background:#00d4aa22;border-color:#00d4aa;color:#00d4aa}

/* Progress */
.progress-bar{height:6px;background:#1a2030;border-radius:3px;margin-bottom:14px;overflow:hidden}
.progress-bar .fill{height:100%;background:linear-gradient(90deg,#ff9800,#ff6b35);border-radius:3px;transition:width .3s}
.sim-info{font-size:12px;color:#888;margin-bottom:10px;display:flex;justify-content:space-between}

/* Coin tabs */
.coin-tab{background:#1a2030;border:1px solid #2a3040;color:#888;padding:6px 16px;border-radius:5px;cursor:pointer;font-size:12px;font-weight:bold;font-family:inherit}
.coin-tab:hover{border-color:#ff980055;color:#ccc}
.coin-tab.active{background:#ff980022;border-color:#ff9800;color:#ff9800}

/* Chart */
#chartBox{background:#141926;border:1px solid #2a3040;border-radius:8px;margin-bottom:14px;overflow:hidden}

/* Cards */
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
.card{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:14px}
.card .name{font-size:13px;color:#888;margin-bottom:4px;display:flex;justify-content:space-between}
.card .name .tag{font-size:10px;padding:2px 6px;border-radius:3px;font-weight:bold}
.tag-long{background:#00d4aa22;color:#00d4aa}
.tag-short{background:#ff4d6a22;color:#ff4d6a}
.tag-flat{background:#66666622;color:#888}
.card .pnl{font-size:28px;font-weight:bold;margin:6px 0}
.gn{color:#00d4aa}.rd{color:#ff4d6a}.gy{color:#555}
.card .stats{display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:11px;color:#999}
.card .stats .val{color:#ddd;font-weight:600}

/* PnL curve */
#pnlCurveBox{background:#141926;border:1px solid #2a3040;border-radius:8px;margin-bottom:14px;overflow:hidden}
</style>
</head>
<body>

<div class="hdr">
  <div style="display:flex;align-items:center;gap:12px">
    <h1>SIMULATION</h1>
    <span class="sim-badge">REPLAY MODE</span>
  </div>
  <div class="meta">
    <span class="price" id="coinPrice">$--</span>
    <span id="simTime" style="color:#ff9800">--</span>
    <span id="clock" style="color:#fff;font-size:13px;font-weight:bold"></span>
  </div>
</div>

<div class="wrap">
  <!-- Progress -->
  <div class="sim-info">
    <span id="simRange">--</span>
    <span id="simPct">0%</span>
  </div>
  <div class="progress-bar"><div class="fill" id="progressFill" style="width:0%"></div></div>

  <!-- Controls -->
  <div class="controls">
    <button class="speed-btn active" data-speed="1">1x</button>
    <button class="speed-btn" data-speed="0.1">10x</button>
    <button class="speed-btn" data-speed="0.01">100x</button>
    <button class="speed-btn" data-speed="0">MAX</button>
    <button class="pause-btn" id="pauseBtn">PAUSE</button>
    <div style="flex:1"></div>
    <button class="coin-tab active" data-coin="ETH">ETH</button>
    <button class="coin-tab" data-coin="BTC">BTC</button>
    <button class="coin-tab" data-coin="SOL">SOL</button>
    <button class="coin-tab" data-coin="XRP">XRP</button>
    <button class="coin-tab" data-coin="ALL">ALL</button>
  </div>

  <!-- Chart -->
  <div id="chartBox"><div id="chart" style="height:350px"></div></div>

  <!-- PnL Curve -->
  <div id="pnlCurveBox"><div id="pnlCurve" style="height:150px"></div></div>

  <!-- Model Cards -->
  <div class="grid" id="cards"></div>
</div>

<script>
let selectedCoin = 'ETH';
let lastData = null;

// Speed buttons
document.querySelectorAll('.speed-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    fetch('/api/speed?v=' + btn.dataset.speed);
  });
});

// Pause button
document.getElementById('pauseBtn').addEventListener('click', () => {
  fetch('/api/pause').then(r => r.json()).then(d => {
    const btn = document.getElementById('pauseBtn');
    btn.textContent = d.paused ? 'RESUME' : 'PAUSE';
    btn.classList.toggle('paused', d.paused);
  });
});

// Coin tabs
document.querySelectorAll('.coin-tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.coin-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedCoin = btn.dataset.coin;
    if (lastData) render(lastData);
  });
});

// Chart
const chartEl = document.getElementById('chart');
const chart = LightweightCharts.createChart(chartEl, {
  layout:{background:{color:'#141926'},textColor:'#888'},
  grid:{vertLines:{color:'#1a2030'},horzLines:{color:'#1a2030'}},
  crosshair:{mode:0},
  timeScale:{timeVisible:true,secondsVisible:false,borderColor:'#2a3040'},
  rightPriceScale:{borderColor:'#2a3040'},
});
const candleSeries = chart.addCandlestickSeries({
  upColor:'#00d4aa',downColor:'#ff4d6a',
  borderUpColor:'#00d4aa',borderDownColor:'#ff4d6a',
  wickUpColor:'#00d4aa88',wickDownColor:'#ff4d6a88',
});

// PnL curve
const pnlEl = document.getElementById('pnlCurve');
const pnlChart = LightweightCharts.createChart(pnlEl, {
  layout:{background:{color:'#141926'},textColor:'#888'},
  grid:{vertLines:{color:'#1a2030'},horzLines:{color:'#1a2030'}},
  timeScale:{timeVisible:true,borderColor:'#2a3040'},
  rightPriceScale:{borderColor:'#2a3040'},
});
const pnlSeries = pnlChart.addLineSeries({color:'#ff9800',lineWidth:2});

function posTag(pos) {
  if (pos===1) return '<span class="tag tag-long">LONG</span>';
  if (pos===-1) return '<span class="tag tag-short">SHORT</span>';
  return '<span class="tag tag-flat">FLAT</span>';
}
function pnlClass(v){return v>0?'gn':v<0?'rd':'gy'}
function fmt(v){return v>=0?'+$'+v.toLocaleString('en',{maximumFractionDigits:0}):'-$'+Math.abs(v).toLocaleString('en',{maximumFractionDigits:0})}

function render(data) {
  lastData = data;

  // Progress
  document.getElementById('progressFill').style.width = data.sim_progress + '%';
  document.getElementById('simPct').textContent = data.sim_progress + '%';

  const simDt = new Date(data.timestamp);
  document.getElementById('simTime').textContent = simDt.toLocaleString('ko-KR',{timeZone:'Asia/Seoul'});

  // Price
  const coin = selectedCoin === 'ALL' ? 'ETH' : selectedCoin;
  const price = data.prices?.[coin] || 0;
  document.getElementById('coinPrice').textContent = coin + ' $' + price.toLocaleString('en',{maximumFractionDigits:2});

  // Filter models by coin
  const models = {};
  for (const name in data.models) {
    const m = data.models[name];
    if (selectedCoin === 'ALL' || (m.coin || 'ETH') === selectedCoin) {
      models[name] = m;
    }
  }

  // Cards
  let cards = '';
  const COLORS = {'B':'#ff6b35','C':'#4ecdc4','D':'#95e1d3','E':'#f38181','F':'#00d4aa','G':'#ffd700','H':'#7b68ee','I':'#ff69b4','J':'#1e90ff'};
  for (const name in models) {
    const m = models[name];
    const pnl = m.pnl;
    const letter = name.replace(/^[A-Z]{2,3}-/,'')[0];
    const clr = COLORS[letter] || '#888';
    const wr = m.total_trades > 0 ? (m.wins/m.total_trades*100).toFixed(0)+'%' : '-';
    cards += `<div class="card" style="border-left:3px solid ${clr}">
      <div class="name">${name} ${posTag(m.position)}</div>
      <div class="pnl ${pnlClass(pnl)}">${fmt(pnl)}</div>
      <div class="stats">
        <div>Trades <div class="val">${m.total_trades} (${m.wins}W/${m.losses}L)</div></div>
        <div>WinRate <div class="val">${wr}</div></div>
        ${m.position!==0?`<div>Entry <div class="val">$${m.entry_price.toLocaleString('en',{maximumFractionDigits:2})}</div></div>
        <div>Stop <div class="val">$${m.stop_price.toLocaleString('en',{maximumFractionDigits:2})}</div></div>`:''}
        ${m.fvg_phase?`<div style="grid-column:1/-1;color:#7b68ee;font-size:10px">FVG: ${m.fvg_phase}</div>`:''}
        ${m.pending_intent?`<div style="grid-column:1/-1;color:#ffd700;font-size:10px">Intent: ${m.pending_intent}</div>`:''}
      </div>
    </div>`;
  }
  document.getElementById('cards').innerHTML = cards;

  // PnL curve
  if (data.pnl_history && data.pnl_history.length > 0) {
    const pnlData = data.pnl_history.map(([t,v]) => ({
      time: Math.floor(new Date(t).getTime()/1000),
      value: v,
    }));
    pnlSeries.setData(pnlData);
  }
}

// Candle fetch from sim exchange
async function fetchCandles() {
  try {
    const coin = selectedCoin === 'ALL' ? 'ETH' : selectedCoin;
    const r = await fetch('/api/candles?coin=' + coin);
    if (!r.ok) return;
    const candles = await r.json();
    if (candles.length > 0) candleSeries.setData(candles);
  } catch(e) {}
}

async function refresh() {
  try {
    const r = await fetch('/api/sim_status?' + Date.now());
    if (r.ok) {
      const data = await r.json();
      render(data);
    }
  } catch(e) {}
}

refresh();
fetchCandles();
setInterval(refresh, 1000);
setInterval(fetchCandles, 5000);
window.addEventListener('resize', () => {
  chart.applyOptions({width:chartEl.clientWidth});
  pnlChart.applyOptions({width:pnlEl.clientWidth});
});
</script>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════
# HTTP Handler
# ══════════════════════════════════════════════════════════════

sim_engine: SimEngine = None  # set in main()


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/sim_status"):
            self._json_response(sim_engine.status_data)
        elif self.path.startswith("/api/speed"):
            v = float(self.path.split("v=")[1].split("&")[0])
            sim_engine.speed = v
            self._json_response({"speed": v})
        elif self.path.startswith("/api/pause"):
            sim_engine.paused = not sim_engine.paused
            self._json_response({"paused": sim_engine.paused})
        elif self.path.startswith("/api/candles"):
            self._serve_candles()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())

    def _json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _serve_candles(self):
        try:
            coin = "ETH"
            if "coin=" in self.path:
                coin = self.path.split("coin=")[1].split("&")[0]
            sym_map = {"ETH": "ETH/USDT:USDT", "BTC": "BTC/USDT:USDT",
                       "SOL": "SOL/USDT:USDT", "XRP": "XRP/USDT:USDT"}
            sym = sym_map.get(coin, "ETH/USDT:USDT")
            ohlcv = sim_engine.exchange.fetch_ohlcv(sym, "30m", limit=200)
            candles = [{"time": c[0]//1000, "open": c[1], "high": c[2],
                        "low": c[3], "close": c[4]} for c in ohlcv]
            self._json_response(candles)
        except Exception:
            self._json_response([])

    def log_message(self, *args):
        pass


def main():
    global sim_engine

    parser = argparse.ArgumentParser(description="Simulation Dashboard")
    parser.add_argument("--start", default="2026-02-01 00:00:00")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--port", type=int, default=8890)
    args = parser.parse_args()

    end_dt = datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S") + timedelta(days=args.days)

    print(f"Simulation Dashboard")
    print(f"  Period: {args.start} -> {end_dt.strftime('%Y-%m-%d')}")
    print(f"  Port: {args.port}")
    print(f"  Loading data...")

    clock = SimClock(start=args.start, end=end_dt.strftime("%Y-%m-%d %H:%M:%S"))
    exchange = MockExchange(clock, db_path=str(DB_PATH))

    print(f"  Loading models...")
    sim_engine = SimEngine(clock, exchange)

    # Start sim in background thread
    sim_thread = threading.Thread(target=sim_engine.run, daemon=True)
    sim_thread.start()

    # Start HTTP server
    server = http.server.HTTPServer(("0.0.0.0", args.port), Handler)
    print(f"\n  Dashboard: http://localhost:{args.port}")
    print(f"  Speed controls: 1x / 10x / 100x / MAX")
    print(f"  Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sim_engine.running = False
        print("\nStopped.")


if __name__ == "__main__":
    main()
