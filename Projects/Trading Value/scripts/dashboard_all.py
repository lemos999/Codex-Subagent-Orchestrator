"""Multi-model paper trading dashboard with live candlestick chart.

Serves HTML dashboard at http://localhost:8889
- Real-time ETHUSDT 30m candlestick chart (via Binance API)
- Model entry price lines on chart
- Model cards with PnL, position, trades
- Recent trades table

Usage: cd "Projects/Trading Value" && py -3 scripts/dashboard_all.py
"""
from __future__ import annotations
import json, http.server, sys, urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
STATUS_FILE = BASE / "data" / "paper_all_status.json"
PORT = 8889

HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Trading Value - Multi-Model Dashboard</title>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e0e0;font-family:'Segoe UI',system-ui,monospace;min-height:100vh}
.hdr{background:#141926;padding:14px 24px;border-bottom:1px solid #2a3040;display:flex;justify-content:space-between;align-items:center}
.hdr h1{font-size:18px;color:#00d4aa;letter-spacing:1px}
.hdr .meta{font-size:12px;color:#666;display:flex;gap:16px;align-items:center}
.hdr .live{color:#00d4aa;animation:pulse 2s infinite}
.hdr .price{font-size:16px;font-weight:bold;color:#fff}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
.wrap{padding:16px 24px;max-width:1400px;margin:0 auto}

/* Chart */
#chartBox{background:#141926;border:1px solid #2a3040;border-radius:8px;margin-bottom:14px;overflow:hidden;position:relative}
#chartLegend{position:absolute;top:8px;right:12px;z-index:10;display:flex;gap:10px;font-size:11px}
#chartLegend .item{display:flex;align-items:center;gap:4px}
#chartLegend .dot{width:8px;height:3px;border-radius:1px}

/* Model cards grid */
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:20px}
.card{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:16px;transition:border-color .3s}
.card:hover{border-color:#00d4aa33}
.card .name{font-size:14px;color:#888;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center}
.card .name .tag{font-size:10px;padding:2px 6px;border-radius:3px;font-weight:bold}
.tag-long{background:#00d4aa22;color:#00d4aa}
.tag-short{background:#ff4d6a22;color:#ff4d6a}
.tag-flat{background:#66666622;color:#888}
.card .pnl{font-size:32px;font-weight:bold;margin:8px 0}
.gn{color:#00d4aa}.rd{color:#ff4d6a}.gy{color:#555}
.card .stats{display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;color:#999}
.card .stats .val{color:#ddd;font-weight:600}
.card .bar{height:4px;background:#1a2030;border-radius:2px;margin-top:10px;overflow:hidden}
.card .bar .fill{height:100%;border-radius:2px;transition:width .5s}

/* Trade history table */
.section{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:16px;margin-bottom:14px}
.section h2{font-size:14px;color:#888;margin-bottom:10px;text-transform:uppercase;letter-spacing:1px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;color:#666;padding:6px 8px;border-bottom:1px solid #2a3040;font-weight:normal;text-transform:uppercase}
td{padding:6px 8px;border-bottom:1px solid #1a2030}
tr:hover{background:#1a203040}

/* PnL comparison */
.cmp{display:flex;gap:4px;align-items:end;height:60px;margin-top:12px}
.cmp .col{flex:1;display:flex;flex-direction:column;align-items:center;gap:2px}
.cmp .col .bar-v{width:100%;border-radius:3px 3px 0 0;min-height:2px;transition:height .5s}
.cmp .col .lbl{font-size:9px;color:#666}

/* Live log feed */
#logFeed{max-height:300px;overflow-y:auto;font-size:12px;line-height:1.8}
#logFeed .log-entry{padding:4px 8px;border-bottom:1px solid #1a2030;display:flex;gap:12px;align-items:center}
#logFeed .log-entry:hover{background:#1a203040}
#logFeed .log-time{color:#555;min-width:60px;font-size:11px}
#logFeed .log-model{min-width:100px;font-weight:600}
#logFeed .log-event{flex:1}
#logFeed .log-pos{min-width:50px;text-align:center}
#logFeed .log-pnl{min-width:80px;text-align:right}

/* Coin tabs */
.coin-tab{background:#1a2030;border:1px solid #2a3040;color:#888;padding:8px 20px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:bold;font-family:inherit;transition:all .2s}
.coin-tab:hover{border-color:#00d4aa55;color:#ccc}
.coin-tab.active{background:#00d4aa22;border-color:#00d4aa;color:#00d4aa}
</style>
</head>
<body>

<div class="hdr">
  <h1>TRADING VALUE - Multi-Coin Live</h1>
  <div class="meta">
    <span class="price" id="coinPrice">$--</span>
    <span class="live">● LIVE</span>
    <span id="clock" style="color:#fff;font-size:14px;font-weight:bold"></span>
    <span id="lastUpdate">Loading...</span>
  </div>
</div>

<div class="wrap">
  <!-- Coin Tabs -->
  <div style="display:flex;gap:8px;margin-bottom:14px" id="coinTabs">
    <button class="coin-tab active" data-coin="ETH">ETH</button>
    <button class="coin-tab" data-coin="BTC">BTC</button>
    <button class="coin-tab" data-coin="SOL">SOL</button>
    <button class="coin-tab" data-coin="XRP">XRP</button>
    <button class="coin-tab" data-coin="ALL">ALL</button>
  </div>

  <!-- Candlestick Chart -->
  <div id="chartBox">
    <div id="chartLegend"></div>
    <div id="chart" style="height:400px"></div>
  </div>

  <!-- PnL Comparison -->
  <div class="section">
    <h2>PnL Comparison</h2>
    <div class="cmp" id="pnlChart"></div>
  </div>

  <!-- Model Cards -->
  <div class="grid" id="cards"></div>

  <!-- Live Log Feed -->
  <div class="section">
    <h2>Live Activity Log</h2>
    <div id="logFeed"></div>
  </div>

  <!-- Recent Trades -->
  <div class="section">
    <h2>Recent Trades (All Models)</h2>
    <table>
      <thead><tr><th>Model</th><th>Time</th><th>Side</th><th>PnL</th><th>PnL%</th><th>Bars</th></tr></thead>
      <tbody id="trades"></tbody>
    </table>
  </div>
</div>

<script>
const COLORS = {
  'B Berserker': '#ff6b35',
  'C Castle':    '#4ecdc4',
  'D Diplomat':  '#95e1d3',
  'E Eagle':     '#f38181',
  'F Fortress':  '#00d4aa',
  'G Gladiator': '#ffd700',
  'H FVG-KR':    '#7b68ee',
  'I FVG-PM':    '#ff69b4',
  'J FVG-US':    '#1e90ff',
};

// ============ Model Dialog ============
const DIALOG = {
  'B Berserker': {
    intent_long:  ['노린다... 올라와봐라!!', '눌림목 대기 중... 이리 와!!'],
    intent_short: ['가라앉기를 기다린다...', '되돌림 대기... 올라와봐'],
    hold_flat: ['피가 끓어오르는데...참자', '전장이 조용하군', '...칼을 가는 중', '아직이다. 아직...'],
    hold_pos:  ['으아아아!! 물러서지 않는다!', '피를 더 봐야 해', '끝까지 간다!!'],
    long:      ['돌격이다!! 전원 돌격!!', '죽어라 올라가!!', '전사의 본능이 외친다! 롱!!'],
    short:     ['밟아버려!! 숏!!', '추락하는 놈은 밟는 거다!!', '파괴!! 전부 부셔라!!'],
    close:     ['...후. 피가 식었다', '전투 종료. 칼을 거둔다', '승리의 함성!'],
    reverse:   ['반전이다! 공격 방향 전환!!', '적이 뒤에 있었다!!'],
    fast_stop: ['크윽...! 후퇴다!!', '부상당했다! 철수!!'],
  },
  'C Castle': {
    intent_long:  ['성문 개방 준비... 좋은 자리를 본다', '눌림목 대기. 서두르지 않는다'],
    intent_short: ['화살 준비... 올라오면 쏜다', '높은 곳을 노린다. 대기'],
    hold_flat: ['성벽 위에서 관망 중', '때를 기다린다', '...조용하군. 좋아', '서두를 필요 없다'],
    hold_pos:  ['방어선 유지', '성채는 흔들리지 않는다', '차분하게 홀딩'],
    long:      ['성문을 연다. 진격', '확인된 기회. 롱 진입', '기초가 탄탄한 자리다'],
    short:     ['성벽에서 화살을 쏜다. 숏', '하락의 신호가 명확하다', '수비적 숏 진입'],
    close:     ['성문을 닫는다. 포지션 정리', '임무 완수. 복귀', '안전하게 회수'],
    reverse:   ['방향 전환. 성채를 재배치', '전략 수정'],
    fast_stop: ['성벽에 균열! 긴급 철수!', '방어선 붕괴. 후퇴'],
  },
  'D Diplomat': {
    intent_long:  ['매수 합의 대기... 가격 조율 중', '상대방 제안을 기다리는 중'],
    intent_short: ['매도 합의 대기... 조건 협상 중', '유리한 조건을 기다린다'],
    hold_flat: ['양측 입장을 듣는 중...', '애매한데? 좀 더 보자', '합의점을 찾는 중', '성급한 결정은 금물'],
    hold_pos:  ['현 포지션 유지가 합리적', '아직 협상 중', '조금만 더...'],
    long:      ['쌍방 합의 완료. 롱으로', '다수결: 올라간다', '외교적 판단. 매수'],
    short:     ['불가피한 결정. 숏', '하방 리스크가 명확', '합의: 내려간다'],
    close:     ['원만한 합의로 청산', '서로 좋게 끝내자', '이 정도면 충분해'],
    reverse:   ['입장을 바꿉니다', '새로운 합의안 도출'],
    fast_stop: ['협상 결렬! 긴급 철수!', '상황이 급변했습니다!'],
  },
  'E Eagle': {
    intent_long:  ['먹이 발견! 급강하 타이밍 계산 중...', '조금만 더 내려와...'],
    intent_short: ['위에서 노린다... 올라와라', '상승 기류 대기 중... 찍는다'],
    hold_flat: ['높은 곳에서 내려다보는 중', '먹이가 아직 안 보인다', '...', '시야 확보. 대기'],
    hold_pos:  ['먹이를 놓치지 않는다', '발톱을 단단히', '하늘에서 지켜보는 중'],
    long:      ['급강하! 먹이 포착! 롱!', '지금이다! 낚아챈다!', '독수리의 눈은 틀리지 않아'],
    short:     ['위에서 내리찍는다! 숏!', '하강 기류 포착!', '먹이가 떨어진다!'],
    close:     ['먹이 획득. 귀환', '깔끔하게 마무리', '다시 하늘로'],
    reverse:   ['방향 전환! 반대편에 먹이!', '바람이 바뀌었다!'],
    fast_stop: ['난기류! 긴급 이탈!', '먹이를 놓쳤다... 귀환'],
  },
  'F Fortress': {
    intent_long:  ['진입 포인트 계산 중... 눌림 대기', '기초 확인. 최적가 탐색'],
    intent_short: ['숏 자리 탐색 중... 되돌림 대기', '구조적 약점 확인. 타이밍 조율'],
    hold_flat: ['요새 점검 중. 이상 무', '안정적인 자리를 찾는 중', '균형을 본다', '아직 조건 미충족'],
    hold_pos:  ['요새는 견고하다. 홀딩', '계획대로 진행 중', '흔들림 없이 유지'],
    long:      ['요새 확장. 롱 진입', '기반 확인 완료. 올라간다', '균형 잡힌 진입점'],
    short:     ['방어적 포지션. 숏', '구조적 하락 감지. 진입', '요새 방어 모드'],
    close:     ['목표 달성. 요새 귀환', '안정적으로 회수', '계획대로 청산'],
    reverse:   ['요새 이동! 방향 전환', '전략적 재배치'],
    fast_stop: ['요새 피격! 긴급 대피!', '구조물 손상. 철수 명령'],
  },
  'G Gladiator': {
    intent_long:  ['취그미니...!! 조금만 내려와!!', '눌림목 노리는 중... 참아'],
    intent_short: ['올라와봐라!! 찍어준다!!', '되돌림 대기... 위에서 기다린다'],
    hold_flat: ['검투사는 링을 관찰한다', '취그미니...참아', '아직 때가 아니야', '관중이 기다린다'],
    hold_pos:  ['끝까지 싸운다!', '검투사는 물러서지 않아', '아직 안 끝났다!'],
    long:      ['취그미니!! 롱!!', '대가리 맞고 올라가는 자리!', '이제 바닥이다! 올라타!!'],
    short:     ['대가리 맞고 떨어지는 자리!', '추락한다!! 숏!!', '위에서 찍는다!!'],
    close:     ['승리!! 관중이 환호한다!', '한판 끝. 다음 상대는?', '피 묻은 검을 닦는다'],
    reverse:   ['반전!! 검을 뒤집는다!!', '상대가 바뀌었다!!'],
    fast_stop: ['크윽!! 방패가 깨졌다!!', '관중이 야유한다... 퇴장'],
  },
  'H FVG-KR': {
    intent_long:  ['한국장 오픈! FVG 매수 대기', '09:30 앵커 돌파! 리테스트 기다리는 중'],
    intent_short: ['한국장 오픈! FVG 매도 대기', '09:30 앵커 하방 돌파! 되돌림 대기'],
    hold_flat: ['한국장 앵커 캔들 관찰 중', 'FVG 패턴 스캔 중...', '09:30 기준 아직 신호 없음', '갭을 찾는 중...'],
    hold_pos:  ['FVG 진입 홀딩 중. RR 2:1 목표', '타겟까지 기다린다', '규칙대로 간다'],
    long:      ['FVG 리테스트 완료! 롱 진입!', '갭이 채워졌다! 매수!', '공정가치로 돌아왔다!'],
    short:     ['FVG 리테스트 완료! 숏 진입!', '갭이 채워졌다! 매도!', '공정가치 회귀 숏!'],
    close:     ['타겟 도달. 규칙대로 청산', '깔끔한 RR 2:1', 'FVG 한 사이클 완료'],
    reverse:   ['FVG 방향 전환!', '새로운 갭 발견!'],
    fast_stop: ['스톱 히트! FVG 무효화', '갭이 거짓이었다... 손절'],
  },
  'I FVG-PM': {
    intent_long:  ['오후장! FVG 매수 포인트 탐색', '17:00 앵커 상방 돌파! 대기'],
    intent_short: ['오후장! FVG 매도 포인트 탐색', '17:00 앵커 하방 돌파! 대기'],
    hold_flat: ['오후 세션 앵커 분석 중', 'PM 캔들 형성 관찰', '17:00 기준 스캔 중...', '유럽-미국 교차 시간대'],
    hold_pos:  ['PM FVG 홀딩. 규칙 준수', '타겟까지 인내', '오후 세션 진행 중'],
    long:      ['PM FVG 롱! 갭 리테스트 진입!', '오후 매수 신호 확인!', '17:00 기준 롱!'],
    short:     ['PM FVG 숏! 갭 리테스트 진입!', '오후 매도 신호 확인!', '17:00 기준 숏!'],
    close:     ['PM 세션 목표 달성', '오후 트레이드 완료', 'RR 2:1 청산'],
    reverse:   ['PM 방향 전환!', '오후 세션 반전!'],
    fast_stop: ['PM 스톱! 손절 실행', '오후 갭 무효화'],
  },
  'J FVG-US': {
    intent_long:  ['US 마켓 오픈! FVG 매수 대기', 'NYSE 개장! 리테스트 대기 중'],
    intent_short: ['US 마켓 오픈! FVG 매도 대기', 'NYSE 개장! 하방 리테스트 대기'],
    hold_flat: ['미국장 개장 캔들 분석 중', 'US 세션 FVG 스캔...', '월스트리트가 깨어난다', '09:30 EDT 앵커 대기'],
    hold_pos:  ['US FVG 홀딩 중. 달러 흐름 추적', 'NYSE 기준 타겟 대기', '미국장 규칙 준수'],
    long:      ['US FVG 롱! 월가가 사인을 줬다!', 'NYSE 갭 리테스트 매수!', '미국장 롱 진입!'],
    short:     ['US FVG 숏! 월가가 내려간다!', 'NYSE 갭 리테스트 매도!', '미국장 숏 진입!'],
    close:     ['US 세션 목표 달성. 청산', '월가 트레이드 완료', 'RR 2:1 클린 청산'],
    reverse:   ['US 방향 전환! 월가가 뒤집었다!', '미국장 반전!'],
    fast_stop: ['US 스톱 히트! 월가의 역습', '미국장 손절. 다음 기회로'],
  },
};

function getDialog(model, action, position) {
  const d = DIALOG[model];
  if (!d) return action;
  let pool;
  if (action === 'FAST_STOP') pool = d.fast_stop || d.close;
  else if (action === 'INTENT_LONG') pool = d.intent_long || d.long;
  else if (action === 'INTENT_SHORT') pool = d.intent_short || d.short;
  else if (position === 1) pool = d.hold_pos;    // already LONG -> holding dialog
  else if (position === -1) pool = d.hold_pos;   // already SHORT -> holding dialog
  else if (action === 'CLOSE' && position === 0) pool = d.hold_flat;
  else if (action === 'CLOSE') pool = d.close;
  else if (action === 'REVERSE') pool = d.reverse;
  else if (action === 'LONG') pool = d.long;
  else if (action === 'SHORT') pool = d.short;
  else pool = d.hold_flat;
  if (!pool || pool.length === 0) return action;
  const idx = Math.floor(Date.now() / 30000) % pool.length;
  return pool[idx];
}

// ============ Coin Tab State ============
let selectedCoin = 'ETH';
const COIN_SYMBOLS = {ETH:'ETHUSDT', BTC:'BTCUSDT', SOL:'SOLUSDT', XRP:'XRPUSDT'};

document.querySelectorAll('.coin-tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.coin-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedCoin = btn.dataset.coin;
    fetchCandles();
    if (lastFullData) render(lastFullData);
    refreshLogs();
  });
});

function getModelsForCoin(models) {
  if (selectedCoin === 'ALL') return models;
  const filtered = {};
  for (const name in models) {
    const coin = models[name].coin || 'ETH';
    if (coin === selectedCoin) filtered[name] = models[name];
  }
  return filtered;
}

// ============ Real-time PnL + Clock ============
let currentCoinPrice = 0;
let lastModelsData = {};
let lastFullData = null;

function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent =
    now.toLocaleTimeString('ko-KR', {timeZone:'Asia/Seoul', hour:'2-digit', minute:'2-digit', second:'2-digit'});
}
setInterval(updateClock, 1000);
updateClock();

function updateRealtimePnl() {
  if (!currentCoinPrice || !lastModelsData) return;
  const cards = document.querySelectorAll('.card');
  const names = Object.keys(lastModelsData);
  cards.forEach((card, i) => {
    const name = names[i];
    if (!name) return;
    const m = lastModelsData[name];
    if (!m) return;
    const mCoin = m.coin || 'ETH';
    // Only update realtime PnL for models of the selected coin
    if (selectedCoin !== 'ALL' && mCoin !== selectedCoin) return;
    let pnl = m.pnl;
    if (m.position !== 0 && m.entry_price > 0 && mCoin === selectedCoin) {
      const qty = m.position_qty || ((m.balance * 0.0035 * 10) / (Math.abs(m.entry_price - (m.stop_price||m.entry_price*0.99)) || 1));
      const unrealized = (currentCoinPrice - m.entry_price) * m.position * qty;
      pnl = (m.balance + unrealized) - 10000;
    }
    const pnlEl = card.querySelector('.pnl');
    if (pnlEl) {
      pnlEl.textContent = fmt(pnl);
      pnlEl.className = 'pnl ' + pnlClass(pnl);
    }
  });
}
setInterval(updateRealtimePnl, 1000);

// ============ Chart Setup ============
const chartEl = document.getElementById('chart');
const chart = LightweightCharts.createChart(chartEl, {
  layout: { background: { color: '#141926' }, textColor: '#888' },
  grid: { vertLines: { color: '#1a2030' }, horzLines: { color: '#1a2030' } },
  crosshair: { mode: 0 },
  timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#2a3040', fixLeftEdge: true },
  localization: { locale: 'ko-KR', timeFormatter: (t) => new Date(t*1000).toLocaleTimeString('ko-KR',{timeZone:'Asia/Seoul',hour:'2-digit',minute:'2-digit'}) },
  rightPriceScale: { borderColor: '#2a3040' },
});

const candleSeries = chart.addCandlestickSeries({
  upColor: '#00d4aa', downColor: '#ff4d6a',
  borderUpColor: '#00d4aa', borderDownColor: '#ff4d6a',
  wickUpColor: '#00d4aa88', wickDownColor: '#ff4d6a88',
});

// Price lines for each model's entry
const priceLines = {};

function updatePriceLines(models) {
  // Remove old lines
  for (const key in priceLines) {
    try { candleSeries.removePriceLine(priceLines[key]); } catch(e) {}
    delete priceLines[key];
  }
  // Add new lines for models with positions
  for (const name in models) {
    const m = models[name];
    if (m.position !== 0 && m.entry_price > 0) {
      const side = m.position === 1 ? 'L' : 'S';
      const clr = COLORS[name] || '#888';
      const shortName = name.split(' ')[0];

      // Entry line
      priceLines[name + '_entry'] = candleSeries.createPriceLine({
        price: m.entry_price,
        color: clr,
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Dashed,
        axisLabelVisible: true,
        title: `${shortName} ${side}`,
      });

      // Stop line
      if (m.stop_price > 0) {
        priceLines[name + '_stop'] = candleSeries.createPriceLine({
          price: m.stop_price,
          color: '#ff4d6a',
          lineWidth: 1,
          lineStyle: LightweightCharts.LineStyle.Dotted,
          axisLabelVisible: true,
          title: `${shortName} SL`,
        });
      }

      // Target line (FVG models)
      if (m.target_price > 0) {
        priceLines[name + '_target'] = candleSeries.createPriceLine({
          price: m.target_price,
          color: '#00d4aa',
          lineWidth: 1,
          lineStyle: LightweightCharts.LineStyle.Dotted,
          axisLabelVisible: true,
          title: `${shortName} TP`,
        });
      }
    }
  }
}

// Build chart legend
let legendHtml = '';
for (const name in COLORS) {
  legendHtml += `<div class="item"><div class="dot" style="background:${COLORS[name]}"></div>${name.split(' ')[0]}</div>`;
}
document.getElementById('chartLegend').innerHTML = legendHtml;

// Fetch and update candles
let lastCandleTime = 0;

async function fetchCandles() {
  try {
    const coin = selectedCoin === 'ALL' ? 'ETH' : selectedCoin;
    const sym = COIN_SYMBOLS[coin] || 'ETHUSDT';
    const r = await fetch(`/api/candles?coin=${sym}&t=` + Date.now());
    if (!r.ok) return;
    const candles = await r.json();
    if (candles.length === 0) return;

    candleSeries.setData(candles);
    const last = candles[candles.length - 1];
    lastCandleTime = last.time;
    document.getElementById('coinPrice').textContent = coin + ' $' + last.close.toLocaleString('en', {maximumFractionDigits: 2});
  } catch(e) {}
}

async function updateLastCandle() {
  try {
    const coin = selectedCoin === 'ALL' ? 'ETH' : selectedCoin;
    const sym = COIN_SYMBOLS[coin] || 'ETHUSDT';
    const r = await fetch(`/api/candles?coin=${sym}&limit=2&t=` + Date.now());
    if (!r.ok) return;
    const candles = await r.json();
    if (candles.length === 0) return;
    const last = candles[candles.length - 1];
    candleSeries.update(last);
    currentCoinPrice = last.close;
    document.getElementById('coinPrice').textContent = coin + ' $' + last.close.toLocaleString('en', {maximumFractionDigits: 2});
  } catch(e) {}
}

// Initial load
fetchCandles();
// Full refresh every 5 min, tick update every 5s for real-time PnL
setInterval(fetchCandles, 300000);
setInterval(updateLastCandle, 5000);

// ============ Model Status ============
function posTag(pos) {
  if (pos === 1) return '<span class="tag tag-long">LONG</span>';
  if (pos === -1) return '<span class="tag tag-short">SHORT</span>';
  return '<span class="tag tag-flat">FLAT</span>';
}
function pnlClass(v) { return v > 0 ? 'gn' : v < 0 ? 'rd' : 'gy'; }
function fmt(v) { return v >= 0 ? '+$' + v.toLocaleString('en',{maximumFractionDigits:0}) : '-$' + Math.abs(v).toLocaleString('en',{maximumFractionDigits:0}); }

function render(data) {
  lastFullData = data;
  const kst = new Date(data.timestamp).toLocaleString('ko-KR', {timeZone:'Asia/Seoul'});
  document.getElementById('lastUpdate').textContent = 'Updated: ' + kst;

  const allModels = data.models;
  const models = getModelsForCoin(allModels);
  const names = Object.keys(models);
  lastModelsData = models;  // Store for real-time PnL updates

  // Update chart price lines
  updatePriceLines(models);

  // Cards
  let cards = '';
  for (const name of names) {
    const m = models[name];
    const pnl = m.pnl;
    const wr = m.total_trades > 0 ? (m.wins / m.total_trades * 100).toFixed(0) : '-';
    const ddPct = m.peak_balance > 0 ? (m.max_drawdown / m.peak_balance * 100).toFixed(1) : '0.0';
    const clr = COLORS[name] || '#888';
    const barW = Math.min(100, Math.max(2, Math.abs(pnl) / 500 * 100));

    cards += `
    <div class="card" style="border-left:3px solid ${clr}">
      <div class="name">${name} ${posTag(m.position)}</div>
      <div class="pnl ${pnlClass(pnl)}">${fmt(pnl)}</div>
      <div class="stats">
        <div>Balance <div class="val">$${m.balance.toLocaleString('en',{maximumFractionDigits:0})}</div></div>
        <div>Trades <div class="val">${m.total_trades} (${m.wins}W/${m.losses}L)</div></div>
        <div>Win Rate <div class="val">${wr}%</div></div>
        <div>Max DD <div class="val">${ddPct}%</div></div>
        ${m.position !== 0 ? `<div>Entry <div class="val">$${m.entry_price.toLocaleString('en',{maximumFractionDigits:2})}</div></div>
        <div>Stop <div class="val">$${m.stop_price.toLocaleString('en',{maximumFractionDigits:2})}</div></div>` : ''}
        ${m.pending_intent ? `<div style="grid-column:1/-1;color:#ffd700;font-size:11px">Pending: ${m.pending_intent} @ $${m.intent_price?.toLocaleString('en',{maximumFractionDigits:0}) || '?'}</div>` : ''}
        ${m.target_price > 0 && m.position !== 0 ? `<div>Target <div class="val gn">$${m.target_price.toLocaleString('en',{maximumFractionDigits:2})}</div></div>` : ''}
        ${m.fvg_phase ? `<div style="grid-column:1/-1;color:#7b68ee;font-size:11px">FVG: ${m.fvg_phase}</div>` : ''}
      </div>
      <div class="bar"><div class="fill" style="width:${barW}%;background:${pnl>=0?'#00d4aa':'#ff4d6a'}"></div></div>
    </div>`;
  }
  document.getElementById('cards').innerHTML = cards;

  // PnL Chart
  const pnls = names.map(n => models[n].pnl);
  const maxPnl = Math.max(...pnls.map(Math.abs), 1);
  let pnlHtml = '';
  for (const name of names) {
    const pnl = models[name].pnl;
    const h = Math.max(2, Math.abs(pnl) / maxPnl * 50);
    const clr = pnl >= 0 ? (COLORS[name] || '#00d4aa') : '#ff4d6a';
    pnlHtml += `<div class="col">
      <div style="font-size:10px" class="${pnlClass(pnl)}">${fmt(pnl)}</div>
      <div class="bar-v" style="height:${h}px;background:${clr}"></div>
      <div class="lbl">${name.split(' ')[0]}</div>
    </div>`;
  }
  document.getElementById('pnlChart').innerHTML = pnlHtml;

  // Recent trades
  let allTrades = [];
  for (const name of names) {
    for (const t of (models[name].trades || [])) {
      allTrades.push({...t, model: name});
    }
  }
  allTrades.sort((a, b) => (b.exit_time || '').localeCompare(a.exit_time || ''));

  let rows = '';
  for (const t of allTrades.slice(0, 30)) {
    const clr = COLORS[t.model] || '#888';
    rows += `<tr>
      <td style="color:${clr}">${t.model}</td>
      <td>${(t.exit_time||'').slice(0,16)}</td>
      <td>${t.side}</td>
      <td class="${pnlClass(t.pnl)}">${fmt(t.pnl)}</td>
      <td class="${pnlClass(t.pnl_pct)}">${t.pnl_pct>0?'+':''}${t.pnl_pct.toFixed(1)}%</td>
      <td>${t.bars_held}</td>
    </tr>`;
  }
  document.getElementById('trades').innerHTML = rows || '<tr><td colspan="6" style="color:#555;text-align:center">No trades yet</td></tr>';
}

async function refreshStatus() {
  try {
    const r = await fetch('/api/status?' + Date.now());
    if (r.ok) render(await r.json());
  } catch(e) {}
}

async function refreshLogs() {
  try {
    const r = await fetch('/api/logs?' + Date.now());
    if (!r.ok) return;
    const logs = await r.json();
    const feed = document.getElementById('logFeed');
    if (logs.length === 0) {
      feed.innerHTML = '<div style="color:#555;text-align:center;padding:20px">Waiting for first cycle...</div>';
      return;
    }
    let html = '';
    for (const l of logs) {
      const clr = COLORS[l.model] || '#888';
      // Convert UTC to KST
      const kstTime = l.time ? new Date(l.time).toLocaleTimeString('ko-KR', {timeZone:'Asia/Seoul', hour:'2-digit', minute:'2-digit'}) : '';
      const posStr = l.position === 1 ? '<span class="tag tag-long">LONG</span>' :
                     l.position === -1 ? '<span class="tag tag-short">SHORT</span>' :
                     '<span class="tag tag-flat">FLAT</span>';
      const isAction = l.event && (l.event.includes('ENTERED') || l.event.includes('CLOSED') || l.event.includes('REVERSED'));
      // Get fun dialog
      const dialog = getDialog(l.model, l.action, l.position);
      const evtStyle = isAction ? 'font-weight:bold;color:#fff' : 'color:#aaa';
      const shortName = (l.model || '').split(' ')[1] || l.model;
      html += `<div class="log-entry">
        <span class="log-time">${kstTime}</span>
        <span class="log-model" style="color:${clr}">${shortName}</span>
        <span class="log-event" style="${evtStyle}">"${dialog}"</span>
        <span class="log-pos">${posStr}</span>
        <span class="log-pnl ${pnlClass(l.pnl)}">${fmt(l.pnl)}</span>
      </div>`;
    }
    feed.innerHTML = html;
    feed.scrollTop = 0;
  } catch(e) {}
}

refreshStatus();
refreshLogs();
setInterval(refreshStatus, 10000);
setInterval(refreshLogs, 10000);

// Resize chart on window resize
window.addEventListener('resize', () => chart.applyOptions({ width: chartEl.clientWidth }));
</script>
</body>
</html>"""


LOG_FILE = BASE / "data" / "paper_all_log.jsonl"


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/candles"):
            self._serve_candles()
        elif self.path.startswith("/api/logs"):
            self._serve_logs()
        elif self.path.startswith("/api/status"):
            self._serve_status()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())

    def _serve_candles(self):
        """Fetch coin 30m candles from Binance and serve as JSON."""
        try:
            # Parse params from query
            limit = 200
            symbol = "ETHUSDT"
            if "limit=" in self.path:
                try:
                    limit = int(self.path.split("limit=")[1].split("&")[0])
                except ValueError:
                    pass
            if "coin=" in self.path:
                try:
                    symbol = self.path.split("coin=")[1].split("&")[0]
                except Exception:
                    pass

            url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=30m&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "TradingValue/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = json.loads(resp.read())

            candles = []
            for k in raw:
                candles.append({
                    "time": k[0] // 1000,  # ms -> seconds
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                })

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(candles).encode())
        except Exception as e:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"[]")

    def _serve_logs(self):
        """Serve last 100 log entries from paper_all_log.jsonl."""
        try:
            if LOG_FILE.exists():
                lines = LOG_FILE.read_text().strip().split("\n")
                # Last 100 entries, newest first
                entries = []
                for line in reversed(lines[-100:]):
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
                data = entries
            else:
                data = []
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        except Exception:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"[]")

    def _serve_status(self):
        try:
            data = json.loads(STATUS_FILE.read_text())
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        except Exception:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"timestamp":"","models":{}}')

    def log_message(self, *args):
        pass


def main():
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Dashboard: http://localhost:{PORT}")
    print(f"Reading: {STATUS_FILE}")
    print(f"Chart: ETHUSDT 30m candles from Binance Futures API")
    server.serve_forever()


if __name__ == "__main__":
    main()
