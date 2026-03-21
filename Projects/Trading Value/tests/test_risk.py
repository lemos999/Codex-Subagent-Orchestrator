"""Tests for trading_value.core.risk — Phase 4.

Covers: RiskTracker, evaluate_risk_gate, record_trade_result,
        record_api_failure, record_api_success, is_slippage_alert,
        record_slippage, select_risk_pct.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from trading_value.core.models import RiskGate
from trading_value.core.risk import (
    RiskTracker,
    evaluate_risk_gate,
    is_slippage_alert,
    record_api_failure,
    record_api_success,
    record_slippage,
    record_trade_result,
    select_risk_pct,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_tracker(**kwargs) -> RiskTracker:
    return RiskTracker(**kwargs)


def ts(date_str: str = "2024-01-01", time_str: str = "12:00:00") -> datetime:
    return datetime.fromisoformat(f"{date_str}T{time_str}")


# ---------------------------------------------------------------------------
# evaluate_risk_gate
# ---------------------------------------------------------------------------

class TestEvaluateRiskGate:

    def test_normal_allow(self):
        tracker = make_tracker()
        result = evaluate_risk_gate(tracker)
        assert result == RiskGate.ALLOW

    def test_consecutive_losses_4_block(self):
        tracker = make_tracker(consecutive_losses=4)
        assert evaluate_risk_gate(tracker) == RiskGate.BLOCK

    def test_consecutive_losses_above_4_block(self):
        tracker = make_tracker(consecutive_losses=10)
        assert evaluate_risk_gate(tracker) == RiskGate.BLOCK

    def test_daily_pnl_exactly_minus3_block(self):
        tracker = make_tracker(daily_pnl_r=-3.0)
        assert evaluate_risk_gate(tracker) == RiskGate.BLOCK

    def test_daily_pnl_below_minus3_block(self):
        tracker = make_tracker(daily_pnl_r=-5.0)
        assert evaluate_risk_gate(tracker) == RiskGate.BLOCK

    def test_api_failures_3_block(self):
        tracker = make_tracker(api_failure_count=3)
        assert evaluate_risk_gate(tracker) == RiskGate.BLOCK

    def test_api_failures_above_3_block(self):
        tracker = make_tracker(api_failure_count=5)
        assert evaluate_risk_gate(tracker) == RiskGate.BLOCK

    def test_slippage_alert_block(self):
        # history: [1.0, 1.0, 1.0, 4.0] — last >= avg(prev) * 2.0
        tracker = make_tracker(slippage_history=[1.0, 1.0, 1.0, 4.0])
        assert evaluate_risk_gate(tracker) == RiskGate.BLOCK

    def test_counter_trend_reduce(self):
        tracker = make_tracker()
        result = evaluate_risk_gate(tracker, is_counter_trend=True)
        assert result == RiskGate.REDUCE

    def test_abnormal_volatility_reduce(self):
        tracker = make_tracker()
        result = evaluate_risk_gate(tracker, is_abnormal_volatility=True)
        assert result == RiskGate.REDUCE

    def test_consecutive_losses_2_reduce(self):
        tracker = make_tracker(consecutive_losses=2)
        assert evaluate_risk_gate(tracker) == RiskGate.REDUCE

    def test_consecutive_losses_3_reduce(self):
        tracker = make_tracker(consecutive_losses=3)
        assert evaluate_risk_gate(tracker) == RiskGate.REDUCE

    def test_block_takes_priority_over_counter_trend(self):
        # consecutive_losses=4 -> BLOCK even when is_counter_trend=True
        tracker = make_tracker(consecutive_losses=4)
        assert evaluate_risk_gate(tracker, is_counter_trend=True) == RiskGate.BLOCK

    def test_daily_pnl_minus2_allow(self):
        tracker = make_tracker(daily_pnl_r=-2.0)
        assert evaluate_risk_gate(tracker) == RiskGate.ALLOW

    def test_weekly_pnl_limit_block(self):
        tracker = make_tracker(weekly_pnl_r=-10.0)
        assert evaluate_risk_gate(tracker) == RiskGate.BLOCK


# ---------------------------------------------------------------------------
# record_trade_result
# ---------------------------------------------------------------------------

class TestRecordTradeResult:

    def test_win_resets_consecutive_losses(self):
        tracker = make_tracker(consecutive_losses=3, current_date="2024-01-01", current_week="2024-W01")
        new = record_trade_result(tracker, pnl_r=1.0, timestamp=ts("2024-01-01"))
        assert new.consecutive_losses == 0

    def test_loss_increments_consecutive(self):
        tracker = make_tracker(consecutive_losses=1, current_date="2024-01-01", current_week="2024-W01")
        new = record_trade_result(tracker, pnl_r=-0.5, timestamp=ts("2024-01-01"))
        assert new.consecutive_losses == 2

    def test_daily_pnl_accumulates(self):
        tracker = make_tracker(daily_pnl_r=-1.0, current_date="2024-01-01", current_week="2024-W01")
        new = record_trade_result(tracker, pnl_r=-1.5, timestamp=ts("2024-01-01"))
        assert abs(new.daily_pnl_r - (-2.5)) < 1e-9

    def test_daily_rollover_resets_daily_pnl(self):
        tracker = make_tracker(
            daily_pnl_r=-2.0,
            current_date="2024-01-01",
            current_week="2024-W01",
        )
        new = record_trade_result(tracker, pnl_r=-0.5, timestamp=ts("2024-01-02"))
        # After rollover, daily_pnl starts from 0 then adds -0.5
        assert abs(new.daily_pnl_r - (-0.5)) < 1e-9
        assert new.current_date == "2024-01-02"

    def test_weekly_rollover_resets_weekly_pnl(self):
        tracker = make_tracker(
            weekly_pnl_r=-5.0,
            current_date="2024-01-07",
            current_week="2024-W01",
        )
        # Move to a new week
        new = record_trade_result(tracker, pnl_r=2.0, timestamp=ts("2024-01-08"))
        assert abs(new.weekly_pnl_r - 2.0) < 1e-9
        assert new.current_week != "2024-W01"

    def test_first_loss_sets_consecutive_to_1(self):
        tracker = make_tracker(consecutive_losses=0, current_date="2024-01-01", current_week="2024-W01")
        new = record_trade_result(tracker, pnl_r=-1.0, timestamp=ts("2024-01-01"))
        assert new.consecutive_losses == 1

    def test_zero_pnl_treated_as_win(self):
        tracker = make_tracker(consecutive_losses=2, current_date="2024-01-01", current_week="2024-W01")
        new = record_trade_result(tracker, pnl_r=0.0, timestamp=ts("2024-01-01"))
        assert new.consecutive_losses == 0


# ---------------------------------------------------------------------------
# record_api_failure / record_api_success
# ---------------------------------------------------------------------------

class TestApiFailureTracking:

    def test_record_api_failure_increments(self):
        tracker = make_tracker(api_failure_count=1)
        new = record_api_failure(tracker)
        assert new.api_failure_count == 2

    def test_record_api_failure_from_zero(self):
        tracker = make_tracker()
        new = record_api_failure(tracker)
        assert new.api_failure_count == 1

    def test_record_api_success_resets_count(self):
        tracker = make_tracker(api_failure_count=5)
        new = record_api_success(tracker)
        assert new.api_failure_count == 0

    def test_record_api_success_already_zero(self):
        tracker = make_tracker(api_failure_count=0)
        new = record_api_success(tracker)
        assert new.api_failure_count == 0


# ---------------------------------------------------------------------------
# is_slippage_alert
# ---------------------------------------------------------------------------

class TestIsSlippageAlert:

    def test_no_history_no_alert(self):
        tracker = make_tracker(slippage_history=[])
        assert is_slippage_alert(tracker) is False

    def test_single_entry_no_alert(self):
        tracker = make_tracker(slippage_history=[5.0])
        assert is_slippage_alert(tracker) is False

    def test_exactly_2x_avg_triggers(self):
        # avg([1.0]) = 1.0, latest = 2.0 => 2.0 >= 1.0 * 2.0 -> True
        tracker = make_tracker(slippage_history=[1.0, 2.0])
        assert is_slippage_alert(tracker) is True

    def test_below_2x_no_alert(self):
        # avg([1.0]) = 1.0, latest = 1.9 < 2.0 -> False
        tracker = make_tracker(slippage_history=[1.0, 1.9])
        assert is_slippage_alert(tracker) is False

    def test_above_2x_avg_triggers(self):
        # avg([1.0, 1.0, 1.0]) = 1.0, latest = 3.0 >= 2.0 -> True
        tracker = make_tracker(slippage_history=[1.0, 1.0, 1.0, 3.0])
        assert is_slippage_alert(tracker) is True

    def test_zero_avg_no_alert(self):
        # avg([0.0]) = 0.0 -> guard prevents division
        tracker = make_tracker(slippage_history=[0.0, 5.0])
        assert is_slippage_alert(tracker) is False

    def test_boundary_just_below_2x(self):
        # latest = 1.999, avg = 1.0 -> 1.999 < 2.0 -> False
        tracker = make_tracker(slippage_history=[1.0, 1.999])
        assert is_slippage_alert(tracker) is False


# ---------------------------------------------------------------------------
# select_risk_pct
# ---------------------------------------------------------------------------

class TestSelectRiskPct:

    def test_block_returns_zero(self):
        assert select_risk_pct(RiskGate.BLOCK, is_counter_trend=False) == 0.0

    def test_block_counter_trend_still_zero(self):
        assert select_risk_pct(RiskGate.BLOCK, is_counter_trend=True) == 0.0

    def test_reduce_returns_counter_trend_pct(self):
        # REDUCE -> min(default_pct=0.0035, counter_trend_pct=0.0025) = 0.0025
        result = select_risk_pct(RiskGate.REDUCE, is_counter_trend=False)
        assert abs(result - 0.0025) < 1e-9

    def test_allow_normal_returns_default(self):
        result = select_risk_pct(RiskGate.ALLOW, is_counter_trend=False)
        assert abs(result - 0.0035) < 1e-9

    def test_allow_counter_trend_returns_counter_trend_pct(self):
        result = select_risk_pct(RiskGate.ALLOW, is_counter_trend=True)
        assert abs(result - 0.0025) < 1e-9

    def test_custom_default_pct(self):
        result = select_risk_pct(RiskGate.ALLOW, is_counter_trend=False, default_pct=0.005)
        assert abs(result - 0.005) < 1e-9
