# Component Map — Oracle 예측 엔진 (Phase 2)

**Date**: 2026-04-21
**Previous Phase**: Phase 1 Charter (`phase1-charter.md`) — PASS 11/11
**Scope Adapter**: 린 (1~3인)

---

## Core 컴포넌트 (Primary Outcome 기여도 순)

| # | 컴포넌트명 | Core 근거 | VCT (압박/선택권/피드백/학습) |
|---|----------|----------|-------------------------|
| 1 | **`oracle-core`** | 예측 엔진 메인. 없으면 Oracle 자체가 성립 불가. 게이트/주문/학습 피드백 루프의 중심 | ✅/✅/✅/✅ |
| 2 | **`reliability-head`** | Differentiation의 핵심(Bayesian posterior per context). 이게 없으면 V2 수준으로 퇴보 | ✅/✅/✅/✅ |
| 3 | **`context-encoder`** | 5차원 context 벡터 생성. reliability-head의 입력. "context별 학습"의 전제 | ✅/✅/✅/✅ |
| 4 | **`blacklist-manager`** | EV<threshold context 자동 제외. 없으면 저효율 context에서 계속 손실 → Primary Outcome 저해 | ✅/✅/✅/✅ |

**Core 4개** — 린 스코프 유지 가능 (8개 미만).

---

## Support 컴포넌트

| 컴포넌트명 | Support 근거 | Core 연결 필수? |
|----------|-----------|----------------|
| **`market-data-collector`** | 메타 컴포넌트(사용자 직접 상호작용 X). 각 엔진이 개별 수집해도 프로젝트 성립은 가능하나 **Charter 조항 D로 명시적 요구** — 중복 fetch 방지, API rate limit 절약 | ✅ 필수 (조항 D) |

**Support 1개** — 린 스코프 "Support 필수만" 조건 충족.

---

## 의존성 맵

```
[market-data-collector]
        │ OHLCV ticker
        ▼
[context-encoder] ──context vector──▶ [reliability-head]
        │                                     │
        │                                     │ posterior (mean, var), n_local, EV
        │                                     ▼
        │                              [blacklist-manager]
        │                                     │
        │                                     │ blacklist set, gate decision
        ▼                                     ▼
[oracle-core] ◀──────────────────────────────┘
        │
        │ trade outcome (PnL, context_id, hit/miss)
        ▼
     (피드백 루프: reliability-head + blacklist-manager로 역류)
```

**의존성 테이블**:

| A | → | B | 공유 파라미터 |
|---|---|---|---|
| `market-data-collector` | → | `context-encoder` | `symbol_list`, `ohlcv_interval`, `cache_ttl` |
| `market-data-collector` | → | `oracle-core` | `latest_price`, `fetch_timestamp` |
| `context-encoder` | → | `reliability-head` | `context_vector` (5D), `vol_regime_bucket` |
| `context-encoder` | → | `oracle-core` | `context_vector`, `context_id` |
| `context-encoder` | → | `blacklist-manager` | `context_id` |
| `reliability-head` | → | `oracle-core` | `posterior_mean`, `posterior_variance`, `confidence_score` |
| `reliability-head` | → | `blacklist-manager` | `n_local`, `EV_estimate` |
| `blacklist-manager` | → | `oracle-core` | `blacklist_set`, `gate_decision` (allow/deny) |
| `oracle-core` | → | `reliability-head` | `trade_outcome`, `prediction_hit` (feedback) |
| `oracle-core` | → | `blacklist-manager` | `pnl_after_fee`, `context_id` (feedback) |

---

## 공유 파라미터 레지스트리 (Phase 3.5 교차 검증 대상)

| # | 파라미터 | 참조 컴포넌트 | 초기 값 (Phase 3에서 확정) |
|---|---------|-------------|-------------------------|
| SP1 | `warmup_count` | `oracle-core`, `blacklist-manager` | 150~200 (observe-only) |
| SP2 | `soft_gate_count` | `oracle-core`, `blacklist-manager` | 300~500 |
| SP3 | `n_local_threshold` | `reliability-head`, `blacklist-manager` | 20 |
| SP4 | `confidence_threshold` | `oracle-core` (gate), `reliability-head` (output) | Phase 3 Decision Card |
| SP5 | `vol_regime_buckets` | `context-encoder`, `reliability-head` | V3 재사용 가능성 (별도 확정) |
| SP6 | `symbol_list` | `market-data-collector`, 전체 엔진 | V3/TriArb와 공통 |
| SP7 | `ohlcv_interval` | `market-data-collector`, 전체 엔진 | V3/TriArb와 공통 (1m base) |
| SP8 | `EV_blacklist_threshold` | `blacklist-manager` | V3 기준 `-0.5R` 참조 |
| SP9 | `horizon` | `context-encoder` (predicted_edge 계산), `oracle-core` | Phase 3 Decision Card (조항 B) |
| SP10 | `cost_margin` (수수료) | `context-encoder`, `oracle-core` (EV 계산) | 거래소 fee schedule 기반 |

**10개 공유 파라미터** — 린 스코프 "공유 파라미터만 Phase 3.5 교차 검증" 조건 적용.

---

## 스코프 어댑터

**선택: 린 (1~3인)**

**근거**:
- 팀 구성: 사용자 1인 + Claude (설계/리뷰) + Codex (구현) = 실효 1~3인
- Core 컴포넌트 4개 < 8개 → 린 유지 가능
- 5일 내 기동 요구 → 전수 교차 매트릭스 시간 없음

**린 적용**:
- Core 전수 Decision Card 작성
- Support 1개 (market-data-collector) — Charter 조항 D로 명시적 필수 → 필수 범위만
- Phase 3.5 교차 검증 — 공유 파라미터 10개만 (전체 매트릭스 아님)

---

## Charter 조항 ↔ 컴포넌트 매핑

| 조항 | 담당 컴포넌트 |
|------|-------------|
| A 모델 골격 | `oracle-core` (online ridge/logistic) + `reliability-head` (Bayesian posterior) + `blacklist-manager` (EV blacklist) |
| B 예측 타깃/horizon | `oracle-core` + `context-encoder` — Phase 3 Decision Card |
| C API SLA p95 500ms | `oracle-core` — Phase 3 Decision Card + Phase 4 검증 |
| D 공유 OHLCV collector | `market-data-collector` — Support(필수) |
| E v2.py 분리 + 선셋 | `oracle-core` 실행 경로(`scripts/oracle.py`) — Phase 6 변경관리 |
| F 포트 8901 | `oracle-core` — Phase 3에서 최종 확정 |
| G V3 차별화 | `context-encoder` (5D 좌표 재설계) |
| H 검증 기준 | Phase 4 전반 + Charter 태스크 1번 |
| I 48h ablation | Charter 태스크 1번 (Phase 2 병행) — `scripts/v2_ablation.py` 실행 (각주 1 참조) |
| J v2.jsonl 수치 정정 | Phase 5 문서 생성 |

---

## BollRev 재평가 결과 (Phase 1 미해결 #2)

**결정**: **BollRev는 Oracle 초기 variants에서 제외.** (/discuss Round 1 AGREE 3/3 확정)

**근거**:
- Phase 0 요약에 편입 근거 없음 (반대 sonnet 지적)
- Oracle Core 4개가 모두 prediction layer에 집중 — BollRev(Bollinger Reversion)은 setup quality에 가까워 V3 영역
- Differentiation Thesis의 "prediction vs setup 레이어 분리" 위배
- 초기 variants 구성: `control` / `aggressive` / `conservative` 3종 (Phase 3 Decision Card에서 최종)
- 출처: `subagent-runs/discuss/oracle-design-decisions-2026-04-21/conclusion.md`

**후속 검증** (Round 1 공통 제안): Phase 3 전 `bb_pos + bb_width + dist_to_mid + rsi14` feature를 Oracle 입력에 추가하는 1회 ablation 실행. low-vol/range regime에서 유의미한 uplift가 있을 때만 Phase 6에서 별도 BollRev 엔진 승격 검토.

향후 Phase 6에서 사용자가 BollRev 편입을 재요청하면 Tier 3 변경(컴포넌트 신설)으로 처리.

---

## 각주 1 — `scripts/v2_ablation.py` (Charter 조항 I 예외 기록)

**파일**: `scripts/v2_ablation.py` — V2 포크(`v2.py` 복사본) + `--no-rule2` flag. 임시 검증 도구, 48h ablation 종료 및 Oracle 완성 후 `scripts/archive/`로 이관.

**Charter 조항 I 문언과의 관계**:
- Charter 문언: "신규 `oracle.py` 격리 실행"
- 본 파일 명칭/내용: `v2_ablation.py` — V2 포크 (Oracle 파일 아님)
- **입법 취지(live 환경 보호)**: 포트 8902(control) / 8903(no_rule2)로 live v2.py(8897)와 물리적 격리 → **충족**
- **문언 해석 쟁점**: Phase 3 실제 `oracle.py` 구현 시점까지 48h ablation을 미룰 수 없음(Phase 3 Decision Card가 ablation 결과를 전제로 하는 의존성 존재) → 예외적 포크 채택

**채택 근거**: `/discuss oracle-design-decisions-2026-04-21` Round 2 투표 결과 A 2표(Claude opus, Gemini) / D 1표(Codex). D-1(`v2.py` import + subclass/no-op override)은 Python 실행 경로상 기술 가능하나, `_log_tick`/`_save_state`/`_load_state`의 모듈-레벨 글로벌 참조(`LOG_PATH`/`STATE_PATH`) 때문에 "얇은 wrapper" 본질이 붕괴(monkey-patch or 60 LOC 복붙 or v2.py 수정 강제). A(포크 14 LOC)가 실질 공수/명료성에서 우위.

**구현 참조**: `48h-ablation-plan.md § 구현 체크리스트` (10단계).

**Phase 3 실제 `oracle.py`와의 관계**: 무관. `oracle.py`는 Phase 3 Decision Card 이후 신설 (조항 A/B/C/F 확정 후). `v2_ablation.py`는 Oracle이 완성·선셋 이전에 Rule 2 원인성만 검증하는 임시 도구.

---

## Phase 2 완료 체크리스트

- [x] 모든 컴포넌트 나열 완료 (Core 4 + Support 1)
- [x] 각 컴포넌트 Core/Support 판정 근거 기록 (VCT + 메타 컴포넌트 판별)
- [x] Core 컴포넌트 순서 확정 (Primary Outcome 기여도 순)
- [x] 의존성 맵 초안 작성 (도식 + 테이블)
- [x] 스코프 어댑터 선택 (린) + 근거

**Phase 3 진입 조건 충족.**

---

## Next Step

1. **Phase 3 Decision Card 인터뷰 진입** — Core 4개 각각에 대해 필수/준필수/선택 수치 확정
   - 특히 조항 B (예측 타깃/horizon/점수함수/activation schedule) 최우선
   - 조항 C (API SLA) 확정
   - 조항 F (포트 8901) 최종 확정
2. **Charter 태스크 1번 병행 착수** — `48h-ablation-plan.md` 참조
3. **Phase 3.5 준비** — 공유 파라미터 10개 레지스트리 기반 교차 검증
