"""BTC 4H Direction Predictor using LSTM (Walk-Forward)."""

import subprocess
import sys
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "torch"])
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sim_1m.sqlite"
MODEL_PATH = Path(__file__).resolve().parent.parent / "data" / "dl_btc_lstm.pt"

SEQ_LEN = 60
HIDDEN_DIM = 128
NUM_LAYERS = 2
DROPOUT = 0.3
LR = 0.001
BATCH_SIZE = 64
EPOCHS = 30
PATIENCE = 5

TRAIN_MONTHS = 6
TEST_MONTHS = 1


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class DirectionLSTM(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = HIDDEN_DIM,
                 num_layers: int = NUM_LAYERS, dropout: float = DROPOUT):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, input_dim)
        out, _ = self.lstm(x)
        out = out[:, -1, :]  # last timestep
        out = self.dropout(out)
        return self.fc(out)  # (batch, 1)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_btc_4h() -> pd.DataFrame:
    """Load BTCUSDT 1m from sqlite, resample to 4H OHLCV."""
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query(
        "SELECT timestamp, open, high, low, close, volume "
        "FROM ohlcv_1m WHERE symbol='BTCUSDT' ORDER BY timestamp",
        conn,
    )
    conn.close()

    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("datetime", inplace=True)
    df.drop(columns=["timestamp"], inplace=True)

    ohlcv = df.resample("4h").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()

    print(f"[Data] 4H candles: {len(ohlcv)}  "
          f"({ohlcv.index[0].date()} ~ {ohlcv.index[-1].date()})")
    return ohlcv


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------
def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _atr(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    prev_c = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_c).abs(),
        (low - prev_c).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def compute_features(df: pd.DataFrame):
    """Build feature sequences and binary targets.

    Returns:
        X: np.ndarray (n_samples, SEQ_LEN, n_features)
        y: np.ndarray (n_samples,)  binary 0/1
        dates: pd.DatetimeIndex of target bars
    """
    c = df["close"]

    feat = pd.DataFrame(index=df.index)

    # --- OHLCV normalised to current close (%) ---
    feat["open_pct"] = (df["open"] - c) / c
    feat["high_pct"] = (df["high"] - c) / c
    feat["low_pct"] = (df["low"] - c) / c
    feat["close_ret"] = c.pct_change()
    # volume z-score (rolling 60)
    vol_ma = df["volume"].rolling(60).mean()
    vol_std = df["volume"].rolling(60).std().replace(0, 1)
    feat["vol_z"] = (df["volume"] - vol_ma) / vol_std

    # --- RSI ---
    feat["rsi"] = _rsi(c, 14) / 100.0  # normalise to 0-1

    # --- ATR / close ---
    feat["atr_pct"] = _atr(df["high"], df["low"], c, 14) / c

    # --- MA position (price relative to MA) ---
    for w in [20, 50, 200]:
        ma = c.rolling(w).mean()
        feat[f"ma{w}_pos"] = (c - ma) / ma

    # --- Momentum (return over N bars) ---
    for n in [1, 4, 12]:
        feat[f"mom_{n}"] = c.pct_change(n)

    # --- Time features (sin/cos of hour-of-day and day-of-week) ---
    hour = df.index.hour
    dow = df.index.dayofweek
    feat["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    feat["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    feat["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    feat["dow_cos"] = np.cos(2 * np.pi * dow / 7)

    # --- Target: next bar direction ---
    future_ret = c.shift(-1) / c - 1
    target = (future_ret > 0).astype(int)

    # Drop NaN rows
    valid = feat.dropna().index.intersection(target.dropna().index)
    feat = feat.loc[valid]
    target = target.loc[valid]

    # Replace any remaining inf/nan with 0
    feat = feat.replace([np.inf, -np.inf], 0).fillna(0)

    n_features = feat.shape[1]
    print(f"[Features] {n_features} dims, {len(feat)} valid bars")

    # Build sequences
    feat_arr = feat.values.astype(np.float32)
    tgt_arr = target.values.astype(np.float32)
    dates_arr = feat.index

    X_list, y_list, d_list = [], [], []
    for i in range(SEQ_LEN, len(feat_arr)):
        X_list.append(feat_arr[i - SEQ_LEN: i])
        y_list.append(tgt_arr[i])
        d_list.append(dates_arr[i])

    X = np.stack(X_list)
    y = np.array(y_list)
    dates = pd.DatetimeIndex(d_list)

    print(f"[Sequences] {X.shape[0]} samples, seq_len={SEQ_LEN}, "
          f"features={X.shape[2]}")
    return X, y, dates


# ---------------------------------------------------------------------------
# Walk-forward training
# ---------------------------------------------------------------------------
def walk_forward_train(X: np.ndarray, y: np.ndarray,
                       dates: pd.DatetimeIndex):
    """Walk-forward: TRAIN_MONTHS train -> TEST_MONTHS test, sliding."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Device] {device}")

    all_months = sorted(pd.Series(dates).dt.to_period("M").unique())
    print(f"[Walk-Forward] Total months: {len(all_months)}")

    results = []
    best_model_state = None
    best_auc = 0.0

    fold = 0
    start_idx = 0

    while start_idx + TRAIN_MONTHS + TEST_MONTHS <= len(all_months):
        fold += 1
        train_periods = all_months[start_idx: start_idx + TRAIN_MONTHS]
        test_periods = all_months[start_idx + TRAIN_MONTHS:
                                  start_idx + TRAIN_MONTHS + TEST_MONTHS]

        train_mask = pd.Series(dates).dt.to_period("M").isin(train_periods).values
        test_mask = pd.Series(dates).dt.to_period("M").isin(test_periods).values

        X_train, y_train = X[train_mask], y[train_mask]
        X_test, y_test = X[test_mask], y[test_mask]

        if len(X_train) < 100 or len(X_test) < 10:
            start_idx += TEST_MONTHS
            continue

        # Normalise per-feature using train stats
        mean = X_train.reshape(-1, X_train.shape[-1]).mean(axis=0)
        std = X_train.reshape(-1, X_train.shape[-1]).std(axis=0)
        std[std < 1e-8] = 1.0

        X_tr_n = (X_train - mean) / std
        X_te_n = (X_test - mean) / std

        train_ds = TensorDataset(
            torch.tensor(X_tr_n, dtype=torch.float32),
            torch.tensor(y_train, dtype=torch.float32),
        )
        train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)

        model = DirectionLSTM(input_dim=X.shape[2]).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=LR)
        criterion = nn.BCEWithLogitsLoss()

        # --- Training with early stopping ---
        best_val_loss = float("inf")
        wait = 0
        best_ep_state = None

        # Use last 15% of train for validation
        val_split = int(len(X_tr_n) * 0.85)
        X_val_split = torch.tensor(X_tr_n[val_split:], dtype=torch.float32).to(device)
        y_val_split = torch.tensor(y_train[val_split:], dtype=torch.float32).to(device)

        train_ds_inner = TensorDataset(
            torch.tensor(X_tr_n[:val_split], dtype=torch.float32),
            torch.tensor(y_train[:val_split], dtype=torch.float32),
        )
        train_dl_inner = DataLoader(train_ds_inner, batch_size=BATCH_SIZE,
                                    shuffle=True)

        for epoch in range(1, EPOCHS + 1):
            model.train()
            epoch_loss = 0.0
            n_batch = 0
            for xb, yb in train_dl_inner:
                xb, yb = xb.to(device), yb.to(device)
                optimizer.zero_grad()
                logits = model(xb).squeeze(-1)
                loss = criterion(logits, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                epoch_loss += loss.item()
                n_batch += 1

            # Validation loss
            model.eval()
            with torch.no_grad():
                val_logits = model(X_val_split).squeeze(-1)
                val_loss = criterion(val_logits, y_val_split).item()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_ep_state = {k: v.cpu().clone()
                                 for k, v in model.state_dict().items()}
                wait = 0
            else:
                wait += 1

            if fold <= 3 and epoch % 5 == 0:
                print(f"  Fold {fold} Epoch {epoch:2d}  "
                      f"train_loss={epoch_loss / n_batch:.4f}  "
                      f"val_loss={val_loss:.4f}")

            if wait >= PATIENCE:
                break

        # Restore best epoch
        if best_ep_state:
            model.load_state_dict(best_ep_state)

        # --- Evaluate on test ---
        model.eval()
        with torch.no_grad():
            X_te_t = torch.tensor(X_te_n, dtype=torch.float32).to(device)
            logits = model(X_te_t).squeeze(-1)
            probs = torch.sigmoid(logits).cpu().numpy()
            preds = (probs >= 0.5).astype(int)

        acc = (preds == y_test).mean()

        # AUC
        try:
            from sklearn.metrics import roc_auc_score
            auc = roc_auc_score(y_test, probs)
        except Exception:
            # Manual AUC if sklearn unavailable
            auc = _manual_auc(y_test, probs)

        # High-confidence accuracy (prob > 0.6 or < 0.4)
        hc_mask = (probs > 0.6) | (probs < 0.4)
        hc_acc = (preds[hc_mask] == y_test[hc_mask]).mean() if hc_mask.sum() > 5 else np.nan
        hc_ratio = hc_mask.mean()

        period_str = str(test_periods[0])
        results.append({
            "fold": fold,
            "test_period": period_str,
            "n_train": len(X_tr_n),
            "n_test": len(X_test),
            "accuracy": acc,
            "auc": auc,
            "hc_accuracy": hc_acc,
            "hc_ratio": hc_ratio,
        })

        print(f"Fold {fold:2d} | {period_str} | "
              f"Acc={acc:.3f}  AUC={auc:.3f}  "
              f"HC_Acc={hc_acc:.3f} ({hc_ratio:.0%}) | "
              f"train={len(X_tr_n)} test={len(X_test)}")

        if auc > best_auc:
            best_auc = auc
            best_model_state = {k: v.cpu().clone()
                                for k, v in model.state_dict().items()}

        start_idx += TEST_MONTHS

    return results, best_model_state


def _manual_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Simple AUC calculation without sklearn."""
    pos = y_score[y_true == 1]
    neg = y_score[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    n = 0
    total = 0
    for p in pos:
        total += len(neg)
        n += (p > neg).sum() + 0.5 * (p == neg).sum()
    return n / total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 65)
    print("  BTC 4H Direction LSTM Predictor  (Walk-Forward)")
    print("=" * 65)

    df = load_btc_4h()
    X, y, dates = compute_features(df)

    print(f"\n[Target distribution] up={y.mean():.3f}  down={1 - y.mean():.3f}\n")

    results, best_state = walk_forward_train(X, y, dates)

    if not results:
        print("No valid walk-forward folds. Check data range.")
        return

    # --- Summary table ---
    res_df = pd.DataFrame(results)
    print("\n" + "=" * 65)
    print("  Walk-Forward Results Summary")
    print("=" * 65)
    print(res_df.to_string(index=False, float_format="%.3f"))

    print(f"\n{'Metric':<20} {'Value':>10}")
    print("-" * 32)
    print(f"{'Avg Accuracy':<20} {res_df['accuracy'].mean():>10.3f}")
    print(f"{'Avg AUC':<20} {res_df['auc'].mean():>10.3f}")
    print(f"{'Avg HC Accuracy':<20} {res_df['hc_accuracy'].mean():>10.3f}")
    print(f"{'Avg HC Ratio':<20} {res_df['hc_ratio'].mean():>10.1%}")
    print(f"{'Best AUC':<20} {res_df['auc'].max():>10.3f}")
    print(f"{'Worst AUC':<20} {res_df['auc'].min():>10.3f}")
    print(f"{'Total Folds':<20} {len(results):>10d}")

    # --- Save best model ---
    if best_state:
        save_obj = {
            "model_state_dict": best_state,
            "input_dim": X.shape[2],
            "hidden_dim": HIDDEN_DIM,
            "num_layers": NUM_LAYERS,
            "seq_len": SEQ_LEN,
            "config": {
                "lr": LR, "batch_size": BATCH_SIZE,
                "epochs": EPOCHS, "patience": PATIENCE,
                "train_months": TRAIN_MONTHS, "test_months": TEST_MONTHS,
            },
        }
        torch.save(save_obj, str(MODEL_PATH))
        print(f"\n[Saved] Best model -> {MODEL_PATH}")

    print("\nDone.")


if __name__ == "__main__":
    main()
