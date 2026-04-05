"""DL Integration for Conviction Engine.

Loads trained DL models (LSTM/Transformer/CNN) and provides a unified
inference interface that returns a conviction boost score (0.0 to 0.40).

Models are loaded from data/dl_*.pt at startup.  Assets without a trained
model fall back gracefully to 0.0 (rule-based only).

Usage (standalone test):
    py -3.12 scripts/dl_integration.py

Integration with conviction_engine.py:
    See INTEGRATION GUIDE at the bottom of this file.
"""
from __future__ import annotations

import importlib
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Auto-install torch if missing
# ---------------------------------------------------------------------------
try:
    import torch
    import torch.nn as nn
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "torch", "-q"])
    import torch
    import torch.nn as nn


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


# ===================================================================
# Model architectures (mirrors training scripts exactly)
# ===================================================================

class DirectionLSTM(nn.Module):
    """BTC 4H LSTM  (from dl_btc_lstm.py)."""

    def __init__(self, input_dim: int, hidden_dim: int = 128,
                 num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim, hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        out = out[:, -1, :]
        out = self.dropout(out)
        return self.fc(out)


class _PositionalEncoding(nn.Module):
    """Sinusoidal PE  (from dl_nvda_transformer.py)."""

    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 200):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        pe = torch.zeros(max_len, d_model)
        pos = torch.arange(0, max_len).unsqueeze(1).float()
        import math
        div = torch.exp(torch.arange(0, d_model, 2).float()
                        * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(pos * div)
        pe[:, 1::2] = torch.cos(pos * div)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)


class DirectionTransformer(nn.Module):
    """NVDA Transformer  (from dl_nvda_transformer.py)."""

    def __init__(self, input_dim: int, d_model: int = 64, nhead: int = 4,
                 num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.proj = nn.Linear(input_dim, d_model)
        self.pos_enc = _PositionalEncoding(d_model, dropout=dropout)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.head = nn.Sequential(
            nn.Linear(d_model, 32), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.proj(x)
        x = self.pos_enc(x)
        x = self.encoder(x)
        x = x[:, -1, :]
        return self.head(x).squeeze(-1)


class DirectionCNN(nn.Module):
    """AMZN 1D-CNN  (from dl_amzn_cnn.py)."""

    def __init__(self, input_channels: int = 14, seq_len: int = 30):
        super().__init__()
        self.conv1 = nn.Sequential(
            nn.Conv1d(input_channels, 32, kernel_size=3, padding=1),
            nn.BatchNorm1d(32), nn.ReLU(), nn.MaxPool1d(2),
        )
        self.conv2 = nn.Sequential(
            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64), nn.ReLU(), nn.MaxPool1d(2),
        )
        self.conv3 = nn.Sequential(
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128), nn.ReLU(),
        )
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Sequential(
            nn.Linear(128, 64), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, channels, seq_len)
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.pool(x).squeeze(-1)
        return self.fc(x)


# ===================================================================
# Feature engineering helpers (shared across models)
# ===================================================================

def _rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """RSI as numpy array, NaN-padded."""
    s = pd.Series(close)
    delta = s.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100.0 - 100.0 / (1.0 + rs)).values


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int = 14) -> np.ndarray:
    h, lo, c = pd.Series(high), pd.Series(low), pd.Series(close)
    prev_c = c.shift(1)
    tr = pd.concat([h - lo, (h - prev_c).abs(), (lo - prev_c).abs()],
                    axis=1).max(axis=1)
    return tr.rolling(period).mean().values


def _sma(arr: np.ndarray, w: int) -> np.ndarray:
    return pd.Series(arr).rolling(w).mean().values


def build_btc_features(c: np.ndarray, h: np.ndarray, lo: np.ndarray,
                       v: np.ndarray) -> np.ndarray | None:
    """Build BTC LSTM feature matrix. Returns (N, n_features) or None."""
    n = len(c)
    if n < 260:  # need 200 for MA200 + 60 for seq
        return None

    df = pd.DataFrame({"close": c, "high": h, "low": lo, "volume": v})
    feat = pd.DataFrame(index=df.index)

    feat["open_pct"] = 0.0  # placeholder (no open in conviction data)
    feat["high_pct"] = (df["high"] - df["close"]) / df["close"]
    feat["low_pct"] = (df["low"] - df["close"]) / df["close"]
    feat["close_ret"] = df["close"].pct_change()

    vol_ma = df["volume"].rolling(60).mean()
    vol_std = df["volume"].rolling(60).std().replace(0, 1)
    feat["vol_z"] = (df["volume"] - vol_ma) / vol_std

    feat["rsi"] = _rsi(c) / 100.0
    feat["atr_pct"] = _atr(h, lo, c) / (df["close"] + 1e-10)

    for w in [20, 50, 200]:
        ma = df["close"].rolling(w).mean()
        feat[f"ma{w}_pos"] = (df["close"] - ma) / (ma + 1e-10)

    for lb in [1, 4, 12]:
        feat[f"mom_{lb}"] = df["close"].pct_change(lb)

    # Time features: fill with zeros (candle data has no timestamp)
    feat["hour_sin"] = 0.0
    feat["hour_cos"] = 0.0
    feat["dow_sin"] = 0.0
    feat["dow_cos"] = 0.0

    feat = feat.replace([np.inf, -np.inf], 0).fillna(0)
    return feat.values.astype(np.float32)


def build_nvda_features(c: np.ndarray, h: np.ndarray, lo: np.ndarray,
                        v: np.ndarray, feat_cols: list[str] | None = None
                        ) -> np.ndarray | None:
    """Build NVDA Transformer feature matrix. Returns (N, n_features) or None."""
    n = len(c)
    if n < 100:
        return None

    close = pd.Series(c, dtype=float)
    high = pd.Series(h, dtype=float)
    low = pd.Series(lo, dtype=float)
    volume = pd.Series(v, dtype=float)

    feat = pd.DataFrame()
    feat["rsi"] = _rsi(c) / 100.0
    feat["atr_ratio"] = _atr(h, lo, c) / (close + 1e-10)

    for w in [10, 20, 50]:
        ma = close.rolling(w).mean()
        feat[f"ma{w}_pos"] = (close - ma) / (ma + 1e-10)

    for lb in [1, 5]:
        feat[f"mom{lb}"] = close.pct_change(lb)

    vol_ma20 = volume.rolling(20).mean()
    feat["vol_ratio"] = volume / (vol_ma20 + 1e-10)
    feat["ret_1d"] = close.pct_change(1)
    feat["ret_5d"] = close.pct_change(5)
    feat["high_low_range"] = (high - low) / (close + 1e-10)

    feat = feat.replace([np.inf, -np.inf], 0).fillna(0)

    # If model was trained with specific feat_cols, reorder/select
    if feat_cols is not None:
        for col in feat_cols:
            if col not in feat.columns:
                feat[col] = 0.0
        feat = feat[feat_cols]

    return feat.values.astype(np.float32)


def build_amzn_features(c: np.ndarray, h: np.ndarray, lo: np.ndarray,
                        v: np.ndarray) -> np.ndarray | None:
    """Build AMZN CNN feature matrix. Returns (N, 14) or None."""
    n = len(c)
    if n < 80:
        return None

    close = pd.Series(c, dtype=float)
    high = pd.Series(h, dtype=float)
    low = pd.Series(lo, dtype=float)
    volume = pd.Series(v, dtype=float)

    rsi_val = pd.Series(_rsi(c)) / 100.0
    atr_ratio = pd.Series(_atr(h, lo, c)) / (close + 1e-10)
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
    ret_1d = close.pct_change(1)
    ret_5d = close.pct_change(5)
    hl_range = (high - low) / (close + 1e-10)

    feat = pd.DataFrame({
        "rsi": rsi_val, "atr_ratio": atr_ratio,
        "ma10_pos": ma10_pos, "ma20_pos": ma20_pos, "ma50_pos": ma50_pos,
        "mom1": mom1, "mom5": mom5,
        "vol_ratio": vol_ratio,
        "ret_1d": ret_1d, "ret_5d": ret_5d,
        "hl_range": hl_range,
        "close_norm": 0.0,  # placeholder (normalised in training via scaler)
        "high_norm": 0.0,
        "low_norm": 0.0,
    })
    feat = feat.replace([np.inf, -np.inf], 0).fillna(0)
    return feat.values.astype(np.float32)


# ===================================================================
# Conviction score conversion
# ===================================================================

def dl_score(prob: float) -> float:
    """Convert DL prediction probability (0-1) to conviction adjustment (-0.20 to +0.40).

    Bidirectional: bearish predictions REDUCE conviction, bullish BOOST it.

    Mapping:
      prob <= 0.30 -> -0.20  (strong bearish = reduce conviction)
      0.30 < prob <= 0.50 -> -0.20 to 0.00  (mild bearish)
      prob == 0.50 -> 0.00  (neutral)
      0.50 < prob <= 0.60 -> 0.00 to 0.20  (mild bullish)
      0.60 < prob <= 1.00 -> 0.20 to 0.40  (strong bullish)
    """
    if prob <= 0.3:
        return -0.20
    elif prob <= 0.5:
        # Linear -0.20 -> 0.00 as prob goes 0.3 -> 0.5
        return (prob - 0.3) / 0.2 * 0.20 - 0.20
    elif prob <= 0.6:
        return (prob - 0.5) / 0.1 * 0.20
    else:
        return 0.20 + min((prob - 0.6) / 0.4 * 0.20, 0.20)


# ===================================================================
# Model registry: maps asset symbol -> (model_file, arch, loader)
# ===================================================================

_MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "BTC": {
        "file": "dl_btc_lstm.pt",
        "arch": "lstm",
        "feature_builder": build_btc_features,
    },
    "NVDA": {
        "file": "dl_nvda_transformer.pt",
        "arch": "transformer",
        "feature_builder": build_nvda_features,
    },
    "AMZN": {
        "file": "dl_amzn_cnn.pt",
        "arch": "cnn",
        "feature_builder": build_amzn_features,
    },
    # ETH: no DL model yet.  Add entry when dl_eth_*.py is trained.
}


# ===================================================================
# DLPredictor - main public class
# ===================================================================

class DLPredictor:
    """Unified DL inference for Conviction Engine integration.

    Loads all available DL models at startup.  For each asset, call
    predict(symbol, candle_data) to get a conviction boost in [0.0, 0.40].
    Assets without a model return 0.0 (graceful fallback).
    """

    def __init__(self, model_dir: str = str(DATA_DIR)):
        self._model_dir = Path(model_dir)
        self._models: dict[str, nn.Module] = {}
        self._configs: dict[str, dict] = {}
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        for sym, info in _MODEL_REGISTRY.items():
            pt_path = self._model_dir / info["file"]
            if not pt_path.exists():
                continue
            try:
                ckpt = torch.load(str(pt_path), map_location=self._device,
                                  weights_only=False)
                model = self._build_model(sym, info["arch"], ckpt)
                if model is not None:
                    model.eval()
                    self._models[sym] = model
                    self._configs[sym] = {
                        "arch": info["arch"],
                        "ckpt": ckpt,
                        "feature_builder": info["feature_builder"],
                    }
                    print(f"  [DL] Loaded {sym} ({info['arch']}) from {pt_path.name}")
            except Exception as e:
                print(f"  [DL] WARN: failed to load {sym}: {e}")

        if not self._models:
            print("  [DL] No models loaded. DL boost disabled (rule-based only).")
        else:
            print(f"  [DL] {len(self._models)} model(s) ready on {self._device}")

    # ----- model construction from checkpoint -----

    def _build_model(self, sym: str, arch: str, ckpt: dict) -> nn.Module | None:
        if arch == "lstm":
            input_dim = ckpt.get("input_dim", 16)
            hidden_dim = ckpt.get("hidden_dim", 128)
            num_layers = ckpt.get("num_layers", 2)
            model = DirectionLSTM(input_dim, hidden_dim, num_layers)
            model.load_state_dict(ckpt["model_state_dict"])
            return model

        elif arch == "transformer":
            cfg = ckpt.get("config", {})
            model = DirectionTransformer(
                input_dim=cfg.get("input_dim", 12),
                d_model=cfg.get("d_model", 64),
                nhead=cfg.get("nhead", 4),
                num_layers=cfg.get("num_layers", 2),
                dropout=cfg.get("dropout", 0.2),
            )
            model.load_state_dict(ckpt["state_dict"])
            return model

        elif arch == "cnn":
            input_channels = ckpt.get("input_channels", 14)
            seq_len = ckpt.get("seq_len", 30)
            model = DirectionCNN(input_channels, seq_len)
            model.load_state_dict(ckpt["model_state"])
            return model

        return None

    # ----- public API -----

    def predict(self, symbol: str, c: np.ndarray, h: np.ndarray,
                lo: np.ndarray, v: np.ndarray) -> float:
        """Return DL conviction boost (0.0 to 0.40) for the given asset.

        Args:
            symbol: Asset key (e.g. "BTC", "NVDA", "AMZN").
            c, h, lo, v: Close, High, Low, Volume arrays (latest bar last).

        Returns:
            Float in [0.0, 0.40].  0.0 if no model or inference fails.
        """
        if symbol not in self._models:
            return 0.0

        try:
            cfg = self._configs[symbol]
            ckpt = cfg["ckpt"]
            feature_builder = cfg["feature_builder"]

            # Build features with optional extra args
            if symbol == "NVDA":
                feat_cols = ckpt.get("config", {}).get("feat_cols", None)
                feat_matrix = feature_builder(c, h, lo, v, feat_cols=feat_cols)
            else:
                feat_matrix = feature_builder(c, h, lo, v)

            if feat_matrix is None:
                return 0.0

            # Get seq_len from checkpoint
            seq_len = self._get_seq_len(symbol, ckpt)

            if len(feat_matrix) < seq_len:
                return 0.0

            # Extract last sequence
            seq = feat_matrix[-seq_len:]  # (seq_len, n_features)

            # Normalise using simple z-score of the sequence itself
            mean = seq.mean(axis=0)
            std = seq.std(axis=0)
            std[std < 1e-8] = 1.0
            seq_norm = (seq - mean) / std

            # Prepare tensor
            if cfg["arch"] == "cnn":
                # CNN expects (batch, channels, seq_len)
                x = torch.tensor(seq_norm.T[np.newaxis, :, :],
                                 dtype=torch.float32).to(self._device)
            else:
                # LSTM/Transformer expect (batch, seq_len, features)
                x = torch.tensor(seq_norm[np.newaxis, :, :],
                                 dtype=torch.float32).to(self._device)

            # Inference
            with torch.no_grad():
                logit = self._models[symbol](x)
                if logit.dim() > 1:
                    logit = logit.squeeze(-1)
                prob = torch.sigmoid(logit).item()

            return dl_score(prob)

        except Exception as e:
            print(f"  [DL] {symbol} inference error: {e}")
            return 0.0

    def predict_proba(self, symbol: str, c: np.ndarray, h: np.ndarray,
                      lo: np.ndarray, v: np.ndarray) -> float | None:
        """Return raw DL probability (0-1) or None if unavailable.

        Useful for logging/debugging.
        """
        if symbol not in self._models:
            return None

        try:
            cfg = self._configs[symbol]
            ckpt = cfg["ckpt"]
            feature_builder = cfg["feature_builder"]

            if symbol == "NVDA":
                feat_cols = ckpt.get("config", {}).get("feat_cols", None)
                feat_matrix = feature_builder(c, h, lo, v, feat_cols=feat_cols)
            else:
                feat_matrix = feature_builder(c, h, lo, v)

            if feat_matrix is None:
                return None

            seq_len = self._get_seq_len(symbol, ckpt)
            if len(feat_matrix) < seq_len:
                return None

            seq = feat_matrix[-seq_len:]
            mean = seq.mean(axis=0)
            std = seq.std(axis=0)
            std[std < 1e-8] = 1.0
            seq_norm = (seq - mean) / std

            if cfg["arch"] == "cnn":
                x = torch.tensor(seq_norm.T[np.newaxis, :, :],
                                 dtype=torch.float32).to(self._device)
            else:
                x = torch.tensor(seq_norm[np.newaxis, :, :],
                                 dtype=torch.float32).to(self._device)

            with torch.no_grad():
                logit = self._models[symbol](x)
                if logit.dim() > 1:
                    logit = logit.squeeze(-1)
                return torch.sigmoid(logit).item()
        except Exception:
            return None

    def available_models(self) -> list[str]:
        """Return list of asset symbols with loaded DL models."""
        return list(self._models.keys())

    def _get_seq_len(self, symbol: str, ckpt: dict) -> int:
        """Extract seq_len from checkpoint metadata."""
        if "seq_len" in ckpt:
            return ckpt["seq_len"]
        cfg = ckpt.get("config", {})
        if "seq_len" in cfg:
            return cfg["seq_len"]
        # Defaults per architecture
        defaults = {"BTC": 60, "NVDA": 40, "AMZN": 30}
        return defaults.get(symbol, 40)


# ===================================================================
# INTEGRATION GUIDE for conviction_engine.py
# ===================================================================
#
# To integrate DLPredictor into conviction_engine.py, apply these changes:
#
# 1. Add import at top of conviction_engine.py (after existing imports):
#
#     from dl_integration import DLPredictor
#
# 2. In compute_conviction(), scale rule-based signals to max 0.60:
#    Change line 107:
#
#     OLD:  raw = trend_score + rsi_score + vol_score + mom_score + atr_score
#           conviction = max(0.0, min(1.0, raw))
#
#     NEW:  raw_rules = trend_score + rsi_score + vol_score + mom_score + atr_score
#           rules_conviction = max(0.0, min(0.60, raw_rules))
#           conviction = rules_conviction  # DL boost added externally
#
# 3. In ConvictionTrader.__init__(), instantiate the predictor:
#    After self._last_ts = {} (line 181), add:
#
#     self.dl_predictor = DLPredictor(str(DATA_DIR))
#
# 4. In cycle_asset(), after compute_conviction() call (line 238-239), add DL boost:
#
#     OLD:  conviction, details = compute_conviction(c, h, lo, v, cfg["max_lev"])
#           s.conviction = conviction
#
#     NEW:  conviction, details = compute_conviction(c, h, lo, v, cfg["max_lev"])
#           # DL boost (0.0 to 0.40)
#           dl_boost = self.dl_predictor.predict(sym, c, h, lo, v)
#           dl_prob = self.dl_predictor.predict_proba(sym, c, h, lo, v)
#           conviction = min(1.0, conviction + dl_boost)
#           details["dl_boost"] = round(dl_boost, 3)
#           details["dl_prob"] = round(dl_prob, 3) if dl_prob is not None else None
#           s.conviction = conviction
#
# 5. (Optional) In dashboard HTML, add a DL signal chip after the existing 4:
#
#     <span class="signal-chip" ...>DL${fmt(det.dl_boost||0)}</span>
#
# ===================================================================


# ===================================================================
# Standalone test / demo
# ===================================================================

def _demo():
    """Load models and run demo inference with synthetic data."""
    print("=" * 60)
    print("  DL Integration - Model Load Test & Demo")
    print("=" * 60)

    predictor = DLPredictor(str(DATA_DIR))

    print(f"\n  Available models: {predictor.available_models()}")
    print(f"  Registry assets:  {list(_MODEL_REGISTRY.keys())}")
    missing = [s for s in _MODEL_REGISTRY if s not in predictor.available_models()]
    if missing:
        print(f"  Missing models:   {missing}  (train first)")

    # --- Demo with synthetic candle data ---
    print("\n--- Demo Inference (synthetic data) ---")
    np.random.seed(42)
    n_bars = 300
    base_price = 100.0
    returns = np.random.normal(0.0005, 0.02, n_bars)
    close = base_price * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.normal(0, 0.005, n_bars)))
    low = close * (1 - np.abs(np.random.normal(0, 0.005, n_bars)))
    volume = np.random.uniform(1e6, 5e6, n_bars)

    for sym in list(_MODEL_REGISTRY.keys()) + ["ETH"]:
        t0 = time.perf_counter()
        boost = predictor.predict(sym, close, high, low, volume)
        prob = predictor.predict_proba(sym, close, high, low, volume)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        status = "loaded" if sym in predictor.available_models() else "no model"
        prob_str = f"{prob:.3f}" if prob is not None else "N/A"
        print(f"  {sym:5s} [{status:>8s}]  prob={prob_str}  "
              f"boost={boost:.3f}  time={elapsed_ms:.1f}ms")

    # --- dl_score function verification ---
    print("\n--- dl_score() mapping verification ---")
    test_probs = [0.0, 0.3, 0.5, 0.55, 0.6, 0.7, 0.8, 0.9, 1.0]
    for p in test_probs:
        s = dl_score(p)
        print(f"  prob={p:.2f}  ->  boost={s:.3f}")

    print("\nDone.")


if __name__ == "__main__":
    _demo()
