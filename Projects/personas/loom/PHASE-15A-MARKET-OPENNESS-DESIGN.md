# Phase 15-A: 영주 교역정책 SNN — market_openness 창발

## 배경

Phase 15 discuss 합의(2026-04-18)에서 **Phase 15-B 집단행동 후 15-A로 순연** 명시. Phase 15 구현 완료([APPROVE] T1~T7 PASS, 2026-04-18), 15-A 진행 조건 충족.

**문제**: 영주의 교역 개방도가 하드코딩(영지 내부만 P2P). density_ratio 높은 단결 공동체는 외부 경계, 성장 욕구 높은 영주는 외부 교역 원할 텐데, 현재는 모두 동일. **SNN에서 창발해야 함**.

**원칙**:
- 새 뉴런 **추가 금지** — 기존 12 cluster + Phase 15 `CommunityMetrics.density_ratio` 재사용
- 기존 정책 구조(`tax_rate, food_priority, stockpile_target, treasury_spending_cap`) 확장
- density_ratio 높은 영지 → 외부 개방 낮아지도록 **자연히 수렴**

## 변경 파일 (2개)

1. `Projects/personas/loom/ontology/layers.py` — `GovernancePolicy`에 `market_openness` 필드 추가
2. `Projects/personas/loom/core/multi_tick_engine.py`
   - `_update_governance_policy` — market_openness SNN 도출
   - `_process_market` Phase B — 영지 간 거래 필터 완화 (market_openness 기반)

테스트: `Projects/personas/loom/test_phase15a_market_openness.py` (신규, T1~T6)

---

## 구현 순서

### Step 1: `GovernancePolicy` 확장

[Projects/personas/loom/ontology/layers.py:93-100](Projects/personas/loom/ontology/layers.py#L93-L100)

```python
@dataclass
class GovernancePolicy:
    """영주의 현재 통치 정책. SNN 신호에서 도출되어 매 48틱마다 갱신."""
    tax_rate: float = 0.10
    food_priority: float = 0.5
    stockpile_target: float = 0.5
    treasury_spending_cap: float = 0.3
    market_openness: float = 0.5          # ★ Phase 15-A: 외부 교역 개방도 [0.0, 1.0]
    last_updated_tick: int = 0
```

### Step 2: `_update_governance_policy` SNN 도출 추가

[Projects/personas/loom/core/multi_tick_engine.py:1374-1472](Projects/personas/loom/core/multi_tick_engine.py#L1374-L1472)

line 1396 뒤 (`old_cap = policy.treasury_spending_cap` 직후):

```python
old_openness = policy.market_openness
```

line 1442 뒤 (`treasury_spending_cap` 계산 후, `last_updated_tick` 앞):

```python
            # ── Phase 15-A: market_openness 창발 ──
            # density_ratio는 이 영지의 최근 CommunityMetrics에서 조회
            density_ratio = 0.0
            for m in self._last_community_metrics:
                if m.territory_id == tid:
                    density_ratio = float(m.density_ratio)
                    break
            # density_ratio > 0.05 이면 단결된 공동체 → 외부 경계 강화
            density_pressure = max(0.0, min(1.0, (density_ratio - 0.03) * 20.0))

            # growth/stability 높을수록 개방, tension/density 높을수록 쇄국
            openness_target = (
                0.5
                + growth * 0.25           # 성장 욕구 → 외부 교역 열망
                + stability * 0.15        # 안정 → 교류 가능
                - tension * 0.25          # 긴장 → 외부 경계
                - density_pressure * 0.3  # 단결 공동체 → 외부 비개방
            )
            openness_target = max(0.0, min(1.0, openness_target))
            # 48틱 부드러운 수렴 (tax와 동일한 0.3 비율)
            policy.market_openness += (openness_target - policy.market_openness) * 0.3
            policy.market_openness = round(max(0.0, min(1.0, policy.market_openness)), 3)
```

line 1448-1452의 `changed` 조건에 추가:

```python
            changed = (
                abs(policy.tax_rate - old_tax) > 0.005
                or abs(policy.food_priority - old_food) > 0.005
                or abs(policy.stockpile_target - old_stockpile) > 0.005
                or abs(policy.treasury_spending_cap - old_cap) > 0.005
                or abs(policy.market_openness - old_openness) > 0.005  # ★
            )
```

line 1461의 `events.append` dict에 추가:

```python
                "market_openness": round(policy.market_openness, 3),
                "density_ratio": round(density_ratio, 4),
```

`snn_signals` dict에 추가:

```python
                    "density_pressure": round(density_pressure, 3),
```

### Step 3: P2P 시장 필터 확장 (영지 간 거래 조건부 허용)

[Projects/personas/loom/core/multi_tick_engine.py:2400-2406](Projects/personas/loom/core/multi_tick_engine.py#L2400-L2406)

**Before** (line 2401-2406):
```python
                orders = [
                    o for o in self.market_orders
                    if (o.goods_type == need_type and o.quantity > 0
                        and o.seller_id != pid
                        and self.personas.get(o.seller_id, persona).territory == persona.territory)
                ]
```

**After**:
```python
                buyer_territory_policy = (
                    self.territories[persona.territory].policy
                    if persona.territory in self.territories
                    else None
                )
                buyer_openness = (
                    buyer_territory_policy.market_openness
                    if buyer_territory_policy else 0.5
                )

                def can_trade(seller_id: str) -> bool:
                    seller = self.personas.get(seller_id)
                    if not seller:
                        return False
                    if seller.territory == persona.territory:
                        return True  # 같은 영지는 항상 허용
                    # 영지 간 거래: 양측 영주 개방성의 평균이 0.4 이상
                    seller_territory = self.territories.get(seller.territory)
                    if not seller_territory:
                        return False
                    avg_openness = (buyer_openness + seller_territory.policy.market_openness) / 2.0
                    return avg_openness >= 0.4

                orders = [
                    o for o in self.market_orders
                    if (o.goods_type == need_type and o.quantity > 0
                        and o.seller_id != pid
                        and can_trade(o.seller_id))
                ]
```

**수수료 변경**: 영지 간 거래는 수수료 2배 (외부 교역 비용 반영)

line 2432 (`fee = FACILITY_FEES.get("market", 2.0)`) 아래 추가:

```python
                    seller_persona = self.personas.get(order.seller_id)
                    is_inter_territory = (
                        seller_persona is not None
                        and seller_persona.territory != persona.territory
                    )
                    if is_inter_territory:
                        fee *= 2.0  # 영지 간 교역은 수수료 2배
```

line 2444-2446의 영지 금고 입금에서, 영지 간 거래의 수수료는 **buyer 영지와 seller 영지에 절반씩 분배**:

```python
                        # 수수료: 영지 간이면 양측 금고에 분배, 아니면 buyer 영지만
                        territory = self.territories.get(persona.territory)
                        sink_amount = fee * MARKET_FEE_SINK_RATIO
                        keep_amount = fee - sink_amount
                        if is_inter_territory and territory:
                            seller_territory = self.territories.get(seller_persona.territory)
                            territory.treasury_gold += keep_amount / 2.0
                            if seller_territory:
                                seller_territory.treasury_gold += keep_amount / 2.0
                        elif territory:
                            territory.treasury_gold += keep_amount
```

### Step 4: `events.append` trade 이벤트에 is_inter_territory 추가

line 2449-2457 `events.append({"type": "trade", ...})` 에 추가:

```python
                            "inter_territory": is_inter_territory,
```

---

## 테스트: `test_phase15a_market_openness.py`

T1~T6 요구사항:

- **T1**: 신규 `GovernancePolicy`는 `market_openness=0.5`로 초기화
- **T2**: `_update_governance_policy` 실행 후 `market_openness`가 SNN 신호에 따라 변동
- **T3**: density_ratio > 0.05인 영지는 48틱 후 market_openness가 0.5보다 낮아짐
- **T4**: 양측 영지 모두 market_openness < 0.4이면 영지 간 거래 발생 안 함 (`can_trade` False)
- **T5**: 양측 평균 openness >= 0.4이면 영지 간 거래 발생 (inter_territory=True 이벤트)
- **T6**: 영지 간 거래 수수료는 기본(2.0)의 2배(4.0), 양측 금고에 절반씩 분배

검증:

```bash
C:\Users\haj\AppData\Local\Programs\Python\Python314\python.exe Projects/personas/loom/test_phase15a_market_openness.py
```

기존 테스트 회귀 금지:
- `test_phase15_collective_action.py` T1~T7 PASS 유지
- `test_phase14b_snn_integration.py` T1~T7 PASS 유지

---

## 설계 근거

1. **추가 뉴런 없음**: growth/stability/tension은 `_update_governance_policy`에서 이미 계산됨. density_ratio는 Phase 15 `CommunityMetrics`에서 재사용.
2. **density_pressure 공식**: `(density_ratio - 0.03) * 20` 은 density 0.03 이하는 0, 0.08 이상은 1로 포화. Phase 15의 warning threshold 0.05와 연속적.
3. **영지 간 거래 수수료 2배**: 외부 교역의 실제 비용 (이동/검역/환전). MARKET_FEE_SINK_RATIO=0.5로 gold 싱크 유지.
4. **거래 가능 임계값 0.4**: 양측 평균이 중간값(0.5) 미만이어도 어느 한 쪽이 강하게 열려 있으면 교역 허용.
5. **수렴 비율 0.3**: 기존 tax_rate와 동일. 48틱에 약 70% 수렴.

---

## 비차단 주의 (Phase 15 인계)

Phase 15 리뷰에서 지적된 `_get_community_members` O(N²) 이슈는 15-A 범위 밖. 별도 Phase에서 처리.
