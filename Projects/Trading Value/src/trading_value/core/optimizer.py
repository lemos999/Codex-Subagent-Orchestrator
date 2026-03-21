"""Bayesian parameter optimizer for the Trading Value backtest system.

Uses Optuna (TPE sampler) to search the parameter space, with strict
time-based train/test split to avoid lookahead bias.
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import optuna
import pandas as pd

from ..adapters.backtest import BacktestConfig, BacktestEngine, BacktestResult
from ..core.models import Timeframe

# ---------------------------------------------------------------------------
# 1. OptimizationConfig
# ---------------------------------------------------------------------------


@dataclass
class OptimizationConfig:
    """Configuration for the optimization run."""

    symbols: list[str] = field(default_factory=lambda: ["ETHUSDT", "BTCUSDT"])
    train_start: str = "2022-01-01"
    train_end: str = "2022-12-31"
    test_start: str = "2023-01-01"
    test_end: str = "2023-11-11"
    n_trials: int = 50
    objective: str = "sharpe"  # "sharpe", "profit_factor", "calmar"
    commission_rate: float = 0.0002
    db_path: str = "data/cache.sqlite"
    primary_timeframe: str = "30m"


# ---------------------------------------------------------------------------
# 2. Parameter search space
# ---------------------------------------------------------------------------

PARAM_SPACE: dict[str, tuple[float, float]] = {
    "min_rr": (1.0, 3.0),
    "risk_pct": (0.001, 0.005),
    "zone_width_pct": (0.001, 0.003),
    "zone_width_atr_factor": (0.15, 0.50),
    "cooldown_normal_bars": (1, 6),
    "cooldown_stop_bars": (2, 8),
    "max_hold_bars": (24, 96),
}

# Integer parameters — sampled with suggest_int
_INT_PARAMS = {"cooldown_normal_bars", "cooldown_stop_bars", "max_hold_bars"}


# ---------------------------------------------------------------------------
# 3. Objective functions
# ---------------------------------------------------------------------------


def compute_sharpe(result: BacktestResult) -> float:
    """Sharpe ratio from trade PnLs. Higher is better.

    Returns 0.0 when there are fewer than 2 trades or zero standard deviation.
    Uses per-trade PnL (not annualized) to stay comparable across periods.
    """
    if result.total_trades < 2:
        return 0.0
    pnls = [t.pnl for t in result.trades]
    mean_pnl = float(np.mean(pnls))
    std_pnl = float(np.std(pnls, ddof=1))
    if std_pnl <= 0:
        return 0.0
    # Annualize: assume ~2 trades/day on average, sqrt(365)
    return (mean_pnl / std_pnl) * math.sqrt(365)


def compute_profit_factor(result: BacktestResult) -> float:
    """Gross profit / Gross loss.  > 1.0 means profitable.

    Returns 0.0 when there are no trades, and a large cap value when
    there are only winners (no gross loss).
    """
    if result.total_trades == 0:
        return 0.0
    gross_profit = sum(t.pnl for t in result.trades if t.pnl > 0)
    gross_loss = abs(sum(t.pnl for t in result.trades if t.pnl < 0))
    if gross_loss <= 0:
        return 10.0 if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def compute_calmar(result: BacktestResult) -> float:
    """Total PnL / Max Drawdown.  Higher is better.

    Returns 0.0 when there are no trades or zero drawdown with non-positive PnL.
    """
    if result.total_trades == 0:
        return 0.0
    if result.max_drawdown <= 0:
        return 10.0 if result.total_pnl > 0 else 0.0
    return result.total_pnl / result.max_drawdown


_OBJECTIVE_MAP = {
    "sharpe": compute_sharpe,
    "profit_factor": compute_profit_factor,
    "calmar": compute_calmar,
}


# ---------------------------------------------------------------------------
# 4. Data loader
# ---------------------------------------------------------------------------

_TF_MAP: dict[str, Timeframe] = {
    "5m": Timeframe.M5,
    "15m": Timeframe.M15,
    "30m": Timeframe.M30,
    "1h": Timeframe.H1,
    "4h": Timeframe.H4,
}


def _load_ohlcv_tf(
    conn: sqlite3.Connection,
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Load a single timeframe from the ohlcv table, filtered by date range."""
    query = """
        SELECT datetime, open, high, low, close, volume
        FROM ohlcv
        WHERE symbol = ? AND timeframe = ? AND datetime >= ? AND datetime <= ?
        ORDER BY timestamp ASC
    """
    df = pd.read_sql_query(query, conn, params=(symbol, timeframe, start, end))
    if df.empty:
        return df
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df.rename(columns={"datetime": "timestamp"})
    return df


def _resample_to_30m(df_15m: pd.DataFrame) -> pd.DataFrame:
    """Resample 15m OHLCV data to 30m bars."""
    if df_15m.empty:
        return df_15m
    resampled = (
        df_15m.set_index("timestamp")
        .resample("30min")
        .agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        })
        .dropna()
        .reset_index()
    )
    return resampled


def _load_30m_from_minute_ohlcv(
    conn: sqlite3.Connection,
    symbol: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Try loading 30m data from the minute_ohlcv table."""
    query = """
        SELECT datetime, open, high, low, close, volume
        FROM minute_ohlcv
        WHERE symbol = ? AND datetime >= ? AND datetime <= ?
        ORDER BY datetime ASC
    """
    df = pd.read_sql_query(query, conn, params=(symbol, start, end))
    if df.empty:
        return df
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df.rename(columns={"datetime": "timestamp"})
    return df


def load_backtest_data(
    db_path: str,
    symbols: list[str],
    start: str,
    end: str,
) -> dict[str, dict[Timeframe, pd.DataFrame]]:
    """Load OHLCV from sqlite, resample 15m -> 30m, return dict[str, dict[Timeframe, DataFrame]].

    Loads 5m, 15m, 1h, 4h from the ``ohlcv`` table.  For 30m it first tries
    the ``minute_ohlcv`` table (pre-aggregated), falling back to resampling
    from 15m.
    """
    resolved = str(Path(db_path).resolve())
    conn = sqlite3.connect(resolved)

    data: dict[str, dict[Timeframe, pd.DataFrame]] = {}

    for symbol in symbols:
        sym_data: dict[Timeframe, pd.DataFrame] = {}

        # Load standard timeframes from ohlcv table
        for tf_str in ("5m", "15m", "1h", "4h"):
            df = _load_ohlcv_tf(conn, symbol, tf_str, start, end)
            sym_data[_TF_MAP[tf_str]] = df

        # 30m: try minute_ohlcv first, then resample from 15m
        df_30m = _load_30m_from_minute_ohlcv(conn, symbol, start, end)
        if df_30m.empty:
            df_30m = _resample_to_30m(sym_data[Timeframe.M15])
        sym_data[Timeframe.M30] = df_30m

        data[symbol] = sym_data

    conn.close()
    return data


# ---------------------------------------------------------------------------
# 5. Optuna objective
# ---------------------------------------------------------------------------


def create_objective(
    opt_config: OptimizationConfig,
    train_data: dict[str, dict[Timeframe, pd.DataFrame]],
):
    """Create an Optuna objective function.

    Returns a callable that:
    1. Samples parameters from the search space
    2. Creates BacktestConfig with sampled params
    3. Runs BacktestEngine on train_data
    4. Returns the objective score
    """
    score_fn = _OBJECTIVE_MAP[opt_config.objective]

    primary_tf = _TF_MAP.get(opt_config.primary_timeframe, Timeframe.M30)

    def objective(trial: optuna.Trial) -> float:
        # Sample parameters
        params: dict = {}
        for name, (lo, hi) in PARAM_SPACE.items():
            if name in _INT_PARAMS:
                params[name] = trial.suggest_int(name, int(lo), int(hi))
            else:
                params[name] = trial.suggest_float(name, lo, hi)

        # Build BacktestConfig
        config = BacktestConfig(
            symbols=opt_config.symbols,
            commission_rate=opt_config.commission_rate,
            risk_pct=params["risk_pct"],
            min_rr=params["min_rr"],
            cooldown_normal_bars=params["cooldown_normal_bars"],
            cooldown_stop_bars=params["cooldown_stop_bars"],
            max_hold_bars=params["max_hold_bars"],
            primary_timeframe=primary_tf,
            zone_width_pct=params["zone_width_pct"],
            zone_width_atr_factor=params["zone_width_atr_factor"],
        )

        # Run backtest
        engine = BacktestEngine(config)
        result = engine.run(train_data)

        # If no trades, return worst possible score
        if result.total_trades == 0:
            return -1e6

        score = score_fn(result)

        # Handle NaN / Inf
        if not math.isfinite(score):
            return -1e6

        return score

    return objective


# ---------------------------------------------------------------------------
# 6. Runner
# ---------------------------------------------------------------------------


@dataclass
class OptimizationResult:
    """Result of a full optimization run with train/test evaluation."""

    best_params: dict
    best_score: float
    train_result: BacktestResult
    test_result: BacktestResult
    all_trials: list[dict]  # [{params, score}]
    overfit_ratio: float  # train_score / test_score -- >2.0 is suspicious


def run_optimization(opt_config: OptimizationConfig) -> OptimizationResult:
    """Full optimization pipeline:

    1. Load train and test data
    2. Run Optuna on train data
    3. Evaluate best params on test data
    4. Compute overfit ratio
    5. Return results
    """
    import sys

    # Reduce Optuna logging noise
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    score_fn = _OBJECTIVE_MAP[opt_config.objective]
    primary_tf = _TF_MAP.get(opt_config.primary_timeframe, Timeframe.M30)

    # 1. Load train and test data
    print("Loading train data...", file=sys.stderr, flush=True)
    train_data = load_backtest_data(
        opt_config.db_path,
        opt_config.symbols,
        opt_config.train_start,
        opt_config.train_end,
    )

    print("Loading test data...", file=sys.stderr, flush=True)
    test_data = load_backtest_data(
        opt_config.db_path,
        opt_config.symbols,
        opt_config.test_start,
        opt_config.test_end,
    )

    # 2. Run Optuna on train data (maximize objective)
    print(
        f"Running {opt_config.n_trials} trials (objective={opt_config.objective})...",
        file=sys.stderr,
        flush=True,
    )
    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=42),
    )
    objective_fn = create_objective(opt_config, train_data)
    study.optimize(objective_fn, n_trials=opt_config.n_trials)

    best_params = study.best_trial.params
    best_train_score = study.best_trial.value

    # Collect all trials
    all_trials = [
        {"params": t.params, "score": t.value}
        for t in study.trials
        if t.value is not None
    ]

    # 3. Evaluate best params on train data (full result)
    print("Evaluating best params on train set...", file=sys.stderr, flush=True)
    train_config = apply_params_to_config(
        BacktestConfig(
            symbols=opt_config.symbols,
            commission_rate=opt_config.commission_rate,
            primary_timeframe=primary_tf,
        ),
        best_params,
    )
    train_engine = BacktestEngine(train_config)
    train_result = train_engine.run(train_data)

    # 4. Evaluate best params on test data
    print("Evaluating best params on test set...", file=sys.stderr, flush=True)
    test_config = apply_params_to_config(
        BacktestConfig(
            symbols=opt_config.symbols,
            commission_rate=opt_config.commission_rate,
            primary_timeframe=primary_tf,
        ),
        best_params,
    )
    test_engine = BacktestEngine(test_config)
    test_result = test_engine.run(test_data)

    # 5. Compute overfit ratio
    train_score = score_fn(train_result)
    test_score = score_fn(test_result)

    if test_score > 0:
        overfit_ratio = train_score / test_score
    elif train_score > 0 and test_score <= 0:
        # Train positive but test zero/negative — clear overfitting
        overfit_ratio = float("inf")
    elif train_score <= 0 and test_score < 0:
        # Both negative — ratio of magnitudes (higher = worse train)
        overfit_ratio = abs(train_score) / abs(test_score)
    else:
        overfit_ratio = 1.0  # both zero

    print(
        f"Done. Train={train_score:.4f} Test={test_score:.4f} "
        f"Overfit={overfit_ratio:.2f}",
        file=sys.stderr,
        flush=True,
    )

    return OptimizationResult(
        best_params=best_params,
        best_score=best_train_score,
        train_result=train_result,
        test_result=test_result,
        all_trials=all_trials,
        overfit_ratio=overfit_ratio,
    )


# ---------------------------------------------------------------------------
# 7. Parameter application
# ---------------------------------------------------------------------------


def apply_params_to_config(
    base_config: BacktestConfig,
    params: dict,
) -> BacktestConfig:
    """Create a new BacktestConfig with optimized parameters applied.

    Maps optimizer parameter names to BacktestConfig fields.
    ``zone_width_pct`` and ``zone_width_atr_factor`` are stored but do not
    directly map to BacktestConfig fields — they influence
    ``indicators.compute_zone_width`` at indicator-computation time.
    """
    # Start from a copy of the base config
    config = BacktestConfig(
        symbols=base_config.symbols,
        initial_balance=base_config.initial_balance,
        commission_rate=base_config.commission_rate,
        slippage_ticks=base_config.slippage_ticks,
        risk_pct=base_config.risk_pct,
        max_risk_pct=base_config.max_risk_pct,
        counter_trend_risk_pct=base_config.counter_trend_risk_pct,
        min_rr=base_config.min_rr,
        cooldown_normal_bars=base_config.cooldown_normal_bars,
        cooldown_stop_bars=base_config.cooldown_stop_bars,
        max_hold_bars=base_config.max_hold_bars,
        min_qty=base_config.min_qty,
        primary_timeframe=base_config.primary_timeframe,
        zone_width_pct=base_config.zone_width_pct,
        zone_width_atr_factor=base_config.zone_width_atr_factor,
    )

    # Direct mappings
    if "min_rr" in params:
        config.min_rr = params["min_rr"]
    if "risk_pct" in params:
        config.risk_pct = params["risk_pct"]
    if "cooldown_normal_bars" in params:
        config.cooldown_normal_bars = int(params["cooldown_normal_bars"])
    if "cooldown_stop_bars" in params:
        config.cooldown_stop_bars = int(params["cooldown_stop_bars"])
    if "max_hold_bars" in params:
        config.max_hold_bars = int(params["max_hold_bars"])

    # Zone width overrides — applied to BacktestConfig for indicator layer
    if "zone_width_pct" in params:
        config.zone_width_pct = params["zone_width_pct"]
    if "zone_width_atr_factor" in params:
        config.zone_width_atr_factor = params["zone_width_atr_factor"]

    return config
