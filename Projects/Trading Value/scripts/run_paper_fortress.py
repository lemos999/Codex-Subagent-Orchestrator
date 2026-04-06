"""Paper trading with F Fortress (v2 Phase1) model.

Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/run_paper_fortress.py [--once|--status]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from trading_value.adapters.paper import PaperTrader


def main():
    trader = PaperTrader(
        model_path=str(Path(__file__).resolve().parent.parent / "data" / "rl_model_c_v2_200k_validation"),
        symbol="ETH/USDT:USDT",
        leverage=10,
        risk_pct=0.0035,
        commission_rate=0.0004,
        state_file=str(Path(__file__).resolve().parent.parent / "data" / "paper_state_fortress.json"),
        log_file=str(Path(__file__).resolve().parent.parent / "data" / "paper_log_fortress.jsonl"),
    )

    if "--once" in sys.argv:
        print(trader.status())
        print()
        trader.run_once()
        print()
        print(trader.status())
    elif "--status" in sys.argv:
        print(trader.status())
    else:
        print(trader.status())
        print()
        trader.run_loop()


if __name__ == "__main__":
    main()
