"""Tests for trading_value.adapters.backtest — Phase 3 module.

At least 10 tests covering:
- BacktestConfig defaults
- VirtualOrder creation
- simulate_fill behavior for all order types
- BacktestResult summary
- DecisionLog fields
- TradeRecord PnL calculation
- BacktestEngine initialization
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading_value.adapters.backtest import (
    BacktestConfig,
    BacktestEngine,
    BacktestResult,
    DecisionLog,
    FillResult,
    TradeRecord,
    VirtualOrder,
    simulate_fill,
)
from trading_value.core.models import Side


_NOW = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helper: build a VirtualOrder
# ---------------------------------------------------------------------------

def make_order(
    order_type: str = "market",
    side: Side = Side.LONG,
    price: float = 100.0,
    qty: float = 1.0,
) -> VirtualOrder:
    return VirtualOrder(
        order_id="test_order",
        symbol="ETHUSDT",
        side=side,
        price=price,
        qty=qty,
        order_type=order_type,
        created_at=_NOW,
        ttl_bars=2,
    )


def make_config(**kwargs) -> BacktestConfig:
    cfg = BacktestConfig()
    for k, v in kwargs.items():
        setattr(cfg, k, v)
    return cfg


# ---------------------------------------------------------------------------
# 1. BacktestConfig defaults match config/default.toml
# ---------------------------------------------------------------------------


def test_backtest_config_defaults():
    """BacktestConfig defaults should match config/default.toml values."""
    cfg = BacktestConfig()
    # from [order] ttl_bars_5m = 2
    assert cfg.min_rr == 1.5
    # from [cooldown] normal_bars_30m = 2, stop_loss_bars_30m = 4
    assert cfg.cooldown_normal_bars == 2
    assert cfg.cooldown_stop_bars == 4
    # from [max_hold] bars_30m = 48
    assert cfg.max_hold_bars == 48
    # from [symbols.ETHUSDT] min_qty = 0.001
    assert cfg.min_qty == 0.001
    # commission taker 0.04%
    assert cfg.commission_rate == pytest.approx(0.0004)


# ---------------------------------------------------------------------------
# 2. VirtualOrder creation
# ---------------------------------------------------------------------------


def test_virtual_order_creation():
    """VirtualOrder can be created with expected fields."""
    order = VirtualOrder(
        order_id="abc123",
        symbol="BTCUSDT",
        side=Side.LONG,
        price=50000.0,
        qty=0.01,
        order_type="limit",
        created_at=_NOW,
        ttl_bars=5,
    )
    assert order.order_id == "abc123"
    assert order.symbol == "BTCUSDT"
    assert order.side == Side.LONG
    assert order.price == 50000.0
    assert order.qty == 0.01
    assert order.order_type == "limit"
    assert order.ttl_bars == 5


# ---------------------------------------------------------------------------
# 3. simulate_fill — market order fills at close ± slippage
# ---------------------------------------------------------------------------


def test_simulate_fill_market_long_fills_at_close_plus_slippage():
    order = make_order("market", Side.LONG, price=100.0, qty=1.0)
    cfg = make_config(slippage_ticks=0.5, commission_rate=0.001)
    result = simulate_fill(order, bar_high=102.0, bar_low=98.0, bar_close=100.0, config=cfg)

    assert result.filled is True
    assert result.fill_price == pytest.approx(100.5)  # close + slippage


def test_simulate_fill_market_short_fills_at_close_minus_slippage():
    order = make_order("market", Side.SHORT, price=100.0, qty=1.0)
    cfg = make_config(slippage_ticks=0.5, commission_rate=0.001)
    result = simulate_fill(order, bar_high=102.0, bar_low=98.0, bar_close=100.0, config=cfg)

    assert result.filled is True
    assert result.fill_price == pytest.approx(99.5)  # close - slippage


# ---------------------------------------------------------------------------
# 4. simulate_fill — limit buy fills when low <= price
# ---------------------------------------------------------------------------


def test_simulate_fill_limit_buy_fills_when_low_lte_price():
    order = make_order("limit", Side.LONG, price=99.0, qty=1.0)
    cfg = make_config(slippage_ticks=0.5, commission_rate=0.001)
    # bar_low=98 <= order.price=99 => should fill
    result = simulate_fill(order, bar_high=102.0, bar_low=98.0, bar_close=100.0, config=cfg)
    assert result.filled is True
    assert result.fill_price == 99.0  # fills at limit price


def test_simulate_fill_limit_buy_no_fill_when_low_gt_price():
    order = make_order("limit", Side.LONG, price=97.0, qty=1.0)
    cfg = make_config(slippage_ticks=0.5, commission_rate=0.001)
    # bar_low=98 > order.price=97 => no fill
    result = simulate_fill(order, bar_high=102.0, bar_low=98.0, bar_close=100.0, config=cfg)
    assert result.filled is False


# ---------------------------------------------------------------------------
# 5. simulate_fill — stop sell fills when low <= stop
# ---------------------------------------------------------------------------


def test_simulate_fill_stop_sell_fills_when_low_lte_stop():
    order = make_order("stop", Side.SHORT, price=99.0, qty=1.0)
    cfg = make_config(slippage_ticks=0.5, commission_rate=0.001)
    # bar_low=98 <= order.price=99 => stop sell triggered
    result = simulate_fill(order, bar_high=102.0, bar_low=98.0, bar_close=100.0, config=cfg)
    assert result.filled is True
    # fill_price = stop_price - slippage = 99 - 0.5 = 98.5
    assert result.fill_price == pytest.approx(98.5)


# ---------------------------------------------------------------------------
# 6. simulate_fill — price out of range → no fill
# ---------------------------------------------------------------------------


def test_simulate_fill_limit_sell_no_fill_when_out_of_range():
    """Limit sell (SHORT limit) should not fill if bar_high < price."""
    order = make_order("limit", Side.SHORT, price=105.0, qty=1.0)
    cfg = make_config(slippage_ticks=0.5, commission_rate=0.001)
    # bar_high=102 < order.price=105 => no fill
    result = simulate_fill(order, bar_high=102.0, bar_low=98.0, bar_close=100.0, config=cfg)
    assert result.filled is False


# ---------------------------------------------------------------------------
# 7. BacktestResult summary contains key metrics
# ---------------------------------------------------------------------------


def test_backtest_result_summary_contains_key_metrics():
    """BacktestResult.summary() should include all required metric labels."""
    result = BacktestResult(
        trades=[],
        decision_logs=[],
        final_balance=10500.0,
        total_pnl=500.0,
        total_commission=10.0,
        win_rate=60.0,
        avg_rr=1.8,
        max_drawdown=200.0,
        max_consecutive_losses=2,
        sharpe_ratio=1.5,
        total_trades=10,
        long_trades=7,
        short_trades=3,
        avg_hold_bars=12.0,
    )
    summary = result.summary()
    assert "Total Trades" in summary
    assert "Win Rate" in summary
    assert "Avg R:R" in summary
    assert "Total PnL" in summary
    assert "Final Balance" in summary
    assert "Max Drawdown" in summary
    assert "Sharpe Ratio" in summary


# ---------------------------------------------------------------------------
# 8. DecisionLog captures required fields
# ---------------------------------------------------------------------------


def test_decision_log_captures_required_fields():
    """DecisionLog should have all required fields populated."""
    log = DecisionLog(
        timestamp=_NOW,
        symbol="ETHUSDT",
        event_type="BAR_PROCESSED",
        regime_state="HTF_BULLISH",
        mode_state="MODE_TREND_LONG",
        setup_state="WAIT_ZONE_TOUCH",
        lifecycle_state="FLAT",
        reason="test reason",
        details={"bar_close": 100.0},
    )
    assert log.timestamp == _NOW
    assert log.symbol == "ETHUSDT"
    assert log.event_type == "BAR_PROCESSED"
    assert log.regime_state == "HTF_BULLISH"
    assert log.mode_state == "MODE_TREND_LONG"
    assert log.setup_state == "WAIT_ZONE_TOUCH"
    assert log.lifecycle_state == "FLAT"
    assert log.reason == "test reason"
    assert log.details is not None


# ---------------------------------------------------------------------------
# 9. TradeRecord PnL calculation
# ---------------------------------------------------------------------------


def test_trade_record_pnl_long():
    """LONG PnL = (exit - entry) * qty - commission."""
    entry_price = 100.0
    exit_price = 110.0
    qty = 1.0
    commission = 0.5
    expected_pnl = (exit_price - entry_price) * qty - commission

    record = TradeRecord(
        symbol="ETHUSDT",
        strategy="TREND_LONG",
        side="LONG",
        entry_price=entry_price,
        exit_price=exit_price,
        qty=qty,
        pnl=expected_pnl,
        pnl_r=2.0,
        commission_total=commission,
        entry_time=_NOW,
        exit_time=_NOW,
        duration_bars=10,
        exit_reason="tp1",
        regime_at_entry="HTF_BULLISH",
        mode_at_entry="MODE_TREND_LONG",
        rr_planned=1.5,
        rr_actual=2.0,
    )
    assert record.pnl == pytest.approx(expected_pnl)
    assert record.pnl > 0  # profitable trade


def test_trade_record_pnl_short():
    """SHORT PnL = (entry - exit) * qty - commission."""
    entry_price = 100.0
    exit_price = 90.0
    qty = 1.0
    commission = 0.4
    expected_pnl = (entry_price - exit_price) * qty - commission

    record = TradeRecord(
        symbol="ETHUSDT",
        strategy="REBOUND_SHORT",
        side="SHORT",
        entry_price=entry_price,
        exit_price=exit_price,
        qty=qty,
        pnl=expected_pnl,
        pnl_r=2.5,
        commission_total=commission,
        entry_time=_NOW,
        exit_time=_NOW,
        duration_bars=5,
        exit_reason="tp2",
        regime_at_entry="HTF_BEARISH",
        mode_at_entry="MODE_REBOUND_SHORT",
        rr_planned=1.5,
        rr_actual=2.5,
    )
    assert record.pnl == pytest.approx(expected_pnl)
    assert record.pnl > 0


# ---------------------------------------------------------------------------
# 10. BacktestEngine initialization
# ---------------------------------------------------------------------------


def test_backtest_engine_initialization_with_config():
    """BacktestEngine should initialize with correct config and empty state."""
    cfg = BacktestConfig(
        symbols=["ETHUSDT"],
        initial_balance=5000.0,
        commission_rate=0.0004,
    )
    engine = BacktestEngine(cfg)

    assert engine.config is cfg
    assert engine.balance == 5000.0
    assert engine.peak_balance == 5000.0
    assert engine.max_drawdown == 0.0
    assert engine.total_commission == 0.0
    assert len(engine.trade_records) == 0
    assert len(engine.decision_logs) == 0
    assert len(engine.pending_orders) == 0
    assert len(engine.setup_contexts) == 0
