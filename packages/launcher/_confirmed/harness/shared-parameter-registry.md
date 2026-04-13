# 공유 파라미터 레지스트리

> 최종 갱신: 2026-04-13

## 정본 테이블

| 파라미터 | 정본 소스 | 타입 | 비고 |
|---|---|---|---|
| `HarnessEvent` | [C1 harness-event-bus.md](harness-event-bus.md) | discriminated union (9 variants) | 모든 이벤트의 기반 타입 |
| `SessionState` | [C3 session-manager.md](session-manager.md) | `'created' \| 'running' \| 'idle' \| 'terminated'` | 4-state |
| `sessionId` | [C3 session-manager.md](session-manager.md) | string, 포맷: `{spec}_{worker}_{YYYYMMDDTHHMMSSmmm}` | 밀리초 정밀도 |
| `ToolUsageSummary` | [C5 tool-tracker.md](tool-tracker.md) | `{ name: string; calls: number }` | |
| `AgentDefinition` | [C4 agent-registry.md](agent-registry.md) | YAML → TypeScript interface | 6 필수 필드 + 2 선택적 |
| `ParserContext` | [C2 engine-output-parser.md](engine-output-parser.md) | `{ sessionId, workerName, engine, buffer }` | spawn.ts가 생성 |

## 참조 그래프

```
C4 AgentRegistry ──→ orchestrator.resolveWorkers()
                              │
                              ▼
C2 EngineOutputParser ──→ C1 HarnessEventBus ──┬→ C3 SessionManager ──→ S4 ManifestExtension
                                                ├→ C5 ToolTracker ─────→ S4 ManifestExtension
                                                ├→ S1 UsageAggregator ─→ S4 ManifestExtension
                                                ├→ S2 EventLogWriter
                                                └→ S3 HarnessCLI
```

## 변경 영향 범위

| 파라미터 변경 시 | 영향받는 컴포넌트 |
|---|---|
| HarnessEvent variant 추가 | C1, 모든 소비자 (C3, C5, S1, S2, S3) |
| SessionState 상태 추가 | C3, C1 (이벤트 타입) |
| sessionId 포맷 변경 | C3, C1, C5, S2, S4 |
| ToolUsageSummary 필드 추가 | C5, S4 |
| AgentDefinition 필드 추가 | C4, orchestrator |
