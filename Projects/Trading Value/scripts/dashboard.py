"""Real-time paper trading dashboard.

Serves an HTML dashboard that auto-refreshes with live trading data.
Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/dashboard.py
Then open http://localhost:8888
"""
from __future__ import annotations

import json
import http.server
import threading
import time
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

BASE = Path(__file__).resolve().parent.parent
STATE_FILE = BASE / "data" / "paper_state.json"
LOG_FILE = BASE / "data" / "paper_log.jsonl"
PORT = 8888

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Trading Value - Live Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e0e0;font-family:'Segoe UI',monospace}
.hdr{background:#141926;padding:12px 20px;border-bottom:1px solid #2a3040;display:flex;justify-content:space-between;align-items:center}
.hdr h1{font-size:18px;color:#00d4aa}
.hdr .st{font-size:12px;color:#888}
.g{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;padding:12px 20px}
.c{background:#141926;border:1px solid #2a3040;border-radius:6px;padding:12px}
.c h3{color:#888;font-size:11px;text-transform:uppercase;margin-bottom:6px}
.bn{font-size:28px;font-weight:bold}
.gn{color:#00d4aa}.rd{color:#ff4d6a}.yl{color:#ffd700}.gy{color:#666}
.r{display:flex;justify-content:space-between;margin:3px 0;font-size:13px}
.lb{color:#888}
.full{grid-column:1/-1}
.half{grid-column:span 2}
canvas{display:block;background:#0d1117;border-radius:4px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;color:#888;padding:6px 4px;border-bottom:1px solid #2a3040}
td{padding:5px 4px;border-bottom:1px solid #1a1f2e}
.pl{display:inline-block;padding:2px 6px;border-radius:3px;font-size:10px;font-weight:bold}
.pl-l{background:#00d4aa22;color:#00d4aa;border:1px solid #00d4aa44}
.pl-s{background:#ff4d6a22;color:#ff4d6a;border:1px solid #ff4d6a44}
.pl-f{background:#88888822;color:#888;border:1px solid #88888844}
.ll{font-size:10px;padding:2px 0;border-bottom:1px solid #1a1f2e;font-family:monospace}
.trk{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:0 20px 12px}
.trk-card{background:#141926;border:1px solid #2a3040;border-radius:6px;padding:12px}
.trk-card h3 span{font-size:14px}
</style>
</head>
<body>
<div class="hdr">
  <h1>Trading Value</h1>
  <div class="st">
    <span id="eth-hdr" class="yl">ETH --</span> |
    <span id="tm">--</span> | 1s refresh
  </div>
</div>
<div class="g">
  <div class="c"><h3>ETH/USDT</h3>
    <div class="bn yl" id="ep">--</div>
    <div class="r"><span class="lb">24h</span><span id="ch">--</span></div>
    <div class="r"><span class="lb">High</span><span id="hi">--</span></div>
    <div class="r"><span class="lb">Low</span><span id="lo">--</span></div>
  </div>
  <div class="c"><h3>Balance (RL v4)</h3>
    <div class="bn" id="bal">$10,000</div>
    <div class="r"><span class="lb">PnL</span><span id="pnl">$0</span></div>
    <div class="r"><span class="lb">Peak</span><span id="pk">$10,000</span></div>
    <div class="r"><span class="lb">Max DD</span><span id="dd">$0</span></div>
  </div>
  <div class="c"><h3>Position (RL v4)</h3>
    <div class="bn" id="pos"><span class="pl pl-f">FLAT</span></div>
    <div class="r"><span class="lb">Entry</span><span id="en">-</span></div>
    <div class="r"><span class="lb">Stop</span><span id="sp">-</span></div>
    <div class="r"><span class="lb">Stop Dist</span><span id="sd" class="gy">-</span></div>
  </div>
  <div class="c"><h3>Stats</h3>
    <div class="bn" id="wr">0%</div>
    <div class="r"><span class="lb">Trades</span><span id="tt">0</span></div>
    <div class="r"><span class="lb">W / L</span><span><span class="gn" id="wi">0</span> / <span class="rd" id="ls">0</span></span></div>
    <div class="r"><span class="lb">Lev</span><span>10x</span></div>
  </div>
  <div class="c full"><h3>ETH/USDT 1m Candles</h3>
    <canvas id="cc" height="320"></canvas>
  </div>
</div>

<!-- Track comparison -->
<div class="trk">
  <div class="trk-card">
    <h3>Track B — <span class="gn">RL v4</span> (30m judgment + 1m guard)</h3>
    <div class="r"><span class="lb">Position</span><span id="tb-pos">-</span></div>
    <div class="r"><span class="lb">PnL</span><span id="tb-pnl">-</span></div>
    <div class="r"><span class="lb">Trades</span><span id="tb-trades">-</span></div>
    <div class="r"><span class="lb">Action</span><span id="tb-action">-</span></div>
  </div>
  <div class="trk-card">
    <h3>Track A — <span class="yl">Rule-based</span> (optimized params)</h3>
    <div class="r"><span class="lb">Balance</span><span id="ta-bal">$10,000</span></div>
    <div class="r"><span class="lb">PnL</span><span id="ta-pnl">$0</span></div>
    <div class="r"><span class="lb">Position</span><span id="ta-pos">FLAT</span></div>
    <div class="r"><span class="lb">W / L</span><span id="ta-wl">0 / 0</span></div>
    <div class="r"><span class="lb">Regime</span><span id="ta-regime">-</span></div>
    <div class="r"><span class="lb">Mode</span><span id="ta-mode">-</span></div>
    <div class="r"><span class="lb">Signal</span><span id="ta-signal" class="gy">-</span></div>
    <div class="r"><span class="lb">Score</span><span id="ta-score" class="yl">-</span></div>
    <div class="r"><span class="lb">Cloud</span><span id="ta-cloud" class="gy" style="font-size:10px">-</span></div>
    <div class="r"><span class="lb">Donchian</span><span id="ta-dc" class="gy" style="font-size:10px">-</span></div>
  </div>
</div>

<div class="g">
  <div class="c full"><h3>PnL Curve</h3>
    <canvas id="pc" height="200"></canvas>
  </div>
  <div class="c half"><h3>Recent Trades</h3>
    <table><thead><tr><th>Time</th><th>Side</th><th>Entry</th><th>Exit</th><th>PnL</th><th>Reason</th></tr></thead>
    <tbody id="tb"></tbody></table>
  </div>
  <div class="c half"><h3>Live Log</h3>
    <div id="lg" style="max-height:250px;overflow-y:auto"></div>
  </div>
</div>

<script>
let S={};
async function fetchState(){
  try{const r=await fetch('/api/state');S=await r.json();renderState()}catch(e){}
}
function renderState(){
  const p=S.balance-10000,pc=p>=0?'gn':'rd';
  el('bal').className='bn '+pc;
  el('bal').textContent='$'+S.balance.toLocaleString(undefined,{maximumFractionDigits:0});
  el('pnl').className=pc;el('pnl').textContent=(p>=0?'+':'')+p.toFixed(0);
  el('pk').textContent='$'+S.peak_balance.toLocaleString(undefined,{maximumFractionDigits:0});
  el('dd').textContent='$'+S.max_drawdown.toFixed(0);
  const pd=el('pos');
  pd.innerHTML=S.position===1?'<span class="pl pl-l">LONG</span>':S.position===-1?'<span class="pl pl-s">SHORT</span>':'<span class="pl pl-f">FLAT</span>';
  el('en').textContent=S.position?'$'+S.entry_price.toFixed(2):'-';
  el('sp').textContent=S.position?'$'+S.stop_price.toFixed(2):'-';
  const w=S.total_trades>0?(S.wins/S.total_trades*100).toFixed(0)+'%':'0%';
  el('wr').textContent=w;el('tt').textContent=S.total_trades;el('wi').textContent=S.wins;el('ls').textContent=S.losses;
  // Track B panel
  el('tb-pos').innerHTML=S.position===1?'<span class="gn">LONG</span>':S.position===-1?'<span class="rd">SHORT</span>':'FLAT';
  el('tb-pnl').className=pc;el('tb-pnl').textContent='$'+(p>=0?'+':'')+p.toFixed(0);
  el('tb-trades').textContent=S.total_trades;
  // Track A panel
  const ta=S.track_a||{};
  const taPnl=(ta.balance||10000)-10000;
  const taPc=taPnl>=0?'gn':'rd';
  el('ta-bal').className=taPc;el('ta-bal').textContent='$'+(ta.balance||10000).toLocaleString(undefined,{maximumFractionDigits:0});
  el('ta-pnl').className=taPc;el('ta-pnl').textContent='$'+(taPnl>=0?'+':'')+taPnl.toFixed(0);
  el('ta-pos').innerHTML=ta.position===1?'<span class="gn">LONG @ $'+(ta.entry_price||0).toFixed(0)+'</span>':ta.position===-1?'<span class="rd">SHORT @ $'+(ta.entry_price||0).toFixed(0)+'</span>':'<span class="gy">FLAT</span>';
  el('ta-wl').innerHTML='<span class="gn">'+(ta.wins||0)+'</span> / <span class="rd">'+(ta.losses||0)+'</span>';
  const regimeColor=ta.regime==='HTF_BULLISH'?'gn':ta.regime==='HTF_BEARISH'?'rd':'gy';
  el('ta-regime').innerHTML=`<span class="${regimeColor}">${ta.regime||'-'}</span> / ${ta.h1||'-'} / ${ta.m30||'-'}`;
  const modeColor=ta.mode==='MODE_NO_TRADE'?'gy':ta.mode&&ta.mode.includes('LONG')?'gn':'rd';
  el('ta-mode').innerHTML=`<span class="${modeColor}">${(ta.mode||'-').replace('MODE_','')}</span>`;
  const sigColor=ta.signal==='NO_TRADE'||ta.signal==='NONE'?'gy':ta.signal&&ta.signal.includes('LONG')?'gn':ta.signal&&ta.signal.includes('SHORT')?'rd':'yl';
  el('ta-signal').innerHTML=`<span class="${sigColor}">${ta.signal||'-'}</span>`;
  const sc=ta.score||0;
  el('ta-score').textContent=sc>0?sc+'/100':'-';
  el('ta-score').className=sc>=55?'gn':sc>=30?'yl':'rd';
  el('ta-cloud').textContent=ta.cloud_info||'-';
  el('ta-dc').textContent=ta.donchian||'-';
  // Trades table
  const tbody=el('tb');tbody.innerHTML='';
  for(const t of (S.trades||[]).slice(-10).reverse()){
    const pn=t.pnl>=0?`<span class="gn">+${t.pnl.toFixed(0)}</span>`:`<span class="rd">${t.pnl.toFixed(0)}</span>`;
    const s=t.side==='LONG'?'<span class="pl pl-l">L</span>':'<span class="pl pl-s">S</span>';
    tbody.innerHTML+=`<tr><td>${(t.exit_time||'').slice(5,16)}</td><td>${s}</td><td>${t.entry_price.toFixed(0)}</td><td>${t.exit_price.toFixed(0)}</td><td>${pn}</td><td>${t.exit_reason}</td></tr>`;
  }
  drawPnl(S.trades||[]);
  el('tm').textContent=new Date().toLocaleTimeString();
}
async function fetchPrice(){
  try{
    const r=await fetch('/api/price'),d=await r.json();
    if(d.error)return;
    el('ep').textContent='$'+d.price.toLocaleString(undefined,{maximumFractionDigits:2});
    el('eth-hdr').textContent='ETH $'+d.price.toFixed(2);
    const c=d.change_pct||0;
    el('ch').textContent=(c>=0?'+':'')+c.toFixed(2)+'%';el('ch').className=c>=0?'gn':'rd';
    if(d.high_24h)el('hi').textContent='$'+d.high_24h.toFixed(2);
    if(d.low_24h)el('lo').textContent='$'+d.low_24h.toFixed(2);
    // Stop dist
    if(S.position&&S.stop_price){
      const dist=Math.abs(d.price-S.stop_price),pct=(dist/d.price*100).toFixed(2);
      const danger=(S.position===1&&d.price<S.stop_price*1.01)||(S.position===-1&&d.price>S.stop_price*0.99);
      el('sd').textContent='$'+dist.toFixed(2)+' ('+pct+'%)';el('sd').className=danger?'rd':'gn';
    }else{el('sd').textContent='-';el('sd').className='gy'}
    // Candle chart
    if(d.candles&&d.candles.length>0)drawCandles(d.candles,d.price);
  }catch(e){}
}
function drawCandles(candles,price){
  const cv=el('cc'),ctx=cv.getContext('2d');
  cv.width=cv.parentElement.clientWidth;const W=cv.width,H=cv.height;
  ctx.fillStyle='#0d1117';ctx.fillRect(0,0,W,H);
  let mn=1e9,mx=0;
  for(const c of candles){if(c.l<mn)mn=c.l;if(c.h>mx)mx=c.h}
  mn*=0.9999;mx*=1.0001;const rng=mx-mn||1;
  const toY=v=>H*0.05+(H*0.9)*(1-(v-mn)/rng);
  const pad=60,cw=Math.max(2,(W-pad-10)/candles.length-2);
  // Grid
  ctx.strokeStyle='#1a1f2e';ctx.lineWidth=1;
  for(let i=0;i<5;i++){const y=H*0.05+(H*0.9)*i/4;ctx.beginPath();ctx.moveTo(pad,y);ctx.lineTo(W-5,y);ctx.stroke();
    ctx.fillStyle='#555';ctx.font='10px monospace';ctx.fillText('$'+(mx-rng*i/4).toFixed(1),2,y+3)}
  // Candles
  for(let i=0;i<candles.length;i++){
    const c=candles[i],x=pad+(W-pad-10)*i/candles.length+1;
    const up=c.c>=c.o,col=up?'#00d4aa':'#ff4d6a';
    // Wick
    ctx.strokeStyle=col;ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(x+cw/2,toY(c.h));ctx.lineTo(x+cw/2,toY(c.l));ctx.stroke();
    // Body
    const bTop=toY(Math.max(c.o,c.c)),bBot=toY(Math.min(c.o,c.c));
    ctx.fillStyle=up?'#00d4aa':'#ff4d6a';
    ctx.fillRect(x,bTop,cw,Math.max(1,bBot-bTop));
  }
  // Entry line
  if(S.position&&S.entry_price){
    const ey=toY(S.entry_price);
    if(ey>0&&ey<H){ctx.strokeStyle='#ffd700';ctx.lineWidth=1;ctx.setLineDash([5,4]);
      ctx.beginPath();ctx.moveTo(pad,ey);ctx.lineTo(W-5,ey);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle='#ffd700';ctx.font='11px monospace';ctx.fillText('Entry '+S.entry_price.toFixed(2),W-130,ey-4)}}
  // Stop line
  if(S.position&&S.stop_price){
    const sy=toY(S.stop_price);
    if(sy>0&&sy<H){ctx.strokeStyle='#ff4d6a88';ctx.lineWidth=1;ctx.setLineDash([3,3]);
      ctx.beginPath();ctx.moveTo(pad,sy);ctx.lineTo(W-5,sy);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle='#ff4d6a';ctx.font='11px monospace';ctx.fillText('Stop '+S.stop_price.toFixed(2),W-130,sy-4)}}
  // Current price
  ctx.fillStyle='#fff';ctx.font='bold 13px monospace';ctx.fillText('$'+price.toFixed(2),W-90,16);
}
function drawPnl(trades){
  const cv=el('pc'),ctx=cv.getContext('2d');
  cv.width=cv.parentElement.clientWidth;
  cv.height=220;
  const W=cv.width,H=cv.height;
  const T=15,B=25,L=65,R=90; // margins: top,bottom,left,right
  const cW=W-L-R,cH=H-T-B; // chart area

  ctx.fillStyle='#0d1117';ctx.fillRect(0,0,W,H);

  if(trades.length<1){
    ctx.fillStyle='#444';ctx.font='13px monospace';
    ctx.fillText('Waiting for trades...',W/2-70,H/2);return;
  }

  let cp=[0];for(const t of trades)cp.push(cp[cp.length-1]+t.pnl);
  const dataMin=Math.min(...cp);
  const dataMax=Math.max(...cp);
  const margin=(dataMax-dataMin)*0.15||10;
  const mn=dataMin-margin,mx=dataMax+margin,rng=mx-mn||1;

  const toX=i=>L+cW*i/(cp.length-1);
  const toY=v=>T+cH*(1-(v-mn)/rng);

  // Clip to chart area
  ctx.save();
  ctx.beginPath();ctx.rect(L,T,cW,cH);ctx.clip();

  // Zero line
  const zy=toY(0);
  ctx.strokeStyle='#ffffff33';ctx.lineWidth=1;
  ctx.beginPath();ctx.moveTo(L,zy);ctx.lineTo(L+cW,zy);ctx.stroke();

  // PnL line
  const up=cp[cp.length-1]>=0;
  ctx.beginPath();ctx.strokeStyle=up?'#00d4aa':'#ff4d6a';ctx.lineWidth=2;
  for(let i=0;i<cp.length;i++){
    const x=toX(i),y=toY(cp[i]);
    i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
  }
  ctx.stroke();

  // Fill under to zero
  ctx.lineTo(toX(cp.length-1),zy);
  ctx.lineTo(toX(0),zy);
  ctx.closePath();ctx.fillStyle=up?'#00d4aa12':'#ff4d6a12';ctx.fill();

  // Dot on last
  const lastY=toY(cp[cp.length-1]);
  ctx.beginPath();ctx.arc(toX(cp.length-1),lastY,4,0,Math.PI*2);
  ctx.fillStyle=up?'#00d4aa':'#ff4d6a';ctx.fill();

  ctx.restore(); // unclip

  // Y-axis labels (outside clip)
  ctx.fillStyle='#666';ctx.font='10px monospace';
  for(let i=0;i<5;i++){
    const v=mx-rng*i/4;
    const y=T+cH*i/4;
    ctx.strokeStyle='#1a1f2e';ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(L+cW,y);ctx.stroke();
    const label=(v>=0?'+':'')+v.toFixed(0);
    ctx.fillText('$'+label,3,y+4);
  }

  // Zero label
  if(zy>T&&zy<T+cH){
    ctx.fillStyle='#888';ctx.fillText('$0',L-22,zy+4);
  }

  // Current PnL (right side)
  const lastPnl=cp[cp.length-1];
  ctx.fillStyle=up?'#00d4aa':'#ff4d6a';ctx.font='bold 12px monospace';
  const pnlLabel='$'+(lastPnl>=0?'+':'')+lastPnl.toFixed(0);
  const labelY=Math.max(T+12,Math.min(T+cH-5,lastY+4));
  ctx.fillText(pnlLabel,L+cW+8,labelY);

  // Bottom stats
  const wins=trades.filter(t=>t.pnl>0).length;
  const wr=trades.length>0?(wins/trades.length*100).toFixed(0)+'%':'0%';
  ctx.fillStyle='#666';ctx.font='10px monospace';
  ctx.fillText(trades.length+' trades | WR '+wr+' | High $'+dataMax.toFixed(0)+' | Low $'+dataMin.toFixed(0),L,H-5);
}
async function fetchLog(){
  try{const r=await fetch('/api/log'),lines=await r.json(),c=el('lg');c.innerHTML='';
    for(const l of lines.slice(-20).reverse()){const d=document.createElement('div');d.className='ll';
      const t=(l.time||'').slice(11,19),e=l.event||'',cl=e==='OPEN'?'#00d4aa':e==='CLOSE'?'#ff4d6a':e==='TRAIL'?'#ffd700':'#666';
      d.innerHTML=`<span style="color:#444">${t}</span> <span style="color:${cl}">${e}</span> ${JSON.stringify(l).slice(0,70)}`;
      c.appendChild(d)}}catch(e){}
}
function el(id){return document.getElementById(id)}
fetchState();fetchPrice();fetchLog();
setInterval(fetchState,1000);
setInterval(fetchPrice,2000);
setInterval(fetchLog,5000);
</script>
</body>
</html>"""


# Global ccxt instance (reuse connection)
import ccxt as _ccxt
_exchange = _ccxt.binance({"options": {"defaultType": "future"}})
_price_cache = {"data": None, "ts": 0}


def _fetch_price_cached():
    """Fetch price with 2s cache to avoid rate limiting."""
    import time as _t
    now = _t.time()
    if _price_cache["data"] and now - _price_cache["ts"] < 2:
        return _price_cache["data"]
    try:
        ticker = _exchange.fetch_ticker("ETH/USDT:USDT")
        ohlcv_1m = _exchange.fetch_ohlcv("ETH/USDT:USDT", "1m", limit=60)
        candles = [{"t": c[0], "o": c[1], "h": c[2], "l": c[3], "c": c[4], "v": c[5]} for c in ohlcv_1m]
        data = {
            "price": ticker["last"],
            "high_24h": ticker.get("high", 0),
            "low_24h": ticker.get("low", 0),
            "change_pct": ticker.get("percentage", 0),
            "volume_24h": ticker.get("quoteVolume", 0),
            "candles": candles,
            "prices_1m": [c[4] for c in ohlcv_1m],
        }
        _price_cache["data"] = data
        _price_cache["ts"] = now
        return data
    except Exception as e:
        return {"error": str(e), "price": 0, "candles": [], "prices_1m": []}


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]  # strip query string
        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif path == "/api/state":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                with open(STATE_FILE) as f:
                    data = f.read()
            except FileNotFoundError:
                data = json.dumps({"balance": 10000, "position": 0, "entry_price": 0,
                    "stop_price": 0, "position_qty": 0, "bars_held": 0,
                    "total_trades": 0, "wins": 0, "losses": 0,
                    "peak_balance": 10000, "max_drawdown": 0, "trades": []})
            self.wfile.write(data.encode())

        elif path == "/api/price":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = _fetch_price_cached()
            self.wfile.write(json.dumps(data).encode())

        elif path == "/api/log":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            lines = []
            try:
                with open(LOG_FILE) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                lines.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
            except FileNotFoundError:
                pass
            self.wfile.write(json.dumps(lines[-50:]).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress request logging


def main():
    server = http.server.HTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print(f"Dashboard running at http://localhost:{PORT}")
    print(f"State file: {STATE_FILE}")
    print(f"Log file: {LOG_FILE}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


if __name__ == "__main__":
    main()
