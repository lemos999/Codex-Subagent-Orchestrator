"""Phase 16-D tests: Dynamic Reserve + Base Activation + NPC Cooldown."""
from __future__ import annotations

import sys
from collections import Counter

sys.path.insert(0, ".")

from core.multi_tick_engine import MultiTickEngine
from ontology import (
    FOOD_STOCKPILE_RESERVE_PER_PERSONA,
    NPC_FOOD_PURCHASE_COOLDOWN_TICKS,
    NPC_FOOD_TRIGGER_RESERVE_RATIO,
    PERSONA_FOOD_SAFE_STOCK,
    PUBLIC_WORKS_BASE_ACTIVATION,
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


def _set_signals(engine: MultiTickEngine, tid: str, value: float = 0.0) -> None:
    territory = engine.territories[tid]
    territory.last_snn_signals = {
        "growth": value,
        "tension": value,
        "stability": value,
    }
    territory.last_snn_signals_tick = engine.time.tick


def _prepare_food_reserve_case(engine: MultiTickEngine, tid: str = "seorim") -> None:
    territory = engine.territories[tid]
    territory.food_reserve = 0.0
    territory.treasury_gold = 3000.0
    territory.policy.food_priority = 1.0
    territory.policy.treasury_spending_cap = 0.5
    territory.last_npc_food_purchase_tick = -9999
    for pid, persona in engine.personas.items():
        if persona.territory == tid:
            engine.inners[pid].inventory["food"] = 0.0


def _events_for(events: list[dict], event_type: str, tid: str) -> list[dict]:
    return [
        ev for ev in events
        if ev.get("type") == event_type and ev.get("territory") == tid
    ]


def test_constants_phase16d() -> None:
    assert PUBLIC_WORKS_BASE_ACTIVATION == 0.04
    assert PUBLIC_WORKS_RATE_MIN == 0.03
    assert PERSONA_FOOD_SAFE_STOCK == 12.0
    assert NPC_FOOD_PURCHASE_COOLDOWN_TICKS == 48
    assert FOOD_STOCKPILE_RESERVE_PER_PERSONA == 14.0
    assert NPC_FOOD_TRIGGER_RESERVE_RATIO == 0.5


def test_territory_has_npc_cooldown_field() -> None:
    engine = MultiTickEngine(seed=42)
    for territory in engine.territories.values():
        assert hasattr(territory, "last_npc_food_purchase_tick")
        assert territory.last_npc_food_purchase_tick == -9999


def test_public_works_fires_with_zero_signal() -> None:
    engine = _setup_engine()
    tid = "seorim"
    territory = engine.territories[tid]
    territory.treasury_gold = 3000.0
    territory.quarter_tax_income = 1000.0
    _set_signals(engine, tid, value=0.0)

    events = engine._process_public_works(tid)

    assert events, events
    assert territory.policy.public_works_rate >= PUBLIC_WORKS_RATE_MIN
    assert events[0]["base_component"] == round(PUBLIC_WORKS_BASE_ACTIVATION, 3)
    assert events[0]["signal_component"] == 0.0


def test_npc_purchase_cooldown_enforced() -> None:
    engine = _setup_engine()
    tid = "seorim"
    purchase_ticks: list[int] = []

    _prepare_food_reserve_case(engine, tid)
    for tick in (24, 48, 72):
        engine.time.tick = tick
        events = engine._process_food_reserve()
        purchases = [
            ev for ev in _events_for(events, "food_stockpile", tid)
            if ev.get("source") == "treasury_purchase"
        ]
        if purchases:
            purchase_ticks.append(tick)

    assert purchase_ticks == [24, 72]
    for a, b in zip(purchase_ticks, purchase_ticks[1:]):
        assert b - a >= NPC_FOOD_PURCHASE_COOLDOWN_TICKS


def test_dynamic_reserve_target() -> None:
    engine = _setup_engine()
    tid = "seorim"
    _prepare_food_reserve_case(engine, tid)
    engine.time.tick = 24

    events = engine._process_food_reserve()

    purchases = [
        ev for ev in _events_for(events, "food_stockpile", tid)
        if ev.get("source") == "treasury_purchase"
    ]
    assert purchases, events
    residents = engine._get_territory_residents(tid)
    expected = len(residents) * FOOD_STOCKPILE_RESERVE_PER_PERSONA
    assert abs(purchases[0]["reserve_target"] - expected) < 0.01
    assert purchases[0]["trigger_ratio"] <= NPC_FOOD_TRIGGER_RESERVE_RATIO


def test_internal_procurement_priority_gate_removed() -> None:
    engine = _setup_engine()
    tid = "seorim"
    territory = engine.territories[tid]
    territory.food_reserve = 0.0
    territory.treasury_gold = 3000.0
    territory.policy.food_priority = 0.2
    territory.policy.treasury_spending_cap = 0.5
    for pid, persona in engine.personas.items():
        if persona.territory == tid:
            engine.inners[pid].inventory["food"] = PERSONA_FOOD_SAFE_STOCK + 20.0
    engine.time.tick = 24

    events = engine._process_food_reserve()

    internal = _events_for(events, "internal_food_procurement", tid)
    npc = [
        ev for ev in _events_for(events, "food_stockpile", tid)
        if ev.get("source") == "treasury_purchase"
    ]
    assert internal, events
    assert npc == []


def test_regression_deterministic_2_runs_500_ticks() -> None:
    def snapshot(seed: int) -> tuple:
        engine = _setup_engine(seed=seed)
        log = engine.run(n_ticks=500, verbose=False)
        counts = Counter()
        for tick_result in log:
            for ev in tick_result.get("economy_events", []):
                counts[ev.get("type", "unknown")] += 1
        return (
            round(sum(w.gold for w in engine.wallets.values()), 6),
            round(sum(t.treasury_gold for t in engine.territories.values()), 6),
            round(sum(t.food_reserve for t in engine.territories.values()), 6),
            counts.get("public_works", 0),
            counts.get("internal_food_procurement", 0),
            counts.get("food_stockpile", 0),
        )

    assert snapshot(42) == snapshot(42)


def run_all() -> None:
    tests = [
        test_constants_phase16d,
        test_territory_has_npc_cooldown_field,
        test_public_works_fires_with_zero_signal,
        test_npc_purchase_cooldown_enforced,
        test_dynamic_reserve_target,
        test_internal_procurement_priority_gate_removed,
        test_regression_deterministic_2_runs_500_ticks,
    ]
    passed = 0
    for test in tests:
        test()
        print(f"  PASS  {test.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} passed")


if __name__ == "__main__":
    run_all()
