당신은 Gemini 2.5-pro입니다. **아키텍처 일관성 / 장문 맥락 / 설계 원칙** 관점에서 Oracle 설계 결정 2건을 교차 검증합니다.

당신의 강점:
- 긴 컨텍스트 윈도우로 Charter + Component Map + Ablation Plan 전체를 한번에 파악
- 설계 원칙 일관성 감사
- 모호한 경계의 아키텍처적 정당화

당신이 특히 주목할 포인트:
- Topic 1: Charter Differentiation Thesis("V3=setup/Oracle=prediction")가 Oracle variants 구성에 강제하는 제약. BollRev는 stock/crypto 거래에서 분명 의미가 있으나, 레이어 분리 원칙 위배 시 어떤 구조적 문제가 생길까
- Topic 2: Charter 원문 "신규 oracle.py 격리"가 반드시 Oracle 최종 구현 파일을 의미하는가, 아니면 "v2.py 프로세스로부터 격리된 검증 파일"로도 해석 가능한가 (문맥 해석). 다른 설계 방법론(SE/ML)에서 ablation 도구의 수명 처리 관습

독립 의견을 내세요. 다른 엔진의 답변이 없다고 가정하고 자신의 관점으로 판단하십시오.

---

[context.md 내용이 여기에 append됨]
# Discussion Context — Oracle Design Decisions (2 topics)

**Date**: 2026-04-21
**Prior artifacts**:
- Phase 0 Intake 토론: `subagent-runs/discuss/oracle-phase0-intake-2026-04-21/conclusion.md` (8인 토론 AGREE 조건부)
- Phase 1 Charter: `subagent-runs/design/oracle-2026-04-21/phase1-charter.md` (11/11 PASS)
- Phase 2 Component Map: `subagent-runs/design/oracle-2026-04-21/phase2-component-map.md`
- 48h Ablation 계획: `subagent-runs/design/oracle-2026-04-21/48h-ablation-plan.md`

---

## Topic 1: BollRev(Bollinger Reversion) variant 편입 여부

### Current Decision
**제외** (Phase 2 Component Map).

### 제외 근거 3가지
1. Phase 0 요약에 편입 근거 없음 — 8인 토론 Round 2 반대 sonnet 지적
2. BollRev는 setup quality 영역 → V3 소관 (meta-decision layer)
3. Charter Differentiation 레이어 분리 위배: **V3 = setup(meta-decision) / Oracle = prediction(signal-generation)**

### 편입 옵션 근거
- V3에 없는 mean-reversion regime 대응이 Oracle에 필요할 수 있음
- Bollinger Band는 통계적 mean-reversion 신호로 classic하며 low-vol regime에 강점

### 코드 검증된 팩트
- `scripts/dl_features.py:93` — `_bollinger_position()` 함수 존재 (feature 수준)
- `scripts/dl_features.py:163-164` — `feat["bb_pos"]` 컬럼 생성 (V3 feature set에 이미 포함)
- **"BollRev variant"는 어디에도 구현 안 됨** — V3/TriArb 모든 variant 검색해도 없음
- 즉 "편입"이 의미하는 것: Oracle에 신규로 BollRev variant를 추가 vs V3 영역에 남기기

### Oracle 초기 variants 후보 (제외 전제 시)
- `control` (baseline)
- `aggressive` (risk-on)
- `conservative` (risk-off)

---

## Topic 2: 48h Rule 2 Ablation 실행 파일 구조

### Charter 원문 (8인 토론 conclusion.md 섹션 3)
> 실행 환경: **신규 oracle.py 격리** (운영 sonnet), v2.py live 환경 수술 금지

### Chicken-and-egg 이슈
- Oracle은 Phase 3 Decision Card 이후 구현 예정 (2026-04-22 이후)
- Ablation은 Phase 2와 병행 (2026-04-22 시작)
- Oracle 구현 없이 Rule 2만 검증 필요

### 대안 비교

| 대안 | 설명 | 장점 | 단점 |
|------|------|------|------|
| **A** (현 제안) | `scripts/v2_ablation.py` — V2 포크 + `--no-rule2` flag. Oracle 완성 후 archive | - 즉시 실행 가능<br>- V2 구조 유지로 정확한 변수 분리<br>- 최소 개발 비용 | - "신규 oracle.py 격리" Charter 원문 위배<br>- 임시 파일 추가 관리 부담 |
| **B** | `scripts/oracle_v0.py` — Oracle 최소 골격 선구현 + Rule 2 toggle | - Charter 원문 충실<br>- Oracle 구현을 앞당김 | - Phase 3 Decision Card 선행 필요<br>- Oracle 설계 미확정 상태에서 코드화 위험<br>- "Rule 2가 원인인지"의 순수 검증에서 변수 증가 |
| **C** | v2.py 런타임 flag 추가 (v2.py 직접 수정) | - 파일 추가 없음<br>- 정확한 V2 행동 유지 | - 8인 토론 "v2.py live 수술 금지" 결정 위배<br>- 운영 중 V2 회귀 위험 |
| **D** | 기타 — 새로운 아이디어 제시 | — | — |

### 코드 검증된 팩트
- V2 Rule 2 위치: `scripts/v2.py:302` — `self._rebalance_memory()` 호출
- `scripts/v2.py:314-342` — `_rebalance_memory()` 본체 (엔트로피 균등화 + exploration noise)
- V2 update() 함수: `scripts/v2.py:275-312` — Rule 2 호출이 학습 끝에 단일 라인
- v2.py는 현재 live 운영 중 (port 8897)

---

## 요청

각 주제에 대해 아래 형식으로 응답:

### Topic 1 응답
- **Position**: 편입 / 제외 (명시)
- **Reasoning**: 2-4 bullet
- **Concerns**: 2-4 bullet
- **Recommendation**: 구체 다음 단계

### Topic 2 응답
- **Position**: A / B / C / D (명시. D인 경우 내용)
- **Reasoning**: 2-4 bullet
- **Concerns**: 2-4 bullet
- **Recommendation**: 구체 다음 단계

마지막 줄에 반드시:
`[POSITION: T1=편입/제외, T2=A/B/C/D]`

각 주제 30줄 이내. 전체 60줄 이내.
