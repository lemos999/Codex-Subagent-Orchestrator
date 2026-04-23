# [Feature + Bug Fix] Phase 16-G — Public Works 후보 풀 확장 + Signal Bootstrap

> 긴급도: 높음
> 선행 조건: Phase 16-F 구현 완료 (PHASE-16F-CODEX-INSTRUCTIONS.md)
> 작업 유형: 기능 추가 (혼합: 후보 풀 확장 + bootstrap)
> DB migration: 없음
> 외부 의존: 없음

---

## 배경

Phase 16-F 검증 결과:
- Hard 5지표 중 4개 PASS. **`public_works >= 50` 만 미달** (43/60 = 71.7%)
- Phase 16-F의 treasury floor는 성공 — persona gold 18864 (목표 6000의 3.1배)
- 그러나 persona gold 성공이 역설적으로 새 병목 노출:

**꼬리 추적**:
```
Phase 16-F 성공 → persona gold 18864 (대성공)
→ LOW_GOLD_THRESHOLD(300) 이하 persona 희소
→ low_gold_hungry 후보 풀 공집합
→ unemployed 4명(대부분 employed)만 남음
→ no_candidates 12건 (전체 skip의 62%)
→ public_works 43 (7건 부족)
```

부가 병목:
- `signal_stale(never_computed)` 3건: 초기 72틱 동안 SNN이 signal 생성 전
- Mirrordale treasury=43, Ironridge treasury=468 (영지 간 불균형은 Phase 16-H 범위)

---

## 작업 범위

### [필수]
1. **A. 후보 풀 확장**: food_crisis 또는 high_tension 조건에서 employed persona를 **part-time 후보**로 포함
   - `employment_id` 변경 금지 — 후보 자격만 완화
   - 임금/생산 비율 감소 (full-time 대비 50%)
2. **B. Signal Bootstrap**: 초기 72틱 동안 `last_snn_signals_tick < 0`이면 기본 signal 주입
   - tick ≥ STALE_SIGNAL_TICKS(72) 이후에는 기존 skip 로직 유지
3. **C. 테스트 갱신**: A+B에 대한 신규 테스트 추가
4. **D. Hard 지표 재검증**: public_works ≥ 50 통과

### [선택]
- 없음

### [금지]
- Phase 12~16F 모든 기존 상수 값 변경 (목록 § "상수 변경 금지" 참조)
- `employment_id` 변경 (part-time은 후보 플래그로만 처리)
- 영지 간 보조금/재정 이전 (`territory_to_territory fiscal transfer`) — 경제 독립 원칙 유지
- 페르소나 간 직접 gold gift / 중앙 재정 이식
- PersonaBrain, SNN 내부, `brain/**` 변경
- `_process_food_reserve`, `_process_internal_food_procurement` 비즈니스 로직 변경
- 결정성 계약 변경 (`self.rng`, `self._np_rng`, seed=42)
- 지시서 범위 밖 테스트 생성 / 기존 script형 테스트의 pytest 변환

---

## 수정 허용 파일 (5개)

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/ontology/layers.py` | 신규 상수 5개 추가 | 수정 |
| `Projects/personas/loom/ontology/__init__.py` | 신규 상수 export | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | `_process_public_works` 로직 변경 (§A, §B) | 수정 |
| `Projects/personas/loom/test_phase16_public_works.py` | 신규 테스트 추가 (§C) | 수정 |
| `Projects/personas/loom/test_phase16c_internal_food_market.py` | 변경 없음 예상 (필요 시 허용) | 수정 |

**변경 없음 (금지)**:
- `brain/**` 전체
- `core/` 하의 `multi_tick_engine.py` 외 모든 파일
- 다른 테스트 파일: `test_phase16d_dynamic_reserve.py`, `test_phase16e_agriculture.py`, `test_class_promotion.py`, `test_nomos.py`

---

## 상수 변경 가능/금지 목록

### 신규 추가 (5개 — 이 목록 외 신규 상수 금지)

| 이름 | 값 | 설명 |
|------|:-:|------|
| `PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD` | `0.5` | 이 값 이상의 tension에서 part-time 후보 풀 활성화 |
| `PUBLIC_WORKS_PARTTIME_WAGE_RATIO` | `0.5` | part-time 임금 비율 (full-time 대비) |
| `PUBLIC_WORKS_PARTTIME_OUTPUT_RATIO` | `0.5` | part-time 생산 비율 (full-time 대비) |
| `PUBLIC_WORKS_BOOTSTRAP_GROWTH` | `0.3` | 초기 72틱 bootstrap growth signal |
| `PUBLIC_WORKS_BOOTSTRAP_TENSION` | `0.2` | 초기 72틱 bootstrap tension signal |

### 변경 금지 (Phase 12~16F 보호 상수 — 자가 튜닝 불허)

```
PUBLIC_WORKS_WAGE_PER_TICK = 5.0
PUBLIC_WORKS_DURATION = 24
PUBLIC_WORKS_MIN_TREASURY = 500.0
PUBLIC_WORKS_MAX_TREASURY_RATIO = 0.5
PUBLIC_WORKS_IN_KIND_RATIO = 0.5
PUBLIC_WORKS_BASE_ACTIVATION = 0.04
PUBLIC_WORKS_RATE_MIN = 0.03
PUBLIC_WORKS_LOW_GOLD_THRESHOLD = 300.0
PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD = 12
PUBLIC_WORKS_FARMER_BIAS = 2.0
PUBLIC_WORKS_TREASURY_INCOME_FLOOR_RATIO = 0.2   # Phase 16-F 도입분도 포함
QUARTER_TAX_BUDGET_MULTIPLIER = 1.2
FOOD_STOCKPILE_RESERVE_THRESHOLD = 30.0
FOOD_STOCKPILE_RESERVE_PER_PERSONA = 14.0
NPC_FOOD_PURCHASE_COOLDOWN_TICKS = 48
NPC_FOOD_TRIGGER_RESERVE_RATIO = 0.5
INTERNAL_FOOD_PRICE_RATIO = 0.75
PERSONA_FOOD_SAFE_STOCK = 12.0
HUNGER_PRESSURE_WEIGHT = 0.2
HUNGER_TRIGGER_THRESHOLD = 0.3
FOOD_LABOR_NON_FARMER_RATIO = 0.7
COMMUNAL_FARM_BOOST = 0.3
FOOD_CRISIS_FARM_THRESHOLD = 3.0
FOOD_CRISIS_RESERVE_RATIO  # (기존 값 유지)
STALE_SIGNAL_TICKS = 72
JOB_BASE_OUTPUT / JOB_OUTPUT_MAP / NPC_PRICES / FACILITY_FEES (dict 전체)
```

---

## A. 후보 풀 확장 (Part-time)

### A-1. 신규 상수 (`ontology/layers.py`)

**삽입 위치**: `PUBLIC_WORKS_TREASURY_INCOME_FLOOR_RATIO` (Phase 16-F 도입) 다음 줄

```python
PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD: float = 0.5
"""Phase 16-G: 이 값 이상의 tension 또는 food_crisis 활성 시 part-time 후보 풀 개방.
employed persona 를 추가 후보로 포함하되 employment_id 는 불변."""

PUBLIC_WORKS_PARTTIME_WAGE_RATIO: float = 0.5
"""Phase 16-G: part-time 임금 비율 (full-time 대비).
employed persona 는 이미 고용 소득이 있으므로 절반 임금만 지급."""

PUBLIC_WORKS_PARTTIME_OUTPUT_RATIO: float = 0.5
"""Phase 16-G: part-time 생산 비율 (full-time 대비).
본업과 분할 노동이므로 공공근로 산출도 절반."""
```

### A-2. Export (`ontology/__init__.py`)

기존 import/export 블록에 3개 상수 추가.

### A-3. `_process_public_works` 로직 변경

**파일**: `Projects/personas/loom/core/multi_tick_engine.py`
**함수**: `_process_public_works`
**라인**: 2780~2880 (candidate 선발 + 임금 지급 블록)

#### A-3-1. food_crisis_active / parttime_enabled 를 후보 선발 전에 계산

**현재 구조** (개념):
```
1. signals 계산 (growth/tension/hunger)
2. rate 계산
3. budget_cap 계산
4. candidates 선발 (unemployed + low_gold_hungry)  ← 여기
5. reserve, reserve_target, food_crisis_active 계산
6. n_hire 계산
7. 임금 지급 루프
```

**변경 후 구조**:
```
1. signals 계산 (growth/tension/hunger)
2. rate 계산
3. budget_cap 계산
4. [이동] reserve, reserve_target, food_crisis_active 계산
4a. [신규] parttime_enabled = food_crisis_active OR tension >= THRESHOLD
5. candidates 선발 (unemployed + low_gold_hungry + parttime)  ← 확장
6. n_hire 계산
7. 임금 지급 루프 (parttime 여부에 따라 비율 적용)
```

#### A-3-2. 후보 선발 블록 변경

**변경 전** (line 2782~2811 근처, 현재 코드):
```python
        lord_id = getattr(territory, "lord_id", None)

        unemployed: list[str] = []
        low_gold_hungry: list[str] = []
        for pid, persona in self.personas.items():
            if persona.territory != territory_id:
                continue
            if pid == lord_id:
                continue
            inner = self.inners[pid]
            if float(inner.vitality) <= 0.0 or inner.is_sleeping:
                continue
            if persona.employment_id is None:
                unemployed.append(pid)
            else:
                wallet = self.wallets.get(pid)
                if wallet is None:
                    continue
                gold = float(getattr(wallet, "gold", 0.0))
                hungry_ticks = int(getattr(inner, "consecutive_hunger_ticks", 0))
                if gold < PUBLIC_WORKS_LOW_GOLD_THRESHOLD and hungry_ticks >= PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD:
                    low_gold_hungry.append(pid)

        candidates = unemployed + low_gold_hungry
        if not candidates:
            return [{ ... "no_candidates" ... }]

        reserve = float(getattr(territory, "food_reserve", 0.0))
        residents_count = sum(
            1 for p in self.personas.values() if p.territory == territory_id
        )
        reserve_target = residents_count * FOOD_STOCKPILE_RESERVE_PER_PERSONA
        food_crisis_active = (
            hunger >= HUNGER_TRIGGER_THRESHOLD
            and reserve < reserve_target * FOOD_CRISIS_RESERVE_RATIO
        )
```

**변경 후**:
```python
        # Phase 16-G: food_crisis / parttime_enabled 를 후보 선발 전에 계산
        reserve = float(getattr(territory, "food_reserve", 0.0))
        residents_count = sum(
            1 for p in self.personas.values() if p.territory == territory_id
        )
        reserve_target = residents_count * FOOD_STOCKPILE_RESERVE_PER_PERSONA
        food_crisis_active = (
            hunger >= HUNGER_TRIGGER_THRESHOLD
            and reserve < reserve_target * FOOD_CRISIS_RESERVE_RATIO
        )
        parttime_enabled = (
            food_crisis_active
            or tension >= PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD
        )

        lord_id = getattr(territory, "lord_id", None)

        unemployed: list[str] = []
        low_gold_hungry: list[str] = []
        parttime_candidates: list[str] = []  # Phase 16-G: employed 중 part-time 후보
        for pid, persona in self.personas.items():
            if persona.territory != territory_id:
                continue
            if pid == lord_id:
                continue
            inner = self.inners[pid]
            if float(inner.vitality) <= 0.0 or inner.is_sleeping:
                continue
            if persona.employment_id is None:
                unemployed.append(pid)
            else:
                wallet = self.wallets.get(pid)
                if wallet is None:
                    continue
                gold = float(getattr(wallet, "gold", 0.0))
                hungry_ticks = int(getattr(inner, "consecutive_hunger_ticks", 0))
                if gold < PUBLIC_WORKS_LOW_GOLD_THRESHOLD and hungry_ticks >= PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD:
                    low_gold_hungry.append(pid)
                elif parttime_enabled:
                    # Phase 16-G: 위기 상황에서만 employed 도 part-time 후보로 포함
                    parttime_candidates.append(pid)

        # 우선순위: unemployed > low_gold_hungry > parttime
        candidates = unemployed + low_gold_hungry + parttime_candidates
        parttime_pids: set[str] = set(parttime_candidates)

        if not candidates:
            return [{
                "type": "public_works_skip_reason",
                "territory": territory_id,
                "reason": "no_candidates",
                "unemployed": 0,
                "low_gold_hungry": 0,
                "parttime": 0,
            }]
```

**제거**: 기존 `reserve / reserve_target / food_crisis_active` 계산 블록 (위로 옮겼으므로 중복 제거).

#### A-3-3. 임금 / 생산 루프에 part-time 비율 적용

**변경 전** (line 2847 근처~):
```python
        events: list[dict] = []
        for pid in chosen:
            if territory.treasury_gold < wage_per_person:
                break
            job_title = self._get_persona_job_title(pid) or "laborer"

            if food_crisis_active:
                produced_type = "food"
                base_output = JOB_BASE_OUTPUT.get("farmer", 2.0)
                if job_title != "farmer":
                    base_output *= FOOD_LABOR_NON_FARMER_RATIO
            else:
                produced_type = JOB_OUTPUT_MAP.get(job_title, "material")
                base_output = JOB_BASE_OUTPUT.get(job_title, 0.5)

            produced = base_output * PUBLIC_WORKS_DURATION

            farm_multiplier = 1.0
            if produced_type == "food":
                farm_multiplier = 1.0 + territory.communal_farms * COMMUNAL_FARM_BOOST
                produced *= farm_multiplier

            in_kind = produced * PUBLIC_WORKS_IN_KIND_RATIO
            to_persona = produced - in_kind

            territory.treasury_gold -= wage_per_person
            territory.quarter_public_spend += wage_per_person
            self.wallets[pid].receive(wage_per_person)
            if produced_type == "food":
                territory.food_reserve = getattr(territory, "food_reserve", 0.0) + in_kind
            else:
                territory.inventory[produced_type] = (
                    territory.inventory.get(produced_type, 0.0) + in_kind
                )
```

**변경 후**:
```python
        events: list[dict] = []
        for pid in chosen:
            # Phase 16-G: part-time 여부에 따라 임금 / 생산 비율 적용
            is_parttime = pid in parttime_pids
            wage_ratio = PUBLIC_WORKS_PARTTIME_WAGE_RATIO if is_parttime else 1.0
            output_ratio = PUBLIC_WORKS_PARTTIME_OUTPUT_RATIO if is_parttime else 1.0
            wage_applied = wage_per_person * wage_ratio

            if territory.treasury_gold < wage_applied:
                break
            job_title = self._get_persona_job_title(pid) or "laborer"

            if food_crisis_active:
                produced_type = "food"
                base_output = JOB_BASE_OUTPUT.get("farmer", 2.0)
                if job_title != "farmer":
                    base_output *= FOOD_LABOR_NON_FARMER_RATIO
            else:
                produced_type = JOB_OUTPUT_MAP.get(job_title, "material")
                base_output = JOB_BASE_OUTPUT.get(job_title, 0.5)

            produced = base_output * PUBLIC_WORKS_DURATION * output_ratio

            farm_multiplier = 1.0
            if produced_type == "food":
                farm_multiplier = 1.0 + territory.communal_farms * COMMUNAL_FARM_BOOST
                produced *= farm_multiplier

            in_kind = produced * PUBLIC_WORKS_IN_KIND_RATIO
            to_persona = produced - in_kind

            territory.treasury_gold -= wage_applied
            territory.quarter_public_spend += wage_applied
            self.wallets[pid].receive(wage_applied)
            if produced_type == "food":
                territory.food_reserve = getattr(territory, "food_reserve", 0.0) + in_kind
            else:
                territory.inventory[produced_type] = (
                    territory.inventory.get(produced_type, 0.0) + in_kind
                )
```

#### A-3-4. public_works 이벤트 dict에 `parttime` 플래그 추가

현재 이벤트 스키마 유지하되 다음 필드 추가:
```python
events.append({
    "type": "public_works",
    "territory": territory_id,
    "persona": pid,
    "job_title": job_title,
    "produced_type": produced_type,
    "produced_total": round(produced, 2),
    "in_kind_to_territory": round(in_kind, 2),
    "to_persona": round(to_persona, 2),
    "wage": round(wage_applied, 2),          # Phase 16-G: 실제 지급 임금
    "parttime": is_parttime,                 # Phase 16-G: part-time 여부
    "food_crisis": food_crisis_active,
    "farm_multiplier": round(farm_multiplier, 3),
})
```

기존 필드가 다른 구조였다면 새 필드만 덧붙여서 호환 유지. 기존 테스트에서 사용 안 하는 필드는 선택 필드로 간주.

---

## B. Signal Bootstrap

### B-1. 신규 상수 (`ontology/layers.py`)

**삽입 위치**: A-1 아래

```python
PUBLIC_WORKS_BOOTSTRAP_GROWTH: float = 0.3
"""Phase 16-G: 초기 72틱(STALE_SIGNAL_TICKS) 동안 SNN 신호 없을 때 사용할 기본 growth.
값 0.3: 완만한 긍정 신호. economy 시작 지원."""

PUBLIC_WORKS_BOOTSTRAP_TENSION: float = 0.2
"""Phase 16-G: 초기 72틱 동안 기본 tension. part-time 활성화 경계 아래,
공공근로 집행은 가능한 낮은 수준."""
```

### B-2. Export (`ontology/__init__.py`)

2개 상수 추가.

### B-3. `_process_public_works` 진입 가드 변경

**파일**: `Projects/personas/loom/core/multi_tick_engine.py`
**라인**: 2726~2745 근처 (signals 로딩 블록)

**변경 전**:
```python
        if territory.last_snn_signals_tick < 0:
            return [{
                "type": "public_works_skip_reason",
                "territory": territory_id,
                "reason": "signal_stale",
                "detail": "never_computed",
            }]
        sig_age = self.time.tick - territory.last_snn_signals_tick
        if sig_age > STALE_SIGNAL_TICKS:
            return [{
                "type": "public_works_skip_reason",
                "territory": territory_id,
                "reason": "signal_stale",
                "detail": f"sig_age={sig_age}",
            }]

        snn = territory.last_snn_signals or {}
        growth = float(snn.get("growth", 0.0))
        tension = float(snn.get("tension", 0.0))
        stability = float(snn.get("stability", 0.0))
```

**변경 후**:
```python
        # Phase 16-G: 초기 STALE_SIGNAL_TICKS(72) 동안 SNN 신호 없음 시 bootstrap
        if territory.last_snn_signals_tick < 0:
            if self.time.tick >= STALE_SIGNAL_TICKS:
                return [{
                    "type": "public_works_skip_reason",
                    "territory": territory_id,
                    "reason": "signal_stale",
                    "detail": "never_computed",
                }]
            # Phase 16-G bootstrap: 초기 72틱은 기본 신호로 economy 시동
            snn = {
                "growth": PUBLIC_WORKS_BOOTSTRAP_GROWTH,
                "tension": PUBLIC_WORKS_BOOTSTRAP_TENSION,
                "stability": 0.0,
            }
        else:
            sig_age = self.time.tick - territory.last_snn_signals_tick
            if sig_age > STALE_SIGNAL_TICKS:
                return [{
                    "type": "public_works_skip_reason",
                    "territory": territory_id,
                    "reason": "signal_stale",
                    "detail": f"sig_age={sig_age}",
                }]
            snn = territory.last_snn_signals or {}

        growth = float(snn.get("growth", 0.0))
        tension = float(snn.get("tension", 0.0))
        stability = float(snn.get("stability", 0.0))
```

**상수 import 확인**: 파일 상단 `from ontology.layers import (...)` 블록에 5개 상수 추가.

---

## C. 신규 테스트 (`test_phase16_public_works.py`)

기존 테스트 맨 뒤에 다음 3개 추가.

### C-1. Part-time 후보 포함 검증

```python
def test_parttime_enabled_by_high_tension() -> None:
    """Phase 16-G: tension >= THRESHOLD 시 employed persona 도 part-time 후보로 포함."""
    from ontology.layers import PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD

    engine = _setup_engine()
    tid = _ready_territory(engine, treasury=3000.0, tax_income=500.0)
    territory = engine.territories[tid]

    # 모든 non-lord persona 에 employment 부여 → 원래대로면 후보 = 공집합
    for pid, persona in engine.personas.items():
        if persona.territory == tid and pid != territory.lord_id:
            persona.employment_id = "fake_emp"
            engine.wallets[pid].gold = 1000.0  # low_gold_hungry 경로 차단
            engine.inners[pid].consecutive_hunger_ticks = 0

    # high tension 주입 → part-time 경로 활성화
    _inject_signals(
        engine, tid,
        growth=0.0, tension=PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD + 0.1,
        stability=0.0,
    )
    events = engine._process_public_works(tid)

    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events, f"part-time 후보가 활성화되어 실제 집행되어야 함: {events}"
    # 실제 집행된 이벤트가 전부 part-time 인지 검증
    assert all(ev.get("parttime") is True for ev in work_events), work_events


def test_parttime_wage_and_output_ratio() -> None:
    """Phase 16-G: part-time 집행 시 임금/생산이 full-time 대비 정해진 비율."""
    from ontology.layers import (
        PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD,
        PUBLIC_WORKS_PARTTIME_WAGE_RATIO,
        PUBLIC_WORKS_PARTTIME_OUTPUT_RATIO,
    )

    engine = _setup_engine()
    tid = _ready_territory(engine, treasury=5000.0, tax_income=500.0)
    territory = engine.territories[tid]
    full_wage = PUBLIC_WORKS_WAGE_PER_TICK * PUBLIC_WORKS_DURATION

    # 모든 non-lord persona employed, high tension → 전원 part-time
    for pid, persona in engine.personas.items():
        if persona.territory == tid and pid != territory.lord_id:
            persona.employment_id = "fake_emp"
            engine.wallets[pid].gold = 1000.0
            engine.inners[pid].consecutive_hunger_ticks = 0

    _inject_signals(
        engine, tid,
        growth=0.0, tension=PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD + 0.1,
        stability=0.0,
    )
    events = engine._process_public_works(tid)
    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events, events

    expected_wage = full_wage * PUBLIC_WORKS_PARTTIME_WAGE_RATIO
    for ev in work_events:
        assert ev.get("parttime") is True
        assert abs(ev["wage"] - expected_wage) < 1e-6, ev
        # produced_total 은 full-time 대비 OUTPUT_RATIO 배 (± farm_multiplier 외 변동은 없음)
        # 정확 검증은 base_output * DURATION * OUTPUT_RATIO
        # base_output 은 job별로 다르므로 간접 검증: produced_total > 0 and in_kind + to_persona == produced_total
        assert ev["produced_total"] > 0.0
        assert abs(ev["in_kind_to_territory"] + ev["to_persona"] - ev["produced_total"]) < 1e-6
```

### C-2. Signal Bootstrap 검증

```python
def test_signal_bootstrap_within_stale_window() -> None:
    """Phase 16-G: tick < STALE_SIGNAL_TICKS 에 SNN 신호 없으면 bootstrap 으로 진행."""
    from ontology.layers import (
        PUBLIC_WORKS_BOOTSTRAP_GROWTH,
        PUBLIC_WORKS_BOOTSTRAP_TENSION,
    )

    engine = _setup_engine()
    tid = "seorim"
    territory = engine.territories[tid]
    territory.treasury_gold = 3000.0
    territory.quarter_tax_income = 500.0
    territory.quarter_public_spend = 0.0
    # SNN 신호 없음 상태 명시
    territory.last_snn_signals = None
    territory.last_snn_signals_tick = -1
    engine.time.tick = 10  # < STALE_SIGNAL_TICKS(72)

    events = engine._process_public_works(tid)

    # bootstrap 덕분에 skip 되지 않고 진행 — skip_reason never_computed 가 없어야 함
    never_computed = [
        ev for ev in events
        if ev.get("type") == "public_works_skip_reason"
        and ev.get("detail") == "never_computed"
    ]
    assert never_computed == [], events


def test_signal_bootstrap_expires_after_stale_window() -> None:
    """Phase 16-G: tick >= STALE_SIGNAL_TICKS 이후에는 여전히 signal_stale skip."""
    engine = _setup_engine()
    tid = "seorim"
    territory = engine.territories[tid]
    territory.treasury_gold = 3000.0
    territory.quarter_tax_income = 500.0
    territory.last_snn_signals = None
    territory.last_snn_signals_tick = -1
    engine.time.tick = STALE_SIGNAL_TICKS + 1

    events = engine._process_public_works(tid)

    skip_reasons = [ev for ev in events if ev.get("type") == "public_works_skip_reason"]
    assert any(
        ev.get("reason") == "signal_stale" and ev.get("detail") == "never_computed"
        for ev in skip_reasons
    ), events
```

### C-3. 회귀 — full-time 기본값

기존 테스트에서 `parttime=False` 로 집행되는지 보강:

```python
def test_fulltime_wage_unchanged_for_unemployed() -> None:
    """Phase 16-G: unemployed 후보는 기존처럼 full-time 으로 집행 (parttime=False)."""
    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)

    events = engine._process_public_works(tid)
    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events, events

    # 기본 시나리오: 모두 unemployed → parttime=False, full wage
    full_wage = PUBLIC_WORKS_WAGE_PER_TICK * PUBLIC_WORKS_DURATION
    for ev in work_events:
        assert ev.get("parttime") is False, ev
        assert abs(ev["wage"] - full_wage) < 1e-6, ev
```

---

## 불변 증명

### A 불변

| 시나리오 | tension | food_crisis | parttime_enabled | 후보 풀 | 결과 |
|----------|:-:|:-:|:-:|------|------|
| 기본 (Phase 16-F 동작) | 0.2 | False | False | unemployed + low_gold_hungry | 기존 동작 유지 |
| high tension | 0.6 | False | True | + parttime_candidates | employed 도 포함 |
| food crisis | 0.2 | True | True | + parttime_candidates | employed 도 포함 |
| 일상 평시 | 0.2 | False | False | 기존 2개 그룹 | 변화 없음 |

- employed persona 의 `employment_id` 는 어느 경로에서도 변경되지 않음 (코드 grep으로 `persona.employment_id = ` 대입 없음 확인 필요)
- 우선순위 `unemployed > low_gold_hungry > parttime` 유지 → 기존 동작 보존
- Part-time 은 **임금/생산이 절반**이므로 treasury 소모 부담 작음

### B 불변

| 시나리오 | tick | last_snn_signals_tick | 동작 |
|----------|:-:|:-:|------|
| 초기 SNN 미생성 | 10 (< 72) | -1 | bootstrap signals 적용, 정상 진행 |
| 초기 SNN 미생성 (경계) | 72 (= 72) | -1 | skip: never_computed |
| 초기 SNN 미생성 (이후) | 100 | -1 | skip: never_computed |
| 정상 SNN 생성 후 fresh | 100 | 80 | 기존 경로 (sig_age=20, 정상) |
| 정상 SNN 생성 후 stale | 200 | 80 | skip: sig_age=120 > 72 |

---

## 검증

### 기계 검증 (필수 — 모두 PASS)

```bash
cd Projects/personas/loom
py -m pytest test_phase16_public_works.py -v
py -m pytest test_phase16c_internal_food_market.py -v
py -m pytest test_phase16d_dynamic_reserve.py -v
py -m pytest test_phase16e_agriculture.py -v
```

### Script형 회귀 (필수 — pytest 변환 금지)

```bash
cd Projects/personas/loom
py test_class_promotion.py    # stdout 에 "ALL PASS" 출력 확인
py test_nomos.py              # stdout 에 "ALL PASS" 출력 확인
```

### Hard 지표 재검증 (500틱, seed=42)

기존 Phase 16-F 검증 스크립트와 **동일** 조건 재실행. 판정 기준:

| 지표 | 기준 | Phase 16-F 값 | Phase 16-G 목표 |
|------|:-:|:-:|:-:|
| public_works | ≥ 50 | 43 | ≥ 50 |
| persona 평균 gold | ≥ 6000 | 18864 | ≥ 6000 유지 |
| NPC food_stockpile | ≤ 34 | 14 | ≤ 34 유지 |
| total_wealth delta | ≥ -40% | +124% | ≥ -40% 유지 |
| deaths | 0/10 | 0/10 | 0/10 유지 |

**기대 효과 분해**:
- no_candidates 12건 → part-time 열린 시나리오에서 ~7~9건 회수 예상
- signal_stale(never_computed) 3건 → bootstrap 으로 0건
- 합계: 43 + 10~12 = **53~55건** → Hard 통과

### 결정성 검증

```bash
py run_phase16_validation.py  # 또는 Phase 16-F 에서 사용한 스크립트
py run_phase16_validation.py  # 재실행
```
두 실행의 public_works 집행 건수 / persona gold 총합이 **정확히 일치** 해야 함 (self.rng/np_rng seed=42 결정성).

---

## Rollback

```bash
git checkout HEAD -- \
    Projects/personas/loom/ontology/layers.py \
    Projects/personas/loom/ontology/__init__.py \
    Projects/personas/loom/core/multi_tick_engine.py \
    Projects/personas/loom/test_phase16_public_works.py \
    Projects/personas/loom/test_phase16c_internal_food_market.py
```

데이터 영향: 없음 (코드/테스트만).

---

## 보고 형식 (구현 완료 후)

1. **변경 파일 목록** (예상 4~5개)
2. **신규 상수 값**: 5개 전부 지시서 값과 일치하는지 명시
3. **테스트 결과**:
   - 각 pytest 파일 PASS/FAIL 개수
   - script 회귀 2개 ALL PASS 여부
4. **Hard 지표 5개**: 각 수치와 기준 비교
5. **skip_reason 분해**: never_computed / no_candidates / budget_insufficient / below_min_treasury / rate_below_min 별 건수 비교 (Phase 16-F 대비)
6. **결정성 검증**: 동일 seed 2회 실행 결과 일치 여부
7. **이탈 사항**: 지시서와 다른 구현 있으면 이유와 함께
8. **자가 튜닝 보고**: Phase 12~16F 보호 상수 + Phase 16-G 5개 신규 상수 값을 지시서 범위 밖으로 조정하지 않았음 확인

---

## 자체 체크리스트

**공통**:
- [x] 메타 (긴급도/선행/유형/migration/의존)
- [x] 배경 + 근본 원인 꼬리 추적
- [x] [필수/선택/금지] 범위 태그
- [x] 변경 파일 표 + 변경 없음 명시
- [x] Rollback 섹션

**버그 수정**:
- [x] 재현 시나리오 (43 < 50, skip 분해)
- [x] 근본 원인 (성공이 다음 병목 노출)
- [x] 수정 코드 Before / After (§A-3, §B-3)
- [x] 회귀 테스트 (C-3 full-time unchanged)

**기능 추가**:
- [x] 신규 기능 계약 (part-time 의미론)
- [x] 이벤트 스키마 변경 (parttime, wage 필드 추가)
- [x] 테스트 시나리오 3개 (C-1, C-2, C-3)

**Codex 오용 방지**:
- [x] 모호 표현 없음 ("참고", "적절히" 등)
- [x] 허용 상수 5개만, 기존 상수 변경 금지 명시
- [x] 허용 파일 5개만, 그 외 금지 명시
- [x] 자가 튜닝 금지 (Hard 미달 시 구조적 제안만)
- [x] 지시서 원문 파일명 오류 교정 (`test_phase16d_dynamic_reserve.py`, `test_phase16e_agriculture.py`)
