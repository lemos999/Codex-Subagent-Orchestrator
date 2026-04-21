# Charter 태스크 1번 — 48시간 Rule 2 Ablation 실행 계획

**Date**: 2026-04-21
**Parent Charter**: `phase1-charter.md` (조항 I)
**Run Mode**: Phase 2와 **병행**

---

## 목적

V2 실패의 근본 원인이 Rule 2(엔트로피 균등화)인지 **단일 변수 실험**으로 검증.

- **PASS** → V2에 수술적 수정(Rule 2 제거)만 적용. Oracle 재설계 스코프 축소 재검토(Charter Tier 2 변경).
- **FAIL** → Oracle 재설계 원안대로 Phase 3 진입.
- **INCONCLUSIVE** → 48h 1회 연장, 그래도 모호 시 FAIL 처리.

---

## 실행 환경 — chicken-and-egg 해결

**이슈**: Oracle은 아직 구현되지 않음. Charter는 "신규 `oracle.py` 격리"를 명시하나, Oracle 진짜 구현은 Phase 3 Decision Card 이후.

**해결**: Ablation은 **V2 포크**로 실행. Oracle 최종 구현과 별개의 격리 실행 파일.

```
scripts/
├── v2.py              ← 운영 (건드리지 않음, port 8897)
├── v2_ablation.py     ← ★ 신규. V2 복제 + --no-rule2 flag
├── oracle.py          ← (Phase 3 이후 작성)
└── archive/
    └── (v2.py는 Oracle이 3주 우위 시 여기로 이동)
```

**`v2_ablation.py`는 Phase 4 통과 후 Oracle이 완성되면 `archive/` 이동.** 임시 검증 도구.

**포크 결정 근거**: `subagent-runs/discuss/oracle-design-decisions-2026-04-21/conclusion.md` — Round 2 투표 A 2/D 1. D-1(subclass import) 기술 가능하나 v2.py의 모듈-레벨 글로벌(`STATE_PATH`/`LOG_PATH`/`DASH_PORT` v2.py:46-48) 때문에 "얇은 wrapper" 본질 붕괴 → A(포크) 채택. Charter 조항 I의 **입법 취지(live 환경 보호)** 는 8902/8903 격리로 충족, **문언**(Oracle 파일명) 예외는 본 각주로 투명 기록.

---

## Variant 구성

| Variant | 파일 | 포트 | Rule 2 | 실행 모드 |
|---------|------|------|--------|----------|
| `v2_abl_control` | `v2_ablation.py --variant control` | 8902 | ✅ 유지 | paper trades (observe-only 아님) |
| `v2_abl_no_rule2` | `v2_ablation.py --variant no_rule2` | 8903 | ❌ 제거 | paper trades |

**두 variant 동일 조건**:
- 동일 심볼 리스트 (BTC/ETH/SOL 우선)
- 동일 OHLCV 데이터 소스 (`market-data-collector` 미완성 시 각자 fetch)
- 동일 Rule 1/3 가중치 초기값
- 시드 고정 (`numpy.random.seed(42)` 등)
- Live trading 금지 (paper trades만)

**Rule 2 제거의 구현**: v2.py:302 `self._rebalance_memory()` 호출 지점을 `OnlinePredictor.__init__(enable_rule2: bool = True)` flag로 gate. `update()` 내부 `if self.enable_rule2: self._rebalance_memory()`. argparse `--no-rule2` → `enable_rule2=False` 주입.

### 구현 체크리스트 (Round 2 확정, 14 LOC)

1. **포크**: `cp scripts/v2.py scripts/v2_ablation.py`
2. **파일 헤더 추가** (최상단):
   ```python
   """V2 Rule 2 Ablation Fork.
   Forked from v2.py @ <SHA-40> on 2026-04-21.
   Purpose: Rule 2 on/off A-B test. 48h lifecycle.
   Archive to scripts/archive/ after 2026-04-23.
   DO NOT sync with v2.py.
   """
   ```
3. **모듈 상수 분리** (v2.py:46-48 대응):
   ```python
   STATE_PATH = DATA_DIR / "v2_ablation_state.npz"  # v2_state.npz → 격리
   LOG_PATH = DATA_DIR / "v2_ablation.jsonl"        # v2.jsonl → 격리
   DASH_PORT = 8902                                  # control default (no_rule2는 argparse로 8903)
   ```
4. **variant별 산출물 경로** (main 함수 내):
   ```python
   suffix = "_no_rule2" if args.no_rule2 else "_with_rule2"
   STATE_PATH = DATA_DIR / f"v2_ablation{suffix}_state.npz"
   LOG_PATH = DATA_DIR / f"v2_ablation{suffix}.jsonl"
   ```
5. **`OnlinePredictor.__init__` flag 추가** (v2.py:252-268 대응):
   ```python
   def __init__(self, ..., enable_rule2: bool = True):
       self.enable_rule2 = enable_rule2
       # 기존 초기화 그대로
   ```
6. **`update()` 내 gate** (v2.py:302 대응):
   ```python
   if self.enable_rule2:
       self._rebalance_memory()
   ```
7. **`V2Engine.__init__`에 flag 전파**: `OnlinePredictor(enable_rule2=args.enable_rule2)` 주입 (또는 V2Engine 파라미터 경유).
8. **argparse 추가**:
   ```python
   parser.add_argument("--no-rule2", action="store_true")
   parser.add_argument("--port", type=int, default=DASH_PORT)
   ```
9. **smoke test** (구현 직후 1회): 1 tick 실행 후 `engine.predictors["BTC"].enable_rule2 == False` 확인, `_rebalance_memory()` 호출 카운터가 0인지 확인.
10. **RNG 고정**: 양 variant에서 `numpy.random.seed(42)` 동일 시점 호출 — strict one-variable 보장 (Codex Round 2 지적 수용).

---

## 데이터 로그 스키마

**파일**: `data/v2_ablation.jsonl` (변이별 파일로 분리 권장)

각 라인 (trade 이벤트):
```json
{
  "timestamp": "2026-04-22T08:30:00Z",
  "variant": "no_rule2",
  "symbol": "BTC/USDT",
  "context": {
    "predicted_edge": 0.0032,
    "uncertainty": 0.18,
    "cost_margin": 0.0008,
    "vol_regime": "low",
    "time_bucket": "asia_am"
  },
  "prediction": "long",
  "confidence": 0.62,
  "entry_price": 67841.5,
  "exit_price": 67923.0,
  "pnl_gross": 0.00120,
  "fee": 0.00016,
  "pnl_after_fee": 0.00104,
  "hit": true,
  "window_id": "walk_fwd_01"
}
```

**부가 로그**:
- `data/v2_ablation_state_{variant}.npz` — 각 variant의 내부 가중치/엔트로피 스냅샷 (디버그용)
- `data/v2_ablation_summary.csv` — 하루 단위 집계

---

## 일정 (5일 내 기동 목표)

| Day | 작업 | Owner | 산출물 |
|-----|------|-------|--------|
| **Day 1 (2026-04-22)** | `v2_ablation.py` 작성 (Codex 지시서 `/spec`) + 포트 8902/8903 바인딩 검증 | Codex (구현) + Claude (리뷰) | `scripts/v2_ablation.py`, 기동 테스트 로그 |
| **Day 1 말** | 사용자 리뷰 + paper trades 시작 승인 | User | Go signal |
| **Day 1~3 (48h)** | 2 variant 병렬 실행. 중간 점검 (24h 지점) — 샘플 수 부족/크래시 감지 | 자동 + Claude 모니터 | `data/v2_ablation.jsonl` |
| **Day 3** | 실행 종료, 분석 착수 (Walk-forward split, CI 계산, calibration) | Claude (sonnet) + `/sub` | 분석 보고서 초안 |
| **Day 4** | PASS/FAIL/INCONCLUSIVE 판정 + 사용자 공유 | Claude (opus) | `ablation-verdict.md` |
| **Day 5** | 분기 실행: Phase 3 진입 / Charter Tier 2 변경 / 연장 | User + Claude | 다음 Phase 진입 |

**병행 진행**: Day 1~3 동안 Claude는 Phase 3 Decision Card 초안 **예비 작성** (FAIL 시나리오 대비). PASS 시 초안은 일부 재작업, 대부분 재사용 가능.

---

## 통과 기준 (Charter 태스크 1번과 동일, 6항목 AND)

1. **수수료 후 순수익 양수** — `no_rule2` variant의 `sum(pnl_after_fee) > 0`
2. **승률 95% CI lower bound > 50%** — Wilson score interval (`from scipy.stats import binomtest`)
3. **Walk-forward 재현** — 48h를 4개 12시간 window로 분할, 2~3개 window에서 기준 일관성
4. **자산별 편차 허용 범위 내** — BTC/ETH/SOL 간 승률 편차 ±5%p 이내
5. **Calibration monotone** — 신뢰도 버킷 [0.5, 0.6, 0.7, 0.8+]별 정확도가 단조 증가 (reliability diagram)
6. **최소 100+ trades** — `no_rule2` variant 기준

**동시 확인(참고용)**:
- `control` variant (Rule 2 유지)가 `no_rule2`보다 열등한지 — **명시적으로 worse** 여야 Rule 2가 원인임이 입증됨

---

## 사용자 개입 지점

1. **Day 1 시작 전**: `scripts/v2_ablation.py` 코드 리뷰 (Codex 작성 → Claude → User 확인 → 기동)
2. **Day 2 (24h 중간)**: 중간 샘플 수 / 크래시 여부 보고
3. **Day 4 판정 회의**: PASS/FAIL/INCONCLUSIVE 결과 검토
4. **Day 5 분기**: 사용자 최종 결정 (Phase 3 진입 vs Tier 2 변경 vs 연장)

---

## 실패 리스크 (사전 식별)

| 리스크 | 완화 |
|--------|------|
| Paper trades 샘플 부족 (100+ trades 미달) | 48h 연장 1회 허용 (Charter 명시). 여전히 부족 시 심볼 리스트 확장 검토 |
| `v2_ablation.py` 버그로 Rule 2 외 다른 요소까지 변경 | v2.py와의 diff 체크리스트 리뷰 — Claude가 Phase 4 1단계 검증 |
| 포트 8902/8903 충돌 | 기동 시 `netstat -ano` 확인. 대체 포트 8912/8913 예비 |
| Market regime 변동으로 control/no_rule2 외 변수 영향 | 동일 시간대 병렬 실행 + 시드 고정 + 동일 OHLCV feed |
| `control` variant도 양수 수익을 냄 (Rule 2 원인 아닐 가능성) | **INCONCLUSIVE 판정** + Oracle 재설계 원안 진행 (FAIL과 동일 분기) |

---

## Phase 2 / Phase 3 병행 관계

| 시점 | Phase 2/3 | Ablation |
|------|----------|----------|
| Day 1 | Phase 3 Decision Card 초안 시작 | 구현 + 기동 |
| Day 2~3 | Phase 3 Decision Card 심화 (조항 B/C/F) | 실행 중 |
| Day 4 | Phase 3 중단 (판정 대기) | 판정 |
| Day 5 | 분기 | — |

**PASS 시**: Phase 3 Decision Card 중단, Charter Tier 2 변경 (Oracle 스코프 축소). V2에 Rule 2 제거 패치만 적용.

**FAIL 시**: Phase 3 Decision Card 초안을 정식 Phase 3으로 전환, Phase 3.5 → Phase 4 진행.

---

## Next Step

1. **`/spec`으로 Codex 구현 지시서 작성** — `scripts/v2_ablation.py` + 로그 스키마 구현
2. **사용자 승인 후 Day 1 착수**
