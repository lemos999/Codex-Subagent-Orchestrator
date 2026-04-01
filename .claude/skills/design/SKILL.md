---
name: design
description: "범용 설계 디렉터 — 신규 기획 / 기존 분석 / 변경 관리 (모든 도메인)"
---

# /design — Design Director

> 실행 전 워크스페이스 루트의 `project-status/current.md`를 읽어 현재 프로젝트 상태를 파악한다.
> 실행 전 WKI 인덱싱: `node workspace-knowledge-index/dist/index.js index`

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
  현재 지원: generic (기본), software (소프트웨어 설계)
  추가 가능: game, business 등

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

## Architecture Discipline

`/design`은 모든 도메인의 설계를 다루되, 설계의 핵심 덕목은 동일하다: **명확성, 일관성, 검증 가능성**.

### 착수 전: 설계 부채를 먼저 해소하라

- 기존 설계 문서에 새 컴포넌트를 추가하기 전에, **폐기된 결정, 삭제된 컴포넌트 참조, 오래된 제약 조건**을 먼저 정리한다. 설계 문서의 dead reference는 코드의 dead code와 같은 해악이다.
- 하나의 Phase에서 **5개를 초과하는 컴포넌트를 동시에 설계하지 않는다**. 초과 시 `/sub`로 워커를 분할한다. Phase 경계를 뛰어넘지 않는 것은 이미 불변 원칙 #5이므로, Phase 안에서의 범위 제어에 집중한다.

### 설계 품질: 수석 아키텍트가 리젝트할 설계를 통과시키지 마라

- Charter에 명시된 핵심 가치와 무관한 컴포넌트, 중복된 책임, 불일치하는 인터페이스 — **구조적 결함을 발견하면 적극 수정한다**.
- Phase 4(Verify)는 형식 검증이 아니다. 컴포넌트 간 의존성 모순, Decision Card 간 충돌, 제약 조건 위반 — **내적 불일치를 모두 잡아낸다**. 검증 없이 Phase 5(Package)로 넘어가지 않는다.
- 설계에서 코드가 생성되는 경우(`/product` 연계 등), `tsc --noEmit` + `eslint` 검증은 필수다.

### 맥락: 설계 문서는 길고 Phase는 많다

- 500LOC 초과 문서는 **offset/limit으로 분할 읽기**. 전체를 한 번에 봤다고 가정하지 않는다.
- Phase 전환 시 또는 10+ 메시지 후, **이전 Phase 산출물을 반드시 재읽기**한다. Phase 0에서 확정한 Charter가 Phase 3에서 왜곡되는 것은 컨텍스트 붕괴의 전형이다.
- 교차 영향 분석(Phase 3.5)에 5개 초과 컴포넌트가 관련되면 **워커를 분할**한다. 검색 결과가 의심스럽게 적으면 범위를 좁혀 재실행.

### 편집 안전: 설계 문서 수정도 코드 수정과 동일하게

- 설계 문서 편집 후 **재읽기로 변경 반영 확인**. 3회 편집마다 검증 읽기.
- 컴포넌트명, 인터페이스명, 제약 조건명 변경 시 — 모든 설계 문서 내 참조를 빠짐없이 수정한다. **Charter, Component Map, Decision Card, 검증 체크리스트, 도메인 팩** 각각을 별도 검색한다.
