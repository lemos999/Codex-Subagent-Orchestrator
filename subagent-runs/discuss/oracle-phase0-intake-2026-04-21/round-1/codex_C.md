Reading prompt from stdin...
OpenAI Codex v0.121.0 (research preview)
--------
workdir: C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
model: gpt-5.4
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR, C:\Users\haj\.codex\memories]
reasoning effort: xhigh
reasoning summaries: none
session id: 019dadfe-1014-78e0-86f8-165351477b7c
--------
user
# Your Role: **Codex gpt-5.4 (C) — 비용/속도 효율 관점**

당신은 운영 비용과 실행 속도를 책임지는 시스템 엔지니어입니다. 위 Phase 0 요약을 기준으로:
- 1틱당 연산 비용 — 현재 V3 (port 8898, 7 variants × context k-NN)에 Oracle까지 얹으면 한 Windows 머신에서 CPU/RAM 감당 가능한가?
- ccxt OHLCV 폴링 주기 — Oracle이 다른 2개 모델과 같은 데이터를 중복 fetch하면 rate-limit/대역폭 문제는?
- state npz 파일 쓰기 주기 — context memory가 커질수록 save/load 시간 증가. 10k+ trades 축적 시 허용 가능?
- 대시보드 프록시 타임아웃 — Oracle의 추론 시간이 길면 127.0.0.1 HTTP 응답 지연 → dashboard가 멈춘 것처럼 보일 수 있다. 상한은?

비용 엔지니어의 계산적 시각으로 판정하라.

---

# Discussion Topic

**Oracle 예측 엔진 (V2 재설계) Phase 0 Intake 요약이 설계 착수 조건으로 적합한가?**

## 배경

V2 Prediction Engine (`scripts/v2.py`, port 8897)은 3규칙 구조로 운영 중:
1. 예측 정확도 보상 (SGD ridge, 맞추면 ↑ / 틀리면 ↓)
2. 메모리 엔트로피 균등화 (context 가중치를 uniform distribution으로 감쇠)
3. 수익 극대화 (trust score로 게이팅)

결과: **-13.13%, 정확도 52%**. 근본 원인 진단 — 규칙 2(엔트로피 균등)가 학습된 가중치를 계속 uniform으로 끌어내려 **학습과 반대로 작동**. 단일 선형 모델이라 context별 신뢰도 분화 불가.

## 사용자 요구 (원문)
> "예측을 맞췄을 때 점수를 올리고, 못 맞추면 점수를 내립니다. 점수 높게 받기 위해 과거 예측치를 분석해서 높게 받도록 해야 합니다."

→ 핵심 원칙: **좋은 예측 패턴 강화 + 나쁜 예측 패턴 소거**. 균등 엔트로피는 금지.

## Phase 0 Intake 요약 (검증 대상)

### 1. 도메인
`software` 팩 사용 (예측 엔진 = 소프트웨어 설계 문제)

### 2. 스코프 (린)
- 팀: 사용자 1인 + Claude(설계/리뷰) + Codex(구현)
- 일정: 5일 내 기동, **승률 67%+ / 5일 +4% 목표**
- 리소스: 기존 V2/V3/TriArb 인프라 재활용

### 3. 제약
- **기술 스택**: Python 3.12, ccxt + numpy + pandas (신규 의존성 금지)
- **통합**: dashboard_unified.py MODELS dict에 `"oracle"` 키 추가 가능
- **상태/로그**: `data/oracle_state.npz` + `data/oracle.jsonl` (V3/TriArb와 일관)
- **포트**: 8897(V2 덮어쓰기) 또는 신규(8901?) — Phase 3 Decision Card에서 확정
- **v2.py 처리**: 덮어쓰기 vs 신규 `oracle.py` — Phase 3에서 확정
- **원칙**: `feedback_self_learning_algorithm.md` — 좋은 패턴 강화 + 나쁜 패턴 소거, 균등 엔트로피 금지
- **네트워크**: 로컬 HTTP는 `127.0.0.1` 하드코딩 (Windows IPv6 회피)

### Ambiguity Gate 판정
- Phase 0 통과 → Phase 1 (Charter) 진입 예정
- 포트/파일처리 2항목은 Phase 3 Decision Card로 지연

## 참고 시스템 (현재 운영 중)
- **V3** (`scripts/v3.py`, port 8898): Parker Brooks + self-learning + HTF. 6차원 context k-NN, warmup 30, EV<-0.5R & n≥20 → 블랙리스트. 7 variants (3m/5m/15m/30m + aggressive/conservative + control).
- **TriArb** (`scripts/triarb.py`, port 8899): 2-leg delta-neutral pairs ratio. 4 pairs (ETHBTC/SOLBTC/SOLETH/XRPBTC), z-score 회귀 + correlation gate + HTF bias. 5 variants.
- **Dashboard** (`scripts/dashboard_unified.py`, port 8900): 3모델 프록시 + variants 비교.

## 검증 질문 (답변 필수)

1. **Phase 1 Charter 진입 가능?** — Phase 0 요약이 Ambiguity Gate 통과에 충분한가?
2. **누락된 제약/모호성?** — Phase 1 전에 반드시 확정해야 할 항목 있나?
3. **Ambiguity Gate 적절?** — 포트/파일처리를 Phase 3로 지연하는 결정이 타당한가?
4. **설계 방향에 근본 결함?** — Oracle 접근이 V2 문제를 해결할까, 아니면 V2 수정이 더 나을까?

## 출력 형식

응답은 아래 구조로:
1. **Position**: 핵심 주장 (한 문단)
2. **Reasoning**: 근거 (2-4 bullet)
3. **Concerns**: 잠재적 리스크/함정 (2-4 bullet)
4. **Recommendation**: 권장 다음 단계 (구체적)

마지막 줄에 반드시:
`[POSITION: 한 줄 요약]`

30줄 이내로 작성.

codex
요청은 Oracle Phase 0 요약이 설계 착수 조건으로 충분한지, 특히 비용·속도 관점에서 병목이 없는지 판정하는 것입니다. 먼저 필수 프로젝트 상태와 인덱스를 갱신하고, 이어서 `v2.py`/`v3.py`/`triarb.py`/`dashboard_unified.py`의 실제 동작 비용 지점을 확인하겠습니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'node workspace-knowledge-index/dist/index.js index' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content project-status/current.md' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "rg --files scripts data project-status . | rg \"(v2\\.py|v3\\.py|triarb\\.py|dashboard_unified\\.py|feedback_self_learning_algorithm\\.md|oracle|Phase 0|phase 0|charter)\"" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
2026-04-21T03:03:37.276839Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 0.4 seconds
Output:
node:internal/modules/cjs/loader:1451
  throw err;
  ^

Error: Cannot find module 'C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value\workspace-knowledge-index\dist\index.js'
    at Module._resolveFilename (node:internal/modules/cjs/loader:1448:15)
    at defaultResolveImpl (node:internal/modules/cjs/loader:1059:19)
    at resolveForCJSWithHooks (node:internal/modules/cjs/loader:1064:22)
    at Module._load (node:internal/modules/cjs/loader:1234:25)
    at TracingChannel.traceSync (node:diagnostics_channel:328:14)
    at wrapModuleLoad (node:internal/modules/cjs/loader:245:24)
    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)
    at node:internal/main/run_main_module:33:47 {
  code: 'MODULE_NOT_FOUND',
  requireStack: []
}

Node.js v24.13.1

 exited 1 in 395ms:
node:internal/modules/cjs/loader:1451
  throw err;
  ^

Error: Cannot find module 'C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value\workspace-knowledge-index\dist\index.js'
    at Module._resolveFilename (node:internal/modules/cjs/loader:1448:15)
    at defaultResolveImpl (node:internal/modules/cjs/loader:1059:19)
    at resolveForCJSWithHooks (node:internal/modules/cjs/loader:1064:22)
    at Module._load (node:internal/modules/cjs/loader:1234:25)
    at TracingChannel.traceSync (node:diagnostics_channel:328:14)
    at wrapModuleLoad (node:internal/modules/cjs/loader:245:24)
    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)
    at node:internal/main/run_main_module:33:47 {
  code: 'MODULE_NOT_FOUND',
  requireStack: []
}

Node.js v24.13.1

2026-04-21T03:03:37.399447Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 0.5 seconds
Output:
scripts\_smoke_triarb.py
scripts\validate_v2.py
scripts\v3.py
scripts\v2.py
scripts\triarb.py
scripts\optimize_v3.py
scripts\optimize_v2.py
scripts\dashboard_unified.py
.\scripts\dashboard_unified.py
.\scripts\optimize_v3.py
.\scripts\optimize_v2.py
.\scripts\v2.py
.\scripts\triarb.py
.\scripts\validate_v2.py
.\scripts\v3.py
.\scripts\_smoke_triarb.py
rg: project-status: 지정된 파일을 찾을 수 없습니다. (os error 2)

 exited 1 in 516ms:
scripts\_smoke_triarb.py
scripts\validate_v2.py
scripts\v3.py
scripts\v2.py
scripts\triarb.py
scripts\optimize_v3.py
scripts\optimize_v2.py
scripts\dashboard_unified.py
.\scripts\dashboard_unified.py
.\scripts\optimize_v3.py
.\scripts\optimize_v2.py
.\scripts\v2.py
.\scripts\triarb.py
.\scripts\validate_v2.py
.\scripts\v3.py
.\scripts\_smoke_triarb.py
rg: project-status: 지정된 파일을 찾을 수 없습니다. (os error 2)

2026-04-21T03:03:37.426839Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 0.5 seconds
Output:
Get-Content : 'C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value\project-status\current.md' 경로는 존재하지 않
으므로 찾을 수 없습니다.
위치 줄:2 문자:1
+ Get-Content project-status/current.md
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:\Users\haj\pr...atus\current.md:String) [Get-Content], ItemNotFoundEx 
   ception
    + FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.GetContentCommand
 

 exited 1 in 545ms:
Get-Content : 'C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value\project-status\current.md' 경로는 존재하지 않
으므로 찾을 수 없습니다.
위치 줄:2 문자:1
+ Get-Content project-status/current.md
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:\Users\haj\pr...atus\current.md:String) [Get-Content], ItemNotFoundEx 
   ception
    + FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.GetContentCommand
 

codex
필수 상태 파일과 WKI 경로는 현재 워크스페이스에 없습니다. 지정된 규칙은 확인했지만 실제 파일이 없어서, 저장소 실체 기준으로 스크립트와 런타임 경로를 직접 읽어 비용 추정을 진행하겠습니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-ChildItem -Force' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "rg -n \"MODELS|timeout|requests|get\\(|ccxt|fetch_ohlcv|npz|savez|jsonl|k-NN|variant|8898|8899|8900|127\\.0\\.0\\.1|ThreadingHTTPServer|HTTPServer|BaseHTTPRequestHandler\" scripts\\v3.py scripts\\v2.py scripts\\triarb.py scripts\\dashboard_unified.py" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 343ms:
scripts\v2.py:33:for _pkg, _imp in [("ccxt", "ccxt")]:
scripts\v2.py:40:import ccxt
scripts\v2.py:46:STATE_PATH = DATA_DIR / "v2_state.npz"
scripts\v2.py:47:LOG_PATH = DATA_DIR / "v2.jsonl"
scripts\v2.py:480:class DashboardHandler(http.server.BaseHTTPRequestHandler):
scripts\v2.py:608:        self.exchange = ccxt.bybit({"enableRateLimit": True})
scripts\v2.py:634:            return float(info.get("fundingRate", 0) or 0)
scripts\v2.py:640:            ohlcv = self.exchange.fetch_ohlcv(self._symbol(asset), "1m", limit=HISTORY_BARS)
scripts\v2.py:651:            ohlcv = self.exchange.fetch_ohlcv(self._symbol(asset), "1m", limit=3)
scripts\v2.py:706:            funding = self._last_funding.get(asset, 0.0)
scripts\v2.py:755:                    pos = self.pm.positions.get(asset)
scripts\v2.py:852:            np.savez_compressed(STATE_PATH, **state)
scripts\v2.py:882:        server = http.server.HTTPServer(("0.0.0.0", self.port), DashboardHandler)
scripts\dashboard_unified.py:5:- V3 Parker Brooks + Self-Learn (port 8898)
scripts\dashboard_unified.py:6:- TriArb Pairs Ratio (port 8899)
scripts\dashboard_unified.py:9:    py -3.12 scripts/dashboard_unified.py [--port 8900]
scripts\dashboard_unified.py:12:    http://127.0.0.1:8900
scripts\dashboard_unified.py:23:PORT = 8900
scripts\dashboard_unified.py:26:MODELS = {
scripts\dashboard_unified.py:28:    "v3":         {"port": 8898, "name": "V3 Parker Brooks + Self-Learn",  "color": "#aa66ff"},
scripts\dashboard_unified.py:29:    "triarb":     {"port": 8899, "name": "TriArb (Pairs Ratio)",           "color": "#66ffaa"},
scripts\dashboard_unified.py:36:            f"http://127.0.0.1:{port}/api/state",
scripts\dashboard_unified.py:39:        with urllib.request.urlopen(req, timeout=3) as resp:
scripts\dashboard_unified.py:45:class Handler(http.server.BaseHTTPRequestHandler):
scripts\dashboard_unified.py:73:            for model_id, info in MODELS.items():
scripts\dashboard_unified.py:82:        elif key in MODELS:
scripts\dashboard_unified.py:83:            state = fetch_model_state(MODELS[key]["port"])
scripts\dashboard_unified.py:367:  const variants=s.variants||{};
scripts\dashboard_unified.py:371:  // Header summary: best variant + total trades
scripts\dashboard_unified.py:373:  for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:382:  let html='<div class="model-section"><div class="model-hdr" style="border-left:3px solid '+color+'"><h2><span class="'+(online?'live':'live offline')+'"></span> '+d.name+' <span style="font-size:10px;color:#aa66ff;margin-left:6px">VWAP/EMA9/VP + Context k-NN + '+htfTF+' HTF Bias | 수수료 0.21% RT | Risk 0.5%/trade</span></h2><div class="stats">';
scripts\dashboard_unified.py:401:  // Variants grid — one card per variant
scripts\dashboard_unified.py:402:  html+='<div style="display:grid;grid-template-columns:repeat('+Object.keys(variants).length+',1fr);gap:8px;margin-bottom:12px">';
scripts\dashboard_unified.py:403:  for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:424:  html+='<div style="margin-top:8px"><div style="font-size:10px;color:#555;margin-bottom:3px;text-transform:uppercase">신호 필터링 깔때기 (각 variant 누적)</div>';
scripts\dashboard_unified.py:426:  for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:445:  for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:461:  // PnL charts per variant (compact)
scripts\dashboard_unified.py:462:  html+='<div style="display:grid;grid-template-columns:repeat('+Object.keys(variants).length+',1fr);gap:6px;margin-top:10px">';
scripts\dashboard_unified.py:463:  for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:468:  // Positions (all variants)
scripts\dashboard_unified.py:471:  for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:484:  for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:485:    (v.trade_log||[]).forEach(t=>{allTrades.push({...t,variant:vn});});
scripts\dashboard_unified.py:490:    html+='<div style="margin-top:10px"><div style="font-size:11px;color:#888;margin-bottom:4px;font-weight:bold">최근 거래 (전체 variant)</div>';
scripts\dashboard_unified.py:494:      html+='<div class="tlog-e"><span class="dim">['+t.variant.replace('v3-','')+']</span> <span class="'+(t.net>0?'grn':'red')+'" style="font-weight:bold">'+t.dir+'</span> '+t.asset+' $'+t.entry+' → $'+t.exit+' <span class="'+(r>0?'grn':'red')+'">'+(r>=0?'+':'')+r.toFixed(2)+'R</span> <span class="dim">['+t.reason+']</span> 잔고='+$(t.capital)+'</div>';
scripts\dashboard_unified.py:506:  const variants=s.variants||{};
scripts\dashboard_unified.py:517:  for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:545:  html+='<div style="display:grid;grid-template-columns:repeat('+Math.max(1,Object.keys(variants).length)+',1fr);gap:8px;margin-bottom:12px">';
scripts\dashboard_unified.py:546:  for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:564:  for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:583:  for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:595:  html+='<div style="display:grid;grid-template-columns:repeat('+Math.max(1,Object.keys(variants).length)+',1fr);gap:6px;margin-top:10px">';
scripts\dashboard_unified.py:596:  for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:602:  for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:614:  for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:615:    (v.trade_log||[]).forEach(t=>{allTrades.push({...t,variant:vn});});
scripts\dashboard_unified.py:620:    html+='<div style="margin-top:10px"><div style="font-size:11px;color:#888;margin-bottom:4px;font-weight:bold">최근 거래 (전체 variant)</div><div class="tlog">';
scripts\dashboard_unified.py:623:      html+='<div class="tlog-e"><span class="dim">['+t.variant.replace('triarb-','')+']</span> <span class="'+(net>0?'grn':'red')+'" style="font-weight:bold">'+t.dir+'</span> '+(t.pair_id||t.asset)+' '+num(t.entry,6)+' → '+num(t.exit,6)+' <span class="'+(r>0?'grn':'red')+'">'+(r>=0?'+':'')+r.toFixed(2)+'R</span> net=<span class="'+(net>0?'grn':'red')+'">$'+net.toFixed(2)+'</span> <span class="dim">['+t.reason+']</span></div>';
scripts\dashboard_unified.py:659:    // Draw V3 per-variant PnL charts
scripts\dashboard_unified.py:662:      const variants=v3d.state.variants||{};
scripts\dashboard_unified.py:663:      for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:670:    // Draw TriArb per-variant PnL charts
scripts\dashboard_unified.py:673:      const variants=td.state.variants||{};
scripts\dashboard_unified.py:674:      for(const[vn,v]of Object.entries(variants)){
scripts\dashboard_unified.py:695:    server = http.server.HTTPServer(("0.0.0.0", args.port), Handler)
scripts\dashboard_unified.py:697:    proxy_desc = ", ".join(f"{v['name']} :{v['port']}" for v in MODELS.values())
scripts\v3.py:5:  2. Context Memory (k-NN based EV tracking) — learns good/bad contexts
scripts\v3.py:7:  4. Multi-variant paper trading (5 variants concurrently)
scripts\v3.py:13:    py -3.12 scripts/v3.py [--assets ETH,BTC,SOL,XRP] [--port 8898]
scripts\v3.py:16:    http://localhost:8898
scripts\v3.py:35:for _pkg, _imp in [("ccxt", "ccxt")]:
scripts\v3.py:42:import ccxt
scripts\v3.py:48:STATE_PATH = DATA_DIR / "v3_state.npz"
scripts\v3.py:49:LOG_PATH = DATA_DIR / "v3.jsonl"
scripts\v3.py:51:DASH_PORT = 8898
scripts\v3.py:84:# Execution TFs expanded per WebSearch findings: 3m/5m/15m/30m + 5m param variants.
scripts\v3.py:404:    """Stores past trades and scores new contexts via k-NN EV.
scripts\v3.py:411:    def __init__(self, variant_name: str):
scripts\v3.py:412:        self.variant_name = variant_name
scripts\v3.py:521:# Position + Position Manager (per-variant)
scripts\v3.py:539:    """Position manager per variant."""
scripts\v3.py:541:    def __init__(self, variant_name: str, config: dict):
scripts\v3.py:542:        self.name = variant_name
scripts\v3.py:550:        self.memory = ContextMemory(variant_name)
scripts\v3.py:704:# V3 Engine (main loop, manages all variants)
scripts\v3.py:710:        self.exchange = ccxt.bybit({"enableRateLimit": True})
scripts\v3.py:711:        # Execution timeframes used by any variant (derived from config)
scripts\v3.py:719:        self.variants: dict[str, VariantPM] = {
scripts\v3.py:733:            ohlcv = self.exchange.fetch_ohlcv(self._symbol(asset), timeframe, limit=limit)
scripts\v3.py:794:    def _process_variant_on_bar(self, variant_name: str, asset: str,
scripts\v3.py:796:        """Evaluate entries+exits for one variant on a new bar.
scripts\v3.py:799:        If variant has htf_filter=True, neutral blocks all entries and
scripts\v3.py:802:        pm = self.variants[variant_name]
scripts\v3.py:817:        if cfg.get("htf_filter", False) and htf_bias_now == "neutral":
scripts\v3.py:831:        if cfg.get("htf_filter", False):
scripts\v3.py:885:            print(f"  [{variant_name} {asset}] {direction.upper()} @{entry_price:.2f} "
scripts\v3.py:891:              f"| {len(VARIANTS_CONFIG)} variants")
scripts\v3.py:911:                price_src = self.history.get(first_tf, {}).get(asset)
scripts\v3.py:940:        # --- Execution TF refresh (each variant uses its own TF) ---
scripts\v3.py:943:                divisor = self._TF_POLL_DIVISOR.get(tf, 1)
scripts\v3.py:952:                prev_ts = self.last_bar_ts[tf].get(asset)
scripts\v3.py:955:                # New closed bar — append and fire variants
scripts\v3.py:966:                htf_now = self.htf_bias.get(asset, "neutral")
scripts\v3.py:969:                        self._process_variant_on_bar(
scripts\v3.py:983:            "variants": {},
scripts\v3.py:985:        for name, pm in self.variants.items():
scripts\v3.py:986:            log_entry["variants"][name] = {
scripts\v3.py:1003:        for name, pm in self.variants.items():
scripts\v3.py:1008:        variants_data = {}
scripts\v3.py:1009:        for name, pm in self.variants.items():
scripts\v3.py:1011:            variants_data[name] = {
scripts\v3.py:1043:            "variants": variants_data,
scripts\v3.py:1045:            "variant_configs": VARIANTS_CONFIG,
scripts\v3.py:1058:            for name, pm in self.variants.items():
scripts\v3.py:1062:            np.savez_compressed(STATE_PATH, **state)
scripts\v3.py:1066:            for name, pm in self.variants.items():
scripts\v3.py:1081:            for name, pm in self.variants.items():
scripts\v3.py:1094:                mem = blob.get("memory", {})
scripts\v3.py:1095:                tlogs = blob.get("trade_logs", {})
scripts\v3.py:1096:                for name, pm in self.variants.items():
scripts\v3.py:1097:                    for rec in mem.get(name, []):
scripts\v3.py:1099:                    pm.trade_log = tlogs.get(name, [])
scripts\v3.py:1100:            print(f"  [load] tick={self.tick_count} variants restored")
scripts\v3.py:1109:        server = http.server.HTTPServer(("0.0.0.0", self.port), DashboardHandler)
scripts\v3.py:1128:# Dashboard (API only — unified dashboard on 8900 renders UI)
scripts\v3.py:1130:class DashboardHandler(http.server.BaseHTTPRequestHandler):
scripts\triarb.py:31:for _pkg, _imp in [("ccxt", "ccxt")]:
scripts\triarb.py:39:import ccxt
scripts\triarb.py:46:STATE_PATH = DATA_DIR / "triarb_state.npz"
scripts\triarb.py:47:LOG_PATH = DATA_DIR / "triarb.jsonl"
scripts\triarb.py:50:DASH_PORT = 8899
scripts\triarb.py:118:    # "daily" variant는 1h TF 기반 장기 시각 진입. 진짜 1d(일봉) 아님.
scripts\triarb.py:337:    if cfg.get("htf_filter", False) and htf_status in ("strong_bull", "strong_bear"):
scripts\triarb.py:341:    z = float(metrics.get("z", float("nan")))
scripts\triarb.py:342:    z_prev = float(metrics.get("z_prev", float("nan")))
scripts\triarb.py:343:    z_velocity = float(metrics.get("z_velocity", float("nan")))
scripts\triarb.py:344:    cv = float(metrics.get("cv", float("nan")))
scripts\triarb.py:361:    if cfg.get("htf_filter", False) and htf_status in ("strong_bull", "strong_bear"):
scripts\triarb.py:365:    z = float(metrics.get("z", float("nan")))
scripts\triarb.py:366:    z_prev = float(metrics.get("z_prev", float("nan")))
scripts\triarb.py:367:    z_velocity = float(metrics.get("z_velocity", float("nan")))
scripts\triarb.py:368:    cv = float(metrics.get("cv", float("nan")))
scripts\triarb.py:424:    def __init__(self, variant_name: str):
scripts\triarb.py:425:        self.variant_name = variant_name
scripts\triarb.py:538:    def __init__(self, variant_name: str, config: dict[str, Any]):
scripts\triarb.py:539:        self.name = variant_name
scripts\triarb.py:547:        self.memory = ContextMemory(variant_name)
scripts\triarb.py:573:        return sum(1 for t in self.trade_log if t.get("net", 0) > 0)
scripts\triarb.py:591:        if self.config.get("memory", False) and self.memory.is_blacklisted(ctx, direction):
scripts\triarb.py:596:        if self.config.get("memory", False):
scripts\triarb.py:634:        z = float(metrics.get("z", float("nan")))
scripts\triarb.py:635:        velocity = float(metrics.get("z_velocity", float("nan")))
scripts\triarb.py:676:        exit_ratio = float(metrics.get("ratio", float("nan")))
scripts\triarb.py:702:                "exit_z": round(float(metrics.get("z", float("nan"))), 3)
scripts\triarb.py:703:                if np.isfinite(metrics.get("z", float("nan")))
scripts\triarb.py:767:        self.exchange = ccxt.bybit({"enableRateLimit": True})
scripts\triarb.py:775:            key=lambda tf: _TF_ORDER.get(tf, 999),
scripts\triarb.py:780:        self.variants = {name: VariantPM(name, cfg) for name, cfg in VARIANTS_CONFIG.items()}
scripts\triarb.py:801:            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
scripts\triarb.py:821:        print(f"[TriArb] Memory warmup: {MEMORY_WARMUP_TRADES} trades | {len(self.variants)} variants")
scripts\triarb.py:841:            preview = self.pair_metrics.get("5m", {}).get(pair_id)
scripts\triarb.py:842:            metrics = preview.get(20) if preview else None
scripts\triarb.py:843:            corr = self.pair_corr.get(pair_id, float("nan"))
scripts\triarb.py:856:        df1 = self.history.get(tf, {}).get(leg1_sym)
scripts\triarb.py:857:        df2 = self.history.get(tf, {}).get(leg2_sym)
scripts\triarb.py:915:        z = float(metrics.get("z", 0.0))
scripts\triarb.py:920:            spread_velocity=float(metrics.get("z_velocity", 0.0)),
scripts\triarb.py:939:    def _process_variant_on_bar(self, variant_name: str, pair_id: str):
scripts\triarb.py:940:        pm = self.variants[variant_name]
scripts\triarb.py:946:        metrics_all = self.pair_metrics.get(tf, {}).get(pair_id)
scripts\triarb.py:949:        metrics = metrics_all.get(cfg["ratio_lookback_bars"])
scripts\triarb.py:952:        if any(not np.isfinite(metrics.get(k, float("nan"))) for k in ("z", "z_velocity", "cv")):
scripts\triarb.py:993:                    f"  [{variant_name} {pair_id}] SHORT_RATIO z={metrics['z']:.2f} "
scripts\triarb.py:1018:                    f"  [{variant_name} {pair_id}] LONG_RATIO z={metrics['z']:.2f} "
scripts\triarb.py:1043:            divisor = self._TF_POLL_DIVISOR.get(tf, 1)
scripts\triarb.py:1053:                prev_ts = self.last_bar_ts[tf].get(symbol)
scripts\triarb.py:1062:                if latest_pair_ts is None or latest_pair_ts == self.last_pair_ts[tf].get(pair_id):
scripts\triarb.py:1068:                        self._process_variant_on_bar(name, pair_id)
scripts\triarb.py:1079:            metrics_all = self.pair_metrics.get("5m", {}).get(pair_id)
scripts\triarb.py:1080:            metrics = metrics_all.get(20) if metrics_all else None
scripts\triarb.py:1081:            if metrics and np.isfinite(metrics.get("z", float("nan"))):
scripts\triarb.py:1083:        variant_parts = [
scripts\triarb.py:1085:            for name, pm in self.variants.items()
scripts\triarb.py:1088:        print(f"  [tick {self.tick_count}] " + " | ".join(variant_parts))
scripts\triarb.py:1095:                    "corr": _finite_or_none(self.pair_corr.get(pid)),
scripts\triarb.py:1097:                        (self.pair_metrics.get("5m", {}).get(pid) or {}).get(20, {}).get("z")
scripts\triarb.py:1102:            "variants": {
scripts\triarb.py:1113:                for name, pm in self.variants.items()
scripts\triarb.py:1120:        variants_data = {}
scripts\triarb.py:1121:        for name, pm in self.variants.items():
scripts\triarb.py:1122:            variants_data[name] = {
scripts\triarb.py:1164:            metrics_all = self.pair_metrics.get("5m", {}).get(pair_id)
scripts\triarb.py:1165:            metrics = metrics_all.get(20) if metrics_all else None
scripts\triarb.py:1168:                    "z": _finite_or_none(metrics.get("z")),
scripts\triarb.py:1169:                    "ratio": _finite_or_none(metrics.get("ratio")),
scripts\triarb.py:1170:                    "cv": _finite_or_none(metrics.get("cv")),
scripts\triarb.py:1189:            "variants": variants_data,
scripts\triarb.py:1190:            "variant_configs": {name: pm.config for name, pm in self.variants.items()},
scripts\triarb.py:1214:            for name, pm in self.variants.items():
scripts\triarb.py:1218:            np.savez_compressed(STATE_PATH, **state)
scripts\triarb.py:1221:            for name, pm in self.variants.items():
scripts\triarb.py:1251:            for name, pm in self.variants.items():
scripts\triarb.py:1261:                for name, pm in self.variants.items():
scripts\triarb.py:1262:                    for rec in blob.get("memory", {}).get(name, []):
scripts\triarb.py:1264:                    pm.trade_log = blob.get("trade_logs", {}).get(name, [])
scripts\triarb.py:1265:                    for raw_pos in blob.get("positions", {}).get(name, []):
scripts\triarb.py:1266:                        ctx_raw = raw_pos.get("entry_context", {})
scripts\triarb.py:1270:            print(f"  [load] TriArb tick={self.tick_count} variants restored")
scripts\triarb.py:1278:        server = http.server.HTTPServer(("0.0.0.0", self.port), DashboardHandler)
scripts\triarb.py:1299:class DashboardHandler(http.server.BaseHTTPRequestHandler):

 succeeded in 433ms:


    디렉터리: C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value


Mode                 LastWriteTime         Length Name                                                                 
----                 -------------         ------ ----                                                                 
d-----        2026-04-21  오전 11:42                .knowledge                                                           
d-----        2026-03-20   오후 2:08                .pytest_cache                                                        
d-----        2026-04-01   오후 8:49                archive                                                              
d-----        2026-03-21   오후 9:35                config                                                               
d-----        2026-04-21  오전 11:28                data                                                                 
d-----        2026-04-21  오전 10:14                docs                                                                 
d-----        2026-04-08  오전 11:25                html                                                                 
d-----        2026-03-20  오전 11:42                reusable-components                                                  
d-----        2026-04-21  오전 11:28                scripts                                                              
d-----        2026-03-21  오전 12:01                tests                                                                
-a----        2026-03-20  오전 11:32          19435 auto_trading_state_machine_design.md                                 
-a----        2026-04-02  오전 10:23           3324 breakthrough-guide.md                                                
-a----        2026-03-20  오전 12:20          22744 coin_strategy_spec.md                                                
-a----        2026-03-20  오전 11:31          21940 coin_strategy_spec_v2.md                                             
-a----        2026-04-05   오후 8:50           4671 limits-history.md                                                    
-a----        2026-03-20   오후 2:14            497 pyproject.toml                                                       
-a----        2026-03-20  오전 11:43          15458 README.md                                                            
-a----        2026-04-08   오후 1:59           2388 RESUME.md                                                            
-a----        2026-03-20  오전 11:43           6320 reusable_components_guide.md                                         
-a----        2026-04-20   오후 3:10         282771 uv.lock                                                              



codex
이제 실제 비용을 좌우하는 상수만 뽑습니다. 폴링 주기, 저장 주기, 메모리 구조, 프록시 timeout을 확인하면 Oracle 추가 시 한 머신 한계가 대략 계산됩니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "@'
from pathlib import Path
for path, start, end in [
 ('scripts/v3.py',1,220),
 ('scripts/v3.py',404,520),
 ('scripts/v3.py',704,1115),
 ('scripts/triarb.py',1,220),
 ('scripts/triarb.py',767,1285),
 ('scripts/dashboard_unified.py',1,120),
 ('scripts/v2.py',600,900),
]:
    print(f'===== {path}:{start}-{end} =====')
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    for i in range(start-1, min(end, len(lines))):
        print(f'{i+1}: {lines[i]}')
'@ | python -" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-ChildItem data | Select-Object Name,Length,LastWriteTime' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
2026-04-21T03:03:55.567983Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 0.4 seconds
Output:
python : 'python' 용어가 cmdlet, 함수, 스크립트 파일 또는 실행할 수 있는 프로그램 이름으로 인식되지 않습니다. 이름이 정확한지 확인하고 경로가 포함된 경우 경로가 올바른지 검증한 다음 다시 
시도하십시오.
위치 줄:17 문자:6
+ '@ | python -
+      ~~~~~~
    + CategoryInfo          : ObjectNotFound: (python:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 

 exited 1 in 421ms:
python : 'python' 용어가 cmdlet, 함수, 스크립트 파일 또는 실행할 수 있는 프로그램 이름으로 인식되지 않습니다. 이름이 정확한지 확인하고 경로가 포함된 경우 경로가 올바른지 검증한 다음 다시 
시도하십시오.
위치 줄:17 문자:6
+ '@ | python -
+      ~~~~~~
    + CategoryInfo          : ObjectNotFound: (python:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 

 succeeded in 465ms:

Name                        Length     LastWriteTime         
----                        ------     -------------         
auto_train_results                     2026-03-26 오후 8:37:08 
charts                                 2026-03-22 오전 2:14:16 
checkpoints                            2026-03-22 오전 12:23:46
logs                                   2026-04-21 오전 10:55:08
btc_funding_cache.json      1304912    2026-04-01 오후 8:46:01 
conviction.log              14241      2026-04-07 오후 5:45:52 
conviction_amzn.json        2512       2026-04-07 오전 4:00:29 
conviction_btc.json         41598      2026-04-07 오후 5:45:52 
conviction_eth.json         37792      2026-04-07 오후 5:45:52 
conviction_nvda.json        3829       2026-04-07 오전 4:00:28 
discuss_prompt.md           3169       2026-04-13 오후 9:45:51 
discuss_rule2.md            3998       2026-04-14 오후 1:29:06 
dl_amzn_cnn.pt              177236     2026-04-05 오전 12:42:03
dl_btc_lstm.pt              834245     2026-04-05 오후 5:02:55 
dl_btc_patchtst.pt          913309     2026-04-05 오후 5:48:55 
dl_btc_train.log            9758       2026-04-05 오후 5:02:55 
dl_nvda_train.log           4918       2026-04-05 오전 12:48:44
dl_nvda_transformer.pt      474946     2026-04-05 오전 12:48:44
dl_patchtst_train.log       10108      2026-04-05 오후 5:48:55 
model_history.jsonl         3072       2026-03-31 오후 10:36:20
opt_amzn.log                761        2026-04-01 오후 5:05:12 
opt_amzn_v2.log             1214       2026-04-01 오후 6:41:17 
opt_btc.log                 2397       2026-04-01 오후 5:23:43 
opt_btc_funding.log         1268       2026-04-01 오후 8:49:37 
opt_btc_v2.log              1225       2026-04-01 오후 6:50:59 
opt_nvda.log                777        2026-04-01 오후 5:05:12 
opt_nvda_regime.log         1106       2026-04-01 오후 8:46:00 
opt_nvda_v2.log             1236       2026-04-01 오후 6:41:20 
paper_all.log               545        2026-04-02 오전 7:51:24 
paper_all_log.jsonl         44551      2026-03-27 오전 11:35:22
paper_btc_amzn.log          350        2026-04-02 오전 12:53:54
paper_btc_state.json        445        2026-04-01 오후 4:45:57 
paper_btc_v2_state.json     708        2026-04-02 오전 1:00:55 
paper_hybrid.log            721        2026-04-02 오전 1:00:56 
paper_hybrid_state.json     12573      2026-04-02 오전 1:00:56 
paper_multi.log             433        2026-04-01 오후 4:42:34 
paper_nvda.log              357        2026-04-02 오전 12:53:50
paper_nvda_state.json       814        2026-04-02 오전 12:53:52
paper_unified_amzn.json     836        2026-04-02 오전 1:15:08 
paper_unified_btc.json      4155       2026-04-02 오전 8:15:25 
paper_unified_eth.json      4148       2026-04-02 오전 8:15:25 
paper_unified_nvda.json     835        2026-04-02 오전 1:15:08 
params_amzn.json            480        2026-04-01 오후 5:05:12 
params_amzn_v2.json         388        2026-04-01 오후 6:41:17 
params_amzn_v3.json         182        2026-04-01 오후 8:35:15 
params_btc_funding.json     238        2026-04-01 오후 8:49:37 
params_btc_v2.json          387        2026-04-01 오후 6:50:59 
params_btc_v3.json          176        2026-04-01 오후 8:35:17 
params_nvda.json            477        2026-04-01 오후 5:05:12 
params_nvda_regime.json     240        2026-04-01 오후 8:46:00 
params_nvda_v2.json         398        2026-04-01 오후 6:41:20 
params_nvda_v3.json         183        2026-04-01 오후 8:35:14 
params_pairs_btc_eth.json   256        2026-04-01 오후 8:53:32 
research_10pct_monthly.json 3838       2026-04-01 오후 8:51:33 
rl_model_c_1.2M             7685647    2026-03-24 오전 10:07:12
rl_model_c_1.4M             7685647    2026-03-24 오전 10:31:01
rl_model_c_1.6M             7685648    2026-03-24 오전 10:57:35
rl_model_c_1.8M             7685648    2026-03-24 오전 11:38:52
rl_model_c_2.0M             7685647    2026-03-24 오후 12:09:46
sim_1m.sqlite               1621860352 2026-03-28 오전 3:39:28 
triarb.jsonl                20832      2026-04-21 오후 12:02:34
triarb_memory.json          334        2026-04-21 오후 12:00:33
triarb_state.npz            4537       2026-04-21 오후 12:00:33
v2.jsonl                    331783     2026-04-21 오후 12:02:12
v2_state.npz                14669      2026-04-21 오후 12:00:11
v3.jsonl                    543549     2026-04-21 오전 11:59:52
v3_memory.json              11899      2026-04-21 오후 12:01:54
v3_state.npz                4791       2026-04-21 오후 12:01:54
xgb_direction_model.json    215285     2026-04-01 오전 11:16:26
xgb_retrain_history.jsonl   235        2026-04-01 오전 11:16:26
_discuss_spec.json          1506       2026-03-31 오후 9:50:21 



codex
`data/` 실파일 크기를 보니 현재 상태 저장 자체는 아직 가볍습니다. 이제 저장 주기와 메모리 직렬화 경로를 코드 라인으로 확인해, 10k+ trade에서 언제 선형 증가가 병목이 되는지 보겠습니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "@'
from pathlib import Path
for path, start, end in [
 ('scripts/v3.py',1,220),
 ('scripts/v3.py',404,520),
 ('scripts/v3.py',704,1115),
 ('scripts/triarb.py',1,220),
 ('scripts/triarb.py',767,1285),
 ('scripts/dashboard_unified.py',1,120),
 ('scripts/v2.py',600,900),
]:
    print(f'===== {path}:{start}-{end} =====')
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    for i in range(start-1, min(end, len(lines))):
        print(f'{i+1}: {lines[i]}')
'@ | py -3.12 -" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "rg -n \"SAVE_EVERY|sleep\\(|time\\.sleep|HISTORY_BARS|LOOKBACK|POLL|MEMORY_WARMUP|MAX|neighbors|k=|trade_log\\[|append\\(|save_state|load_state|save\\(|/api/state|urlopen\\(|timeout=\" scripts\\v3.py scripts\\triarb.py scripts\\v2.py scripts\\dashboard_unified.py" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
2026-04-21T03:04:08.313836Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 0.4 seconds
Output:
No installed Python found!

 exited 1 in 368ms:
No installed Python found!

 succeeded in 309ms:
scripts\dashboard_unified.py:36:            f"http://127.0.0.1:{port}/api/state",
scripts\dashboard_unified.py:39:        with urllib.request.urlopen(req, timeout=3) as resp:
scripts\triarb.py:52:HISTORY_BARS = 500
scripts\triarb.py:62:MAX_NOTIONAL_PER_LEG_USD = 500.0
scripts\triarb.py:77:MEMORY_WARMUP_TRADES = 30
scripts\triarb.py:82:CORR_LOOKBACK_BARS = 300
scripts\triarb.py:84:RATIO_MAX_CV = 0.05
scripts\triarb.py:292:    leg1_close: np.ndarray, leg2_close: np.ndarray, period: int = CORR_LOOKBACK_BARS
scripts\triarb.py:353:    if not np.isfinite(cv) or not (RATIO_MIN_CV <= cv <= RATIO_MAX_CV):
scripts\triarb.py:377:    if not np.isfinite(cv) or not (RATIO_MIN_CV <= cv <= RATIO_MAX_CV):
scripts\triarb.py:429:        self.records.append(record)
scripts\triarb.py:436:    def _neighbors(self, ctx: ContextVector, direction: str, k: int) -> list[TradeRecord]:
scripts\triarb.py:446:        neighbors = self._neighbors(ctx, direction, KNN_K)
scripts\triarb.py:447:        if not neighbors:
scripts\triarb.py:449:        return float(np.mean([r.r_multiple for r in neighbors])), len(neighbors)
scripts\triarb.py:452:        if len(self.records) < MEMORY_WARMUP_TRADES:
scripts\triarb.py:454:        cluster = self._neighbors(ctx, direction, MEMORY_MIN_SAMPLES_FOR_BLACKLIST)
scripts\triarb.py:461:        if total_trades < MEMORY_WARMUP_TRADES:
scripts\triarb.py:469:            span = MEMORY_FULL_ACTIVATION - MEMORY_WARMUP_TRADES
scripts\triarb.py:470:            weight = (total_trades - MEMORY_WARMUP_TRADES) / span
scripts\triarb.py:598:        notional_per_leg = min(notional_per_leg, MAX_NOTIONAL_PER_LEG_USD)
scripts\triarb.py:674:        self.pnl_history.append(self.capital)
scripts\triarb.py:694:        self.trade_log.append(
scripts\triarb.py:739:            out.append(
scripts\triarb.py:795:    _TF_POLL_DIVISOR = {"5m": 1, "30m": 5, "1h": 10}
scripts\triarb.py:798:        self, symbol: str, timeframe: str = "5m", limit: int = HISTORY_BARS
scripts\triarb.py:811:        DATA_DIR.mkdir(parents=True, exist_ok=True)
scripts\triarb.py:821:        print(f"[TriArb] Memory warmup: {MEMORY_WARMUP_TRADES} trades | {len(self.variants)} variants")
scripts\triarb.py:825:                df = self._fetch_history(symbol, tf, HISTORY_BARS)
scripts\triarb.py:833:        self.history_htf = self._fetch_history("BTC/USDT:USDT", HTF_TIMEFRAME, HISTORY_BARS)
scripts\triarb.py:849:        print(f"[TriArb] Dashboard API: http://localhost:{self.port}/api/state")
scripts\triarb.py:880:        self.pair_corr[pair_id] = compute_pair_correlation(close1, close2, CORR_LOOKBACK_BARS)
scripts\triarb.py:1039:                        self.history_htf = pd.concat([self.history_htf, row]).tail(HISTORY_BARS)
scripts\triarb.py:1043:            divisor = self._TF_POLL_DIVISOR.get(tf, 1)
scripts\triarb.py:1057:                self.history[tf][symbol] = pd.concat([self.history[tf][symbol], row]).tail(HISTORY_BARS)
scripts\triarb.py:1073:            self._save_state()
scripts\triarb.py:1082:                preview_parts.append(f"{pair_id} z={metrics['z']:+.2f}")
scripts\triarb.py:1137:                "trade_log": pm.trade_log[-50:],
scripts\triarb.py:1191:            "memory_warmup": MEMORY_WARMUP_TRADES,
scripts\triarb.py:1195:    def _save_state(self):
scripts\triarb.py:1197:            DATA_DIR.mkdir(parents=True, exist_ok=True)
scripts\triarb.py:1208:                    bar_idx_tfs.append(tf)
scripts\triarb.py:1209:                    bar_idx_pairs.append(pair_id)
scripts\triarb.py:1210:                    bar_idx_values.append(int(idx))
scripts\triarb.py:1223:                blob["trade_logs"][name] = pm.trade_log[-200:]
scripts\triarb.py:1231:    def _load_state(self):
scripts\triarb.py:1263:                        pm.memory.records.append(TradeRecord(**rec))
scripts\triarb.py:1270:            print(f"  [load] TriArb tick={self.tick_count} variants restored")
scripts\triarb.py:1275:        self._load_state()
scripts\triarb.py:1285:                self._save_state()
scripts\triarb.py:1293:            time.sleep(TICK_SEC)
scripts\triarb.py:1306:        if self.path.startswith("/api/state"):
scripts\triarb.py:1314:            msg = b"TriArb API running. Use /api/state."
scripts\v2.py:50:HISTORY_BARS = 500
scripts\v2.py:61:MAX_LEVERAGE = 100           # 1~100x leverage range
scripts\v2.py:298:        self.predictions.append(y_pred)
scripts\v2.py:299:        self.actuals.append(y_true)
scripts\v2.py:312:            self.accuracy_history.append(correct / len(recent_p))
scripts\v2.py:321:            self.entropy_history.append(1.0)
scripts\v2.py:331:        self.entropy_history.append(entropy / max_entropy)
scripts\v2.py:428:        # Leverage: scales with calibration. Low confidence → 1x, high → up to MAX
scripts\v2.py:429:        leverage = max(1.0, round(calibration * prediction_strength * MAX_LEVERAGE))
scripts\v2.py:430:        leverage = min(leverage, MAX_LEVERAGE)
scripts\v2.py:449:        self.trade_returns.append(net_pct)     # Kelly uses unweighted returns
scripts\v2.py:452:        self.pnl_history.append(self.capital)
scripts\v2.py:454:        self.trade_log.append({
scripts\v2.py:487:        if self.path == "/api/state":
scripts\v2.py:570:    const d=await(await fetch('/api/state')).json();
scripts\v2.py:640:            ohlcv = self.exchange.fetch_ohlcv(self._symbol(asset), "1m", limit=HISTORY_BARS)
scripts\v2.py:696:            ).tail(HISTORY_BARS)
scripts\v2.py:767:            self._save_state()
scripts\v2.py:811:                all_acc.append(float(np.mean(vals)))
scripts\v2.py:830:            "max_leverage": MAX_LEVERAGE,
scripts\v2.py:838:            "trade_log": self.pm.trade_log[-50:],
scripts\v2.py:841:    def _save_state(self):
scripts\v2.py:857:    def _load_state(self):
scripts\v2.py:873:            print(f"  [load] tick={self.tick_count} cap=${self.pm.capital:,.0f}")
scripts\v2.py:878:        self._load_state()
scripts\v2.py:890:                self._save_state()
scripts\v2.py:895:            time.sleep(TICK_SEC)
scripts\v3.py:53:HISTORY_BARS = 500
scripts\v3.py:68:MEMORY_WARMUP_TRADES = 30              # trades before memory activates
scripts\v3.py:286:            pullback_bars.append(i)
scripts\v3.py:320:            pullback_bars.append(i)
scripts\v3.py:417:        self.records.append(record)
scripts\v3.py:427:    def _neighbors(self, ctx: ContextVector, direction: str, k: int) -> list[TradeRecord]:
scripts\v3.py:441:        neighbors = self._neighbors(ctx, direction, KNN_K)
scripts\v3.py:442:        if not neighbors:
scripts\v3.py:444:        ev = float(np.mean([r.r_multiple for r in neighbors]))
scripts\v3.py:445:        return ev, len(neighbors)
scripts\v3.py:449:        cluster = self._neighbors(ctx, direction, MEMORY_MIN_SAMPLES_FOR_BLACKLIST)
scripts\v3.py:458:        Warmup: no memory effect until MEMORY_WARMUP_TRADES.
scripts\v3.py:461:        if total_trades < MEMORY_WARMUP_TRADES:
scripts\v3.py:472:            span = MEMORY_FULL_ACTIVATION - MEMORY_WARMUP_TRADES
scripts\v3.py:473:            weight = (total_trades - MEMORY_WARMUP_TRADES) / span
scripts\v3.py:651:        self.pnl_history.append(self.capital)
scripts\v3.py:672:        self.trade_log.append({
scripts\v3.py:731:                       limit: int = HISTORY_BARS) -> pd.DataFrame | None:
scripts\v3.py:894:        print(f"[V3] Memory warmup: {MEMORY_WARMUP_TRADES} trades")
scripts\v3.py:898:                df = self._fetch_history(asset, tf, HISTORY_BARS)
scripts\v3.py:904:            df_htf = self._fetch_history(asset, HTF_TIMEFRAME, HISTORY_BARS)
scripts\v3.py:915:        print(f"[V3] Dashboard API: http://localhost:{self.port}/api/state")
scripts\v3.py:918:    _TF_POLL_DIVISOR = {"1m": 1, "3m": 1, "5m": 1, "15m": 3, "30m": 5}
scripts\v3.py:936:                        ).tail(HISTORY_BARS)
scripts\v3.py:943:                divisor = self._TF_POLL_DIVISOR.get(tf, 1)
scripts\v3.py:959:                ).tail(HISTORY_BARS)
scripts\v3.py:976:            self._save_state()
scripts\v3.py:1004:            parts.append(f"{name.replace('v3-','')}={pm.total_return()*100:+.1f}%/{len(pm.trade_log)}t")
scripts\v3.py:1030:                "trade_log": pm.trade_log[-30:],
scripts\v3.py:1046:            "memory_warmup": MEMORY_WARMUP_TRADES,
scripts\v3.py:1053:    def _save_state(self):
scripts\v3.py:1068:                trade_logs[name] = pm.trade_log[-200:]
scripts\v3.py:1075:    def _load_state(self):
scripts\v3.py:1098:                        pm.memory.records.append(TradeRecord(**rec))
scripts\v3.py:1100:            print(f"  [load] tick={self.tick_count} variants restored")
scripts\v3.py:1105:        self._load_state()
scripts\v3.py:1117:                self._save_state()
scripts\v3.py:1124:            time.sleep(TICK_SEC)
scripts\v3.py:1137:        if self.path.startswith("/api/state"):
scripts\v3.py:1145:            msg = b"V3 API running. Use /api/state."

exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content scripts\\v3.py | Select-Object -First 140" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content scripts\\v3.py | Select-Object -Skip 404 -First 90" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content scripts\\v3.py | Select-Object -Skip 704 -First 430" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content scripts\\triarb.py | Select-Object -First 120" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content scripts\\triarb.py | Select-Object -Skip 767 -First 540" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content scripts\\dashboard_unified.py | Select-Object -First 80" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content scripts\\v2.py | Select-Object -Skip 600 -First 310" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 466ms:
# ===================================================================
class V3Engine:
    def __init__(self, assets: list[str], port: int = DASH_PORT):
        self.assets = assets
        self.port = port
        self.exchange = ccxt.bybit({"enableRateLimit": True})
        # Execution timeframes used by any variant (derived from config)
        self.exec_timeframes: list[str] = sorted({cfg["timeframe"] for cfg in VARIANTS_CONFIG.values()})
        # history[tf][asset] -> DataFrame
        self.history: dict[str, dict[str, pd.DataFrame]] = {tf: {} for tf in self.exec_timeframes}
        # HTF (1h) history for bias filter
        self.history_htf: dict[str, pd.DataFrame] = {}
        # htf_bias per asset: 'bullish' | 'bearish' | 'neutral'
        self.htf_bias: dict[str, str] = {a: "neutral" for a in assets}
        self.variants: dict[str, VariantPM] = {
            name: VariantPM(name, cfg) for name, cfg in VARIANTS_CONFIG.items()
        }
        self.tick_count = 0
        self.last_save = time.time()
        # Per-(tf, asset) last-seen bar ts to detect newly closed bars
        self.last_bar_ts: dict[str, dict[str, Any]] = {tf: {} for tf in self.exec_timeframes}

    def _symbol(self, asset: str) -> str:
        return f"{asset}/USDT:USDT"

    def _fetch_history(self, asset: str, timeframe: str = "5m",
                       limit: int = HISTORY_BARS) -> pd.DataFrame | None:
        try:
            ohlcv = self.exchange.fetch_ohlcv(self._symbol(asset), timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
            df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
            return df
        except Exception as e:
            print(f"  [{asset} {timeframe}] fetch error: {e}")
            return None

    def _compute_snapshot(self, df: pd.DataFrame) -> MarketSnapshot | None:
        if len(df) < 60:
            return None
        c = df["close"].values
        vwap_arr = IndicatorEngine.session_vwap(df)
        ema_arr = IndicatorEngine.ema(c, 9)
        atr14_arr = IndicatorEngine.atr(df, 14)
        atr60_arr = IndicatorEngine.atr(df, 60)

        atr14_now = float(atr14_arr[-1])
        atr60_now = float(atr60_arr[-1]) if len(atr60_arr) > 0 else atr14_now
        if atr14_now <= 0:
            return None

        # VWAP crosses in last 20 bars
        lb = min(20, len(c) - 1)
        crosses = 0
        for i in range(-lb, 0):
            prev = c[i - 1] - vwap_arr[i - 1]
            curr = c[i] - vwap_arr[i]
            if prev * curr < 0:
                crosses += 1

        vwap_slope_3 = 0.0
        if len(vwap_arr) >= 4:
            vwap_slope_3 = float(vwap_arr[-1] - vwap_arr[-4])

        ts_now = df["ts"].iloc[-1]
        hour = int(ts_now.hour) if hasattr(ts_now, "hour") else 0

        return MarketSnapshot(
            close=float(c[-1]),
            vwap=float(vwap_arr[-1]),
            ema9=float(ema_arr[-1]),
            atr14=atr14_now,
            vwap_slope_3=vwap_slope_3,
            ema_dist_atr=(float(c[-1]) - float(ema_arr[-1])) / atr14_now,
            recent_vwap_crosses=crosses,
            close_vwap_dist_atr=abs(float(c[-1]) - float(vwap_arr[-1])) / atr14_now,
            session_hour=hour,
            vol_regime=atr14_now / max(atr60_now, 1e-9),
        )

    def _make_context(self, snap: MarketSnapshot, vp_distance: float, rr: float) -> ContextVector:
        return ContextVector(
            vwap_slope=snap.vwap_slope_3 / max(snap.atr14, 1e-9),
            ema_dist_atr=snap.ema_dist_atr,
            vp_clearance_atr=vp_distance / max(snap.atr14, 1e-9),
            rr_estimate=rr,
            session_hour_bucket=snap.session_hour // 4,
            vol_regime=snap.vol_regime,
        )

    def _process_variant_on_bar(self, variant_name: str, asset: str,
                                df: pd.DataFrame, bar: dict, htf_bias_now: str):
        """Evaluate entries+exits for one variant on a new bar.

        htf_bias_now: 'bullish'/'bearish'/'neutral' from 1h EMA20/50.
        If variant has htf_filter=True, neutral blocks all entries and
        signals must match the HTF direction.
        """
        pm = self.variants[variant_name]
        cfg = pm.config

        snap = self._compute_snapshot(df)
        if snap is None:
            return

        # Exits first (use latest bar's HL and close + current EMA9/ATR)
        pm.check_exits(asset, bar, snap.ema9, snap.atr14)

        # Then entries (only if no existing position)
        if asset in pm.positions:
            return

        # 0. HTF bias filter (before any expensive computation)
        if cfg.get("htf_filter", False) and htf_bias_now == "neutral":
            pm.signals_blocked_htf += 1
            pm.signals_considered += 1
            return

        # 1. Market state classification
        state = classify_state(df, snap, cfg["chop_strict"])
        if state not in ("LONG_BIAS", "SHORT_BIAS"):
            if state == "VWAP_CHOP":
                pm.signals_blocked_chop += 1
            pm.signals_considered += 1
            return

        # HTF direction match check
        if cfg.get("htf_filter", False):
            if state == "LONG_BIAS" and htf_bias_now != "bullish":
                pm.signals_blocked_htf += 1
                pm.signals_considered += 1
                return
            if state == "SHORT_BIAS" and htf_bias_now != "bearish":
                pm.signals_blocked_htf += 1
                pm.signals_considered += 1
                return

        # 2. Pullback validity
        if state == "LONG_BIAS":
            valid, pullback_low = long_pullback_valid(df, snap)
            if not valid:
                pm.signals_considered += 1
                return
            entry_price = snap.close  # signal bar close triggers next-bar breakout
            hard_stop = pullback_low - 0.15 * snap.atr14
            soft_stop_ref = snap.ema9 - 0.05 * snap.atr14
            direction = "long"
        else:  # SHORT_BIAS
            valid, pullback_high = short_pullback_valid(df, snap)
            if not valid:
                pm.signals_considered += 1
                return
            entry_price = snap.close
            hard_stop = pullback_high + 0.15 * snap.atr14
            soft_stop_ref = snap.ema9 + 0.05 * snap.atr14
            direction = "short"

        hard_stop_dist = abs(entry_price - hard_stop)
        if hard_stop_dist <= 0:
            return

        # 3. Volume profile clearance + RR
        clear, first_hvn, rr = vp_clearance(
            df, entry_price, direction, snap.atr14, hard_stop_dist, cfg["rr_min"]
        )
        if not clear:
            pm.signals_blocked_rr += 1
            pm.signals_considered += 1
            return

        vp_distance = abs(first_hvn - entry_price)
        ctx = self._make_context(snap, vp_distance, rr)

        # 4. Execute
        result = pm.try_open(
            asset=asset, direction=direction, entry=entry_price,
            hard_stop=hard_stop, target=first_hvn, soft_stop_ref=soft_stop_ref,
            ctx=ctx,
        )
        pm.signals_considered += 1
        if result is None:
            print(f"  [{variant_name} {asset}] {direction.upper()} @{entry_price:.2f} "
                  f"stop={hard_stop:.2f} tgt={first_hvn:.2f} RR={rr:.2f} "
                  f"htf={htf_bias_now}")

    def init(self):
        print(f"[V3] Parker Brooks + Context Memory | {len(self.assets)} assets "
              f"| {len(VARIANTS_CONFIG)} variants")
        print(f"[V3] Exec TFs: {','.join(self.exec_timeframes)} | HTF bias: {HTF_TIMEFRAME}")
        print(f"[V3] Cost: {ROUND_TRIP_COST*100:.2f}% RT | Risk/trade: {RISK_PER_TRADE*100:.1f}%")
        print(f"[V3] Memory warmup: {MEMORY_WARMUP_TRADES} trades")
        for asset in self.assets:
            sizes = {}
            for tf in self.exec_timeframes:
                df = self._fetch_history(asset, tf, HISTORY_BARS)
                if df is not None:
                    self.history[tf][asset] = df
                    self.last_bar_ts[tf][asset] = df["ts"].iloc[-1]
                    sizes[tf] = len(df)
            # HTF (1h) load
            df_htf = self._fetch_history(asset, HTF_TIMEFRAME, HISTORY_BARS)
            if df_htf is not None:
                self.history_htf[asset] = df_htf
                self.htf_bias[asset] = htf_bias(df_htf)
                sizes[HTF_TIMEFRAME] = len(df_htf)
            if sizes:
                first_tf = self.exec_timeframes[0]
                price_src = self.history.get(first_tf, {}).get(asset)
                price_txt = f"price=${float(price_src['close'].iloc[-1]):,.2f}" if price_src is not None else ""
                tf_txt = " ".join(f"{tf}={n}" for tf, n in sizes.items())
                print(f"  [{asset}] {tf_txt} htf_bias={self.htf_bias[asset]} {price_txt}")
        print(f"[V3] Dashboard API: http://localhost:{self.port}/api/state")

    # Per-TF poll frequency (in ticks). Shorter TF ??poll more often.
    _TF_POLL_DIVISOR = {"1m": 1, "3m": 1, "5m": 1, "15m": 3, "30m": 5}

    def tick(self):
        self.tick_count += 1

        # --- HTF (1h) refresh every HTF_REFRESH_TICKS ---
        if self.tick_count % HTF_REFRESH_TICKS == 0:
            for asset in self.assets:
                if asset not in self.history_htf:
                    continue
                new_htf = self._fetch_history(asset, HTF_TIMEFRAME, 5)
                if new_htf is not None and len(new_htf) >= 2:
                    latest = new_htf.iloc[-2]
                    prev_ts = self.history_htf[asset]["ts"].iloc[-1]
                    if latest["ts"] != prev_ts:
                        row = new_htf.iloc[-2:-1]
                        self.history_htf[asset] = pd.concat(
                            [self.history_htf[asset], row], ignore_index=True
                        ).tail(HISTORY_BARS)
                    # Always refresh bias (EMA reacts to closes even without new bar)
                    self.htf_bias[asset] = htf_bias(self.history_htf[asset])

        # --- Execution TF refresh (each variant uses its own TF) ---
        for asset in self.assets:
            for tf in self.exec_timeframes:
                divisor = self._TF_POLL_DIVISOR.get(tf, 1)
                if self.tick_count % divisor != 0:
                    continue
                if asset not in self.history[tf]:
                    continue
                new_df = self._fetch_history(asset, tf, 5)
                if new_df is None or len(new_df) < 2:
                    continue
                latest = new_df.iloc[-2]  # closed bar
                prev_ts = self.last_bar_ts[tf].get(asset)
                if prev_ts is not None and latest["ts"] == prev_ts:
                    continue  # no new closed bar
                # New closed bar ??append and fire variants
                row = new_df.iloc[-2:-1]
                self.history[tf][asset] = pd.concat(
                    [self.history[tf][asset], row], ignore_index=True
                ).tail(HISTORY_BARS)
                self.last_bar_ts[tf][asset] = latest["ts"]
                bar = {
                    "ts": latest["ts"], "open": float(latest["open"]),
                    "high": float(latest["high"]), "low": float(latest["low"]),
                    "close": float(latest["close"]), "volume": float(latest["volume"]),
                }
                htf_now = self.htf_bias.get(asset, "neutral")
                for name, cfg in VARIANTS_CONFIG.items():
                    if cfg["timeframe"] == tf:
                        self._process_variant_on_bar(
                            name, asset, self.history[tf][asset], bar, htf_now
                        )

        if self.tick_count % 5 == 0:
            self._log_tick()
        if time.time() - self.last_save > SAVE_INTERVAL:
            self._save_state()
            self.last_save = time.time()

    def _log_tick(self):
        log_entry: dict[str, Any] = {
            "tick": self.tick_count,
            "t": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "variants": {},
        }
        for name, pm in self.variants.items():
            log_entry["variants"][name] = {
                "ret": round(pm.total_return(), 6),
                "cap": round(pm.capital, 2),
                "trades": len(pm.trade_log),
                "win_rate": round(pm.win_rate(), 3),
                "mem_trades": len(pm.memory.records),
                "blocked_chop": pm.signals_blocked_chop,
                "blocked_rr": pm.signals_blocked_rr,
                "blocked_mem": pm.signals_blocked_memory,
                "blocked_htf": pm.signals_blocked_htf,
                "positions": len(pm.positions),
            }
        log_entry["htf_bias"] = dict(self.htf_bias)
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        # Console summary
        parts = []
        for name, pm in self.variants.items():
            parts.append(f"{name.replace('v3-','')}={pm.total_return()*100:+.1f}%/{len(pm.trade_log)}t")
        print(f"  [tick {self.tick_count}] " + " | ".join(parts))

    def snapshot(self) -> dict:
        variants_data = {}
        for name, pm in self.variants.items():
            ms = pm.memory.snapshot()
            variants_data[name] = {
                "name": name,
                "config": pm.config,
                "total_return": pm.total_return(),
                "capital": pm.capital,
                "initial_capital": pm.initial_capital,
                "drawdown": pm.drawdown(),
                "win_rate": pm.win_rate(),
                "total_trades": len(pm.trade_log),
                "positions": [
                    {
                        "asset": p.asset, "dir": p.direction,
                        "entry": p.entry_price, "target": p.target_price,
                        "hard_stop": p.hard_stop, "size": p.size,
                        "lev": p.leverage, "time": p.entry_time,
                    }
                    for p in pm.positions.values()
                ],
                "pnl_history": pm.pnl_history[-300:],
                "trade_log": pm.trade_log[-30:],
                "memory": ms,
                "signals": {
                    "considered": pm.signals_considered,
                    "blocked_chop": pm.signals_blocked_chop,
                    "blocked_rr": pm.signals_blocked_rr,
                    "blocked_memory": pm.signals_blocked_memory,
                    "blocked_htf": pm.signals_blocked_htf,
                    "executed": pm.signals_executed,
                },
            }
        return {
            "tick": self.tick_count,
            "variants": variants_data,
            "assets": self.assets,
            "variant_configs": VARIANTS_CONFIG,
            "memory_warmup": MEMORY_WARMUP_TRADES,
            "memory_full_activation": MEMORY_FULL_ACTIVATION,
            "exec_timeframes": self.exec_timeframes,
            "htf_timeframe": HTF_TIMEFRAME,
            "htf_bias": dict(self.htf_bias),
        }

    def _save_state(self):
        try:
            state: dict[str, Any] = {
                "tick_count": np.array([self.tick_count]),
            }
            for name, pm in self.variants.items():
                state[f"{name}_capital"] = np.array([pm.capital])
                state[f"{name}_peak"] = np.array([pm.peak_capital])
                state[f"{name}_pnl"] = np.array(pm.pnl_history[-1000:])
            np.savez_compressed(STATE_PATH, **state)
            # Memory saved separately as JSON
            memory_blob = {}
            trade_logs = {}
            for name, pm in self.variants.items():
                memory_blob[name] = [asdict(r) for r in pm.memory.records[-500:]]
                trade_logs[name] = pm.trade_log[-200:]
            with open(MEMORY_PATH, "w") as f:
                json.dump({"memory": memory_blob, "trade_logs": trade_logs}, f)
            print(f"  [save] state + memory persisted")
        except Exception as e:
            print(f"  [save] error: {e}")

    def _load_state(self):
        if not STATE_PATH.exists():
            return
        try:
            d = np.load(STATE_PATH, allow_pickle=True)
            self.tick_count = int(d["tick_count"][0])
            for name, pm in self.variants.items():
                key_cap = f"{name}_capital"
                key_peak = f"{name}_peak"
                key_pnl = f"{name}_pnl"
                if key_cap in d:
                    pm.capital = float(d[key_cap][0])
                if key_peak in d:
                    pm.peak_capital = float(d[key_peak][0])
                if key_pnl in d:
                    pm.pnl_history = d[key_pnl].tolist()
            if MEMORY_PATH.exists():
                with open(MEMORY_PATH) as f:
                    blob = json.load(f)
                mem = blob.get("memory", {})
                tlogs = blob.get("trade_logs", {})
                for name, pm in self.variants.items():
                    for rec in mem.get(name, []):
                        pm.memory.records.append(TradeRecord(**rec))
                    pm.trade_log = tlogs.get(name, [])
            print(f"  [load] tick={self.tick_count} variants restored")
        except Exception as e:
            print(f"  [load] error: {e}")

    def run(self):
        self._load_state()
        self.init()

        DashboardHandler.engine = self
        server = http.server.HTTPServer(("0.0.0.0", self.port), DashboardHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        while True:
            try:
                self.tick()
            except KeyboardInterrupt:
                self._save_state()
                print("\n[V3] Stopped. State saved.")
                break
            except Exception as e:
                print(f"  [error] {e}")
                import traceback
                traceback.print_exc()
            time.sleep(TICK_SEC)


# ===================================================================
# Dashboard (API only ??unified dashboard on 8900 renders UI)
# ===================================================================
class DashboardHandler(http.server.BaseHTTPRequestHandler):
    engine: Any = None

    def log_message(self, *a):
        pass

 succeeded in 471ms:

    The self-improving core:
      - Bad contexts (EV < threshold with enough samples) ??blacklist
      - Good contexts (EV > threshold) ??position size boost
    """

    def __init__(self, variant_name: str):
        self.variant_name = variant_name
        self.records: list[TradeRecord] = []
        self._blacklist_cache: set[int] | None = None  # hash-based

    def add(self, record: TradeRecord):
        self.records.append(record)
        self._blacklist_cache = None  # invalidate

    def _distance(self, a: np.ndarray, b: np.ndarray) -> float:
        # Weighted Euclidean: numeric dims use standard, hour_bucket uses 0/1 mismatch
        diff = a - b
        # hour_bucket at index 4 ??treat as categorical (0 if same, 2 if diff)
        diff[4] = 0.0 if a[4] == b[4] else 2.0
        return float(np.linalg.norm(diff))

    def _neighbors(self, ctx: ContextVector, direction: str, k: int) -> list[TradeRecord]:
        if not self.records:
            return []
        target = ctx.to_array()
        same_dir = [r for r in self.records if r.direction == direction]
        if not same_dir:
            return []
        distances = [(self._distance(target, np.array(r.context)), r) for r in same_dir]
        distances.sort(key=lambda x: x[0])
        k = min(k, len(distances))
        return [r for _, r in distances[:k]]

    def query_ev(self, ctx: ContextVector, direction: str) -> tuple[float, int]:
        """Top-k EV estimate for position sizing."""
        neighbors = self._neighbors(ctx, direction, KNN_K)
        if not neighbors:
            return 0.0, 0
        ev = float(np.mean([r.r_multiple for r in neighbors]))
        return ev, len(neighbors)

    def is_blacklisted(self, ctx: ContextVector, direction: str) -> bool:
        """Blacklist check uses a larger neighborhood for statistical significance."""
        cluster = self._neighbors(ctx, direction, MEMORY_MIN_SAMPLES_FOR_BLACKLIST)
        if len(cluster) < MEMORY_MIN_SAMPLES_FOR_BLACKLIST:
            return False
        cluster_ev = float(np.mean([r.r_multiple for r in cluster]))
        return cluster_ev < MEMORY_BLACKLIST_EV_THRESHOLD

    def size_multiplier(self, ctx: ContextVector, direction: str, total_trades: int) -> float:
        """Returns position size multiplier in [0, 1.5] based on context EV.

        Warmup: no memory effect until MEMORY_WARMUP_TRADES.
        Gradual activation between warmup and full-activation.
        """
        if total_trades < MEMORY_WARMUP_TRADES:
            return 1.0

        ev, n = self.query_ev(ctx, direction)
        if n == 0:
            return 1.0

        # Activation weight ramps 0->1 between WARMUP and FULL
        if total_trades >= MEMORY_FULL_ACTIVATION:
            weight = 1.0
        else:
            span = MEMORY_FULL_ACTIVATION - MEMORY_WARMUP_TRADES
            weight = (total_trades - MEMORY_WARMUP_TRADES) / span

        # Base multiplier: 1.0. Scale by EV with clip.
        if ev > MEMORY_BOOST_EV_THRESHOLD:
            boost = min((ev - MEMORY_BOOST_EV_THRESHOLD) * 1.0, 0.5)  # max +50%
            return 1.0 + boost * weight
        elif ev < 0:
            # Soft penalty before blacklist threshold
            penalty = min(abs(ev) * 0.5, 0.5)  # max -50%
            return max(0.5, 1.0 - penalty * weight)
        return 1.0

    def snapshot(self) -> dict:
        if not self.records:
            return {
                "n_trades": 0,
                "ev_long": 0.0,
                "ev_short": 0.0,
                "win_rate": 0.0,
                "avg_r": 0.0,
                "blacklisted_clusters": 0,
            }

 succeeded in 548ms:
"""V3 ??Parker Brooks Rule Engine + Self-Learning Context Memory.

Design:
  1. Parker Brooks rule engine (VWAP/EMA9/Volume Profile) ??deterministic entry gate
  2. Context Memory (k-NN based EV tracking) ??learns good/bad contexts
  3. Kill Switch ??auto-blacklist bad context clusters
  4. Multi-variant paper trading (5 variants concurrently)

Core principle (user requirement):
  "??醫뗭? 嫄??뚭굅, 醫뗭? 嫄?諛쏆븘?ㅼ엫. ?ㅼ뒪濡?諛쒖쟾?섎뒗 ?뚭퀬由ъ쬁."

Usage:
    py -3.12 scripts/v3.py [--assets ETH,BTC,SOL,XRP] [--port 8898]

Dashboard:
    http://localhost:8898
"""
from __future__ import annotations

import argparse
import http.server
import json
import math
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

for _pkg, _imp in [("ccxt", "ccxt")]:
    try:
        __import__(_imp)
    except ImportError:
        import subprocess as _sp
        _sp.check_call([sys.executable, "-m", "pip", "install", _pkg])

import ccxt

# ===================================================================
# Constants
# ===================================================================
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATE_PATH = DATA_DIR / "v3_state.npz"
LOG_PATH = DATA_DIR / "v3.jsonl"
MEMORY_PATH = DATA_DIR / "v3_memory.json"
DASH_PORT = 8898
TICK_SEC = 60
HISTORY_BARS = 500
INITIAL_CAPITAL = 10_000.0
SAVE_INTERVAL = 1800

# Cost model (Bybit USDT perp)
TAKER_FEE = 0.00055
SLIPPAGE = 0.0005
ROUND_TRIP_COST = (TAKER_FEE * 2) + (SLIPPAGE * 2)  # ~0.21%

# Context Memory policy
CTX_DIM = 6
KNN_K = 5
MEMORY_MIN_SAMPLES_FOR_BLACKLIST = 20
MEMORY_BLACKLIST_EV_THRESHOLD = -0.5   # in R units
MEMORY_BOOST_EV_THRESHOLD = 0.3        # in R units
MEMORY_WARMUP_TRADES = 30              # trades before memory activates
MEMORY_FULL_ACTIVATION = 100           # trades before memory at full weight

# Risk
RISK_PER_TRADE = 0.005  # 0.5% of equity per trade (hard stop distance)

# HTF bias filter (higher-timeframe context)
# Research (Parker Brooks / intraday scalping multi-TF analysis):
#   - Execution TFs: 1m??0m. Core: 5m, 15m. 30m is upper bound.
#   - HTF context: 1h (standard for scalping confluence). Daily for swing.
#   - 60m/120m as execution TF ??unsuitable (VWAP is session-anchored; beyond 30m it smooths out).
HTF_TIMEFRAME = "1h"
HTF_MIN_BARS = 60          # need enough bars for EMA50
HTF_REFRESH_TICKS = 15     # refresh 1h bias every 15 minutes (tick = 60s)

# Variants ??user said: "?ㅼ뼇?섍쾶 紐⑤뜽??留뚮뱾?댁꽌 蹂묓뻾 ?섏씠???몃젅?대뵫 ?뚯뒪??
# Execution TFs expanded per WebSearch findings: 3m/5m/15m/30m + 5m param variants.
# htf_filter=True ??block entries against 1h EMA20/50 bias; neutral ??NO_TRADE.
VARIANTS_CONFIG = {
    "v3-3m":              dict(rr_min=1.5, chop_strict=1.0, memory=True,  timeframe="3m",  htf_filter=True),
    "v3-5m":              dict(rr_min=1.5, chop_strict=1.0, memory=True,  timeframe="5m",  htf_filter=True),
    "v3-15m":             dict(rr_min=1.5, chop_strict=1.0, memory=True,  timeframe="15m", htf_filter=True),
    "v3-30m":             dict(rr_min=1.5, chop_strict=1.0, memory=True,  timeframe="30m", htf_filter=True),
    "v3-5m-aggressive":   dict(rr_min=1.2, chop_strict=0.8, memory=True,  timeframe="5m",  htf_filter=True),
    "v3-5m-conservative": dict(rr_min=2.0, chop_strict=1.2, memory=True,  timeframe="5m",  htf_filter=True),
    "v3-control":         dict(rr_min=1.5, chop_strict=1.0, memory=False, timeframe="5m",  htf_filter=False),
}


# ===================================================================
# Indicator Engine
# ===================================================================
class IndicatorEngine:
    """Computes VWAP (session-anchored UTC 00:00), EMA9, ATR14, Volume Profile."""

    @staticmethod
    def session_vwap(df: pd.DataFrame) -> np.ndarray:
        """VWAP anchored at UTC 00:00 (daily reset)."""
        # Ensure ts is datetime
        ts = pd.to_datetime(df["ts"])
        date = ts.dt.date
        tp = (df["high"] + df["low"] + df["close"]) / 3.0
        vol = df["volume"]
        tpv = tp * vol
        # Cumulative within each day
        cum_tpv = tpv.groupby(date).cumsum()
        cum_vol = vol.groupby(date).cumsum()
        vwap = cum_tpv / cum_vol.replace(0, np.nan)
        return vwap.ffill().bfill().values.astype(float)

    @staticmethod
    def ema(values: np.ndarray, period: int) -> np.ndarray:
        s = pd.Series(values)
        return s.ewm(span=period, adjust=False).mean().values.astype(float)

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> np.ndarray:
        h = df["high"].values.astype(float)
        lo = df["low"].values.astype(float)
        c = df["close"].values.astype(float)
        if len(c) < 2:
            return np.zeros_like(c)
        prev_c = np.concatenate([[c[0]], c[:-1]])
        tr = np.maximum.reduce([
            h - lo,
            np.abs(h - prev_c),
            np.abs(lo - prev_c),
        ])
        return pd.Series(tr).rolling(period, min_periods=1).mean().values.astype(float)

    @staticmethod
    def volume_profile(df: pd.DataFrame, lookback: int = 120, nbins: int = 30) -> tuple[np.ndarray, np.ndarray]:
        """Fixed-range volume profile. Returns (price_midpoints, volumes)."""

 succeeded in 417ms:
"""TriArb -- Pairs Ratio Mean-Reversion Engine.

NOTE: TriArb is not a live 3-leg triangular arbitrage implementation.
The name comes from the original triangular-arb idea, but this engine is
implemented as 2-leg pairs ratio arbitrage because single-exchange REST
execution cannot reliably capture true triangular mispricing.

Market-neutral pair positions:
  - short_ratio: leg1 SHORT + leg2 LONG with matched USDT notional
  - long_ratio:  leg1 LONG  + leg2 SHORT with matched USDT notional

Detailed design: docs/triarb_260420.md
"""
from __future__ import annotations

import argparse
import http.server
import json
import math
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

for _pkg, _imp in [("ccxt", "ccxt")]:
    try:
        __import__(_imp)
    except ImportError:
        import subprocess as _sp

        _sp.check_call([sys.executable, "-m", "pip", "install", _pkg])

import ccxt


# =====================================================================
# Constants
# =====================================================================
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATE_PATH = DATA_DIR / "triarb_state.npz"
LOG_PATH = DATA_DIR / "triarb.jsonl"
MEMORY_PATH = DATA_DIR / "triarb_memory.json"

DASH_PORT = 8899
TICK_SEC = 60
HISTORY_BARS = 500
INITIAL_CAPITAL = 10_000.0
SAVE_INTERVAL = 1800

TAKER_FEE = 0.00055
SLIPPAGE = 0.0005
PER_LEG_ROUND_TRIP = (TAKER_FEE * 2) + (SLIPPAGE * 2)
PAIR_ROUND_TRIP_COST = PER_LEG_ROUND_TRIP * 2

RISK_PER_TRADE_NOTIONAL = 0.02
MAX_NOTIONAL_PER_LEG_USD = 500.0
MIN_CORRELATION = 0.4
CORRELATION_BREAK_THRESHOLD = 0.3
LEVERAGE = 5.0

HTF_TIMEFRAME = "1h"
HTF_MIN_BARS = 60
HTF_REFRESH_TICKS = 15
HTF_STRONG_TREND_THRESHOLD = 0.02

CTX_DIM = 6
KNN_K = 5
MEMORY_MIN_SAMPLES_FOR_BLACKLIST = 20
MEMORY_BLACKLIST_EV_THRESHOLD = -0.5
MEMORY_BOOST_EV_THRESHOLD = 0.3
MEMORY_WARMUP_TRADES = 30
MEMORY_FULL_ACTIVATION = 100

# 300 bars of the shortest exec TF (5m) ??25h. On 1h TF ??12.5 days.
# ?ㅽ럺 "30???곴?" 紐낆묶? 珥덇린 臾몄꽌 ?쒗쁽?대ŉ, ?ㅼ젣 ?덈룄?곕뒗 TF蹂?bar ??
CORR_LOOKBACK_BARS = 300
RATIO_MIN_CV = 0.001
RATIO_MAX_CV = 0.05

PAIRS = {
    "ETHBTC": {"leg1": "ETH/USDT:USDT", "leg2": "BTC/USDT:USDT"},
    "SOLETH": {"leg1": "SOL/USDT:USDT", "leg2": "ETH/USDT:USDT"},
    "XRPBTC": {"leg1": "XRP/USDT:USDT", "leg2": "BTC/USDT:USDT"},
    "SOLBTC": {"leg1": "SOL/USDT:USDT", "leg2": "BTC/USDT:USDT"},
}

VARIANTS_CONFIG = {
    "triarb-5m": dict(
        timeframe="5m",
        ratio_lookback_bars=20,
        entry_z=2.0,
        exit_target_z=0.5,
        exit_stop_z=3.5,
        time_stop_bars=24,
        max_velocity=1.0,
        pairs=["ETHBTC", "SOLETH", "XRPBTC", "SOLBTC"],
        memory=True,
        htf_filter=False,
    ),
    "triarb-30m": dict(
        timeframe="30m",
        ratio_lookback_bars=20,
        entry_z=2.0,
        exit_target_z=0.5,
        exit_stop_z=3.5,
        time_stop_bars=8,
        max_velocity=1.0,
        pairs=["ETHBTC", "SOLETH", "XRPBTC", "SOLBTC"],
        memory=True,
        htf_filter=False,
    ),
    # "daily" variant??1h TF 湲곕컲 ?κ린 ?쒓컖 吏꾩엯. 吏꾩쭨 1d(?쇰큺) ?꾨떂.
    "triarb-daily": dict(
        timeframe="1h",

 succeeded in 485ms:
# ===================================================================
# V2 Engine (main loop)
# ===================================================================
class V2Engine:
    def __init__(self, assets: list[str], port: int = DASH_PORT):
        self.assets = assets
        self.port = port
        self.exchange = ccxt.bybit({"enableRateLimit": True})
        self.feature_engines: dict[str, FeatureEngine] = {
            a: FeatureEngine() for a in assets
        }
        # Per-asset predictors (Rule 1: each asset gets its own model)
        self.predictors: dict[str, OnlinePredictor] = {
            a: OnlinePredictor() for a in assets
        }
        self.pm = PositionManager()
        self.history: dict[str, pd.DataFrame] = {}
        self.prices: dict[str, float] = {}
        self.tick_count = 0
        self.last_save = time.time()

        # t+1 labeling: store previous tick's features per asset
        self.prev_features: dict[str, np.ndarray] = {}
        # Cache funding rates between fetches
        self._last_funding: dict[str, float] = {a: 0.0 for a in assets}

    def _symbol(self, asset: str) -> str:
        return f"{asset}/USDT:USDT"

    def _fetch_funding(self, asset: str) -> float:
        """Fetch funding rate. Returns 0 on failure."""
        try:
            info = self.exchange.fetch_funding_rate(self._symbol(asset))
            return float(info.get("fundingRate", 0) or 0)
        except Exception:
            return 0.0

    def _fetch_history(self, asset: str) -> pd.DataFrame | None:
        try:
            ohlcv = self.exchange.fetch_ohlcv(self._symbol(asset), "1m", limit=HISTORY_BARS)
            df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
            df["ts"] = pd.to_datetime(df["ts"], unit="ms")
            return df
        except Exception as e:
            print(f"  [{asset}] fetch error: {e}")
            return None

    def _fetch_latest(self, asset: str) -> dict | None:
        """Fetch the most recent CLOSED bar (not the open candle)."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(self._symbol(asset), "1m", limit=3)
            if len(ohlcv) < 2:
                return None
            # Use [-2] = last fully closed bar. [-1] may be an open candle.
            bar = ohlcv[-2]
            return {
                "ts": pd.Timestamp(bar[0], unit="ms"),
                "open": bar[1], "high": bar[2], "low": bar[3],
                "close": bar[4], "volume": bar[5],
            }
        except Exception:
            return None

    def init(self):
        print(f"[V2] Initializing {len(self.assets)} assets...")
        print(f"[V2] Cost model: {ROUND_TRIP_COST*100:.2f}% round-trip")
        print(f"[V2] Kelly cap: {KELLY_CAP*100:.0f}% | Exposure cap: {TOTAL_EXPOSURE_CAP*100:.0f}%")
        for asset in self.assets:
            df = self._fetch_history(asset)
            if df is not None:
                self.history[asset] = df
                self.prices[asset] = float(df["close"].iloc[-1])
                print(f"  [{asset}] {len(df)} bars, ${self.prices[asset]:,.2f}")
        print(f"[V2] Dashboard: http://localhost:{self.port}")

    def tick(self):
        self.tick_count += 1

        for asset in self.assets:
            if asset not in self.history:
                continue

            # Fetch new bar
            bar = self._fetch_latest(asset)
            if bar is None:
                # API error ??do NOT skip position management
                # Close positions if we can't get price (safety)
                if asset in self.pm.positions and self.tick_count % 5 == 0:
                    print(f"  [{asset}] WARNING: API error, keeping position")
                continue

            # Update history
            new_row = pd.DataFrame([bar])
            self.history[asset] = pd.concat(
                [self.history[asset], new_row], ignore_index=True
            ).tail(HISTORY_BARS)

            price = float(bar["close"])
            self.prices[asset] = price

            # Fetch funding (every 30 ticks to avoid rate limits), cache between fetches
            if self.tick_count % 30 == 1:
                fr = self._fetch_funding(asset)
                if fr != 0.0:
                    self._last_funding[asset] = fr
            funding = self._last_funding.get(asset, 0.0)

            # Compute features
            fe = self.feature_engines[asset]
            features = fe.compute(self.history[asset], funding)
            if features is None:
                continue

            predictor = self.predictors[asset]

            # === PROPER t+1 LABELING ===
            # Update model: previous features ??current return (features[0])
            if asset in self.prev_features:
                actual_return = features[0]  # ret_1 of current bar
                predictor.update(self.prev_features[asset], actual_return)

            # Predict NEXT bar's return from current features
            prediction = predictor.predict(features)

            # Store for next tick's update
            self.prev_features[asset] = features.copy()

            # === POSITION MANAGEMENT ===
            if asset in self.pm.positions:
                pos = self.pm.positions[asset]
                should_exit = False

                # Exit if prediction flips direction
                if pos.direction == "long" and prediction < -MIN_EDGE_THRESHOLD:
                    should_exit = True
                elif pos.direction == "short" and prediction > MIN_EDGE_THRESHOLD:
                    should_exit = True
                # Exit if prediction drops to noise level
                elif abs(prediction) < MIN_EDGE_THRESHOLD * 0.5:
                    should_exit = True

                if should_exit:
                    ret = self.pm.close_position(asset, price)
                    if ret is not None:
                        tag = "WIN" if ret > 0 else "LOSS"
                        print(f"  [{asset}] CLOSE {tag} net={ret:+.4%} cap=${self.pm.capital:,.0f}")

            # === ENTRY: pure prediction-based ===
            elif abs(prediction) > MIN_EDGE_THRESHOLD and predictor.norm.is_warm():
                direction = "long" if prediction > 0 else "short"
                cal = predictor.calibration()
                if cal > 0.05:  # minimum trust
                    pred_strength = min(abs(prediction) / MIN_EDGE_THRESHOLD, 3.0) / 3.0
                    self.pm.open_position(asset, direction, price, pred_strength, cal)
                    pos = self.pm.positions.get(asset)
                    lev = pos.leverage if pos else 1
                    print(f"  [{asset}] OPEN {direction} @${price:,.2f} "
                          f"pred={prediction:+.6f} cal={cal:.2f} "
                          f"lev={lev:.0f}x kelly={self.pm.kelly_fraction():.2f}")

        # Periodic log
        if self.tick_count % 5 == 0:
            self._log_tick()

        # Save state
        if time.time() - self.last_save > SAVE_INTERVAL:
            self._save_state()
            self.last_save = time.time()

    def _log_tick(self):
        # Aggregate metrics across all asset predictors
        accs = [p.direction_accuracy() for p in self.predictors.values()]
        ents = [p.memory_entropy() for p in self.predictors.values()]
        avg_acc = np.mean(accs) if accs else 0.5
        avg_ent = np.mean(ents) if ents else 1.0
        total_preds = sum(len(p.predictions) for p in self.predictors.values())

        log_entry = {
            "tick": self.tick_count,
            "t": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "acc": round(avg_acc, 4),
            "entropy": round(avg_ent, 4),
            "ret": round(self.pm.total_return(), 6),
            "capital": round(self.pm.capital, 2),
            "trades": len(self.pm.trade_returns),
            "positions": len(self.pm.positions),
            "exposure": round(self.pm.current_exposure(), 4),
            "predictions": total_preds,
        }
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        print(f"  [tick {self.tick_count}] acc={avg_acc:.1%} ent={avg_ent:.1%} "
              f"ret={self.pm.total_return():+.2%} trades={len(self.pm.trade_returns)} "
              f"exp={self.pm.current_exposure():.1%}")

    def snapshot(self) -> dict:
        accs = [p.direction_accuracy() for p in self.predictors.values()]
        ents = [p.memory_entropy() for p in self.predictors.values()]
        # Use first predictor's feature importance for display (or average)
        fi = np.mean(
            [p.feature_importance for p in self.predictors.values()], axis=0
        ).tolist() if self.predictors else [1 / N_FEATURES] * N_FEATURES

        # Aggregate accuracy history: average across assets per time step
        max_len = max((len(p.accuracy_history) for p in self.predictors.values()), default=0)
        all_acc = []
        for i in range(max(0, max_len - 500), max_len):
            vals = [p.accuracy_history[i] for p in self.predictors.values()
                    if i < len(p.accuracy_history)]
            if vals:
                all_acc.append(float(np.mean(vals)))

        return {
            "tick": self.tick_count,
            "accuracy": float(np.mean(accs)) if accs else 0.5,
            "entropy": float(np.mean(ents)) if ents else 1.0,
            "total_return": self.pm.total_return(),
            "capital": self.pm.capital,
            "initial_capital": self.pm.initial_capital,
            "drawdown": self.pm.drawdown(),
            "kelly": self.pm.kelly_fraction(),
            "exposure": self.pm.current_exposure(),
            "exposure_cap": TOTAL_EXPOSURE_CAP,
            "total_predictions": sum(len(p.predictions) for p in self.predictors.values()),
            "feature_names": FEATURE_NAMES,
            "feature_importance": fi,
            "pnl_history": self.pm.pnl_history[-500:],
            "accuracy_history": all_acc[-500:],
            "notional": self.pm.current_notional(),
            "max_leverage": MAX_LEVERAGE,
            "total_trades": len(self.pm.trade_returns),
            "positions": [
                {"asset": p.asset, "dir": p.direction,
                 "entry": p.entry_price, "size": p.size,
                 "lev": p.leverage, "time": p.entry_time}
                for p in self.pm.positions.values()
            ],
            "trade_log": self.pm.trade_log[-50:],
        }

    def _save_state(self):
        try:
            state = {"tick_count": np.array([self.tick_count]),
                     "capital": np.array([self.pm.capital]),
                     "trade_returns": np.array(self.pm.trade_returns[-1000:])}
            for asset, pred in self.predictors.items():
                state[f"{asset}_w"] = pred.w
                state[f"{asset}_b"] = np.array([pred.b])
                state[f"{asset}_mean"] = pred.norm.mean
                state[f"{asset}_var"] = pred.norm.var
                state[f"{asset}_warm"] = np.array([pred.norm.warm])
            np.savez_compressed(STATE_PATH, **state)
            print(f"  [save] state ??{STATE_PATH}")
        except Exception as e:
            print(f"  [save] error: {e}")

    def _load_state(self):
        if not STATE_PATH.exists():
            return
        try:
            d = np.load(STATE_PATH, allow_pickle=True)
            self.tick_count = int(d["tick_count"][0])
            self.pm.capital = float(d["capital"][0])
            self.pm.trade_returns = d["trade_returns"].tolist()
            for asset in self.assets:
                if f"{asset}_w" in d:
                    pred = self.predictors[asset]
                    pred.w = d[f"{asset}_w"]
                    pred.b = float(d[f"{asset}_b"][0])
                    pred.norm.mean = d[f"{asset}_mean"]
                    pred.norm.var = d[f"{asset}_var"]
                    pred.norm.warm = int(d[f"{asset}_warm"][0])
            print(f"  [load] tick={self.tick_count} cap=${self.pm.capital:,.0f}")
        except Exception as e:
            print(f"  [load] error: {e}")

    def run(self):
        self._load_state()
        self.init()

        DashboardHandler.engine = self
        server = http.server.HTTPServer(("0.0.0.0", self.port), DashboardHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        while True:
            try:
                self.tick()
            except KeyboardInterrupt:
                self._save_state()
                print("\n[V2] Stopped. State saved.")
                break
            except Exception as e:
                print(f"  [error] {e}")
            time.sleep(TICK_SEC)


def main():
    parser = argparse.ArgumentParser(description="V2 Prediction Engine")
    parser.add_argument("--assets", default="ETH,BTC,SOL,XRP")
    parser.add_argument("--port", type=int, default=DASH_PORT)
    args = parser.parse_args()
    assets = [a.strip().upper() for a in args.assets.split(",")]
    V2Engine(assets=assets, port=args.port).run()


if __name__ == "__main__":
    main()

 succeeded in 563ms:
        self.active_pair_ids = sorted({p for cfg in VARIANTS_CONFIG.values() for p in cfg["pairs"]})
        self.active_symbols = sorted(
            {PAIRS[pid]["leg1"] for pid in self.active_pair_ids}
            | {PAIRS[pid]["leg2"] for pid in self.active_pair_ids}
        )
        self.exec_timeframes = sorted(
            {cfg["timeframe"] for cfg in VARIANTS_CONFIG.values()},
            key=lambda tf: _TF_ORDER.get(tf, 999),
        )
        self.history: dict[str, dict[str, pd.DataFrame]] = {tf: {} for tf in self.exec_timeframes}
        self.history_htf: pd.DataFrame | None = None
        self.htf_status = "mild"
        self.variants = {name: VariantPM(name, cfg) for name, cfg in VARIANTS_CONFIG.items()}
        self.tick_count = 0
        self.last_save = time.time()
        self.last_bar_ts: dict[str, dict[str, Any]] = {tf: {} for tf in self.exec_timeframes}
        self.last_pair_ts: dict[str, dict[str, Any]] = {
            tf: {pid: None for pid in self.active_pair_ids} for tf in self.exec_timeframes
        }
        self.bar_idx: dict[str, dict[str, int]] = {
            tf: {pid: 0 for pid in self.active_pair_ids} for tf in self.exec_timeframes
        }
        self.pair_metrics: dict[str, dict[str, dict[int, dict[str, float]] | None]] = {
            tf: {} for tf in self.exec_timeframes
        }
        self.pair_corr: dict[str, float] = {pid: float("nan") for pid in self.active_pair_ids}

    _TF_POLL_DIVISOR = {"5m": 1, "30m": 5, "1h": 10}

    def _fetch_history(
        self, symbol: str, timeframe: str = "5m", limit: int = HISTORY_BARS
    ) -> pd.DataFrame | None:
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
            df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
            df = df.drop_duplicates("ts").sort_values("ts").set_index("ts", drop=False)
            return df
        except Exception as e:
            print(f"  [{symbol} {timeframe}] fetch error: {e}")
            return None

    def init(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        print("[TriArb] Pairs Ratio Arbitrage (2-leg delta-neutral)")
        print(f"[TriArb] Active pairs: {', '.join(self.active_pair_ids)} ({len(self.active_pair_ids)})")
        bases = ", ".join(_symbol_base(s) + "/USDT" for s in self.active_symbols)
        print(f"[TriArb] Active symbols: {bases} ({len(self.active_symbols)})")
        print(f"[TriArb] Exec TFs: {', '.join(self.exec_timeframes)} | HTF: {HTF_TIMEFRAME} (BTC)")
        print(
            f"[TriArb] Cost: {PAIR_ROUND_TRIP_COST*100:.2f}% round-trip per pair "
            f"| Risk/trade: {RISK_PER_TRADE_NOTIONAL*100:.0f}% notional"
        )
        print(f"[TriArb] Memory warmup: {MEMORY_WARMUP_TRADES} trades | {len(self.variants)} variants")

        for tf in self.exec_timeframes:
            for symbol in self.active_symbols:
                df = self._fetch_history(symbol, tf, HISTORY_BARS)
                if df is None or df.empty:
                    continue
                self.history[tf][symbol] = df
                self.last_bar_ts[tf][symbol] = df["ts"].iloc[-1]
                price = float(df["close"].iloc[-1])
                print(f"  [{tf} {_symbol_base(symbol)}/USDT] bars={len(df)} price=${price:,.4f}")

        self.history_htf = self._fetch_history("BTC/USDT:USDT", HTF_TIMEFRAME, HISTORY_BARS)
        self.htf_status = htf_strong_trend(self.history_htf)
        for tf in self.exec_timeframes:
            for pair_id in self.active_pair_ids:
                latest_ts = self._update_pair_metrics(pair_id, tf)
                self.last_pair_ts[tf][pair_id] = latest_ts

        for pair_id in self.active_pair_ids:
            preview = self.pair_metrics.get("5m", {}).get(pair_id)
            metrics = preview.get(20) if preview else None
            corr = self.pair_corr.get(pair_id, float("nan"))
            if metrics:
                print(
                    f"  [{pair_id}] ratio={metrics['ratio']:.6f} "
                    f"z={metrics['z']:+.2f} rho={corr:.2f}"
                )
        print(f"[TriArb] Dashboard API: http://localhost:{self.port}/api/state")

    def _aligned_pair_closes(
        self, pair_id: str, tf: str
    ) -> tuple[np.ndarray, np.ndarray, pd.Index] | None:
        leg1_sym = PAIRS[pair_id]["leg1"]
        leg2_sym = PAIRS[pair_id]["leg2"]
        df1 = self.history.get(tf, {}).get(leg1_sym)
        df2 = self.history.get(tf, {}).get(leg2_sym)
        if df1 is None or df2 is None:
            return None
        idx_common = df1.index.intersection(df2.index).sort_values()
        if len(idx_common) == 0:
            return None
        close1 = df1.loc[idx_common, "close"].values.astype(float)
        close2 = df2.loc[idx_common, "close"].values.astype(float)
        return close1, close2, idx_common

    def _update_pair_metrics(self, pair_id: str, tf: str) -> Any:
        aligned = self._aligned_pair_closes(pair_id, tf)
        if aligned is None:
            self.pair_metrics[tf][pair_id] = None
            return None
        close1, close2, idx_common = aligned
        lookbacks = sorted({cfg["ratio_lookback_bars"] for cfg in VARIANTS_CONFIG.values()})
        if len(close1) < max(lookbacks) + 5:
            self.pair_metrics[tf][pair_id] = None
            return idx_common[-1]
        self.pair_metrics[tf][pair_id] = {
            lookback: compute_pair_metrics(close1, close2, lookback) for lookback in lookbacks
        }
        self.pair_corr[pair_id] = compute_pair_correlation(close1, close2, CORR_LOOKBACK_BARS)
        return idx_common[-1]

    def _build_context(
        self,
        pair_id: str,
        tf: str,
        metrics: dict[str, float],
        corr: float,
        direction: str,
    ) -> ContextVector:
        aligned = self._aligned_pair_closes(pair_id, tf)
        leg_vol_ratio = 1.0
        vol_regime = 1.0
        hour = datetime.now(timezone.utc).hour
        if aligned is not None:
            close1, close2, idx = aligned
            ratio = compute_pair_ratio_series(close1, close2)
            if len(idx):
                ts = idx[-1]
                hour = int(getattr(ts, "hour", hour))
            returns1 = np.diff(close1[-61:]) / np.maximum(close1[-61:-1], 1e-12) if len(close1) >= 61 else np.array([])
            returns2 = np.diff(close2[-61:]) / np.maximum(close2[-61:-1], 1e-12) if len(close2) >= 61 else np.array([])
            if len(returns1) and len(returns2):
                v1 = float(np.std(returns1, ddof=0))
                v2 = float(np.std(returns2, ddof=0))
                if v2 > 1e-12:
                    leg_vol_ratio = v1 / v2
            if len(ratio) >= 61:
                abs_delta = np.abs(np.diff(ratio[-61:]))
                atr14 = float(np.mean(abs_delta[-14:]))
                atr60 = float(np.mean(abs_delta))
                if atr60 > 1e-12:
                    vol_regime = atr14 / atr60

        z = float(metrics.get("z", 0.0))
        if direction == "long_ratio":
            z = abs(z)
        return ContextVector(
            spread_zscore=float(abs(z)),
            spread_velocity=float(metrics.get("z_velocity", 0.0)),
            correlation_30d=float(corr) if np.isfinite(corr) else 0.0,
            leg_vol_ratio=float(leg_vol_ratio) if np.isfinite(leg_vol_ratio) else 1.0,
            session_hour_bucket=hour // 4,
            vol_regime=float(vol_regime) if np.isfinite(vol_regime) else 1.0,
        )

    def _record_entry_block(self, pm: VariantPM, reason_s: str, reason_l: str):
        reasons = [reason_s, reason_l]
        if "htf_block" in reasons:
            pm.signals_blocked_htf += 1
        elif "low_corr" in reasons:
            pm.signals_blocked_corr += 1
        elif "velocity_high" in reasons:
            pm.signals_blocked_velocity += 1
        elif "cv_out_of_range" in reasons:
            pm.signals_blocked_cv += 1
        # z_too_low, no_rollover???뺤긽 ?곹깭 ??移댁슫??利앷? ????
    def _process_variant_on_bar(self, variant_name: str, pair_id: str):
        pm = self.variants[variant_name]
        cfg = pm.config
        if pair_id not in cfg["pairs"]:
            return

        tf = cfg["timeframe"]
        metrics_all = self.pair_metrics.get(tf, {}).get(pair_id)
        if metrics_all is None:
            return
        metrics = metrics_all.get(cfg["ratio_lookback_bars"])
        if not metrics:
            return
        if any(not np.isfinite(metrics.get(k, float("nan"))) for k in ("z", "z_velocity", "cv")):
            return

        corr = self.pair_corr[pair_id]
        current_idx = self.bar_idx[tf][pair_id]
        leg1_sym = PAIRS[pair_id]["leg1"]
        leg2_sym = PAIRS[pair_id]["leg2"]
        price_leg1 = float(self.history[tf][leg1_sym]["close"].iloc[-1])
        price_leg2 = float(self.history[tf][leg2_sym]["close"].iloc[-1])
        pm.check_exits(
            pair_id,
            metrics,
            corr,
            price_leg1,
            price_leg2,
            current_idx,
            cfg["time_stop_bars"],
        )

        if pair_id in pm.positions:
            return
        pm.signals_considered += 1

        valid_s, reason_s = check_short_ratio_entry(metrics, corr, cfg, self.htf_status)
        if valid_s:
            ctx = self._build_context(pair_id, tf, metrics, corr, "short_ratio")
            result = pm.try_open(
                pair_id,
                "short_ratio",
                metrics["ratio"],
                metrics["z"],
                price_leg1,
                price_leg2,
                ctx,
                pm.balance,
                current_idx,
            )
            if result is None:
                pair = PAIRS[pair_id]
                pos = pm.positions[pair_id]
                print(
                    f"  [{variant_name} {pair_id}] SHORT_RATIO z={metrics['z']:.2f} "
                    f"corr={corr:.2f} ratio={metrics['ratio']:.6f} "
                    f"size=[{_symbol_base(pair['leg1'])}:{pos.size_leg1:.6f}, "
                    f"{_symbol_base(pair['leg2'])}:{pos.size_leg2:.6f}]"
                )
            return

        valid_l, reason_l = check_long_ratio_entry(metrics, corr, cfg, self.htf_status)
        if valid_l:
            ctx = self._build_context(pair_id, tf, metrics, corr, "long_ratio")
            result = pm.try_open(
                pair_id,
                "long_ratio",
                metrics["ratio"],
                metrics["z"],
                price_leg1,
                price_leg2,
                ctx,
                pm.balance,
                current_idx,
            )
            if result is None:
                pair = PAIRS[pair_id]
                pos = pm.positions[pair_id]
                print(
                    f"  [{variant_name} {pair_id}] LONG_RATIO z={metrics['z']:.2f} "
                    f"corr={corr:.2f} ratio={metrics['ratio']:.6f} "
                    f"size=[{_symbol_base(pair['leg1'])}:{pos.size_leg1:.6f}, "
                    f"{_symbol_base(pair['leg2'])}:{pos.size_leg2:.6f}]"
                )
            return

        self._record_entry_block(pm, reason_s, reason_l)

    def tick(self):
        self.tick_count += 1

        if self.tick_count % HTF_REFRESH_TICKS == 0:
            new_htf = self._fetch_history("BTC/USDT:USDT", HTF_TIMEFRAME, 5)
            if new_htf is not None and len(new_htf) >= 2:
                latest = new_htf.iloc[-2]
                if self.history_htf is None or latest["ts"] != self.history_htf["ts"].iloc[-1]:
                    row = new_htf.iloc[-2:-1]
                    if self.history_htf is None:
                        self.history_htf = row
                    else:
                        self.history_htf = pd.concat([self.history_htf, row]).tail(HISTORY_BARS)
            self.htf_status = htf_strong_trend(self.history_htf)

        for tf in self.exec_timeframes:
            divisor = self._TF_POLL_DIVISOR.get(tf, 1)
            if self.tick_count % divisor != 0:
                continue
            for symbol in self.active_symbols:
                if symbol not in self.history[tf]:
                    continue
                new_df = self._fetch_history(symbol, tf, 5)
                if new_df is None or len(new_df) < 2:
                    continue
                latest = new_df.iloc[-2]
                prev_ts = self.last_bar_ts[tf].get(symbol)
                if prev_ts is not None and latest["ts"] == prev_ts:
                    continue
                row = new_df.iloc[-2:-1]
                self.history[tf][symbol] = pd.concat([self.history[tf][symbol], row]).tail(HISTORY_BARS)
                self.last_bar_ts[tf][symbol] = latest["ts"]

            for pair_id in self.active_pair_ids:
                latest_pair_ts = self._update_pair_metrics(pair_id, tf)
                if latest_pair_ts is None or latest_pair_ts == self.last_pair_ts[tf].get(pair_id):
                    continue
                self.last_pair_ts[tf][pair_id] = latest_pair_ts
                self.bar_idx[tf][pair_id] += 1
                for name, cfg in VARIANTS_CONFIG.items():
                    if cfg["timeframe"] == tf and pair_id in cfg["pairs"]:
                        self._process_variant_on_bar(name, pair_id)

        if self.tick_count % 5 == 0:
            self._log_tick()
        if time.time() - self.last_save > SAVE_INTERVAL:
            self._save_state()
            self.last_save = time.time()

    def _log_tick(self):
        preview_parts = []
        for pair_id in self.active_pair_ids:
            metrics_all = self.pair_metrics.get("5m", {}).get(pair_id)
            metrics = metrics_all.get(20) if metrics_all else None
            if metrics and np.isfinite(metrics.get("z", float("nan"))):
                preview_parts.append(f"{pair_id} z={metrics['z']:+.2f}")
        variant_parts = [
            f"{name.replace('triarb-', '')}={pm.total_return()*100:+.1f}%/{len(pm.trade_log)}t"
            for name, pm in self.variants.items()
        ]
        print(f"  [tick {self.tick_count}] " + " | ".join(preview_parts) + f" | htf={self.htf_status}")
        print(f"  [tick {self.tick_count}] " + " | ".join(variant_parts))
        log_entry = {
            "tick": self.tick_count,
            "t": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "htf_status": self.htf_status,
            "pairs": {
                pid: {
                    "corr": _finite_or_none(self.pair_corr.get(pid)),
                    "z": _finite_or_none(
                        (self.pair_metrics.get("5m", {}).get(pid) or {}).get(20, {}).get("z")
                    ),
                }
                for pid in self.active_pair_ids
            },
            "variants": {
                name: {
                    "ret": round(pm.total_return(), 6),
                    "cap": round(pm.capital, 2),
                    "trades": len(pm.trade_log),
                    "positions": len(pm.positions),
                    "blocked_corr": pm.signals_blocked_corr,
                    "blocked_velocity": pm.signals_blocked_velocity,
                    "blocked_cv": pm.signals_blocked_cv,
                    "blocked_mem": pm.signals_blocked_memory,
                }
                for name, pm in self.variants.items()
            },
        }
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=_json_default) + "\n")

    def snapshot(self) -> dict[str, Any]:
        variants_data = {}
        for name, pm in self.variants.items():
            variants_data[name] = {
                "name": name,
                "config": pm.config,
                "total_return": pm.total_return(),
                "capital": pm.capital,
                "balance": pm.balance,
                "initial_capital": pm.initial_capital,
                "drawdown": pm.drawdown(),
                "peak_balance": pm.peak_balance,
                "win_rate": pm.win_rate(),
                "total_trades": len(pm.trade_log),
                "trade_count": pm.trade_count,
                "win_count": pm.win_count,
                "positions": pm.position_snapshots(),
                "pnl_history": pm.pnl_history[-300:],
                "trade_log": pm.trade_log[-50:],
                "memory": pm.memory.snapshot(),
                "memory_count": len(pm.memory.records),
                "signals_considered": pm.signals_considered,
                "signals_executed": pm.signals_executed,
                "signals_blocked_memory": pm.signals_blocked_memory,
                "signals_blocked_htf": pm.signals_blocked_htf,
                "signals_blocked_corr": pm.signals_blocked_corr,
                "signals_blocked_z": pm.signals_blocked_z,
                "signals_blocked_velocity": pm.signals_blocked_velocity,
                "signals_blocked_cv": pm.signals_blocked_cv,
                "signals": {
                    "considered": pm.signals_considered,
                    "blocked_chop": pm.signals_blocked_chop,
                    "blocked_rr": pm.signals_blocked_rr,
                    "blocked_memory": pm.signals_blocked_memory,
                    "blocked_htf": pm.signals_blocked_htf,
                    "blocked_corr": pm.signals_blocked_corr,
                    "blocked_z": pm.signals_blocked_z,
                    "blocked_velocity": pm.signals_blocked_velocity,
                    "blocked_cv": pm.signals_blocked_cv,
                    "executed": pm.signals_executed,
                },
            }

        preview = {}
        for pair_id in self.active_pair_ids:
            metrics_all = self.pair_metrics.get("5m", {}).get(pair_id)
            metrics = metrics_all.get(20) if metrics_all else None
            preview[pair_id] = (
                {
                    "z": _finite_or_none(metrics.get("z")),
                    "ratio": _finite_or_none(metrics.get("ratio")),
                    "cv": _finite_or_none(metrics.get("cv")),
                }
                if metrics
                else None
            )

        return {
            "tick": self.tick_count,
            "model": "TriArb",
            "assets": self.active_symbols,
            "exec_timeframes": self.exec_timeframes,
            "htf_timeframe": HTF_TIMEFRAME,
            "htf_status": self.htf_status,
            "active_pairs": self.active_pair_ids,
            "pair_definitions": PAIRS,
            "pair_correlations": {
                pid: _finite_or_none(corr) for pid, corr in self.pair_corr.items()
            },
            "pair_metrics_preview": preview,
            "variants": variants_data,
            "variant_configs": {name: pm.config for name, pm in self.variants.items()},
            "memory_warmup": MEMORY_WARMUP_TRADES,
            "memory_full_activation": MEMORY_FULL_ACTIVATION,
        }

    def _save_state(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            state: dict[str, Any] = {
                "tick_count": np.array([self.tick_count]),
                "pair_corr_keys": np.array(list(self.pair_corr.keys())),
                "pair_corr_values": np.array([self.pair_corr[k] for k in self.pair_corr.keys()]),
            }
            bar_idx_tfs: list[str] = []
            bar_idx_pairs: list[str] = []
            bar_idx_values: list[int] = []
            for tf, per_pair in self.bar_idx.items():
                for pair_id, idx in per_pair.items():
                    bar_idx_tfs.append(tf)
                    bar_idx_pairs.append(pair_id)
                    bar_idx_values.append(int(idx))
            state["bar_idx_tfs"] = np.array(bar_idx_tfs)
            state["bar_idx_pairs"] = np.array(bar_idx_pairs)
            state["bar_idx_values"] = np.array(bar_idx_values)
            for name, pm in self.variants.items():
                state[f"{name}_capital"] = np.array([pm.capital])
                state[f"{name}_peak"] = np.array([pm.peak_capital])
                state[f"{name}_pnl"] = np.array(pm.pnl_history[-1000:])
            np.savez_compressed(STATE_PATH, **state)

            blob = {"memory": {}, "trade_logs": {}, "positions": {}}
            for name, pm in self.variants.items():
                blob["memory"][name] = [asdict(r) for r in pm.memory.records[-500:]]
                blob["trade_logs"][name] = pm.trade_log[-200:]
                blob["positions"][name] = [asdict(p) for p in pm.positions.values()]
            with open(MEMORY_PATH, "w", encoding="utf-8") as f:
                json.dump(blob, f, default=_json_default)
            print("  [save] TriArb state + memory persisted")
        except Exception as e:
            print(f"  [save] error: {e}")

    def _load_state(self):
        if not STATE_PATH.exists():
            return
        try:
            d = np.load(STATE_PATH, allow_pickle=True)
            if "tick_count" in d:
                self.tick_count = int(d["tick_count"][0])
            if "pair_corr_keys" in d and "pair_corr_values" in d:
                for key, value in zip(d["pair_corr_keys"].tolist(), d["pair_corr_values"].tolist()):
                    self.pair_corr[str(key)] = float(value)
            if {"bar_idx_tfs", "bar_idx_pairs", "bar_idx_values"} <= set(d.files):
                for tf, pair_id, idx in zip(
                    d["bar_idx_tfs"].tolist(),
                    d["bar_idx_pairs"].tolist(),
                    d["bar_idx_values"].tolist(),
                ):
                    tf = str(tf)
                    pair_id = str(pair_id)
                    if tf in self.bar_idx and pair_id in self.bar_idx[tf]:
                        self.bar_idx[tf][pair_id] = int(idx)
            for name, pm in self.variants.items():
                if f"{name}_capital" in d:
                    pm.capital = float(d[f"{name}_capital"][0])
                if f"{name}_peak" in d:
                    pm.peak_capital = float(d[f"{name}_peak"][0])
                if f"{name}_pnl" in d:
                    pm.pnl_history = d[f"{name}_pnl"].tolist()
            if MEMORY_PATH.exists():
                with open(MEMORY_PATH, encoding="utf-8") as f:
                    blob = json.load(f)
                for name, pm in self.variants.items():
                    for rec in blob.get("memory", {}).get(name, []):
                        pm.memory.records.append(TradeRecord(**rec))
                    pm.trade_log = blob.get("trade_logs", {}).get(name, [])
                    for raw_pos in blob.get("positions", {}).get(name, []):
                        ctx_raw = raw_pos.get("entry_context", {})
                        if isinstance(ctx_raw, dict):
                            raw_pos["entry_context"] = ContextVector(**ctx_raw)
                        pm.positions[raw_pos["pair_id"]] = PairPosition(**raw_pos)
            print(f"  [load] TriArb tick={self.tick_count} variants restored")
        except Exception as e:
            print(f"  [load] error: {e}")

    def run(self):
        self._load_state()
        self.init()
        DashboardHandler.engine = self
        server = http.server.HTTPServer(("0.0.0.0", self.port), DashboardHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        while True:
            try:
                self.tick()
            except KeyboardInterrupt:
                self._save_state()
                print("\n[TriArb] Stopped. State saved.")
                break
            except Exception as e:
                print(f"  [error] {e}")
                import traceback

                traceback.print_exc()
            time.sleep(TICK_SEC)


# =====================================================================
# API Handler
# =====================================================================
class DashboardHandler(http.server.BaseHTTPRequestHandler):
    engine: Any = None

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/api/state"):
            body = json.dumps(self.engine.snapshot(), default=_json_default).encode()
            self.send_response(200)

 succeeded in 592ms:
"""Unified Paper Trading Dashboard.

Proxies and displays all running models in one view.
- V2 Prediction Engine (port 8897)
- V3 Parker Brooks + Self-Learn (port 8898)
- TriArb Pairs Ratio (port 8899)

Usage:
    py -3.12 scripts/dashboard_unified.py [--port 8900]

Dashboard:
    http://127.0.0.1:8900
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
    "v2":         {"port": 8897, "name": "V2 Prediction Engine",           "color": "#00ccff"},
    "v3":         {"port": 8898, "name": "V3 Parker Brooks + Self-Learn",  "color": "#aa66ff"},
    "triarb":     {"port": 8899, "name": "TriArb (Pairs Ratio)",           "color": "#66ffaa"},
}


def fetch_model_state(port: int) -> dict | None:
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/state",
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
        # /api/all ??aggregate all models
        # /api/tournament ??proxy to 8895
        # /api/v2 ??proxy to 8897
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

codex
메모리 병목은 저장보다 조회 경로가 더 중요합니다. `ContextMemory.records`가 무한히 늘고 `snapshot()`이나 k-NN이 전체를 매번 선형 스캔하면, 10k trades에서 CPU는 저장보다 추론 시점에 먼저 터집니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content scripts\\v3.py | Select-Object -Skip 440 -First 90" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content scripts\\triarb.py | Select-Object -Skip 440 -First 90" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "rg -n \"trade_log = \\[\\]|self.trade_log.append|self.records.append|pnl_history.append|positions\\[|del self.positions|snapshot\\(\" scripts\\v3.py scripts\\triarb.py" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 400ms:
        distances = [(self._distance(target, np.array(r.context, dtype=float)), r) for r in same_dir]
        distances.sort(key=lambda x: x[0])
        return [r for _, r in distances[: min(k, len(distances))]]

    def query_ev(self, ctx: ContextVector, direction: str) -> tuple[float, int]:
        neighbors = self._neighbors(ctx, direction, KNN_K)
        if not neighbors:
            return 0.0, 0
        return float(np.mean([r.r_multiple for r in neighbors])), len(neighbors)

    def is_blacklisted(self, ctx: ContextVector, direction: str) -> bool:
        if len(self.records) < MEMORY_WARMUP_TRADES:
            return False
        cluster = self._neighbors(ctx, direction, MEMORY_MIN_SAMPLES_FOR_BLACKLIST)
        if len(cluster) < MEMORY_MIN_SAMPLES_FOR_BLACKLIST:
            return False
        cluster_ev = float(np.mean([r.r_multiple for r in cluster]))
        return cluster_ev < MEMORY_BLACKLIST_EV_THRESHOLD

    def size_multiplier(self, ctx: ContextVector, direction: str, total_trades: int) -> float:
        if total_trades < MEMORY_WARMUP_TRADES:
            return 1.0
        ev, n = self.query_ev(ctx, direction)
        if n == 0:
            return 1.0
        if total_trades >= MEMORY_FULL_ACTIVATION:
            weight = 1.0
        else:
            span = MEMORY_FULL_ACTIVATION - MEMORY_WARMUP_TRADES
            weight = (total_trades - MEMORY_WARMUP_TRADES) / span
        if ev > MEMORY_BOOST_EV_THRESHOLD:
            boost = min((ev - MEMORY_BOOST_EV_THRESHOLD) * 1.0, 0.5)
            return 1.0 + boost * weight
        if ev < 0:
            penalty = min(abs(ev) * 0.5, 0.5)
            return max(0.5, 1.0 - penalty * weight)
        return 1.0

    def snapshot(self) -> dict[str, Any]:
        if not self.records:
            return {
                "n_trades": 0,
                "ev_long": 0.0,
                "ev_short": 0.0,
                "win_rate": 0.0,
                "avg_r": 0.0,
                "blacklisted_clusters": 0,
            }
        rs = [r.r_multiple for r in self.records]
        longs = [r.r_multiple for r in self.records if r.direction == "long_ratio"]
        shorts = [r.r_multiple for r in self.records if r.direction == "short_ratio"]
        wins = sum(1 for r in rs if r > 0)
        bl_count = 0
        for rec in self.records[-50:]:
            arr = np.array(rec.context, dtype=float)
            ctx = ContextVector(
                spread_zscore=arr[0],
                spread_velocity=arr[1],
                correlation_30d=arr[2],
                leg_vol_ratio=arr[3],
                session_hour_bucket=int(arr[4]),
                vol_regime=arr[5],
            )
            if self.is_blacklisted(ctx, rec.direction):
                bl_count += 1
        return {
            "n_trades": len(self.records),
            "ev_long": float(np.mean(longs)) if longs else 0.0,
            "ev_short": float(np.mean(shorts)) if shorts else 0.0,
            "win_rate": wins / len(rs),
            "avg_r": float(np.mean(rs)),
            "blacklisted_clusters": bl_count,
        }


# =====================================================================
# Position Manager
# =====================================================================
@dataclass
class PairPosition:
    pair_id: str
    direction: str
    entry_ratio: float
    entry_z: float
    entry_price_leg1: float
    entry_price_leg2: float
    size_leg1: float
    size_leg2: float
    notional_per_leg_usd: float
    leverage: float

 succeeded in 319ms:
scripts\triarb.py:429:        self.records.append(record)
scripts\triarb.py:479:    def snapshot(self) -> dict[str, Any]:
scripts\triarb.py:602:        self.positions[pair_id] = PairPosition(
scripts\triarb.py:633:        pos = self.positions[pair_id]
scripts\triarb.py:674:        self.pnl_history.append(self.capital)
scripts\triarb.py:694:        self.trade_log.append(
scripts\triarb.py:991:                pos = pm.positions[pair_id]
scripts\triarb.py:1016:                pos = pm.positions[pair_id]
scripts\triarb.py:1119:    def snapshot(self) -> dict[str, Any]:
scripts\triarb.py:1138:                "memory": pm.memory.snapshot(),
scripts\triarb.py:1269:                        pm.positions[raw_pos["pair_id"]] = PairPosition(**raw_pos)
scripts\triarb.py:1307:            body = json.dumps(self.engine.snapshot(), default=_json_default).encode()
scripts\v3.py:417:        self.records.append(record)
scripts\v3.py:485:    def snapshot(self) -> dict:
scripts\v3.py:594:        self.positions[asset] = V3Position(
scripts\v3.py:609:        pos = self.positions[asset]
scripts\v3.py:651:        self.pnl_history.append(self.capital)
scripts\v3.py:672:        self.trade_log.append({
scripts\v3.py:741:    def _compute_snapshot(self, df: pd.DataFrame) -> MarketSnapshot | None:
scripts\v3.py:805:        snap = self._compute_snapshot(df)
scripts\v3.py:1007:    def snapshot(self) -> dict:
scripts\v3.py:1010:            ms = pm.memory.snapshot()
scripts\v3.py:1138:            body = json.dumps(self.engine.snapshot()).encode()

 succeeded in 463ms:
        neighbors = self._neighbors(ctx, direction, KNN_K)
        if not neighbors:
            return 0.0, 0
        ev = float(np.mean([r.r_multiple for r in neighbors]))
        return ev, len(neighbors)

    def is_blacklisted(self, ctx: ContextVector, direction: str) -> bool:
        """Blacklist check uses a larger neighborhood for statistical significance."""
        cluster = self._neighbors(ctx, direction, MEMORY_MIN_SAMPLES_FOR_BLACKLIST)
        if len(cluster) < MEMORY_MIN_SAMPLES_FOR_BLACKLIST:
            return False
        cluster_ev = float(np.mean([r.r_multiple for r in cluster]))
        return cluster_ev < MEMORY_BLACKLIST_EV_THRESHOLD

    def size_multiplier(self, ctx: ContextVector, direction: str, total_trades: int) -> float:
        """Returns position size multiplier in [0, 1.5] based on context EV.

        Warmup: no memory effect until MEMORY_WARMUP_TRADES.
        Gradual activation between warmup and full-activation.
        """
        if total_trades < MEMORY_WARMUP_TRADES:
            return 1.0

        ev, n = self.query_ev(ctx, direction)
        if n == 0:
            return 1.0

        # Activation weight ramps 0->1 between WARMUP and FULL
        if total_trades >= MEMORY_FULL_ACTIVATION:
            weight = 1.0
        else:
            span = MEMORY_FULL_ACTIVATION - MEMORY_WARMUP_TRADES
            weight = (total_trades - MEMORY_WARMUP_TRADES) / span

        # Base multiplier: 1.0. Scale by EV with clip.
        if ev > MEMORY_BOOST_EV_THRESHOLD:
            boost = min((ev - MEMORY_BOOST_EV_THRESHOLD) * 1.0, 0.5)  # max +50%
            return 1.0 + boost * weight
        elif ev < 0:
            # Soft penalty before blacklist threshold
            penalty = min(abs(ev) * 0.5, 0.5)  # max -50%
            return max(0.5, 1.0 - penalty * weight)
        return 1.0

    def snapshot(self) -> dict:
        if not self.records:
            return {
                "n_trades": 0,
                "ev_long": 0.0,
                "ev_short": 0.0,
                "win_rate": 0.0,
                "avg_r": 0.0,
                "blacklisted_clusters": 0,
            }
        rs = [r.r_multiple for r in self.records]
        longs = [r.r_multiple for r in self.records if r.direction == "long"]
        shorts = [r.r_multiple for r in self.records if r.direction == "short"]
        wins = sum(1 for r in rs if r > 0)
        # Rough blacklist count: sample centers of each record and test
        bl_count = 0
        # Sample-based: count how many past contexts ARE currently blacklisted
        for r in self.records[-50:]:  # recent only for efficiency
            arr = np.array(r.context)
            ctx = ContextVector(
                vwap_slope=arr[0], ema_dist_atr=arr[1], vp_clearance_atr=arr[2],
                rr_estimate=arr[3], session_hour_bucket=int(arr[4]), vol_regime=arr[5],
            )
            if self.is_blacklisted(ctx, r.direction):
                bl_count += 1
        return {
            "n_trades": len(self.records),
            "ev_long": float(np.mean(longs)) if longs else 0.0,
            "ev_short": float(np.mean(shorts)) if shorts else 0.0,
            "win_rate": wins / len(rs),
            "avg_r": float(np.mean(rs)),
            "blacklisted_clusters": bl_count,
        }


# ===================================================================
# Position + Position Manager (per-variant)
# ===================================================================
@dataclass
class V3Position:
    asset: str
    direction: str
    entry_price: float
    hard_stop: float
    soft_stop_ref: float        # EMA9 +/- buffer
    target_price: float         # first HVN

exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "rg -n \"add_argument\\(|VARIANTS_CONFIG|PAIRS =|TICK_SEC|SAVE_INTERVAL|HTF_REFRESH_TICKS|_TF_POLL_DIVISOR|MEMORY_PATH|STATE_PATH|urlopen\\(|MODELS =|HTTPServer\\(|/api/state|trade_log\\[-|records\\[-|self.records.append|distances.sort|time.sleep\\(\" scripts\\v3.py scripts\\triarb.py scripts\\dashboard_unified.py scripts\\v2.py" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 339ms:
scripts\v2.py:46:STATE_PATH = DATA_DIR / "v2_state.npz"
scripts\v2.py:49:TICK_SEC = 60
scripts\v2.py:52:SAVE_INTERVAL = 1800
scripts\v2.py:487:        if self.path == "/api/state":
scripts\v2.py:570:    const d=await(await fetch('/api/state')).json();
scripts\v2.py:766:        if time.time() - self.last_save > SAVE_INTERVAL:
scripts\v2.py:838:            "trade_log": self.pm.trade_log[-50:],
scripts\v2.py:852:            np.savez_compressed(STATE_PATH, **state)
scripts\v2.py:853:            print(f"  [save] state → {STATE_PATH}")
scripts\v2.py:858:        if not STATE_PATH.exists():
scripts\v2.py:861:            d = np.load(STATE_PATH, allow_pickle=True)
scripts\v2.py:882:        server = http.server.HTTPServer(("0.0.0.0", self.port), DashboardHandler)
scripts\v2.py:895:            time.sleep(TICK_SEC)
scripts\v2.py:900:    parser.add_argument("--assets", default="ETH,BTC,SOL,XRP")
scripts\v2.py:901:    parser.add_argument("--port", type=int, default=DASH_PORT)
scripts\triarb.py:46:STATE_PATH = DATA_DIR / "triarb_state.npz"
scripts\triarb.py:48:MEMORY_PATH = DATA_DIR / "triarb_memory.json"
scripts\triarb.py:51:TICK_SEC = 60
scripts\triarb.py:54:SAVE_INTERVAL = 1800
scripts\triarb.py:69:HTF_REFRESH_TICKS = 15
scripts\triarb.py:86:PAIRS = {
scripts\triarb.py:93:VARIANTS_CONFIG = {
scripts\triarb.py:429:        self.records.append(record)
scripts\triarb.py:442:        distances.sort(key=lambda x: x[0])
scripts\triarb.py:494:        for rec in self.records[-50:]:
scripts\triarb.py:768:        self.active_pair_ids = sorted({p for cfg in VARIANTS_CONFIG.values() for p in cfg["pairs"]})
scripts\triarb.py:774:            {cfg["timeframe"] for cfg in VARIANTS_CONFIG.values()},
scripts\triarb.py:780:        self.variants = {name: VariantPM(name, cfg) for name, cfg in VARIANTS_CONFIG.items()}
scripts\triarb.py:795:    _TF_POLL_DIVISOR = {"5m": 1, "30m": 5, "1h": 10}
scripts\triarb.py:849:        print(f"[TriArb] Dashboard API: http://localhost:{self.port}/api/state")
scripts\triarb.py:873:        lookbacks = sorted({cfg["ratio_lookback_bars"] for cfg in VARIANTS_CONFIG.values()})
scripts\triarb.py:1030:        if self.tick_count % HTF_REFRESH_TICKS == 0:
scripts\triarb.py:1043:            divisor = self._TF_POLL_DIVISOR.get(tf, 1)
scripts\triarb.py:1066:                for name, cfg in VARIANTS_CONFIG.items():
scripts\triarb.py:1072:        if time.time() - self.last_save > SAVE_INTERVAL:
scripts\triarb.py:1137:                "trade_log": pm.trade_log[-50:],
scripts\triarb.py:1218:            np.savez_compressed(STATE_PATH, **state)
scripts\triarb.py:1222:                blob["memory"][name] = [asdict(r) for r in pm.memory.records[-500:]]
scripts\triarb.py:1223:                blob["trade_logs"][name] = pm.trade_log[-200:]
scripts\triarb.py:1225:            with open(MEMORY_PATH, "w", encoding="utf-8") as f:
scripts\triarb.py:1232:        if not STATE_PATH.exists():
scripts\triarb.py:1235:            d = np.load(STATE_PATH, allow_pickle=True)
scripts\triarb.py:1258:            if MEMORY_PATH.exists():
scripts\triarb.py:1259:                with open(MEMORY_PATH, encoding="utf-8") as f:
scripts\triarb.py:1278:        server = http.server.HTTPServer(("0.0.0.0", self.port), DashboardHandler)
scripts\triarb.py:1293:            time.sleep(TICK_SEC)
scripts\triarb.py:1306:        if self.path.startswith("/api/state"):
scripts\triarb.py:1314:            msg = b"TriArb API running. Use /api/state."
scripts\triarb.py:1324:    parser.add_argument("--port", type=int, default=DASH_PORT)
scripts\dashboard_unified.py:26:MODELS = {
scripts\dashboard_unified.py:36:            f"http://127.0.0.1:{port}/api/state",
scripts\dashboard_unified.py:39:        with urllib.request.urlopen(req, timeout=3) as resp:
scripts\dashboard_unified.py:692:    parser.add_argument("--port", type=int, default=PORT)
scripts\dashboard_unified.py:695:    server = http.server.HTTPServer(("0.0.0.0", args.port), Handler)
scripts\v3.py:48:STATE_PATH = DATA_DIR / "v3_state.npz"
scripts\v3.py:50:MEMORY_PATH = DATA_DIR / "v3_memory.json"
scripts\v3.py:52:TICK_SEC = 60
scripts\v3.py:55:SAVE_INTERVAL = 1800
scripts\v3.py:81:HTF_REFRESH_TICKS = 15     # refresh 1h bias every 15 minutes (tick = 60s)
scripts\v3.py:86:VARIANTS_CONFIG = {
scripts\v3.py:417:        self.records.append(record)
scripts\v3.py:435:        distances.sort(key=lambda x: x[0])
scripts\v3.py:502:        for r in self.records[-50:]:  # recent only for efficiency
scripts\v3.py:712:        self.exec_timeframes: list[str] = sorted({cfg["timeframe"] for cfg in VARIANTS_CONFIG.values()})
scripts\v3.py:720:            name: VariantPM(name, cfg) for name, cfg in VARIANTS_CONFIG.items()
scripts\v3.py:891:              f"| {len(VARIANTS_CONFIG)} variants")
scripts\v3.py:915:        print(f"[V3] Dashboard API: http://localhost:{self.port}/api/state")
scripts\v3.py:918:    _TF_POLL_DIVISOR = {"1m": 1, "3m": 1, "5m": 1, "15m": 3, "30m": 5}
scripts\v3.py:923:        # --- HTF (1h) refresh every HTF_REFRESH_TICKS ---
scripts\v3.py:924:        if self.tick_count % HTF_REFRESH_TICKS == 0:
scripts\v3.py:943:                divisor = self._TF_POLL_DIVISOR.get(tf, 1)
scripts\v3.py:967:                for name, cfg in VARIANTS_CONFIG.items():
scripts\v3.py:975:        if time.time() - self.last_save > SAVE_INTERVAL:
scripts\v3.py:1030:                "trade_log": pm.trade_log[-30:],
scripts\v3.py:1045:            "variant_configs": VARIANTS_CONFIG,
scripts\v3.py:1062:            np.savez_compressed(STATE_PATH, **state)
scripts\v3.py:1067:                memory_blob[name] = [asdict(r) for r in pm.memory.records[-500:]]
scripts\v3.py:1068:                trade_logs[name] = pm.trade_log[-200:]
scripts\v3.py:1069:            with open(MEMORY_PATH, "w") as f:
scripts\v3.py:1076:        if not STATE_PATH.exists():
scripts\v3.py:1079:            d = np.load(STATE_PATH, allow_pickle=True)
scripts\v3.py:1091:            if MEMORY_PATH.exists():
scripts\v3.py:1092:                with open(MEMORY_PATH) as f:
scripts\v3.py:1109:        server = http.server.HTTPServer(("0.0.0.0", self.port), DashboardHandler)
scripts\v3.py:1124:            time.sleep(TICK_SEC)
scripts\v3.py:1137:        if self.path.startswith("/api/state"):
scripts\v3.py:1145:            msg = b"V3 API running. Use /api/state."
scripts\v3.py:1155:    parser.add_argument("--assets", default="ETH,BTC,SOL,XRP")
scripts\v3.py:1156:    parser.add_argument("--port", type=int, default=DASH_PORT)

exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content scripts\\triarb.py | Select-Object -Skip 90 -First 70" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 407ms:
}

VARIANTS_CONFIG = {
    "triarb-5m": dict(
        timeframe="5m",
        ratio_lookback_bars=20,
        entry_z=2.0,
        exit_target_z=0.5,
        exit_stop_z=3.5,
        time_stop_bars=24,
        max_velocity=1.0,
        pairs=["ETHBTC", "SOLETH", "XRPBTC", "SOLBTC"],
        memory=True,
        htf_filter=False,
    ),
    "triarb-30m": dict(
        timeframe="30m",
        ratio_lookback_bars=20,
        entry_z=2.0,
        exit_target_z=0.5,
        exit_stop_z=3.5,
        time_stop_bars=8,
        max_velocity=1.0,
        pairs=["ETHBTC", "SOLETH", "XRPBTC", "SOLBTC"],
        memory=True,
        htf_filter=False,
    ),
    # "daily" variant??1h TF 湲곕컲 ?κ린 ?쒓컖 吏꾩엯. 吏꾩쭨 1d(?쇰큺) ?꾨떂.
    "triarb-daily": dict(
        timeframe="1h",
        ratio_lookback_bars=48,
        entry_z=2.5,
        exit_target_z=0.5,
        exit_stop_z=4.0,
        time_stop_bars=12,
        max_velocity=1.0,
        pairs=["ETHBTC", "SOLETH"],
        memory=True,
        htf_filter=True,
    ),
    "triarb-tight": dict(
        timeframe="5m",
        ratio_lookback_bars=20,
        entry_z=1.5,
        exit_target_z=0.3,
        exit_stop_z=3.0,
        time_stop_bars=16,
        max_velocity=1.2,
        pairs=["ETHBTC", "SOLETH", "XRPBTC", "SOLBTC"],
        memory=True,
        htf_filter=False,
    ),
    "triarb-control": dict(
        timeframe="5m",
        ratio_lookback_bars=20,
        entry_z=2.0,
        exit_target_z=0.5,
        exit_stop_z=3.5,
        time_stop_bars=24,
        max_velocity=1.0,
        pairs=["ETHBTC", "SOLETH", "XRPBTC", "SOLBTC"],
        memory=False,
        htf_filter=False,
    ),
}

_TF_ORDER = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60}


def _finite_or_none(value: Any) -> float | None:

exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "rg -n \"@dataclass\\s*class TradeRecord|class TradeRecord|ContextVector|r_multiple|context:|entry_context\" scripts\\v3.py scripts\\triarb.py" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content data\\v3_memory.json | Select-Object -First 80" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content data\\triarb_memory.json | Select-Object -First 80" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 345ms:
scripts\v3.py:77:#   - HTF context: 1h (standard for scalping confluence). Daily for swing.
scripts\v3.py:376:class ContextVector:
scripts\v3.py:392:class TradeRecord:
scripts\v3.py:393:    context: list[float]        # ContextVector as array
scripts\v3.py:397:    r_multiple: float           # PnL in R units (hard stop distance)
scripts\v3.py:427:    def _neighbors(self, ctx: ContextVector, direction: str, k: int) -> list[TradeRecord]:
scripts\v3.py:439:    def query_ev(self, ctx: ContextVector, direction: str) -> tuple[float, int]:
scripts\v3.py:444:        ev = float(np.mean([r.r_multiple for r in neighbors]))
scripts\v3.py:447:    def is_blacklisted(self, ctx: ContextVector, direction: str) -> bool:
scripts\v3.py:452:        cluster_ev = float(np.mean([r.r_multiple for r in cluster]))
scripts\v3.py:455:    def size_multiplier(self, ctx: ContextVector, direction: str, total_trades: int) -> float:
scripts\v3.py:495:        rs = [r.r_multiple for r in self.records]
scripts\v3.py:496:        longs = [r.r_multiple for r in self.records if r.direction == "long"]
scripts\v3.py:497:        shorts = [r.r_multiple for r in self.records if r.direction == "short"]
scripts\v3.py:504:            ctx = ContextVector(
scripts\v3.py:534:    entry_context: ContextVector
scripts\v3.py:559:                 target: float, soft_stop_ref: float, ctx: ContextVector) -> str | None:
scripts\v3.py:599:            entry_context=ctx,
scripts\v3.py:661:            context=pos.entry_context.to_array().tolist(),
scripts\v3.py:665:            r_multiple=r_mult,
scripts\v3.py:784:    def _make_context(self, snap: MarketSnapshot, vp_distance: float, rr: float) -> ContextVector:
scripts\v3.py:785:        return ContextVector(
scripts\triarb.py:386:class ContextVector:
scripts\triarb.py:409:class TradeRecord:
scripts\triarb.py:410:    context: list[float]
scripts\triarb.py:414:    r_multiple: float
scripts\triarb.py:436:    def _neighbors(self, ctx: ContextVector, direction: str, k: int) -> list[TradeRecord]:
scripts\triarb.py:445:    def query_ev(self, ctx: ContextVector, direction: str) -> tuple[float, int]:
scripts\triarb.py:449:        return float(np.mean([r.r_multiple for r in neighbors])), len(neighbors)
scripts\triarb.py:451:    def is_blacklisted(self, ctx: ContextVector, direction: str) -> bool:
scripts\triarb.py:457:        cluster_ev = float(np.mean([r.r_multiple for r in cluster]))
scripts\triarb.py:460:    def size_multiplier(self, ctx: ContextVector, direction: str, total_trades: int) -> float:
scripts\triarb.py:489:        rs = [r.r_multiple for r in self.records]
scripts\triarb.py:490:        longs = [r.r_multiple for r in self.records if r.direction == "long_ratio"]
scripts\triarb.py:491:        shorts = [r.r_multiple for r in self.records if r.direction == "short_ratio"]
scripts\triarb.py:496:            ctx = ContextVector(
scripts\triarb.py:533:    entry_context: ContextVector
scripts\triarb.py:583:        ctx: ContextVector,
scripts\triarb.py:615:            entry_context=ctx,
scripts\triarb.py:681:            context=pos.entry_context.to_array().tolist(),
scripts\triarb.py:685:            r_multiple=float(r_mult),
scripts\triarb.py:890:    ) -> ContextVector:
scripts\triarb.py:918:        return ContextVector(
scripts\triarb.py:1266:                        ctx_raw = raw_pos.get("entry_context", {})
scripts\triarb.py:1268:                            raw_pos["entry_context"] = ContextVector(**ctx_raw)

 succeeded in 431ms:
{"memory": {"v3-3m": [{"context": [0.009392126650245483, 0.138342124980445, 2.4839760638298602, 2.1207425068119274, 5.0, 0.8544969035850088], "direction": "long", "entry_price": 75891.2, "exit_price": 76077.995, "r_multiple": 2.1207425068119274, "net_pct": 0.010206762839433548, "asset": "BTC", "timestamp": "22:09:37"}, {"context": [0.01512648560700651, 0.07295717629033933, 1.6250206916402692, 1.6041612271244376, 5.0, 0.7820991632729543], "direction": "long", "entry_price": 75927.6, "exit_price": 75860.57535714285, "r_multiple": -1.0, "net_pct": -0.006513720627094442, "asset": "BTC", "timestamp": "23:03:34"}], "v3-5m": [{"context": [-0.009064666772060437, -0.26811805286088924, 3.151400933955932, 5.6652275589133625, 0.0, 0.6971741733943632], "direction": "short", "entry_price": 2276.66, "exit_price": 2279.0424285714284, "r_multiple": -1.0, "net_pct": -0.007332288904423177, "asset": "ETH", "timestamp": "02:50:57"}, {"context": [0.029930766743391502, 0.18691648789898294, 2.090904168922544, 1.7076341447235688, 5.0, 0.8102476365949408], "direction": "long", "entry_price": 75964.1, "exit_price": 75880.6, "r_multiple": -0.6461276558112312, "net_pct": -0.00759601719759707, "asset": "BTC", "timestamp": "22:50:20"}, {"context": [0.031018005401202337, 0.11108409237611962, 4.410895166534348, 2.1735571762468395, 5.0, 0.8638962400758856], "direction": "long", "entry_price": 75748.7, "exit_price": 75693.4, "r_multiple": -0.27563225061102564, "net_pct": -0.0057502276606731335, "asset": "BTC", "timestamp": "00:10:45"}], "v3-15m": [], "v3-30m": [], "v3-5m-aggressive": [{"context": [-0.009064666772060437, -0.26811805286088924, 3.151400933955932, 5.6652275589133625, 0.0, 0.6971741733943632], "direction": "short", "entry_price": 2276.66, "exit_price": 2279.0424285714284, "r_multiple": -1.0, "net_pct": -0.007332288904423177, "asset": "ETH", "timestamp": "02:50:57"}, {"context": [0.019398304889944974, 0.36110829346598955, 1.9789617114048004, 1.4577756364894185, 5.0, 0.7939032041712675], "direction": "long", "entry_price": 75977.3, "exit_price": 75880.6, "r_multiple": -0.6794240603842553, "net_pct": -0.008463742854773592, "asset": "BTC", "timestamp": "22:50:20"}, {"context": [0.031018005401202337, 0.11108409237611962, 4.410895166534348, 2.1735571762468395, 5.0, 0.8638962400758856], "direction": "long", "entry_price": 75748.7, "exit_price": 75693.4, "r_multiple": -0.27563225061102564, "net_pct": -0.0057502276606731335, "asset": "BTC", "timestamp": "00:10:45"}], "v3-5m-conservative": [{"context": [-0.009064666772060437, -0.26811805286088924, 3.151400933955932, 5.6652275589133625, 0.0, 0.6971741733943632], "direction": "short", "entry_price": 2276.66, "exit_price": 2279.0424285714284, "r_multiple": -1.0, "net_pct": -0.007332288904423177, "asset": "ETH", "timestamp": "02:50:57"}, {"context": [0.031018005401202337, 0.11108409237611962, 4.410895166534348, 2.1735571762468395, 5.0, 0.8638962400758856], "direction": "long", "entry_price": 75748.7, "exit_price": 75693.4, "r_multiple": -0.27563225061102564, "net_pct": -0.0057502276606731335, "asset": "BTC", "timestamp": "00:10:45"}], "v3-control": [{"context": [0.2338840538171816, 0.2603980894454294, 3.0856655290102974, 2.420939884857439, 0.0, 0.9046932894195141], "direction": "long", "entry_price": 2273.58, "exit_price": 2276.86, "r_multiple": 0.4391484803856176, "net_pct": 0.005113293572252421, "asset": "ETH", "timestamp": "01:25:58"}, {"context": [0.06959539748924956, 0.5979664335954428, 2.6233601748718476, 3.6723872780806905, 0.0, 0.8967505278860902], "direction": "long", "entry_price": 74210.9, "exit_price": 74191.0, "r_multiple": -0.18805455337040097, "net_pct": -0.0034407733904313715, "asset": "BTC", "timestamp": "01:25:58"}, {"context": [0.20989857333623485, 0.28197489827144223, 5.713513513513545, 3.0838803792851843, 0.0, 0.9286760092030885], "direction": "long", "entry_price": 83.76, "exit_price": 83.95, "r_multiple": 0.48504741064915463, "net_pct": 0.009241929321871945, "asset": "SOL", "timestamp": "01:25:58"}, {"context": [0.20886044857558672, 0.5620812063736464, 1.9221405228758297, 2.6211007130128023, 0.0, 0.845946506323867], "direction": "long", "entry_price": 1.406, "exit_price": 1.4046, "r_multiple": -0.6550802139037453, "net_pct": -0.007078662873399431, "asset": "XRP", "timestamp": "01:25:58"}, {"context": [0.08447152164248509, 0.2791104426862556, 3.463113225144459, 3.5499244727433577, 0.0, 0.6318366841833253], "direction": "long", "entry_price": 74256.8, "exit_price": 74610.43333333333, "r_multiple": 3.5499244727433577, "net_pct": 0.02171151176278351, "asset": "BTC", "timestamp": "01:40:06"}, {"context": [0.1270010991420991, 0.43421930587095275, 5.26210235131401, 4.625813119338416, 0.0, 0.7611327508158686], "direction": "long", "entry_price": 84.06, "exit_price": 84.12, "r_multiple": 0.3064016049607897, "net_pct": 0.0014688793718768871, "asset": "SOL", "timestamp": "02:05:20"}, {"context": [-0.009064666772060437, -0.26811805286088924, 3.151400933955932, 5.6652275589133625, 0.0, 0.6971741733943632], "direction": "short", "entry_price": 2276.66, "exit_price": 2279.0424285714284, "r_multiple": -1.0, "net_pct": -0.007332288904423177, "asset": "ETH", "timestamp": "02:50:57"}, {"context": [0.19312558874855082, 0.1621082006416573, 2.62210401891249, 1.6494163134806206, 0.0, 0.6401331719128355], "direction": "long", "entry_price": 1.4062, "exit_price": 1.4114816666666665, "r_multiple": 1.6494163134806206, "net_pct": 0.016679926989996863, "asset": "XRP", "timestamp": "03:15:28"}, {"context": [0.041803236373102313, 0.4065321302158865, 4.852161785216122, 3.515739477540155, 0.0, 0.7615507169410486], "direction": "long", "entry_price": 84.15, "exit_price": 84.4, "r_multiple": 1.0610883735030832, "net_pct": 0.012754426619133053, "asset": "SOL", "timestamp": "04:10:26"}, {"context": [0.029930766743391502, 0.18691648789898294, 2.090904168922544, 1.7076341447235688, 5.0, 0.8102476365949408], "direction": "long", "entry_price": 75964.1, "exit_price": 75880.6, "r_multiple": -0.6461276558112312, "net_pct": -0.00759601719759707, "asset": "BTC", "timestamp": "22:50:20"}, {"context": [0.031018005401202337, 0.11108409237611962, 4.410895166534348, 2.1735571762468395, 5.0, 0.8638962400758856], "direction": "long", "entry_price": 75748.7, "exit_price": 75693.4, "r_multiple": -0.27563225061102564, "net_pct": -0.0057502276606731335, "asset": "BTC", "timestamp": "00:10:45"}]}, "trade_logs": {"v3-3m": [{"asset": "BTC", "dir": "long", "entry": 75891.2, "exit": 76077.995, "target": 76077.995, "hard_stop": 75803.12, "size": 0.2, "lev": 5.0, "r_mult": 2.121, "net": 0.002041, "net_pct": 0.010207, "capital": 10020.41, "reason": "target", "time": "22:09:37"}, {"asset": "BTC", "dir": "long", "entry": 75927.6, "exit": 75860.5754, "target": 76035.1183, "hard_stop": 75860.5754, "size": 0.2, "lev": 5.0, "r_mult": -1.0, "net": -0.001303, "net_pct": -0.006514, "capital": 10007.36, "reason": "hard_stop", "time": "23:03:34"}], "v3-5m": [{"asset": "ETH", "dir": "short", "entry": 2276.66, "exit": 2279.0424, "target": 2263.163, "hard_stop": 2279.0424, "size": 0.2, "lev": 5.0, "r_mult": -1.0, "net": -0.001466, "net_pct": -0.007332, "capital": 9985.34, "reason": "hard_stop", "time": "02:50:57"}, {"asset": "BTC", "dir": "long", "entry": 75964.1, "exit": 75880.6, "target": 76184.78, "hard_stop": 75834.8686, "size": 0.2, "lev": 5.0, "r_mult": -0.646, "net": -0.001519, "net_pct": -0.007596, "capital": 9970.17, "reason": "soft_stop", "time": "22:50:20"}, {"asset": "BTC", "dir": "long", "entry": 75748.7, "exit": 75693.4, "target": 76184.78, "hard_stop": 75548.0704, "size": 0.2, "lev": 5.0, "r_mult": -0.276, "net": -0.00115, "net_pct": -0.00575, "capital": 9958.7, "reason": "soft_stop", "time": "00:10:45"}], "v3-15m": [], "v3-30m": [], "v3-5m-aggressive": [{"asset": "ETH", "dir": "short", "entry": 2276.66, "exit": 2279.0424, "target": 2263.163, "hard_stop": 2279.0424, "size": 0.2, "lev": 5.0, "r_mult": -1.0, "net": -0.001466, "net_pct": -0.007332, "capital": 9985.34, "reason": "hard_stop", "time": "02:50:57"}, {"asset": "BTC", "dir": "long", "entry": 75977.3, "exit": 75880.6, "target": 76184.78, "hard_stop": 75834.9736, "size": 0.2, "lev": 5.0, "r_mult": -0.679, "net": -0.001693, "net_pct": -0.008464, "capital": 9968.43, "reason": "soft_stop", "time": "22:50:20"}, {"asset": "BTC", "dir": "long", "entry": 75748.7, "exit": 75693.4, "target": 76184.78, "hard_stop": 75548.0704, "size": 0.2, "lev": 5.0, "r_mult": -0.276, "net": -0.00115, "net_pct": -0.00575, "capital": 9956.97, "reason": "soft_stop", "time": "00:10:45"}], "v3-5m-conservative": [{"asset": "ETH", "dir": "short", "entry": 2276.66, "exit": 2279.0424, "target": 2263.163, "hard_stop": 2279.0424, "size": 0.2, "lev": 5.0, "r_mult": -1.0, "net": -0.001466, "net_pct": -0.007332, "capital": 9985.34, "reason": "hard_stop", "time": "02:50:57"}, {"asset": "BTC", "dir": "long", "entry": 75748.7, "exit": 75693.4, "target": 76184.78, "hard_stop": 75548.0704, "size": 0.2, "lev": 5.0, "r_mult": -0.276, "net": -0.00115, "net_pct": -0.00575, "capital": 9973.85, "reason": "soft_stop", "time": "00:10:45"}], "v3-control": [{"asset": "ETH", "dir": "long", "entry": 2273.58, "exit": 2276.86, "target": 2291.662, "hard_stop": 2266.111, "size": 0.2, "lev": 5.0, "r_mult": 0.439, "net": 0.001023, "net_pct": 0.005113, "capital": 10010.23, "reason": "soft_stop", "time": "01:25:58"}, {"asset": "BTC", "dir": "long", "entry": 74210.9, "exit": 74191.0, "target": 74599.5133, "hard_stop": 74105.0796, "size": 0.2, "lev": 5.0, "r_mult": -0.188, "net": -0.000688, "net_pct": -0.003441, "capital": 10003.34, "reason": "soft_stop", "time": "01:25:58"}, {"asset": "SOL", "dir": "long", "entry": 83.76, "exit": 83.95, "target": 84.968, "hard_stop": 83.3683, "size": 0.2, "lev": 5.0, "r_mult": 0.485, "net": 0.001848, "net_pct": 0.009242, "capital": 10021.83, "reason": "soft_stop", "time": "01:25:58"}, {"asset": "XRP", "dir": "long", "entry": 1.406, "exit": 1.4046, "target": 1.4116, "hard_stop": 1.4039, "size": 0.2, "lev": 5.0, "r_mult": -0.655, "net": -0.001416, "net_pct": -0.007079, "capital": 10007.64, "reason": "soft_stop", "time": "01:25:58"}, {"asset": "BTC", "dir": "long", "entry": 74256.8, "exit": 74610.4333, "target": 74610.4333, "hard_stop": 74157.1829, "size": 0.2, "lev": 5.0, "r_mult": 3.55, "net": 0.004342, "net_pct": 0.021712, "capital": 10051.1, "reason": "target", "time": "01:40:06"}, {"asset": "SOL", "dir": "long", "entry": 84.06, "exit": 84.12, "target": 84.9658, "hard_stop": 83.8642, "size": 0.2, "lev": 5.0, "r_mult": 0.306, "net": 0.000294, "net_pct": 0.001469, "capital": 10054.05, "reason": "soft_stop", "time": "02:05:20"}, {"asset": "ETH", "dir": "short", "entry": 2276.66, "exit": 2279.0424, "target": 2263.163, "hard_stop": 2279.0424, "size": 0.2, "lev": 5.0, "r_mult": -1.0, "net": -0.001466, "net_pct": -0.007332, "capital": 10039.3, "reason": "hard_stop", "time": "02:50:57"}, {"asset": "XRP", "dir": "long", "entry": 1.4062, "exit": 1.4115, "target": 1.4115, "hard_stop": 1.403, "size": 0.2, "lev": 5.0, "r_mult": 1.649, "net": 0.003336, "net_pct": 0.01668, "capital": 10072.8, "reason": "target", "time": "03:15:28"}, {"asset": "SOL", "dir": "long", "entry": 84.15, "exit": 84.4, "target": 84.9783, "hard_stop": 83.9144, "size": 0.2, "lev": 5.0, "r_mult": 1.061, "net": 0.002551, "net_pct": 0.012754, "capital": 10098.49, "reason": "soft_stop", "time": "04:10:26"}, {"asset": "BTC", "dir": "long", "entry": 75964.1, "exit": 75880.6, "target": 76184.78, "hard_stop": 75834.8686, "size": 0.2, "lev": 5.0, "r_mult": -0.646, "net": -0.001519, "net_pct": -0.007596, "capital": 10083.15, "reason": "soft_stop", "time": "22:50:20"}, {"asset": "BTC", "dir": "long", "entry": 75748.7, "exit": 75693.4, "target": 76184.78, "hard_stop": 75548.0704, "size": 0.2, "lev": 5.0, "r_mult": -0.276, "net": -0.00115, "net_pct": -0.00575, "capital": 10071.55, "reason": "soft_stop", "time": "00:10:45"}]}}

 succeeded in 380ms:
{"memory": {"triarb-5m": [], "triarb-30m": [], "triarb-daily": [], "triarb-tight": [], "triarb-control": []}, "trade_logs": {"triarb-5m": [], "triarb-30m": [], "triarb-daily": [], "triarb-tight": [], "triarb-control": []}, "positions": {"triarb-5m": [], "triarb-30m": [], "triarb-daily": [], "triarb-tight": [], "triarb-control": []}}

exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "rg --files docs . | rg \"feedback_self_learning_algorithm\\.md|feedback|oracle|oracle.*md|phase.*0|intake|charter\"" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
2026-04-21T03:05:10.971263Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 0.4 seconds
Output:

 exited 1 in 429ms:
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content scripts\\v3.py | Select-Object -Skip 540 -First 90" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content scripts\\triarb.py | Select-Object -Skip 560 -First 90" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 394ms:
    def __init__(self, variant_name: str, config: dict):
        self.name = variant_name
        self.config = config
        self.capital = INITIAL_CAPITAL
        self.initial_capital = INITIAL_CAPITAL
        self.positions: dict[str, V3Position] = {}
        self.trade_log: list[dict] = []
        self.pnl_history: list[float] = [INITIAL_CAPITAL]
        self.peak_capital = INITIAL_CAPITAL
        self.memory = ContextMemory(variant_name)
        self.signals_considered = 0
        self.signals_blocked_chop = 0
        self.signals_blocked_rr = 0
        self.signals_blocked_memory = 0
        self.signals_blocked_htf = 0
        self.signals_executed = 0

    def try_open(self, asset: str, direction: str, entry: float, hard_stop: float,
                 target: float, soft_stop_ref: float, ctx: ContextVector) -> str | None:
        """Returns None on success, error reason string on block."""
        if asset in self.positions:
            return "already_open"

        # Memory blacklist check (only if memory enabled)
        if self.config["memory"] and self.memory.is_blacklisted(ctx, direction):
            self.signals_blocked_memory += 1
            return "memory_blacklist"

        r_dist = abs(entry - hard_stop)
        if r_dist <= 0:
            return "zero_r_distance"

        # Position sizing: risk RISK_PER_TRADE of capital across hard stop distance
        # size * leverage * r_dist/entry = RISK_PER_TRADE
        # ??margin_notional_pct = RISK_PER_TRADE / (r_dist/entry)
        risk_fraction = r_dist / entry
        if risk_fraction <= 0:
            return "invalid_risk"

        # Memory multiplier adjusts base risk
        mult = 1.0
        if self.config["memory"]:
            mult = self.memory.size_multiplier(ctx, direction,
                                               len(self.memory.records))
        target_notional_pct = (RISK_PER_TRADE * mult) / risk_fraction
        # Cap total capital exposure
        target_notional_pct = min(target_notional_pct, 1.0)
        # Use leverage to achieve target notional with small margin
        # Default: leverage 5x, size = notional / leverage
        leverage = 5.0
        size = target_notional_pct / leverage
        size = max(0.001, min(size, 0.5))  # safety caps

        self.positions[asset] = V3Position(
            asset=asset, direction=direction, entry_price=entry,
            hard_stop=hard_stop, soft_stop_ref=soft_stop_ref, target_price=target,
            size=size, leverage=leverage,
            entry_time=datetime.now(timezone.utc).strftime("%H:%M:%S"),
            entry_context=ctx,
            r_distance=r_dist,
        )
        self.signals_executed += 1
        return None

    def check_exits(self, asset: str, bar: dict, ema9_now: float, atr_now: float) -> str | None:
        """Returns exit_reason if closed, else None."""
        if asset not in self.positions:
            return None
        pos = self.positions[asset]
        h = float(bar["high"])
        lo = float(bar["low"])
        close = float(bar["close"])

        # 1) Hard stop (intrabar immediate)
        if pos.direction == "long" and lo <= pos.hard_stop:
            self._close(asset, pos.hard_stop, "hard_stop")
            return "hard_stop"
        if pos.direction == "short" and h >= pos.hard_stop:
            self._close(asset, pos.hard_stop, "hard_stop")
            return "hard_stop"

        # 2) Target hit (partial ??take it all at first HVN for simplicity)
        if pos.direction == "long" and h >= pos.target_price:
            self._close(asset, pos.target_price, "target")
            return "target"
        if pos.direction == "short" and lo <= pos.target_price:
            self._close(asset, pos.target_price, "target")
            return "target"

        # 3) Soft stop ??close below (long) or above (short) EMA9 +/- 0.05 ATR

 succeeded in 477ms:
        return self.capital

    @property
    def peak_balance(self) -> float:
        return self.peak_capital

    @property
    def trade_count(self) -> int:
        return len(self.trade_log)

    @property
    def win_count(self) -> int:
        return sum(1 for t in self.trade_log if t.get("net", 0) > 0)

    def try_open(
        self,
        pair_id: str,
        direction: str,
        entry_ratio: float,
        entry_z: float,
        price_leg1: float,
        price_leg2: float,
        ctx: ContextVector,
        capital: float,
        current_bar_idx: int,
    ) -> str | None:
        if pair_id in self.positions:
            return "already_open"
        if price_leg1 <= 0 or price_leg2 <= 0:
            return "invalid_price"
        if self.config.get("memory", False) and self.memory.is_blacklisted(ctx, direction):
            self.signals_blocked_memory += 1
            return "memory_blacklist"

        notional_per_leg = capital * RISK_PER_TRADE_NOTIONAL * LEVERAGE / 2.0
        if self.config.get("memory", False):
            notional_per_leg *= self.memory.size_multiplier(ctx, direction, len(self.memory.records))
        notional_per_leg = min(notional_per_leg, MAX_NOTIONAL_PER_LEG_USD)

        size_leg1 = notional_per_leg / price_leg1
        size_leg2 = notional_per_leg / price_leg2
        self.positions[pair_id] = PairPosition(
            pair_id=pair_id,
            direction=direction,
            entry_ratio=float(entry_ratio),
            entry_z=float(entry_z),
            entry_price_leg1=float(price_leg1),
            entry_price_leg2=float(price_leg2),
            size_leg1=float(size_leg1),
            size_leg2=float(size_leg2),
            notional_per_leg_usd=float(notional_per_leg),
            leverage=LEVERAGE,
            entry_time=datetime.now(timezone.utc).strftime("%H:%M:%S"),
            entry_bar_idx=int(current_bar_idx),
            entry_context=ctx,
            entry_capital=float(capital),
        )
        self.signals_executed += 1
        return None

    def check_exits(
        self,
        pair_id: str,
        metrics: dict[str, float],
        corr: float,
        price_leg1: float,
        price_leg2: float,
        current_bar_idx: int,
        time_stop_bars: int,
    ) -> str | None:
        if pair_id not in self.positions:
            return None
        pos = self.positions[pair_id]
        z = float(metrics.get("z", float("nan")))
        velocity = float(metrics.get("z_velocity", float("nan")))
        if np.isfinite(corr) and corr < CORRELATION_BREAK_THRESHOLD:
            return self._close(pair_id, metrics, price_leg1, price_leg2, "corr_break")
        if np.isfinite(z):
            if pos.direction == "short_ratio" and abs(z) >= self.config["exit_stop_z"] and z > 0:
                return self._close(pair_id, metrics, price_leg1, price_leg2, "hard_stop")
            if pos.direction == "long_ratio" and abs(z) >= self.config["exit_stop_z"] and z < 0:
                return self._close(pair_id, metrics, price_leg1, price_leg2, "hard_stop")
            if abs(z) <= self.config["exit_target_z"]:
                return self._close(pair_id, metrics, price_leg1, price_leg2, "target")
        if current_bar_idx - pos.entry_bar_idx >= time_stop_bars:
            return self._close(pair_id, metrics, price_leg1, price_leg2, "time_stop")
        if np.isfinite(velocity) and velocity > float(self.config["max_velocity"]) * 2.0:
            return self._close(pair_id, metrics, price_leg1, price_leg2, "velocity")
        return None


exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "rg -n \"setInterval|fetch\\('/api/all|fetch\\('/api/|refresh|3000|5000|10000\" scripts\\dashboard_unified.py" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 330ms:
299:  const cap=s.capital||10000;
632:async function refresh(){
634:    const r=await fetch('/api/all');
684:setInterval(refresh,5000);
685:refresh();

exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content scripts\\dashboard_unified.py | Select-Object -Skip 628 -First 60" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 386ms:
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
      else if(id==='triarb')html+=renderTriArb(id,m,m.color);
      else if(id==='v3')html+=renderV3(id,m,m.color);
      else html+=renderV2(id,m,m.color);
    }
    q('#root').innerHTML=html;
    q('#model-count').textContent=online+'/'+total+' 紐⑤뜽 ?⑤씪??;
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

    // Draw TriArb per-variant PnL charts
    const td=d.triarb;
    if(td&&td.online&&td.state){
      const variants=td.state.variants||{};
      for(const[vn,v]of Object.entries(variants)){
        const ret=v.total_return||0;
        const color=ret>0?'#00ff88':ret<-0.05?'#ff4466':'#ffcc00';
        drawLine(q('#cv-triarb-'+vn),v.pnl_history,color,v.initial_capital);
      }
    }
  }catch(e){
    q('#root').innerHTML='<div style="color:#f44;padding:40px">??쒕낫???곌껐 ?ㅻ쪟. 紐⑤뜽???ㅽ봽?쇱씤?????덉뒿?덈떎.</div>';
  }
}
setInterval(refresh,5000);
refresh();
</script>
</body></html>"""


codex
1. **Position**: 가정은 `V3와 같은 자산 수(기본 4개)`, `7 variants`, `numpy/pandas + ccxt`, `분봉 close 기준 처리`입니다. 이 전제라면 Oracle 추가 자체는 한 대의 Windows 머신에서 CPU/RAM으로 감당 가능합니다. 따라서 **Phase 1 Charter 진입은 가능**하지만, 지금 요약은 설계 착수용으로는 3개 제약이 빠져 있어 아직 “구현 착수 확정” 수준은 아닙니다: `데이터 fetch 소유권`, `context memory 보존 한도`, `HTTP 응답 SLA`.

2. **Reasoning**:
- V3는 기본 4자산에서 분당 약 `10.4` OHLCV fetch, TriArb는 약 `5.3`, V2는 약 `4.1` 수준입니다 (`scripts/v3.py:918-975`, `scripts/triarb.py:795-1073`, `scripts/v2.py:640-767`). Oracle이 V3급으로 하나 더 붙어도 총 `~30/min` 내외라 rate-limit/대역폭은 낮은 편입니다.
- RAM은 500-bar DataFrame 위주라 병목이 아닙니다. 진짜 CPU 리스크는 k-NN이 `records` 전체를 매번 스캔+정렬하는 구조라는 점입니다 (`scripts/v3.py:417-445`, `scripts/triarb.py:429-449`). 그래도 “신호 발생 시만” 돌면 아직 감당 가능하지만, per-tick/per-request로 돌리면 바로 비효율입니다.
- `10k+ trades`에서 디스크 save/load 자체는 현재 방식이면 아직 허용 가능합니다. 이유는 실제 저장이 전체 메모리가 아니라 최근 `500` memory record와 `200` trade만 저장되기 때문입니다 (`scripts/v3.py:1067-1068`, `scripts/triarb.py:1222-1223`). 즉 병목은 `npz`보다 **무한 증가하는 in-memory k-NN** 입니다.
- 대시보드는 모델들을 순차 프록시하고 모델별 timeout이 `3초`이며, 프런트는 `5초`마다 갱신합니다 (`scripts/dashboard_unified.py:26-39, 632-685`). 따라서 Oracle `/api/state`가 `1초`만 넘어도 체감상 뻑뻑해지고, `3초`를 넘기면 offline처럼 보입니다. **상한은 1초, 목표는 500ms 이하**로 봐야 합니다.

3. **Concerns**:
- `포트/파일명`을 Phase 3로 미루는 건 타당합니다. 반면 `데이터 중복 fetch 허용 여부`, `memory cap`, `API latency budget`은 아키텍처를 바꾸므로 Phase 1 전에 확정해야 합니다.
- 현재 V3/TriArb는 `records`는 무한 증가하지만 저장은 최근 500개만 합니다. 운영은 가볍지만, “Oracle이 장기 기억으로 학습한다”는 주장과는 충돌합니다.
- `/api/state` 경로에서 live inference나 전체 memory 재계산을 하면 안 됩니다. snapshot은 반드시 캐시된 최신 결과만 즉시 반환해야 합니다.
- 설계 방향은 **V2 수정본보다 신규 Oracle 엔진이 맞습니다**. V2의 근본 문제는 rule 2뿐 아니라 context 분화가 안 되는 단일 선형 구조라, 패치만으로는 사용자 요구 “좋은 패턴 강화 / 나쁜 패턴 소거”를 충분히 못 풉니다.

4. **Recommendation**:
- Phase 1로 진행하되 Charter에 바로 추가하십시오: `shared fetch per engine/timeframe`, `memory retention policy(예: variant당 2k/5k cap 또는 ring buffer)`, `/api/state p95 500ms / hard 1s`.
- Oracle은 `v2.py` 덮어쓰기보다 신규 `oracle.py`가 안전합니다. V2와 운용 모델이 다르고, rollback도 쉬워집니다.
- Phase 1 산출물에 반드시 넣으십시오: `분당 REST 호출 예산`, `variant당 max records`, `10k/25k/50k에서 k-NN latency`, `save/load p95`, `dashboard timeout 정책`.

[POSITION: Phase 1 진입은 가능하지만, fetch topology·memory cap·API SLA 없이는 아직 설계 착수 조건이 완전히 닫히지 않았다.]
tokens used
67,272
1. **Position**: 가정은 `V3와 같은 자산 수(기본 4개)`, `7 variants`, `numpy/pandas + ccxt`, `분봉 close 기준 처리`입니다. 이 전제라면 Oracle 추가 자체는 한 대의 Windows 머신에서 CPU/RAM으로 감당 가능합니다. 따라서 **Phase 1 Charter 진입은 가능**하지만, 지금 요약은 설계 착수용으로는 3개 제약이 빠져 있어 아직 “구현 착수 확정” 수준은 아닙니다: `데이터 fetch 소유권`, `context memory 보존 한도`, `HTTP 응답 SLA`.

2. **Reasoning**:
- V3는 기본 4자산에서 분당 약 `10.4` OHLCV fetch, TriArb는 약 `5.3`, V2는 약 `4.1` 수준입니다 (`scripts/v3.py:918-975`, `scripts/triarb.py:795-1073`, `scripts/v2.py:640-767`). Oracle이 V3급으로 하나 더 붙어도 총 `~30/min` 내외라 rate-limit/대역폭은 낮은 편입니다.
- RAM은 500-bar DataFrame 위주라 병목이 아닙니다. 진짜 CPU 리스크는 k-NN이 `records` 전체를 매번 스캔+정렬하는 구조라는 점입니다 (`scripts/v3.py:417-445`, `scripts/triarb.py:429-449`). 그래도 “신호 발생 시만” 돌면 아직 감당 가능하지만, per-tick/per-request로 돌리면 바로 비효율입니다.
- `10k+ trades`에서 디스크 save/load 자체는 현재 방식이면 아직 허용 가능합니다. 이유는 실제 저장이 전체 메모리가 아니라 최근 `500` memory record와 `200` trade만 저장되기 때문입니다 (`scripts/v3.py:1067-1068`, `scripts/triarb.py:1222-1223`). 즉 병목은 `npz`보다 **무한 증가하는 in-memory k-NN** 입니다.
- 대시보드는 모델들을 순차 프록시하고 모델별 timeout이 `3초`이며, 프런트는 `5초`마다 갱신합니다 (`scripts/dashboard_unified.py:26-39, 632-685`). 따라서 Oracle `/api/state`가 `1초`만 넘어도 체감상 뻑뻑해지고, `3초`를 넘기면 offline처럼 보입니다. **상한은 1초, 목표는 500ms 이하**로 봐야 합니다.

3. **Concerns**:
- `포트/파일명`을 Phase 3로 미루는 건 타당합니다. 반면 `데이터 중복 fetch 허용 여부`, `memory cap`, `API latency budget`은 아키텍처를 바꾸므로 Phase 1 전에 확정해야 합니다.
- 현재 V3/TriArb는 `records`는 무한 증가하지만 저장은 최근 500개만 합니다. 운영은 가볍지만, “Oracle이 장기 기억으로 학습한다”는 주장과는 충돌합니다.
- `/api/state` 경로에서 live inference나 전체 memory 재계산을 하면 안 됩니다. snapshot은 반드시 캐시된 최신 결과만 즉시 반환해야 합니다.
- 설계 방향은 **V2 수정본보다 신규 Oracle 엔진이 맞습니다**. V2의 근본 문제는 rule 2뿐 아니라 context 분화가 안 되는 단일 선형 구조라, 패치만으로는 사용자 요구 “좋은 패턴 강화 / 나쁜 패턴 소거”를 충분히 못 풉니다.

4. **Recommendation**:
- Phase 1로 진행하되 Charter에 바로 추가하십시오: `shared fetch per engine/timeframe`, `memory retention policy(예: variant당 2k/5k cap 또는 ring buffer)`, `/api/state p95 500ms / hard 1s`.
- Oracle은 `v2.py` 덮어쓰기보다 신규 `oracle.py`가 안전합니다. V2와 운용 모델이 다르고, rollback도 쉬워집니다.
- Phase 1 산출물에 반드시 넣으십시오: `분당 REST 호출 예산`, `variant당 max records`, `10k/25k/50k에서 k-NN latency`, `save/load p95`, `dashboard timeout 정책`.

[POSITION: Phase 1 진입은 가능하지만, fetch topology·memory cap·API SLA 없이는 아직 설계 착수 조건이 완전히 닫히지 않았다.]
