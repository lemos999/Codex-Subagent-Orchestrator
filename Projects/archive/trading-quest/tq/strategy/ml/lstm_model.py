"""LSTM-like price direction predictor using pure numpy.

Uses a two-layer MLP trained with mini-batch gradient descent as a
portable alternative to PyTorch LSTM.  Sequential features (flattened
sliding windows) give the model temporal context similar to an RNN.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class _NumpyMLP:
    """Minimal two-hidden-layer MLP with ReLU, trained via SGD.

    Intended as a lightweight, dependency-free stand-in for
    sklearn.neural_network.MLPRegressor / MLPClassifier.
    """

    def __init__(self, layer_sizes: list[int], lr: float = 0.001):
        """
        Parameters
        ----------
        layer_sizes : e.g. [input, hidden1, hidden2, output]
        lr          : learning rate
        """
        self.lr = lr
        self.weights: list[np.ndarray] = []
        self.biases: list[np.ndarray] = []
        rng = np.random.RandomState(42)
        for i in range(len(layer_sizes) - 1):
            fan_in = layer_sizes[i]
            fan_out = layer_sizes[i + 1]
            # He initialisation
            scale = np.sqrt(2.0 / fan_in)
            self.weights.append(rng.randn(fan_in, fan_out).astype(np.float64) * scale)
            self.biases.append(np.zeros(fan_out, dtype=np.float64))

    # -- forward ----------------------------------------------------------

    def forward(self, X: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
        """Forward pass. Returns (output, activations_list)."""
        activations = [X]
        h = X
        for i, (W, b) in enumerate(zip(self.weights, self.biases)):
            z = h @ W + b
            if i < len(self.weights) - 1:
                h = np.maximum(0, z)  # ReLU
            else:
                h = self._sigmoid(z)  # output layer
            activations.append(h)
        return h, activations

    # -- backward + update ------------------------------------------------

    def backward(
        self, y_true: np.ndarray, activations: list[np.ndarray]
    ) -> float:
        """Backprop + weight update.  Returns mean loss (binary cross-entropy)."""
        y_pred = activations[-1]
        eps = 1e-12
        y_pred_clipped = np.clip(y_pred, eps, 1 - eps)
        # Binary cross-entropy loss
        loss = -np.mean(
            y_true * np.log(y_pred_clipped)
            + (1 - y_true) * np.log(1 - y_pred_clipped)
        )

        # Gradient of BCE w.r.t. sigmoid output
        delta = (y_pred_clipped - y_true) / len(y_true)

        for i in reversed(range(len(self.weights))):
            a_prev = activations[i]
            dW = a_prev.T @ delta
            db = delta.sum(axis=0)

            # Clip gradients for stability
            np.clip(dW, -5, 5, out=dW)
            np.clip(db, -5, 5, out=db)

            self.weights[i] -= self.lr * dW
            self.biases[i] -= self.lr * db

            if i > 0:
                delta = (delta @ self.weights[i].T) * (activations[i] > 0).astype(float)

        return float(loss)

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _sigmoid(z: np.ndarray) -> np.ndarray:
        z = np.clip(z, -500, 500)
        return 1.0 / (1.0 + np.exp(-z))


class LSTMPredictor:
    """LSTM-like price direction predictor.

    Uses a numpy MLP with flattened sequential features as a portable
    alternative to PyTorch LSTM.  The sliding-window input is reshaped
    to (n_samples, seq_length * n_features) before being fed to the MLP.
    """

    def __init__(
        self,
        seq_length: int = 30,
        hidden_size: int = 64,
        lr: float = 0.001,
        epochs: int = 30,
        batch_size: int = 32,
    ):
        self.seq_length = seq_length
        self.hidden_size = hidden_size
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.model: _NumpyMLP | None = None
        self._mean: np.ndarray | None = None
        self._std: np.ndarray | None = None

    # -----------------------------------------------------------------
    # Train / predict
    # -----------------------------------------------------------------

    def train(self, X: np.ndarray, y: np.ndarray) -> dict:
        """Train the model on sliding-window sequences.

        Parameters
        ----------
        X : shape (n, seq_length, n_features)
        y : shape (n,)  -- binary labels

        Returns
        -------
        dict with 'loss_history' and 'final_accuracy'.
        """
        n = X.shape[0]
        if n == 0:
            return {"loss_history": [], "final_accuracy": 0.0}

        X_flat = X.reshape(n, -1)

        # Standardise
        self._mean = X_flat.mean(axis=0)
        self._std = X_flat.std(axis=0) + 1e-8
        X_flat = (X_flat - self._mean) / self._std

        input_size = X_flat.shape[1]
        self.model = _NumpyMLP(
            [input_size, self.hidden_size, self.hidden_size // 2, 1],
            lr=self.lr,
        )

        y_col = y.reshape(-1, 1)
        losses: list[float] = []
        rng = np.random.RandomState(0)

        for epoch in range(self.epochs):
            indices = rng.permutation(n)
            epoch_loss = 0.0
            batches = 0
            for start in range(0, n, self.batch_size):
                idx = indices[start : start + self.batch_size]
                out, acts = self.model.forward(X_flat[idx])
                batch_loss = self.model.backward(y_col[idx], acts)
                epoch_loss += batch_loss
                batches += 1
            avg_loss = epoch_loss / max(batches, 1)
            losses.append(avg_loss)

        # Final accuracy
        preds = self.predict(X)
        acc = float(np.mean((preds >= 0.5) == y.astype(bool)))
        logger.info("LSTMPredictor training done: loss=%.4f, acc=%.3f", losses[-1], acc)
        return {"loss_history": losses, "final_accuracy": acc}

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict price direction probability (0-1).

        Parameters
        ----------
        X : shape (n, seq_length, n_features) or (n, flat_features)

        Returns
        -------
        ndarray of shape (n,) with values in [0, 1].
        """
        if self.model is None:
            raise RuntimeError("Model not trained yet. Call train() first.")
        if X.ndim == 3:
            X = X.reshape(X.shape[0], -1)
        X = (X - self._mean) / self._std
        out, _ = self.model.forward(X)
        return out.ravel()

    # -----------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------

    def save(self, path: Path) -> None:
        """Save model weights and normalisation stats to *path* directory."""
        path.mkdir(parents=True, exist_ok=True)
        if self.model is None:
            return
        for i, (W, b) in enumerate(zip(self.model.weights, self.model.biases)):
            np.save(str(path / f"W{i}.npy"), W)
            np.save(str(path / f"b{i}.npy"), b)
        if self._mean is not None:
            np.save(str(path / "mean.npy"), self._mean)
            np.save(str(path / "std.npy"), self._std)
        meta = {
            "seq_length": self.seq_length,
            "hidden_size": self.hidden_size,
            "lr": self.lr,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "n_layers": len(self.model.weights),
            "layer_sizes": [w.shape[0] for w in self.model.weights]
            + [self.model.weights[-1].shape[1]],
        }
        (path / "meta.json").write_text(json.dumps(meta))

    def load(self, path: Path) -> None:
        """Load model weights from *path* directory."""
        meta = json.loads((path / "meta.json").read_text())
        self.seq_length = meta["seq_length"]
        self.hidden_size = meta["hidden_size"]
        self.model = _NumpyMLP(meta["layer_sizes"], lr=meta.get("lr", 0.001))
        for i in range(meta["n_layers"]):
            self.model.weights[i] = np.load(str(path / f"W{i}.npy"))
            self.model.biases[i] = np.load(str(path / f"b{i}.npy"))
        mean_path = path / "mean.npy"
        if mean_path.exists():
            self._mean = np.load(str(mean_path))
            self._std = np.load(str(path / "std.npy"))
