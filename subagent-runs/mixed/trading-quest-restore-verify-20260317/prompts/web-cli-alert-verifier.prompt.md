# Verify restored web/ + cli/ + agent/ + alert/ + live/ modules

Working directory: C:\Users\haj\projects\subagent-orchestrator\trading-quest

Run these verification steps:

1. CLI help: py -m tq --help (should show data, quest, strategy, serve, live commands)
2. Quest subcommands: py -m tq quest --help (should show start, run, status, compare, evolve, run-full, backtest, optimize)
3. Live subcommands: py -m tq live --help (should show paper, binance)
4. Read tq/web/routes.py — verify API endpoints exist: /api/quests, /api/quest/<id>, /api/quest/<id>/run, /api/quest/<id>/trades, /api/data/<symbol>, /api/data/<symbol>/indicators, /api/compare, /api/strategies
5. Read tq/web/templates/ — verify index.html, quest.html, leaderboard.html exist and have proper HTML structure
6. Read tq/alert/telegram.py — verify TelegramAlert class with send_trade_alert, send_daily_summary methods
7. Read tq/alert/manager.py — verify AlertManager class
8. Read tq/live/broker_base.py — verify LiveBroker ABC
9. Read tq/live/paper_broker.py — verify PaperBroker class
10. Read tq/live/runner.py — verify LiveRunner class
11. Read tq/agent/interface.py — verify AgentInterface with step() method
12. Run: py -m pytest tests/test_alert.py tests/test_live.py -v --tb=short 2>&1 | tail -20

Report PASS/FAIL for each step.
Print issues found:
=== VERIFICATION REPORT ===
## Critical Issues
## Medium Issues  
## Minor Issues
=== END REPORT ===
