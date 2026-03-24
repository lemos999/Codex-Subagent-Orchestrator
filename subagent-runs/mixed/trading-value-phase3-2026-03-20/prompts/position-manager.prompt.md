You operate under the shared contract in AGENTS.md at the workspace root.

## Contract

**Engine**: codex
**Task**: Create the position manager for the Trading Value automated trading system.

**Inspect first**:
- `Projects/Trading Value/auto_trading_state_machine_design.md` (§5.6 TradeLifecycleState, §9.3 TradeLifecycleState transitions, §11 invariants, §12 data model)
- `Projects/Trading Value/coin_strategy_spec_v2.md` (§11 strategy details for trailing, §13 risk management, §14 order execution)
- `Projects/Trading Value/src/trading_value/core/models.py` (TradeLifecycleState, SymbolState, GlobalState, TradingState, Side, ModeState)
- `Projects/Trading Value/src/trading_value/core/events.py` (order events, tp events, stop events)
- `Projects/Trading Value/config/default.toml` (risk, cooldown, max_hold, entry_split, exit_split params)

**Writable scope**:
- `Projects/Trading Value/src/trading_value/core/position.py` (create)

**Requirements**:

Create pure functions and dataclasses for position lifecycle management. No side effects, no exchange calls.

### 1. Position sizing (§13.2)

```python
def compute_position_size(
    account_balance: float,
    risk_pct: float,
    entry_price: float,
    stop_price: float,
    min_qty: float = 0.001,
) -> float:
    """Spec v2 §13.2: TargetQty = (Balance * Risk%) / |Entry - Stop|

    - account_balance: realized balance (no unrealized PnL)
    - risk_pct: 0.0035 default, 0.005 max, 0.0025 counter-trend
    - Round down to min_qty increments
    """
```

### 2. Split entry quantities (§11 entry price sections)

```python
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
    """Split total quantity into 3 entry stages. Round down each to min_qty."""
```

### 3. Exit plan (§11 청산 sections)

```python
@dataclass(frozen=True)
class ExitPlan:
    tp1_qty: float   # 30% of total
    tp2_qty: float   # 30% of total
    trailing_qty: float  # 40% of total

def compute_exit_plan(
    total_qty: float,
    tp1_pct: float = 0.30,
    tp2_pct: float = 0.30,
    trailing_pct: float = 0.40,
    min_qty: float = 0.001,
) -> ExitPlan:
    """Split total quantity into exit stages."""
```

### 4. Trailing stop evaluation (§11 trailing sections per strategy)

```python
@dataclass(frozen=True)
class TrailingAction:
    action: str  # "hold", "reduce_half", "reduce_30pct", "close_all"
    reason: str

def evaluate_trailing_trend_long(
    close_5m: float, kijun_5m: float,
    close_15m: float, tenkan_15m: float,
) -> TrailingAction:
    """§11.1 TREND_LONG trailing:
    - 5m close < 5m Kijun → reduce half of remaining
    - 15m close < 15m Tenkan → close all remaining
    """

def evaluate_trailing_pullback_long(
    close_15m: float, kijun_15m: float,
    close_30m: float, zone_mid: float,
) -> TrailingAction:
    """§11.2 PULLBACK_LONG trailing:
    - 15m close < 15m Kijun → reduce half
    - 30m close < zone mid → close all
    """

def evaluate_trailing_rebound_short(
    close_5m: float, kijun_5m: float,
    close_15m: float, tenkan_15m: float, kijun_15m: float,
) -> TrailingAction:
    """§11.3 REBOUND_SHORT trailing:
    - 5m close > 5m Kijun → reduce 30% of remaining
    - 15m close > 15m Tenkan → reduce half of remaining
    - 15m close > 15m Kijun → close all
    """
```

### 5. Cooldown check (§13.5)

```python
def compute_cooldown_end(
    exit_timestamp: datetime,
    was_stop_loss: bool,
    normal_bars: int = 2,
    stop_loss_bars: int = 4,
    bar_duration_minutes: int = 30,
) -> datetime:
    """§13.5: Cooldown = normal 2 bars (1h) or stop-loss 4 bars (2h)."""

def is_cooldown_active(cooldown_until: datetime | None, current_time: datetime) -> bool:
    """Check if cooldown period has elapsed."""
```

### 6. Max hold time check (§13.6)

```python
@dataclass(frozen=True)
class MaxHoldAction:
    action: str  # "hold", "close_all", "tighten_trailing"
    reason: str

def evaluate_max_hold(
    entry_timestamp: datetime,
    current_timestamp: datetime,
    unrealized_pnl_r: float,
    max_bars: int = 48,
    bar_duration_minutes: int = 30,
    min_profit_r: float = 0.5,
    trailing_move_r: float = 0.3,
) -> MaxHoldAction:
    """§13.6: After 48 30m bars (24h):
    - If unrealized PnL < 0.5R → close all
    - If unrealized PnL >= 0.5R → tighten trailing (move stop to entry + 0.3R)
    """
```

### 7. TradeLifecycleState transition logic (§9.3)

```python
@dataclass(frozen=True)
class LifecycleTransition:
    new_state: TradeLifecycleState
    reason: str
    updates: dict  # fields to update on SymbolState

def process_lifecycle_event(
    symbol_state: SymbolState,
    global_state: GlobalState,
    event: Event,
) -> LifecycleTransition | None:
    """Process an event and return the lifecycle transition if applicable.

    Transitions per §9.3:
    - FLAT → ENTRY_WORKING: when ENTRY_READY + engine READY + risk allows + no opposite position
    - ENTRY_WORKING → OPEN_STAGE0: first fill + stop attached
    - ENTRY_WORKING → FLAT: order cancelled/expired with 0 fills
    - ENTRY_WORKING → EXIT_WORKING: partial fill + setup invalidated or stop attach failed
    - OPEN_STAGE0 → OPEN_STAGE1: TP1 filled
    - OPEN_STAGE1 → OPEN_STAGE2: TP2 filled
    - OPEN_STAGE0/1/2 → EXIT_WORKING: stop filled, invalidation, manual, halted
    - EXIT_WORKING → COOLDOWN: position qty 0, orders cleaned
    - COOLDOWN → FLAT: cooldown time elapsed

    Returns None if no transition applies.
    """
```

### 8. Risk exposure tracking helpers

```python
def compute_risk_pct(entry_price: float, stop_price: float, qty: float, account_balance: float) -> float:
    """Compute risk as percentage of account balance."""

def check_risk_budget(
    global_state: GlobalState,
    candidate_risk_pct: float,
    symbol_risk_pct: float,
    max_total_risk: float = 0.01,
    max_symbol_risk: float = 0.005,
) -> tuple[bool, str]:
    """Check if new position fits within risk budget. Returns (allowed, reason)."""
```

### 9. Invariant enforcement

```python
def validate_position_invariants(symbol_state: SymbolState) -> list[str]:
    """Check all position invariants from §11. Returns list of violation descriptions.

    Invariants:
    - OPEN states must have stop_price
    - ENTRY_WORKING must have stop_price planned (can be None until STOP_ORDER_ATTACHED)
    - Side must match lifecycle (FLAT → NONE, OPEN → LONG or SHORT)
    - No duplicate setup_version while in non-FLAT state
    """
```

### Important:
- `from __future__ import annotations`
- Import from `.models` and `.events`
- Use `from dataclasses import dataclass`
- All functions are pure — stateless, no side effects
- Use `from datetime import datetime, timedelta`
- Round quantities down to min_qty using `math.floor(qty / min_qty) * min_qty`
- Do NOT import or depend on indicators.py, regime.py, or mode.py

**Validation**:
1. File exists and is non-empty
2. All 9 function groups implemented
3. Valid Python syntax
4. Imports resolve

**Return**:
- Files created
- Function count
- Validation results

**Stop condition**: Create only position.py. Do not create setup.py, backtest.py, or tests.
