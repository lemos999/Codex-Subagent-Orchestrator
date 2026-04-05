# Trading Value - Session Resume Guide

> 새 세션에서 이 파일과 `limits-history.md`를 반드시 읽는다.

## 미션
**최고 수익률 달성 (상한 없음).** 한계를 두지 않는다.

## 정신
`limits-history.md` 참조. 7번의 한계를 돌파해왔다. 다음 한계도 넘는다.

## 현재 상태: Conviction Engine

이진법적 진입/미진입을 폐기. 확신도(0~100%) 기반 연속 포지셔닝.

```
5개 시그널 → 확신도 → 포지션 크기
추세(MA20/50/200) + RSI + 볼륨 + 모멘텀 + 변동성
```

### 자산 & 전략

| 자산 | 타입 | 최대 레버리지 | 데이터 |
|------|------|-------------|--------|
| ETH | Crypto 15m | 2.0x | ccxt Binance |
| BTC | Crypto 15m | 1.5x | ccxt Binance |
| NVDA | Stock 1d | 3.0x | yfinance |
| AMZN | Stock 1d | 2.0x | yfinance |

### 대시보드
http://localhost:8895

### 핵심 파일

| 파일 | 역할 |
|------|------|
| `scripts/conviction_engine.py` | 통합 실행 엔진 (4자산, 대시보드) |
| `scripts/start_paper.bat` | Windows 시작 프로그램 |
| `limits-history.md` | 한계 돌파 기록 (필독) |
| `archive/rl_learning_log.md` | 전체 학습 이력 |
| `data/conviction_*.json` | 자산별 상태 파일 |

### 백테스트 도구

| 파일 | 역할 |
|------|------|
| `scripts/strategy_hybrid.py` | ETH 하이브리드 백테스트 |
| `scripts/strategy_cmaes.py` | CMA-ES 파라미터 최적화 |
| `scripts/optimize_v3.py` | 초단순 2-param 그리드 서치 |
| `scripts/pairs_btc_eth.py` | BTC/ETH 페어 트레이딩 |
| `scripts/retrain_xgb.py` | XGBoost 재학습 |

### 실행

```bash
cd "Projects/Trading Value"
py -3.12 -u scripts/conviction_engine.py
```

### 환경
- Python 3.12
- ccxt, yfinance, xgboost, cma, pandas, numpy, scikit-learn
