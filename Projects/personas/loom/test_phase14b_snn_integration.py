# -*- coding: utf-8 -*-
"""Phase 14-B SNN governance integration verification."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.multi_tick_engine import MultiTickEngine
from ontology.layers import (
    FACTION_TELEMETRY_BIAS_NEIGHBOR,
    FACTION_TELEMETRY_BIAS_OWN,
    Relationship,
)


def _first_resident(engine: MultiTickEngine) -> tuple[str, str, str]:
    for tid, territory in engine.territories.items():
        if not territory.lord_id:
            continue
        for pid in engine._get_territory_residents(tid):
            if pid != territory.lord_id:
                return tid, pid, territory.lord_id
    raise AssertionError("no resident found")


def _wake_lord(engine: MultiTickEngine, lord_id: str) -> None:
    inner = engine.inners[lord_id]
    inner.is_sleeping = False
    inner.energy_pool = 1.0
    inner.tone[0] = np.float16(2.0)
    inner.tone[10] = np.float16(2.0)


def _economic_input(engine: MultiTickEngine, pid: str, grievance: float) -> np.ndarray:
    brain = engine.brains[pid]
    brain.tick(
        climate_vec=np.zeros(8, dtype=np.float16),
        energy_pool=1.0,
        oyok=np.array([0.2, 0.0, 0.0, 0.0, 0.0], dtype=np.float16),
        tone=np.ones(12, dtype=np.float16),
        economic_state={
            "food_ratio": 1.0,
            "tool_ratio": 1.0,
            "wealth_ratio": 1.0,
            "job_satisfaction": 0.5,
            "relative_wealth": 1.0,
            "tax_burden": 0.0,
            "grievance": grievance,
            "trust_to_lord": 0.5,
        },
    )
    return brain._last_economic_input.copy()


def test_t1_grievance_in_economic_state() -> None:
    engine = MultiTickEngine()
    _, pid, lord_id = _first_resident(engine)
    rel = engine.relationships[Relationship(persona_a=pid, persona_b=lord_id).key()]
    rel.trust = 0.25
    engine.inners[pid].grievance = 0.7
    eco = engine._build_economic_state(pid)
    assert abs(eco["grievance"] - 0.7) < 0.01
    assert abs(eco["trust_to_lord"] - 0.25) < 0.01
    assert "tax_burden" in eco


def test_t2_grievance_stimulates_snn_neurons() -> None:
    engine = MultiTickEngine()
    _, pid, _ = _first_resident(engine)
    low = _economic_input(engine, pid, grievance=0.0)
    high = _economic_input(engine, pid, grievance=0.9)
    assert high[20:30].sum() > low[20:30].sum() + 0.1
    assert high[30:40].sum() > low[30:40].sum() + 0.1


def test_t3_grievance_raises_body_stress() -> None:
    engine = MultiTickEngine()
    _, pid, _ = _first_resident(engine)
    inner = engine.inners[pid]
    inner.grievance = 0.8
    inner.chronic_stress = 0.0
    inner.oyok[4] = np.float16(0.0)
    inner.chiljeong[1] = np.float16(0.0)
    inner.chiljeong[3] = np.float16(0.0)
    engine.time.tick = 24
    engine._update_grievances()
    assert inner.chronic_stress > 0.0
    assert float(inner.oyok[4]) > 0.0
    assert float(inner.chiljeong[1]) > 0.0
    assert float(inner.chiljeong[3]) > 0.0


def test_t4_lord_responds_to_resident_grievance() -> None:
    engine = MultiTickEngine()
    tid = next(iter(engine.territories))
    territory = engine.territories[tid]
    lord_id = territory.lord_id
    assert lord_id is not None
    _wake_lord(engine, lord_id)
    territory.policy.food_priority = 0.0
    engine.brains[lord_id]._last_firing_rate = np.zeros(
        engine.brains[lord_id].n_neurons, dtype=np.float32
    )
    for pid in engine._get_territory_residents(tid):
        if pid != lord_id:
            engine.inners[pid].grievance = 0.9
    events = engine._update_governance_policy()
    assert territory.policy.food_priority >= 0.13
    assert any(
        evt.get("territory") == tid
        and evt.get("snn_signals", {}).get("tension", 0.0) >= 0.4
        for evt in events
    )


def test_t5_max_farmers_is_dynamic() -> None:
    engine = MultiTickEngine()
    tid = next(iter(engine.territories))
    territory = engine.territories[tid]
    lord_id = territory.lord_id
    assert lord_id is not None
    for persona in engine.personas.values():
        persona.territory = tid
        persona.employment_id = None
    engine._territory_residents_cache = None
    engine.jobs.clear()
    engine.employments.clear()
    _wake_lord(engine, lord_id)
    territory.treasury_gold = 5000.0
    engine.wallets[lord_id].will = 10.0
    territory.policy.food_priority = 0.9
    for pid in engine._get_territory_residents(tid):
        engine.inners[pid].oyok[0] = np.float16(0.8)
    for _ in range(3):
        assert engine.create_job(lord_id, "farmer", 6.0, "seed farmer") is not None
    for tick in range(1, 81):
        engine.time.tick = tick
        engine._auto_economy_tick()
        farmers = sum(
            1 for job in engine.jobs.values()
            if job.employer_id == lord_id and job.title == "farmer"
        )
        if farmers > 3:
            break
    assert farmers > 3


def test_t6_exodus_blocked_yields_stress() -> None:
    engine = MultiTickEngine()
    _, pid, _ = _first_resident(engine)
    for territory in engine.territories.values():
        territory.policy.tax_rate = 0.10
    inner = engine.inners[pid]
    inner.grievance = 0.95
    stress_before = inner.chronic_stress
    event = engine._try_exodus(pid)
    assert event is not None
    assert event["type"] == "exodus_blocked"
    assert inner.chronic_stress > stress_before


def test_t7_grievance_critical_announced_once() -> None:
    engine = MultiTickEngine()
    _, pid, _ = _first_resident(engine)
    inner = engine.inners[pid]
    inner.grievance = 0.85
    engine.time.tick = 24
    first = engine._update_grievances()
    engine.time.tick = 48
    second = engine._update_grievances()
    inner.grievance = 0.5
    engine.time.tick = 72
    engine._update_grievances()
    inner.grievance = 0.85
    engine.time.tick = 96
    third = engine._update_grievances()
    assert sum(evt.get("persona") == pid for evt in first) == 1
    assert sum(evt.get("persona") == pid for evt in second) == 0
    assert sum(evt.get("persona") == pid for evt in third) == 1


def test_phase14b_faction_bias_noise_bound() -> None:
    """D9 faction bias가 경제 readout의 tax/grievance 신호를 오염시키지 않음 확증.

    현재 loom 구현에서 D9 주입은 `brain._last_economic_input`이 아니라
    engine-side pre-bias(`brain.snn.v += _build_persona_snn_input(pid)`) 경로다.
    따라서 계약은 두 층으로 검증한다.
    - 동일 경제 입력 하에서 경제 뉴런 20~40 차이 < 0.01
    - faction telemetry 전류 300~349는 own/neighbor bias만큼 증가
    """
    engine_baseline = MultiTickEngine(seed=42)
    _, pid, lord_id = _first_resident(engine_baseline)
    for candidate_pid in sorted(engine_baseline.personas):
        if engine_baseline.personas[candidate_pid].faction is not None:
            engine_baseline._change_persona_faction(candidate_pid, None, source="drift")
    engine_baseline.factions.clear()
    engine_baseline._faction_members_cache = {}

    original_baseline_neighbors = engine_baseline._collect_neighbor_faction_ids
    engine_baseline._collect_neighbor_faction_ids = lambda territory_id: set()
    try:
        rel = engine_baseline.relationships[Relationship(persona_a=pid, persona_b=lord_id).key()]
        rel.trust = 0.25
        engine_baseline.inners[pid].grievance = 0.7
        eco_baseline = _economic_input(engine_baseline, pid, grievance=0.7)
        current_baseline = engine_baseline._build_persona_snn_input(pid)
    finally:
        engine_baseline._collect_neighbor_faction_ids = original_baseline_neighbors

    engine_faction = MultiTickEngine(seed=42)
    _, pid_faction, lord_id_faction = _first_resident(engine_faction)
    assert pid_faction == pid
    assert lord_id_faction == lord_id
    faction_ids = sorted(engine_faction.factions)
    assert len(faction_ids) >= 2, "faction telemetry test expects at least 2 founder factions"
    own_fid, neighbor_fid = faction_ids[:2]
    engine_faction._change_persona_faction(pid_faction, own_fid, source="affiliation")

    original_faction_neighbors = engine_faction._collect_neighbor_faction_ids
    engine_faction._collect_neighbor_faction_ids = lambda territory_id: {neighbor_fid}
    try:
        rel2 = engine_faction.relationships[Relationship(persona_a=pid_faction, persona_b=lord_id_faction).key()]
        rel2.trust = 0.25
        engine_faction.inners[pid_faction].grievance = 0.7
        eco_faction = _economic_input(engine_faction, pid_faction, grievance=0.7)
        current_faction = engine_faction._build_persona_snn_input(pid_faction)
    finally:
        engine_faction._collect_neighbor_faction_ids = original_faction_neighbors

    eco_diff = float(np.abs(eco_baseline[20:40] - eco_faction[20:40]).max())
    assert eco_diff < 0.01, f"economic neurons contaminated by faction bias: diff={eco_diff}"

    own_diff = float((current_faction[300:325] - current_baseline[300:325]).mean())
    assert own_diff >= FACTION_TELEMETRY_BIAS_OWN * 0.5, f"own bias not applied: diff={own_diff}"

    neighbor_diff = float((current_faction[325:350] - current_baseline[325:350]).mean())
    assert neighbor_diff >= FACTION_TELEMETRY_BIAS_NEIGHBOR * 0.5, (
        f"neighbor bias not applied: diff={neighbor_diff}"
    )


def _run_all() -> None:
    tests = [
        test_t1_grievance_in_economic_state,
        test_t2_grievance_stimulates_snn_neurons,
        test_t3_grievance_raises_body_stress,
        test_t4_lord_responds_to_resident_grievance,
        test_t5_max_farmers_is_dynamic,
        test_t6_exodus_blocked_yields_stress,
        test_t7_grievance_critical_announced_once,
        test_phase14b_faction_bias_noise_bound,
    ]
    passed = 0
    print("=== Phase 14-B SNN Integration Verification ===")
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  [PASS] {test.__name__}")
        except Exception as exc:
            print(f"  [FAIL] {test.__name__} - {exc}")
            raise
    print(f"\n{passed}/{len(tests)} PASS")
    print("ALL PASS")


if __name__ == "__main__":
    _run_all()
