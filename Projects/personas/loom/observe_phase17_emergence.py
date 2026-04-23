"""Phase 17 Faction emergence probe runner.

Collects emergence metrics without mutating engine internals.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.multi_tick_engine import MultiTickEngine
from ontology.layers import GRIEVANCE_MIN_SHARED

OUT_ROOT = Path(__file__).resolve().parent / "data" / "phase17_probe"
DEFAULT_SEEDS = (7, 13, 42)
DEFAULT_TICKS = 5000
QUICK_SEEDS = (42,)
QUICK_TICKS = 500


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 17 Faction emergence probe")
    parser.add_argument(
        "--seeds",
        default=",".join(str(seed) for seed in DEFAULT_SEEDS),
        help="Comma-separated seeds (default: 7,13,42)",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=DEFAULT_TICKS,
        help="Ticks per seed (default: 5000)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Smoke mode: seed 42 only, 500 ticks",
    )
    return parser.parse_args()


def _parse_seed_text(seed_text: str) -> list[int]:
    seeds: list[int] = []
    for chunk in seed_text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        seeds.append(int(chunk))
    if not seeds:
        raise ValueError("at least one seed is required")
    return seeds


def _write_jsonl_line(handle, payload: dict[str, Any]) -> None:
    handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    handle.flush()


def _active_counts(dist: dict[str, int]) -> list[int]:
    return [int(count) for count in dist.values() if int(count) > 0]


def _entropy_evenness(dist: dict[str, int]) -> float:
    counts = _active_counts(dist)
    if not counts:
        return 0.0
    if len(counts) == 1:
        return 1.0
    total = float(sum(counts))
    entropy = 0.0
    for count in counts:
        prob = count / total
        if prob > 0.0:
            entropy -= prob * math.log(prob)
    return entropy / math.log(len(counts))


def _source_cumulative(engine: MultiTickEngine) -> dict[str, int]:
    counts = Counter()
    for event in engine.event_log:
        if event.get("type") == "faction_change":
            counts[str(event.get("source", "unknown"))] += 1
    return {
        "birth_founder": int(counts.get("birth_founder", 0)),
        "affiliation": int(counts.get("affiliation", 0)),
        "drift": int(counts.get("drift", 0)),
        "conflict": int(counts.get("conflict", 0)),
    }


def _shared_grievance_pairs(raw: dict[str, dict[str, int]]) -> int:
    shared_pairs: set[tuple[str, str]] = set()
    lords = sorted({lord_id for counts in raw.values() for lord_id in counts})
    for lord_id in lords:
        carriers = sorted(
            fid for fid, counts in raw.items()
            if counts.get(lord_id, 0) > 0
        )
        for index, fid_a in enumerate(carriers):
            for fid_b in carriers[index + 1:]:
                shared_pairs.add((fid_a, fid_b))
    return len(shared_pairs)


def _safe_grievance_targets(engine: MultiTickEngine) -> dict[str, dict[str, int]]:
    try:
        return engine.faction_grievance_targets()
    except KeyError:
        result: dict[str, dict[str, int]] = {fid: {} for fid in sorted(engine.factions)}
        for pid in sorted(engine.personas):
            if pid not in engine.inners:
                continue
            persona = engine.personas[pid]
            if persona.faction is None or persona.faction not in result:
                continue
            inner = engine.inners[pid]
            if inner.grievance >= GRIEVANCE_MIN_SHARED and inner.grievance_lord_id is not None:
                counts = result[persona.faction]
                counts[inner.grievance_lord_id] = counts.get(inner.grievance_lord_id, 0) + 1
        return result


def _dump_snapshot(handle, engine: MultiTickEngine, tick: int) -> None:
    if tick == 0 or tick % 100 == 0:
        _write_jsonl_line(
            handle,
            {
                "tick": tick,
                "type": "population",
                "data": engine.faction_population_distribution(),
            },
        )
        pairs = engine.factions_in_contact(radius=1)
        _write_jsonl_line(
            handle,
            {
                "tick": tick,
                "type": "contact",
                "pairs": [list(pair) for pair in pairs],
                "count": len(pairs),
            },
        )
    if tick == 0 or tick % 500 == 0:
        _write_jsonl_line(
            handle,
            {
                "tick": tick,
                "type": "wealth",
                "data": engine.faction_wealth_distribution(),
            },
        )
        grievance_raw = _safe_grievance_targets(engine)
        _write_jsonl_line(
            handle,
            {
                "tick": tick,
                "type": "grievance_targets",
                "raw": grievance_raw,
                "shared_pairs": _shared_grievance_pairs(grievance_raw),
            },
        )
    if tick == 0 or tick % 1000 == 0:
        _write_jsonl_line(
            handle,
            {
                "tick": tick,
                "type": "source_cumulative",
                "data": _source_cumulative(engine),
            },
        )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _sample_population_rows(rows: list[dict[str, Any]], ticks: int) -> list[dict[str, Any]]:
    wanted = {0, ticks}
    step = 1000
    for tick in range(step, ticks, step):
        wanted.add(tick)
    samples: list[dict[str, Any]] = []
    for row in rows:
        if row.get("type") != "population":
            continue
        tick = int(row["tick"])
        if tick not in wanted:
            continue
        dist = {str(fid): int(count) for fid, count in row["data"].items()}
        active = _active_counts(dist)
        samples.append(
            {
                "tick": tick,
                "active": len(active),
                "largest": max(active) if active else 0,
                "evenness": _entropy_evenness(dist),
            }
        )
    return samples


def _gini_mean(wealth_row: dict[str, Any] | None) -> float:
    if not wealth_row:
        return 0.0
    data = wealth_row["data"]
    values = [
        float(payload["gini"])
        for payload in data.values()
        if float(payload.get("total", 0.0)) > 0.0
    ]
    if not values:
        values = [float(payload["gini"]) for payload in data.values()]
    return sum(values) / len(values) if values else 0.0


def _last_row(rows: list[dict[str, Any]], row_type: str) -> dict[str, Any] | None:
    for row in reversed(rows):
        if row.get("type") == row_type:
            return row
    return None


def _build_seed_summary(seed: int, ticks: int, elapsed: float, jsonl_path: Path) -> tuple[str, dict[str, Any]]:
    rows = _load_jsonl(jsonl_path)
    population_rows = [row for row in rows if row.get("type") == "population"]
    contact_rows = [row for row in rows if row.get("type") == "contact"]
    wealth_rows = [row for row in rows if row.get("type") == "wealth"]
    grievance_rows = [row for row in rows if row.get("type") == "grievance_targets"]
    source_row = _last_row(rows, "source_cumulative")

    initial_population = population_rows[0]["data"] if population_rows else {}
    final_population = population_rows[-1]["data"] if population_rows else {}
    initial_active = len(_active_counts(initial_population))
    final_active = len(_active_counts(final_population))
    total_events = sum(source_row["data"].values()) if source_row else 0
    final_contact_count = int(contact_rows[-1]["count"]) if contact_rows else 0
    final_shared_pairs = int(grievance_rows[-1]["shared_pairs"]) if grievance_rows else 0

    source_counts = source_row["data"] if source_row else {
        "birth_founder": 0,
        "affiliation": 0,
        "drift": 0,
        "conflict": 0,
    }
    drift_ratio = (
        float(source_counts["drift"]) / float(total_events)
        if total_events > 0 else 0.0
    )

    gini_500 = _gini_mean(next((row for row in wealth_rows if int(row["tick"]) == 500), None))
    gini_mid = _gini_mean(next((row for row in wealth_rows if int(row["tick"]) == 2500), None))
    gini_end = _gini_mean(wealth_rows[-1] if wealth_rows else None)

    pass_diversified = final_active > initial_active
    pass_contact = final_contact_count >= 1
    pass_drift = drift_ratio >= 0.05
    pass_gini = gini_end > gini_500
    verdict = "PASS" if all((pass_diversified, pass_contact, pass_drift, pass_gini)) else "FAIL"

    population_table = _sample_population_rows(rows, ticks)
    trend = "증가" if gini_end > gini_500 else "감소" if gini_end < gini_500 else "정체"

    summary_lines = [
        f"# Phase 17 Emergence Probe — seed {seed}",
        "",
        "## 실행 요약",
        f"- 틱: {ticks}",
        f"- 시작 faction 수: {initial_active}",
        f"- 종료 faction 수: {final_active}",
        f"- 총 faction_change 이벤트: {total_events}",
        f"- 경과: {elapsed:.1f}s ({elapsed / max(1, ticks) * 1000:.1f}ms/tick)",
        "",
        "## 분포 진화 (1000틱 간격 샘플)",
        "| tick | 활성 faction 수 | 최대 소속 인원 | 균등도 (H/Hmax) |",
        "|------|----------------|----------------|------------------|",
    ]
    for row in population_table:
        summary_lines.append(
            f"| {row['tick']} | {row['active']} | {row['largest']} | {row['evenness']:.2f} |"
        )

    summary_lines.extend(
        [
            "",
            "## Φ-3 재료: 접촉 쌍 추이",
            f"- tick 0: {int(contact_rows[0]['count']) if contact_rows else 0}쌍",
            f"- tick 1000: {int(next((row['count'] for row in contact_rows if int(row['tick']) == 1000), 0))}쌍",
            f"- tick {ticks}: {final_contact_count}쌍",
            f"- **판정**: {'[PASS]' if pass_contact else '[FAIL]'} if ≥1쌍 at tick {ticks} else [FAIL]",
            "",
            "## Source 비율 (누적)",
            "| source | count | pct |",
            "|--------|-------|-----|",
        ]
    )
    for source in ("birth_founder", "affiliation", "drift", "conflict"):
        count = int(source_counts[source])
        pct = (count / total_events * 100.0) if total_events else 0.0
        summary_lines.append(f"| {source} | {count} | {pct:.0f}% |")

    summary_lines.extend(
        [
            "",
            f"**판정**: drift ≥ 5% → {'[PASS]' if pass_drift else '[FAIL]'}",
            "",
            "## Wealth gini 추이",
            f"- tick 500: avg gini {gini_500:.2f}",
            f"- tick 2500: avg gini {gini_mid:.2f}",
            f"- tick {ticks}: avg gini {gini_end:.2f}",
            f"- **경향**: [{trend}]",
            "",
            "## Grievance 공유 (봉기 재료)",
            f"- tick {ticks} 기준: {final_shared_pairs} 쌍의 faction이 같은 lord를 grievance 대상으로 공유",
            f"- **판정**: {'[PASS]' if final_shared_pairs >= 1 else '[N/A]'} if ≥1쌍 else [N/A]",
            "",
            "## 종합 판정",
            f"- {'[PASS]' if pass_diversified else '[FAIL]'} 분화 발생 (최종 active faction 수 > 초기)",
            f"- {'[PASS]' if pass_contact else '[FAIL]'} 접촉 쌍 ≥ 1 (Φ-3 진입 가능)",
            f"- {'[PASS]' if pass_drift else '[FAIL]'} drift source ≥ 5% (bottom-up 재배치 실제 발생)",
            f"- {'[PASS]' if pass_gini else '[FAIL]'} wealth gini 증가 경향 (계급 재료 축적)",
            "",
            "## 이상 징후 (있을 경우)",
        ]
    )
    if final_active <= 0:
        summary_lines.append("- [WARN] no factions emerged")
    else:
        summary_lines.append("- 없음")

    result = {
        "seed": seed,
        "ticks": ticks,
        "elapsed": elapsed,
        "ms_per_tick": elapsed / max(1, ticks) * 1000.0,
        "active_factions_end": final_active,
        "contact_pairs_end": final_contact_count,
        "drift_ratio": drift_ratio,
        "gini_mean_end": gini_end,
        "verdict": verdict,
        "shared_pairs_end": final_shared_pairs,
        "total_events": total_events,
    }
    return "\n".join(summary_lines) + "\n", result


def run_seed(seed: int, ticks: int) -> dict[str, Any]:
    engine = MultiTickEngine(seed=seed)
    out_dir = OUT_ROOT / f"seed-{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "metrics.jsonl"
    summary_path = out_dir / "summary.md"

    with jsonl_path.open("w", encoding="utf-8") as handle:
        _dump_snapshot(handle, engine, tick=0)
        started = time.time()
        for tick in range(1, ticks + 1):
            engine.tick()
            _dump_snapshot(handle, engine, tick=tick)
        elapsed = time.time() - started

    summary_text, result = _build_seed_summary(seed, ticks, elapsed, jsonl_path)
    summary_path.write_text(summary_text, encoding="utf-8")
    result["summary_path"] = str(summary_path)
    result["jsonl_path"] = str(jsonl_path)
    return result


def _write_top_summary(results: list[dict[str, Any]]) -> None:
    lines = [
        "# Phase 17 Emergence Probe — 전체 요약",
        "",
        "| seed | active_factions_end | contact_pairs_end | drift_ratio | gini_mean_end | verdict |",
        "|------|---------------------|-------------------|-------------|---------------|---------|",
    ]
    all_pass = True
    for result in results:
        if "error" in result:
            all_pass = False
            lines.append(
                f"| {result['seed']} | ERROR | ERROR | ERROR | ERROR | FAIL ({result['error']}) |"
            )
            continue
        lines.append(
            f"| {result['seed']} | {result['active_factions_end']} | {result['contact_pairs_end']} "
            f"| {result['drift_ratio'] * 100:.0f}% | {result['gini_mean_end']:.2f} | {result['verdict']} |"
        )
        all_pass = all_pass and result["verdict"] == "PASS"
    lines.extend(
        [
            "",
            (
                "**3 seed 전원 PASS 시 Φ-3 Struggle 진입 가능.**"
                if all_pass and results
                else "**추가 검토 필요: 일부 seed가 FAIL 또는 ERROR 입니다.**"
            ),
            "",
        ]
    )
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = _parse_args()
    seeds = list(QUICK_SEEDS if args.quick else _parse_seed_text(args.seeds))
    ticks = QUICK_TICKS if args.quick else int(args.ticks)

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for seed in seeds:
        print(f"[run] seed={seed} ticks={ticks}", flush=True)
        try:
            result = run_seed(seed, ticks)
        except Exception as exc:  # pragma: no cover - runtime reporting path
            print(f"[fail] seed={seed}: {exc}", flush=True)
            results.append({"seed": seed, "error": str(exc)})
            continue
        print(
            "[done] seed={seed} active={active} contact={contact} drift={drift:.1f}% gini={gini:.2f} verdict={verdict}".format(
                seed=seed,
                active=result["active_factions_end"],
                contact=result["contact_pairs_end"],
                drift=result["drift_ratio"] * 100.0,
                gini=result["gini_mean_end"],
                verdict=result["verdict"],
            ),
            flush=True,
        )
        results.append(result)

    _write_top_summary(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
