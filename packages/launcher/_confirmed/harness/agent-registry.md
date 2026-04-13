# C4. AgentRegistry

> 최종 갱신: 2026-04-13
> 주관 섹션: agent-registry
> 참조 섹션: session-management

## [확정] 저장 포맷 (C4-1)

YAML 파일. 기존 `config/capabilities/*.yaml` 패턴과 일관.

## [확정] 파일 구조 (C4-2)

디렉토리 기반. 파일명 = agent_id.

```
config/agents/
├── reviewer.yaml
├── impl-codex.yaml
├── impl-claude.yaml
└── planner.yaml
```

## [확정] 에이전트 정의 스키마 (C4-3) — system/task 분리

```yaml
# config/agents/{id}.yaml
id: reviewer                     # 필수. 파일명과 일치
version: 1                       # 필수. 정수, 업데이트마다 수동 증가
name: "코드 리뷰어"               # 필수. 사람이 읽는 이름
engine: claude                   # 필수.
model: claude-sonnet-4-6         # 필수.
system: |                        # 필수. 에이전트 페르소나/행동 지침
  너는 코드 리뷰어다. 변경사항을 검토하고
  보안, 성능, 가독성 관점에서 피드백한다.
defaults:                        # 선택적. spec에서 미지정 시 적용
  sandbox: read-only
  kind: reviewer
  reasoning_effort: high
  extra_args: []
metadata:                        # 선택적. 사람용 메타데이터
  description: "보안/성능/가독성 코드 리뷰"
  tags: [review, security]
```

### spec에서 사용

```json
{
  "agents": [
    {
      "name": "review",
      "agent_id": "reviewer",
      "task": "packages/launcher/src/workers/spawn.ts 변경사항 리뷰"
    }
  ]
}
```

### 프롬프트 주입 순서

```
1. AGENTS.md (shared directive)
2. AgentDefinition.system (레지스트리)
3. WKI context (자동 주입)
4. task 또는 prompt (spec)
```

### agent_id 해석 우선순위

| 우선순위 | 조합 | 동작 |
|---|---|---|
| 1 | `agent_id` + `task` | system(레지스트리) + task(spec) |
| 2 | `agent_id` + `prompt` (task 없음) | system(레지스트리) + prompt를 task로 사용 + 경고 |
| 3 | `prompt` (agent_id 없음) | 기존 동작 그대로 (하위 호환) |
| 4 | `agent_id` + `task` + `prompt` | 1번과 동일 + prompt 무시 경고 |
| 5 | 아무것��� 없음 | 기존 에러 (변경 없음) |

### 에러 처리
- `agent_id` 지정했으나 파일 미존재 → 즉시 에러 + 명확한 메시지: `Agent '{id}' not found in config/agents/`
- YAML 파싱 실패 → 즉시 에러 + 파일 경로 + 파싱 에러 메시지

### 입출력 계약
- 입력: agent_id (spec), config/agents/ 디렉토리
- 출력: AgentDefinition → orchestrator `resolveWorkers()`에서 system + defaults 적용
- 실패 시 기본값: 없음 (에러). 폴백 금지 — 오타 방지.

## [확정] 버전 관리 (C4-4)

파일 내 `version: N` 정수. Managed Agents 패턴 동일.

- spec에서 `agent_version` 미지정 → 최신 파일 사용
- spec에서 `agent_version: 2` 지정 → 미지원 (파일이 하나이므로 현재 version과 불일치 시 에러)
- 향후 버전 히스토리 필요 시 git 기반 확장 가능

```typescript
interface AgentDefinition {
  id: string;
  version: number;
  name: string;
  engine: Engine;
  model: string;
  system: string;
  defaults?: Partial<{
    sandbox: Sandbox;
    kind: WorkerKind;
    reasoning_effort: ReasoningEffort;
    extra_args: string[];
  }>;
  metadata?: Record<string, unknown>;
}
```
