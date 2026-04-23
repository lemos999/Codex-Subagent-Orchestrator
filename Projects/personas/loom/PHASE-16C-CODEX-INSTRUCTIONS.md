# [기능+리팩토링] Phase 16-C: Internal Food Market — Codex 구현 지시서

> 긴급도: 중간
> 선행 조건: Phase 16-B 구현 완료 (GovernancePolicy.public_works_rate, Territory.last_snn_signals_tick, _process_public_works 등)
> 작업 유형: 기능(신규 함수 2개) + 리팩토링(기존 메서드 2개 수정 + np.random 교체)
> DB migration: 없음 (Python 메모리 시뮬)
> 외부 의존: 없음 (기존 numpy·random만 사용)

---

## 배경

Phase 16-B 구현 결과 2000틱에서 persona gold 감소 -91.5% (보강 관측 -74.0%), public_works 12건(목표 ≥50), food_stockpile 88~136건(목표 ≤34)으로 **하드 기준 미달**. 근본 원인은 "영지-페르소나 직접 food 거래 경로 부재" + "public_works rate 게이트가 너무 타이트" + "numpy 전역 random의 비결정성". Phase 16-C는 3축 개입으로 이 문제를 해결한다.

설계 원본: [PHASE-16C-INTERNAL-FOOD-MARKET-DESIGN.md](./PHASE-16C-INTERNAL-FOOD-MARKET-DESIGN.md)

---

## 작업 범위

### [필수]
1. 영지가 같은 영지 farmer에게서 직접 food 매입 경로 구현 (`_process_internal_food_procurement`)
2. 기존 `food_stockpile` 매수 분기에 내부 조달 우선순위 삽입 (reserve 체크 → **내부 조달** → 시장 → NPC)
3. `_process_public_works` rate 공식에 `hunger_pressure` 반영 + 발동 하한 0.1→0.05 완화 + farmer 편향 선택
4. `MultiTickEngine`에 `self._np_rng` 추가 및 **SNN/경제 경로 4개 호출**을 교체하여 같은 seed 재현성 확보
5. `test_phase16c_internal_food_market.py` 신규 7 tests
6. `observe_phase15_stack.py`에 Phase 16-C 섹션 추가 (internal_food_procurement 집계, 공급망 breakdown)
7. 합격 기준 (Hard): persona gold ≤-70%, total_wealth ≤-40%, deaths=0, public_works ≥50, food_stockpile ≤34, 전체 회귀 PASS, 16-C tests 7/7 PASS

### [선택]
- 불합격 시 Phase 16-D 파라미터 대안 표(본 지시서 §7) 기록만. 자가 튜닝 금지
- 관측 스크립트에 공급망 비율 막대 그래프 (ASCII)

### [금지]
- 새 PersonaBrain 뉴런·SNN 축 추가
- `food_stockpile` NPC 매수 완전 제거 (후순위로만 강등)
- `GOLD_DIRECT_PAY_RATIO` 등 Phase 16-B 이전 상수 재튜닝
- Phase 16-B 구조(public_works 자체) 변경 — 위에 덧붙이기만
- `np.random.default_rng(seed + offset)` 패턴 변경 (이미 결정적)
- `random.random()` / `random.sample()` 전역 호출 추가

---

## 프레임워크·프로젝트 제약

- Python 3.x, numpy. 별도 패키지 추가 금지.
- `MultiTickEngine`은 `Projects/personas/loom/core/multi_tick_engine.py`에 정의.
- `self.rng` (Python `random.Random`)는 Phase 16-B에서 이미 추가되어 있음. `self._np_rng` 는 신규.
- 기존 `np.random.default_rng(seed + N)` 호출은 **seed 결정적**이므로 교체 대상이 아님.
- **교체 대상**은 `np.random.random()` 전역 호출 정확히 4곳:
  - `multi_tick_engine.py:865`
  - `multi_tick_engine.py:1659`
  - `multi_tick_engine.py:1694`
  - `multi_tick_engine.py:1824`
- 파일 >500 LOC는 offset/limit 청크 읽기. 필요 시 3회 편집마다 검증 읽기.
- 모든 신규 상수는 `ontology/layers.py`에 정의하고 `ontology/__init__.py`에서 export.

---

## 변경 파일

| 파일 | 작업 | 유형 |
|---|---|:---:|
| `Projects/personas/loom/ontology/layers.py` | 상수 6개 + `Territory.internal_food_procured_total` 필드 | 수정 |
| `Projects/personas/loom/ontology/__init__.py` | 신규 상수 export | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | `_process_internal_food_procurement` / `_calc_hunger_pressure` / `_weighted_sample_without_replacement` 신규, `_process_public_works` 수정, food_stockpile 분기 수정, `self._np_rng` 초기화 + 4곳 교체 | 수정 |
| `Projects/personas/loom/observe_phase15_stack.py` | Phase 16-C 집계·출력 블록 추가 | 수정 |
| `Projects/personas/loom/test_phase16c_internal_food_market.py` | 7 tests | 추가 |

**변경 없음 (금지):**
- `Projects/personas/loom/brain/*.py` — 이번 작업 범위 밖
- `Projects/personas/loom/test_phase16_public_works.py` — Phase 16-B 테스트, 건드리지 말 것
- `packages/launcher/**` — 본 작업과 무관
- 기타 기존 Phase(12/13/14/15) 전용 상수·함수

---

## 구체 사양

### § 1. 상수 (`ontology/layers.py`)

기존 Phase 16-B 상수 블록 바로 뒤에 추가:

```python
# ── Phase 16-C 추가 상수 ─────────────────────────────
INTERNAL_FOOD_PRICE_RATIO: float = 0.75       # 영지 매수가 = NPC.buy * 0.75
PERSONA_FOOD_SAFE_STOCK: float = 24.0         # farmer 개인 안전재고 (이 초과분만 매도)
PUBLIC_WORKS_RATE_MIN: float = 0.05           # rate 하한 (기존 0.1 완화)
HUNGER_PRESSURE_WEIGHT: float = 0.2           # rate 공식 hunger 가중치
PUBLIC_WORKS_FARMER_BIAS: float = 2.0         # hunger 활성 시 farmer 선택 가중
HUNGER_TRIGGER_THRESHOLD: float = 0.3         # 이 이상이면 farmer 편향 활성
```

`Territory` dataclass 안, 기존 `quarter_tax_income` 필드 바로 뒤:

```python
    internal_food_procured_total: float = 0.0
```

`ontology/__init__.py`에 6개 상수 export 추가.

### § 2. `MultiTickEngine.__init__` — `self._np_rng` 추가

`self.rng = random.Random(...)` 설정 근처에 추가:

```python
import numpy as np  # 파일 상단 import 블록에 이미 있으면 skip
self._np_rng: np.random.Generator = np.random.default_rng(self._seed)
```

### § 3. `np.random.random()` 4곳 교체

각 위치에서 `np.random.random()` → `self._np_rng.random()` 치환. 다른 로직 변경 금지.

| 파일:줄 | Before | After |
|---|---|---|
| `core/multi_tick_engine.py:865` | `if np.random.random() >= inner.grievance * 0.3:` | `if self._np_rng.random() >= inner.grievance * 0.3:` |
| `core/multi_tick_engine.py:1659` | `if np.random.random() < share_prob:` | `if self._np_rng.random() < share_prob:` |
| `core/multi_tick_engine.py:1694` | `if np.random.random() < spread_prob:` | `if self._np_rng.random() < spread_prob:` |
| `core/multi_tick_engine.py:1824` | `if np.random.random() > teach_prob:` | `if self._np_rng.random() > teach_prob:` |

> 실제 줄 번호는 최근 수정으로 변경될 수 있음. 각 패턴을 grep 후 **동일 패턴 1회씩**만 교체.

### § 4. 신규 함수 — `_process_internal_food_procurement`

`MultiTickEngine` 클래스 내부, `_process_public_works` 근처에 추가:

```python
def _process_internal_food_procurement(
    self, territory_id: str, target_qty: float
) -> tuple[float, list[dict]]:
    """Phase 16-C: 영지가 같은 영지 farmer의 food 잉여를 매입.

    Returns:
        (procured_qty, events) — 실제 조달된 양 + 이벤트 리스트
    """
    territory = self.territories.get(territory_id)
    if not territory or target_qty <= 0:
        return 0.0, []

    npc_food = NPC_PRICES.get("food", {})
    unit_price = float(npc_food.get("buy", 10)) * INTERNAL_FOOD_PRICE_RATIO

    candidates: list[tuple[str, float]] = []
    for pid, persona in self.personas.items():
        if persona.territory != territory_id:
            continue
        inner = self.inners[pid]
        if float(inner.vitality) <= 0 or inner.is_sleeping:
            continue
        food_stock = float(inner.inventory.get("food", 0))
        surplus = food_stock - PERSONA_FOOD_SAFE_STOCK
        if surplus <= 0:
            continue
        candidates.append((pid, surplus))

    if not candidates:
        return 0.0, []

    # 결정적 순서: surplus 큰 순, 동점 시 pid 알파벳
    candidates.sort(key=lambda x: (-x[1], x[0]))

    procured = 0.0
    events: list[dict] = []
    remaining = float(target_qty)
    for pid, surplus in candidates:
        if remaining <= 0:
            break
        qty = min(surplus, remaining)
        cost = qty * unit_price
        if territory.treasury_gold < cost:
            if unit_price <= 0:
                break
            qty = territory.treasury_gold / unit_price
            cost = qty * unit_price
            if qty < 1.0:
                break

        territory.treasury_gold -= cost
        self.wallets[pid].receive(cost)
        inner = self.inners[pid]
        inner.inventory["food"] = float(inner.inventory.get("food", 0)) - qty
        territory.food_reserve = float(getattr(territory, "food_reserve", 0.0)) + qty
        territory.internal_food_procured_total += qty
        procured += qty
        remaining -= qty
        events.append({
            "type": "internal_food_procurement",
            "territory": territory_id,
            "seller": pid,
            "qty": round(qty, 2),
            "unit_price": round(unit_price, 2),
            "cost": round(cost, 2),
            "reserve_after": round(territory.food_reserve, 2),
        })
    return procured, events
```

### § 5. `food_stockpile` 분기 수정 — 내부 조달 우선순위 삽입

기존 `food_stockpile` 경로(파일 내 `"type": "food_stockpile"` 이벤트를 emit하는 블록)를 다음 구조로 수정. 위치는 기존 reserve 체크 직후, 시장 체크 직전:

**Before (Phase 16-B):**
```python
# Phase 16-B reserve 가드
if territory.food_reserve >= FOOD_STOCKPILE_RESERVE_THRESHOLD:
    continue

# Phase 16-B 시장 우선
has_market_food_order = any(...)
if has_market_food_order:
    continue

# NPC 매수 (기존)
if buy_qty >= 1 and cost <= territory.treasury_gold:
    territory.treasury_gold -= cost
    territory.food_reserve += buy_qty
    events.append({"type": "food_stockpile", ...})
```

**After (Phase 16-C):**
```python
# Phase 16-B reserve 가드
if territory.food_reserve >= FOOD_STOCKPILE_RESERVE_THRESHOLD:
    continue

# Phase 16-C: 내부 조달 (farmer 직접 매입)
shortfall = max(0.0, FOOD_STOCKPILE_RESERVE_THRESHOLD - territory.food_reserve)
if shortfall > 0:
    _procured, ip_events = self._process_internal_food_procurement(
        territory_id, shortfall
    )
    events.extend(ip_events)
    if territory.food_reserve >= FOOD_STOCKPILE_RESERVE_THRESHOLD:
        continue

# Phase 16-B 시장 우선
has_market_food_order = any(
    getattr(o, "goods_type", None) == "food"
    and getattr(o, "territory_id", None) == territory_id
    for o in getattr(self, "market_orders", [])
)
if has_market_food_order:
    continue

# NPC 매수 (최후)
if buy_qty >= 1 and cost <= territory.treasury_gold:
    territory.treasury_gold -= cost
    territory.food_reserve += buy_qty
    events.append({"type": "food_stockpile", ...})
```

> `shortfall` 타겟은 `FOOD_STOCKPILE_RESERVE_THRESHOLD` 기준으로 산정. 기존 코드의 `buy_qty` 계산식이 있으면 그 값을 상한으로 `min(shortfall, buy_qty_target)` 사용.

### § 6. `_process_public_works` 수정 (축 2)

**헬퍼 신규** — `_calc_hunger_pressure`:

```python
def _calc_hunger_pressure(self, territory_id: str) -> float:
    """영지 persona 평균 consecutive_hunger_ticks를 0~1 정규화 (72 = 상한)."""
    vals = [
        float(self.inners[pid].consecutive_hunger_ticks)
        for pid, p in self.personas.items()
        if p.territory == territory_id
    ]
    if not vals:
        return 0.0
    avg = sum(vals) / len(vals)
    return min(1.0, avg / 72.0)
```

**헬퍼 신규** — `_weighted_sample_without_replacement` (Efraimidis-Spirakis):

```python
def _weighted_sample_without_replacement(
    self, population: list, weights: list[float], k: int
) -> list:
    if k <= 0:
        return []
    if k >= len(population):
        return list(population)
    keyed = []
    for item, w in zip(population, weights):
        if w <= 0:
            continue
        u = self.rng.random()
        key = u ** (1.0 / w)
        keyed.append((key, item))
    keyed.sort(key=lambda x: -x[0])
    return [item for _, item in keyed[:k]]
```

**`_process_public_works` 안에서 rate 계산·선택 부분 교체**:

Before (Phase 16-B):
```python
rate = min(0.8, max(0.0, growth * 0.6 + tension * 0.3 + stability * 0.1))
territory.policy.public_works_rate = rate
if rate < 0.1:
    return []
# ...
chosen = self.rng.sample(unemployed, n_hire)
```

After (Phase 16-C):
```python
hunger = self._calc_hunger_pressure(territory_id)
rate = min(0.8, max(0.0,
    growth * 0.5 + tension * 0.3 + stability * 0.15 + hunger * HUNGER_PRESSURE_WEIGHT
))
territory.policy.public_works_rate = rate
if rate < PUBLIC_WORKS_RATE_MIN:
    return []
# ... (실업자 필터·n_hire 산정은 기존 그대로)
if hunger >= HUNGER_TRIGGER_THRESHOLD:
    weights = [
        PUBLIC_WORKS_FARMER_BIAS if (self._get_persona_job_title(pid) or "") == "farmer" else 1.0
        for pid in unemployed
    ]
    chosen = self._weighted_sample_without_replacement(unemployed, weights, n_hire)
else:
    chosen = self.rng.sample(unemployed, n_hire)
```

이벤트 dict에 2개 필드 추가:
```python
"hunger_pressure": round(hunger, 3),
"farmer_bias_active": hunger >= HUNGER_TRIGGER_THRESHOLD,
```

**import 추가** (파일 상단 ontology import 블록):
```python
from ontology.layers import (
    # 기존 import 유지
    INTERNAL_FOOD_PRICE_RATIO, PERSONA_FOOD_SAFE_STOCK,
    PUBLIC_WORKS_RATE_MIN, HUNGER_PRESSURE_WEIGHT,
    PUBLIC_WORKS_FARMER_BIAS, HUNGER_TRIGGER_THRESHOLD,
)
```

### § 7. 관측 스크립트 (`observe_phase15_stack.py`)

기존 Phase 16-B 집계 다음에 Phase 16-C 섹션 추가. 위치는 "Phase 16-B" 섹션 아래, "Economy Snapshot" 위.

```python
internal_food_events = []
for tick_idx, tick_result in enumerate(log):
    for ev in tick_result.get("economy_events", []):
        if ev.get("type") == "internal_food_procurement":
            internal_food_events.append((tick_idx, ev))

food_stockpile_events = [
    (i, ev) for i, tr in enumerate(log) for ev in tr.get("economy_events", [])
    if ev.get("type") == "food_stockpile"
]

total_internal_food = sum(ev.get("qty", 0) for _, ev in internal_food_events)
total_internal_gold = sum(ev.get("cost", 0) for _, ev in internal_food_events)
total_npc_food = sum(ev.get("buy_qty", 0) or 0 for _, ev in food_stockpile_events)

print("\n" + "─" * 70)
print("  Phase 16-C: Internal Food Market")
print("─" * 70)
print(f"  internal_food_procurement events : {len(internal_food_events)}")
print(f"  total food procured internally   : {total_internal_food:.1f}")
print(f"  total gold → farmers (internal)  : {total_internal_gold:.0f}")
print(f"  food_stockpile events (NPC)       : {len(food_stockpile_events)}")
print(f"  food supply breakdown:")
print(f"    internal (farmer→territory)  : {total_internal_food:.1f}")
print(f"    NPC (food_stockpile)          : {total_npc_food:.1f}")
```

---

## 테스트 — `test_phase16c_internal_food_market.py` (신규)

완전한 스켈레톤 (Codex가 픽스처만 채움):

```python
"""Phase 16-C: Internal Food Market 테스트."""
import sys
sys.path.insert(0, ".")

from core.multi_tick_engine import MultiTickEngine
from ontology.layers import (
    PERSONA_FOOD_SAFE_STOCK, INTERNAL_FOOD_PRICE_RATIO,
    PUBLIC_WORKS_RATE_MIN, HUNGER_TRIGGER_THRESHOLD,
    FOOD_STOCKPILE_RESERVE_THRESHOLD, NPC_PRICES,
)


def _setup_engine(seed=42):
    return MultiTickEngine(seed=seed)


def _inject_signals(territory, tick, *, growth=0.0, tension=0.0, stability=0.0):
    territory.last_snn_signals = {
        "growth": growth, "tension": tension, "stability": stability
    }
    territory.last_snn_signals_tick = tick


def _pick_territory_and_farmer(engine):
    tid = next(iter(engine.territories))
    territory = engine.territories[tid]
    # 첫 persona를 farmer로 가정, 같은 영지에 속함 보장
    for pid, p in engine.personas.items():
        if p.territory == tid:
            return tid, territory, pid
    raise RuntimeError("no persona in territory")


def test_internal_procurement_from_farmer():
    engine = _setup_engine()
    tid, territory, pid = _pick_territory_and_farmer(engine)
    territory.treasury_gold = 1000.0
    engine.inners[pid].inventory["food"] = PERSONA_FOOD_SAFE_STOCK + 20
    wallet_before = engine.wallets[pid].gold
    procured, events = engine._process_internal_food_procurement(tid, target_qty=10)
    assert procured > 0, "should procure from farmer surplus"
    assert events and events[0]["type"] == "internal_food_procurement"
    assert engine.wallets[pid].gold > wallet_before
    assert engine.inners[pid].inventory["food"] <= PERSONA_FOOD_SAFE_STOCK + 20


def test_no_surplus_no_procurement():
    engine = _setup_engine()
    tid, territory, pid = _pick_territory_and_farmer(engine)
    territory.treasury_gold = 1000.0
    engine.inners[pid].inventory["food"] = PERSONA_FOOD_SAFE_STOCK  # 정확히 safe stock
    procured, events = engine._process_internal_food_procurement(tid, target_qty=10)
    assert procured == 0 and events == []


def test_procurement_respects_treasury():
    engine = _setup_engine()
    tid, territory, pid = _pick_territory_and_farmer(engine)
    unit_price = float(NPC_PRICES["food"]["buy"]) * INTERNAL_FOOD_PRICE_RATIO
    territory.treasury_gold = unit_price * 3  # 3 units만 살 수 있음
    engine.inners[pid].inventory["food"] = PERSONA_FOOD_SAFE_STOCK + 100
    procured, _ = engine._process_internal_food_procurement(tid, target_qty=100)
    assert procured <= 3.01


def test_food_stockpile_prefers_internal_over_npc():
    """통합: 영지 reserve 낮고 farmer 잉여 있으면 NPC 매수 skip."""
    engine = _setup_engine()
    tid, territory, pid = _pick_territory_and_farmer(engine)
    territory.food_reserve = 0
    territory.treasury_gold = 2000.0
    engine.inners[pid].inventory["food"] = PERSONA_FOOD_SAFE_STOCK + 80
    # _auto_economy_tick 또는 food_stockpile 분기 호출 (엔진 API에 따라 조정)
    # 몇 틱 진행
    for _ in range(30):
        engine.tick()
    npc_events = [
        ev for tr in engine._last_tick_log[-30:] if hasattr(engine, "_last_tick_log")
        for ev in tr.get("economy_events", [])
        if ev.get("type") == "food_stockpile"
    ]
    # 내부 조달이 충분했다면 NPC 매수 0 또는 극소수
    assert len(npc_events) <= 1


def test_hunger_pressure_raises_rate():
    engine = _setup_engine()
    tid, territory, pid = _pick_territory_and_farmer(engine)
    territory.treasury_gold = 3000.0
    territory.quarter_tax_income = 500.0
    for p_pid, p in engine.personas.items():
        if p.territory == tid:
            engine.inners[p_pid].consecutive_hunger_ticks = 50  # hunger 높음
    _inject_signals(territory, engine.time.tick, growth=0.0, tension=0.0, stability=0.0)
    events = engine._process_public_works(tid)
    # growth/tension 0이어도 hunger만으로 rate가 RATE_MIN 넘어야 함
    assert territory.policy.public_works_rate >= PUBLIC_WORKS_RATE_MIN


def test_farmer_bias_selection():
    """hunger > threshold 상태에서 farmer가 포함될 확률 > 단순 균등."""
    # 통계적 테스트: 시드 고정 + 여러 시도 후 farmer 포함 비율 확인
    engine = _setup_engine()
    tid, territory, pid_farmer = _pick_territory_and_farmer(engine)
    # farmer 1명 + 비-farmer 여러 명 세팅
    # (엔진 초기화 방식에 따라 persona job 수동 지정)
    territory.treasury_gold = 5000.0
    territory.quarter_tax_income = 1000.0
    for p_pid, p in engine.personas.items():
        if p.territory == tid:
            engine.inners[p_pid].consecutive_hunger_ticks = 60
    _inject_signals(territory, engine.time.tick, growth=0.5)
    events = engine._process_public_works(tid)
    assert any(ev.get("farmer_bias_active") for ev in events)


def test_determinism_seed():
    """같은 seed → 200틱 후 persona gold 합 동일."""
    def run():
        e = _setup_engine(seed=42)
        for _ in range(200):
            e.tick()
        return sum(w.gold for w in e.wallets.values())
    assert abs(run() - run()) < 1e-6


if __name__ == "__main__":
    tests = [
        test_internal_procurement_from_farmer,
        test_no_surplus_no_procurement,
        test_procurement_respects_treasury,
        test_food_stockpile_prefers_internal_over_npc,
        test_hunger_pressure_raises_rate,
        test_farmer_bias_selection,
        test_determinism_seed,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
```

> `test_food_stockpile_prefers_internal_over_npc`와 `test_farmer_bias_selection`은 엔진 tick API에 맞춰 Codex가 조정. 나머지 5개는 위 코드 그대로 통과해야 함.

---

## 검증

### 기계 검증 (필수 — 모두 PASS)

```bash
cd Projects/personas/loom

# 1) 문법
py -m py_compile ontology/layers.py core/multi_tick_engine.py observe_phase15_stack.py test_phase16c_internal_food_market.py

# 2) Phase 16-C 테스트
py test_phase16c_internal_food_market.py
# 기대: 7/7 passed

# 3) 회귀 (모두 PASS 필수)
py test_phase16_public_works.py    # Phase 16-B (이미 PASS 상태 유지)
py test_economy_balance.py
py test_phase12b_perf_npc.py
py test_economy.py
py test_nomos.py
py test_class_promotion.py

# 4) TypeScript launcher
npm --prefix packages/launcher run typecheck

# 5) 2000틱 관측
py observe_phase15_stack.py 2>&1 | tail -100
```

### 기능 검증 (2000틱 Hard 기준 — 모두 통과 필수)

| # | 지표 | 기준 | 측정 위치 |
|---|---|---|---|
| 1 | persona gold 감소율 | ≤ **-70%** (최종 ≥ 6000) | Economy Snapshot `total persona gold` |
| 2 | total_wealth 감소율 | ≤ **-40%** | Phase 16-B 섹션 `TOTAL` |
| 3 | deaths | 0 / 10 | Economy Snapshot `deaths` |
| 4 | public_works events | ≥ 50 | Phase 16-B 섹션 `public_works events` |
| 5 | food_stockpile events | ≤ 34 | Phase 16-C 섹션 `food_stockpile events (NPC)` |
| 6 | test_phase16c...py | 7/7 PASS | test 실행 결과 |
| 7 | 기존 회귀 전체 | 모두 PASS | 각 test 실행 결과 |

### 계약 검증 (결정성)

```bash
# 같은 seed 2회 실행해서 persona gold 합 동일해야 함
py -c "
import sys; sys.path.insert(0,'.')
from core.multi_tick_engine import MultiTickEngine
def run():
    e = MultiTickEngine(seed=42)
    for _ in range(500): e.tick()
    return sum(w.gold for w in e.wallets.values())
a, b = run(), run()
assert abs(a-b) < 1e-6, f'non-deterministic: {a} != {b}'
print('OK', a)
"
```

2회 실행 수치 차이 < 1e-6이어야 PASS.

### Soft 지표 (리포트만 — 실패해도 불합격 아님)

- `internal_food_procurement` events ≥ 40
- farmer 공공 고용 비율 ≥ 30% (hunger 시나리오)
- `food_supply breakdown`에서 internal > NPC

---

## 에러 케이스 표 (내부 조달)

| 상황 | 기대 동작 | 이벤트 |
|---|---|---|
| target_qty ≤ 0 | 즉시 반환 (0.0, []) | 없음 |
| territory 없음 | 즉시 반환 | 없음 |
| 모든 farmer 재고 ≤ safe_stock | 반환 (0.0, []) | 없음 |
| treasury 부족 | 살 수 있는 만큼만 매수 | internal_food_procurement (부분) |
| 영주가 food 잉여 보유 | 일반 persona와 동일 처리 (lord 제외 없음) | internal_food_procurement |
| 졸고 있거나 vitality=0 | 후보에서 제외 | — |

---

## Rollback

```bash
cd Projects/personas/loom
git checkout -- \
  ontology/layers.py \
  ontology/__init__.py \
  core/multi_tick_engine.py \
  observe_phase15_stack.py
rm test_phase16c_internal_food_market.py
```

데이터 영향: 없음 (메모리 시뮬). 기존 save 파일 호환성 영향 없음.

---

## 실패 시 에스컬레이션

Hard 기준 **1개 이상 미달 시 수정 금지**. 결과 그대로 아래 템플릿으로 보고하고 Phase 16-D 설계 지시 요청:

```markdown
## Phase 16-C 구현 결과 보고

### 구현 완료
- [체크] § 1 상수 추가
- [체크] § 2 _np_rng 초기화
- [체크] § 3 np.random 4곳 교체
- [체크] § 4 _process_internal_food_procurement
- [체크] § 5 food_stockpile 분기 수정
- [체크] § 6 _process_public_works + 헬퍼 2개
- [체크] § 7 observe 스크립트

### 검증 결과
- py_compile: PASS/FAIL
- test_phase16c: N/7 PASS
- 회귀: ...
- 결정성: PASS/FAIL (차이 = X)

### 2000틱 Hard 지표
| # | 지표 | 기준 | 실제 | 결과 |
|---|---|---|---|---|
| 1 | persona gold | ≤-70% | X% | ✓/✗ |
| 2 | total_wealth | ≤-40% | X% | ✓/✗ |
| 3 | deaths | 0 | X | ✓/✗ |
| 4 | public_works | ≥50 | X | ✓/✗ |
| 5 | food_stockpile | ≤34 | X | ✓/✗ |

### Soft 지표
- internal_food_procurement events: X
- food supply breakdown: internal=X, NPC=Y

### 관측된 이상
(자유 기술)
```

---

## GPT/Codex 전달 프롬프트 템플릿

지시서 전달 시 아래 프롬프트 동봉:

```
당신은 페르소나 자율 생활 시뮬 loom 프로젝트의 시니어 Python 개발자입니다.

## 프로젝트 경로
c:/Users/haj/projects/subagent-orchestrator/Projects/personas/loom

## 기술 스택
Python 3.x, numpy, dataclasses. SNN 기반 페르소나 뇌 시뮬 + 다중 영지 경제. 외부 패키지 추가 금지.

## 작업 지시서
Projects/personas/loom/PHASE-16C-CODEX-INSTRUCTIONS.md 파일을 그대로 따라 구현하세요.

## 규칙 (절대 준수)
1. 지시서 [필수] 100% 구현, [금지] 절대 건드리지 말 것
2. 지시서 코드 블록은 직접 복사 반영 — 해석·의역 금지
3. `np.random.random()` 교체는 **정확히 4곳**. 다른 `np.random.default_rng(seed+N)` 패턴은 건드리지 말 것
4. 기존 `food_stockpile` NPC 매수를 **제거하지 말 것** — 후순위 강등만
5. 검증 순서 (모두 통과까지 반복):
   a. py -m py_compile
   b. py test_phase16c_internal_food_market.py (7/7)
   c. 기존 회귀 테스트 전부 (§검증 목록)
   d. 결정성 검증 (계약 검증 섹션)
   e. 2000틱 관측 → Hard 5개 지표 측정
6. Hard 기준 1개라도 미달 시 자가 수정 금지 — 결과 그대로 보고
7. 보고 양식: 지시서 §"실패 시 에스컬레이션" 템플릿 사용
```
