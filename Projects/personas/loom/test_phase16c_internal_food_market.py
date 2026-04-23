"""Phase 16-C: Internal Food Market verification."""
from __future__ import annotations

import sys
from collections import Counter

sys.path.insert(0, ".")

from core.multi_tick_engine import MultiTickEngine
from ontology.layers import (
    FOOD_STOCKPILE_RESERVE_THRESHOLD,
    HUNGER_TRIGGER_THRESHOLD,
    INTERNAL_FOOD_PRICE_RATIO,
    NPC_PRICES,
    PERSONA_FOOD_SAFE_STOCK,
    PUBLIC_WORKS_FARMER_BIAS,
    PUBLIC_WORKS_RATE_MIN,
)


def _setup_engine(seed: int = 42) -> MultiTickEngine:
    engine = MultiTickEngine(seed=seed)
    for pid, inner in engine.inners.items():
        inner.is_sleeping = False
        inner.vitality = 1.0
        inner.consecutive_hunger_ticks = 0
        engine.personas[pid].employment_id = None
    return engine


def _territory_with_seller(engine: MultiTickEngine) -> tuple[str, object, str]:
    tid = "seorim"
    territory = engine.territories[tid]
    for pid, persona in engine.personas.items():
        if persona.territory == tid and pid != territory.lord_id:
            return tid, territory, pid
    raise AssertionError("no non-lord resident available")


def _reset_food(engine: MultiTickEngine, tid: str, amount: float = PERSONA_FOOD_SAFE_STOCK) -> None:
    for pid, persona in engine.personas.items():
        if persona.territory == tid:
            engine.inners[pid].inventory["food"] = amount


def _inject_signals(
    engine: MultiTickEngine,
    tid: str,
    *,
    growth: float = 0.0,
    tension: float = 0.0,
    stability: float = 0.0,
) -> None:
    territory = engine.territories[tid]
    territory.last_snn_signals = {
        "growth": growth,
        "tension": tension,
        "stability": stability,
    }
    territory.last_snn_signals_tick = engine.time.tick


def test_internal_procurement_from_farmer() -> None:
    engine = _setup_engine()
    tid, territory, seller = _territory_with_seller(engine)
    _reset_food(engine, tid)
    territory.treasury_gold = 1000.0
    territory.food_reserve = 0.0
    engine.inners[seller].inventory["food"] = PERSONA_FOOD_SAFE_STOCK + 20.0
    wallet_before = engine.wallets[seller].gold

    procured, events = engine._process_internal_food_procurement(tid, target_qty=10.0)

    expected_cost = 10.0 * NPC_PRICES["food"]["buy"] * INTERNAL_FOOD_PRICE_RATIO
    assert abs(procured - 10.0) < 1e-6
    assert len(events) == 1
    assert events[0]["type"] == "internal_food_procurement"
    assert events[0]["territory"] == tid
    assert events[0]["seller"] == seller
    assert abs(engine.wallets[seller].gold - (wallet_before + expected_cost)) < 1e-6
    assert abs(engine.inners[seller].inventory["food"] - (PERSONA_FOOD_SAFE_STOCK + 10.0)) < 1e-6
    assert abs(territory.food_reserve - 10.0) < 1e-6
    assert abs(territory.internal_food_procured_total - 10.0) < 1e-6


def test_no_surplus_no_procurement() -> None:
    engine = _setup_engine()
    tid, territory, seller = _territory_with_seller(engine)
    territory.treasury_gold = 1000.0

    assert engine._process_internal_food_procurement(tid, target_qty=0.0) == (0.0, [])
    assert engine._process_internal_food_procurement("missing", target_qty=10.0) == (0.0, [])

    _reset_food(engine, tid)
    procured, events = engine._process_internal_food_procurement(tid, target_qty=10.0)
    assert procured == 0.0 and events == []

    engine.inners[seller].inventory["food"] = PERSONA_FOOD_SAFE_STOCK + 10.0
    engine.inners[seller].is_sleeping = True
    procured, events = engine._process_internal_food_procurement(tid, target_qty=10.0)
    assert procured == 0.0 and events == []

    engine.inners[seller].is_sleeping = False
    engine.inners[seller].vitality = 0.0
    procured, events = engine._process_internal_food_procurement(tid, target_qty=10.0)
    assert procured == 0.0 and events == []


def test_procurement_respects_treasury() -> None:
    engine = _setup_engine()
    tid, territory, seller = _territory_with_seller(engine)
    _reset_food(engine, tid)
    unit_price = NPC_PRICES["food"]["buy"] * INTERNAL_FOOD_PRICE_RATIO
    territory.treasury_gold = unit_price * 3.0
    engine.inners[seller].inventory["food"] = PERSONA_FOOD_SAFE_STOCK + 100.0

    procured, events = engine._process_internal_food_procurement(tid, target_qty=100.0)

    assert abs(procured - 3.0) < 1e-6
    assert len(events) == 1
    assert territory.treasury_gold >= -1e-6
    assert abs(territory.treasury_gold) < 1e-6
    assert abs(territory.food_reserve - 3.0) < 1e-6


def test_food_stockpile_prefers_internal_over_npc() -> None:
    engine = _setup_engine()
    tid, territory, seller = _territory_with_seller(engine)
    _reset_food(engine, tid)
    engine.time.tick = 24
    territory.food_reserve = 0.0
    territory.treasury_gold = 2000.0
    territory.policy.food_priority = 1.0
    territory.policy.treasury_spending_cap = 0.5
    engine.inners[seller].inventory["food"] = PERSONA_FOOD_SAFE_STOCK + 80.0

    events = engine._process_food_reserve()

    internal_events = [
        ev for ev in events
        if ev.get("type") == "internal_food_procurement" and ev.get("territory") == tid
    ]
    npc_events = [
        ev for ev in events
        if ev.get("type") == "food_stockpile" and ev.get("source") == "treasury_purchase"
        and ev.get("territory") == tid
    ]
    assert internal_events, events
    assert npc_events == []
    # Phase 16-D: reserve_target = residents * FOOD_STOCKPILE_RESERVE_PER_PERSONA.
    # The contract now checks that internal procurement happened without NPC
    # mixing, rather than comparing against the old fixed threshold.
    assert territory.food_reserve > 0.0
    total_internal_qty = sum(float(ev.get("qty", 0.0)) for ev in internal_events)
    assert abs(territory.food_reserve - total_internal_qty) < 1e-6


def test_hunger_pressure_raises_rate() -> None:
    engine = _setup_engine()
    tid, territory, _seller = _territory_with_seller(engine)
    territory.treasury_gold = 3000.0
    territory.quarter_tax_income = 1000.0

    _inject_signals(engine, tid, growth=0.0, tension=0.0, stability=0.0)
    low_events = engine._process_public_works(tid)
    low_rate = territory.policy.public_works_rate

    for pid, persona in engine.personas.items():
        if persona.territory == tid:
            engine.inners[pid].consecutive_hunger_ticks = 50
    _inject_signals(engine, tid, growth=0.0, tension=0.0, stability=0.0)
    high_events = engine._process_public_works(tid)
    high_rate = territory.policy.public_works_rate

    assert low_rate >= PUBLIC_WORKS_RATE_MIN
    assert high_events, high_events
    assert high_rate > low_rate
    assert high_rate >= PUBLIC_WORKS_RATE_MIN


def test_farmer_bias_selection() -> None:
    engine = _setup_engine(seed=42)
    tid, territory, farmer_pid = _territory_with_seller(engine)
    territory.treasury_gold = 5000.0
    territory.quarter_tax_income = 1000.0

    for pid, persona in engine.personas.items():
        if persona.territory == tid:
            engine.inners[pid].consecutive_hunger_ticks = 72
            persona.aptitude_map = {
                "farmer": 0.1, "laborer": 0.9, "craftsman": 0.1,
                "healer": 0.1, "scholar": 0.1, "guard": 0.1,
            }
    engine.personas[farmer_pid].aptitude_map = {
        "farmer": 1.0, "laborer": 0.1, "craftsman": 0.1,
        "healer": 0.1, "scholar": 0.1, "guard": 0.1,
    }
    assert engine._get_persona_job_title(farmer_pid) == "farmer"
    assert engine._weighted_sample_without_replacement(
        [farmer_pid, "non_farmer"],
        [PUBLIC_WORKS_FARMER_BIAS, 1.0],
        1,
    ) == [farmer_pid]

    _inject_signals(engine, tid, growth=1.0, tension=1.0, stability=1.0)
    events = engine._process_public_works(tid)

    assert events, events
    assert events[0]["farmer_bias_active"] is True
    assert events[0]["hunger_pressure"] >= HUNGER_TRIGGER_THRESHOLD
    assert events[0]["persona"] == farmer_pid


def test_determinism_seed() -> None:
    def run_snapshot() -> tuple:
        engine = _setup_engine(seed=42)
        log = engine.run(n_ticks=200, verbose=False)
        counts = Counter()
        for tick_result in log:
            for ev in tick_result.get("economy_events", []):
                counts[ev.get("type", "unknown")] += 1
        return (
            round(sum(w.gold for w in engine.wallets.values()), 6),
            tuple(round(t.treasury_gold, 6) for t in engine.territories.values()),
            tuple(round(t.food_reserve, 6) for t in engine.territories.values()),
            tuple(sorted(counts.items())),
        )

    assert run_snapshot() == run_snapshot()


def run_all() -> None:
    tests = [
        test_internal_procurement_from_farmer,
        test_no_surplus_no_procurement,
        test_procurement_respects_treasury,
        test_food_stockpile_prefers_internal_over_npc,
        test_hunger_pressure_raises_rate,
        test_farmer_bias_selection,
        test_determinism_seed,
    ]
    passed = 0
    for test in tests:
        test()
        print(f"  PASS  {test.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} passed")


if __name__ == "__main__":
    run_all()
