# Phase 12-B: 성능 최적화 + NPC SNN화 — Codex 지시서

> **작성자**: Claude (설계/리뷰)
> **구현자**: Codex (코딩/검증)
> **선행 조건**: Phase 12 APPROVE 완료, 4개 테스트 ALL PASS
> **목표**: tick 성능 343ms → 250ms 이하 + NPC 매도를 SNN 기반으로 전환

---

## 현황 분석

### 성능 프로파일 (추정 병목)

1틱 = 10명 페르소나 × (brain.tick + 엔진 로직)

| 구간 | 추정 비중 | 병목 원인 |
|------|:--------:|----------|
| **LIF step() × 10** | ~60% | 1000×1000 STDP 행렬 연산 × 10스텝 × 10명 |
| **_stdp_update()** | ~25% | `np.tile` + `eligibility_trace` 전체 곱셈/감쇠 |
| **경제 로직** | ~10% | `_compute_snn_pricing` 호출 빈도 |
| **기타** | ~5% | 입력 조립, readout, 이벤트 생성 |

### NPC 매도 현황

현재 `_process_npc_shop()` 내 잉여 매도:
```python
# 1814~1827행: 순수 규칙 — surplus > 10이면 무조건 3단위 매도
for goods_type in ["material", "tool", "medicine", "knowledge"]:
    surplus = inner.inventory.get(goods_type, 0) - 10
    if surplus <= 0:
        continue
    sell_qty = min(surplus, 3)
    revenue = npc.get("sell", 5) * sell_qty
```

SNN과 전혀 연결 안 됨. 식량 NPC 매수는 이미 SNN urgency 기반(1795~1812행).

---

## Task A: 성능 최적화 (343ms → 250ms)

### A-1: 희소 STDP (핵심 — 예상 40% 절감)

**파일**: `brain/lif_network.py` `_stdp_update()` (118~164행)

**문제**: `eligibility_trace`가 1000×1000 dense 행렬. 매 스텝 전체 감쇠 + 전체 곱셈.
실제 연결은 5%만 존재 (`connectivity = 0.05`). 95%는 0을 곱하는 낭비.

**해결**: 연결 마스크를 `__init__`에서 캐싱하고, STDP를 희소 연산으로 전환.

```python
# __init__에 추가:
self.conn_mask = (self.weights != 0)  # bool (1000, 1000)
self.conn_indices = np.argwhere(self.conn_mask)  # (N_conn, 2)
```

**_stdp_update 최적화 전략**:

1. `eligibility_trace` 감쇠: 전체 행렬 대신 `conn_mask` 위치만
   ```python
   self.eligibility_trace[self.conn_mask] *= self.eligibility_decay
   ```

2. `np.tile` 제거: post 뉴런별 루프 대신 벡터 인덱싱
   ```python
   # Before (느림):
   pre_matrix = np.tile(self.spike_trace, (len(post_idx), 1))
   
   # After (빠름):
   # post_idx의 연결된 pre만 선택
   for pidx in post_idx:
       connected = self.conn_mask[pidx]
       self.eligibility_trace[pidx, connected] += self.spike_trace[connected]
   ```
   
   또는 더 빠른 벡터화:
   ```python
   if len(post_idx) > 0:
       mask_rows = self.conn_mask[post_idx]       # (N_post, 1000)
       traces = self.spike_trace[np.newaxis, :]    # (1, 1000) broadcast
       self.eligibility_trace[post_idx] += traces * mask_rows
   ```

3. 가중치 클리핑: `np.clip` 전체 대신 변경된 행만
   ```python
   if changed_rows_exc:
       rows = np.array(changed_rows_exc)
       self.weights[rows] = np.clip(self.weights[rows], 0, 0.3)
   ```

4. `conn_mask` 갱신: 가중치가 0이 되거나 새로 생기면 `_stdp_update` 마지막에 갱신
   ```python
   self.conn_mask = (self.weights != 0)
   ```
   단, 매 스텝이 아니라 **가중치 변경이 있을 때만** (reward_signal > 0.01 또는 exc_spikes 존재 시)

### A-2: 시뮬레이션 스텝 최적화

**파일**: `brain/persona_brain.py` tick() (167~178행)

현재: 10스텝 × 10명 = 100회 `snn.step()` / 틱

**선택지** (택 1, 리스크 순):

| 옵션 | 변경 | 절감 | 리스크 |
|------|------|:----:|--------|
| ① 스텝 8로 축소 | `range(10)` → `range(8)` | ~20% | 발화율 분포 변화 |
| ② 격틱 전체 시뮬 | 짝수 틱=10스텝, 홀수 틱=캐시 재사용 | ~50% | 반응 지연 1틱 |
| ③ 배치 입력 | 10스텝 입력을 한 번에 조립 후 배치 실행 | ~15% | 구조 변경 큼 |

**권장**: 옵션 ① (8스텝) 먼저 적용. `firing_rate = total_spikes / 8.0`으로 수정.
테스트 후 발화율이 기존과 유의미하게 다르면 ②로 전환.

> **SNN 레이블: [SNN]** — 시뮬레이션 정밀도 조정이므로 창발에 직접 영향. 8스텝에서도 STDP/항상성이 정상 작동하는지 반드시 검증.

### A-3: 경제 호출 빈도 축소

**파일**: `core/multi_tick_engine.py`

`_compute_snn_pricing`이 `_process_market`과 `_process_npc_shop`에서 페르소나당 다수 호출됨.

**해결**: 24틱 주기 경제 처리 시작 시 **한 번만 계산해서 캐시**.

```python
# _auto_economy_tick() 시작 부분에:
self._pricing_cache = {}
for pid in self.personas:
    if not self.inners[pid].is_sleeping:
        self._pricing_cache[pid] = {
            goods: self._compute_snn_pricing(pid, goods)
            for goods in ["food", "material", "tool", "medicine", "knowledge"]
        }
```

그리고 `_should_sell`, `_should_buy`, `_process_market`, `_process_npc_shop`에서:
```python
# Before:
pricing = self._compute_snn_pricing(pid, goods_type)

# After:
pricing = self._pricing_cache.get(pid, {}).get(goods_type)
if pricing is None:
    pricing = self._compute_snn_pricing(pid, goods_type)
```

**이점**: 24틱마다 호출되는 경제 사이클에서 중복 계산 제거. 
발화율은 같은 틱 안에서 변하지 않으므로 **정확도 손실 없음**.

---

## Task B: NPC 매도 SNN화

### B-1: NPC 매도에 SNN urgency/motivation 반영

**파일**: `core/multi_tick_engine.py` `_process_npc_shop()` 1814~1827행

**현재 (규칙)**:
```python
surplus = inner.inventory.get(goods_type, 0) - 10
if surplus <= 0: continue
sell_qty = min(surplus, 3)
revenue = npc.get("sell", 5) * sell_qty
```

**변경 (SNN 하이브리드)**:
```python
# NPC 매도: SNN 동기 + 안전 가이드
surplus = inner.inventory.get(goods_type, 0) - 10
if surplus <= 0:
    continue

pricing = self._pricing_cache.get(pid, {}).get(goods_type)
if pricing is None:
    pricing = self._compute_snn_pricing(pid, goods_type)

# [SNN] motivation이 높으면 비축 선호 (팔지 않음)
# motivation = drive_rate * 10 (0~1). 높으면 "이 재화가 필요하다"
if pricing["motivation"] > 0.6:
    continue  # 뇌가 이 재화에 동기를 느끼면 NPC에 팔지 않음

# [SNN] urgency가 높으면 급전이 필요 → 더 많이 매도
if pricing["urgency"] > 0.5:
    sell_qty = min(surplus, 5)  # 급할 때는 5단위까지
else:
    sell_qty = min(surplus, 2)  # 여유로우면 2단위만

# [Guide] NPC 매수가(sell)에 SNN 발화 기반 가격 조정
# 실제 NPC가 사는 가격은 고정이지만, 매도량을 조절함으로써
# SNN이 경제 행동에 영향을 미침
npc = NPC_PRICES.get(goods_type, {})
revenue = npc.get("sell", 5) * sell_qty
inner.inventory[goods_type] -= sell_qty
wallet.receive(revenue)
events.append({
    "type": "npc_sell", "seller": pid,
    "goods": goods_type, "qty": sell_qty, "revenue": revenue,
    "motivation": round(float(pricing["motivation"]), 3),
    "urgency": round(float(pricing["urgency"]), 3),
})
```

### B-2: NPC 매수 urgency 임계값 완화

**현재**: `pricing["urgency"] > 0.6 and food_stock < 10` — 긴급 식량만.

**추가**: 도구/약품도 SNN urgency 기반 NPC 매수 허용.

```python
# food 긴급 매수 기존 로직 유지 (1795~1812행)

# [SNN] 도구 NPC 긴급 매수: 도구 없고 urgency 높을 때
tool_pricing = self._pricing_cache.get(pid, {}).get("tool")
if tool_pricing is None:
    tool_pricing = self._compute_snn_pricing(pid, "tool")
if (inner.equipped_tool_durability is None
        and inner.inventory.get("tool", 0) == 0
        and tool_pricing["urgency"] > 0.4):
    npc = NPC_PRICES["tool"]
    stock = self._npc_stock.get("tool", 0)
    if stock > 0 and wallet.gold >= npc["buy"]:
        wallet.pay(npc["buy"])
        inner.inventory["tool"] = inner.inventory.get("tool", 0) + 1
        self._npc_stock["tool"] -= 1
        events.append({
            "type": "npc_buy", "buyer": pid,
            "goods": "tool", "qty": 1, "cost": npc["buy"],
            "urgency": round(float(tool_pricing["urgency"]), 3),
        })

# [SNN] 약품 NPC 긴급 매수: vitality 낮고 urgency 높을 때
if inner.vitality < 0.5 and inner.inventory.get("medicine", 0) == 0:
    med_pricing = self._pricing_cache.get(pid, {}).get("medicine")
    if med_pricing is None:
        med_pricing = self._compute_snn_pricing(pid, "medicine")
    if med_pricing["urgency"] > 0.5:
        npc = NPC_PRICES["medicine"]
        stock = self._npc_stock.get("medicine", 0)
        if stock > 0 and wallet.gold >= npc["buy"]:
            wallet.pay(npc["buy"])
            inner.inventory["medicine"] = inner.inventory.get("medicine", 0) + 1
            self._npc_stock["medicine"] -= 1
            events.append({
                "type": "npc_buy", "buyer": pid,
                "goods": "medicine", "qty": 1, "cost": npc["buy"],
                "urgency": round(float(med_pricing["urgency"]), 3),
            })
```

> **SNN/Guide 레이블**:
> - motivation > 0.6 비축: **[SNN]** — 뉴런 발화율이 직접 결정
> - urgency > 0.5 매도량 조절: **[SNN]** — 뉴런 발화율 기반
> - surplus > 10 임계값: **[Guide]** — 아사 방지 안전장치
> - NPC 가격 고정: **[Guide]** — 외부 상단이므로 규칙 적절

---

## 구현 순서

### Step 1: 희소 STDP (A-1)
1. `lif_network.py` `__init__`에 `conn_mask` 캐시 추가
2. `_stdp_update` 희소화 적용
3. `conn_mask` 갱신 조건 추가
4. 검증: `test_nomos.py` PASS + 발화율 범위 동일

### Step 2: 시뮬레이션 스텝 축소 (A-2)
1. `persona_brain.py` `range(10)` → `range(8)`, `/ 10.0` → `/ 8.0`
2. 검증: `test_snn_economy.py` T5 food scarcity 여전히 PASS

### Step 3: 경제 캐시 (A-3)
1. `_auto_economy_tick`에 `_pricing_cache` 생성
2. 4개 메서드에서 캐시 우선 조회
3. 검증: `test_economy.py` PASS

### Step 4: NPC SNN화 (B-1, B-2)
1. NPC 매도 SNN 동기/urgency 연결
2. 도구/약품 NPC 매수 추가
3. 검증: `test_economy.py` PASS + NPC 매도 이벤트에 motivation/urgency 필드 존재

### Step 5: 통합 검증
```bash
cd Projects/personas/loom
py test_economy.py          # goods/trade/gold 정합성
py test_nomos.py            # stress/사회규범
py test_class_promotion.py  # 승급/drive
py test_snn_economy.py      # SNN 경제 연결
```

### Step 6: 성능 측정
```python
import time
engine = MultiTickEngine()
start = time.time()
for _ in range(100):
    engine.tick()
elapsed = time.time() - start
ms_per_tick = elapsed / 100 * 1000
print(f"Performance: {ms_per_tick:.1f}ms/tick (target: <250ms)")
```

**목표**: 250ms/tick 이하. 달성 못하면 A-2를 옵션 ②(격틱)로 전환.

---

## SNN 창발 경계 요약

| 변경 | 레이블 | 근거 |
|------|--------|------|
| 희소 STDP | [SNN] | STDP 결과 동일, 연산만 축소 |
| 8스텝 시뮬 | [SNN] | 발화율 분포 검증 필수 |
| pricing 캐시 | [인프라] | 같은 틱 내 동일 결과 |
| NPC 매도 motivation 차단 | [SNN] | 뉴런 drive가 비축 결정 |
| NPC 매도 urgency 조절 | [SNN] | 뉴런 urgency가 매도량 결정 |
| NPC 도구/약품 매수 | [SNN] | urgency 기반 구매 |
| surplus 임계값 10 | [Guide] | 아사/도구고갈 방지 |
| NPC 가격 고정 | [Guide] | 외부 상단 = 세계 규칙 |

---

## 리뷰 요청서 템플릿

구현 완료 후 아래 형식으로 리뷰 요청:

```
## Phase 12-B 리뷰 요청

### 변경 요약
- [ ] A-1: 희소 STDP
- [ ] A-2: 8스텝 시뮬레이션
- [ ] A-3: pricing 캐시
- [ ] B-1: NPC 매도 SNN화
- [ ] B-2: NPC 도구/약품 매수

### 성능 결과
- Before: ___ms/tick
- After: ___ms/tick
- 개선율: ___%

### 테스트 결과
- test_economy: _/6
- test_nomos: _/5
- test_class_promotion: _/6
- test_snn_economy: _/6

### 발화율 비교 (A-2 검증)
- 10스텝 평균 발화율: ___
- 8스텝 평균 발화율: ___
- 차이: ___%

### 이슈/우려
```

---

## 금지 사항

1. `eligibility_trace`를 scipy sparse로 교체하지 마라 — numpy 의존성만 유지
2. SNN 스텝을 5 이하로 줄이지 마라 — STDP 학습 품질 보장 불가
3. NPC 가격을 SNN으로 변경하지 마라 — 외부 상단은 세계 규칙
4. `_compute_snn_pricing`의 클러스터 해석(5=stress, 8=fatigue)을 변경하지 마라 — Phase 12에서 검증 완료
5. 기존 테스트를 수정하지 마라 — 새 테스트만 추가 가능
