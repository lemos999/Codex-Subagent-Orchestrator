"""Phase 17 Phi-4 DC-2 CPCM overlap extractor.

Read V3 raw events, rerun the deterministic engine, and write faction-level
charter overlap distribution candidates.
"""

from __future__ import annotations

import json
import importlib
import math
import sys
from itertools import combinations
from pathlib import Path
from typing import Any, Protocol, TypedDict, cast

import numpy as np


LOOM_ROOT = Path(__file__).resolve().parents[1]
if str(LOOM_ROOT) not in sys.path:
    sys.path.insert(0, str(LOOM_ROOT))

DATA_ROOT = LOOM_ROOT / "data" / "phase17_probe_phi3-case-c-diagnosis-v3"
OUT_ROOT = LOOM_ROOT / "data" / "phase17_phi4_cpcm"
SEEDS = (7, 13, 42)
TOTAL_TICKS = 20_000
SNAPSHOT_INTERVAL = 500
EXPECTED_SNAPSHOT_COUNT = 40
QUANTILES = (25, 50, 67, 75, 90)
CONSISTENCY_QUANTILES = ("P50", "P67", "P75")

JsonObject = dict[str, Any]


class PairMetric(TypedDict):
    a: str
    b: str
    jaccard: float


class SnapshotMetrics(TypedDict):
    tick: int
    active_count: int
    active_fids: list[str]
    pair_count: int
    pairs: list[PairMetric]
    mean_jaccard: float
    max_jaccard: float
    min_jaccard: float


class CapturedSnapshot(TypedDict):
    tick: int
    active_fids: list[str]
    charters: dict[str, tuple[str, ...]]


class AnchorValidation(TypedDict):
    snapshot_count_match: bool
    fid_set_match_per_snapshot: bool
    active_count_self_consistency: bool
    passed: bool


class SeedResult(TypedDict):
    seed: int
    snapshots: list[SnapshotMetrics]
    quantiles: dict[str, float]
    all_jaccards: list[float]
    anchor_validation: AnchorValidation


class TickTime(Protocol):
    tick: int


class EngineLike(Protocol):
    factions: dict[str, Any]
    _faction_members_cache: dict[str, Any]
    time: TickTime

    def tick(self) -> Any: ...

    def faction_charter_primitives(self, faction_id: str) -> tuple[str, ...]: ...


def make_engine(seed: int) -> EngineLike:
    module = importlib.import_module("core.multi_tick_engine")
    engine_cls = module.MultiTickEngine
    return cast(EngineLike, engine_cls(seed=seed))


def load_v3_active_snapshots(events_path: Path) -> list[JsonObject]:
    with events_path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, list):
        raise TypeError(f"{events_path}: expected JSON list")
    snapshots: list[JsonObject] = []
    for index, event in enumerate(loaded):
        if not isinstance(event, dict):
            raise TypeError(f"{events_path}: event index {index} is not an object")
        if event.get("type") == "active_factions_snapshot":
            if "tick" not in event:
                raise KeyError(f"{events_path}: snapshot index {index} missing tick")
            snapshots.append(cast(JsonObject, event))
    snapshots.sort(key=lambda event: int(cast(int | float | str, event["tick"])))
    return snapshots


def jaccard(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    set_a = set(a)
    set_b = set(b)
    union = set_a | set_b
    if not union:
        return float("nan")
    return len(set_a & set_b) / len(union)


def active_fids_from_cache(engine: EngineLike) -> list[str]:
    return sorted(
        fid
        for fid in engine.factions
        if len(engine._faction_members_cache.get(fid, ())) > 0
    )


def run_engine_and_capture_charters(seed: int) -> list[CapturedSnapshot]:
    engine = make_engine(seed)
    captured: list[CapturedSnapshot] = []
    while engine.time.tick < TOTAL_TICKS:
        engine.tick()
        if engine.time.tick > 0 and engine.time.tick % SNAPSHOT_INTERVAL == 0:
            active_fids = active_fids_from_cache(engine)
            captured.append(
                {
                    "tick": engine.time.tick,
                    "active_fids": active_fids,
                    "charters": {
                        fid: engine.faction_charter_primitives(fid)
                        for fid in active_fids
                    },
                }
            )
    return captured


def finite_mean(values: list[float]) -> float:
    finite_values = [value for value in values if not math.isnan(value)]
    if not finite_values:
        return float("nan")
    return float(sum(finite_values) / len(finite_values))


def finite_min(values: list[float]) -> float:
    finite_values = [value for value in values if not math.isnan(value)]
    if not finite_values:
        return float("nan")
    return float(min(finite_values))


def finite_max(values: list[float]) -> float:
    finite_values = [value for value in values if not math.isnan(value)]
    if not finite_values:
        return float("nan")
    return float(max(finite_values))


def compute_snapshot_metrics(captured: CapturedSnapshot) -> SnapshotMetrics:
    active_fids = captured["active_fids"]
    pairs: list[PairMetric] = []
    for fid_a, fid_b in combinations(active_fids, 2):
        pairs.append(
            {
                "a": fid_a,
                "b": fid_b,
                "jaccard": jaccard(
                    captured["charters"][fid_a],
                    captured["charters"][fid_b],
                ),
            }
        )
    values = [pair["jaccard"] for pair in pairs]
    return {
        "tick": captured["tick"],
        "active_count": len(active_fids),
        "active_fids": active_fids,
        "pair_count": len(pairs),
        "pairs": pairs,
        "mean_jaccard": finite_mean(values),
        "max_jaccard": finite_max(values),
        "min_jaccard": finite_min(values),
    }


def compute_quantiles(values: list[float]) -> dict[str, float]:
    finite_values = [value for value in values if not math.isnan(value)]
    if not finite_values:
        return {f"P{q}": float("nan") for q in QUANTILES}
    return {
        f"P{q}": float(np.percentile(finite_values, q, method="linear"))
        for q in QUANTILES
    }


def faction_sizes_from_snapshot(snapshot: JsonObject) -> dict[str, int]:
    raw_sizes = snapshot.get("faction_sizes")
    if not isinstance(raw_sizes, dict):
        raise TypeError(f"tick {snapshot.get('tick')}: faction_sizes is not an object")
    return {str(fid): int(cast(int | float | str, size)) for fid, size in raw_sizes.items()}


def assert_v3_anchor_match(
    seed: int,
    captured: list[CapturedSnapshot],
    v3_snapshots: list[JsonObject],
) -> AnchorValidation:
    assert len(captured) == EXPECTED_SNAPSHOT_COUNT, (
        f"seed {seed}: re-run snapshot count={len(captured)}, "
        f"expected={EXPECTED_SNAPSHOT_COUNT}"
    )
    assert len(v3_snapshots) == EXPECTED_SNAPSHOT_COUNT, (
        f"seed {seed}: V3 raw snapshot count={len(v3_snapshots)}, "
        f"expected={EXPECTED_SNAPSHOT_COUNT}"
    )
    for cap, v3 in zip(captured, v3_snapshots, strict=True):
        v3_tick = int(cast(int | float | str, v3["tick"]))
        assert cap["tick"] == v3_tick, (
            f"seed {seed}: tick mismatch re-run={cap['tick']} vs V3={v3_tick}"
        )
        v3_sizes = faction_sizes_from_snapshot(v3)
        v3_fids = sorted(v3_sizes)
        if cap["active_fids"] != v3_fids:
            missing = sorted(set(v3_fids) - set(cap["active_fids"]))
            extra = sorted(set(cap["active_fids"]) - set(v3_fids))
            raise AssertionError(
                f"seed {seed} tick {cap['tick']}: active fid mismatch "
                f"missing={missing} extra={extra}"
            )
    for v3 in v3_snapshots:
        v3_tick = int(cast(int | float | str, v3["tick"]))
        v3_sizes = faction_sizes_from_snapshot(v3)
        active_count = int(cast(int | float | str, v3["active_count"]))
        assert active_count == len(v3_sizes), (
            f"seed {seed} tick {v3_tick}: active_count={active_count} "
            f"vs faction_sizes len={len(v3_sizes)}"
        )
    return {
        "snapshot_count_match": True,
        "fid_set_match_per_snapshot": True,
        "active_count_self_consistency": True,
        "passed": True,
    }


def count_nan(values: list[float]) -> int:
    return sum(1 for value in values if math.isnan(value))


def json_safe(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return value
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def dump_json(path: Path, payload: JsonObject) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(json_safe(payload), handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def markdown_quantile_rows(quantiles: dict[str, float]) -> str:
    rows = [
        "| 분위수 | 값 |",
        "|---|---:|",
    ]
    for q in QUANTILES:
        label = f"P{q}"
        rows.append(f"| {label} | {quantiles[label]:.6f} |")
    return "\n".join(rows)


def save_seed_json(
    path: Path,
    seed: int,
    snapshots: list[SnapshotMetrics],
    quantiles: dict[str, float],
    anchor_validation: AnchorValidation,
) -> None:
    all_values = [pair["jaccard"] for snapshot in snapshots for pair in snapshot["pairs"]]
    payload: JsonObject = {
        "seed": seed,
        "total_ticks": TOTAL_TICKS,
        "snapshot_interval": SNAPSHOT_INTERVAL,
        "snapshot_count": len(snapshots),
        "algorithm": "jaccard",
        "snapshots": snapshots,
        "all_pair_jaccard_distribution": {
            "n": len(all_values),
            "nan_count": count_nan(all_values),
            "quantiles": quantiles,
        },
        "v3_anchor_validation": anchor_validation,
    }
    dump_json(path, payload)


def save_seed_summary(
    path: Path,
    seed: int,
    snapshots: list[SnapshotMetrics],
    quantiles: dict[str, float],
    anchor_validation: AnchorValidation,
) -> None:
    all_values = [pair["jaccard"] for snapshot in snapshots for pair in snapshot["pairs"]]
    text = "\n".join(
        [
            f"# DC-2 CPCM overlap distribution - seed {seed}",
            "",
            f"- seed: {seed}",
            f"- total_ticks: {TOTAL_TICKS}",
            f"- snapshot_count: {len(snapshots)}",
            f"- snapshot_interval: {SNAPSHOT_INTERVAL}",
            "- algorithm: Jaccard",
            f"- 활성 faction pair 관측치: {len(all_values)}",
            f"- 빈 charter pair (nan): {count_nan(all_values)}",
            "",
            "## 분위수 후보",
            "",
            markdown_quantile_rows(quantiles),
            "",
            "## V3 anchor 검증",
            "",
            f"- snapshot count: {anchor_validation['snapshot_count_match']}",
            f"- active fid set match: {anchor_validation['fid_set_match_per_snapshot']}",
            f"- active_count self-consistency: {anchor_validation['active_count_self_consistency']}",
            f"- passed: {anchor_validation['passed']}",
            "",
            "## 주의",
            "",
            "이 결과는 exploratory telemetry다. 분위수 후보만 산출하며 의사결정 조건을 고정하지 않는다.",
            "P5R body semantics나 branch rule로 승격하지 않는다.",
            "",
        ]
    )
    with path.open("w", encoding="utf-8") as handle:
        handle.write(text)


def process_seed(seed: int) -> SeedResult:
    print(f"processing seed-{seed}")
    events_path = DATA_ROOT / f"seed-{seed}" / "case_c_events.json"
    v3_snapshots = load_v3_active_snapshots(events_path)
    captured = run_engine_and_capture_charters(seed)
    anchor_validation = assert_v3_anchor_match(seed, captured, v3_snapshots)
    snapshots = [compute_snapshot_metrics(entry) for entry in captured]
    all_jaccards = [pair["jaccard"] for snapshot in snapshots for pair in snapshot["pairs"]]
    quantiles = compute_quantiles(all_jaccards)

    out_dir = OUT_ROOT / f"seed-{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_seed_json(
        out_dir / "overlap_distribution.json",
        seed,
        snapshots,
        quantiles,
        anchor_validation,
    )
    save_seed_summary(
        out_dir / "summary.md",
        seed,
        snapshots,
        quantiles,
        anchor_validation,
    )
    return {
        "seed": seed,
        "snapshots": snapshots,
        "quantiles": quantiles,
        "all_jaccards": all_jaccards,
        "anchor_validation": anchor_validation,
    }


def consistency_details(per_seed: list[SeedResult]) -> dict[str, JsonObject]:
    details: dict[str, JsonObject] = {}
    for q_name in CONSISTENCY_QUANTILES:
        values = {
            str(seed_result["seed"]): seed_result["quantiles"][q_name]
            for seed_result in per_seed
        }
        finite_values = [value for value in values.values() if not math.isnan(value)]
        if not finite_values:
            mean_value = float("nan")
            passed = False
        else:
            mean_value = sum(finite_values) / len(finite_values)
            if mean_value == 0.0:
                passed = all(value == 0.0 for value in finite_values)
            else:
                passed = all(
                    abs(value - mean_value) / abs(mean_value) <= 0.10
                    for value in finite_values
                )
        details[q_name] = {
            "values_by_seed": values,
            "mean": mean_value,
            "within_10pct": passed,
        }
    return details


def save_aggregate_json(
    path: Path,
    aggregate_quantiles: dict[str, float],
    consistency: dict[str, JsonObject],
    per_seed: list[SeedResult],
) -> None:
    payload: JsonObject = {
        "seeds_combined": list(SEEDS),
        "total_ticks": TOTAL_TICKS,
        "snapshot_interval": SNAPSHOT_INTERVAL,
        "snapshot_count_per_seed": EXPECTED_SNAPSHOT_COUNT,
        "algorithm": "jaccard",
        "total_pair_observations": sum(
            len(seed_result["all_jaccards"]) for seed_result in per_seed
        ),
        "aggregate_quantiles": aggregate_quantiles,
        "consistency_within_10pct": consistency,
        "per_seed_summary": [
            {
                "seed": seed_result["seed"],
                "quantiles": seed_result["quantiles"],
                "n": len(seed_result["all_jaccards"]),
                "nan_count": count_nan(seed_result["all_jaccards"]),
            }
            for seed_result in per_seed
        ],
        "v3_anchor_validation_all_seeds": all(
            seed_result["anchor_validation"]["passed"] for seed_result in per_seed
        ),
    }
    dump_json(path, payload)


def save_aggregate_summary(
    path: Path,
    aggregate_quantiles: dict[str, float],
    consistency: dict[str, JsonObject],
    per_seed: list[SeedResult],
) -> None:
    lines = [
        "# DC-2 CPCM aggregate overlap distribution",
        "",
        f"- seed: {', '.join(str(seed) for seed in SEEDS)}",
        f"- total_ticks: {TOTAL_TICKS}",
        f"- snapshot_count_per_seed: {EXPECTED_SNAPSHOT_COUNT}",
        "- algorithm: Jaccard",
        "",
        "## 분위수 후보",
        "",
        markdown_quantile_rows(aggregate_quantiles),
        "",
        "## Seed consistency within 10 percent",
        "",
        "| 분위수 | within_10pct | mean | seed_7 | seed_13 | seed_42 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for q_name in CONSISTENCY_QUANTILES:
        row = consistency[q_name]
        values = cast(dict[str, float], row["values_by_seed"])
        lines.append(
            f"| {q_name} | {str(row['within_10pct']).lower()} | "
            f"{float(cast(float, row['mean'])):.6f} | "
            f"{values['7']:.6f} | {values['13']:.6f} | {values['42']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## V3 anchor 검증",
            "",
            "| seed | snapshot_count | fid set match | active_count self-consistency |",
            "|---:|---:|---:|---:|",
        ]
    )
    for seed_result in per_seed:
        validation = seed_result["anchor_validation"]
        lines.append(
            f"| {seed_result['seed']} | {validation['snapshot_count_match']} | "
            f"{validation['fid_set_match_per_snapshot']} | "
            f"{validation['active_count_self_consistency']} |"
        )
    lines.extend(
        [
            "",
            "## 주의",
            "",
            "이 결과는 exploratory telemetry다. 분위수 후보만 산출하며 의사결정 조건을 고정하지 않는다.",
            "SIS와 CPCM 결합, P5R body, branch rule 승격은 별도 spec에서 다룬다.",
            "",
        ]
    )
    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def aggregate_and_consistency(per_seed: list[SeedResult]) -> None:
    all_jaccards = [
        value for seed_result in per_seed for value in seed_result["all_jaccards"]
    ]
    aggregate_quantiles = compute_quantiles(all_jaccards)
    consistency = consistency_details(per_seed)

    out_dir = OUT_ROOT / "aggregate"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_aggregate_json(
        out_dir / "overlap_distribution.json",
        aggregate_quantiles,
        consistency,
        per_seed,
    )
    save_aggregate_summary(
        out_dir / "summary.md",
        aggregate_quantiles,
        consistency,
        per_seed,
    )


def main() -> None:
    per_seed = [process_seed(seed) for seed in SEEDS]
    aggregate_and_consistency(per_seed)
    print(f"wrote CPCM outputs to {OUT_ROOT}")
    for result in per_seed:
        print(
            "seed-{seed}: snapshots={snapshots}, pairs={pairs}, P50={p50:.6f}".format(
                seed=result["seed"],
                snapshots=len(result["snapshots"]),
                pairs=len(result["all_jaccards"]),
                p50=result["quantiles"]["P50"],
            )
        )


if __name__ == "__main__":
    main()
