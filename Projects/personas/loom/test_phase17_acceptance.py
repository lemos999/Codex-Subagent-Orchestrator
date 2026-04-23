"""Phase 17 / Φ-1 Land — single-entry acceptance gate.

Run with: `py test_phase17_acceptance.py`
Exit 0 on PASS, non-zero on any FAIL.
"""
from __future__ import annotations

import os
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


def _measure_tick_ms(n_ticks: int = 100) -> float:
    from core.multi_tick_engine import MultiTickEngine
    engine = MultiTickEngine(seed=42)
    start = time.perf_counter()
    for _ in range(n_ticks):
        engine.tick()
    elapsed_ms = (time.perf_counter() - start) * 1000.0 / n_ticks
    return elapsed_ms


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

    elapsed = _measure_tick_ms(n_ticks=100)
    perf_ok = elapsed <= 250.0
    status = "PASS" if perf_ok else "FAIL"
    print(f"[{status}] tick_performance: {elapsed:.1f} ms/tick (contract ≤ 250)")
    if not perf_ok:
        failures.append(f"performance ({elapsed:.1f}ms)")

    print()
    if failures:
        print(f"Phase 17 Φ-1 Acceptance: FAIL ({len(failures)} failures)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("Phase 17 Φ-1 Acceptance: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
