# C3. SessionManager

> 최종 갱신: 2026-04-13
> 주관 섹션: session-management
> 참조 섹션: event-system

## [확정] 상태 모델 (C3-1)

4-state 모델:

```
created ──spawn──→ running ──exit(0)──→ idle
                      │
                      └──exit(≠0)/timeout──→ terminated
```

### 전이 규칙
| 현재 상태 | 이벤트 | 다음 상태 |
|---|---|---|
| created | `spawnWorker()` 호출 | running |
| running | exitCode === 0 | idle |
| running | exitCode !== 0 또는 timeout | terminated |

- 역방향 전이 금지
- 전이 시 `session.state_changed` 이벤트 emit (C1 EventBus 경유)

### SessionState 타입

```typescript
type SessionState = 'created' | 'running' | 'idle' | 'terminated';
```

## [확정] 세션 ID 생성 (C3-2)

포맷: `{specName}_{workerName}_{YYYYMMDDTHHMMSSmmm}`

- specName: spec 파일명에서 확장자 제거 + 비영숫자 → `_` 치환
- workerName: agents[].name 그대로
- timestamp: 밀리초 13자리 (`20260413T143022731`)
- 생성 시점: `resolveWorkers()` (Phase 5, spawn 이전)

예시: `build_impl_20260413T143022731`

### 입출력 계약
- 입력: specName (orchestrator), workerName (spec), timestamp (Date.now)
- 출력: sessionId string → C1 모든 이벤트, C5, S2, S4에서 참조
- 충돌 확률: 같은 밀리초에 동일 spec+worker 조합은 불가 (이름 유니크 제약)

## [확정] 저장 방식 (C3-3)

인메모리 `Map<string, SessionState>`.

```typescript
class SessionManager {
  private readonly states = new Map<string, SessionState>();

  create(sessionId: string): void;
  transition(sessionId: string, to: SessionState): void;
  getState(sessionId: string): SessionState | undefined;
  getAllSessions(): Map<string, SessionState>;
}
```

- 실행 중에만 유효. 종료 시 manifest + 이벤트 로그가 영속 레이어.
- `transition()` 내부에서 역방향 검증 + `session.state_changed` emit.
