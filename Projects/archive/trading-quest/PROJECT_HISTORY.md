# Trading Quest — 프로젝트 역사

## 개요

Trading Quest는 AI 기반 트레이딩 전략 자동 최적화 시스템이었다. 웹 대시보드를 통해 다양한 전략과 파라미터 조합을 자동 탐색하며, 점수·승률·수익률 기준으로 최적 조합을 찾는 재귀 개선 시스템을 구축했다.

## 기간

2025년 말 ~ 2026년 3월

## 핵심 구현물

### 웹 대시보드
- Flask 기반 웹 서버 (`tq/web/`)
- 임무 수행 페이지 — 실시간 SSE 스트리밍으로 최적화 진행 시각화
- 점수 추이 차트, 전략별 비교 막대, 최고 점수 추적
- 종목 자동완성, 거래 유형 선택 (일봉/분봉)

### 전략 프레임워크
- 24개 내장 전략 (MACD, RSI, Bollinger, Ichimoku, Candle Pattern 등)
- `BaseStrategy` 추상 클래스 + 전략 레지스트리
- 멀티 타임프레임 지원 (`on_candle_mtf`)
- 자동 파라미터 변이 생성 + 최적화

### 미션 시스템
- Phase 1 (스캔): 전략별 기본/최적 파라미터로 백테스트
- Phase 2 (최적화): 상위 전략의 파라미터 근처에서 hill climbing
- VV 시스템: 2개 이상 목표 달성 전략 우선 최적화
- 전략별 독립 best 추적 + 세션 간 학습

### AI 학습 메모리
- `TradingMemory` 클래스 — 인메모리 캐시 + 배치 디스크 쓰기
- best-params, tried-params, mistakes, insights, history 영구 저장
- 중복 방지, 자동 compact (500건/200건 상한)
- 승률 가중 점수 + 손익비(RR) 반영

### 시뮬레이션 엔진
- `QuestEngine` — 일별/분봉 캔들 시뮬레이션
- `SimBroker` — 주문 체결, 수수료, 슬리피지
- `VirtualPortfolio` — 롱/숏 포지션 관리
- 자동 포지션 사이징 (자금의 30%)

### 데이터 파이프라인
- Binance REST API (코인), yfinance (주식) 데이터 수집
- SQLite 캐시 (일봉/분봉)
- 멀티 타임프레임 리샘플링 (1m→5m→15m→30m→1h→4h)

## 주요 기술적 도전과 해결

| 문제 | 해결 |
|------|------|
| 같은 전략/파라미터 반복 시도 | has_tried() + 캐시 결과 재사용 |
| 분봉 pd.concat O(n²) | iloc 슬라이싱으로 O(1) |
| 공매도 PnL 반전 | CompletedTrade.is_short 플래그 |
| BTC 가격으로 qty=1 매수 불가 | 자동 포지션 사이징 (자금 30%) |
| 메모리 파일 무한 성장 | compact() + flush 배치 |
| 0-trade 결과가 mistake로 기록 | trades > 0 가드 |

## 후속 프로젝트

이 프로젝트의 경험과 일부 코드는 **Trading Value** 프로젝트로 계승되었다.

Trading Value는 파라미터 무작위 탐색 대신 문서 기반 결정론적 규칙(이치목 + 볼륨프로파일 + 멀티 타임프레임 상태머신)을 사용하는 방향으로 전환했다.

재활용된 컴포넌트: ichimoku_advanced, candle_pattern, atr_breakout, multi_tf, triple_screen, channel, pivot_point 등 7개 전략 모듈.

## 폴더 구조 (아카이브 시점)

```
trading-quest/
├── tq/
│   ├── web/          — Flask 웹 서버 + 템플릿
│   ├── quest/        — 퀘스트 엔진, 점수, 페이즈
│   ├── strategy/     — 24개 전략 + 레지스트리
│   ├── sim/          — 브로커, 포트폴리오, 주문
│   ├── data/         — 데이터 캐시, 페처, 스키마
│   ├── journal/      — AI 학습 메모리
│   └── config.py     — 설정
├── data/             — SQLite 캐시
└── .tq-journal/      — 학습 메모리 파일
```
