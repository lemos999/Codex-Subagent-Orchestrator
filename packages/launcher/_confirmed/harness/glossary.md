# Glossary — Launcher Harness Mode

> 최종 갱신: 2026-04-13

| 용어 | 정의 |
|------|------|
| Harness Mode | launcher의 실행 모드. `--harness` 플래그로 활성화하면 이벤트 스트리밍, 세션 추적, 에이전트 레지스트리 기능이 켜진다. |
| HarnessEvent | 워커 실행 중 발생하는 구조화된 이벤트의 타입. discriminated union으로 9개 variant. |
| HarnessEventBus | 이벤���를 생산자→소비자로 전달하는 중앙 버스. 동기 콜백 기반. |
| EngineOutputParser | 엔진별 stdout/stderr 청크를 HarnessEvent로 변환하는 파서 플러그인. |
| SessionManager | 워커별 세션 상태(created→running→idle\|terminated)를 추적하는 상태 머신. |
| SessionState | 세션의 4가지 상태: `created`, `running`, `idle`, `terminated`. |
| sessionId | 세션 고유 식별자. 포맷: `{specName}_{workerName}_{YYYYMMDDTHHMMSSmmm}`. |
| AgentRegistry | `config/agents/*.yaml`에 저장된 재사용 가능 에이전트 정의 모음. |
| AgentDefinition | 에이전트의 페르소나(system) + 기본 설정(engine, model, sandbox 등)을 정의하는 YAML 파일. |
| system prompt | 에이전트의 역할·행동 지침. AgentDefinition의 `system` 필드. task와 분리. |
| task | 이번 세션에서 수행할 작업. spec의 `task` 필드. system과 분리. |
| ToolUsageSummary | 워커가 사용한 도구의 이름과 호출 횟수. `{name: string, calls: number}`. |
| best-effort 파싱 | Claude/Gemini 엔진처럼 구조화된 출력이 없는 경우, 정규식 휴리스틱으로 도구 사용을 추정하는 방식. 정확도 보장 안 됨. |
| ParserContext | 파서에 전달되는 컨텍스트: sessionId, workerName, engine, 줄바꿈 미완성 버퍼. |
| EventLogWriter | 이벤트를 JSON-L 파일로 영속화하는 컴포넌트. `{name}.events.jsonl`. |
| ManifestExtension | 기존 WorkerResult에 하네스 데이터(session_id, tools_used, events_emitted, duration_ms)를 추가하는 브릿지. |
