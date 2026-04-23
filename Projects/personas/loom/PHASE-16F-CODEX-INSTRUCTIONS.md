# [Bug Fix + Contract Update] Phase 16-F — 회귀 계약 정정 + Public Works 순환 참조 파괴

> 긴급도: 높음
> 선행 조건: Phase 16-E 구현 완료 (PHASE-16E-CODEX-INSTRUCTIONS.md)
> 작업 유형: 버그 수정 + 리팩토링 (계약 변경)
> DB migration: 없음
> 외부 의존: 없음

---

## 배경

Phase 16-E 구현 검증 결과:
- 신규 테스트 8/8 PASS, Phase 16-D 회귀 PASS
- **Phase 16-B/16-C 회귀 2건 FAIL** (Phase 16-D/16-E 계약 변경을 테스트가 못 따라감)
- **Hard 지표 2건 미달**: public_works 집행 13건(목표 ≥50), persona 평균 gold 2708(목표 ≥6000)

근본 원인 — 꼬리 추적:

1. **회귀 FAIL**: Phase 16-D에서 reserve_target을 동적 공식으로 변경(`residents × PER_PERSONA`), Phase 16-E에서 `BASE_ACTIVATION=0.04`와 `skip_reason` 이벤트 도입. 그러나 기존 테스트 어서션은 고정 임계값(30) / `events == []`를 그대로 가정.
2. **Hard 미달 — 자기강화 악순환**:
   ```
   persona gold 낮음 → 소비 저하 → 세수(qincome) 저하
   → cap_income = qincome × 1.2 작음 → budget_cap < wage(120)
   → public_works budget_insufficient 202건 → 집행 불발
   → 페르소나에게 gold 유입 없음 → persona gold 낮음 (순환 재진입)
   ```
   `cap_income` 공식이 `qincome`에만 의존하므로, 세수가 떨어지면 treasury가 쌓여 있어도 집행 불가.

---

## 작업 범위

### [필수]
1. 회귀 테스트 어서션 5건 갱신 — Phase 16-D/16-E 신규 계약에 맞춤
2. 신규 상수 `PUBLIC_WORKS_TREASURY_INCOME_FLOOR_RATIO` 도입
3. `_process_public_works`의 `cap_income` 공식에 treasury 기반 하한선 추가
4. Hard 지표 2건 통과: public_works ≥ 50, persona 평균 gold ≥ 6000

### [선택]
- 없음

### [금지]
- Phase 12~16E 기존 상수 값 변경 (§ "상수 변경 금지" 목록)
- `_process_food_reserve` / `_process_internal_food_procurement` 비즈니스 로직 변경
- PersonaBrain, SNN 내부, tick_engine의 다른 모듈 변경
- 결정성 계약 변경 (self.rng, self._np_rng, seed=42)
- 지표 달성을 위한 상수 자가 튜닝 (값 변경은 명시 허용 범위 내에서만)
- 지시서에 언급되지 않은 테스트 추가/삭제

---

## 수정 허용 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/test_phase16c_internal_food_market.py` | 어서션 1건 갱신 | 수정 |
| `Projects/personas/loom/test_phase16_public_works.py` | 어서션 4건 갱신 | 수정 |
| `Projects/personas/loom/ontology/layers.py` | 신규 상수 1개 추가 | 수정 |
| `Projects/personas/loom/ontology/__init__.py` | 신규 상수 export | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | `cap_income` 공식 1곳 | 수정 |

**변경 없음 (금지)**:
- `Projects/personas/loom/brain/**`
- `Projects/personas/loom/core/` 중 `multi_tick_engine.py` 외 전부
- 다른 테스트 파일 (`test_class_promotion.py`, `test_nomos.py`, `test_phase16d_*`, `test_phase16_pipeline.py` 등)
- `_process_public_works`, `_process_food_reserve` 의 지시 범위 외 로직

---

## 상수 변경 가능/금지 목록

### 신규 추가 (허용 — 이 항목만)

| 이름 | 값 | 위치 |
|------|:-:|------|
| `PUBLIC_WORKS_TREASURY_INCOME_FLOOR_RATIO` | `0.2` | `ontology/layers.py` (§B-1 참조) |

### 변경 금지 (Phase 12~16E 보호 상수)

아래 상수의 **값 변경 절대 금지**. Hard 지표를 맞추기 위한 자가 튜닝 불허.

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
STALE_SIGNAL_TICKS = 72
JOB_BASE_OUTPUT (dict 전체)
JOB_OUTPUT_MAP (dict 전체)
NPC_PRICES (dict 전체)
FACILITY_FEES (dict 전체)
```

---

## A. 회귀 테스트 갱신

### A-1. `test_phase16c_internal_food_market.py::test_food_stockpile_prefers_internal_over_npc`

**파일**: `Projects/personas/loom/test_phase16c_internal_food_market.py`
**라인**: 126–147

**근본 원인**: Phase 16-D가 `reserve_target`을 고정 30 → 동적 `residents × PER_PERSONA(14)`로 변경. 예컨대 residents=6이면 target=84로 기존 임계값 30을 훨씬 초과.

**변경 전 (line 145–147)**:
```python
    assert internal_events, events
    assert npc_events == []
    assert territory.food_reserve <= FOOD_STOCKPILE_RESERVE_THRESHOLD
```

**변경 후**:
```python
    assert internal_events, events
    assert npc_events == []
    # Phase 16-D: reserve_target = residents × FOOD_STOCKPILE_RESERVE_PER_PERSONA (동적).
    # 고정 THRESHOLD 비교 대신 (a) 내부 procurement 발생 (b) food_reserve 가
    # 내부 구매분과만 일치 (NPC 혼합 없음) 를 검증.
    assert territory.food_reserve > 0.0
    total_internal_qty = sum(float(ev.get("quantity", 0.0)) for ev in internal_events)
    assert abs(territory.food_reserve - total_internal_qty) < 1e-6
```

**테스트 의도**:
- [x] 내부 procurement이 NPC 상점보다 우선 (유지)
- [x] 세력자 잉여를 영지가 활용 (유지)
- [변경] 고정 임계값 → 내부 경로 단일성 (NPC 혼합 없음)

**주의**: `internal_events[0]["quantity"]` 필드명이 다르다면 실제 이벤트 키에 맞춰 조정. (engine 구현 기준으로 맞춤 — 없으면 `internal_events[0]` dict 조사 후 quantity/procured 중 존재하는 키 사용.)

---

### A-2. `test_phase16_public_works.py::test_rate_threshold_suppression` → `test_base_activation_floor`

**파일**: `Projects/personas/loom/test_phase16_public_works.py`
**라인**: 80–86

**근본 원인**: Phase 16-E에서 `BASE_ACTIVATION=0.04 > RATE_MIN=0.03`. signal_component는 양수 signal만 가산하므로 `rate ≥ 0.04 > 0.03`. 따라서 `rate_below_min` 분기는 양수 signal 환경에서 도달 불가. 테스트의 원래 의도("low signal → 억제")는 signal 값 범위상 재현 불가.

**변경 전 (line 80–86)**:
```python
def test_rate_threshold_suppression() -> None:
    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.0, tension=0.0, stability=0.0)

    events = engine._process_public_works(tid)

    assert events == []
```

**변경 후**:
```python
def test_base_activation_floor() -> None:
    """Phase 16-E: BASE_ACTIVATION=0.04 > RATE_MIN=0.03 이므로
    zero signal 조건에서도 rate 바닥선이 보장되어 공공근로 집행이 발생.
    (원본 test_rate_threshold_suppression 은 BASE 도입으로 도달 불가능해짐.)"""
    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.0, tension=0.0, stability=0.0)

    events = engine._process_public_works(tid)

    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events, f"BASE_ACTIVATION floor 가 rate 바닥선을 보장해야 함: {events}"
```

---

### A-3. `test_phase16_public_works.py::test_treasury_min_guard`

**파일**: `Projects/personas/loom/test_phase16_public_works.py`
**라인**: 89–99

**근본 원인**: Phase 16-E에서 `treasury < MIN` 시 `skip_reason` 이벤트(reason=budget_insufficient, detail=below_min_treasury) 반환. 기존 `events == []` 가정 불성립.

**변경 전 (line 99)**:
```python
    assert events == []
```

**변경 후** (전체 테스트 본문을 아래로 교체):
```python
def test_treasury_min_guard() -> None:
    engine = _setup_engine()
    tid = _ready_territory(
        engine,
        treasury=PUBLIC_WORKS_MIN_TREASURY - 1,
        growth=0.8,
    )

    events = engine._process_public_works(tid)

    # Phase 16-E: skip_reason 이벤트 반환 (관측용)
    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events == []
    skip_reasons = [ev for ev in events if ev.get("type") == "public_works_skip_reason"]
    assert len(skip_reasons) == 1
    assert skip_reasons[0].get("reason") == "budget_insufficient"
    assert skip_reasons[0].get("detail") == "below_min_treasury"
```

---

### A-4. `test_phase16_public_works.py::test_budget_cap_enforced`

**파일**: `Projects/personas/loom/test_phase16_public_works.py`
**라인**: 102–108

**근본 원인**:
(a) Phase 16-E skip_reason 이벤트 반환 (기존 `events == []` 불성립)
(b) Phase 16-F에서 treasury 기반 floor 추가. 기존 시나리오(treasury=5000)에서는 `floor = 5000 × 0.2 = 1000 > wage(120)`이므로 budget_cap 충족 → 억제 안 됨.

**변경 전 (line 102–108)**:
```python
def test_budget_cap_enforced() -> None:
    engine = _setup_engine()
    tid = _ready_territory(engine, treasury=5000.0, tax_income=50.0, growth=0.8)

    events = engine._process_public_works(tid)

    assert events == []
```

**변경 후**:
```python
def test_budget_cap_enforced() -> None:
    """Phase 16-F: cap_income = max(qincome × 1.2, treasury × FLOOR_RATIO).
    budget_cap < wage 조건을 만들려면 treasury와 qincome 모두 낮아야.
    treasury=550: floor=110, cap_treasury=275, qincome_tax=60
    → cap_income=max(110,60)=110, budget_cap=min(110,275)=110 < wage(120) → skip."""
    engine = _setup_engine()
    tid = _ready_territory(engine, treasury=550.0, tax_income=50.0, growth=0.8)

    events = engine._process_public_works(tid)

    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events == []
    skip_reasons = [ev for ev in events if ev.get("type") == "public_works_skip_reason"]
    assert any(ev.get("reason") == "budget_insufficient" for ev in skip_reasons), events
```

**시나리오 검산**:
- `treasury = 550 ≥ PUBLIC_WORKS_MIN_TREASURY(500)` → MIN guard 통과
- `cap_income_from_tax = 50 × 1.2 = 60`
- `cap_income_from_treasury = 550 × 0.2 = 110`
- `cap_income = max(60, 110) = 110`
- `cap_treasury = 550 × 0.5 = 275`
- `budget_cap = min(110, 275) = 110`
- `wage_per_person = 5 × 24 = 120`
- `110 < 120` → `budget_insufficient` skip_reason 발생 ✓

---

### A-5. `test_phase16_public_works.py::test_stale_signal_suppressed`

**파일**: `Projects/personas/loom/test_phase16_public_works.py`
**라인**: 190–202

**근본 원인**: Phase 16-E에서 `sig_age > STALE_SIGNAL_TICKS` 시 `skip_reason` 이벤트(reason=signal_stale) 반환. 기존 `events == []` 불성립.

**변경 전 (line 202)**:
```python
    assert events == []
```

**변경 후** (전체 테스트 본문을 아래로 교체):
```python
def test_stale_signal_suppressed() -> None:
    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)
    _inject_signals(
        engine,
        tid,
        tick=engine.time.tick - STALE_SIGNAL_TICKS - 1,
        growth=0.8,
    )

    events = engine._process_public_works(tid)

    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events == []
    skip_reasons = [ev for ev in events if ev.get("type") == "public_works_skip_reason"]
    assert any(ev.get("reason") == "signal_stale" for ev in skip_reasons), events
```

---

## B. Public Works 예산 공식 변경 (Hard 지표 해소)

### B-1. 신규 상수 (`ontology/layers.py`)

**삽입 위치**: line 243 다음 (기존 `PUBLIC_WORKS_LOW_GOLD_THRESHOLD = 300.0` 아래, 관련 상수 그룹 내)

**추가 코드**:
```python
PUBLIC_WORKS_TREASURY_INCOME_FLOOR_RATIO: float = 0.2
"""Phase 16-F: 공공근로 예산의 treasury 기반 하한선 비율.
세수(qincome)가 낮아도 금고가 충분하면 공공근로 집행 가능하도록 순환 참조를 파괴.
근본: persona gold 낮음 → 소비/세수 저하 → cap_income 저하 → public_works 불발
     → 페르소나 gold 유입 없음 (자기강화 악순환).
Treasury의 20%를 예산 floor로 사용하여 cycle 을 끊음. 
cap_treasury(=0.5 × treasury) 로 overspending은 계속 방지됨."""
```

### B-2. Export (`ontology/__init__.py`)

기존 `from .layers import (...)` 블록에 신규 상수 추가:

```python
from .layers import (
    # ... 기존 export 목록 ...
    PUBLIC_WORKS_TREASURY_INCOME_FLOOR_RATIO,
)
```

또는 `__all__` 리스트 사용 시 해당 리스트에도 추가.

### B-3. `_process_public_works` 예산 공식 변경

**파일**: `Projects/personas/loom/core/multi_tick_engine.py`
**라인**: 2763–2770

**변경 전**:
```python
        wage_per_person = PUBLIC_WORKS_WAGE_PER_TICK * PUBLIC_WORKS_DURATION
        qincome = float(getattr(territory, "quarter_tax_income", 0.0))
        cap_income = (
            qincome * QUARTER_TAX_BUDGET_MULTIPLIER
            if qincome > 0 else float("inf")
        )
        cap_treasury = territory.treasury_gold * PUBLIC_WORKS_MAX_TREASURY_RATIO
        budget_cap = min(cap_income, cap_treasury)
```

**변경 후**:
```python
        wage_per_person = PUBLIC_WORKS_WAGE_PER_TICK * PUBLIC_WORKS_DURATION
        qincome = float(getattr(territory, "quarter_tax_income", 0.0))
        cap_income_from_tax = (
            qincome * QUARTER_TAX_BUDGET_MULTIPLIER
            if qincome > 0 else 0.0
        )
        cap_income_from_treasury = (
            territory.treasury_gold * PUBLIC_WORKS_TREASURY_INCOME_FLOOR_RATIO
        )
        cap_income = max(cap_income_from_tax, cap_income_from_treasury)
        cap_treasury = territory.treasury_gold * PUBLIC_WORKS_MAX_TREASURY_RATIO
        budget_cap = min(cap_income, cap_treasury)
```

**핵심 변경**:
- 기존: `qincome == 0` 이면 `inf` 사용 (cap_treasury만 유효) — 논리적 특수 케이스
- 신규: `qincome ≤ 0` 이면 `0` 으로, treasury floor가 자연스럽게 하한선 제공 — 일관성
- `cap_treasury = treasury × 0.5` 의 overspending 방지는 그대로 유지

**상수 import 확인**: 파일 상단 import 블록에 `PUBLIC_WORKS_TREASURY_INCOME_FLOOR_RATIO` 추가 필요. 기존 import 형식에 맞춰 기입 (한 줄 추가 or 기존 다중 import에 끼워넣기).

### B-4. 불변 증명

| 시나리오 | qincome | treasury | cap_tax | cap_floor | cap_income | cap_treasury | budget_cap | wage | 결과 |
|----------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 기준 (test_budget_cap_enforced after) | 50 | 550 | 60 | 110 | 110 | 275 | 110 | 120 | **skip** ✓ |
| MIN 임계 (treasury=500) | 0 | 500 | 0 | 100 | 100 | 250 | 100 | 120 | **skip** (budget) |
| 순환 탈출 (treasury 누적 후) | 10 | 2000 | 12 | 400 | 400 | 1000 | 400 | 120 | **집행 3인** ✓ |
| 정상 고세수 | 1000 | 3000 | 1200 | 600 | 1200 | 1500 | 1200 | 120 | **집행 10인** (기존 유지) |
| 극단 overspending 방지 | 100000 | 200 | 120000 | 40 | 120000 | 100 | 100 | 120 | **skip** (cap_treasury 보호) |

**보장 사항**:
1. 금고 총액의 50% 이상은 한 분기에 소진 불가 (`cap_treasury` 유지)
2. `treasury ≥ MIN_TREASURY(500)` 상황에서 최소 예산 100 (원활한 집행은 아니지만 cycle 탈출 시동)
3. `treasury ≥ 600` → floor 120 → 최소 1인 집행 보장 (누적 시 자기치유 가속)
4. 고세수 상황에서는 기존 공식과 동일 (tax path 우세)

---

## 검증

### 기계 검증 (필수 — 모두 PASS)

**Windows (사용자 환경)**:
```bash
cd Projects/personas/loom
py -m pytest test_phase16_public_works.py -v
py -m pytest test_phase16c_internal_food_market.py -v
py -m pytest test_phase16d_public_works_foodmode.py -v
py -m pytest test_phase16_pipeline.py -v
```

**회귀 미폭 검증**:
```bash
py -m pytest test_class_promotion.py test_nomos.py -v
```

### 기능 검증 (Hard 지표 — 필수)

500틱 시뮬레이션 스크립트 (Phase 16-E 검증과 동일한 것 재실행):

```bash
cd Projects/personas/loom
py run_phase16_validation.py    # 또는 Phase 16-E 에서 사용한 검증 스크립트
```

판정 기준 (모두 통과):
- [ ] public_works 집행 건수 ≥ 50 (Phase 16-E: 13 → **3.8×**)
- [ ] persona 평균 gold ≥ 6000 (Phase 16-E: 2708 → **2.2×**)
- [ ] 사망 건수 = 0 (Phase 16-E 달성 유지)
- [ ] total_wealth 변화 ≥ -40% (Phase 16-E 달성 유지)
- [ ] NPC food_stockpile 이벤트 ≤ 34 (Phase 16-E 달성 유지)

### 관측 검증 (결정성 포함)

- [ ] 동일 seed(42) 에서 재현 가능한 결과 확인 (2회 실행 시 동일 집행 건수)
- [ ] `public_works_skip_reason` 이벤트 분포 확인 (`budget_insufficient` 급감 예상)

---

## Rollback

변경 파일 5개 모두 revert:
```bash
git checkout HEAD -- \
    Projects/personas/loom/test_phase16c_internal_food_market.py \
    Projects/personas/loom/test_phase16_public_works.py \
    Projects/personas/loom/ontology/layers.py \
    Projects/personas/loom/ontology/__init__.py \
    Projects/personas/loom/core/multi_tick_engine.py
```

데이터 영향: 없음 (코드/테스트 변경만).

---

## 보고 형식 (구현 완료 후)

1. **변경 파일 목록** (5개 예상)
2. **테스트 결과**:
   - 각 테스트 파일별 PASS/FAIL 개수
   - 실패 있을 경우 실패 테스트명 + 짧은 이유
3. **Hard 지표 수치**:
   - public_works, persona gold, deaths, total_wealth, NPC food_stockpile
4. **이탈 사항**: 지시서와 다르게 구현된 부분 있으면 이유와 함께 명시
5. **자가 튜닝 보고**: 상수 값을 지시서 허용 범위 밖으로 조정하지 않았음을 명시. Hard 미달 시 추가 구조적 제안 (값 변경 제안 금지).

---

## 자체 체크리스트

**공통**:
- [x] 메타 (긴급도/선행/유형/migration/의존) 포함
- [x] 배경 3문장 + 근본 원인 꼬리 추적
- [x] [필수/선택/금지] 범위 태그
- [x] 변경 파일 표 + 변경 없음 명시
- [x] Rollback 섹션

**버그 수정**:
- [x] 재현 시나리오 (2 회귀 실패 + 2 Hard 미달)
- [x] 근본 원인 (각 항목별 명시)
- [x] 수정 코드 Before / After
- [x] 회귀 테스트 (기존 Phase 12–15 + Phase 16-D/E 신규)

**리팩토링 (계약 변경)**:
- [x] Before / After 구조 (cap_income 공식)
- [x] 불변 증명 (B-4 표: 5 시나리오)

**Codex 오용 방지**:
- [x] "적절히", "알아서", "참고" 모호 표현 없음
- [x] 허용 상수 1개만 신규, 기존 상수 변경 금지 명시
- [x] 허용 파일 5개만, 그 외 금지 명시
- [x] 자가 튜닝 금지 명시 (상수 값 바꿔서 Hard 통과 시도 불허)
