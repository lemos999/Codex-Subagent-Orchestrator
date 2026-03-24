# 큐 러너 TS 전환 계획서

> GPT 5.4 (xhigh) watchdog 리뷰 반영 — 2026-03-22

## 배경

현재 큐 러너(`start-codex-subagent-queue.ps1`, 1,700줄)는 PowerShell 전용으로 Windows에서만 동작한다.
TS로 전환하면 Mac/Linux에서도 실행 가능하고, 기존 TS 런처(`packages/launcher/`)와 코드를 공유할 수 있다.

## 현재 PS 큐 러너 핵심 기능

| 기능 | 설명 |
|------|------|
| **폴링** | 트래커에서 이슈 주기적 조회 (interval_seconds) |
| **트래커 종류** | local-json, local-files, mock-json(별칭), linear (GraphQL) |
| **디스패치** | 이슈 → 런처 spec 생성 → 자식 프로세스 실행 |
| **동시성 제어** | max_concurrent_issues로 병렬 제한 |
| **블로킹** | blocked_by 의존성 해결 (문자열/객체 혼합, fingerprint 기반 해소) |
| **우선순위** | priority → updated → identifier 순 정렬 |
| **핑거프린트** | 정규화된 JSON 문자열로 이미 완료된 이슈 재디스패치 방지 |
| **재시도** | 지수 백오프 (base=30s, max=300s) |
| **상태 저장** | queue-state.json (17개 필드, 매 폴링마다 저장) |
| **리포트** | queue-report.md (사람이 읽는 요약) |
| **워크스페이스** | 이슈별 디렉토리 생성 + 부트스트랩 훅 (after_create + sentinel_paths) |
| **종료** | drain-on-exit (실행 중 작업 대기 후 종료) |

## TS 전환 범위

### Phase 1: 전체 호환 (hooks 포함)

> GPT 5.4 피드백: hooks 제외와 기존 설정 호환은 양립 불가 → Phase 1에 hooks 포함

```
packages/launcher/src/queue/
├── queue-runner.ts        — 메인 폴링 루프 + 스케줄러
├── queue-config.ts        — 설정 파싱 (Zod, passthrough)
├── queue-compat.ts        — 레거시 PS 설정 → canonical 내부 설정 변환
├── queue-state.ts         — 상태 저장/로드 (17필드 + 스키마 버전 + 원자적 쓰기)
├── queue-report.ts        — 리포트 생성
├── queue-cli.ts           — CLI 진입점
├── issue-normalizer.ts    — 이슈 정규화 (id/identifier/key, title/name 등) + 핑거프린트
├── launcher-adapter.ts    — 런처 실행 캡슐화 (경로, cwd, stdout/stderr, kill)
├── workspace-bootstrap.ts — 워크스페이스 생성 + hooks.after_create + sentinel 대기
└── trackers/
    ├── tracker.ts          — Tracker 인터페이스 (raw 이슈만 반환)
    ├── local-json.ts       — local-json / mock-json(별칭) 트래커
    └── local-files.ts      — local-files 트래커 (json/md/txt)
```

**미포함 (Phase 2):**
- Linear GraphQL 트래커
- MCP 서버 통합
- 동적 스케일링

## 설계 결정 (GPT 5.4 피드백 반영)

### 1. 런처 실행 위치 분리 (#1 fix)

> 런처 실행 cwd ≠ 이슈 워크스페이스. PS와 동일하게 config 디렉토리 기준 런처 경로 고정.

```typescript
// launcher-adapter.ts
const launcherPath = path.resolve(configDir, 'packages/launcher/dist/cli.js');

const child = spawn('node', [launcherPath, '--spec', specPath, '--json'], {
  cwd: configDir,  // 런처는 config 디렉토리에서 실행
  stdio: ['ignore', 'pipe', 'pipe'],
});

// spec 내부의 cwd가 실제 작업 디렉토리를 지정
spec.cwd = workspacePath;
```

### 2. 설정 호환 계층 (#2, #6 fix)

> 레거시 PS 설정 → canonical 내부 설정 변환. Zod `.passthrough()` 사용.

```typescript
// queue-compat.ts
function normalizeConfig(raw: unknown): CanonicalQueueConfig {
  // mock-json → local-json 별칭 처리
  // hooks.after_create (문자열) → hooks.after_create.command (중첩 객체)
  // after_create_sentinel_paths → hooks.after_create.sentinel_paths
  // 알 수 없는 필드는 무시 (passthrough)
}
```

### 3. 이슈 정규화 + 핑거프린트 분리 (#3, #5 fix)

> Tracker는 raw 이슈만 반환. 정규화와 핑거프린트는 별도 모듈.

```typescript
// trackers/tracker.ts — raw만 반환
interface Tracker {
  fetchRawIssues(): Promise<RawIssue[]>;
}

// issue-normalizer.ts — 중앙 정규화
interface NormalizedIssue {
  id: string;
  identifier: string;
  title: string;
  description: string;
  state: string;
  priority: number;            // default 999
  labels: string[];
  blocked_by: (string | BlockerObject)[];  // 문자열/객체 혼합 허용
  requested_deliverables: string[];
  auto_run: boolean;           // default true
  source_path?: string;
  source_kind?: string;
  branch_name?: string;
  url?: string;
  created_at?: string;
  updated_at?: string;
  mode_hint?: string;
}

// 핑거프린트: PS와 동일한 정규화 JSON 문자열 (SHA256 아님!)
function computeFingerprint(issue: NormalizedIssue): string {
  const ordered = {
    identifier: issue.identifier,
    title: issue.title,
    description: issue.description,
    priority: issue.priority,
    state: issue.state,
    branch_name: issue.branch_name ?? '',
    url: issue.url ?? '',
    labels: [...new Set(issue.labels)].sort(),
    blocked_by: normalizeBlockedBy(issue.blocked_by),
    created_at: issue.created_at ?? '',
    updated_at: issue.updated_at ?? '',
    requested_deliverables: [...new Set(issue.requested_deliverables)].sort(),
    mode_hint: issue.mode_hint ?? '',
    auto_run: issue.auto_run,
    source_path: issue.source_path ?? '',
    source_kind: issue.source_kind ?? '',
  };
  return JSON.stringify(ordered);  // PS와 동일: JSON 문자열 비교
}
```

### 4. blocked_by 복잡 로직 (#4 fix)

> 문자열/객체 혼합 + fingerprint 기반 해소

```typescript
function isBlocked(
  issue: NormalizedIssue,
  activeStates: string[],
  issueMap: Map<string, NormalizedIssue>,
  state: QueueState,
): boolean {
  for (const blocker of issue.blocked_by) {
    const blockerKey = typeof blocker === 'string'
      ? blocker
      : blocker.identifier ?? blocker.id ?? blocker.key;

    if (!blockerKey) continue;

    const stateRecord = state.issues[blockerKey];

    // blocker가 성공 완료 + 핑거프린트 일치 → 해소
    if (stateRecord?.last_success_fingerprint) {
      const blockerIssue = issueMap.get(blockerKey);
      if (blockerIssue) {
        const currentFp = computeFingerprint(blockerIssue);
        if (stateRecord.last_success_fingerprint === currentFp) continue;
      }
    }

    // blocker가 아직 활성 상태 → 차단
    const blockerIssue = issueMap.get(blockerKey);
    if (blockerIssue && activeStates.includes(blockerIssue.state)) return true;

    // blocker가 트래커에 없지만 상태 파일에 성공 기록 없음 → 차단
    if (!blockerIssue && !stateRecord?.last_success_fingerprint) return true;
  }
  return false;
}
```

### 5. 상태 파일 계약 (#7 fix)

> PS와 동일한 17개 필드 + 스키마 버전 + 원자적 저장

```typescript
interface IssueStateRecord {
  issue_key: string;
  status: 'idle' | 'running' | 'completed' | 'failed' | 'stopped';
  dispatch_count: number;
  consecutive_failures: number;
  next_eligible_at_utc: string | null;
  workspace_path: string | null;
  last_state: string | null;
  last_manifest: string | null;
  last_summary: string | null;
  last_stdout: string | null;
  last_stderr: string | null;
  last_exit_code: number | null;
  last_started_at_utc: string | null;
  last_finished_at_utc: string | null;
  last_seen_at_utc: string | null;
  last_issue_fingerprint: string | null;
  last_success_fingerprint: string | null;
  last_success_at_utc: string | null;
  source_path: string | null;
  stop_reason: string | null;
}

interface QueueState {
  schema_version: 1;
  updated_at_utc: string;
  issues: Record<string, IssueStateRecord>;
}

// 원자적 저장: 임시 파일에 쓰고 rename
async function saveState(statePath: string, state: QueueState): Promise<void> {
  const tmp = statePath + '.tmp';
  await fs.writeFile(tmp, JSON.stringify(state, null, 2));
  await fs.rename(tmp, statePath);
}
```

### 6. 런처 JSON 출력 모드 (#8 fix)

> TS CLI에 `--json` 플래그 추가 필요 (사전 작업)

```bash
# 현재: stdout에 텍스트 출력
node packages/launcher/dist/cli.js --spec spec.json

# 추가: JSON 모드 (큐 러너가 파싱)
node packages/launcher/dist/cli.js --spec spec.json --json
# → { "manifest": "path", "summary": "path", "exit_code": 0 }
```

### 7. 재시도 기본값 (#3 fix)

PS와 동일하게 유지:
- `base_backoff_seconds`: **30** (계획서 오류 수정: 2s → 30s)
- `max_backoff_seconds`: **300**

## 구현 순서 (GPT 5.4 권장 순서 반영)

1. **골든 테스트** — PS 동작을 fixture로 고정
   - config normalization, fingerprint, blocked_by, retry/backoff, state/report
   - local-json, local-files, mock-json 트래커 입력/출력 fixture
2. **queue-compat.ts** — 레거시 설정 → canonical 변환
3. **issue-normalizer.ts** — 이슈 정규화 + 핑거프린트
4. **launcher-adapter.ts** — 런처 경로/cwd/spawn/kill 캡슐화
5. **TS CLI --json 모드** — 런처에 JSON 출력 추가
6. **trackers/** — local-json, local-files, mock-json 별칭
7. **queue-state.ts** — 상태 저장/로드 (17필드 + 원자적)
8. **workspace-bootstrap.ts** — 워크스페이스 생성 + hooks
9. **queue-runner.ts** — 폴링 루프 + 스케줄러
10. **queue-report.ts** — 리포트 생성
11. **queue-cli.ts** — CLI 진입점
12. **통합 테스트** — local-json 3개 이슈 end-to-end

## 리스크

| 리스크 | 대응 |
|--------|------|
| PS 엣지 케이스 누락 | 골든 테스트로 PS 동작 고정 후 TS 구현 |
| Windows child_process 이슈 | 기존 TS 런처의 winCmd/spawn 로직 재사용 |
| 설정 포맷 호환성 | queue-compat 변환 계층 + Zod passthrough |
| 핑거프린트 드리프트 | PS와 동일한 JSON 문자열 비교 (SHA256 아님) |
| 상태 파일 충돌 | 원자적 저장 (tmp+rename) + 단일 인스턴스 체크 |
| TS CLI JSON 모드 부재 | Phase 1 사전 작업으로 먼저 추가 |

## 성공 기준

- [ ] 골든 테스트 fixture와 TS 출력 일치
- [ ] local-json 트래커로 3개 이슈 큐 처리 성공
- [ ] 블로킹 의존성 해결 확인 (문자열 + 객체 + fingerprint 해소)
- [ ] 실패 → 백오프 재시도 확인 (30s base)
- [ ] 핑거프린트 기반 재디스패치 스킵 확인
- [ ] 워크스페이스 부트스트랩 + sentinel 대기 확인
- [ ] 기존 PS 큐 설정 파일 (template 포함) 파싱 성공
- [ ] Mac/Linux에서 동작 확인 (또는 WSL)

## GPT 5.4 리뷰 반영 요약

| # | 지적 | 반영 |
|---|------|------|
| 1 | 디스패치 cwd 오류 | launcher-adapter.ts로 분리, configDir 기준 실행 |
| 2 | 훅 포맷 불일치 | queue-compat.ts 변환 계층 추가, hooks Phase 1 포함 |
| 3 | 핑거프린트/백오프 차이 | JSON 문자열 비교, base=30s로 수정 |
| 4 | blocked_by 복잡도 | 문자열/객체 혼합 + fingerprint 해소 로직 명시 |
| 5 | fingerprint 위치 | Tracker 밖 issue-normalizer로 분리 |
| 6 | Zod strict 문제 | passthrough + mock-json 별칭 처리 |
| 7 | 상태 스키마 미비 | 17필드 전체 + schema_version + 원자적 저장 |
| 8 | TS CLI JSON 모드 없음 | 사전 작업으로 --json 추가 |
| 9 | 구현 순서 | 골든 테스트 → compat → normalizer → adapter 순으로 변경 |
