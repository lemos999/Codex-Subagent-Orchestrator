"""Trading engine — the integration layer that coordinates all modules.

Implements the orchestrator per state machine design doc section 4 (overall structure),
section 9.1 (EngineState transitions), and section 10 (evaluation priority).

This module is stateful (it is the coordinator) but delegates to pure functions
in the core and infra modules.
"""
from __future__ import annotations

import logging
from datetime import datetime

from .events import (
    BarClosedEvent,
    EngineEvent,
    Event,
    EventType,
    RiskEvent,
)
from .indicators import build_timeframe_snapshot
from .mode import ModeResult, evaluate_mode
from .models import (
    EngineState,
    GlobalState,
    ModeState,
    RiskGate,
    SetupState,
    Side,
    SymbolState,
    Timeframe,
    TimeframeSnapshot,
    TradeLifecycleState,
    TradingState,
)
from .position import process_lifecycle_event, LifecycleTransition
from .regime import RegimeSnapshot, classify_regime
from .risk import RiskTracker, evaluate_risk_gate
from .setup import SetupContext, evaluate_setup_transition

from ..infra.journal import DecisionJournal, JournalEntry
from ..infra.state_store import StateStore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. EngineState transition (pure function, section 9.1)
# ---------------------------------------------------------------------------

# System event types that trigger engine state changes
_SYSTEM_EVENTS = frozenset({
    EventType.BOOT_COMPLETED,
    EventType.HISTORY_READY,
    EventType.API_DEGRADED,
    EventType.API_RECOVERED,
    EventType.MANUAL_HALT,
    EventType.MANUAL_RESUME,
    EventType.RISK_LIMIT_BREACHED,
})

# Order event types routed to _handle_order_event
_ORDER_EVENTS = frozenset({
    EventType.ENTRY_ORDER_SUBMITTED,
    EventType.ENTRY_ORDER_PARTIAL_FILL,
    EventType.ENTRY_ORDER_FILLED,
    EventType.STOP_ORDER_ATTACHED,
    EventType.TP1_FILLED,
    EventType.TP2_FILLED,
    EventType.STOP_FILLED,
    EventType.EXIT_ORDER_FILLED,
    EventType.TRIGGER_INVALIDATED,
})

# Bar close event types
_BAR_EVENTS = frozenset({
    EventType.BAR_CLOSED_4H,
    EventType.BAR_CLOSED_1H,
    EventType.BAR_CLOSED_30M,
    EventType.BAR_CLOSED_15M,
    EventType.BAR_CLOSED_5M,
})


def transition_engine_state(
    current: EngineState,
    event: Event,
    data_ready: bool = False,
) -> tuple[EngineState, str]:
    """Pure function for engine state transitions per section 9.1.

    BOOTSTRAPPING -> WARMUP: on BOOT_COMPLETED
    WARMUP -> READY: on HISTORY_READY (all timeframes have enough data)
    READY -> DEGRADED: on API_DEGRADED
    DEGRADED -> READY: on API_RECOVERED + consistency check
    any -> HALTED: on MANUAL_HALT or critical failure
    HALTED -> WARMUP: on MANUAL_RESUME

    Returns (new_state, reason).
    """
    et = event.event_type

    # any -> HALTED on MANUAL_HALT
    if et == EventType.MANUAL_HALT:
        return EngineState.HALTED, "manual halt requested"

    # RISK_LIMIT_BREACHED -> HALTED (policy: auto-halt on risk breach)
    if et == EventType.RISK_LIMIT_BREACHED and current != EngineState.HALTED:
        return EngineState.HALTED, "risk limit breached — automatic halt"

    # BOOTSTRAPPING -> WARMUP
    if current == EngineState.BOOTSTRAPPING and et == EventType.BOOT_COMPLETED:
        return EngineState.WARMUP, "boot completed — entering warmup"

    # WARMUP -> READY
    if current == EngineState.WARMUP and et == EventType.HISTORY_READY:
        if data_ready:
            return EngineState.READY, "history ready — all timeframes available"
        return EngineState.WARMUP, "history event received but data not ready"

    # READY -> DEGRADED
    if current == EngineState.READY and et == EventType.API_DEGRADED:
        return EngineState.DEGRADED, "API degraded — suspending new trades"

    # DEGRADED -> READY
    if current == EngineState.DEGRADED and et == EventType.API_RECOVERED:
        return EngineState.READY, "API recovered — resuming after consistency check"

    # HALTED -> WARMUP
    if current == EngineState.HALTED and et == EventType.MANUAL_RESUME:
        return EngineState.WARMUP, "manual resume — re-entering warmup"

    return current, f"no transition: {current} + {et}"


# ---------------------------------------------------------------------------
# 2. Bar close timeframe detection
# ---------------------------------------------------------------------------

_TF_ORDER = [Timeframe.H4, Timeframe.H1, Timeframe.M30, Timeframe.M15, Timeframe.M5]

_TF_MINUTES = {
    Timeframe.H4: 240,
    Timeframe.H1: 60,
    Timeframe.M30: 30,
    Timeframe.M15: 15,
    Timeframe.M5: 5,
}


def detect_bar_closes(timestamp: datetime) -> list[Timeframe]:
    """Determine which timeframes close at this timestamp.

    Returns in order: 4H -> 1H -> 30M -> 15M -> 5M (higher first per section 10).
    A timeframe closes when the timestamp's total minutes since midnight
    is evenly divisible by the timeframe's period.
    """
    total_minutes = timestamp.hour * 60 + timestamp.minute
    result: list[Timeframe] = []
    for tf in _TF_ORDER:
        period = _TF_MINUTES[tf]
        if total_minutes % period == 0:
            result.append(tf)
    return result


# ---------------------------------------------------------------------------
# 3. TradingEngine class
# ---------------------------------------------------------------------------


class TradingEngine:
    """Main trading engine. Coordinates all modules per section 10 evaluation priority.

    Priority order (section 10):
    1. EngineState check
    2. RiskGate update
    3. Exchange position/order consistency check
    4. Bar close events: RegimeState + ModeState refresh (4H->1H->30M->15M->5M)
    5. Setup invalidation check
    6. Position management (exits first)
    7. New setup tracking and entry
    8. Decision log
    """

    def __init__(
        self,
        symbols: list[str],
        state_store: StateStore | None = None,
        journal: DecisionJournal | None = None,
    ) -> None:
        self.symbols = symbols
        self.state = TradingState(
            global_state=GlobalState(),
            symbols={s: SymbolState(symbol=s) for s in symbols},
        )
        self.risk_tracker = RiskTracker()
        self.setup_contexts: dict[str, SetupContext | None] = {s: None for s in symbols}
        self.snapshots: dict[str, dict[Timeframe, TimeframeSnapshot]] = {}
        self.state_store = state_store
        self.journal = journal
        self.engine_state = EngineState.BOOTSTRAPPING
        self._mode_results: dict[str, ModeResult | None] = {s: None for s in symbols}

    # -- Boot ----------------------------------------------------------------

    def boot(self) -> None:
        """BOOTSTRAPPING -> WARMUP -> READY sequence.

        1. Load saved state from state_store (if available)
        2. Transition to WARMUP
        3. Once data is available, transition to READY
        """
        # Step 1: load saved state
        if self.state_store is not None:
            snapshot = self.state_store.load_latest()
            if snapshot is not None:
                self.state = snapshot.state
                # Restore engine state from global state
                self.engine_state = EngineState(self.state.global_state.engine)
                logger.info("Loaded state snapshot version=%s", snapshot.version)

        # Step 2: transition to WARMUP
        boot_event = EngineEvent(
            event_type=EventType.BOOT_COMPLETED,
            timestamp=datetime.utcnow(),
            reason="engine boot",
        )
        new_state, reason = transition_engine_state(self.engine_state, boot_event)
        self.engine_state = new_state
        self.state.global_state.engine = new_state
        logger.info("Engine boot: %s -> %s (%s)", EngineState.BOOTSTRAPPING, new_state, reason)
        self.save_state()

    # -- Main event dispatch -------------------------------------------------

    def process_event(self, event: Event) -> None:
        """Main event processing entry point. Routes to appropriate handler.

        Per section 10, evaluation order:
        1. Check engine state -- if not READY, only handle system events
        2. Update risk gate
        3. Route by event type:
           - BarClosedEvent -> _handle_bar_close
           - Order events -> _handle_order_event
           - System events -> _handle_system_event
        """
        et = event.event_type

        # Step 1: system events are always processed
        if et in _SYSTEM_EVENTS:
            self._handle_system_event(event)
            return

        # If not READY (and not DEGRADED with existing positions), reject
        if self.engine_state not in (EngineState.READY, EngineState.DEGRADED):
            logger.debug("Ignoring event %s — engine state is %s", et, self.engine_state)
            return

        # Step 2: update risk gate
        risk_gate = evaluate_risk_gate(self.risk_tracker)
        self.state.global_state.risk_gate = risk_gate

        # Step 3: route by event type
        if et in _BAR_EVENTS:
            assert isinstance(event, BarClosedEvent)
            self._handle_bar_close(event)
        elif et in _ORDER_EVENTS:
            self._handle_order_event(event)
        else:
            logger.warning("Unhandled event type: %s", et)

    # -- Bar close handler ---------------------------------------------------

    def _handle_bar_close(self, event: BarClosedEvent) -> None:
        """Process bar close event for a symbol.

        1. Update snapshots for this timeframe
        2. If 30m+ bar close: refresh regime and mode
        3. Check setup invalidation
        4. Evaluate position (trailing, max hold)
        5. If FLAT and mode allows: evaluate setup for new entry
        6. Log decision
        """
        symbol = event.symbol
        if symbol is None or symbol not in self.state.symbols:
            return

        sym_state = self.state.symbols[symbol]
        tf = event.timeframe

        # Step 1: update snapshot for this timeframe
        if symbol not in self.snapshots:
            self.snapshots[symbol] = {}
        # Build a minimal snapshot from the bar event data
        snap = TimeframeSnapshot(
            timeframe=tf,
            timestamp=event.timestamp,
            close=event.close,
            tenkan=0.0,  # Will be populated from full indicator engine
            kijun=0.0,
            cloud_top=0.0,
            cloud_bottom=0.0,
            cloud_position="in",
            tk_state="bullish",
            poc=0.0,
            vah=0.0,
            val=0.0,
            profile_bias="inside_va",
            volume=event.volume,
            volume_sma_5=0.0,
            volume_sma_20=0.0,
            atr=0.0,
        )
        self.snapshots[symbol][tf] = snap

        # Step 2: refresh regime and mode on 30m+ bar close
        htf_timeframes = {Timeframe.H4, Timeframe.H1, Timeframe.M30}
        if tf in htf_timeframes:
            self._update_regime_mode(symbol)

        # Step 3: check setup invalidation (reset INVALIDATED -> IDLE on new 30m cycle)
        ctx = self.setup_contexts.get(symbol)
        if ctx is not None and ctx.state == SetupState.INVALIDATED:
            if tf == Timeframe.M30:
                # New 30m evaluation cycle: reset to IDLE per section 9.2
                self.setup_contexts[symbol] = None
                sym_state.setup = SetupState.IDLE

        # Step 4: evaluate position management (exits first, per section 10 rule 6)
        if sym_state.lifecycle not in (
            TradeLifecycleState.FLAT,
            TradeLifecycleState.COOLDOWN,
        ):
            self._evaluate_position(symbol)

        # Step 5: new setup tracking if FLAT and mode allows (section 10 rule 7)
        if sym_state.lifecycle == TradeLifecycleState.FLAT:
            if self.engine_state == EngineState.READY:
                self._evaluate_setup(symbol)

        # Step 6: process lifecycle transitions (COOLDOWN -> FLAT, EXIT_WORKING -> COOLDOWN)
        transition = process_lifecycle_event(
            sym_state, self.state.global_state, event,
        )
        if transition is not None:
            self._apply_lifecycle_transition(symbol, transition, event)

        # Log decision
        self._log_decision(
            symbol,
            event.event_type,
            f"bar_close {tf}",
            timeframe=str(tf),
        )
        self.save_state()

    # -- Order event handler -------------------------------------------------

    def _handle_order_event(self, event: Event) -> None:
        """Process order lifecycle events.

        Routes to position.process_lifecycle_event.
        Updates symbol state and global risk.
        """
        symbol = event.symbol
        if symbol is None or symbol not in self.state.symbols:
            return

        sym_state = self.state.symbols[symbol]
        transition = process_lifecycle_event(
            sym_state, self.state.global_state, event,
        )

        if transition is not None:
            self._apply_lifecycle_transition(symbol, transition, event)
            self._log_decision(
                symbol,
                event.event_type,
                transition.reason,
            )
            self.save_state()

    # -- System event handler ------------------------------------------------

    def _handle_system_event(self, event: Event) -> None:
        """Handle engine state transitions.

        - API_DEGRADED: READY -> DEGRADED
        - API_RECOVERED: DEGRADED -> READY (after consistency check)
        - MANUAL_HALT: any -> HALTED
        - MANUAL_RESUME: HALTED -> WARMUP
        - RISK_LIMIT_BREACHED: update risk gate
        """
        et = event.event_type

        # Update risk tracker on risk breach event
        if et == EventType.RISK_LIMIT_BREACHED and isinstance(event, RiskEvent):
            logger.warning(
                "Risk limit breached: %s (value=%s, threshold=%s)",
                event.rule_name, event.current_value, event.threshold,
            )

        old_state = self.engine_state
        new_state, reason = transition_engine_state(
            self.engine_state, event, data_ready=True,
        )

        if new_state != old_state:
            self.engine_state = new_state
            self.state.global_state.engine = new_state
            logger.info("Engine state: %s -> %s (%s)", old_state, new_state, reason)

            self._log_decision(
                symbol="__engine__",
                event_type=str(et),
                reason=reason,
            )
            self.save_state()

    # -- Internal helpers ----------------------------------------------------

    def _update_regime_mode(self, symbol: str) -> None:
        """Refresh regime classification and mode selection for a symbol."""
        sym_snaps = self.snapshots.get(symbol, {})

        # Need at least H4, H1, M30 for regime classification
        required = {Timeframe.H4, Timeframe.H1, Timeframe.M30}
        if not required.issubset(sym_snaps.keys()):
            return

        regime = classify_regime(sym_snaps)
        sym_state = self.state.symbols[symbol]
        sym_state.regime = regime.htf

        # Evaluate mode
        risk_blocked = self.state.global_state.risk_gate == RiskGate.BLOCK
        mode_result = evaluate_mode(
            regime,
            engine_ready=(self.engine_state == EngineState.READY),
            risk_gate_blocked=risk_blocked,
        )
        sym_state.mode = mode_result.mode
        self._mode_results[symbol] = mode_result

    def _evaluate_setup(self, symbol: str) -> None:
        """Evaluate setup state machine for a symbol. May create new SetupContext."""
        sym_state = self.state.symbols[symbol]
        mode_result = self._mode_results.get(symbol)
        sym_snaps = self.snapshots.get(symbol, {})

        # Cannot evaluate without mode result or snapshots
        if mode_result is None:
            return

        # DEGRADED state: no new entries per section 6
        if self.engine_state == EngineState.DEGRADED:
            return

        ctx = self.setup_contexts.get(symbol)

        # If no active setup and mode allows trading, create context
        if ctx is None and mode_result.mode != ModeState.MODE_NO_TRADE:
            if mode_result.allowed_setups:
                strategy = mode_result.allowed_setups[0]
                side_map = {
                    "TREND_LONG": "LONG",
                    "PULLBACK_LONG": "LONG",
                    "REBOUND_SHORT": "SHORT",
                }
                side = Side(side_map.get(strategy, "NONE"))
                sym_state.setup_version += 1
                ctx = SetupContext(
                    setup_version=sym_state.setup_version,
                    strategy=strategy,
                    state=SetupState.IDLE,
                    watch_zones=[],
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

        if ctx is not None:
            # Use current close as current_price
            current_price = 0.0
            for tf in reversed(_TF_ORDER):
                if tf in sym_snaps:
                    current_price = sym_snaps[tf].close
                    break

            ctx = evaluate_setup_transition(
                ctx=ctx,
                current_price=current_price,
                trigger_input=None,  # Trigger input comes from external data
                snapshots=sym_snaps,
                mode_result=mode_result,
            )
            self.setup_contexts[symbol] = ctx
            sym_state.setup = ctx.state

    def _evaluate_position(self, symbol: str) -> None:
        """Evaluate position: trailing stops, max hold, etc.

        Delegates to position module functions. In DEGRADED state,
        existing positions are maintained but no new entries allowed.
        """
        # Position evaluation is handled via order events from the exchange.
        # The engine coordinates but does not directly compute trailing —
        # that requires real-time price data from the exchange adapter.
        # This method is a hook for future integration.
        pass

    def _apply_lifecycle_transition(
        self,
        symbol: str,
        transition: LifecycleTransition,
        event: Event,
    ) -> None:
        """Apply a lifecycle transition to symbol state."""
        sym_state = self.state.symbols[symbol]
        old_lifecycle = sym_state.lifecycle
        sym_state.lifecycle = transition.new_state
        sym_state.last_transition_reason = transition.reason

        # Apply updates from transition
        for key, value in transition.updates.items():
            if key.startswith("_"):
                continue  # Skip internal markers
            if hasattr(sym_state, key):
                setattr(sym_state, key, value)

        logger.info(
            "%s lifecycle: %s -> %s (%s)",
            symbol, old_lifecycle, transition.new_state, transition.reason,
        )

    def _log_decision(
        self,
        symbol: str,
        event_type: str,
        reason: str,
        **kwargs: object,
    ) -> None:
        """Record decision in journal."""
        if self.journal is None:
            return

        sym_state = self.state.symbols.get(symbol)
        entry = JournalEntry(
            timestamp=datetime.utcnow(),
            symbol=symbol,
            event_type=str(event_type),
            engine_state=str(self.engine_state),
            risk_gate=str(self.state.global_state.risk_gate),
            regime_state=str(sym_state.regime) if sym_state else "",
            mode_state=str(sym_state.mode) if sym_state else "",
            setup_state=str(sym_state.setup) if sym_state else "",
            trade_lifecycle_state=str(sym_state.lifecycle) if sym_state else "",
            setup_version=sym_state.setup_version if sym_state else 0,
            transition_from="",
            transition_to="",
            transition_reason=reason,
        )
        self.journal.log(entry)

    # -- State persistence ---------------------------------------------------

    def save_state(self) -> None:
        """Persist current state via state_store."""
        if self.state_store is None:
            return
        try:
            self.state.global_state.engine = self.engine_state
            self.state_store.save(self.state)
        except Exception:
            logger.exception("Failed to save state")

    # -- Monitoring ----------------------------------------------------------

    def get_status(self) -> dict:
        """Return current engine status for monitoring."""
        symbol_statuses = {}
        for sym in self.symbols:
            sym_state = self.state.symbols[sym]
            ctx = self.setup_contexts.get(sym)
            symbol_statuses[sym] = {
                "regime": str(sym_state.regime),
                "mode": str(sym_state.mode),
                "setup": str(sym_state.setup),
                "lifecycle": str(sym_state.lifecycle),
                "side": str(sym_state.side),
                "setup_version": sym_state.setup_version,
                "has_setup_context": ctx is not None,
                "setup_strategy": ctx.strategy if ctx else None,
            }

        return {
            "engine_state": str(self.engine_state),
            "risk_gate": str(self.state.global_state.risk_gate),
            "total_risk_exposure_pct": self.state.global_state.total_risk_exposure_pct,
            "consecutive_losses": self.risk_tracker.consecutive_losses,
            "symbols": symbol_statuses,
        }
