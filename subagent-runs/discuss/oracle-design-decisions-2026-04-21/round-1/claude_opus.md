# Round 1 — Claude opus

### Topic 1 응답
- **Position**: **제외**
- **Reasoning**:
  - Charter "Differentiation Thesis"(조항 G, 전원 합의)는 단순 수사가 아니라 **레이어 분리 선언**이다. "V3=setup quality / Oracle=signal-generation (ex-ante predictive edge/uncertainty/regime)"은 context 벡터 구성(`predicted_edge, predictive_uncertainty, cost_margin, vol_regime, time_bucket`)에 **기계적으로 하드코딩**되어 있다. BollRev(Bollinger Reversion)는 본질적으로 "가격이 밴드를 벗어나면 평균 회귀 setup 진입"이라는 **setup 선택 로직** — 정의상 V3 소관이다.
  - Charter `scripts/dl_features.py:163-164`에서 `bb_pos`는 이미 V3 feature set에 포함되어 있다. Oracle이 BollRev variant를 가진다면 **같은 feature를 다른 레이어에서 중복 학습**하는 구조가 되어 Charter의 "공유 OHLCV cache"(조항 D) 취지와도 역행한다.
  - Charter 자체가 미해결 이견 #2에서 "Phase 0 어디에도 편입 근거 없음"을 명시했고, Oracle 기본 variants(control/aggressive/conservative)는 **신뢰도 게이트 임계치 스펙트럼**(risk tolerance 축)이다. BollRev는 이 축과 직교하는 "전략 유형" 축이므로 variant 체계 자체가 일관되지 않는다.
- **Concerns**:
  - mean-reversion regime 대응 공백은 실제 있는 이슈. 단, 이는 `vol_regime` context 세분화 또는 V3 측 variant 추가로 해소해야지 Oracle 레이어로 밀어넣으면 안 됨.
  - "편입"을 기본 제외하면 low-vol regime에서 Oracle confidence가 지속 낮아 거래가 중단될 가능성 — 하지만 이는 Charter Primary Outcome("자신감 없으면 거래 안함")과 정합. 문제 아님.
  - Phase 3 Decision Card 조항 B(예측 타깃/horizon)에서 mean-reversion style horizon을 별도 정의할 여지는 남겨둘 것.
- **Recommendation**: Phase 2 Component Map variants 목록을 **control/aggressive/conservative 3개로 확정**. BollRev는 "V3 신규 variant 후보"로 별도 기록(`project-status/current.md`)하여 V3 후속 작업 큐에 이관. 편입 필요성 재발 시 Charter 재개정 절차를 거쳐야 한다.

### Topic 2 응답
- **Position**: **A** (`scripts/v2_ablation.py` — V2 포크 + `--no-rule2` flag)
- **Reasoning**:
  - 실제 코드(v2.py:275-312) 확인 결과 Rule 2는 `update()` 끝의 **단일 라인 `self._rebalance_memory()`**. 포크본에서 이 한 줄을 flag로 감싸는 것(예: `if not self.no_rule2: self._rebalance_memory()`)은 **실질 수정 범위 3-5 LOC**. 변수 분리 정확도는 최고 수준.
  - B안(oracle_v0.py 선구현)은 Charter 조항 B(예측 타깃/horizon/점수함수/activation schedule)가 **아직 Phase 3 Decision Card 미작성**인 상태. 모델 골격(online ridge + Bayesian reliability head + EV blacklist)을 코드화하려면 미정 파라미터가 최소 4개. 이들이 Ablation 결과에 **교란 변수**로 들어가 "Rule 2가 원인인가"의 순수 검증 명제를 오염시킨다. Charter 태스크 1번 목적("V2 실패 근본 원인 진단") 위반.
  - C안(v2.py 직접 수정)은 8인 토론 conclusion.md "**v2.py live 환경 수술 금지**" 결정 위반. 포트 8897 live 운영 중이므로 회귀 리스크 현실적.
  - A안의 "Charter 원문 위배" 지적은 표면적 문제. Charter 조항 I는 **"격리된 환경에서 실행"**이 본질 요구사항이고, `scripts/v2_ablation.py`는 V2 live(8897)와 완전히 별도 프로세스로 격리된다. 문언 해석으로는 위배지만 **입법 취지(live 환경 보호)는 충족**.
- **Concerns**:
  - A안 archive 규칙을 미리 정하지 않으면 임시 파일이 영구 잔존할 위험. Ablation 종료 후 `scripts/archive/v2_ablation_2026-04-21.py`로 자동 이관하는 체크리스트 필수.
  - 포크 시 v2.py 내부 import 경로(normalizer, feature loader 등)가 바뀌면 동기화 부담. 포크 시점을 commit hash로 고정 기록.
  - Rule 2 toggle이 "제거"만 시험하고 "수정된 Rule 2"는 시험 못함. 그러나 Charter 태스크 1번 목적은 이진 검증이므로 허용 범위.
  - Ablation 결과가 PASS로 나오면 Charter 조항 E 선셋 조건이 앞당겨질 수 있음 — 이는 오히려 긍정적 outcome이므로 리스크 아님.
- **Recommendation**: (1) `scripts/v2_ablation.py` 생성 시 v2.py 현재 commit hash를 파일 상단 주석에 기록. (2) `--no-rule2` flag로 `_rebalance_memory()` 호출만 skip. (3) `data/oracle_ablation.jsonl` 스키마는 Charter 지정대로 준수. (4) 48시간 종료 시점을 cron으로 설정, 종료 후 파일을 `scripts/archive/`로 이동하는 정리 스크립트를 동시 작성. (5) Charter 조항 I 문언 해석 이슈는 Phase 2 Component Map에 각주로 명시("v2_ablation.py는 oracle.py 격리 원칙의 취지인 live 환경 보호를 만족하는 예외적 포크").

[POSITION: T1=제외, T2=A]
