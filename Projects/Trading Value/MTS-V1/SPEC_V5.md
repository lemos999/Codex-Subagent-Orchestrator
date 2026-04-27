# Triple Confluence Runner (MTS-V1) — SPEC_V5.2 Final

**작성일**: 2026-04-24
**버전**: v5.2 Final (v5.1 24건 정합화 + SPEC Gap 2건 명시화)
**대상**: Pine Script v5 (TradingView 백테스트) + Python CCXT (Binance USDT-M Perpetuals 실전/페이퍼)
**구현자**: Codex (지시서: `REVIEW_FOR_CODEX.md`)
**불변 원칙 (Invariants)**:
1. **7:3 비대칭** — 승률 30%대 × 평균 RR ≥ 2.5 × tail winner share 최대화 (이건 승률 30%를 유지하라는 뜻이 아닙니다. 낮은 승률이어도 손실을 만회하는 수익을 뜻합니다.)
2. **Layered 평균가 하향** — L1/L2/L3가 점진적으로 깊어져 반전 시 tail 포착 확률 ↑
3. **Triple Confluence 희소 승급** — 흔한 수렴에서 발화하면 noise 확대. 2차 전용·0.2×ATR 유지
4. **Runner 대승 보호** — Kijun break 단일 청산. 조기 익절은 A/B/C가 담당

> 본 버전의 모든 수치·공식은 위 4가지 불변 원칙을 훼손하지 않는 범위에서 선택됐다.

---

## 0. 전략 철학

- **7:3 비대칭**: 승률 30% × 대승 > 패율 70% × 소손. Tail winner share 최대화.
- 중앙값 수익 희생 허용 — 산술평균 기댓값 > 0만 필요충분.
- 대상 자산: BTC / ETH / SOL / XRP / BNB / DOGE (6 symbols).
- 대장주(BTC) EMA 동조 필터로 나머지 5종목 추세 검증.

---

## 1. 시스템 구성

### 1.1 TF 구성

| TF | 값 | 용도 |
|---|---|---|
| `htf` | 4H | 추세/편향 확인, 대장주 BTC EMA(50) |
| `entry_tf` | 1H | State Machine, Kijun, ATR, Triple Confluence, Hard SL |
| `ltf` | 15m | **CVD Divergence 전용** (다른 용도 금지 — L3 확정) |

### 1.2 지표 (v5.1 수식 확정)

| 지표 | 정의 | 사용처 |
|---|---|---|
| ATR | `ATR(entry_tf, 14)` | ε, Triple Confluence, Liquidation 분모, Hard SL |
| Ichimoku | `(tenkan=9, kijun=26, senkou_b=52)` on entry_tf | Kijun(Runner 청산, TP A, Entry trigger) |
| Dynamic VP | POC/VAH/VAL (entry_tf rolling 500 캔들, **bins = 50**, price range = window high-low, **volume allocation: close-price single-bin**) | L1 Limit, Triple Confluence POC |
| Fibo Anchor | Pivot H/L **(Bill Williams 5-bar fractal, pivot_length=2)**, 없으면 100캔들 H/L fallback | L2/L3 Limit, TP B(1.0), TP C(1.5) |
| RSI | `RSI(entry_tf, 14)` | TP A |
| Volume SMA | `SMA(volume, 20)` on entry_tf | TP C |
| CVD Proxy (Pine) | `cumsum((close - open) × volume)`, **UTC 00:00 일별 리셋** | Pine 백테스트 근사 |
| CVD Trade Stream (Python) | Binance trade delta 누적, **UTC 00:00 일별 리셋** | 실전 실행 정확값 |
| CVD Spike (절대) | `|delta_bar| > 3 × SMA(|delta|, 20)` | 후보 탐지 |
| Reverse Spike | 롱 포지션: `delta_bar < -3 × SMA(|delta|, 20)` / 숏: 부호 반전 | State 2 Abort, EVASION (1) |
| BTC EMA (4H) | `EMA(close_4H, 50)` | HTF 편향, Entry trigger (a) |

### 1.3 Liquidation Safeguard (공식)

```
mmr (Python) = ccxt.fetch_position_risk(symbol)['maintenanceMarginRate']
mmr (Pine)   = input_mmr_{symbol}   (심볼별 상수 input)

cur_lev = config.yaml::user_leverage   (default 10)
buffer        = 0.20   # 20% 가격 버퍼
fees_slippage = 0.01   # 1% 수수료·슬리피지

raw_cap = floor(1 / (buffer + fees_slippage + mmr))
effective_leverage = max(1, min(cur_lev, raw_cap))
```

---

## 2. Entry Logic

### 2.0 State 0 → 1 Trigger (최초 신호) — **v5.1 신규 (C1 해결)**

Long 진입 조건 (**AND**):

1. **HTF 편향**: HTF(4H) 가격 > BTC EMA(50). 대상 심볼이 BTC면 자기 EMA 위.
2. **entry_tf 편향**: entry_tf(1H) 가격 첫 종가 돌파 — `close[t] > Kijun[t]` AND `close[t-1] ≤ Kijun[t-1]`.
3. **CVD 합치**: 직전 30분 누적 CVD > 0 (30m bar 2개 delta 합, 또는 1H bar 1개 delta).
4. **중복 방지**: 동일 심볼 state ∈ {0} 및 쿨다운 아님.

Short 진입: 전 조건 부호 반전.

**방향성 근거**: 
- (1)은 대장주 동조 필터 → noise trade 감소, tail winner 집중 (불변 원칙 1).
- (2)는 첫 종가 돌파만 — Layered entry의 깊은 L2/L3 배치를 위해 **돌파 직후에 주문**이 걸려야 의미 (불변 원칙 2).
- (3)은 거래 주체의 매수 우세 확인 — 반대편 함정 회피.

### 2.1 Layered Entry 33/33/34 (Maker Limit) — **v5.1 공식 확정 (C3 해결)**

| Layer | 비율 | 가격 공식 (Long) |
|---|---|---|
| L1 | 33% | `max(POC, Kijun_entry_tf) + 0.05 × ATR(entry_tf, 14)` |
| L2 | 33% | `Fibo 0.618` (Pivot L 기반 retracement) |
| L3 | 34% | `min(Fibo 0.786, VAL)` |

Short: 방향 반전, 버퍼 부호 반전(-0.05 × ATR).

**Pivot 시간 순서 검증 (v5.2 addendum)**:
- Long anchor는 `pivot_low`가 `pivot_high`보다 먼저 형성되어야 한다 (`pivot_low_ts < pivot_high_ts`).
- Short anchor는 `pivot_high`가 `pivot_low`보다 먼저 형성되어야 한다 (`pivot_high_ts < pivot_low_ts`).
- Pivot H/L 중 하나라도 100캔들 fallback이면 시간 순서 검증은 통과로 간주한다.
- 시간 순서가 맞지 않으면 해당 bar의 Layered Entry 가격 계산은 skip하고 다음 bar에서 재평가한다.
- Fibo 수식 자체(`0.618 / 0.786 / 1.0 / 1.5`)와 §2.0 Entry trigger는 변경하지 않는다.

**방향성 근거**: 
- L1 버퍼(+0.05×ATR)는 fake-breakout 필터 — State 1에서 재하강 시 48h Timeout으로 자연 탈락.
- L2/L3는 깊은 매수 구간에서만 체결 → **체결 시 평균가 하향**. 반전 시 L2 대비 Fibo 1.0 (TP B)까지 RR ≥ 2.5 확보 (불변 원칙 2).
- L3 `min(Fibo 0.786, VAL)`는 보수적 선택 — L3 체결 확률 ↓, 대신 체결 시 평균가 최대 하향.

### 2.2 Triple Confluence (마스터 키 — 2차 전용) — H6 해결

**평가 시점**: **L2 체결이 확정된 entry_tf(1H) 바의 close 시점 1회만.**
**금지**: L1·L3 진입에서는 평가·기록·저장하지 않음.

```
abs_range = max(POC, Kijun_entry_tf, Fibo_0.618) - min(POC, Kijun_entry_tf, Fibo_0.618)
triple_confluence = (abs_range ≤ 0.2 × ATR(entry_tf, 14))
```

**역할**: 사이징 5% → 10% 승급 플래그 (§4.2). 진입 필요조건 아님.

**방향성 근거**: 임계 0.2×ATR은 **희소 승급** — 흔하게 발화하면 noise를 증폭 (불변 원칙 3). Hard SL(2×ATR)의 1/10 폭에서만 승급 → "매우 강한 수렴"에서만 베팅 2배.

### 2.3 LTF(15m) CVD Divergence — L2 체결 직전 참고 게이트

- 윈도: L2 체결 직전 15m 캔들 **20개**
- 방식: **Bill Williams 5-bar fractal (pivot_length=2)** 기반 regular divergence — 가격 LL + CVD HL (롱) / 가격 HH + CVD LH (숏)
- 효과: 참고 신호 (blocker 아님). 없어도 L2 체결 진행 가능.
- **tie-break 가중**: divergence 발견 + triple_confluence TRUE 동시 시 L3 재주문 5초 우선 실행 (maker queue 유리 위치 선점).

---

## 3. State Machine

| State | 이름 | 진입 | 전이 |
|---|---|---|---|
| 0 | IDLE | 신호 대기 | §2.0 trigger → 1 |
| 1 | PENDING | L1 Limit pending | 체결 → 2 / **48h Timeout → Abort 0** |
| 2 | FILLED_PARTIAL | L1~L2 체결 | L3 체결 → 3 / **Reverse Spike OR HTF(4H) 기준선 반대 관통 → Abort 0** |
| 3 | FILLED_FULL | L3 체결 완료, 미청산 | Hard SL hit → 0+쿨다운 / TP A → 3.A / TP B → 3.AB / TP C → 0 또는 4 / EVASION → 5 |
| 3.A | TP_A_HIT | A 50% 청산 완료 | A **lock**, B/C만 재평가. Hard SL/EVASION 유효 |
| 3.AB | TP_B_HIT | A+B 합산 75% 청산 완료 | A+B **lock**, C만 재평가. Hard SL/EVASION 유효 |
| 4 | RUNNER | TP C hit + use_runner=true | Kijun 2연속 이탈 → 0 (해당 심볼 24h 쿨다운) |
| 5 | EVASION | 비상 청산 | 시장가 전량 청산 → 0 (해당 심볼 24h 쿨다운) |

### 3.1 State 2 Abort 조건 (H7 Reverse Spike 수식 확정)

```
Reverse Spike (롱):  delta_bar < -3 × SMA(|delta|, 20)
Reverse Spike (숏):  delta_bar > +3 × SMA(|delta|, 20)
HTF 관통 (롱):        HTF(4H) 가격 < Kijun_htf 첫 종가
HTF 관통 (숏):        부호 반전

둘 중 하나라도 충족 시 State 2 → 0 (L3 pending 취소, L1/L2 포지션 시장가 청산, 해당 심볼 쿨다운 없음)
```

### 3.2 EVASION 조건 (§3.1 보충, H8 peak 기준 확정)

```
ε = 0.1 × ATR(entry_tf, 14)

(1) Reverse Spike (위 §3.1) OR HTF(4H) 기준선 반대 관통
(2) 체결 후 48h 내 미실현 수익의 peak (max over [체결~현재]) < ε

둘 다 충족 시 State → 5 EVASION → 시장가 전량 청산 → 0 + 24h 쿨다운
```

**방향성 근거**: (1)은 "시장 의견 반전", (2)는 "signal 죽음". 두 신호 AND로 **false EVASION 억제** — 조기 청산이 잦으면 tail winner 빈도 감소 (불변 원칙 1·4).

---

## 4. Sizing

### 4.1 기본

- 총자본 비중: `equity × 0.05` (5%)
- 레이어 분할: L1 33% / L2 33% / L3 34%

### 4.2 Triple Confluence 승급 (M15 부분 체결 처리 추가)

**조건**: §2.2 triple_confluence == TRUE (L2 체결 직후 1회 평가)
**목표 총 노출**: `equity × 0.10` (10%)

**재사이징 공식**:
```
L1 노출: equity × 0.05 × 0.33 = 1.65%  (고정, 소급 증액 불가)
잔여 예산: equity × (0.10 - 0.0165) = 8.35%
L2 재사이징: 8.35% × (33 / 67) ≈ 4.11%
L3 재사이징: 8.35% × (34 / 67) ≈ 4.24%
```

**L3 부분 체결 중 승급 (M15)**:
- L3 Limit이 5% 프레임 수량으로 **부분 체결 중** 승급 신호 발생:
  - 부분 체결분 **유지** (이미 체결된 포지션 소급 변경 불가)
  - 남은 pending 수량을 10% 프레임 기준 L3 수량과 부분 체결분의 **차이**로 재계산 → 기존 pending 취소 → 차분 수량 재주문
  - client_order_id 신규 생성 (idempotency 보존)
- **L3 미체결 상태**: pending 전부 취소 → 10% 프레임 L3 수량으로 재주문.

### 4.3 Risk Limits

- `daily_max_loss`: **전 심볼 합산** equity 대비 `-5%` 도달 시 **모든 신규 신호 중단** (UTC 00:00 리셋 전까지).
  - 기존 포지션은 TP/EVASION/Hard SL 정상 경로로 진행.
- `hard_sl` hit 시: 해당 심볼 **24h 쿨다운**.
- Runner / EVASION 청산 시: 해당 심볼 **24h 쿨다운**.

---

## 5. Exit Logic (Hard SL + Dynamic TP A/B/C)

### 5.0 Hard SL — **v5.1 신규 (C2 해결)**

```
avg_entry = Σ(fill_price_i × fill_qty_i) / Σ(fill_qty_i)   (L1~L3 중 체결된 layer 가중평균)

Hard SL (Long)  = avg_entry - 2 × ATR(entry_tf, 14)
Hard SL (Short) = avg_entry + 2 × ATR(entry_tf, 14)

발동: 가격이 Hard SL 도달/관통 → 시장가 전량 청산 → State → 0 → **해당 심볼 24h 쿨다운**.
재계산: L2 체결 시, L3 체결 시마다 avg_entry 업데이트 → Hard SL 재계산 (주문 cancel+replace).
Triple Confluence 승급 후에도 avg_entry는 체결가 기준 동일 (수량만 증가) → Hard SL 재계산.
```

**방향성 근거**: 
- 2×ATR 폭 = Triple Confluence 승급 임계(0.2×ATR, §2.2)의 **10배** → "승급 구간에서 10배 벗어나면 실패 선언".
- TP B(Fibo 1.0)는 일반적으로 avg_entry + 3~5×ATR → **Hard SL : TP B = 2 : 3~5** → RR ≥ 2.5 공식 충족 (불변 원칙 1).
- avg_entry 기반 계산으로 Layered 평균가 하향 효과가 Hard SL에도 반영 (L3 체결 시 Hard SL 자동 하향).

### 5.1 TP 우선순위 (Sub-state 흐름) — **v5.1 확정 (C4 해결)**

```
State 3 (FILLED_FULL, 미청산)
  ├── Hard SL hit  → State 0 + 24h 쿨다운
  ├── TP A hit     → State 3.A (50% 청산, A lock — 재발화 금지)
  │      ├── Hard SL hit → State 0 + 24h 쿨다운
  │      ├── TP B hit    → State 3.AB (추가 50% 청산, 누적 75%)
  │      │      ├── Hard SL hit → State 0 + 24h 쿨다운
  │      │      ├── TP C hit    → 전량 청산 OR State 4 (Runner)
  │      │      └── EVASION     → State 5
  │      ├── TP C hit    → 전량 청산 OR State 4
  │      └── EVASION     → State 5
  ├── TP B hit     → State 3.AB (50% 청산, A+B lock)
  │      └── (이하 3.AB 가지와 동일)
  ├── TP C hit     → 전량 청산 OR State 4
  └── EVASION      → State 5
```

**방향성 근거**: A → B → C = **모멘텀 약함 → 기본 → 강함** 트리거 스펙트럼.
- A 먼저 발화 = 하락 시작 신호 → early 50% 확정 (손실 제한).
- B만 발화 = 정상 궤적 → 중앙값 수익 실현.
- C 발화 = tail winner 조짐 → Runner 승급이 정상 경로 (불변 원칙 4).
- 각 lock은 재발화 방지 — 동일 TP 조건이 연속 bar에서 유지돼도 이미 청산 완료 수준 존중.

### 5.2 조건 A (H10 "제한적 실행" 삭제)

```
RSI(entry_tf, 14) < 55
AND Kijun 기울기 ≤ 0 2연속:
  Kijun[t] - Kijun[t-1] ≤ 0
  AND Kijun[t-1] - Kijun[t-2] ≤ 0

→ 포지션의 50% 시장가 청산 → State 3 → 3.A (A lock)
```

### 5.3 조건 B

```
가격 ≥ Fibo 1.0 (Pivot H 확장)
→ 잔여 포지션의 50% 청산 → State (3 → 3.AB) 또는 (3.A → 3.AB) (B lock)
```

### 5.4 조건 C

```
가격 ≥ Fibo 1.5
AND volume > SMA(volume, 20) × 1.5

→ config.use_runner == true 이면:  State → 4 (Runner, 포지션 유지)
   config.use_runner == false 이면: 전량 시장가 청산 → State → 0
```

---

## 6. Runner

### 6.1 진입

TP C hit + `config.use_runner == true` 시 State {3 | 3.A | 3.AB} → 4.
진입 시점 잔여 포지션 전량 유지 (부분 청산 없음).

### 6.2 Runner state 내 TP A/B/C 평가 — **M14: 비활성**

Runner state에서는 Kijun break 단일 청산 조건만 평가. A/B/C는 비활성.
Hard SL과 EVASION도 비활성 (이미 대승 구간 진입 — trailing은 Kijun이 담당).

### 6.3 청산 — entry_tf(1H) Kijun 2연속 이탈

```
TF: entry_tf (1H)
조건:
  close[t-1] < Kijun_sen[t-1]
  AND open[t] < Kijun_sen[t]
액션: 시장가 전량 청산 → State 4 → 0
```

### 6.4 청산 후 쿨다운 — M17

Runner 청산 후 해당 심볼 **24h 쿨다운** (hard_sl 동일 규칙).

**방향성 근거**: Runner 승급은 tail winner 포착 핵심. 청산 직후 재진입하면 시장 피로 구간에서 noise에 눌림 → tail 크기 축소. 24h 대기로 시장 구조 재정비 (불변 원칙 4).

### 6.5 구현 예시

**Pine v5**
```pine
kijun_entry = (ta.highest(high, 26) + ta.lowest(low, 26)) / 2
kijun_break = close[1] < kijun_entry[1] and open < kijun_entry
if state == 4 and kijun_break
    strategy.close_all(comment="RUNNER_KIJUN_BREAK")
```

**Python CCXT**
```python
if state == STATE_RUNNER:
    c_prev_close = ohlcv_1h[-2]['close']
    c_cur_open   = ohlcv_1h[-1]['open']
    k_prev, k_cur = kijun_1h[-2], kijun_1h[-1]
    if c_prev_close < k_prev and c_cur_open < k_cur:
        close_position_market(reason="RUNNER_KIJUN_BREAK")
        set_symbol_cooldown(symbol, hours=24)
```

---

## 7. Ops & Backtest

### 7.1 Persistence (M16 파일명 규칙)

디렉터리: `state/`
파일명: `state_{symbol_slug}.json` (예: `state_BTC_USDT_USDT.json`)
`symbol_slug`: 슬래시·콜론을 언더스코어로 치환 (`BTC/USDT:USDT` → `BTC_USDT_USDT`)

스키마:
```json
{
  "strategy": "MTS-V1",
  "version": "v5.2",
  "symbol": "BTC/USDT:USDT",
  "state": 2,
  "sub_state": null,
  "avg_entry": 0.0,
  "hard_sl": 0.0,
  "entry_prices": {"L1": 0.0, "L2": 0.0, "L3": null},
  "fill_qtys":    {"L1": 0.0, "L2": 0.0, "L3": 0.0},
  "triple_confluence": true,
  "sizing_frame": 0.10,
  "client_order_ids": {"L1": "...", "L2": "...", "L3": "..."},
  "cvd_daily_start": "2026-04-24T00:00:00Z",
  "created_ts": "ISO8601",
  "updated_ts": "ISO8601"
}
```

### 7.2 Idempotency

```
client_order_id = f"mtsv1_{symbol_slug}_{state_from}{state_to}_{timestamp_ms}"
```

### 7.3 Parity Check (Pine vs Python) — **v5.1 완화 (C5)**

| 항목 | v5.0 임계 | v5.1 임계 | 근거 |
|---|---|---|---|
| 시그널 발화 타이밍 일치 | ≥ 95% | **≥ 85%** | Pine bar-close vs Python tick 차이 |
| 승률 차이 (24h 기준) | ≤ 3%p | ≤ 5%p | parity 완화 반영 |
| 평균 RR 차이 | ≤ 10% | ≤ 15% | parity 완화 반영 |
| CVD 값 일치 | (묵시 필요) | **비교 배제** | 구조적 차이 — Proxy vs Tick |
| CVD 부호 일치 (bar 단위) | — | **≥ 90%** | 방향성만 검증 |

미달 시: Pine proxy 수식 재조정 또는 Pine `request.security()` lower-TF 호출로 tick 근사.

### 7.4 Trade Log (jsonl append)

```json
{
  "ts": "ISO8601",
  "symbol": "BTC/USDT:USDT",
  "variant": "v5.2",
  "event": "ENTRY_L1|ENTRY_L2|ENTRY_L3|TP_A|TP_B|TP_C|RUNNER_START|RUNNER_EXIT|EVASION|HARD_SL|TIMEOUT|ABORT",
  "state_transition": "1→2",
  "layer": 2,
  "fill_price": 0.0,
  "fill_qty": 0.0,
  "fees": 0.0,
  "funding_fee": 0.0,
  "equity": 0.0,
  "cvd_delta": 0.0,
  "cvd_sign": 1,
  "reverse_spike": false,
  "triple_confluence": false,
  "avg_entry": 0.0,
  "hard_sl": 0.0,
  "rr_realized": 0.0,
  "exit_reason": null,
  "runner_exit_price": null,
  "evasion_reason": null,
  "hit": true
}
```

**Null 정책 (L20)**:
- Runner 미발동 trade: `runner_exit_price = null`.
- EVASION 미발동 trade: `evasion_reason = null`.
- Triple Confluence: 항상 boolean (null 아님).
- L3 미체결 상태에서 청산: `entry_prices.L3 = null` 유지.

### 7.5 Backtest Criteria (통과 기준 — 6항목 AND)

| # | 기준 | 임계 |
|---|------|------|
| 1 | Sharpe | ≥ 1.0 |
| 2 | Profit Factor | ≥ 1.3 |
| 3 | Max Drawdown | ≤ 20% |
| 4 | trades / walk-forward window | ≥ 100 |
| 5 | Wilson 95% CI lower | > BE(RR) = 1 / (1 + avg_RR) |
| 6 | 평균 RR | ≥ 2.5 |

Walk-forward: 4 window (시간축 기반, trade timestamp 필수 기록).
전체 PASS 조건: 1~6 모두 PASS AND walk-forward ≥ 2 window가 (1~3 AND 5) 개별 충족.

### 7.6 Ops Robustness — **v5.1 신규 (L18/L19)**

- **Maker Rejection 재시도 (L18)**: post-only 주문 거부 시 방향 반대로 1 tick 조정 후 재주문, **최대 3회**. 초과 시 해당 layer 포기 → state 유지, 다음 entry_tf 바에 재평가.
- **CVD 누적 시작점 (L19)**: UTC 00:00 일별 리셋. 각 심볼 독립. 대장주 BTC CVD도 동일 리셋.
- **State 복구 타이밍**: 프로세스 시작 시 state.json 읽고 → Binance 포지션·주문 재조회 → 불일치 시 **사용자 알림** 후 state.json 우선 (자동 수정 금지, reconciliation은 수동).

---

## Appendix A. Min-1/2/3 확정

| Min | 내용 | 확정값 |
|---|---|---|
| Min-1 | State 1 Timeout TF | 48 bars on entry_tf(1H) = **48h** |
| Min-2 | Runner 청산 TF | **entry_tf(1H)**, close[t-1]<Kijun + open[t]<Kijun 2연속 |
| Min-3 | Triple Confluence 범위 | **L2 전용** 마스터 키, 사이징 5%→10% 승급 트리거 |

## Appendix B. v1 → v5.1 변경 이력

- **v1**: 최초 명세 (Part 2 검증에서 24건 빈틈 식별 — Critical 3 / High 9 / Medium 5 / Low 7).
- **v2**: Liquidation Safeguard, State 전이 완결, TP A/B/C 우선순위, 로그 스키마.
- **v3**: RR≥2.5 추가, Volume Decay Lock 제거, 48 bars/48h.
- **v4**: v2+v3 통합, State 5 조건 (1)+(2) 병합, 조건 A/B/C 복원 (일부 회귀).
- **v5**: 모든 v1 Must-fix 해결 — Liquidation 공식, ε, 20 ltf 캔들, State 2 Abort 바인딩, 대장주 EMA@HTF, fees/funding_fee/equity, trades/Wilson, RR≥2.5, UTC 00:00, 전 심볼, ltf CVD 전용, 조건 A RSI+Kijun 기울기.
- **v5.1** (현재): v5 리뷰 24건 정합화.
  - **Critical (C1~C5)**:
    - C1 Entry trigger 정의 (§2.0 신규)
    - C2 Hard SL 수식 (§5.0 신규, avg_entry - 2×ATR)
    - C3 Layer 가격 공식 (§2.1 표)
    - C4 A/B/C sub-state 흐름 (§3 표 + §5.1)
    - C5 Parity 기준 완화 (§7.3)
  - **High (H6~H13)**: Triple Confluence 평가 시점 / Reverse Spike 수식 / EVASION peak / CVD 부호 / "제한적 실행" 삭제 / cur_lev 출처 / POC bin + Fibo pivot / LTF fractal length.
  - **Medium (M14~M17)**: Runner 내 A/B/C 비활성 / L3 부분 체결 처리 / state.json 파일명 / Runner 청산 쿨다운.
  - **Low (L18~L20)**: Maker rejection 재시도 / CVD UTC 리셋 / jsonl nullable.
  - **방향성 불변 (확인됨)**: 7:3 비대칭 / Layered 평균가 하향 / Triple Confluence 희소 승급 / Runner 대승 보호 — 24건 모두 이 4원칙 위에서 수치·공식 선택. 원칙 훼손 없음.

## Appendix C. 빈틈 매핑

- **Part 2 24건 (v5에서 해결)**: Critical 3 / High 9 / Medium 5 / Low 7.
- **v5 리뷰 24건 (v5.1에서 해결)**: Critical 5 / High 8 / Medium 4 / Low 3 — Appendix B 참조.
## Appendix D. v5.2 Addendum

- **v5.2**: SPEC Gap 2건 명시만 추가, 방향성 변경 없음.
  - Gap A: Dynamic VP volume allocation = close-price single-bin.
  - Gap B: Fibo anchor는 시간 순서 검증을 전제로 사용한다.
    - Long: `pivot_low_ts < pivot_high_ts`
    - Short: `pivot_high_ts < pivot_low_ts`
    - fallback 100캔들 H/L 포함 시 시간 순서 검증은 통과로 간주
    - 시간 순서 불일치 시 해당 bar Layered Entry 가격 계산은 skip 후 다음 bar 재평가
## Current Accepted Profile Addendum (2026-04-25)

- Source of truth: `mts_profile.py`.
- Accepted profile: `15m/core5/symbol-RSM`, HTF `4h`, execution TF `15m`, Pine-LTF CVD mode.
- Accepted symbols: `BTC/ETH/SOL/XRP/BNB`; DOGE is historical/experimental only and is excluded from the accepted MTS-V1 profile because it did not pass the trade-count/avgRR gates.
- Symbol RSM map: `BTC=6.3, ETH=6.8, SOL=5.5, XRP=6.3, BNB=2.5`.
- Replay parity note: Python replay must model Pine-equivalent contract quantity (`equity_fraction / order_price`) for layer fills and pending L2 promotion size. `L2_PROMO` is treated as additional L2 quantity for average entry, does not replace the L2 Hard SL, and must be included before L3 aggregate-fill recognition.
- Live-readiness note: MMR leverage cap and daily max-loss fail-closed behavior remain pending production validation. Current accepted results are backtest/parity artifacts only, not a live-ready approval.
