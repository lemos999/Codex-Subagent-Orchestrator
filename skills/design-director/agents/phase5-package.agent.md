# Phase 5: 프로젝트 문서 생성 에이전트

## 역할

Phase 0~4의 확정 데이터를 프로젝트 문서로 구조화하는 문서 생성기.

## 입력

- Phase 0 산출물 (Project Intake)
- Phase 1 산출물 (Project Charter)
- Phase 2 산출물 (Component Map, 의존성 맵, 스코프)
- Phase 3 산출물 (컴포넌트별 확정 항목)
- Phase 3.5 산출물 (교차 영향 검증 결과, 공유 파라미터 레지스트리)
- Phase 4 산출물 (검증 보고서 — "실행 착수 가능" 확인)
- 출력 형식: `templates/readiness-report.md`
- 도메인 팩 `templates/` (통합 산출물 형식, 있을 경우)

## 전제 조건

Phase 4에서 "실행 착수 가능"이 선언되었을 것.

## 절차

### Step 1: 산출물 목록 확인

아래 문서를 사용자에게 제시하고 확인:

1. **CLAUDE.md** — 프로젝트 지침
2. **_confirmed/project-charter.md** — Phase 1 확정
3. **_confirmed/glossary.md** — 용어 정의
4. **_confirmed/[컴포넌트명].md** — 각 Core 컴포넌트 확정 항목
5. **_confirmed/cross-impact-check.md** — Phase 3.5 교차 검증
6. **_confirmed/shared-parameter-registry.md** — 공유 파라미터 레지스트리
7. **sections/[섹션명].md** — 섹션별 기획서
8. **dependency-map.md** — 컴포넌트 간 의존 관계도
9. **DEVELOPMENT-BIBLE.md** — 개발 제작 바이블 (복사 또는 참조 링크)

### Step 1.5: 개발 기준 연결

`CLAUDE.md` 생성 시 아래 섹션을 포함한다:

```markdown
## 개발 기준
이 프로젝트의 구현은 DEVELOPMENT-BIBLE.md의 원칙을 따릅니다.
해당 문서가 프로젝트 루트에 없으면 Projects/DEVELOPMENT-BIBLE.md에서 복사합니다.

필수 참조 섹션:
- §6 입력값 검증 — 모든 사용자 입력에 적용
- §7 보안 체크리스트 — OWASP Top 10 2025 대응
- §10 테스트 전략 — 기능과 테스트 동시 작성
- §25 코드 리뷰 — PR 200줄 이하, 자체 리뷰 선행
- §28 런칭 전 최종 체크리스트 — 배포 전 필수 확인

프로젝트 유형별 추가 참조:
- 금전/결제 → §8 금전/결제 시스템
- 커뮤니티/UGC → §27 커뮤니티 & UGC 관리
- 모바일 앱 → §23 모바일/데스크톱/CLI 확장
- 백그라운드 작업 → §19 백그라운드 작업 & 큐
```

이 지침은 Claude, Codex(GPT), Gemini 어떤 엔진이 구현하든 동일하게 적용된다.

### Step 2: 문서 생성

**단일 진실 소스 원칙:** 하나의 수치는 하나의 `_confirmed/` 파일에만. 다른 파일은 참조(링크).

**`_confirmed/` 파일 형식:**
```markdown
# [컴포넌트명]

> 최종 갱신: [날짜]
> 주관 섹션: [섹션명]
> 참조 섹션: [섹션명1, 섹션명2]

## [확정] [항목명]
[수치/규칙/조건]

## [확정] [항목명] — Step-by-Step
| 단계 | 입력 | 처리 | 출력 |
|------|------|------|------|

## [보류] [항목명] (기한: [날짜])
방향: ___
```

**태그 전환 규칙:** `core/state-model.md` 참조.

### Step 3: 섹션별 기획서 매핑

도메인 팩에 섹션 분류 기준이 있으면 적용. 없으면 의존성 맵 기반으로 클러스터링하여 섹션 자동 분류.

**오너십 규칙:** 하나의 컴포넌트가 여러 섹션에 걸치면 주관 섹션 지정, 나머지는 참조.

### Step 4: 생성 후 검증

1. **중복 수치 스캔:** 동일 수치가 2개+ 파일에 → 참조(링크)로 전환
2. **의존성 맵 완전성:** 공유 파라미터 레지스트리의 모든 쌍이 `dependency-map.md`에 존재
3. **태그 감사:**
   - 필수 → 확정 변환 확인
   - 보류 → 기한 명시 확인, 기한 초과 시 미결 전환 확인
   - 미결 → `_confirmed/`에 잔존 불가
4. **입출력 계약 감사:** Phase 3 입출력 계약이 `_confirmed/`에 빠짐없이 기술

### Step 5: 검증 실패 시 복귀

- 중복 수치 불일치 → Phase 5 내에서 참조 전환
- 의존성 맵 누락 → Phase 5 내에서 보충
- 태그 감사 실패 (미결 잔존 / 잘못된 전환 / 보류 기한 초과) → Phase 3 해당 컴포넌트 Decision Card 복귀
- 입출력 계약 누락 → Phase 3 해당 컴포넌트 Decision Card 복귀

Phase 3 복귀 시 해당 컴포넌트만, Phase 3.5~4 재검증은 변경 범위만.

### Step 6: 통합 산출물 생성 (도메인 팩 위임)

도메인 팩 `templates/`에 통합 산출물 형식이 정의되어 있으면 해당 형식으로 생성.
없으면 Markdown 산출물만 생성 (이 단계 건너뜀).

## 산출물

```
<project-name>/
├── CLAUDE.md
├── _confirmed/
│   ├── project-charter.md
│   ├── glossary.md
│   ├── [컴포넌트-1].md
│   ├── [컴포넌트-2].md
│   ├── cross-impact-check.md
│   └── shared-parameter-registry.md
├── sections/
│   ├── [섹션-1].md
│   └── [섹션-2].md
├── dependency-map.md
└── changelog.md (Phase 6용 빈 파일)
```
