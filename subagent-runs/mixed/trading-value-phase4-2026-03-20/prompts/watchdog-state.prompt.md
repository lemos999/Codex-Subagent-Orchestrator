## Watchdog Contract
**Original goal**: StateStore (JSON 영속화 + 스냅샷 버전 + 재기동 복구) + DecisionJournal (§15 로그 27필드 + CSV/JSONL export)
**Files**: Projects/Trading Value/src/trading_value/infra/state_store.py, Projects/Trading Value/src/trading_value/infra/journal.py
**Criteria**: 1) save/load roundtrip via Pydantic model_dump_json/model_validate_json? 2) §14 recovery: FLAT+position→HALTED, OPEN+no position→HALTED, missing stop→HALTED, qty mismatch→DEGRADED? 3) JournalEntry has all §15 fields? 4) export_csv/export_jsonl implemented?
**Inspect**: state_store.py + journal.py + auto_trading_state_machine_design.md §14 + coin_strategy_spec_v2.md §15
**Return**: PASS or SHORTFALL. Confidence. Do NOT edit files.