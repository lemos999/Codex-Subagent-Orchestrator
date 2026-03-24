"""LSTM-based price direction prediction strategy."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.ml.features import FeatureEngineering
from tq.strategy.ml.lstm_model import LSTMPredictor

logger = logging.getLogger(__name__)

_MODELS_DIR = Path("models") / "lstm"


@strategy("lstm")
class LSTMStrategy(BaseStrategy):
    """LSTM-based price direction prediction.

    Auto-trains on the first invocation if no saved model exists,
    then retrains periodically every *retrain_days* calls.
    """

    name = "lstm"
    description = "LSTM-based price direction prediction"

    def __init__(
        self,
        seq_length: int = 30,
        threshold: float = 0.6,
        retrain_days: int = 50,
        hidden_size: int = 64,
        epochs: int = 20,
    ):
        self.seq_length = seq_length
        self.threshold = threshold
        self.retrain_days = retrain_days
        self.hidden_size = hidden_size
        self.epochs = epochs

        self.features = FeatureEngineering()
        self.model: LSTMPredictor | None = None
        self._days_since_train = 0
        self._symbol_models: dict[str, LSTMPredictor] = {}

    # -----------------------------------------------------------------
    # BaseStrategy interface
    # -----------------------------------------------------------------

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        symbol = (
            data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"
        )

        if len(data) < self.features.MIN_ROWS + self.seq_length:
            return []

        model = self._ensure_trained(symbol, data)
        if model is None:
            return []

        # Build features for the latest window
        feat_df = self.features.build_features(data)
        if len(feat_df) < self.seq_length:
            return []

        latest = feat_df.values[-self.seq_length :]
        X = latest.reshape(1, self.seq_length, -1)

        try:
            prob = float(model.predict(X)[0])
        except Exception as e:
            logger.warning("LSTM predict error: %s", e)
            return []

        self._days_since_train += 1

        signals: list[dict] = []
        if prob > self.threshold:
            signals.append({
                "symbol": symbol,
                "side": "BUY",
                "qty": 1,
                "confidence": prob,
                "reason": f"LSTM bullish ({prob:.2f})",
            })
        elif prob < (1 - self.threshold):
            signals.append({
                "symbol": symbol,
                "side": "SELL",
                "qty": 1,
                "confidence": 1 - prob,
                "reason": f"LSTM bearish ({prob:.2f})",
            })
        return signals

    def get_params(self) -> dict:
        return {
            "seq_length": self.seq_length,
            "threshold": self.threshold,
            "retrain_days": self.retrain_days,
            "hidden_size": self.hidden_size,
            "epochs": self.epochs,
        }

    # -----------------------------------------------------------------
    # Training helpers
    # -----------------------------------------------------------------

    def _ensure_trained(
        self, symbol: str, data: pd.DataFrame
    ) -> LSTMPredictor | None:
        """Return a trained model for *symbol*, training or retraining as
        needed."""
        model = self._symbol_models.get(symbol)

        needs_train = (
            model is None or self._days_since_train >= self.retrain_days
        )

        if not needs_train:
            return model

        # Try loading a saved model
        model_dir = _MODELS_DIR / symbol
        if model is None and model_dir.exists() and (model_dir / "meta.json").exists():
            try:
                model = LSTMPredictor(
                    seq_length=self.seq_length, hidden_size=self.hidden_size
                )
                model.load(model_dir)
                self._symbol_models[symbol] = model
                self._days_since_train = 0
                logger.info("Loaded saved LSTM model for %s", symbol)
                return model
            except Exception as e:
                logger.warning("Failed to load LSTM model for %s: %s", symbol, e)

        # Train a new model
        return self._train_model(symbol, data)

    def _train_model(
        self, symbol: str, data: pd.DataFrame
    ) -> LSTMPredictor | None:
        """Train a fresh LSTM model on *data*."""
        try:
            feat_df = self.features.build_features(data)
            labels = self.features.build_labels(data)
            X, y = self.features.prepare_sequences(feat_df, labels, self.seq_length)
            if len(X) < 10:
                logger.warning("Insufficient data to train LSTM for %s (%d samples)", symbol, len(X))
                return None

            model = LSTMPredictor(
                seq_length=self.seq_length,
                hidden_size=self.hidden_size,
                epochs=self.epochs,
            )
            metrics = model.train(X, y)
            logger.info(
                "Trained LSTM for %s: acc=%.3f, loss=%.4f",
                symbol, metrics["final_accuracy"], metrics["loss_history"][-1] if metrics["loss_history"] else 0,
            )

            # Save model
            model_dir = _MODELS_DIR / symbol
            model.save(model_dir)

            self._symbol_models[symbol] = model
            self._days_since_train = 0
            return model
        except Exception as e:
            logger.warning("LSTM training failed for %s: %s", symbol, e)
            return None
