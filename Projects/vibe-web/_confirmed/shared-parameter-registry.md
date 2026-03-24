# 공유 파라미터 레지스트리

> 최종 갱신: 2026-03-24
> Phase 6 변경 관리 시 참조. 각 파라미터 수치/정의의 정본 위치를 명시.

| 파라미터 | 타입 | 주요 생성처 | 주요 소비처 | 정본 위치 |
|---------|------|-----------|-----------|---------|
| `userId` | string | 사용자 인증 | 전 컴포넌트 | 사용자 인증 모듈 |
| `postId` | string | 갤러리(업로드) | 갤러리 → 상세 → 명예의 전당 | gallery-system.md |
| `activityScore` | number | 등급 시스템 | 등급 시스템 내부 | grade-system.md |
| `expPoints` | number | 등급 시스템 | 등급 시스템 내부, 프로필 표시 | grade-system.md |
| `userLevel` | string (단계+레벨) | 등급 시스템 | 프로필, 명예의 전당 필터 | grade-system.md |
| `likeCount` | number | 갤러리+게시판 (전체 합산) | 명예의 전당 선정 기준 | hall-of-fame.md |
| `likeReceived` | number | 갤러리+게시판 (전체 합산) | 등급 시스템 activityScore +2pt | grade-system.md |
| `viewCount` | number | 작품 상세 페이지 진입 | 상세 페이지 표시용 전용 | detail-process.md |
| `uploadCount` | number | 갤러리 (갤러리 작품 전용) | 등급 시스템 activityScore +10pt | gallery-system.md |
| `commentCount` | number | 게시판+갤러리 (전체 합산) | 등급 시스템 activityScore +2pt | grade-system.md |
| `commentReceived` | number | 게시판+갤러리 (전체 합산) | 등급 시스템 activityScore +1pt | grade-system.md |
| `categoryId` | number (1~5) | 커뮤니티 게시판 | 게시판 라우팅, 쿨다운 체크 | community-board.md |

## [확정] activityScore 미포함 파라미터

| 파라미터 | 미포함 이유 |
|---------|-----------|
| `viewCount` | 조작 방지 (만장일치 결정) |

## [확정] 명예의 전당 미반영 파라미터

| 파라미터 | 미반영 이유 |
|---------|-----------|
| `viewCount` | 조작 방지, likeCount 단독 선정 (2:1 결정) |
| `activityScore` | HoF는 likeCount 단독 기준 |
