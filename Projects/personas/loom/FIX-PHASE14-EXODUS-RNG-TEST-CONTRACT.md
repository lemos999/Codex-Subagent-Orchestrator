# Hotfix: Phase 14 Exodus 테스트 RNG 계약 정정

> 긴급도: **높음** (Phase 17 Case-C V3 진단 차단 중)
> 선행 조건: PHASE-17-CASE-C-DIAGNOSIS-V3-SPEC.md rev.3 (Codex 구현 진행, 회귀 게이트 차단으로 20,000틱 보류)
> 작업 유형: **버그 수정 (테스트 계약 정정)**
> DB migration: 없음
> 외부 의존: 없음
> 정책: [LOOM-DIRECTION.md §3.3.1](LOOM-DIRECTION.md) 자율 제안 적용 두 번째 사례 (Codex 결함 보고 → 사용자 결정 영역 정정)

---

## 배경

### 발생 경위 (Codex v3 진단 보고 2026-05-03)

Codex가 `PHASE-17-CASE-C-DIAGNOSIS-V3-SPEC.md` rev.3 helper 정정 구현 완료 후 회귀 게이트 9/12 PASS, `test_economy_balance.py`만 4/6 PASS (T5/T6 실패) 보고. v3 spec [필수] "EXPECTED FAIL 외 신규 회귀 발생 시 중단" 조건에 따라 20,000틱 probe 보류.

Codex 진단 (`§3.3.1` 정책 4항목 보고 절차 정합):

| 항목 | 사실 |
|------|------|
| 발견 위치 | [test_economy_balance.py:167-168](test_economy_balance.py#L167-L168) |
| 문제 | 전역 `np.random.random` monkeypatch가 엔진 RNG를 잡지 못함 |
| 변경 미실행 사유 | spec [필수] 회귀 게이트 = spec 본문 일부, 자율 수정 시 spec 위반 |
| 부합 근거 | LOOM 방향성: mechanism 보정 거부 + 거짓 PASS 절대 금지 부합. 테스트 계약 정정만이 정합 |

### Claude 검증 (코드 인용)

| 사실 | 위치 | 인용 |
|------|------|------|
| `_try_exodus()` RNG 진원지 | [multi_tick_engine.py:2298](core/multi_tick_engine.py#L2298) | `exodus_roll = float(self._np_rng.random())` |
| Phase 16C 결정성 RNG SSoT | [multi_tick_engine.py:203](core/multi_tick_engine.py#L203) | `self._np_rng: np.random.Generator = np.random.default_rng(self._seed)` |
| stale monkeypatch | [test_economy_balance.py:167-168](test_economy_balance.py#L167-L168) | `old_random = np.random.random; np.random.random = lambda: 0.0` |
| `_np_rng.random()` 첫 값 | Codex 측정 | ≈ 0.6956 (성공 임계 `roll < 0.3` 미달) |

→ **테스트가 잡는 RNG ≠ 엔진이 사용하는 RNG**. 결과: grievance=1.0이어도 첫 `random()` 값이 0.6956이라 `0.6956 >= 1.0 * 0.3` 성립, exodus가 발생하지 않아 T5/T6 실패.

### 근본 원인

Phase 16C에서 결정성 보장을 위해 RNG 진원지를 전역 `numpy.random` → 엔진 인스턴스 멤버 `self._np_rng`로 이전했으나, Phase 14에 작성된 `test_economy_balance.test_exodus_event_and_population_shift()`는 갱신되지 않음. **mechanism 회귀가 아니라 테스트 계약과 엔진 RNG SSoT의 불일치.**

### 표면 수정 금지 (LOOM-DIRECTION 방향성)

다음 시도는 거짓 PASS / 거짓 보정 안티패턴이므로 절대 금지:

| 금지 시도 | 위반 항목 |
|-----------|----------|
| `_try_exodus()` 성공 확률 임계 상향 (`* 0.3` → `* 0.5`) | mechanism 보정으로 테스트 통과 → 거짓 PASS |
| `grievance >= 0.9`이면 무조건 exodus 강제 | 자연 발생 원칙 위반 (axis C 안티패턴) |
| 회귀 실패 위에서 20,000틱 강행 | 측정 데이터 오염 (Phase 14 회귀 + Φ-3 collapse 분리 불가) |
| Phase 14 mechanism 조용히 변경 | spec [금지] + Rule 17 표면 수정 금지 |

---

## 작업 범위

### [필수]

1. `test_economy_balance.py` line 167-168, 172의 전역 `np.random.random` monkeypatch를 `engine._np_rng.random` 직접 패치로 교체
2. T5/T6 PASS 복원 (exodus event 발생 + 영지 population shift 확인)
3. 회귀 7종 PASS 유지 (Phase 17 acceptance known fail 3건은 EXPECTED FAIL 유지)
4. `Tools/scripts/verify_phase17_case_c_diagnosis.py` PASS 유지

### [선택]

- 다른 테스트 파일에 동일 stale 패턴(`np.random.random = lambda: 0.0`)이 있으면 **목록만 별도 보고**. 수정은 본 hotfix에 포함하지 않음 (스코프 격리)

### [금지]

- `core/multi_tick_engine.py` 일체 수정 (mechanism 무수정 절대 보장)
- `_try_exodus()` 임계값(`* 0.3`, `< 0.9`, `is_sleeping`, `cooldown`) 변경
- `_np_rng` 초기화 코드 변경
- v3 spec rev.3 helper 코드 변경 (이미 Codex 구현 완료, 검증 통과)
- 안전 전제 5종 변경: `HYSTERESIS=2`, `FOUNDER_RESPAWN_EVERY=480`, `TARGET_ACTIVE=2`, `COMMIT_EVERY=48`, `MAX_MEMBERS=2`
- `BOOST=0.20` 변경
- 다른 테스트 파일 변경 (단일 파일 격리)

---

## 구체 사양

### Before (현재 — line 150-197)

```python
def test_exodus_event_and_population_shift() -> tuple[bool, str]:
    engine = MultiTickEngine()
    pid = "persona_002"
    from_tid = engine.personas[pid].territory
    to_tid = "ironridge"
    engine.territories[from_tid].policy.tax_rate = 0.30
    engine.territories[to_tid].policy.tax_rate = 0.05
    engine.inners[pid].grievance = 1.0
    engine.inners[pid].is_sleeping = False
    rel_key = Relationship(persona_a=pid, persona_b="persona_001").key()
    rel_before = engine.relationships.get(rel_key)
    trust_before = rel_before.trust if rel_before else None
    familiarity_before = rel_before.familiarity if rel_before else None

    before_from = sum(1 for p in engine.personas.values() if p.territory == from_tid)
    before_to = sum(1 for p in engine.personas.values() if p.territory == to_tid)

    old_random = np.random.random              # ← STALE: 전역 numpy random
    np.random.random = lambda: 0.0             # ← 엔진의 _np_rng.random()는 영향받지 않음
    try:
        result = engine.tick()
    finally:
        np.random.random = old_random          # ← 원복도 같은 진원지

    exodus = [...]
```

### After (정정안)

```python
def test_exodus_event_and_population_shift() -> tuple[bool, str]:
    engine = MultiTickEngine()
    pid = "persona_002"
    from_tid = engine.personas[pid].territory
    to_tid = "ironridge"
    engine.territories[from_tid].policy.tax_rate = 0.30
    engine.territories[to_tid].policy.tax_rate = 0.05
    engine.inners[pid].grievance = 1.0
    engine.inners[pid].is_sleeping = False
    rel_key = Relationship(persona_a=pid, persona_b="persona_001").key()
    rel_before = engine.relationships.get(rel_key)
    trust_before = rel_before.trust if rel_before else None
    familiarity_before = rel_before.familiarity if rel_before else None

    before_from = sum(1 for p in engine.personas.values() if p.territory == from_tid)
    before_to = sum(1 for p in engine.personas.values() if p.territory == to_tid)

    # Phase 16C 결정성 RNG SSoT는 engine._np_rng. _try_exodus()는 self._np_rng.random()를
    # 사용하므로 엔진 인스턴스의 RNG random 메서드를 직접 patch한다.
    # 본 패치는 단일 tick 동안만 유효, finally 블록에서 원복.
    old_random = engine._np_rng.random
    engine._np_rng.random = lambda: 0.0
    try:
        result = engine.tick()
    finally:
        engine._np_rng.random = old_random

    exodus = [
        evt for evt in result.get("economy_events", [])
        if evt.get("type") == "exodus" and evt.get("persona") == pid
    ]
    # ... (이하 동일)
```

### 변경 핵심

| 항목 | Before | After |
|------|--------|-------|
| 진원지 | `np.random.random` (모듈 전역) | `engine._np_rng.random` (엔진 인스턴스 메서드) |
| 영향 범위 | 전역 numpy 사용처 (실제 0건) | 엔진 RNG 사용처 (`_try_exodus` 포함 정확히 일치) |
| 단일 tick 격리 | try/finally로 원복 | 동일 (try/finally로 원복) |
| 결정성 SSoT 일치 | ❌ Phase 16C 이후 어긋남 | ✅ 일치 |

### 검토: numpy Generator 메서드 monkeypatch 가능성

`numpy.random.Generator`는 일반 Python 객체이며 메서드 attribute 재할당 가능. `engine._np_rng.random = lambda: 0.0` 직접 할당은 numpy 1.17+에서 동작. 단 `Generator` 객체에 `__slots__`가 있다면 실패할 수 있으므로 **Codex는 구현 후 즉시 1회 단위 실행으로 확인**:

```python
import numpy as np
g = np.random.default_rng(42)
g.random = lambda: 0.0
assert g.random() == 0.0
```

`__slots__` 제약으로 실패 시 fallback: `engine._np_rng` 자체를 부분 wrapping fake로 교체:

```python
class _ExodusForceRng:
    """Test-only: random()는 0.0 반환, 다른 메서드는 baseline에 위임."""
    def __init__(self, base):
        self._base = base
    def random(self):
        return 0.0
    def __getattr__(self, name):
        return getattr(self._base, name)

old_rng = engine._np_rng
engine._np_rng = _ExodusForceRng(old_rng)
try:
    result = engine.tick()
finally:
    engine._np_rng = old_rng
```

**구현자 우선순위**: 메서드 직접 monkeypatch (단순) → 실패 시 wrapping class fallback. 둘 중 동작하는 쪽 채택, 다른 쪽은 주석으로 사유 1줄 명시.

---

## 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/test_economy_balance.py` | line 167-168, 172 RNG 진원지 교체 | 수정 |

**변경 없음 (금지):**
- `Projects/personas/loom/core/multi_tick_engine.py` (mechanism 무수정)
- `Projects/personas/loom/observe_phase17_emergence.py`
- `Projects/personas/loom/Tools/scripts/verify_phase17_case_c_diagnosis.py`
- `Projects/personas/loom/PHASE-17-CASE-C-DIAGNOSIS-V3-SPEC.md`
- `Projects/personas/loom/PHASE-17-CASE-C-COLLAPSE-DIAGNOSIS-SPEC.md`
- 기타 v3 spec helper 정정 관련 모든 파일

---

## 검증

### 기계 검증

```bash
cd Projects/personas/loom
py -m py_compile test_economy_balance.py
```

### 기능 검증 (회귀 게이트)

```bash
cd Projects/personas/loom
py test_economy_balance.py             # 6/6 PASS 기대
py test_economy.py                      # 6/6 PASS 유지
py test_class_promotion.py              # PASS 유지
py test_nomos.py                        # PASS 유지
py test_phase14b_snn_integration.py     # 8/8 PASS 유지
py test_phase17_faction_handoff_contract.py  # PASS 유지
py test_phase17_faction_stage3.py       # PASS 유지
py test_phase17_acceptance.py           # 기존 known fail 3건만 유지 (EXPECTED FAIL)
py Tools/scripts/verify_phase17_case_c_diagnosis.py   # PASS 유지
```

### 계약 검증

T5/T6 PASS 시 `test_exodus_event_and_population_shift()` 결과:
- `events >= 1` (exodus 이벤트 1건 이상)
- `before_from - 1 == after_from` (출발 영지 population -1)
- `before_to + 1 == after_to` (도착 영지 population +1)
- `relation_kept == True` (관계 보존)

위 4개 모두 `True` 시 PASS. 하나라도 실패 시 monkeypatch 진원지를 `_np_rng.random` → wrapping class fallback으로 변경 후 재실행.

---

## Rollback

```bash
cd Projects/personas/loom
git diff HEAD -- test_economy_balance.py     # 변경 확인
git checkout HEAD -- test_economy_balance.py # 원복
```

데이터 영향: 없음 (테스트 파일 단일 변경).

---

## 회고 인정 ([LOOM-DIRECTION.md §3.3.1](LOOM-DIRECTION.md) — 두 번째 적용 사례)

본 hotfix는 §3.3.1 정책의 **두 번째** 적용 사례 (첫 번째: Phase 17 Case-C V2 helper 자율 정정 + stale 코드 5종 자율 제거).

### Codex 행동 평가

매트릭스 적용 영역: **테스트 계약 (`test_*.py`) — spec [필수] 회귀 게이트인 경우** = **자율 X (사용자 보고만)**.

| 항목 | 행동 | 평가 (매트릭스 인용) |
|------|------|------|
| 결함 발견 (test_economy_balance.py stale monkeypatch) | spec [필수] 회귀 게이트에서 발견 | **정합** — 회귀 게이트 실행이 의무인 spec 본문에서 적법하게 발견 |
| 자율 수정 회피 | test_economy_balance.py가 v3 spec [필수] 회귀 게이트이므로 매트릭스 "자율 X" 행 적용 인식 | **정합** — 매트릭스 "테스트 계약 (spec [필수] 회귀 게이트)" 행 정확히 준수. 동일 파일이라도 spec 외부면 자율 정정 가능했을 영역 |
| 사용자 보고 | 발견 위치·문제·변경 미실행 사유·부합 근거 명시 | **정합** — §3.3.1 4항목 보고 절차 (당시 시점 정책). 본 hotfix 작성 후 §3.3.1이 5항목으로 확장됨 — 다음 자율 행동부터 5항목 적용 |
| 20,000틱 probe 중단 | "EXPECTED FAIL 외 신규 회귀 시 중단" 조건 준수 | **정합** — spec 본문 [필수] 절대 준수 |

### Claude 책임 인정

| 결함 | 위치 | 책임 |
|------|------|------|
| v3 spec rev.3 회귀 게이트 사전 검증 누락 | spec 작성자 (Claude) | **인정** — `test_economy_balance.py`를 회귀 게이트로 포함했으나 현재 RNG SSoT와 정합 검증 안 함 |
| Phase 16C RNG SSoT 이전 후 stale 테스트 미갱신 | Phase 14 작성자 → Phase 16C 마이그레이션 시 누락 | **부분 인정** — 본 hotfix에서 정정 |

### 다음 spec 학습 반영 (§3.3.1 5항목 보고 형식 적용)

5번째 항목 = **spec rev 갱신 권고**. Codex 자율 발견을 Claude의 다음 spec rev에 강제 흡수시키는 피드백 루프.

- **현재 spec rev 결함**: `PHASE-17-CASE-C-DIAGNOSIS-V3-SPEC.md` rev.3 회귀 게이트에 `test_economy_balance.py`를 포함했으나, 해당 테스트가 현재 RNG SSoT(`self._np_rng`)와 정합한지 사전 검증 안 함.
- **다음 spec rev 갱신 권고**: 차기 진단/hotfix spec 작성 시 회귀 게이트에 다음 [필수] 사전 점검 3종 명문화:
  1. 지정한 회귀 테스트가 현재 RNG SSoT (`self._np_rng`)와 정합한가? (전역 `np.random.*` monkeypatch 사용 여부 grep)
  2. 회귀 게이트 실행을 spec 본문에 포함하기 전에 1회 PASS 확인 (지시서 작성 시점 baseline)
  3. Phase 16C 이후 RNG 진원지 이전 영향 받은 테스트 목록을 별도 reference로 유지 (다음 spec에서 재참조)

---

## 다음 단계 (본 hotfix 완료 후)

1. **회귀 7종 PASS 확인** → v3 spec rev.3 회귀 게이트 통과 복원
2. **20,000틱 probe 재개** — `PHASE-17-CASE-C-DIAGNOSIS-V3-SPEC.md` §검증 6.5에 따라:
   ```bash
   cd Projects/personas/loom
   py observe_phase17_emergence.py --label phi3-case-c-diagnosis-v3 --seeds 7,13,42 --ticks 20000
   ```
3. **v3 진단 보고서 작성** (`PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md` Codex 작성 분이 있다면 보강) → closure-v2 §7.2 Finding A 재판정
4. **(이후)** SUMMARY.md mojibake hotfix spec
5. **(이후)** P1+P2 통합 패치 spec 설계 (axis C 가드레일 적용)

---

## Codex 위임 프롬프트 (참고 — `/sub` 또는 `codex exec --full-auto`용)

```
당신은 loom 프로젝트의 시니어 Python 개발자입니다.

## 프로젝트 경로
c:\Users\haj\projects\subagent-orchestrator\Projects\personas\loom\

## 작업 지시서
FIX-PHASE14-EXODUS-RNG-TEST-CONTRACT.md 파일을 그대로 따라 구현하세요.

## 규칙 (절대 준수)
1. 변경 파일은 test_economy_balance.py 단 1개. core/multi_tick_engine.py 등 다른 파일 수정 절대 금지.
2. _try_exodus() 등 mechanism 코드는 한 줄도 변경 금지.
3. 지시서 §구체 사양 "After" 코드 블록을 직접 적용. wrapping class fallback은 메서드 monkeypatch 실패 시에만.
4. 검증 순서:
   a. py -m py_compile test_economy_balance.py
   b. py test_economy_balance.py (6/6 PASS 기대)
   c. py test_economy.py (6/6 PASS 유지)
   d. py test_class_promotion.py (PASS 유지)
   e. py test_nomos.py (PASS 유지)
   f. py test_phase14b_snn_integration.py (8/8 PASS 유지)
   g. py test_phase17_faction_handoff_contract.py (PASS 유지)
   h. py test_phase17_faction_stage3.py (PASS 유지)
   i. py test_phase17_acceptance.py (기존 known fail 3건만 유지)
   j. py Tools/scripts/verify_phase17_case_c_diagnosis.py (PASS 유지)
5. 모든 검증 통과 시 hotfix 완료 보고. 어느 하나라도 실패 시 즉시 중단·보고 (mechanism 변경 절대 금지).
6. 본 hotfix 완료 후 v3 spec 20,000틱 probe 재개는 사용자 결정 후 별도 위임.

## spec 외 자율 제안 정책 (LOOM-DIRECTION §3.3.1 영역별 자율 매트릭스)

본 hotfix 진행 중 spec 외부에서 코드 결함·개선 기회를 발견하면 다음 매트릭스에 따라 행동:

| 영역 | 자율 폭 | 본 hotfix 적용 시 |
|------|---------|------------------|
| 진단 helper / 분석 스크립트 | **자율 정정** | 결함 발견 시 분리 커밋 + 5항목 보고 |
| stale 코드 (데이터 오염 위험) | **자율 제거** | 5종 제거 사례(v2)와 동일 절차 |
| 테스트 계약 (`test_*.py`) — spec 외부 | **자율 정정** | 다른 테스트 파일에서 동일 stale `np.random.*` 패턴 발견 시 발견 사실만 보고. 본 hotfix는 `test_economy_balance.py` 단일 파일 격리이므로 자율 정정은 별도 hotfix로 분리 권고 (cross-spec 정합성 결함 행) |
| **테스트 계약 — spec [필수] 회귀 게이트** (`test_economy_balance.py`) | **자율 X** | 본 hotfix 작업 대상이지만 매트릭스 행이 아닌 spec 본문 [필수] 사양에 따라 정정 |
| **mechanism 본문** (`core/multi_tick_engine.py`) | **자율 절대 X** | `_try_exodus()` 등 한 줄도 변경 금지. 의심 시 즉시 중단·보고 |
| **안전 전제 5종 + `BOOST=0.20`** | **자율 절대 X** | 동일 |
| **acceptance 정의 / `brain/**` / D10 SNN API** | **자율 절대 X** | 동일 |

자율 정정 시 4단 절차 [필수]:
1. 분리 커밋 (CLAUDE.md Rule 3 분리 원칙) — hotfix 메인 커밋과 다른 커밋
2. 5항목 보고:
   - (a) 발견 위치 (파일:줄)
   - (b) 문제 인식 (코드 인용 + 영향 분석)
   - (c) 변경 내용 (적용된 코드 인용)
   - (d) 부합 근거 (LOOM-DIRECTION §3.7 / §2.2 / 안전 전제 / 데이터 오염 방지 등 인용)
   - (e) **spec rev 갱신 권고** — "현재 spec rev 결함: <빠뜨린 항목 1줄>" + "다음 spec rev 갱신 권고: <명문화 항목 1줄>"
3. 사후 인정 절차 (사용자 부합 판정 시 수용, 미부합 시 revert)
4. 메인 커밋 미혼입 (자율 변경을 hotfix 본문 커밋에 "조용히" 섞지 않기)

절대 금지:
- 매트릭스 "자율 절대 X" 영역 자율 변경
- "조용히" 자율 변경 후 메인 커밋에 섞기

## 보고 내용
- 변경 파일: test_economy_balance.py 1건
- monkeypatch 진원지 변경 (np.random.random → engine._np_rng.random) — 또는 wrapping class fallback 사용 시 사유 1줄
- 검증 a~j 결과 표
- spec 외 자율 발견 항목:
  - 자율 정정 영역 발견 → 5항목 보고 형식 (a~e)
  - 자율 X 영역 발견 → 발견 위치·문제만 보고
  - 없으면 "없음" 명시
```
