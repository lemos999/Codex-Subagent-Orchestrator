# Phase 13: 영주 통치 + 세금 + 식량 균형 — Codex 지시서

> **작성자**: Claude (설계/리뷰)
> **구현자**: Codex (코딩/검증)
> **선행 조건**: Phase 12-B APPROVE, 전 테스트 ALL PASS, ~140ms/tick
> **목표**: Layer 7(통치)의 첫 수직 단면. 영주가 세금을 걷고, 식량 정책을 세우고, 금고를 운영한다.

---

## 왜 이것이 다음인가 — 근본 원인 추적

Phase 11 RESEARCH-LOG 결론:
> "farmer 비율 증가, P2P 거래 활성화, 세금/통치 시스템"

**꼬리 추적**:
- "food 생산이 500틱에 5~7밖에 안 된다" → 왜? → farmer 일자리가 없다
- "farmer 일자리가 없다" → 왜? → 영주가 `avg_hunger > 0.5`일 때만 farmer 생성
- "0.5까지 배고파야 한다" → 왜? → 영주가 "예방" 개념이 없다 (위기 대응만)
- "P2P 거래가 적다" → 왜? → 모든 persona가 같은 직업군(laborer/craftsman)이라 교환할 재화가 없다
- "세금이 있는데 금고는 어디서 채우나?" → 이미 tax_rate 0.1 있지만, **세금 징수 로직이 없다**
- "통치는?" → 영주 ID만 지정, **의사결정/정책/법 집행 코드 0줄**

**근본**: Layer 7이 완전히 비어 있어서, Layer 6(경제)이 자기 피드백 없이 돌고 있다.

---

## 설계 원칙

### SNN 연결 (Phase 12 정신 계승)

영주도 페르소나다. 영주의 통치 행동은 **영주 뇌의 SNN 신호**에서 나와야 한다.
- 영주의 hunger/stress/urgency가 높으면 → 세금 인상, 식량 정책 강화
- 영주의 motivation이 높으면 → 비축 선호, 지출 억제
- 영주의 greed(oyok[3])가 높으면 → 금고 축적 성향

### Guide Rail

- 세율 범위: 0.05 ~ 0.30 (기아 방지/착취 방지)
- 금고 최소 유지: 500 gold (파산 방지)
- 식량 안전 재고: territory 주민 × 24 food (1일분)

---

## 변경 파일 (3파일)

1. `ontology/layers.py` — Territory 필드 추가, GovernancePolicy dataclass
2. `ontology/__init__.py` — export 추가
3. `core/multi_tick_engine.py` — 통치 로직 3개 메서드 + 기존 메서드 수정

---

## Step 1: 데이터 모델 (`ontology/layers.py`)

### 1-A. GovernancePolicy dataclass (Territory 클래스 앞, line 93 직전)

```python
@dataclass
class GovernancePolicy:
    """영주의 현재 통치 정책. SNN 신호에서 도출되어 매 24틱마다 갱신."""
    tax_rate: float = 0.10             # 소득세율 (0.05~0.30)
    food_priority: float = 0.5        # 식량 정책 강도 (0~1). 높으면 farmer 우선
    stockpile_target: float = 0.5     # 비축 성향 (0~1). 높으면 금고 지출 억제
    treasury_spending_cap: float = 0.3 # 분기 GDP 대비 최대 지출 비율
    last_updated_tick: int = 0
```

### 1-B. Territory 필드 추가 (line 110 뒤)

```python
    # ── 통치 정책 (Phase 13) ────────────────────────
    policy: GovernancePolicy = field(default_factory=GovernancePolicy)
    tax_collected_total: float = 0.0   # 누적 징수액
    food_reserve: float = 0.0          # 영지 식량 비축량
```

### 1-C. export (`__init__.py`)

`GovernancePolicy` 추가.

---

## Step 2: 세금 징수 (`multi_tick_engine.py`)

### 새 메서드: `_collect_taxes()` — 24틱마다 호출

```
위치: _auto_economy_tick() 내, market/npc/tool 처리 이전 (line 835 직전)
```

**로직**:

```python
def _collect_taxes(self) -> list[dict]:
    """영주가 세금을 징수한다. 24틱마다."""
    events = []
    for tid, territory in self.territories.items():
        lord_id = territory.lord_id
        if not lord_id or lord_id not in self.personas:
            continue
        
        lord_inner = self.inners[lord_id]
        if lord_inner.is_sleeping:
            continue
        
        # [SNN] 영주 뇌 상태에서 세율 조정
        # → Step 4에서 _update_governance_policy로 분리
        tax_rate = territory.policy.tax_rate
        
        residents = [
            pid for pid, p in self.personas.items()
            if p.territory == tid and pid != lord_id
        ]
        
        total_collected = 0.0
        for pid in residents:
            wallet = self.wallets.get(pid)
            if not wallet or wallet.gold < 10:  # 최소 소지금 보호
                continue
            
            # 소득세: 이전 24틱 동안의 수입 추정 (wallet.gold 변화분 대신 단순 비율)
            tax_amount = wallet.gold * tax_rate * (1/24)  # 일일 세율
            tax_amount = min(tax_amount, wallet.gold - 10)  # 최소 10 gold 보호
            tax_amount = max(0.0, tax_amount)
            
            if tax_amount > 0.1:
                wallet.pay(tax_amount)
                territory.treasury_gold += tax_amount
                territory.tax_collected_total += tax_amount
                total_collected += tax_amount
        
        if total_collected > 0:
            events.append({
                "type": "tax_collected",
                "territory": tid,
                "lord": lord_id,
                "amount": round(total_collected, 2),
                "tax_rate": round(tax_rate, 3),
                "treasury_after": round(territory.treasury_gold, 1),
                "residents_taxed": len(residents),
            })
    
    return events
```

> **SNN/Guide 레이블**:
> - tax_rate: **[SNN]** — Step 4에서 영주 뇌 신호로 결정
> - 최소 소지금 10 gold: **[Guide]** — 기아 방지 안전장치
> - 24틱 주기: **[Guide]** — 인프라 (매 틱 세금은 비현실적)

---

## Step 3: 식량 정책 (`multi_tick_engine.py`)

### 기존 메서드 수정: `_auto_economy_tick()` 직업 생성 로직

**문제**: farmer가 `avg_hunger > 0.5`일 때만 생성. 예방적 식량 정책 없음.

**변경**: 영주 정책의 `food_priority`를 직업 생성에 반영.

```
위치: line 717 farmer 조건 수정
```

**Before** (717~720):
```python
if avg_hunger > 0.5 and "farmer" not in existing_titles:
    urgency = (avg_hunger - 0.3) * 2.0
    needs.append(("farmer", urgency, "작물 재배 및 식량 공급", 6.0))
```

**After**:
```python
# [SNN] 식량 정책 반영: food_priority 높으면 hunger 낮아도 farmer 생성
food_urgency = 0.0
food_policy = territory.policy.food_priority

# 주민 평균 food 재고 확인
avg_food = float(np.mean([
    self.inners[p].inventory.get("food", 0) for p in residents
]))
food_safety = len(residents) * 24  # 1일분 안전 재고
territory_food = territory.food_reserve + avg_food * len(residents)

if avg_hunger > 0.5:
    food_urgency = (avg_hunger - 0.3) * 2.0
elif food_policy > 0.4:
    # 예방적: hunger 낮아도 정책 강도에 따라 urgency 부여
    food_urgency = food_policy * 0.6
    if territory_food < food_safety:
        food_urgency += 0.3  # 안전 재고 미달 시 추가

if food_urgency > 0.1 and "farmer" not in existing_titles:
    needs.append(("farmer", food_urgency,
                  "작물 재배 및 식량 공급", 6.0))
```

### 새 메서드: `_process_food_reserve()` — 24틱마다

영주가 영지 food 비축량을 관리한다.

```python
def _process_food_reserve(self) -> list[dict]:
    """영주가 영지 식량을 비축/배급한다. 24틱마다."""
    events = []
    for tid, territory in self.territories.items():
        lord_id = territory.lord_id
        if not lord_id or lord_id not in self.personas:
            continue
        
        lord_inner = self.inners[lord_id]
        if lord_inner.is_sleeping:
            continue
        
        residents = [
            pid for pid, p in self.personas.items()
            if p.territory == tid
        ]
        
        # [SNN] 영주의 비축 성향에 따라 자기 잉여 food를 비축
        lord_food = lord_inner.inventory.get("food", 0)
        stockpile = territory.policy.stockpile_target
        
        # 영주가 food 30 초과분을 비축 (비축 성향이 높을수록 더 많이)
        personal_reserve = 30  # 영주 개인 유지분
        if lord_food > personal_reserve:
            transfer = min(lord_food - personal_reserve,
                          (lord_food - personal_reserve) * stockpile)
            if transfer >= 1:
                lord_inner.inventory["food"] -= transfer
                territory.food_reserve += transfer
                events.append({
                    "type": "food_stockpile",
                    "territory": tid,
                    "lord": lord_id,
                    "amount": round(transfer, 2),
                    "reserve_after": round(territory.food_reserve, 1),
                })
        
        # [Guide] 긴급 배급: 주민 food < 5이고 비축 있으면 배급
        for pid in residents:
            if pid == lord_id:
                continue
            inner = self.inners[pid]
            food = inner.inventory.get("food", 0)
            if food < 5 and territory.food_reserve >= 3:
                ration = min(5, territory.food_reserve)
                inner.inventory["food"] = food + ration
                territory.food_reserve -= ration
                events.append({
                    "type": "food_ration",
                    "territory": tid,
                    "recipient": pid,
                    "amount": round(ration, 2),
                    "reserve_after": round(territory.food_reserve, 1),
                })
    
    return events
```

---

## Step 4: 영주 정책 갱신 — SNN 기반 (`multi_tick_engine.py`)

### 새 메서드: `_update_governance_policy()` — 48틱마다 호출

영주의 **뇌 상태**에서 통치 정책을 도출한다. 행동을 직접 결정하지 않는다.

```python
def _update_governance_policy(self) -> list[dict]:
    """[SNN] 영주 뇌 발화율에서 통치 정책을 도출한다. 48틱마다."""
    events = []
    for tid, territory in self.territories.items():
        lord_id = territory.lord_id
        if not lord_id or lord_id not in self.personas:
            continue
        
        brain = self.brains[lord_id]
        inner = self.inners[lord_id]
        fr = getattr(brain, "_last_firing_rate", None)
        if fr is None or len(fr) == 0:
            continue
        
        policy = territory.policy
        old_tax = policy.tax_rate
        
        # ── 뉴런 발화율에서 통치 성향 읽기 ──
        clusters = np.array_split(fr, 12)
        
        # V(Drive/DA): 높으면 적극적 정책
        drive = float(clusters[0].mean()) * 10.0  # 0~1 정규화
        # T(Tension/CORT): 높으면 위기 대응 모드
        tension = float(clusters[5].mean()) * 10.0
        # S(Stability/5-HT): 높으면 안정 추구
        stability = float(clusters[2].mean()) * 10.0
        # D(Dominance/T): 높으면 권위적 (세금 높게)
        dominance = float(clusters[10].mean()) * 10.0
        # G(Growth/Glu): 높으면 성장 투자
        growth = float(clusters[7].mean()) * 10.0
        
        # greed (내면 욕구)
        greed = float(inner.oyok[3])
        
        # ── 세율 조정 ──
        # 기본 0.10 + 위기(tension) + 권위(dominance) - 안정(stability)
        tax_target = 0.10 + tension * 0.05 + dominance * 0.03 - stability * 0.02 + greed * 0.04
        # [Guide] 범위 제한
        tax_target = max(0.05, min(0.30, tax_target))
        # 점진적 조정 (급격한 변화 방지)
        policy.tax_rate += (tax_target - policy.tax_rate) * 0.3
        policy.tax_rate = round(max(0.05, min(0.30, policy.tax_rate)), 3)
        
        # ── 식량 정책 강도 ──
        # 경제 뉴런 300~309(food scarcity) 발화율 읽기
        food_signal = 0.0
        if len(fr) >= 350:
            food_signal = float(fr[300:310].mean()) * 10.0
        policy.food_priority = min(1.0, food_signal + tension * 0.3 + drive * 0.2)
        
        # ── 비축 성향 ──
        # stability 높으면 비축, drive 높으면 투자 (비축 낮춤)
        policy.stockpile_target = min(1.0, max(0.0,
            0.3 + stability * 0.3 + greed * 0.2 - drive * 0.2 - growth * 0.1
        ))
        
        # ── 지출 상한 ──
        policy.treasury_spending_cap = min(0.5, max(0.1,
            0.2 + growth * 0.15 + drive * 0.1 - stability * 0.05
        ))
        
        policy.last_updated_tick = self.time.tick
        
        # Territory의 tax_rate도 동기화 (기존 코드 호환)
        territory.tax_rate = policy.tax_rate
        
        if abs(policy.tax_rate - old_tax) > 0.005:
            events.append({
                "type": "policy_update",
                "territory": tid,
                "lord": lord_id,
                "tax_rate": policy.tax_rate,
                "food_priority": round(policy.food_priority, 3),
                "stockpile_target": round(policy.stockpile_target, 3),
                "spending_cap": round(policy.treasury_spending_cap, 3),
                "snn_signals": {
                    "drive": round(drive, 3),
                    "tension": round(tension, 3),
                    "stability": round(stability, 3),
                    "dominance": round(dominance, 3),
                    "growth": round(growth, 3),
                    "greed": round(greed, 3),
                },
            })
    
    return events
```

> **SNN/Guide 레이블**:
> - 클러스터 발화율 → 세율/정책: **[SNN]** — 뉴런이 결정
> - 세율 0.05~0.30: **[Guide]** — 착취/기아 방지
> - 점진적 조정 0.3: **[Guide]** — 급변 방지
> - food_priority/stockpile_target 산출: **[SNN]** — 발화율 + 욕구 기반

---

## Step 5: tick() 통합

### _auto_economy_tick() 수정

```python
def _auto_economy_tick(self) -> list[dict]:
    events = []
    self._pricing_cache = {}
    for pid in self.personas:
        if self.inners[pid].is_sleeping:
            continue
        self._pricing_cache[pid] = { ... }  # 기존
    
    # [NEW] Phase 13: 통치 정책 갱신 (48틱마다)
    if self.time.tick % 48 == 0:
        policy_events = self._update_governance_policy()
        events.extend(policy_events)
    
    # [NEW] Phase 13: 세금 징수
    tax_events = self._collect_taxes()
    events.extend(tax_events)
    
    # [NEW] Phase 13: 식량 비축/배급
    food_events = self._process_food_reserve()
    events.extend(food_events)
    
    # ── Phase A: 영주 일자리 생성 ── (기존, farmer 로직 수정됨)
    ...
    
    # ── Phase 11: P2P + NPC + 도구 ── (기존)
    ...
    
    self._pricing_cache = {}
    return events
```

**호출 순서가 중요하다**:
1. 정책 갱신 (48틱) — 세율/식량정책 결정
2. 세금 징수 — 정책의 세율 적용
3. 식량 비축/배급 — 정책의 비축 성향 적용
4. 일자리 생성 — 정책의 food_priority 적용
5. 시장/NPC/도구 — 기존

---

## Step 6: _build_economic_state 확장

영주 정책이 주민의 경제 지각에 반영되어야 한다.

**파일**: `core/multi_tick_engine.py` `_build_economic_state()` (line 847~)

**추가 필드**:
```python
# 기존 5채널 유지 + tax 부담 감각 추가
territory = self.territories.get(persona.territory)
tax_burden = 0.0
if territory:
    tax_burden = territory.policy.tax_rate / 0.30  # 최대 세율 대비 비율 (0~1)

return {
    "food_ratio": ...,       # 기존
    "tool_ratio": ...,       # 기존
    "wealth_ratio": ...,     # 기존
    "job_satisfaction": ..., # 기존
    "relative_wealth": ...,  # 기존
    "tax_burden": tax_burden, # [NEW] Phase 13
}
```

**PersonaBrain 반영** (`persona_brain.py`): 뉴런 350~359에 tax_burden 주입은 **하지 않는다**. 현재 뉴런은 300~349까지 사용 중이고, 세금 부담은 wealth_ratio를 통해 간접적으로 이미 반영된다 (세금 → gold 감소 → wealth_ratio 하락 → 뉴런 320~329 반응). 직접 연결은 Phase 14에서 필요 시 추가.

---

## 검증

### 새 테스트: `test_governance.py`

```
T1: 세금 징수 — 500틱 후 tax_collected 이벤트 1건 이상
T2: 세율 범위 — 모든 영지 tax_rate 0.05~0.30 내
T3: 금고 변동 — 세금으로 금고 증가 확인 (treasury_after > 초기값)
T4: 식량 비축 — food_stockpile 또는 food_ration 이벤트 1건 이상
T5: 정책 SNN 기반 — policy_update 이벤트에 snn_signals 필드 존재
T6: farmer 생성 — 500틱 내 farmer 일자리 1건 이상 (food_priority 효과)
```

### 기존 테스트 회귀

```bash
cd Projects/personas/loom
py test_governance.py        # Phase 13 전용
py test_economy.py           # goods/trade/gold
py test_nomos.py             # stress/사회규범
py test_class_promotion.py   # 승급/drive
py test_snn_economy.py       # SNN 경제 연결
```

**모든 기존 테스트 ALL PASS 필수.**

---

## SNN 창발 경계 요약

| 변경 | 레이블 | 근거 |
|------|--------|------|
| 세율 도출 (클러스터 발화율) | **[SNN]** | 영주 뇌가 결정 |
| food_priority 도출 | **[SNN]** | food scarcity 뉴런 + tension |
| stockpile_target 도출 | **[SNN]** | stability + greed |
| 세율 범위 0.05~0.30 | **[Guide]** | 착취/기아 방지 |
| 최소 소지금 10 gold | **[Guide]** | 기아 방지 |
| 긴급 배급 (food < 5) | **[Guide]** | 아사 방지 안전망 |
| 24틱 주기 | **[Guide]** | 인프라 |
| tax_burden → wealth_ratio 간접 | **[SNN 간접]** | 기존 뉴런 경로 재사용 |

---

## treasury_spending_cap 집행

`GovernancePolicy.treasury_spending_cap`은 Step 4에서 SNN 기반으로 계산된다. **집행 지점**:

- `_process_food_reserve()`: NPC에서 food 매입 시 금고 지출이 `treasury_gold * spending_cap` 초과 금지
- `_collect_taxes()` 내 금고→배급 이체 시 동일 상한 적용
- 상한 초과 시 해당 틱은 지출 건너뛰기 (다음 갱신 때 재시도)

```python
# 금고 지출 상한 확인 (모든 지출 지점에 적용)
max_spend = territory.treasury_gold * territory.policy.treasury_spending_cap
if accumulated_spend >= max_spend:
    break  # 이번 사이클 지출 중단
```

---

## P2P 활성화 로드맵

Phase 13에서 P2P 시장 코드는 수정하지 않는다 (Phase 12-B 안정화 유지).
후속 Phase에서의 P2P 활성화 방향:

- **Phase 14 (예정)**: 영주 정책에 `market_openness` 필드 추가 → P2P 수수료율을 영주가 SNN으로 결정
- **Phase 15 (예정)**: 영지 간 교역 허용 → territory 경계를 넘는 MarketOrder

---

## Codex용 기존 인터페이스 레퍼런스

Phase 13에서 호출할 기존 API:

```python
# Wallet (ontology/layers.py line ~160)
wallet = self.wallets[pid]            # dict[str, Wallet]
wallet.gold                            # float — 현재 소지금
wallet.pay(amount)                     # gold 차감, 잔액 부족 시 False 반환
wallet.receive(amount)                 # gold 추가

# InnerWorld (ontology/layers.py line ~700)
inner = self.inners[pid]              # dict[str, InnerWorld]
inner.inventory                        # dict: {"food": float, "material": float, ...}
inner.oyok                             # np.ndarray[8] — 내면 욕구 (oyok[3] = greed)
inner.is_sleeping                      # bool

# Territory (ontology/layers.py line ~93)
territory = self.territories[tid]     # dict[str, Territory]
territory.lord_id                      # str | None
territory.treasury_gold                # float — 금고 잔액
territory.tax_rate                     # float — 현재 세율 (policy.tax_rate와 동기화)

# PersonaBrain (brain/persona_brain.py)
brain = self.brains[pid]              # dict[str, PersonaBrain]
brain._last_firing_rate                # np.ndarray — 마지막 tick의 뉴런별 발화율

# Engine 주요 멤버
self.personas                          # dict[str, Persona]
self.time.tick                         # int — 현재 틱
self.territories                       # dict[str, Territory]
```

---

## 금지 사항

1. PersonaBrain에 새 뉴런 영역(350+)을 추가하지 마라 — Phase 14에서 결정
2. 영주를 "특별한 뇌"로 만들지 마라 — 같은 PersonaBrain, 같은 SNN
3. 세율을 매 틱 갱신하지 마라 — 48틱 주기 (정책은 신중해야)
4. 금고를 음수로 만들지 마라 — pay() 실패 시 징수 중단
5. 기존 테스트를 수정하지 마라 — 새 테스트만 추가
6. _process_market/_process_npc_shop을 수정하지 마라 — Phase 12-B 안정화 유지
7. territory.tax_rate와 territory.policy.tax_rate를 분리하지 마라 — 항상 동기화

---

## 리뷰 요청서 템플릿

```
## Phase 13 리뷰 요청

### 변경 요약
- [ ] Step 1: GovernancePolicy dataclass + Territory 필드
- [ ] Step 2: _collect_taxes
- [ ] Step 3: 식량 정책 (farmer 생성 수정 + _process_food_reserve)
- [ ] Step 4: _update_governance_policy (SNN 기반)
- [ ] Step 5: tick 통합 (호출 순서)
- [ ] Step 6: _build_economic_state 확장

### 테스트 결과
- test_governance: _/6
- test_economy: _/6
- test_nomos: _/5
- test_class_promotion: _/6
- test_snn_economy: _/6

### 통치 관측 (500틱)
- 세율 범위: ___ ~ ___
- 총 세수: ___
- 식량 비축 이벤트: ___건
- 식량 배급 이벤트: ___건
- farmer 일자리 생성: ___건
- 정책 갱신 이벤트: ___건

### 이슈/우려
```
