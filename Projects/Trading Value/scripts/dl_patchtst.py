"""BTC PatchTST + RevIN + Triple Barrier  (Walk-Forward, Multi-Timeframe).

Gemini 2.5 Pro analysis-driven model for BTC OOS accuracy 55%+.
- Triple Barrier Labeling instead of binary up/down
- RevIN (Reversible Instance Normalization) for non-stationarity
- PatchTST with separate encoders for 15m and 1H timeframes
- 4H outcome prediction via walk-forward validation
"""

import subprocess
import sys
import sqlite3
import math
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
# Paths & Hyperparameters
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sim_1m.sqlite"
MODEL_PATH = Path(__file__).resolve().parent.parent / "data" / "dl_btc_patchtst.pt"

# PatchTST config
SEQ_LEN_15M = 96   # 96 x 15m = 24 hours
SEQ_LEN_1H = 24    # 24 x 1H  = 24 hours
PATCH_LEN = 8
STRIDE = 4
D_MODEL = 64
NHEAD = 4
NUM_LAYERS = 2
DROPOUT = 0.2

# Training config
LR = 0.0003
WEIGHT_DECAY = 0.01
BATCH_SIZE = 64
EPOCHS = 30
PATIENCE = 5
LABEL_SMOOTHING = 0.1

# Walk-forward config
TRAIN_MONTHS = 6
TEST_MONTHS = 1

# Triple barrier config
TB_UPPER_MULT = 1.5
TB_LOWER_MULT = 1.5
TB_MAX_BARS = 3  # max 4H bars (= 12 hours)


# ---------------------------------------------------------------------------
# Triple Barrier Labeling
# ---------------------------------------------------------------------------
def triple_barrier_labels(close: np.ndarray, atr: np.ndarray,
                          upper_mult: float = TB_UPPER_MULT,
                          lower_mult: float = TB_LOWER_MULT,
                          max_bars: int = TB_MAX_BARS):
    """Assign labels based on which barrier is hit first.

    For each bar i:
      - Upper barrier: close[i] + upper_mult * atr[i]  -> label 1 (profit)
      - Lower barrier: close[i] - lower_mult * atr[i]  -> label 0 (stop loss)
      - Time barrier:  max_bars bars without either hit -> label 2 (timeout)

    Returns:
        labels: np.ndarray of shape (n,) with values 0, 1, or 2
    """
    n = len(close)
    labels = np.full(n, 2, dtype=np.int64)  # default timeout

    for i in range(n):
        if np.isnan(atr[i]) or atr[i] < 1e-12:
            continue
        upper = close[i] + upper_mult * atr[i]
        lower = close[i] - lower_mult * atr[i]
        end = min(i + max_bars + 1, n)

        for j in range(i + 1, end):
            if close[j] >= upper:
                labels[i] = 1
                break
            elif close[j] <= lower:
                labels[i] = 0
                break

    return labels


# ---------------------------------------------------------------------------
# RevIN (Reversible Instance Normalization)
# ---------------------------------------------------------------------------
class RevIN(nn.Module):
    """Remove instance mean/variance before encoder, add back if needed."""

    def __init__(self, num_features: int, affine: bool = True, eps: float = 1e-5):
        super().__init__()
        self.num_features = num_features
        self.affine = affine
        self.eps = eps
        if affine:
            self.gamma = nn.Parameter(torch.ones(1, 1, num_features))
            self.beta = nn.Parameter(torch.zeros(1, 1, num_features))

    def forward(self, x: torch.Tensor, mode: str = "norm") -> torch.Tensor:
        """x: (batch, seq_len, features)."""
        if mode == "norm":
            self._mean = x.mean(dim=1, keepdim=True).detach()
            self._std = (x.var(dim=1, keepdim=True, unbiased=False) + self.eps).sqrt().detach()
            x = (x - self._mean) / self._std
            if self.affine:
                x = x * self.gamma + self.beta
        elif mode == "denorm":
            if self.affine:
                x = (x - self.beta) / (self.gamma + self.eps)
            x = x * self._std + self._mean
        return x


# ---------------------------------------------------------------------------
# PatchTST Encoder
# ---------------------------------------------------------------------------
class PatchTSTEncoder(nn.Module):
    """Single-timeframe PatchTST encoder.

    Input:  (batch, seq_len, input_dim)
    Output: (batch, d_model)  -- pooled representation
    """

    def __init__(self, input_dim: int, seq_len: int,
                 patch_len: int = PATCH_LEN, stride: int = STRIDE,
                 d_model: int = D_MODEL, nhead: int = NHEAD,
                 num_layers: int = NUM_LAYERS, dropout: float = DROPOUT):
        super().__init__()
        self.patch_len = patch_len
        self.stride = stride

        # Number of patches
        self.n_patches = (seq_len - patch_len) // stride + 1

        # RevIN per feature
        self.revin = RevIN(input_dim, affine=True)

        # Linear projection: each patch (patch_len * input_dim) -> d_model
        self.patch_proj = nn.Linear(patch_len * input_dim, d_model)

        # Learnable positional embedding
        self.pos_embed = nn.Parameter(torch.randn(1, self.n_patches, d_model) * 0.02)

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
            activation="gelu",
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.dropout = nn.Dropout(dropout)
        self.norm = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (batch, seq_len, input_dim) -> (batch, d_model)."""
        # 1. RevIN normalization
        x = self.revin(x, mode="norm")

        # 2. Extract patches: (batch, n_patches, patch_len * input_dim)
        batch_size = x.shape[0]
        patches = []
        for i in range(self.n_patches):
            start = i * self.stride
            end = start + self.patch_len
            patch = x[:, start:end, :]  # (batch, patch_len, input_dim)
            patches.append(patch.reshape(batch_size, -1))  # (batch, patch_len * input_dim)
        patches = torch.stack(patches, dim=1)  # (batch, n_patches, patch_len * input_dim)

        # 3. Linear projection + positional embedding
        z = self.patch_proj(patches)  # (batch, n_patches, d_model)
        z = z + self.pos_embed

        # 4. Transformer encoder
        z = self.transformer(z)  # (batch, n_patches, d_model)

        # 5. Pool: mean over patches
        z = z.mean(dim=1)  # (batch, d_model)
        z = self.norm(self.dropout(z))
        return z


# ---------------------------------------------------------------------------
# Multi-Timeframe PatchTST Model
# ---------------------------------------------------------------------------
class MultiTFPatchTST(nn.Module):
    """Two PatchTST encoders (15m + 1H) -> classification head."""

    def __init__(self, input_dim_15m: int, input_dim_1h: int,
                 d_model: int = D_MODEL, dropout: float = DROPOUT):
        super().__init__()
        self.enc_15m = PatchTSTEncoder(
            input_dim=input_dim_15m, seq_len=SEQ_LEN_15M,
            patch_len=PATCH_LEN, stride=STRIDE,
            d_model=d_model, nhead=NHEAD, num_layers=NUM_LAYERS,
            dropout=dropout,
        )
        self.enc_1h = PatchTSTEncoder(
            input_dim=input_dim_1h, seq_len=SEQ_LEN_1H,
            patch_len=PATCH_LEN, stride=STRIDE,
            d_model=d_model, nhead=NHEAD, num_layers=NUM_LAYERS,
            dropout=dropout,
        )
        # Classification head: concatenated embeddings -> 2 classes (0=stop, 1=profit)
        self.head = nn.Sequential(
            nn.Linear(d_model * 2, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, 2),
        )

    def forward(self, x_15m: torch.Tensor, x_1h: torch.Tensor) -> torch.Tensor:
        """
        x_15m: (batch, 96, feat_15m)
        x_1h:  (batch, 24, feat_1h)
        Returns: (batch, 2) logits
        """
        z_15m = self.enc_15m(x_15m)  # (batch, d_model)
        z_1h = self.enc_1h(x_1h)     # (batch, d_model)
        z = torch.cat([z_15m, z_1h], dim=-1)  # (batch, d_model * 2)
        return self.head(z)


# ---------------------------------------------------------------------------
# Data loading helpers
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


def load_ohlcv(freq: str) -> pd.DataFrame:
    """Load BTCUSDT 1m from sqlite, resample to given frequency."""
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

    ohlcv = df.resample(freq).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()

    return ohlcv


def compute_features_tf(df: pd.DataFrame, is_15m: bool = True) -> pd.DataFrame:
    """Build 12 features for a single timeframe.

    Features:
      1. log_return       2. high_pct        3. low_pct
      4. close_pct        5. volume_zscore   6. RSI(14) / 100
      7. ATR / close      8. MA(20) pos      9. MA(50) pos
     10. momentum 4-bar  11. momentum 12-bar 12. hour_sin (15m only, 0 for 1H)
    """
    c = df["close"]
    feat = pd.DataFrame(index=df.index)

    # 1. log return
    feat["log_return"] = np.log(c / c.shift(1))

    # 2-4. OHLC pct relative to close
    feat["high_pct"] = (df["high"] - c) / c
    feat["low_pct"] = (df["low"] - c) / c
    feat["close_pct"] = c.pct_change()

    # 5. volume z-score (rolling 60)
    vol_ma = df["volume"].rolling(60).mean()
    vol_std = df["volume"].rolling(60).std().replace(0, 1)
    feat["volume_zscore"] = (df["volume"] - vol_ma) / vol_std

    # 6. RSI(14) normalized
    feat["rsi_norm"] = _rsi(c, 14) / 100.0

    # 7. ATR / close
    feat["atr_pct"] = _atr(df["high"], df["low"], c, 14) / c

    # 8-9. MA position
    for w in [20, 50]:
        ma = c.rolling(w).mean()
        feat[f"ma{w}_pos"] = (c - ma) / ma

    # 10-11. Momentum
    for n in [4, 12]:
        feat[f"mom_{n}"] = c.pct_change(n)

    # 12. hour_sin (15m only)
    if is_15m:
        hour = df.index.hour + df.index.minute / 60.0
        feat["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    else:
        feat["hour_sin"] = 0.0

    return feat


# ---------------------------------------------------------------------------
# Build aligned multi-TF samples with triple barrier labels
# ---------------------------------------------------------------------------
def build_samples():
    """Build aligned (X_15m, X_1h, labels, dates) arrays.

    Alignment strategy:
    - Resample to 4H for labeling (triple barrier on 4H close)
    - For each 4H bar, gather the preceding 96 x 15m bars and 24 x 1H bars
    """
    print("[Data] Loading 15m, 1H, 4H candles...")
    df_15m = load_ohlcv("15min")
    df_1h = load_ohlcv("1h")
    df_4h = load_ohlcv("4h")

    print(f"  15m: {len(df_15m)} bars  ({df_15m.index[0].date()} ~ {df_15m.index[-1].date()})")
    print(f"  1H:  {len(df_1h)} bars  ({df_1h.index[0].date()} ~ {df_1h.index[-1].date()})")
    print(f"  4H:  {len(df_4h)} bars  ({df_4h.index[0].date()} ~ {df_4h.index[-1].date()})")

    # Compute features
    feat_15m = compute_features_tf(df_15m, is_15m=True)
    feat_1h = compute_features_tf(df_1h, is_15m=False)

    # Triple barrier labels on 4H
    close_4h = df_4h["close"].values
    atr_4h = _atr(df_4h["high"], df_4h["low"], df_4h["close"], 14).values
    tb_labels = triple_barrier_labels(close_4h, atr_4h)

    print(f"\n[Triple Barrier] Total 4H bars: {len(tb_labels)}")
    print(f"  Profit (1): {(tb_labels == 1).sum()}  "
          f"Stop (0): {(tb_labels == 0).sum()}  "
          f"Timeout (2): {(tb_labels == 2).sum()}")

    # Drop NaN features
    feat_15m = feat_15m.replace([np.inf, -np.inf], np.nan).dropna()
    feat_1h = feat_1h.replace([np.inf, -np.inf], np.nan).dropna()

    feat_15m_arr = feat_15m.values.astype(np.float32)
    feat_1h_arr = feat_1h.values.astype(np.float32)

    n_feat_15m = feat_15m.shape[1]
    n_feat_1h = feat_1h.shape[1]

    print(f"\n[Features] 15m: {n_feat_15m} dims, 1H: {n_feat_1h} dims")

    # Build samples aligned to 4H bars
    X_15m_list, X_1h_list, y_list, date_list = [], [], [], []

    # Pre-compute index mappings for efficiency
    idx_15m = feat_15m.index
    idx_1h = feat_1h.index

    for idx_4h in range(len(df_4h)):
        label = tb_labels[idx_4h]
        bar_time = df_4h.index[idx_4h]

        # Get preceding 15m bars using searchsorted (O(log n), no copy)
        end_15m = idx_15m.searchsorted(bar_time, side="right")
        if end_15m < SEQ_LEN_15M:
            continue
        available_15m = feat_15m_arr[end_15m - SEQ_LEN_15M:end_15m]

        # Get preceding 1H bars
        end_1h = idx_1h.searchsorted(bar_time, side="right")
        if end_1h < SEQ_LEN_1H:
            continue
        seq_1h = feat_1h_arr[end_1h - SEQ_LEN_1H:end_1h]

        seq_15m = available_15m  # already sliced to SEQ_LEN_15M

        X_15m_list.append(seq_15m)
        X_1h_list.append(seq_1h)
        y_list.append(label)
        date_list.append(bar_time)

    X_15m = np.stack(X_15m_list)  # (N, 96, feat_15m)
    X_1h = np.stack(X_1h_list)    # (N, 24, feat_1h)
    y = np.array(y_list, dtype=np.int64)
    dates = pd.DatetimeIndex(date_list)

    print(f"\n[Samples] Total: {len(y)}  "
          f"(Profit: {(y == 1).sum()}, Stop: {(y == 0).sum()}, Timeout: {(y == 2).sum()})")
    print(f"  X_15m: {X_15m.shape}, X_1h: {X_1h.shape}")

    return X_15m, X_1h, y, dates


# ---------------------------------------------------------------------------
# Label-Smoothed CrossEntropy
# ---------------------------------------------------------------------------
class LabelSmoothedCE(nn.Module):
    def __init__(self, num_classes: int = 2, smoothing: float = LABEL_SMOOTHING):
        super().__init__()
        self.num_classes = num_classes
        self.smoothing = smoothing
        self.confidence = 1.0 - smoothing

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        log_probs = torch.log_softmax(logits, dim=-1)
        # One-hot with smoothing
        with torch.no_grad():
            true_dist = torch.full_like(log_probs, self.smoothing / (self.num_classes - 1))
            true_dist.scatter_(1, targets.unsqueeze(1), self.confidence)
        return (-true_dist * log_probs).sum(dim=-1).mean()


# ---------------------------------------------------------------------------
# AUC helper
# ---------------------------------------------------------------------------
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
    return float(n / total)


# ---------------------------------------------------------------------------
# Walk-Forward Training
# ---------------------------------------------------------------------------
def walk_forward_train(X_15m: np.ndarray, X_1h: np.ndarray,
                       y: np.ndarray, dates: pd.DatetimeIndex):
    """Walk-forward: TRAIN_MONTHS train -> TEST_MONTHS test, sliding."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n[Device] {device}")

    all_months = sorted(pd.Series(dates).dt.to_period("M").unique())
    print(f"[Walk-Forward] Total months: {len(all_months)}")

    results = []
    best_model_state = None
    best_auc = 0.0

    n_feat_15m = X_15m.shape[2]
    n_feat_1h = X_1h.shape[2]

    fold = 0
    start_idx = 0

    while start_idx + TRAIN_MONTHS + TEST_MONTHS <= len(all_months):
        fold += 1
        train_periods = all_months[start_idx: start_idx + TRAIN_MONTHS]
        test_periods = all_months[start_idx + TRAIN_MONTHS:
                                  start_idx + TRAIN_MONTHS + TEST_MONTHS]

        periods_series = pd.Series(dates).dt.to_period("M")
        train_mask = periods_series.isin(train_periods).values
        test_mask = periods_series.isin(test_periods).values

        # Filter out timeout labels (2) from training and test
        train_valid = train_mask & (y != 2)
        test_valid = test_mask & (y != 2)

        X_15m_train, X_1h_train = X_15m[train_valid], X_1h[train_valid]
        X_15m_test, X_1h_test = X_15m[test_valid], X_1h[test_valid]
        y_train, y_test = y[train_valid], y[test_valid]

        if len(y_train) < 100 or len(y_test) < 10:
            start_idx += TEST_MONTHS
            continue

        # --- Create model ---
        model = MultiTFPatchTST(
            input_dim_15m=n_feat_15m, input_dim_1h=n_feat_1h,
            d_model=D_MODEL, dropout=DROPOUT,
        ).to(device)

        optimizer = torch.optim.AdamW(
            model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY,
        )
        scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer, T_0=10, T_mult=2,
        )
        criterion = LabelSmoothedCE(num_classes=2, smoothing=LABEL_SMOOTHING)

        # --- Validation split (last 15% of train) ---
        val_split = int(len(y_train) * 0.85)

        X_15m_tr = torch.tensor(X_15m_train[:val_split], dtype=torch.float32)
        X_1h_tr = torch.tensor(X_1h_train[:val_split], dtype=torch.float32)
        y_tr = torch.tensor(y_train[:val_split], dtype=torch.long)

        X_15m_val = torch.tensor(X_15m_train[val_split:], dtype=torch.float32).to(device)
        X_1h_val = torch.tensor(X_1h_train[val_split:], dtype=torch.float32).to(device)
        y_val = torch.tensor(y_train[val_split:], dtype=torch.long).to(device)

        train_ds = TensorDataset(X_15m_tr, X_1h_tr, y_tr)
        train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)

        # --- Training loop with early stopping ---
        best_val_loss = float("inf")
        wait = 0
        best_ep_state = None

        for epoch in range(1, EPOCHS + 1):
            model.train()
            epoch_loss = 0.0
            n_batch = 0
            for xb_15m, xb_1h, yb in train_dl:
                xb_15m = xb_15m.to(device)
                xb_1h = xb_1h.to(device)
                yb = yb.to(device)

                optimizer.zero_grad()
                logits = model(xb_15m, xb_1h)
                loss = criterion(logits, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                epoch_loss += loss.item()
                n_batch += 1

            scheduler.step()

            # Validation
            model.eval()
            with torch.no_grad():
                val_logits = model(X_15m_val, X_1h_val)
                val_loss = criterion(val_logits, y_val).item()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_ep_state = {k: v.cpu().clone()
                                 for k, v in model.state_dict().items()}
                wait = 0
            else:
                wait += 1

            if fold <= 3 and epoch % 5 == 0:
                print(f"  Fold {fold} Epoch {epoch:2d}  "
                      f"train_loss={epoch_loss / max(n_batch, 1):.4f}  "
                      f"val_loss={val_loss:.4f}")

            if wait >= PATIENCE:
                break

        # Restore best epoch
        if best_ep_state:
            model.load_state_dict(best_ep_state)

        # --- Evaluate on OOS test ---
        model.eval()
        with torch.no_grad():
            X_15m_te = torch.tensor(X_15m_test, dtype=torch.float32).to(device)
            X_1h_te = torch.tensor(X_1h_test, dtype=torch.float32).to(device)
            logits = model(X_15m_te, X_1h_te)
            probs = torch.softmax(logits, dim=-1)[:, 1].cpu().numpy()  # P(profit)
            preds = (probs >= 0.5).astype(int)

        y_test_binary = y_test.astype(int)
        acc = float((preds == y_test_binary).mean())

        # AUC
        try:
            from sklearn.metrics import roc_auc_score
            auc = float(roc_auc_score(y_test_binary, probs))
        except Exception:
            auc = _manual_auc(y_test_binary, probs)

        # High-confidence accuracy (prob > 0.6 or < 0.4)
        hc_mask = (probs > 0.6) | (probs < 0.4)
        hc_acc = float((preds[hc_mask] == y_test_binary[hc_mask]).mean()) if hc_mask.sum() > 5 else float("nan")
        hc_ratio = float(hc_mask.mean())

        period_str = str(test_periods[0])
        results.append({
            "fold": fold,
            "test_period": period_str,
            "n_train": len(y_train),
            "n_test": len(y_test),
            "accuracy": acc,
            "auc": auc,
            "hc_accuracy": hc_acc,
            "hc_ratio": hc_ratio,
        })

        print(f"Fold {fold:2d} | {period_str} | "
              f"Acc={acc:.3f}  AUC={auc:.3f}  "
              f"HC_Acc={hc_acc:.3f} ({hc_ratio:.0%}) | "
              f"train={len(y_train)} test={len(y_test)}")

        if auc > best_auc:
            best_auc = auc
            best_model_state = {k: v.cpu().clone()
                                for k, v in model.state_dict().items()}

        start_idx += TEST_MONTHS

    return results, best_model_state, n_feat_15m, n_feat_1h


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("  BTC PatchTST + RevIN + Triple Barrier  (Walk-Forward)")
    print("  Multi-Timeframe: 15m (96 bars) + 1H (24 bars) -> 4H outcome")
    print("=" * 70)

    X_15m, X_1h, y, dates = build_samples()

    # Only keep profit/stop for stats
    valid_mask = y != 2
    y_valid = y[valid_mask]
    print(f"\n[Label distribution (excl. timeout)] "
          f"Profit={y_valid.mean():.3f}  Stop={1 - y_valid.mean():.3f}\n")

    results, best_state, n_feat_15m, n_feat_1h = walk_forward_train(
        X_15m, X_1h, y, dates,
    )

    if not results:
        print("No valid walk-forward folds. Check data range.")
        return

    # --- Summary table ---
    res_df = pd.DataFrame(results)
    print("\n" + "=" * 70)
    print("  Walk-Forward Results Summary")
    print("=" * 70)
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

    target_hit = res_df["accuracy"].mean() >= 0.55
    print(f"\n{'TARGET 55%+ ACC':<20} {'HIT' if target_hit else 'MISS':>10}")

    # --- Save best model ---
    if best_state:
        save_obj = {
            "model_state_dict": best_state,
            "model_class": "MultiTFPatchTST",
            "input_dim_15m": n_feat_15m,
            "input_dim_1h": n_feat_1h,
            "seq_len_15m": SEQ_LEN_15M,
            "seq_len_1h": SEQ_LEN_1H,
            "config": {
                "patch_len": PATCH_LEN, "stride": STRIDE,
                "d_model": D_MODEL, "nhead": NHEAD,
                "num_layers": NUM_LAYERS, "dropout": DROPOUT,
                "lr": LR, "weight_decay": WEIGHT_DECAY,
                "batch_size": BATCH_SIZE, "epochs": EPOCHS,
                "patience": PATIENCE, "label_smoothing": LABEL_SMOOTHING,
                "train_months": TRAIN_MONTHS, "test_months": TEST_MONTHS,
                "tb_upper_mult": TB_UPPER_MULT, "tb_lower_mult": TB_LOWER_MULT,
                "tb_max_bars": TB_MAX_BARS,
            },
        }
        torch.save(save_obj, str(MODEL_PATH))
        print(f"\n[Saved] Best model -> {MODEL_PATH}")

    print("\nDone.")


if __name__ == "__main__":
    main()
