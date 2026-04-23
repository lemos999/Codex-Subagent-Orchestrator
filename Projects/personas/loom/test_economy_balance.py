# -*- coding: utf-8 -*-
"""Phase 14 economy/rebellion balance verification.

Run:
    py test_economy_balance.py
"""
from __future__ import annotations

import sys
import time

sys.path.insert(0, ".")

import numpy as np

from core.multi_tick_engine import MultiTickEngine
from ontology import NPC_PRICES, Relationship


def total_gold(engine: MultiTickEngine) -> float:
    wallets = sum(wallet.total_in_gold() for wallet in engine.wallets.values())
    treasuries = sum(t.treasury_gold for t in engine.territories.values())
    return wallets + treasuries


def prime_balance_run(engine: MultiTickEngine) -> None:
    for territory in engine.territories.values():
        residents = [
            pid for pid, persona in engine.personas.items()
            if persona.territory == territory.id
        ]
        territory.policy.food_priority = 1.0
        territory.policy.stockpile_target = 0.1
        territory.policy.treasury_spending_cap = 0.1
        territory.food_reserve = float(len(residents) * 24)
        if territory.lord_id:
            lord_inner = engine.inners[territory.lord_id]
            lord_inner.tone[0] = np.float16(2.0)
            lord_inner.tone[10] = np.float16(2.0)

    for pid, inner in engine.inners.items():
        inner.is_sleeping = False
        inner.energy_pool = 1.0
        inner.oyok[0] = np.float16(0.2)
        inner.oyok[1] = np.float16(0.0)
        inner.inventory["food"] = 1200.0
        if pid in engine.wallets:
            engine.wallets[pid].gold = 2000.0


def run_balance_1000() -> dict:
    engine = MultiTickEngine()
    prime_balance_run(engine)

    initial_gold = total_gold(engine)
    farmer_jobs_at_500 = 0
    start = time.time()
    for tick in range(1, 1001):
        engine.tick()
        if tick == 500:
            farmer_jobs_at_500 = sum(
                1 for job in engine.jobs.values() if job.title == "farmer"
            )
    elapsed = time.time() - start
    final_gold = total_gold(engine)
    farmer_jobs = sum(1 for job in engine.jobs.values() if job.title == "farmer")
    return {
        "engine": engine,
        "initial_gold": initial_gold,
        "final_gold": final_gold,
        "gold_retained": final_gold / initial_gold if initial_gold else 0.0,
        "farmer_jobs_at_500": farmer_jobs_at_500,
        "farmer_jobs": farmer_jobs,
        "elapsed": elapsed,
        "ms_per_tick": elapsed / 1000 * 1000,
    }


def quote(urgency: float, motivation: float) -> dict:
    return {
        "sell_price": 5.0,
        "buy_max": 20.0,
        "urgency": urgency,
        "motivation": motivation,
        "stress_rate": 0.0,
        "fatigue_rate": 0.0,
        "drive_rate": motivation / 10.0,
        "economic_rate": urgency / 6.0,
        "greed": 0.0,
    }


def test_npc_sell_gold_revenue() -> tuple[bool, str]:
    engine = MultiTickEngine()
    pid = "persona_001"
    engine.territories[engine.personas[pid].territory].policy.tax_rate = 0.30
    engine.inners[pid].inventory["material"] = 20.0
    engine.inners[pid].inventory["food"] = 30.0
    engine.wallets[pid].gold = 1000.0
    engine._pricing_cache = {
        pid: {
            "food": quote(0.0, 0.0),
            "material": quote(0.8, 0.1),
            "tool": quote(0.0, 0.0),
            "medicine": quote(0.0, 0.0),
            "knowledge": quote(0.0, 0.0),
        }
    }

    events = engine._process_npc_shop()
    sell = next(
        (evt for evt in events
         if evt.get("type") == "npc_sell" and evt.get("goods") == "material"),
        None,
    )
    if not sell:
        return False, "no npc_sell material event"
    expected = NPC_PRICES["material"]["sell"] * 5 * 1.15
    ok = sell["revenue"] > 0 and abs(sell["revenue"] - expected) < 1e-6
    return ok, f"revenue={sell['revenue']:.2f}, expected={expected:.2f}"


def test_grievance_accumulates() -> tuple[bool, str]:
    engine = MultiTickEngine()
    territory = engine.territories["seorim"]
    territory.policy.tax_rate = 0.30
    territory.tax_rate = 0.30

    for pid, persona in engine.personas.items():
        if persona.territory != "seorim" or pid == territory.lord_id:
            continue
        inner = engine.inners[pid]
        inner.inventory["food"] = 0.0
        inner.oyok[0] = np.float16(0.8)

    for tick in range(24, 201, 24):
        engine.time.tick = tick
        engine._territory_residents_cache = None
        engine._update_grievances()

    grievous = [
        pid for pid, persona in engine.personas.items()
        if persona.territory == "seorim"
        and pid != territory.lord_id
        and engine.inners[pid].grievance > 0.5
    ]
    return len(grievous) >= 1, f"residents={len(grievous)}"


def test_exodus_event_and_population_shift() -> tuple[bool, str]:
    engine = MultiTickEngine()
    pid = "persona_002"
    from_tid = engine.personas[pid].territory
    to_tid = "ironridge"
    engine.territories[from_tid].policy.tax_rate = 0.30
    engine.territories[to_tid].policy.tax_rate = 0.05
    engine.inners[pid].grievance = 1.0
    engine.inners[pid].is_sleeping = False
    rel_key = Relationship(persona_a=pid, persona_b="persona_001").key()
    rel_before = engine.relationships.get(rel_key)
    trust_before = rel_before.trust if rel_before else None
    familiarity_before = rel_before.familiarity if rel_before else None

    before_from = sum(1 for p in engine.personas.values() if p.territory == from_tid)
    before_to = sum(1 for p in engine.personas.values() if p.territory == to_tid)

    old_random = np.random.random
    np.random.random = lambda: 0.0
    try:
        result = engine.tick()
    finally:
        np.random.random = old_random

    exodus = [
        evt for evt in result.get("economy_events", [])
        if evt.get("type") == "exodus" and evt.get("persona") == pid
    ]
    after_from = sum(1 for p in engine.personas.values() if p.territory == from_tid)
    after_to = sum(1 for p in engine.personas.values() if p.territory == to_tid)
    rel_after = engine.relationships.get(rel_key)
    relation_kept = (
        rel_after is rel_before
        and (rel_after is None or (
            rel_after.trust == trust_before
            and rel_after.familiarity == familiarity_before
        ))
    )
    ok = (
        len(exodus) >= 1
        and after_from == before_from - 1
        and after_to == before_to + 1
        and relation_kept
    )
    return ok, (
        f"events={len(exodus)}, from={before_from}->{after_from}, "
        f"to={before_to}->{after_to}, relation_kept={relation_kept}"
    )


def report(results: list[tuple[str, bool, str]]) -> None:
    passed = 0
    print("\n=== Phase 14 Economy Balance Results ===")
    for name, ok, detail in results:
        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name} - {detail}")
    print(f"\n{passed}/{len(results)} PASS")
    if passed != len(results):
        raise SystemExit(1)
    print("ALL PASS")


def main() -> None:
    print("=== Phase 14 Economy/Rebellion Verification ===")
    balance = run_balance_1000()
    npc_ok, npc_detail = test_npc_sell_gold_revenue()
    grievance_ok, grievance_detail = test_grievance_accumulates()
    exodus_ok, exodus_detail = test_exodus_event_and_population_shift()

    print(
        "\n1000 tick observations: "
        f"gold_retained={balance['gold_retained'] * 100:.1f}%, "
        f"farmers={balance['farmer_jobs']}, "
        f"ms/tick={balance['ms_per_tick']:.1f}"
    )

    results = [
        (
            "T1 gold retained > 70% after 1000 ticks",
            balance["gold_retained"] > 0.70,
            f"{balance['gold_retained'] * 100:.1f}%",
        ),
        (
            "T2 farmer jobs >= 2 by 500 ticks",
            balance["farmer_jobs_at_500"] >= 2,
            f"farmers_at_500={balance['farmer_jobs_at_500']}",
        ),
        ("T3 NPC sell gold revenue > 0", npc_ok, npc_detail),
        ("T4 grievance > 0.5 under 0.30 tax", grievance_ok, grievance_detail),
        ("T5 exodus event within high/low tax contrast", exodus_ok, exodus_detail),
        ("T6 exodus shifts territory population", exodus_ok, exodus_detail),
    ]
    report(results)


if __name__ == "__main__":
    main()
