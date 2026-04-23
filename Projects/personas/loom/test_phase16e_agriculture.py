"""Phase 16-E tests: Public Works candidate expansion + Food Crisis Mode."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.multi_tick_engine import MultiTickEngine
from ontology import (
    COMMUNAL_FARM_BOOST,
    FARM_EXPANSION_COST_GOLD,
    FOOD_CRISIS_COUNTER_DECAY,
    FOOD_CRISIS_FARM_THRESHOLD,
    FOOD_CRISIS_RESERVE_RATIO,
    FOOD_LABOR_NON_FARMER_RATIO,
    JOB_BASE_OUTPUT,
    PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD,
    PUBLIC_WORKS_LOW_GOLD_THRESHOLD,
)


def _prime_public_works(engine: MultiTickEngine, tid: str) -> None:
    territory = engine.territories[tid]
    territory.last_snn_signals = {"growth": 0.8, "tension": 0.7, "stability": 0.5}
    territory.last_snn_signals_tick = engine.time.tick
    territory.treasury_gold = 10000.0
    territory.quarter_tax_income = 1000.0
    for pid, persona in engine.personas.items():
        if persona.territory == tid:
            engine.inners[pid].is_sleeping = False
            engine.inners[pid].vitality = 1.0
            engine.inners[pid].consecutive_hunger_ticks = 50
            engine.personas[pid].employment_id = None
    residents = [p for p in engine.personas.values() if p.territory == tid]
    territory.food_reserve = len(residents) * 14.0 * 0.2


def test_constants_phase16e() -> None:
    assert PUBLIC_WORKS_LOW_GOLD_THRESHOLD == 300.0
    assert PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD == 12
    assert FOOD_LABOR_NON_FARMER_RATIO == 0.7
    assert COMMUNAL_FARM_BOOST == 0.3
    assert FOOD_CRISIS_FARM_THRESHOLD == 3.0
    assert FARM_EXPANSION_COST_GOLD == 500.0
    assert FOOD_CRISIS_RESERVE_RATIO == 0.4
    assert FOOD_CRISIS_COUNTER_DECAY == 0.5


def test_territory_has_farm_fields() -> None:
    engine = MultiTickEngine(seed=42)
    for _tid, territory in engine.territories.items():
        assert hasattr(territory, "communal_farms")
        assert territory.communal_farms == 1
        assert hasattr(territory, "food_crisis_counter")
        assert territory.food_crisis_counter == 0.0


def test_low_gold_hungry_eligible_for_public_works() -> None:
    engine = MultiTickEngine(seed=42)
    pid = next(
        candidate
        for candidate, candidate_persona in engine.personas.items()
        if candidate != engine.territories[candidate_persona.territory].lord_id
    )
    persona = engine.personas[pid]
    persona.employment_id = "dummy_emp"
    engine.wallets[pid].gold = 100.0
    engine.inners[pid].consecutive_hunger_ticks = 20
    engine.inners[pid].is_sleeping = False
    engine.inners[pid].vitality = 1.0
    tid = persona.territory
    for other_pid, other_persona in engine.personas.items():
        if other_pid != pid and other_persona.territory == tid:
            engine.inners[other_pid].is_sleeping = True
    territory = engine.territories[tid]
    territory.last_snn_signals = {"growth": 0.3, "tension": 0.2, "stability": 0.1}
    territory.last_snn_signals_tick = engine.time.tick
    territory.treasury_gold = max(territory.treasury_gold, 5000.0)
    territory.quarter_tax_income = 1000.0

    events = engine._process_public_works(tid)
    pw = [e for e in events if e.get("type") == "public_works"]

    assert any(
        e["persona"] == pid and e.get("from_pool") == "low_gold_hungry"
        for e in pw
    ), f"low_gold_hungry candidate was not selected: {events}"


def test_food_crisis_mode_produces_food_only() -> None:
    engine = MultiTickEngine(seed=42)
    tid = next(
        territory_id
        for territory_id, territory in engine.territories.items()
        if sum(
            1
            for pid, persona in engine.personas.items()
            if persona.territory == territory_id and pid != territory.lord_id
        ) >= 3
    )
    territory = engine.territories[tid]
    _prime_public_works(engine, tid)

    events = engine._process_public_works(tid)
    pw = [e for e in events if e.get("type") == "public_works"]

    assert len(pw) >= 2, f"expected at least 2 food crisis public works, got {len(pw)}: {events}"
    for e in pw:
        assert e["produced_type"] == "food", f"non-food production in crisis mode: {e}"
        assert e["food_crisis_active"] is True


def test_non_farmer_food_labor_penalty() -> None:
    engine = MultiTickEngine(seed=42)
    tid, territory = next(iter(engine.territories.items()))
    _prime_public_works(engine, tid)

    events = engine._process_public_works(tid)
    pw = [e for e in events if e.get("type") == "public_works"]
    farmer_base = JOB_BASE_OUTPUT.get("farmer", 2.0)
    for e in pw:
        farms = e["communal_farms"]
        mult = 1.0 + farms * COMMUNAL_FARM_BOOST
        max_farmer = farmer_base * 24 * mult
        max_nonfarmer = max_farmer * FOOD_LABOR_NON_FARMER_RATIO
        assert e["produced_total"] <= max_farmer + 0.01
        assert (
            abs(e["produced_total"] - max_farmer) < 0.01
            or e["produced_total"] <= max_nonfarmer + 0.01
        )


def test_communal_farm_boost_applied() -> None:
    engine = MultiTickEngine(seed=42)
    tid, territory = next(iter(engine.territories.items()))
    _prime_public_works(engine, tid)
    territory.communal_farms = 2

    events = engine._process_public_works(tid)
    pw = [
        e for e in events
        if e.get("type") == "public_works" and e["produced_type"] == "food"
    ]

    assert pw, "no food public works events"
    for e in pw:
        expected_mult = 1.0 + 2 * COMMUNAL_FARM_BOOST
        assert abs(e["farm_multiplier"] - expected_mult) < 0.01


def test_farm_expansion_triggers_after_3_crises() -> None:
    engine = MultiTickEngine(seed=42)
    engine.time.tick = 24
    tid, territory = next(iter(engine.territories.items()))
    territory.treasury_gold = 1000.0
    territory.food_crisis_counter = FOOD_CRISIS_FARM_THRESHOLD
    initial_farms = territory.communal_farms

    events = engine._process_farm_expansion()

    assert any(e["type"] == "farm_expansion" and e["territory"] == tid for e in events), events
    assert territory.communal_farms == initial_farms + 1
    assert territory.food_crisis_counter == 0.0
    assert territory.treasury_gold == 500.0


def test_regression_deterministic_2_runs_500_ticks() -> None:
    def snapshot(seed: int) -> dict[str, float]:
        eng = MultiTickEngine(seed=seed)
        for _ in range(500):
            eng.tick()
        return {
            "total_gold": sum(w.gold for w in eng.wallets.values()),
            "total_treasury": sum(t.treasury_gold for t in eng.territories.values()),
            "total_food": sum(t.food_reserve for t in eng.territories.values()),
            "pw_count": sum(1 for e in eng.event_log if e.get("type") == "public_works"),
            "skip_count": sum(
                1 for e in eng.event_log if e.get("type") == "public_works_skip_reason"
            ),
            "ip_count": sum(
                1 for e in eng.event_log if e.get("type") == "internal_food_procurement"
            ),
            "farm_count": sum(
                1 for e in eng.event_log if e.get("type") == "farm_expansion"
            ),
        }

    a = snapshot(42)
    b = snapshot(42)
    for k in a:
        assert abs(a[k] - b[k]) < 1e-6, f"determinism broken on {k}: {a[k]} vs {b[k]}"


if __name__ == "__main__":
    import traceback

    tests = [
        test_constants_phase16e,
        test_territory_has_farm_fields,
        test_low_gold_hungry_eligible_for_public_works,
        test_food_crisis_mode_produces_food_only,
        test_non_farmer_food_labor_penalty,
        test_communal_farm_boost_applied,
        test_farm_expansion_triggers_after_3_crises,
        test_regression_deterministic_2_runs_500_ticks,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
            passed += 1
        except Exception as exc:
            print(f"FAIL {test.__name__}: {exc}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{len(tests)} passed, {failed} failed")
    if failed:
        sys.exit(1)
