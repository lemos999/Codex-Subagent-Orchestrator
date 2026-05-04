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
from test_phase17_acceptance import (
    _format_observe_perf_line,
    _measure_faction_kernel_ms,
    _measure_tick_ms_stable,
)

DEFAULT_OUT_ROOT = Path(__file__).resolve().parent / "data" / "phase17_probe"
DEFAULT_SEEDS = (7, 13, 42)
DEFAULT_TICKS = 5000
QUICK_SEEDS = (42,)
QUICK_TICKS = 500
CASE_C_EVENT_TYPES = {
    "uprising_skip_no_contact",
    "respawn_skip_reason",
    "respawn_fallback_attempt",
    "respawn_fallback_founder_created",
    "minority_boost_applied",
    "drift_recovery_to_minority",
    "active_factions_snapshot",
    # Phase 17 過-3 Case-C P1+P2 telemetry (2026-04-30 hotfix)
    "cross_faction_lord_pair_emerged",
    "cross_faction_lord_pair_collapsed",
    "uprising_skip_snn_inactive",
}
# Phase 14B-d1 SNN 異쒕젰 ?뚮줈 吏꾨떒 telemetry (2026-05-02)
SNN_OUTPUT_DIAG_EVENT_TYPES = {
    "uprising_leader_snn_snapshot",
    "founder_absorbed_snn_snapshot",
    "small_faction_snn_snapshot",
    "territory_snn_distribution",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 17 Faction emergence probe")
    parser.add_argument(
        "--seeds",
        nargs="*",
        default=None,
        help="Seeds as comma-separated text or space-separated values (default: 7,13,42)",
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
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory (default: data/phase17_probe or data/phase17_probe_<label>)",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="Probe label. Example: --label phi3 writes data/phase17_probe_phi3 by default.",
    )
    parser.add_argument(
        "--measure-tick-time",
        action="store_true",
        help="Compatibility flag: print tick/faction-kernel timing line at the end.",
    )
    return parser.parse_args()


def _parse_seed_arg(seed_arg) -> list[int]:
    if seed_arg is None:
        return list(DEFAULT_SEEDS)
    if isinstance(seed_arg, str):
        chunks = seed_arg.split(",")
    else:
        chunks = []
        for item in seed_arg:
            chunks.extend(str(item).split(","))
    seeds: list[int] = []
    for chunk in chunks:
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


def _case_c_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(event) for event in events if event.get("type") in CASE_C_EVENT_TYPES]


def _snn_output_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Phase 14B-d1 SNN 異쒕젰 吏꾨떒 telemetry 4醫?異붿텧 (uprising leader / founder absorbed / small faction / territory dist)."""
    return [dict(event) for event in events if event.get("type") in SNN_OUTPUT_DIAG_EVENT_TYPES]


def _write_json_file(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _case_c_counter(events: list[dict[str, Any]], event_type: str, **filters: Any) -> int:
    count = 0
    for event in events:
        if event.get("type") != event_type:
            continue
        if all(event.get(key) == value for key, value in filters.items()):
            count += 1
    return count


def _stat_summary(values: list[float]) -> dict[str, Any]:
    """list of float ??{n, avg, std, min, max} ?듦퀎 (鍮?由ъ뒪????None)."""
    if not values:
        return {"n": 0, "avg": None, "std": None, "min": None, "max": None}
    arr = [float(v) for v in values]
    n = len(arr)
    avg = sum(arr) / n
    if n > 1:
        var = sum((v - avg) ** 2 for v in arr) / (n - 1)
        std = math.sqrt(var)
    else:
        std = 0.0
    return {
        "n": n,
        "avg": float(avg),
        "std": float(std),
        "min": float(min(arr)),
        "max": float(max(arr)),
    }


def _phase14b_d1_diagnosis(
    events: list[dict[str, Any]], engine: MultiTickEngine
) -> dict[str, Any]:
    """Phase 14B-d1 SNN 異쒕젰 ?뚮줈 吏꾨떒 ??4 媛??PASS/FAIL/INSUFFICIENT_N 痢≪젙.

    媛??(?먯뿰 痢≪젙 湲곕컲, mechanism 臾댁닔??:
        G1: uprising leader gate_passed 洹몃９??SNN ?됯퇏??gate_failed 洹몃９蹂대떎 ?쇨? 李⑥씠 ?덈뒗媛?
            (PASS 議곌굔: ??洹몃９ 紐⑤몢 n>=5 + |diff_anger|+|diff_fear|+|diff_dignity|+|diff_chronic| > 0.05)
        G2: founder ?≪닔 ??founder SNN怨?absorbing faction avg SNN 李⑥씠媛 紐낇솗?쒓??
            (PASS 議곌굔: n>=5 + |diff_chronic| > 0.05)
        G3: small_faction snapshot fid媛 5000??醫낅즺 ???쒖꽦(persisted)/?뚮㈇(expired)??洹몃９蹂?SNN ?됯퇏 李⑥씠?
            (PASS 議곌굔: ??洹몃９ 紐⑤몢 n>=5 + |diff_chronic| + |diff_anger| > 0.05)
        G4: territory蹂??쒓퀎??(avg_chronic_stress ?? ??CV (std/mean) ???숈쭏???щ? 痢≪젙.
            (PASS 議곌굔: ?됯퇏 CV >= 0.05 ??遺꾩궛 ?댁븘?덉쓬)
    """
    snn_events = _snn_output_events(events)

    # ?? G1: uprising leader gate_passed/failed 洹몃９蹂?SNN ???????????????
    g1_pass_snn = {"anger": [], "fear": [], "dignity": [], "chronic": [], "grievance": []}
    g1_fail_snn = {"anger": [], "fear": [], "dignity": [], "chronic": [], "grievance": []}
    for ev in snn_events:
        if ev.get("type") != "uprising_leader_snn_snapshot":
            continue
        bucket = g1_pass_snn if ev.get("gate_passed") else g1_fail_snn
        bucket["anger"].append(float(ev.get("leader_anger", 0.0)))
        bucket["fear"].append(float(ev.get("leader_fear", 0.0)))
        bucket["dignity"].append(float(ev.get("leader_dignity", 0.0)))
        bucket["chronic"].append(float(ev.get("leader_chronic_stress", 0.0)))
        bucket["grievance"].append(float(ev.get("leader_grievance", 0.0)))

    g1_pass_stats = {k: _stat_summary(v) for k, v in g1_pass_snn.items()}
    g1_fail_stats = {k: _stat_summary(v) for k, v in g1_fail_snn.items()}
    n_pass = g1_pass_stats["anger"]["n"]
    n_fail = g1_fail_stats["anger"]["n"]
    if n_pass < 5 or n_fail < 5:
        g1_verdict = "INSUFFICIENT_N"
        g1_diff_sum = None
    else:
        diffs = []
        for key in ("anger", "fear", "dignity", "chronic"):
            a = g1_pass_stats[key]["avg"] or 0.0
            b = g1_fail_stats[key]["avg"] or 0.0
            diffs.append(abs(a - b))
        g1_diff_sum = float(sum(diffs))
        g1_verdict = "PASS" if g1_diff_sum > 0.05 else "FAIL"

    # ?? G2: founder ?≪닔 ??founder vs absorbing avg SNN ???????????????
    g2_diff_anger = []
    g2_diff_fear = []
    g2_diff_dignity = []
    g2_diff_chronic = []
    g2_diff_grievance = []
    g2_founder_chronic = []
    g2_absorbing_avg_chronic = []
    for ev in snn_events:
        if ev.get("type") != "founder_absorbed_snn_snapshot":
            continue
        f_a = float(ev.get("founder_anger", 0.0))
        f_f = float(ev.get("founder_fear", 0.0))
        f_d = float(ev.get("founder_dignity", 0.0))
        f_c = float(ev.get("founder_chronic_stress", 0.0))
        f_g = float(ev.get("founder_grievance", 0.0))
        a_a = float(ev.get("absorbing_faction_avg_anger", 0.0))
        a_f = float(ev.get("absorbing_faction_avg_fear", 0.0))
        a_d = float(ev.get("absorbing_faction_avg_dignity", 0.0))
        a_c = float(ev.get("absorbing_faction_avg_chronic", 0.0))
        g2_diff_anger.append(f_a - a_a)
        g2_diff_fear.append(f_f - a_f)
        g2_diff_dignity.append(f_d - a_d)
        g2_diff_chronic.append(f_c - a_c)
        g2_diff_grievance.append(f_g)
        g2_founder_chronic.append(f_c)
        g2_absorbing_avg_chronic.append(a_c)

    g2_n = len(g2_diff_chronic)
    g2_stats = {
        "n": g2_n,
        "diff_anger": _stat_summary(g2_diff_anger),
        "diff_fear": _stat_summary(g2_diff_fear),
        "diff_dignity": _stat_summary(g2_diff_dignity),
        "diff_chronic": _stat_summary(g2_diff_chronic),
        "founder_chronic": _stat_summary(g2_founder_chronic),
        "absorbing_avg_chronic": _stat_summary(g2_absorbing_avg_chronic),
    }
    if g2_n < 5:
        g2_verdict = "INSUFFICIENT_N"
    else:
        avg_diff_chronic = abs(g2_stats["diff_chronic"]["avg"] or 0.0)
        g2_verdict = "PASS" if avg_diff_chronic > 0.05 else "FAIL"

    # ?? G3: small_faction snapshot persisted/expired 洹몃９蹂?SNN ??????????
    persisted_anger, persisted_chronic, persisted_grievance = [], [], []
    expired_anger, expired_chronic, expired_grievance = [], [], []
    for ev in snn_events:
        if ev.get("type") != "small_faction_snn_snapshot":
            continue
        fid = ev.get("fid")
        members = ev.get("members_snn") or []
        if not members:
            continue
        member_avg_anger = sum(float(m.get("anger", 0.0)) for m in members) / len(members)
        member_avg_chronic = sum(float(m.get("chronic_stress", 0.0)) for m in members) / len(members)
        member_avg_grievance = sum(float(m.get("grievance", 0.0)) for m in members) / len(members)
        if fid in engine.factions:
            persisted_anger.append(member_avg_anger)
            persisted_chronic.append(member_avg_chronic)
            persisted_grievance.append(member_avg_grievance)
        else:
            expired_anger.append(member_avg_anger)
            expired_chronic.append(member_avg_chronic)
            expired_grievance.append(member_avg_grievance)

    g3_persisted = {
        "anger": _stat_summary(persisted_anger),
        "chronic": _stat_summary(persisted_chronic),
        "grievance": _stat_summary(persisted_grievance),
    }
    g3_expired = {
        "anger": _stat_summary(expired_anger),
        "chronic": _stat_summary(expired_chronic),
        "grievance": _stat_summary(expired_grievance),
    }
    n_persisted = g3_persisted["anger"]["n"]
    n_expired = g3_expired["anger"]["n"]
    if n_persisted < 5 or n_expired < 5:
        g3_verdict = "INSUFFICIENT_N"
        g3_diff_sum = None
    else:
        d_anger = abs((g3_persisted["anger"]["avg"] or 0.0) - (g3_expired["anger"]["avg"] or 0.0))
        d_chronic = abs((g3_persisted["chronic"]["avg"] or 0.0) - (g3_expired["chronic"]["avg"] or 0.0))
        g3_diff_sum = float(d_anger + d_chronic)
        g3_verdict = "PASS" if g3_diff_sum > 0.05 else "FAIL"

    # ?? G4: territory蹂??쒓퀎??CV (avg_chronic_stress / avg_anger) ???????
    territory_series: dict[str, dict[str, list[float]]] = {}
    for ev in snn_events:
        if ev.get("type") != "territory_snn_distribution":
            continue
        tid = ev.get("territory_id")
        if tid is None:
            continue
        slot = territory_series.setdefault(tid, {"chronic": [], "anger": [], "fear": [], "dignity": []})
        slot["chronic"].append(float(ev.get("avg_chronic_stress", 0.0)))
        slot["anger"].append(float(ev.get("avg_anger", 0.0)))
        slot["fear"].append(float(ev.get("avg_fear", 0.0)))
        slot["dignity"].append(float(ev.get("avg_dignity", 0.0)))

    territory_cvs = []
    territory_cv_breakdown = {}
    for tid, series in territory_series.items():
        chronic_stat = _stat_summary(series["chronic"])
        if chronic_stat["n"] < 3 or (chronic_stat["avg"] or 0.0) < 1e-6:
            continue
        cv = (chronic_stat["std"] or 0.0) / (chronic_stat["avg"] or 1e-6)
        territory_cvs.append(cv)
        territory_cv_breakdown[tid] = {
            "n": chronic_stat["n"],
            "avg_chronic": chronic_stat["avg"],
            "std_chronic": chronic_stat["std"],
            "cv_chronic": float(cv),
        }
    g4_n_territories = len(territory_cvs)
    if g4_n_territories < 1:
        g4_verdict = "INSUFFICIENT_N"
        g4_avg_cv = None
    else:
        g4_avg_cv = float(sum(territory_cvs) / g4_n_territories)
        g4_verdict = "PASS" if g4_avg_cv >= 0.05 else "FAIL"

    return {
        "g1_uprising_leader_gate_diff": {
            "verdict": g1_verdict,
            "n_pass": n_pass,
            "n_fail": n_fail,
            "diff_sum": g1_diff_sum,
            "pass_stats": g1_pass_stats,
            "fail_stats": g1_fail_stats,
        },
        "g2_founder_vs_absorbing": {
            "verdict": g2_verdict,
            "n": g2_n,
            "stats": g2_stats,
        },
        "g3_small_faction_persistence": {
            "verdict": g3_verdict,
            "n_persisted": n_persisted,
            "n_expired": n_expired,
            "diff_sum": g3_diff_sum,
            "persisted_stats": g3_persisted,
            "expired_stats": g3_expired,
        },
        "g4_territory_distribution_cv": {
            "verdict": g4_verdict,
            "n_territories": g4_n_territories,
            "avg_cv_chronic": g4_avg_cv,
            "per_territory": territory_cv_breakdown,
        },
        "telemetry_event_counts": {
            "uprising_leader_snn_snapshot": sum(1 for ev in snn_events if ev.get("type") == "uprising_leader_snn_snapshot"),
            "founder_absorbed_snn_snapshot": sum(1 for ev in snn_events if ev.get("type") == "founder_absorbed_snn_snapshot"),
            "small_faction_snn_snapshot": sum(1 for ev in snn_events if ev.get("type") == "small_faction_snn_snapshot"),
            "territory_snn_distribution": sum(1 for ev in snn_events if ev.get("type") == "territory_snn_distribution"),
        },
    }


def _case_c_diagnosis(events: list[dict[str, Any]]) -> dict[str, Any]:
    case_events = _case_c_events(events)
    snapshots = [
        event for event in case_events
        if event.get("type") == "active_factions_snapshot"
    ]
    final_snapshot = snapshots[-1] if snapshots else {}
    final_sizes = final_snapshot.get("faction_sizes", {}) or {}
    fallback_created = [
        event for event in case_events
        if event.get("type") == "respawn_fallback_founder_created"
    ]
    fallback_survived = sum(
        1 for event in fallback_created
        if str(event.get("faction_id")) in final_sizes
    )
    collapse_tick = next(
        (int(event["tick"]) for event in snapshots if int(event.get("active_count", 0)) <= 1),
        None,
    )
    fallback_attempts = [
        event for event in case_events
        if event.get("type") == "respawn_fallback_attempt"
    ]
    phase_a_all_blocked = sum(
        1 for event in fallback_attempts
        if event.get("phase_a_skips")
        and all(int(item.get("free_residents_count", 0)) < 3 for item in event["phase_a_skips"])
    )
    minority_boosts = [
        event for event in case_events
        if event.get("type") == "minority_boost_applied"
    ]
    drift_recovery = _case_c_counter(case_events, "drift_recovery_to_minority")
    h1_count = _case_c_counter(case_events, "uprising_skip_no_contact")
    h2b_count = _case_c_counter(
        case_events,
        "respawn_skip_reason",
        phase="after_b",
        reason="phase_b_insufficient",
    )
    cfl_emerged = [
        event for event in case_events
        if event.get("type") == "cross_faction_lord_pair_emerged"
    ]
    cfl_collapsed = [
        event for event in case_events
        if event.get("type") == "cross_faction_lord_pair_collapsed"
    ]
    cfl_reasons = Counter(str(event.get("collapse_reason", "unknown")) for event in cfl_collapsed)
    delayed_emerged = sum(1 for event in cfl_emerged if int(event.get("tick", 0)) >= 1000)
    durations = sorted(float(event.get("duration_ticks", 0.0)) for event in cfl_collapsed)

    def _percentile(values: list[float], pct: float) -> float | None:
        if not values:
            return None
        idx = min(len(values) - 1, max(0, int(math.ceil((pct / 100.0) * len(values))) - 1))
        return float(values[idx])

    return {
        "h1_uprising_skip_no_contact": h1_count,
        "h2a_phase_a_all_blocked": phase_a_all_blocked,
        "h2a_fallback_attempts": len(fallback_attempts),
        "h2b_phase_b_insufficient": h2b_count,
        "h2c_fallback_founders_created": len(fallback_created),
        "h2c_fallback_founders_absorbed_by_end": len(fallback_created) - fallback_survived,
        "h3_minority_boost_applied": len(minority_boosts),
        "h4_drift_recovery_to_minority": drift_recovery,
        "collapse_tick_snapshot": collapse_tick,
        "active_snapshots": snapshots,
        "h5_cross_faction_lord_emerged": len(cfl_emerged),
        "h5_cross_faction_lord_collapsed": len(cfl_collapsed),
        "h5a_faction_consolidated": int(cfl_reasons.get("faction_consolidated", 0)),
        "h5b_lord_id_replaced": int(cfl_reasons.get("lord_id_replaced", 0)),
        "h5c_lord_persona_missing": int(cfl_reasons.get("lord_persona_missing", 0)),
        "h5d_delayed_emerged_count": int(delayed_emerged),
        "h5d_delayed_emerged_ratio": (
            delayed_emerged / len(cfl_emerged) if cfl_emerged else 0.0
        ),
        "h5_duration_ticks": {
            "count": len(durations),
            "p50": _percentile(durations, 50),
            "p75": _percentile(durations, 75),
            "p90": _percentile(durations, 90),
            "max": max(durations) if durations else None,
        },
        "h5_final_cross_faction_lord_count": int(
            final_snapshot.get("cross_faction_lord_count", 0) or 0
        ),
    }


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
        grievance_raw = engine.faction_grievance_targets()
        _write_jsonl_line(
            handle,
            {
                "tick": tick,
                "type": "grievance_targets",
                "raw": grievance_raw,
                "shared_pairs": engine.shared_grievance_pairs_count(min_carriers=1),
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


def _dump_new_event_rows(handle, events: list[dict[str, Any]], start_index: int) -> int:
    """Dump probe-visible event rows appended since the previous tick."""
    for event in events[start_index:]:
        if event.get("type") == "uprising":
            _write_jsonl_line(handle, dict(event))
    return len(events)


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
    uprising_rows = [row for row in rows if row.get("type") == "uprising"]
    source_row = _last_row(rows, "source_cumulative")

    initial_population = population_rows[0]["data"] if population_rows else {}
    final_population = population_rows[-1]["data"] if population_rows else {}
    initial_active = len(_active_counts(initial_population))
    final_active = len(_active_counts(final_population))
    final_total = sum(int(count) for count in final_population.values())
    top_population = max((int(count) for count in final_population.values()), default=0)
    dom_share_end = top_population / final_total if final_total else 0.0
    total_events = sum(source_row["data"].values()) if source_row else 0
    final_contact_count = int(contact_rows[-1]["count"]) if contact_rows else 0
    final_shared_pairs = int(grievance_rows[-1]["shared_pairs"]) if grievance_rows else 0
    uprising_count = len(uprising_rows)
    branch_count = sum(1 for row in uprising_rows if bool(row.get("branch")))
    join_count = uprising_count - branch_count

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
    trend = "利앷?" if gini_end > gini_500 else "媛먯냼" if gini_end < gini_500 else "?뺤껜"

    summary_lines = [
        f"# Phase 17 Emergence Probe ??seed {seed}",
        "",
        "## ?ㅽ뻾 ?붿빟",
        f"- ?? {ticks}",
        f"- ?쒖옉 faction ?? {initial_active}",
        f"- 醫낅즺 faction ?? {final_active}",
        f"- 珥?faction_change ?대깽?? {total_events}",
        f"- 寃쎄낵: {elapsed:.1f}s ({elapsed / max(1, ticks) * 1000:.1f}ms/tick)",
        "",
        "## 遺꾪룷 吏꾪솕 (1000??媛꾧꺽 ?섑뵆)",
        "| tick | ?쒖꽦 faction ??| 理쒕? ?뚯냽 ?몄썝 | 洹좊벑??(H/Hmax) |",
        "|------|----------------|----------------|------------------|",
    ]
    for row in population_table:
        summary_lines.append(
            f"| {row['tick']} | {row['active']} | {row['largest']} | {row['evenness']:.2f} |"
        )

    summary_lines.extend(
        [
            "",
            "## 過-3 ?щ즺: ?묒큺 ??異붿씠",
            f"- tick 0: {int(contact_rows[0]['count']) if contact_rows else 0} pairs",
            f"- tick 1000: {int(next((row['count'] for row in contact_rows if int(row['tick']) == 1000), 0))} pairs",
            f"- tick {ticks}: {final_contact_count} pairs",
            f"- **?먯젙**: {'[PASS]' if pass_contact else '[FAIL]'} if ????at tick {ticks} else [FAIL]",
            "",
            "## Source 鍮꾩쑉 (?꾩쟻)",
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
            f"**?먯젙**: drift ??5% ??{'[PASS]' if pass_drift else '[FAIL]'}",
            "",
            "## Wealth gini 異붿씠",
            f"- tick 500: avg gini {gini_500:.2f}",
            f"- tick 2500: avg gini {gini_mid:.2f}",
            f"- tick {ticks}: avg gini {gini_end:.2f}",
            f"- **寃쏀뼢**: [{trend}]",
            "",
            "## Grievance 怨듭쑀 (遊됯린 ?щ즺)",
            f"- tick {ticks} 湲곗?: {final_shared_pairs} ?띿쓽 faction??媛숈? lord瑜?grievance ??곸쑝濡?怨듭쑀",
            f"- **?먯젙**: {'[PASS]' if final_shared_pairs >= 1 else '[N/A]'} if ????else [N/A]",
            "",
            "## 醫낇빀 ?먯젙",
            f"- {'[PASS]' if pass_diversified else '[FAIL]'} 遺꾪솕 諛쒖깮 (理쒖쥌 active faction ??> 珥덇린)",
            f"- {'[PASS]' if pass_contact else '[FAIL]'} ?묒큺 ????1 (過-3 吏꾩엯 媛??",
            f"- {'[PASS]' if pass_drift else '[FAIL]'} drift source ??5% (bottom-up ?щ같移??ㅼ젣 諛쒖깮)",
            f"- {'[PASS]' if pass_gini else '[FAIL]'} wealth gini 利앷? 寃쏀뼢 (怨꾧툒 ?щ즺 異뺤쟻)",
            "",
            "## ?댁긽 吏뺥썑 (?덉쓣 寃쎌슦)",
        ]
    )
    if final_active <= 0:
        summary_lines.append("- [WARN] no factions emerged")
    else:
        summary_lines.append("- ?놁쓬")

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
        "uprising_count": uprising_count,
        "dom_share_end": dom_share_end,
        "branch_factions_total": branch_count,
        "uprising_branch_share": branch_count / uprising_count if uprising_count else 0.0,
        "uprising_join_share": join_count / uprising_count if uprising_count else 0.0,
    }
    return "\n".join(summary_lines) + "\n", result


def run_seed(seed: int, ticks: int, out_root: Path) -> dict[str, Any]:
    engine = MultiTickEngine(seed=seed)
    out_dir = out_root / f"seed-{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "metrics.jsonl"
    summary_path = out_dir / "summary.md"
    chain_path = out_dir / "chain.json"
    case_c_path = out_dir / "case_c_events.json"

    with jsonl_path.open("w", encoding="utf-8") as handle:
        _dump_snapshot(handle, engine, tick=0)
        event_cursor = len(engine.event_log)
        started = time.time()
        for tick in range(1, ticks + 1):
            engine.tick()
            event_cursor = _dump_new_event_rows(handle, engine.event_log, event_cursor)
            _dump_snapshot(handle, engine, tick=tick)
        elapsed = time.time() - started

    summary_text, result = _build_seed_summary(seed, ticks, elapsed, jsonl_path)
    case_events = _case_c_events(engine.event_log)
    case_c_diagnosis = _case_c_diagnosis(engine.event_log)
    snn_output_events = _snn_output_events(engine.event_log)
    snn_output_diagnosis = _phase14b_d1_diagnosis(engine.event_log, engine)
    snn_output_path = out_dir / "snn_output_events.json"
    _write_json_file(chain_path, engine.event_log)
    _write_json_file(case_c_path, case_events)
    _write_json_file(snn_output_path, snn_output_events)
    summary_path.write_text(summary_text, encoding="utf-8")
    result["case_c_diagnosis"] = case_c_diagnosis
    result["snn_output_diagnosis"] = snn_output_diagnosis
    result["summary_path"] = str(summary_path)
    result["jsonl_path"] = str(jsonl_path)
    result["chain_path"] = str(chain_path)
    result["case_c_events_path"] = str(case_c_path)
    result["snn_output_events_path"] = str(snn_output_path)
    return result


def _write_top_summary(results: list[dict[str, Any]], out_root: Path) -> None:
    """Write the 過-3 primary acceptance summary, overriding the legacy summary writer."""

    def _seed_result(seed: int) -> dict[str, Any] | None:
        return next((result for result in results if result.get("seed") == seed), None)

    def _value(seed: int, key: str, default: Any = "ERR") -> Any:
        result = _seed_result(seed)
        if result is None or "error" in result:
            return default
        return result.get(key, default)

    def _diag(seed: int, key: str, default: Any = "ERR") -> Any:
        result = _seed_result(seed)
        if result is None or "error" in result:
            return default
        diagnosis = result.get("case_c_diagnosis", {})
        return diagnosis.get(key, default)

    valid_results = [result for result in results if "error" not in result]
    primary_uprising = (
        all(result.get("uprising_count", 0) >= 1 for result in valid_results)
        and len(valid_results) == len(results)
    )
    primary_grievance = (
        all(result.get("shared_pairs_end", 0) >= 1 for result in valid_results)
        and len(valid_results) == len(results)
    )
    primary_dom = (
        all(result.get("dom_share_end", 0.0) >= 0.50 for result in valid_results)
        and len(valid_results) == len(results)
    )

    lines = [
        "# Phase 17 過-3 Struggle ??probe SUMMARY",
        "",
        "> Charter: PHASE-17-STRUGGLE-CHARTER.md",
        "",
        "## Primary Acceptance (3醫?",
        "",
        "| # | 湲곗? | seed 7 | seed 13 | seed 42 | 寃곌낵 |",
        "|---|------|:------:|:-------:|:-------:|:----:|",
        (
            "| 1 | uprising_event ??1 | "
            + " | ".join(str(_value(seed, "uprising_count")) for seed in (7, 13, 42))
            + f" | {'PASS' if primary_uprising else 'FAIL'} |"
        ),
        (
            "| 2 | grievance_pairs_end ??1 | "
            + " | ".join(str(_value(seed, "shared_pairs_end")) for seed in (7, 13, 42))
            + f" | {'PASS' if primary_grievance else 'FAIL'} |"
        ),
        (
            "| 3 | dom_share_end ??0.50 | "
            + " | ".join(
                (
                    f"{float(_value(seed, 'dom_share_end', 0.0)):.0%}"
                    if _value(seed, "dom_share_end", "ERR") != "ERR"
                    else "ERR"
                )
                for seed in (7, 13, 42)
            )
            + f" | {'PASS' if primary_dom else 'FAIL'} |"
        ),
        "",
        "## Secondary Metrics (Stage 6 怨꾩듅)",
        "",
        "| seed | active_factions_end | contact_pairs_end | drift_ratio | gini_mean_end | verdict |",
        "|------|---------------------|-------------------|-------------|---------------|---------|",
    ]

    legacy_pass = True
    for result in results:
        if "error" in result:
            legacy_pass = False
            lines.append(
                f"| {result['seed']} | ERROR | ERROR | ERROR | ERROR | FAIL ({result['error']}) |"
            )
            continue
        lines.append(
            f"| {result['seed']} | {result['active_factions_end']} | {result['contact_pairs_end']} "
            f"| {result['drift_ratio'] * 100:.0f}% | {result['gini_mean_end']:.2f} | {result['verdict']} |"
        )
        legacy_pass = legacy_pass and result["verdict"] == "PASS"

    lines.extend(
        [
            "",
            "| ??ぉ | seed 7 | seed 13 | seed 42 |",
            "|------|:------:|:-------:|:-------:|",
            "| branch_factions_total | "
            + " | ".join(str(_value(seed, "branch_factions_total")) for seed in (7, 13, 42))
            + " |",
            "| uprising_branch_share | "
            + " | ".join(
                (
                    f"{float(_value(seed, 'uprising_branch_share', 0.0)):.0%}"
                    if _value(seed, "uprising_branch_share", "ERR") != "ERR"
                    else "ERR"
                )
                for seed in (7, 13, 42)
            )
            + " |",
            "| uprising_join_share | "
            + " | ".join(
                (
                    f"{float(_value(seed, 'uprising_join_share', 0.0)):.0%}"
                    if _value(seed, "uprising_join_share", "ERR") != "ERR"
                    else "ERR"
                )
                for seed in (7, 13, 42)
            )
            + " |",
            "",
            (
                "**3 seed ?꾩썝 PASS ??過-3 primary acceptance 異⑹”**"
                if primary_uprising and primary_grievance and primary_dom
                else "**異붽? 寃利??꾩슂: 過-3 primary acceptance 以?FAIL ??ぉ???덉뒿?덈떎.**"
            ),
            "",
            (
                "**Legacy emergence verdict???꾩썝 PASS**"
                if legacy_pass and results
                else "**Legacy emergence verdict???쇰? seed媛 FAIL ?먮뒗 ERROR?낅땲??**"
            ),
            "",
        ]
    )
    lines.extend(
        [
            "## Case C Diagnosis",
            "",
            "| hypothesis | seed 7 | seed 13 | seed 42 |",
            "|------------|:------:|:-------:|:-------:|",
            "| H1 uprising_skip_no_contact | "
            + " | ".join(str(_diag(seed, "h1_uprising_skip_no_contact")) for seed in (7, 13, 42))
            + " |",
            "| H2a phase_a_all_blocked / attempts | "
            + " | ".join(
                f"{_diag(seed, 'h2a_phase_a_all_blocked')}/{_diag(seed, 'h2a_fallback_attempts')}"
                for seed in (7, 13, 42)
            )
            + " |",
            "| H2b phase_b_insufficient | "
            + " | ".join(str(_diag(seed, "h2b_phase_b_insufficient")) for seed in (7, 13, 42))
            + " |",
            "| H2c fallback_created / absorbed_by_end | "
            + " | ".join(
                f"{_diag(seed, 'h2c_fallback_founders_created')}/{_diag(seed, 'h2c_fallback_founders_absorbed_by_end')}"
                for seed in (7, 13, 42)
            )
            + " |",
            "| H3 minority_boost_applied | "
            + " | ".join(str(_diag(seed, "h3_minority_boost_applied")) for seed in (7, 13, 42))
            + " |",
            "| H4 drift_recovery_to_minority | "
            + " | ".join(str(_diag(seed, "h4_drift_recovery_to_minority")) for seed in (7, 13, 42))
            + " |",
            "| H5 emerged / collapsed | "
            + " | ".join(
                f"{_diag(seed, 'h5_cross_faction_lord_emerged')}/{_diag(seed, 'h5_cross_faction_lord_collapsed')}"
                for seed in (7, 13, 42)
            )
            + " |",
            "| H5a faction_consolidated | "
            + " | ".join(str(_diag(seed, "h5a_faction_consolidated")) for seed in (7, 13, 42))
            + " |",
            "| H5b lord_id_replaced | "
            + " | ".join(str(_diag(seed, "h5b_lord_id_replaced")) for seed in (7, 13, 42))
            + " |",
            "| H5c lord_persona_missing | "
            + " | ".join(str(_diag(seed, "h5c_lord_persona_missing")) for seed in (7, 13, 42))
            + " |",
            "| H5d delayed_emerged_count / ratio | "
            + " | ".join(
                f"{_diag(seed, 'h5d_delayed_emerged_count')}/{float(_diag(seed, 'h5d_delayed_emerged_ratio', 0.0)):.2f}"
                for seed in (7, 13, 42)
            )
            + " |",
            "| H5 final_cross_faction_lord_count | "
            + " | ".join(str(_diag(seed, "h5_final_cross_faction_lord_count")) for seed in (7, 13, 42))
            + " |",
            "| collapse_tick_snapshot | "
            + " | ".join(str(_diag(seed, "collapse_tick_snapshot")) for seed in (7, 13, 42))
            + " |",
            "",
            "### Active Factions Trace",
            "",
        ]
    )
    for seed in (7, 13, 42):
        snapshots = _diag(seed, "active_snapshots", [])
        compact = ", ".join(
            f"{event.get('tick')}:{event.get('active_count')}/cfl={event.get('cross_faction_lord_count', 0)}"
            for event in snapshots
        )
        lines.append(f"- seed {seed}: {compact if compact else 'ERR'}")
    lines.append("")
    def _snn_diag(seed: int) -> dict[str, Any]:
        result = _seed_result(seed)
        if result is None or "error" in result:
            return {}
        return result.get("snn_output_diagnosis", {}) or {}

    def _verdict_cell(seed: int, key: str) -> str:
        diag = _snn_diag(seed)
        sub = diag.get(key, {}) or {}
        return str(sub.get("verdict", "ERR"))

    def _fmt_num(v: Any, fmt: str = "{:.3f}") -> str:
        if v is None:
            return "n/a"
        try:
            return fmt.format(float(v))
        except (TypeError, ValueError):
            return str(v)

    seeds_for_summary = (7, 13, 42)

    lines.extend(
        [
            "## Phase 14B SNN Output Diagnosis (per seed)",
            "",
            "?곗씠???뺣떦???ъ뒳: telemetry 4醫??먯뿰 痢≪젙 ??4 媛??PASS/FAIL/INSUFFICIENT_N ??寃고빀???꾨낫 ?앸퀎.",
            "",
            "### Verdict Matrix (G1~G4)",
            "",
            "| hypothesis | seed 7 | seed 13 | seed 42 |",
            "|-----------|:------:|:-------:|:-------:|",
            "| G1 uprising leader gate diff | "
            + " | ".join(_verdict_cell(s, "g1_uprising_leader_gate_diff") for s in seeds_for_summary)
            + " |",
            "| G2 founder vs absorbing chronic | "
            + " | ".join(_verdict_cell(s, "g2_founder_vs_absorbing") for s in seeds_for_summary)
            + " |",
            "| G3 small faction persist diff | "
            + " | ".join(_verdict_cell(s, "g3_small_faction_persistence") for s in seeds_for_summary)
            + " |",
            "| G4 territory dist CV | "
            + " | ".join(_verdict_cell(s, "g4_territory_distribution_cv") for s in seeds_for_summary)
            + " |",
            "",
            "### G1 Detail (uprising leader gate)",
            "",
            "| seed | n_pass | n_fail | diff_sum | pass_avg_anger | fail_avg_anger | pass_avg_chronic | fail_avg_chronic |",
            "|:----:|:------:|:------:|:--------:|:--------------:|:--------------:|:----------------:|:----------------:|",
        ]
    )
    for s in seeds_for_summary:
        diag = _snn_diag(s).get("g1_uprising_leader_gate_diff", {}) or {}
        pass_stats = diag.get("pass_stats", {}) or {}
        fail_stats = diag.get("fail_stats", {}) or {}
        lines.append(
            f"| {s} | {diag.get('n_pass', 'ERR')} | {diag.get('n_fail', 'ERR')} | "
            f"{_fmt_num(diag.get('diff_sum'))} | "
            f"{_fmt_num((pass_stats.get('anger') or {}).get('avg'))} | "
            f"{_fmt_num((fail_stats.get('anger') or {}).get('avg'))} | "
            f"{_fmt_num((pass_stats.get('chronic') or {}).get('avg'))} | "
            f"{_fmt_num((fail_stats.get('chronic') or {}).get('avg'))} |"
        )
    lines.append("")

    lines.extend(
        [
            "### G2 Detail (founder vs absorbing chronic)",
            "",
            "| seed | n | avg_diff_chronic | avg_founder_chronic | avg_absorbing_chronic |",
            "|:----:|:-:|:----------------:|:-------------------:|:---------------------:|",
        ]
    )
    for s in seeds_for_summary:
        diag = _snn_diag(s).get("g2_founder_vs_absorbing", {}) or {}
        stats = diag.get("stats", {}) or {}
        diff_chronic = (stats.get("diff_chronic") or {}).get("avg")
        founder_chronic = (stats.get("founder_chronic") or {}).get("avg")
        absorbing_chronic = (stats.get("absorbing_avg_chronic") or {}).get("avg")
        lines.append(
            f"| {s} | {diag.get('n', 'ERR')} | "
            f"{_fmt_num(diff_chronic)} | {_fmt_num(founder_chronic)} | {_fmt_num(absorbing_chronic)} |"
        )
    lines.append("")

    lines.extend(
        [
            "### G3 Detail (small faction persist vs expired)",
            "",
            "| seed | n_persisted | n_expired | diff_sum | persisted_avg_chronic | expired_avg_chronic |",
            "|:----:|:-----------:|:---------:|:--------:|:---------------------:|:-------------------:|",
        ]
    )
    for s in seeds_for_summary:
        diag = _snn_diag(s).get("g3_small_faction_persistence", {}) or {}
        ps = diag.get("persisted_stats", {}) or {}
        es = diag.get("expired_stats", {}) or {}
        lines.append(
            f"| {s} | {diag.get('n_persisted', 'ERR')} | {diag.get('n_expired', 'ERR')} | "
            f"{_fmt_num(diag.get('diff_sum'))} | "
            f"{_fmt_num((ps.get('chronic') or {}).get('avg'))} | "
            f"{_fmt_num((es.get('chronic') or {}).get('avg'))} |"
        )
    lines.append("")

    lines.extend(
        [
            "### G4 Detail (territory CV chronic)",
            "",
            "| seed | n_territories | avg_cv_chronic |",
            "|:----:|:-------------:|:--------------:|",
        ]
    )
    for s in seeds_for_summary:
        diag = _snn_diag(s).get("g4_territory_distribution_cv", {}) or {}
        lines.append(
            f"| {s} | {diag.get('n_territories', 'ERR')} | "
            f"{_fmt_num(diag.get('avg_cv_chronic'))} |"
        )
    lines.append("")

    lines.extend(
        [
            "### Telemetry Event Counts (per seed)",
            "",
            "| event_type | seed 7 | seed 13 | seed 42 |",
            "|-----------|:------:|:-------:|:-------:|",
        ]
    )
    for ev_type in (
        "uprising_leader_snn_snapshot",
        "founder_absorbed_snn_snapshot",
        "small_faction_snn_snapshot",
        "territory_snn_distribution",
    ):
        cells = []
        for s in seeds_for_summary:
            diag = _snn_diag(s)
            counts = diag.get("telemetry_event_counts", {}) or {}
            cells.append(str(counts.get(ev_type, "ERR")))
        lines.append(f"| {ev_type} | " + " | ".join(cells) + " |")
    lines.append("")

    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = _parse_args()
    seeds = list(QUICK_SEEDS if args.quick else _parse_seed_arg(args.seeds))
    ticks = QUICK_TICKS if args.quick else int(args.ticks)
    default_out = f"data/phase17_probe_{args.label}" if args.label else "data/phase17_probe"
    out_root = Path(args.out or default_out)
    if not out_root.is_absolute():
        out_root = (Path.cwd() / out_root).resolve()

    out_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for seed in seeds:
        print(f"[run] seed={seed} ticks={ticks}", flush=True)
        try:
            result = run_seed(seed, ticks, out_root)
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

    _write_top_summary(results, out_root)
    median, _p95, _samples = _measure_tick_ms_stable(seed=42)
    kernel = _measure_faction_kernel_ms(seed=42)
    print(_format_observe_perf_line(median, kernel["total"]), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
