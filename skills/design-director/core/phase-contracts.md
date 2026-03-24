# Phase Contracts — 범용 설계 파이프라인

> 각 Phase의 입력/산출물/게이트를 계약으로 정의.
> 앞 Phase 게이트 미통과 시 다음 Phase 진입 금지.

---

## Phase 0: Intake

**입력:** 사용자 요청 (자유 형식)
**산출물:**
- 도메인 확정 (도메인 팩 로드 또는 generic 폴백)
- 스코프 파악 (팀 규모, 일정, 리소스)
- 제약조건 수집 (기술 스택, 예산, 규정, 기존 연동)

**게이트:**
- [ ] 도메인 확정 + 도메인 팩 로드 (또는 generic 폴백 확인)
- [ ] 스코프 1문장 이상 확정
- [ ] 제약조건 0건이면 "제약 없음" 명시 확인

---

## Phase 1: Charter

**입력:** Phase 0 산출물
**산출물:** Charter 5항목 확정 문서
- Primary Outcome (핵심 가치/결과)
- Operating Loop (마이크로/미들/매크로)
- Baseline Expectations (포함/제외)
- Differentiation Thesis (차별점 1문장)
- Target Audience (대상/환경/허용 복잡도)

**게이트 — Charter 일관성 검증:**
- [ ] Primary Outcome 1가지 확정
- [ ] 3레이어 Operating Loop 한 문장씩
- [ ] Baseline 포함/제외 결정
- [ ] Differentiation Thesis 한 문장
- [ ] Target Audience 환경/제약 확정
- [ ] Primary Outcome <-> Operating Loop 양립?
- [ ] Differentiation <-> Baseline 모순 없음?
- [ ] Target 허용 복잡도 <-> Primary Outcome 일치?
- [ ] 3레이어 모두 Primary Outcome 강화?
- [ ] 마이크로 -> 미들 -> 매크로 피드 연결?

---

## Phase 2: Component Map

**입력:** Phase 1 산출물 (Charter)
**산출물:**
- 전체 컴포넌트 목록
- Core/Support 분류 (가치 기여도 평가 기반)
- Core 순서 확정
- 의존성 맵 초안
- 스코프 어댑터 선택

**게이트:**
- [ ] 모든 컴포넌트 나열 완료
- [ ] 각 컴포넌트 Core/Support 판정 근거 기록
- [ ] Core 컴포넌트 순서 확정
- [ ] 의존성 맵 초안 작성
- [ ] 스코프 어댑터 선택 + 근거

---

## Phase 3: Decision Cards

**입력:** Phase 1 산출물 + Phase 2 산출물
**산출물:** 컴포넌트별 확정 항목 문서
- 필수 항목 확정값
- 준필수 항목 확정값/방향
- 선택 항목 (확정된 것만)
- 공유 파라미터 식별 목록
- 용어 정의 (Glossary)

**게이트:**
- [ ] Core 필수 100% 결정 (보류 시 의존 컴포넌트 명시)
- [ ] Core 준필수 70%+ 결정
- [ ] 공유 파라미터 식별 완료
- [ ] Support Core-연결 필수 확정 완료

---

## Phase 3.5: Cross-Impact Integration

**입력:** Phase 3 산출물 + Phase 2 의존성 맵
**산출물:**
- `cross-impact-check.md` (임시 — Phase 5에서 `_confirmed/`로 이전)
- 공유 파라미터 레지스트리
- 연쇄 효과 검증 결과
- 트레이드오프 의도 판정
- 타이밍/동시 발생 검증

**게이트:**
- [ ] 공유 파라미터 값 일치 확인
- [ ] 극단값 경계 조건 시나리오 최소 1건
- [ ] 트레이드오프 3조건 판정 완료
- [ ] 미해결 모순: 0건

---

## Phase 4: Recursive Verification

**입력:** Phase 3 산출물 + Phase 3.5 산출물
**산출물:** 검증 보고서 + "실행 착수 가능" 선언 (또는 미통과 사유)

**게이트 — 6조건:**
1. Core 필수: 검증 4단계 통과 + 모호 표현 0건
2. Core 준필수: 방향 확정 (보류 허용, 기한 명시)
3. 교차 모순: 0건
4. Support Core-연결 필수: 확정 + 검증 1~2번 통과
5. 오버엔지니어링 3문항: 전 컴포넌트 통과
6. 실행자 관점 셀프체크: (a)~(e) 전항목 확인

---

## Phase 5: Package

**입력:** Phase 1~4 전체 산출물
**산출물:**
- `_confirmed/project-charter.md`
- `_confirmed/glossary.md`
- `_confirmed/[컴포넌트명].md`
- `_confirmed/cross-impact-check.md`
- `_confirmed/shared-parameter-registry.md`
- `sections/[섹션명].md`
- `dependency-map.md`
- `CLAUDE.md`

**게이트:**
- [ ] 중복 수치 0건 (참조 전환 완료)
- [ ] 의존성 맵 완전성 확인
- [ ] 태그 감사 통과 (미결 항목 _confirmed/ 잔존 0건)
- [ ] 입출력 계약 감사 통과

---

## Phase 6: Change Control

**입력:** 변경 요청 + 현재 _confirmed/ + 의존성 맵
**산출물:** 수정된 _confirmed/ + changelog.md + 재검증 보고서

**게이트:**
- [ ] Tier 판정 완료 (1/2/3)
- [ ] 영향 범위 식별 완료
- [ ] 재검증 PASS
- [ ] changelog 기록 완료
