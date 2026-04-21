# Round 2 — Gemini 2.5-pro

### Q1 답변
**충분함.** 48h 단기 ablation 실험에서 `v2.py`의 대규모 리팩토링 가능성은 극히 낮으며, 발생하더라도 `archive/` 폴더에 `v2.py`의 특정 commit 시점을 스냅샷으로 저장하고 이를 reference로 삼는 **"Frozen Fork"** 전략을 통해 drift를 완벽히 차단할 수 있습니다. 주석에 commit hash를 기록하는 것만으로도 재현 가능성은 확보됩니다.

### Q2 답변 (핵심)
**D-1은 "부분적으로 가능하나 Live 오염 리스크가 치명적"임.**

1. **기술적 가능성**: `AblationPredictor(OnlinePredictor)`를 만들고 `V2Engine.__init__` 호출 직후 `self.predictors`를 재할당하는 것은 파이썬 런타임상 문제가 없습니다.

2. **치명적 결함**: `v2.py`의 Line 45-47(`LOG_PATH`, `STATE_PATH`, `DASH_PORT`)이 **모듈 레벨 전역 상수**로 하드코딩되어 있습니다. `oracle_rule2_ablation.py`에서 `from v2 import V2Engine`을 수행하는 순간, 이 상수들은 `v2.py`가 정의된 시점의 Live 경로를 참조하게 됩니다.

3. **사이드 이펙트**: 이를 수정하려면 `v2.LOG_PATH = "..."` 식으로 Monkey Patching을 해야 하는데, 이는 `v2.py`를 수정하는 것보다 추적하기 어렵고 리스크가 큽니다. 특히 `DashboardHandler`나 별도 스레드에서 돌아가는 로직들이 이 상수를 참조할 때 Race Condition이나 설정 미적용이 발생할 수 있어, **Charter 조항 I(Live 환경 격리)**를 정면으로 위반할 위험이 큽니다.

### Q3 답변
D-1의 상수 오염 리스크로 인해 **A(포크)가 유일한 안전한 경로**입니다.
- **수정 대상**: `scripts/v2.py`를 `scripts/oracle_rule2_ablation.py`로 복사.
- **수정 내용**:
    1. Line 45-47: `LOG_PATH`, `STATE_PATH`에 `_ablation` 접미사 추가, `DASH_PORT`를 8898로 변경.
    2. Line 233: `self._rebalance_memory()` 호출부 주석 처리 (Rule 2 제거).
- **장점**: Live 코드와의 물리적/논리적 완벽 격리 및 단일 변수(Rule 2) 통제의 확실성.

### Q4 답변
**하이브리드(A의 구현 방식 + Charter 명칭)가 최적의 낙착점임.**
내용물은 `v2.py`의 독립적 포크(A)로 구성하여 실험의 정확도와 Live 안전성을 확보하되, 파일명만 `oracle_rule2_ablation.py`로 명명하여 Charter의 형식적 요건을 충족하는 방식입니다. 이는 각 엔진의 우려를 모두 해소합니다.

### 최종 결론
Position: **A** (Hybrid 형태)
Reasoning: `v2.py`의 하드코딩된 전역 상수 구조상, D안은 Live 데이터 오염 및 포트 충돌 리스크를 피하기 위해 지저분한 Monkey Patching이 강제됩니다. 실험의 순수성과 Live 환경의 물리적 격리를 보장하는 **"명칭만 Oracle인 V2 포크(A)"**가 가장 Senior한 접근입니다.

[POSITION: T2=A]
