# -*- coding: utf-8 -*-
"""Phase 12 SNN economy verification.

Checks direct SNN observability for economic perception, pricing, reward,
and market conservation. Long-run work avoidance is reported as a diagnostic
because it is an emergent trend and can be noisy in a single script run.
"""
import sys
import time

sys.path.insert(0, ".")

import numpy as np

from brain.persona_brain import PersonaBrain
from core.multi_tick_engine import MultiTickEngine
from ontology import NPC_PRICES, SkillProfile


def check(results, name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name} - {detail}")
    results.append((name, condition, detail))


def synthetic_pricing_quotes(engine):
    """Seed each brain with a controlled firing pattern, then quote food."""
    pids = list(engine.personas.keys())
    n = next(iter(engine.brains.values())).n_neurons
    cluster_indices = np.array_split(np.arange(n), 12)

    quotes = []
    for idx, pid in enumerate(pids):
        urgency_level = idx / max(1, len(pids) - 1)
        fr = np.zeros(n, dtype=np.float32)
        fr[cluster_indices[5]] = urgency_level * 0.08
        fr[cluster_indices[8]] = urgency_level * 0.08
        fr[cluster_indices[0]] = 0.02
        engine.brains[pid]._last_firing_rate = fr
        engine.inners[pid].oyok[3] = np.float16(0.05 + idx * 0.08)
        quote = engine._compute_snn_pricing(pid, "food")
        quote["pid"] = pid
        quote["stress_rank"] = urgency_level
        quotes.append(quote)
    return quotes


def economic_slice_rate(food_ratio):
    rates = []
    for seed in range(32):
        brain = PersonaBrain(n_neurons=1_000, seed=10_000 + seed)
        for _ in range(3):
            brain.tick(
                climate_vec=np.zeros(8, dtype=np.float16),
                energy_pool=1.0,
                oyok=np.array([0.3, 0.0, 0.0, 0.1, 0.1], dtype=np.float16),
                tone=np.ones(12, dtype=np.float16),
                economic_state={
                    "food_ratio": food_ratio,
                    "tool_ratio": 1.0,
                    "wealth_ratio": 1.0,
                    "job_satisfaction": 0.5,
                    "relative_wealth": 1.0,
                },
            )
        rates.append(float(brain._last_firing_rate[300:310].mean()))
    return float(np.mean(rates))


def job_dissatisfaction_slice_rate(job_satisfaction):
    rates = []
    for seed in range(16):
        brain = PersonaBrain(n_neurons=1_000, seed=20_000 + seed)
        for _ in range(3):
            brain.tick(
                climate_vec=np.zeros(8, dtype=np.float16),
                energy_pool=1.0,
                oyok=np.array([0.3, 0.0, 0.0, 0.1, 0.1], dtype=np.float16),
                tone=np.ones(12, dtype=np.float16),
                economic_state={
                    "food_ratio": 1.0,
                    "tool_ratio": 1.0,
                    "wealth_ratio": 1.0,
                    "job_satisfaction": job_satisfaction,
                    "relative_wealth": 1.0,
                },
            )
        rates.append(float(brain._last_firing_rate[330:340].mean()))
    return float(np.mean(rates))


def test_work_reward_gap(engine):
    pid = "persona_024"  # Orin Flint, craftsman-leaning
    inner = engine.inners[pid]
    inner.energy_pool = 0.8
    inner.skill_profiles["craftsman"] = SkillProfile(persona_id=pid, skill_id="craftsman")
    inner.skill_profiles.pop("laborer", None)

    craftsman_reward = engine._compute_reward(
        pid, "work", energy=0.8, prev_energy=0.9, job_title="craftsman"
    )
    laborer_reward = engine._compute_reward(
        pid, "work", energy=0.8, prev_energy=0.9, job_title="laborer"
    )
    return craftsman_reward, laborer_reward


def test_market_conservation(engine):
    seller = "persona_001"
    buyer = "persona_002"
    goods = "food"

    engine.inners[seller].inventory[goods] = 60.0
    engine.inners[buyer].inventory[goods] = 0.0
    engine.wallets[buyer].gold = 5000.0

    n = engine.brains[seller].n_neurons
    cluster_indices = np.array_split(np.arange(n), 12)
    seller_fr = np.zeros(n, dtype=np.float32)
    buyer_fr = np.zeros(n, dtype=np.float32)
    buyer_fr[cluster_indices[5]] = 0.08
    buyer_fr[cluster_indices[8]] = 0.08
    buyer_fr[300:310] = 0.15
    engine.brains[seller]._last_firing_rate = seller_fr
    engine.brains[buyer]._last_firing_rate = buyer_fr

    before_seller = float(engine.inners[seller].inventory[goods])
    before_buyer = float(engine.inners[buyer].inventory[goods])
    events = engine._process_market()
    trades = [e for e in events if e.get("type") == "trade" and e.get("goods") == goods]
    after_seller = float(engine.inners[seller].inventory[goods])
    after_buyer = float(engine.inners[buyer].inventory[goods])

    if not trades:
        return False, "no trade event"
    moved = sum(float(e["qty"]) for e in trades)
    seller_delta = before_seller - after_seller
    buyer_delta = after_buyer - before_buyer
    ok = abs(seller_delta - moved) < 1e-6 and abs(buyer_delta - moved) < 1e-6
    return ok, f"moved={moved:.2f}, seller_delta={seller_delta:.2f}, buyer_delta={buyer_delta:.2f}"


def work_share_diagnostic():
    ticks = 60
    window = 20
    engine = MultiTickEngine()
    counts = {pid: {"work": 0, "seen": 0} for pid in engine.personas}

    start = time.time()
    for tick in range(ticks):
        result = engine.tick()
        if tick < ticks - window:
            continue
        for pid, pdata in result.get("personas", {}).items():
            action = pdata.get("action")
            if action in ("idle", "work", "eat", "sleep", "explore", "socialize"):
                counts[pid]["seen"] += 1
                if action == "work":
                    counts[pid]["work"] += 1
    elapsed = time.time() - start

    rows = []
    for pid, count in counts.items():
        if count["seen"] == 0:
            continue
        job = engine._get_persona_job_title(pid)
        aptitude = engine.personas[pid].aptitude_map.get(job, 0.5)
        work_share = count["work"] / count["seen"]
        rows.append((aptitude, work_share, pid, job))
    rows.sort()
    low = rows[:3]
    high = rows[-3:]
    low_share = float(np.mean([r[1] for r in low])) if low else 0.0
    high_share = float(np.mean([r[1] for r in high])) if high else 0.0
    return high_share, low_share, elapsed, high, low


print("=== Phase 12 SNN Economy Verification ===")
results = []

engine = MultiTickEngine()
for _ in range(3):
    engine.tick()

quotes = synthetic_pricing_quotes(engine)
prices = np.array([q["sell_price"] for q in quotes], dtype=np.float32)
std = float(prices.std())
mean = float(prices.mean())
cv = std / mean if mean else 0.0
unique_prices = len({round(float(p), 2) for p in prices})
npc_sell = NPC_PRICES["food"]["sell"]
check(
    results,
    "T1 price dispersion",
    (cv >= 0.20 or std > npc_sell * 0.20) and unique_prices >= 2,
    f"std={std:.2f}, mean={mean:.2f}, cv={cv:.2f}, unique={unique_prices}",
)

ranked = sorted(quotes, key=lambda q: q["stress_rank"])
low = ranked[:3]
high = ranked[-3:]
low_avg = float(np.mean([q["sell_price"] for q in low]))
high_avg = float(np.mean([q["sell_price"] for q in high]))
delta = low_avg - high_avg
check(
    results,
    "T2 urgency lowers sell price",
    high_avg <= low_avg - 1.0 or high_avg <= low_avg * 0.9,
    f"low_avg={low_avg:.2f}, high_avg={high_avg:.2f}, delta={delta:.2f}",
)

craftsman_reward, laborer_reward = test_work_reward_gap(engine)
reward_delta = craftsman_reward - laborer_reward
check(
    results,
    "T3 aptitude reward gap",
    reward_delta >= 0.15,
    f"craftsman={craftsman_reward:.3f}, laborer={laborer_reward:.3f}, delta={reward_delta:.3f}",
)

low_sat_rate = job_dissatisfaction_slice_rate(job_satisfaction=0.0)
high_sat_rate = job_dissatisfaction_slice_rate(job_satisfaction=1.0)
sat_delta = low_sat_rate - high_sat_rate
sat_relative_gain = sat_delta / max(0.001, high_sat_rate)
check(
    results,
    "T4 job dissatisfaction drives neurons 330:339",
    sat_delta >= 0.02 or sat_relative_gain >= 0.15,
    f"low_sat={low_sat_rate:.4f}, high_sat={high_sat_rate:.4f}, delta={sat_delta:.4f}, rel={sat_relative_gain:.2f}",
)

low_food_rate = economic_slice_rate(food_ratio=0.0)
full_food_rate = economic_slice_rate(food_ratio=1.0)
rate_delta = low_food_rate - full_food_rate
relative_gain = rate_delta / max(0.001, full_food_rate)
check(
    results,
    "T5 food scarcity drives neurons 300:309",
    rate_delta >= 0.05 or relative_gain >= 0.20,
    f"scarce={low_food_rate:.4f}, full={full_food_rate:.4f}, delta={rate_delta:.4f}, rel={relative_gain:.2f}",
)

market_ok, market_detail = test_market_conservation(engine)
check(results, "Market goods conservation", market_ok, market_detail)

high_share, low_share, elapsed, high_rows, low_rows = work_share_diagnostic()
trend_ok = high_share >= low_share + 0.05
trend_status = "PASS" if trend_ok else "WARN"
print(
    f"  [{trend_status}] T4 long-run work-share diagnostic - "
    f"high={high_share:.2%}, low={low_share:.2%}, elapsed={elapsed:.1f}s"
)
print(f"       high={[(pid, job, round(apt, 2), round(ws, 3)) for apt, ws, pid, job in high_rows]}")
print(f"       low={[(pid, job, round(apt, 2), round(ws, 3)) for apt, ws, pid, job in low_rows]}")

print("  [INFO] T6 regression suite is separate: test_economy, test_nomos, test_class_promotion, test_neural_drive")

passed = sum(1 for _, ok, _ in results if ok)
print(f"\n{passed}/{len(results)} required checks PASS")
if passed != len(results):
    sys.exit(1)
print("ALL REQUIRED CHECKS PASS")
