# Phase 14B SNN Output Circuit — 데이터 정당화 사슬 진단 Spec (d-1)

> 긴급도: 높음
> 선행 조건: Phase 17 Φ-3 Case-C P1+P2 SPEC v2 종결 (PARTIAL_PROGRESS, acceptance #2 빈도 1/3 → 2/3) + Phase 14B-A axis A 기각 + Case C collapse 진단 종결
> 작업 유형: **진단 (instrumentation + measurement)**. mechanism 로직 변경 없음. event_log 텔레메트리 보강만.
> DB migration: 없음
> 외부 의존: 없음
> 분리 정책: 본 spec은 **데이터 수집·분석만**. SNN 결합 패치 spec은 본 진단 보고서 작성 + 3엔진 cross-check 후 별도 작성 (d-4 단계).

---

## 1. 배경 — 근본 원인 5단 추적

### 1.1 3계층 목표 (loom 정신 명시)

`feedback_loom_goal_first.md`:
- **궁극 목표**: 자율 사회 시뮬 + **SNN 창발**(규칙 < 창발) + **PersonaBrain 논문 출판**
- **Phase 17 목적**: 사회 **자연 발생** (top-down 선언 금지). Φ-1 Land → Φ-2 Faction → Φ-3 Struggle → Φ-4 Nation 인과 사슬
- **본 spec 고유 역할**: Phase 14B 출력 회로(SNN → faction lifecycle 결정)의 **데이터 정당화 사슬 표준**을 정착시키는 진단 단계. 안티패턴 #3 (SNN gate 정당화 부재) 회피의 방법론.

### 1.2 근본 원인 5단 추적 (꼬리에 꼬리)

| 단계 | 질문 | 답 |
|:----:|------|------|
| 표면 | 왜 acceptance #2 (`grievance_pairs_end ≥ 1`) FAIL 빈도 높나? | 봉기가 발화 못 하거나 발화 후 새 faction 형성 못 함 |
| 1단 | 왜 봉기 발화/지속 실패? | contact graph 0쌍 붕괴 + founder 흡수 압력 (Case C 진단 root cause) |
| 2단 | 왜 contact graph 붕괴? | majority faction이 모든 territory 흡수 → 단일 faction → `factions_in_contact = 0쌍` |
| 3단 | 왜 majority가 모든 territory 흡수? | `_compute_affiliation_tick`에서 territory 가중치 + drift 마진이 small faction 보호 부족. `MINORITY_PERSISTENCE_BOOST=0.20`도 부분 효과 (PARTIAL_PROGRESS 1/3 → 2/3) |
| 4단 | 왜 minority boost가 부분 효과만? | **boost는 정적 임계** — "size ≤ 2"만 보고 일률 보호. **"누구를 보호할 것인가"의 동적 신호(SNN)가 mechanism에 결합 안 됨** |
| 5단 | 왜 SNN 출력이 faction lifecycle에 결합 안 됨? | Phase 14B 본래 의도는 **입력 회로 강화** (test_phase14b_snn_integration.py 8/8 PASS). **출력 회로**(SNN → mechanism 결정)는 axis A로 시도했으나 거짓 PASS 5건과 구조 동형 → 기각. **출력 회로 설계 자체 정체** |
| **근본 원인** | 왜 출력 회로 설계가 정체? | **데이터 정당화 사슬 표준이 미설계**. axis A는 `anger ≥ 0.5 → dampen`을 데이터 없이 즉답함 → 안티패턴 #3 직격 → 거짓 PASS 동형 비판 회피 불가. **"자연 측정 → 결합점 식별 → 임계 정당화"의 표준 사슬이 LOOM-DIRECTION.md에 명시되지 않음** |

### 1.3 본 spec의 위치

- **거짓 PASS 5건 + axis A 기각 + Case C "연결·지속성 실패"가 모두 동일 근본 원인의 표면**: 데이터 정당화 사슬 표준 부재 → mechanism 결정에 임의 임계 도입 → 자연 발생 가장 + acceptance 우회.
- **본 spec은 단순 telemetry 추가가 아닌 "Phase 14B 출력 회로 정당화 사슬"의 표준 정착**.
- 본 spec 부산물로 LOOM-DIRECTION.md에 §2.6 또는 신규 §3 "출력 회로 데이터 정당화 사슬 표준" 추가 권고.

### 1.4 현재 SNN 출력 결합 매핑 (선행 조사 결과)

**이미 결합된 영역 (3곳)**:

| 영역 | 위치 | SNN 신호 | 결정 |
|------|------|---------|------|
| 봉기 leader 검사 | `_snn_uprising_signal_active` → `_uprising_trigger:2035` | chiljeong[1] / chiljeong[3] / oyok[4] | leader 발화 게이트 (단 1명만) |
| territory 정책 | `_compute_territory_policy_tick:2982-3014` | drive/tension/stability/dominance/growth/greed/density_pressure | tax_rate, market_openness 등 |
| public works | `_apply_public_works_tick:4040-4296` | growth/tension/stability + hunger | hire rate, food_crisis, parttime |

**결합되지 않은 영역 (4곳, faction lifecycle 차원)**:

| 영역 | 위치 | 현재 read 변수 | SNN read |
|------|------|--------------|---------|
| affiliation score | `_compute_affiliation_tick:1219-1292` | territory/trust/grievance/proximity/lineage + 정적 boost 3종 | **없음** ← axis A 후보 (REJECTED) |
| uprising target 선택 | `_pick_uprising_target:1926-1952` | neighbor_tids, territory_dist | **없음** |
| founder respawn | `_respawn_faction_tick:1339~` | free_residents 수, lord_id | **없음** |
| uprising follower 선정 | `_select_uprising_followers:1954-1968` | grievance_lord_id, grievance | **없음** (anger·dignity 미반영) |

**핵심 통찰**: SNN 결합은 **economy/policy/uprising leader 1명**까지 진행됐으나 **faction lifecycle 자체 결정**(spawn/grow/follow/collapse)에는 부재. Case C root cause "연결·지속성 실패"가 정확히 이 빈 영역에서 발생.

### 1.5 본 spec의 데이터 가설

각 가설은 데이터로 반증 가능. PASS = SNN 결합 가능성 입증, FAIL = 해당 결합점 부적합:

| 가설 | 의도 | 반증 데이터 (있으면 가설 기각) |
|------|------|------------------------------|
| **G1** | uprising 발화 시점에 leader 외 follower 후보들의 SNN 분포가 **bimodal** (gate pass / fail 명확 분리) | 봉기 시점 follower 후보 SNN이 단일 모드 (gate 의미 없음) |
| **G2** | founder 흡수 시점에 founder의 chronic_stress가 흡수 직전 일정 수준 이상 누적 | founder SNN이 흡수 직전과 비흡수 founder의 평소 SNN 분포 동일 (SNN 무관 흡수) |
| **G3** | small faction 멤버들의 평균 SNN 신호가 **소멸하는 small faction**과 **유지되는 small faction** 사이에 통계 유의미 차이 | 두 그룹 SNN 분포 동일 (SNN으로 보호 대상 식별 불가) |
| **G4** | territory tension(이미 결합된 신호)이 founder respawn 시점·우선순위에 자연 결합 가능 | tension 분포가 territory 간 평탄 (priority 결정 변수로 부적합) |

**진단의 출력**:
1. 4 가설(G1~G4)의 PASS/FAIL + 측정 데이터
2. **자연 결합점 후보 식별** (PASS 가설마다 결합 mechanism 명시)
3. **각 후보의 임계 후보값** (자연 측정 분포의 N 분위수 — 임의 0.5 같은 magic number 사용 금지)
4. 3엔진 cross-check 입력으로 사용할 data summary

---

## 2. 작업 범위

### [필수]

1. `core/multi_tick_engine.py`에 **read-only 텔레메트리 이벤트** 4종 추가 (mechanism 변경 없음)
2. `observe_phase17_emergence.py`에 SNN 분포 분석 섹션 추가 (영지별·시점별 SNN 분포 + 가설별 PASS/FAIL 집계)
3. `data/phase17_probe_phi3-snn-output-diagnosis/` 신규 디렉토리에 3 seed × 5000 tick 진단 결과 저장
4. `PHASE-14B-SNN-OUTPUT-DIAGNOSIS-REPORT.md` 작성 — 4 가설 PASS/FAIL + 자연 결합점 후보 + 각 후보의 임계 후보값(분위수)

### [선택]

- (보고서가 단일 결합점으로 수렴하지 않을 경우) 추가 텔레메트리 후속 진단 spec 분리 권고
- LOOM-DIRECTION.md §2.6 또는 §3 "출력 회로 데이터 정당화 사슬 표준" 추가안 (별도 문서 권고)

### [금지]

- **mechanism 로직 변경 절대 금지** — `_compute_affiliation_tick`, `_uprising_trigger`, `_emit_uprising`, `_respawn_faction_tick`, `_change_persona_faction`, `_select_uprising_followers`, `_pick_uprising_target`, `_snn_uprising_signal_active` 본문 무수정
- **상수 값 변경 금지** — Stage 1/2/3/5/6 + Φ-3 + Phase 14 + SPEC-V2 상수 (MINORITY_PERSISTENCE_BOOST=0.20 포함) 전부 동결
- **무파괴 9 보장 계승** — Phase 14 spec §[금지]와 동일
- **신규 FactionChangeSource 추가 금지** — 4종 고정 (`birth_founder | affiliation | drift | conflict`)
- **acceptance 기준 완화 금지** — 본 spec은 acceptance를 손대지 않음 (진단만)
- **신규 SNN 뉴런 추가 금지** — 기존 chiljeong[7] / oyok[6] / chronic_stress 만 read
- **임의 임계 도입 금지** — 본 spec은 분포 측정만. 임계는 보고서 단계에서 분위수로만 제안 (예: "P75 = 0.43" 같은 데이터 도출값. magic number 0.5 등 금지)
- **회귀 테스트 7종 무수정** — test_economy.py / test_governance.py / test_class_promotion.py / test_nomos.py / test_phase17_faction_handoff_contract.py / test_phase14b_snn_integration.py / test_phase17_faction_stage3.py 본문 무수정 (telemetry 추가는 새 이벤트만이므로 기존 assert 침범 0)

---

## 3. 구체 사양

### 3.1 텔레메트리 이벤트 4종 (`core/multi_tick_engine.py`)

각 이벤트는 `self.event_log.append(...)`만 추가. **logic 분기 없음**. 모두 [기존 코드 위치]의 if/return 직후나 직전에 텔레메트리만 삽입.

#### Event 1: `uprising_leader_snn_snapshot` (가설 G1 검증)

**삽입 위치**: `_uprising_trigger` 내 leader 후보 식별 직후, SNN gate 검사 전후 (현 [multi_tick_engine.py:2034-2039](core/multi_tick_engine.py#L2034-L2039) 구간 확장).

**개념적 위치**:

```python
# 기존 코드 (보존):
eligible.sort(key=lambda p: (-float(self.inners[p].grievance), p))
leader_pid = eligible[0]
gate_passed = self._snn_uprising_signal_active(leader_pid)

# [APPEND] 텔레메트리 — gate pass + skip 모두 기록 (gate 분포 측정용)
leader_inner = self.inners[leader_pid]
follower_candidates_pids = eligible[1:UPRISING_FOLLOWER_MAX + 1]
follower_snn = []
for fpid in follower_candidates_pids:
    finner = self.inners[fpid]
    follower_snn.append({
        "pid": fpid,
        "anger": float(finner.chiljeong[1]),
        "fear": float(finner.chiljeong[3]),
        "dignity": float(finner.oyok[4]),
        "chronic_stress": float(finner.chronic_stress),
        "grievance": float(finner.grievance),
    })
self.event_log.append({
    "type": "uprising_leader_snn_snapshot",
    "tick": self.time.tick,
    "fid": fid,
    "leader_pid": leader_pid,
    "gate_passed": gate_passed,
    "leader_anger": float(leader_inner.chiljeong[1]),
    "leader_fear": float(leader_inner.chiljeong[3]),
    "leader_dignity": float(leader_inner.oyok[4]),
    "leader_chronic_stress": float(leader_inner.chronic_stress),
    "leader_grievance": float(leader_inner.grievance),
    "follower_candidates": follower_snn,
    "resonance_score": float(reso["resonance_score"]),
    "top_lord_id": top_lord,
})

# 기존 코드 (보존):
if not gate_passed:
    self.event_log.append({"type": "uprising_skip_snn_inactive", ...})  # 기존 SPEC-V2 telemetry
    continue
```

**측정 의도**: 봉기 발화 후보 시점에 leader + follower 후보의 SNN 신호 분포를 기록. G1 PASS 시 gate_passed=True 그룹과 False 그룹의 SNN 분포가 분리됨. follower 후보의 SNN 분포를 통해 axis C' (follower SNN 결합) 자연 결합점 후보 식별.

**조건**: 본 telemetry는 gate 검사 직전이므로 gate_passed=True/False 분기와 무관하게 leader 후보가 식별된 모든 시점에서 발화. `if not eligible: continue` 분기 이후이므로 leader 미식별 시 발화 안 됨 (자연 차단).

#### Event 2: `founder_absorbed_snn_snapshot` (가설 G2 검증)

**삽입 위치**: `_change_persona_faction` 본문 내 기존 `drift_recovery_to_minority` 분기 닫힌 후 ([multi_tick_engine.py:1094](core/multi_tick_engine.py#L1094) 직후). `event_log.append({"type": "faction_change", ...})`는 line 1077~1084에 있고, line 1085~1094는 기존 SPEC-V2의 `drift_recovery_to_minority` 분기 (보존 대상). Event 2는 그 분기 닫힌 후 메서드 본문 indent 8 spaces로 삽입.

**개념적 위치**:

```python
# 기존 코드 (line 1077~1084, 보존):
self.event_log.append({
    "type": "faction_change",
    "tick": self.time.tick,
    "pid": pid,
    "from_faction": prev,
    "to_faction": new_faction_id,
    "source": source,
})
# 기존 코드 (line 1085~1094, SPEC-V2 telemetry, 보존):
if source == "drift" and new_faction_id is not None:
    new_member_count = len(self._faction_members_cache.get(new_faction_id, ())) + 1
    if new_member_count <= MINORITY_PERSISTENCE_MAX_MEMBERS + 1:
        self.event_log.append({
            "type": "drift_recovery_to_minority",
            "tick": self.time.tick,
            "pid": pid,
            "to_faction": new_faction_id,
            "new_member_count": new_member_count,
        })

# [APPEND] founder 흡수 추적 — pid가 prev faction의 founder였던 경우만 (line 1094 직후)
prev_faction_obj = self.factions.get(prev) if prev is not None else None
if (
    prev_faction_obj is not None
    and prev_faction_obj.founder_pid == pid
    and source in ("affiliation", "drift")
    and new_faction_id is not None
    and new_faction_id != prev
):
    founder_inner = self.inners[pid]
    new_faction_members = self._faction_members_cache.get(new_faction_id, ())
    if new_faction_members:
        avg_anger = float(np.mean([float(self.inners[m.id].chiljeong[1]) for m in new_faction_members]))
        avg_fear = float(np.mean([float(self.inners[m.id].chiljeong[3]) for m in new_faction_members]))
        avg_dignity = float(np.mean([float(self.inners[m.id].oyok[4]) for m in new_faction_members]))
        avg_chronic = float(np.mean([float(self.inners[m.id].chronic_stress) for m in new_faction_members]))
    else:
        avg_anger = avg_fear = avg_dignity = avg_chronic = 0.0
    self.event_log.append({
        "type": "founder_absorbed_snn_snapshot",
        "tick": self.time.tick,
        "founder_pid": pid,
        "from_faction": prev,
        "to_faction": new_faction_id,
        "source": source,
        "founder_anger": float(founder_inner.chiljeong[1]),
        "founder_fear": float(founder_inner.chiljeong[3]),
        "founder_dignity": float(founder_inner.oyok[4]),
        "founder_chronic_stress": float(founder_inner.chronic_stress),
        "founder_grievance": float(founder_inner.grievance),
        "absorbing_faction_avg_anger": avg_anger,
        "absorbing_faction_avg_fear": avg_fear,
        "absorbing_faction_avg_dignity": avg_dignity,
        "absorbing_faction_avg_chronic": avg_chronic,
        "absorbing_faction_size": len(new_faction_members),
        "from_faction_size_at_absorb": len(self._faction_members_cache.get(prev, ())),
    })
```

**측정 의도**: founder가 다른 faction에 흡수되는 시점의 SNN 신호 분포를 기록. G2 PASS 시 흡수 직전 founder의 chronic_stress 또는 grievance가 비흡수 founder 대비 유의미하게 높음 → axis E' (founder 안정화 SNN 결합) 자연 결합점 후보 식별.

**중복 방지**: source가 `birth_founder` 또는 `conflict` (봉기)이거나 founder가 아닌 일반 멤버는 발화 안 됨. founder 흡수 케이스만.

#### Event 3: `small_faction_snn_snapshot` (가설 G3 검증)

**삽입 위치**: `_compute_affiliation_tick` 내 boost 적용 분기 직후 ([multi_tick_engine.py:1255](core/multi_tick_engine.py#L1255) 직후), 단 `tick % FACTION_COMMIT_EVERY == 0` 조건으로 빈도 제어.

**중복 방지 first_pid는 메서드 진입 시 1회만 계산** (기존 SPEC-V2 telemetry 패턴 계승):

```python
def _compute_affiliation_tick(self) -> None:
    self._rebuild_faction_members_cache()
    total_active = max(1, sum(1 for pid in self.personas if pid in self.inners))
    new_scores: dict[str, dict[str, float]] = {}
    diagnostic_first_pid = min(self.personas, default=None)  # 기존 SPEC-V2 telemetry용 (보존)

    for pid in sorted(self.personas):
        # ... 기존 코드 ...
        for fid in sorted(self.factions):
            # ... 기존 score 계산 ...
            if 0 < member_count <= MINORITY_PERSISTENCE_MAX_MEMBERS:
                if self._same_territory(persona, fid) > 0.5:
                    score += MINORITY_PERSISTENCE_BOOST
                    if pid == diagnostic_first_pid:
                        # 기존 minority_boost_applied (보존)
                        self.event_log.append({"type": "minority_boost_applied", ...})

                        # [APPEND] small_faction_snn_snapshot — 48틱 주기 + first_pid 1회만
                        if self.time.tick % FACTION_COMMIT_EVERY == 0:
                            members = self._faction_members_cache.get(fid, ())
                            if members:
                                snn_dist = []
                                for m in members:
                                    minner = self.inners[m.id]
                                    snn_dist.append({
                                        "pid": m.id,
                                        "anger": float(minner.chiljeong[1]),
                                        "fear": float(minner.chiljeong[3]),
                                        "dignity": float(minner.oyok[4]),
                                        "chronic_stress": float(minner.chronic_stress),
                                        "grievance": float(minner.grievance),
                                    })
                                self.event_log.append({
                                    "type": "small_faction_snn_snapshot",
                                    "tick": self.time.tick,
                                    "fid": fid,
                                    "member_count": member_count,
                                    "members_snn": snn_dist,
                                })
            # ... 기존 lineage 등 ...
```

**측정 의도**: small faction(size ≤ 2) 멤버들의 SNN 분포를 정기 스냅샷. 보고서 분석 단계에서 "tick T 시점에 small faction X의 멤버 SNN 분포" → "그 faction이 200틱 내 소멸했나 유지했나"로 G3 PASS/FAIL 판정.

**중복 방지 규칙**: `diagnostic_first_pid`로 tick·fid 당 1회만 발화 (기존 SPEC-V2 패턴). 추가로 `tick % FACTION_COMMIT_EVERY == 0` 조건으로 48틱 주기 제어 (5000틱 / 48틱 ≈ 104 snapshot per fid).

#### Event 4: `territory_snn_distribution` (가설 G4 검증)

**삽입 위치**: `tick()` 메서드 본문, [multi_tick_engine.py:2636](core/multi_tick_engine.py#L2636) 직후 (Case C 진단 spec의 `active_factions_snapshot` append 닫힌 후, line 2637 `return events` 직전 — 메서드 본문 indent 8 spaces).

**개념적 위치 (Case C 진단의 active_factions_snapshot 직후, 별도 % 100 주기 분기로 추가)**:

```python
        # 기존 (Case C 진단으로 line 2623~2636에 추가됨 — 보존):
        if self.time.tick > 0 and self.time.tick % 500 == 0:
            self.event_log.append({
                "type": "active_factions_snapshot",
                # ... (보존)
            })

        # [APPEND] territory_snn_distribution — 100틱 주기 (line 2636 직후, return events 직전)
        if self.time.tick > 0 and self.time.tick % 100 == 0:
            for tid, territory in self.territories.items():
                residents = [
                    p for p in self.personas.values()
                    if p.territory == tid and p.id in self.inners
                ]
                if not residents:
                    continue
                residents_inners = [self.inners[p.id] for p in residents]
                snn_payload = {
                    "type": "territory_snn_distribution",
                    "tick": self.time.tick,
                    "territory_id": tid,
                    "resident_count": len(residents),
                    "lord_id": territory.lord_id,
                    "avg_anger": float(np.mean([float(i.chiljeong[1]) for i in residents_inners])),
                    "avg_fear": float(np.mean([float(i.chiljeong[3]) for i in residents_inners])),
                    "avg_dignity": float(np.mean([float(i.oyok[4]) for i in residents_inners])),
                    "avg_chronic_stress": float(np.mean([i.chronic_stress for i in residents_inners])),
                    "avg_grievance": float(np.mean([float(i.grievance) for i in residents_inners])),
                    "active_faction_count_in_territory": len(set(
                        p.faction for p in residents if p.faction is not None
                    )),
                }
                if territory.last_snn_signals_tick >= 0:
                    snn_payload["territory_snn_tension"] = float(
                        territory.last_snn_signals.get("tension", 0.0)
                    )
                    snn_payload["territory_snn_growth"] = float(
                        territory.last_snn_signals.get("growth", 0.0)
                    )
                    snn_payload["territory_snn_signal_age"] = self.time.tick - territory.last_snn_signals_tick
                self.event_log.append(snn_payload)

        return events
```

**측정 의도**: territory별 SNN 분포 시계열 + 기존 territory.last_snn_signals 값과의 상관 측정. G4 PASS 시 tension 분포에 territory 간 유의미한 분산 존재 → axis D' (founder respawn priority에 territory tension 자연 결합) 자연 결합점 후보 식별.

**100틱 주기**: 5000틱 ÷ 100 = 50 snapshot per territory (territory 5개 가정 시 250개 이벤트). 너무 자주 발화하면 chain.json 비대 → 100틱이 분포 변화 추적에 충분 + 데이터량 적정.

### 3.2 진단 분석 섹션 (`observe_phase17_emergence.py`)

기존 SUMMARY.md 출력 직후 별도 섹션 추가. 4개 텔레메트리 이벤트를 집계.

**삽입 위치**: probe 결과 출력 함수의 SUMMARY.md 작성 부분에 `phase14b_snn_output_diagnosis` 섹션 append.

**출력 형식 (각 seed별)**:
```markdown
## Phase 14B SNN Output Diagnosis (per seed)

### seed N

| 가설 | 측정 | 결과 |
|------|------|------|
| G1 (uprising leader/follower SNN bimodal) | gate_passed=True 그룹 vs False 그룹의 SNN 분포 KS-test p-value | PASS (p<0.05) / FAIL |
| G2 (founder 흡수 시 SNN 차이) | founder_absorbed의 founder_chronic vs 비흡수 founder 평균 chronic 차 | PASS (mean_diff > 1σ) / FAIL |
| G3 (small faction 소멸 vs 유지 SNN 차이) | 200틱 내 size=0 도달 그룹 vs 유지 그룹 SNN 분포 차 | PASS (mean_diff > 1σ) / FAIL |
| G4 (territory tension 분산) | territory 간 avg_anger/avg_chronic 분산 (CV: std/mean) | PASS (CV ≥ 0.2) / FAIL |

### G1 데이터 — uprising leader/follower SNN 분포

| 그룹 | leader_anger 평균 | leader_chronic 평균 | follower 평균 anger | n |
|------|:---:|:---:|:---:|:--:|
| gate_passed=True | M | M | M | N |
| gate_passed=False | M | M | M | N |

### G2 데이터 — founder 흡수 시점 SNN

| 케이스 | 평균 founder chronic | 평균 founder grievance | 평균 absorbing_size | n |
|--------|:---:|:---:|:---:|:--:|
| 흡수 (source=affiliation/drift) | M | M | M | N |
| 비흡수 (대조: faction 유지 founder의 평균 SNN) | M | M | M | N |

### G3 데이터 — small faction 200틱 추이

| small faction 그룹 | 평균 anger | 평균 chronic | 평균 grievance | 200틱 후 size=0 비율 | n |
|--------|:---:|:---:|:---:|:---:|:--:|
| 소멸 그룹 | M | M | M | 100% | N |
| 유지 그룹 | M | M | M | 0% | N |

### G4 데이터 — territory SNN 분산

| territory_id | avg_anger 평균 | avg_chronic 평균 | territory_snn_tension 평균 | resident_count |
|--------|:---:|:---:|:---:|:--:|
| t-1 | M | M | M | N |
| ... | ... | ... | ... | ... |

CV(avg_anger) = std / mean = X.XX

### 자연 결합점 후보 (PASS 가설별)

- G1 PASS → axis B'/C' 후보 (uprising target/follower 선정 시 SNN 결합)
  - 임계 후보값: gate_passed=True 그룹 leader_chronic의 P25 = X.XX
- G2 PASS → axis E' 후보 (founder 안정화 SNN 결합)
  - 임계 후보값: 흡수 founder chronic의 P75 = X.XX
- G3 PASS → axis F' 후보 (minority boost 동적화)
  - 임계 후보값: 소멸 그룹 평균 anger와 유지 그룹 평균 anger의 중간점 = X.XX
- G4 PASS → axis D' 후보 (founder respawn priority에 territory tension 결합)
  - 임계 후보값: territory tension의 P75 = X.XX
```

**집계 로직**:
- `uprising_leader_snn_snapshot` 이벤트 그룹화: gate_passed=True/False 분리 → SNN 분포 비교
- `founder_absorbed_snn_snapshot` 이벤트 + 비흡수 founder 비교군: 흡수 시점 founder SNN vs 비흡수 founder의 평균 SNN
- `small_faction_snn_snapshot` 이벤트 → 각 (tick, fid) 시점부터 200틱 내 size=0 도달 추적 (Case C 진단의 H3 추적 패턴 계승)
- `territory_snn_distribution` 이벤트 → territory별 시계열 → CV 계산

### 3.3 진단 디렉토리 (`data/phase17_probe_phi3-snn-output-diagnosis/`)

`.gitignore` 패턴 `data/phase17_probe*/` 자동 매칭됨.

**구조**:
```
data/phase17_probe_phi3-snn-output-diagnosis/
├── SUMMARY.md                       # 기존 형식 + Phase 14B SNN Output Diagnosis 섹션
├── seed-7/
│   ├── chain.json                   # 전체 event_log
│   └── snn_output_events.json       # 4종 텔레메트리 이벤트 추출본 (분석 편의)
├── seed-13/...
└── seed-42/...
```

### 3.4 진단 보고서 (`PHASE-14B-SNN-OUTPUT-DIAGNOSIS-REPORT.md`)

**필수 섹션**:
1. 요약 — 4 가설 PASS/FAIL 결과 표
2. 가설별 데이터 — 각 seed의 분포·차이·통계
3. **자연 결합점 후보 식별** — PASS 가설마다 자연 결합 mechanism 후보 명시 + **각 후보의 임계 후보값(분위수)**
4. **3엔진 cross-check 입력** — 각 후보별 자연 측정 데이터 요약 (axis A 함정 회피 검증용)
5. **다음 단계 권고**:
   - 단일 PASS 후보 → 해당 axis로 직접 d-4 spec 작성 (cross-check 후)
   - 다중 PASS 후보 → 우선순위 권고 (acceptance #2 대응력 + SNN 창발 정신 부합도 + 구현 비용)
   - 모두 FAIL → axis 전환 보류, d-3 territory cross-propagation 강화로 우회 권고
6. **데이터 정당화 사슬 표준** (LOOM-DIRECTION.md 추가 권고 초안):
   - 표준 사슬 6단계: 자연 측정 → 분포 분석 → PASS/FAIL 판정 → 결합점 후보 식별 → 임계 후보값 (분위수) → 3엔진 cross-check
   - 임의 임계 도입 금지 (magic number 0.5 등)

**진단의 가치**:
- 본 spec은 acceptance #2를 직접 풀지 않음
- 데이터로 SNN 출력 결합점을 확정한 뒤 자연 mechanism 설계 단계로 진입
- axis A 거짓 PASS 함정 사전 차단 (역공학 회피)
- LOOM-DIRECTION.md 데이터 정당화 사슬 표준 정착 (방법론적 부산물)

---

## 4. 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `core/multi_tick_engine.py` | telemetry 4종 append (mechanism 무수정) | 수정 |
| `observe_phase17_emergence.py` | SUMMARY.md 출력에 SNN Output Diagnosis 섹션 추가 | 수정 |
| `data/phase17_probe_phi3-snn-output-diagnosis/SUMMARY.md` | 자연 측정 결과 (probe 실행 산출물) | 신규 |
| `data/phase17_probe_phi3-snn-output-diagnosis/seed-{7,13,42}/chain.json` | 전체 event_log (probe 실행 산출물) | 신규 |
| `data/phase17_probe_phi3-snn-output-diagnosis/seed-{7,13,42}/snn_output_events.json` | telemetry 추출본 (분석 편의) | 신규 |
| `PHASE-14B-SNN-OUTPUT-DIAGNOSIS-REPORT.md` | 진단 보고서 본체 | 신규 |

**변경 없음 (금지):**
- `core/multi_tick_engine.py`의 mechanism 함수 본문 (Section 1.4 표 7개 함수 + 그 외 Phase 11~16 경제 함수)
- `ontology/layers.py` 본문 (상수 / 클래스 / SNN 뉴런 정의)
- `brain/**` 전부 (PersonaBrain SSoT)
- `physis/**` 전부 (territory 인프라)
- `tests/**` 회귀 7종 본문 (test_economy/governance/class_promotion/nomos/phase17_faction_handoff_contract/phase14b_snn_integration/phase17_faction_stage3)
- `PHASE-17-CASE-C-P1-P2-SPEC-V2.md` (선행 종결 spec)
- `LOOM-DIRECTION.md` (본 spec에서는 미수정. 보고서 단계에서 §2.6/§3 추가 권고만)

---

## 5. 검증

### 5.1 기계 검증 (필수)

1. `py -m py_compile Projects/personas/loom/core/multi_tick_engine.py` → PASS
2. `py -m py_compile Projects/personas/loom/observe_phase17_emergence.py` → PASS
3. 회귀 테스트 7종:
   - `py Projects/personas/loom/test_economy.py`
   - `py Projects/personas/loom/test_governance.py`
   - `py Projects/personas/loom/test_class_promotion.py`
   - `py Projects/personas/loom/test_nomos.py`
   - `py Projects/personas/loom/tests/test_phase17_faction_handoff_contract.py`
   - `py Projects/personas/loom/tests/test_phase14b_snn_integration.py`
   - `py Projects/personas/loom/tests/test_phase17_faction_stage3.py`
   - 모두 PASS (telemetry 추가만이므로 기존 assert 침범 0)

### 5.2 자연 측정 검증 (필수)

```bash
py Projects/personas/loom/observe_phase17_emergence.py \
   --seeds 7 13 42 --ticks 5000 \
   --out data/phase17_probe_phi3-snn-output-diagnosis/
```

**기대 결과**:
- 3 seed × 5000 tick 측정 완료 (각 ~10분, 총 ~30분 sequential)
- exit 0
- 4종 telemetry 이벤트 발생 (각 seed당 최소):
  - `uprising_leader_snn_snapshot` ≥ 5 (seed별 봉기 발생 빈도 기반)
  - `founder_absorbed_snn_snapshot` ≥ 1 (Case C에서 founder 흡수 다수 관찰됨)
  - `small_faction_snn_snapshot` ≥ 50 (48틱 × 5000틱 / 48 = 104회)
  - `territory_snn_distribution` ≥ 200 (territory 4~5개 × 100틱 × 50회)
- SUMMARY.md에 Phase 14B SNN Output Diagnosis 섹션 출력
- chain.json 비대 우려 없음 (telemetry 4종 합계 ≈ 1000~2000 events per seed)

### 5.3 진단 보고서 검증 (필수)

`PHASE-14B-SNN-OUTPUT-DIAGNOSIS-REPORT.md` 작성 후:
- 4 가설 PASS/FAIL 표 + 데이터 근거
- 자연 결합점 후보별 임계 후보값(분위수) 명시 (magic number 0.5 등 금지)
- 3엔진 cross-check 입력용 data summary 섹션
- LOOM-DIRECTION.md 추가 권고 초안

### 5.4 분포 검증 (의미 검증)

- G1: `uprising_leader_snn_snapshot`의 gate_passed=True/False 그룹 모두 n ≥ 3 (통계 유의미)
- G2: founder 흡수 케이스 n ≥ 5 (Case C에서 흡수 다수 관찰)
- G3: small faction snapshot 후 200틱 추적 가능한 케이스 n ≥ 10 (48틱 주기로 충분)
- G4: territory_snn_distribution의 territory별 100틱 시계열 ≥ 30 datapoints

n이 미달이면 "데이터 부족 — 추가 진단 필요" 명시 (PASS/FAIL 단정 금지).

---

## 6. Rollback

본 spec은 telemetry append만 추가. mechanism 무수정.

```bash
# 1. core/multi_tick_engine.py에서 추가된 4종 append 블록 제거
git diff Projects/personas/loom/core/multi_tick_engine.py
# 해당 블록만 revert

# 2. observe_phase17_emergence.py에서 추가된 분석 섹션 제거
git diff Projects/personas/loom/observe_phase17_emergence.py

# 3. 진단 디렉토리 삭제 (data/.gitignore 매칭, 추적 안 됨)
rm -rf Projects/personas/loom/data/phase17_probe_phi3-snn-output-diagnosis/

# 4. 보고서 삭제 (선택)
rm Projects/personas/loom/PHASE-14B-SNN-OUTPUT-DIAGNOSIS-REPORT.md

# 5. 회귀 테스트 재확인
py Projects/personas/loom/test_economy.py
# ... 7종 모두 PASS 확인
```

데이터 손실: telemetry 측정 기록만 사라짐 (mechanism 동작 0 영향).

---

## 7. 안티패턴 회피 점검 (LOOM-DIRECTION.md §안티패턴 표 7종)

| # | 안티패턴 | 회피 근거 |
|:--:|---------|----------|
| 1 | acceptance 우회 (false PASS) | 본 spec은 acceptance를 손대지 않음. 진단만 |
| 2 | top-down 임계 강제 | 임계 도입 0건 (분포 측정만). 보고서에서 분위수로만 후보 제안 |
| 3 | **SNN gate 정당화 부재** | **본 spec의 핵심 회피 대상** — 자연 측정 데이터로 결합점 식별 후에야 다음 단계 진입 |
| 4 | 무파괴 9 침범 | mechanism 무수정, 회귀 7종 무수정, 안전 전제 5종 무수정 |
| 5 | 거짓 보정 (sticky/inject 등) | telemetry append만, 보정 0건 |
| 6 | 단일 lever 비싸게 적용 | 본 spec은 lever 도입 0건 (진단 단계) |
| 7 | mechanism 없는 결정 | 본 spec은 mechanism 결정 자체를 손대지 않음 |

---

## 8. 다음 단계 (사용자 결정 영역)

본 spec 종결 후:

| 단계 | 내용 |
|------|------|
| (1) | telemetry 구현 + 자연 측정 5000틱×3seed (예상 1~2일) |
| (2) | 진단 보고서 작성 — 4 가설 PASS/FAIL + 자연 결합점 후보 + 임계 후보값 (예상 0.5일) |
| (3) | 3엔진 cross-check (`/discuss --quick`) — 자연 결합점 후보의 axis A 함정 회피 검증 (예상 0.5일) |
| (4) | d-4 spec 작성 — 검증된 결합점으로 mechanism 결합 spec (별도) |
| (5) | LOOM-DIRECTION.md §2.6 또는 §3 데이터 정당화 사슬 표준 추가 (보고서 부산물) |

본 spec은 (1)~(2) 범위. (3)~(5)는 보고서 작성 후 별도 단계.

---

## 9. Evidence 위치

본 spec 종결 시 evidence:
- spec 본문: `PHASE-14B-SNN-OUTPUT-DIAGNOSIS-SPEC.md` (본 파일)
- 진단 보고서: `PHASE-14B-SNN-OUTPUT-DIAGNOSIS-REPORT.md` (작성 예정)
- 자연 측정 데이터: `data/phase17_probe_phi3-snn-output-diagnosis/seed-{7,13,42}/`
- 선행 spec: `PHASE-17-CASE-C-P1-P2-SPEC-V2.md` (종결, PARTIAL_PROGRESS)
- 선행 진단: `PHASE-17-CASE-C-DIAGNOSIS-REPORT.md` (Case C root cause "연결·지속성 실패" 식별)
- axis A 기각 evidence: `subagent-runs/discuss/phase14b-a-cross-check-2026-04-28-quick/conclusion/conclusion.md`
- 본 spec 작업 evidence: `subagent-runs/claude/loom-phase14b-snn-output-diagnosis-spec-2026-05-02/`
