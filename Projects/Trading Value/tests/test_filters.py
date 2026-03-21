"""Tests for trading_value.core.filters (Phase 5)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading_value.adapters.backtest import TradeRecord
from trading_value.core.filters import (
    ConditionStats,
    ConditionalFilter,
    TradeAnalysis,
    analyze_trades,
    check_conditional_filters,
    classify_session,
    format_analysis_report,
    format_filter_report,
    generate_filters,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trade(
    pnl: float,
    entry_hour: int = 10,
    weekday_offset: int = 0,  # 0=Mon
    strategy: str = "trend_long",
    regime: str = "HTF_BULLISH",
    pnl_r: float = 0.0,
) -> TradeRecord:
    # 2022-01-03 is a Monday
    base = datetime(2022, 1, 3 + weekday_offset, entry_hour, 0, tzinfo=timezone.utc)
    return TradeRecord(
        symbol="ETHUSDT",
        strategy=strategy,
        side="LONG",
        entry_price=2000.0,
        exit_price=2000.0 + pnl,
        qty=1.0,
        pnl=pnl,
        pnl_r=pnl_r,
        commission_total=0.0,
        entry_time=base,
        exit_time=base,
        duration_bars=4,
        exit_reason="tp1",
        regime_at_entry=regime,
        mode_at_entry="MODE_TREND_LONG",
        rr_planned=1.5,
        rr_actual=pnl_r,
    )


# ---------------------------------------------------------------------------
# classify_session
# ---------------------------------------------------------------------------

def test_classify_session_asia_hour_0():
    assert classify_session(0) == "Asia"


def test_classify_session_asia_hour_7():
    assert classify_session(7) == "Asia"


def test_classify_session_europe_hour_8():
    assert classify_session(8) == "Europe"


def test_classify_session_europe_hour_15():
    assert classify_session(15) == "Europe"


def test_classify_session_us_hour_16():
    assert classify_session(16) == "US"


def test_classify_session_us_hour_23():
    assert classify_session(23) == "US"


# ---------------------------------------------------------------------------
# analyze_trades
# ---------------------------------------------------------------------------

def test_analyze_trades_with_empty_list():
    result = analyze_trades([])
    assert result.total_trades == 0
    assert result.overall_win_rate == 0.0
    assert result.by_session == []


def test_analyze_trades_grouping_by_session():
    """Trades in different sessions should be grouped separately."""
    trades = [
        _make_trade(100.0, entry_hour=3),   # Asia
        _make_trade(-50.0, entry_hour=3),   # Asia
        _make_trade(80.0, entry_hour=10),   # Europe
        _make_trade(-30.0, entry_hour=20),  # US
    ]
    result = analyze_trades(trades)
    assert result.total_trades == 4
    session_names = [s.condition_value for s in result.by_session]
    assert "Asia" in session_names
    assert "Europe" in session_names
    assert "US" in session_names


def test_analyze_trades_win_rate_calculated_correctly():
    """3 wins / 5 total = 60% win rate."""
    trades = [
        _make_trade(100.0),
        _make_trade(50.0),
        _make_trade(75.0),
        _make_trade(-40.0),
        _make_trade(-20.0),
    ]
    result = analyze_trades(trades)
    assert result.overall_win_rate == pytest.approx(0.6)


def test_analyze_trades_by_strategy():
    trades = [
        _make_trade(100.0, strategy="trend_long"),
        _make_trade(-50.0, strategy="pullback_long"),
    ]
    result = analyze_trades(trades)
    strat_names = [s.condition_value for s in result.by_strategy]
    assert "trend_long" in strat_names
    assert "pullback_long" in strat_names


# ---------------------------------------------------------------------------
# generate_filters
# ---------------------------------------------------------------------------

def test_generate_filters_creates_filter_for_underperformer():
    """A condition with many losses and low win rate should produce a filter."""
    # Create 25 losing Asia trades to trigger filter (min_sample=20, win_rate < 0.35)
    bad_trades = [_make_trade(-100.0, entry_hour=3) for _ in range(25)]
    # Add some good overall trades so there is an overall win rate context
    good_trades = [_make_trade(200.0, entry_hour=10) for _ in range(30)]
    all_trades = bad_trades + good_trades

    analysis = analyze_trades(all_trades)
    filters = generate_filters(analysis, min_sample=20, max_win_rate=0.35)
    # Asia session should be blocked
    condition_names = [f.condition_name for f in filters]
    assert len(filters) >= 1
    # At least one filter about session or similar
    assert any(f.condition_name in ("session", "weekday", "strategy", "regime") for f in filters)


def test_generate_filters_small_sample_no_filter():
    """Conditions with sample < min_sample should not produce filters."""
    # Only 5 bad trades — below min_sample=20
    trades = [_make_trade(-100.0, entry_hour=3) for _ in range(5)]
    trades += [_make_trade(200.0, entry_hour=10) for _ in range(30)]
    analysis = analyze_trades(trades)
    filters = generate_filters(analysis, min_sample=20, max_win_rate=0.35)
    # The Asia group with 5 trades should not become a filter
    asia_filters = [f for f in filters if f.condition_name == "session" and "Asia" in f.condition_check]
    assert len(asia_filters) == 0


def test_generate_filters_good_performance_no_filter():
    """Conditions with high win rate should not produce filters."""
    # 25 winning Asia trades
    good_trades = [_make_trade(100.0, entry_hour=3) for _ in range(25)]
    analysis = analyze_trades(good_trades)
    filters = generate_filters(analysis, min_sample=20, max_win_rate=0.35)
    assert filters == []


# ---------------------------------------------------------------------------
# check_conditional_filters
# ---------------------------------------------------------------------------

def test_check_conditional_filters_matching_session_blocks():
    """A session filter should block matching entries."""
    f = ConditionalFilter(
        condition_name="session",
        condition_check="Entry during Asia session",
        block_reason="Asia underperforms",
        win_rate=0.20,
        sample_size=30,
        avg_pnl=-50.0,
    )
    ts = datetime(2022, 1, 3, 3, 0, tzinfo=timezone.utc)  # hour=3 -> Asia
    blocked, reason = check_conditional_filters([f], ts, "trend_long", "HTF_BULLISH", 0)
    assert blocked is True
    assert reason is not None


def test_check_conditional_filters_no_matching_filter_passes():
    """A filter for a different session should not block a different session entry."""
    f = ConditionalFilter(
        condition_name="session",
        condition_check="Entry during Asia session",
        block_reason="Asia underperforms",
        win_rate=0.20,
        sample_size=30,
        avg_pnl=-50.0,
    )
    # Europe session (hour=10)
    ts = datetime(2022, 1, 3, 10, 0, tzinfo=timezone.utc)
    blocked, reason = check_conditional_filters([f], ts, "trend_long", "HTF_BULLISH", 0)
    assert blocked is False
    assert reason is None


def test_check_conditional_filters_empty_filters_always_passes():
    ts = datetime(2022, 1, 3, 10, 0, tzinfo=timezone.utc)
    blocked, reason = check_conditional_filters([], ts, "trend_long", "HTF_BULLISH", 0)
    assert blocked is False
    assert reason is None


def test_check_conditional_filters_strategy_match():
    """Strategy filter blocks matching strategy."""
    f = ConditionalFilter(
        condition_name="strategy",
        condition_check="Strategy is pullback_long",
        block_reason="Pullback loses",
        win_rate=0.20,
        sample_size=25,
        avg_pnl=-30.0,
    )
    ts = datetime(2022, 1, 3, 10, 0, tzinfo=timezone.utc)
    blocked, reason = check_conditional_filters([f], ts, "pullback_long", "HTF_BULLISH", 0)
    assert blocked is True


# ---------------------------------------------------------------------------
# format_analysis_report
# ---------------------------------------------------------------------------

def test_format_analysis_report_returns_nonempty_string():
    trades = [_make_trade(100.0), _make_trade(-50.0)]
    analysis = analyze_trades(trades)
    report = format_analysis_report(analysis)
    assert isinstance(report, str)
    assert len(report) > 0
    assert "TRADE PATTERN ANALYSIS REPORT" in report


def test_format_analysis_report_empty_trades():
    analysis = analyze_trades([])
    report = format_analysis_report(analysis)
    assert isinstance(report, str)
    assert "Total trades" in report


# ---------------------------------------------------------------------------
# format_filter_report
# ---------------------------------------------------------------------------

def test_format_filter_report_returns_nonempty_string():
    report = format_filter_report([])
    assert isinstance(report, str)
    assert "CONDITIONAL ENTRY FILTERS" in report


def test_format_filter_report_with_filters():
    f = ConditionalFilter(
        condition_name="session",
        condition_check="Entry during Asia session",
        block_reason="reason",
        win_rate=0.20,
        sample_size=30,
        avg_pnl=-50.0,
    )
    report = format_filter_report([f])
    assert "Filter #1" in report
    assert "Asia" in report


# ---------------------------------------------------------------------------
# ConditionStats creation
# ---------------------------------------------------------------------------

def test_condition_stats_fields():
    stats = ConditionStats(
        condition_name="session",
        condition_value="Asia",
        total_trades=25,
        winning_trades=5,
        win_rate=0.20,
        avg_pnl=-40.0,
        avg_pnl_r=-0.5,
        is_significant=True,
    )
    assert stats.condition_name == "session"
    assert stats.condition_value == "Asia"
    assert stats.total_trades == 25
    assert stats.win_rate == pytest.approx(0.20)
    assert stats.is_significant is True
