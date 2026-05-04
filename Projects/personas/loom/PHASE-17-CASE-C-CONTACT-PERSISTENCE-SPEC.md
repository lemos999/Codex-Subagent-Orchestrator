# Phase 17 Φ-3 Case-C P1+P2 통합 spec — Contact Graph 자연 확장 + Founder Loyalty 가산

> 긴급도: 높음 (acceptance #2 grievance_pairs_end FAIL — Case C diagnosis 후속)
> 선행 조건: PHASE-17-CASE-C-DIAGNOSIS-REPORT.md (P1 1순위 + P2 2순위 식별), PHASE-17-CASE-C-P1-P2-SPEC-V2.md (BOOST 0.15→0.20 PARTIAL_PROGRESS 종결)
> 작업 유형: 기능 (자연 메커니즘 추가)
> DB migration: 없음
> 외부 의존: 없음
> 작성일: 2026-04-30
> 목적 정렬:
>   - 궁극: LOOM 자율 사회 시뮬 + SNN 창발 + PersonaBrain 논문
>   - Phase 목적: Φ-3 Struggle 의 grievance_pairs_end 자연 PASS 빈도 회복
>   - 본 spec 고유 역할: 두 단계 붕괴 (contact graph 0쌍 + founder 흡수) 의 자연 메커니즘 패치 — sticky/floor/artificial 우회 금지

---

## 배경

`PHASE-17-CASE-C-DIAGNOSIS-REPORT.md` 6 가설 판정 결과 두 단계 붕괴가 식별되었다.

1. **Contact graph collapse**: `contact_pairs_end = 0/0/0` (3 seed 전원). uprising 자체는 13/11/16 회 발화하나, 인접 faction 부재로 grievance resonance 가 cross-faction 으로 이어지지 못해 `uprising_skip_no_contact = 99/158/78` 다발.
2. **Founder absorption**: respawn fallback 으로 minority faction 이 3/1/2 개 생성되지만, 끝까지 유지되지 못해 `absorbed_by_end = 2/1/1`. 최종 active=1 수렴.

선행 SPEC-V2 (BOOST 0.15→0.20) 는 PARTIAL_PROGRESS (1/3 → 2/3) 로 종결되었다. seed-13 trajectory 동결은 단일 lever 한계 신호로 식별되어, **차원 전환 — 두 자연 메커니즘 (P1 + P2) 추가** 가 합의되었다.

본 spec 은 진단 보고서 §패치 후보의 **P1 (Contact Graph Recovery)** 와 **P2 (Respawn Founder Persistence)** 를 통합한다. 두 축은 상호 보완:
- P2 는 신생 founder 가 흡수되지 않고 지속 → minority faction 이 살아있는 상태에서
- P1 은 그 minority faction 이 인접 territory 거주민 관계 통해 자연 contact 회복 → uprising 발화 가능성 ↑

---

## 작업 범위

### [필수]

1. **P1**: `factions_in_contact()` 자연 확장 — 인접 territory 거주민 간 cross-faction trust >= 0.4 관계가 1개 이상이면 contact 인정 (territoryRef path 기존 유지 + persona-based path 신규 추가).
2. **P2**: `FOUNDER_LOYALTY_BONUS = 0.15` 상수 신규 + `_compute_affiliation_tick` 의 founder 자기 faction grace 가산 분기 추가. grace 종료 시 정확히 0.
3. 텔레메트리 2종 추가: `contact_via_persona_relationship` (P1 path 활성), `founder_loyalty_applied` (P2 가산).
4. 자연 측정 5000틱 × 3 seed 통해 acceptance #2 PASS 빈도 측정 (목표: 3/3, 부분 효과도 데이터로 기록).

### [선택]

- chain.json 에 P1 path 발생 위치 (territory_id 쌍) 기록.
- closure 보고서 작성 시 SPEC-V2 와 동일 형식.

### [금지]

- **sticky contact**: contact 회복 후 N틱 보존하는 메커니즘 추가 금지 (자연 재계산 원칙).
- **floor contact**: contact_pairs >= 1 보장하는 인공 하한 금지.
- **artificial propagation**: relationship.trust 직접 강제 증가 금지.
- **acceptance 우회**: grievance_pairs_end 직접 조작 금지.
- **새 source enum 추가**: FactionChangeSource 4종 (`birth_founder`, `affiliation`, `cooldown`, `conflict`) 무수정.
- **score \*= 형태**: P2 founder loyalty 는 반드시 `score += FOUNDER_LOYALTY_BONUS` 가산식. 곱셈 금지 (THETA_JOIN 우회 차단).
- 안전 전제 5종 변경: HYSTERESIS=2, FOUNDER_RESPAWN_EVERY=480, TARGET_ACTIVE=2, COMMIT_EVERY=48, MAX_MEMBERS=2 무수정.
- mechanism 본문 직접 변경: `_uprising_trigger`, `_emit_uprising`, `_respawn_faction_tick` 본체 로직 무수정 (`factions_in_contact` 만 자연 확장).
- 회귀 7종 (`test_economy.py`, `test_governance.py`, `test_class_promotion.py`, `test_nomos.py`, `test_phase17_faction_handoff_contract.py`, `test_phase14b_snn_integration.py`, `test_phase17_faction_stage3.py`) 어느 하나라도 FAIL 시 spec FAIL.

---

## 구체 사양

### A. P1 — `factions_in_contact()` 자연 확장

#### A-1. 현재 구현 (`core/multi_tick_engine.py:1734~1751`)

```python
def factions_in_contact(self, radius: int = 1) -> list[tuple[str, str]]:
    """근접 Territory 간 서로 다른 factionRef 쌍."""
    if radius < 1:
        raise ValueError(f"radius must be >= 1, got {radius}")
    pairs: set[tuple[str, str]] = set()
    for tid in sorted(self.territories):
        ref_a = self.territories[tid].factionRef
        if ref_a is None:
            continue
        for nid in self._territories_within(tid, radius):
            if nid <= tid:
                continue
            ref_b = self.territories[nid].factionRef
            if ref_b is None or ref_b == ref_a:
                continue
            a, b = sorted((ref_a, ref_b))
            pairs.add((a, b))
    return sorted(pairs)
```

**문제**: territory.factionRef 만 매개. 신생 minority faction 이 territory dominance (FACTION_HYSTERESIS=2) 를 못 얻으면 contact 영구 부재.

#### A-2. 변경 후 (자연 path 추가)

```python
def factions_in_contact(self, radius: int = 1) -> list[tuple[str, str]]:
    """근접 Territory 간 서로 다른 factionRef 쌍.

    Phase 17 Φ-3 Case-C P1 (2026-04-30):
        territoryRef path (기존) + persona-based path (신규).
        territoryRef 가 dominance 부족 (HYSTERESIS=2 미달) 으로 None/단일 인 경우에도,
        인접 territory 거주민 간 cross-faction trust >= 0.4 관계가 1개 이상이면 contact 인정.
        sticky/floor 아님 — 매 호출 자연 재계산. relationship.trust 진화에만 의존.
    """
    if radius < 1:
        raise ValueError(f"radius must be >= 1, got {radius}")
    pairs: set[tuple[str, str]] = set()
    # Path 1: territoryRef 기반 (기존)
    for tid in sorted(self.territories):
        ref_a = self.territories[tid].factionRef
        if ref_a is None:
            continue
        for nid in self._territories_within(tid, radius):
            if nid <= tid:
                continue
            ref_b = self.territories[nid].factionRef
            if ref_b is None or ref_b == ref_a:
                continue
            a, b = sorted((ref_a, ref_b))
            pairs.add((a, b))
    # Path 2: persona relationship 기반 (Phase 17 Φ-3 Case-C P1)
    # 인접 territory 거주민 cross-faction 관계가 contact 매개임을 자연으로 인정.
    territory_residents: dict[str, list[Persona]] = {tid: [] for tid in self.territories}
    for persona in self.personas.values():
        if (
            persona.id in self.inners
            and persona.faction is not None
            and persona.territory in territory_residents
        ):
            territory_residents[persona.territory].append(persona)
    for tid in sorted(self.territories):
        residents_a = territory_residents[tid]
        if not residents_a:
            continue
        for nid in self._territories_within(tid, radius):
            if nid <= tid:
                continue
            residents_b = territory_residents[nid]
            if not residents_b:
                continue
            for pa in residents_a:
                for pb in residents_b:
                    if pa.faction == pb.faction or pa.faction is None or pb.faction is None:
                        continue
                    pair_sorted = tuple(sorted((pa.faction, pb.faction)))
                    if pair_sorted in pairs:
                        continue  # 이미 territoryRef path 로 인정됨
                    trust = self._get_relationship_trust(pa.id, pb.id)
                    if trust >= 0.4:
                        pairs.add(pair_sorted)
                        self.event_log.append({
                            "type": "contact_via_persona_relationship",
                            "tick": self.time.tick,
                            "fid_a": pair_sorted[0],
                            "fid_b": pair_sorted[1],
                            "tid_a": tid,
                            "tid_b": nid,
                            "trust": float(trust),
                        })
                        break  # 한 쌍의 territory 간 contact 인정 1건만
                else:
                    continue
                break
    return sorted(pairs)
```

**삽입 위치**: `core/multi_tick_engine.py:1751` (기존 return 직전 — Path 2 블록 추가 후 sort 반환).

**자연 메커니즘 정당화**:
- 임계 0.4 = `_pick_seed_group` 의 `trust >= 0.4` 와 정합 (community 임계). 별개 임계 도입 금지.
- `for/else/break` 조기 종료: 한 territory 쌍에서 contact 1건만 기록 (성능 — O(N²) 방지).
- 매 호출 자연 재계산 — sticky 아님.
- `pair_sorted in pairs` 체크: territoryRef path 우선 (중복 텔레메트리 방지).

**계산 복잡도 분석**:
- 호출 빈도: `_uprising_trigger` 에서 24/48틱마다 1회 호출 (5000틱 동안 ~100~200회).
- territory 쌍 수: ~6~8 territories × neighbors radius=1 ≈ ~24 쌍 (Chebyshev 인접).
- 거주민 곱: 한 territory 당 평균 ~5 personas → O(territory_pairs × residents²) ≈ 24 × 25 = ~600 trust 조회.
- 5000틱 총 cost: ~200 × 600 = ~120,000 trust 조회 — 충분히 허용 범위.
- **radius >= 2 호출 시 O(N⁴) 위험**: 본 spec 은 radius=1 (기본값) 만 가정. radius >= 2 호출 시 별도 검토 필요.

#### A-3. 텔레메트리

`contact_via_persona_relationship` event:
- `fid_a, fid_b`: sorted faction id 쌍
- `tid_a, tid_b`: 매개 territory 쌍 (a < b)
- `trust`: 매개 관계의 trust 값
- 매 호출 시 새 event log entry — 누적 카운트로 P1 path 활성 빈도 측정 가능.

---

### B. P2 — Founder Loyalty Bonus

#### B-1. 신규 상수 (`ontology/layers.py`)

기존 `GRACE_AFFILIATION_BOOST = 0.12` (line 262) 직후 추가:

```python
# ── Phase 17 Φ-3 Case-C P2: Founder loyalty bonus (2026-04-30) ──
# 근거: respawn fallback founder 즉시 흡수 (DIAGNOSIS H2c absorbed_by_end 2/1/1) 완화.
# founder 자신이 자기 신생 faction 에 grace 기간 동안 자연 score 가산.
# GRACE_AFFILIATION_BOOST(0.12) 위, W_LINEAGE(0.2) 아래로 두어 founder 단독 차별 의도 명시.
# grace_until_tick 종료 시 정확히 0 (sticky 금지). score *= 형태 금지 (THETA_JOIN 우회 차단).
FOUNDER_LOYALTY_BONUS = 0.15
```

**삽입 위치**: `ontology/layers.py:263` (GRACE_AFFILIATION_BOOST 다음 빈 줄).

**값 정당화**:
- W_LINEAGE = 0.2 (founder lineage affinity 기본)
- GRACE_AFFILIATION_BOOST = 0.12 (grace 기간 same-territory 거주자)
- FOUNDER_LOYALTY_BONUS = 0.15 (founder 본인) — 두 값 사이에 위치.
- founder 차별: founder 본인이 일반 grace 동거자보다 자기 faction 에 더 강한 자연 충성 가짐을 모델.
- W_TRUST(0.5), W_TERRITORY_SAME(0.5) 의 30% 수준 — 우위 결정 변수가 아닌 자연 가산.

#### B-2. `_compute_affiliation_tick` 수정 (`core/multi_tick_engine.py:1271~1280`)

기존 P2 grace 분기 (line 1271~1280):

```python
# Φ-3 Case-C P2: founder grace 흡수 면역 (2026-04-30)
# 자연 가산 — same-territory 거주자에 grace 200틱 동안 GRACE_AFFILIATION_BOOST 가산.
# grace 종료 시 정확히 0. score *= 형태 금지 (임계 우회 차단).
cand_faction_for_grace = self.factions.get(fid)
if (
    cand_faction_for_grace is not None
    and cand_faction_for_grace.grace_until_tick > self.time.tick
    and self._same_territory(persona, fid) > 0.5
):
    score += GRACE_AFFILIATION_BOOST
```

**바로 다음에 추가** (line 1280 직후):

```python
# Φ-3 Case-C P2 보강: founder loyalty bonus (2026-04-30)
# founder 본인이 자기 신생 faction 에 grace 기간 동안 추가 자연 가산.
# 흡수 면역이 아니라 자연 충성 — score += 형태, grace 종료 시 정확히 0.
if (
    cand_faction_for_grace is not None
    and cand_faction_for_grace.founder_pid == persona.id
    and persona.faction == fid
    and cand_faction_for_grace.grace_until_tick > self.time.tick
):
    score += FOUNDER_LOYALTY_BONUS
    if pid == diagnostic_first_pid:
        self.event_log.append({
            "type": "founder_loyalty_applied",
            "tick": self.time.tick,
            "fid": fid,
            "founder_pid": persona.id,
            "grace_remaining": int(
                cand_faction_for_grace.grace_until_tick - self.time.tick
            ),
        })
```

**조건 정당화**:
- `cand_faction_for_grace.founder_pid == persona.id`: founder 본인만 (`birth_founder` source 계약 유지).
- `persona.faction == fid`: 이미 가입한 자기 faction 에 대한 충성 (다른 faction 의 grace 흡수 금지).
- `grace_until_tick > self.time.tick`: grace 기간 종료 시 정확히 0 (sticky 금지).
- 텔레메트리 첫 pid 만 기록 (event_log 폭주 방지) — minority_boost_applied 패턴과 정합.

**수정 위치**: `core/multi_tick_engine.py:1281` (`scored[fid] = DECAY * ...` 직전).

#### B-3. import 갱신 (`core/multi_tick_engine.py:33~73` 영역)

기존 import 블록 형식 (line 33 `from ontology.layers import (`, line 73 닫는 괄호):

```python
# Before (line 69)
    GRACE_AFFILIATION_BOOST,

# After (line 69~70)
    GRACE_AFFILIATION_BOOST,
    FOUNDER_LOYALTY_BONUS,
```

**정확한 위치**: `core/multi_tick_engine.py:69` `GRACE_AFFILIATION_BOOST,` 다음 줄 (line 70 신규 1줄 삽입). 닫는 괄호 `)` 위치는 line 73 → line 74 로 이동.

**`from ontology import (...)` 블록 (line 19~32)**: 본 spec 은 layers.py 직접 import 경로 (line 33~73) 만 사용. `from ontology import` 블록 (line 19~32) 무수정.

**`__init__.py` 갱신 불필요**: `multi_tick_engine.py` 는 `from ontology.layers import` 직접 경로 사용. `ontology/__init__.py` 의 `__all__` 갱신은 본 spec 범위 외 (선택). 필요 시 별도 chore PR.

---

## 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:----:|
| `Projects/personas/loom/ontology/layers.py` | `FOUNDER_LOYALTY_BONUS = 0.15` 신규 (line 263 — `GRACE_AFFILIATION_BOOST` 직후 빈 줄에 6줄 블록 추가) | 수정 (+~6 lines) |
| `Projects/personas/loom/core/multi_tick_engine.py` | (1) line 70 import 1줄 (`FOUNDER_LOYALTY_BONUS,`), (2) `factions_in_contact` Path 2 블록 (line 1751 직전, ~30 lines 추가), (3) `_compute_affiliation_tick` founder loyalty 분기 (line 1280 직후, ~14 lines 추가) | 수정 (+~45 lines) |
| `Projects/personas/loom/Tools/scripts/verify_phase17_case_c_diagnosis.py` | EXPECT 값 갱신 (`_compute_affiliation_tick`: 60 → 75, `factions_in_contact` 신규 limit 60 추가) | 수정 (선택 — verify 스크립트 유지 시) |

**변경 없음 (금지)**:

- `Projects/personas/loom/core/multi_tick_engine.py` 내:
  - `_uprising_trigger` (line 2001~2061) 본체 로직
  - `_emit_uprising` (line 2063~) 본체 로직
  - `_respawn_faction_tick` (line 1332~1508) 본체 로직 (이미 SPEC-V2 결과 반영됨)
  - `_pick_seed_group` (line 1528~1563) 본체 로직
  - `_change_persona_faction`, FactionChangeSource enum
  - `_project_faction_tick` (HYSTERESIS 사용 — 무수정)
- `Projects/personas/loom/ontology/layers.py` 안전 전제 5종 (line 226~262 영역의 기존 값들 — `MINORITY_PERSISTENCE_BOOST = 0.20` 포함 SPEC-V2 결과 보존).
- `Projects/personas/loom/brain/**` 전체 (SNN 본체).
- 회귀 테스트 7종 (`test_economy.py`, `test_governance.py`, `test_class_promotion.py`, `test_nomos.py`, `test_phase17_faction_handoff_contract.py`, `test_phase14b_snn_integration.py`, `test_phase17_faction_stage3.py`).
- Charter / spec / closure 문서 (별도 closure 보고서는 신규 작성).

---

## 검증

### 1. 기계 검증 (필수, 순서 고정)

```bash
cd Projects/personas/loom

# (a) 컴파일
py -m py_compile ontology/layers.py
py -m py_compile core/multi_tick_engine.py
py -m py_compile ontology/__init__.py

# (b) 회귀 테스트 7종 — 모두 PASS 필요
py test_economy.py
py test_governance.py
py test_class_promotion.py
py test_nomos.py
py test_phase17_faction_handoff_contract.py
py test_phase14b_snn_integration.py
py test_phase17_faction_stage3.py
```

**Hard 기준**: 7/7 PASS. 1건이라도 FAIL 시 spec FAIL — 본 spec 적용 즉시 rollback.

### 2. AST 본문 길이 검증 (`Tools/scripts/verify_phase17_case_c_diagnosis.py`)

기존 EXPECT 표 갱신 (line 8~13):

```python
EXPECT = {
    "_compute_affiliation_tick": 75,    # 60 → 75 (P2 founder loyalty 분기 +14 lines, 여유 +1)
    "_uprising_trigger": 50,             # 무수정
    "_respawn_faction_tick": 155,        # 무수정 (SPEC-V2 결과 보존)
    "_change_persona_faction": 40,       # 무수정
    "factions_in_contact": 60,           # 신규 (Path 2 추가 후 본체 ~50 lines, 여유 +10)
}
```

검증 명령:

```bash
cd Projects/personas/loom
py Tools/scripts/verify_phase17_case_c_diagnosis.py
# 기대 출력: "OK"
```

**Hard 기준**: exit 0 + "OK" 출력. 한 메서드라도 EXPECT 초과 시 spec FAIL — 과도한 변경 차단.

### 3. 자연 측정 (5000틱 × 3 seed)

```bash
cd Projects/personas/loom
py observe_phase17_emergence.py \
  --label phi3-case-c-contact-persistence \
  --seeds 7,13,42 \
  --ticks 5000
```

산출 위치: `data/phase17_probe_phi3-case-c-contact-persistence/seed-{7,13,42}/`.

**Hard 기준** (위반 시 spec FAIL — rollback 발동):
- `acceptance #2 grievance_pairs_end >= 1` PASS 빈도 SPEC-V2 (2/3) 대비 같거나 향상 — 회귀 금지.
- `contact_pairs_end >= 1` 빈도 1/3 이상 (SPEC-V2 0/3 → 본 spec 최소 1/3 — Path 2 활성 입증).
- 회귀 가드: `uprising_event >= 1` 3/3 PASS 유지 (SPEC-V2 와 동일).
- 회귀 가드: `dom_share_end >= 0.50` 3/3 PASS 유지.

**Soft 기준** (관찰용 — closure 보고서에 데이터 기록, 위반해도 spec FAIL 아님):
- `contact_via_persona_relationship` event 누적 카운트 seed 별 >= 100 (5000틱 동안 자연 발생 확인).
- `founder_loyalty_applied` event 누적 카운트 seed 별 >= 50 (respawn 발화 후 grace 기간 활성 확인).
- `uprising_skip_no_contact` 빈도 SPEC-V2 (99/158/78) 대비 감소 (P1 효과 측정).
- `active_factions_end >= 2` 빈도 1/3 이상 (P2 효과 측정).

**판정 매트릭스** (Hard 결과별):

| acceptance #2 | contact_pairs_end | 판정 |
|:-:|:-:|:-:|
| 3/3 PASS | 3/3 | COMPLETE |
| 3/3 PASS | 1~2/3 | COMPLETE_PARTIAL_CONTACT |
| 2/3 PASS | 1+/3 | PARTIAL_PROGRESS (SPEC-V2 동등 + contact 회복) |
| 2/3 PASS | 0/3 | INCONCLUSIVE (P1 무효 — closure 에 진단) |
| 1/3 PASS | any | REGRESSION → rollback |
| 0/3 PASS | any | CRITICAL_REGRESSION → 즉시 rollback |

### 4. 안티패턴 자기 점검 (필수, 12종)

closure 보고서에 모두 명시:

| # | 안티패턴 | 본 spec 회피 근거 |
|---|----------|------------------|
| 1 | top-down 임계 강제 | DIAGNOSIS 데이터 + SPEC-V2 PARTIAL_PROGRESS 사슬 후속 — lever 결정·강도 모두 데이터 정당화 |
| 2 | sticky contact | `factions_in_contact` 매 호출 자연 재계산. 캐시·persistence 없음 |
| 3 | floor contact | `contact_pairs >= 1` 인공 보장 없음. trust 자연 진화에만 의존 |
| 4 | artificial trust propagation | `relationship.trust` 직접 변경 없음. 가산 score 만 추가 |
| 5 | acceptance 우회 | `grievance_pairs_end` 직접 조작 없음. mechanism 본문 무수정 |
| 6 | 새 source enum | FactionChangeSource 4종 무수정 |
| 7 | score 곱셈 우회 | P2 founder loyalty `score += FOUNDER_LOYALTY_BONUS` 가산식. THETA_JOIN 우회 차단 |
| 8 | 안전 전제 변경 | HYSTERESIS=2, FOUNDER_RESPAWN_*, COMMIT_EVERY=48, MAX_MEMBERS=2 무수정 |
| 9 | mechanism 본문 직접 변경 | `_uprising_trigger`, `_emit_uprising`, `_respawn_faction_tick` 무수정. `factions_in_contact` 만 path 추가 |
| 10 | 자가 튜닝 | 본 spec 고정값 `FOUNDER_LOYALTY_BONUS = 0.15`, `trust >= 0.4`. 실패 시 자가 조정 금지 |
| 11 | brain 본체 변경 | `brain/**` 무수정 |
| 12 | 거짓 PASS | acceptance 변경 없음. 자연 측정 데이터로만 효과 입증. PARTIAL/NO_PROGRESS 가능성 인정 |

---

## Rollback

### 즉시 롤백 명령

```bash
cd Projects/personas/loom

# (1) layers.py: FOUNDER_LOYALTY_BONUS = 0.15 라인 삭제 (line 263 근처)
# (2) __init__.py: FOUNDER_LOYALTY_BONUS export 삭제 (조건부)
# (3) multi_tick_engine.py:
#     - factions_in_contact 의 Path 2 블록 (line ~1751 직전 추가분) 삭제 — Path 1 만 유지
#     - _compute_affiliation_tick 의 founder loyalty 분기 (line ~1281 직전 추가분) 삭제
#     - import 에서 FOUNDER_LOYALTY_BONUS 제거

# 검증
py -m py_compile ontology/layers.py core/multi_tick_engine.py
py test_phase17_faction_handoff_contract.py
py test_phase17_faction_stage3.py
```

**데이터 영향**: 없음 (인메모리 시뮬레이션, persistent state 없음).

**부분 롤백 옵션**:
- P1 만 롤백: `factions_in_contact` Path 2 삭제, P2 founder loyalty 유지.
- P2 만 롤백: P2 분기 삭제, P1 Path 2 유지.

---

## 안티패턴 #2 정당화 데이터 사슬 (LOOM-DIRECTION.md)

### 데이터 흐름 7단계

1. **DIAGNOSIS 자연 측정**: contact_pairs_end = 0/0/0, absorbed_by_end = 2/1/1 → 두 단계 붕괴 식별.
2. **SPEC-V2 자연 측정**: BOOST 0.15→0.20 단일 lever PARTIAL_PROGRESS (1/3 → 2/3). seed-13 trajectory 동결 → 단일 lever 한계 확인.
3. **차원 전환 결정**: 진단 보고서 P1 (Contact) + P2 (Persistence) 통합 — 두 자연 메커니즘 추가가 단일 임계 조정보다 본질적 회복 경로.
4. **메커니즘 설계**:
   - P1: trust >= 0.4 임계는 `_pick_seed_group` 기존 임계와 정합 (별개 임계 도입 금지).
   - P2: 0.15 = W_LINEAGE(0.2) 와 GRACE_AFFILIATION_BOOST(0.12) 사이 — 자연 위계.
5. **자연 측정 5000틱 × 3 seed**: 본 spec 적용 후 PASS 빈도 측정.
6. **anti-pattern 12종 자기 점검**: 모든 항목 회피 근거 명시.
7. **종합 판정**: 데이터 기반 PASS/PARTIAL/NO_PROGRESS 인정. 거짓 PASS 패턴 잠복 차단.

### 검증 사슬

- ✅ 자연 측정 데이터 근거 (DIAGNOSIS + SPEC-V2 closure-v2)
- ✅ 회귀 7종 + 안전 전제 5종 무수정 (보존 전제)
- ✅ chain.json 카운트 비교 (양적 근거 — `contact_via_persona_relationship`, `founder_loyalty_applied`)
- ✅ "This tells us:" 해석 동반 (Rule 14)
- ✅ 안티패턴 12종 자기 점검 (top-down 회피 입증)

---

## 다음 단계 (사용자 결정 영역)

| 옵션 | 내용 | 상태 |
|:----:|------|:----:|
| (a) | 본 spec 채택 → /spec-review → 구현 | 권고 ✅ |
| (b) | spec 추가 조정 — 임계값·텔레메트리 형식 등 | 검토 가능 |
| (c) | spec 거부 → 진단 P3/P4 (Affiliation Pressure / Resonance Bridge) 으로 전환 | 차순위 |
| (d) | Phase 14B-C SNN 게이트 axis 전환 (별도 진행 — 한계 대응 전제 D) | 별도 진행 |

**spec 작성자 권고**: **(a) 우선**. SPEC-V2 PARTIAL_PROGRESS 사슬에서 식별된 단일 lever 한계 (seed-13 trajectory 동결) 의 자연 회복 경로는 두 메커니즘 (P1 contact 회복 + P2 founder 지속) 의 결합. 본 spec 은 두 축을 안전 전제 5종 무수정 + mechanism 본문 무수정 하에 설계.

---

## Evidence 위치 (구현 완료 후 갱신 예정)

- 본 spec: `PHASE-17-CASE-C-CONTACT-PERSISTENCE-SPEC.md`
- 선행 진단: `PHASE-17-CASE-C-DIAGNOSIS-REPORT.md`
- 선행 spec: `PHASE-17-CASE-C-P1-P2-SPEC-V2.md` (closure-v2)
- 자연 측정 (구현 후): `data/phase17_probe_phi3-case-c-contact-persistence/seed-{7,13,42}/`
- 회귀 7종 (구현 후): 메인 세션 background bash
- closure 보고서 (구현 후): `PHASE-17-CASE-C-CONTACT-PERSISTENCE-CLOSURE.md`

---

## 자체 검증 체크리스트 (spec 작성자)

- [x] 메타 (긴급도/선행/유형/migration/의존) 포함
- [x] 배경 1-3문장 (DIAGNOSIS 두 단계 붕괴 + SPEC-V2 한계 식별)
- [x] [필수/선택/금지] 태그
- [x] 변경 파일 표 + "변경 없음" 명시
- [x] 기계 검증 (py_compile + 회귀 7종)
- [x] 자연 측정 acceptance 기준 (Hard + Soft)
- [x] Rollback 절차 + 부분 롤백 옵션
- [x] 안티패턴 12종 자기 점검 표
- [x] 데이터 사슬 7단계 명시
- [x] 사용자 결정 영역 4 옵션
- [x] 모호 표현 없음 (`적절히`, `깔끔하게` 등 부재)
- [x] 코드 블록 직접 인용 (factions_in_contact, founder_loyalty 분기 — 구현자가 그대로 복사 가능)
- [x] 임계값 정당화 (0.15 = W_LINEAGE 와 GRACE_AFFILIATION_BOOST 사이, 0.4 = `_pick_seed_group` 정합)
