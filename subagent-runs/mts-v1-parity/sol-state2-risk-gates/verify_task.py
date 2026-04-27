from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MTS = ROOT / "Projects" / "Trading Value" / "MTS-V1"
RUN = ROOT / "subagent-runs" / "mts-v1-parity" / "sol-state2-risk-gates"


def require_contains(path: Path, expected: str) -> None:
    text = path.read_text(encoding="utf-8")
    if expected not in text:
        raise AssertionError(f"{path} does not contain {expected!r}")


def latest_summary(root: Path) -> dict[str, object]:
    summaries = sorted(root.rglob("summary.json"))
    if not summaries:
        raise AssertionError(f"No summary.json under {root}")
    return json.loads(summaries[-1].read_text(encoding="utf-8"))


def main() -> int:
    require_contains(MTS / "risk_gate.py", "def evaluate_risk_gate")
    require_contains(MTS / "strategy.pine", "f_effective_leverage()")
    require_contains(MTS / "tests" / "test_risk_gate.py", "daily max-loss")
    require_contains(
        MTS / "parity_reports" / "sol_diff_minratio_1500.md",
        "matched_common_window_tv_trades | 35 / 71",
    )
    require_contains(MTS / "REPORT.md", "MTS-V1 SOL State2 Risk Gate Pass")
    require_contains(ROOT / "project-status" / "current.md", "SOL State2 risk-gate pass")
    require_contains(RUN / "VERIFICATION_LOG.md", "Full MTS-V1 tests")
    missing_mmr = latest_summary(RUN / "missing_mmr_probe")
    if missing_mmr.get("blocked") is not True:
        raise AssertionError("missing MMR probe did not block")
    daily_loss = latest_summary(RUN / "daily_loss_probe")
    if daily_loss.get("blocked") is not True:
        raise AssertionError("daily loss probe did not block")
    print("sol-state2-risk-gates self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
