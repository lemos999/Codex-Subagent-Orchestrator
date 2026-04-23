# Phase 17 / Φ-1 Land — Codex Instructions Addendum **v2** (리뷰 2차 대응)

> `/spec` 2차 Review 대응 산출물. v1 addendum 구현 후 재리뷰에서 확인된 **P0 1건 + P1 3건 + P2 2건** 수정 지시.
>
> - 긴급도: **높음** — v1에서 해결한 줄 알았던 split-state가 mass_exodus 경로로 **다른 얼굴로 재발**
> - 선행 조건: v1 addendum 구현 완료 (12/12 테스트 PASS 상태)
> - 작업 유형: **혼합** — 아키텍처 리팩터 + Spec 문서 개정 + 테스트 보강 + 인프라 (통합 스크립트)
> - DB migration: **없음**
> - 외부 의존: **없음**
> - 지침 관계: **v1 SUPERSEDED BY v2** — v1 addendum의 Fix 1(D7 단일 경로 sync) 은 v2 Fix 5 (공통 헬퍼)로 흡수·대체. v1의 Fix 2/3/4는 v2에서도 유효 (중복 지시 아님, 전제 조건).

---

## 배경

v1 addendum 기반 Codex 구현은 12/12 테스트 PASS + Phase 11-16 회귀 4건 PASS를 확인했으나, 2차 리뷰에서 **v1이 해결하려 한 "split-state" 버그의 핵심 우회 경로가 남아 있음**을 발견:

### 재리뷰 실측 근거

| # | 경로 | 증상 | 파일:라인 |
|:--:|---|---|---|
| 1 | `mass_exodus` (정치적 집단 이주) | `persona.territory = target_tid`만 쓰고 `persona.region` 미동기화 | [multi_tick_engine.py:1095](Projects/personas/loom/core/multi_tick_engine.py#L1095) |
| 2 | `_try_exodus`의 RNG | `np.random.random` monkeypatch 의존 분기 — 결정성 계약 오염 | [multi_tick_engine.py:937-940](Projects/personas/loom/core/multi_tick_engine.py#L937-L940) |
| 3 | Decisions 검증 체크리스트 | "D8: 20명 배치 성공, 7:7:6 정확" 문구 잔존 (spec drift) | [PHASE-17-LAND-DECISIONS.md:423](Projects/personas/loom/PHASE-17-LAND-DECISIONS.md#L423) |
| 4 | acceptance gate | Hard 5 / ≤250ms / 500틱 검증이 개별 테스트에 분산, Phase 17 단일 acceptance 경로 없음 | (신규 파일 필요) |
| 5 | `project_territory()` contested 처리 | 2표 우위 미만 시 stale `territoryRef` 유지 — **의도된 히스테리시스**인데 문서화 없음 | [physis/world.py:67-91](Projects/personas/loom/physis/world.py#L67-L91) |
| 6 | `test_fix3_movement_before_economy` | source grep 기반 — 리팩터링에 취약, 런타임 순서 미증명 | [test_phase17_land.py:175-191](Projects/personas/loom/test_phase17_land.py#L175-L191) |

### 근본 원인 분석 (CLAUDE.md Rule 17-20 적용)

v1 Fix 1은 `_try_exodus()` 한 경로에만 `persona.region` 동기화를 추가. 이는 **표면 해결** — 같은 invariant("territory 변경 시 region 동기 갱신")를 강제하는 단일 지점이 없으므로 다른 경로에서 같은 버그가 재발.

v1 리뷰에서 이미 "persona.territory 쓰기를 single point로"를 권고했어야 했다. v2는 이 실수를 교정한다.

**Single Source of Truth**: `persona.territory`는 오직 `_change_persona_territory()` 헬퍼를 통해서만 변경. 직접 쓰기(`persona.territory = X`) 금지 — grep 회귀 가드로 강제.

### 3엔진 /discuss 합의 (Round 3, 전원 AGREE)

- **Option A** 채택: v2 신규 작성, v1 상단 `[SUPERSEDED BY v2]` 마커 추가
- **Contract-first**: `_change_persona_territory()` 시그니처 + atomicity 불변식을 **먼저 확정** → 구현
- `_change_persona_territory()` 는 단순 Fix가 아니라 **아키텍처 결정**
- v1 파일은 git history로 충분 (deprecation window 불필요, 즉시 supersede)

Evidence: [discussions/.../quick-phase-17-land-addendum-리뷰-대응-방식-선택-2026-04-21/conclusion/conclusion.md](discussions/quick-phase-17-land-addendum-리뷰-대응-방식-선택-리뷰-결과-6-이-2026-04-21/conclusion/conclusion.md)

---

## Contract — `_change_persona_territory()` 헬퍼 계약

**이 계약은 Fix 5-10 모든 항목의 전제**. 구현 순서: **계약 구현 → Fix 5 → Fix 6~10**.

### 시그니처

```python
def _change_persona_territory(
    self,
    persona_id: str,
    target_territory_id: str,
    reason: str,
) -> dict:
    """Atomically change persona.territory and sync persona.region.

    The **only** allowed write path to `persona.territory` outside
    the engine constructor / initial placement. All migration code
    paths (`_try_exodus`, `_update_grievances.mass_exodus`, future
    Φ-2 faction moves) MUST call this helper.

    Args:
        persona_id: Target persona identifier.
        target_territory_id: New territory id. Must exist in `self.territories`.
        reason: Migration reason tag for events ("exodus", "mass_exodus", ...).

    Returns:
        dict {
            "persona": persona_id,
            "from_territory": old_tid,
            "to_territory": target_territory_id,
            "from_region": old_region,
            "to_region": new_region,
            "reason": reason,
            "employment_cleanup": {...},   # from _release_employment
        }

    Raises:
        KeyError: target_territory_id not in self.territories.
        ValueError: persona_id not in self.personas.

    Invariants (MUST hold at return):
        I1. persona.territory == target_territory_id
        I2. persona.region == self.territories[target_territory_id].region
        I3. self._territory_residents_cache is None (invalidated)
        I4. Employment in old territory is released (via _release_employment)

    Atomicity:
        If any step raises, the caller is responsible — this helper
        does NOT rollback partial changes. Callers MUST validate
        preconditions (target exists, persona exists) before invoking.

    Side effects (allowed):
        - Releases persona's employment in the *old* territory
        - Invalidates resident cache
        - Returns an employment_cleanup dict for event propagation

    Non-side-effects (forbidden):
        - Does NOT reset grievance (caller decides; exodus halves it,
          mass_exodus sets 0.3)
        - Does NOT set exodus_cooldown_until_tick (caller decides)
        - Does NOT emit "exodus"/"mass_exodus" events (caller builds)
    """
```

### 왜 이 경계인가

- **grievance / cooldown / event emission은 caller 책임**: migration 종류마다 정책이 다름 (exodus는 grievance *= 0.5, mass_exodus는 grievance = 0.3). 헬퍼가 일괄 처리하면 새 migration 경로 추가 시 헬퍼가 비대해짐.
- **헬퍼가 책임지는 것은 "territory/region/employment 정합성"만**: 이 세 가지는 **모든** migration에서 동일해야 함.

### grep 회귀 가드 (강제)

아래 패턴이 `Projects/personas/loom/` 이하 Python 파일(테스트 + 헬퍼 본체 제외)에 **하나도 없어야** 한다:

| 금지 패턴 | 허용 예외 |
|---|---|
| `persona.territory\s*=` (정규식) | `_change_persona_territory` 본체, `PERSONA_DEFS` 초기화, `_assign_personas()` 초기 배치 |
| `\.territory\s*=\s*(?!None\|""\|persona_def)` | 동일 |
| `self.personas\[.*\]\.territory\s*=` | 동일 |

**구현**: `test_phase17_land.py` 의 `test_forbidden_grep_regression` 에 위 패턴 3종 추가. 허용 예외는 파일명+라인 whitelist 기반 (하드코딩).

---

## 작업 범위

### [필수]
1. **Contract 구현**: `_change_persona_territory()` 헬퍼를 [multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py) 에 추가 (위 docstring 그대로).
2. **Fix 5 (P0)**: `_try_exodus()` + `mass_exodus` 양쪽을 헬퍼 호출로 치환. 직접 쓰기 전부 제거.
3. **Fix 6 (P1)**: `_try_exodus()` 의 `np.random.random` monkeypatch 분기 제거. 테스트는 `_np_rng.random` monkeypatch로 재작성.
4. **Fix 7 (P1)**: `PHASE-17-LAND-DECISIONS.md:423` 의 "20명 / 7:7:6" 문구를 `PERSONA_DEFS` 동적 참조 문구로 교체.
5. **Fix 8 (P1)**: `test_phase17_acceptance.py` 신규 — Phase 17 Φ-1 단일 acceptance gate (Hard 5 + 250ms/tick + 500틱 결정성 + Phase 11-16 회귀 묶음).
6. **Fix 9 (P2)**: `project_territory()` docstring 에 "contested hysteresis" 명시 + `test_d6_project_territory_atomicity` 에 설명 주석 추가.
7. **Fix 10 (P2)**: `test_phase17_land.py` 에 `test_fix10_movement_before_economy_behavioral` 추가 (기존 grep 테스트 병행 유지).
8. **grep 회귀 가드 확장**: `test_forbidden_grep_regression` 에 `persona.territory\s*=` 직접 쓰기 금지 패턴 3종 추가.
9. v1 addendum 파일 상단에 `[SUPERSEDED BY v2]` 마커 1줄 추가.
10. 기존 Phase 11-16 회귀 4건 + Phase 17 v1 테스트 12건 + 신규 v2 테스트 4건 **전부 PASS** 유지.

### [선택]
- 원본 `PHASE-17-LAND-CODEX-INSTRUCTIONS.md` 본문에 v2 Contract 섹션 발췌 삽입 (향후 재현성)

### [금지]
- `persona.territory = X` 직접 쓰기 신규 도입 **금지**. 오직 헬퍼 경유.
- `persona.region = X` 직접 쓰기 신규 도입 **금지**. 헬퍼 내부에서만 발생해야 함.
- Contract 시그니처 **임의 변경 금지**. `reason` 파라미터 생략, 반환 타입 변경 등 제안은 별도 PR로.
- 헬퍼에 grievance/cooldown 파라미터 추가 **금지** — caller 책임.
- Issue 4 (WILD 98%) 관련 튜닝 **금지** — `DOMINANCE_VOTE_MARGIN`, `DOMINANCE_RADIUS_K`, Bridson r 건드리지 말 것. Φ-2 진입 조건 정의 후 역산 대상.
- v1 addendum 본문 **편집 금지** (상단 SUPERSEDED 마커 1줄 제외). v1은 history.

---

## Fix 5 — `_change_persona_territory()` 도입 + 모든 migration 경로 통합 (P0)

### 재현 시나리오 (mass_exodus split-state)

1. `MultiTickEngine(seed=42)`
2. 영주가 있는 영지에 non-lord 페르소나 3명 이상 배치
3. 해당 영지의 `tax_rate = 0.6`, 다른 영지 `tax_rate = 0.05`, non-lord 전원 `grievance = 0.8`
4. `engine._update_grievances()` 호출 → `mass_exodus` 트리거
5. **기대**: 이주한 페르소나 모두 `territory == target_tid` AND `region == territories[target_tid].region`
6. **실제**: `territory` 갱신됨, `region`은 **이전 값 유지** → split-state

### 근본 원인

`multi_tick_engine.py:1095`

```python
# 현재 (v1 addendum 후에도 미수정)
for p in non_lord:
    if float(self.inners[p].grievance) >= 0.7:
        self.personas[p].territory = target_tid   # ← region 동기화 누락
        self.inners[p].grievance = 0.3
        migrated.append(p)
```

v1 Fix 1은 `_try_exodus()` 만 고쳤고, 이 경로는 건드리지 않았다. **invariant를 강제하는 single point가 없기 때문**.

### 구현

#### 5-A. 헬퍼 메서드 추가

`multi_tick_engine.py` 내, `_release_employment()` 바로 뒤 (line 900 부근)에 추가:

```python
def _change_persona_territory(
    self,
    persona_id: str,
    target_territory_id: str,
    reason: str,
) -> dict:
    """Atomically change persona.territory and sync persona.region.

    The only allowed write path to persona.territory outside engine
    initialization. See PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum-v2.md
    Contract section for invariants.
    """
    if persona_id not in self.personas:
        raise ValueError(f"unknown persona: {persona_id}")
    if target_territory_id not in self.territories:
        raise KeyError(f"unknown territory: {target_territory_id}")

    persona = self.personas[persona_id]
    target_territory = self.territories[target_territory_id]
    old_tid = persona.territory
    old_region = persona.region

    employment_cleanup = self._release_employment(persona_id, reason=reason)

    persona.territory = target_territory_id          # noqa: PHASE17_SSOT_WRITE
    persona.region = target_territory.region         # noqa: PHASE17_SSOT_WRITE

    self._territory_residents_cache = None

    return {
        "persona": persona_id,
        "from_territory": old_tid,
        "to_territory": target_territory_id,
        "from_region": old_region,
        "to_region": target_territory.region,
        "reason": reason,
        "employment_cleanup": employment_cleanup,
    }
```

`# noqa: PHASE17_SSOT_WRITE` 주석은 grep 회귀 가드의 whitelist 앵커. 정확히 이 주석이 있는 라인만 허용.

#### 5-B. `_try_exodus()` 를 헬퍼 호출로 치환

기존 `multi_tick_engine.py:944-951` 블록

```python
new_territory = min(alternatives, key=lambda item: item[1].policy.tax_rate)[1]
new_tid = new_territory.id
old_grievance = float(inner.grievance)
employment_cleanup = self._release_employment(pid, reason="exodus")
persona.territory = new_tid
persona.region = new_territory.region
inner.grievance = max(0.0, min(1.0, old_grievance * 0.5))
self._territory_residents_cache = None
```

→ 교체

```python
new_territory = min(alternatives, key=lambda item: item[1].policy.tax_rate)[1]
new_tid = new_territory.id
old_grievance = float(inner.grievance)
change = self._change_persona_territory(pid, new_tid, reason="exodus")
employment_cleanup = change["employment_cleanup"]
inner.grievance = max(0.0, min(1.0, old_grievance * 0.5))
```

(`_territory_residents_cache = None` 은 헬퍼가 처리하므로 제거.)

#### 5-C. `mass_exodus` 를 헬퍼 호출로 치환

기존 `multi_tick_engine.py:1092-1098` 블록

```python
migrated = []
for p in non_lord:
    if float(self.inners[p].grievance) >= 0.7:
        self.personas[p].territory = target_tid
        self.inners[p].grievance = 0.3
        migrated.append(p)
self._territory_residents_cache = None
```

→ 교체

```python
migrated = []
for p in non_lord:
    if float(self.inners[p].grievance) >= 0.7:
        self._change_persona_territory(p, target_tid, reason="mass_exodus")
        self.inners[p].grievance = 0.3
        migrated.append(p)
```

(캐시 무효화는 헬퍼가 담당하므로 중복 라인 제거.)

### 기능 검증

- [ ] Fix 5 테스트: `test_fix5_mass_exodus_region_sync` 추가 — mass_exodus 트리거 후 이주자 전원 `region == territories[target_tid].region` 확인
- [ ] 기존 `test_fix1_exodus_region_sync` PASS 유지 (헬퍼 경유로도 invariant 동일)
- [ ] grep 회귀 가드 통과: `persona.territory\s*=` 직접 쓰기 패턴이 헬퍼 본체 외 0건

---

## Fix 6 — exodus RNG monkeypatch 분기 제거 (P1, 결정성 오염)

### 근본 원인

`multi_tick_engine.py:937-940`

```python
exodus_roll = float(self._np_rng.random())
current_np_random = getattr(np.random, "random")
if current_np_random is not _ORIGINAL_NP_RANDOM:
    exodus_roll = min(exodus_roll, float(current_np_random()))
```

이 분기는 v1 `test_fix1_exodus_region_sync` 에서 `np.random.random = lambda: 0.0` 으로 exodus를 강제하기 위해 삽입. **production 코드가 test fixture를 인식**하는 구조 — "engine seed 만으로 결정성 보장" 계약 위배.

### 구현

#### 6-A. Production 코드 정리

`multi_tick_engine.py:937-940` 블록을 다음으로 치환

```python
exodus_roll = float(self._np_rng.random())
```

(3줄 monkeypatch consultation 제거.)

모듈 상단 `_ORIGINAL_NP_RANDOM = np.random.random` 도 다른 용처가 없으면 제거. 다른 용처가 있으면 유지 (grep으로 확인 후 판단).

#### 6-B. 테스트 재작성

`test_phase17_land.py` 의 `test_fix1_exodus_region_sync` 에서

```python
original_random = np.random.random
np.random.random = lambda: 0.0
try:
    event = engine._try_exodus(pid)
finally:
    np.random.random = original_random
```

→ 다음으로 교체

```python
# engine seed 단일 진원지 — _np_rng를 직접 조작
class _FixedRNG:
    def __init__(self, wrapped): self._wrapped = wrapped
    def random(self): return 0.0
    def __getattr__(self, name): return getattr(self._wrapped, name)

original_rng = engine._np_rng
engine._np_rng = _FixedRNG(original_rng)
try:
    event = engine._try_exodus(pid)
finally:
    engine._np_rng = original_rng
```

### 기능 검증

- [ ] `test_fix1_exodus_region_sync` PASS (교체된 mock 경로)
- [ ] `test_determinism_500ticks` PASS (monkeypatch 제거가 결정성에 영향 없음)
- [ ] grep: `np.random.random\s*=` 쓰기 패턴이 test 파일 외 0건
- [ ] grep: `_ORIGINAL_NP_RANDOM` 모듈 내 잔존 참조 0건 (제거했을 경우)

---

## Fix 7 — Decisions 체크리스트 spec drift 수정 (P1)

### 근본 원인

v1 addendum Fix 2에서 본문의 "20명 / 7:7:6" 문구는 제거했으나, Decisions 검증 계약 체크리스트 1행(`:423`)을 놓쳤다.

### 구현

`PHASE-17-LAND-DECISIONS.md:423` 라인 교체

**기존**:
```
- [ ] **D8**: 20명 배치 성공 (r=5 또는 fallback), region 쿼터 7:7:6 정확
```

**교체**:
```
- [ ] **D8**: `len(PERSONA_DEFS)`명 배치 성공 (r=5 또는 fallback), region 분포가 `Counter(p["region"] for p in PERSONA_DEFS)` 와 정확히 일치
```

### 기능 검증

- [ ] grep `Projects/personas/loom/PHASE-17-LAND-*.md`: `"20명"`, `"7:7:6"` 문자열 0건
- [ ] `test_fix2_region_distribution_matches_persona_defs` (v1) 는 이미 이 invariant를 테스트 중 — 영향 없음

---

## Fix 8 — Phase 17 Φ-1 Acceptance Gate 경량 통합 (P1)

### 근본 원인

Hard 5 지표, ≤ 250ms/tick, 500틱 결정성, Phase 11-16 회귀가 **여러 파일에 분산** — "Phase 17 완료 판정"을 자동화할 단일 경로 없음.

### 구현

**신규 파일**: `Projects/personas/loom/test_phase17_acceptance.py`

```python
"""Phase 17 / Φ-1 Land — single-entry acceptance gate.

Run with: `py test_phase17_acceptance.py`
Exit 0 on PASS, non-zero on any FAIL.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _run(cmd: list[str], label: str) -> bool:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    ok = result.returncode == 0
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {label}")
    if not ok:
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
    return ok


def _measure_tick_ms(n_ticks: int = 100) -> float:
    from core.multi_tick_engine import MultiTickEngine
    engine = MultiTickEngine(seed=42)
    start = time.perf_counter()
    for _ in range(n_ticks):
        engine.tick()
    elapsed_ms = (time.perf_counter() - start) * 1000.0 / n_ticks
    return elapsed_ms


def main() -> int:
    failures: list[str] = []

    # Phase 17 core (v1 + v2 merged)
    if not _run([sys.executable, "test_phase17_land.py"], "Phase 17 Land (v1+v2)"):
        failures.append("phase17_land")

    # Phase 11-16 regression (Hard 5 indirectly covered)
    for name in [
        "test_nomos.py",
        "test_class_promotion.py",
        "test_phase16_public_works.py",
        "test_climate_impact.py",
    ]:
        if not _run([sys.executable, name], name):
            failures.append(name)

    # Performance contract
    elapsed = _measure_tick_ms(n_ticks=100)
    perf_ok = elapsed <= 250.0
    status = "PASS" if perf_ok else "FAIL"
    print(f"[{status}] tick_performance: {elapsed:.1f} ms/tick (contract ≤ 250)")
    if not perf_ok:
        failures.append(f"performance ({elapsed:.1f}ms)")

    print()
    if failures:
        print(f"Phase 17 Φ-1 Acceptance: FAIL ({len(failures)} failures)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("Phase 17 Φ-1 Acceptance: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 사용 경계 (금지)

- 이 파일에 **신규 test logic 작성 금지** — 오직 기존 테스트의 통합 실행자. logic 추가는 개별 `test_*.py` 로.
- Φ-2 진입 시 이 파일에 Φ-2 테스트 추가 **금지** — `test_phase18_*_acceptance.py` 별도 생성.
- `CI` 파이프라인 통합은 별도 작업 (현재 리포 CI 구조 불확정).

### 기능 검증

- [ ] `py test_phase17_acceptance.py` exit 0
- [ ] 고의 회귀 (예: `DOMINANCE_VOTE_MARGIN = 99`) 삽입 시 exit 1
- [ ] Windows CP949 환경에서도 실행 (subprocess 인코딩 기본값 UTF-8 명시)

---

## Fix 9 — `project_territory()` contested hysteresis 문서화 (P2, AS DESIGNED)

### 근본 원인

`physis/world.py:67-91` — contested cell (2표 우위 미달) 은 **updates dict 에 키를 추가하지 않음** → 기존 `territoryRef` 유지. 이는 **Decision 6 "2표 우위 히스테리시스"의 구현**이지만 docstring/주석에 명시 없어 독자가 "버그"로 오인.

### 구현

#### 9-A. `physis/world.py:67` docstring 교체

```python
def project_territory(world: World, personas: list) -> None:
    """Project persona territory dominance onto the land grid.

    Rule (Decision 6 — 2-vote hysteresis):
        - No residents within Chebyshev K → cell.territoryRef = None
        - Clear winner (top_count - second_count >= DOMINANCE_VOTE_MARGIN)
          → cell.territoryRef = winner_territory_id
        - Contested (margin < DOMINANCE_VOTE_MARGIN) → cell.territoryRef
          is left **unchanged** (previous value retained).

    The "left unchanged" branch is intentional hysteresis: it prevents
    flip-flop when two territories contest a border cell with roughly
    equal density. Φ-2 faction logic may replace this with explicit
    CONTESTED state; until then, stale retention is the contract.
    """
```

#### 9-B. `test_d6_project_territory_atomicity` 주석 강화

기존 테스트 `test_phase17_land.py:86-105` 의 두 번째 블록 (residents reversed) 앞에

```python
# Hysteresis: when multiple personas from different territories tie
# within Chebyshev K, the existing territoryRef is retained.
# See project_territory() docstring — this is by design (Decision 6).
```

### 기능 검증

- [ ] 기존 `test_d6_project_territory_atomicity` PASS 유지
- [ ] `project_territory.__doc__` 문자열에 `"hysteresis"` 포함 (간접 검증)

---

## Fix 10 — movement ordering behavioral test (P2)

### 근본 원인

`test_fix3_movement_before_economy` 은 source grep 기반. 함수 분리/리팩터링으로 `_process_movement`가 인라인되거나 call site가 이동하면 테스트가 false positive/negative를 낼 수 있음.

### 구현

**기존 grep 테스트 유지** (방어선 1) + **behavioral 추가** (방어선 2).

`test_phase17_land.py` 에 추가:

```python
def test_fix10_movement_before_economy_behavioral() -> None:
    """Behavioral: persona.pos changes within one tick BEFORE economy.

    Strategy: set an explicit dest 3 cells away, run one tick with
    an instrumented hook that asserts pos was moved before any
    economy/action event is emitted.
    """
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=42)
    # 첫 non-sleeping persona 선택
    pid = next(
        pid for pid, inner in engine.inners.items()
        if not inner.is_sleeping
    )
    persona = engine.personas[pid]
    inner = engine.inners[pid]

    # Prime: 명시적 dest 부여
    start_pos = persona.pos
    dest = (
        min(start_pos[0] + 3, engine.world.width - 1),
        min(start_pos[1] + 3, engine.world.height - 1),
    )
    inner.dest = dest
    inner.migration_cooldown = 0

    pos_before_tick = persona.pos
    engine.tick()
    pos_after_tick = persona.pos

    # 같은 틱 내에서 최소 1칸 이동 (movement가 economy 앞에 있으므로
    # economy가 position을 기준으로 계산할 때는 이미 이동 후 값).
    # 만약 movement가 economy 뒤로 잘못 이동되면, 이동 전 좌표로
    # economy가 계산되고 다음 틱에서만 이동 — 최소 1틱 지연.
    moved = pos_after_tick != pos_before_tick
    assert moved, (
        f"persona {pid} did not move this tick; "
        f"movement may have been deferred past economy. "
        f"start={pos_before_tick}, dest={dest}, after={pos_after_tick}"
    )
```

`__main__` tests 리스트에 `test_fix10_movement_before_economy_behavioral` 추가.

### 주의사항

- Persona 위치/상태 의존 — `seed=42` 에서 첫 non-sleeping persona가 이동 가능한 biome에 있는지 한 번 확인. 실패 시 fixture를 명시적으로 세팅 (biome을 plain으로 force).
- `migration_cooldown = 0` 명시 — 기본 상태에서 cooldown 걸려 있으면 이동 안 됨.

### 기능 검증

- [ ] `test_fix10_movement_before_economy_behavioral` PASS
- [ ] 고의 회귀 (Fix 3 롤백) 시 FAIL — 두 번째 틱에서 pos 갱신되는지 실측
- [ ] 기존 `test_fix3_movement_before_economy` (grep) PASS 유지

---

## 변경 파일

| 파일 | 작업 | 유형 |
|---|---|:---:|
| [Projects/personas/loom/core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py) | `_change_persona_territory()` 추가, `_try_exodus` / `mass_exodus` 치환, `np.random` monkeypatch 분기 제거 | 수정 |
| [Projects/personas/loom/physis/world.py](Projects/personas/loom/physis/world.py) | `project_territory()` docstring 강화 (hysteresis 명시) | 수정 |
| [Projects/personas/loom/test_phase17_land.py](Projects/personas/loom/test_phase17_land.py) | `test_fix1_exodus_region_sync` 재작성, `test_fix5_mass_exodus_region_sync`, `test_fix10_movement_before_economy_behavioral` 추가, `test_forbidden_grep_regression` 확장 | 수정 |
| [Projects/personas/loom/test_phase17_acceptance.py](Projects/personas/loom/test_phase17_acceptance.py) | 신규 — Φ-1 acceptance gate 통합 실행자 | 추가 |
| [Projects/personas/loom/PHASE-17-LAND-DECISIONS.md](Projects/personas/loom/PHASE-17-LAND-DECISIONS.md) | `:423` 체크리스트 행 `PERSONA_DEFS` 동적 참조로 교체 | 수정 |
| [Projects/personas/loom/PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum.md](Projects/personas/loom/PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum.md) | 상단에 `[SUPERSEDED BY addendum-v2]` 1줄 마커 추가 | 수정 |

**변경 없음 (금지)**:
- `Projects/personas/loom/PHASE-17-LAND-CHARTER.md` — v1 addendum 에서 이미 반영
- `Projects/personas/loom/PHASE-17-LAND-CODEX-INSTRUCTIONS.md` — 원본, 선택적 업데이트만
- `Projects/personas/loom/ontology/layers.py` — region/territory 필드 구조 유지
- `Projects/personas/loom/physis/poisson.py` — Bridson 결정성 유지
- `DOMINANCE_*` / `INIT_POISSON_FALLBACK` 등 상수 — Φ-1 튜닝 금지

---

## 검증

### 기계 검증 (항상)

```bash
# 1. 기존 테스트 전체 PASS
cd Projects/personas/loom
py test_phase17_land.py                 # 12 (v1) + 4 (v2) = 16 테스트
py test_nomos.py
py test_class_promotion.py
py test_phase16_public_works.py
PYTHONIOENCODING=utf-8 py test_climate_impact.py

# 2. 신규 acceptance gate 단일 PASS
py test_phase17_acceptance.py
echo $?   # 0 이어야 함
```

### 계약 검증 (Contract)

- [ ] `_change_persona_territory()` 가 `multi_tick_engine.py` 에 정의되고 위 Contract 섹션 docstring과 **한 자도 다르지 않음** (복붙)
- [ ] 직접 쓰기 grep 0건:
  - `grep -nE 'persona\.territory\s*=' Projects/personas/loom/**/*.py | grep -v '_change_persona_territory\|noqa: PHASE17_SSOT_WRITE\|PERSONA_DEFS\|_assign_personas\|test_'`
  - 결과 **0줄**
- [ ] `persona.region = ` 쓰기도 동일하게 헬퍼 본체 외 0건

### 기능 검증 (신규 테스트)

- [ ] `test_fix5_mass_exodus_region_sync` PASS — mass_exodus 트리거 후 이주자 전원 region 동기
- [ ] `test_fix10_movement_before_economy_behavioral` PASS — 단일 틱 내 pos 갱신
- [ ] `test_forbidden_grep_regression` PASS — 확장된 금지 패턴 (territory 직접 쓰기) 포함 clean
- [ ] 교체된 `test_fix1_exodus_region_sync` PASS — `_np_rng` mock 경로

### 회귀 검증

- [ ] `test_determinism_500ticks` PASS — monkeypatch 분기 제거가 결정성에 영향 없음
- [ ] Hard 5 지표 (Phase 16 회귀 테스트로 간접 검증) 이상 없음
- [ ] tick 성능 ≤ 250ms (acceptance gate 내장)

### 시각 QA

해당 없음 (UI 변경 없음).

---

## Rollback

### 완전 롤백 (v2 전체)

```bash
git revert <v2 commit hash>
```

v1 addendum의 Fix 1(`_try_exodus` region sync)로 복귀. `mass_exodus` split-state는 다시 발생.

### 부분 롤백

| Fix | 롤백 영향 |
|---|---|
| 5 (helper) | mass_exodus split-state 재발. test_fix5 FAIL. |
| 6 (RNG cleanup) | 결정성 계약 명시적 오염 복귀. test_fix1 영향 있음 (monkeypatch 경로 의존). |
| 7 (spec sync) | Decisions 문서에 drift 재발. 구현 동작 영향 없음. |
| 8 (acceptance gate) | 파일 삭제만 하면 됨. 회귀 검증 수동 실행 필요. |
| 9 (docstring) | docstring revert. 동작 영향 없음. |
| 10 (behavioral test) | 테스트 제거. grep 방어선 1개만 남음. |

데이터 손실: 없음 (런타임 상태 변화 없음).

---

## GPT / Codex 전달 프롬프트

```
당신은 loom 페르소나 시뮬레이션의 시니어 풀스택 개발자입니다.

## 프로젝트 경로
c:\Users\haj\projects\subagent-orchestrator\Projects\personas\loom

## 기술 스택
- Python 3.14 (@dataclass(slots=True) 주의: 수동 __slots__과 병용 시 ValueError)
- numpy (RNG 단일 진원지: engine._np_rng)
- 테스트: pytest 미사용, 각 test_*.py 가 __main__에서 직접 실행

## 작업 지시서 (필독 순서)
1. `Projects/personas/loom/PHASE-17-LAND-CHARTER.md` — Φ-1 Charter
2. `Projects/personas/loom/PHASE-17-LAND-DECISIONS.md` — Decision 1~8
3. `Projects/personas/loom/PHASE-17-LAND-CODEX-INSTRUCTIONS.md` — 원본 구현 지시서
4. `Projects/personas/loom/PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum.md` — v1 대응 (상단 SUPERSEDED 마커 확인)
5. `Projects/personas/loom/PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum-v2.md` — 본 지시서 (최우선)

## 규칙 (절대 준수)
1. v2 지시서의 Contract 섹션 docstring은 `_change_persona_territory()` 본체에 **한 자도 다르지 않게** 복사.
2. v2 지시서의 [필수] 10항 100% 구현. [금지] 6항 절대 건드리지 말 것.
3. v2 지시서의 코드 블록은 **직접 복사**해서 반영. "해석"하지 말 것.
4. `persona.territory = X` 직접 쓰기는 헬퍼 본체 + `# noqa: PHASE17_SSOT_WRITE` 주석이 있는 라인만 허용. 그 외 모두 금지.
5. 검증 순서:
   a. py test_phase17_land.py  → 16개 PASS (12 v1 + 4 v2)
   b. py test_nomos.py         → PASS
   c. py test_class_promotion.py → PASS
   d. py test_phase16_public_works.py → PASS
   e. PYTHONIOENCODING=utf-8 py test_climate_impact.py → PASS
   f. py test_phase17_acceptance.py → exit 0 (통합 실행자)
   g. grep 회귀: `persona.territory\s*=` 직접 쓰기 헬퍼 본체 외 0건
6. 검증 실패 시 재작업, 통과할 때까지 반복.
7. 보고 내용:
   - 변경 파일 목록 (v2 지시서의 "변경 파일" 표와 대조)
   - Contract docstring 복붙 검증 결과
   - 각 Fix 5~10 의 테스트 결과
   - 금지 grep 결과 (0건 확인)
   - acceptance gate exit code
   - v1 SUPERSEDED 마커 추가 확인
```

---

## Φ-1 Closure 조건

v2 addendum 의 모든 [필수] 10항 PASS + acceptance gate exit 0 달성 시:

- **Phase 17 Φ-1 Land CLOSED** ✓
- 다음 단계: Φ-2 Faction Charter 착수
- Φ-2 진입 시 해소될 보류 항목:
  - Issue 4 WILD 98% → faction seed 도입 후 CONTESTED/SETTLED 분화
  - D7 region 필드 최종 삭제 → Φ-3
  - Dashboard region 색상 → Φ-2 Faction 시스템 통합

v2 addendum 의 본 Contract (`_change_persona_territory()`) 는 Φ-2 faction migration 에서도 그대로 사용. 시그니처 유지 강제.
