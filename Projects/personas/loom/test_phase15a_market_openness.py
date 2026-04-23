# -*- coding: utf-8 -*-
"""Phase 15-A market openness verification."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.multi_tick_engine import MultiTickEngine
from ontology.layers import CommunityMetrics, GovernancePolicy


def _wake_lord(engine: MultiTickEngine, lord_id: str) -> None:
    inner = engine.inners[lord_id]
    inner.is_sleeping = False
    inner.energy_pool = 1.0


def _set_lord_firing(
    engine: MultiTickEngine,
    lord_id: str,
    *,
    growth: float = 0.0,
    stability: float = 0.0,
    tension: float = 0.0,
) -> None:
    brain = engine.brains[lord_id]
    fr = np.zeros(brain.n_neurons, dtype=np.float32)
    clusters = np.array_split(np.arange(brain.n_neurons), 12)
    fr[clusters[7]] = growth / 10.0
    fr[clusters[2]] = stability / 10.0
    fr[clusters[5]] = tension / 10.0
    brain._last_firing_rate = fr


def _prepare_food_trade(
    engine: MultiTickEngine,
    *,
    seller_id: str = "persona_022",
    buyer_id: str = "persona_002",
) -> tuple[str, str]:
    engine.market_orders.clear()
    for pid, inner in engine.inners.items():
        inner.is_sleeping = False
        inner.inventory["food"] = 10
        inner.chronic_stress = 0.0
        inner.oyok[3] = np.float16(0.0)
    engine.inners[seller_id].inventory["food"] = 30
    engine.inners[buyer_id].inventory["food"] = 0
    engine.wallets[buyer_id].gold = 200.0
    engine.wallets[seller_id].gold = 0.0
    engine._pricing_cache = {
        seller_id: {"food": {"sell_price": 5.0, "buy_max": 20.0, "urgency": 0.0}},
        buyer_id: {"food": {"sell_price": 5.0, "buy_max": 20.0, "urgency": 1.0}},
    }
    return buyer_id, seller_id


def test_t1_governance_policy_default_market_openness() -> None:
    assert GovernancePolicy().market_openness == 0.5


def test_t2_policy_update_changes_market_openness_from_snn() -> None:
    engine = MultiTickEngine()
    tid = "seorim"
    lord_id = engine.territories[tid].lord_id
    assert lord_id is not None
    _wake_lord(engine, lord_id)
    _set_lord_firing(engine, lord_id, growth=1.0, stability=1.0, tension=0.0)
    events = engine._update_governance_policy()
    assert engine.territories[tid].policy.market_openness > 0.5
    assert any(evt.get("market_openness") for evt in events)


def test_t3_dense_community_lowers_market_openness() -> None:
    engine = MultiTickEngine()
    tid = "seorim"
    lord_id = engine.territories[tid].lord_id
    assert lord_id is not None
    _wake_lord(engine, lord_id)
    _set_lord_firing(engine, lord_id, growth=0.0, stability=0.0, tension=0.0)
    engine._last_community_metrics = [
        CommunityMetrics(tid, node_count=3, edge_count=3, density_ratio=0.8,
                         intra_edges=3, inter_edges=0, intra_inter_ratio=3.0)
    ]
    engine._update_governance_policy()
    assert engine.territories[tid].policy.market_openness < 0.5


def test_t4_low_openness_blocks_inter_territory_trade() -> None:
    engine = MultiTickEngine()
    buyer_id, seller_id = _prepare_food_trade(engine)
    engine.territories["seorim"].policy.market_openness = 0.2
    engine.territories["ironridge"].policy.market_openness = 0.2
    events = engine._process_market()
    assert not any(evt.get("type") == "trade" for evt in events)
    assert engine.inners[buyer_id].inventory["food"] == 0
    assert engine.inners[seller_id].inventory["food"] == 30


def test_t5_average_openness_allows_inter_territory_trade() -> None:
    engine = MultiTickEngine()
    buyer_id, seller_id = _prepare_food_trade(engine)
    engine.territories["seorim"].policy.market_openness = 0.5
    engine.territories["ironridge"].policy.market_openness = 0.3
    events = engine._process_market()
    trades = [evt for evt in events if evt.get("type") == "trade"]
    assert trades
    assert trades[0]["buyer"] == buyer_id
    assert trades[0]["seller"] == seller_id
    assert trades[0]["inter_territory"] is True


def test_t6_inter_territory_fee_doubles_and_splits_treasury() -> None:
    engine = MultiTickEngine()
    buyer_id, seller_id = _prepare_food_trade(engine)
    engine.territories["seorim"].policy.market_openness = 0.5
    engine.territories["ironridge"].policy.market_openness = 0.5
    seorim_before = engine.territories["seorim"].treasury_gold
    iron_before = engine.territories["ironridge"].treasury_gold
    events = engine._process_market()
    trade = next(evt for evt in events if evt.get("type") == "trade")
    assert trade["fee"] == 4.0
    assert engine.wallets[buyer_id].gold == 171.0
    assert engine.wallets[seller_id].gold == 25.0
    assert engine.territories["seorim"].treasury_gold == seorim_before + 1.0
    assert engine.territories["ironridge"].treasury_gold == iron_before + 1.0


def _run_all() -> None:
    tests = [
        test_t1_governance_policy_default_market_openness,
        test_t2_policy_update_changes_market_openness_from_snn,
        test_t3_dense_community_lowers_market_openness,
        test_t4_low_openness_blocks_inter_territory_trade,
        test_t5_average_openness_allows_inter_territory_trade,
        test_t6_inter_territory_fee_doubles_and_splits_treasury,
    ]
    print("=== Phase 15-A Market Openness Verification ===")
    for test in tests:
        test()
        print(f"  [PASS] {test.__name__}")
    print(f"\n{len(tests)}/{len(tests)} PASS")
    print("ALL PASS")


if __name__ == "__main__":
    _run_all()
