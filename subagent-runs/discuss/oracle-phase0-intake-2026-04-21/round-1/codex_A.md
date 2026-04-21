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
session id: 019dadfe-0274-7801-9941-d892a7c39f97
--------
user
# Your Role: **Codex gpt-5.4 (A) — 구현 가능성 + 복잡도 관점**

당신은 실제 코드를 짜야 하는 구현자입니다. 위 Phase 0 요약을 기준으로:
- 현재 제약(Python 3.12 + ccxt/numpy/pandas)으로 Oracle을 만들 수 있는가?
- `dashboard_unified.py` 통합 요구가 구현 공수를 얼마나 늘리는가?
- npz+jsonl 상태 파일 구조가 context-aware 학습에 적합한가?
- V3/TriArb 코드베이스 재활용률은 얼마나 될까? (k-NN, ContextMemory, HTFFilter 등)

구현자의 현실적 눈으로 판정하라. 과장/낙관 금지.

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
Phase 0 검증 관점에서 구현 가능성과 실제 공수를 코드 기준으로 판정하겠습니다. 먼저 세션 규칙대로 WKI 인덱스를 갱신하고 `project-status/current.md`, V2/V3/TriArb/대시보드 코드를 읽어 재활용 가능 범위와 숨은 제약을 확인하겠습니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'node workspace-knowledge-index/dist/index.js index' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
2026-04-21T03:03:34.356776Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 0.5 seconds
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

 exited 1 in 469ms:
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

codex
WKI 경로가 현재 작업 디렉터리에 없어서 바로 실행되진 않았습니다. 경로를 확인하는 동안 `project-status/current.md`와 핵심 스크립트를 함께 읽어 실제 구현 기준으로 판단하겠습니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-ChildItem -Name' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content project-status/current.md' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "rg --files scripts data project-status . | rg \"(v2\\.py|v3\\.py|triarb\\.py|dashboard_unified\\.py|feedback_self_learning_algorithm\\.md|workspace-knowledge-index)\"" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 353ms:
.knowledge
.pytest_cache
archive
config
data
docs
html
reusable-components
scripts
tests
auto_trading_state_machine_design.md
breakthrough-guide.md
coin_strategy_spec.md
coin_strategy_spec_v2.md
limits-history.md
pyproject.toml
README.md
RESUME.md
reusable_components_guide.md
uv.lock

2026-04-21T03:03:41.019799Z ERROR codex_core::tools::router: error=Exit code: 1
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
 

 exited 1 in 456ms:
Get-Content : 'C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value\project-status\current.md' 경로는 존재하지 않
으므로 찾을 수 없습니다.
위치 줄:2 문자:1
+ Get-Content project-status/current.md
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:\Users\haj\pr...atus\current.md:String) [Get-Content], ItemNotFoundEx 
   ception
    + FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.GetContentCommand
 

2026-04-21T03:03:41.061741Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 0.4 seconds
Output:
scripts\_smoke_triarb.py
scripts\validate_v2.py
scripts\v3.py
scripts\v2.py
scripts\triarb.py
scripts\optimize_v3.py
scripts\optimize_v2.py
scripts\dashboard_unified.py
.\scripts\_smoke_triarb.py
.\scripts\validate_v2.py
.\scripts\v3.py
.\scripts\v2.py
.\scripts\triarb.py
.\scripts\optimize_v3.py
.\scripts\optimize_v2.py
.\scripts\dashboard_unified.py
rg: project-status: 지정된 파일을 찾을 수 없습니다. (os error 2)

 exited 1 in 422ms:
scripts\_smoke_triarb.py
scripts\validate_v2.py
scripts\v3.py
scripts\v2.py
scripts\triarb.py
scripts\optimize_v3.py
scripts\optimize_v2.py
scripts\dashboard_unified.py
.\scripts\_smoke_triarb.py
.\scripts\validate_v2.py
.\scripts\v3.py
.\scripts\v2.py
.\scripts\triarb.py
.\scripts\optimize_v3.py
.\scripts\optimize_v2.py
.\scripts\dashboard_unified.py
rg: project-status: 지정된 파일을 찾을 수 없습니다. (os error 2)

codex
`project-status/current.md`도 현재 워크스페이스에는 없습니다. 이 평가는 현행 코드와 문서 기준으로 진행하되, 세션 필수 파일과 WKI 경로가 빠져 있다는 점은 Phase 0의 운영 리스크로 같이 반영하겠습니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'rg -n "class |def |ContextMemory|HTF|k-NN|knn|MODELS|8897|8898|8899|8900|npz|jsonl|blacklist|warmup|variant|trust|entropy" scripts/v2.py scripts/v3.py scripts/triarb.py scripts/dashboard_unified.py' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "rg --files . | rg \"feedback_self_learning_algorithm\\.md|current\\.md|workspace-knowledge-index|submix|discuss\"" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/v2.py -TotalCount 260' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/v3.py -TotalCount 320' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/triarb.py -TotalCount 320' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/dashboard_unified.py -TotalCount 260' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 339ms:
scripts/triarb.py:46:STATE_PATH = DATA_DIR / "triarb_state.npz"
scripts/triarb.py:47:LOG_PATH = DATA_DIR / "triarb.jsonl"
scripts/triarb.py:50:DASH_PORT = 8899
scripts/triarb.py:67:HTF_TIMEFRAME = "1h"
scripts/triarb.py:68:HTF_MIN_BARS = 60
scripts/triarb.py:69:HTF_REFRESH_TICKS = 15
scripts/triarb.py:70:HTF_STRONG_TREND_THRESHOLD = 0.02
scripts/triarb.py:118:    # "daily" variant는 1h TF 기반 장기 시각 진입. 진짜 1d(일봉) 아님.
scripts/triarb.py:160:def _finite_or_none(value: Any) -> float | None:
scripts/triarb.py:168:def _json_default(obj: Any) -> Any:
scripts/triarb.py:180:def _symbol_base(symbol: str) -> str:
scripts/triarb.py:187:class IndicatorEngine:
scripts/triarb.py:189:    def ema(values: np.ndarray, period: int) -> np.ndarray:
scripts/triarb.py:194:    def sma(values: np.ndarray, period: int) -> np.ndarray:
scripts/triarb.py:199:    def atr(df: pd.DataFrame, period: int = 14) -> np.ndarray:
scripts/triarb.py:210:    def zscore(values: np.ndarray, period: int) -> np.ndarray:
scripts/triarb.py:218:    def correlation(x: np.ndarray, y: np.ndarray, period: int) -> np.ndarray:
scripts/triarb.py:228:def compute_pair_ratio_series(leg1_close: np.ndarray, leg2_close: np.ndarray) -> np.ndarray:
scripts/triarb.py:245:def _nan_metrics() -> dict[str, float]:
scripts/triarb.py:257:def compute_pair_metrics(
scripts/triarb.py:291:def compute_pair_correlation(
scripts/triarb.py:311:def htf_strong_trend(df_htf: pd.DataFrame | None) -> str:
scripts/triarb.py:312:    if df_htf is None or len(df_htf) < HTF_MIN_BARS:
scripts/triarb.py:324:    if spread > HTF_STRONG_TREND_THRESHOLD:
scripts/triarb.py:326:    if spread < -HTF_STRONG_TREND_THRESHOLD:
scripts/triarb.py:334:def check_short_ratio_entry(
scripts/triarb.py:358:def check_long_ratio_entry(
scripts/triarb.py:386:class ContextVector:
scripts/triarb.py:394:    def to_array(self) -> np.ndarray:
scripts/triarb.py:409:class TradeRecord:
scripts/triarb.py:423:class ContextMemory:
scripts/triarb.py:424:    def __init__(self, variant_name: str):
scripts/triarb.py:425:        self.variant_name = variant_name
scripts/triarb.py:428:    def add(self, record: TradeRecord):
scripts/triarb.py:431:    def _distance(self, a: np.ndarray, b: np.ndarray) -> float:
scripts/triarb.py:436:    def _neighbors(self, ctx: ContextVector, direction: str, k: int) -> list[TradeRecord]:
scripts/triarb.py:445:    def query_ev(self, ctx: ContextVector, direction: str) -> tuple[float, int]:
scripts/triarb.py:451:    def is_blacklisted(self, ctx: ContextVector, direction: str) -> bool:
scripts/triarb.py:460:    def size_multiplier(self, ctx: ContextVector, direction: str, total_trades: int) -> float:
scripts/triarb.py:479:    def snapshot(self) -> dict[str, Any]:
scripts/triarb.py:487:                "blacklisted_clusters": 0,
scripts/triarb.py:504:            if self.is_blacklisted(ctx, rec.direction):
scripts/triarb.py:512:            "blacklisted_clusters": bl_count,
scripts/triarb.py:520:class PairPosition:
scripts/triarb.py:537:class VariantPM:
scripts/triarb.py:538:    def __init__(self, variant_name: str, config: dict[str, Any]):
scripts/triarb.py:539:        self.name = variant_name
scripts/triarb.py:547:        self.memory = ContextMemory(variant_name)
scripts/triarb.py:560:    def balance(self) -> float:
scripts/triarb.py:564:    def peak_balance(self) -> float:
scripts/triarb.py:568:    def trade_count(self) -> int:
scripts/triarb.py:572:    def win_count(self) -> int:
scripts/triarb.py:575:    def try_open(
scripts/triarb.py:591:        if self.config.get("memory", False) and self.memory.is_blacklisted(ctx, direction):
scripts/triarb.py:593:            return "memory_blacklist"
scripts/triarb.py:621:    def check_exits(
scripts/triarb.py:651:    def _close(
scripts/triarb.py:722:    def total_return(self) -> float:
scripts/triarb.py:725:    def drawdown(self) -> float:
scripts/triarb.py:730:    def win_rate(self) -> float:
scripts/triarb.py:735:    def position_snapshots(self) -> list[dict[str, Any]]:
scripts/triarb.py:764:class TriArbEngine:
scripts/triarb.py:765:    def __init__(self, port: int = DASH_PORT):
scripts/triarb.py:780:        self.variants = {name: VariantPM(name, cfg) for name, cfg in VARIANTS_CONFIG.items()}
scripts/triarb.py:797:    def _fetch_history(
scripts/triarb.py:810:    def init(self):
scripts/triarb.py:816:        print(f"[TriArb] Exec TFs: {', '.join(self.exec_timeframes)} | HTF: {HTF_TIMEFRAME} (BTC)")
scripts/triarb.py:821:        print(f"[TriArb] Memory warmup: {MEMORY_WARMUP_TRADES} trades | {len(self.variants)} variants")
scripts/triarb.py:833:        self.history_htf = self._fetch_history("BTC/USDT:USDT", HTF_TIMEFRAME, HISTORY_BARS)
scripts/triarb.py:851:    def _aligned_pair_closes(
scripts/triarb.py:867:    def _update_pair_metrics(self, pair_id: str, tf: str) -> Any:
scripts/triarb.py:883:    def _build_context(
scripts/triarb.py:927:    def _record_entry_block(self, pm: VariantPM, reason_s: str, reason_l: str):
scripts/triarb.py:939:    def _process_variant_on_bar(self, variant_name: str, pair_id: str):
scripts/triarb.py:940:        pm = self.variants[variant_name]
scripts/triarb.py:993:                    f"  [{variant_name} {pair_id}] SHORT_RATIO z={metrics['z']:.2f} "
scripts/triarb.py:1018:                    f"  [{variant_name} {pair_id}] LONG_RATIO z={metrics['z']:.2f} "
scripts/triarb.py:1027:    def tick(self):
scripts/triarb.py:1030:        if self.tick_count % HTF_REFRESH_TICKS == 0:
scripts/triarb.py:1031:            new_htf = self._fetch_history("BTC/USDT:USDT", HTF_TIMEFRAME, 5)
scripts/triarb.py:1068:                        self._process_variant_on_bar(name, pair_id)
scripts/triarb.py:1076:    def _log_tick(self):
scripts/triarb.py:1083:        variant_parts = [
scripts/triarb.py:1085:            for name, pm in self.variants.items()
scripts/triarb.py:1088:        print(f"  [tick {self.tick_count}] " + " | ".join(variant_parts))
scripts/triarb.py:1102:            "variants": {
scripts/triarb.py:1113:                for name, pm in self.variants.items()
scripts/triarb.py:1119:    def snapshot(self) -> dict[str, Any]:
scripts/triarb.py:1120:        variants_data = {}
scripts/triarb.py:1121:        for name, pm in self.variants.items():
scripts/triarb.py:1122:            variants_data[name] = {
scripts/triarb.py:1181:            "htf_timeframe": HTF_TIMEFRAME,
scripts/triarb.py:1189:            "variants": variants_data,
scripts/triarb.py:1190:            "variant_configs": {name: pm.config for name, pm in self.variants.items()},
scripts/triarb.py:1191:            "memory_warmup": MEMORY_WARMUP_TRADES,
scripts/triarb.py:1195:    def _save_state(self):
scripts/triarb.py:1214:            for name, pm in self.variants.items():
scripts/triarb.py:1221:            for name, pm in self.variants.items():
scripts/triarb.py:1231:    def _load_state(self):
scripts/triarb.py:1251:            for name, pm in self.variants.items():
scripts/triarb.py:1261:                for name, pm in self.variants.items():
scripts/triarb.py:1270:            print(f"  [load] TriArb tick={self.tick_count} variants restored")
scripts/triarb.py:1274:    def run(self):
scripts/triarb.py:1299:class DashboardHandler(http.server.BaseHTTPRequestHandler):
scripts/triarb.py:1302:    def log_message(self, *a):
scripts/triarb.py:1305:    def do_GET(self):
scripts/triarb.py:1322:def main():
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
scripts/dashboard_unified.py:33:def fetch_model_state(port: int) -> dict | None:
scripts/dashboard_unified.py:45:class Handler(http.server.BaseHTTPRequestHandler):
scripts/dashboard_unified.py:46:    def log_message(self, *a):
scripts/dashboard_unified.py:49:    def do_GET(self):
scripts/dashboard_unified.py:57:    def _serve_html(self):
scripts/dashboard_unified.py:65:    def _serve_api(self):
scripts/dashboard_unified.py:68:        # /api/v2 — proxy to 8897
scripts/dashboard_unified.py:73:            for model_id, info in MODELS.items():
scripts/dashboard_unified.py:82:        elif key in MODELS:
scripts/dashboard_unified.py:83:            state = fetch_model_state(MODELS[key]["port"])
scripts/dashboard_unified.py:297:  const ent=s.entropy||1;
scripts/dashboard_unified.py:367:  const variants=s.variants||{};
scripts/dashboard_unified.py:368:  const warmup=s.memory_warmup||30;
scripts/dashboard_unified.py:371:  // Header summary: best variant + total trades
scripts/dashboard_unified.py:373:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:382:  let html='<div class="model-section"><div class="model-hdr" style="border-left:3px solid '+color+'"><h2><span class="'+(online?'live':'live offline')+'"></span> '+d.name+' <span style="font-size:10px;color:#aa66ff;margin-left:6px">VWAP/EMA9/VP + Context k-NN + '+htfTF+' HTF Bias | 수수료 0.21% RT | Risk 0.5%/trade</span></h2><div class="stats">';
scripts/dashboard_unified.py:385:  html+='<span class="dim" style="font-size:10px">실행 TF: '+execTFs+' / HTF: '+htfTF+'</span>';
scripts/dashboard_unified.py:386:  html+='<span class="dim" style="font-size:10px">메모리: '+warmup+'거래 후 활성 → '+fullAct+'거래에 100%</span>';
scripts/dashboard_unified.py:389:  // HTF bias strip — per-asset 1h directional context
scripts/dashboard_unified.py:391:    html+='<div style="margin-bottom:10px"><div style="font-size:10px;color:#555;margin-bottom:3px;text-transform:uppercase">'+htfTF+' HTF 바이어스 (EMA20/50 — neutral 시 진입 차단)</div>';
scripts/dashboard_unified.py:401:  // Variants grid — one card per variant
scripts/dashboard_unified.py:402:  html+='<div style="display:grid;grid-template-columns:repeat('+Object.keys(variants).length+',1fr);gap:8px;margin-bottom:12px">';
scripts/dashboard_unified.py:403:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:409:    const bl=mem.blacklisted_clusters||0;
scripts/dashboard_unified.py:416:    html+='<div style="font-size:9px;color:#555;margin-top:3px">RR≥'+cfg.rr_min+' | TF '+cfg.timeframe+(cfg.htf_filter?'':' <span style="color:#f44">|HTF OFF</span>')+'</div>';
scripts/dashboard_unified.py:424:  html+='<div style="margin-top:8px"><div style="font-size:10px;color:#555;margin-bottom:3px;text-transform:uppercase">신호 필터링 깔때기 (각 variant 누적)</div>';
scripts/dashboard_unified.py:425:  html+='<table class="dtbl"><tr><th>Variant</th><th>검토</th><th>HTF 차단</th><th>CHOP 차단</th><th>RR 차단</th><th>메모리 차단</th><th>실행</th><th>실행률</th></tr>';
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
scripts/dashboard_unified.py:526:  html+='<span class="dim" style="font-size:10px">실행 TF: '+execTFs+' / HTF: '+htf+'</span>';
scripts/dashboard_unified.py:527:  html+='<span class="dim" style="font-size:10px">메모리: '+warmup+' → '+fullAct+' trades</span>';
scripts/dashboard_unified.py:545:  html+='<div style="display:grid;grid-template-columns:repeat('+Math.max(1,Object.keys(variants).length)+',1fr);gap:8px;margin-bottom:12px">';
scripts/dashboard_unified.py:546:  for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:555:    html+='<div style="font-size:9px;color:#555;margin-top:3px">z≥'+cfg.entry_z+' | target '+cfg.exit_target_z+' | TF '+cfg.timeframe+(cfg.htf_filter?' | HTF':'')+'</div>';
scripts/dashboard_unified.py:557:    html+='<div style="font-size:9px;color:#666;margin-top:3px">mem: <span class="cyn">'+(mem.n_trades||0)+'</span> 블랙: <span class="'+((mem.blacklisted_clusters||0)>0?'red':'dim')+'">'+(mem.blacklisted_clusters||0)+'</span></div>';
scripts/dashboard_unified.py:563:  html+='<table class="dtbl"><tr><th>Variant</th><th>검토</th><th>상관차단</th><th>속도차단</th><th>CV차단</th><th>HTF차단</th><th>메모리차단</th><th>실행</th><th>실행률</th></tr>';
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
scripts/dashboard_unified.py:659:    // Draw V3 per-variant PnL charts
scripts/dashboard_unified.py:662:      const variants=v3d.state.variants||{};
scripts/dashboard_unified.py:663:      for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:670:    // Draw TriArb per-variant PnL charts
scripts/dashboard_unified.py:673:      const variants=td.state.variants||{};
scripts/dashboard_unified.py:674:      for(const[vn,v]of Object.entries(variants)){
scripts/dashboard_unified.py:690:def main():
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
scripts/v3.py:79:HTF_TIMEFRAME = "1h"
scripts/v3.py:80:HTF_MIN_BARS = 60          # need enough bars for EMA50
scripts/v3.py:81:HTF_REFRESH_TICKS = 15     # refresh 1h bias every 15 minutes (tick = 60s)
scripts/v3.py:84:# Execution TFs expanded per WebSearch findings: 3m/5m/15m/30m + 5m param variants.
scripts/v3.py:100:class IndicatorEngine:
scripts/v3.py:104:    def session_vwap(df: pd.DataFrame) -> np.ndarray:
scripts/v3.py:119:    def ema(values: np.ndarray, period: int) -> np.ndarray:
scripts/v3.py:124:    def atr(df: pd.DataFrame, period: int = 14) -> np.ndarray:
scripts/v3.py:139:    def volume_profile(df: pd.DataFrame, lookback: int = 120, nbins: int = 30) -> tuple[np.ndarray, np.ndarray]:
scripts/v3.py:165:    def hvn_indices(volumes: np.ndarray, percentile: float = 70.0) -> np.ndarray:
scripts/v3.py:173:def htf_bias(df_htf: pd.DataFrame) -> str:
scripts/v3.py:181:    if df_htf is None or len(df_htf) < HTF_MIN_BARS:
scripts/v3.py:200:class MarketSnapshot:
scripts/v3.py:213:def classify_state(df: pd.DataFrame, snap: MarketSnapshot, chop_strict: float) -> str:
scripts/v3.py:268:def long_pullback_valid(df: pd.DataFrame, snap: MarketSnapshot) -> tuple[bool, float]:
scripts/v3.py:303:def short_pullback_valid(df: pd.DataFrame, snap: MarketSnapshot) -> tuple[bool, float]:
scripts/v3.py:336:def vp_clearance(df: pd.DataFrame, entry: float, direction: str, atr_val: float,
scripts/v3.py:376:class ContextVector:
scripts/v3.py:384:    def to_array(self) -> np.ndarray:
scripts/v3.py:392:class TradeRecord:
scripts/v3.py:403:class ContextMemory:
scripts/v3.py:404:    """Stores past trades and scores new contexts via k-NN EV.
scripts/v3.py:407:      - Bad contexts (EV < threshold with enough samples) → blacklist
scripts/v3.py:411:    def __init__(self, variant_name: str):
scripts/v3.py:412:        self.variant_name = variant_name
scripts/v3.py:414:        self._blacklist_cache: set[int] | None = None  # hash-based
scripts/v3.py:416:    def add(self, record: TradeRecord):
scripts/v3.py:418:        self._blacklist_cache = None  # invalidate
scripts/v3.py:420:    def _distance(self, a: np.ndarray, b: np.ndarray) -> float:
scripts/v3.py:427:    def _neighbors(self, ctx: ContextVector, direction: str, k: int) -> list[TradeRecord]:
scripts/v3.py:439:    def query_ev(self, ctx: ContextVector, direction: str) -> tuple[float, int]:
scripts/v3.py:447:    def is_blacklisted(self, ctx: ContextVector, direction: str) -> bool:
scripts/v3.py:455:    def size_multiplier(self, ctx: ContextVector, direction: str, total_trades: int) -> float:
scripts/v3.py:459:        Gradual activation between warmup and full-activation.
scripts/v3.py:480:            # Soft penalty before blacklist threshold
scripts/v3.py:485:    def snapshot(self) -> dict:
scripts/v3.py:493:                "blacklisted_clusters": 0,
scripts/v3.py:499:        # Rough blacklist count: sample centers of each record and test
scripts/v3.py:501:        # Sample-based: count how many past contexts ARE currently blacklisted
scripts/v3.py:508:            if self.is_blacklisted(ctx, r.direction):
scripts/v3.py:516:            "blacklisted_clusters": bl_count,
scripts/v3.py:521:# Position + Position Manager (per-variant)
scripts/v3.py:524:class V3Position:
scripts/v3.py:538:class VariantPM:
scripts/v3.py:539:    """Position manager per variant."""
scripts/v3.py:541:    def __init__(self, variant_name: str, config: dict):
scripts/v3.py:542:        self.name = variant_name
scripts/v3.py:550:        self.memory = ContextMemory(variant_name)
scripts/v3.py:558:    def try_open(self, asset: str, direction: str, entry: float, hard_stop: float,
scripts/v3.py:564:        # Memory blacklist check (only if memory enabled)
scripts/v3.py:565:        if self.config["memory"] and self.memory.is_blacklisted(ctx, direction):
scripts/v3.py:567:            return "memory_blacklist"
scripts/v3.py:605:    def check_exits(self, asset: str, bar: dict, ema9_now: float, atr_now: float) -> str | None:
scripts/v3.py:641:    def _close(self, asset: str, exit_price: float, reason: str):
scripts/v3.py:688:    def total_return(self) -> float:
scripts/v3.py:691:    def drawdown(self) -> float:
scripts/v3.py:696:    def win_rate(self) -> float:
scripts/v3.py:704:# V3 Engine (main loop, manages all variants)
scripts/v3.py:706:class V3Engine:
scripts/v3.py:707:    def __init__(self, assets: list[str], port: int = DASH_PORT):
scripts/v3.py:711:        # Execution timeframes used by any variant (derived from config)
scripts/v3.py:715:        # HTF (1h) history for bias filter
scripts/v3.py:719:        self.variants: dict[str, VariantPM] = {
scripts/v3.py:727:    def _symbol(self, asset: str) -> str:
scripts/v3.py:730:    def _fetch_history(self, asset: str, timeframe: str = "5m",
scripts/v3.py:741:    def _compute_snapshot(self, df: pd.DataFrame) -> MarketSnapshot | None:
scripts/v3.py:784:    def _make_context(self, snap: MarketSnapshot, vp_distance: float, rr: float) -> ContextVector:
scripts/v3.py:794:    def _process_variant_on_bar(self, variant_name: str, asset: str,
scripts/v3.py:796:        """Evaluate entries+exits for one variant on a new bar.
scripts/v3.py:799:        If variant has htf_filter=True, neutral blocks all entries and
scripts/v3.py:800:        signals must match the HTF direction.
scripts/v3.py:802:        pm = self.variants[variant_name]
scripts/v3.py:816:        # 0. HTF bias filter (before any expensive computation)
scripts/v3.py:830:        # HTF direction match check
scripts/v3.py:885:            print(f"  [{variant_name} {asset}] {direction.upper()} @{entry_price:.2f} "
scripts/v3.py:889:    def init(self):
scripts/v3.py:891:              f"| {len(VARIANTS_CONFIG)} variants")
scripts/v3.py:892:        print(f"[V3] Exec TFs: {','.join(self.exec_timeframes)} | HTF bias: {HTF_TIMEFRAME}")
scripts/v3.py:894:        print(f"[V3] Memory warmup: {MEMORY_WARMUP_TRADES} trades")
scripts/v3.py:903:            # HTF (1h) load
scripts/v3.py:904:            df_htf = self._fetch_history(asset, HTF_TIMEFRAME, HISTORY_BARS)
scripts/v3.py:908:                sizes[HTF_TIMEFRAME] = len(df_htf)
scripts/v3.py:920:    def tick(self):
scripts/v3.py:923:        # --- HTF (1h) refresh every HTF_REFRESH_TICKS ---
scripts/v3.py:924:        if self.tick_count % HTF_REFRESH_TICKS == 0:
scripts/v3.py:928:                new_htf = self._fetch_history(asset, HTF_TIMEFRAME, 5)
scripts/v3.py:940:        # --- Execution TF refresh (each variant uses its own TF) ---
scripts/v3.py:955:                # New closed bar — append and fire variants
scripts/v3.py:969:                        self._process_variant_on_bar(
scripts/v3.py:979:    def _log_tick(self):
scripts/v3.py:983:            "variants": {},
scripts/v3.py:985:        for name, pm in self.variants.items():
scripts/v3.py:986:            log_entry["variants"][name] = {
scripts/v3.py:1003:        for name, pm in self.variants.items():
scripts/v3.py:1007:    def snapshot(self) -> dict:
scripts/v3.py:1008:        variants_data = {}
scripts/v3.py:1009:        for name, pm in self.variants.items():
scripts/v3.py:1011:            variants_data[name] = {
scripts/v3.py:1043:            "variants": variants_data,
scripts/v3.py:1045:            "variant_configs": VARIANTS_CONFIG,
scripts/v3.py:1046:            "memory_warmup": MEMORY_WARMUP_TRADES,
scripts/v3.py:1049:            "htf_timeframe": HTF_TIMEFRAME,
scripts/v3.py:1053:    def _save_state(self):
scripts/v3.py:1058:            for name, pm in self.variants.items():
scripts/v3.py:1066:            for name, pm in self.variants.items():
scripts/v3.py:1075:    def _load_state(self):
scripts/v3.py:1081:            for name, pm in self.variants.items():
scripts/v3.py:1096:                for name, pm in self.variants.items():
scripts/v3.py:1100:            print(f"  [load] tick={self.tick_count} variants restored")
scripts/v3.py:1104:    def run(self):
scripts/v3.py:1128:# Dashboard (API only — unified dashboard on 8900 renders UI)
scripts/v3.py:1130:class DashboardHandler(http.server.BaseHTTPRequestHandler):
scripts/v3.py:1133:    def log_message(self, *a):
scripts/v3.py:1136:    def do_GET(self):
scripts/v3.py:1153:def main():
scripts/v2.py:11:    py -3.12 scripts/v2.py [--assets ETH,BTC,SOL,XRP] [--port 8897]
scripts/v2.py:14:    http://localhost:8897
scripts/v2.py:46:STATE_PATH = DATA_DIR / "v2_state.npz"
scripts/v2.py:47:LOG_PATH = DATA_DIR / "v2.jsonl"
scripts/v2.py:48:DASH_PORT = 8897
scripts/v2.py:88:class EMANormalizer:
scripts/v2.py:91:    def __init__(self, n: int, alpha: float = 0.01):
scripts/v2.py:98:    def update(self, x: np.ndarray):
scripts/v2.py:105:    def normalize(self, x: np.ndarray) -> np.ndarray:
scripts/v2.py:108:    def is_warm(self) -> bool:
scripts/v2.py:115:class FeatureEngine:
scripts/v2.py:118:    def __init__(self):
scripts/v2.py:121:    def compute(self, df: pd.DataFrame, funding: float = 0.0) -> np.ndarray | None:
scripts/v2.py:207:    def _rsi_norm(self, c: np.ndarray, period: int) -> float:
scripts/v2.py:220:    def _macd_hist(self, c: np.ndarray) -> float:
scripts/v2.py:229:    def _atr(self, h, lo, c, period: int) -> float:
scripts/v2.py:243:# Rule 1+2: Online Predictor (per-asset, entropy memory balancing)
scripts/v2.py:245:class OnlinePredictor:
scripts/v2.py:246:    """SGD ridge with EMA normalization + entropy-based memory balancing.
scripts/v2.py:249:    Rule 2: Use memory evenly (adaptive L2 via feature importance entropy).
scripts/v2.py:252:    def __init__(self, n: int = N_FEATURES, lr: float = 0.003,
scripts/v2.py:267:        self.entropy_history: list[float] = []
scripts/v2.py:270:    def predict(self, x: np.ndarray) -> float:
scripts/v2.py:275:    def update(self, x_prev: np.ndarray, y_true: float):
scripts/v2.py:314:    def _rebalance_memory(self):
scripts/v2.py:315:        """Rule 2: Adaptive L2 + exploration noise to keep entropy high."""
scripts/v2.py:321:            self.entropy_history.append(1.0)
scripts/v2.py:329:        entropy = -np.sum(safe_p * np.log(safe_p))
scripts/v2.py:330:        max_entropy = np.log(self.n)
scripts/v2.py:331:        self.entropy_history.append(entropy / max_entropy)
scripts/v2.py:344:    def memory_entropy(self) -> float:
scripts/v2.py:345:        if not self.entropy_history:
scripts/v2.py:347:        return self.entropy_history[-1]
scripts/v2.py:349:    def direction_accuracy(self) -> float:
scripts/v2.py:354:    def calibration(self) -> float:
scripts/v2.py:355:        """Trust score [0, 1]. High accuracy + high entropy + enough data = high trust."""
scripts/v2.py:357:        ent = self.memory_entropy()
scripts/v2.py:358:        # FIX: entropy floor to prevent deadlock (low ent → no trade → no learn → ent stays low)
scripts/v2.py:361:        warmup = min(n_samples / 50, 1.0)
scripts/v2.py:362:        return acc * ent_factor * warmup
scripts/v2.py:369:class Position:
scripts/v2.py:379:class PositionManager:
scripts/v2.py:382:    def __init__(self, capital: float = INITIAL_CAPITAL):
scripts/v2.py:391:    def kelly_fraction(self) -> float:
scripts/v2.py:410:    def current_exposure(self) -> float:
scripts/v2.py:414:    def current_notional(self) -> float:
scripts/v2.py:418:    def open_position(self, asset: str, direction: str, price: float,
scripts/v2.py:438:    def close_position(self, asset: str, price: float) -> float | None:
scripts/v2.py:468:    def total_return(self) -> float:
scripts/v2.py:471:    def drawdown(self) -> float:
scripts/v2.py:480:class DashboardHandler(http.server.BaseHTTPRequestHandler):
scripts/v2.py:483:    def log_message(self, *a):
scripts/v2.py:486:    def do_GET(self):
scripts/v2.py:574:    q('#ent').textContent=fmt(d.entropy,1);
scripts/v2.py:575:    q('#ent').className='big '+(d.entropy>0.8?'grn':d.entropy>0.6?'ylw':'red');
scripts/v2.py:576:    q('#ent-d').textContent=d.entropy>0.8?'balanced':'rebalancing...';
scripts/v2.py:604:class V2Engine:
scripts/v2.py:605:    def __init__(self, assets: list[str], port: int = DASH_PORT):
scripts/v2.py:627:    def _symbol(self, asset: str) -> str:
scripts/v2.py:630:    def _fetch_funding(self, asset: str) -> float:
scripts/v2.py:638:    def _fetch_history(self, asset: str) -> pd.DataFrame | None:
scripts/v2.py:648:    def _fetch_latest(self, asset: str) -> dict | None:
scripts/v2.py:664:    def init(self):
scripts/v2.py:676:    def tick(self):
scripts/v2.py:752:                if cal > 0.05:  # minimum trust
scripts/v2.py:770:    def _log_tick(self):
scripts/v2.py:773:        ents = [p.memory_entropy() for p in self.predictors.values()]
scripts/v2.py:782:            "entropy": round(avg_ent, 4),
scripts/v2.py:796:    def snapshot(self) -> dict:
scripts/v2.py:798:        ents = [p.memory_entropy() for p in self.predictors.values()]
scripts/v2.py:816:            "entropy": float(np.mean(ents)) if ents else 1.0,
scripts/v2.py:841:    def _save_state(self):
scripts/v2.py:857:    def _load_state(self):
scripts/v2.py:877:    def run(self):
scripts/v2.py:898:def main():

 succeeded in 474ms:
.\data\discuss_rule2.md
.\data\discuss_prompt.md
.\data\_discuss_spec.json

 succeeded in 386ms:
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

 succeeded in 420ms:
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

 succeeded in 482ms:
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

 succeeded in 544ms:
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

codex
이제 판단 포인트를 좁혔습니다. V2의 실제 결함은 `entropy` 재균등화와 `calibration` 게이팅이 어떻게 묶였는지, V3/TriArb 재활용은 `ContextMemory`와 state schema가 어느 정도 공통인지 확인하면 충분합니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/v2.py | Select-Object -Skip 245 -First 170' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/v2.py | Select-Object -Skip 796 -First 90' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/v3.py | Select-Object -Skip 376 -First 170' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/v3.py | Select-Object -Skip 1000 -First 110' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/triarb.py | Select-Object -Skip 386 -First 150' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/triarb.py | Select-Object -Skip 1190 -First 95' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 411ms:
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
        self.norm = EMANormalizer(n)

        # Tracking
        self.predictions: list[float] = []
        self.actuals: list[float] = []
        self.accuracy_history: list[float] = []
        self.entropy_history: list[float] = []
        self.feature_importance = np.ones(n) / n

    def predict(self, x: np.ndarray) -> float:
        """Predict next-bar return."""
        x_n = self.norm.normalize(x)
        return float(np.dot(self.w, x_n) + self.b)

    def update(self, x_prev: np.ndarray, y_true: float):
        """Learn from previous features ??actual return. Proper t+1 labeling."""
        # Update normalizer with previous features
        self.norm.update(x_prev)
        x_n = self.norm.normalize(x_prev)

        y_pred = float(np.dot(self.w, x_n) + self.b)
        error = y_pred - y_true

        # SGD with per-feature L2
        grad_w = error * x_n + self.l2_per_feat * self.w
        grad_b = error

        # Gradient clipping (protect against outliers)
        grad_norm = np.linalg.norm(grad_w)
        if grad_norm > 1.0:
            grad_w = grad_w / grad_norm
        grad_b = np.clip(grad_b, -1.0, 1.0)  # clip bias gradient too

        self.w -= self.lr * grad_w
        self.b -= self.lr * grad_b

        # Track
        self.predictions.append(y_pred)
        self.actuals.append(y_true)

        # Rule 2: rebalance memory
        self._rebalance_memory()

        # Direction accuracy (rolling 50)
        if len(self.predictions) >= 10:
            recent_p = self.predictions[-50:]
            recent_a = self.actuals[-50:]
            correct = sum(
                1 for p, a in zip(recent_p, recent_a)
                if (p > 0) == (a > 0)
            )
            self.accuracy_history.append(correct / len(recent_p))

    def _rebalance_memory(self):
        """Rule 2: Adaptive L2 + exploration noise to keep entropy high."""
        # FIX: importance = |w| only (normalized model, sqrt(var) was wrong)
        imp = np.abs(self.w)
        imp_sum = imp.sum()
        if imp_sum < 1e-10:
            self.feature_importance = np.ones(self.n) / self.n
            self.entropy_history.append(1.0)
            return

        p = imp / imp_sum
        self.feature_importance = p

        # Entropy (NaN-safe)
        safe_p = np.clip(p, 1e-10, 1.0)
        entropy = -np.sum(safe_p * np.log(safe_p))
        max_entropy = np.log(self.n)
        self.entropy_history.append(entropy / max_entropy)

        # Adaptive L2: penalize overused features
        uniform = 1.0 / self.n
        excess = np.maximum(p - uniform, 0)
        self.l2_per_feat = self.base_l2 * (1.0 + self.memory_alpha * excess * self.n)

        # FIX: exploration noise for underused features (L2 only shrinks, can't grow)
        deficit = np.maximum(uniform - p, 0)
        if deficit.sum() > 0:
            noise_scale = self.lr * 0.1 * deficit * self.n
            self.w += np.random.randn(self.n) * noise_scale

    def memory_entropy(self) -> float:
        if not self.entropy_history:
            return 1.0
        return self.entropy_history[-1]

    def direction_accuracy(self) -> float:
        if not self.accuracy_history:
            return 0.5
        return self.accuracy_history[-1]

    def calibration(self) -> float:
        """Trust score [0, 1]. High accuracy + high entropy + enough data = high trust."""
        acc = self.direction_accuracy()
        ent = self.memory_entropy()
        # FIX: entropy floor to prevent deadlock (low ent ??no trade ??no learn ??ent stays low)
        ent_factor = max(ent, 0.3)
        n_samples = min(len(self.predictions), 200)
        warmup = min(n_samples / 50, 1.0)
        return acc * ent_factor * warmup


# ===================================================================
# Rule 3: Position Manager (cost-aware, Kelly-capped, exposure-capped)
# ===================================================================
@dataclass
class Position:
    direction: str
    entry_price: float
    size: float          # margin fraction (0~1)
    leverage: float      # 1~100x
    entry_time: str
    asset: str
    entry_prediction: float


class PositionManager:
    """Fractional Kelly sizing with costs. Maximum profit within safety bounds."""

    def __init__(self, capital: float = INITIAL_CAPITAL):
        self.capital = capital
        self.initial_capital = capital
        self.positions: dict[str, Position] = {}
        self.trade_returns: list[float] = []
        self.trade_log: list[dict] = []
        self.pnl_history: list[float] = [capital]
        self.peak_capital = capital

    def kelly_fraction(self) -> float:
        if len(self.trade_returns) < 30:
            return 0.05  # very conservative until enough data
        rets = np.array(self.trade_returns[-200:])
        wins = rets[rets > 0]
        losses = rets[rets < 0]
        if len(wins) == 0:
            return 0.02
        if len(losses) == 0:
            return 0.15
        win_rate = len(wins) / len(rets)
        avg_win = float(wins.mean())
        avg_loss = float(abs(losses.mean()))
        if avg_loss < 1e-10:
            return 0.15
        payoff = avg_win / avg_loss
        kelly = (win_rate * payoff - (1 - win_rate)) / payoff
        return float(np.clip(kelly, 0.01, KELLY_CAP))

    def current_exposure(self) -> float:
        """Total margin usage across all assets."""
        return sum(p.size for p in self.positions.values())

    def current_notional(self) -> float:
        """Total leveraged notional exposure."""

 succeeded in 442ms:
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

 succeeded in 498ms:
    vwap_slope: float           # normalized by ATR
    ema_dist_atr: float         # (close - ema9) / ATR
    vp_clearance_atr: float     # distance to first HVN / ATR
    rr_estimate: float
    session_hour_bucket: int    # 0..5 (6 buckets of 4h each)
    vol_regime: float           # atr14 / atr60

    def to_array(self) -> np.ndarray:
        return np.array([
            self.vwap_slope, self.ema_dist_atr, self.vp_clearance_atr,
            self.rr_estimate, float(self.session_hour_bucket), self.vol_regime,
        ])


@dataclass
class TradeRecord:
    context: list[float]        # ContextVector as array
    direction: str              # "long"/"short"
    entry_price: float
    exit_price: float
    r_multiple: float           # PnL in R units (hard stop distance)
    net_pct: float              # net return % after fees
    asset: str
    timestamp: str


class ContextMemory:
    """Stores past trades and scores new contexts via k-NN EV.

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
# ===================================================================
@dataclass
class V3Position:
    asset: str
    direction: str
    entry_price: float
    hard_stop: float
    soft_stop_ref: float        # EMA9 +/- buffer
    target_price: float         # first HVN
    size: float                 # margin fraction
    leverage: float
    entry_time: str
    entry_context: ContextVector
    r_distance: float           # abs(entry - hard_stop), in price


class VariantPM:
    """Position manager per variant."""

    def __init__(self, variant_name: str, config: dict):
        self.name = variant_name
        self.config = config
        self.capital = INITIAL_CAPITAL
        self.initial_capital = INITIAL_CAPITAL
        self.positions: dict[str, V3Position] = {}

 succeeded in 445ms:
    spread_zscore: float
    spread_velocity: float
    correlation_30d: float
    leg_vol_ratio: float
    session_hour_bucket: int
    vol_regime: float

    def to_array(self) -> np.ndarray:
        return np.array(
            [
                self.spread_zscore,
                self.spread_velocity,
                self.correlation_30d,
                self.leg_vol_ratio,
                float(self.session_hour_bucket),
                self.vol_regime,
            ],
            dtype=float,
        )


@dataclass
class TradeRecord:
    context: list[float]
    direction: str
    entry_price: float
    exit_price: float
    r_multiple: float
    net_pct: float
    asset: str
    timestamp: str
    pair_id: str
    entry_ratio: float
    exit_ratio: float


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
    entry_time: str
    entry_bar_idx: int
    entry_context: ContextVector
    entry_capital: float



 succeeded in 499ms:
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

 succeeded in 544ms:
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

exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/v2.py | Select-Object -Skip 664 -First 125' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'rg -n "oracle|feedback_self_learning_algorithm|rule2|entropy" docs data scripts tests' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content data/discuss_rule2.md -TotalCount 220' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 346ms:
docs\triarb_review_request_260420.md:138:- 기존 `tournament`, `v2`, `v3` 키는 유지됨. architecture 문서의 rename 목표(`bollrev`, `oracle`, `brooks`)와 현재 repo 상태가 다르므로, 여기서는 기존 대시보드 호환성을 우선함.
docs\triarb_260420.md:246:1. **절대** `scripts/brooks.py`, `scripts/bollrev.py`(존재 시), `scripts/oracle.py`를 수정하지 마라. 읽기만 허용. 구조 템플릿으로 사용.
docs\triarb_260420.md:792:    {"id": "oracle",  "name": "Oracle (LSTM Prediction)",     "port": 8897, "color": "#44aaff"},
scripts\dl_breakthrough_strategy.md:198:        bce = F.binary_cross_entropy_with_logits(logits, targets_smooth, reduction='none')
docs\models_architecture_260420.md:44:| `scripts/v2.py` | `scripts/oracle.py` | 8897 | 리네임만 |
docs\models_architecture_260420.md:63:├── oracle.jsonl            # (기존 v2 파일 리네임: v2.jsonl → oracle.jsonl)
docs\models_architecture_260420.md:64:├── oracle_state.npz        # (v2_state.npz → oracle_state.npz)
docs\models_architecture_260420.md:210:    {"id": "oracle",  "name": "Oracle (LSTM Prediction)",     "port": 8897, "color": "#44aaff"},
docs\models_architecture_260420.md:245:start /min "" py -3.12 -u scripts\oracle.py
docs\models_architecture_260420.md:266:1. `v2.py` → `oracle.py` (Engine 클래스명 `V2Engine` → `OracleEngine`)
docs\models_architecture_260420.md:269:4. data 파일 리네임 (`v2_state.npz` → `oracle_state.npz` 등)
docs\bollrev_260420.md:568:    {"id": "oracle",  "name": "Oracle (LSTM Prediction)",     "port": 8897, "color": "#44aaff"},
scripts\dashboard_unified.py:297:  const ent=s.entropy||1;
data\discuss_rule2.md:33:    """Rule 2: Adaptive L2 to keep feature importance entropy high."""
data\discuss_rule2.md:38:        self.entropy_history.append(1.0)
data\discuss_rule2.md:46:    entropy = -np.sum(safe_p * np.log(safe_p))
data\discuss_rule2.md:47:    max_entropy = np.log(self.n)  # log(28) ≈ 3.33
data\discuss_rule2.md:48:    self.entropy_history.append(entropy / max_entropy)  # 0~1 정규화
data\discuss_rule2.md:61:    ent = self.memory_entropy()       # 엔트로피 0~1
data\discuss_prompt.md:36:entropy = -sum(p * log(p))
data\discuss_prompt.md:53:# calibration = accuracy * entropy * sample_factor
scripts\train_6m.py:127:    """Combined callback: entropy cycling, checkpoints, validation gate, NaN safety.
scripts\train_6m.py:130:    - Raised entropy floor (0.012 base)
scripts\train_6m.py:313:    # Callback with raised entropy floor
scripts\v2.py:243:# Rule 1+2: Online Predictor (per-asset, entropy memory balancing)
scripts\v2.py:246:    """SGD ridge with EMA normalization + entropy-based memory balancing.
scripts\v2.py:249:    Rule 2: Use memory evenly (adaptive L2 via feature importance entropy).
scripts\v2.py:267:        self.entropy_history: list[float] = []
scripts\v2.py:315:        """Rule 2: Adaptive L2 + exploration noise to keep entropy high."""
scripts\v2.py:321:            self.entropy_history.append(1.0)
scripts\v2.py:329:        entropy = -np.sum(safe_p * np.log(safe_p))
scripts\v2.py:330:        max_entropy = np.log(self.n)
scripts\v2.py:331:        self.entropy_history.append(entropy / max_entropy)
scripts\v2.py:344:    def memory_entropy(self) -> float:
scripts\v2.py:345:        if not self.entropy_history:
scripts\v2.py:347:        return self.entropy_history[-1]
scripts\v2.py:355:        """Trust score [0, 1]. High accuracy + high entropy + enough data = high trust."""
scripts\v2.py:357:        ent = self.memory_entropy()
scripts\v2.py:358:        # FIX: entropy floor to prevent deadlock (low ent → no trade → no learn → ent stays low)
scripts\v2.py:574:    q('#ent').textContent=fmt(d.entropy,1);
scripts\v2.py:575:    q('#ent').className='big '+(d.entropy>0.8?'grn':d.entropy>0.6?'ylw':'red');
scripts\v2.py:576:    q('#ent-d').textContent=d.entropy>0.8?'balanced':'rebalancing...';
scripts\v2.py:773:        ents = [p.memory_entropy() for p in self.predictors.values()]
scripts\v2.py:782:            "entropy": round(avg_ent, 4),
scripts\v2.py:798:        ents = [p.memory_entropy() for p in self.predictors.values()]
scripts\v2.py:816:            "entropy": float(np.mean(ents)) if ents else 1.0,
scripts\_analyze_results.py:25:print(f'[V2] 최종 상태: tick={last["tick"]} acc={last["acc"]:.3f} entropy={last["entropy"]:.3f} ret={last["ret"]*100:+.2f}% capital={last["capital"]:.0f} trades={last["trades"]}')
scripts\_analyze_results.py:40:    print(f'  tick {r["tick"]:5d} | acc {r["acc"]:.3f} | ent {r["entropy"]:.3f} | ret {r["ret"]*100:+7.2f}% | trades {r["trades"]:5d}')
data\v2.jsonl:1:{"tick": 5, "t": "05:07:04", "acc": 0.5, "entropy": 0.9672, "ret": 0.0, "capital": 10000.0, "trades": 0, "positions": 0, "exposure": 0, "predictions": 16}
data\v2.jsonl:2:{"tick": 10, "t": "05:12:06", "acc": 0.5, "entropy": 0.9738, "ret": 0.0, "capital": 10000.0, "trades": 0, "positions": 0, "exposure": 0, "predictions": 36}
data\v2.jsonl:3:{"tick": 15, "t": "05:17:08", "acc": 0.4821, "entropy": 0.9894, "ret": 0.0, "capital": 10000.0, "trades": 0, "positions": 0, "exposure": 0, "predictions": 56}
data\v2.jsonl:4:{"tick": 5, "t": "05:52:58", "acc": 0.5, "entropy": 0.9457, "ret": 0.0, "capital": 10000.0, "trades": 0, "positions": 0, "exposure": 0, "predictions": 16}
data\v2.jsonl:5:{"tick": 10, "t": "05:58:00", "acc": 0.5, "entropy": 0.972, "ret": 0.0, "capital": 10000.0, "trades": 0, "positions": 0, "exposure": 0, "predictions": 36}
data\v2.jsonl:6:{"tick": 15, "t": "06:03:02", "acc": 0.5357, "entropy": 0.9828, "ret": 0.0, "capital": 10000.0, "trades": 0, "positions": 0, "exposure": 0, "predictions": 56}
data\v2.jsonl:7:{"tick": 20, "t": "06:08:04", "acc": 0.5789, "entropy": 0.9857, "ret": 0.0, "capital": 10000.0, "trades": 0, "positions": 0, "exposure": 0, "predictions": 76}
data\v2.jsonl:8:{"tick": 25, "t": "06:13:06", "acc": 0.5625, "entropy": 0.9824, "ret": 0.0, "capital": 10000.0, "trades": 0, "positions": 0, "exposure": 0, "predictions": 96}
data\v2.jsonl:9:{"tick": 30, "t": "06:18:08", "acc": 0.5431, "entropy": 0.9893, "ret": 0.0, "capital": 10000.0, "trades": 0, "positions": 0, "exposure": 0, "predictions": 116}
data\v2.jsonl:10:{"tick": 35, "t": "06:23:11", "acc": 0.5441, "entropy": 0.9906, "ret": 0.0, "capital": 10000.0, "trades": 0, "positions": 0, "exposure": 0, "predictions": 136}
data\v2.jsonl:11:{"tick": 40, "t": "06:28:13", "acc": 0.5192, "entropy": 0.9883, "ret": 0.0, "capital": 10000.0, "trades": 0, "positions": 0, "exposure": 0, "predictions": 156}
data\v2.jsonl:12:{"tick": 45, "t": "06:33:15", "acc": 0.5091, "entropy": 0.9917, "ret": 0.0, "capital": 10000.0, "trades": 0, "positions": 0, "exposure": 0, "predictions": 175}
data\v2.jsonl:13:{"tick": 50, "t": "06:38:17", "acc": 0.5133, "entropy": 0.9927, "ret": 0.0, "capital": 10000.0, "trades": 0, "positions": 0, "exposure": 0, "predictions": 195}
data\v2.jsonl:14:{"tick": 55, "t": "06:43:19", "acc": 0.5, "entropy": 0.9939, "ret": 4e-05, "capital": 10000.4, "trades": 2, "positions": 1, "exposure": 0.01, "predictions": 215}
data\v2.jsonl:15:{"tick": 60, "t": "06:48:21", "acc": 0.5, "entropy": 0.9904, "ret": -4.7e-05, "capital": 9999.53, "trades": 3, "positions": 2, "exposure": 0.0211, "predictions": 235}
data\v2.jsonl:16:{"tick": 65, "t": "06:53:23", "acc": 0.495, "entropy": 0.9896, "ret": -2.5e-05, "capital": 9999.75, "trades": 5, "positions": 1, "exposure": 0.0104, "predictions": 255}
data\v2.jsonl:17:{"tick": 70, "t": "06:58:25", "acc": 0.475, "entropy": 0.9931, "ret": -0.000534, "capital": 9994.66, "trades": 7, "positions": 3, "exposure": 0.0351, "predictions": 275}
data\v2.jsonl:18:{"tick": 75, "t": "07:03:27", "acc": 0.48, "entropy": 0.9928, "ret": -0.000802, "capital": 9991.98, "trades": 10, "positions": 1, "exposure": 0.0239, "predictions": 295}
data\v2.jsonl:19:{"tick": 80, "t": "07:08:30", "acc": 0.485, "entropy": 0.9915, "ret": -0.001537, "capital": 9984.63, "trades": 12, "positions": 2, "exposure": 0.0372, "predictions": 315}
data\v2.jsonl:20:{"tick": 85, "t": "07:13:32", "acc": 0.5, "entropy": 0.9878, "ret": -0.003374, "capital": 9966.26, "trades": 16, "positions": 1, "exposure": 0.0115, "predictions": 335}
data\v2.jsonl:21:{"tick": 90, "t": "07:18:33", "acc": 0.5, "entropy": 0.9921, "ret": -0.003342, "capital": 9966.58, "trades": 18, "positions": 0, "exposure": 0, "predictions": 355}
data\v2.jsonl:22:{"tick": 95, "t": "07:23:36", "acc": 0.5, "entropy": 0.9864, "ret": -0.003342, "capital": 9966.58, "trades": 18, "positions": 1, "exposure": 0.0149, "predictions": 375}
data\v2.jsonl:23:{"tick": 100, "t": "07:28:38", "acc": 0.495, "entropy": 0.9919, "ret": -0.002013, "capital": 9979.87, "trades": 19, "positions": 2, "exposure": 0.02, "predictions": 395}
data\v2.jsonl:24:{"tick": 105, "t": "07:33:40", "acc": 0.495, "entropy": 0.9944, "ret": -0.001566, "capital": 9984.34, "trades": 21, "positions": 0, "exposure": 0, "predictions": 415}
data\v2.jsonl:25:{"tick": 110, "t": "07:38:42", "acc": 0.485, "entropy": 0.9957, "ret": -0.001683, "capital": 9983.17, "trades": 23, "positions": 1, "exposure": 0.0103, "predictions": 435}
data\v2.jsonl:26:{"tick": 115, "t": "07:43:44", "acc": 0.47, "entropy": 0.9942, "ret": -0.001683, "capital": 9983.17, "trades": 23, "positions": 1, "exposure": 0.0103, "predictions": 455}
data\v2.jsonl:27:{"tick": 120, "t": "07:48:47", "acc": 0.465, "entropy": 0.9944, "ret": -0.002096, "capital": 9979.04, "trades": 25, "positions": 0, "exposure": 0, "predictions": 475}
data\v2.jsonl:28:{"tick": 125, "t": "07:53:49", "acc": 0.445, "entropy": 0.9942, "ret": -0.002096, "capital": 9979.04, "trades": 25, "positions": 0, "exposure": 0, "predictions": 495}
data\v2.jsonl:29:{"tick": 130, "t": "07:58:51", "acc": 0.425, "entropy": 0.9966, "ret": -0.002096, "capital": 9979.04, "trades": 25, "positions": 0, "exposure": 0, "predictions": 515}
data\v2.jsonl:30:{"tick": 135, "t": "08:04:11", "acc": 0.43, "entropy": 0.997, "ret": -0.002096, "capital": 9979.04, "trades": 25, "positions": 1, "exposure": 0.01, "predictions": 535}
data\v2.jsonl:31:{"tick": 140, "t": "08:09:13", "acc": 0.425, "entropy": 0.9987, "ret": -0.002121, "capital": 9978.79, "trades": 27, "positions": 0, "exposure": 0, "predictions": 555}
data\v2.jsonl:32:{"tick": 145, "t": "08:14:16", "acc": 0.43, "entropy": 0.9956, "ret": -0.002151, "capital": 9978.49, "trades": 28, "positions": 0, "exposure": 0, "predictions": 575}
data\v2.jsonl:33:{"tick": 150, "t": "08:19:18", "acc": 0.41, "entropy": 0.9973, "ret": -0.002151, "capital": 9978.49, "trades": 28, "positions": 0, "exposure": 0, "predictions": 594}
data\v2.jsonl:34:{"tick": 155, "t": "08:24:22", "acc": 0.41, "entropy": 0.9958, "ret": -0.002151, "capital": 9978.49, "trades": 28, "positions": 2, "exposure": 0.02, "predictions": 614}
data\v2.jsonl:35:{"tick": 160, "t": "08:29:24", "acc": 0.425, "entropy": 0.999, "ret": -0.002225, "capital": 9977.75, "trades": 30, "positions": 1, "exposure": 0.01, "predictions": 634}
data\v2.jsonl:36:{"tick": 165, "t": "08:34:26", "acc": 0.415, "entropy": 0.999, "ret": -0.002594, "capital": 9974.06, "trades": 31, "positions": 2, "exposure": 0.02, "predictions": 654}
data\v2.jsonl:37:{"tick": 170, "t": "08:39:28", "acc": 0.44, "entropy": 0.9952, "ret": -0.002896, "capital": 9971.04, "trades": 34, "positions": 0, "exposure": 0, "predictions": 674}
data\v2.jsonl:38:{"tick": 175, "t": "08:44:30", "acc": 0.44, "entropy": 0.9955, "ret": -0.002968, "capital": 9970.32, "trades": 35, "positions": 0, "exposure": 0, "predictions": 694}
data\v2.jsonl:39:{"tick": 180, "t": "08:49:33", "acc": 0.44, "entropy": 0.9957, "ret": -0.002968, "capital": 9970.32, "trades": 35, "positions": 0, "exposure": 0, "predictions": 714}
data\v2.jsonl:40:{"tick": 185, "t": "08:54:35", "acc": 0.425, "entropy": 0.9962, "ret": -0.003137, "capital": 9968.63, "trades": 36, "positions": 1, "exposure": 0.01, "predictions": 734}
data\v2.jsonl:41:{"tick": 190, "t": "08:59:37", "acc": 0.445, "entropy": 0.9973, "ret": -0.003138, "capital": 9968.62, "trades": 37, "positions": 2, "exposure": 0.02, "predictions": 754}
data\v2.jsonl:42:{"tick": 195, "t": "09:04:39", "acc": 0.415, "entropy": 0.998, "ret": -0.003081, "capital": 9969.19, "trades": 40, "positions": 1, "exposure": 0.01, "predictions": 774}
data\v2.jsonl:43:{"tick": 200, "t": "09:09:41", "acc": 0.425, "entropy": 0.9951, "ret": -0.003145, "capital": 9968.55, "trades": 42, "positions": 0, "exposure": 0, "predictions": 794}
data\v2.jsonl:44:{"tick": 205, "t": "09:14:43", "acc": 0.43, "entropy": 0.9977, "ret": -0.003335, "capital": 9966.65, "trades": 44, "positions": 0, "exposure": 0, "predictions": 814}
data\v2.jsonl:45:{"tick": 210, "t": "09:19:45", "acc": 0.425, "entropy": 0.9953, "ret": -0.003335, "capital": 9966.65, "trades": 44, "positions": 0, "exposure": 0, "predictions": 834}
data\v2.jsonl:46:{"tick": 215, "t": "09:24:47", "acc": 0.44, "entropy": 0.9962, "ret": -0.003335, "capital": 9966.65, "trades": 44, "positions": 2, "exposure": 0.02, "predictions": 854}
data\v2.jsonl:47:{"tick": 220, "t": "09:29:49", "acc": 0.42, "entropy": 0.9935, "ret": -0.003498, "capital": 9965.02, "trades": 47, "positions": 1, "exposure": 0.01, "predictions": 874}
data\v2.jsonl:48:{"tick": 225, "t": "09:35:05", "acc": 0.43, "entropy": 0.9923, "ret": -0.003584, "capital": 9964.16, "trades": 49, "positions": 0, "exposure": 0, "predictions": 894}
data\v2.jsonl:49:{"tick": 230, "t": "09:40:07", "acc": 0.415, "entropy": 0.9947, "ret": -0.003584, "capital": 9964.16, "trades": 49, "positions": 2, "exposure": 0.02, "predictions": 914}
data\v2.jsonl:50:{"tick": 235, "t": "09:45:09", "acc": 0.425, "entropy": 0.9949, "ret": -0.00393, "capital": 9960.7, "trades": 51, "positions": 1, "exposure": 0.01, "predictions": 934}
data\v2.jsonl:51:{"tick": 240, "t": "09:50:12", "acc": 0.405, "entropy": 0.9957, "ret": -0.00371, "capital": 9962.9, "trades": 53, "positions": 0, "exposure": 0, "predictions": 954}
data\v2.jsonl:52:{"tick": 245, "t": "09:55:14", "acc": 0.425, "entropy": 0.9969, "ret": -0.00371, "capital": 9962.9, "trades": 53, "positions": 0, "exposure": 0, "predictions": 974}
data\v2.jsonl:53:{"tick": 250, "t": "10:00:16", "acc": 0.45, "entropy": 0.9961, "ret": -0.00371, "capital": 9962.9, "trades": 53, "positions": 0, "exposure": 0, "predictions": 994}
data\v2.jsonl:54:{"tick": 255, "t": "10:05:19", "acc": 0.44, "entropy": 0.9921, "ret": -0.003767, "capital": 9962.33, "trades": 54, "positions": 0, "exposure": 0, "predictions": 1013}
data\v2.jsonl:55:{"tick": 260, "t": "10:10:21", "acc": 0.435, "entropy": 0.9941, "ret": -0.003821, "capital": 9961.79, "trades": 55, "positions": 0, "exposure": 0, "predictions": 1033}
data\v2.jsonl:56:{"tick": 265, "t": "10:15:24", "acc": 0.455, "entropy": 0.993, "ret": -0.003821, "capital": 9961.79, "trades": 55, "positions": 0, "exposure": 0, "predictions": 1053}
data\v2.jsonl:57:{"tick": 270, "t": "10:20:26", "acc": 0.455, "entropy": 0.9963, "ret": -0.003821, "capital": 9961.79, "trades": 55, "positions": 0, "exposure": 0, "predictions": 1073}
data\v2.jsonl:58:{"tick": 275, "t": "10:25:29", "acc": 0.455, "entropy": 0.9947, "ret": -0.003821, "capital": 9961.79, "trades": 55, "positions": 0, "exposure": 0, "predictions": 1093}
data\v2.jsonl:59:{"tick": 280, "t": "10:30:31", "acc": 0.48, "entropy": 0.9935, "ret": -0.003869, "capital": 9961.31, "trades": 56, "positions": 0, "exposure": 0, "predictions": 1113}
data\v2.jsonl:60:{"tick": 285, "t": "10:35:33", "acc": 0.485, "entropy": 0.9964, "ret": -0.003853, "capital": 9961.47, "trades": 57, "positions": 0, "exposure": 0, "predictions": 1133}
data\v2.jsonl:61:{"tick": 290, "t": "10:40:35", "acc": 0.525, "entropy": 0.9944, "ret": -0.00415, "capital": 9958.5, "trades": 58, "positions": 2, "exposure": 0.02, "predictions": 1153}
data\v2.jsonl:62:{"tick": 295, "t": "10:45:37", "acc": 0.54, "entropy": 0.9935, "ret": -0.003944, "capital": 9960.56, "trades": 62, "positions": 0, "exposure": 0, "predictions": 1173}
data\v2.jsonl:63:{"tick": 300, "t": "10:50:39", "acc": 0.54, "entropy": 0.9954, "ret": -0.003944, "capital": 9960.56, "trades": 62, "positions": 0, "exposure": 0, "predictions": 1193}
data\v2.jsonl:64:{"tick": 305, "t": "10:55:41", "acc": 0.56, "entropy": 0.9958, "ret": -0.004103, "capital": 9958.97, "trades": 63, "positions": 1, "exposure": 0.01, "predictions": 1213}
data\v2.jsonl:65:{"tick": 310, "t": "11:00:43", "acc": 0.55, "entropy": 0.9961, "ret": -0.00396, "capital": 9960.4, "trades": 64, "positions": 1, "exposure": 0.01, "predictions": 1233}
data\v2.jsonl:66:{"tick": 315, "t": "11:05:45", "acc": 0.555, "entropy": 0.9953, "ret": -0.003659, "capital": 9963.41, "trades": 66, "positions": 0, "exposure": 0, "predictions": 1253}
data\v2.jsonl:67:{"tick": 320, "t": "11:10:47", "acc": 0.56, "entropy": 0.9936, "ret": -0.003872, "capital": 9961.28, "trades": 68, "positions": 0, "exposure": 0, "predictions": 1273}
data\v2.jsonl:68:{"tick": 325, "t": "11:15:49", "acc": 0.555, "entropy": 0.9959, "ret": -0.004153, "capital": 9958.47, "trades": 70, "positions": 0, "exposure": 0, "predictions": 1293}
data\v2.jsonl:69:{"tick": 330, "t": "11:20:51", "acc": 0.56, "entropy": 0.996, "ret": -0.004153, "capital": 9958.47, "trades": 70, "positions": 2, "exposure": 0.02, "predictions": 1313}
data\v2.jsonl:70:{"tick": 335, "t": "11:25:54", "acc": 0.55, "entropy": 0.9951, "ret": -0.003924, "capital": 9960.76, "trades": 71, "positions": 2, "exposure": 0.02, "predictions": 1333}
data\v2.jsonl:71:{"tick": 340, "t": "11:30:56", "acc": 0.535, "entropy": 0.997, "ret": -0.003737, "capital": 9962.63, "trades": 73, "positions": 2, "exposure": 0.02, "predictions": 1353}
data\v2.jsonl:72:{"tick": 345, "t": "11:35:58", "acc": 0.535, "entropy": 0.9949, "ret": -0.003308, "capital": 9966.92, "trades": 76, "positions": 0, "exposure": 0, "predictions": 1373}
data\v2.jsonl:73:{"tick": 350, "t": "11:41:00", "acc": 0.535, "entropy": 0.9972, "ret": -0.003288, "capital": 9967.12, "trades": 77, "positions": 0, "exposure": 0, "predictions": 1393}
data\v2.jsonl:74:{"tick": 355, "t": "11:46:02", "acc": 0.545, "entropy": 0.9958, "ret": -0.003288, "capital": 9967.12, "trades": 77, "positions": 1, "exposure": 0.01, "predictions": 1413}
data\v2.jsonl:75:{"tick": 360, "t": "11:51:10", "acc": 0.55, "entropy": 0.9938, "ret": -0.003567, "capital": 9964.33, "trades": 79, "positions": 2, "exposure": 0.02, "predictions": 1433}
data\v2.jsonl:76:{"tick": 365, "t": "11:56:13", "acc": 0.53, "entropy": 0.9911, "ret": -0.00347, "capital": 9965.3, "trades": 82, "positions": 1, "exposure": 0.01, "predictions": 1453}
data\v2.jsonl:77:{"tick": 370, "t": "12:01:15", "acc": 0.56, "entropy": 0.991, "ret": -0.002892, "capital": 9971.08, "trades": 86, "positions": 0, "exposure": 0, "predictions": 1473}
data\v2.jsonl:78:{"tick": 375, "t": "12:06:17", "acc": 0.565, "entropy": 0.9954, "ret": -0.002627, "capital": 9973.73, "trades": 87, "positions": 1, "exposure": 0.01, "predictions": 1493}
data\v2.jsonl:79:{"tick": 380, "t": "12:11:19", "acc": 0.555, "entropy": 0.9962, "ret": -0.002712, "capital": 9972.88, "trades": 88, "positions": 0, "exposure": 0, "predictions": 1513}
data\v2.jsonl:80:{"tick": 385, "t": "12:16:21", "acc": 0.54, "entropy": 0.9933, "ret": -0.002677, "capital": 9973.23, "trades": 89, "positions": 0, "exposure": 0, "predictions": 1532}
data\v2.jsonl:81:{"tick": 390, "t": "12:21:23", "acc": 0.535, "entropy": 0.9961, "ret": -0.002547, "capital": 9974.53, "trades": 90, "positions": 1, "exposure": 0.01, "predictions": 1552}
data\v2.jsonl:82:{"tick": 395, "t": "12:26:26", "acc": 0.52, "entropy": 0.9955, "ret": -0.002593, "capital": 9974.07, "trades": 94, "positions": 1, "exposure": 0.01, "predictions": 1572}
data\v2.jsonl:83:{"tick": 400, "t": "12:31:29", "acc": 0.53, "entropy": 0.9972, "ret": -0.002613, "capital": 9973.87, "trades": 96, "positions": 2, "exposure": 0.02, "predictions": 1592}
data\v2.jsonl:84:{"tick": 405, "t": "12:36:41", "acc": 0.505, "entropy": 0.9963, "ret": -0.002107, "capital": 9978.93, "trades": 99, "positions": 1, "exposure": 0.01, "predictions": 1608}
data\v2.jsonl:85:{"tick": 410, "t": "12:41:43", "acc": 0.52, "entropy": 0.9973, "ret": -0.001461, "capital": 9985.39, "trades": 104, "positions": 0, "exposure": 0, "predictions": 1628}
data\v2.jsonl:86:{"tick": 415, "t": "12:46:45", "acc": 0.53, "entropy": 0.997, "ret": -0.001263, "capital": 9987.37, "trades": 105, "positions": 0, "exposure": 0, "predictions": 1648}
data\v2.jsonl:87:{"tick": 420, "t": "12:51:47", "acc": 0.53, "entropy": 0.9939, "ret": -0.001543, "capital": 9984.57, "trades": 108, "positions": 1, "exposure": 0.01, "predictions": 1668}
data\v2.jsonl:88:{"tick": 425, "t": "12:56:50", "acc": 0.51, "entropy": 0.9947, "ret": -0.001456, "capital": 9985.44, "trades": 109, "positions": 0, "exposure": 0, "predictions": 1688}
data\v2.jsonl:89:{"tick": 430, "t": "13:01:52", "acc": 0.5, "entropy": 0.9898, "ret": -0.001576, "capital": 9984.24, "trades": 110, "positions": 1, "exposure": 0.01, "predictions": 1708}
data\v2.jsonl:90:{"tick": 435, "t": "13:06:54", "acc": 0.515, "entropy": 0.9923, "ret": -0.002016, "capital": 9979.84, "trades": 111, "positions": 3, "exposure": 0.03, "predictions": 1728}
data\v2.jsonl:91:{"tick": 440, "t": "13:11:56", "acc": 0.525, "entropy": 0.9942, "ret": -0.001992, "capital": 9980.08, "trades": 114, "positions": 0, "exposure": 0, "predictions": 1748}
data\v2.jsonl:92:{"tick": 445, "t": "13:16:58", "acc": 0.52, "entropy": 0.9931, "ret": -0.0021, "capital": 9979.0, "trades": 117, "positions": 0, "exposure": 0, "predictions": 1768}
data\v2.jsonl:93:{"tick": 450, "t": "13:22:00", "acc": 0.53, "entropy": 0.994, "ret": -0.002578, "capital": 9974.22, "trades": 120, "positions": 1, "exposure": 0.01, "predictions": 1788}
data\v2.jsonl:94:{"tick": 455, "t": "13:27:03", "acc": 0.535, "entropy": 0.9964, "ret": -0.002451, "capital": 9975.49, "trades": 123, "positions": 0, "exposure": 0, "predictions": 1808}
data\v2.jsonl:95:{"tick": 460, "t": "13:32:05", "acc": 0.535, "entropy": 0.9949, "ret": -0.002398, "capital": 9976.02, "trades": 124, "positions": 3, "exposure": 0.03, "predictions": 1828}
data\v2.jsonl:96:{"tick": 465, "t": "13:37:07", "acc": 0.525, "entropy": 0.9921, "ret": -0.003404, "capital": 9965.96, "trades": 130, "positions": 0, "exposure": 0, "predictions": 1848}
data\v2.jsonl:97:{"tick": 470, "t": "13:42:09", "acc": 0.52, "entropy": 0.995, "ret": -0.003485, "capital": 9965.15, "trades": 131, "positions": 2, "exposure": 0.02, "predictions": 1868}
data\v2.jsonl:98:{"tick": 475, "t": "13:47:11", "acc": 0.55, "entropy": 0.9944, "ret": -0.003865, "capital": 9961.35, "trades": 135, "positions": 1, "exposure": 0.01, "predictions": 1888}
data\v2.jsonl:99:{"tick": 480, "t": "13:52:14", "acc": 0.56, "entropy": 0.9902, "ret": -0.003048, "capital": 9969.52, "trades": 139, "positions": 2, "exposure": 0.02, "predictions": 1908}
data\v2.jsonl:100:{"tick": 485, "t": "13:57:19", "acc": 0.58, "entropy": 0.9854, "ret": -0.002161, "capital": 9978.39, "trades": 141, "positions": 1, "exposure": 0.01, "predictions": 1928}
data\v2.jsonl:101:{"tick": 490, "t": "14:02:21", "acc": 0.585, "entropy": 0.9897, "ret": -0.001859, "capital": 9981.41, "trades": 142, "positions": 2, "exposure": 0.02, "predictions": 1947}
data\v2.jsonl:102:{"tick": 495, "t": "14:07:23", "acc": 0.585, "entropy": 0.9894, "ret": -0.002184, "capital": 9978.16, "trades": 145, "positions": 1, "exposure": 0.01, "predictions": 1967}
data\v2.jsonl:103:{"tick": 500, "t": "14:12:26", "acc": 0.58, "entropy": 0.9908, "ret": -0.001374, "capital": 9986.26, "trades": 147, "positions": 1, "exposure": 0.01, "predictions": 1987}
data\v2.jsonl:104:{"tick": 505, "t": "14:17:19", "acc": 0.585, "entropy": 0.9913, "ret": -0.001729, "capital": 9982.71, "trades": 150, "positions": 0, "exposure": 0, "predictions": 2007}
data\v2.jsonl:105:{"tick": 510, "t": "14:22:21", "acc": 0.585, "entropy": 0.9941, "ret": -0.001729, "capital": 9982.71, "trades": 150, "positions": 0, "exposure": 0, "predictions": 2027}
data\v2.jsonl:106:{"tick": 515, "t": "14:27:24", "acc": 0.585, "entropy": 0.9965, "ret": -0.00245, "capital": 9975.5, "trades": 151, "positions": 0, "exposure": 0, "predictions": 2047}
data\v2.jsonl:107:{"tick": 520, "t": "14:32:26", "acc": 0.565, "entropy": 0.9969, "ret": -0.002535, "capital": 9974.65, "trades": 152, "positions": 0, "exposure": 0, "predictions": 2067}
data\v2.jsonl:108:{"tick": 525, "t": "14:37:28", "acc": 0.545, "entropy": 0.9947, "ret": -0.002372, "capital": 9976.28, "trades": 156, "positions": 0, "exposure": 0, "predictions": 2087}
data\v2.jsonl:109:{"tick": 530, "t": "14:42:30", "acc": 0.525, "entropy": 0.9917, "ret": -0.002542, "capital": 9974.58, "trades": 159, "positions": 4, "exposure": 0.04, "predictions": 2107}
data\v2.jsonl:110:{"tick": 535, "t": "14:47:32", "acc": 0.51, "entropy": 0.992, "ret": -0.002866, "capital": 9971.34, "trades": 164, "positions": 1, "exposure": 0.01, "predictions": 2127}
data\v2.jsonl:111:{"tick": 540, "t": "14:52:34", "acc": 0.495, "entropy": 0.9933, "ret": -0.001923, "capital": 9980.77, "trades": 167, "positions": 0, "exposure": 0, "predictions": 2147}
data\v2.jsonl:112:{"tick": 545, "t": "14:57:37", "acc": 0.49, "entropy": 0.9961, "ret": -0.00223, "capital": 9977.7, "trades": 169, "positions": 0, "exposure": 0, "predictions": 2167}
data\v2.jsonl:113:{"tick": 550, "t": "15:02:39", "acc": 0.495, "entropy": 0.9931, "ret": -0.001816, "capital": 9981.84, "trades": 170, "positions": 3, "exposure": 0.03, "predictions": 2187}
data\v2.jsonl:114:{"tick": 555, "t": "15:07:41", "acc": 0.5, "entropy": 0.9962, "ret": -0.000358, "capital": 9996.42, "trades": 174, "positions": 1, "exposure": 0.01, "predictions": 2207}
data\v2.jsonl:115:{"tick": 560, "t": "15:12:43", "acc": 0.505, "entropy": 0.9956, "ret": 0.001151, "capital": 10011.51, "trades": 178, "positions": 1, "exposure": 0.0138, "predictions": 2227}
data\v2.jsonl:116:{"tick": 565, "t": "15:17:45", "acc": 0.525, "entropy": 0.9954, "ret": 0.001028, "capital": 10010.28, "trades": 180, "positions": 0, "exposure": 0, "predictions": 2247}
data\v2.jsonl:117:{"tick": 570, "t": "15:22:47", "acc": 0.515, "entropy": 0.9952, "ret": 0.001028, "capital": 10010.28, "trades": 180, "positions": 2, "exposure": 0.0316, "predictions": 2267}
data\v2.jsonl:118:{"tick": 575, "t": "15:27:50", "acc": 0.485, "entropy": 0.9945, "ret": 0.001119, "capital": 10011.19, "trades": 181, "positions": 1, "exposure": 0.0181, "predictions": 2287}
data\v2.jsonl:119:{"tick": 580, "t": "15:32:52", "acc": 0.51, "entropy": 0.9954, "ret": 0.00029, "capital": 10002.9, "trades": 183, "positions": 1, "exposure": 0.0181, "predictions": 2307}
data\v2.jsonl:120:{"tick": 585, "t": "15:37:54", "acc": 0.48, "entropy": 0.9931, "ret": 0.00029, "capital": 10002.9, "trades": 183, "positions": 2, "exposure": 0.0387, "predictions": 2327}
data\v2.jsonl:121:{"tick": 590, "t": "15:42:56", "acc": 0.475, "entropy": 0.9925, "ret": -0.003745, "capital": 9962.55, "trades": 186, "positions": 1, "exposure": 0.01, "predictions": 2347}
data\v2.jsonl:122:{"tick": 595, "t": "15:47:58", "acc": 0.475, "entropy": 0.9943, "ret": -0.003688, "capital": 9963.12, "trades": 187, "positions": 2, "exposure": 0.02, "predictions": 2367}
data\v2.jsonl:123:{"tick": 600, "t": "15:53:00", "acc": 0.455, "entropy": 0.9913, "ret": -0.003859, "capital": 9961.41, "trades": 189, "positions": 2, "exposure": 0.02, "predictions": 2387}
data\v2.jsonl:124:{"tick": 605, "t": "15:58:03", "acc": 0.445, "entropy": 0.9906, "ret": -0.004063, "capital": 9959.37, "trades": 191, "positions": 2, "exposure": 0.02, "predictions": 2407}
data\v2.jsonl:125:{"tick": 610, "t": "16:03:05", "acc": 0.435, "entropy": 0.9883, "ret": -0.0036, "capital": 9964.0, "trades": 192, "positions": 3, "exposure": 0.03, "predictions": 2427}
data\v2.jsonl:126:{"tick": 615, "t": "16:08:07", "acc": 0.415, "entropy": 0.9877, "ret": -0.004063, "capital": 9959.37, "trades": 194, "positions": 1, "exposure": 0.01, "predictions": 2447}
data\v2.jsonl:127:{"tick": 620, "t": "16:13:09", "acc": 0.455, "entropy": 0.9873, "ret": -0.003841, "capital": 9961.59, "trades": 195, "positions": 3, "exposure": 0.03, "predictions": 2467}
data\v2.jsonl:128:{"tick": 625, "t": "16:18:11", "acc": 0.49, "entropy": 0.9908, "ret": -0.003438, "capital": 9965.62, "trades": 197, "positions": 1, "exposure": 0.01, "predictions": 2487}
data\v2.jsonl:129:{"tick": 630, "t": "16:23:13", "acc": 0.485, "entropy": 0.9922, "ret": -0.003328, "capital": 9966.72, "trades": 198, "positions": 2, "exposure": 0.02, "predictions": 2507}
data\v2.jsonl:130:{"tick": 635, "t": "16:28:16", "acc": 0.53, "entropy": 0.9915, "ret": -0.003424, "capital": 9965.76, "trades": 200, "positions": 3, "exposure": 0.03, "predictions": 2527}
data\v2.jsonl:131:{"tick": 640, "t": "16:33:18", "acc": 0.535, "entropy": 0.9895, "ret": -0.002411, "capital": 9975.89, "trades": 205, "positions": 1, "exposure": 0.01, "predictions": 2547}
data\v2.jsonl:132:{"tick": 645, "t": "16:38:20", "acc": 0.56, "entropy": 0.9937, "ret": -0.001926, "capital": 9980.74, "trades": 207, "positions": 0, "exposure": 0, "predictions": 2567}
data\v2.jsonl:133:{"tick": 650, "t": "16:43:22", "acc": 0.555, "entropy": 0.9939, "ret": -0.001926, "capital": 9980.74, "trades": 207, "positions": 0, "exposure": 0, "predictions": 2587}
data\v2.jsonl:134:{"tick": 655, "t": "16:48:24", "acc": 0.55, "entropy": 0.9932, "ret": -0.001926, "capital": 9980.74, "trades": 207, "positions": 1, "exposure": 0.01, "predictions": 2607}
data\v2.jsonl:135:{"tick": 660, "t": "16:53:26", "acc": 0.535, "entropy": 0.9929, "ret": -0.001926, "capital": 9980.74, "trades": 207, "positions": 3, "exposure": 0.0373, "predictions": 2627}
data\v2.jsonl:136:{"tick": 665, "t": "16:58:29", "acc": 0.535, "entropy": 0.9807, "ret": -0.004248, "capital": 9957.52, "trades": 210, "positions": 2, "exposure": 0.02, "predictions": 2647}
data\v2.jsonl:137:{"tick": 670, "t": "17:03:31", "acc": 0.525, "entropy": 0.9891, "ret": -0.003885, "capital": 9961.15, "trades": 211, "positions": 2, "exposure": 0.02, "predictions": 2667}
data\v2.jsonl:138:{"tick": 675, "t": "17:08:33", "acc": 0.51, "entropy": 0.9882, "ret": -0.00359, "capital": 9964.1, "trades": 215, "positions": 0, "exposure": 0, "predictions": 2687}
data\v2.jsonl:139:{"tick": 680, "t": "17:13:35", "acc": 0.515, "entropy": 0.9934, "ret": -0.003597, "capital": 9964.03, "trades": 216, "positions": 1, "exposure": 0.01, "predictions": 2707}
data\v2.jsonl:140:{"tick": 685, "t": "17:18:37", "acc": 0.52, "entropy": 0.9954, "ret": -0.003537, "capital": 9964.63, "trades": 217, "positions": 2, "exposure": 0.02, "predictions": 2727}
data\v2.jsonl:141:{"tick": 690, "t": "17:23:39", "acc": 0.535, "entropy": 0.9944, "ret": -0.003147, "capital": 9968.53, "trades": 219, "positions": 1, "exposure": 0.01, "predictions": 2747}
data\v2.jsonl:142:{"tick": 695, "t": "17:28:41", "acc": 0.505, "entropy": 0.9887, "ret": -0.004305, "capital": 9956.95, "trades": 221, "positions": 1, "exposure": 0.01, "predictions": 2767}
data\v2.jsonl:143:{"tick": 700, "t": "17:33:44", "acc": 0.495, "entropy": 0.9879, "ret": -0.004404, "capital": 9955.96, "trades": 222, "positions": 0, "exposure": 0, "predictions": 2787}
data\v2.jsonl:144:{"tick": 705, "t": "17:38:46", "acc": 0.5, "entropy": 0.9882, "ret": -0.0044, "capital": 9956.0, "trades": 226, "positions": 1, "exposure": 0.01, "predictions": 2807}
data\v2.jsonl:145:{"tick": 710, "t": "17:43:48", "acc": 0.51, "entropy": 0.9921, "ret": -0.004621, "capital": 9953.79, "trades": 227, "positions": 3, "exposure": 0.03, "predictions": 2827}
data\v2.jsonl:146:{"tick": 715, "t": "17:48:50", "acc": 0.505, "entropy": 0.9939, "ret": -0.004744, "capital": 9952.56, "trades": 228, "positions": 2, "exposure": 0.02, "predictions": 2847}
data\v2.jsonl:147:{"tick": 720, "t": "17:53:52", "acc": 0.53, "entropy": 0.9945, "ret": -0.004299, "capital": 9957.01, "trades": 232, "positions": 1, "exposure": 0.01, "predictions": 2867}
data\v2.jsonl:148:{"tick": 725, "t": "17:58:54", "acc": 0.535, "entropy": 0.9954, "ret": -0.004574, "capital": 9954.26, "trades": 233, "positions": 1, "exposure": 0.01, "predictions": 2887}
data\v2.jsonl:149:{"tick": 730, "t": "18:03:56", "acc": 0.52, "entropy": 0.9955, "ret": -0.004264, "capital": 9957.36, "trades": 234, "positions": 2, "exposure": 0.0208, "predictions": 2907}
data\v2.jsonl:150:{"tick": 735, "t": "18:08:58", "acc": 0.49, "entropy": 0.9928, "ret": -0.004625, "capital": 9953.75, "trades": 238, "positions": 0, "exposure": 0, "predictions": 2927}
data\v2.jsonl:151:{"tick": 740, "t": "18:14:01", "acc": 0.48, "entropy": 0.9936, "ret": -0.004625, "capital": 9953.75, "trades": 238, "positions": 0, "exposure": 0, "predictions": 2947}
data\v2.jsonl:152:{"tick": 745, "t": "18:19:03", "acc": 0.48, "entropy": 0.995, "ret": -0.004493, "capital": 9955.07, "trades": 241, "positions": 0, "exposure": 0, "predictions": 2967}
data\v2.jsonl:153:{"tick": 750, "t": "18:24:05", "acc": 0.5, "entropy": 0.9957, "ret": -0.00479, "capital": 9952.1, "trades": 243, "positions": 1, "exposure": 0.0113, "predictions": 2987}
data\v2.jsonl:154:{"tick": 755, "t": "18:29:07", "acc": 0.495, "entropy": 0.9973, "ret": -0.005237, "capital": 9947.63, "trades": 244, "positions": 1, "exposure": 0.01, "predictions": 3007}
data\v2.jsonl:155:{"tick": 760, "t": "18:34:09", "acc": 0.48, "entropy": 0.9974, "ret": -0.005437, "capital": 9945.63, "trades": 246, "positions": 2, "exposure": 0.02, "predictions": 3025}
data\v2.jsonl:156:{"tick": 765, "t": "18:39:12", "acc": 0.49, "entropy": 0.9965, "ret": -0.007218, "capital": 9927.82, "trades": 251, "positions": 1, "exposure": 0.01, "predictions": 3045}
data\v2.jsonl:157:{"tick": 770, "t": "18:44:14", "acc": 0.46, "entropy": 0.9953, "ret": -0.007094, "capital": 9929.06, "trades": 252, "positions": 2, "exposure": 0.02, "predictions": 3065}
data\v2.jsonl:158:{"tick": 775, "t": "18:49:16", "acc": 0.46, "entropy": 0.9947, "ret": -0.006596, "capital": 9934.04, "trades": 256, "positions": 2, "exposure": 0.02, "predictions": 3085}
data\v2.jsonl:159:{"tick": 780, "t": "18:54:18", "acc": 0.455, "entropy": 0.9938, "ret": -0.006858, "capital": 9931.42, "trades": 260, "positions": 1, "exposure": 0.01, "predictions": 3105}
data\v2.jsonl:160:{"tick": 785, "t": "18:59:21", "acc": 0.455, "entropy": 0.9939, "ret": -0.006717, "capital": 9932.83, "trades": 262, "positions": 0, "exposure": 0, "predictions": 3125}
data\v2.jsonl:161:{"tick": 790, "t": "19:04:23", "acc": 0.435, "entropy": 0.9953, "ret": -0.006717, "capital": 9932.83, "trades": 262, "positions": 1, "exposure": 0.01, "predictions": 3145}
data\v2.jsonl:162:{"tick": 795, "t": "19:09:25", "acc": 0.435, "entropy": 0.995, "ret": -0.006029, "capital": 9939.71, "trades": 263, "positions": 0, "exposure": 0, "predictions": 3165}
data\v2.jsonl:163:{"tick": 800, "t": "19:14:27", "acc": 0.455, "entropy": 0.9938, "ret": -0.006029, "capital": 9939.71, "trades": 263, "positions": 0, "exposure": 0, "predictions": 3185}
data\v2.jsonl:164:{"tick": 805, "t": "19:19:29", "acc": 0.44, "entropy": 0.992, "ret": -0.006103, "capital": 9938.97, "trades": 264, "positions": 3, "exposure": 0.03, "predictions": 3205}
data\v2.jsonl:165:{"tick": 810, "t": "19:24:31", "acc": 0.455, "entropy": 0.995, "ret": -0.006308, "capital": 9936.92, "trades": 266, "positions": 2, "exposure": 0.02, "predictions": 3225}
data\v2.jsonl:166:{"tick": 815, "t": "19:29:34", "acc": 0.445, "entropy": 0.9936, "ret": -0.004506, "capital": 9954.94, "trades": 270, "positions": 2, "exposure": 0.0253, "predictions": 3245}
data\v2.jsonl:167:{"tick": 820, "t": "19:34:36", "acc": 0.455, "entropy": 0.9951, "ret": -0.005742, "capital": 9942.58, "trades": 273, "positions": 2, "exposure": 0.0207, "predictions": 3265}
data\v2.jsonl:168:{"tick": 825, "t": "19:39:38", "acc": 0.455, "entropy": 0.9966, "ret": -0.006374, "capital": 9936.26, "trades": 276, "positions": 1, "exposure": 0.01, "predictions": 3285}
data\v2.jsonl:169:{"tick": 830, "t": "19:44:41", "acc": 0.455, "entropy": 0.9958, "ret": -0.006413, "capital": 9935.87, "trades": 277, "positions": 2, "exposure": 0.02, "predictions": 3305}
data\v2.jsonl:170:{"tick": 835, "t": "19:49:43", "acc": 0.47, "entropy": 0.9939, "ret": -0.006482, "capital": 9935.18, "trades": 279, "positions": 0, "exposure": 0, "predictions": 3325}
data\v2.jsonl:171:{"tick": 840, "t": "19:54:45", "acc": 0.5, "entropy": 0.9944, "ret": -0.006482, "capital": 9935.18, "trades": 279, "positions": 0, "exposure": 0, "predictions": 3345}
data\v2.jsonl:172:{"tick": 845, "t": "19:59:48", "acc": 0.495, "entropy": 0.993, "ret": -0.006482, "capital": 9935.18, "trades": 279, "positions": 1, "exposure": 0.01, "predictions": 3365}
data\v2.jsonl:173:{"tick": 850, "t": "20:04:50", "acc": 0.485, "entropy": 0.9972, "ret": -0.006174, "capital": 9938.26, "trades": 281, "positions": 0, "exposure": 0, "predictions": 3385}
data\v2.jsonl:174:{"tick": 855, "t": "20:09:52", "acc": 0.48, "entropy": 0.996, "ret": -0.006165, "capital": 9938.35, "trades": 282, "positions": 1, "exposure": 0.01, "predictions": 3405}
data\v2.jsonl:175:{"tick": 860, "t": "20:14:55", "acc": 0.475, "entropy": 0.9975, "ret": -0.006315, "capital": 9936.85, "trades": 284, "positions": 0, "exposure": 0, "predictions": 3425}
data\v2.jsonl:176:{"tick": 865, "t": "20:19:57", "acc": 0.505, "entropy": 0.9983, "ret": -0.006764, "capital": 9932.36, "trades": 286, "positions": 0, "exposure": 0, "predictions": 3445}
data\v2.jsonl:177:{"tick": 870, "t": "20:24:59", "acc": 0.51, "entropy": 0.9969, "ret": -0.00662, "capital": 9933.8, "trades": 287, "positions": 2, "exposure": 0.02, "predictions": 3465}
data\v2.jsonl:178:{"tick": 875, "t": "20:30:01", "acc": 0.51, "entropy": 0.9965, "ret": -0.006498, "capital": 9935.02, "trades": 290, "positions": 1, "exposure": 0.01, "predictions": 3485}
data\v2.jsonl:179:{"tick": 880, "t": "20:35:03", "acc": 0.535, "entropy": 0.9941, "ret": -0.006643, "capital": 9933.57, "trades": 294, "positions": 0, "exposure": 0, "predictions": 3505}
data\v2.jsonl:180:{"tick": 885, "t": "20:40:05", "acc": 0.525, "entropy": 0.9961, "ret": -0.006766, "capital": 9932.34, "trades": 295, "positions": 0, "exposure": 0, "predictions": 3525}
data\v2.jsonl:181:{"tick": 875, "t": "01:06:00", "acc": 0.5, "entropy": 0.9951, "ret": -0.006455, "capital": 9935.45, "trades": 289, "positions": 0, "exposure": 0, "predictions": 12}
data\v2.jsonl:182:{"tick": 880, "t": "01:11:04", "acc": 0.5, "entropy": 0.9948, "ret": -0.006473, "capital": 9935.27, "trades": 290, "positions": 1, "exposure": 0.01, "predictions": 32}
data\v2.jsonl:183:{"tick": 885, "t": "01:16:07", "acc": 0.3654, "entropy": 0.9946, "ret": -0.006575, "capital": 9934.25, "trades": 292, "positions": 3, "exposure": 0.03, "predictions": 52}
data\v2.jsonl:184:{"tick": 890, "t": "01:21:44", "acc": 0.4493, "entropy": 0.9957, "ret": -0.006694, "capital": 9933.06, "trades": 296, "positions": 1, "exposure": 0.01, "predictions": 71}
data\v2.jsonl:185:{"tick": 895, "t": "01:27:11", "acc": 0.4822, "entropy": 0.9962, "ret": -0.006563, "capital": 9934.37, "trades": 298, "positions": 2, "exposure": 0.02, "predictions": 91}
data\v2.jsonl:186:{"tick": 900, "t": "01:32:13", "acc": 0.5036, "entropy": 0.9955, "ret": -0.006716, "capital": 9932.84, "trades": 301, "positions": 1, "exposure": 0.01, "predictions": 111}
data\v2.jsonl:187:{"tick": 905, "t": "01:37:16", "acc": 0.5258, "entropy": 0.9945, "ret": -0.006635, "capital": 9933.65, "trades": 305, "positions": 0, "exposure": 0, "predictions": 131}
data\v2.jsonl:188:{"tick": 910, "t": "01:42:18", "acc": 0.5293, "entropy": 0.9971, "ret": -0.006637, "capital": 9933.63, "trades": 306, "positions": 2, "exposure": 0.02, "predictions": 151}
data\v2.jsonl:189:{"tick": 915, "t": "01:47:20", "acc": 0.5375, "entropy": 0.9956, "ret": -0.006711, "capital": 9932.89, "trades": 308, "positions": 0, "exposure": 0, "predictions": 171}
data\v2.jsonl:190:{"tick": 920, "t": "01:52:22", "acc": 0.5338, "entropy": 0.995, "ret": -0.006915, "capital": 9930.85, "trades": 309, "positions": 3, "exposure": 0.03, "predictions": 191}
data\v2.jsonl:191:{"tick": 925, "t": "01:57:24", "acc": 0.54, "entropy": 0.9957, "ret": -0.006493, "capital": 9935.07, "trades": 313, "positions": 2, "exposure": 0.02, "predictions": 211}
data\v2.jsonl:192:{"tick": 930, "t": "02:02:26", "acc": 0.535, "entropy": 0.993, "ret": -0.006513, "capital": 9934.87, "trades": 316, "positions": 0, "exposure": 0, "predictions": 231}
data\v2.jsonl:193:{"tick": 935, "t": "02:07:28", "acc": 0.53, "entropy": 0.9945, "ret": -0.006605, "capital": 9933.95, "trades": 318, "positions": 0, "exposure": 0, "predictions": 251}
data\v2.jsonl:194:{"tick": 940, "t": "02:12:30", "acc": 0.52, "entropy": 0.9965, "ret": -0.006665, "capital": 9933.35, "trades": 319, "positions": 0, "exposure": 0, "predictions": 271}
data\v2.jsonl:195:{"tick": 945, "t": "02:17:32", "acc": 0.51, "entropy": 0.9954, "ret": -0.00659, "capital": 9934.1, "trades": 320, "positions": 0, "exposure": 0, "predictions": 291}
data\v2.jsonl:196:{"tick": 950, "t": "02:22:34", "acc": 0.505, "entropy": 0.9963, "ret": -0.006704, "capital": 9932.96, "trades": 322, "positions": 1, "exposure": 0.01, "predictions": 311}
data\v2.jsonl:197:{"tick": 955, "t": "02:27:37", "acc": 0.47, "entropy": 0.993, "ret": -0.006866, "capital": 9931.34, "trades": 324, "positions": 2, "exposure": 0.02, "predictions": 331}
data\v2.jsonl:198:{"tick": 960, "t": "02:32:39", "acc": 0.475, "entropy": 0.9924, "ret": -0.007808, "capital": 9921.92, "trades": 327, "positions": 2, "exposure": 0.02, "predictions": 351}
data\v2.jsonl:199:{"tick": 965, "t": "02:37:51", "acc": 0.44, "entropy": 0.9947, "ret": -0.00807, "capital": 9919.3, "trades": 332, "positions": 2, "exposure": 0.02, "predictions": 371}
data\v2.jsonl:200:{"tick": 970, "t": "02:42:53", "acc": 0.43, "entropy": 0.9902, "ret": -0.008261, "capital": 9917.39, "trades": 334, "positions": 1, "exposure": 0.01, "predictions": 391}
data\v2.jsonl:201:{"tick": 975, "t": "02:47:55", "acc": 0.435, "entropy": 0.9912, "ret": -0.00831, "capital": 9916.9, "trades": 335, "positions": 1, "exposure": 0.01, "predictions": 411}
data\v2.jsonl:202:{"tick": 980, "t": "02:52:57", "acc": 0.44, "entropy": 0.9944, "ret": -0.00858, "capital": 9914.2, "trades": 338, "positions": 2, "exposure": 0.02, "predictions": 431}
data\v2.jsonl:203:{"tick": 985, "t": "02:57:59", "acc": 0.46, "entropy": 0.9965, "ret": -0.009004, "capital": 9909.96, "trades": 341, "positions": 0, "exposure": 0, "predictions": 451}
data\v2.jsonl:204:{"tick": 990, "t": "03:03:01", "acc": 0.445, "entropy": 0.9959, "ret": -0.009037, "capital": 9909.63, "trades": 342, "positions": 2, "exposure": 0.02, "predictions": 471}
data\v2.jsonl:205:{"tick": 995, "t": "03:08:03", "acc": 0.435, "entropy": 0.9964, "ret": -0.009201, "capital": 9907.99, "trades": 347, "positions": 1, "exposure": 0.01, "predictions": 491}
data\v2.jsonl:206:{"tick": 1000, "t": "03:13:06", "acc": 0.44, "entropy": 0.9951, "ret": -0.009376, "capital": 9906.24, "trades": 350, "positions": 1, "exposure": 0.01, "predictions": 511}
data\v2.jsonl:207:{"tick": 1005, "t": "03:18:08", "acc": 0.465, "entropy": 0.9927, "ret": -0.009441, "capital": 9905.59, "trades": 351, "positions": 2, "exposure": 0.02, "predictions": 531}
data\v2.jsonl:208:{"tick": 1010, "t": "03:23:10", "acc": 0.46, "entropy": 0.992, "ret": -0.009586, "capital": 9904.14, "trades": 353, "positions": 0, "exposure": 0, "predictions": 551}
data\v2.jsonl:209:{"tick": 1015, "t": "03:28:12", "acc": 0.475, "entropy": 0.9938, "ret": -0.009715, "capital": 9902.85, "trades": 355, "positions": 0, "exposure": 0, "predictions": 571}
data\v2.jsonl:210:{"tick": 1020, "t": "03:33:14", "acc": 0.475, "entropy": 0.9946, "ret": -0.009715, "capital": 9902.85, "trades": 355, "positions": 2, "exposure": 0.02, "predictions": 591}
data\v2.jsonl:211:{"tick": 1025, "t": "03:38:17", "acc": 0.47, "entropy": 0.9952, "ret": -0.00988, "capital": 9901.2, "trades": 358, "positions": 1, "exposure": 0.01, "predictions": 611}
data\v2.jsonl:212:{"tick": 1030, "t": "03:43:19", "acc": 0.48, "entropy": 0.997, "ret": -0.009846, "capital": 9901.54, "trades": 359, "positions": 0, "exposure": 0, "predictions": 631}
data\v2.jsonl:213:{"tick": 1035, "t": "03:48:21", "acc": 0.455, "entropy": 0.9962, "ret": -0.00988, "capital": 9901.2, "trades": 361, "positions": 1, "exposure": 0.01, "predictions": 651}
data\v2.jsonl:214:{"tick": 1040, "t": "03:53:23", "acc": 0.445, "entropy": 0.9977, "ret": -0.00988, "capital": 9901.2, "trades": 361, "positions": 1, "exposure": 0.01, "predictions": 671}
data\v2.jsonl:215:{"tick": 1045, "t": "03:58:25", "acc": 0.445, "entropy": 0.9978, "ret": -0.009792, "capital": 9902.08, "trades": 362, "positions": 1, "exposure": 0.01, "predictions": 691}
data\v2.jsonl:216:{"tick": 1050, "t": "04:03:27", "acc": 0.435, "entropy": 0.9971, "ret": -0.009716, "capital": 9902.84, "trades": 365, "positions": 1, "exposure": 0.01, "predictions": 711}
data\v2.jsonl:217:{"tick": 1055, "t": "04:08:29", "acc": 0.415, "entropy": 0.9954, "ret": -0.009723, "capital": 9902.77, "trades": 368, "positions": 1, "exposure": 0.01, "predictions": 731}
data\v2.jsonl:218:{"tick": 1060, "t": "04:13:31", "acc": 0.395, "entropy": 0.9964, "ret": -0.009711, "capital": 9902.89, "trades": 372, "positions": 0, "exposure": 0, "predictions": 751}
data\v2.jsonl:219:{"tick": 1065, "t": "04:18:33", "acc": 0.42, "entropy": 0.9957, "ret": -0.009711, "capital": 9902.89, "trades": 372, "positions": 0, "exposure": 0, "predictions": 771}
data\v2.jsonl:220:{"tick": 1070, "t": "04:23:35", "acc": 0.425, "entropy": 0.9959, "ret": -0.009699, "capital": 9903.01, "trades": 373, "positions": 1, "exposure": 0.01, "predictions": 791}
data\v2.jsonl:221:{"tick": 1075, "t": "04:28:37", "acc": 0.42, "entropy": 0.9964, "ret": -0.009753, "capital": 9902.47, "trades": 375, "positions": 3, "exposure": 0.03, "predictions": 811}
data\v2.jsonl:222:{"tick": 1080, "t": "04:33:39", "acc": 0.415, "entropy": 0.9955, "ret": -0.009788, "capital": 9902.12, "trades": 378, "positions": 0, "exposure": 0, "predictions": 831}
data\v2.jsonl:223:{"tick": 1085, "t": "04:38:41", "acc": 0.455, "entropy": 0.9975, "ret": -0.009685, "capital": 9903.15, "trades": 382, "positions": 0, "exposure": 0, "predictions": 851}
data\v2.jsonl:224:{"tick": 1090, "t": "04:43:43", "acc": 0.475, "entropy": 0.9972, "ret": -0.009716, "capital": 9902.84, "trades": 384, "positions": 1, "exposure": 0.01, "predictions": 871}
data\v2.jsonl:225:{"tick": 1095, "t": "04:48:45", "acc": 0.49, "entropy": 0.9976, "ret": -0.00971, "capital": 9902.9, "trades": 387, "positions": 1, "exposure": 0.01, "predictions": 891}
data\v2.jsonl:226:{"tick": 1100, "t": "04:53:47", "acc": 0.48, "entropy": 0.9952, "ret": -0.009215, "capital": 9907.85, "trades": 389, "positions": 0, "exposure": 0, "predictions": 911}
data\v2.jsonl:227:{"tick": 1105, "t": "04:58:49", "acc": 0.5, "entropy": 0.9933, "ret": -0.009161, "capital": 9908.39, "trades": 390, "positions": 1, "exposure": 0.01, "predictions": 931}
data\v2.jsonl:228:{"tick": 1110, "t": "05:03:51", "acc": 0.51, "entropy": 0.9951, "ret": -0.009358, "capital": 9906.42, "trades": 394, "positions": 0, "exposure": 0, "predictions": 951}
data\v2.jsonl:229:{"tick": 1115, "t": "05:08:54", "acc": 0.485, "entropy": 0.9934, "ret": -0.009784, "capital": 9902.16, "trades": 397, "positions": 3, "exposure": 0.03, "predictions": 971}
data\v2.jsonl:230:{"tick": 1120, "t": "05:13:56", "acc": 0.495, "entropy": 0.9919, "ret": -0.009986, "capital": 9900.14, "trades": 400, "positions": 1, "exposure": 0.01, "predictions": 991}
data\v2.jsonl:231:{"tick": 1125, "t": "05:18:58", "acc": 0.515, "entropy": 0.9948, "ret": -0.010392, "capital": 9896.08, "trades": 402, "positions": 1, "exposure": 0.01, "predictions": 1011}
data\v2.jsonl:232:{"tick": 1130, "t": "05:24:00", "acc": 0.52, "entropy": 0.992, "ret": -0.010534, "capital": 9894.66, "trades": 403, "positions": 3, "exposure": 0.03, "predictions": 1031}
data\v2.jsonl:233:{"tick": 1135, "t": "05:29:02", "acc": 0.5, "entropy": 0.9927, "ret": -0.010785, "capital": 9892.15, "trades": 407, "positions": 1, "exposure": 0.01, "predictions": 1051}
data\v2.jsonl:234:{"tick": 1140, "t": "05:34:04", "acc": 0.505, "entropy": 0.9953, "ret": -0.01042, "capital": 9895.8, "trades": 410, "positions": 1, "exposure": 0.01, "predictions": 1071}
data\v2.jsonl:235:{"tick": 1145, "t": "05:39:09", "acc": 0.51, "entropy": 0.9949, "ret": -0.010346, "capital": 9896.54, "trades": 412, "positions": 2, "exposure": 0.02, "predictions": 1091}
data\v2.jsonl:236:{"tick": 1150, "t": "05:44:11", "acc": 0.505, "entropy": 0.9934, "ret": -0.010405, "capital": 9895.95, "trades": 415, "positions": 1, "exposure": 0.01, "predictions": 1111}
data\v2.jsonl:237:{"tick": 1155, "t": "05:49:13", "acc": 0.51, "entropy": 0.9941, "ret": -0.010839, "capital": 9891.61, "trades": 417, "positions": 1, "exposure": 0.01, "predictions": 1130}
data\v2.jsonl:238:{"tick": 1160, "t": "05:54:15", "acc": 0.515, "entropy": 0.992, "ret": -0.010905, "capital": 9890.95, "trades": 418, "positions": 2, "exposure": 0.02, "predictions": 1150}
data\v2.jsonl:239:{"tick": 1165, "t": "05:59:17", "acc": 0.53, "entropy": 0.993, "ret": -0.010819, "capital": 9891.81, "trades": 420, "positions": 0, "exposure": 0, "predictions": 1170}
data\v2.jsonl:240:{"tick": 1170, "t": "06:04:19", "acc": 0.53, "entropy": 0.9915, "ret": -0.010884, "capital": 9891.16, "trades": 422, "positions": 2, "exposure": 0.02, "predictions": 1190}
data\v2.jsonl:241:{"tick": 1175, "t": "06:09:22", "acc": 0.52, "entropy": 0.9904, "ret": -0.011149, "capital": 9888.51, "trades": 425, "positions": 2, "exposure": 0.02, "predictions": 1210}
data\v2.jsonl:242:{"tick": 1180, "t": "06:14:24", "acc": 0.52, "entropy": 0.9892, "ret": -0.011259, "capital": 9887.41, "trades": 427, "positions": 2, "exposure": 0.02, "predictions": 1230}
data\v2.jsonl:243:{"tick": 1185, "t": "06:19:27", "acc": 0.52, "entropy": 0.989, "ret": -0.011185, "capital": 9888.15, "trades": 429, "positions": 2, "exposure": 0.02, "predictions": 1250}
data\v2.jsonl:244:{"tick": 1190, "t": "06:24:29", "acc": 0.52, "entropy": 0.991, "ret": -0.011352, "capital": 9886.48, "trades": 431, "positions": 0, "exposure": 0, "predictions": 1270}
data\v2.jsonl:245:{"tick": 1195, "t": "06:29:34", "acc": 0.51, "entropy": 0.9923, "ret": -0.011341, "capital": 9886.59, "trades": 433, "positions": 0, "exposure": 0, "predictions": 1290}
data\v2.jsonl:246:{"tick": 1200, "t": "06:34:36", "acc": 0.52, "entropy": 0.9906, "ret": -0.011341, "capital": 9886.59, "trades": 433, "positions": 0, "exposure": 0, "predictions": 1310}
data\v2.jsonl:247:{"tick": 1205, "t": "06:39:40", "acc": 0.5, "entropy": 0.9911, "ret": -0.011402, "capital": 9885.98, "trades": 434, "positions": 0, "exposure": 0, "predictions": 1330}
data\v2.jsonl:248:{"tick": 1210, "t": "06:44:42", "acc": 0.495, "entropy": 0.9893, "ret": -0.011487, "capital": 9885.13, "trades": 436, "positions": 0, "exposure": 0, "predictions": 1350}
data\v2.jsonl:249:{"tick": 1215, "t": "06:49:44", "acc": 0.475, "entropy": 0.9906, "ret": -0.011487, "capital": 9885.13, "trades": 436, "positions": 0, "exposure": 0, "predictions": 1370}
data\v2.jsonl:250:{"tick": 1220, "t": "06:54:46", "acc": 0.465, "entropy": 0.9885, "ret": -0.011487, "capital": 9885.13, "trades": 436, "positions": 0, "exposure": 0, "predictions": 1390}
data\v2.jsonl:251:{"tick": 1225, "t": "06:59:48", "acc": 0.48, "entropy": 0.9867, "ret": -0.011638, "capital": 9883.62, "trades": 438, "positions": 2, "exposure": 0.02, "predictions": 1410}
data\v2.jsonl:252:{"tick": 1230, "t": "07:04:50", "acc": 0.49, "entropy": 0.9913, "ret": -0.01168, "capital": 9883.2, "trades": 441, "positions": 1, "exposure": 0.01, "predictions": 1430}
data\v2.jsonl:253:{"tick": 1235, "t": "07:09:53", "acc": 0.49, "entropy": 0.9947, "ret": -0.011833, "capital": 9881.67, "trades": 443, "positions": 1, "exposure": 0.01, "predictions": 1450}
data\v2.jsonl:254:{"tick": 1240, "t": "07:14:55", "acc": 0.485, "entropy": 0.9949, "ret": -0.012202, "capital": 9877.98, "trades": 445, "positions": 4, "exposure": 0.04, "predictions": 1470}
data\v2.jsonl:255:{"tick": 1245, "t": "07:19:57", "acc": 0.47, "entropy": 0.9906, "ret": -0.014762, "capital": 9852.38, "trades": 450, "positions": 1, "exposure": 0.01, "predictions": 1490}
data\v2.jsonl:256:{"tick": 1250, "t": "07:25:15", "acc": 0.485, "entropy": 0.9905, "ret": -0.014806, "capital": 9851.94, "trades": 452, "positions": 4, "exposure": 0.04, "predictions": 1510}
data\v2.jsonl:257:{"tick": 1255, "t": "07:30:17", "acc": 0.51, "entropy": 0.9892, "ret": -0.015218, "capital": 9847.82, "trades": 456, "positions": 1, "exposure": 0.01, "predictions": 1530}
data\v2.jsonl:258:{"tick": 1260, "t": "07:35:19", "acc": 0.505, "entropy": 0.9891, "ret": -0.01521, "capital": 9847.9, "trades": 457, "positions": 3, "exposure": 0.03, "predictions": 1550}
data\v2.jsonl:259:{"tick": 1265, "t": "07:40:21", "acc": 0.525, "entropy": 0.99, "ret": -0.015144, "capital": 9848.56, "trades": 462, "positions": 1, "exposure": 0.01, "predictions": 1570}
data\v2.jsonl:260:{"tick": 1270, "t": "07:45:23", "acc": 0.545, "entropy": 0.991, "ret": -0.015288, "capital": 9847.12, "trades": 463, "positions": 1, "exposure": 0.01, "predictions": 1590}
data\v2.jsonl:261:{"tick": 1275, "t": "07:50:25", "acc": 0.535, "entropy": 0.9928, "ret": -0.015578, "capital": 9844.22, "trades": 466, "positions": 1, "exposure": 0.01, "predictions": 1610}
data\v2.jsonl:262:{"tick": 1280, "t": "07:55:27", "acc": 0.525, "entropy": 0.9917, "ret": -0.016047, "capital": 9839.53, "trades": 470, "positions": 0, "exposure": 0, "predictions": 1630}
data\v2.jsonl:263:{"tick": 1285, "t": "08:00:29", "acc": 0.535, "entropy": 0.9937, "ret": -0.016047, "capital": 9839.53, "trades": 470, "positions": 2, "exposure": 0.02, "predictions": 1649}
data\v2.jsonl:264:{"tick": 1290, "t": "08:05:31", "acc": 0.545, "entropy": 0.993, "ret": -0.016053, "capital": 9839.47, "trades": 473, "positions": 2, "exposure": 0.02, "predictions": 1669}
data\v2.jsonl:265:{"tick": 1295, "t": "08:10:34", "acc": 0.54, "entropy": 0.9889, "ret": -0.016235, "capital": 9837.65, "trades": 475, "positions": 2, "exposure": 0.02, "predictions": 1689}
data\v2.jsonl:266:{"tick": 1300, "t": "08:15:35", "acc": 0.535, "entropy": 0.9922, "ret": -0.016673, "capital": 9833.27, "trades": 477, "positions": 2, "exposure": 0.02, "predictions": 1709}
data\v2.jsonl:267:{"tick": 1305, "t": "08:20:38", "acc": 0.535, "entropy": 0.9913, "ret": -0.017042, "capital": 9829.58, "trades": 479, "positions": 2, "exposure": 0.02, "predictions": 1729}
data\v2.jsonl:268:{"tick": 1310, "t": "08:25:40", "acc": 0.535, "entropy": 0.9924, "ret": -0.016683, "capital": 9833.17, "trades": 482, "positions": 1, "exposure": 0.01, "predictions": 1749}
data\v2.jsonl:269:{"tick": 1315, "t": "08:30:42", "acc": 0.53, "entropy": 0.993, "ret": -0.016704, "capital": 9832.96, "trades": 483, "positions": 0, "exposure": 0, "predictions": 1769}
data\v2.jsonl:270:{"tick": 1320, "t": "08:35:44", "acc": 0.5, "entropy": 0.9916, "ret": -0.016707, "capital": 9832.93, "trades": 484, "positions": 2, "exposure": 0.02, "predictions": 1789}
data\v2.jsonl:271:{"tick": 1325, "t": "08:40:47", "acc": 0.505, "entropy": 0.9886, "ret": -0.017098, "capital": 9829.02, "trades": 488, "positions": 2, "exposure": 0.02, "predictions": 1809}
data\v2.jsonl:272:{"tick": 1330, "t": "08:45:49", "acc": 0.51, "entropy": 0.99, "ret": -0.017116, "capital": 9828.84, "trades": 491, "positions": 2, "exposure": 0.02, "predictions": 1829}
data\v2.jsonl:273:{"tick": 1335, "t": "08:50:51", "acc": 0.485, "entropy": 0.9874, "ret": -0.017291, "capital": 9827.09, "trades": 494, "positions": 0, "exposure": 0, "predictions": 1849}
data\v2.jsonl:274:{"tick": 1340, "t": "08:55:52", "acc": 0.5, "entropy": 0.9889, "ret": -0.017171, "capital": 9828.29, "trades": 497, "positions": 1, "exposure": 0.01, "predictions": 1869}
data\v2.jsonl:275:{"tick": 1345, "t": "09:00:55", "acc": 0.49, "entropy": 0.9901, "ret": -0.01718, "capital": 9828.2, "trades": 499, "positions": 1, "exposure": 0.01, "predictions": 1889}
data\v2.jsonl:276:{"tick": 1350, "t": "09:05:57", "acc": 0.48, "entropy": 0.9902, "ret": -0.017465, "capital": 9825.35, "trades": 503, "positions": 2, "exposure": 0.02, "predictions": 1909}
data\v2.jsonl:277:{"tick": 1355, "t": "09:10:59", "acc": 0.47, "entropy": 0.9934, "ret": -0.017312, "capital": 9826.88, "trades": 507, "positions": 0, "exposure": 0, "predictions": 1929}
data\v2.jsonl:278:{"tick": 1360, "t": "09:16:01", "acc": 0.475, "entropy": 0.9911, "ret": -0.017727, "capital": 9822.73, "trades": 511, "positions": 0, "exposure": 0, "predictions": 1949}
data\v2.jsonl:279:{"tick": 1365, "t": "09:21:03", "acc": 0.485, "entropy": 0.991, "ret": -0.017727, "capital": 9822.73, "trades": 511, "positions": 1, "exposure": 0.01, "predictions": 1969}
data\v2.jsonl:280:{"tick": 1370, "t": "09:26:05", "acc": 0.51, "entropy": 0.9928, "ret": -0.017991, "capital": 9820.09, "trades": 513, "positions": 3, "exposure": 0.03, "predictions": 1989}
data\v2.jsonl:281:{"tick": 1375, "t": "09:31:08", "acc": 0.48, "entropy": 0.9928, "ret": -0.017972, "capital": 9820.28, "trades": 515, "positions": 1, "exposure": 0.01, "predictions": 2009}
data\v2.jsonl:282:{"tick": 1380, "t": "09:36:10", "acc": 0.46, "entropy": 0.9922, "ret": -0.017833, "capital": 9821.67, "trades": 518, "positions": 1, "exposure": 0.01, "predictions": 2029}
data\v2.jsonl:283:{"tick": 1385, "t": "09:41:14", "acc": 0.465, "entropy": 0.9925, "ret": -0.017849, "capital": 9821.51, "trades": 521, "positions": 2, "exposure": 0.02, "predictions": 2049}
data\v2.jsonl:284:{"tick": 1390, "t": "09:46:15", "acc": 0.44, "entropy": 0.9912, "ret": -0.017818, "capital": 9821.82, "trades": 525, "positions": 0, "exposure": 0, "predictions": 2069}
data\v2.jsonl:285:{"tick": 1395, "t": "09:51:18", "acc": 0.45, "entropy": 0.9908, "ret": -0.017931, "capital": 9820.69, "trades": 526, "positions": 1, "exposure": 0.01, "predictions": 2089}
data\v2.jsonl:286:{"tick": 1400, "t": "09:56:20", "acc": 0.45, "entropy": 0.9914, "ret": -0.017798, "capital": 9822.02, "trades": 528, "positions": 1, "exposure": 0.01, "predictions": 2109}
data\v2.jsonl:287:{"tick": 1405, "t": "10:01:22", "acc": 0.45, "entropy": 0.9878, "ret": -0.017849, "capital": 9821.51, "trades": 529, "positions": 0, "exposure": 0, "predictions": 2129}
data\v2.jsonl:288:{"tick": 1410, "t": "10:06:24", "acc": 0.46, "entropy": 0.9926, "ret": -0.017849, "capital": 9821.51, "trades": 529, "positions": 1, "exposure": 0.01, "predictions": 2149}
data\v2.jsonl:289:{"tick": 1415, "t": "10:11:26", "acc": 0.46, "entropy": 0.9893, "ret": -0.017744, "capital": 9822.56, "trades": 531, "positions": 2, "exposure": 0.02, "predictions": 2169}
data\v2.jsonl:290:{"tick": 1420, "t": "10:16:28", "acc": 0.45, "entropy": 0.9906, "ret": -0.018513, "capital": 9814.87, "trades": 536, "positions": 2, "exposure": 0.02, "predictions": 2189}
data\v2.jsonl:291:{"tick": 1425, "t": "10:21:30", "acc": 0.485, "entropy": 0.9896, "ret": -0.018023, "capital": 9819.77, "trades": 538, "positions": 1, "exposure": 0.01, "predictions": 2209}
data\v2.jsonl:292:{"tick": 1430, "t": "10:26:32", "acc": 0.5, "entropy": 0.9948, "ret": -0.017969, "capital": 9820.31, "trades": 539, "positions": 2, "exposure": 0.02, "predictions": 2229}
data\v2.jsonl:293:{"tick": 1435, "t": "10:31:34", "acc": 0.52, "entropy": 0.9931, "ret": -0.018552, "capital": 9814.48, "trades": 543, "positions": 1, "exposure": 0.01, "predictions": 2249}
data\v2.jsonl:294:{"tick": 1440, "t": "10:36:36", "acc": 0.525, "entropy": 0.9949, "ret": -0.018727, "capital": 9812.73, "trades": 545, "positions": 2, "exposure": 0.02, "predictions": 2269}
data\v2.jsonl:295:{"tick": 1445, "t": "10:41:39", "acc": 0.54, "entropy": 0.9934, "ret": -0.018421, "capital": 9815.79, "trades": 547, "positions": 2, "exposure": 0.02, "predictions": 2288}
data\v2.jsonl:296:{"tick": 1450, "t": "10:46:41", "acc": 0.56, "entropy": 0.9929, "ret": -0.017803, "capital": 9821.97, "trades": 548, "positions": 3, "exposure": 0.03, "predictions": 2308}
data\v2.jsonl:297:{"tick": 1455, "t": "10:51:43", "acc": 0.57, "entropy": 0.9886, "ret": -0.017354, "capital": 9826.46, "trades": 552, "positions": 2, "exposure": 0.02, "predictions": 2328}
data\v2.jsonl:298:{"tick": 1460, "t": "10:56:45", "acc": 0.54, "entropy": 0.9866, "ret": -0.017549, "capital": 9824.51, "trades": 557, "positions": 1, "exposure": 0.01, "predictions": 2348}
data\v2.jsonl:299:{"tick": 1465, "t": "11:01:47", "acc": 0.525, "entropy": 0.9853, "ret": -0.017466, "capital": 9825.34, "trades": 558, "positions": 3, "exposure": 0.03, "predictions": 2368}
data\v2.jsonl:300:{"tick": 1470, "t": "11:06:49", "acc": 0.515, "entropy": 0.9871, "ret": -0.017466, "capital": 9825.34, "trades": 558, "positions": 3, "exposure": 0.03, "predictions": 2388}
data\v2.jsonl:301:{"tick": 1475, "t": "11:11:51", "acc": 0.515, "entropy": 0.99, "ret": -0.018401, "capital": 9815.99, "trades": 562, "positions": 2, "exposure": 0.02, "predictions": 2408}
data\v2.jsonl:302:{"tick": 1480, "t": "11:16:54", "acc": 0.505, "entropy": 0.9883, "ret": -0.01778, "capital": 9822.2, "trades": 565, "positions": 1, "exposure": 0.01, "predictions": 2428}
data\v2.jsonl:303:{"tick": 1485, "t": "11:21:56", "acc": 0.47, "entropy": 0.99, "ret": -0.018131, "capital": 9818.69, "trades": 567, "positions": 1, "exposure": 0.01, "predictions": 2448}
data\v2.jsonl:304:{"tick": 1490, "t": "11:26:58", "acc": 0.45, "entropy": 0.9911, "ret": -0.018519, "capital": 9814.81, "trades": 571, "positions": 1, "exposure": 0.01, "predictions": 2468}
data\v2.jsonl:305:{"tick": 1495, "t": "11:32:00", "acc": 0.43, "entropy": 0.9945, "ret": -0.018567, "capital": 9814.33, "trades": 573, "positions": 2, "exposure": 0.02, "predictions": 2488}
data\v2.jsonl:306:{"tick": 1500, "t": "11:37:02", "acc": 0.41, "entropy": 0.9924, "ret": -0.0186, "capital": 9814.0, "trades": 575, "positions": 0, "exposure": 0, "predictions": 2508}
data\v2.jsonl:307:{"tick": 1505, "t": "11:42:05", "acc": 0.41, "entropy": 0.9943, "ret": -0.018622, "capital": 9813.78, "trades": 576, "positions": 1, "exposure": 0.01, "predictions": 2528}
data\v2.jsonl:308:{"tick": 1510, "t": "11:47:07", "acc": 0.42, "entropy": 0.9961, "ret": -0.018838, "capital": 9811.62, "trades": 580, "positions": 4, "exposure": 0.04, "predictions": 2548}
data\v2.jsonl:309:{"tick": 1515, "t": "11:52:10", "acc": 0.415, "entropy": 0.992, "ret": -0.019252, "capital": 9807.48, "trades": 584, "positions": 1, "exposure": 0.01, "predictions": 2568}
data\v2.jsonl:310:{"tick": 1520, "t": "11:57:12", "acc": 0.415, "entropy": 0.991, "ret": -0.019976, "capital": 9800.24, "trades": 586, "positions": 2, "exposure": 0.02, "predictions": 2588}
data\v2.jsonl:311:{"tick": 1525, "t": "12:02:14", "acc": 0.405, "entropy": 0.9924, "ret": -0.020144, "capital": 9798.56, "trades": 590, "positions": 1, "exposure": 0.01, "predictions": 2606}
data\v2.jsonl:312:{"tick": 1530, "t": "12:07:16", "acc": 0.415, "entropy": 0.9932, "ret": -0.02012, "capital": 9798.8, "trades": 593, "positions": 1, "exposure": 0.01, "predictions": 2626}
data\v2.jsonl:313:{"tick": 1535, "t": "12:12:18", "acc": 0.445, "entropy": 0.9923, "ret": -0.019967, "capital": 9800.33, "trades": 595, "positions": 2, "exposure": 0.02, "predictions": 2646}
data\v2.jsonl:314:{"tick": 1540, "t": "12:17:20", "acc": 0.47, "entropy": 0.9937, "ret": -0.020356, "capital": 9796.44, "trades": 598, "positions": 2, "exposure": 0.02, "predictions": 2666}
data\v2.jsonl:315:{"tick": 1545, "t": "12:22:23", "acc": 0.485, "entropy": 0.9943, "ret": -0.020518, "capital": 9794.82, "trades": 602, "positions": 0, "exposure": 0, "predictions": 2686}
data\v2.jsonl:316:{"tick": 1550, "t": "12:27:25", "acc": 0.49, "entropy": 0.9908, "ret": -0.020507, "capital": 9794.93, "trades": 603, "positions": 1, "exposure": 0.01, "predictions": 2706}
data\v2.jsonl:317:{"tick": 1555, "t": "12:32:27", "acc": 0.485, "entropy": 0.9939, "ret": -0.02062, "capital": 9793.8, "trades": 605, "positions": 0, "exposure": 0, "predictions": 2726}
data\v2.jsonl:318:{"tick": 1560, "t": "12:37:29", "acc": 0.515, "entropy": 0.9925, "ret": -0.020546, "capital": 9794.54, "trades": 606, "positions": 1, "exposure": 0.01, "predictions": 2746}
data\v2.jsonl:319:{"tick": 1565, "t": "12:42:31", "acc": 0.535, "entropy": 0.9921, "ret": -0.020732, "capital": 9792.68, "trades": 609, "positions": 1, "exposure": 0.01, "predictions": 2766}
data\v2.jsonl:320:{"tick": 1570, "t": "12:47:33", "acc": 0.535, "entropy": 0.9935, "ret": -0.020866, "capital": 9791.34, "trades": 611, "positions": 2, "exposure": 0.02, "predictions": 2786}
data\v2.jsonl:321:{"tick": 1575, "t": "12:52:36", "acc": 0.53, "entropy": 0.9958, "ret": -0.020703, "capital": 9792.97, "trades": 613, "positions": 1, "exposure": 0.01, "predictions": 2806}
data\v2.jsonl:322:{"tick": 1580, "t": "12:57:38", "acc": 0.5, "entropy": 0.9926, "ret": -0.02088, "capital": 9791.2, "trades": 616, "positions": 1, "exposure": 0.01, "predictions": 2826}
data\v2.jsonl:323:{"tick": 1585, "t": "13:02:40", "acc": 0.485, "entropy": 0.9901, "ret": -0.021124, "capital": 9788.76, "trades": 619, "positions": 2, "exposure": 0.02, "predictions": 2846}
data\v2.jsonl:324:{"tick": 1590, "t": "13:07:42", "acc": 0.48, "entropy": 0.9894, "ret": -0.020935, "capital": 9790.65, "trades": 623, "positions": 2, "exposure": 0.02, "predictions": 2866}
data\v2.jsonl:325:{"tick": 1595, "t": "13:12:45", "acc": 0.49, "entropy": 0.9912, "ret": -0.020941, "capital": 9790.59, "trades": 624, "positions": 1, "exposure": 0.01, "predictions": 2886}
data\v2.jsonl:326:{"tick": 1600, "t": "13:17:47", "acc": 0.48, "entropy": 0.9888, "ret": -0.020689, "capital": 9793.11, "trades": 628, "positions": 1, "exposure": 0.01, "predictions": 2906}
data\v2.jsonl:327:{"tick": 1605, "t": "13:22:49", "acc": 0.485, "entropy": 0.9919, "ret": -0.020737, "capital": 9792.63, "trades": 629, "positions": 2, "exposure": 0.02, "predictions": 2926}
data\v2.jsonl:328:{"tick": 1610, "t": "13:27:51", "acc": 0.46, "entropy": 0.9886, "ret": -0.02087, "capital": 9791.3, "trades": 632, "positions": 3, "exposure": 0.03, "predictions": 2946}
data\v2.jsonl:329:{"tick": 1615, "t": "13:32:54", "acc": 0.465, "entropy": 0.9893, "ret": -0.021296, "capital": 9787.04, "trades": 636, "positions": 2, "exposure": 0.02, "predictions": 2966}
data\v2.jsonl:330:{"tick": 1620, "t": "13:37:56", "acc": 0.48, "entropy": 0.991, "ret": -0.020954, "capital": 9790.46, "trades": 638, "positions": 2, "exposure": 0.02, "predictions": 2986}
data\v2.jsonl:331:{"tick": 1625, "t": "13:42:58", "acc": 0.49, "entropy": 0.9908, "ret": -0.021359, "capital": 9786.41, "trades": 642, "positions": 4, "exposure": 0.04, "predictions": 3006}
data\v2.jsonl:332:{"tick": 1630, "t": "13:48:00", "acc": 0.515, "entropy": 0.9916, "ret": -0.021449, "capital": 9785.51, "trades": 649, "positions": 0, "exposure": 0, "predictions": 3026}
data\v2.jsonl:333:{"tick": 1635, "t": "13:53:02", "acc": 0.51, "entropy": 0.9911, "ret": -0.021575, "capital": 9784.25, "trades": 650, "positions": 2, "exposure": 0.02, "predictions": 3046}
data\v2.jsonl:334:{"tick": 1640, "t": "13:58:13", "acc": 0.505, "entropy": 0.9914, "ret": -0.02155, "capital": 9784.5, "trades": 654, "positions": 2, "exposure": 0.02, "predictions": 3066}
data\v2.jsonl:335:{"tick": 1645, "t": "14:03:18", "acc": 0.505, "entropy": 0.9884, "ret": -0.020944, "capital": 9790.56, "trades": 656, "positions": 2, "exposure": 0.02, "predictions": 3086}
data\v2.jsonl:336:{"tick": 1650, "t": "14:08:22", "acc": 0.525, "entropy": 0.99, "ret": -0.021059, "capital": 9789.41, "trades": 658, "positions": 2, "exposure": 0.02, "predictions": 3105}
data\v2.jsonl:337:{"tick": 1655, "t": "14:13:27", "acc": 0.55, "entropy": 0.9884, "ret": -0.021688, "capital": 9783.12, "trades": 660, "positions": 4, "exposure": 0.04, "predictions": 3125}
data\v2.jsonl:338:{"tick": 1660, "t": "14:18:32", "acc": 0.555, "entropy": 0.9932, "ret": -0.022062, "capital": 9779.38, "trades": 664, "positions": 2, "exposure": 0.02, "predictions": 3145}
data\v2.jsonl:339:{"tick": 1665, "t": "14:23:37", "acc": 0.545, "entropy": 0.9914, "ret": -0.022108, "capital": 9778.92, "trades": 666, "positions": 2, "exposure": 0.02, "predictions": 3165}
data\v2.jsonl:340:{"tick": 1670, "t": "14:28:42", "acc": 0.555, "entropy": 0.992, "ret": -0.020762, "capital": 9792.38, "trades": 670, "positions": 1, "exposure": 0.01, "predictions": 3185}
data\v2.jsonl:341:{"tick": 1675, "t": "14:33:48", "acc": 0.56, "entropy": 0.9907, "ret": -0.021333, "capital": 9786.67, "trades": 673, "positions": 2, "exposure": 0.02, "predictions": 3205}
data\v2.jsonl:342:{"tick": 1680, "t": "14:38:51", "acc": 0.565, "entropy": 0.9903, "ret": -0.023402, "capital": 9765.98, "trades": 675, "positions": 3, "exposure": 0.03, "predictions": 3225}
data\v2.jsonl:343:{"tick": 1685, "t": "14:43:54", "acc": 0.59, "entropy": 0.9918, "ret": -0.021208, "capital": 9787.92, "trades": 679, "positions": 2, "exposure": 0.02, "predictions": 3245}
data\v2.jsonl:344:{"tick": 1690, "t": "14:48:56", "acc": 0.605, "entropy": 0.9892, "ret": -0.020759, "capital": 9792.41, "trades": 682, "positions": 0, "exposure": 0, "predictions": 3265}
data\v2.jsonl:345:{"tick": 1695, "t": "14:53:58", "acc": 0.59, "entropy": 0.9881, "ret": -0.021163, "capital": 9788.37, "trades": 683, "positions": 0, "exposure": 0, "predictions": 3285}
data\v2.jsonl:346:{"tick": 1700, "t": "14:59:00", "acc": 0.575, "entropy": 0.9896, "ret": -0.021281, "capital": 9787.19, "trades": 684, "positions": 0, "exposure": 0, "predictions": 3305}
data\v2.jsonl:347:{"tick": 1705, "t": "15:04:02", "acc": 0.565, "entropy": 0.9877, "ret": -0.021456, "capital": 9785.44, "trades": 686, "positions": 0, "exposure": 0, "predictions": 3325}
data\v2.jsonl:348:{"tick": 1710, "t": "15:09:04", "acc": 0.56, "entropy": 0.9889, "ret": -0.021628, "capital": 9783.72, "trades": 688, "positions": 2, "exposure": 0.02, "predictions": 3345}
data\v2.jsonl:349:{"tick": 1715, "t": "15:14:07", "acc": 0.55, "entropy": 0.9894, "ret": -0.021674, "capital": 9783.26, "trades": 693, "positions": 1, "exposure": 0.01, "predictions": 3365}
data\v2.jsonl:350:{"tick": 1720, "t": "15:19:09", "acc": 0.54, "entropy": 0.9919, "ret": -0.021043, "capital": 9789.57, "trades": 695, "positions": 2, "exposure": 0.02, "predictions": 3385}
data\v2.jsonl:351:{"tick": 1725, "t": "15:24:11", "acc": 0.545, "entropy": 0.992, "ret": -0.021167, "capital": 9788.33, "trades": 698, "positions": 3, "exposure": 0.03, "predictions": 3405}
data\v2.jsonl:352:{"tick": 1730, "t": "15:29:13", "acc": 0.54, "entropy": 0.9923, "ret": -0.020086, "capital": 9799.14, "trades": 703, "positions": 2, "exposure": 0.02, "predictions": 3425}
data\v2.jsonl:353:{"tick": 1735, "t": "15:34:15", "acc": 0.535, "entropy": 0.9916, "ret": -0.022365, "capital": 9776.35, "trades": 708, "positions": 1, "exposure": 0.01, "predictions": 3445}
data\v2.jsonl:354:{"tick": 1740, "t": "15:39:17", "acc": 0.53, "entropy": 0.9871, "ret": -0.021979, "capital": 9780.21, "trades": 711, "positions": 2, "exposure": 0.02, "predictions": 3465}
data\v2.jsonl:355:{"tick": 1745, "t": "15:44:20", "acc": 0.53, "entropy": 0.9897, "ret": -0.022177, "capital": 9778.23, "trades": 712, "positions": 2, "exposure": 0.02, "predictions": 3485}
data\v2.jsonl:356:{"tick": 1750, "t": "15:49:22", "acc": 0.525, "entropy": 0.9927, "ret": -0.023412, "capital": 9765.88, "trades": 718, "positions": 1, "exposure": 0.01, "predictions": 3505}
data\v2.jsonl:357:{"tick": 1755, "t": "15:54:24", "acc": 0.51, "entropy": 0.9922, "ret": -0.023253, "capital": 9767.47, "trades": 720, "positions": 2, "exposure": 0.02, "predictions": 3525}
data\v2.jsonl:358:{"tick": 1760, "t": "15:59:26", "acc": 0.52, "entropy": 0.9922, "ret": -0.023493, "capital": 9765.07, "trades": 722, "positions": 2, "exposure": 0.02, "predictions": 3545}
data\v2.jsonl:359:{"tick": 1765, "t": "16:04:28", "acc": 0.51, "entropy": 0.993, "ret": -0.024365, "capital": 9756.35, "trades": 725, "positions": 2, "exposure": 0.02, "predictions": 3565}
data\v2.jsonl:360:{"tick": 1770, "t": "16:09:30", "acc": 0.505, "entropy": 0.9925, "ret": -0.024389, "capital": 9756.11, "trades": 726, "positions": 2, "exposure": 0.02, "predictions": 3585}
data\v2.jsonl:361:{"tick": 1775, "t": "16:14:32", "acc": 0.48, "entropy": 0.9886, "ret": -0.024459, "capital": 9755.41, "trades": 728, "positions": 3, "exposure": 0.03, "predictions": 3605}
data\v2.jsonl:362:{"tick": 1780, "t": "16:19:34", "acc": 0.475, "entropy": 0.9904, "ret": -0.025342, "capital": 9746.58, "trades": 731, "positions": 2, "exposure": 0.02, "predictions": 3625}
data\v2.jsonl:363:{"tick": 1785, "t": "16:24:36", "acc": 0.455, "entropy": 0.9918, "ret": -0.024016, "capital": 9759.84, "trades": 734, "positions": 1, "exposure": 0.01, "predictions": 3645}
data\v2.jsonl:364:{"tick": 1790, "t": "16:29:38", "acc": 0.475, "entropy": 0.994, "ret": -0.024184, "capital": 9758.16, "trades": 736, "positions": 1, "exposure": 0.01, "predictions": 3665}
data\v2.jsonl:365:{"tick": 1795, "t": "16:34:40", "acc": 0.485, "entropy": 0.9927, "ret": -0.023851, "capital": 9761.49, "trades": 738, "positions": 3, "exposure": 0.03, "predictions": 3685}
data\v2.jsonl:366:{"tick": 1800, "t": "16:39:42", "acc": 0.495, "entropy": 0.9926, "ret": -0.02418, "capital": 9758.2, "trades": 741, "positions": 1, "exposure": 0.01, "predictions": 3705}
data\v2.jsonl:367:{"tick": 1805, "t": "16:44:44", "acc": 0.505, "entropy": 0.9933, "ret": -0.023975, "capital": 9760.25, "trades": 743, "positions": 2, "exposure": 0.02, "predictions": 3725}
data\v2.jsonl:368:{"tick": 1810, "t": "16:49:47", "acc": 0.49, "entropy": 0.9937, "ret": -0.023366, "capital": 9766.34, "trades": 747, "positions": 1, "exposure": 0.01, "predictions": 3745}
data\v2.jsonl:369:{"tick": 1815, "t": "16:54:48", "acc": 0.495, "entropy": 0.9926, "ret": -0.023824, "capital": 9761.76, "trades": 749, "positions": 1, "exposure": 0.01, "predictions": 3765}
data\v2.jsonl:370:{"tick": 1820, "t": "16:59:50", "acc": 0.51, "entropy": 0.9912, "ret": -0.023716, "capital": 9762.84, "trades": 751, "positions": 1, "exposure": 0.01, "predictions": 3785}
data\v2.jsonl:371:{"tick": 1825, "t": "17:04:52", "acc": 0.505, "entropy": 0.9923, "ret": -0.023636, "capital": 9763.64, "trades": 754, "positions": 1, "exposure": 0.01, "predictions": 3805}
data\v2.jsonl:372:{"tick": 1830, "t": "17:09:54", "acc": 0.49, "entropy": 0.992, "ret": -0.024061, "capital": 9759.39, "trades": 756, "positions": 1, "exposure": 0.01, "predictions": 3825}
data\v2.jsonl:373:{"tick": 1835, "t": "17:14:57", "acc": 0.525, "entropy": 0.9911, "ret": -0.023651, "capital": 9763.49, "trades": 758, "positions": 0, "exposure": 0, "predictions": 3845}
data\v2.jsonl:374:{"tick": 1840, "t": "17:19:59", "acc": 0.525, "entropy": 0.9927, "ret": -0.023651, "capital": 9763.49, "trades": 758, "positions": 1, "exposure": 0.01, "predictions": 3865}
data\v2.jsonl:375:{"tick": 1845, "t": "17:25:01", "acc": 0.53, "entropy": 0.9923, "ret": -0.023485, "capital": 9765.15, "trades": 760, "positions": 1, "exposure": 0.01, "predictions": 3885}
data\v2.jsonl:376:{"tick": 1850, "t": "17:30:03", "acc": 0.495, "entropy": 0.993, "ret": -0.023343, "capital": 9766.57, "trades": 762, "positions": 2, "exposure": 0.02, "predictions": 3905}
data\v2.jsonl:377:{"tick": 1855, "t": "17:35:05", "acc": 0.5, "entropy": 0.9923, "ret": -0.02357, "capital": 9764.3, "trades": 765, "positions": 0, "exposure": 0, "predictions": 3925}
data\v2.jsonl:378:{"tick": 1860, "t": "17:40:07", "acc": 0.5, "entropy": 0.9913, "ret": -0.023336, "capital": 9766.64, "trades": 767, "positions": 1, "exposure": 0.01, "predictions": 3945}
data\v2.jsonl:379:{"tick": 1865, "t": "17:45:09", "acc": 0.52, "entropy": 0.9918, "ret": -0.02395, "capital": 9760.5, "trades": 771, "positions": 2, "exposure": 0.02, "predictions": 3965}
data\v2.jsonl:380:{"tick": 1870, "t": "17:50:11", "acc": 0.5, "entropy": 0.9928, "ret": -0.023857, "capital": 9761.43, "trades": 775, "positions": 0, "exposure": 0, "predictions": 3985}
data\v2.jsonl:381:{"tick": 1875, "t": "17:55:13", "acc": 0.52, "entropy": 0.9944, "ret": -0.023677, "capital": 9763.23, "trades": 777, "positions": 2, "exposure": 0.02, "predictions": 4005}
data\v2.jsonl:382:{"tick": 1880, "t": "18:00:15", "acc": 0.545, "entropy": 0.9929, "ret": -0.0241, "capital": 9759.0, "trades": 780, "positions": 1, "exposure": 0.01, "predictions": 4024}
data\v2.jsonl:383:{"tick": 1885, "t": "18:05:17", "acc": 0.535, "entropy": 0.9941, "ret": -0.02394, "capital": 9760.6, "trades": 783, "positions": 1, "exposure": 0.01, "predictions": 4044}
data\v2.jsonl:384:{"tick": 1890, "t": "18:10:19", "acc": 0.52, "entropy": 0.9935, "ret": -0.023123, "capital": 9768.77, "trades": 785, "positions": 0, "exposure": 0, "predictions": 4064}
data\v2.jsonl:385:{"tick": 1895, "t": "18:15:21", "acc": 0.525, "entropy": 0.9953, "ret": -0.023061, "capital": 9769.39, "trades": 787, "positions": 3, "exposure": 0.03, "predictions": 4084}
data\v2.jsonl:386:{"tick": 1900, "t": "18:20:24", "acc": 0.545, "entropy": 0.9919, "ret": -0.023439, "capital": 9765.61, "trades": 790, "positions": 2, "exposure": 0.02, "predictions": 4104}
data\v2.jsonl:387:{"tick": 1905, "t": "18:25:25", "acc": 0.53, "entropy": 0.9924, "ret": -0.023516, "capital": 9764.84, "trades": 794, "positions": 1, "exposure": 0.01, "predictions": 4124}
data\v2.jsonl:388:{"tick": 1910, "t": "18:30:27", "acc": 0.54, "entropy": 0.99, "ret": -0.023337, "capital": 9766.63, "trades": 795, "positions": 2, "exposure": 0.02, "predictions": 4144}
data\v2.jsonl:389:{"tick": 1915, "t": "18:35:30", "acc": 0.51, "entropy": 0.9934, "ret": -0.023368, "capital": 9766.32, "trades": 797, "positions": 0, "exposure": 0, "predictions": 4164}
data\v2.jsonl:390:{"tick": 1920, "t": "18:40:31", "acc": 0.52, "entropy": 0.9923, "ret": -0.023564, "capital": 9764.36, "trades": 799, "positions": 0, "exposure": 0, "predictions": 4184}
data\v2.jsonl:391:{"tick": 1925, "t": "18:45:34", "acc": 0.49, "entropy": 0.9905, "ret": -0.023591, "capital": 9764.09, "trades": 801, "positions": 1, "exposure": 0.01, "predictions": 4204}
data\v2.jsonl:392:{"tick": 1930, "t": "18:50:36", "acc": 0.485, "entropy": 0.9948, "ret": -0.023705, "capital": 9762.95, "trades": 802, "positions": 0, "exposure": 0, "predictions": 4224}
data\v2.jsonl:393:{"tick": 1935, "t": "18:55:38", "acc": 0.49, "entropy": 0.9944, "ret": -0.023814, "capital": 9761.86, "trades": 805, "positions": 0, "exposure": 0, "predictions": 4244}
data\v2.jsonl:394:{"tick": 1940, "t": "19:00:40", "acc": 0.48, "entropy": 0.9921, "ret": -0.023774, "capital": 9762.26, "trades": 806, "positions": 1, "exposure": 0.01, "predictions": 4264}
data\v2.jsonl:395:{"tick": 1945, "t": "19:05:42", "acc": 0.455, "entropy": 0.9922, "ret": -0.023923, "capital": 9760.77, "trades": 809, "positions": 2, "exposure": 0.02, "predictions": 4284}
data\v2.jsonl:396:{"tick": 1950, "t": "19:10:44", "acc": 0.455, "entropy": 0.9899, "ret": -0.024298, "capital": 9757.02, "trades": 813, "positions": 1, "exposure": 0.01, "predictions": 4304}
data\v2.jsonl:397:{"tick": 1955, "t": "19:15:47", "acc": 0.47, "entropy": 0.9902, "ret": -0.023593, "capital": 9764.07, "trades": 816, "positions": 1, "exposure": 0.01, "predictions": 4324}
data\v2.jsonl:398:{"tick": 1960, "t": "19:20:48", "acc": 0.46, "entropy": 0.9901, "ret": -0.02416, "capital": 9758.4, "trades": 818, "positions": 1, "exposure": 0.01, "predictions": 4344}
data\v2.jsonl:399:{"tick": 1965, "t": "19:25:51", "acc": 0.49, "entropy": 0.9925, "ret": -0.024281, "capital": 9757.19, "trades": 821, "positions": 0, "exposure": 0, "predictions": 4364}
data\v2.jsonl:400:{"tick": 1970, "t": "19:30:53", "acc": 0.465, "entropy": 0.991, "ret": -0.024191, "capital": 9758.09, "trades": 823, "positions": 2, "exposure": 0.02, "predictions": 4384}
data\v2.jsonl:401:{"tick": 1975, "t": "19:35:55", "acc": 0.46, "entropy": 0.9924, "ret": -0.025652, "capital": 9743.48, "trades": 826, "positions": 1, "exposure": 0.01, "predictions": 4404}
data\v2.jsonl:402:{"tick": 1980, "t": "19:40:58", "acc": 0.46, "entropy": 0.9942, "ret": -0.028695, "capital": 9713.05, "trades": 831, "positions": 0, "exposure": 0, "predictions": 4424}
data\v2.jsonl:403:{"tick": 1985, "t": "19:46:00", "acc": 0.435, "entropy": 0.9943, "ret": -0.029032, "capital": 9709.68, "trades": 835, "positions": 0, "exposure": 0, "predictions": 4444}
data\v2.jsonl:404:{"tick": 1990, "t": "19:51:02", "acc": 0.44, "entropy": 0.9941, "ret": -0.028957, "capital": 9710.43, "trades": 837, "positions": 2, "exposure": 0.02, "predictions": 4464}
data\v2.jsonl:405:{"tick": 1995, "t": "19:56:04", "acc": 0.46, "entropy": 0.9927, "ret": -0.029634, "capital": 9703.66, "trades": 840, "positions": 3, "exposure": 0.03, "predictions": 4484}
data\v2.jsonl:406:{"tick": 2000, "t": "20:01:06", "acc": 0.46, "entropy": 0.9922, "ret": -0.029497, "capital": 9705.03, "trades": 845, "positions": 1, "exposure": 0.01, "predictions": 4504}
data\v2.jsonl:407:{"tick": 2005, "t": "20:06:08", "acc": 0.46, "entropy": 0.9934, "ret": -0.029156, "capital": 9708.44, "trades": 849, "positions": 1, "exposure": 0.01, "predictions": 4524}
data\v2.jsonl:408:{"tick": 2010, "t": "20:11:10", "acc": 0.455, "entropy": 0.9916, "ret": -0.029147, "capital": 9708.53, "trades": 851, "positions": 0, "exposure": 0, "predictions": 4544}
data\v2.jsonl:409:{"tick": 2015, "t": "20:16:13", "acc": 0.435, "entropy": 0.9894, "ret": -0.029112, "capital": 9708.88, "trades": 854, "positions": 1, "exposure": 0.01, "predictions": 4564}
data\v2.jsonl:410:{"tick": 2020, "t": "20:21:15", "acc": 0.445, "entropy": 0.9897, "ret": -0.029189, "capital": 9708.11, "trades": 856, "positions": 1, "exposure": 0.01, "predictions": 4584}
data\v2.jsonl:411:{"tick": 2025, "t": "20:26:17", "acc": 0.465, "entropy": 0.9891, "ret": -0.028919, "capital": 9710.81, "trades": 857, "positions": 1, "exposure": 0.01, "predictions": 4604}
data\v2.jsonl:412:{"tick": 2030, "t": "20:31:19", "acc": 0.48, "entropy": 0.9923, "ret": -0.029249, "capital": 9707.51, "trades": 859, "positions": 1, "exposure": 0.01, "predictions": 4624}
data\v2.jsonl:413:{"tick": 2035, "t": "20:36:22", "acc": 0.51, "entropy": 0.9936, "ret": -0.028412, "capital": 9715.88, "trades": 862, "positions": 1, "exposure": 0.01, "predictions": 4644}
data\v2.jsonl:414:{"tick": 2040, "t": "20:41:24", "acc": 0.515, "entropy": 0.9929, "ret": -0.028571, "capital": 9714.29, "trades": 864, "positions": 0, "exposure": 0, "predictions": 4664}
data\v2.jsonl:415:{"tick": 2045, "t": "20:46:26", "acc": 0.52, "entropy": 0.996, "ret": -0.028477, "capital": 9715.23, "trades": 866, "positions": 1, "exposure": 0.01, "predictions": 4684}
data\v2.jsonl:416:{"tick": 2050, "t": "20:51:28", "acc": 0.53, "entropy": 0.9935, "ret": -0.028567, "capital": 9714.33, "trades": 868, "positions": 1, "exposure": 0.01, "predictions": 4704}
data\v2.jsonl:417:{"tick": 2055, "t": "20:56:30", "acc": 0.52, "entropy": 0.9955, "ret": -0.028726, "capital": 9712.74, "trades": 870, "positions": 1, "exposure": 0.01, "predictions": 4724}
data\v2.jsonl:418:{"tick": 2060, "t": "21:01:32", "acc": 0.525, "entropy": 0.9953, "ret": -0.028723, "capital": 9712.77, "trades": 871, "positions": 3, "exposure": 0.03, "predictions": 4744}
data\v2.jsonl:419:{"tick": 2065, "t": "21:06:34", "acc": 0.525, "entropy": 0.9922, "ret": -0.029249, "capital": 9707.51, "trades": 874, "positions": 2, "exposure": 0.02, "predictions": 4764}
data\v2.jsonl:420:{"tick": 2070, "t": "21:11:36", "acc": 0.54, "entropy": 0.991, "ret": -0.029254, "capital": 9707.46, "trades": 879, "positions": 2, "exposure": 0.02, "predictions": 4784}
data\v2.jsonl:421:{"tick": 2075, "t": "21:16:38", "acc": 0.535, "entropy": 0.9911, "ret": -0.029649, "capital": 9703.51, "trades": 883, "positions": 1, "exposure": 0.01, "predictions": 4804}
data\v2.jsonl:422:{"tick": 2080, "t": "21:21:40", "acc": 0.52, "entropy": 0.9915, "ret": -0.030114, "capital": 9698.86, "trades": 887, "positions": 2, "exposure": 0.02, "predictions": 4824}
data\v2.jsonl:423:{"tick": 2085, "t": "21:26:42", "acc": 0.505, "entropy": 0.9924, "ret": -0.030155, "capital": 9698.45, "trades": 891, "positions": 0, "exposure": 0, "predictions": 4844}
data\v2.jsonl:424:{"tick": 2090, "t": "21:31:44", "acc": 0.485, "entropy": 0.9905, "ret": -0.030155, "capital": 9698.45, "trades": 891, "positions": 2, "exposure": 0.02, "predictions": 4864}
data\v2.jsonl:425:{"tick": 2095, "t": "21:36:46", "acc": 0.47, "entropy": 0.9934, "ret": -0.030116, "capital": 9698.84, "trades": 893, "positions": 2, "exposure": 0.02, "predictions": 4884}
data\v2.jsonl:426:{"tick": 2100, "t": "21:41:48", "acc": 0.445, "entropy": 0.9908, "ret": -0.030538, "capital": 9694.62, "trades": 896, "positions": 2, "exposure": 0.02, "predictions": 4904}
data\v2.jsonl:427:{"tick": 2105, "t": "21:46:51", "acc": 0.44, "entropy": 0.9928, "ret": -0.029568, "capital": 9704.32, "trades": 899, "positions": 0, "exposure": 0, "predictions": 4924}
data\v2.jsonl:428:{"tick": 2110, "t": "21:51:53", "acc": 0.44, "entropy": 0.9942, "ret": -0.029568, "capital": 9704.32, "trades": 899, "positions": 0, "exposure": 0, "predictions": 4944}
data\v2.jsonl:429:{"tick": 2115, "t": "21:56:55", "acc": 0.45, "entropy": 0.9939, "ret": -0.02954, "capital": 9704.6, "trades": 901, "positions": 0, "exposure": 0, "predictions": 4964}
data\v2.jsonl:430:{"tick": 2120, "t": "22:01:57", "acc": 0.445, "entropy": 0.9932, "ret": -0.029561, "capital": 9704.39, "trades": 902, "positions": 3, "exposure": 0.03, "predictions": 4984}
data\v2.jsonl:431:{"tick": 2125, "t": "22:06:59", "acc": 0.47, "entropy": 0.9924, "ret": -0.029402, "capital": 9705.98, "trades": 905, "positions": 2, "exposure": 0.02, "predictions": 5004}
data\v2.jsonl:432:{"tick": 2130, "t": "22:12:01", "acc": 0.47, "entropy": 0.993, "ret": -0.028096, "capital": 9719.04, "trades": 908, "positions": 2, "exposure": 0.02, "predictions": 5024}
data\v2.jsonl:433:{"tick": 2135, "t": "22:17:03", "acc": 0.465, "entropy": 0.9927, "ret": -0.02877, "capital": 9712.3, "trades": 911, "positions": 1, "exposure": 0.01, "predictions": 5044}
data\v2.jsonl:434:{"tick": 2140, "t": "22:22:06", "acc": 0.475, "entropy": 0.994, "ret": -0.028911, "capital": 9710.89, "trades": 913, "positions": 4, "exposure": 0.04, "predictions": 5064}
data\v2.jsonl:435:{"tick": 2145, "t": "22:27:08", "acc": 0.48, "entropy": 0.9922, "ret": -0.028871, "capital": 9711.29, "trades": 914, "positions": 3, "exposure": 0.03, "predictions": 5084}
data\v2.jsonl:436:{"tick": 2150, "t": "22:32:10", "acc": 0.495, "entropy": 0.9898, "ret": -0.029416, "capital": 9705.84, "trades": 918, "positions": 2, "exposure": 0.02, "predictions": 5104}
data\v2.jsonl:437:{"tick": 2155, "t": "22:37:12", "acc": 0.51, "entropy": 0.9882, "ret": -0.029733, "capital": 9702.67, "trades": 922, "positions": 0, "exposure": 0, "predictions": 5124}
data\v2.jsonl:438:{"tick": 2160, "t": "22:42:14", "acc": 0.51, "entropy": 0.9907, "ret": -0.029049, "capital": 9709.51, "trades": 924, "positions": 3, "exposure": 0.03, "predictions": 5144}
data\v2.jsonl:439:{"tick": 2165, "t": "22:47:16", "acc": 0.495, "entropy": 0.9908, "ret": -0.02934, "capital": 9706.6, "trades": 927, "positions": 2, "exposure": 0.02, "predictions": 5162}
data\v2.jsonl:440:{"tick": 2170, "t": "22:52:19", "acc": 0.49, "entropy": 0.9921, "ret": -0.029402, "capital": 9705.98, "trades": 931, "positions": 0, "exposure": 0, "predictions": 5182}
data\v2.jsonl:441:{"tick": 2175, "t": "22:57:22", "acc": 0.485, "entropy": 0.9914, "ret": -0.030088, "capital": 9699.12, "trades": 933, "positions": 0, "exposure": 0, "predictions": 5202}
data\v2.jsonl:442:{"tick": 2180, "t": "23:02:25", "acc": 0.485, "entropy": 0.9917, "ret": -0.030702, "capital": 9692.98, "trades": 937, "positions": 1, "exposure": 0.01, "predictions": 5222}
data\v2.jsonl:443:{"tick": 2185, "t": "23:07:28", "acc": 0.49, "entropy": 0.9935, "ret": -0.030815, "capital": 9691.85, "trades": 940, "positions": 2, "exposure": 0.02, "predictions": 5242}
data\v2.jsonl:444:{"tick": 2190, "t": "23:12:31", "acc": 0.51, "entropy": 0.9934, "ret": -0.030802, "capital": 9691.98, "trades": 942, "positions": 2, "exposure": 0.02, "predictions": 5262}
data\v2.jsonl:445:{"tick": 2195, "t": "23:17:34", "acc": 0.52, "entropy": 0.9934, "ret": -0.030382, "capital": 9696.18, "trades": 946, "positions": 1, "exposure": 0.01, "predictions": 5282}
data\v2.jsonl:446:{"tick": 2200, "t": "23:22:36", "acc": 0.535, "entropy": 0.9953, "ret": -0.030435, "capital": 9695.65, "trades": 950, "positions": 1, "exposure": 0.01, "predictions": 5302}
data\v2.jsonl:447:{"tick": 2205, "t": "23:27:39", "acc": 0.54, "entropy": 0.9924, "ret": -0.030536, "capital": 9694.64, "trades": 953, "positions": 1, "exposure": 0.01, "predictions": 5322}
data\v2.jsonl:448:{"tick": 2210, "t": "23:32:42", "acc": 0.55, "entropy": 0.9938, "ret": -0.030598, "capital": 9694.02, "trades": 957, "positions": 1, "exposure": 0.01, "predictions": 5342}
data\v2.jsonl:449:{"tick": 2215, "t": "23:37:44", "acc": 0.56, "entropy": 0.9948, "ret": -0.030187, "capital": 9698.13, "trades": 960, "positions": 1, "exposure": 0.01, "predictions": 5362}
data\v2.jsonl:450:{"tick": 2220, "t": "23:42:47", "acc": 0.565, "entropy": 0.9953, "ret": -0.030374, "capital": 9696.26, "trades": 964, "positions": 2, "exposure": 0.02, "predictions": 5382}
data\v2.jsonl:451:{"tick": 2225, "t": "23:47:50", "acc": 0.57, "entropy": 0.9949, "ret": -0.03098, "capital": 9690.2, "trades": 966, "positions": 1, "exposure": 0.01, "predictions": 5402}
data\v2.jsonl:452:{"tick": 2230, "t": "23:52:52", "acc": 0.55, "entropy": 0.9919, "ret": -0.03098, "capital": 9690.2, "trades": 966, "positions": 2, "exposure": 0.02, "predictions": 5422}
data\v2.jsonl:453:{"tick": 2235, "t": "23:57:55", "acc": 0.56, "entropy": 0.9885, "ret": -0.031137, "capital": 9688.63, "trades": 968, "positions": 2, "exposure": 0.02, "predictions": 5442}
data\v2.jsonl:454:{"tick": 2240, "t": "00:02:57", "acc": 0.545, "entropy": 0.9899, "ret": -0.031192, "capital": 9688.08, "trades": 972, "positions": 1, "exposure": 0.01, "predictions": 5462}
data\v2.jsonl:455:{"tick": 2245, "t": "00:08:00", "acc": 0.545, "entropy": 0.9923, "ret": -0.030493, "capital": 9695.07, "trades": 973, "positions": 2, "exposure": 0.02, "predictions": 5482}
data\v2.jsonl:456:{"tick": 2250, "t": "00:13:03", "acc": 0.525, "entropy": 0.993, "ret": -0.030293, "capital": 9697.07, "trades": 975, "positions": 2, "exposure": 0.02, "predictions": 5502}
data\v2.jsonl:457:{"tick": 2255, "t": "00:18:05", "acc": 0.5, "entropy": 0.995, "ret": -0.030476, "capital": 9695.24, "trades": 977, "positions": 2, "exposure": 0.02, "predictions": 5522}
data\v2.jsonl:458:{"tick": 2260, "t": "00:23:08", "acc": 0.515, "entropy": 0.9944, "ret": -0.030538, "capital": 9694.62, "trades": 979, "positions": 2, "exposure": 0.02, "predictions": 5542}
data\v2.jsonl:459:{"tick": 2265, "t": "00:28:11", "acc": 0.505, "entropy": 0.9956, "ret": -0.030074, "capital": 9699.26, "trades": 983, "positions": 1, "exposure": 0.01, "predictions": 5562}
data\v2.jsonl:460:{"tick": 2270, "t": "00:33:13", "acc": 0.495, "entropy": 0.9953, "ret": -0.030182, "capital": 9698.18, "trades": 986, "positions": 2, "exposure": 0.02, "predictions": 5582}
data\v2.jsonl:461:{"tick": 2275, "t": "00:38:15", "acc": 0.51, "entropy": 0.9942, "ret": -0.030052, "capital": 9699.48, "trades": 990, "positions": 1, "exposure": 0.01, "predictions": 5602}
data\v2.jsonl:462:{"tick": 2280, "t": "00:43:17", "acc": 0.53, "entropy": 0.9954, "ret": -0.029485, "capital": 9705.15, "trades": 993, "positions": 1, "exposure": 0.01, "predictions": 5622}
data\v2.jsonl:463:{"tick": 2285, "t": "00:48:19", "acc": 0.51, "entropy": 0.9952, "ret": -0.029468, "capital": 9705.32, "trades": 994, "positions": 1, "exposure": 0.01, "predictions": 5641}
data\v2.jsonl:464:{"tick": 2290, "t": "00:53:21", "acc": 0.51, "entropy": 0.9947, "ret": -0.029438, "capital": 9705.62, "trades": 997, "positions": 1, "exposure": 0.01, "predictions": 5661}
data\v2.jsonl:465:{"tick": 2295, "t": "00:58:23", "acc": 0.52, "entropy": 0.9949, "ret": -0.029915, "capital": 9700.85, "trades": 1002, "positions": 1, "exposure": 0.01, "predictions": 5681}
data\v2.jsonl:466:{"tick": 2300, "t": "01:03:25", "acc": 0.54, "entropy": 0.993, "ret": -0.029756, "capital": 9702.44, "trades": 1004, "positions": 2, "exposure": 0.02, "predictions": 5701}
data\v2.jsonl:467:{"tick": 2305, "t": "01:08:27", "acc": 0.545, "entropy": 0.9932, "ret": -0.030135, "capital": 9698.65, "trades": 1010, "positions": 1, "exposure": 0.01, "predictions": 5721}
data\v2.jsonl:468:{"tick": 2285, "t": "01:14:15", "acc": 0.5, "entropy": 0.9938, "ret": -0.029468, "capital": 9705.32, "trades": 994, "positions": 0, "exposure": 0, "predictions": 12}
data\v2.jsonl:469:{"tick": 2290, "t": "01:19:17", "acc": 0.5, "entropy": 0.9921, "ret": -0.029482, "capital": 9705.18, "trades": 995, "positions": 3, "exposure": 0.03, "predictions": 32}
data\v2.jsonl:470:{"tick": 2295, "t": "01:24:19", "acc": 0.5769, "entropy": 0.9922, "ret": -0.029471, "capital": 9705.29, "trades": 999, "positions": 1, "exposure": 0.01, "predictions": 52}
data\v2.jsonl:471:{"tick": 2300, "t": "01:29:21", "acc": 0.5694, "entropy": 0.9914, "ret": -0.02947, "capital": 9705.3, "trades": 1001, "positions": 3, "exposure": 0.03, "predictions": 72}
data\v2.jsonl:472:{"tick": 2305, "t": "01:34:23", "acc": 0.5761, "entropy": 0.9898, "ret": -0.029419, "capital": 9705.81, "trades": 1004, "positions": 1, "exposure": 0.01, "predictions": 92}
data\v2.jsonl:473:{"tick": 2310, "t": "01:39:25", "acc": 0.5714, "entropy": 0.9875, "ret": -0.029485, "capital": 9705.15, "trades": 1007, "positions": 0, "exposure": 0, "predictions": 112}
data\v2.jsonl:474:{"tick": 2315, "t": "01:44:27", "acc": 0.5379, "entropy": 0.9876, "ret": -0.029485, "capital": 9705.15, "trades": 1007, "positions": 0, "exposure": 0, "predictions": 132}
data\v2.jsonl:475:{"tick": 2320, "t": "01:49:30", "acc": 0.5329, "entropy": 0.9912, "ret": -0.029758, "capital": 9702.42, "trades": 1009, "positions": 1, "exposure": 0.01, "predictions": 152}
data\v2.jsonl:476:{"tick": 2325, "t": "01:54:32", "acc": 0.5174, "entropy": 0.9898, "ret": -0.029753, "capital": 9702.47, "trades": 1011, "positions": 1, "exposure": 0.01, "predictions": 172}
data\v2.jsonl:477:{"tick": 2330, "t": "01:59:35", "acc": 0.5312, "entropy": 0.9918, "ret": -0.029634, "capital": 9703.66, "trades": 1014, "positions": 0, "exposure": 0, "predictions": 192}
data\v2.jsonl:478:{"tick": 2335, "t": "02:04:37", "acc": 0.55, "entropy": 0.9952, "ret": -0.029367, "capital": 9706.33, "trades": 1015, "positions": 1, "exposure": 0.01, "predictions": 212}
data\v2.jsonl:479:{"tick": 2340, "t": "02:09:39", "acc": 0.53, "entropy": 0.9951, "ret": -0.029367, "capital": 9706.33, "trades": 1016, "positions": 0, "exposure": 0, "predictions": 232}
data\v2.jsonl:480:{"tick": 2345, "t": "02:14:41", "acc": 0.495, "entropy": 0.9945, "ret": -0.029446, "capital": 9705.54, "trades": 1017, "positions": 2, "exposure": 0.02, "predictions": 252}
data\v2.jsonl:481:{"tick": 2350, "t": "02:19:43", "acc": 0.495, "entropy": 0.9938, "ret": -0.029396, "capital": 9706.04, "trades": 1022, "positions": 1, "exposure": 0.01, "predictions": 272}
data\v2.jsonl:482:{"tick": 2355, "t": "02:24:51", "acc": 0.495, "entropy": 0.9933, "ret": -0.02916, "capital": 9708.4, "trades": 1025, "positions": 3, "exposure": 0.03, "predictions": 292}
data\v2.jsonl:483:{"tick": 2360, "t": "02:29:53", "acc": 0.475, "entropy": 0.9903, "ret": -0.029851, "capital": 9701.49, "trades": 1030, "positions": 0, "exposure": 0, "predictions": 312}
data\v2.jsonl:484:{"tick": 2365, "t": "02:34:55", "acc": 0.465, "entropy": 0.9898, "ret": -0.02976, "capital": 9702.4, "trades": 1031, "positions": 3, "exposure": 0.03, "predictions": 332}
data\v2.jsonl:485:{"tick": 2370, "t": "02:39:58", "acc": 0.465, "entropy": 0.9881, "ret": -0.029317, "capital": 9706.83, "trades": 1035, "positions": 3, "exposure": 0.03, "predictions": 352}
data\v2.jsonl:486:{"tick": 2375, "t": "02:45:00", "acc": 0.47, "entropy": 0.9895, "ret": -0.028757, "capital": 9712.43, "trades": 1038, "positions": 4, "exposure": 0.04, "predictions": 372}
data\v2.jsonl:487:{"tick": 2380, "t": "02:50:02", "acc": 0.44, "entropy": 0.992, "ret": -0.029547, "capital": 9704.53, "trades": 1041, "positions": 1, "exposure": 0.01, "predictions": 392}
data\v2.jsonl:488:{"tick": 2385, "t": "02:55:04", "acc": 0.435, "entropy": 0.991, "ret": -0.029969, "capital": 9700.31, "trades": 1044, "positions": 2, "exposure": 0.02, "predictions": 412}
data\v2.jsonl:489:{"tick": 2390, "t": "03:00:06", "acc": 0.47, "entropy": 0.989, "ret": -0.030121, "capital": 9698.79, "trades": 1048, "positions": 3, "exposure": 0.03, "predictions": 432}
data\v2.jsonl:490:{"tick": 2395, "t": "03:05:08", "acc": 0.485, "entropy": 0.9912, "ret": -0.030339, "capital": 9696.61, "trades": 1050, "positions": 2, "exposure": 0.02, "predictions": 452}
data\v2.jsonl:491:{"tick": 2400, "t": "03:10:13", "acc": 0.47, "entropy": 0.9895, "ret": -0.031648, "capital": 9683.52, "trades": 1055, "positions": 1, "exposure": 0.01, "predictions": 472}
data\v2.jsonl:492:{"tick": 2405, "t": "03:15:16", "acc": 0.465, "entropy": 0.9925, "ret": -0.031828, "capital": 9681.72, "trades": 1058, "positions": 1, "exposure": 0.01, "predictions": 492}
data\v2.jsonl:493:{"tick": 2410, "t": "03:20:18", "acc": 0.475, "entropy": 0.9937, "ret": -0.031955, "capital": 9680.45, "trades": 1062, "positions": 3, "exposure": 0.03, "predictions": 512}
data\v2.jsonl:494:{"tick": 2415, "t": "03:25:20", "acc": 0.495, "entropy": 0.9941, "ret": -0.031865, "capital": 9681.35, "trades": 1066, "positions": 2, "exposure": 0.02, "predictions": 532}
data\v2.jsonl:495:{"tick": 2420, "t": "03:30:21", "acc": 0.495, "entropy": 0.9949, "ret": -0.032115, "capital": 9678.85, "trades": 1068, "positions": 2, "exposure": 0.02, "predictions": 552}
data\v2.jsonl:496:{"tick": 2425, "t": "03:35:24", "acc": 0.48, "entropy": 0.9924, "ret": -0.032096, "capital": 9679.04, "trades": 1069, "positions": 4, "exposure": 0.04, "predictions": 572}
data\v2.jsonl:497:{"tick": 2430, "t": "03:40:26", "acc": 0.5, "entropy": 0.9938, "ret": -0.032314, "capital": 9676.86, "trades": 1071, "positions": 4, "exposure": 0.04, "predictions": 592}
data\v2.jsonl:498:{"tick": 2435, "t": "03:45:28", "acc": 0.485, "entropy": 0.9904, "ret": -0.032387, "capital": 9676.13, "trades": 1074, "positions": 2, "exposure": 0.02, "predictions": 612}
data\v2.jsonl:499:{"tick": 2440, "t": "03:50:30", "acc": 0.46, "entropy": 0.9906, "ret": -0.032386, "capital": 9676.14, "trades": 1077, "positions": 1, "exposure": 0.01, "predictions": 632}
data\v2.jsonl:500:{"tick": 2445, "t": "03:55:33", "acc": 0.45, "entropy": 0.9889, "ret": -0.032511, "capital": 9674.89, "trades": 1079, "positions": 2, "exposure": 0.02, "predictions": 652}
data\v2.jsonl:501:{"tick": 2450, "t": "04:00:35", "acc": 0.46, "entropy": 0.9904, "ret": -0.032713, "capital": 9672.87, "trades": 1081, "positions": 2, "exposure": 0.02, "predictions": 672}
data\v2.jsonl:502:{"tick": 2455, "t": "04:05:37", "acc": 0.48, "entropy": 0.9885, "ret": -0.032132, "capital": 9678.68, "trades": 1084, "positions": 2, "exposure": 0.02, "predictions": 692}
data\v2.jsonl:503:{"tick": 2460, "t": "04:10:39", "acc": 0.48, "entropy": 0.9892, "ret": -0.032066, "capital": 9679.34, "trades": 1088, "positions": 0, "exposure": 0, "predictions": 712}
data\v2.jsonl:504:{"tick": 2465, "t": "04:15:41", "acc": 0.485, "entropy": 0.9891, "ret": -0.03254, "capital": 9674.6, "trades": 1091, "positions": 2, "exposure": 0.02, "predictions": 732}
data\v2.jsonl:505:{"tick": 2470, "t": "04:20:44", "acc": 0.51, "entropy": 0.9896, "ret": -0.032681, "capital": 9673.19, "trades": 1095, "positions": 2, "exposure": 0.02, "predictions": 752}
data\v2.jsonl:506:{"tick": 2475, "t": "04:25:46", "acc": 0.525, "entropy": 0.9864, "ret": -0.033037, "capital": 9669.63, "trades": 1097, "positions": 3, "exposure": 0.03, "predictions": 772}
data\v2.jsonl:507:{"tick": 2480, "t": "04:30:48", "acc": 0.53, "entropy": 0.9896, "ret": -0.03317, "capital": 9668.3, "trades": 1100, "positions": 2, "exposure": 0.02, "predictions": 792}
data\v2.jsonl:508:{"tick": 2485, "t": "04:35:51", "acc": 0.545, "entropy": 0.986, "ret": -0.033175, "capital": 9668.25, "trades": 1103, "positions": 0, "exposure": 0, "predictions": 812}
data\v2.jsonl:509:{"tick": 2490, "t": "04:40:54", "acc": 0.54, "entropy": 0.9898, "ret": -0.033366, "capital": 9666.34, "trades": 1105, "positions": 3, "exposure": 0.03, "predictions": 832}
data\v2.jsonl:510:{"tick": 2495, "t": "04:45:56", "acc": 0.55, "entropy": 0.9902, "ret": -0.034055, "capital": 9659.45, "trades": 1108, "positions": 2, "exposure": 0.02, "predictions": 852}
data\v2.jsonl:511:{"tick": 2500, "t": "04:50:58", "acc": 0.535, "entropy": 0.9905, "ret": -0.034688, "capital": 9653.12, "trades": 1112, "positions": 3, "exposure": 0.03, "predictions": 872}
data\v2.jsonl:512:{"tick": 2505, "t": "04:56:01", "acc": 0.535, "entropy": 0.9872, "ret": -0.034703, "capital": 9652.97, "trades": 1115, "positions": 3, "exposure": 0.03, "predictions": 892}
data\v2.jsonl:513:{"tick": 2510, "t": "05:01:05", "acc": 0.54, "entropy": 0.9891, "ret": -0.034299, "capital": 9657.01, "trades": 1120, "positions": 2, "exposure": 0.02, "predictions": 912}
data\v2.jsonl:514:{"tick": 2495, "t": "05:29:44", "acc": 0.5, "entropy": 0.9883, "ret": -0.033495, "capital": 9665.05, "trades": 1000, "positions": 0, "exposure": 0, "predictions": 8}
data\v2.jsonl:515:{"tick": 2500, "t": "05:34:48", "acc": 0.5, "entropy": 0.9871, "ret": -0.033495, "capital": 9665.05, "trades": 1000, "positions": 1, "exposure": 0.01, "predictions": 28}
data\v2.jsonl:516:{"tick": 2505, "t": "05:39:50", "acc": 0.4792, "entropy": 0.9886, "ret": -0.033566, "capital": 9664.34, "trades": 1002, "positions": 1, "exposure": 0.01, "predictions": 48}
data\v2.jsonl:517:{"tick": 2510, "t": "05:44:52", "acc": 0.5, "entropy": 0.9908, "ret": -0.033552, "capital": 9664.48, "trades": 1004, "positions": 0, "exposure": 0, "predictions": 68}
data\v2.jsonl:518:{"tick": 2515, "t": "05:49:54", "acc": 0.4886, "entropy": 0.9927, "ret": -0.033593, "capital": 9664.07, "trades": 1006, "positions": 1, "exposure": 0.01, "predictions": 88}
data\v2.jsonl:519:{"tick": 2520, "t": "05:54:57", "acc": 0.4907, "entropy": 0.9902, "ret": -0.033614, "capital": 9663.86, "trades": 1009, "positions": 2, "exposure": 0.02, "predictions": 108}
data\v2.jsonl:520:{"tick": 2525, "t": "05:59:59", "acc": 0.4922, "entropy": 0.9908, "ret": -0.033744, "capital": 9662.56, "trades": 1013, "positions": 0, "exposure": 0, "predictions": 128}
data\v2.jsonl:521:{"tick": 2530, "t": "06:05:13", "acc": 0.4932, "entropy": 0.991, "ret": -0.033849, "capital": 9661.51, "trades": 1015, "positions": 2, "exposure": 0.02, "predictions": 148}
data\v2.jsonl:522:{"tick": 2535, "t": "06:10:27", "acc": 0.506, "entropy": 0.9873, "ret": -0.033687, "capital": 9663.13, "trades": 1020, "positions": 2, "exposure": 0.02, "predictions": 168}
data\v2.jsonl:523:{"tick": 2540, "t": "06:15:28", "acc": 0.5106, "entropy": 0.9893, "ret": -0.033805, "capital": 9661.95, "trades": 1024, "positions": 1, "exposure": 0.01, "predictions": 188}
data\v2.jsonl:524:{"tick": 2545, "t": "06:20:30", "acc": 0.515, "entropy": 0.9879, "ret": -0.033853, "capital": 9661.47, "trades": 1026, "positions": 2, "exposure": 0.02, "predictions": 208}
data\v2.jsonl:525:{"tick": 2550, "t": "06:25:33", "acc": 0.5, "entropy": 0.9902, "ret": -0.033745, "capital": 9662.55, "trades": 1029, "positions": 1, "exposure": 0.01, "predictions": 228}
data\v2.jsonl:526:{"tick": 2555, "t": "06:30:36", "acc": 0.51, "entropy": 0.988, "ret": -0.033895, "capital": 9661.05, "trades": 1030, "positions": 2, "exposure": 0.02, "predictions": 248}
data\v2.jsonl:527:{"tick": 2560, "t": "06:35:38", "acc": 0.51, "entropy": 0.9883, "ret": -0.034044, "capital": 9659.56, "trades": 1033, "positions": 3, "exposure": 0.03, "predictions": 268}
data\v2.jsonl:528:{"tick": 2565, "t": "06:40:40", "acc": 0.515, "entropy": 0.9867, "ret": -0.033738, "capital": 9662.62, "trades": 1036, "positions": 2, "exposure": 0.02, "predictions": 288}
data\v2.jsonl:529:{"tick": 2570, "t": "06:45:42", "acc": 0.515, "entropy": 0.9895, "ret": -0.033637, "capital": 9663.63, "trades": 1039, "positions": 1, "exposure": 0.01, "predictions": 308}
data\v2.jsonl:530:{"tick": 2575, "t": "06:50:52", "acc": 0.505, "entropy": 0.9874, "ret": -0.034196, "capital": 9658.04, "trades": 1043, "positions": 1, "exposure": 0.01, "predictions": 328}
data\v2.jsonl:531:{"tick": 2580, "t": "06:55:55", "acc": 0.53, "entropy": 0.9905, "ret": -0.034414, "capital": 9655.86, "trades": 1046, "positions": 3, "exposure": 0.03, "predictions": 348}
data\v2.jsonl:532:{"tick": 2585, "t": "07:01:01", "acc": 0.525, "entropy": 0.9878, "ret": -0.034493, "capital": 9655.07, "trades": 1050, "positions": 1, "exposure": 0.01, "predictions": 368}
data\v2.jsonl:533:{"tick": 2590, "t": "07:06:04", "acc": 0.53, "entropy": 0.9914, "ret": -0.034386, "capital": 9656.14, "trades": 1054, "positions": 1, "exposure": 0.01, "predictions": 388}
data\v2.jsonl:534:{"tick": 2595, "t": "07:11:06", "acc": 0.52, "entropy": 0.9938, "ret": -0.034727, "capital": 9652.73, "trades": 1056, "positions": 3, "exposure": 0.03, "predictions": 408}
data\v2.jsonl:535:{"tick": 2600, "t": "07:16:09", "acc": 0.54, "entropy": 0.9917, "ret": -0.034639, "capital": 9653.61, "trades": 1062, "positions": 1, "exposure": 0.01, "predictions": 428}
data\v2.jsonl:536:{"tick": 2605, "t": "07:21:11", "acc": 0.535, "entropy": 0.9911, "ret": -0.035086, "capital": 9649.14, "trades": 1065, "positions": 3, "exposure": 0.03, "predictions": 448}
data\v2.jsonl:537:{"tick": 2610, "t": "07:26:14", "acc": 0.55, "entropy": 0.9894, "ret": -0.034894, "capital": 9651.06, "trades": 1069, "positions": 2, "exposure": 0.02, "predictions": 468}
data\v2.jsonl:538:{"tick": 2615, "t": "07:31:17", "acc": 0.575, "entropy": 0.9931, "ret": -0.034441, "capital": 9655.59, "trades": 1072, "positions": 1, "exposure": 0.01, "predictions": 488}
data\v2.jsonl:539:{"tick": 2620, "t": "07:36:19", "acc": 0.585, "entropy": 0.9926, "ret": -0.034564, "capital": 9654.36, "trades": 1074, "positions": 2, "exposure": 0.02, "predictions": 508}
data\v2.jsonl:540:{"tick": 2625, "t": "07:41:21", "acc": 0.585, "entropy": 0.9928, "ret": -0.034417, "capital": 9655.83, "trades": 1076, "positions": 1, "exposure": 0.01, "predictions": 528}
data\v2.jsonl:541:{"tick": 2630, "t": "07:46:23", "acc": 0.56, "entropy": 0.9932, "ret": -0.034208, "capital": 9657.92, "trades": 1078, "positions": 2, "exposure": 0.02, "predictions": 548}
data\v2.jsonl:542:{"tick": 2635, "t": "07:51:32", "acc": 0.55, "entropy": 0.9918, "ret": -0.033626, "capital": 9663.74, "trades": 1082, "positions": 0, "exposure": 0, "predictions": 568}
data\v2.jsonl:543:{"tick": 2640, "t": "07:56:35", "acc": 0.54, "entropy": 0.9919, "ret": -0.034108, "capital": 9658.92, "trades": 1088, "positions": 1, "exposure": 0.01, "predictions": 588}
data\v2.jsonl:544:{"tick": 2645, "t": "08:01:58", "acc": 0.535, "entropy": 0.9919, "ret": -0.034205, "capital": 9657.95, "trades": 1090, "positions": 1, "exposure": 0.01, "predictions": 608}
data\v2.jsonl:545:{"tick": 2650, "t": "08:07:06", "acc": 0.505, "entropy": 0.9939, "ret": -0.034489, "capital": 9655.11, "trades": 1093, "positions": 4, "exposure": 0.04, "predictions": 628}
data\v2.jsonl:546:{"tick": 2655, "t": "08:12:13", "acc": 0.49, "entropy": 0.9931, "ret": -0.035162, "capital": 9648.38, "trades": 1097, "positions": 1, "exposure": 0.01, "predictions": 648}
data\v2.jsonl:547:{"tick": 2660, "t": "08:17:19", "acc": 0.45, "entropy": 0.991, "ret": -0.035732, "capital": 9642.68, "trades": 1102, "positions": 0, "exposure": 0, "predictions": 668}
data\v2.jsonl:548:{"tick": 2665, "t": "08:22:21", "acc": 0.41, "entropy": 0.9905, "ret": -0.03607, "capital": 9639.3, "trades": 1104, "positions": 3, "exposure": 0.03, "predictions": 688}
data\v2.jsonl:549:{"tick": 2670, "t": "08:27:23", "acc": 0.39, "entropy": 0.9908, "ret": -0.036371, "capital": 9636.29, "trades": 1109, "positions": 1, "exposure": 0.01, "predictions": 708}
data\v2.jsonl:550:{"tick": 2675, "t": "08:32:25", "acc": 0.405, "entropy": 0.9905, "ret": -0.036343, "capital": 9636.57, "trades": 1110, "positions": 2, "exposure": 0.02, "predictions": 728}
data\v2.jsonl:551:{"tick": 2680, "t": "08:37:27", "acc": 0.4, "entropy": 0.9929, "ret": -0.036308, "capital": 9636.92, "trades": 1112, "positions": 3, "exposure": 0.03, "predictions": 748}
data\v2.jsonl:552:{"tick": 2685, "t": "08:42:29", "acc": 0.425, "entropy": 0.9927, "ret": -0.036457, "capital": 9635.43, "trades": 1117, "positions": 1, "exposure": 0.01, "predictions": 768}
data\v2.jsonl:553:{"tick": 2690, "t": "08:47:31", "acc": 0.455, "entropy": 0.9889, "ret": -0.036303, "capital": 9636.97, "trades": 1119, "positions": 3, "exposure": 0.03, "predictions": 788}
data\v2.jsonl:554:{"tick": 2695, "t": "08:52:33", "acc": 0.47, "entropy": 0.9902, "ret": -0.036014, "capital": 9639.86, "trades": 1124, "positions": 1, "exposure": 0.01, "predictions": 808}
data\v2.jsonl:555:{"tick": 2700, "t": "08:57:45", "acc": 0.49, "entropy": 0.9893, "ret": -0.036016, "capital": 9639.84, "trades": 1128, "positions": 0, "exposure": 0, "predictions": 828}
data\v2.jsonl:556:{"tick": 2705, "t": "09:02:47", "acc": 0.53, "entropy": 0.993, "ret": -0.035776, "capital": 9642.24, "trades": 1131, "positions": 1, "exposure": 0.01, "predictions": 848}
data\v2.jsonl:557:{"tick": 2710, "t": "09:07:53", "acc": 0.57, "entropy": 0.99, "ret": -0.035494, "capital": 9645.06, "trades": 1134, "positions": 2, "exposure": 0.02, "predictions": 868}
data\v2.jsonl:558:{"tick": 2715, "t": "09:12:55", "acc": 0.59, "entropy": 0.992, "ret": -0.035284, "capital": 9647.16, "trades": 1137, "positions": 2, "exposure": 0.02, "predictions": 888}
data\v2.jsonl:559:{"tick": 2720, "t": "09:17:57", "acc": 0.59, "entropy": 0.9901, "ret": -0.036368, "capital": 9636.32, "trades": 1141, "positions": 1, "exposure": 0.01, "predictions": 908}
data\v2.jsonl:560:{"tick": 2725, "t": "09:23:01", "acc": 0.58, "entropy": 0.9906, "ret": -0.036204, "capital": 9637.96, "trades": 1143, "positions": 2, "exposure": 0.02, "predictions": 928}
data\v2.jsonl:561:{"tick": 2730, "t": "09:28:04", "acc": 0.575, "entropy": 0.9927, "ret": -0.036225, "capital": 9637.75, "trades": 1148, "positions": 3, "exposure": 0.03, "predictions": 948}
data\v2.jsonl:562:{"tick": 2735, "t": "09:33:06", "acc": 0.565, "entropy": 0.991, "ret": -0.03597, "capital": 9640.3, "trades": 1153, "positions": 1, "exposure": 0.01, "predictions": 968}
data\v2.jsonl:563:{"tick": 2740, "t": "09:38:08", "acc": 0.53, "entropy": 0.9917, "ret": -0.036391, "capital": 9636.09, "trades": 1156, "positions": 3, "exposure": 0.03, "predictions": 988}
data\v2.jsonl:564:{"tick": 2745, "t": "09:43:10", "acc": 0.535, "entropy": 0.9882, "ret": -0.036393, "capital": 9636.07, "trades": 1161, "positions": 2, "exposure": 0.02, "predictions": 1008}
data\v2.jsonl:565:{"tick": 2750, "t": "09:48:12", "acc": 0.545, "entropy": 0.9882, "ret": -0.036093, "capital": 9639.07, "trades": 1163, "positions": 2, "exposure": 0.02, "predictions": 1028}
data\v2.jsonl:566:{"tick": 2755, "t": "09:53:14", "acc": 0.52, "entropy": 0.9876, "ret": -0.037659, "capital": 9623.41, "trades": 1166, "positions": 1, "exposure": 0.01, "predictions": 1048}
data\v2.jsonl:567:{"tick": 2760, "t": "09:58:16", "acc": 0.5, "entropy": 0.9878, "ret": -0.037477, "capital": 9625.23, "trades": 1169, "positions": 1, "exposure": 0.01, "predictions": 1068}
data\v2.jsonl:568:{"tick": 2765, "t": "10:03:19", "acc": 0.5, "entropy": 0.9916, "ret": -0.037348, "capital": 9626.52, "trades": 1172, "positions": 2, "exposure": 0.02, "predictions": 1088}
data\v2.jsonl:569:{"tick": 2770, "t": "10:08:21", "acc": 0.5, "entropy": 0.9911, "ret": -0.039647, "capital": 9603.53, "trades": 1176, "positions": 2, "exposure": 0.02, "predictions": 1108}
data\v2.jsonl:570:{"tick": 2775, "t": "10:13:23", "acc": 0.495, "entropy": 0.9906, "ret": -0.03982, "capital": 9601.8, "trades": 1178, "positions": 3, "exposure": 0.03, "predictions": 1128}
data\v2.jsonl:571:{"tick": 2780, "t": "10:18:25", "acc": 0.5, "entropy": 0.9899, "ret": -0.040281, "capital": 9597.19, "trades": 1181, "positions": 3, "exposure": 0.03, "predictions": 1148}
data\v2.jsonl:572:{"tick": 2785, "t": "10:23:27", "acc": 0.485, "entropy": 0.9911, "ret": -0.040685, "capital": 9593.15, "trades": 1185, "positions": 1, "exposure": 0.01, "predictions": 1168}
data\v2.jsonl:573:{"tick": 2790, "t": "10:28:29", "acc": 0.48, "entropy": 0.9905, "ret": -0.041034, "capital": 9589.66, "trades": 1188, "positions": 3, "exposure": 0.03, "predictions": 1188}
data\v2.jsonl:574:{"tick": 2795, "t": "10:33:32", "acc": 0.48, "entropy": 0.9913, "ret": -0.041233, "capital": 9587.67, "trades": 1190, "positions": 4, "exposure": 0.04, "predictions": 1208}
data\v2.jsonl:575:{"tick": 2800, "t": "10:38:34", "acc": 0.46, "entropy": 0.9904, "ret": -0.041272, "capital": 9587.28, "trades": 1194, "positions": 4, "exposure": 0.04, "predictions": 1228}
data\v2.jsonl:576:{"tick": 2805, "t": "10:43:36", "acc": 0.475, "entropy": 0.9887, "ret": -0.041713, "capital": 9582.87, "trades": 1199, "positions": 0, "exposure": 0, "predictions": 1248}
data\v2.jsonl:577:{"tick": 2810, "t": "10:48:38", "acc": 0.44, "entropy": 0.9854, "ret": -0.041713, "capital": 9582.87, "trades": 1199, "positions": 2, "exposure": 0.02, "predictions": 1268}
data\v2.jsonl:578:{"tick": 2815, "t": "10:53:40", "acc": 0.415, "entropy": 0.9884, "ret": -0.042133, "capital": 9578.67, "trades": 1201, "positions": 2, "exposure": 0.02, "predictions": 1288}
data\v2.jsonl:579:{"tick": 2820, "t": "10:58:42", "acc": 0.44, "entropy": 0.9866, "ret": -0.041814, "capital": 9581.86, "trades": 1205, "positions": 1, "exposure": 0.01, "predictions": 1308}
data\v2.jsonl:580:{"tick": 2825, "t": "11:03:45", "acc": 0.45, "entropy": 0.9843, "ret": -0.04156, "capital": 9584.4, "trades": 1207, "positions": 3, "exposure": 0.03, "predictions": 1328}
data\v2.jsonl:581:{"tick": 2830, "t": "11:08:47", "acc": 0.47, "entropy": 0.988, "ret": -0.041214, "capital": 9587.86, "trades": 1211, "positions": 2, "exposure": 0.02, "predictions": 1348}
data\v2.jsonl:582:{"tick": 2835, "t": "11:13:49", "acc": 0.48, "entropy": 0.9894, "ret": -0.041641, "capital": 9583.59, "trades": 1216, "positions": 2, "exposure": 0.02, "predictions": 1368}
data\v2.jsonl:583:{"tick": 2840, "t": "11:18:51", "acc": 0.495, "entropy": 0.9871, "ret": -0.041749, "capital": 9582.51, "trades": 1218, "positions": 1, "exposure": 0.01, "predictions": 1388}
data\v2.jsonl:584:{"tick": 2845, "t": "11:23:53", "acc": 0.48, "entropy": 0.9903, "ret": -0.041808, "capital": 9581.92, "trades": 1220, "positions": 3, "exposure": 0.03, "predictions": 1408}
data\v2.jsonl:585:{"tick": 2850, "t": "11:28:56", "acc": 0.495, "entropy": 0.9904, "ret": -0.041753, "capital": 9582.47, "trades": 1225, "positions": 1, "exposure": 0.01, "predictions": 1428}
data\v2.jsonl:586:{"tick": 2855, "t": "11:33:58", "acc": 0.48, "entropy": 0.9886, "ret": -0.041901, "capital": 9580.99, "trades": 1228, "positions": 2, "exposure": 0.02, "predictions": 1448}
data\v2.jsonl:587:{"tick": 2860, "t": "11:39:00", "acc": 0.505, "entropy": 0.9855, "ret": -0.041964, "capital": 9580.36, "trades": 1232, "positions": 2, "exposure": 0.02, "predictions": 1468}
data\v2.jsonl:588:{"tick": 2865, "t": "11:44:02", "acc": 0.53, "entropy": 0.9878, "ret": -0.042188, "capital": 9578.12, "trades": 1234, "positions": 1, "exposure": 0.01, "predictions": 1488}
data\v2.jsonl:589:{"tick": 2870, "t": "11:49:04", "acc": 0.525, "entropy": 0.9877, "ret": -0.042185, "capital": 9578.15, "trades": 1236, "positions": 2, "exposure": 0.02, "predictions": 1508}
data\v2.jsonl:590:{"tick": 2875, "t": "11:54:06", "acc": 0.53, "entropy": 0.9864, "ret": -0.04187, "capital": 9581.3, "trades": 1239, "positions": 1, "exposure": 0.01, "predictions": 1528}
data\v2.jsonl:591:{"tick": 2880, "t": "11:59:09", "acc": 0.525, "entropy": 0.9876, "ret": -0.041903, "capital": 9580.97, "trades": 1241, "positions": 1, "exposure": 0.01, "predictions": 1548}
data\v2.jsonl:592:{"tick": 2885, "t": "12:04:11", "acc": 0.505, "entropy": 0.9903, "ret": -0.041903, "capital": 9580.97, "trades": 1241, "positions": 2, "exposure": 0.02, "predictions": 1568}
data\v2.jsonl:593:{"tick": 2890, "t": "12:09:13", "acc": 0.475, "entropy": 0.9915, "ret": -0.042071, "capital": 9579.29, "trades": 1242, "positions": 4, "exposure": 0.04, "predictions": 1588}
data\v2.jsonl:594:{"tick": 2895, "t": "12:14:15", "acc": 0.48, "entropy": 0.9887, "ret": -0.043733, "capital": 9562.67, "trades": 1248, "positions": 1, "exposure": 0.01, "predictions": 1608}
data\v2.jsonl:595:{"tick": 2900, "t": "12:19:33", "acc": 0.475, "entropy": 0.988, "ret": -0.043898, "capital": 9561.02, "trades": 1252, "positions": 4, "exposure": 0.04, "predictions": 1628}
data\v2.jsonl:596:{"tick": 2905, "t": "12:24:54", "acc": 0.48, "entropy": 0.9851, "ret": -0.044563, "capital": 9554.37, "trades": 1256, "positions": 2, "exposure": 0.02, "predictions": 1648}
data\v2.jsonl:597:{"tick": 2910, "t": "12:29:56", "acc": 0.485, "entropy": 0.9801, "ret": -0.044597, "capital": 9554.03, "trades": 1258, "positions": 2, "exposure": 0.02, "predictions": 1668}
data\v2.jsonl:598:{"tick": 2915, "t": "12:34:58", "acc": 0.485, "entropy": 0.984, "ret": -0.044461, "capital": 9555.39, "trades": 1260, "positions": 3, "exposure": 0.03, "predictions": 1688}
data\v2.jsonl:599:{"tick": 2920, "t": "12:40:00", "acc": 0.475, "entropy": 0.9854, "ret": -0.044308, "capital": 9556.92, "trades": 1261, "positions": 2, "exposure": 0.02, "predictions": 1708}
data\v2.jsonl:600:{"tick": 2925, "t": "12:45:02", "acc": 0.475, "entropy": 0.9828, "ret": -0.044788, "capital": 9552.12, "trades": 1264, "positions": 2, "exposure": 0.02, "predictions": 1728}
data\v2.jsonl:601:{"tick": 2930, "t": "12:50:05", "acc": 0.48, "entropy": 0.9806, "ret": -0.044279, "capital": 9557.21, "trades": 1268, "positions": 2, "exposure": 0.02, "predictions": 1748}
data\v2.jsonl:602:{"tick": 2935, "t": "12:55:07", "acc": 0.5, "entropy": 0.9864, "ret": -0.043816, "capital": 9561.84, "trades": 1272, "positions": 1, "exposure": 0.01, "predictions": 1768}
data\v2.jsonl:603:{"tick": 2940, "t": "13:00:09", "acc": 0.53, "entropy": 0.9816, "ret": -0.04367, "capital": 9563.3, "trades": 1275, "positions": 1, "exposure": 0.01, "predictions": 1788}
data\v2.jsonl:604:{"tick": 2945, "t": "13:05:12", "acc": 0.525, "entropy": 0.9857, "ret": -0.043647, "capital": 9563.53, "trades": 1277, "positions": 2, "exposure": 0.02, "predictions": 1808}
data\v2.jsonl:605:{"tick": 2950, "t": "13:10:14", "acc": 0.525, "entropy": 0.9853, "ret": -0.04356, "capital": 9564.4, "trades": 1281, "positions": 2, "exposure": 0.02, "predictions": 1828}
data\v2.jsonl:606:{"tick": 2955, "t": "13:15:16", "acc": 0.53, "entropy": 0.9877, "ret": -0.043247, "capital": 9567.53, "trades": 1284, "positions": 3, "exposure": 0.03, "predictions": 1847}
data\v2.jsonl:607:{"tick": 2960, "t": "13:20:18", "acc": 0.51, "entropy": 0.988, "ret": -0.043729, "capital": 9562.71, "trades": 1288, "positions": 1, "exposure": 0.01, "predictions": 1867}
data\v2.jsonl:608:{"tick": 2965, "t": "13:25:20", "acc": 0.51, "entropy": 0.9862, "ret": -0.043765, "capital": 9562.35, "trades": 1291, "positions": 3, "exposure": 0.03, "predictions": 1887}
data\v2.jsonl:609:{"tick": 2970, "t": "13:30:22", "acc": 0.505, "entropy": 0.9828, "ret": -0.0446, "capital": 9554.0, "trades": 1293, "positions": 2, "exposure": 0.02, "predictions": 1907}
data\v2.jsonl:610:{"tick": 2975, "t": "13:35:25", "acc": 0.505, "entropy": 0.9833, "ret": -0.045052, "capital": 9549.48, "trades": 1297, "positions": 1, "exposure": 0.01, "predictions": 1927}
data\v2.jsonl:611:{"tick": 2980, "t": "13:40:27", "acc": 0.485, "entropy": 0.987, "ret": -0.045092, "capital": 9549.08, "trades": 1300, "positions": 2, "exposure": 0.02, "predictions": 1947}
data\v2.jsonl:612:{"tick": 2985, "t": "13:45:29", "acc": 0.495, "entropy": 0.9863, "ret": -0.044502, "capital": 9554.98, "trades": 1301, "positions": 3, "exposure": 0.03, "predictions": 1967}
data\v2.jsonl:613:{"tick": 2990, "t": "13:50:31", "acc": 0.48, "entropy": 0.9829, "ret": -0.044332, "capital": 9556.68, "trades": 1305, "positions": 1, "exposure": 0.01, "predictions": 1987}
data\v2.jsonl:614:{"tick": 2995, "t": "13:55:33", "acc": 0.48, "entropy": 0.9845, "ret": -0.04716, "capital": 9528.4, "trades": 1309, "positions": 3, "exposure": 0.03, "predictions": 2007}
data\v2.jsonl:615:{"tick": 3000, "t": "14:00:35", "acc": 0.48, "entropy": 0.9832, "ret": -0.045367, "capital": 9546.33, "trades": 1316, "positions": 3, "exposure": 0.03, "predictions": 2027}
data\v2.jsonl:616:{"tick": 3005, "t": "14:05:37", "acc": 0.47, "entropy": 0.9757, "ret": -0.044669, "capital": 9553.31, "trades": 1321, "positions": 1, "exposure": 0.01, "predictions": 2047}
data\v2.jsonl:617:{"tick": 3010, "t": "14:10:40", "acc": 0.485, "entropy": 0.9789, "ret": -0.044858, "capital": 9551.42, "trades": 1324, "positions": 2, "exposure": 0.02, "predictions": 2067}
data\v2.jsonl:618:{"tick": 3015, "t": "14:15:42", "acc": 0.465, "entropy": 0.9829, "ret": -0.045189, "capital": 9548.11, "trades": 1325, "positions": 4, "exposure": 0.04, "predictions": 2087}
data\v2.jsonl:619:{"tick": 3020, "t": "14:20:44", "acc": 0.445, "entropy": 0.9856, "ret": -0.046587, "capital": 9534.13, "trades": 1330, "positions": 2, "exposure": 0.02, "predictions": 2107}
data\v2.jsonl:620:{"tick": 3025, "t": "14:25:46", "acc": 0.435, "entropy": 0.9869, "ret": -0.048909, "capital": 9510.91, "trades": 1333, "positions": 1, "exposure": 0.01, "predictions": 2127}
data\v2.jsonl:621:{"tick": 3030, "t": "14:30:48", "acc": 0.44, "entropy": 0.9898, "ret": -0.047967, "capital": 9520.33, "trades": 1336, "positions": 2, "exposure": 0.02, "predictions": 2147}
data\v2.jsonl:622:{"tick": 3035, "t": "14:35:52", "acc": 0.43, "entropy": 0.9904, "ret": -0.048426, "capital": 9515.74, "trades": 1338, "positions": 2, "exposure": 0.02, "predictions": 2167}
data\v2.jsonl:623:{"tick": 3040, "t": "14:40:54", "acc": 0.445, "entropy": 0.9892, "ret": -0.049351, "capital": 9506.49, "trades": 1340, "positions": 1, "exposure": 0.01, "predictions": 2187}
data\v2.jsonl:624:{"tick": 3045, "t": "14:45:57", "acc": 0.46, "entropy": 0.9847, "ret": -0.050473, "capital": 9495.27, "trades": 1341, "positions": 1, "exposure": 0.01, "predictions": 2207}
data\v2.jsonl:625:{"tick": 3050, "t": "14:50:59", "acc": 0.445, "entropy": 0.9884, "ret": -0.050487, "capital": 9495.13, "trades": 1345, "positions": 1, "exposure": 0.01, "predictions": 2227}
data\v2.jsonl:626:{"tick": 3055, "t": "14:56:01", "acc": 0.435, "entropy": 0.9879, "ret": -0.050204, "capital": 9497.96, "trades": 1348, "positions": 1, "exposure": 0.01, "predictions": 2247}
data\v2.jsonl:627:{"tick": 3060, "t": "15:01:03", "acc": 0.46, "entropy": 0.9901, "ret": -0.050129, "capital": 9498.71, "trades": 1351, "positions": 0, "exposure": 0, "predictions": 2267}
data\v2.jsonl:628:{"tick": 3065, "t": "15:06:06", "acc": 0.46, "entropy": 0.9904, "ret": -0.050564, "capital": 9494.36, "trades": 1352, "positions": 2, "exposure": 0.02, "predictions": 2287}
data\v2.jsonl:629:{"tick": 3070, "t": "15:11:09", "acc": 0.495, "entropy": 0.9882, "ret": -0.049408, "capital": 9505.92, "trades": 1355, "positions": 1, "exposure": 0.01, "predictions": 2307}
data\v2.jsonl:630:{"tick": 3075, "t": "15:16:12", "acc": 0.495, "entropy": 0.9849, "ret": -0.049654, "capital": 9503.46, "trades": 1357, "positions": 1, "exposure": 0.01, "predictions": 2327}
data\v2.jsonl:631:{"tick": 3080, "t": "15:21:15", "acc": 0.495, "entropy": 0.9874, "ret": -0.049906, "capital": 9500.94, "trades": 1358, "positions": 0, "exposure": 0, "predictions": 2347}
data\v2.jsonl:632:{"tick": 3085, "t": "15:26:17", "acc": 0.49, "entropy": 0.985, "ret": -0.050341, "capital": 9496.59, "trades": 1359, "positions": 3, "exposure": 0.03, "predictions": 2367}
data\v2.jsonl:633:{"tick": 3090, "t": "15:31:20", "acc": 0.46, "entropy": 0.9895, "ret": -0.051689, "capital": 9483.11, "trades": 1362, "positions": 1, "exposure": 0.01, "predictions": 2387}
data\v2.jsonl:634:{"tick": 3095, "t": "15:36:23", "acc": 0.455, "entropy": 0.9901, "ret": -0.052142, "capital": 9478.58, "trades": 1364, "positions": 1, "exposure": 0.01, "predictions": 2407}
data\v2.jsonl:635:{"tick": 3100, "t": "15:41:25", "acc": 0.465, "entropy": 0.989, "ret": -0.052927, "capital": 9470.73, "trades": 1369, "positions": 1, "exposure": 0.01, "predictions": 2427}
data\v2.jsonl:636:{"tick": 3105, "t": "15:46:28", "acc": 0.48, "entropy": 0.986, "ret": -0.053018, "capital": 9469.82, "trades": 1372, "positions": 2, "exposure": 0.02, "predictions": 2447}
data\v2.jsonl:637:{"tick": 3110, "t": "15:51:31", "acc": 0.455, "entropy": 0.9864, "ret": -0.053122, "capital": 9468.78, "trades": 1375, "positions": 1, "exposure": 0.01, "predictions": 2467}
data\v2.jsonl:638:{"tick": 3115, "t": "15:56:34", "acc": 0.475, "entropy": 0.9875, "ret": -0.05405, "capital": 9459.5, "trades": 1379, "positions": 1, "exposure": 0.01, "predictions": 2487}
data\v2.jsonl:639:{"tick": 3120, "t": "16:01:37", "acc": 0.45, "entropy": 0.9841, "ret": -0.053715, "capital": 9462.85, "trades": 1381, "positions": 0, "exposure": 0, "predictions": 2507}
data\v2.jsonl:640:{"tick": 3125, "t": "16:06:33", "acc": 0.455, "entropy": 0.9873, "ret": -0.053836, "capital": 9461.64, "trades": 1383, "positions": 3, "exposure": 0.03, "predictions": 2527}
data\v2.jsonl:641:{"tick": 3130, "t": "16:11:36", "acc": 0.45, "entropy": 0.9889, "ret": -0.053899, "capital": 9461.01, "trades": 1386, "positions": 2, "exposure": 0.02, "predictions": 2547}
data\v2.jsonl:642:{"tick": 3135, "t": "16:16:38", "acc": 0.455, "entropy": 0.9917, "ret": -0.054419, "capital": 9455.81, "trades": 1391, "positions": 2, "exposure": 0.02, "predictions": 2567}
data\v2.jsonl:643:{"tick": 3140, "t": "16:21:40", "acc": 0.485, "entropy": 0.994, "ret": -0.054449, "capital": 9455.51, "trades": 1396, "positions": 0, "exposure": 0, "predictions": 2587}
data\v2.jsonl:644:{"tick": 3145, "t": "16:26:42", "acc": 0.485, "entropy": 0.9933, "ret": -0.054201, "capital": 9457.99, "trades": 1398, "positions": 1, "exposure": 0.01, "predictions": 2607}
data\v2.jsonl:645:{"tick": 3150, "t": "16:31:44", "acc": 0.48, "entropy": 0.9938, "ret": -0.053963, "capital": 9460.37, "trades": 1399, "positions": 0, "exposure": 0, "predictions": 2627}
data\v2.jsonl:646:{"tick": 3155, "t": "16:36:47", "acc": 0.475, "entropy": 0.9917, "ret": -0.055373, "capital": 9446.27, "trades": 1402, "positions": 3, "exposure": 0.03, "predictions": 2647}
data\v2.jsonl:647:{"tick": 3160, "t": "16:41:49", "acc": 0.46, "entropy": 0.9893, "ret": -0.054644, "capital": 9453.56, "trades": 1408, "positions": 1, "exposure": 0.01, "predictions": 2667}
data\v2.jsonl:648:{"tick": 3165, "t": "16:46:51", "acc": 0.45, "entropy": 0.9915, "ret": -0.054444, "capital": 9455.56, "trades": 1409, "positions": 2, "exposure": 0.02, "predictions": 2687}
data\v2.jsonl:649:{"tick": 3170, "t": "16:51:53", "acc": 0.44, "entropy": 0.991, "ret": -0.054926, "capital": 9450.74, "trades": 1413, "positions": 2, "exposure": 0.02, "predictions": 2707}
data\v2.jsonl:650:{"tick": 3175, "t": "16:56:55", "acc": 0.445, "entropy": 0.9906, "ret": -0.05556, "capital": 9444.4, "trades": 1414, "positions": 2, "exposure": 0.02, "predictions": 2727}
data\v2.jsonl:651:{"tick": 3180, "t": "17:01:57", "acc": 0.44, "entropy": 0.9917, "ret": -0.055076, "capital": 9449.24, "trades": 1418, "positions": 4, "exposure": 0.04, "predictions": 2747}
data\v2.jsonl:652:{"tick": 3185, "t": "17:06:59", "acc": 0.445, "entropy": 0.9912, "ret": -0.054569, "capital": 9454.31, "trades": 1422, "positions": 2, "exposure": 0.02, "predictions": 2767}
data\v2.jsonl:653:{"tick": 3190, "t": "17:12:01", "acc": 0.43, "entropy": 0.99, "ret": -0.054824, "capital": 9451.76, "trades": 1424, "positions": 2, "exposure": 0.02, "predictions": 2787}
data\v2.jsonl:654:{"tick": 3195, "t": "17:17:03", "acc": 0.435, "entropy": 0.9902, "ret": -0.054808, "capital": 9451.92, "trades": 1426, "positions": 2, "exposure": 0.02, "predictions": 2807}
data\v2.jsonl:655:{"tick": 3200, "t": "17:22:05", "acc": 0.44, "entropy": 0.9913, "ret": -0.05455, "capital": 9454.5, "trades": 1427, "positions": 3, "exposure": 0.03, "predictions": 2827}
data\v2.jsonl:656:{"tick": 3205, "t": "17:27:07", "acc": 0.455, "entropy": 0.9902, "ret": -0.054824, "capital": 9451.76, "trades": 1432, "positions": 1, "exposure": 0.01, "predictions": 2847}
data\v2.jsonl:657:{"tick": 3210, "t": "17:32:10", "acc": 0.48, "entropy": 0.9911, "ret": -0.054927, "capital": 9450.73, "trades": 1436, "positions": 0, "exposure": 0, "predictions": 2867}
data\v2.jsonl:658:{"tick": 3215, "t": "17:37:12", "acc": 0.495, "entropy": 0.9905, "ret": -0.054602, "capital": 9453.98, "trades": 1438, "positions": 1, "exposure": 0.01, "predictions": 2887}
data\v2.jsonl:659:{"tick": 3220, "t": "17:42:14", "acc": 0.53, "entropy": 0.9928, "ret": -0.054227, "capital": 9457.73, "trades": 1439, "positions": 2, "exposure": 0.02, "predictions": 2907}
data\v2.jsonl:660:{"tick": 3225, "t": "17:47:16", "acc": 0.52, "entropy": 0.9923, "ret": -0.055084, "capital": 9449.16, "trades": 1442, "positions": 1, "exposure": 0.01, "predictions": 2927}
data\v2.jsonl:661:{"tick": 3230, "t": "17:52:18", "acc": 0.54, "entropy": 0.9908, "ret": -0.054999, "capital": 9450.01, "trades": 1444, "positions": 2, "exposure": 0.02, "predictions": 2947}
data\v2.jsonl:662:{"tick": 3235, "t": "17:57:20", "acc": 0.535, "entropy": 0.9907, "ret": -0.055239, "capital": 9447.61, "trades": 1446, "positions": 2, "exposure": 0.02, "predictions": 2967}
data\v2.jsonl:663:{"tick": 3240, "t": "18:02:23", "acc": 0.545, "entropy": 0.9902, "ret": -0.056143, "capital": 9438.57, "trades": 1447, "positions": 2, "exposure": 0.02, "predictions": 2987}
data\v2.jsonl:664:{"tick": 3245, "t": "18:07:25", "acc": 0.53, "entropy": 0.9871, "ret": -0.055224, "capital": 9447.76, "trades": 1453, "positions": 0, "exposure": 0, "predictions": 3007}
data\v2.jsonl:665:{"tick": 3250, "t": "18:12:27", "acc": 0.535, "entropy": 0.9851, "ret": -0.056138, "capital": 9438.62, "trades": 1456, "positions": 1, "exposure": 0.01, "predictions": 3027}
data\v2.jsonl:666:{"tick": 3255, "t": "18:17:29", "acc": 0.515, "entropy": 0.9852, "ret": -0.055879, "capital": 9441.21, "trades": 1460, "positions": 2, "exposure": 0.02, "predictions": 3047}
data\v2.jsonl:667:{"tick": 3260, "t": "18:22:31", "acc": 0.5, "entropy": 0.9895, "ret": -0.057178, "capital": 9428.22, "trades": 1462, "positions": 1, "exposure": 0.01, "predictions": 3067}
data\v2.jsonl:668:{"tick": 3265, "t": "18:27:33", "acc": 0.505, "entropy": 0.9886, "ret": -0.05603, "capital": 9439.7, "trades": 1466, "positions": 2, "exposure": 0.02, "predictions": 3087}
data\v2.jsonl:669:{"tick": 3270, "t": "18:32:35", "acc": 0.5, "entropy": 0.9903, "ret": -0.055977, "capital": 9440.23, "trades": 1470, "positions": 1, "exposure": 0.01, "predictions": 3107}
data\v2.jsonl:670:{"tick": 3275, "t": "18:37:38", "acc": 0.515, "entropy": 0.9871, "ret": -0.055754, "capital": 9442.46, "trades": 1472, "positions": 3, "exposure": 0.03, "predictions": 3127}
data\v2.jsonl:671:{"tick": 3280, "t": "18:42:40", "acc": 0.5, "entropy": 0.9851, "ret": -0.057057, "capital": 9429.43, "trades": 1477, "positions": 2, "exposure": 0.02, "predictions": 3147}
data\v2.jsonl:672:{"tick": 3285, "t": "18:47:42", "acc": 0.5, "entropy": 0.9862, "ret": -0.057488, "capital": 9425.12, "trades": 1479, "positions": 2, "exposure": 0.02, "predictions": 3167}
data\v2.jsonl:673:{"tick": 3290, "t": "18:52:44", "acc": 0.495, "entropy": 0.9887, "ret": -0.056016, "capital": 9439.84, "trades": 1481, "positions": 1, "exposure": 0.01, "predictions": 3187}
data\v2.jsonl:674:{"tick": 3295, "t": "18:57:46", "acc": 0.505, "entropy": 0.9875, "ret": -0.055036, "capital": 9449.64, "trades": 1483, "positions": 3, "exposure": 0.03, "predictions": 3207}
data\v2.jsonl:675:{"tick": 3300, "t": "19:02:48", "acc": 0.515, "entropy": 0.9879, "ret": -0.055381, "capital": 9446.19, "trades": 1487, "positions": 3, "exposure": 0.03, "predictions": 3227}
data\v2.jsonl:676:{"tick": 3305, "t": "19:07:50", "acc": 0.515, "entropy": 0.9887, "ret": -0.05528, "capital": 9447.2, "trades": 1490, "positions": 3, "exposure": 0.03, "predictions": 3247}
data\v2.jsonl:677:{"tick": 3310, "t": "19:12:52", "acc": 0.55, "entropy": 0.9889, "ret": -0.05602, "capital": 9439.8, "trades": 1493, "positions": 3, "exposure": 0.03, "predictions": 3267}
data\v2.jsonl:678:{"tick": 3315, "t": "19:17:54", "acc": 0.53, "entropy": 0.99, "ret": -0.056389, "capital": 9436.11, "trades": 1497, "positions": 0, "exposure": 0, "predictions": 3287}
data\v2.jsonl:679:{"tick": 3320, "t": "19:22:56", "acc": 0.515, "entropy": 0.9892, "ret": -0.056389, "capital": 9436.11, "trades": 1497, "positions": 3, "exposure": 0.03, "predictions": 3307}
data\v2.jsonl:680:{"tick": 3325, "t": "19:27:59", "acc": 0.515, "entropy": 0.9886, "ret": -0.056921, "capital": 9430.79, "trades": 1499, "positions": 3, "exposure": 0.03, "predictions": 3327}
data\v2.jsonl:681:{"tick": 3330, "t": "19:33:01", "acc": 0.53, "entropy": 0.9883, "ret": -0.057767, "capital": 9422.33, "trades": 1502, "positions": 1, "exposure": 0.01, "predictions": 3347}
data\v2.jsonl:682:{"tick": 3335, "t": "19:38:03", "acc": 0.53, "entropy": 0.9858, "ret": -0.05758, "capital": 9424.2, "trades": 1505, "positions": 2, "exposure": 0.02, "predictions": 3367}
data\v2.jsonl:683:{"tick": 3340, "t": "19:43:05", "acc": 0.55, "entropy": 0.9858, "ret": -0.056759, "capital": 9432.41, "trades": 1510, "positions": 1, "exposure": 0.01, "predictions": 3387}
data\v2.jsonl:684:{"tick": 3345, "t": "19:48:07", "acc": 0.56, "entropy": 0.9874, "ret": -0.055804, "capital": 9441.96, "trades": 1512, "positions": 2, "exposure": 0.02, "predictions": 3407}
data\v2.jsonl:685:{"tick": 3350, "t": "19:53:09", "acc": 0.545, "entropy": 0.9805, "ret": -0.055422, "capital": 9445.78, "trades": 1516, "positions": 1, "exposure": 0.01, "predictions": 3427}
data\v2.jsonl:686:{"tick": 3355, "t": "19:58:11", "acc": 0.56, "entropy": 0.985, "ret": -0.055553, "capital": 9444.47, "trades": 1519, "positions": 2, "exposure": 0.02, "predictions": 3447}
data\v2.jsonl:687:{"tick": 3360, "t": "20:03:13", "acc": 0.565, "entropy": 0.9869, "ret": -0.055376, "capital": 9446.24, "trades": 1520, "positions": 3, "exposure": 0.03, "predictions": 3467}
data\v2.jsonl:688:{"tick": 3365, "t": "20:08:16", "acc": 0.57, "entropy": 0.9866, "ret": -0.055355, "capital": 9446.45, "trades": 1523, "positions": 1, "exposure": 0.01, "predictions": 3487}
data\v2.jsonl:689:{"tick": 3370, "t": "20:13:18", "acc": 0.57, "entropy": 0.9874, "ret": -0.054365, "capital": 9456.35, "trades": 1524, "positions": 2, "exposure": 0.02, "predictions": 3507}
data\v2.jsonl:690:{"tick": 3375, "t": "20:18:20", "acc": 0.57, "entropy": 0.9862, "ret": -0.054902, "capital": 9450.98, "trades": 1526, "positions": 2, "exposure": 0.02, "predictions": 3527}
data\v2.jsonl:691:{"tick": 3380, "t": "20:23:22", "acc": 0.545, "entropy": 0.9876, "ret": -0.054171, "capital": 9458.29, "trades": 1528, "positions": 3, "exposure": 0.03, "predictions": 3547}
data\v2.jsonl:692:{"tick": 3385, "t": "20:28:24", "acc": 0.525, "entropy": 0.9912, "ret": -0.055757, "capital": 9442.43, "trades": 1533, "positions": 0, "exposure": 0, "predictions": 3567}
data\v2.jsonl:693:{"tick": 3390, "t": "20:33:26", "acc": 0.49, "entropy": 0.9882, "ret": -0.056977, "capital": 9430.23, "trades": 1535, "positions": 1, "exposure": 0.01, "predictions": 3587}
data\v2.jsonl:694:{"tick": 3395, "t": "20:38:29", "acc": 0.49, "entropy": 0.9906, "ret": -0.056367, "capital": 9436.33, "trades": 1538, "positions": 0, "exposure": 0, "predictions": 3607}
data\v2.jsonl:695:{"tick": 3400, "t": "20:43:31", "acc": 0.505, "entropy": 0.9881, "ret": -0.056466, "capital": 9435.34, "trades": 1539, "positions": 2, "exposure": 0.02, "predictions": 3627}
data\v2.jsonl:696:{"tick": 3405, "t": "20:48:33", "acc": 0.495, "entropy": 0.9891, "ret": -0.056506, "capital": 9434.94, "trades": 1542, "positions": 3, "exposure": 0.03, "predictions": 3647}
data\v2.jsonl:697:{"tick": 3410, "t": "20:53:35", "acc": 0.48, "entropy": 0.9884, "ret": -0.056259, "capital": 9437.41, "trades": 1547, "positions": 1, "exposure": 0.01, "predictions": 3667}
data\v2.jsonl:698:{"tick": 3415, "t": "20:58:37", "acc": 0.495, "entropy": 0.9881, "ret": -0.056217, "capital": 9437.83, "trades": 1551, "positions": 2, "exposure": 0.02, "predictions": 3687}
data\v2.jsonl:699:{"tick": 3420, "t": "21:03:39", "acc": 0.48, "entropy": 0.9902, "ret": -0.056247, "capital": 9437.53, "trades": 1554, "positions": 3, "exposure": 0.03, "predictions": 3707}
data\v2.jsonl:700:{"tick": 3425, "t": "21:08:41", "acc": 0.475, "entropy": 0.9892, "ret": -0.056379, "capital": 9436.21, "trades": 1559, "positions": 1, "exposure": 0.01, "predictions": 3727}
data\v2.jsonl:701:{"tick": 3430, "t": "21:13:43", "acc": 0.475, "entropy": 0.9916, "ret": -0.057116, "capital": 9428.84, "trades": 1561, "positions": 2, "exposure": 0.02, "predictions": 3747}
data\v2.jsonl:702:{"tick": 3435, "t": "21:18:45", "acc": 0.49, "entropy": 0.9923, "ret": -0.057352, "capital": 9426.48, "trades": 1564, "positions": 0, "exposure": 0, "predictions": 3767}
data\v2.jsonl:703:{"tick": 3440, "t": "21:23:47", "acc": 0.505, "entropy": 0.993, "ret": -0.057213, "capital": 9427.87, "trades": 1567, "positions": 2, "exposure": 0.02, "predictions": 3787}
data\v2.jsonl:704:{"tick": 3445, "t": "21:28:49", "acc": 0.51, "entropy": 0.9911, "ret": -0.05658, "capital": 9434.2, "trades": 1571, "positions": 2, "exposure": 0.02, "predictions": 3807}
data\v2.jsonl:705:{"tick": 3450, "t": "21:33:51", "acc": 0.51, "entropy": 0.9904, "ret": -0.056613, "capital": 9433.87, "trades": 1574, "positions": 2, "exposure": 0.02, "predictions": 3827}
data\v2.jsonl:706:{"tick": 3455, "t": "21:38:54", "acc": 0.525, "entropy": 0.9919, "ret": -0.056608, "capital": 9433.92, "trades": 1575, "positions": 4, "exposure": 0.04, "predictions": 3847}
data\v2.jsonl:707:{"tick": 3460, "t": "21:43:56", "acc": 0.525, "entropy": 0.9897, "ret": -0.056253, "capital": 9437.47, "trades": 1577, "positions": 2, "exposure": 0.02, "predictions": 3867}
data\v2.jsonl:708:{"tick": 3465, "t": "21:48:58", "acc": 0.5, "entropy": 0.9898, "ret": -0.056253, "capital": 9437.47, "trades": 1577, "positions": 3, "exposure": 0.03, "predictions": 3887}
data\v2.jsonl:709:{"tick": 3470, "t": "21:54:00", "acc": 0.525, "entropy": 0.9882, "ret": -0.056253, "capital": 9437.47, "trades": 1577, "positions": 3, "exposure": 0.03, "predictions": 3907}
data\v2.jsonl:710:{"tick": 3475, "t": "21:59:02", "acc": 0.515, "entropy": 0.9881, "ret": -0.055888, "capital": 9441.12, "trades": 1581, "positions": 1, "exposure": 0.01, "predictions": 3927}
data\v2.jsonl:711:{"tick": 3480, "t": "22:04:04", "acc": 0.5, "entropy": 0.988, "ret": -0.056627, "capital": 9433.73, "trades": 1584, "positions": 3, "exposure": 0.03, "predictions": 3947}
data\v2.jsonl:712:{"tick": 3485, "t": "22:09:06", "acc": 0.51, "entropy": 0.9904, "ret": -0.056784, "capital": 9432.16, "trades": 1586, "positions": 3, "exposure": 0.03, "predictions": 3967}
data\v2.jsonl:713:{"tick": 3490, "t": "22:14:08", "acc": 0.51, "entropy": 0.9867, "ret": -0.055904, "capital": 9440.96, "trades": 1590, "positions": 2, "exposure": 0.02, "predictions": 3987}
data\v2.jsonl:714:{"tick": 3495, "t": "22:19:10", "acc": 0.48, "entropy": 0.9912, "ret": -0.055843, "capital": 9441.57, "trades": 1593, "positions": 2, "exposure": 0.02, "predictions": 4007}
data\v2.jsonl:715:{"tick": 3500, "t": "22:24:12", "acc": 0.47, "entropy": 0.9898, "ret": -0.056183, "capital": 9438.17, "trades": 1596, "positions": 2, "exposure": 0.02, "predictions": 4027}
data\v2.jsonl:716:{"tick": 3505, "t": "22:29:14", "acc": 0.44, "entropy": 0.9876, "ret": -0.056215, "capital": 9437.85, "trades": 1597, "positions": 4, "exposure": 0.04, "predictions": 4047}
data\v2.jsonl:717:{"tick": 3510, "t": "22:34:16", "acc": 0.43, "entropy": 0.9872, "ret": -0.056581, "capital": 9434.19, "trades": 1600, "positions": 1, "exposure": 0.01, "predictions": 4067}
data\v2.jsonl:718:{"tick": 3515, "t": "22:39:19", "acc": 0.43, "entropy": 0.9913, "ret": -0.057733, "capital": 9422.67, "trades": 1603, "positions": 2, "exposure": 0.02, "predictions": 4087}
data\v2.jsonl:719:{"tick": 3520, "t": "22:44:21", "acc": 0.425, "entropy": 0.9893, "ret": -0.057652, "capital": 9423.48, "trades": 1605, "positions": 2, "exposure": 0.02, "predictions": 4107}
data\v2.jsonl:720:{"tick": 3525, "t": "22:49:23", "acc": 0.415, "entropy": 0.988, "ret": -0.057378, "capital": 9426.22, "trades": 1608, "positions": 3, "exposure": 0.03, "predictions": 4127}
data\v2.jsonl:721:{"tick": 3530, "t": "22:54:25", "acc": 0.455, "entropy": 0.988, "ret": -0.05723, "capital": 9427.7, "trades": 1610, "positions": 1, "exposure": 0.01, "predictions": 4147}
data\v2.jsonl:722:{"tick": 3535, "t": "22:59:27", "acc": 0.47, "entropy": 0.989, "ret": -0.057503, "capital": 9424.97, "trades": 1614, "positions": 1, "exposure": 0.01, "predictions": 4167}
data\v2.jsonl:723:{"tick": 3540, "t": "23:04:29", "acc": 0.46, "entropy": 0.9902, "ret": -0.057659, "capital": 9423.41, "trades": 1617, "positions": 3, "exposure": 0.03, "predictions": 4187}
data\v2.jsonl:724:{"tick": 3545, "t": "23:09:32", "acc": 0.48, "entropy": 0.9872, "ret": -0.057751, "capital": 9422.49, "trades": 1620, "positions": 4, "exposure": 0.04, "predictions": 4207}
data\v2.jsonl:725:{"tick": 3550, "t": "23:14:34", "acc": 0.475, "entropy": 0.9848, "ret": -0.057814, "capital": 9421.86, "trades": 1623, "positions": 2, "exposure": 0.02, "predictions": 4227}
data\v2.jsonl:726:{"tick": 3555, "t": "23:19:36", "acc": 0.51, "entropy": 0.9884, "ret": -0.057555, "capital": 9424.45, "trades": 1626, "positions": 1, "exposure": 0.01, "predictions": 4247}
data\v2.jsonl:727:{"tick": 3560, "t": "23:24:38", "acc": 0.515, "entropy": 0.9852, "ret": -0.057595, "capital": 9424.05, "trades": 1629, "positions": 1, "exposure": 0.01, "predictions": 4267}
data\v2.jsonl:728:{"tick": 3565, "t": "23:29:40", "acc": 0.525, "entropy": 0.9878, "ret": -0.057045, "capital": 9429.55, "trades": 1631, "positions": 3, "exposure": 0.03, "predictions": 4287}
data\v2.jsonl:729:{"tick": 3570, "t": "23:34:42", "acc": 0.525, "entropy": 0.9888, "ret": -0.056732, "capital": 9432.68, "trades": 1636, "positions": 2, "exposure": 0.02, "predictions": 4307}
data\v2.jsonl:730:{"tick": 3575, "t": "23:39:44", "acc": 0.545, "entropy": 0.9876, "ret": -0.056313, "capital": 9436.87, "trades": 1639, "positions": 3, "exposure": 0.03, "predictions": 4327}
data\v2.jsonl:731:{"tick": 3580, "t": "23:44:46", "acc": 0.535, "entropy": 0.9832, "ret": -0.056865, "capital": 9431.35, "trades": 1643, "positions": 1, "exposure": 0.01, "predictions": 4347}
data\v2.jsonl:732:{"tick": 3585, "t": "23:49:48", "acc": 0.5, "entropy": 0.9848, "ret": -0.0569, "capital": 9431.0, "trades": 1646, "positions": 1, "exposure": 0.01, "predictions": 4367}
data\v2.jsonl:733:{"tick": 3590, "t": "23:54:50", "acc": 0.505, "entropy": 0.9841, "ret": -0.057312, "capital": 9426.88, "trades": 1650, "positions": 4, "exposure": 0.04, "predictions": 4387}
data\v2.jsonl:734:{"tick": 3595, "t": "23:59:52", "acc": 0.49, "entropy": 0.9853, "ret": -0.057947, "capital": 9420.53, "trades": 1654, "positions": 1, "exposure": 0.01, "predictions": 4407}
data\v2.jsonl:735:{"tick": 3600, "t": "00:04:54", "acc": 0.495, "entropy": 0.9863, "ret": -0.058164, "capital": 9418.36, "trades": 1655, "positions": 3, "exposure": 0.03, "predictions": 4427}
data\v2.jsonl:736:{"tick": 3605, "t": "00:09:57", "acc": 0.5, "entropy": 0.987, "ret": -0.057928, "capital": 9420.72, "trades": 1657, "positions": 2, "exposure": 0.02, "predictions": 4447}
data\v2.jsonl:737:{"tick": 3610, "t": "00:14:59", "acc": 0.485, "entropy": 0.9867, "ret": -0.057377, "capital": 9426.23, "trades": 1661, "positions": 2, "exposure": 0.02, "predictions": 4467}
data\v2.jsonl:738:{"tick": 3615, "t": "00:20:01", "acc": 0.49, "entropy": 0.9864, "ret": -0.057178, "capital": 9428.22, "trades": 1663, "positions": 3, "exposure": 0.03, "predictions": 4487}
data\v2.jsonl:739:{"tick": 3620, "t": "00:25:03", "acc": 0.495, "entropy": 0.9828, "ret": -0.057188, "capital": 9428.12, "trades": 1667, "positions": 3, "exposure": 0.03, "predictions": 4507}
data\v2.jsonl:740:{"tick": 3625, "t": "00:30:06", "acc": 0.505, "entropy": 0.9849, "ret": -0.056805, "capital": 9431.95, "trades": 1671, "positions": 2, "exposure": 0.02, "predictions": 4527}
data\v2.jsonl:741:{"tick": 3630, "t": "00:35:08", "acc": 0.51, "entropy": 0.9878, "ret": -0.056975, "capital": 9430.25, "trades": 1677, "positions": 2, "exposure": 0.02, "predictions": 4547}
data\v2.jsonl:742:{"tick": 3635, "t": "00:40:10", "acc": 0.52, "entropy": 0.9914, "ret": -0.057372, "capital": 9426.28, "trades": 1679, "positions": 3, "exposure": 0.03, "predictions": 4567}
data\v2.jsonl:743:{"tick": 3640, "t": "00:45:12", "acc": 0.515, "entropy": 0.9912, "ret": -0.057426, "capital": 9425.74, "trades": 1681, "positions": 2, "exposure": 0.02, "predictions": 4586}
data\v2.jsonl:744:{"tick": 3645, "t": "00:50:14", "acc": 0.51, "entropy": 0.99, "ret": -0.057721, "capital": 9422.79, "trades": 1684, "positions": 1, "exposure": 0.01, "predictions": 4606}
data\v2.jsonl:745:{"tick": 3650, "t": "00:55:16", "acc": 0.51, "entropy": 0.9906, "ret": -0.058175, "capital": 9418.25, "trades": 1687, "positions": 0, "exposure": 0, "predictions": 4626}
data\v2.jsonl:746:{"tick": 3655, "t": "01:00:18", "acc": 0.495, "entropy": 0.9891, "ret": -0.058335, "capital": 9416.65, "trades": 1689, "positions": 1, "exposure": 0.01, "predictions": 4646}
data\v2.jsonl:747:{"tick": 3660, "t": "01:05:21", "acc": 0.515, "entropy": 0.9902, "ret": -0.058176, "capital": 9418.24, "trades": 1692, "positions": 0, "exposure": 0, "predictions": 4666}
data\v2.jsonl:748:{"tick": 3665, "t": "01:10:36", "acc": 0.5, "entropy": 0.9912, "ret": -0.05898, "capital": 9410.2, "trades": 1696, "positions": 1, "exposure": 0.01, "predictions": 4686}
data\v2.jsonl:749:{"tick": 3670, "t": "01:15:42", "acc": 0.495, "entropy": 0.9929, "ret": -0.058103, "capital": 9418.97, "trades": 1699, "positions": 2, "exposure": 0.02, "predictions": 4706}
data\v2.jsonl:750:{"tick": 3675, "t": "01:20:52", "acc": 0.475, "entropy": 0.9923, "ret": -0.05819, "capital": 9418.1, "trades": 1702, "positions": 1, "exposure": 0.01, "predictions": 4726}
data\v2.jsonl:751:{"tick": 3680, "t": "01:25:58", "acc": 0.465, "entropy": 0.991, "ret": -0.059211, "capital": 9407.89, "trades": 1708, "positions": 0, "exposure": 0, "predictions": 4746}
data\v2.jsonl:752:{"tick": 3685, "t": "01:31:10", "acc": 0.465, "entropy": 0.9907, "ret": -0.059116, "capital": 9408.84, "trades": 1710, "positions": 2, "exposure": 0.02, "predictions": 4766}
data\v2.jsonl:753:{"tick": 3690, "t": "01:36:19", "acc": 0.485, "entropy": 0.99, "ret": -0.058909, "capital": 9410.91, "trades": 1714, "positions": 2, "exposure": 0.02, "predictions": 4786}
data\v2.jsonl:754:{"tick": 3695, "t": "01:41:24", "acc": 0.495, "entropy": 0.9883, "ret": -0.059113, "capital": 9408.87, "trades": 1717, "positions": 4, "exposure": 0.04, "predictions": 4806}
data\v2.jsonl:755:{"tick": 3700, "t": "01:46:26", "acc": 0.49, "entropy": 0.9878, "ret": -0.060303, "capital": 9396.97, "trades": 1723, "positions": 2, "exposure": 0.02, "predictions": 4826}
data\v2.jsonl:756:{"tick": 3705, "t": "01:51:28", "acc": 0.46, "entropy": 0.9888, "ret": -0.060795, "capital": 9392.05, "trades": 1727, "positions": 2, "exposure": 0.02, "predictions": 4846}
data\v2.jsonl:757:{"tick": 3710, "t": "01:56:30", "acc": 0.435, "entropy": 0.9871, "ret": -0.061636, "capital": 9383.64, "trades": 1731, "positions": 2, "exposure": 0.02, "predictions": 4866}
data\v2.jsonl:758:{"tick": 3715, "t": "02:01:32", "acc": 0.435, "entropy": 0.9864, "ret": -0.061823, "capital": 9381.77, "trades": 1735, "positions": 1, "exposure": 0.01, "predictions": 4886}
data\v2.jsonl:759:{"tick": 3720, "t": "02:06:34", "acc": 0.455, "entropy": 0.9881, "ret": -0.061857, "capital": 9381.43, "trades": 1738, "positions": 1, "exposure": 0.01, "predictions": 4906}
data\v2.jsonl:760:{"tick": 3725, "t": "02:11:36", "acc": 0.465, "entropy": 0.986, "ret": -0.062019, "capital": 9379.81, "trades": 1739, "positions": 2, "exposure": 0.02, "predictions": 4926}
data\v2.jsonl:761:{"tick": 3730, "t": "02:16:39", "acc": 0.47, "entropy": 0.9878, "ret": -0.062163, "capital": 9378.37, "trades": 1743, "positions": 1, "exposure": 0.01, "predictions": 4946}
data\v2.jsonl:762:{"tick": 3735, "t": "02:21:41", "acc": 0.455, "entropy": 0.9886, "ret": -0.062047, "capital": 9379.53, "trades": 1745, "positions": 3, "exposure": 0.03, "predictions": 4966}
data\v2.jsonl:763:{"tick": 3740, "t": "02:26:43", "acc": 0.435, "entropy": 0.9893, "ret": -0.062073, "capital": 9379.27, "trades": 1748, "positions": 1, "exposure": 0.01, "predictions": 4986}
data\v2.jsonl:764:{"tick": 3745, "t": "02:31:51", "acc": 0.425, "entropy": 0.992, "ret": -0.062187, "capital": 9378.13, "trades": 1749, "positions": 3, "exposure": 0.03, "predictions": 5006}
data\v2.jsonl:765:{"tick": 3750, "t": "02:36:57", "acc": 0.43, "entropy": 0.9909, "ret": -0.062198, "capital": 9378.02, "trades": 1752, "positions": 3, "exposure": 0.03, "predictions": 5026}
data\v2.jsonl:766:{"tick": 3755, "t": "02:42:06", "acc": 0.47, "entropy": 0.9889, "ret": -0.062864, "capital": 9371.36, "trades": 1754, "positions": 2, "exposure": 0.02, "predictions": 5046}
data\v2.jsonl:767:{"tick": 3760, "t": "02:47:09", "acc": 0.47, "entropy": 0.987, "ret": -0.062749, "capital": 9372.51, "trades": 1757, "positions": 3, "exposure": 0.03, "predictions": 5066}
data\v2.jsonl:768:{"tick": 3765, "t": "02:52:11", "acc": 0.475, "entropy": 0.9865, "ret": -0.062048, "capital": 9379.52, "trades": 1759, "positions": 3, "exposure": 0.03, "predictions": 5086}
data\v2.jsonl:769:{"tick": 3770, "t": "02:57:13", "acc": 0.48, "entropy": 0.9871, "ret": -0.061995, "capital": 9380.05, "trades": 1762, "positions": 1, "exposure": 0.01, "predictions": 5106}
data\v2.jsonl:770:{"tick": 3775, "t": "03:02:15", "acc": 0.465, "entropy": 0.9845, "ret": -0.061995, "capital": 9380.05, "trades": 1762, "positions": 3, "exposure": 0.03, "predictions": 5125}
data\v2.jsonl:771:{"tick": 3780, "t": "03:07:17", "acc": 0.46, "entropy": 0.9883, "ret": -0.06201, "capital": 9379.9, "trades": 1764, "positions": 2, "exposure": 0.02, "predictions": 5145}
data\v2.jsonl:772:{"tick": 3785, "t": "03:12:19", "acc": 0.475, "entropy": 0.9881, "ret": -0.06222, "capital": 9377.8, "trades": 1766, "positions": 2, "exposure": 0.02, "predictions": 5165}
data\v2.jsonl:773:{"tick": 3790, "t": "03:17:21", "acc": 0.49, "entropy": 0.9875, "ret": -0.062502, "capital": 9374.98, "trades": 1767, "positions": 3, "exposure": 0.03, "predictions": 5185}
data\v2.jsonl:774:{"tick": 3795, "t": "03:22:23", "acc": 0.5, "entropy": 0.9869, "ret": -0.062343, "capital": 9376.57, "trades": 1770, "positions": 2, "exposure": 0.02, "predictions": 5205}
data\v2.jsonl:775:{"tick": 3800, "t": "03:27:25", "acc": 0.5, "entropy": 0.9851, "ret": -0.0625, "capital": 9375.0, "trades": 1772, "positions": 3, "exposure": 0.03, "predictions": 5225}
data\v2.jsonl:776:{"tick": 3805, "t": "03:32:27", "acc": 0.485, "entropy": 0.9906, "ret": -0.062553, "capital": 9374.47, "trades": 1777, "positions": 1, "exposure": 0.01, "predictions": 5245}
data\v2.jsonl:777:{"tick": 3810, "t": "03:37:29", "acc": 0.47, "entropy": 0.9897, "ret": -0.062699, "capital": 9373.01, "trades": 1780, "positions": 3, "exposure": 0.03, "predictions": 5265}
data\v2.jsonl:778:{"tick": 3815, "t": "03:42:31", "acc": 0.48, "entropy": 0.9898, "ret": -0.063588, "capital": 9364.12, "trades": 1785, "positions": 2, "exposure": 0.02, "predictions": 5285}
data\v2.jsonl:779:{"tick": 3820, "t": "03:47:33", "acc": 0.45, "entropy": 0.9926, "ret": -0.063683, "capital": 9363.17, "trades": 1788, "positions": 2, "exposure": 0.02, "predictions": 5305}
data\v2.jsonl:780:{"tick": 3825, "t": "03:52:35", "acc": 0.47, "entropy": 0.9918, "ret": -0.06379, "capital": 9362.1, "trades": 1790, "positions": 2, "exposure": 0.02, "predictions": 5325}
data\v2.jsonl:781:{"tick": 3830, "t": "03:57:37", "acc": 0.475, "entropy": 0.9931, "ret": -0.064165, "capital": 9358.35, "trades": 1793, "positions": 2, "exposure": 0.02, "predictions": 5345}
data\v2.jsonl:782:{"tick": 3835, "t": "04:02:39", "acc": 0.47, "entropy": 0.9903, "ret": -0.064395, "capital": 9356.05, "trades": 1796, "positions": 3, "exposure": 0.03, "predictions": 5365}
data\v2.jsonl:783:{"tick": 3840, "t": "04:07:41", "acc": 0.47, "entropy": 0.9887, "ret": -0.064164, "capital": 9358.36, "trades": 1800, "positions": 0, "exposure": 0, "predictions": 5385}
data\v2.jsonl:784:{"tick": 3845, "t": "04:12:44", "acc": 0.465, "entropy": 0.9881, "ret": -0.064164, "capital": 9358.36, "trades": 1800, "positions": 2, "exposure": 0.02, "predictions": 5405}
data\v2.jsonl:785:{"tick": 3850, "t": "04:18:06", "acc": 0.485, "entropy": 0.9888, "ret": -0.064325, "capital": 9356.75, "trades": 1801, "positions": 2, "exposure": 0.02, "predictions": 5417}
data\v2.jsonl:786:{"tick": 3855, "t": "04:23:08", "acc": 0.485, "entropy": 0.9888, "ret": -0.064325, "capital": 9356.75, "trades": 1801, "positions": 2, "exposure": 0.02, "predictions": 5417}
data\v2.jsonl:787:{"tick": 3860, "t": "04:28:10", "acc": 0.49, "entropy": 0.989, "ret": -0.064289, "capital": 9357.11, "trades": 1804, "positions": 1, "exposure": 0.01, "predictions": 5437}
data\v2.jsonl:788:{"tick": 3865, "t": "04:33:12", "acc": 0.505, "entropy": 0.9873, "ret": -0.064175, "capital": 9358.25, "trades": 1806, "positions": 1, "exposure": 0.01, "predictions": 5457}
data\v2.jsonl:789:{"tick": 3870, "t": "04:38:14", "acc": 0.52, "entropy": 0.9919, "ret": -0.064326, "capital": 9356.74, "trades": 1809, "positions": 2, "exposure": 0.02, "predictions": 5477}
data\v2.jsonl:790:{"tick": 3875, "t": "04:43:17", "acc": 0.515, "entropy": 0.9865, "ret": -0.065191, "capital": 9348.09, "trades": 1815, "positions": 1, "exposure": 0.01, "predictions": 5497}
data\v2.jsonl:791:{"tick": 3880, "t": "04:48:19", "acc": 0.515, "entropy": 0.9875, "ret": -0.065623, "capital": 9343.77, "trades": 1820, "positions": 1, "exposure": 0.01, "predictions": 5517}
data\v2.jsonl:792:{"tick": 3885, "t": "04:53:21", "acc": 0.52, "entropy": 0.9872, "ret": -0.065496, "capital": 9345.04, "trades": 1822, "positions": 2, "exposure": 0.02, "predictions": 5537}
data\v2.jsonl:793:{"tick": 3890, "t": "04:58:23", "acc": 0.5, "entropy": 0.9886, "ret": -0.065549, "capital": 9344.51, "trades": 1825, "positions": 3, "exposure": 0.03, "predictions": 5557}
data\v2.jsonl:794:{"tick": 3895, "t": "05:03:25", "acc": 0.5, "entropy": 0.9903, "ret": -0.065854, "capital": 9341.46, "trades": 1829, "positions": 3, "exposure": 0.03, "predictions": 5577}
data\v2.jsonl:795:{"tick": 3900, "t": "05:08:27", "acc": 0.51, "entropy": 0.986, "ret": -0.065101, "capital": 9348.99, "trades": 1833, "positions": 2, "exposure": 0.02, "predictions": 5597}
data\v2.jsonl:796:{"tick": 3905, "t": "05:13:30", "acc": 0.505, "entropy": 0.9903, "ret": -0.064891, "capital": 9351.09, "trades": 1835, "positions": 2, "exposure": 0.02, "predictions": 5617}
data\v2.jsonl:797:{"tick": 3910, "t": "05:18:31", "acc": 0.495, "entropy": 0.9899, "ret": -0.065903, "capital": 9340.97, "trades": 1838, "positions": 2, "exposure": 0.02, "predictions": 5637}
data\v2.jsonl:798:{"tick": 3915, "t": "05:23:34", "acc": 0.51, "entropy": 0.9858, "ret": -0.066011, "capital": 9339.89, "trades": 1840, "positions": 2, "exposure": 0.02, "predictions": 5657}
data\v2.jsonl:799:{"tick": 3920, "t": "05:28:36", "acc": 0.495, "entropy": 0.9842, "ret": -0.065813, "capital": 9341.87, "trades": 1843, "positions": 3, "exposure": 0.03, "predictions": 5677}
data\v2.jsonl:800:{"tick": 3925, "t": "05:33:38", "acc": 0.485, "entropy": 0.9884, "ret": -0.065005, "capital": 9349.95, "trades": 1846, "positions": 1, "exposure": 0.01, "predictions": 5697}
data\v2.jsonl:801:{"tick": 3930, "t": "05:38:40", "acc": 0.495, "entropy": 0.988, "ret": -0.06489, "capital": 9351.1, "trades": 1848, "positions": 3, "exposure": 0.03, "predictions": 5717}
data\v2.jsonl:802:{"tick": 3935, "t": "05:43:43", "acc": 0.49, "entropy": 0.9894, "ret": -0.064785, "capital": 9352.15, "trades": 1851, "positions": 1, "exposure": 0.01, "predictions": 5737}
data\v2.jsonl:803:{"tick": 3940, "t": "05:48:45", "acc": 0.505, "entropy": 0.9898, "ret": -0.064699, "capital": 9353.01, "trades": 1852, "positions": 3, "exposure": 0.03, "predictions": 5757}
data\v2.jsonl:804:{"tick": 3945, "t": "05:53:48", "acc": 0.51, "entropy": 0.9893, "ret": -0.064871, "capital": 9351.29, "trades": 1856, "positions": 3, "exposure": 0.03, "predictions": 5777}
data\v2.jsonl:805:{"tick": 3950, "t": "05:58:53", "acc": 0.515, "entropy": 0.9886, "ret": -0.065071, "capital": 9349.29, "trades": 1860, "positions": 3, "exposure": 0.03, "predictions": 5797}
data\v2.jsonl:806:{"tick": 3955, "t": "06:03:59", "acc": 0.515, "entropy": 0.9872, "ret": -0.065158, "capital": 9348.42, "trades": 1864, "positions": 1, "exposure": 0.01, "predictions": 5817}
data\v2.jsonl:807:{"tick": 3960, "t": "06:09:01", "acc": 0.515, "entropy": 0.9898, "ret": -0.065086, "capital": 9349.14, "trades": 1868, "positions": 1, "exposure": 0.01, "predictions": 5837}
data\v2.jsonl:808:{"tick": 3965, "t": "06:14:03", "acc": 0.495, "entropy": 0.9914, "ret": -0.065322, "capital": 9346.78, "trades": 1872, "positions": 3, "exposure": 0.03, "predictions": 5857}
data\v2.jsonl:809:{"tick": 3970, "t": "06:19:05", "acc": 0.495, "entropy": 0.9897, "ret": -0.065441, "capital": 9345.59, "trades": 1875, "positions": 0, "exposure": 0, "predictions": 5877}
data\v2.jsonl:810:{"tick": 3975, "t": "06:24:07", "acc": 0.515, "entropy": 0.9901, "ret": -0.065476, "capital": 9345.24, "trades": 1879, "positions": 2, "exposure": 0.02, "predictions": 5897}
data\v2.jsonl:811:{"tick": 3980, "t": "06:29:09", "acc": 0.515, "entropy": 0.989, "ret": -0.065807, "capital": 9341.93, "trades": 1880, "positions": 2, "exposure": 0.02, "predictions": 5917}
data\v2.jsonl:812:{"tick": 3985, "t": "06:34:11", "acc": 0.51, "entropy": 0.9898, "ret": -0.065902, "capital": 9340.98, "trades": 1884, "positions": 1, "exposure": 0.01, "predictions": 5937}
data\v2.jsonl:813:{"tick": 3990, "t": "06:39:13", "acc": 0.505, "entropy": 0.9889, "ret": -0.065994, "capital": 9340.06, "trades": 1886, "positions": 2, "exposure": 0.02, "predictions": 5957}
data\v2.jsonl:814:{"tick": 3995, "t": "06:44:17", "acc": 0.49, "entropy": 0.9874, "ret": -0.066248, "capital": 9337.52, "trades": 1889, "positions": 3, "exposure": 0.03, "predictions": 5977}
data\v2.jsonl:815:{"tick": 4000, "t": "06:49:24", "acc": 0.47, "entropy": 0.9865, "ret": -0.066032, "capital": 9339.68, "trades": 1892, "positions": 2, "exposure": 0.02, "predictions": 5997}
data\v2.jsonl:816:{"tick": 4005, "t": "06:54:30", "acc": 0.465, "entropy": 0.9866, "ret": -0.065926, "capital": 9340.74, "trades": 1895, "positions": 2, "exposure": 0.02, "predictions": 6017}
data\v2.jsonl:817:{"tick": 4010, "t": "06:59:32", "acc": 0.465, "entropy": 0.9899, "ret": -0.06612, "capital": 9338.8, "trades": 1897, "positions": 2, "exposure": 0.02, "predictions": 6037}
data\v2.jsonl:818:{"tick": 4015, "t": "07:04:34", "acc": 0.48, "entropy": 0.9902, "ret": -0.065887, "capital": 9341.13, "trades": 1901, "positions": 2, "exposure": 0.02, "predictions": 6057}
data\v2.jsonl:819:{"tick": 4020, "t": "07:09:36", "acc": 0.475, "entropy": 0.991, "ret": -0.065042, "capital": 9349.58, "trades": 1904, "positions": 2, "exposure": 0.02, "predictions": 6077}
data\v2.jsonl:820:{"tick": 4025, "t": "07:14:38", "acc": 0.475, "entropy": 0.99, "ret": -0.064918, "capital": 9350.82, "trades": 1908, "positions": 2, "exposure": 0.02, "predictions": 6097}
data\v2.jsonl:821:{"tick": 4030, "t": "07:19:41", "acc": 0.455, "entropy": 0.9882, "ret": -0.064848, "capital": 9351.52, "trades": 1910, "positions": 1, "exposure": 0.01, "predictions": 6117}
data\v2.jsonl:822:{"tick": 4035, "t": "07:24:43", "acc": 0.455, "entropy": 0.9894, "ret": -0.064691, "capital": 9353.09, "trades": 1913, "positions": 2, "exposure": 0.02, "predictions": 6137}
data\v2.jsonl:823:{"tick": 4040, "t": "07:29:45", "acc": 0.455, "entropy": 0.9894, "ret": -0.064734, "capital": 9352.66, "trades": 1916, "positions": 2, "exposure": 0.02, "predictions": 6157}
data\v2.jsonl:824:{"tick": 4045, "t": "07:34:47", "acc": 0.46, "entropy": 0.9887, "ret": -0.065297, "capital": 9347.03, "trades": 1920, "positions": 2, "exposure": 0.02, "predictions": 6177}
data\v2.jsonl:825:{"tick": 4050, "t": "07:39:49", "acc": 0.46, "entropy": 0.9884, "ret": -0.065306, "capital": 9346.94, "trades": 1924, "positions": 3, "exposure": 0.03, "predictions": 6197}
data\v2.jsonl:826:{"tick": 4055, "t": "07:44:52", "acc": 0.46, "entropy": 0.9914, "ret": -0.065515, "capital": 9344.85, "trades": 1927, "positions": 3, "exposure": 0.03, "predictions": 6217}
data\v2.jsonl:827:{"tick": 4060, "t": "07:49:54", "acc": 0.46, "entropy": 0.9892, "ret": -0.065782, "capital": 9342.18, "trades": 1930, "positions": 3, "exposure": 0.03, "predictions": 6237}
data\v2.jsonl:828:{"tick": 4065, "t": "07:54:56", "acc": 0.43, "entropy": 0.9902, "ret": -0.066482, "capital": 9335.18, "trades": 1936, "positions": 2, "exposure": 0.02, "predictions": 6257}
data\v2.jsonl:829:{"tick": 4070, "t": "08:00:07", "acc": 0.445, "entropy": 0.9938, "ret": -0.066709, "capital": 9332.91, "trades": 1940, "positions": 3, "exposure": 0.03, "predictions": 6277}
data\v2.jsonl:830:{"tick": 4075, "t": "08:05:13", "acc": 0.435, "entropy": 0.9921, "ret": -0.066973, "capital": 9330.27, "trades": 1944, "positions": 2, "exposure": 0.02, "predictions": 6297}
data\v2.jsonl:831:{"tick": 4080, "t": "08:10:16", "acc": 0.43, "entropy": 0.9891, "ret": -0.067018, "capital": 9329.82, "trades": 1946, "positions": 3, "exposure": 0.03, "predictions": 6317}
data\v2.jsonl:832:{"tick": 4085, "t": "08:15:22", "acc": 0.43, "entropy": 0.9906, "ret": -0.066543, "capital": 9334.57, "trades": 1949, "positions": 3, "exposure": 0.03, "predictions": 6337}
data\v2.jsonl:833:{"tick": 4090, "t": "08:20:24", "acc": 0.435, "entropy": 0.9921, "ret": -0.066779, "capital": 9332.21, "trades": 1953, "positions": 2, "exposure": 0.02, "predictions": 6357}
data\v2.jsonl:834:{"tick": 4095, "t": "08:25:26", "acc": 0.455, "entropy": 0.9912, "ret": -0.065121, "capital": 9348.79, "trades": 1955, "positions": 2, "exposure": 0.02, "predictions": 6377}
data\v2.jsonl:835:{"tick": 4100, "t": "08:30:28", "acc": 0.455, "entropy": 0.9891, "ret": -0.065717, "capital": 9342.83, "trades": 1959, "positions": 1, "exposure": 0.01, "predictions": 6397}
data\v2.jsonl:836:{"tick": 4105, "t": "08:35:30", "acc": 0.46, "entropy": 0.9884, "ret": -0.065175, "capital": 9348.25, "trades": 1962, "positions": 4, "exposure": 0.04, "predictions": 6417}
data\v2.jsonl:837:{"tick": 4110, "t": "08:40:33", "acc": 0.455, "entropy": 0.9875, "ret": -0.065366, "capital": 9346.34, "trades": 1967, "positions": 3, "exposure": 0.03, "predictions": 6437}
data\v2.jsonl:838:{"tick": 4115, "t": "08:45:56", "acc": 0.47, "entropy": 0.9868, "ret": -0.064102, "capital": 9358.98, "trades": 1971, "positions": 0, "exposure": 0, "predictions": 6453}
data\v2.jsonl:839:{"tick": 4120, "t": "08:50:58", "acc": 0.475, "entropy": 0.9862, "ret": -0.064024, "capital": 9359.76, "trades": 1974, "positions": 3, "exposure": 0.03, "predictions": 6473}
data\v2.jsonl:840:{"tick": 4125, "t": "08:56:00", "acc": 0.47, "entropy": 0.9895, "ret": -0.063711, "capital": 9362.89, "trades": 1980, "positions": 3, "exposure": 0.03, "predictions": 6493}
data\v2.jsonl:841:{"tick": 4130, "t": "09:01:02", "acc": 0.495, "entropy": 0.9845, "ret": -0.064327, "capital": 9356.73, "trades": 1983, "positions": 2, "exposure": 0.02, "predictions": 6513}
data\v2.jsonl:842:{"tick": 4135, "t": "09:06:05", "acc": 0.515, "entropy": 0.9833, "ret": -0.064762, "capital": 9352.38, "trades": 1986, "positions": 1, "exposure": 0.01, "predictions": 6533}
data\v2.jsonl:843:{"tick": 4140, "t": "09:11:08", "acc": 0.55, "entropy": 0.9863, "ret": -0.064111, "capital": 9358.89, "trades": 1989, "positions": 1, "exposure": 0.01, "predictions": 6553}
data\v2.jsonl:844:{"tick": 4145, "t": "09:16:11", "acc": 0.55, "entropy": 0.9866, "ret": -0.063474, "capital": 9365.26, "trades": 1992, "positions": 1, "exposure": 0.01, "predictions": 6573}
data\v2.jsonl:845:{"tick": 4150, "t": "09:21:13", "acc": 0.56, "entropy": 0.9902, "ret": -0.06303, "capital": 9369.7, "trades": 1995, "positions": 1, "exposure": 0.01, "predictions": 6593}
data\v2.jsonl:846:{"tick": 4155, "t": "09:26:15", "acc": 0.545, "entropy": 0.9897, "ret": -0.063116, "capital": 9368.84, "trades": 1997, "positions": 2, "exposure": 0.0218, "predictions": 6613}
data\v2.jsonl:847:{"tick": 4160, "t": "09:31:17", "acc": 0.59, "entropy": 0.9895, "ret": -0.061061, "capital": 9389.39, "trades": 2001, "positions": 1, "exposure": 0.0338, "predictions": 6632}
data\v2.jsonl:848:{"tick": 4165, "t": "09:36:20", "acc": 0.6, "entropy": 0.9906, "ret": -0.063109, "capital": 9368.91, "trades": 2006, "positions": 3, "exposure": 0.0535, "predictions": 6652}
data\v2.jsonl:849:{"tick": 4170, "t": "09:41:22", "acc": 0.6, "entropy": 0.9904, "ret": -0.062685, "capital": 9373.15, "trades": 2009, "positions": 2, "exposure": 0.0398, "predictions": 6672}
data\v2.jsonl:850:{"tick": 4175, "t": "09:46:24", "acc": 0.6, "entropy": 0.9872, "ret": -0.062733, "capital": 9372.67, "trades": 2011, "positions": 3, "exposure": 0.0588, "predictions": 6692}
data\v2.jsonl:851:{"tick": 4180, "t": "09:51:26", "acc": 0.585, "entropy": 0.9924, "ret": -0.06438, "capital": 9356.2, "trades": 2017, "positions": 1, "exposure": 0.0308, "predictions": 6712}
data\v2.jsonl:852:{"tick": 4185, "t": "09:56:28", "acc": 0.58, "entropy": 0.9908, "ret": -0.061173, "capital": 9388.27, "trades": 2019, "positions": 3, "exposure": 0.0634, "predictions": 6732}
data\v2.jsonl:853:{"tick": 4190, "t": "10:01:30", "acc": 0.55, "entropy": 0.9892, "ret": -0.061686, "capital": 9383.14, "trades": 2020, "positions": 4, "exposure": 0.0745, "predictions": 6752}
data\v2.jsonl:854:{"tick": 4195, "t": "10:06:32", "acc": 0.54, "entropy": 0.992, "ret": -0.06118, "capital": 9388.2, "trades": 2026, "positions": 1, "exposure": 0.0331, "predictions": 6772}
data\v2.jsonl:855:{"tick": 4200, "t": "10:11:34", "acc": 0.515, "entropy": 0.9876, "ret": -0.065259, "capital": 9347.41, "trades": 2028, "positions": 2, "exposure": 0.0598, "predictions": 6792}
data\v2.jsonl:856:{"tick": 4205, "t": "10:16:36", "acc": 0.535, "entropy": 0.9881, "ret": -0.066552, "capital": 9334.48, "trades": 2031, "positions": 4, "exposure": 0.1136, "predictions": 6812}
data\v2.jsonl:857:{"tick": 4210, "t": "10:21:38", "acc": 0.495, "entropy": 0.9887, "ret": -0.067718, "capital": 9322.82, "trades": 2036, "positions": 1, "exposure": 0.0112, "predictions": 6832}
data\v2.jsonl:858:{"tick": 4215, "t": "10:26:40", "acc": 0.48, "entropy": 0.988, "ret": -0.067774, "capital": 9322.26, "trades": 2038, "positions": 3, "exposure": 0.0459, "predictions": 6852}
data\v2.jsonl:859:{"tick": 4220, "t": "10:31:42", "acc": 0.465, "entropy": 0.9879, "ret": -0.073467, "capital": 9265.33, "trades": 2041, "positions": 1, "exposure": 0.0116, "predictions": 6872}
data\v2.jsonl:860:{"tick": 4225, "t": "10:36:44", "acc": 0.475, "entropy": 0.9869, "ret": -0.072287, "capital": 9277.13, "trades": 2045, "positions": 3, "exposure": 0.03, "predictions": 6892}
data\v2.jsonl:861:{"tick": 4230, "t": "10:41:47", "acc": 0.475, "entropy": 0.9849, "ret": -0.073205, "capital": 9267.95, "trades": 2049, "positions": 3, "exposure": 0.03, "predictions": 6912}
data\v2.jsonl:862:{"tick": 4235, "t": "10:46:49", "acc": 0.46, "entropy": 0.9891, "ret": -0.073631, "capital": 9263.69, "trades": 2055, "positions": 2, "exposure": 0.02, "predictions": 6932}
data\v2.jsonl:863:{"tick": 4240, "t": "10:51:51", "acc": 0.465, "entropy": 0.9881, "ret": -0.073609, "capital": 9263.91, "trades": 2058, "positions": 3, "exposure": 0.03, "predictions": 6952}
data\v2.jsonl:864:{"tick": 4245, "t": "10:56:53", "acc": 0.465, "entropy": 0.9884, "ret": -0.073766, "capital": 9262.34, "trades": 2059, "positions": 2, "exposure": 0.02, "predictions": 6972}
data\v2.jsonl:865:{"tick": 4250, "t": "11:01:55", "acc": 0.475, "entropy": 0.9873, "ret": -0.073398, "capital": 9266.02, "trades": 2062, "positions": 3, "exposure": 0.03, "predictions": 6992}
data\v2.jsonl:866:{"tick": 4255, "t": "11:06:57", "acc": 0.48, "entropy": 0.9885, "ret": -0.073265, "capital": 9267.35, "trades": 2064, "positions": 3, "exposure": 0.03, "predictions": 7012}
data\v2.jsonl:867:{"tick": 4260, "t": "11:11:59", "acc": 0.5, "entropy": 0.9877, "ret": -0.072641, "capital": 9273.59, "trades": 2066, "positions": 3, "exposure": 0.03, "predictions": 7032}
data\v2.jsonl:868:{"tick": 4265, "t": "11:17:02", "acc": 0.49, "entropy": 0.9875, "ret": -0.072702, "capital": 9272.98, "trades": 2069, "positions": 2, "exposure": 0.02, "predictions": 7052}
data\v2.jsonl:869:{"tick": 4270, "t": "11:22:04", "acc": 0.52, "entropy": 0.9865, "ret": -0.072699, "capital": 9273.01, "trades": 2070, "positions": 4, "exposure": 0.04, "predictions": 7072}
data\v2.jsonl:870:{"tick": 4275, "t": "11:27:06", "acc": 0.525, "entropy": 0.9878, "ret": -0.072228, "capital": 9277.72, "trades": 2074, "positions": 3, "exposure": 0.03, "predictions": 7092}
data\v2.jsonl:871:{"tick": 4280, "t": "11:32:08", "acc": 0.515, "entropy": 0.9851, "ret": -0.072446, "capital": 9275.54, "trades": 2077, "positions": 1, "exposure": 0.01, "predictions": 7112}
data\v2.jsonl:872:{"tick": 4285, "t": "11:37:37", "acc": 0.525, "entropy": 0.9876, "ret": -0.072142, "capital": 9278.58, "trades": 2080, "positions": 0, "exposure": 0, "predictions": 7131}
data\v2.jsonl:873:{"tick": 4290, "t": "11:42:39", "acc": 0.545, "entropy": 0.9884, "ret": -0.072431, "capital": 9275.69, "trades": 2081, "positions": 3, "exposure": 0.03, "predictions": 7151}
data\v2.jsonl:874:{"tick": 4295, "t": "11:47:41", "acc": 0.53, "entropy": 0.9872, "ret": -0.072895, "capital": 9271.05, "trades": 2084, "positions": 4, "exposure": 0.04, "predictions": 7171}
data\v2.jsonl:875:{"tick": 4300, "t": "11:52:43", "acc": 0.53, "entropy": 0.987, "ret": -0.072221, "capital": 9277.79, "trades": 2089, "positions": 2, "exposure": 0.02, "predictions": 7191}
data\v2.jsonl:876:{"tick": 4305, "t": "11:58:23", "acc": 0.525, "entropy": 0.9898, "ret": -0.072225, "capital": 9277.75, "trades": 2091, "positions": 1, "exposure": 0.01, "predictions": 7210}
data\v2.jsonl:877:{"tick": 4310, "t": "12:03:25", "acc": 0.51, "entropy": 0.9887, "ret": -0.072517, "capital": 9274.83, "trades": 2096, "positions": 0, "exposure": 0, "predictions": 7230}
data\v2.jsonl:878:{"tick": 4315, "t": "12:08:27", "acc": 0.51, "entropy": 0.984, "ret": -0.072605, "capital": 9273.95, "trades": 2097, "positions": 2, "exposure": 0.02, "predictions": 7250}
data\v2.jsonl:879:{"tick": 4320, "t": "12:13:29", "acc": 0.5, "entropy": 0.9881, "ret": -0.072669, "capital": 9273.31, "trades": 2101, "positions": 1, "exposure": 0.01, "predictions": 7270}
data\v2.jsonl:880:{"tick": 4325, "t": "12:18:32", "acc": 0.475, "entropy": 0.9888, "ret": -0.072597, "capital": 9274.03, "trades": 2102, "positions": 3, "exposure": 0.03, "predictions": 7290}
data\v2.jsonl:881:{"tick": 4330, "t": "12:23:34", "acc": 0.49, "entropy": 0.9881, "ret": -0.072684, "capital": 9273.16, "trades": 2107, "positions": 0, "exposure": 0, "predictions": 7310}
data\v2.jsonl:882:{"tick": 4335, "t": "12:28:36", "acc": 0.475, "entropy": 0.9861, "ret": -0.072035, "capital": 9279.65, "trades": 2110, "positions": 3, "exposure": 0.03, "predictions": 7330}
data\v2.jsonl:883:{"tick": 4340, "t": "12:33:38", "acc": 0.46, "entropy": 0.9862, "ret": -0.071103, "capital": 9288.97, "trades": 2115, "positions": 1, "exposure": 0.01, "predictions": 7350}
data\v2.jsonl:884:{"tick": 4345, "t": "12:38:40", "acc": 0.455, "entropy": 0.9849, "ret": -0.072027, "capital": 9279.73, "trades": 2118, "positions": 1, "exposure": 0.01, "predictions": 7370}
data\v2.jsonl:885:{"tick": 4350, "t": "12:43:42", "acc": 0.47, "entropy": 0.9849, "ret": -0.072018, "capital": 9279.82, "trades": 2120, "positions": 2, "exposure": 0.02, "predictions": 7390}
data\v2.jsonl:886:{"tick": 4355, "t": "12:48:45", "acc": 0.46, "entropy": 0.9855, "ret": -0.070755, "capital": 9292.45, "trades": 2123, "positions": 3, "exposure": 0.03, "predictions": 7410}
data\v2.jsonl:887:{"tick": 4360, "t": "12:53:47", "acc": 0.44, "entropy": 0.9837, "ret": -0.072001, "capital": 9279.99, "trades": 2125, "positions": 4, "exposure": 0.0462, "predictions": 7430}
data\v2.jsonl:888:{"tick": 4365, "t": "12:58:49", "acc": 0.445, "entropy": 0.9818, "ret": -0.073513, "capital": 9264.87, "trades": 2127, "positions": 4, "exposure": 0.04, "predictions": 7450}
data\v2.jsonl:889:{"tick": 4370, "t": "13:03:51", "acc": 0.43, "entropy": 0.9877, "ret": -0.075104, "capital": 9248.96, "trades": 2130, "positions": 3, "exposure": 0.03, "predictions": 7470}
data\v2.jsonl:890:{"tick": 4375, "t": "13:08:53", "acc": 0.445, "entropy": 0.9865, "ret": -0.07508, "capital": 9249.2, "trades": 2137, "positions": 2, "exposure": 0.02, "predictions": 7490}
data\v2.jsonl:891:{"tick": 4380, "t": "13:14:16", "acc": 0.44, "entropy": 0.9863, "ret": -0.076408, "capital": 9235.92, "trades": 2142, "positions": 3, "exposure": 0.03, "predictions": 7510}
data\v2.jsonl:892:{"tick": 4385, "t": "13:19:18", "acc": 0.435, "entropy": 0.9838, "ret": -0.075556, "capital": 9244.44, "trades": 2146, "positions": 4, "exposure": 0.04, "predictions": 7530}
data\v2.jsonl:893:{"tick": 4390, "t": "13:24:20", "acc": 0.43, "entropy": 0.9862, "ret": -0.075517, "capital": 9244.83, "trades": 2152, "positions": 2, "exposure": 0.02, "predictions": 7550}
data\v2.jsonl:894:{"tick": 4395, "t": "13:29:23", "acc": 0.44, "entropy": 0.985, "ret": -0.075525, "capital": 9244.75, "trades": 2154, "positions": 3, "exposure": 0.03, "predictions": 7570}
data\v2.jsonl:895:{"tick": 4400, "t": "13:34:25", "acc": 0.425, "entropy": 0.9853, "ret": -0.079177, "capital": 9208.23, "trades": 2159, "positions": 2, "exposure": 0.02, "predictions": 7590}
data\v2.jsonl:896:{"tick": 4405, "t": "13:39:27", "acc": 0.425, "entropy": 0.9832, "ret": -0.079774, "capital": 9202.26, "trades": 2163, "positions": 1, "exposure": 0.01, "predictions": 7610}
data\v2.jsonl:897:{"tick": 4410, "t": "13:44:29", "acc": 0.45, "entropy": 0.9856, "ret": -0.079558, "capital": 9204.42, "trades": 2167, "positions": 2, "exposure": 0.02, "predictions": 7630}
data\v2.jsonl:898:{"tick": 4415, "t": "13:49:31", "acc": 0.46, "entropy": 0.9798, "ret": -0.078979, "capital": 9210.21, "trades": 2171, "positions": 3, "exposure": 0.03, "predictions": 7650}
data\v2.jsonl:899:{"tick": 4420, "t": "13:54:33", "acc": 0.47, "entropy": 0.9816, "ret": -0.07896, "capital": 9210.4, "trades": 2176, "positions": 1, "exposure": 0.01, "predictions": 7670}
data\v2.jsonl:900:{"tick": 4425, "t": "13:59:35", "acc": 0.49, "entropy": 0.9813, "ret": -0.079054, "capital": 9209.46, "trades": 2179, "positions": 1, "exposure": 0.01, "predictions": 7690}
data\v2.jsonl:901:{"tick": 4430, "t": "14:04:37", "acc": 0.495, "entropy": 0.9819, "ret": -0.079054, "capital": 9209.46, "trades": 2180, "positions": 3, "exposure": 0.03, "predictions": 7710}
data\v2.jsonl:902:{"tick": 4435, "t": "14:09:31", "acc": 0.505, "entropy": 0.9816, "ret": -0.07866, "capital": 9213.4, "trades": 2182, "positions": 3, "exposure": 0.03, "predictions": 7730}
data\v2.jsonl:903:{"tick": 4440, "t": "14:14:33", "acc": 0.515, "entropy": 0.9842, "ret": -0.078177, "capital": 9218.23, "trades": 2184, "positions": 4, "exposure": 0.04, "predictions": 7750}
data\v2.jsonl:904:{"tick": 4445, "t": "14:19:36", "acc": 0.52, "entropy": 0.9839, "ret": -0.07802, "capital": 9219.8, "trades": 2187, "positions": 2, "exposure": 0.02, "predictions": 7770}
data\v2.jsonl:905:{"tick": 4450, "t": "14:24:38", "acc": 0.555, "entropy": 0.9837, "ret": -0.078412, "capital": 9215.88, "trades": 2190, "positions": 1, "exposure": 0.01, "predictions": 7790}
data\v2.jsonl:906:{"tick": 4455, "t": "14:29:40", "acc": 0.57, "entropy": 0.984, "ret": -0.078898, "capital": 9211.02, "trades": 2194, "positions": 2, "exposure": 0.02, "predictions": 7810}
data\v2.jsonl:907:{"tick": 4460, "t": "14:34:42", "acc": 0.57, "entropy": 0.9828, "ret": -0.078601, "capital": 9213.99, "trades": 2196, "positions": 3, "exposure": 0.03, "predictions": 7830}
data\v2.jsonl:908:{"tick": 4465, "t": "14:39:44", "acc": 0.57, "entropy": 0.9878, "ret": -0.079358, "capital": 9206.42, "trades": 2201, "positions": 0, "exposure": 0, "predictions": 7850}
data\v2.jsonl:909:{"tick": 4470, "t": "14:44:46", "acc": 0.565, "entropy": 0.9879, "ret": -0.080381, "capital": 9196.19, "trades": 2205, "positions": 1, "exposure": 0.01, "predictions": 7870}
data\v2.jsonl:910:{"tick": 4475, "t": "14:49:48", "acc": 0.54, "entropy": 0.9865, "ret": -0.079891, "capital": 9201.09, "trades": 2207, "positions": 2, "exposure": 0.02, "predictions": 7890}
data\v2.jsonl:911:{"tick": 4480, "t": "14:54:51", "acc": 0.54, "entropy": 0.9853, "ret": -0.080309, "capital": 9196.91, "trades": 2209, "positions": 3, "exposure": 0.03, "predictions": 7910}
data\v2.jsonl:912:{"tick": 4485, "t": "14:59:53", "acc": 0.54, "entropy": 0.9878, "ret": -0.079653, "capital": 9203.47, "trades": 2214, "positions": 0, "exposure": 0, "predictions": 7930}
data\v2.jsonl:913:{"tick": 4490, "t": "15:04:55", "acc": 0.54, "entropy": 0.9892, "ret": -0.079653, "capital": 9203.47, "trades": 2214, "positions": 3, "exposure": 0.03, "predictions": 7950}
data\v2.jsonl:914:{"tick": 4495, "t": "15:09:57", "acc": 0.55, "entropy": 0.9857, "ret": -0.078798, "capital": 9212.02, "trades": 2217, "positions": 2, "exposure": 0.02, "predictions": 7970}
data\v2.jsonl:915:{"tick": 4500, "t": "15:14:59", "acc": 0.525, "entropy": 0.9893, "ret": -0.077558, "capital": 9224.42, "trades": 2218, "positions": 2, "exposure": 0.02, "predictions": 7990}
data\v2.jsonl:916:{"tick": 4505, "t": "15:20:02", "acc": 0.535, "entropy": 0.9883, "ret": -0.078472, "capital": 9215.28, "trades": 2222, "positions": 2, "exposure": 0.02, "predictions": 8010}
data\v2.jsonl:917:{"tick": 4510, "t": "15:25:04", "acc": 0.535, "entropy": 0.9887, "ret": -0.078923, "capital": 9210.77, "trades": 2224, "positions": 2, "exposure": 0.02, "predictions": 8030}
data\v2.jsonl:918:{"tick": 4515, "t": "15:30:06", "acc": 0.52, "entropy": 0.9885, "ret": -0.078188, "capital": 9218.12, "trades": 2229, "positions": 1, "exposure": 0.01, "predictions": 8050}
data\v2.jsonl:919:{"tick": 4520, "t": "15:35:08", "acc": 0.51, "entropy": 0.9866, "ret": -0.078461, "capital": 9215.39, "trades": 2232, "positions": 1, "exposure": 0.01, "predictions": 8070}
data\v2.jsonl:920:{"tick": 4525, "t": "15:40:10", "acc": 0.515, "entropy": 0.9857, "ret": -0.07872, "capital": 9212.8, "trades": 2236, "positions": 2, "exposure": 0.02, "predictions": 8090}
data\v2.jsonl:921:{"tick": 4530, "t": "15:45:12", "acc": 0.505, "entropy": 0.987, "ret": -0.078738, "capital": 9212.62, "trades": 2239, "positions": 1, "exposure": 0.01, "predictions": 8110}
data\v2.jsonl:922:{"tick": 4535, "t": "15:50:14", "acc": 0.505, "entropy": 0.9886, "ret": -0.078579, "capital": 9214.21, "trades": 2243, "positions": 3, "exposure": 0.03, "predictions": 8130}
data\v2.jsonl:923:{"tick": 4540, "t": "15:55:16", "acc": 0.48, "entropy": 0.9888, "ret": -0.079188, "capital": 9208.12, "trades": 2248, "positions": 1, "exposure": 0.01, "predictions": 8150}
data\v2.jsonl:924:{"tick": 4545, "t": "16:00:18", "acc": 0.46, "entropy": 0.9883, "ret": -0.079466, "capital": 9205.34, "trades": 2253, "positions": 2, "exposure": 0.02, "predictions": 8170}
data\v2.jsonl:925:{"tick": 4550, "t": "16:05:20", "acc": 0.455, "entropy": 0.9901, "ret": -0.0798, "capital": 9202.0, "trades": 2255, "positions": 3, "exposure": 0.03, "predictions": 8190}
data\v2.jsonl:926:{"tick": 4555, "t": "16:10:22", "acc": 0.445, "entropy": 0.9854, "ret": -0.079626, "capital": 9203.74, "trades": 2257, "positions": 2, "exposure": 0.02, "predictions": 8210}
data\v2.jsonl:927:{"tick": 4560, "t": "16:15:24", "acc": 0.46, "entropy": 0.9889, "ret": -0.07927, "capital": 9207.3, "trades": 2259, "positions": 4, "exposure": 0.04, "predictions": 8230}
data\v2.jsonl:928:{"tick": 4565, "t": "16:20:27", "acc": 0.465, "entropy": 0.9894, "ret": -0.07922, "capital": 9207.8, "trades": 2262, "positions": 2, "exposure": 0.02, "predictions": 8250}
data\v2.jsonl:929:{"tick": 4570, "t": "16:25:29", "acc": 0.485, "entropy": 0.9904, "ret": -0.079705, "capital": 9202.95, "trades": 2266, "positions": 3, "exposure": 0.03, "predictions": 8270}
data\v2.jsonl:930:{"tick": 4575, "t": "16:30:31", "acc": 0.475, "entropy": 0.9909, "ret": -0.079981, "capital": 9200.19, "trades": 2270, "positions": 2, "exposure": 0.02, "predictions": 8290}
data\v2.jsonl:931:{"tick": 4580, "t": "16:35:33", "acc": 0.49, "entropy": 0.9909, "ret": -0.081621, "capital": 9183.79, "trades": 2274, "positions": 2, "exposure": 0.02, "predictions": 8310}
data\v2.jsonl:932:{"tick": 4585, "t": "16:40:35", "acc": 0.505, "entropy": 0.991, "ret": -0.08262, "capital": 9173.8, "trades": 2276, "positions": 1, "exposure": 0.01, "predictions": 8330}
data\v2.jsonl:933:{"tick": 4590, "t": "16:45:37", "acc": 0.515, "entropy": 0.9914, "ret": -0.082554, "capital": 9174.46, "trades": 2278, "positions": 3, "exposure": 0.03, "predictions": 8350}
data\v2.jsonl:934:{"tick": 4595, "t": "16:50:39", "acc": 0.51, "entropy": 0.9886, "ret": -0.082776, "capital": 9172.24, "trades": 2280, "positions": 2, "exposure": 0.02, "predictions": 8370}
data\v2.jsonl:935:{"tick": 4600, "t": "16:55:41", "acc": 0.5, "entropy": 0.9912, "ret": -0.08486, "capital": 9151.4, "trades": 2283, "positions": 2, "exposure": 0.02, "predictions": 8390}
data\v2.jsonl:936:{"tick": 4605, "t": "17:00:43", "acc": 0.48, "entropy": 0.9893, "ret": -0.084332, "capital": 9156.68, "trades": 2286, "positions": 1, "exposure": 0.01, "predictions": 8410}
data\v2.jsonl:937:{"tick": 4610, "t": "17:05:46", "acc": 0.465, "entropy": 0.9904, "ret": -0.084344, "capital": 9156.56, "trades": 2289, "positions": 2, "exposure": 0.02, "predictions": 8430}
data\v2.jsonl:938:{"tick": 4615, "t": "17:10:48", "acc": 0.475, "entropy": 0.9905, "ret": -0.08461, "capital": 9153.9, "trades": 2294, "positions": 3, "exposure": 0.03, "predictions": 8450}
data\v2.jsonl:939:{"tick": 4620, "t": "17:15:50", "acc": 0.475, "entropy": 0.9913, "ret": -0.082943, "capital": 9170.57, "trades": 2302, "positions": 0, "exposure": 0, "predictions": 8470}
data\v2.jsonl:940:{"tick": 4625, "t": "17:20:52", "acc": 0.48, "entropy": 0.9878, "ret": -0.083551, "capital": 9164.49, "trades": 2304, "positions": 2, "exposure": 0.02, "predictions": 8490}
data\v2.jsonl:941:{"tick": 4630, "t": "17:25:54", "acc": 0.475, "entropy": 0.9902, "ret": -0.085867, "capital": 9141.33, "trades": 2308, "positions": 2, "exposure": 0.02, "predictions": 8510}
data\v2.jsonl:942:{"tick": 4635, "t": "17:30:56", "acc": 0.47, "entropy": 0.9895, "ret": -0.085962, "capital": 9140.38, "trades": 2314, "positions": 3, "exposure": 0.03, "predictions": 8530}
data\v2.jsonl:943:{"tick": 4640, "t": "17:35:58", "acc": 0.48, "entropy": 0.9858, "ret": -0.085377, "capital": 9146.23, "trades": 2316, "positions": 2, "exposure": 0.02, "predictions": 8550}
data\v2.jsonl:944:{"tick": 4645, "t": "17:41:00", "acc": 0.495, "entropy": 0.9868, "ret": -0.086762, "capital": 9132.38, "trades": 2319, "positions": 3, "exposure": 0.03, "predictions": 8570}
data\v2.jsonl:945:{"tick": 4650, "t": "17:46:02", "acc": 0.515, "entropy": 0.9887, "ret": -0.086991, "capital": 9130.09, "trades": 2320, "positions": 3, "exposure": 0.03, "predictions": 8590}
data\v2.jsonl:946:{"tick": 4655, "t": "17:51:04", "acc": 0.53, "entropy": 0.99, "ret": -0.085748, "capital": 9142.52, "trades": 2324, "positions": 1, "exposure": 0.01, "predictions": 8610}
data\v2.jsonl:947:{"tick": 4660, "t": "17:56:06", "acc": 0.525, "entropy": 0.9883, "ret": -0.085631, "capital": 9143.69, "trades": 2325, "positions": 3, "exposure": 0.03, "predictions": 8630}
data\v2.jsonl:948:{"tick": 4665, "t": "18:01:09", "acc": 0.535, "entropy": 0.9862, "ret": -0.085713, "capital": 9142.87, "trades": 2327, "positions": 3, "exposure": 0.03, "predictions": 8649}
data\v2.jsonl:949:{"tick": 4670, "t": "18:06:11", "acc": 0.525, "entropy": 0.9865, "ret": -0.085936, "capital": 9140.64, "trades": 2334, "positions": 0, "exposure": 0, "predictions": 8669}
data\v2.jsonl:950:{"tick": 4675, "t": "18:11:13", "acc": 0.54, "entropy": 0.9892, "ret": -0.084828, "capital": 9151.72, "trades": 2335, "positions": 2, "exposure": 0.02, "predictions": 8689}
data\v2.jsonl:951:{"tick": 4680, "t": "18:16:15", "acc": 0.535, "entropy": 0.9884, "ret": -0.087419, "capital": 9125.81, "trades": 2339, "positions": 1, "exposure": 0.01, "predictions": 8709}
data\v2.jsonl:952:{"tick": 4685, "t": "18:21:17", "acc": 0.54, "entropy": 0.9921, "ret": -0.087616, "capital": 9123.84, "trades": 2340, "positions": 1, "exposure": 0.01, "predictions": 8729}
data\v2.jsonl:953:{"tick": 4690, "t": "18:26:19", "acc": 0.525, "entropy": 0.9918, "ret": -0.087295, "capital": 9127.05, "trades": 2343, "positions": 3, "exposure": 0.03, "predictions": 8749}
data\v2.jsonl:954:{"tick": 4695, "t": "18:31:21", "acc": 0.525, "entropy": 0.9911, "ret": -0.087739, "capital": 9122.61, "trades": 2348, "positions": 2, "exposure": 0.02, "predictions": 8769}
data\v2.jsonl:955:{"tick": 4700, "t": "18:36:23", "acc": 0.525, "entropy": 0.9919, "ret": -0.087789, "capital": 9122.11, "trades": 2353, "positions": 1, "exposure": 0.01, "predictions": 8789}
data\v2.jsonl:956:{"tick": 4705, "t": "18:41:25", "acc": 0.555, "entropy": 0.9911, "ret": -0.087748, "capital": 9122.52, "trades": 2355, "positions": 2, "exposure": 0.02, "predictions": 8809}
data\v2.jsonl:957:{"tick": 4710, "t": "18:46:27", "acc": 0.55, "entropy": 0.9891, "ret": -0.087797, "capital": 9122.03, "trades": 2357, "positions": 2, "exposure": 0.02, "predictions": 8829}
data\v2.jsonl:958:{"tick": 4715, "t": "18:51:30", "acc": 0.525, "entropy": 0.9882, "ret": -0.08806, "capital": 9119.4, "trades": 2360, "positions": 3, "exposure": 0.03, "predictions": 8849}
data\v2.jsonl:959:{"tick": 4720, "t": "18:56:32", "acc": 0.535, "entropy": 0.9889, "ret": -0.089126, "capital": 9108.74, "trades": 2364, "positions": 2, "exposure": 0.02, "predictions": 8869}
data\v2.jsonl:960:{"tick": 4725, "t": "19:01:34", "acc": 0.53, "entropy": 0.99, "ret": -0.089648, "capital": 9103.52, "trades": 2366, "positions": 3, "exposure": 0.03, "predictions": 8889}
data\v2.jsonl:961:{"tick": 4730, "t": "19:06:36", "acc": 0.57, "entropy": 0.9906, "ret": -0.088716, "capital": 9112.84, "trades": 2369, "positions": 3, "exposure": 0.03, "predictions": 8909}
data\v2.jsonl:962:{"tick": 4735, "t": "19:11:38", "acc": 0.565, "entropy": 0.9872, "ret": -0.088657, "capital": 9113.43, "trades": 2371, "positions": 2, "exposure": 0.02, "predictions": 8929}
data\v2.jsonl:963:{"tick": 4740, "t": "19:16:40", "acc": 0.565, "entropy": 0.9889, "ret": -0.089707, "capital": 9102.93, "trades": 2373, "positions": 1, "exposure": 0.01, "predictions": 8949}
data\v2.jsonl:964:{"tick": 4745, "t": "19:21:42", "acc": 0.55, "entropy": 0.9905, "ret": -0.089657, "capital": 9103.43, "trades": 2374, "positions": 2, "exposure": 0.02, "predictions": 8969}
data\v2.jsonl:965:{"tick": 4750, "t": "19:26:44", "acc": 0.535, "entropy": 0.9888, "ret": -0.091379, "capital": 9086.21, "trades": 2380, "positions": 0, "exposure": 0, "predictions": 8989}
data\v2.jsonl:966:{"tick": 4755, "t": "19:31:46", "acc": 0.495, "entropy": 0.9882, "ret": -0.091686, "capital": 9083.14, "trades": 2382, "positions": 1, "exposure": 0.01, "predictions": 9009}
data\v2.jsonl:967:{"tick": 4760, "t": "19:36:48", "acc": 0.5, "entropy": 0.986, "ret": -0.091835, "capital": 9081.65, "trades": 2383, "positions": 4, "exposure": 0.04, "predictions": 9029}
data\v2.jsonl:968:{"tick": 4765, "t": "19:41:50", "acc": 0.51, "entropy": 0.9879, "ret": -0.092086, "capital": 9079.14, "trades": 2388, "positions": 1, "exposure": 0.01, "predictions": 9049}
data\v2.jsonl:969:{"tick": 4770, "t": "19:46:52", "acc": 0.52, "entropy": 0.99, "ret": -0.091751, "capital": 9082.49, "trades": 2390, "positions": 3, "exposure": 0.03, "predictions": 9069}
data\v2.jsonl:970:{"tick": 4775, "t": "19:51:55", "acc": 0.515, "entropy": 0.9869, "ret": -0.091969, "capital": 9080.31, "trades": 2396, "positions": 2, "exposure": 0.02, "predictions": 9089}
data\v2.jsonl:971:{"tick": 4780, "t": "19:56:57", "acc": 0.485, "entropy": 0.9865, "ret": -0.092024, "capital": 9079.76, "trades": 2399, "positions": 2, "exposure": 0.02, "predictions": 9109}
data\v2.jsonl:972:{"tick": 4785, "t": "20:01:59", "acc": 0.49, "entropy": 0.9873, "ret": -0.092222, "capital": 9077.78, "trades": 2403, "positions": 2, "exposure": 0.02, "predictions": 9129}
data\v2.jsonl:973:{"tick": 4790, "t": "20:07:01", "acc": 0.485, "entropy": 0.9872, "ret": -0.092332, "capital": 9076.68, "trades": 2405, "positions": 3, "exposure": 0.03, "predictions": 9149}
data\v2.jsonl:974:{"tick": 4795, "t": "20:12:03", "acc": 0.49, "entropy": 0.9856, "ret": -0.093711, "capital": 9062.89, "trades": 2409, "positions": 2, "exposure": 0.02, "predictions": 9169}
data\v2.jsonl:975:{"tick": 4800, "t": "20:17:05", "acc": 0.5, "entropy": 0.9815, "ret": -0.094043, "capital": 9059.57, "trades": 2411, "positions": 2, "exposure": 0.02, "predictions": 9189}
data\v2.jsonl:976:{"tick": 4805, "t": "20:22:07", "acc": 0.51, "entropy": 0.9806, "ret": -0.093208, "capital": 9067.92, "trades": 2416, "positions": 1, "exposure": 0.01, "predictions": 9209}
data\v2.jsonl:977:{"tick": 4810, "t": "20:27:09", "acc": 0.525, "entropy": 0.9842, "ret": -0.093138, "capital": 9068.62, "trades": 2419, "positions": 0, "exposure": 0, "predictions": 9229}
data\v2.jsonl:978:{"tick": 4815, "t": "20:32:11", "acc": 0.525, "entropy": 0.9863, "ret": -0.092928, "capital": 9070.72, "trades": 2422, "positions": 2, "exposure": 0.02, "predictions": 9249}
data\v2.jsonl:979:{"tick": 4820, "t": "20:37:13", "acc": 0.525, "entropy": 0.986, "ret": -0.092966, "capital": 9070.34, "trades": 2426, "positions": 1, "exposure": 0.01, "predictions": 9269}
data\v2.jsonl:980:{"tick": 4825, "t": "20:42:15", "acc": 0.51, "entropy": 0.9861, "ret": -0.093141, "capital": 9068.59, "trades": 2428, "positions": 2, "exposure": 0.02, "predictions": 9289}
data\v2.jsonl:981:{"tick": 4830, "t": "20:47:17", "acc": 0.515, "entropy": 0.988, "ret": -0.093141, "capital": 9068.59, "trades": 2430, "positions": 1, "exposure": 0.01, "predictions": 9309}
data\v2.jsonl:982:{"tick": 4835, "t": "20:52:20", "acc": 0.515, "entropy": 0.9868, "ret": -0.092926, "capital": 9070.74, "trades": 2433, "positions": 2, "exposure": 0.02, "predictions": 9329}
data\v2.jsonl:983:{"tick": 4840, "t": "20:57:22", "acc": 0.515, "entropy": 0.9831, "ret": -0.092774, "capital": 9072.26, "trades": 2436, "positions": 2, "exposure": 0.02, "predictions": 9349}
data\v2.jsonl:984:{"tick": 4845, "t": "21:02:24", "acc": 0.535, "entropy": 0.9801, "ret": -0.092772, "capital": 9072.28, "trades": 2437, "positions": 4, "exposure": 0.04, "predictions": 9369}
data\v2.jsonl:985:{"tick": 4850, "t": "21:07:26", "acc": 0.56, "entropy": 0.9858, "ret": -0.09245, "capital": 9075.5, "trades": 2442, "positions": 3, "exposure": 0.03, "predictions": 9389}
data\v2.jsonl:986:{"tick": 4855, "t": "21:12:28", "acc": 0.55, "entropy": 0.9817, "ret": -0.092749, "capital": 9072.51, "trades": 2445, "positions": 1, "exposure": 0.01, "predictions": 9409}
data\v2.jsonl:987:{"tick": 4860, "t": "21:17:30", "acc": 0.545, "entropy": 0.9843, "ret": -0.092095, "capital": 9079.05, "trades": 2447, "positions": 3, "exposure": 0.03, "predictions": 9429}
data\v2.jsonl:988:{"tick": 4865, "t": "21:22:32", "acc": 0.55, "entropy": 0.9812, "ret": -0.092319, "capital": 9076.81, "trades": 2450, "positions": 1, "exposure": 0.01, "predictions": 9449}
data\v2.jsonl:989:{"tick": 4870, "t": "21:27:34", "acc": 0.51, "entropy": 0.9825, "ret": -0.092273, "capital": 9077.27, "trades": 2451, "positions": 2, "exposure": 0.02, "predictions": 9469}
data\v2.jsonl:990:{"tick": 4875, "t": "21:32:36", "acc": 0.525, "entropy": 0.9827, "ret": -0.092589, "capital": 9074.11, "trades": 2456, "positions": 0, "exposure": 0, "predictions": 9489}
data\v2.jsonl:991:{"tick": 4880, "t": "21:37:38", "acc": 0.52, "entropy": 0.9859, "ret": -0.092669, "capital": 9073.31, "trades": 2458, "positions": 2, "exposure": 0.02, "predictions": 9509}
data\v2.jsonl:992:{"tick": 4885, "t": "21:42:40", "acc": 0.52, "entropy": 0.984, "ret": -0.092127, "capital": 9078.73, "trades": 2462, "positions": 2, "exposure": 0.02, "predictions": 9529}
data\v2.jsonl:993:{"tick": 4890, "t": "21:47:42", "acc": 0.52, "entropy": 0.981, "ret": -0.09279, "capital": 9072.1, "trades": 2465, "positions": 1, "exposure": 0.01, "predictions": 9549}
data\v2.jsonl:994:{"tick": 4895, "t": "21:52:44", "acc": 0.51, "entropy": 0.9821, "ret": -0.092865, "capital": 9071.35, "trades": 2466, "positions": 2, "exposure": 0.02, "predictions": 9569}
data\v2.jsonl:995:{"tick": 4900, "t": "21:57:46", "acc": 0.48, "entropy": 0.9789, "ret": -0.092458, "capital": 9075.42, "trades": 2469, "positions": 0, "exposure": 0, "predictions": 9589}
data\v2.jsonl:996:{"tick": 4905, "t": "22:02:48", "acc": 0.49, "entropy": 0.978, "ret": -0.092648, "capital": 9073.52, "trades": 2472, "positions": 2, "exposure": 0.02, "predictions": 9609}
data\v2.jsonl:997:{"tick": 4910, "t": "22:07:51", "acc": 0.465, "entropy": 0.9807, "ret": -0.093159, "capital": 9068.41, "trades": 2476, "positions": 0, "exposure": 0, "predictions": 9629}
data\v2.jsonl:998:{"tick": 4915, "t": "22:12:52", "acc": 0.47, "entropy": 0.9811, "ret": -0.093594, "capital": 9064.06, "trades": 2477, "positions": 4, "exposure": 0.04, "predictions": 9649}
data\v2.jsonl:999:{"tick": 4920, "t": "22:17:55", "acc": 0.49, "entropy": 0.983, "ret": -0.093472, "capital": 9065.28, "trades": 2481, "positions": 3, "exposure": 0.03, "predictions": 9669}
data\v2.jsonl:1000:{"tick": 4925, "t": "22:22:57", "acc": 0.485, "entropy": 0.9832, "ret": -0.093251, "capital": 9067.49, "trades": 2485, "positions": 1, "exposure": 0.01, "predictions": 9689}
data\v2.jsonl:1001:{"tick": 4930, "t": "22:27:59", "acc": 0.48, "entropy": 0.9823, "ret": -0.093385, "capital": 9066.15, "trades": 2489, "positions": 1, "exposure": 0.01, "predictions": 9709}
data\v2.jsonl:1002:{"tick": 4935, "t": "22:33:01", "acc": 0.475, "entropy": 0.9854, "ret": -0.092889, "capital": 9071.11, "trades": 2493, "positions": 3, "exposure": 0.03, "predictions": 9729}
data\v2.jsonl:1003:{"tick": 4940, "t": "22:38:03", "acc": 0.48, "entropy": 0.9835, "ret": -0.092805, "capital": 9071.95, "trades": 2497, "positions": 3, "exposure": 0.03, "predictions": 9749}
data\v2.jsonl:1004:{"tick": 4945, "t": "22:43:06", "acc": 0.47, "entropy": 0.9827, "ret": -0.093185, "capital": 9068.15, "trades": 2503, "positions": 0, "exposure": 0, "predictions": 9769}
data\v2.jsonl:1005:{"tick": 4950, "t": "22:48:08", "acc": 0.47, "entropy": 0.9847, "ret": -0.093597, "capital": 9064.03, "trades": 2508, "positions": 1, "exposure": 0.01, "predictions": 9789}
data\v2.jsonl:1006:{"tick": 4955, "t": "22:53:10", "acc": 0.455, "entropy": 0.9846, "ret": -0.093605, "capital": 9063.95, "trades": 2509, "positions": 1, "exposure": 0.01, "predictions": 9809}
data\v2.jsonl:1007:{"tick": 4960, "t": "22:58:12", "acc": 0.51, "entropy": 0.9875, "ret": -0.093357, "capital": 9066.43, "trades": 2512, "positions": 3, "exposure": 0.03, "predictions": 9829}
data\v2.jsonl:1008:{"tick": 4965, "t": "23:03:14", "acc": 0.51, "entropy": 0.9876, "ret": -0.092697, "capital": 9073.03, "trades": 2517, "positions": 2, "exposure": 0.02, "predictions": 9849}
data\v2.jsonl:1009:{"tick": 4970, "t": "23:08:16", "acc": 0.515, "entropy": 0.9892, "ret": -0.092586, "capital": 9074.14, "trades": 2519, "positions": 1, "exposure": 0.01, "predictions": 9869}
data\v2.jsonl:1010:{"tick": 4975, "t": "23:13:18", "acc": 0.53, "entropy": 0.9878, "ret": -0.092454, "capital": 9075.46, "trades": 2521, "positions": 2, "exposure": 0.02, "predictions": 9889}
data\v2.jsonl:1011:{"tick": 4980, "t": "23:18:20", "acc": 0.54, "entropy": 0.9885, "ret": -0.091656, "capital": 9083.44, "trades": 2526, "positions": 1, "exposure": 0.01, "predictions": 9909}
data\v2.jsonl:1012:{"tick": 4985, "t": "23:23:23", "acc": 0.535, "entropy": 0.988, "ret": -0.092446, "capital": 9075.54, "trades": 2530, "positions": 2, "exposure": 0.02, "predictions": 9929}
data\v2.jsonl:1013:{"tick": 4990, "t": "23:28:25", "acc": 0.555, "entropy": 0.9888, "ret": -0.092185, "capital": 9078.15, "trades": 2534, "positions": 2, "exposure": 0.02, "predictions": 9949}
data\v2.jsonl:1014:{"tick": 4995, "t": "23:33:27", "acc": 0.55, "entropy": 0.988, "ret": -0.09204, "capital": 9079.6, "trades": 2535, "positions": 4, "exposure": 0.04, "predictions": 9969}
data\v2.jsonl:1015:{"tick": 5000, "t": "23:38:29", "acc": 0.56, "entropy": 0.9892, "ret": -0.092057, "capital": 9079.43, "trades": 2537, "positions": 4, "exposure": 0.04, "predictions": 9989}
data\v2.jsonl:1016:{"tick": 5005, "t": "23:43:31", "acc": 0.565, "entropy": 0.9878, "ret": -0.091998, "capital": 9080.02, "trades": 2540, "positions": 2, "exposure": 0.02, "predictions": 10009}
data\v2.jsonl:1017:{"tick": 5010, "t": "23:48:34", "acc": 0.53, "entropy": 0.9877, "ret": -0.092243, "capital": 9077.57, "trades": 2543, "positions": 3, "exposure": 0.03, "predictions": 10029}
data\v2.jsonl:1018:{"tick": 5015, "t": "23:53:36", "acc": 0.545, "entropy": 0.9871, "ret": -0.091777, "capital": 9082.23, "trades": 2548, "positions": 1, "exposure": 0.01, "predictions": 10049}
data\v2.jsonl:1019:{"tick": 5020, "t": "23:58:38", "acc": 0.555, "entropy": 0.9885, "ret": -0.092131, "capital": 9078.69, "trades": 2552, "positions": 1, "exposure": 0.01, "predictions": 10069}
data\v2.jsonl:1020:{"tick": 5025, "t": "00:03:40", "acc": 0.545, "entropy": 0.9881, "ret": -0.091821, "capital": 9081.79, "trades": 2554, "positions": 1, "exposure": 0.01, "predictions": 10089}
data\v2.jsonl:1021:{"tick": 5030, "t": "00:08:42", "acc": 0.535, "entropy": 0.9837, "ret": -0.092166, "capital": 9078.34, "trades": 2557, "positions": 1, "exposure": 0.01, "predictions": 10109}
data\v2.jsonl:1022:{"tick": 5035, "t": "00:13:44", "acc": 0.525, "entropy": 0.9857, "ret": -0.092934, "capital": 9070.66, "trades": 2560, "positions": 1, "exposure": 0.01, "predictions": 10129}
data\v2.jsonl:1023:{"tick": 5040, "t": "00:18:46", "acc": 0.505, "entropy": 0.9866, "ret": -0.093215, "capital": 9067.85, "trades": 2562, "positions": 2, "exposure": 0.02, "predictions": 10149}
data\v2.jsonl:1024:{"tick": 5045, "t": "00:23:49", "acc": 0.505, "entropy": 0.9819, "ret": -0.092996, "capital": 9070.04, "trades": 2565, "positions": 3, "exposure": 0.03, "predictions": 10169}
data\v2.jsonl:1025:{"tick": 5050, "t": "00:28:51", "acc": 0.5, "entropy": 0.9791, "ret": -0.09408, "capital": 9059.2, "trades": 2570, "positions": 1, "exposure": 0.01, "predictions": 10189}
data\v2.jsonl:1026:{"tick": 5055, "t": "00:33:53", "acc": 0.5, "entropy": 0.9838, "ret": -0.094056, "capital": 9059.44, "trades": 2572, "positions": 1, "exposure": 0.01, "predictions": 10209}
data\v2.jsonl:1027:{"tick": 5060, "t": "00:38:55", "acc": 0.49, "entropy": 0.9808, "ret": -0.094525, "capital": 9054.75, "trades": 2575, "positions": 2, "exposure": 0.02, "predictions": 10229}
data\v2.jsonl:1028:{"tick": 5065, "t": "00:43:57", "acc": 0.465, "entropy": 0.9833, "ret": -0.094367, "capital": 9056.33, "trades": 2578, "positions": 2, "exposure": 0.02, "predictions": 10249}
data\v2.jsonl:1029:{"tick": 5070, "t": "00:48:59", "acc": 0.44, "entropy": 0.981, "ret": -0.094675, "capital": 9053.25, "trades": 2582, "positions": 0, "exposure": 0, "predictions": 10269}
data\v2.jsonl:1030:{"tick": 5075, "t": "00:54:01", "acc": 0.45, "entropy": 0.9861, "ret": -0.094716, "capital": 9052.84, "trades": 2586, "positions": 0, "exposure": 0, "predictions": 10289}
data\v2.jsonl:1031:{"tick": 5080, "t": "00:59:03", "acc": 0.46, "entropy": 0.9864, "ret": -0.094511, "capital": 9054.89, "trades": 2589, "positions": 3, "exposure": 0.03, "predictions": 10309}
data\v2.jsonl:1032:{"tick": 5085, "t": "01:04:05", "acc": 0.475, "entropy": 0.9871, "ret": -0.094511, "capital": 9054.89, "trades": 2593, "positions": 1, "exposure": 0.01, "predictions": 10329}
data\v2.jsonl:1033:{"tick": 5090, "t": "01:09:08", "acc": 0.495, "entropy": 0.9898, "ret": -0.094444, "capital": 9055.56, "trades": 2596, "positions": 1, "exposure": 0.01, "predictions": 10349}
data\v2.jsonl:1034:{"tick": 5095, "t": "01:14:10", "acc": 0.53, "entropy": 0.99, "ret": -0.094991, "capital": 9050.09, "trades": 2599, "positions": 1, "exposure": 0.01, "predictions": 10369}
data\v2.jsonl:1035:{"tick": 5100, "t": "01:19:12", "acc": 0.535, "entropy": 0.988, "ret": -0.094942, "capital": 9050.58, "trades": 2603, "positions": 1, "exposure": 0.01, "predictions": 10389}
data\v2.jsonl:1036:{"tick": 5105, "t": "01:24:14", "acc": 0.525, "entropy": 0.9886, "ret": -0.095136, "capital": 9048.64, "trades": 2604, "positions": 2, "exposure": 0.02, "predictions": 10409}
data\v2.jsonl:1037:{"tick": 5110, "t": "01:29:17", "acc": 0.545, "entropy": 0.9877, "ret": -0.09513, "capital": 9048.7, "trades": 2608, "positions": 1, "exposure": 0.01, "predictions": 10429}
data\v2.jsonl:1038:{"tick": 5115, "t": "01:34:19", "acc": 0.55, "entropy": 0.9884, "ret": -0.095572, "capital": 9044.28, "trades": 2611, "positions": 3, "exposure": 0.03, "predictions": 10449}
data\v2.jsonl:1039:{"tick": 5120, "t": "01:39:21", "acc": 0.56, "entropy": 0.988, "ret": -0.095841, "capital": 9041.59, "trades": 2613, "positions": 4, "exposure": 0.04, "predictions": 10469}
data\v2.jsonl:1040:{"tick": 5125, "t": "01:44:23", "acc": 0.535, "entropy": 0.9849, "ret": -0.096249, "capital": 9037.51, "trades": 2616, "positions": 2, "exposure": 0.02, "predictions": 10489}
data\v2.jsonl:1041:{"tick": 5130, "t": "01:49:25", "acc": 0.53, "entropy": 0.9843, "ret": -0.096309, "capital": 9036.91, "trades": 2618, "positions": 3, "exposure": 0.03, "predictions": 10509}
data\v2.jsonl:1042:{"tick": 5135, "t": "01:54:27", "acc": 0.52, "entropy": 0.9857, "ret": -0.096188, "capital": 9038.12, "trades": 2622, "positions": 0, "exposure": 0, "predictions": 10529}
data\v2.jsonl:1043:{"tick": 5140, "t": "01:59:29", "acc": 0.515, "entropy": 0.9861, "ret": -0.09638, "capital": 9036.2, "trades": 2623, "positions": 3, "exposure": 0.03, "predictions": 10549}
data\v2.jsonl:1044:{"tick": 5145, "t": "02:04:31", "acc": 0.51, "entropy": 0.9846, "ret": -0.096851, "capital": 9031.49, "trades": 2628, "positions": 2, "exposure": 0.02, "predictions": 10569}
data\v2.jsonl:1045:{"tick": 5150, "t": "02:09:33", "acc": 0.505, "entropy": 0.9858, "ret": -0.096668, "capital": 9033.32, "trades": 2631, "positions": 3, "exposure": 0.03, "predictions": 10589}
data\v2.jsonl:1046:{"tick": 5155, "t": "02:14:35", "acc": 0.51, "entropy": 0.984, "ret": -0.096221, "capital": 9037.79, "trades": 2635, "positions": 3, "exposure": 0.03, "predictions": 10609}
data\v2.jsonl:1047:{"tick": 5160, "t": "02:19:38", "acc": 0.5, "entropy": 0.9858, "ret": -0.095321, "capital": 9046.79, "trades": 2638, "positions": 2, "exposure": 0.02, "predictions": 10629}
data\v2.jsonl:1048:{"tick": 5165, "t": "02:24:40", "acc": 0.475, "entropy": 0.9852, "ret": -0.095647, "capital": 9043.53, "trades": 2641, "positions": 4, "exposure": 0.04, "predictions": 10649}
data\v2.jsonl:1049:{"tick": 5170, "t": "02:29:42", "acc": 0.47, "entropy": 0.9886, "ret": -0.096186, "capital": 9038.14, "trades": 2646, "positions": 2, "exposure": 0.02, "predictions": 10669}
data\v2.jsonl:1050:{"tick": 5175, "t": "02:34:44", "acc": 0.47, "entropy": 0.9875, "ret": -0.096245, "capital": 9037.55, "trades": 2650, "positions": 2, "exposure": 0.02, "predictions": 10689}
data\v2.jsonl:1051:{"tick": 5180, "t": "02:39:52", "acc": 0.48, "entropy": 0.9857, "ret": -0.095547, "capital": 9044.53, "trades": 2652, "positions": 3, "exposure": 0.03, "predictions": 10709}
data\v2.jsonl:1052:{"tick": 5185, "t": "02:45:04", "acc": 0.485, "entropy": 0.9868, "ret": -0.095605, "capital": 9043.95, "trades": 2656, "positions": 3, "exposure": 0.03, "predictions": 10725}
data\v2.jsonl:1053:{"tick": 5190, "t": "02:50:07", "acc": 0.455, "entropy": 0.9872, "ret": -0.095684, "capital": 9043.16, "trades": 2659, "positions": 3, "exposure": 0.03, "predictions": 10745}
data\v2.jsonl:1054:{"tick": 5195, "t": "02:55:09", "acc": 0.435, "entropy": 0.9891, "ret": -0.096042, "capital": 9039.58, "trades": 2664, "positions": 3, "exposure": 0.03, "predictions": 10765}
data\v2.jsonl:1055:{"tick": 5200, "t": "03:00:11", "acc": 0.435, "entropy": 0.9868, "ret": -0.096164, "capital": 9038.36, "trades": 2668, "positions": 2, "exposure": 0.02, "predictions": 10783}
data\v2.jsonl:1056:{"tick": 5205, "t": "03:05:13", "acc": 0.42, "entropy": 0.9851, "ret": -0.096424, "capital": 9035.76, "trades": 2670, "positions": 3, "exposure": 0.03, "predictions": 10803}
data\v2.jsonl:1057:{"tick": 5210, "t": "03:10:15", "acc": 0.44, "entropy": 0.9842, "ret": -0.096207, "capital": 9037.93, "trades": 2671, "positions": 3, "exposure": 0.03, "predictions": 10823}
data\v2.jsonl:1058:{"tick": 5215, "t": "03:15:17", "acc": 0.445, "entropy": 0.9861, "ret": -0.096186, "capital": 9038.14, "trades": 2674, "positions": 3, "exposure": 0.03, "predictions": 10843}
data\v2.jsonl:1059:{"tick": 5220, "t": "03:20:37", "acc": 0.445, "entropy": 0.9824, "ret": -0.09633, "capital": 9036.7, "trades": 2678, "positions": 2, "exposure": 0.02, "predictions": 10863}
data\v2.jsonl:1060:{"tick": 5225, "t": "03:25:40", "acc": 0.465, "entropy": 0.9799, "ret": -0.096254, "capital": 9037.46, "trades": 2679, "positions": 3, "exposure": 0.03, "predictions": 10883}
data\v2.jsonl:1061:{"tick": 5230, "t": "03:30:42", "acc": 0.465, "entropy": 0.9788, "ret": -0.096328, "capital": 9036.72, "trades": 2681, "positions": 4, "exposure": 0.04, "predictions": 10903}
data\v2.jsonl:1062:{"tick": 5235, "t": "03:35:44", "acc": 0.465, "entropy": 0.978, "ret": -0.096073, "capital": 9039.27, "trades": 2685, "positions": 3, "exposure": 0.03, "predictions": 10923}
data\v2.jsonl:1063:{"tick": 5240, "t": "03:40:46", "acc": 0.49, "entropy": 0.9806, "ret": -0.095716, "capital": 9042.84, "trades": 2687, "positions": 3, "exposure": 0.03, "predictions": 10943}
data\v2.jsonl:1064:{"tick": 5245, "t": "03:45:48", "acc": 0.515, "entropy": 0.9821, "ret": -0.095761, "capital": 9042.39, "trades": 2690, "positions": 2, "exposure": 0.02, "predictions": 10963}
data\v2.jsonl:1065:{"tick": 5250, "t": "03:50:50", "acc": 0.525, "entropy": 0.9813, "ret": -0.095768, "capital": 9042.32, "trades": 2692, "positions": 3, "exposure": 0.03, "predictions": 10983}
data\v2.jsonl:1066:{"tick": 5255, "t": "03:55:52", "acc": 0.535, "entropy": 0.9824, "ret": -0.095136, "capital": 9048.64, "trades": 2695, "positions": 2, "exposure": 0.02, "predictions": 11003}
data\v2.jsonl:1067:{"tick": 5260, "t": "04:00:54", "acc": 0.53, "entropy": 0.9834, "ret": -0.094811, "capital": 9051.89, "trades": 2701, "positions": 2, "exposure": 0.02, "predictions": 11023}
data\v2.jsonl:1068:{"tick": 5265, "t": "04:05:56", "acc": 0.53, "entropy": 0.9803, "ret": -0.094944, "capital": 9050.56, "trades": 2707, "positions": 2, "exposure": 0.02, "predictions": 11043}
data\v2.jsonl:1069:{"tick": 5270, "t": "04:10:58", "acc": 0.55, "entropy": 0.9785, "ret": -0.094847, "capital": 9051.53, "trades": 2711, "positions": 2, "exposure": 0.02, "predictions": 11063}
data\v2.jsonl:1070:{"tick": 5275, "t": "04:16:00", "acc": 0.53, "entropy": 0.9821, "ret": -0.095057, "capital": 9049.43, "trades": 2713, "positions": 3, "exposure": 0.03, "predictions": 11083}
data\v2.jsonl:1071:{"tick": 5280, "t": "04:21:03", "acc": 0.525, "entropy": 0.9809, "ret": -0.09518, "capital": 9048.2, "trades": 2717, "positions": 2, "exposure": 0.02, "predictions": 11103}
data\v2.jsonl:1072:{"tick": 5285, "t": "04:26:05", "acc": 0.515, "entropy": 0.978, "ret": -0.094993, "capital": 9050.07, "trades": 2720, "positions": 1, "exposure": 0.01, "predictions": 11123}
data\v2.jsonl:1073:{"tick": 5290, "t": "04:31:08", "acc": 0.51, "entropy": 0.981, "ret": -0.09548, "capital": 9045.2, "trades": 2723, "positions": 2, "exposure": 0.02, "predictions": 11143}
data\v2.jsonl:1074:{"tick": 5295, "t": "04:36:10", "acc": 0.51, "entropy": 0.9794, "ret": -0.095247, "capital": 9047.53, "trades": 2725, "positions": 3, "exposure": 0.03, "predictions": 11163}
data\v2.jsonl:1075:{"tick": 5300, "t": "04:41:12", "acc": 0.52, "entropy": 0.9808, "ret": -0.094406, "capital": 9055.94, "trades": 2727, "positions": 3, "exposure": 0.03, "predictions": 11183}
data\v2.jsonl:1076:{"tick": 5305, "t": "04:46:15", "acc": 0.515, "entropy": 0.9826, "ret": -0.094662, "capital": 9053.38, "trades": 2728, "positions": 4, "exposure": 0.04, "predictions": 11203}
data\v2.jsonl:1077:{"tick": 5310, "t": "04:51:17", "acc": 0.52, "entropy": 0.9832, "ret": -0.094667, "capital": 9053.33, "trades": 2730, "positions": 4, "exposure": 0.04, "predictions": 11223}
data\v2.jsonl:1078:{"tick": 5315, "t": "04:56:19", "acc": 0.515, "entropy": 0.9842, "ret": -0.09537, "capital": 9046.3, "trades": 2733, "positions": 2, "exposure": 0.02, "predictions": 11243}
data\v2.jsonl:1079:{"tick": 5320, "t": "05:01:23", "acc": 0.52, "entropy": 0.9845, "ret": -0.095199, "capital": 9048.01, "trades": 2735, "positions": 3, "exposure": 0.03, "predictions": 11263}
data\v2.jsonl:1080:{"tick": 5325, "t": "05:06:25", "acc": 0.54, "entropy": 0.9818, "ret": -0.094523, "capital": 9054.77, "trades": 2739, "positions": 3, "exposure": 0.03, "predictions": 11283}
data\v2.jsonl:1081:{"tick": 5330, "t": "05:11:27", "acc": 0.535, "entropy": 0.9815, "ret": -0.094664, "capital": 9053.36, "trades": 2741, "positions": 4, "exposure": 0.04, "predictions": 11303}
data\v2.jsonl:1082:{"tick": 5335, "t": "05:16:29", "acc": 0.535, "entropy": 0.981, "ret": -0.094841, "capital": 9051.59, "trades": 2744, "positions": 2, "exposure": 0.02, "predictions": 11323}
data\v2.jsonl:1083:{"tick": 5340, "t": "05:21:31", "acc": 0.535, "entropy": 0.9817, "ret": -0.094838, "capital": 9051.62, "trades": 2747, "positions": 1, "exposure": 0.01, "predictions": 11343}
data\v2.jsonl:1084:{"tick": 5345, "t": "05:26:34", "acc": 0.51, "entropy": 0.9794, "ret": -0.094637, "capital": 9053.63, "trades": 2749, "positions": 2, "exposure": 0.02, "predictions": 11363}
data\v2.jsonl:1085:{"tick": 5350, "t": "05:31:36", "acc": 0.48, "entropy": 0.9817, "ret": -0.094995, "capital": 9050.05, "trades": 2753, "positions": 1, "exposure": 0.01, "predictions": 11383}
data\v2.jsonl:1086:{"tick": 5355, "t": "05:36:38", "acc": 0.485, "entropy": 0.9843, "ret": -0.094967, "capital": 9050.33, "trades": 2754, "positions": 3, "exposure": 0.03, "predictions": 11403}
data\v2.jsonl:1087:{"tick": 5360, "t": "05:41:40", "acc": 0.49, "entropy": 0.9835, "ret": -0.094233, "capital": 9057.67, "trades": 2758, "positions": 2, "exposure": 0.02, "predictions": 11423}
data\v2.jsonl:1088:{"tick": 5365, "t": "05:46:42", "acc": 0.505, "entropy": 0.9823, "ret": -0.093872, "capital": 9061.28, "trades": 2762, "positions": 1, "exposure": 0.01, "predictions": 11443}
data\v2.jsonl:1089:{"tick": 5370, "t": "05:51:44", "acc": 0.505, "entropy": 0.9799, "ret": -0.094177, "capital": 9058.23, "trades": 2764, "positions": 3, "exposure": 0.03, "predictions": 11463}
data\v2.jsonl:1090:{"tick": 5375, "t": "05:56:47", "acc": 0.5, "entropy": 0.9821, "ret": -0.094274, "capital": 9057.26, "trades": 2768, "positions": 1, "exposure": 0.01, "predictions": 11483}
data\v2.jsonl:1091:{"tick": 5380, "t": "06:01:49", "acc": 0.515, "entropy": 0.9846, "ret": -0.094251, "capital": 9057.49, "trades": 2771, "positions": 1, "exposure": 0.01, "predictions": 11503}
data\v2.jsonl:1092:{"tick": 5385, "t": "06:06:51", "acc": 0.545, "entropy": 0.9821, "ret": -0.093822, "capital": 9061.78, "trades": 2773, "positions": 2, "exposure": 0.02, "predictions": 11523}
data\v2.jsonl:1093:{"tick": 5390, "t": "06:11:53", "acc": 0.535, "entropy": 0.9815, "ret": -0.093878, "capital": 9061.22, "trades": 2776, "positions": 3, "exposure": 0.03, "predictions": 11543}
data\v2.jsonl:1094:{"tick": 5395, "t": "06:16:55", "acc": 0.54, "entropy": 0.9788, "ret": -0.093948, "capital": 9060.52, "trades": 2778, "positions": 2, "exposure": 0.02, "predictions": 11563}
data\v2.jsonl:1095:{"tick": 5400, "t": "06:21:57", "acc": 0.545, "entropy": 0.9793, "ret": -0.093735, "capital": 9062.65, "trades": 2781, "positions": 1, "exposure": 0.01, "predictions": 11583}
data\v2.jsonl:1096:{"tick": 5405, "t": "06:27:00", "acc": 0.53, "entropy": 0.9793, "ret": -0.093923, "capital": 9060.77, "trades": 2784, "positions": 2, "exposure": 0.02, "predictions": 11603}
data\v2.jsonl:1097:{"tick": 5410, "t": "06:32:02", "acc": 0.515, "entropy": 0.9816, "ret": -0.094004, "capital": 9059.96, "trades": 2787, "positions": 2, "exposure": 0.02, "predictions": 11623}
data\v2.jsonl:1098:{"tick": 5415, "t": "06:37:42", "acc": 0.53, "entropy": 0.9765, "ret": -0.094149, "capital": 9058.51, "trades": 2789, "positions": 2, "exposure": 0.02, "predictions": 11642}
data\v2.jsonl:1099:{"tick": 5420, "t": "06:42:59", "acc": 0.53, "entropy": 0.9782, "ret": -0.093921, "capital": 9060.79, "trades": 2792, "positions": 2, "exposure": 0.02, "predictions": 11662}
data\v2.jsonl:1100:{"tick": 5425, "t": "06:48:04", "acc": 0.535, "entropy": 0.9805, "ret": -0.093867, "capital": 9061.33, "trades": 2795, "positions": 3, "exposure": 0.03, "predictions": 11682}
data\v2.jsonl:1101:{"tick": 5430, "t": "06:53:06", "acc": 0.53, "entropy": 0.9756, "ret": -0.093474, "capital": 9065.26, "trades": 2799, "positions": 2, "exposure": 0.02, "predictions": 11702}
data\v2.jsonl:1102:{"tick": 5435, "t": "06:58:16", "acc": 0.5, "entropy": 0.9829, "ret": -0.093217, "capital": 9067.83, "trades": 2803, "positions": 1, "exposure": 0.0103, "predictions": 11722}
data\v2.jsonl:1103:{"tick": 5440, "t": "07:03:18", "acc": 0.51, "entropy": 0.9823, "ret": -0.092921, "capital": 9070.79, "trades": 2808, "positions": 0, "exposure": 0, "predictions": 11742}
data\v2.jsonl:1104:{"tick": 5445, "t": "07:08:20", "acc": 0.52, "entropy": 0.984, "ret": -0.092969, "capital": 9070.31, "trades": 2809, "positions": 2, "exposure": 0.0288, "predictions": 11762}
data\v2.jsonl:1105:{"tick": 5450, "t": "07:13:22", "acc": 0.53, "entropy": 0.986, "ret": -0.092875, "capital": 9071.25, "trades": 2812, "positions": 3, "exposure": 0.0724, "predictions": 11782}
data\v2.jsonl:1106:{"tick": 5455, "t": "07:18:24", "acc": 0.53, "entropy": 0.9869, "ret": -0.093894, "capital": 9061.06, "trades": 2816, "positions": 1, "exposure": 0.0341, "predictions": 11802}
data\v2.jsonl:1107:{"tick": 5460, "t": "07:23:27", "acc": 0.54, "entropy": 0.9827, "ret": -0.094429, "capital": 9055.71, "trades": 2819, "positions": 2, "exposure": 0.066, "predictions": 11822}
data\v2.jsonl:1108:{"tick": 5465, "t": "07:28:29", "acc": 0.54, "entropy": 0.979, "ret": -0.094564, "capital": 9054.36, "trades": 2820, "positions": 3, "exposure": 0.074, "predictions": 11842}
data\v2.jsonl:1109:{"tick": 5470, "t": "07:33:31", "acc": 0.545, "entropy": 0.979, "ret": -0.093843, "capital": 9061.57, "trades": 2824, "positions": 3, "exposure": 0.0907, "predictions": 11862}
data\v2.jsonl:1110:{"tick": 5475, "t": "07:38:34", "acc": 0.54, "entropy": 0.9768, "ret": -0.094391, "capital": 9056.09, "trades": 2828, "positions": 0, "exposure": 0, "predictions": 11882}
data\v2.jsonl:1111:{"tick": 5480, "t": "07:43:36", "acc": 0.53, "entropy": 0.9814, "ret": -0.095248, "capital": 9047.52, "trades": 2830, "positions": 3, "exposure": 0.1186, "predictions": 11902}
data\v2.jsonl:1112:{"tick": 5485, "t": "07:48:37", "acc": 0.555, "entropy": 0.9815, "ret": -0.093744, "capital": 9062.56, "trades": 2834, "positions": 3, "exposure": 0.1024, "predictions": 11922}
data\v2.jsonl:1113:{"tick": 5490, "t": "07:53:40", "acc": 0.535, "entropy": 0.9837, "ret": -0.098412, "capital": 9015.88, "trades": 2838, "positions": 1, "exposure": 0.0223, "predictions": 11942}
data\v2.jsonl:1114:{"tick": 5495, "t": "07:58:42", "acc": 0.525, "entropy": 0.9881, "ret": -0.099065, "capital": 9009.35, "trades": 2842, "positions": 1, "exposure": 0.01, "predictions": 11962}
data\v2.jsonl:1115:{"tick": 5500, "t": "08:03:44", "acc": 0.55, "entropy": 0.9843, "ret": -0.099099, "capital": 9009.01, "trades": 2844, "positions": 3, "exposure": 0.0359, "predictions": 11982}
data\v2.jsonl:1116:{"tick": 5505, "t": "08:08:46", "acc": 0.56, "entropy": 0.9858, "ret": -0.097351, "capital": 9026.49, "trades": 2849, "positions": 1, "exposure": 0.0195, "predictions": 12002}
data\v2.jsonl:1117:{"tick": 5510, "t": "08:13:48", "acc": 0.545, "entropy": 0.9846, "ret": -0.097399, "capital": 9026.01, "trades": 2854, "positions": 2, "exposure": 0.0227, "predictions": 12022}
data\v2.jsonl:1118:{"tick": 5515, "t": "08:18:50", "acc": 0.53, "entropy": 0.9828, "ret": -0.098035, "capital": 9019.65, "trades": 2857, "positions": 2, "exposure": 0.0241, "predictions": 12042}
data\v2.jsonl:1119:{"tick": 5520, "t": "08:23:53", "acc": 0.515, "entropy": 0.9839, "ret": -0.099102, "capital": 9008.98, "trades": 2862, "positions": 3, "exposure": 0.0329, "predictions": 12062}
data\v2.jsonl:1120:{"tick": 5525, "t": "08:28:56", "acc": 0.52, "entropy": 0.9813, "ret": -0.098827, "capital": 9011.73, "trades": 2865, "positions": 2, "exposure": 0.0238, "predictions": 12082}
data\v2.jsonl:1121:{"tick": 5530, "t": "08:34:06", "acc": 0.515, "entropy": 0.982, "ret": -0.098863, "capital": 9011.37, "trades": 2869, "positions": 2, "exposure": 0.02, "predictions": 12102}
data\v2.jsonl:1122:{"tick": 5535, "t": "08:39:08", "acc": 0.485, "entropy": 0.9786, "ret": -0.100084, "capital": 8999.16, "trades": 2875, "positions": 3, "exposure": 0.0464, "predictions": 12122}
data\v2.jsonl:1123:{"tick": 5540, "t": "08:44:11", "acc": 0.51, "entropy": 0.9821, "ret": -0.099888, "capital": 9001.12, "trades": 2879, "positions": 3, "exposure": 0.0474, "predictions": 12142}
data\v2.jsonl:1124:{"tick": 5545, "t": "08:49:32", "acc": 0.535, "entropy": 0.982, "ret": -0.100204, "capital": 8997.96, "trades": 2882, "positions": 2, "exposure": 0.0467, "predictions": 12162}
data\v2.jsonl:1125:{"tick": 5550, "t": "08:54:35", "acc": 0.51, "entropy": 0.9793, "ret": -0.097908, "capital": 9020.92, "trades": 2883, "positions": 3, "exposure": 0.0618, "predictions": 12182}
data\v2.jsonl:1126:{"tick": 5555, "t": "08:59:37", "acc": 0.51, "entropy": 0.9835, "ret": -0.099982, "capital": 9000.18, "trades": 2888, "positions": 3, "exposure": 0.0325, "predictions": 12202}
data\v2.jsonl:1127:{"tick": 5560, "t": "09:04:39", "acc": 0.52, "entropy": 0.982, "ret": -0.100412, "capital": 8995.88, "trades": 2891, "positions": 3, "exposure": 0.0325, "predictions": 12222}
data\v2.jsonl:1128:{"tick": 5565, "t": "09:09:41", "acc": 0.53, "entropy": 0.9822, "ret": -0.100323, "capital": 8996.77, "trades": 2893, "positions": 3, "exposure": 0.0328, "predictions": 12242}
data\v2.jsonl:1129:{"tick": 5570, "t": "09:14:43", "acc": 0.54, "entropy": 0.9804, "ret": -0.098764, "capital": 9012.36, "trades": 2898, "positions": 1, "exposure": 0.0103, "predictions": 12262}
data\v2.jsonl:1130:{"tick": 5575, "t": "09:19:45", "acc": 0.535, "entropy": 0.9821, "ret": -0.09851, "capital": 9014.9, "trades": 2902, "positions": 2, "exposure": 0.0209, "predictions": 12282}
data\v2.jsonl:1131:{"tick": 5580, "t": "09:24:48", "acc": 0.53, "entropy": 0.9797, "ret": -0.098763, "capital": 9012.37, "trades": 2905, "positions": 2, "exposure": 0.02, "predictions": 12302}
data\v2.jsonl:1132:{"tick": 5585, "t": "09:29:50", "acc": 0.535, "entropy": 0.9784, "ret": -0.098857, "capital": 9011.43, "trades": 2907, "positions": 2, "exposure": 0.02, "predictions": 12322}
data\v2.jsonl:1133:{"tick": 5590, "t": "09:34:52", "acc": 0.535, "entropy": 0.9779, "ret": -0.099322, "capital": 9006.78, "trades": 2910, "positions": 3, "exposure": 0.03, "predictions": 12342}
data\v2.jsonl:1134:{"tick": 5595, "t": "09:39:54", "acc": 0.515, "entropy": 0.9792, "ret": -0.099273, "capital": 9007.27, "trades": 2912, "positions": 2, "exposure": 0.0231, "predictions": 12362}
data\v2.jsonl:1135:{"tick": 5600, "t": "09:44:56", "acc": 0.515, "entropy": 0.9797, "ret": -0.099193, "capital": 9008.07, "trades": 2916, "positions": 2, "exposure": 0.02, "predictions": 12382}
data\v2.jsonl:1136:{"tick": 5605, "t": "09:49:58", "acc": 0.505, "entropy": 0.9785, "ret": -0.099361, "capital": 9006.39, "trades": 2919, "positions": 3, "exposure": 0.03, "predictions": 12402}
data\v2.jsonl:1137:{"tick": 5610, "t": "09:55:00", "acc": 0.495, "entropy": 0.9817, "ret": -0.09967, "capital": 9003.3, "trades": 2924, "positions": 0, "exposure": 0, "predictions": 12422}
data\v2.jsonl:1138:{"tick": 5615, "t": "10:00:02", "acc": 0.5, "entropy": 0.9833, "ret": -0.099064, "capital": 9009.36, "trades": 2926, "positions": 2, "exposure": 0.02, "predictions": 12442}
data\v2.jsonl:1139:{"tick": 5620, "t": "10:05:04", "acc": 0.465, "entropy": 0.9794, "ret": -0.099062, "capital": 9009.38, "trades": 2929, "positions": 2, "exposure": 0.02, "predictions": 12462}
data\v2.jsonl:1140:{"tick": 5625, "t": "10:10:06", "acc": 0.45, "entropy": 0.9833, "ret": -0.099576, "capital": 9004.24, "trades": 2933, "positions": 2, "exposure": 0.02, "predictions": 12482}
data\v2.jsonl:1141:{"tick": 5630, "t": "10:15:08", "acc": 0.46, "entropy": 0.9836, "ret": -0.099759, "capital": 9002.41, "trades": 2936, "positions": 1, "exposure": 0.01, "predictions": 12502}
data\v2.jsonl:1142:{"tick": 5635, "t": "10:20:10", "acc": 0.465, "entropy": 0.9863, "ret": -0.099796, "capital": 9002.04, "trades": 2939, "positions": 4, "exposure": 0.04, "predictions": 12522}
data\v2.jsonl:1143:{"tick": 5640, "t": "10:26:41", "acc": 0.47, "entropy": 0.9834, "ret": -0.099986, "capital": 9000.14, "trades": 2942, "positions": 3, "exposure": 0.03, "predictions": 12539}
data\v2.jsonl:1144:{"tick": 5645, "t": "10:32:13", "acc": 0.47, "entropy": 0.9865, "ret": -0.100279, "capital": 8997.21, "trades": 2946, "positions": 3, "exposure": 0.03, "predictions": 12559}
data\v2.jsonl:1145:{"tick": 5650, "t": "10:37:25", "acc": 0.465, "entropy": 0.9864, "ret": -0.100364, "capital": 8996.36, "trades": 2949, "positions": 3, "exposure": 0.03, "predictions": 12579}
data\v2.jsonl:1146:{"tick": 5655, "t": "10:42:27", "acc": 0.46, "entropy": 0.986, "ret": -0.100406, "capital": 8995.94, "trades": 2952, "positions": 3, "exposure": 0.03, "predictions": 12599}
data\v2.jsonl:1147:{"tick": 5660, "t": "10:47:29", "acc": 0.48, "entropy": 0.9836, "ret": -0.100224, "capital": 8997.76, "trades": 2955, "positions": 1, "exposure": 0.01, "predictions": 12619}
data\v2.jsonl:1148:{"tick": 5665, "t": "10:52:31", "acc": 0.48, "entropy": 0.9852, "ret": -0.10052, "capital": 8994.8, "trades": 2958, "positions": 3, "exposure": 0.03, "predictions": 12639}
data\v2.jsonl:1149:{"tick": 5670, "t": "10:57:33", "acc": 0.53, "entropy": 0.9873, "ret": -0.10052, "capital": 8994.8, "trades": 2961, "positions": 1, "exposure": 0.01, "predictions": 12659}
data\v2.jsonl:1150:{"tick": 5675, "t": "11:02:36", "acc": 0.52, "entropy": 0.9856, "ret": -0.100627, "capital": 8993.73, "trades": 2966, "positions": 2, "exposure": 0.02, "predictions": 12679}
data\v2.jsonl:1151:{"tick": 5680, "t": "11:07:38", "acc": 0.54, "entropy": 0.9851, "ret": -0.101215, "capital": 8987.85, "trades": 2968, "positions": 2, "exposure": 0.02, "predictions": 12699}
data\v2.jsonl:1152:{"tick": 5685, "t": "11:12:40", "acc": 0.535, "entropy": 0.9842, "ret": -0.101003, "capital": 8989.97, "trades": 2970, "positions": 2, "exposure": 0.02, "predictions": 12719}
data\v2.jsonl:1153:{"tick": 5690, "t": "11:17:42", "acc": 0.52, "entropy": 0.9832, "ret": -0.101517, "capital": 8984.83, "trades": 2974, "positions": 2, "exposure": 0.02, "predictions": 12739}
data\v2.jsonl:1154:{"tick": 5695, "t": "11:22:44", "acc": 0.51, "entropy": 0.9855, "ret": -0.101109, "capital": 8988.91, "trades": 2975, "positions": 3, "exposure": 0.03, "predictions": 12759}
data\v2.jsonl:1155:{"tick": 5700, "t": "11:27:46", "acc": 0.51, "entropy": 0.9842, "ret": -0.100476, "capital": 8995.24, "trades": 2979, "positions": 1, "exposure": 0.01, "predictions": 12779}
data\v2.jsonl:1156:{"tick": 5705, "t": "11:32:48", "acc": 0.525, "entropy": 0.9828, "ret": -0.100838, "capital": 8991.62, "trades": 2982, "positions": 1, "exposure": 0.01, "predictions": 12799}
data\v2.jsonl:1157:{"tick": 5710, "t": "11:37:50", "acc": 0.51, "entropy": 0.9858, "ret": -0.101506, "capital": 8984.94, "trades": 2987, "positions": 1, "exposure": 0.01, "predictions": 12819}
data\v2.jsonl:1158:{"tick": 5715, "t": "11:42:52", "acc": 0.475, "entropy": 0.9835, "ret": -0.10105, "capital": 8989.5, "trades": 2990, "positions": 2, "exposure": 0.02, "predictions": 12839}
data\v2.jsonl:1159:{"tick": 5720, "t": "11:47:54", "acc": 0.46, "entropy": 0.9869, "ret": -0.10036, "capital": 8996.4, "trades": 2993, "positions": 3, "exposure": 0.03, "predictions": 12859}
data\v2.jsonl:1160:{"tick": 5725, "t": "11:52:56", "acc": 0.47, "entropy": 0.9889, "ret": -0.099852, "capital": 9001.48, "trades": 2997, "positions": 1, "exposure": 0.01, "predictions": 12879}
data\v2.jsonl:1161:{"tick": 5730, "t": "11:57:58", "acc": 0.445, "entropy": 0.9848, "ret": -0.100777, "capital": 8992.23, "trades": 3002, "positions": 1, "exposure": 0.01, "predictions": 12899}
data\v2.jsonl:1162:{"tick": 5735, "t": "12:03:01", "acc": 0.445, "entropy": 0.9866, "ret": -0.100969, "capital": 8990.31, "trades": 3004, "positions": 1, "exposure": 0.01, "predictions": 12919}
data\v2.jsonl:1163:{"tick": 5740, "t": "12:08:03", "acc": 0.445, "entropy": 0.9886, "ret": -0.10064, "capital": 8993.6, "trades": 3008, "positions": 2, "exposure": 0.02, "predictions": 12939}
data\v2.jsonl:1164:{"tick": 5745, "t": "12:13:05", "acc": 0.46, "entropy": 0.9871, "ret": -0.100547, "capital": 8994.53, "trades": 3011, "positions": 2, "exposure": 0.02, "predictions": 12959}
data\v2.jsonl:1165:{"tick": 5750, "t": "12:18:07", "acc": 0.455, "entropy": 0.9849, "ret": -0.100711, "capital": 8992.89, "trades": 3015, "positions": 1, "exposure": 0.01, "predictions": 12979}
data\v2.jsonl:1166:{"tick": 5755, "t": "12:23:09", "acc": 0.43, "entropy": 0.9859, "ret": -0.100894, "capital": 8991.06, "trades": 3018, "positions": 3, "exposure": 0.03, "predictions": 12999}
data\v2.jsonl:1167:{"tick": 5760, "t": "12:28:11", "acc": 0.45, "entropy": 0.9882, "ret": -0.100642, "capital": 8993.58, "trades": 3021, "positions": 2, "exposure": 0.02, "predictions": 13019}
data\v2.jsonl:1168:{"tick": 5765, "t": "12:33:13", "acc": 0.465, "entropy": 0.9873, "ret": -0.100919, "capital": 8990.81, "trades": 3026, "positions": 1, "exposure": 0.01, "predictions": 13039}
data\v2.jsonl:1169:{"tick": 5770, "t": "12:38:16", "acc": 0.46, "entropy": 0.9871, "ret": -0.101377, "capital": 8986.23, "trades": 3028, "positions": 3, "exposure": 0.03, "predictions": 13059}
data\v2.jsonl:1170:{"tick": 5775, "t": "12:43:18", "acc": 0.435, "entropy": 0.9876, "ret": -0.101301, "capital": 8986.99, "trades": 3031, "positions": 1, "exposure": 0.01, "predictions": 13079}
data\v2.jsonl:1171:{"tick": 5780, "t": "12:48:20", "acc": 0.45, "entropy": 0.9853, "ret": -0.101054, "capital": 8989.46, "trades": 3034, "positions": 2, "exposure": 0.02, "predictions": 13099}
data\v2.jsonl:1172:{"tick": 5785, "t": "12:53:22", "acc": 0.46, "entropy": 0.9865, "ret": -0.100607, "capital": 8993.93, "trades": 3038, "positions": 3, "exposure": 0.03, "predictions": 13119}
data\v2.jsonl:1173:{"tick": 5790, "t": "12:58:24", "acc": 0.47, "entropy": 0.9859, "ret": -0.100417, "capital": 8995.83, "trades": 3040, "positions": 2, "exposure": 0.02, "predictions": 13139}
data\v2.jsonl:1174:{"tick": 5795, "t": "13:03:26", "acc": 0.475, "entropy": 0.9864, "ret": -0.100528, "capital": 8994.72, "trades": 3042, "positions": 2, "exposure": 0.02, "predictions": 13159}
data\v2.jsonl:1175:{"tick": 5800, "t": "13:08:28", "acc": 0.475, "entropy": 0.9848, "ret": -0.100518, "capital": 8994.82, "trades": 3043, "positions": 3, "exposure": 0.03, "predictions": 13179}
data\v2.jsonl:1176:{"tick": 5805, "t": "13:13:30", "acc": 0.485, "entropy": 0.9865, "ret": -0.10077, "capital": 8992.3, "trades": 3046, "positions": 2, "exposure": 0.02, "predictions": 13199}
data\v2.jsonl:1177:{"tick": 5810, "t": "13:18:32", "acc": 0.475, "entropy": 0.9859, "ret": -0.100663, "capital": 8993.37, "trades": 3048, "positions": 4, "exposure": 0.04, "predictions": 13219}
data\v2.jsonl:1178:{"tick": 5815, "t": "13:23:34", "acc": 0.47, "entropy": 0.9856, "ret": -0.100827, "capital": 8991.73, "trades": 3052, "positions": 2, "exposure": 0.02, "predictions": 13239}
data\v2.jsonl:1179:{"tick": 5820, "t": "13:28:36", "acc": 0.465, "entropy": 0.9872, "ret": -0.101171, "capital": 8988.29, "trades": 3053, "positions": 3, "exposure": 0.03, "predictions": 13259}
data\v2.jsonl:1180:{"tick": 5825, "t": "13:33:39", "acc": 0.5, "entropy": 0.9857, "ret": -0.100964, "capital": 8990.36, "trades": 3056, "positions": 2, "exposure": 0.02, "predictions": 13279}
data\v2.jsonl:1181:{"tick": 5830, "t": "13:38:42", "acc": 0.525, "entropy": 0.9858, "ret": -0.100791, "capital": 8992.09, "trades": 3059, "positions": 2, "exposure": 0.02, "predictions": 13299}
data\v2.jsonl:1182:{"tick": 5835, "t": "13:43:44", "acc": 0.515, "entropy": 0.9823, "ret": -0.101667, "capital": 8983.33, "trades": 3062, "positions": 2, "exposure": 0.02, "predictions": 13319}
data\v2.jsonl:1183:{"tick": 5840, "t": "13:48:59", "acc": 0.505, "entropy": 0.9874, "ret": -0.102619, "capital": 8973.81, "trades": 3065, "positions": 2, "exposure": 0.02, "predictions": 13339}
data\v2.jsonl:1184:{"tick": 5845, "t": "13:54:01", "acc": 0.47, "entropy": 0.9866, "ret": -0.102112, "capital": 8978.88, "trades": 3066, "positions": 4, "exposure": 0.04, "predictions": 13359}
data\v2.jsonl:1185:{"tick": 5850, "t": "13:59:03", "acc": 0.48, "entropy": 0.9884, "ret": -0.10349, "capital": 8965.1, "trades": 3069, "positions": 2, "exposure": 0.02, "predictions": 13379}
data\v2.jsonl:1186:{"tick": 5855, "t": "14:04:06", "acc": 0.5, "entropy": 0.9882, "ret": -0.103246, "capital": 8967.54, "trades": 3073, "positions": 3, "exposure": 0.03, "predictions": 13399}
data\v2.jsonl:1187:{"tick": 5860, "t": "14:08:59", "acc": 0.51, "entropy": 0.9886, "ret": -0.103481, "capital": 8965.19, "trades": 3079, "positions": 1, "exposure": 0.01, "predictions": 13419}
data\v2.jsonl:1188:{"tick": 5865, "t": "14:14:01", "acc": 0.52, "entropy": 0.9886, "ret": -0.103632, "capital": 8963.68, "trades": 3083, "positions": 0, "exposure": 0, "predictions": 13439}
data\v2.jsonl:1189:{"tick": 5870, "t": "14:19:03", "acc": 0.53, "entropy": 0.9919, "ret": -0.103656, "capital": 8963.44, "trades": 3084, "positions": 2, "exposure": 0.02, "predictions": 13459}
data\v2.jsonl:1190:{"tick": 5875, "t": "14:24:05", "acc": 0.52, "entropy": 0.991, "ret": -0.103754, "capital": 8962.46, "trades": 3087, "positions": 2, "exposure": 0.02, "predictions": 13479}
data\v2.jsonl:1191:{"tick": 5880, "t": "14:29:07", "acc": 0.5, "entropy": 0.9857, "ret": -0.10406, "capital": 8959.4, "trades": 3089, "positions": 3, "exposure": 0.03, "predictions": 13499}
data\v2.jsonl:1192:{"tick": 5885, "t": "14:34:10", "acc": 0.51, "entropy": 0.9863, "ret": -0.103499, "capital": 8965.01, "trades": 3094, "positions": 0, "exposure": 0, "predictions": 13519}
data\v2.jsonl:1193:{"tick": 5890, "t": "14:39:12", "acc": 0.53, "entropy": 0.9859, "ret": -0.10346, "capital": 8965.4, "trades": 3096, "positions": 2, "exposure": 0.02, "predictions": 13539}
data\v2.jsonl:1194:{"tick": 5895, "t": "14:44:14", "acc": 0.535, "entropy": 0.99, "ret": -0.103927, "capital": 8960.73, "trades": 3101, "positions": 3, "exposure": 0.03, "predictions": 13559}
data\v2.jsonl:1195:{"tick": 5900, "t": "14:49:15", "acc": 0.535, "entropy": 0.9913, "ret": -0.104631, "capital": 8953.69, "trades": 3104, "positions": 3, "exposure": 0.03, "predictions": 13579}
data\v2.jsonl:1196:{"tick": 5905, "t": "14:54:17", "acc": 0.515, "entropy": 0.9881, "ret": -0.104633, "capital": 8953.67, "trades": 3110, "positions": 3, "exposure": 0.03, "predictions": 13599}
data\v2.jsonl:1197:{"tick": 5910, "t": "14:59:19", "acc": 0.505, "entropy": 0.9871, "ret": -0.104565, "capital": 8954.35, "trades": 3113, "positions": 3, "exposure": 0.03, "predictions": 13619}
data\v2.jsonl:1198:{"tick": 5915, "t": "15:04:22", "acc": 0.5, "entropy": 0.9865, "ret": -0.10556, "capital": 8944.4, "trades": 3116, "positions": 3, "exposure": 0.03, "predictions": 13639}
data\v2.jsonl:1199:{"tick": 5920, "t": "15:09:25", "acc": 0.51, "entropy": 0.9858, "ret": -0.105296, "capital": 8947.04, "trades": 3120, "positions": 3, "exposure": 0.03, "predictions": 13659}
data\v2.jsonl:1200:{"tick": 5925, "t": "15:14:27", "acc": 0.51, "entropy": 0.9867, "ret": -0.105169, "capital": 8948.31, "trades": 3128, "positions": 1, "exposure": 0.01, "predictions": 13679}
data\v2.jsonl:1201:{"tick": 5930, "t": "15:19:29", "acc": 0.49, "entropy": 0.9862, "ret": -0.105445, "capital": 8945.55, "trades": 3133, "positions": 2, "exposure": 0.02, "predictions": 13699}
data\v2.jsonl:1202:{"tick": 5935, "t": "15:24:31", "acc": 0.495, "entropy": 0.9856, "ret": -0.105534, "capital": 8944.66, "trades": 3137, "positions": 1, "exposure": 0.01, "predictions": 13719}
data\v2.jsonl:1203:{"tick": 5940, "t": "15:29:32", "acc": 0.48, "entropy": 0.9842, "ret": -0.105704, "capital": 8942.96, "trades": 3140, "positions": 1, "exposure": 0.01, "predictions": 13739}
data\v2.jsonl:1204:{"tick": 5945, "t": "15:34:35", "acc": 0.495, "entropy": 0.9852, "ret": -0.105605, "capital": 8943.95, "trades": 3142, "positions": 3, "exposure": 0.03, "predictions": 13759}
data\v2.jsonl:1205:{"tick": 5950, "t": "15:39:37", "acc": 0.52, "entropy": 0.9868, "ret": -0.105338, "capital": 8946.62, "trades": 3148, "positions": 0, "exposure": 0, "predictions": 13779}
data\v2.jsonl:1206:{"tick": 5955, "t": "15:44:39", "acc": 0.505, "entropy": 0.988, "ret": -0.105492, "capital": 8945.08, "trades": 3150, "positions": 2, "exposure": 0.02, "predictions": 13799}
data\v2.jsonl:1207:{"tick": 5960, "t": "15:49:41", "acc": 0.49, "entropy": 0.988, "ret": -0.105594, "capital": 8944.06, "trades": 3152, "positions": 3, "exposure": 0.03, "predictions": 13819}
data\v2.jsonl:1208:{"tick": 5965, "t": "15:54:43", "acc": 0.495, "entropy": 0.9874, "ret": -0.105854, "capital": 8941.46, "trades": 3155, "positions": 2, "exposure": 0.02, "predictions": 13839}
data\v2.jsonl:1209:{"tick": 5970, "t": "15:59:45", "acc": 0.485, "entropy": 0.9853, "ret": -0.106419, "capital": 8935.81, "trades": 3158, "positions": 2, "exposure": 0.02, "predictions": 13859}
data\v2.jsonl:1210:{"tick": 5975, "t": "16:04:47", "acc": 0.49, "entropy": 0.9875, "ret": -0.104674, "capital": 8953.26, "trades": 3163, "positions": 3, "exposure": 0.03, "predictions": 13879}
data\v2.jsonl:1211:{"tick": 5980, "t": "16:09:49", "acc": 0.5, "entropy": 0.9905, "ret": -0.104552, "capital": 8954.48, "trades": 3167, "positions": 3, "exposure": 0.03, "predictions": 13899}
data\v2.jsonl:1212:{"tick": 5985, "t": "16:14:51", "acc": 0.495, "entropy": 0.9878, "ret": -0.105062, "capital": 8949.38, "trades": 3171, "positions": 1, "exposure": 0.01, "predictions": 13919}
data\v2.jsonl:1213:{"tick": 5990, "t": "16:19:53", "acc": 0.51, "entropy": 0.988, "ret": -0.104904, "capital": 8950.96, "trades": 3174, "positions": 4, "exposure": 0.04, "predictions": 13939}
data\v2.jsonl:1214:{"tick": 5995, "t": "16:24:55", "acc": 0.52, "entropy": 0.9883, "ret": -0.107297, "capital": 8927.03, "trades": 3177, "positions": 2, "exposure": 0.02, "predictions": 13959}
data\v2.jsonl:1215:{"tick": 6000, "t": "16:29:57", "acc": 0.51, "entropy": 0.9877, "ret": -0.106931, "capital": 8930.69, "trades": 3180, "positions": 2, "exposure": 0.02, "predictions": 13979}
data\v2.jsonl:1216:{"tick": 6005, "t": "16:35:00", "acc": 0.525, "entropy": 0.9845, "ret": -0.10704, "capital": 8929.6, "trades": 3184, "positions": 3, "exposure": 0.03, "predictions": 13999}
data\v2.jsonl:1217:{"tick": 6010, "t": "16:40:02", "acc": 0.515, "entropy": 0.9862, "ret": -0.106726, "capital": 8932.74, "trades": 3188, "positions": 2, "exposure": 0.02, "predictions": 14019}
data\v2.jsonl:1218:{"tick": 6015, "t": "16:45:04", "acc": 0.525, "entropy": 0.9876, "ret": -0.1068, "capital": 8932.0, "trades": 3190, "positions": 4, "exposure": 0.04, "predictions": 14039}
data\v2.jsonl:1219:{"tick": 6020, "t": "16:50:06", "acc": 0.505, "entropy": 0.9888, "ret": -0.106969, "capital": 8930.31, "trades": 3195, "positions": 1, "exposure": 0.01, "predictions": 14059}
data\v2.jsonl:1220:{"tick": 6025, "t": "16:55:08", "acc": 0.49, "entropy": 0.9858, "ret": -0.106824, "capital": 8931.76, "trades": 3200, "positions": 1, "exposure": 0.01, "predictions": 14079}
data\v2.jsonl:1221:{"tick": 6030, "t": "17:00:10", "acc": 0.51, "entropy": 0.9853, "ret": -0.10658, "capital": 8934.2, "trades": 3202, "positions": 3, "exposure": 0.03, "predictions": 14099}
data\v2.jsonl:1222:{"tick": 6035, "t": "17:05:12", "acc": 0.52, "entropy": 0.9888, "ret": -0.105852, "capital": 8941.48, "trades": 3206, "positions": 3, "exposure": 0.03, "predictions": 14119}
data\v2.jsonl:1223:{"tick": 6040, "t": "17:10:14", "acc": 0.505, "entropy": 0.9903, "ret": -0.105983, "capital": 8940.17, "trades": 3211, "positions": 1, "exposure": 0.01, "predictions": 14139}
data\v2.jsonl:1224:{"tick": 6045, "t": "17:15:16", "acc": 0.505, "entropy": 0.9896, "ret": -0.106413, "capital": 8935.87, "trades": 3214, "positions": 1, "exposure": 0.01, "predictions": 14159}
data\v2.jsonl:1225:{"tick": 6050, "t": "17:20:18", "acc": 0.47, "entropy": 0.99, "ret": -0.106482, "capital": 8935.18, "trades": 3219, "positions": 1, "exposure": 0.01, "predictions": 14179}
data\v2.jsonl:1226:{"tick": 6055, "t": "17:25:20", "acc": 0.485, "entropy": 0.9885, "ret": -0.106334, "capital": 8936.66, "trades": 3221, "positions": 1, "exposure": 0.01, "predictions": 14199}
data\v2.jsonl:1227:{"tick": 6060, "t": "17:30:22", "acc": 0.51, "entropy": 0.9899, "ret": -0.106414, "capital": 8935.86, "trades": 3222, "positions": 4, "exposure": 0.04, "predictions": 14219}
data\v2.jsonl:1228:{"tick": 6065, "t": "17:35:24", "acc": 0.51, "entropy": 0.9878, "ret": -0.106743, "capital": 8932.57, "trades": 3226, "positions": 3, "exposure": 0.03, "predictions": 14239}
data\v2.jsonl:1229:{"tick": 6070, "t": "17:40:26", "acc": 0.53, "entropy": 0.9908, "ret": -0.106675, "capital": 8933.25, "trades": 3227, "positions": 3, "exposure": 0.03, "predictions": 14259}
data\v2.jsonl:1230:{"tick": 6075, "t": "17:45:28", "acc": 0.545, "entropy": 0.99, "ret": -0.107208, "capital": 8927.92, "trades": 3229, "positions": 2, "exposure": 0.02, "predictions": 14279}
data\v2.jsonl:1231:{"tick": 6080, "t": "17:50:30", "acc": 0.53, "entropy": 0.9865, "ret": -0.107027, "capital": 8929.73, "trades": 3232, "positions": 1, "exposure": 0.01, "predictions": 14299}
data\v2.jsonl:1232:{"tick": 6085, "t": "17:55:32", "acc": 0.51, "entropy": 0.9884, "ret": -0.107136, "capital": 8928.64, "trades": 3234, "positions": 2, "exposure": 0.02, "predictions": 14319}
data\v2.jsonl:1233:{"tick": 6090, "t": "18:00:34", "acc": 0.5, "entropy": 0.9872, "ret": -0.107288, "capital": 8927.12, "trades": 3235, "positions": 4, "exposure": 0.04, "predictions": 14339}
data\v2.jsonl:1234:{"tick": 6095, "t": "18:05:37", "acc": 0.495, "entropy": 0.9874, "ret": -0.108011, "capital": 8919.89, "trades": 3242, "positions": 1, "exposure": 0.01, "predictions": 14359}
data\v2.jsonl:1235:{"tick": 6100, "t": "18:10:40", "acc": 0.51, "entropy": 0.9846, "ret": -0.108042, "capital": 8919.58, "trades": 3245, "positions": 2, "exposure": 0.02, "predictions": 14379}
data\v2.jsonl:1236:{"tick": 6105, "t": "18:15:42", "acc": 0.48, "entropy": 0.986, "ret": -0.108254, "capital": 8917.46, "trades": 3248, "positions": 4, "exposure": 0.04, "predictions": 14399}
data\v2.jsonl:1237:{"tick": 6110, "t": "18:20:44", "acc": 0.47, "entropy": 0.9871, "ret": -0.108723, "capital": 8912.77, "trades": 3251, "positions": 3, "exposure": 0.03, "predictions": 14419}
data\v2.jsonl:1238:{"tick": 6115, "t": "18:25:47", "acc": 0.455, "entropy": 0.9868, "ret": -0.108228, "capital": 8917.72, "trades": 3254, "positions": 2, "exposure": 0.02, "predictions": 14439}
data\v2.jsonl:1239:{"tick": 6120, "t": "18:30:50", "acc": 0.455, "entropy": 0.9866, "ret": -0.10874, "capital": 8912.6, "trades": 3257, "positions": 3, "exposure": 0.03, "predictions": 14459}
data\v2.jsonl:1240:{"tick": 6125, "t": "18:35:53", "acc": 0.445, "entropy": 0.9855, "ret": -0.109338, "capital": 8906.62, "trades": 3261, "positions": 2, "exposure": 0.02, "predictions": 14479}
data\v2.jsonl:1241:{"tick": 6130, "t": "18:40:55", "acc": 0.455, "entropy": 0.9879, "ret": -0.109423, "capital": 8905.77, "trades": 3265, "positions": 2, "exposure": 0.02, "predictions": 14499}
data\v2.jsonl:1242:{"tick": 6135, "t": "18:45:57", "acc": 0.47, "entropy": 0.9873, "ret": -0.109746, "capital": 8902.54, "trades": 3269, "positions": 0, "exposure": 0, "predictions": 14519}
data\v2.jsonl:1243:{"tick": 6140, "t": "18:51:00", "acc": 0.495, "entropy": 0.9838, "ret": -0.108862, "capital": 8911.38, "trades": 3272, "positions": 2, "exposure": 0.02, "predictions": 14539}
data\v2.jsonl:1244:{"tick": 6145, "t": "18:56:03", "acc": 0.49, "entropy": 0.985, "ret": -0.108489, "capital": 8915.11, "trades": 3275, "positions": 1, "exposure": 0.01, "predictions": 14559}
data\v2.jsonl:1245:{"tick": 6150, "t": "19:01:05", "acc": 0.49, "entropy": 0.9831, "ret": -0.108928, "capital": 8910.72, "trades": 3280, "positions": 1, "exposure": 0.01, "predictions": 14579}
data\v2.jsonl:1246:{"tick": 6155, "t": "19:06:08", "acc": 0.51, "entropy": 0.9871, "ret": -0.109751, "capital": 8902.49, "trades": 3284, "positions": 2, "exposure": 0.02, "predictions": 14599}
data\v2.jsonl:1247:{"tick": 6160, "t": "19:11:10", "acc": 0.52, "entropy": 0.9859, "ret": -0.109361, "capital": 8906.39, "trades": 3285, "positions": 3, "exposure": 0.03, "predictions": 14619}
data\v2.jsonl:1248:{"tick": 6165, "t": "19:16:12", "acc": 0.52, "entropy": 0.9855, "ret": -0.109664, "capital": 8903.36, "trades": 3290, "positions": 2, "exposure": 0.02, "predictions": 14639}
data\v2.jsonl:1249:{"tick": 6170, "t": "19:21:14", "acc": 0.515, "entropy": 0.9849, "ret": -0.110062, "capital": 8899.38, "trades": 3294, "positions": 1, "exposure": 0.01, "predictions": 14659}
data\v2.jsonl:1250:{"tick": 6175, "t": "19:26:16", "acc": 0.51, "entropy": 0.9888, "ret": -0.110124, "capital": 8898.76, "trades": 3296, "positions": 2, "exposure": 0.02, "predictions": 14679}
data\v2.jsonl:1251:{"tick": 6180, "t": "19:31:18", "acc": 0.505, "entropy": 0.9864, "ret": -0.110027, "capital": 8899.73, "trades": 3298, "positions": 3, "exposure": 0.03, "predictions": 14699}
data\v2.jsonl:1252:{"tick": 6185, "t": "19:36:20", "acc": 0.49, "entropy": 0.9867, "ret": -0.111066, "capital": 8889.34, "trades": 3305, "positions": 2, "exposure": 0.02, "predictions": 14719}
data\v2.jsonl:1253:{"tick": 6190, "t": "19:41:22", "acc": 0.475, "entropy": 0.9882, "ret": -0.111107, "capital": 8888.93, "trades": 3308, "positions": 1, "exposure": 0.01, "predictions": 14739}
data\v2.jsonl:1254:{"tick": 6195, "t": "19:46:25", "acc": 0.465, "entropy": 0.988, "ret": -0.11112, "capital": 8888.8, "trades": 3310, "positions": 2, "exposure": 0.02, "predictions": 14759}
data\v2.jsonl:1255:{"tick": 6200, "t": "19:51:27", "acc": 0.455, "entropy": 0.9887, "ret": -0.111179, "capital": 8888.21, "trades": 3311, "positions": 3, "exposure": 0.03, "predictions": 14779}
data\v2.jsonl:1256:{"tick": 6205, "t": "19:56:29", "acc": 0.465, "entropy": 0.9891, "ret": -0.111876, "capital": 8881.24, "trades": 3314, "positions": 3, "exposure": 0.03, "predictions": 14799}
data\v2.jsonl:1257:{"tick": 6210, "t": "20:01:31", "acc": 0.45, "entropy": 0.9899, "ret": -0.11192, "capital": 8880.8, "trades": 3318, "positions": 3, "exposure": 0.03, "predictions": 14819}
data\v2.jsonl:1258:{"tick": 6215, "t": "20:06:34", "acc": 0.465, "entropy": 0.9887, "ret": -0.111867, "capital": 8881.33, "trades": 3323, "positions": 3, "exposure": 0.03, "predictions": 14839}
data\v2.jsonl:1259:{"tick": 6220, "t": "20:11:36", "acc": 0.475, "entropy": 0.9882, "ret": -0.111437, "capital": 8885.63, "trades": 3326, "positions": 3, "exposure": 0.03, "predictions": 14859}
data\v2.jsonl:1260:{"tick": 6225, "t": "20:16:38", "acc": 0.47, "entropy": 0.9837, "ret": -0.111564, "capital": 8884.36, "trades": 3331, "positions": 3, "exposure": 0.03, "predictions": 14879}
data\v2.jsonl:1261:{"tick": 6230, "t": "20:21:40", "acc": 0.485, "entropy": 0.9795, "ret": -0.111617, "capital": 8883.83, "trades": 3334, "positions": 1, "exposure": 0.01, "predictions": 14899}
data\v2.jsonl:1262:{"tick": 6235, "t": "20:26:41", "acc": 0.49, "entropy": 0.9823, "ret": -0.111885, "capital": 8881.15, "trades": 3337, "positions": 3, "exposure": 0.03, "predictions": 14919}
data\v2.jsonl:1263:{"tick": 6240, "t": "20:31:43", "acc": 0.485, "entropy": 0.9871, "ret": -0.111999, "capital": 8880.01, "trades": 3340, "positions": 3, "exposure": 0.03, "predictions": 14939}
data\v2.jsonl:1264:{"tick": 6245, "t": "20:36:46", "acc": 0.505, "entropy": 0.9849, "ret": -0.111987, "capital": 8880.13, "trades": 3342, "positions": 3, "exposure": 0.03, "predictions": 14959}
data\v2.jsonl:1265:{"tick": 6250, "t": "20:41:48", "acc": 0.52, "entropy": 0.9874, "ret": -0.112224, "capital": 8877.76, "trades": 3346, "positions": 2, "exposure": 0.02, "predictions": 14979}
data\v2.jsonl:1266:{"tick": 6255, "t": "20:46:50", "acc": 0.5, "entropy": 0.9884, "ret": -0.112317, "capital": 8876.83, "trades": 3350, "positions": 3, "exposure": 0.03, "predictions": 14999}
data\v2.jsonl:1267:{"tick": 6260, "t": "20:51:52", "acc": 0.51, "entropy": 0.9835, "ret": -0.112379, "capital": 8876.21, "trades": 3355, "positions": 1, "exposure": 0.01, "predictions": 15019}
data\v2.jsonl:1268:{"tick": 6265, "t": "20:56:53", "acc": 0.51, "entropy": 0.9847, "ret": -0.112519, "capital": 8874.81, "trades": 3358, "positions": 2, "exposure": 0.02, "predictions": 15039}
data\v2.jsonl:1269:{"tick": 6270, "t": "21:01:55", "acc": 0.495, "entropy": 0.9873, "ret": -0.112934, "capital": 8870.66, "trades": 3361, "positions": 4, "exposure": 0.04, "predictions": 15059}
data\v2.jsonl:1270:{"tick": 6275, "t": "21:06:58", "acc": 0.51, "entropy": 0.9899, "ret": -0.113073, "capital": 8869.27, "trades": 3365, "positions": 3, "exposure": 0.03, "predictions": 15079}
data\v2.jsonl:1271:{"tick": 6280, "t": "21:12:00", "acc": 0.505, "entropy": 0.9874, "ret": -0.1131, "capital": 8869.0, "trades": 3370, "positions": 1, "exposure": 0.01, "predictions": 15099}
data\v2.jsonl:1272:{"tick": 6285, "t": "21:17:02", "acc": 0.515, "entropy": 0.9881, "ret": -0.113102, "capital": 8868.98, "trades": 3374, "positions": 2, "exposure": 0.02, "predictions": 15119}
data\v2.jsonl:1273:{"tick": 6290, "t": "21:22:04", "acc": 0.51, "entropy": 0.9895, "ret": -0.113691, "capital": 8863.09, "trades": 3377, "positions": 1, "exposure": 0.01, "predictions": 15139}
data\v2.jsonl:1274:{"tick": 6295, "t": "21:27:05", "acc": 0.505, "entropy": 0.9895, "ret": -0.114189, "capital": 8858.11, "trades": 3379, "positions": 4, "exposure": 0.04, "predictions": 15159}
data\v2.jsonl:1275:{"tick": 6300, "t": "21:32:07", "acc": 0.485, "entropy": 0.9908, "ret": -0.114675, "capital": 8853.25, "trades": 3382, "positions": 3, "exposure": 0.03, "predictions": 15179}
data\v2.jsonl:1276:{"tick": 6305, "t": "21:37:10", "acc": 0.51, "entropy": 0.9919, "ret": -0.114576, "capital": 8854.24, "trades": 3385, "positions": 3, "exposure": 0.03, "predictions": 15199}
data\v2.jsonl:1277:{"tick": 6310, "t": "21:42:12", "acc": 0.5, "entropy": 0.992, "ret": -0.114705, "capital": 8852.95, "trades": 3390, "positions": 1, "exposure": 0.01, "predictions": 15219}
data\v2.jsonl:1278:{"tick": 6315, "t": "21:47:14", "acc": 0.49, "entropy": 0.9908, "ret": -0.113913, "capital": 8860.87, "trades": 3394, "positions": 4, "exposure": 0.04, "predictions": 15238}
data\v2.jsonl:1279:{"tick": 6320, "t": "21:52:15", "acc": 0.48, "entropy": 0.9891, "ret": -0.113492, "capital": 8865.08, "trades": 3399, "positions": 2, "exposure": 0.02, "predictions": 15258}
data\v2.jsonl:1280:{"tick": 6325, "t": "21:57:17", "acc": 0.485, "entropy": 0.9857, "ret": -0.114209, "capital": 8857.91, "trades": 3403, "positions": 3, "exposure": 0.03, "predictions": 15278}
data\v2.jsonl:1281:{"tick": 6330, "t": "22:02:19", "acc": 0.47, "entropy": 0.9894, "ret": -0.114158, "capital": 8858.42, "trades": 3405, "positions": 4, "exposure": 0.04, "predictions": 15298}
data\v2.jsonl:1282:{"tick": 6335, "t": "22:07:22", "acc": 0.445, "entropy": 0.9862, "ret": -0.114437, "capital": 8855.63, "trades": 3410, "positions": 2, "exposure": 0.02, "predictions": 15318}
data\v2.jsonl:1283:{"tick": 6340, "t": "22:12:24", "acc": 0.47, "entropy": 0.9871, "ret": -0.114531, "capital": 8854.69, "trades": 3412, "positions": 2, "exposure": 0.02, "predictions": 15338}
data\v2.jsonl:1284:{"tick": 6345, "t": "22:17:26", "acc": 0.48, "entropy": 0.9879, "ret": -0.114425, "capital": 8855.75, "trades": 3415, "positions": 3, "exposure": 0.03, "predictions": 15358}
data\v2.jsonl:1285:{"tick": 6350, "t": "22:22:28", "acc": 0.49, "entropy": 0.9895, "ret": -0.114217, "capital": 8857.83, "trades": 3420, "positions": 1, "exposure": 0.01, "predictions": 15378}
data\v2.jsonl:1286:{"tick": 6355, "t": "22:27:31", "acc": 0.47, "entropy": 0.987, "ret": -0.114242, "capital": 8857.58, "trades": 3422, "positions": 2, "exposure": 0.02, "predictions": 15398}
data\v2.jsonl:1287:{"tick": 6360, "t": "22:32:33", "acc": 0.47, "entropy": 0.9881, "ret": -0.11433, "capital": 8856.7, "trades": 3425, "positions": 2, "exposure": 0.02, "predictions": 15418}
data\v2.jsonl:1288:{"tick": 6365, "t": "22:37:35", "acc": 0.485, "entropy": 0.9888, "ret": -0.113844, "capital": 8861.56, "trades": 3431, "positions": 1, "exposure": 0.01, "predictions": 15438}
data\v2.jsonl:1289:{"tick": 6370, "t": "22:42:37", "acc": 0.49, "entropy": 0.9911, "ret": -0.113999, "capital": 8860.01, "trades": 3433, "positions": 2, "exposure": 0.02, "predictions": 15458}
data\v2.jsonl:1290:{"tick": 6375, "t": "22:47:39", "acc": 0.485, "entropy": 0.9915, "ret": -0.113826, "capital": 8861.74, "trades": 3435, "positions": 4, "exposure": 0.04, "predictions": 15478}
data\v2.jsonl:1291:{"tick": 6380, "t": "22:52:41", "acc": 0.52, "entropy": 0.9909, "ret": -0.11316, "capital": 8868.4, "trades": 3439, "positions": 1, "exposure": 0.01, "predictions": 15498}
data\v2.jsonl:1292:{"tick": 6385, "t": "22:57:43", "acc": 0.53, "entropy": 0.9894, "ret": -0.113247, "capital": 8867.53, "trades": 3443, "positions": 2, "exposure": 0.02, "predictions": 15518}
data\v2.jsonl:1293:{"tick": 6390, "t": "23:02:45", "acc": 0.5, "entropy": 0.9886, "ret": -0.113434, "capital": 8865.66, "trades": 3447, "positions": 2, "exposure": 0.02, "predictions": 15538}
data\v2.jsonl:1294:{"tick": 6395, "t": "23:07:47", "acc": 0.505, "entropy": 0.9865, "ret": -0.113134, "capital": 8868.66, "trades": 3451, "positions": 3, "exposure": 0.03, "predictions": 15558}
data\v2.jsonl:1295:{"tick": 6400, "t": "23:12:49", "acc": 0.535, "entropy": 0.9882, "ret": -0.11314, "capital": 8868.6, "trades": 3456, "positions": 2, "exposure": 0.02, "predictions": 15578}
data\v2.jsonl:1296:{"tick": 6405, "t": "23:17:51", "acc": 0.545, "entropy": 0.9887, "ret": -0.113021, "capital": 8869.79, "trades": 3460, "positions": 3, "exposure": 0.03, "predictions": 15598}
data\v2.jsonl:1297:{"tick": 6410, "t": "23:22:53", "acc": 0.54, "entropy": 0.9888, "ret": -0.11349, "capital": 8865.1, "trades": 3464, "positions": 3, "exposure": 0.03, "predictions": 15618}
data\v2.jsonl:1298:{"tick": 6415, "t": "23:27:55", "acc": 0.525, "entropy": 0.9906, "ret": -0.113569, "capital": 8864.31, "trades": 3468, "positions": 2, "exposure": 0.02, "predictions": 15638}
data\v2.jsonl:1299:{"tick": 6420, "t": "23:32:57", "acc": 0.525, "entropy": 0.9912, "ret": -0.113613, "capital": 8863.87, "trades": 3470, "positions": 4, "exposure": 0.04, "predictions": 15658}
data\v2.jsonl:1300:{"tick": 6425, "t": "23:38:00", "acc": 0.545, "entropy": 0.988, "ret": -0.113362, "capital": 8866.38, "trades": 3475, "positions": 2, "exposure": 0.02, "predictions": 15678}
data\v2.jsonl:1301:{"tick": 6430, "t": "23:43:01", "acc": 0.535, "entropy": 0.9872, "ret": -0.113412, "capital": 8865.88, "trades": 3478, "positions": 2, "exposure": 0.02, "predictions": 15698}
data\v2.jsonl:1302:{"tick": 6435, "t": "23:48:03", "acc": 0.54, "entropy": 0.9858, "ret": -0.113592, "capital": 8864.08, "trades": 3483, "positions": 2, "exposure": 0.02, "predictions": 15718}
data\v2.jsonl:1303:{"tick": 6440, "t": "23:53:05", "acc": 0.555, "entropy": 0.985, "ret": -0.113611, "capital": 8863.89, "trades": 3484, "positions": 2, "exposure": 0.02, "predictions": 15738}
data\v2.jsonl:1304:{"tick": 6445, "t": "23:58:08", "acc": 0.545, "entropy": 0.9858, "ret": -0.113435, "capital": 8865.65, "trades": 3489, "positions": 3, "exposure": 0.03, "predictions": 15758}
data\v2.jsonl:1305:{"tick": 6450, "t": "00:03:10", "acc": 0.53, "entropy": 0.9887, "ret": -0.113515, "capital": 8864.85, "trades": 3494, "positions": 1, "exposure": 0.01, "predictions": 15777}
data\v2.jsonl:1306:{"tick": 6455, "t": "00:08:12", "acc": 0.495, "entropy": 0.9916, "ret": -0.113643, "capital": 8863.57, "trades": 3497, "positions": 3, "exposure": 0.03, "predictions": 15797}
data\v2.jsonl:1307:{"tick": 6460, "t": "00:13:14", "acc": 0.51, "entropy": 0.9903, "ret": -0.113432, "capital": 8865.68, "trades": 3503, "positions": 2, "exposure": 0.02, "predictions": 15817}
data\v2.jsonl:1308:{"tick": 6465, "t": "00:18:16", "acc": 0.525, "entropy": 0.9872, "ret": -0.112959, "capital": 8870.41, "trades": 3505, "positions": 4, "exposure": 0.04, "predictions": 15836}
data\v2.jsonl:1309:{"tick": 6470, "t": "00:23:18", "acc": 0.54, "entropy": 0.9872, "ret": -0.111238, "capital": 8887.62, "trades": 3509, "positions": 3, "exposure": 0.03, "predictions": 15856}
data\v2.jsonl:1310:{"tick": 6475, "t": "00:28:20", "acc": 0.51, "entropy": 0.9868, "ret": -0.111831, "capital": 8881.69, "trades": 3514, "positions": 1, "exposure": 0.01, "predictions": 15876}
data\v2.jsonl:1311:{"tick": 6480, "t": "00:33:22", "acc": 0.5, "entropy": 0.985, "ret": -0.111824, "capital": 8881.76, "trades": 3516, "positions": 1, "exposure": 0.01, "predictions": 15896}
data\v2.jsonl:1312:{"tick": 6485, "t": "00:38:24", "acc": 0.475, "entropy": 0.982, "ret": -0.112152, "capital": 8878.48, "trades": 3521, "positions": 0, "exposure": 0, "predictions": 15916}
data\v2.jsonl:1313:{"tick": 6490, "t": "00:43:26", "acc": 0.45, "entropy": 0.9818, "ret": -0.112174, "capital": 8878.26, "trades": 3523, "positions": 1, "exposure": 0.01, "predictions": 15936}
data\v2.jsonl:1314:{"tick": 6495, "t": "00:48:29", "acc": 0.455, "entropy": 0.9862, "ret": -0.112024, "capital": 8879.76, "trades": 3529, "positions": 1, "exposure": 0.01, "predictions": 15956}
data\v2.jsonl:1315:{"tick": 6500, "t": "00:53:31", "acc": 0.44, "entropy": 0.9856, "ret": -0.112053, "capital": 8879.47, "trades": 3531, "positions": 2, "exposure": 0.02, "predictions": 15976}
data\v2.jsonl:1316:{"tick": 6505, "t": "00:58:33", "acc": 0.435, "entropy": 0.9822, "ret": -0.111889, "capital": 8881.11, "trades": 3532, "positions": 2, "exposure": 0.02, "predictions": 15996}
data\v2.jsonl:1317:{"tick": 6510, "t": "01:03:35", "acc": 0.455, "entropy": 0.9855, "ret": -0.11167, "capital": 8883.3, "trades": 3538, "positions": 2, "exposure": 0.02, "predictions": 16016}
data\v2.jsonl:1318:{"tick": 6515, "t": "01:08:37", "acc": 0.455, "entropy": 0.9845, "ret": -0.111324, "capital": 8886.76, "trades": 3541, "positions": 1, "exposure": 0.01, "predictions": 16036}
data\v2.jsonl:1319:{"tick": 6520, "t": "01:13:39", "acc": 0.445, "entropy": 0.9839, "ret": -0.111276, "capital": 8887.24, "trades": 3542, "positions": 2, "exposure": 0.02, "predictions": 16056}
data\v2.jsonl:1320:{"tick": 6525, "t": "01:18:41", "acc": 0.455, "entropy": 0.9821, "ret": -0.111108, "capital": 8888.92, "trades": 3545, "positions": 4, "exposure": 0.0478, "predictions": 16076}
data\v2.jsonl:1321:{"tick": 6530, "t": "01:23:43", "acc": 0.465, "entropy": 0.9795, "ret": -0.110965, "capital": 8890.35, "trades": 3547, "positions": 3, "exposure": 0.0381, "predictions": 16096}
data\v2.jsonl:1322:{"tick": 6535, "t": "01:28:45", "acc": 0.485, "entropy": 0.9822, "ret": -0.110546, "capital": 8894.54, "trades": 3550, "positions": 2, "exposure": 0.0239, "predictions": 16116}
data\v2.jsonl:1323:{"tick": 6540, "t": "01:33:47", "acc": 0.51, "entropy": 0.984, "ret": -0.110745, "capital": 8892.55, "trades": 3552, "positions": 4, "exposure": 0.075, "predictions": 16136}
data\v2.jsonl:1324:{"tick": 6545, "t": "01:38:50", "acc": 0.49, "entropy": 0.9822, "ret": -0.109939, "capital": 8900.61, "trades": 3557, "positions": 1, "exposure": 0.0162, "predictions": 16156}
data\v2.jsonl:1325:{"tick": 6550, "t": "01:43:52", "acc": 0.515, "entropy": 0.9829, "ret": -0.110874, "capital": 8891.26, "trades": 3559, "positions": 3, "exposure": 0.0391, "predictions": 16176}
data\v2.jsonl:1326:{"tick": 6555, "t": "01:48:54", "acc": 0.535, "entropy": 0.985, "ret": -0.110651, "capital": 8893.49, "trades": 3562, "positions": 3, "exposure": 0.059, "predictions": 16196}
data\v2.jsonl:1327:{"tick": 6560, "t": "01:53:56", "acc": 0.515, "entropy": 0.9832, "ret": -0.111156, "capital": 8888.44, "trades": 3565, "positions": 3, "exposure": 0.0605, "predictions": 16216}
data\v2.jsonl:1328:{"tick": 6565, "t": "01:58:58", "acc": 0.495, "entropy": 0.9786, "ret": -0.110621, "capital": 8893.79, "trades": 3570, "positions": 2, "exposure": 0.0265, "predictions": 16236}
data\v2.jsonl:1329:{"tick": 6570, "t": "02:04:01", "acc": 0.485, "entropy": 0.9784, "ret": -0.111016, "capital": 8889.84, "trades": 3574, "positions": 3, "exposure": 0.043, "predictions": 16256}
data\v2.jsonl:1330:{"tick": 6575, "t": "02:09:03", "acc": 0.5, "entropy": 0.9783, "ret": -0.111066, "capital": 8889.34, "trades": 3578, "positions": 0, "exposure": 0, "predictions": 16276}
data\v2.jsonl:1331:{"tick": 6580, "t": "02:14:05", "acc": 0.475, "entropy": 0.978, "ret": -0.111053, "capital": 8889.47, "trades": 3581, "positions": 1, "exposure": 0.0369, "predictions": 16296}
data\v2.jsonl:1332:{"tick": 6585, "t": "02:19:07", "acc": 0.475, "entropy": 0.9832, "ret": -0.111039, "capital": 8889.61, "trades": 3583, "positions": 2, "exposure": 0.0605, "predictions": 16316}
data\v2.jsonl:1333:{"tick": 6590, "t": "02:24:09", "acc": 0.47, "entropy": 0.9868, "ret": -0.111, "capital": 8890.0, "trades": 3585, "positions": 2, "exposure": 0.0606, "predictions": 16336}
data\v2.jsonl:1334:{"tick": 6595, "t": "02:29:11", "acc": 0.475, "entropy": 0.9849, "ret": -0.116849, "capital": 8831.51, "trades": 3591, "positions": 1, "exposure": 0.01, "predictions": 16356}
data\v2.jsonl:1335:{"tick": 6600, "t": "02:34:13", "acc": 0.475, "entropy": 0.9844, "ret": -0.116661, "capital": 8833.39, "trades": 3597, "positions": 1, "exposure": 0.0114, "predictions": 16376}
data\v2.jsonl:1336:{"tick": 6605, "t": "02:39:15", "acc": 0.46, "entropy": 0.9875, "ret": -0.11631, "capital": 8836.9, "trades": 3600, "positions": 2, "exposure": 0.02, "predictions": 16396}
data\v2.jsonl:1337:{"tick": 6610, "t": "02:44:17", "acc": 0.46, "entropy": 0.9843, "ret": -0.115388, "capital": 8846.12, "trades": 3604, "positions": 4, "exposure": 0.0669, "predictions": 16416}
data\v2.jsonl:1338:{"tick": 6615, "t": "02:49:19", "acc": 0.48, "entropy": 0.9821, "ret": -0.116527, "capital": 8834.73, "trades": 3605, "positions": 3, "exposure": 0.0569, "predictions": 16436}
data\v2.jsonl:1339:{"tick": 6620, "t": "02:54:21", "acc": 0.48, "entropy": 0.9832, "ret": -0.119629, "capital": 8803.71, "trades": 3608, "positions": 3, "exposure": 0.03, "predictions": 16456}
data\v2.jsonl:1340:{"tick": 6625, "t": "02:59:23", "acc": 0.475, "entropy": 0.9845, "ret": -0.119812, "capital": 8801.88, "trades": 3612, "positions": 2, "exposure": 0.02, "predictions": 16476}
data\v2.jsonl:1341:{"tick": 6630, "t": "03:04:25", "acc": 0.475, "entropy": 0.9831, "ret": -0.119617, "capital": 8803.83, "trades": 3614, "positions": 4, "exposure": 0.04, "predictions": 16496}
data\v2.jsonl:1342:{"tick": 6635, "t": "03:09:28", "acc": 0.49, "entropy": 0.9806, "ret": -0.120248, "capital": 8797.52, "trades": 3618, "positions": 3, "exposure": 0.03, "predictions": 16516}
data\v2.jsonl:1343:{"tick": 6640, "t": "03:14:30", "acc": 0.51, "entropy": 0.9846, "ret": -0.120059, "capital": 8799.41, "trades": 3622, "positions": 1, "exposure": 0.01, "predictions": 16536}
data\v2.jsonl:1344:{"tick": 6645, "t": "03:19:32", "acc": 0.505, "entropy": 0.985, "ret": -0.118921, "capital": 8810.79, "trades": 3626, "positions": 3, "exposure": 0.03, "predictions": 16556}
data\v2.jsonl:1345:{"tick": 6650, "t": "03:24:34", "acc": 0.505, "entropy": 0.9848, "ret": -0.119211, "capital": 8807.89, "trades": 3630, "positions": 1, "exposure": 0.01, "predictions": 16576}
data\v2.jsonl:1346:{"tick": 6655, "t": "03:29:36", "acc": 0.525, "entropy": 0.9868, "ret": -0.118823, "capital": 8811.77, "trades": 3632, "positions": 2, "exposure": 0.02, "predictions": 16596}
data\v2.jsonl:1347:{"tick": 6660, "t": "03:34:38", "acc": 0.53, "entropy": 0.9846, "ret": -0.118944, "capital": 8810.56, "trades": 3634, "positions": 2, "exposure": 0.02, "predictions": 16616}
data\v2.jsonl:1348:{"tick": 6665, "t": "03:39:44", "acc": 0.51, "entropy": 0.9842, "ret": -0.119013, "capital": 8809.87, "trades": 3636, "positions": 2, "exposure": 0.02, "predictions": 16636}
data\v2.jsonl:1349:{"tick": 6670, "t": "03:44:47", "acc": 0.52, "entropy": 0.9853, "ret": -0.118952, "capital": 8810.48, "trades": 3638, "positions": 2, "exposure": 0.02, "predictions": 16656}
data\v2.jsonl:1350:{"tick": 6675, "t": "03:49:49", "acc": 0.495, "entropy": 0.9842, "ret": -0.119348, "capital": 8806.52, "trades": 3641, "positions": 2, "exposure": 0.02, "predictions": 16676}
data\v2.jsonl:1351:{"tick": 6680, "t": "03:54:51", "acc": 0.49, "entropy": 0.9848, "ret": -0.119289, "capital": 8807.11, "trades": 3643, "positions": 3, "exposure": 0.03, "predictions": 16696}
data\v2.jsonl:1352:{"tick": 6685, "t": "03:59:53", "acc": 0.485, "entropy": 0.9832, "ret": -0.119636, "capital": 8803.64, "trades": 3648, "positions": 1, "exposure": 0.01, "predictions": 16716}
data\v2.jsonl:1353:{"tick": 6690, "t": "04:04:55", "acc": 0.47, "entropy": 0.9872, "ret": -0.11967, "capital": 8803.3, "trades": 3651, "positions": 3, "exposure": 0.03, "predictions": 16736}
data\v2.jsonl:1354:{"tick": 6695, "t": "04:09:59", "acc": 0.48, "entropy": 0.988, "ret": -0.119456, "capital": 8805.44, "trades": 3654, "positions": 2, "exposure": 0.02, "predictions": 16756}
data\v2.jsonl:1355:{"tick": 6700, "t": "04:15:01", "acc": 0.45, "entropy": 0.9838, "ret": -0.120153, "capital": 8798.47, "trades": 3657, "positions": 2, "exposure": 0.02, "predictions": 16776}
data\v2.jsonl:1356:{"tick": 6705, "t": "04:20:04", "acc": 0.45, "entropy": 0.9861, "ret": -0.120737, "capital": 8792.63, "trades": 3660, "positions": 3, "exposure": 0.03, "predictions": 16796}
data\v2.jsonl:1357:{"tick": 6710, "t": "04:25:06", "acc": 0.45, "entropy": 0.9843, "ret": -0.121056, "capital": 8789.44, "trades": 3662, "positions": 2, "exposure": 0.02, "predictions": 16816}
data\v2.jsonl:1358:{"tick": 6715, "t": "04:30:09", "acc": 0.46, "entropy": 0.9828, "ret": -0.121147, "capital": 8788.53, "trades": 3665, "positions": 2, "exposure": 0.02, "predictions": 16836}
data\v2.jsonl:1359:{"tick": 6720, "t": "04:35:11", "acc": 0.465, "entropy": 0.9832, "ret": -0.120441, "capital": 8795.59, "trades": 3669, "positions": 2, "exposure": 0.02, "predictions": 16856}
data\v2.jsonl:1360:{"tick": 6725, "t": "04:40:14", "acc": 0.485, "entropy": 0.9845, "ret": -0.120126, "capital": 8798.74, "trades": 3673, "positions": 1, "exposure": 0.01, "predictions": 16876}
data\v2.jsonl:1361:{"tick": 6730, "t": "04:45:17", "acc": 0.475, "entropy": 0.9838, "ret": -0.12115, "capital": 8788.5, "trades": 3679, "positions": 1, "exposure": 0.01, "predictions": 16896}
data\v2.jsonl:1362:{"tick": 6735, "t": "04:50:19", "acc": 0.485, "entropy": 0.9822, "ret": -0.121084, "capital": 8789.16, "trades": 3681, "positions": 2, "exposure": 0.02, "predictions": 16916}
data\v2.jsonl:1363:{"tick": 6740, "t": "04:55:21", "acc": 0.495, "entropy": 0.9783, "ret": -0.120386, "capital": 8796.14, "trades": 3683, "positions": 3, "exposure": 0.03, "predictions": 16936}
data\v2.jsonl:1364:{"tick": 6745, "t": "05:00:23", "acc": 0.49, "entropy": 0.9874, "ret": -0.120577, "capital": 8794.23, "trades": 3687, "positions": 1, "exposure": 0.01, "predictions": 16956}
data\v2.jsonl:1365:{"tick": 6750, "t": "05:05:24", "acc": 0.515, "entropy": 0.9842, "ret": -0.122083, "capital": 8779.17, "trades": 3692, "positions": 2, "exposure": 0.02, "predictions": 16976}
data\v2.jsonl:1366:{"tick": 6755, "t": "05:10:27", "acc": 0.535, "entropy": 0.9859, "ret": -0.121942, "capital": 8780.58, "trades": 3694, "positions": 1, "exposure": 0.01, "predictions": 16996}
data\v2.jsonl:1367:{"tick": 6760, "t": "05:15:29", "acc": 0.525, "entropy": 0.9818, "ret": -0.122189, "capital": 8778.11, "trades": 3696, "positions": 1, "exposure": 0.01, "predictions": 17016}
data\v2.jsonl:1368:{"tick": 6765, "t": "05:20:31", "acc": 0.53, "entropy": 0.9813, "ret": -0.121901, "capital": 8780.99, "trades": 3699, "positions": 2, "exposure": 0.02, "predictions": 17036}
data\v2.jsonl:1369:{"tick": 6770, "t": "05:25:33", "acc": 0.54, "entropy": 0.989, "ret": -0.122044, "capital": 8779.56, "trades": 3702, "positions": 1, "exposure": 0.01, "predictions": 17056}
data\v2.jsonl:1370:{"tick": 6775, "t": "05:30:36", "acc": 0.55, "entropy": 0.9878, "ret": -0.122022, "capital": 8779.78, "trades": 3705, "positions": 2, "exposure": 0.02, "predictions": 17076}
data\v2.jsonl:1371:{"tick": 6780, "t": "05:35:38", "acc": 0.58, "entropy": 0.9898, "ret": -0.121951, "capital": 8780.49, "trades": 3709, "positions": 3, "exposure": 0.03, "predictions": 17096}
data\v2.jsonl:1372:{"tick": 6785, "t": "05:41:02", "acc": 0.57, "entropy": 0.9885, "ret": -0.122309, "capital": 8776.91, "trades": 3712, "positions": 2, "exposure": 0.02, "predictions": 17112}
data\v2.jsonl:1373:{"tick": 6790, "t": "05:46:06", "acc": 0.52, "entropy": 0.9893, "ret": -0.12239, "capital": 8776.1, "trades": 3714, "positions": 2, "exposure": 0.02, "predictions": 17132}
data\v2.jsonl:1374:{"tick": 6795, "t": "05:51:09", "acc": 0.53, "entropy": 0.9894, "ret": -0.121918, "capital": 8780.82, "trades": 3718, "positions": 2, "exposure": 0.02, "predictions": 17152}
data\v2.jsonl:1375:{"tick": 6800, "t": "05:56:11", "acc": 0.525, "entropy": 0.9887, "ret": -0.122301, "capital": 8776.99, "trades": 3721, "positions": 3, "exposure": 0.03, "predictions": 17172}
data\v2.jsonl:1376:{"tick": 6805, "t": "06:01:13", "acc": 0.505, "entropy": 0.9896, "ret": -0.122576, "capital": 8774.24, "trades": 3724, "positions": 1, "exposure": 0.01, "predictions": 17191}
data\v2.jsonl:1377:{"tick": 6810, "t": "06:06:15", "acc": 0.52, "entropy": 0.9878, "ret": -0.12251, "capital": 8774.9, "trades": 3727, "positions": 4, "exposure": 0.04, "predictions": 17211}
data\v2.jsonl:1378:{"tick": 6815, "t": "06:11:18", "acc": 0.51, "entropy": 0.9881, "ret": -0.122887, "capital": 8771.13, "trades": 3733, "positions": 2, "exposure": 0.02, "predictions": 17231}
data\v2.jsonl:1379:{"tick": 6820, "t": "06:16:20", "acc": 0.46, "entropy": 0.9877, "ret": -0.123933, "capital": 8760.67, "trades": 3737, "positions": 2, "exposure": 0.02, "predictions": 17251}
data\v2.jsonl:1380:{"tick": 6825, "t": "06:21:22", "acc": 0.44, "entropy": 0.9893, "ret": -0.12496, "capital": 8750.4, "trades": 3742, "positions": 1, "exposure": 0.01, "predictions": 17271}
data\v2.jsonl:1381:{"tick": 6830, "t": "06:26:24", "acc": 0.415, "entropy": 0.9878, "ret": -0.124749, "capital": 8752.51, "trades": 3745, "positions": 1, "exposure": 0.01, "predictions": 17291}
data\v2.jsonl:1382:{"tick": 6835, "t": "06:31:26", "acc": 0.43, "entropy": 0.9883, "ret": -0.124579, "capital": 8754.21, "trades": 3748, "positions": 3, "exposure": 0.03, "predictions": 17311}
data\v2.jsonl:1383:{"tick": 6840, "t": "06:36:28", "acc": 0.485, "entropy": 0.9891, "ret": -0.124546, "capital": 8754.54, "trades": 3749, "positions": 4, "exposure": 0.04, "predictions": 17331}
data\v2.jsonl:1384:{"tick": 6845, "t": "06:41:30", "acc": 0.47, "entropy": 0.9886, "ret": -0.124259, "capital": 8757.41, "trades": 3753, "positions": 3, "exposure": 0.03, "predictions": 17351}
data\v2.jsonl:1385:{"tick": 6850, "t": "06:46:32", "acc": 0.48, "entropy": 0.9883, "ret": -0.124153, "capital": 8758.47, "trades": 3756, "positions": 3, "exposure": 0.03, "predictions": 17371}
data\v2.jsonl:1386:{"tick": 6855, "t": "06:51:34", "acc": 0.49, "entropy": 0.9879, "ret": -0.124281, "capital": 8757.19, "trades": 3759, "positions": 3, "exposure": 0.03, "predictions": 17391}
data\v2.jsonl:1387:{"tick": 6860, "t": "06:56:36", "acc": 0.485, "entropy": 0.9866, "ret": -0.123958, "capital": 8760.42, "trades": 3762, "positions": 3, "exposure": 0.03, "predictions": 17411}
data\v2.jsonl:1388:{"tick": 6865, "t": "07:01:38", "acc": 0.49, "entropy": 0.9874, "ret": -0.123943, "capital": 8760.57, "trades": 3766, "positions": 2, "exposure": 0.02, "predictions": 17431}
data\v2.jsonl:1389:{"tick": 6870, "t": "07:06:41", "acc": 0.505, "entropy": 0.9902, "ret": -0.12412, "capital": 8758.8, "trades": 3769, "positions": 2, "exposure": 0.02, "predictions": 17451}
data\v2.jsonl:1390:{"tick": 6875, "t": "07:11:43", "acc": 0.5, "entropy": 0.9897, "ret": -0.124231, "capital": 8757.69, "trades": 3770, "positions": 3, "exposure": 0.03, "predictions": 17471}
data\v2.jsonl:1391:{"tick": 6880, "t": "07:16:45", "acc": 0.515, "entropy": 0.9901, "ret": -0.125025, "capital": 8749.75, "trades": 3774, "positions": 1, "exposure": 0.01, "predictions": 17491}
data\v2.jsonl:1392:{"tick": 6885, "t": "07:21:47", "acc": 0.505, "entropy": 0.9903, "ret": -0.126333, "capital": 8736.67, "trades": 3776, "positions": 3, "exposure": 0.03, "predictions": 17511}
data\v2.jsonl:1393:{"tick": 6890, "t": "07:26:49", "acc": 0.475, "entropy": 0.9878, "ret": -0.128434, "capital": 8715.66, "trades": 3781, "positions": 3, "exposure": 0.03, "predictions": 17531}
data\v2.jsonl:1394:{"tick": 6895, "t": "07:31:52", "acc": 0.495, "entropy": 0.9892, "ret": -0.128966, "capital": 8710.34, "trades": 3789, "positions": 3, "exposure": 0.03, "predictions": 17551}
data\v2.jsonl:1395:{"tick": 6900, "t": "07:36:54", "acc": 0.495, "entropy": 0.9841, "ret": -0.129824, "capital": 8701.76, "trades": 3793, "positions": 2, "exposure": 0.02, "predictions": 17571}
data\v2.jsonl:1396:{"tick": 6905, "t": "07:41:56", "acc": 0.465, "entropy": 0.9862, "ret": -0.129729, "capital": 8702.71, "trades": 3798, "positions": 2, "exposure": 0.02, "predictions": 17591}
data\v2.jsonl:1397:{"tick": 6910, "t": "07:46:59", "acc": 0.475, "entropy": 0.9843, "ret": -0.129671, "capital": 8703.29, "trades": 3801, "positions": 4, "exposure": 0.04, "predictions": 17611}
data\v2.jsonl:1398:{"tick": 6915, "t": "07:52:01", "acc": 0.47, "entropy": 0.9864, "ret": -0.129571, "capital": 8704.29, "trades": 3805, "positions": 2, "exposure": 0.02, "predictions": 17631}
data\v2.jsonl:1399:{"tick": 6920, "t": "07:57:03", "acc": 0.5, "entropy": 0.9843, "ret": -0.12936, "capital": 8706.4, "trades": 3809, "positions": 3, "exposure": 0.03, "predictions": 17651}
data\v2.jsonl:1400:{"tick": 6925, "t": "08:02:05", "acc": 0.515, "entropy": 0.9844, "ret": -0.129249, "capital": 8707.51, "trades": 3813, "positions": 2, "exposure": 0.02, "predictions": 17671}
data\v2.jsonl:1401:{"tick": 6930, "t": "08:07:07", "acc": 0.51, "entropy": 0.9863, "ret": -0.129191, "capital": 8708.09, "trades": 3817, "positions": 3, "exposure": 0.03, "predictions": 17691}
data\v2.jsonl:1402:{"tick": 6935, "t": "08:12:10", "acc": 0.515, "entropy": 0.9878, "ret": -0.129324, "capital": 8706.76, "trades": 3819, "positions": 3, "exposure": 0.03, "predictions": 17711}
data\v2.jsonl:1403:{"tick": 6940, "t": "08:17:12", "acc": 0.53, "entropy": 0.9863, "ret": -0.129266, "capital": 8707.34, "trades": 3821, "positions": 3, "exposure": 0.03, "predictions": 17731}
data\v2.jsonl:1404:{"tick": 6945, "t": "08:22:14", "acc": 0.51, "entropy": 0.9826, "ret": -0.128569, "capital": 8714.31, "trades": 3825, "positions": 2, "exposure": 0.02, "predictions": 17751}
data\v2.jsonl:1405:{"tick": 6950, "t": "08:27:16", "acc": 0.51, "entropy": 0.9834, "ret": -0.128401, "capital": 8715.99, "trades": 3829, "positions": 2, "exposure": 0.02, "predictions": 17771}
data\v2.jsonl:1406:{"tick": 6955, "t": "08:32:18", "acc": 0.555, "entropy": 0.9849, "ret": -0.128545, "capital": 8714.55, "trades": 3833, "positions": 3, "exposure": 0.03, "predictions": 17791}
data\v2.jsonl:1407:{"tick": 6960, "t": "08:37:33", "acc": 0.52, "entropy": 0.9826, "ret": -0.128967, "capital": 8710.33, "trades": 3836, "positions": 2, "exposure": 0.02, "predictions": 17811}
data\v2.jsonl:1408:{"tick": 6965, "t": "08:42:37", "acc": 0.525, "entropy": 0.981, "ret": -0.129604, "capital": 8703.96, "trades": 3840, "positions": 1, "exposure": 0.01, "predictions": 17831}
data\v2.jsonl:1409:{"tick": 6970, "t": "08:47:41", "acc": 0.515, "entropy": 0.982, "ret": -0.12934, "capital": 8706.6, "trades": 3845, "positions": 1, "exposure": 0.01, "predictions": 17851}
data\v2.jsonl:1410:{"tick": 6975, "t": "08:52:54", "acc": 0.52, "entropy": 0.9856, "ret": -0.129072, "capital": 8709.28, "trades": 3850, "positions": 2, "exposure": 0.02, "predictions": 17871}
data\v2.jsonl:1411:{"tick": 6980, "t": "08:57:57", "acc": 0.51, "entropy": 0.9864, "ret": -0.12965, "capital": 8703.5, "trades": 3853, "positions": 3, "exposure": 0.03, "predictions": 17891}
data\v2.jsonl:1412:{"tick": 6985, "t": "09:02:59", "acc": 0.5, "entropy": 0.9881, "ret": -0.130292, "capital": 8697.08, "trades": 3856, "positions": 1, "exposure": 0.01, "predictions": 17911}
data\v2.jsonl:1413:{"tick": 6990, "t": "09:08:01", "acc": 0.485, "entropy": 0.9837, "ret": -0.130327, "capital": 8696.73, "trades": 3858, "positions": 2, "exposure": 0.02, "predictions": 17931}
data\v2.jsonl:1414:{"tick": 6995, "t": "09:13:03", "acc": 0.5, "entropy": 0.9871, "ret": -0.129864, "capital": 8701.36, "trades": 3861, "positions": 3, "exposure": 0.03, "predictions": 17951}
data\v2.jsonl:1415:{"tick": 7000, "t": "09:18:05", "acc": 0.505, "entropy": 0.9874, "ret": -0.129673, "capital": 8703.27, "trades": 3864, "positions": 3, "exposure": 0.03, "predictions": 17971}
data\v2.jsonl:1416:{"tick": 7005, "t": "09:23:07", "acc": 0.465, "entropy": 0.9862, "ret": -0.130808, "capital": 8691.92, "trades": 3868, "positions": 0, "exposure": 0, "predictions": 17991}
data\v2.jsonl:1417:{"tick": 7010, "t": "09:28:38", "acc": 0.475, "entropy": 0.9861, "ret": -0.13053, "capital": 8694.7, "trades": 3871, "positions": 2, "exposure": 0.02, "predictions": 18010}
data\v2.jsonl:1418:{"tick": 7015, "t": "09:33:41", "acc": 0.475, "entropy": 0.9835, "ret": -0.129844, "capital": 8701.56, "trades": 3875, "positions": 3, "exposure": 0.03, "predictions": 18030}
data\v2.jsonl:1419:{"tick": 7020, "t": "09:38:43", "acc": 0.48, "entropy": 0.9838, "ret": -0.130206, "capital": 8697.94, "trades": 3878, "positions": 2, "exposure": 0.02, "predictions": 18050}
data\v2.jsonl:1420:{"tick": 7025, "t": "09:43:47", "acc": 0.47, "entropy": 0.9848, "ret": -0.130047, "capital": 8699.53, "trades": 3882, "positions": 1, "exposure": 0.01, "predictions": 18070}
data\v2.jsonl:1421:{"tick": 7030, "t": "09:48:49", "acc": 0.465, "entropy": 0.9863, "ret": -0.130185, "capital": 8698.15, "trades": 3884, "positions": 1, "exposure": 0.01, "predictions": 18090}
data\v2.jsonl:1422:{"tick": 7035, "t": "09:53:51", "acc": 0.48, "entropy": 0.9875, "ret": -0.129802, "capital": 8701.98, "trades": 3887, "positions": 2, "exposure": 0.02, "predictions": 18110}
data\v2.jsonl:1423:{"tick": 7040, "t": "09:58:54", "acc": 0.465, "entropy": 0.9832, "ret": -0.129756, "capital": 8702.44, "trades": 3888, "positions": 3, "exposure": 0.03, "predictions": 18130}
data\v2.jsonl:1424:{"tick": 7045, "t": "10:03:56", "acc": 0.45, "entropy": 0.9831, "ret": -0.12976, "capital": 8702.4, "trades": 3891, "positions": 3, "exposure": 0.03, "predictions": 18150}
data\v2.jsonl:1425:{"tick": 7050, "t": "10:08:58", "acc": 0.43, "entropy": 0.9846, "ret": -0.129684, "capital": 8703.16, "trades": 3895, "positions": 3, "exposure": 0.03, "predictions": 18170}
data\v2.jsonl:1426:{"tick": 7055, "t": "10:14:00", "acc": 0.45, "entropy": 0.9849, "ret": -0.129599, "capital": 8704.01, "trades": 3900, "positions": 2, "exposure": 0.02, "predictions": 18190}
data\v2.jsonl:1427:{"tick": 7060, "t": "10:19:02", "acc": 0.45, "entropy": 0.9839, "ret": -0.129681, "capital": 8703.19, "trades": 3903, "positions": 3, "exposure": 0.03, "predictions": 18210}
data\v2.jsonl:1428:{"tick": 7065, "t": "10:24:04", "acc": 0.435, "entropy": 0.9828, "ret": -0.129739, "capital": 8702.61, "trades": 3908, "positions": 1, "exposure": 0.01, "predictions": 18230}
data\v2.jsonl:1429:{"tick": 7070, "t": "10:29:06", "acc": 0.42, "entropy": 0.9856, "ret": -0.129759, "capital": 8702.41, "trades": 3912, "positions": 3, "exposure": 0.03, "predictions": 18250}
data\v2.jsonl:1430:{"tick": 7075, "t": "10:34:08", "acc": 0.41, "entropy": 0.9831, "ret": -0.129894, "capital": 8701.06, "trades": 3916, "positions": 1, "exposure": 0.01, "predictions": 18270}
data\v2.jsonl:1431:{"tick": 7080, "t": "10:39:10", "acc": 0.425, "entropy": 0.9842, "ret": -0.129913, "capital": 8700.87, "trades": 3919, "positions": 2, "exposure": 0.02, "predictions": 18290}
data\v2.jsonl:1432:{"tick": 7085, "t": "10:44:21", "acc": 0.42, "entropy": 0.9824, "ret": -0.129759, "capital": 8702.41, "trades": 3924, "positions": 0, "exposure": 0, "predictions": 18310}
data\v2.jsonl:1433:{"tick": 7090, "t": "10:49:30", "acc": 0.43, "entropy": 0.985, "ret": -0.129767, "capital": 8702.33, "trades": 3926, "positions": 2, "exposure": 0.02, "predictions": 18330}
data\v2.jsonl:1434:{"tick": 7095, "t": "10:54:32", "acc": 0.43, "entropy": 0.9842, "ret": -0.130418, "capital": 8695.82, "trades": 3928, "positions": 3, "exposure": 0.03, "predictions": 18350}
data\v2.jsonl:1435:{"tick": 7100, "t": "10:59:34", "acc": 0.435, "entropy": 0.981, "ret": -0.130857, "capital": 8691.43, "trades": 3931, "positions": 3, "exposure": 0.03, "predictions": 18370}
data\v2.jsonl:1436:{"tick": 7105, "t": "11:04:36", "acc": 0.44, "entropy": 0.9828, "ret": -0.131066, "capital": 8689.34, "trades": 3934, "positions": 3, "exposure": 0.03, "predictions": 18390}
data\v2.jsonl:1437:{"tick": 7110, "t": "11:09:38", "acc": 0.46, "entropy": 0.9836, "ret": -0.130717, "capital": 8692.83, "trades": 3937, "positions": 2, "exposure": 0.02, "predictions": 18410}
data\v2.jsonl:1438:{"tick": 7115, "t": "11:14:41", "acc": 0.465, "entropy": 0.9768, "ret": -0.12912, "capital": 8708.8, "trades": 3943, "positions": 1, "exposure": 0.01, "predictions": 18430}
data\v2.jsonl:1439:{"tick": 7120, "t": "11:19:43", "acc": 0.475, "entropy": 0.981, "ret": -0.129349, "capital": 8706.51, "trades": 3946, "positions": 3, "exposure": 0.03, "predictions": 18450}
data\v2.jsonl:1440:{"tick": 7125, "t": "11:24:49", "acc": 0.48, "entropy": 0.9814, "ret": -0.1304, "capital": 8696.0, "trades": 3949, "positions": 3, "exposure": 0.03, "predictions": 18470}
data\v2.jsonl:1441:{"tick": 7130, "t": "11:29:51", "acc": 0.48, "entropy": 0.9808, "ret": -0.130453, "capital": 8695.47, "trades": 3953, "positions": 2, "exposure": 0.02, "predictions": 18490}
data\v2.jsonl:1442:{"tick": 7135, "t": "11:34:53", "acc": 0.485, "entropy": 0.9817, "ret": -0.13063, "capital": 8693.7, "trades": 3958, "positions": 2, "exposure": 0.02, "predictions": 18510}
data\v2.jsonl:1443:{"tick": 7140, "t": "11:39:55", "acc": 0.495, "entropy": 0.9823, "ret": -0.130643, "capital": 8693.57, "trades": 3960, "positions": 2, "exposure": 0.02, "predictions": 18530}
data\v2.jsonl:1444:{"tick": 7145, "t": "11:45:09", "acc": 0.495, "entropy": 0.9824, "ret": -0.130683, "capital": 8693.17, "trades": 3964, "positions": 2, "exposure": 0.02, "predictions": 18550}
data\v2.jsonl:1445:{"tick": 7150, "t": "11:50:23", "acc": 0.495, "entropy": 0.9832, "ret": -0.130651, "capital": 8693.49, "trades": 3968, "positions": 2, "exposure": 0.02, "predictions": 18570}
data\v2.jsonl:1446:{"tick": 7155, "t": "11:55:27", "acc": 0.485, "entropy": 0.9833, "ret": -0.131008, "capital": 8689.92, "trades": 3973, "positions": 0, "exposure": 0, "predictions": 18590}
data\v2.jsonl:1447:{"tick": 7160, "t": "12:00:29", "acc": 0.48, "entropy": 0.9837, "ret": -0.13122, "capital": 8687.8, "trades": 3975, "positions": 1, "exposure": 0.01, "predictions": 18610}
data\v2.jsonl:1448:{"tick": 7165, "t": "12:05:31", "acc": 0.49, "entropy": 0.9827, "ret": -0.130991, "capital": 8690.09, "trades": 3976, "positions": 3, "exposure": 0.03, "predictions": 18630}
data\v2.jsonl:1449:{"tick": 7170, "t": "12:10:33", "acc": 0.505, "entropy": 0.9819, "ret": -0.131082, "capital": 8689.18, "trades": 3982, "positions": 2, "exposure": 0.02, "predictions": 18650}
data\v2.jsonl:1450:{"tick": 7175, "t": "12:16:12", "acc": 0.53, "entropy": 0.9807, "ret": -0.130806, "capital": 8691.94, "trades": 3986, "positions": 2, "exposure": 0.02, "predictions": 18669}
data\v2.jsonl:1451:{"tick": 7180, "t": "12:21:16", "acc": 0.52, "entropy": 0.9824, "ret": -0.131347, "capital": 8686.53, "trades": 3991, "positions": 1, "exposure": 0.01, "predictions": 18689}
data\v2.jsonl:1452:{"tick": 7185, "t": "12:26:19", "acc": 0.505, "entropy": 0.9807, "ret": -0.131657, "capital": 8683.43, "trades": 3993, "positions": 3, "exposure": 0.03, "predictions": 18709}
data\v2.jsonl:1453:{"tick": 7190, "t": "12:31:21", "acc": 0.5, "entropy": 0.9848, "ret": -0.131431, "capital": 8685.69, "trades": 3997, "positions": 2, "exposure": 0.02, "predictions": 18729}
data\v2.jsonl:1454:{"tick": 7195, "t": "12:36:25", "acc": 0.51, "entropy": 0.9829, "ret": -0.131509, "capital": 8684.91, "trades": 4001, "positions": 2, "exposure": 0.02, "predictions": 18749}
data\v2.jsonl:1455:{"tick": 7200, "t": "12:41:27", "acc": 0.515, "entropy": 0.9821, "ret": -0.131241, "capital": 8687.59, "trades": 4004, "positions": 1, "exposure": 0.01, "predictions": 18769}
data\v2.jsonl:1456:{"tick": 7205, "t": "12:46:52", "acc": 0.525, "entropy": 0.9809, "ret": -0.131268, "capital": 8687.32, "trades": 4006, "positions": 4, "exposure": 0.04, "predictions": 18789}
data\v2.jsonl:1457:{"tick": 7210, "t": "12:52:02", "acc": 0.53, "entropy": 0.9783, "ret": -0.130988, "capital": 8690.12, "trades": 4011, "positions": 2, "exposure": 0.02, "predictions": 18809}
data\v2.jsonl:1458:{"tick": 7215, "t": "12:57:04", "acc": 0.52, "entropy": 0.9801, "ret": -0.131276, "capital": 8687.24, "trades": 4015, "positions": 2, "exposure": 0.02, "predictions": 18829}
data\v2.jsonl:1459:{"tick": 7220, "t": "13:02:07", "acc": 0.505, "entropy": 0.9761, "ret": -0.131164, "capital": 8688.36, "trades": 4020, "positions": 3, "exposure": 0.03, "predictions": 18849}
data\v2.jsonl:1460:{"tick": 7225, "t": "13:07:09", "acc": 0.495, "entropy": 0.9832, "ret": -0.131608, "capital": 8683.92, "trades": 4023, "positions": 3, "exposure": 0.03, "predictions": 18869}
data\v2.jsonl:1461:{"tick": 7230, "t": "13:12:11", "acc": 0.505, "entropy": 0.9847, "ret": -0.130948, "capital": 8690.52, "trades": 4029, "positions": 2, "exposure": 0.02, "predictions": 18889}
data\v2.jsonl:1462:{"tick": 7235, "t": "13:17:15", "acc": 0.51, "entropy": 0.9842, "ret": -0.130717, "capital": 8692.83, "trades": 4032, "positions": 3, "exposure": 0.03, "predictions": 18909}
data\v2.jsonl:1463:{"tick": 7240, "t": "13:22:17", "acc": 0.505, "entropy": 0.9869, "ret": -0.132647, "capital": 8673.53, "trades": 4037, "positions": 2, "exposure": 0.02, "predictions": 18929}
data\v2.jsonl:1464:{"tick": 7245, "t": "13:27:20", "acc": 0.515, "entropy": 0.9888, "ret": -0.132732, "capital": 8672.68, "trades": 4042, "positions": 2, "exposure": 0.02, "predictions": 18949}
data\v2.jsonl:1465:{"tick": 7250, "t": "13:32:22", "acc": 0.505, "entropy": 0.9871, "ret": -0.132725, "capital": 8672.75, "trades": 4045, "positions": 1, "exposure": 0.01, "predictions": 18969}
data\v2.jsonl:1466:{"tick": 7235, "t": "13:39:37", "acc": 0.5, "entropy": 0.9873, "ret": -0.130948, "capital": 8690.52, "trades": 1000, "positions": 0, "exposure": 0, "predictions": 12}
data\v2.jsonl:1467:{"tick": 7240, "t": "13:44:39", "acc": 0.5, "entropy": 0.9842, "ret": -0.130934, "capital": 8690.66, "trades": 1001, "positions": 2, "exposure": 0.02, "predictions": 32}
data\v2.jsonl:1468:{"tick": 7245, "t": "13:49:43", "acc": 0.5, "entropy": 0.9853, "ret": -0.130966, "capital": 8690.34, "trades": 1003, "positions": 4, "exposure": 0.04, "predictions": 52}
data\v2.jsonl:1469:{"tick": 7250, "t": "13:54:46", "acc": 0.4861, "entropy": 0.9841, "ret": -0.131107, "capital": 8688.93, "trades": 1008, "positions": 1, "exposure": 0.01, "predictions": 72}
data\v2.jsonl:1470:{"tick": 7255, "t": "13:59:47", "acc": 0.5217, "entropy": 0.9839, "ret": -0.130938, "capital": 8690.62, "trades": 1011, "positions": 3, "exposure": 0.03, "predictions": 92}
data\v2.jsonl:1471:{"tick": 7260, "t": "14:04:50", "acc": 0.5089, "entropy": 0.9838, "ret": -0.130186, "capital": 8698.14, "trades": 1017, "positions": 1, "exposure": 0.01, "predictions": 112}
data\v2.jsonl:1472:{"tick": 7265, "t": "14:09:43", "acc": 0.5152, "entropy": 0.985, "ret": -0.129404, "capital": 8705.96, "trades": 1021, "positions": 1, "exposure": 0.01, "predictions": 132}
data\v2.jsonl:1473:{"tick": 7270, "t": "14:14:45", "acc": 0.4934, "entropy": 0.9886, "ret": -0.129818, "capital": 8701.82, "trades": 1023, "positions": 1, "exposure": 0.01, "predictions": 152}
data\v2.jsonl:1474:{"tick": 7275, "t": "14:19:48", "acc": 0.4942, "entropy": 0.9874, "ret": -0.130179, "capital": 8698.21, "trades": 1027, "positions": 3, "exposure": 0.03, "predictions": 172}
data\v2.jsonl:1475:{"tick": 7280, "t": "14:24:49", "acc": 0.5, "entropy": 0.9855, "ret": -0.130072, "capital": 8699.28, "trades": 1031, "positions": 1, "exposure": 0.01, "predictions": 192}
data\v2.jsonl:1476:{"tick": 7285, "t": "14:29:51", "acc": 0.5, "entropy": 0.9874, "ret": -0.129501, "capital": 8704.99, "trades": 1034, "positions": 2, "exposure": 0.02, "predictions": 212}
data\v2.jsonl:1477:{"tick": 7290, "t": "14:34:54", "acc": 0.485, "entropy": 0.987, "ret": -0.131148, "capital": 8688.52, "trades": 1037, "positions": 2, "exposure": 0.02, "predictions": 232}
data\v2.jsonl:1478:{"tick": 7295, "t": "14:39:56", "acc": 0.5, "entropy": 0.9894, "ret": -0.131081, "capital": 8689.19, "trades": 1038, "positions": 4, "exposure": 0.04, "predictions": 252}
data\v2.jsonl:1479:{"tick": 7300, "t": "14:44:58", "acc": 0.5, "entropy": 0.9884, "ret": -0.131184, "capital": 8688.16, "trades": 1041, "positions": 3, "exposure": 0.03, "predictions": 272}
data\v2.jsonl:1480:{"tick": 7305, "t": "14:50:00", "acc": 0.485, "entropy": 0.9882, "ret": -0.131787, "capital": 8682.13, "trades": 1044, "positions": 2, "exposure": 0.02, "predictions": 292}
data\v2.jsonl:1481:{"tick": 7310, "t": "14:55:02", "acc": 0.495, "entropy": 0.9867, "ret": -0.132004, "capital": 8679.96, "trades": 1048, "positions": 1, "exposure": 0.01, "predictions": 312}
data\v2.jsonl:1482:{"tick": 7315, "t": "15:00:04", "acc": 0.49, "entropy": 0.9879, "ret": -0.131813, "capital": 8681.87, "trades": 1051, "positions": 2, "exposure": 0.02, "predictions": 332}
data\v2.jsonl:1483:{"tick": 7320, "t": "15:05:06", "acc": 0.5, "entropy": 0.9856, "ret": -0.131271, "capital": 8687.29, "trades": 1053, "positions": 3, "exposure": 0.03, "predictions": 352}
data\v2.jsonl:1484:{"tick": 7325, "t": "15:10:09", "acc": 0.495, "entropy": 0.9816, "ret": -0.130828, "capital": 8691.72, "trades": 1057, "positions": 1, "exposure": 0.01, "predictions": 372}
data\v2.jsonl:1485:{"tick": 7330, "t": "15:15:11", "acc": 0.48, "entropy": 0.9839, "ret": -0.130923, "capital": 8690.77, "trades": 1059, "positions": 3, "exposure": 0.03, "predictions": 392}
data\v2.jsonl:1486:{"tick": 7335, "t": "15:20:13", "acc": 0.475, "entropy": 0.9829, "ret": -0.130615, "capital": 8693.85, "trades": 1061, "positions": 4, "exposure": 0.04, "predictions": 412}
data\v2.jsonl:1487:{"tick": 7340, "t": "15:25:15", "acc": 0.485, "entropy": 0.987, "ret": -0.129759, "capital": 8702.41, "trades": 1065, "positions": 2, "exposure": 0.02, "predictions": 432}
data\v2.jsonl:1488:{"tick": 7345, "t": "15:30:17", "acc": 0.475, "entropy": 0.9874, "ret": -0.12981, "capital": 8701.9, "trades": 1069, "positions": 1, "exposure": 0.01, "predictions": 452}
data\v2.jsonl:1489:{"tick": 7350, "t": "15:35:19", "acc": 0.48, "entropy": 0.9856, "ret": -0.129475, "capital": 8705.25, "trades": 1071, "positions": 3, "exposure": 0.03, "predictions": 472}
data\v2.jsonl:1490:{"tick": 7355, "t": "15:40:21", "acc": 0.5, "entropy": 0.9858, "ret": -0.131536, "capital": 8684.64, "trades": 1074, "positions": 2, "exposure": 0.02, "predictions": 492}
data\v2.jsonl:1491:{"tick": 7360, "t": "15:45:23", "acc": 0.5, "entropy": 0.9854, "ret": -0.131349, "capital": 8686.51, "trades": 1077, "positions": 1, "exposure": 0.01, "predictions": 512}
data\v2.jsonl:1492:{"tick": 7365, "t": "15:50:25", "acc": 0.505, "entropy": 0.986, "ret": -0.131053, "capital": 8689.47, "trades": 1081, "positions": 3, "exposure": 0.03, "predictions": 532}
data\v2.jsonl:1493:{"tick": 7370, "t": "15:55:27", "acc": 0.505, "entropy": 0.9869, "ret": -0.130155, "capital": 8698.45, "trades": 1086, "positions": 3, "exposure": 0.03, "predictions": 552}
data\v2.jsonl:1494:{"tick": 7375, "t": "16:00:29", "acc": 0.525, "entropy": 0.9881, "ret": -0.130248, "capital": 8697.52, "trades": 1089, "positions": 4, "exposure": 0.04, "predictions": 572}
data\v2.jsonl:1495:{"tick": 7380, "t": "16:05:31", "acc": 0.53, "entropy": 0.9873, "ret": -0.130248, "capital": 8697.52, "trades": 1091, "positions": 3, "exposure": 0.03, "predictions": 592}
data\v2.jsonl:1496:{"tick": 7385, "t": "16:10:33", "acc": 0.515, "entropy": 0.987, "ret": -0.130081, "capital": 8699.19, "trades": 1092, "positions": 3, "exposure": 0.03, "predictions": 612}
data\v2.jsonl:1497:{"tick": 7390, "t": "16:15:35", "acc": 0.51, "entropy": 0.987, "ret": -0.130477, "capital": 8695.23, "trades": 1094, "positions": 2, "exposure": 0.02, "predictions": 632}
data\v2.jsonl:1498:{"tick": 7395, "t": "16:20:37", "acc": 0.505, "entropy": 0.9883, "ret": -0.130795, "capital": 8692.05, "trades": 1097, "positions": 3, "exposure": 0.03, "predictions": 652}
data\v2.jsonl:1499:{"tick": 7400, "t": "16:25:39", "acc": 0.49, "entropy": 0.9906, "ret": -0.129564, "capital": 8704.36, "trades": 1099, "positions": 3, "exposure": 0.0302, "predictions": 672}
data\v2.jsonl:1500:{"tick": 7405, "t": "16:30:41", "acc": 0.47, "entropy": 0.9905, "ret": -0.128968, "capital": 8710.32, "trades": 1103, "positions": 0, "exposure": 0, "predictions": 692}
data\v2.jsonl:1501:{"tick": 7410, "t": "16:35:43", "acc": 0.495, "entropy": 0.9863, "ret": -0.128268, "capital": 8717.32, "trades": 1106, "positions": 1, "exposure": 0.0255, "predictions": 712}
data\v2.jsonl:1502:{"tick": 7415, "t": "16:40:46", "acc": 0.485, "entropy": 0.9877, "ret": -0.126737, "capital": 8732.63, "trades": 1108, "positions": 1, "exposure": 0.0114, "predictions": 732}
data\v2.jsonl:1503:{"tick": 7420, "t": "16:45:48", "acc": 0.505, "entropy": 0.9889, "ret": -0.127809, "capital": 8721.91, "trades": 1110, "positions": 3, "exposure": 0.038, "predictions": 752}
data\v2.jsonl:1504:{"tick": 7425, "t": "16:50:50", "acc": 0.5, "entropy": 0.9897, "ret": -0.127683, "capital": 8723.17, "trades": 1116, "positions": 3, "exposure": 0.03, "predictions": 772}
data\v2.jsonl:1505:{"tick": 7430, "t": "16:55:52", "acc": 0.5, "entropy": 0.9905, "ret": -0.126077, "capital": 8739.23, "trades": 1119, "positions": 2, "exposure": 0.0373, "predictions": 792}
data\v2.jsonl:1506:{"tick": 7435, "t": "17:00:54", "acc": 0.515, "entropy": 0.989, "ret": -0.125686, "capital": 8743.14, "trades": 1121, "positions": 3, "exposure": 0.0718, "predictions": 812}
data\v2.jsonl:1507:{"tick": 7440, "t": "17:05:56", "acc": 0.535, "entropy": 0.987, "ret": -0.123938, "capital": 8760.62, "trades": 1126, "positions": 3, "exposure": 0.0488, "predictions": 832}
data\v2.jsonl:1508:{"tick": 7445, "t": "17:10:58", "acc": 0.545, "entropy": 0.9889, "ret": -0.123629, "capital": 8763.71, "trades": 1134, "positions": 2, "exposure": 0.0566, "predictions": 852}
data\v2.jsonl:1509:{"tick": 7450, "t": "17:16:00", "acc": 0.535, "entropy": 0.9897, "ret": -0.124046, "capital": 8759.54, "trades": 1138, "positions": 2, "exposure": 0.0629, "predictions": 872}
data\v2.jsonl:1510:{"tick": 7455, "t": "17:21:02", "acc": 0.525, "entropy": 0.9903, "ret": -0.125244, "capital": 8747.56, "trades": 1141, "positions": 2, "exposure": 0.0541, "predictions": 892}
data\v2.jsonl:1511:{"tick": 7460, "t": "17:26:04", "acc": 0.495, "entropy": 0.9872, "ret": -0.132058, "capital": 8679.42, "trades": 1146, "positions": 1, "exposure": 0.018, "predictions": 912}
data\v2.jsonl:1512:{"tick": 7465, "t": "17:31:06", "acc": 0.485, "entropy": 0.9895, "ret": -0.131829, "capital": 8681.71, "trades": 1150, "positions": 1, "exposure": 0.01, "predictions": 932}
data\v2.jsonl:1513:{"tick": 7470, "t": "17:36:08", "acc": 0.47, "entropy": 0.9895, "ret": -0.131879, "capital": 8681.21, "trades": 1154, "positions": 1, "exposure": 0.0108, "predictions": 952}
data\v2.jsonl:1514:{"tick": 7475, "t": "17:41:10", "acc": 0.455, "entropy": 0.9888, "ret": -0.131502, "capital": 8684.98, "trades": 1157, "positions": 0, "exposure": 0, "predictions": 972}
data\v2.jsonl:1515:{"tick": 7480, "t": "17:46:12", "acc": 0.445, "entropy": 0.989, "ret": -0.131651, "capital": 8683.49, "trades": 1162, "positions": 1, "exposure": 0.01, "predictions": 992}
data\v2.jsonl:1516:{"tick": 7485, "t": "17:51:14", "acc": 0.465, "entropy": 0.9895, "ret": -0.13121, "capital": 8687.9, "trades": 1163, "positions": 2, "exposure": 0.0235, "predictions": 1012}
data\v2.jsonl:1517:{"tick": 7490, "t": "17:56:16", "acc": 0.47, "entropy": 0.989, "ret": -0.129345, "capital": 8706.55, "trades": 1166, "positions": 3, "exposure": 0.0766, "predictions": 1032}
data\v2.jsonl:1518:{"tick": 7495, "t": "18:01:18", "acc": 0.47, "entropy": 0.9871, "ret": -0.126353, "capital": 8736.47, "trades": 1172, "positions": 2, "exposure": 0.0405, "predictions": 1052}
data\v2.jsonl:1519:{"tick": 7500, "t": "18:06:20", "acc": 0.5, "entropy": 0.9894, "ret": -0.127186, "capital": 8728.14, "trades": 1175, "positions": 3, "exposure": 0.0762, "predictions": 1072}
data\v2.jsonl:1520:{"tick": 7505, "t": "18:11:23", "acc": 0.495, "entropy": 0.9904, "ret": -0.126101, "capital": 8738.99, "trades": 1179, "positions": 3, "exposure": 0.0816, "predictions": 1092}
data\v2.jsonl:1521:{"tick": 7510, "t": "18:16:24", "acc": 0.495, "entropy": 0.9893, "ret": -0.127217, "capital": 8727.83, "trades": 1183, "positions": 2, "exposure": 0.0576, "predictions": 1112}
data\v2.jsonl:1522:{"tick": 7515, "t": "18:21:26", "acc": 0.5, "entropy": 0.9892, "ret": -0.127872, "capital": 8721.28, "trades": 1186, "positions": 2, "exposure": 0.0589, "predictions": 1132}
data\v2.jsonl:1523:{"tick": 7520, "t": "18:26:28", "acc": 0.505, "entropy": 0.9881, "ret": -0.126947, "capital": 8730.53, "trades": 1189, "positions": 1, "exposure": 0.0351, "predictions": 1152}
data\v2.jsonl:1524:{"tick": 7525, "t": "18:31:31", "acc": 0.52, "entropy": 0.9896, "ret": -0.128038, "capital": 8719.62, "trades": 1192, "positions": 3, "exposure": 0.0867, "predictions": 1172}
data\v2.jsonl:1525:{"tick": 7530, "t": "18:36:33", "acc": 0.545, "entropy": 0.9888, "ret": -0.12611, "capital": 8738.9, "trades": 1197, "positions": 2, "exposure": 0.0606, "predictions": 1192}
data\v2.jsonl:1526:{"tick": 7535, "t": "18:41:35", "acc": 0.525, "entropy": 0.9891, "ret": -0.124476, "capital": 8755.24, "trades": 1201, "positions": 1, "exposure": 0.0378, "predictions": 1212}
data\v2.jsonl:1527:{"tick": 7540, "t": "18:46:37", "acc": 0.505, "entropy": 0.9871, "ret": -0.123813, "capital": 8761.87, "trades": 1204, "positions": 0, "exposure": 0, "predictions": 1232}
data\v2.jsonl:1528:{"tick": 7545, "t": "18:51:39", "acc": 0.515, "entropy": 0.9888, "ret": -0.122914, "capital": 8770.86, "trades": 1208, "positions": 1, "exposure": 0.0233, "predictions": 1252}
data\v2.jsonl:1529:{"tick": 7550, "t": "18:56:41", "acc": 0.49, "entropy": 0.9857, "ret": -0.123772, "capital": 8762.28, "trades": 1212, "positions": 1, "exposure": 0.031, "predictions": 1272}
data\v2.jsonl:1530:{"tick": 7555, "t": "19:01:43", "acc": 0.545, "entropy": 0.9849, "ret": -0.121734, "capital": 8782.66, "trades": 1214, "positions": 2, "exposure": 0.0634, "predictions": 1292}
data\v2.jsonl:1531:{"tick": 7560, "t": "19:06:45", "acc": 0.54, "entropy": 0.9813, "ret": -0.121109, "capital": 8788.91, "trades": 1217, "positions": 3, "exposure": 0.1215, "predictions": 1312}
data\v2.jsonl:1532:{"tick": 7565, "t": "19:11:48", "acc": 0.53, "entropy": 0.9853, "ret": -0.115718, "capital": 8842.82, "trades": 1221, "positions": 2, "exposure": 0.0572, "predictions": 1332}
data\v2.jsonl:1533:{"tick": 7570, "t": "19:16:50", "acc": 0.54, "entropy": 0.9829, "ret": -0.115552, "capital": 8844.48, "trades": 1223, "positions": 1, "exposure": 0.0254, "predictions": 1352}
data\v2.jsonl:1534:{"tick": 7575, "t": "19:21:51", "acc": 0.53, "entropy": 0.9831, "ret": -0.117371, "capital": 8826.29, "trades": 1226, "positions": 1, "exposure": 0.0244, "predictions": 1372}
data\v2.jsonl:1535:{"tick": 7580, "t": "19:26:53", "acc": 0.505, "entropy": 0.9822, "ret": -0.119013, "capital": 8809.87, "trades": 1232, "positions": 2, "exposure": 0.0811, "predictions": 1392}
data\v2.jsonl:1536:{"tick": 7585, "t": "19:31:55", "acc": 0.51, "entropy": 0.9833, "ret": -0.118474, "capital": 8815.26, "trades": 1234, "positions": 3, "exposure": 0.1006, "predictions": 1412}
data\v2.jsonl:1537:{"tick": 7590, "t": "19:36:58", "acc": 0.51, "entropy": 0.9845, "ret": -0.117333, "capital": 8826.67, "trades": 1238, "positions": 1, "exposure": 0.0297, "predictions": 1432}
data\v2.jsonl:1538:{"tick": 7595, "t": "19:42:00", "acc": 0.51, "entropy": 0.9856, "ret": -0.117877, "capital": 8821.23, "trades": 1240, "positions": 2, "exposure": 0.0773, "predictions": 1452}
data\v2.jsonl:1539:{"tick": 7600, "t": "19:47:02", "acc": 0.51, "entropy": 0.9866, "ret": -0.117802, "capital": 8821.98, "trades": 1243, "positions": 3, "exposure": 0.0984, "predictions": 1472}
data\v2.jsonl:1540:{"tick": 7605, "t": "19:52:04", "acc": 0.465, "entropy": 0.9858, "ret": -0.119183, "capital": 8808.17, "trades": 1247, "positions": 3, "exposure": 0.096, "predictions": 1492}
data\v2.jsonl:1541:{"tick": 7610, "t": "19:57:06", "acc": 0.47, "entropy": 0.9869, "ret": -0.120067, "capital": 8799.33, "trades": 1250, "positions": 3, "exposure": 0.1249, "predictions": 1512}
data\v2.jsonl:1542:{"tick": 7615, "t": "20:02:08", "acc": 0.49, "entropy": 0.9891, "ret": -0.121299, "capital": 8787.01, "trades": 1256, "positions": 4, "exposure": 0.1495, "predictions": 1532}
data\v2.jsonl:1543:{"tick": 7620, "t": "20:07:09", "acc": 0.49, "entropy": 0.9899, "ret": -0.116715, "capital": 8832.85, "trades": 1258, "positions": 3, "exposure": 0.1045, "predictions": 1552}
data\v2.jsonl:1544:{"tick": 7625, "t": "20:12:12", "acc": 0.5, "entropy": 0.9856, "ret": -0.118148, "capital": 8818.52, "trades": 1260, "positions": 3, "exposure": 0.0868, "predictions": 1572}
data\v2.jsonl:1545:{"tick": 7630, "t": "20:17:14", "acc": 0.49, "entropy": 0.9886, "ret": -0.117799, "capital": 8822.01, "trades": 1262, "positions": 4, "exposure": 0.1137, "predictions": 1592}
data\v2.jsonl:1546:{"tick": 7635, "t": "20:22:16", "acc": 0.5, "entropy": 0.9839, "ret": -0.116658, "capital": 8833.42, "trades": 1266, "positions": 2, "exposure": 0.0897, "predictions": 1612}
data\v2.jsonl:1547:{"tick": 7640, "t": "20:27:18", "acc": 0.495, "entropy": 0.9873, "ret": -0.114624, "capital": 8853.76, "trades": 1269, "positions": 1, "exposure": 0.0226, "predictions": 1632}
data\v2.jsonl:1548:{"tick": 7645, "t": "20:32:20", "acc": 0.485, "entropy": 0.9869, "ret": -0.115117, "capital": 8848.83, "trades": 1273, "positions": 2, "exposure": 0.058, "predictions": 1652}
data\v2.jsonl:1549:{"tick": 7650, "t": "20:37:21", "acc": 0.51, "entropy": 0.9863, "ret": -0.11604, "capital": 8839.6, "trades": 1277, "positions": 3, "exposure": 0.1129, "predictions": 1672}
data\v2.jsonl:1550:{"tick": 7655, "t": "20:42:24", "acc": 0.515, "entropy": 0.9861, "ret": -0.117933, "capital": 8820.67, "trades": 1280, "positions": 3, "exposure": 0.0762, "predictions": 1692}
data\v2.jsonl:1551:{"tick": 7660, "t": "20:47:26", "acc": 0.52, "entropy": 0.9882, "ret": -0.118115, "capital": 8818.85, "trades": 1285, "positions": 1, "exposure": 0.0275, "predictions": 1712}
data\v2.jsonl:1552:{"tick": 7665, "t": "20:52:28", "acc": 0.54, "entropy": 0.9841, "ret": -0.118929, "capital": 8810.71, "trades": 1288, "positions": 1, "exposure": 0.0358, "predictions": 1732}
data\v2.jsonl:1553:{"tick": 7670, "t": "20:57:30", "acc": 0.53, "entropy": 0.9871, "ret": -0.119418, "capital": 8805.82, "trades": 1291, "positions": 2, "exposure": 0.1031, "predictions": 1752}
data\v2.jsonl:1554:{"tick": 7675, "t": "21:02:32", "acc": 0.515, "entropy": 0.987, "ret": -0.119418, "capital": 8805.82, "trades": 1291, "positions": 4, "exposure": 0.1683, "predictions": 1772}
data\v2.jsonl:1555:{"tick": 7680, "t": "21:07:34", "acc": 0.54, "entropy": 0.9851, "ret": -0.1232, "capital": 8768.0, "trades": 1294, "positions": 3, "exposure": 0.09, "predictions": 1792}
data\v2.jsonl:1556:{"tick": 7685, "t": "21:12:36", "acc": 0.51, "entropy": 0.9829, "ret": -0.123697, "capital": 8763.03, "trades": 1295, "positions": 2, "exposure": 0.0638, "predictions": 1812}
data\v2.jsonl:1557:{"tick": 7690, "t": "21:17:38", "acc": 0.51, "entropy": 0.9831, "ret": -0.123757, "capital": 8762.43, "trades": 1296, "positions": 2, "exposure": 0.0772, "predictions": 1832}
data\v2.jsonl:1558:{"tick": 7695, "t": "21:22:40", "acc": 0.51, "entropy": 0.9847, "ret": -0.124613, "capital": 8753.87, "trades": 1300, "positions": 0, "exposure": 0, "predictions": 1852}
data\v2.jsonl:1559:{"tick": 7700, "t": "21:27:42", "acc": 0.5, "entropy": 0.982, "ret": -0.124087, "capital": 8759.13, "trades": 1302, "positions": 1, "exposure": 0.0155, "predictions": 1872}
data\v2.jsonl:1560:{"tick": 7705, "t": "21:32:44", "acc": 0.49, "entropy": 0.9841, "ret": -0.124213, "capital": 8757.87, "trades": 1304, "positions": 4, "exposure": 0.0807, "predictions": 1892}
data\v2.jsonl:1561:{"tick": 7710, "t": "21:37:46", "acc": 0.485, "entropy": 0.9828, "ret": -0.123949, "capital": 8760.51, "trades": 1306, "positions": 3, "exposure": 0.0476, "predictions": 1912}
data\v2.jsonl:1562:{"tick": 7715, "t": "21:42:48", "acc": 0.465, "entropy": 0.9829, "ret": -0.123906, "capital": 8760.94, "trades": 1311, "positions": 0, "exposure": 0, "predictions": 1932}
data\v2.jsonl:1563:{"tick": 7720, "t": "21:47:50", "acc": 0.46, "entropy": 0.9787, "ret": -0.124548, "capital": 8754.52, "trades": 1314, "positions": 2, "exposure": 0.0249, "predictions": 1952}
data\v2.jsonl:1564:{"tick": 7725, "t": "21:52:52", "acc": 0.47, "entropy": 0.9871, "ret": -0.123859, "capital": 8761.41, "trades": 1318, "positions": 2, "exposure": 0.0294, "predictions": 1972}
data\v2.jsonl:1565:{"tick": 7730, "t": "21:57:54", "acc": 0.48, "entropy": 0.986, "ret": -0.123646, "capital": 8763.54, "trades": 1320, "positions": 4, "exposure": 0.0775, "predictions": 1992}
data\v2.jsonl:1566:{"tick": 7735, "t": "22:02:56", "acc": 0.49, "entropy": 0.9844, "ret": -0.116872, "capital": 8831.28, "trades": 1327, "positions": 3, "exposure": 0.109, "predictions": 2012}
data\v2.jsonl:1567:{"tick": 7740, "t": "22:07:59", "acc": 0.495, "entropy": 0.9883, "ret": -0.12244, "capital": 8775.6, "trades": 1334, "positions": 2, "exposure": 0.028, "predictions": 2032}
data\v2.jsonl:1568:{"tick": 7745, "t": "22:13:01", "acc": 0.49, "entropy": 0.9878, "ret": -0.122181, "capital": 8778.19, "trades": 1339, "positions": 3, "exposure": 0.0473, "predictions": 2052}
data\v2.jsonl:1569:{"tick": 7750, "t": "22:18:03", "acc": 0.51, "entropy": 0.9877, "ret": -0.120176, "capital": 8798.24, "trades": 1343, "positions": 2, "exposure": 0.035, "predictions": 2072}
data\v2.jsonl:1570:{"tick": 7755, "t": "22:23:05", "acc": 0.51, "entropy": 0.9851, "ret": -0.120455, "capital": 8795.45, "trades": 1347, "positions": 1, "exposure": 0.0255, "predictions": 2092}
data\v2.jsonl:1571:{"tick": 7760, "t": "22:28:07", "acc": 0.51, "entropy": 0.9871, "ret": -0.122836, "capital": 8771.64, "trades": 1351, "positions": 1, "exposure": 0.0298, "predictions": 2112}
data\v2.jsonl:1572:{"tick": 7765, "t": "22:33:09", "acc": 0.53, "entropy": 0.9843, "ret": -0.119617, "capital": 8803.83, "trades": 1355, "positions": 1, "exposure": 0.044, "predictions": 2132}
data\v2.jsonl:1573:{"tick": 7770, "t": "22:38:11", "acc": 0.53, "entropy": 0.9846, "ret": -0.123441, "capital": 8765.59, "trades": 1358, "positions": 2, "exposure": 0.0539, "predictions": 2152}
data\v2.jsonl:1574:{"tick": 7775, "t": "22:43:13", "acc": 0.54, "entropy": 0.9812, "ret": -0.122804, "capital": 8771.96, "trades": 1361, "positions": 3, "exposure": 0.0776, "predictions": 2172}
data\v2.jsonl:1575:{"tick": 7780, "t": "22:48:16", "acc": 0.54, "entropy": 0.9862, "ret": -0.123007, "capital": 8769.93, "trades": 1364, "positions": 3, "exposure": 0.085, "predictions": 2192}
data\v2.jsonl:1576:{"tick": 7785, "t": "22:53:17", "acc": 0.54, "entropy": 0.985, "ret": -0.122819, "capital": 8771.81, "trades": 1366, "positions": 2, "exposure": 0.0561, "predictions": 2212}
data\v2.jsonl:1577:{"tick": 7790, "t": "22:58:19", "acc": 0.545, "entropy": 0.9867, "ret": -0.122718, "capital": 8772.82, "trades": 1369, "positions": 2, "exposure": 0.0624, "predictions": 2232}
data\v2.jsonl:1578:{"tick": 7795, "t": "23:03:22", "acc": 0.56, "entropy": 0.9861, "ret": -0.118257, "capital": 8817.43, "trades": 1372, "positions": 3, "exposure": 0.0705, "predictions": 2252}
data\v2.jsonl:1579:{"tick": 7800, "t": "23:08:24", "acc": 0.545, "entropy": 0.9893, "ret": -0.11857, "capital": 8814.3, "trades": 1376, "positions": 1, "exposure": 0.0221, "predictions": 2272}
data\v2.jsonl:1580:{"tick": 7805, "t": "23:13:27", "acc": 0.54, "entropy": 0.9898, "ret": -0.118778, "capital": 8812.22, "trades": 1379, "positions": 3, "exposure": 0.0591, "predictions": 2292}
data\v2.jsonl:1581:{"tick": 7810, "t": "23:18:29", "acc": 0.54, "entropy": 0.9917, "ret": -0.120176, "capital": 8798.24, "trades": 1383, "positions": 2, "exposure": 0.0308, "predictions": 2312}
data\v2.jsonl:1582:{"tick": 7815, "t": "23:23:31", "acc": 0.515, "entropy": 0.9918, "ret": -0.120365, "capital": 8796.35, "trades": 1386, "positions": 3, "exposure": 0.0484, "predictions": 2332}
data\v2.jsonl:1583:{"tick": 7820, "t": "23:28:33", "acc": 0.525, "entropy": 0.992, "ret": -0.119684, "capital": 8803.16, "trades": 1390, "positions": 2, "exposure": 0.0423, "predictions": 2352}
data\v2.jsonl:1584:{"tick": 7825, "t": "23:33:35", "acc": 0.515, "entropy": 0.9903, "ret": -0.119401, "capital": 8805.99, "trades": 1393, "positions": 1, "exposure": 0.0126, "predictions": 2372}
data\v2.jsonl:1585:{"tick": 7830, "t": "23:38:37", "acc": 0.505, "entropy": 0.9903, "ret": -0.119623, "capital": 8803.77, "trades": 1397, "positions": 1, "exposure": 0.01, "predictions": 2392}
data\v2.jsonl:1586:{"tick": 7835, "t": "23:43:40", "acc": 0.51, "entropy": 0.9888, "ret": -0.119761, "capital": 8802.39, "trades": 1402, "positions": 3, "exposure": 0.0358, "predictions": 2412}
data\v2.jsonl:1587:{"tick": 7840, "t": "23:48:42", "acc": 0.49, "entropy": 0.9871, "ret": -0.119652, "capital": 8803.48, "trades": 1405, "positions": 3, "exposure": 0.034, "predictions": 2432}
data\v2.jsonl:1588:{"tick": 7845, "t": "23:53:44", "acc": 0.485, "entropy": 0.987, "ret": -0.119496, "capital": 8805.04, "trades": 1410, "positions": 1, "exposure": 0.01, "predictions": 2452}
data\v2.jsonl:1589:{"tick": 7850, "t": "23:58:45", "acc": 0.495, "entropy": 0.988, "ret": -0.119451, "capital": 8805.49, "trades": 1411, "positions": 0, "exposure": 0, "predictions": 2472}
data\v2.jsonl:1590:{"tick": 7855, "t": "00:03:47", "acc": 0.505, "entropy": 0.9868, "ret": -0.119638, "capital": 8803.62, "trades": 1412, "positions": 2, "exposure": 0.0313, "predictions": 2492}
data\v2.jsonl:1591:{"tick": 7860, "t": "00:08:49", "acc": 0.505, "entropy": 0.9878, "ret": -0.122632, "capital": 8773.68, "trades": 1415, "positions": 2, "exposure": 0.02, "predictions": 2512}
data\v2.jsonl:1592:{"tick": 7865, "t": "00:13:52", "acc": 0.495, "entropy": 0.9897, "ret": -0.12267, "capital": 8773.3, "trades": 1419, "positions": 1, "exposure": 0.01, "predictions": 2532}
data\v2.jsonl:1593:{"tick": 7870, "t": "00:18:54", "acc": 0.475, "entropy": 0.9875, "ret": -0.12183, "capital": 8781.7, "trades": 1422, "positions": 2, "exposure": 0.02, "predictions": 2552}
data\v2.jsonl:1594:{"tick": 7875, "t": "00:23:56", "acc": 0.465, "entropy": 0.9886, "ret": -0.121818, "capital": 8781.82, "trades": 1424, "positions": 2, "exposure": 0.02, "predictions": 2572}
data\v2.jsonl:1595:{"tick": 7880, "t": "00:28:57", "acc": 0.47, "entropy": 0.9861, "ret": -0.121189, "capital": 8788.11, "trades": 1426, "positions": 2, "exposure": 0.02, "predictions": 2592}
data\v2.jsonl:1596:{"tick": 7885, "t": "00:33:59", "acc": 0.47, "entropy": 0.9872, "ret": -0.12135, "capital": 8786.5, "trades": 1431, "positions": 0, "exposure": 0, "predictions": 2612}
data\v2.jsonl:1597:{"tick": 7890, "t": "00:39:01", "acc": 0.47, "entropy": 0.9879, "ret": -0.121521, "capital": 8784.79, "trades": 1433, "positions": 3, "exposure": 0.03, "predictions": 2632}
data\v2.jsonl:1598:{"tick": 7895, "t": "00:44:04", "acc": 0.455, "entropy": 0.9867, "ret": -0.121581, "capital": 8784.19, "trades": 1435, "positions": 3, "exposure": 0.03, "predictions": 2652}
data\v2.jsonl:1599:{"tick": 7900, "t": "00:49:06", "acc": 0.47, "entropy": 0.9897, "ret": -0.121673, "capital": 8783.27, "trades": 1437, "positions": 3, "exposure": 0.03, "predictions": 2672}
data\v2.jsonl:1600:{"tick": 7905, "t": "00:54:08", "acc": 0.475, "entropy": 0.9889, "ret": -0.12099, "capital": 8790.1, "trades": 1439, "positions": 2, "exposure": 0.02, "predictions": 2692}
data\v2.jsonl:1601:{"tick": 7910, "t": "00:59:10", "acc": 0.48, "entropy": 0.9889, "ret": -0.121109, "capital": 8788.91, "trades": 1442, "positions": 2, "exposure": 0.02, "predictions": 2712}
data\v2.jsonl:1602:{"tick": 7915, "t": "01:04:12", "acc": 0.5, "entropy": 0.989, "ret": -0.120967, "capital": 8790.33, "trades": 1444, "positions": 4, "exposure": 0.04, "predictions": 2730}
data\v2.jsonl:1603:{"tick": 7920, "t": "01:09:14", "acc": 0.5, "entropy": 0.9887, "ret": -0.120956, "capital": 8790.44, "trades": 1449, "positions": 0, "exposure": 0, "predictions": 2750}
data\v2.jsonl:1604:{"tick": 7925, "t": "01:14:17", "acc": 0.51, "entropy": 0.9865, "ret": -0.121264, "capital": 8787.36, "trades": 1451, "positions": 2, "exposure": 0.02, "predictions": 2770}
data\v2.jsonl:1605:{"tick": 7930, "t": "01:19:18", "acc": 0.515, "entropy": 0.9861, "ret": -0.121277, "capital": 8787.23, "trades": 1453, "positions": 2, "exposure": 0.02, "predictions": 2790}
data\v2.jsonl:1606:{"tick": 7935, "t": "01:24:20", "acc": 0.52, "entropy": 0.9886, "ret": -0.120784, "capital": 8792.16, "trades": 1456, "positions": 3, "exposure": 0.033, "predictions": 2810}
data\v2.jsonl:1607:{"tick": 7940, "t": "01:29:22", "acc": 0.545, "entropy": 0.9889, "ret": -0.120564, "capital": 8794.36, "trades": 1461, "positions": 2, "exposure": 0.02, "predictions": 2830}
data\v2.jsonl:1608:{"tick": 7945, "t": "01:34:24", "acc": 0.53, "entropy": 0.989, "ret": -0.120667, "capital": 8793.33, "trades": 1462, "positions": 2, "exposure": 0.02, "predictions": 2850}
data\v2.jsonl:1609:{"tick": 7950, "t": "01:39:26", "acc": 0.5, "entropy": 0.9877, "ret": -0.121436, "capital": 8785.64, "trades": 1468, "positions": 2, "exposure": 0.02, "predictions": 2870}
data\v2.jsonl:1610:{"tick": 7955, "t": "01:44:29", "acc": 0.495, "entropy": 0.9877, "ret": -0.12184, "capital": 8781.6, "trades": 1470, "positions": 4, "exposure": 0.04, "predictions": 2890}
data\v2.jsonl:1611:{"tick": 7960, "t": "01:49:31", "acc": 0.495, "entropy": 0.9869, "ret": -0.121518, "capital": 8784.82, "trades": 1474, "positions": 3, "exposure": 0.03, "predictions": 2910}
data\v2.jsonl:1612:{"tick": 7965, "t": "01:54:33", "acc": 0.51, "entropy": 0.9864, "ret": -0.121262, "capital": 8787.38, "trades": 1478, "positions": 2, "exposure": 0.02, "predictions": 2930}
data\v2.jsonl:1613:{"tick": 7970, "t": "01:59:35", "acc": 0.525, "entropy": 0.987, "ret": -0.12108, "capital": 8789.2, "trades": 1482, "positions": 3, "exposure": 0.03, "predictions": 2950}
data\v2.jsonl:1614:{"tick": 7975, "t": "02:04:37", "acc": 0.54, "entropy": 0.9864, "ret": -0.121095, "capital": 8789.05, "trades": 1484, "positions": 3, "exposure": 0.03, "predictions": 2970}
data\v2.jsonl:1615:{"tick": 7980, "t": "02:09:39", "acc": 0.53, "entropy": 0.9837, "ret": -0.122033, "capital": 8779.67, "trades": 1489, "positions": 2, "exposure": 0.02, "predictions": 2990}
data\v2.jsonl:1616:{"tick": 7985, "t": "02:14:41", "acc": 0.53, "entropy": 0.982, "ret": -0.122085, "capital": 8779.15, "trades": 1491, "positions": 3, "exposure": 0.03, "predictions": 3010}
data\v2.jsonl:1617:{"tick": 7990, "t": "02:19:43", "acc": 0.52, "entropy": 0.9837, "ret": -0.121916, "capital": 8780.84, "trades": 1494, "positions": 2, "exposure": 0.02, "predictions": 3030}
data\v2.jsonl:1618:{"tick": 7995, "t": "02:24:45", "acc": 0.545, "entropy": 0.9855, "ret": -0.121612, "capital": 8783.88, "trades": 1496, "positions": 2, "exposure": 0.02, "predictions": 3050}
data\v2.jsonl:1619:{"tick": 8000, "t": "02:29:47", "acc": 0.535, "entropy": 0.9854, "ret": -0.121691, "capital": 8783.09, "trades": 1498, "positions": 2, "exposure": 0.02, "predictions": 3070}
data\v2.jsonl:1620:{"tick": 8005, "t": "02:34:49", "acc": 0.56, "entropy": 0.986, "ret": -0.122177, "capital": 8778.23, "trades": 1500, "positions": 2, "exposure": 0.02, "predictions": 3090}
data\v2.jsonl:1621:{"tick": 8010, "t": "02:39:52", "acc": 0.565, "entropy": 0.9804, "ret": -0.12254, "capital": 8774.6, "trades": 1504, "positions": 1, "exposure": 0.01, "predictions": 3110}
data\v2.jsonl:1622:{"tick": 8015, "t": "02:44:56", "acc": 0.54, "entropy": 0.9812, "ret": -0.122574, "capital": 8774.26, "trades": 1507, "positions": 2, "exposure": 0.02, "predictions": 3130}
data\v2.jsonl:1623:{"tick": 8020, "t": "02:49:58", "acc": 0.53, "entropy": 0.983, "ret": -0.122488, "capital": 8775.12, "trades": 1509, "positions": 3, "exposure": 0.03, "predictions": 3150}
data\v2.jsonl:1624:{"tick": 8025, "t": "02:55:00", "acc": 0.51, "entropy": 0.985, "ret": -0.122944, "capital": 8770.56, "trades": 1510, "positions": 4, "exposure": 0.04, "predictions": 3170}
data\v2.jsonl:1625:{"tick": 8030, "t": "03:00:03", "acc": 0.52, "entropy": 0.9844, "ret": -0.123339, "capital": 8766.61, "trades": 1513, "positions": 2, "exposure": 0.02, "predictions": 3190}
data\v2.jsonl:1626:{"tick": 8035, "t": "03:05:05", "acc": 0.495, "entropy": 0.983, "ret": -0.1234, "capital": 8766.0, "trades": 1516, "positions": 2, "exposure": 0.02, "predictions": 3210}
data\v2.jsonl:1627:{"tick": 8040, "t": "03:10:07", "acc": 0.495, "entropy": 0.9848, "ret": -0.12388, "capital": 8761.2, "trades": 1519, "positions": 3, "exposure": 0.03, "predictions": 3230}
data\v2.jsonl:1628:{"tick": 8045, "t": "03:15:10", "acc": 0.48, "entropy": 0.9846, "ret": -0.124405, "capital": 8755.95, "trades": 1525, "positions": 2, "exposure": 0.02, "predictions": 3250}
data\v2.jsonl:1629:{"tick": 8050, "t": "03:20:12", "acc": 0.485, "entropy": 0.9823, "ret": -0.124732, "capital": 8752.68, "trades": 1526, "positions": 4, "exposure": 0.04, "predictions": 3270}
data\v2.jsonl:1630:{"tick": 8055, "t": "03:25:14", "acc": 0.48, "entropy": 0.9839, "ret": -0.125302, "capital": 8746.98, "trades": 1529, "positions": 3, "exposure": 0.03, "predictions": 3290}
data\v2.jsonl:1631:{"tick": 8060, "t": "03:30:16", "acc": 0.47, "entropy": 0.985, "ret": -0.125176, "capital": 8748.24, "trades": 1532, "positions": 1, "exposure": 0.01, "predictions": 3310}
data\v2.jsonl:1632:{"tick": 8065, "t": "03:35:18", "acc": 0.495, "entropy": 0.9798, "ret": -0.125494, "capital": 8745.06, "trades": 1535, "positions": 1, "exposure": 0.01, "predictions": 3330}
data\v2.jsonl:1633:{"tick": 8070, "t": "03:40:20", "acc": 0.495, "entropy": 0.9844, "ret": -0.125248, "capital": 8747.52, "trades": 1538, "positions": 3, "exposure": 0.03, "predictions": 3350}
data\v2.jsonl:1634:{"tick": 8075, "t": "03:45:23", "acc": 0.495, "entropy": 0.9888, "ret": -0.125076, "capital": 8749.24, "trades": 1544, "positions": 2, "exposure": 0.02, "predictions": 3370}
data\v2.jsonl:1635:{"tick": 8080, "t": "03:50:25", "acc": 0.485, "entropy": 0.9864, "ret": -0.125315, "capital": 8746.85, "trades": 1549, "positions": 3, "exposure": 0.03, "predictions": 3390}
data\v2.jsonl:1636:{"tick": 8085, "t": "03:55:26", "acc": 0.49, "entropy": 0.985, "ret": -0.125269, "capital": 8747.31, "trades": 1552, "positions": 2, "exposure": 0.02, "predictions": 3410}
data\v2.jsonl:1637:{"tick": 8090, "t": "04:00:28", "acc": 0.48, "entropy": 0.9865, "ret": -0.12461, "capital": 8753.9, "trades": 1555, "positions": 4, "exposure": 0.04, "predictions": 3430}
data\v2.jsonl:1638:{"tick": 8095, "t": "04:05:30", "acc": 0.475, "entropy": 0.9845, "ret": -0.12522, "capital": 8747.8, "trades": 1558, "positions": 3, "exposure": 0.03, "predictions": 3450}
data\v2.jsonl:1639:{"tick": 8100, "t": "04:10:32", "acc": 0.485, "entropy": 0.9868, "ret": -0.125805, "capital": 8741.95, "trades": 1561, "positions": 2, "exposure": 0.02, "predictions": 3470}
data\v2.jsonl:1640:{"tick": 8105, "t": "04:15:35", "acc": 0.495, "entropy": 0.9867, "ret": -0.125786, "capital": 8742.14, "trades": 1563, "positions": 4, "exposure": 0.04, "predictions": 3490}
data\v2.jsonl:1641:{"tick": 8110, "t": "04:20:37", "acc": 0.495, "entropy": 0.9859, "ret": -0.125737, "capital": 8742.63, "trades": 1567, "positions": 1, "exposure": 0.01, "predictions": 3510}
data\v2.jsonl:1642:{"tick": 8115, "t": "04:25:39", "acc": 0.46, "entropy": 0.9873, "ret": -0.126358, "capital": 8736.42, "trades": 1572, "positions": 1, "exposure": 0.01, "predictions": 3530}
data\v2.jsonl:1643:{"tick": 8120, "t": "04:30:41", "acc": 0.465, "entropy": 0.9861, "ret": -0.126023, "capital": 8739.77, "trades": 1574, "positions": 0, "exposure": 0, "predictions": 3550}
data\v2.jsonl:1644:{"tick": 8125, "t": "04:35:43", "acc": 0.465, "entropy": 0.9861, "ret": -0.126023, "capital": 8739.77, "trades": 1574, "positions": 3, "exposure": 0.03, "predictions": 3570}
data\v2.jsonl:1645:{"tick": 8130, "t": "04:40:45", "acc": 0.465, "entropy": 0.9865, "ret": -0.126118, "capital": 8738.82, "trades": 1577, "positions": 2, "exposure": 0.02, "predictions": 3590}
data\v2.jsonl:1646:{"tick": 8135, "t": "04:45:47", "acc": 0.505, "entropy": 0.9865, "ret": -0.12626, "capital": 8737.4, "trades": 1578, "positions": 2, "exposure": 0.02, "predictions": 3610}
data\v2.jsonl:1647:{"tick": 8140, "t": "04:50:49", "acc": 0.51, "entropy": 0.9885, "ret": -0.126657, "capital": 8733.43, "trades": 1581, "positions": 3, "exposure": 0.03, "predictions": 3630}
data\v2.jsonl:1648:{"tick": 8145, "t": "04:55:51", "acc": 0.53, "entropy": 0.987, "ret": -0.126785, "capital": 8732.15, "trades": 1584, "positions": 3, "exposure": 0.03, "predictions": 3650}
data\v2.jsonl:1649:{"tick": 8150, "t": "05:00:53", "acc": 0.545, "entropy": 0.9874, "ret": -0.126955, "capital": 8730.45, "trades": 1588, "positions": 3, "exposure": 0.03, "predictions": 3670}
data\v2.jsonl:1650:{"tick": 8155, "t": "05:05:55", "acc": 0.535, "entropy": 0.9866, "ret": -0.127325, "capital": 8726.75, "trades": 1591, "positions": 2, "exposure": 0.02, "predictions": 3690}
data\v2.jsonl:1651:{"tick": 8160, "t": "05:10:57", "acc": 0.535, "entropy": 0.9835, "ret": -0.127678, "capital": 8723.22, "trades": 1596, "positions": 2, "exposure": 0.02, "predictions": 3710}
data\v2.jsonl:1652:{"tick": 8165, "t": "05:16:00", "acc": 0.53, "entropy": 0.9857, "ret": -0.127687, "capital": 8723.13, "trades": 1599, "positions": 1, "exposure": 0.01, "predictions": 3730}
data\v2.jsonl:1653:{"tick": 8170, "t": "05:21:04", "acc": 0.53, "entropy": 0.9831, "ret": -0.127992, "capital": 8720.08, "trades": 1606, "positions": 1, "exposure": 0.01, "predictions": 3750}
data\v2.jsonl:1654:{"tick": 8175, "t": "05:26:06", "acc": 0.51, "entropy": 0.982, "ret": -0.128543, "capital": 8714.57, "trades": 1609, "positions": 3, "exposure": 0.03, "predictions": 3770}
data\v2.jsonl:1655:{"tick": 8180, "t": "05:31:09", "acc": 0.52, "entropy": 0.9819, "ret": -0.128385, "capital": 8716.15, "trades": 1613, "positions": 2, "exposure": 0.02, "predictions": 3790}
data\v2.jsonl:1656:{"tick": 8185, "t": "05:36:11", "acc": 0.475, "entropy": 0.9806, "ret": -0.128655, "capital": 8713.45, "trades": 1617, "positions": 1, "exposure": 0.01, "predictions": 3810}
data\v2.jsonl:1657:{"tick": 8190, "t": "05:41:13", "acc": 0.48, "entropy": 0.9798, "ret": -0.128259, "capital": 8717.41, "trades": 1622, "positions": 1, "exposure": 0.01, "predictions": 3830}
data\v2.jsonl:1658:{"tick": 8195, "t": "05:46:15", "acc": 0.47, "entropy": 0.9808, "ret": -0.128701, "capital": 8712.99, "trades": 1624, "positions": 2, "exposure": 0.02, "predictions": 3850}
data\v2.jsonl:1659:{"tick": 8200, "t": "05:51:24", "acc": 0.435, "entropy": 0.9795, "ret": -0.128985, "capital": 8710.15, "trades": 1627, "positions": 3, "exposure": 0.03, "predictions": 3870}
data\v2.jsonl:1660:{"tick": 8205, "t": "05:56:26", "acc": 0.425, "entropy": 0.9846, "ret": -0.129878, "capital": 8701.22, "trades": 1631, "positions": 1, "exposure": 0.01, "predictions": 3890}
data\v2.jsonl:1661:{"tick": 8210, "t": "06:01:28", "acc": 0.41, "entropy": 0.9838, "ret": -0.130001, "capital": 8699.99, "trades": 1633, "positions": 4, "exposure": 0.04, "predictions": 3910}
data\v2.jsonl:1662:{"tick": 8215, "t": "06:06:30", "acc": 0.425, "entropy": 0.9838, "ret": -0.129898, "capital": 8701.02, "trades": 1634, "positions": 4, "exposure": 0.04, "predictions": 3930}
data\v2.jsonl:1663:{"tick": 8220, "t": "06:11:32", "acc": 0.42, "entropy": 0.9847, "ret": -0.130359, "capital": 8696.41, "trades": 1638, "positions": 0, "exposure": 0, "predictions": 3950}
data\v2.jsonl:1664:{"tick": 8225, "t": "06:16:36", "acc": 0.425, "entropy": 0.9818, "ret": -0.130454, "capital": 8695.46, "trades": 1640, "positions": 2, "exposure": 0.02, "predictions": 3970}
data\v2.jsonl:1665:{"tick": 8230, "t": "06:21:39", "acc": 0.415, "entropy": 0.9822, "ret": -0.130405, "capital": 8695.95, "trades": 1643, "positions": 3, "exposure": 0.03, "predictions": 3990}
data\v2.jsonl:1666:{"tick": 8235, "t": "06:26:41", "acc": 0.425, "entropy": 0.984, "ret": -0.130581, "capital": 8694.19, "trades": 1647, "positions": 2, "exposure": 0.02, "predictions": 4010}
data\v2.jsonl:1667:{"tick": 8240, "t": "06:31:43", "acc": 0.445, "entropy": 0.982, "ret": -0.130138, "capital": 8698.62, "trades": 1650, "positions": 3, "exposure": 0.03, "predictions": 4030}
data\v2.jsonl:1668:{"tick": 8245, "t": "06:36:45", "acc": 0.47, "entropy": 0.982, "ret": -0.129743, "capital": 8702.57, "trades": 1653, "positions": 2, "exposure": 0.02, "predictions": 4050}
data\v2.jsonl:1669:{"tick": 8250, "t": "06:41:47", "acc": 0.485, "entropy": 0.9841, "ret": -0.12979, "capital": 8702.1, "trades": 1657, "positions": 2, "exposure": 0.02, "predictions": 4070}
data\v2.jsonl:1670:{"tick": 8255, "t": "06:46:50", "acc": 0.485, "entropy": 0.9822, "ret": -0.130501, "capital": 8694.99, "trades": 1662, "positions": 3, "exposure": 0.03, "predictions": 4090}
data\v2.jsonl:1671:{"tick": 8260, "t": "06:51:52", "acc": 0.5, "entropy": 0.9819, "ret": -0.130205, "capital": 8697.95, "trades": 1667, "positions": 3, "exposure": 0.03, "predictions": 4110}
data\v2.jsonl:1672:{"tick": 8265, "t": "06:56:54", "acc": 0.47, "entropy": 0.9802, "ret": -0.130326, "capital": 8696.74, "trades": 1672, "positions": 3, "exposure": 0.03, "predictions": 4130}
data\v2.jsonl:1673:{"tick": 8270, "t": "07:01:56", "acc": 0.47, "entropy": 0.9864, "ret": -0.130455, "capital": 8695.45, "trades": 1677, "positions": 2, "exposure": 0.02, "predictions": 4150}
data\v2.jsonl:1674:{"tick": 8275, "t": "07:06:58", "acc": 0.495, "entropy": 0.9887, "ret": -0.130417, "capital": 8695.83, "trades": 1679, "positions": 3, "exposure": 0.03, "predictions": 4170}
data\v2.jsonl:1675:{"tick": 8280, "t": "07:12:00", "acc": 0.48, "entropy": 0.9893, "ret": -0.130654, "capital": 8693.46, "trades": 1685, "positions": 3, "exposure": 0.03, "predictions": 4190}
data\v2.jsonl:1676:{"tick": 8285, "t": "07:17:02", "acc": 0.51, "entropy": 0.9889, "ret": -0.1307, "capital": 8693.0, "trades": 1689, "positions": 3, "exposure": 0.03, "predictions": 4210}
data\v2.jsonl:1677:{"tick": 8290, "t": "07:22:04", "acc": 0.51, "entropy": 0.9855, "ret": -0.130723, "capital": 8692.77, "trades": 1693, "positions": 2, "exposure": 0.02, "predictions": 4230}
data\v2.jsonl:1678:{"tick": 8295, "t": "07:27:06", "acc": 0.48, "entropy": 0.9824, "ret": -0.128893, "capital": 8711.07, "trades": 1699, "positions": 2, "exposure": 0.02, "predictions": 4250}
data\v2.jsonl:1679:{"tick": 8300, "t": "07:32:08", "acc": 0.5, "entropy": 0.9819, "ret": -0.128737, "capital": 8712.63, "trades": 1703, "positions": 2, "exposure": 0.02, "predictions": 4270}
data\v2.jsonl:1680:{"tick": 8305, "t": "07:37:10", "acc": 0.505, "entropy": 0.9774, "ret": -0.127887, "capital": 8721.13, "trades": 1706, "positions": 3, "exposure": 0.03, "predictions": 4290}
data\v2.jsonl:1681:{"tick": 8310, "t": "07:42:13", "acc": 0.505, "entropy": 0.9728, "ret": -0.12796, "capital": 8720.4, "trades": 1709, "positions": 3, "exposure": 0.03, "predictions": 4310}
data\v2.jsonl:1682:{"tick": 8315, "t": "07:47:15", "acc": 0.53, "entropy": 0.9738, "ret": -0.127556, "capital": 8724.44, "trades": 1712, "positions": 2, "exposure": 0.02, "predictions": 4330}
data\v2.jsonl:1683:{"tick": 8320, "t": "07:52:17", "acc": 0.535, "entropy": 0.9751, "ret": -0.12756, "capital": 8724.4, "trades": 1714, "positions": 3, "exposure": 0.03, "predictions": 4350}
data\v2.jsonl:1684:{"tick": 8325, "t": "07:57:19", "acc": 0.525, "entropy": 0.9754, "ret": -0.127114, "capital": 8728.86, "trades": 1716, "positions": 3, "exposure": 0.03, "predictions": 4370}
data\v2.jsonl:1685:{"tick": 8330, "t": "08:02:21", "acc": 0.555, "entropy": 0.9773, "ret": -0.127778, "capital": 8722.22, "trades": 1719, "positions": 4, "exposure": 0.04, "predictions": 4390}
data\v2.jsonl:1686:{"tick": 8335, "t": "08:07:23", "acc": 0.53, "entropy": 0.9783, "ret": -0.127985, "capital": 8720.15, "trades": 1722, "positions": 3, "exposure": 0.03, "predictions": 4410}
data\v2.jsonl:1687:{"tick": 8340, "t": "08:12:25", "acc": 0.52, "entropy": 0.9813, "ret": -0.127531, "capital": 8724.69, "trades": 1725, "positions": 2, "exposure": 0.02, "predictions": 4430}
data\v2.jsonl:1688:{"tick": 8345, "t": "08:17:27", "acc": 0.52, "entropy": 0.9805, "ret": -0.128073, "capital": 8719.27, "trades": 1729, "positions": 2, "exposure": 0.02, "predictions": 4450}
data\v2.jsonl:1689:{"tick": 8350, "t": "08:22:29", "acc": 0.5, "entropy": 0.9769, "ret": -0.127666, "capital": 8723.34, "trades": 1730, "positions": 4, "exposure": 0.04, "predictions": 4470}
data\v2.jsonl:1690:{"tick": 8355, "t": "08:27:31", "acc": 0.515, "entropy": 0.9762, "ret": -0.128825, "capital": 8711.75, "trades": 1735, "positions": 2, "exposure": 0.02, "predictions": 4490}
data\v2.jsonl:1691:{"tick": 8360, "t": "08:32:33", "acc": 0.52, "entropy": 0.978, "ret": -0.128844, "capital": 8711.56, "trades": 1739, "positions": 2, "exposure": 0.02, "predictions": 4510}
data\v2.jsonl:1692:{"tick": 8365, "t": "08:37:36", "acc": 0.525, "entropy": 0.9736, "ret": -0.128412, "capital": 8715.88, "trades": 1744, "positions": 0, "exposure": 0, "predictions": 4530}
data\v2.jsonl:1693:{"tick": 8370, "t": "08:42:38", "acc": 0.525, "entropy": 0.9784, "ret": -0.12845, "capital": 8715.5, "trades": 1747, "positions": 2, "exposure": 0.02, "predictions": 4550}
data\v2.jsonl:1694:{"tick": 8375, "t": "08:47:40", "acc": 0.525, "entropy": 0.9791, "ret": -0.128457, "capital": 8715.43, "trades": 1750, "positions": 2, "exposure": 0.02, "predictions": 4570}
data\v2.jsonl:1695:{"tick": 8380, "t": "08:52:42", "acc": 0.505, "entropy": 0.9742, "ret": -0.128581, "capital": 8714.19, "trades": 1754, "positions": 2, "exposure": 0.02, "predictions": 4590}
data\v2.jsonl:1696:{"tick": 8385, "t": "08:57:44", "acc": 0.515, "entropy": 0.977, "ret": -0.128774, "capital": 8712.26, "trades": 1755, "positions": 3, "exposure": 0.03, "predictions": 4610}
data\v2.jsonl:1697:{"tick": 8390, "t": "09:02:47", "acc": 0.52, "entropy": 0.9794, "ret": -0.129082, "capital": 8709.18, "trades": 1761, "positions": 0, "exposure": 0, "predictions": 4630}
data\v2.jsonl:1698:{"tick": 8395, "t": "09:07:48", "acc": 0.54, "entropy": 0.9833, "ret": -0.128972, "capital": 8710.28, "trades": 1762, "positions": 3, "exposure": 0.03, "predictions": 4650}
data\v2.jsonl:1699:{"tick": 8400, "t": "09:12:50", "acc": 0.545, "entropy": 0.986, "ret": -0.128841, "capital": 8711.59, "trades": 1766, "positions": 2, "exposure": 0.02, "predictions": 4670}
data\v2.jsonl:1700:{"tick": 8405, "t": "09:17:53", "acc": 0.515, "entropy": 0.9848, "ret": -0.128263, "capital": 8717.37, "trades": 1769, "positions": 1, "exposure": 0.01, "predictions": 4690}
data\v2.jsonl:1701:{"tick": 8410, "t": "09:22:55", "acc": 0.505, "entropy": 0.9843, "ret": -0.128295, "capital": 8717.05, "trades": 1773, "positions": 1, "exposure": 0.01, "predictions": 4710}
data\v2.jsonl:1702:{"tick": 8415, "t": "09:27:57", "acc": 0.5, "entropy": 0.9839, "ret": -0.128194, "capital": 8718.06, "trades": 1774, "positions": 4, "exposure": 0.04, "predictions": 4730}
data\v2.jsonl:1703:{"tick": 8420, "t": "09:32:59", "acc": 0.505, "entropy": 0.9838, "ret": -0.128467, "capital": 8715.33, "trades": 1781, "positions": 2, "exposure": 0.02, "predictions": 4750}
data\v2.jsonl:1704:{"tick": 8425, "t": "09:38:01", "acc": 0.505, "entropy": 0.9838, "ret": -0.128334, "capital": 8716.66, "trades": 1784, "positions": 2, "exposure": 0.02, "predictions": 4770}
data\v2.jsonl:1705:{"tick": 8430, "t": "09:43:03", "acc": 0.5, "entropy": 0.9823, "ret": -0.129103, "capital": 8708.97, "trades": 1788, "positions": 1, "exposure": 0.01, "predictions": 4790}
data\v2.jsonl:1706:{"tick": 8435, "t": "09:48:05", "acc": 0.5, "entropy": 0.985, "ret": -0.129067, "capital": 8709.33, "trades": 1791, "positions": 2, "exposure": 0.02, "predictions": 4810}
data\v2.jsonl:1707:{"tick": 8440, "t": "09:53:07", "acc": 0.475, "entropy": 0.9852, "ret": -0.129093, "capital": 8709.07, "trades": 1796, "positions": 1, "exposure": 0.01, "predictions": 4830}
data\v2.jsonl:1708:{"tick": 8445, "t": "09:58:09", "acc": 0.46, "entropy": 0.9858, "ret": -0.128916, "capital": 8710.84, "trades": 1801, "positions": 2, "exposure": 0.02, "predictions": 4850}
data\v2.jsonl:1709:{"tick": 8450, "t": "10:03:11", "acc": 0.48, "entropy": 0.9875, "ret": -0.12873, "capital": 8712.7, "trades": 1804, "positions": 4, "exposure": 0.04, "predictions": 4870}
data\v2.jsonl:1710:{"tick": 8455, "t": "10:08:14", "acc": 0.49, "entropy": 0.9877, "ret": -0.128546, "capital": 8714.54, "trades": 1807, "positions": 3, "exposure": 0.03, "predictions": 4890}
data\v2.jsonl:1711:{"tick": 8460, "t": "10:13:16", "acc": 0.5, "entropy": 0.9875, "ret": -0.128358, "capital": 8716.42, "trades": 1810, "positions": 3, "exposure": 0.03, "predictions": 4910}
data\v2.jsonl:1712:{"tick": 8465, "t": "10:18:19", "acc": 0.495, "entropy": 0.9876, "ret": -0.128699, "capital": 8713.01, "trades": 1814, "positions": 0, "exposure": 0, "predictions": 4930}
data\v2.jsonl:1713:{"tick": 8470, "t": "10:23:21", "acc": 0.495, "entropy": 0.9888, "ret": -0.129111, "capital": 8708.89, "trades": 1816, "positions": 2, "exposure": 0.02, "predictions": 4950}
data\v2.jsonl:1714:{"tick": 8475, "t": "10:28:23", "acc": 0.485, "entropy": 0.9889, "ret": -0.129193, "capital": 8708.07, "trades": 1818, "positions": 3, "exposure": 0.03, "predictions": 4970}
data\v2.jsonl:1715:{"tick": 8480, "t": "10:33:25", "acc": 0.475, "entropy": 0.9883, "ret": -0.128744, "capital": 8712.56, "trades": 1822, "positions": 2, "exposure": 0.02, "predictions": 4990}
data\v2.jsonl:1716:{"tick": 8485, "t": "10:38:27", "acc": 0.47, "entropy": 0.9873, "ret": -0.128721, "capital": 8712.79, "trades": 1825, "positions": 2, "exposure": 0.02, "predictions": 5010}
data\v2.jsonl:1717:{"tick": 8490, "t": "10:43:29", "acc": 0.47, "entropy": 0.9849, "ret": -0.128844, "capital": 8711.56, "trades": 1829, "positions": 1, "exposure": 0.01, "predictions": 5030}
data\v2.jsonl:1718:{"tick": 8495, "t": "10:48:32", "acc": 0.455, "entropy": 0.9864, "ret": -0.128862, "capital": 8711.38, "trades": 1830, "positions": 3, "exposure": 0.03, "predictions": 5050}
data\v2.jsonl:1719:{"tick": 8500, "t": "10:53:34", "acc": 0.435, "entropy": 0.9859, "ret": -0.128777, "capital": 8712.23, "trades": 1833, "positions": 1, "exposure": 0.01, "predictions": 5070}
data\v2.jsonl:1720:{"tick": 8505, "t": "10:58:36", "acc": 0.445, "entropy": 0.988, "ret": -0.128628, "capital": 8713.72, "trades": 1835, "positions": 1, "exposure": 0.0152, "predictions": 5090}
data\v2.jsonl:1721:{"tick": 8510, "t": "11:03:38", "acc": 0.44, "entropy": 0.9881, "ret": -0.130453, "capital": 8695.47, "trades": 1837, "positions": 3, "exposure": 0.03, "predictions": 5110}
data\v2.jsonl:1722:{"tick": 8515, "t": "11:08:40", "acc": 0.44, "entropy": 0.9865, "ret": -0.130483, "capital": 8695.17, "trades": 1842, "positions": 1, "exposure": 0.01, "predictions": 5130}
data\v2.jsonl:1723:{"tick": 8520, "t": "11:13:42", "acc": 0.44, "entropy": 0.9866, "ret": -0.130483, "capital": 8695.17, "trades": 1842, "positions": 3, "exposure": 0.03, "predictions": 5150}
data\v2.jsonl:1724:{"tick": 8525, "t": "11:18:44", "acc": 0.45, "entropy": 0.9875, "ret": -0.130581, "capital": 8694.19, "trades": 1846, "positions": 1, "exposure": 0.01, "predictions": 5170}
data\v2.jsonl:1725:{"tick": 8530, "t": "11:23:47", "acc": 0.49, "entropy": 0.9898, "ret": -0.130269, "capital": 8697.31, "trades": 1850, "positions": 1, "exposure": 0.01, "predictions": 5190}
data\v2.jsonl:1726:{"tick": 8535, "t": "11:28:49", "acc": 0.485, "entropy": 0.9906, "ret": -0.130105, "capital": 8698.95, "trades": 1853, "positions": 3, "exposure": 0.03, "predictions": 5210}
data\v2.jsonl:1727:{"tick": 8540, "t": "11:33:51", "acc": 0.5, "entropy": 0.9895, "ret": -0.130305, "capital": 8696.95, "trades": 1857, "positions": 2, "exposure": 0.02, "predictions": 5230}
data\v2.jsonl:1728:{"tick": 8545, "t": "11:38:53", "acc": 0.52, "entropy": 0.9885, "ret": -0.130512, "capital": 8694.88, "trades": 1860, "positions": 2, "exposure": 0.02, "predictions": 5250}
data\v2.jsonl:1729:{"tick": 8550, "t": "11:43:54", "acc": 0.52, "entropy": 0.9888, "ret": -0.129881, "capital": 8701.19, "trades": 1864, "positions": 2, "exposure": 0.02, "predictions": 5270}
data\v2.jsonl:1730:{"tick": 8555, "t": "11:48:57", "acc": 0.515, "entropy": 0.9895, "ret": -0.129446, "capital": 8705.54, "trades": 1866, "positions": 3, "exposure": 0.0395, "predictions": 5290}
data\v2.jsonl:1731:{"tick": 8560, "t": "11:53:59", "acc": 0.51, "entropy": 0.9897, "ret": -0.12954, "capital": 8704.6, "trades": 1870, "positions": 1, "exposure": 0.01, "predictions": 5310}
data\v2.jsonl:1732:{"tick": 8565, "t": "11:59:01", "acc": 0.525, "entropy": 0.989, "ret": -0.129618, "capital": 8703.82, "trades": 1874, "positions": 1, "exposure": 0.01, "predictions": 5330}
data\v2.jsonl:1733:{"tick": 8570, "t": "12:04:03", "acc": 0.525, "entropy": 0.9902, "ret": -0.12937, "capital": 8706.3, "trades": 1877, "positions": 1, "exposure": 0.0173, "predictions": 5350}
data\v2.jsonl:1734:{"tick": 8575, "t": "12:09:05", "acc": 0.52, "entropy": 0.9881, "ret": -0.129657, "capital": 8703.43, "trades": 1881, "positions": 1, "exposure": 0.0164, "predictions": 5370}
data\v2.jsonl:1735:{"tick": 8580, "t": "12:14:07", "acc": 0.505, "entropy": 0.9901, "ret": -0.130382, "capital": 8696.18, "trades": 1884, "positions": 3, "exposure": 0.0315, "predictions": 5390}
data\v2.jsonl:1736:{"tick": 8585, "t": "12:19:09", "acc": 0.485, "entropy": 0.9877, "ret": -0.130101, "capital": 8698.99, "trades": 1888, "positions": 2, "exposure": 0.02, "predictions": 5410}
data\v2.jsonl:1737:{"tick": 8590, "t": "12:24:11", "acc": 0.5, "entropy": 0.9883, "ret": -0.129944, "capital": 8700.56, "trades": 1892, "positions": 3, "exposure": 0.0436, "predictions": 5430}
data\v2.jsonl:1738:{"tick": 8595, "t": "12:29:13", "acc": 0.49, "entropy": 0.9873, "ret": -0.130204, "capital": 8697.96, "trades": 1895, "positions": 3, "exposure": 0.03, "predictions": 5450}
data\v2.jsonl:1739:{"tick": 8600, "t": "12:34:15", "acc": 0.48, "entropy": 0.9841, "ret": -0.129975, "capital": 8700.25, "trades": 1898, "positions": 2, "exposure": 0.02, "predictions": 5470}
data\v2.jsonl:1740:{"tick": 8605, "t": "12:39:17", "acc": 0.475, "entropy": 0.9866, "ret": -0.130377, "capital": 8696.23, "trades": 1902, "positions": 1, "exposure": 0.01, "predictions": 5490}
data\v2.jsonl:1741:{"tick": 8610, "t": "12:44:20", "acc": 0.495, "entropy": 0.9858, "ret": -0.130157, "capital": 8698.43, "trades": 1904, "positions": 3, "exposure": 0.03, "predictions": 5510}
data\v2.jsonl:1742:{"tick": 8615, "t": "12:49:22", "acc": 0.5, "entropy": 0.9872, "ret": -0.129792, "capital": 8702.08, "trades": 1907, "positions": 2, "exposure": 0.02, "predictions": 5530}
data\v2.jsonl:1743:{"tick": 8620, "t": "12:54:24", "acc": 0.505, "entropy": 0.9868, "ret": -0.130004, "capital": 8699.96, "trades": 1910, "positions": 1, "exposure": 0.01, "predictions": 5550}
data\v2.jsonl:1744:{"tick": 8625, "t": "12:59:26", "acc": 0.515, "entropy": 0.9887, "ret": -0.130166, "capital": 8698.34, "trades": 1911, "positions": 2, "exposure": 0.02, "predictions": 5570}
data\v2.jsonl:1745:{"tick": 8630, "t": "13:04:28", "acc": 0.52, "entropy": 0.9886, "ret": -0.130886, "capital": 8691.14, "trades": 1914, "positions": 2, "exposure": 0.02, "predictions": 5590}
data\v2.jsonl:1746:{"tick": 8635, "t": "13:09:30", "acc": 0.54, "entropy": 0.9904, "ret": -0.131402, "capital": 8685.98, "trades": 1918, "positions": 1, "exposure": 0.01, "predictions": 5610}
data\v2.jsonl:1747:{"tick": 8640, "t": "13:14:32", "acc": 0.525, "entropy": 0.9888, "ret": -0.131607, "capital": 8683.93, "trades": 1922, "positions": 2, "exposure": 0.02, "predictions": 5630}
data\v2.jsonl:1748:{"tick": 8645, "t": "13:19:35", "acc": 0.535, "entropy": 0.9885, "ret": -0.130309, "capital": 8696.91, "trades": 1925, "positions": 2, "exposure": 0.02, "predictions": 5650}
data\v2.jsonl:1749:{"tick": 8650, "t": "13:24:37", "acc": 0.555, "entropy": 0.992, "ret": -0.130468, "capital": 8695.32, "trades": 1929, "positions": 4, "exposure": 0.04, "predictions": 5670}
data\v2.jsonl:1750:{"tick": 8655, "t": "13:29:39", "acc": 0.55, "entropy": 0.9883, "ret": -0.129661, "capital": 8703.39, "trades": 1936, "positions": 1, "exposure": 0.01, "predictions": 5690}
data\v2.jsonl:1751:{"tick": 8660, "t": "13:34:41", "acc": 0.545, "entropy": 0.9915, "ret": -0.127552, "capital": 8724.48, "trades": 1941, "positions": 2, "exposure": 0.0439, "predictions": 5710}
data\v2.jsonl:1752:{"tick": 8665, "t": "13:39:43", "acc": 0.535, "entropy": 0.991, "ret": -0.130565, "capital": 8694.35, "trades": 1943, "positions": 2, "exposure": 0.0341, "predictions": 5730}
data\v2.jsonl:1753:{"tick": 8670, "t": "13:44:45", "acc": 0.52, "entropy": 0.9924, "ret": -0.129568, "capital": 8704.32, "trades": 1944, "positions": 3, "exposure": 0.0349, "predictions": 5750}
data\v2.jsonl:1754:{"tick": 8675, "t": "13:49:48", "acc": 0.525, "entropy": 0.9922, "ret": -0.129728, "capital": 8702.72, "trades": 1949, "positions": 2, "exposure": 0.0259, "predictions": 5770}
data\v2.jsonl:1755:{"tick": 8680, "t": "13:54:50", "acc": 0.525, "entropy": 0.9929, "ret": -0.129481, "capital": 8705.19, "trades": 1952, "positions": 3, "exposure": 0.0441, "predictions": 5790}
data\v2.jsonl:1756:{"tick": 8685, "t": "13:59:52", "acc": 0.54, "entropy": 0.9931, "ret": -0.126156, "capital": 8738.44, "trades": 1955, "positions": 2, "exposure": 0.0357, "predictions": 5810}
data\v2.jsonl:1757:{"tick": 8690, "t": "14:04:55", "acc": 0.55, "entropy": 0.9925, "ret": -0.122327, "capital": 8776.73, "trades": 1959, "positions": 3, "exposure": 0.0812, "predictions": 5830}
data\v2.jsonl:1758:{"tick": 8695, "t": "14:09:48", "acc": 0.54, "entropy": 0.992, "ret": -0.121778, "capital": 8782.22, "trades": 1961, "positions": 3, "exposure": 0.0913, "predictions": 5850}
data\v2.jsonl:1759:{"tick": 8700, "t": "14:14:50", "acc": 0.535, "entropy": 0.9893, "ret": -0.122274, "capital": 8777.26, "trades": 1966, "positions": 2, "exposure": 0.0755, "predictions": 5870}
data\v2.jsonl:1760:{"tick": 8705, "t": "14:19:53", "acc": 0.53, "entropy": 0.9877, "ret": -0.120651, "capital": 8793.49, "trades": 1968, "positions": 2, "exposure": 0.0755, "predictions": 5890}
data\v2.jsonl:1761:{"tick": 8710, "t": "14:24:56", "acc": 0.52, "entropy": 0.9897, "ret": -0.125283, "capital": 8747.17, "trades": 1971, "positions": 2, "exposure": 0.0981, "predictions": 5910}
data\v2.jsonl:1762:{"tick": 8715, "t": "14:29:58", "acc": 0.53, "entropy": 0.9876, "ret": -0.109775, "capital": 8902.25, "trades": 1974, "positions": 3, "exposure": 0.1284, "predictions": 5930}
data\v2.jsonl:1763:{"tick": 8720, "t": "14:35:01", "acc": 0.53, "entropy": 0.9835, "ret": -0.109533, "capital": 8904.67, "trades": 1975, "positions": 3, "exposure": 0.1462, "predictions": 5950}
data\v2.jsonl:1764:{"tick": 8725, "t": "14:40:04", "acc": 0.525, "entropy": 0.9851, "ret": -0.112853, "capital": 8871.47, "trades": 1981, "positions": 1, "exposure": 0.0383, "predictions": 5970}
data\v2.jsonl:1765:{"tick": 8730, "t": "14:45:06", "acc": 0.51, "entropy": 0.9874, "ret": -0.11538, "capital": 8846.2, "trades": 1984, "positions": 2, "exposure": 0.0586, "predictions": 5989}
data\v2.jsonl:1766:{"tick": 8735, "t": "14:50:10", "acc": 0.51, "entropy": 0.9876, "ret": -0.109779, "capital": 8902.21, "trades": 1987, "positions": 2, "exposure": 0.0883, "predictions": 6009}
data\v2.jsonl:1767:{"tick": 8740, "t": "14:55:12", "acc": 0.51, "entropy": 0.9893, "ret": -0.101119, "capital": 8988.81, "trades": 1993, "positions": 1, "exposure": 0.0483, "predictions": 6029}
data\v2.jsonl:1768:{"tick": 8745, "t": "15:00:15", "acc": 0.535, "entropy": 0.9898, "ret": -0.100309, "capital": 8996.91, "trades": 1997, "positions": 3, "exposure": 0.1958, "predictions": 6049}
data\v2.jsonl:1769:{"tick": 8750, "t": "15:05:17", "acc": 0.53, "entropy": 0.9903, "ret": -0.104751, "capital": 8952.49, "trades": 2002, "positions": 1, "exposure": 0.0319, "predictions": 6069}
data\v2.jsonl:1770:{"tick": 8755, "t": "15:10:19", "acc": 0.54, "entropy": 0.9905, "ret": -0.104343, "capital": 8956.57, "trades": 2003, "positions": 3, "exposure": 0.1701, "predictions": 6089}
data\v2.jsonl:1771:{"tick": 8760, "t": "15:15:21", "acc": 0.535, "entropy": 0.9879, "ret": -0.106397, "capital": 8936.03, "trades": 2007, "positions": 2, "exposure": 0.1052, "predictions": 6109}
data\v2.jsonl:1772:{"tick": 8765, "t": "15:20:24", "acc": 0.535, "entropy": 0.9886, "ret": -0.122763, "capital": 8772.37, "trades": 2009, "positions": 2, "exposure": 0.0662, "predictions": 6129}
data\v2.jsonl:1773:{"tick": 8770, "t": "15:25:26", "acc": 0.52, "entropy": 0.9896, "ret": -0.122853, "capital": 8771.47, "trades": 2014, "positions": 1, "exposure": 0.0241, "predictions": 6149}
data\v2.jsonl:1774:{"tick": 8775, "t": "15:30:28", "acc": 0.515, "entropy": 0.9861, "ret": -0.117126, "capital": 8828.74, "trades": 2018, "positions": 3, "exposure": 0.0964, "predictions": 6169}
data\v2.jsonl:1775:{"tick": 8780, "t": "15:35:30", "acc": 0.525, "entropy": 0.9874, "ret": -0.115998, "capital": 8840.02, "trades": 2021, "positions": 4, "exposure": 0.129, "predictions": 6189}
data\v2.jsonl:1776:{"tick": 8785, "t": "15:40:32", "acc": 0.505, "entropy": 0.9832, "ret": -0.12112, "capital": 8788.8, "trades": 2027, "positions": 2, "exposure": 0.0464, "predictions": 6209}
data\v2.jsonl:1777:{"tick": 8790, "t": "15:45:34", "acc": 0.525, "entropy": 0.9859, "ret": -0.12112, "capital": 8788.8, "trades": 2027, "positions": 4, "exposure": 0.0892, "predictions": 6229}
data\v2.jsonl:1778:{"tick": 8795, "t": "15:50:36", "acc": 0.495, "entropy": 0.9849, "ret": -0.120895, "capital": 8791.05, "trades": 2031, "positions": 1, "exposure": 0.024, "predictions": 6249}
data\v2.jsonl:1779:{"tick": 8800, "t": "15:55:38", "acc": 0.49, "entropy": 0.9865, "ret": -0.120427, "capital": 8795.73, "trades": 2035, "positions": 2, "exposure": 0.0691, "predictions": 6269}
data\v2.jsonl:1780:{"tick": 8805, "t": "16:00:40", "acc": 0.48, "entropy": 0.988, "ret": -0.120352, "capital": 8796.48, "trades": 2039, "positions": 3, "exposure": 0.0833, "predictions": 6289}
data\v2.jsonl:1781:{"tick": 8810, "t": "16:05:42", "acc": 0.485, "entropy": 0.9871, "ret": -0.120707, "capital": 8792.93, "trades": 2041, "positions": 4, "exposure": 0.1075, "predictions": 6309}
data\v2.jsonl:1782:{"tick": 8815, "t": "16:10:44", "acc": 0.48, "entropy": 0.9893, "ret": -0.117523, "capital": 8824.77, "trades": 2045, "positions": 3, "exposure": 0.0905, "predictions": 6329}
data\v2.jsonl:1783:{"tick": 8820, "t": "16:15:46", "acc": 0.5, "entropy": 0.987, "ret": -0.120011, "capital": 8799.89, "trades": 2048, "positions": 3, "exposure": 0.1116, "predictions": 6349}
data\v2.jsonl:1784:{"tick": 8825, "t": "16:20:49", "acc": 0.495, "entropy": 0.9862, "ret": -0.117553, "capital": 8824.47, "trades": 2052, "positions": 2, "exposure": 0.0659, "predictions": 6369}
data\v2.jsonl:1785:{"tick": 8830, "t": "16:25:51", "acc": 0.48, "entropy": 0.9841, "ret": -0.116581, "capital": 8834.19, "trades": 2054, "positions": 2, "exposure": 0.0796, "predictions": 6389}
data\v2.jsonl:1786:{"tick": 8835, "t": "16:30:52", "acc": 0.485, "entropy": 0.9843, "ret": -0.117682, "capital": 8823.18, "trades": 2057, "positions": 0, "exposure": 0, "predictions": 6409}
data\v2.jsonl:1787:{"tick": 8840, "t": "16:35:54", "acc": 0.46, "entropy": 0.9816, "ret": -0.118176, "capital": 8818.24, "trades": 2059, "positions": 2, "exposure": 0.0756, "predictions": 6429}
data\v2.jsonl:1788:{"tick": 8845, "t": "16:40:57", "acc": 0.46, "entropy": 0.982, "ret": -0.113478, "capital": 8865.22, "trades": 2065, "positions": 0, "exposure": 0, "predictions": 6449}
data\v2.jsonl:1789:{"tick": 8850, "t": "16:45:59", "acc": 0.49, "entropy": 0.9804, "ret": -0.114571, "capital": 8854.29, "trades": 2067, "positions": 3, "exposure": 0.1016, "predictions": 6469}
data\v2.jsonl:1790:{"tick": 8855, "t": "16:51:01", "acc": 0.505, "entropy": 0.9835, "ret": -0.115951, "capital": 8840.49, "trades": 2069, "positions": 1, "exposure": 0.0533, "predictions": 6489}
data\v2.jsonl:1791:{"tick": 8860, "t": "16:56:03", "acc": 0.51, "entropy": 0.9852, "ret": -0.108923, "capital": 8910.77, "trades": 2070, "positions": 3, "exposure": 0.0689, "predictions": 6509}
data\v2.jsonl:1792:{"tick": 8865, "t": "17:01:05", "acc": 0.495, "entropy": 0.984, "ret": -0.109081, "capital": 8909.19, "trades": 2071, "positions": 4, "exposure": 0.152, "predictions": 6529}
data\v2.jsonl:1793:{"tick": 8870, "t": "17:06:07", "acc": 0.49, "entropy": 0.9823, "ret": -0.108907, "capital": 8910.93, "trades": 2073, "positions": 2, "exposure": 0.1076, "predictions": 6549}
data\v2.jsonl:1794:{"tick": 8875, "t": "17:11:09", "acc": 0.48, "entropy": 0.9842, "ret": -0.104888, "capital": 8951.12, "trades": 2076, "positions": 3, "exposure": 0.1176, "predictions": 6569}
data\v2.jsonl:1795:{"tick": 8880, "t": "17:16:11", "acc": 0.485, "entropy": 0.9787, "ret": -0.116377, "capital": 8836.23, "trades": 2078, "positions": 1, "exposure": 0.0281, "predictions": 6588}
data\v2.jsonl:1796:{"tick": 8885, "t": "17:21:13", "acc": 0.485, "entropy": 0.9787, "ret": -0.117953, "capital": 8820.47, "trades": 2081, "positions": 3, "exposure": 0.0777, "predictions": 6608}
data\v2.jsonl:1797:{"tick": 8890, "t": "17:26:15", "acc": 0.51, "entropy": 0.9816, "ret": -0.116022, "capital": 8839.78, "trades": 2086, "positions": 1, "exposure": 0.026, "predictions": 6628}
data\v2.jsonl:1798:{"tick": 8895, "t": "17:31:18", "acc": 0.485, "entropy": 0.9848, "ret": -0.116186, "capital": 8838.14, "trades": 2090, "positions": 2, "exposure": 0.0491, "predictions": 6648}
data\v2.jsonl:1799:{"tick": 8900, "t": "17:36:20", "acc": 0.475, "entropy": 0.9846, "ret": -0.116439, "capital": 8835.61, "trades": 2094, "positions": 0, "exposure": 0, "predictions": 6668}
data\v2.jsonl:1800:{"tick": 8905, "t": "17:41:22", "acc": 0.455, "entropy": 0.9847, "ret": -0.116579, "capital": 8834.21, "trades": 2096, "positions": 3, "exposure": 0.0633, "predictions": 6688}
data\v2.jsonl:1801:{"tick": 8910, "t": "17:46:24", "acc": 0.465, "entropy": 0.9846, "ret": -0.116388, "capital": 8836.12, "trades": 2100, "positions": 2, "exposure": 0.0519, "predictions": 6708}
data\v2.jsonl:1802:{"tick": 8915, "t": "17:51:26", "acc": 0.455, "entropy": 0.9858, "ret": -0.116557, "capital": 8834.43, "trades": 2104, "positions": 2, "exposure": 0.0748, "predictions": 6728}
data\v2.jsonl:1803:{"tick": 8920, "t": "17:56:28", "acc": 0.445, "entropy": 0.9852, "ret": -0.115727, "capital": 8842.73, "trades": 2106, "positions": 2, "exposure": 0.0318, "predictions": 6748}
data\v2.jsonl:1804:{"tick": 8925, "t": "18:01:30", "acc": 0.47, "entropy": 0.9857, "ret": -0.115356, "capital": 8846.44, "trades": 2109, "positions": 1, "exposure": 0.0179, "predictions": 6768}
data\v2.jsonl:1805:{"tick": 8930, "t": "18:06:32", "acc": 0.475, "entropy": 0.9863, "ret": -0.113969, "capital": 8860.31, "trades": 2111, "positions": 3, "exposure": 0.1084, "predictions": 6788}
data\v2.jsonl:1806:{"tick": 8935, "t": "18:11:34", "acc": 0.495, "entropy": 0.9866, "ret": -0.109481, "capital": 8905.19, "trades": 2115, "positions": 3, "exposure": 0.1111, "predictions": 6808}
data\v2.jsonl:1807:{"tick": 8940, "t": "18:16:36", "acc": 0.475, "entropy": 0.9868, "ret": -0.110526, "capital": 8894.74, "trades": 2118, "positions": 3, "exposure": 0.1104, "predictions": 6828}
data\v2.jsonl:1808:{"tick": 8945, "t": "18:21:39", "acc": 0.51, "entropy": 0.9809, "ret": -0.108324, "capital": 8916.76, "trades": 2121, "positions": 1, "exposure": 0.035, "predictions": 6848}
data\v2.jsonl:1809:{"tick": 8950, "t": "18:26:40", "acc": 0.5, "entropy": 0.9823, "ret": -0.106605, "capital": 8933.95, "trades": 2124, "positions": 2, "exposure": 0.068, "predictions": 6868}
data\v2.jsonl:1810:{"tick": 8955, "t": "18:31:42", "acc": 0.525, "entropy": 0.981, "ret": -0.106522, "capital": 8934.78, "trades": 2125, "positions": 4, "exposure": 0.1411, "predictions": 6888}
data\v2.jsonl:1811:{"tick": 8960, "t": "18:36:44", "acc": 0.53, "entropy": 0.9847, "ret": -0.105918, "capital": 8940.82, "trades": 2128, "positions": 2, "exposure": 0.0769, "predictions": 6908}
data\v2.jsonl:1812:{"tick": 8965, "t": "18:41:47", "acc": 0.555, "entropy": 0.9825, "ret": -0.102148, "capital": 8978.52, "trades": 2132, "positions": 1, "exposure": 0.0219, "predictions": 6928}
data\v2.jsonl:1813:{"tick": 8970, "t": "18:46:49", "acc": 0.57, "entropy": 0.9859, "ret": -0.102453, "capital": 8975.47, "trades": 2134, "positions": 1, "exposure": 0.0253, "predictions": 6948}
data\v2.jsonl:1814:{"tick": 8975, "t": "18:51:52", "acc": 0.57, "entropy": 0.986, "ret": -0.099883, "capital": 9001.17, "trades": 2136, "positions": 2, "exposure": 0.0679, "predictions": 6968}
data\v2.jsonl:1815:{"tick": 8980, "t": "18:56:54", "acc": 0.57, "entropy": 0.9847, "ret": -0.099489, "capital": 9005.11, "trades": 2142, "positions": 1, "exposure": 0.036, "predictions": 6988}
data\v2.jsonl:1816:{"tick": 8985, "t": "19:01:56", "acc": 0.57, "entropy": 0.9838, "ret": -0.100041, "capital": 8999.59, "trades": 2144, "positions": 1, "exposure": 0.036, "predictions": 7008}
data\v2.jsonl:1817:{"tick": 8990, "t": "19:06:58", "acc": 0.565, "entropy": 0.9843, "ret": -0.102689, "capital": 8973.11, "trades": 2149, "positions": 0, "exposure": 0, "predictions": 7028}
data\v2.jsonl:1818:{"tick": 8995, "t": "19:12:00", "acc": 0.56, "entropy": 0.9832, "ret": -0.105683, "capital": 8943.17, "trades": 2154, "positions": 3, "exposure": 0.1108, "predictions": 7048}
data\v2.jsonl:1819:{"tick": 9000, "t": "19:17:02", "acc": 0.545, "entropy": 0.9874, "ret": -0.105818, "capital": 8941.82, "trades": 2157, "positions": 3, "exposure": 0.0577, "predictions": 7068}
data\v2.jsonl:1820:{"tick": 9005, "t": "19:22:04", "acc": 0.545, "entropy": 0.9863, "ret": -0.107868, "capital": 8921.32, "trades": 2161, "positions": 1, "exposure": 0.0178, "predictions": 7088}
data\v2.jsonl:1821:{"tick": 9010, "t": "19:27:06", "acc": 0.53, "entropy": 0.9876, "ret": -0.108193, "capital": 8918.07, "trades": 2163, "positions": 4, "exposure": 0.05, "predictions": 7108}
data\v2.jsonl:1822:{"tick": 9015, "t": "19:32:08", "acc": 0.515, "entropy": 0.9861, "ret": -0.108323, "capital": 8916.77, "trades": 2167, "positions": 2, "exposure": 0.0254, "predictions": 7128}
data\v2.jsonl:1823:{"tick": 9020, "t": "19:37:10", "acc": 0.51, "entropy": 0.9842, "ret": -0.108597, "capital": 8914.03, "trades": 2169, "positions": 2, "exposure": 0.0258, "predictions": 7148}
data\v2.jsonl:1824:{"tick": 9025, "t": "19:42:12", "acc": 0.52, "entropy": 0.9853, "ret": -0.108712, "capital": 8912.88, "trades": 2173, "positions": 2, "exposure": 0.02, "predictions": 7168}
data\v2.jsonl:1825:{"tick": 9030, "t": "19:47:15", "acc": 0.525, "entropy": 0.9888, "ret": -0.108832, "capital": 8911.68, "trades": 2176, "positions": 3, "exposure": 0.03, "predictions": 7188}
data\v2.jsonl:1826:{"tick": 9035, "t": "19:52:17", "acc": 0.505, "entropy": 0.9909, "ret": -0.10866, "capital": 8913.4, "trades": 2180, "positions": 2, "exposure": 0.0219, "predictions": 7208}
data\v2.jsonl:1827:{"tick": 9040, "t": "19:57:19", "acc": 0.495, "entropy": 0.9899, "ret": -0.10877, "capital": 8912.3, "trades": 2183, "positions": 3, "exposure": 0.0349, "predictions": 7228}
data\v2.jsonl:1828:{"tick": 9045, "t": "20:02:21", "acc": 0.49, "entropy": 0.9901, "ret": -0.109616, "capital": 8903.84, "trades": 2187, "positions": 1, "exposure": 0.01, "predictions": 7247}
data\v2.jsonl:1829:{"tick": 9050, "t": "20:07:23", "acc": 0.505, "entropy": 0.9901, "ret": -0.11036, "capital": 8896.4, "trades": 2191, "positions": 1, "exposure": 0.01, "predictions": 7267}
data\v2.jsonl:1830:{"tick": 9055, "t": "20:12:25", "acc": 0.505, "entropy": 0.9901, "ret": -0.110627, "capital": 8893.73, "trades": 2196, "positions": 1, "exposure": 0.01, "predictions": 7287}
data\v2.jsonl:1831:{"tick": 9060, "t": "20:17:27", "acc": 0.5, "entropy": 0.9884, "ret": -0.110653, "capital": 8893.47, "trades": 2201, "positions": 2, "exposure": 0.02, "predictions": 7307}
data\v2.jsonl:1832:{"tick": 9065, "t": "20:22:30", "acc": 0.5, "entropy": 0.9897, "ret": -0.110954, "capital": 8890.46, "trades": 2206, "positions": 2, "exposure": 0.02, "predictions": 7327}
data\v2.jsonl:1833:{"tick": 9070, "t": "20:27:32", "acc": 0.49, "entropy": 0.989, "ret": -0.110872, "capital": 8891.28, "trades": 2209, "positions": 3, "exposure": 0.03, "predictions": 7347}
data\v2.jsonl:1834:{"tick": 9075, "t": "20:32:34", "acc": 0.455, "entropy": 0.9895, "ret": -0.110946, "capital": 8890.54, "trades": 2212, "positions": 3, "exposure": 0.03, "predictions": 7367}
data\v2.jsonl:1835:{"tick": 9080, "t": "20:37:36", "acc": 0.455, "entropy": 0.9902, "ret": -0.111526, "capital": 8884.74, "trades": 2216, "positions": 2, "exposure": 0.02, "predictions": 7387}
data\v2.jsonl:1836:{"tick": 9085, "t": "20:42:38", "acc": 0.455, "entropy": 0.9878, "ret": -0.11239, "capital": 8876.1, "trades": 2219, "positions": 1, "exposure": 0.01, "predictions": 7407}
data\v2.jsonl:1837:{"tick": 9090, "t": "20:47:40", "acc": 0.465, "entropy": 0.9903, "ret": -0.112352, "capital": 8876.48, "trades": 2220, "positions": 3, "exposure": 0.03, "predictions": 7427}
data\v2.jsonl:1838:{"tick": 9095, "t": "20:52:42", "acc": 0.48, "entropy": 0.9884, "ret": -0.112441, "capital": 8875.59, "trades": 2225, "positions": 4, "exposure": 0.04, "predictions": 7447}
data\v2.jsonl:1839:{"tick": 9100, "t": "20:57:44", "acc": 0.475, "entropy": 0.9857, "ret": -0.112335, "capital": 8876.65, "trades": 2230, "positions": 1, "exposure": 0.01, "predictions": 7467}
data\v2.jsonl:1840:{"tick": 9105, "t": "21:02:46", "acc": 0.475, "entropy": 0.9823, "ret": -0.112317, "capital": 8876.83, "trades": 2233, "positions": 4, "exposure": 0.04, "predictions": 7487}
data\v2.jsonl:1841:{"tick": 9110, "t": "21:07:48", "acc": 0.495, "entropy": 0.9827, "ret": -0.112198, "capital": 8878.02, "trades": 2236, "positions": 4, "exposure": 0.04, "predictions": 7507}
data\v2.jsonl:1842:{"tick": 9115, "t": "21:12:50", "acc": 0.525, "entropy": 0.9817, "ret": -0.111244, "capital": 8887.56, "trades": 2240, "positions": 4, "exposure": 0.04, "predictions": 7527}
data\v2.jsonl:1843:{"tick": 9120, "t": "21:17:52", "acc": 0.525, "entropy": 0.983, "ret": -0.110046, "capital": 8899.54, "trades": 2245, "positions": 3, "exposure": 0.0339, "predictions": 7547}
data\v2.jsonl:1844:{"tick": 9125, "t": "21:22:54", "acc": 0.53, "entropy": 0.9846, "ret": -0.110844, "capital": 8891.56, "trades": 2250, "positions": 0, "exposure": 0, "predictions": 7567}
data\v2.jsonl:1845:{"tick": 9130, "t": "21:27:56", "acc": 0.53, "entropy": 0.982, "ret": -0.110975, "capital": 8890.25, "trades": 2252, "positions": 3, "exposure": 0.03, "predictions": 7587}
data\v2.jsonl:1846:{"tick": 9135, "t": "21:32:58", "acc": 0.55, "entropy": 0.9842, "ret": -0.110812, "capital": 8891.88, "trades": 2256, "positions": 3, "exposure": 0.03, "predictions": 7607}
data\v2.jsonl:1847:{"tick": 9140, "t": "21:38:01", "acc": 0.55, "entropy": 0.9847, "ret": -0.1101, "capital": 8899.0, "trades": 2261, "positions": 1, "exposure": 0.01, "predictions": 7627}
data\v2.jsonl:1848:{"tick": 9145, "t": "21:43:03", "acc": 0.535, "entropy": 0.9848, "ret": -0.109863, "capital": 8901.37, "trades": 2263, "positions": 3, "exposure": 0.03, "predictions": 7647}
data\v2.jsonl:1849:{"tick": 9150, "t": "21:48:05", "acc": 0.55, "entropy": 0.985, "ret": -0.109901, "capital": 8900.99, "trades": 2268, "positions": 2, "exposure": 0.02, "predictions": 7667}
data\v2.jsonl:1850:{"tick": 9155, "t": "21:53:09", "acc": 0.56, "entropy": 0.9848, "ret": -0.109818, "capital": 8901.82, "trades": 2271, "positions": 3, "exposure": 0.03, "predictions": 7687}
data\v2.jsonl:1851:{"tick": 9160, "t": "21:58:11", "acc": 0.545, "entropy": 0.9862, "ret": -0.110533, "capital": 8894.67, "trades": 2274, "positions": 3, "exposure": 0.03, "predictions": 7707}
data\v2.jsonl:1852:{"tick": 9165, "t": "22:03:13", "acc": 0.5, "entropy": 0.986, "ret": -0.110223, "capital": 8897.77, "trades": 2278, "positions": 3, "exposure": 0.03, "predictions": 7726}
data\v2.jsonl:1853:{"tick": 9170, "t": "22:08:15", "acc": 0.505, "entropy": 0.9863, "ret": -0.109845, "capital": 8901.55, "trades": 2282, "positions": 2, "exposure": 0.02, "predictions": 7746}
data\v2.jsonl:1854:{"tick": 9175, "t": "22:13:17", "acc": 0.515, "entropy": 0.9858, "ret": -0.109855, "capital": 8901.45, "trades": 2285, "positions": 1, "exposure": 0.01, "predictions": 7766}
data\v2.jsonl:1855:{"tick": 9180, "t": "22:18:19", "acc": 0.52, "entropy": 0.9844, "ret": -0.11019, "capital": 8898.1, "trades": 2287, "positions": 2, "exposure": 0.02, "predictions": 7786}
data\v2.jsonl:1856:{"tick": 9185, "t": "22:23:21", "acc": 0.51, "entropy": 0.9853, "ret": -0.109879, "capital": 8901.21, "trades": 2290, "positions": 2, "exposure": 0.02, "predictions": 7806}
data\v2.jsonl:1857:{"tick": 9190, "t": "22:28:23", "acc": 0.51, "entropy": 0.9874, "ret": -0.109757, "capital": 8902.43, "trades": 2292, "positions": 3, "exposure": 0.03, "predictions": 7826}
data\v2.jsonl:1858:{"tick": 9195, "t": "22:33:26", "acc": 0.52, "entropy": 0.9845, "ret": -0.110056, "capital": 8899.44, "trades": 2293, "positions": 3, "exposure": 0.03, "predictions": 7846}
data\v2.jsonl:1859:{"tick": 9200, "t": "22:38:28", "acc": 0.515, "entropy": 0.9834, "ret": -0.110308, "capital": 8896.92, "trades": 2296, "positions": 0, "exposure": 0, "predictions": 7866}
data\v2.jsonl:1860:{"tick": 9205, "t": "22:43:30", "acc": 0.5, "entropy": 0.9872, "ret": -0.110331, "capital": 8896.69, "trades": 2299, "positions": 2, "exposure": 0.02, "predictions": 7886}
data\v2.jsonl:1861:{"tick": 9210, "t": "22:48:32", "acc": 0.5, "entropy": 0.9841, "ret": -0.110539, "capital": 8894.61, "trades": 2301, "positions": 3, "exposure": 0.03, "predictions": 7906}
data\v2.jsonl:1862:{"tick": 9215, "t": "22:53:34", "acc": 0.505, "entropy": 0.9861, "ret": -0.110749, "capital": 8892.51, "trades": 2305, "positions": 2, "exposure": 0.02, "predictions": 7926}
data\v2.jsonl:1863:{"tick": 9220, "t": "22:58:36", "acc": 0.515, "entropy": 0.9903, "ret": -0.110856, "capital": 8891.44, "trades": 2310, "positions": 1, "exposure": 0.01, "predictions": 7946}
data\v2.jsonl:1864:{"tick": 9225, "t": "23:03:38", "acc": 0.495, "entropy": 0.9888, "ret": -0.111369, "capital": 8886.31, "trades": 2314, "positions": 3, "exposure": 0.03, "predictions": 7966}
data\v2.jsonl:1865:{"tick": 9230, "t": "23:08:40", "acc": 0.48, "entropy": 0.989, "ret": -0.111429, "capital": 8885.71, "trades": 2319, "positions": 2, "exposure": 0.02, "predictions": 7986}
data\v2.jsonl:1866:{"tick": 9235, "t": "23:13:42", "acc": 0.475, "entropy": 0.9888, "ret": -0.111374, "capital": 8886.26, "trades": 2321, "positions": 3, "exposure": 0.03, "predictions": 8006}
data\v2.jsonl:1867:{"tick": 9240, "t": "23:18:44", "acc": 0.485, "entropy": 0.9872, "ret": -0.111276, "capital": 8887.24, "trades": 2326, "positions": 0, "exposure": 0, "predictions": 8026}
data\v2.jsonl:1868:{"tick": 9245, "t": "23:23:46", "acc": 0.475, "entropy": 0.9874, "ret": -0.111325, "capital": 8886.75, "trades": 2328, "positions": 3, "exposure": 0.03, "predictions": 8046}
data\v2.jsonl:1869:{"tick": 9250, "t": "23:28:48", "acc": 0.47, "entropy": 0.9863, "ret": -0.11155, "capital": 8884.5, "trades": 2332, "positions": 1, "exposure": 0.01, "predictions": 8066}
data\v2.jsonl:1870:{"tick": 9255, "t": "23:33:51", "acc": 0.465, "entropy": 0.9859, "ret": -0.111638, "capital": 8883.62, "trades": 2337, "positions": 1, "exposure": 0.01, "predictions": 8086}
data\v2.jsonl:1871:{"tick": 9260, "t": "23:38:52", "acc": 0.46, "entropy": 0.9849, "ret": -0.111774, "capital": 8882.26, "trades": 2340, "positions": 1, "exposure": 0.01, "predictions": 8106}
data\v2.jsonl:1872:{"tick": 9265, "t": "23:43:54", "acc": 0.45, "entropy": 0.9804, "ret": -0.111688, "capital": 8883.12, "trades": 2344, "positions": 2, "exposure": 0.02, "predictions": 8126}
data\v2.jsonl:1873:{"tick": 9270, "t": "23:48:56", "acc": 0.45, "entropy": 0.9853, "ret": -0.111937, "capital": 8880.63, "trades": 2348, "positions": 0, "exposure": 0, "predictions": 8146}
data\v2.jsonl:1874:{"tick": 9275, "t": "23:53:59", "acc": 0.49, "entropy": 0.9826, "ret": -0.112022, "capital": 8879.78, "trades": 2350, "positions": 2, "exposure": 0.02, "predictions": 8166}
data\v2.jsonl:1875:{"tick": 9280, "t": "23:59:01", "acc": 0.48, "entropy": 0.9806, "ret": -0.112244, "capital": 8877.56, "trades": 2353, "positions": 2, "exposure": 0.02, "predictions": 8186}
data\v2.jsonl:1876:{"tick": 9285, "t": "00:04:03", "acc": 0.48, "entropy": 0.9809, "ret": -0.11279, "capital": 8872.1, "trades": 2356, "positions": 3, "exposure": 0.03, "predictions": 8206}
data\v2.jsonl:1877:{"tick": 9290, "t": "00:09:05", "acc": 0.46, "entropy": 0.9819, "ret": -0.112896, "capital": 8871.04, "trades": 2358, "positions": 3, "exposure": 0.03, "predictions": 8226}
data\v2.jsonl:1878:{"tick": 9295, "t": "00:14:07", "acc": 0.475, "entropy": 0.9823, "ret": -0.113251, "capital": 8867.49, "trades": 2359, "positions": 4, "exposure": 0.04, "predictions": 8246}
data\v2.jsonl:1879:{"tick": 9300, "t": "00:19:09", "acc": 0.47, "entropy": 0.9806, "ret": -0.113049, "capital": 8869.51, "trades": 2363, "positions": 3, "exposure": 0.03, "predictions": 8266}
data\v2.jsonl:1880:{"tick": 9305, "t": "00:24:11", "acc": 0.47, "entropy": 0.9786, "ret": -0.11315, "capital": 8868.5, "trades": 2367, "positions": 2, "exposure": 0.02, "predictions": 8286}
data\v2.jsonl:1881:{"tick": 9310, "t": "00:29:13", "acc": 0.47, "entropy": 0.9812, "ret": -0.113342, "capital": 8866.58, "trades": 2369, "positions": 3, "exposure": 0.03, "predictions": 8306}
data\v2.jsonl:1882:{"tick": 9315, "t": "00:34:16", "acc": 0.475, "entropy": 0.9825, "ret": -0.113292, "capital": 8867.08, "trades": 2371, "positions": 3, "exposure": 0.03, "predictions": 8325}
data\v2.jsonl:1883:{"tick": 9320, "t": "00:39:18", "acc": 0.47, "entropy": 0.984, "ret": -0.113558, "capital": 8864.42, "trades": 2374, "positions": 3, "exposure": 0.03, "predictions": 8345}
data\v2.jsonl:1884:{"tick": 9325, "t": "00:44:20", "acc": 0.46, "entropy": 0.9852, "ret": -0.113827, "capital": 8861.73, "trades": 2379, "positions": 1, "exposure": 0.01, "predictions": 8365}
data\v2.jsonl:1885:{"tick": 9330, "t": "00:49:22", "acc": 0.455, "entropy": 0.9856, "ret": -0.113958, "capital": 8860.42, "trades": 2383, "positions": 3, "exposure": 0.03, "predictions": 8385}
data\v2.jsonl:1886:{"tick": 9335, "t": "00:54:24", "acc": 0.46, "entropy": 0.9818, "ret": -0.114028, "capital": 8859.72, "trades": 2386, "positions": 3, "exposure": 0.03, "predictions": 8405}
data\v2.jsonl:1887:{"tick": 9340, "t": "00:59:26", "acc": 0.48, "entropy": 0.9815, "ret": -0.113503, "capital": 8864.97, "trades": 2387, "positions": 4, "exposure": 0.04, "predictions": 8425}
data\v2.jsonl:1888:{"tick": 9345, "t": "01:04:28", "acc": 0.46, "entropy": 0.9859, "ret": -0.113755, "capital": 8862.45, "trades": 2389, "positions": 3, "exposure": 0.03, "predictions": 8445}
data\v2.jsonl:1889:{"tick": 9350, "t": "01:09:30", "acc": 0.49, "entropy": 0.9862, "ret": -0.111356, "capital": 8886.44, "trades": 2394, "positions": 3, "exposure": 0.03, "predictions": 8465}
data\v2.jsonl:1890:{"tick": 9355, "t": "01:14:32", "acc": 0.51, "entropy": 0.9895, "ret": -0.111435, "capital": 8885.65, "trades": 2397, "positions": 4, "exposure": 0.04, "predictions": 8485}
data\v2.jsonl:1891:{"tick": 9360, "t": "01:19:34", "acc": 0.51, "entropy": 0.9894, "ret": -0.111137, "capital": 8888.63, "trades": 2399, "positions": 2, "exposure": 0.02, "predictions": 8505}
data\v2.jsonl:1892:{"tick": 9365, "t": "01:24:39", "acc": 0.52, "entropy": 0.9853, "ret": -0.111166, "capital": 8888.34, "trades": 2400, "positions": 4, "exposure": 0.04, "predictions": 8525}
data\v2.jsonl:1893:{"tick": 9365, "t": "01:31:28", "acc": 0.5, "entropy": 0.9885, "ret": -0.111137, "capital": 8888.63, "trades": 1000, "positions": 0, "exposure": 0, "predictions": 8}
data\v2.jsonl:1894:{"tick": 9370, "t": "01:36:30", "acc": 0.5, "entropy": 0.9843, "ret": -0.111137, "capital": 8888.63, "trades": 1000, "positions": 3, "exposure": 0.03, "predictions": 28}
data\v2.jsonl:1895:{"tick": 9375, "t": "01:41:32", "acc": 0.4583, "entropy": 0.9851, "ret": -0.1111, "capital": 8889.0, "trades": 1004, "positions": 3, "exposure": 0.03, "predictions": 48}
data\v2.jsonl:1896:{"tick": 9380, "t": "01:46:34", "acc": 0.4706, "entropy": 0.9834, "ret": -0.111224, "capital": 8887.76, "trades": 1009, "positions": 2, "exposure": 0.02, "predictions": 68}
data\v2.jsonl:1897:{"tick": 9385, "t": "01:51:36", "acc": 0.4886, "entropy": 0.9849, "ret": -0.11122, "capital": 8887.8, "trades": 1011, "positions": 3, "exposure": 0.03, "predictions": 88}
data\v2.jsonl:1898:{"tick": 9390, "t": "01:56:38", "acc": 0.4722, "entropy": 0.9824, "ret": -0.111334, "capital": 8886.66, "trades": 1015, "positions": 1, "exposure": 0.01, "predictions": 108}
data\v2.jsonl:1899:{"tick": 9395, "t": "02:01:41", "acc": 0.4688, "entropy": 0.9819, "ret": -0.111506, "capital": 8884.94, "trades": 1020, "positions": 1, "exposure": 0.01, "predictions": 128}
data\v2.jsonl:1900:{"tick": 9400, "t": "02:06:46", "acc": 0.473, "entropy": 0.9841, "ret": -0.111988, "capital": 8880.12, "trades": 1023, "positions": 2, "exposure": 0.02, "predictions": 148}
data\v2.jsonl:1901:{"tick": 9405, "t": "02:11:47", "acc": 0.4583, "entropy": 0.9838, "ret": -0.112111, "capital": 8878.89, "trades": 1027, "positions": 2, "exposure": 0.02, "predictions": 168}
data\v2.jsonl:1902:{"tick": 9410, "t": "02:16:49", "acc": 0.4574, "entropy": 0.9858, "ret": -0.112307, "capital": 8876.93, "trades": 1029, "positions": 3, "exposure": 0.03, "predictions": 188}
data\v2.jsonl:1903:{"tick": 9415, "t": "02:21:51", "acc": 0.485, "entropy": 0.986, "ret": -0.112274, "capital": 8877.26, "trades": 1032, "positions": 2, "exposure": 0.02, "predictions": 208}
data\v2.jsonl:1904:{"tick": 9420, "t": "02:26:53", "acc": 0.495, "entropy": 0.9877, "ret": -0.112274, "capital": 8877.26, "trades": 1032, "positions": 2, "exposure": 0.02, "predictions": 228}
data\v2.jsonl:1905:{"tick": 9425, "t": "02:31:56", "acc": 0.495, "entropy": 0.9824, "ret": -0.112103, "capital": 8878.97, "trades": 1033, "positions": 3, "exposure": 0.03, "predictions": 248}
data\v2.jsonl:1906:{"tick": 9430, "t": "02:36:58", "acc": 0.5, "entropy": 0.9807, "ret": -0.112081, "capital": 8879.19, "trades": 1037, "positions": 3, "exposure": 0.03, "predictions": 268}
data\v2.jsonl:1907:{"tick": 9435, "t": "02:42:00", "acc": 0.5, "entropy": 0.9825, "ret": -0.111321, "capital": 8886.79, "trades": 1039, "positions": 3, "exposure": 0.03, "predictions": 288}
data\v2.jsonl:1908:{"tick": 9440, "t": "02:47:04", "acc": 0.52, "entropy": 0.9825, "ret": -0.111374, "capital": 8886.26, "trades": 1042, "positions": 3, "exposure": 0.03, "predictions": 308}
data\v2.jsonl:1909:{"tick": 9445, "t": "02:52:07", "acc": 0.52, "entropy": 0.9828, "ret": -0.111609, "capital": 8883.91, "trades": 1045, "positions": 3, "exposure": 0.03, "predictions": 328}
data\v2.jsonl:1910:{"tick": 9450, "t": "02:57:09", "acc": 0.51, "entropy": 0.9868, "ret": -0.11165, "capital": 8883.5, "trades": 1048, "positions": 1, "exposure": 0.01, "predictions": 348}
data\v2.jsonl:1911:{"tick": 9455, "t": "03:02:12", "acc": 0.54, "entropy": 0.9886, "ret": -0.111479, "capital": 8885.21, "trades": 1051, "positions": 1, "exposure": 0.01, "predictions": 368}

 succeeded in 452ms:
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

 succeeded in 475ms:
# V2 洹쒖튃2 "湲곗뼲 怨듦컙??怨④퀬猷??ъ슜?대씪" 援ы쁽 寃利?
## 寃利????肄붾뱶

### EMANormalizer
```python
class EMANormalizer:
    def __init__(self, n, alpha=0.01):
        self.mean = np.zeros(n)
        self.var = np.ones(n)   # 珥덇린媛?1.0
        self.warm = 0

    def update(self, x):
        self.warm += 1
        a = max(self.alpha, 1.0 / self.warm)  # warm-up
        self.mean = (1 - a) * self.mean + a * x
        diff = x - self.mean
        self.var = (1 - a) * self.var + a * diff * diff

    def normalize(self, x):
        return (x - self.mean) / (sqrt(self.var) + 1e-8)
```

### OnlinePredictor ???듭떖 硫붾え由?諛몃윴??```python
def __init__(self, n=28, lr=0.003, base_l2=0.001, memory_alpha=2.0):
    self.w = np.random.randn(n) * 0.0001  # 珥덇린 媛以묒튂 ~0??媛源뚯?
    self.l2_per_feat = np.full(n, base_l2)  # 珥덇린 L2 = 0.001 洹좊벑
    self.norm = EMANormalizer(n)
    self.feature_importance = np.ones(n) / n  # 珥덇린 洹좊벑

def _rebalance_memory(self):
    """Rule 2: Adaptive L2 to keep feature importance entropy high."""
    imp = np.abs(self.w) * np.sqrt(self.norm.var + 1e-8)
    imp_sum = imp.sum()
    if imp_sum < 1e-10:
        self.feature_importance = np.ones(self.n) / self.n
        self.entropy_history.append(1.0)
        return  # 珥덇린: 媛以묒튂 嫄곗쓽 0?대㈃ 洹좊벑 泥섎━

    p = imp / imp_sum
    self.feature_importance = p

    # ?뷀듃濡쒗뵾 怨꾩궛
    safe_p = np.clip(p, 1e-10, 1.0)
    entropy = -np.sum(safe_p * np.log(safe_p))
    max_entropy = np.log(self.n)  # log(28) ??3.33
    self.entropy_history.append(entropy / max_entropy)  # 0~1 ?뺢퇋??
    # ?곸쓳??L2: 怨쇱슜 ?쇱쿂 ?⑤꼸??利앷?
    uniform = 1.0 / self.n  # 1/28 ??0.0357
    excess = np.maximum(p - uniform, 0)  # uniform 珥덇낵遺꾨쭔
    self.l2_per_feat = self.base_l2 * (1.0 + self.memory_alpha * excess * self.n)
    # memory_alpha=2.0, n=28 ??理쒕? ?뱀닔 = 1 + 2 * 1 * 28 = 57
```

### calibration (洹쒖튃2媛 洹쒖튃3??誘몄튂???곹뼢)
```python
def calibration(self):
    acc = self.direction_accuracy()   # ?덉륫 ?뺥솗??0~1
    ent = self.memory_entropy()       # ?뷀듃濡쒗뵾 0~1
    warmup = min(n_samples / 50, 1.0)
    return acc * ent * warmup  # ?뷀듃濡쒗뵾媛 ??쑝硫?calibration????븘吏???嫄곕옒 異뺤냼
```

## ?꾩옱 ?ㅼ륫媛?- ?뷀듃濡쒗뵾: ~17% (0.177)
- ?뚮컢???? ~15 (50 誘몃쭔)
- 媛以묒튂: ?遺遺?0??媛源뚯? (0.0001 珥덇린??

## 寃利?吏덈Ц
1. **adaptive L2媛 ?ㅼ젣濡?洹좊벑?붾? 留뚮뱶?붽??** ??excess媛 ?묒닔???쇱쿂留??⑤꼸?곌? ?щ씪媛怨? ?뚯닔(誘몄궗?? ?쇱쿂??base_l2 洹몃?濡? ?닿쾬留뚯쑝濡?誘몄궗???쇱쿂??媛以묒튂媛 ?щ씪媛?붽?? L2??媛以묒튂瑜?0?쇰줈 諛?대궡???뺢퇋?붿씤?? ?⑤꼸?곕? 以꾩씤?ㅺ퀬 媛以묒튂媛 而ㅼ???
2. **珥덇린 ?뷀듃濡쒗뵾 17%媛 ?뺤긽?멸??** ??w 珥덇린媛?random(0.0001), var 珥덇린媛?1.0. imp = |w| * sqrt(var). ?쒕뜡 珥덇린?붿쓽 遺덇퇏?쇱꽦???뷀듃濡쒗뵾瑜???텛??寃껋씤媛?
3. **?섑븰???ㅻ쪟**: imp = |w| * sqrt(var)?먯꽌 var???쇱쿂??遺꾩궛. ?뺢퇋?붾맂 紐⑤뜽?먯꽌 以묒슂?꾨? ?대젃寃??뺤쓽?섎뒗 寃껋씠 ?щ컮瑜멸?? ?뺢퇋????x_n = (x - mean) / sqrt(var)?대?濡? ?ㅼ젣 ?쇱쿂 湲곗뿬??= w_i * x_n_i = w_i * (x_i - mean_i) / sqrt(var_i). ?곕씪???쇱쿂 以묒슂?꾨뒗 |w_i| (?뺢퇋????媛以묒튂)?ъ빞吏, |w_i| * sqrt(var_i)媛 ?꾨땶 寃??꾨땶媛?
4. **?뷀듃濡쒗뵾媛 calibration??怨깊빐吏??援ъ“**: ?뷀듃濡쒗뵾 17%?대㈃ calibration = 0.5 * 0.17 * 0.3 = 0.026. ?대뒗 0.05 ?꾧퀎媛?誘몃쭔?대씪 嫄곕옒瑜??꾩쟾??李⑤떒. ?뚮컢??湲곌컙???뷀듃濡쒗뵾媛 ?щ씪媛吏 ?딆쑝硫??곸썝??嫄곕옒 遺덇??
5. **_rebalance_memory媛 SGD ?낅뜲?댄듃 ?댄썑???몄텧??*: w媛 ?대? ?낅뜲?댄듃????l2_per_feat瑜?蹂寃쏀븯誘濡? 蹂寃쎈맂 l2???ㅼ쓬 ?ㅽ뀦?먯빞 ?곸슜. ??1-step lag媛 臾몄젣?멸??

媛?吏덈Ц??????섑븰??洹쇨굅? ?④퍡 CORRECT/INCORRECT/PROBLEMATIC?쇰줈 遺꾨쪟?댁＜?몄슂.

codex
현재 코드 기준으로는 두 가지가 분명합니다. 하나는 V2를 그대로 손보는 수준으로는 context 분화가 안 된다는 점이고, 다른 하나는 대시보드 통합은 단순 포트 추가가 아니라 응답 스키마와 렌더러까지 맞춰야 해서 생각보다 공수가 든다는 점입니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content docs/models_architecture_260420.md | Select-Object -Skip 35 -First 60' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content docs/models_architecture_260420.md | Select-Object -Skip 200 -First 85' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content docs/triarb_review_request_260420.md | Select-Object -Skip 128 -First 25' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 396ms:

### 6.1 MODELS 由ъ뒪???섏젙

```python
MODELS = [
    {"id": "bollrev", "name": "BollRev (Bollinger Reversion)", "port": 8895, "color": "#ffaa44"},
    {"id": "oracle",  "name": "Oracle (LSTM Prediction)",     "port": 8897, "color": "#44aaff"},
    {"id": "brooks",  "name": "Brooks (Parker Brooks)",       "port": 8898, "color": "#aa66ff"},
    {"id": "triarb",  "name": "TriArb (Pairs Arbitrage)",     "port": 8899, "color": "#66ff99"},
]
```

### 6.2 Render ?⑥닔 ?ㅼ씠諛?
- `renderBollRev(id,d,color)`
- `renderOracle(id,d,color)` (援?renderV2 由щ꽕??
- `renderBrooks(id,d,color)` (援?renderV3 由щ꽕??
- `renderTriArb(id,d,color)` (?좉퇋)

怨듯넻 ?ㅽ궎留?以?섑븯誘濡?BollRev/TriArb??renderBrooks 援ъ“ 李몄“ 媛??

### 6.3 ?좉퇋 移대뱶 ?꾩젽

- BollRev: **BB ??/ RSI** ?곹깭 ?쒖떆 (?먯궛蹂??꾩옱 ????꾩튂)
- TriArb: **?꾩옱 spread z-score / correlation** ?쒖떆 (asset pair蹂?

---

## 7. Startup ?먮룞?쒖옉 (`start_unified.bat`)

```bat
@echo off
title Trading Value - Unified Dashboard
cd /d "C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value"

echo === Trading Value - 4-Model Dashboard ===

echo [1/5] Starting BollRev (port 8895)...
start /min "" py -3.12 -u scripts\bollrev.py

echo [2/5] Starting Oracle (port 8897)...
start /min "" py -3.12 -u scripts\oracle.py

echo [3/5] Starting Brooks (port 8898)...
start /min "" py -3.12 -u scripts\brooks.py

echo [4/5] Starting TriArb (port 8899)...
start /min "" py -3.12 -u scripts\triarb.py

echo [5/5] Starting Unified Dashboard (port 8900)...
timeout /t 5 /nobreak >nul
start "" http://localhost:8900
py -3.12 -u scripts\dashboard_unified.py

pause
```

---

## 8. 援ы쁽 ?쒖꽌 (?ㅽ뻾 濡쒕뱶留?

### Phase 1 ??由щ꽕?대컢 (Claude ?대떦, 臾댁쐞??
1. `v2.py` ??`oracle.py` (Engine ?대옒?ㅻ챸 `V2Engine` ??`OracleEngine`)
2. `v3.py` ??`brooks.py` (`V3Engine` ??`BrooksEngine`)
3. `tournament.py` ??`Projects/archive/trading-value-tournament/scout.py` (?닿?)
4. data ?뚯씪 由щ꽕??(`v2_state.npz` ??`oracle_state.npz` ??
5. `dashboard_unified.py` MODELS + render ?⑥닔 ?낅뜲?댄듃
6. `start_unified.bat` ?낅뜲?댄듃
7. 援щЦ 寃利?+ 湲곕룞 ?뺤씤

### Phase 2 ??BollRev 援ы쁽 (Codex ?대떦)
- 吏?쒖꽌: `docs/bollrev_260420.md`
- ?곗텧臾? `scripts/bollrev.py` + ??쒕낫??`renderBollRev` 異붽?

### Phase 3 ??TriArb 援ы쁽 (Codex ?대떦)
- 吏?쒖꽌: `docs/triarb_260420.md`
- ?곗텧臾? `scripts/triarb.py` + ??쒕낫??`renderTriArb` 異붽?

### Phase 4 ???듯빀 寃利?(Claude 由щ럭)
- 4媛?紐⑤뜽 ?숈떆 湲곕룞
- ??쒕낫?쒖뿉??4媛????뺤긽 ?뚮뜑
- 媛?紐⑤뜽 ?먭린?꾧껐??(crash ???ㅻⅨ 紐⑤뜽 ?곹뼢 ?놁쓬)
- 24?쒓컙 ?섏씠???몃젅?대뵫 ???깃낵 ?섏튂??
---

## 9. Codex ?꾨떖 ???꾩닔 媛??

 succeeded in 456ms:

## 3. ?뚯씪쨌?ы듃쨌?붾젆?좊━ 留ㅽ븨

### 3.1 由щ꽕?대컢 (湲곗〈 ?뚯씪)

| 湲곗〈 ?뚯씪 | ?좉퇋 ?뚯씪 | ?ы듃 | ?곹깭 |
|-----------|-----------|------|------|
| `scripts/tournament.py` | `Projects/archive/trading-value-tournament/scout.py` | ?먭린 | 李멸퀬???닿? |
| `scripts/v2.py` | `scripts/oracle.py` | 8897 | 由щ꽕?꾨쭔 |
| `scripts/v3.py` | `scripts/brooks.py` | 8898 | 由щ꽕?꾨쭔 |
| `scripts/dashboard_unified.py` | ?숈씪 | 8900 | 紐⑤뜽 紐⑸줉 ?섏젙 |
| `scripts/start_unified.bat` | ?숈씪 | ??| ?④퀎 ?쒖꽌 ?섏젙 |

### 3.2 ?좉퇋 ?뚯씪

| ?좉퇋 ?뚯씪 | ?ы듃 | ??븷 |
|-----------|------|------|
| `scripts/bollrev.py` | 8895 (Tournament ?ы듃 ?ъ궗?? | Bollinger Reversion ?붿쭊 |
| `scripts/triarb.py` | 8899 | Triangular/Pairs Arb ?붿쭊 |

### 3.3 ?곗씠???뚯씪 (媛?紐⑤뜽 ?낅┰)

```
data/
?쒋?? bollrev.jsonl           # tick log
?쒋?? bollrev_state.npz       # ?먮낯/?ъ????쇳겕/tick_count ???쒋?? bollrev_memory.json     # ContextMemory + trade_log
?쒋?? oracle.jsonl            # (湲곗〈 v2 ?뚯씪 由щ꽕?? v2.jsonl ??oracle.jsonl)
?쒋?? oracle_state.npz        # (v2_state.npz ??oracle_state.npz)
?쒋?? brooks.jsonl            # (v3.jsonl ??brooks.jsonl)
?쒋?? brooks_state.npz        # (v3_state.npz ??brooks_state.npz)
?쒋?? brooks_memory.json      # (v3_memory.json ??brooks_memory.json)
?쒋?? triarb.jsonl
?쒋?? triarb_state.npz
?붴?? triarb_memory.json
```

**以묒슂**: 湲곗〈 v2/v3 ?곗씠???뚯씪? 由щ꽕?? 湲곗〈 tournament ?곗씠?곕뒗 archive濡??닿? ??`data/tournament_*` ??젣.

---

## 4. 怨듯넻 ?꾪궎?띿쿂 (紐⑤뱺 4媛?紐⑤뜽??以??

### 4.1 ?쒖? 紐⑤뱢 怨꾩링 (?붿쭊蹂??대?)

```
scripts/<model>.py
?쒋?? Constants (DATA_DIR, DASH_PORT, TICK_SEC, VARIANTS_CONFIG ??
?쒋?? IndicatorEngine (static methods ??BB/RSI/EMA/ATR/VWAP ??
?쒋?? Signal functions (classify_state, entry_valid ??
?쒋?? ContextVector / TradeRecord (dataclasses)
?쒋?? ContextMemory (k-NN EV + 釉붾옓由ъ뒪??+ ?ъ씠利?遺?ㅽ듃)
?쒋?? Position (dataclass)
?쒋?? VariantPM (variant蹂??ъ???留ㅻ땲?)
?쒋?? Engine (main loop, assets 횞 variants)
?쒋?? DashboardHandler (http.server ??/api/state)
?붴?? main()
```

**?먯튃**: `scripts/brooks.py` (援?`v3.py`)??援ъ“瑜?洹몃?濡?蹂듭젣. ?좉퇋 紐⑤뜽 2媛쒕룄 ?숈씪 怨꾩링.


 succeeded in 358ms:
- `/api/state` snapshot??JSON 吏곷젹??媛?ν븳 媛믩쭔 諛섑솚?섎뒗吏 ?뺤씤.

### 8.4 ??쒕낫???듯빀
- `dashboard_unified.py`??`triarb` proxy媛 8899 ?ы듃濡?異붽??섏뿀?붿? ?뺤씤.
- `renderTriArb()`媛 Pair Status, HTF ?곹깭, TriArb ?꾩슜 ?좏샇 源붾븣湲? memory EV, PnL chart, two-leg position display瑜??뚮뜑?섎뒗吏 ?뺤씤.
- 湲곗〈 `tournament`, `v2`, `v3` ?ㅻ뒗 ?좎??? architecture 臾몄꽌??rename 紐⑺몴(`bollrev`, `oracle`, `brooks`)? ?꾩옱 repo ?곹깭媛 ?ㅻⅤ誘濡? ?ш린?쒕뒗 湲곗〈 ??쒕낫???명솚?깆쓣 ?곗꽑??

## 9. 異붽? 踰꾧렇 ?뚯뒪??留ㅽ븨

| Test | 寃利?紐⑹쟻 |
|------|----------|
| `test_delta_neutral_size_and_cap` | ???덇렇 USDT notional ?숈씪??+ per-leg $500 cap |
| `test_short_ratio_pnl_sign_and_cost` | short_ratio PnL 遺??+ fee/slippage 李④컧 |
| `test_long_ratio_pnl_sign_and_cost` | long_ratio PnL 遺??+ fee/slippage 李④컧 |
| `test_exit_priority_corr_break` | correlation break媛 ?ㅻⅨ exit蹂대떎 ?곗꽑?섎뒗吏 |
| `test_control_variant_memory_off` | control variant?먯꽌 memory blacklist媛 李⑤떒?섏? ?딅뒗吏 |
| `test_pair_alignment_metrics` | ?쒕줈 ?ㅻⅨ timestamp series媛 index intersection?쇰줈 ?뺣젹?섎뒗吏 |
| `test_snapshot_json_serializable_with_position` | open position ?ы븿 snapshot JSON 吏곷젹??媛???щ? |
| `test_state_roundtrip_positions_memory` | state/memory/trade_log/open position save/load roundtrip |

## 10. ?먯껜 由щ럭 寃곕줎

- ?꾩옱 ?뚯뒪?몄? 肄붾뱶 寃??踰붿쐞?먯꽌??李⑤떒湲?踰꾧렇瑜?諛쒓껄?섏? 紐삵븿.
- 吏?쒖꽌 ?鍮??섎룄?곸쑝濡??щ씪吏?遺遺꾩? ??媛吏??
  - `scripts/brooks.py`媛 ?놁뼱 `scripts/v3.py`瑜?Brooks template?쇰줈 李몄“.

exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "rg -n \"function renderV2|function renderV3|function renderTriArb|renderV2\\(|renderV3\\(|renderTriArb\\(|case 'v2'|case 'v3'|case 'triarb'|Object.entries\\(data\\)\" scripts/dashboard_unified.py" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 334ms:
293:function renderV2(id,d,color){
364:function renderV3(id,d,color){
503:function renderTriArb(id,d,color){
642:      else if(id==='triarb')html+=renderTriArb(id,m,m.color);
643:      else if(id==='v3')html+=renderV3(id,m,m.color);
644:      else html+=renderV2(id,m,m.color);

exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/dashboard_unified.py | Select-Object -Skip 288 -First 90' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 401ms:
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

  let html='<div class="model-section"><div class="model-hdr" style="border-left:3px solid '+color+'"><h2><span class="'+(online?'live':'live offline')+'"></span> '+d.name+' <span style="font-size:10px;color:#ff8800;margin-left:6px">?섏닔猷?0.21% RT | ?덈쾭由ъ? 1~'+maxLev+'x | Long+Short</span></h2><div class="stats">';
  html+='<span>?뺥솗?? <b class="'+(acc>0.52?'grn':acc>0.48?'ylw':'red')+'">'+fmt(acc)+'</b></span>';
  html+='<span>?뷀듃濡쒗뵾: <b class="'+(ent>0.8?'grn':'ylw')+'">'+fmt(ent,1)+'</b></span>';
  html+='<span>?섏씡: <b class="'+(ret>0?'grn':'red')+'">'+fmt(ret)+'</b></span>';
  html+='<span>嫄곕옒: <b>'+totalTrades+'</b>??/span>';
  html+='</div></div><div class="model-body">';

  // Metrics
  html+='<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-bottom:12px">';
  html+='<div class="mc"><label>洹쒖튃1: ?덉륫 ?뺥솗??/label><div class="val '+(acc>0.52?'cyn':'dim')+'">'+fmt(acc)+'</div></div>';
  html+='<div class="mc"><label>洹쒖튃2: 湲곗뼲 ?뷀듃濡쒗뵾</label><div class="val '+(ent>0.8?'ylw':'dim')+'">'+fmt(ent,1)+'</div></div>';
  html+='<div class="mc"><label>洹쒖튃3: ?쒖닔??/label><div class="val '+(ret>0?'grn':'red')+'">'+fmt(ret)+'</div></div>';
  html+='<div class="mc"><label>?먮낯</label><div class="val">'+$(cap)+'</div></div>';
  html+='<div class="mc"><label>珥?嫄곕옒</label><div class="val">'+totalTrades+'<span style="font-size:11px;color:#555">??/span></div></div>';
  html+='<div class="mc"><label>耳덈━ / ?덈쾭由ъ?</label><div class="val dim">'+fmt(kelly)+' / '+(notional>0?notional.toFixed(1):'0')+'x</div></div>';
  html+='</div>';

  // Charts
  html+='<div class="charts">';
  html+='<div class="chart-box"><h3>?먯씡 (?섏닔猷?李④컧)</h3><canvas id="cv-v2-pnl"></canvas></div>';
  html+='<div class="chart-box"><h3>?덉륫 ?뺥솗??/h3><canvas id="cv-v2-acc"></canvas></div>';
  html+='</div>';

  // Memory map (bigger)
  html+='<div style="font-size:11px;color:#888;margin-bottom:4px;font-weight:bold">湲곗뼲 怨듦컙 留?('+((s.feature_names||[]).length)+'媛??쇱쿂)</div>';
  html+='<div id="v2-feat" style="display:flex;flex-wrap:wrap;gap:3px;padding:8px;background:#0a0a10;border:1px solid #1a1a24;border-radius:6px"></div>';

  // Positions
  html+='<div style="margin-top:10px"><div style="font-size:11px;color:#888;margin-bottom:4px;font-weight:bold">?ъ???/div>';
  const pos=s.positions||[];
  if(!pos.length)html+='<span class="dim" style="font-size:11px">?ъ????놁쓬</span>';
  else{
    html+='<div style="font-size:11px">';
    pos.forEach(p=>{
      html+='<div style="padding:3px 0;border-bottom:1px solid #111"><span class="'+(p.dir==='long'?'grn':'red')+'" style="font-weight:bold">'+p.dir.toUpperCase()+'</span> '+p.asset+' @$'+p.entry+' <span class="dim">留덉쭊 '+(p.size*100).toFixed(1)+'%</span> <span class="org">'+p.lev+'x</span> <span class="dim">'+p.time+'</span></div>';
    });
    html+='</div>';
  }
  html+='</div>';

  // Trade log
  const tlog=s.trade_log||[];
  html+='<div style="margin-top:10px"><div style="font-size:11px;color:#888;margin-bottom:4px;font-weight:bold">嫄곕옒 ?댁뿭</div>';
  if(tlog.length){
    html+='<div class="tlog">';
    tlog.slice(-20).reverse().forEach(t=>{
      html+='<div class="tlog-e"><span class="'+(t.net>0?'grn':'red')+'" style="font-weight:bold">'+t.dir+'</span> '+t.asset+' $'+t.entry+' ??$'+t.exit+' <span class="dim">留덉쭊 '+(t.size*100).toFixed(1)+'%</span> <span class="org">'+(t.lev||1)+'x</span> ?쒖씡=<span class="'+(t.net>0?'grn':'red')+'">'+fmt(t.net)+'</span> ?붽퀬='+$(t.capital)+'</div>';
    });
    html+='</div>';
  }else html+='<span class="dim" style="font-size:11px">嫄곕옒 ?놁쓬 (?뚮컢??以?</span>';
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

  const htfTF=s.htf_timeframe||'1h';

exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content scripts/_analyze_results.py -TotalCount 120' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 373ms:
"""V2 + Tournament 寃곌낵 遺꾩꽍"""
import json
import statistics

# ==== V2 遺꾩꽍 ====
v2 = []
with open('C:/Users/haj/projects/subagent-orchestrator/Projects/Trading Value/data/v2.jsonl') as f:
    for line in f:
        v2.append(json.loads(line))

print(f'[V2] 珥??덉퐫?? {len(v2)}')

# session reset 李얘린 (tick??媛먯냼?섎뒗 吏??
resets = [0]
for i in range(1, len(v2)):
    if v2[i]['tick'] < v2[i-1]['tick']:
        resets.append(i)
resets.append(len(v2))
print(f'[V2] ?몄뀡 ?? {len(resets)-1}')

# 留덉?留??몄뀡
last_session = v2[resets[-2]:]
print(f'[V2] 留덉?留??몄뀡 ?덉퐫?? {len(last_session)}, tick {last_session[0]["tick"]} -> {last_session[-1]["tick"]}')
last = v2[-1]
print(f'[V2] 理쒖쥌 ?곹깭: tick={last["tick"]} acc={last["acc"]:.3f} entropy={last["entropy"]:.3f} ret={last["ret"]*100:+.2f}% capital={last["capital"]:.0f} trades={last["trades"]}')

accs = [r['acc'] for r in last_session]
rets = [r['ret'] for r in last_session]
trades = [r['trades'] for r in last_session]

print(f'[V2] acc: avg {sum(accs)/len(accs):.3f} min {min(accs):.3f} max {max(accs):.3f} stdev {statistics.stdev(accs):.3f}')
print(f'[V2] ret: first {rets[0]*100:+.2f}% last {rets[-1]*100:+.2f}% max {max(rets)*100:+.2f}% min {min(rets)*100:+.2f}%')
print(f'[V2] trades: {trades[-1] - trades[0]}??({len(last_session)} ticks)')

print()
print('[V2] 援ш컙蹂?異붿씠:')
step = max(1, len(last_session)//15)
for i in range(0, len(last_session), step):
    r = last_session[i]
    print(f'  tick {r["tick"]:5d} | acc {r["acc"]:.3f} | ent {r["entropy"]:.3f} | ret {r["ret"]*100:+7.2f}% | trades {r["trades"]:5d}')

# ==== Tournament 遺꾩꽍 ====
print()
print('='*70)
eff = []
with open('C:/Users/haj/projects/subagent-orchestrator/Projects/Trading Value/data/effectiveness.jsonl') as f:
    for line in f:
        eff.append(json.loads(line))

print(f'[Tournament] 珥??덉퐫?? {len(eff)}')
last_t = eff[-1]
print(f'[Tournament] 理쒖쥌: best {last_t["best"]:+.2f} | top10_avg {last_t["top10_avg"]:+.3f} | avg {last_t["avg"]:+.3f} | worst {last_t["worst"]:+.2f} | +ve {last_t["positive_pct"]}% | trades {last_t["trades"]}')

bests = [r['best'] for r in eff]
top10s = [r['top10_avg'] for r in eff]
avgs = [r['avg'] for r in eff]
worsts = [r['worst'] for r in eff]
poss = [r['positive_pct'] for r in eff]

print(f'[Tournament] best: min {min(bests):+.2f} max {max(bests):+.2f} avg {sum(bests)/len(bests):+.2f}')
print(f'[Tournament] top10_avg: avg {sum(top10s)/len(top10s):+.3f} max {max(top10s):+.3f}')
print(f'[Tournament] ?꾩껜 ?됯퇏(5000媛?: avg {sum(avgs)/len(avgs):+.3f} min {min(avgs):+.3f}')
print(f'[Tournament] worst: min {min(worsts):+.2f} (理쒖븙 variant)')
print(f'[Tournament] positive_pct: avg {sum(poss)/len(poss):.1f}% max {max(poss):.1f}% min {min(poss):.1f}%')

print()
print('[Tournament] ?쒓컙 寃쎄낵 異붿씠:')
step = max(1, len(eff)//20)
for i in range(0, len(eff), step):
    r = eff[i]
    print(f'  t {r["t"]} | best {r["best"]:+6.2f} | top10 {r["top10_avg"]:+.3f} | avg {r["avg"]:+.3f} | +ve {r["positive_pct"]:4.1f}% | trades {r["trades"]:6d}')

exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'py -3.12 scripts/_analyze_results.py' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
2026-04-21T03:04:58.869469Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 0.3 seconds
Output:
No installed Python found!

 exited 1 in 332ms:
No installed Python found!

codex
런타임 별칭 `py -3.12`는 이 셸에서 바로 잡히지 않습니다. 분석은 계속 가능하지만, 이 워크스페이스의 실제 실행 명령은 문서와 다를 수 있어 런타임 검증 항목으로 남겨야 합니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content data/v2.jsonl -Tail 3' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content docs/triarb_260420.md | Select-Object -Skip 780 -First 18' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content docs/models_architecture_260420.md | Select-Object -Skip 58 -First 12' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 347ms:
{"tick": 9445, "t": "02:52:07", "acc": 0.52, "entropy": 0.9828, "ret": -0.111609, "capital": 8883.91, "trades": 1045, "positions": 3, "exposure": 0.03, "predictions": 328}
{"tick": 9450, "t": "02:57:09", "acc": 0.51, "entropy": 0.9868, "ret": -0.11165, "capital": 8883.5, "trades": 1048, "positions": 1, "exposure": 0.01, "predictions": 348}
{"tick": 9455, "t": "03:02:12", "acc": 0.54, "entropy": 0.9886, "ret": -0.111479, "capital": 8885.21, "trades": 1051, "positions": 1, "exposure": 0.01, "predictions": 368}

 succeeded in 445ms:
    {"id": "triarb",  "name": "TriArb (Pairs Ratio)",         "port": 8899, "color": "#66ffaa"},
]
```

#### B.4.2 renderTriArb(id, d, color) ?⑥닔

`renderBrooks(id,d,color)`??援ъ“瑜?蹂듭궗????援먯껜:

1. **?ㅻ뜑**: `"TriArb ??Pairs Ratio Arbitrage (2-leg delta-neutral)"`
2. **Pair Status 移대뱶** (?뱀뀡 理쒖긽?? ?먯궛 移대뱶 ???:
   - 4媛??섏뼱 媛곴컖:
     - `{pair_id}: z={z:.2f} ?={corr:.2f} ratio={r:.5f}`
     - 諛곌꼍?? `|z| ??2` ??二쇳솴, `? < 0.4` ??鍮④컯, ?섎㉧吏 珥덈줉
3. **HTF ?곹깭** (?묎쾶 ?쒖떆): BTC 1h bullish/bearish/mild
4. **?좏샇 源붾븣湲?*: 而щ읆??TriArb ?꾩슜?쇰줈
   - `寃??/ ?곴?李⑤떒 / ?띾룄李⑤떒 / CV李⑤떒 / HTF李⑤떒 / 硫붾え由ъ감??/ ?ㅽ뻾 / ?ㅽ뻾瑜?
5. **硫붾え由?EV ?뚯씠釉?*: 洹몃?濡??ъ궗??6. **PnL 李⑦듃 + ?ъ???嫄곕옒 濡쒓렇**: ?ъ궗?? ???ъ????쒖떆??two-leg 援ъ“濡?
   ```

 succeeded in 388ms:
data/
?쒋?? bollrev.jsonl           # tick log
?쒋?? bollrev_state.npz       # ?먮낯/?ъ????쇳겕/tick_count ???쒋?? bollrev_memory.json     # ContextMemory + trade_log
?쒋?? oracle.jsonl            # (湲곗〈 v2 ?뚯씪 由щ꽕?? v2.jsonl ??oracle.jsonl)
?쒋?? oracle_state.npz        # (v2_state.npz ??oracle_state.npz)
?쒋?? brooks.jsonl            # (v3.jsonl ??brooks.jsonl)
?쒋?? brooks_state.npz        # (v3_state.npz ??brooks_state.npz)
?쒋?? brooks_memory.json      # (v3_memory.json ??brooks_memory.json)
?쒋?? triarb.jsonl
?쒋?? triarb_state.npz
?붴?? triarb_memory.json
```

exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-ChildItem .. -Name' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-ChildItem ..\\.. -Name" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "rg --files ..\\.. | rg \"workspace-knowledge-index\\\\dist\\\\index\\.js"'$|project-status'"\\\\current\\.md"'$"' in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 443ms:
archive
intelligent-delegation
novel
personas
shortlive-shop-helper
telegram-digest
Trading Value
vibe-web
AI-SECURITY-INSTRUCTION.md
DEVELOPMENT-BIBLE.md
security-checklist-guide.md

 succeeded in 481ms:
-p
.claude
.gemini
.github
.knowledge
.npm-cache
.pytest_cache
.tq-journal
claude-sub-specs
config
discussions
docs
game-design-director
node_modules
output
packages
project-status
Projects
skills
subagent-runs
tests
workspace-knowledge-index
.gitignore
.mcp.json
AGENTS.md
chain.json
CLAUDE.md
CLAUDE.md.bak
CLAUDE_new.md
deep-thinking-tokens-guide.md
dummy-spec.json
gemini-subagent-orchestrator.skill
intelligent_ai_delegation_detailed_ko.md
package.json
plan-discussion-system.md
plan-queue-runner-ts.md
problem-resolution-log.md
README.md
wki.config.json

2026-04-21T03:05:15.721095Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 0.5 seconds
Output:

 exited 1 in 490ms:
codex
상위 리포지토리에는 `workspace-knowledge-index`와 `project-status`가 있습니다. 워크스페이스 루트가 다르게 잡혀 있었던 문제였고, 상위 루트 기준으로 필수 파일까지 확인한 뒤 결론을 마무리하겠습니다.
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "node ..\\..\\workspace-knowledge-index\\dist\\index.js index" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
exec
"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-Content ..\\..\\project-status\\current.md" in C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value
 succeeded in 420ms:
# Project Status ??Current

> ???뚯씪? 紐⑤뱺 AI ?붿쭊(Claude, Codex/GPT, Gemini)??李몄“?⑸땲??
> ???대뜑?먯꽌 ?묒뾽?섎뒗 AI?????뚯씪???쎄퀬 ?꾩옱 ?곹깭瑜??뚯븙?섏꽭??
> ?꾨즺 湲곕줉? project-status/2026-Q2.md??吏곸젒 異붽??쒕떎.
> current.md?먮뒗 ?꾨즺 ?대젰??湲곕줉?섏? ?딅뒗??
> ???꾨즺 ?대젰: project-status/2026-Q2.md

---

## Project: Subagent Orchestrator

硫??AI ?붿쭊(Claude, Codex/GPT, Gemini)??議곗쑉?섎뒗 ?ㅼ??ㅽ듃?덉씠???쒖뒪??

## ?듭떖 援ъ꽦 ?붿냼

| 援ъ꽦 ?붿냼 | ?곹깭 | 寃쎈줈 |
|---|---|---|
| TS ?곗쿂 (primary) | ?꾨즺 | `packages/launcher/` |
| PS ?곗쿂 (legacy fallback) | ?좎? | `skills/codex-subagent-orchestrator/scripts/` |
| WKI (Workspace Knowledge Index) | ?꾨즺 | `workspace-knowledge-index/` |
| Claude ?ㅼ??ㅽ듃?덉씠??(/sub) | ?꾨즺 | `skills/claude-subagent-orchestrator/` |
| 硫?곗뿏吏??ㅼ??ㅽ듃?덉씠??(/submix) | ?꾨즺 | `.claude/skills/submix/` |
| Gemini ?ㅼ??ㅽ듃?덉씠??| ?꾨즺 | `skills/gemini-subagent-orchestrator/` |
| Codex ?ㅼ??ㅽ듃?덉씠??| ?꾨즺 | `skills/codex-subagent-orchestrator/` |
| **?좊줎 ?쒖뒪??(/discuss)** | **Phase 1~3 ?꾨즺** | `packages/launcher/src/discussion/` |
| **???щ꼫 TS** | **Phase 1~2 ?꾨즺** | `packages/launcher/src/queue/` |
| **踰붿슜 ?ㅺ퀎 ?붾젆??(/design)** | **?꾨즺** | `skills/design-director/` + `.claude/skills/design/` |
| **寃뚯엫 湲고쉷 ?붾젆??(/gdd)** | **?꾨즺** | `skills/game-design-director/` + `.claude/skills/gdd/` |
| **Intelligent Delegation ?꾨젅?꾩썙??* | **?꾨즺** | `packages/launcher/src/` + `config/capabilities/` + 湲고쉷??`Projects/intelligent-delegation/` |

## ?ㅼ쓬 ?묒뾽 (?곗꽑?쒖쐞 ??

1. **?섎Ⅴ?뚮굹 援?? ??Phase 17 過-1 Land 吏꾩엯 (援?? ?먯뿰?꾩깮 濡쒕뱶留?**
   - Phase 11: 寃쎌젣 ?명봽??(goods/P2P/NPC/?꾧뎄) ???꾨즺
   - Phase 12 / 12-B: SNN 寃쎌젣 ?곌껐 + ?깅뒫 理쒖쟻??+ NPC SNN?????꾨즺
   - Phase 13~16: ?듭튂/?멸툑/?앸웾/怨듦났洹쇰줈 ??16-H 寃쎌젣 ?덉젙?붾줈 ?섎졃 (Hard 5吏??PASS, 2026-04-20)
   - **Phase 17 吏꾪뻾 ?덉젙**: 過-1 Land Charter ?ㅺ퀎 以???LandCell(臾쇰━ 怨듦컙) + Territory(吏諛??ъ쁺) ?댁썝 遺꾨━, 2D tile grid, 2.5D/3D 洹몃옒???뺤옣 ?鍮?   - 濡쒕뱶留? **過-1 Land ??過-2 Faction ??過-3 Struggle ??過-4 Nation** (?먯뿰 ?꾩깮)
2. **WKI 異붽? 媛쒖꽑** ??Mean nDCG 0.819, Line-scoped 0.655 (Min 0.630)
3. **/design domains/software/ ?ㅼ쟾 ?ъ슜**

## ?섎Ⅴ?뚮굹 援?? ?ㅺ퀎 ?꾪솴 (2026-04-12 ?꾨즺)

| Charter | 踰꾩쟾 | ?곹깭 |
|---------|------|:----:|
| world-ontology | Phase A ?섏젙 ?꾨즺 | ??|
| constitution | 8??27議?| ??|
| economy-whitepaper | 11??| ??|
| physis-charter-v2 | v2.4 | ??|
| tick-daemon-charter | v1.1 | ??|
| humanity-charter | H1~H6 | ??|
| death-reincarnation-charter | v1 | ??|
| order-charter | v1 | ??|
| society-charter-draft | v1.1 | ??|
| secret-rumor-evidence-charter | v1.1 | ??|
| **personabrain-snn-charter** | **v3.1** | ??|

PersonaBrain SNN: 50M ?대윴, 12?대윭占쏙옙??V-L-S-B-A-T-C-G-F-I-D-P), 湲곗뼲 5?좏삎+留앷컖 寃쎌젣?? 20K紐?CPU 10ms

## 二쇱슂 紐낅졊??
```bash
# TS ?곗쿂 ?ㅽ뻾
node packages/launcher/dist/cli.js --spec <spec.json>

# WKI ?몃뜳??node workspace-knowledge-index/dist/index.js index

# WKI 寃??node workspace-knowledge-index/dist/index.js search "<query>" --top 5

# WKI ?곹깭 ?뺤씤
node workspace-knowledge-index/dist/index.js status

# WKI 寃???덉쭏 ?됯?
node workspace-knowledge-index/dist/index.js eval workspace-knowledge-index/eval/gold-set-v2.json

# ???щ꼫 ?ㅽ뻾
node packages/launcher/dist/queue/queue-cli.js --config <queue.json>
node packages/launcher/dist/queue/queue-cli.js --config <queue.json> --max-polls 10

# ?좊줎 ?ㅽ뻾
node packages/launcher/dist/discussion/discuss-cli.js "二쇱젣"
node packages/launcher/dist/discussion/discuss-cli.js --auto "二쇱젣"

# WKI lock 臾몄젣 ??rm .knowledge/.wki.lock
```

## 臾몄젣 ?닿껐

臾몄젣 諛쒖깮 ??`problem-resolution-log.md`瑜?癒쇱? ?뺤씤?섏꽭?? 8嫄댁쓽 ?닿껐 ?щ?媛 湲곕줉?섏뼱 ?덉뒿?덈떎.

## 洹쒖튃

- **?몄뀡 ?쒖옉 ??WKI ?몃뜳???꾩닔** ??泥??묒뾽 ?꾩뿉 `node workspace-knowledge-index/dist/index.js index` 瑜?1???ㅽ뻾. ?ㅻⅨ AI/?몄뀡??蹂寃쎌궗??씠 諛섏쁺?? 蹂寃??놁쑝硫?利됱떆 諛섑솚 (0珥?.
- ?뚯씪 ??젣 ??諛섎뱶???ъ슜?먯뿉寃??뺤씤 ??吏꾪뻾
- ???대뜑?먮뒗 蹂꾨룄 ?꾨줈?앺듃 ?대뜑媛 議댁옱?????덉쓬 (game-design-director, trading-quest ??
- Evidence 湲곕줉? ?꾩닔 ??寃곌낵 蹂닿퀬 ?꾩뿉 諛섎뱶??湲곕줉
---

## Mostria (vibe-web) ?꾨즺 ?대젰

??`project-status/2026-Q2.md` 李몄“. `git log --oneline Projects/vibe-web/` 濡쒕룄 ?뺤씤 媛??

 succeeded in 1035ms:
Indexed: 0 files, 0 chunks, 0 symbols (87ms)
[wki] git diff failed: spawnSync C:\WINDOWS\system32\cmd.exe EPERM
[wki] git diff failed: spawnSync C:\WINDOWS\system32\cmd.exe EPERM
[wki] git diff failed: spawnSync C:\WINDOWS\system32\cmd.exe EPERM
[wki] git ls-files failed: spawnSync C:\WINDOWS\system32\cmd.exe EPERM
[wki] Git change detection failed. Running full index as fallback.
[wki] git diff failed: spawnSync C:\WINDOWS\system32\cmd.exe EPERM
[wki] git diff failed: spawnSync C:\WINDOWS\system32\cmd.exe EPERM
[wki] git diff failed: spawnSync C:\WINDOWS\system32\cmd.exe EPERM
[wki] git ls-files failed: spawnSync C:\WINDOWS\system32\cmd.exe EPERM
[scanner] Failed to read directory: C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value Error: EPERM: operation not permitted, scandir 'C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value\.pytest_cache'
    at read (node:fs:1473:35)
    at readdirSyncRecursive (node:fs:1491:5)
    at Object.readdirSync (node:fs:1565:12)
    at Scanner.scan (file:///C:/Users/haj/projects/subagent-orchestrator/workspace-knowledge-index/dist/core/scanner.js:84:26)
    at Indexer.indexIncremental (file:///C:/Users/haj/projects/subagent-orchestrator/workspace-knowledge-index/dist/core/indexer.js:263:38)
    at cmdIndex (file:///C:/Users/haj/projects/subagent-orchestrator/workspace-knowledge-index/dist/index.js:261:45)
    at handleCommand (file:///C:/Users/haj/projects/subagent-orchestrator/workspace-knowledge-index/dist/index.js:993:19)
    at main (file:///C:/Users/haj/projects/subagent-orchestrator/workspace-knowledge-index/dist/index.js:1042:11)
    at file:///C:/Users/haj/projects/subagent-orchestrator/workspace-knowledge-index/dist/index.js:1044:1
    at ModuleJob.run (node:internal/modules/esm/module_job:430:25) {
  errno: -4048,
  code: 'EPERM',
  syscall: 'scandir',
  path: 'C:\\Users\\haj\\projects\\subagent-orchestrator\\Projects\\Trading Value\\.pytest_cache'
}
[wki] git rev-parse failed: spawnSync C:\WINDOWS\system32\cmd.exe EPERM
[wki] git rev-parse failed: spawnSync C:\WINDOWS\system32\cmd.exe EPERM
[wki] git status failed: spawnSync C:\WINDOWS\system32\cmd.exe EPERM
[wki] git diff failed: spawnSync C:\WINDOWS\system32\cmd.exe EPERM
[wki] git diff failed: spawnSync C:\WINDOWS\system32\cmd.exe EPERM
[wki] git ls-files failed: spawnSync C:\WINDOWS\system32\cmd.exe EPERM

codex
1. **Position**: Phase 0는 **Phase 1 Charter 진입은 가능**합니다. 다만 이는 “설계 착수 허가” 수준이지 “구현 착수 충분조건”은 아닙니다. 현재 제약으로도 Oracle은 만들 수 있지만, 그 실체는 `numpy/pandas` 기반의 **context-aware 통계 엔진**이어야지 문서에 적힌 식의 **LSTM Oracle**이어선 안 됩니다. V2의 Rule 2만 걷어내는 패치로는 손실 원인은 줄여도 핵심 결함인 **context 분화 부재**는 못 고칩니다.

2. **Reasoning**:
- `scripts/v2.py`는 단일 선형 모델 + `entropy` 기반 재균등화 + `calibration` 게이팅이 묶여 있어, 학습된 가중치를 다시 평탄화하는 구조입니다. 이건 수정 가능하지만 context별 좋은/나쁜 패턴 분리는 못 합니다.
- 현재 스택으로 가능한 Oracle은 `V2 feature pipeline + V3/TriArb의 k-NN ContextMemory + 보상/패널티 업데이트` 조합입니다. 이 방향은 구현 가능하지만, “딥러닝형 Oracle”은 5일 내 현실적이지 않습니다.
- `dashboard_unified.py` 통합은 `MODELS` 한 줄 추가로 끝나지 않습니다. 지금은 `renderV2/renderV3/renderTriArb`가 하드코딩이라 Oracle state schema가 V2와 다르면 **0.5~1.5일**, 대략 **총 공수 +25~40%**는 붙습니다.
- `npz+jsonl`만으로는 context-aware 학습 상태 보존이 애매합니다. 실제 `v3.py`/`triarb.py`는 `*_state.npz` + `*_memory.json`을 씁니다. 즉 “V3/TriArb와 일관”하다는 전제가 현재 코드와 맞지 않습니다.
- 재활용률은 인프라 기준으론 괜찮습니다. `ContextMemory/k-NN` **70~85%**, `HTFFilter` **50~70%**, 엔진/스냅샷/save-load 골격 **60~70%**. 하지만 V3/TriArb의 실제 신호 로직 재활용은 낮아서 **전체 체감 재활용률은 40~55% 정도**로 보는 게 현실적입니다.

3. **Concerns**:
- Phase 1 전에 최소한 **예측 타깃**을 못 박아야 합니다: 다음 1-bar 수익률인지, 방향 확률인지, multi-horizon score인지.
- **상태 영속화 계약**은 Phase 3로 미루면 안 됩니다. memory를 `npz`에 억지로 넣을지, `oracle_memory.json`을 허용할지 먼저 정해야 합니다.
- 포트/`v2.py` 덮어쓰기 여부는 Phase 3로 미뤄도 됩니다. 그건 운영 packaging 문제이지 학습 아키텍처 문제는 아닙니다.
- `67%+ / 5일 +4%`는 설계 목표로는 너무 공격적입니다. 받아들일 수는 있어도 **커밋 가능한 구현 목표**로 두면 과장입니다.

4. **Recommendation**:
- **Phase 1로는 들어가되**, Charter에서 4개를 먼저 고정하십시오: `Oracle의 모델 정의(비-LSTM)`, `예측 타깃/학습 라벨`, `dashboard snapshot schema`, `memory persistence 형식`.
- 구현은 `V2 feature engine` 위에 `V3 ContextMemory`를 이식하는 방향이 가장 현실적입니다. V2 수정만으로 끝내지 말고, 새 `oracle.py`로 병행 검증한 뒤 8897 교체를 결정하는 게 안전합니다.

[POSITION: Phase 1 조건부 진입 가능, 하지만 Oracle은 “numpy 기반 context-aware 통계 엔진”으로 재정의해야 하며 포트보다 학습목표·상태스키마를 먼저 고정해야 함]
tokens used
82,905
1. **Position**: Phase 0는 **Phase 1 Charter 진입은 가능**합니다. 다만 이는 “설계 착수 허가” 수준이지 “구현 착수 충분조건”은 아닙니다. 현재 제약으로도 Oracle은 만들 수 있지만, 그 실체는 `numpy/pandas` 기반의 **context-aware 통계 엔진**이어야지 문서에 적힌 식의 **LSTM Oracle**이어선 안 됩니다. V2의 Rule 2만 걷어내는 패치로는 손실 원인은 줄여도 핵심 결함인 **context 분화 부재**는 못 고칩니다.

2. **Reasoning**:
- `scripts/v2.py`는 단일 선형 모델 + `entropy` 기반 재균등화 + `calibration` 게이팅이 묶여 있어, 학습된 가중치를 다시 평탄화하는 구조입니다. 이건 수정 가능하지만 context별 좋은/나쁜 패턴 분리는 못 합니다.
- 현재 스택으로 가능한 Oracle은 `V2 feature pipeline + V3/TriArb의 k-NN ContextMemory + 보상/패널티 업데이트` 조합입니다. 이 방향은 구현 가능하지만, “딥러닝형 Oracle”은 5일 내 현실적이지 않습니다.
- `dashboard_unified.py` 통합은 `MODELS` 한 줄 추가로 끝나지 않습니다. 지금은 `renderV2/renderV3/renderTriArb`가 하드코딩이라 Oracle state schema가 V2와 다르면 **0.5~1.5일**, 대략 **총 공수 +25~40%**는 붙습니다.
- `npz+jsonl`만으로는 context-aware 학습 상태 보존이 애매합니다. 실제 `v3.py`/`triarb.py`는 `*_state.npz` + `*_memory.json`을 씁니다. 즉 “V3/TriArb와 일관”하다는 전제가 현재 코드와 맞지 않습니다.
- 재활용률은 인프라 기준으론 괜찮습니다. `ContextMemory/k-NN` **70~85%**, `HTFFilter` **50~70%**, 엔진/스냅샷/save-load 골격 **60~70%**. 하지만 V3/TriArb의 실제 신호 로직 재활용은 낮아서 **전체 체감 재활용률은 40~55% 정도**로 보는 게 현실적입니다.

3. **Concerns**:
- Phase 1 전에 최소한 **예측 타깃**을 못 박아야 합니다: 다음 1-bar 수익률인지, 방향 확률인지, multi-horizon score인지.
- **상태 영속화 계약**은 Phase 3로 미루면 안 됩니다. memory를 `npz`에 억지로 넣을지, `oracle_memory.json`을 허용할지 먼저 정해야 합니다.
- 포트/`v2.py` 덮어쓰기 여부는 Phase 3로 미뤄도 됩니다. 그건 운영 packaging 문제이지 학습 아키텍처 문제는 아닙니다.
- `67%+ / 5일 +4%`는 설계 목표로는 너무 공격적입니다. 받아들일 수는 있어도 **커밋 가능한 구현 목표**로 두면 과장입니다.

4. **Recommendation**:
- **Phase 1로는 들어가되**, Charter에서 4개를 먼저 고정하십시오: `Oracle의 모델 정의(비-LSTM)`, `예측 타깃/학습 라벨`, `dashboard snapshot schema`, `memory persistence 형식`.
- 구현은 `V2 feature engine` 위에 `V3 ContextMemory`를 이식하는 방향이 가장 현실적입니다. V2 수정만으로 끝내지 말고, 새 `oracle.py`로 병행 검증한 뒤 8897 교체를 결정하는 게 안전합니다.

[POSITION: Phase 1 조건부 진입 가능, 하지만 Oracle은 “numpy 기반 context-aware 통계 엔진”으로 재정의해야 하며 포트보다 학습목표·상태스키마를 먼저 고정해야 함]
