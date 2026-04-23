# -*- coding: utf-8 -*-
"""Phase 13 governance verification.

500틱 시뮬레이션으로 검증:
T1: 세금 징수 이벤트 1건 이상
T2: 세율 범위 0.05~0.30
T3: 세금으로 금고 증가 확인
T4: 식량 비축 또는 배급 이벤트 1건 이상
T5: 정책 갱신 이벤트에 snn_signals 포함
T6: farmer 일자리 1건 이상 생성
"""
import sys
import time

sys.path.insert(0, ".")

from core.multi_tick_engine import MultiTickEngine


TICKS = 500
print(f"=== Phase 13 Governance Verification ({TICKS} ticks) ===")

engine = MultiTickEngine()
initial_treasury = {
    tid: territory.treasury_gold
    for tid, territory in engine.territories.items()
}

# 정책 효과가 500틱 안에 관측되도록 초기 조건을 명확히 둔다.
for territory in engine.territories.values():
    territory.policy.food_priority = 1.0
    territory.policy.stockpile_target = 1.0
    territory.policy.treasury_spending_cap = 0.3
for lord_id in [t.lord_id for t in engine.territories.values() if t.lord_id]:
    inner = engine.inners[lord_id]
    inner.is_sleeping = False
    inner.energy_pool = 1.0
    inner.oyok[1] = 0.0
    inner.inventory["food"] = 80.0

tax_events = []
policy_events = []
food_events = []
farmer_events = []

start = time.time()
for _ in range(TICKS):
    result = engine.tick()
    for evt in result.get("economy_events", []):
        etype = evt.get("type")
        if etype == "tax_collected":
            tax_events.append(evt)
        elif etype == "policy_update":
            policy_events.append(evt)
        elif etype in ("food_stockpile", "food_ration"):
            food_events.append(evt)
        elif etype == "job_created" and evt.get("job_title") == "farmer":
            farmer_events.append(evt)
elapsed = time.time() - start

tax_rates = [t.policy.tax_rate for t in engine.territories.values()]
treasury_after_tax = [
    evt for evt in tax_events
    if evt.get("treasury_after", 0) > initial_treasury.get(evt.get("territory"), 0)
]
policy_with_snn = [
    evt for evt in policy_events
    if isinstance(evt.get("snn_signals"), dict) and evt["snn_signals"]
]

print(f"\nElapsed: {elapsed:.1f}s ({elapsed / TICKS * 1000:.0f}ms/tick)")
print(f"Tax events: {len(tax_events)}")
print(f"Policy updates: {len(policy_events)}")
print(f"Food reserve events: {len(food_events)}")
print(f"Farmer jobs: {len(farmer_events)}")
print(f"Tax rates: {min(tax_rates):.3f} ~ {max(tax_rates):.3f}")

results = [
    ("T1 tax_collected >= 1", len(tax_events) >= 1, f"events={len(tax_events)}"),
    ("T2 tax_rate in 0.05..0.30", all(0.05 <= r <= 0.30 for r in tax_rates),
     f"range={min(tax_rates):.3f}..{max(tax_rates):.3f}"),
    ("T3 treasury_after initial by tax", len(treasury_after_tax) >= 1,
     f"events={len(treasury_after_tax)}"),
    ("T4 food reserve event >= 1", len(food_events) >= 1,
     f"events={len(food_events)}"),
    ("T5 policy_update has snn_signals", len(policy_with_snn) >= 1,
     f"events={len(policy_with_snn)}"),
    ("T6 farmer job_created >= 1", len(farmer_events) >= 1,
     f"events={len(farmer_events)}"),
]

# ── T7: spending_cap 집행 검증 ──
# treasury_spending_cap=0.3이면 금고의 30%를 초과 지출할 수 없어야 한다.
# food_stockpile(source=treasury_purchase) 이벤트의 spending_cap 값이
# 해당 시점 금고의 cap 비율 이하인지 확인.
t7_ok = True
t7_violations = 0
for evt in food_events:
    if evt.get("source") != "treasury_purchase":
        continue
    spent = evt.get("treasury_spent", 0)
    cap_limit = evt.get("spending_cap", 0)
    if spent > 0 and cap_limit > 0 and spent > cap_limit + 0.01:
        t7_violations += 1
        t7_ok = False
# 최소 1건의 treasury_purchase가 있어야 의미 있는 테스트
treasury_purchases = [e for e in food_events if e.get("source") == "treasury_purchase"]
t7_has_data = len(treasury_purchases) >= 1
results.append(
    ("T7 spending_cap enforced", t7_ok and t7_has_data,
     f"purchases={len(treasury_purchases)}, violations={t7_violations}")
)

# ── T8: 영주 수면 시 통치 중단 검증 ──
# 새 엔진에서 영주를 강제 수면 → 24틱 돌린 뒤 통치 이벤트 0건 확인.
engine2 = MultiTickEngine()
for territory in engine2.territories.values():
    if territory.lord_id and territory.lord_id in engine2.inners:
        lord_inner = engine2.inners[territory.lord_id]
        lord_inner.is_sleeping = True
        lord_inner.energy_pool = 0.0
        lord_inner.sleep_ticks_remaining = 999  # 48틱 내내 수면 유지

sleep_gov_events = []
for _ in range(48):
    r2 = engine2.tick()
    for evt in r2.get("economy_events", []):
        if evt.get("type") in ("tax_collected", "food_stockpile", "food_ration", "policy_update"):
            sleep_gov_events.append(evt)

results.append(
    ("T8 sleeping lord = no governance", len(sleep_gov_events) == 0,
     f"gov_events_during_sleep={len(sleep_gov_events)}")
)

print("\n=== Results ===")
passed = 0
for name, ok, detail in results:
    if ok:
        passed += 1
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name} - {detail}")

print(f"\n{passed}/{len(results)} PASS")
if passed == len(results):
    print("ALL PASS")
else:
    print("SOME FAILED")
    sys.exit(1)
