## Watchdog: rl_env.py
**Goal**: Gymnasium RL 환경 — 25-dim observation, Discrete(5) action, 보상 함수 (실현PnL + holding cost + drawdown penalty), 사전계산 스냅샷, SB3 호환
**Criteria**: 1) observation_space/action_space 정의 올바른가? 2) 보상 함수에 미실현 PnL 보상이 없는가 (holding forever 방지)? 3) 커미션이 보상에 반영되는가? 4) 에피소드 종료 조건이 명확한가? 5) step()이 gymnasium API (obs, reward, terminated, truncated, info) 반환하는가? 6) 상태 정규화가 적절한가? 7) random_start로 에피소드 다양성 보장?
**Inspect**: Projects/Trading Value/src/trading_value/adapters/rl_env.py
**Return**: PASS or SHORTFALL. Do NOT edit.