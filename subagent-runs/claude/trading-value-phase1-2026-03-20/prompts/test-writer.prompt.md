# Test-Writer Prompt

Write tests in `tests/`:
- test_models.py: serialization roundtrip for all StrEnums and BaseModels
- test_events.py: EventType cardinality, event creation, EVENT_TYPE_MAP completeness
- test_invariants.py: §11 invariants — stop_price required, no opposite direction, mode bar-close only, engine-ready gate, duplicate setup_version, reboot mismatch, risk_gate block
- 7 pure helper functions (check_invariant_*) for reuse by engine layer
