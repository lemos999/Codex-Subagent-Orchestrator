"""
Phase 12-B verification: pricing cache and NPC SNN behavior.

Run:
    py test_phase12b_perf_npc.py
"""
from __future__ import annotations

from core.multi_tick_engine import MultiTickEngine, NPC_PRICES


GOODS = ["food", "material", "tool", "medicine", "knowledge"]


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


def prime_cache(engine: MultiTickEngine, pid: str, **overrides: dict) -> None:
    engine._pricing_cache = {
        pid: {goods: quote(0.0, 0.0) for goods in GOODS}
    }
    engine._pricing_cache[pid].update(overrides)


def quiet_needs(engine: MultiTickEngine, pid: str) -> None:
    inner = engine.inners[pid]
    inner.is_sleeping = False
    inner.inventory.update({
        "food": 30,
        "material": 0,
        "tool": 1,
        "medicine": 1,
        "knowledge": 0,
    })
    inner.equipped_tool_durability = 100
    inner.vitality = 1.0
    engine.wallets[pid].gold = 2000.0


def test_high_motivation_suppresses_npc_sell() -> None:
    engine = MultiTickEngine()
    pid = "persona_001"
    quiet_needs(engine, pid)
    engine.inners[pid].inventory["material"] = 20
    prime_cache(engine, pid, material=quote(0.9, 0.8))

    events = engine._process_npc_shop()

    sells = [
        e for e in events
        if e.get("type") == "npc_sell" and e.get("goods") == "material"
    ]
    assert not sells, sells
    assert engine.inners[pid].inventory["material"] == 20


def test_high_urgency_npc_sell_uses_five_unit_cap_and_fields() -> None:
    engine = MultiTickEngine()
    pid = "persona_001"
    quiet_needs(engine, pid)
    engine.inners[pid].inventory["material"] = 20
    prime_cache(engine, pid, material=quote(0.8, 0.1))

    events = engine._process_npc_shop()

    sell = next(
        e for e in events
        if e.get("type") == "npc_sell" and e.get("goods") == "material"
    )
    assert sell["qty"] == 5
    territory = engine.territories[engine.personas[pid].territory]
    expected_bonus = 1.0 + territory.policy.tax_rate * 0.5
    expected_revenue = NPC_PRICES["material"]["sell"] * 5 * expected_bonus
    assert abs(sell["revenue"] - expected_revenue) < 1e-6, (
        f"{sell['revenue']} != {expected_revenue}"
    )
    assert sell["motivation"] == 0.1
    assert sell["urgency"] == 0.8
    assert sell["surplus"] == 10
    assert sell["stock_before"] == 20
    assert sell["stock_after"] == 15
    assert "price_basis" in sell
    assert "trade_bonus" in sell
    assert engine.inners[pid].inventory["material"] == 15


def test_low_urgency_npc_sell_uses_two_unit_cap() -> None:
    engine = MultiTickEngine()
    pid = "persona_001"
    quiet_needs(engine, pid)
    engine.inners[pid].inventory["material"] = 20
    prime_cache(engine, pid, material=quote(0.2, 0.1))

    events = engine._process_npc_shop()

    sell = next(
        e for e in events
        if e.get("type") == "npc_sell" and e.get("goods") == "material"
    )
    assert sell["qty"] == 2
    assert sell["stock_after"] == 18


def test_tool_and_medicine_emergency_buys_use_snn_urgency() -> None:
    engine = MultiTickEngine()
    pid = "persona_001"
    quiet_needs(engine, pid)
    inner = engine.inners[pid]
    inner.inventory["tool"] = 0
    inner.inventory["medicine"] = 0
    inner.equipped_tool_durability = None
    inner.vitality = 0.4
    prime_cache(
        engine,
        pid,
        tool=quote(0.45, 0.1),
        medicine=quote(0.6, 0.1),
    )

    events = engine._process_npc_shop()

    buys = {
        e["goods"]: e for e in events
        if e.get("type") == "npc_buy" and e.get("buyer") == pid
    }
    assert "tool" in buys, events
    assert "medicine" in buys, events
    assert buys["tool"]["urgency"] == 0.45
    assert buys["medicine"]["urgency"] == 0.6
    assert buys["tool"]["stock_before"] == 0
    assert buys["tool"]["stock_after"] == 1
    assert buys["medicine"]["stock_before"] == 0
    assert buys["medicine"]["stock_after"] == 1


def test_get_pricing_reuses_tick_cache() -> None:
    engine = MultiTickEngine()
    pid = "persona_001"
    calls: list[tuple[str, str]] = []
    original = engine._compute_snn_pricing

    def counted(persona_id: str, goods_type: str) -> dict:
        calls.append((persona_id, goods_type))
        return original(persona_id, goods_type)

    engine._compute_snn_pricing = counted  # type: ignore[method-assign]
    engine._pricing_cache = {}

    first = engine._get_pricing(pid, "food")
    second = engine._get_pricing(pid, "food")

    assert first is second
    assert calls == [(pid, "food")]


def run_all() -> None:
    tests = [
        test_high_motivation_suppresses_npc_sell,
        test_high_urgency_npc_sell_uses_five_unit_cap_and_fields,
        test_low_urgency_npc_sell_uses_two_unit_cap,
        test_tool_and_medicine_emergency_buys_use_snn_urgency,
        test_get_pricing_reuses_tick_cache,
    ]
    for test in tests:
        test()
        print(f"[PASS] {test.__name__}")
    print(f"\n{len(tests)}/{len(tests)} Phase 12-B checks PASS")


if __name__ == "__main__":
    run_all()
