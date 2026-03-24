# 기술 스택 (DEVELOPMENT-BIBLE §1 기반)

> 최종 갱신: 2026-03-24
> 근거: DEVELOPMENT-BIBLE §1 "커뮤니티/포럼" + "MVP/1인 개발" 교차 적용

## [확정] 스택

| 구분 | 선택 | 근거 (BIBLE §) |
|------|------|---------------|
| 프레임워크 | Next.js (App Router) | §1 MVP/1인 → 풀스택 프레임워크 |
| 언어 | TypeScript (strict mode) | §2 첫날 설정 |
| DB | PostgreSQL (Prisma ORM) | §1 커뮤니티 → PostgreSQL. §3 ID는 CUID |
| 인증 | NextAuth (OAuth) | §5 NextAuth + OAuth |
| 스타일링 | Tailwind CSS | PLANNING.md 확정 |
| 상태관리 | React Query (서버) + Zustand (클라이언트) | §15 상태관리 선택 기준 |
| 배포 | Vercel | §13 Next.js 기본 배포 환경 |
| 파일 스토리지 | Vercel Blob 또는 R2 | §20 파일은 스토리지, 메타만 DB |
| 검색 | PostgreSQL Full-text (MVP) → Meilisearch (v2) | §27 LIKE 금지 |
| 테스트 | Vitest | §10 테스트 전략 |

## [확정] 환경변수 (§2)

```
DATABASE_URL=
NEXTAUTH_SECRET=           # 32자 이상
NEXTAUTH_URL=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
BLOB_READ_WRITE_TOKEN=     # 파일 스토리지
```
