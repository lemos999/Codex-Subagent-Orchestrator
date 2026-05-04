"""Phase 14B-B PROBE — anger quantile + threshold simulation.

§3.7 4단 (임계 분위수) + 5단 (cross-check 입력) 산출.
mechanism 무수정 — 텔레메트리 후처리만.
"""
from __future__ import annotations
import json
import statistics
from collections import defaultdict
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "phase17_probe_phi3-snn-output-diag"
OUTPUT_QUANTILES = DATA_ROOT.parent / "phase14b_b_anger_quantiles.json"
OUTPUT_SIMULATION = DATA_ROOT.parent / "phase14b_b_threshold_simulation.md"
SEEDS = [7, 13, 42]


def load_uprising_events(seed: int) -> list[dict]:
    path = DATA_ROOT / f"seed-{seed}" / "snn_output_events.json"
    with path.open("r", encoding="utf-8") as f:
        events = json.load(f)
    return [e for e in events if e.get("type") == "uprising_leader_snn_snapshot"]


def quantiles(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    sorted_v = sorted(values)
    n = len(sorted_v)

    def q(p: float) -> float:
        idx = max(0, min(n - 1, int(round(p * (n - 1)))))
        return sorted_v[idx]

    return {
        "n": n,
        "min": sorted_v[0],
        "p25": q(0.25),
        "p50": q(0.50),
        "p67": q(0.67),
        "p75": q(0.75),
        "p80": q(0.80),
        "p90": q(0.90),
        "max": sorted_v[-1],
        "mean": statistics.mean(sorted_v),
        "median": statistics.median(sorted_v),
        "stdev": statistics.stdev(sorted_v) if n > 1 else 0.0,
    }


def analyze_seed(seed: int) -> dict:
    events = load_uprising_events(seed)
    pass_anger = [e["leader_anger"] for e in events if e.get("gate_passed")]
    fail_anger = [e["leader_anger"] for e in events if not e.get("gate_passed")]
    all_anger = pass_anger + fail_anger
    return {
        "seed": seed,
        "n_total": len(all_anger),
        "n_pass": len(pass_anger),
        "n_fail": len(fail_anger),
        "pass_quantiles": quantiles(pass_anger),
        "fail_quantiles": quantiles(fail_anger),
        "all_quantiles": quantiles(all_anger),
    }


def threshold_simulation(seed: int, thresholds: dict[str, float]) -> dict:
    events = load_uprising_events(seed)
    results = {}
    for name, T in thresholds.items():
        meets = [e for e in events if e["leader_anger"] >= T]
        # cross-faction pair potential: same top_lord_id, different fid
        by_lord = defaultdict(set)
        for e in meets:
            lid = e.get("top_lord_id")
            if lid:
                by_lord[lid].add(e["fid"])
        cross_lord_count = sum(1 for fids in by_lord.values() if len(fids) >= 2)
        # pass-meet ratio: of those meeting threshold, how many actually gate_passed
        meet_pass = sum(1 for e in meets if e.get("gate_passed"))
        meet_fail = sum(1 for e in meets if not e.get("gate_passed"))
        results[name] = {
            "threshold": T,
            "meet_count": len(meets),
            "meet_pass": meet_pass,
            "meet_fail": meet_fail,
            "meet_pass_ratio": meet_pass / len(meets) if meets else 0.0,
            "unique_top_lords": len(by_lord),
            "cross_faction_lord_count": cross_lord_count,
        }
    return results


def main() -> None:
    per_seed = [analyze_seed(s) for s in SEEDS]

    # combined quantiles (all 3 seeds merged)
    all_pass: list[float] = []
    all_fail: list[float] = []
    all_total: list[float] = []
    for s in SEEDS:
        events = load_uprising_events(s)
        for e in events:
            a = e["leader_anger"]
            all_total.append(a)
            if e.get("gate_passed"):
                all_pass.append(a)
            else:
                all_fail.append(a)

    combined = {
        "n_total": len(all_total),
        "n_pass": len(all_pass),
        "n_fail": len(all_fail),
        "pass_quantiles": quantiles(all_pass),
        "fail_quantiles": quantiles(all_fail),
        "all_quantiles": quantiles(all_total),
    }

    # threshold candidates from combined (3 후보 + 추가)
    aq = combined["all_quantiles"]
    thresholds = {
        "P50": aq["p50"],
        "P67": aq["p67"],
        "P75": aq["p75"],
        "fail_P50": combined["fail_quantiles"]["p50"],
        "pass_P25": combined["pass_quantiles"]["p25"],
    }

    sims = {}
    for s in SEEDS:
        sims[f"seed-{s}"] = threshold_simulation(s, thresholds)

    output = {
        "spec": "PHASE-14B-B-ANGER-COUPLING-PROBE-SPEC.md",
        "phi3_7_chain": "§3.7 4단 (임계 분위수) + 5단 cross-check 입력",
        "seeds": SEEDS,
        "per_seed": per_seed,
        "combined": combined,
        "threshold_candidates": thresholds,
        "threshold_simulation_per_seed": sims,
    }

    OUTPUT_QUANTILES.write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[OK] Wrote {OUTPUT_QUANTILES}")

    # Markdown report
    lines = []
    lines.append("# Phase 14B-B Anger Coupling — Threshold Simulation")
    lines.append("")
    lines.append("> Source: `data/phase17_probe_phi3-snn-output-diag/seed-{7,13,42}/snn_output_events.json`")
    lines.append("> Spec: `PHASE-14B-B-ANGER-COUPLING-PROBE-SPEC.md`")
    lines.append("> §3.7 위치: 4단 (임계 분위수) + 5단 cross-check 입력")
    lines.append("> mechanism 본문 변경 **없음** — 텔레메트리 후처리만")
    lines.append("")
    lines.append("## 1. 전체 통합 분포")
    lines.append("")
    lines.append("| 항목 | n | min | P25 | P50 | P67 | P75 | P80 | P90 | max | mean | stdev |")
    lines.append("|------|:-:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:----:|:-----:|")
    for label, key in [("전체 (pass+fail)", "all_quantiles"), ("pass (gate 통과)", "pass_quantiles"), ("fail (gate 미통과)", "fail_quantiles")]:
        q = combined[key]
        lines.append(
            f"| {label} | {q['n']} | {q['min']:.3f} | {q['p25']:.3f} | {q['p50']:.3f} | {q['p67']:.3f} | {q['p75']:.3f} | {q['p80']:.3f} | {q['p90']:.3f} | {q['max']:.3f} | {q['mean']:.3f} | {q['stdev']:.3f} |"
        )
    lines.append("")

    lines.append("## 2. 임계 후보 (3 seed 통합 분위수에서 도출)")
    lines.append("")
    lines.append("| 후보명 | 임계 | 위치 정당화 |")
    lines.append("|--------|:----:|-------------|")
    lines.append(f"| **P50** | {thresholds['P50']:.4f} | 통합 분포 중앙값 — 약한 결합, 자연 보수적 |")
    lines.append(f"| **P67** | {thresholds['P67']:.4f} | pass 평균과 fail 평균 사이 — 중간 결합 |")
    lines.append(f"| **P75** | {thresholds['P75']:.4f} | pass 분포 P25 근처 — 강한 변별 |")
    lines.append(f"| (참고) fail_P50 | {thresholds['fail_P50']:.4f} | fail 그룹 중앙값 — 너무 낮음 |")
    lines.append(f"| (참고) pass_P25 | {thresholds['pass_P25']:.4f} | pass 그룹 P25 — pass 그룹의 75% 통과 지점 |")
    lines.append("")

    lines.append("## 3. 임계 후보 시뮬 — seed별 PASS 비율 추정")
    lines.append("")
    lines.append("**시뮬 방법**: 각 임계 T에 대해, anger ≥ T인 leader 이벤트만 세서 (1) 실제 gate_passed 비율, (2) cross-faction lord 공유 카운트 (top_lord_id가 동일한 다른 fid 페어 카운트). 이는 mechanism 변경 없는 **후처리 추산** — 실제 mechanism이 임계를 사용한 결과 측정 아님.")
    lines.append("")
    for s in SEEDS:
        lines.append(f"### seed-{s}")
        lines.append("")
        lines.append("| 후보 | 임계 | meet_count | meet_pass | meet_fail | meet_pass_ratio | unique_top_lords | cross_faction_lord_count |")
        lines.append("|------|:----:|:----------:|:---------:|:---------:|:---------------:|:----------------:|:------------------------:|")
        for name, T in thresholds.items():
            r = sims[f"seed-{s}"][name]
            lines.append(
                f"| {name} | {r['threshold']:.4f} | {r['meet_count']} | {r['meet_pass']} | {r['meet_fail']} | {r['meet_pass_ratio']:.3f} | {r['unique_top_lords']} | {r['cross_faction_lord_count']} |"
            )
        lines.append("")

    lines.append("## 4. 해석 (cross-check 입력 자료)")
    lines.append("")
    lines.append("- **meet_pass_ratio**: 임계 T 통과 leader 중 실제 gate_passed 비율. 1.0에 가까울수록 임계가 pass 그룹 변별력 높음.")
    lines.append("- **cross_faction_lord_count**: 동일 `top_lord_id`를 가진 다른 fid 페어 수. ≥ 1이면 cross-faction grievance pair 잠재력 존재 — acceptance #2 (`grievance_pairs_end ≥ 1`) 자연 발생 가능성 시뮬 지표.")
    lines.append("- **주의**: 본 시뮬은 **현재 텔레메트리 후처리** — 실제 mechanism 변경 시 leader 풀이 바뀔 수 있음. 시뮬 결과는 잠재력 비교 자료 (cross-check 의사결정 입력).")
    lines.append("")
    lines.append("## 5. 다음 단계")
    lines.append("")
    lines.append("3엔진 cross-check (`/discuss --quick`) 입력으로 본 데이터 + axis A vs B 차별 검토 + Spec §5의 4 질문 사용. cross-check 후 mechanism 결정.")

    OUTPUT_SIMULATION.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] Wrote {OUTPUT_SIMULATION}")


if __name__ == "__main__":
    main()
