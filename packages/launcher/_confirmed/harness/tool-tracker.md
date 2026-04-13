# C5. ToolTracker

> 최종 갱신: 2026-04-13
> 주관 섹션: tool-visibility
> 참조 섹션: event-system

## [확정] 추적 항목 (C5-1)

도구명 + 호출 횟수. CLI 파싱 한계 내 실용적 최소 단위.

```typescript
interface ToolUsageSummary {
  name: string;
  calls: number;
}
```

### 동작

1. C1 EventBus에서 `worker.tool_use` 이벤트 구독
2. 워커별 `Map<toolName, callCount>` 집계
3. 워커 완료 시 `ToolUsageSummary[]` 반환

```typescript
class ToolTracker {
  private readonly usage = new Map<string, Map<string, number>>();

  /** C1 EventBus 리스너로 등록 */
  onToolUse(event: Extract<HarnessEvent, { type: 'worker.tool_use' }>): void;

  /** 워커 완료 시 호출 */
  getSummary(sessionId: string): ToolUsageSummary[];
}
```

### 입출력 계약
- 입력: `worker.tool_use` 이벤트 (C1 경유, C2가 생산)
- 출력: `ToolUsageSummary[]` per worker → S4 ManifestExtension
- 실패 시 기본값: 파싱 실패한 도구 → 미카운트 (빈 배열). 에러 아님.
- 엔진별 정확도: Codex = 정확, Claude/Gemini = best-effort (누락 허용)
