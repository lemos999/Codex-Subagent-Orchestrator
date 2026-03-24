"""Event-driven backtest adapter for the Trading Value system.

Replays historical OHLCV data through the full trading engine pipeline.
All core module calls are pure; the engine maintains mutable state internally.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from ..core.events import (
    BarClosedEvent,
    Event,
    EventType,
)
from ..core.indicators import build_timeframe_snapshot, compute_fib_extensions, detect_swings
from ..core.models import (
    EngineState,
    GlobalState,
    ModeState,
    RiskGate,
    Side,
    SymbolState,
    Timeframe,
    TimeframeSnapshot,
    TradeLifecycleState,
    TradingState,
)
from ..core.mode import ModeResult, evaluate_mode
from ..core.position import (
    compute_cooldown_end,
    compute_exit_plan,
    compute_position_size,
    evaluate_max_hold,
    evaluate_trailing_trend_long,
    evaluate_trailing_pullback_long,
    evaluate_trailing_rebound_short,
    is_cooldown_active,
    process_lifecycle_event,
)
from ..core.regime import RegimeSnapshot, classify_regime
from ..core.setup import (
    InvalidationInput,
    SetupContext,
    StopTarget,
    TriggerInput,
    check_zone_touch,
    compute_stop_target_pullback_long,
    compute_stop_target_rebound_short,
    compute_stop_target_trend_long,
    evaluate_setup_transition,
    select_watch_zones,
)


# ---------------------------------------------------------------------------
# 1. BacktestConfig
# ---------------------------------------------------------------------------

_BAR_CLOSED_MAP: dict[Timeframe, EventType] = {
    Timeframe.H4: EventType.BAR_CLOSED_4H,
    Timeframe.H1: EventType.BAR_CLOSED_1H,
    Timeframe.M30: EventType.BAR_CLOSED_30M,
    Timeframe.M15: EventType.BAR_CLOSED_15M,
    Timeframe.M5: EventType.BAR_CLOSED_5M,
}

_TF_ORDER: list[Timeframe] = [
    Timeframe.H4,
    Timeframe.H1,
    Timeframe.M30,
    Timeframe.M15,
    Timeframe.M5,
]

# Default profile windows from config/default.toml
_PROFILE_WINDOWS: dict[Timeframe, int | None] = {
    Timeframe.H4: 90,
    Timeframe.H1: 120,
    Timeframe.M30: 96,
    Timeframe.M15: None,
    Timeframe.M5: None,
}


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""

    symbols: list[str] = field(default_factory=lambda: ["ETHUSDT", "BTCUSDT"])
    initial_balance: float = 10000.0
    commission_rate: float = 0.0004  # 0.04% taker
    slippage_ticks: float = 0.5  # ticks of slippage
    # Risk parameters from config/default.toml
    risk_pct: float = 0.0035
    max_risk_pct: float = 0.005
    counter_trend_risk_pct: float = 0.0025
    min_rr: float = 1.5
    cooldown_normal_bars: int = 2
    cooldown_stop_bars: int = 4
    max_hold_bars: int = 48
    min_qty: float = 0.001
    primary_timeframe: Timeframe = Timeframe.M15
    # Zone width overrides (used by indicators.compute_zone_width)
    zone_width_pct: float = 0.0015
    zone_width_atr_factor: float = 0.25
    # v2: full trigger confirmation (spec v2 section 11)
    use_full_triggers: bool = False
    # Individual filter toggles (all default True when use_full_triggers=True)
    filter_zone_limit: bool = True
    filter_invalidation: bool = True
    filter_swing_5m: bool = True
    filter_split_entry: bool = True
    filter_daily_loss: bool = True
    filter_fib: bool = True
    filter_risk_budget: bool = True
    filter_volatility: bool = True
    filter_volume: bool = True
    filter_consec_loss: bool = True


# ---------------------------------------------------------------------------
# 2. Virtual order execution (section 16.1)
# ---------------------------------------------------------------------------


@dataclass
class VirtualOrder:
    """A simulated order awaiting fill."""

    order_id: str
    symbol: str
    side: Side
    price: float
    qty: float
    order_type: str  # "market", "limit", "stop"
    created_at: datetime
    ttl_bars: int = 2  # 2 x 5m bars


@dataclass
class FillResult:
    """Result of attempting to fill a virtual order against a bar."""

    filled: bool
    fill_price: float
    fill_qty: float
    commission: float
    slippage: float


def simulate_fill(
    order: VirtualOrder,
    bar_high: float,
    bar_low: float,
    bar_close: float,
    config: BacktestConfig,
) -> FillResult:
    """Simulate order fill against a bar's price range.

    - Market orders fill at close +/- slippage.
    - Limit buy fills if bar_low <= price (fill at limit price).
    - Limit sell fills if bar_high >= price (fill at limit price).
    - Stop sell fills if bar_low <= stop_price (fill at stop - slippage).
    - Stop buy fills if bar_high >= stop_price (fill at stop + slippage).
    - Commission = fill_price * qty * commission_rate.
    """
    slip = config.slippage_ticks
    no_fill = FillResult(filled=False, fill_price=0.0, fill_qty=0.0, commission=0.0, slippage=0.0)

    if order.order_type == "market":
        if order.side == Side.LONG:
            fp = bar_close + slip
        else:
            fp = bar_close - slip
        actual_slip = abs(fp - bar_close)
        comm = fp * order.qty * config.commission_rate
        return FillResult(filled=True, fill_price=fp, fill_qty=order.qty, commission=comm, slippage=actual_slip)

    if order.order_type == "limit":
        if order.side == Side.LONG:
            if bar_low <= order.price:
                fp = order.price
                comm = fp * order.qty * config.commission_rate
                return FillResult(filled=True, fill_price=fp, fill_qty=order.qty, commission=comm, slippage=0.0)
        else:  # SHORT limit sell
            if bar_high >= order.price:
                fp = order.price
                comm = fp * order.qty * config.commission_rate
                return FillResult(filled=True, fill_price=fp, fill_qty=order.qty, commission=comm, slippage=0.0)
        return no_fill

    if order.order_type == "stop":
        if order.side == Side.SHORT:
            # Stop sell: triggered when bar_low <= stop_price
            if bar_low <= order.price:
                fp = order.price - slip
                actual_slip = slip
                comm = fp * order.qty * config.commission_rate
                return FillResult(filled=True, fill_price=fp, fill_qty=order.qty, commission=comm, slippage=actual_slip)
        else:  # LONG stop buy
            if bar_high >= order.price:
                fp = order.price + slip
                actual_slip = slip
                comm = fp * order.qty * config.commission_rate
                return FillResult(filled=True, fill_price=fp, fill_qty=order.qty, commission=comm, slippage=actual_slip)
        return no_fill

    return no_fill


# ---------------------------------------------------------------------------
# 3. Trade journal (section 15)
# ---------------------------------------------------------------------------


@dataclass
class TradeRecord:
    """Complete record of a single trade from entry to exit."""

    symbol: str
    strategy: str
    side: str
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    pnl_r: float  # PnL in R units
    commission_total: float
    entry_time: datetime
    exit_time: datetime
    duration_bars: int
    exit_reason: str  # "tp1", "tp2", "trailing", "stop", "max_hold", "invalidation"
    regime_at_entry: str
    mode_at_entry: str
    rr_planned: float
    rr_actual: float


@dataclass
class DecisionLog:
    """Logs a single decision point in the backtest."""

    timestamp: datetime
    symbol: str
    event_type: str
    regime_state: str
    mode_state: str
    setup_state: str
    lifecycle_state: str
    reason: str  # why entered, skipped, or exited
    details: dict | None = None


# ---------------------------------------------------------------------------
# 4. BacktestResult — aggregated metrics
# ---------------------------------------------------------------------------


@dataclass
class BacktestResult:
    """Aggregated backtest results and metrics."""

    trades: list[TradeRecord]
    decision_logs: list[DecisionLog]
    final_balance: float
    total_pnl: float
    total_commission: float
    win_rate: float  # % of profitable trades
    avg_rr: float  # average R:R achieved
    max_drawdown: float  # peak-to-trough in account balance
    max_consecutive_losses: int
    sharpe_ratio: float | None  # if enough trades
    total_trades: int
    long_trades: int
    short_trades: int
    avg_hold_bars: float

    def summary(self) -> str:
        """Human-readable summary of backtest results."""
        lines = [
            "=== Backtest Summary ===",
            f"Total Trades:    {self.total_trades}",
            f"  Long:          {self.long_trades}",
            f"  Short:         {self.short_trades}",
            f"Win Rate:        {self.win_rate:.1f}%",
            f"Avg R:R:         {self.avg_rr:.2f}",
            f"Total PnL:       {self.total_pnl:.2f}",
            f"Total Commission:{self.total_commission:.2f}",
            f"Final Balance:   {self.final_balance:.2f}",
            f"Max Drawdown:    {self.max_drawdown:.2f}",
            f"Max Consec Loss: {self.max_consecutive_losses}",
            f"Avg Hold (bars): {self.avg_hold_bars:.1f}",
        ]
        if self.sharpe_ratio is not None:
            lines.append(f"Sharpe Ratio:    {self.sharpe_ratio:.2f}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 5. Helper: build snapshots from historical data
# ---------------------------------------------------------------------------


def _build_snapshots_indexed(
    indexed_data: dict[Timeframe, pd.DataFrame],
    timestamp: datetime,
    profile_windows: dict[Timeframe, int | None] | None = None,
) -> dict[Timeframe, TimeframeSnapshot]:
    """Build TimeframeSnapshot from pre-indexed (timestamp-indexed) DataFrames.

    Uses .loc[:ts] slicing for O(log n) access instead of full-scan mask.
    """
    if profile_windows is None:
        profile_windows = _PROFILE_WINDOWS

    snapshots: dict[Timeframe, TimeframeSnapshot] = {}
    for tf, idf in indexed_data.items():
        if idf.empty:
            continue
        available = idf.loc[:timestamp]
        if len(available) < 52:
            continue
        pw = profile_windows.get(tf)
        try:
            snap = build_timeframe_snapshot(
                available.reset_index().rename(columns={"index": "timestamp"}) if available.index.name else available,
                tf,
                profile_window=pw,
            )
            snapshots[tf] = snap
        except Exception:
            continue
    return snapshots


def build_snapshots_at(
    data: dict[Timeframe, pd.DataFrame],
    timestamp: datetime,
    profile_windows: dict[Timeframe, int | None] | None = None,
) -> dict[Timeframe, TimeframeSnapshot]:
    """Build TimeframeSnapshot for each timeframe at a given timestamp.

    Uses the most recent completed bar at or before timestamp for each TF.
    Returns only timeframes that have sufficient data.
    """
    if profile_windows is None:
        profile_windows = _PROFILE_WINDOWS

    snapshots: dict[Timeframe, TimeframeSnapshot] = {}
    for tf, df in data.items():
        if df.empty:
            continue
        # Select rows at or before the timestamp
        mask = df["timestamp"] <= timestamp
        available = df.loc[mask]
        if available.empty:
            continue
        # Need enough bars for indicators (at least 52 for Ichimoku)
        if len(available) < 52:
            continue
        pw = profile_windows.get(tf)
        try:
            snap = build_timeframe_snapshot(
                available, tf, profile_window=pw,
            )
            snapshots[tf] = snap
        except (ValueError, KeyError):
            # Insufficient data for this timeframe — skip
            continue
    return snapshots


# ---------------------------------------------------------------------------
# 6. BacktestEngine — the main event loop
# ---------------------------------------------------------------------------


class BacktestEngine:
    """Event-driven backtester. Replays OHLCV bars through the full pipeline.

    State evaluation priority per section 10:
    1. EngineState check (always READY in backtest)
    2. RiskGate update
    3. Bar close events -> RegimeState + ModeState refresh (4H->1H->30M->15M->5M order)
    4. Setup invalidation check
    5. Position management (exits first)
    6. New setup tracking and entry
    7. Decision log
    """

    def __init__(self, config: BacktestConfig) -> None:
        self.config = config
        self.state: TradingState = TradingState()
        self.setup_contexts: dict[str, SetupContext] = {}
        self.pending_orders: list[VirtualOrder] = []
        self.trade_records: list[TradeRecord] = []
        self.decision_logs: list[DecisionLog] = []
        self.balance: float = config.initial_balance
        self.peak_balance: float = config.initial_balance
        self.max_drawdown: float = 0.0
        self.total_commission: float = 0.0
        # Internal tracking for open trades
        self._open_trade_info: dict[str, dict] = {}
        # Regime/mode cache per symbol
        self._regime_cache: dict[str, RegimeSnapshot] = {}
        self._mode_cache: dict[str, ModeResult] = {}
        # Setup version counter
        self._setup_version_counter: int = 0
        # Swing cache per symbol: {symbol: (swing_highs, swing_lows)}
        self._swing_cache: dict[str, tuple[list[tuple[int, float]], list[tuple[int, float]]]] = {}
        # 5m swing cache per symbol (Item 3)
        self._swing_cache_5m: dict[str, tuple[list[tuple[int, float]], list[tuple[int, float]]]] = {}
        # Consecutive losses per symbol (for entry filter)
        self._consecutive_losses: dict[str, int] = {}
        # Daily PnL tracking (Item 5)
        self._daily_pnl: dict[str, float] = {}
        self._daily_r_unit: float = 0.0

    def run(
        self,
        data: dict[str, dict[Timeframe, pd.DataFrame]],
    ) -> BacktestResult:
        """Run backtest on historical data.

        Args:
            data: {symbol: {timeframe: DataFrame}} -- each DataFrame has
                  columns [timestamp, open, high, low, close, volume].
                  The 5m timeframe is the primary tick.

        Returns:
            BacktestResult with trade records, metrics, and logs.
        """
        # Initialize state
        self.state = TradingState(
            global_state=GlobalState(
                engine=EngineState.READY,
                risk_gate=RiskGate.ALLOW,
            ),
            symbols={
                sym: SymbolState(symbol=sym)
                for sym in self.config.symbols
            },
        )
        self.balance = self.config.initial_balance
        self.peak_balance = self.config.initial_balance
        self.max_drawdown = 0.0
        self.total_commission = 0.0
        self.trade_records = []
        self.decision_logs = []
        self.pending_orders = []
        self.setup_contexts = {}
        self._open_trade_info = {}
        self._regime_cache = {}
        self._mode_cache = {}
        self._setup_version_counter = 0
        # Item 5: Daily loss limit
        self._daily_pnl = {}
        self._daily_r_unit = self.config.initial_balance * self.config.risk_pct

        # ── Phase A: Batch pre-compute ALL snapshots (O(N) per TF) ─────
        import sys
        from ..core.indicators import build_all_snapshots
        snapshot_cache: dict[str, dict[Timeframe, dict[datetime, TimeframeSnapshot]]] = {}
        for sym in self.config.symbols:
            sym_data = data.get(sym)
            if sym_data is None:
                continue
            snapshot_cache[sym] = {}
            for tf, df in sym_data.items():
                if df.empty:
                    continue
                # Ensure DataFrame has columns (not index)
                if "timestamp" not in df.columns:
                    if df.index.name == "timestamp":
                        df = df.reset_index()
                    else:
                        continue
                pw = _PROFILE_WINDOWS.get(tf)
                import time as _time
                t0 = _time.time()
                tf_cache = build_all_snapshots(df, tf, profile_window=pw)
                elapsed = _time.time() - t0
                snapshot_cache[sym][tf] = tf_cache
                print(f"  Pre-computed {sym}/{tf.value}: {len(tf_cache)} snapshots in {elapsed:.1f}s", file=sys.stderr, flush=True)

        # Build sorted timestamp keys for bisect lookup in Phase C
        _sorted_keys_cache: dict[str, dict[Timeframe, list[datetime]]] = {}
        for sym, sym_c in snapshot_cache.items():
            _sorted_keys_cache[sym] = {}
            for tf, tf_c in sym_c.items():
                _sorted_keys_cache[sym][tf] = sorted(tf_c.keys())

        # ── Phase B: Index primary bars for O(1) lookup ────────────────
        # Primary tick = 15m (configurable via self.config)
        primary_tf = getattr(self.config, 'primary_timeframe', Timeframe.M15)
        indexed_primary: dict[str, pd.DataFrame] = {}
        for sym in self.config.symbols:
            sym_data = data.get(sym)
            if sym_data is None:
                continue
            df_primary = sym_data.get(primary_tf)
            if df_primary is None or df_primary.empty:
                continue
            if "timestamp" in df_primary.columns:
                indexed_primary[sym] = df_primary.set_index("timestamp").sort_index()
            else:
                indexed_primary[sym] = df_primary.sort_index()

        # ── Phase C: Main event loop — cache lookup only ───────────────
        all_timestamps: set[datetime] = set()
        for sym, idf in indexed_primary.items():
            all_timestamps.update(idf.index.tolist())

        sorted_timestamps = sorted(all_timestamps)

        for ts in sorted_timestamps:
            for sym in self.config.symbols:
                if sym not in indexed_primary:
                    continue
                df_primary = indexed_primary[sym]
                if ts not in df_primary.index:
                    continue
                bar = df_primary.loc[ts]
                bar_dict = {
                    "open": float(bar["open"]),
                    "high": float(bar["high"]),
                    "low": float(bar["low"]),
                    "close": float(bar["close"]),
                    "volume": float(bar["volume"]),
                }

                # Lookup pre-computed snapshots (latest at or before ts)
                snapshots: dict[Timeframe, TimeframeSnapshot] = {}
                sym_cache = snapshot_cache.get(sym, {})
                for tf, tf_sorted in _sorted_keys_cache.get(sym, {}).items():
                    tf_cache = sym_cache.get(tf, {})
                    if not tf_sorted:
                        continue
                    import bisect
                    idx = bisect.bisect_right(tf_sorted, ts) - 1
                    if idx >= 0:
                        snapshots[tf] = tf_cache[tf_sorted[idx]]

                if not snapshots:
                    continue

                self._process_bar(sym, ts, bar_dict, snapshots, data.get(sym, {}))

        return self._build_result()

    def _process_bar(
        self,
        symbol: str,
        timestamp: datetime,
        bar_primary: dict,
        snapshots: dict[Timeframe, TimeframeSnapshot],
        sym_data: dict[Timeframe, pd.DataFrame] | None = None,
    ) -> None:
        """Process a single 5m bar for one symbol.

        1. Detect which higher timeframes also closed at this timestamp
        2. Generate BarClosedEvent for each
        3. Update regime/mode on 30m+ closes
        4. Check invalidation
        5. Process pending orders (fills)
        6. Evaluate position (trailing, max hold)
        7. Evaluate setup (zone touch, trigger)
        8. Log decisions
        """
        sym_state = self.state.symbols[symbol]
        closed_tfs = self._detect_bar_closes(timestamp)

        # --- Step 1-3: Process bar closes in priority order (4H->1H->30M->15M->5M) ---
        regime_updated = False
        mode_result: ModeResult | None = self._mode_cache.get(symbol)

        for tf in _TF_ORDER:
            if tf not in closed_tfs:
                continue
            if tf not in snapshots:
                continue

            # Generate bar close event (used for lifecycle processing)
            snap = snapshots[tf]
            # Use actual OHLCV from the historical DataFrame when available
            bar_open = snap.close
            bar_hi = snap.close
            bar_lo = snap.close
            bar_cl = snap.close
            bar_vol = snap.volume
            if tf in (Timeframe.M15, Timeframe.M30):
                bar_open = bar_primary["open"]
                bar_hi = bar_primary["high"]
                bar_lo = bar_primary["low"]
                bar_cl = bar_primary["close"]
                bar_vol = bar_primary["volume"]
            elif sym_data is not None and tf in sym_data:
                tf_df = sym_data[tf]
                tf_rows = tf_df.loc[tf_df["timestamp"] == timestamp]
                if not tf_rows.empty:
                    tf_bar = tf_rows.iloc[0]
                    bar_open = float(tf_bar["open"])
                    bar_hi = float(tf_bar["high"])
                    bar_lo = float(tf_bar["low"])
                    bar_cl = float(tf_bar["close"])
                    bar_vol = float(tf_bar["volume"])
            bar_event = BarClosedEvent(
                event_type=_BAR_CLOSED_MAP[tf],
                timestamp=timestamp,
                symbol=symbol,
                timeframe=tf,
                open=bar_open,
                high=bar_hi,
                low=bar_lo,
                close=bar_cl,
                volume=bar_vol,
            )

            # Process lifecycle event (cooldown transitions, etc.)
            lc_transition = process_lifecycle_event(
                sym_state, self.state.global_state, bar_event,
            )
            if lc_transition is not None:
                sym_state = self._apply_lifecycle_transition(
                    symbol, lc_transition,
                )

            # Update regime/mode on 30m+ closes
            if tf in (Timeframe.H4, Timeframe.H1, Timeframe.M30):
                required_tfs = {Timeframe.H4, Timeframe.H1, Timeframe.M30}
                if required_tfs.issubset(snapshots.keys()):
                    regime = classify_regime(snapshots)
                    self._regime_cache[symbol] = regime
                    mode_result = evaluate_mode(regime)
                    self._mode_cache[symbol] = mode_result
                    regime_updated = True

                    # Update symbol state with new regime/mode
                    sym_state = self.state.symbols[symbol]
                    sym_state.regime = regime.htf
                    sym_state.mode = mode_result.mode

            # Update swing cache on M30 bar close
            if tf == Timeframe.M30 and sym_data is not None:
                m30_df = sym_data.get(Timeframe.M30)
                if m30_df is not None and "timestamp" in m30_df.columns:
                    mask = m30_df["timestamp"] <= timestamp
                    df_up_to_now = m30_df.loc[mask]
                    if len(df_up_to_now) >= 5:
                        self._swing_cache[symbol] = detect_swings(df_up_to_now)

            # Item 3: Update 5m swing cache
            if self.config.use_full_triggers and sym_data is not None:
                should_update_5m = False
                if self.config.primary_timeframe == Timeframe.M5 and tf == Timeframe.M5:
                    should_update_5m = True
                elif tf == Timeframe.M15:
                    should_update_5m = True
                if should_update_5m:
                    m5_df = sym_data.get(Timeframe.M5)
                    if m5_df is not None and "timestamp" in m5_df.columns:
                        mask5 = m5_df["timestamp"] <= timestamp
                        df5_up = m5_df.loc[mask5]
                        if len(df5_up) >= 5:
                            self._swing_cache_5m[symbol] = detect_swings(df5_up)

        # Use 5m bar data for order fills
        bar_high = bar_primary["high"]
        bar_low = bar_primary["low"]
        bar_close = bar_primary["close"]

        # --- Step 4: Check setup invalidation ---
        if symbol in self.setup_contexts:
            ctx = self.setup_contexts[symbol]
            effective_mode = mode_result or self._mode_cache.get(symbol)
            if effective_mode is not None:
                # Item 2: Build InvalidationInput when use_full_triggers
                inv_input = None
                if self.config.use_full_triggers and self.config.filter_invalidation:
                    snap_m30 = snapshots.get(Timeframe.M30)
                    snap_m15 = snapshots.get(Timeframe.M15)
                    snap_m5 = snapshots.get(Timeframe.M5)
                    snap_h1 = snapshots.get(Timeframe.H1)
                    inv_input = InvalidationInput(
                        close_15m=bar_primary["close"],
                        close_1h=snap_h1.close if snap_h1 else bar_primary["close"],
                        zone=ctx.active_zone,
                        upper_support_low=ctx.active_zone.low if ctx.active_zone else None,
                        m30_below_cloud=(str(snap_m30.cloud_position) == "below") if snap_m30 else False,
                        m15_below_cloud_tk_bear=(
                            str(snap_m15.cloud_position) == "below"
                            and str(snap_m15.tk_state) == "bearish"
                        ) if snap_m15 else False,
                        m5_below_cloud_tk_bear=(
                            str(snap_m5.cloud_position) == "below"
                            and str(snap_m5.tk_state) == "bearish"
                        ) if snap_m5 else False,
                        m30_above_cloud_tk_bull=(
                            str(snap_m30.cloud_position) == "above"
                            and str(snap_m30.tk_state) == "bullish"
                        ) if snap_m30 else False,
                        h1_above_poc_or_vah_2bars=False,  # simplified
                    )
                new_ctx = evaluate_setup_transition(
                    ctx=ctx,
                    current_price=bar_close,
                    trigger_input=None,
                    snapshots=snapshots,
                    mode_result=effective_mode,
                    invalidation_input=inv_input,
                )
                self.setup_contexts[symbol] = new_ctx
                if str(new_ctx.state) == "INVALIDATED":
                    self._log_decision(
                        timestamp, symbol, "SETUP_INVALIDATED",
                        sym_state, effective_mode,
                        f"invalidated: {new_ctx.invalidation_reason}",
                    )
                    del self.setup_contexts[symbol]

        # --- Step 5: Process pending orders (exits first, then entries) ---
        # Exit orders: stops, TP limits (tp1_/tp2_ prefix), and market exits (exit_ prefix).
        # Entry orders: everything else (entry_ prefix market/limit orders).
        def _is_exit_order(o: VirtualOrder) -> bool:
            if o.order_type == "stop":
                return True
            oid = o.order_id
            if oid.startswith("tp1_") or oid.startswith("tp2_") or oid.startswith("exit_"):
                return True
            return False

        exit_orders = [
            o for o in self.pending_orders
            if o.symbol == symbol and _is_exit_order(o)
        ]
        entry_orders = [
            o for o in self.pending_orders
            if o.symbol == symbol and not _is_exit_order(o)
        ]

        for order in exit_orders:
            fill = simulate_fill(order, bar_high, bar_low, bar_close, self.config)
            if fill.filled:
                # Determine exit reason from order_id prefix
                if order.order_id.startswith("stop_"):
                    reason = "stop"
                elif order.order_id.startswith("tp1_"):
                    reason = "tp1"
                elif order.order_id.startswith("tp2_"):
                    reason = "tp2"
                elif order.order_id.startswith("exit_"):
                    reason = "max_hold"
                else:
                    reason = "stop"
                self._handle_exit_fill(symbol, order, fill, timestamp, reason)
                self.pending_orders = [o for o in self.pending_orders if o.order_id != order.order_id]
            else:
                order.ttl_bars -= 1
                if order.ttl_bars <= 0:
                    self.pending_orders = [o for o in self.pending_orders if o.order_id != order.order_id]

        for order in entry_orders:
            fill = simulate_fill(order, bar_high, bar_low, bar_close, self.config)
            if fill.filled:
                self._handle_entry_fill(symbol, order, fill, timestamp)
                self.pending_orders = [o for o in self.pending_orders if o.order_id != order.order_id]
            else:
                order.ttl_bars -= 1
                if order.ttl_bars <= 0:
                    self.pending_orders = [o for o in self.pending_orders if o.order_id != order.order_id]
                    self._log_decision(
                        timestamp, symbol, "ORDER_EXPIRED",
                        sym_state, mode_result, "entry order TTL expired",
                    )

        # --- Step 5b: Detect orphaned positions (no orders left) ---
        sym_state = self.state.symbols[symbol]
        if sym_state.lifecycle in (
            TradeLifecycleState.OPEN_STAGE0,
            TradeLifecycleState.OPEN_STAGE1,
            TradeLifecycleState.OPEN_STAGE2,
        ):
            sym_orders = [o for o in self.pending_orders if o.symbol == symbol]
            if not sym_orders and symbol in self._open_trade_info:
                # All orders gone (filled/expired) but position still open — force exit
                self._place_market_exit(symbol, timestamp, "orphaned_no_orders")

        # --- Step 6: Evaluate position (trailing, max hold) ---
        sym_state = self.state.symbols[symbol]
        if sym_state.lifecycle in (
            TradeLifecycleState.OPEN_STAGE0,
            TradeLifecycleState.OPEN_STAGE1,
            TradeLifecycleState.OPEN_STAGE2,
        ):
            self._evaluate_position_management(
                symbol, timestamp, bar_close, snapshots,
            )

        # --- Step 7: Evaluate setup (create new or continue existing) ---
        sym_state = self.state.symbols[symbol]
        if sym_state.lifecycle == TradeLifecycleState.FLAT and not is_cooldown_active(sym_state.cooldown_until, timestamp):
            # Use cached mode_result if not refreshed this bar
            effective_mode = mode_result or self._mode_cache.get(symbol)
            if effective_mode is not None and effective_mode.mode != ModeState.MODE_NO_TRADE:
                self._evaluate_new_setup(
                    symbol, timestamp, bar_close, bar_primary, snapshots, effective_mode, sym_data,
                )
            elif symbol in self.setup_contexts:
                # Mode changed to NO_TRADE — invalidate existing setup
                del self.setup_contexts[symbol]

        # --- Step 8: Log decision ---
        sym_state = self.state.symbols[symbol]
        self._log_decision(
            timestamp, symbol, "BAR_PROCESSED",
            sym_state, mode_result,
            f"close={bar_close:.2f} lc={sym_state.lifecycle}",
        )

    def _detect_bar_closes(self, timestamp: datetime) -> list[Timeframe]:
        """Determine which timeframes have a bar close at this timestamp.

        Primary tick depends on config.primary_timeframe (Item 6).
        M5 primary: M5 always, M15 when minute % 15 == 0
        M15 primary (default): M15 always
        30m: when minute in (0, 30)
        1h: when minute == 0
        4h: when hour % 4 == 0 and minute == 0
        """
        minute = timestamp.minute
        hour = timestamp.hour

        # Item 6: Primary tick M5 switch
        if self.config.primary_timeframe == Timeframe.M5:
            closes: list[Timeframe] = [Timeframe.M5]
            if minute % 15 == 0:
                closes.append(Timeframe.M15)
        else:
            closes = [Timeframe.M15]

        if minute in (0, 30):
            closes.append(Timeframe.M30)
        if minute == 0:
            closes.append(Timeframe.H1)
        if hour % 4 == 0 and minute == 0:
            closes.append(Timeframe.H4)

        return closes

    # --- Internal helpers ---

    def _next_setup_version(self) -> int:
        self._setup_version_counter += 1
        return self._setup_version_counter

    def _build_trigger_input(
        self,
        bar_primary: dict,
        snapshots: dict[Timeframe, TimeframeSnapshot],
        sym_data: dict[Timeframe, pd.DataFrame] | None,
        timestamp: datetime,
    ) -> TriggerInput | None:
        """Build TriggerInput from real 5m + 15m bar data."""
        # Defaults from primary bar
        close_5m = bar_primary["close"]
        high_5m = bar_primary["high"]
        low_5m = bar_primary["low"]
        open_5m = bar_primary["open"]
        volume_5m = bar_primary["volume"]
        prev_5m_high = high_5m
        prev_5m_low = low_5m
        prev_5m_highs_3 = [high_5m]
        avg_volume_5m_5 = volume_5m

        close_15m = bar_primary["close"]
        high_15m = bar_primary["high"]
        low_15m = bar_primary["low"]
        open_15m = bar_primary["open"]
        volume_15m = bar_primary["volume"]
        prev_volume_15m = volume_15m

        if sym_data is not None:
            # Use real 5m data if available
            m5_df = sym_data.get(Timeframe.M5)
            if m5_df is not None and "timestamp" in m5_df.columns:
                mask = m5_df["timestamp"] <= timestamp
                recent_5m = m5_df.loc[mask].tail(8)
                if len(recent_5m) >= 1:
                    last_5m = recent_5m.iloc[-1]
                    close_5m = float(last_5m["close"])
                    high_5m = float(last_5m["high"])
                    low_5m = float(last_5m["low"])
                    open_5m = float(last_5m["open"])
                    volume_5m = float(last_5m["volume"])
                if len(recent_5m) >= 2:
                    prev_bar = recent_5m.iloc[-2]
                    prev_5m_high = float(prev_bar["high"])
                    prev_5m_low = float(prev_bar["low"])
                if len(recent_5m) >= 4:
                    prev_5m_highs_3 = [float(recent_5m.iloc[-i]["high"]) for i in range(2, min(5, len(recent_5m)))]
                if len(recent_5m) >= 6:
                    avg_volume_5m_5 = float(recent_5m.iloc[-6:-1]["volume"].mean())

            # Use real 15m data if available
            m15_df = sym_data.get(Timeframe.M15)
            if m15_df is not None and "timestamp" in m15_df.columns:
                mask = m15_df["timestamp"] <= timestamp
                recent_15m = m15_df.loc[mask].tail(3)
                if len(recent_15m) >= 1:
                    last_15m = recent_15m.iloc[-1]
                    close_15m = float(last_15m["close"])
                    high_15m = float(last_15m["high"])
                    low_15m = float(last_15m["low"])
                    open_15m = float(last_15m["open"])
                    volume_15m = float(last_15m["volume"])
                if len(recent_15m) >= 2:
                    prev_volume_15m = float(recent_15m.iloc[-2]["volume"])

        # 30m close
        close_30m = close_15m
        snap_30m = snapshots.get(Timeframe.M30)
        if snap_30m is not None:
            close_30m = snap_30m.close

        return TriggerInput(
            close_5m=close_5m,
            high_5m=high_5m,
            low_5m=low_5m,
            open_5m=open_5m,
            volume_5m=volume_5m,
            prev_5m_high=prev_5m_high,
            prev_5m_low=prev_5m_low,
            prev_5m_highs_3=prev_5m_highs_3,
            avg_volume_5m_5=avg_volume_5m_5,
            close_15m=close_15m,
            high_15m=high_15m,
            low_15m=low_15m,
            open_15m=open_15m,
            volume_15m=volume_15m,
            prev_volume_15m=prev_volume_15m,
            close_30m=close_30m,
        )

    def _compute_stop_target_full(
        self,
        strategy: str,
        entry_price: float,
        zone,
        snapshots: dict[Timeframe, TimeframeSnapshot],
        bar_primary: dict,
    ) -> StopTarget | None:
        """Compute spec-compliant stop and target prices per strategy."""
        snap_30m = snapshots.get(Timeframe.M30)
        snap_1h = snapshots.get(Timeframe.H1)
        snap_4h = snapshots.get(Timeframe.H4)
        atr_15m = snapshots[Timeframe.M15].atr if Timeframe.M15 in snapshots else (
            snap_30m.atr if snap_30m else entry_price * 0.001)
        atr_5m = atr_15m * 0.6  # proxy: 5m ATR ~ 60% of 15m ATR

        # Get swing data from cache (Phase 3A + Item 3: prefer 5m swings)
        sym_key = next(iter(self.state.symbols))
        # Item 3: Use 5m swing cache when available under use_full_triggers
        if self.config.use_full_triggers and sym_key in self._swing_cache_5m:
            swing_highs_5m, swing_lows_5m = self._swing_cache_5m[sym_key]
        else:
            swing_highs_5m, swing_lows_5m = [], []
        swing_highs, swing_lows = self._swing_cache.get(sym_key, ([], []))
        # Prefer 5m swings, fallback to M30
        eff_swing_lows = swing_lows_5m if swing_lows_5m else swing_lows
        eff_swing_highs = swing_highs_5m if swing_highs_5m else swing_highs
        recent_swing_low = eff_swing_lows[-1][1] if eff_swing_lows else entry_price - atr_15m * 1.5
        recent_swing_high_val = eff_swing_highs[-1][1] if eff_swing_highs else entry_price + atr_15m * 3.0

        if strategy == "TREND_LONG":
            swing_low_5m = recent_swing_low
            if snap_30m and snap_30m.val > 0 and snap_30m.val < entry_price:
                swing_low_5m = min(swing_low_5m, snap_30m.val)
            recent_swing_high = max(recent_swing_high_val, entry_price + atr_15m * 2.0)
            if snap_30m and snap_30m.vah > entry_price:
                recent_swing_high = max(recent_swing_high, snap_30m.vah)
            # Item 7: Fib extensions
            fib_ext = compute_fib_extensions(swing_low_5m, recent_swing_high)
            vah_30m = snap_30m.vah if (snap_30m and snap_30m.vah > entry_price) else entry_price + atr_15m * 3.0
            vah_1h = snap_1h.vah if (snap_1h and snap_1h.vah > entry_price) else entry_price + atr_15m * 5.0
            st = compute_stop_target_trend_long(
                entry_price=entry_price, zone=zone,
                swing_low_5m=swing_low_5m, atr_5m=atr_5m, atr_15m=atr_15m,
                recent_swing_high=recent_swing_high, vah_30m=vah_30m, vah_1h=vah_1h,
                fib_extensions=fib_ext,
            )
        elif strategy == "PULLBACK_LONG":
            if not snap_30m or not snap_1h:
                return None
            st = compute_stop_target_pullback_long(
                entry_price=entry_price, zone=zone, atr_15m=atr_15m,
                tenkan_30m=max(snap_30m.tenkan, entry_price + atr_15m),
                kijun_30m=max(snap_30m.kijun, entry_price + atr_15m * 1.5),
                tenkan_1h=max(snap_1h.tenkan, entry_price + atr_15m * 2.0),
                kijun_1h=max(snap_1h.kijun, entry_price + atr_15m * 3.0),
                poc_1h=max(snap_1h.poc, entry_price + atr_15m * 2.5),
            )
        elif strategy == "REBOUND_SHORT":
            if not snap_30m:
                return None
            # Item 3: Use 5m swing low for REBOUND_SHORT
            recent_low = recent_swing_low if recent_swing_low < entry_price else entry_price - atr_15m * 3.0
            if snap_30m.val > 0 and snap_30m.val < entry_price:
                recent_low = min(recent_low, snap_30m.val)
            poc_30m = snap_30m.poc if (snap_30m.poc > 0 and snap_30m.poc < entry_price) else entry_price - atr_15m * 2.0
            val_30m = snap_30m.val if (snap_30m.val > 0 and snap_30m.val < entry_price) else entry_price - atr_15m * 3.0
            val_1h = (snap_1h.val if snap_1h and snap_1h.val > 0 and snap_1h.val < entry_price else entry_price - atr_15m * 4.0)
            kijun_4h = (snap_4h.kijun if snap_4h and snap_4h.kijun < entry_price else entry_price - atr_15m * 5.0)
            st = compute_stop_target_rebound_short(
                entry_price=entry_price, zone=zone, atr_15m=atr_15m,
                recent_low=recent_low, poc_30m=poc_30m, val_30m=val_30m,
                val_1h=val_1h, kijun_4h=kijun_4h,
            )
        else:
            return None

        # Fallback: if TP1 is None, use ATR-based target
        if st.tp1_price is None:
            risk = abs(entry_price - st.stop_price)
            if risk > 0:
                if "LONG" in strategy:
                    fallback_tp1 = entry_price + risk * self.config.min_rr
                    fallback_tp2 = entry_price + risk * self.config.min_rr * 2.0
                else:
                    fallback_tp1 = entry_price - risk * self.config.min_rr
                    fallback_tp2 = entry_price - risk * self.config.min_rr * 2.0
                from trading_value.core.setup import _compute_rr
                rr = _compute_rr(entry_price, st.stop_price, fallback_tp1)
                st = StopTarget(
                    stop_price=st.stop_price,
                    tp1_price=fallback_tp1, tp2_price=fallback_tp2, tp3_price=None,
                    rr_to_tp1=rr,
                )
        return st

    def _apply_lifecycle_transition(self, symbol: str, transition) -> SymbolState:
        """Apply a LifecycleTransition to the symbol state."""
        sym_state = self.state.symbols[symbol]
        sym_state.lifecycle = transition.new_state
        sym_state.last_transition_reason = transition.reason
        for key, value in transition.updates.items():
            if key.startswith("_"):
                continue  # skip private keys
            if hasattr(sym_state, key):
                setattr(sym_state, key, value)
        return sym_state

    def _evaluate_new_setup(
        self,
        symbol: str,
        timestamp: datetime,
        bar_close: float,
        bar_primary: dict,
        snapshots: dict[Timeframe, TimeframeSnapshot],
        mode_result: ModeResult,
        sym_data: dict[Timeframe, pd.DataFrame] | None = None,
    ) -> None:
        """Evaluate whether to start tracking a new setup and potentially enter."""
        if not mode_result.allowed_setups:
            return

        strategy = mode_result.allowed_setups[0]
        side = Side.LONG if "LONG" in strategy else Side.SHORT

        # Create or update setup context
        # Always refresh zones every bar (zones are based on current indicator values)
        # This ensures zones track the moving market, not stale prices.
        ver = self._next_setup_version()
        if Timeframe.M15 in snapshots:
            atr_ref = snapshots[Timeframe.M15].atr
        elif Timeframe.M30 in snapshots:
            atr_ref = snapshots[Timeframe.M30].atr
        else:
            atr_ref = 0.0
        zones = select_watch_zones(strategy, snapshots, atr_ref)
        if not zones:
            if symbol in self.setup_contexts:
                del self.setup_contexts[symbol]
            return

        # Item 1: Zone merge limit — filter out zones wider than ATR*2.0
        if self.config.use_full_triggers and self.config.filter_zone_limit and atr_ref > 0:
            max_zone_width = atr_ref * 2.0
            narrow_zones = [z for z in zones if (z.high - z.low) <= max_zone_width]
            if narrow_zones:
                zones = narrow_zones
            elif zones:
                # All zones too wide — pick closest to current price
                zones = [min(zones, key=lambda z: abs(z.mid - bar_close))]

        existing = self.setup_contexts.get(symbol)
        if existing and existing.state == "WAIT_TRIGGER_CONFIRM":
            pass  # Don't reset if already in trigger confirmation
        else:
            ctx = SetupContext(
                setup_version=ver,
                strategy=strategy,
                state="WAIT_ZONE_TOUCH",
                watch_zones=zones,
                active_zone=None,
                side=side,
                entry_price=None,
                stop_price=None,
                tp1_price=None,
                tp2_price=None,
                tp3_price=None,
                rr_to_tp1=None,
                invalidation_reason=None,
            )
            self.setup_contexts[symbol] = ctx

        ctx = self.setup_contexts[symbol]

        # Check zone touch — use bar high/low range, not just close
        if ctx.state == "WAIT_ZONE_TOUCH":
            bar_high = bar_primary["high"]
            bar_low = bar_primary["low"]
            # Check if any part of the bar's range enters a watch zone
            touched = None
            for z in ctx.watch_zones:
                if z.low <= 0 or z.high <= 0:
                    continue  # skip invalid zones (VP=0)
                if bar_low <= z.high and bar_high >= z.low:
                    touched = z
                    break
            if touched is not None:
                ctx.state = "WAIT_TRIGGER_CONFIRM"
                ctx.active_zone = touched
                self._log_decision(
                    timestamp, symbol, "ZONE_TOUCHED",
                    self.state.symbols[symbol], mode_result,
                    f"zone {touched.id} touched at {bar_close:.2f}",
                )

        # Trigger + entry: if zone touched, check trigger and place entry
        if ctx.state == "WAIT_TRIGGER_CONFIRM" and ctx.active_zone is not None:
            zone = ctx.active_zone
            atr_15m = snapshots[Timeframe.M15].atr if Timeframe.M15 in snapshots else (snapshots[Timeframe.M30].atr if Timeframe.M30 in snapshots else bar_close * 0.001)

            # Full trigger confirmation mode: validate trigger, use simplified stop/TP
            # (Full stop/TP via spec functions deferred to Phase 3 with swing tracking)
            if self.config.use_full_triggers:
                # Compute simplified stop/TP first for RR check
                if side == Side.LONG:
                    stop_price = zone.low - 0.2 * atr_15m
                    tp1_price = bar_close + abs(bar_close - stop_price) * self.config.min_rr
                    tp2_price = bar_close + abs(bar_close - stop_price) * self.config.min_rr * 2.0
                else:
                    stop_price = zone.high + 0.2 * atr_15m
                    tp1_price = bar_close - abs(bar_close - stop_price) * self.config.min_rr
                    tp2_price = bar_close - abs(bar_close - stop_price) * self.config.min_rr * 2.0

                risk_distance = abs(bar_close - stop_price)
                rr = abs(tp1_price - bar_close) / risk_distance if risk_distance > 0 else 0

                # Set RR on context for trigger check
                from dataclasses import replace as _replace
                ctx = _replace(ctx, rr_to_tp1=rr, stop_price=stop_price,
                               tp1_price=tp1_price, tp2_price=tp2_price)
                self.setup_contexts[symbol] = ctx

                # Validate trigger conditions
                trigger_input = self._build_trigger_input(bar_primary, snapshots, sym_data, timestamp)
                if trigger_input is not None:
                    new_ctx = evaluate_setup_transition(
                        ctx=ctx,
                        current_price=bar_close,
                        trigger_input=trigger_input,
                        snapshots=snapshots,
                        mode_result=mode_result,
                    )
                    if str(new_ctx.state) == "INVALIDATED":
                        self._log_decision(
                            timestamp, symbol, "TRIGGER_REJECTED",
                            self.state.symbols[symbol], mode_result,
                            f"trigger failed: {new_ctx.invalidation_reason}",
                        )
                        del self.setup_contexts[symbol]
                        return
                    if str(new_ctx.state) != "ENTRY_READY":
                        # Still waiting for trigger confirmation
                        self.setup_contexts[symbol] = new_ctx
                        return
            else:
                # Simplified mode (backward compatible)
                if side == Side.LONG:
                    stop_price = zone.low - 0.2 * atr_15m
                    tp1_price = bar_close + abs(bar_close - stop_price) * self.config.min_rr
                    tp2_price = bar_close + abs(bar_close - stop_price) * self.config.min_rr * 2.0
                else:
                    stop_price = zone.high + 0.2 * atr_15m
                    tp1_price = bar_close - abs(bar_close - stop_price) * self.config.min_rr
                    tp2_price = bar_close - abs(bar_close - stop_price) * self.config.min_rr * 2.0

            risk_distance = abs(bar_close - stop_price)
            if risk_distance == 0:
                return

            rr = abs(tp1_price - bar_close) / risk_distance
            if rr < self.config.min_rr:
                self._log_decision(
                    timestamp, symbol, "SETUP_REJECTED",
                    self.state.symbols[symbol], mode_result,
                    f"RR {rr:.2f} < min {self.config.min_rr}",
                )
                del self.setup_contexts[symbol]
                return

            # --- Entry filters (Phase 3C) — each gated by individual config flag ---
            if self.config.use_full_triggers:
                snap_ref = snapshots.get(Timeframe.M15) or snapshots.get(Timeframe.M30)
                if snap_ref:
                    # 1. Abnormal volatility
                    if self.config.filter_volatility:
                        bar_range = bar_primary["high"] - bar_primary["low"]
                        if snap_ref.atr > 0 and bar_range > 2.5 * snap_ref.atr:
                            self._log_decision(timestamp, symbol, "FILTER_BLOCKED",
                                self.state.symbols[symbol], mode_result,
                                f"abnormal_volatility: range={bar_range:.1f} > 2.5*ATR={snap_ref.atr*2.5:.1f}")
                            del self.setup_contexts[symbol]
                            return

                    # 2. Minimum volume
                    if self.config.filter_volume:
                        if snap_ref.volume_sma_20 > 0 and bar_primary["volume"] < 0.6 * snap_ref.volume_sma_20:
                            self._log_decision(timestamp, symbol, "FILTER_BLOCKED",
                                self.state.symbols[symbol], mode_result,
                                f"low_volume: {bar_primary['volume']:.0f} < 0.6*SMA20={snap_ref.volume_sma_20*0.6:.0f}")
                            del self.setup_contexts[symbol]
                            return

                # 3. Consecutive loss gate
                if self.config.filter_consec_loss:
                    consec = self._consecutive_losses.get(symbol, 0)
                    if consec >= 3 and rr < 2.0:
                        self._log_decision(timestamp, symbol, "FILTER_BLOCKED",
                            self.state.symbols[symbol], mode_result,
                            f"consec_loss_gate: {consec} losses, RR={rr:.2f} < 2.0")
                        del self.setup_contexts[symbol]
                        return

            # Item 5: Daily loss limit
            if self.config.use_full_triggers and self.config.filter_daily_loss:
                today = timestamp.strftime("%Y-%m-%d")
                daily = self._daily_pnl.get(today, 0.0)
                if daily <= -3.0 * self._daily_r_unit:
                    self._log_decision(timestamp, symbol, "FILTER_BLOCKED",
                        self.state.symbols[symbol], mode_result,
                        f"daily_loss_limit: daily_pnl={daily:.2f} <= -3R={-3.0 * self._daily_r_unit:.2f}")
                    if symbol in self.setup_contexts:
                        del self.setup_contexts[symbol]
                    return

            # Determine risk pct based on strategy
            risk_pct = self.config.risk_pct
            if strategy == "REBOUND_SHORT":
                risk_pct = self.config.counter_trend_risk_pct

            qty = compute_position_size(
                account_balance=self.balance,
                risk_pct=risk_pct,
                entry_price=bar_close,
                stop_price=stop_price,
                min_qty=self.config.min_qty,
            )
            if qty <= 0:
                return

            # Item 8: Risk budget check — block entry if total open risk > 1%
            if self.config.use_full_triggers and self.config.filter_risk_budget:
                current_risk_pct = 0.0
                for _sym, info in self._open_trade_info.items():
                    r = abs(info["entry_price"] - info["stop_price"]) * info["qty"]
                    current_risk_pct += r / self.balance if self.balance > 0 else 0
                candidate_risk = risk_distance * qty / self.balance if self.balance > 0 else 0
                if current_risk_pct + candidate_risk > 0.01:  # 1.0%
                    self._log_decision(
                        timestamp, symbol, "FILTER_BLOCKED",
                        self.state.symbols[symbol], mode_result,
                        f"risk_budget: open={current_risk_pct:.4f} + new={candidate_risk:.4f} > 1%",
                    )
                    if symbol in self.setup_contexts:
                        del self.setup_contexts[symbol]
                    return

            # Place entry order(s)
            order_id = str(uuid.uuid4())[:8]

            # Item 4: Split entry 50/30/20 under use_full_triggers
            if self.config.use_full_triggers and self.config.filter_split_entry:
                qty1 = math.floor(qty * 0.50 / self.config.min_qty) * self.config.min_qty
                qty2 = math.floor(qty * 0.30 / self.config.min_qty) * self.config.min_qty
                qty3 = qty - qty1 - qty2
                # 1st: 50% market immediate
                entry_order_1 = VirtualOrder(
                    order_id=f"entry_{order_id}_1",
                    symbol=symbol,
                    side=side,
                    price=bar_close,
                    qty=qty1,
                    order_type="market",
                    created_at=timestamp,
                    ttl_bars=2,
                )
                self.pending_orders.append(entry_order_1)
                # 2nd: 30% limit at entry price (fills on pullback)
                if qty2 > 0:
                    entry_order_2 = VirtualOrder(
                        order_id=f"entry_{order_id}_2",
                        symbol=symbol,
                        side=side,
                        price=bar_close,
                        qty=qty2,
                        order_type="limit",
                        created_at=timestamp,
                        ttl_bars=6,
                    )
                    self.pending_orders.append(entry_order_2)
                # 3rd: 20% limit slightly beyond entry (fills on continuation)
                if qty3 > 0:
                    if side == Side.LONG:
                        price3 = bar_close + risk_distance * 0.3
                    else:
                        price3 = bar_close - risk_distance * 0.3
                    entry_order_3 = VirtualOrder(
                        order_id=f"entry_{order_id}_3",
                        symbol=symbol,
                        side=side,
                        price=price3,
                        qty=qty3,
                        order_type="limit",
                        created_at=timestamp,
                        ttl_bars=12,
                    )
                    self.pending_orders.append(entry_order_3)
            else:
                entry_order = VirtualOrder(
                    order_id=f"entry_{order_id}",
                    symbol=symbol,
                    side=side,
                    price=bar_close,
                    qty=qty,
                    order_type="market",
                    created_at=timestamp,
                    ttl_bars=2,
                )
                self.pending_orders.append(entry_order)

            # Place stop order (full qty regardless of split)
            stop_order = VirtualOrder(
                order_id=f"stop_{order_id}",
                symbol=symbol,
                side=Side.SHORT if side == Side.LONG else Side.LONG,
                price=stop_price,
                qty=qty,
                order_type="stop",
                created_at=timestamp,
                ttl_bars=9999,  # stop lives until cancelled
            )
            self.pending_orders.append(stop_order)

            # Place TP limit orders — spec: 30% at TP1, 30% at TP2, 40% trailing/stop
            tp1_qty = math.floor(qty * 0.30 / self.config.min_qty) * self.config.min_qty
            tp2_qty = math.floor(qty * 0.30 / self.config.min_qty) * self.config.min_qty
            trailing_qty = qty - tp1_qty - tp2_qty  # ~40%
            tp1_order = VirtualOrder(
                order_id=f"tp1_{order_id}",
                symbol=symbol,
                side=Side.SHORT if side == Side.LONG else Side.LONG,
                price=tp1_price,
                qty=tp1_qty,
                order_type="limit",
                created_at=timestamp,
                ttl_bars=9999,
            )
            tp2_order = VirtualOrder(
                order_id=f"tp2_{order_id}",
                symbol=symbol,
                side=Side.SHORT if side == Side.LONG else Side.LONG,
                price=tp2_price,
                qty=tp2_qty,
                order_type="limit",
                created_at=timestamp,
                ttl_bars=9999,
            )
            if tp1_order.qty > 0:
                self.pending_orders.append(tp1_order)
            if tp2_order.qty > 0:
                self.pending_orders.append(tp2_order)

            # Store trade info for later record creation
            regime = self._regime_cache.get(symbol)
            self._open_trade_info[symbol] = {
                "strategy": strategy,
                "side": side.value,
                "entry_price": bar_close,
                "qty": qty,
                "stop_price": stop_price,
                "tp1_price": tp1_price,
                "tp2_price": tp2_price,
                "entry_time": timestamp,
                "regime_at_entry": regime.htf.value if regime else "UNKNOWN",
                "mode_at_entry": mode_result.mode.value,
                "rr_planned": rr,
                "commission_entry": 0.0,
                "order_id_prefix": order_id,
            }

            # Update symbol state
            sym_state = self.state.symbols[symbol]
            sym_state.lifecycle = TradeLifecycleState.ENTRY_WORKING
            sym_state.side = side
            sym_state.setup_version = ctx.setup_version
            sym_state.stop_price = stop_price
            sym_state.tp1_price = tp1_price
            sym_state.tp2_price = tp2_price

            self._log_decision(
                timestamp, symbol, "ENTRY_SIGNAL",
                sym_state, mode_result,
                f"entry={bar_close:.2f} stop={stop_price:.2f} tp1={tp1_price:.2f} qty={qty}",
            )

            # Remove setup context (setup consumed)
            del self.setup_contexts[symbol]

    def _handle_entry_fill(
        self,
        symbol: str,
        order: VirtualOrder,
        fill: FillResult,
        timestamp: datetime,
    ) -> None:
        """Handle an entry order fill."""
        self.total_commission += fill.commission
        sym_state = self.state.symbols[symbol]
        sym_state.avg_entry_price = fill.fill_price
        sym_state.filled_qty = fill.fill_qty
        sym_state.entry_timestamp = timestamp
        sym_state.lifecycle = TradeLifecycleState.OPEN_STAGE0

        if symbol in self._open_trade_info:
            self._open_trade_info[symbol]["entry_price"] = fill.fill_price
            self._open_trade_info[symbol]["commission_entry"] = fill.commission

    def _handle_exit_fill(
        self,
        symbol: str,
        order: VirtualOrder,
        fill: FillResult,
        timestamp: datetime,
        exit_reason: str,
    ) -> None:
        """Handle an exit order fill. Partial exits (TP1/TP2) reduce position; full exits close it."""
        self.total_commission += fill.commission
        trade_info = self._open_trade_info.get(symbol)
        if trade_info is None:
            return

        entry_price = trade_info["entry_price"]
        qty = fill.fill_qty
        side = trade_info["side"]
        is_partial = exit_reason in ("tp1", "tp2")

        # Calculate PnL for this fill
        if side == "LONG":
            raw_pnl = (fill.fill_price - entry_price) * qty
        else:
            raw_pnl = (entry_price - fill.fill_price) * qty
        commission_this = fill.commission
        pnl = raw_pnl - commission_this

        # PnL in R units
        risk_per_unit = abs(entry_price - trade_info["stop_price"])
        risk_total = risk_per_unit * trade_info["qty"]
        pnl_r = pnl / risk_total if risk_total > 0 else 0.0

        # R:R actual
        reward_per_unit = abs(fill.fill_price - entry_price)
        rr_actual = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0.0

        # Duration in 5m bars
        entry_time = trade_info["entry_time"]
        duration = timestamp - entry_time
        duration_bars = max(1, int(duration.total_seconds() / 300))

        record = TradeRecord(
            symbol=symbol,
            strategy=trade_info["strategy"],
            side=side,
            entry_price=entry_price,
            exit_price=fill.fill_price,
            qty=qty,
            pnl=pnl,
            pnl_r=pnl_r,
            commission_total=commission_this,
            entry_time=entry_time,
            exit_time=timestamp,
            duration_bars=duration_bars,
            exit_reason=exit_reason,
            regime_at_entry=trade_info["regime_at_entry"],
            mode_at_entry=trade_info["mode_at_entry"],
            rr_planned=trade_info["rr_planned"],
            rr_actual=rr_actual,
        )
        self.trade_records.append(record)

        # Update balance
        self.balance += pnl
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance
        drawdown = self.peak_balance - self.balance
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown

        # Item 5: Track daily PnL
        day_key = timestamp.strftime("%Y-%m-%d")
        self._daily_pnl[day_key] = self._daily_pnl.get(day_key, 0.0) + pnl

        # Track consecutive losses (Phase 3C)
        if not is_partial:
            if pnl < 0:
                self._consecutive_losses[symbol] = self._consecutive_losses.get(symbol, 0) + 1
            else:
                self._consecutive_losses[symbol] = 0

        if is_partial:
            # Partial exit (TP1/TP2): reduce remaining qty, update stop qty, advance stage
            sym_state = self.state.symbols[symbol]
            remaining = (sym_state.filled_qty or trade_info["qty"]) - qty
            sym_state.filled_qty = remaining
            # Update stop order qty to match remaining position
            prefix = trade_info.get("order_id_prefix", "")
            for o in self.pending_orders:
                if o.symbol == symbol and o.order_id.startswith(f"stop_{prefix}"):
                    o.qty = remaining
            # Advance lifecycle stage
            if exit_reason == "tp1":
                sym_state.lifecycle = TradeLifecycleState.OPEN_STAGE1
            elif exit_reason == "tp2":
                sym_state.lifecycle = TradeLifecycleState.OPEN_STAGE2
            return  # Don't close the position

        # Full exit (stop, max_hold, trailing): close everything
        if pnl < 0:
            self.state.global_state.consecutive_losses += 1
        else:
            self.state.global_state.consecutive_losses = 0

        # Cancel remaining orders for this symbol
        prefix = trade_info.get("order_id_prefix", "")
        if prefix:
            self.pending_orders = [
                o for o in self.pending_orders
                if not (o.symbol == symbol and prefix in o.order_id)
            ]

        # Reset symbol state
        sym_state = self.state.symbols[symbol]
        was_stop = exit_reason == "stop"
        sym_state.lifecycle = TradeLifecycleState.COOLDOWN
        sym_state.filled_qty = 0.0
        sym_state.cooldown_until = compute_cooldown_end(
            timestamp,
            was_stop_loss=was_stop,
            normal_bars=self.config.cooldown_normal_bars,
            stop_loss_bars=self.config.cooldown_stop_bars,
        )
        sym_state.last_transition_reason = f"exit: {exit_reason}"

        # Clean up open trade info
        if symbol in self._open_trade_info:
            del self._open_trade_info[symbol]

    def _evaluate_position_management(
        self,
        symbol: str,
        timestamp: datetime,
        bar_close: float,
        snapshots: dict[Timeframe, TimeframeSnapshot],
    ) -> None:
        """Evaluate trailing stop and max hold for an open position."""
        sym_state = self.state.symbols[symbol]
        trade_info = self._open_trade_info.get(symbol)
        if trade_info is None:
            # Orphaned OPEN state with no trade info — reset to FLAT
            sym_state.lifecycle = TradeLifecycleState.FLAT
            sym_state.side = Side.NONE
            sym_state.filled_qty = None
            sym_state.stop_price = None
            return

        entry_price = trade_info["entry_price"]
        stop_price = trade_info["stop_price"]
        entry_time = trade_info["entry_time"]

        # PnL in R units for max hold
        risk_per_unit = abs(entry_price - stop_price)
        if risk_per_unit > 0:
            if trade_info["side"] == "LONG":
                unrealized_r = (bar_close - entry_price) / risk_per_unit
            else:
                unrealized_r = (entry_price - bar_close) / risk_per_unit
        else:
            unrealized_r = 0.0

        # Trailing stop evaluation (only in STAGE1+ after TP1 hit)
        strategy = trade_info.get("strategy", "")
        if sym_state.lifecycle in (TradeLifecycleState.OPEN_STAGE1, TradeLifecycleState.OPEN_STAGE2):
            snap_5m = snapshots.get(Timeframe.M5)
            snap_15m = snapshots.get(Timeframe.M15)
            snap_30m = snapshots.get(Timeframe.M30)
            trailing_action = None

            if strategy == "TREND_LONG" and snap_5m and snap_15m:
                trailing_action = evaluate_trailing_trend_long(
                    close_5m=snap_5m.close, kijun_5m=snap_5m.kijun,
                    close_15m=snap_15m.close, tenkan_15m=snap_15m.tenkan,
                )
            elif strategy == "PULLBACK_LONG" and snap_15m and snap_30m:
                zone_mid = trade_info.get("stop_price", 0) + abs(entry_price - trade_info.get("stop_price", 0)) * 0.5
                trailing_action = evaluate_trailing_pullback_long(
                    close_15m=snap_15m.close, kijun_15m=snap_15m.kijun,
                    close_30m=snap_30m.close, zone_mid=zone_mid,
                )
            elif strategy == "REBOUND_SHORT" and snap_5m and snap_15m:
                trailing_action = evaluate_trailing_rebound_short(
                    close_5m=snap_5m.close, kijun_5m=snap_5m.kijun,
                    close_15m=snap_15m.close, tenkan_15m=snap_15m.tenkan,
                    kijun_15m=snap_15m.kijun,
                )

            if trailing_action and trailing_action.action == "close_all":
                self._place_market_exit(symbol, timestamp, "trailing")
                return
            elif trailing_action and trailing_action.action in ("reduce_half", "reduce_30pct"):
                # Tighten stop to breakeven instead of partial close (simpler for backtest)
                prefix = trade_info.get("order_id_prefix", "")
                for o in self.pending_orders:
                    if o.symbol == symbol and o.order_id.startswith(f"stop_{prefix}"):
                        o.price = entry_price  # move stop to breakeven

        # Max hold check
        max_hold_action = evaluate_max_hold(
            entry_timestamp=entry_time,
            current_timestamp=timestamp,
            unrealized_pnl_r=unrealized_r,
            max_bars=self.config.max_hold_bars,
        )
        if max_hold_action.action == "close_all":
            self._place_market_exit(symbol, timestamp, "max_hold")
            return

    def _place_market_exit(
        self,
        symbol: str,
        timestamp: datetime,
        reason: str,
    ) -> None:
        """Place a market exit order for the full position."""
        trade_info = self._open_trade_info.get(symbol)
        if trade_info is None:
            return

        sym_state = self.state.symbols[symbol]
        qty = sym_state.filled_qty or trade_info["qty"]
        side = Side.SHORT if trade_info["side"] == "LONG" else Side.LONG

        order = VirtualOrder(
            order_id=f"exit_{str(uuid.uuid4())[:8]}",
            symbol=symbol,
            side=side,
            price=0.0,  # market order
            qty=qty,
            order_type="market",
            created_at=timestamp,
            ttl_bars=1,
        )
        self.pending_orders.append(order)

        # Cancel existing stop/tp orders for this symbol
        prefix = trade_info.get("order_id_prefix", "")
        if prefix:
            self.pending_orders = [
                o for o in self.pending_orders
                if not (o.symbol == symbol and prefix in o.order_id)
            ] + [order]

    def _log_decision(
        self,
        timestamp: datetime,
        symbol: str,
        event_type: str,
        sym_state: SymbolState,
        mode_result: ModeResult | None,
        reason: str,
        details: dict | None = None,
    ) -> None:
        """Append a decision log entry."""
        regime = self._regime_cache.get(symbol)
        log = DecisionLog(
            timestamp=timestamp,
            symbol=symbol,
            event_type=event_type,
            regime_state=regime.htf.value if regime else "UNKNOWN",
            mode_state=mode_result.mode.value if mode_result else "UNKNOWN",
            setup_state=self.setup_contexts[symbol].state if symbol in self.setup_contexts else "NONE",
            lifecycle_state=sym_state.lifecycle.value,
            reason=reason,
            details=details,
        )
        self.decision_logs.append(log)

    def _build_result(self) -> BacktestResult:
        """Compute final metrics and return BacktestResult."""
        trades = self.trade_records
        total_trades = len(trades)

        if total_trades == 0:
            return BacktestResult(
                trades=trades,
                decision_logs=self.decision_logs,
                final_balance=self.balance,
                total_pnl=self.balance - self.config.initial_balance,
                total_commission=self.total_commission,
                win_rate=0.0,
                avg_rr=0.0,
                max_drawdown=self.max_drawdown,
                max_consecutive_losses=0,
                sharpe_ratio=None,
                total_trades=0,
                long_trades=0,
                short_trades=0,
                avg_hold_bars=0.0,
            )

        wins = sum(1 for t in trades if t.pnl > 0)
        win_rate = (wins / total_trades) * 100.0

        avg_rr = sum(t.rr_actual for t in trades) / total_trades

        long_trades = sum(1 for t in trades if t.side == "LONG")
        short_trades = sum(1 for t in trades if t.side == "SHORT")

        avg_hold = sum(t.duration_bars for t in trades) / total_trades

        # Max consecutive losses
        max_consec = 0
        current_consec = 0
        for t in trades:
            if t.pnl < 0:
                current_consec += 1
                max_consec = max(max_consec, current_consec)
            else:
                current_consec = 0

        # Sharpe ratio (annualized, using daily returns approximation)
        pnl_values = [t.pnl for t in trades]
        if len(pnl_values) >= 2:
            mean_pnl = np.mean(pnl_values)
            std_pnl = np.std(pnl_values, ddof=1)
            if std_pnl > 0:
                # Approximate: assume ~288 5m bars per day, annualize by sqrt(365)
                sharpe = (mean_pnl / std_pnl) * math.sqrt(365)
            else:
                sharpe = None
        else:
            sharpe = None

        total_pnl = self.balance - self.config.initial_balance

        return BacktestResult(
            trades=trades,
            decision_logs=self.decision_logs,
            final_balance=self.balance,
            total_pnl=total_pnl,
            total_commission=self.total_commission,
            win_rate=win_rate,
            avg_rr=avg_rr,
            max_drawdown=self.max_drawdown,
            max_consecutive_losses=max_consec,
            sharpe_ratio=sharpe,
            total_trades=total_trades,
            long_trades=long_trades,
            short_trades=short_trades,
            avg_hold_bars=avg_hold,
        )
