# Project Status — Current

> 이 파일은 모든 AI 엔진(Claude, Codex/GPT, Gemini)이 참조합니다.
> 이 폴더에서 작업하는 AI는 이 파일을 읽고 현재 상태를 파악하세요.
> 완료된 작업은 분기별 아카이브로 이동합니다.

## Project: Subagent Orchestrator

멀티 AI 엔진(Claude, Codex/GPT, Gemini)을 조율하는 오케스트레이션 시스템.

## 핵심 구성 요소

| 구성 요소 | 상태 | 경로 |
|---|---|---|
| TS 런처 (primary) | 완료 | `packages/launcher/` |
| PS 런처 (legacy fallback) | 유지 | `skills/codex-subagent-orchestrator/scripts/` |
| WKI (Workspace Knowledge Index) | 완료 | `workspace-knowledge-index/` |
| Claude 오케스트레이터 (/sub) | 완료 | `skills/claude-subagent-orchestrator/` |
| 멀티엔진 오케스트레이터 (/submix) | 완료 | `.claude/skills/submix/` |
| Gemini 오케스트레이터 | 완료 | `skills/gemini-subagent-orchestrator/` |
| Codex 오케스트레이터 | 완료 | `skills/codex-subagent-orchestrator/` |
| **토론 시스템 (/discuss)** | **Phase 1~3 완료** | `packages/launcher/src/discussion/` |
| **큐 러너 TS** | **Phase 1~2 완료** | `packages/launcher/src/queue/` |
| **범용 설계 디렉터 (/design)** | **완료** | `skills/design-director/` + `.claude/skills/design/` |
| **게임 기획 디렉터 (/gdd)** | **완료** | `skills/game-design-director/` + `.claude/skills/gdd/` |
| **Intelligent Delegation 프레임워크** | **완료** | `packages/launcher/src/` + `config/capabilities/` + 기획서 `Projects/intelligent-delegation/` |

## 다음 작업 (우선순위 순)

1. **WKI 추가 개선** — Mean nDCG 0.819, Line-scoped 0.655 (Min 0.630)
2. **/design domains/software/ 실전 사용** — 실제 SW 프로젝트에 software 도메인 팩 적용 검증 (trust.validated_count → 1)

## 최근 완료 (2026-03-26)

- **/design 실전 테스트 + software 도메인 팩 생성**
  - /design Phase 0~5 전 파이프라인 실전 검증 완료
  - `skills/design-director/domains/software/` 4개 파일 생성 (profile.yaml, heuristics.md, catalogs/components.md, catalogs/decisions.md)
  - SW 특화: 용어 매핑, 맥락 검증 3축(아키텍처/운영/보안), VCT 보조질문 4개, 6범주 컴포넌트 카탈로그, ~35개 결정 항목 레퍼런스
  - SKILL.md 도메인 목록 업데이트 (generic + software)
- **WKI nDCG 0.781 → 0.819 (+4.9%)**
  - Heading 다중 용어 매칭 보너스 (3+ 매칭 시 +0.15)
  - Cross-encoder 후보 풀 확대 (topK*2 → topK*3)
  - Structural boost 가중치 재조정 (0.15 → 0.20)
  - Noise path 추가 (intelligent-delegation 기획 문서)
  - Line-scoped: 0.568 → 0.655 (+15.3%), Min: 0.374 → 0.630 (+68.4%)
- **/discuss WKI 마이크로 맥락 자동 주입**
  - Round 2+: 모더레이터 요약에서 미해결 쟁점 추출 → WKI 재검색 → 마이크로 맥락 주입
  - 모더레이터에 WKI 맥락 전달 (R1: 초기 맥락, R2+: 마이크로 맥락) + 팩트체크 지시
  - 결론(Conclusion)에 초기 WKI 맥락 전달
  - 마이크로 맥락 per-round evidence 저장
  - 빌드 PASS, 테스트 63/63 PASS
- **WKI nDCG 0.769 → 0.781 (+1.6%)**
  - filename 기반 교차 디렉터리 중복 제거 (max 4 per basename)
  - 동일 파일이 claude/codex/gemini/ 디렉터리에 복사된 경우 결과 다양성 향상
  - File-only 0.907→0.914, Line-scoped 0.548→0.568
- **WKI 인덱스 정상화 + /discuss WKI 연동 강화**
  - 인덱스 오염 해결: 부분 인덱스(448청크) → 정상 full index(579파일, 4339청크)
  - nDCG baseline 재측정: 0.769 (File-only 0.908, Line-scoped 0.548)
  - 이전 0.793은 부분 인덱스 기준으로 직접 비교 불가
  - /discuss Conclusion에 WKI 맥락 주입 추가
  - /discuss Moderator에 WKI 맥락 주입 + 코드베이스 팩트체크 지시 추가
  - /discuss per-round 마이크로 맥락 증거 파일 저장 추가
  - BM25 앙상블 검토: FTS5가 이미 BM25 사용 중 — 별도 구현 불필요
  - 미커밋 FTS stop words 변경 revert (regression 유발)
  - 검증: Build PASS, Test 63/63 PASS
- **Intelligent AI Delegation 프레임워크 전체 구현** (논문 arxiv:2602.11865 기반)
  - /discuss 3라운드 토론 → /design Phase 0~5 기획(16파일) → /submix 3단계 구현
  - Core 6개 (C1 Capability Registry, C2 Authority Profile, C3 Ambiguity Gate, C4 Hash-Chain, C5 Behavioral Metrics, C6 Risk Matrix)
  - Support 10개 (S1~S10, 5개 스킬 프롬프트 적용)
  - TS 코드: capability-registry.ts, authority.ts, chain-manager.ts, risk-matrix.ts, trust-registry.ts 확장
  - YAML: config/capabilities/{claude,codex,gemini}.yaml (엔진별 8차원 역량 프로파일)
  - 검증: 빌드 PASS, 테스트 44/44 PASS, /submix 교차리뷰 ACCEPTED
  - 기획서: Projects/intelligent-delegation/, Evidence: subagent-runs/discuss/intelligent-delegation-apply-2026-03-26/

## 최근 완료 (2026-03-25)

- `Projects/vibe-web` 로컬 데모 문서 정리
  - `.env.local.example` 추가로 로컬 demo auth 진입값을 명시
  - `README.md` 추가로 로컬 실행, 샘플 라우트, discovery 플래그 동작을 정리
  - `docs/TEST-RESULT-2026-03-25.md`를 실제 원인 기준으로 수정
  - 잘못된 샘플 ID에 의한 404와 discovery 플래그 기반 404를 구분해 문서화
- `Projects/vibe-web` Preview Ready 정리 완료
  - Sentry 초기화(`instrumentation.ts`, `instrumentation-client.ts`, `sentry.*.config.ts`)와 서버 액션 예외 캡처 추가
  - `.env.example`, `vercel.json`, `scripts/check-preview-env.mjs`, `docs/PREVIEW-DEPLOY.md`로 Preview 배포 기준 정리
  - 핵심 화면과 정책 문서, 날짜 포맷, demo/seed 콘텐츠를 한국어 우선으로 정리
  - `docs/IMPLEMENTATION-STATUS.md`, `docs/COMPLETION-ROADMAP.md`, `docs/HOW-TO-READ.md`를 현재 상태 기준으로 갱신
  - 검증: `npm run lint`, `npm run test` (10 passed), `npm run build`, `npm run test:e2e` (2 passed)
  - 참고: `npm run preview:env:check`는 실제 시크릿이 없어서 실패하며, 현재 누락값은 `DATABASE_URL`, `NEXTAUTH_URL`, `NEXTAUTH_SECRET`, `BLOB_READ_WRITE_TOKEN`, `CRON_SECRET`, OAuth provider pair
- `Projects/vibe-web` 최종 완성 로드맵 문서 추가
  - `docs/COMPLETION-ROADMAP.md` 작성
  - 구현 상태 문서와 읽기 안내 문서에서 로드맵 링크 연결
- `Projects/vibe-web` 아키텍처 정돈 리팩터링
  - `docs/ARCHITECTURE.md` 기준으로 action/domain/revalidation 책임을 재정렬
  - 입력 검증 스키마를 `lib/validators.ts`로 분리하고 공통 revalidation 유틸 추가
  - 작품/게시글 상세 페이지의 공통 섹션을 묶어 중복 마크업과 액션 폼 구조를 정리
  - 버튼 스타일을 링크와 공유해 마크업 일관성 개선
  - 검증: `npm run lint`, `npm run test` (9 passed), `npm run build`

## 최근 완료 (2026-03-24)

- `Projects/vibe-web` 문서 전용 설계를 실행 가능한 Next.js MVP로 구현
  - App Router + Tailwind + Prisma(PostgreSQL 스키마) + Vitest 골격 추가
  - 갤러리/업로드/상세/게시판/프로필/설정/명예의 전당/검색 라우트 구현
  - 점수 규칙, HoF 정렬, 신고 3건 자동 숨김, 데모 세션 기반 보호 라우트 동작
  - 검증: `npm run lint`, `npm run test` (9 passed), `npm run build`
- `/design` 범용 설계 디렉터 스킬 완성 (26개 파일, Watchdog 24기 교차 검수)
  - /gdd 골격 포크 → 게임 특화 제거 → 도메인 팩 플러그인 구조
  - Phase 0~6 + Mode B + 멀티엔진(Claude+GPT+Gemini) 지원
  - generic 도메인 팩 완비, /sub + /submix 스펙 4개
- 맥락 공유 구조 개선:
  - CLAUDE.md 생성 (포인터 3줄), AGENTS.md에 project-status 참조 추가
  - /design, /gdd SKILL.md에 project-status 참조 추가
  - 3엔진 감사(/submix) → CLAUDE.md 경량화, memory 정본 규칙 적용
- WKI 검색 파이프라인: nDCG 0.686 → 0.744 (+8.5%)

## 이전 완료 (2026-03-17~22)

- TS 런처 Phase 0~4 (PS 런처 대체)
- WKI 로컬 임베딩 (paraphrase-multilingual-MiniLM-L12-v2)
- WKI 맥락 자동 주입 (모든 엔진 동일 적용)
- WKI 한글 Query Expansion
- WKI Eval 시스템 (Mean nDCG 0.686, Median 0.714 — 평가기 dedupe 수정 후 정상화)
- WKI 자동 증분 인덱싱
- WKI 토론 이력 인덱싱 (노이즈 파일 제외)
- Evidence 기록 강화
- 골든 테스트 4/4 PASS
- 토론 시스템 Phase 1~3 완료:
  - 3자 토론 (Claude + Codex/GPT + Gemini) 교차 검증
  - 실시간 상태 표시 (엔진별 응답 시간)
  - 페르소나 시스템 (토픽 기반 자동 생성 + 수동 지정 + 기본 프리셋)
  - 역할(role) 커스터마이징
  - 실전 테스트 3회 완료
- 큐 러너 TS 전환 Phase 1 완료:
  - PS 큐 러너(1,700줄) → TS(1,514줄, 10개 모듈)
  - local-json, local-files, mock-json(별칭) 트래커
  - PS 설정 호환 계층 (queue-compat)
  - 핑거프린트/blocked_by/백오프 PS 동작 일치
  - TS CLI --json 모드 추가
  - /submix 검증(3엔진) + GPT 5.4 watchdog 리뷰 2회
  - PS 호환성 수정 4건 (priority, blocked_by, isEligibleNow, hooks)
  - 골든 테스트 36/36 PASS
  - Phase 2: Linear GraphQL 트래커 (/submix 검증 완료)
- WKI 검색 개선 추가:
  - Negative sampling (노이즈 경로 패널티)
  - Multi-vector search (fail-soft)
  - Re-ranking 강화 (heading/filePath + stop word 필터링)
  - 평가기 dedupe 수정 (nDCG > 1 방지)

## 주요 명령어

```bash
# TS 런처 실행
node packages/launcher/dist/cli.js --spec <spec.json>

# WKI 인덱싱
node workspace-knowledge-index/dist/index.js index

# WKI 검색
node workspace-knowledge-index/dist/index.js search "<query>" --top 5

# WKI 상태 확인
node workspace-knowledge-index/dist/index.js status

# WKI 검색 품질 평가
node workspace-knowledge-index/dist/index.js eval workspace-knowledge-index/eval/gold-set-v2.json

# 큐 러너 실행
node packages/launcher/dist/queue/queue-cli.js --config <queue.json>
node packages/launcher/dist/queue/queue-cli.js --config <queue.json> --max-polls 10

# 토론 실행
node packages/launcher/dist/discussion/discuss-cli.js "주제"
node packages/launcher/dist/discussion/discuss-cli.js --auto "주제"

# WKI lock 문제 시
rm .knowledge/.wki.lock
```

## 문제 해결

문제 발생 시 `problem-resolution-log.md`를 먼저 확인하세요. 8건의 해결 사례가 기록되어 있습니다.

## 규칙

- **세션 시작 시 WKI 인덱싱 필수** — 첫 작업 전에 `node workspace-knowledge-index/dist/index.js index` 를 1회 실행. 다른 AI/세션의 변경사항이 반영됨. 변경 없으면 즉시 반환 (0초).
- 파일 삭제 시 반드시 사용자에게 확인 후 진행
- 이 폴더에는 별도 프로젝트 폴더가 존재할 수 있음 (game-design-director, trading-quest 등)
- Evidence 기록은 필수 — 결과 보고 전에 반드시 기록

## Latest Completed (2026-03-26)

- `packages/launcher` C4 Hash-Chained Evidence + C6 Risk Matrix implementation completed.
  - Added salted SHA-256 helpers in `packages/launcher/src/common/fs-helpers.ts` and introduced `packages/launcher/src/evidence/chain-manager.ts` with stable worker-result hashing, append-time chain verification, `.broken` preservation for malformed chains, and per-run `chain.json` updates.
  - Extended `packages/launcher/src/types/manifest.ts` with optional `evidence` metadata and wired `packages/launcher/src/orchestrator.ts` + `packages/launcher/src/evidence/manifest-builder.ts` so launcher manifests now record `chain_index`, `prev_hash`, `current_hash`, `salt`, and `spec_sha256`.
  - Added `packages/launcher/src/supervisor/risk-matrix.ts` with the 2-axis matrix, default task risk table, upward-only overrides, and inherited security gates.
  - Expanded launcher regression coverage with `packages/launcher/tests/chain-manager.test.mjs`, `packages/launcher/tests/manifest-builder.test.mjs`, and `packages/launcher/tests/risk-matrix.test.mjs`; updated `packages/launcher/package.json` so `npm run test` executes the full launcher test suite.
  - Verification completed in `packages/launcher`: `npm run build`, `npm run test` (44/44).

## Latest Completed (2026-03-25)

- `Projects/vibe-web` post-detail QA regressions fixed and redeployed to production.
  - Allowed Vercel Blob public subdomains in `Projects/vibe-web/next.config.ts`, which restores uploaded gallery image rendering for store-specific Blob hosts.
  - Added explicit view-tracking helpers in `Projects/vibe-web/lib/view-tracking.ts` and switched gallery/board detail pages to skip view increments on action-return refreshes, so likes/comments/reports no longer inflate `viewCount`.
  - Updated `Projects/vibe-web/app/actions.ts` to use PRG-style redirects after comment/like/report server actions, which clears the stuck pending state and keeps detail-page interactions predictable under refresh.
  - Updated `Projects/vibe-web/components/sections/content-actions.tsx` to disable self-like attempts on the author's own post and show an explanatory message instead of silently no-oping.
  - Added regression coverage with `Projects/vibe-web/tests/view-tracking.test.ts` and refreshed `Projects/vibe-web/tests/e2e/smoke.spec.ts` to cover own-post like disabling, non-owner likes, and stable view counts after commenting.
  - Verification completed in `Projects/vibe-web`: `npm run lint`, `npm run test` (12/12), `npm run build`, `npx playwright test tests/e2e/smoke.spec.ts --reporter=line` (2/2), followed by `npx vercel --prod` and production alias refresh at `https://vibe-web-rose.vercel.app`.
- `Projects/vibe-web` board/upload form validation UX hardened and redeployed to production.
  - Rewrote `Projects/vibe-web/app/board/new/page.tsx` and `Projects/vibe-web/app/upload/page.tsx` with UTF-8 Korean copy plus native `minLength`/`maxLength` hints so invalid summaries, bodies, and tags are blocked before submit.
  - Updated `Projects/vibe-web/app/actions.ts` to convert board/upload validation failures into redirects with user-facing error messages instead of generic server-component crashes.
  - Replaced corrupted validation text in `Projects/vibe-web/lib/validators.ts` and added `getValidationMessage()` so server actions can reuse the first Zod issue safely.
  - Refreshed `Projects/vibe-web/tests/e2e/smoke.spec.ts` with a regression that verifies short board summaries stay on the form instead of crashing; set `Projects/vibe-web/playwright.config.ts` to always boot a fresh dev server so memory-backed moderation state does not leak between runs.
  - Verification completed in `Projects/vibe-web`: `npm run lint`, `npm run test` (12/12), `npm run build`, `npx playwright test tests/e2e/smoke.spec.ts --reporter=line` (3/3), followed by `npx vercel --prod` and production alias refresh at `https://vibe-web-rose.vercel.app`.
- `Projects/vibe-web` minimum-length restrictions relaxed across writer flows and redeployed to production.
  - Reduced `Projects/vibe-web/lib/validators.ts` minimum requirements for title, summary, body, process notes, tags, comments, profile name, and bio from multi-character thresholds to simple non-empty checks.
  - Removed native `minLength` blockers from `Projects/vibe-web/app/board/new/page.tsx` and `Projects/vibe-web/app/upload/page.tsx`, keeping only required/max-length constraints and lighter helper copy so short free-form input is not blocked.
  - Replaced the previous short-summary failure smoke with a success-path regression in `Projects/vibe-web/tests/e2e/smoke.spec.ts`, and added `Projects/vibe-web/tests/validators.test.ts` to verify short Korean-tag inputs pass while blank values still fail.
  - Updated `Projects/vibe-web/eslint.config.mjs` to ignore `test-results/**` and `playwright-report/**`, which avoids ENOENT lint failures after Playwright cleanup.
  - Verification completed in `Projects/vibe-web`: `npm run lint`, `npm run test` (15/15), `npm run build`, `npx playwright test tests/e2e/smoke.spec.ts --reporter=line` (3/3), followed by `npx vercel --prod` and production alias refresh at `https://vibe-web-rose.vercel.app`.
  - Follow-up docs: added `Projects/vibe-web/docs/POST-MVP-BACKLOG.md` to track post-MVP items currently requested by the user (`삭제 확인 팝업`, `게시글 수정`).
- `Projects/vibe-web` Vercel project link established for preview handoff.
  - Local `npx vercel link` completed and `.vercel/project.json` now points to Vercel project `vibe-web`.
  - Follow-up finding: `vercel env add ... preview` is currently returning a branch/git-repository requirement for this non-Git-connected project, so preview environment variables should be entered from the Vercel dashboard instead of relying on CLI automation.
  - Follow-up fix: `Projects/vibe-web/vercel.json` HoF cron schedule was lowered from hourly to daily so Hobby-plan preview deployments are not blocked by Vercel cron limits.
  - Follow-up fix: Vercel deployment type-check was blocked by an implicit `any` in `Projects/vibe-web/app/login/page.tsx`; the login page now explicitly types the demo user list from shared app types, and local `npm run build` / `npm run lint` pass again.
  - Follow-up fix: Vercel build also failed before Prisma client generation in a clean install, so `Projects/vibe-web/package.json` now runs `prisma generate` during `postinstall` and before `build`; local `npm run db:generate`, `npm run build`, and `npm run lint` pass.
  - Follow-up fix: `Projects/vibe-web/scripts/preview-env-lib.mjs` now warns when `DATABASE_URL` is present but not shaped like a PostgreSQL connection string, which catches pasted Prisma snippets before the next preview deploy.
  - Follow-up progress: Preview cloud env now contains `DATABASE_URL`, `NEXTAUTH_*`, `GOOGLE_CLIENT_*`, `BLOB_READ_WRITE_TOKEN`, `CRON_SECRET`, and the beta flags; the remaining preview verification caveat is that unauthenticated access still hits Vercel Authentication, so OAuth smoke testing should either use an authenticated Vercel browser session or temporarily disable preview deployment protection.
  - Follow-up progress: production deployment succeeded at `https://vibe-web-rose.vercel.app`, the login page now renders the Google sign-in button, and `/api/health` returns `database=true`, `blob=true`, `sentry=false`, so the only remaining health gap is missing Sentry env configuration.
  - Follow-up fix: production login failures traced back to an unapplied Prisma migration and Prisma 7 runtime setup gaps. `migration.sql` was rewritten without BOM, Prisma runtime/seed switched to `@prisma/adapter-pg`, production migration `20260325000000_init` was recovered and applied, seed data was loaded, login rate-limit rows were cleared, and production was redeployed.
- `Projects/vibe-web` operational upgrade implemented on top of the MVP scaffold.
  - Replaced the in-memory-first repository entrypoint with a Prisma-capable repository split and added Prisma config, schema updates, seed data, and an initial SQL migration under `Projects/vibe-web/prisma/migrations/20260325000000_init/`.
  - Swapped demo cookie auth for NextAuth session auth with GitHub/Google provider hooks, demo credentials fallback, closed-beta allowlist checks, login rate limiting, and suspended/banned sign-in blocking.
  - Moved gallery upload to real file input handling with MIME/size validation, Vercel Blob support, and persisted upload metadata.
  - Added admin moderation surface at `Projects/vibe-web/app/admin/moderation/page.tsx`, health/cron endpoints, policy pages, CI workflow updates, Playwright smoke coverage, and feature flags for beta/discovery surfaces.
  - Cleaned corrupted UI copy in key shared surfaces and replaced the broken memory seed with a smaller English dataset that includes `Admin Maker` and `Process Maker` for local CLI/demo flows.
  - Verification completed in `Projects/vibe-web`: `npm run lint`, `npm run test`, `npm run build`, `npm run test:e2e`.
- `Projects/vibe-web` UX polish and Korean-first cleanup applied for preview readiness.
  - Added `lib/site.ts`, `app/loading.tsx`, and `components/ui/empty-state.tsx` to centralize site URL metadata, loading skeletons, empty states, and safer preview/production SEO behavior.
  - Updated the main navigation, footer, home, login, upload, settings, board, search, profile, moderation, detail pages, and policy pages to replace corrupted copy with readable Korean UI strings.
  - Added skip-to-content accessibility affordance, preview-safe `robots.txt` behavior, canonical metadata wiring, and public sitemap generation from environment-aware site URLs.
  - Refreshed Playwright smoke expectations to match the stabilized Korean UI contract and verified the end-to-end auth/upload/moderation flow again.
  - Verification completed in `Projects/vibe-web`: `npm run lint`, `npm run test`, `npm run build`, `npm run test:e2e`.
- `Projects/vibe-web` preview preflight tightened for actual deployment handoff.
  - Rewrote `Projects/vibe-web/docs/PREVIEW-DEPLOY.md` in readable Korean with the real preview sequence, required secrets, manual QA checklist, and rollback notes.
  - Updated `Projects/vibe-web/scripts/check-preview-env.mjs` to load `.env.local` / `.env`, warn when `.vercel/project.json` is missing, and report preview blockers without false negatives for locally defined vars.
  - Current local preflight result: missing `DATABASE_URL`, `BLOB_READ_WRITE_TOKEN`, `CRON_SECRET`, and at least one OAuth provider pair; warnings remain for missing Vercel link, `ENABLE_DEMO_AUTH=true`, and localhost `NEXTAUTH_URL`.
  - Verification completed in `Projects/vibe-web`: `npm run preview:env:check` (expected fail with concrete blockers), `npm run lint`.
- `Projects/vibe-web` core handoff docs normalized for CLI use.
  - Rewrote `README.md`, `docs/IMPLEMENTATION-STATUS.md`, and `docs/HOW-TO-READ.md` in readable Korean so local run, preview prep, and document navigation are no longer blocked by mojibake.
  - Added `.env.preview.example` and allowed it in `.gitignore` so preview env setup has a dedicated template separate from local demo defaults.
  - Verification completed in `Projects/vibe-web`: `npm run lint`.
- `Projects/vibe-web` preview handoff shape refined into input-sheet format.
  - Added `docs/PREVIEW-INPUT-SHEET.md` with the exact Vercel Preview env list, source-of-truth notes, OAuth callback URLs, current blockers, and post-input commands.
  - Linked the new input sheet from `README.md`, `docs/IMPLEMENTATION-STATUS.md`, `docs/HOW-TO-READ.md`, and `docs/PREVIEW-DEPLOY.md` so the preview setup path is now `status -> deploy guide -> input sheet`.
- `Projects/vibe-web` preview workflow extended into report + QA checklist.
  - Added `scripts/preview-env-lib.mjs` and `scripts/preview-report.mjs`, then exposed `npm run preview:report` so the current preview blockers and flag state can be read in one command.
  - Added `docs/PREVIEW-QA-CHECKLIST.md` and linked it from the README / status / deploy docs, making the flow `preview:report -> env input -> preview:env:check -> QA`.
  - Current `preview:report` result: missing `DATABASE_URL`, `BLOB_READ_WRITE_TOKEN`, `CRON_SECRET`, and one OAuth provider pair; warnings remain for missing Vercel link, `ENABLE_DEMO_AUTH=true`, and localhost `NEXTAUTH_URL`.
  - Verification completed in `Projects/vibe-web`: `npm run preview:report`, `npm run preview:env:check` (expected fail with concrete blockers), `npm run lint`.
- `Projects/vibe-web` preview command flow consolidated.
  - Added a shared preview env helper (`scripts/preview-env-lib.mjs`) so both `preview:report` and `preview:env:check` read the same ruleset.
  - Updated README and preview docs so the execution path is now `db:generate -> preview:report -> preview:env:check -> db:migrate:deploy -> db:seed -> PREVIEW-QA-CHECKLIST`.
  - Verification completed in `Projects/vibe-web`: `npm run preview:report`, `npm run lint`.
- `Projects/vibe-web` preview and full verification commands bundled for repeatable execution.
  - Added `npm run verify` to run `lint -> test -> build -> test:e2e` in one command.
  - Added `npm run preview:doctor` and `npm run preview:db:prepare` so preview setup can be run as `preview:doctor -> preview:db:prepare -> PREVIEW-QA-CHECKLIST`.
  - Verification completed in `Projects/vibe-web`: `npm run verify` (lint pass, 10/10 tests, 21 routes built, 2/2 e2e), `npm run preview:doctor` (expected fail with concrete secret/link blockers only).
- `Projects/vibe-web` full local verification completed after preview handoff polish.
  - Verification passed: `npm run lint`, `npm run test` (10/10), `npm run build` (21 routes), `npm run test:e2e` (2/2).
  - `preview:env:check` still fails as expected because real preview secrets are not connected yet.
  - Follow-up cleanup included converting 19 doc links from absolute paths to relative paths, leaving `NEXTAUTH_URL` blank in `.env.preview.example` with Vercel fallback guidance, adding an empty-`NEXTAUTH_URL` warning in `check-preview-env.mjs`, and extending the upload redirect timeout in `tests/e2e/smoke.spec.ts` from 5s to 15s for Turbopack startup delay.
