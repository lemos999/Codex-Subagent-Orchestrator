## Watchdog: optimizer.py
**Goal**: Bayesian 파라미터 최적화 — optuna TPE, 7개 파라미터 탐색, Sharpe/profit_factor/calmar 목적함수, train/test 시간순 분리, 과적합 비율 계산
**Criteria**: 1) Train/test가 시간순 분리인가 (미래 유출 없음)? 2) 0-trade 엣지 케이스 처리? 3) overfit_ratio 계산 올바른가? 4) PARAM_SPACE가 config/default.toml과 일관적인가? 5) load_backtest_data가 30m 리샘플링을 올바르게 하는가?
**Inspect**: Projects/Trading Value/src/trading_value/core/optimizer.py
**Return**: PASS or SHORTFALL. Do NOT edit.