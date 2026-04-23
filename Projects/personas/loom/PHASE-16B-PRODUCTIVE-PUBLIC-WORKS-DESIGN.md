# Phase 16-B: Productive Public Works + NPC Outflow Control

## 배경

Phase 16 Public Works 구현 결과:
- public_works 이벤트 70건, 공공임금 8400 gold 지급
- persona gold: 20000 → 2757 (**-86.2%**), 목표 -70% 미달 (개선 +3%p)
- treasury 최종: seorim 463 / ironridge 498 / mirrordale 433 (MIN_TREASURY 500 경계)
- 사망 0, strike 13

**결론**: Public Works는 gold를 treasury → persona로 **순환**시키지만, 그 gold가 곧장 NPC 쪽으로 흘러나감. "밑 빠진 독에 물 붓기". 근본 원인은 **NPC outflow가 페르소나·영지의 생산성을 초과**한다는 점.

**근본 원인 재추적** (Claude.md 17조 "왜?" 반복):
1. gold 감소 → 왜? persona·treasury가 NPC로 지출
2. 왜 NPC로? → `food_stockpile` 매수 (treasury) + 긴급 식량 매수 (persona)
3. 왜 NPC에서 사나? → 영지 `food_reserve` 고갈 + persona inventory food 부족
4. 왜 food가 부족한가? → **페르소나가 생산한 food가 영지로 흐르는 경로 없음** (farmer의 food는 자기 소비만)
5. 근본: **생산자와 영지 공급망 단절** — 공공 고용이 "임금만" 주고 "생산 기여"를 안 받음

→ **Option A(Productive Public Works) + Option B(NPC Outflow Control) 하이브리드**가 올바른 방향.

---

## 결정 사항 (사용자 요청 5개)

### 1. `growth` 가중치: `0.7` formalize + stability 추가
```python
rate = min(0.8, max(0.0,
    growth * 0.6 + tension * 0.3 + stability * 0.1
))
```
- `growth` 주도는 유지하되 stability 10% 기여로 장기 안정 반영.
- 0.5는 너무 보수적, 0.7은 stability 무시. 합의안: **0.6 + 0.3 + 0.1**.

### 2. Phase 16-B 전략: **A+B 하이브리드**
- **A (Productive)**: 공공 고용된 페르소나는 본 직업대로 goods 생산. 생산량의 **50% (세율 `public_works_in_kind_ratio`)가 영지에 귀속** → `territory.food_reserve` / 영지 inventory 누적.
- **B (Outflow Control)**: `food_stockpile` 매수 조건 타이트화 — `territory.food_reserve < threshold` **AND** 영지 inventory food 부족 **AND** 시장에 food 매도 주문 없음일 때만 NPC 구매.

### 3. 합격 지표 재정의 (Option D 일부 수용)
Persona gold 단독 -70% 하드 타겟은 **유지하되**, 보조 지표 추가:
- **Total Wealth** = persona gold + treasury + goods value (food 10g, material 15g, tool 60g, medicine 30g, knowledge 45g = NPC buy price 기준)
- 하드 타겟 (both must pass):
  - persona gold ≥ -70% (= 6000 floor from 20000)
  - total wealth ≥ -40% (goods로 전환된 가치 반영)

### 4. Treasury 고갈 방지 강화
현행 MIN=500 + ratio=0.5 유지하고 추가:
- `quarter_tax_income` 추적 (분기 세수 누적)
- 공공지출 1 cycle 예산 ≤ `quarter_tax_income * 1.2`
- 초과 시 rate 자동 감소 (`rate *= budget_factor`)
- 세수 > 지출이면 영구 흑자, 과지출은 자동 제동 → 재정 규율 창발

### 5. Phase 16 테스트 (`test_phase16_public_works.py`)
9개 focused test. 아래 Step 5 참조.

---

## 변경 파일 (4개)

1. `Projects/personas/loom/ontology/layers.py`
   - 상수 추가: `PUBLIC_WORKS_IN_KIND_RATIO`, `STALE_SIGNAL_TICKS`, `FOOD_STOCKPILE_RESERVE_THRESHOLD`
   - `Territory.last_snn_signals_tick: int = -1` 추가
   - `Territory.inventory: dict` 추가 (공공 생산물 귀속)
   - `Territory.quarter_tax_income: float = 0.0` 추가 (없으면)
2. `Projects/personas/loom/core/multi_tick_engine.py`
   - `_process_public_works` 리팩토링 (A+B 로직)
   - `_update_governance_policy` — `last_snn_signals_tick` 저장, stale 가드
   - `_stockpile_food` (또는 해당 로직) 우선순위 수정 (B)
   - 공공 생산물 귀속 처리 (A)
3. `Projects/personas/loom/observe_phase15_stack.py`
   - `public_works_in_kind` 집계, total_wealth 계산·출력
4. `Projects/personas/loom/test_phase16_public_works.py` (신규)

---

## 구현 순서

### Step 1: 상수 + dataclass 필드 (`layers.py`)

```python
# ── Phase 16-B 추가 상수 ──
PUBLIC_WORKS_IN_KIND_RATIO: float = 0.5         # 공공 생산물 중 영지 귀속 비율
STALE_SIGNAL_TICKS: int = 72                    # SNN 신호 유효 기간 (3 cycles)
FOOD_STOCKPILE_RESERVE_THRESHOLD: float = 30.0  # 이 미만일 때만 NPC food_stockpile
```

`Territory`:
```python
    last_snn_signals_tick: int = -1   # stale 가드
    inventory: dict = field(default_factory=lambda: {
        "food": 0.0, "material": 0.0, "tool": 0.0, "medicine": 0.0, "knowledge": 0.0
    })  # 공공 생산물 누적
    # quarter_tax_income 기존에 있으면 재사용, 없으면 추가
```

### Step 2: `_process_public_works` 리팩토링 (A+B)

```python
def _process_public_works(self, territory_id: str) -> list[dict]:
    territory = self.territories.get(territory_id)
    if not territory or territory.treasury_gold < PUBLIC_WORKS_MIN_TREASURY:
        return []

    # Stale 가드 (리뷰 제안 1)
    sig_age = self.time.tick - territory.last_snn_signals_tick
    if territory.last_snn_signals_tick < 0 or sig_age > STALE_SIGNAL_TICKS:
        return []
    snn = territory.last_snn_signals or {}
    growth = float(snn.get("growth", 0.0))
    tension = float(snn.get("tension", 0.0))
    stability = float(snn.get("stability", 0.0))

    base_rate = min(0.8, max(0.0, growth * 0.6 + tension * 0.3 + stability * 0.1))

    # 예산 연동 (결정 4)
    wage_per_person = PUBLIC_WORKS_WAGE_PER_TICK * PUBLIC_WORKS_DURATION
    quarter_income = float(getattr(territory, "quarter_tax_income", 0.0))
    budget_cap_income = quarter_income * 1.2
    budget_cap_treasury = territory.treasury_gold * PUBLIC_WORKS_MAX_TREASURY_RATIO
    budget_cap = min(budget_cap_income, budget_cap_treasury) if quarter_income > 0 else budget_cap_treasury

    if budget_cap < wage_per_person:
        return []

    # 실업자 (리뷰 제안 3: lord 제외)
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

    rate = base_rate
    n_hire = max(1, int(rate * len(unemployed)))
    max_affordable = int(budget_cap // wage_per_person)
    n_hire = min(n_hire, max_affordable, len(unemployed))
    if n_hire <= 0:
        return []

    # Stable RNG (리뷰 제안 2)
    chosen = self.rng.sample(unemployed, n_hire)

    territory.policy.public_works_rate = rate
    events = []
    for pid in chosen:
        if territory.treasury_gold < wage_per_person:
            break
        persona = self.personas[pid]

        # A: Productive — 본 직업 산출 × DURATION × IN_KIND_RATIO = 영지 귀속
        job_title = self._get_persona_job_title(pid) or "laborer"
        goods_type = JOB_OUTPUT_MAP.get(job_title, "material")
        base_output = JOB_BASE_OUTPUT.get(job_title, 0.5)
        produced = base_output * PUBLIC_WORKS_DURATION
        in_kind = produced * PUBLIC_WORKS_IN_KIND_RATIO
        to_persona = produced - in_kind

        # 임금 지급
        territory.treasury_gold -= wage_per_person
        self.wallets[pid].receive(wage_per_person)

        # 생산물: 영지 귀속분 + 페르소나 보유분
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

### Step 3: `_update_governance_policy` — 시그널 + 타임스탬프

기존 policy 업데이트 말미:
```python
territory.last_snn_signals = {
    "growth": float(growth),
    "stability": float(stability),
    "tension": float(tension),
}
territory.last_snn_signals_tick = self.time.tick
```

### Step 4: NPC food_stockpile 매수 타이트화 (B)

기존 `_stockpile_food` 또는 해당 treasury → NPC 구매 분기 (multi_tick_engine.py:1363 부근):
```python
# 조건 강화: Phase 16-B
food_reserve = getattr(territory, "food_reserve", 0.0)
if food_reserve >= FOOD_STOCKPILE_RESERVE_THRESHOLD:
    continue  # 이미 충분 — NPC 매수 보류

# 시장에 food 매도 주문이 있으면 그걸 우선
has_market_food = any(
    o.goods_type == "food" and o.territory_id == territory_id
    for o in self.market_orders
)
if has_market_food:
    continue  # 시장 우선 — NPC 매수 보류
# 기존 로직 이어서...
```

### Step 5: 테스트 `test_phase16_public_works.py`

9개 test functions:
1. `test_snn_triggers_public_works` — growth=0.8 → public_works 이벤트 ≥ 1
2. `test_rate_threshold_suppression` — growth=0.0, tension=0.0 → 이벤트 0
3. `test_treasury_min_guard` — treasury=400 (< 500) → 이벤트 0
4. `test_budget_cap_enforced` — quarter_income=0, treasury * 0.5 < wage → 이벤트 0 또는 1명만
5. `test_unemployed_only_and_lord_excluded` — lord_id, employment_id 있는 pid 제외
6. `test_wallet_and_treasury_transfer` — wage_per_person 정확히 이동
7. `test_productive_in_kind_credit` — food/material/tool 각각 영지 귀속 정확
8. `test_stale_signal_suppressed` — last_snn_signals_tick 이 현재-73틱이면 skip
9. `test_stable_random_selection` — 두 번 시뮬 실행 시 동일 시드에서 동일 선택

픽스처: 경량 MultiTickEngine 초기화 + territory·persona mock. 2000틱 불필요.

### Step 6: 관측 스크립트 확장

`observe_phase15_stack.py`:
```python
in_kind_total = defaultdict(float)
for _, ev in public_works_events:
    gt = ev.get("produced_type", "?")
    in_kind_total[gt] += ev.get("in_kind_to_territory", 0)

# Total wealth (보조 지표)
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
```

출력 섹션:
```
Phase 16-B: Productive Public Works
─────────────────────────────────────
public_works events      : {count}
total wage paid          : {wage}
avg rate                  : {avg_rate}
in-kind goods to territory:
  food       : {in_kind_total[food]:.1f}
  material   : {in_kind_total[material]:.1f}
  ...
Total Wealth (gold + treasury + goods value)
  initial : {initial_wealth}
  final   : {final_wealth}
  delta   : {delta} ({pct}%)
```

---

## 2000틱 Acceptance Criteria

합격 (both hard + soft):
- **Hard**: persona gold 감소 ≤ **-70%** (= 최종 ≥ 6000)
- **Hard**: total_wealth 감소 ≤ **-40%**
- **Hard**: 사망 = 0
- **Soft**: public_works 이벤트 ≥ 50건
- **Soft**: territory food_reserve 최종 ≥ 20 (NPC 의존 완화 증거)
- **Soft**: food_stockpile 이벤트 ≤ 기존의 50% (Phase 16 기준 69건 → 34건 이하)
- **Regression**: test_nomos.py / test_class_promotion.py / test_economy_balance.py / test_phase12b_perf_npc.py PASS
- **Regression**: test_phase16_public_works.py 9/9 PASS

불합격 시 Phase 16-C fallback:
- persona gold < 6000 → `PUBLIC_WORKS_IN_KIND_RATIO` 0.5 → 0.3 (페르소나 몫 증가)
- treasury 고갈 → `PUBLIC_WORKS_WAGE_PER_TICK` 5.0 → 3.0
- food_stockpile 여전히 과다 → 영지가 시장에서 직접 food 매수 (P2P, 수수료만 소멸)

---

## 창발 포인트 (SNN 철학 유지)

| SNN 변화 | Public Works 반응 | 경제 효과 | 피드백 |
|---|---|---|---|
| `growth` ↑ | rate ↑ → 공공 고용 ↑ | food_reserve ↑, persona gold ↑ | hunger ↓ → `stability` ↑ → 다음 `growth` ↑ (양성) |
| `tension` ↑ | rate ↑ (긴급) | persona gold ↑ + in-kind food | grievance ↓ → strike ↓ → `tension` ↓ (자기조정) |
| `quarter_tax_income` 저조 | budget_cap 축소 → rate 자동 감소 | 공공지출 절제 | 세수 회복 대기 — 재정규율 창발 |
| `food_reserve` 충분 | NPC food_stockpile 보류 | treasury → NPC 유출 중단 | 무역수지 개선 |

**핵심 철학**:
- 규칙은 "공공 고용 rate = SNN 선형 합" + "예산 상한 = 분기세수 × 1.2"만 명시
- **얼마나, 언제, 누구를, 무엇을 생산**할지는 SNN과 기존 직업 시스템이 결정
- 하드코딩 없이 "gold가 늘도록" 강제하지 않음 — 생산성이 소비를 따라잡으면 자연히 순환

---

## Technical Review Findings 반영

| 이슈 | 해결 |
|---|---|
| 1. stale signals | `last_snn_signals_tick` + `STALE_SIGNAL_TICKS=72` 가드 |
| 2. hash 비결정성 | `self.rng.sample()` 사용 (엔진 rng 필수) |
| 3. 영주 포함 | `pid != lord_id` 제외 |
| 4. 테스트 부재 | `test_phase16_public_works.py` 9개 테스트 신규 |

---

## 다음 단계

1. 이 지시서 검토 승인
2. `/harness --evolve PHASE-16B-PRODUCTIVE-PUBLIC-WORKS-DESIGN.md 지시서대로 구현` 로 구현 루프 시작
3. 9/9 테스트 + 2000틱 관측 후 합격 여부 판정
4. 불합격 시 Phase 16-C fallback 조항 적용
