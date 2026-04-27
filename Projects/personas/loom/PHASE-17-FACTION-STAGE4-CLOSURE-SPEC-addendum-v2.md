# [기능] Phase 17 Φ-2 Faction Stage 4 — Closure Spec Addendum v2

> 긴급도: 중간 (Stage 4 1차 구현 머지됨, **검증·보고 정합성만 보정**)
> 선행 조건: `PHASE-17-FACTION-STAGE4-CLOSURE-SPEC.md` (이하 base spec) 1차 구현 머지됨.
> 작업 유형: 기능 (검증 강화 + 측정 정합성 + 보고 형식)
> DB migration: 없음
> 외부 의존: 없음 (`pytest-timeout`은 dev-only, 이미 가용 시 사용)
> 사용자: Codex (gpt-5.5, reasoning_effort=xhigh)

---

## 본 addendum의 역할 (base spec과의 관계)

**base spec은 유효, 그러나 1차 구현 결과 6건 보정이 필요.**
본 addendum은 base spec [필수] 1~8 위에 **검증·측정·보고 정합성 [필수] A~F**를 추가한다.

### 1차 구현 검토 요약 (Stage 4 Closure Review)

base spec 8 [필수] 중 1차 구현 결과:
- Step 1 probe: **1/3 PASS** (seed=42 만 active=2, seed=7/13 active=1) — Φ-2 CLOSED **불가**.
- Step 2 freeze 테스트: PASS (단, D10 read-only 정의 모호로 비결정적 PASS 가능성).
- Step 3 결정성: PASS.
- Step 4 성능: 1회 측정 (351.6ms vs 224.2ms) — 분산 큼, 신뢰도 낮음.
- Step 5 Hard 불변: `test_class_promotion`이 KeyError 대신 **timeout 600s** 발생. base spec이 인정한 "사전 버그 KeyError"와 다름 → Stage 3 회귀 가능성 미배제.
- Step 6 Closure Report: 1차 작성됨, perf median/p95 표가 단일값. kernel perf는 tick 51-150만 측정.
- Step 7 Φ-3 Handoff 트리거: 작성됨.
- Step 8 Φ-3 스텁: 작성됨.

**Φ-2 CLOSED 선언 보류**, Stage 5 escalation은 **별도 spec**으로 이관(본 addendum 스코프 외).
본 addendum은 *현재 코드 상태에서* 검증·측정·보고가 **재현 가능하고 정확하게** 실행되도록 보정.

---

## 작업 범위

### [필수] (A~F — base spec [필수] 1~8 위에 추가)

#### A. 코드 블록 직접 복사 — functional equivalence 허용 명시

**문제**: base spec은 "코드 블록은 직접 복사" 원칙 명시. 1차 구현은 일부 서명을 변경하거나 헬퍼로 재구성. 그러나 동작·assertion이 동등하면 spec 의도(=해석 변종 차단)를 위반하지 않음.

**보정**:
1. 본 addendum 머지 시점부터, base spec의 모든 코드 블록은 다음 **둘 중 하나**를 만족해야 한다 ([필수]):
   - **(a) 직접 복사**: 토큰 단위 동일.
   - **(b) functional equivalence**: 함수 시그니처가 변경되었더라도 ① 핵심 assertion (`assert ...`) 문구·비교 대상이 동일, ② 호출 경로(어떤 API를 어떤 인자로 호출)가 동일, ③ 검증 부수 효과(internal state·snapshot 비교)가 동일.
2. (b)를 사용한 모든 위치는 테스트 파일 상단 docstring 또는 함수 docstring에 한 줄 명시:
   ```python
   """spec functional-equivalence: <assertion 핵심 키워드>"""
   ```
3. 해석 변종 (예: `>=`를 `>`로 변경, 비교 대상 채널 누락, snapshot 시점 변경) 은 **금지**.

**대상 파일**:
- `test_phase17_faction_handoff_contract.py`
- `test_phase17_acceptance.py` (Stage 4 추가분만)

**검증**: 본 addendum 머지 후 base spec [필수] 2·3에 해당하는 테스트의 assertion 문자열을 `grep`으로 추출하여 base spec 본문 코드 블록과 1:1 대응 확인.

---

#### B. `test_class_promotion` 사전 버그 분리 진단 ([필수])

**문제**: 1차 구현에서 `test_class_promotion`가 timeout 600s. base spec은 이를 "사전 버그 KeyError, 환생자 pid 미정리, baseline 동일 재현"으로 인정. 그러나 timeout과 KeyError는 별개 증상. **Stage 3 회귀(예: respawn 무한 루프)가 timeout으로 위장 가능**.

**보정** (모두 [필수]):
1. `pytest --timeout=600 Projects/personas/loom/test_class_promotion.py -v` 단독 실행하여 **끝까지 진행**.
   - `pytest-timeout`이 미설치면 `pip install pytest-timeout` (dev-only, requirements 미수정).
2. 결과 분기:
   - **(a) KeyError 재현 + 라인 위치 = `test_class_promotion.py:102`**: base spec이 인정한 사전 버그. Stage 4 baseline에 영향 없음. Closure Report에 "사전 버그 재현 — Stage 4 회귀 무관" 명시.
   - **(b) KeyError 재현 + 라인 위치 다름**: 사전 버그가 다른 위치로 이동. Stage 3 영향 가능성. Closure Report에 라인 위치·trace 첫 5줄 기록 + Stage 5 escalation 후보로 표시.
   - **(c) timeout 600s 재발생**: Stage 3 회귀 강력 의심. **Φ-2 CLOSED 보류** 유지. addendum FAIL.
3. (a)/(b)/(c) 어느 분기든 산출 위치: `Projects/personas/loom/data/phase17_probe/stage4_addendum/class_promotion_diag.txt` (pytest -v 출력 그대로).

**금지**: `test_class_promotion.py` 본체 수정. (사전 버그 fix는 별도 1줄 커밋, 본 addendum 스코프 외.)

---

#### C. 성능 측정 안정화 — warmup + median + p95 ([필수])

**문제**: 1차 측정은 1회 단발 (351.6ms vs 224.2ms). JIT 워밍업·GC pause·OS scheduling jitter로 분산 큼. 단발 측정은 회귀 판정에 부적합.

**보정** (`test_phase17_acceptance.py::test_phase17_phi2_perf_budget` 보강 — 또는 신규 `test_phase17_phi2_perf_budget_stable`):

1. **측정 절차** (모두 [필수]):
   - 동일 시드(seed=42)로 `MultiTickEngine` 인스턴스 1회 생성.
   - **Warmup 100틱**: 결과 기록 안 함, GC `gc.collect()` 후 측정 진입.
   - **측정 5회 반복**: 매 반복마다 `time.perf_counter`로 100틱 소요시간 측정 → 100으로 나누어 ms/tick 산출.
   - 5개 ms/tick 값에서 **median**과 **p95 (4번째로 큰 값, 5/5 percentile)** 계산.
2. **판정 기준** (모두 [필수]):
   - `median <= 250.0 ms/tick`
   - `p95 <= 350.0 ms/tick`
   - 둘 중 하나라도 위반 시 테스트 FAIL.
3. **출력 형식** (Closure Report·main runner 공통):
   ```
   [perf] tick(ms)  median=XXX.X  p95=YYY.Y  samples=[a,b,c,d,e]
   ```
4. 5회 반복 사이 별도 `engine` 재초기화 **금지** (state 일관성 유지).

**금지**: 5회 미만 측정값으로 PASS 판정.

---

#### D. faction kernel perf 측정 구간 확장 ([필수])

**문제**: 1차 측정은 tick 51~150만 측정. **`_respawn_faction_tick`은 `FOUNDER_RESPAWN_EVERY=480`마다 발동** — tick 51~150 구간은 respawn 0회, kernel 비용 과소측정.

**보정** (`test_phase17_acceptance.py::test_phase17_phi2_perf_budget` 또는 분리 테스트):

1. **측정 구간**: `tick 0 ~ tick 960` (= 2 × FOUNDER_RESPAWN_EVERY). respawn 발동 **최소 1회**, 가능하면 2회 포함.
2. **kernel 측정 대상 4구간** (base spec [필수] 4와 동일):
   - `_compute_affiliation_tick`
   - `_commit_faction_tick`
   - `_project_faction_tick`
   - `_respawn_faction_tick`
3. **측정 방법** (모두 [필수]):
   - 4구간 각각을 `time.perf_counter` 차분으로 누적합 측정 (전체 960틱 동안).
   - 960으로 나누어 평균 ms/tick. respawn 미발동 틱은 0ms로 합산.
4. **판정**: faction kernel 합 평균 ≤ **5.0 ms/tick** (base spec 동일 기준).
5. **출력 형식**:
   ```
   [perf] faction_kernel(ms/tick)  affiliation=A.AA  commit=B.BB  project=C.CC  respawn=D.DD  total=E.EE
   ```
   (`respawn`은 960틱 평균이므로 D.DD < 0.5ms 정상.)

**금지**: 측정 구간 < 480틱 (respawn 최소 1회 보장 위반).

---

#### E. acceptance main runner — perf 한 줄 출력 추가 ([필수])

**문제**: 1차 구현의 `python observe_phase17_emergence.py --seeds 7,13,42 --ticks 5000` 또는 `python -m pytest test_phase17_acceptance.py` main runner는 시드별 4지표만 출력. perf 정보가 분리된 테스트에만 존재 → Closure Report 작성 시 사람이 따로 수집해야 함.

**보정**:

1. **`observe_phase17_emergence.py`** main 출력 끝에 한 줄 추가 ([필수]):
   ```
   [perf] tick=<median_ms>ms  faction_kernel=<kernel_total_ms>ms  (seed=42 sample)
   ```
   - seed=42 샘플 1건만 (3시드 모두 측정 시 측정 비용 3배 → 시간 낭비). seed=42는 결정성 기준 시드.
   - 측정 방식은 [필수] C·D와 동일 (warmup 100 + 측정 100 × 5회 median, kernel 0~960틱 평균).
2. **`test_phase17_acceptance.py::test_phase17_phi2_acceptance_e2e`** (또는 main acceptance 테스트)도 동일 한 줄을 `print()`로 출력 ([필수]).
3. **Closure Report** 작성 시 이 한 줄을 그대로 인용 (사람 가공 금지).

**금지**:
- 측정 절차를 [필수] C·D와 다르게 변형.
- seed=7, 13에 대해서도 perf 측정 (시간 비용 + 결정성 기준 외 시드 혼선).

---

#### F. D10 read-only 정의 명확화 ([필수])

**문제**: base spec [필수] 2의 "read-only freeze" 검증 대상이 모호. 1차 구현은 `_faction_members_cache`까지 byte-level 동일을 요구했을 수 있음. 그러나 cache는 호출 시점에 lazy 갱신되는 **내부 최적화 산물**이며, `factions_in_contact()` 같은 read API는 **호출 시점에 cache refresh가 정상 동작**.

**보정** — D10 7종 API의 "read-only"를 다음과 같이 [확정]:

1. **read-only 정의** (Charter 추가):
   > **D10 7종 API의 read-only 보장**:
   > - **금지 (도메인 state mutation)**: `persona.faction`, `persona.faction_cooldown`, `inner.affiliation_scores`, `engine.factions` registry (id/name/founder_pid/charter/created_tick), `territory.factionRef` 변경 금지.
   > - **허용 (내부 캐시 refresh)**: `_faction_members_cache`, 메모이제이션 dict, lazy-built lookup 테이블의 갱신 허용. caller에 보이지 않는 부수 효과는 허용.
   > - **반환 객체**: 신규 생성된 dict/list/tuple. caller가 mutate해도 internal state 무영향.

2. **freeze 테스트의 byte-level 비교 채널** (base spec [필수] 2의 5채널을 다음 **4채널 + affiliation_scores**로 [확정]):
   - 비교 대상: `persona.faction`, `persona.faction_cooldown`, `engine.factions` registry (id/name/founder_pid/charter/created_tick), `territory.factionRef`, `inner.affiliation_scores`.
   - **`_faction_members_cache`는 비교 대상 제외** (cache refresh 허용).
3. **mutation 검증 방법** (모두 [필수]):
   - 7종 API 호출 전 위 5채널을 `pickle.dumps(..., protocol=4)` → `hashlib.sha256().hexdigest()` 산출.
   - 7종 API 100회 round-robin 호출.
   - 호출 후 동일 절차로 hash 산출.
   - **호출 전 hash == 호출 후 hash** (5채널 모두).
4. **반환 객체 mutation 검증** (모두 [필수]):
   - 각 API의 반환값을 caller가 `.clear()` / `.append(...)` / `.pop(...)` 등으로 변형 시도.
   - 변형 후 위 5채널 hash가 변형 전과 동일 (즉, caller mutation이 internal state 미오염).

**Charter 갱신**: `PHASE-17-FACTION-CHARTER.md`의 `[확정] #8`(D10 read-only 보장) 본문에 위 정의를 1단락 추가.

**금지**:
- `_faction_members_cache`를 mutation 금지 대상에 포함 (cache refresh 차단 → 정상 동작 막힘).
- `_*` prefix가 붙지 않은 신규 internal cache를 read API 내부에서 도입 (read-only 정의 모호화).

---

### [선택]

- secondary 지표 시각화 (matplotlib).
- perf median/p95 시계열 분석.

### [금지] (base spec [금지] 전부 + addendum 강화)

- **새 Faction 동역학 메커니즘 추가** — Stage 5 후보(D Territory 재결합 / E Contact 보정 / F Join/leave asymmetry)는 본 addendum **스코프 외**. 별도 spec.
- **Stage 1/2/3 상수 값 변경** — base spec과 동일.
- **D10 7종 API 시그니처 변경** — base spec과 동일.
- **base spec [필수] 1~8 항목의 행동 변경** — addendum은 *위에 추가*만, *대체* 아님.
- **`pytest-timeout` 외 신규 의존성 추가**.
- **`test_class_promotion.py` 본체 수정** — 사전 버그 fix는 별도 커밋.
- **perf 측정 절차의 임의 변경** — warmup 100, 측정 100×5, kernel 0~960 [확정].

---

## 변경 파일

| 파일 | 작업 | 근거 |
|------|:----:|------|
| `Projects/personas/loom/test_phase17_faction_handoff_contract.py` | 수정 | [필수] A·F |
| `Projects/personas/loom/test_phase17_acceptance.py` | 수정 | [필수] A·C·D·E |
| `Projects/personas/loom/observe_phase17_emergence.py` | 수정 (한 줄 print 추가) | [필수] E |
| `Projects/personas/loom/PHASE-17-FACTION-CHARTER.md` | 수정 ([확정] #8 본문 1단락 추가) | [필수] F |
| `Projects/personas/loom/PHASE-17-FACTION-STAGE4-CLOSURE-REPORT.md` | 수정 (perf 표 갱신 + class_promotion 분기 결과) | [필수] B·C·D |
| `Projects/personas/loom/data/phase17_probe/stage4_addendum/class_promotion_diag.txt` | 신규 | [필수] B |

**변경 없음 (금지)**:
- `Projects/personas/loom/core/multi_tick_engine.py` — D10 API 본체 무수정.
- `Projects/personas/loom/ontology/layers.py` — Stage 1~3 상수 무수정.
- `Projects/personas/loom/brain/**` — Phase 14-B 계약 불변.
- `Projects/personas/loom/test_class_promotion.py` — 사전 버그 fix 분리.
- `Projects/personas/loom/PHASE-17-STRUGGLE-CHARTER-STUB.md` — Φ-3 본격 설계 분리.

---

## 검증

### 기계 검증 (항상)
1. `python -m mypy Projects/personas/loom/` (loom 스코프)
2. `python -m ruff check Projects/personas/loom/`
3. `python -m pytest Projects/personas/loom/test_phase17_faction_handoff_contract.py -v`
4. `python -m pytest Projects/personas/loom/test_phase17_acceptance.py -v`

### 기능 검증 ([필수] A~F)

#### A. functional equivalence
- [ ] `test_phase17_faction_handoff_contract.py` 모든 테스트 함수의 docstring 또는 module docstring에 `spec functional-equivalence:` 또는 `spec direct-copy` 표기.
- [ ] base spec 본문 코드 블록의 핵심 assertion 키워드 (예: `read_only`, `byte_level_hash`, `caller_mutation_safe`)가 테스트 코드에 등장.

#### B. test_class_promotion 분리 진단
- [ ] `pytest --timeout=600 test_class_promotion.py -v` 실행 완료 (timeout/error 무관, 끝까지 진행).
- [ ] `class_promotion_diag.txt` 생성, 내용에 (a)/(b)/(c) 분기 명시.
- [ ] Closure Report에 분기 결과 1단락 기록.

#### C. perf median + p95
- [ ] perf 테스트 5회 측정값 모두 출력.
- [ ] median ≤ 250 ms/tick, p95 ≤ 350 ms/tick.
- [ ] 출력 형식 `[perf] tick(ms)  median=XXX.X  p95=YYY.Y  samples=[a,b,c,d,e]` 일치.

#### D. faction kernel perf 0~960틱
- [ ] 측정 구간 `tick 0 ~ tick 960` 명시.
- [ ] 4구간 (affiliation/commit/project/respawn) 각각 평균 ms/tick 출력.
- [ ] 합계 ≤ 5.0 ms/tick.
- [ ] 출력 형식 일치.

#### E. main runner perf 한 줄
- [ ] `observe_phase17_emergence.py` 출력 마지막 줄에 `[perf] tick=Xms  faction_kernel=Yms  (seed=42 sample)` 등장.
- [ ] `test_phase17_phi2_acceptance_e2e` print 출력에 동일 형식 등장.
- [ ] Closure Report에 동일 줄 그대로 인용.

#### F. D10 read-only 정의
- [ ] Charter [확정] #8 본문에 read-only 정의 1단락 추가.
- [ ] `test_phase17_faction_handoff_contract.py`의 비교 채널이 4채널 + affiliation_scores (5채널)로 명시, `_faction_members_cache` 제외.
- [ ] 7종 API 100회 round-robin 호출 전후 5채널 hash 일치 검증.
- [ ] 반환 객체 mutation 시도 후 internal state hash 무변동 검증.

### 계약 검증 (Φ-3 인계)
- [ ] base spec [필수] 7 (Φ-3 진입 트리거 [확정]) 본문이 read-only 4채널 + affiliation_scores 만으로 계산 가능 (D10 정의 변경 후에도 호환).
- [ ] base spec [필수] 8 (Φ-3 스텁) 변경 없음.

### 회귀 검증 (Hard 불변)
- [ ] base spec [필수] 5 항목 (Phase 16 Hard 5지표, Φ-1 23/23, Φ-2 핵심 4) 모두 PASS.
- [ ] `test_class_promotion` 분기는 [필수] B 결과로 대체 (timeout/KeyError 분리 진단).

---

## Rollback

본 addendum 변경은 **검증·측정·보고 형식 보강**만. 도메인 코드 무수정.
- 테스트 파일 revert: `git revert <addendum-commit>`로 단일 커밋 되돌림.
- Charter 1단락은 `git revert` 또는 수동 제거.
- Closure Report perf 표·class_promotion 분기는 base spec 1차 작성 상태로 복귀 가능.

데이터 손실 없음. SNN/multi_tick_engine 무수정.

---

## 결정 게이트 (본 addendum 통과 후)

본 addendum이 모든 [필수] A~F 검증을 통과하면:

- **결과 1: probe 1/3 PASS 유지** (가장 가능성 높음)
  - Φ-2 CLOSED **보류** 유지.
  - Stage 5 escalation으로 진입 (D/E/F 후보 토론).
  - **Stage 5는 별도 spec** — `/discuss` 6엔진 토론 후 후보 선정 → 별도 `/spec` 사이클.
- **결과 2: probe 2/3 또는 3/3 PASS** (재측정으로 확률 변화 가능 — Stage 3 RNG 의존성)
  - Closure Report 갱신, Φ-2 CLOSED 선언 검토.
  - 단, [필수] B에서 timeout 재발 또는 KeyError 라인 이동 시 CLOSED 보류 유지.

본 addendum은 **결과 분기를 결정하지 않음** — 측정 정합성만 보장.

---

## Codex 전달 프롬프트 템플릿

```
당신은 loom 페르소나 시뮬레이션의 시니어 백엔드 개발자입니다.

## 프로젝트 경로
c:/Users/haj/projects/subagent-orchestrator/Projects/personas/loom

## 기술 스택
Python 3.14 + numpy + pytest. Brian2/SNN은 brain/에 격리, 본 addendum 무관.

## 작업 지시서
PHASE-17-FACTION-STAGE4-CLOSURE-SPEC-addendum-v2.md 파일을 그대로 따라 구현하세요.
선행 spec: PHASE-17-FACTION-STAGE4-CLOSURE-SPEC.md (1차 구현 머지됨, 본 addendum이 위에 추가).

## 규칙 (절대 준수)
1. addendum의 [필수] A~F 100% 구현. [금지] 항목 절대 건드리지 말 것.
2. base spec과 충돌 시 addendum 우선.
3. 새 Faction 동역학 메커니즘 추가 절대 금지 (Stage 5 별도 spec).
4. 검증 순서:
   a. python -m mypy Projects/personas/loom/
   b. python -m ruff check Projects/personas/loom/
   c. python -m pytest test_phase17_faction_handoff_contract.py -v
   d. python -m pytest test_phase17_acceptance.py -v
   e. pytest --timeout=600 test_class_promotion.py -v ([필수] B 분리 진단)
   f. 기능 검증 체크리스트 [필수] A~F 모두 통과 확인
5. 검증 실패 시 재작업, 통과할 때까지 반복.
6. 보고 내용:
   - 변경 파일 목록 (addendum [변경 파일] 표 기준).
   - 각 검증 단계 통과 여부.
   - [필수] A~F 체크리스트 결과.
   - perf 출력 한 줄 (`[perf] tick=...  faction_kernel=...`).
   - test_class_promotion 분기 결과 (a/b/c).
   - Closure Report 갱신 diff 요약.

## 우선순위 (충돌 시)
1. 데이터 무결성·결정성 보존 (도메인 state mutation 금지).
2. base spec [필수] 1~8 의도 보존 (functional equivalence 허용).
3. 측정 절차 [확정] (warmup 100 / 측정 100×5 / kernel 0~960).
4. 보고 형식 [확정] (`[perf] tick=...  faction_kernel=...` 한 줄).
```
