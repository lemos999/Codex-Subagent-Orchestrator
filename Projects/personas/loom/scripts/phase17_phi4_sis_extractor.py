"""Phase 17 Phi-4 DC-1 SIS distribution extractor.

This script is intentionally read-only with respect to the simulation core. It
uses only V3 raw telemetry files and writes faction-level windowed distribution
tables for Nation Charter design.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

import numpy as np


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_ROOT = BASE_DIR / "data" / "phase17_probe_phi3-case-c-diagnosis-v3"
OUT_ROOT = BASE_DIR / "data" / "phase17_phi4_sis"
WINDOW_SIZE = 720
TOTAL_TICKS = 20_000
SEEDS = (7, 13, 42)
QUANTILES = (25, 50, 67, 75, 90)
CONSISTENCY_QUANTILES = ("P50", "P67", "P75")
METRIC_KEYS = (
    "dom_share",
    "member_share",
    "conflict_pair_count",
    "cross_faction_lord_count",
)
EXPECTED_CFL_TOTAL = {7: 22, 13: 23, 42: 19}
EXPECTED_CONTACT_AT_END = 1


JsonObject = dict[str, Any]


class WindowMetrics(TypedDict):
    window_start: int
    window_end: int
    partial: bool
    dom_share: float
    member_share_per_faction: dict[str, float]
    conflict_pair_count: int
    cross_faction_lord_count: int


class SeedResult(TypedDict):
    seed: int
    windows: list[WindowMetrics]
    quantiles: dict[str, dict[str, float]]
    cfl_total: int
    last_contact_count: int


def load_case_c_events(path: Path) -> list[JsonObject]:
    """Load case_c_events.json as a JSON list. Every event needs type and tick."""
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, list):
        raise TypeError(f"{path}: expected JSON list")
    for index, event in enumerate(loaded):
        if not isinstance(event, dict):
            raise TypeError(f"{path}: event index {index} is not an object")
        if "type" not in event:
            raise KeyError(f"{path}: event index {index} missing type")
        if "tick" not in event:
            raise KeyError(f"{path}: event index {index} missing tick")
    return loaded


def load_metrics_jsonl(path: Path) -> list[JsonObject]:
    """Load metrics.jsonl where every non-empty line is one JSON event."""
    rows: list[JsonObject] = []
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise TypeError(f"{path}: line {index} is not an object")
            if "type" not in row:
                raise KeyError(f"{path}: line {index} missing type")
            if "tick" not in row:
                raise KeyError(f"{path}: line {index} missing tick")
            rows.append(row)
    return rows


def faction_sizes_at(metrics: list[JsonObject], t: int) -> dict[str, int]:
    """Return the closest prior population snapshot at or before tick t."""
    latest: JsonObject | None = None
    for row in metrics:
        if row["type"] == "population" and int(row["tick"]) <= t:
            latest = row
    if latest is None:
        return {}
    data = latest.get("data")
    if not isinstance(data, dict):
        raise TypeError(f"population snapshot at tick {latest['tick']} has invalid data")
    sizes: dict[str, int] = {}
    for fid, size in data.items():
        sizes[str(fid)] = int(size)
    return sizes


def contact_count_in_window(metrics: list[JsonObject], w_start: int, w_end: int) -> int:
    """Sum contact snapshot counts inside window [w_start, w_end)."""
    total = 0
    for row in metrics:
        if row["type"] == "contact" and w_start <= int(row["tick"]) < w_end:
            if "count" not in row:
                raise KeyError(f"contact snapshot at tick {row['tick']} missing count")
            total += int(row["count"])
    return total


def cfl_emerged_in_window(events: list[JsonObject], w_start: int, w_end: int) -> int:
    """Count cross-faction lord pair emerged events in window [w_start, w_end)."""
    return sum(
        1
        for event in events
        if event["type"] == "cross_faction_lord_pair_emerged"
        and w_start <= int(event["tick"]) < w_end
    )


def compute_window(
    events: list[JsonObject], metrics: list[JsonObject], w_start: int, w_end: int
) -> WindowMetrics:
    sizes_end = faction_sizes_at(metrics, w_end - 1)
    active_sizes = {
        fid: size for fid, size in sorted(sizes_end.items()) if size > 0
    }
    total = sum(active_sizes.values())
    if total == 0:
        dom_share = 0.0
        member_share_per_faction: dict[str, float] = {}
    else:
        dom_share = max(active_sizes.values()) / total
        member_share_per_faction = {
            fid: size / total for fid, size in active_sizes.items()
        }
    return {
        "window_start": w_start,
        "window_end": w_end,
        "partial": (w_end - w_start) < WINDOW_SIZE,
        "dom_share": float(dom_share),
        "member_share_per_faction": member_share_per_faction,
        "conflict_pair_count": contact_count_in_window(metrics, w_start, w_end),
        "cross_faction_lord_count": cfl_emerged_in_window(events, w_start, w_end),
    }


def compute_quantiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {f"P{q}": float("nan") for q in QUANTILES}
    return {f"P{q}": float(np.percentile(values, q)) for q in QUANTILES}


def quantiles_for_windows(windows: list[WindowMetrics]) -> dict[str, dict[str, float]]:
    member_values = [
        value for window in windows for value in window["member_share_per_faction"].values()
    ]
    return {
        "dom_share": compute_quantiles([window["dom_share"] for window in windows]),
        "member_share": compute_quantiles(member_values),
        "conflict_pair_count": compute_quantiles(
            [float(window["conflict_pair_count"]) for window in windows]
        ),
        "cross_faction_lord_count": compute_quantiles(
            [float(window["cross_faction_lord_count"]) for window in windows]
        ),
    }


def last_contact_count_at_end(metrics: list[JsonObject]) -> int:
    contacts = [
        row
        for row in metrics
        if row["type"] == "contact" and int(row["tick"]) <= TOTAL_TICKS
    ]
    assert contacts, "no contact snapshot at or before total tick"
    if "count" not in contacts[-1]:
        raise KeyError(f"last contact snapshot at tick {contacts[-1]['tick']} missing count")
    return int(contacts[-1]["count"])


def metric_values_for_seed(windows: list[WindowMetrics]) -> dict[str, list[float]]:
    return {
        "dom_share": [window["dom_share"] for window in windows],
        "member_share": [
            value for window in windows for value in window["member_share_per_faction"].values()
        ],
        "conflict_pair_count": [
            float(window["conflict_pair_count"]) for window in windows
        ],
        "cross_faction_lord_count": [
            float(window["cross_faction_lord_count"]) for window in windows
        ],
    }


def save_distribution_json(
    path: Path,
    seed: int,
    windows: list[WindowMetrics],
    quantiles_per_metric: dict[str, dict[str, float]],
    cfl_total: int,
    last_contact_count: int,
) -> None:
    payload = {
        "seed": seed,
        "total_ticks": TOTAL_TICKS,
        "window_size": WINDOW_SIZE,
        "windows": windows,
        "quantiles_per_metric": quantiles_per_metric,
        "v3_validation": {
            "cfl_total": cfl_total,
            "expected_cfl_total": EXPECTED_CFL_TOTAL[seed],
            "last_contact_count_at_20000": last_contact_count,
            "expected_last_contact": EXPECTED_CONTACT_AT_END,
            "passed": (
                cfl_total == EXPECTED_CFL_TOTAL[seed]
                and last_contact_count == EXPECTED_CONTACT_AT_END
            ),
        },
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def markdown_quantile_table(quantiles_per_metric: dict[str, dict[str, float]]) -> str:
    lines = [
        "| metric | P25 | P50 | P67 | P75 | P90 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for metric in METRIC_KEYS:
        q = quantiles_per_metric[metric]
        lines.append(
            f"| {metric} | {q['P25']:.6f} | {q['P50']:.6f} | "
            f"{q['P67']:.6f} | {q['P75']:.6f} | {q['P90']:.6f} |"
        )
    return "\n".join(lines)


def save_summary_md_utf8(
    path: Path,
    seed: int,
    windows: list[WindowMetrics],
    quantiles_per_metric: dict[str, dict[str, float]],
    cfl_total: int,
    last_contact_count: int,
) -> None:
    faction_ids = sorted(
        {
            fid
            for window in windows
            for fid in window["member_share_per_faction"]
        }
    )
    partial_count = sum(1 for window in windows if window["partial"])
    text = "\n".join(
        [
            f"# DC-1 SIS distribution - seed {seed}",
            "",
            f"- total_ticks: {TOTAL_TICKS}",
            f"- windows: {len(windows)}",
            f"- window_size: {WINDOW_SIZE}",
            f"- partial_windows: {partial_count}",
            f"- factions_observed: {len(faction_ids)}",
            "",
            "## 분위수 후보",
            "",
            markdown_quantile_table(quantiles_per_metric),
            "",
            "## V3 일치 검증",
            "",
            f"- cfl_total: {cfl_total}",
            f"- expected_cfl_total: {EXPECTED_CFL_TOTAL[seed]}",
            f"- last_contact_count_at_20000: {last_contact_count}",
            f"- expected_last_contact: {EXPECTED_CONTACT_AT_END}",
            f"- passed: {str(cfl_total == EXPECTED_CFL_TOTAL[seed] and last_contact_count == EXPECTED_CONTACT_AT_END).lower()}",
            "",
            "## 주의",
            "",
            "This extractor derives distribution candidates only. It does not freeze a threshold, does not change mechanism code, and does not read mojibake summaries.",
            "",
        ]
    )
    with path.open("w", encoding="utf-8") as handle:
        handle.write(text)


def process_seed(seed: int) -> SeedResult:
    seed_dir = DATA_ROOT / f"seed-{seed}"
    events = load_case_c_events(seed_dir / "case_c_events.json")
    metrics = load_metrics_jsonl(seed_dir / "metrics.jsonl")

    windows: list[WindowMetrics] = []
    for w_start in range(0, TOTAL_TICKS, WINDOW_SIZE):
        w_end = min(w_start + WINDOW_SIZE, TOTAL_TICKS)
        windows.append(compute_window(events, metrics, w_start, w_end))

    quantiles_per_metric = quantiles_for_windows(windows)
    cfl_total = sum(window["cross_faction_lord_count"] for window in windows)
    assert cfl_total == EXPECTED_CFL_TOTAL[seed], (
        f"seed {seed}: cfl_total={cfl_total}, expected={EXPECTED_CFL_TOTAL[seed]}"
    )
    last_contact_count = last_contact_count_at_end(metrics)
    assert last_contact_count == EXPECTED_CONTACT_AT_END, (
        f"seed {seed}: last contact count={last_contact_count}, expected={EXPECTED_CONTACT_AT_END}"
    )

    out_dir = OUT_ROOT / f"seed-{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_distribution_json(
        out_dir / "distribution.json",
        seed,
        windows,
        quantiles_per_metric,
        cfl_total,
        last_contact_count,
    )
    save_summary_md_utf8(
        out_dir / "summary.md",
        seed,
        windows,
        quantiles_per_metric,
        cfl_total,
        last_contact_count,
    )
    return {
        "seed": seed,
        "windows": windows,
        "quantiles": quantiles_per_metric,
        "cfl_total": cfl_total,
        "last_contact_count": last_contact_count,
    }


def aggregate_metric_values(per_seed: list[SeedResult]) -> dict[str, list[float]]:
    aggregate = {metric: [] for metric in METRIC_KEYS}
    for seed_result in per_seed:
        values = metric_values_for_seed(seed_result["windows"])
        for metric in METRIC_KEYS:
            aggregate[metric].extend(values[metric])
    return aggregate


def compute_consistency(
    per_seed: list[SeedResult],
) -> tuple[dict[str, dict[str, bool]], dict[str, dict[str, dict[str, Any]]]]:
    consistency: dict[str, dict[str, bool]] = {}
    details: dict[str, dict[str, dict[str, Any]]] = {}
    for metric in METRIC_KEYS:
        consistency[metric] = {}
        details[metric] = {}
        for q_name in CONSISTENCY_QUANTILES:
            values = {
                str(seed_result["seed"]): seed_result["quantiles"][metric][q_name]
                for seed_result in per_seed
            }
            mean_v = sum(values.values()) / len(values)
            if mean_v == 0:
                passed = all(value == 0 for value in values.values())
            else:
                passed = all(
                    abs(value - mean_v) / abs(mean_v) <= 0.10
                    for value in values.values()
                )
            consistency[metric][q_name] = passed
            details[metric][q_name] = {
                "values_by_seed": values,
                "mean": mean_v,
                "within_10pct": passed,
            }
    return consistency, details


def save_aggregate_json(
    path: Path,
    aggregate_quantiles: dict[str, dict[str, float]],
    consistency: dict[str, dict[str, bool]],
    consistency_details: dict[str, dict[str, dict[str, Any]]],
    validation: dict[str, dict[str, int]],
) -> None:
    payload = {
        "seeds_combined": list(SEEDS),
        "total_ticks": TOTAL_TICKS,
        "window_size": WINDOW_SIZE,
        "aggregate_quantiles": aggregate_quantiles,
        "consistency_within_10pct": consistency,
        "consistency_details": consistency_details,
        "v3_validation": validation,
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def save_aggregate_summary_utf8(
    path: Path,
    aggregate_quantiles: dict[str, dict[str, float]],
    consistency: dict[str, dict[str, bool]],
    consistency_details: dict[str, dict[str, dict[str, Any]]],
    validation: dict[str, dict[str, int]],
) -> None:
    lines = [
        "# DC-1 SIS aggregate distribution",
        "",
        f"- seeds: {', '.join(str(seed) for seed in SEEDS)}",
        f"- total_ticks: {TOTAL_TICKS}",
        f"- window_size: {WINDOW_SIZE}",
        "",
        "## 분위수 후보",
        "",
        markdown_quantile_table(aggregate_quantiles),
        "",
        "## Seed consistency within 10 percent",
        "",
        "| metric | quantile | within_10pct | mean | seed_7 | seed_13 | seed_42 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for metric in METRIC_KEYS:
        for q_name in CONSISTENCY_QUANTILES:
            row = consistency_details[metric][q_name]
            values = row["values_by_seed"]
            lines.append(
                f"| {metric} | {q_name} | {str(consistency[metric][q_name]).lower()} | "
                f"{row['mean']:.6f} | {values['7']:.6f} | {values['13']:.6f} | {values['42']:.6f} |"
            )
    lines.extend(
        [
            "",
            "## V3 일치 검증",
            "",
            "| seed | cfl_total | last_contact_count_at_20000 |",
            "|---:|---:|---:|",
        ]
    )
    for seed in SEEDS:
        seed_key = str(seed)
        lines.append(
            f"| {seed} | {validation[seed_key]['cfl_total']} | "
            f"{validation[seed_key]['last_contact_count_at_20000']} |"
        )
    lines.extend(
        [
            "",
            "## 주의",
            "",
            "This extractor only derives quantile candidates. It does not freeze a threshold and does not change mechanism code.",
            "",
        ]
    )
    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def aggregate_and_consistency(per_seed: list[SeedResult]) -> None:
    aggregate_values = aggregate_metric_values(per_seed)
    aggregate_quantiles = {
        metric: compute_quantiles(values) for metric, values in aggregate_values.items()
    }
    consistency, consistency_details = compute_consistency(per_seed)
    validation = {
        str(seed_result["seed"]): {
            "cfl_total": seed_result["cfl_total"],
            "expected_cfl_total": EXPECTED_CFL_TOTAL[seed_result["seed"]],
            "last_contact_count_at_20000": seed_result["last_contact_count"],
            "expected_last_contact": EXPECTED_CONTACT_AT_END,
        }
        for seed_result in per_seed
    }

    out_dir = OUT_ROOT / "aggregate"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_aggregate_json(
        out_dir / "distribution.json",
        aggregate_quantiles,
        consistency,
        consistency_details,
        validation,
    )
    save_aggregate_summary_utf8(
        out_dir / "summary.md",
        aggregate_quantiles,
        consistency,
        consistency_details,
        validation,
    )


def main() -> None:
    per_seed = [process_seed(seed) for seed in SEEDS]
    aggregate_and_consistency(per_seed)
    print(f"wrote SIS outputs to {OUT_ROOT}")
    for result in per_seed:
        print(
            "seed-{seed}: windows={windows}, cfl_total={cfl}, last_contact={contact}".format(
                seed=result["seed"],
                windows=len(result["windows"]),
                cfl=result["cfl_total"],
                contact=result["last_contact_count"],
            )
        )


if __name__ == "__main__":
    main()
