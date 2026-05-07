"""Phase 17 Phi-1 Land rev.next §7-1 Land-Climate distribution extractor.

Spec authority: ``PHASE-17-LAND-REV-NEXT-DC-1-LAND-CLIMATE-PROBE-SPEC.md``
rev.0 [확정] 2026-05-07.

This script consumes raw probe telemetry written by
``scripts/phase17_phi1_land_climate_collect.py`` (or any external collector
that obeys the wire format defined in this module) and emits two derived
products per spec §2.3 / §4.2:

  - ``DistributionTable`` per seed: 8 metric × 2 window × P25/P50/P67/P75/P90.
  - ``SeedConsistencyTable`` aggregate: P50/P67/P75 × 8 metric × 2 window
    boolean flags marking three-seed agreement within ±10 percent.

It is *intentionally* read-only with respect to the simulation core: this
script only reads JSON files under ``data/phase17_phi1_land_climate_probe/``
and writes derived JSON / Markdown summaries alongside them. mechanism /
acceptance / brain·SNN / core / Φ-2~Φ-5 modules are never touched.

Strict invariants (spec §1.3 / §5.2 / §6.2):
  - mechanism coupling: 0건 (raw distribution tabulation only).
  - magic threshold freeze: 0건 — quantile candidates are *derived*.
  - file open: ``encoding='utf-8'`` mandatory (mojibake 회피).
  - 3 seed (7/13/42) replay: deterministic input filenames.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, TypedDict

import numpy as np


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_ROOT = BASE_DIR / "data" / "phase17_phi1_land_climate_probe"

SEEDS: tuple[int, ...] = (7, 13, 42)
QUANTILE_PERCENTILES: tuple[int, ...] = (25, 50, 67, 75, 90)
CONSISTENCY_QUANTILES: tuple[str, ...] = ("P50", "P67", "P75")
CONSISTENCY_TOLERANCE: float = 0.10  # ±10 percent (spec §2.3 / §6.3)


MetricName = Literal[
    "soil_moisture",
    "fertility",
    "rainfall_30d",
    "temperature_30d",
    "drought_days",
    "depletion",
    "recovery_rate",
    "hazard_damage",
]
QuantileName = Literal["P25", "P50", "P67", "P75", "P90"]
WindowName = Literal["current", "cumulative"]


METRIC_KEYS: tuple[MetricName, ...] = (
    "soil_moisture",
    "fertility",
    "rainfall_30d",
    "temperature_30d",
    "drought_days",
    "depletion",
    "recovery_rate",
    "hazard_damage",
)
WINDOW_KEYS: tuple[WindowName, ...] = ("current", "cumulative")


JsonObject = dict[str, Any]

DistributionTable = dict[
    MetricName, dict[WindowName, dict[QuantileName, float]]
]
SeedConsistencyTable = dict[
    MetricName, dict[WindowName, dict[QuantileName, bool]]
]


class SeedDistribution(TypedDict):
    """Result of distribution analysis for a single seed."""

    seed: int
    counts: dict[WindowName, int]
    quantiles: DistributionTable


# ---------------------------------------------------------------------------
# Loader — reads the probe JSON written by the collector script
# ---------------------------------------------------------------------------


def load_probe_json(path: Path) -> JsonObject:
    """Load a probe JSON file (one seed) emitted by the collector script.

    Expected schema::

        {
          "seed": 7,
          "window_size": 30,
          "tick_range": [start, end_inclusive],
          "current": [{measurement…}, …],
          "cumulative": [{measurement…}, …]
        }

    Each measurement entry is the dict serialization of
    :class:`physis.land_climate_telemetry.LandClimateMeasurement`, namely::

        {"tick": int, "x": int, "y": int,
         "soil_moisture": float, "fertility": float,
         "rainfall_30d": float, "temperature_30d": float,
         "drought_days": int, "depletion": float,
         "recovery_rate": float, "hazard_damage": float}
    """
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise TypeError(f"{path}: expected JSON object")
    for required_key in ("seed", "window_size", "current", "cumulative"):
        if required_key not in loaded:
            raise KeyError(f"{path}: missing required key '{required_key}'")
    if not isinstance(loaded["current"], list):
        raise TypeError(f"{path}: 'current' must be a list")
    if not isinstance(loaded["cumulative"], list):
        raise TypeError(f"{path}: 'cumulative' must be a list")
    return loaded


# ---------------------------------------------------------------------------
# Quantile derivation
# ---------------------------------------------------------------------------


def compute_quantiles(values: list[float]) -> dict[QuantileName, float]:
    """Return ``{P25, P50, P67, P75, P90}`` for an unsorted list of floats.

    Empty input is treated as a hard upstream contract violation (raw probe
    must yield at least one observation per metric × window). The extractor
    refuses to forge a NaN sentinel because §1.0 caveat ("no false PASS")
    prefers a loud failure over a silent NaN propagating into the
    DistributionTable / SeedConsistencyTable JSON outputs.
    """
    if not values:
        raise ValueError(
            "compute_quantiles: empty input - cannot compute quantiles. "
            "This indicates the upstream probe.json has zero measurements "
            "for the requested metric x window. Strict-JSON contract "
            "(allow_nan=False) forbids NaN sentinel emission."
        )
    return {
        f"P{q}": float(np.percentile(values, q))  # type: ignore[misc]
        for q in QUANTILE_PERCENTILES
    }


def metric_values_from_window(
    measurements: list[JsonObject], metric: MetricName
) -> list[float]:
    """Extract every value of ``metric`` from a measurement list."""
    out: list[float] = []
    for entry in measurements:
        if metric not in entry:
            raise KeyError(f"measurement missing field '{metric}': {entry!r}")
        out.append(float(entry[metric]))
    return out


def derive_distribution_table(
    current: list[JsonObject], cumulative: list[JsonObject]
) -> DistributionTable:
    """Produce a 8 metric × 2 window × 5 quantile table for one seed."""
    table: DistributionTable = {}
    for metric in METRIC_KEYS:
        per_window: dict[WindowName, dict[QuantileName, float]] = {}
        per_window["current"] = compute_quantiles(
            metric_values_from_window(current, metric)
        )
        per_window["cumulative"] = compute_quantiles(
            metric_values_from_window(cumulative, metric)
        )
        table[metric] = per_window
    return table


# ---------------------------------------------------------------------------
# Per-seed processing + aggregation + consistency
# ---------------------------------------------------------------------------


def process_seed(seed: int) -> SeedDistribution:
    """Load one seed's probe JSON and produce the per-seed distribution."""
    path = DATA_ROOT / f"seed-{seed}" / "probe.json"
    payload = load_probe_json(path)
    current_list = list(payload["current"])
    cumulative_list = list(payload["cumulative"])
    table = derive_distribution_table(current_list, cumulative_list)

    out_dir = DATA_ROOT / f"seed-{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_seed_distribution_json(
        out_dir / "distribution.json",
        seed,
        len(current_list),
        len(cumulative_list),
        table,
    )
    save_seed_summary_md(
        out_dir / "summary.md",
        seed,
        len(current_list),
        len(cumulative_list),
        table,
    )
    return SeedDistribution(
        seed=seed,
        counts={
            "current": len(current_list),
            "cumulative": len(cumulative_list),
        },
        quantiles=table,
    )


def compute_consistency(
    per_seed: list[SeedDistribution],
) -> tuple[SeedConsistencyTable, JsonObject]:
    """Compute three-seed ±10 percent agreement on P50/P67/P75 per metric × window.

    Returns the boolean table (spec §2.3) plus a details payload with the
    actual seed values and means for traceability.
    """
    consistency: SeedConsistencyTable = {}
    details: JsonObject = {}
    for metric in METRIC_KEYS:
        consistency[metric] = {}
        details[metric] = {}
        for window in WINDOW_KEYS:
            consistency[metric][window] = {}
            details[metric][window] = {}
            for q_name in CONSISTENCY_QUANTILES:
                per_seed_values: dict[str, float] = {}
                for seed_result in per_seed:
                    per_seed_values[str(seed_result["seed"])] = float(
                        seed_result["quantiles"][metric][window][
                            q_name  # type: ignore[index]
                        ]
                    )
                values = list(per_seed_values.values())
                if any(np.isnan(v) or np.isinf(v) for v in values):
                    # `compute_quantiles` raises on empty input, so reaching
                    # this branch means a NaN/Inf leaked through — strict
                    # JSON output forbids serialization. Fail loudly.
                    raise ValueError(
                        "compute_consistency: NaN/Inf detected in per-seed "
                        f"quantiles for metric={metric}, window={window}, "
                        f"quantile={q_name}. values={per_seed_values!r}. "
                        "Strict-JSON contract (allow_nan=False) requires "
                        "finite values only."
                    )
                mean_v = sum(values) / len(values)
                if mean_v == 0.0:
                    passed = all(v == 0.0 for v in values)
                else:
                    passed = all(
                        abs(v - mean_v) / abs(mean_v) <= CONSISTENCY_TOLERANCE
                        for v in values
                    )
                consistency[metric][window][
                    q_name  # type: ignore[index]
                ] = passed
                details[metric][window][q_name] = {
                    "values_by_seed": per_seed_values,
                    "mean": mean_v,
                    "within_tolerance": passed,
                }
    return consistency, details


def aggregate_distribution(
    per_seed: list[SeedDistribution],
) -> DistributionTable:
    """Produce a flattened-three-seed aggregate distribution table.

    For each metric × window we re-compute quantiles over the union of all
    raw measurements seen across the three seeds. This requires re-reading
    the probe JSONs because per-seed quantiles are not arithmetic-additive.
    """
    flattened: dict[MetricName, dict[WindowName, list[float]]] = {
        metric: {"current": [], "cumulative": []} for metric in METRIC_KEYS
    }
    for seed_result in per_seed:
        seed = seed_result["seed"]
        path = DATA_ROOT / f"seed-{seed}" / "probe.json"
        payload = load_probe_json(path)
        for window in WINDOW_KEYS:
            entries = list(payload[window])
            for metric in METRIC_KEYS:
                flattened[metric][window].extend(
                    metric_values_from_window(entries, metric)
                )

    table: DistributionTable = {}
    for metric in METRIC_KEYS:
        per_window: dict[WindowName, dict[QuantileName, float]] = {}
        for window in WINDOW_KEYS:
            per_window[window] = compute_quantiles(flattened[metric][window])
        table[metric] = per_window
    return table


# ---------------------------------------------------------------------------
# Output serialization
# ---------------------------------------------------------------------------


def save_seed_distribution_json(
    path: Path,
    seed: int,
    current_count: int,
    cumulative_count: int,
    table: DistributionTable,
) -> None:
    payload: JsonObject = {
        "seed": seed,
        "counts": {
            "current": current_count,
            "cumulative": cumulative_count,
        },
        "quantiles": table,
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def markdown_quantile_table(table: DistributionTable) -> str:
    lines = [
        "| metric | window | P25 | P50 | P67 | P75 | P90 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for metric in METRIC_KEYS:
        for window in WINDOW_KEYS:
            row = table[metric][window]
            lines.append(
                f"| {metric} | {window} | "
                f"{row['P25']:.6f} | {row['P50']:.6f} | "
                f"{row['P67']:.6f} | {row['P75']:.6f} | {row['P90']:.6f} |"
            )
    return "\n".join(lines)


def save_seed_summary_md(
    path: Path,
    seed: int,
    current_count: int,
    cumulative_count: int,
    table: DistributionTable,
) -> None:
    text = "\n".join(
        [
            f"# DC-1 Land-Climate distribution - seed {seed}",
            "",
            (
                "> **Provenance**: synthetic smoke collector (random walk). "
                "NOT actual `ClimateEngine` output. Suitable as smoke "
                "evidence only. §7-2 evidence requires real-collector "
                "reproduction."
            ),
            "",
            f"- current_window_measurements: {current_count}",
            f"- cumulative_measurements: {cumulative_count}",
            "",
            "## 분위수 후보 (8 metric × 2 window × 5 quantile)",
            "",
            markdown_quantile_table(table),
            "",
            "## 주의",
            "",
            (
                "This extractor derives quantile candidates only. It does "
                "not freeze any analytic threshold and does not change "
                "mechanism code. The current vs cumulative split mirrors "
                "paper §8 separation and the spec §2.2 telemetry buckets."
            ),
            "",
        ]
    )
    with path.open("w", encoding="utf-8") as handle:
        handle.write(text)


def save_aggregate_json(
    path: Path,
    aggregate: DistributionTable,
    consistency: SeedConsistencyTable,
    consistency_details: JsonObject,
    counts_per_seed: JsonObject,
) -> None:
    payload: JsonObject = {
        "seeds_combined": list(SEEDS),
        "consistency_tolerance": CONSISTENCY_TOLERANCE,
        "counts_per_seed": counts_per_seed,
        "aggregate_quantiles": aggregate,
        "consistency_within_tolerance": consistency,
        "consistency_details": consistency_details,
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def save_aggregate_summary_md(
    path: Path,
    aggregate: DistributionTable,
    consistency: SeedConsistencyTable,
    consistency_details: JsonObject,
) -> None:
    lines = [
        "# DC-1 Land-Climate aggregate distribution",
        "",
        (
            "> **Provenance**: synthetic smoke collector (random walk). "
            "NOT actual `ClimateEngine` output. Suitable as smoke evidence "
            "only. §7-2 evidence requires real-collector reproduction."
        ),
        "",
        f"- seeds: {', '.join(str(seed) for seed in SEEDS)}",
        f"- tolerance: ±{int(CONSISTENCY_TOLERANCE * 100)} percent",
        "",
        "## 분위수 후보 (3-seed flattened, 8 metric × 2 window × 5 quantile)",
        "",
        markdown_quantile_table(aggregate),
        "",
        "## Seed consistency (3-seed P50/P67/P75 ±tolerance boolean)",
        "",
        "| metric | window | quantile | within_tolerance | mean | seed_7 | seed_13 | seed_42 |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for metric in METRIC_KEYS:
        for window in WINDOW_KEYS:
            for q_name in CONSISTENCY_QUANTILES:
                row = consistency_details[metric][window][q_name]
                values = row["values_by_seed"]
                mean_v = row["mean"]
                lines.append(
                    f"| {metric} | {window} | {q_name} | "
                    f"{str(consistency[metric][window][q_name]).lower()} | "  # type: ignore[index]
                    f"{mean_v:.6f} | {values['7']:.6f} | "
                    f"{values['13']:.6f} | {values['42']:.6f} |"
                )
    lines.extend(
        [
            "",
            "## 주의",
            "",
            (
                "This extractor only derives quantile candidates. It does "
                "not freeze any analytic threshold and does not change "
                "mechanism code. Threshold freeze is reserved for §7-2 "
                "after this raw analysis is complete."
            ),
            "",
        ]
    )
    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    per_seed: list[SeedDistribution] = []
    for seed in SEEDS:
        per_seed.append(process_seed(seed))

    aggregate = aggregate_distribution(per_seed)
    consistency, details = compute_consistency(per_seed)
    counts_per_seed: JsonObject = {
        str(seed_result["seed"]): seed_result["counts"]
        for seed_result in per_seed
    }

    out_dir = DATA_ROOT / "aggregate"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_aggregate_json(
        out_dir / "distribution.json",
        aggregate,
        consistency,
        details,
        counts_per_seed,
    )
    save_aggregate_summary_md(
        out_dir / "summary.md",
        aggregate,
        consistency,
        details,
    )

    print(f"wrote land-climate distribution outputs to {DATA_ROOT}")
    for seed_result in per_seed:
        seed = seed_result["seed"]
        cur = seed_result["counts"]["current"]
        cum = seed_result["counts"]["cumulative"]
        print(
            f"seed-{seed}: current_measurements={cur}, "
            f"cumulative_measurements={cum}"
        )


if __name__ == "__main__":
    main()
