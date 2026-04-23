# -*- coding: utf-8 -*-
"""Phase 15-C job diversity verification."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.multi_tick_engine import MultiTickEngine
from ontology.layers import Relationship, SkillProfile


def _force_trust(engine: MultiTickEngine, pid_a: str, pid_b: str, trust: float) -> None:
    key = Relationship(persona_a=pid_a, persona_b=pid_b).key()
    if key not in engine.relationships:
        engine.relationships[key] = Relationship(persona_a=pid_a, persona_b=pid_b)
    engine.relationships[key].trust = float(trust)


def _set_all_trust(engine: MultiTickEngine, trust: float) -> None:
    for rel in engine.relationships.values():
        rel.trust = float(trust)


def _set_job(engine: MultiTickEngine, pid: str, job_title: str) -> None:
    engine.personas[pid].employment_id = None
    engine.inners[pid].skill_profiles.clear()
    engine.inners[pid].skill_profiles[job_title] = SkillProfile(
        persona_id=pid,
        skill_id=job_title,
        mastery=0.1,
    )


def _wake_lord(engine: MultiTickEngine, lord_id: str) -> None:
    inner = engine.inners[lord_id]
    inner.is_sleeping = False
    inner.energy_pool = 1.0


def _prepare_guard_case(with_guard: bool) -> tuple[MultiTickEngine, str, float]:
    engine = MultiTickEngine()
    tid = "seorim"
    lord_id = "persona_001"
    guard_id = "persona_022"
    target_id = "persona_002"

    for persona in engine.personas.values():
        persona.territory = tid
        persona.employment_id = None
    engine._territory_residents_cache = None
    engine.territories[tid].lord_id = lord_id

    for territory in engine.territories.values():
        territory.policy.tax_rate = 0.10
    engine.territories[tid].policy.tax_rate = 0.20

    _set_all_trust(engine, 0.5)
    for pid, inner in engine.inners.items():
        inner.is_sleeping = False
        inner.strike_until_tick = 0
        inner.grievance = 0.0
        inner.grievance_announced = False
        inner.inventory["food"] = 20
        inner.oyok[0] = np.float16(0.3)
        _set_job(engine, pid, "farmer")
    if with_guard:
        _set_job(engine, guard_id, "guard")

    engine.time.tick = 24
    base_delta = ((0.20 / 0.30) - 0.5) * 0.03
    return engine, target_id, base_delta


def test_t1_healer_work_reduces_trusted_same_territory_stress() -> None:
    engine = MultiTickEngine()
    healer_id = "persona_003"
    target_id = "persona_002"
    _set_job(engine, healer_id, "healer")
    _force_trust(engine, healer_id, target_id, 0.8)
    engine.inners[target_id].chronic_stress = 0.5

    engine._process_economy(healer_id, "work")

    assert abs(engine.inners[target_id].chronic_stress - 0.498) < 1e-9


def test_t2_healer_requires_work_and_same_territory() -> None:
    engine = MultiTickEngine()
    healer_id = "persona_003"
    same_territory_id = "persona_002"
    other_territory_id = "persona_022"
    _set_job(engine, healer_id, "healer")
    _force_trust(engine, healer_id, same_territory_id, 0.8)
    _force_trust(engine, healer_id, other_territory_id, 0.8)
    engine.inners[same_territory_id].chronic_stress = 0.5
    engine.inners[other_territory_id].chronic_stress = 0.5

    engine._process_economy(healer_id, "idle")
    assert engine.inners[same_territory_id].chronic_stress == 0.5

    engine._process_economy(healer_id, "work")
    assert engine.inners[other_territory_id].chronic_stress == 0.5


def test_t3_guard_ratio_dampens_positive_grievance_delta() -> None:
    engine, target_id, base_delta = _prepare_guard_case(with_guard=True)

    assert engine._get_territory_guard_active_count("seorim") == 1
    assert len(engine._get_territory_residents("seorim")) == 10
    engine._update_grievances()

    expected = base_delta * 0.9
    assert abs(engine.inners[target_id].grievance - expected) < 1e-6


def test_t4_no_guard_keeps_original_grievance_delta() -> None:
    engine, target_id, base_delta = _prepare_guard_case(with_guard=False)

    assert engine._get_territory_guard_active_count("seorim") == 0
    engine._update_grievances()

    assert abs(engine.inners[target_id].grievance - base_delta) < 1e-6


def test_t5_scholar_records_recent_strike_in_chronicle() -> None:
    engine = MultiTickEngine()
    scholar_id = "persona_003"
    tid = engine.personas[scholar_id].territory
    _set_job(engine, scholar_id, "scholar")
    engine.territories[tid].chronicle.clear()
    engine.log = [{"economy_events": []} for _ in range(23)]
    engine.log.append({
        "economy_events": [
            {"type": "strike_executed", "territory": tid},
        ],
    })

    engine._process_economy(scholar_id, "work")

    assert len(engine.territories[tid].chronicle) == 1
    entry = engine.territories[tid].chronicle[0]
    assert entry["type"] == "strike"
    assert entry["summary"] == "strikes=1"


def test_t6_chronicle_boosts_governance_stability_signal() -> None:
    engine = MultiTickEngine()
    tid = "seorim"
    territory = engine.territories[tid]
    lord_id = territory.lord_id
    assert lord_id is not None
    _wake_lord(engine, lord_id)
    territory.chronicle = [
        {"tick": i, "type": "policy_shift", "summary": "policy_updated"}
        for i in range(5)
    ]
    engine.brains[lord_id]._last_firing_rate = np.zeros(
        engine.brains[lord_id].n_neurons,
        dtype=np.float32,
    )

    events = engine._update_governance_policy()

    event = next(evt for evt in events if evt.get("territory") == tid)
    assert event["snn_signals"]["stability"] == 0.05


def _run_all() -> None:
    tests = [
        test_t1_healer_work_reduces_trusted_same_territory_stress,
        test_t2_healer_requires_work_and_same_territory,
        test_t3_guard_ratio_dampens_positive_grievance_delta,
        test_t4_no_guard_keeps_original_grievance_delta,
        test_t5_scholar_records_recent_strike_in_chronicle,
        test_t6_chronicle_boosts_governance_stability_signal,
    ]
    print("=== Phase 15-C Job Diversity Verification ===")
    for test in tests:
        test()
        print(f"  [PASS] {test.__name__}")
    print(f"\n{len(tests)}/{len(tests)} PASS")
    print("ALL PASS")


if __name__ == "__main__":
    _run_all()
