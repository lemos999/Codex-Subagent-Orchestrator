# Round 1 Moderator Summary — Oracle Phase 0 Intake 적합성

## 참여자 (8인)
| # | 엔진 | 역할 | POSITION |
|---|------|------|----------|
| 1 | Claude opus | Senior Architect | 조건부 통과, v2.py 처리·수학적 골격·V3 차별화 3건 Charter 진입 전 확정 |
| 2 | Claude sonnet | 운영 리스크 | oracle.py 신규+포트 8901 즉시 확정, dashboard graceful fallback 검증 후 Phase 1 착수 |
| 3 | Codex gpt-5.4 (A) | 구현 가능성 | Phase 1 조건부 진입, Oracle=numpy 기반 context-aware 통계 엔진 재정의 |
| 4 | Codex gpt-5.4 (B) | 알고리즘 엄밀성 | Phase 1 진입 OK, Oracle은 "새 학습 코어"로 설계, label/horizon/reward 고정 필수 |
| 5 | Codex gpt-5.4 (C) | 비용/효율 | Phase 1 진입 가능, fetch topology·memory cap·API SLA 미확정 |
| 6 | Claude sonnet (Gemini A fallback) | 찬성 | Phase 1 적합, V2 반학습 구조 코드 확인, 검증 기준 명확화 필요 |
| 7 | Claude sonnet (Gemini B fallback) | 반대 (Devil's Advocate) | **Rule 2 제거 48시간 실험 없이 재설계 진입은 과잉 공학, Ambiguity Gate 무효** |
| 8 | Gemini 2.5-flash | 사용자 관점 | Phase 0 적합, 학습 메커니즘 1-2문장 스케치 필요 |

※ Gemini 2.5-pro 2명은 쿼터 소진 (429)으로 Claude sonnet 대체.

## 수렴 판정: **PARTIAL** (조건부 합의)

### 합의점 (7/8 이상 동의)
1. **Phase 1 Charter 진입 자체는 가능** — 7 찬성 / 1 반대 (48시간 백테스트 선행 주장)
2. **포트/v2.py 처리를 Phase 3로 지연하는 것은 잘못** — 6명 "지금 확정하라" 지적
3. **학습 메커니즘의 수학적 골격이 Phase 0에 부재** — 6명 지적
4. **"좋은/나쁜 패턴 소거"를 구체 모델 구조로 번역한 1문장 스케치 필요** — 4명 명시
5. **67% 승률 KPI 근거 취약, 측정 프로토콜 부재** — 5명 지적

### 이견 (DISAGREE)
| 쟁점 | 입장 A | 입장 B | 입장 C |
|------|--------|--------|--------|
| v2.py 처리 | 덮어쓰기(Oracle=후계자): opus | 신규 oracle.py(롤백 유지): sonnet, Codex A, Codex C, sonnet-찬성 (4명) | Phase 3 지연 OK: Codex B, flash (2명) |
| 재설계 필요성 | Rule 2 + context 분화 동시 해결 필요 (7명) | Rule 2 제거 48시간 실험 선행 (1명) | — |
| V3 6D 벡터 재사용 | 불가 (setup/management용, 예측엔진에 부적합): Codex B | 가능 (인터페이스 호환 확인): sonnet-찬성 | 가능 but 재활용률 40-55%: Codex A |

### 검증된 팩트 (코드 확인)
- **v2.jsonl 실제 수익률 -11.15%** (문서 `-13.13%`와 불일치, Codex B 확인 `data/v2.jsonl`)
- **V3/TriArb 실제 파일: `*_state.npz` + `*_memory.json`** (Phase 0의 "npz+jsonl 일관" 전제 오류, Codex A 확인)
- **Dashboard timeout 3초 / refresh 5초** → Oracle `/api/state` p95 500ms 필요 (Codex C, `dashboard_unified.py:26-39, 632-685`)
- **Dashboard `renderV2/V3/TriArb` 하드코딩** → Oracle 통합 +25~40% 공수 (Codex A)
- **V3 `ContextMemory`는 개념 검증 완료** (sonnet-찬성, V3 성공 사례)

### Phase 0에서 누락된 항목 (통합)
A. **모델 골격 1문장** (6명) — 예: "per-context ridge + EV-based blacklist + trust-weighted softmax"
B. **예측 타깃 / horizon / 점수함수 / confidence activation schedule** (Codex B)
C. **data fetch 소유권 / memory cap / API SLA p95 500ms** (Codex C)
D. **v2.py 처리 + 포트 결정** (6명, 지금 확정)
E. **검증 기준**: 최소 trade 수, CI lower bound, 측정 window (sonnet-찬성, 반대 공통)
F. **V3 차별화 1문장** (opus) — V3도 context k-NN + 블랙리스트 보유
G. **BollRev 스코프 진입 경위** (반대 sonnet)
H. **v2.jsonl 수익률 수치 정정** -11.15% (Codex B)
I. **V3/TriArb 실제 파일 포맷 반영** `*_memory.json` 포함 (Codex A)

### 새로 제기된 핵심 도전 (Breakthrough Protocol)
**반대 sonnet의 "V3가 이미 67%+면 Oracle은 중복"** — 이 검증이 선행되지 않으면 Oracle 프로젝트 존재 이유 자체가 취약. opus의 "V3 차별화 1문장" 지적과 동일 문제를 다른 각도에서.
