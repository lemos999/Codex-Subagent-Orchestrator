# Phase 14 Grievance Resonance 보강 — Cross-Territory lord_id Propagation

> 긴급도: 높음 (Φ-3 acceptance #2 자연 PASS 차단 요인)
> 선행 조건: Φ-3 hotfix v1 (commit 5a08998 — 거짓 PASS 5건 제거 + Case B finding)
> 작업 유형: 기능 (mechanism 추가) + 위생 (SSoT 통합 + 중복 제거)
> DB migration: 없음
> 외부 의존: 없음
> 변경 줄 수 예상: +115 / -50 (LoC) — §5 변경 파일 합계 (layers.py +5, engine +60, observe -50, test +50)

---

## 1. 배경

Φ-3 hotfix v1 (commit 5a08998)은 mechanism 거짓 5건을 제거하여 자연 측정 진실성을 복원했다. 그 결과:

| acceptance | 결과 | 측정 (seed 7/13/42) |
|------------|:----:|:-:|
| #1 uprising_event ≥ 1 | **PASS** | 8 / 12 / 9 |
| #2 grievance_pairs_end ≥ 1 | **FAIL** | 0 / 0 / 0 |
| #3 dom_share_end ≥ 0.50 | **PASS** | 80% / 100% / 50% |

**Case B**로 closure 인정 (closure 보고서 §5). #2 FAIL은 **Phase 14 grievance accumulator의 cross-territory lord_id propagation 결손**이 근본 원인 (closure §6 주 finding).

본 spec은 이 결손을 자연 mechanism으로 해결한다. **거짓 PASS 절대 금지** (`feedback_snn_emergence_first.md` + `feedback_root_cause_first.md` 계승).

---

## 2. 근본 원인 분석 (closure §6 주 finding 계승)

### 2.1 코드 구조 (현재 HEAD, multi_tick_engine.py)

`_update_grievances` ([line 2036~2197](core/multi_tick_engine.py#L2036)) 처리 흐름:

| 단계 | line | 동작 | cross-territory 경로 |
|---|---|---|:---:|
| A | 2042~2104 | 자기 territory lord에 대한 grievance 누적 | ✗ (`grievance_lord_id = lord_id` 강제) |
| B | 2107~2129 | same-territory neighbor diffusion | ✗ (`_get_community_members`은 territory 동일 조건) |
| C | 2131~2197 | mass exodus / strike (territory 단위) | ✗ |

### 2.2 결손 정확화

[line 2055](core/multi_tick_engine.py#L2055):
```python
inner.grievance_lord_id = lord_id   # 매 24틱마다 자기 territory lord로 덮어씀
```

[line 2114](core/multi_tick_engine.py#L2114):
```python
neighbors = self._get_community_members(pid, min_trust=0.4)   # same-territory only
```

[line 857~869](core/multi_tick_engine.py#L857):
```python
def _get_community_members(self, pid: str, min_trust: float = 0.4) -> list[str]:
    persona = self.personas[pid]
    territory_id = persona.territory
    members = []
    for other_pid, other in self.personas.items():
        if other_pid == pid or other.territory != territory_id:   # ← cross-territory 차단
            continue
        ...
```

**결론**: 페르소나가 다른 territory의 lord를 grievance 대상으로 인식할 자연 경로가 **구조적으로 부재**. 모든 페르소나의 `grievance_lord_id`는 자기 territory lord로 강제 → faction-level pair는 같은 territory 거주자 사이에서만 형성 가능 → 5000틱 진행으로도 cross-territory pair 0쌍.

### 2.3 보조 finding (closure §6 보조 1·2·3 중 #2·#3)

| 항목 | 현재 | 보강안 |
|---|---|---|
| probe `_shared_grievance_pairs` ([observe:126](observe_phase17_emergence.py#L126)) | `count > 0` | engine SSoT helper 호출 |
| pytest `test_phi3_grievance_pairs_resonate` ([test:362](test_phase17_acceptance.py#L362)) | `cnt ≥ 2` | engine SSoT helper 호출 (다른 인자) |
| observe `_write_top_summary` 중복 ([observe:414, 449](observe_phase17_emergence.py)) | 2개 정의 (후자 override) | 1개 유지 |

보조 finding 1 (`branch_factions_total = 0`)은 별도 spec — Φ-3 acceptance와 무관, 본 spec 범위 외.

---

## 3. 작업 범위

### [필수]

1. **Cross-territory grievance_lord_id propagation mechanism** — 자연 발생 경로 추가
2. **Grievance pair SSoT helper** — engine 단일 helper로 통합 (probe + pytest 호출)
3. **observe `_write_top_summary` 중복 제거** — 1개 정의 유지
4. **acceptance #2 자연 PASS 검증** — 3 seed × 5000 tick 재측정에서 `grievance_pairs_end ≥ 1` (3/3)
5. **무파괴 9 보장** — hotfix v1 계약 그대로 계승

### [선택]

- 없음. (위생 작업 1건 추가는 §보조 finding 3 한정으로 [필수]에 포함)

### [금지]

1. **자기 territory lord 우선 위반** — 자기 grievance가 강하면 자기 territory lord 유지 (cross 위에 own이 자동 우선되어선 안 됨; **자연 가중치 비교만**)
2. **Sticky 가드** — propagation 결과를 24틱 이상 강제 유지하는 hold/cache 금지 (hotfix v1 finding #4 재발 방지)
3. **임의 임계치 손질** — propagation을 강제 발화시키는 후반부 보정·단순 floor 추가 금지
4. **Faction registry 직접 조작** — `_change_persona_faction` signature·`FactionChangeSource` Literal 4종 무수정 (무파괴 #1·#2)
5. **AST whitelist 확장** — 기존 5건 (`# noqa: PHASE17_FACTION_SSOT_WRITE`) 무수정 (무파괴 #3)
6. **SNN 뉴런 300~349 수정** — neuron count·index 무변경 (무파괴 #7)
7. **D10 7종 read-only API signature 변경** — `faction_grievance_targets()` 등 (무파괴 #8)
8. **Φ-3 신규 상수 5종 값 수정** — `THETA_UPRISING`, `UPRISING_CHECK_INTERVAL` 등 (무파괴 #9)
9. **probe / pytest 분리 helper 잔존** — §3 [필수] #2 미수행 시 SSoT 위반 잔존
10. **인공 우선 채택** — propagation 채택을 "더 강한 grievance 보유자" 외 기준 (예: 영향 점수 절대치 무시 후 첫 번째 친구 채택 등) 금지

---

## 4. 구체 사양

### 4.1 신규 상수 ([ontology/layers.py](ontology/layers.py) — Phase 17 Φ-3 상수 직후, line 252 뒤)

```python
# ── Phase 14 grievance resonance 보강 (2026-04-28) ──────────────────────
# Φ-3 hotfix v1 closure §6 주 finding 대응. cross-territory lord_id 자연 전파.
# 자기 territory grievance가 강하면 자기 lord 유지 (자연 가중치 비교).
GRIEVANCE_PROPAGATE_TRUST_MIN = 0.6      # propagation 발동 trust 임계 (community 0.4보다 높음 → 단순 친밀 < 정치적 동조)
GRIEVANCE_DONOR_MIN = 0.5                # propagation 발동 donor grievance 임계 (≥ GRIEVANCE_MIN_SHARED 0.3 + 안전여유)
```

상수 2종만 추가. 기존 Φ-3 5종 ([line 247~250](ontology/layers.py#L247))은 무수정.

### 4.1.1 import 추가 ([core/multi_tick_engine.py](core/multi_tick_engine.py) line 33~71의 `from ontology.layers import (...)` 블록)

기존 `THETA_UPRISING, UPRISING_CHECK_INTERVAL, ...` 라인 직후 또는 SNN_ANGER_FIRE_THRESHOLD 다음 라인에 추가:

```python
    THETA_UPRISING, UPRISING_CHECK_INTERVAL, UPRISING_GRIEVANCE_DECAY,
    UPRISING_FOLLOWER_MAX, SNN_ANGER_FIRE_THRESHOLD,
    GRIEVANCE_PROPAGATE_TRUST_MIN, GRIEVANCE_DONOR_MIN,   # ← 신규 추가
```

### 4.2 cross-territory propagation helper ([core/multi_tick_engine.py](core/multi_tick_engine.py))

`_update_grievances` 내부에 새 단계 D 추가. line 2197 (`return events`) 직전, 단계 C 종료 후 cross-territory propagation 실행.

#### 4.2.1 신규 메서드 `_propagate_grievance_lord_id_cross_territory()`

위치: `_update_grievances` 메서드 정의 직후 (line 2198 뒤). 같은 클래스 멤버.

```python
def _propagate_grievance_lord_id_cross_territory(self) -> None:
    """24틱 주기에서 cross-territory lord_id 자연 전파.

    원리:
        - trust >= GRIEVANCE_PROPAGATE_TRUST_MIN 친구가
        - 다른 territory에 거주하면서
        - grievance >= GRIEVANCE_DONOR_MIN 보유 시
        - 그 친구의 grievance_lord_id를 자신의 후보군에 추가.
        - 자기 territory grievance × 1.0 vs 친구 grievance × trust 중 max 채택.

    invariants:
        - lord_id == None인 경우 propagation 불가 (donor 자격 미달).
        - 자기 territory lord 채택 시에도 score 0이면 갱신 안 함 (sticky 방지).
        - persona가 lord 자신이면 skip (lord 자신은 grievance 대상 아님).
    """
    candidates: dict[str, tuple[str, float]] = {}   # pid -> (best_lord_id, best_score)

    for pid, persona in self.personas.items():
        if pid not in self.inners:
            continue
        inner = self.inners[pid]

        # lord 본인은 grievance 대상 아님
        own_lord = self.territories[persona.territory].lord_id if persona.territory in self.territories else None
        if pid == own_lord:
            continue

        # 자기 territory lord 후보 — 자기 grievance × 1.0 (트러스트는 자기 자신이므로 정의상 1.0)
        best_lord: str | None = None
        best_score: float = 0.0
        if own_lord is not None and inner.grievance > 0.0:
            best_lord = own_lord
            best_score = float(inner.grievance)

        # 다른 페르소나(친구) 후보 탐색
        for other_pid, other in self.personas.items():
            if other_pid == pid:
                continue
            other_inner = self.inners.get(other_pid)
            if other_inner is None:
                continue
            if other_inner.grievance < GRIEVANCE_DONOR_MIN:
                continue
            if other_inner.grievance_lord_id is None:
                continue
            rel_key = Relationship(persona_a=pid, persona_b=other_pid).key()
            rel = self.relationships.get(rel_key)
            if rel is None or rel.trust < GRIEVANCE_PROPAGATE_TRUST_MIN:
                continue
            score = float(other_inner.grievance) * float(rel.trust)
            if score > best_score:
                best_score = score
                best_lord = other_inner.grievance_lord_id

        if best_lord is not None and best_score > 0.0:
            candidates[pid] = (best_lord, best_score)

    # 채택 — 자기 territory 단계에서 이미 설정된 grievance_lord_id를 cross 결과로 덮어쓸 수 있음
    for pid, (lord_id, _score) in candidates.items():
        self.inners[pid].grievance_lord_id = lord_id
```

#### 4.2.2 호출 위치 — `_update_grievances` 마지막 단계

[line 2197 (`return events`)](core/multi_tick_engine.py#L2197) 직전에 단계 D 호출 1줄 추가:

```python
        # 단계 D — Phase 14 보강: cross-territory grievance_lord_id 자연 전파
        self._propagate_grievance_lord_id_cross_territory()

        return events
```

호출 위치 명세:
- **B 단계 (same-territory neighbor diffusion, line 2107~2129) 이후**: own grievance 값이 community 평균 반영 후 결정되므로 propagation의 score 계산이 정확해짐
- **C 단계 (mass exodus / strike, line 2131~2195) 이후**: territory 이주가 일어난 다음 propagation을 적용해야 territory_id-lord_id 일관성 보존
- **return events 직전**: 한 24틱 주기의 마지막 단계로 자연스러운 처리 순서

### 4.3 grievance pair SSoT helper ([core/multi_tick_engine.py](core/multi_tick_engine.py))

`faction_grievance_targets()` 메서드 직후 (line 1702 뒤)에 새 helper 추가:

```python
    def shared_grievance_pairs_count(self, min_carriers: int = 1) -> int:
        """faction-level shared grievance_lord_id pair count.

        같은 lord_id를 ≥ min_carriers 명 보유한 faction을 추출하여, 두 faction이 모두
        해당 lord_id에 대한 carrier ≥ min_carriers 조건을 만족하면 1쌍으로 카운트.

        Args:
            min_carriers: faction별 lord_id carrier 최소 수.
                - 1 (probe widest lens) = ≥ 1명만 carrier여도 인정.
                - 2 (pytest strict) = 응결 검증으로 ≥ 2명 carrier 요구.

        Returns:
            faction 쌍 수 (양방향 중복 제거, (fid_a, fid_b) sorted).
        """
        if min_carriers < 1:
            raise ValueError(f"min_carriers must be >= 1, got {min_carriers}")
        targets = self.faction_grievance_targets()
        by_lord: dict[str, list[str]] = {}
        for fid, lord_map in targets.items():
            for lord_id, cnt in lord_map.items():
                if cnt >= min_carriers:
                    by_lord.setdefault(lord_id, []).append(fid)
        pair_count = 0
        for fids in by_lord.values():
            if len(fids) < 2:
                continue
            pair_count += len(fids) * (len(fids) - 1) // 2
        return pair_count
```

#### 4.3.1 probe 호출 변경 ([observe_phase17_emergence.py:126~137](observe_phase17_emergence.py#L126))

```python
# 삭제: _shared_grievance_pairs(raw) 함수 정의 (line 126~137)

# 호출처 변경 ([observe:176](observe_phase17_emergence.py#L176)):
#   "shared_pairs": _shared_grievance_pairs(grievance_raw),
#                                 ↓
#   "shared_pairs": engine.shared_grievance_pairs_count(min_carriers=1),
```

이때 `engine` 참조는 `_dump_snapshot(handle, engine, tick)` signature에서 직접 사용 가능.

#### 4.3.2 pytest 호출 변경 ([test_phase17_acceptance.py:358~373](test_phase17_acceptance.py#L358))

```python
def test_phi3_grievance_pairs_resonate():
    """Φ-3 acceptance #2: grievance_pairs_end >= 1 (3/3, cross-territory 자연 응결)."""
    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        pair_count = engine.shared_grievance_pairs_count(min_carriers=2)
        assert pair_count >= 1, f"seed {seed}: grievance_pairs 0쌍 (cross-territory 자연 응결 실패)"
```

### 4.4 observe `_write_top_summary` 중복 제거 ([observe_phase17_emergence.py:414~448](observe_phase17_emergence.py#L414))

[line 414](observe_phase17_emergence.py#L414)~[line 448](observe_phase17_emergence.py#L448)의 첫 번째 `_write_top_summary` 정의 **전체 삭제**. 두 번째 정의 ([line 449~](observe_phase17_emergence.py#L449)) 유지.

**검증**: `grep -c "^def _write_top_summary" observe_phase17_emergence.py` 결과 `1` 이어야 함.

---

## 5. 변경 파일

| 파일 | 작업 | 줄 수 변동 |
|------|------|:-:|
| `Projects/personas/loom/ontology/layers.py` | 수정 (상수 2종 추가) | +5 |
| `Projects/personas/loom/core/multi_tick_engine.py` | 수정 (helper 2개 + 호출 1줄) | +60 |
| `Projects/personas/loom/observe_phase17_emergence.py` | 수정 (`_shared_grievance_pairs` 제거 + 호출 변경 + 중복 `_write_top_summary` 제거) | -50 |
| `Projects/personas/loom/test_phase17_acceptance.py` | 수정 (테스트 1개 + 신규 테스트 3개) | +50 |

**변경 없음 (금지):**
- `Projects/personas/loom/ontology/__init__.py` — export 수정 불요 (상수는 layers.py 직접 import 가능)
- `Projects/personas/loom/test_phase17_faction_handoff_contract.py` — Phase 17 Φ-2 contract 무관
- `Projects/personas/loom/test_phase17_acceptance.py`의 기존 hotfix 테스트 3건 (`test_branch_faction_id_no_collision`, `test_grievance_lord_id_not_sticky`, `test_uprising_tick_no_artificial_injection`) 무수정
- core/multi_tick_engine.py의 `_uprising_trigger`, `_emit_uprising`, `_uprising_tick`, `_spawn_branch_faction` — Φ-3 hotfix v1 결과 그대로 유지

---

## 6. 계약 — 무파괴 9 보장 (hotfix v1 계승)

| # | 항목 | 본 spec 영향 |
|---|------|:--:|
| 1 | `_change_persona_faction` 시그니처 | 호출 없음 |
| 2 | `FactionChangeSource` Literal 4종 | 호출 없음 |
| 3 | AST whitelist `# noqa: PHASE17_FACTION_SSOT_WRITE` 5건 | 신규 노란 위치 없음 |
| 4 | `Faction.grace_until_tick` | 무수정 |
| 5 | `Faction.founder_lineage` | 무수정 |
| 6 | `InnerWorld.residence_ticks` | 무수정 |
| 7 | SNN 뉴런 300~349 / n_neurons | 무수정 |
| 8 | D10 7종 read-only API | `faction_grievance_targets()` signature 무수정. `shared_grievance_pairs_count()` 신규 추가만 |
| 9 | Φ-3 신규 상수 5종 값 | 무수정 |

신규 상수 2종 (`GRIEVANCE_PROPAGATE_TRUST_MIN`, `GRIEVANCE_DONOR_MIN`)은 **신규 추가**로 무파괴 #9에 위배되지 않음 (값 변경이 아님).

---

## 7. 검증

### 7.1 기계 검증 (필수, 순서대로)

```bash
cd Projects/personas/loom

py -m py_compile ontology/layers.py
py -m py_compile core/multi_tick_engine.py
py -m py_compile observe_phase17_emergence.py
py -m py_compile test_phase17_acceptance.py
```

전부 통과해야 함.

### 7.2 회귀 테스트 (필수)

```bash
cd Projects/personas/loom

py test_phase17_faction_handoff_contract.py    # Φ-2 12건 PASS 유지
py -m pytest test_phase17_acceptance.py::test_branch_faction_id_no_collision
py -m pytest test_phase17_acceptance.py::test_grievance_lord_id_not_sticky
py -m pytest test_phase17_acceptance.py::test_uprising_tick_no_artificial_injection
py -m pytest test_phase17_acceptance.py::test_phi2_phi3_continuity_hash
py -m pytest test_phase17_acceptance.py::test_phi3_dom_share_natural_imbalance
```

전부 PASS 유지.

### 7.3 신규 테스트 (필수)

`test_phase17_acceptance.py`에 추가:

#### 7.3.1 `test_grievance_pair_helper_ssot`

```python
def test_grievance_pair_helper_ssot():
    """probe와 pytest가 같은 engine helper 호출 (legacy probe helper는 제거되어야 함)."""
    import observe_phase17_emergence as observe_mod
    # legacy 분리 helper가 제거되었는지 검증
    assert not hasattr(observe_mod, "_shared_grievance_pairs"), (
        "legacy probe helper _shared_grievance_pairs는 SSoT 통합으로 제거되어야 함"
    )
    # engine helper 존재 검증
    from core.multi_tick_engine import MultiTickEngine
    assert hasattr(MultiTickEngine, "shared_grievance_pairs_count"), (
        "engine.shared_grievance_pairs_count helper 누락"
    )
```

#### 7.3.2 `test_grievance_propagation_no_artificial_sticky`

```python
def test_grievance_propagation_no_artificial_sticky():
    """propagation 본문에 sticky/floor/cache 의심 키워드 0건 (정적 검증).

    런타임 검증은 시뮬 내 다중 mechanism 간섭으로 결정성 확보가 어렵다.
    소스 정적 grep + propagation idempotency 검증으로 대체.
    트랩: hotfix v1 finding #4 (sticky lord_id guard) 재발 방지.

    검출 방식: word-boundary regex (False-positive 방지).
    예: "threshold"의 "hold" 부분 매칭은 무시. 토큰으로서의 "hold"만 검출.
    """
    import inspect
    import re
    from core.multi_tick_engine import MultiTickEngine
    src = inspect.getsource(MultiTickEngine._propagate_grievance_lord_id_cross_territory)

    # word-boundary 기반 토큰 매칭 (substring 매칭으로 인한 false-positive 방지)
    forbidden_tokens = ["sticky", "previous_lord", "prev_lord", "hold"]
    for kw in forbidden_tokens:
        assert re.search(rf"\b{re.escape(kw)}\b", src) is None, (
            f"propagation 본문에 sticky 의심 토큰 '{kw}' 검출 — hotfix v1 finding #4 재발 위험"
        )

    # 부분 매칭 의심 키워드 — 정당 용례가 거의 없으므로 substring으로 검사
    forbidden_substrings = ["_cache", "_sticky_"]
    for kw in forbidden_substrings:
        assert kw not in src, (
            f"propagation 본문에 sticky 의심 키워드 '{kw}' 검출 — hotfix v1 finding #4 재발 위험"
        )

    # idempotency: 같은 입력에 대해 2회 호출 결과가 동일 (cache 잔존 없음)
    engine = run_simulation(seed=7, ticks=200)
    snapshot_a = {pid: inner.grievance_lord_id for pid, inner in engine.inners.items()}
    engine._propagate_grievance_lord_id_cross_territory()
    snapshot_b = {pid: inner.grievance_lord_id for pid, inner in engine.inners.items()}
    engine._propagate_grievance_lord_id_cross_territory()
    snapshot_c = {pid: inner.grievance_lord_id for pid, inner in engine.inners.items()}

    # 첫 직접 호출은 시뮬 진행 외 변화 없음 → snapshot_a == snapshot_b 또는 snapshot_b == snapshot_c
    # (a→b 사이에는 grievance 변화 가능. b→c는 grievance 변화 없으므로 결과 동일해야 함)
    assert snapshot_b == snapshot_c, (
        "propagation 결과가 두 번째 idempotent 호출에서 변동 — cache/sticky 잔존 의심"
    )
```

#### 7.3.3 `test_phi3_grievance_pairs_resonate` (수정 — 4.3.2 § 참조)

기존 helper(by_lord 직접 계산)를 `engine.shared_grievance_pairs_count(min_carriers=2)` 호출로 변경.

#### 7.3.4 `test_grievance_propagate_natural_emergence`

> **부하 정책**: 본 테스트는 5000틱 × 3 seed로 단일 실행 시 수 분이 소요된다. pytest 기본 실행에서는 제외하고 `pytest -m slow` 또는 명시 호출 시에만 수행. acceptance #2 자연 PASS 최종 판정은 §7.4 probe 재측정으로 한다 (probe와 본 테스트는 같은 SSoT helper 호출).

```python
import pytest

@pytest.mark.slow
def test_grievance_propagate_natural_emergence():
    """5000틱 진행 후 cross-territory grievance pair가 자연 발생 — Φ-3 acceptance #2 자연 PASS.

    부하: 5000틱 × 3 seed (수 분). 기본 pytest 실행에서 제외 (`@pytest.mark.slow`).
    명시 실행: `py -m pytest test_phase17_acceptance.py -m slow`.
    최종 판정 SSoT: §7.4 probe 재측정 (`observe_phase17_emergence.py --label phi3-phase14-resonance`).
    """
    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        # min_carriers=1 (probe widest lens) 기준
        pairs_wide = engine.shared_grievance_pairs_count(min_carriers=1)
        # min_carriers=2 (pytest strict) 기준
        pairs_strict = engine.shared_grievance_pairs_count(min_carriers=2)
        assert pairs_wide >= 1, (
            f"seed {seed}: cross-territory propagation 실패 (probe lens=1, pairs={pairs_wide})"
        )
        assert pairs_strict >= 1, (
            f"seed {seed}: cross-territory 응결 실패 (pytest strict=2, pairs={pairs_strict})"
        )
```

**`pytest.ini` 또는 `pyproject.toml` 마커 등록 (없을 시 추가)**:
```ini
[pytest]
markers =
    slow: 무거운 시뮬 테스트 (5000틱+). 명시 호출 시에만 수행.
```

### 7.4 probe 재측정 (필수)

```bash
cd Projects/personas/loom

py observe_phase17_emergence.py --label phi3-phase14-resonance --seeds 7,13,42 --ticks 5000
```

**기대 결과** (data/phase17_probe_phi3-phase14-resonance/SUMMARY.md 자동 생성):

| # | 기준 | seed 7 | seed 13 | seed 42 | 결과 |
|---|------|:------:|:-------:|:-------:|:----:|
| 1 | uprising_event ≥ 1 | ≥ 1 | ≥ 1 | ≥ 1 | **PASS** |
| 2 | grievance_pairs_end ≥ 1 | ≥ 1 | ≥ 1 | ≥ 1 | **PASS** |
| 3 | dom_share_end ≥ 0.50 | ≥ 50% | ≥ 50% | ≥ 50% | **PASS** |

### 7.5 결과 분기 정책

| Case | 정의 | 후속 |
|------|------|------|
| **Case A — 전체 자연 PASS** | 3 acceptance × 3 seed 모두 PASS | Φ-3 closure 2차 확정. 5단계 Φ-4 Nation Charter 진입 |
| **Case B' — pair만 PASS, 회귀** | acceptance #2 PASS이나 #1·#3 회귀 | propagation 부작용 finding. 추가 hotfix |
| **Case C — pair 여전히 FAIL** | acceptance #2 0쌍 잔존 | propagation 임계치 상향 또는 다른 mechanism (예: cross-territory work/trade interaction) 검토. 본 spec 중단, 사용자 결정 대기 |

**거짓 PASS는 절대 허용하지 않는다** — Case A 충족 시에도 hotfix v1과 동일하게 다음 검증:
- `_propagate_grievance_lord_id_cross_territory` 본문에 sticky/floor/artificial injection 0건
- `grep -c "^def _shared_grievance_pairs" observe_phase17_emergence.py` 결과 0
- `grep -c "^def _write_top_summary" observe_phase17_emergence.py` 결과 1

---

## 8. Rollback

본 spec 적용 commit revert (commit 직후 본 spec §8에 hash 갱신):

```bash
# 옵션 A: commit hash 기반 (commit 직후 hash 명기)
git revert <commit_hash>

# 옵션 B: hash-free 파일별 수동 복원 (Phase 14 보강이 직전 commit인 경우)
git checkout HEAD~1 -- \
    Projects/personas/loom/ontology/layers.py \
    Projects/personas/loom/core/multi_tick_engine.py \
    Projects/personas/loom/observe_phase17_emergence.py \
    Projects/personas/loom/test_phase17_acceptance.py
```

> **hash 갱신 절차**: Phase 14 보강 closure commit 직후, 본 §8의 `<commit_hash>`를 실제 hash로 치환하여 `docs(loom): update Phase 14 spec rollback hash` commit으로 갱신.

데이터 영향: 없음 (런타임 mechanism 추가만, persisted state 변경 없음). probe 결과 디렉토리는 `.gitignore`로 무시.

회귀 검증:
```bash
py test_phase17_faction_handoff_contract.py
py -m pytest test_phase17_acceptance.py::test_phi2_phi3_continuity_hash
```

---

## 9. 자체 검증 체크리스트 (구현자 — Codex 또는 Claude)

구현 완료 보고 **전** 모두 통과해야 함:

### 9.1 코드 무결성

- [ ] `py -m py_compile` 4개 파일 전부 통과
- [ ] `_propagate_grievance_lord_id_cross_territory` 본문 ≤ 50줄
- [ ] `shared_grievance_pairs_count` 본문 ≤ 20줄
- [ ] sticky 의심 토큰 0건 (word-boundary 매칭, §9.6 기준 그대로)
- [ ] `min_carriers < 1` ValueError 검증

### 9.2 SSoT 통합

- [ ] `grep -c "def _shared_grievance_pairs" Projects/personas/loom/observe_phase17_emergence.py` 결과 **0**
- [ ] `grep -c "def _write_top_summary" Projects/personas/loom/observe_phase17_emergence.py` 결과 **1**
- [ ] `grep -c "engine.shared_grievance_pairs_count" Projects/personas/loom/observe_phase17_emergence.py` 결과 ≥ **1**
- [ ] `grep -c "engine.shared_grievance_pairs_count" Projects/personas/loom/test_phase17_acceptance.py` 결과 ≥ **1**

### 9.3 무파괴 9 보장

- [ ] `_change_persona_faction(...)` 시그니처 git diff 변동 없음
- [ ] `FactionChangeSource = Literal[...]` 4종 git diff 변동 없음
- [ ] `# noqa: PHASE17_FACTION_SSOT_WRITE` 마커 5건 그대로
- [ ] `THETA_UPRISING = 0.40`, `UPRISING_CHECK_INTERVAL = 48`, `UPRISING_GRIEVANCE_DECAY = 0.5`, `UPRISING_FOLLOWER_MAX = 2`, `SNN_ANGER_FIRE_THRESHOLD = 0.6` 값 무수정

### 9.4 회귀 + 신규 테스트

- [ ] 기존 acceptance 테스트 5건 + handoff contract 12건 PASS
- [ ] 신규 테스트 3건 PASS (`test_grievance_pair_helper_ssot`, `test_grievance_propagation_no_artificial_sticky`, `test_grievance_propagate_natural_emergence`)
- [ ] `test_phi3_grievance_pairs_resonate` 수정 후 PASS

### 9.5 probe 재측정

- [ ] `py observe_phase17_emergence.py --label phi3-phase14-resonance --seeds 7,13,42 --ticks 5000` 정상 종료
- [ ] `data/phase17_probe_phi3-phase14-resonance/SUMMARY.md` Primary 3종 PASS
- [ ] secondary verdict 회귀 없음 (active_factions_end ≥ 1, drift_ratio ≤ 60% 권장 — 단 strict 기준 아님)

### 9.6 거짓 PASS 차단

- [ ] propagation 본문에 다음 토큰 0건 (word-boundary 검사): `sticky`, `hold`, `previous_lord`, `prev_lord`
- [ ] propagation 본문에 다음 substring 0건: `_cache`, `_sticky_`
- [ ] propagation 본문에 artificial 보정 의도 의심 표현 (예: `if score < threshold: score = threshold`, 후반부 강제 floor) 0건
- [ ] propagation 결과는 24틱 주기마다 **재계산** (cache 잔존 없음)
- [ ] propagation 본문에 sticky/cache/hold 키워드 grep 0건이며, 동일 입력 2회 호출 결과가 동일 (`test_grievance_propagation_no_artificial_sticky` PASS — 정적 grep + idempotency 검증)

---

## 10. 결과 분기 후속 작업

### Case A (자연 PASS 3/3)

1. closure 보고서 2차 작성: `PHASE-17-STRUGGLE-CLOSURE-REPORT-PHASE14.md`
2. Φ-3 acceptance 자연 충족 공식 인정 (Charter v2 entry check OR-3 0쌍 결손 해결)
3. 5단계 Φ-4 Nation Charter 진입 (`/design`)

### Case B' (회귀 발생)

1. propagation 부작용 분석 — uprising 발화 변동 / dom_share 분포 변동 식별
2. 추가 hotfix spec — propagation 가중치 또는 timing 조정
3. 본 spec 부분 rollback 후 재시도

### Case C (pair 여전히 FAIL)

1. propagation 임계치 분석 — `GRIEVANCE_PROPAGATE_TRUST_MIN = 0.6`이 너무 높았을 가능성
2. 대체 mechanism 검토:
   - Option B: cross-territory work/trade interaction 시 lord_id 자연 인식 (Phase 11~16 경제 시스템 활용)
   - Option C: territory adjacency 기반 propagation (`_territory_neighbors` 활용)
3. 사용자 결정 대기

---

## 11. GPT/Codex 전달 프롬프트

```
당신은 loom (페르소나 자율 사회 시뮬) 프로젝트의 시니어 Python 개발자입니다.

## 프로젝트 경로
c:\Users\haj\projects\subagent-orchestrator\Projects\personas\loom

## 기술 스택
- Python 3.11+
- numpy, pytest
- SNN 시뮬레이션 + multi-tick engine + Phase 17 Φ-2/Φ-3 mechanism

## 작업 지시서
PHASE-14-GRIEVANCE-RESONANCE-SPEC.md 파일을 그대로 따라 구현하세요.

## 규칙 (절대 준수)
1. 지시서의 [필수] 항목 100% 구현. [금지] 항목 절대 건드리지 말 것.
2. 무파괴 9 보장 — Φ-3 hotfix v1 (commit 5a08998) 계약 그대로 계승. 
3. 자기 검증 체크리스트 §9 모든 항목 통과 후에만 완료 보고.
4. **거짓 PASS 절대 금지** — propagation 결과를 강제 유지하는 sticky/floor/artificial 보정 0건. 
   24틱마다 자연 재계산만 허용.
5. 검증 순서:
   a. py -m py_compile (4개 파일)
   b. py test_phase17_faction_handoff_contract.py
   c. py -m pytest test_phase17_acceptance.py
   d. py observe_phase17_emergence.py --label phi3-phase14-resonance --seeds 7,13,42 --ticks 5000
   e. SUMMARY.md Primary 3종 PASS 확인
6. 검증 실패 시 재작업, 통과할 때까지 반복.

## 보고 내용
- 변경 파일 목록 + 줄 수 변동
- 각 검증 단계 통과 여부
- SUMMARY.md Primary 결과 (acceptance #1·#2·#3 각각)
- §9 자체 검증 체크리스트 결과
- Case 판정 (A/B'/C)
- 거짓 PASS 차단 검증 (propagation 본문 키워드 grep 결과)
```

---

## 12. 결론

본 spec은 Φ-3 hotfix v1 closure §6 주 finding (Phase 14 cross-territory propagation 결손)을 자연 mechanism으로 해결한다. 핵심:

1. `GRIEVANCE_PROPAGATE_TRUST_MIN = 0.6` + `GRIEVANCE_DONOR_MIN = 0.5` 임계치 2종으로 자연 사회적 영향 모델
2. `grievance × trust` 가중치 비교로 자기 territory lord vs cross-territory lord 자연 경쟁
3. SSoT helper `engine.shared_grievance_pairs_count(min_carriers)`로 probe + pytest 통합
4. observe `_write_top_summary` 중복 제거

**거짓 PASS 차단**: hotfix v1과 동일 원칙 — propagation 본문 ≤ 50줄, sticky/floor/cache 키워드 0건, 24틱 주기 자연 재계산만 허용.

성공 시 Φ-3 acceptance 3종 자연 PASS → Case A → Φ-3 closure 2차 + 5단계 Φ-4 Nation 진입.
