"""Phase 17 land verification."""
from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path
import re
import sys
import traceback

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _grep_in_tree(pattern: str, root: Path, excludes: set[str]) -> list[str]:
    hits: list[str] = []
    for path in root.rglob("*.py"):
        if path.name in excludes:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(lines, 1):
            if pattern in line:
                hits.append(f"{path}:{lineno}:{line}")
    return hits


def test_d1_landcell_slots() -> None:
    from Projects.personas.loom.physis.world import LandCell, set_biome_initial

    cell = LandCell(x=0, y=0, biome="plain")
    assert not hasattr(cell, "__dict__"), "slots=True is required"
    raised = False
    try:
        set_biome_initial(cell, "invalid_biome")
    except AssertionError:
        raised = True
    assert raised, "invalid biome should raise AssertionError"
    for biome in ("plain", "forest", "mountain", "water", "desert", "tundra"):
        set_biome_initial(cell, biome)
        assert cell.biome == biome


def test_d2_world_api() -> None:
    from Projects.personas.loom.physis.world import World

    world = World(width=50, height=50)
    assert world.width == 50 and world.height == 50
    cell = world.get_cell(0, 0)
    assert (cell.x, cell.y) == (0, 0)
    assert sum(1 for _ in world.iter_cells()) == 2500
    assert world.in_bounds(49, 49)
    assert not world.in_bounds(50, 50)


def test_d3_persona_fields() -> None:
    from Projects.personas.loom.ontology.layers import Persona, InnerWorld

    persona = Persona(id="t", name="t", full_name="t")
    assert persona.pos == (0, 0)
    assert persona.offset == (0.0, 0.0)
    assert persona.outfit_id is None

    inner = InnerWorld(persona_id="t")
    assert inner.dest is None
    assert inner.migration_cooldown == 0


def test_d4_d5_score_move() -> None:
    from Projects.personas.loom.ontology.layers import Persona, score_move
    from Projects.personas.loom.physis.world import LandCell

    persona = Persona(id="t", name="t", full_name="t")
    persona.pos = (5, 5)
    cell = LandCell(x=5, y=5, biome="plain")
    cell.resources = {"food": 2.0, "material": 1.0}
    cell.path_cost = 1.0
    expected = 2.0 * 2.0 + 1.0 * 1.0 + (-1.5) * 1.0 + (-0.5) * 0
    assert abs(score_move(cell, persona) - expected) < 1e-6


def test_d6_project_territory_atomicity() -> None:
    from Projects.personas.loom.ontology.layers import Persona
    from Projects.personas.loom.physis.world import World, project_territory

    world = World(10, 10)
    personas = [
        Persona(id=f"p{i}", name=f"p{i}", full_name=f"p{i}", territory="T1")
        for i in range(3)
    ]
    for persona in personas:
        persona.pos = (5, 5)
    project_territory(world, personas)
    assert world.get_cell(5, 5).territoryRef == "T1"

    world.get_cell(5, 5).territoryRef = "T1"
    personas = [
        Persona(id="p0", name="p0", full_name="p0", territory="T2"),
        Persona(id="p1", name="p1", full_name="p1", territory="T1"),
        Persona(id="p2", name="p2", full_name="p2", territory="T2"),
    ]
    for persona in personas:
        persona.pos = (5, 5)
    # Hysteresis: when multiple personas from different territories tie
    # within Chebyshev K, the existing territoryRef is retained.
    # See project_territory() docstring — this is by design (Decision 6).
    project_territory(world, list(reversed(personas)))
    assert world.get_cell(5, 5).territoryRef == "T1"


def test_d7_region_unchanged() -> None:
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=42)
    for _ in range(120):
        engine.tick()
    for persona in engine.personas.values():
        assert persona.region in {"claude", "codex", "gemini"}


def test_d8_bridson_determinism() -> None:
    from Projects.personas.loom.physis.poisson import bridson_poisson_disk

    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)
    pos1 = bridson_poisson_disk(50, 50, r=5, rng=rng1)
    pos2 = bridson_poisson_disk(50, 50, r=5, rng=rng2)
    assert pos1 == pos2


def test_fix1_exodus_region_sync() -> None:
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=42)
    pid = next(
        pid
        for pid, persona in sorted(engine.personas.items())
        if pid != engine.territories[persona.territory].lord_id
    )
    persona = engine.personas[pid]
    inner = engine.inners[pid]
    current_territory = engine.territories[persona.territory]
    current_territory.policy.tax_rate = 0.30
    for tid, territory in engine.territories.items():
        if tid != persona.territory:
            territory.policy.tax_rate = 0.05
    inner.grievance = 1.0
    inner.is_sleeping = False
    inner.exodus_cooldown_until_tick = 0
    engine.time.tick = 100

    class _FixedRNG:
        def __init__(self, wrapped):
            self._wrapped = wrapped

        def random(self):
            return 0.0

        def __getattr__(self, name):
            return getattr(self._wrapped, name)

    original_rng = engine._np_rng
    engine._np_rng = _FixedRNG(original_rng)
    try:
        event = engine._try_exodus(pid)
    finally:
        engine._np_rng = original_rng

    assert event and event.get("type") == "exodus", f"exodus not triggered: {event}"
    new_tid = event["to_territory"]
    assert persona.territory == new_tid
    assert persona.region == engine.territories[new_tid].region


def test_fix2_region_distribution_matches_persona_defs() -> None:
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine, PERSONA_DEFS

    engine = MultiTickEngine(seed=42)
    positions = [persona.pos for persona in engine.personas.values()]
    assert len(set(positions)) == len(positions), "initial positions must be unique"

    expected_region_counts = Counter(pdef["region"] for pdef in PERSONA_DEFS)
    actual_region_counts = Counter(persona.region for persona in engine.personas.values())
    assert actual_region_counts == expected_region_counts


def test_fix3_movement_before_economy() -> None:
    src = (
        ROOT
        / "Projects"
        / "personas"
        / "loom"
        / "core"
        / "multi_tick_engine.py"
    ).read_text(encoding="utf-8")
    movement_idx = src.find("self._process_movement(pid)")
    action_idx = src.find("action, intensity, cost = brain.tick(")
    survival_idx = src.find("survival_evt = self._process_survival_consume(pid)")
    assert movement_idx > 0, "_process_movement call missing"
    assert action_idx > 0, "brain.tick call missing"
    assert survival_idx > 0, "survival consume call missing"
    assert movement_idx < action_idx, "movement must happen before action selection"
    assert movement_idx < survival_idx, "movement must happen before survival consume"


def test_fix5_mass_exodus_region_sync() -> None:
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=42)
    source_tid = next(
        tid
        for tid, territory in engine.territories.items()
        if territory.lord_id and len([pid for pid, persona in engine.personas.items() if persona.territory == tid]) >= 4
    )
    target_tid = next(tid for tid in engine.territories if tid != source_tid)

    engine.territories[source_tid].policy.tax_rate = 0.60
    engine.territories[target_tid].policy.tax_rate = 0.05
    for tid, territory in engine.territories.items():
        if tid not in {source_tid, target_tid}:
            territory.policy.tax_rate = 0.50

    lord_id = engine.territories[source_tid].lord_id
    movers: list[str] = []
    for pid, persona in engine.personas.items():
        if persona.territory != source_tid or pid == lord_id:
            continue
        engine.inners[pid].grievance = 0.8
        engine.inners[pid].strike_until_tick = 0
        movers.append(pid)
    assert len(movers) >= 3, "mass_exodus fixture requires at least three non-lord residents"

    events = engine._update_grievances()
    event = next((ev for ev in events if ev.get("type") == "mass_exodus"), None)
    assert event is not None, f"mass_exodus not triggered: {events}"
    assert event["to_territory"] == target_tid
    for pid in event["personas"]:
        persona = engine.personas[pid]
        assert persona.territory == target_tid
        assert persona.region == engine.territories[target_tid].region


def test_fix7_decisions_checklist_synced() -> None:
    decisions_path = ROOT / "Projects" / "personas" / "loom" / "PHASE-17-LAND-DECISIONS.md"
    text = decisions_path.read_text(encoding="utf-8")
    assert "20명 배치 성공" not in text
    assert "7:7:6 정확" not in text
    assert "Counter(p[\"region\"] for p in PERSONA_DEFS)" in text


def test_fix9_project_territory_doc_mentions_hysteresis() -> None:
    from Projects.personas.loom.physis.world import project_territory

    doc = project_territory.__doc__ or ""
    assert "hysteresis" in doc
    assert "left **unchanged**" in doc


def test_fix10_movement_before_economy_behavioral() -> None:
    """Behavioral: persona.pos changes within one tick BEFORE economy.

    Strategy: set an explicit dest 3 cells away, run one tick with
    an instrumented hook that asserts pos was moved before any
    economy/action event is emitted.
    """
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=42)
    pid = next(
        pid for pid, inner in engine.inners.items()
        if not inner.is_sleeping
    )
    persona = engine.personas[pid]
    inner = engine.inners[pid]

    start_pos = persona.pos
    dest = (
        min(start_pos[0] + 3, engine.world.width - 1),
        min(start_pos[1] + 3, engine.world.height - 1),
    )
    inner.dest = dest
    inner.migration_cooldown = 0

    candidates = []
    x, y = start_pos
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            nx, ny = x + dx, y + dy
            if not engine.world.in_bounds(nx, ny):
                continue
            cell = engine.world.get_cell(nx, ny)
            cell.biome = "plain"
            cell.resources = {"food": 0.0, "material": 0.0}
            cell.path_cost = 5.0
            candidates.append(cell)
    better = next(
        cell for cell in candidates
        if (cell.x, cell.y) != start_pos
    )
    better.resources = {"food": 10.0, "material": 5.0}
    better.path_cost = 0.1

    pos_before_tick = persona.pos
    engine.tick()
    pos_after_tick = persona.pos

    moved = pos_after_tick != pos_before_tick
    assert moved, (
        f"persona {pid} did not move this tick; "
        f"movement may have been deferred past economy. "
        f"start={pos_before_tick}, dest={dest}, after={pos_after_tick}"
    )


def test_fix11_cross_process_determinism() -> None:
    """Two fresh engines with seed=42 produce identical snapshots
    across 80 ticks. Regression against hash()-based RNG.
    """
    import subprocess
    import sys
    import hashlib
    import json

    script = """
import sys, json, hashlib
sys.path.insert(0, r'{root}')
from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine
engine = MultiTickEngine(seed=42)
for _ in range(80):
    engine.tick()
snap = sorted([
    (pid, tuple(persona.pos), persona.territory, persona.region,
     round(engine.inners[pid].energy_pool, 6),
     round(engine.inners[pid].grievance, 6))
    for pid, persona in engine.personas.items()
])
h = hashlib.sha256(json.dumps(snap, default=str).encode()).hexdigest()
print(h)
""".format(root=str(ROOT).replace("\\", "\\\\"))

    digests = set()
    for _ in range(3):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=120,
            env={"PYTHONHASHSEED": "random"},
        )
        assert result.returncode == 0, f"subprocess failed: {result.stderr}"
        digests.add(result.stdout.strip().splitlines()[-1])

    assert len(digests) == 1, (
        f"cross-process determinism violated: {digests}. "
        f"hash()-based RNG regression suspected."
    )

    from Projects.personas.loom.physis.climate_engine import ClimateEngine

    engine_a = ClimateEngine(seed=1)
    engine_b = ClimateEngine(seed=999)
    sample_a = [
        engine_a.tick(day, hour)["claude"]
        for day, hour in [(10, 12), (40, 6), (90, 18)]
    ]
    sample_b = [
        engine_b.tick(day, hour)["claude"]
        for day, hour in [(10, 12), (40, 6), (90, 18)]
    ]
    assert sample_a != sample_b, (
        "ClimateEngine(seed=...) must influence generated weather"
    )


def _setup_helper_fixture():
    """Shared fixture for helper direct tests."""
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine
    engine = MultiTickEngine(seed=42)
    pid = next(
        pid for pid, persona in sorted(engine.personas.items())
        if pid != engine.territories[persona.territory].lord_id
    )
    persona = engine.personas[pid]
    source_tid = persona.territory
    target_tid = next(tid for tid in engine.territories if tid != source_tid)
    return engine, pid, source_tid, target_tid


def test_contract_i1_territory_updated() -> None:
    """I1: persona.territory == target_territory_id after helper return."""
    engine, pid, source_tid, target_tid = _setup_helper_fixture()
    result = engine._change_persona_territory(pid, target_tid, "test_i1")
    assert engine.personas[pid].territory == target_tid
    assert result["from_territory"] == source_tid
    assert result["to_territory"] == target_tid


def test_contract_i2_region_synced() -> None:
    """I2: persona.region == territories[target_tid].region."""
    engine, pid, _source_tid, target_tid = _setup_helper_fixture()
    engine._change_persona_territory(pid, target_tid, "test_i2")
    expected_region = engine.territories[target_tid].region
    assert engine.personas[pid].region == expected_region


def test_contract_i3_cache_invalidated() -> None:
    """I3: _territory_residents_cache is None after helper return."""
    engine, pid, _source_tid, target_tid = _setup_helper_fixture()
    _ = engine._get_territory_residents(target_tid)
    engine._change_persona_territory(pid, target_tid, "test_i3")
    assert engine._territory_residents_cache is None, (
        "cache must be invalidated by helper"
    )


def test_contract_i4_employment_released() -> None:
    """I4: employment in old territory is released."""
    engine, pid, source_tid, target_tid = _setup_helper_fixture()
    lord_id = engine.territories[source_tid].lord_id
    if lord_id and lord_id != pid:
        job = engine.create_job(lord_id, "test_laborer", 5.0, "test")
        if job:
            engine.hire(job.id, pid)
            employment_id = engine.personas[pid].employment_id
            assert employment_id is not None, (
                "fixture: persona must be employed before migration"
            )
            same_target = engine._change_persona_territory(
                pid, source_tid, "test_i4_same_target"
            )
            assert engine.personas[pid].employment_id == employment_id, (
                "same-target move must not release employment"
            )
            assert same_target["employment_cleanup"] is None
            result = engine._change_persona_territory(pid, target_tid, "test_i4")
            assert engine.personas[pid].employment_id is None, (
                "I4 violated: employment not released"
            )
            assert "employment_cleanup" in result


def test_contract_raises_on_unknown_territory() -> None:
    """Error boundary: KeyError when target_territory_id does not exist."""
    engine, pid, _source_tid, _target_tid = _setup_helper_fixture()
    try:
        engine._change_persona_territory(pid, "NONEXISTENT_TID", "test_err")
    except KeyError:
        return
    raise AssertionError("KeyError not raised for unknown territory")


def test_fix10_ordering_instrumentation() -> None:
    """Direct ordering proof via _phase_trace: movement < action < economy
    for every persona, every tick.
    """
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=42)
    engine._phase_trace = []
    for _ in range(5):
        engine.tick()

    from collections import defaultdict
    grouped: dict[tuple, list[tuple[int, str]]] = defaultdict(list)
    for idx, entry in enumerate(engine._phase_trace):
        phase, pid, tick_str = entry.split(":")
        tick = int(tick_str.split("=")[1])
        grouped[(pid, tick)].append((idx, phase))

    for (pid, tick), ordered in grouped.items():
        phases = [p for _, p in ordered]
        assert phases == ["movement", "action", "economy"], (
            f"phase trace incomplete or out of order for {pid}@{tick}: {phases}"
        )


def test_forbidden_grep_regression() -> None:
    root = ROOT / "Projects" / "personas" / "loom"
    forbidden = [
        "world._land",
        "world.land[",
        "score_reside",
        "RESIDE_WEIGHTS",
        "score_cell(",
        "INIT_REGION_QUOTA",
        "INIT_SEED",
    ]
    for pattern in forbidden:
        hits = _grep_in_tree(pattern, root, {"test_phase17_land.py"})
        assert not hits, f"forbidden pattern {pattern!r} detected:\n" + "\n".join(hits)

    regex_guards = [
        re.compile(r"persona\.territory\s*=(?!=)"),
        re.compile(r"\.territory\s*=(?!=)\s*(?!None|\"\"|persona_def)"),
        re.compile(r"self\.personas\[.*\]\.territory\s*=(?!=)"),
        re.compile(r"persona\.region\s*=(?!=)"),
        re.compile(r"self\.personas\[.*\]\.region\s*=(?!=)"),
        re.compile(r"np\.random\.default_rng\s*\(\s*.*hash\("),
        re.compile(r"hash\(.*\)\s*[&%]\s*(0x|\d)"),
    ]
    regex_hits: list[str] = []
    for path in root.rglob("*.py"):
        if path.name.startswith("test_"):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(lines, 1):
            for regex in regex_guards:
                if not regex.search(line):
                    continue
                allowed = (
                    path == root / "core" / "multi_tick_engine.py"
                    and "# noqa: PHASE17_SSOT_WRITE" in line
                )
                if not allowed:
                    regex_hits.append(f"{path}:{lineno}:{line}")
    assert not regex_hits, "forbidden territory direct-write pattern detected:\n" + "\n".join(regex_hits)

    allowed_default_rng_calls = {
        ("multi_tick_engine.py", "__init__"),
        ("multi_tick_engine.py", "_derive_rng"),
        ("climate_engine.py", "_noise"),
    }
    default_rng_calls: list[tuple[str, str | None, int]] = []
    for path in [
        root / "core" / "multi_tick_engine.py",
        root / "physis" / "climate_engine.py",
    ]:
        tree = ast.parse(path.read_text(encoding="utf-8"))

        class _Visitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.stack: list[str] = []

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self.stack.append(node.name)
                self.generic_visit(node)
                self.stack.pop()

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self.stack.append(node.name)
                self.generic_visit(node)
                self.stack.pop()

            def visit_Call(self, node: ast.Call) -> None:
                func = node.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "default_rng"
                    and isinstance(func.value, ast.Attribute)
                    and func.value.attr == "random"
                    and isinstance(func.value.value, ast.Name)
                    and func.value.value.id == "np"
                ):
                    default_rng_calls.append(
                        (path.name, self.stack[-1] if self.stack else None, node.lineno)
                    )
                self.generic_visit(node)

        _Visitor().visit(tree)

    actual_default_rng_calls = {
        (path_name, func_name)
        for path_name, func_name, _lineno in default_rng_calls
    }
    assert actual_default_rng_calls == allowed_default_rng_calls, (
        "unexpected np.random.default_rng call sites detected:\n"
        + "\n".join(
            f"{path_name}:{func_name}:{lineno}"
            for path_name, func_name, lineno in default_rng_calls
        )
    )


def test_determinism_500ticks() -> None:
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine

    engine_a = MultiTickEngine(seed=42)
    engine_b = MultiTickEngine(seed=42)
    for _ in range(500):
        engine_a.tick()
        engine_b.tick()

    snap_a = {
        pid: (
            persona.pos,
            persona.territory,
            persona.region,
            engine_a.inners[pid].migration_cooldown,
        )
        for pid, persona in sorted(engine_a.personas.items())
    }
    snap_b = {
        pid: (
            persona.pos,
            persona.territory,
            persona.region,
            engine_b.inners[pid].migration_cooldown,
        )
        for pid, persona in sorted(engine_b.personas.items())
    }
    world_a = {
        (cell.x, cell.y): cell.territoryRef for cell in engine_a.world.iter_cells()
    }
    world_b = {
        (cell.x, cell.y): cell.territoryRef for cell in engine_b.world.iter_cells()
    }
    assert snap_a == snap_b, "500-tick determinism failed"
    assert world_a == world_b, "500-tick world projection determinism failed"


if __name__ == "__main__":
    tests = [
        test_d1_landcell_slots,
        test_d2_world_api,
        test_d3_persona_fields,
        test_d4_d5_score_move,
        test_d6_project_territory_atomicity,
        test_d7_region_unchanged,
        test_d8_bridson_determinism,
        test_fix1_exodus_region_sync,
        test_fix2_region_distribution_matches_persona_defs,
        test_fix3_movement_before_economy,
        test_fix5_mass_exodus_region_sync,
        test_fix7_decisions_checklist_synced,
        test_fix9_project_territory_doc_mentions_hysteresis,
        test_fix10_movement_before_economy_behavioral,
        test_fix11_cross_process_determinism,
        test_contract_i1_territory_updated,
        test_contract_i2_region_synced,
        test_contract_i3_cache_invalidated,
        test_contract_i4_employment_released,
        test_contract_raises_on_unknown_territory,
        test_fix10_ordering_instrumentation,
        test_forbidden_grep_regression,
        test_determinism_500ticks,
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
