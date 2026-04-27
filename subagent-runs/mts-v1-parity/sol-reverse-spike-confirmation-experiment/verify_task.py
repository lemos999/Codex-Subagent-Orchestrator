from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MTS = ROOT / "Projects" / "Trading Value" / "MTS-V1"


def require_text(path: Path, expected: str) -> None:
    text = path.read_text(encoding="utf-8")
    if expected not in text:
        raise AssertionError(f"{path} missing expected text: {expected}")


def main() -> int:
    require_text(MTS / "offline_replay.py", "reverse_spike_confirm_bars")
    require_text(MTS / "mts_profile.py", '"reverse_spike_confirm_bars": 1')
    require_text(
        MTS / "tests" / "test_offline_replay.py",
        "test_reverse_spike_confirm_bars_requires_previous_pulse",
    )
    require_text(
        MTS / "parity_reports" / "core5_parity.md",
        "BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D",
    )
    require_text(
        MTS / "parity_reports" / "core5_parity.md",
        "EEC7A0BD5C1D8B61A78E66AB88DF9A66F802EB754A4AB625D28809922CCE1AF8",
    )
    require_text(MTS / "parity_reports" / "sol_diff_entry15.md", "Prev pulse")
    require_text(MTS / "parity_reports" / "sol_diff_entry15.md", "ENTRY_L2/L2_FILL_ON_CLOSE | 240.0m")
    require_text(MTS / "parity_reports" / "sol_diff_confirm2.md", "| matched_common_window_tv_trades | 28 / 71 |")
    require_text(MTS / "parity_reports" / "sol_diff_confirm2.md", "| exit_timestamp_matches | 12 / 28 |")
    print("sol-reverse-spike-confirmation-experiment self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
