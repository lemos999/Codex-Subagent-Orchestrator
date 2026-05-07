"""Phase 17 Phi-1 Land rev.next §7-1 DC-1C Multi-config Collector — alt planet config axis.

Spec authority:
``Projects/personas/loom/PHASE-17-LAND-REV-NEXT-DC-1C-MULTICONFIG-NORMALIZED-PROBE-SPEC.md``
rev.0+ [봉인] 2026-05-07 (OQ 1C-1~1C-4 [확정] + spec-review 1차 [승인]).

WARNING — alt planet config axis collector (NovaPlanet alt instance, NOT default config):
This collector uses :class:`physis.climate_engine.ClimateEngine` driven by
an *alternative* :class:`physis.planet.NovaPlanet` instance with a single
parameter changed from default (sub-impl OQ 1C-5 decision: ``sea_level_temp_c=10.0``,
default 16.0). The rainfall channel mapping is *raw* (DC-1B 동형, no
normalization) — so this collector isolates the contribution of planet-config
variation on the rainfall_30d distribution.

Output JSON is paper §7-1 planet-variation evidence base (complementary to the
DC-1B real raw collector at ``scripts/phase17_phi1_land_climate_collect_real.py``,
the synthetic smoke baseline at ``scripts/phase17_phi1_land_climate_collect.py``,
and the DC-1C normalized collector at
``scripts/phase17_phi1_land_climate_collect_normalized.py``).

OQ 1C-5 [sub-impl 결정 / 2026-05-07]:
  alt planet config = NovaPlanet(sea_level_temp_c=10.0)  # default 16.0 → 한랭 기후
  alt name          = "nova_cool"

  근거:
    - sea_level_temp_c는 ClimateEngine `_compute_region_weather` Stage 2 (계절 기온)에서
      `base_temp = sea_level_temp_c + season_offset - altitude*lapse` 로 직접 사용되며,
      이는 Stage 5 (humidity + 강수) 의 `wind_base = abs(temp - sea_level_temp_c)*0.08`
      및 cum buffer (heatwave/coldsnap) 에 cascading 영향. 단일 파라미터 변동이
      rainfall 분포에 비교적 깔끔하게 추적 가능.
    - axial_tilt_deg 는 계절성에만 영향 (정성적, P50 영향 작음 가능),
      eccentricity 는 0.02→0.05 변화 폭이 작아 효과 미약,
      solar_constant 는 전역 영향이지만 단일 파라미터 의미가 sea_level_temp_c 만큼
      직관적이지 않음.
    - 한랭 기후 변동 (16°C → 10°C) 은 DC-1B sub-impl §Uncertainty #1 의 5배 차이
      (synthetic 5.40 → real 29.20) 의 config 한정 영향을 깔끔하게 분리하는 candidate.

direct mapping (DC-1B 동형, NO normalization):
  cell.climate["rainfall"]    = weather["precipitation_mm"]
  cell.climate["temperature"] = weather["temperature_c"]

CLI default: --ticks 90 (DC-1B 동형 invariant).

Strict invariants (spec §0.3 / §1.3 / §3.4):
  - LandCell 본문 변경 0건. ``physis/world.py`` 무수정.
  - climate dict 키 추가 0건 (rainfall + temperature 기존 키만 갱신).
  - LandClimateTelemetry observer 본문 변경 0건 (재사용만).
  - ClimateEngine 본문 변경 0건 (driver는 public ``tick()`` 호출만).
  - NovaPlanet 본문 변경 0건 — `@dataclass(frozen=True)` invariant 유지.
    alt config 는 NovaPlanet 의 다른 파라미터 값 인스턴스화만 (본문 0건).
  - extractor 본문 변경 0건 (probe.json schema 호환 강제 — runtime DATA_ROOT swap).
  - DC-1B real collector / `_probe_real/` 데이터 무영향 (분리 dir `_probe_multiconfig/`).
  - synthetic baseline (`collect.py` + `_probe/`) 변경 0건.
  - normalized collector / `_probe_normalized/` 무영향 (분리 dir).
  - mechanism 결합 수식 0건 (driver wiring + alt config instantiation only).

Output schema (one file per seed, identical to synthetic baseline schema):
  ``data/phase17_phi1_land_climate_probe_multiconfig/seed-{N}/probe.json``::

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
DATA_ROOT = BASE_DIR / "data" / "phase17_phi1_land_climate_probe_multiconfig"

# Ensure the loom package root is importable when this script is invoked
# directly (``py scripts/phase17_phi1_land_climate_collect_multiconfig.py``).
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

# Probe length in observation ticks. Spec §0.2 / §1.3 alignment with DC-1B
# OQ 1B-3 [확정]: 90 tick default for current vs cumulative separation evidence.
DEFAULT_MULTICONFIG_PROBE_TICK_COUNT: int = 90

# DC-1B §3.3 #12 검증 표 + spec body §1.2 "8x8 = 64 cells" reference:
# multiconfig collector grid is 8x8 (DC-1B 동형). The ``_assign_region()``
# helper splits this into three deterministic latitude bands
# (3/3/2 rows = 24/24/16 cells per region).
WORLD_WIDTH: int = 8
WORLD_HEIGHT: int = 8

# OQ 1C-5 [sub-impl 결정 / 2026-05-07] — alt planet config registry.
#
# Each entry maps an alt-config name to the override dict that will be passed
# to the NovaPlanet dataclass constructor. NovaPlanet remains @dataclass(frozen=True);
# we never mutate planet.py — we only instantiate it with different values.
#
# The default configuration ("nova_cool") changes a single parameter
# (sea_level_temp_c: 16.0 → 10.0) to isolate the contribution of planet-config
# variation on the rainfall_30d distribution (DC-1B sub-impl §Uncertainty #1
# config-한정 axis).
ALT_CONFIG_REGISTRY: dict[str, dict[str, Any]] = {
    "nova_cool": {"sea_level_temp_c": 10.0},
}
DEFAULT_ALT_CONFIG_NAME: str = "nova_cool"


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
    multiconfig collector to the real collector module.
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
    """Build a deterministic 8x8 World for the multiconfig collector.

    The world is initialized via ``physis.world._init_biomes`` so the LandCell
    biome / resources / elevation / path_cost defaults match the DC-1B real
    collector pathway. This keeps the telemetry observer's depletion / hazard
    derivations well-formed even though the climate driver uses an alt
    NovaPlanet config.
    """
    import numpy as np  # local import keeps top-level imports lean
    from physis.world import _init_biomes  # local import: avoid cycles

    rng = np.random.default_rng(seed)
    world = World(width=WORLD_WIDTH, height=WORLD_HEIGHT)
    _init_biomes(world, rng)
    return world


def _build_alt_planet(alt_name: str) -> NovaPlanet:
    """Construct an alt NovaPlanet instance from the registry.

    NovaPlanet is ``@dataclass(frozen=True)`` (physis/planet.py:13). This helper
    never mutates planet.py — it only instantiates NovaPlanet with the override
    parameters from :data:`ALT_CONFIG_REGISTRY`.
    """
    if alt_name not in ALT_CONFIG_REGISTRY:
        raise ValueError(
            f"--alt-config: unknown alt-config name '{alt_name}'. "
            f"Known: {sorted(ALT_CONFIG_REGISTRY.keys())}"
        )
    overrides = ALT_CONFIG_REGISTRY[alt_name]
    return NovaPlanet(**overrides)


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
    alt_planet: NovaPlanet,
) -> Path:
    """Run a deterministic ``tick_count``-tick alt-config ClimateEngine probe for ``seed``.

    Pseudocode (spec §2.4):

        engine = ClimateEngine(planet=alt_planet, seed=<seed>)  # alt config
        world = World(8, 8)
        observer = LandClimateTelemetry(window_size=30)
        for t in range(tick_count):
            day_of_year = t // 24
            hour = t % 24
            weather_by_region = engine.tick(day_of_year, hour)
            for cell in world.iter_cells():
                region_id = _assign_region(cell)
                weather = weather_by_region[region_id]
                cell.climate["rainfall"]    = weather["precipitation_mm"]   # raw, NOT normalized
                cell.climate["temperature"] = weather["temperature_c"]
            observer.observe(t, world)

    The only behavioral difference vs DC-1B real collector is the
    ``planet=alt_planet`` argument to ClimateEngine. Everything else (region
    assignment, world init, telemetry buckets, raw rainfall mapping, JSON
    schema) is bit-identical to DC-1B.
    """
    world = _initialize_world(seed)
    # Spec §2.3 [확정]: alt NovaPlanet config (OQ 1C-5 sub-impl decision)
    engine = ClimateEngine(planet=alt_planet, seed=seed)
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
            # DC-1B 동형 raw mapping (NO normalization — that is the
            # collect_normalized.py axis):
            cell.climate["rainfall"] = weather.get(
                "precipitation_mm", weather.get("rainfall", 0.0)
            )
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
            "Phase 17 Phi-1 Land §7-1 DC-1C Multi-config Collector "
            "(ClimateEngine driver + alt NovaPlanet config — OQ 1C-5 sub-impl decision)."
        ),
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=DEFAULT_MULTICONFIG_PROBE_TICK_COUNT,
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
    parser.add_argument(
        "--alt-config",
        type=str,
        default=DEFAULT_ALT_CONFIG_NAME,
        choices=sorted(ALT_CONFIG_REGISTRY.keys()),
        help=(
            "alt NovaPlanet config name (OQ 1C-5 sub-impl decision; default: "
            f"'{DEFAULT_ALT_CONFIG_NAME}'). Each name maps to a NovaPlanet "
            "kwargs override (single parameter per spec §2.1 invariant)."
        ),
    )
    return parser


# ---------------------------------------------------------------------------
# extractor re-run wrapper (extractor 본문 무수정 invariant — runtime DATA_ROOT swap)
# ---------------------------------------------------------------------------


def _run_extractor_against_multiconfig_dir() -> None:
    """Re-run the synthetic extractor against the multiconfig collector output dir.

    The extractor module hard-codes its DATA_ROOT to the synthetic baseline
    dir (``scripts/phase17_phi1_land_climate_extractor.py:36``). Spec
    §0.3 invariant + DC-1B 동형 pattern: extractor 본문 변경 금지. This
    wrapper imports the extractor module, monkey-patches its DATA_ROOT to
    point at ``data/phase17_phi1_land_climate_probe_multiconfig/`` for the
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


def _post_process_summary_provenance(seeds: tuple[int, ...], alt_name: str) -> None:
    """Replace the extractor's synthetic Provenance label with the multiconfig one.

    Spec §2.3 / §3.3 #9: each summary.md (3 seeds + aggregate) must carry a
    ``ClimateEngine multi-config axis`` label so paper §7-1 evidence consumers
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
    multiconfig_marker = (
        "> **Provenance**: ClimateEngine multi-config axis "
        f"(NovaPlanet alt instance: {alt_name}). "
        "paper §7-1 planet-variation evidence base."
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
            text = text.replace(synth_seed_marker, multiconfig_marker)
            replaced = True
        if synth_aggregate_marker in text:
            text = text.replace(synth_aggregate_marker, multiconfig_marker)
            replaced = True
        if not replaced:
            # Defensive: prepend the multiconfig marker after the H1 if no
            # synthetic marker was found. This keeps the validation #9 grep
            # contract (``ClimateEngine multi-config axis``) intact even if
            # the extractor ever changes its boilerplate.
            lines = text.split("\n")
            if lines and lines[0].startswith("# "):
                insertion = ["", multiconfig_marker, ""]
                lines = lines[:1] + insertion + lines[1:]
                text = "\n".join(lines)
        target.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    tick_count: int = int(args.ticks)
    seeds: tuple[int, ...] = tuple(args.seeds)
    alt_name: str = str(args.alt_config)
    alt_planet = _build_alt_planet(alt_name)

    print(
        "[MULTICONFIG] phase17_phi1_land_climate_collect_multiconfig.py - "
        f"NovaPlanet({alt_name})"
    )
    overrides = ALT_CONFIG_REGISTRY[alt_name]
    print(
        f"[MULTICONFIG] tick_count={tick_count}, seeds={list(seeds)}, "
        f"world={WORLD_WIDTH}x{WORLD_HEIGHT}, alt_overrides={overrides} "
        "(paper section 7-1 planet-variation evidence base)"
    )

    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for seed in seeds:
        out_path = collect_seed(seed, tick_count=tick_count, alt_planet=alt_planet)
        written.append(out_path)
        print(f"seed-{seed}: wrote {out_path}")
    print(f"wrote {len(written)} probe files under {DATA_ROOT}")

    # Spec section 3.3 #6 + #9: re-run extractor against the multiconfig dir,
    # then stamp provenance label on the emitted summary.md files.
    print("[MULTICONFIG] re-running extractor against multiconfig probe dir ...")
    _run_extractor_against_multiconfig_dir()
    _post_process_summary_provenance(seeds, alt_name)
    print(
        "[MULTICONFIG] extractor re-run complete + provenance stamped: "
        f"{DATA_ROOT}"
    )


if __name__ == "__main__":
    main()
