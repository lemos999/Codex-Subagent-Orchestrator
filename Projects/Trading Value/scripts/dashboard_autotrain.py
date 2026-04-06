"""Unified auto-train dashboard v2: clear at-a-glance status."""
import http.server, json, urllib.request

INSTANCES = [
    {"name": "V2 Autonomous", "port": 8891, "algo": "LSTM continuous [-1,+1]"},
]

DASH_PORT = 8893

# Rough timing estimates (seconds) per phase
EST_EVAL_SEC = 300      # ~5 min for 20-day sim
EST_RETRAIN_SEC = 1200  # ~20 min for 200K steps


def fetch_instance(port: int, timeout: float = 2.0) -> dict | None:
    try:
        req = urllib.request.urlopen(f"http://localhost:{port}/api/status", timeout=timeout)
        return json.loads(req.read())
    except Exception:
        return None


HTML = r"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<title>Auto-Train Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e0e0;font-family:'Segoe UI',system-ui,monospace;min-height:100vh}
.hdr{background:#141926;padding:12px 24px;border-bottom:1px solid #2a3040;display:flex;justify-content:space-between;align-items:center}
.hdr h1{font-size:15px;color:#ff6b35;letter-spacing:1px}
.hdr .ts{font-size:11px;color:#555}
.wrap{padding:16px 20px;max-width:1400px;margin:0 auto}
.models{display:grid;grid-template-columns:repeat(auto-fit,minmax(560px,1fr));gap:14px}

/* Card */
.card{background:#141926;border:1px solid #2a3040;border-radius:8px;overflow:hidden}
.card.offline{opacity:0.5}
.card-top{padding:14px 16px;border-bottom:1px solid #1a2030}
.card-top .row1{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.card-top .model-name{font-size:16px;font-weight:bold;color:#fff}
.card-top .algo{font-size:11px;color:#666;margin-left:8px}

/* Status badge */
.badge{padding:3px 10px;border-radius:4px;font-size:10px;font-weight:bold;text-transform:uppercase;letter-spacing:0.5px}
.b-eval{background:#4dabf722;color:#4dabf7}
.b-train{background:#ffd70022;color:#ffd700}
.b-hold{background:#b35cff22;color:#b35cff}
.b-done{background:#00d4aa22;color:#00d4aa}
.b-fail{background:#ff4d6a22;color:#ff4d6a}
.b-off{background:#33333322;color:#666}

/* Progress bar */
.progress-wrap{margin-top:6px}
.progress-label{display:flex;justify-content:space-between;font-size:11px;color:#888;margin-bottom:3px}
.progress-bar{height:8px;background:#1a2030;border-radius:4px;overflow:hidden}
.progress-bar .fill{height:100%;border-radius:4px;transition:width .8s ease}

/* Key metrics strip */
.metrics-strip{display:grid;grid-template-columns:repeat(6,1fr);border-bottom:1px solid #1a2030}
.ms-item{padding:10px 8px;text-align:center;border-right:1px solid #1a2030}
.ms-item:last-child{border-right:none}
.ms-item .k{font-size:9px;color:#555;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px}
.ms-item .v{font-size:16px;font-weight:bold}

/* Current activity */
.activity{padding:10px 16px;border-bottom:1px solid #1a2030;font-size:12px;color:#999;display:flex;align-items:center;gap:8px}
.activity .dot{width:6px;height:6px;border-radius:50%;animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}
.dot-eval{background:#4dabf7}
.dot-train{background:#ffd700}
.dot-hold{background:#b35cff}

/* History */
.history{padding:10px 16px}
.history .title{font-size:10px;color:#444;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
table{width:100%;border-collapse:collapse;font-size:11px}
th{text-align:left;color:#555;padding:4px 6px;border-bottom:1px solid #2a3040;font-size:10px}
td{padding:4px 6px;border-bottom:1px solid #141926}
.gn{color:#00d4aa}.rd{color:#ff4d6a}.gy{color:#444}.yl{color:#ffd700}

/* Offline */
.off-msg{padding:40px 16px;text-align:center;color:#555;font-size:13px}
</style></head><body>
<div class="hdr">
  <h1>RL \uc790\ub3d9 \ud559\uc2b5</h1>
  <div class="ts" id="clock">--</div>
</div>
<div class="wrap">
  <div class="models" id="models"></div>
</div>
<script>
const EST_EVAL=300,EST_RETRAIN=1200;
function fmt(v){return v>=0?'+'+v.toFixed(1):v.toFixed(1)}

function calcProgress(d){
  // Total work units: per cycle = 1 eval + up to 3 retrain + 3 re-eval + maybe holdout
  // Simplified: each cycle has ~4 phases avg
  const h=d.history||[];
  const maxC=d.max_cycles||3;
  const phase=d.phase||'';
  const extra=d.extra||{};

  // Completed cycles count as done
  let done=h.length;
  // Current cycle partial progress
  let partial=0;
  if(phase==='evaluating') partial=0.3;
  else if(phase==='retraining'){
    const att=extra.attempt||1;
    partial=0.1+att*0.25;
  }
  else if(phase==='holdout') partial=0.8;
  else if(phase==='cycle_done') partial=1.0;

  const total=done+partial;
  return Math.min(100,total/maxC*100);
}

function estRemain(d){
  const h=d.history||[];
  const maxC=d.max_cycles||3;
  const phase=d.phase||'';
  const extra=d.extra||{};
  const remaining=maxC-h.length;
  if(remaining<=0)return'\uc644\ub8cc';

  // Rough: each cycle ~30min avg (eval+retrain+reeval)
  const perCycle=30;
  let currentLeft=0;
  if(phase==='evaluating') currentLeft=5;
  else if(phase==='retraining'){
    const att=extra.attempt||1;
    currentLeft=20+(3-att)*25; // remaining retrains
  }
  else if(phase==='holdout') currentLeft=5;

  const totalMin=currentLeft+(remaining-1)*perCycle;
  if(totalMin<60) return `~${Math.round(totalMin)}m`;
  return `~${(totalMin/60).toFixed(1)}h`;
}

function totalRetrains(h){
  return h.reduce((s,c)=>s+(c.retrain_attempts||0),0);
}

function bestScore(h){
  if(!h.length)return{wr:0,ret:0};
  const wrs=h.map(c=>(c.val_result||{}).win_rate||0);
  const rets=h.map(c=>(c.val_result||{}).return_pct||-999);
  return{wr:Math.max(...wrs),ret:Math.max(...rets)};
}

function renderCard(d,name,algo){
  if(!d)return`<div class="card offline"><div class="card-top"><div class="row1"><div><span class="model-name">${name}</span><span class="algo">${algo}</span></div><span class="badge b-off">\uc624\ud504\ub77c\uc778</span></div></div><div class="off-msg">\uc751\ub2f5 \uc5c6\uc74c</div></div>`;

  const phase=d.phase||d.status||'init';
  const status=d.status||'loading';
  const h=d.history||[];
  const maxC=d.max_cycles||3;
  const extra=d.extra||{};
  const passes=d.holdout_passes||0;
  const pct=calcProgress(d);
  const remain=estRemain(d);
  const retrains=totalRetrains(h);
  const best=bestScore(h);
  const lastH=h.length>0?h[h.length-1]:{};
  const lastVal=lastH.val_result||{};

  // Badge
  let badgeCls='b-eval',badgeTxt=phase.toUpperCase();
  if(status==='deploy_candidate'){badgeCls='b-done';badgeTxt='\ubc30\ud3ec \uc900\ube44';}
  else if(status==='completed'){badgeCls='b-done';badgeTxt='\uc644\ub8cc';}
  else if(phase==='retraining'){badgeCls='b-train';badgeTxt=`\ud559\uc2b5 ${extra.attempt||'?'}/3`;}
  else if(phase==='evaluating'){badgeCls='b-eval';badgeTxt='\ud3c9\uac00 \uc911';}
  else if(phase==='holdout'){badgeCls='b-hold';badgeTxt='\ud640\ub4dc\uc544\uc6c3';}

  // Dot color
  let dotCls='dot-eval';
  if(phase==='retraining')dotCls='dot-train';
  else if(phase==='holdout')dotCls='dot-hold';

  // Activity text
  let actText='\ucd08\uae30\ud654 \uc911...';
  if(extra.period){
    const labels={evaluating:'\uc2dc\ubbac \ud3c9\uac00',retraining:'RL \ud559\uc2b5 (200K \uc2a4\ud15d)',holdout:'\ud640\ub4dc\uc544\uc6c3 \uac80\uc99d'};
    actText=`${labels[phase]||phase}: ${extra.period}`;
    if(phase==='retraining'&&extra.attempt) actText+=` (\uc2dc\ub3c4 ${extra.attempt}/3)`;
  }

  // Performance status
  let perfStatus='', perfCls='gy';
  if(h.length>0){
    if(lastVal.passed_internal){perfStatus='\ud1b5\uacfc';perfCls='gn';}
    else if(lastVal.win_rate>=50){perfStatus='\uadfc\uc811';perfCls='yl';}
    else if(lastVal.win_rate>=40){perfStatus='\uac1c\uc120 \uc911';perfCls='yl';}
    else{perfStatus='\ubbf8\ub2ec';perfCls='rd';}
  }else{perfStatus='\ub300\uae30';perfCls='gy';}

  // History rows
  let rows='';
  for(const c of h){
    const vr=c.val_result||{};
    const hr=c.holdout_result;
    const adj=c.reward_adjusted?'<span class="yl" title="Reward adjusted"> &#9881;</span>':'';
    const hoText=hr?`<span class="${hr.passed_internal?'gn':'rd'}">${hr.win_rate}%/${fmt(hr.return_pct)}%</span>`:'<span class="gy">-</span>';
    rows+=`<tr>
      <td>${c.cycle}</td><td>${c.wf_set}</td>
      <td class="${vr.win_rate>=55?'gn':'rd'}">${vr.win_rate?.toFixed(0)||0}%</td>
      <td class="${vr.return_pct>=5?'gn':'rd'}">${fmt(vr.return_pct||0)}%</td>
      <td>${vr.trades||0}</td>
      <td>${c.retrain_attempts}${adj}</td>
      <td>${hoText}</td>
      <td class="${vr.passed_internal?'gn':'rd'}">${vr.passed_internal?'\ud1b5\uacfc':'\uc2e4\ud328'}</td></tr>`;
  }
  if(!rows)rows='<tr><td colspan="8" class="gy" style="text-align:center">\uc544\uc9c1 \uc644\ub8cc\ub41c \uc0ac\uc774\ud074 \uc5c6\uc74c</td></tr>';

  return `<div class="card">
    <div class="card-top">
      <div class="row1">
        <div><span class="model-name">${name}</span><span class="algo">${algo}</span></div>
        <span class="badge ${badgeCls}">${badgeTxt}</span>
      </div>
      <div class="progress-wrap">
        <div class="progress-label">
          <span>Cycle ${h.length}/${maxC}</span>
          <span>${pct.toFixed(0)}% &middot; ${remain} \ub0a8\uc74c</span>
        </div>
        <div class="progress-bar"><div class="fill" style="width:${pct}%;background:linear-gradient(90deg,#ff6b35,#ff9800)"></div></div>
      </div>
    </div>

    <div class="metrics-strip">
      <div class="ms-item"><div class="k">\uc131\uacfc</div><div class="v ${perfCls}" style="font-size:12px">${perfStatus}</div></div>
      <div class="ms-item"><div class="k">\ucd5c\uace0 \uc2b9\ub960</div><div class="v ${best.wr>=55?'gn':'rd'}">${best.wr>0?best.wr.toFixed(0)+'%':'--'}</div></div>
      <div class="ms-item"><div class="k">\ucd5c\uace0 \uc218\uc775</div><div class="v ${best.ret>=5?'gn':'rd'}">${best.ret>-999?fmt(best.ret)+'%':'--'}</div></div>
      <div class="ms-item"><div class="k">\ud640\ub4dc\uc544\uc6c3</div><div class="v ${passes>=2?'gn':passes>0?'yl':'gy'}">${passes}/2</div></div>
      <div class="ms-item"><div class="k">\ud559\uc2b5 \ud69f\uc218</div><div class="v">${retrains}</div></div>
      <div class="ms-item"><div class="k">\uac70\ub798 \uc218</div><div class="v">${lastVal.trades||'--'}</div></div>
    </div>

    <div class="activity">
      <div class="dot ${dotCls}"></div>
      <span>${actText}</span>
    </div>

    <div class="history">
      <div class="title">\uc0ac\uc774\ud074 \uc774\ub825</div>
      <table><thead><tr><th>#</th><th>\uc138\ud2b8</th><th>\uc2b9\ub960</th><th>\uc218\uc775\ub960</th><th>\uac70\ub798</th><th>\ud559\uc2b5</th><th>\ud640\ub4dc\uc544\uc6c3</th><th>\uac8c\uc774\ud2b8</th></tr></thead>
      <tbody>${rows}</tbody></table>
    </div>
  </div>`;
}

async function refresh(){
  document.getElementById('clock').textContent=new Date().toLocaleString('ko-KR');
  try{
    const r=await fetch('/api/all?'+Date.now());
    if(!r.ok)return;
    const all=await r.json();
    let html='';
    for(const item of all){
      html+=renderCard(item.data,item.name,item.algo);
    }
    document.getElementById('models').innerHTML=html;
  }catch(e){}
}
refresh();setInterval(refresh,3000);
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/all"):
            results = []
            for inst in INSTANCES:
                data = fetch_instance(inst["port"])
                results.append({
                    "name": inst["name"],
                    "port": inst["port"],
                    "algo": inst.get("algo", ""),
                    "data": data,
                })
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(results, default=str).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", DASH_PORT), Handler)
    names = ", ".join(f"{i['name']}(:{i['port']})" for i in INSTANCES)
    print(f"  Auto-Train Dashboard: http://localhost:{DASH_PORT}")
    print(f"  Monitoring: {names}")
    server.serve_forever()
