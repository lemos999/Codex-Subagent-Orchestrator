# Phase 17 / Φ-3 Struggle — Project Charter

> `/design` Phase 1 산출물. STUB([PHASE-17-STRUGGLE-CHARTER-STUB.md](PHASE-17-STRUGGLE-CHARTER-STUB.md))에서 정의한 handoff 계약을 본 Charter가 수퍼셋으로 계승.
> 선행:
> - Φ-2 Faction Stage 6 H-lite 구현 PASS (founder_lineage W=0.2, drift -53/-14/-12%p 안정화)
> - Charter v2 Φ-3 진입 OR 측정([CHARTER-V2-ENTRY-CHECK.md](data/phase17_probe_stage6/CHARTER-V2-ENTRY-CHECK.md)) — 3 seed 전부 OR-1 단독 충족 (1/3) → **진입 자격 PASS**

---

## 목표·목적 3계층 (역산 기준)

**궁극 목적 (loom 전체)**
페르소나가 살아가는 과정에서 국가가 자연 탄생한다. Top-down "여기 국가 있음" 선언 금지. **삶 → 유대 → 갈등 → 주권 선언**의 인과 사슬로만 국가 생성.

**Phase 17 목적**
자연 탄생의 4단계 인과 사슬 구축. 각 단계는 다음 단계의 재료를 만든다.
- Φ-1 Land: '어디에' 있는가 (공간 기반) — CLOSED
- Φ-2 Faction: '누구와' 뜻이 같은가 (정치 기반) — CLOSED (Stage 6)
- **Φ-3 Struggle**: 다른 '누구'와 충돌·동맹 (분화 동역학) — **본 Charter**
- Φ-4 Nation: 충분히 큰 결집이 주권 선언 (자연 탄생)

**Φ-3 고유 역할**
"왜 싸우는가"의 자연 발생. Φ-2가 만들어낸 "우리"(Faction) 위에 **공동 분노 → 봉기 → 분파·합류 → 분포 비대칭**의 사슬을 도입. 충돌은 top-down 선언이 아니라 **누적된 grievance에서 자라나야** 함. SNN의 anger·fear·dignity 발화가 봉기 trigger로 작동하여 규칙 < 창발 비율 유지.

---

## 메타

| 항목 | 값 |
|------|-----|
| 프로젝트 | loom 페르소나 국가 시뮬 |
| Phase | 17 (Φ-3 Struggle) |
| 로드맵 위치 | Φ-1 Land → Φ-2 Faction → **Φ-3 Struggle** → Φ-4 Nation |
| 선행 합의 | Φ-2 Stage 6 closure / Charter v2 무파괴 9 보장 / D10 read-only 7종 freeze |
| 선행 측정 | OR-1 PASS (3/3) / OR-2 FAIL (40%) / OR-3 FAIL (0쌍) — 본 Charter가 OR-2/OR-3를 자연 충족시켜야 함 |
| 날짜 | v1 2026-04-27 |

---

## Primary Outcome

페르소나의 **누적된 grievance가 faction 단위로 응결**하여 **봉기(uprising)로 발화**하고, 그 결과 **faction 멤버 분포가 자연 비대칭**으로 재편된다. Φ-4 Nation이 필요로 하는 **분파·합류·지배 구도**의 재료를 Φ-3 동역학이 자연 생성한다.

**핵심 시나리오**:
1. Territory T1의 lord L1이 세금·식량 부족·trust 결여로 거주민 grievance 누적 (Phase 14 인프라)
2. Faction F1 멤버 다수가 L1을 `grievance_lord_id`로 공유 → `faction_grievance_targets()`의 `{F1: {L1: count≥2}}` 응결
3. 응결된 공동 분노가 임계치 돌파 + SNN anger·fear 발화 동기화 → **uprising_event 발화**
4. 봉기 페르소나는 인접 faction(`factions_in_contact`)으로 자발 이주 (`source="conflict"`) **또는** 분파 신규 faction 생성 (Stage 6 `_respawn_faction_tick` 패턴 계승)
5. 결과: contact_pairs 간 멤버 재분포 → `dom_share` 자연 증가 (OR-2 충족) + `grievance_pairs ≥ 1` 응결 유지 (OR-3 충족)
6. → Φ-4 진입 조건: 충분히 큰 단일 faction이 다수 territory 지배 → 주권 선언 재료

---

## Operating Loop

- **마이크로 (틱 단위)**: 각 페르소나의 `inner.grievance` 누적 (Phase 14 `_update_grievances`). SNN 300~349 영역에서 anger·fear·dignity 채널이 grievance와 co-fire. **신규 mechanism 없음** — 기존 인프라 관찰만.
- **미들 (24~48틱)**: `faction_grievance_resonance(faction_id)` — 같은 faction 멤버가 같은 `lord_id`를 공유하는 카운트 + grievance 평균. 임계치 `THETA_UPRISING` 돌파 + 인접 faction 존재 시 **uprising_event** 발화. 봉기 페르소나는 `_change_persona_faction(source="conflict")`로 인접 faction 가입 또는 분파 신규 faction 생성.
- **매크로 (수백~수천틱, 목표 지향형)**: 봉기 누적 → `dom_share` 자연 비대칭 + `grievance_pairs ≥ 1` 응결 유지 → **Φ-4 Nation 진입 조건** (단일 faction의 multi-territory 지배 + 사회 안정도 임계 등) 충족.

---

## Baseline Expectations

**포함**:
1. `faction_grievance_resonance(fid) -> dict` — read-only API. faction 멤버의 `grievance_lord_id` 분포 + 평균 grievance 반환.
2. `uprising_trigger()` — 24/48틱 주기. 응결 임계치 + 인접 faction 존재 시 봉기 후보 페르소나 list 산출.
3. `_emit_uprising(pid, target_faction_id | new_faction_intent)` — 봉기 페르소나의 faction 변경 단일 경로. 내부적으로 `_change_persona_faction(source="conflict")` 호출.
4. 신규 source 사용: 기존 4종 중 `"conflict"` 활용 (Φ-3 예약 분, Charter v2 [확정] #7). **5번째 source 추가 금지.**
5. 분파 신규 faction 생성 경로: 기존 `_respawn_faction_tick` 패턴 계승 — `founder_pid` = 봉기 주도자, `founder_lineage` = 원 faction lineage 연장 (분파 추적), Charter primitives 변형 (Decision Card에서 결정).
6. SNN 통합: 기존 300~349 영역에 uprising telemetry co-fire. **n_neurons=1000 절대 고정**, 신규 뉴런 추가 금지.
7. uprising_event 텔레메트리: `event_log.append({"type": "uprising", "tick", "leader_pid", "from_faction", "target_faction" | "new_faction_id", "lord_id", "members_count", "grievance_mean"})`.
8. metrics.jsonl 신규 type: `"uprising"` (probe 측정용 read-only). 기존 5종(`population`, `contact`, `wealth`, `grievance_targets`, `source_cumulative`) 무수정.

**제외 (Φ-3 비범위)**:
- 전투·약탈·사망 → Φ-4 또는 별도 Charter (Φ-3는 멤버 이동·분파만)
- 영주 교체·정권 전복 → Φ-4 (사회 권력 재편은 nation level)
- Charter primitives 개정 → Φ-4 reform (Φ-3는 분파의 신규 charter만 생성, 기존 charter 수정 X)
- Faction 간 동맹·연맹 구조 (탈주가 아닌 합병) → Φ-4
- 외교·교섭 행동 → Φ-4
- **대체**: Φ-3는 "응결 → 봉기 → 분포 변화"만. 권력 재편·외교는 Φ-4.

**거부 결정**:
- ❌ **신규 SNN 뉴런 (350~389)**: Phase 14-B `n_neurons=1000` freeze, `readout_weights_v1.npy` 1000폭 고정 — 거부. 300~349 재사용.
- ❌ **신규 FactionChangeSource (`"uprising"` 추가)**: Stage 4 closure D10에서 4종 freeze. 기존 `"conflict"` 재사용.
- ❌ **Top-down 봉기 선언** (특정 tick에 무조건 봉기 발화): grievance 누적 + SNN 발화에서만 trigger. 시간 기반 강제 봉기 금지.
- ❌ **Φ-2 internal state 직접 mutation**: `_change_persona_faction()` SSoT 경로 외 faction 변경 금지. AST whitelist 5건 무수정.

---

## Differentiation Thesis

**"갈등 시뮬인데, 봉기를 설계자가 정의하지 않고 grievance 응결과 SNN 발화의 중첩에서 발화하기 때문에, 봉기가 시나리오 이벤트로 박히지 않고 누적된 분노의 임계 현상으로 떠오른다."**

- 기존 4X·civ 게임: 봉기·반란이 "유닛 행복도 < N" 또는 "이벤트 카드"로 명시 정의
- loom Φ-3: **이미 누적되는 grievance(Phase 14) + 이미 작동하는 SNN(Phase 14-B) + Φ-2 faction 응결**의 **3중 중첩**에서만 봉기 발화 — 봉기 자체는 신규 mechanism이 아니라 **3 layer 정렬 시 자동 발화**되는 임계 현상
- 그 결과 봉기 횟수·시점·규모가 시뮬 시작 시점에 존재하지 않고, grievance·SNN·faction의 실제 흐름에서만 떠오름

---

## Target Audience

| 항목 | 결정 |
|------|------|
| 대상 사용자 | loom 시뮬 개발자(본인), Φ-4 Nation 진입 게이트 사용자 |
| 사용 환경 | `MultiTickEngine` (Python 3.x), 5000~수만 틱 단위 시뮬 |
| 허용 복잡도 | 중간 — 신규 1 함수(`uprising_trigger`) + 신규 1 호출 (`_emit_uprising`), **신규 SNN 뉴런·신규 source 금지** |
| 기대 사용 빈도 | 매 24~48틱 봉기 응결 검사, 봉기 발화 시 1~수 명 faction 이동, 5000틱당 봉기 0~수회 |
| 핵심 제약 | Charter v2 무파괴 9 보장 / 결정성(seed=42 재현) / SNN n_neurons=1000 절대 고정 / 성능 ≤ 250ms/tick (Φ-3 예산 ≤ 5ms) / D10 7종 read-only 무수정 |

---

## Charter 일관성 검증

- [x] Primary Outcome 1가지 확정
- [x] 3레이어 Operating Loop 한 문장씩
- [x] Baseline 포함/제외/거부 결정
- [x] Differentiation Thesis 한 문장
- [x] Target Audience 환경/제약 확정
- [x] Primary Outcome ↔ Operating Loop 양립? — 마이크로 grievance 누적이 미들 응결에 피드, 미들 봉기가 매크로 분포 비대칭으로 수렴
- [x] Differentiation ↔ Baseline 모순 없음? — "임계 현상 vs 무파괴 원칙" 잠재 상충 → 해소: **신규 mechanism은 trigger·emit 2 함수만**, 나머지는 기존 인프라(Phase 14 grievance + Stage 6 _respawn) 호출 조합
- [x] Target 허용 복잡도 ↔ Primary Outcome 일치? — 중간 복잡도로 응결·발화·재분포만 도입, 권력 재편은 Φ-4
- [x] 3레이어 모두 Primary Outcome 강화? — 마이크로(grievance) → 미들(uprising) → 매크로(imbalance + grievance_pairs 응결) 전부 같은 방향
- [x] 마이크로 → 미들 → 매크로 피드 연결? — Phase 14 grievance → Φ-3 trigger → faction 멤버 재분포 → D10 API 측정값 변동
- [x] 매크로가 순환형? — **목표 지향형** (Φ-4 진입 조건이 최종 goal)
- [x] 궁극 목적 정렬? — grievance 누적은 페르소나 내부 상태, 봉기는 SNN 발화 + faction 응결 중첩에서만 → **top-down 선언 금지 원칙** 준수

**결과**: **PASS**

---

## [확정 선행 결정] — Phase 2/3 스텁

다음 Phase(Component Map, Decision Card)에서 확장되지만 Charter 단계에서 이미 결정된 사항.

### 1. 진입 조건 (Charter v2 OR 검증 결과 반영)

Φ-3 본 구현은 **OR-1 단독 충족(`factions_in_contact ≥ 1`)** 자격으로 진행 가능. Stage 6 측정 3 seed 전부 PASS.

OR-2 (imbalance), OR-3 (grievance) 미충족은 **Φ-3가 자연 발생시킬 결과**로 정의 (Charter v2 §"Phi-3 Entry Trigger Candidates"의 OR 의미 전환):
- v2 정의: OR 충족 시 Φ-3 진입 가능 (단일 조건도 OK)
- Φ-3 본 Charter 정의: 진입은 OR-1만 / OR-2·OR-3는 **Φ-3 acceptance 기준**

### 2. 핵심 신규 API — Φ-3 내부 (read-only 1종 + write 0종)

```python
def faction_grievance_resonance(self, faction_id: str) -> dict:
    """faction 멤버의 lord별 grievance 응결 측정.
    
    반환: {
        "lord_counts": {lord_id: member_count},   # ≥ GRIEVANCE_MIN_SHARED 멤버만
        "grievance_mean": float,                  # 전체 멤버 grievance 평균
        "max_lord_share": float,                  # 최다 lord 카운트 / 전체 grievance 보유 멤버
        "resonance_score": float,                 # 응결 강도 (max_lord_share * grievance_mean)
    }
    
    공허 faction(멤버 0) → 모든 값 0. read-only, 신규 객체 반환.
    Φ-3 내부 호출 전용. D10 7종 외부 API에는 추가 금지.
    """
```

`faction_grievance_targets()` (Φ-2 D10 #7)는 `{fid: {lord_id: count}}` 외형만 반환. `faction_grievance_resonance()`는 Φ-3 내부 강도 측정. **D10 7종은 무수정**.

### 3. Uprising trigger 단일 함수

```python
def _uprising_trigger(self) -> list[dict]:
    """24/48틱 주기. 응결 + SNN + 인접 조건 동시 충족 시 봉기 후보 산출.
    
    반환: [{"leader_pid", "from_faction", "lord_id", "target_faction" | None, ...}]
    target_faction = None → 분파 신규 faction 생성 의도
    """
    if self.time.tick % UPRISING_CHECK_INTERVAL != 0:
        return []
    
    candidates = []
    for fid in self.factions:
        reso = self.faction_grievance_resonance(fid)
        if reso["resonance_score"] < THETA_UPRISING:
            continue
        # 인접 faction 존재 검사 (D10 호출, read-only)
        contacts = [pair for pair in self.factions_in_contact(radius=1) if fid in pair]
        if not contacts:
            continue
        # 봉기 leader 선정: faction 내 grievance 최고치 멤버 (sorted(pid) tie-break)
        members = self._faction_members(fid)
        eligible = [
            pid for pid in sorted(members)
            if self.inners[pid].grievance >= GRIEVANCE_MIN_SHARED
            and self.inners[pid].grievance_lord_id == reso["lord_counts_top_lord_id"]
            and self.personas[pid].faction_cooldown == 0
        ]
        if not eligible:
            continue
        leader_pid = max(eligible, key=lambda p: (self.inners[p].grievance, p))
        # SNN 발화 검사 (Phase 14-B: anger·fear·dignity 임계)
        if not self._snn_uprising_signal_active(leader_pid):
            continue
        # target_faction 선정: contact pair 중 봉기 leader와 territory 인접도 최고
        target_fid = self._pick_uprising_target(leader_pid, contacts) or None
        candidates.append({
            "leader_pid": leader_pid,
            "from_faction": fid,
            "lord_id": reso["lord_counts_top_lord_id"],
            "target_faction": target_fid,
            "grievance_mean": reso["grievance_mean"],
        })
    return candidates
```

- `THETA_UPRISING`, `UPRISING_CHECK_INTERVAL`, `_snn_uprising_signal_active`, `_pick_uprising_target` 구체 수식 → **Phase 3 Decision Card**.
- 모든 RNG 사용 시 `_derive_rng("uprising_*", ...)` 경유 — Phase 17 Φ-1 중앙 RNG 정책 준수.

### 4. Uprising 발화 단일 함수

```python
def _emit_uprising(self, candidate: dict) -> None:
    """봉기 발화. _change_persona_faction(source="conflict") 단일 경로 호출.
    
    candidate["target_faction"] is not None:
        → 인접 faction으로 가입 (분포 재편)
    candidate["target_faction"] is None:
        → 분파 신규 faction 생성 (Stage 6 _respawn_faction_tick 패턴 계승)
    """
    leader_pid = candidate["leader_pid"]
    from_fid = candidate["from_faction"]
    target_fid = candidate["target_faction"]
    
    if target_fid is None:
        # 분파 신규 faction 생성 (Stage 6 패턴)
        new_fid = self._spawn_branch_faction(
            founder_pid=leader_pid,
            parent_fid=from_fid,           # founder_lineage 체인 계승 (Stage 6)
            charter_basis="dissent",       # Decision Card에서 norm primitive 결정
        )
        target_fid = new_fid
    
    self._change_persona_faction(leader_pid, target_fid, source="conflict")
    
    # 동조 멤버 follow-up (Decision Card에서 결정: 0~K명)
    followers = self._select_uprising_followers(candidate)
    for pid in sorted(followers):
        self._change_persona_faction(pid, target_fid, source="conflict")
    
    # 텔레메트리
    self.event_log.append({
        "type": "uprising",
        "tick": self.time.tick,
        "leader_pid": leader_pid,
        "from_faction": from_fid,
        "target_faction": target_fid,
        "lord_id": candidate["lord_id"],
        "members_count": 1 + len(followers),
        "grievance_mean": round(candidate["grievance_mean"], 3),
    })
    
    # grievance reset (봉기 행위 자체가 분노 해소)
    for pid in [leader_pid, *followers]:
        self.inners[pid].grievance = max(0.0, self.inners[pid].grievance * UPRISING_GRIEVANCE_DECAY)
```

- AST whitelist 5건 무수정. `# noqa: PHASE17_FACTION_SSOT_WRITE` 마커는 `_change_persona_faction()` 내부에만 존재.
- 분파 신규 faction의 `founder_lineage`는 부모 faction lineage 연장 (Stage 6 H-lite 패턴) — 분파 추적 가능.

### 5. tick() 통합 위치

```
Stage 1 (각 페르소나, 매 틱):
    [기존] _process_economy(pid, action)        # grievance 누적 (Phase 14)
    [기존] eat/work/explore/socialize           # SNN 발화 갱신
    
Stage 4 (24~48틱마다, _auto_economy_tick 또는 _respawn_faction_tick 직후):
    [기존] _respawn_faction_tick()              # Stage 3 anti-collapse
    [신규] candidates = self._uprising_trigger()
    [신규] for c in candidates:
              self._emit_uprising(c)
```

- `_uprising_trigger`는 `_respawn_faction_tick` 직후 호출 — anti-collapse가 신규 faction을 만든 직후 봉기 검사로 자연 흐름.
- 봉기 발화 직후 `FACTION_COOLDOWN_TICKS = 48`이 적용되어 같은 페르소나 연속 봉기 방지.

### 6. 신규 상수 (초기값은 Phase 3 Decision Card에서 확정)

```python
# Phase 17 Φ-3 Struggle 신규 상수
THETA_UPRISING = TBD              # resonance_score 임계치 (예상 0.4~0.6)
UPRISING_CHECK_INTERVAL = TBD     # 봉기 검사 주기 (예상 24 또는 48)
UPRISING_GRIEVANCE_DECAY = TBD    # 봉기 후 grievance 감쇠 비율 (예상 0.3~0.5)
UPRISING_FOLLOWER_MAX = TBD       # 동조 멤버 최대 수 (예상 1~3)
SNN_ANGER_FIRE_THRESHOLD = TBD    # SNN anger 채널 발화 판정 (예상 0.6~0.8)
```

### 7. 검증 계약 (Hard 불변)

Phase 17 Φ-3 구현 후 반드시 통과:
- [ ] **Φ-2 무파괴 9 보장 그대로 계승** (Stage 4 closure §5 D10 read-only handoff lock 12/12 PASS 유지)
- [ ] **AST whitelist 5건 무수정** (`PHASE17_FACTION_SSOT_WRITE` 마커 5라인 그대로)
- [ ] **FactionChangeSource 4종 불변** (`birth_founder` | `affiliation` | `drift` | `conflict`)
- [ ] **D10 7종 API read-only freeze 유지** (`test_phase17_faction_handoff_contract.py` 12/12 PASS)
- [ ] **결정성 (`five_channel_determinism`)**: seed=42, 5000틱 2회 실행 snapshot 일치 (`uprising_event` 포함)
- [ ] **SNN n_neurons=1000 고정** (`readout_weights_v1.npy` 호환)
- [ ] **성능 회귀 ≤ 250ms/tick** (현 154.4ms, Φ-3 예산 ≤ 5ms)
- [ ] **Φ-3 acceptance 1차**: seed 7/13/42 5000틱 모두 `uprising_event ≥ 1` (3/3)
- [ ] **Φ-3 acceptance 2차**: seed 7/13/42 5000틱 모두 `grievance_pairs_end ≥ 1` (3/3)
- [ ] **Φ-3 acceptance 3차**: seed 7/13/42 5000틱 모두 `dom_share_end ≥ 0.50` (3/3, OR-2 자연 충족)
- [ ] **무사망 보장**: `population_total_end == population_total_start` (Φ-3는 멤버 이동만, 사망 X)
- [ ] **분파 lineage 추적**: 분파 faction의 `founder_lineage`가 부모 faction lineage 포함 (Stage 6 패턴 검증)

---

## [보류 해소 현황] — Phase 3 Decision Card 대기

| 항목 | 해소 위치 |
|------|-----------|
| `THETA_UPRISING` 임계치 (resonance_score 컷오프) | Phase 3 Decision Card |
| `UPRISING_CHECK_INTERVAL` 검사 주기 (24 vs 48 vs 72) | Phase 3 |
| `UPRISING_GRIEVANCE_DECAY` 봉기 후 감쇠 비율 | Phase 3 |
| `UPRISING_FOLLOWER_MAX` 동조 멤버 상한 | Phase 3 |
| `SNN_ANGER_FIRE_THRESHOLD` SNN 발화 판정 | Phase 3 (Phase 14-B 발화율 분포 측정 필요) |
| `_snn_uprising_signal_active()` 구체 수식 (anger + fear + dignity 가중합?) | Phase 3 (`/sub p-snn-charter` 검증 권장) |
| `_pick_uprising_target()` 우선순위 (territory 인접도 vs 종교성 vs 경제성?) | Phase 3 |
| `_select_uprising_followers()` 선정 기준 (같은 lord_id 공유 + grievance 차순?) | Phase 3 |
| `_spawn_branch_faction()` charter primitives 변형 규칙 (부모 charter ⊕ "dissent" 1개 교체?) | Phase 3 |
| 분파 신규 faction의 territory 시작점 (leader 거주지 vs 빈 territory?) | Phase 3 |
| Φ-3 metrics.jsonl 신규 type `"uprising"` schema | Phase 3 |
| Φ-3 SUMMARY.md primary 분리 형식 (Stage 5/6 패턴 계승) | Phase 5 (`/spec` Codex 지시서) |

---

## [확정] — Charter v2 무파괴 9 보장 계승

Stage 4 closure §"D10 read-only definition" + Stage 6 H-lite의 9 보장을 그대로 계승. Φ-3 구현은 9 항목 중 어느 하나도 깨지 않음:

1. **D10 read-only 7종 API**: `persona.faction`, `persona.faction_cooldown`, `inner.affiliation_scores`, `engine.factions` 레지스트리 5필드 (id, name, founder_pid, charter, created_tick), `territory.factionRef` — domain mutation 금지. Φ-3는 `_change_persona_faction(source="conflict")` 단일 경로로만 변경.
2. **AST whitelist 5건**: `# noqa: PHASE17_FACTION_SSOT_WRITE` 마커 5라인 무수정. Φ-3는 신규 마커 추가 0건.
3. **FactionChangeSource 4종 freeze**: `birth_founder` | `affiliation` | `drift` | `conflict`. Φ-3는 `"conflict"` 재사용, 신규 source 추가 금지.
4. **SNN n_neurons=1000 freeze**: Phase 14-B `readout_weights_v1.npy` 1000폭 고정. Φ-3는 신규 뉴런 추가 0건, 기존 300~349 영역 재사용.
5. **grace_until_tick 정합**: 신규 faction (분파 포함)의 `grace_until_tick`은 `created_tick + GRACE_PERIOD`. 기존 패턴 계승.
6. **residence_ticks 정합**: 봉기 leader의 territory 거주 이력은 `inner.residence_ticks`에 보존. 봉기로 territory 이동 시 기존 reset 규칙 적용.
7. **공허 정합 (None 허용)**: `territory.factionRef = None`은 봉기 발화 후에도 정합. 분파 신규 faction이 territory를 점유하지 않으면 None 유지.
8. **Kernel SSoT (`_update_affiliation_scores`)**: 봉기 발화 후 affiliation_scores는 자연 재계산. Φ-3는 affiliation_scores 직접 mutation 금지.
9. **Double-buffer commit**: territory.factionRef 갱신은 기존 24틱 double-buffer 경로 유지. Φ-3는 commit 경로 추가 금지.

---

## [확정] — handoff API 7종 read-only 사용

Φ-3 구현은 Φ-2 D10 7종 API를 **read-only 소비자**로만 사용:

| API | Φ-3 사용 |
|-----|---------|
| `faction_population_distribution()` | 봉기 후 imbalance 측정 (acceptance 3차) |
| `faction_territory_distribution()` | `_pick_uprising_target()` 인접도 계산 |
| `faction_charter_primitives(fid)` | `_spawn_branch_faction()` 부모 charter 참조 |
| `factions_in_contact(radius=1)` | uprising_trigger 인접 faction 존재 검사 |
| `faction_wealth_distribution()` | 향후 Phase 3 Decision Card에서 follower 선정 가중치로 사용 가능 |
| `faction_social_matrix()` | 향후 Phase 3 Decision Card에서 target_faction 우선순위로 사용 가능 |
| `faction_grievance_targets()` | `faction_grievance_resonance()`의 외형 출력. 직접 caller mutation 금지. |

신규 D10 API 추가 금지. 7종 freeze 유지.

---

## 다음 단계

1. **사용자 Charter 검증** — 본 문서 수정 요청 or 확정
2. **Phase 2 Component Map** — `faction_grievance_resonance` / `_uprising_trigger` / `_emit_uprising` / `_spawn_branch_faction` 분해 + SNN telemetry hook 매핑
3. **Phase 3 Decision Card** — `[보류 해소 현황]` 12개 항목 초기값·수식 구체 결정
4. **Phase 3.5 Cross-Impact** (선택) — `/sub p-snn-charter` 또는 `/discuss`로 SNN anger·fear·dignity 발화율 분포 측정 → `SNN_ANGER_FIRE_THRESHOLD` 정량화
5. **Phase 4 Verify** — 결정성·성능·무파괴·acceptance 3차 검증 계약 모두 통과 게이트
6. **Phase 5 Package** — `/spec`으로 Codex 전달용 `PHASE-17-STRUGGLE-CODEX-INSTRUCTIONS.md` 작성
7. **구현 후** — 3 seed × 5000 tick probe → SUMMARY.md primary 분리 → `test_phase17_acceptance.py`에 grievance/uprising 검증 추가 → Φ-3 closure
