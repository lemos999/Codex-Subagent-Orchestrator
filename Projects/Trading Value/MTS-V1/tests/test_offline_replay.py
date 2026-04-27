from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pandas as pd

from offline_replay import (
    OfflineReplay,
    ReplayClock,
    ReplayPosition,
    align_security_frame_to_base_close,
    intrabar_limit_fill_price,
    load_15m_cache,
    marketable_limit_fill_price,
    pandas_timeframe,
    parse_symbol_float_map,
    pine_contract_qty,
    reverse_spike_ratio,
    state2_trigger_source,
    timeframe_delta,
)
from strategy import (
    Candle,
    StateCode,
    StateMachine,
    StrategyStateSnapshot,
    TradeSide,
    base_layer_fraction,
)


def _replay_stub() -> OfflineReplay:
    replay = OfflineReplay.__new__(OfflineReplay)
    replay.events = []
    replay.state2_exit_mode = "all"
    replay.state2_signal_mode = "any"
    replay.state2_profit_hold_r = None
    replay.l3_max_distance_atr = None
    replay.reverse_spike_multiplier = 3.0
    replay.symbol_reverse_spike_multipliers = {}
    replay.reverse_spike_min_ratio = 1.0
    replay.reverse_spike_confirm_bars = 1
    replay.state2_reverse_min_minutes_since_l2 = 0.0
    replay.symbol_cooldowns = {}
    replay.cvd_entry_mode = "pine-ltf"
    return replay


def test_pandas_timeframe_normalizes_supported_replay_values() -> None:
    assert pandas_timeframe("15m") == "15min"
    assert pandas_timeframe("60") == "1h"
    assert pandas_timeframe("4h") == "4h"
    assert timeframe_delta("30m").total_seconds() == 1800


def test_state2_trigger_source_labels_signal_families() -> None:
    assert state2_trigger_source(reverse=True, htf_cross=False) == "reverse_spike"
    assert state2_trigger_source(reverse=False, htf_cross=True) == "htf_cross"
    assert state2_trigger_source(reverse=True, htf_cross=True) == "both"
    assert state2_trigger_source(reverse=False, htf_cross=False) == "unknown"


def test_reverse_spike_ratio_uses_adverse_direction() -> None:
    assert reverse_spike_ratio(side=TradeSide.LONG, cvd_delta=-12.0, threshold=3.0) == 4.0
    assert reverse_spike_ratio(side=TradeSide.SHORT, cvd_delta=12.0, threshold=3.0) == 4.0
    assert reverse_spike_ratio(side=TradeSide.LONG, cvd_delta=12.0, threshold=3.0) == -4.0


def test_execution_span_advances_without_replaying_signal_bar() -> None:
    replay = _replay_stub()
    start = datetime(2026, 4, 24, 0, 0, tzinfo=UTC)
    candles = [
        Candle(start + timedelta(minutes=minute), 1.0, 2.0, 0.5, 1.5, 10.0)
        for minute in (0, 15, 30, 45, 60)
    ]

    span, next_index = replay._execution_span(
        candles,
        0,
        datetime(2026, 4, 24, 0, 0, tzinfo=UTC),
        datetime(2026, 4, 24, 1, 0, tzinfo=UTC),
    )
    next_span, final_index = replay._execution_span(
        candles,
        next_index,
        datetime(2026, 4, 24, 1, 0, tzinfo=UTC),
        datetime(2026, 4, 24, 2, 0, tzinfo=UTC),
    )

    assert [candle.timestamp.minute for candle in span] == [0, 15, 30, 45]
    assert [candle.timestamp.minute for candle in next_span] == [0]
    assert final_index == len(candles)


def test_aggregate_execution_span_preserves_intrabar_extremes() -> None:
    replay = _replay_stub()
    candles = [
        Candle(datetime(2026, 4, 24, 0, 0, tzinfo=UTC), 10.0, 11.0, 9.0, 10.5, 1.0),
        Candle(datetime(2026, 4, 24, 0, 15, tzinfo=UTC), 10.5, 13.0, 10.0, 12.0, 2.0),
    ]

    result = replay._aggregate_execution_span(candles)

    assert result is not None
    assert result.open == 10.0
    assert result.high == 13.0
    assert result.low == 9.0
    assert result.close == 12.0
    assert result.volume == 3.0


def test_htf_security_frame_aligns_to_last_base_bar_before_close() -> None:
    frame = pd.DataFrame(
        {
            "ts": [pd.Timestamp("2026-04-24T00:00:00Z")],
            "open": [1.0],
            "high": [2.0],
            "low": [0.5],
            "close": [1.5],
            "volume": [10.0],
        },
    )

    aligned = align_security_frame_to_base_close(frame, "4h", "15min")

    assert aligned["ts"].iloc[0] == pd.Timestamp("2026-04-24T03:45:00Z")


def test_symbol_htf_cross_only_pulses_on_aligned_htf_update_bar() -> None:
    replay = _replay_stub()
    start = datetime(2026, 4, 1, tzinfo=UTC)
    candles = [
        Candle(
            start + timedelta(hours=4 * index),
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1.0,
        )
        for index in range(60)
    ]
    aligned_update_ts = candles[-1].timestamp
    candles[-2] = Candle(candles[-2].timestamp, 100.0, 110.0, 90.0, 105.0, 1.0)
    candles[-1] = Candle(aligned_update_ts, 100.0, 110.0, 80.0, 90.0, 1.0)

    assert replay._symbol_htf_crosses(candles, aligned_update_ts) == (True, False)
    assert replay._symbol_htf_crosses(
        candles,
        aligned_update_ts + timedelta(minutes=15),
    ) == (False, False)


def test_precomputed_htf_cross_cache_matches_direct_update_bar_logic() -> None:
    replay = _replay_stub()
    start = datetime(2026, 4, 1, tzinfo=UTC)
    candles = [
        Candle(
            start + timedelta(hours=4 * index),
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1.0,
        )
        for index in range(60)
    ]
    candles[-1] = Candle(candles[-1].timestamp, 100.0, 110.0, 80.0, 90.0, 1.0)

    cache = replay._precompute_htf_crosses(candles)

    assert cache[candles[-1].timestamp] == replay._symbol_htf_crosses(
        candles,
        candles[-1].timestamp,
    )
    assert cache.get(candles[-1].timestamp + timedelta(minutes=15), (False, False)) == (
        False,
        False,
    )


def test_marketable_limit_fills_at_close_for_process_orders_on_close() -> None:
    assert marketable_limit_fill_price(TradeSide.LONG, 101.0, 100.0) == 100.0
    assert marketable_limit_fill_price(TradeSide.SHORT, 99.0, 100.0) == 100.0
    assert marketable_limit_fill_price(TradeSide.LONG, 99.0, 100.0) is None
    assert marketable_limit_fill_price(TradeSide.SHORT, 101.0, 100.0) is None


def test_active_limit_fill_uses_open_when_bar_opens_through_limit() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    long_gap = Candle(ts, open=98.0, high=101.0, low=97.0, close=100.0, volume=10.0)
    short_gap = Candle(ts, open=102.0, high=103.0, low=99.0, close=100.0, volume=10.0)
    long_touch = Candle(ts, open=101.0, high=102.0, low=99.0, close=101.0, volume=10.0)
    short_touch = Candle(ts, open=99.0, high=101.0, low=98.0, close=99.0, volume=10.0)

    assert intrabar_limit_fill_price(TradeSide.LONG, 100.0, long_gap) == 98.0
    assert intrabar_limit_fill_price(TradeSide.SHORT, 100.0, short_gap) == 102.0
    assert intrabar_limit_fill_price(TradeSide.LONG, 100.0, long_touch) == 100.0
    assert intrabar_limit_fill_price(TradeSide.SHORT, 100.0, short_touch) == 100.0


def test_pending_l1_timeout_uses_48h_not_48_entry_bars() -> None:
    entry_ts = datetime(2026, 4, 20, 15, 15, tzinfo=UTC)
    fill_ts = entry_ts + timedelta(hours=26)
    replay = _replay_stub()
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.PENDING),
        side=TradeSide.LONG.value,
        entry_prices={"L1": 100.0, "L2": 90.0, "L3": 80.0},
        entry_started_bar=0,
    )
    active = ReplayPosition(
        machine=StateMachine(snapshot, now_fn=lambda: fill_ts),
        side=TradeSide.LONG,
        entry_ts=entry_ts,
        entry_index=0,
        entry_cvd_sign=1,
    )

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(fill_ts, open=101.0, high=102.0, low=99.0, close=101.0, volume=10.0),
        prev_candle=Candle(fill_ts - timedelta(minutes=15), 101.0, 102.0, 100.0, 101.0, 10.0),
        index=104,
        indicators={
            "atr": 10.0,
            "val": 80.0,
            "vah": 120.0,
            "fibo_long_0618": 90.0,
            "fibo_long_0786": 80.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is active
    assert active.machine.snapshot.state == int(StateCode.FILLED_PARTIAL)
    assert replay.events[-1]["event"] == "ENTRY_L1"
    assert replay.events[-1]["price"] == 100.0


def test_pending_l1_timeout_fires_after_48h_elapsed() -> None:
    entry_ts = datetime(2026, 4, 20, 15, 15, tzinfo=UTC)
    timeout_ts = entry_ts + timedelta(hours=48)
    replay = _replay_stub()
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.PENDING),
        side=TradeSide.LONG.value,
        entry_prices={"L1": 100.0, "L2": 90.0, "L3": 80.0},
        entry_started_bar=0,
    )
    active = ReplayPosition(
        machine=StateMachine(snapshot, now_fn=lambda: timeout_ts),
        side=TradeSide.LONG,
        entry_ts=entry_ts,
        entry_index=0,
        entry_cvd_sign=1,
    )

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(timeout_ts, open=101.0, high=102.0, low=101.0, close=101.0, volume=10.0),
        prev_candle=Candle(timeout_ts - timedelta(minutes=15), 101.0, 102.0, 100.0, 101.0, 10.0),
        index=192,
        indicators={},
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is None
    assert active.machine.snapshot.state == int(StateCode.IDLE)


def test_parse_symbol_float_map_accepts_asset_overrides() -> None:
    assert parse_symbol_float_map("BTC=6.3, ETH=6.8") == {"BTC": 6.3, "ETH": 6.8}


def test_pine_contract_qty_scales_equity_fraction_by_order_price() -> None:
    assert pine_contract_qty(0.25, 100.0) == 0.0025


def test_symbol_reverse_spike_multiplier_prefers_asset_override() -> None:
    replay = _replay_stub()
    replay.reverse_spike_multiplier = 3.0
    replay.symbol_reverse_spike_multipliers = {"BTC": 6.3}

    assert replay._reverse_spike_multiplier("BTC/USDT:USDT") == 6.3
    assert replay._reverse_spike_multiplier("ETH/USDT:USDT") == 3.0


def test_reverse_spike_min_ratio_filters_threshold_edge_pulse() -> None:
    replay = _replay_stub()
    indicators = {
        "entry_cvd_delta": -100.4,
        "reverse_spike_threshold": 100.0,
        "reverse_spike_long": 1.0,
    }

    assert replay._reverse_spike_against(TradeSide.LONG, indicators) is True

    replay.reverse_spike_min_ratio = 1.005

    assert replay._reverse_spike_against(TradeSide.LONG, indicators) is False


def test_reverse_spike_min_ratio_keeps_strong_pulse() -> None:
    replay = _replay_stub()
    replay.reverse_spike_min_ratio = 1.005

    assert (
        replay._reverse_spike_against(
            TradeSide.SHORT,
            {
                "entry_cvd_delta": 120.0,
                "reverse_spike_threshold": 100.0,
                "reverse_spike_short": 1.0,
            },
        )
        is True
    )


def test_reverse_spike_confirm_bars_requires_previous_pulse() -> None:
    replay = _replay_stub()
    replay.reverse_spike_confirm_bars = 2

    assert (
        replay._reverse_spike_against(
            TradeSide.LONG,
            {
                "entry_cvd_delta": -120.0,
                "reverse_spike_threshold": 100.0,
                "reverse_spike_long": 1.0,
                "reverse_spike_long_prev": 0.0,
            },
        )
        is False
    )
    assert (
        replay._reverse_spike_against(
            TradeSide.LONG,
            {
                "entry_cvd_delta": -120.0,
                "reverse_spike_threshold": 100.0,
                "reverse_spike_long": 1.0,
                "reverse_spike_long_prev": 1.0,
            },
        )
        is True
    )


def test_spec_30m_cvd_entry_mode_uses_two_bars_for_15m_entry_timeframe() -> None:
    replay = _replay_stub()
    replay.entry_timeframe = "15min"
    replay.cvd_entry_mode = "spec-30m"

    assert replay._entry_cvd_delta([1.0, -2.0, 4.0]) == 2.0


def test_pine_ltf_cvd_entry_mode_uses_current_ltf_delta() -> None:
    replay = _replay_stub()
    replay.entry_timeframe = "15min"
    replay.cvd_entry_mode = "pine-ltf"

    assert replay._entry_cvd_delta([1.0, -2.0, 4.0]) == 4.0


def test_maybe_enter_blocks_fibo_temporal_invalid_signal(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    replay = _replay_stub()
    replay._btc_context = lambda _ts: (101.0, 100.0)  # type: ignore[method-assign]
    ts = datetime(2026, 4, 24, tzinfo=UTC)

    monkeypatch.setattr(StateMachine, "evaluate_entry_trigger", lambda *_, **__: True)

    def fail_place_layers(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("temporally invalid fibo anchor should block layer placement")

    monkeypatch.setattr(StateMachine, "place_layers", fail_place_layers)

    result = replay._maybe_enter(
        symbol="BTC/USDT:USDT",
        candle=Candle(ts, open=100.0, high=101.0, low=99.0, close=100.5, volume=10.0),
        prev_candle=Candle(ts - timedelta(minutes=15), 99.0, 100.0, 98.0, 99.5, 10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "entry_cvd_delta": 1.0,
            "kijun": 100.0,
            "poc": 100.0,
            "val": 95.0,
            "vah": 105.0,
            "fibo_long_0618": 98.0,
            "fibo_long_0786": 96.0,
            "fibo_short_0618": 102.0,
            "fibo_short_0786": 104.0,
            "fibo_long_temporal_valid": 0.0,
            "fibo_short_temporal_valid": 0.0,
        },
        prev_kijun=99.0,
    )

    assert result is None
    assert replay.events == []


def test_maybe_enter_records_marketable_l1_on_signal_close(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    replay = _replay_stub()
    replay._btc_context = lambda _ts: (101.0, 100.0)  # type: ignore[method-assign]
    ts = datetime(2026, 4, 24, tzinfo=UTC)

    monkeypatch.setattr(StateMachine, "evaluate_entry_trigger", lambda *_, **__: True)

    active = replay._maybe_enter(
        symbol="BTC/USDT:USDT",
        candle=Candle(ts, open=100.5, high=101.0, low=99.5, close=100.0, volume=10.0),
        prev_candle=Candle(ts - timedelta(minutes=15), 99.0, 100.0, 98.0, 99.5, 10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "entry_cvd_delta": 1.0,
            "kijun": 100.0,
            "poc": 100.0,
            "val": 95.0,
            "vah": 105.0,
            "fibo_long_0618": 90.0,
            "fibo_long_0786": 85.0,
            "fibo_short_0618": 110.0,
            "fibo_short_0786": 115.0,
            "fibo_long_temporal_valid": 1.0,
            "fibo_short_temporal_valid": 1.0,
        },
        prev_kijun=99.0,
    )

    assert active is not None
    assert [(event["event"], event["price"]) for event in replay.events] == [
        ("ENTRY_SIGNAL", 100.0),
        ("ENTRY_L1", 100.0),
    ]


def test_hard_sl_exit_records_nonzero_rr_after_state_reset() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.LONG.value,
        avg_entry=100.0,
        hard_sl=90.0,
        remaining_position_fraction=1.0,
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts,
        entry_index=0,
        entry_cvd_sign=1,
    )
    candle = Candle(ts, open=100.0, high=101.0, low=89.0, close=95.0, volume=10.0)
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=candle,
        prev_candle=Candle(ts, open=101.0, high=102.0, low=100.0, close=100.0, volume=10.0),
        index=1,
        indicators={},
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is None
    assert replay.events[-1]["reason"] == "HARD_SL"
    assert replay.events[-1]["price"] == 90.0
    assert replay.events[-1]["rr"] == -1.0
    assert replay._symbol_cooldown_active("BTC/USDT:USDT", ts + timedelta(hours=23))
    assert not replay._symbol_cooldown_active("BTC/USDT:USDT", ts + timedelta(hours=24))


def test_hard_sl_replay_ignores_one_tick_boundary_touch() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.LONG.value,
        avg_entry=100.0,
        hard_sl=90.05,
        remaining_position_fraction=1.0,
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts,
        entry_index=0,
        entry_cvd_sign=1,
    )
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=100.0, high=101.0, low=90.0, close=95.0, volume=10.0),
        prev_candle=Candle(ts, open=101.0, high=102.0, low=100.0, close=100.0, volume=10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "reverse_spike_long": 0.0,
            "htf_cross_long": 0.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is active
    assert replay.events == []


def test_hard_sl_cooldown_uses_exit_bar_time_not_entry_time() -> None:
    entry_ts = datetime(2026, 4, 23, tzinfo=UTC)
    exit_ts = datetime(2026, 4, 24, tzinfo=UTC)
    clock = ReplayClock(entry_ts)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.LONG.value,
        avg_entry=100.0,
        hard_sl=90.0,
        remaining_position_fraction=1.0,
    )
    machine = StateMachine(snapshot, now_fn=clock.now)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=entry_ts,
        entry_index=0,
        entry_cvd_sign=1,
        clock=clock,
    )
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(exit_ts, open=100.0, high=101.0, low=89.0, close=95.0, volume=10.0),
        prev_candle=Candle(exit_ts, open=101.0, high=102.0, low=100.0, close=100.0, volume=10.0),
        index=1,
        indicators={},
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is None
    assert replay._symbol_cooldown_active("BTC/USDT:USDT", exit_ts + timedelta(hours=23))
    assert not replay._symbol_cooldown_active("BTC/USDT:USDT", exit_ts + timedelta(hours=24))


def test_symbol_cooldown_blocks_new_entry_after_exit(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    replay = _replay_stub()
    replay._btc_context = lambda _ts: (101.0, 100.0)  # type: ignore[method-assign]
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    replay.symbol_cooldowns["BTC/USDT:USDT"] = ts + timedelta(hours=1)
    monkeypatch.setattr(StateMachine, "evaluate_entry_trigger", lambda *_, **__: True)

    result = replay._maybe_enter(
        symbol="BTC/USDT:USDT",
        candle=Candle(ts, open=100.0, high=101.0, low=99.0, close=100.5, volume=10.0),
        prev_candle=Candle(ts - timedelta(minutes=15), 99.0, 100.0, 98.0, 99.5, 10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "entry_cvd_delta": 1.0,
            "kijun": 100.0,
            "poc": 100.0,
            "val": 95.0,
            "vah": 105.0,
            "fibo_long_0618": 98.0,
            "fibo_long_0786": 96.0,
            "fibo_short_0618": 102.0,
            "fibo_short_0786": 104.0,
            "fibo_long_temporal_valid": 1.0,
            "fibo_short_temporal_valid": 1.0,
        },
        prev_kijun=99.0,
    )

    assert result is None
    assert replay.events == []


def test_pending_l1_fill_can_cascade_l2_on_same_bar() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.PENDING),
        side=TradeSide.LONG.value,
        entry_prices={"L1": 100.0, "L2": 95.0, "L3": 90.0},
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts,
        entry_index=0,
        entry_cvd_sign=1,
    )
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=101.0, high=102.0, low=94.0, close=94.0, volume=10.0),
        prev_candle=Candle(ts - timedelta(minutes=15), 100.0, 101.0, 99.0, 100.0, 10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "poc": 100.0,
            "kijun": 100.0,
            "fibo_long_0618": 95.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is active
    assert [(event["event"], event["ts"]) for event in replay.events] == [
        ("ENTRY_L1", "2026-04-24T00:00:00Z"),
        ("ENTRY_L2", "2026-04-24T00:00:00Z"),
    ]
    assert replay.events[-1]["price"] == 94.0
    assert replay.events[-1]["reason"] == "L2_FILL_ON_CLOSE"
    assert machine.snapshot.entry_prices["L2"] == 95.0
    assert active.pending_l2_fill_price == 94.0


def test_pending_l1_fill_refreshes_child_layers_once_on_fill_bar() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.PENDING),
        side=TradeSide.LONG.value,
        entry_prices={"L1": 100.0, "L2": 90.0, "L3": 85.0},
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts - timedelta(minutes=15),
        entry_index=0,
        entry_cvd_sign=1,
    )
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=101.0, high=102.0, low=96.0, close=99.0, volume=10.0),
        prev_candle=Candle(ts - timedelta(minutes=15), 100.0, 101.0, 99.0, 100.0, 10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "poc": 100.0,
            "kijun": 100.0,
            "fibo_long_0618": 95.0,
            "fibo_long_0786": 90.0,
            "val": 88.0,
            "vah": 105.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is active
    assert machine.snapshot.entry_prices["L2"] == 95.0
    assert machine.snapshot.entry_prices["L3"] == 88.0
    assert [event["event"] for event in replay.events] == ["ENTRY_L1"]


def test_signal_close_l1_refreshes_unfilled_child_layers_on_next_bar(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    replay = _replay_stub()
    replay._btc_context = lambda _ts: (101.0, 100.0)  # type: ignore[method-assign]
    ts = datetime(2026, 4, 24, tzinfo=UTC)

    monkeypatch.setattr(StateMachine, "evaluate_entry_trigger", lambda *_, **__: True)

    active = replay._maybe_enter(
        symbol="BTC/USDT:USDT",
        candle=Candle(ts, open=100.5, high=101.0, low=99.5, close=100.0, volume=10.0),
        prev_candle=Candle(ts - timedelta(minutes=15), 99.0, 100.0, 98.0, 99.5, 10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "entry_cvd_delta": 1.0,
            "kijun": 100.0,
            "poc": 100.0,
            "val": 95.0,
            "vah": 105.0,
            "fibo_long_0618": 90.0,
            "fibo_long_0786": 85.0,
            "fibo_short_0618": 110.0,
            "fibo_short_0786": 115.0,
            "fibo_long_temporal_valid": 1.0,
            "fibo_short_temporal_valid": 1.0,
        },
        prev_kijun=99.0,
    )

    assert active is not None
    assert active.refresh_child_layers_on_next_bar

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(
            ts + timedelta(minutes=15),
            open=100.0,
            high=101.0,
            low=94.0,
            close=99.0,
            volume=10.0,
        ),
        prev_candle=Candle(ts, 100.5, 101.0, 99.5, 100.0, 10.0),
        index=2,
        indicators={
            "atr": 10.0,
            "poc": 100.0,
            "kijun": 100.0,
            "fibo_long_0618": 95.0,
            "fibo_long_0786": 90.0,
            "val": 88.0,
            "vah": 105.0,
            "reverse_spike_long": 0.0,
            "htf_cross_long": 0.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is active
    assert not active.refresh_child_layers_on_next_bar
    assert active.machine.snapshot.entry_prices["L2"] == 95.0
    assert active.machine.snapshot.entry_prices["L3"] == 88.0
    assert [event["event"] for event in replay.events] == ["ENTRY_SIGNAL", "ENTRY_L1"]


def test_signal_close_l1_child_layer_can_fill_on_creation_bar_close(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    replay = _replay_stub()
    replay._btc_context = lambda _ts: (101.0, 100.0)  # type: ignore[method-assign]
    ts = datetime(2026, 4, 24, tzinfo=UTC)

    monkeypatch.setattr(StateMachine, "evaluate_entry_trigger", lambda *_, **__: True)

    active = replay._maybe_enter(
        symbol="BTC/USDT:USDT",
        candle=Candle(ts, open=100.5, high=101.0, low=99.5, close=100.0, volume=10.0),
        prev_candle=Candle(ts - timedelta(minutes=15), 99.0, 100.0, 98.0, 99.5, 10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "entry_cvd_delta": 1.0,
            "kijun": 100.0,
            "poc": 100.0,
            "val": 95.0,
            "vah": 105.0,
            "fibo_long_0618": 90.0,
            "fibo_long_0786": 85.0,
            "fibo_short_0618": 110.0,
            "fibo_short_0786": 115.0,
            "fibo_long_temporal_valid": 1.0,
            "fibo_short_temporal_valid": 1.0,
        },
        prev_kijun=99.0,
    )

    assert active is not None

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(
            ts + timedelta(minutes=15),
            open=100.0,
            high=101.0,
            low=94.0,
            close=94.0,
            volume=10.0,
        ),
        prev_candle=Candle(ts, 100.5, 101.0, 99.5, 100.0, 10.0),
        index=2,
        indicators={
            "atr": 10.0,
            "poc": 100.0,
            "kijun": 100.0,
            "fibo_long_0618": 95.0,
            "fibo_long_0786": 90.0,
            "val": 88.0,
            "vah": 105.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is active
    assert replay.events[-1]["event"] == "ENTRY_L2"
    assert replay.events[-1]["reason"] == "L2_FILL_ON_CLOSE"
    assert replay.events[-1]["price"] == 94.0


def test_partial_position_does_not_refresh_child_layers_after_order_creation() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.LONG.value,
        entry_prices={"L1": 100.0, "L2": 95.0, "L3": 90.0},
        fill_qtys={"L1": base_layer_fraction("L1"), "L2": 0.0, "L3": 0.0},
        avg_entry=100.0,
        remaining_position_fraction=base_layer_fraction("L1"),
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts - timedelta(minutes=15),
        entry_index=0,
        entry_cvd_sign=1,
        refresh_child_layers_on_next_bar=False,
    )
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=100.0, high=101.0, low=96.0, close=99.0, volume=10.0),
        prev_candle=Candle(ts - timedelta(minutes=15), 100.0, 101.0, 99.0, 100.0, 10.0),
        index=2,
        indicators={
            "atr": 10.0,
            "poc": 100.0,
            "kijun": 100.0,
            "fibo_long_0618": 97.0,
            "fibo_long_0786": 90.0,
            "val": 88.0,
            "vah": 105.0,
            "reverse_spike_long": 0.0,
            "htf_cross_long": 0.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is active
    assert machine.snapshot.entry_prices["L2"] == 95.0
    assert [event["event"] for event in replay.events] == []


def test_pending_l1_fill_does_not_cascade_l2_from_preexisting_same_bar_low() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.PENDING),
        side=TradeSide.LONG.value,
        entry_prices={"L1": 100.0, "L2": 95.0, "L3": 90.0},
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts,
        entry_index=0,
        entry_cvd_sign=1,
    )
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=101.0, high=102.0, low=94.0, close=99.0, volume=10.0),
        prev_candle=Candle(ts - timedelta(minutes=15), 100.0, 101.0, 99.0, 100.0, 10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "poc": 100.0,
            "kijun": 100.0,
            "fibo_long_0618": 95.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is active
    assert [event["event"] for event in replay.events] == ["ENTRY_L1"]
    assert machine.snapshot.state == int(StateCode.FILLED_PARTIAL)


def test_active_l1_fill_uses_order_price_for_contract_qty() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.PENDING),
        side=TradeSide.LONG.value,
        entry_prices={"L1": 100.0, "L2": 95.0, "L3": 90.0},
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts,
        entry_index=0,
        entry_cvd_sign=1,
    )
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=99.0, high=100.0, low=98.0, close=99.5, volume=10.0),
        prev_candle=Candle(ts - timedelta(minutes=15), 101.0, 102.0, 100.0, 101.0, 10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "poc": 120.0,
            "kijun": 100.0,
            "fibo_long_0618": 95.0,
            "fibo_long_0786": 90.0,
            "val": 88.0,
            "vah": 125.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is active
    assert replay.events[-1]["price"] == 99.0
    assert machine.snapshot.fill_qtys["L1"] == pine_contract_qty(
        base_layer_fraction("L1"),
        100.0,
    )


def test_l2_fill_uses_order_price_for_contract_qty_when_fill_improves() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    l1_qty = pine_contract_qty(base_layer_fraction("L1"), 100.0)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.LONG.value,
        entry_prices={"L1": 100.0, "L2": 95.0, "L3": 90.0},
        fill_qtys={"L1": l1_qty, "L2": 0.0, "L3": 0.0},
        avg_entry=100.0,
        remaining_position_fraction=base_layer_fraction("L1"),
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts - timedelta(minutes=15),
        entry_index=0,
        entry_cvd_sign=1,
        avg_entry_for_r=100.0,
        risk_for_r=10.0,
    )
    replay = _replay_stub()

    result = replay._fill_l2(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=94.0, high=96.0, low=93.0, close=96.0, volume=10.0),
        indicators={
            "atr": 10.0,
            "poc": 120.0,
            "kijun": 100.0,
            "fibo_long_0618": 95.0,
        },
        fill_price=94.0,
    )

    assert result is active
    assert replay.events[-1]["price"] == 94.0
    assert machine.snapshot.fill_qtys["L2"] == pine_contract_qty(
        base_layer_fraction("L2"),
        95.0,
    )


def test_runner_break_uses_previous_close_not_kijun_value() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.RUNNER),
        side=TradeSide.LONG.value,
        remaining_position_fraction=0.25,
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts,
        entry_index=0,
        entry_cvd_sign=1,
        avg_entry_for_r=100.0,
        risk_for_r=10.0,
        remaining_fraction_for_r=0.25,
    )
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=99.0, high=101.0, low=98.0, close=100.0, volume=10.0),
        prev_candle=Candle(ts, open=101.0, high=102.0, low=99.0, close=99.0, volume=10.0),
        index=1,
        indicators={},
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is None
    assert replay.events[-1]["reason"] == "RUNNER_KIJUN_BREAK"
    assert replay.events[-1]["rr"] == -0.025


def test_state2_abort_records_exit_and_releases_position() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.LONG.value,
        avg_entry=100.0,
        hard_sl=90.0,
        remaining_position_fraction=1.0,
        first_fill_ts=ts.isoformat(),
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts,
        entry_index=0,
        entry_cvd_sign=1,
    )
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=100.0, high=101.0, low=99.0, close=99.5, volume=10.0),
        prev_candle=Candle(ts, open=101.0, high=102.0, low=100.0, close=100.0, volume=10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "reverse_spike_long": 1.0,
            "reverse_spike_short": 0.0,
            "htf_cross_long": 0.0,
            "htf_cross_short": 0.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is None
    assert replay.events[-1]["reason"] == "STATE_2_ABORT"
    assert replay.events[-1]["state2_trigger_source"] == "reverse_spike"
    assert replay.events[-1]["state2_reverse_spike"] is True
    assert replay.events[-1]["state2_htf_cross"] is False
    assert replay.events[-1]["state2_signal_mode"] == "any"
    assert "state2_reverse_spike_ratio" in replay.events[-1]
    assert replay.events[-1]["rr"] == -0.05
    assert machine.snapshot.state == int(StateCode.IDLE)


def test_pending_l2_fill_is_recorded_before_same_bar_state2_abort() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.SHORT.value,
        entry_prices={"L1": 99.0, "L2": 100.0, "L3": 103.0},
        fill_qtys={"L1": base_layer_fraction("L1"), "L2": 0.0, "L3": 0.0},
        avg_entry=99.0,
        remaining_position_fraction=1.0,
        first_fill_ts=(ts - timedelta(hours=2)).isoformat(),
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.SHORT,
        entry_ts=ts - timedelta(hours=2),
        entry_index=0,
        entry_cvd_sign=-1,
        avg_entry_for_r=99.0,
        risk_for_r=10.0,
    )
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=99.0, high=101.0, low=98.0, close=100.5, volume=10.0),
        prev_candle=Candle(ts - timedelta(minutes=15), 99.0, 100.0, 98.0, 99.0, 10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "poc": 100.0,
            "kijun": 100.0,
            "fibo_short_0618": 100.0,
            "reverse_spike_long": 0.0,
            "reverse_spike_short": 1.0,
            "htf_cross_long": 0.0,
            "htf_cross_short": 0.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is None
    assert [(event["event"], event["reason"]) for event in replay.events] == [
        ("ENTRY_L2", "L2_FILL"),
        ("EXIT", "STATE_2_ABORT"),
    ]
    assert replay.events[0]["price"] == 100.0
    assert replay.events[1]["price"] == 100.5


def test_active_l2_fill_closes_on_same_bar_hard_sl_at_close_price() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.SHORT.value,
        entry_prices={"L1": 100.0, "L2": 105.0, "L3": 110.0},
        fill_qtys={"L1": base_layer_fraction("L1"), "L2": 0.0, "L3": 0.0},
        avg_entry=100.0,
        remaining_position_fraction=base_layer_fraction("L1"),
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.SHORT,
        entry_ts=ts - timedelta(minutes=15),
        entry_index=0,
        entry_cvd_sign=-1,
        avg_entry_for_r=100.0,
        risk_for_r=10.0,
        remaining_fraction_for_r=base_layer_fraction("L1"),
    )
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=100.0, high=112.0, low=99.0, close=108.0, volume=10.0),
        prev_candle=Candle(ts - timedelta(minutes=15), 100.0, 101.0, 99.0, 100.0, 10.0),
        index=1,
        indicators={
            "atr": 1.0,
            "poc": 100.0,
            "kijun": 100.0,
            "fibo_short_0618": 105.0,
            "reverse_spike_short": 0.0,
            "htf_cross_short": 0.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is None
    assert [(event["event"], event["reason"], event["price"]) for event in replay.events] == [
        ("ENTRY_L2", "L2_FILL", 105.0),
        ("EXIT", "HARD_SL", 108.0),
    ]


def test_deferred_l2_recognition_closes_same_bar_hard_sl_at_close_price() -> None:
    fill_ts = datetime(2026, 4, 24, tzinfo=UTC)
    recognition_ts = fill_ts + timedelta(minutes=15)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.LONG.value,
        entry_prices={"L1": 100.0, "L2": 95.0, "L3": 90.0},
        fill_qtys={"L1": base_layer_fraction("L1"), "L2": 0.0, "L3": 0.0},
        avg_entry=100.0,
        remaining_position_fraction=base_layer_fraction("L1"),
        first_fill_ts=fill_ts.isoformat(),
    )
    machine = StateMachine(snapshot, now_fn=lambda: recognition_ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=fill_ts,
        entry_index=0,
        entry_cvd_sign=1,
        pending_l2_fill_price=95.0,
        pending_l2_fill_ts=fill_ts,
        avg_entry_for_r=100.0,
        risk_for_r=10.0,
    )
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(recognition_ts, open=96.0, high=97.0, low=90.0, close=93.0, volume=10.0),
        prev_candle=Candle(fill_ts, 100.0, 101.0, 94.0, 95.0, 10.0),
        index=1,
        indicators={
            "atr": 1.0,
            "poc": 100.0,
            "kijun": 100.0,
            "fibo_long_0618": 95.0,
            "reverse_spike_long": 0.0,
            "htf_cross_long": 0.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is None
    assert [(event["event"], event["reason"], event["price"]) for event in replay.events] == [
        ("EXIT", "HARD_SL", 93.0),
    ]


def test_l2_promo_fill_updates_average_without_entry_match_event() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    l1_qty = pine_contract_qty(base_layer_fraction("L1"), 100.0)
    l2_qty = pine_contract_qty(base_layer_fraction("L2"), 95.0)
    promo_fraction = 0.01
    initial_avg = ((100.0 * l1_qty) + (95.0 * l2_qty)) / (l1_qty + l2_qty)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.LONG.value,
        entry_prices={"L1": 100.0, "L2": 95.0, "L3": 90.0},
        fill_qtys={"L1": l1_qty, "L2": l2_qty, "L3": 0.0},
        avg_entry=initial_avg,
        hard_sl=80.0,
        remaining_position_fraction=base_layer_fraction("L1") + base_layer_fraction("L2"),
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts - timedelta(minutes=30),
        entry_index=0,
        entry_cvd_sign=1,
        avg_entry_for_r=initial_avg,
        risk_for_r=10.0,
        pending_l2_promo_fraction=promo_fraction,
        pending_l2_promo_price=95.0,
    )
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=96.0, high=97.0, low=94.0, close=97.0, volume=10.0),
        prev_candle=Candle(ts - timedelta(minutes=15), 100.0, 101.0, 99.0, 100.0, 10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "poc": 100.0,
            "kijun": 100.0,
            "fibo_long_0618": 95.0,
            "reverse_spike_long": 0.0,
            "htf_cross_long": 0.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    promo_qty = pine_contract_qty(promo_fraction, 95.0)
    assert result is active
    assert active.pending_l2_promo_fraction == 0.0
    assert machine.snapshot.hard_sl == 80.0
    assert machine.snapshot.fill_qtys["L2"] == l2_qty + promo_qty
    assert replay.events == [
        {
            "ts": "2026-04-24T00:00:00Z",
            "symbol": "BTC/USDT:USDT",
            "event": "ENTRY_L2_PROMO",
            "side": "long",
            "price": 95.0,
            "reason": "L2_PROMO_FILL",
            "cvd_sign": 1,
        }
    ]


def test_pending_l2_promo_blocks_l3_until_promo_fills() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.LONG.value,
        entry_prices={"L1": 100.0, "L2": 95.0, "L3": 90.0},
        fill_qtys={
            "L1": pine_contract_qty(base_layer_fraction("L1"), 100.0),
            "L2": pine_contract_qty(base_layer_fraction("L2"), 95.0),
            "L3": 0.0,
        },
        avg_entry=98.0,
        hard_sl=80.0,
        remaining_position_fraction=base_layer_fraction("L1") + base_layer_fraction("L2"),
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts - timedelta(minutes=30),
        entry_index=0,
        entry_cvd_sign=1,
        avg_entry_for_r=98.0,
        risk_for_r=10.0,
        pending_l2_promo_fraction=0.01,
        pending_l2_promo_price=85.0,
        pending_l3_fraction=base_layer_fraction("L3"),
    )
    replay = _replay_stub()

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=94.0, high=94.0, low=89.0, close=92.0, volume=10.0),
        prev_candle=Candle(ts - timedelta(minutes=15), 100.0, 101.0, 99.0, 100.0, 10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "poc": 100.0,
            "kijun": 100.0,
            "fibo_long_0618": 95.0,
            "reverse_spike_long": 0.0,
            "htf_cross_long": 0.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is active
    assert machine.snapshot.state == int(StateCode.FILLED_PARTIAL)
    assert machine.snapshot.fill_qtys["L3"] == 0.0
    assert replay.events == []


def test_state2_adverse_only_keeps_profitable_partial_position() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.LONG.value,
        avg_entry=100.0,
        hard_sl=90.0,
        remaining_position_fraction=1.0,
        first_fill_ts=ts.isoformat(),
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts,
        entry_index=0,
        entry_cvd_sign=1,
    )
    replay = _replay_stub()
    replay.state2_exit_mode = "adverse-only"

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=100.0, high=103.0, low=99.0, close=102.0, volume=10.0),
        prev_candle=Candle(ts, open=101.0, high=102.0, low=100.0, close=100.0, volume=10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "reverse_spike_long": 1.0,
            "reverse_spike_short": 0.0,
            "htf_cross_long": 0.0,
            "htf_cross_short": 0.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is active
    assert replay.events == []
    assert machine.snapshot.state == int(StateCode.FILLED_PARTIAL)


def test_state2_signal_mode_both_requires_reverse_and_htf_confirmation() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.LONG.value,
        avg_entry=100.0,
        hard_sl=90.0,
        remaining_position_fraction=1.0,
        first_fill_ts=ts.isoformat(),
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts,
        entry_index=0,
        entry_cvd_sign=1,
    )
    replay = _replay_stub()
    replay.state2_signal_mode = "both"

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=100.0, high=101.0, low=99.0, close=99.5, volume=10.0),
        prev_candle=Candle(ts, open=101.0, high=102.0, low=100.0, close=100.0, volume=10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "reverse_spike_long": 1.0,
            "reverse_spike_short": 0.0,
            "htf_cross_long": 0.0,
            "htf_cross_short": 0.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is active
    assert replay.events == []
    assert machine.snapshot.state == int(StateCode.FILLED_PARTIAL)


def test_state2_signal_mode_reverse_only_ignores_htf_only_cross() -> None:
    replay = _replay_stub()
    replay.state2_signal_mode = "reverse-only"

    assert replay._state2_signal_matches(reverse=False, htf_cross=True) is False
    assert replay._state2_signal_matches(reverse=True, htf_cross=False) is True


def test_state2_profit_hold_keeps_position_above_threshold() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.LONG.value,
        avg_entry=100.0,
        hard_sl=90.0,
        remaining_position_fraction=1.0,
        first_fill_ts=ts.isoformat(),
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts,
        entry_index=0,
        entry_cvd_sign=1,
    )
    replay = _replay_stub()
    replay.state2_profit_hold_r = 0.1

    result = replay._advance_active(
        symbol="BTC/USDT:USDT",
        active=active,
        candle=Candle(ts, open=100.0, high=103.0, low=99.0, close=102.0, volume=10.0),
        prev_candle=Candle(ts, open=101.0, high=102.0, low=100.0, close=100.0, volume=10.0),
        index=1,
        indicators={
            "atr": 10.0,
            "reverse_spike_long": 1.0,
            "reverse_spike_short": 0.0,
            "htf_cross_long": 0.0,
            "htf_cross_short": 0.0,
        },
        kijun_series=[100.0, 100.0, 100.0],
    )

    assert result is active
    assert replay.events == []


def test_state2_reverse_l2_hold_suppresses_recent_l2_reverse_only_signal() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.LONG.value,
        avg_entry=100.0,
        hard_sl=90.0,
        remaining_position_fraction=1.0,
        first_fill_ts=(ts - timedelta(hours=2)).isoformat(),
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts - timedelta(hours=2),
        entry_index=0,
        entry_cvd_sign=1,
        avg_entry_for_r=100.0,
        risk_for_r=10.0,
        peak_mfe=2.0,
        last_fill_event="ENTRY_L2",
        last_fill_ts=ts - timedelta(minutes=30),
    )
    replay = _replay_stub()
    replay.state2_reverse_min_minutes_since_l2 = 60.0

    reason = replay._state2_exit_reason(
        active=active,
        candle=Candle(ts, open=99.0, high=100.0, low=98.0, close=99.0, volume=10.0),
        indicators={
            "atr": 10.0,
            "reverse_spike_long": 1.0,
            "reverse_spike_short": 0.0,
            "htf_cross_long": 0.0,
            "htf_cross_short": 0.0,
        },
    )

    assert reason is None


def test_state2_reverse_l2_hold_keeps_htf_cross_signal() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_PARTIAL),
        side=TradeSide.LONG.value,
        avg_entry=100.0,
        hard_sl=90.0,
        remaining_position_fraction=1.0,
        first_fill_ts=(ts - timedelta(hours=2)).isoformat(),
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    active = ReplayPosition(
        machine=machine,
        side=TradeSide.LONG,
        entry_ts=ts - timedelta(hours=2),
        entry_index=0,
        entry_cvd_sign=1,
        avg_entry_for_r=100.0,
        risk_for_r=10.0,
        peak_mfe=2.0,
        last_fill_event="ENTRY_L2",
        last_fill_ts=ts - timedelta(minutes=30),
    )
    replay = _replay_stub()
    replay.state2_reverse_min_minutes_since_l2 = 60.0

    reason = replay._state2_exit_reason(
        active=active,
        candle=Candle(ts, open=99.0, high=100.0, low=98.0, close=99.0, volume=10.0),
        indicators={
            "atr": 10.0,
            "reverse_spike_long": 1.0,
            "reverse_spike_short": 0.0,
            "htf_cross_long": 1.0,
            "htf_cross_short": 0.0,
        },
    )

    assert reason == "STATE_2_ABORT"


def test_l3_distance_cap_keeps_layer_deep_but_reachable() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        side=TradeSide.LONG.value,
        entry_prices={"L1": 105.0, "L2": 100.0, "L3": 80.0},
    )
    machine = StateMachine(snapshot, now_fn=lambda: ts)
    replay = _replay_stub()
    replay.l3_max_distance_atr = 1.5

    replay._cap_l3_distance(machine, TradeSide.LONG, 10.0)

    assert machine.snapshot.entry_prices["L3"] == 85.0


def test_load_15m_cache_rejects_timestamp_gaps(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "BTC.csv").write_text(
        "\n".join(
            [
                "open,high,low,close,volume,timestamp",
                "1,2,1,2,10,2026-04-24T00:00:00Z",
                "2,3,2,3,10,2026-04-24T00:30:00Z",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="non-15m timestamp gaps"):
        load_15m_cache(tmp_path, "BTC")
