# Event-Builder Prompt

Create event types in `src/trading_value/core/events.py`:
- EventType StrEnum with all 23 events from auto_trading_state_machine_design.md §7
- Base Event class with event_id (UUID), event_type, timestamp, symbol
- 10 specialized models: BarClosedEvent, ZoneTouchedEvent, TriggerEvent, EntryOrderEvent, StopOrderEvent, TpFilledEvent, StopFilledEvent, ExitOrderFilledEvent, EngineEvent, RiskEvent
- EVENT_TYPE_MAP covering all 23 EventType values
