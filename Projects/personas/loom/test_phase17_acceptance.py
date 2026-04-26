"""Phase 17 acceptance gate and Stage 4 closure checks.

spec functional-equivalence: stable_perf_median_p95, faction_kernel_0_960,
seed42_perf_line, five_channel_determinism.

Run with: `py test_phase17_acceptance.py`
Exit 0 on PASS, non-zero on any FAIL.
"""
from __future__ import annotations

import gc
import hashlib
import os
import pickle
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _run(cmd: list[str], label: str) -> bool:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=ROOT,
        env=env,
    )
    ok = result.returncode == 0
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {label}")
    if not ok:
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
    return ok


def _measure_tick_ms_stable(seed: int = 42) -> tuple[float, float, list[float]]:
    from core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=seed)
    for _ in range(100):
        engine.tick()
    gc.collect()

    samples: list[float] = []
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(100):
            engine.tick()
        samples.append((time.perf_counter() - start) * 1000.0 / 100.0)

    ordered = sorted(samples)
    median = ordered[len(ordered) // 2]
    p95 = ordered[3]
    return median, p95, samples


def _format_tick_perf(median: float, p95: float, samples: list[float]) -> str:
    sample_text = ",".join(f"{sample:.1f}" for sample in samples)
    return f"[perf] tick(ms)  median={median:.1f}  p95={p95:.1f}  samples=[{sample_text}]"


def _prepare_respawn_probe_engine(seed: int = 42):
    from core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=seed)
    first_fid = next(iter(engine.factions))
    for pid in sorted(engine.personas):
        engine._change_persona_faction(pid, first_fid, source="drift")
    engine._rebuild_faction_members_cache()
    return engine


def _measure_faction_kernel_ms(seed: int = 42) -> dict[str, float]:
    from ontology.layers import FOUNDER_RESPAWN_EVERY

    engine = _prepare_respawn_probe_engine(seed=seed)
    respawn_events_before = sum(
        1 for event in engine.event_log
        if event.get("type") == "faction_change" and event.get("source") == "birth_founder"
    )
    totals = {
        "affiliation": 0.0,
        "commit": 0.0,
        "project": 0.0,
        "respawn": 0.0,
    }
    total_ticks = FOUNDER_RESPAWN_EVERY * 2

    for tick in range(1, total_ticks + 1):
        engine.time.tick = tick

        start = time.perf_counter()
        engine._compute_affiliation_tick()
        totals["affiliation"] += (time.perf_counter() - start) * 1000.0

        start = time.perf_counter()
        engine._commit_faction_tick()
        totals["commit"] += (time.perf_counter() - start) * 1000.0

        start = time.perf_counter()
        engine._project_faction_tick()
        totals["project"] += (time.perf_counter() - start) * 1000.0

        start = time.perf_counter()
        engine._respawn_faction_tick()
        totals["respawn"] += (time.perf_counter() - start) * 1000.0

    per_tick = {name: value / total_ticks for name, value in totals.items()}
    per_tick["total"] = sum(per_tick.values())
    respawn_events_after = sum(
        1 for event in engine.event_log
        if event.get("type") == "faction_change" and event.get("source") == "birth_founder"
    )
    per_tick["respawn_events"] = float(respawn_events_after - respawn_events_before)
    return per_tick


def _format_faction_kernel_perf(kernel: dict[str, float]) -> str:
    return (
        "[perf] faction_kernel(ms/tick)  "
        f"affiliation={kernel['affiliation']:.2f}  "
        f"commit={kernel['commit']:.2f}  "
        f"project={kernel['project']:.2f}  "
        f"respawn={kernel['respawn']:.2f}  "
        f"total={kernel['total']:.2f}"
    )


def _format_observe_perf_line(median: float, kernel_total: float) -> str:
    return f"[perf] tick={median:.1f}ms  faction_kernel={kernel_total:.2f}ms  (seed=42 sample)"


def _phase17_phi2_stage4_snapshot(seed: int = 42, ticks: int = 500) -> bytes:
    from core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=seed)
    for _ in range(ticks):
        engine.tick()
    snapshot = {
        "p_faction": {
            pid: engine.personas[pid].faction
            for pid in sorted(engine.personas)
        },
        "p_cooldown": {
            pid: engine.personas[pid].faction_cooldown
            for pid in sorted(engine.personas)
        },
        "i_aff": {
            pid: dict(engine.inners[pid].affiliation_scores)
            for pid in sorted(engine.inners)
        },
        "factions": {
            fid: (
                engine.factions[fid].name,
                engine.factions[fid].founder_pid,
                tuple(engine.factions[fid].charter),
                engine.factions[fid].created_tick,
            )
            for fid in sorted(engine.factions)
        },
        "t_ref": {
            tid: engine.territories[tid].factionRef
            for tid in sorted(engine.territories)
        },
    }
    return pickle.dumps(snapshot, protocol=4)


def _phase17_phi2_stage4_hash(seed: int = 42, ticks: int = 500) -> str:
    return hashlib.sha256(_phase17_phi2_stage4_snapshot(seed=seed, ticks=ticks)).hexdigest()


def test_phase17_phi2_determinism_500_ticks_stage4() -> None:
    """Stage 4: 5-channel byte-level determinism."""
    h1 = _phase17_phi2_stage4_hash(seed=42, ticks=500)
    h2 = _phase17_phi2_stage4_hash(seed=42, ticks=500)
    assert h1 == h2, f"Phi-2 Stage 4 determinism hash mismatch ({h1} != {h2})"


def _phase17_phi2_stage5_snapshot(seed: int = 42, ticks: int = 500) -> bytes:
    from core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=seed)
    for _ in range(ticks):
        engine.tick()
    snapshot = {
        "p_faction": {pid: engine.personas[pid].faction for pid in sorted(engine.personas)},
        "p_cooldown": {pid: engine.personas[pid].faction_cooldown for pid in sorted(engine.personas)},
        "i_aff": {pid: dict(engine.inners[pid].affiliation_scores) for pid in sorted(engine.inners)},
        "i_residence": {pid: dict(engine.inners[pid].residence_ticks) for pid in sorted(engine.inners)},
        "factions": {
            fid: (
                engine.factions[fid].founder_pid,
                engine.factions[fid].grace_until_tick,
                tuple(engine.factions[fid].charter),
            )
            for fid in sorted(engine.factions)
        },
        "t_ref": {tid: engine.territories[tid].factionRef for tid in sorted(engine.territories)},
    }
    return pickle.dumps(snapshot, protocol=4)


def _phase17_phi2_stage5_hash(seed: int = 42, ticks: int = 500) -> str:
    return hashlib.sha256(_phase17_phi2_stage5_snapshot(seed=seed, ticks=ticks)).hexdigest()


def test_phase17_phi2_perf_stage4() -> None:
    median, p95, samples = _measure_tick_ms_stable(seed=42)
    print(_format_tick_perf(median, p95, samples))
    assert median <= 250.0, f"tick median budget exceeded: {median:.1f}ms"
    assert p95 <= 350.0, f"tick p95 budget exceeded: {p95:.1f}ms"


def test_phase17_phi2_faction_kernel_perf_stage4() -> None:
    kernel = _measure_faction_kernel_ms(seed=42)
    print(_format_faction_kernel_perf(kernel))
    assert kernel["respawn_events"] >= 1.0
    assert kernel["total"] <= 5.0, f"faction kernel budget exceeded: {kernel['total']:.2f}ms"


def main() -> int:
    failures: list[str] = []

    if not _run([sys.executable, "test_phase17_land.py"], "Phase 17 Land (v1+v2)"):
        failures.append("phase17_land")

    for name in [
        "test_nomos.py",
        "test_class_promotion.py",
        "test_phase16_public_works.py",
        "test_climate_impact.py",
        "test_phase14b_snn_integration.py",
        "test_phase15_collective_action.py",
    ]:
        if not _run([sys.executable, name], name):
            failures.append(name)

    median, p95, samples = _measure_tick_ms_stable(seed=42)
    print(_format_tick_perf(median, p95, samples))
    kernel = _measure_faction_kernel_ms(seed=42)
    print(_format_faction_kernel_perf(kernel))
    print(_format_observe_perf_line(median, kernel["total"]))
    perf_ok = median <= 250.0 and p95 <= 350.0 and kernel["total"] <= 5.0
    status = "PASS" if perf_ok else "FAIL"
    print(
        f"[{status}] tick_performance: median={median:.1f}ms p95={p95:.1f}ms "
        f"kernel={kernel['total']:.2f}ms"
    )
    if not perf_ok:
        failures.append(
            f"performance (median={median:.1f}ms p95={p95:.1f}ms kernel={kernel['total']:.2f}ms)"
        )

    determinism_a = _phase17_phi2_stage4_hash(seed=42, ticks=500)
    determinism_b = _phase17_phi2_stage4_hash(seed=42, ticks=500)
    determinism_ok = determinism_a == determinism_b
    status = "PASS" if determinism_ok else "FAIL"
    print(f"[{status}] phi2_stage4_determinism_500: {determinism_a} / {determinism_b}")
    if not determinism_ok:
        failures.append("phi2_stage4_determinism_500")

    stage5_a = _phase17_phi2_stage5_hash(seed=42, ticks=500)
    stage5_b = _phase17_phi2_stage5_hash(seed=42, ticks=500)
    stage5_ok = stage5_a == stage5_b
    status = "PASS" if stage5_ok else "FAIL"
    print(f"[{status}] phi2_stage5_determinism_500 (grace_until_tick+residence_ticks): {stage5_a[:16]}…")
    if not stage5_ok:
        failures.append("phi2_stage5_determinism_500")

    print()
    if failures:
        print(f"Phase 17 Acceptance: FAIL ({len(failures)} failures)")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Phase 17 Acceptance: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
