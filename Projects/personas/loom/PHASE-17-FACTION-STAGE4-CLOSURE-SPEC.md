# [기능] Phase 17 Φ-2 Faction Stage 4 — Closure & Φ-3 Handoff

> 긴급도: 중간 (Stage 3 구현 완료, 실측·인계 검증만 남음)
> 선행 조건: Stage 3 머지됨 (commit `501a7a4` 기준 — minority persistence + founder respawn)
> 작업 유형: 기능 (시뮬 백엔드: probe 재실행 + 신규 계약 테스트 + 문서) + 일부 설계(Charter §Stage4)
> DB migration: 없음
> 외부 의존: 없음 (numpy, dataclass)
> 사용자: Codex (gpt-5.5, reasoning_effort=xhigh)

---

## 목표·목적 3계층 (역산 기준)

**궁극 목적 (loom 전체)**
페르소나가 살아가는 과정에서 국가가 자연 탄생한다. Top-down "여기 국가 있음" 선언 금지. 삶 → 유대 → 갈등 → 주권 선언의 인과 사슬로만 국가 생성.

**Phase 17 목적**
자연 탄생의 4단계 인과 사슬 구축:
- Φ-1 Land: '어디에' 있는가 (CLOSED 2026-04-22)
- **Φ-2 Faction**: '누구와' 뜻이 같은가 (Stage 1~3 머지, **본 스펙에서 마감**)
- Φ-3 Struggle: 다른 '누구'와의 충돌·동맹
- Φ-4 Nation: 충분히 큰 결집의 주권 선언

**Φ-2 Stage 4 고유 역할**
"창발이 진짜로 일어났는지 측정한다." Stage 1~3은 *씨앗·이탈·복구*의 메커니즘을 심었다. Stage 4는 그 메커니즘이 **5000틱·3시드 환경에서 실제로 다수 Faction 공존을 만들어내는지**를 acceptance gate로 검증하고, **Φ-3가 받을 수 있는 read-only 인계 계약**을 동결한다. 새 메커니즘 추가가 아니라 **이미 만든 것의 진위(眞偽) 확인**이 본 스펙의 본질.

---

## 배경

Stage 1~3 진행 경로:
- **Stage 1** (`5217e39` 2026-04-22): SSoT-FIX + affiliation drift unlock (v5). `_change_persona_faction()` 단일 경로 강제, drift 가능성 확보.
- **Stage 2** (`f48cfd0` 2026-04-23): collapse mitigation v6 — size tax + homeostasis. 거대 Faction 흡수 압력 완화. **3/3 seed에서 active_factions_end=1 수렴 (acceptance FAIL)**.
- **Stage 3** (`501a7a4` 2026-04-24): anti-collapse B+C — minority persistence boost(소멸 직전 score 가산) + founder respawn(absorbing state 탈출). 단위 테스트 7/7 PASS, **5000틱 probe acceptance는 미측정**.

**현 상태 진단**:
- D1~D11 모두 구현 완료. D10 7종 API 전부 [multi_tick_engine.py:1568-1679](Projects/personas/loom/core/multi_tick_engine.py#L1568-L1679) 존재.
- Stage 3 hook도 모두 적용 (`MINORITY_PERSISTENCE_BOOST` line 1235, `_respawn_faction_tick` line 1284, `tick()` 호출 line 2154).
- 그러나 **Stage 3가 absorbing state를 정말로 탈출시키는지의 5000틱 실측이 없음**.
- D10 7종 API의 **read-only 보장(caller mutation이 internal state 오염하지 않음)** 계약 테스트가 없음. Charter [확정] #8(v2) "전 7종 read-only" 명시되어 있으나 검증 부재.
- Φ-3 Struggle 진입 트리거(언제 Φ-3 시작?)가 [보류] 상태. Charter `[확정] 5. Φ-2 진입 트리거: 보류`(Land Charter line 209)와 같은 패턴으로 **Φ-2 → Φ-3 진입 트리거** 미정의.

**해결 방향**:
Stage 4는 **메커니즘 추가 없는 검증·인계 마감 단계**.

1. Probe 재실행으로 Stage 3 acceptance 측정 (active≥2, drift, gini, faction_change).
2. D10 7종 API freeze 테스트 신설로 Φ-3 인계 계약 동결.
3. 결정성·성능·무파괴 회귀 종합 검증.
4. Closure Report에 측정값 기록.
5. Φ-3 진입 트리거 [확정] 사양화 → Charter Stage 4 섹션 추가.
6. acceptance PASS 시 Φ-2 CLOSED 선언, FAIL 시 Stage 5 후보 분석 (메커니즘 추가는 본 스펙 스코프 외).

---

## 작업 범위

### [필수]

1. **Stage 3 acceptance probe 재실행**:
   `python observe_phase17_emergence.py --seeds 7,13,42 --ticks 5000 --out data/phase17_probe/stage4`. 산출 JSON line 별 시드의 primary 4지표(`active_factions_end`, `drift_ratio`, `gini`, `faction_change_count`) 기록.

2. **신규 계약 테스트 추가**: `Projects/personas/loom/test_phase17_faction_handoff_contract.py`
   - D10 7종 API 각각의 반환 타입·shape 검증.
   - 반환 dict/list/tuple을 **caller가 mutate해도 internal state 영향 없음** 검증 (read-only freeze).
   - 7종 API를 100회 round-robin 호출 후 `(personas[pid].faction, faction_cooldown, factions registry, Territory.factionRef, _faction_members_cache)` 5채널 모두 호출 전 snapshot과 동일한지 검증.
   - `factions_in_contact(radius)` 음수/0 → ValueError 검증.
   - `faction_charter_primitives(unknown)` → KeyError 검증.

3. **결정성 회귀 테스트 보강**: `Projects/personas/loom/test_phase17_acceptance.py`에 `test_phase17_phi2_determinism_500_ticks` 추가 (이미 있으면 Stage 4 비교 채널 추가).
   - seed=42 × 500틱 × 2회 실행.
   - 비교 채널: `persona.faction`, `persona.faction_cooldown`, `inner.affiliation_scores`, `engine.factions` registry (id/name/founder_pid/charter/created_tick), `territory.factionRef`.
   - 두 실행의 5채널 직렬화 결과가 byte-level 일치.

4. **성능 회귀 측정**: 기존 `test_phase17_acceptance.py::test_phase17_phi2_perf_budget` 또는 신규 perf 테스트로 250ms/tick 미만 + faction kernel 단독 예산 ≤5ms 측정. faction kernel 예산은 `_compute_affiliation_tick + _commit_faction_tick + _project_faction_tick + _respawn_faction_tick` 4구간 합. 측정 방식은 `time.perf_counter` 기반 100틱 평균.

5. **Hard 불변 회귀 검증 (모두 PASS)**:
   - Phase 16 Hard 5지표: persona gold·public_works·food_stockpile·total_wealth·deaths.
   - Phase 17 Φ-1 23/23 PASS (`test_phase17_land.py`, `test_phase17_acceptance.py`).
   - Phase 17 Φ-2 핵심 4 (`test_phase17_faction.py`, `test_phase17_faction_drift.py`, `test_phase17_faction_mitigation.py`, `test_phase17_faction_stage3.py`).
   - 인접 4 (`test_phase17_faction_regression.py`, `test_phase17_faction_reincarnation_safety.py`, `test_nomos.py`, `test_phase14b_snn_integration.py`, `test_phase16_public_works.py`, `test_class_promotion.py` — 단 `test_class_promotion`은 사전 버그(line 102 KeyError, 환생자 pid 미정리)로 baseline 동일 재현됨. Stage 4 기준선에는 영향 없음. 별도 1줄 fix 커밋은 본 스펙 스코프 외).

6. **Closure Report 작성**: `Projects/personas/loom/PHASE-17-FACTION-STAGE4-CLOSURE-REPORT.md`
   - probe 산출 표(시드별 active/drift/gini/faction_change + secondary `min_faction_size_p50`, `respawn_event_count`, `last_500_ticks_active_ge_2_ratio`).
   - Acceptance 판정: `active_factions_end >= 2 (3/3 seed)` PASS/FAIL.
   - 결정성 byte-diff 결과 + 성능 ms/tick + faction kernel 예산.
   - source 분포 (`birth_founder` / `affiliation` / `drift`).
   - PASS 시: "**Φ-2 CLOSED 2026-XX-XX**" 선언.
   - FAIL 시: Stage 5 후보 분석 (D Territory 재결합, E Contact 보정, F Join/leave asymmetry, 기타) — 본 스펙 스코프 **외**, 사용자 결정 대기 표시.

7. **Φ-3 Struggle 진입 트리거 [확정] 사양화**: `Projects/personas/loom/PHASE-17-FACTION-CHARTER.md`에 `## Stage 4 — Φ-3 Handoff` 섹션 추가.
   진입 조건 3종(아래 §6 구체 사양 참조). 트리거는 **D10 7종 API의 read-only 호출만으로** 계산 가능해야 함. Φ-2 내부 state 의존 금지.

8. **Φ-3 Charter 스텁 파일**: `Projects/personas/loom/PHASE-17-STRUGGLE-CHARTER-STUB.md`
   2~3 페이지의 스텁만. Primary Outcome / Operating Loop / Φ-2 인계 입력(7종 API + 진입 트리거 결과) / [미결] 항목 카탈로그. 본격 Charter는 Φ-3 진입 시 `/design`으로 별도 작성. 본 스텁은 "**Φ-2가 무엇을 넘기는가**"의 인계 계약 측면만 명시.

### [선택]

- secondary 지표 시각화 (probe JSON → matplotlib plot). 필수 아님.
- faction_change source 분포 시계열 분석.
- `_faction_members_cache` invalidation 회귀 테스트 (이미 일부 커버). 보강 가능.

### [금지]

- **brain/** 디렉토리 수정** — Phase 14-B 계약 불변. SNN telemetry hook도 Stage 4에서는 무수정.
- **Stage 1/2/3 상수 값 변경** — `W_TERRITORY_*`, `W_TRUST/GRIEVANCE/PROXIMITY`, `DECAY`, `DRIFT_MARGIN_*`, `FACTION_SIZE_TAX_*`, `HOMEOSTASIS_*`, `MINORITY_PERSISTENCE_*`, `FOUNDER_RESPAWN_*` 모두 동결.
- **새 Faction 동역학 메커니즘 추가** — Stage 4는 측정·계약 동결만. D/E/F 후보(territory 재결합·contact 보정·join/leave asymmetry) 본 스펙에 **포함 금지**. acceptance FAIL 시 Stage 5 별도 spec.
- **D10 7종 API 시그니처 변경** — Charter [확정] #8(v2)와 현 구현([core/multi_tick_engine.py:1568-1679](Projects/personas/loom/core/multi_tick_engine.py#L1568-L1679)) 일치 유지. 인자·반환 타입 변경 금지.
- **D10 7종 외부에 새 read API 추가** — Φ-3가 필요하면 Φ-3 Charter에서 추가, Φ-2 마감에서는 동결.
- **SSoT 우회** — `persona.faction = X` 직접 대입 금지 (AST whitelist로 강제됨).
- **FactionChangeSource 추가** — `"birth_founder" | "affiliation" | "drift" | "conflict"` 4종 고정.
- **`np.random.default_rng(...)` 직접 호출** — 결정성 테스트에서도 `_derive_rng` 경유.
- **`charter primitive 3-5` 범위 수정** — `CHARTER_PRIMITIVE_COUNT = (3, 5)` 동결.
- **Φ-3 본 Charter·Decisions·Codex Instructions 작성** — 본 스펙은 *스텁*만. Φ-3 본격 설계는 Φ-2 CLOSED 후 별도 `/design` 사이클.
- **범위 밖 리팩토링** — 본 지시서 명시 파일 외 수정 금지. 특히 `dashboard/`, `scripts/`, `physis/`, `brain/` 무수정.

---

## 불변 원칙 (모든 구현이 준수)

1. **Top-down 금지** — Stage 4는 측정·계약 동결. founder+charter only 원칙 무손상.
2. **Phase 11-17 무파괴** — Φ-1 23/23, Phase 16 Hard 5지표, 핵심 테스트 ALL PASS.
3. **SNN `n_neurons=1000` freeze** — `readout_weights_v1.npy` 호환. 본 스텝에서 SNN 무수정.
4. **단방향 SSoT** — `persona.faction` 주, `Territory.factionRef` 파생.
5. **단일 쓰기 경로** — `_change_persona_faction()` / `_tick_faction_cooldown()` 외 모든 경로 차단 (AST whitelist).
6. **결정성 계약** — `_derive_rng("faction_*", key_parts)`, `sorted(pid)` tie-break, double-buffer snapshot→compute→commit.
7. **read-only 인계** — Φ-3가 받는 7종 API는 호출 후 internal state 무변경. 반환 객체는 신규 생성된 dict/list/tuple.

---

## 프레임워크 제약

### Python 3.14
- `@dataclass(slots=True)` + `field(default_factory=...)` 조합 시 ValueError. Φ-1 D1 실측 근거. 본 스펙은 신규 dataclass 추가 없음, 기존 정의 유지.

### numpy RNG
- `numpy.random.Generator.bytes(n)` 지원됨. 결정성 테스트의 snapshot 직렬화는 `json.dumps(..., sort_keys=True, default=str)` 또는 `pickle.dumps(...)` 둘 중 하나로 통일. **선택**: `pickle.dumps(snapshot, protocol=4)` 후 `hashlib.sha256().hexdigest()` 비교 — 두 회 실행의 hash 일치.

### pytest collection
- pytest는 module top-level 코드를 collection 시점에 실행. 신규 테스트 파일에서 `engine = MultiTickEngine(...)` 같은 module-level 인스턴스화 금지. 모든 인스턴스화는 `def test_*` 또는 fixture 내부.

### 속성 접근
- `MultiTickEngine`의 dict는 public — `engine.personas`, `engine.territories`, `engine.factions`, `engine.inners`, `engine.wallets`. private(`_personas` 등) 접근 금지.
- tick 카운터: `engine.time.tick`.

---

## 참조 코드 위치 (기존 구현 접지)

| 역할 | 파일:라인 | 용도 |
|------|-----------|------|
| `MultiTickEngine.tick()` | [core/multi_tick_engine.py:2154](Projects/personas/loom/core/multi_tick_engine.py#L2154) | `_respawn_faction_tick()` 호출 (Stage 3 C) |
| `_compute_affiliation_tick` | [core/multi_tick_engine.py:1235](Projects/personas/loom/core/multi_tick_engine.py#L1235) | Stage 3 B `MINORITY_PERSISTENCE_BOOST` 적용 위치 |
| `_respawn_faction_tick` | [core/multi_tick_engine.py:1284](Projects/personas/loom/core/multi_tick_engine.py#L1284) | Stage 3 C, FOUNDER_RESPAWN 주기 발동 |
| D10 7종 API | [core/multi_tick_engine.py:1568-1679](Projects/personas/loom/core/multi_tick_engine.py#L1568-L1679) | freeze 테스트 대상. 시그니처 동결. |
| `_derive_rng()` | [core/multi_tick_engine.py:1681](Projects/personas/loom/core/multi_tick_engine.py#L1681) | 결정성 RNG 단일 경로 |
| Stage 3 상수 | [ontology/layers.py:215-235](Projects/personas/loom/ontology/layers.py#L215-L235) | 동결 대상 |
| Stage 3 단위 테스트 | [test_phase17_faction_stage3.py](Projects/personas/loom/test_phase17_faction_stage3.py) | 7/7 PASS 확인 |
| Probe 스크립트 | [observe_phase17_emergence.py](Projects/personas/loom/observe_phase17_emergence.py) | `--seeds 7,13,42 --ticks 5000` |
| Φ-2 Charter v2 | [PHASE-17-FACTION-CHARTER.md](Projects/personas/loom/PHASE-17-FACTION-CHARTER.md) | Stage 4 섹션 추가 위치 |
| Φ-1 Charter (참고) | [PHASE-17-LAND-CHARTER.md](Projects/personas/loom/PHASE-17-LAND-CHARTER.md) | CLOSED 선언 패턴 (line 38, "Φ-1 Land — CLOSED") |

---

## 구현 순서 (DAG)

```
Phase A (측정)        — Step 1 probe 재실행
                          ↓ JSON 산출
Phase B (계약 동결)   — Step 2 freeze 테스트 (probe 결과 무관, 독립 가능)
Phase C (회귀)        — Step 3 결정성, Step 4 성능, Step 5 Hard 불변
Phase D (보고)        — Step 6 Closure Report (Phase A·B·C 산출 종합)
Phase E (인계)        — Step 7 Charter Stage 4 추가, Step 8 Φ-3 Charter 스텁
Phase F (gate 결정)   — Closure Report PASS 판정 시 Φ-2 CLOSED 선언, FAIL 시 Stage 5 escalation
```

의존:
- Phase B는 Phase A에 독립. 병렬 가능.
- Phase D는 Phase A+B+C 모두 종료 후.
- Phase E는 Phase D 결과(PASS/FAIL)에 따라 Stage 4 섹션 내용 분기.

---

## Step 1 — Stage 3 acceptance probe 재실행

### 실행

```bash
cd Projects/personas/loom
python observe_phase17_emergence.py --seeds 7,13,42 --ticks 5000 --out data/phase17_probe/stage4
```

### 산출 (예상)

`data/phase17_probe/stage4/probe_seed_7.json`, `..._13.json`, `..._42.json` (probe 스크립트가 어떻게 구성되어 있는지에 따름. **probe 산출 형식은 변경 금지** — 스크립트 수정도 본 스펙 스코프 외).

### Acceptance (primary, 4지표 모두 충족)

각 시드 단독으로:
- `active_factions_end >= 2`
- `drift_ratio` 가 Stage 2 v6 baseline (42-55%) 범위 또는 그 이내
- `gini >= 0.0` (분포 불균등성, 단 0이면 완전 균등 = collapse 직전과 구분 필요 — secondary 지표로 보완)
- `faction_change_count > 0` (이동 발생)

3시드 중 **3/3 모두 primary 통과해야 Φ-2 CLOSED 후보**.

### Acceptance (secondary, 진단용)

- `min_faction_size_p50` (500틱 단위 윈도우, 최소 faction size의 중앙값) — Stage 3 B 동작 확인.
- `respawn_event_count` (Stage 3 C 발동 횟수) — 0이면 C는 작동 안 했고 B만으로 통과; >0이면 C 효과 입증.
- `last_500_ticks_active_ge_2_ratio` (마지막 500틱 중 active≥2 인 틱 비율) — 후반 안정성.

secondary는 PASS 게이트 아님. Closure Report에 **기록만**. 단 모든 시드에서 `min_faction_size_p50 == 0` 이면 "잠시 0이지만 respawn으로 복구 중인 transient" 가능성 분석.

### 실패 시 분기

3/3 PASS → Phase D 진행.
1/3 또는 2/3 PASS → Closure Report에 부분 PASS 기록. **Φ-2 CLOSED 선언 보류**, Stage 5 escalation 사용자 결정 대기.
0/3 PASS → Stage 3가 absorbing state를 탈출시키지 못함을 확정. Stage 5 spec 작성 권고 (별도).

---

## Step 2 — D10 7종 API freeze 계약 테스트

### 신규 파일

`Projects/personas/loom/test_phase17_faction_handoff_contract.py`

### 테스트 클래스 골격

```python
"""Phase 17 Φ-2 Stage 4 — D10 read-only handoff contract tests.

Φ-3 Struggle이 Φ-2의 출력으로 7종 API만을 사용하기 위한
read-only freeze 계약을 검증한다.
"""
from __future__ import annotations

import copy
import pickle
import hashlib
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.multi_tick_engine import MultiTickEngine


def _engine_after(ticks: int = 200, seed: int = 42) -> MultiTickEngine:
    eng = MultiTickEngine(seed=seed)
    for _ in range(ticks):
        eng.tick()
    return eng


def _internal_state_hash(eng: MultiTickEngine) -> str:
    """Stable hash of all faction-related internal state."""
    snap = {
        "personas_faction": {
            pid: (eng.personas[pid].faction, eng.personas[pid].faction_cooldown)
            for pid in sorted(eng.personas)
        },
        "factions": {
            fid: (
                eng.factions[fid].id,
                eng.factions[fid].name,
                eng.factions[fid].founder_pid,
                tuple(eng.factions[fid].charter),
                eng.factions[fid].created_tick,
            )
            for fid in sorted(eng.factions)
        },
        "territory_ref": {
            tid: eng.territories[tid].factionRef for tid in sorted(eng.territories)
        },
        "affiliation_scores": {
            pid: dict(eng.inners[pid].affiliation_scores)
            for pid in sorted(eng.inners)
        },
    }
    return hashlib.sha256(pickle.dumps(snap, protocol=4)).hexdigest()


# ─── Shape & type tests ───────────────────────────────────────────

def test_population_distribution_returns_int_dict():
    eng = _engine_after()
    dist = eng.faction_population_distribution()
    assert isinstance(dist, dict)
    for fid, count in dist.items():
        assert isinstance(fid, str)
        assert isinstance(count, int)
        assert count >= 0


def test_territory_distribution_returns_str_lists():
    eng = _engine_after()
    dist = eng.faction_territory_distribution()
    for fid, tids in dist.items():
        assert isinstance(tids, list)
        assert all(isinstance(t, str) for t in tids)


def test_charter_primitives_returns_tuple():
    eng = _engine_after()
    fid = next(iter(eng.factions))
    charter = eng.faction_charter_primitives(fid)
    assert isinstance(charter, tuple)
    assert 3 <= len(charter) <= 5


def test_charter_primitives_unknown_id_raises_keyerror():
    eng = _engine_after()
    with pytest.raises(KeyError):
        eng.faction_charter_primitives("FACTION_DOES_NOT_EXIST")


def test_factions_in_contact_radius_validation():
    eng = _engine_after()
    eng.factions_in_contact(radius=1)  # ok
    with pytest.raises(ValueError):
        eng.factions_in_contact(radius=0)
    with pytest.raises(ValueError):
        eng.factions_in_contact(radius=-1)


def test_wealth_distribution_shape():
    eng = _engine_after()
    wealth = eng.faction_wealth_distribution()
    for fid, stats in wealth.items():
        assert set(stats.keys()) == {"total", "mean", "gini", "top_decile_share"}
        assert all(isinstance(v, float) for v in stats.values())


def test_social_matrix_sorted_pairs():
    eng = _engine_after()
    matrix = eng.faction_social_matrix()
    for (a, b), trust in matrix.items():
        assert a < b
        assert isinstance(trust, float)


def test_grievance_targets_shape():
    eng = _engine_after()
    griev = eng.faction_grievance_targets()
    for fid, lord_counts in griev.items():
        for lord_id, count in lord_counts.items():
            assert isinstance(lord_id, str)
            assert isinstance(count, int)
            assert count > 0


# ─── Read-only freeze tests ────────────────────────────────────────

def test_caller_mutation_does_not_affect_internal_state():
    """7종 API 반환 객체를 caller가 mutate해도 internal state는 불변."""
    eng = _engine_after()
    before = _internal_state_hash(eng)

    pop = eng.faction_population_distribution()
    pop["INJECTED_KEY"] = 999
    pop_existing = next(iter(pop)) if pop else None
    if pop_existing:
        pop[pop_existing] = -1

    terr = eng.faction_territory_distribution()
    for tids in terr.values():
        tids.append("INJECTED_TERRITORY")

    fid = next(iter(eng.factions), None)
    if fid:
        # tuple은 immutable이므로 identity만 검증
        charter = eng.faction_charter_primitives(fid)
        assert charter is eng.factions[fid].charter or charter == eng.factions[fid].charter

    pairs = eng.factions_in_contact()
    pairs.append(("INJECTED_A", "INJECTED_B"))

    wealth = eng.faction_wealth_distribution()
    for stats in wealth.values():
        stats["total"] = -1.0

    matrix = eng.faction_social_matrix()
    for k in list(matrix):
        matrix[k] = -1.0

    griev = eng.faction_grievance_targets()
    for lord_counts in griev.values():
        lord_counts["INJECTED_LORD"] = 999

    after = _internal_state_hash(eng)
    assert before == after, "D10 caller mutation leaked into internal state"


def test_round_robin_calls_do_not_advance_state():
    """7종 API 100회 round-robin 호출 후에도 internal state hash 동일."""
    eng = _engine_after()
    before = _internal_state_hash(eng)
    fids = list(eng.factions)
    for _ in range(100):
        eng.faction_population_distribution()
        eng.faction_territory_distribution()
        if fids:
            eng.faction_charter_primitives(fids[0])
        eng.factions_in_contact(radius=2)
        eng.faction_wealth_distribution()
        eng.faction_social_matrix()
        eng.faction_grievance_targets()
    after = _internal_state_hash(eng)
    assert before == after


# ─── Composability ─────────────────────────────────────────────────

def test_population_keys_match_factions_registry():
    eng = _engine_after()
    pop = eng.faction_population_distribution()
    assert set(pop.keys()) == set(eng.factions.keys())


def test_territory_keys_match_factions_registry():
    eng = _engine_after()
    terr = eng.faction_territory_distribution()
    assert set(terr.keys()) == set(eng.factions.keys())
```

### 검증

```bash
cd Projects/personas/loom && pytest test_phase17_faction_handoff_contract.py -v
```

전 테스트 PASS.

### 만일 freeze 테스트 FAIL 시

D10 7종 API의 일부가 internal 객체를 직접 반환하고 있다는 뜻. 해결 방법:
- `dict(...)` / `list(...)` / `copy.copy(...)` 로 신규 객체 반환하도록 수정.
- tuple은 immutable이므로 그대로 OK.
- 단 **시그니처(인자·반환 타입)는 변경 금지**.

---

## Step 3 — 결정성 회귀

### 기존 테스트 보강

`Projects/personas/loom/test_phase17_acceptance.py`에 다음 추가 (이미 유사 테스트가 있다면 비교 채널을 5채널로 확장):

```python
def test_phase17_phi2_determinism_500_ticks_stage4():
    """Stage 4: 5채널 byte-level 일치."""
    import pickle, hashlib
    from core.multi_tick_engine import MultiTickEngine

    def snap(eng: MultiTickEngine) -> bytes:
        s = {
            "p_faction": {pid: eng.personas[pid].faction for pid in sorted(eng.personas)},
            "p_cooldown": {pid: eng.personas[pid].faction_cooldown for pid in sorted(eng.personas)},
            "i_aff": {pid: dict(eng.inners[pid].affiliation_scores) for pid in sorted(eng.inners)},
            "factions": {
                fid: (
                    eng.factions[fid].name,
                    eng.factions[fid].founder_pid,
                    tuple(eng.factions[fid].charter),
                    eng.factions[fid].created_tick,
                )
                for fid in sorted(eng.factions)
            },
            "t_ref": {tid: eng.territories[tid].factionRef for tid in sorted(eng.territories)},
        }
        return pickle.dumps(s, protocol=4)

    def run():
        e = MultiTickEngine(seed=42)
        for _ in range(500):
            e.tick()
        return hashlib.sha256(snap(e)).hexdigest()

    h1, h2 = run(), run()
    assert h1 == h2, f"Φ-2 Stage 4 determinism: 5채널 hash 불일치 ({h1} != {h2})"
```

### 검증

```bash
cd Projects/personas/loom && pytest test_phase17_acceptance.py::test_phase17_phi2_determinism_500_ticks_stage4 -v
```

PASS 필수.

---

## Step 4 — 성능 회귀

### 측정 방식

기존 `test_phase17_acceptance.py::test_phase17_phi2_perf_budget`(있으면 그대로) 또는 신규:

```python
def test_phase17_phi2_perf_stage4():
    import time
    from core.multi_tick_engine import MultiTickEngine

    e = MultiTickEngine(seed=42)
    for _ in range(50):  # warmup
        e.tick()

    t0 = time.perf_counter()
    for _ in range(100):
        e.tick()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0 / 100.0
    assert elapsed_ms <= 250.0, f"tick budget exceeded: {elapsed_ms:.1f}ms"
```

### Faction kernel 단독 예산 (선택)

`time.perf_counter()` 기반 4 구간 (`_compute_affiliation_tick`, `_commit_faction_tick`, `_project_faction_tick`, `_respawn_faction_tick`) 호출 직전·직후 측정. 합계 ≤5ms/tick. 측정 자체는 perf 테스트에 통합 또는 별도 micro benchmark 스크립트 (`benchmark_phase17_faction.py`).

### 결과 기록

Closure Report에 ms/tick + faction kernel ms/tick 기록.

---

## Step 5 — Hard 불변 회귀

### 실행 명령

```bash
cd Projects/personas/loom && pytest \
  test_phase17_land.py \
  test_phase17_acceptance.py \
  test_phase17_faction.py \
  test_phase17_faction_drift.py \
  test_phase17_faction_mitigation.py \
  test_phase17_faction_stage3.py \
  test_phase17_faction_regression.py \
  test_phase17_faction_reincarnation_safety.py \
  test_phase17_faction_handoff_contract.py \
  test_nomos.py \
  test_phase14b_snn_integration.py \
  test_phase16_public_works.py \
  -v
```

### 결과 (필수)

`test_phase17_land.py` 23/23 + `test_phase17_acceptance.py` 모두 PASS + Φ-2 핵심 4 + 인접 4 + 신규 freeze 테스트 ALL PASS.

`test_class_promotion.py`는 사전 버그(line 102 KeyError, 환생자 pid 미정리)로 baseline 동일 재현. 본 스펙 직접 스코프 외이므로 **failure 무시 + Closure Report에 명시**. 수정은 별도 1줄 fix 커밋(스펙 스코프 외).

### Phase 16 Hard 5지표

기존 acceptance 테스트가 5지표를 자동으로 커버. 명시적 측정이 필요하면 `test_phase17_acceptance.py`의 관련 case 또는 `test_phase16_public_works.py` 재실행.

---

## Step 6 — Closure Report 작성

### 신규 파일

`Projects/personas/loom/PHASE-17-FACTION-STAGE4-CLOSURE-REPORT.md`

### 형식

```markdown
# Phase 17 Φ-2 Faction Stage 4 — Closure Report

> 측정일: 2026-XX-XX
> 코드 기준: commit 501a7a4 (Stage 3 머지) + Stage 4 신규 테스트 추가
> 사용자 결정 대기 항목: (있으면 명시)

---

## 1. Acceptance Summary

| 시드 | active_factions_end | drift_ratio | gini | faction_change_count | min_faction_size_p50 | respawn_event_count | last_500_ticks_active_ge_2_ratio | Verdict |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 7  | …  | … | … | … | … | … | … | PASS/FAIL |
| 13 | …  | … | … | … | … | … | … | PASS/FAIL |
| 42 | …  | … | … | … | … | … | … | PASS/FAIL |

**Primary acceptance**: `active_factions_end >= 2 (3/3 seed)` → **PASS / FAIL**

## 2. 결정성

- 5채널 byte-level hash (seed=42, 500틱 × 2회): `<sha256>` == `<sha256>` → **PASS**

## 3. 성능

- 평균 ms/tick: ____ (예산 ≤250)
- Faction kernel 합 ms/tick: ____ (예산 ≤5)

## 4. Hard 불변

- Φ-1 23/23: PASS
- Φ-2 핵심 4: PASS (`faction`, `drift`, `mitigation`, `stage3`)
- 인접 4: PASS
- Phase 16 Hard 5지표: PASS
- `test_class_promotion.py`: 사전 버그(line 102 환생자 pid 미정리)로 baseline 동일 FAIL. **본 Stage 회귀 아님**.

## 5. faction_change source 분포 (5000틱 평균)

| source | 시드 7 | 시드 13 | 시드 42 |
|---|---:|---:|---:|
| birth_founder | … | … | … |
| affiliation | … | … | … |
| drift | … | … | … |
| conflict (Φ-3 예약) | 0 | 0 | 0 |

## 6. Verdict

- [PASS] **Φ-2 CLOSED 2026-XX-XX**. Φ-3 Struggle 진입 가능.
- [FAIL] Stage 5 escalation 후보 분석 (사용자 결정 대기):
  - D Territory 재결합
  - E Contact 보정
  - F Join/leave asymmetry
  - 기타: …
```

PASS 시 verdict 블록의 PASS 줄만 유지, FAIL 시 FAIL 줄만 유지.

---

## Step 7 — Charter Stage 4 섹션 추가

### 위치

`Projects/personas/loom/PHASE-17-FACTION-CHARTER.md` 의 `## 다음 단계` 직전에 신규 섹션 삽입.

### 내용

```markdown
---

## Stage 4 — Φ-3 Handoff (2026-XX-XX)

### Φ-3 진입 트리거 [확정]

D10 7종 API의 read-only 호출만으로 계산. 3 조건 **OR** (전부 만족 아님 — 어느 하나라도 트리거):

1. **지리적 분화**: `factions_in_contact(radius=1)` 결과의 길이 ≥ 1.
   *해석*: 인접 영지에 서로 다른 dominant faction 존재. 충돌 가능성.

2. **인구 비대칭**: `faction_population_distribution()` 의 최대값 ÷ 합 ≥ 0.55.
   *해석*: 한 faction이 인구 55% 이상 점유. 다른 faction에 압박. (Stage 2 size tax 임계 동일 정합)

3. **공유 분노**: `faction_grievance_targets()` 에서 동일 lord_id를 ≥2 faction의 멤버 ≥3 명이 grievance target으로 공유.
   *해석*: 공동의 적이 존재. Φ-3 동맹 씨앗.

세 조건 모두 미충족이면 Φ-3 진입 보류 (Φ-2 안정 상태로 운영 지속).

### Φ-3가 받는 입력 (read-only 7종)

| API | 용도 (Φ-3 관점) |
|---|---|
| `faction_population_distribution` | 진영 규모 비교, 동맹·약자 식별 |
| `faction_territory_distribution` | 지리적 영향권, 이동 경로 |
| `faction_charter_primitives` | 이념 충돌 진단 (charter overlap·conflict) |
| `factions_in_contact` | 1차 충돌 후보 쌍 |
| `faction_wealth_distribution` | 경제 약탈 동기, 계급 갈등 |
| `faction_social_matrix` | 신뢰 기반 동맹·대립 그래프 |
| `faction_grievance_targets` | 공동 적 기반 결집 |

전 API는 호출 후 internal state 무변경(test_phase17_faction_handoff_contract.py로 보장).

### Φ-2 → Φ-3 인계 시점

Closure Report 가 **Verdict=PASS** 인 시점부터 Φ-3 진입 트리거 측정 가능. 트리거 1개 이상 만족 시 별도 `/design` 사이클로 Φ-3 본 Charter 작성 (스텁: `PHASE-17-STRUGGLE-CHARTER-STUB.md`).
```

---

## Step 8 — Φ-3 Charter 스텁

### 신규 파일

`Projects/personas/loom/PHASE-17-STRUGGLE-CHARTER-STUB.md`

### 내용 (2-3 페이지 분량)

```markdown
# Phase 17 / Φ-3 Struggle — Charter STUB

> 본 파일은 *스텁* 입니다. Φ-2 CLOSED 후 별도 `/design` Phase 0~5 사이클로 본 Charter 작성.
> 본 스텁은 Φ-2 Stage 4 인계 계약 측면만 명시.

## 메타

| 항목 | 값 |
|---|---|
| 프로젝트 | loom 페르소나 국가 시뮬 |
| Phase | 17 (Φ-3 Struggle) |
| 로드맵 위치 | Φ-1 Land → Φ-2 Faction → **Φ-3 Struggle** → Φ-4 Nation |
| 선행 | Φ-2 CLOSED (Stage 4 Closure Report PASS 후) |
| 상태 | STUB (본격 Charter 별도 작성 대기) |

## 3계층

- 궁극: 국가 자연 탄생.
- Phase 17: 4단계 인과 사슬.
- Φ-3 고유 역할: "다른 우리"와의 충돌·동맹. Φ-2가 만든 Faction 분포가 갈등 동역학으로 변환되는 단계.

## Primary Outcome (잠정)

Faction 간 **선언 없는 충돌·동맹 동역학**이 자연 발생. 외부 작가가 "이 두 진영이 적이다"라고 정하지 않고, charter 충돌·자원 경합·grievance 공유로 적대/우호가 떠오른다.

## Operating Loop (잠정)

- 마이크로 (틱): Faction 간 contact 발생 시 charter 충돌 점수 + 자원 경합 + 신뢰 변화.
- 미들 (수십 틱): 동맹 결성 / 적대 확정 / 영토 압박.
- 매크로 (수백~수천 틱): 충분히 큰 Faction 결집 → Φ-4 Nation 진입.

## Φ-2 인계 입력 (read-only 7종)

[Stage 4 Charter §"Φ-3가 받는 입력"](PHASE-17-FACTION-CHARTER.md#stage-4--φ-3-handoff) 참조.

추가 인계 없음. Φ-3는 Φ-2 internal state에 직접 접근 금지 — 7종 API만 사용.

## Baseline 포함 / 제외 (잠정)

**포함 후보** (Φ-3 본 Charter에서 확정):
- Faction 간 적대도 (hostility) 누적
- 동맹 결성 메커니즘 (charter overlap + 공동 적)
- 자원 경합 (territory 점유 변화)
- 충돌 이벤트 트리거 (contact pair 중 hostility 임계 초과)

**제외 (Φ-3 비범위)**:
- 실제 전투 시뮬 (Φ-3 말기 또는 Φ-4)
- 국가 형성 자체 (Φ-4)
- 외교 의례·언어 분화 (Φ-4)

## [미결] 항목 카탈로그

- 적대도 수식 (charter primitive 충돌 + grievance 공유 + wealth gap?)
- 동맹 결성 임계
- 충돌 이벤트의 결과 (territory 이동? charter 변형? 인구 손실?)
- Faction 소멸 규칙 (Φ-2 말기 백로그와 통합)
- SNN 통합 (300~349 재사용? 또는 hostility 채널 신설?)

## 다음 단계

1. Φ-2 CLOSED 확정 (Stage 4 Closure Report Verdict=PASS).
2. Φ-3 본격 `/design` 사이클 (Phase 0 Intake → Phase 5 Package).
3. `/discuss` 다중 엔진 토론으로 [미결] 카탈로그 확정.
4. `/spec` 으로 Codex 전달용 PHASE-17-STRUGGLE-CODEX-INSTRUCTIONS.md 작성.
```

---

## 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/test_phase17_faction_handoff_contract.py` | 신규 작성 | 추가 |
| `Projects/personas/loom/test_phase17_acceptance.py` | `test_phase17_phi2_determinism_500_ticks_stage4` 추가, perf 테스트 보강 (있으면) | 수정 |
| `Projects/personas/loom/PHASE-17-FACTION-CHARTER.md` | `## Stage 4 — Φ-3 Handoff` 섹션 추가 (다음 단계 직전) | 수정 |
| `Projects/personas/loom/PHASE-17-FACTION-STAGE4-CLOSURE-REPORT.md` | 신규 작성 (probe 결과 + verdict) | 추가 |
| `Projects/personas/loom/PHASE-17-STRUGGLE-CHARTER-STUB.md` | 신규 작성 | 추가 |
| `Projects/personas/loom/data/phase17_probe/stage4/probe_seed_*.json` | probe 산출 (자동 생성) | 추가 |

**변경 없음 (금지)**:
- `Projects/personas/loom/core/multi_tick_engine.py` — 본 스펙 검증 단계, 코드 무수정 원칙. **단 freeze 테스트 FAIL 시에만** D10 7종 중 해당 메서드를 신규 dict/list 반환으로 수정 허용 (시그니처 변경 금지).
- `Projects/personas/loom/ontology/layers.py` — Stage 1/2/3 상수 동결, 본 스펙 무수정.
- `Projects/personas/loom/brain/**` — Phase 14-B 계약 불변.
- `Projects/personas/loom/observe_phase17_emergence.py` — probe 산출 형식 동결.
- `dashboard/`, `scripts/`, `physis/` — 무관.

---

## 검증

### 기계 검증 (항상)

```bash
cd Projects/personas/loom

# 1. 새 테스트 파일 통과
pytest test_phase17_faction_handoff_contract.py -v

# 2. 결정성·성능 테스트 통과
pytest test_phase17_acceptance.py -v

# 3. 핵심 회귀 통과
pytest \
  test_phase17_land.py test_phase17_faction.py test_phase17_faction_drift.py \
  test_phase17_faction_mitigation.py test_phase17_faction_stage3.py \
  test_phase17_faction_regression.py test_phase17_faction_reincarnation_safety.py \
  test_nomos.py test_phase14b_snn_integration.py test_phase16_public_works.py \
  -v

# 4. ruff (있으면)
ruff check core/multi_tick_engine.py ontology/layers.py test_phase17_faction_handoff_contract.py

# 5. mypy (있으면)
mypy core/multi_tick_engine.py
```

### 기능 검증 (Φ-2 마감 핵심)

- [ ] `python observe_phase17_emergence.py --seeds 7,13,42 --ticks 5000 --out data/phase17_probe/stage4` 정상 종료
- [ ] 3시드 모두 `active_factions_end >= 2` (PASS) 또는 부분 PASS 시 Closure Report에 정확히 기록
- [ ] D10 7종 freeze 테스트 PASS (caller mutation 비격리 발견 시 해당 메서드 수정 + 재실행)
- [ ] 결정성 5채널 byte-level 일치
- [ ] 성능 ms/tick ≤250, faction kernel ≤5

### 계약 검증 (Φ-3 인계)

- [ ] Charter `## Stage 4 — Φ-3 Handoff` 섹션 추가 완료
- [ ] 진입 트리거 3 조건 명시 (factions_in_contact, population 비대칭 0.55, grievance 공유)
- [ ] Φ-3 Charter 스텁 작성 (Primary Outcome 잠정 + [미결] 카탈로그 ≥5 항목)
- [ ] Closure Report Verdict=PASS 시 "Φ-2 CLOSED YYYY-MM-DD" 표기
- [ ] Closure Report Verdict=FAIL 시 Stage 5 후보 분석 + 사용자 결정 대기 명시

### 시각 QA

해당 없음 (백엔드 검증 스펙).

---

## Rollback

본 스펙은 **검증·문서 추가 only**. 코드 변경은 freeze 테스트 FAIL 시 D10 메서드 일부 보정에 한정.

롤백 시나리오:
1. **freeze 테스트 보정 롤백**: 해당 메서드(예: `faction_population_distribution`)를 이전 구현으로 되돌리고 freeze 테스트를 `xfail` 마크.
   - 데이터 손실: 없음.
   - 영향: D10 read-only 계약 미달성. Φ-3 인계 보류.
2. **신규 파일 롤백**: `git rm` 으로 4개 신규 파일(.md 3 + .py 1) 제거.
3. **Charter §Stage 4 롤백**: Charter 섹션 제거 (이전 ## 다음 단계 직전 상태로 복원).
4. **probe JSON 롤백**: `data/phase17_probe/stage4/` 디렉토리 삭제.

전 롤백 시나리오에서 commit 501a7a4 (Stage 3 머지) 이전 상태로 영향 없음.

---

## Codex 전달용 프롬프트 템플릿

```
당신은 loom 페르소나 시뮬의 시니어 백엔드 엔지니어입니다.

## 프로젝트 경로
c:\Users\haj\projects\subagent-orchestrator\Projects\personas\loom

## 기술 스택
Python 3.14, numpy, dataclass, pytest. 단일 프로세스 시뮬, brain/(SNN)/core/(엔진)/ontology/(계약 dataclass)/physis/(World 격자) 디렉토리.

## 작업 지시서
Projects/personas/loom/PHASE-17-FACTION-STAGE4-CLOSURE-SPEC.md 파일을 그대로 따라 구현하세요.

## 규칙 (절대 준수)
1. 지시서의 [필수] 항목 100% 구현. [금지] 항목 절대 건드리지 말 것.
2. 지시서에 포함된 코드 블록은 직접 복사. 해석 금지.
3. 프레임워크 제약 섹션 먼저 읽고 설계.
4. brain/** 절대 무수정. SNN 구조 변경 금지 (n_neurons=1000 freeze).
5. Stage 1/2/3 상수 값 변경 금지. 새 메커니즘 추가 금지 (Stage 4는 검증·인계 마감 only).
6. SSoT 우회 금지 (`persona.faction = X` 직접 대입은 AST whitelist에 의해 차단됨).
7. 검증 순서:
   a. probe 재실행 → JSON 산출 확인
   b. test_phase17_faction_handoff_contract.py 신규 작성 → PASS
   c. test_phase17_acceptance.py 결정성 + 성능 테스트 → PASS
   d. 핵심 회귀 11종 모두 PASS (test_class_promotion 사전 버그는 명시)
   e. Closure Report 작성 (probe 결과 표 + verdict)
   f. Charter Stage 4 섹션 추가
   g. Φ-3 Charter 스텁 작성
8. 검증 실패 시 재작업, 통과할 때까지 반복.
9. 보고 내용:
   - 변경 파일 목록 (신규 4 + 수정 2)
   - probe 시드별 4 primary 지표 + 3 secondary 지표
   - freeze 테스트 PASS/FAIL (FAIL 시 D10 메서드 보정 내용)
   - 결정성 hash 2회 일치 여부
   - 성능 ms/tick + faction kernel ms/tick
   - Verdict 최종 (Φ-2 CLOSED 또는 Stage 5 escalation)
```

---

## 자체 체크리스트 (작성자 검증)

- [x] 메타 (긴급도/선행/유형/migration/의존) 포함
- [x] 3계층 선언 (궁극/Phase 17/Φ-2 Stage 4 고유 역할) 명시
- [x] 배경 — Stage 1~3 진행 + 현 상태 진단 + 해결 방향
- [x] [필수/선택/금지] 태그로 범위 분류
- [x] 변경 파일 표 + "변경 없음" 명시
- [x] 기계 검증 + 기능 검증 + 계약 검증 3종 분리
- [x] Rollback 섹션
- [x] D10 7종 API freeze 테스트 코드 블록 직접 인용 (해석 여지 차단)
- [x] 결정성 테스트 5채널 (`persona.faction`, `persona.faction_cooldown`, `inner.affiliation_scores`, `engine.factions`, `territory.factionRef`) 명시
- [x] 성능 예산 명시 (≤250ms/tick, faction kernel ≤5ms)
- [x] 진입 트리거 3 조건 구체 수치 (`factions_in_contact ≥ 1`, `max/sum ≥ 0.55`, `grievance 공유 ≥2 faction × ≥3 멤버`)
- [x] Φ-3 Charter 스텁 형식 사전 정의 ([미결] 카탈로그 ≥5)
- [x] Codex 전달용 프롬프트 템플릿 포함
- [x] 모호 표현 0건 ("적절히", "깔끔하게" 등 미사용)
- [x] UI/DB/인프라 혼합 없음 — 단일 유형 (기능: 백엔드 + 일부 설계 문서)
