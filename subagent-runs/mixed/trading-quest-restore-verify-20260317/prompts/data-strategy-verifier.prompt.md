# Verify restored data/ + strategy/ modules

Working directory: C:\Users\haj\projects\subagent-orchestrator\trading-quest

Run these commands and report results:

1. Data fetch US: py -m tq data fetch --market US --symbols "TSLA,META" 
2. Data fetch CRYPTO: py -m tq data fetch --market CRYPTO --symbols "BTCUSDT,ETHUSDT"
3. Data fetch KRX: py -m tq data fetch --market KRX --symbols "005930.KS"
4. Data status: py -m tq data status
5. Data timeframe test: py -m tq data timeframe --market US --symbol AAPL --interval 15m --days 3
6. Strategy list: py -m tq strategy list
7. Strategy create: py -m tq strategy create test_verify_strategy
8. Read tq/strategy/indicator.py and verify ichimoku, supertrend, stochastic, donchian_channel functions exist
9. Read tq/strategy/builtin/ and count .py files (should be 13+)
10. Run tests: py -m pytest tests/test_strategy.py tests/test_data.py -v --tb=short 2>&1 | tail -30

For each test, report PASS or FAIL with details.
Print a bug report at the end:
=== BUG REPORT ===
- [severity] description
=== END REPORT ===
