# Round 1 — Codex gpt-5.4

### Topic 1 응답
- **Position**: 제외
- **Reasoning**:
  - 현재 repo 기준 BollRev는 "variant"가 아니라 별도 엔진급 작업입니다. 설계 문서도 `scripts/bollrev.py` 약 900 LOC + smoke test + dashboard 수정까지 잡고 있어, Oracle variant 추가보다 모델 신설에 가깝습니다.
  - 구현 관점에서 mean-reversion은 지금 구조상 prediction layer보다 setup layer에 더 자연스럽습니다. `scripts/v3.py`는 `VARIANTS_CONFIG`와 `ContextMemory`로 setup/regime를 파라미터화하고, Oracle charter는 `predicted_edge / uncertainty / regime` 학습에 집중합니다.
  - Oracle 쪽에는 이미 feature 재사용 경로가 있습니다. `scripts/dl_features.py:93,164`의 `bb_pos`를 비롯해 `bb_width`, `dist_to_mid`, `rsi`를 얹으면 mean-reversion 정보는 prediction input으로 넣을 수 있습니다.
  - 공수/효율 기준으로 별도 BollRev 편입은 대략 20-35h, feature reuse ablation은 4-10h 수준입니다. 초기 Oracle에선 후자가 훨씬 효율적입니다.
- **Concerns**:
  - 제외만 하면 low-vol/range regime blind spot이 남을 수 있습니다.
  - `bb_pos` 하나만으로는 BollRev 성격이 약합니다. `bb_width`, `dist_to_mid`, `time_in_band`류 보강이 필요합니다.
  - V3 런타임은 아직 bb 계열 context를 쓰지 않으므로 "V3 소관"도 무공수는 아닙니다.
- **Recommendation**:
  - Oracle 초기 variants는 `control / aggressive / conservative`만 유지하십시오.
  - Phase 3 전에 `bb_pos + bb_width + dist_to_mid + rsi14`를 Oracle 입력 또는 V3 context에 추가하는 1회 ablation만 먼저 돌리고, low-vol/range slice에서 유의미한 uplift가 있을 때만 Phase 6 별도 BollRev 엔진으로 승격하는 쪽이 맞습니다.

### Topic 2 응답
- **Position**: D — `scripts/v2_rule2_ablation.py` 같은 얇은 분리 harness. `v2.py`를 import하고 predictor만 교체해 Rule 2 on/off를 비교
- **Reasoning**:
  - `scripts/v2.py`는 795 LOC이고 Rule 2 차이는 사실상 `update()` 말단의 `self._rebalance_memory()` 한 점(`scripts/v2.py:302`)입니다. full fork보다 wrapper/subclass가 더 정확한 one-variable ablation입니다.
  - 대략 공수/운영리스크(1=낮음, 5=높음): A 8-12h/3, B 16-28h/4, C 2-4h/5, D 6-10h/2.
  - D는 live `v2.py` 무수정, 별도 포트/로그/상태파일 분리, 동일 코드경로 재사용을 동시에 만족합니다. 임베디드의 shadow binary, ML의 isolated experiment harness와 같은 정석 패턴입니다.
  - B는 Charter 문구에는 예쁘지만, 실험이 Rule 2 ablation이 아니라 "미확정 Oracle skeleton + Rule 2" 복합 실험으로 바뀝니다.
- **Concerns**:
  - Charter를 글자 그대로 읽으면 `oracle.py` 명칭 불일치가 논점이 될 수 있습니다.
  - import 기반 harness는 `LOG_PATH / STATE_PATH / DASH_PORT`를 variant별로 재바인딩하지 않으면 live 산출물 오염 위험이 있습니다.
  - A보다 코드 중복은 적지만, `V2Engine` predictor 주입 방식은 스모크 테스트로 먼저 잠가야 합니다.
- **Recommendation**:
  - 새 파일 1개만 만들고 `OnlinePredictor`를 subclass/no-op override해 Rule 2를 끄십시오. 포트는 8902/8903, 산출물은 `data/v2_ablation_{variant}.*`로 분리하면 됩니다.
  - 문서 정합성이 필요하면 파일명만 `oracle_rule2_ablation.py`로 두고 내부는 `v2.py` 재사용으로 구현하십시오. 핵심은 "future Oracle 선구현"이 아니라 "same V2 path, one toggle, isolated artifacts"입니다.

[POSITION: T1=제외, T2=D]
