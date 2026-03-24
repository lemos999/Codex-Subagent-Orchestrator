---
name: design
description: "범용 설계 디렉터 — 신규 기획 / 기존 분석 / 변경 관리 (모든 도메인)"
---

# /design — Design Director

> 실행 전 워크스페이스 루트의 `project-status/current.md`를 읽어 현재 프로젝트 상태를 파악한다.

모든 도메인의 기획/설계를 체계적으로 수행하는 범용 AI 디렉터.

## 인수 없이 호출 시 — 도움말 출력

인수가 없으면(`/design`만 입력) 아래 도움말을 그대로 출력하고 사용자 입력을 기다린다:

```
/design — 범용 설계 디렉터

사용법:
  /design <요청>

■ 신규 기획 (Mode A)
  /design 새 프로젝트를 기획하고 싶다       → Phase 0(Intake)부터 시작
  /design SaaS 백엔드 아키텍처 설계         → 도메인 힌트와 함께 Phase 0 시작
  /design 1인 개발, 린 스코프로              → 스코프 어댑터 '린' 자동 선택

■ 이어서 진행
  /design Phase 3부터                       → Decision Card부터 재개
  /design Phase 3.5~5 자동화                → /sub로 교차검증→검증→문서 생성

■ 기존 분석 (Mode B)
  /design 이 기획서를 검토해줘               → Charter 추출 → 진단 → 처방
  /design 인증 모듈 진단                     → 특정 컴포넌트 집중 분석

■ 변경 관리 (Phase 6)
  /design 타임아웃 값을 변경하고 싶다        → Tier 판단 → 영향 분석 → 재검증

■ 멀티엔진 (GPT + Gemini 교차 검증)
  /design Phase 3.5~5 자동화 (/submix)   → Claude+GPT+Gemini 교차 검증
  /design 이 기획서를 검토해줘 (/submix)  → 3엔진 독립 분석

■ 도메인 팩
  현재 지원: generic (기본)
  추가 가능: game, software, business 등

■ 참조
  프레임워크: skills/design-director/SKILL.md
  에이전트:   skills/design-director/agents/
  템플릿:     skills/design-director/templates/
  도메인:     skills/design-director/domains/
```

## Entry Protocol (인수가 있을 때)

1. Strip the `/design` prefix
2. 프레임워크 로드: `skills/design-director/SKILL.md`
3. 사용자 요청 분석 → Mode 분기

## Mode 분기

| 요청 유형 | Mode | 진입 |
|----------|------|------|
| "새 프로젝트를 기획하고 싶다" | Mode A | Phase 0부터 |
| "이 기획서를 검토해줘" | Mode B | Step 1부터 |
| "Phase 3부터 이어서" | Mode A | 지정 Phase부터 (중간 진입 시: `_confirmed/`에 기존 산출물이 있으면 읽고, 없으면 사용자에게 이전 Phase 산출물 제공 요청) |
| "변경 사항이 있다" | Phase 6 | 변경 관리 |

## 실행 방식

### 대화형 Phase (사용자 입력 필요)
- Phase 0: Intake → `agents/phase0-intake.agent.md`
- Phase 1: Charter → `agents/phase1-charter.agent.md`
- Phase 2: Component Map → `agents/phase2-map.agent.md`
- Phase 3: Decision Card → `agents/phase3-decide.agent.md`
- Phase 6: Change → `agents/phase6-change.agent.md`
- Mode B: Analysis → `agents/analysis-mode.agent.md`

### 자동화 Phase (`/sub` 연동 가능)
- Phase 3.5: Cross-Impact → `agents/phase35-integrate.agent.md`
- Phase 4: Verify → `agents/phase4-verify.agent.md`
- Phase 5: Package → `agents/phase5-package.agent.md`

자동화 Phase 실행 시:
- `/sub` (Claude 단독): `specs/pipeline.claude.json` / `specs/analysis.claude.json`
- `/submix` (Claude + GPT + Gemini 멀티엔진): `specs/pipeline-mixed.json` / `specs/analysis-mixed.json`

## 핵심 참조

| 파일 | 용도 |
|------|------|
| `skills/design-director/SKILL.md` | 실행 스킬 전체 |
| `skills/design-director/core/` | Phase 계약, 검증, 변경관리, 상태 모델 |
| `skills/design-director/agents/*.agent.md` | Phase별 에이전트 지침 |
| `skills/design-director/templates/*.md` | 인터뷰/검증/출력 형식 |
| `skills/design-director/domains/` | 도메인 팩 (generic 기본) |
| `skills/design-director/specs/*.claude.json` | `/sub` 파이프라인 스펙 (Claude 단독) |
| `skills/design-director/specs/*-mixed.json` | `/submix` 파이프라인 스펙 (멀티엔진) |

## 불변 원칙

1. 핵심 가치가 최우선
2. 모호한 결정은 결정이 아니다
3. What만 정의, How는 실행자 판단
4. 더 복잡하게가 아니라, 더 명확하고 빠르게
5. 앞 Phase 미확정 → 다음 Phase 금지
