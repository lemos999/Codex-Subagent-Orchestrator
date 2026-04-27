from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MTS = ROOT / "Projects" / "Trading Value" / "MTS-V1"


def require_text(path: Path, expected: str) -> None:
    text = path.read_text(encoding="utf-8")
    if expected not in text:
        raise AssertionError(f"{path} missing expected text: {expected}")


def main() -> int:
    official = MTS / "runs" / "mtsv1_tv_sol_15m_binanceusdm_profile" / "trades.jsonl"
    default_probe = (
        MTS
        / "runs"
        / "mtsv1_tv_sol_15m_binanceusdm_profile"
        / "trades_default_minratio_probe.jsonl"
    )
    if official.read_bytes() != default_probe.read_bytes():
        raise AssertionError("default reverse_spike_min_ratio probe is not byte-equal to official SOL artifact")

    require_text(
        MTS / "parity_reports" / "core5_parity.md",
        "BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D",
    )
    require_text(MTS / "parity_reports" / "core5_parity.md", "| SOL | partial_entry_match |")
    require_text(MTS / "parity_reports" / "sol_diff_minratio_1005.md", "| exit_timestamp_matches | 27 / 40 |")
    require_text(MTS / "parity_reports" / "sol_diff_minratio_1005.md", "| exit_price_within_0_15 | 35 / 40 |")
    require_text(MTS / "parity_reports" / "sol_diff_minratio_1005.md", "2026-04-20T23:00:00Z")
    require_text(MTS / "offline_replay.py", "reverse_spike_min_ratio")
    require_text(MTS / "tests" / "test_offline_replay.py", "test_reverse_spike_min_ratio_filters_threshold_edge_pulse")
    print("sol-reverse-spike-threshold-experiment self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
