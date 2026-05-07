"""Regenerate Phase 17 V3 diagnosis summaries from raw probe artifacts.

This script repairs Markdown mojibake only. It preserves the raw JSON/JSONL
artifacts byte-for-byte and creates one byte-for-byte backup for each original
mojibake summary before overwriting the human-readable Markdown.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "phase17_probe_phi3-case-c-diagnosis-v3"
SEEDS = (7, 13, 42)
SUMMARY_TARGETS = (
    SOURCE / "SUMMARY.md",
    SOURCE / "seed-7" / "summary.md",
    SOURCE / "seed-13" / "summary.md",
    SOURCE / "seed-42" / "summary.md",
)
EXPECTED_BACKUP_HASHES = {
    "SUMMARY.mojibake.bak.md": (
        "f1dd2e99854be5e34adee42bc3d7c13b9a0aaf20ce9fe199c0c7481365f40b99"
    ),
    "seed-7/summary.mojibake.bak.md": (
        "acc69017167177f3dd863bf1970af4b3e39da414da6fa3f7a74e3c4c21e203a1"
    ),
    "seed-13/summary.mojibake.bak.md": (
        "be440ef6c26a62983bc255d31a11cfd68302192288ee5803f8bfc7d85d714f9e"
    ),
    "seed-42/summary.mojibake.bak.md": (
        "e39603f16854876298f721fd21a9764e49fbf0c3e9050672c5dfb8bdf19c0cbf"
    ),
}
EXPECTED_TOKENS = (
    "Φ-3",
    "실행 요약",
    "시작 faction 수",
    "활성 faction 수",
    "분위수",
    "검증",
    "결과",
    "기준",
    "균등도",
    "최대 소속 인원",
    "Source 비율",
    "종합 판정",
)
QUANTILE_NOTE = (
    "주의: 본 V3 SUMMARY는 분위수 산출물이 아니며, "
    "DC-1/DC-2 분위수 산출물의 입력 raw 상태를 설명한다."
)
CJK_RE = re.compile(r"[\u4e00-\u9fff\uf900-\ufaff]")
QMARK_HANGUL_RE = re.compile(r"\?[\uac00-\ud7af]")
ELAPSED_RE = re.compile(r"(\d+(?:\.\d+)?)s\s*\((\d+(?:\.\d+)?)ms/tick\)")


@dataclass(frozen=True)
class SeedReport:
    seed: int
    elapsed: str
    elapsed_note: str
    ticks: int
    start_active: int
    end_active: int
    total_changes: int
    population_rows: list[tuple[int, int, int, float]]
    source_counts: dict[str, int]
    source_pcts: dict[str, float]
    wealth_gini: dict[int, float]
    grievance_pairs: dict[int, int]
    uprising_count: int
    branch_count: int
    join_count: int
    dom_share: float
    final_gini: float
    contact_pairs_end: int
    active_trace: list[tuple[int, int, int]]
    diagnosis_counts: dict[str, int]
    fallback_absorbed: int
    snn_counts: dict[str, int]
    verdict: str


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def backup_path_for(path: Path) -> Path:
    return path.with_suffix(".mojibake.bak.md")


def backup_mojibake_if_first_run(path: Path) -> None:
    backup = backup_path_for(path)
    backup_key = backup.relative_to(SOURCE).as_posix()
    expected_digest = EXPECTED_BACKUP_HASHES[backup_key]
    if not backup.exists():
        current_digest = sha256(path)
        if current_digest != expected_digest:
            raise RuntimeError(
                f"missing backup and current summary is not original mojibake: {path}"
            )
        backup.write_bytes(path.read_bytes())
    actual_digest = sha256(backup)
    if actual_digest != expected_digest:
        raise RuntimeError(
            f"backup provenance mismatch for {backup}: "
            f"{actual_digest} != {expected_digest}"
        )


def extract_elapsed_from_current_summary(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = ELAPSED_RE.search(text)
    if match is None:
        return "N/A", "raw 미존재"
    elapsed = f"{match.group(1)}s ({match.group(2)}ms/tick)"
    return elapsed, "원본 숫자 보존, raw 미존재"


def active_values(data: dict[str, int]) -> list[int]:
    return [count for count in data.values() if count > 0]


def evenness(values: list[int]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return 1.0
    total = sum(values)
    if total <= 0:
        return 0.0
    probs = [value / total for value in values if value > 0]
    entropy = -sum(prob * math.log(prob) for prob in probs)
    return entropy / math.log(len(probs))


def avg_active_gini(record: dict[str, Any]) -> float:
    values = [
        faction["gini"]
        for faction in record["data"].values()
        if float(faction.get("total", 0.0)) > 0.0
    ]
    return sum(values) / len(values) if values else 0.0


def find_metric(records: list[dict[str, Any]], metric_type: str, tick: int) -> dict[str, Any]:
    for record in records:
        if record["type"] == metric_type and record["tick"] == tick:
            return record
    raise KeyError(f"missing metric type={metric_type!r} tick={tick}")


def collect_seed(seed: int) -> SeedReport:
    seed_dir = SOURCE / f"seed-{seed}"
    elapsed, elapsed_note = extract_elapsed_from_current_summary(seed_dir / "summary.md")
    events = load_json(seed_dir / "case_c_events.json")
    snn_events = load_json(seed_dir / "snn_output_events.json")
    metrics = load_jsonl(seed_dir / "metrics.jsonl")

    event_counts = Counter(event["type"] for event in events)
    snn_counts = Counter(event["type"] for event in snn_events)
    snapshots = [event for event in events if event["type"] == "active_factions_snapshot"]
    snapshots.sort(key=lambda item: item["tick"])

    population_rows: list[tuple[int, int, int, float]] = []
    for tick in range(0, 20001, 1000):
        record = find_metric(metrics, "population", tick)
        values = active_values(record["data"])
        population_rows.append(
            (tick, len(values), max(values) if values else 0, evenness(values))
        )

    source_record = [m for m in metrics if m["type"] == "source_cumulative"][-1]
    source_counts = {key: int(value) for key, value in source_record["data"].items()}
    total_changes = sum(source_counts.values())
    source_pcts = {
        key: (value / total_changes * 100.0 if total_changes else 0.0)
        for key, value in source_counts.items()
    }

    wealth_gini = {
        tick: avg_active_gini(find_metric(metrics, "wealth", tick))
        for tick in (500, 2500, 20000)
    }

    grievance_pairs = {
        tick: int(find_metric(metrics, "grievance_targets", tick)["shared_pairs"])
        for tick in (0, 1000, 20000)
    }

    uprising_records = [m for m in metrics if m["type"] == "uprising"]
    branch_count = sum(1 for record in uprising_records if record.get("branch"))
    join_count = len(uprising_records) - branch_count

    final_snapshot = snapshots[-1]
    final_sizes = [int(value) for value in final_snapshot["faction_sizes"].values() if value > 0]
    dom_share = max(final_sizes) / sum(final_sizes) if final_sizes else 0.0
    contact_pairs_end = grievance_pairs[20000]
    drift_ratio = source_pcts.get("drift", 0.0)
    verdict = (
        "PASS"
        if final_snapshot["active_count"] >= snapshots[0]["active_count"]
        and contact_pairs_end >= 1
        and drift_ratio >= 5.0
        and wealth_gini[20000] >= 0.3
        else "FAIL"
    )

    fallback_created = event_counts["respawn_fallback_founder_created"]
    fallback_absorbed = max(0, fallback_created - final_snapshot["active_count"])

    return SeedReport(
        seed=seed,
        elapsed=elapsed,
        elapsed_note=elapsed_note,
        ticks=20000,
        start_active=snapshots[0]["active_count"],
        end_active=final_snapshot["active_count"],
        total_changes=total_changes,
        population_rows=population_rows,
        source_counts=source_counts,
        source_pcts=source_pcts,
        wealth_gini=wealth_gini,
        grievance_pairs=grievance_pairs,
        uprising_count=len(uprising_records),
        branch_count=branch_count,
        join_count=join_count,
        dom_share=dom_share,
        final_gini=wealth_gini[20000],
        contact_pairs_end=contact_pairs_end,
        active_trace=[
            (
                int(snapshot["tick"]),
                int(snapshot["active_count"]),
                int(snapshot.get("cross_faction_lord_count", 0)),
            )
            for snapshot in snapshots
        ],
        diagnosis_counts={
            "uprising_skip_no_contact": event_counts["uprising_skip_no_contact"],
            "uprising_skip_snn_inactive": event_counts["uprising_skip_snn_inactive"],
            "respawn_fallback_attempt": event_counts["respawn_fallback_attempt"],
            "respawn_fallback_created": fallback_created,
            "respawn_skip_reason": event_counts["respawn_skip_reason"],
            "minority_boost_applied": event_counts["minority_boost_applied"],
            "drift_recovery_to_minority": event_counts["drift_recovery_to_minority"],
            "cross_faction_lord_pair_emerged": event_counts[
                "cross_faction_lord_pair_emerged"
            ],
            "cross_faction_lord_pair_collapsed": event_counts[
                "cross_faction_lord_pair_collapsed"
            ],
        },
        fallback_absorbed=fallback_absorbed,
        snn_counts=dict(snn_counts),
        verdict=verdict,
    )


def fmt_pct(value: float) -> str:
    return f"{value:.0f}%"


def fmt_float(value: float) -> str:
    return f"{value:.2f}"


def pass_label(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def render_source_table(report: SeedReport) -> list[str]:
    lines = [
        "| source | count | pct |",
        "|--------|------:|----:|",
    ]
    for key in ("birth_founder", "affiliation", "drift", "conflict"):
        lines.append(
            f"| {key} | {report.source_counts.get(key, 0)} | "
            f"{fmt_pct(report.source_pcts.get(key, 0.0))} |"
        )
    return lines


def render_seed_summary(report: SeedReport) -> str:
    lines: list[str] = [
        f"# Phase 17 Φ-3 Emergence Probe - seed {report.seed}",
        "",
        "## 실행 요약",
        f"- tick: {report.ticks}",
        f"- 시작 faction 수: {report.start_active}",
        f"- 활성 faction 수: {report.end_active}",
        f"- 총 faction_change 수: {report.total_changes}",
        f"- 경과: {report.elapsed} ({report.elapsed_note})",
        "",
        "## 분포 진화 (1000틱 간격)",
        "| tick | 활성 faction 수 | 최대 소속 인원 | 균등도 (H/Hmax) |",
        "|-----:|---------------:|--------------:|----------------:|",
    ]
    for tick, active, max_members, entropy in report.population_rows:
        lines.append(f"| {tick} | {active} | {max_members} | {entropy:.2f} |")

    lines.extend(
        [
            "",
            "## Φ-3 grievance 공유 진단",
            f"- tick 0: {report.grievance_pairs[0]} pairs",
            f"- tick 1000: {report.grievance_pairs[1000]} pairs",
            f"- tick 20000: {report.grievance_pairs[20000]} pairs",
            "- 기준: tick 20000에서 1 이상이면 PASS",
            f"- 결과: {'PASS' if report.grievance_pairs[20000] >= 1 else 'FAIL'}",
            "",
            "## Source 비율 (누적)",
        ]
    )
    lines.extend(render_source_table(report))
    lines.extend(
        [
            "",
            "- 기준: drift source 5% 이상이면 PASS",
            f"- 결과: {'PASS' if report.source_pcts.get('drift', 0.0) >= 5.0 else 'FAIL'}",
            "",
            "## Wealth gini 추이",
        ]
    )
    for tick in (500, 2500, 20000):
        lines.append(f"- tick {tick}: avg gini {report.wealth_gini[tick]:.2f}")
    lines.extend(
        [
            "- 기준: gini가 남아 있으면 불평등 신호 보존",
            f"- 결과: {'PASS' if report.wealth_gini[20000] >= 0.3 else 'FAIL'}",
            "",
            "## Case C Diagnosis",
            f"- H1 uprising_skip_no_contact: "
            f"{report.diagnosis_counts['uprising_skip_no_contact']}",
            f"- H2a fallback attempts/created: "
            f"{report.diagnosis_counts['respawn_fallback_attempt']}/"
            f"{report.diagnosis_counts['respawn_fallback_created']}",
            f"- H2b respawn_skip_reason: "
            f"{report.diagnosis_counts['respawn_skip_reason']}",
            f"- H2c fallback absorbed by end: {report.fallback_absorbed}",
            f"- H3 minority_boost_applied: "
            f"{report.diagnosis_counts['minority_boost_applied']}",
            f"- H4 drift_recovery_to_minority: "
            f"{report.diagnosis_counts['drift_recovery_to_minority']}",
            f"- H5 cross_faction_lord_pair_emerged/collapsed: "
            f"{report.diagnosis_counts['cross_faction_lord_pair_emerged']}/"
            f"{report.diagnosis_counts['cross_faction_lord_pair_collapsed']}",
            "",
            "## Phase 14B SNN Output Diagnosis",
            "| event_type | count |",
            "|------------|------:|",
        ]
    )
    for key in (
        "uprising_leader_snn_snapshot",
        "founder_absorbed_snn_snapshot",
        "small_faction_snn_snapshot",
        "territory_snn_distribution",
    ):
        lines.append(f"| {key} | {report.snn_counts.get(key, 0)} |")

    lines.extend(
        [
            "",
            "## 종합 판정",
            f"- {'PASS' if report.end_active >= report.start_active else 'FAIL'} "
            "활성 faction 수 >= 시작 faction 수",
            f"- {'PASS' if report.contact_pairs_end >= 1 else 'FAIL'} contact pair >= 1",
            f"- {'PASS' if report.source_pcts.get('drift', 0.0) >= 5.0 else 'FAIL'} "
            "drift source >= 5%",
            f"- {'PASS' if report.wealth_gini[20000] >= 0.3 else 'FAIL'} "
            "wealth gini signal",
            f"- 결과: {report.verdict}",
            "",
            "## Active Factions Trace",
        ]
    )
    trace = ", ".join(
        f"{tick}:{active}/cfl={cfl}" for tick, active, cfl in report.active_trace
    )
    lines.extend(
        [
            f"- seed {report.seed}: {trace}",
            "",
            "## 검증",
            "- 기준: raw 4 카테고리에서 재계산 가능한 값만 본문 수치로 사용했다.",
            "- 주의: 이 seed SUMMARY는 분위수 산출물이 아니다.",
            "- 결과: raw 미존재 항목은 원본 숫자 보존 또는 N/A로만 처리했다.",
            "",
            "## 주의",
            "- 이 문서는 raw JSON/JSONL에서 Markdown만 재합성한 인프라 산출물이다.",
            "- mechanism, acceptance, charter, DC-1, DC-2 산출물은 변경하지 않았다.",
            "",
        ]
    )
    return "\n".join(lines)


def render_top_summary(reports: list[SeedReport]) -> str:
    primary_1_pass = all(report.uprising_count >= 1 for report in reports)
    primary_2_pass = all(report.contact_pairs_end >= 1 for report in reports)
    primary_3_pass = all(report.dom_share >= 0.50 for report in reports)
    primary_all_pass = primary_1_pass and primary_2_pass and primary_3_pass
    lines = [
        "# Phase 17 Φ-3 Struggle Probe SUMMARY",
        "",
        "> Charter: PHASE-17-STRUGGLE-CHARTER.md",
        "",
        "## 주의",
        QUANTILE_NOTE,
        "",
        "## 실행 요약",
        "| seed | 시작 faction 수 | 활성 faction 수 | 경과 | 결과 |",
        "|-----:|---------------:|---------------:|------|------|",
    ]
    for report in reports:
        lines.append(
            f"| {report.seed} | {report.start_active} | {report.end_active} | "
            f"{report.elapsed} ({report.elapsed_note}) | {report.verdict} |"
        )

    lines.extend(
        [
            "",
            "## 분포 요약",
            "| seed | tick | 활성 faction 수 | 최대 소속 인원 | 균등도 (H/Hmax) |",
            "|-----:|-----:|---------------:|--------------:|----------------:|",
        ]
    )
    for report in reports:
        tick, active, max_members, entropy = report.population_rows[-1]
        lines.append(
            f"| {report.seed} | {tick} | {active} | {max_members} | {entropy:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Primary Acceptance (3 seeds)",
            "| # | 기준 | seed 7 | seed 13 | seed 42 | 결과 |",
            "|---|------|:------:|:-------:|:-------:|:----:|",
            "| 1 | uprising_event >= 1 | "
            + " | ".join(str(r.uprising_count) for r in reports)
            + f" | {pass_label(primary_1_pass)} |",
            "| 2 | grievance_pairs_end >= 1 | "
            + " | ".join(str(r.contact_pairs_end) for r in reports)
            + f" | {pass_label(primary_2_pass)} |",
            "| 3 | dom_share_end >= 0.50 | "
            + " | ".join(fmt_pct(r.dom_share * 100.0) for r in reports)
            + f" | {pass_label(primary_3_pass)} |",
            "",
            "## Secondary Metrics",
            "| seed | active_factions_end | contact_pairs_end | drift_ratio | "
            "gini_mean_end | verdict |",
            "|-----:|--------------------:|------------------:|------------:|--------------:|---------|",
        ]
    )
    for report in reports:
        lines.append(
            f"| {report.seed} | {report.end_active} | {report.contact_pairs_end} | "
            f"{fmt_pct(report.source_pcts.get('drift', 0.0))} | "
            f"{report.final_gini:.2f} | {report.verdict} |"
        )

    lines.extend(
        [
            "",
            "## 종합 판정",
            f"- 결과: 3 seed Primary Acceptance 3종은 {pass_label(primary_all_pass)}이다.",
            "- 결과: legacy emergence verdict는 gini 기준 때문에 seed별 FAIL이 남아 있다.",
            "",
            "| branch metric | seed 7 | seed 13 | seed 42 |",
            "|---------------|:------:|:-------:|:-------:|",
            "| branch_factions_total | "
            + " | ".join(str(r.branch_count) for r in reports)
            + " |",
            "| uprising_branch_share | "
            + " | ".join(
                fmt_pct(r.branch_count / r.uprising_count * 100.0)
                if r.uprising_count
                else "0%"
                for r in reports
            )
            + " |",
            "| uprising_join_share | "
            + " | ".join(
                fmt_pct(r.join_count / r.uprising_count * 100.0)
                if r.uprising_count
                else "0%"
                for r in reports
            )
            + " |",
            "",
            "## Source 비율 (누적)",
            "| seed | birth_founder | affiliation | drift | conflict |",
            "|-----:|--------------:|------------:|------:|---------:|",
        ]
    )
    for report in reports:
        lines.append(
            f"| {report.seed} | "
            f"{report.source_counts.get('birth_founder', 0)} "
            f"({fmt_pct(report.source_pcts.get('birth_founder', 0.0))}) | "
            f"{report.source_counts.get('affiliation', 0)} "
            f"({fmt_pct(report.source_pcts.get('affiliation', 0.0))}) | "
            f"{report.source_counts.get('drift', 0)} "
            f"({fmt_pct(report.source_pcts.get('drift', 0.0))}) | "
            f"{report.source_counts.get('conflict', 0)} "
            f"({fmt_pct(report.source_pcts.get('conflict', 0.0))}) |"
        )

    lines.extend(
        [
            "",
            "## Case C Diagnosis",
            "| hypothesis | seed 7 | seed 13 | seed 42 |",
            "|------------|:------:|:-------:|:-------:|",
        ]
    )
    diagnosis_rows = [
        ("H1 uprising_skip_no_contact", "uprising_skip_no_contact"),
        ("H2a respawn_fallback_attempt", "respawn_fallback_attempt"),
        ("H2b respawn_skip_reason", "respawn_skip_reason"),
        ("H2c fallback_created", "respawn_fallback_created"),
        ("H3 minority_boost_applied", "minority_boost_applied"),
        ("H4 drift_recovery_to_minority", "drift_recovery_to_minority"),
        ("H5 emerged", "cross_faction_lord_pair_emerged"),
        ("H5 collapsed", "cross_faction_lord_pair_collapsed"),
    ]
    for label, key in diagnosis_rows:
        lines.append(
            f"| {label} | "
            + " | ".join(str(r.diagnosis_counts[key]) for r in reports)
            + " |"
        )
    lines.append(
        "| H5 final_cross_faction_lord_count | "
        + " | ".join(str(r.active_trace[-1][2]) for r in reports)
        + " |"
    )

    lines.extend(
        [
            "",
            "## Active Factions Trace",
        ]
    )
    for report in reports:
        trace = ", ".join(
            f"{tick}:{active}/cfl={cfl}" for tick, active, cfl in report.active_trace
        )
        lines.append(f"- seed {report.seed}: {trace}")

    lines.extend(
        [
            "",
            "## Phase 14B SNN Output Diagnosis",
            "| event_type | seed 7 | seed 13 | seed 42 |",
            "|------------|:------:|:-------:|:-------:|",
        ]
    )
    for key in (
        "uprising_leader_snn_snapshot",
        "founder_absorbed_snn_snapshot",
        "small_faction_snn_snapshot",
        "territory_snn_distribution",
    ):
        lines.append(
            f"| {key} | "
            + " | ".join(str(report.snn_counts.get(key, 0)) for report in reports)
            + " |"
        )

    lines.extend(
        [
            "",
            "## 검증",
            "- 기준: raw 4 카테고리에서 재계산 가능한 값만 본문 수치로 사용했다.",
            "- 기준: wall-clock 경과 시간은 raw 미존재 항목이라 원본 숫자만 보존했다.",
            "- 결과: SUMMARY 4개를 UTF-8 Markdown으로 재합성했다.",
            "",
        ]
    )
    return "\n".join(lines)


def verify_tokens(path: Path) -> None:
    verify_tokens_in_text(path.read_text(encoding="utf-8"), path)


def verify_tokens_in_text(text: str, label: object) -> None:
    for token in EXPECTED_TOKENS:
        if token not in text:
            raise AssertionError(f"token missing: {token!r} in {label}")


def verify_mojibake_clean(path: Path) -> None:
    verify_mojibake_clean_text(path.read_text(encoding="utf-8"), path)


def verify_mojibake_clean_text(text: str, label: object) -> None:
    cjk_hits = sorted(set(CJK_RE.findall(text)))
    qmark_hangul_hits = sorted(set(QMARK_HANGUL_RE.findall(text)))
    if cjk_hits:
        raise AssertionError(f"residual CJK ideograph in {label}: {cjk_hits}")
    if qmark_hangul_hits:
        raise AssertionError(
            f"residual '?+Hangul' mojibake in {label}: {qmark_hangul_hits[:5]}"
        )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text_atomic(path: Path, text: str) -> None:
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    temp.replace(path)


def main() -> None:
    raw_hashes_before = {
        path: sha256(path)
        for seed in SEEDS
        for path in (
            SOURCE / f"seed-{seed}" / "case_c_events.json",
            SOURCE / f"seed-{seed}" / "chain.json",
            SOURCE / f"seed-{seed}" / "snn_output_events.json",
            SOURCE / f"seed-{seed}" / "metrics.jsonl",
        )
    }

    elapsed_inputs = {
        seed: extract_elapsed_from_current_summary(
            SOURCE / f"seed-{seed}" / "summary.md"
        )
        for seed in SEEDS
    }
    for target in SUMMARY_TARGETS:
        backup_mojibake_if_first_run(target)

    reports = []
    for seed in SEEDS:
        report = collect_seed(seed)
        elapsed, elapsed_note = elapsed_inputs[seed]
        reports.append(
            SeedReport(
                **{
                    **report.__dict__,
                    "elapsed": elapsed,
                    "elapsed_note": elapsed_note,
                }
            )
        )

    outputs = {SOURCE / "SUMMARY.md": render_top_summary(reports)}
    for report in reports:
        outputs[SOURCE / f"seed-{report.seed}" / "summary.md"] = render_seed_summary(
            report
        )

    for path, text in outputs.items():
        verify_tokens_in_text(text, path)
        verify_mojibake_clean_text(text, path)
    if QUANTILE_NOTE not in outputs[SOURCE / "SUMMARY.md"]:
        raise AssertionError("quantile note missing in top SUMMARY.md")

    for path, text in outputs.items():
        write_text_atomic(path, text)

    raw_hashes_after = {path: sha256(path) for path in raw_hashes_before}
    if raw_hashes_before != raw_hashes_after:
        raise AssertionError("raw byte hash changed")

    for target in SUMMARY_TARGETS:
        verify_tokens(target)
        verify_mojibake_clean(target)

    top_text = (SOURCE / "SUMMARY.md").read_text(encoding="utf-8")
    if QUANTILE_NOTE not in top_text:
        raise AssertionError("quantile note missing in top SUMMARY.md")

    print("regenerated 4 SUMMARY files")
    print("created/preserved 4 .mojibake.bak.md files")
    print("raw byte hash unchanged")
    print("token and mojibake checks passed")


if __name__ == "__main__":
    main()
