# Codex 착수 지시서 — MTS-V1 (Triple Confluence Runner)

**작성일**: 2026-04-24
**Spec 버전**: v5.1 (파일: `SPEC_V5.md`, 내부 `version: v5.1`)
**요청자**: Claude (설계·리뷰)
**수행자**: Codex (구현)

---

## 0. 불변 원칙 (모든 Phase에서 유지)

1. **7:3 비대칭** — 승률 30%대 × 평균 RR ≥ 2.5 × tail winner 최대화
2. **Layered 평균가 하향** — L1/L2/L3가 점진적으로 깊어져야 함
3. **Triple Confluence 희소 승급** — 흔한 수렴에서 발화 금지, 2차 전용·0.2×ATR 유지
4. **Runner 대승 보호** — Kijun break 단일 청산 (A/B/C/Hard SL/EVASION 비활성)

**구현 중 Spec 조항과 위 원칙이 충돌한다고 느끼면** — Spec 먼저 의심하지 말고 `REPORT.md`에 "Principle conflict: <조항>" 기록 후 Claude 의견 대기.

---

## 1. 목표

`SPEC_V5.md` (v5.1) 명세에 따라 **동일 전략의 2-구현 쌍** 작성:

- `strategy.pine` — Pine Script v5 (TradingView 백테스트)
- `strategy.py`   — Python CCXT (Binance USDT-M Perpetuals 실전/페이퍼)

두 구현은 동일 로직·파라미터. Parity 기준은 §4 참조 (v5.1에서 85% + CVD 부호 90%로 완화).

---

## 2. 작업 파일 & 경로

### 2.1 생성/수정 허용 (이 디렉터리 한정)

```
Projects/Trading Value/MTS-V1/
  SPEC_V5.md              (읽기 전용 — 변경 요청 시 Claude에 보고)
  REVIEW_FOR_CODEX.md     (이 문서, 읽기 전용)
  strategy.pine           (신규)
  strategy.py             (신규)
  config.yaml             (신규 — symbols, risk, TF, user_leverage, mmr 심볼별)
  state/                  (신규 디렉터리)
    state_BTC_USDT_USDT.json  (심볼별 1 파일)
    state_ETH_USDT_USDT.json
    ...
  state.json.example      (신규 — 스키마 샘플, §7.1)
  parity_check.py         (신규)
  REPORT.md               (신규 — Phase 진행 보고)
  BACKTEST_VERDICT.md     (Phase 7 완료 시 생성)
```

### 2.2 금지 구역 (건드리지 말 것)

- `Projects/Trading Value/scripts/`  — 기존 v3, Oracle
- `Projects/Trading Value/data/`     — 기존 데이터
- `Projects/Trading Value/predictive_runner_paper/` — 별도 실험
- 그 외 `Projects/Trading Value/` 직하 파일

이 전략은 `MTS-V1/` 독립 self-contained. 기존 인프라 의존 금지.

---

## 3. 구현 순서 (Phase)

각 Phase 종료 시 `REPORT.md`에 체크리스트 업데이트 + Rule 4 자체 검증 (`mypy`, `ruff`).

### Phase 1 — 스켈레톤 & Config (½일)

- [ ] `config.yaml`:
  - `symbols`: ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT", "BNB/USDT:USDT", "DOGE/USDT:USDT"]
  - `risk.daily_max_loss_pct`: 5
  - `risk.symbol_cooldown_hours`: 24 (hard_sl / Runner exit / EVASION 공용)
  - `user_leverage`: 10 (default)
  - `mmr`: 심볼별 dict (Binance Perpetual 고시값)
  - `use_runner`: true
  - TF: `htf: "4h"`, `entry_tf: "1h"`, `ltf: "15m"`
- [ ] `state.json.example`: §7.1 스키마 전체 필드 (avg_entry, hard_sl, sub_state, sizing_frame 포함)
- [ ] `state/` 디렉터리 생성 + `.gitignore`에 `state/state_*.json` 추가 (실전 상태 커밋 방지)
- [ ] `strategy.py` 모듈 구조: Entry / State / Exit / Ops 섹션
- [ ] `strategy.pine` strategy() 선언, input 매개변수: user_leverage, mmr (심볼별 input), use_runner

### Phase 2 — 지표 계산 (1일)

- [ ] `ATR(entry_tf, 14)` — Wilder's ATR (Pine `ta.atr(14)` on 1H 차트)
- [ ] `Ichimoku (9, 26, 52)` — Kijun_sen 핵심, entry_tf 기준
- [ ] `POC/VAH/VAL` on entry_tf rolling **500 캔들**, **bins=50**, price range = window high-low
- [ ] `Fibo Anchor`: Bill Williams 5-bar fractal (pivot_length=2) 최근 Pivot H/L 탐지, 없으면 최근 100캔들 H/L fallback
- [ ] `RSI(entry_tf, 14)` — Pine `ta.rsi(close, 14)`
- [ ] `Volume SMA(20)` — on entry_tf
- [ ] **CVD Proxy (Pine)**: `cumsum((close - open) × volume)`, **UTC 00:00 일별 리셋** (`ta.change(dayofyear)` 트리거)
- [ ] **CVD Trade Stream (Python)**: Binance WebSocket trade stream → buy/sell delta 누적, UTC 00:00 리셋
- [ ] **CVD Spike / Reverse Spike**: `|delta_bar| > 3 × SMA(|delta|, 20)` 탐지 + **delta 부호 보존** → `reverse_spike(side)` 함수 (롱/숏 분기)
- [ ] `BTC EMA(4H, 50)` — 대장주 HTF 편향 필터

**검증**: Phase 2 종료 시 각 지표를 1 bar에서 수동 계산 후 Pine/Python 값이 소수 3자리까지 일치하는지 확인 (CVD 제외).

### Phase 3 — State Machine (1.5일)

- [ ] State 0~5 + sub-state 3.A / 3.AB 전이 로직 (SPEC §3 표)
- [ ] **Entry trigger (SPEC §2.0)** 구현:
  - Long: HTF>BTC_EMA AND entry_tf close 첫 Kijun 돌파 AND 30m 누적 CVD>0 AND state==0
  - Short: 부호 반전
- [ ] State 1 Timeout: 48 bars on entry_tf = 48h (L1 Limit pending 48 bar 경과 미체결 시 cancel → state 0)
- [ ] State 2 Abort 조건: `reverse_spike(side) OR HTF(4H) 기준선 반대 관통` (첫 종가 기준)
- [ ] EVASION 조건 (§3.2): `(1) reverse_spike OR HTF 관통 AND (2) 48h peak 미실현수익 < ε` — peak 측정은 체결 후 tick마다 max 갱신
- [ ] 각 State 전이 시 trade log append (§7.4)

### Phase 4 — Entry & Sizing (1일)

- [ ] Layered Limit 33/33/34 maker-only (Binance `postOnly=true`, Pine `strategy.entry` 가격 지정)
- [ ] **Layer 가격 공식 (SPEC §2.1)**:
  - L1 (Long): `max(POC, Kijun_entry_tf) + 0.05 × ATR`
  - L2 (Long): `Fibo 0.618`
  - L3 (Long): `min(Fibo 0.786, VAL)`
  - Short: 방향 반전, 버퍼 부호 반전
- [ ] Triple Confluence 평가: **L2 체결 확정된 entry_tf 바의 close 시점 1회만** (H6 반영)
- [ ] L1·L3에서 triple_confluence 평가·기록 **금지** 유닛 테스트 추가
- [ ] Sizing 5% → 10% 승급 (§4.2):
  - L3 미체결 시: pending 전량 취소 → 10% 프레임 L3 재주문
  - L3 부분 체결 중: 부분 체결분 유지, 차분 수량만 재주문, client_order_id 신규
- [ ] Liquidation Safeguard (§1.3): `cur_lev = config.user_leverage`, mmr = ccxt 조회 (Python) / input (Pine) → effective_leverage 계산 후 주문 적용
- [ ] daily_max_loss (전 심볼 합산 equity 대비 -5%) → 신규 신호 차단 (UTC 00:00 리셋)

### Phase 5 — Exit Logic (1일)

- [ ] **Hard SL (SPEC §5.0)** — `avg_entry - 2 × ATR` (롱) / 부호 반전 (숏)
  - avg_entry = 체결된 layer의 fill_qty 가중평균
  - L2 체결 시, L3 체결 시, Triple Confluence 승급 후 L3 부분 차분 체결 시 — 각각 avg_entry 갱신 → Hard SL cancel+replace
  - 발동: 시장가 전량 청산 → State 0 → 24h 쿨다운
- [ ] TP A (SPEC §5.2): RSI<55 AND Kijun 기울기 ≤ 0 2연속 → 50% 시장가 청산 → State 3.A (A lock)
- [ ] TP B (SPEC §5.3): 가격 ≥ Fibo 1.0 → 잔여 50% 청산 → State 3.AB (B lock)
- [ ] TP C (SPEC §5.4): 가격 ≥ Fibo 1.5 AND volume > SMA(20)×1.5 → use_runner 분기 (전량 청산 or State 4)
- [ ] **Sub-state 흐름 (SPEC §5.1)** — 3 → 3.A → 3.AB → (C/Runner) 트리거 lock 매니지먼트
- [ ] Runner 청산 (SPEC §6.3): close[t-1]<Kijun AND open[t]<Kijun → 시장가 전량 청산 + 24h 쿨다운
- [ ] **Runner 내 TP A/B/C / Hard SL / EVASION 비활성** (M14): state==4에서 Kijun break만 평가

### Phase 6 — Ops & Logs (1일)

- [ ] Persistence: `state/state_{symbol_slug}.json` (M16)
- [ ] State 복구: 프로세스 시작 시 state.json 읽기 → Binance 포지션·주문 재조회 → 불일치 시 사용자 알림 후 state.json 우선 (자동 수정 금지)
- [ ] Idempotency: `client_order_id = f"mtsv1_{symbol_slug}_{state_from}{state_to}_{timestamp_ms}"`
- [ ] **Maker Rejection 재시도 (L18)**: post-only 거부 시 1 tick 불리한 방향 조정 후 재주문, 최대 3회. 초과 시 해당 layer 포기 (state 유지).
- [ ] **CVD UTC 00:00 리셋 (L19)** 구현 확인 — Phase 2 결과 재검증
- [ ] Trade log jsonl (§7.4 전체 필드, nullable 정책 L20 준수)
- [ ] `parity_check.py`: Pine 로그 export vs Python trade log 비교 — 타이밍 일치 %, 승률 차, RR 차, CVD 부호 일치 %

### Phase 7 — Backtest & Verify (2일)

- [ ] Python 백테스트: 12개월, 6 symbols, walk-forward 4 window (timestamp 기반 — order-based 금지)
- [ ] Sharpe / Profit Factor / MDD / trades/window / Wilson 95% CI lower / avg RR 계산
- [ ] SPEC §7.5 6항목 AND 판정
- [ ] Pine 백테스트: TradingView 수동 업로드 → 6 symbols 각각 실행
- [ ] `parity_check.py` 실행 → **v5.1 기준**:
  - 시그널 타이밍 일치 ≥ 85%
  - 승률 차 ≤ 5%p
  - avg RR 차 ≤ 15%
  - CVD 부호 일치 ≥ 90%
- [ ] `BACKTEST_VERDICT.md` 생성 (포맷: `subagent-runs/spec/oracle-v2-ablation-2026-04-21/ablation-verdict.md`)

---

## 4. 검증 기준 (Phase 7 최종)

### 4.1 전략 기준 (SPEC §7.5)

1. Sharpe ≥ 1.0
2. Profit Factor ≥ 1.3
3. MDD ≤ 20%
4. trades / walk-forward window ≥ 100
5. Wilson 95% CI lower > BE(RR) = 1 / (1 + avg_RR)
6. 평균 RR ≥ 2.5

**전체 PASS**: 1~6 모두 AND, 그리고 walk-forward 4 window 중 ≥ 2 window가 (1~3 AND 5) 개별 충족.

### 4.2 Parity 기준 (SPEC §7.3 v5.1)

- 시그널 타이밍 일치 ≥ 85%
- 승률 차 ≤ 5%p
- avg RR 차 ≤ 15%
- CVD 부호 (bar 단위) 일치 ≥ 90%
- CVD 값 일치: **비교 배제** (구조적 차이 인정)

**FAIL 시**: SPEC Gap 분석 → `REPORT.md`에 섹션 추가 → Claude 보고. 임의 파라미터 튜닝으로 수치 맞추기 **금지** (Rule 17~20 Root Cause First).

---

## 5. 재현 명령

```bash
cd "c:/Users/haj/projects/subagent-orchestrator/Projects/Trading Value/MTS-V1"

# 의존성
py -m pip install ccxt numpy pandas scipy pyyaml websocket-client

# 백테스트 (12개월, 6 symbols)
py strategy.py --mode backtest --symbols BTC,ETH,SOL,XRP,BNB,DOGE --months 12

# 페이퍼 트레이드 (실전 API 조회, 주문 시뮬만)
py strategy.py --mode paper --config config.yaml

# Parity check
py parity_check.py --pine-log pine_signals.csv --python-log data/trades.jsonl

# Pine 수동 실행:
#   1. strategy.pine → TradingView Pine Editor
#   2. 차트 TF = 1H (entry_tf 고정)
#   3. 심볼별 백테스트 → Strategy Tester CSV export
```

---

## 6. 보고 형식

### 6.1 Phase별 REPORT.md

매 Phase 완료 시 append (덮어쓰기 금지):

```markdown
## Phase N — <제목> (YYYY-MM-DD)

### 구현 (체크리스트)
- [x] / [ ]

### 검증
- mypy: (결과)
- ruff: (결과)
- 단위 테스트: (해당 시)

### SPEC Gap (발견된 것만)
- (없으면 "None" 명시)

### Principle Conflict (§0 4원칙 위반 의심 사항, 있으면만)
- ...

### 다음 Phase 진입 조건
- ...
```

### 6.2 Phase 7 BACKTEST_VERDICT.md

포맷: `subagent-runs/spec/oracle-v2-ablation-2026-04-21/ablation-verdict.md`

최소 섹션:
1. Verdict (PASS / FAIL / INCONCLUSIVE)
2. 데이터 요약 표
3. 6항목 AND 판정 표 (§4.1)
4. Walk-forward 4 window 분석
5. Pine vs Python Parity 결과 (§4.2)
6. 후속 조치 (Claude 승인 필요 항목)
7. 재현 명령
8. 요약 한 줄

---

## 7. SPEC 변경 프로토콜

구현 중 SPEC_V5.md와 gap 발견 시:

1. **임의 구현 변경 금지** (Rule 3 SENIOR DEV OVERRIDE는 "원 태스크와 직접 연관된 결함"에만 적용).
2. `REPORT.md`에 `### SPEC Gap: <내용>` 섹션 추가 — 현재 SPEC 조항 인용 + 발견된 ambiguity/누락/충돌 명시.
3. Claude에 보고, 결정 대기.
4. 결정 후 SPEC_V5.md 업데이트되면 버전 상향 (`v5.1` → `v5.2`), **파일명은 SPEC_V5.md 유지** (내부 버전 필드만 수정).

---

## 8. 규칙 준수 요약

- **Rule 4 FORCED VERIFICATION**: Phase 종료 시 `mypy strategy.py` + `ruff check .` 통과
- **Rule 6 CONTEXT DECAY**: 장기 작업이므로 Phase 진입 시 SPEC_V5.md 해당 섹션 재읽기
- **Rule 10 NO SEMANTIC SEARCH**: 리네이밍 시 6패턴 grep (호출/타입/문자열/import/re-export/mock)
- **Rule 17~20 ROOT CAUSE FIRST**: Backtest FAIL 시 표면 파라미터 조정 금지, "왜?" 연쇄 탐색 먼저
- **불변 원칙 (이 문서 §0)**: 모든 Phase에서 4원칙 유지. 위반 의심 시 REPORT에 Principle Conflict 기록.

---

## 9. Kickoff 체크리스트 (Codex 첫 세션)

- [ ] 본 문서 + SPEC_V5.md (v5.1) 통독
- [ ] 디렉터리 구조 확인 (§2.1)
- [ ] 금지 구역 확인 (§2.2)
- [ ] 불변 원칙 4가지 (§0) 숙지
- [ ] Phase 1 착수 선언: `REPORT.md` 생성 + `## Phase 1 진행 중 (YYYY-MM-DD)` 섹션
- [ ] 질문 있으면 착수 전 Claude에 문의 (구현 시작 후 발견 시 REPORT에 기록)
