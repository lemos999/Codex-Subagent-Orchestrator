# vibe-web 설계 문서 읽는 법

## 한 줄 요약

`CLAUDE.md` → `_confirmed/project-charter.md` → `_confirmed/wireframe.md` 순서로 읽으면 전체 그림이 잡힙니다.

---

## 문서 구조

```
Projects/vibe-web/
├── CLAUDE.md                    ← 1. 여기서 시작. 프로젝트 지침 + 전체 파일 맵
├── _confirmed/                  ← 2. 확정된 설계 (정본)
│   ├── project-charter.md       ←    프로젝트 정체성 (왜 만드는가)
│   ├── wireframe.md             ←    화면 구조 + 흐름도 + DB 스키마 + 라우트
│   ├── tech-stack.md            ←    기술 스택 결정
│   ├── gallery-system.md        ←    Core 1: 갤러리
│   ├── detail-process.md        ←    Core 2: 작품 상세 + 제작과정
│   ├── grade-system.md          ←    Core 3: 등급 시스템
│   ├── hall-of-fame.md          ←    Core 4: 명예의 전당
│   ├── community-board.md       ←    Core 5: 게시판
│   ├── auth-system.md           ←    인증 (GitHub + Google OAuth)
│   ├── profile-portfolio.md     ←    프로필 / 포트폴리오
│   ├── search.md                ←    검색
│   ├── common-rules.md          ←    공통 규칙 (점수, 악용 방지, 제재)
│   └── shared-parameter-registry.md ← 컴포넌트 간 공유 파라미터
├── dependency-map.md            ← 3. 컴포넌트 간 의존 관계
└── docs/
    ├── PLANNING.md              ←    원본 기획 (참고용)
    ├── phase3-confirmed.md      ←    Phase 3 확정 데이터 (참고용)
    └── HOW-TO-READ.md           ←    이 파일
```

---

## 읽는 순서

### 전체 파악 (5분)

1. **`CLAUDE.md`** — 프로젝트 목적, Charter 요약, 전체 파일 맵
2. **`_confirmed/project-charter.md`** — Primary Outcome, Operating Loop, Differentiation, Target
3. **`_confirmed/wireframe.md`** — 11개 페이지 목록, 화면 흐름도, DB 스키마

### 구현 계획 수립 시 (추가 15분)

4. **`_confirmed/tech-stack.md`** — Next.js + PostgreSQL + Prisma + NextAuth + Vercel
5. **`dependency-map.md`** — 컴포넌트 간 의존 관계 → 구현 순서 결정에 핵심
6. **`_confirmed/common-rules.md`** — 점수 체계, 악용 방지, 제재 절차 → 전 컴포넌트에 적용

### 개별 컴포넌트 구현 시

각 `_confirmed/[컴포넌트].md`를 읽되, 반드시 확인할 것:
- **컴포넌트 인터페이스 테이블** — 입력/출력/실패 시 기본값
- **`shared-parameter-registry.md`** — 이 컴포넌트가 사용하는 공유 파라미터

---

## 핵심 규칙

| 규칙 | 설명 |
|------|------|
| **단일 진실 소스** | 수치는 하나의 파일에만 정의. 다른 파일은 링크 참조 |
| **[확정] 태그** | `_confirmed/` 내 모든 항목은 [확정] 상태. 구현 시 그대로 따르면 됨 |
| **공통 규칙 우선** | 점수, 악용 방지, 제재는 `common-rules.md`가 정본 |
| **DEVELOPMENT-BIBLE 참조** | 구현 패턴은 `Projects/DEVELOPMENT-BIBLE.md` 기준 |

---

## 구현 순서 추천

`dependency-map.md` 기반, 의존성 상위부터:

```
Phase 1: 기반
  └── 인증 (auth-system) + DB 스키마 + 프로젝트 스캐폴딩

Phase 2: Core (의존성 순)
  ├── 갤러리 시스템 (gallery-system) — 핵심 UI
  ├── 작품 상세 + 제작과정 (detail-process) — 갤러리 의존
  └── 커뮤니티 게시판 (community-board) — 독립적

Phase 3: 연결
  ├── 등급 시스템 (grade-system) — 갤러리+게시판 의존
  ├── 명예의 전당 (hall-of-fame) — 갤러리+게시판+등급 의존
  └── 프로필/포트폴리오 (profile-portfolio) — 등급 의존

Phase 4: 보조
  ├── 검색 (search)
  └── 신고/제재 (common-rules 내)
```
