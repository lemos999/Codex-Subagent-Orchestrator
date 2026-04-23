# [기능+리팩토링] Phase 16-E: Public Works 후보 확장 + Food Crisis Mode + 초기 농장 — Codex 구현 지시서

> 긴급도: 높음 (Phase 16-D 이후 Hard 3개 여전히 실패 — public_works 9건 · persona gold 3328 · NPC 65건)
> 선행 조건: Phase 16-D 구현 완료 (`PUBLIC_WORKS_BASE_ACTIVATION=0.04`, `NPC_FOOD_PURCHASE_COOLDOWN_TICKS=48`, `FOOD_STOCKPILE_RESERVE_PER_PERSONA=14.0`, `NPC_FOOD_TRIGGER_RESERVE_RATIO=0.5`, `Territory.last_npc_food_purchase_tick`)
> 작업 유형: 기능(신규 메서드 1개 + 신규 필드 2개) + 리팩토링(기존 메서드 2개 로직 확장)
> DB migration: 없음 (Python 메모리 시뮬)
> 외부 의존: 없음

---

## 배경

Phase 16-D 는 구현·테스트·결정성 모두 PASS 했지만 2000틱 Hard 중 3개 여전히 실패:

| 지표 | 기준 | 16-C | 16-D | 비고 |
|---|---|---|---|---|
| persona gold final | ≥ 6000 | 2960 | **3328** | 회복 절대 부족 |
| public_works events | ≥ 50 | 6 | **9** | base activation 도움 안 됨 |
| NPC treasury food_stockpile | ≤ 34 | 71 | **65** | cooldown 작동하나 내부 공급 부족 |
| total_wealth | ≥ −40% | +13.8% | +100.7% | PASS |
| deaths | 0 | 0 | 0 | PASS |

관측: `cooldown_skip = 45` → cooldown 은 작동하지만 skip 동안 내부 공급이 그 공백을 못 채움.

### 근본 원인 5단 재추적 (코드 확증)

**A. public_works 9건만 (rate 통과율 ~100% vs 이벤트율 11%)**

rate `≥ 0.03` 통과 후 4개 후속 gate:
1. `budget_cap < wage_per_person` (`_process_public_works:2681`)
2. **`if not unemployed: return []` (`_process_public_works:2693`)** ← 진짜 병목
3. `n_hire <= 0`
4. 대상자 `treasury_gold < wage`

[multi_tick_engine.py:2685-2692](./core/multi_tick_engine.py#L2685) 에서 후보가 `persona.employment_id is None` 전용. **Phase 15 고용 lifecycle 이 잘 작동하면 unemployed 는 거의 비어있음** → 공공근로가 구조적으로 불발.

**B. 식량 생산 구조 적자**

- `JOB_BASE_OUTPUT["farmer"] = 2.0` × farmer 2~3명 ≈ 4~6 food/tick
- 생존 소비 ≈ 10 food/tick (population 10)
- **구조적 적자 4~6/tick** — NPC 없이는 감당 불가

**C. food_priority 무관 internal procurement (Phase 16-D 축 2)**

`_process_food_reserve` 에서 internal 먼저 시도하나 페르소나 전체 surplus 가 부족해서 4건만 기록됨.

**D. `cooldown_skip 45 + NPC 65`**

cooldown 경과 시점마다 reserve < target × 0.5 = 70 이므로 매번 NPC 매수 재점화. **내부 생산이 공백을 못 채움**.

**E. 최근본**: Phase 15 정규고용과 Phase 16 임시 공공근로가 **배타적 후보 풀** 을 경쟁함. 공공근로가 "employment_id is None" 으로만 필터 → 24틱 double-role 허용 안 함.

### Phase 16-E 3축 개입

| 축 | 대응 근본 | 변경 | 기대 효과 |
|---|---|---|---|
| §A | E, A | public_works 후보 확장: unemployed OR (low_gold AND hungry) | 후보 풀 3~4배, 이벤트 9→50+ |
| §B | B, C, D | food crisis mode: hunger 압력 + reserve 비상 시 **전원 food labor** (비farmer 0.7× 패널티) — 근본 C(food_priority 무관 internal 부족) 는 "전원 food" 배치로 internal procurement 의 공급 부족을 직접 **대체** | food 생산 분기 확보, NPC 구매 대체 |
| §C | B | Territory.communal_farms=1 초기 부여 + food 생산 `× (1 + farms × 0.3)` 증폭, farm 확장은 food crisis 3회 반복 시 자동 `build_farm` 이벤트 | 구조적 적자 완화 (창발 확장) |

**철학 준수**: 새 뉴런 0 · 새 SNN 축 0 · gold 하드코딩 주입 0 · NPC 매수 제거 안 함 · food 자동 생성 안 함 · 페르소나 행동 override 0 · Phase 16-D 구조 유지.

### 역산 목표 (GPT 리뷰 수치 재확인)

- 추가 공공근로 41건 필요 — **축 A 로 충분**
- 추가 food 공공근로 12건 필요 — **축 B + C 로 확보**
- 추가 reserve food 400+ 필요 — farmer 12건 × base 2.0 × duration 24 × in_kind 0.5 × (1 + 1 × 0.3) = 374, 비farmer 추가로 400+ 도달

---

## 작업 범위

### [필수]

1. `ontology/layers.py` 신규 상수 8개
   - `PUBLIC_WORKS_LOW_GOLD_THRESHOLD: float = 300.0`
   - `PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD: int = 12`
   - `FOOD_LABOR_NON_FARMER_RATIO: float = 0.7`
   - `COMMUNAL_FARM_BOOST: float = 0.3`
   - `FOOD_CRISIS_FARM_THRESHOLD: float = 3.0` — float 로 통일 (counter 가 비대칭 감소하므로)
   - `FARM_EXPANSION_COST_GOLD: float = 500.0`
   - `FOOD_CRISIS_RESERVE_RATIO: float = 0.4`
   - `FOOD_CRISIS_COUNTER_DECAY: float = 0.5` — NPC 무매수 사이클당 counter 감소량 (+1/-0.5 비대칭)

   **비대칭 근거**: NPC 매수 시 +1, 무매수 시 -0.5. Phase 16-D 관측치 "NPC 매수 65회/2000틱 / 24틱 주기 = 전체 사이클 83회 중 65회 매수" 기준 시뮬: counter 상승이 하락을 2배로 앞서므로 2~3 사이클 만에 threshold(3) 도달 → farm_expansion 1~3회 실현 가능. 대칭(+1/-1)이면 양극단 (0 고착 또는 50+)으로 쏠려 §12 기대값 미달.

2. `Territory` 에 신규 필드 2개
   - `communal_farms: int = 1`
   - `food_crisis_counter: float = 0.0` — float (counter 가 0.5 단위로 감소)

3. `_process_public_works` 확장:
   - 후보 풀: unemployed OR (low_gold AND hungry) — `employment_id` 는 건드리지 않음
   - food crisis mode: `hunger ≥ HUNGER_TRIGGER_THRESHOLD AND reserve < reserve_target × FOOD_CRISIS_RESERVE_RATIO` 시 **전원 food labor** 배치
   - food 생산 증폭: `produced *= (1 + communal_farms × COMMUNAL_FARM_BOOST)` (food 만 적용)
   - 비farmer food labor 패널티: `produced_adjusted = produced × FOOD_LABOR_NON_FARMER_RATIO` (farmer 제외)
   - skip reason 이벤트 발행: no_candidates / budget_insufficient / rate_below_min / signal_stale

4. `_process_food_reserve` 에 food_crisis_counter 증가 로직
   - NPC 매수 실행 시 `territory.food_crisis_counter += 1`
   - NPC 매수 없이 충족된 사이클 시 `territory.food_crisis_counter = max(0, counter - 1)` (자연 감소)

5. 신규 메서드 `_process_farm_expansion(territory_id)`:
   - `counter >= FOOD_CRISIS_FARM_THRESHOLD AND treasury_gold >= FARM_EXPANSION_COST_GOLD` 일 때 발동
   - `treasury_gold -= COST`, `communal_farms += 1`, `counter = 0`, 이벤트 발행
   - `_process_food_reserve` 뒤 또는 `_auto_economy_tick` 내에서 호출 (24틱 주기)

6. `ontology/__init__.py` 신규 상수 7개 export

7. `test_phase16e_agriculture.py` 신규 **8 tests**

8. `observe_phase15_stack.py` Phase 16-E 섹션 추가
   - skip_reason 분해 (no_candidates / budget_insufficient / rate_below_min)
   - food_crisis_active 이벤트 수
   - communal_farms 최종값 (영지별)
   - farm_expansion 이벤트 수

9. 합격 기준: §검증 섹션의 "기능 검증 (2000틱 Hard)" 표 + "기계 검증" + "계약 검증" 전부 통과. **단일 소스 원칙** — 중복 나열 금지, 기준은 §검증에만 명시.

### [선택]

- Hard 실패 시 본 지시서 §9 Phase 16-F 대안표 기록만. **자가 튜닝 금지**.
- 관측 스크립트에 farm_expansion 타임라인 (ASCII, 선택).

### [금지]

- 새 PersonaBrain 뉴런·SNN 축 추가
- 페르소나 행동 override (예: `persona.next_action = "work"` 직접 세팅 금지)
- 직접 gold 주입 (`wallet.receive(X)` 의 non-economic gift 금지)
- `persona.employment_id` 를 public works 내부에서 변경 (정규 Job lifecycle 과 충돌)
- NPC food 매수 완전 제거 (여전히 최후 안전망)
- food 자동 생성 (staffing 없는 공장형 생성 금지 — communal_farms 는 어디까지나 **multiplier**)
- Phase 12~15 상수 재튜닝 (`JOB_BASE_OUTPUT`, tax rate, `snlt_gold_per_tick` 등)
- Phase 16-B/C/D 핵심 상수 값 변경 (`PUBLIC_WORKS_BASE_ACTIVATION`, `NPC_FOOD_PURCHASE_COOLDOWN_TICKS`, `FOOD_STOCKPILE_RESERVE_PER_PERSONA`, `NPC_FOOD_TRIGGER_RESERVE_RATIO`, `PERSONA_FOOD_SAFE_STOCK`, `PUBLIC_WORKS_RATE_MIN`, `INTERNAL_FOOD_PRICE_RATIO`, `HUNGER_PRESSURE_WEIGHT`, `PUBLIC_WORKS_FARMER_BIAS`, `HUNGER_TRIGGER_THRESHOLD`, `PUBLIC_WORKS_IN_KIND_RATIO`, `STALE_SIGNAL_TICKS`)
- `_process_internal_food_procurement` / `_calc_hunger_pressure` / `_weighted_sample_without_replacement` 로직 변경
- 시설 종류 분화 (granary/irrigation/seed_stock/mill 등) — Phase 17+ 에서 다룬다

---

## 프레임워크·프로젝트 제약

- Python 3.x, numpy. 추가 패키지 금지.
- `MultiTickEngine` 은 `Projects/personas/loom/core/multi_tick_engine.py`.
- `self.rng` (Python `random.Random`) 와 `self._np_rng` (numpy Generator) 는 Phase 16-C 에서 이미 추가됨 — 재정의 금지. 모든 신규 샘플링은 이 둘 중 하나 사용.
- `np.random.default_rng(seed + offset)` 패턴 유지 (이미 결정적).
- Territory dataclass 는 `Projects/personas/loom/ontology/layers.py:116` 근처. 신규 필드는 기존 필드(Phase 16-D 의 `last_npc_food_purchase_tick` 바로 뒤) 뒤에 추가.
- 파일 >500 LOC 는 offset/limit 청크 읽기. 3회 편집마다 검증 읽기.
- 모든 신규 상수는 `ontology/layers.py` + `ontology/__init__.py` 양쪽에 추가.
- `consecutive_hunger_ticks` 는 InnerWorld 에 이미 존재 (Phase 11).

---

## 변경 파일

| 파일 | 작업 | 유형 |
|---|---|:---:|
| `Projects/personas/loom/ontology/layers.py` | 신규 상수 8개 + Territory 필드 2개 | 수정 |
| `Projects/personas/loom/ontology/__init__.py` | 신규 상수 8개 export | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | `_process_public_works` 확장 + `_process_food_reserve` counter 로직 + `_process_farm_expansion` 신규 + `_auto_economy_tick` 내 호출 + import 추가 | 수정 |
| `Projects/personas/loom/observe_phase15_stack.py` | Phase 16-E 섹션 추가 | 수정 |
| `Projects/personas/loom/test_phase16e_agriculture.py` | 8 tests 신규 | 추가 |

**변경 없음 (금지):**

- `Projects/personas/loom/brain/*.py`
- `Projects/personas/loom/test_phase16_public_works.py`, `test_phase16c_internal_food_market.py`, `test_phase16d_dynamic_reserve.py` — 회귀 보호
- `Projects/personas/loom/core/tick_engine.py` — 레거시
- `packages/launcher/**`
- Phase 12~15 상수 블록, Phase 16-B/C/D 상수 블록 (값 변경 금지)

---

## 구체 사양

### § 1. 상수 (`ontology/layers.py`)

**위치**: Phase 16-D 상수 블록 바로 뒤.

```python
# ── Phase 16-E: Public Works 후보 확장 + Food Crisis Mode + 초기 농장 ────
PUBLIC_WORKS_LOW_GOLD_THRESHOLD: float = 300.0
"""공공근로 임시 후보 편입 — wallet.gold 가 이 값 미만일 때 저소득으로 간주."""

PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD: int = 12
"""공공근로 임시 후보 편입 — consecutive_hunger_ticks 가 이 값 이상일 때 굶주림으로 간주."""

FOOD_LABOR_NON_FARMER_RATIO: float = 0.7
"""Food crisis mode 에서 비farmer 의 food 생산 계수 (farmer 대비 70%)."""

COMMUNAL_FARM_BOOST: float = 0.3
"""Communal farm 1개당 food 생산 증폭 비율. produced *= (1 + farms × 0.3)."""

FOOD_CRISIS_FARM_THRESHOLD: float = 3.0
"""food_crisis_counter 가 이 값 이상일 때 영주가 자동으로 farm 확장 건설을 시도 (float — counter 가 비대칭 감소)."""

FARM_EXPANSION_COST_GOLD: float = 500.0
"""Farm 1개 확장 비용 — treasury_gold 에서 차감."""

FOOD_CRISIS_RESERVE_RATIO: float = 0.4
"""Food crisis mode 발동 threshold — reserve < reserve_target × 이 값 + hunger 조건."""

FOOD_CRISIS_COUNTER_DECAY: float = 0.5
"""NPC 무매수 사이클당 food_crisis_counter 감소량 — +1/-0.5 비대칭 설계."""
```

### § 2. Territory 필드 (`ontology/layers.py`)

**위치**: `Territory` dataclass 의 Phase 16-D 필드 (`last_npc_food_purchase_tick: int = -9999`) 바로 뒤.

```python
    last_npc_food_purchase_tick: int = -9999     # Phase 16-D (기존)
    communal_farms: int = 1                       # Phase 16-E (신규)
    food_crisis_counter: float = 0.0              # Phase 16-E (신규, float — 비대칭 감소)
```

### § 3. `ontology/__init__.py` export

**주의**: 아래 코드 블록의 `...,` 는 Markdown 의 **기존 import·export 생략 표시** 이지 Python `Ellipsis` 리터럴이 아니다. 실제 파일 편집 시 **기존 import/export 행은 유지**하고 "Phase 16-E" 주석 이하 8개 행만 기존 블록 끝에 추가한다. `...` 문자를 그대로 파일에 복사하지 말 것.

```python
from .layers import (
    # (기존 import 전부 유지)
    # Phase 16-E 추가:
    PUBLIC_WORKS_LOW_GOLD_THRESHOLD,
    PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD,
    FOOD_LABOR_NON_FARMER_RATIO,
    COMMUNAL_FARM_BOOST,
    FOOD_CRISIS_FARM_THRESHOLD,
    FARM_EXPANSION_COST_GOLD,
    FOOD_CRISIS_RESERVE_RATIO,
    FOOD_CRISIS_COUNTER_DECAY,
)

__all__ = [
    # (기존 export 전부 유지)
    # Phase 16-E 추가:
    "PUBLIC_WORKS_LOW_GOLD_THRESHOLD",
    "PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD",
    "FOOD_LABOR_NON_FARMER_RATIO",
    "COMMUNAL_FARM_BOOST",
    "FOOD_CRISIS_FARM_THRESHOLD",
    "FARM_EXPANSION_COST_GOLD",
    "FOOD_CRISIS_RESERVE_RATIO",
    "FOOD_CRISIS_COUNTER_DECAY",
]
```

### § 4. `_process_public_works` 확장 (`multi_tick_engine.py:2645`)

**전체 재작성**. 기존 시그니처 유지.

```python
def _process_public_works(self, territory_id: str) -> list[dict]:
    """Phase 16-B/C/D/E: SNN-driven public employment + productive output.

    Phase 16-E 확장:
    - 후보 풀: unemployed OR (low_gold AND hungry)
    - Food crisis mode: hunger >= HUNGER_TRIGGER_THRESHOLD AND reserve < target * FOOD_CRISIS_RESERVE_RATIO
      → 전원 food labor 배치, 비farmer produced *= FOOD_LABOR_NON_FARMER_RATIO
    - food 생산 증폭: produced_food *= (1 + communal_farms * COMMUNAL_FARM_BOOST)
    - skip reason 이벤트 발행 (관측용)
    """
    territory = self.territories.get(territory_id)
    if not territory:
        return []
    if territory.treasury_gold < PUBLIC_WORKS_MIN_TREASURY:
        return [{
            "type": "public_works_skip_reason",
            "territory": territory_id,
            "reason": "budget_insufficient",
            "detail": "below_min_treasury",
        }]

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
    hunger = self._calc_hunger_pressure(territory_id)
    signal_component = (
        growth * 0.5
        + tension * 0.3
        + stability * 0.15
        + hunger * HUNGER_PRESSURE_WEIGHT
    )
    rate = min(0.8, max(0.0, PUBLIC_WORKS_BASE_ACTIVATION + signal_component))
    territory.policy.public_works_rate = rate
    if rate < PUBLIC_WORKS_RATE_MIN:
        return [{
            "type": "public_works_skip_reason",
            "territory": territory_id,
            "reason": "rate_below_min",
            "rate": round(rate, 4),
        }]

    wage_per_person = PUBLIC_WORKS_WAGE_PER_TICK * PUBLIC_WORKS_DURATION
    qincome = float(getattr(territory, "quarter_tax_income", 0.0))
    cap_income = (
        qincome * QUARTER_TAX_BUDGET_MULTIPLIER
        if qincome > 0 else float("inf")
    )
    cap_treasury = territory.treasury_gold * PUBLIC_WORKS_MAX_TREASURY_RATIO
    budget_cap = min(cap_income, cap_treasury)
    if budget_cap < wage_per_person:
        return [{
            "type": "public_works_skip_reason",
            "territory": territory_id,
            "reason": "budget_insufficient",
            "budget_cap": round(budget_cap, 1),
            "wage_required": wage_per_person,
        }]

    lord_id = getattr(territory, "lord_id", None)

    # Phase 16-E: 후보 풀 확장
    # 기존: employment_id is None 만
    # 추가: (wallet.gold < LOW_GOLD) AND (consecutive_hunger_ticks >= HUNGRY_TICKS)
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
        return [{
            "type": "public_works_skip_reason",
            "territory": territory_id,
            "reason": "no_candidates",
            "unemployed": 0,
            "low_gold_hungry": 0,
        }]

    # Food crisis mode 판정
    reserve = float(getattr(territory, "food_reserve", 0.0))
    residents_count = sum(
        1 for p in self.personas.values() if p.territory == territory_id
    )
    reserve_target = residents_count * FOOD_STOCKPILE_RESERVE_PER_PERSONA
    food_crisis_active = (
        hunger >= HUNGER_TRIGGER_THRESHOLD
        and reserve < reserve_target * FOOD_CRISIS_RESERVE_RATIO
    )

    n_hire = max(1, int(rate * len(candidates)))
    max_affordable = int(budget_cap // wage_per_person)
    n_hire = min(n_hire, max_affordable, len(candidates))
    if n_hire <= 0:
        return [{
            "type": "public_works_skip_reason",
            "territory": territory_id,
            "reason": "no_candidates",
            "detail": "n_hire_zero",
        }]

    # 선발: farmer_bias_active (기존 Phase 16-C) 유지하되 확장 후보 풀 대상
    farmer_bias_active = hunger >= HUNGER_TRIGGER_THRESHOLD
    if farmer_bias_active:
        weights = [
            PUBLIC_WORKS_FARMER_BIAS
            if (self._get_persona_job_title(pid) or "") == "farmer"
            else 1.0
            for pid in candidates
        ]
        chosen = self._weighted_sample_without_replacement(candidates, weights, n_hire)
    else:
        chosen = self.rng.sample(candidates, n_hire)

    events: list[dict] = []
    for pid in chosen:
        if territory.treasury_gold < wage_per_person:
            break
        job_title = self._get_persona_job_title(pid) or "laborer"

        # Phase 16-E: food crisis mode 에서는 전원 food labor 로 배치
        if food_crisis_active:
            produced_type = "food"
            base_output = JOB_BASE_OUTPUT.get("farmer", 2.0)
            if job_title != "farmer":
                base_output *= FOOD_LABOR_NON_FARMER_RATIO
        else:
            produced_type = JOB_OUTPUT_MAP.get(job_title, "material")
            base_output = JOB_BASE_OUTPUT.get(job_title, 0.5)

        produced = base_output * PUBLIC_WORKS_DURATION

        # Phase 16-E: communal_farm 증폭 (food 만)
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
        inner = self.inners[pid]
        inner.inventory[produced_type] = inner.inventory.get(produced_type, 0.0) + to_persona

        was_employed_elsewhere = (
            self.personas[pid].employment_id is not None
        )
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
            "hunger_pressure": round(hunger, 3),
            "farmer_bias_active": farmer_bias_active,
            "food_crisis_active": food_crisis_active,                # Phase 16-E
            "from_pool": "low_gold_hungry" if was_employed_elsewhere else "unemployed",  # Phase 16-E
            "communal_farms": territory.communal_farms,              # Phase 16-E
            "farm_multiplier": round(farm_multiplier, 3),            # Phase 16-E
            "base_component": round(PUBLIC_WORKS_BASE_ACTIVATION, 3),
            "signal_component": round(signal_component, 3),
            "produced_type": produced_type,
            "produced_total": round(produced, 2),
            "in_kind_to_territory": round(in_kind, 2),
            "to_persona": round(to_persona, 2),
            "treasury_after": round(territory.treasury_gold, 1),
            "signal_age": sig_age,
        })
    return events
```

**중요 — import 추가** (파일 상단 `from ontology.layers import (...)` 블록). **기존 import 행은 그대로 유지**하고 블록 끝에 Phase 16-E 8개 행을 추가. `...` 는 Python 리터럴이 아닌 기존 import 생략 표시:

```python
from ontology.layers import (
    # (기존 import 전부 유지)
    # Phase 16-E 추가:
    PUBLIC_WORKS_LOW_GOLD_THRESHOLD,
    PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD,
    FOOD_LABOR_NON_FARMER_RATIO,
    COMMUNAL_FARM_BOOST,
    FOOD_CRISIS_FARM_THRESHOLD,
    FARM_EXPANSION_COST_GOLD,
    FOOD_CRISIS_RESERVE_RATIO,
    FOOD_CRISIS_COUNTER_DECAY,
)
```

### § 5. `_process_food_reserve` counter 증가/감소 로직

**Phase 16-D 현재 구조** ([multi_tick_engine.py:1345-1488](./core/multi_tick_engine.py#L1345-L1488)):

```python
def _process_food_reserve(self) -> list[dict]:
    if self.time.tick % 24 != 0:
        return []
    events = []
    for tid, territory in self.territories.items():            # ← line 1351: 영지별 for 루프
        lord_id = territory.lord_id
        if not lord_id or lord_id not in self.personas:
            continue                                            # continue 분기들 (line 1354, 1358, 1362)
        # (lord_inventory transfer: line 1364-1380)
        # (internal procurement: line 1383-1403)
        # (NPC 매수: line 1417-1456)  ← treasury_purchase 이벤트 발행
        for pid in residents:                                   # ← line 1470: 배급 루프
            # ration 처리
    return events                                               # ← line 1488
```

§5-A, §5-B 모두 **영지 for 루프 내부** 에 삽입. **기존 로직 삭제 금지, 추가만**.

#### 5-A. NPC 매수 성공 지점 (line 1456 `})` 직후, treasury_purchase 이벤트 append 블록 바로 뒤)

기존 Phase 16-D 블록:

```python
# multi_tick_engine.py:1443-1456 (기존)
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
territory.food_crisis_counter += 1.0     # Phase 16-E 추가: NPC 의존 사이클 누적 (+1.0 float)
```

#### 5-B. 영지 iteration 말미 (line 1486 배급 루프 직후, 각 영지 iteration 끝)

영지별 독립 처리이므로 `events` 체크는 **현재 영지 이번 호출분만** 필터해야 한다. 영지 iteration 시작에 `start_idx = len(events)` 앵커를 저장 → iteration 끝에서 `events[start_idx:]` 로 해당 영지 이벤트만 필터.

**Before** (Phase 16-D, [multi_tick_engine.py:1351-1488](./core/multi_tick_engine.py#L1351-L1488) 발췌):

```python
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
    # (lord_inventory transfer, internal, NPC 매수)
    for pid in residents:
        if pid == lord_id:
            continue
        # ration 처리
return events
```

**After** (Phase 16-E 추가분 표시):

```python
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
    start_idx = len(events)                                        # ← Phase 16-E 추가
    # (lord_inventory transfer, internal, NPC 매수 — 기존 유지, §5-A 의 counter += 1.0 포함)
    for pid in residents:
        if pid == lord_id:
            continue
        # ration 처리
    # ↓ Phase 16-E 추가: 영지 iteration 끝에서 NPC 무매수 시 counter 비대칭 감소
    npc_buy_happened = any(
        e.get("type") == "food_stockpile"
        and e.get("source") == "treasury_purchase"
        for e in events[start_idx:]
    )
    if not npc_buy_happened:
        territory.food_crisis_counter = max(
            0.0, territory.food_crisis_counter - FOOD_CRISIS_COUNTER_DECAY
        )
return events
```

**주의**:
1. `continue` 분기 (lord 없음/sleeping/residents 비어있음) 는 `start_idx` 할당 **이전** 이므로 영향 없음.
2. 영지별 **독립** 필터: `e.get("territory") == tid` 조건은 불필요 (slice 가 이미 영지 단위).
3. `FOOD_CRISIS_COUNTER_DECAY = 0.5` 비대칭 — NPC 매수 +1.0 vs 무매수 -0.5 (§[필수 1] 비대칭 근거 참조).

### § 6. 신규 메서드 `_process_farm_expansion`

**위치**: `_process_food_reserve` 바로 뒤.

```python
def _process_farm_expansion(self) -> list[dict]:
    """Phase 16-E: food_crisis_counter >= threshold 시 farm 자동 확장.

    발동 조건:
    - territory.food_crisis_counter >= FOOD_CRISIS_FARM_THRESHOLD
    - territory.treasury_gold >= FARM_EXPANSION_COST_GOLD

    효과:
    - treasury_gold -= FARM_EXPANSION_COST_GOLD
    - communal_farms += 1
    - food_crisis_counter = 0 (반복 발동 방지)
    """
    if self.time.tick % 24 != 0:
        return []

    events: list[dict] = []
    for tid, territory in self.territories.items():
        if territory.food_crisis_counter < FOOD_CRISIS_FARM_THRESHOLD:
            continue
        if territory.treasury_gold < FARM_EXPANSION_COST_GOLD:
            events.append({
                "type": "farm_expansion_skip",
                "tick": self.time.tick,              # Phase 16-E: 관측 타임라인용
                "territory": tid,
                "reason": "treasury_insufficient",
                "required": FARM_EXPANSION_COST_GOLD,
                "have": round(territory.treasury_gold, 1),
            })
            continue

        territory.treasury_gold -= FARM_EXPANSION_COST_GOLD
        territory.communal_farms += 1
        territory.food_crisis_counter = 0.0         # float 로 리셋
        events.append({
            "type": "farm_expansion",
            "tick": self.time.tick,                  # Phase 16-E: 관측 타임라인용
            "territory": tid,
            "cost": FARM_EXPANSION_COST_GOLD,
            "communal_farms_after": territory.communal_farms,
            "treasury_after": round(territory.treasury_gold, 1),
        })

    return events
```

### § 7. `_auto_economy_tick` 에 `_process_farm_expansion` 호출

**위치**: `_auto_economy_tick` 내, `_process_food_reserve()` 호출 **바로 뒤**.

```python
# 기존
events.extend(self._process_food_reserve())

# Phase 16-E: farm 확장 체크 (food_reserve 내 counter 증감 후)
events.extend(self._process_farm_expansion())
```

`_auto_economy_tick` 의 정확한 위치는 `grep "_process_food_reserve"` 로 확인. (이미 [multi_tick_engine.py:1085](./core/multi_tick_engine.py#L1085) 근처 확인됨: `events.extend(self._process_food_reserve())` — 이 줄 뒤에 삽입.)

### § 8. 관측 스크립트 확장 (`observe_phase15_stack.py`)

기존 Phase 16-D 섹션 뒤에 추가.

```python
# ── Phase 16-E: 후보 확장 + Food Crisis + Farm Expansion ────
print("\n=== Phase 16-E observations ===")

# skip reason 분해
skip_events = [e for e in events if e.get("type") == "public_works_skip_reason"]
skip_counts: dict[str, int] = {}
for e in skip_events:
    reason = e.get("reason", "unknown")
    skip_counts[reason] = skip_counts.get(reason, 0) + 1
print(f"public_works skip reasons: {dict(sorted(skip_counts.items()))}")

# food crisis active 이벤트 수
pw_events = [e for e in events if e.get("type") == "public_works"]
food_crisis_pw = [e for e in pw_events if e.get("food_crisis_active")]
print(f"public_works in food_crisis_active mode: {len(food_crisis_pw)}")

# from_pool 분해
pool_counts: dict[str, int] = {}
for e in pw_events:
    pool = e.get("from_pool", "unknown")
    pool_counts[pool] = pool_counts.get(pool, 0) + 1
print(f"public_works from_pool: {dict(sorted(pool_counts.items()))}")

# farm_expansion 이벤트
farm_events = [e for e in events if e.get("type") == "farm_expansion"]
print(f"farm_expansion events: {len(farm_events)}")
for e in farm_events:
    print(f"  tick={e.get('tick', '?')} territory={e['territory']} farms={e['communal_farms_after']}")

# communal_farms 최종값
# engine state 기반 — 호출자가 engine 변수를 알면
# 아래는 events 에서 유추 (마지막 farm_expansion event 의 communal_farms_after 값)
final_farms: dict[str, int] = {}
for e in farm_events:
    final_farms[e["territory"]] = e["communal_farms_after"]
print(f"final communal_farms per territory: {final_farms or '(no expansions, defaults=1)'}")
```

**주의**: `events` 에 `tick` 필드가 자동 기록되지 않으면 "tick=?" 출력. 핵심 집계는 tick 무관이므로 OK.

### § 9. 신규 테스트 (`test_phase16e_agriculture.py`)

```python
"""Phase 16-E tests: Public Works 후보 확장 + Food Crisis Mode + 초기 농장."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.multi_tick_engine import MultiTickEngine
from ontology import (
    PUBLIC_WORKS_LOW_GOLD_THRESHOLD,
    PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD,
    FOOD_LABOR_NON_FARMER_RATIO,
    COMMUNAL_FARM_BOOST,
    FOOD_CRISIS_FARM_THRESHOLD,
    FARM_EXPANSION_COST_GOLD,
    FOOD_CRISIS_RESERVE_RATIO,
    FOOD_CRISIS_COUNTER_DECAY,
)


def test_constants_phase16e():
    assert PUBLIC_WORKS_LOW_GOLD_THRESHOLD == 300.0
    assert PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD == 12
    assert FOOD_LABOR_NON_FARMER_RATIO == 0.7
    assert COMMUNAL_FARM_BOOST == 0.3
    assert FOOD_CRISIS_FARM_THRESHOLD == 3.0
    assert FARM_EXPANSION_COST_GOLD == 500.0
    assert FOOD_CRISIS_RESERVE_RATIO == 0.4
    assert FOOD_CRISIS_COUNTER_DECAY == 0.5


def test_territory_has_farm_fields():
    engine = MultiTickEngine(seed=42)
    for tid, territory in engine.territories.items():
        assert hasattr(territory, "communal_farms")
        assert territory.communal_farms == 1
        assert hasattr(territory, "food_crisis_counter")
        assert territory.food_crisis_counter == 0.0


def test_low_gold_hungry_eligible_for_public_works():
    """§4: employment_id 가 있어도 wallet.gold < 300 AND hunger_ticks >= 12 시 후보 편입.

    주의: §4 구현은 policy.public_works_rate 를 SNN signals 기반으로 재계산하여 덮어쓴다.
    따라서 rate 는 SNN signals 로만 조절하고 policy.public_works_rate 직접 세팅은 금지.
    """
    engine = MultiTickEngine(seed=42)
    pid = next(iter(engine.personas))
    persona = engine.personas[pid]
    persona.employment_id = "dummy_emp"  # 정규 고용 중
    engine.wallets[pid].gold = 100.0      # 저소득
    engine.inners[pid].consecutive_hunger_ticks = 20  # 굶주림
    # SNN signal 세팅 (rate 재계산: 0.04 + 0.3*0.5 + 0.2*0.3 + 0.1*0.15 + hunger*weight ≈ 0.26+ ≥ RATE_MIN 0.03)
    tid = persona.territory
    territory = engine.territories[tid]
    territory.last_snn_signals = {"growth": 0.3, "tension": 0.2, "stability": 0.1}
    territory.last_snn_signals_tick = engine.time.tick
    territory.treasury_gold = max(territory.treasury_gold, 5000.0)

    events = engine._process_public_works(tid)
    pw = [e for e in events if e.get("type") == "public_works"]
    # 유일한 저소득+굶주림 후보가 선발되었어야 함
    assert any(e["persona"] == pid and e.get("from_pool") == "low_gold_hungry" for e in pw), (
        f"low_gold_hungry 후보 편입 실패: {events}"
    )


def test_food_crisis_mode_produces_food_only():
    """§4: food crisis active 시 모든 공공근로 produced_type == 'food'."""
    engine = MultiTickEngine(seed=42)
    tid, territory = next(iter(engine.territories.items()))
    territory.last_snn_signals = {"growth": 0.2, "tension": 0.5, "stability": 0.1}
    territory.last_snn_signals_tick = engine.time.tick
    territory.treasury_gold = 10000.0
    # hunger 강제 유도: 모든 주민 consecutive_hunger_ticks 상승
    for pid, persona in engine.personas.items():
        if persona.territory == tid:
            engine.inners[pid].consecutive_hunger_ticks = 50
    # reserve 를 target * 0.2 수준으로 낮춤
    residents = [p for p in engine.personas.values() if p.territory == tid]
    territory.food_reserve = len(residents) * 14.0 * 0.2

    events = engine._process_public_works(tid)
    pw = [e for e in events if e.get("type") == "public_works"]
    assert len(pw) >= 2, f"food_crisis 모드 발동 시 n_hire>=2 기대, 실제 {len(pw)}건: {events}"
    for e in pw:
        assert e["produced_type"] == "food", f"food_crisis 모드에서 non-food 생산: {e}"
        assert e["food_crisis_active"] is True


def test_non_farmer_food_labor_penalty():
    """§4: food crisis mode + non-farmer → produced <= farmer 출력 × FOOD_LABOR_NON_FARMER_RATIO × farm_multiplier × duration."""
    engine = MultiTickEngine(seed=42)
    tid, territory = next(iter(engine.territories.items()))
    territory.last_snn_signals = {"growth": 0.2, "tension": 0.5, "stability": 0.1}
    territory.last_snn_signals_tick = engine.time.tick
    territory.treasury_gold = 10000.0
    for pid, persona in engine.personas.items():
        if persona.territory == tid:
            engine.inners[pid].consecutive_hunger_ticks = 50
    residents = [p for p in engine.personas.values() if p.territory == tid]
    territory.food_reserve = len(residents) * 14.0 * 0.2

    events = engine._process_public_works(tid)
    pw = [e for e in events if e.get("type") == "public_works"]
    for e in pw:
        farms = e["communal_farms"]
        mult = 1.0 + farms * 0.3
        # farmer 기준 최대 생산량 (duration 24)
        max_farmer = 2.0 * 24 * mult
        # 비farmer 는 0.7 배
        max_nonfarmer = max_farmer * 0.7
        assert e["produced_total"] <= max_farmer + 0.01
        # 반드시 한 패턴에 속해야 함 (farmer 또는 non-farmer)
        assert (
            abs(e["produced_total"] - max_farmer) < 0.01
            or e["produced_total"] <= max_nonfarmer + 0.01
        )


def test_communal_farm_boost_applied():
    """§4: food 생산 시 produced == base_output × 24 × (1 + farms × 0.3)."""
    engine = MultiTickEngine(seed=42)
    tid, territory = next(iter(engine.territories.items()))
    territory.communal_farms = 2  # 강제로 2개
    territory.last_snn_signals = {"growth": 0.2, "tension": 0.5, "stability": 0.1}
    territory.last_snn_signals_tick = engine.time.tick
    territory.treasury_gold = 10000.0
    for pid, persona in engine.personas.items():
        if persona.territory == tid:
            engine.inners[pid].consecutive_hunger_ticks = 50
    residents = [p for p in engine.personas.values() if p.territory == tid]
    territory.food_reserve = len(residents) * 14.0 * 0.2

    events = engine._process_public_works(tid)
    pw = [e for e in events if e.get("type") == "public_works" and e["produced_type"] == "food"]
    assert pw, "food 공공근로 이벤트 없음"
    for e in pw:
        expected_mult = 1.0 + 2 * 0.3  # 1.6
        assert abs(e["farm_multiplier"] - expected_mult) < 0.01


def test_farm_expansion_triggers_after_3_crises():
    """§6: food_crisis_counter >= FOOD_CRISIS_FARM_THRESHOLD(3.0) AND treasury >= 500 시 farm 확장.

    주의: engine.tick() 호출은 _process_food_reserve 의 §5-B 자연 감소를 유발해
    counter 를 떨어뜨릴 수 있으므로 tick 을 직접 세팅하고 counter 는 tick 세팅 이후에 설정.
    기존 Phase 16 테스트들의 `engine.time.tick = 24` 패턴 준수.
    """
    engine = MultiTickEngine(seed=42)
    engine.time.tick = 24                                # 직접 세팅, engine.tick() 호출 금지
    tid, territory = next(iter(engine.territories.items()))
    territory.treasury_gold = 1000.0
    territory.food_crisis_counter = 3.0                  # tick 세팅 이후에 counter 설정
    initial_farms = territory.communal_farms

    events = engine._process_farm_expansion()
    assert any(e["type"] == "farm_expansion" and e["territory"] == tid for e in events), events
    assert territory.communal_farms == initial_farms + 1
    assert territory.food_crisis_counter == 0.0
    assert territory.treasury_gold == 500.0  # 1000 - 500


def test_regression_deterministic_2_runs_500_ticks():
    def snapshot(seed: int):
        eng = MultiTickEngine(seed=seed)
        for _ in range(500):
            eng.tick()
        return {
            "total_gold": sum(w.gold for w in eng.wallets.values()),
            "total_treasury": sum(t.treasury_gold for t in eng.territories.values()),
            "total_food": sum(t.food_reserve for t in eng.territories.values()),
            "pw_count": sum(1 for e in eng.event_log if e.get("type") == "public_works"),
            "skip_count": sum(
                1 for e in eng.event_log if e.get("type") == "public_works_skip_reason"
            ),
            "ip_count": sum(
                1 for e in eng.event_log if e.get("type") == "internal_food_procurement"
            ),
            "farm_count": sum(
                1 for e in eng.event_log if e.get("type") == "farm_expansion"
            ),
        }
    a = snapshot(42)
    b = snapshot(42)
    for k in a:
        assert abs(a[k] - b[k]) < 1e-6, f"determinism broken on {k}: {a[k]} vs {b[k]}"


if __name__ == "__main__":
    import traceback
    tests = [
        test_constants_phase16e,
        test_territory_has_farm_fields,
        test_low_gold_hungry_eligible_for_public_works,
        test_food_crisis_mode_produces_food_only,
        test_non_farmer_food_labor_penalty,
        test_communal_farm_boost_applied,
        test_farm_expansion_triggers_after_3_crises,
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

### § 10. 에러 케이스 테이블

| 상황 | 기대 동작 | 검증 |
|---|---|---|
| treasury < `PUBLIC_WORKS_MIN_TREASURY` | `skip_reason=budget_insufficient, detail=below_min_treasury` | 이벤트 1건 |
| `signals_tick < 0` | `skip_reason=signal_stale, detail=never_computed` | |
| `sig_age > STALE_SIGNAL_TICKS` | `skip_reason=signal_stale, detail=sig_age=N` | |
| `rate < RATE_MIN` | `skip_reason=rate_below_min` | |
| `budget_cap < wage` | `skip_reason=budget_insufficient, budget_cap=..., wage_required=120` | |
| 후보 없음 (unemployed + low_gold_hungry 둘 다 0) | `skip_reason=no_candidates, unemployed=0, low_gold_hungry=0` | |
| `n_hire == 0` | `skip_reason=no_candidates, detail=n_hire_zero` | |
| food_crisis_active + non-farmer 선발 | `produced_type="food"`, `produced *= FOOD_LABOR_NON_FARMER_RATIO × farm_mult` | test_non_farmer_food_labor_penalty |
| food_crisis_active + farmer 선발 | `produced_type="food"`, `produced = 2.0 × 24 × farm_mult` | |
| farm 확장 시 treasury < 500 | `farm_expansion_skip` 이벤트, communal_farms 증가 안 함 | |
| counter < 3 | `_process_farm_expansion` 아무 이벤트 없음 | |

### § 11. 결정성 계약

- `self._np_rng` / `self.rng` Phase 16-C 초기화 그대로. 재정의 금지.
- Phase 16-E 신규 로직에 `random.random()` / `np.random.random()` 전역 호출 없음.
- `test_regression_deterministic_2_runs_500_ticks` 가 검증.

### § 12. 관측 출력 기대값 (2000틱)

```
=== Phase 16-E observations ===
public_works skip reasons: {'no_candidates': N1, 'budget_insufficient': N2, 'rate_below_min': N3, 'signal_stale': N4}
public_works in food_crisis_active mode: >= 12
public_works from_pool: {'unemployed': K1, 'low_gold_hungry': K2}  (K1+K2 >= 50)
farm_expansion events: 1~3 (2000틱 내 1회 이상 확장 기대)
farm_expansion_skip events: 0~2 (treasury < 500 상태에서만 발생, 보통 0)
final communal_farms per territory: {...: 2 or 3, ...}
```

### § 13. Phase 16-F 대안표 (Hard 실패 시 **기록만**)

| 미달 지표 | 1순위 대안 | 2순위 대안 |
|---|---|---|
| public_works < 50 | `PUBLIC_WORKS_LOW_GOLD_THRESHOLD` 300 → 500 (더 넓은 후보) | `PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD` 12 → 6 |
| persona gold < 6000 | `PUBLIC_WORKS_WAGE_PER_TICK` 상향 (Phase 16-B 상수 — 별도 승인) | 공공근로 duration 24→36 |
| NPC > 34 | `COMMUNAL_FARM_BOOST` 0.3 → 0.5 | `FOOD_CRISIS_RESERVE_RATIO` 0.4 → 0.6 |
| farm_expansion 0회 | `FOOD_CRISIS_FARM_THRESHOLD` 3.0 → 2.0 | `FOOD_CRISIS_COUNTER_DECAY` 0.5 → 0.25 (감소 더 느리게) |
| farm_expansion 과도 (4회+) | `FOOD_CRISIS_COUNTER_DECAY` 0.5 → 1.0 (대칭) | `FOOD_CRISIS_FARM_THRESHOLD` 3.0 → 4.0 |
| food_crisis mode 발동률 낮음 | `HUNGER_TRIGGER_THRESHOLD` 0.3 → 0.2 (Phase 16-C 상수 — 별도 승인) | `FOOD_CRISIS_RESERVE_RATIO` 0.4 → 0.5 |

---

## 검증

### 기계 검증 (항상)

```bash
py -m py_compile ontology/layers.py ontology/__init__.py core/multi_tick_engine.py observe_phase15_stack.py test_phase16e_agriculture.py
py test_phase16e_agriculture.py                 # 8/8 PASS
py test_phase16d_dynamic_reserve.py             # 7/7 PASS (회귀)
py test_phase16c_internal_food_market.py        # 7/7 PASS (회귀)
py test_phase16_public_works.py                 # 9/9 PASS (회귀)
py test_phase12b_perf_npc.py                    # 5/5 PASS (회귀)
py test_economy_balance.py                      # 6/6 PASS (회귀)
py test_economy.py                              # 6/6 PASS (회귀)
py test_nomos.py                                # PASS (회귀)
py test_class_promotion.py                      # PASS (회귀)
npm --prefix packages/launcher run typecheck    # PASS (회귀)
```

### 기능 검증 (2000틱 Hard)

```bash
py observe_phase15_stack.py
```

**5개 지표 전부 통과 필수**:

| 지표 | 기준 |
|---|---|
| persona gold final | ≥ 6000 |
| total_wealth loss | ≤ 40% |
| deaths | 0/10 |
| public_works events | ≥ 50 |
| NPC food_stockpile (source=treasury_purchase) | ≤ 34 |

### 계약 검증

- 결정성: `test_regression_deterministic_2_runs_500_ticks` 통과 (7개 key 모두 < 1e-6 차이)
- 호환성: 9개 테스트 파일 전부 PASS
- Import 안정성: `py -c "from ontology import PUBLIC_WORKS_LOW_GOLD_THRESHOLD, FOOD_LABOR_NON_FARMER_RATIO, COMMUNAL_FARM_BOOST, FOOD_CRISIS_FARM_THRESHOLD, FARM_EXPANSION_COST_GOLD, FOOD_CRISIS_RESERVE_RATIO, PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD, FOOD_CRISIS_COUNTER_DECAY; print('OK')"` → "OK"

---

## Rollback

```bash
cd Projects/personas/loom
git checkout HEAD -- ontology/layers.py ontology/__init__.py core/multi_tick_engine.py observe_phase15_stack.py
rm -f test_phase16e_agriculture.py
py test_phase16d_dynamic_reserve.py   # 회귀 확인
```

**데이터 영향**: 없음 (인메모리 시뮬).

---

## 실패 시 에스컬레이션 템플릿

Hard 1개 이상 미달 또는 회귀 실패 시 **파라미터 자가 튜닝 금지**. 다음 포맷으로 리뷰 리포트:

```markdown
# Phase 16-E 구현 리뷰 요청: <한 줄 요약>

## 구현 완료
- [변경 파일 + 요약]

## 테스트 결과
- [8 신규 + 7+7+9+5+6+6 회귀 요약]

## 2000틱 관측 결과
- [persona gold / public_works / NPC food_stockpile / total_wealth / deaths 표]
- [Phase 16-E 관측 섹션 그대로 붙여넣기]
- [skip reason 분해, from_pool 분해, farm_expansion 횟수]

## 가설 (왜 실패했나)
- [문제 축 A/B/C 중 어느 것이 약했나, 1~2문장씩]

## 요청
- Phase 16-F 설계 요청 또는 §13 대안 선택 요청
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
Projects/personas/loom/PHASE-16E-CODEX-INSTRUCTIONS.md 파일을 그대로 따라 구현하세요.

## 규칙 (절대 준수)
1. 지시서 [필수] 9개 항목 100% 구현. [금지] 10개 항목 절대 건드리지 말 것.
2. 지시서에 포함된 코드 블록은 **직접 복사**해서 반영. 해석·재작성 금지.
3. Phase 16-B/C/D 구조는 유지하며 이 지시서 지정 지점만 수정.
4. Phase 12~15 상수와 Phase 16-B/C/D 상수 값 절대 변경 금지.
5. 검증 순서:
   a. py -m py_compile <5개 파일>
   b. py test_phase16e_agriculture.py   → 8/8 PASS
   c. 회귀 테스트 전부 PASS
   d. npm --prefix packages/launcher run typecheck → PASS
   e. py observe_phase15_stack.py → Hard 5개 지표 확인
6. Hard 미달 시 **파라미터 자가 조정 금지**. §실패 에스컬레이션 템플릿대로 리뷰 리포트.
7. 보고:
   - 변경 파일 목록 + 각 변경 요약
   - 각 검증 단계 통과 여부
   - 2000틱 hard 지표 표
   - Phase 16-E 관측 섹션 출력 그대로
   - [선택] 항목 구현 여부
```

---

## 자체 검증 체크리스트 (작성자)

- [x] 메타 5종 (긴급도/선행/유형/migration/의존)
- [x] 배경 + 근본 원인 5단 + 3축 대응표 (근본 C → §B 간접 해결 매핑 포함) + 역산 목표
- [x] [필수 9 / 선택 2 / 금지 10]
- [x] 프레임워크 제약 섹션
- [x] 변경 파일 표 + 변경 없음 5개
- [x] §1~§13 구체 사양 (상수·필드·메서드 코드 블록)
- [x] 에러 케이스 테이블 (skip reason 4종 + food_crisis 2종 + farm_expansion 2종)
- [x] 결정성 계약 + test 포함
- [x] Rollback 명령
- [x] GPT 전달 프롬프트 템플릿
- [x] 실패 에스컬레이션 템플릿
- [x] Phase 16-F 대안표 (자가 튜닝 금지 명시)
- [x] 모호 표현 없음 (모든 숫자·조건·경로 명시)
- [x] 다른 skill 결과 (GPT Phase 16-E 리뷰) → 지시서 언어로 번역 완료 (14개 질문 중 핵심 3축만 채택)
- [x] **/spec-review 리포트 11건 반영** (Addendum — 아래 참조)

---

## Addendum — /spec-review 반영 내역 (2026-04-19)

`.claude/skills/spec-review` 로 수행한 검토 리포트 11건을 본 지시서에 반영 완료.

| # | Severity | 이슈 | 반영 위치 |
|---|---|---|---|
| 1 | CRITICAL | §5-B 구조 가정·앵커 부재 | §5 서두에 Phase 16-D `_process_food_reserve` 실제 코드 인용 + §5-B before/after diff 추가 |
| 2 | MAJOR | test_farm_expansion while 루프 부작용 | `engine.time.tick = 24` 직접 세팅, counter 설정을 tick 세팅 이후로 이동 |
| 3 | MAJOR | counter +1/-1 대칭 밸런스 미검증 | `FOOD_CRISIS_COUNTER_DECAY = 0.5` 비대칭 도입, [필수 1] 에 시나리오 근거 주석 |
| 4 | MAJOR | 근본원인 C 3축 미매핑 | 대응표 §B 행을 `B, C, D` 로 확장 + "전원 food 배치로 internal 대체" 명시 |
| 5 | MINOR | test_low_gold_hungry `policy.public_works_rate=0.2` redundant | 해당 라인 제거 + 코멘트로 "rate 는 SNN signals 로만 조절" 명시 |
| 6 | MINOR | Phase 16-D 구조 전제 불명 | CRITICAL 1 과 함께 §5 서두 코드 인용으로 해결 |
| 7 | MINOR | farm_expansion 이벤트 tick 필드 누락 | `_process_farm_expansion` 의 `farm_expansion` / `farm_expansion_skip` 이벤트에 `"tick": self.time.tick` 추가 |
| 8 | MINOR | [필수 9] 합격 기준과 §검증 중복 | [필수 9] 를 "§검증 참조" 단일 소스로 축소 |
| 9 | MINOR | import `...` placeholder Ellipsis 혼동 | § 3 및 § 4 import 블록 앞에 "`...` 는 생략 표시, Python 리터럴 아님" 경고 + 예시를 "기존 import 전부 유지" 주석으로 변경 |
| 10 | TRIVIA | test_food_crisis_mode assertion 약함 | `len(pw) >= 1` → `>= 2` 로 강화 + 실패 메시지 추가 |
| 11 | TRIVIA | §12 farm_expansion_skip 빈도 누락 | 관측 기대값에 "0~2 (treasury<500 상태에서만, 보통 0)" 행 추가 |

**부수 변경**:
- 상수 7개 → **8개** (FOOD_CRISIS_COUNTER_DECAY 추가)
- `food_crisis_counter` 타입 `int → float`, `FOOD_CRISIS_FARM_THRESHOLD` 타입 `int → float` (비대칭 감소 대응)
- 변경 파일 표·export 목록·테스트 assertion·Phase 16-F 대안표에 일관 반영
- [선택] 및 [금지] 범위는 미변경 — 자가 튜닝 금지 원칙 유지
