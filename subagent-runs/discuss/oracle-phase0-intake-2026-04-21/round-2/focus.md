# Round 2 Focus — 이견 집중

## Round 1 요약 (참조)
- 수렴 상태: **PARTIAL**
- 합의: Phase 1 진입 가능 (7/8), 포트/v2.py 즉시 확정 필요 (6명), 수학 골격 스케치 부재 (6명), 67% KPI 근거 취약 (5명)
- 코드로 검증된 팩트:
  - v2.jsonl 실제 -11.15% (문서 -13.13%와 불일치)
  - V3/TriArb는 `*_state.npz + *_memory.json` (Phase 0의 "npz+jsonl 일관" 전제 오류)
  - Dashboard timeout 3초/refresh 5초 → Oracle `/api/state` p95 500ms 필수
  - Dashboard `renderV2/V3/TriArb` 하드코딩 → 통합 공수 +25~40%

## Round 2 집중 쟁점 (3개)

### 쟁점 1 — v2.py 처리
- 입장 A **덮어쓰기** (Oracle=V2 후계자): opus 단독
  - 근거: 정체성 명확화, 이중 유지 비용 제거
- 입장 B **신규 oracle.py**: sonnet / Codex A / Codex C / sonnet-찬성 (4명)
  - 근거: 롤백 유지, 베이스라인 비교, 새 코드=새 버그 주기 최소화
- 입장 C **Phase 3 유지**: Codex B / gemini-flash (2명)
  - 근거: 운영 packaging 문제이지 학습 아키텍처 문제 아님

### 쟁점 2 — 재설계 vs 수술적 수정
- **반대 sonnet**: Rule 2 제거는 30-50줄 PR. **48시간 백테스트로 60%+ 나오면 재설계 불필요**. 재설계는 검증 없는 과잉 공학.
- **찬성측 (7명)**: 단일 선형+context 분화 불가는 구조적 결함. 파라미터 조정(Rule 2 제거)으로 해결 불가.

### 쟁점 3 — V3 차별화
- **opus**: V3도 context k-NN + 블랙리스트 보유. Oracle이 V3와 무엇이 다른가? 차별화 1문장이 없으면 Oracle 재검토.
- **반대 sonnet**: V3 현재 승률을 측정해 67%+이면 Oracle은 **중복**.
- **찬성 sonnet**: V2 feature pipeline + V3 ContextMemory 재조립. V3와 다른 차원.
- **Codex B**: Oracle context = predicted edge/uncertainty/vol regime. V3의 rr_estimate/vp_clearance는 setup/management용이라 예측엔진에 부적합. **Oracle은 별도 context 공간 필요**.

## Round 2 지시

자신의 Round 1 입장을 **재평가**하고 세 이견에 답하라:

1. **v2.py 처리**: 지금 어느 입장(A/B/C)? 새 논거 또는 양보점?
2. **48시간 실험 선행**: 타당한가? 재설계 정당화 기준은?
3. **V3 차별화**: Oracle이 V3와 본질적으로 무엇이 다른가? (또는 다르지 않은가?)

## 응답 형식 (30줄 이내)

**첫 줄 라벨 필수**: `[AGREE] / [PARTIAL] / [DISAGREE]`
→ 대상: **"Phase 1 진입 OK + Round 1의 9항목(A~I) Charter 전 추가 확정"** 방향에 대한 당신의 입장.

1. **Reasoning**: 라벨 선택 이유
2. **쟁점 1 답**: v2.py 처리
3. **쟁점 2 답**: 48시간 실험 타당성
4. **쟁점 3 답**: V3 차별화
5. **Updated position**: 바뀐 점 있으면 명시

마지막 줄: `[POSITION: 한 줄 업데이트된 입장]`
