# Phase 17 / Φ-1 Land — Codex Instructions Addendum v2.1 (2차 리뷰 대응)

> 긴급도: 높음
> 선행 조건: [PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum-v2.md](PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum-v2.md) 구현 완료 (16/16 PASS)
> 작업 유형: 혼합 (버그 수정 + 리팩토링 + 테스트)
> DB migration: 없음
> 외부 의존: 없음 (Python 표준 라이브러리 `hashlib` 사용)

---

## 배경

v2 구현 후 2차 시니어 리뷰에서 **Partial compliance / REQUEST_CHANGES** 판정. v2는 `_change_persona_territory()` helper로 "단일 진원지"를 구축했지만, **결정성 계약**과 **ordering backstop**에서 v1과 동일한 표면 해결 패턴이 재발. Contract를 **선언만 하고 증명하지 않은** 상태.

### 근본 원인 (CLAUDE.md Rule 17-20 적용)

- 표면: hash() 기반 보조 RNG 5곳 → 결정성 깨짐 → seed=42 계약 위반
- 꼬리 추적: 왜 깨졌나? → `hash()`는 PYTHONHASHSEED salt → process별 상이 → 같은 코드 경로가 process마다 다른 난수 소비
- 근본: **RNG 파생 경로가 engine에 중앙화되지 않음**. `np.random.default_rng(...)` 호출부가 로컬 ad-hoc seed를 조립.
- 처방: `_derive_rng(*keys)` helper로 중앙화. engine._seed + tick + stable hash → 단일 진원지.

검증 근거:
- 실측: hash() 기반 RNG = multi_tick_engine.py 9곳 + climate_engine.py 1곳 (리뷰는 5곳만 명시, 실제 10곳)
- seed=42 동일 설정 3 프로세스 → snapshot digest 3개 상이 (d615c5c.., 896873a.., 5b75346..)
- 문서 계약 3곳 위반: [PHASE-17-LAND-CODEX-INSTRUCTIONS.md:23](PHASE-17-LAND-CODEX-INSTRUCTIONS.md#L23), [PHASE-17-LAND-DECISIONS.md:27](PHASE-17-LAND-DECISIONS.md#L27), [PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum-v2.md:707](PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum-v2.md#L707)

Evidence: 2차 시니어 리뷰 판정 (Fix 11~16 도입).

---

## 작업 범위

### [필수] — MUST (Φ-1 Closure 차단)

1. **Fix 11 (High)**: 중앙 RNG 파생 helper `_derive_rng()` 도입 + hash() 기반 10곳 전부 교체
2. **Fix 12 (High)**: `_change_persona_territory()` Contract I1~I4 + error boundary 직접 검증 테스트 5건
3. **Fix 13 (High)**: `_phase_trace` 계측 훅 도입 + Fix 10을 ordering instrumentation test로 재작성

### [선택] — SHOULD (Φ-1 Closure 강권)

4. **Fix 14 (Medium)**: `test_phase17_acceptance.py` 에 migration 계열 테스트 2건 추가
5. **Fix 15 (Medium)**: `test_forbidden_grep_regression` 에 region direct write + hash() RNG 패턴 가드 추가

### [선택] — TRIVIAL

6. **Fix 16 (Low)**: v1 addendum 하단 SUPERSEDED 마커 1줄 제거 (상단 1줄만 유지)

### [금지]

- `_derive_rng()` 시그니처 변경 금지 — `(*keys) -> np.random.Generator` 고정
- `hashlib` 외의 cross-process hash 방법 도입 금지 (md5/sha256 등 과도함, blake2b 고정)
- Fix 10의 기존 grep 테스트 **제거 금지** — behavioral test **추가** (`test_fix10_movement_before_economy_behavioral`는 유지)
- `_phase_trace`를 운영 환경에서 default 활성화 금지 — None 체크로 zero-cost
- v1 addendum 본문 편집 금지 (하단 마커 1줄 삭제만 허용)
- climate_engine.py의 기존 기후 시뮬 로직 **동작 변경 금지** — seed 파생 방식만 교체, 결과 분포 유지

---

## Fix 11 — 중앙 RNG 파생 helper + hash() 기반 RNG 전부 교체 (High)

### 실측 위치 (10곳)

**multi_tick_engine.py (9곳)**:

| 라인 | 현재 코드 |
|---|---|
| 1349 | `rng = np.random.default_rng(self.time.tick + hash(lord_id) % 10000)` |
| 1392 | `rng = np.random.default_rng(self.time.tick * 100 + hash(pid) % 10000)` |
| 2102 | `rng_apt = np.random.default_rng(self.time.tick + hash(student_id) % 10000)` |
| 2406 | `rng_d = np.random.default_rng(self.time.tick + hash(pid) % 10000 + 42)` |
| 3538 | `rng = np.random.default_rng(self.time.tick * 1000 + hash(pid) % 10000)` |
| 3622 | `rng = np.random.default_rng(hash((pid, region, age, "init_knowledge")) & 0xFFFFFFFF)` |
| 3694 | `rng = np.random.default_rng(hash((pid, self.time.tick, "forage")) & 0xFFFFFFFF)` |
| 3780 | `rng = np.random.default_rng(hash((pid, self.time.tick, "emergency_forage")) & 0xFFFFFFFF)` |
| 3817 | `rng = np.random.default_rng(hash((pid, self.time.tick, food.id, "effect")) & 0xFFFFFFFF)` |

**physis/climate_engine.py (1곳)**:

| 라인 | 현재 코드 |
|---|---|
| 169 | `seed_val = hash((day, hour, region_id, channel)) & 0xFFFFFFFF` |

### 근본 처방: helper 도입

**multi_tick_engine.py**, `MultiTickEngine.__init__` 근처 (세션 내 단 한 번 정의). 기존 `self._np_rng: np.random.Generator = np.random.default_rng(self._seed)` (현재 L167) **유지**. helper 두 개 신규:

```python
import hashlib
import numpy as np

# ── module-level helper (class 밖, import 아래) ──
def _stable_int(*keys) -> int:
    """Deterministic cross-process 8-byte int from arbitrary keys.

    Replaces Python built-in `hash()` which is PYTHONHASHSEED-salted
    and differs across processes. Uses blake2b for stability.
    """
    h = hashlib.blake2b(digest_size=8)
    for k in keys:
        h.update(str(k).encode("utf-8"))
        h.update(b"\x00")
    return int.from_bytes(h.digest(), "big")


# ── MultiTickEngine 내부 method ──
def _derive_rng(self, *keys) -> np.random.Generator:
    """Per-call RNG stream derived deterministically from (seed, tick, keys).

    **The only allowed way** to create a sub-stream RNG inside
    MultiTickEngine. Direct `np.random.default_rng(...)` calls
    outside __init__ are forbidden (enforced by grep guard).

    Guarantees:
        - Identical across processes given identical (seed, tick, keys)
        - Different `keys` tuples yield independent streams (tag isolation)
        - Does NOT consume `self._np_rng` state (independent sub-stream)

    Args:
        *keys: Stable identifiers. First key should be a string tag
               for stream namespacing ("forage", "job_seeking", ...).
               Persona ids, territory ids, tick numbers all acceptable.

    Example:
        rng = self._derive_rng("forage", pid, self.time.tick)
        if rng.random() < prob: ...
    """
    seed_seq = np.random.SeedSequence([
        self._seed,
        _stable_int(*keys),
    ])
    return np.random.default_rng(seed_seq)
```

### 교체 규칙 (multi_tick_engine.py 9곳)

각 위치에서 `hash(...)` 표현을 제거하고 `self._derive_rng(tag, *keys)` 로 치환. **tag는 용도별 stream 격리 보장**.

| 라인 | 교체 후 |
|---|---|
| 1349 | `rng = self._derive_rng("lord_job_create", lord_id, self.time.tick)` |
| 1392 | `rng = self._derive_rng("job_seek", pid, self.time.tick)` |
| 2102 | `rng_apt = self._derive_rng("aptitude", student_id, self.time.tick)` |
| 2406 | `rng_d = self._derive_rng("deliberation", pid, self.time.tick)` |
| 3538 | `rng = self._derive_rng("wild_food_choose", pid, self.time.tick)` |
| 3622 | `rng = self._derive_rng("init_knowledge", pid, region, age)` |
| 3694 | `rng = self._derive_rng("forage", pid, self.time.tick)` |
| 3780 | `rng = self._derive_rng("emergency_forage", pid, self.time.tick)` |
| 3817 | `rng = self._derive_rng("food_effect", pid, self.time.tick, food.id)` |

### climate_engine.py 처방 (1곳)

`ClimateEngine` 은 `MultiTickEngine` 과 독립 존재. 두 가지 선택지 중 **B** 채택:

**A 기각**: engine._np_rng를 ClimateEngine에 주입 → ClimateEngine 생성 시점 의존성 역전, 기존 시그니처 변경 영향 큼
**B 채택**: ClimateEngine 자체에 동일 패턴 (`_stable_int` 재사용 + 자체 `seed`)

physis/climate_engine.py 상단 import 추가 + 클래스 내부 교체:

```python
# physis/climate_engine.py 상단
import hashlib

def _stable_int(*keys) -> int:
    """Same contract as multi_tick_engine._stable_int. Duplicated
    to keep physis package free of core dependency.
    """
    h = hashlib.blake2b(digest_size=8)
    for k in keys:
        h.update(str(k).encode("utf-8"))
        h.update(b"\x00")
    return int.from_bytes(h.digest(), "big")
```

`ClimateEngine.__init__` 에 `self._seed: int = 42` 추가 (기본값, 필요 시 외부에서 override). L169 교체:

```python
# Before
seed_val = hash((day, hour, region_id, channel)) & 0xFFFFFFFF

# After
seed_val = _stable_int(self._seed, day, hour, region_id, channel) & 0xFFFFFFFF
```

`MultiTickEngine.__init__` 에서 `self.climate = ClimateEngine()` (현재 L170) 다음 줄 추가:

```python
self.climate._seed = self._seed
```

이렇게 하면 `MultiTickEngine(seed=42)` 생성 시 climate도 자동으로 same seed 공유.

### 검증 (Fix 11 전용)

**test_phase17_land.py 에 신규 추가**:

```python
def test_fix11_cross_process_determinism() -> None:
    """Two fresh engines with seed=42 produce identical snapshots
    across 80 ticks. Regression against hash()-based RNG.
    """
    import subprocess
    import sys
    import hashlib
    import json

    script = """
import sys, json, hashlib
sys.path.insert(0, r'{root}')
from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine
engine = MultiTickEngine(seed=42)
for _ in range(80):
    engine.tick()
snap = sorted([
    (pid, tuple(persona.pos), persona.territory, persona.region,
     round(engine.inners[pid].energy_pool, 6),
     round(engine.inners[pid].grievance, 6))
    for pid, persona in engine.personas.items()
])
h = hashlib.sha256(json.dumps(snap, default=str).encode()).hexdigest()
print(h)
""".format(root=str(ROOT).replace("\\\\", "\\\\\\\\"))

    digests = set()
    for _ in range(3):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=120,
            env={"PYTHONHASHSEED": "random"},  # salt intentionally different
        )
        assert result.returncode == 0, f"subprocess failed: {result.stderr}"
        digests.add(result.stdout.strip().splitlines()[-1])

    assert len(digests) == 1, (
        f"cross-process determinism violated: {digests}. "
        f"hash()-based RNG regression suspected."
    )
```

**검증 순서**:

1. `py test_phase17_land.py` → 17/17 PASS (기존 16 + test_fix11_cross_process_determinism 1)
2. 수동 재확인: 터미널 3개에서 `py -c "<80tick digest script>"` → 3회 모두 동일 digest

---

## Fix 12 — Helper Contract 직접 검증 테스트 (High)

### 현재 gap

v2 는 Contract I1~I4 를 docstring 으로 선언. test_fix1_exodus_region_sync / test_fix5_mass_exodus_region_sync 는 **간접 경로만** 검증. helper 자체의 atomicity 불변식과 error boundary 는 직접 호출로 검증되지 않음.

### 신규 테스트 5건 (test_phase17_land.py 에 추가)

```python
def _setup_helper_fixture():
    """Shared fixture for helper direct tests."""
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine
    engine = MultiTickEngine(seed=42)
    pid = next(
        pid for pid, persona in sorted(engine.personas.items())
        if pid != engine.territories[persona.territory].lord_id
    )
    persona = engine.personas[pid]
    source_tid = persona.territory
    target_tid = next(tid for tid in engine.territories if tid != source_tid)
    return engine, pid, source_tid, target_tid


def test_contract_i1_territory_updated() -> None:
    """I1: persona.territory == target_territory_id after helper return."""
    engine, pid, source_tid, target_tid = _setup_helper_fixture()
    result = engine._change_persona_territory(pid, target_tid, "test_i1")
    assert engine.personas[pid].territory == target_tid
    assert result["from_territory"] == source_tid
    assert result["to_territory"] == target_tid


def test_contract_i2_region_synced() -> None:
    """I2: persona.region == territories[target_tid].region."""
    engine, pid, _source_tid, target_tid = _setup_helper_fixture()
    engine._change_persona_territory(pid, target_tid, "test_i2")
    expected_region = engine.territories[target_tid].region
    assert engine.personas[pid].region == expected_region


def test_contract_i3_cache_invalidated() -> None:
    """I3: _territory_residents_cache is None after helper return."""
    engine, pid, _source_tid, target_tid = _setup_helper_fixture()
    # Prime the cache first
    _ = engine._territory_residents(target_tid) \
        if hasattr(engine, "_territory_residents") else None
    engine._change_persona_territory(pid, target_tid, "test_i3")
    assert engine._territory_residents_cache is None, (
        "cache must be invalidated by helper"
    )


def test_contract_i4_employment_released() -> None:
    """I4: employment in old territory is released."""
    engine, pid, source_tid, target_tid = _setup_helper_fixture()
    # Force-hire persona in source territory if possible
    lord_id = engine.territories[source_tid].lord_id
    if lord_id and lord_id != pid:
        job = engine.create_job(lord_id, "test_laborer", 5.0, "test")
        if job:
            engine.hire(job.id, pid)
            assert engine.personas[pid].employment_id is not None, (
                "fixture: persona must be employed before migration"
            )
            result = engine._change_persona_territory(pid, target_tid, "test_i4")
            assert engine.personas[pid].employment_id is None, (
                "I4 violated: employment not released"
            )
            assert "employment_cleanup" in result


def test_contract_raises_on_unknown_territory() -> None:
    """Error boundary: KeyError when target_territory_id does not exist."""
    engine, pid, _source_tid, _target_tid = _setup_helper_fixture()
    import pytest as _pytest  # graceful if pytest installed, else AssertionError
    try:
        engine._change_persona_territory(pid, "NONEXISTENT_TID", "test_err")
    except KeyError:
        return  # expected
    raise AssertionError("KeyError not raised for unknown territory")
```

### 검증

- `py test_phase17_land.py` → **22/22** PASS (기존 16 + Fix 11 의 1 + Fix 12 의 5)

---

## Fix 13 — Ordering Instrumentation Test (High)

### 현재 gap

[test_phase17_land.py:264](Projects/personas/loom/test_phase17_land.py#L264) `test_fix10_movement_before_economy_behavioral` 는 tick 전후 pos 차이만 본다. brain.tick() 이후 movement 가 발생해도 통과 가능 → ordering backstop 불완전.

### 근본 처방: `_phase_trace` 계측 훅

**multi_tick_engine.py**, `MultiTickEngine.__init__` 에 추가:

```python
# __init__ 내부, 기존 self._np_rng 초기화 아래
self._phase_trace: list[str] | None = None  # None = disabled (zero cost)
```

**3곳에 trace append 삽입**:

`tick()` 내부 각 페르소나 루프의 주요 분기점:

```python
# _process_movement(pid) 호출 직전 (현재 L317 "self._process_movement(pid)")
if self._phase_trace is not None:
    self._phase_trace.append(f"movement:{pid}:tick={self.time.tick}")
self._process_movement(pid)

# brain.tick(...) 호출 직전 (현재 "action, intensity, cost = brain.tick(...)")
if self._phase_trace is not None:
    self._phase_trace.append(f"action:{pid}:tick={self.time.tick}")
action, intensity, cost = brain.tick(...)

# _process_economy(pid, action) 호출 직전
if self._phase_trace is not None:
    self._phase_trace.append(f"economy:{pid}:tick={self.time.tick}")
self._process_economy(pid, action)
```

**운영 영향**: `None` 체크 1회만. production 기본 `None` 유지. zero-cost.

### 테스트 재작성 (test_phase17_land.py)

기존 `test_fix10_movement_before_economy_behavioral` (L264) 는 **유지** (regression 보조). 새로 추가:

```python
def test_fix10_ordering_instrumentation() -> None:
    """Direct ordering proof via _phase_trace: movement < action < economy
    for every persona, every tick.
    """
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=42)
    engine._phase_trace = []
    for _ in range(5):
        engine.tick()

    # Group trace entries by (pid, tick)
    from collections import defaultdict
    grouped: dict[tuple, list[tuple[int, str]]] = defaultdict(list)
    for idx, entry in enumerate(engine._phase_trace):
        phase, pid, tick_str = entry.split(":")
        tick = int(tick_str.split("=")[1])
        grouped[(pid, tick)].append((idx, phase))

    for (pid, tick), ordered in grouped.items():
        phases = [p for _, p in ordered]
        # movement must precede action, action must precede economy
        if "movement" in phases and "economy" in phases:
            m_idx = phases.index("movement")
            e_idx = phases.index("economy")
            assert m_idx < e_idx, (
                f"ordering violated for {pid}@{tick}: {phases}"
            )
        if "action" in phases and "economy" in phases:
            a_idx = phases.index("action")
            e_idx = phases.index("economy")
            assert a_idx < e_idx
        if "movement" in phases and "action" in phases:
            m_idx = phases.index("movement")
            a_idx = phases.index("action")
            assert m_idx < a_idx
```

### 검증

- `py test_phase17_land.py` → **23/23** PASS (기존 16 + Fix 11/12/13 = 1 + 5 + 1)
- 성능: `_phase_trace = None` 상태에서 500tick 전후 차이 ≤ 1% (기존 acceptance 250ms/tick 유지)

---

## Fix 14 — Acceptance Gate 확장 (Medium)

### 현재 gap

[test_phase17_acceptance.py:54-59](Projects/personas/loom/test_phase17_acceptance.py#L54) 는 land/nomos/class_promotion/public_works/climate 5건만 묶음. migration 계열 (SNN + region, collective action + territory) 회귀는 별도 파일에 남아 있음.

### 처방

test_phase17_acceptance.py 의 테스트 리스트에 추가:

```python
# 현재 (L54-59)
for name in [
    "test_nomos.py",
    "test_class_promotion.py",
    "test_phase16_public_works.py",
    "test_climate_impact.py",
]:

# 교체 후
for name in [
    "test_nomos.py",
    "test_class_promotion.py",
    "test_phase16_public_works.py",
    "test_climate_impact.py",
    "test_phase14b_snn_integration.py",   # 추가: SNN + region 회귀
    "test_phase15_collective_action.py",  # 추가: collective + territory 회귀
]:
```

### 검증

- `py test_phase17_acceptance.py` → exit 0, 7 파일 전부 PASS 리포트
- 성능 gate (250ms/tick) 유지 확인

---

## Fix 15 — Grep Guard 확장 (Medium)

### 현재 gap

[test_phase17_land.py:320-359](Projects/personas/loom/test_phase17_land.py#L320) `test_forbidden_grep_regression` 은 `persona.territory` 직접 쓰기만 가드. 다음 2종 누락:

1. `persona.region` 직접 쓰기 (region 은 territory 종속. helper 외 쓰면 split-state 재발 가능)
2. `hash(...)` 기반 RNG seed (Fix 11 의 회귀 방지)

### 처방 (test_phase17_land.py 수정)

`test_forbidden_grep_regression` 본문에 `regex_guards` 리스트 확장 (기존 3종 + 신규 2종):

```python
regex_guards = [
    # 기존 territory 쓰기 가드
    re.compile(r"persona\.territory\s*=(?!=)"),
    re.compile(r"\.territory\s*=(?!=)\s*(?!None|\"\"|persona_def)"),
    re.compile(r"self\.personas\[.*\]\.territory\s*=(?!=)"),
    # Fix 15 신규: region 직접 쓰기 금지
    re.compile(r"persona\.region\s*=(?!=)"),
    re.compile(r"self\.personas\[.*\]\.region\s*=(?!=)"),
    # Fix 15 신규: hash() 기반 RNG seed 금지
    re.compile(r"np\.random\.default_rng\s*\(\s*.*hash\("),
    re.compile(r"hash\(.*\)\s*[&%]\s*(0x|\d)"),
]
```

`allowed` 판정 확장 (helper 본체 + climate_engine.py 의 신규 `_stable_int` 파일 포함):

```python
allowed_helper_paths = {
    root / "core" / "multi_tick_engine.py",
    root / "physis" / "climate_engine.py",
}
...
allowed = (
    path in allowed_helper_paths
    and "# noqa: PHASE17_SSOT_WRITE" in line
)
```

**헬퍼 본체 마킹**: multi_tick_engine.py 의 `_change_persona_territory()` 내부 `persona.territory = ...` / `persona.region = ...` 라인 끝에 `# noqa: PHASE17_SSOT_WRITE` 주석 유지 (기존 v2 에서 도입됨). **신규**: `_derive_rng()` 는 hash() 를 쓰지 않으므로 마킹 불필요. `_stable_int` 도 hash() 를 쓰지 않음 (blake2b 사용).

### 검증

- `py test_phase17_land.py` → `test_forbidden_grep_regression` PASS
- 실측: 교체 후 전체 tree 에서 `hash(` 기반 RNG seed 0건 (`_stable_int` 자체는 blake2b 내부라 해당 regex 비매치)

---

## Fix 16 — v1 Addendum 하단 SUPERSEDED 마커 제거 (Trivial)

### 현재 상태

[PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum.md:1](Projects/personas/loom/PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum.md#L1) 상단 1줄 + [L569](Projects/personas/loom/PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum.md#L569) 하단 1줄. v2 정책은 **상단 1줄만**.

### 처방

파일 L569 한 줄 제거:

```
# Before (L568-569 마지막 두 줄)
이 addendum의 P0 3건 + P1 1건 전부 APPROVE 받으면 Phase 17 Φ-1 Land **closure**. Φ-2 Faction Charter 착수 가능.
[SUPERSEDED BY `PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum-v2.md`]

# After (L569 삭제)
이 addendum의 P0 3건 + P1 1건 전부 APPROVE 받으면 Phase 17 Φ-1 Land **closure**. Φ-2 Faction Charter 착수 가능.
```

### 검증

- `grep -c SUPERSEDED Projects/personas/loom/PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum.md` = 1 (상단 줄만)

---

## 변경 파일

| 파일 | 작업 | Fix | 유형 |
|---|---|:-:|:-:|
| [multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py) | `_stable_int` 모듈 helper + `_derive_rng()` method 추가, hash()-RNG 9곳 교체, `_phase_trace` 필드 + 3곳 append | 11, 13 | 수정 |
| [physis/climate_engine.py](Projects/personas/loom/physis/climate_engine.py) | `_stable_int` 추가, `self._seed` 필드, L169 seed 파생 교체 | 11 | 수정 |
| [test_phase17_land.py](Projects/personas/loom/test_phase17_land.py) | 신규 테스트 7건 (Fix 11 의 1 + Fix 12 의 5 + Fix 13 의 1), `test_forbidden_grep_regression` 가드 확장 | 11, 12, 13, 15 | 수정 |
| [test_phase17_acceptance.py](Projects/personas/loom/test_phase17_acceptance.py) | 테스트 리스트 2건 추가 | 14 | 수정 |
| [PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum.md](Projects/personas/loom/PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum.md) | L569 하단 마커 1줄 삭제 | 16 | 수정 |

**변경 없음 (금지)**:
- v1 addendum 본문 (L2~L568) — 하단 마커 1줄만 예외
- [PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum-v2.md](Projects/personas/loom/PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum-v2.md) — v2 Contract 섹션은 증명 대상, 변경 금지
- [PHASE-17-LAND-DECISIONS.md](Projects/personas/loom/PHASE-17-LAND-DECISIONS.md) — Fix 7 이미 완료, 재편집 금지
- `_change_persona_territory()` helper 본체 — Fix 12 는 helper 를 검증하지 helper 를 변경하지 않는다
- Issue 4 (WILD 98%) 관련 튜닝 — `DOMINANCE_VOTE_MARGIN`, `DOMINANCE_RADIUS_K`, Bridson r 모두 고정

---

## 검증

### 기계 검증 (항상)

1. `cd Projects/personas/loom && py test_phase17_land.py` → **23/23 PASS**
2. `cd Projects/personas/loom && py test_phase17_acceptance.py` → **exit 0**, 7 파일 전부 PASS
3. `cd Projects/personas/loom && py test_nomos.py` → PASS
4. `cd Projects/personas/loom && py test_class_promotion.py` → PASS
5. `cd Projects/personas/loom && py test_phase16_public_works.py` → **18/18 PASS**
6. `cd Projects/personas/loom && PYTHONIOENCODING=utf-8 py test_climate_impact.py` → PASS
7. `cd Projects/personas/loom && py test_phase14b_snn_integration.py` → PASS (기존 회귀 유지)
8. `cd Projects/personas/loom && py test_phase15_collective_action.py` → PASS (기존 회귀 유지)

### 계약 검증 (Φ-1 Closure 조건)

- [ ] `test_fix11_cross_process_determinism` PASS → seed=42 동일 설정 3 프로세스 digest 일치
- [ ] `test_contract_i1_territory_updated` PASS → I1 증명
- [ ] `test_contract_i2_region_synced` PASS → I2 증명
- [ ] `test_contract_i3_cache_invalidated` PASS → I3 증명
- [ ] `test_contract_i4_employment_released` PASS → I4 증명
- [ ] `test_contract_raises_on_unknown_territory` PASS → error boundary 증명
- [ ] `test_fix10_ordering_instrumentation` PASS → movement < action < economy 순서 증명
- [ ] `test_forbidden_grep_regression` PASS (region + hash()-RNG 가드 포함)

### 성능 검증

- [ ] `test_phase17_acceptance.py` 에서 100tick 평균 ≤ 250ms/tick (v2 기준값 161.2ms 에서 회귀 없음)

### 수동 재현

터미널 3개에서 각각:
```bash
cd Projects/personas/loom
PYTHONHASHSEED=random py -c "from core.multi_tick_engine import MultiTickEngine; import hashlib, json; e = MultiTickEngine(seed=42); [e.tick() for _ in range(80)]; snap = sorted([(p, tuple(pe.pos), pe.territory, pe.region) for p, pe in e.personas.items()]); print(hashlib.sha256(json.dumps(snap, default=str).encode()).hexdigest())"
```

**기대**: 3 프로세스 모두 **동일** digest. (v2 에서는 상이했음)

### grep 기반 재검증 (수동)

```bash
cd Projects/personas/loom
grep -rn "np.random.default_rng.*hash(" . --include="*.py"
# 기대: 0 matches (production), test 파일은 regex 가드 구현용이므로 예외
grep -rn "hash(.*) *[&%] *0x" . --include="*.py"
# 기대: test_phase17_land.py 의 가드 정의부만 (실행 코드 아님)
```

---

## Rollback

Fix 11 전체를 원복할 경우:
1. `_stable_int`, `_derive_rng` 제거
2. 각 라인의 `self._derive_rng(tag, *keys)` 를 원래 `np.random.default_rng(hash(...))` 호출로 복원
3. climate_engine.py 의 `self._seed`, `_stable_int` 제거, L169 원상 복구
4. test_phase17_land.py 의 Fix 11~13 신규 테스트 삭제

**영향**: 결정성 계약 다시 위반. Φ-1 Closure 차단 상태로 복귀.

Fix 13 ordering 훅만 비활성화하려면: `self._phase_trace = None` 유지 (default) → 운영 영향 0.

---

## 자체 검증 체크리스트

- [x] 메타(긴급도/선행/유형/migration/의존) 포함
- [x] 배경 (v2 리뷰 근본 원인) 명시
- [x] [필수/선택/금지] 태그
- [x] 변경 파일 표 + 변경 없음 명시
- [x] 기계 검증 8건 + 계약 검증 8건 + 성능 검증 1건 + 수동 재현 1건
- [x] Rollback 섹션
- [x] Fix 11~16 각각 "현재 gap → 처방 → 검증" 3단 구조
- [x] 모든 코드 교체 before/after 코드 블록 포함
- [x] 모호 표현 없음 ("적절히", "참고" 등 검사 완료)
- [x] 범위 경계 명시 ([금지]에 Issue 4 튜닝, v1 본문 편집 등 나열)
- [x] 혼합 작업 → Fix 단위로 분리 구조

---

## Φ-1 Closure 조건 (v2 → v2.1 업데이트)

v2 의 Closure 조건: "v2 addendum MUST 항목 전부 APPROVE"
v2.1 추가 조건: "Fix 11~13 (MUST) 전부 APPROVE + Fix 14~15 (SHOULD) APPROVE 권장 + Fix 16 (TRIVIAL)"

**Φ-1 Closure = v2.1 Fix 11~16 전부 반영 + acceptance gate exit 0 + cross-process determinism PASS**

이 조건 충족 시 Phase 17 Φ-1 Land **closure**. Φ-2 Faction Charter 착수 가능.

---

## GPT/Codex 전달 프롬프트 템플릿

```
당신은 loom 페르소나 시뮬레이션의 시니어 풀스택 개발자입니다.

## 프로젝트 경로
c:\Users\haj\projects\subagent-orchestrator

## 작업 지시서
Projects/personas/loom/PHASE-17-LAND-CODEX-INSTRUCTIONS-addendum-v2.1.md 파일을 그대로 따라 구현하세요.

## 규칙 (절대 준수)
1. [필수] Fix 11~13 100% 구현. [금지] 항목 절대 건드리지 말 것.
2. 지시서 코드 블록은 직접 복사·반영. "해석"하지 말 것.
3. _derive_rng() / _stable_int() 시그니처 임의 변경 금지.
4. 검증 순서:
   a. py test_phase17_land.py → 23/23 PASS
   b. py test_phase17_acceptance.py → exit 0
   c. 수동 cross-process determinism (PYTHONHASHSEED=random × 3회 동일 digest)
5. 실패 시 재작업, 전부 통과할 때까지 반복.
6. 보고 내용:
   - Fix 11~16 구현 여부 (각 Fix별)
   - 각 검증 단계 통과 여부
   - 성능 측정값 (ms/tick)
   - cross-process digest 일치 확인
```
