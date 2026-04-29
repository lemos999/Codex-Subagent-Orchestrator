# Phase 17 Case C — active_factions Collapse 인과 진단 Spec

> 긴급도: 높음
> 선행 조건: Phase 14 propagation 구현 (`_propagate_grievance_lord_id_cross_territory`) + Stage 3 anti-collapse (Minority Persistence + Founder Respawn) + Stage 5 Respawn Grace + Stage 6 Lineage Affinity 모두 머지됨
> 작업 유형: **진단 (instrumentation + measurement)**. mechanism 로직 변경 없음. event_log 텔레메트리 보강만.
> DB migration: 없음
> 외부 의존: 없음
> 분리 정책: 본 spec은 **데이터 수집·분석만**. 패치 spec은 진단 보고서 작성 후 별도 작성.

---

## 1. 배경 — Phase 14B-A 기각 후속

### 1.1 3계층 목표 (loom 정신 명시)

`feedback_loom_goal_first.md`:
- **궁극 목표**: 자율 사회 시뮬 + **SNN 창발**(규칙 < 창발) + **PersonaBrain 논문 출판**
- **Phase 17 목적**: 사회 **자연 발생** (top-down 선언 금지). Φ-1 Land → Φ-2 Faction → Φ-3 Struggle → Φ-4 Nation 인과 사슬
- **본 spec 고유 역할**: 표면 패치(axis A) 시도가 외부 엔진 cross-check에서 거짓 PASS 패턴으로 식별됨. 근본 원인을 데이터로 확정한 뒤 자연 mechanism으로 해결할 진단 단계.

### 1.2 Phase 14B-A 기각 (선행 결정)

`/discuss --quick` 2/3 응답 합의 ([subagent-runs/discuss/phase14b-a-cross-check-2026-04-28-quick/run-summary.md](../../subagent-runs/discuss/phase14b-a-cross-check-2026-04-28-quick/run-summary.md)):
- axis A (affiliation drift dampen + SNN anger gate)는 hotfix v1에서 제거된 거짓 보정 5건과 **구조 동형**
- `feedback_root_cause_first.md` "표면 해결 금지" + `feedback_snn_emergence_first.md` "규칙 < 창발" 양쪽 위반 위험
- 기각, 근본 원인 진단 우선

### 1.3 측정된 결손 (재인용)

`data/phase17_probe_phi3-phase14-resonance/SUMMARY.md`:

| # | 항목 | seed 7 | seed 13 | seed 42 |
|---|------|:--:|:--:|:--:|
| 1 | uprising_event | 13 | 11 | 16 |
| 2 | grievance_pairs_end | **0** | **0** | **0** |
| 3 | dom_share_end | 100% | 100% | 100% |
| - | active_factions_end | **1** | **1** | **1** |
| - | branch_factions_total | 0 | 0 | 0 |
| - | uprising_join_share | 100% | 100% | 100% |
| - | drift_ratio | 63% | 52% | 75% |

**핵심 패턴**:
- 봉기는 평균 13건 발생하나 **모두 join (인접 faction 흡수)**, branch=0
- drift는 활발 (52~75%)하나 collapse 진행
- 후기에 active_factions=1 수렴 후 dominant faction 100% 점유

### 1.4 코드 단서 (smoking gun 후보, 가설 단계)

진단 시작 전 코드 분석으로 식별된 collapse 진행 후보 경로 4건:

#### 가설 H1: 봉기 trigger 인접 강제로 branch 발화 구조 차단
- `_uprising_trigger` (line 1897): `if not fid_in_contact: continue`
- 인접 faction 없는 외딴 faction은 봉기 자체 불가 → branch 발화 경로 닫힘
- 결과: 모든 봉기는 인접 faction 흡수 (join) → active_factions 단조 감소

#### 가설 H2: founder respawn 2단 구조에서 absorbing state 탈출 실패

`_respawn_faction_tick`은 [multi_tick_engine.py:1303-1427](core/multi_tick_engine.py#L1303-L1427)에 **Phase A + Phase B fallback** 2단 구조 보유. 후보 분해:

- **H2a**: Phase A 차단 — `if len(free_residents) < 3: continue` (line 1333). 단일 faction 수렴 시 모든 persona가 dominant faction에 가입 → free_residents=0 → Phase A skip.
- **H2b**: Phase B fallback (line 1379-1427) 발동되었으나 `if len(residents) < 3: continue` (line 1404)로 차단. territory 자체가 미달 인구.
- **H2c**: Phase B로 founder 생성 성공했으나, 다음 `_commit_faction_tick`에서 founder 또는 grace 종료 후 즉시 dominant faction으로 흡수되어 active_factions 증가 효과 무력화.

세 분기 중 어느 것이 실제 발동 패턴인지 데이터로 확정해야 패치 방향 선택 가능.

#### 가설 H3: minority persistence boost 흡수 속도 미달
- `MINORITY_PERSISTENCE_BOOST = 0.15` (small faction에 score 가산)
- 그러나 dominant faction의 trust/proximity positive feedback 우위 시 흡수 속도 > boost 효과

#### 가설 H4: drift 재가입 cooldown 누적 차단
- `FACTION_COOLDOWN_TICKS = 48` (faction 변경 후 cooldown)
- drift가 활발해도 cooldown 누적으로 minority faction 잔류 페르소나 재이탈 못함

### 1.5 본 spec의 인과 가설 (반증 가능 형태)

각 가설은 데이터로 반증 가능:

| 가설 | 반증 데이터 (있으면 가설 기각) |
|------|------|
| H1 | 5000틱 중 한 번이라도 branch faction이 spawn된 기록 |
| H2a | collapse 후 free_residents ≥ 3인 territory가 한 번이라도 존재 |
| H2b | Phase B fallback 진입(active_count < TARGET) 후 residents ≥ 3 territory가 존재 |
| H2c | Phase B로 founder 생성된 새 faction이 grace 종료 후 size ≥ 2를 ≥500틱 유지 |
| H3 | 소규모 faction(≤2명)이 boost로 안정화된 기록 (size 유지 ≥500틱) |
| H4 | dominant faction에 흡수된 페르소나가 cooldown 종료 후 다른 faction으로 재이탈 |

진단의 출력은 **가설 6개(H1, H2a, H2b, H2c, H3, H4)의 PASS/FAIL + 측정 데이터 + 진짜 root cause 식별**.

---

## 2. 작업 범위

### [필수]
1. `core/multi_tick_engine.py`에 **read-only 텔레메트리 이벤트** 4종 추가 (mechanism 변경 없음)
2. `observe_phase17_emergence.py`에 진단 분석 섹션 추가 (collapse tick, branch 시도, respawn skip 사유)
3. `data/phase17_probe_phi3-case-c-diagnosis/` 신규 디렉토리에 3 seed × 5000 tick 진단 결과 저장
4. `PHASE-17-CASE-C-DIAGNOSIS-REPORT.md` 작성 — 가설 4개 PASS/FAIL + 진짜 root cause + 패치 spec 후보 방향

### [선택]
- (보고서가 단일 root cause로 수렴하지 않을 경우) 추가 텔레메트리 후속 진단 spec 분리 권고

### [금지]
- **mechanism 로직 변경 절대 금지** — `_compute_affiliation_tick`, `_uprising_trigger`, `_emit_uprising`, `_respawn_faction_tick`, `_change_persona_faction` 본문 무수정
- **상수 값 변경 금지** — Stage 1/2/3/5/6 + Φ-3 + Phase 14 상수 전부 동결
- **무파괴 9 보장 계승** — Phase 14 spec §[금지]와 동일
- **신규 FactionChangeSource 추가 금지** — 4종 고정 (`birth_founder | affiliation | drift | conflict`)
- **acceptance 기준 완화 금지** — 본 spec은 acceptance를 손대지 않음 (진단만)

---

## 3. 구체 사양

### 3.1 텔레메트리 이벤트 4종 (`core/multi_tick_engine.py`)

각 이벤트는 `self.event_log.append(...)`만 추가. **logic 분기 없음**. 모두 [기존 코드 위치]의 if/return 직후나 직전에 텔레메트리만 삽입.

#### Event 1: `uprising_skip_no_contact` (가설 H1 검증)

**삽입 위치**: `_uprising_trigger`의 `if not fid_in_contact: continue` 직전 (현 line 1898 직전)

```python
if not fid_in_contact:
    self.event_log.append({
        "type": "uprising_skip_no_contact",
        "tick": self.time.tick,
        "fid": fid,
        "resonance_score": float(reso["resonance_score"]),
        "top_lord_id": top_lord,
    })
    continue
```

**측정 의도**: branch 발화가 차단된 모든 케이스를 기록. 가설 H1 PASS 시 5000틱 중 이벤트 발생 빈도 ≥ 1.

#### Event 2: `respawn_skip_reason` + `respawn_fallback_*` (가설 H2a/H2b/H2c 검증)

**삽입 위치**: `_respawn_faction_tick` ([multi_tick_engine.py:1303-1427](core/multi_tick_engine.py#L1303-L1427)) 내 4지점. 단 발동 가능 윈도우(`tick % FOUNDER_RESPAWN_EVERY == 0` AND `tick != 0`)에서만 기록. 코드 본문 로직은 무수정, append만 추가.

**개념적 위치 (실제 줄 번호는 코드 그대로 보존)**:

```python
def _respawn_faction_tick(self) -> None:
    if self.time.tick == 0:
        return
    if self.time.tick % FOUNDER_RESPAWN_EVERY != 0:
        return  # 주기 미도달은 텔레메트리 불필요

    active_count = sum(...)
    if active_count >= FOUNDER_RESPAWN_TARGET_ACTIVE:
        # [APPEND 1] active target met
        self.event_log.append({
            "type": "respawn_skip_reason",
            "tick": self.time.tick,
            "phase": "pre",
            "reason": "active_target_met",
            "active_count": active_count,
        })
        return

    # ── Phase A (기존 free_residents 루프) ──
    territory_priority = []
    phase_a_skips = []   # [APPEND 2 보조 변수]
    for territory in self.territories.values():
        free_residents = [...]  # 기존 코드 그대로
        if len(free_residents) < 3:
            phase_a_skips.append({
                "territory_id": territory.id,
                "free_residents_count": len(free_residents),
            })
            continue
        # ... 기존 로직 그대로 ...

    # ... 기존 territory_priority sort + Phase A spawn 루프 ...

    if active_count >= FOUNDER_RESPAWN_TARGET_ACTIVE:
        # [APPEND 3] Phase A 성공
        self.event_log.append({
            "type": "respawn_skip_reason",
            "tick": self.time.tick,
            "phase": "after_a",
            "reason": "phase_a_succeeded",
            "active_count": active_count,
            "phase_a_skips": phase_a_skips,
        })
        self._rebuild_faction_members_cache()
        return

    # [APPEND 4] Phase B 진입 — H2a 또는 H2b/H2c 검증 시작
    self.event_log.append({
        "type": "respawn_fallback_attempt",
        "tick": self.time.tick,
        "active_count_after_a": active_count,
        "phase_a_skips": phase_a_skips,
    })

    # ── Phase B fallback (기존 residents 루프) ──
    territory_priority = []
    phase_b_skips = []   # [APPEND 5 보조 변수]
    for territory in self.territories.values():
        residents = [...]  # 기존 코드 그대로
        if len(residents) < 3:
            phase_b_skips.append({
                "territory_id": territory.id,
                "residents_count": len(residents),
            })
            continue
        # ... 기존 로직 그대로 ...

    # ... 기존 spawn 루프 (founder 생성 후 [APPEND 6] 발화 포인트) ...
    # founder 생성 직후 (line 1424 self._change_persona_faction(...) 직후):
    #     self.event_log.append({
    #         "type": "respawn_fallback_founder_created",
    #         "tick": self.time.tick,
    #         "founder_pid": founder.id,
    #         "faction_id": faction.id,
    #         "territory_id": territory.id,
    #     })

    # 메서드 끝 (line 1427 _rebuild_faction_members_cache 직전):
    self.event_log.append({
        "type": "respawn_skip_reason",
        "tick": self.time.tick,
        "phase": "after_b",
        "reason": "phase_b_done" if active_count >= FOUNDER_RESPAWN_TARGET_ACTIVE else "phase_b_insufficient",
        "active_count": active_count,
        "phase_b_skips": phase_b_skips,
    })
    self._rebuild_faction_members_cache()
```

**측정 의도**:
- `respawn_skip_reason.phase=pre`: pre-loop early return 비율 (정상 운영)
- `respawn_skip_reason.phase=after_a`: Phase A로 활성도 회복 비율 (H2a 반증)
- `respawn_fallback_attempt`: Phase B 진입 빈도 = collapse 시도 빈도
- `respawn_skip_reason.phase=after_b reason=phase_b_insufficient`: Phase B 실패 = territory 인구 자체 미달 (H2b PASS 신호)
- `respawn_fallback_founder_created`: Phase B 성공 founder 생성. follow-up으로 grace 종료 후 size 추적 (H2c 검증)

#### Event 3: `minority_boost_applied` (가설 H3 검증)

**삽입 위치**: `_compute_affiliation_tick` 내 `score += MINORITY_PERSISTENCE_BOOST` 직후 (현 [multi_tick_engine.py:1242](core/multi_tick_engine.py#L1242) 직후).

**중복 방지 first_pid는 메서드 진입 시 1회만 계산** (인라인 sorted 금지 — O(n²) 회피):

```python
def _compute_affiliation_tick(self) -> None:
    self._rebuild_faction_members_cache()
    total_active = max(1, sum(1 for pid in self.personas if pid in self.inners))
    new_scores: dict[str, dict[str, float]] = {}
    # [APPEND] 메서드 진입 시 1회 — diagnostic only, 중복 방지용
    diagnostic_first_pid = min(self.personas, default=None)

    for pid in sorted(self.personas):
        # ... 기존 코드 ...
        for fid in sorted(self.factions):
            # ... 기존 score 계산 ...
            if 0 < member_count <= MINORITY_PERSISTENCE_MAX_MEMBERS:
                if self._same_territory(persona, fid) > 0.5:
                    score += MINORITY_PERSISTENCE_BOOST
                    # [APPEND] 텔레메트리: tick·fid 당 1회만 기록
                    if pid == diagnostic_first_pid:
                        self.event_log.append({
                            "type": "minority_boost_applied",
                            "tick": self.time.tick,
                            "fid": fid,
                            "member_count": member_count,
                        })
            # ... 기존 lineage 등 ...
```

**측정 의도**: small faction에 boost가 실제 가산되는 시점을 기록. 가설 H3 PASS 시 boost 적용 후 해당 faction이 수백 틱 내 소멸했는지 추적 가능.

**중복 방지 규칙**: `diagnostic_first_pid`는 진단 텔레메트리 전용. faction logic은 기존 sorted(self.personas) 그대로 사용. 인라인 `sorted(self.personas)[0]` 호출 **금지** (O(n²) 회피).

#### Event 4: `drift_recovery_to_minority` (가설 H4 검증)

**삽입 위치**: `_change_persona_faction` 본문 내 `event_log.append(...)` 직전 (현 line 1075 직전), `source == "drift"` 조건 추가 텔레메트리

```python
# 기존 코드:
self.event_log.append({
    "type": "faction_change",
    "tick": self.time.tick,
    "pid": pid,
    "from_faction": prev,
    "to_faction": new_faction_id,
    "source": source,
})
# 추가 (본 spec):
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
```

**측정 의도**: dominant 흡수에서 drift로 small faction에 재이탈하는 케이스를 기록. 가설 H4 PASS 시 빈도 ≥ 1 (cooldown 종료 후 회수 경로 자연 작동).

### 3.2 진단 분석 섹션 (`observe_phase17_emergence.py`)

기존 SUMMARY.md 출력 직후 별도 섹션 추가. 4개 텔레메트리 이벤트를 집계.

**삽입 위치**: probe 결과 출력 함수의 SUMMARY.md 작성 부분에 case_c_diagnosis 섹션 append.

**출력 형식 (각 seed별)**:
```markdown
## Case C Diagnosis (per seed)

### seed N

| 가설 | 측정 | 결과 |
|------|------|------|
| H1 (uprising 인접 차단) | uprising_skip_no_contact 빈도 | M회 |
| H2a (respawn Phase A 차단) | respawn_skip_reason.phase=after_a 빈도 (active_count<TARGET) | M회 |
| H2b (respawn Phase B 자체 미달) | respawn_skip_reason.phase=after_b reason=phase_b_insufficient 빈도 | M회 |
| H2c (Phase B founder 흡수) | respawn_fallback_founder_created 후 200틱 내 faction size=0 도달 비율 | X% |
| H3 (minority boost 효과) | minority_boost_applied first emission 후 200틱 내 faction size=0 도달 비율 | X% |
| H4 (drift 회수 작동) | drift_recovery_to_minority 빈도 | M회 |

**Active Factions Trace** (active_factions_snapshot 500틱 간격):
- tick 500: 활성 N개, 크기 분포 ...
- tick 1000: ...
- ... (5000틱까지 10 snapshot)

**Collapse 시점**: 첫 active_count=1 도달 tick = T (snapshot 기준 ±500틱 범위)

**Branch 발화 시도**: uprising_skip_no_contact 빈도 N건 + 실제 branch spawn 0건
```

**집계 로직**:
- `uprising_skip_no_contact` 이벤트 카운트 → H1 빈도
- `respawn_skip_reason.phase=after_a` 카운트 → H2a 빈도
- `respawn_skip_reason.phase=after_b reason=phase_b_insufficient` 카운트 → H2b 빈도
- `respawn_fallback_founder_created` per faction_id 추적: emission tick T부터 200틱 내 `_faction_members_cache[faction_id]` size=0 도달 비율 → H2c
  - tick T+200까지 size 유지되면 H2c 반증 (founder 안정화 성공)
- `minority_boost_applied` first emission per fid: 해당 fid의 첫 emission tick T부터 200틱 내 size=0 도달 비율 → H3
  - 200틱 = MINORITY_PERSISTENCE_BOOST 효과를 검증할 만한 충분한 윈도우 (FACTION_COMMIT_EVERY=48틱 × 4회분)
- `drift_recovery_to_minority` 카운트 → H4 빈도
- `active_factions_snapshot` 시계열 → active_factions 추이 + collapse 시점 식별

#### 보조 — `active_factions_snapshot` 이벤트 추가

기존 텔레메트리만으로 active 추이 도출 어려우면 5번째 이벤트 추가:

**삽입 위치**: `tick()` 메서드 본문, [multi_tick_engine.py:2498](core/multi_tick_engine.py#L2498) `return events` 직전. **메서드 본문 indent 레벨** (QUARTER_TICKS for 루프 내부 아님).

현재 코드 ([multi_tick_engine.py:2494-2498](core/multi_tick_engine.py#L2494-L2498)):
```python
2494:        if self.time.tick > 0 and self.time.tick % QUARTER_TICKS == 0:
2495:            for territory in self.territories.values():
2496:                territory.quarter_tax_income = 0.0
2497:                territory.quarter_public_spend = 0.0
2498:        return events  # ← 이 줄 바로 위에, 같은 indent로 삽입
```

삽입 코드:
```python
        # [APPEND] active_factions_snapshot — 메서드 본문 indent (8 spaces)
        if self.time.tick > 0 and self.time.tick % 500 == 0:
            self.event_log.append({
                "type": "active_factions_snapshot",
                "tick": self.time.tick,
                "active_count": sum(
                    1 for fid in self.factions
                    if len(self._faction_members_cache.get(fid, ())) > 0
                ),
                "faction_sizes": {
                    fid: len(self._faction_members_cache.get(fid, ()))
                    for fid in self.factions
                    if len(self._faction_members_cache.get(fid, ())) > 0
                },
            })
        return events
```

500틱 간격 (5000 tick → 10개 snapshot). collapse 정확한 tick 식별 가능.

**주의**: QUARTER_TICKS for 루프 내부에 삽입하면 매 territory마다 발화 → 측정 데이터 오염. 반드시 메서드 본문 레벨 indent.

### 3.3 진단 디렉토리 (`data/phase17_probe_phi3-case-c-diagnosis/`)

`.gitignore` 패턴 `data/phase17_probe*/` 자동 매칭됨.

**구조**:
```
data/phase17_probe_phi3-case-c-diagnosis/
├── SUMMARY.md                   # 기존 형식 + Case C Diagnosis 섹션
├── seed-7/
│   ├── chain.json               # 전체 event_log
│   └── case_c_events.json       # 4종 텔레메트리 이벤트 추출본 (분석 편의)
├── seed-13/...
└── seed-42/...
```

### 3.4 진단 보고서 (`PHASE-17-CASE-C-DIAGNOSIS-REPORT.md`)

**필수 섹션**:
1. 요약 — 4가지 가설 PASS/FAIL 결과 표
2. 가설별 데이터 — 각 seed의 빈도·시점·맥락
3. **진짜 root cause 식별** — 단일/다중. 단일이면 패치 방향 1개. 다중이면 우선순위.
4. **다음 단계 패치 spec 후보 방향** — 다음 중 하나 또는 조합 권고:
   - 패치 후보 P1: `_uprising_trigger` 인접 조건 자연 완화 (charter 시너지/grievance 강도/territory 거리 등 자연 조건으로 인접 대체)
   - 패치 후보 P2: `_respawn_faction_tick` free_residents 임계 자연 완화 (예: dominant 흡수 후 grievance high 페르소나가 자발 이탈하면 free 상태)
   - 패치 후보 P3: territory cross-propagation 강화 (Phase 14 후속) — `_propagate_grievance_lord_id_cross_territory`의 전파 폭 확장
   - 패치 후보 P4: 다른 차원 — 데이터에 따라 발견되는 새 mechanism

**진단의 가치**:
- 본 spec은 acceptance #2를 직접 풀지 않음
- 데이터로 collapse 진짜 원인 확정 후 자연 mechanism 설계 단계로 진입
- 거짓 PASS 패턴을 사전 차단 (역공학 회피)

---

## 4. 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/core/multi_tick_engine.py` | 텔레메트리 이벤트 5종 추가 (logic 변경 없음) | 수정 |
| `Projects/personas/loom/observe_phase17_emergence.py` | Case C Diagnosis 섹션 + 집계 로직 | 수정 |
| `Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis/SUMMARY.md` | 새 진단 결과 | 추가 |
| `Projects/personas/loom/PHASE-17-CASE-C-DIAGNOSIS-REPORT.md` | 진단 보고서 (가설 PASS/FAIL + root cause + 패치 후보) | 추가 |
| `Projects/personas/loom/Tools/scripts/verify_phase17_case_c_diagnosis.py` | AST 본문 길이 검증 스크립트 (§5.2) | 추가 |

**변경 없음 (금지)**:
- `core/multi_tick_engine.py`의 `_compute_affiliation_tick`, `_uprising_trigger`, `_emit_uprising`, `_respawn_faction_tick`, `_change_persona_faction` 본문 로직 (event_log append만 추가)
- `ontology/layers.py` 모든 상수
- `ontology/__init__.py` export
- `test_phase17_*.py` 기존 테스트
- `brain/**` 전체

---

## 5. 검증

### 5.1 기계 검증

```bash
cd Projects/personas/loom
py -m py_compile core/multi_tick_engine.py
py -m py_compile observe_phase17_emergence.py
```

### 5.2 무파괴 보장 검증 (Python AST)

기존 핵심 메서드의 본문 길이가 변경 폭 내인지 AST로 확인 (logic 변경 없이 텔레메트리만 추가됐는지).

**baseline 실측** (HEAD 기준, 본 spec 작성 시점):
- `_compute_affiliation_tick`: 49줄 (line 1207-1256)
- `_uprising_trigger`: 43줄 (line 1883-1926)
- `_respawn_faction_tick`: 124줄 (line 1303-1427) — Phase A + Phase B fallback 2단 구조
- `_change_persona_faction`: 29줄 (line 1053-1082)

**텔레메트리 추가 허용 폭**:
- 단순 1지점 append: +5줄
- 복수 지점 append (Event 2의 _respawn_faction_tick): +25줄 (Phase A skip + after_a + fallback_attempt + Phase B skip + after_b + founder_created)

```python
# Projects/personas/loom/Tools/scripts/verify_phase17_case_c_diagnosis.py
import ast, sys
src = open("core/multi_tick_engine.py", encoding="utf-8").read()
tree = ast.parse(src)

# 메서드별 baseline + 허용 폭 = max span
EXPECT = {
    "_compute_affiliation_tick": 60,   # baseline 49 + 11 (first_pid 1줄 + emit 9줄 + 여유 1)
    "_uprising_trigger": 50,            # baseline 43 + 7 (skip_no_contact emit 6줄 + 여유 1)
    "_respawn_faction_tick": 155,       # baseline 124 + 31 (Phase A/B 양쪽 텔레메트리 6포인트)
    "_change_persona_faction": 40,      # baseline 29 + 11 (drift_recovery emit 9줄 + 여유 2)
}

errs = []
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name in EXPECT:
        span = node.end_lineno - node.lineno
        if span > EXPECT[node.name]:
            errs.append(f"{node.name}: span {span} > expected {EXPECT[node.name]}")
if errs: sys.exit("\n".join(errs))
print("OK")
```

**검증 의도**: 텔레메트리 추가가 logic 변경(분기 추가, 조건 변경 등)으로 변질되지 않았는지 본문 크기 상한으로 보장. 상한 초과 시 코드 리뷰로 회귀.

### 5.3 회귀 검증

```bash
# 기존 acceptance 회귀 (변경 없어야 함)
py test_phase17_acceptance.py        # 기존 결과 그대로 (acceptance #2 FAIL 유지)
py test_phase17_faction_handoff_contract.py  # 12건 PASS
py test_phase14b_snn_integration.py  # 8건 PASS
py test_phase17_faction_stage3.py    # PASS
```

logic 변경 없으므로 모든 결과는 기존 그대로여야 함.

### 5.4 진단 측정 실행

```bash
py observe_phase17_emergence.py --label phi3-case-c-diagnosis --seeds 7,13,42 --ticks 5000
```

### 5.5 보고서 자체 검증

`PHASE-17-CASE-C-DIAGNOSIS-REPORT.md` 작성 후 다음 4가지 검증:
1. 4가지 가설 모두 PASS/FAIL 명확 판정
2. 진짜 root cause가 데이터에 근거 (가설 결과 + 추가 관찰)
3. 패치 후보 방향이 자연 mechanism 형태 (역공학 신호 없음)
4. acceptance #2 PASS를 강제하지 않는 설계 (후속 spec에서도)

---

## 6. Rollback

```bash
cd Projects/personas/loom
git checkout HEAD -- core/multi_tick_engine.py observe_phase17_emergence.py
rm -rf data/phase17_probe_phi3-case-c-diagnosis/
rm PHASE-17-CASE-C-DIAGNOSIS-REPORT.md
```

데이터 손실: 텔레메트리 데이터(진단 디렉토리)만 사라짐. mechanism 미수정이므로 production 영향 없음.

---

## 7. Codex 전달용 핵심 요약

본 spec은 **진단 단계** (mechanism 변경 없음, 텔레메트리만):

1. `core/multi_tick_engine.py`에 event_log.append 텔레메트리 5종 추가 ([§3.1](#31-텔레메트리-이벤트-4종-coremulti_tick_enginepy) 참조):
   - `uprising_skip_no_contact` ([line 1898](core/multi_tick_engine.py#L1898) `if not fid_in_contact: continue` 직전)
   - `respawn_skip_reason` + `respawn_fallback_attempt` + `respawn_fallback_founder_created` ([line 1303-1427](core/multi_tick_engine.py#L1303-L1427) Phase A + Phase B 양쪽)
   - `minority_boost_applied` ([line 1242](core/multi_tick_engine.py#L1242) 직후, diagnostic_first_pid 외부 1회 계산)
   - `drift_recovery_to_minority` ([line 1075](core/multi_tick_engine.py#L1075) faction_change emit 직후, source=="drift" 조건부)
   - `active_factions_snapshot` ([line 2498](core/multi_tick_engine.py#L2498) `return events` 직전, 메서드 본문 indent, tick % 500 == 0 시)

2. `observe_phase17_emergence.py`에 Case C Diagnosis 섹션 (6 가설 H1/H2a/H2b/H2c/H3/H4 집계 + active 추이)

3. probe 실행: `py observe_phase17_emergence.py --label phi3-case-c-diagnosis --seeds 7,13,42 --ticks 5000`

4. `PHASE-17-CASE-C-DIAGNOSIS-REPORT.md` 작성:
   - 6 가설 PASS/FAIL 표
   - 진짜 root cause (단일 또는 다중)
   - 패치 후보 P1~P4 중 권고 + 우선순위

**제약**:
- mechanism 본문 로직 절대 무수정 (텔레메트리 append만)
- 상수 무수정
- acceptance 손대지 않음 (진단만)
- 인라인 `sorted(self.personas)[0]` 호출 금지 (외부 1회 계산)

**완료 조건**:
- AST 본문 길이 검증 통과 (§5.2 EXPECT 상한 내)
- 회귀 테스트 모두 PASS (기존과 동일, acceptance #2 FAIL 유지 — 진단이므로 정상)
- 6 가설 PASS/FAIL이 데이터 근거로 명확
- 패치 후보 권고가 자연 mechanism 형태 (역공학 신호 없음)

---

## 8. 외부 엔진 cross-check 권고 (다음 단계 spec 작성 시)

본 spec의 진단 단계는 외부 cross-check 불필요 (mechanism 미수정, 데이터 수집만).

**그러나 진단 결과 작성될 패치 spec은 반드시 cross-check 실행**:
- `/discuss --quick` (Claude + Codex + Gemini) 1라운드
- 거짓 PASS 패턴 잠복 여부 검증
- SNN 창발 정신 정합성 검증
- 인과 사슬 자연성 검증

이는 Phase 14B-A 기각 교훈의 직접 계승: **acceptance를 풀려고 mechanism을 추가하기 전, 자연 검증을 거친다**.
