# MTS-V1 Codex 지시서 — 남은 구현 (Phase 3~7 + SPEC Gap)

**작성일**: 2026-04-24
**작성자**: Claude (설계·리뷰)
**수행자**: Codex (구현)
**전제**: Phase 0~2 완료 (REPORT.md 기준). Phase 2 parity 16지표 3dp match 확인됨.

---

## 0. 절대 불변 원칙 (모든 Brief 공통)

1. **7:3 비대칭** — 승률 30%대 × 평균 RR ≥ 2.5 × tail winner 최대화
2. **Layered 평균가 하향** — L1/L2/L3 점진적 깊이, 평균가 자연 하향
3. **Triple Confluence 희소 승급** — 0.2×ATR 임계, L2 전용, 5%→10% 승급
4. **Runner 대승 보호** — Kijun break 단일 청산 (Runner state에서 A/B/C/Hard SL/EVASION 비활성)

**방향성·맥락·목표·전략 변경 금지**. SPEC_V5.md는 읽기 전용. SPEC 조항과 불변 원칙이 충돌한다고 느끼면 구현 중단하고 `REPORT.md`에 "Principle conflict: <조항>" 기록 후 Claude 의견 대기.

---

## 공통 검증 요구 (모든 Brief 완료 조건)

1. `ruff check .` — 에러 0
2. `mypy --strict strategy.py` — 에러 0 (Windows Smart App Control 비활성 필요)
3. `python strategy.py --mode indicator-check` — 기존 parity 표 재현
4. Phase별 단위 테스트 (pytest) — 해당 Brief 요구 항목 참조
5. `REPORT.md`에 Phase 체크리스트 업데이트

**모든 배치는 파일 5개 제한**. 초과 시 분할 커밋.

---

## Brief #1 — Phase 3: State Machine (1.5일)

### 배경
Phase 2에서 지표 계산 완료. 이제 State 0~5 + sub-state 3.A/3.AB 전이 로직을 구현한다. 이것이 전략의 뼈대로, 이후 Phase 4/5/6이 여기에 붙는다.

### SPEC 참조 (엄수)
- §3 State Machine 전이 표
- §3.1 State 2 Abort 조건 (Reverse Spike 수식 + HTF 관통)
- §3.2 EVASION 조건 (peak 기준, (1) AND (2))
- §2.0 Entry trigger (State 0 → 1)
- §2.1 Layered Entry 33/33/34
- §2.2 Triple Confluence (L2 체결 직후 1회 평가)
- §2.3 LTF CVD Divergence (참고 게이트, blocker 아님)

### 구현 요구사항

#### Python (`strategy.py`)
- `class StateMachine` — State 전이 책임자
  - `evaluate_entry_trigger(bar, prev_bar, htf_bar, btc_ema_htf, cvd_30m) → bool`
  - `place_layers(avg_fill_fn, atr, poc, kijun, fibo_0618, fibo_0786, val) → list[LayerOrder]`
  - `on_l1_fill()`, `on_l2_fill()`, `on_l3_fill()` — state 전이 + avg_entry 갱신 + triple_confluence 1회 평가
  - `check_state_2_abort(reverse_spike, htf_cross) → bool`
  - `check_evasion(peak_mfe, atr, reverse_spike, htf_cross, hours_since_fill) → bool`
  - `check_state_1_timeout(bars_elapsed) → bool` (48 bars)
- `TripleConfluence` 평가는 **L2 체결 확정 entry_tf 바의 close 시점 1회**만. L1/L3에서 평가·저장 금지.
- `triple_confluence=True` 시 sizing_frame 0.05 → 0.10 승급 (L2 재사이징 4.11%, L3 4.24%; L1은 1.65% 고정).
- L3 부분 체결 중 승급 시: 부분 체결분 유지 + 잔여 pending 취소 + 10% 프레임 차분 재주문 (client_order_id 신규).

#### Pine (`strategy.pine`)
- `var int state = 0`, `var string sub_state = ""` 선언 (이미 있음).
- State 전이 주요 지점:
  - State 0 → 1: Entry trigger AND (2.0) — `strategy.order` L1 Limit post-only
  - State 1 → 2: L1 체결 확인 (strategy.position_size 변화) → L2 Limit 발주
  - State 2 → 3: L3 체결 확인
  - State 2 → 0 (Abort): Reverse Spike OR HTF 관통 → `strategy.close_all` + `strategy.cancel_all`
  - State 1 → 0 (Timeout): 48h 경과 → `strategy.cancel_all`
- Pine `strategy.order(id, direction, qty, limit=price)` maker limit으로 L1/L2/L3 발주.
- Triple Confluence 평가: L2 체결 직후 1회 (`barstate.isconfirmed` + 이전 bar에 L2 체결 사인) → `var bool triple_confluence_long`.

### 금지 사항
- State 3에서 조건 A/B/C 로직은 구현하지 말 것 (Phase 4 담당).
- Hard SL 계산은 구현하지 말 것 (Phase 5 담당).
- Runner state(4) 로직은 구현하지 말 것 (Phase 6 담당).
- Phase 3에서는 **State 전이 + Layered Entry + Triple Confluence + Abort + EVASION + Timeout**까지만.

### 검증
- `pytest tests/test_state_machine.py::test_entry_trigger_long` — Long 진입 조건 4가지 AND 성립 시 State 0 → 1 전이
- `pytest tests/test_state_machine.py::test_triple_confluence_gate_rare` — 0.2×ATR 임계 이내/초과 각 1케이스
- `pytest tests/test_state_machine.py::test_state_2_abort_reverse_spike` — delta_bar < -3×SMA(|delta|, 20) 충족 시 Abort
- `pytest tests/test_state_machine.py::test_evasion_peak_and_reverse` — (1) AND (2) 모두 충족 시 EVASION
- `pytest tests/test_state_machine.py::test_state_1_timeout_48h` — 48 bars 초과 시 Abort
- Pine 수동 차트 테스트: TradingView에서 BTC 1H 최근 3개월 데이터로 State 전이 로그 확인

### 완료 기준
REPORT.md Phase 3 체크리스트 전원 완료 + 단위 테스트 5개 PASS + Pine 차트 실행 시 State 전이 로그 생성.

---

## Brief #2 — Phase 4: TP A/B/C (1일)

### 배경
State Machine이 완료되면 State 3 (FILLED_FULL)에서 청산 조건을 구현한다. Hard SL은 Phase 5이지만 TP A/B/C 우선순위 처리는 Phase 4에서 완결.

### SPEC 참조
- §5.1 TP 우선순위 (sub-state 흐름 트리)
- §5.2 조건 A (RSI < 55 AND Kijun 기울기 ≤ 0 2연속)
- §5.3 조건 B (Fibo 1.0 도달)
- §5.4 조건 C (Fibo 1.5 AND volume > SMA(20) × 1.5)
- §4.2 Triple Confluence 승급 후에도 TP 로직 동일 (sizing만 다름)

### 구현 요구사항

#### Python
- `TPEvaluator`:
  - `evaluate_a(rsi, kijun_series) → bool` — 2연속 기울기 + RSI
  - `evaluate_b(price, fibo_1_0) → bool`
  - `evaluate_c(price, fibo_1_5, volume, volume_sma_20) → bool`
- `StateMachine.on_tp_a()`: 50% market close → State 3 → 3.A (A lock — 재발화 금지)
- `StateMachine.on_tp_b()`:
  - State 3에서 발화: 50% market close → 3.AB (B lock, A lock 아님 → A 더 이상 평가 안 함)
  - State 3.A에서 발화: 잔여 50%의 50% → 3.AB
- `StateMachine.on_tp_c()`:
  - `use_runner == true`: State → 4 (Runner, 잔여 전량 유지)
  - `use_runner == false`: 잔여 전량 market close → State 0
- TP 평가 우선순위: **같은 bar에 여러 조건 동시 충족** 시 A → B → C 순으로 1회씩만 처리. C hit 후 runner 승급이면 A/B 평가 중단.

#### Pine
- `strategy.close(id, qty=...)` 또는 `strategy.order("TP_A_CLOSE", strategy.short, qty=...)` (역방향)으로 부분 청산.
- Sub-state는 `var string sub_state = ""` 문자열로 추적 (`""`, `"A"`, `"AB"`).
- TP 평가는 `barstate.isconfirmed` 시점에서.

### 금지 사항
- Runner state(4)에서 TP A/B/C 평가 금지 (§6.2 비활성).
- TP 조건 A/B/C 동시 충족 시 동일 bar에서 모두 처리하지 말고 우선순위에 따라 1개만.
- Hard SL 체크는 여기서 안 함 (Phase 5).

### 검증
- `pytest tests/test_tp.py::test_tp_a_triggers_state_3_to_3a` — A 발화 후 sub_state == "A", 50% 청산
- `pytest tests/test_tp.py::test_tp_b_from_3_skips_a` — State 3에서 B 직접 발화 시 sub_state == "AB"
- `pytest tests/test_tp.py::test_tp_c_runner_enabled` — C 발화 + use_runner=True → State 4
- `pytest tests/test_tp.py::test_tp_c_runner_disabled` — C 발화 + use_runner=False → State 0
- `pytest tests/test_tp.py::test_tp_priority_same_bar` — A/B/C 동시 충족 시 A만 실행, B/C는 다음 bar

### 완료 기준
TP 단위 테스트 5개 PASS + REPORT.md Phase 4 체크리스트 전원 완료.

---

## Brief #3 — Phase 5: Hard SL (0.5일)

### 배경
Hard SL은 Layered Entry 기반이라 avg_entry 재계산이 핵심. L1→L2, L2→L3 체결마다 avg_entry + Hard SL 갱신. Triple Confluence 승급 후에도 avg_entry는 체결가 기준 (사이징만 변화).

### SPEC 참조
- §5.0 Hard SL 수식 (`avg_entry - 2 × ATR(entry_tf, 14)`)
- §4.3 hard_sl hit 시 24h 쿨다운
- §5.1 Hard SL이 TP A/B/C보다 우선 (트리 맨 위)

### 구현 요구사항

#### Python
- `Position.compute_avg_entry() → float`:
  - `Σ(fill_price_i × fill_qty_i) / Σ(fill_qty_i)` (체결된 L1~L3 가중평균)
- `Position.compute_hard_sl(atr_entry_tf) → float`:
  - Long: `avg_entry - 2 × atr`
  - Short: `avg_entry + 2 × atr`
- `on_l2_fill()`, `on_l3_fill()` 콜백에서 avg_entry + Hard SL 재계산 → 기존 stop order cancel + replace (client_order_id 신규).
- Hard SL hit 판정: 매 bar에서 `low ≤ hard_sl` (Long) / `high ≥ hard_sl` (Short) 시 **시장가 전량 청산** → State 0 + 24h 쿨다운 설정.

#### Pine
- `strategy.exit(id, stop=hard_sl_price)` — hard_sl 갱신 시 기존 exit 취소 후 재설정.
- Pine 쿨다운: `var int last_hard_sl_ts` + `timenow - last_hard_sl_ts < 24 * 60 * 60 * 1000` 체크로 신규 entry trigger 차단.

### 금지 사항
- Runner state(4)에서 Hard SL 평가 금지 (§6.2).
- avg_entry 계산에 Triple Confluence 승급 후 추가된 수량을 다른 가격으로 계산하지 말 것 (L2/L3 실제 체결가 그대로).

### 검증
- `pytest tests/test_hard_sl.py::test_avg_entry_after_l2_fill` — L1+L2 체결 후 가중평균 확인
- `pytest tests/test_hard_sl.py::test_hard_sl_recalc_after_l3` — L3 체결 후 avg_entry 하향 → Hard SL 하향 확인
- `pytest tests/test_hard_sl.py::test_hard_sl_hit_triggers_cooldown` — Hard SL hit 시 쿨다운 24h 설정
- `pytest tests/test_hard_sl.py::test_rr_at_least_2_5` — 2×ATR Hard SL 대비 Fibo 1.0 거리 ≥ 2.5 (typical atr/fibo 배치 샘플)

### 완료 기준
Hard SL 단위 테스트 4개 PASS + REPORT.md Phase 5 체크리스트 완료.

---

## Brief #4 — Phase 6: Runner (0.5일)

### 배경
Runner는 tail winner 포착의 핵심. TP C hit + use_runner=true 시 진입, Kijun 2연속 이탈 시 청산. Runner 내 모든 다른 청산 조건은 비활성.

### SPEC 참조
- §6 Runner (전 섹션)
- §6.1 진입: State {3 | 3.A | 3.AB} → 4
- §6.2 비활성 규칙: A/B/C, Hard SL, EVASION 모두 비활성
- §6.3 청산: entry_tf(1H) Kijun 2연속 이탈 (`close[t-1] < Kijun[t-1]` AND `open[t] < Kijun[t]`)
- §6.4 청산 후 24h 쿨다운

### 구현 요구사항

#### Python
- `class RunnerHandler`:
  - `check_kijun_break(close_prev, open_cur, kijun_prev, kijun_cur) → bool`
  - `on_kijun_break()`: 시장가 전량 청산 → State 4 → 0 + 24h 쿨다운
- `StateMachine.tick()`:
  - State == 4 (Runner)인 경우 **RunnerHandler만 호출**. TPEvaluator, HardSL, EVASION 호출 금지.
- 쿨다운은 Phase 5의 `CooldownManager`와 공유 (hard_sl과 동일 저장소).

#### Pine
- `state == 4`에서 Kijun 2연속 이탈 체크 → `strategy.close_all(comment="RUNNER_KIJUN_BREAK")`
- 쿨다운: `var int last_runner_exit_ts` + 24h 체크.

### 금지 사항
- Runner state(4)에서 TPEvaluator 호출 절대 금지.
- Runner state에서 Hard SL·EVASION 평가 절대 금지.
- Runner 진입 시 잔여 포지션의 추가 부분 청산 금지 (전량 유지).

### 검증
- `pytest tests/test_runner.py::test_enter_runner_from_tp_c` — TP C + use_runner → State 4
- `pytest tests/test_runner.py::test_runner_ignores_tp_abc` — Runner에서 A/B/C 조건 충족해도 state 유지
- `pytest tests/test_runner.py::test_runner_ignores_hard_sl` — Runner에서 Hard SL 조건 충족해도 state 유지
- `pytest tests/test_runner.py::test_kijun_2bar_break_closes` — 2연속 이탈 시 State 4 → 0 + 24h 쿨다운
- `pytest tests/test_runner.py::test_kijun_1bar_break_no_exit` — 1bar만 이탈하면 state 유지

### 완료 기준
Runner 단위 테스트 5개 PASS + REPORT.md Phase 6 체크리스트 완료.

---

## Brief #5 — Phase 7: Ops + Parity + Backtest Criteria (1.5일)

### 배경
Phase 3~6 완료 후 실전·페이퍼 운영 요건과 검증 가능 상태로 마무리. Parity 검증(Pine vs Python)이 이 Phase의 핵심.

### SPEC 참조
- §7.1 Persistence (state.json 스키마, 파일명 규칙)
- §7.2 Idempotency (client_order_id)
- §7.3 Parity Check 기준 (85% / 5%p / 15% / 90%)
- §7.4 Trade Log jsonl + Null 정책
- §7.5 Backtest Criteria 6항목 AND + walk-forward
- §7.6 Ops Robustness (Maker rejection, CVD UTC, State 복구)

### 구현 요구사항

#### Python
- `PersistenceManager`:
  - `save_state(symbol, state_dict)` → `state/state_<slug>.json`
  - `load_state(symbol) → dict | None`
  - `symbol_slug(symbol)`: `BTC/USDT:USDT` → `BTC_USDT_USDT`
- `TradeLogger`:
  - `append(event_dict)` → `logs/trades_<date>.jsonl`
  - Null 정책 준수 (Runner 미발동 trade에서 runner_exit_price=null, EVASION 미발동에서 evasion_reason=null 등)
- `OrderManager`:
  - `client_order_id = f"mtsv1_{slug}_{state_from}{state_to}_{ts_ms}"`
  - Maker rejection (post-only 거부) 시 방향 반대로 1 tick 조정 후 재주문, 최대 3회
- `StartupReconciliation`:
  - 프로세스 시작 시 `state.json` 로드 → `ccxt.fetch_positions()` + `fetch_open_orders()` 비교 → 불일치 시 **사용자 알림** (로그 WARN + exit code 2). 자동 수정 금지.

#### `parity_check.py` (신규)
- Pine 백테스트 결과 (TradingView export CSV) + Python 백테스트 결과 (trade log jsonl) 비교.
- 지표 항목:
  - 시그널 발화 타이밍 일치율 (entry signal timestamp ±1 bar 허용) → ≥ 85%
  - 24h window별 승률 차이 → ≤ 5%p
  - 평균 RR 차이 → ≤ 15%
  - CVD 부호 일치율 (bar 단위) → ≥ 90%
- 미달 항목은 `parity_report.md`에 원인 후보 기록.

#### `backtest_runner.py` (신규)
- 6자산 × 90d × entry_tf 1H 로컬 백테스트
- 산출:
  - 6-metric 표 (Sharpe, PF, MDD, trades, Wilson CI lower, 평균 RR)
  - walk-forward 4 window (시간축 기반, trade timestamp 필수)
- 통과 판정: 6항목 AND + walk-forward ≥ 2 window (1~3 AND 5) 개별 충족
- 결과: `BACKTEST_VERDICT.md` 생성 — PASS/FAIL + 실패 항목 원인

### 금지 사항
- State 복구 시 자동 수정 금지 (사용자 알림만).
- Trade log의 Runner/EVASION 관련 필드를 없는 event에서 0이나 ""로 채우지 말 것 (null 유지).

### 검증
- `pytest tests/test_persistence.py` — save/load round-trip + slug 변환
- `pytest tests/test_trade_log.py::test_null_policy` — Runner 미발동 trade에서 runner_exit_price=null 확인
- `pytest tests/test_order_manager.py::test_maker_rejection_retry_3x` — 3회 재시도 후 포기
- `python parity_check.py --pine <tv_export.csv> --py <trades.jsonl>` → parity_report.md 생성 + 4항목 통과/미달 표시
- `python backtest_runner.py --config config.yaml --days 90` → BACKTEST_VERDICT.md 생성

### 완료 기준
- Phase 7 단위 테스트 PASS
- `parity_check.py` 실행 가능 + 기본 샘플 데이터 통과
- `BACKTEST_VERDICT.md` 생성 (PASS 여부 무관, 생성 자체가 Phase 완료 증거)
- REPORT.md Phase 7 체크리스트 완료

---

## Brief #6 — SPEC v5.2 Gap 대응 (Phase 2 리뷰 후속, 0.5일)

### 배경
Phase 2 리뷰에서 식별된 SPEC Gap 2건을 방향성·목적 유지 관점에서 명시한다. 전략 변경 아님 — **미명시 세부를 명시로 확정**.

### Gap A: Volume Profile volume 분배 방식 (SPEC §1.2)

#### 문제
현 구현: 각 bar의 volume을 close 가격 단일 bin에 적재 (close-single-bin allocation).
SPEC §1.2: "POC/VAH/VAL (entry_tf rolling 500 캔들, **bins = 50**)" — 분배 방식 침묵.
Pine과 Python 모두 동일 방식이므로 parity는 문제 없으나, SPEC 명시 부재로 추후 구현자가 high-low 구간 분배로 해석할 가능성.

#### 방향성 근거 (변경 없음)
- 불변 원칙 3 (Triple Confluence 희소 승급) 관점: close-single-bin은 **특정 가격대에 집중된 거래 흔적**을 선명하게 만들어 POC를 좁게 응집. Triple Confluence 희소성 강화 부합.
- High-low 구간 분배는 POC를 평탄화 → Triple Confluence 발화 빈도 과잉 증가 (noise).

#### 조치
- `SPEC_V5.md` §1.2 표에 다음 줄 **추가만** (기존 조항 수정 금지):
  ```
  Dynamic VP | POC/VAH/VAL (entry_tf rolling 500 캔들, bins = 50, price range = window high-low,
                            **volume 분배: close 가격 단일 bin에 적재**) | L1 Limit, Triple Confluence POC
  ```
- Appendix B에 v5.2 항목 추가:
  ```
  - **v5.2**: SPEC Gap 2건 명시화 (방향성 유지)
    - Gap A: Volume Profile volume 분배 방식 = close-single-bin (희소 승급 원칙 부합)
    - Gap B: Fibo anchor pivot 시간 순서 조건부 검증 (§2.1/§5.3/§5.4 보완)
  ```
- `strategy.py` / `strategy.pine` **구현은 불변** (이미 close-single-bin).

### Gap B: Fibo pivot 시간 순서 조건부 검증 (SPEC §2.1 / §5.3 / §5.4)

#### 문제
현 구현 (`strategy.py` 555-582 근처 `latest_fibo_anchor`): Pivot H/L 중 가장 최근 것을 각각 선택. **시간 순서 검증 없음**.
Long 진입에서 `pivot_low → pivot_high` 순서로 상승 레그가 있어야 Fibo retracement/extension이 의미 있음. 역전되면 L2/L3 체결·TP B/C의 가격 거리가 SPEC 의도와 어긋남.

#### 방향성 근거 (변경 없음)
- 불변 원칙 2 (Layered 평균가 하향) 관점: Long 진입 시 pivot_low가 pivot_high보다 과거여야 자연스러운 상승 레그 되돌림 = L2/L3 깊은 체결 의미.
- 역전 케이스: 하락 레그 중인데 Long 진입하는 부정합 상황 → 이미 Entry trigger (§2.0)에서 HTF·Kijun 편향으로 차단되어야 함. 시간 순서 검증은 이중 안전장치.

#### 조치
- `strategy.py`에 pivot 시간 순서 검증 함수 추가:
  ```python
  def validate_fibo_anchor_temporal(
      pivot_high_ts: int | None,
      pivot_low_ts: int | None,
      side: TradeSide,
  ) -> bool:
      """Long: pivot_low → pivot_high (상승 레그). Short: pivot_high → pivot_low.
      둘 중 하나라도 fallback(100-bar H/L)이면 통과 (시간 순서 미검증)."""
      if pivot_high_ts is None or pivot_low_ts is None:
          return True  # fallback 케이스
      if side == TradeSide.LONG:
          return pivot_low_ts < pivot_high_ts
      else:
          return pivot_high_ts < pivot_low_ts
  ```
- `place_layers`에서 `validate_fibo_anchor_temporal` 호출 → False 시 **Layered Entry 건너뛰고 다음 bar 재평가** (entry abort 아님, 단순 skip).
- Pine: `ta.pivothigh`/`ta.pivotlow`는 내부적으로 bar_index 반환하므로 `pivot_high_bar`/`pivot_low_bar` 변수로 시간 순서 비교 가능. 해당 bar_index 미확정(fallback 경로) 시 통과.
- `SPEC_V5.md` §2.1에 pivot 시간 순서 조건부 검증 조항 추가 (Appendix B v5.2 포함).

### 검증
- `pytest tests/test_fibo_anchor.py::test_temporal_order_long_valid` — pivot_low < pivot_high ts → True
- `pytest tests/test_fibo_anchor.py::test_temporal_order_long_inverted` — pivot_high < pivot_low ts → False → entry skip
- `pytest tests/test_fibo_anchor.py::test_temporal_order_fallback` — pivot_high None → True (통과)
- `python strategy.py --mode indicator-check` 재실행 → parity 표 재현 (Fibo 값은 동일, 단 entry skip 카운터 추가)

### 금지 사항
- SPEC의 **기존** 조항 수정 금지. 추가만.
- Fibo 수식 자체 변경 금지 (0.618/0.786/1.0/1.5 그대로).
- Entry trigger (§2.0) 조건 수정 금지. 시간 순서는 `place_layers` 단계에서만 적용.

### 완료 기준
- `SPEC_V5.md` v5.2 업데이트 완료
- Pine/Python 시간 순서 검증 구현 + 단위 테스트 3개 PASS
- REPORT.md에 "Phase 2 후속 SPEC Gap 대응 완료" 섹션 추가
- `ruff check .` + `mypy --strict strategy.py` 통과

---

## 전체 작업 순서 (Codex 권장 수행 순서)

```
Brief #6 (SPEC Gap 명시) → SPEC v5.2 확정 후 이후 Phase들이 v5.2 기반으로 진행
  ↓
Brief #1 (Phase 3: State Machine) → 뼈대 구축
  ↓
Brief #3 (Phase 5: Hard SL) → State 3에서 최우선 청산 조건 먼저
  ↓
Brief #2 (Phase 4: TP A/B/C) → Hard SL 이후 sub-state 청산
  ↓
Brief #4 (Phase 6: Runner) → TP C의 분기로 자연 연결
  ↓
Brief #5 (Phase 7: Ops + Parity + Backtest) → 모든 Phase 통합 검증
```

**권장 이유**: Hard SL은 TP 트리의 최상위 우선순위 (§5.1). 이를 Phase 4보다 먼저 구현하면 Phase 4에서 TP A가 Hard SL을 덮지 않는지 자연스러운 회귀 방지.

---

## Evidence & 보고

각 Brief 완료 시 `REPORT.md`에 다음 섹션 추가:

```markdown
## Brief #N 완료 (YYYY-MM-DD)
- [x] <체크리스트 항목>
- 단위 테스트: N passed
- ruff: 0 errors
- mypy --strict: 0 errors
- Pine 차트 테스트: (확인 내용)
- Principle conflict: (발견 시 기록)
```

**Principle conflict 발생 시 즉시 중단 + REPORT.md 기록 + Claude 알림.** 독단 판단 금지.

---

## Windows 환경 유의사항

- `python -m ruff check .` / `python -m mypy --strict strategy.py` (PATH 미등록 시 모듈 호출)
- mypy 네이티브 .pyd 로드 차단은 Smart App Control 비활성화로 이미 해결 (2026-04-24).
- Pine 개발은 TradingView 웹에서 직접 편집·테스트 (로컬 실행 환경 부재).

---

**지시서 종료**. 다음 Codex 세션 시작 시 `Brief #N 진행 중` 한 줄을 REPORT.md에 먼저 기록하고 작업 개시.
