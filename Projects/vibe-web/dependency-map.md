# 컴포넌트 의존성 맵

> 최종 갱신: 2026-03-24

| 컴포넌트 A | → 영향 → | 컴포넌트 B | 공유 파라미터 | 영향 설명 | A 변경 시 B 재검증 |
|-----------|---------|-----------|-------------|----------|-----------------|
| 갤러리(Core 1) | → | 작품 상세(Core 2) | `postId` | 카드 클릭 → 상세 페이지 진입 | postId 구조 변경 시 상세 페이지 라우팅 재검증 |
| 갤러리(Core 1) | → | 등급 시스템(Core 3) | `uploadCount` | 업로드 이벤트 → activityScore +10pt | 업로드 이벤트 발생 방식 변경 시 등급 계산 재검증 |
| 갤러리(Core 1) | → | 명예의 전당(Core 4) | `likeCount` | 갤러리 좋아요 → HoF 합산 | likeCount 집계 방식 변경 시 HoF 선정 재검증 |
| 작품 상세(Core 2) | → | 등급 시스템(Core 3) | `viewCount` (미반영) | viewCount는 activityScore 미반영 확정 | viewCount 정책 변경 시 등급 시스템 검토 |
| 등급 시스템(Core 3) | → | 프로필 | `userLevel`, `expPoints` | 등급 산정 → 프로필 표시 | 등급 구조 변경 시 프로필 표시 재검증 |
| 등급 시스템(Core 3) | → | 명예의 전당(Core 4) | `userLevel` | 등급 기반 HoF 필터 | 등급 단계 변경 시 HoF 필터 재검증 |
| 명예의 전당(Core 4) | → | 홈 페이지 | 주간/월간 위젯 데이터 | HoF 결과 → 홈 위젯 출력 | HoF 갱신 주기 변경 시 홈 위젯 재검증 |
| 커뮤니티 게시판(Core 5) | → | 등급 시스템(Core 3) | `commentCount`, `likeReceived`, `commentReceived` | 게시판 활동 → activityScore 반영 | 게시판 카테고리 변경 시 등급 점수 집계 재검증 |
| 커뮤니티 게시판(Core 5) | → | 명예의 전당(Core 4) | `likeCount` | 게시판 좋아요 → HoF 합산 | likeCount 집계 방식 변경 시 HoF 선정 재검증 |
| 공통 규칙 | → | 전 컴포넌트 | 삭제 쿨다운, 좋아요 유일성, 업로드 상한, 신고 유형 | 전역 규칙 변경은 전 컴포넌트에 영향 | 공통 규칙 변경 시 전 컴포넌트 재검증 필수 |

## 단일 진실 소스 원칙

- 하나의 수치는 하나의 `_confirmed/` 파일에만 기재
- 다른 파일은 해당 파일 링크로 참조
- 정본 위치: [shared-parameter-registry.md](_confirmed/shared-parameter-registry.md) 참조
