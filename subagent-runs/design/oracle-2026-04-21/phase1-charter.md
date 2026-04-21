# Project Charter — Oracle 예측 엔진

**Date**: 2026-04-21
**Mode**: Design (Phase 1)
**Domain**: software (린 스코프)
**Previous Phase**: Phase 0 Intake (8인 토론 AGREE 조건부 수렴) → `subagent-runs/discuss/oracle-phase0-intake-2026-04-21/conclusion.md`

---

## Primary Outcome (핵심 품질 속성)

**Context-aware 예측 신뢰도 기반 수익 양수 달성.**

> 과거 예측 히스토리를 맥락(context)별로 분석하여 "어느 맥락에서 내 예측이 잘 맞았는지" 학습하고, 자신감 있는 맥락에서만 거래하여 5일 누적 +4% 이상 수익을 실현한다.

**핵심 시나리오**: OHLCV tick 수신 → 현재 context 계산 → 그 context에서의 과거 승률/신뢰도 조회 → 신뢰도 게이트 통과 시에만 예측 + 주문 실행 → 결과 피드백으로 context별 신뢰도 업데이트.

**정량 목표**: 승률 **69%+**, 5일 누적 수익률 **+6%+**, 최소 100+ trades 샘플 (신뢰도 통계 유의).

> **근거**: Trading Value 프로젝트 점수 체계(수익 +0.1 / 손실 -0.2, 비대칭 2배 패널티)의 손익분기 승률 67%에 대한 **+2%p 마진**. 5일 +6% 수익은 기존 프로젝트 목표(+4%) 대비 공격적 상향 — 자기설정 목표 "2주 66%"와 일관되게 Oracle은 엔진 전체가 이 기준 이하로 떨어지지 않도록 학습률·임계치를 자동 조정한다.

---

## Operating Loop (요청-처리 흐름)

**3레이어 순환 구조** (자기설정 목표 기반):

- **마이크로 (초~분)**: OHLCV tick → context 벡터 계산 (`predicted_edge, predictive_uncertainty, cost_margin, vol_regime, time_bucket`) → Bayesian reliability head 조회 → 신뢰도 ≥ 임계치 시 예측 생성 → EV-blacklist 체크 통과 시 주문 (observe-only / soft-gate / full 단계별)
- **미들 (시간~일)**: 체결 결과 수신 → online ridge/logistic 가중치 업데이트 (맞춤 강화, 틀림 소거) → Beta-Bernoulli/Normal-Gamma posterior 갱신 → 성능 미달 context는 blacklist 추가 (n_local ≥ 20 이후)
- **매크로 (주)**: Oracle vs V2 주간 승률/수익 비교 → **3주 연속 Oracle 우위 시 v2.py → `scripts/archive/` (선셋 조항 발동)** → 신뢰도 목표 갱신, 학습률 재조정

**매크로 루프 유형: 순환형.** 자기설정 목표 = **"2주 누적 승률 66% 유지"** (미달 시 학습률 재보정, 상회 시 임계치 상향).

---

## Baseline Expectations (기본 요구사항)

**포함** (조항 C, D, F, 일반 인프라):

1. **상태/로그 구조 일관성** — `data/oracle_state.npz` + `data/oracle_memory.json` + `data/oracle.jsonl`. V3/TriArb 실제 포맷(`*_state.npz + *_memory.json`) 준수 (Phase 0 "npz+jsonl 일관" 표현은 불완전했음, Codex A 확인).
2. **Dashboard 통합** — `scripts/dashboard_unified.py` MODELS dict에 `"oracle"` 키 추가. `renderOracle()` 함수 신규 작성 (하드코딩 구조 상 +25~40% 공수 인정).
3. **API SLA** — `/api/state` p95 500ms, hard ceiling 1s. Dashboard polling timeout 3초, refresh 5초 준수. (**조항 C**)
4. **공유 OHLCV collector/cache** — Oracle/V3/TriArb가 같은 심볼 OHLCV를 중복 fetch하지 않도록 공통 수집 레이어 도입. (**조항 D**)
5. **신규 포트 8901** — V2(8897)·V3(8898)·TriArb(8899)·Dashboard(8900)와 병행. (**조항 F**, 하단 미해결 이견 참조)
6. **Warmup 단계** — observe-only 150~200 trades → soft-gate 300~500 → full. blacklist 활성은 `n_local ≥ 20` 이후.
7. **네트워크** — 로컬 HTTP는 `127.0.0.1` 하드코딩 (Windows IPv6 timeout 회피).

**제외 및 대체** (조항 E, J):

- ❌ **Rule 2 (엔트로피 균등화)** — 학습 역방향 작동. → 대체: **Bayesian reliability head** (Beta-Bernoulli / Normal-Gamma posterior per context) + **EV-based blacklist**.
- ❌ **단일 선형 모델** (v2.py의 SGD ridge 단독) — context별 신뢰도 분화 불가. → 대체: **Online ridge/logistic + context-indexed reliability posterior**.
- ❌ **v2.py 덮어쓰기** (opus 초기 제안, Round 2에서 철회) — 롤백 불가. → 대체: **신규 `scripts/oracle.py` 분리 + 선셋 조항** — Oracle이 v2.py 대비 **3주 연속 주간 승률 우위 시 v2.py → `scripts/archive/`**. (**조항 E**)
- ❌ **v2.jsonl 문서 수치 -13.13%** — 실제 -10.97~-11.15%. → Phase 5 문서 생성 시 부록 J로 수치 정정 반영. (**조항 J**)

---

## Differentiation Thesis (아키텍처 차별점)

> **트레이딩 예측 엔진인데, ex-ante predictive edge + uncertainty + regime을 context별 Bayesian reliability posterior로 학습하기 때문에 "자신감 없는 시장에서는 거래하지 않는" 선택권이 생긴다.**

**V3와의 레이어 분리** (**조항 G**, 전원 합의):

- **V3 = setup quality / trade management** 학습 (`vwap_slope, ema_dist, vp_clearance, rr_estimate, hour, vol_regime`) — **meta-decision** (어느 setup을 선택할 것인가)
- **Oracle = ex-ante predictive edge / uncertainty / regime** 학습 (`predicted_edge, predictive_uncertainty, cost_margin, vol_regime, time_bucket`) — **signal-generation** (이 시점 예측이 신뢰할 만한가)

→ **V3 k-NN 틀은 재사용 가능, 6차원 context 좌표는 재설계 필수.** 같은 엔진 스택(numpy/pandas only, 비-LSTM)이지만 의미 공간이 다름.

**모델 골격** (**조항 A**, 전원 합의):

> **Online ridge/logistic** (point prediction) + **Bayesian reliability head per context** (Beta-Bernoulli for binary direction / Normal-Gamma for magnitude) + **EV-based context blacklist**.
>
> - 비-LSTM / 비-neural (현재 스택 제약 + 학습 해석가능성)
> - `numpy/pandas`만으로 구현
> - Warmup: observe-only 150-200 trades → soft-gate 300-500 → full. blacklist는 `n_local ≥ 20`부터 활성.

---

## Target Audience (사용자/클라이언트)

| 항목 | 결정 |
|------|------|
| 대상 사용자/이해관계자 | 사용자 1인 (자동매매 운영자) |
| 사용 환경 | Windows 11, Python 3.12, 로컬 단일 머신, ccxt + numpy + pandas (신규 의존성 금지) |
| 허용 복잡도 | 중 — 수학적 추상화(Bayesian posterior) 허용, 딥러닝 프레임워크(PyTorch/TF) 금지 |
| 기대 사용 빈도 | 24/7 무중단 운영, Dashboard 5초 refresh polling, 장애 시 즉시 v2.py 폴백 가능 |
| 핵심 제약 | 5일 내 Phase 4 "코딩 착수 가능" 선언, V3/TriArb 운영 무중단, API SLA p95 500ms |

---

## Charter 조항 10개 (A~J) 번역 매핑

| 조항 | 내용 | Charter 위치 | 다음 Phase 번역 |
|------|------|------------|----------------|
| **A** | Oracle 모델 골격 (online ridge/logistic + Bayesian reliability + EV blacklist) | Differentiation | Phase 2 컴포넌트 맵 + Phase 3 구현 결정 |
| **B** | 예측 타깃 / horizon / 점수함수 / confidence activation schedule | (Phase 3 전제) | **Phase 3 Decision Card 필수** |
| **C** | API SLA `/api/state` p95 500ms, hard 1s | Baseline 3 | Phase 3 구현 + Phase 4 검증 |
| **D** | 공유 OHLCV collector/cache | Baseline 4 | Phase 2 컴포넌트 `market-data-collector` |
| **E** | v2.py 신규 분리 + 선셋 조항 (3주 우위 시 archive) | Baseline 제외/대체 | Phase 2 + Phase 6 변경관리 |
| **F** | 포트 8901 신규 | Baseline 5 (**미해결**) | 하단 이견 참조 |
| **G** | V3 차별화 1문장 (setup vs prediction 레이어 분리) | Differentiation | — (확정) |
| **H** | 검증 기준 (CI, walk-forward, 최소 trade) | Operating Loop + 태스크 1번 | Phase 4 검증 통합 |
| **I** | 48시간 Rule 2 ablation | **Charter 태스크 1번** | 하단 섹션 참조 |
| **J** | v2.jsonl -11.15% 수치 정정 | Baseline 제외/대체 | Phase 5 문서 생성 시 반영 |

---

## Charter 태스크 1번: 48시간 Rule 2 Ablation Go/No-Go Gate (조항 I)

**배치**: Phase 1 Charter 확정 직후, Phase 2 Component Map 작성과 **병행 실행** 가능.

**목적**: V2 실패의 근본 원인이 Rule 2(엔트로피 균등화)인지 검증. 통과 시 Oracle 재설계 스코프 축소 가능, 미달 시 재설계 정당화.

**실행 환경**:
- **신규 `scripts/oracle.py` 격리** (v2.py live 환경 수술 금지)
- Oracle-w-Rule2 vs Oracle-wo-Rule2 2 variant 48시간 병행 observe-only + 일부 paper trades
- 기존 V2/V3/TriArb 운영에 영향 없음

**통과 기준** (6항목 전부 AND — 조항 H):

1. **수수료 후 순수익 양수**
2. **승률 95% CI lower bound > 50%** (Wilson score or Clopper-Pearson)
3. **Walk-forward 재현** — 2~5개 rolling window에서 통과 기준 일관성
4. **자산별 편차 허용 범위 내** — BTC/ETH/SOL 등 주요 심볼 간 승률 편차 ±5%p 이내
5. **Calibration monotone** — 신뢰도 버킷별 정확도가 단조 증가 (reliability diagram)
6. **최소 100+ trades** — 샘플 유의성 확보

**결과 분기**:
- **PASS** → V2에 수술적 수정(Rule 2 제거)만 적용. Oracle 재설계 스코프 축소 재검토. 사용자에게 Charter Tier 2 변경 제안.
- **FAIL** → Oracle 재설계 원안대로 Phase 2 진입.
- **INCONCLUSIVE** (일부 기준만 통과) → 추가 48시간 연장 1회 허용, 그래도 모호 시 FAIL 처리.

**측정 로그**: `data/oracle_ablation.jsonl` — 각 trade의 `(timestamp, variant, context, prediction, result, confidence, pnl_after_fee)` 기록.

---

## 미해결 이견 (Phase 2 이전 확정 필요)

### 1. 포트 즉시 확정 vs Phase 3 지연 (조항 F)

- **운영 sonnet + opus**: 즉시 8901 확정 (dashboard 통합 일정에 포트 번호가 상류 종속)
- **Codex B**: Phase 3까지 늦춰도 무방 (포트는 config 파라미터)
- **Charter 타협안**: **포트 8901 잠정 확정** + Phase 3에서 번복 가능 조항 추가. Phase 2 Component Map 작성 시 번복 트리거(예: dashboard 구조 리팩토링 필요)가 없으면 Phase 4에서 최종 확정.

### 2. BollRev 스코프 편입 경위 (반대 sonnet 지적)

- Phase 0 요약 어디에도 BollRev(Bollinger Reversion) variant 편입 근거 없음
- Oracle 기본 variant(control / aggressive / conservative) 외 BollRev 편입 이유 미설명
- **Charter 결정**: Phase 2 Component Map에서 Oracle variants 최종 목록 확정 시 BollRev 편입 여부 재평가. 편입 시 근거(예: "V3 aggressive variant 대응") Component Map에 명시 필수.

---

## Charter 일관성 검증 (11 체크리스트)

- [x] **Primary Outcome 1가지 확정** — Context-aware 예측 신뢰도 기반 수익 양수 달성
- [x] **3레이어 Operating Loop 한 문장씩** — 마이크로/미들/매크로 모두 정의
- [x] **Baseline 포함/제외 결정** — 포함 7개, 제외 4개 + 대체안 명시
- [x] **Differentiation Thesis 한 문장** — "ex-ante predictive edge + uncertainty를 context별 Bayesian posterior로 학습..."
- [x] **Target Audience 환경/제약 확정** — 5항목 표
- [x] **Primary Outcome ↔ Operating Loop 양립?** — 마이크로 context 조회 → 미들 posterior 업데이트 → 매크로 신뢰도 목표 갱신. 자기설정 목표가 Primary Outcome과 직결.
- [x] **Differentiation ↔ Baseline 모순 없음?** — Baseline 제외 항목(Rule 2, 단일 선형)이 Differentiation 대체안(Bayesian posterior, online ridge)으로 정합.
- [x] **Target 허용 복잡도 ↔ Primary Outcome 일치?** — numpy/pandas만으로 Bayesian posterior 구현 가능(Beta-Bernoulli 업데이트는 2줄 수식). 허용 복잡도 "중" 범위 내.
- [x] **3레이어 모두 Primary Outcome 강화?** — 마이크로=신뢰도 게이트, 미들=신뢰도 학습, 매크로=신뢰도 목표. 모두 Primary Outcome 기여.
- [x] **마이크로 → 미들 → 매크로 피드 연결?** — 마이크로 trade 결과 → 미들 posterior 업데이트 → 매크로 승률 집계 → 학습률 재조정 → 마이크로 임계치 갱신. 피드백 완결.
- [x] **매크로가 순환형이면 자기설정 목표 기반?** — "2주 누적 승률 66% 유지" 자기설정 목표 명시.

**검증 결과: PASS** — 11/11 항목 통과. Phase 2 (Component Map) 진입 조건 충족.

---

## Next Step

1. **Charter 태스크 1번 실행** (48시간 Rule 2 ablation) — Phase 2 Component Map 작성과 **병행**. 결과에 따라 Phase 2 스코프 조정.
2. **Phase 2 Component Map 작성** — Oracle 모듈을 최대 5개 컴포넌트로 분할. 제안:
   - `oracle-core` (예측 엔진 메인)
   - `context-encoder` (5차원 context 벡터 생성)
   - `reliability-head` (Bayesian posterior 유지/조회)
   - `blacklist-manager` (EV 기반 context 제외)
   - `market-data-collector` (공유 OHLCV, 조항 D)
3. **Phase 3 Decision Card 준비** — 조항 B(예측 타깃/horizon/점수함수/activation schedule), F(포트 최종), 및 Phase 2에서 식별된 공유 파라미터 확정.
4. **이후 `/spec`으로 Codex 구현 지시서 작성** — Phase 4 검증 통과 후.

---

## Evidence

- 이전 Phase 0 산출물: `subagent-runs/discuss/oracle-phase0-intake-2026-04-21/conclusion.md`
- 토론 8인 Round 1~2 응답: `subagent-runs/discuss/oracle-phase0-intake-2026-04-21/round-{1,2}/*.md`
- 도메인 팩 참조: `skills/design-director/domains/software/` (profile.yaml, heuristics.md)
- Charter 양식: `skills/design-director/templates/charter.md`
- Phase 1 에이전트 지침: `skills/design-director/agents/phase1-charter.agent.md`
