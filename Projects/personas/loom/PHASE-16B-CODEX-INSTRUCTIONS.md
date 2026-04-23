# Phase 16-B Codex Implementation Instructions

> **역할 분담**: Claude = 설계/리뷰, Codex = 구현. 이 문서는 Codex에게 넘기는 구현 지시서.
> **설계 원본**: [PHASE-16B-PRODUCTIVE-PUBLIC-WORKS-DESIGN.md](./PHASE-16B-PRODUCTIVE-PUBLIC-WORKS-DESIGN.md)
> **작업 범위**: Phase 16-B = Productive Public Works + NPC Outflow Control

---

## 0. Pre-flight (필수 선행 확인)

구현 시작 전 아래를 반드시 확인하고 결과를 보고서에 기록:

```bash
cd Projects/personas/loom
py -m py_compile ontology/layers.py core/multi_tick_engine.py observe_phase15_stack.py
py test_economy_balance.py     # 기존 PASS 확인 (baseline)
py test_phase12b_perf_npc.py   # 기존 PASS 확인
```

**금지 사항**
- 새 PersonaBrain 뉴런 추가 금지 (철학 원칙)
- 기존 SNN 축 외 임의 신호 만들기 금지
- `food_stockpile` 매수를 완전히 막지 말 것 — 조건 타이트화만
- `random.random()` / `random.sample()` 전역 호출 금지 → 반드시 `self.rng` 사용 (Step 1에서 초기화)

**커밋 단위**: Step 1~5 각각 개별 커밋. 메시지 접두사 `feat(phase16b):` / `test(phase16b):`.

---

## 1. Step-by-step 구현

### Step 1 — RNG 필드 초기화 (엔진 결정성 확보)

**파일**: `Projects/personas/loom/core/multi_tick_engine.py`

**위치**: `MultiTickEngine.__init__` 내부 (기존 필드 초기화 근처)

**변경**:

```python
# 최상단 import 블록 (이미 있으면 skip)
import random

# __init__ 내부 추가 (seed는 기존 설정값 재사용 or 고정)
self.rng: random.Random = random.Random(getattr(self, "_seed", 42))
```

> 기존 `self._seed` 필드가 있으면 그대로 사용. 없으면 `__init__` 시그니처에 `seed: int = 42` 추가하고 `self._seed = seed` 저장.

**자가 검증**: `py -c "from core.multi_tick_engine import MultiTickEngine; e=MultiTickEngine(); print(e.rng.random())"` 두 번 실행 → 동일 값 출력.

---

### Step 2 — 상수 + dataclass 필드 (`ontology/layers.py`)

**위치 1**: `GOLD_DIRECT_PAY_RATIO` 정의 바로 뒤 (현재 line 211)

**추가**:

```python
# ── Phase 16-B 추가 상수 ──────────────────────────────
PUBLIC_WORKS_IN_KIND_RATIO: float = 0.5         # 공공 생산물 중 영지 귀속 비율
STALE_SIGNAL_TICKS: int = 72                    # SNN 신호 유효 기간 (3 cycles)
FOOD_STOCKPILE_RESERVE_THRESHOLD: float = 30.0  # 이 미만일 때만 NPC food_stockpile 허용
QUARTER_TAX_BUDGET_MULTIPLIER: float = 1.2      # 공공지출 예산 = 분기세수 × 1.2
```

**위치 2**: `Territory` dataclass 내부 (현재 line 117-140)

**추가** (기존 필드 다음):

```python
    # ── Phase 16-B: 재정 추적 + 공공 생산물 누적 ──
    last_snn_signals_tick: int = -1
    inventory: dict = field(default_factory=lambda: {
        "food": 0.0, "material": 0.0, "tool": 0.0, "medicine": 0.0, "knowledge": 0.0,
    })
    quarter_tax_income: float = 0.0           # 이번 분기 누적 세수 (gold)
    quarter_public_spend: float = 0.0         # 이번 분기 누적 공공지출 (gold)
```

> `food_reserve` / `chronicle` / `last_snn_signals`는 **이미 존재**하므로 건드리지 말 것.

**`__init__.py` export**: `ontology/__init__.py`에 신규 상수 4개 추가.

**자가 검증**:
```bash
py -c "from ontology.layers import PUBLIC_WORKS_IN_KIND_RATIO, STALE_SIGNAL_TICKS, FOOD_STOCKPILE_RESERVE_THRESHOLD, QUARTER_TAX_BUDGET_MULTIPLIER; print('OK')"
py -c "from ontology.layers import Territory; t=Territory(id='x', name='x', region='claude'); print(t.quarter_tax_income, t.inventory, t.last_snn_signals_tick)"
```

---

### Step 3 — `_update_governance_policy` 수정 (`multi_tick_engine.py:1408`)

**목적**:
1. SNN readout을 `territory.last_snn_signals`에 이미 저장 중이면 그대로, 아니면 저장
2. `territory.last_snn_signals_tick = self.time.tick` 추가
3. 분기 종료(매 `QUARTER_TICKS` 혹은 기존 분기 루틴) 시 `quarter_tax_income` / `quarter_public_spend` 리셋

**Before → After 패턴**:

기존 policy 업데이트 말미 (policy_update 이벤트 append 직전):
```python
territory.last_snn_signals = {
    "growth": float(growth),
    "stability": float(stability),
    "tension": float(tension),
}
territory.last_snn_signals_tick = self.time.tick   # ← 추가
```

**세금 징수 로직** (line 1306 `tax_collected_total` 근처):
```python
territory.tax_collected_total += tax_amount
territory.quarter_tax_income += tax_amount          # ← 추가
```

**분기 리셋**: `_update_governance_policy` 내부에 분기 경계 감지 블록이 있을 것. 없으면 `_auto_economy_tick` 분기 경계에 아래 추가:
```python
if self.time.tick > 0 and self.time.tick % QUARTER_TICKS == 0:
    for t in self.territories.values():
        t.quarter_tax_income = 0.0
        t.quarter_public_spend = 0.0
```

> `QUARTER_TICKS` 상수가 기존에 있으면 재사용. 없으면 `QUARTER_TICKS: int = 168` (기존 분기 길이와 일치시킬 것 — grep으로 확인).

---

### Step 4 — `_process_public_works` 리팩토링 (`multi_tick_engine.py:2469`)

**기존 메서드 전체 교체**. 완전한 코드:

```python
def _process_public_works(self, territory_id: str) -> list[dict]:
    """Phase 16-B: SNN 기반 공공 고용 + 생산 기여.

    - Rate = growth*0.6 + tension*0.3 + stability*0.1  (cap 0.8)
    - Stale SNN (tick 차이 > STALE_SIGNAL_TICKS) 시 보류
    - 예산 상한: min(quarter_tax_income * 1.2, treasury * 0.5)
    - Unemployed only, lord 제외, vitality > 0, not sleeping
    - 생산물: 본 직업 × DURATION. IN_KIND_RATIO(0.5)는 영지, 나머지는 페르소나
    """
    territory = self.territories.get(territory_id)
    if not territory or territory.treasury_gold < PUBLIC_WORKS_MIN_TREASURY:
        return []

    # Stale guard
    if territory.last_snn_signals_tick < 0:
        return []
    sig_age = self.time.tick - territory.last_snn_signals_tick
    if sig_age > STALE_SIGNAL_TICKS:
        return []

    snn = territory.last_snn_signals or {}
    growth = float(snn.get("growth", 0.0))
    tension = float(snn.get("tension", 0.0))
    stability = float(snn.get("stability", 0.0))

    rate = min(0.8, max(0.0, growth * 0.6 + tension * 0.3 + stability * 0.1))
    territory.policy.public_works_rate = rate
    if rate < 0.1:
        return []

    wage_per_person = PUBLIC_WORKS_WAGE_PER_TICK * PUBLIC_WORKS_DURATION  # 120 gold

    # Budget cap
    qincome = float(getattr(territory, "quarter_tax_income", 0.0))
    cap_income = qincome * QUARTER_TAX_BUDGET_MULTIPLIER if qincome > 0 else float("inf")
    cap_treasury = territory.treasury_gold * PUBLIC_WORKS_MAX_TREASURY_RATIO
    budget_cap = min(cap_income, cap_treasury)
    if budget_cap < wage_per_person:
        return []

    # Candidate pool
    lord_id = getattr(territory, "lord_id", None)
    unemployed = [
        pid for pid, p in self.personas.items()
        if p.territory == territory_id
        and p.employment_id is None
        and pid != lord_id
        and float(self.inners[pid].vitality) > 0
        and not self.inners[pid].is_sleeping
    ]
    if not unemployed:
        return []

    n_hire = max(1, int(rate * len(unemployed)))
    max_affordable = int(budget_cap // wage_per_person)
    n_hire = min(n_hire, max_affordable, len(unemployed))
    if n_hire <= 0:
        return []

    chosen = self.rng.sample(unemployed, n_hire)

    events: list[dict] = []
    for pid in chosen:
        if territory.treasury_gold < wage_per_person:
            break
        persona = self.personas[pid]
        job_title = self._get_persona_job_title(pid) or "laborer"
        goods_type = JOB_OUTPUT_MAP.get(job_title, "material")
        base_output = JOB_BASE_OUTPUT.get(job_title, 0.5)

        produced = base_output * PUBLIC_WORKS_DURATION
        in_kind = produced * PUBLIC_WORKS_IN_KIND_RATIO
        to_persona = produced - in_kind

        # Wage transfer
        territory.treasury_gold -= wage_per_person
        territory.quarter_public_spend += wage_per_person
        self.wallets[pid].receive(wage_per_person)

        # In-kind: goods_type 별 분기
        if goods_type == "food":
            territory.food_reserve = getattr(territory, "food_reserve", 0.0) + in_kind
        else:
            territory.inventory[goods_type] = territory.inventory.get(goods_type, 0.0) + in_kind

        inner = self.inners[pid]
        inner.inventory[goods_type] = inner.inventory.get(goods_type, 0.0) + to_persona

        events.append({
            "type": "public_works",
            "territory": territory_id,
            "persona": pid,
            "wage": wage_per_person,
            "duration": PUBLIC_WORKS_DURATION,
            "rate": round(rate, 3),
            "snn_growth": round(growth, 3),
            "snn_tension": round(tension, 3),
            "snn_stability": round(stability, 3),
            "produced_type": goods_type,
            "produced_total": round(produced, 2),
            "in_kind_to_territory": round(in_kind, 2),
            "to_persona": round(to_persona, 2),
            "treasury_after": round(territory.treasury_gold, 1),
            "signal_age": sig_age,
        })
    return events
```

**import 확인**: 파일 상단에 아래 심볼이 import 되어 있어야 함 (기존 import 블록에서 확인·추가):

```python
from ontology.layers import (
    # 기존 import ...
    JOB_OUTPUT_MAP, JOB_BASE_OUTPUT,
    PUBLIC_WORKS_WAGE_PER_TICK, PUBLIC_WORKS_DURATION,
    PUBLIC_WORKS_MIN_TREASURY, PUBLIC_WORKS_MAX_TREASURY_RATIO,
    PUBLIC_WORKS_IN_KIND_RATIO, STALE_SIGNAL_TICKS,
    QUARTER_TAX_BUDGET_MULTIPLIER,
)
```

---

### Step 5 — NPC `food_stockpile` 매수 조건 타이트화

**위치**: `multi_tick_engine.py` line 1360 부근 (`territory.treasury_gold -= cost` 근처. `food_stockpile` 이벤트 append 직전 블록)

**변경**: NPC 매수 분기 진입 전에 가드 추가.

Before:
```python
# 기존: treasury > cost 만 체크해서 NPC 매수
if buy_qty >= 1 and cost <= territory.treasury_gold:
    territory.treasury_gold -= cost
    territory.food_reserve += buy_qty
    events.append({ "type": "food_stockpile", ... })
```

After:
```python
food_reserve = getattr(territory, "food_reserve", 0.0)

# [Phase 16-B] 조건 1: 이미 충분하면 NPC 매수 skip
if food_reserve >= FOOD_STOCKPILE_RESERVE_THRESHOLD:
    continue  # 또는 적절한 skip 분기

# [Phase 16-B] 조건 2: 시장에 food 매도 주문 있으면 NPC보다 시장 우선
has_market_food_order = any(
    getattr(o, "goods_type", None) == "food"
    and getattr(o, "territory_id", None) == territory_id
    for o in getattr(self, "market_orders", [])
)
if has_market_food_order:
    continue  # 시장 매수 우선 (별도 루틴에서 처리)

# 기존 NPC 매수 로직 이어서
if buy_qty >= 1 and cost <= territory.treasury_gold:
    territory.treasury_gold -= cost
    territory.food_reserve += buy_qty
    events.append({ "type": "food_stockpile", ... })
```

**주의**:
- 기존 `continue`가 올바른 루프 레벨에서 동작하는지 확인 (for territory / while / match-case).
- `continue`가 부적절한 구조이면 `if ... :` else 블록으로 감싸 skip 처리.
- `FOOD_STOCKPILE_RESERVE_THRESHOLD`는 Step 2에서 import.

**import 추가**:
```python
from ontology.layers import FOOD_STOCKPILE_RESERVE_THRESHOLD
```

---

### Step 6 — `_auto_economy_tick` 호출 순서 확인 (`multi_tick_engine.py:1042`)

Phase 16 구현에서 이미 `_process_public_works` 호출 중일 것. 아래 순서인지 확인:

```
_auto_economy_tick:
  1. 세금 징수 (quarter_tax_income 누적)
  2. Phase 16-B: for tid in territories: self._process_public_works(tid)
  3. food_stockpile (Step 5 조건 적용)
  4. _process_market
  5. _process_npc_shop
  6. 분기 경계 시 quarter_* 리셋
```

**핵심**: public_works는 세금 수입 반영 **후에**, food_stockpile **전에** 실행 (영지가 food 자급하면 NPC 매수 skip).

---

### Step 7 — 테스트 `test_phase16_public_works.py` 신규

**파일**: `Projects/personas/loom/test_phase16_public_works.py`

**스켈레톤 (9개 테스트, Codex가 완성)**:

```python
"""Phase 16-B: Productive Public Works 테스트."""
import sys
sys.path.insert(0, ".")

from core.multi_tick_engine import MultiTickEngine
from ontology.layers import (
    PUBLIC_WORKS_WAGE_PER_TICK, PUBLIC_WORKS_DURATION,
    PUBLIC_WORKS_MIN_TREASURY, PUBLIC_WORKS_IN_KIND_RATIO,
    STALE_SIGNAL_TICKS, JOB_OUTPUT_MAP, JOB_BASE_OUTPUT,
)


def _setup_engine(seed=42):
    """테스트용 엔진 + territory + personas 픽스처."""
    engine = MultiTickEngine(seed=seed)  # seed 인자 존재 확인 (Step 1)
    # 최소 영지 1개, 페르소나 3~5명 (고용주 + 실업자 + 영주)
    # 실제 MultiTickEngine 초기화 방식에 맞춰 조정
    return engine


def _inject_signals(territory, tick, *, growth=0.0, tension=0.0, stability=0.0):
    territory.last_snn_signals = {"growth": growth, "tension": tension, "stability": stability}
    territory.last_snn_signals_tick = tick


def test_snn_triggers_public_works():
    """growth=0.8 → public_works 이벤트 ≥ 1."""
    engine = _setup_engine()
    tid = next(iter(engine.territories))
    territory = engine.territories[tid]
    territory.treasury_gold = 2000.0
    territory.quarter_tax_income = 500.0
    _inject_signals(territory, engine.time.tick, growth=0.8)
    events = engine._process_public_works(tid)
    assert len(events) >= 1, f"expected public_works events, got {events}"
    assert events[0]["type"] == "public_works"


def test_rate_threshold_suppression():
    """growth=0, tension=0 → rate < 0.1 → 이벤트 0."""
    engine = _setup_engine()
    tid = next(iter(engine.territories))
    territory = engine.territories[tid]
    territory.treasury_gold = 2000.0
    _inject_signals(territory, engine.time.tick)  # 모두 0
    events = engine._process_public_works(tid)
    assert events == []


def test_treasury_min_guard():
    """treasury < PUBLIC_WORKS_MIN_TREASURY → 이벤트 0."""
    engine = _setup_engine()
    tid = next(iter(engine.territories))
    territory = engine.territories[tid]
    territory.treasury_gold = PUBLIC_WORKS_MIN_TREASURY - 1
    _inject_signals(territory, engine.time.tick, growth=0.8)
    events = engine._process_public_works(tid)
    assert events == []


def test_budget_cap_enforced():
    """quarter_tax_income * 1.2 가 wage_per_person 미만이면 이벤트 0."""
    engine = _setup_engine()
    tid = next(iter(engine.territories))
    territory = engine.territories[tid]
    territory.treasury_gold = 5000.0
    territory.quarter_tax_income = 50.0   # cap = 60, wage = 120 → 부족
    _inject_signals(territory, engine.time.tick, growth=0.8)
    events = engine._process_public_works(tid)
    assert events == []


def test_unemployed_only_and_lord_excluded():
    """lord_id + employment_id 있는 persona는 선택되지 않음."""
    engine = _setup_engine()
    tid = next(iter(engine.territories))
    territory = engine.territories[tid]
    territory.treasury_gold = 3000.0
    territory.quarter_tax_income = 500.0
    _inject_signals(territory, engine.time.tick, growth=0.8)
    # lord 지정 + 다른 persona 하나에 employment_id 설정
    # ...
    events = engine._process_public_works(tid)
    chosen_pids = {ev["persona"] for ev in events}
    assert territory.lord_id not in chosen_pids
    # employment_id 있는 persona id도 chosen_pids에 없음


def test_wallet_and_treasury_transfer():
    """wage_per_person 정확히 이동: treasury -=, wallet +=."""
    engine = _setup_engine()
    tid = next(iter(engine.territories))
    territory = engine.territories[tid]
    territory.treasury_gold = 3000.0
    territory.quarter_tax_income = 500.0
    _inject_signals(territory, engine.time.tick, growth=0.8)
    t_before = territory.treasury_gold
    wallets_before = {pid: w.gold for pid, w in engine.wallets.items()}
    events = engine._process_public_works(tid)
    wage = PUBLIC_WORKS_WAGE_PER_TICK * PUBLIC_WORKS_DURATION
    assert territory.treasury_gold == t_before - wage * len(events)
    for ev in events:
        assert engine.wallets[ev["persona"]].gold == wallets_before[ev["persona"]] + wage


def test_productive_in_kind_credit():
    """생산물이 goods_type에 따라 영지에 정확히 귀속."""
    engine = _setup_engine()
    tid = next(iter(engine.territories))
    territory = engine.territories[tid]
    territory.treasury_gold = 3000.0
    territory.quarter_tax_income = 500.0
    _inject_signals(territory, engine.time.tick, growth=0.8)
    food_before = territory.food_reserve
    inv_before = dict(territory.inventory)
    events = engine._process_public_works(tid)
    for ev in events:
        gt = ev["produced_type"]
        ik = ev["in_kind_to_territory"]
        if gt == "food":
            assert territory.food_reserve >= food_before  # 누적
        else:
            assert territory.inventory[gt] >= inv_before.get(gt, 0)


def test_stale_signal_suppressed():
    """sig_age > STALE_SIGNAL_TICKS → 이벤트 0."""
    engine = _setup_engine()
    tid = next(iter(engine.territories))
    territory = engine.territories[tid]
    territory.treasury_gold = 3000.0
    territory.quarter_tax_income = 500.0
    _inject_signals(territory, engine.time.tick - STALE_SIGNAL_TICKS - 1, growth=0.8)
    events = engine._process_public_works(tid)
    assert events == []


def test_stable_random_selection():
    """같은 seed → 같은 선택 결과."""
    def run():
        engine = _setup_engine(seed=42)
        tid = next(iter(engine.territories))
        territory = engine.territories[tid]
        territory.treasury_gold = 3000.0
        territory.quarter_tax_income = 500.0
        _inject_signals(territory, engine.time.tick, growth=0.8)
        events = engine._process_public_works(tid)
        return [ev["persona"] for ev in events]
    assert run() == run()


if __name__ == "__main__":
    tests = [
        test_snn_triggers_public_works,
        test_rate_threshold_suppression,
        test_treasury_min_guard,
        test_budget_cap_enforced,
        test_unemployed_only_and_lord_excluded,
        test_wallet_and_treasury_transfer,
        test_productive_in_kind_credit,
        test_stale_signal_suppressed,
        test_stable_random_selection,
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

**Codex에게 남긴 자유도**:
- 테스트 픽스처(`_setup_engine`) 내부는 `MultiTickEngine` 실제 초기화 방식에 맞춰 완성.
- persona 3~5명 수동 추가(필요 시), lord_id 수동 지정, employment_id 한 명 세팅.
- 테스트 1~2개는 통합 테스트가 필요할 수 있음 (2000틱 시뮬 대신 수십 틱).

---

### Step 8 — 관측 스크립트 확장 (`observe_phase15_stack.py`)

기존 Phase 16 집계 블록 근처에 추가:

```python
from collections import defaultdict

# 이미 있는 public_works_events 활용
in_kind_total = defaultdict(float)
for _, ev in public_works_events:
    gt = ev.get("produced_type", "?")
    in_kind_total[gt] += float(ev.get("in_kind_to_territory", 0))

print("\n" + "─" * 70)
print("  Phase 16-B: Productive Public Works")
print("─" * 70)
print(f"  public_works events       : {len(public_works_events)}")
print(f"  total wage paid            : {sum(ev.get('wage', 0) for _, ev in public_works_events):.0f}")
print(f"  in-kind goods to territory :")
for gt, amt in in_kind_total.items():
    print(f"    {gt:12s} {amt:.1f}")

# Total Wealth 지표
GOODS_VALUE = {"food": 10, "material": 15, "tool": 60, "medicine": 30, "knowledge": 45}
persona_gold = sum(w.gold for w in engine.wallets.values())
treasury_total = sum(t.treasury_gold for t in engine.territories.values())
persona_goods = sum(
    inner.inventory.get(g, 0) * v
    for inner in engine.inners.values()
    for g, v in GOODS_VALUE.items()
)
territory_goods = sum(
    t.inventory.get(g, 0) * v
    for t in engine.territories.values()
    for g, v in GOODS_VALUE.items()
) + sum(getattr(t, "food_reserve", 0) * GOODS_VALUE["food"] for t in engine.territories.values())
total_wealth = persona_gold + treasury_total + persona_goods + territory_goods

initial_wealth = total_initial + sum(initial_treasury.values()) + (20 * 3 * GOODS_VALUE["food"])  # 근사
print(f"\n  Total Wealth = gold + treasury + goods value")
print(f"    persona gold     : {persona_gold:.0f}")
print(f"    treasury total   : {treasury_total:.0f}")
print(f"    persona goods    : {persona_goods:.0f}")
print(f"    territory goods  : {territory_goods:.0f}")
print(f"    TOTAL            : {total_wealth:.0f}")
```

> Codex는 기존 `observe_phase15_stack.py` 구조를 읽어 삽입 위치를 결정. 출력 섹션은 "Phase 15-C" 뒤, "Economy Snapshot" 앞이 자연스러움.

---

## 2. 검증 명령 (Codex 자가 체크리스트)

구현 완료 후 **반드시** 아래 순서 실행 및 결과 기록:

```bash
cd Projects/personas/loom

# 1) 정적 검사
py -m py_compile ontology/layers.py core/multi_tick_engine.py observe_phase15_stack.py test_phase16_public_works.py

# 2) Phase 16-B 전용 테스트
py test_phase16_public_works.py
# 기대: 9/9 passed

# 3) 기존 회귀 테스트 (전부 PASS 필수)
py test_economy_balance.py
py test_phase12b_perf_npc.py
py test_nomos.py
py test_class_promotion.py

# 4) 2000틱 관측
py observe_phase15_stack.py 2>&1 | tail -80
```

---

## 3. 합격 기준 (2000틱)

**Hard (전부 통과 필수)**
| 지표 | 기준 | 측정 |
|---|---|---|
| persona gold 감소율 | ≤ **-70%** (≥ 6000) | Economy Snapshot `total persona gold` |
| total_wealth 감소율 | ≤ **-40%** | Phase 16-B 섹션 출력 |
| deaths | 0 / 10 | Economy Snapshot `deaths` |
| test_phase16_public_works.py | 9/9 PASS | test 결과 |
| 기존 회귀 테스트 전체 | 모두 PASS | 각 test 결과 |

**Soft (리포트 기재, 미달 시 Phase 16-C 분석 필요)**
| 지표 | 기준 |
|---|---|
| public_works events | ≥ 50 |
| territory food_reserve 최종 (3영지 합) | ≥ 60 |
| food_stockpile 이벤트 | ≤ 34 (Phase 16 기준 69건 대비 ≤50%) |

---

## 4. 보고 형식 (PR/결과 본문 템플릿)

구현 완료 후 아래 형식으로 보고:

```markdown
## Phase 16-B Implementation Report

### Changes
- ontology/layers.py: 상수 4개 + Territory 필드 4개
- core/multi_tick_engine.py: _process_public_works 재작성, _update_governance_policy 확장, food_stockpile 조건 강화, RNG 초기화
- observe_phase15_stack.py: Phase 16-B 섹션 + Total Wealth
- test_phase16_public_works.py: 9 tests (신규)

### Verification
- py_compile: PASS
- test_phase16_public_works.py: N/9 passed
- 기존 회귀: (목록별 PASS/FAIL)
- 2000틱:
  - persona gold: 20000 → X (Y%)
  - total_wealth: I → F (D%)
  - deaths: 0/10
  - public_works events: N
  - food_stockpile events: N

### Acceptance
- Hard: [✓/✗] persona gold, [✓/✗] total_wealth, [✓/✗] deaths, [✓/✗] tests
- Soft: [✓/✗] events ≥ 50, [✓/✗] food_reserve ≥ 60, [✓/✗] stockpile ≤ 34

### Deviations (if any)
- (Codex가 설계에서 벗어난 결정은 여기 기록 — 이유 포함)
```

---

## 5. 실패 시 에스컬레이션 경로

- Hard 기준 1개 이상 미달 → 수정 금지. 결과 그대로 보고하고 Claude에게 Phase 16-C 지시 요청.
- 테스트가 설계 상 불가능한 케이스 발견 → 구현 중단하고 즉시 보고.
- 기존 회귀 테스트 FAIL → 원인 추적 후 본 작업이 아닌 별도 이슈로 보고 (이 작업은 기존 테스트를 깨지 말 것).

---

## 6. Notes

- **"gold가 오르도록" 하드코딩 금지**. 이 지시서의 모든 수식은 SNN 입력 → 결정 흐름을 유지.
- `self.rng`를 통한 결정적 무작위성 → 테스트 재현성 확보.
- 기존 `food_reserve`, `chronicle`, `last_snn_signals`, `policy`는 이미 존재하므로 **재정의하지 말 것**.
- `QUARTER_TICKS` 값은 **기존 코드 검색 후** 결정. 중복 정의 금지.
