# Round 2 — Topic 2 (Ablation 파일 구조) 집중 논의

## Round 1 수렴 결과
- **T1 BollRev 편입**: AGREE (제외) — 확정, 재논의 불필요
- **T2 Ablation 파일 구조**: PARTIAL — A 2표(Claude opus, Gemini) vs D 1표(Codex)

## Round 1 각 엔진 입장 요약

### Claude opus — A (`scripts/v2_ablation.py` V2 포크)
- Rule 2는 v2.py:302 `self._rebalance_memory()` 단일 라인. 포크에서 flag로 감싸면 실질 수정 3-5 LOC.
- Charter 조항 I "oracle.py 격리"는 입법 취지(live 환경 보호)가 본질. 포크도 8897 live와 격리되므로 취지 충족.
- archive 규칙 미리 정의, commit hash 고정 필수.

### Codex gpt-5.4 — D (v2.py import + subclass/no-op override, 파일명 `oracle_rule2_ablation.py`)
- v2.py 무수정 + 동일 코드경로 재사용. 공수 6-10h/리스크 2 (A는 8-12h/리스크 3).
- ML "isolated experiment harness" 정석 패턴. Charter 문언(파일명)은 `oracle_rule2_ablation.py`로 해결.
- `LOG_PATH / STATE_PATH / DASH_PORT` variant별 재바인딩 필수. predictor 주입은 smoke test로 잠궈야 함.

### Gemini 2.5-pro — A (`scripts/v2_ablation.py`)
- 실험 순수성: 단일 변수(Rule 2) 외 모든 환경 동일해야. 미확정 Oracle 골격(B) 노이즈.
- Charter 맥락적 격리: "live 운영(v2.py)에 영향 주지 않는 독립 프로세스" 해석.
- archive 라이프사이클 강제 필요.

---

## 집중 쟁점 Q1-Q4

### Q1 — A(포크)의 drift 리스크
v2.py 포크 시 commit hash 고정만으로 drift 방지 충분한가?
- 48h 동안 v2.py 수정 가능성은 낮으나 bug fix 가능성은 있음.
- drift 방지 대안: branch 고정? read-only archive? 아니면 commit hash 주석만으로 OK?

### Q2 — D(subclass) v2.py 수정 필요성 실증 ★핵심 쟁점★

**실제 v2.py:604-620 구조** (Round 2 신규 확인):

```python
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
        ...
```

**Rule 2 위치** (v2.py:302):
```python
def update(self, features, outcome):
    ...
    self._rebalance_memory()  # Rule 2: entropy normalization
```

**검증 질문**: 이 구조에서 D안(v2.py 무수정 + predictor 주입)이 실현 가능한가?

**가능성 분석**:
- **옵션 D-1**: `OnlinePredictor` subclass로 `_rebalance_memory`를 no-op 오버라이드 → `V2Engine` subclass로 `__init__` 호출 후 `self.predictors`를 재할당 → v2.py 무수정으로 실현 가능
- **옵션 D-2**: `V2Engine.__init__`에 `predictor_factory` 파라미터 추가 → v2.py 수정 필요 → D의 핵심 장점(v2.py 무수정) 붕괴

**구체 판단 요청**: D-1이 Python 언어 문법상 문제없는가? V2Engine `__init__` 내부에서 `self.predictors`가 즉시 사용되지 않고 `tick()` 시점에 사용되므로, 부모 `__init__` 호출 후 재할당하면 실행 시점까지 충분한가?

### Q3 — D 불가 시 A의 구체 구현
만약 D-1도 현실적으로 실패(예: `OnlinePredictor` 생성 시점 부작용, 상태 초기화 문제)한다면, A가 유일 실용안. Codex에게: A의 구체 구현 경로를 제시하라 (어느 파일 어느 라인을 어떻게 수정할지).

### Q4 — 하이브리드 안 실현 가능성
"A의 포크 방식 + 파일명만 `oracle_rule2_ablation.py`" 하이브리드:
- 장점: Charter 문언(oracle 명칭) 충족 + A의 변수 분리 정확도 유지
- 단점: 파일명과 내용의 괴리(Oracle 아닌 V2 포크)
- 판단: 이 하이브리드는 각 진영의 본질적 주장을 만족하는가, 아니면 양쪽 단점만 합친 것인가?

---

## 요청

**Q1-Q4 각각 답변 후 최종 결론**: A / D / 하이브리드 중 하나 선택.

Q2 답변 특히 중요. "가능/불가능"이 아니라 **Python 실행 경로로 구체 검증**하라.

형식:
```
### Q1 답변
...

### Q2 답변 (핵심)
...

### Q3 답변
...

### Q4 답변
...

### 최종 결론
Position: <A|D|Hybrid>
Reasoning: 1-2문장
```

[POSITION: T2=<A|D|Hybrid>]
