"""Multi-engine backtest spec generation."""
from __future__ import annotations

from typing import Optional


def generate_multi_engine_backtest(
    quest_id: str,
    market: str = "US",
    symbols: Optional[list[str]] = None,
    strategies: Optional[list[str]] = None,
    start_date: str = "2024-01-01",
    days: int = 30,
    initial_capital: float = 100_000.0,
) -> dict:
    """Generate a sub-spec for multi-engine backtesting.

    Compares multiple strategies in parallel across the same market/symbols.
    Returns a dict suitable for the subagent orchestrator.
    """
    symbols = symbols or ["AAPL", "MSFT", "GOOGL"]
    strategies = strategies or ["ma_crossover", "rsi", "macd"]

    sub_tasks = []
    for strat in strategies:
        sub_tasks.append({
            "task": "backtest",
            "engine": strat,
            "quest_id": f"{quest_id}_{strat}",
            "config": {
                "market": market,
                "symbols": symbols,
                "strategy": strat,
                "start_date": start_date,
                "days": days,
                "initial_capital": initial_capital,
            },
            "command": (
                f"py -m tq quest run --quest-id {quest_id}_{strat} "
                f"--market {market} --symbols {','.join(symbols)} "
                f"--days {days} --start-date {start_date} "
                f"--capital {initial_capital} --strategy {strat}"
            ),
        })

    return {
        "task": "multi_engine_backtest",
        "quest_id": quest_id,
        "parallel": True,
        "sub_tasks": sub_tasks,
        "expected_output": {
            "comparison": "list[dict]",
            "best_strategy": "str",
            "leaderboard": "str",
        },
        "aggregate_command": (
            f"py -m tq quest compare --market {market} "
            f"--strategies {','.join(strategies)} "
            f"--symbols {','.join(symbols)} --days {days}"
        ),
    }
