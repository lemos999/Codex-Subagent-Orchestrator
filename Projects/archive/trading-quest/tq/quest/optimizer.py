"""Strategy optimizer -- train/validation split, walk-forward optimization."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of a single optimization run."""
    strategy_name: str
    params: dict
    train_score: float = 0.0
    validation_score: float = 0.0
    train_return: float = 0.0
    validation_return: float = 0.0
    train_days: int = 0
    validation_days: int = 0

    @property
    def overfitting_ratio(self) -> float:
        """How much worse validation is vs training."""
        if self.train_score == 0:
            return 0.0
        return 1 - (self.validation_score / self.train_score)

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "params": self.params,
            "train_score": self.train_score,
            "validation_score": self.validation_score,
            "train_return": self.train_return,
            "validation_return": self.validation_return,
            "train_days": self.train_days,
            "validation_days": self.validation_days,
            "overfitting_ratio": self.overfitting_ratio,
        }


class StrategyOptimizer:
    """Walk-forward optimization with train/validation split."""

    def __init__(self, train_ratio: float = 0.7,
                 n_windows: int = 3):
        """
        Args:
            train_ratio: Fraction of data for training.
            n_windows: Number of walk-forward windows.
        """
        self.train_ratio = train_ratio
        self.n_windows = n_windows
        self.results: list[OptimizationResult] = []

    def split_data(self, data: pd.DataFrame,
                   train_ratio: Optional[float] = None
                   ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Split data into train and validation sets."""
        ratio = train_ratio or self.train_ratio
        split_idx = int(len(data) * ratio)
        return data.iloc[:split_idx], data.iloc[split_idx:]

    def walk_forward(self, data: pd.DataFrame,
                     evaluate_fn: Callable[[pd.DataFrame, dict], float],
                     param_grid: list[dict],
                     strategy_name: str = "") -> list[OptimizationResult]:
        """Walk-forward optimization.

        Args:
            data: Full OHLCV DataFrame.
            evaluate_fn: Function(data, params) -> score.
            param_grid: List of parameter dicts to test.
            strategy_name: Name for logging.
        """
        results = []
        window_size = len(data) // self.n_windows

        for window_idx in range(self.n_windows):
            start = window_idx * window_size
            end = min(start + window_size, len(data))
            window_data = data.iloc[start:end]

            train, validation = self.split_data(window_data)

            best_score = -float("inf")
            best_params = param_grid[0] if param_grid else {}
            best_train_score = 0.0

            for params in param_grid:
                try:
                    score = evaluate_fn(train, params)
                    if score > best_score:
                        best_score = score
                        best_params = params
                        best_train_score = score
                except Exception as e:
                    logger.warning("Evaluation failed for params %s: %s", params, e)

            # Validate best params
            try:
                val_score = evaluate_fn(validation, best_params)
            except Exception:
                val_score = 0.0

            result = OptimizationResult(
                strategy_name=strategy_name,
                params=best_params,
                train_score=best_train_score,
                validation_score=val_score,
                train_days=len(train),
                validation_days=len(validation),
            )
            results.append(result)
            self.results.append(result)

            logger.info(
                "Window %d: train=%.2f, val=%.2f, overfit=%.2f%%",
                window_idx, best_train_score, val_score,
                result.overfitting_ratio * 100,
            )

        return results

    def get_best_params(self) -> Optional[dict]:
        """Get parameters with best average validation score."""
        if not self.results:
            return None
        best = max(self.results, key=lambda r: r.validation_score)
        return best.params

    def to_dict(self) -> dict:
        return {
            "train_ratio": self.train_ratio,
            "n_windows": self.n_windows,
            "results": [r.to_dict() for r in self.results],
            "best_params": self.get_best_params(),
        }
