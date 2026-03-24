"""Sub-spec generation for subagent orchestration."""
from __future__ import annotations

import json
from typing import Optional


def generate_backtest_spec(
    quest_id: str,
    market: str = "US",
    symbols: Optional[list[str]] = None,
    strategy_name: str = "ma_crossover",
    start_date: str = "2024-01-01",
    days: int = 30,
    initial_capital: float = 100_000.0,
) -> dict:
    """Generate a sub-spec for backtesting a strategy.

    Returns a dict suitable for the subagent orchestrator.
    """
    symbols = symbols or ["AAPL", "MSFT", "GOOGL"]
    return {
        "task": "backtest",
        "quest_id": quest_id,
        "config": {
            "market": market,
            "symbols": symbols,
            "strategy": strategy_name,
            "start_date": start_date,
            "days": days,
            "initial_capital": initial_capital,
        },
        "expected_output": {
            "total_return_pct": "float",
            "total_trades": "int",
            "win_rate": "float",
            "max_drawdown": "float",
            "sharpe_ratio": "float",
            "daily_results": "list[dict]",
        },
        "command": (
            f"py -m tq quest run --quest-id {quest_id} "
            f"--market {market} --symbols {','.join(symbols)} "
            f"--days {days} --start-date {start_date} "
            f"--capital {initial_capital} --strategy {strategy_name}"
        ),
    }


def generate_optimization_spec(
    quest_id: str,
    market: str = "US",
    symbols: Optional[list[str]] = None,
    strategy_name: str = "ma_crossover",
    start_date: str = "2024-01-01",
    days: int = 60,
    param_ranges: Optional[dict] = None,
    generations: int = 10,
) -> dict:
    """Generate a sub-spec for strategy optimization.

    Returns a dict suitable for the subagent orchestrator.
    """
    symbols = symbols or ["AAPL", "MSFT", "GOOGL"]
    param_ranges = param_ranges or {
        "fast_period": [5, 20],
        "slow_period": [20, 60],
    }
    return {
        "task": "optimize",
        "quest_id": quest_id,
        "config": {
            "market": market,
            "symbols": symbols,
            "strategy": strategy_name,
            "start_date": start_date,
            "days": days,
            "param_ranges": param_ranges,
            "generations": generations,
        },
        "expected_output": {
            "best_params": "dict",
            "best_score": "float",
            "generations_run": "int",
            "optimization_history": "list[dict]",
        },
        "command": (
            f"py -m tq quest optimize --quest-id {quest_id} "
            f"--market {market} --symbols {','.join(symbols)} "
            f"--strategy {strategy_name} --days {days}"
        ),
    }
