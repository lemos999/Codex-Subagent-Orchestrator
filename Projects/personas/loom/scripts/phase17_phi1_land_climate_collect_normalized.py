"""Phase 17 Phi-1 Land rev.next §7-1 DC-1C Normalized Collector — unit-normalized axis.

Spec authority:
``Projects/personas/loom/PHASE-17-LAND-REV-NEXT-DC-1C-MULTICONFIG-NORMALIZED-PROBE-SPEC.md``
rev.0+ [봉인] 2026-05-07 (OQ 1C-1~1C-4 [확정] + spec-review 1차 [승인]).

WARNING — normalized axis collector (precipitation_mm / 30.0 unit normalization, NOT raw):
This collector uses :class:`physis.climate_engine.ClimateEngine` with the
default :class:`physis.planet.NovaPlanet` config (DC-1B와 동일 baseline) and
applies a unit normalization to the rainfall channel before observer sampling.
The normalization divisor is :data:`RAINFALL_NORMALIZATION_DIVISOR` = 30.0
(spec §2.2 [확정], aligned with
:data:`physis.land_climate_telemetry.DEFAULT_WINDOW_SIZE` = 30 tick).

Output JSON is paper §7-1 unit-normalized evidence base (complementary to the
DC-1B real raw collector at ``scripts/phase17_phi1_land_climate_collect_real.py``
and the synthetic smoke baseline at
``scripts/phase17_phi1_land_climate_collect.py``).

direct mapping (spec §2.2 [확정]):
  cell.climate["rainfall"]    = weather["precipitation_mm"] / 30.0
  cell.climate["temperature"] = weather["temperature_c"]

CLI default: --ticks 90 (current/cumulative separation; DC-1B 동형 invariant).

Strict invariants (spec §0.3 / §1.3 / §3.4):
  - LandCell 본문 변경 0건. ``physis/world.py`` 무수정.
  - climate dict 키 추가 0건 (rainfall + temperature 기존 키만 갱신).
  - LandClimateTelemetry observer 본문 변경 0건 (재사용만).
  - ClimateEngine 본문 변경 0건 (driver는 public ``tick()`` 호출만).
  - NovaPlanet 본문 변경 0건 (default config 인스턴스만 사용).
  - extractor 본문 변경 0건 (probe.json schema 호환 강제 — runtime DATA_ROOT swap).
  - DC-1B real collector / `_probe_real/` 데이터 무영향 (분리 dir `_probe_normalized/`).
  - synthetic baseline (`collect.py` + `_probe/`) 변경 0건.
  - mechanism 결합 수식 0건 (driver wiring + normalize 식 only).

Output schema (one file per seed, identical to synthetic baseline schema):
  ``data/phase17_phi1_land_climate_probe_normalized/seed-{N}/probe.json``::

    {
      "seed": int,
      "window_size": int,
      "tick_range": [int, int],
      "current": [<measurement>, …],
      "cumulative": [<measurement>, …]
    }

  Each measurement is the dict serialization of
  :class:`physis.land_climate_telemetry.LandClimateMeasurement`.

OQ-1B-2 (region tag): LandCell does not carry a ``region_id`` field
(``physis/world.py:23`` dataclass slots=True invariant). The collector
assigns regions deterministically by ``cell.y`` on the 8x8 grid using a
3-band split (y<3 → claude / 3≤y<6 → codex / y≥6 → gemini). This helper
lives inside the collector — LandCell is never modified.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_ROOT = BASE_DIR / "data" / "phase17_phi1_land_climate_probe_normalized"

# Ensure the loom package root is importable when this script is invoked
# directly (``py scripts/phase17_phi1_land_climate_collect_normalized.py``).
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from physis.climate_engine import ClimateEngine  # noqa: E402  (sys.path setup above)
from physis.land_climate_telemetry import (  # noqa: E402
    DEFAULT_WINDOW_SIZE,
    LandClimateTelemetry,
)
from physis.planet import NovaPlanet  # noqa: E402
from physis.world import LandCell, World  # noqa: E402

# Spec §0.3 / §6.2 / §6.3 (DC-1 §7-1) + DC-1B §1.3 [필수]: deterministic
# three-seed replay (default).
DEFAULT_SEEDS: tuple[int, ...] = (7, 13, 42)

# Probe length in observation ticks. Spec §2.2 [확정] alignment with DC-1B
# OQ 1B-3 [확정]: 90 tick default for current vs cumulative separation evidence.
DEFAULT_NORMALIZED_PROBE_TICK_COUNT: int = 90

# DC-1B §3.3 #12 검증 표 + spec body §1.2 "8x8 = 64 cells" reference:
# normalized collector grid is 8x8 (DC-1B 동형). The ``_assign_region()``
# helper splits this into three deterministic latitude bands
# (3/3/2 rows = 24/24/16 cells per region).
WORLD_WIDTH: int = 8
WORLD_HEIGHT: int = 8

# Spec §2.2 [확정] — RAINFALL_NORMALIZATION_DIVISOR is a *unit normalization
# divisor* (NOT a quantile threshold). It aligns with
# physis.land_climate_telemetry.DEFAULT_WINDOW_SIZE = 30 tick — i.e. dividing
# precipitation_mm by 30.0 yields a "per-window-tick rate" that maps the raw
# precipitation_mm channel onto the same numerical magnitude as the synthetic
# random[0,1] baseline (DC-1B sub-impl §Uncertainty #1 quantification).
#
# spec §1.0 caveat ("magic threshold freeze 금지") applies to *quantile
# thresholds* (P25/P50/P67/P75/P90). This unit normalization divisor is a
# §0.2 freeze-확정 영역 entry — sub-impl 자가 조정 금지.
RAINFALL_NORMALIZATION_DIVISOR: float = 30.0


JsonObject = dict[str, Any]


def _assign_region(cell: LandCell) -> str:
    """Deterministic 8x8-grid region tag (DC-1B OQ-1B-2 sub-impl decision; reused).

    LandCell does not carry a ``region_id`` field (``physis/world.py:23``
    dataclass slots=True invariant). DC-1B spec rev.1 §2.4 explicitly forbids
    adding one. This helper performs the assignment inside the collector
    using a 3-band split on ``cell.y``:

      - ``y in [0, 1, 2]``  → ``"claude"`` (3 rows × 8 cols = 24 cells)
      - ``y in [3, 4, 5]``  → ``"codex"``  (3 rows × 8 cols = 24 cells)
      - ``y in [6, 7]``     → ``"gemini"`` (2 rows × 8 cols = 16 cells)

    The assignment is deterministic (function of cell.y only), seed-
    independent, and contains no mechanism coupling. ClimateEngine returns
    a 3-region weather dict per tick; this helper picks the matching key.
    """
    if cell.y < 3:
        return "claude"
    if cell.y < 6:
        return "codex"
    return "gemini"


def _measurement_to_dict(measurement: Any) -> JsonObject:
    """Serialize a LandClimateMeasurement dataclass to a JSON-safe dict.

    Identical serializer to DC-1B real collector (spec §0.3 invariant 11:
    DC-1B real collector body 무수정), duplicated here to avoid coupling the
    normalized collector to the real collector module.
    """
    raw = asdict(measurement)
    out: JsonObject = {}
    for key, value in raw.items():
        if isinstance(value, (bool, int, float, str)):
            out[key] = value
        else:
            out[key] = float(value)
    return out


def _initialize_world(seed: int) -> World:
    """Build a deterministic 8x8 World for the normalized collector.

    The world is initialized via ``physis.world._init_biomes`` so the LandCell
    biome / resources / elevation / path_cost defaults match the DC-1B real
    collector pathway. This keeps the telemetry observer's depletion / hazard
    derivations well-formed even though the rainfall channel is now
    unit-normalized.
    """
    import numpy as np  # local import keeps top-level imports lean
    from physis.world import _init_biomes  # local import: avoid cycles

    rng = np.random.default_rng(seed)
    world = World(width=WORLD_WIDTH, height=WORLD_HEIGHT)
    _init_biomes(world, rng)
    return world


def _save_probe_json(
    path: Path,
    seed: int,
    window_size: int,
    tick_start: int,
    tick_end_inclusive: int,
    telemetry: LandClimateTelemetry,
) -> None:
    """Serialize the probe payload using the synthetic-compatible schema.

    Schema is identical to ``scripts/phase17_phi1_land_climate_collect.py`` /
    ``scripts/phase17_phi1_land_climate_collect_real.py`` (spec §1.3 [필수]:
    probe.json 인터페이스 호환 — 기존 extractor 재사용 via runtime
    DATA_ROOT swap).
    """
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
        # Spec §1.3 [필수]: NaN/Infinity strict (DC-1 §7-1 hotfix policy).
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def collect_seed(
    seed: int,
    tick_count: int,
) -> Path:
    """Run a deterministic ``tick_count``-tick normalized ClimateEngine probe for ``seed``.

    Pseudocode (spec §2.4):

        engine = ClimateEngine(planet=NovaPlanet(), seed=<seed>)
        world = World(8, 8)
        observer = LandClimateTelemetry(window_size=30)
        for t in range(tick_count):
            day_of_year = t // 24
            hour = t % 24
            weather_by_region = engine.tick(day_of_year, hour)
            for cell in world.iter_cells():
                region_id = _assign_region(cell)
                weather = weather_by_region[region_id]
                cell.climate["rainfall"]    = weather["precipitation_mm"] / 30.0
                cell.climate["temperature"] = weather["temperature_c"]
            observer.observe(t, world)

    The only behavioral difference vs DC-1B real collector is the ``/ 30.0``
    division on the rainfall channel before observer sampling. Everything
    else (planet config, region assignment, world init, telemetry buckets,
    JSON schema) is bit-identical.
    """
    world = _initialize_world(seed)
    # Spec §2.3 [확정]: default NovaPlanet (DC-1B와 동일 baseline)
    engine = ClimateEngine(planet=NovaPlanet(), seed=seed)
    telemetry = LandClimateTelemetry(seed=seed, window_size=DEFAULT_WINDOW_SIZE)

    tick_start = 0
    tick_end_inclusive = tick_count - 1
    for tick in range(tick_start, tick_end_inclusive + 1):
        day_of_year = tick // 24
        hour = tick % 24
        # ClimateEngine public interface: returns 3-region weather dict
        # (physis/climate_engine.py line 52-69).
        weather_by_region = engine.tick(day_of_year, hour)

        for cell in world.iter_cells():
            region_id = _assign_region(cell)
            weather = weather_by_region[region_id]
            # Spec §2.2 [확정] direct mapping with normalization:
            # cell.climate["rainfall"] = weather["precipitation_mm"] / 30.0
            # ClimateEngine emits both keys at line 162-165 unconditionally,
            # so the fallback is purely defensive (DC-1B 동형).
            raw_precipitation = weather.get(
                "precipitation_mm", weather.get("rainfall", 0.0)
            )
            cell.climate["rainfall"] = (
                raw_precipitation / RAINFALL_NORMALIZATION_DIVISOR
            )
            # temperature is NOT normalized — temperature_c is SI standard
            # (spec §2.2 근거: "temperature는 unit 변환 없음").
            cell.climate["temperature"] = weather.get(
                "temperature_c", weather.get("temperature", 20.0)
            )

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
            "Phase 17 Phi-1 Land §7-1 DC-1C Normalized Collector "
            "(ClimateEngine driver + precipitation_mm / 30.0 unit normalization)."
        ),
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=DEFAULT_NORMALIZED_PROBE_TICK_COUNT,
        help=(
            "tick count (default: 90 = DC-1B 동형 current/cumulative separation "
            "evidence default). NOT a frozen threshold (spec §0.2 caveat)."
        ),
    )
    parser.add_argument(
        "--seeds",
        type=_parse_seeds_arg,
        default=DEFAULT_SEEDS,
        help=(
            "comma-separated seed list (default: 7,13,42). Deterministic "
            "three-seed replay matches DC-1 §7-1 spec rev.0 §0.3 / §6.2."
        ),
    )
    return parser


# ---------------------------------------------------------------------------
# extractor re-run wrapper (extractor 본문 무수정 invariant — runtime DATA_ROOT swap)
# ---------------------------------------------------------------------------


def _run_extractor_against_normalized_dir() -> None:
    """Re-run the synthetic extractor against the normalized collector output dir.

    The extractor module hard-codes its DATA_ROOT to the synthetic baseline
    dir (``scripts/phase17_phi1_land_climate_extractor.py:36``). Spec
    §0.3 invariant + DC-1B 동형 pattern: extractor 본문 변경 금지. This
    wrapper imports the extractor module, monkey-patches its DATA_ROOT to
    point at ``data/phase17_phi1_land_climate_probe_normalized/`` for the
    duration of one main() call, then restores the original. The extractor
    module bytes on disk are untouched.

    Provenance markers on the emitted summary.md files are post-processed
    by ``_post_process_summary_provenance`` immediately after extractor
    completion — see spec §2.3 / §3.3 #9.
    """
    from scripts import phase17_phi1_land_climate_extractor as extractor

    original_data_root = extractor.DATA_ROOT
    try:
        extractor.DATA_ROOT = DATA_ROOT
        extractor.main()
    finally:
        extractor.DATA_ROOT = original_data_root


def _post_process_summary_provenance(seeds: tuple[int, ...]) -> None:
    """Replace the extractor's synthetic Provenance label with the normalized one.

    Spec §2.3 / §3.3 #9: each summary.md (3 seeds + aggregate) must carry a
    ``ClimateEngine normalized axis`` label so paper §7-1 evidence consumers
    can disambiguate the four evidence axes (synthetic / real / normalized /
    multiconfig). The extractor itself is forbidden from being modified
    (DC-1B invariant 9 + DC-1C invariant 11), so this collector edits the
    emitted summary.md files in place after the extractor returns. The edit
    is text-only and preserves the rest of the summary structure.
    """
    synth_seed_marker = (
        "> **Provenance**: synthetic smoke collector (random walk). "
        "NOT actual `ClimateEngine` output. Suitable as smoke "
        "evidence only. §7-2 evidence requires real-collector "
        "reproduction."
    )
    synth_aggregate_marker = (
        "> **Provenance**: synthetic smoke collector (random walk). "
        "NOT actual `ClimateEngine` output. Suitable as smoke evidence "
        "only. §7-2 evidence requires real-collector reproduction."
    )
    normalized_marker = (
        "> **Provenance**: ClimateEngine normalized axis "
        f"(precipitation_mm / {RAINFALL_NORMALIZATION_DIVISOR}). "
        "NOT raw or synthetic. paper §7-1 unit-normalized evidence base."
    )

    targets: list[Path] = []
    for seed in seeds:
        targets.append(DATA_ROOT / f"seed-{seed}" / "summary.md")
    targets.append(DATA_ROOT / "aggregate" / "summary.md")

    for target in targets:
        if not target.exists():
            continue
        text = target.read_text(encoding="utf-8")
        replaced = False
        if synth_seed_marker in text:
            text = text.replace(synth_seed_marker, normalized_marker)
            replaced = True
        if synth_aggregate_marker in text:
            text = text.replace(synth_aggregate_marker, normalized_marker)
            replaced = True
        if not replaced:
            # Defensive: prepend the normalized marker after the H1 if no
            # synthetic marker was found. This keeps the validation #9 grep
            # contract (``ClimateEngine normalized axis``) intact even if the
            # extractor ever changes its boilerplate.
            lines = text.split("\n")
            if lines and lines[0].startswith("# "):
                insertion = ["", normalized_marker, ""]
                lines = lines[:1] + insertion + lines[1:]
                text = "\n".join(lines)
        target.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    tick_count: int = int(args.ticks)
    seeds: tuple[int, ...] = tuple(args.seeds)

    print(
        "[NORMALIZED] phase17_phi1_land_climate_collect_normalized.py - "
        f"precipitation_mm / {RAINFALL_NORMALIZATION_DIVISOR}"
    )
    print(
        f"[NORMALIZED] tick_count={tick_count}, seeds={list(seeds)}, "
        f"world={WORLD_WIDTH}x{WORLD_HEIGHT} "
        "(paper section 7-1 unit-normalized evidence base)"
    )

    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for seed in seeds:
        out_path = collect_seed(seed, tick_count=tick_count)
        written.append(out_path)
        print(f"seed-{seed}: wrote {out_path}")
    print(f"wrote {len(written)} probe files under {DATA_ROOT}")

    # Spec section 3.3 #6 + #9: re-run extractor against the normalized dir,
    # then stamp provenance label on the emitted summary.md files.
    print("[NORMALIZED] re-running extractor against normalized probe dir ...")
    _run_extractor_against_normalized_dir()
    _post_process_summary_provenance(seeds)
    print(
        "[NORMALIZED] extractor re-run complete + provenance stamped: "
        f"{DATA_ROOT}"
    )


if __name__ == "__main__":
    main()
