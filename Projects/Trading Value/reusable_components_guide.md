# 재활용 가능 컴포넌트 가이드

이 문서는 `trading-quest` 프로젝트에서 가져온 전략 코드 중 Trading Value 프로젝트에 활용 가능한 컴포넌트를 정리한다. 원본 파일은 `./reusable-components/`에 보존되어 있다.

## 1. 활용 판단 기준

각 컴포넌트는 `coin_strategy_spec_v2.md`의 요구사항과 대조하여 평가했다.

- **REUSE**: 로직을 그대로 또는 최소 수정으로 사용 가능
- **PARTIAL**: 일부 함수만 발췌하여 사용 가능, 나머지는 신규 구현 필요
- **참고용**: 설계 패턴이나 구조만 참고

## 2. REUSE — 직접 활용 가능 (7개)

### 2.1 ichimoku_advanced.py

| 항목 | 내용 |
|------|------|
| TV 요구사항 | v2 §5.2 이치목 규칙, §8 타임프레임 상태 분류 |
| 제공 기능 | tenkan(9), kijun(26), senkou_a, senkou_b(52), chikou, cloud_top/bottom 계산 |
| TK 상태 | `tenkan > kijun` → bullish, `tenkan < kijun` → bearish |
| 구름 위치 | `close > cloud_top` → above, `close < cloud_bottom` → below, 나머지 → in |
| 수정 필요 | 없음. 파라미터 9/26/52가 TV 스펙과 동일 |
| 활용 위치 | `indicator-engine`, `regime-classifier` |

### 2.2 candle_pattern.py

| 항목 | 내용 |
|------|------|
| TV 요구사항 | v2 §11.2 망치형 캔들 조건, §7.2 상단 거절, §7.3 하단 이탈 실패 |
| 제공 패턴 | 망치형(Hammer), 강세장악형, 약세장악형, 도지, 샛별, 저녁별 |
| 핵심 로직 | body_ratio, upper_shadow, lower_shadow 계산. 추세 문맥(SMA 20) 포함 |
| 수정 필요 | 없음. v2 §11.2의 망치형 조건(몸통 35% 이하, 아래꼬리 2배 이상)과 호환 |
| 활용 위치 | `setup-tracker` (PULLBACK_LONG 트리거 확인) |

### 2.3 atr_breakout.py

| 항목 | 내용 |
|------|------|
| TV 요구사항 | v2 §5.4 ATR 규칙 (14 기간), §7.1 존 폭 계산, §11 손절 계산 |
| 제공 기능 | ATR 계산 (True Range → EMA), 돌파 레벨 (시가 ± ATR × k) |
| 수정 필요 | `atr_period` 기본값 20 → 14로 변경 |
| 활용 위치 | `indicator-engine` (ATR_5m ~ ATR_4h 각각 계산) |

### 2.4 multi_tf.py

| 항목 | 내용 |
|------|------|
| TV 요구사항 | v2 §3.1 타임프레임 구조 (4h/1h/30m/15m/5m) |
| 제공 기능 | `on_candle_mtf(candles: dict[str, DataFrame])` — 타임프레임별 DataFrame 수신 패턴 |
| 핵심 가치 | 멀티 타임프레임 병렬 처리 스켈레톤. 5층 상태머신의 기본 구조 |
| 수정 필요 | 현재 daily+hourly 2층 → 5층으로 확장 |
| 활용 위치 | `regime-classifier`, `mode-selector` 전체 구조 |

### 2.5 triple_screen.py

| 항목 | 내용 |
|------|------|
| TV 요구사항 | v2 §10 허용 전략 매트릭스 (상위→중위→하위 확인 순서) |
| 제공 기능 | 3단계 확인: Screen 1 (추세 SMA), Screen 2 (RSI+Stochastic), Screen 3 (돌파 진입) |
| 핵심 가치 | "상위 추세 확인 → 중간 오실레이터 → 하위 트리거" 패턴이 TV의 4h→1h→30m→15m→5m과 구조적으로 동일 |
| 수정 필요 | SMA 기반 추세 → 이치목 기반 상태 분류로 교체 |
| 활용 위치 | `mode-selector` 설계 참고 |

### 2.6 channel.py

| 항목 | 내용 |
|------|------|
| TV 요구사항 | v2 §7.1 지지/저항 존 |
| 제공 기능 | Keltner Channel: EMA(20) ± ATR(10) × multiplier. 상/중/하단 밴드 |
| 핵심 가치 | 동적 지지/저항 존 계산. 평균회귀 바운스 감지 |
| 수정 필요 | 파라미터 조정 (EMA/ATR 기간) |
| 활용 위치 | `setup-tracker` (존 생성 보조) |

### 2.7 pivot_point.py

| 항목 | 내용 |
|------|------|
| TV 요구사항 | v2 §7.1 지지/저항 존, §11 감시 존 |
| 제공 기능 | 피봇 = (H+L+C)/3, S1/R1/S2/R2 계산. tolerance 기반 근접 판정 |
| 핵심 가치 | 정적 지지/저항 레벨 생성. 존 후보군 확장 |
| 수정 필요 | 없음 |
| 활용 위치 | `setup-tracker` (감시 존 후보 생성 보조) |

## 3. PARTIAL — 일부만 활용 가능 (2개)

### 3.1 volume_profile.py

| 항목 | 내용 |
|------|------|
| TV 요구사항 | v2 §5.3 고정 볼륨 프로파일 (POC, VAH, VAL) |
| 제공 기능 | OBV 추세 감지, 거래량 급증 감지 (2x 평균), VWMA 계산 |
| 부족한 부분 | **POC/VAH/VAL 없음** — 가격 분포 히스토그램 기반 계산이 필요하나 구현되어 있지 않음 |
| 활용 가능 | OBV 추세 + 거래량 급증 로직 → v2 §11 진입 조건의 거래량 필터에 활용 |
| 신규 구현 필요 | 고정 윈도우(96/120/90봉) 기반 POC/VAH/VAL 계산 모듈 |

### 3.2 supertrend_strategy.py

| 항목 | 내용 |
|------|------|
| TV 요구사항 | v2 §11 트레일링 스탑 |
| 제공 기능 | Supertrend 방향 추적 (bullish/bearish 전환) |
| 부족한 부분 | 실제 트레일링 스탑 (동적 손절 이동) 로직 없음. 방향 전환만 감지 |
| 활용 가능 | 방향 추적 패턴 → 트레일링 참고용 |
| 신규 구현 필요 | v2 §11.1/11.2/11.3 각 트레일링 규칙 전체 |

## 4. 활용하지 않는 것 (20개)

bollinger, donchian, donchian_larry, dqn, dual_momentum, lstm, ma_crossover, macd, macd_divergence, mean_reversion, momentum, rsi, rsi_divergence, stochastic, trendline, volume_breakout, vwap 등.

이유: Trading Value의 3개 전략(TREND_LONG, PULLBACK_LONG, REBOUND_SHORT)은 이치목 + 볼륨프로파일 + ATR 기반이며, 위 전략들의 지표(MACD, RSI, Bollinger 등)는 사용하지 않는다.

## 5. 구현 시 권장 활용 순서

| 단계 | 구현 대상 | 재활용 소스 | 신규 구현 |
|------|----------|-----------|----------|
| 1 | 지표 엔진 | ichimoku_advanced + atr_breakout | 스윙 감지 (§5.5 프랙탈) |
| 2 | 캔들 패턴 | candle_pattern | §7.2 상단 거절, §7.3 하단 이탈 실패 |
| 3 | 존 생성기 | channel + pivot_point | 볼륨프로파일 POC/VAH/VAL |
| 4 | 상태 판정기 | multi_tf + triple_screen 패턴 | RegimeState/ModeState 판정 로직 |
| 5 | 거래량 필터 | volume_profile (OBV/VWMA) | 거래량 조건 검증 |

## 6. 파일 위치

원본 소스: `./reusable-components/`

이 파일들은 `trading-quest`에서 복사한 원본이다. Trading Value 구현 시 필요한 함수만 발췌하여 새 모듈에 통합한다. 원본을 직접 수정하지 않는다.
