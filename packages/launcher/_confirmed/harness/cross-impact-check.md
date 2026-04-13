# 교차 영향 검증 결과

> 최종 갱신: 2026-04-13

## 공유 파라미터 레지스트리

| 파라미터 | 정본 | 소비자 | 일치 |
|---|---|---|:---:|
| `HarnessEvent` (discriminated union, 9 variants) | C1 | C3, C5, S1, S2, S3 | ✅ |
| `SessionState` (`'created'\|'running'\|'idle'\|'terminated'`) | C3 | C1 | ✅ |
| `sessionId` (`{spec}_{worker}_{YYYYMMDDTHHMMSSmmm}`) | C3 | C1, C5, S2, S4 | ✅ |
| `ToolUsageSummary` (`{name, calls}`) | C5 | S4 | ✅ |
| `AgentDefinition` (YAML → 타입) | C4 | orchestrator | ✅ |
| `ParserContext` (sessionId, workerName, engine, buffer) | spawn.ts | C2 | ✅ |

불일치: 0건.

## 연쇄 효과 검���

| 시나리오 | 입력 | 결과 | 판정 |
|---|---|---|:---:|
| A. 워커 0개 (빈 spec) | agents=[] | 이벤트 0건, 파일 미생성, manifest 정상 | PASS |
| B. 워커 50개 병렬 | 동시 emit | 단일 스레드 직렬 처리, 순서=chunk 수신 순 | PASS (의도된 트레이드오프) |
| C. agent_id + prompt 혼용 | 일부 agent_id, 일부 prompt | 각각 독립 해석, 이벤트 동일 | PASS |
| D. 미존재 agent_id | agent_id="unknown" | 즉시 에러 + 명확한 메시지 | PASS |
| E. Codex timeout | exitCode≠0 | running→terminated, 불완전 buffer 무시 | PASS |

## 트레이드오프 판정

| 트레이드오프 | Primary Outcome 강화? | 인지 가능? | 진행 가능? | 판정 |
|---|:---:|:---:|:---:|---|
| 동기 emit vs 처리 속도 | ✅ | ✅ | ✅ | 의도됨 |
| Claude/Gemini best-effort 파싱 | ✅ | ✅ | ✅ | 의도됨 |
| agent_id 미존재 시 에러 (폴백 없음) | ✅ | ✅ | ✅ | 의도됨 |

## 타이밍 검증

| 동시 발생 상황 | 규칙 |
|---|---|
| 병렬 워커 동시 emit | 단일 스레드 직렬. 워커 간 순서 보장 불필요 (내부 순서만) |
| sessionId 생성 vs spawn | resolveWorkers()(Phase 5) → spawn(Phase 6). 순서 보장 |
| EventLogWriter append vs 종료 | 동기 append. completed 이벤트 기록 후 진행 |

## 미해결 모순: 0건
