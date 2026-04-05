"""
dl_train_pipeline.py -- Walk-Forward Deep Learning Training Pipeline
=============================================================
다른 dl_*.py 스크립트에서 공통으로 사용하는 학습 인프라.

Usage (import):
    from dl_train_pipeline import WalkForwardTrainer, EarlyStopping, SequenceDataset

Usage (standalone demo):
    py -3.12 scripts/dl_train_pipeline.py
"""

from __future__ import annotations

import math
import pathlib
import subprocess
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Auto-install
# ---------------------------------------------------------------------------
def _ensure(pkg: str, import_name: str | None = None) -> None:
    import_name = import_name or pkg
    try:
        __import__(import_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

_ensure("torch")
_ensure("numpy")
_ensure("scikit-learn", "sklearn")

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

try:
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------
def get_device() -> torch.device:
    """CUDA > CPU 자동 감지."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")

# ---------------------------------------------------------------------------
# EarlyStopping
# ---------------------------------------------------------------------------
class EarlyStopping:
    """Validation loss 기반 Early Stopping.

    Parameters
    ----------
    patience : int
        성능 개선 없이 허용할 에폭 수.
    min_delta : float
        개선으로 인정할 최소 감소량.
    """

    def __init__(self, patience: int = 5, min_delta: float = 0.001) -> None:
        self.patience = patience
        self.min_delta = min_delta
        self._best_loss = float("inf")
        self._counter = 0
        self.best_epoch: int = 0

    def step(self, val_loss: float) -> bool:
        """val_loss를 받아 학습 중단 여부 반환. True면 중단."""
        if val_loss < self._best_loss - self.min_delta:
            self._best_loss = val_loss
            self._counter = 0
        else:
            self._counter += 1
        if self._counter >= self.patience:
            return True
        return False

    def reset(self) -> None:
        self._best_loss = float("inf")
        self._counter = 0
        self.best_epoch = 0

# ---------------------------------------------------------------------------
# SequenceDataset
# ---------------------------------------------------------------------------
class SequenceDataset(Dataset):
    """Sliding-window 시퀀스 Dataset.

    Parameters
    ----------
    X : np.ndarray, shape (T, F)
        특성 행렬.
    y : np.ndarray, shape (T,)
        레이블 (0/1 분류 또는 float 회귀).
    seq_len : int
        시퀀스 길이(lookback 윈도우).
    """

    def __init__(self, X: np.ndarray, y: np.ndarray, seq_len: int = 60) -> None:
        assert len(X) == len(y), "X와 y의 길이가 일치해야 합니다."
        assert len(X) > seq_len, f"데이터({len(X)})가 seq_len({seq_len})보다 길어야 합니다."
        self.seq_len = seq_len
        # seq_len ~ T-1 인덱스에 대해 슬라이딩 윈도우 생성
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.X) - self.seq_len

    def __getitem__(self, idx: int):
        x_seq = self.X[idx : idx + self.seq_len]       # (seq_len, F)
        label = self.y[idx + self.seq_len]
        return x_seq, label

# ---------------------------------------------------------------------------
# Data utilities
# ---------------------------------------------------------------------------
def normalize_features(
    X_train: np.ndarray,
    X_val: np.ndarray,
    X_test: np.ndarray | None = None,
) -> tuple:
    """Train 기준 StandardScaler 정규화.

    Returns
    -------
    tuple of (X_train_norm, X_val_norm[, X_test_norm], scaler)
    """
    scaler = StandardScaler()
    X_train_n = scaler.fit_transform(X_train)
    X_val_n = scaler.transform(X_val)
    if X_test is not None:
        X_test_n = scaler.transform(X_test)
        return X_train_n, X_val_n, X_test_n, scaler
    return X_train_n, X_val_n, scaler


def train_val_split(
    X: np.ndarray,
    y: np.ndarray,
    val_ratio: float = 0.15,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """시계열 순서를 유지하는 Train/Val 분할."""
    n = len(X)
    split = int(n * (1.0 - val_ratio))
    return X[:split], y[:split], X[split:], y[split:]


def make_month_boundaries(
    timestamps: np.ndarray,
    train_months: int,
    test_months: int,
) -> list[tuple[int, int, int, int]]:
    """timestamps 배열로부터 walk-forward 윈도우 인덱스 목록 생성.

    Returns
    -------
    list of (train_start, train_end, test_start, test_end) index tuples.
    """
    import pandas as pd

    ts = pd.to_datetime(timestamps)
    min_ts = ts.min()
    max_ts = ts.max()

    windows = []
    cursor = min_ts + pd.DateOffset(months=train_months)

    while cursor + pd.DateOffset(months=test_months) <= max_ts + pd.Timedelta(days=1):
        train_start_ts = cursor - pd.DateOffset(months=train_months)
        train_end_ts = cursor
        test_start_ts = cursor
        test_end_ts = cursor + pd.DateOffset(months=test_months)

        tr_s = int(np.searchsorted(ts.values, np.datetime64(train_start_ts)))
        tr_e = int(np.searchsorted(ts.values, np.datetime64(train_end_ts)))
        te_s = int(np.searchsorted(ts.values, np.datetime64(test_start_ts)))
        te_e = int(np.searchsorted(ts.values, np.datetime64(test_end_ts)))

        if te_e > te_s and tr_e > tr_s:
            windows.append((tr_s, tr_e, te_s, te_e))

        cursor += pd.DateOffset(months=test_months)

    return windows


# ---------------------------------------------------------------------------
# WalkForwardTrainer
# ---------------------------------------------------------------------------
class WalkForwardTrainer:
    """Walk-Forward 딥러닝 학습 파이프라인.

    Parameters
    ----------
    model_class : type
        PyTorch nn.Module 서브클래스.
    model_kwargs : dict
        model_class 생성자에 전달할 키워드 인수.
    train_months : int
        학습 윈도우 크기(월).
    test_months : int
        테스트 윈도우 크기(월).
    lr : float
        초기 학습률.
    batch_size : int
        미니배치 크기.
    epochs : int
        최대 에폭 수.
    patience : int
        EarlyStopping patience.
    seq_len : int
        SequenceDataset lookback 길이.
    val_ratio : float
        학습 데이터 내 검증 분할 비율.
    device : str | None
        'cuda' / 'cpu' / None(자동 감지).
    task : str
        'classification' 또는 'regression'.
    """

    def __init__(
        self,
        model_class: type,
        model_kwargs: dict,
        train_months: int = 6,
        test_months: int = 1,
        lr: float = 0.001,
        batch_size: int = 64,
        epochs: int = 30,
        patience: int = 5,
        seq_len: int = 60,
        val_ratio: float = 0.15,
        device: str | None = None,
        task: str = "classification",
    ) -> None:
        self.model_class = model_class
        self.model_kwargs = model_kwargs
        self.train_months = train_months
        self.test_months = test_months
        self.lr = lr
        self.batch_size = batch_size
        self.epochs = epochs
        self.patience = patience
        self.seq_len = seq_len
        self.val_ratio = val_ratio
        self.task = task

        if device is None:
            self.device = get_device()
        else:
            self.device = torch.device(device)

        self._best_model_state: dict | None = None
        self._window_results: list[dict] = []

    # ------------------------------------------------------------------
    def _build_model(self) -> nn.Module:
        return self.model_class(**self.model_kwargs).to(self.device)

    def _loss_fn(self) -> nn.Module:
        if self.task == "classification":
            return nn.BCEWithLogitsLoss()
        return nn.MSELoss()

    def _compute_metrics(
        self,
        model: nn.Module,
        loader: DataLoader,
    ) -> dict[str, float]:
        """acc(분류) 또는 mse(회귀), auc(분류만) 계산."""
        model.eval()
        all_logits: list[np.ndarray] = []
        all_labels: list[np.ndarray] = []
        total_loss = 0.0
        n_batches = 0
        criterion = self._loss_fn()

        with torch.no_grad():
            for xb, yb in loader:
                xb, yb = xb.to(self.device), yb.to(self.device)
                logits = model(xb).squeeze(-1)
                loss = criterion(logits, yb)
                total_loss += loss.item()
                n_batches += 1
                all_logits.append(logits.cpu().numpy())
                all_labels.append(yb.cpu().numpy())

        logits_np = np.concatenate(all_logits)
        labels_np = np.concatenate(all_labels)
        avg_loss = total_loss / max(n_batches, 1)

        metrics: dict[str, float] = {"loss": avg_loss}

        if self.task == "classification":
            preds = (logits_np > 0.0).astype(int)
            acc = float((preds == labels_np.astype(int)).mean())
            metrics["acc"] = acc
            if _SKLEARN_AVAILABLE and len(np.unique(labels_np)) > 1:
                probs = torch.sigmoid(torch.tensor(logits_np)).numpy()
                metrics["auc"] = float(roc_auc_score(labels_np, probs))
            else:
                metrics["auc"] = float("nan")
        else:
            metrics["mse"] = float(np.mean((logits_np - labels_np) ** 2))

        return metrics

    # ------------------------------------------------------------------
    def train_window(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> dict[str, Any]:
        """단일 윈도우 학습.

        Returns
        -------
        dict with keys: train_acc, val_acc, val_auc, val_loss, model_state, epochs_run
        """
        # 정규화
        X_tr_n, X_vl_n, _ = normalize_features(X_train, X_val)

        # 데이터셋
        try:
            train_ds = SequenceDataset(X_tr_n, y_train, self.seq_len)
            val_ds = SequenceDataset(X_vl_n, y_val, self.seq_len)
        except AssertionError as exc:
            print(f"  [skip window] {exc}")
            return {
                "train_acc": float("nan"), "val_acc": float("nan"),
                "val_auc": float("nan"), "val_loss": float("nan"),
                "model_state": None, "epochs_run": 0,
            }

        train_loader = DataLoader(train_ds, batch_size=self.batch_size, shuffle=False)
        val_loader = DataLoader(val_ds, batch_size=self.batch_size, shuffle=False)

        model = self._build_model()
        optimizer = torch.optim.Adam(model.parameters(), lr=self.lr)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=max(2, self.patience // 2)
        )
        criterion = self._loss_fn()
        early_stop = EarlyStopping(patience=self.patience)

        best_val_loss = float("inf")
        best_state: dict | None = None
        epochs_run = 0

        for epoch in range(1, self.epochs + 1):
            model.train()
            for xb, yb in train_loader:
                xb, yb = xb.to(self.device), yb.to(self.device)
                optimizer.zero_grad()
                logits = model(xb).squeeze(-1)
                loss = criterion(logits, yb)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

            val_metrics = self._compute_metrics(model, val_loader)
            val_loss = val_metrics["loss"]
            scheduler.step(val_loss)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

            epochs_run = epoch
            if early_stop.step(val_loss):
                break

        # 최적 가중치 로드 후 최종 지표 계산
        if best_state is not None:
            model.load_state_dict(best_state)

        train_metrics = self._compute_metrics(model, train_loader)
        val_metrics = self._compute_metrics(model, val_loader)

        return {
            "train_acc": train_metrics.get("acc", float("nan")),
            "val_acc": val_metrics.get("acc", float("nan")),
            "val_auc": val_metrics.get("auc", float("nan")),
            "val_loss": val_metrics["loss"],
            "model_state": best_state,
            "epochs_run": epochs_run,
        }

    # ------------------------------------------------------------------
    def walk_forward(
        self,
        X: np.ndarray,
        y: np.ndarray,
        timestamps: np.ndarray,
    ) -> list[dict[str, Any]]:
        """전체 Walk-Forward 학습 실행.

        Parameters
        ----------
        X : np.ndarray, shape (T, F)
        y : np.ndarray, shape (T,)
        timestamps : np.ndarray of datetime-like, shape (T,)

        Returns
        -------
        list of window result dicts (각 dict는 train_window 결과 + window 인덱스).
        """
        windows = make_month_boundaries(timestamps, self.train_months, self.test_months)
        if not windows:
            raise ValueError("walk-forward 윈도우가 0개입니다. 데이터 기간을 확인하세요.")

        self._window_results = []
        best_val_auc = -float("inf")

        for i, (tr_s, tr_e, te_s, te_e) in enumerate(windows):
            X_tr_raw = X[tr_s:tr_e]
            y_tr_raw = y[tr_s:tr_e]

            # 학습 데이터를 train/val로 분할
            X_tr, y_tr, X_vl, y_vl = train_val_split(
                X_tr_raw, y_tr_raw, val_ratio=self.val_ratio
            )

            print(
                f"  Window {i+1}/{len(windows)} | "
                f"train [{tr_s}:{tr_e}] ({len(X_tr)}+{len(X_vl)}) | "
                f"test [{te_s}:{te_e}]"
            )

            result = self.train_window(X_tr, y_tr, X_vl, y_vl)
            result["window_idx"] = i
            result["train_range"] = (tr_s, tr_e)
            result["test_range"] = (te_s, te_e)
            self._window_results.append(result)

            # 전체 best 모델 추적
            auc = result.get("val_auc", float("nan"))
            if not math.isnan(auc) and auc > best_val_auc:
                best_val_auc = auc
                self._best_model_state = result["model_state"]

            print(
                f"    => val_acc={result['val_acc']:.4f}  "
                f"val_auc={result['val_auc']:.4f}  "
                f"epochs={result['epochs_run']}"
            )

        return self._window_results

    # ------------------------------------------------------------------
    def aggregate_results(self) -> dict[str, float]:
        """walk_forward 결과 전체 집계."""
        if not self._window_results:
            return {}

        valid = [r for r in self._window_results if not math.isnan(r.get("val_acc", float("nan")))]
        if not valid:
            return {"windows": 0}

        avg_acc = float(np.mean([r["val_acc"] for r in valid]))
        avg_auc_vals = [r["val_auc"] for r in valid if not math.isnan(r.get("val_auc", float("nan")))]
        avg_auc = float(np.mean(avg_auc_vals)) if avg_auc_vals else float("nan")

        return {
            "windows": len(valid),
            "avg_val_acc": avg_acc,
            "avg_val_auc": avg_auc,
            "window_accs": [r["val_acc"] for r in valid],
            "window_aucs": [r["val_auc"] for r in valid],
        }

    # ------------------------------------------------------------------
    def save_best_model(self, path: str | pathlib.Path) -> None:
        """Best model state_dict를 파일로 저장."""
        if self._best_model_state is None:
            raise RuntimeError("저장할 모델이 없습니다. walk_forward()를 먼저 실행하세요.")
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_kwargs": self.model_kwargs,
                "state_dict": self._best_model_state,
            },
            path,
        )
        print(f"  Best model saved -> {path}")

    def load_model(self, path: str | pathlib.Path) -> nn.Module:
        """저장된 state_dict를 로드하여 모델 반환."""
        checkpoint = torch.load(path, map_location=self.device)
        model = self._build_model()
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()
        return model


# ===========================================================================
# DEMO (standalone) -- sin wave next-step direction prediction
# ===========================================================================
def _make_sin_demo_data(
    n: int = 1000,
    noise: float = 0.05,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """sin wave + 노이즈에서 (X, y, timestamps) 생성.
    y = 1 if next step goes up, else 0.
    """
    import pandas as pd

    t = np.linspace(0, 10 * np.pi, n)
    signal = np.sin(t) + np.random.randn(n) * noise

    # 피처: [value, diff1, diff2, abs_diff1]
    diff1 = np.diff(signal, prepend=signal[0])
    diff2 = np.diff(diff1, prepend=diff1[0])
    X = np.stack([signal, diff1, diff2, np.abs(diff1)], axis=1).astype(np.float32)

    # 레이블: 다음 스텝 상승이면 1
    y = (np.diff(signal, append=signal[-1]) > 0).astype(np.float32)

    # timestamps: 2021-01-01 기준 일별
    start = pd.Timestamp("2021-01-01")
    timestamps = np.array(
        [start + pd.Timedelta(days=int(i)) for i in range(n)], dtype="datetime64[ns]"
    )

    return X, y, timestamps


class _DemoLSTM(nn.Module):
    """데모용 단순 LSTM 분류기."""

    def __init__(self, input_size: int = 4, hidden_size: int = 32, num_layers: int = 1) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size, hidden_size, num_layers=num_layers, batch_first=True
        )
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, seq_len, F)
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])  # (B, 1)


if __name__ == "__main__":
    print("=" * 60)
    print("dl_train_pipeline.py -- Walk-Forward Demo")
    print("=" * 60)
    device = get_device()
    print(f"Device: {device}")

    print("\n[1] Sin wave data generation...")
    # Use 2000 samples to ensure enough data per window
    X, y, ts = _make_sin_demo_data(n=2000)
    print(f"    X shape: {X.shape}, y shape: {y.shape}, positive ratio: {y.mean():.3f}")

    print("\n[2] WalkForwardTrainer init (LSTM)...")
    # seq_len=10, train_months=6 -> ~180 rows per window; val(15%)=~27 > seq_len
    trainer = WalkForwardTrainer(
        model_class=_DemoLSTM,
        model_kwargs={"input_size": 4, "hidden_size": 32},
        train_months=6,
        test_months=1,
        lr=0.002,
        batch_size=32,
        epochs=15,
        patience=4,
        seq_len=10,
        val_ratio=0.15,
        task="classification",
    )

    print("\n[3] Walk-Forward training...")
    results = trainer.walk_forward(X, y, ts)

    print("\n[4] Aggregate results:")
    agg = trainer.aggregate_results()
    print(f"    Windows    : {agg['windows']}")
    if agg.get("avg_val_acc") is not None:
        print(f"    Avg Val Acc: {agg['avg_val_acc']:.4f}")
        print(f"    Avg Val AUC: {agg['avg_val_auc']:.4f}")

    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
        tmp_path = f.name
    trainer.save_best_model(tmp_path)
    model = trainer.load_model(tmp_path)
    os.unlink(tmp_path)
    print(f"    save/load best model: OK (params={sum(p.numel() for p in model.parameters())})")

    print("\n[5] Done.")
