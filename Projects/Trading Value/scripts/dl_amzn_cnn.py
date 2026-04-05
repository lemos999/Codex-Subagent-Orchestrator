#!/usr/bin/env python
"""
AMZN 1D-CNN Direction Classifier
- Data: yfinance AMZN 5yr daily
- Model: PyTorch 1D-CNN (3 conv + pool + FC)
- Walk-forward: 1yr train -> 3mo test sliding
"""

import subprocess, sys, importlib, pathlib, datetime as dt

def _ensure(pkg, pip_name=None):
    try:
        importlib.import_module(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name or pkg, "-q"])

_ensure("torch", "torch")
_ensure("yfinance")
_ensure("numpy")
_ensure("pandas")

import numpy as np
import pandas as pd
import yfinance as yf
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
MODEL_PATH = DATA_DIR / "dl_amzn_cnn.pt"

# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------
WINDOW = 30
FORWARD = 5
NUM_FEATURES = 14


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - 100 / (1 + rs)


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def build_features(df: pd.DataFrame) -> np.ndarray:
    """Return (N, NUM_FEATURES) array aligned with df index."""
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"].astype(float)

    rsi = compute_rsi(close) / 100.0
    atr_ratio = compute_atr(high, low, close) / (close + 1e-10)
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    ma10_pos = (close - ma10) / (ma10 + 1e-10)
    ma20_pos = (close - ma20) / (ma20 + 1e-10)
    ma50_pos = (close - ma50) / (ma50 + 1e-10)
    mom1 = close.pct_change(1)
    mom5 = close.pct_change(5)
    vol_ma20 = volume.rolling(20).mean()
    vol_ratio = volume / (vol_ma20 + 1e-10)

    feat = pd.DataFrame({
        "open": df["Open"],
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "rsi": rsi,
        "atr_ratio": atr_ratio,
        "ma10_pos": ma10_pos,
        "ma20_pos": ma20_pos,
        "ma50_pos": ma50_pos,
        "mom1": mom1,
        "mom5": mom5,
        "vol_ratio": vol_ratio,
    }, index=df.index)

    # 14th feature: intraday range normalised
    feat["intraday_range"] = (high - low) / (close + 1e-10)

    return feat.values  # (N, 14)


def make_windows(features: np.ndarray, close: np.ndarray):
    """
    Create windowed samples.
    Returns X (num_samples, NUM_FEATURES, WINDOW), y (num_samples,)
    """
    X_list, y_list = [], []
    n = len(features)
    for i in range(WINDOW, n - FORWARD):
        window_feat = features[i - WINDOW: i]  # (WINDOW, 14)
        # normalise OHLCV cols (0-4) relative to first close of window
        normed = window_feat.copy()
        ref_close = window_feat[0, 3]  # first close
        if ref_close > 0:
            for c in range(5):  # OHLCV
                normed[:, c] = (normed[:, c] - ref_close) / ref_close
        # volume: normalise to window mean
        vol_mean = normed[:, 4].mean()
        if vol_mean > 0:
            normed[:, 4] = normed[:, 4] / vol_mean

        X_list.append(normed.T)  # (14, WINDOW)
        # target: 5-day forward return direction
        future_ret = (close[i + FORWARD - 1] - close[i - 1]) / (close[i - 1] + 1e-10)
        y_list.append(1.0 if future_ret > 0 else 0.0)

    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.float32)


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
class WindowDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X)
        self.y = torch.tensor(y)

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class DirectionCNN(nn.Module):
    def __init__(self, input_channels: int = NUM_FEATURES, seq_len: int = WINDOW):
        super().__init__()
        self.conv1 = nn.Sequential(
            nn.Conv1d(input_channels, 32, kernel_size=3, padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(2),
        )
        self.conv2 = nn.Sequential(
            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(2),
        )
        self.conv3 = nn.Sequential(
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(),
        )
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 1),
        )

    def forward(self, x):  # (batch, channels, seq_len) -> (batch, 1)
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.pool(x).squeeze(-1)  # (batch, 128)
        return self.fc(x)  # (batch, 1)


# ---------------------------------------------------------------------------
# Training helpers
# ---------------------------------------------------------------------------
def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss, correct, total = 0.0, 0, 0
    for X_b, y_b in loader:
        X_b, y_b = X_b.to(device), y_b.to(device)
        optimizer.zero_grad()
        pred = model(X_b).squeeze(-1)
        loss = criterion(pred, y_b)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * len(y_b)
        preds_bin = (torch.sigmoid(pred) > 0.5).float()
        correct += (preds_bin == y_b).sum().item()
        total += len(y_b)
    return total_loss / total, correct / total


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss, correct, total = 0.0, 0, 0
    all_preds, all_labels = [], []
    for X_b, y_b in loader:
        X_b, y_b = X_b.to(device), y_b.to(device)
        pred = model(X_b).squeeze(-1)
        loss = criterion(pred, y_b)
        total_loss += loss.item() * len(y_b)
        preds_bin = (torch.sigmoid(pred) > 0.5).float()
        correct += (preds_bin == y_b).sum().item()
        total += len(y_b)
        all_preds.extend(preds_bin.cpu().numpy().tolist())
        all_labels.extend(y_b.cpu().numpy().tolist())
    acc = correct / total if total > 0 else 0
    return total_loss / max(total, 1), acc, all_preds, all_labels


# ---------------------------------------------------------------------------
# Walk-forward
# ---------------------------------------------------------------------------
TRAIN_DAYS = 252       # ~1 year
TEST_DAYS = 63         # ~3 months
EPOCHS = 40
PATIENCE = 8
LR = 0.001
BATCH = 32


def run():
    print("=" * 60)
    print("  AMZN 1D-CNN Direction Classifier  (Walk-Forward)")
    print("=" * 60)

    # --- Download ---
    end = dt.datetime.now()
    start = end - dt.timedelta(days=365 * 5 + 30)
    print(f"\nDownloading AMZN {start.date()} ~ {end.date()} ...")
    df = yf.download("AMZN", start=start.strftime("%Y-%m-%d"),
                      end=end.strftime("%Y-%m-%d"), progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    print(f"  rows: {len(df)}")

    # --- Features ---
    features = build_features(df)
    close_arr = df["Close"].values.astype(float)

    # replace NaN with 0
    features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)

    X_all, y_all = make_windows(features, close_arr)
    print(f"  total windows: {len(y_all)}  (up={y_all.sum():.0f}  down={len(y_all)-y_all.sum():.0f})")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  device: {device}\n")

    # --- Walk-forward splits ---
    total_samples = len(y_all)
    results = []
    fold = 0
    offset = 0
    best_model_state = None
    best_overall_acc = 0.0

    while offset + TRAIN_DAYS + TEST_DAYS <= total_samples:
        fold += 1
        tr_end = offset + TRAIN_DAYS
        te_end = tr_end + TEST_DAYS

        X_tr, y_tr = X_all[offset:tr_end], y_all[offset:tr_end]
        X_te, y_te = X_all[tr_end:te_end], y_all[tr_end:te_end]

        train_ds = WindowDataset(X_tr, y_tr)
        test_ds = WindowDataset(X_te, y_te)
        train_loader = DataLoader(train_ds, batch_size=BATCH, shuffle=True)
        test_loader = DataLoader(test_ds, batch_size=BATCH)

        model = DirectionCNN().to(device)
        criterion = nn.BCEWithLogitsLoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=LR)

        best_val_loss = float("inf")
        patience_cnt = 0
        best_state = None

        for ep in range(1, EPOCHS + 1):
            tr_loss, tr_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
            val_loss, val_acc, _, _ = evaluate(model, test_loader, criterion, device)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_cnt = 0
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            else:
                patience_cnt += 1

            if ep % 10 == 0 or ep == 1 or patience_cnt >= PATIENCE:
                print(f"  Fold {fold} | Ep {ep:2d} | "
                      f"Train loss={tr_loss:.4f} acc={tr_acc:.3f} | "
                      f"Val loss={val_loss:.4f} acc={val_acc:.3f}")

            if patience_cnt >= PATIENCE:
                print(f"  -> Early stop at epoch {ep}")
                break

        # reload best
        if best_state:
            model.load_state_dict(best_state)
            model.to(device)

        _, test_acc, preds, labels = evaluate(model, test_loader, criterion, device)
        preds_arr = np.array(preds)
        labels_arr = np.array(labels)
        up_mask = preds_arr == 1
        dn_mask = preds_arr == 0
        up_precision = (labels_arr[up_mask] == 1).mean() if up_mask.sum() > 0 else 0
        dn_precision = (labels_arr[dn_mask] == 0).mean() if dn_mask.sum() > 0 else 0

        results.append({
            "fold": fold,
            "train_range": f"{offset}-{tr_end}",
            "test_range": f"{tr_end}-{te_end}",
            "test_acc": test_acc,
            "up_prec": up_precision,
            "dn_prec": dn_precision,
            "n_test": len(y_te),
            "up_pct": y_te.mean(),
        })
        print(f"  Fold {fold} RESULT: acc={test_acc:.3f}  "
              f"up_prec={up_precision:.3f}  dn_prec={dn_precision:.3f}  "
              f"n={len(y_te)}  up%={y_te.mean():.2f}\n")

        if test_acc > best_overall_acc:
            best_overall_acc = test_acc
            best_model_state = best_state

        offset += TEST_DAYS  # slide by test window

    # --- Summary ---
    print("=" * 60)
    print("  WALK-FORWARD RESULTS")
    print("=" * 60)
    header = f"{'Fold':>4}  {'Test Range':>12}  {'Acc':>6}  {'Up Prec':>7}  {'Dn Prec':>7}  {'N':>4}  {'Up%':>5}"
    print(header)
    print("-" * len(header))
    accs = []
    for r in results:
        print(f"{r['fold']:4d}  {r['test_range']:>12}  {r['test_acc']:6.3f}  "
              f"{r['up_prec']:7.3f}  {r['dn_prec']:7.3f}  {r['n_test']:4d}  {r['up_pct']:5.2f}")
        accs.append(r["test_acc"])

    if accs:
        print("-" * len(header))
        print(f" AVG  {'':>12}  {np.mean(accs):6.3f}  "
              f"{'':>7}  {'':>7}  {sum(r['n_test'] for r in results):4d}")
        print(f" STD  {'':>12}  {np.std(accs):6.3f}")

    # --- Save best model ---
    if best_model_state:
        save_obj = {
            "model_state": best_model_state,
            "input_channels": NUM_FEATURES,
            "seq_len": WINDOW,
            "results": results,
        }
        torch.save(save_obj, MODEL_PATH)
        print(f"\nBest model saved -> {MODEL_PATH}")
        print(f"Best fold accuracy: {best_overall_acc:.3f}")
    else:
        print("\nNo model to save (no folds completed).")

    print("\nDone.")


if __name__ == "__main__":
    run()
