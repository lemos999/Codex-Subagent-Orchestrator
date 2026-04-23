# [기능+리팩토링] Phase 16-D: Dynamic Reserve + Base Activation — Codex 구현 지시서

> 긴급도: 높음 (Phase 16-C Hard 기준 3개 실패 — persona gold −85.2%, public_works 6건, NPC food_stockpile 71건)
> 선행 조건: Phase 16-C 구현 완료 (`_process_internal_food_procurement`, `_calc_hunger_pressure`, `_weighted_sample_without_replacement`, `self._np_rng`)
> 작업 유형: 기능(새 필드 1개) + 리팩토링(기존 메서드 2개 로직 교체, 상수 3개 값 변경, 신규 상수 4개)
> DB migration: 없음 (Python 메모리 시뮬)
> 외부 의존: 없음 (기존 numpy·random만 사용)

---

## 배경

Phase 16-C 구현은 compile·7 tests·결정성 모두 PASS했지만 2000틱 관측에서:

| 지표 | 기준 | 실제 | 결과 |
|---|---|---|---|
| persona gold loss | ≤ 70% (final ≥ 6000) | −85.2% (final 2960) | FAIL |
| public_works events | ≥ 50 | 6 | FAIL |
| NPC food_stockpile events | ≤ 34 | 71 | FAIL |
| total wealth | ≥ −40% | +13.8% | PASS |
| deaths | 0 | 0 | PASS |

공급 내역: internal 0.1 · P2P 137 · **NPC 798** (98.6% 여전히 외부 의존).

### 근본 원인 4단 (코드 기반 재추적)

**A. Internal procurement 1건만 발동**
- `_process_internal_food_procurement:2541` 에서 candidates 필터가 `food_stock - PERSONA_FOOD_SAFE_STOCK(24) > 0` 요구
- Phase 11 생존 소비 1/tick + eat 이벤트로 페르소나 평균 food 재고가 **8~16** 범위에서 진동 — 24 돌파 확률 희박
- **근본**: `SAFE_STOCK=24`가 farmer·일반 구분 없이 일괄 적용되어 평시 잉여를 구조적으로 포착 불가

**B. Public works 6건만 발동 (2000/24=83 gates 중 7%)**
- `_process_public_works:2633` 의 rate 공식 `growth*0.5 + tension*0.3 + stability*0.15 + hunger*0.2` 는 선형 합. 베이스 없음
- SNN 신호 평균이 낮으면 rate ≈ 0 → rate_min 0.05 문턱 탈락
- **근본**: "최소 재분배"를 SNN 강도 신호에 100% 의존 — 약신호 시기 gold 재분배가 아예 멈춤

**C. NPC food_stockpile 71건 (기준 ≤34)**
- `_process_food_reserve:1395` 의 `stockpile_needed = food_shortfall≥1 AND food_priority>0.4 AND reserve<FOOD_STOCKPILE_RESERVE_THRESHOLD(30)` — 쿨다운 없음
- reserve가 30 근처에서 진동하면 24틱마다 매수 반복
- **근본**: 고정 threshold 30은 인구 대비 3일치(10인 기준). 내부 조달 시간을 벌어주지 않고 즉시 NPC로 향함

**D. Persona gold 회복 실패**
- Public works (주요 재분배 경로)가 6회만 발동 → 재분배 금액 미미
- NPC treasury purchase 798×15 = **11,970 gold** 외부 유출로 수지 적자
- **근본**: B + C 의 결과값. Phase 16-D에서 B·C 해결하면 D는 자동 회복 예상

### Phase 16-D 4축 개입

| 축 | 대응 근본 | 변경 | 기대 효과 |
|---|---|---|---|
| §1 | A | `PERSONA_FOOD_SAFE_STOCK 24→12` | candidates 평시 2~4명 존재 |
| §2 | C | `FOOD_STOCKPILE_RESERVE_THRESHOLD` 고정값 → 동적 `residents × 14` | NPC 매수 충족 문턱 완화, 내부 조달 수요 상시 존재 |
| §3 | B | `PUBLIC_WORKS_BASE_ACTIVATION=0.04` 추가 + `RATE_MIN 0.05→0.03` | signal 약해도 `0.04 ≥ 0.03` 로 상시 발동 |
| §4 | C | `NPC_FOOD_PURCHASE_COOLDOWN_TICKS=48` + reserve ratio gate | NPC 매수 빈도 반감 + 내부 경로 우선 |

**철학 준수**: 새 SNN 뉴런 0, 축 0 / 새 계산 차원 0 / Phase 16-C 구조 유지 / gold 하드코딩 주입 0 / food_stockpile 경로 유지(제거 금지).

설계 원본: 본 지시서 §0 (근본 원인 4단 추적이 설계 문서 역할 겸함).

---

## 작업 범위

### [필수]

1. `ontology/layers.py` 상수 4개 변경/추가
   - `PERSONA_FOOD_SAFE_STOCK`: 24.0 → **12.0**
   - `PUBLIC_WORKS_RATE_MIN`: 0.05 → **0.03**
   - (신규) `PUBLIC_WORKS_BASE_ACTIVATION: float = 0.04`
   - (신규) `NPC_FOOD_PURCHASE_COOLDOWN_TICKS: int = 48`
   - (신규) `FOOD_STOCKPILE_RESERVE_PER_PERSONA: float = 14.0`
   - (신규) `NPC_FOOD_TRIGGER_RESERVE_RATIO: float = 0.5`
   - `FOOD_STOCKPILE_RESERVE_THRESHOLD`는 **유지** (deprecated, import 호환 용도로만 남겨두고 사용 지점에서 대체)

2. `Territory` 에 신규 필드 추가
   - `last_npc_food_purchase_tick: int = -9999` (`ontology/layers.py` 의 Territory dataclass)

3. `_process_food_reserve` 재작성 (고정 threshold → 동적 reserve target + cooldown + gate 분리)

4. `_process_public_works` rate 공식에 `PUBLIC_WORKS_BASE_ACTIVATION` 가산, `PUBLIC_WORKS_RATE_MIN` 0.03 반영

5. `ontology/__init__.py` 신규 상수 4개 export

6. `test_phase16d_dynamic_reserve.py` 신규 **7 tests** 작성

7. `observe_phase15_stack.py` Phase 16-D 섹션 추가
   - NPC cooldown trigger 건수 (쿨다운으로 인해 스킵된 매수 시도)
   - reserve_target 평균값
   - public_works base 기여도 비율 (rate 중 base 가 차지하는 비율 평균)

8. 합격 기준 (Hard): persona gold loss ≤ 70% (final ≥ 6000) **AND** public_works events ≥ 50 **AND** NPC food_stockpile events ≤ 34 **AND** total_wealth ≥ −40% **AND** deaths = 0 **AND** Phase 16-D tests 7/7 PASS **AND** 모든 회귀 테스트 PASS

### [선택]

- Hard 실패 시 본 지시서 §10 Phase 16-E 대안표 기록만. **자가 튜닝 금지** (이 지시서의 상수 값을 마음대로 조정하지 말 것 — 실패 시 리뷰 리포트로 돌아올 것)
- 관측 스크립트 ASCII 막대 그래프 (선택, reserve_target 시계열 등)

### [금지]

- 새 PersonaBrain 뉴런 추가
- 새 SNN 축 추가
- `food_stockpile` NPC 매수 경로 **완전 제거** (후순위로만 유지)
- 직접 gold 주입 (e.g., `wallet.receive(500)` 형태의 경제 외 gift)
- Phase 12~15 상수 재튜닝 (`GOLD_DIRECT_PAY_RATIO`, `snlt_gold_per_tick`, tax rate 등)
- Phase 16-B/C 핵심 상수 (`INTERNAL_FOOD_PRICE_RATIO`, `HUNGER_PRESSURE_WEIGHT`, `PUBLIC_WORKS_FARMER_BIAS`, `HUNGER_TRIGGER_THRESHOLD`, `PUBLIC_WORKS_IN_KIND_RATIO`, `STALE_SIGNAL_TICKS`) 값 변경
- `FOOD_STOCKPILE_RESERVE_THRESHOLD` 상수 삭제 (외부 테스트·문서 호환 위해 **유지만** 하고 `_process_food_reserve` 내부에서만 사용 중단)
- `_process_internal_food_procurement` / `_calc_hunger_pressure` / `_weighted_sample_without_replacement` 로직 변경 (Phase 16-C 확정)
- 새 `random.random()` / `np.random.random()` 전역 호출 추가 (모두 `self._np_rng` 또는 `self.rng` 사용)

---

## 프레임워크·프로젝트 제약

- Python 3.x, numpy. 추가 패키지 금지.
- `MultiTickEngine` 은 `Projects/personas/loom/core/multi_tick_engine.py` 에 있음.
- `self.rng` (Python `random.Random`) 와 `self._np_rng` (numpy Generator) 는 Phase 16-C 에서 이미 추가됨. 재초기화 금지.
- Territory dataclass 는 `Projects/personas/loom/ontology/layers.py:116` 전후. 기존 필드 순서 유지, 신규 필드는 가장 마지막에 추가.
- 파일 >500 LOC 는 offset/limit 청크 읽기 후 편집. 편집 후 3회마다 검증 읽기.
- 모든 신규 상수는 `ontology/layers.py` 정의 + `ontology/__init__.py` export.
- `np.random.default_rng(seed + offset)` 와 `hash(...)` 기반 seed 패턴은 **변경 금지** (이미 결정적).

---

## 변경 파일

| 파일 | 작업 | 유형 |
|---|---|:---:|
| `Projects/personas/loom/ontology/layers.py` | 상수 3개 값 변경 + 신규 상수 4개 + Territory 필드 1개 | 수정 |
| `Projects/personas/loom/ontology/__init__.py` | 신규 상수 4개 export | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | `_process_food_reserve` 재작성 + `_process_public_works` rate 공식 2줄 수정 | 수정 |
| `Projects/personas/loom/observe_phase15_stack.py` | Phase 16-D 섹션 추가 (cooldown trigger 집계, reserve_target 평균, base 기여도) | 수정 |
| `Projects/personas/loom/test_phase16d_dynamic_reserve.py` | 7 tests 신규 | 추가 |

**변경 없음 (금지):**

- `Projects/personas/loom/brain/*.py` — PersonaBrain 건드리지 말 것
- `Projects/personas/loom/test_phase16_public_works.py`, `test_phase16c_internal_food_market.py` — 기존 테스트 수정 금지 (회귀 보호)
- `Projects/personas/loom/core/tick_engine.py` — MultiTickEngine 아닌 레거시. 건드리지 말 것
- `packages/launcher/**` — 무관
- `FOOD_STOCKPILE_RESERVE_THRESHOLD` 상수 값 (30.0 유지)

---

## 구체 사양

### § 1. 상수 변경 (`ontology/layers.py`)

**위치**: 기존 Phase 16-B/C 상수 블록(line 220~235 근처) 내에서 값 수정 + 신규 블록 추가.

#### 1-A. 기존 값 변경

```python
# Before (line 221~232 중 일부)
PUBLIC_WORKS_RATE_MIN: float = 0.05
PERSONA_FOOD_SAFE_STOCK: float = 24.0

# After
PUBLIC_WORKS_RATE_MIN: float = 0.03          # Phase 16-D: 0.05 → 0.03 (base activation 반영)
PERSONA_FOOD_SAFE_STOCK: float = 12.0        # Phase 16-D: 24 → 12 (surplus 포착 확률↑)
```

#### 1-B. 신규 상수 (기존 Phase 16-C 상수 블록 바로 뒤)

```python
# ── Phase 16-D: Dynamic Reserve + Base Activation ───────
PUBLIC_WORKS_BASE_ACTIVATION: float = 0.04
"""SNN 신호가 0일 때도 공공근로가 최소한 발동되도록 rate 에 가산되는 베이스."""

NPC_FOOD_PURCHASE_COOLDOWN_TICKS: int = 48
"""NPC treasury food 매수 최소 간격 (24틱 주기 대비 2배 — 내부 조달 시간 확보)."""

FOOD_STOCKPILE_RESERVE_PER_PERSONA: float = 14.0
"""인구 1인당 목표 food reserve (2주치). Territory reserve target = residents × 이 값."""

NPC_FOOD_TRIGGER_RESERVE_RATIO: float = 0.5
"""NPC 매수 발동 threshold — reserve < reserve_target × 이 값 일 때만 NPC 매수 허용."""
```

#### 1-C. Territory 필드 추가

**위치**: `Territory` dataclass 의 기존 필드 목록 끝 (Phase 16-C 에서 추가한 `internal_food_procured_total: float = 0.0` 바로 아래).

```python
    internal_food_procured_total: float = 0.0          # Phase 16-C (기존)
    last_npc_food_purchase_tick: int = -9999           # Phase 16-D (신규)
```

**중요**: `-9999` 는 "아직 한 번도 매수한 적 없음" 센티널. 쿨다운 비교 시 `self.time.tick - territory.last_npc_food_purchase_tick >= NPC_FOOD_PURCHASE_COOLDOWN_TICKS` 가 항상 True 가 되게.

---

### § 2. `ontology/__init__.py` export 추가

**위치**: 기존 `from .layers import (...)` 블록과 `__all__` 리스트 양쪽에 4개 추가.

```python
# Before (예시 — 실제 파일 구조 확인 후 동일 섹션에 삽입)
from .layers import (
    ...,
    INTERNAL_FOOD_PRICE_RATIO, PERSONA_FOOD_SAFE_STOCK,
    PUBLIC_WORKS_RATE_MIN, HUNGER_PRESSURE_WEIGHT,
    PUBLIC_WORKS_FARMER_BIAS, HUNGER_TRIGGER_THRESHOLD,
)

# After
from .layers import (
    ...,
    INTERNAL_FOOD_PRICE_RATIO, PERSONA_FOOD_SAFE_STOCK,
    PUBLIC_WORKS_RATE_MIN, HUNGER_PRESSURE_WEIGHT,
    PUBLIC_WORKS_FARMER_BIAS, HUNGER_TRIGGER_THRESHOLD,
    # Phase 16-D
    PUBLIC_WORKS_BASE_ACTIVATION,
    NPC_FOOD_PURCHASE_COOLDOWN_TICKS,
    FOOD_STOCKPILE_RESERVE_PER_PERSONA,
    NPC_FOOD_TRIGGER_RESERVE_RATIO,
)

__all__ = [
    ...,
    # Phase 16-D
    "PUBLIC_WORKS_BASE_ACTIVATION",
    "NPC_FOOD_PURCHASE_COOLDOWN_TICKS",
    "FOOD_STOCKPILE_RESERVE_PER_PERSONA",
    "NPC_FOOD_TRIGGER_RESERVE_RATIO",
]
```

`FOOD_STOCKPILE_RESERVE_THRESHOLD` 는 **계속 export** (테스트 호환).

---

### § 3. `_process_food_reserve` 재작성 (`multi_tick_engine.py:1343`)

**Before (현재 구현, 요약)**:

```python
def _process_food_reserve(self) -> list[dict]:
    if self.time.tick % 24 != 0:
        return []
    for tid, territory in self.territories.items():
        ...
        reserve_target = len(residents) * 24.0     # unused — stockpile check 만 사용
        food_shortfall = reserve_target - territory.food_reserve
        stockpile_needed = (
            food_shortfall >= 1
            and territory.policy.food_priority > 0.4
            and territory.food_reserve < FOOD_STOCKPILE_RESERVE_THRESHOLD  # 고정 30
        )
        if stockpile_needed:
            # internal procurement 시도
            internal_target = min(
                max(0.0, FOOD_STOCKPILE_RESERVE_THRESHOLD - territory.food_reserve),
                buy_qty_limit,
            )
            ...
        if (stockpile_needed and not has_market_food_order
                and max_spend >= npc_food_price):
            # NPC 매수 — 쿨다운 없음, 조건 충족 시 항상 발동
            ...
```

**After (Phase 16-D — 항상 internal 시도 + NPC 쿨다운·gate)**:

```python
def _process_food_reserve(self) -> list[dict]:
    """영주가 영지 식량을 비축/배급한다. 24틱마다.

    Phase 16-D:
    - reserve target 을 인구 × FOOD_STOCKPILE_RESERVE_PER_PERSONA 로 동적 산출
    - internal procurement 는 food_shortfall > 0 이면 food_priority 무관하게 먼저 시도
    - NPC 매수는 (priority > 0.4) AND (reserve < target × NPC_FOOD_TRIGGER_RESERVE_RATIO)
      AND (cooldown 경과) 3중 게이트, 매수 시 last_npc_food_purchase_tick 갱신
    """
    if self.time.tick % 24 != 0:
        return []

    events: list[dict] = []
    for tid, territory in self.territories.items():
        lord_id = territory.lord_id
        if not lord_id or lord_id not in self.personas:
            continue
        lord_inner = self.inners[lord_id]
        if lord_inner.is_sleeping:
            continue

        residents = self._get_territory_residents(tid)
        if not residents:
            continue

        # (1) 영주 개인 재고 → 영지 비축 (기존 로직 유지)
        lord_food = float(lord_inner.inventory.get("food", 0))
        stockpile = territory.policy.stockpile_target
        personal_reserve = 30.0
        if lord_food > personal_reserve:
            transfer = (lord_food - personal_reserve) * stockpile
            if transfer >= 1:
                lord_inner.inventory["food"] = lord_food - transfer
                territory.food_reserve += transfer
                events.append({
                    "type": "food_stockpile",
                    "territory": tid,
                    "lord": lord_id,
                    "amount": round(transfer, 2),
                    "reserve_after": round(territory.food_reserve, 1),
                    "source": "lord_inventory",
                })

        # (2) Phase 16-D: 동적 reserve target
        reserve_target = len(residents) * FOOD_STOCKPILE_RESERVE_PER_PERSONA
        food_shortfall = reserve_target - territory.food_reserve

        cap = max(0.0, min(0.5, territory.policy.treasury_spending_cap))
        max_spend = min(
            territory.treasury_gold * cap,
            max(0.0, territory.treasury_gold - 500.0),
        )
        npc_food_price = float(getattr(
            self, "_npc_food_price", NPC_PRICES["food"]["buy"]
        ))

        # (3) Phase 16-D: internal procurement 를 food_priority 무관하게 우선 시도
        # food_shortfall > 0 일 때만, 타겟은 reserve_target 까지
        if food_shortfall >= 1 and max_spend >= 1:
            internal_target = min(
                food_shortfall,
                max_spend / max(1.0, npc_food_price * INTERNAL_FOOD_PRICE_RATIO),
            )
            if internal_target >= 1:
                _procured, ip_events = self._process_internal_food_procurement(
                    tid, internal_target
                )
                events.extend(ip_events)
                food_shortfall = reserve_target - territory.food_reserve
                # internal 로 목표 충족되면 NPC 발동 안함 (아래 ratio gate 로 자연 차단)

        # (4) market P2P food order 존재 여부 확인
        has_market_food_order = any(
            getattr(order, "goods_type", None) == "food"
            and getattr(order, "territory_id", None) == tid
            and getattr(order, "quantity", 0) > 0
            for order in getattr(self, "market_orders", [])
        )

        # (5) Phase 16-D: NPC 매수 3중 게이트 — priority + cooldown + ratio
        priority_ok = territory.policy.food_priority > 0.4
        cooldown_ok = (
            self.time.tick - territory.last_npc_food_purchase_tick
            >= NPC_FOOD_PURCHASE_COOLDOWN_TICKS
        )
        ratio_threshold = reserve_target * NPC_FOOD_TRIGGER_RESERVE_RATIO
        ratio_ok = territory.food_reserve < ratio_threshold

        npc_needed = (
            food_shortfall >= 1
            and priority_ok
            and cooldown_ok
            and ratio_ok
            and not has_market_food_order
            and max_spend >= npc_food_price
        )
        if npc_needed:
            # 매수량: ratio_threshold 까지만 (과도 매수 방지)
            npc_target = min(
                max(0.0, ratio_threshold - territory.food_reserve),
                max_spend / npc_food_price,
            )
            buy_qty = float(int(npc_target))
            cost = buy_qty * npc_food_price
            if buy_qty >= 1 and cost <= territory.treasury_gold:
                territory.treasury_gold -= cost
                territory.food_reserve += buy_qty
                territory.last_npc_food_purchase_tick = self.time.tick  # 쿨다운 갱신
                events.append({
                    "type": "food_stockpile",
                    "territory": tid,
                    "lord": lord_id,
                    "amount": round(buy_qty, 2),
                    "reserve_after": round(territory.food_reserve, 1),
                    "source": "treasury_purchase",
                    "treasury_spent": round(cost, 1),
                    "spending_cap": round(max_spend, 1),
                    "reserve_target": round(reserve_target, 1),
                    "trigger_ratio": round(
                        territory.food_reserve / max(1.0, reserve_target), 3
                    ),
                })
        elif food_shortfall >= 1 and priority_ok and not cooldown_ok:
            # 쿨다운으로 스킵된 매수 시도 — 관측용 이벤트
            events.append({
                "type": "npc_food_purchase_cooldown_skip",
                "territory": tid,
                "ticks_since_last": self.time.tick - territory.last_npc_food_purchase_tick,
                "required": NPC_FOOD_PURCHASE_COOLDOWN_TICKS,
            })

        # (6) ration (기존 유지)
        for pid in residents:
            if pid == lord_id:
                continue
            inner = self.inners[pid]
            food = float(inner.inventory.get("food", 0))
            if food < 5 and territory.food_reserve >= 3:
                ration = min(5.0, territory.food_reserve)
                inner.inventory["food"] = food + ration
                territory.food_reserve -= ration
                events.append({
                    "type": "food_ration",
                    "territory": tid,
                    "lord": lord_id,
                    "recipient": pid,
                    "amount": round(ration, 2),
                    "reserve_after": round(territory.food_reserve, 1),
                })

    return events
```

**중요 변경 요약**:

| 포인트 | Before | After |
|---|---|---|
| reserve target | 실제 미사용 (30 고정) | `residents × 14` 동적 |
| internal trigger | `priority > 0.4 AND reserve < 30` 의 후속 | `food_shortfall ≥ 1` 만으로 발동 |
| NPC trigger | `priority AND reserve < 30` | `priority AND cooldown AND reserve < target × 0.5` |
| NPC 매수량 상한 | `FOOD_STOCKPILE_RESERVE_THRESHOLD` | `ratio_threshold` (target × 0.5) |
| cooldown skip | (없음) | `npc_food_purchase_cooldown_skip` 이벤트 기록 |

**주의 — 상수 import**: 파일 상단 import 에 `INTERNAL_FOOD_PRICE_RATIO`, `FOOD_STOCKPILE_RESERVE_PER_PERSONA`, `NPC_FOOD_PURCHASE_COOLDOWN_TICKS`, `NPC_FOOD_TRIGGER_RESERVE_RATIO` 추가 필요. `FOOD_STOCKPILE_RESERVE_THRESHOLD` import 는 유지 (다른 모듈 참조 보호).

---

### § 4. `_process_public_works` rate 공식 수정 (`multi_tick_engine.py:2616~2642`)

**Before**:

```python
rate = min(0.8, max(
    0.0,
    growth * 0.5
    + tension * 0.3
    + stability * 0.15
    + hunger * HUNGER_PRESSURE_WEIGHT,
))
territory.policy.public_works_rate = rate
if rate < PUBLIC_WORKS_RATE_MIN:
    return []
```

**After**:

```python
# Phase 16-D: base activation 가산
signal_component = (
    growth * 0.5
    + tension * 0.3
    + stability * 0.15
    + hunger * HUNGER_PRESSURE_WEIGHT
)
rate = min(0.8, max(0.0, PUBLIC_WORKS_BASE_ACTIVATION + signal_component))
territory.policy.public_works_rate = rate
if rate < PUBLIC_WORKS_RATE_MIN:    # 이제 0.03 상수 사용
    return []
```

**관측용 이벤트 필드 추가** (`_process_public_works` 내 event dict 에 추가):

```python
events.append({
    ...,   # 기존 필드 유지
    "base_component": round(PUBLIC_WORKS_BASE_ACTIVATION, 3),   # 신규
    "signal_component": round(signal_component, 3),             # 신규
})
```

**Import 추가**: 파일 상단에 `PUBLIC_WORKS_BASE_ACTIVATION` 추가.

---

### § 5. `observe_phase15_stack.py` Phase 16-D 섹션

**위치**: 기존 Phase 16-C 섹션 바로 뒤.

```python
# ── Phase 16-D: Dynamic Reserve + Base Activation 섹션 ────────
print("\n=== Phase 16-D observations ===")

cooldown_skips = [e for e in events if e.get("type") == "npc_food_purchase_cooldown_skip"]
print(f"npc_food_purchase cooldown skips: {len(cooldown_skips)}")

pw_events = [e for e in events if e.get("type") == "public_works"]
if pw_events:
    base_ratios = [
        e["base_component"] / max(1e-9, e["base_component"] + e["signal_component"])
        for e in pw_events
        if "base_component" in e and "signal_component" in e
    ]
    if base_ratios:
        avg_base_ratio = sum(base_ratios) / len(base_ratios)
        print(f"public_works base contribution ratio (avg): {avg_base_ratio:.3f}")
    else:
        print("public_works base contribution ratio (avg): N/A")

npc_buys = [
    e for e in events
    if e.get("type") == "food_stockpile" and e.get("source") == "treasury_purchase"
]
if npc_buys:
    targets = [e.get("reserve_target", 0.0) for e in npc_buys if e.get("reserve_target")]
    if targets:
        print(f"reserve_target at NPC buys (avg): {sum(targets)/len(targets):.1f}")
    trigger_ratios = [e.get("trigger_ratio", 0.0) for e in npc_buys]
    if trigger_ratios:
        print(f"NPC buy trigger_ratio (avg): {sum(trigger_ratios)/len(trigger_ratios):.3f}")
```

기존 집계 로직은 손대지 않는다. Phase 16-C hard metric (`internal_food_procurement` 이벤트 수, food supply breakdown) 은 그대로 유지.

---

### § 6. 신규 테스트 (`test_phase16d_dynamic_reserve.py`)

**파일 경로**: `Projects/personas/loom/test_phase16d_dynamic_reserve.py`

**7 tests 스켈레톤** (실제 assert 로직은 기존 `test_phase16c_internal_food_market.py` 의 패턴을 참조하여 작성):

```python
"""Phase 16-D tests: Dynamic Reserve + Base Activation + NPC Cooldown."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.multi_tick_engine import MultiTickEngine
from ontology import (
    PUBLIC_WORKS_BASE_ACTIVATION,
    PUBLIC_WORKS_RATE_MIN,
    PERSONA_FOOD_SAFE_STOCK,
    NPC_FOOD_PURCHASE_COOLDOWN_TICKS,
    FOOD_STOCKPILE_RESERVE_PER_PERSONA,
    NPC_FOOD_TRIGGER_RESERVE_RATIO,
)


def test_constants_phase16d():
    """§1: 상수 값이 기대대로 설정되어 있다."""
    assert PUBLIC_WORKS_BASE_ACTIVATION == 0.04
    assert PUBLIC_WORKS_RATE_MIN == 0.03
    assert PERSONA_FOOD_SAFE_STOCK == 12.0
    assert NPC_FOOD_PURCHASE_COOLDOWN_TICKS == 48
    assert FOOD_STOCKPILE_RESERVE_PER_PERSONA == 14.0
    assert NPC_FOOD_TRIGGER_RESERVE_RATIO == 0.5


def test_territory_has_npc_cooldown_field():
    """§1-C: Territory 에 last_npc_food_purchase_tick 필드가 있고 기본값 -9999."""
    engine = MultiTickEngine(seed=42)
    for tid, territory in engine.territories.items():
        assert hasattr(territory, "last_npc_food_purchase_tick")
        assert territory.last_npc_food_purchase_tick == -9999


def test_public_works_fires_with_zero_signal():
    """§4: SNN 신호 0 이어도 base 0.04 ≥ min 0.03 으로 public_works 발동 가능.
    강제로 SNN signal 을 0 으로 세팅하고 24틱 주기를 지나면 최소 1건 발동."""
    engine = MultiTickEngine(seed=42)
    # territory 에 stale 한 snn_signals 를 0 으로 세팅
    for tid, territory in engine.territories.items():
        territory.last_snn_signals = {"growth": 0.0, "tension": 0.0, "stability": 0.0}
        territory.last_snn_signals_tick = 0
        territory.policy.food_priority = 0.5  # NPC 발동 조건과 무관한 public_works 테스트
    # 48틱 돌리고 event 수집 — base 0.04 만으로 public_works 나와야 함
    for _ in range(48):
        engine.tick()
    pw_events = [e for e in engine.event_log if e.get("type") == "public_works"]
    assert len(pw_events) >= 1, "base activation 만으로 public_works 발동 실패"


def test_npc_purchase_cooldown_enforced():
    """§3: 같은 territory 에서 NPC 매수가 48틱 이내 두 번 발생하지 않는다."""
    engine = MultiTickEngine(seed=42)
    # 2000틱 중 첫 절반만 돌려도 충분한 샘플
    for _ in range(500):
        engine.tick()
    by_territory: dict[str, list[int]] = {}
    for event in engine.event_log:
        if event.get("type") != "food_stockpile":
            continue
        if event.get("source") != "treasury_purchase":
            continue
        by_territory.setdefault(event["territory"], []).append(event.get("tick", -1))
    # 이벤트 로그에 tick 이 없다면 engine.time.tick 기록 로직 확인
    for tid, ticks in by_territory.items():
        ticks.sort()
        for a, b in zip(ticks, ticks[1:]):
            assert b - a >= NPC_FOOD_PURCHASE_COOLDOWN_TICKS, (
                f"cooldown violated: territory={tid} a={a} b={b}"
            )


def test_dynamic_reserve_target():
    """§2: reserve_target 이 residents 수에 비례해서 변한다."""
    engine = MultiTickEngine(seed=42)
    # 몇 틱 돌려 events 수집
    for _ in range(100):
        engine.tick()
    npc_buys = [
        e for e in engine.event_log
        if e.get("type") == "food_stockpile" and e.get("source") == "treasury_purchase"
    ]
    # 매수가 발생했다면 reserve_target 필드가 기록되어 있다
    for e in npc_buys:
        assert "reserve_target" in e
        # 영지의 현재 residents 수 × 14 와 일치
        tid = e["territory"]
        territory = engine.territories[tid]
        residents = engine._get_territory_residents(tid)
        expected = len(residents) * FOOD_STOCKPILE_RESERVE_PER_PERSONA
        assert abs(e["reserve_target"] - expected) < 0.01


def test_internal_procurement_priority_gate_removed():
    """§3: food_priority ≤ 0.4 이어도 food_shortfall > 0 이면 internal procurement 시도된다."""
    engine = MultiTickEngine(seed=42)
    for tid, territory in engine.territories.items():
        territory.policy.food_priority = 0.2  # 낮은 우선순위
        # 영지 보유 food 를 0 으로 세팅하여 shortfall 강제
        territory.food_reserve = 0.0
    # 페르소나 food 를 넉넉히 세팅하여 candidates 존재하게
    for pid in engine.personas:
        engine.inners[pid].inventory["food"] = 25.0
    # 24틱 경계까지 진행
    while engine.time.tick % 24 != 0:
        engine.tick()
    engine.tick()  # 24 경계 한 번
    ip_events = [e for e in engine.event_log if e.get("type") == "internal_food_procurement"]
    assert len(ip_events) >= 1, (
        "food_priority 낮아도 internal procurement 는 시도되어야 함"
    )


def test_regression_deterministic_2_runs_500_ticks():
    """결정성 계약: 같은 seed=42 로 500틱 2회 실행 시 key 집계 동일."""
    def snapshot(seed: int):
        eng = MultiTickEngine(seed=seed)
        for _ in range(500):
            eng.tick()
        return {
            "total_gold": sum(w.gold for w in eng.wallets.values()),
            "total_treasury": sum(t.treasury_gold for t in eng.territories.values()),
            "total_food": sum(t.food_reserve for t in eng.territories.values()),
            "pw_count": sum(
                1 for e in eng.event_log if e.get("type") == "public_works"
            ),
            "ip_count": sum(
                1 for e in eng.event_log
                if e.get("type") == "internal_food_procurement"
            ),
            "npc_count": sum(
                1 for e in eng.event_log
                if e.get("type") == "food_stockpile"
                and e.get("source") == "treasury_purchase"
            ),
        }
    a = snapshot(42)
    b = snapshot(42)
    for k in a:
        assert abs(a[k] - b[k]) < 1e-6, f"determinism broken on {k}: {a[k]} vs {b[k]}"


if __name__ == "__main__":
    import traceback
    tests = [
        test_constants_phase16d,
        test_territory_has_npc_cooldown_field,
        test_public_works_fires_with_zero_signal,
        test_npc_purchase_cooldown_enforced,
        test_dynamic_reserve_target,
        test_internal_procurement_priority_gate_removed,
        test_regression_deterministic_2_runs_500_ticks,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
            passed += 1
        except Exception as exc:
            print(f"FAIL {t.__name__}: {exc}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{len(tests)} passed, {failed} failed")
    if failed:
        sys.exit(1)
```

**주의**: 테스트의 `test_npc_purchase_cooldown_enforced` 에서 `event.get("tick", -1)` 을 사용하려면 `event_log` 에 `tick` 필드가 저장되어야 한다. 현재 엔진이 event 에 tick 을 자동 주입하지 않으면 **해당 테스트를 살짝 수정**: event_log 길이 대신 직접 `engine.tick()` 호출 시점에 `engine.time.tick` 을 기록한 로컬 리스트를 사용. 아래 대체 패턴:

```python
def test_npc_purchase_cooldown_enforced():
    engine = MultiTickEngine(seed=42)
    purchase_ticks_by_territory: dict[str, list[int]] = {}
    for _ in range(500):
        before_len = len(engine.event_log)
        engine.tick()
        for ev in engine.event_log[before_len:]:
            if ev.get("type") == "food_stockpile" and ev.get("source") == "treasury_purchase":
                purchase_ticks_by_territory.setdefault(ev["territory"], []).append(
                    engine.time.tick
                )
    for tid, ticks in purchase_ticks_by_territory.items():
        ticks.sort()
        for a, b in zip(ticks, ticks[1:]):
            assert b - a >= NPC_FOOD_PURCHASE_COOLDOWN_TICKS
```

이 대체 패턴을 기본으로 사용.

---

### § 7. 에러 케이스 테이블

| 상황 | 기대 동작 | 검증 |
|---|---|---|
| treasury_gold < NPC 1단위 가격 | NPC 매수 skip, 이벤트 없음 | cooldown_skip 도 발동 안 함 (max_spend==0) |
| residents == 0 (영지 빈집) | `continue` — 영지 처리 건너뜀 | 분기 없음 |
| lord is None / not in personas | `continue` | 분기 없음 |
| lord is sleeping | `continue` | 분기 없음 |
| food_shortfall <= 0 (reserve 충분) | internal·NPC 모두 skip | internal_food_procurement 이벤트 없음 |
| internal procurement candidates empty | `return 0.0, []` → shortfall 유지, NPC gate 로 넘어감 | 기존 동작 유지 |
| 쿨다운 미경과 + priority_ok + shortfall | NPC 매수 skip + `cooldown_skip` 이벤트 기록 | 신규 이벤트 타입 |
| 쿨다운 경과 + priority_ok + ratio_ok | NPC 매수 발동 + `last_npc_food_purchase_tick` 갱신 | 다음 번 호출 시 쿨다운 재적용 |
| max_spend < npc_food_price | NPC skip (기존과 동일) | |

---

### § 8. 결정성 계약

- `self._np_rng = np.random.default_rng(self._seed)` 초기화는 Phase 16-C 에서 이미 추가됨. 재정의 금지.
- Phase 16-D 신규 로직에는 `random.random()` / `np.random.random()` 전역 호출 없음. 모든 샘플링은 `self.rng` 또는 `self._np_rng` 사용.
- `test_regression_deterministic_2_runs_500_ticks` 가 결정성 계약 검증.

---

### § 9. 관측 출력 예시 (기대값)

2000틱 실행 후 `observe_phase15_stack.py` 출력 말미에 다음 같은 섹션이 나와야 한다:

```
=== Phase 16-D observations ===
npc_food_purchase cooldown skips: N  (N > 0 이면 cooldown 이 실제로 스킵 발생시킴)
public_works base contribution ratio (avg): 0.2~0.6 범위
reserve_target at NPC buys (avg): 140 (residents 10 × 14)
NPC buy trigger_ratio (avg): ~0.3~0.5 (NPC_FOOD_TRIGGER_RESERVE_RATIO=0.5 이하에서만 발동)
```

---

### § 10. Phase 16-E 대안표 (Hard 실패 시 **기록만**)

자가 튜닝 금지. 아래 표는 리뷰 리포트에서 "다음 Phase 후보" 용도로만 제시.

| 미달 지표 | 1순위 대안 | 2순위 대안 |
|---|---|---|
| persona gold 회복 부족 | `PUBLIC_WORKS_BASE_ACTIVATION` 0.04 → 0.06 | `PUBLIC_WORKS_IN_KIND_RATIO` 재조정 (단 Phase 16-B 상수 — 이건 별도 승인 필요) |
| public_works < 50 | `PUBLIC_WORKS_RATE_MIN` 0.03 → 0.02 | `PUBLIC_WORKS_BASE_ACTIVATION` 0.04 → 0.05 |
| NPC > 34 | `NPC_FOOD_PURCHASE_COOLDOWN_TICKS` 48 → 72 | `NPC_FOOD_TRIGGER_RESERVE_RATIO` 0.5 → 0.35 |
| internal procurement < 30 | `PERSONA_FOOD_SAFE_STOCK` 12 → 8 | farmer 에게만 `SAFE_STOCK_FARMER = 6` 별도 상수 도입 (구조 변경) |
| total_wealth < −40% | Phase 16-B `PUBLIC_WORKS_IN_KIND_RATIO` 증가 (별도 승인) | Phase 12 `NPC_PRICES["food"]["sell"]` 상향 (별도 승인) |

---

## 검증

### 기계 검증 (항상)

```bash
py -m py_compile ontology/layers.py ontology/__init__.py core/multi_tick_engine.py observe_phase15_stack.py test_phase16d_dynamic_reserve.py
py test_phase16d_dynamic_reserve.py            # 7/7 PASS
py test_phase16c_internal_food_market.py       # 7/7 PASS (회귀)
py test_phase16_public_works.py                # 9/9 PASS (회귀)
py test_phase12b_perf_npc.py                   # 5/5 PASS (회귀)
py test_economy_balance.py                     # 6/6 PASS (회귀)
py test_economy.py                             # 6/6 PASS (회귀)
py test_nomos.py                               # PASS (회귀)
py test_class_promotion.py                     # PASS (회귀)
npm --prefix packages/launcher run typecheck   # PASS (회귀)
```

`npm lint` 는 packages/launcher 에 스크립트 없음 — skip (Phase 16-C 와 동일).

### 기능 검증 (2000틱 Hard)

```bash
py observe_phase15_stack.py
```

출력 중 다음 5개 지표 **전부** 통과해야 합격:

| 지표 | 기준 | 비고 |
|---|---|---|
| persona gold final | ≥ 6000 (loss ≤ 70%) | 초기 20000 기준 |
| total_wealth loss | ≤ 40% | gold + treasury + goods×NPC buy |
| deaths | 0/10 | 아사·사망 0 |
| public_works events | ≥ 50 | 2000틱 동안 |
| NPC food_stockpile events (source=treasury_purchase) | ≤ 34 | lord_inventory 경로 제외 |

### 계약 검증

- 결정성: `test_regression_deterministic_2_runs_500_ticks` 통과 (key 집계 6개 모두 차이 < 1e-6)
- 호환성: 기존 8개 테스트 파일 전부 PASS
- Import 안정성: `py -c "from ontology import PUBLIC_WORKS_BASE_ACTIVATION, NPC_FOOD_PURCHASE_COOLDOWN_TICKS, FOOD_STOCKPILE_RESERVE_PER_PERSONA, NPC_FOOD_TRIGGER_RESERVE_RATIO; print('OK')"` → "OK"

---

## Rollback

```bash
cd Projects/personas/loom
git checkout HEAD -- ontology/layers.py ontology/__init__.py core/multi_tick_engine.py observe_phase15_stack.py
rm -f test_phase16d_dynamic_reserve.py
py test_phase16c_internal_food_market.py    # 회귀 확인
```

**데이터 영향**: 없음 (Python 인메모리 시뮬).

---

## 실패 시 에스컬레이션 템플릿

Hard 기준 중 1개 이상 실패하거나 회귀 테스트 실패 시 **파라미터 자가 튜닝 금지**. 다음 리포트 포맷으로 돌아올 것:

```markdown
# Phase 16-D 구현 리뷰 요청: <한 줄 요약>

## 구현 완료
- [변경한 파일과 요약]

## 테스트 결과
- [tests 통과/실패 내역]

## 2000틱 관측 결과
- [persona gold, public_works, NPC food_stockpile 등 hard 지표 표]
- [Phase 16-D 관측 섹션 그대로 붙여넣기]

## 가설 (왜 실패했나)
- [가장 큰 문제 3가지, 각각 1~2문장]

## 요청
- Phase 16-E 설계 지시서 작성 요청
- 또는 §10 대안표 중 어느 축을 우선 시도할지 결정 요청
```

---

## GPT 전달 프롬프트 템플릿

```
당신은 persona life simulator loom 프로젝트의 시니어 Python 엔지니어입니다.

## 프로젝트 경로
c:\Users\haj\projects\subagent-orchestrator\Projects\personas\loom

## 기술 스택
- Python 3.x, numpy
- Custom SNN (PersonaBrain), dataclass 기반 ontology
- 단일 파일 multi_tick_engine.py (~2700 LOC)

## 작업 지시서
Projects/personas/loom/PHASE-16D-CODEX-INSTRUCTIONS.md 파일을 그대로 따라 구현하세요.

## 규칙 (절대 준수)
1. 지시서 [필수] 7개 항목 100% 구현. [금지] 9개 항목 절대 건드리지 말 것.
2. 지시서에 포함된 코드 블록은 **직접 복사**해서 반영. 해석·재작성 금지.
3. Phase 16-B/C 구조(public_works 자체, internal_food_procurement 메서드)는 유지하며 이 지시서의 지정 지점만 수정.
4. 기존 상수(INTERNAL_FOOD_PRICE_RATIO, HUNGER_PRESSURE_WEIGHT 등) 값 변경 금지.
5. 검증 순서:
   a. py -m py_compile <5개 파일>
   b. py test_phase16d_dynamic_reserve.py   → 7/7 PASS
   c. py test_phase16c_internal_food_market.py → 7/7 PASS (회귀)
   d. 나머지 기존 테스트 파일 모두 PASS
   e. npm --prefix packages/launcher run typecheck → PASS
   f. py observe_phase15_stack.py → Hard 5개 지표 확인
6. Hard 기준 미달 시 **파라미터 자가 조정 금지**. 지시서 §실패 에스컬레이션 템플릿대로 리뷰 리포트 제출.
7. 보고 내용:
   - 변경 파일 목록 + 각 파일의 변경 요약
   - 각 검증 단계 통과 여부
   - 2000틱 hard 지표 표
   - Phase 16-D 관측 섹션 출력 그대로
   - [선택] 항목 구현 여부
```

---

## 자체 검증 체크리스트 (작성자)

- [x] 메타 5종 (긴급도/선행/유형/migration/의존)
- [x] 배경 3문장 + 근본 원인 4단 + 4축 대응표
- [x] [필수 8 / 선택 2 / 금지 9]
- [x] 프레임워크 제약 섹션
- [x] 변경 파일 표 + 변경 없음 5개
- [x] 구체 사양 §1~§10 (상수·필드·메서드 Before/After 코드블록)
- [x] 기계 검증 + 기능 검증 + 계약 검증
- [x] 에러 케이스 테이블
- [x] Rollback 명령
- [x] GPT 전달 프롬프트 템플릿
- [x] 실패 에스컬레이션 템플릿
- [x] §10 Phase 16-E 대안표 (자가 튜닝 금지 명시)
- [x] 모호 표현 없음 (모든 숫자·조건·파일경로 명시)
- [x] "참고" 단독 지시 없음 (모든 참조에 코드 블록 동반)
