# Project Status — Current

> 이 파일은 모든 AI 엔진(Claude, Codex/GPT, Gemini)이 참조합니다.
> 이 폴더에서 작업하는 AI는 이 파일을 읽고 현재 상태를 파악하세요.
> 완료 기록은 project-status/2026-Q2.md에 직접 추가한다.
> current.md에는 완료 이력을 기록하지 않는다.
> → 완료 이력: project-status/2026-Q2.md

---

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

1. **페르소나 국가 — 구현 단계 진입** (설계 전부 완료)
   - Phase C: constants-charter 신설, 극한 SLA 정의, PersonaBrain 학습 발산 복구
   - 구현 순서: Physis → 틱 데몬 → 사회 시스템 → PersonaBrain SNN → 자율 생활
2. **WKI 추가 개선** — Mean nDCG 0.819, Line-scoped 0.655 (Min 0.630)
3. **/design domains/software/ 실전 사용**

## 페르소나 국가 설계 현황 (2026-04-12 완료)

| Charter | 버전 | 상태 |
|---------|------|:----:|
| world-ontology | Phase A 수정 완료 | ✅ |
| constitution | 8장 27조 | ✅ |
| economy-whitepaper | 11장 | ✅ |
| physis-charter-v2 | v2.4 | ✅ |
| tick-daemon-charter | v1.1 | ✅ |
| humanity-charter | H1~H6 | ✅ |
| death-reincarnation-charter | v1 | ✅ |
| order-charter | v1 | ✅ |
| society-charter-draft | v1.1 | ✅ |
| secret-rumor-evidence-charter | v1.1 | ✅ |
| **personabrain-snn-charter** | **v3.1** | ✅ |

PersonaBrain SNN: 50M 뉴런, 12클러��터(V-L-S-B-A-T-C-G-F-I-D-P), 기억 5유형+망각 경제학, 20K명 CPU 10ms

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
---

## 2026-04-08 Mostria perf/auth note

- Implemented public `/board` SSR fallback plus hydration-sync category/page shell.
- Opened `/board` and `/board/[id]` for guest read access while keeping `/board/new` and `/board/[id]/edit` auth-gated.
- Board detail now keeps core SSR and lazy-loads comments, revisions, and recent posts through `/api/board/[id]/panels`.
- Guest board detail shows login CTAs for comment/like/report instead of interactive forms.
- `getSettingsSummary()` now uses aggregate-only metrics instead of per-post gallery scans.
- `getPublicProfileSummary()` now returns aggregate/result-only summary data, so `/users/[id]` works-first no longer double-loads gallery-derived stats.
- Validation: `npx tsc --noEmit`, `npm run test` (212 passed), `npm run lint`, `npm run build`.

## 2026-04-08 Board unicode fix

- Replaced escaped unicode and mojibake strings on board list/detail surfaces with real Korean copy.
- Fixed board page header, category nav, board cards, board detail panels, and guest CTA text.
- Validation: npm run lint, npm run build.

## 2026-04-09 Mostria profile visibility controls

- Added per-user visibility flags for portfolio and activity tabs with default `true` values for existing and new users.
- Settings now expose `포트폴리오 공개` and `활동 기록 공개` toggles through the existing profile update flow.
- Public profile routes now gate works/activity data before loading tab content:
  - owner always sees both tabs
  - non-owners see lock panels for hidden tabs
  - default `/users/<handle>` redirects to `?tab=activity` when works is hidden but activity remains public
- Portfolio-hidden profiles now conceal derived stats, latest work, tool tags, featured/HoF counts, and sidebar portfolio cards.
- Search still returns hidden-profile users, but concealed results now expose only identity-level fields (name, handle, avatar).
- Validation: `npx prisma migrate deploy`, `npx tsc --noEmit`, `npm run test` (220 passed), `npm run lint`, `npm run build`.

## 2026-04-09 Mostria profile visibility follow-up

- Closed a HoF privacy leak where `portfolioPublic=false` and `activityPublic=true` could still expose `명예의 전당 N회 선정됨` through the activity feed.
- Removed raw `visibility` flags from search result payloads so concealed users no longer leak privacy configuration metadata.
- Hid the EXP/progress card when portfolio visibility is off while keeping identity-level profile info public.
- Expanded regression coverage for:
  - hidden activity tab rendering
  - both-tabs-private default route behavior
  - concealed search cards
  - legacy users with missing visibility flags defaulting to public
- Validation: `npx tsc --noEmit`, `npm run test` (225 passed), `npm run lint`, `npm run build`.

## 2026-04-09 Mostria transaction resilience hardening

- Replaced the old serializable-only transaction helper with a generic retrying `runTransaction()` helper in the DB repository.
- Transaction retries now use:
  - retry limit `5`
  - base delay `50ms`
  - exponential backoff with jitter
  - transaction timeout `15_000`
- Gallery create, like toggle, feature, and unfeature now use the generic helper without forcing `Serializable` isolation.
- Added `lib/db-errors.ts` so server actions can classify transient DB failures separately from repository retry logic.
- `runAction()` now supports `fallbackRedirect`, allowing upload, gallery edit, like, and curation actions to redirect back with a friendly transient-error message instead of surfacing the generic error page.
- Initial regression coverage added retry exhaustion, retry success, and transient DB error classification before the policy was narrowed in the follow-up below.
- Validation: `npx tsc --noEmit`, `npx vitest run` (234 passed), `npm run lint`, `npm run build`.

## 2026-04-09 Mostria transaction resilience follow-up

- Narrowed repository-level automatic retries to rollback-safe transaction failures only:
  - `P2034`
  - unknown-request messages containing `could not serialize access`
  - unknown-request messages containing `deadlock detected`
- Explicitly stopped repository auto-retries for ambiguous commit/transport failures such as `P2028` and generic `connection reset` paths to avoid duplicate post creation or like state inversion on replay.
- Narrowed `isTransientDbError()` so `PrismaClientUnknownRequestError` / `PrismaClientInitializationError` are no longer treated as transient wholesale; they now require a matching transient message.
- Restored the default validation redirect message to a normal Korean string.
- Expanded repository regression coverage to lock:
  - `createPost` retry on `P2034`
  - `toggleLike` retry on `P2034`
  - `unfeaturePost` retry on `P2034`
  - unknown rollback-safe retry messages
  - `P2028` and `connection reset` non-retry behavior
- Added server-action regression coverage to lock the split policy directly:
  - repository keeps `P2028` / `connection reset` as non-retry
  - `uploadAction`, `updateGalleryPostAction`, `likeAction`, `featurePostAction`, and `unfeaturePostAction` still redirect back with a friendly transient DB error message
- Final review pass from the read-only review team reported no actionable findings.
- Validation: `npx tsc --noEmit`, `npm run test` (239 passed), `npm run lint`, `npm run build`.

## 2026-04-09 Mostria upload v2

- Shipped upload v2 with multi-image persistence (`PostImage` / `PostRevisionImage`), server-generated excerpts, markdown editor preview, `.md` import, and preview-only YouTube embeds.
- Gallery create/edit now use `files[]` and `primaryImageIndex`, while edit preserves existing images when no new files are uploaded and replaces the full image set when new files are present.
- Revision restore now rebuilds the full image set, legacy single-image rows are backfilled into the new image tables, and failed upload mutations clean up persisted blobs.
- Completed the spec-alignment follow-up without changing the data model or action contract:
  - art image upload now uses a fixed 5-slot layout and multi-image copy
  - gallery form section ordering is driven by `getFieldOrder()`
  - regression coverage now locks excerpt generation, max image rules, primary-image index resync, edit image passthrough, and preserve/replace semantics
- Validation: `npx tsc --noEmit`, `npx vitest run` (255 passed), `npm run lint`, `npm run build`.

## 2026-04-09 Mostria P0 hotfix (#4, #6, #9)

- Fixed hall-entry home feed behavior so `hall !== "all"` now shows all matching hall/subhall submissions instead of featured-only results.
- Hall-specific home views now hide `HomeHofMini` and `AiNews`; only the subhall tabs and hall feed remain visible.
- Increased the home preload limit from `40` to `100` so hall filtering has enough gallery coverage in the current MVP.
- Promoted `명예의전당` into the main header navigation and removed the unused `DISCOVERY_NAV_ITEMS` split.
- Removed `isDiscoveryEnabled()` gating from `/search` and `/hall-of-fame`, so both pages remain directly accessible.
- Fixed the header search box so Enter submits via `/search?q=...` using a real `<form>` and `name="q"`.
- Updated home-feed regression tests to lock the new hall behavior and the larger `getHomeFeed(..., 100)` contract.
- Validation: `npx tsc --noEmit`, `npm run lint`, `npx vitest run` (240 passed), `npm run build`.

## 2026-04-09 Mostria P0 hotfix follow-up

- Removed the remaining hall-feed cap mismatch by letting hall views build feed items without the home-page `20` item slice.
- Switched hall featured prioritization to use the same hall/subhall resolver path as the visible feed, so override/legacy hall matches also float correctly.
- Dropped the home gallery preload limit for this route so hall views can render the full matching set instead of the latest `100` only.
- Added a regression test covering resolver-based featured ordering (`post_neon-study`) and updated the home preload expectation accordingly.
- Validation: `npx tsc --noEmit`, `npm run lint`, `npx vitest run` (241 passed), `npm run build`.
