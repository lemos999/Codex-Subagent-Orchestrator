# -*- coding: utf-8 -*-
"""Phase 15 collective action verification."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.multi_tick_engine import MultiTickEngine
from ontology.layers import Relationship


def _force_trust(engine: MultiTickEngine, pid_a: str, pid_b: str, trust: float) -> None:
    key = Relationship(persona_a=pid_a, persona_b=pid_b).key()
    if key not in engine.relationships:
        engine.relationships[key] = Relationship(persona_a=pid_a, persona_b=pid_b)
    engine.relationships[key].trust = float(trust)


def _set_all_trust(engine: MultiTickEngine, trust: float) -> None:
    for rel in engine.relationships.values():
        rel.trust = float(trust)


def _territory_with_non_lord(
    engine: MultiTickEngine,
    min_non_lord: int = 3,
) -> tuple[str, list[str]]:
    for tid, territory in engine.territories.items():
        residents = engine._get_territory_residents(tid)
        non_lord = [pid for pid in residents if pid != territory.lord_id]
        if len(non_lord) >= min_non_lord:
            return tid, non_lord
    raise AssertionError("no territory with enough non-lord residents")


def test_t1_community_members_by_trust() -> None:
    engine = MultiTickEngine()
    tid, non_lord = _territory_with_non_lord(engine, min_non_lord=3)
    pid = non_lord[0]
    residents = engine._get_territory_residents(tid)
    _force_trust(engine, pid, non_lord[1], 0.8)
    _force_trust(engine, pid, non_lord[2], 0.2)
    members = engine._get_community_members(pid, min_trust=0.4)
    assert non_lord[1] in members
    assert non_lord[2] not in members
    assert pid not in members
    assert all(engine.personas[m].territory == tid for m in members)
    assert set(members).issubset(set(residents))


def test_t2_grievance_contagion() -> None:
    engine = MultiTickEngine()
    _set_all_trust(engine, 0.0)
    _, non_lord = _territory_with_non_lord(engine, min_non_lord=3)
    source = non_lord[0]
    engine.inners[source].grievance = 0.9
    for pid in non_lord[1:]:
        engine.inners[pid].grievance = 0.1
        _force_trust(engine, source, pid, 0.8)
    before = float(engine.inners[non_lord[1]].grievance)
    engine.time.tick = 24
    engine._update_grievances()
    after = float(engine.inners[non_lord[1]].grievance)
    assert after > before


def test_t3_strike_triggers_when_isolated() -> None:
    engine = MultiTickEngine()
    tid, non_lord = _territory_with_non_lord(engine, min_non_lord=3)
    for territory in engine.territories.values():
        territory.policy.tax_rate = 0.20
    for pid in non_lord:
        engine.inners[pid].grievance = 0.85
    engine.time.tick = 24
    events = engine._update_grievances()
    assert any(evt.get("type") == "strike" and evt.get("territory") == tid for evt in events)
    assert all(engine.inners[pid].strike_until_tick == 72 for pid in non_lord)
    assert all(float(engine.inners[pid].grievance) < 0.85 for pid in non_lord)


def test_t4_mass_exodus_when_alternative_exists() -> None:
    engine = MultiTickEngine()
    source_tid, non_lord = _territory_with_non_lord(engine, min_non_lord=3)
    target_tid = next(tid for tid in engine.territories if tid != source_tid)
    for territory in engine.territories.values():
        territory.policy.tax_rate = 0.20
    engine.territories[source_tid].policy.tax_rate = 0.25
    engine.territories[target_tid].policy.tax_rate = 0.05
    for pid in non_lord:
        engine.inners[pid].grievance = 0.85
    engine.time.tick = 24
    events = engine._update_grievances()
    migrated = [pid for pid in non_lord if engine.personas[pid].territory == target_tid]
    assert any(evt.get("type") == "mass_exodus" for evt in events)
    assert len(migrated) == len(non_lord)
    assert all(abs(float(engine.inners[pid].grievance) - 0.3) < 1e-6 for pid in migrated)


def test_t5_strike_blocks_work() -> None:
    engine = MultiTickEngine()
    _, non_lord = _territory_with_non_lord(engine, min_non_lord=1)
    pid = non_lord[0]
    engine.inners[pid].strike_until_tick = engine.time.tick + 10
    food_before = engine.inners[pid].inventory.get("food", 0)
    gold_before = engine.wallets[pid].gold
    result = engine._process_work(pid)
    direct = engine._process_economy(pid, "work")
    assert result is not None and result.get("type") == "strike_refuse_work"
    assert direct is not None and direct.get("type") == "strike_refuse_work"
    assert engine.inners[pid].inventory.get("food", 0) == food_before
    assert engine.wallets[pid].gold == gold_before


def test_t6_density_metrics_computed() -> None:
    engine = MultiTickEngine()
    _set_all_trust(engine, 0.0)
    source_tid, _ = _territory_with_non_lord(engine, min_non_lord=3)
    target_tid = next(tid for tid in engine.territories if tid != source_tid)
    source = engine._get_territory_residents(source_tid)
    target = engine._get_territory_residents(target_tid)
    _force_trust(engine, source[0], source[1], 0.8)
    _force_trust(engine, source[1], source[2], 0.8)
    _force_trust(engine, source[0], target[0], 0.8)
    metrics = {metric.territory_id: metric for metric in engine._compute_community_metrics()}
    source_metric = metrics[source_tid]
    assert source_metric.intra_edges == 2
    assert source_metric.inter_edges == 1
    assert source_metric.edge_count == 3
    n = source_metric.node_count
    possible = max(1, n * (n - 1) // 2)
    expected = min(1.0, source_metric.intra_edges / possible)
    assert 0.0 <= source_metric.density_ratio <= 1.0
    assert abs(source_metric.density_ratio - expected) < 1e-9


def test_t7_density_warning_fires_above_05() -> None:
    engine = MultiTickEngine()
    _set_all_trust(engine, 0.0)
    source_tid, _ = _territory_with_non_lord(engine, min_non_lord=3)
    residents = engine._get_territory_residents(source_tid)
    for i, pid_a in enumerate(residents):
        for pid_b in residents[i + 1:]:
            _force_trust(engine, pid_a, pid_b, 0.8)
    engine.time.tick = 47
    result = engine.tick()
    warnings = [
        evt for evt in result.get("economy_events", [])
        if evt.get("type") == "density_warning" and evt.get("territory") == source_tid
    ]
    metric = next(m for m in result["community_metrics"] if m["territory_id"] == source_tid)
    assert metric["density_ratio"] <= 1.0
    assert metric["density_ratio"] > 0.5
    assert warnings


def _run_all() -> None:
    tests = [
        test_t1_community_members_by_trust,
        test_t2_grievance_contagion,
        test_t3_strike_triggers_when_isolated,
        test_t4_mass_exodus_when_alternative_exists,
        test_t5_strike_blocks_work,
        test_t6_density_metrics_computed,
        test_t7_density_warning_fires_above_05,
    ]
    print("=== Phase 15 Collective Action Verification ===")
    for test in tests:
        test()
        print(f"  [PASS] {test.__name__}")
    print(f"\n{len(tests)}/{len(tests)} PASS")
    print("ALL PASS")


if __name__ == "__main__":
    _run_all()
