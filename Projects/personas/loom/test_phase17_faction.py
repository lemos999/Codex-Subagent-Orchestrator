"""Phase 17 faction verification."""
from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path
import sys
import traceback

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _make_faction(fid: str, founder_pid: str, created_tick: int = 0):
    from Projects.personas.loom.ontology import layers

    return layers.Faction(
        id=fid,
        name=fid,
        founder_pid=founder_pid,
        charter=("duty", "care", "grain"),
        created_tick=created_tick,
    )


def _fresh_engine(seed: int = 42):
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=seed)
    engine.factions = {}
    engine._faction_members_cache = {}
    engine._territory_neighbors_cache = None
    engine.event_log = []
    for persona in engine.personas.values():
        persona.faction = None
        persona.faction_cooldown = 0
    for territory in engine.territories.values():
        territory.factionRef = None
    for inner in engine.inners.values():
        inner.affiliation_scores = {}
    return engine


def _scan_faction_writes(tree: ast.AST, source_lines: list[str]) -> list[tuple[int, str, str]]:
    whitelist_marker = "PHASE17_FACTION_SSOT_WRITE"
    banned_attrs = {"faction", "faction_cooldown"}
    hits: list[tuple[int, str, str]] = []

    def _targets(node: ast.AST):
        if isinstance(node, ast.Assign):
            yield from node.targets
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            yield node.target
        elif isinstance(node, ast.NamedExpr):
            yield node.target

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.NamedExpr)):
            continue
        line_idx = node.lineno - 1
        if line_idx < len(source_lines) and whitelist_marker in source_lines[line_idx]:
            continue
        for target in _targets(node):
            if isinstance(target, ast.Attribute) and target.attr in banned_attrs:
                hits.append((node.lineno, target.attr, type(node).__name__))
    return hits


def test_d1_faction_dataclass_contract() -> None:
    from Projects.personas.loom.ontology import layers

    Faction = layers.Faction
    assert not hasattr(Faction("fid", "name", "p1", ("a", "b", "c"), 0), "__dict__")

    faction = Faction("fid", "name", "p1", ("a", "b", "c"), 0)
    assert faction.charter == ("a", "b", "c")

    for bad_charter in (("a", "b"), ("a", "a", "b")):
        raised = False
        try:
            Faction("fid", "name", "p1", bad_charter, 0)
        except ValueError:
            raised = True
        assert raised, f"charter validation failed for {bad_charter!r}"

    engine = _fresh_engine()
    assert isinstance(engine.factions, dict)
    assert engine.factions == {}


def test_d2_persona_and_innerworld_faction_fields() -> None:
    from dataclasses import fields
    from Projects.personas.loom.ontology import layers

    persona_fields = {f.name for f in fields(layers.Persona)}
    inner_fields = {f.name for f in fields(layers.InnerWorld)}

    assert "faction" in persona_fields
    assert "faction_cooldown" in persona_fields
    assert "affiliation_scores" in inner_fields
    assert getattr(layers, "MAX_TRACKED_FACTIONS_PER_PERSONA") == 8

    persona = layers.Persona(id="p", name="p", full_name="p")
    inner = layers.InnerWorld(persona_id="p")
    assert getattr(persona, "faction") is None
    assert getattr(persona, "faction_cooldown") == 0
    assert inner.affiliation_scores == {}


def test_d3_change_persona_faction_and_cooldown() -> None:
    from Projects.personas.loom.ontology import layers

    engine = _fresh_engine()
    pid = sorted(engine.personas)[0]
    fid_a = "faction_a"
    fid_b = "faction_b"
    engine.factions[fid_a] = _make_faction(fid_a, pid, created_tick=0)
    engine.factions[fid_b] = _make_faction(fid_b, pid, created_tick=0)

    before = len(engine.event_log)
    engine._change_persona_faction(pid, fid_a, source="birth_founder")
    persona = engine.personas[pid]
    assert persona.faction == fid_a
    assert persona.faction_cooldown == 0
    assert len(engine.event_log) == before + 1
    first_event = engine.event_log[-1]
    assert first_event["type"] == "faction_change"
    assert first_event["source"] == "birth_founder"

    engine._change_persona_faction(pid, fid_a, source="birth_founder")
    assert len(engine.event_log) == before + 1

    engine._change_persona_faction(pid, fid_b, source="drift")
    assert persona.faction == fid_b
    assert persona.faction_cooldown == getattr(layers, "FACTION_COOLDOWN_TICKS")
    assert engine.event_log[-1]["source"] == "drift"

    for _ in range(getattr(layers, "FACTION_COOLDOWN_TICKS")):
        engine._tick_faction_cooldown(pid)
    assert persona.faction_cooldown == 0
    engine._tick_faction_cooldown(pid)
    assert persona.faction_cooldown == 0


def test_d3_change_persona_faction_rejects_unknown_inputs() -> None:
    engine = _fresh_engine()
    pid = sorted(engine.personas)[0]
    fid = "faction_a"
    engine.factions[fid] = _make_faction(fid, pid)

    for kwargs in (
        {"new_faction_id": "missing", "source": "affiliation"},
        {"new_faction_id": fid, "source": "invalid"},
    ):
        raised = False
        try:
            engine._change_persona_faction(pid, **kwargs)
        except ValueError:
            raised = True
        assert raised, f"expected ValueError for {kwargs!r}"


def test_d4_affiliation_kernel_updates_innerworld_scores() -> None:
    from Projects.personas.loom.ontology import layers

    engine = _fresh_engine()
    pid = sorted(engine.personas)[0]
    fid_a = "faction_a"
    fid_b = "faction_b"
    engine.factions = {
        fid_a: _make_faction(fid_a, pid),
        fid_b: _make_faction(fid_b, pid),
    }
    engine.inners[pid].affiliation_scores = {fid_a: 2.0}

    patches = {
        "_same_territory": lambda persona, faction_id: 1.0 if faction_id == fid_a else 0.0,
        "_trust_density": lambda persona, faction_id: 1.0 if faction_id == fid_a else 0.0,
        "_shared_grievance": lambda persona, faction_id: 1.0 if faction_id == fid_a else 0.0,
        "_spatial_proximity": lambda persona, faction_id: 1.0 if faction_id == fid_a else 0.0,
    }
    originals = {name: (hasattr(engine, name), getattr(engine, name, None)) for name in patches}
    try:
        for name, replacement in patches.items():
            setattr(engine, name, replacement)
        engine._compute_affiliation_tick()
    finally:
        for name, (had_attr, original) in originals.items():
            if had_attr:
                setattr(engine, name, original)
            elif hasattr(engine, name):
                delattr(engine, name)

    expected_a = (
        layers.DECAY * 2.0
        + layers.W_TERRITORY_SAME
        + layers.W_TRUST
        + layers.W_GRIEVANCE
        + layers.W_PROXIMITY
    )
    expected_b = layers.W_TERRITORY_DIFF
    assert abs(engine.inners[pid].affiliation_scores[fid_a] - expected_a) < 1e-6
    assert abs(engine.inners[pid].affiliation_scores[fid_b] - expected_b) < 1e-6
    assert getattr(engine.personas[pid], "affiliation_scores", None) is None


def test_d5_commit_loop_respects_thresholds_and_cooldown() -> None:
    from Projects.personas.loom.ontology import layers

    engine = _fresh_engine()
    pids = sorted(engine.personas)[:3]
    fid_a = "faction_a"
    fid_b = "faction_b"
    engine.factions = {
        fid_a: _make_faction(fid_a, pids[0]),
        fid_b: _make_faction(fid_b, pids[0]),
    }
    engine.time.tick = getattr(layers, "FACTION_COMMIT_EVERY")

    engine.personas[pids[0]].faction = None
    engine.personas[pids[0]].faction_cooldown = 0
    engine.inners[pids[0]].affiliation_scores = {
        fid_a: getattr(layers, "THETA_JOIN") + 0.1,
        fid_b: 0.0,
    }

    engine.personas[pids[1]].faction = fid_a
    engine.personas[pids[1]].faction_cooldown = 0
    engine.inners[pids[1]].affiliation_scores = {
        fid_a: 1.0,
        fid_b: 1.0 + getattr(layers, "DRIFT_MARGIN") + 0.1,
    }

    engine.personas[pids[2]].faction = fid_b
    engine.personas[pids[2]].faction_cooldown = getattr(layers, "FACTION_COOLDOWN_TICKS")
    engine.inners[pids[2]].affiliation_scores = {
        fid_a: 10.0,
        fid_b: 0.0,
    }

    engine._commit_faction_tick()

    assert engine.personas[pids[0]].faction == fid_a
    assert engine.personas[pids[1]].faction == fid_b
    assert engine.personas[pids[2]].faction == fid_b
    assert engine.personas[pids[2]].faction_cooldown == getattr(layers, "FACTION_COOLDOWN_TICKS")


def test_d6_founder_seed_generator_is_deterministic() -> None:
    def _snapshot(seed: int):
        engine = _fresh_engine(seed=seed)
        engine._init_founder_seeds()
        factions = sorted(
            (
                faction.id,
                faction.founder_pid,
                faction.charter,
                faction.created_tick,
            )
            for faction in engine.factions.values()
        )
        founders = [f.founder_pid for f in engine.factions.values()]
        return engine, factions, founders

    engine_a, factions_a, founders_a = _snapshot(42)
    _, factions_b, founders_b = _snapshot(42)

    assert factions_a == factions_b
    assert founders_a == founders_b
    assert len(founders_a) == len(set(founders_a))
    assert len(engine_a.factions) <= len(engine_a.territories)
    for faction in engine_a.factions.values():
        assert 3 <= len(faction.charter) <= 5
        assert len(set(faction.charter)) == len(faction.charter)


def test_d7_territory_projection_uses_majority_and_hysteresis() -> None:
    from Projects.personas.loom.ontology import layers

    engine = _fresh_engine()
    fid_a = "faction_a"
    fid_b = "faction_b"
    engine.factions = {
        fid_a: _make_faction(fid_a, "p0"),
        fid_b: _make_faction(fid_b, "p0"),
    }

    target_tid = Counter(persona.territory for persona in engine.personas.values()).most_common(1)[0][0]
    residents = [
        (pid, persona)
        for pid, persona in sorted(engine.personas.items())
        if persona.territory == target_tid
    ]
    if len(residents) < 4:
        extras = [
            (pid, persona)
            for pid, persona in sorted(engine.personas.items())
            if persona.territory != target_tid
        ][: 4 - len(residents)]
        for _pid, persona in extras:
            persona.territory = target_tid
        residents = [
            (pid, persona)
            for pid, persona in sorted(engine.personas.items())
            if persona.territory == target_tid
        ]
    assert len(residents) >= 4, "phase 17 faction projection fixture needs at least 4 residents"

    for index, (pid, persona) in enumerate(residents):
        persona.faction = fid_a if index < 3 else fid_b
    engine.territories[target_tid].factionRef = None
    engine.time.tick = getattr(layers, "FACTION_PROJECT_EVERY")
    engine._project_faction_tick()
    assert engine.territories[target_tid].factionRef == fid_a

    engine.territories[target_tid].factionRef = fid_b
    for index, (_pid, persona) in enumerate(residents):
        persona.faction = fid_a if index < 2 else fid_b
    engine._project_faction_tick()
    assert engine.territories[target_tid].factionRef == fid_b
    assert getattr(layers, "FACTION_HYSTERESIS") == 2


def test_d8_faction_ssot_write_is_whitelisted() -> None:
    loom_root = ROOT / "Projects" / "personas" / "loom"
    violations: list[str] = []
    for subdir in ("core", "ontology", "physis", "brain"):
        for path in (loom_root / subdir).rglob("*.py"):
            src = path.read_text(encoding="utf-8")
            tree = ast.parse(src)
            lines = src.splitlines()
            for lineno, attr, kind in _scan_faction_writes(tree, lines):
                violations.append(
                    f"{path.relative_to(loom_root)}:{lineno}  persona.{attr} [{kind}]"
                )
    assert not violations, (
        "Phase 17 faction SSoT write paths must go through "
        "`_change_persona_faction()` / `_tick_faction_cooldown()`.\n"
        "Add `# noqa: PHASE17_FACTION_SSOT_WRITE` only on the helper write lines.\n\n"
        + "\n".join(violations)
    )


def test_d9_faction_telemetry_applies_expected_biases() -> None:
    from Projects.personas.loom.ontology import layers

    engine = _fresh_engine()
    pid = sorted(engine.personas)[0]
    fid_a = "faction_a"
    fid_b = "faction_b"
    engine.factions = {
        fid_a: _make_faction(fid_a, pid),
        fid_b: _make_faction(fid_b, pid),
    }
    engine.personas[pid].faction = fid_a
    engine.personas[pid].territory = next(iter(engine.territories))

    original = getattr(engine, "_collect_neighbor_faction_ids", None)
    try:
        engine._collect_neighbor_faction_ids = lambda territory_id: {fid_b}
        current = np.zeros(400, dtype=np.float32)
        engine._apply_faction_telemetry(pid, current)
        assert np.allclose(current[300:325], layers.FACTION_TELEMETRY_BIAS_OWN)
        assert np.allclose(current[325:350], layers.FACTION_TELEMETRY_BIAS_NEIGHBOR)

        engine.personas[pid].faction = None
        current = np.zeros(400, dtype=np.float32)
        engine._collect_neighbor_faction_ids = lambda territory_id: set()
        engine._apply_faction_telemetry(pid, current)
        assert np.allclose(current[300:350], 0.0)
    finally:
        if original is not None:
            engine._collect_neighbor_faction_ids = original
        elif hasattr(engine, "_collect_neighbor_faction_ids"):
            delattr(engine, "_collect_neighbor_faction_ids")


def test_d10_handoff_api_shapes_and_empty_cases() -> None:
    from Projects.personas.loom.ontology import layers

    engine = _fresh_engine()
    by_territory: dict[str, list[str]] = {}
    for pid, persona in sorted(engine.personas.items()):
        by_territory.setdefault(persona.territory, []).append(pid)
    territory_ids = sorted(by_territory)
    tid_a = territory_ids[0]
    tid_b = next(tid for tid in territory_ids if tid != tid_a)
    pids = by_territory[tid_a][:2] + by_territory[tid_b][:1]
    fid_a = "faction_a"
    fid_b = "faction_b"
    engine.factions = {
        fid_a: _make_faction(fid_a, pids[0]),
        fid_b: _make_faction(fid_b, pids[0]),
    }

    for pid, gold in zip(pids, (10.0, 0.0, 5.0)):
        engine.personas[pid].faction = fid_a if pid != pids[2] else None
        engine.wallets[pid] = layers.Wallet(persona_id=pid, gold=gold)

    engine.territories[tid_a].factionRef = fid_a
    engine.territories[tid_b].factionRef = fid_b
    engine.inners[pids[0]].grievance = 0.6
    engine.inners[pids[0]].grievance_lord_id = "lord_a"
    engine.inners[pids[1]].grievance = 0.6
    engine.inners[pids[1]].grievance_lord_id = "lord_a"
    engine.inners[pids[2]].grievance = 0.2
    engine.inners[pids[2]].grievance_lord_id = None

    original_within = getattr(engine, "_territories_within", None)
    original_trust = getattr(engine, "_get_relationship_trust", None)
    try:
        engine._territories_within = lambda tid, radius: {tid_b} if tid == tid_a and radius == 1 else set()
        engine._get_relationship_trust = lambda a, b: 0.25 if {a, b} == {pids[0], pids[1]} else 0.0

        population = engine.faction_population_distribution()
        assert population[fid_a] == 2
        assert population[fid_b] == 0

        territory = engine.faction_territory_distribution()
        assert territory[fid_a] == [tid_a]
        assert territory[fid_b] == [tid_b]

        raised = False
        try:
            engine.faction_charter_primitives("missing")
        except KeyError:
            raised = True
        assert raised

        raised = False
        try:
            engine.factions_in_contact(radius=0)
        except ValueError:
            raised = True
        assert raised

        wealth = engine.faction_wealth_distribution()
        assert wealth[fid_b] == {
            "total": 0.0,
            "mean": 0.0,
            "gini": 0.0,
            "top_decile_share": 0.0,
        }
        assert wealth[fid_a]["total"] == 10.0
        assert wealth[fid_a]["mean"] == 5.0

        contact = engine.factions_in_contact(radius=1)
        assert contact == [(fid_a, fid_b)]

        social = engine.faction_social_matrix()
        assert social == {}

        grievance = engine.faction_grievance_targets()
        assert grievance[fid_a] == {"lord_a": 2}
        assert grievance[fid_b] == {}
    finally:
        if original_within is not None:
            engine._territories_within = original_within
        elif hasattr(engine, "_territories_within"):
            delattr(engine, "_territories_within")
        if original_trust is not None:
            engine._get_relationship_trust = original_trust
        elif hasattr(engine, "_get_relationship_trust"):
            delattr(engine, "_get_relationship_trust")


def test_d11_adjacency_helpers_cover_radius_and_cache_copy() -> None:
    from Projects.personas.loom.ontology import layers

    engine = _fresh_engine()
    tid_a = "territory_a"
    tid_b = "territory_b"
    engine.territories = {
        tid_a: layers.Territory(id=tid_a, name=tid_a, region="claude"),
        tid_b: layers.Territory(id=tid_b, name=tid_b, region="codex"),
    }

    for y in range(3):
        for x in range(3):
            engine.world.get_cell(x, y).territoryRef = tid_a
    engine.world.get_cell(1, 0).territoryRef = tid_b
    engine.world.get_cell(2, 2).territoryRef = tid_b

    neighbors = engine._territory_neighbors(tid_a)
    within_one = engine._territories_within(tid_a, 1)
    assert tid_b in neighbors
    assert within_one == neighbors

    mutated = engine._territories_within(tid_a, 1)
    mutated.add("bogus")
    assert "bogus" not in engine._territories_within(tid_a, 1)

    raised = False
    try:
        engine._territories_within(tid_a, 0)
    except ValueError:
        raised = True
    assert raised
    assert engine._territories_within("missing", 1) == set()


if __name__ == "__main__":
    tests = [
        test_d1_faction_dataclass_contract,
        test_d2_persona_and_innerworld_faction_fields,
        test_d3_change_persona_faction_and_cooldown,
        test_d3_change_persona_faction_rejects_unknown_inputs,
        test_d4_affiliation_kernel_updates_innerworld_scores,
        test_d5_commit_loop_respects_thresholds_and_cooldown,
        test_d6_founder_seed_generator_is_deterministic,
        test_d7_territory_projection_uses_majority_and_hysteresis,
        test_d8_faction_ssot_write_is_whitelisted,
        test_d9_faction_telemetry_applies_expected_biases,
        test_d10_handoff_api_shapes_and_empty_cases,
        test_d11_adjacency_helpers_cover_radius_and_cache_copy,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {test.__name__}")
            traceback.print_exc()
    sys.exit(0 if failed == 0 else 1)
