# C1. HarnessEventBus

> 최종 갱신: 2026-04-13
> 주관 섹션: event-system
> 참조 섹션: session-management, tool-visibility

## [확정] 이벤트 타입 분류 (C1-1)

CLI-실현 가능 서브셋. 9개 variant, 전부 실제 발생 보장.

```typescript
type HarnessEvent =
  | { type: 'worker.spawned';       sessionId: string; name: string; engine: Engine; model: string; timestamp: string }
  | { type: 'worker.chunk';         sessionId: string; name: string; stream: 'stdout' | 'stderr'; text: string; timestamp: string }
  | { type: 'worker.tool_use';      sessionId: string; name: string; tool: string; timestamp: string }
  | { type: 'worker.message';       sessionId: string; name: string; text: string; timestamp: string }
  | { type: 'worker.completed';     sessionId: string; name: string; exitCode: number; durationMs: number; timestamp: string }
  | { type: 'worker.error';         sessionId: string; name: string; error: string; timestamp: string }
  | { type: 'session.state_changed'; sessionId: string; from: SessionState; to: SessionState; timestamp: string }
  | { type: 'stage.started';        stageNum: number; workerCount: number; timestamp: string }
  | { type: 'stage.completed';      stageNum: number; succeeded: number; failed: number; timestamp: string };
```

Managed Agents 명명 패턴(`{domain}.{action}`) 준수.

## [확정] 전달 메커니즘 (C1-2)

콜백 배열 (typed). 외부 의존성 0, TypeScript 제네릭으로 타입 안전.

```typescript
interface HarnessEventBus {
  on<T extends HarnessEvent['type']>(
    type: T,
    listener: (event: Extract<HarnessEvent, { type: T }>) => void,
  ): void;
  emit(event: HarnessEvent): void;
  off<T extends HarnessEvent['type']>(
    type: T,
    listener: (event: Extract<HarnessEvent, { type: T }>) => void,
  ): void;
}
```

### 입출력 계약
- 입력: `HarnessEvent` (C2 파서, stage-runner, orchestrator에서 생산)
- 출력: 등록된 리스너에 동기 전달
- 실패 시 기본값: 리스너 에러 → catch 후 다음 리스너 계속 (버스 자체는 중단하지 않음)

## [확정] 워커별 이벤트 카운터

`emit()` 시 워커별 카운트를 증가. S4 ManifestExtension의 `events_emitted` 필드 생산자.

```typescript
interface HarnessEventBus {
  // ... on, emit, off (위 참조)
  getEventCount(sessionId: string): number;
}
```

## [확정] 동기/비동기 (C1-3)

동기 emit. 이벤트 순서 보장 필수 (세션 상태 머신 정합성).
리스너는 전부 경량 (Map.set, counter++, appendFileSync).
