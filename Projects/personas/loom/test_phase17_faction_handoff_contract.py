"""Phase 17 Phi-2 Stage 4: D10 read-only handoff contract tests.

spec functional-equivalence: d10_read_only, byte_level_hash,
caller_mutation_safe, radius_validation, unknown_faction_keyerror.

Phi-3 Struggle must consume Phi-2 output only through the seven D10 APIs.
These tests freeze shape, validation, domain-state read-only behavior, and
caller-mutation safety while allowing internal cache refresh.
"""
from __future__ import annotations

import hashlib
import pickle
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.multi_tick_engine import MultiTickEngine


def _engine_after(ticks: int = 0, seed: int = 42) -> MultiTickEngine:
    eng = MultiTickEngine(seed=seed)
    for _ in range(ticks):
        eng.tick()
    return eng


def _domain_state_hash(eng: MultiTickEngine) -> str:
    """Hash only the five D10 domain channels, excluding lazy caches."""
    snap = {
        "personas_faction": {
            pid: (eng.personas[pid].faction, eng.personas[pid].faction_cooldown)
            for pid in sorted(eng.personas)
        },
        "factions": {
            fid: (
                eng.factions[fid].id,
                eng.factions[fid].name,
                eng.factions[fid].founder_pid,
                tuple(eng.factions[fid].charter),
                eng.factions[fid].created_tick,
            )
            for fid in sorted(eng.factions)
        },
        "territory_ref": {
            tid: eng.territories[tid].factionRef for tid in sorted(eng.territories)
        },
        "affiliation_scores": {
            pid: dict(sorted(eng.inners[pid].affiliation_scores.items()))
            for pid in sorted(eng.inners)
        },
    }
    return hashlib.sha256(pickle.dumps(snap, protocol=4)).hexdigest()


def _call_all_apis(eng: MultiTickEngine) -> list[Any]:
    fid = next(iter(eng.factions))
    return [
        eng.faction_population_distribution(),
        eng.faction_territory_distribution(),
        eng.faction_charter_primitives(fid),
        eng.factions_in_contact(radius=1),
        eng.faction_wealth_distribution(),
        eng.faction_social_matrix(),
        eng.faction_grievance_targets(),
    ]


def test_population_distribution_returns_int_dict() -> None:
    eng = _engine_after()
    dist = eng.faction_population_distribution()
    assert isinstance(dist, dict)
    for fid, count in dist.items():
        assert isinstance(fid, str)
        assert isinstance(count, int)
        assert count >= 0


def test_territory_distribution_returns_str_lists() -> None:
    eng = _engine_after()
    dist = eng.faction_territory_distribution()
    assert isinstance(dist, dict)
    for fid, tids in dist.items():
        assert isinstance(fid, str)
        assert isinstance(tids, list)
        assert all(isinstance(tid, str) for tid in tids)


def test_charter_primitives_returns_tuple() -> None:
    eng = _engine_after()
    fid = next(iter(eng.factions))
    charter = eng.faction_charter_primitives(fid)
    assert isinstance(charter, tuple)
    assert 3 <= len(charter) <= 5
    assert all(isinstance(item, str) for item in charter)


def test_charter_primitives_unknown_id_raises_keyerror() -> None:
    eng = _engine_after()
    with pytest.raises(KeyError):
        eng.faction_charter_primitives("FACTION_DOES_NOT_EXIST")


def test_factions_in_contact_radius_validation() -> None:
    eng = _engine_after()
    pairs = eng.factions_in_contact(radius=1)
    assert isinstance(pairs, list)
    assert all(isinstance(pair, tuple) and len(pair) == 2 for pair in pairs)
    assert pairs == sorted(pairs)
    assert all(pair[0] < pair[1] for pair in pairs)
    with pytest.raises(ValueError):
        eng.factions_in_contact(radius=0)
    with pytest.raises(ValueError):
        eng.factions_in_contact(radius=-1)


def test_wealth_distribution_shape() -> None:
    eng = _engine_after()
    wealth = eng.faction_wealth_distribution()
    assert isinstance(wealth, dict)
    for fid, stats in wealth.items():
        assert isinstance(fid, str)
        assert set(stats) == {"total", "mean", "gini", "top_decile_share"}
        assert all(isinstance(value, float) for value in stats.values())


def test_social_matrix_shape() -> None:
    eng = _engine_after()
    matrix = eng.faction_social_matrix()
    assert isinstance(matrix, dict)
    for pair, trust in matrix.items():
        assert isinstance(pair, tuple)
        assert len(pair) == 2
        assert pair[0] < pair[1]
        assert isinstance(trust, float)


def test_grievance_targets_shape() -> None:
    eng = _engine_after()
    targets = eng.faction_grievance_targets()
    assert isinstance(targets, dict)
    for fid, counts in targets.items():
        assert isinstance(fid, str)
        assert isinstance(counts, dict)
        for lord_id, count in counts.items():
            assert isinstance(lord_id, str)
            assert isinstance(count, int)
            assert count >= 0


def test_returned_containers_are_caller_mutation_safe() -> None:
    eng = _engine_after()
    before_hash = _domain_state_hash(eng)

    population = eng.faction_population_distribution()
    population["MUTATED"] = 999

    territory = eng.faction_territory_distribution()
    first_territory_key = next(iter(territory))
    territory[first_territory_key].append("MUTATED")

    contact = eng.factions_in_contact(radius=1)
    contact.append(("MUTATED_A", "MUTATED_B"))

    charter_fid = next(iter(eng.factions))
    charter = eng.faction_charter_primitives(charter_fid)
    charter = charter + ("MUTATED_CHARTER",)
    assert "MUTATED_CHARTER" in charter

    wealth = eng.faction_wealth_distribution()
    first_wealth_key = next(iter(wealth))
    wealth[first_wealth_key]["total"] = -999.0

    social = eng.faction_social_matrix()
    social[("MUTATED_A", "MUTATED_B")] = -1.0

    grievance = eng.faction_grievance_targets()
    first_grievance_key = next(iter(grievance))
    grievance[first_grievance_key]["MUTATED_LORD"] = 999

    after_hash = _domain_state_hash(eng)
    assert after_hash == before_hash

    assert "MUTATED" not in eng.faction_population_distribution()
    assert "MUTATED" not in eng.faction_territory_distribution()[first_territory_key]
    assert ("MUTATED_A", "MUTATED_B") not in eng.factions_in_contact(radius=1)
    assert "MUTATED_CHARTER" not in eng.faction_charter_primitives(charter_fid)
    assert eng.faction_wealth_distribution()[first_wealth_key]["total"] >= 0.0
    assert ("MUTATED_A", "MUTATED_B") not in eng.faction_social_matrix()
    assert "MUTATED_LORD" not in eng.faction_grievance_targets()[first_grievance_key]


def test_read_apis_do_not_mutate_domain_state_after_round_robin_calls() -> None:
    eng = _engine_after()
    before = _domain_state_hash(eng)
    for _ in range(100):
        _call_all_apis(eng)
    after = _domain_state_hash(eng)
    assert after == before


def test_population_keys_match_factions_registry() -> None:
    eng = _engine_after()
    pop = eng.faction_population_distribution()
    assert set(pop.keys()) == set(eng.factions.keys())


def test_territory_keys_match_factions_registry() -> None:
    eng = _engine_after()
    terr = eng.faction_territory_distribution()
    assert set(terr.keys()) == set(eng.factions.keys())
