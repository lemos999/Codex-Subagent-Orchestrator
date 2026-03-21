from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EngineState(StrEnum):
    BOOTSTRAPPING = "BOOTSTRAPPING"
    WARMUP = "WARMUP"
    READY = "READY"
    DEGRADED = "DEGRADED"
    HALTED = "HALTED"


class RiskGate(StrEnum):
    ALLOW = "ALLOW"
    REDUCE = "REDUCE"
    BLOCK = "BLOCK"


class RegimeState(StrEnum):
    HTF_BULLISH = "HTF_BULLISH"
    HTF_NEUTRAL = "HTF_NEUTRAL"
    HTF_BEARISH = "HTF_BEARISH"


class ModeState(StrEnum):
    MODE_TREND_LONG = "MODE_TREND_LONG"
    MODE_PULLBACK_LONG = "MODE_PULLBACK_LONG"
    MODE_REBOUND_SHORT = "MODE_REBOUND_SHORT"
    MODE_NO_TRADE = "MODE_NO_TRADE"


class SetupState(StrEnum):
    IDLE = "IDLE"
    WAIT_ZONE_TOUCH = "WAIT_ZONE_TOUCH"
    WAIT_TRIGGER_CONFIRM = "WAIT_TRIGGER_CONFIRM"
    ENTRY_READY = "ENTRY_READY"
    INVALIDATED = "INVALIDATED"


class TradeLifecycleState(StrEnum):
    FLAT = "FLAT"
    ENTRY_WORKING = "ENTRY_WORKING"
    OPEN_STAGE0 = "OPEN_STAGE0"
    OPEN_STAGE1 = "OPEN_STAGE1"
    OPEN_STAGE2 = "OPEN_STAGE2"
    EXIT_WORKING = "EXIT_WORKING"
    COOLDOWN = "COOLDOWN"


class Side(StrEnum):
    NONE = "NONE"
    LONG = "LONG"
    SHORT = "SHORT"


class CloudPosition(StrEnum):
    ABOVE = "above"
    IN = "in"
    BELOW = "below"


class TkState(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class ProfileBias(StrEnum):
    ABOVE_VA = "above_va"
    INSIDE_VA = "inside_va"
    BELOW_VA = "below_va"


class Timeframe(StrEnum):
    H4 = "4h"
    H1 = "1h"
    M30 = "30m"
    M15 = "15m"
    M5 = "5m"


class TimeframeSnapshot(BaseModel):
    """Per-timeframe indicator snapshot — spec v2 section 6 derived fields."""

    model_config = ConfigDict(use_enum_values=True)

    timeframe: Timeframe
    timestamp: datetime
    close: float
    tenkan: float
    kijun: float
    cloud_top: float
    cloud_bottom: float
    cloud_position: CloudPosition
    tk_state: TkState
    poc: float
    vah: float
    val: float
    profile_bias: ProfileBias
    volume: float
    volume_sma_5: float
    volume_sma_20: float
    atr: float


class Zone(BaseModel):
    """Support/resistance zone — spec v2 section 7.1."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    level: float
    low: float
    mid: float
    high: float
    timeframe: Timeframe
    source: str


class SymbolState(BaseModel):
    """Per-symbol independent state — state machine doc section 12."""

    model_config = ConfigDict(use_enum_values=True)

    symbol: str
    regime: RegimeState = RegimeState.HTF_NEUTRAL
    mode: ModeState = ModeState.MODE_NO_TRADE
    setup: SetupState = SetupState.IDLE
    lifecycle: TradeLifecycleState = TradeLifecycleState.FLAT
    side: Side = Side.NONE
    setup_version: int = 0
    active_zone_id: str | None = None
    avg_entry_price: float | None = None
    filled_qty: float | None = None
    stop_price: float | None = None
    tp1_price: float | None = None
    tp2_price: float | None = None
    tp3_price: float | None = None
    cooldown_until: datetime | None = None
    entry_timestamp: datetime | None = None
    last_transition_reason: str = ""


class GlobalState(BaseModel):
    """Account-level global state — state machine doc section 12."""

    model_config = ConfigDict(use_enum_values=True)

    engine: EngineState = EngineState.BOOTSTRAPPING
    risk_gate: RiskGate = RiskGate.BLOCK
    total_risk_exposure_pct: float = 0.0
    pending_risk_pct: float = 0.0
    consecutive_losses: int = 0


class TradingState(BaseModel):
    """Complete system state — state machine doc section 12."""

    model_config = ConfigDict(use_enum_values=True)

    global_state: GlobalState = Field(default_factory=GlobalState)
    symbols: dict[str, SymbolState] = Field(default_factory=dict)


class OHLCV(BaseModel):
    """Single candle data."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketSnapshot(BaseModel):
    """Complete market state for one symbol at evaluation time."""

    model_config = ConfigDict(use_enum_values=True)

    symbol: str
    timestamp: datetime
    timeframes: dict[Timeframe, TimeframeSnapshot]
    zones: list[Zone] = Field(default_factory=list)
