"""Phase 17 Phi-1 Land rev.next §7-1 Land-Climate probe collector (optional).

Spec authority: ``PHASE-17-LAND-REV-NEXT-DC-1-LAND-CLIMATE-PROBE-SPEC.md``
rev.0 [확정] 2026-05-07.

> **WARNING — synthetic smoke collector**: This collector uses a *random walk* in
> ``_evolve_climate()`` (line ~140), NOT the actual ``ClimateEngine``. The output
> JSON is suitable as **smoke / sample evidence only**, not as raw evidence for
> §7-2 Resource/Fertility decisions. A separate
> ``phase17_phi1_land_climate_collect_real.py`` (using
> ``physis.climate_engine.ClimateEngine``) is to be added in a follow-up PR
> before §7-2 evidence base is finalized.

This script is the *optional* collector that drives a 30-day Phi-1 land
climate probe across three deterministic seeds (7, 13, 42) and serializes
the resulting telemetry to disk for the extractor to consume.

The collector is intentionally a thin wrapper:
  - It instantiates :class:`physis.world.World` directly.
  - It invokes :class:`physis.land_climate_telemetry.LandClimateTelemetry`
    once per simulated tick to record the read-only observation.
  - It never touches ``core/`` ``ontology/`` ``struggle/`` ``brain/`` ``api/``.

If a project-internal hook for per-tick observers already exists, this
script is the canonical fallback path; otherwise it can be invoked stand-
alone. Either way, the LandCell type and the world initialization helper
are imported and used unmodified.

Output schema (one file per seed):
  ``data/phase17_phi1_land_climate_probe/seed-{N}/probe.json``::

    {
      "seed": int,
      "window_size": int,
      "tick_range": [int, int],
      "current": [<measurement>, …],
      "cumulative": [<measurement>, …]
    }

  Each measurement is the dict serialization of
  :class:`physis.land_climate_telemetry.LandClimateMeasurement`.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_ROOT = BASE_DIR / "data" / "phase17_phi1_land_climate_probe"

# Ensure the loom package root is importable when this script is invoked
# directly (``py scripts/phase17_phi1_land_climate_collect.py``). When the
# user has already configured PYTHONPATH or runs from a tooling context
# the prepend is a no-op.
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from physis.land_climate_telemetry import (  # noqa: E402  (sys.path setup above)
    DEFAULT_WINDOW_SIZE,
    LandClimateTelemetry,
)
from physis.world import World  # noqa: E402

# Spec §0.3 / §6.2 / §6.3: deterministic three-seed replay (default).
DEFAULT_SEEDS: tuple[int, ...] = (7, 13, 42)

# Probe length in observation ticks. Spec §2.2 names 30 days as the
# default rolling-window length (OQ 1); the collector therefore observes
# at least one full window so the rolling and cumulative buckets contain
# meaningful data. Any other probe length is freeze 금지 at the spec body
# level, so the constant lives here in the collector script (caller
# tweakable) rather than inside the telemetry module.
DEFAULT_PROBE_TICK_COUNT: int = DEFAULT_WINDOW_SIZE

# Default world dimensions. The probe is a Phi-1 read-only observation, so
# any modest deterministic grid suffices for distribution coverage.
WORLD_WIDTH: int = 16
WORLD_HEIGHT: int = 16


JsonObject = dict[str, Any]


def _measurement_to_dict(measurement: Any) -> JsonObject:
    """Serialize a LandClimateMeasurement dataclass to a JSON-safe dict."""
    raw = asdict(measurement)
    # Cast numpy scalars and bools to native Python types to keep the
    # serialized output stable across numpy versions.
    out: JsonObject = {}
    for key, value in raw.items():
        if isinstance(value, (bool, int, float, str)):
            out[key] = value
        else:
            out[key] = float(value)
    return out


def _initialize_world(seed: int) -> World:
    """Build a deterministic World seeded by ``seed``.

    The world is initialized via ``physis.world._init_biomes`` semantics —
    we call the public helpers only. The collector seeds a fresh
    ``np.random.Generator`` so the per-seed observations are reproducible.
    """
    from physis.world import _init_biomes  # local import: avoid cycles

    rng = np.random.default_rng(seed)
    world = World(width=WORLD_WIDTH, height=WORLD_HEIGHT)
    # _init_biomes is the authoritative biome initializer used by
    # initialize_world. Calling it directly avoids the persona placement
    # code path which is not relevant to a land-climate probe.
    _init_biomes(world, rng)
    return world


def _evolve_climate(world: World, rng: np.random.Generator, tick: int) -> None:
    """Mutate climate dict entries on each LandCell for the next tick.

    This is a *non-mechanism* random walk — the collector only feeds
    raw climate signals so the telemetry has something to observe. The
    actual climate driver is a separate concern (``physis/climate_engine``)
    and is not invoked here so the probe stays self-contained and
    deterministic without engaging the wider physics stack.

    NOTE: Mutating ``cell.climate`` is *allowed* under the spec — the only
    LandCell write the spec forbids is changing the *class definition*
    or adding new dict keys. ``cell.climate['rainfall']`` and
    ``cell.climate['temperature']`` are the two existing keys (see
    ``physis/world.py`` line 32) and we only update those.
    """
    for cell in world.iter_cells():
        rainfall_noise = float(rng.uniform(0.0, 1.0))
        temperature_noise = float(rng.uniform(-2.0, 2.0))
        # Bias rainfall toward zero on a fraction of ticks so drought_days
        # has a chance to accumulate (raw signal — no mechanism coupling).
        if rng.uniform(0.0, 1.0) < 0.3:
            rainfall_noise = 0.0
        cell.climate["rainfall"] = rainfall_noise
        cell.climate["temperature"] = 20.0 + temperature_noise
        # Slow resource drain so depletion / recovery_rate observers see
        # variation. We do not change the dict shape; only the existing
        # keys established by ``physis.world._default_resources``.
        for resource_key in list(cell.resources.keys()):
            current = float(cell.resources[resource_key])
            drift = float(rng.uniform(-0.05, 0.10))
            updated = current + drift
            if updated < 0.0:
                updated = 0.0
            cell.resources[resource_key] = updated
    _ = tick  # tick is intentionally unused; rng drives the walk


def _save_probe_json(
    path: Path,
    seed: int,
    window_size: int,
    tick_start: int,
    tick_end_inclusive: int,
    telemetry: LandClimateTelemetry,
) -> None:
    payload: JsonObject = {
        "seed": seed,
        "window_size": window_size,
        "tick_range": [tick_start, tick_end_inclusive],
        "current": [
            _measurement_to_dict(measurement)
            for measurement in telemetry.iter_current()
        ],
        "cumulative": [
            _measurement_to_dict(measurement)
            for measurement in telemetry.iter_cumulative()
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def collect_seed(seed: int, tick_count: int = DEFAULT_PROBE_TICK_COUNT) -> Path:
    """Run a deterministic ``tick_count``-tick probe for ``seed`` and serialize results."""
    world = _initialize_world(seed)
    rng = np.random.default_rng(seed + 1)  # decoupled from world rng stream
    telemetry = LandClimateTelemetry(seed=seed, window_size=DEFAULT_WINDOW_SIZE)

    tick_start = 0
    tick_end_inclusive = tick_count - 1
    for tick in range(tick_start, tick_end_inclusive + 1):
        _evolve_climate(world, rng, tick)
        telemetry.observe(tick=tick, world=world)

    out_path = DATA_ROOT / f"seed-{seed}" / "probe.json"
    _save_probe_json(
        out_path,
        seed=seed,
        window_size=DEFAULT_WINDOW_SIZE,
        tick_start=tick_start,
        tick_end_inclusive=tick_end_inclusive,
        telemetry=telemetry,
    )
    return out_path


def _parse_seeds_arg(raw: str) -> tuple[int, ...]:
    """Parse a ``--seeds`` CLI value such as ``"7,13,42"`` into a tuple of ints."""
    parts = [chunk.strip() for chunk in raw.split(",") if chunk.strip()]
    if not parts:
        raise argparse.ArgumentTypeError(
            f"--seeds: empty list. Provide e.g. '7,13,42'. raw={raw!r}"
        )
    seeds: list[int] = []
    for part in parts:
        try:
            seeds.append(int(part))
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"--seeds: '{part}' is not an integer. raw={raw!r}"
            ) from exc
    return tuple(seeds)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 17 Phi-1 Land §7-1 Land-Climate probe collector "
            "(synthetic smoke / random walk — NOT ClimateEngine)."
        ),
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=DEFAULT_PROBE_TICK_COUNT,
        help=(
            "tick count (default: 30 = DEFAULT_WINDOW_SIZE). "
            "Use --ticks 60 or 90 for current/cumulative separation evidence. "
            "NOTE: this is raw window extension, NOT threshold freeze."
        ),
    )
    parser.add_argument(
        "--seeds",
        type=_parse_seeds_arg,
        default=DEFAULT_SEEDS,
        help=(
            "comma-separated seed list (default: 7,13,42). "
            "Deterministic three-seed replay matches spec §0.3 / §6.2."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    tick_count: int = int(args.ticks)
    seeds: tuple[int, ...] = tuple(args.seeds)

    print(
        "[SMOKE] phase17_phi1_land_climate_collect.py - "
        "synthetic random walk (NOT ClimateEngine)"
    )
    print(
        f"[SMOKE] tick_count={tick_count}, seeds={list(seeds)} "
        f"(raw window extension, NOT threshold freeze)"
    )

    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for seed in seeds:
        out_path = collect_seed(seed, tick_count=tick_count)
        written.append(out_path)
        print(f"seed-{seed}: wrote {out_path}")
    print(f"wrote {len(written)} probe files under {DATA_ROOT}")


if __name__ == "__main__":
    main()
