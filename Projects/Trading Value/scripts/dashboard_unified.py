"""Unified Paper Trading Dashboard.

Proxies and displays all running models in one view.
- Tournament (port 8895) — 5,000 variant tournament
- V2 Prediction Engine (port 8897) — 3-rule prediction model

Usage:
    py -3.12 scripts/dashboard_unified.py [--port 8900]

Dashboard:
    http://localhost:8900
"""
from __future__ import annotations

import argparse
import http.server
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

PORT = 8900

# Model endpoints to proxy
MODELS = {
    "tournament": {"port": 8895, "name": "Tournament (5K variants)",       "color": "#ff8800"},
    "v2":         {"port": 8897, "name": "V2 Prediction Engine",           "color": "#00ccff"},
    "v3":         {"port": 8898, "name": "V3 Parker Brooks + Self-Learn",  "color": "#aa66ff"},
}


def fetch_model_state(port: int) -> dict | None:
    try:
        req = urllib.request.Request(
            f"http://localhost:{port}/api/state",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/":
            self._serve_html()
        elif self.path.startswith("/api/"):
            self._serve_api()
        else:
            self.send_error(404)

    def _serve_html(self):
        body = DASHBOARD_HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _serve_api(self):
        # /api/all — aggregate all models
        # /api/tournament — proxy to 8895
        # /api/v2 — proxy to 8897
        key = self.path.split("/api/")[-1].split("?")[0]

        if key == "all":
            result = {}
            for model_id, info in MODELS.items():
                state = fetch_model_state(info["port"])
                result[model_id] = {
                    "name": info["name"],
                    "color": info["color"],
                    "online": state is not None,
                    "state": state or {},
                }
            data = json.dumps(result)
        elif key in MODELS:
            state = fetch_model_state(MODELS[key]["port"])
            data = json.dumps(state or {"error": "offline"})
        else:
            self.send_error(404)
            return

        body = data.encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


DASHBOARD_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Trading Value — Unified Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Courier New',monospace;background:#08080c;color:#ccc;min-height:100vh}
.hdr{background:#0e0e14;border-bottom:1px solid #1a1a24;padding:12px 20px;display:flex;justify-content:space-between;align-items:center}
.hdr h1{font-size:18px;color:#fff;letter-spacing:1px}
.hdr .meta{font-size:11px;color:#555;display:flex;gap:14px;align-items:center}
.live{width:6px;height:6px;border-radius:50%;background:#0f0;display:inline-block;animation:pulse 2s infinite}
.offline{background:#f44}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.wrap{padding:16px 20px;max-width:1600px;margin:0 auto}

/* Model sections */
.model-section{background:#0e0e14;border:1px solid #1a1a24;border-radius:8px;margin-bottom:16px;overflow:hidden}
.model-hdr{padding:12px 16px;display:flex;justify-content:space-between;align-items:center;cursor:pointer}
.model-hdr h2{font-size:14px;display:flex;align-items:center;gap:8px}
.model-hdr .badge{font-size:10px;padding:2px 8px;border-radius:10px;font-weight:bold}
.model-hdr .stats{display:flex;gap:20px;font-size:12px}
.model-body{padding:0 16px 16px}

/* Metrics grid */
.mg{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:12px}
.mc{background:#12121a;border:1px solid #1e1e2a;border-radius:6px;padding:10px}
.mc label{font-size:9px;color:#555;text-transform:uppercase;display:block;margin-bottom:4px}
.mc .val{font-size:20px;font-weight:bold}

/* Charts */
.charts{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px}
.chart-box{background:#0a0a10;border:1px solid #1a1a24;border-radius:6px;padding:8px}
.chart-box h3{font-size:10px;color:#555;margin-bottom:4px;text-transform:uppercase}
canvas{width:100%;height:120px}

/* Feature bars */
.feat-row{display:flex;flex-wrap:wrap;gap:1px;margin-top:4px}
.feat-bar{width:16px;border-radius:2px}
.feat-label{font-size:5px;color:#444;text-align:center;width:16px;overflow:hidden}

/* Trade log */
.tlog{max-height:140px;overflow-y:auto;font-size:10px;line-height:1.4}
.tlog-e{border-bottom:1px solid #111;padding:1px 0}

/* Distribution tables */
.dtbl{width:100%;border-collapse:collapse;font-size:10px;margin-top:4px}
.dtbl th{text-align:left;color:#555;font-weight:normal;padding:2px 6px;border-bottom:1px solid #1a1a24}
.dtbl td{padding:2px 6px;border-bottom:1px solid #111}
.dtbl .bar-bg{background:#12121a;border-radius:2px;height:10px;position:relative;min-width:60px}
.dtbl .bar-fill{height:100%;border-radius:2px;position:absolute;top:0;left:0}

/* Top/Bottom cards */
.rank-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}
.rank-card{background:#0a0a10;border:1px solid #1a1a24;border-radius:6px;padding:10px}
.rank-card h3{font-size:10px;color:#555;margin-bottom:6px;text-transform:uppercase}
.rank-item{font-size:10px;padding:2px 0;border-bottom:1px solid #0e0e14;display:flex;justify-content:space-between}

/* Colors */
.grn{color:#00ff88}.red{color:#ff4466}.ylw{color:#ffcc00}.cyn{color:#00ccff}.org{color:#ff8800}
.dim{color:#444}
</style></head><body>

<div class="hdr">
  <h1>TRADING VALUE</h1>
  <div class="meta">
    <span id="clock"></span>
    <span id="model-count"></span>
  </div>
</div>
<div class="wrap" id="root"></div>

<script>
const q=s=>document.querySelector(s);
const fmt=(v,d=2)=>v!=null?(v*100).toFixed(d)+'%':'--';
const $=(v,d=2)=>v!=null?'$'+v.toFixed(0):'--';

function drawLine(cv,data,color,bl){
  if(!cv)return;
  const ctx=cv.getContext('2d');
  const W=cv.width=cv.offsetWidth;
  const H=cv.height=120;
  ctx.clearRect(0,0,W,H);
  if(!data||data.length<2)return;
  const mn=Math.min(...data),mx=Math.max(...data),r=mx-mn||1;
  if(bl!==undefined){ctx.strokeStyle='#1a1a24';ctx.lineWidth=1;ctx.beginPath();
    const by=H-(bl-mn)/r*H;ctx.moveTo(0,by);ctx.lineTo(W,by);ctx.stroke();}
  ctx.strokeStyle=color;ctx.lineWidth=1.5;ctx.beginPath();
  data.forEach((v,i)=>{const x=i/(data.length-1)*W,y=H-(v-mn)/r*H;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
  ctx.stroke();
}

function renderFeatures(el,imp,names){
  if(!imp||!imp.length){el.innerHTML='<span class="dim">워밍업 중</span>';return;}
  const mx=Math.max(...imp);
  const uniform=1.0/imp.length;
  el.innerHTML=imp.map((v,i)=>{
    const h=Math.max(6,(v/mx)*60);
    const ratio=v*imp.length;
    const hue=ratio>1.5?0:ratio<0.5?200:120;
    const sat=ratio>1.5?'80%':ratio<0.5?'60%':'70%';
    const name=names?names[i]:'?';
    return '<div style="text-align:center"><div style="width:30px;height:'+h+'px;border-radius:3px;background:hsl('+hue+','+sat+',42%);margin:0 auto" title="'+name+': '+(v*100).toFixed(1)+'%"></div><div style="font-size:8px;color:#666;margin-top:3px;width:30px;overflow:hidden">'+name.slice(0,5)+'</div><div style="font-size:7px;color:#444">'+(v*100).toFixed(0)+'%</div></div>';
  }).join('');
}

function distTable(items,label,maxAbs){
  if(!items||!items.length)return'';
  if(!maxAbs)maxAbs=Math.max(...items.map(x=>Math.abs(parseFloat(x.avg_ret)||0)),0.1);
  const hasWr=items[0].avg_wr!==undefined;
  let h='<table class="dtbl"><tr><th>'+label+'</th><th>수량</th><th>평균수익</th>'+(hasWr?'<th>승률</th>':'')+'<th></th></tr>';
  items.forEach(x=>{
    const v=parseFloat(x.avg_ret)||0;
    const wr=parseFloat(x.avg_wr)||0;
    const cls=v>0.05?'grn':v<-0.05?'red':'dim';
    const wrCls=wr>45?'grn':wr>30?'ylw':'red';
    const w=Math.abs(v)/maxAbs*100;
    const bg=v>=0?'#00ff8833':'#ff446633';
    h+='<tr><td><b>'+x.name+'</b></td><td>'+x.count+'</td><td class="'+cls+'">'+v.toFixed(1)+'%</td>'+(hasWr?'<td class="'+wrCls+'">'+wr.toFixed(1)+'%</td>':'')+'<td><div class="bar-bg"><div class="bar-fill" style="width:'+w+'%;background:'+bg+'"></div></div></td></tr>';
  });
  return h+'</table>';
}

function renderTournament(id,d,color){
  const s=d.state||{};
  const summary=s.summary||{};
  const online=d.online;
  const retBest=(summary.best_ret||0)/100;
  const retAvg=(summary.avg_ret||0)/100;
  const retWorst=(summary.worst_ret||0)/100;
  const trades=summary.total_trades||0;
  const posPct=(summary.positive_pct||0)/100;
  const progress=s.progress||{};
  const tournament=s.tournament||{};

  let h='<div class="model-section"><div class="model-hdr" style="border-left:3px solid '+color+'"><h2><span class="'+(online?'live':'live offline')+'"></span> '+d.name+'</h2><div class="stats">';
  h+='<span>최고: <b class="'+(retBest>0?'grn':'red')+'">'+fmt(retBest)+'</b></span>';
  h+='<span>거래: <b>'+trades+'</b>회</span>';
  h+='<span>'+((tournament.phase)||'')+'</span>';
  h+='<span>'+(tournament.next_round||'')+'</span>';
  h+='<span class="red" style="font-size:10px">수수료: 미반영 (총수익)</span>';
  h+='</div></div><div class="model-body">';

  // Summary metrics
  h+='<div class="mg">';
  h+='<div class="mc"><label>최고 수익</label><div class="val '+(retBest>0?'grn':'red')+'">'+fmt(retBest)+'</div></div>';
  h+='<div class="mc"><label>평균 수익</label><div class="val '+(retAvg>0?'grn':'red')+'">'+fmt(retAvg)+'</div></div>';
  h+='<div class="mc"><label>최악 손실</label><div class="val red">'+fmt(retWorst)+'</div></div>';
  h+='<div class="mc"><label>총 거래</label><div class="val">'+trades+'</div></div>';
  h+='<div class="mc"><label>수익 비율</label><div class="val '+(posPct>0.04?'ylw':'red')+'">'+fmt(posPct)+'</div></div>';
  h+='</div>';

  // Strategy / Asset / Timeframe distribution tables
  h+='<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px">';
  h+='<div>'+distTable(s.strategy_dist,'Strategy')+'</div>';
  h+='<div>'+distTable(s.asset_dist,'Asset')+'</div>';
  h+='<div>'+distTable(s.tf_dist,'Timeframe')+'</div>';
  h+='</div>';

  // Top 10 / Bottom 10
  const top10=s.top10||[];
  const bot10=s.bot10||[];
  h+='<div class="rank-grid">';
  h+='<div class="rank-card"><h3>Top 10 (수익)</h3>';
  if(top10.length){
    top10.forEach((v,i)=>{
      h+='<div class="rank-item"><span>#'+(i+1)+' <b class="org">'+v.strategy+'</b> '+v.asset+'/'+v.tf+' lev='+v.lev.toFixed(1)+'x</span><span class="grn">+'+v.ret.toFixed(2)+'% <span class="dim">'+v.trades+'t WR'+v.wr.toFixed(0)+'%</span></span></div>';
    });
  }else h+='<span class="dim">no data</span>';
  h+='</div>';
  h+='<div class="rank-card"><h3>Bottom 10 (손실)</h3>';
  if(bot10.length){
    bot10.forEach((v,i)=>{
      h+='<div class="rank-item"><span>#'+(i+1)+' <b class="red">'+v.strategy+'</b> '+v.asset+'/'+v.tf+' lev='+v.lev.toFixed(1)+'x</span><span class="red">'+v.ret.toFixed(2)+'% <span class="dim">'+v.trades+'t DD'+v.dd.toFixed(1)+'%</span></span></div>';
    });
  }else h+='<span class="dim">no data</span>';
  h+='</div></div>';

  // Histogram
  const hist=s.histogram||{};
  if(hist.bins&&hist.counts){
    const maxC=Math.max(...hist.counts);
    h+='<div style="margin-top:10px"><div style="font-size:10px;color:#555;margin-bottom:4px">수익률 분포 (5,000개 변형)</div>';
    h+='<div style="display:flex;align-items:flex-end;gap:1px;height:50px">';
    hist.counts.forEach((c,i)=>{
      const hPx=maxC>0?Math.max(1,c/maxC*48):1;
      const isPos=i>=hist.bins.length/2;
      h+='<div title="'+hist.bins[i]+': '+c+'" style="flex:1;height:'+hPx+'px;background:'+(isPos?'#00ff8844':'#ff446644')+';border-radius:1px"></div>';
    });
    h+='</div>';
    h+='<div style="display:flex;justify-content:space-between;font-size:8px;color:#444"><span>'+hist.bins[0]+'</span><span>0%</span><span>'+hist.bins[hist.bins.length-1]+'</span></div>';
    h+='</div>';
  }

  h+='</div></div>';
  return h;
}

function renderV2(id,d,color){
  const s=d.state||{};
  const online=d.online;
  const acc=s.accuracy||0.5;
  const ent=s.entropy||1;
  const ret=s.total_return||0;
  const cap=s.capital||10000;
  const dd=s.drawdown||0;
  const kelly=s.kelly||0;
  const exp=s.exposure||0;
  const notional=s.notional||0;
  const maxLev=s.max_leverage||100;
  const preds=s.total_predictions||0;
  const totalTrades=s.total_trades||0;

  let html='<div class="model-section"><div class="model-hdr" style="border-left:3px solid '+color+'"><h2><span class="'+(online?'live':'live offline')+'"></span> '+d.name+' <span style="font-size:10px;color:#ff8800;margin-left:6px">수수료 0.21% RT | 레버리지 1~'+maxLev+'x | Long+Short</span></h2><div class="stats">';
  html+='<span>정확도: <b class="'+(acc>0.52?'grn':acc>0.48?'ylw':'red')+'">'+fmt(acc)+'</b></span>';
  html+='<span>엔트로피: <b class="'+(ent>0.8?'grn':'ylw')+'">'+fmt(ent,1)+'</b></span>';
  html+='<span>수익: <b class="'+(ret>0?'grn':'red')+'">'+fmt(ret)+'</b></span>';
  html+='<span>거래: <b>'+totalTrades+'</b>회</span>';
  html+='</div></div><div class="model-body">';

  // Metrics
  html+='<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-bottom:12px">';
  html+='<div class="mc"><label>규칙1: 예측 정확도</label><div class="val '+(acc>0.52?'cyn':'dim')+'">'+fmt(acc)+'</div></div>';
  html+='<div class="mc"><label>규칙2: 기억 엔트로피</label><div class="val '+(ent>0.8?'ylw':'dim')+'">'+fmt(ent,1)+'</div></div>';
  html+='<div class="mc"><label>규칙3: 순수익</label><div class="val '+(ret>0?'grn':'red')+'">'+fmt(ret)+'</div></div>';
  html+='<div class="mc"><label>자본</label><div class="val">'+$(cap)+'</div></div>';
  html+='<div class="mc"><label>총 거래</label><div class="val">'+totalTrades+'<span style="font-size:11px;color:#555">회</span></div></div>';
  html+='<div class="mc"><label>켈리 / 레버리지</label><div class="val dim">'+fmt(kelly)+' / '+(notional>0?notional.toFixed(1):'0')+'x</div></div>';
  html+='</div>';

  // Charts
  html+='<div class="charts">';
  html+='<div class="chart-box"><h3>손익 (수수료 차감)</h3><canvas id="cv-v2-pnl"></canvas></div>';
  html+='<div class="chart-box"><h3>예측 정확도</h3><canvas id="cv-v2-acc"></canvas></div>';
  html+='</div>';

  // Memory map (bigger)
  html+='<div style="font-size:11px;color:#888;margin-bottom:4px;font-weight:bold">기억 공간 맵 ('+((s.feature_names||[]).length)+'개 피처)</div>';
  html+='<div id="v2-feat" style="display:flex;flex-wrap:wrap;gap:3px;padding:8px;background:#0a0a10;border:1px solid #1a1a24;border-radius:6px"></div>';

  // Positions
  html+='<div style="margin-top:10px"><div style="font-size:11px;color:#888;margin-bottom:4px;font-weight:bold">포지션</div>';
  const pos=s.positions||[];
  if(!pos.length)html+='<span class="dim" style="font-size:11px">포지션 없음</span>';
  else{
    html+='<div style="font-size:11px">';
    pos.forEach(p=>{
      html+='<div style="padding:3px 0;border-bottom:1px solid #111"><span class="'+(p.dir==='long'?'grn':'red')+'" style="font-weight:bold">'+p.dir.toUpperCase()+'</span> '+p.asset+' @$'+p.entry+' <span class="dim">마진 '+(p.size*100).toFixed(1)+'%</span> <span class="org">'+p.lev+'x</span> <span class="dim">'+p.time+'</span></div>';
    });
    html+='</div>';
  }
  html+='</div>';

  // Trade log
  const tlog=s.trade_log||[];
  html+='<div style="margin-top:10px"><div style="font-size:11px;color:#888;margin-bottom:4px;font-weight:bold">거래 내역</div>';
  if(tlog.length){
    html+='<div class="tlog">';
    tlog.slice(-20).reverse().forEach(t=>{
      html+='<div class="tlog-e"><span class="'+(t.net>0?'grn':'red')+'" style="font-weight:bold">'+t.dir+'</span> '+t.asset+' $'+t.entry+' → $'+t.exit+' <span class="dim">마진 '+(t.size*100).toFixed(1)+'%</span> <span class="org">'+(t.lev||1)+'x</span> 순익=<span class="'+(t.net>0?'grn':'red')+'">'+fmt(t.net)+'</span> 잔고='+$(t.capital)+'</div>';
    });
    html+='</div>';
  }else html+='<span class="dim" style="font-size:11px">거래 없음 (워밍업 중)</span>';
  html+='</div>';

  html+='</div></div>';
  return html;
}

function renderV3(id,d,color){
  const s=d.state||{};
  const online=d.online;
  const variants=s.variants||{};
  const warmup=s.memory_warmup||30;
  const fullAct=s.memory_full_activation||100;

  // Header summary: best variant + total trades
  let bestName='--', bestRet=-Infinity, totalTrades=0;
  for(const[vn,v]of Object.entries(variants)){
    totalTrades+=v.total_trades||0;
    if((v.total_return||0)>bestRet){bestRet=v.total_return||0;bestName=vn;}
  }

  let html='<div class="model-section"><div class="model-hdr" style="border-left:3px solid '+color+'"><h2><span class="'+(online?'live':'live offline')+'"></span> '+d.name+' <span style="font-size:10px;color:#aa66ff;margin-left:6px">VWAP/EMA9/VP + Context k-NN | 수수료 0.21% RT | Risk 0.5%/trade</span></h2><div class="stats">';
  html+='<span>최고: <b class="'+(bestRet>0?'grn':'red')+'">'+fmt(bestRet)+'</b> ('+bestName+')</span>';
  html+='<span>총 거래: <b>'+totalTrades+'</b>회</span>';
  html+='<span class="dim" style="font-size:10px">메모리: '+warmup+'거래 후 활성 → '+fullAct+'거래에 100%</span>';
  html+='</div></div><div class="model-body">';

  // Variants grid — one card per variant
  html+='<div style="display:grid;grid-template-columns:repeat('+Object.keys(variants).length+',1fr);gap:8px;margin-bottom:12px">';
  for(const[vn,v]of Object.entries(variants)){
    const ret=v.total_return||0;
    const wr=v.win_rate||0;
    const dd=v.drawdown||0;
    const mem=v.memory||{};
    const sig=v.signals||{};
    const bl=mem.blacklisted_clusters||0;
    const cfg=v.config||{};
    const isOff=!cfg.memory;

    html+='<div class="mc" style="border-left:3px solid '+(ret>0?'#00ff88':ret<-0.05?'#ff4466':'#ffcc00')+'">';
    html+='<label>'+vn.replace('v3-','').toUpperCase()+' '+(isOff?'<span style="color:#f44">[CONTROL]</span>':'')+'</label>';
    html+='<div class="val '+(ret>0?'grn':'red')+'" style="font-size:16px">'+fmt(ret)+'</div>';
    html+='<div style="font-size:9px;color:#555;margin-top:3px">RR≥'+cfg.rr_min+' | TF '+cfg.timeframe+'</div>';
    html+='<div style="font-size:10px;margin-top:4px"><span class="'+(wr>0.5?'grn':wr>0.4?'ylw':'red')+'">WR '+(wr*100).toFixed(0)+'%</span> <span class="dim">'+v.total_trades+'t</span> <span class="red" style="font-size:9px">DD '+(dd*100).toFixed(1)+'%</span></div>';
    html+='<div style="font-size:9px;color:#666;margin-top:3px">mem: <span class="cyn">'+(mem.n_trades||0)+'</span> 블랙: <span class="'+(bl>0?'red':'dim')+'">'+bl+'</span></div>';
    html+='</div>';
  }
  html+='</div>';

  // Signal funnel table
  html+='<div style="margin-top:8px"><div style="font-size:10px;color:#555;margin-bottom:3px;text-transform:uppercase">신호 필터링 깔때기 (각 variant 누적)</div>';
  html+='<table class="dtbl"><tr><th>Variant</th><th>검토</th><th>CHOP 차단</th><th>RR 차단</th><th>메모리 차단</th><th>실행</th><th>실행률</th></tr>';
  for(const[vn,v]of Object.entries(variants)){
    const sig=v.signals||{};
    const considered=sig.considered||0;
    const exec=sig.executed||0;
    const execPct=considered>0?(exec/considered*100):0;
    html+='<tr><td><b>'+vn.replace('v3-','')+'</b></td>';
    html+='<td>'+considered+'</td>';
    html+='<td class="dim">'+(sig.blocked_chop||0)+'</td>';
    html+='<td class="dim">'+(sig.blocked_rr||0)+'</td>';
    html+='<td class="'+((sig.blocked_memory||0)>0?'ylw':'dim')+'">'+(sig.blocked_memory||0)+'</td>';
    html+='<td class="cyn"><b>'+exec+'</b></td>';
    html+='<td class="'+(execPct>5?'grn':'dim')+'">'+execPct.toFixed(1)+'%</td></tr>';
  }
  html+='</table></div>';

  // Memory EV summary
  html+='<div style="margin-top:10px"><div style="font-size:10px;color:#555;margin-bottom:3px;text-transform:uppercase">컨텍스트 메모리 통계 (자기학습)</div>';
  html+='<table class="dtbl"><tr><th>Variant</th><th>메모리 거래</th><th>EV Long (R)</th><th>EV Short (R)</th><th>평균 R</th><th>승률</th><th>블랙리스트</th></tr>';
  for(const[vn,v]of Object.entries(variants)){
    const m=v.memory||{};
    const evL=m.ev_long||0;
    const evS=m.ev_short||0;
    const avgR=m.avg_r||0;
    const mwr=m.win_rate||0;
    html+='<tr><td><b>'+vn.replace('v3-','')+'</b></td>';
    html+='<td>'+(m.n_trades||0)+'</td>';
    html+='<td class="'+(evL>0.3?'grn':evL<-0.3?'red':'dim')+'">'+evL.toFixed(2)+'</td>';
    html+='<td class="'+(evS>0.3?'grn':evS<-0.3?'red':'dim')+'">'+evS.toFixed(2)+'</td>';
    html+='<td class="'+(avgR>0?'grn':'red')+'">'+avgR.toFixed(2)+'</td>';
    html+='<td class="'+(mwr>0.5?'grn':mwr>0.4?'ylw':'red')+'">'+(mwr*100).toFixed(0)+'%</td>';
    html+='<td class="'+((m.blacklisted_clusters||0)>0?'red':'dim')+'">'+(m.blacklisted_clusters||0)+'</td></tr>';
  }
  html+='</table></div>';

  // PnL charts per variant (compact)
  html+='<div style="display:grid;grid-template-columns:repeat('+Object.keys(variants).length+',1fr);gap:6px;margin-top:10px">';
  for(const[vn,v]of Object.entries(variants)){
    html+='<div class="chart-box"><h3>'+vn.replace('v3-','').toUpperCase()+' PnL</h3><canvas id="cv-v3-'+vn+'"></canvas></div>';
  }
  html+='</div>';

  // Positions (all variants)
  let posCount=0;
  let posHtml='';
  for(const[vn,v]of Object.entries(variants)){
    const pos=v.positions||[];
    pos.forEach(p=>{
      posCount++;
      posHtml+='<div style="padding:3px 0;border-bottom:1px solid #111;font-size:11px"><span class="dim">['+vn.replace('v3-','')+']</span> <span class="'+(p.dir==='long'?'grn':'red')+'" style="font-weight:bold">'+p.dir.toUpperCase()+'</span> '+p.asset+' @$'+p.entry.toFixed(2)+' → tgt $'+p.target.toFixed(2)+' / stop $'+p.hard_stop.toFixed(2)+' <span class="org">'+p.lev+'x</span></div>';
    });
  }
  if(posCount>0){
    html+='<div style="margin-top:10px"><div style="font-size:11px;color:#888;margin-bottom:4px;font-weight:bold">열린 포지션 ('+posCount+')</div>'+posHtml+'</div>';
  }

  // Recent trades (aggregated, latest 20)
  let allTrades=[];
  for(const[vn,v]of Object.entries(variants)){
    (v.trade_log||[]).forEach(t=>{allTrades.push({...t,variant:vn});});
  }
  allTrades.sort((a,b)=>(b.time||'').localeCompare(a.time||''));
  allTrades=allTrades.slice(0,20);
  if(allTrades.length){
    html+='<div style="margin-top:10px"><div style="font-size:11px;color:#888;margin-bottom:4px;font-weight:bold">최근 거래 (전체 variant)</div>';
    html+='<div class="tlog">';
    allTrades.forEach(t=>{
      const r=t.r_mult||0;
      html+='<div class="tlog-e"><span class="dim">['+t.variant.replace('v3-','')+']</span> <span class="'+(t.net>0?'grn':'red')+'" style="font-weight:bold">'+t.dir+'</span> '+t.asset+' $'+t.entry+' → $'+t.exit+' <span class="'+(r>0?'grn':'red')+'">'+(r>=0?'+':'')+r.toFixed(2)+'R</span> <span class="dim">['+t.reason+']</span> 잔고='+$(t.capital)+'</div>';
    });
    html+='</div></div>';
  }

  html+='</div></div>';
  return html;
}

async function refresh(){
  try{
    const r=await fetch('/api/all');
    const d=await r.json();
    let html='';
    let online=0,total=0;
    for(const[id,m]of Object.entries(d)){
      total++;
      if(m.online)online++;
      if(id==='tournament')html+=renderTournament(id,m,m.color);
      else if(id==='v3')html+=renderV3(id,m,m.color);
      else html+=renderV2(id,m,m.color);
    }
    q('#root').innerHTML=html;
    q('#model-count').textContent=online+'/'+total+' 모델 온라인';
    q('#clock').textContent=new Date().toLocaleTimeString();

    // Draw V2 charts after DOM update
    const v2=d.v2;
    if(v2&&v2.online&&v2.state){
      const s=v2.state;
      drawLine(q('#cv-v2-pnl'),s.pnl_history,'#00ff88',s.initial_capital);
      drawLine(q('#cv-v2-acc'),s.accuracy_history,'#00ccff',0.5);
      renderFeatures(q('#v2-feat'),s.feature_importance,s.feature_names);
    }

    // Draw V3 per-variant PnL charts
    const v3d=d.v3;
    if(v3d&&v3d.online&&v3d.state){
      const variants=v3d.state.variants||{};
      for(const[vn,v]of Object.entries(variants)){
        const ret=v.total_return||0;
        const color=ret>0?'#00ff88':ret<-0.05?'#ff4466':'#ffcc00';
        drawLine(q('#cv-v3-'+vn),v.pnl_history,color,v.initial_capital);
      }
    }
  }catch(e){
    q('#root').innerHTML='<div style="color:#f44;padding:40px">대시보드 연결 오류. 모델이 오프라인일 수 있습니다.</div>';
  }
}
setInterval(refresh,5000);
refresh();
</script>
</body></html>"""


def main():
    parser = argparse.ArgumentParser(description="Unified Trading Dashboard")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    server = http.server.HTTPServer(("0.0.0.0", args.port), Handler)
    print(f"[Unified Dashboard] http://localhost:{args.port}")
    print(f"[Proxying] {', '.join(f'{v['name']} :{v['port']}' for v in MODELS.values())}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Dashboard] Stopped.")


if __name__ == "__main__":
    main()
