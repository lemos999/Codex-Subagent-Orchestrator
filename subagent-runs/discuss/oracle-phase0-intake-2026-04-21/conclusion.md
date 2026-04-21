# Oracle Phase 0 Intake 토론 — 최종 결론

**주제**: Phase 0 Intake 요약이 Oracle 설계 착수 조건으로 적합한가?
**일시**: 2026-04-21
**참여자**: 8명 (Claude opus, Claude sonnet, Claude sonnet × 3 대체 (Gemini pro 쿼터 소진 fallback), Codex gpt-5.4 × 3, Gemini 2.5-flash)
**라운드**: 2

## 수렴 판정: **AGREE (조건부)**

Phase 1 Charter 진입 적합. 단 Charter 전에 아래 10항목 확정 필수.

## 합의된 결정 (Round 2에서 수렴)

### 1. v2.py 처리 — **신규 `oracle.py` 분리** (8/8 합의)
- opus가 단독 "덮어쓰기" 입장에서 양보, Codex B가 "Phase 3 지연" C입장에서 B로 이동하며 전원 합의
- **선셋 조항** (opus 제안): Oracle이 v2.py 대비 **3주 연속 승률 우위 시 v2.py → archive 이동**
- 비용 절감은 미미(~4.1 calls/min)하나 롤백/베이스라인/장애 분리 가치가 훨씬 큼

### 2. V3와 Oracle의 의미 공간 분리 — 전원 합의
**V3 차별화 1문장 (확정)**:
> **V3는 setup quality / trade management 학습 (vwap_slope, ema_dist, vp_clearance, rr_estimate, hour, vol_regime). Oracle은 ex-ante predictive edge / uncertainty / regime 학습 (predicted_edge, predictive_uncertainty, cost_margin, vol_regime, time_bucket). V3 = meta-decision (setup selection), Oracle = signal-generation (prediction).**

→ V3 k-NN **틀**은 재사용 가능, 6차원 **좌표**는 재설계 필수.

### 3. 48시간 Rule 2 ablation 실험 — 실행 (위치 논쟁만 남음)
- 7/8 "실행 가치 있음", 1/8 "불필요" (flash)
- **반대 sonnet**: 선행 Go/No-Go gate → **Charter 태스크 1번**으로 번역됨 (찬성 sonnet + Codex A/B/C 합의)
- 실행 환경: **신규 oracle.py 격리** (운영 sonnet), v2.py live 환경 수술 금지
- **통과 기준 (단일 60%+ 거부)**:
  - 수수료 후 순수익 양수
  - 95% CI lower bound > 50%
  - Walk-forward 2~5개 window 재현
  - 자산별 편차 허용 범위 내
  - Calibration monotone
  - 최소 100+ trades
- 미달 시 → 재설계 진행. 통과 시 → 수술적 수정 + 재설계 스코프 축소.

### 4. Oracle 모델 골격 스케치 — 확정
> **Online ridge/logistic + Bayesian reliability head (Beta-Bernoulli/Normal-Gamma posterior) + EV-based context blacklist**
> - 비-LSTM (현재 스택 제약)
> - `numpy/pandas`만으로 구현
> - 초기 `150-200` trades observe-only, `300-500` soft gate, blacklist는 `n_local ≥ 20` 이후

## Charter 전 확정 필요 10항목

| # | 항목 | 제기자 | 상태 |
|---|------|--------|------|
| A | 모델 골격 1문장 | opus/Codex A/B/C/flash | 위 섹션 4 확정 |
| B | 예측 타깃/horizon/점수함수/confidence activation schedule | Codex B | Phase 1 진입 시 필수 |
| C | API SLA: `/api/state` p95 500ms, hard 1s | Codex C | 확정 |
| D | 공유 OHLCV collector/cache (중복 fetch 방지) | Codex C | Charter 필수 |
| E | v2.py 처리: 신규 oracle.py + 선셋 조항 (3주 우위 시 archive) | opus | **확정** |
| F | 포트: 8901 신규 (다수) / Phase 3 유지(소수) | 운영 sonnet, opus | 즉시 확정 권고 |
| G | V3 차별화 1문장 | opus/Codex B 합의 | **확정** (섹션 2) |
| H | 검증 기준: CI/walk-forward/최소 trade 수 | Codex A/B/C + 찬성/반대 sonnet | **확정** (섹션 3) |
| I | 48시간 Rule 2 ablation (Charter 태스크 1번) | 반대 sonnet + 다수 | **확정** |
| J | v2.jsonl 수치 정정 -11.15% → 현재 약 -10.97% | Codex B | 문서만 수정 |

## 코드 수준 검증된 팩트 (Phase 0 재작성 근거)

1. **v2.jsonl 실제 수익률 -10.97~-11.15%** (문서 -13.13%와 불일치, Codex B 확인)
2. **V3/TriArb 실제 파일 포맷**: `*_state.npz + *_memory.json` (Phase 0 "npz+jsonl 일관" 전제 오류, Codex A 확인)
3. **V3 실제 승률** (tick 2225, 2026-04-21 기준): v3-control **54.5% (11 trades)**, v3-3m **50% (2)**, 나머지 0-50%. **전 variant 67% 미달** (반대 sonnet 측정)
4. **Dashboard 통합 공수 +25~40%**: `renderV2/V3/TriArb` 하드코딩이라 "MODELS 한 줄 추가"가 아님 (Codex A 확인)
5. **Dashboard 한계**: timeout 3초, refresh 5초, refresh 겹침 방지 없음 (Codex C)

## 이견 / 미해결 (중요도 낮음)

- **포트 즉시 확정 vs Phase 3 지연**: 운영 sonnet/opus는 즉시 8901, Codex B는 늦춰도 OK. → 실용적 타협: **포트 지금 확정 + Charter에 조항만 추가**
- **BollRev 스코프 진입 경위**: 반대 sonnet 지적, 누락됨. → Charter에 명시 필요

## Evidence 전체 경로

- `subagent-runs/discuss/oracle-phase0-intake-2026-04-21/`
  - `context.md` — 원본 배경
  - `role_*.md` — 역할별 프롬프트
  - `round-1/` — Round 1 8명 응답 + moderator-summary
  - `round-2/focus.md` — Round 2 집중 쟁점
  - `round-2/*.md` — Round 2 8명 응답

## Next Step

**`/design Phase 1 Charter 진입`** 권고. Charter 진입 첫 결정:
1. 섹션 2 (V3 차별화 1문장) + 섹션 4 (모델 골격) 확정 수록
2. 10항목 A~J 각각 Charter 조항으로 번역
3. Charter 태스크 1번 = 48시간 Rule 2 ablation (섹션 3 기준으로 Go/No-Go)
4. 이후 `/spec`으로 Codex 구현 지시서 작성

**또는**, 사용자가 원하면:
- Charter 진입 전 v2.py Rule 2 제거 ablation만 먼저 실행 → 결과 보고 재설계 스코프 재평가
