"""
NVDA Transformer Direction Predictor
=====================================
Standalone script: PyTorch Transformer Encoder for next-5-day return direction.
Data source: yfinance (NVDA 5-year daily bars).
Walk-forward validation: 1-year train -> 3-month test, sliding.

Usage:
    py -3.12 scripts/dl_nvda_transformer.py
"""

from __future__ import annotations

import subprocess
import sys
import math
import pathlib
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Auto-install dependencies
# ---------------------------------------------------------------------------
def _ensure(pkg: str, import_name: str | None = None):
    import_name = import_name or pkg
    try:
        __import__(import_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

_ensure("yfinance")
_ensure("torch")
_ensure("numpy")
_ensure("pandas")
_ensure("scikit-learn", "sklearn")

import numpy as np
import pandas as pd
import yfinance as yf
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TICKER = "NVDA"
YEARS = 5
SEQ_LEN = 40          # 40 trading days (~2 months)
FORWARD_DAYS = 5      # predict 5-day return direction
TRAIN_DAYS = 252      # ~1 year
TEST_DAYS = 63        # ~3 months
D_MODEL = 64
NHEAD = 4
NUM_LAYERS = 2
DROPOUT = 0.2
LR = 0.0005
BATCH = 32
EPOCHS = 50
PATIENCE = 10

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "data" / "dl_nvda_transformer.pt"

# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame of ~16 features per bar."""
    c = df["Close"]
    h = df["High"]
    lo = df["Low"]
    o = df["Open"]
    v = df["Volume"].astype(float)

    feats = pd.DataFrame(index=df.index)

    # Normalised OHLCV (pct change style)
    feats["ret_close"] = c.pct_change()
    feats["ret_open"] = o.pct_change()
    feats["ret_high"] = h.pct_change()
    feats["ret_low"] = lo.pct_change()
    feats["range_hl"] = (h - lo) / c  # intraday range

    # Volume ratio (vs 20-day mean)
    feats["vol_ratio"] = v / v.rolling(20).mean()

    # RSI(14)
    feats["rsi"] = _rsi(c, 14) / 100.0  # scale 0-1

    # ATR(14) / close
    feats["atr_norm"] = _atr(h, lo, c, 14) / c

    # MA position: (close - MA) / close
    for w in (10, 20, 50):
        feats[f"ma{w}_pos"] = (c - c.rolling(w).mean()) / c

    # Momentum (log returns over N days)
    for n in (1, 5, 20):
        feats[f"mom_{n}"] = np.log(c / c.shift(n))

    # Volume momentum
    feats["vol_mom_5"] = np.log(v / v.shift(5).replace(0, np.nan))

    # Body ratio  (close - open) / (high - low)
    body = (c - o) / (h - lo).replace(0, np.nan)
    feats["body_ratio"] = body

    return feats


def build_target(df: pd.DataFrame, forward: int = FORWARD_DAYS) -> pd.Series:
    """1 if close[t+forward] > close[t] else 0."""
    future_ret = df["Close"].shift(-forward) / df["Close"] - 1.0
    return (future_ret > 0).astype(float)


# ---------------------------------------------------------------------------
# Dataset helpers
# ---------------------------------------------------------------------------

def make_sequences(features: np.ndarray, target: np.ndarray, seq_len: int):
    """Slide a window of `seq_len` over features; target is from the last row."""
    X, y = [], []
    for i in range(seq_len, len(features)):
        X.append(features[i - seq_len: i])
        y.append(target[i])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 200, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        pe = torch.zeros(max_len, d_model)
        pos = torch.arange(0, max_len).unsqueeze(1).float()
        div = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(pos * div)
        pe[:, 1::2] = torch.cos(pos * div)
        self.register_buffer("pe", pe.unsqueeze(0))  # (1, max_len, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq, d_model)
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)


class DirectionTransformer(nn.Module):
    def __init__(self, input_dim: int, d_model: int = 64, nhead: int = 4,
                 num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.proj = nn.Linear(input_dim, d_model)
        self.pos_enc = PositionalEncoding(d_model, dropout=dropout)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.head = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq, feat)
        x = self.proj(x)             # -> (batch, seq, d_model)
        x = self.pos_enc(x)
        x = self.encoder(x)          # -> (batch, seq, d_model)
        x = x[:, -1, :]              # last time-step
        return self.head(x).squeeze(-1)  # (batch,)


# ---------------------------------------------------------------------------
# Train / eval one fold
# ---------------------------------------------------------------------------

def train_fold(X_train: np.ndarray, y_train: np.ndarray,
               X_test: np.ndarray, y_test: np.ndarray,
               device: torch.device, verbose: bool = True):
    input_dim = X_train.shape[2]
    model = DirectionTransformer(input_dim, D_MODEL, NHEAD, NUM_LAYERS, DROPOUT).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.BCEWithLogitsLoss()

    train_ds = TensorDataset(torch.tensor(X_train), torch.tensor(y_train))
    train_dl = DataLoader(train_ds, batch_size=BATCH, shuffle=True)

    best_loss = float("inf")
    wait = 0
    best_state = None

    for epoch in range(1, EPOCHS + 1):
        model.train()
        losses = []
        for xb, yb in train_dl:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            opt.step()
            losses.append(loss.item())

        # Validation loss on test set
        model.eval()
        with torch.no_grad():
            xt = torch.tensor(X_test).to(device)
            yt = torch.tensor(y_test).to(device)
            val_logits = model(xt)
            val_loss = criterion(val_logits, yt).item()

        avg_train = np.mean(losses)
        if verbose and epoch % 10 == 0:
            print(f"    epoch {epoch:3d}  train_loss={avg_train:.4f}  val_loss={val_loss:.4f}")

        if val_loss < best_loss:
            best_loss = val_loss
            wait = 0
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            wait += 1
            if wait >= PATIENCE:
                if verbose:
                    print(f"    early stop at epoch {epoch}")
                break

    # Evaluate best model
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        xt = torch.tensor(X_test).to(device)
        preds = torch.sigmoid(model(xt)).cpu().numpy()
    pred_labels = (preds > 0.5).astype(float)
    acc = (pred_labels == y_test).mean()
    return model, best_state, acc, pred_labels, preds


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    print(f"Downloading {TICKER} {YEARS}-year daily data...")

    end = datetime.now()
    start = end - timedelta(days=YEARS * 365)
    df = yf.download(TICKER, start=start.strftime("%Y-%m-%d"),
                     end=end.strftime("%Y-%m-%d"), auto_adjust=True)
    if df.empty:
        print("ERROR: no data downloaded")
        return

    # Flatten multi-level columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    print(f"Bars: {len(df)}  ({df.index[0].date()} ~ {df.index[-1].date()})")

    # Build features and target
    feats_df = build_features(df)
    target_s = build_target(df, FORWARD_DAYS)

    # Align and drop NaN
    combined = pd.concat([feats_df, target_s.rename("target")], axis=1).dropna()
    feat_cols = [c for c in combined.columns if c != "target"]
    print(f"Features: {len(feat_cols)} dims  |  Usable bars: {len(combined)}")

    feat_vals = combined[feat_cols].values
    tgt_vals = combined["target"].values

    # Replace any remaining inf
    feat_vals = np.nan_to_num(feat_vals, nan=0.0, posinf=0.0, neginf=0.0)

    # Walk-forward
    results = []
    fold = 0
    start_idx = 0
    total = len(feat_vals)
    best_global_acc = 0.0
    best_global_state = None
    best_input_dim = len(feat_cols)

    print(f"\n{'='*70}")
    print(f"Walk-Forward:  train={TRAIN_DAYS}d  test={TEST_DAYS}d  seq={SEQ_LEN}")
    print(f"{'='*70}")

    while start_idx + TRAIN_DAYS + TEST_DAYS + SEQ_LEN <= total:
        fold += 1
        tr_start = start_idx
        tr_end = start_idx + TRAIN_DAYS + SEQ_LEN
        te_end = tr_end + TEST_DAYS

        if te_end > total:
            break

        tr_feat = feat_vals[tr_start:tr_end]
        te_feat = feat_vals[tr_end - SEQ_LEN:te_end]  # overlap for seq context
        tr_tgt = tgt_vals[tr_start:tr_end]
        te_tgt = tgt_vals[tr_end - SEQ_LEN:te_end]

        # Fit scaler on train only
        scaler = StandardScaler()
        tr_feat_sc = scaler.fit_transform(tr_feat)
        te_feat_sc = scaler.transform(te_feat)

        X_train, y_train = make_sequences(tr_feat_sc, tr_tgt, SEQ_LEN)
        X_test, y_test = make_sequences(te_feat_sc, te_tgt, SEQ_LEN)

        if len(X_test) == 0:
            break

        period_start = combined.index[tr_start]
        period_end = combined.index[min(te_end - 1, len(combined) - 1)]
        print(f"\n--- Fold {fold}: train {period_start.date()}..  test ..{period_end.date()}  "
              f"(train={len(X_train)}, test={len(X_test)}) ---")

        model, state, acc, _, _ = train_fold(X_train, y_train, X_test, y_test, device)

        up_rate = y_test.mean()
        baseline = max(up_rate, 1 - up_rate)
        print(f"    Accuracy: {acc:.4f}  (baseline: {baseline:.4f})")

        results.append({
            "fold": fold,
            "period": f"{period_start.date()} ~ {period_end.date()}",
            "train_n": len(X_train),
            "test_n": len(X_test),
            "accuracy": acc,
            "baseline": baseline,
            "beat": acc > baseline,
        })

        if acc > best_global_acc:
            best_global_acc = acc
            best_global_state = state

        # Slide by TEST_DAYS
        start_idx += TEST_DAYS

    # Results table
    print(f"\n{'='*70}")
    print(f"{'FOLD':>5} {'PERIOD':<30} {'TRAIN':>6} {'TEST':>5} {'ACC':>7} {'BASE':>7} {'BEAT':>5}")
    print(f"{'-'*70}")
    for r in results:
        print(f"{r['fold']:>5} {r['period']:<30} {r['train_n']:>6} {r['test_n']:>5} "
              f"{r['accuracy']:>7.4f} {r['baseline']:>7.4f} {'Y' if r['beat'] else 'N':>5}")

    accs = [r["accuracy"] for r in results]
    beats = sum(1 for r in results if r["beat"])
    print(f"{'-'*70}")
    print(f"Mean accuracy: {np.mean(accs):.4f}  |  Std: {np.std(accs):.4f}")
    print(f"Beat baseline: {beats}/{len(results)} folds")
    print(f"Best fold acc: {max(accs):.4f}")

    # Save best model
    if best_global_state is not None:
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        save_payload = {
            "state_dict": best_global_state,
            "config": {
                "input_dim": best_input_dim,
                "d_model": D_MODEL,
                "nhead": NHEAD,
                "num_layers": NUM_LAYERS,
                "dropout": DROPOUT,
                "seq_len": SEQ_LEN,
                "forward_days": FORWARD_DAYS,
                "feat_cols": feat_cols,
            },
            "best_acc": best_global_acc,
            "ticker": TICKER,
        }
        torch.save(save_payload, MODEL_PATH)
        print(f"\nModel saved -> {MODEL_PATH}")
    else:
        print("\nNo model saved (no successful fold).")


if __name__ == "__main__":
    main()
