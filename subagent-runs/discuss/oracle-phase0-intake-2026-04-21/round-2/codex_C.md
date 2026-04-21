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
session id: 019dae36-c117-73a2-bbe7-7aad13e0dc1d
--------
user
# Round 2 Focus — 이견 집중

## Round 1 요약 (참조)
- 수렴 상태: **PARTIAL**
- 합의: Phase 1 진입 가능 (7/8), 포트/v2.py 즉시 확정 필요 (6명), 수학 골격 스케치 부재 (6명), 67% KPI 근거 취약 (5명)
- 코드로 검증된 팩트:
  - v2.jsonl 실제 -11.15% (문서 -13.13%와 불일치)
  - V3/TriArb는 `*_state.npz + *_memory.json` (Phase 0의 "npz+jsonl 일관" 전제 오류)
  - Dashboard timeout 3초/refresh 5초 → Oracle `/api/state` p95 500ms 필수
  - Dashboard `renderV2/V3/TriArb` 하드코딩 → 통합 공수 +25~40%

## Round 2 집중 쟁점 (3개)

### 쟁점 1 — v2.py 처리
- 입장 A **덮어쓰기** (Oracle=V2 후계자): opus 단독
  - 근거: 정체성 명확화, 이중 유지 비용 제거
- 입장 B **신규 oracle.py**: sonnet / Codex A / Codex C / sonnet-찬성 (4명)
  - 근거: 롤백 유지, 베이스라인 비교, 새 코드=새 버그 주기 최소화
- 입장 C **Phase 3 유지**: Codex B / gemini-flash (2명)
  - 근거: 운영 packaging 문제이지 학습 아키텍처 문제 아님

### 쟁점 2 — 재설계 vs 수술적 수정
- **반대 sonnet**: Rule 2 제거는 30-50줄 PR. **48시간 백테스트로 60%+ 나오면 재설계 불필요**. 재설계는 검증 없는 과잉 공학.
- **찬성측 (7명)**: 단일 선형+context 분화 불가는 구조적 결함. 파라미터 조정(Rule 2 제거)으로 해결 불가.

### 쟁점 3 — V3 차별화
- **opus**: V3도 context k-NN + 블랙리스트 보유. Oracle이 V3와 무엇이 다른가? 차별화 1문장이 없으면 Oracle 재검토.
- **반대 sonnet**: V3 현재 승률을 측정해 67%+이면 Oracle은 **중복**.
- **찬성 sonnet**: V2 feature pipeline + V3 ContextMemory 재조립. V3와 다른 차원.
- **Codex B**: Oracle context = predicted edge/uncertainty/vol regime. V3의 rr_estimate/vp_clearance는 setup/management용이라 예측엔진에 부적합. **Oracle은 별도 context 공간 필요**.

## Round 2 지시

자신의 Round 1 입장을 **재평가**하고 세 이견에 답하라:

1. **v2.py 처리**: 지금 어느 입장(A/B/C)? 새 논거 또는 양보점?
2. **48시간 실험 선행**: 타당한가? 재설계 정당화 기준은?
3. **V3 차별화**: Oracle이 V3와 본질적으로 무엇이 다른가? (또는 다르지 않은가?)

## 응답 형식 (30줄 이내)

**첫 줄 라벨 필수**: `[AGREE] / [PARTIAL] / [DISAGREE]`
→ 대상: **"Phase 1 진입 OK + Round 1의 9항목(A~I) Charter 전 추가 확정"** 방향에 대한 당신의 입장.

1. **Reasoning**: 라벨 선택 이유
2. **쟁점 1 답**: v2.py 처리
3. **쟁점 2 답**: 48시간 실험 타당성
4. **쟁점 3 답**: V3 차별화
5. **Updated position**: 바뀐 점 있으면 명시

마지막 줄: `[POSITION: 한 줄 업데이트된 입장]`
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
세 이견을 비용/속도 관점에서 재평가하기 위해 현재 프로젝트 상태와 관련 코드 경로부터 확인하겠습니다. 먼저 필수 초기화인 WKI 인덱싱과 `project-status/current.md`를 읽고, 이어서 `v2.py`/`v3.py`/`triarb.py`/`dashboard_unified.py`의 비용 경로를 점검하겠습니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'node workspace-knowledge-index/dist/index.js index' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content project-status/current.md' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
2026-04-21T04:05:30.823280Z ERROR codex_core::tools::router: error=Exit code: 1
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

 exited 1 in 435ms:
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

2026-04-21T04:05:30.833886Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 0.4 seconds
Output:
Get-Content : 'C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value\project-status\current.md' 경로는 존재하지 않
으므로 찾을 수 없습니다.
위치 줄:2 문자:1
+ Get-Content project-status/current.md
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:\Users\haj\pr...atus\current.md:String) [Get-Content], ItemNotFoundEx 
   ception
    + FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.GetContentCommand
 

 exited 1 in 447ms:
Get-Content : 'C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value\project-status\current.md' 경로는 존재하지 않
으므로 찾을 수 없습니다.
위치 줄:2 문자:1
+ Get-Content project-status/current.md
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:\Users\haj\pr...atus\current.md:String) [Get-Content], ItemNotFoundEx 
   ception
    + FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.GetContentCommand
 

codex
필수 초기화 경로가 현재 워크스페이스에 그대로 있지 않습니다. `workspace-knowledge-index/dist/index.js`와 `project-status/current.md`의 실제 위치를 찾아서 그 기준으로 진행하겠습니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'rg --files -g "current.md" -g "*.md" project-status .' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'rg --files -g "index.js" workspace-knowledge-index .' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command Get-ChildItem in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
2026-04-21T04:05:36.514290Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 0.3 seconds
Output:
rg: workspace-knowledge-index: 지정된 파일을 찾을 수 없습니다. (os error 2)

 exited 1 in 311ms:
rg: workspace-knowledge-index: 지정된 파일을 찾을 수 없습니다. (os error 2)

2026-04-21T04:05:36.579048Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 0.4 seconds
Output:
.\scripts\dl_breakthrough_strategy.md
.\reusable_components_guide.md
.\RESUME.md
.\README.md
.\limits-history.md
.\coin_strategy_spec.md
.\coin_strategy_spec_v2.md
.\auto_trading_state_machine_design.md
.\breakthrough-guide.md
.\docs\triarb_review_request_260420.md
.\docs\triarb_fix_review_260420.md
.\docs\triarb_fix_260420.md
.\docs\triarb_260420.md
.\docs\new_trade_260419.md
.\docs\models_architecture_260420.md
.\docs\bollrev_260420.md
.\archive\btc_alpha_research.md
.\archive\alternative_paradigm_research.md
.\archive\rl_learning_log.md
.\data\discuss_prompt.md
.\data\discuss_rule2.md
rg: project-status: 지정된 파일을 찾을 수 없습니다. (os error 2)

 exited 1 in 375ms:
.\scripts\dl_breakthrough_strategy.md
.\reusable_components_guide.md
.\RESUME.md
.\README.md
.\limits-history.md
.\coin_strategy_spec.md
.\coin_strategy_spec_v2.md
.\auto_trading_state_machine_design.md
.\breakthrough-guide.md
.\docs\triarb_review_request_260420.md
.\docs\triarb_fix_review_260420.md
.\docs\triarb_fix_260420.md
.\docs\triarb_260420.md
.\docs\new_trade_260419.md
.\docs\models_architecture_260420.md
.\docs\bollrev_260420.md
.\archive\btc_alpha_research.md
.\archive\alternative_paradigm_research.md
.\archive\rl_learning_log.md
.\data\discuss_prompt.md
.\data\discuss_rule2.md
rg: project-status: 지정된 파일을 찾을 수 없습니다. (os error 2)

 succeeded in 370ms:


    디렉터리: C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value


Mode                 LastWriteTime         Length Name                                                                 
----                 -------------         ------ ----                                                                 
d-----        2026-04-21  오후 12:05                .knowledge                                                           
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
워크스페이스에는 `project-status/current.md`가 없고 `.knowledge/`만 있어 해당 규칙은 현 상태 기준으로 충족 불가입니다. 이제 실제 운영 코드에서 폴링 주기, variant 수, 상태 저장, 프록시 타임아웃을 추출해 비용 관점 판정을 고정하겠습니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "rg -n \"8897|8898|8899|8900|refresh|timeout|MODELS|api/state|127\\.0\\.0\\.1|save|npz|jsonl|context|k-NN|kNN|nearest|variant|OHLCV|fetch_ohlcv|sleep|poll|warmup|blacklist|n>=20|n ≥20|n>= 20\" scripts/v2.py scripts/v3.py scripts/triarb.py scripts/dashboard_unified.py" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/v2.py -TotalCount 260' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/v3.py -TotalCount 320' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/triarb.py -TotalCount 320' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/dashboard_unified.py -TotalCount 260' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 353ms:
scripts/dashboard_unified.py:4:- V2 Prediction Engine (port 8897)
scripts/dashboard_unified.py:5:- V3 Parker Brooks + Self-Learn (port 8898)
scripts/dashboard_unified.py:6:- TriArb Pairs Ratio (port 8899)
scripts/dashboard_unified.py:9:    py -3.12 scripts/dashboard_unified.py [--port 8900]
scripts/dashboard_unified.py:12:    http://127.0.0.1:8900
scripts/dashboard_unified.py:23:PORT = 8900
scripts/dashboard_unified.py:26:MODELS = {
scripts/dashboard_unified.py:27:    "v2":         {"port": 8897, "name": "V2 Prediction Engine",           "color": "#00ccff"},
scripts/dashboard_unified.py:28:    "v3":         {"port": 8898, "name": "V3 Parker Brooks + Self-Learn",  "color": "#aa66ff"},
scripts/dashboard_unified.py:29:    "triarb":     {"port": 8899, "name": "TriArb (Pairs Ratio)",           "color": "#66ffaa"},
scripts/dashboard_unified.py:36:            f"http://127.0.0.1:{port}/api/state",
scripts/dashboard_unified.py:39:        with urllib.request.urlopen(req, timeout=3) as resp:
scripts/dashboard_unified.py:68:        # /api/v2 — proxy to 8897
scripts/dashboard_unified.py:73:            for model_id, info in MODELS.items():
scripts/dashboard_unified.py:82:        elif key in MODELS:
scripts/dashboard_unified.py:83:            state = fetch_model_state(MODELS[key]["port"])
scripts/dashboard_unified.py:367:  const variants=s.variants||{};
scripts/dashboard_unified.py:368:  const warmup=s.memory_warmup||30;
scripts/dashboard_unified.py:371:  // Header summary: best variant + total trades
scripts/dashboard_unified.py:373:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:382:  let html='<div class="model-section"><div class="model-hdr" style="border-left:3px solid '+color+'"><h2><span class="'+(online?'live':'live offline')+'"></span> '+d.name+' <span style="font-size:10px;color:#aa66ff;margin-left:6px">VWAP/EMA9/VP + Context k-NN + '+htfTF+' HTF Bias | 수수료 0.21% RT | Risk 0.5%/trade</span></h2><div class="stats">';
scripts/dashboard_unified.py:386:  html+='<span class="dim" style="font-size:10px">메모리: '+warmup+'거래 후 활성 → '+fullAct+'거래에 100%</span>';
scripts/dashboard_unified.py:389:  // HTF bias strip — per-asset 1h directional context
scripts/dashboard_unified.py:401:  // Variants grid — one card per variant
scripts/dashboard_unified.py:402:  html+='<div style="display:grid;grid-template-columns:repeat('+Object.keys(variants).length+',1fr);gap:8px;margin-bottom:12px">';
scripts/dashboard_unified.py:403:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:409:    const bl=mem.blacklisted_clusters||0;
scripts/dashboard_unified.py:424:  html+='<div style="margin-top:8px"><div style="font-size:10px;color:#555;margin-bottom:3px;text-transform:uppercase">신호 필터링 깔때기 (각 variant 누적)</div>';
scripts/dashboard_unified.py:426:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:445:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:457:    html+='<td class="'+((m.blacklisted_clusters||0)>0?'red':'dim')+'">'+(m.blacklisted_clusters||0)+'</td></tr>';
scripts/dashboard_unified.py:461:  // PnL charts per variant (compact)
scripts/dashboard_unified.py:462:  html+='<div style="display:grid;grid-template-columns:repeat('+Object.keys(variants).length+',1fr);gap:6px;margin-top:10px">';
scripts/dashboard_unified.py:463:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:468:  // Positions (all variants)
scripts/dashboard_unified.py:471:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:484:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:485:    (v.trade_log||[]).forEach(t=>{allTrades.push({...t,variant:vn});});
scripts/dashboard_unified.py:490:    html+='<div style="margin-top:10px"><div style="font-size:11px;color:#888;margin-bottom:4px;font-weight:bold">최근 거래 (전체 variant)</div>';
scripts/dashboard_unified.py:494:      html+='<div class="tlog-e"><span class="dim">['+t.variant.replace('v3-','')+']</span> <span class="'+(t.net>0?'grn':'red')+'" style="font-weight:bold">'+t.dir+'</span> '+t.asset+' $'+t.entry+' → $'+t.exit+' <span class="'+(r>0?'grn':'red')+'">'+(r>=0?'+':'')+r.toFixed(2)+'R</span> <span class="dim">['+t.reason+']</span> 잔고='+$(t.capital)+'</div>';
scripts/dashboard_unified.py:506:  const variants=s.variants||{};
scripts/dashboard_unified.py:512:  const warmup=s.memory_warmup||30;
scripts/dashboard_unified.py:517:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:527:  html+='<span class="dim" style="font-size:10px">메모리: '+warmup+' → '+fullAct+' trades</span>';
scripts/dashboard_unified.py:545:  html+='<div style="display:grid;grid-template-columns:repeat('+Math.max(1,Object.keys(variants).length)+',1fr);gap:8px;margin-bottom:12px">';
scripts/dashboard_unified.py:546:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:557:    html+='<div style="font-size:9px;color:#666;margin-top:3px">mem: <span class="cyn">'+(mem.n_trades||0)+'</span> 블랙: <span class="'+((mem.blacklisted_clusters||0)>0?'red':'dim')+'">'+(mem.blacklisted_clusters||0)+'</span></div>';
scripts/dashboard_unified.py:564:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:583:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:591:    html+='<td class="'+((m.blacklisted_clusters||0)>0?'red':'dim')+'">'+(m.blacklisted_clusters||0)+'</td></tr>';
scripts/dashboard_unified.py:595:  html+='<div style="display:grid;grid-template-columns:repeat('+Math.max(1,Object.keys(variants).length)+',1fr);gap:6px;margin-top:10px">';
scripts/dashboard_unified.py:596:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:602:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:614:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:615:    (v.trade_log||[]).forEach(t=>{allTrades.push({...t,variant:vn});});
scripts/dashboard_unified.py:620:    html+='<div style="margin-top:10px"><div style="font-size:11px;color:#888;margin-bottom:4px;font-weight:bold">최근 거래 (전체 variant)</div><div class="tlog">';
scripts/dashboard_unified.py:623:      html+='<div class="tlog-e"><span class="dim">['+t.variant.replace('triarb-','')+']</span> <span class="'+(net>0?'grn':'red')+'" style="font-weight:bold">'+t.dir+'</span> '+(t.pair_id||t.asset)+' '+num(t.entry,6)+' → '+num(t.exit,6)+' <span class="'+(r>0?'grn':'red')+'">'+(r>=0?'+':'')+r.toFixed(2)+'R</span> net=<span class="'+(net>0?'grn':'red')+'">$'+net.toFixed(2)+'</span> <span class="dim">['+t.reason+']</span></div>';
scripts/dashboard_unified.py:632:async function refresh(){
scripts/dashboard_unified.py:659:    // Draw V3 per-variant PnL charts
scripts/dashboard_unified.py:662:      const variants=v3d.state.variants||{};
scripts/dashboard_unified.py:663:      for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:670:    // Draw TriArb per-variant PnL charts
scripts/dashboard_unified.py:673:      const variants=td.state.variants||{};
scripts/dashboard_unified.py:674:      for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:684:setInterval(refresh,5000);
scripts/dashboard_unified.py:685:refresh();
scripts/dashboard_unified.py:697:    proxy_desc = ", ".join(f"{v['name']} :{v['port']}" for v in MODELS.values())
scripts/v3.py:5:  2. Context Memory (k-NN based EV tracking) — learns good/bad contexts
scripts/v3.py:6:  3. Kill Switch — auto-blacklist bad context clusters
scripts/v3.py:7:  4. Multi-variant paper trading (5 variants concurrently)
scripts/v3.py:13:    py -3.12 scripts/v3.py [--assets ETH,BTC,SOL,XRP] [--port 8898]
scripts/v3.py:16:    http://localhost:8898
scripts/v3.py:48:STATE_PATH = DATA_DIR / "v3_state.npz"
scripts/v3.py:49:LOG_PATH = DATA_DIR / "v3.jsonl"
scripts/v3.py:51:DASH_PORT = 8898
scripts/v3.py:74:# HTF bias filter (higher-timeframe context)
scripts/v3.py:77:#   - HTF context: 1h (standard for scalping confluence). Daily for swing.
scripts/v3.py:81:HTF_REFRESH_TICKS = 15     # refresh 1h bias every 15 minutes (tick = 60s)
scripts/v3.py:84:# Execution TFs expanded per WebSearch findings: 3m/5m/15m/30m + 5m param variants.
scripts/v3.py:393:    context: list[float]        # ContextVector as array
scripts/v3.py:404:    """Stores past trades and scores new contexts via k-NN EV.
scripts/v3.py:407:      - Bad contexts (EV < threshold with enough samples) → blacklist
scripts/v3.py:408:      - Good contexts (EV > threshold) → position size boost
scripts/v3.py:411:    def __init__(self, variant_name: str):
scripts/v3.py:412:        self.variant_name = variant_name
scripts/v3.py:414:        self._blacklist_cache: set[int] | None = None  # hash-based
scripts/v3.py:418:        self._blacklist_cache = None  # invalidate
scripts/v3.py:434:        distances = [(self._distance(target, np.array(r.context)), r) for r in same_dir]
scripts/v3.py:447:    def is_blacklisted(self, ctx: ContextVector, direction: str) -> bool:
scripts/v3.py:456:        """Returns position size multiplier in [0, 1.5] based on context EV.
scripts/v3.py:459:        Gradual activation between warmup and full-activation.
scripts/v3.py:480:            # Soft penalty before blacklist threshold
scripts/v3.py:493:                "blacklisted_clusters": 0,
scripts/v3.py:499:        # Rough blacklist count: sample centers of each record and test
scripts/v3.py:501:        # Sample-based: count how many past contexts ARE currently blacklisted
scripts/v3.py:503:            arr = np.array(r.context)
scripts/v3.py:508:            if self.is_blacklisted(ctx, r.direction):
scripts/v3.py:516:            "blacklisted_clusters": bl_count,
scripts/v3.py:521:# Position + Position Manager (per-variant)
scripts/v3.py:534:    entry_context: ContextVector
scripts/v3.py:539:    """Position manager per variant."""
scripts/v3.py:541:    def __init__(self, variant_name: str, config: dict):
scripts/v3.py:542:        self.name = variant_name
scripts/v3.py:550:        self.memory = ContextMemory(variant_name)
scripts/v3.py:564:        # Memory blacklist check (only if memory enabled)
scripts/v3.py:565:        if self.config["memory"] and self.memory.is_blacklisted(ctx, direction):
scripts/v3.py:567:            return "memory_blacklist"
scripts/v3.py:599:            entry_context=ctx,
scripts/v3.py:661:            context=pos.entry_context.to_array().tolist(),
scripts/v3.py:704:# V3 Engine (main loop, manages all variants)
scripts/v3.py:711:        # Execution timeframes used by any variant (derived from config)
scripts/v3.py:719:        self.variants: dict[str, VariantPM] = {
scripts/v3.py:723:        self.last_save = time.time()
scripts/v3.py:733:            ohlcv = self.exchange.fetch_ohlcv(self._symbol(asset), timeframe, limit=limit)
scripts/v3.py:784:    def _make_context(self, snap: MarketSnapshot, vp_distance: float, rr: float) -> ContextVector:
scripts/v3.py:794:    def _process_variant_on_bar(self, variant_name: str, asset: str,
scripts/v3.py:796:        """Evaluate entries+exits for one variant on a new bar.
scripts/v3.py:799:        If variant has htf_filter=True, neutral blocks all entries and
scripts/v3.py:802:        pm = self.variants[variant_name]
scripts/v3.py:875:        ctx = self._make_context(snap, vp_distance, rr)
scripts/v3.py:885:            print(f"  [{variant_name} {asset}] {direction.upper()} @{entry_price:.2f} "
scripts/v3.py:891:              f"| {len(VARIANTS_CONFIG)} variants")
scripts/v3.py:894:        print(f"[V3] Memory warmup: {MEMORY_WARMUP_TRADES} trades")
scripts/v3.py:915:        print(f"[V3] Dashboard API: http://localhost:{self.port}/api/state")
scripts/v3.py:917:    # Per-TF poll frequency (in ticks). Shorter TF → poll more often.
scripts/v3.py:923:        # --- HTF (1h) refresh every HTF_REFRESH_TICKS ---
scripts/v3.py:937:                    # Always refresh bias (EMA reacts to closes even without new bar)
scripts/v3.py:940:        # --- Execution TF refresh (each variant uses its own TF) ---
scripts/v3.py:955:                # New closed bar — append and fire variants
scripts/v3.py:969:                        self._process_variant_on_bar(
scripts/v3.py:975:        if time.time() - self.last_save > SAVE_INTERVAL:
scripts/v3.py:976:            self._save_state()
scripts/v3.py:977:            self.last_save = time.time()
scripts/v3.py:983:            "variants": {},
scripts/v3.py:985:        for name, pm in self.variants.items():
scripts/v3.py:986:            log_entry["variants"][name] = {
scripts/v3.py:1003:        for name, pm in self.variants.items():
scripts/v3.py:1008:        variants_data = {}
scripts/v3.py:1009:        for name, pm in self.variants.items():
scripts/v3.py:1011:            variants_data[name] = {
scripts/v3.py:1043:            "variants": variants_data,
scripts/v3.py:1045:            "variant_configs": VARIANTS_CONFIG,
scripts/v3.py:1046:            "memory_warmup": MEMORY_WARMUP_TRADES,
scripts/v3.py:1053:    def _save_state(self):
scripts/v3.py:1058:            for name, pm in self.variants.items():
scripts/v3.py:1062:            np.savez_compressed(STATE_PATH, **state)
scripts/v3.py:1063:            # Memory saved separately as JSON
scripts/v3.py:1066:            for name, pm in self.variants.items():
scripts/v3.py:1071:            print(f"  [save] state + memory persisted")
scripts/v3.py:1073:            print(f"  [save] error: {e}")
scripts/v3.py:1081:            for name, pm in self.variants.items():
scripts/v3.py:1096:                for name, pm in self.variants.items():
scripts/v3.py:1100:            print(f"  [load] tick={self.tick_count} variants restored")
scripts/v3.py:1117:                self._save_state()
scripts/v3.py:1118:                print("\n[V3] Stopped. State saved.")
scripts/v3.py:1124:            time.sleep(TICK_SEC)
scripts/v3.py:1128:# Dashboard (API only — unified dashboard on 8900 renders UI)
scripts/v3.py:1137:        if self.path.startswith("/api/state"):
scripts/v3.py:1145:            msg = b"V3 API running. Use /api/state."
scripts/triarb.py:46:STATE_PATH = DATA_DIR / "triarb_state.npz"
scripts/triarb.py:47:LOG_PATH = DATA_DIR / "triarb.jsonl"
scripts/triarb.py:50:DASH_PORT = 8899
scripts/triarb.py:118:    # "daily" variant는 1h TF 기반 장기 시각 진입. 진짜 1d(일봉) 아님.
scripts/triarb.py:410:    context: list[float]
scripts/triarb.py:424:    def __init__(self, variant_name: str):
scripts/triarb.py:425:        self.variant_name = variant_name
scripts/triarb.py:441:        distances = [(self._distance(target, np.array(r.context, dtype=float)), r) for r in same_dir]
scripts/triarb.py:451:    def is_blacklisted(self, ctx: ContextVector, direction: str) -> bool:
scripts/triarb.py:487:                "blacklisted_clusters": 0,
scripts/triarb.py:495:            arr = np.array(rec.context, dtype=float)
scripts/triarb.py:504:            if self.is_blacklisted(ctx, rec.direction):
scripts/triarb.py:512:            "blacklisted_clusters": bl_count,
scripts/triarb.py:533:    entry_context: ContextVector
scripts/triarb.py:538:    def __init__(self, variant_name: str, config: dict[str, Any]):
scripts/triarb.py:539:        self.name = variant_name
scripts/triarb.py:547:        self.memory = ContextMemory(variant_name)
scripts/triarb.py:591:        if self.config.get("memory", False) and self.memory.is_blacklisted(ctx, direction):
scripts/triarb.py:593:            return "memory_blacklist"
scripts/triarb.py:615:            entry_context=ctx,
scripts/triarb.py:681:            context=pos.entry_context.to_array().tolist(),
scripts/triarb.py:780:        self.variants = {name: VariantPM(name, cfg) for name, cfg in VARIANTS_CONFIG.items()}
scripts/triarb.py:782:        self.last_save = time.time()
scripts/triarb.py:801:            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
scripts/triarb.py:821:        print(f"[TriArb] Memory warmup: {MEMORY_WARMUP_TRADES} trades | {len(self.variants)} variants")
scripts/triarb.py:849:        print(f"[TriArb] Dashboard API: http://localhost:{self.port}/api/state")
scripts/triarb.py:883:    def _build_context(
scripts/triarb.py:939:    def _process_variant_on_bar(self, variant_name: str, pair_id: str):
scripts/triarb.py:940:        pm = self.variants[variant_name]
scripts/triarb.py:977:            ctx = self._build_context(pair_id, tf, metrics, corr, "short_ratio")
scripts/triarb.py:993:                    f"  [{variant_name} {pair_id}] SHORT_RATIO z={metrics['z']:.2f} "
scripts/triarb.py:1002:            ctx = self._build_context(pair_id, tf, metrics, corr, "long_ratio")
scripts/triarb.py:1018:                    f"  [{variant_name} {pair_id}] LONG_RATIO z={metrics['z']:.2f} "
scripts/triarb.py:1068:                        self._process_variant_on_bar(name, pair_id)
scripts/triarb.py:1072:        if time.time() - self.last_save > SAVE_INTERVAL:
scripts/triarb.py:1073:            self._save_state()
scripts/triarb.py:1074:            self.last_save = time.time()
scripts/triarb.py:1083:        variant_parts = [
scripts/triarb.py:1085:            for name, pm in self.variants.items()
scripts/triarb.py:1088:        print(f"  [tick {self.tick_count}] " + " | ".join(variant_parts))
scripts/triarb.py:1102:            "variants": {
scripts/triarb.py:1113:                for name, pm in self.variants.items()
scripts/triarb.py:1120:        variants_data = {}
scripts/triarb.py:1121:        for name, pm in self.variants.items():
scripts/triarb.py:1122:            variants_data[name] = {
scripts/triarb.py:1189:            "variants": variants_data,
scripts/triarb.py:1190:            "variant_configs": {name: pm.config for name, pm in self.variants.items()},
scripts/triarb.py:1191:            "memory_warmup": MEMORY_WARMUP_TRADES,
scripts/triarb.py:1195:    def _save_state(self):
scripts/triarb.py:1214:            for name, pm in self.variants.items():
scripts/triarb.py:1218:            np.savez_compressed(STATE_PATH, **state)
scripts/triarb.py:1221:            for name, pm in self.variants.items():
scripts/triarb.py:1227:            print("  [save] TriArb state + memory persisted")
scripts/triarb.py:1229:            print(f"  [save] error: {e}")
scripts/triarb.py:1251:            for name, pm in self.variants.items():
scripts/triarb.py:1261:                for name, pm in self.variants.items():
scripts/triarb.py:1266:                        ctx_raw = raw_pos.get("entry_context", {})
scripts/triarb.py:1268:                            raw_pos["entry_context"] = ContextVector(**ctx_raw)
scripts/triarb.py:1270:            print(f"  [load] TriArb tick={self.tick_count} variants restored")
scripts/triarb.py:1285:                self._save_state()
scripts/triarb.py:1286:                print("\n[TriArb] Stopped. State saved.")
scripts/triarb.py:1293:            time.sleep(TICK_SEC)
scripts/triarb.py:1306:        if self.path.startswith("/api/state"):
scripts/triarb.py:1314:            msg = b"TriArb API running. Use /api/state."
scripts/v2.py:11:    py -3.12 scripts/v2.py [--assets ETH,BTC,SOL,XRP] [--port 8897]
scripts/v2.py:14:    http://localhost:8897
scripts/v2.py:46:STATE_PATH = DATA_DIR / "v2_state.npz"
scripts/v2.py:47:LOG_PATH = DATA_DIR / "v2.jsonl"
scripts/v2.py:48:DASH_PORT = 8897
scripts/v2.py:116:    """Compute 28 unique features from OHLCV."""
scripts/v2.py:361:        warmup = min(n_samples / 50, 1.0)
scripts/v2.py:362:        return acc * ent_factor * warmup
scripts/v2.py:487:        if self.path == "/api/state":
scripts/v2.py:570:    const d=await(await fetch('/api/state')).json();
scripts/v2.py:620:        self.last_save = time.time()
scripts/v2.py:640:            ohlcv = self.exchange.fetch_ohlcv(self._symbol(asset), "1m", limit=HISTORY_BARS)
scripts/v2.py:651:            ohlcv = self.exchange.fetch_ohlcv(self._symbol(asset), "1m", limit=3)
scripts/v2.py:766:        if time.time() - self.last_save > SAVE_INTERVAL:
scripts/v2.py:767:            self._save_state()
scripts/v2.py:768:            self.last_save = time.time()
scripts/v2.py:841:    def _save_state(self):
scripts/v2.py:852:            np.savez_compressed(STATE_PATH, **state)
scripts/v2.py:853:            print(f"  [save] state → {STATE_PATH}")
scripts/v2.py:855:            print(f"  [save] error: {e}")
scripts/v2.py:890:                self._save_state()
scripts/v2.py:891:                print("\n[V2] Stopped. State saved.")
scripts/v2.py:895:            time.sleep(TICK_SEC)

 succeeded in 418ms:
"""V2 ??Prediction Engine.

3 Rules:
  1. Predict what happens next accurately
  2. Use memory space evenly
  3. Goal is maximum profit

NOT contrarian. Pure prediction ??trade in predicted direction.

Usage:
    py -3.12 scripts/v2.py [--assets ETH,BTC,SOL,XRP] [--port 8897]

Dashboard:
    http://localhost:8897
"""
from __future__ import annotations

import argparse
import http.server
import json
import math
import sys
import threading
import time
from dataclasses import dataclass
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
STATE_PATH = DATA_DIR / "v2_state.npz"
LOG_PATH = DATA_DIR / "v2.jsonl"
DASH_PORT = 8897
TICK_SEC = 60
HISTORY_BARS = 500
INITIAL_CAPITAL = 10_000.0
SAVE_INTERVAL = 1800

# Cost model (Bybit USDT perp)
TAKER_FEE = 0.00055        # 0.055% per side
SLIPPAGE = 0.0005           # 0.05% estimated
ROUND_TRIP_COST = (TAKER_FEE * 2) + (SLIPPAGE * 2)  # ~0.21%

# Rule 3: profit maximization with safety
KELLY_CAP = 0.25            # fractional Kelly cap
MAX_LEVERAGE = 100           # 1~100x leverage range
TOTAL_EXPOSURE_CAP = 1.0    # max 100% margin across all assets
MIN_EDGE_THRESHOLD = ROUND_TRIP_COST * 1.5  # prediction must exceed 1.5x costs

# Feature config: 28 unique features, 0 duplicates
FEATURE_NAMES = [
    # Price dynamics (6)
    "ret_1", "ret_5", "ret_15", "ret_60", "ret_240", "price_accel",
    # Trend (4)
    "sma_r5", "sma_r20", "sma_r60", "sma_r200",
    # Momentum (4)
    "rsi_14", "rsi_6", "macd_hist", "roc_20",
    # Volatility (4)
    "atr_ratio", "bb_width", "real_vol", "hl_range",
    # Volume (4)
    "vol_ratio", "obv_slope", "vwap_dist", "vol_trend",
    # Microstructure (3)
    "consec_dir", "body_wick", "range_rank",
    # Market structure (3)
    "funding_rate", "hour_sin", "hour_cos",
]
N_FEATURES = len(FEATURE_NAMES)  # 28


# ===================================================================
# EMA Normalizer (replaces Welford ??adapts to regime changes)
# ===================================================================
class EMANormalizer:
    """Exponential moving average normalizer. Adapts to non-stationarity."""

    def __init__(self, n: int, alpha: float = 0.01):
        self.n = n
        self.alpha = alpha
        self.mean = np.zeros(n)
        self.var = np.ones(n)
        self.warm = 0

    def update(self, x: np.ndarray):
        self.warm += 1
        a = max(self.alpha, 1.0 / self.warm)  # warm-up: higher alpha early
        self.mean = (1 - a) * self.mean + a * x
        diff = x - self.mean
        self.var = (1 - a) * self.var + a * diff * diff

    def normalize(self, x: np.ndarray) -> np.ndarray:
        return (x - self.mean) / (np.sqrt(self.var) + 1e-8)

    def is_warm(self) -> bool:
        return self.warm >= 50


# ===================================================================
# Feature Engine (28 features, 0 duplicates)
# ===================================================================
class FeatureEngine:
    """Compute 28 unique features from OHLCV."""

    def __init__(self):
        self._prev_ret1 = 0.0  # for price acceleration

    def compute(self, df: pd.DataFrame, funding: float = 0.0) -> np.ndarray | None:
        if len(df) < 250:
            return None
        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        lo = df["low"].values.astype(float)
        v = df["volume"].values.astype(float)
        o = df["open"].values.astype(float)
        ts = df["ts"].iloc[-1]

        feat = np.zeros(N_FEATURES, dtype=np.float64)

        # --- Price dynamics (6) ---
        ret1 = c[-1] / c[-2] - 1 if c[-2] != 0 else 0
        feat[0] = ret1
        feat[1] = c[-1] / c[-6] - 1 if c[-6] != 0 else 0
        feat[2] = c[-1] / c[-16] - 1 if c[-16] != 0 else 0
        feat[3] = c[-1] / c[-61] - 1 if c[-61] != 0 else 0
        feat[4] = c[-1] / c[-241] - 1 if len(c) > 241 and c[-241] != 0 else 0
        feat[5] = ret1 - self._prev_ret1  # acceleration
        self._prev_ret1 = ret1

        # --- Trend (4) ---
        for i, period in enumerate([5, 20, 60, 200]):
            sma = c[-period:].mean() if len(c) >= period else c.mean()
            feat[6 + i] = c[-1] / sma - 1 if sma != 0 else 0

        # --- Momentum (4) ---
        feat[10] = self._rsi_norm(c, 14)
        feat[11] = self._rsi_norm(c, 6)
        feat[12] = self._macd_hist(c)
        feat[13] = c[-1] / c[-21] - 1 if len(c) > 21 and c[-21] != 0 else 0

        # --- Volatility (4) ---
        atr14 = self._atr(h, lo, c, 14)
        atr60 = self._atr(h, lo, c, 60)
        feat[14] = atr14 / atr60 - 1 if atr60 > 0 else 0
        sma20 = c[-20:].mean()
        std20 = c[-20:].std()
        feat[15] = (2 * std20 / sma20) if sma20 > 0 else 0
        rets_20 = np.diff(c[-21:]) / (c[-21:-1] + 1e-10)
        feat[16] = np.std(rets_20) if len(rets_20) > 0 else 0
        feat[17] = (h[-1] - lo[-1]) / c[-1] if c[-1] > 0 else 0

        # --- Volume (4) ---
        vol_sma20 = v[-20:].mean()
        feat[18] = v[-1] / vol_sma20 if vol_sma20 > 0 else 1.0
        obv = np.cumsum(np.sign(np.diff(c[-21:])) * v[-20:])
        feat[19] = (obv[-1] - obv[0]) / (abs(obv[0]) + 1e-10) if len(obv) > 1 else 0
        vwap = np.sum(c[-20:] * v[-20:]) / (np.sum(v[-20:]) + 1e-10)
        feat[20] = c[-1] / vwap - 1 if vwap > 0 else 0
        vol_sma5 = v[-5:].mean()
        vol_sma60 = v[-60:].mean()
        feat[21] = vol_sma5 / vol_sma60 if vol_sma60 > 0 else 1.0

        # --- Microstructure (3) ---
        consec = 0
        for k in range(1, min(20, len(c) - 1)):
            if c[-k] > c[-k - 1]:
                if consec >= 0:
                    consec += 1
                else:
                    break
            elif c[-k] < c[-k - 1]:
                if consec <= 0:
                    consec -= 1
                else:
                    break
            else:
                break
        feat[22] = np.tanh(consec / 5.0)
        body = abs(c[-1] - o[-1])
        wick = h[-1] - lo[-1]
        feat[23] = body / wick if wick > 0 else 0.5
        ranges = h[-50:] - lo[-50:]
        feat[24] = np.searchsorted(np.sort(ranges), h[-1] - lo[-1]) / len(ranges)

        # --- Market structure (3) ---
        feat[25] = funding  # funding rate (from exchange API, cached)
        # Hour cycle: sin+cos encoding for full 24h representation
        hour = ts.hour if hasattr(ts, "hour") else 0
        feat[26] = math.sin(2 * math.pi * hour / 24)
        feat[27] = math.cos(2 * math.pi * hour / 24)

        return feat

    def _rsi_norm(self, c: np.ndarray, period: int) -> float:
        """RSI normalized to [-1, 1]."""
        if len(c) < period + 1:
            return 0.0
        delta = np.diff(c[-(period + 1):])
        gain = np.mean(np.maximum(delta, 0))
        loss = np.mean(np.maximum(-delta, 0))
        if loss == 0:
            return 1.0
        rs = gain / loss
        rsi = 100.0 - 100.0 / (1.0 + rs)
        return (rsi - 50) / 50

    def _macd_hist(self, c: np.ndarray) -> float:
        if len(c) < 35:
            return 0.0
        s = pd.Series(c)
        macd_line = s.ewm(span=12).mean().iloc[-1] - s.ewm(span=26).mean().iloc[-1]
        macd_series = s.ewm(span=12).mean() - s.ewm(span=26).mean()
        signal_line = macd_series.ewm(span=9).mean().iloc[-1]
        return (macd_line - signal_line) / c[-1] if c[-1] > 0 else 0.0

    def _atr(self, h, lo, c, period: int) -> float:
        if len(h) < period + 1:
            return 0.0
        tr = np.maximum(
            h[-period:] - lo[-period:],
            np.maximum(
                np.abs(h[-period:] - c[-period - 1:-1]),
                np.abs(lo[-period:] - c[-period - 1:-1]),
            ),
        )
        return float(tr.mean())


# ===================================================================
# Rule 1+2: Online Predictor (per-asset, entropy memory balancing)
# ===================================================================
class OnlinePredictor:
    """SGD ridge with EMA normalization + entropy-based memory balancing.

    Rule 1: Predict accurately (tracks direction accuracy, calibration).
    Rule 2: Use memory evenly (adaptive L2 via feature importance entropy).
    """

    def __init__(self, n: int = N_FEATURES, lr: float = 0.003,
                 base_l2: float = 0.001, memory_alpha: float = 2.0):
        self.n = n
        self.w = np.random.randn(n) * 0.0001
        self.b = 0.0
        self.lr = lr
        self.base_l2 = base_l2
        self.memory_alpha = memory_alpha
        self.l2_per_feat = np.full(n, base_l2)

 succeeded in 370ms:
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
        if len(df) < lookback:
            return np.array([]), np.array([])
        recent = df.iloc[-lookback:]
        lo = float(recent["low"].min())
        hi = float(recent["high"].max())
        if hi <= lo:
            return np.array([]), np.array([])
        bins = np.linspace(lo, hi, nbins + 1)
        mids = (bins[:-1] + bins[1:]) / 2.0
        volumes = np.zeros(nbins)
        for _, row in recent.iterrows():
            bar_lo, bar_hi = float(row["low"]), float(row["high"])
            bar_vol = float(row["volume"])
            if bar_hi <= bar_lo:
                continue
            # distribute bar volume across overlapping bins
            for i in range(nbins):
                b_lo, b_hi = bins[i], bins[i + 1]
                overlap = max(0.0, min(bar_hi, b_hi) - max(bar_lo, b_lo))
                if overlap > 0:
                    volumes[i] += bar_vol * overlap / (bar_hi - bar_lo)
        return mids, volumes

    @staticmethod
    def hvn_indices(volumes: np.ndarray, percentile: float = 70.0) -> np.ndarray:
        """Returns indices of bins with volume >= given percentile. HVN = top 30%."""
        if len(volumes) == 0:
            return np.array([], dtype=int)
        threshold = np.percentile(volumes, percentile)
        return np.where(volumes >= threshold)[0]


def htf_bias(df_htf: pd.DataFrame) -> str:
    """Higher-timeframe directional bias from 1h EMA20/50.

    Returns 'bullish' / 'bearish' / 'neutral'.
    bullish  = close > EMA20 > EMA50
    bearish  = close < EMA20 < EMA50
    else     = neutral (block new entries)
    """
    if df_htf is None or len(df_htf) < HTF_MIN_BARS:
        return "neutral"
    c = df_htf["close"].values.astype(float)
    ema20 = IndicatorEngine.ema(c, 20)
    ema50 = IndicatorEngine.ema(c, 50)
    close = c[-1]
    e20 = ema20[-1]
    e50 = ema50[-1]
    if close > e20 > e50:
        return "bullish"
    if close < e20 < e50:
        return "bearish"
    return "neutral"


# ===================================================================
# Market State Classifier (Parker Brooks rule sections A/B/C)
# ===================================================================
@dataclass
class MarketSnapshot:
    close: float
    vwap: float
    ema9: float
    atr14: float
    vwap_slope_3: float       # vwap_now - vwap_3bars_ago
    ema_dist_atr: float       # (close - ema9) / atr14
    recent_vwap_crosses: int  # count in last 20 bars
    close_vwap_dist_atr: float  # abs(close - vwap) / atr14
    session_hour: int
    vol_regime: float         # atr14 / atr60


def classify_state(df: pd.DataFrame, snap: MarketSnapshot, chop_strict: float) -> str:
    """A/B/C classification. chop_strict>1.0 = stricter chop detection."""
    if len(df) < 20:
        return "INSUFFICIENT_DATA"

    c = df["close"].values
    vwap_arr = IndicatorEngine.session_vwap(df)
    atr_val = snap.atr14
    if atr_val <= 0:
        return "INSUFFICIENT_DATA"

    # A. VWAP_CHOP ??any of these conditions
    # (1) > 3 VWAP crosses in last 20 bars  (tightened by chop_strict)
    max_crosses = max(1, int(round(3 / chop_strict)))
    if snap.recent_vwap_crosses > max_crosses:
        return "VWAP_CHOP"

    # (2) 4+ of last 10 bars have abs(close - vwap) <= 0.15 * ATR
    hug_threshold = 0.15 * atr_val * chop_strict
    last10 = min(10, len(c))
    hug_count = sum(
        1 for i in range(-last10, 0)
        if abs(c[i] - vwap_arr[i]) <= hug_threshold
    )
    if hug_count >= 4:
        return "VWAP_CHOP"

    # (3) ema9/vwap distance <= 0.10 * ATR for 3+ of last 5 bars
    ema_arr = IndicatorEngine.ema(c, 9)
    close_threshold = 0.10 * atr_val * chop_strict
    close_count = sum(
        1 for i in range(-min(5, len(c)), 0)
        if abs(ema_arr[i] - vwap_arr[i]) <= close_threshold
    )
    if close_count >= 3:
        return "VWAP_CHOP"

    # B/C bias
    last2_above = all(c[i] > vwap_arr[i] for i in [-1, -2])
    last2_below = all(c[i] < vwap_arr[i] for i in [-1, -2])
    vwap_rising = snap.vwap_slope_3 > 0
    vwap_falling = snap.vwap_slope_3 < 0
    ema_above_vwap = snap.ema9 > snap.vwap
    ema_below_vwap = snap.ema9 < snap.vwap

    if last2_above and vwap_rising and ema_above_vwap:
        return "LONG_BIAS"
    if last2_below and vwap_falling and ema_below_vwap:
        return "SHORT_BIAS"
    return "NEUTRAL"


# ===================================================================
# Pullback Validator (Parker Brooks D/E)
# ===================================================================
def long_pullback_valid(df: pd.DataFrame, snap: MarketSnapshot) -> tuple[bool, float]:
    """Check D. Returns (valid, recent_pullback_low)."""
    if len(df) < 7:
        return False, 0.0
    c = df["close"].values
    lo = df["low"].values
    ema_arr = IndicatorEngine.ema(c, 9)
    atr_val = snap.atr14
    if atr_val <= 0:
        return False, 0.0

    # (1) any bar in last 1-6 had low <= EMA9 + 0.10*ATR
    touch_threshold = 0.10 * atr_val
    pullback_bars = []
    for i in range(-6, 0):
        if abs(i) > len(c):
            continue
        if lo[i] <= ema_arr[i] + touch_threshold:
            pullback_bars.append(i)
    if not pullback_bars:
        return False, 0.0

    # (2) current close >= EMA9 + 0.05*ATR
    if c[-1] < ema_arr[-1] + 0.05 * atr_val:
        return False, 0.0

    # (3) current close > VWAP
    if c[-1] <= snap.vwap:
        return False, 0.0

    # (4) recent pullback low is real (at or near the lowest of recent bars)
    pullback_low = float(min(lo[i] for i in pullback_bars))
    return True, pullback_low


def short_pullback_valid(df: pd.DataFrame, snap: MarketSnapshot) -> tuple[bool, float]:
    """Check E. Returns (valid, recent_pullback_high)."""
    if len(df) < 7:
        return False, 0.0
    c = df["close"].values
    h = df["high"].values
    ema_arr = IndicatorEngine.ema(c, 9)
    atr_val = snap.atr14
    if atr_val <= 0:
        return False, 0.0

    touch_threshold = 0.10 * atr_val
    pullback_bars = []
    for i in range(-6, 0):
        if abs(i) > len(c):
            continue
        if h[i] >= ema_arr[i] - touch_threshold:
            pullback_bars.append(i)

 succeeded in 416ms:
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
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return _finite_or_none(obj)
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def _symbol_base(symbol: str) -> str:
    return symbol.split("/")[0]


# =====================================================================
# Indicator Engine
# =====================================================================
class IndicatorEngine:
    @staticmethod
    def ema(values: np.ndarray, period: int) -> np.ndarray:
        s = pd.Series(np.asarray(values, dtype=float))
        return s.ewm(span=period, adjust=False).mean().values.astype(float)

    @staticmethod
    def sma(values: np.ndarray, period: int) -> np.ndarray:
        s = pd.Series(np.asarray(values, dtype=float))
        return s.rolling(period, min_periods=period).mean().values.astype(float)

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> np.ndarray:
        h = df["high"].values.astype(float)
        lo = df["low"].values.astype(float)
        c = df["close"].values.astype(float)
        if len(c) < 2:
            return np.zeros_like(c)
        prev_c = np.concatenate([[c[0]], c[:-1]])
        tr = np.maximum.reduce([h - lo, np.abs(h - prev_c), np.abs(lo - prev_c)])
        return pd.Series(tr).rolling(period, min_periods=1).mean().values.astype(float)

    @staticmethod
    def zscore(values: np.ndarray, period: int) -> np.ndarray:
        s = pd.Series(np.asarray(values, dtype=float))
        mean = s.rolling(period, min_periods=period).mean()
        std = s.rolling(period, min_periods=period).std(ddof=0)
        z = (s - mean) / std.replace(0, np.nan)
        return z.values.astype(float)

    @staticmethod
    def correlation(x: np.ndarray, y: np.ndarray, period: int) -> np.ndarray:
        sx = pd.Series(np.asarray(x, dtype=float))
        sy = pd.Series(np.asarray(y, dtype=float))
        corr = sx.rolling(period, min_periods=period).corr(sy)
        return corr.values.astype(float)


# =====================================================================
# Pair Metrics
# =====================================================================
def compute_pair_ratio_series(leg1_close: np.ndarray, leg2_close: np.ndarray) -> np.ndarray:
    leg1 = np.asarray(leg1_close, dtype=float)
    leg2 = np.asarray(leg2_close, dtype=float)
    n = min(len(leg1), len(leg2))
    if n == 0:
        return np.array([], dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.divide(
            leg1[-n:],
            leg2[-n:],
            out=np.full(n, np.nan, dtype=float),
            where=leg2[-n:] != 0,
        )
    ratio[~np.isfinite(ratio)] = np.nan
    return ratio


def _nan_metrics() -> dict[str, float]:
    return {
        "ratio": float("nan"),
        "z": float("nan"),
        "z_prev": float("nan"),
        "z_velocity": float("nan"),
        "mean": float("nan"),
        "std": float("nan"),
        "cv": float("nan"),
    }


def compute_pair_metrics(
    leg1_close: np.ndarray, leg2_close: np.ndarray, lookback: int
) -> dict[str, float]:
    ratio = compute_pair_ratio_series(leg1_close, leg2_close)
    if len(ratio) < lookback + 1:
        return _nan_metrics()

    latest_window = ratio[-lookback:]
    prev_window = ratio[-lookback - 1 : -1]
    if np.isnan(latest_window).any() or np.isnan(prev_window).any():
        return _nan_metrics()

    mean = float(np.mean(latest_window))
    std = float(np.std(latest_window, ddof=0))
    prev_mean = float(np.mean(prev_window))
    prev_std = float(np.std(prev_window, ddof=0))
    if abs(mean) < 1e-12 or std < 1e-10 or prev_std < 1e-10:
        return _nan_metrics()

    ratio_now = float(ratio[-1])
    ratio_prev = float(ratio[-2])
    z = (ratio_now - mean) / std
    z_prev = (ratio_prev - prev_mean) / prev_std
    return {
        "ratio": ratio_now,
        "z": float(z),
        "z_prev": float(z_prev),
        "z_velocity": float(abs(z - z_prev)),
        "mean": mean,
        "std": std,
        "cv": float(std / abs(mean)),
    }


def compute_pair_correlation(
    leg1_close: np.ndarray, leg2_close: np.ndarray, period: int = CORR_LOOKBACK_BARS
) -> float:
    leg1 = np.asarray(leg1_close, dtype=float)
    leg2 = np.asarray(leg2_close, dtype=float)
    n = min(len(leg1), len(leg2))
    if n < period:
        return float("nan")
    x = leg1[-period:].astype(float)
    y = leg2[-period:].astype(float)
    mask = np.isfinite(x) & np.isfinite(y)
    if int(mask.sum()) < period:
        return float("nan")
    x = x[mask]
    y = y[mask]
    if float(np.std(x, ddof=0)) < 1e-12 or float(np.std(y, ddof=0)) < 1e-12:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def htf_strong_trend(df_htf: pd.DataFrame | None) -> str:
    if df_htf is None or len(df_htf) < HTF_MIN_BARS:
        return "mild"
    closes = df_htf["close"].values.astype(float)
    ema20 = IndicatorEngine.ema(closes, 20)
    ema50 = IndicatorEngine.ema(closes, 50)
    close = float(closes[-1])
    if close <= 0 or not np.isfinite(close):
        return "mild"
    ema50_last = float(ema50[-1])

 succeeded in 472ms:
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
<title>Trading Value ??Unified Dashboard</title>
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
  if(!imp||!imp.length){el.innerHTML='<span class="dim">?뚮컢??以?/span>';return;}
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
  let h='<table class="dtbl"><tr><th>'+label+'</th><th>?섎웾</th><th>?됯퇏?섏씡</th>'+(hasWr?'<th>?밸쪧</th>':'')+'<th></th></tr>';
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
  h+='<span>理쒓퀬: <b class="'+(retBest>0?'grn':'red')+'">'+fmt(retBest)+'</b></span>';
  h+='<span>嫄곕옒: <b>'+trades+'</b>??/span>';
  h+='<span>'+((tournament.phase)||'')+'</span>';
  h+='<span>'+(tournament.next_round||'')+'</span>';
  h+='<span class="red" style="font-size:10px">?섏닔猷? 誘몃컲??(珥앹닔??</span>';
  h+='</div></div><div class="model-body">';

  // Summary metrics
  h+='<div class="mg">';
  h+='<div class="mc"><label>理쒓퀬 ?섏씡</label><div class="val '+(retBest>0?'grn':'red')+'">'+fmt(retBest)+'</div></div>';
  h+='<div class="mc"><label>?됯퇏 ?섏씡</label><div class="val '+(retAvg>0?'grn':'red')+'">'+fmt(retAvg)+'</div></div>';
  h+='<div class="mc"><label>理쒖븙 ?먯떎</label><div class="val red">'+fmt(retWorst)+'</div></div>';
  h+='<div class="mc"><label>珥?嫄곕옒</label><div class="val">'+trades+'</div></div>';
  h+='<div class="mc"><label>?섏씡 鍮꾩쑉</label><div class="val '+(posPct>0.04?'ylw':'red')+'">'+fmt(posPct)+'</div></div>';
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
  h+='<div class="rank-card"><h3>Top 10 (?섏씡)</h3>';
  if(top10.length){
    top10.forEach((v,i)=>{

codex
주요 상수는 잡혔습니다. 이제 루프당 `fetch_ohlcv` 호출 수, variant fan-out, 상태 저장 직렬화 비용을 직접 읽어 비용 상한을 계산하겠습니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command '$c=Get-Content scripts/v3.py; $c[700..1125]' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command '$c=Get-Content scripts/triarb.py; $c[760..1295]' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command '$c=Get-Content scripts/v2.py; $c[600..905]' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-ChildItem data | Select-Object Name,Length,LastWriteTime' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 376ms:


# ===================================================================
# V3 Engine (main loop, manages all variants)
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



 succeeded in 419ms:
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



 succeeded in 474ms:
# =====================================================================
# Engine
# =====================================================================
class TriArbEngine:
    def __init__(self, port: int = DASH_PORT):
        self.port = port
        self.exchange = ccxt.bybit({"enableRateLimit": True})
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

 succeeded in 416ms:

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
triarb.jsonl                33995      2026-04-21 오후 1:03:37 
triarb_memory.json          2095       2026-04-21 오후 1:01:35 
triarb_state.npz            4538       2026-04-21 오후 1:01:35 
v2.jsonl                    333854     2026-04-21 오후 1:02:41 
v2_state.npz                14667      2026-04-21 오후 1:00:40 
v3.jsonl                    560679     2026-04-21 오후 1:01:08 
v3_memory.json              11899      2026-04-21 오후 1:03:09 
v3_state.npz                4791       2026-04-21 오후 1:03:09 
xgb_direction_model.json    215285     2026-04-01 오전 11:16:26
xgb_retrain_history.jsonl   235        2026-04-01 오전 11:16:26
_discuss_spec.json          1506       2026-03-31 오후 9:50:21 



codex
`/api/state` 응답비용은 저장보다 더 중요합니다. 메모리 스냅샷이 요청마다 O(n) 스캔인지 확인해서 대시보드 지연 상한을 계산하겠습니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command '$c=Get-Content scripts/v3.py; $c[404..520]' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command '$c=Get-Content scripts/triarb.py; $c[420..515]' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command '$c=Get-Content scripts/triarb.py; $c[1298..1325]' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command '$c=Get-Content scripts/v3.py; $c[1128..1165]' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 373ms:

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

 succeeded in 418ms:
    engine: Any = None

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/api/state"):
            body = json.dumps(self.engine.snapshot(), default=_json_default).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            msg = b"TriArb API running. Use /api/state."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)


def main():
    parser = argparse.ArgumentParser(description="TriArb -- Pairs Ratio Arbitrage")
    parser.add_argument("--port", type=int, default=DASH_PORT)
    args = parser.parse_args()
    TriArbEngine(port=args.port).run()


 succeeded in 459ms:
# ===================================================================
class DashboardHandler(http.server.BaseHTTPRequestHandler):
    engine: Any = None

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/api/state"):
            body = json.dumps(self.engine.snapshot()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            msg = b"V3 API running. Use /api/state."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", len(msg))
            self.end_headers()
            self.wfile.write(msg)


def main():
    parser = argparse.ArgumentParser(description="V3 Parker Brooks + Context Memory")
    parser.add_argument("--assets", default="ETH,BTC,SOL,XRP")
    parser.add_argument("--port", type=int, default=DASH_PORT)
    args = parser.parse_args()
    assets = [a.strip().upper() for a in args.assets.split(",")]
    V3Engine(assets=assets, port=args.port).run()


if __name__ == "__main__":
    main()

 succeeded in 529ms:


class ContextMemory:
    def __init__(self, variant_name: str):
        self.variant_name = variant_name
        self.records: list[TradeRecord] = []

    def add(self, record: TradeRecord):
        self.records.append(record)

    def _distance(self, a: np.ndarray, b: np.ndarray) -> float:
        diff = a - b
        diff[4] = 0.0 if a[4] == b[4] else 2.0
        return float(np.linalg.norm(diff))

    def _neighbors(self, ctx: ContextVector, direction: str, k: int) -> list[TradeRecord]:
        if not self.records:
            return []
        target = ctx.to_array()
        same_dir = [r for r in self.records if r.direction == direction]
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

codex
현재 저장 크기만 보면 문제를 숨길 수 있어 메모리 레코드 수와 로그 길이도 확인하겠습니다. 운영 상한은 현재 관측치와 10k-trade extrapolation을 분리해서 판단하겠습니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "(Get-Content data\\v2.jsonl | Measure-Object -Line).Lines; (Get-Content data\\v3.jsonl | Measure-Object -Line).Lines; (Get-Content data\\triarb.jsonl | Measure-Object -Line).Lines" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content data\\v3_memory.json" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content data\\triarb_memory.json" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 319ms:
{"memory": {"v3-3m": [{"context": [0.009392126650245483, 0.138342124980445, 2.4839760638298602, 2.1207425068119274, 5.0, 0.8544969035850088], "direction": "long", "entry_price": 75891.2, "exit_price": 76077.995, "r_multiple": 2.1207425068119274, "net_pct": 0.010206762839433548, "asset": "BTC", "timestamp": "22:09:37"}, {"context": [0.01512648560700651, 0.07295717629033933, 1.6250206916402692, 1.6041612271244376, 5.0, 0.7820991632729543], "direction": "long", "entry_price": 75927.6, "exit_price": 75860.57535714285, "r_multiple": -1.0, "net_pct": -0.006513720627094442, "asset": "BTC", "timestamp": "23:03:34"}], "v3-5m": [{"context": [-0.009064666772060437, -0.26811805286088924, 3.151400933955932, 5.6652275589133625, 0.0, 0.6971741733943632], "direction": "short", "entry_price": 2276.66, "exit_price": 2279.0424285714284, "r_multiple": -1.0, "net_pct": -0.007332288904423177, "asset": "ETH", "timestamp": "02:50:57"}, {"context": [0.029930766743391502, 0.18691648789898294, 2.090904168922544, 1.7076341447235688, 5.0, 0.8102476365949408], "direction": "long", "entry_price": 75964.1, "exit_price": 75880.6, "r_multiple": -0.6461276558112312, "net_pct": -0.00759601719759707, "asset": "BTC", "timestamp": "22:50:20"}, {"context": [0.031018005401202337, 0.11108409237611962, 4.410895166534348, 2.1735571762468395, 5.0, 0.8638962400758856], "direction": "long", "entry_price": 75748.7, "exit_price": 75693.4, "r_multiple": -0.27563225061102564, "net_pct": -0.0057502276606731335, "asset": "BTC", "timestamp": "00:10:45"}], "v3-15m": [], "v3-30m": [], "v3-5m-aggressive": [{"context": [-0.009064666772060437, -0.26811805286088924, 3.151400933955932, 5.6652275589133625, 0.0, 0.6971741733943632], "direction": "short", "entry_price": 2276.66, "exit_price": 2279.0424285714284, "r_multiple": -1.0, "net_pct": -0.007332288904423177, "asset": "ETH", "timestamp": "02:50:57"}, {"context": [0.019398304889944974, 0.36110829346598955, 1.9789617114048004, 1.4577756364894185, 5.0, 0.7939032041712675], "direction": "long", "entry_price": 75977.3, "exit_price": 75880.6, "r_multiple": -0.6794240603842553, "net_pct": -0.008463742854773592, "asset": "BTC", "timestamp": "22:50:20"}, {"context": [0.031018005401202337, 0.11108409237611962, 4.410895166534348, 2.1735571762468395, 5.0, 0.8638962400758856], "direction": "long", "entry_price": 75748.7, "exit_price": 75693.4, "r_multiple": -0.27563225061102564, "net_pct": -0.0057502276606731335, "asset": "BTC", "timestamp": "00:10:45"}], "v3-5m-conservative": [{"context": [-0.009064666772060437, -0.26811805286088924, 3.151400933955932, 5.6652275589133625, 0.0, 0.6971741733943632], "direction": "short", "entry_price": 2276.66, "exit_price": 2279.0424285714284, "r_multiple": -1.0, "net_pct": -0.007332288904423177, "asset": "ETH", "timestamp": "02:50:57"}, {"context": [0.031018005401202337, 0.11108409237611962, 4.410895166534348, 2.1735571762468395, 5.0, 0.8638962400758856], "direction": "long", "entry_price": 75748.7, "exit_price": 75693.4, "r_multiple": -0.27563225061102564, "net_pct": -0.0057502276606731335, "asset": "BTC", "timestamp": "00:10:45"}], "v3-control": [{"context": [0.2338840538171816, 0.2603980894454294, 3.0856655290102974, 2.420939884857439, 0.0, 0.9046932894195141], "direction": "long", "entry_price": 2273.58, "exit_price": 2276.86, "r_multiple": 0.4391484803856176, "net_pct": 0.005113293572252421, "asset": "ETH", "timestamp": "01:25:58"}, {"context": [0.06959539748924956, 0.5979664335954428, 2.6233601748718476, 3.6723872780806905, 0.0, 0.8967505278860902], "direction": "long", "entry_price": 74210.9, "exit_price": 74191.0, "r_multiple": -0.18805455337040097, "net_pct": -0.0034407733904313715, "asset": "BTC", "timestamp": "01:25:58"}, {"context": [0.20989857333623485, 0.28197489827144223, 5.713513513513545, 3.0838803792851843, 0.0, 0.9286760092030885], "direction": "long", "entry_price": 83.76, "exit_price": 83.95, "r_multiple": 0.48504741064915463, "net_pct": 0.009241929321871945, "asset": "SOL", "timestamp": "01:25:58"}, {"context": [0.20886044857558672, 0.5620812063736464, 1.9221405228758297, 2.6211007130128023, 0.0, 0.845946506323867], "direction": "long", "entry_price": 1.406, "exit_price": 1.4046, "r_multiple": -0.6550802139037453, "net_pct": -0.007078662873399431, "asset": "XRP", "timestamp": "01:25:58"}, {"context": [0.08447152164248509, 0.2791104426862556, 3.463113225144459, 3.5499244727433577, 0.0, 0.6318366841833253], "direction": "long", "entry_price": 74256.8, "exit_price": 74610.43333333333, "r_multiple": 3.5499244727433577, "net_pct": 0.02171151176278351, "asset": "BTC", "timestamp": "01:40:06"}, {"context": [0.1270010991420991, 0.43421930587095275, 5.26210235131401, 4.625813119338416, 0.0, 0.7611327508158686], "direction": "long", "entry_price": 84.06, "exit_price": 84.12, "r_multiple": 0.3064016049607897, "net_pct": 0.0014688793718768871, "asset": "SOL", "timestamp": "02:05:20"}, {"context": [-0.009064666772060437, -0.26811805286088924, 3.151400933955932, 5.6652275589133625, 0.0, 0.6971741733943632], "direction": "short", "entry_price": 2276.66, "exit_price": 2279.0424285714284, "r_multiple": -1.0, "net_pct": -0.007332288904423177, "asset": "ETH", "timestamp": "02:50:57"}, {"context": [0.19312558874855082, 0.1621082006416573, 2.62210401891249, 1.6494163134806206, 0.0, 0.6401331719128355], "direction": "long", "entry_price": 1.4062, "exit_price": 1.4114816666666665, "r_multiple": 1.6494163134806206, "net_pct": 0.016679926989996863, "asset": "XRP", "timestamp": "03:15:28"}, {"context": [0.041803236373102313, 0.4065321302158865, 4.852161785216122, 3.515739477540155, 0.0, 0.7615507169410486], "direction": "long", "entry_price": 84.15, "exit_price": 84.4, "r_multiple": 1.0610883735030832, "net_pct": 0.012754426619133053, "asset": "SOL", "timestamp": "04:10:26"}, {"context": [0.029930766743391502, 0.18691648789898294, 2.090904168922544, 1.7076341447235688, 5.0, 0.8102476365949408], "direction": "long", "entry_price": 75964.1, "exit_price": 75880.6, "r_multiple": -0.6461276558112312, "net_pct": -0.00759601719759707, "asset": "BTC", "timestamp": "22:50:20"}, {"context": [0.031018005401202337, 0.11108409237611962, 4.410895166534348, 2.1735571762468395, 5.0, 0.8638962400758856], "direction": "long", "entry_price": 75748.7, "exit_price": 75693.4, "r_multiple": -0.27563225061102564, "net_pct": -0.0057502276606731335, "asset": "BTC", "timestamp": "00:10:45"}]}, "trade_logs": {"v3-3m": [{"asset": "BTC", "dir": "long", "entry": 75891.2, "exit": 76077.995, "target": 76077.995, "hard_stop": 75803.12, "size": 0.2, "lev": 5.0, "r_mult": 2.121, "net": 0.002041, "net_pct": 0.010207, "capital": 10020.41, "reason": "target", "time": "22:09:37"}, {"asset": "BTC", "dir": "long", "entry": 75927.6, "exit": 75860.5754, "target": 76035.1183, "hard_stop": 75860.5754, "size": 0.2, "lev": 5.0, "r_mult": -1.0, "net": -0.001303, "net_pct": -0.006514, "capital": 10007.36, "reason": "hard_stop", "time": "23:03:34"}], "v3-5m": [{"asset": "ETH", "dir": "short", "entry": 2276.66, "exit": 2279.0424, "target": 2263.163, "hard_stop": 2279.0424, "size": 0.2, "lev": 5.0, "r_mult": -1.0, "net": -0.001466, "net_pct": -0.007332, "capital": 9985.34, "reason": "hard_stop", "time": "02:50:57"}, {"asset": "BTC", "dir": "long", "entry": 75964.1, "exit": 75880.6, "target": 76184.78, "hard_stop": 75834.8686, "size": 0.2, "lev": 5.0, "r_mult": -0.646, "net": -0.001519, "net_pct": -0.007596, "capital": 9970.17, "reason": "soft_stop", "time": "22:50:20"}, {"asset": "BTC", "dir": "long", "entry": 75748.7, "exit": 75693.4, "target": 76184.78, "hard_stop": 75548.0704, "size": 0.2, "lev": 5.0, "r_mult": -0.276, "net": -0.00115, "net_pct": -0.00575, "capital": 9958.7, "reason": "soft_stop", "time": "00:10:45"}], "v3-15m": [], "v3-30m": [], "v3-5m-aggressive": [{"asset": "ETH", "dir": "short", "entry": 2276.66, "exit": 2279.0424, "target": 2263.163, "hard_stop": 2279.0424, "size": 0.2, "lev": 5.0, "r_mult": -1.0, "net": -0.001466, "net_pct": -0.007332, "capital": 9985.34, "reason": "hard_stop", "time": "02:50:57"}, {"asset": "BTC", "dir": "long", "entry": 75977.3, "exit": 75880.6, "target": 76184.78, "hard_stop": 75834.9736, "size": 0.2, "lev": 5.0, "r_mult": -0.679, "net": -0.001693, "net_pct": -0.008464, "capital": 9968.43, "reason": "soft_stop", "time": "22:50:20"}, {"asset": "BTC", "dir": "long", "entry": 75748.7, "exit": 75693.4, "target": 76184.78, "hard_stop": 75548.0704, "size": 0.2, "lev": 5.0, "r_mult": -0.276, "net": -0.00115, "net_pct": -0.00575, "capital": 9956.97, "reason": "soft_stop", "time": "00:10:45"}], "v3-5m-conservative": [{"asset": "ETH", "dir": "short", "entry": 2276.66, "exit": 2279.0424, "target": 2263.163, "hard_stop": 2279.0424, "size": 0.2, "lev": 5.0, "r_mult": -1.0, "net": -0.001466, "net_pct": -0.007332, "capital": 9985.34, "reason": "hard_stop", "time": "02:50:57"}, {"asset": "BTC", "dir": "long", "entry": 75748.7, "exit": 75693.4, "target": 76184.78, "hard_stop": 75548.0704, "size": 0.2, "lev": 5.0, "r_mult": -0.276, "net": -0.00115, "net_pct": -0.00575, "capital": 9973.85, "reason": "soft_stop", "time": "00:10:45"}], "v3-control": [{"asset": "ETH", "dir": "long", "entry": 2273.58, "exit": 2276.86, "target": 2291.662, "hard_stop": 2266.111, "size": 0.2, "lev": 5.0, "r_mult": 0.439, "net": 0.001023, "net_pct": 0.005113, "capital": 10010.23, "reason": "soft_stop", "time": "01:25:58"}, {"asset": "BTC", "dir": "long", "entry": 74210.9, "exit": 74191.0, "target": 74599.5133, "hard_stop": 74105.0796, "size": 0.2, "lev": 5.0, "r_mult": -0.188, "net": -0.000688, "net_pct": -0.003441, "capital": 10003.34, "reason": "soft_stop", "time": "01:25:58"}, {"asset": "SOL", "dir": "long", "entry": 83.76, "exit": 83.95, "target": 84.968, "hard_stop": 83.3683, "size": 0.2, "lev": 5.0, "r_mult": 0.485, "net": 0.001848, "net_pct": 0.009242, "capital": 10021.83, "reason": "soft_stop", "time": "01:25:58"}, {"asset": "XRP", "dir": "long", "entry": 1.406, "exit": 1.4046, "target": 1.4116, "hard_stop": 1.4039, "size": 0.2, "lev": 5.0, "r_mult": -0.655, "net": -0.001416, "net_pct": -0.007079, "capital": 10007.64, "reason": "soft_stop", "time": "01:25:58"}, {"asset": "BTC", "dir": "long", "entry": 74256.8, "exit": 74610.4333, "target": 74610.4333, "hard_stop": 74157.1829, "size": 0.2, "lev": 5.0, "r_mult": 3.55, "net": 0.004342, "net_pct": 0.021712, "capital": 10051.1, "reason": "target", "time": "01:40:06"}, {"asset": "SOL", "dir": "long", "entry": 84.06, "exit": 84.12, "target": 84.9658, "hard_stop": 83.8642, "size": 0.2, "lev": 5.0, "r_mult": 0.306, "net": 0.000294, "net_pct": 0.001469, "capital": 10054.05, "reason": "soft_stop", "time": "02:05:20"}, {"asset": "ETH", "dir": "short", "entry": 2276.66, "exit": 2279.0424, "target": 2263.163, "hard_stop": 2279.0424, "size": 0.2, "lev": 5.0, "r_mult": -1.0, "net": -0.001466, "net_pct": -0.007332, "capital": 10039.3, "reason": "hard_stop", "time": "02:50:57"}, {"asset": "XRP", "dir": "long", "entry": 1.4062, "exit": 1.4115, "target": 1.4115, "hard_stop": 1.403, "size": 0.2, "lev": 5.0, "r_mult": 1.649, "net": 0.003336, "net_pct": 0.01668, "capital": 10072.8, "reason": "target", "time": "03:15:28"}, {"asset": "SOL", "dir": "long", "entry": 84.15, "exit": 84.4, "target": 84.9783, "hard_stop": 83.9144, "size": 0.2, "lev": 5.0, "r_mult": 1.061, "net": 0.002551, "net_pct": 0.012754, "capital": 10098.49, "reason": "soft_stop", "time": "04:10:26"}, {"asset": "BTC", "dir": "long", "entry": 75964.1, "exit": 75880.6, "target": 76184.78, "hard_stop": 75834.8686, "size": 0.2, "lev": 5.0, "r_mult": -0.646, "net": -0.001519, "net_pct": -0.007596, "capital": 10083.15, "reason": "soft_stop", "time": "22:50:20"}, {"asset": "BTC", "dir": "long", "entry": 75748.7, "exit": 75693.4, "target": 76184.78, "hard_stop": 75548.0704, "size": 0.2, "lev": 5.0, "r_mult": -0.276, "net": -0.00115, "net_pct": -0.00575, "capital": 10071.55, "reason": "soft_stop", "time": "00:10:45"}]}}

 succeeded in 422ms:
1923
454
31

 succeeded in 311ms:
{"memory": {"triarb-5m": [], "triarb-30m": [], "triarb-daily": [], "triarb-tight": [], "triarb-control": []}, "trade_logs": {"triarb-5m": [], "triarb-30m": [], "triarb-daily": [], "triarb-tight": [], "triarb-control": []}, "positions": {"triarb-5m": [{"pair_id": "SOLETH", "direction": "long_ratio", "entry_ratio": 0.036850420968335386, "entry_z": -2.037958790044627, "entry_price_leg1": 85.13, "entry_price_leg2": 2310.15, "size_leg1": 5.87337013978621, "size_leg2": 0.21643616215397268, "notional_per_leg_usd": 500.0, "leverage": 5.0, "entry_time": "04:00:35", "entry_bar_idx": 30, "entry_context": {"spread_zscore": 2.037958790044627, "spread_velocity": 0.1453337844282072, "correlation_30d": 0.9475274289901116, "leg_vol_ratio": 1.2217144007802627, "session_hour_bucket": 0, "vol_regime": 1.810940413872049}, "entry_capital": 10000.0}], "triarb-30m": [], "triarb-daily": [], "triarb-tight": [{"pair_id": "SOLETH", "direction": "long_ratio", "entry_ratio": 0.036850420968335386, "entry_z": -2.037958790044627, "entry_price_leg1": 85.13, "entry_price_leg2": 2310.15, "size_leg1": 5.87337013978621, "size_leg2": 0.21643616215397268, "notional_per_leg_usd": 500.0, "leverage": 5.0, "entry_time": "04:00:35", "entry_bar_idx": 30, "entry_context": {"spread_zscore": 2.037958790044627, "spread_velocity": 0.1453337844282072, "correlation_30d": 0.9475274289901116, "leg_vol_ratio": 1.2217144007802627, "session_hour_bucket": 0, "vol_regime": 1.810940413872049}, "entry_capital": 10000.0}], "triarb-control": [{"pair_id": "SOLETH", "direction": "long_ratio", "entry_ratio": 0.036850420968335386, "entry_z": -2.037958790044627, "entry_price_leg1": 85.13, "entry_price_leg2": 2310.15, "size_leg1": 5.87337013978621, "size_leg2": 0.21643616215397268, "notional_per_leg_usd": 500.0, "leverage": 5.0, "entry_time": "04:00:35", "entry_bar_idx": 30, "entry_context": {"spread_zscore": 2.037958790044627, "spread_velocity": 0.1453337844282072, "correlation_30d": 0.9475274289901116, "leg_vol_ratio": 1.2217144007802627, "session_hour_bucket": 0, "vol_regime": 1.810940413872049}, "entry_capital": 10000.0}]}}

codex
대시보드 체감 지연은 단순 타임아웃보다 겹침 여부가 더 중요합니다. `refresh()`가 이전 요청 완료를 기다리지 않는 구조인지 확인해서 응답 상한을 보수적으로 잡겠습니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command '$c=Get-Content scripts/dashboard_unified.py; $c[628..688]' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "rg -n \"def snapshot|memory\\.snapshot\\(|trade_log\\[-|pnl_history\\[-|json.dumps\\(self\\.engine\\.snapshot|urlopen\\(req, timeout=3\\)|setInterval\\(refresh,5000\\)\" scripts/v2.py scripts/v3.py scripts/triarb.py scripts/dashboard_unified.py" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 364ms:
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



 succeeded in 319ms:
scripts/dashboard_unified.py:39:        with urllib.request.urlopen(req, timeout=3) as resp:
scripts/dashboard_unified.py:684:setInterval(refresh,5000);
scripts/triarb.py:479:    def snapshot(self) -> dict[str, Any]:
scripts/triarb.py:1119:    def snapshot(self) -> dict[str, Any]:
scripts/triarb.py:1136:                "pnl_history": pm.pnl_history[-300:],
scripts/triarb.py:1137:                "trade_log": pm.trade_log[-50:],
scripts/triarb.py:1138:                "memory": pm.memory.snapshot(),
scripts/triarb.py:1217:                state[f"{name}_pnl"] = np.array(pm.pnl_history[-1000:])
scripts/triarb.py:1223:                blob["trade_logs"][name] = pm.trade_log[-200:]
scripts/triarb.py:1307:            body = json.dumps(self.engine.snapshot(), default=_json_default).encode()
scripts/v3.py:485:    def snapshot(self) -> dict:
scripts/v3.py:1007:    def snapshot(self) -> dict:
scripts/v3.py:1010:            ms = pm.memory.snapshot()
scripts/v3.py:1029:                "pnl_history": pm.pnl_history[-300:],
scripts/v3.py:1030:                "trade_log": pm.trade_log[-30:],
scripts/v3.py:1061:                state[f"{name}_pnl"] = np.array(pm.pnl_history[-1000:])
scripts/v3.py:1068:                trade_logs[name] = pm.trade_log[-200:]
scripts/v3.py:1138:            body = json.dumps(self.engine.snapshot()).encode()
scripts/v2.py:488:            body = json.dumps(self.engine.snapshot()).encode()
scripts/v2.py:796:    def snapshot(self) -> dict:
scripts/v2.py:827:            "pnl_history": self.pm.pnl_history[-500:],
scripts/v2.py:838:            "trade_log": self.pm.trade_log[-50:],

codex
[AGREE]

1. **Reasoning**: Phase 0은 Charter 착수엔 충분합니다. 다만 비용 관점에서 조건부입니다: 한 Windows 머신은 `Oracle=단일 예측 엔진`이면 감당 가능하지만, Oracle이 V3처럼 `다중 variants + k-NN + 무한 메모리 스캔`을 복제하면 병목은 CPU보다도 `/api/state` 지연과 중복 REST polling에서 먼저 옵니다. 현재 3모델만으로도 steady-state가 대략 `~20 REST calls/min`이고, Oracle이 추가되면 `+4~10/min`이 붙습니다.
2. **쟁점 1 답**: `B` 신규 `oracle.py`입니다. 덮어쓰기로 절감되는 건 사실상 `v2.py`의 `~4.1 calls/min`뿐인데, 대신 롤백과 베이스라인을 잃습니다. 비용/속도 관점의 타협점은 `코드는 분리, 운영은 동시 실행 금지`입니다. 즉 Oracle 활성 시 V2 프로세스는 내리되, 파일은 남겨야 합니다.
3. **쟁점 2 답**: 48시간 Rule 2 제거 실험은 타당한 `반증 게이트`입니다. 다만 기준은 승률 하나가 아니라 `0.21% RT 비용 반영 순손익`, 자산별 일관성, 그리고 운영 지연까지 포함해야 합니다. Rule 2-off가 미리 선언한 기준, 예를 들면 `60%+`, `net positive after costs`, `API latency no worse`를 못 넘으면 재설계 정당화는 충분합니다.
4. **쟁점 3 답**: Oracle이 V3와 다른 경우는 `예측 엔진 전용 context 공간`을 가질 때뿐입니다. 예를 들면 `predicted_edge`, `calibration/uncertainty`, `vol_regime`, `feature regime` 같은 축입니다. V3의 `vwap_slope / vp_clearance / rr_estimate`는 규칙엔진의 setup·trade management 메모리이지, 다음 바의 alpha 예측 공간이 아닙니다. 그 차별화가 없으면 Oracle은 중복입니다.
5. **Updated position**: Round 1의 `B`는 유지하지만, 운영 제약은 더 강하게 봅니다. Charter 전에 `공유 OHLCV collector/cache`를 못 박아야 합니다. 지금 구조는 모델별로 데이터를 따로 fetch하므로 rate-limit보다 `burstiness`와 중복 fetch가 문제입니다. 또 저장 파일은 V3/TriArb가 `최근 500개`만 저장해서 `10k+ trades`에서도 디스크 save/load는 버티지만, 런타임 메모리는 계속 커지고 `memory.snapshot()`은 variant당 `O(50*n)`이라 Oracle `/api/state`는 `p95 < 500ms`, `hard cap < 1s`로 제한해야 합니다. 대시보드는 3초 timeout에 5초 refresh, 그리고 `refresh` 겹침 방지가 없습니다.

[POSITION: Phase 1 진입은 가능하지만, `oracle.py` 분리 유지와 48시간 Rule2 반증 실험, 그리고 공유 폴링·bounded memory·sub-500ms state API를 Charter 전제조건으로 올려야 한다.]
tokens used
64,723
[AGREE]

1. **Reasoning**: Phase 0은 Charter 착수엔 충분합니다. 다만 비용 관점에서 조건부입니다: 한 Windows 머신은 `Oracle=단일 예측 엔진`이면 감당 가능하지만, Oracle이 V3처럼 `다중 variants + k-NN + 무한 메모리 스캔`을 복제하면 병목은 CPU보다도 `/api/state` 지연과 중복 REST polling에서 먼저 옵니다. 현재 3모델만으로도 steady-state가 대략 `~20 REST calls/min`이고, Oracle이 추가되면 `+4~10/min`이 붙습니다.
2. **쟁점 1 답**: `B` 신규 `oracle.py`입니다. 덮어쓰기로 절감되는 건 사실상 `v2.py`의 `~4.1 calls/min`뿐인데, 대신 롤백과 베이스라인을 잃습니다. 비용/속도 관점의 타협점은 `코드는 분리, 운영은 동시 실행 금지`입니다. 즉 Oracle 활성 시 V2 프로세스는 내리되, 파일은 남겨야 합니다.
3. **쟁점 2 답**: 48시간 Rule 2 제거 실험은 타당한 `반증 게이트`입니다. 다만 기준은 승률 하나가 아니라 `0.21% RT 비용 반영 순손익`, 자산별 일관성, 그리고 운영 지연까지 포함해야 합니다. Rule 2-off가 미리 선언한 기준, 예를 들면 `60%+`, `net positive after costs`, `API latency no worse`를 못 넘으면 재설계 정당화는 충분합니다.
4. **쟁점 3 답**: Oracle이 V3와 다른 경우는 `예측 엔진 전용 context 공간`을 가질 때뿐입니다. 예를 들면 `predicted_edge`, `calibration/uncertainty`, `vol_regime`, `feature regime` 같은 축입니다. V3의 `vwap_slope / vp_clearance / rr_estimate`는 규칙엔진의 setup·trade management 메모리이지, 다음 바의 alpha 예측 공간이 아닙니다. 그 차별화가 없으면 Oracle은 중복입니다.
5. **Updated position**: Round 1의 `B`는 유지하지만, 운영 제약은 더 강하게 봅니다. Charter 전에 `공유 OHLCV collector/cache`를 못 박아야 합니다. 지금 구조는 모델별로 데이터를 따로 fetch하므로 rate-limit보다 `burstiness`와 중복 fetch가 문제입니다. 또 저장 파일은 V3/TriArb가 `최근 500개`만 저장해서 `10k+ trades`에서도 디스크 save/load는 버티지만, 런타임 메모리는 계속 커지고 `memory.snapshot()`은 variant당 `O(50*n)`이라 Oracle `/api/state`는 `p95 < 500ms`, `hard cap < 1s`로 제한해야 합니다. 대시보드는 3초 timeout에 5초 refresh, 그리고 `refresh` 겹침 방지가 없습니다.

[POSITION: Phase 1 진입은 가능하지만, `oracle.py` 분리 유지와 48시간 Rule2 반증 실험, 그리고 공유 폴링·bounded memory·sub-500ms state API를 Charter 전제조건으로 올려야 한다.]
