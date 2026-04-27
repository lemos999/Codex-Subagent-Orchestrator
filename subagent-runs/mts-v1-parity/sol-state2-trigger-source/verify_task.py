from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MTS = ROOT / "Projects" / "Trading Value" / "MTS-V1"
BTC_SHA = "BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_text(path: Path) -> str:
    require(path.exists(), f"missing file: {path}")
    return path.read_text(encoding="utf-8")


def main() -> int:
    sol_artifact = MTS / "runs" / "mtsv1_tv_sol_15m_binanceusdm_profile" / "trades.jsonl"
    rows = [
        json.loads(line)
        for line in read_text(sol_artifact).splitlines()
        if line.strip()
    ]
    state2_exits = [
        row
        for row in rows
        if row.get("event") == "EXIT" and row.get("reason") == "STATE_2_ABORT"
    ]
    require(state2_exits, "SOL artifact has no STATE_2_ABORT exits")
    require(
        all("state2_trigger_source" in row for row in state2_exits),
        "missing state2_trigger_source on a STATE_2_ABORT exit",
    )
    sources = {row["state2_trigger_source"] for row in state2_exits}
    require("reverse_spike" in sources, "SOL artifact missing reverse_spike source")
    require("htf_cross" in sources, "SOL artifact missing htf_cross source")

    sol_diff = read_text(MTS / "parity_reports" / "sol_diff_entry15.md")
    require("## State2 Trigger Source Summary" in sol_diff, "SOL diff missing trigger summary")
    require("| reverse_spike | 20 | 13 | 7 | 0 |" in sol_diff, "SOL diff reverse_spike summary changed")
    require("| htf_cross | 4 | 4 | 0 | 0 |" in sol_diff, "SOL diff htf_cross summary changed")
    require("state2_reverse_spike" in sol_diff, "SOL diff missing state2_reverse_spike residual bucket")

    sol_trace = read_text(MTS / "parity_reports" / "sol_trace_entry15.md")
    require("Python State2 trigger" in sol_trace, "SOL trace missing trigger column")
    require("STATE_2_ABORT | reverse_spike" in sol_trace, "SOL trace missing reverse_spike rows")
    require("STATE_2_ABORT | htf_cross" in sol_trace, "SOL trace missing htf_cross rows")

    core5 = read_text(MTS / "parity_reports" / "core5_parity.md")
    require(BTC_SHA in core5, "BTC baseline SHA missing from Core5 report")
    require("| BTC | 64 | 64 | 0 | 0 | true | " + BTC_SHA + " | pass |" in core5, "BTC baseline gate row changed")
    require("| SOL | 71 | 69 | 0 | 2 | true | 29477E417024C8D115C77FF80EBCC3B74180763687F17AC770BF642E263B198F | pass |" in core5, "SOL gate row changed")

    print("sol-state2-trigger-source self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
