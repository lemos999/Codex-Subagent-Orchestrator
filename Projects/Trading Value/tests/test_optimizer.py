"""Tests for trading_value.core.optimizer (Phase 5)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pytest

from trading_value.adapters.backtest import BacktestConfig, BacktestResult, TradeRecord
from trading_value.core.models import Timeframe
from trading_value.core.optimizer import (
    PARAM_SPACE,
    OptimizationConfig,
    apply_params_to_config,
    compute_calmar,
    compute_profit_factor,
    compute_sharpe,
    create_objective,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trade(pnl: float, pnl_r: float = 0.0) -> TradeRecord:
    return TradeRecord(
        symbol="ETHUSDT",
        strategy="trend_long",
        side="LONG",
        entry_price=2000.0,
        exit_price=2000.0 + pnl,
        qty=1.0,
        pnl=pnl,
        pnl_r=pnl_r,
        commission_total=0.0,
        entry_time=datetime(2022, 1, 1, 10, 0),
        exit_time=datetime(2022, 1, 1, 12, 0),
        duration_bars=4,
        exit_reason="tp1",
        regime_at_entry="HTF_BULLISH",
        mode_at_entry="MODE_TREND_LONG",
        rr_planned=1.5,
        rr_actual=pnl_r,
    )


def _make_result(
    trades: list[TradeRecord],
    total_pnl: float | None = None,
    max_drawdown: float = 100.0,
) -> BacktestResult:
    pnl = total_pnl if total_pnl is not None else sum(t.pnl for t in trades)
    return BacktestResult(
        trades=trades,
        decision_logs=[],
        final_balance=10000.0 + pnl,
        total_pnl=pnl,
        total_commission=0.0,
        win_rate=sum(1 for t in trades if t.pnl > 0) / max(len(trades), 1),
        avg_rr=0.0,
        max_drawdown=max_drawdown,
        max_consecutive_losses=0,
        sharpe_ratio=None,
        total_trades=len(trades),
        long_trades=len(trades),
        short_trades=0,
        avg_hold_bars=0.0,
    )


# ---------------------------------------------------------------------------
# compute_sharpe
# ---------------------------------------------------------------------------

def test_compute_sharpe_positive_trades():
    """Positive trades yield positive Sharpe."""
    trades = [_make_trade(100.0), _make_trade(80.0), _make_trade(120.0)]
    result = _make_result(trades)
    sharpe = compute_sharpe(result)
    assert sharpe > 0.0


def test_compute_sharpe_negative_trades():
    """Negative trades yield negative Sharpe."""
    trades = [_make_trade(-100.0), _make_trade(-80.0), _make_trade(-120.0)]
    result = _make_result(trades)
    sharpe = compute_sharpe(result)
    assert sharpe < 0.0


def test_compute_sharpe_zero_std_returns_zero():
    """All identical PnLs -> std=0, should return 0.0."""
    trades = [_make_trade(50.0), _make_trade(50.0), _make_trade(50.0)]
    result = _make_result(trades)
    sharpe = compute_sharpe(result)
    assert sharpe == 0.0


def test_compute_sharpe_less_than_two_trades():
    """Fewer than 2 trades -> 0.0."""
    result = _make_result([_make_trade(100.0)])
    assert compute_sharpe(result) == 0.0


# ---------------------------------------------------------------------------
# compute_profit_factor
# ---------------------------------------------------------------------------

def test_compute_profit_factor_normal():
    """Mixed wins and losses -> profit_factor > 0."""
    trades = [_make_trade(200.0), _make_trade(-100.0), _make_trade(50.0)]
    result = _make_result(trades)
    pf = compute_profit_factor(result)
    assert pytest.approx(pf, rel=1e-3) == 250.0 / 100.0


def test_compute_profit_factor_all_losses():
    """All losers -> profit_factor == 0.0."""
    trades = [_make_trade(-100.0), _make_trade(-50.0)]
    result = _make_result(trades)
    assert compute_profit_factor(result) == 0.0


def test_compute_profit_factor_all_wins():
    """All winners -> capped at 10.0."""
    trades = [_make_trade(100.0), _make_trade(200.0)]
    result = _make_result(trades)
    assert compute_profit_factor(result) == 10.0


def test_compute_profit_factor_no_trades():
    """No trades -> 0.0."""
    result = _make_result([])
    assert compute_profit_factor(result) == 0.0


# ---------------------------------------------------------------------------
# compute_calmar
# ---------------------------------------------------------------------------

def test_compute_calmar_normal():
    """Positive PnL and non-zero drawdown -> positive calmar."""
    trades = [_make_trade(300.0)]
    result = _make_result(trades, total_pnl=300.0, max_drawdown=100.0)
    assert compute_calmar(result) == pytest.approx(3.0, rel=1e-3)


def test_compute_calmar_zero_drawdown_positive_pnl():
    """Zero drawdown with positive PnL -> capped at 10.0."""
    trades = [_make_trade(100.0)]
    result = _make_result(trades, total_pnl=100.0, max_drawdown=0.0)
    assert compute_calmar(result) == 10.0


def test_compute_calmar_no_trades():
    """No trades -> 0.0."""
    result = _make_result([])
    assert compute_calmar(result) == 0.0


# ---------------------------------------------------------------------------
# apply_params_to_config
# ---------------------------------------------------------------------------

def test_apply_params_to_config_direct_fields():
    """Verify that optimizer params are applied to BacktestConfig fields."""
    base = BacktestConfig()
    params = {
        "min_rr": 2.5,
        "risk_pct": 0.003,
        "cooldown_normal_bars": 3,
        "cooldown_stop_bars": 6,
        "max_hold_bars": 72,
    }
    cfg = apply_params_to_config(base, params)
    assert cfg.min_rr == pytest.approx(2.5)
    assert cfg.risk_pct == pytest.approx(0.003)
    assert cfg.cooldown_normal_bars == 3
    assert cfg.cooldown_stop_bars == 6
    assert cfg.max_hold_bars == 72


def test_apply_params_to_config_preserves_base_fields():
    """Fields not in params remain at base values."""
    base = BacktestConfig(initial_balance=50000.0, commission_rate=0.001)
    cfg = apply_params_to_config(base, {"min_rr": 2.0})
    assert cfg.initial_balance == 50000.0
    assert cfg.commission_rate == pytest.approx(0.001)


# ---------------------------------------------------------------------------
# OptimizationConfig defaults
# ---------------------------------------------------------------------------

def test_optimization_config_defaults():
    cfg = OptimizationConfig()
    assert cfg.n_trials == 50
    assert cfg.objective == "sharpe"
    assert cfg.train_start == "2022-01-01"
    assert cfg.test_end == "2023-11-11"
    assert cfg.primary_timeframe == "30m"


# ---------------------------------------------------------------------------
# PARAM_SPACE
# ---------------------------------------------------------------------------

def test_param_space_contains_all_seven_params():
    expected = {
        "min_rr", "risk_pct", "zone_width_pct", "zone_width_atr_factor",
        "cooldown_normal_bars", "cooldown_stop_bars", "max_hold_bars",
    }
    assert set(PARAM_SPACE.keys()) == expected


def test_param_space_ranges_are_valid():
    """Each range (lo, hi) must have lo < hi and both be positive."""
    for name, (lo, hi) in PARAM_SPACE.items():
        assert lo < hi, f"{name}: lo={lo} must be < hi={hi}"
        assert lo >= 0, f"{name}: lo must be >= 0"


# ---------------------------------------------------------------------------
# create_objective
# ---------------------------------------------------------------------------

def test_create_objective_returns_callable():
    """create_objective should return a callable."""
    import pandas as pd
    import numpy as np

    cfg = OptimizationConfig()
    dates = pd.date_range("2022-01-01", periods=100, freq="30min", tz="UTC")
    close = 2000 + np.cumsum(np.random.randn(100) * 5)
    df30 = pd.DataFrame({
        "timestamp": dates,
        "open": close - 2,
        "high": close + 5,
        "low": close - 5,
        "close": close,
        "volume": np.random.rand(100) * 1000,
    })
    train_data = {"ETHUSDT": {Timeframe.M30: df30}}
    obj = create_objective(cfg, train_data)
    assert callable(obj)


# ---------------------------------------------------------------------------
# load_backtest_data (skip if no DB)
# ---------------------------------------------------------------------------

def test_load_backtest_data_skipped_without_db():
    """load_backtest_data raises or returns empty when DB doesn't exist."""
    from trading_value.core.optimizer import load_backtest_data
    import sqlite3

    with pytest.raises(Exception):
        load_backtest_data(
            db_path="nonexistent_path/fake.sqlite",
            symbols=["ETHUSDT"],
            start="2022-01-01",
            end="2022-12-31",
        )
