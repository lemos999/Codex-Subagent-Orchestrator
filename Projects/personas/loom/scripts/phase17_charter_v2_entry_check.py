# -*- coding: utf-8 -*-
"""Phase 17 Charter v2 Φ-3 진입 OR 조건 3종 정량 측정.

Charter v2 PHASE-17-FACTION-CHARTER.md "Phi-3 Entry Trigger Candidates":
1. Geographic differentiation: factions_in_contact >= 1
2. Population imbalance: max / sum >= 0.55
3. Shared grievance: 2개 이상 faction이 같은 lord_id를 각각 ≥2명 멤버로 공유

부수 측정: gini 추세 (Stage 5↔6 비교), drift_ratio, 1000~5000 tick 범위 min_active.

사용법:
    py Projects/personas/loom/scripts/phase17_charter_v2_entry_check.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"

DATASETS = [
    ("v6", "Stage 4 이전 collapse"),
    ("stage5", "Stage 5 founder_lineage 도입 직전"),
    ("stage6", "Stage 6 H-lite founder_lineage(W=0.2) 도입 후"),
]
SEEDS = [7, 13, 42]


def load_metrics(seed: int, label: str) -> list[dict]:
    suffix = "phase17_probe_v6" if label == "v6" else f"phase17_probe_{label}"
    path = DATA_ROOT / suffix / f"seed-{seed}" / "metrics.jsonl"
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def population_at(events: list[dict], target_tick: int) -> dict | None:
    pop = [e for e in events if e["type"] == "population" and e["tick"] == target_tick]
    return pop[0]["data"] if pop else None


def population_imbalance_end(events: list[dict]) -> tuple[int, int, int, float]:
    pop = [e for e in events if e["type"] == "population"]
    last = max(pop, key=lambda e: e["tick"])
    counts = list(last["data"].values())
    s = sum(counts)
    m = max(counts) if counts else 0
    share = m / s if s else 0.0
    return last["tick"], s, m, share


def contact_pairs_end(events: list[dict]) -> tuple[int, int]:
    contact = [e for e in events if e["type"] == "contact"]
    last = max(contact, key=lambda e: e["tick"])
    pairs = last.get("pairs", [])  # top-level (not under 'data')
    return last["tick"], len(pairs)


def grievance_shared_pairs(events: list[dict]) -> tuple[int, int, list[tuple]]:
    """Charter v2 OR-3: 같은 lord_id를 각각 ≥2명 멤버로 가진 faction 쌍 수.

    metrics.jsonl 형식: {tick, type, raw: {fid: {lord_id: count}}, shared_pairs: int}
    raw로 직접 재계산하여 사전 계산된 shared_pairs와 검증한다.
    """
    gri = [e for e in events if e["type"] == "grievance_targets"]
    last = max(gri, key=lambda e: e["tick"])
    raw = last.get("raw", {})  # top-level (not 'data')
    by_lord: dict[str, dict[str, int]] = {}
    for fid, lord_map in raw.items():
        for lord_id, cnt in lord_map.items():
            by_lord.setdefault(lord_id, {})[fid] = int(cnt)
    pairs: list[tuple] = []
    for lord_id, fid_counts in by_lord.items():
        eligible = sorted([fid for fid, c in fid_counts.items() if c >= 2])
        for i in range(len(eligible)):
            for j in range(i + 1, len(eligible)):
                pairs.append((lord_id[:8], eligible[i][:8], eligible[j][:8]))
    return last["tick"], len(pairs), pairs


def gini_at(events: list[dict], target_tick: int) -> float | None:
    wealth = [e for e in events if e["type"] == "wealth" and e["tick"] == target_tick]
    if not wealth:
        return None
    fid_data = wealth[0]["data"]
    ginis = [v["gini"] for v in fid_data.values() if "gini" in v]
    return sum(ginis) / len(ginis) if ginis else 0.0


def gini_curve(events: list[dict]) -> list[tuple[int, float]]:
    out = []
    for e in events:
        if e["type"] == "wealth":
            ginis = [v["gini"] for v in e["data"].values() if "gini" in v]
            avg = sum(ginis) / len(ginis) if ginis else 0.0
            out.append((e["tick"], avg))
    out.sort()
    return out


def source_ratios(events: list[dict]) -> dict[str, float]:
    """누적 source 비율 — last source_cumulative 이벤트."""
    src = [e for e in events if e["type"] == "source_cumulative"]
    if not src:
        return {}
    last = max(src, key=lambda e: e["tick"])
    data = last.get("data", {})
    total = sum(data.values()) or 1
    return {k: v / total for k, v in data.items()}


def min_active_1000to5000(events: list[dict]) -> int | None:
    pop = [e for e in events if e["type"] == "population" and 1000 <= e["tick"] <= 5000]
    if not pop:
        return None
    return min(sum(1 for v in e["data"].values() if v > 0) for e in pop)


def main() -> None:
    print()
    print("=" * 100)
    print("Phase 17 Charter v2 Φ-3 진입 OR 조건 3종 정량 측정")
    print("=" * 100)
    for seed in SEEDS:
        print(f"\n## seed {seed}")
        rows: list[dict] = []
        for label, desc in DATASETS:
            try:
                events = load_metrics(seed, label)
            except FileNotFoundError:
                print(f"  - {label}: 데이터 없음")
                continue
            pt, total, top, share = population_imbalance_end(events)
            ct, cpairs = contact_pairs_end(events)
            gt, gpairs, gpair_detail = grievance_shared_pairs(events)
            g2500 = gini_at(events, 2500)
            g5000 = gini_at(events, 5000)
            min_a = min_active_1000to5000(events)
            sr = source_ratios(events)
            drift = sr.get("drift", 0.0)
            rows.append({
                "label": label, "desc": desc,
                "pt": pt, "total": total, "top": top, "share": share,
                "ct": ct, "cpairs": cpairs,
                "gt": gt, "gpairs": gpairs, "gpair_detail": gpair_detail,
                "g2500": g2500, "g5000": g5000,
                "min_a": min_a, "drift": drift,
            })

        print(f"  {'set':>7} | {'min_act':>7} | {'pop@end':>8} | {'top':>4} | {'dom%':>5} | {'cont':>4} | {'gri':>4} | {'gini2500':>8} | {'gini5000':>8} | {'drift%':>6}")
        print(f"  {'-'*7} | {'-'*7} | {'-'*8} | {'-'*4} | {'-'*5} | {'-'*4} | {'-'*4} | {'-'*8} | {'-'*8} | {'-'*6}")
        for r in rows:
            g25 = f"{r['g2500']:.3f}" if r["g2500"] is not None else "-"
            g50 = f"{r['g5000']:.3f}" if r["g5000"] is not None else "-"
            print(
                f"  {r['label']:>7} | {r['min_a']!s:>7} | {r['total']:>8} | {r['top']:>4} | "
                f"{r['share']*100:>4.1f}% | {r['cpairs']:>4} | {r['gpairs']:>4} | "
                f"{g25:>8} | {g50:>8} | {r['drift']*100:>5.1f}%"
            )

        # OR conditions on stage6
        s6 = next((r for r in rows if r["label"] == "stage6"), None)
        if s6:
            or1 = s6["cpairs"] >= 1
            or2 = s6["share"] >= 0.55
            or3 = s6["gpairs"] >= 1
            satisfied = sum([or1, or2, or3])
            print(f"\n  Charter v2 Phi-3 entry OR condition (stage6, tick {s6['pt']}/{s6['ct']}/{s6['gt']}):")
            print(f"    [{'PASS' if or1 else 'FAIL'}] OR-1 Geographic: contact_pairs={s6['cpairs']} (>=1 required)")
            print(f"    [{'PASS' if or2 else 'FAIL'}] OR-2 Imbalance:  dom_share={s6['share']*100:.1f}% (>=55% required)")
            print(f"    [{'PASS' if or3 else 'FAIL'}] OR-3 Grievance:  shared_pairs={s6['gpairs']} (>=1 required)")
            print(f"    -> satisfied {satisfied}/3 (OR condition: any 1 enables Phi-3 entry)")


if __name__ == "__main__":
    main()
