# Phase 12: 경제 SNN 연결 - "뇌가 경제를 느낀다"

> **Claude -> Codex 지시서**
> 이 문서를 기반으로 구현하세요. 프로젝트 전체 이해는 `CODEX-PROJECT-GUIDE.md` 참조.

---

## 1. 목표

Phase 11에서 깔아놓은 경제 인프라(goods, 시장, NPC, 도구)에 SNN을 연결한다.
현재 경제 행동은 전부 규칙(if-else/상수)인데, 이것을 **뉴런 신호에서 읽는** 구조로 전환한다.

### Before / After

| 경제 행동 | Before (Phase 11) | After (Phase 12) |
|-----------|-------------------|-------------------|
| 가격 결정 | `rng.uniform(0.4, 0.7) * npc_buy` | 뉴런 절박함 신호 -> 가격 |
| NPC 매수 판단 | `hunger_ticks > 6 and food < 5` | SNN 절박 신호 > 임계값 |
| 일 만족도 | 없음 (모든 일 동일 reward) | 적성 일치 시 DA 보상 증가 |
| 거래 의사 | `inventory > 72 이면 판매` | 잉여 인식 신호 + 성격(탐욕) |
| 직업 전환 | 없음 (배정되면 고정) | 낮은 만족도 -> work 회피 -> 자연 이직 |

---

## 2. 창발 경계

**모든 항목에 [SNN] 또는 [가이드] 레이블이 붙어있습니다. Codex는 이 경계를 반드시 지켜야 합니다.**

| # | 컴포넌트 | 레이블 | 의미 |
|---|---------|--------|------|
| A | 경제 입력 인코딩 | **[SNN]** | 인벤토리/부/도구 상태를 뉴런 입력으로 |
| B | 경제 보상 강화 | **[SNN]** | 적성 일치, 거래 성공에 DA 보상 |
| C | SNN 기반 가격 | **[SNN]** | 클러스터 발화율 -> 절박함 -> 가격 |
| D | SNN 기반 거래 판단 | **[SNN]** | 잉여 인식 + 성격 -> 매도/매수 결정 |
| E | 주문서 매칭 인프라 | **[가이드]** | 매수-매도 주문 매칭 로직 (기존 유지) |
| F | NPC 상점 인프라 | **[가이드]** | NPC 가격 테이블, 일일 재고 (기존 유지) |

**규칙**: [SNN]으로 표시된 부분을 if-else로 구현하면 리뷰에서 거부됩니다.

---

## 3. 구현 Step

### Step 1: 경제 지각 - 뇌가 경제를 본다 [SNN]

**파일**: `brain/persona_brain.py`

**현재**: brain.tick()의 입력은 climate(0~99), oyok(100~149), fear(150~199), joy(200~249), anger(250~299)만 있다. 뇌는 자기 인벤토리, 부, 도구 상태를 모른다.

**변경**: 뉴런 300~349에 경제 입력 채널 5개를 추가한다.

#### 1-A. brain.tick() 시그니처 확장

```python
# persona_brain.py tick() 파라미터에 추가:
def tick(
    self,
    climate_vec: np.ndarray,
    energy_pool: float,
    oyok: np.ndarray,
    tone: np.ndarray,
    personality: np.ndarray | None = None,
    fear: float = 0.0,
    social_pull: float = 0.0,
    memory_bias: np.ndarray | None = None,
    skill_drive_signals: dict | None = None,
    economic_state: dict | None = None,       # <-- NEW
) -> tuple[str, int, float]:
```

#### 1-B. 경제 입력 인코딩 (tick() 내부, oyok 주입 다음)

```python
# ── Phase 12: 경제 지각 (뉴런 300~349) ──
if economic_state is not None:
    eco = economic_state
    eco_base = 300  # 경제 뉴런 시작 위치

    # 채널 1 (300~309): 식량 부족 신호
    # food_ratio = 현재 food / 초기 food(30). 0이면 극도 부족, 1이면 충분.
    # 부족할수록 강한 흥분 (생존 위협 인식)
    food_scarcity = 1.0 - min(1.0, eco.get("food_ratio", 1.0))
    if food_scarcity > 0.1:
        targets = rng.choice(range(eco_base, eco_base + 10),
                             size=5, replace=False)
        input_signal[targets] += food_scarcity * 0.5

    # 채널 2 (310~319): 도구 상태 신호
    # tool_ratio = durability / 100. 0이면 도구 없음, 1이면 완벽.
    # 도구 없으면 흥분 (도구 필요 인식)
    tool_lack = 1.0 - min(1.0, eco.get("tool_ratio", 0.0))
    if tool_lack > 0.3:
        targets = rng.choice(range(eco_base + 10, eco_base + 20),
                             size=5, replace=False)
        input_signal[targets] += tool_lack * 0.3

    # 채널 3 (320~329): 경제적 안정 신호
    # wealth_ratio = 현재 gold / 시작 gold(2000). 부유하면 억제, 빈곤하면 흥분.
    wealth_ratio = min(2.0, eco.get("wealth_ratio", 1.0))
    if wealth_ratio < 0.5:
        # 빈곤 -> 불안 신호
        targets = rng.choice(range(eco_base + 20, eco_base + 30),
                             size=5, replace=False)
        input_signal[targets] += (0.5 - wealth_ratio) * 0.4
    elif wealth_ratio > 1.5:
        # 풍요 -> 안정 억제
        targets = rng.choice(range(eco_base + 20, eco_base + 30),
                             size=5, replace=False)
        input_signal[targets] -= 0.15

    # 채널 4 (330~339): 직업 만족도 신호
    # job_satisfaction = 최근 work reward 평균 (0~1). 높으면 억제, 낮으면 흥분.
    job_sat = eco.get("job_satisfaction", 0.5)
    if job_sat < 0.3:
        # 불만족 -> work 회피 뉴런 흥분 (자연스러운 이직 동기)
        targets = rng.choice(range(eco_base + 30, eco_base + 40),
                             size=5, replace=False)
        input_signal[targets] += (0.3 - job_sat) * 0.5
    elif job_sat > 0.7:
        # 만족 -> 안정 신호
        targets = rng.choice(range(eco_base + 30, eco_base + 40),
                             size=5, replace=False)
        input_signal[targets] -= 0.1

    # 채널 5 (340~349): 상대적 부 비교 (사회 비교)
    # relative_wealth = 내 gold / 영지 평균 gold. 1.0이 평균.
    rel_wealth = eco.get("relative_wealth", 1.0)
    if rel_wealth < 0.5:
        # 빈곤층 -> 박탈감 (분노/욕구 뉴런 자극)
        targets = rng.choice(range(eco_base + 40, eco_base + 50),
                             size=5, replace=False)
        input_signal[targets] += (0.5 - rel_wealth) * 0.4
```

**핵심**: 이 입력들은 뉴런에 전류로 주입된다. 뇌는 이 신호를 **직접 해석하지 않는다**. STDP가 시간이 지나면서 "식량 부족 뉴런이 활성화될 때 eat을 하면 보상을 받는다"는 연결을 **스스로 학습**한다.

#### 1-C. 엔진에서 economic_state 조립

**파일**: `core/multi_tick_engine.py` (brain.tick() 호출 직전, ~line 292 부근)

```python
# ── Phase 12: 경제 지각 신호 조립 ──
_wallet = self.wallets.get(pid)
_territory = self.territories.get(persona.territory)

# 영지 평균 gold 계산
_territory_pids = [p for p, pp in self.personas.items()
                   if pp.territory == persona.territory]
_avg_gold = (sum(self.wallets[p].gold for p in _territory_pids
                 if p in self.wallets) / max(1, len(_territory_pids)))

# 직업 만족도: 최근 work 보상의 이동평균
_work_rewards = [r for r in brain.snn.reward_history[-30:]
                 if r is not None] if brain.snn.reward_history else []
# work 보상만 분리할 수 없으므로 전체 양의 보상 평균 사용
# (work가 주요 행동이므로 근사적으로 유효)
_positive_rewards = [r for r in _work_rewards if r > 0]
_job_satisfaction = float(np.mean(_positive_rewards)) if _positive_rewards else 0.5

economic_state = {
    "food_ratio": inner.inventory.get("food", 0) / 30.0,
    "tool_ratio": (inner.equipped_tool_durability or 0) / 100.0,
    "wealth_ratio": (_wallet.gold / 2000.0) if _wallet else 0.5,
    "job_satisfaction": _job_satisfaction,
    "relative_wealth": (_wallet.gold / max(1, _avg_gold)) if _wallet else 1.0,
}
```

brain.tick() 호출에 `economic_state=economic_state` 추가:

```python
action, intensity, cost = brain.tick(
    climate_vec=climate_vec,
    energy_pool=inner.energy_pool,
    oyok=inner.oyok,
    tone=inner.tone,
    personality=self.personas[pid].personality,
    fear=fear_val,
    social_pull=social_pull,
    memory_bias=memory_bias,
    skill_drive_signals=skill_drive_signals,
    economic_state=economic_state,         # <-- NEW
)
```

---

### Step 2: 경제 보상 강화 - 뇌가 경제를 느낀다 [SNN]

**파일**: `core/multi_tick_engine.py`

**현재 _compute_reward (line 2535~2576)**:

```python
# 현재 work 보상:
elif action == "work":
    if energy > 0.3:
        reward += 0.3
    else:
        reward -= 0.1
```

모든 work가 동일한 +0.3. farmer든 craftsman이든. 적성과 무관.

**변경**: work 보상에 적성 일치도와 경제적 성과를 반영한다.

```python
elif action == "work":
    if energy > 0.3:
        reward += 0.15  # 기본 work 보상 (0.3 -> 0.15로 낮춤)

        # [SNN] 적성 일치 보너스: 뇌가 "이 일이 나에게 맞는다"를 학습
        job_title = self._get_persona_job_title(pid)
        aptitude = self.personas[pid].aptitude_map.get(job_title, 0.5)
        reward += (aptitude - 0.4) * 0.5  # 적성 0.4->+0, 0.7->+0.15, 1.0->+0.3

        # [SNN] 숙달 성장 보상: 성장하고 있으면 추가 도파민
        if inner.skill_profiles and job_title in inner.skill_profiles:
            sp = inner.skill_profiles[job_title]
            ceiling = SKILL_CEILINGS.get(job_title, (0.5, 0.5, 0.005))[0]
            growth_room = 1.0 - (sp.mastery / ceiling if ceiling > 0 else 1.0)
            if growth_room > 0.1:  # 아직 성장 여지가 있음
                reward += 0.1
    else:
        reward -= 0.1

    # [SNN] 경제적 성과: goods를 생산했으면 추가 보상
    # (이미 inventory에 goods가 추가된 후이므로, 생산이 있었으면 보상)
    # engine에서 이 정보를 전달할 필요 있음 -> 아래 2-B 참조
```

#### 2-B. 경제 이벤트 기반 추가 보상

_compute_reward 시그니처를 확장하거나, 엔진에서 직접 추가 보상을 적용한다.

**파일**: `core/multi_tick_engine.py` (line ~402, reward 계산 직후)

현재:
```python
reward = self._compute_reward(pid, action, inner.energy_pool, prev_energy)
if econ_event and action == "work":
    etype = econ_event.get("type", "")
    if etype == "wage_unpaid":
```

변경 - 경제 이벤트에 따른 추가 보상:

```python
reward = self._compute_reward(pid, action, inner.energy_pool, prev_energy)

# [SNN] Phase 12: 경제 이벤트 -> 도파민 보상
if econ_event and action == "work":
    etype = econ_event.get("type", "")
    if etype == "wage_unpaid":
        reward -= 0.3  # 기존
    elif etype in ("self_employed", "employed"):
        # goods 생산에 대한 미세 보상 (생산의 기쁨)
        goods_amt = econ_event.get("goods_amount", 0)
        if goods_amt > 0:
            reward += min(0.15, goods_amt * 0.05)  # 최대 +0.15
```

---

### Step 3: SNN 기반 가격 결정 [SNN]

**파일**: `core/multi_tick_engine.py` (_process_market 내부)

**현재 (line ~1541)**:

```python
# 매도 가격: 무작위
price = npc_buy * rng.uniform(0.4, 0.7)
```

**변경**: 뇌의 상태가 가격을 결정한다.

새 메서드 `_compute_snn_pricing(pid, goods_type)`:

```python
def _compute_snn_pricing(self, pid: str, goods_type: str) -> dict:
    """[SNN] 페르소나의 뉴런 상태에서 매도/매수 가격을 도출한다.

    핵심 원리:
    - 스트레스/피로 높으면 -> 절박 -> 싸게 팔고, 비싸게라도 산다
    - 안정/여유 있으면 -> 여유 -> 비싸게 팔고, 싼 것만 산다
    - 성격(탐욕 oyok[3]) -> 전반적 가격 수준 조절
    """
    inner = self.inners[pid]
    brain = self.brains[pid]
    npc = NPC_PRICES.get(goods_type, {"buy": 20, "sell": 5})

    # SNN 신호 읽기: 최근 발화율에서 클러스터별 활성도 추출
    fr = getattr(brain, '_last_firing_rate', None)
    if fr is None:
        # 발화율 없으면 중간값 폴백
        urgency = 0.5
    else:
        # T-cluster(스트레스, idx=5) 뉴런 범위의 평균 발화율
        # F-cluster(피로, idx=8) 뉴런 범위의 평균 발화율
        # V-cluster(동기/DA, idx=0) 뉴런 범위의 평균 발화율
        n = brain.n_neurons
        cluster_size = n // 12  # ~83 neurons per cluster

        stress_rate = float(fr[5 * cluster_size : 6 * cluster_size].mean())
        fatigue_rate = float(fr[8 * cluster_size : 9 * cluster_size].mean())
        drive_rate = float(fr[0 * cluster_size : 1 * cluster_size].mean())

        # 절박함 = (stress + fatigue) / 2, 동기 = drive
        # 정규화: 발화율은 0~0.3 범위. 0.04가 목표. 0.1 이상이면 강한 신호.
        urgency = min(1.0, (stress_rate + fatigue_rate) * 5.0)  # 0~1
        motivation = min(1.0, drive_rate * 10.0)  # 0~1

    # 성격: 탐욕(oyok[3]) -> 가격 마진 조절
    greed = float(inner.oyok[3])  # 0~1

    # 매도 가격: 여유로우면 비싸게, 절박하면 싸게
    price_floor = npc["sell"]        # NPC 매입가 (최소)
    price_ceiling = npc["buy"]       # NPC 판매가 (최대)
    price_range = price_ceiling - price_floor

    # 여유도 = 1 - urgency. 여유로울수록 비싸게 팔 수 있음.
    patience = 1.0 - urgency
    sell_price = price_floor + price_range * patience * (0.3 + greed * 0.4)

    # 매수 최대 가격: 절박하면 비싸게라도 삼
    buy_max = price_floor + price_range * urgency * (0.5 + (1 - greed) * 0.3)

    return {
        "sell_price": max(price_floor, sell_price),
        "buy_max": min(price_ceiling, buy_max),
        "urgency": urgency,
    }
```

**_process_market() 수정**: 기존 `rng.uniform(0.4, 0.7) * npc_buy` 를 `_compute_snn_pricing()` 호출로 교체.

---

### Step 4: SNN 기반 거래 판단 [SNN]

**파일**: `core/multi_tick_engine.py` (_process_market 내부)

**현재**: `inventory > 72이면 무조건 매도 등록`

**변경**: 잉여 인식과 성격이 거래 의사를 결정한다.

```python
def _should_sell(self, pid: str, goods_type: str) -> tuple[bool, float]:
    """[SNN] 매도 의사결정. 잉여 인식 + 성격 + 뇌 상태.

    Returns: (should_sell, quantity)
    """
    inner = self.inners[pid]
    stock = inner.inventory.get(goods_type, 0)

    # 기본 잉여 인식: goods별 "충분하다"의 기준
    # food는 넉넉히 보유해야 안심 (생존), tool/material은 적게 보유해도 됨
    comfort_level = {"food": 20, "material": 8, "tool": 3,
                     "medicine": 5, "knowledge": 3}
    threshold = comfort_level.get(goods_type, 10)
    surplus = stock - threshold

    if surplus <= 0:
        return False, 0  # 잉여 없음

    # [SNN] 뇌 상태 반영: stress 높으면 비축 성향 (매도 꺼림)
    stress = inner.chronic_stress
    if stress > 0.5:
        surplus *= (1.0 - (stress - 0.5))  # stress 0.5~1.0에서 매도량 감소

    # 성격: greed(oyok[3]) 높으면 많이 비축 (매도 꺼림)
    greed = float(inner.oyok[3])
    surplus *= (1.0 - greed * 0.3)  # greed 1.0이면 매도량 30% 감소

    sell_qty = max(0, min(surplus, 5))  # 1회 최대 5단위
    return sell_qty > 0.5, sell_qty


def _should_buy(self, pid: str, goods_type: str) -> tuple[bool, float]:
    """[SNN] 매수 의사결정. 부족 인식 + 절박함 + 뇌 상태.

    Returns: (should_buy, max_price_willing)
    """
    inner = self.inners[pid]
    stock = inner.inventory.get(goods_type, 0)
    pricing = self._compute_snn_pricing(pid, goods_type)

    # 부족 인식
    need_level = {"food": 10, "material": 3, "tool": 1,
                  "medicine": 2, "knowledge": 1}
    threshold = need_level.get(goods_type, 5)

    if stock >= threshold:
        return False, 0  # 충분함

    # [SNN] 절박도에 따라 지불 의사 결정
    # urgency가 높으면 (stress/fatigue 높으면) 비싸게라도 삼
    return True, pricing["buy_max"]
```

---

### Step 5: NPC 매수 판단 SNN화 [SNN]

**파일**: `core/multi_tick_engine.py` (_process_npc_shop 내부)

**현재 (line ~1628)**:

```python
# 긴급 식량 구매 (hunger_ticks > 6이고 food < 5)
if (inner.inventory.get("food", 0) < 5
        and inner.consecutive_hunger_ticks > 6):
```

**변경**: SNN 절박 신호 기반으로 전환.

```python
# [SNN] 긴급 식량 구매: 뇌의 절박 신호 기반
pricing = self._compute_snn_pricing(pid, "food")
food_stock = inner.inventory.get("food", 0)

# 절박 조건: urgency > 0.6 AND food < 10
# (urgency는 SNN의 stress+fatigue 클러스터에서 유래)
if pricing["urgency"] > 0.6 and food_stock < 10:
    # 매수량: 절박할수록 많이 삼
    buy_qty = min(int(3 + pricing["urgency"] * 5), stock)
    # ... 기존 구매 로직
```

---

## 4. 수정 대상 파일 요약

| 파일 | 변경 | Step |
|------|------|------|
| `brain/persona_brain.py` | tick() 시그니처에 `economic_state` 추가, 뉴런 300~349 입력 인코딩 | 1 |
| `core/multi_tick_engine.py` | economic_state 조립 + brain.tick() 호출 수정 | 1 |
| `core/multi_tick_engine.py` | _compute_reward() 적성/성장/생산 보상 추가 | 2 |
| `core/multi_tick_engine.py` | 경제 이벤트 -> 추가 reward | 2 |
| `core/multi_tick_engine.py` | _compute_snn_pricing() 신규 메서드 | 3 |
| `core/multi_tick_engine.py` | _should_sell(), _should_buy() 신규 메서드 | 4 |
| `core/multi_tick_engine.py` | _process_market() 기존 가격/판단 로직 교체 | 3, 4 |
| `core/multi_tick_engine.py` | _process_npc_shop() 긴급매수 조건 교체 | 5 |

---

## 5. 검증 기준

### T1: 가격 분산 (SNN 연결 증거)

**같은 goods에 대해 페르소나별 매도 가격이 다르다.**
- 10명의 매도 가격 표준편차 > NPC sell가의 20%
- 근거: 각 페르소나의 stress/fatigue/greed가 다르므로 가격이 달라야 함

### T2: 절박 가격 역전 (SNN 인과 관계)

**stress 높은 페르소나가 낮은 페르소나보다 싸게 판다.**
- 500틱 시뮬 중 stress 상위 3명의 평균 매도가 < stress 하위 3명의 평균 매도가
- 근거: urgency가 높으면 patience가 낮아 가격이 내려감

### T3: 적성 보상 차이 (학습 증거)

**적성 높은 직업 work의 reward가 낮은 직업보다 높다.**
- Orin(craftsman 적성 0.74)의 craftsman work reward > laborer work reward
- 근거: aptitude bonus가 reward에 반영됨

### T4: 직업 불만족 -> work 회피 (창발 증거)

**적성 낮은 직업에 배정된 페르소나의 work 비율이 감소한다.**
- 이건 3000틱 필요. 적성 0.3 페르소나의 work% < 적성 0.7 페르소나의 work%
- 완전한 증거는 어렵지만, 추세가 보여야 함

### T5: 경제 입력 -> 뉴런 발화 (입력 증명)

**food_ratio가 0에 가까울 때 뉴런 300~309의 발화율이 높다.**
- 식량 부족 상태에서 해당 뉴런 범위의 평균 발화율 > 식량 충분 상태

### T6: 기존 테스트 호환

**test_economy.py, test_nomos.py, test_class_promotion.py 전부 PASS.**

---

## 6. 테스트 파일 (신규 작성)

**파일**: `test_snn_economy.py`

```python
# 검증 항목:
# T1: 가격 분산 (500틱)
# T2: 절박 가격 역전 (500틱)
# T3: 적성 보상 차이 (500틱)
# T4: work 비율 추세 (3000틱, 선택)
# T5: 경제 뉴런 발화 (500틱)
# T6: 기존 테스트 호환 (별도 실행)
```

---

## 7. 구현 순서 및 중간 체크포인트

```
Step 1 (경제 지각):
  1a. persona_brain.py: tick() 시그니처 + 뉴런 300~349 입력
  1b. multi_tick_engine.py: economic_state 조립 + tick() 호출
  -> 중간 검증: 기존 테스트 3개 ALL PASS (기능 추가만, 기존 동작 불변)

Step 2 (경제 보상):
  2a. _compute_reward() 수정
  2b. 경제 이벤트 추가 보상
  -> 중간 검증: 기존 테스트 + T3(적성 보상 차이) 확인

Step 3 (SNN 가격):
  3a. _compute_snn_pricing() 신규
  3b. _process_market() 가격 로직 교체
  -> 중간 검증: T1(가격 분산) + T2(절박 역전)

Step 4 (SNN 거래 판단):
  4a. _should_sell(), _should_buy() 신규
  4b. _process_market() 거래 판단 교체
  -> 중간 검증: P2P 거래 발생 확인

Step 5 (NPC 매수 SNN화):
  5a. _process_npc_shop() 조건 교체
  -> 최종 검증: T1~T6 전부

각 Step 완료 후 기존 테스트 3개 실행하여 호환성 확인.
```

---

## 8. 주의사항

1. **뉴런 범위 충돌 금지**: 기존 0~299는 건드리지 않는다. 300~349만 사용.
2. **발화율 읽기**: `brain._last_firing_rate`는 tick() 실행 후에만 유효. tick() 전에 읽으면 이전 틱 데이터.
3. **클러스터 인덱스**: 12개 클러스터는 뉴런을 균등 분할(~83개). `cluster_size = n // 12`.
4. **보상 범위**: `np.clip(reward, -1.0, 1.0)` 유지. 개별 보상 항목이 아무리 많아도 합계는 [-1, 1].
5. **성능**: 500틱 test_economy가 250ms/tick 이하로 유지. 1000뉴런 범위 연산은 무시 가능.
6. **기존 동작 보존**: Step 1~2는 기능 추가만. Step 3~5에서 기존 로직을 교체할 때 주의.

---

## 9. Codex 리뷰 요청서 템플릿

구현 완료 후 아래 형식으로 리뷰 요청서를 작성하세요:

```markdown
# Phase 12 리뷰 요청서

## 변경 요약
- [파일별 변경 내용]

## 창발 경계 준수
- [SNN] 항목: [각각 어떻게 SNN 신호를 읽었는지]
- [가이드] 항목: [기존 규칙 유지 확인]

## 테스트 결과
- T1: PASS/FAIL (수치)
- T2: PASS/FAIL (수치)
- ...
- T6: 기존 테스트 3개 ALL PASS

## 질문/이슈
- [구현 중 발견한 문제나 설계와 다른 부분]
```
