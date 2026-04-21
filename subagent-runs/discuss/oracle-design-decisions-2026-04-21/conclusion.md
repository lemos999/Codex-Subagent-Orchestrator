# /discuss Conclusion — Oracle Design Decisions

**Date**: 2026-04-21
**Topic**: Oracle 예측 엔진 설계 결정 2건 교차 검증
**Participants**: Claude opus, Codex gpt-5.4, Gemini 2.5-pro
**Rounds**: 2 (Topic 1은 Round 1에서 AGREE, Topic 2는 Round 2에서 PARTIAL 다수안 채택)

---

## 최종 결정 요약

| Topic | 최종 결정 | 판정 근거 |
|-------|----------|----------|
| **T1 BollRev 편입** | **제외 (Exclude)** | Round 1 AGREE 3/3, 독립 추론 동일 결론 |
| **T2 Ablation 파일 구조** | **A (`scripts/v2_ablation.py` V2 포크 + `--no-rule2` flag)** | Round 2 PARTIAL (A 2 / D 1), 다수안 + 기술·공수 분석 수용 |

---

## Topic 1 — BollRev variant 편입 여부

### 결정: 제외

Oracle 초기 variants는 **control / aggressive / conservative 3종**으로 확정.

### 공통 근거 (3엔진 독립 추론)
- **Charter Differentiation Thesis**: Oracle(prediction layer) vs V3(setup quality/meta-decision) 레이어 분리. BollRev는 본질적으로 setup 선택 로직 → V3 소관.
- **피처 중복 방지**: `dl_features.py:163-164` `bb_pos`는 이미 V3 feature set. Oracle variant로 편입 시 동일 feature 이중 학습.
- **variant 체계 일관성**: control/aggressive/conservative는 "신뢰도 게이트 임계치" 축. BollRev는 "전략 유형" 축(직교) — variant 체계 붕괴.
- **공수 효율**: BollRev 신설 20-35h vs feature reuse ablation 4-10h (Codex 정량).

### 후속 조치
1. **feature reuse 1회 ablation** (Phase 3 전): `bb_pos + bb_width + dist_to_mid + rsi14`를 Oracle 입력에 추가하여 low-vol/range regime uplift 검증.
2. **BollRev 재요청 시 절차**: Charter 재개정 필요. V3 신규 variant 또는 Phase 6 별도 엔진 승격 경로.
3. Phase 3 Decision Card 조항 B에서 mean-reversion style horizon 정의 여지 유지.

---

## Topic 2 — 48h Rule 2 Ablation 파일 구조

### 결정: A — `scripts/v2_ablation.py` (V2 포크 + `--no-rule2` flag)

### 투표
- Round 1: A 2 (Claude opus, Gemini) / D 1 (Codex) / B·C 탈락
- Round 2: A 2 / D 1 (동일)

### 채택 근거

#### 1. 기술적 명료성
- 모듈-레벨 글로벌(`STATE_PATH`, `LOG_PATH`, `DASH_PORT`)을 **포크 파일에서 상수만 교체**하여 분리 가능. 런타임 재바인딩(monkey-patch) 불필요.
- D-1(subclass + `self.predictors` 재할당)은 Python 문법상 작동하나(3엔진 합의), `_log_tick`/`_save_state`/`_load_state`의 전역 참조 때문에 "얇은 wrapper" 본질이 붕괴: (a) monkey-patch 전역 오염, (b) 3개 메서드 60 LOC 복붙, (c) v2.py 수정 → D-2 중 하나 강제.

#### 2. 실질 공수 최소
- A 구현: **14 LOC 수정, 2-3h**
- Round 1에서 Codex가 추정한 A=8-12h는 과대. Round 2에서 **Codex도 A 공수 재계산 결과 인정**.

#### 3. Charter 조항 I 입법 취지 충족
- "신규 `oracle.py` 격리"는 **live 환경(8897) 보호**가 본질. `v2_ablation.py`는 포트 8902/8903으로 격리되어 취지 충족.
- 문언(Oracle 파일명)은 Component Map 각주로 "예외적 포크" 투명 기록하여 해결.

#### 4. drift 통제 가능
- 48h 단기 맥락상 drift 리스크 경미. commit hash 헤더 + 만료 체크리스트로 충분.

### 구현 체크리스트 (Claude opus Q3 채택)

1. **포크**: `cp scripts/v2.py scripts/v2_ablation.py`
2. **파일 헤더**:
   ```python
   """V2 Rule 2 Ablation Fork.
   Forked from v2.py @ <SHA> on 2026-04-21.
   Purpose: Rule 2 on/off A-B test. 48h lifecycle.
   Archive to scripts/archive/ after 2026-04-23.
   DO NOT sync with v2.py.
   """
   ```
3. **모듈 상수 분리** (v2.py:46-48 대응):
   ```python
   STATE_PATH = DATA_DIR / "v2_ablation_state.npz"
   LOG_PATH = DATA_DIR / "v2_ablation.jsonl"
   DASH_PORT = 8902  # control default; argparse로 8903 (no_rule2) override
   ```
4. **`OnlinePredictor.__init__`에 flag 주입**:
   ```python
   def __init__(self, ..., enable_rule2: bool = True):
       self.enable_rule2 = enable_rule2
   ```
   `update()` 내부:
   ```python
   if self.enable_rule2:
       self._rebalance_memory()
   ```
5. **argparse 추가**:
   ```python
   parser.add_argument("--no-rule2", action="store_true")
   parser.add_argument("--port", type=int, default=8902)
   ```
   `V2Engine`에 `OnlinePredictor(enable_rule2=not args.no_rule2)` 주입.
6. **variant별 산출물 분리**:
   ```python
   suffix = "_no_rule2" if args.no_rule2 else "_with_rule2"
   STATE_PATH = DATA_DIR / f"v2_ablation{suffix}_state.npz"
   LOG_PATH = DATA_DIR / f"v2_ablation{suffix}.jsonl"
   ```
7. **smoke test** (구현 직후): 1 tick 실행 후 `engine.predictors["BTC"].enable_rule2 == False` 확인.
8. **48h 종료 후**: `scripts/archive/v2_ablation_2026-04-21.py`로 이관 + Component Map 각주 업데이트.

### Codex의 D 주장에서 수용한 요소
- **파일명은 `v2_ablation.py` 유지**: Charter 문언보다 파일 내용과의 일치 우선. Component Map 각주에 입법 취지 충족 및 Phase 3 Oracle 파일과의 무관함 투명 기록.
- **RNG 상태 맞춤**: control / no_rule2 양 variant 동일 harness로 실행하여 RNG 소비 동등화 — strict one-variable 비교 보장.

### 기각 안
- **B (Oracle 최소 골격 선구현)**: Phase 3 Decision Card 미작성 상태에서 미확정 파라미터 4+ 개가 교란 변수 유입. Rule 2 순수 검증 명제 오염. (3/3 공통 기각)
- **C (v2.py 런타임 flag 직접 수정)**: "v2.py live 수술 금지" 결정(8인 토론 conclusion.md) 위반. (3/3 공통 기각)
- **D (import + subclass/no-op override)**: 기술 가능하나 모듈-레벨 글로벌 재바인딩이 "얇은 wrapper" 장점 붕괴. 공수 이득 소멸 후 drift 유리점만 남음 (48h 맥락상 경미).
- **Hybrid (A 포크 + `oracle_rule2_ablation.py` 파일명)**: 양쪽 단점 결합. Phase 3 실제 Oracle 파일 신설 시 네이밍 충돌.

---

## 미해결 이슈 (Round 3 불필요하지만 기록)

### Issue #1: 모듈-레벨 글로벌 재바인딩 성격 판단
- Codex: "standard module state override, race 없음"
- Claude/Gemini: "monkey patch, 스피릿 위반/리스크"
- **성격**: 기술적이 아닌 아키텍처 스타일 감각 차이. 추가 라운드로 해소 불가. 다수 판단(엄격 해석) 수용.

### Issue #2: 장기 재실행 drift 리스크
- D가 유리한 지점이나 48h 실험 맥락에서는 미미. 만약 향후 유사 ablation을 반복 실행한다면 **V2에 범용 `enable_rule2` parameterization을 먼저 적용**하는 쪽이 더 깨끗 — 이는 Phase 6 변경 관리로 이관.

---

## 후속 액션

### 즉시
1. **Phase 2 Component Map 업데이트** (`subagent-runs/design/oracle-2026-04-21/phase2-component-map.md`):
   - BollRev 제외 결정 확정 (이미 반영되었다면 본 conclusion 링크만 추가)
   - 각주: "Charter 조항 I 입법 취지 충족을 위한 예외적 V2 포크. Phase 3 Oracle 파일과 무관"
2. **48h-ablation-plan.md 갱신**: 파일명 `v2_ablation.py` 확정, 구현 체크리스트 8단계 반영, 포트 8902(control)/8903(no_rule2) 확정.

### Phase 3 진입 전
3. **Phase 3 Decision Card 작성 대기**: B/D 중 하나로 Ablation을 구현하는 게 아니므로, Phase 3 설계와 병행 가능.
4. **feature reuse 1회 ablation** (Topic 1 후속): `bb_pos + bb_width + dist_to_mid + rsi14` Oracle 입력 추가 효과 검증.

### Phase 3 이후
5. Oracle `phase1-charter.md`의 Charter 태스크 1번(48h Rule 2 ablation Go/No-Go gate)은 본 A 구현으로 수행.
6. Oracle이 V2 대비 3주 연속 우위 시 v2.py → `scripts/archive/` 이관 (Charter 선셋 조항).

---

## Evidence Trail

### 토론 산출물
- `context.md` — 토론 주제 정의
- `round-1/` — Round 1 응답 4개 (claude_opus, codex, gemini, moderator-summary)
- `round-2/` — Round 2 응답 4개 (claude_opus, codex, gemini, moderator-summary) + `_prompt.md`

### 코드 검증 참조 (v2.py)
- `v2.py:46-48` 모듈 상수 (STATE_PATH, LOG_PATH, DASH_PORT)
- `v2.py:252-342` OnlinePredictor class (특히 `_rebalance_memory` v2.py:314)
- `v2.py:302` Rule 2 호출 단일 라인
- `v2.py:604-625` V2Engine.__init__
- `v2.py:714-723` tick() 내 predictor 첫 사용
- `v2.py:790` `_log_tick`의 LOG_PATH 전역 참조
- `v2.py:841-873` `_save_state`/`_load_state`의 STATE_PATH 전역 참조

### 상위 맥락
- `subagent-runs/design/oracle-2026-04-21/phase1-charter.md`
- `subagent-runs/design/oracle-2026-04-21/phase2-component-map.md`
- `subagent-runs/design/oracle-2026-04-21/48h-ablation-plan.md`
- `subagent-runs/discuss/oracle-phase0-intake-2026-04-21/conclusion.md`
