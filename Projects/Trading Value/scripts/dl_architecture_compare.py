"""
DL Architecture Comparison — BTC 4H from sim_1m.sqlite
Architectures: Simple LSTM, Bi-LSTM, GRU, Transformer, 1D-CNN
"""

import sqlite3
import time
import math
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import numpy as np

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sim_1m.sqlite"
SYMBOL = "BTCUSDT"
SEQ_LEN = 60
N_FEATURES = 12
BATCH_SIZE = 64
EPOCHS = 20
LR = 0.001
PATIENCE = 3
TRAIN_RATIO = 0.60
VAL_RATIO = 0.20
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ---------------------------------------------------------------------------
# Data loading: aggregate 1m → 4H OHLCV
# ---------------------------------------------------------------------------

def load_4h_ohlcv() -> np.ndarray:
    """Load BTCUSDT 1m rows and resample to 4H bars.
    Returns numpy array shape (N, 5): open, high, low, close, volume
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT timestamp, open, high, low, close, volume "
        "FROM ohlcv_1m WHERE symbol=? ORDER BY timestamp",
        (SYMBOL,),
    )
    rows = cur.fetchall()
    conn.close()

    # Each 4H bar = 240 1m candles
    BARS_PER_4H = 240
    n_full = len(rows) // BARS_PER_4H
    data = []
    for i in range(n_full):
        chunk = rows[i * BARS_PER_4H : (i + 1) * BARS_PER_4H]
        o = chunk[0][1]
        h = max(r[2] for r in chunk)
        l = min(r[3] for r in chunk)
        c = chunk[-1][4]
        v = sum(r[5] for r in chunk)
        data.append([o, h, l, c, v])
    return np.array(data, dtype=np.float32)

# ---------------------------------------------------------------------------
# Feature engineering (12-dim per bar)
# ---------------------------------------------------------------------------

def compute_features(ohlcv: np.ndarray) -> np.ndarray:
    """
    Features per bar (12-dim):
      0-4: OHLCV normalized (div by close of previous bar)
      5:   RSI(14)
      6:   ATR(14) normalized
      7:   MA20 position   (close / MA20 - 1)
      8:   MA50 position
      9:   MA200 position
      10:  momentum1       (close[t] / close[t-1] - 1)
      11:  padding zero (kept for N_FEATURES=12 alignment)
    """
    N = len(ohlcv)
    feats = np.zeros((N, N_FEATURES), dtype=np.float32)

    close = ohlcv[:, 3]

    # --- OHLCV normalized by previous close ---
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    for j, col in enumerate(range(5)):
        feats[:, j] = ohlcv[:, col] / prev_close

    # --- RSI(14) ---
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    # Wilder smoothing via EMA
    rsi_period = 14
    avg_gain = np.zeros(N, dtype=np.float32)
    avg_loss = np.zeros(N, dtype=np.float32)
    avg_gain[rsi_period] = gain[1:rsi_period+1].mean()
    avg_loss[rsi_period] = loss[1:rsi_period+1].mean()
    for i in range(rsi_period + 1, N):
        avg_gain[i] = (avg_gain[i-1] * (rsi_period - 1) + gain[i]) / rsi_period
        avg_loss[i] = (avg_loss[i-1] * (rsi_period - 1) + loss[i]) / rsi_period
    rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100.0)
    rsi = 100 - 100 / (1 + rs)
    feats[:, 5] = rsi / 100.0  # normalize to [0,1]

    # --- ATR(14) normalized ---
    high = ohlcv[:, 1]
    low_p = ohlcv[:, 2]
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    tr = np.maximum(high - low_p, np.maximum(np.abs(high - prev_c), np.abs(low_p - prev_c)))
    atr = np.zeros(N, dtype=np.float32)
    atr[rsi_period] = tr[1:rsi_period+1].mean()
    for i in range(rsi_period + 1, N):
        atr[i] = (atr[i-1] * (rsi_period - 1) + tr[i]) / rsi_period
    feats[:, 6] = atr / (close + 1e-8)

    # --- MA positions ---
    for ma_period, col_idx in [(20, 7), (50, 8), (200, 9)]:
        ma = np.zeros(N, dtype=np.float32)
        for i in range(N):
            start = max(0, i - ma_period + 1)
            ma[i] = close[start:i+1].mean()
        feats[:, col_idx] = close / (ma + 1e-8) - 1.0

    # --- Momentum 1 ---
    mom1 = np.roll(close, 1)
    mom1[0] = close[0]
    feats[:, 10] = close / (mom1 + 1e-8) - 1.0

    # feats[:, 11] stays zero (padding slot)
    return feats


def build_sequences(feats: np.ndarray):
    """Build (X, y) where y=1 if next close > current close."""
    N = len(feats)
    # We need features AND the raw close for labeling
    # close was already embedded in feats[:, 3] as normed, so recompute label separately
    # Use momentum1 = close[t]/close[t-1]-1 sign of NEXT bar for label
    # Label: next bar's momentum1 > 0  (feats[i+1, 10] > 0)
    X, y = [], []
    for i in range(SEQ_LEN, N - 1):
        X.append(feats[i - SEQ_LEN : i])       # shape (60, 12)
        y.append(1.0 if feats[i + 1, 10] > 0 else 0.0)  # next bar up?
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def split_dataset(X: np.ndarray, y: np.ndarray):
    N = len(X)
    n_train = int(N * TRAIN_RATIO)
    n_val = int(N * VAL_RATIO)
    X_train, y_train = X[:n_train], y[:n_train]
    X_val, y_val = X[n_train:n_train+n_val], y[n_train:n_train+n_val]
    X_test, y_test = X[n_train+n_val:], y[n_train+n_val:]
    return (X_train, y_train), (X_val, y_val), (X_test, y_test)


def make_loader(X, y, shuffle=False) -> DataLoader:
    ds = TensorDataset(
        torch.tensor(X, dtype=torch.float32),
        torch.tensor(y, dtype=torch.float32),
    )
    return DataLoader(ds, batch_size=BATCH_SIZE, shuffle=shuffle)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SimpleLSTM(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(N_FEATURES, 64, batch_first=True)
        self.fc = nn.Linear(64, 1)

    def forward(self, x):
        _, (h, _) = self.lstm(x)
        return self.fc(h[-1]).squeeze(-1)


class BiLSTM(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(N_FEATURES, 64, batch_first=True, bidirectional=True)
        self.fc = nn.Linear(128, 1)

    def forward(self, x):
        _, (h, _) = self.lstm(x)
        # h: (2, B, 64) → cat forward+backward
        h_cat = torch.cat([h[0], h[1]], dim=-1)
        return self.fc(h_cat).squeeze(-1)


class GRUModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.gru = nn.GRU(N_FEATURES, 64, num_layers=2, batch_first=True, dropout=0.1)
        self.fc = nn.Linear(64, 1)

    def forward(self, x):
        _, h = self.gru(x)
        return self.fc(h[-1]).squeeze(-1)


class TransformerModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.input_proj = nn.Linear(N_FEATURES, 64)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=64, nhead=4, dim_feedforward=128,
            dropout=0.1, batch_first=True
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=2)
        self.fc = nn.Linear(64, 1)

    def forward(self, x):
        x = self.input_proj(x)                  # (B, T, 64)
        x = self.encoder(x)                     # (B, T, 64)
        x = x.mean(dim=1)                       # global avg pool over time
        return self.fc(x).squeeze(-1)


class CNN1D(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(N_FEATURES, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
        )
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Linear(128, 1)

    def forward(self, x):
        x = x.permute(0, 2, 1)      # (B, F, T)
        x = self.conv(x)             # (B, 128, T)
        x = self.pool(x).squeeze(-1) # (B, 128)
        return self.fc(x).squeeze(-1)

# ---------------------------------------------------------------------------
# Training / Evaluation helpers
# ---------------------------------------------------------------------------

def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def train_epoch(model, loader, optimizer, criterion) -> float:
    model.train()
    total_loss, correct, total = 0.0, 0, 0
    for xb, yb in loader:
        xb, yb = xb.to(DEVICE), yb.to(DEVICE)
        optimizer.zero_grad()
        logits = model(xb)
        loss = criterion(logits, yb)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * len(yb)
        preds = (torch.sigmoid(logits) >= 0.5).float()
        correct += (preds == yb).sum().item()
        total += len(yb)
    return correct / total


def eval_epoch(model, loader) -> tuple[float, list, list]:
    model.eval()
    correct, total = 0, 0
    all_probs, all_labels = [], []
    with torch.no_grad():
        for xb, yb in loader:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            logits = model(xb)
            probs = torch.sigmoid(logits)
            preds = (probs >= 0.5).float()
            correct += (preds == yb).sum().item()
            total += len(yb)
            all_probs.extend(probs.cpu().numpy().tolist())
            all_labels.extend(yb.cpu().numpy().tolist())
    return correct / total, all_probs, all_labels


def compute_auc(probs, labels) -> float:
    """Compute ROC-AUC without sklearn."""
    paired = sorted(zip(probs, labels), key=lambda x: -x[0])
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5
    tp, fp = 0, 0
    prev_fpr = 0.0
    auc = 0.0
    for _, label in paired:
        if label == 1:
            tp += 1
        else:
            fp += 1
        fpr = fp / n_neg
        tpr = tp / n_pos
        auc += tpr * (fpr - prev_fpr)
        prev_fpr = fpr
    return auc


def run_experiment(name: str, model: nn.Module, train_loader, val_loader, test_loader) -> dict:
    model = model.to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.BCEWithLogitsLoss()

    best_val_acc = 0.0
    best_state = None
    no_improve = 0
    train_acc_final = 0.0

    t0 = time.time()
    for epoch in range(EPOCHS):
        train_acc = train_epoch(model, train_loader, optimizer, criterion)
        val_acc, _, _ = eval_epoch(model, val_loader)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            no_improve = 0
            train_acc_final = train_acc
        else:
            no_improve += 1

        if no_improve >= PATIENCE:
            break

    elapsed = time.time() - t0

    # Restore best weights
    if best_state is not None:
        model.load_state_dict(best_state)

    test_acc, test_probs, test_labels = eval_epoch(model, test_loader)
    auc = compute_auc(test_probs, test_labels)

    return {
        "name": name,
        "params": count_params(model),
        "train_acc": train_acc_final,
        "val_acc": best_val_acc,
        "test_acc": test_acc,
        "auc": auc,
        "time": elapsed,
    }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Device: {DEVICE}")
    print("Loading and resampling 4H OHLCV from sim_1m.sqlite ...")
    ohlcv = load_4h_ohlcv()
    print(f"  4H bars: {len(ohlcv)}")

    print("Computing features ...")
    feats = compute_features(ohlcv)

    print("Building sequences ...")
    X, y = build_sequences(feats)
    print(f"  Sequences: {len(X)}, class balance: {y.mean():.3f}")

    (X_tr, y_tr), (X_val, y_val), (X_te, y_te) = split_dataset(X, y)
    print(f"  Train={len(X_tr)}  Val={len(X_val)}  Test={len(X_te)}")

    train_loader = make_loader(X_tr, y_tr, shuffle=True)
    val_loader   = make_loader(X_val, y_val)
    test_loader  = make_loader(X_te, y_te)

    architectures = [
        ("LSTM",        SimpleLSTM()),
        ("Bi-LSTM",     BiLSTM()),
        ("GRU",         GRUModel()),
        ("Transformer", TransformerModel()),
        ("1D-CNN",      CNN1D()),
    ]

    results = []
    for name, model in architectures:
        print(f"\n[{name}] Training ...")
        r = run_experiment(name, model, train_loader, val_loader, test_loader)
        results.append(r)
        print(
            f"  Params={r['params']:,}  "
            f"Train={r['train_acc']*100:.1f}%  "
            f"Val={r['val_acc']*100:.1f}%  "
            f"Test={r['test_acc']*100:.1f}%  "
            f"AUC={r['auc']:.3f}  "
            f"Time={r['time']:.0f}s"
        )

    # ---------------------------------------------------------------------------
    # Summary table
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(
        f"{'Architecture':<16}"
        f"{'Params':>8}"
        f"{'Train_Acc':>12}"
        f"{'Val_Acc':>10}"
        f"{'Test_Acc':>10}"
        f"{'AUC':>8}"
        f"{'Time(s)':>9}"
    )
    print("-" * 80)
    for r in results:
        print(
            f"{r['name']:<16}"
            f"{r['params']:>8,}"
            f"{r['train_acc']*100:>11.1f}%"
            f"{r['val_acc']*100:>9.1f}%"
            f"{r['test_acc']*100:>9.1f}%"
            f"{r['auc']:>8.3f}"
            f"{r['time']:>8.0f}s"
        )
    print("=" * 80)

    # ---------------------------------------------------------------------------
    # Recommendation
    # ---------------------------------------------------------------------------
    # Score: weighted combination of test_acc (50%) + AUC (50%)
    scored = [(r, 0.5 * r["test_acc"] + 0.5 * r["auc"]) for r in results]
    scored.sort(key=lambda x: -x[1])
    best = scored[0][0]

    # Rationale per architecture
    notes = {
        "LSTM":        "단순하고 빠름. 순차 패턴 기본 포착. 과적합 위험 낮음.",
        "Bi-LSTM":     "미래 컨텍스트 포함 — 실시간 추론 시 비현실적이지만 오프라인 특징 추출에 유리.",
        "GRU":         "LSTM보다 파라미터 적고 빠름. 실용적 기준점.",
        "Transformer": "장기 의존성 포착 우수. 데이터 적을 때 오버피팅 주의.",
        "1D-CNN":      "국소 패턴(캔들 군집) 포착 강점. 빠른 추론.",
    }

    print(f"\n★ 권장 아키텍처: {best['name']}")
    print(f"  Score(0.5*TestAcc + 0.5*AUC) = {scored[0][1]:.4f}")
    print(f"  Test Acc={best['test_acc']*100:.1f}%  AUC={best['auc']:.3f}  Params={best['params']:,}")
    print(f"  특성: {notes.get(best['name'], '')}")
    print()
    print("  전체 순위:")
    for rank, (r, sc) in enumerate(scored, 1):
        print(f"  {rank}. {r['name']:<14} score={sc:.4f}  "
              f"test={r['test_acc']*100:.1f}%  auc={r['auc']:.3f}  params={r['params']:,}")

    print("\n  참고: Bi-LSTM은 미래 데이터를 이용하므로 실시간 적용 시 순방향(LSTM/GRU)으로 대체 필요.")
    print("  금융 시계열은 노이즈가 높아 AUC 0.52~0.56도 의미 있는 수준임.")


if __name__ == "__main__":
    main()
