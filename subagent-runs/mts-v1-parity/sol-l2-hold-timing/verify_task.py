from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MTS = ROOT / "Projects" / "Trading Value" / "MTS-V1"
RUN = ROOT / "subagent-runs" / "mts-v1-parity" / "sol-l2-hold-timing"


def require_contains(path: Path, expected: str) -> None:
    text = path.read_text(encoding="utf-8")
    if expected not in text:
        raise AssertionError(f"{path} does not contain {expected!r}")


def main() -> int:
    require_contains(
        MTS / "offline_replay.py",
        "state2_reverse_min_minutes_since_l2",
    )
    require_contains(
        MTS / "tests" / "test_offline_replay.py",
        "test_state2_reverse_l2_hold_suppresses_recent_l2_reverse_only_signal",
    )
    require_contains(
        MTS / "parity_reports" / "sol_diff_l2hold60.md",
        "matched_common_window_tv_trades | 40 / 71",
    )
    require_contains(
        MTS / "parity_reports" / "sol_diff_l2hold300.md",
        "matched_common_window_tv_trades | 39 / 71",
    )
    require_contains(MTS / "REPORT.md", "MTS-V1 SOL L2-Hold Timing Probe")
    require_contains(
        ROOT / "project-status" / "current.md",
        "SOL L2-hold timing probe completed",
    )
    require_contains(
        MTS / "parity_reports" / "core5_parity.md",
        "BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D",
    )
    require_contains(RUN / "FINAL_REVIEW.md", "Rejected as an accepted semantic replay rule")
    print("sol-l2-hold-timing self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
