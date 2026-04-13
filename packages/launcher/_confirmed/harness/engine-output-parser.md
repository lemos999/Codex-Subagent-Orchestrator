# C2. EngineOutputParser

> 최종 갱신: 2026-04-13
> 주관 섹션: event-system
> 참조 섹션: tool-visibility

## [확정] 파서 플러그인 인터페이스 (C2-1)

함수 맵. stateless 청크 처리기. 엔진 추가 시 함수 하나만 등록.

```typescript
type ChunkParser = (chunk: string, context: ParserContext) => HarnessEvent[];

interface ParserContext {
  sessionId: string;
  workerName: string;
  engine: Engine;
  buffer: string;  // 줄바꿈 미완성 청크 버퍼 (파서가 갱신)
}

const ENGINE_PARSERS: Record<Engine, ChunkParser> = {
  codex: parseCodexChunk,
  'codex-mcp': parseCodexChunk,
  claude: parseClaudeChunk,
  gemini: parseGeminiChunk,
};
```

### 입출력 계약
- 입력: stdout/stderr 청크 (Buffer → string), ParserContext (spawn.ts에서 생성)
- 출력: `HarnessEvent[]` (0개 이상) → C1 EventBus로 emit
- 실패 시 기본값: 파싱 실패한 청크 → 빈 배열 반환 (이벤트 미생성), 에러 로그만

## [확정] 엔진별 파싱 전략 (C2-2)

| 엔진 | stdout 포맷 | 파싱 전략 | tool_use 정확도 |
|------|-----------|---------|:---:|
| Codex | JSON 이벤트 라인 | `JSON.parse` → `type` 필드 기반 구조화 추출 | 높음 |
| Codex-MCP | JSON-RPC 응답 | `JSON.parse` → content 추출 | 높음 |
| Claude | 자유 텍스트 (`--print` 최종 출력) | 전체를 `worker.message`로. tool_use는 best-effort 정규식 | 낮음 |
| Gemini | 자유 텍스트 | 전체를 `worker.message`로. tool_use는 best-effort 정규식 | 낮음 |

### Codex JSON 이벤트 매핑

| Codex event type | → HarnessEvent type |
|---|---|
| `function_call` | `worker.tool_use` (tool = function name) |
| `message` / `text` | `worker.message` |
| `usage` / `token_usage` | (S1 UsageAggregator가 별도 소비) |

### Claude/Gemini best-effort 정규식 (참고)

도구 사용 패턴이 감지되면 `worker.tool_use` emit. 미감지 시 누락 허용.
정규식 패턴은 실행자 재량. 초기 구현에서는 `worker.message`만으로 충분.
