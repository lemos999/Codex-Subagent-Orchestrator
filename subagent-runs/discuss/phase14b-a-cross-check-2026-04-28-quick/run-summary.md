# Phase 14B-A axis A spec — 외부 엔진 cross-check 결론

> Completed: 2026-04-28
> Mode: /discuss --quick (max_rounds=1, --auto)
> Verdict: **REQUEST_CHANGES — axis A 기각 권고 우세**

---

## 응답 현황

| Engine | Model | 응답 | 시간 |
|--------|-------|:----:|:----:|
| Claude | sonnet | ✅ | 28.6s |
| Codex  | gpt-5.5 | ✅ | 41.9s |
| Gemini | gemini-3.1-pro | ❌ ModelNotFoundError 404 | 13.8s |

**Gemini 모델 이슈**: `gemini-3.1-pro`가 API에 부재 (404). 2/3 응답이지만 Claude vs Codex 명확 이견 존재 → DISAGREE 패턴 자체가 정보가치 있음.

---

## 3엔진 입장 (Gemini 결시)

### Claude (형식논리 엄격파) — **기각**

> [POSITION: axis A는 거짓 PASS 역공학 — SNN 게이트 포장과 무관하게 hotfix v1 제거 패턴과 동형, 기각 권고]

핵심 논거 3건:
1. **SNN 정합성 부정합**: `chiljeong[1] ≥ 0.5` 게이트가 존재하는 이유가 "affiliation을 막아야 하기 때문" — SNN이 원인이 아니라 분기 정당화 도구로 호출됨. 임계 0.5는 어떤 창발 관측에서도 도출되지 않은 임의값.
2. **거짓 PASS 동일 패턴**: hotfix v1 제거 5건과 구조 동형. (a) acceptance 미달 식별 → (b) 막는 조건 삽입 → (c) 자연 현상 포장. dampen 0.6은 `follower_reserve` sticky와 동일.
3. **인과 역공학**: "anger → dampen → active_factions ≥ 2 → pair 응결"은 각 단계가 독립 검증되지 않음. 진정한 인과라면 "anger gate 없이도 dampen이 다른 문제를 해결" 독립 근거 필요.

### Codex (실행가능성 현실주의자) — **조건부 (계측 실험 후 승격)**

> [POSITION: axis A는 도메인 인과는 있으나 현재 상수형 hard gate는 보정 PASS 위험이 커서 계측 실험 후 승격해야 한다]

도메인 인과 인정. 단 현재 상수형 hard gate(0.5/0.6)는 보정 PASS 위험. 계측 후 승격 권고 (구체 계측 항목은 미명시).

### Gemini — 응답 실패

`gemini-3.1-pro` 모델 부재. memory `feedback_gemini_model_pin.md` 갱신 필요.

---

## Moderator 종합 (Claude separate)

**Consensus**:
- axis A는 acceptance #2 PASS를 목적으로 설계된 역공학 조건
- 후기 active_factions collapse가 Case C의 실제 근본 원인
- 근본 추적 없이 dampen 삽입은 선행 제거된 5건 거짓 보정과 구조 동형 위험

**Disputed**:
- Claude(기각 — 재포장 거짓 보정) vs Codex(조건부 허용 — 실험 후 승격)
- SNN gate 0.5의 창발 정당화 근거 — 두 엔진 모두 미확보

**Recommendation**: **axis A 기각, territory cross-propagation 강화 우선**

---

## 결정 권고 (사용자 보고용)

`feedback_snn_emergence_first.md` + `feedback_root_cause_first.md` 직접 적용 시:

### 옵션 A — axis A 기각 + 근본 추적 (Claude·Moderator 권고)

새 spec 작성: `Phase 17 Case C: active_factions collapse 인과 추적`
- tick별 faction count 로그
- 후기 tick에서 active_factions=1로 수렴하는 정확한 코드 경로 진단
- Phase 14 propagation이 후기 tick에 유지되는지 직접 검증
- territory cross-prop 강화 패치 (axis A 없이)

### 옵션 B — axis A 보존 + 계측 모드로 재설계 (Codex 권고)

PHASE-14B-AFFILIATION-RESONANCE-SPEC.md를 다음으로 보강:
- §6 회귀 테스트에 "anger gate 없이 dampen 단독 적용 시 동일 효과 검증" 추가 (독립 인과 입증)
- §3.2에 "임계 0.5 / dampen 0.6은 잠정값. 자연 측정 후 SNN 분포에서 역산하여 갱신" 명시
- §5 검증 단계에서 "active_factions collapse 발생 tick 추적 항목" 우선 측정

### 옵션 C — 하이브리드 (root cause 우선 + axis A 보류)

옵션 A 우선 실행. Case C 근본 진단 후 territory 강화 패치 시도. 그래도 acceptance #2 미충족 시 axis A를 옵션 B 형태로 재투입.

---

## 위험 신호 요약 (commit 전 사용자 결정 사항)

| 신호 | 강도 | 출처 |
|------|:--:|------|
| axis A = acceptance 역공학 | **강** | Claude + Codex + Moderator 합의 |
| dampen 0.6 = 거짓 보정 5건 동형 | **강** | Claude (구체 비교: follower_reserve sticky) |
| SNN gate 0.5 정당화 부재 | **중** | Claude + Codex 공통 |
| active_factions collapse가 진짜 근본 | **강** | Moderator + Claude 합의 |
| Gemini 응답 부재로 창발 관점 1개 누락 | 약 | 환경 이슈 (모델명) |

**Verdict**: 현재 상태로 commit 진행하면 `feedback_snn_emergence_first.md`("규칙 < 창발") + `feedback_root_cause_first.md`("표면 해결 금지") 양쪽 위반 위험. **commit 보류 권고**.
