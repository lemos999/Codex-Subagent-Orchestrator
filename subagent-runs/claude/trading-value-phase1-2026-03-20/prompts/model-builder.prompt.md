# Model-Builder Prompt

Create Pydantic v2 state models in `src/trading_value/core/models.py`:
- 11 StrEnum types: EngineState, RiskGate, RegimeState, ModeState, SetupState, TradeLifecycleState, Side, CloudPosition, TkState, ProfileBias, Timeframe
- 7 BaseModel classes: TimeframeSnapshot (17 fields), Zone, SymbolState (per §12), GlobalState (per §12), TradingState, OHLCV, MarketSnapshot
- All from auto_trading_state_machine_design.md §12 + coin_strategy_spec_v2.md §6
