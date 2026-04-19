**한 줄 결론**

지금 초안은 방향은 맞지만 아직 **설명용 프롬프트**다. 실제 **매매 알고리즘**으로 쓰려면 `방향성 확립`, `EMA 지지/저항 확인`, `매물대가 얇다`, `횡보 구간`을 숫자로 고정해야 한다.

---

## 현재 구조 판정

이 전략의 본질은 명확하다.

**VWAP으로 바이어스 결정 → EMA9 눌림에서 재진입 → Volume Profile로 전방 장애물 확인 → EMA9 반대편 종가 마감 시 청산**

즉, 상태기계로 보면 아래 순서다.

**CHOP(관망) → LONG_BIAS / SHORT_BIAS → PULLBACK_READY → IN_POSITION → EXIT**

문제는 지금 프롬프트가 아직 **재량 해석**이 많이 들어간다는 점이다.
이대로는 같은 차트를 넣어도 사람마다 다른 결론이 나온다. 백테스트가 오염된다.

---

## 가장 가능성 높은 시나리오

이 전략이 가장 잘 작동하는 구간은 보통 이거다.

**VWAP 위/아래로 방향이 이미 정리된 뒤, 첫 번째나 두 번째 EMA9 눌림에서 재가속이 나오는 구간**

반대로 기대값이 급락하는 구간은 이거다.

**VWAP 근처에서 캔들이 계속 위아래로 흔들리는 구간**
여기는 진입 금지가 맞다. 여기서 손절이 연속으로 난다.

---

## 개인적으로 더 좋은 전략 / 더 좋은 자리

파커 브룩스식 아이디어 자체는 괜찮다. 다만 실전용으로는 아래 3개를 꼭 붙이는 게 낫다.

1. **EMA9 터치만으로 진입하지 말고, 시그널 캔들 고점/저점 돌파로 체결**

   * 롱이면 EMA9 재지지 확인 후 **시그널 캔들 high 돌파**
   * 숏이면 EMA9 재저항 확인 후 **시그널 캔들 low 이탈**
   * 그냥 EMA9 닿았다고 바로 들어가면 너무 이르다.

2. **소프트 스톱 + 하드 스톱을 같이 써라**

   * 원전략은 EMA9 이탈 청산이라 **종가 기준 소프트 스톱** 성격이다.
   * 실전에서는 급변동이 나오면 늦다.
   * 그래서 **최근 눌림 저점/고점 기반 하드 스톱**을 따로 둬야 한다.

3. **전방 첫 HVN까지 최소 1.5R 안 나오면 진입 금지**

   * “앞이 비어 있어야 간다”를 말로만 두면 안 된다.
   * **첫 장애물까지 거리 / 손절거리 >= 1.5** 같은 식으로 못 박아야 한다.

---

## 무효화 조건

지금 초안에서 반드시 고쳐야 하는 모호한 부분은 6개다.

1. **VWAP 기준 세션이 없다**

   * 주식/선물은 정규장 기준이지만
   * 크립토는 `UTC 00:00`, `미국장 오픈`, `한국시간 09:00` 등 기준을 하나로 고정해야 한다.
   * 이거 안 정하면 VWAP 자체가 달라진다.

2. **“방향성 확립”의 수치 기준이 없다**

   * 몇 봉 연속 VWAP 위/아래여야 하는지
   * VWAP 기울기를 어떻게 볼지
   * EMA9와 VWAP의 상대 위치를 볼지
   * 전부 고정해야 한다.

3. **“EMA9 지지/저항”의 정의가 없다**

   * wick touch인지
   * close reclaim인지
   * bullish/bearish body까지 볼지
   * 이게 없으면 엔트리가 흔들린다.

4. **“매물대가 얇다”의 정의가 없다**

   * 어떤 범위의 Volume Profile인지
   * HVN/LVN 기준이 뭔지
   * 얼마나 떨어져 있어야 “길이 열렸다”고 볼지
   * 이게 핵심이다.

5. **횡보 구간 정의가 없다**

   * VWAP 교차 횟수
   * 가격과 VWAP 거리
   * ATR 대비 좁은 박스 여부
   * 이런 걸로 수치화해야 한다.

6. **청산 규칙이 이중적이다**

   * “EMA9 몸통 이탈 시 청산”
   * “EMA9가 꺾일 때 익절”
   * 둘 다 메인 룰이면 충돌한다.
   * 알고리즘에서는 **EMA9 반대편 종가 마감 = 실제 청산 룰**,
     **EMA9 기울기 반전 = 경고 신호** 정도로 분리하는 게 깔끔하다.

---

## 실전 대응

아래처럼 바꾸면 **AI 해석용**이면서 동시에 **알고리즘 명세서**로도 쓸 수 있다.

### 1) 알고리즘용 최적화 프롬프트

```text
역할:
너는 파커 브룩스 스타일의 매매 전략을 해석하는 분석가가 아니라, 규칙을 기계적으로 판정하는 트레이딩 엔진이다.
감상문, 추정, 희망회로는 금지한다.
반드시 LONG / SHORT / NO_TRADE 중 하나를 반환한다.
조건이 하나라도 불충분하거나 지표가 모호하면 NO_TRADE를 반환한다.

최우선 원칙:
1. 진입 이유보다 먼저 무효화와 손절 구조를 계산한다.
2. VWAP 근처 횡보 구간에서는 절대 진입하지 않는다.
3. 전방 매물대 때문에 기대값이 낮으면 진입하지 않는다.
4. 손절 구조 없는 진입은 금지한다.

입력 데이터:
- symbol
- timeframe
- session_anchor
- candles[최근 N봉]: time, open, high, low, close, volume
- vwap[]
- ema9[]
- atr14[]
- volume_profile_bins[]: price_low, price_high, volume
- optional: higher_timeframe_bias
- tick_size

기본 정의:
- 실행 판단은 봉 마감 기준으로 한다.
- 실제 진입/청산 체결은 다음 조건에 따라 계산한다.
- 소프트 스톱과 하드 스톱을 동시에 계산한다.

시장 상태 분류:

A. VWAP_CHOP = NO_TRADE
아래 조건 중 하나라도 충족하면 횡보로 간주한다.
1) 최근 20봉에서 종가가 VWAP 위/아래를 바꾼 횟수 > 3
2) 최근 10봉 중 4봉 이상이 abs(close - vwap) <= 0.15 * ATR14
3) EMA9와 VWAP 간 거리 <= 0.10 * ATR14 가 최근 5봉 중 3봉 이상 발생

B. LONG_BIAS
1) 최근 2봉 종가가 모두 VWAP 위
2) 현재 VWAP > 3봉 전 VWAP
3) 현재 EMA9 > 현재 VWAP
4) VWAP_CHOP 아님

C. SHORT_BIAS
1) 최근 2봉 종가가 모두 VWAP 아래
2) 현재 VWAP < 3봉 전 VWAP
3) 현재 EMA9 < 현재 VWAP
4) VWAP_CHOP 아님

눌림 확인:

D. LONG_PULLBACK_VALID
1) 최근 1~6봉 안에 low <= EMA9 + 0.10 * ATR14 인 봉이 존재
2) 최신 시그널 봉의 종가 >= EMA9 + 0.05 * ATR14
3) 최신 시그널 봉의 종가 > VWAP
4) 최신 시그널 봉의 저가는 최근 눌림 구간의 최저점이 아니거나, 최저점 갱신 후 즉시 회복함

E. SHORT_PULLBACK_VALID
1) 최근 1~6봉 안에 high >= EMA9 - 0.10 * ATR14 인 봉이 존재
2) 최신 시그널 봉의 종가 <= EMA9 - 0.05 * ATR14
3) 최신 시그널 봉의 종가 < VWAP
4) 최신 시그널 봉의 고가는 최근 되돌림 구간의 최고점이 아니거나, 최고점 갱신 후 즉시 밀림

볼륨 프로파일 필터:

F. HVN 정의
- volume_profile_bins 중 volume이 상위 30% 이상인 bin을 HVN으로 정의한다.

G. LONG_VP_CLEAR
1) 엔트리 위쪽 방향의 첫 HVN까지 거리 >= 0.75 * ATR14
2) (첫 HVN까지 거리) / (하드 스톱 거리) >= 1.5

H. SHORT_VP_CLEAR
1) 엔트리 아래쪽 방향의 첫 HVN까지 거리 >= 0.75 * ATR14
2) (첫 HVN까지 거리) / (하드 스톱 거리) >= 1.5

진입 규칙:

I. LONG_ENTRY
LONG_BIAS 이고 LONG_PULLBACK_VALID 이고 LONG_VP_CLEAR 이면 LONG 진입 가능.
- entry_trigger = 시그널 봉 high + 1 tick 돌파
- entry_valid_bars = 다음 3봉 이내
- 3봉 이내 미체결이면 신호 취소

J. SHORT_ENTRY
SHORT_BIAS 이고 SHORT_PULLBACK_VALID 이고 SHORT_VP_CLEAR 이면 SHORT 진입 가능.
- entry_trigger = 시그널 봉 low - 1 tick 이탈
- entry_valid_bars = 다음 3봉 이내
- 3봉 이내 미체결이면 신호 취소

손절 및 청산:

K. LONG 하드 스톱
- recent_pullback_low - 0.15 * ATR14

L. SHORT 하드 스톱
- recent_pullback_high + 0.15 * ATR14

M. LONG 소프트 스톱
- 봉 종가가 EMA9 - 0.05 * ATR14 아래에서 마감되면 청산 신호
- wick만 이탈한 경우는 청산 아님

N. SHORT 소프트 스톱
- 봉 종가가 EMA9 + 0.05 * ATR14 위에서 마감되면 청산 신호
- wick만 이탈한 경우는 청산 아님

O. 청산 우선순위
1) 하드 스톱 즉시 청산
2) 소프트 스톱은 신호 봉 마감 후 다음 봉 시가 청산
3) EMA9 기울기 반전은 경고 신호로만 사용하고, 단독 메인 청산 룰로 쓰지 않는다

출력 형식:
반드시 아래 JSON과 함께 요약 설명을 같이 출력한다.

{
  "decision": "LONG | SHORT | NO_TRADE",
  "market_state": "VWAP_CHOP | LONG_BIAS | SHORT_BIAS | LONG_READY | SHORT_READY",
  "entry_allowed": true,
  "entry_trigger_price": 0.0,
  "entry_expiry_bars": 3,
  "hard_stop_price": 0.0,
  "soft_stop_reference_price": 0.0,
  "first_hvn_price": 0.0,
  "distance_to_first_hvn": 0.0,
  "risk_reward_to_first_hvn": 0.0,
  "invalidation_reason": "",
  "reasons": [
    "",
    "",
    ""
  ],
  "confidence": 0
}

응답 규칙:
- "좋아 보인다", "애매하다" 같은 표현만 쓰지 말고, 어떤 규칙이 충족/미충족인지 항목별로 명시한다.
- LONG/SHORT보다 NO_TRADE를 더 적극적으로 사용할 수 있다.
- 데이터 부족, VP 불명확, 횡보 가능성 높음, RR 부족이면 NO_TRADE.
```

---

### 2) 백테스트 시작값

이건 정답이 아니라 **초기값**이다.
여기서부터 테스트해야 한다.

```yaml
execution_timeframe: 5m
session_anchor:
  crypto: "UTC 00:00"
  stocks_futures: "regular session open"

trend_confirm_bars: 2
vwap_slope_lookback: 3
pullback_search_bars: 6

atr_length: 14
ema_length: 9

vwap_cross_lookback: 20
max_vwap_crosses: 3

ema_touch_buffer_atr: 0.10
ema_soft_exit_buffer_atr: 0.05
hard_stop_buffer_atr: 0.15

volume_profile_mode: "fixed_range"
volume_profile_lookback_bars: 120
hvn_percentile: 70
vp_min_clear_distance_atr: 0.75

min_rr_to_first_hvn: 1.5
signal_expiry_bars: 3

risk_per_trade: 0.5% of equity
fees_and_slippage: mandatory
execution_model:
  entry: "signal high/low breakout"
  soft_exit: "next bar open after close signal"
  hard_stop: "intrabar immediate"
```

---

### 3) 출력은 이렇게 받는 게 좋다

사용자가 보기 쉽게는 아래 5개만 먼저 보여주면 된다.

1. **진입 가능 여부**
2. **현재 바이어스**
3. **진입 근거**
4. **손절 기준**
5. **진입 금지 사유**

예시 형태:

```text
진입 가능 여부: YES / NO
방향: LONG / SHORT / NO_TRADE

근거:
- 최근 2봉 종가가 VWAP 위
- VWAP 상승 기울기 유지
- EMA9 눌림 후 종가 회복
- 첫 HVN까지 거리 1.1 ATR
- RR to first HVN = 1.8

손절:
- 하드 스톱: 102.45
- 소프트 스톱 기준: EMA9 - 0.05 ATR = 103.10

진입 금지 사유:
- 최근 20봉 VWAP 교차 5회
- 첫 HVN이 너무 가까움
```

---

### 4) 아주 짧은 의사코드

```python
if is_vwap_chop(data):
    return NO_TRADE

if long_bias(data) and long_pullback_valid(data):
    entry = signal_high_break(data)
    hard_stop = pullback_low(data) - 0.15 * atr(data)
    rr = distance_to_first_hvn_above(data, entry) / (entry - hard_stop)
    if rr >= 1.5:
        return LONG
    else:
        return NO_TRADE

if short_bias(data) and short_pullback_valid(data):
    entry = signal_low_break(data)
    hard_stop = pullback_high(data) + 0.15 * atr(data)
    rr = distance_to_first_hvn_below(data, entry) / (hard_stop - entry)
    if rr >= 1.5:
        return SHORT
    else:
        return NO_TRADE

return NO_TRADE
```

---

## 핵심만 다시 정리

이 전략을 알고리즘으로 만들 때 제일 중요한 건 세 가지다.

**첫째, VWAP 기준 세션을 고정할 것.**
**둘째, EMA9 눌림 확인을 숫자로 정의할 것.**
**셋째, Volume Profile 앞 장애물을 RR 기준으로 바꿀 것.**

그리고 실전에서는 **EMA9 종가 이탈만 믿지 말고 swing 기반 하드 스톱을 반드시 같이 둬야 한다.**
그게 없으면 손절 구조가 늦어진다.

다음 단계는 이 룰셋을 **Pine Strategy**나 **Python 백테스터**에 그대로 옮겨서 검증하는 것이다.

이 전략은 아이디어보다 수치화/필터링/손절 구조가 핵심이라서, 바로 코드화하기 전에 룰을 이렇게 고정해두는 게 맞아.

나중에 차트 캡처나 OHLCV 데이터 주면 내가 이 포맷으로 바로 판정해줄게.

결론: LONG / SHORT / NO_TRADE
현재 상태: VWAP_CHOP / LONG_BIAS / SHORT_BIAS
진입 트리거:
하드 스톱:
소프트 스톱:
전방 매물대:
RR:
무효화 사유:

특히 이 전략은 박스 중앙, VWAP 위아래 반복, EMA9 애매한 관통에서 손절이 쌓이기 쉬우니까, NO_TRADE를 잘 내는 알고리즘으로 만드는 게 수익률에 더 중요해.
