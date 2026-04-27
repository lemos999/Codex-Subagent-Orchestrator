from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MTS = ROOT / "Projects" / "Trading Value" / "MTS-V1"
BTC_SHA = "BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D"
SOL_SHA = "2E70E938E97C19E42D63F3464DCE913A7068D3F91999D3C0FF109A9639E3F559"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_text(path: Path) -> str:
    require(path.exists(), f"missing file: {path}")
    return path.read_text(encoding="utf-8")


def main() -> int:
    rows = [
        json.loads(line)
        for line in read_text(MTS / "runs" / "mtsv1_tv_sol_15m_binanceusdm_profile" / "trades.jsonl").splitlines()
        if line.strip()
    ]
    state2 = [
        row
        for row in rows
        if row.get("event") == "EXIT" and row.get("reason") == "STATE_2_ABORT"
    ]
    require(state2, "missing SOL State2 exits")
    for key in (
        "state2_cvd_delta",
        "state2_reverse_spike_threshold",
        "state2_reverse_spike_ratio",
        "state2_reverse_spike_margin",
    ):
        require(all(key in row for row in state2), f"missing {key} on a State2 row")

    sol_diff = read_text(MTS / "parity_reports" / "sol_diff_entry15.md")
    require("CVD delta | Reverse threshold | Reverse ratio | Reverse margin" in sol_diff, "missing reverse-spike residual columns")
    require("| 65 | python_exit_early | state2_reverse_spike | reverse_spike |" in sol_diff, "missing trade 65 residual")
    require("| -121376.0080 | 121189.8383 | 1.0015 | -186.1697 |" in sol_diff, "trade 65 threshold-edge values changed")
    require("| 56 | python_exit_early | state2_reverse_spike | reverse_spike |" in sol_diff, "missing trade 56 residual")
    require("| 68821.0200 | 52390.8597 | 1.3136 | 16430.1603 |" in sol_diff, "trade 56 reverse-spike values changed")

    core5 = read_text(MTS / "parity_reports" / "core5_parity.md")
    require(BTC_SHA in core5, "BTC baseline SHA missing")
    require(SOL_SHA in core5, "SOL telemetry SHA missing")
    require("| BTC | 64 | 64 | 0 | 0 | true | " + BTC_SHA + " | pass |" in core5, "BTC gate row changed")

    print("sol-reverse-spike-pulse-inspection self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
