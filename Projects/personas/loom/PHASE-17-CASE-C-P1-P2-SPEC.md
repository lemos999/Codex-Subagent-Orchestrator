# Phase 17 Φ-3 — Case C P1+P2 통합 패치 지시서

> 긴급도: 높음 (Φ-3 closure 봉쇄 해제 + Φ-4 진입 차단 해제)
> 선행 조건: Φ-3 hotfix v1 closure (5a08998), Phase 14 grievance resonance 보강 (1e9085d)
> 작업 유형: 버그 수정 + 기능 보강 (혼합 — 구조적 단절 메커니즘 복원)
> DB migration: 없음
> 외부 의존: 없음

---

## 배경

### 진단 (PHASE-17-CASE-C-DIAGNOSIS-REPORT.md 기반)

Case-C `grievance_pairs_end = 0/0/0` (3 seed × 5000틱 전부 FAIL)의 root cause는 단일 원인이 아닌 **2 단계 붕괴**:

1. **contact graph가 0쌍으로 수렴** (`active_factions_end = 1` 3/3 seed)
   - `factions_in_contact(radius=1)` = 빈 list
   - `_uprising_trigger` (multi_tick_engine.py:1925-1934)에서 `fid_in_contact = False` → `uprising_skip_no_contact` 이벤트 기록 후 continue → 봉기는 발화되지만 `_emit_uprising` 호출 0건
   - 결과: `_change_persona_faction(source="conflict")` 호출 site = 0 (loom-full-coherence-audit R7 MAJOR-2 finding과 일치)

2. **respawn fallback founder가 affiliation/drift 흡수 압력으로 즉시 소멸** (H2c PARTIAL PASS)
   - Phase A: `free_residents < 3`로 대부분 차단 (3/3, 1/1, 2/2 attempts)
   - Phase B fallback: founder는 생성되지만 (`fallback_founder_created` 3/1/2건) **followers·affiliation 부여 없음** (multi_tick_engine.py:1437-1452)
   - 결과: founder 단독으로 다음 commit cycle 진입 → 자기 territory 거주민 다수가 dominant faction으로 affiliation kernel 점수 누적 → founder 흡수
   - `RESPAWN_GRACE_TICKS=200` drift 면역은 존재하나, **affiliation 신규 가입 차단은 없음** → minority가 멤버를 모으기 전에 founder 자체가 흡수 압력 받음

### loom 3계층 목표 정렬

- **궁극 목적**: 자율 사회 자연 발생. Top-down 선언 금지.
- **Phase 17 목적**: Φ-3 갈등 자연 발생 → Φ-4 Nation 진입 재료 생성.
- **현재 작업의 고유 역할**: Case-C가 가로막은 메커니즘 단절 1점을 자연 흐름으로 복원. mechanism 본문 추가 최소화, acceptance 사후 변경 금지, sticky/floor 금지.

### 본 spec의 단일 책임

**4축 동시 finding 1개의 root cause를 자연 흐름으로 해결한다**:

| 축 | finding |
|---|---|
| B 수평 인과 | Φ-4 진입 차단 (Case C #2 FAIL) |
| E 안티패턴 | skip-when-zero 회피 흔적 (`test_phi3_branch_lineage_chain`) |
| F-1 brain substrate | `_snn_uprising_signal_active`가 trigger 통과 못함 |
| G 상호작용 | `conflict` source 호출 site 0 (메커니즘 연결 고리) |

P1 (Contact Graph Recovery) + P2 (Respawn Founder Persistence) 두 축을 통합 1개 spec으로 해결.

### 인과 사슬 증명 (P1+P2 → contact graph 회복 → grievance pair)

**현재 (collapse) 상태**:
- `active_factions_end = 1` (3/3 seed). 단일 dominant faction이 모든 territory 점유 추세.
- `_pick_uprising_target` (multi_tick_engine.py:1833-1859) 의 contacts 빈 list → `_uprising_trigger` (1925-1934)의 `fid_in_contact = False` → `uprising_skip_no_contact` 이벤트만 기록 → `_emit_uprising` 호출 0건.
- 결과: `_change_persona_faction(source="conflict")` 호출 site 0.

**P1+P2 적용 후 인과 사슬**:

1. **respawn → minority faction 복수 멤버 출범 (P1)**:
   - `_respawn_faction_tick` Phase A·B 어디든 founder가 만들어지면 즉시 `_pick_seed_group()`이 같은 territory T₁ 거주자 중 trust ≥ 0.4 통과자 최대 2명을 동시 가입시킴.
   - 신생 faction A는 founder 1명이 아니라 **2-3명 minority**로 출범.

2. **grace 200틱 동안 흡수 면역 (P2)**:
   - faction A의 멤버는 `_compute_affiliation_tick`에서 same-territory 가산 + W_LINEAGE 가산 + GRACE_AFFILIATION_BOOST(0.12) 합산.
   - dominant faction B의 absorption pressure(W_TRUST·trust_density 등) 대비 신생 쪽이 동일 territory 거주자에게 **자연 우위**.
   - 결과: faction A 멤버 일부가 grace 기간 200틱 동안 잔존.

3. **contact graph 형성 (factionRef 변경 조건 + LandCell 인접 의존)**:
   - `factions_in_contact(radius=1)` (multi_tick_engine.py:1644~1661)은 페르소나 멤버십이 아닌 **`territory.factionRef`** 기반으로 인접 territory 간 서로 다른 factionRef 쌍을 검출.
   - `_project_faction_tick` (line 1506~1538, 24틱마다 갱신)이 T₁의 `factionRef`를 신생 faction A로 변경하려면 **Φ-2 Charter §Operating Loop의 자연 안정성 조건**(`FACTION_HYSTERESIS = 2`, layers.py:276)을 충족해야 함:

     ```
     T₁ 내 faction A 멤버 수 − T₁ 내 직전 dominant faction 멤버 수 ≥ FACTION_HYSTERESIS(2)
     ```

   - **HYSTERESIS는 Φ-2 Charter가 정의한 "24/48틱 double-buffer + 히스테리시스" 자연 안정성 조건이며, P1의 목표는 이 조건을 "우회"가 아닌 "충족"하는 것.** 자연 발화는 자연 안정성 조건 위에서만 일어난다 (LOOM-DIRECTION §2.4 무파괴 보장).
   - P1 seed group이 founder 1 + seed 최대 2 = 3명을 동시 가입시키면, T₁의 dominant faction B 거주자가 ≤ 0명일 때(빈 territory respawn fallback) 자연 충족. 1~3명일 때 boundary case.
   - 조건 충족 시 T₁.factionRef = A, 인접 T₂.factionRef = B(또는 다른 ref) → contact pair (A, B) 형성. LandCell 토폴로지(Φ-1 Land Charter, 2D tile grid)는 territory 경계 인접을 보장하므로 factionRef 차이만 형성되면 contact 자연 발화.

4. **uprising 발화 → grievance pair**:
   - contact 형성 후 `_uprising_trigger` (1925-1934)의 `fid_in_contact = True` → `_emit_uprising` (1963-1997) 정상 호출.
   - 단 `_uprising_trigger`는 `_snn_uprising_signal_active` (line 1819~1831) SNN 게이트도 동시 통과해야 함. SNN anger fire가 자연 임계 미달이면 `uprising_skip_snn_inactive` 경로 (Φ-3 Differentiation Thesis: grievance + SNN + faction 3중 중첩 발화 조건).
   - `_emit_uprising`은 `_change_persona_faction(source="conflict")`로 leader + followers를 새 branch faction으로 이동 + grievance 갱신 → cross-territory grievance pair 형성.

**잔존 위험 (한계 대응 프로토콜 trigger)**:
- **HYSTERESIS 미충족**: T₁ 내 dominant faction B 거주자가 ≥ 4명이면 P1 seed 3명만으론 멤버 수 우위 + HYSTERESIS(2) 미충족 → factionRef 미변경 → contact 미형성. **이는 Φ-2 자연 안정성 조건의 정상 작동이며 위반이 아님** — territory 인구 분포 자연 흐름 재검토 또는 P3 (Affiliation Absorption Pressure) 차원 전환 필요. 단 Stage 3 anti-collapse 상수(`FOUNDER_RESPAWN_*`)는 안전 전제로 변경 금지.
- P1 seed group이 모두 빈 list로 반환되는 경우(territory 거주자 중 trust ≥ 0.4 통과자 부재) → DIAGNOSIS H2a 표면 재발. P3 (Affiliation Absorption Pressure) 차원 전환.
- LandCell 인접도가 낮아 cross-territory radius=1 contact가 형성되지 않는 경우 → P4 (Grievance Resonance Bridge) 차원 전환.
- SNN anger fire가 자연 임계 미달인 경우 → DIAGNOSIS-REPORT의 H3 후보 (SNN 발화 진폭 부족) — 별도 spec 영역.
- 위 모두 **자가 튜닝 금지**. 사용자 에스컬레이션 후 별도 spec 진입.

---

## 작업 범위

### [필수]

1. **P1: Respawn 신규 faction에 동기 가입자(seed group) 자연 부여**
   - Phase A·B fallback에서 founder 생성 직후, 같은 territory 거주민 중 `_pick_seed_group()` 결정성 선정 → 동시 가입.
   - 신규 source enum 추가 금지. 기존 `"birth_founder"` 재사용 (founder 외 가입은 `"affiliation"` 재사용 — 이미 존재).
   - 가입은 affiliation kernel의 자연 측정값(territory + trust)을 통과하는 자만. **floor/sticky/임계 우회 금지.**

2. **P2: Founder grace 기간 affiliation 흡수 면역 채널 신설**
   - 신규 faction의 `grace_until_tick` 동안, faction 멤버는 **다른 faction으로의 drift만** 면역(이미 존재)이 아니라, **affiliation 신규 가입에서 다른 faction으로 흡수되지 않도록** founder_lineage 가중치를 자연 boost.
   - 신규 상수 1개: `GRACE_AFFILIATION_BOOST = 0.12` (W_LINEAGE 0.2의 60% 수준 — 자연 가산 경계 §B-1).
   - `RESPAWN_GRACE_TICKS = 200` 기존 값 무수정.

3. **자연 측정 acceptance #2 통과 (Hard 불변)**
   - seed 7/13/42 × 5000틱:
     - `active_factions_end >= 2` (3/3)
     - `factions_in_contact_end >= 1` (3/3)
     - `_change_persona_faction(source="conflict")` 호출 카운트 >= 1 (3/3) — `event_log` `type="uprising"` ≥ 1로 측정
     - `grievance_pairs_end >= 1` (3/3)

4. **거짓 PASS 안티패턴 차단**
   - 각 acceptance 검증은 **자연 측정**으로만 통과. test 코드에 `if x == 0: skip`, `if x < 1: ...` 패턴 금지.
   - `_emit_uprising` 호출 카운트 vs `event_log type="uprising"` 카운트 == 일관 (uprising 발화 후 follower 0명 기록 금지).

5. **무파괴 9 전부 유지**
   - 기존 Φ-3 acceptance 1·3차 (uprising_event ≥ 1, dom_share ≥ 0.50)는 PASS 유지.
   - Phase 11~16 경제 시스템 본체 무수정.

### [선택]

- P3 / P4 (DIAGNOSIS-REPORT 후순위) 진입은 본 spec 범위 외. Φ-3 closure v2에서 별도 평가.
- minority_boost telemetry의 `min(personas)` 1인분 카운트 제한 (R3 MINOR) 보강은 본 spec 범위 외.

### [금지]

- **신규 `FactionChangeSource` enum 추가 금지**. 4종 freeze (`birth_founder`, `affiliation`, `drift`, `conflict`).
- **AST whitelist `PHASE17_FACTION_SSOT_WRITE` 마커 5라인 변경 금지**. 신규 마커 추가 0건.
- **Phase 11~16 경제 상수 변경 금지**. `MARKET_FEE_SINK_RATIO`, `FOOD_CONSUME_PER_TICK` 등 무수정.
- **brain/** 변경 금지**. SNN 본체·Persona Brain readout 무수정.
- **Phase 17 Stage 3 anti-collapse 상수 변경 금지**: `MINORITY_PERSISTENCE_BOOST=0.15`, `FOUNDER_RESPAWN_EVERY=480`, `FOUNDER_RESPAWN_TARGET_ACTIVE=2`, `RESPAWN_GRACE_TICKS=200` 모두 무수정.
- **`FACTION_HYSTERESIS = 2` 변경 금지** (layers.py:276). Φ-2 Charter §Operating Loop의 24/48틱 double-buffer 자연 안정성 조건. P1 목표는 이 조건의 "우회"가 아닌 "충족"이며, HYSTERESIS 약화는 LOOM-DIRECTION §2.4 무파괴 9 보장 위반.
- **Φ-3 신규 상수 5종 변경 금지**: `THETA_UPRISING=0.40`, `UPRISING_CHECK_INTERVAL=48`, `UPRISING_GRIEVANCE_DECAY=0.5`, `UPRISING_FOLLOWER_MAX=2`, `SNN_ANGER_FIRE_THRESHOLD=0.6` 무수정. 검증 단계에서 데이터 부족 시에도 자가 튜닝 금지 — 사용자 에스컬레이션.
- **Phase 14 grievance 상수 변경 금지**: `GRIEVANCE_PROPAGATE_TRUST_MIN=0.6`, `GRIEVANCE_DONOR_MIN=0.5` 무수정.
- **24틱 자연 재계산 사이클 변경 금지**. 신규 시간축 도입 금지.
- **acceptance 기준 사후 변경 금지** (역공학 안티패턴 차단).
- **sticky / floor / artificial propagation 금지** (CASE-C-DIAGNOSIS §P1 명시 금지 사항).
- **인라인 `sorted(self.personas)[0]` 호출 금지**. min/max 외부 1회 계산 후 재사용.
- **`_change_persona_faction()` 외 경로로 `persona.faction` 변경 금지**. AST whitelist 통과.

---

## 구체 사양

### Section A — P1 Respawn Seed Group

#### A-1. 신규 helper `_pick_seed_group()` 추가

**위치**: `Projects/personas/loom/core/multi_tick_engine.py`, `_pick_founder` 메서드 직후 (현재 line 1457~1473 다음).

**시그니처 및 동작**:

```python
def _pick_seed_group(
    self,
    *,
    founder_pid: str,
    candidates: list[Persona],
    territory: Territory,
    max_size: int,
) -> list[str]:
    """Founder와 함께 신규 faction에 동기 가입할 seed 멤버 결정.

    자연 측정 기반 선정:
    - founder와의 relationship trust >= 0.4 (community 임계와 정합)
    - 같은 territory(territory.id) 거주 (helper 단독 안전성을 위해 내부 검증)
    - persona.faction is None 또는 faction_cooldown == 0
    - founder 본인 제외

    tie-break: trust 내림차순(음수 트릭으로 단일 sort), sorted(pid).
    반환 길이: 0 ~ max_size (자연 부족 시 적게 반환, 인공 채움 금지).
    """
    if max_size <= 0:
        return []
    pool = [
        persona for persona in candidates
        if persona.id != founder_pid
        and persona.id in self.inners
        and persona.territory == territory.id  # helper 단독 안전성 검증
        and (persona.faction is None or persona.faction_cooldown == 0)
    ]
    scored: list[tuple[float, str]] = []
    for persona in pool:
        trust = float(self._get_relationship_trust(founder_pid, persona.id))
        if trust < 0.4:
            continue
        scored.append((-trust, persona.id))  # trust 내림차순 + pid 오름차순 tie-break
    scored.sort()
    return [pid for _, pid in scored[:max_size]]
```

**자연성 검증**:
- `0.4` 임계는 `_get_community_members(min_trust=0.4)` 와 동일 — 이미 community 응결의 자연 임계로 통용 (`_get_community_members` 정의 line 858, default min_trust=0.4).
- `max_size`는 `min(2, free_residents - 1)` 형태로 호출자가 결정. 신규 상수 0건.
- pool이 비면 빈 list 반환. **인공 fallback 금지**.
- `territory.id` 인자 검증을 helper 내부에 둠 → 호출자 필터링 누락 시에도 안전 (방어적 설계).

#### A-2. `_respawn_faction_tick` Phase A 수정

**위치**: `multi_tick_engine.py:1370-1400` 영역.

**수정 지점** (line 1393~1395 직후, `active_count += 1` 이전):

기존:
```python
self.factions[faction.id] = faction
self._change_persona_faction(founder.id, faction.id, source="birth_founder")
self.personas[founder.id].faction_cooldown = FOUNDER_RESPAWN_EVERY  # noqa: PHASE17_FACTION_SSOT_WRITE
active_count += 1
```

변경 후:
```python
self.factions[faction.id] = faction
self._change_persona_faction(founder.id, faction.id, source="birth_founder")
self.personas[founder.id].faction_cooldown = FOUNDER_RESPAWN_EVERY  # noqa: PHASE17_FACTION_SSOT_WRITE
# P1: seed group 자연 가입. free_residents 풀에서 founder 제외 후 최대 2명.
seed_group = self._pick_seed_group(
    founder_pid=founder.id,
    candidates=free_residents,
    territory=territory,
    max_size=min(2, len(free_residents) - 1),
)
for seed_pid in seed_group:
    self._change_persona_faction(seed_pid, faction.id, source="affiliation")
    # P1+P2 결합: seed 멤버는 grace 기간 동안 commit 사이클의 drift 후보가 되지 않도록
    # FACTION_COMMIT_EVERY 1 사이클(48틱) cooldown 부여. grace 200틱 보호와 정합.
    # Stage 3 anti-collapse 상수 무수정 (FACTION_COMMIT_EVERY는 layers.py 기존값 재사용).
    self.personas[seed_pid].faction_cooldown = FACTION_COMMIT_EVERY  # noqa: PHASE17_FACTION_SSOT_WRITE
self.event_log.append({
    "type": "respawn_seed_group",
    "tick": self.time.tick,
    "phase": "a",
    "faction_id": faction.id,
    "founder_pid": founder.id,
    "seed_pids": list(seed_group),
})
active_count += 1
```

#### A-3. `_respawn_faction_tick` Phase B 수정

**위치**: `multi_tick_engine.py:1402-1455` 영역.

**수정 지점** (line 1449~1452 직후):

기존:
```python
self.factions[faction.id] = faction
self._change_persona_faction(founder.id, faction.id, source="birth_founder")
self.event_log.append({"type": "respawn_fallback_founder_created", ...})
self.personas[founder.id].faction_cooldown = FOUNDER_RESPAWN_EVERY  # noqa: PHASE17_FACTION_SSOT_WRITE
active_count += 1
```

변경 후:
```python
self.factions[faction.id] = faction
self._change_persona_faction(founder.id, faction.id, source="birth_founder")
self.event_log.append({"type": "respawn_fallback_founder_created", "tick": self.time.tick, "founder_pid": founder.id, "faction_id": faction.id, "territory_id": territory.id})
self.personas[founder.id].faction_cooldown = FOUNDER_RESPAWN_EVERY  # noqa: PHASE17_FACTION_SSOT_WRITE
# P1: seed group 자연 가입. residents 풀에서 founder 제외 후 최대 2명.
seed_group = self._pick_seed_group(
    founder_pid=founder.id,
    candidates=residents,
    territory=territory,
    max_size=min(2, len(residents) - 1),
)
for seed_pid in seed_group:
    self._change_persona_faction(seed_pid, faction.id, source="affiliation")
    # P1+P2 결합: seed 멤버는 grace 기간 동안 drift 보호 (A-2와 동일 처리).
    self.personas[seed_pid].faction_cooldown = FACTION_COMMIT_EVERY  # noqa: PHASE17_FACTION_SSOT_WRITE
self.event_log.append({
    "type": "respawn_seed_group",
    "tick": self.time.tick,
    "phase": "b",
    "faction_id": faction.id,
    "founder_pid": founder.id,
    "seed_pids": list(seed_group),
})
active_count += 1
```

#### A-4. 자연성 보존

- seed group 가입은 trust ≥ 0.4 자연 임계 통과한 멤버만. 빈 group은 그대로 빈 group으로 결과(자연 부족 인정).
- `source="affiliation"`은 기존 enum 재사용. 4종 freeze 유지.
- seed 멤버는 founder와 동일 territory 거주자만 → `factions_in_contact` 그래프 형성에 자연 기여.
- **seed 멤버 cooldown = `FACTION_COMMIT_EVERY` 부여**: P2 grace 200틱 의도(trust 형성 시간 확보)와 P1 seed 가입의 결합 정합. cooldown 0이면 다음 commit 사이클(48틱)에서 drift 후보 → P2 grace 효과 무력화 위험. cooldown은 신규 상수 도입이 아닌 layers.py 기존값(`FACTION_COMMIT_EVERY = 48`) 재사용. founder의 `FOUNDER_RESPAWN_EVERY` 보호와 다른 차원(founder는 respawn 차단, seed는 commit drift 차단).

### Section B — P2 Founder Grace Affiliation Boost

#### B-1. 신규 상수 1개

**위치**: `Projects/personas/loom/ontology/layers.py`, line 257~258 (현재 GRIEVANCE_DONOR_MIN 다음).

```python
# ── Phase 17 Φ-3 Case-C P2: Founder grace affiliation 흡수 면역 (2026-04-30) ──
# 근거: respawn fallback founder의 즉시 흡수 (DIAGNOSIS H2c) 완화.
# grace_until_tick 동안 founder_lineage 멤버에게 자연 boost. RESPAWN_GRACE_TICKS=200 기존값 무수정.
GRACE_AFFILIATION_BOOST = 0.12       # W_LINEAGE(0.2)의 60% 수준. THETA_JOIN 우회 금지값.
```

**근거 — bootstrapping 모순 자연 해결**:

신생 faction은 trust 네트워크가 형성되기 전에는 측정될 수 없다(닭과 달걀 구조). dominant faction은 누적된 W_TRUST 기반 affiliation 가산 우위로 신생 faction 멤버를 즉시 흡수 → 신생 faction은 trust를 형성할 시간 자체를 갖지 못하고 소멸 (DIAGNOSIS H2c).

`RESPAWN_GRACE_TICKS = 200`은 신생 faction이 자신만의 trust 네트워크를 형성할 **물리적 시간**이며, `GRACE_AFFILIATION_BOOST`는 그 시간 동안 trust 형성이 자연 진행될 수 있도록 dominant faction의 누적 trust 가산을 일시 중화하는 자연 가산이다. boost는 임의 도입 magic number가 아니라 bootstrapping 모순의 자연 해결책 — grace 종료 시점에는 신생 faction이 자체 trust 네트워크를 갖추고 있어 boost 없이 자연 score 비교만으로 잔존 여부 결정.

**임계 정당화**:
- `W_LINEAGE = 0.2` (Stage 6 H-lite founder lineage 가산)의 60% 수준 — 강도 제한.
- `THETA_JOIN`은 affiliation 임계로 별도 존재. boost는 임계 직접 우회가 아니라 같은 territory 거주자가 dominant faction과 신생 faction 사이 score 비교에서 신생 쪽이 인근 trust 정합 시 자연 우위에 서게 함.
- grace 종료 후 boost 0 → 자연 흡수 압력 정상 적용 (top-down 영구 보호 금지).

**임계 우회와 자연 가산의 경계 (4 조건 모두 충족 시 자연 가산)**:

1. **same-territory 한정**: boost는 `_same_territory(persona, fid) > 0.5` 통과 시에만 적용. cross-territory 거주자에는 적용 0 (territory 자연 인접 가산과 정합).
2. **grace 종료 정확히 0**: `tick >= faction.grace_until_tick`이면 boost = 0. 잔존 보호 없음.
3. **절대 우위 형성 불가**: score 이론 최대 ≈ 1.5 (W_TERRITORY_SAME 0.5 + W_TRUST 1.0 + W_PROXIMITY 1.0)에서 0.12는 약 8% 가산. dominant faction이 W_TERRITORY_SAME + W_TRUST 우위인 경우 boost로 역전 불가 = 자연 score 비교 보존.
4. **가산만 사용**: `score += GRACE_AFFILIATION_BOOST` (sum). `score *= multiplier` 형태 금지 (스케일 변화는 임계 우회 효과 유발).

**검증 hook**:
- 결정성 검증 단계에서 grace 종료 직후 (`created_tick + RESPAWN_GRACE_TICKS`) snapshot의 affiliation_scores를 확인. boost가 정확히 0으로 사라졌는지 확인.
- `_commit_faction_tick` (line 1276~)에서 commit 결정에 boost가 영향을 주는 경우, **boost로만 commit이 통과**한 case가 있는지 telemetry 측정 (옵션, 보강 단계).

#### B-2. `_compute_affiliation_tick` grace boost 분기 추가

**위치 확정**: `multi_tick_engine.py:1217~1274` (`_compute_affiliation_tick` 본문). 특히 W_LINEAGE 가산 분기(line 1261~1269) **직후**에 신규 분기 1개 추가.

**기존 코드 (line 1261~1270, 변경 전)**:
```python
                # Stage 6 H-lite: founder lineage identity affinity (2026-04-26)
                if W_LINEAGE > 0 and persona.faction:
                    cur_faction = self.factions.get(persona.faction)
                    cand_faction = self.factions.get(fid)
                    if cur_faction and cand_faction:
                        lineage_a = set(cur_faction.founder_lineage) | {cur_faction.founder_pid}
                        lineage_b = set(cand_faction.founder_lineage) | {cand_faction.founder_pid}
                        overlap = len(lineage_a & lineage_b) / max(len(lineage_a), len(lineage_b), 1)
                        score += W_LINEAGE * overlap
                scored[fid] = DECAY * prev_scores.get(fid, 0.0) + score
```

**변경 후 (W_LINEAGE 분기 직후, line 1270 `scored[fid] = ...` 직전 삽입)**:
```python
                # Stage 6 H-lite: founder lineage identity affinity (2026-04-26)
                if W_LINEAGE > 0 and persona.faction:
                    cur_faction = self.factions.get(persona.faction)
                    cand_faction = self.factions.get(fid)
                    if cur_faction and cand_faction:
                        lineage_a = set(cur_faction.founder_lineage) | {cur_faction.founder_pid}
                        lineage_b = set(cand_faction.founder_lineage) | {cand_faction.founder_pid}
                        overlap = len(lineage_a & lineage_b) / max(len(lineage_a), len(lineage_b), 1)
                        score += W_LINEAGE * overlap
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
                scored[fid] = DECAY * prev_scores.get(fid, 0.0) + score
```

**구현 주의사항**:
- `cand_faction_for_grace`는 W_LINEAGE 분기의 `cand_faction`과 별도 변수 사용. W_LINEAGE 분기는 `persona.faction is not None` 조건이지만 grace boost는 그 조건 무관 (faction 미가입 자도 신생 faction에 가입 후보).
- `self._same_territory(persona, fid)` (line 1124 정의)는 affiliation kernel 내부에서 이미 line 1233·1252에서 동일 패턴으로 사용 — 일관성 보존.
- `cand_faction_for_grace.grace_until_tick`은 `Faction` dataclass 기존 필드 (1389, 1445, 1897 라인에서 set, 정의는 layers.py Faction 본체). 신규 필드 추가 0건.
- `import` 추가: `layers.py`에서 `GRACE_AFFILIATION_BOOST` import (기존 layers import 라인에 추가).

**금지 사항 재확인** (§B-1 4 조건 위반 차단):
- `score *= boost_multiplier` 금지 (스케일 변화 = 임계 우회).
- `if grace_until_tick > self.time.tick + EXTRA` 형태 grace 연장 금지.
- boost를 cross-territory persona에게 적용 금지 (`_same_territory > 0.5` 누락 = 자연 가산 위반).

#### B-3. 결정성 보장

- `grace_until_tick`은 `created_tick + RESPAWN_GRACE_TICKS` 정합. 기존 라인 (multi_tick_engine.py:1389, 1445, 1897) 무수정.
- boost 적용 조건은 tick·faction id·persona territory만 의존 (RNG 사용 없음).

### Section C — Telemetry (자연 측정 가시화)

#### C-1. 신규 metrics 키 (`SUMMARY.md` Primary Acceptance 표 보강용)

`observe_phase17_emergence.py` 또는 probe 스크립트가 5000틱 측정 시 다음을 집계 (event_log 기반, 후처리):

**[필수] (P1+P2 효과 가시화 + HYSTERESIS 충족 측정)**:
```
respawn_seed_group_total              # respawn_seed_group 이벤트 총수
respawn_seed_group_phase_a            # phase=="a" 만
respawn_seed_group_phase_b            # phase=="b" 만
seed_member_persisted_count           # 5000틱 종료 시 신생 faction에 남은 seed 멤버 수
conflict_source_change_count          # _change_persona_faction(source="conflict") 호출 카운트 = event_log 'uprising' 항목의 1+followers 합
factionRef_changed_by_respawn_count   # respawn 후 24~96틱 이내 _project_faction_tick에서
                                      # territory.factionRef가 신생 faction id로 변경된 횟수.
                                      # HYSTERESIS(2) 충족 여부의 핵심 측정값.
                                      # 0이면 P1 seed group이 멤버 수 우위에 도달하지 못함 → 잔존 위험 시나리오 진입.
```

**[권장] (Φ-3 Differentiation Thesis 논문 evidence)**:
```
snn_gate_pass_count                   # _snn_uprising_signal_active=True로 통과한 횟수
                                      # (uprising 후보 중 SNN anger fire 자연 임계 통과)
uprising_skip_snn_inactive_count      # SNN 게이트 미통과로 uprising 발화 차단 횟수
                                      # _uprising_trigger 본문 무수정 — 신규 event_log 'uprising_skip_snn_inactive' 추가만으로 측정.
                                      # snn_gate_pass / (snn_gate_pass + skip_snn_inactive) 비율이
                                      # "SNN 창발이 봉기를 결정한다" 논문 claim의 핵심 evidence.
```

`uprising_skip_snn_inactive` 이벤트 emit 위치: `_uprising_trigger` 내 `_snn_uprising_signal_active(...)` 분기에서 False 반환 시 `event_log.append({"type": "uprising_skip_snn_inactive", ...})` 1줄 추가. 본체 로직 변경 0.

**금지 항목**:
- **금지**: 위 metrics가 0이면 acceptance를 통과시키는 분기 추가.
- **금지**: 위 metrics 임계 사후 추가.
- **금지**: `factionRef_changed_by_respawn_count = 0`인데 acceptance #2 PASS — 가능한 자연 경로 없음. PASS 시 HYSTERESIS 충족 외 다른 contact 형성 경로 재현 분석 필요.

### Section D — `_uprising_trigger` 및 `_emit_uprising` 무수정

P1+P2 패치는 contact graph 회복 + founder 지속에 한정. uprising trigger·emit 본체는 무수정.

**근거**: DIAGNOSIS-REPORT §"진짜 Root Cause" — uprising 발화 mechanism 자체는 작동(`13/11/16` 회 발화). 단절은 contact graph 0쌍과 minority 지속성. 두 곳을 자연 보강하면 trigger·emit이 자동으로 통과.

`_snn_uprising_signal_active` (1819~1831), `_pick_uprising_target` (1833~1859), `_uprising_trigger` (1911~1961), `_emit_uprising` (1963~1997) 4 함수 전부 본체 무수정.

---

### Section E — 테스트 자연 측정 강화 (skip-when-zero 차단)

#### E-1. `test_phi3_branch_lineage_chain` 강화

**위치**: `Projects/personas/loom/test_phase17_acceptance.py:447~462`.

**기존 코드 (line 447~462)**:
```python
def test_phi3_branch_lineage_chain():
    """분파 신규 faction의 founder_lineage가 부모 fid 포함."""
    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        branches = [
            e for e in engine.event_log
            if e["type"] == "faction_spawn" and e.get("source") == "uprising_branch"
        ]
        for b in branches:
            new_fid = b["fid"]
            parent_fid = b["parent_fid"]
            new_faction = engine.factions[new_fid]
            assert parent_fid in new_faction.founder_lineage, (
                f"분파 {new_fid}의 founder_lineage에 부모 {parent_fid} 없음: "
                f"{new_faction.founder_lineage}"
            )
```

**문제 (R5 H2c finding)**:
명시적 `if x == 0: skip` 패턴은 없지만, `branches`가 빈 list이면 inner for-loop 미실행 → 모든 assertion 0건 = **자동 PASS**. 즉 mechanism 단절 시에도 본 테스트는 통과 → 거짓 PASS.

**변경 후**:
```python
def test_phi3_branch_lineage_chain():
    """분파 신규 faction의 founder_lineage가 부모 fid 포함.

    skip-when-zero 차단: 3 seed 합계 branches >= 1을 명시 assertion으로 보장.
    """
    total_branches = 0
    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        branches = [
            e for e in engine.event_log
            if e["type"] == "faction_spawn" and e.get("source") == "uprising_branch"
        ]
        total_branches += len(branches)
        for b in branches:
            new_fid = b["fid"]
            parent_fid = b["parent_fid"]
            new_faction = engine.factions[new_fid]
            assert parent_fid in new_faction.founder_lineage, (
                f"분파 {new_fid}의 founder_lineage에 부모 {parent_fid} 없음: "
                f"{new_faction.founder_lineage}"
            )
    assert total_branches >= 1, (
        "3 seed 합계 uprising_branch 0건 = mechanism 단절 (R5 H2c 거짓 PASS 차단)"
    )
```

**자연성 보존**:
- `>= 1` 임계는 3 seed 합. 단일 seed 임계가 아니므로 결정성 측면에서 자연 측정 보존 (특정 seed 운에 의존 ↓).
- 인공 분기 추가 없음. mechanism이 작동하면 자연 통과, 작동 안 하면 자연 fail → "FAIL" 해석 의무 발동.

#### E-2. `test_phi3_grievance_pairs_resonate` 무수정

**위치**: `test_phase17_acceptance.py:360~365`.

**현재 코드** (자연 측정 이미 충족):
```python
def test_phi3_grievance_pairs_resonate():
    """Φ-3 acceptance #2: grievance_pairs_end >= 1 (3/3, cross-territory 자연 응결)."""
    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        pair_count = engine.shared_grievance_pairs_count(min_carriers=2)
        assert pair_count >= 1, f"seed {seed}: grievance_pairs 0쌍 (cross-territory 자연 응결 실패)"
```

**판정**: 무수정. 이미 seed-별 assertion으로 자연 측정 통과 검증 — spec [필수] 3번이 통과하면 자연 PASS, 미통과 시 자연 FAIL → 한계 대응 프로토콜 발동.

#### E-3. 신규 단위 테스트 ([필수])

**위치**: `test_phase17_acceptance.py` 또는 `test_phase17_faction_stage3.py` (신규 단위 테스트 파일 분리도 가능).

**내용**: P1 seed group 기록 자체 검증 + P2 grace 종료 정확성 검증.
```python
def test_respawn_seed_group_emitted():
    """P1: respawn 시 seed_group 이벤트가 자연 발생 (founder만 만들지 않음)."""
    total_seed_events = 0
    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        total_seed_events += sum(
            1 for e in engine.event_log if e["type"] == "respawn_seed_group"
        )
    assert total_seed_events >= 1, (
        "3 seed 합계 respawn_seed_group 이벤트 0건 = P1 미작동"
    )


def test_grace_boost_terminates():
    """P2: grace 종료 시 boost가 정확히 0으로 사라짐 (top-down 보호 차단).

    검증 흐름:
    1. seed=42, ticks=engine 의 첫 respawn_faction 생성 후 grace_until_tick + 5 까지 진행
    2. 신생 faction `fid_new`, 그 lineage의 founder pid `pid_f` 식별
    3. grace 활성 구간 중간 tick `t_mid` 에서 affiliation_scores 스냅샷 1
    4. grace 종료 직후 tick `t_post = grace_until_tick + 1` 에서 스냅샷 2
    5. 스냅샷 1 의 `scored[fid_new]` - (스냅샷 1 의 baseline) ≥ 0.10 (boost 활성)
    6. 스냅샷 2 의 `scored[fid_new]` - (스냅샷 2 의 baseline) < 0.005 (boost 0)

    구현 가이드:
    - micro-simulation 으로 비결정 요소 최소화. 외부 noise 가 0.005 임계 침범 시
      noise 시드를 grace 활성/종료 두 구간 동일 tick offset 으로 고정.
    - W_LINEAGE 자체는 boost 와 독립이어야 하므로 baseline 계산은
      `grace_until_tick = 0` 으로 강제 호출한 _compute_affiliation_tick 결과 사용.
    """
    engine = run_simulation(seed=42, ticks=2_000)
    # founder respawn 이벤트로부터 fid_new, pid_f, grace_until 추출
    respawn_events = [e for e in engine.event_log if e["type"] == "respawn_faction"]
    assert respawn_events, "respawn_faction 이벤트 0건 — P2 검증 전제 실패"
    ev = respawn_events[0]
    fid_new, pid_f, grace_until = ev["faction_id"], ev["founder_pid"], ev["grace_until_tick"]

    t_mid = (ev["tick"] + grace_until) // 2
    t_post = grace_until + 1

    boost_mid = engine.replay_affiliation_score(seed=42, tick=t_mid, pid=pid_f, fid=fid_new) \
              - engine.replay_affiliation_score(seed=42, tick=t_mid, pid=pid_f, fid=fid_new, force_grace_off=True)
    boost_post = engine.replay_affiliation_score(seed=42, tick=t_post, pid=pid_f, fid=fid_new) \
               - engine.replay_affiliation_score(seed=42, tick=t_post, pid=pid_f, fid=fid_new, force_grace_off=True)

    assert boost_mid >= 0.10, f"grace 활성 구간 boost 미달 ({boost_mid:.4f})"
    assert boost_post < 0.005, f"grace 종료 후 boost 잔존 ({boost_post:.4f}) — top-down 보호 의심"
```

**판정**: E-3은 **[필수]**. 거짓 PASS 안티패턴(`grace 종료 후 잔존`) 자기 차단의 핵심 — `test_grace_boost_terminates` 미구현 시 자연 가산 4 조건 중 #2(grace 종료 정확히 0)가 검증 공백 상태로 잔존하여 top-down 보호 잠복 위험.

**구현 보강**: `replay_affiliation_score(seed, tick, pid, fid, force_grace_off=False)` helper 가 없으면 동일 의도의 micro-simulation 으로 대체 가능 (예: 같은 seed 두 번 실행하되 한 쪽에서만 `_compute_affiliation_tick` 호출 직전 `engine.factions[fid_new].grace_until_tick = 0` 강제 설정).

---

## 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/ontology/layers.py` | `GRACE_AFFILIATION_BOOST = 0.12` 상수 추가 (line 258 직후, "하위 호환" 주석 직전) | 추가 |
| `Projects/personas/loom/core/multi_tick_engine.py` | `_pick_seed_group()` 신규 메서드 추가 (`_pick_founder` 직후, line 1473 다음) | 추가 |
| `Projects/personas/loom/core/multi_tick_engine.py` | `_respawn_faction_tick` Phase A (line 1392~1395 직후) + Phase B (line 1448~1452 직후) 두 곳에 seed group 호출 + 이벤트 로그 추가. seed 멤버 각 pid 에 대해 `self.personas[pid].faction_cooldown = FACTION_COMMIT_EVERY` 설정 1줄 (Phase A·B 각 1건, `# noqa: PHASE17_FACTION_SSOT_WRITE` 주석 포함) | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | `_compute_affiliation_tick` (line 1217~1274) 본문에 grace boost 분기 1개 추가 (W_LINEAGE 분기 line 1261~1269 직후, line 1270 `scored[fid]=` 직전) | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | `_uprising_trigger` (line 1911~1961) 내 `_snn_uprising_signal_active(...)` False 분기에 `self.event_log.append({"type": "uprising_skip_snn_inactive", ...})` 1줄 추가 (본체 로직 무수정, telemetry-only) | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | layers import 에 `GRACE_AFFILIATION_BOOST`, `FACTION_COMMIT_EVERY` 추가 | 수정 |
| `Projects/personas/loom/observe_phase17_emergence.py` | §C-1 telemetry [필수] 6종 + [권장] 2종 = 8종 집계 추가 (SUMMARY 표 보강 — `respawn_seed_group_total`, `respawn_seed_group_phase_a`, `respawn_seed_group_phase_b`, `seed_member_persisted_count`, `conflict_source_change_count`, `factionRef_changed_by_respawn_count`, `snn_gate_pass_count`, `uprising_skip_snn_inactive_count`) | 수정 |
| `Projects/personas/loom/test_phase17_acceptance.py` | §E-1: `test_phi3_branch_lineage_chain` (line 447~462) 강화 — `total_branches >= 1` assertion 추가 (R5 H2c 거짓 PASS 차단). §E-2: `test_phi3_grievance_pairs_resonate` (line 360~365) 무수정. §E-3 (선택): 신규 단위 테스트 2종 추가 | 수정 |

**변경 없음 (금지)**:
- `Projects/personas/loom/brain/**` 전체
- `Projects/personas/loom/PHASE-17-FACTION-CHARTER.md` (handoff 계약 본체 — 단 §2 affiliation_scores 위치 갱신은 별도 PR로 분리 권고, 본 spec 범위 외)
- `Projects/personas/loom/PHASE-17-STRUGGLE-CHARTER.md` (Charter 본체 무수정, §6 보류 5종 TBD는 본 spec에서 미해소 — Φ-3 closure v2에서 별도 처리)
- `Projects/personas/loom/PHASE-17-CASE-C-DIAGNOSIS-REPORT.md` (진단 보고서 무수정)
- Phase 11~16 회귀 테스트 (test_economy.py, test_economy_balance.py, test_snn_economy.py, test_governance.py, test_phase12b_perf_npc.py, test_phase15*.py, test_phase16*.py)
- `Projects/personas/loom/test_phase17_faction_handoff_contract.py` (D10 7종 freeze 보존)
- `Projects/personas/loom/test_phase14b_snn_integration.py`
- `Projects/personas/loom/test_phase17_faction_stage3.py`
- `Projects/personas/loom/physis/world.py` (Φ-1 LandCell 본체)

---

## 검증

### 기계 검증 (항상)

1. `cd Projects/personas/loom && py -m py_compile core/multi_tick_engine.py`
2. `cd Projects/personas/loom && py -m py_compile ontology/layers.py`
3. `cd Projects/personas/loom && py -m py_compile observe_phase17_emergence.py`
4. (Python type-check 도구 미설정 시 `mypy`/`ruff` 생략 → 그 사실 명시)

### 회귀 테스트 (무파괴 9 검증)

```bash
cd Projects/personas/loom && py test_phase17_faction_handoff_contract.py   # PASS 12/12 유지
cd Projects/personas/loom && py test_phase14b_snn_integration.py            # PASS 8/8 유지
cd Projects/personas/loom && py test_phase17_faction_stage3.py              # PASS 유지
cd Projects/personas/loom && py test_phase17_acceptance.py                  # acceptance 1·3차 PASS 유지, 2차 PASS 신규
```

기존 회귀 테스트 (직접 실행 또는 보고서 인용 필수):
```bash
cd Projects/personas/loom && py test_economy.py
cd Projects/personas/loom && py test_economy_balance.py
cd Projects/personas/loom && py test_snn_economy.py
cd Projects/personas/loom && py test_governance.py
cd Projects/personas/loom && py test_phase16_public_works.py
cd Projects/personas/loom && py test_class_promotion.py
cd Projects/personas/loom && py test_nomos.py
```

### 자연 측정 acceptance (Hard 불변)

```bash
cd Projects/personas/loom && py observe_phase17_emergence.py \
    --label phi3-case-c-p1p2-natural \
    --seeds 7,13,42 \
    --ticks 5000
```

**기대 결과** (산출 SUMMARY.md):

| 기준 | seed 7 | seed 13 | seed 42 | 결과 |
|---|--:|--:|--:|---|
| `uprising_event_count >= 1` | ≥1 | ≥1 | ≥1 | PASS (기존 PASS 유지) |
| **`grievance_pairs_end >= 1`** | **≥1** | **≥1** | **≥1** | **PASS (신규 — 본 spec 핵심)** |
| `dom_share_end >= 0.50` | ≥0.50 | ≥0.50 | ≥0.50 | PASS (기존 PASS 유지) |
| `active_factions_end >= 2` | ≥2 | ≥2 | ≥2 | PASS (신규) |
| `factions_in_contact_end >= 1` | ≥1 | ≥1 | ≥1 | PASS (신규) |
| `conflict_source_change_count >= 1` | ≥1 | ≥1 | ≥1 | PASS (신규 — `_change_persona_faction(source="conflict")` 호출 site 회복) |
| `population_total_end == population_total_start` | == | == | == | PASS (Φ-3 무사망 보장) |

**자연성 보강 측정**:
- `respawn_seed_group_total >= 1` 3 seed 전부
- `seed_member_persisted_count > 0` 적어도 1 seed (인공 sticky 없는 자연 잔존 측정)

### 결정성 검증 (필수)

```bash
cd Projects/personas/loom && py observe_phase17_emergence.py \
    --label phi3-case-c-p1p2-determinism-1 \
    --seeds 42 --ticks 5000
cd Projects/personas/loom && py observe_phase17_emergence.py \
    --label phi3-case-c-p1p2-determinism-2 \
    --seeds 42 --ticks 5000
diff data/phase17_probe_phi3-case-c-p1p2-determinism-1/seed-42/snapshot_5000.json \
     data/phase17_probe_phi3-case-c-p1p2-determinism-2/seed-42/snapshot_5000.json
# 출력: empty (snapshot 일치)
```

비교 대상 키에 `respawn_seed_group_*`, `seed_pids`, `conflict_source_change_count`, `grievance_pairs_count`, `factionRef_changed_by_respawn_count`, `snn_gate_pass_count`, `uprising_skip_snn_inactive_count`, seed 멤버의 `faction_cooldown` 초기값 포함. 신규 telemetry 키가 결정성 비교에서 누락되면 P1 seed group 또는 SNN 게이트 측정의 결정성이 검증 공백 상태로 잔존.

### 성능 검증

- 평균 tick 시간 ≤ 250ms (현 154.4ms 기준 +5ms 이하 권장).
- `_pick_seed_group()`은 `_pick_founder()`와 동등 복잡도 (territory residents 1회 sort) → 성능 회귀 ≤ 0.5ms/tick.

### 안티패턴 자기 차단 점검 (Hard)

| 항목 | 판정 기준 |
|---|---|
| `if x == 0: skip` 회피 패턴 | test_phase17_acceptance.py 신규/수정 함수에 zero-condition skip 없음 |
| `respawn_events>=1` 단순 카운트 | 효과까지 검증 (seed_member_persisted_count > 0 또는 동등 측정 동반) |
| acceptance 사후 변경 | acceptance #2 임계 `>= 1` 무수정 (역공학 분기 차단) |
| 신규 source enum | `git grep "FactionChangeSource"` 결과 4종(`birth_founder`, `affiliation`, `drift`, `conflict`) 그대로 |
| sticky / floor / artificial propagation | grace boost가 grace 기간 종료 후에도 잔존하지 않음 (코드 검사 + E-3 `test_grace_boost_terminates` PASS) |
| 인라인 `sorted(self.personas)[0]` | `git grep "sorted(self.personas)\[0\]"` 결과 0건 |
| `brain/**` 변경 | `git diff HEAD -- Projects/personas/loom/brain/` 출력 0줄 |
| Phase 11~16 상수 변경 | layers.py diff에 `MARKET_*`, `FOOD_*`, `TOOL_*` 등 변경 0건 |
| 24틱 자연 재계산 | `_update_grievances` line 2091 `tick % 24 != 0` guard 무수정 |
| `score *= multiplier` 곱셈 가산 패턴 | `git grep -nE "score\s*\*=" Projects/personas/loom/core/multi_tick_engine.py` 결과 0건 (자연 가산은 += 만 사용 — 곱셈은 절대 우위 형성·자연 가산 4 조건 위반) |
| HYSTERESIS 자연 충족 | `factionRef_changed_by_respawn_count >= 1` 3 seed 중 최소 2 seed (자연 측정 통과 = HYSTERESIS 우회 아닌 충족) |
| seed 멤버 cooldown 자연 결합 | `git grep -nE "faction_cooldown\s*=\s*FACTION_COMMIT_EVERY" Projects/personas/loom/core/multi_tick_engine.py` 결과 ≥ 2건 (Phase A·B 각 1건) — 누락 시 P2 grace 200틱 의도와 self-flip 가능성 충돌 |

---

## 한계 대응 프로토콜 (CLAUDE.md Rule 11~16 적용)

만약 acceptance #2 자연 측정이 5000틱 × 3 seed 전부 PASS 못한다면:

### Recognize (한계 신호)
- 같은 접근(seed_group + grace boost 조합)으로 3회 이상 실패 → 한계 도달.

### Premise Inversion 후보 (안전 전제 제외)
1. **전제 A**: "founder 단독 → 즉시 흡수" → seed group 자연 가입으로 해결 가능.
   - **반전**: founder 단독으로도 충분한가? → 아니. seed 없으면 H2c 재현.
2. **전제 B**: "trust ≥ 0.4가 community 자연 임계" → seed 멤버 풀이 충분한가?
   - **반전**: trust 0.4 멤버가 territory 거주자 중 부족할 수 있음 → free_residents 풀 자체가 빈약 (Phase A 차단의 root). DIAGNOSIS H2a 표면 재발.
3. **전제 C**: "grace boost 0.12는 흡수 압력을 충분히 상쇄" → 측정 후 임계 조정 필요할 수도.
   - **반전 시 위험**: 자가 튜닝 = 거짓 PASS 안티패턴. **금지**.
4. **전제 D**: "P1 seed 3명이 FACTION_HYSTERESIS=2 를 자연 충족할 수 있는 territory 인구 조건이 성립한다."
   - **반전**: T₁ dominant ≥ 6명이면 P1 seed 3명만으로는 `_project_faction_tick` HYSTERESIS 미통과 → contact 미회복 → grievance pair 미응결.
   - **검출 신호**: `factionRef_changed_by_respawn_count == 0` (3 seed 전부) + `respawn_seed_group_total >= 1` 동시 만족 시 = "seed 는 만들어졌으나 dominant 우위 미형성".
   - **대응 경로**: 본 spec 범위 외 → P3·P4 외에 Φ-2 Stage 3 respawn 인구 파라미터 재검토 경로(`FOUNDER_RESPAWN_TARGET_ACTIVE` 상향, seed group 크기 4·5 시뮬) 도 후보로 사용자에게 보고.

### 안전 전제 (반전 대상 제외 — LOOM-DIRECTION §2.4 보호)
- `FACTION_HYSTERESIS = 2` (Φ-2 Charter §Operating Loop 자연 안정성 조건 — 약화 시 dominance 진동·테스트 결정성 붕괴)
- `FOUNDER_RESPAWN_EVERY`, `FOUNDER_RESPAWN_TARGET_ACTIVE` (Stage 3 anti-collapse 자연 발화 보호 상수)
- `FACTION_COMMIT_EVERY = 48` (drift cooldown — self-flip 방지의 자연 게이트)
- 위 상수 중 하나라도 변경 필요가 의심되면 **반전 대신** 사용자 에스컬레이션 + LOOM-DIRECTION §2.4 무파괴 충돌 보고.

### Dimension Shift 후보 (premise A·B·D 모두 무효 시)
- DIAGNOSIS-REPORT P3 (Affiliation Absorption Pressure 조정) 또는 P4 (Grievance Resonance Bridge) 별도 spec 진입.
- 또는 Φ-2 Stage 3 respawn 인구 파라미터 재검토 (전제 D 반전 결과 한정, 안전 전제 보호 하에서만).
- 본 spec 범위 외 → 사용자 에스컬레이션.

### "FAIL" 해석 의무 (CLAUDE.md Rule 14)
P1+P2가 acceptance #2 PASS 못하면, 실패 보고는 **"FAIL"만으로 끝내지 말 것**:
- "This tells us": contact graph 회복 + founder 지속만으로는 grievance 응결까지 보장 못한다 → P3·P4 차원의 absorption pressure 또는 grievance bridge 필요.

---

## Rollback

```bash
git revert <commit-hash>
# 또는 수동 rollback:
# 1. multi_tick_engine.py: _pick_seed_group 메서드 삭제
# 2. multi_tick_engine.py: _respawn_faction_tick Phase A·B의 seed_group 호출·이벤트 로그 제거
# 3. multi_tick_engine.py: _compute_affiliation_tick의 grace boost 분기 제거
# 4. layers.py: GRACE_AFFILIATION_BOOST 상수 제거
# 5. observe_phase17_emergence.py: 신규 telemetry 5종 집계 제거
# 6. test_phase17_acceptance.py: 변경분 revert
```

데이터 영향: 없음 (인메모리 telemetry만 변경, 파일/DB 영향 0).

---

## 다음 단계 (본 spec 통과 후)

1. **/spec-review 자체 검토** — 10 카테고리 체크리스트 통과 후 사용자에게 제시.
2. **사용자 승인** → 구현 분기 결정 (Claude 직접 / /sub sub-implementer / Codex 지시서 외부 위임).
3. **구현 후 closure**:
   - 5000틱 × 3 seed natural acceptance #2 PASS 확인 → `PHASE-17-CASE-C-CLOSURE-REPORT.md` 작성.
   - audit run-summary.md의 finding 7건 (C-1, C-2, M-2, M-3, M-4, M-5, M-7-2) 해소 표 작성.
4. **Φ-3 closure v2** — 본 spec 통과 후 STRUGGLE-CHARTER §6 보류 5종 TBD 해소 + Φ-4 진입 trigger 정량 확정 (run-summary R2 C-1 finding 후속 처리).
5. **분기 B (PersonaBrain substrate)** 진입 검토 — 사단 substrate + chiljeong readout coupling.
