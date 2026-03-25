---
name: gdd
description: "게임 기획 디렉터 — 새 게임 기획 / 기획서 분석 / 기획 변경 관리"
---

# /gdd — Game Design Director

> 실행 전 워크스페이스 루트의 `project-status/current.md`를 읽어 현재 프로젝트 상태를 파악한다.

게임 기획 디렉터 프레임워크(97/100)를 실행하여 실제 게임 기획서를 생산한다.

## 인수 없이 호출 시 — 도움말 출력

인수가 없으면(`/gdd`만 입력) 아래 도움말을 그대로 출력하고 사용자 입력을 기다린다:

```
/gdd — 게임 기획 디렉터

사용법:
  /gdd <요청>

■ 신규 기획 (Mode A)
  /gdd 새 게임을 기획하고 싶다         → Phase 1(DNA)부터 시작
  /gdd 로그라이크 덱빌더 게임           → 장르 힌트와 함께 Phase 1 시작
  /gdd 1인 개발, 린 스코프로            → 스코프 어댑터 '린' 자동 선택

■ 이어서 진행
  /gdd Phase 3부터                     → 핀셋 인터뷰부터 재개
  /gdd Phase 3.5~5 자동화              → /sub로 교차검증→검증→문서 생성

■ 기존 게임 분석 (Mode B)
  /gdd 이 기획서를 검토해줘             → DNA 추출 → 진단 → 처방
  /gdd 전투 밸런스 진단                 → 특정 시스템 집중 분석

■ 변경 관리 (Phase 6)
  /gdd HP 공식을 변경하고 싶다          → Tier 판단 → 영향 분석 → 재검증

■ 내보내기
  /gdd 기획서를 HTML로                  → 통합 HTML 기획서 (열람용)
  /gdd 기획서를 docx로                  → Word 문서 (팀 공유, 외부 전달)
  /gdd 수치 테이블을 xlsx로             → 엑셀 시트 (밸런스 시뮬레이션)

■ 멀티엔진 교차 검증
  /gdd Phase 3.5~5 자동화 (/submix)     → Claude+GPT+Gemini 교차 검증

■ 게임 개발 연계
  /product Stage 3부터                  → /gdd 기획 완료 후 게임 개발 착수

■ 참조
  프레임워크: game-design-director/game-design-director-integrated.md
  에이전트:   skills/game-design-director/agents/
  템플릿:     skills/game-design-director/templates/
```

## Entry Protocol (인수가 있을 때)

1. Strip the `/gdd` prefix
2. 프레임워크 로드: `skills/game-design-director/SKILL.md`
3. 사용자 요청 분석 → Mode 분기

## Mode 분기

| 요청 유형 | Mode | 진입 |
|----------|------|------|
| "새 게임을 기획하고 싶다" | Mode A | Phase 1부터 |
| "이 기획서를 검토해줘" | Mode B | Step 1부터 |
| "Phase 3부터 이어서" | Mode A | 지정 Phase부터 |
| "변경 사항이 있다" | Phase 6 | 변경 관리 |

## 실행 방식

### 대화형 Phase (사용자 입력 필요)
- Phase 1: DNA 확정 → `agents/phase1-dna.agent.md`
- Phase 2: 시스템 분류 → `agents/phase2-priority.agent.md`
- Phase 3: 핀셋 인터뷰 → `agents/phase3-pinset.agent.md`
- Phase 6: 변경 관리 → `agents/phase6-change.agent.md`
- Mode B: 전체 분석 → `agents/modeb-analysis.agent.md`

### 자동화 Phase (`/sub` 연동 가능)
- Phase 3.5: 교차 검증 → `agents/phase35-crosscheck.agent.md`
- Phase 4: 재귀 검증 → `agents/phase4-verify.agent.md`
- Phase 5: 문서 생성 → `agents/phase5-document.agent.md`

자동화 Phase를 `/sub`로 실행 시: `specs/mode-a-pipeline.claude.json` 사용.

## 핵심 참조

| 파일 | 용도 |
|------|------|
| `skills/game-design-director/SKILL.md` | 실행 스킬 전체 |
| `game-design-director/game-design-director-integrated.md` | 프레임워크 원본 (2269줄) |
| `skills/game-design-director/agents/*.agent.md` | Phase별 에이전트 지침 |
| `skills/game-design-director/templates/*.md` | 인터뷰·검증·출력 형식 |
| `skills/game-design-director/specs/*.claude.json` | `/sub` 파이프라인 스펙 |

## 불변 원칙

1. 재미가 최우선
2. 모호한 결정은 결정이 아니다
3. What만 정의, How는 개발자 판단
4. 더 복잡하게가 아니라, 더 명확하고 빠르게
5. 앞 Phase 미확정 → 다음 Phase 금지
