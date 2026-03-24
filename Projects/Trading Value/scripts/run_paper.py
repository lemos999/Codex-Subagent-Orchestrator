"""Start paper trading with RL v4 agent.

Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/run_paper.py [--once]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from trading_value.adapters.paper import PaperTrader


def main():
    trader = PaperTrader(
        model_path=str(Path(__file__).resolve().parent.parent / "data" / "rl_model_v4"),
        symbol="ETH/USDT:USDT",
        leverage=10,
        risk_pct=0.0035,
        commission_rate=0.0004,
        state_file=str(Path(__file__).resolve().parent.parent / "data" / "paper_state.json"),
        log_file=str(Path(__file__).resolve().parent.parent / "data" / "paper_log.jsonl"),
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
