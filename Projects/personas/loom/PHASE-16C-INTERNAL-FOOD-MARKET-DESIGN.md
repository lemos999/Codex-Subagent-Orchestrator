# Phase 16-C: Internal Food Market — 영지가 페르소나에게서 직접 매수

## 배경

Phase 16-B 구현 결과 (2000틱, 2026-04-18):

| 지표 | 공식 관측 | 보강 관측 | Hard 기준 | 결과 |
|---|---|---|---|---|
| persona gold | 20000 → 1703 (-91.5%) | 20000 → 5194 (-74.0%) | ≤-70% | **FAIL** |
| total_wealth | 33950 → 30126 (-11.3%) | - | ≤-40% | **PASS** |
| deaths | 0/10 | 0/10 | 0 | PASS |
| public_works events | 12 | 9 | ≥50 | **FAIL** |
| food_stockpile events | 88 | 136 | ≤34 | **FAIL** |
| food_reserve 합 | - | 3615 | ≥60 | PASS |

회귀: 9/9 + 기존 테스트 모두 PASS. 구현은 정확. **목표 경제 효과가 부족**.

---

## 근본 원인 재추적 ("왜?" 5단)

1. persona gold 감소 → **왜?**
   → food_stockpile 88~136건이 treasury gold를 NPC로 유출 + 페르소나 gold도 긴급 식량 매수로 NPC 유출

2. food_stockpile이 왜 저리 많이? → **왜?**
   → `reserve < 30` threshold를 영지 인구 대비 자주 밑돎. 10 persona × food 소비 1/tick × 24tick = 240/day → reserve 30은 1.25일치만. 매우 낮은 안전재고

3. Phase 16-B의 productive public works 수확이 왜 부족? → **왜?**
   → public_works 이벤트가 12건뿐. rate < 0.1 게이트에 대부분 걸림. SNN signals `growth`가 대부분 낮아 `rate = growth*0.6 + tension*0.3 + stability*0.1`이 0.1 미만

4. public_works가 자주 트리거되어도 food 공급이 메울 수 있나? → **왜?**
   → 120 gold wage × 현재 job 분포(craftsman 우세) → tool/material만 생산. food 자급 거의 없음. public_works가 food 공급 루프에 기여하지 못함

5. **근본**: 영지의 식량 조달이 **"NPC에서 사거나 / public_works로 만들거나" 이분법**. 그런데 이미 farmer 페르소나가 food를 생산하고 있음. **영지와 farmer 사이에 직접 거래 경로가 없어** treasury가 NPC로 새고 farmer는 inventory에 food를 쌓아둠

---

## Phase 16-C 해결 축

세 축을 함께 투입. 각 축은 기존 시스템을 *대체*가 아닌 *추가*.

### 축 1. Internal Food Procurement — 영지-페르소나 직접 매수 (핵심)

영지가 NPC로 가기 전에 **자기 영지 내 farmer에게서 food를 매입**. gold: treasury → farmer wallet (영지 내 순환, NPC 유출 0).

**우선순위 체인 (food_stockpile 분기 수정)**:
```
1. 영지 food_reserve >= threshold          → skip (기존 Phase 16-B)
2. 영지 내 farmer inventory food 잉여 탐색 → procure from farmer (Phase 16-C 신규)
3. 영지 market_orders에 food 매도 주문 존재 → buy from market (기존 Phase 16-B)
4. 그래도 모자람                            → NPC 매수 (기존, 최후 수단)
```

**매수 가격**: `NPC.buy * 0.75` (페르소나에게는 NPC보다 불리하지만 저장 비용·상하는 위험 상쇄 유인)

**farmer 측 조건**:
- inventory food > `PERSONA_FOOD_SAFE_STOCK` (기본 24 = 하루치)를 초과하는 잉여만 매도
- 같은 영지에 속함
- vitality > 0, not sleeping

### 축 2. Public Works Frequency Boost

**rate 공식 개선**:
```
rate = min(0.8, max(0.0,
  growth * 0.5 + tension * 0.3 + stability * 0.15 + hunger_pressure * 0.2
))
```
- `hunger_pressure` = 영지 내 persona 평균 `consecutive_hunger_ticks` 정규화 (0~1). 기아 신호는 영지가 SNN 외에 관측하는 **구체 생활지표**. 새 뉴런이 아닌, 이미 추적 중인 필드의 합산
- hunger가 쌓이면 rate 강제 상승 → food 부족 시 공공 고용 확대 → farmer 공공 고용 → food 생산

**threshold 조정**: `rate < 0.1` → `rate < 0.05` (발동 턱 낮춤)

**job 편향 보정**: public_works 대상 선정 시 **farmer > 기타 비율 2:1** 가중 (hunger_pressure > 0.3일 때). food 공급 부족 상황에서 자연히 농업에 인력 투입.

### 축 3. Determinism (같은 seed에서 관측 일관성)

현재 `self.rng` 추가로 Python 측은 결정적이나, **numpy 기반 SNN 경로가 비결정적**.

```python
# MultiTickEngine.__init__
import numpy as np
self._np_rng: np.random.Generator = np.random.default_rng(self._seed)
# SNN firing 계산·정책 변동 등에서 전역 np.random 대신 self._np_rng 사용
```

이와 병행하여 SNN 관련 모든 `np.random.*` 호출을 `self._np_rng.*`로 교체. 범위: `brain/`, `core/`, `ontology/` 내 SNN 경로만. 기타는 그대로.

---

## 변경 파일 (4~5개)

1. `Projects/personas/loom/ontology/layers.py`
   - 상수 추가: `INTERNAL_FOOD_PRICE_RATIO`, `PERSONA_FOOD_SAFE_STOCK`, `PUBLIC_WORKS_RATE_MIN`, `HUNGER_PRESSURE_WEIGHT`
   - (필요 시) `Territory.internal_food_procured_total` 누적 필드
2. `Projects/personas/loom/core/multi_tick_engine.py`
   - `_process_internal_food_procurement(territory_id)` 신규
   - `food_stockpile` 매수 로직에서 신규 함수 호출 분기 (축 1)
   - `_process_public_works` 수정: hunger_pressure 계산, farmer 가중 선택, rate_min 적용 (축 2)
   - `self._np_rng` 초기화 + SNN 경로 교체 (축 3)
3. `Projects/personas/loom/observe_phase15_stack.py`
   - `internal_food_procurement` 집계, 공급망 breakdown 출력
4. `Projects/personas/loom/test_phase16c_internal_food_market.py` (신규)
5. (필요 시) `Projects/personas/loom/brain/*.py` — SNN np.random 교체 (축 3)

---

## 구현 순서

### Step 1 — 상수 (`layers.py`)

Phase 16-B 상수 뒤에 추가:
```python
# ── Phase 16-C 추가 상수 ─────────────────────────
INTERNAL_FOOD_PRICE_RATIO: float = 0.75       # 영지 매수가 = NPC.buy * 0.75
PERSONA_FOOD_SAFE_STOCK: float = 24.0         # farmer 개인 안전재고 (이 초과분만 매도)
PUBLIC_WORKS_RATE_MIN: float = 0.05           # rate 하한 (기존 0.1 완화)
HUNGER_PRESSURE_WEIGHT: float = 0.2           # rate 공식에서 hunger 가중치
PUBLIC_WORKS_FARMER_BIAS: float = 2.0         # hunger_pressure > 0.3일 때 farmer 선택 가중
HUNGER_TRIGGER_THRESHOLD: float = 0.3         # 이 이상이면 farmer 편향 활성
```

`Territory`에 누적 필드 추가:
```python
    internal_food_procured_total: float = 0.0   # 영지가 자영자에게서 매입한 총 food
```

### Step 2 — `_process_internal_food_procurement` 신규

```python
def _process_internal_food_procurement(
    self, territory_id: str, target_qty: float
) -> tuple[float, list[dict]]:
    """Phase 16-C: 영지가 같은 영지 farmer에게서 food 매입.

    Returns:
        (procured_qty, events) — target_qty 중 실제 조달된 양과 이벤트 리스트
    """
    territory = self.territories.get(territory_id)
    if not territory or target_qty <= 0:
        return 0.0, []

    npc_food = NPC_PRICES.get("food", {})
    unit_price = float(npc_food.get("buy", 10)) * INTERNAL_FOOD_PRICE_RATIO

    # 영지 내 farmer 후보 (food inventory 잉여 보유)
    candidates = []
    for pid, persona in self.personas.items():
        if persona.territory != territory_id:
            continue
        if float(self.inners[pid].vitality) <= 0:
            continue
        if self.inners[pid].is_sleeping:
            continue
        food_stock = float(self.inners[pid].inventory.get("food", 0))
        surplus = food_stock - PERSONA_FOOD_SAFE_STOCK
        if surplus <= 0:
            continue
        candidates.append((pid, surplus))

    if not candidates:
        return 0.0, []

    # 결정적 순서 — 잉여 큰 순 + pid 알파벳
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
            # 예산 안에서 부분 매수
            if unit_price <= 0:
                break
            qty = territory.treasury_gold / unit_price
            cost = qty * unit_price
            if qty < 1.0:
                break

        territory.treasury_gold -= cost
        self.wallets[pid].receive(cost)
        self.inners[pid].inventory["food"] = (
            float(self.inners[pid].inventory.get("food", 0)) - qty
        )
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

### Step 3 — `food_stockpile` 분기에서 호출

기존 로직 (reserve 체크 → 시장 체크 → NPC 매수)의 **시장 체크와 NPC 매수 사이**에 삽입:

```python
# [Phase 16-B] reserve 충분 시 skip
if territory.food_reserve >= FOOD_STOCKPILE_RESERVE_THRESHOLD:
    continue

# [Phase 16-C] 영지 내 farmer 직접 매입 우선
shortfall = target_reserve - territory.food_reserve
if shortfall > 0:
    procured, ip_events = self._process_internal_food_procurement(
        territory_id, shortfall
    )
    events.extend(ip_events)
    if territory.food_reserve >= FOOD_STOCKPILE_RESERVE_THRESHOLD:
        continue  # 내부 조달로 충족 → NPC 매수 불필요

# [Phase 16-B] 시장 매도 주문 우선
has_market_food_order = any(
    getattr(o, "goods_type", None) == "food"
    and getattr(o, "territory_id", None) == territory_id
    for o in getattr(self, "market_orders", [])
)
if has_market_food_order:
    continue

# [기존] NPC 매수 (최후)
if buy_qty >= 1 and cost <= territory.treasury_gold:
    territory.treasury_gold -= cost
    territory.food_reserve += buy_qty
    events.append({"type": "food_stockpile", ...})
```

> `target_reserve`는 기존 코드에서 쓰이는 목표치. 기존 NPC buy_qty 산정식과 동일 기준. grep으로 확인.

### Step 4 — `_process_public_works` 수정 (축 2)

**hunger_pressure 계산 helper**:
```python
def _calc_hunger_pressure(self, territory_id: str) -> float:
    """영지 내 persona 평균 consecutive_hunger_ticks를 0~1로 정규화."""
    vals = [
        float(self.inners[pid].consecutive_hunger_ticks)
        for pid, p in self.personas.items()
        if p.territory == territory_id
    ]
    if not vals:
        return 0.0
    avg = sum(vals) / len(vals)
    # 72틱(3 cycle) 이상이면 상한 도달
    return min(1.0, avg / 72.0)
```

**rate 공식 교체**:
```python
hunger = self._calc_hunger_pressure(territory_id)
rate = min(0.8, max(0.0,
    growth * 0.5 + tension * 0.3 + stability * 0.15 + hunger * HUNGER_PRESSURE_WEIGHT
))
territory.policy.public_works_rate = rate
if rate < PUBLIC_WORKS_RATE_MIN:
    return []
```

**farmer 편향 선택** (기존 `self.rng.sample(unemployed, n_hire)` 대체):
```python
if hunger >= HUNGER_TRIGGER_THRESHOLD:
    weights = []
    for pid in unemployed:
        job_title = self._get_persona_job_title(pid) or ""
        w = PUBLIC_WORKS_FARMER_BIAS if job_title == "farmer" else 1.0
        weights.append(w)
    # 가중 무작위 sampling without replacement (rng 사용)
    chosen = self._weighted_sample_without_replacement(unemployed, weights, n_hire)
else:
    chosen = self.rng.sample(unemployed, n_hire)
```

**헬퍼**:
```python
def _weighted_sample_without_replacement(
    self, population: list, weights: list[float], k: int
) -> list:
    """self.rng 기반 가중 추출. Efraimidis-Spirakis 알고리즘."""
    if k >= len(population):
        return list(population)
    keyed = []
    for item, w in zip(population, weights):
        if w <= 0:
            continue
        u = self.rng.random()
        # key = u^(1/w)
        key = u ** (1.0 / w)
        keyed.append((key, item))
    keyed.sort(key=lambda x: -x[0])
    return [item for _, item in keyed[:k]]
```

event에 추가 필드:
```python
"hunger_pressure": round(hunger, 3),
"farmer_bias_active": hunger >= HUNGER_TRIGGER_THRESHOLD,
```

### Step 5 — numpy 결정성 (`multi_tick_engine.py` + `brain/*.py`)

`__init__`:
```python
import numpy as np
self._np_rng: np.random.Generator = np.random.default_rng(self._seed)
```

SNN 관련 파일(`brain/persona_brain.py`, `brain/lif_network.py` 등)에서 `np.random.*` 호출 grep:
```bash
grep -rn "np\.random\." Projects/personas/loom/brain Projects/personas/loom/core Projects/personas/loom/ontology
```

교체 원칙:
- SNN·policy 경로: 엔진에서 `np_rng` 주입 (함수 인자 또는 메서드) 후 `rng.normal`, `rng.uniform`, `rng.choice` 사용
- UI/로그/초기 seed 등 비핵심 경로: 교체 불요

**불확실성**: brain 모듈이 엔진 참조 없이 독립이면 별도 RNG 인스턴스를 생성자에 전달. 이 부분은 Codex가 코드 구조 확인 후 결정. 원칙은 "같은 seed → 같은 2000틱 수치".

### Step 6 — 테스트 `test_phase16c_internal_food_market.py`

7개 focused test:
1. `test_internal_procurement_from_farmer` — farmer에게 food 잉여 세팅, 영지 매수 호출, farmer wallet += cost / inventory -= qty 확인
2. `test_no_surplus_no_procurement` — 모든 farmer food <= safe_stock → procured=0
3. `test_procurement_respects_treasury` — treasury 부족 시 부분 매수
4. `test_food_stockpile_prefers_internal_over_npc` — farmer 잉여 존재 시 NPC food_stockpile 이벤트 발생 0
5. `test_hunger_pressure_raises_rate` — hunger_ticks 조작 → rate >= PUBLIC_WORKS_RATE_MIN 통과
6. `test_farmer_bias_selection` — hunger > 0.3, farmer 1명 + 비-farmer 5명 → 샘플에 farmer 포함 확률 높음 (통계)
7. `test_determinism_seed` — seed=42 두 번 돌려 동일 결과 (public_works 선택, 2000틱은 길어서 200틱 축소)

### Step 7 — 관측 스크립트 확장

`observe_phase15_stack.py`에 추가:
```
Phase 16-C: Internal Food Market
─────────────────────────────────
  internal_food_procurement events : N
  total food procured internally   : X.X
  total gold to farmers (internal) : Y
  food supply chain breakdown:
    internal (farmer→territory) : X
    market   (P2P order)        : X
    NPC      (food_stockpile)   : X
```

---

## 검증 (2000틱)

**Hard (전부 필수)**:
| 지표 | 기준 |
|---|---|
| persona gold 감소율 | ≤ -70% |
| total_wealth 감소율 | ≤ -40% |
| deaths | 0/10 |
| public_works events | ≥ 50 |
| food_stockpile events | ≤ 34 |
| 회귀 테스트 전체 | PASS |
| Phase 16-C 신규 테스트 | 7/7 PASS |

**Soft (기록)**:
- `internal_food_procurement events` ≥ 40 (새 경로 활성화 증거)
- 같은 seed 2회 실행 수치 편차 ≤ 1% (축 3 효과)
- farmer 공공 고용 비율 ≥ hunger 시나리오에서 30%

**불합격 시 Phase 16-D 방향**:
- persona gold 기준만 실패 → 축 1의 `INTERNAL_FOOD_PRICE_RATIO` 0.75 → 0.85 (farmer 측 이득 증대)
- public_works ≥ 50 실패 → rate_min 0.05 → 0.03, hunger weight 0.2 → 0.3
- food_stockpile ≤ 34 실패 → `FOOD_STOCKPILE_RESERVE_THRESHOLD` 30 → population × 5 동적
- 결정성 실패 → brain/core 전체 np.random grep 재확인, 누락된 경로 교체

---

## SNN 창발 관점

| SNN 변화 | Phase 16-C 반응 |
|---|---|
| `growth` ↑ | public_works rate ↑ → 고용 ↑ (Phase 16-B 유지) |
| `tension` ↑ | public_works rate ↑ (긴급 고용) |
| `stability` ↑ | rate 완만 상승 |
| **hunger_pressure** ↑ | **rate 강제 상승 + farmer 편향** (16-C 신규) |
| 영지 food_reserve 부족 | NPC 대신 farmer 매수 → treasury → farmer wallet (영지 내 순환) |

**철학**: 규칙은 "어떻게 조달할지" 우선순위 체인만 정의. 실제로 **얼마나, 누구에게서, 언제** 살지는 페르소나 재고·SNN·가격으로 결정. hunger_pressure는 기존 필드 합산이지 새 뉴런 아님.

---

## 변경 범위 요약

| 파일 | 성격 |
|---|---|
| `layers.py` | 상수 + Territory 필드 |
| `multi_tick_engine.py` | 신규 함수 2개 + 기존 수정 2곳 + RNG 추가 |
| `brain/*.py` | np.random → _np_rng 교체 (축 3만) |
| `observe_phase15_stack.py` | 집계 섹션 추가 |
| `test_phase16c_internal_food_market.py` | 신규 7 tests |

철학 원칙 재확인:
- 새 뉴런 0개
- 새 SNN 축 0개
- gold 하드코딩 주입 0건 — 전부 "조달 경로 우선순위"와 "기존 필드 기반 가중치"
- food_stockpile은 **여전히 살아있음** — 단지 후순위
- Phase 16-B 구조 전부 유지 — 위에 3개 축만 덧붙임

---

## 다음 단계

1. 본 설계 승인
2. Codex용 구현 지시서 `PHASE-16C-CODEX-INSTRUCTIONS.md` 작성 (별도 요청 시)
3. `/harness --evolve`로 구현 루프
4. 2000틱 검증 후 합격/Phase 16-D 판단
