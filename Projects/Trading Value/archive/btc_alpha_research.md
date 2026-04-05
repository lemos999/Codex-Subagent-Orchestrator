# BTC 수익 전략 돌파구 -- 새로운 알파 소스 탐색

> 작성일: 2026-03-31
> 기반: rl_learning_log.md 전체 히스토리 + 멀티코인 검증 결과

---

## 1. 왜 ETH는 되고 BTC는 안 되는가?

### 1.1 시장 미시구조 차이

| 특성 | BTC | ETH |
|------|-----|-----|
| 일중 변동성 (ATR/Price) | 1.5~2.5% | 2.5~4.0% |
| 추세 지속성 (Hurst) | ~0.48 (약 랜덤워크) | ~0.53 (약 추세) |
| 유동성 깊이 | 매우 깊음 | 상대적 얕음 |
| 기관 참여도 | ETF, CME 선물, 국가 보유 | DeFi 중심 |
| 뉴스 반응 속도 | 즉각 (HFT/봇) | 지연 (BTC 후행) |
| MA Cross 수익성 | OOS -28.1% | OOS +42.4% |

**핵심 원인 3가지**:

1. **BTC의 효율적 시장**: BTC는 세계에서 가장 많은 봇과 기관이 거래. 15분봉 기술적 신호에 이미 가격이 반영됨. ETH는 상대적으로 비효율적이라 MA Cross 같은 단순 추세추종이 작동.

2. **변동성 구조 차이**: ETH의 높은 변동성 = 같은 ATR 배수의 SL/TP가 더 넓은 가격 범위를 커버. 수수료 대비 수익 폭이 커서 양의 기대값 확보가 쉬움. BTC는 수수료 비율 대비 수익 폭이 좁음.

3. **추세 지속성**: ETH의 Hurst ~0.53은 약하지만 추세추종에 유리. BTC ~0.48은 약한 평균회귀 성향으로, MA Cross류 전략에 불리.

### 1.2 ETH/BTC 상관관계 활용 가능성

- BTC-ETH 상관계수: 일봉 ~0.85, 15분봉 ~0.65
- **Lead-Lag 관계**: BTC가 ETH를 ~2~5분 선행하는 경향. 이를 직접 BTC 매매에 쓰기는 어려움 (BTC 자체가 선행이므로).
- **ETH/BTC 비율 스프레드**: 평균회귀 가능성 있음 (아래 Pairs Trading에서 상세)

---

## 2. BTC만의 알파 소스

### 2.1 펀딩레이트 (Funding Rate)

**원리**: 무기한 선물의 롱/숏 불균형을 8시간마다 정산. 극단적 펀딩 = 과열/과냉 신호.

**접근성**: 무료, ccxt로 즉시 접근

**코드 스니펫**:
```python
import ccxt

exchange = ccxt.binance({'options': {'defaultType': 'future'}})

# 현재 펀딩레이트
funding = exchange.fetch_funding_rate('BTC/USDT:USDT')
current_rate = funding['fundingRate']  # ex: 0.0001 = 0.01%

# 과거 펀딩레이트 이력
history = exchange.fetch_funding_rate_history('BTC/USDT:USDT', limit=500)
# [{'timestamp': ..., 'fundingRate': 0.0003, ...}, ...]
```

**전략 아이디어**:
- 펀딩 > 0.05% (연 182%): 롱 과열 -> 숏 기회 (또는 중립)
- 펀딩 < -0.03% (연 -109%): 숏 과열 -> 롱 기회
- 펀딩 수집만으로도 보유 수익 (positive carry)

**예상 효과**: 단독으로는 약한 신호 (일 3회만 업데이트). CMA-ES 진입 필터로 추가 시 10~15%p DD 감소 기대.

**구현 난이도**: 낮음 (2~4시간). ccxt API 호출 + 기존 전략에 필터 추가.

---

### 2.2 미결제약정 변화율 (Open Interest Change)

**원리**: OI 급증 + 가격 상승 = 강한 추세. OI 급감 + 가격 상승 = 숏 청산 랠리 (취약). OI 급감 + 가격 하락 = 롱 청산 캐스케이드.

**접근성**: 무료, ccxt로 접근 가능

**코드 스니펫**:
```python
import ccxt

exchange = ccxt.binance({'options': {'defaultType': 'future'}})

# 현재 미결제약정
oi = exchange.fetch_open_interest('BTC/USDT:USDT')
oi_value = oi['openInterestValue']  # USD 기준

# OI 이력 (5분 간격)
oi_history = exchange.fetch_open_interest_history(
    'BTC/USDT:USDT',
    timeframe='5m',
    limit=500
)
# [{'timestamp': ..., 'openInterestAmount': 45000, ...}, ...]

# OI 변화율 계산
import pandas as pd
df_oi = pd.DataFrame(oi_history)
df_oi['oi_change_pct'] = df_oi['openInterestAmount'].pct_change(12)  # 1시간 변화율
```

**전략 아이디어**:
- OI 1시간 변화율 > +5% + 가격 상승 -> 추세 지속 기대, 롱 진입 확신 강화
- OI 급감 > -5% + 가격 급등 -> 숏 청산 랠리, 추격 매수 자제
- OI + 펀딩레이트 조합: 두 신호가 일치할 때만 진입

**예상 효과**: CMA-ES 필터로 추가 시 승률 3~5%p 개선 기대. 단독 전략보다 필터로 더 효과적.

**구현 난이도**: 낮음 (3~5시간). 과거 데이터 축적이 필요 (자체 DB 저장).

---

### 2.3 BTC 도미넌스 (BTC.D)

**원리**: BTC.D 상승 = 자금이 알트에서 BTC로 이동 (Risk-off). BTC.D 하락 = BTC에서 알트로 이동 (Risk-on).

**접근성**: 직접 계산 가능 (BTC marketcap / total marketcap). CoinGecko 무료 API (분당 30회)

**코드 스니펫**:
```python
import requests

# CoinGecko 무료 API
url = "https://api.coingecko.com/api/v3/global"
data = requests.get(url).json()['data']
btc_dominance = data['market_cap_percentage']['btc']  # ex: 54.2

# 또는 ccxt로 BTC + 주요 코인 시가총액 직접 계산
# BTCUSDT ticker에서 price * circulating_supply
```

**전략 아이디어**:
- BTC.D 상승 추세 + BTC 가격 상승 = 강한 롱 신호
- BTC.D 하락 + BTC 가격 상승 = 약한 추세 (알트 시즌 임박, BTC 약세 전환 가능)

**예상 효과**: 매크로 필터로 사용 시 역추세 진입 방지. 효과 미미할 가능성 높음 (일봉 단위 변화가 느림).

**구현 난이도**: 중간 (1일). API 호출 + 15분봉과 시간 매칭이 번거로움.

---

### 2.4 거래소 유입/유출 (온체인)

**원리**: 대량 거래소 유입 = 매도 압력 증가. 대량 유출 = 장기 보유 의향.

**접근 가능한 무료 API**:
- **CryptoQuant Free Tier**: 일 10회 호출 (너무 적음)
- **Glassnode Free**: 주간 데이터만 (실시간 불가)
- **Blockchain.com API**: BTC 트랜잭션 조회 가능하나 거래소 주소 식별 필요
- **IntoTheBlock Free**: 제한적

**결론**: 무료 실시간 온체인 데이터는 사실상 없음. 유료 서비스(CryptoQuant Pro $49/월, Glassnode Advanced $29/월)가 필요.

**구현 난이도**: 높음 (유료 구독 필요 + 1~2일 구현). 비용 대비 효과 불확실.

---

### 2.5 CME 선물 갭 (주말 갭 전략)

**원리**: CME BTC 선물은 주말 휴장. 금요일 종가 vs 월요일 시가의 갭이 80%+ 확률로 메워짐.

**접근성**: 무료 (Binance 현물로 갭 추적 가능, CME 데이터 불필요)

**코드 스니펫**:
```python
import ccxt
import pandas as pd

exchange = ccxt.binance()

# 주간 데이터로 금요일 종가 vs 월요일 시가 계산
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', limit=365)
df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
df['dt'] = pd.to_datetime(df['ts'], unit='ms')
df['dow'] = df['dt'].dt.dayofweek  # 0=Mon

# CME 갭 = 월요일 시가 - 금요일 종가
fridays = df[df['dow'] == 4]['c'].values
mondays = df[df['dow'] == 0]['o'].values
min_len = min(len(fridays), len(mondays))
gaps = (mondays[:min_len] - fridays[:min_len]) / fridays[:min_len] * 100
# gap > 0: 주말 상승 -> 갭 메우기 = 숏
# gap < 0: 주말 하락 -> 갭 메우기 = 롱
```

**전략 아이디어**:
- 월요일 06:00 UTC (CME 개장): 갭 방향 반대로 진입
- 갭 > 1%일 때만 진입 (노이즈 필터)
- TP: 금요일 종가 레벨, SL: 갭 방향 2% 추가 확대

**예상 효과**: 주 1회 거래, 80% 갭 메우기 확률이 실증됨. 연 40~50회 거래, 승률 60%+ 기대. 하지만 수익 폭이 작음 (평균 갭 1~2%).

**구현 난이도**: 낮음 (3~4시간). 단순 규칙 기반.

---

### 2.6 김치 프리미엄

**원리**: 한국 거래소(업비트)와 Binance 사이 가격 괴리. 프리미엄 > 3% = 한국 과열, 하락 선행 신호.

**접근성**: 무료 (업비트 API + 환율)

**코드 스니펫**:
```python
import requests

# 업비트 BTC 가격 (KRW)
upbit_resp = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC")
btc_krw = upbit_resp.json()[0]['trade_price']  # ex: 130,000,000 KRW

# 환율 (한국은행 or 대략적)
usd_krw = 1380  # 실시간은 exchangerate-api.com (무료 월 1500회)

# Binance BTC 가격
import ccxt
binance = ccxt.binance()
ticker = binance.fetch_ticker('BTC/USDT')
btc_usd = ticker['last']

# 김치 프리미엄
kimchi = (btc_krw / usd_krw / btc_usd - 1) * 100
# ex: 2.5% -> 소폭 과열
# ex: 5%+ -> 강한 과열 신호
```

**전략 아이디어**:
- 프리미엄 > 5%: 숏 또는 롱 진입 금지
- 프리미엄 < -2%: 한국 저평가 = 롱 기회
- 매크로 필터로만 사용 (일 1~2회 체크)

**예상 효과**: 극단적 과열/과냉 신호로만 유효. 월 1~2번 발생. 단독 전략 불가, 필터로만 사용.

**구현 난이도**: 낮음 (2~3시간).

---

## 3. BTC에 더 적합한 전략 구조

### 3.1 BTC/ETH Pairs Trading (스프레드 트레이딩)

**원리**: BTC와 ETH는 높은 상관관계. 비율(ETH/BTC)이 평균에서 이탈하면 회귀를 기대하고 스프레드 매매.

**왜 BTC에 적합한가**: BTC 방향을 맞출 필요 없음. 두 자산 간 상대 가치만 판단. 시장 중립(delta-neutral)이므로 시장 방향 리스크 제거.

**코드 스니펫**:
```python
import ccxt
import numpy as np

exchange = ccxt.binance({'options': {'defaultType': 'future'}})

# 두 자산의 15분봉 가져오기
btc = exchange.fetch_ohlcv('BTC/USDT:USDT', '15m', limit=200)
eth = exchange.fetch_ohlcv('ETH/USDT:USDT', '15m', limit=200)

btc_close = np.array([c[4] for c in btc])
eth_close = np.array([c[4] for c in eth])

# 스프레드 비율
ratio = eth_close / btc_close
ratio_ma = np.mean(ratio[-50:])
ratio_std = np.std(ratio[-50:])
z_score = (ratio[-1] - ratio_ma) / ratio_std

# 진입 신호
if z_score > 2.0:
    # ETH 비정상 고평가 -> Short ETH, Long BTC
    print("Short ETH / Long BTC")
elif z_score < -2.0:
    # ETH 비정상 저평가 -> Long ETH, Short BTC
    print("Long ETH / Short BTC")
```

**핵심 파라미터**:
- MA 기간: 50~200 (15분봉)
- Z-score 진입: 2.0 / 청산: 0.5
- 포지션 비율: 금액 동일 (dollar-neutral)

**예상 효과**: 시장 중립이므로 방향 리스크 없음. 연 10~20% 기대 (보수적). 하지만 수수료가 2배 (양쪽 진입/청산).

**구현 난이도**: 중간 (1~2일). 동시 주문 실행, 포지션 밸런싱 로직 필요.

---

### 3.2 변동성 매매 (ATR Regime)

**원리**: BTC는 "저변동 압축 -> 폭발" 패턴이 반복됨. 변동성 자체를 매매 대상으로 삼음.

**전략**:
1. ATR(14) / ATR(50) < 0.7 = 변동성 압축 감지
2. 압축 후 첫 방향성 캔들에 진입 (브레이크아웃)
3. 높은 R:R (1:3 이상) + 작은 포지션

**코드 스니펫**:
```python
import pandas as pd
import numpy as np

def detect_volatility_squeeze(df_15m: pd.DataFrame) -> pd.Series:
    """ATR 압축 감지. True = 스퀴즈 상태."""
    h, l, c = df_15m['high'], df_15m['low'], df_15m['close']
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    atr_fast = tr.rolling(14).mean()
    atr_slow = tr.rolling(50).mean()
    squeeze = atr_fast / atr_slow
    return squeeze < 0.7

def breakout_signal(df_15m: pd.DataFrame, squeeze: pd.Series) -> pd.Series:
    """스퀴즈 후 브레이크아웃 방향. 1=롱, -1=숏, 0=없음."""
    dc_high = df_15m['high'].rolling(20).max()
    dc_low = df_15m['low'].rolling(20).min()
    signal = pd.Series(0, index=df_15m.index)
    # 스퀴즈 중에 돈치안 상단 돌파
    signal[(squeeze.shift(1)) & (df_15m['close'] > dc_high.shift(1))] = 1
    # 스퀴즈 중에 돈치안 하단 이탈
    signal[(squeeze.shift(1)) & (df_15m['close'] < dc_low.shift(1))] = -1
    return signal
```

**예상 효과**: BTC의 랜덤워크 특성을 회피 (추세를 예측하지 않고, 변동성 폭발만 포착). 연 30~60회 거래, 승률 40%지만 R:R 1:3으로 양의 기대값.

**구현 난이도**: 낮음 (4~6시간). 기존 CMA-ES 프레임워크에 통합 가능.

---

### 3.3 주말 효과 (Weekend Seasonality)

**원리**: BTC는 주말에 유동성 감소 -> 변동성 증가 + 특정 패턴 반복.

**관측된 패턴**:
- 토요일 00:00~06:00 UTC: 아시아 세션 시작, 유동성 최저
- 일요일 오후~월요일 새벽: CME 갭 형성

**구현 난이도**: 낮음이나 예상 효과 미미 (단독 전략 불가).

---

### 3.4 반감기 매크로 전략 (4년 주기)

BTC 반감기는 ~4년 주기. 반감기 후 12~18개월 상승 패턴이 역사적으로 반복.
- 마지막 반감기: 2024-04-20
- 현재: 반감기 후 ~23개월 (역사적 상승 구간 후반부)

**전략**: 이건 "언제 매매할지"가 아니라 "언제 롱 바이어스를 가질지"의 매크로 필터. 15분봉 전략의 방향 바이어스로 활용.

**구현 난이도**: 거의 없음 (상수 플래그). 하지만 단독 알파 불가.

---

## 4. 무료 데이터 소스 목록

| 데이터 | API/소스 | 형식 | 비용 | Python |
|--------|----------|------|------|--------|
| 펀딩레이트 | ccxt (Binance) | JSON | 무료 | `fetch_funding_rate_history()` |
| 미결제약정 | ccxt (Binance) | JSON | 무료 | `fetch_open_interest_history()` |
| BTC 도미넌스 | CoinGecko API | JSON | 무료(30/분) | `requests` |
| CME 갭 | Binance 일봉 | OHLCV | 무료 | `fetch_ohlcv('1d')` |
| 김치 프리미엄 | Upbit API + 환율 | JSON | 무료 | `requests` |
| 온체인 (유입/유출) | CryptoQuant | JSON | $49/월 | `requests` |
| 롱/숏 비율 | ccxt (Binance) | JSON | 무료 | `fetch_long_short_ratio_history()` |
| 청산 데이터 | Binance WebSocket | Stream | 무료 | `websockets` |
| 오더북 깊이 | ccxt (Binance) | JSON | 무료 | `fetch_order_book()` |

**추가 유용한 ccxt 메서드**:
```python
# 롱/숏 비율 (최상위 트레이더)
exchange.fetch_long_short_ratio_history('BTC/USDT:USDT', '15m', limit=100)

# 청산 히스토리 (Binance 전용)
# WebSocket: wss://fstream.binance.com/ws/btcusdt@forceOrder
```

---

## 5. Top 3 구현 계획

### TOP 1: 펀딩레이트 + OI 복합 필터 (기존 CMA-ES 위에)

**왜 1위**: 무료, 즉시 접근 가능, BTC에 특화된 파생 시장 데이터, 기존 전략 프레임워크에 필터로 추가만 하면 됨.

**구현 계획**:

1. **데이터 수집기** (4시간)
   - `scripts/collect_derivatives.py` 신규 생성
   - 15분마다: 펀딩레이트, OI, 롱/숏 비율 수집
   - SQLite `derivatives_data` 테이블에 저장
   - 과거 데이터: ccxt history API로 최대 가용 기간 수집

2. **XGBoost 피처 추가** (3시간)
   - `strategy_hybrid.py`의 `compute_xgb_features()`에 파생 피처 추가:
     - `funding_rate`: 현재 펀딩레이트
     - `funding_zscore`: 펀딩레이트 z-score (50기간)
     - `oi_change_1h`: OI 1시간 변화율
     - `oi_change_4h`: OI 4시간 변화율
     - `ls_ratio`: 롱/숏 비율
   - BTC 전용 XGBoost 모델 학습

3. **CMA-ES 필터** (2시간)
   - 극단 펀딩 필터: |funding| > 0.03% 시 반대 방향만 허용
   - OI 발산 필터: OI 감소 + 가격 상승 = 롱 진입 금지

4. **백테스트** (2시간)
   - `strategy_hybrid.py`를 BTC 대응으로 확장
   - Walk-forward 동일 프레임워크 적용

**총 소요**: 약 1.5일
**기대 효과**: BTC Hybrid 수익률 +12.7% -> +20%+ 개선 (파생 데이터가 BTC 방향성에 대한 추가 정보 제공)

---

### TOP 2: BTC/ETH Pairs Trading (시장 중립)

**왜 2위**: BTC 방향 예측이라는 근본 난제를 회피. ETH에서 검증된 알파(+42.4%)를 BTC 없이도 활용하면서 BTC 노출을 상쇄.

**구현 계획**:

1. **스프레드 분석** (3시간)
   - `scripts/pairs_analysis.py` 신규 생성
   - ETH/BTC 비율의 정상성 검정 (ADF test)
   - 최적 lookback 기간 탐색 (MA 50~200)
   - Z-score 진입/청산 임계값 백테스트

2. **시뮬레이션 엔진** (6시간)
   - `scripts/pairs_backtest.py` 신규 생성
   - 동시 롱/숏 포지션 관리
   - 수수료 2배 계산 (양쪽)
   - Dollar-neutral 포지션 사이징
   - Walk-forward 검증 (기존 프레임워크 재사용)

3. **실행 엔진** (4시간)
   - `scripts/pairs_trader.py` 신규 생성
   - Binance Futures 동시 주문 실행
   - 포지션 리밸런싱 (비율 drift 보정)
   - 대시보드 통합

**총 소요**: 약 2일
**기대 효과**: 연 10~20% 수익, 최대DD < 15% (시장 중립이므로 DD가 작음). 방향 리스크 제거가 최대 장점.

**주의**: 수수료 부담 2배. Binance Futures 수수료 0.04% x 4 (양쪽 진입+청산) = 0.16%/라운드트립. 거래 빈도를 주 2~3회로 제한해야 수수료에 잠식되지 않음.

---

### TOP 3: 변동성 브레이크아웃 (ATR Squeeze)

**왜 3위**: BTC의 "랜덤워크 + 간헐적 폭발" 특성에 가장 잘 맞는 전략 구조. 추세를 예측하지 않고, 변동성 상태 전환만 포착.

**구현 계획**:

1. **CMA-ES 변동성 전략 최적화** (4시간)
   - `scripts/strategy_cmaes_vol.py` 신규 생성
   - 파라미터: squeeze_ratio, dc_period, atr_fast, atr_slow, entry_mult, sl_mult, tp_mult, cooldown
   - 목적함수: Sharpe (기존 CMA-ES 프레임워크 재사용)
   - Walk-forward: Train 2021~2023, Val 2024, Test 2025~

2. **XGBoost 브레이크아웃 방향 예측** (3시간)
   - 스퀴즈 감지 후, 브레이크아웃 방향 예측
   - 피처: squeeze_duration, 직전 추세, 볼륨 패턴, 펀딩레이트
   - 스퀴즈 시점만 학습 (데이터셋 축소 -> 과적합 주의)

3. **백테스트 및 비교** (2시간)
   - 기존 MA Cross 전략과 수익률/DD/Sharpe 비교
   - BTC + ETH 모두 테스트 (일반화 확인)

**총 소요**: 약 1.5일
**기대 효과**: 연 15~25% 기대 (승률 35~40%지만 R:R 1:3). BTC에 MA Cross보다 적합할 가능성 높음.

---

## 6. 종합 전략 로드맵

```
Week 1 (Day 1~2): TOP 1 - 펀딩레이트+OI 필터
  -> 데이터 수집기 + BTC XGBoost 학습 + 백테스트
  -> 성공 기준: BTC Hybrid OOS Sharpe > 0.3

Week 1 (Day 3~4): TOP 3 - 변동성 브레이크아웃
  -> CMA-ES 최적화 + 백테스트
  -> 성공 기준: OOS Sharpe > 0.3, DD < -30%

Week 2 (Day 1~2): TOP 2 - Pairs Trading
  -> 스프레드 분석 + 백테스트
  -> 성공 기준: Sharpe > 0.5, DD < -15%

Week 2 (Day 3~4): 최종 비교 + 페이퍼 배포
  -> 3개 전략 OOS 비교
  -> 최고 전략 페이퍼 트레이딩 배포
```

**최소 기대값**: 3개 중 1개라도 BTC OOS Sharpe > 0.3이면 성공. 현재 BTC Hybrid가 +12.7% / Sharpe ~0.2이므로, 파생 데이터 추가로 0.3+ 달성 가능성이 가장 높음.

**핵심 원칙**: ETH에서 작동한 "기술적 분석 추세추종"은 BTC에서 구조적으로 작동하기 어렵다. BTC는 파생시장 데이터(펀딩, OI) 또는 방향 중립(Pairs) 또는 변동성 레짐(Squeeze)으로 접근해야 한다.
