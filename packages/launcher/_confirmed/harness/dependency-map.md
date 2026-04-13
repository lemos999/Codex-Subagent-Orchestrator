# 의존성 맵

> 최종 갱신: 2026-04-13

## 컴포넌트 간 의존 관계

| 컴포넌트 A | → | 컴포넌트 B | 공유 파라미터 | 방향 |
|---|---|---|---|---|
| C2 EngineOutputParser | → | C1 HarnessEventBus | `HarnessEvent` | 생산→방출 |
| C1 HarnessEventBus | → | C3 SessionManager | `HarnessEvent`, `session.state_changed` | 이벤트→상태 갱신 |
| C1 HarnessEventBus | → | C5 ToolTracker | `worker.tool_use` | 이벤트→집계 |
| C1 HarnessEventBus | → | S1 UsageAggregator | `worker.completed` | 이벤트→사용량 |
| C1 HarnessEventBus | → | S2 EventLogWriter | `HarnessEvent` (전체) | 이벤트→파일 |
| C1 HarnessEventBus | → | S3 HarnessCLI | `HarnessEvent` (전체) | 이벤트→콘솔 |
| C3 SessionManager | → | S4 ManifestExtension | `sessionId`, `SessionState` | 상태→manifest |
| C4 AgentRegistry | → | orchestrator `resolveWorkers()` | `AgentDefinition` | 정의→해석 |
| C5 ToolTracker | → | S4 ManifestExtension | `ToolUsageSummary[]` | ��계→manifest |
| S1 UsageAggregator | → | S4 ManifestExtension | `durationMs`, 토큰 | 사용량→manifest |

## 구현 순서 (의존성 위상 정렬)

```
Phase 1: C1 HarnessEventBus (의존 없음)
         C4 AgentRegistry (의존 없음)
Phase 2: C2 EngineOutputParser (C1 필요)
         C3 SessionManager (C1 필요)
         C5 ToolTracker (C1 필요)
Phase 3: S2 EventLogWriter (C1 필요)
         S4 ManifestExtension (C3, C5 필요. S1은 선택적 — 없으면 duration_ms만, 토큰 null)
Phase 4: orchestrator 통합 (전체 필요)
         S1 UsageAggregator (C1 필요, 린 스코프 후순위. S4에 지연 바인딩)
         S3 HarnessCLI (C1 필요, 린 스코프 후순위)

> S1(UsageAggregator), S3(HarnessCLI)는 린 스코프에서 후순위.
> S2, S4만 필수 설계 문서 작성 대상. S1, S3는 구현 시 설계.
```

## 기존 코드 수정 지점

| 기존 파일 | 수정 내용 | 관련 컴포넌트 |
|---|---|---|
| `src/workers/spawn.ts` | stdout/stderr chunk 리스너에 C2 파서 호출 추가 | C2 |
| `src/supervisor/stage-runner.ts` | `executeWorker()` 전후에 세션 상태 전이 + 이벤트 emit | C1, C3 |
| `src/orchestrator.ts` | `resolveWorkers()`에서 C4 레지스트리 조회 + sessionId 생성 | C3, C4 |
| `src/orchestrator.ts` | `orchestrate()` 옵션에 `harnessMode?: boolean` 추가 | C1 |
| `src/types/spec.ts` | `AgentSpec`에 `agent_id`, `agent_version`, `task` 필드 추가 | C4 |
| `src/types/manifest.ts` | `WorkerResult`에 tools_used, events_emitted, duration_ms 채움 | S4 |
| `src/cli.ts` | `--harness` 플래그 추가 | S3 |
| `src/evidence/manifest-builder.ts` | 하네스 데이터 manifest 기록 | S4 |
