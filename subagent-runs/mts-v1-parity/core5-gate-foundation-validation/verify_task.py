from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MTS = ROOT / "Projects" / "Trading Value" / "MTS-V1"


def require_contains(path: Path, expected: str) -> None:
    text = path.read_text(encoding="utf-8")
    if expected not in text:
        raise AssertionError(f"{path} does not contain {expected!r}")


def main() -> int:
    core5_report = MTS / "parity_reports" / "core5_parity.md"
    require_contains(core5_report, "| BTC | exit_price_mismatch | semantic_replay_mismatch")
    require_contains(core5_report, "| BTC | 64 | 64 | 0 | 0 | true | BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D | pass |")
    require_contains(core5_report, "| SOL | partial_entry_match | semantic_replay_mismatch")
    require_contains(
        MTS / "parity_report.md",
        "Historical Phase7 sample report",
    )
    require_contains(
        MTS / "parity_summary.md",
        "Historical pre-Core5 parity summary",
    )
    print("core5-gate-foundation-validation self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
