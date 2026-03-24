"""Daily target evaluation for quests."""
from __future__ import annotations

import logging
from typing import Optional

from tq.config import DAILY_TARGET_SCORE

logger = logging.getLogger(__name__)


def evaluate_daily_target(day_result: dict,
                          target_return: float = DAILY_TARGET_SCORE,
                          max_drawdown: float = 0.20) -> dict:
    """Evaluate whether a day met its target.

    Args:
        day_result: Dict with return_pct, trades, win_rate, max_drawdown, score.
        target_return: Minimum return percentage target (decimal).
        max_drawdown: Maximum acceptable drawdown.

    Returns:
        Dict with passed, score, feedback fields.
    """
    return_pct = day_result.get("return_pct", 0.0)
    trades = day_result.get("trades", 0)
    win_rate = day_result.get("win_rate", 0.0)
    drawdown = day_result.get("max_drawdown", 0.0)
    score = day_result.get("score", 0)

    feedback = []
    passed = True

    # Check return target
    if return_pct >= target_return * 100:
        feedback.append(f"Return target met: {return_pct:.2f}%")
    elif return_pct > 0:
        feedback.append(f"Positive return but below target: {return_pct:.2f}% < {target_return * 100:.1f}%")
    elif return_pct == 0 and trades == 0:
        feedback.append("No trades executed -- neutral day")
        # Days with 0 trades are neutral (pass)
    else:
        feedback.append(f"Negative return: {return_pct:.2f}%")
        passed = False

    # Check drawdown
    if drawdown > max_drawdown:
        feedback.append(f"Drawdown exceeded limit: {drawdown:.2%} > {max_drawdown:.2%}")
        passed = False

    # Win rate feedback
    if trades > 0:
        if win_rate >= 50:
            feedback.append(f"Good win rate: {win_rate:.1f}%")
        else:
            feedback.append(f"Low win rate: {win_rate:.1f}%")

    return {
        "passed": passed,
        "score": score,
        "return_pct": return_pct,
        "trades": trades,
        "win_rate": win_rate,
        "drawdown": drawdown,
        "feedback": feedback,
    }
