from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3] / "Projects" / "Trading Value" / "MTS-V1"
CORE5 = ROOT / "parity_reports" / "core5_parity.md"
SOL_DIFF = ROOT / "parity_reports" / "sol_diff_entry15.md"
SOL_TRACE = ROOT / "parity_reports" / "sol_trace_entry15.md"

sys.path.insert(0, str(ROOT))

from btc_parity_diff import matched_exit_timing_bucket

BTC_SHA = "BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D"


def require(text: str, needle: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing expected text: {needle}")


def main() -> int:
    bucket, delta = matched_exit_timing_bucket(
        datetime(2026, 4, 24, 1, 0, tzinfo=UTC),
        datetime(2026, 4, 24, 0, 30, tzinfo=UTC),
        tolerance=timedelta(minutes=15),
    )
    assert bucket == "python_exit_early"
    assert delta == timedelta(minutes=-30)

    core5 = CORE5.read_text(encoding="utf-8")
    require(core5, "| BTC | exit_price_mismatch | semantic_replay_mismatch")
    require(core5, "| BTC | 64 | 64 | 0 | 0 | true | " + BTC_SHA + " | pass |")
    require(core5, "| SOL | partial_entry_match | semantic_replay_mismatch")
    require(core5, "| SOL | 71 | 69 | 0 | 2 | true |")

    sol_diff = SOL_DIFF.read_text(encoding="utf-8")
    require(sol_diff, "- TradingView raw rows: `71`")
    require(sol_diff, "- TradingView common-window rows: `69`")
    require(sol_diff, "- TradingView tail after Python artifact: `2`")
    require(sol_diff, "| matched_common_window_tv_trades | 40 / 69 |")
    require(sol_diff, "| matched_exit_timing_residuals | `{'python_exit_early': 7, 'python_exit_late': 6}` |")
    require(sol_diff, "| matched_exit_cause_buckets | `{'entry_cycle_drift': 1, 'non_state2_abort': 6, 'same_bar_close_or_fill_ordering': 2, 'unknown_state2_abort': 4}` |")

    sol_trace = SOL_TRACE.read_text(encoding="utf-8")
    require(sol_trace, "- TV raw closed trade rows: 71")
    require(sol_trace, "- TV common-window closed trade rows: 69")
    require(sol_trace, "- TV tail after Python artifact: 2")
    require(sol_trace, "- Matched common-window TV rows: 40 / 69")

    print("sol-state2-diagnosis self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
