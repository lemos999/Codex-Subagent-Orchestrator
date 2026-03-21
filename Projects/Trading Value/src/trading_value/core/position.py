from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from .events import (
    EntryOrderEvent,
    Event,
    EventType,
    ExitOrderFilledEvent,
    StopFilledEvent,
    StopOrderEvent,
    TpFilledEvent,
)
from .models import (
    GlobalState,
    Side,
    SymbolState,
    TradeLifecycleState,
    TradingState,
)


# ---------------------------------------------------------------------------
# 1. Position sizing (§13.2)
# ---------------------------------------------------------------------------

def compute_position_size(
    account_balance: float,
    risk_pct: float,
    entry_price: float,
    stop_price: float,
    min_qty: float = 0.001,
) -> float:
    """TargetQty = (Balance * Risk%) / |Entry - Stop|. Round down to min_qty."""
    distance = abs(entry_price - stop_price)
    if distance == 0.0:
        return 0.0
    raw_qty = (account_balance * risk_pct) / distance
    if min_qty <= 0:
        return raw_qty
    floored = math.floor(raw_qty / min_qty) * min_qty
    return max(floored, 0.0)


# ---------------------------------------------------------------------------
# 2. Split entry (§11)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EntrySplits:
    stage1_qty: float  # 50%
    stage2_qty: float  # 30%
    stage3_qty: float  # 20%
    total_qty: float


def compute_entry_splits(
    total_qty: float,
    stage1_pct: float = 0.50,
    stage2_pct: float = 0.30,
    stage3_pct: float = 0.20,
    min_qty: float = 0.001,
) -> EntrySplits:
    """Split total quantity into 3 entry stages, each floored to min_qty."""
    def _floor(qty: float) -> float:
        if min_qty <= 0:
            return qty
        return math.floor(qty / min_qty) * min_qty

    s1 = _floor(total_qty * stage1_pct)
    s2 = _floor(total_qty * stage2_pct)
    s3 = _floor(total_qty * stage3_pct)
    return EntrySplits(
        stage1_qty=s1,
        stage2_qty=s2,
        stage3_qty=s3,
        total_qty=s1 + s2 + s3,
    )


# ---------------------------------------------------------------------------
# 3. Exit plan (§11)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExitPlan:
    tp1_qty: float  # 30%
    tp2_qty: float  # 30%
    trailing_qty: float  # 40%


def compute_exit_plan(
    total_qty: float,
    tp1_pct: float = 0.30,
    tp2_pct: float = 0.30,
    trailing_pct: float = 0.40,
    min_qty: float = 0.001,
) -> ExitPlan:
    """Split total quantity into exit plan buckets, each floored to min_qty."""
    def _floor(qty: float) -> float:
        if min_qty <= 0:
            return qty
        return math.floor(qty / min_qty) * min_qty

    t1 = _floor(total_qty * tp1_pct)
    t2 = _floor(total_qty * tp2_pct)
    tr = _floor(total_qty * trailing_pct)
    return ExitPlan(tp1_qty=t1, tp2_qty=t2, trailing_qty=tr)


# ---------------------------------------------------------------------------
# 4. Trailing stop (§11 per strategy)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TrailingAction:
    action: str  # "hold", "reduce_half", "reduce_30pct", "close_all"
    reason: str


def evaluate_trailing_trend_long(
    close_5m: float,
    kijun_5m: float,
    close_15m: float,
    tenkan_15m: float,
) -> TrailingAction:
    """§11.1: 5m close < 5m Kijun -> reduce half; 15m close < 15m Tenkan -> close all."""
    if close_15m < tenkan_15m:
        return TrailingAction(
            action="close_all",
            reason="15m close < 15m Tenkan — trend break confirmed",
        )
    if close_5m < kijun_5m:
        return TrailingAction(
            action="reduce_half",
            reason="5m close < 5m Kijun — early trend weakness",
        )
    return TrailingAction(action="hold", reason="trailing conditions intact")


def evaluate_trailing_pullback_long(
    close_15m: float,
    kijun_15m: float,
    close_30m: float,
    zone_mid: float,
) -> TrailingAction:
    """§11.2: 15m close < 15m Kijun -> reduce half; 30m close < zone mid -> close all."""
    if close_30m < zone_mid:
        return TrailingAction(
            action="close_all",
            reason="30m close < zone mid — pullback thesis invalidated",
        )
    if close_15m < kijun_15m:
        return TrailingAction(
            action="reduce_half",
            reason="15m close < 15m Kijun — pullback momentum fading",
        )
    return TrailingAction(action="hold", reason="trailing conditions intact")


def evaluate_trailing_rebound_short(
    close_5m: float,
    kijun_5m: float,
    close_15m: float,
    tenkan_15m: float,
    kijun_15m: float,
) -> TrailingAction:
    """§11.3: 5m close > 5m Kijun -> reduce 30%; 15m close > 15m Tenkan -> reduce half; 15m close > 15m Kijun -> close all."""
    if close_15m > kijun_15m:
        return TrailingAction(
            action="close_all",
            reason="15m close > 15m Kijun — rebound short invalidated",
        )
    if close_15m > tenkan_15m:
        return TrailingAction(
            action="reduce_half",
            reason="15m close > 15m Tenkan — short pressure weakening",
        )
    if close_5m > kijun_5m:
        return TrailingAction(
            action="reduce_30pct",
            reason="5m close > 5m Kijun — early counter-signal",
        )
    return TrailingAction(action="hold", reason="trailing conditions intact")


# ---------------------------------------------------------------------------
# 5. Cooldown (§13.5)
# ---------------------------------------------------------------------------

def compute_cooldown_end(
    exit_timestamp: datetime,
    was_stop_loss: bool,
    normal_bars: int = 2,
    stop_loss_bars: int = 4,
    bar_minutes: int = 30,
) -> datetime:
    """Return the datetime when cooldown ends."""
    bars = stop_loss_bars if was_stop_loss else normal_bars
    return exit_timestamp + timedelta(minutes=bars * bar_minutes)


def is_cooldown_active(
    cooldown_until: datetime | None,
    current_time: datetime,
) -> bool:
    """Return True if still in cooldown period."""
    if cooldown_until is None:
        return False
    return current_time < cooldown_until


# ---------------------------------------------------------------------------
# 6. Max hold (§13.6)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MaxHoldAction:
    action: str  # "hold", "close_all", "tighten_trailing"
    reason: str


def evaluate_max_hold(
    entry_timestamp: datetime,
    current_timestamp: datetime,
    unrealized_pnl_r: float,
    max_bars: int = 48,
    bar_minutes: int = 30,
    min_profit_r: float = 0.5,
    trailing_move_r: float = 0.3,
) -> MaxHoldAction:
    """Evaluate max-hold rule.

    If holding time >= max_bars * bar_minutes:
      - unrealized_pnl_r < min_profit_r => close_all (not enough profit)
      - unrealized_pnl_r >= min_profit_r => tighten_trailing (lock profit)
    Otherwise: hold.
    """
    elapsed = current_timestamp - entry_timestamp
    max_hold_duration = timedelta(minutes=max_bars * bar_minutes)
    if elapsed < max_hold_duration:
        return MaxHoldAction(action="hold", reason="within max-hold window")
    if unrealized_pnl_r < min_profit_r:
        return MaxHoldAction(
            action="close_all",
            reason=f"max hold exceeded, PnL {unrealized_pnl_r:.2f}R < {min_profit_r}R threshold",
        )
    return MaxHoldAction(
        action="tighten_trailing",
        reason=f"max hold exceeded, PnL {unrealized_pnl_r:.2f}R >= {min_profit_r}R — tighten by {trailing_move_r}R",
    )


# ---------------------------------------------------------------------------
# 7. Lifecycle transitions (§9.3)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LifecycleTransition:
    new_state: TradeLifecycleState
    reason: str
    updates: dict


def process_lifecycle_event(
    symbol_state: SymbolState,
    global_state: GlobalState,
    event: Event,
) -> LifecycleTransition | None:
    """Process event -> lifecycle transition per §9.3. Returns None if no transition."""
    lc = symbol_state.lifecycle
    et = event.event_type

    # FLAT -> ENTRY_WORKING on ENTRY_ORDER_SUBMITTED
    if lc == TradeLifecycleState.FLAT and et == EventType.ENTRY_ORDER_SUBMITTED:
        assert isinstance(event, EntryOrderEvent)
        return LifecycleTransition(
            new_state=TradeLifecycleState.ENTRY_WORKING,
            reason="entry order submitted",
            updates={
                "side": event.side,
                "setup_version": event.setup_version,
            },
        )

    # ENTRY_WORKING: record fill but stay in ENTRY_WORKING until stop confirmed (§14.2)
    if lc == TradeLifecycleState.ENTRY_WORKING and et in (
        EventType.ENTRY_ORDER_PARTIAL_FILL,
        EventType.ENTRY_ORDER_FILLED,
    ):
        assert isinstance(event, EntryOrderEvent)
        return LifecycleTransition(
            new_state=TradeLifecycleState.ENTRY_WORKING,
            reason="entry fill received, awaiting stop order confirmation",
            updates={
                "avg_entry_price": event.avg_fill_price,
                "filled_qty": event.filled_qty,
                "entry_timestamp": event.timestamp,
            },
        )

    # ENTRY_WORKING -> OPEN_STAGE0 only after stop order confirmed (§14.2)
    if lc == TradeLifecycleState.ENTRY_WORKING and et == EventType.STOP_ORDER_ATTACHED:
        assert isinstance(event, StopOrderEvent)
        return LifecycleTransition(
            new_state=TradeLifecycleState.OPEN_STAGE0,
            reason="stop order confirmed — position protected",
            updates={
                "stop_price": event.stop_price,
            },
        )

    # OPEN_STAGE0 -> OPEN_STAGE1 on TP1_FILLED
    if lc == TradeLifecycleState.OPEN_STAGE0 and et == EventType.TP1_FILLED:
        assert isinstance(event, TpFilledEvent)
        return LifecycleTransition(
            new_state=TradeLifecycleState.OPEN_STAGE1,
            reason="TP1 filled",
            updates={
                "filled_qty": event.remaining_qty,
            },
        )

    # OPEN_STAGE1 -> OPEN_STAGE2 on TP2_FILLED
    if lc == TradeLifecycleState.OPEN_STAGE1 and et == EventType.TP2_FILLED:
        assert isinstance(event, TpFilledEvent)
        return LifecycleTransition(
            new_state=TradeLifecycleState.OPEN_STAGE2,
            reason="TP2 filled",
            updates={
                "filled_qty": event.remaining_qty,
            },
        )

    # Any OPEN_* -> EXIT_WORKING on STOP_FILLED (§9.3)
    if lc in (
        TradeLifecycleState.OPEN_STAGE0,
        TradeLifecycleState.OPEN_STAGE1,
        TradeLifecycleState.OPEN_STAGE2,
    ) and et == EventType.STOP_FILLED:
        assert isinstance(event, StopFilledEvent)
        return LifecycleTransition(
            new_state=TradeLifecycleState.EXIT_WORKING,
            reason="stop loss filled — confirming exit",
            updates={
                "filled_qty": 0.0,
                "_was_stop_loss": True,
                "_exit_timestamp": event.timestamp,
            },
        )

    # Any OPEN_* -> EXIT_WORKING on EXIT_ORDER_FILLED (trailing / manual exit) (§9.3)
    if lc in (
        TradeLifecycleState.OPEN_STAGE0,
        TradeLifecycleState.OPEN_STAGE1,
        TradeLifecycleState.OPEN_STAGE2,
    ) and et == EventType.EXIT_ORDER_FILLED:
        assert isinstance(event, ExitOrderFilledEvent)
        return LifecycleTransition(
            new_state=TradeLifecycleState.EXIT_WORKING,
            reason=f"exit filled — {event.reason}",
            updates={
                "filled_qty": 0.0,
                "_was_stop_loss": False,
                "_exit_timestamp": event.timestamp,
            },
        )

    # EXIT_WORKING -> COOLDOWN on bar close (position qty confirmed == 0)
    if lc == TradeLifecycleState.EXIT_WORKING and et in (
        EventType.BAR_CLOSED_30M,
        EventType.BAR_CLOSED_15M,
        EventType.BAR_CLOSED_5M,
        EventType.BAR_CLOSED_1H,
        EventType.BAR_CLOSED_4H,
    ):
        if symbol_state.filled_qty is not None and symbol_state.filled_qty <= 0.0:
            was_stop = getattr(symbol_state, '_was_stop_loss', False)
            exit_ts = getattr(symbol_state, '_exit_timestamp', event.timestamp)
            return LifecycleTransition(
                new_state=TradeLifecycleState.COOLDOWN,
                reason="exit confirmed — qty zero",
                updates={
                    "filled_qty": 0.0,
                    "cooldown_until": compute_cooldown_end(
                        exit_ts, was_stop_loss=was_stop,
                    ),
                },
            )

    # COOLDOWN -> FLAT (handled externally by cooldown timer check, but
    # we can also process a synthetic event or bar-close check)
    # For bar-close events during COOLDOWN, check if cooldown expired
    if lc == TradeLifecycleState.COOLDOWN and et in (
        EventType.BAR_CLOSED_30M,
        EventType.BAR_CLOSED_15M,
        EventType.BAR_CLOSED_5M,
        EventType.BAR_CLOSED_1H,
        EventType.BAR_CLOSED_4H,
    ):
        if not is_cooldown_active(symbol_state.cooldown_until, event.timestamp):
            return LifecycleTransition(
                new_state=TradeLifecycleState.FLAT,
                reason="cooldown expired",
                updates={
                    "side": Side.NONE,
                    "cooldown_until": None,
                    "avg_entry_price": None,
                    "stop_price": None,
                    "tp1_price": None,
                    "tp2_price": None,
                    "tp3_price": None,
                    "entry_timestamp": None,
                    "active_zone_id": None,
                },
            )

    # ENTRY_WORKING + TRIGGER_INVALIDATED:
    #   - No fill yet -> FLAT (cancel before fill)
    #   - Partial fill exists -> EXIT_WORKING (must exit remaining qty)
    if lc == TradeLifecycleState.ENTRY_WORKING and et == EventType.TRIGGER_INVALIDATED:
        has_partial_fill = (
            symbol_state.filled_qty is not None and symbol_state.filled_qty > 0.0
        )
        if has_partial_fill:
            return LifecycleTransition(
                new_state=TradeLifecycleState.EXIT_WORKING,
                reason="trigger invalidated with partial fill — forced exit",
                updates={
                    "_was_stop_loss": False,
                    "_exit_timestamp": event.timestamp,
                },
            )
        return LifecycleTransition(
            new_state=TradeLifecycleState.FLAT,
            reason="trigger invalidated before fill",
            updates={
                "side": Side.NONE,
            },
        )

    return None


# ---------------------------------------------------------------------------
# 8. Risk helpers
# ---------------------------------------------------------------------------

def compute_risk_pct(
    entry_price: float,
    stop_price: float,
    qty: float,
    account_balance: float,
) -> float:
    """Compute risk as a fraction of account balance."""
    if account_balance <= 0:
        return 0.0
    dollar_risk = abs(entry_price - stop_price) * qty
    return dollar_risk / account_balance


def check_risk_budget(
    global_state: GlobalState,
    candidate_risk_pct: float,
    symbol_risk_pct: float,
    max_total: float = 0.01,
    max_symbol: float = 0.005,
) -> tuple[bool, str]:
    """Check whether a new position fits the risk budget.

    Returns (allowed: bool, reason: str).
    """
    new_total = global_state.total_risk_exposure_pct + candidate_risk_pct
    if new_total > max_total:
        return (
            False,
            f"total risk {new_total:.4f} would exceed max {max_total:.4f}",
        )
    new_symbol = symbol_risk_pct + candidate_risk_pct
    if new_symbol > max_symbol:
        return (
            False,
            f"symbol risk {new_symbol:.4f} would exceed max {max_symbol:.4f}",
        )
    return (True, "within risk budget")


# ---------------------------------------------------------------------------
# 9. Invariant validation
# ---------------------------------------------------------------------------

def validate_position_invariants(
    symbol_state: SymbolState,
    trading_state: TradingState | None = None,
) -> list[str]:
    """Check ALL position invariants. Returns list of violation messages (empty = valid).

    Rules (§11):
    - Non-FLAT and non-COOLDOWN states must have stop protection
      (ENTRY_WORKING may have planned stop via filled_qty > 0 check;
       OPEN_* and EXIT_WORKING must have stop_price set)
    - OPEN_* must have stop_price set (not None)
    - Side must not be NONE when in OPEN_* states
    - Side must be NONE when FLAT
    - setup_version must be > 0 when in OPEN_* or ENTRY_WORKING
    - If trading_state provided, check no opposite direction on same symbol
    """
    violations: list[str] = []
    lc = symbol_state.lifecycle
    open_states = {
        TradeLifecycleState.OPEN_STAGE0,
        TradeLifecycleState.OPEN_STAGE1,
        TradeLifecycleState.OPEN_STAGE2,
    }

    # Non-FLAT, non-COOLDOWN states must have stop protection (§11)
    non_flat_active_states = open_states | {
        TradeLifecycleState.ENTRY_WORKING,
        TradeLifecycleState.EXIT_WORKING,
    }
    if lc in non_flat_active_states:
        # ENTRY_WORKING with partial fill needs stop_price (or at least planned)
        # OPEN_* and EXIT_WORKING strictly require stop_price
        if lc != TradeLifecycleState.ENTRY_WORKING and symbol_state.stop_price is None:
            violations.append(
                f"state {lc} must have stop_price set (stop protection required)"
            )
        if lc == TradeLifecycleState.ENTRY_WORKING:
            has_fill = (
                symbol_state.filled_qty is not None and symbol_state.filled_qty > 0.0
            )
            if has_fill and symbol_state.stop_price is None:
                violations.append(
                    "ENTRY_WORKING with partial fill must have stop_price (planned or attached)"
                )

    if lc in open_states:
        if symbol_state.side == Side.NONE:
            violations.append(
                f"OPEN state {lc} must have side != NONE"
            )
        if symbol_state.setup_version <= 0:
            violations.append(
                f"OPEN state {lc} must have setup_version > 0"
            )

    if lc == TradeLifecycleState.ENTRY_WORKING:
        if symbol_state.side == Side.NONE:
            violations.append(
                "ENTRY_WORKING must have side != NONE"
            )
        if symbol_state.setup_version <= 0:
            violations.append(
                "ENTRY_WORKING must have setup_version > 0"
            )

    if lc == TradeLifecycleState.FLAT:
        if symbol_state.side != Side.NONE:
            violations.append(
                f"FLAT state must have side == NONE, got {symbol_state.side}"
            )

    # Opposite-direction check: no two symbols in same direction conflict
    if trading_state is not None and lc in non_flat_active_states:
        my_side = symbol_state.side
        if my_side != Side.NONE:
            opposite = Side.SHORT if my_side == Side.LONG else Side.LONG
            for other_sym, other_state in trading_state.symbols.items():
                if other_sym == symbol_state.symbol:
                    continue
                if (
                    other_state.lifecycle in non_flat_active_states
                    and other_state.side == opposite
                    and _same_base_asset(symbol_state.symbol, other_sym)
                ):
                    violations.append(
                        f"opposite direction conflict: {symbol_state.symbol} "
                        f"({my_side}) vs {other_sym} ({other_state.side})"
                    )

    return violations


def _same_base_asset(symbol_a: str, symbol_b: str) -> bool:
    """Check if two symbols share the same base asset (e.g., BTCUSDT and BTCBUSD)."""
    # Simple heuristic: strip common quote suffixes and compare
    for suffix in ("USDT", "BUSD", "USD", "USDC"):
        base_a = symbol_a.removesuffix(suffix) if symbol_a.endswith(suffix) else None
        base_b = symbol_b.removesuffix(suffix) if symbol_b.endswith(suffix) else None
        if base_a and base_b and base_a == base_b:
            return True
    return symbol_a == symbol_b
