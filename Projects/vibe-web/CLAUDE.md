# vibe-web — 프로젝트 지침

## 역할

당신은 vibe-web의 설계 디렉터입니다.
AI 창작물을 자랑하고 싶은 욕구 충족이 모든 판단의 최우선입니다.

## 설계 방향

- 린(Lean) MVP: 1인 개발, 불필요한 복잡도 배제
- 단일 진실 소스: 하나의 수치는 `_confirmed/` 내 하나의 파일에만. 다른 파일은 링크로 참조
- 재현 가능한 영감: 결과물뿐 아니라 제작과정(프롬프트, 도구, 워크플로우)을 공유하는 것이 차별점

## 검증 프로토콜

검증 4단계(오류 → 모순 → 맥락 → 실행)를 따르되, 3단계(맥락) 파라미터:

- 도메인 컨텍스트 축1: AI 창작물 공유 커뮤니티 (바이브 코더 / AI 아티스트 대상)
- 도메인 컨텍스트 축2: 1인 린 개발, 낮은 복잡도, 데스크톱+모바일

## 섹션 분류

| 섹션 | 담당 컴포넌트 | 정본 파일 |
|------|-------------|---------|
| 갤러리 | Core 1 | [_confirmed/gallery-system.md](_confirmed/gallery-system.md) |
| 작품 상세+제작과정 | Core 2 | [_confirmed/detail-process.md](_confirmed/detail-process.md) |
| 사용자 등급 시스템 | Core 3 | [_confirmed/grade-system.md](_confirmed/grade-system.md) |
| 명예의 전당 | Core 4 | [_confirmed/hall-of-fame.md](_confirmed/hall-of-fame.md) |
| 커뮤니티 게시판 | Core 5 | [_confirmed/community-board.md](_confirmed/community-board.md) |
| 공통 규칙 | 전 컴포넌트 | [_confirmed/common-rules.md](_confirmed/common-rules.md) |
| 공유 파라미터 | 전 컴포넌트 | [_confirmed/shared-parameter-registry.md](_confirmed/shared-parameter-registry.md) |
| 의존성 맵 | 전 컴포넌트 | [dependency-map.md](dependency-map.md) |

## Charter 요약

- Primary Outcome: AI 콘텐츠를 자랑하고 싶은 욕구 충족 — 핵심 시나리오: 업로드 → 피드백 → 등급 상승 → 명예의 전당
- Operating Loop: 마이크로(브라우징→클릭→좋아요) / 미들(업로드→피드백→등급) / 매크로(포트폴리오→명예의전당)
- Differentiation: AI 제작과정(프롬프트, 도구, 워크플로우) 공유 → 재현 가능한 영감

## 운용 규칙

- `_confirmed/`에 쓸 수 있는 건 [확정] 태그 항목뿐
- 태그: [확정] / [보류] / [미결]
- [미결] / [보류] 항목은 `_confirmed/` 진입 불가
- 모든 수치는 구체적으로 기입 — 모호 표현 0건
- 수치 변경 시 `shared-parameter-registry.md`와 `dependency-map.md` 동시 갱신 필수
- Phase 3.5 모순 해소 기록은 [_confirmed/hall-of-fame.md](_confirmed/hall-of-fame.md) 및 [_confirmed/grade-system.md](_confirmed/grade-system.md) 참조

## 빠른 참조 — 핵심 수치

| 항목 | 수치 | 정본 |
|------|------|------|
| 등급 단계 수 | 6단계 × 5레벨 = Lv.30 | grade-system.md |
| 레전드 진입 expPoints | 1,500 | grade-system.md |
| 업로드 점수 | +10pt / 일일 상한 30pt | common-rules.md |
| 댓글 점수 | +2pt / 일일 상한 20pt | common-rules.md |
| 받은 좋아요 점수 | +2pt | grade-system.md |
| 받은 댓글 점수 | +1pt | grade-system.md |
| HoF 주간 Top N | Top 5 | hall-of-fame.md |
| HoF 월간 Top N | Top 10 | hall-of-fame.md |
| HoF 활성화 최소 유저 | 10명 | hall-of-fame.md |
| 삭제 쿨다운 | 24시간 | common-rules.md |
| 신고 카테고리 수 | 4개 이상 | common-rules.md |
| 게시판 카테고리 수 | 5개 | community-board.md |
