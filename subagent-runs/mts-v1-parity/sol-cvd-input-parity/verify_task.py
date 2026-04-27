from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MTS = ROOT / "Projects" / "Trading Value" / "MTS-V1"


def require_contains(path: Path, expected: str) -> None:
    text = path.read_text(encoding="utf-8")
    if expected not in text:
        raise AssertionError(f"{path} does not contain {expected!r}")


def main() -> int:
    require_contains(
        MTS / "parity_reports" / "sol_cvd_input_parity.md",
        "| reverse_spike_exit_timing_residuals | 7 |",
    )
    require_contains(
        MTS / "parity_reports" / "sol_cvd_input_parity.md",
        "| python_formula_pulses_at_tv_exit | 4 |",
    )
    require_contains(
        MTS / "parity_reports" / "sol_cvd_input_parity.md",
        "| isolated_python_pulse_no_tv_exit_pulse | 3 |",
    )
    require_contains(
        MTS / "REPORT.md",
        "MTS-V1 SOL CVD Input Parity Diagnostic",
    )
    require_contains(
        ROOT / "project-status" / "current.md",
        "MTS-V1 SOL CVD input parity diagnostic completed",
    )
    require_contains(
        ROOT / "subagent-runs" / "mts-v1-parity" / "sol-cvd-input-parity" / "VERIFICATION_LOG.md",
        "Full MTS-V1 tests",
    )
    require_contains(
        MTS / "parity_report.md",
        "Historical Phase7 sample report",
    )
    require_contains(
        MTS / "parity_summary.md",
        "Historical pre-Core5 parity summary",
    )
    print("sol-cvd-input-parity self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
