# Phase 17 / Φ-3 Struggle — Phase 3 Decision Card

> Charter([PHASE-17-STRUGGLE-CHARTER.md](PHASE-17-STRUGGLE-CHARTER.md)) §"보류 해소 현황" 12개 항목의 초기값·구체 수식 확정.
> 모든 값은 **probe 측정 결과로 후속 튜닝 가능** (Φ-2 v3→v4→v5→v6→Stage 5/6의 가중치 진화 패턴 계승).
> 작성: 2026-04-27.

---

## D1. 신규 상수 5종 초기값

| 상수 | 초기값 | 근거 |
|------|:------:|------|
| `THETA_UPRISING` | **0.40** | resonance_score = max_lord_share × grievance_mean. faction 절반이 같은 lord에 grievance 0.8 → 0.5×0.8=0.40 (응결 강한 상태). |
| `UPRISING_CHECK_INTERVAL` | **48** | `FACTION_COOLDOWN_TICKS`와 동일. 한 cooldown 사이클당 검사 1회. `_update_grievances`(24틱) 2 사이클 후 검사. |
| `UPRISING_GRIEVANCE_DECAY` | **0.5** | `_try_exodus`의 `inner.grievance * 0.5` (multi_tick_engine.py:1773)와 일관. 봉기 = 분노 절반 해소. |
| `UPRISING_FOLLOWER_MAX` | **2** | leader + 2 followers = 최대 3명 이동. Stage 6 측정 평균 멤버 ≈ 3~4명 → 1회 봉기 영향 ≤ 50% (faction 붕괴 방지). |
| `SNN_ANGER_FIRE_THRESHOLD` | **0.6** | `chiljeong[1]` anger ≥ 0.6. grievance 0.8에서 `(0.8-0.5)*0.2=0.06`/24틱 누적 → 100~200틱 내 도달 가능. |

**튜닝 정책**: probe에서 `uprising_event_count == 0` (acceptance #1 FAIL) 시 `THETA_UPRISING` 0.05 단계씩 하향. `uprising_event_count > 10/seed` 시 0.05 단계씩 상향 (과발화 방지).

---

## D2. `_snn_uprising_signal_active(pid)` 수식

```python
def _snn_uprising_signal_active(self, pid: str) -> bool:
    """Phase 14-B chiljeong/oyok 기반 SNN 발화 검사. 신규 SNN 뉴런 0건."""
    inner = self.inners[pid]
    anger = float(inner.chiljeong[1])
    fear = float(inner.chiljeong[3])
    dignity = float(inner.oyok[4])
    return (
        anger >= SNN_ANGER_FIRE_THRESHOLD   # 0.6
        and fear < anger                     # 분노 > 두려움 (소극적 위축 배제)
        and dignity >= 0.5                   # 자존감 임계 (체념 상태 배제)
    )
```

**근거**:
- `_update_grievances` (multi_tick_engine.py:1834~1841)이 grievance ≥ 0.5에서 anger·fear·dignity를 동시 증가 → 3채널 정렬은 자연 발생
- `fear < anger`: 두려움 우세 시 봉기 대신 exodus·체념. Phase 14 `_try_exodus`가 grievance ≥ 0.9에서 발화하므로 0.5~0.9 구간이 Φ-3 범위
- `dignity >= 0.5`: oyok[4] 명예욕 임계. 자존감 없는 페르소나는 봉기 주도자 부적합

---

## D3. `_pick_uprising_target(leader_pid, contacts)` 수식

```python
def _pick_uprising_target(
    self, leader_pid: str, contacts: list[tuple[str, str]]
) -> str | None:
    """봉기 leader가 가입할 인접 faction 선택. None → 분파 신규 생성 의도."""
    from_fid = self.personas[leader_pid].faction
    if from_fid is None:
        return None
    # contact pair에서 leader의 from_fid와 짝 이루는 다른 fid 추출
    candidates = sorted({
        other for pair in contacts for other in pair if other != from_fid
    })
    if not candidates:
        return None
    # leader 거주 territory와 인접한 territory를 가진 faction 우선
    leader_tid = self.personas[leader_pid].territory
    if leader_tid is None:
        return candidates[0]   # tie-break sorted(fid) 첫 번째
    neighbor_tids = self._get_neighbor_territories(leader_tid)
    territory_dist = self.faction_territory_distribution()
    for fid in candidates:    # sorted 순회 = tie-break
        fid_territories = territory_dist.get(fid, [])
        if any(t in fid_territories for t in neighbor_tids):
            return fid
    return candidates[0]
```

**근거**:
- 봉기 페르소나는 멀리 못 떠남 → 인접 territory의 faction 우선
- tie-break: `sorted(fid)` 사전순 (Charter v2 [확정] #5 결정성 정책 계승)
- `_get_neighbor_territories`는 Φ-1 인프라. 미존재 시 contact pair 전부에서 sorted 첫 번째

---

## D4. `_select_uprising_followers(candidate)` 수식

```python
def _select_uprising_followers(self, candidate: dict) -> list[str]:
    """봉기 동조 멤버 선정. 최대 UPRISING_FOLLOWER_MAX명."""
    from_fid = candidate["from_faction"]
    lord_id = candidate["lord_id"]
    leader_pid = candidate["leader_pid"]
    members = self._faction_members(from_fid)
    eligible = [
        pid for pid in members
        if pid != leader_pid
        and self.inners[pid].grievance_lord_id == lord_id
        and self.inners[pid].grievance >= GRIEVANCE_MIN_SHARED
        and self.personas[pid].faction_cooldown == 0
    ]
    # 정렬: grievance 내림차순, tie-break sorted(pid)
    eligible.sort(key=lambda p: (-float(self.inners[p].grievance), p))
    return eligible[:UPRISING_FOLLOWER_MAX]
```

**근거**:
- 같은 lord_id를 grievance 대상으로 공유하는 멤버만 follower 자격
- `cooldown == 0` 필터: 직전 봉기로 cooldown 진행 중인 멤버는 제외
- 결정성: `(-grievance, pid)` tuple sort 안정. follower 전부 supersede 시 한 명도 이동 없을 수 있음 (그래도 leader 단독 이동 OK)

---

## D5. `_spawn_branch_faction(...)` 수식

```python
def _spawn_branch_faction(
    self, *, founder_pid: str, parent_fid: str, charter_basis: str = "dissent"
) -> str:
    """분파 신규 faction 생성. founder_lineage 체인 계승 (Stage 6 H-lite 패턴)."""
    parent = self.factions[parent_fid]
    parent_charter = list(parent.charter)
    # charter primitives 변형: 1개 교체 (NORM_PRIMITIVE_CATALOG에서 부모에 없는 것)
    used = set(parent_charter)
    replacements = sorted(p for p in NORM_PRIMITIVE_CATALOG if p not in used)
    if replacements and parent_charter:
        # 교체 인덱스: tick 결정성 활용 (sorted 안정)
        replace_idx = self.time.tick % len(parent_charter)
        parent_charter[replace_idx] = replacements[0]
    new_charter = tuple(parent_charter) if parent_charter else ("외세_배척", "능력주의", "자연_경외")
    # founder_lineage: 부모 lineage + 부모 fid 추가
    new_lineage = (*parent.founder_lineage, parent_fid)
    new_id = f"f-r-{founder_pid}-{self.time.tick}"        # rebel branch ID
    self.factions[new_id] = Faction(
        id=new_id,
        name=f"Rebels of {parent.name}",
        founder_pid=founder_pid,
        charter=new_charter,
        created_tick=self.time.tick,
        grace_until_tick=self.time.tick + RESPAWN_GRACE_TICKS,
        founder_lineage=new_lineage,
    )
    self._faction_members_cache = {}
    self.event_log.append({
        "type": "faction_spawn",
        "tick": self.time.tick,
        "fid": new_id,
        "source": "uprising_branch",
        "parent_fid": parent_fid,
        "founder_pid": founder_pid,
    })
    return new_id
```

**근거**:
- charter 변형: 부모 primitive 1개 교체. 12개 카탈로그 중 부모에 없는 첫 sorted primitive로 (결정성). 교체 인덱스는 `tick % len`으로 결정성 + 다양성 동시 확보
- charter 길이 보존: Faction `__post_init__`이 [3,5] 검증 → 1개 교체로 길이 변동 0
- charter 중복 검사: 교체 후에도 unique (replacements ⊂ NORM - parent set)
- Edge case: `parent_charter` 비어 있을 수 없음 (Faction __post_init__이 보장). 안전장치로 `("외세_배척", "능력주의", "자연_경외")` 폴백 — 실제로는 도달 불가
- `founder_lineage`: Stage 6 H-lite 패턴. 분파 추적 + drift 감쇠 (Stage 6 W_LINEAGE=0.2 효과 자동 계승)
- `grace_until_tick`: Stage 5 RESPAWN_GRACE_TICKS=200. 신생 분파가 즉시 모 faction에 재흡수되는 second-collapse 방지
- ID 형식: `f-r-` prefix로 rebel branch 식별 가능
- **ID 충돌 정정 (hotfix v1)**: `founder_pid[:6]`은 모든 페르소나가 같은 prefix를 가지면 충돌(예: `persona_001` ~ `persona_999`). 본 명세는 `founder_pid` 풀 ID 사용으로 정정.
- **Charter 폴백 길이 정정 (hotfix v1)**: 폴백 `("외세_배척",)`(1개)은 `Faction.__post_init__` charter 길이 [3,5] 검증 위반. 안전장치로 3-primitive 폴백(실제 도달 불가, 검증 통과 보장)으로 정정.

---

## D6. 분파 신규 faction의 territory 시작점

**결정**: leader 거주 territory에서 시작. 신규 faction은 별도 territory 점유 X.

**구현**:
- `_spawn_branch_faction` 자체는 territory에 손대지 않음
- 봉기 발화 후 `_change_persona_faction(leader_pid, new_fid, source="conflict")` → 다음 24틱 `_project_faction_dominance` (Charter v2 §6) double-buffer commit에서 territory.factionRef 자연 갱신
- leader + followers의 거주 territory에서 분파가 자연 dominant 갱신 (Counter+히스테리시스)

**근거**: 무파괴 9 보장 §7 (공허 정합) 유지. factionRef 직접 mutation 금지. 24틱 commit 경로만 사용.

---

## D7. metrics.jsonl 신규 type "uprising" schema

```json
{
  "tick": 1488,
  "type": "uprising",
  "leader_pid": "p-a3f81c",
  "from_faction": "f-seed-2",
  "target_faction": "f-r-a3f81c-1488",
  "branch": true,
  "lord_id": "p-lord-9d2",
  "members_count": 3,
  "grievance_mean": 0.812,
  "resonance_score": 0.487
}
```

| 필드 | 타입 | 의미 |
|------|------|------|
| `tick` | int | 발화 tick |
| `type` | "uprising" | freeze |
| `leader_pid` | str | 봉기 주도자 |
| `from_faction` | str | 출신 faction |
| `target_faction` | str | 가입 faction (분파면 신규 ID) |
| `branch` | bool | 분파 신규 생성 여부 |
| `lord_id` | str | grievance 대상 영주 |
| `members_count` | int | leader + followers 합 |
| `grievance_mean` | float (3 decimal) | 봉기 그룹 평균 grievance |
| `resonance_score` | float (3 decimal) | trigger 시점 응결 강도 |

기존 5종 type (`population`, `contact`, `wealth`, `grievance_targets`, `source_cumulative`) 무수정.

---

## D8. Φ-3 SUMMARY.md primary 분리 형식

Stage 5/6 패턴 그대로 계승. acceptance 3종 + 측정값 표.

```markdown
# Phase 17 Φ-3 Struggle — probe SUMMARY

> 측정: phase17_probe_phi3 / 3 seed (7, 13, 42) × 5000 tick
> Charter: PHASE-17-STRUGGLE-CHARTER.md
> 측정 시각: <YYYY-MM-DD>

## Primary Acceptance (3종)

| # | 기준 | seed 7 | seed 13 | seed 42 | 결과 |
|---|------|:------:|:-------:|:-------:|:----:|
| 1 | uprising_event ≥ 1 | <count> | <count> | <count> | <PASS/FAIL> |
| 2 | grievance_pairs_end ≥ 1 | <count> | <count> | <count> | <PASS/FAIL> |
| 3 | dom_share_end ≥ 0.50 | <%> | <%> | <%> | <PASS/FAIL> |

## Secondary Metrics (Stage 6 계승)

| 항목 | seed 7 | seed 13 | seed 42 |
|------|:------:|:-------:|:-------:|
| active_factions_end | | | |
| min_active_1000to5000 | | | |
| drift_ratio | | | |
| gini@5000 mean | | | |
| branch_factions_total | | | |
| uprising_branch_share | | | |
| uprising_join_share | | | |

## 결정성

`five_channel_determinism` PASS / FAIL — seed=42 5000틱 2회 실행 hash 일치 여부.

## Φ-4 진입 자격 OR 조건 (Charter v2 → Φ-4)

(Φ-3 closure 시 다음 OR 조건을 측정. Φ-4 Charter는 별도)
```

---

## D9. 검증 계약 추가 사항 (Charter §7 보강)

Charter §7 검증 계약 11종에 다음 보강:

12. **uprising 무사망 보장**: probe 5000틱 시점 `population_total_end == population_total_start`. Φ-3는 멤버 이동만, 사망 X (Charter §Baseline 제외 항목과 정합).
13. **봉기 cooldown 정합**: `_emit_uprising` 호출 후 leader+followers의 `faction_cooldown == FACTION_COOLDOWN_TICKS`.
14. **branch lineage 검증**: 분파 신규 faction의 `founder_lineage`에 부모 fid 포함. `len(branch.founder_lineage) >= 1` (parent_lineage + parent_fid).
15. **결정성 hash 추가**: `phi2_phi3_hash = hash((sorted(personas, key=...), sorted(factions, ...), sorted(uprising_events, ...)))` — `test_phase17_acceptance.py`에 추가.
16. **AST whitelist 강제**: `# noqa: PHASE17_FACTION_SSOT_WRITE` 마커 line 수가 **5건 그대로** (현 multi_tick_engine.py:1068, 1069 등). Φ-3 신규 마커 추가 0건.

---

## D10. tick() 통합 정확 위치

multi_tick_engine.py 현재 구조:
- line 2175: `self._respawn_faction_tick()  # Stage 3 C: absorbing state 탈출`

**Φ-3 통합 (1줄 추가)**:
```python
self._respawn_faction_tick()
self._uprising_tick()       # Phase 17 Φ-3 신규
```

`_uprising_tick()` 내부:
```python
def _uprising_tick(self) -> None:
    """24/48틱 주기 봉기 검사 + 발화. read-only handoff API 호출."""
    candidates = self._uprising_trigger()
    for c in candidates:
        self._emit_uprising(c)
```

---

## D11. 보류 제로 — Phase 4 Verify 진입 자격

12 보류 항목 모두 초기값 + 수식 확정. **Phase 3 Decision Card 종료**. Phase 4 Verify (결정성·성능·무파괴·acceptance 3종 검증)는 Codex 구현 후 probe 측정으로 진행.

---

## 다음 단계

1. **`/spec`으로 Codex 지시서 작성** — `PHASE-17-STRUGGLE-CODEX-INSTRUCTIONS.md` (본 Decision Card + Charter를 통합한 구현 계약)
2. **Codex 구현** — 기능(백엔드) 작업 유형. 변경 파일: `layers.py` (상수 5종), `core/multi_tick_engine.py` (신규 6 메서드 + tick 통합 1줄)
3. **probe** — 3 seed × 5000 tick → SUMMARY 자동 생성
4. **closure** — acceptance 3종 PASS 시 `test_phase17_acceptance.py` 확장 + Φ-3 closure 선언
