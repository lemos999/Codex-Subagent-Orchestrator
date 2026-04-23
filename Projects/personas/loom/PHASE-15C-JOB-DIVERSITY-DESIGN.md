# Phase 15-C: 직업 다양화 — healer/scholar/guard 특화 효과

## 배경

Phase 15 discuss(2026-04-18) 합의에 따른 15-C 순연 작업. 현재 `healer`, `scholar`, `guard` 직업은 이름만 있고 farmer/laborer/craftsman과 동일하게 `material`/`medicine`/`knowledge`/`material` goods만 생산. **직업 고유 효과 없음**.

**문제**: 왜 healer를 고용? 왜 scholar가 필요? 왜 guard를 키워? 현재는 구분 의미가 없음. Phase 15의 집단행동/grievance 전염이 작동하는 지금, 이를 **완화하거나 영향을 주는 직업 특화 효과가 필요**.

**원칙**:
- 새 뉴런 추가 금지 — 기존 SNN 경로만 사용
- healer/guard 효과는 **일하는 tick에 발동** (strike 중이면 효과 없음)
- scholar는 영지 기록을 축적 (정책 결정 재료)
- 인접 범위는 **같은 영지 내 trust ≥ 0.4** 주민 (`_get_community_members`와 동일 기준)

## 변경 파일 (2개)

1. `Projects/personas/loom/ontology/layers.py` — `Territory.chronicle` 필드 추가
2. `Projects/personas/loom/core/multi_tick_engine.py`
   - `_process_economy` work 분기 — healer/scholar/guard 특화 효과 호출
   - `_get_territory_guard_active_count` 헬퍼 추가
   - line 878 delta 계산 — guard 완화 계수 적용
   - `_update_governance_policy` — chronicle 기반 stability 가산

테스트: `Projects/personas/loom/test_phase15c_job_diversity.py` (신규, T1~T6)

---

## 구현 순서

### Step 1: Territory에 `chronicle` 필드 추가

[Projects/personas/loom/ontology/layers.py:117-138](Projects/personas/loom/ontology/layers.py#L117-L138) line 137 (`gdp_this_quarter` 위)에 추가:

```python
    # ── Phase 15-C: scholar가 기록한 영지 연대기 ────────
    chronicle: list = field(default_factory=list)  # 각 항목: {"tick": int, "type": str, "summary": str}
```

chronicle 각 항목은 dict: `{"tick": int, "type": "grievance_spike"|"strike"|"policy_shift", "summary": str}`. 최대 100개 유지 (오래된 것 pop).

### Step 2: healer 특화 — 같은 영지 trust 주민 chronic_stress 감소

[Projects/personas/loom/core/multi_tick_engine.py:2071](Projects/personas/loom/core/multi_tick_engine.py#L2071) `_process_economy` 함수 내, `job_title` 판정 후 추가.

work가 성공적으로 끝나기 직전(return 직전) 혹은 job_title별 분기로 처리. 가장 단순한 위치는 line 2089 `job_title = self._get_persona_job_title(pid)` 뒤:

```python
        # ── Phase 15-C: 직업 특화 효과 (work 시점에만) ──
        self._apply_job_speciality(pid, job_title)
```

새 메서드 `_apply_job_speciality`를 클래스 내부에 추가:

```python
    def _apply_job_speciality(self, pid: str, job_title: str) -> None:
        """Phase 15-C: healer/scholar/guard 특화 효과 — work 시점에 호출."""
        if job_title == "healer":
            # 같은 영지 trust≥0.4 주민들의 chronic_stress -0.002
            members = self._get_community_members(pid, min_trust=0.4)
            for member_pid in members:
                m_inner = self.inners.get(member_pid)
                if m_inner and not m_inner.is_sleeping:
                    m_inner.chronic_stress = max(0.0, m_inner.chronic_stress - 0.002)

        elif job_title == "scholar":
            # 같은 영지의 최근 tick events에서 grievance_spike/strike/policy_shift 발견 시 기록
            persona = self.personas[pid]
            territory = self.territories.get(persona.territory)
            if territory is not None:
                summary = self._summarize_recent_events(persona.territory)
                if summary:
                    territory.chronicle.append({
                        "tick": self.time.tick,
                        "type": summary["type"],
                        "summary": summary["text"],
                    })
                    # 최대 100개 유지
                    if len(territory.chronicle) > 100:
                        territory.chronicle = territory.chronicle[-100:]

        # guard는 line 878 delta 계산에서 감쇠 계수로 처리 (아래 Step 3)
```

새 헬퍼 `_summarize_recent_events`:

```python
    def _summarize_recent_events(self, territory_id: str) -> dict | None:
        """Phase 15-C: 최근 24틱 territory의 주요 이벤트 요약. 없으면 None."""
        if not self.log or len(self.log) == 0:
            return None
        recent = self.log[-24:]
        strike_count = 0
        grievance_high = 0
        policy_changed = False
        for tick_result in recent:
            for ev in tick_result.get("economy_events", []):
                if ev.get("type") == "strike_executed" and ev.get("territory") == territory_id:
                    strike_count += 1
                if ev.get("type") == "policy_update" and ev.get("territory") == territory_id:
                    policy_changed = True
                if ev.get("type") == "grievance_spike" and ev.get("territory") == territory_id:
                    grievance_high += 1
        if strike_count > 0:
            return {"type": "strike", "text": f"strikes={strike_count}"}
        if grievance_high > 0:
            return {"type": "grievance_spike", "text": f"spikes={grievance_high}"}
        if policy_changed:
            return {"type": "policy_shift", "text": "policy_updated"}
        return None
```

### Step 3: guard 완화 계수 — grievance delta 감쇠

[Projects/personas/loom/core/multi_tick_engine.py:870-891](Projects/personas/loom/core/multi_tick_engine.py#L870-L891) line 891 `inner.grievance = max(0.0, min(1.0, inner.grievance + delta))` 바로 앞에 추가:

```python
                # Phase 15-C: 영지에 active guard가 있으면 상승 delta 감쇠
                if delta > 0:
                    guard_count = self._get_territory_guard_active_count(persona.territory)
                    residents_count = max(1, len(self._get_territory_residents(persona.territory)))
                    guard_ratio = min(1.0, guard_count / residents_count)
                    # guard 비율 10%당 10% 감쇠, 최대 30% 감쇠
                    delta *= max(0.7, 1.0 - guard_ratio * 1.0)
```

주의: 위 코드의 `persona`는 line 870 근처에 이미 정의된 `persona = self.personas[pid]` 재사용. 없으면 `self.personas[pid].territory` 직접 사용.

새 헬퍼 `_get_territory_guard_active_count`:

```python
    def _get_territory_guard_active_count(self, territory_id: str) -> int:
        """Phase 15-C: 같은 영지의 현재 깨어있고 strike 중이 아닌 guard 수."""
        count = 0
        for other_pid in self._get_territory_residents(territory_id):
            other_inner = self.inners.get(other_pid)
            if not other_inner or other_inner.is_sleeping:
                continue
            if other_inner.strike_until_tick > self.time.tick:
                continue
            if self._get_persona_job_title(other_pid) == "guard":
                count += 1
        return count
```

### Step 4: chronicle → `_update_governance_policy` stability 가산

[Projects/personas/loom/core/multi_tick_engine.py:1416](Projects/personas/loom/core/multi_tick_engine.py#L1416) `stability = cluster_signal(2)` 바로 뒤에 추가:

```python
            # Phase 15-C: territory.chronicle이 5개 이상이면 stability +0.05 가산 (지식 축적 효과)
            chronicle_len = len(territory.chronicle) if territory else 0
            if chronicle_len >= 5:
                stability = min(1.0, stability + 0.05)
```

---

## 테스트: `test_phase15c_job_diversity.py`

T1~T6:

- **T1**: healer가 work하면 같은 영지 trust≥0.4 주민의 chronic_stress가 감소 (−0.002)
- **T2**: healer가 work하지 않거나 다른 영지 주민의 chronic_stress는 변화 없음
- **T3**: guard가 1명 있고 residents가 10명이면 grievance delta가 0.9배로 감쇠 (10% 감쇠)
- **T4**: guard가 없으면 grievance delta는 원본 그대로
- **T5**: scholar가 work하고 최근 24틱에 strike_executed 이벤트가 있으면 territory.chronicle에 1건 추가
- **T6**: territory.chronicle이 5개 이상이면 `_update_governance_policy`의 stability 신호가 +0.05 가산됨

검증:

```bash
C:\Users\haj\AppData\Local\Programs\Python\Python314\python.exe Projects/personas/loom/test_phase15c_job_diversity.py
C:\Users\haj\AppData\Local\Programs\Python\Python314\python.exe Projects/personas/loom/test_phase15a_market_openness.py
C:\Users\haj\AppData\Local\Programs\Python\Python314\python.exe Projects/personas/loom/test_phase15_collective_action.py
C:\Users\haj\AppData\Local\Programs\Python\Python314\python.exe Projects/personas/loom/test_phase14b_snn_integration.py
```

기존 테스트 회귀 금지.

---

## 설계 근거

1. **healer 효과 규모**: -0.002/tick은 24틱 work 반복 시 약 -0.05 감소. 자연 증가율(line 821 +0.005)의 40%를 상쇄. 과도하지 않음.
2. **guard 감쇠 0%~30%**: guard 비율 30% 초과 시 감쇠 포화. 경찰국가가 아닌 적정 치안.
3. **scholar chronicle 저장 → 정책 stability 가산**: scholar 고용의 **가시적 보상**. 기록이 축적될수록 안정성 인지 향상(지혜로운 관료 효과).
4. **strike 페르소나 guard 배제**: strike 중인 guard는 치안 효과 없음. 현실 정합성.
5. **효과 발동 조건 = work**: 세금/grievance가 직업 활동과 연동되므로 노동 분쟁 시 효과 자동 중단.

---

## 비차단 이슈 (Phase 15 인계)

- `_get_community_members` O(N²) contagion loop 이슈: Phase 15-C에서 `_apply_job_speciality` 매 work 호출로 부담 증가. healer가 많은 영지에서 체감. 당장 차단 수준 아님. Phase 15-D에서 `_territory_residents_cache` + trust index로 교체.
