# [Bug Fix] Phase 16-H — Stale Signal Decay Fallback (Guide Layer)

> 긴급도: 높음
> 선행 조건: Phase 16-G 구현 완료 (PHASE-16G-CODEX-INSTRUCTIONS.md)
> 작업 유형: 버그 수정 (guide-layer 보정)
> DB migration: 없음
> 외부 의존: 없음

---

## 배경

Phase 16-G 검증 결과:
- `persona gold`, `NPC food_stockpile`, `total_wealth`, `deaths` 4지표 PASS
- **`public_works ≥ 50` 여전히 미달 (38/60, Phase 16-F의 43보다 오히려 감소)**
- Bootstrap은 초기 `never_computed` 3건을 0으로 해결했지만, **새 병목 `signal_stale / sig_age=* 16건` 이 드러남**

**근본 원인 꼬리 추적**:
```
Bootstrap 으로 초기 economy 활성화
→ persona/territory state 연쇄 변화 (Phase 16-F 대비)
→ 일부 영지에서 SNN signal refresh 타이밍 어긋남
→ last_snn_signals_tick 은 있지만 갱신 빈도 낮음
→ sig_age 가 96, 120, 144, ..., 360 까지 누적
→ 현재 STALE gate: sig_age > 72 시 즉시 완전 skip
→ 16건 전부 막힘 (0/100 gate)
```

**진짜 근본**: 공공근로 정책 결정의 signal gate가 **너무 엄격한 이진 규칙** (72틱 초과 시 무조건 폐기). SNN은 영지별로 firing 빈도가 불규칙하며, guide layer가 이를 **완만한 감쇠**로 해석하면 대부분 집행 가능.

**비유**: 여론조사가 낡았다고 즉시 버리지 말고, **낡은 정도만큼 신뢰도를 낮춰서** 정책 참고. PersonaBrain/SNN 자체는 불변, guide layer만 유연화.

---

## 작업 범위

### [필수]
1. `_process_public_works` 의 stale signal gate 를 **decay fallback** 으로 교체
2. 3개 신규 상수 도입: decay window, decay floor, max age
3. decay 적용 시 `public_works` 이벤트에 관측 필드 추가
4. 신규 테스트 4개로 decay 동작 검증
5. Hard 지표 재검증: public_works ≥ 50 통과

### [선택]
- 없음

### [금지]
- Phase 12~16G 기존 상수 값 변경 (§ "변경 금지" 목록 참조)
- **특히 `STALE_SIGNAL_TICKS = 72` 값 변경 절대 금지** — 72 경계는 유지, decay 로 완만화만 허용
- PersonaBrain, SNN, `brain/**` 변경
- `_process_food_reserve`, `_process_internal_food_procurement` 등 다른 로직 변경
- `employment_id` 변경 (Phase 16-G 규칙 유지)
- 영지 간 보조금, 중앙 gold 이식, persona 간 direct gift (Phase 16-F/G 규칙 유지)
- 결정성 계약 변경 (`self.rng`, `self._np_rng`, seed=42)
- Hard 미달 시 상수 자가 튜닝 (값 변경은 지시 범위 내 명시 값만)
- 지시서 범위 밖 파일/테스트 생성

---

## 수정 허용 파일 (4개)

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/ontology/layers.py` | 신규 상수 3개 추가 | 수정 |
| `Projects/personas/loom/ontology/__init__.py` | 신규 상수 export | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | `_process_public_works` stale gate 변경 | 수정 |
| `Projects/personas/loom/test_phase16_public_works.py` | 신규 테스트 4개 추가 | 수정 |

**변경 없음 (금지)**:
- `brain/**` 전체
- `core/` 중 `multi_tick_engine.py` 외 파일
- 다른 테스트: `test_phase16c_internal_food_market.py`, `test_phase16d_dynamic_reserve.py`, `test_phase16e_agriculture.py`, `test_class_promotion.py`, `test_nomos.py`

---

## 상수 변경 가능/금지 목록

### 신규 추가 (3개 — 이 목록 외 신규 상수 금지)

| 이름 | 값 | 설명 |
|------|:-:|------|
| `PUBLIC_WORKS_STALE_DECAY_WINDOW` | `168.0` | sig_age가 STALE_SIGNAL_TICKS(72) 초과 후 선형 감쇠 기간. 72+168=240 틱에 floor 도달 |
| `PUBLIC_WORKS_STALE_DECAY_FLOOR` | `0.3` | decay 최소 신뢰도. 240 틱 초과해도 30% 유지 (집행 여지 보존) |
| `PUBLIC_WORKS_STALE_MAX_AGE` | `480` | 이 age 초과 시 decay 없이 완전 skip. STALE_SIGNAL_TICKS × 6.67배 |

### 변경 금지 (Phase 12~16G 보호 상수 — 자가 튜닝 불허)

**특히 중요 — 값 변경 금지**:
- `STALE_SIGNAL_TICKS = 72` (gate 경계는 유지, decay로 완만화만 허용)

기타 보호 상수:
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
PUBLIC_WORKS_TREASURY_INCOME_FLOOR_RATIO = 0.2          # Phase 16-F
PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD = 0.5           # Phase 16-G
PUBLIC_WORKS_PARTTIME_WAGE_RATIO = 0.5                  # Phase 16-G
PUBLIC_WORKS_PARTTIME_OUTPUT_RATIO = 0.5                # Phase 16-G
PUBLIC_WORKS_BOOTSTRAP_GROWTH = 0.3                     # Phase 16-G
PUBLIC_WORKS_BOOTSTRAP_TENSION = 0.2                    # Phase 16-G
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
JOB_BASE_OUTPUT / JOB_OUTPUT_MAP / NPC_PRICES / FACILITY_FEES (dict 전체)
```

---

## A. Decay Fallback 로직 변경

### A-1. 신규 상수 (`ontology/layers.py`)

**삽입 위치**: Phase 16-G 상수 (`PUBLIC_WORKS_BOOTSTRAP_TENSION`) 바로 아래

```python
PUBLIC_WORKS_STALE_DECAY_WINDOW: float = 168.0
"""Phase 16-H: stale signal 선형 감쇠 기간 (ticks).
sig_age가 STALE_SIGNAL_TICKS(72)를 초과한 뒤 이 창만큼 선형 감쇠.
72 + 168 = 240 틱 시점에 decay_floor 도달."""

PUBLIC_WORKS_STALE_DECAY_FLOOR: float = 0.3
"""Phase 16-H: stale signal 최소 신뢰도 (decay 하한).
240 틱 초과해도 30% 신뢰로 쓸 수 있게 하여 기본 집행 여지 확보.
0이 아닌 floor 로 설정하여 완전 0 붕괴 방지."""

PUBLIC_WORKS_STALE_MAX_AGE: int = 480
"""Phase 16-H: stale signal 최대 허용 age (ticks).
이 이상은 decay 로도 구제 안 함. 완전 skip.
STALE_SIGNAL_TICKS(72) × 6.67배. 반년치 이상 outdated signal은 무효."""
```

### A-2. Export (`ontology/__init__.py`)

기존 import 블록에 3개 추가:

```python
from .layers import (
    # ... 기존 ...
    PUBLIC_WORKS_STALE_DECAY_WINDOW,
    PUBLIC_WORKS_STALE_DECAY_FLOOR,
    PUBLIC_WORKS_STALE_MAX_AGE,
)
```

`__all__` 리스트 사용 시 해당 리스트에도 추가.

### A-3. `_process_public_works` stale gate 교체

**파일**: `Projects/personas/loom/core/multi_tick_engine.py`
**라인**: 2730~2760 (현재 bootstrap + stale gate 블록)

**변경 전** (Phase 16-G 현재 코드):
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
            sig_age = 0
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

**변경 후**:
```python
        # Phase 16-G: 초기 STALE_SIGNAL_TICKS(72) 동안 SNN 신호 없음 시 bootstrap
        signal_decay: float = 1.0  # Phase 16-H: 기본은 decay 없음
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
            sig_age = 0
        else:
            sig_age = self.time.tick - territory.last_snn_signals_tick
            # Phase 16-H: stale signal decay fallback.
            # sig_age 가 STALE_SIGNAL_TICKS 초과 시 즉시 skip 하지 않고, 
            # MAX_AGE 이하면 decay 를 적용한 signal 로 진행.
            if sig_age > PUBLIC_WORKS_STALE_MAX_AGE:
                return [{
                    "type": "public_works_skip_reason",
                    "territory": territory_id,
                    "reason": "signal_stale",
                    "detail": f"sig_age={sig_age}_max_exceeded",
                }]
            raw_signals = territory.last_snn_signals or {}
            if sig_age > STALE_SIGNAL_TICKS:
                # 선형 감쇠: sig_age=72 시 1.0, sig_age=240 시 DECAY_FLOOR
                over = float(sig_age - STALE_SIGNAL_TICKS)
                signal_decay = max(
                    PUBLIC_WORKS_STALE_DECAY_FLOOR,
                    1.0 - over / PUBLIC_WORKS_STALE_DECAY_WINDOW,
                )
                snn = {k: float(v) * signal_decay for k, v in raw_signals.items()}
            else:
                snn = raw_signals

        growth = float(snn.get("growth", 0.0))
        tension = float(snn.get("tension", 0.0))
        stability = float(snn.get("stability", 0.0))
```

**핵심 변경**:
- 기존: `sig_age > 72` → 즉시 skip
- 신규: `sig_age > 72 AND sig_age ≤ 480` → decay 적용 signal 로 진행
- 기존: `sig_age > 72` (상한 없음) → 무조건 skip
- 신규: `sig_age > 480` → 완전 skip (detail 에 `max_exceeded` 명시)
- `signal_decay` 변수는 이후 `public_works` 이벤트 필드로 전달 (§A-4)
- hunger 는 `_calc_hunger_pressure()` 로 별도 계산되므로 **decay 영향 없음** (territory 현재 상태 기반)

**상수 import 확인**: 파일 상단 `from ontology.layers import (...)` 블록에 3개 신규 상수 추가.

### A-4. `public_works` 이벤트에 `signal_decay` 필드 추가

**파일**: `Projects/personas/loom/core/multi_tick_engine.py`
**위치**: public_works 이벤트 append 블록 (루프 내)

기존 이벤트 dict 에 `"signal_decay"` 선택 필드 추가:

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
    "wage": round(wage_applied, 2),
    "parttime": is_parttime,
    "food_crisis": food_crisis_active,
    "farm_multiplier": round(farm_multiplier, 3),
    "signal_decay": round(signal_decay, 3),   # Phase 16-H: 1.0 = no decay, < 1.0 = stale signal
})
```

기존 필드 순서 변경 없이 `signal_decay` 필드만 추가. 기존 테스트가 사용하지 않는 선택 필드.

---

## B. 신규 테스트 (4개)

기존 `test_phase16_public_works.py` 맨 뒤에 추가.

### B-1. Decay 비활성 — fresh signal

```python
def test_signal_decay_inactive_when_fresh() -> None:
    """Phase 16-H: sig_age <= STALE_SIGNAL_TICKS 일 때 decay 미적용."""
    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)
    # fresh signals (tick 동일)

    events = engine._process_public_works(tid)
    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events, events
    for ev in work_events:
        assert abs(ev["signal_decay"] - 1.0) < 1e-6, ev
```

### B-2. Decay 활성 — moderately stale

```python
def test_signal_decay_active_when_stale() -> None:
    """Phase 16-H: STALE_SIGNAL_TICKS < sig_age < MAX_AGE 구간에서 선형 decay."""
    from ontology.layers import (
        PUBLIC_WORKS_STALE_DECAY_WINDOW,
        PUBLIC_WORKS_STALE_DECAY_FLOOR,
    )

    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)
    # 의도적으로 signals_tick 을 과거로 설정
    # sig_age = 120 (72 + 48): decay = 1.0 - 48/168 ≈ 0.714
    target_sig_age = 120
    engine.territories[tid].last_snn_signals_tick = (
        engine.time.tick - target_sig_age
    )

    events = engine._process_public_works(tid)
    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    # decay 적용된 signal 로도 집행 가능해야 (이전: skip 되었음)
    assert work_events, f"decay fallback 으로 집행되어야: {events}"

    expected_decay = max(
        PUBLIC_WORKS_STALE_DECAY_FLOOR,
        1.0 - (target_sig_age - STALE_SIGNAL_TICKS) / PUBLIC_WORKS_STALE_DECAY_WINDOW,
    )
    for ev in work_events:
        assert abs(ev["signal_decay"] - expected_decay) < 1e-6, ev
```

### B-3. Decay floor — very stale

```python
def test_signal_decay_floor_applied() -> None:
    """Phase 16-H: sig_age 가 window 를 넘어서면 DECAY_FLOOR 로 고정."""
    from ontology.layers import (
        PUBLIC_WORKS_STALE_DECAY_FLOOR,
        PUBLIC_WORKS_STALE_MAX_AGE,
    )

    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)
    # sig_age = 400 (window 168 훨씬 초과, MAX_AGE 480 이내)
    engine.territories[tid].last_snn_signals_tick = engine.time.tick - 400

    events = engine._process_public_works(tid)
    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events, f"floor 구간 decay 로 집행되어야: {events}"
    for ev in work_events:
        assert abs(ev["signal_decay"] - PUBLIC_WORKS_STALE_DECAY_FLOOR) < 1e-6, ev
```

### B-4. Max age 초과 — complete skip

```python
def test_signal_decay_max_age_skip() -> None:
    """Phase 16-H: sig_age > MAX_AGE 이면 decay 없이 완전 skip."""
    from ontology.layers import PUBLIC_WORKS_STALE_MAX_AGE

    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)
    # sig_age = MAX_AGE + 10
    engine.territories[tid].last_snn_signals_tick = (
        engine.time.tick - (PUBLIC_WORKS_STALE_MAX_AGE + 10)
    )

    events = engine._process_public_works(tid)
    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events == []
    skip_reasons = [ev for ev in events if ev.get("type") == "public_works_skip_reason"]
    assert any(
        ev.get("reason") == "signal_stale"
        and "max_exceeded" in str(ev.get("detail", ""))
        for ev in skip_reasons
    ), events
```

---

## 불변 증명

### Decay 테이블 (선형 감쇠 + floor + max)

| sig_age | over (age-72) | 1.0 - over/168 | max(floor, ...) | 비고 |
|:-:|:-:|:-:|:-:|:-:|
| 50 | - | - | **1.0** | fresh, decay 없음 |
| 72 | 0 | 1.000 | **1.000** | 경계, decay 없음 |
| 96 | 24 | 0.857 | **0.857** | Phase 16-G sig_age=96 2건 |
| 120 | 48 | 0.714 | **0.714** | Phase 16-G sig_age=120 2건 |
| 144 | 72 | 0.571 | **0.571** | Phase 16-G sig_age=144 2건 |
| 168 | 96 | 0.429 | **0.429** | Phase 16-G sig_age=168 2건 |
| 192 | 120 | 0.286 | **0.300** | floor 적용 |
| 240 | 168 | 0.000 | **0.300** | floor 적용 |
| 360 | 288 | -0.714 | **0.300** | Phase 16-G sig_age=360 1건 |
| 480 | 408 | -1.429 | **0.300** | max age 경계 |
| 481 | - | - | **skip** | max age 초과 |

**Phase 16-G 의 16건 sig_age 전부 480 이하** → decay 적용 가능 → 전부 집행 시도.

### Rate 계산 시 decay 효과

```
rate = BASE_ACTIVATION(0.04) + signal_component
signal_component = growth*0.5 + tension*0.3 + stability*0.15 + hunger*HUNGER_PRESSURE_WEIGHT
```

decay 는 **snn dict 값만** 감쇠 (growth/tension/stability). hunger 는 territory 현재 상태 기반이므로 decay 미적용.

예시:
- Phase 16-G 원래 rate 0.15 (BASE 0.04 + signal 0.11)
- sig_age=120 decay 0.714 적용 → rate = 0.04 + 0.11 × 0.714 = 0.119
- `RATE_MIN(0.03)` 여전히 초과 → 집행 가능 ✓

`BASE_ACTIVATION=0.04 > RATE_MIN=0.03` 이므로 decay 가 0.3 까지 떨어져도 rate 는 최소 0.04 유지 → rate_below_min skip 발생 안 함.

### Phase 16-F/G 에서 보존되어야 할 동작

- fresh signal (sig_age ≤ 72): 기존과 완전 동일 (decay=1.0)
- bootstrap (`last_snn_signals_tick < 0 && tick < 72`): Phase 16-G 동작 완전 동일
- `treasury < MIN`: 즉시 skip (기존 동작 유지)
- `last_snn_signals_tick < 0 && tick ≥ 72`: `never_computed` skip (Phase 16-G 동작 유지)

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

### Script형 회귀 (필수)

```bash
cd Projects/personas/loom
py test_class_promotion.py   # stdout "ALL PASS"
py test_nomos.py             # stdout "ALL PASS"
```

### 500틱 Hard 지표 (seed=42, 2회 실행 결정성 + 5지표 통과)

| 지표 | 기준 | Phase 16-F | Phase 16-G | **Phase 16-H 목표** |
|------|:-:|:-:|:-:|:-:|
| public_works | ≥ 50 | 43 | 38 | **≥ 50** |
| persona 평균 gold | ≥ 6000 | 18864 | 16623 | ≥ 6000 유지 |
| NPC food_stockpile | ≤ 34 | 14 | 14 | ≤ 34 유지 |
| total_wealth delta | ≥ -40% | +124% | +89% | ≥ -40% 유지 |
| deaths | 0/10 | 0/10 | 0/10 | 0/10 유지 |

**기대 효과**:
- Phase 16-G 의 sig_age=* 16건 → decay 로 전부 회수 (rate > RATE_MIN 유지 가정)
- `38 + 14~16 (decay 회수) = 52~54 건` → Hard 통과 안정권
- 만약 rate 감쇠로 일부 고용 수가 줄어도 이벤트 건수는 충분

### 결정성 검증

```bash
py run_phase16_validation.py    # 동일 검증 스크립트 2회 실행
py run_phase16_validation.py
```

두 실행의 public_works 건수·persona gold 합계·total_wealth 가 **정확히 일치** 해야 함. decay 계산은 순수 arithmetic 이므로 deterministic.

---

## Rollback

```bash
git checkout HEAD -- \
    Projects/personas/loom/ontology/layers.py \
    Projects/personas/loom/ontology/__init__.py \
    Projects/personas/loom/core/multi_tick_engine.py \
    Projects/personas/loom/test_phase16_public_works.py
```

데이터 영향: 없음.

---

## 보고 형식 (구현 완료 후)

1. **변경 파일 목록** (4개 예상)
2. **신규 상수 값**: 3개 전부 지시서 값과 일치 확인
3. **테스트 결과**:
   - pytest 4개 파일별 PASS/FAIL 개수
   - script 회귀 2개 ALL PASS 여부
   - B-1 ~ B-4 신규 테스트 PASS
4. **Hard 지표 5개**: 각 수치 + 기준 비교
5. **skip_reason 분해** (Phase 16-G 대비):
   - never_computed / no_candidates / budget_insufficient / below_min_treasury / **signal_stale (max_exceeded 여부 포함)**
6. **signal_decay 분포**: decay 적용된 public_works 이벤트의 signal_decay 값 분포 (최솟값/평균/건수)
7. **결정성 검증**: seed=42 2회 실행 결과 일치 여부
8. **이탈 사항**: 지시서와 다른 구현 있으면 이유와 함께
9. **자가 튜닝 보고**: Phase 12~16G 보호 상수 + Phase 16-H 3개 신규 상수 값 불변 확인

---

## 자체 체크리스트

**공통**:
- [x] 메타 (긴급도/선행/유형/의존)
- [x] 배경 + 근본 원인 꼬리 추적
- [x] [필수/선택/금지] 범위 태그
- [x] 변경 파일 표 + 변경 없음 명시
- [x] Rollback 섹션

**버그 수정**:
- [x] 재현 시나리오 (sig_age=* 16건 분포)
- [x] 근본 원인 (진짜 근본: 72틱 0/100 gate 의 경직성)
- [x] 수정 코드 Before / After (§A-3)
- [x] 회귀 테스트 (B-1: fresh 시 기존 동작 유지)

**리팩토링 (계약 변경)**:
- [x] Before / After (stale gate 로직)
- [x] 불변 증명 (Decay 테이블, rate 영향 분석)

**Codex 오용 방지**:
- [x] 모호 표현 없음
- [x] 허용 상수 3개만, 기존 상수 변경 금지 (특히 STALE_SIGNAL_TICKS 명시)
- [x] 허용 파일 4개만
- [x] 자가 튜닝 금지 (Hard 미달 시 구조적 제안만)
- [x] decay 공식 수치화 (테이블로 불변 검증)
