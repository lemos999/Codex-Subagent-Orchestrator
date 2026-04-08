# Codex-Subagent-Orchestrator

## English

This repository provides a local Codex workflow for two cases:

- stay inside the current chat session by default
- use internal `/sub` delegation only when splitting the work is actually useful

The current edition is designed around internal chat-session orchestration. It no longer treats external launcher flows as the main path.

### How it works

There are two working modes.

#### 1. Default mode: one session

If the user does not explicitly ask for `/sub` or otherwise explicitly request subagents, work stays inside the current Codex session.

The usual flow is:

1. scan
2. plan
3. implement
4. verify
5. review

If a problem is found, the workflow does not just stop there. It goes back to the necessary step, fixes the issue in a bounded way, and checks again.

#### 2. `/sub` mode: internal subagents

If the task is better handled by splitting work, `/sub` can be used to supervise internal subagents.

Before launch, the parent session decides:

- whether one worker is enough
- whether the run should be serial, parallel, or mixed
- where review belongs
- which files or scopes each worker owns
- which rules are actually needed for the task

### Agent Skills integration

This repository also includes the Agent Skills pack and connects it to the main workflow.

The important part is that those skills are not loaded blindly.

The parent session or internal subagents:

1. first decide what the current task needs
2. then select only the relevant skills
3. avoid attaching unnecessary skills
4. can use multiple skills when the task truly requires them

In short, the rule is not “always use fewer skills.”  
The rule is “use what is needed, and explain why.”

### What this repository helps with

- keeping work organized inside one Codex session
- using internal `/sub` workers only when they are justified
- separating planning, implementation, verification, and review
- running bounded fix-and-recheck loops instead of broad reruns
- keeping plan, status, results, and acceptance notes on disk
- selecting Agent Skills dynamically based on the task

### Repository layout

```text
.
|-- AGENTS.md
|-- README.md
|-- skills/
|   |-- agent-skills-integration/
|   |   `-- agent-skill-routing.md
|   |-- codex-parent-session-orchestrator/
|   |   |-- SKILL.md
|   |   |-- assets/run-templates/
|   |   `-- references/
|   `-- codex-subagent-orchestrator/
|       |-- SKILL.md
|       |-- agents/openai.yaml
|       |-- assets/run-templates/
|       `-- references/
`-- vendor/
    `-- agent-skills/
```

### Read this first

For the default one-session path:

- `skills/codex-parent-session-orchestrator/SKILL.md`
- `skills/codex-parent-session-orchestrator/references/parent-session-workflow.md`
- `skills/codex-parent-session-orchestrator/references/phase-spec-format.md`

For `/sub`:

- `skills/codex-subagent-orchestrator/SKILL.md`
- `skills/codex-subagent-orchestrator/references/orchestration-workflow.md`
- `skills/codex-subagent-orchestrator/references/sub-command-protocol.md`
- `skills/codex-subagent-orchestrator/references/testing-playbook.md`

For Agent Skills routing:

- `skills/agent-skills-integration/agent-skill-routing.md`

### Core rules

- default to one-session work
- use `/sub` or another explicit subagent request only when delegation is justified
- do not attach a reviewer after every writer
- use bounded repairs when review finds a problem
- do not load all Agent Skills by habit
- select only the skills that change behavior, validation, or acceptance for the current task

---

## 한국어

이 저장소는 Codex 작업을 두 가지 방식으로 정리해서 쓰기 위한 로컬 스킬 모음입니다.

- 기본은 현재 대화 세션 하나 안에서 작업하기
- 정말 필요할 때만 `/sub`로 내부 서브에이전트를 붙이기

현재 버전은 내부 대화 세션 기준으로 다시 정리된 구조입니다. 예전처럼 외부 실행 경로나 런처를 기본 경로로 두지 않습니다.

### 작동 방식

작업 방식은 두 가지입니다.

#### 1. 기본 방식: 한 세션 안에서 작업

사용자가 `/sub`를 명시하지 않고, 별도로 서브에이전트를 명시적으로 요청하지도 않으면 작업은 현재 Codex 대화 세션 안에서 진행됩니다.

기본 흐름은 아래와 같습니다.

1. 살펴보기
2. 계획 세우기
3. 구현하기
4. 확인하기
5. 검토하기

이 과정에서 문제가 보이면 그냥 끝내지 않습니다. 필요한 단계로 돌아가서 정해진 범위 안에서 고친 뒤 다시 확인합니다.

#### 2. `/sub` 방식: 내부 서브에이전트 사용

작업을 나눠 처리하는 편이 더 낫다고 판단되면 `/sub`를 사용해 내부 서브에이전트를 붙입니다.

실행 전에 부모 세션은 아래를 먼저 정합니다.

- 한 명으로 충분한지
- 순서대로 할지 동시에 할지
- 검토를 어디에 둘지
- 각 작업자가 어떤 파일이나 범위를 맡을지
- 어떤 규칙이 실제로 필요한지

### Agent Skills 통합

이 저장소는 Agent Skills 규칙 묶음도 함께 가져와 연결해 둔 상태입니다.

중요한 점은 이 규칙들을 무조건 한꺼번에 붙이지 않는다는 것입니다.

메인 세션이나 내부 서브에이전트는:

1. 먼저 지금 작업에 무엇이 필요한지 판단하고
2. 그다음 필요한 규칙만 고르고
3. 필요 없는 규칙은 붙이지 않으며
4. 작업상 정말 필요하면 여러 규칙을 함께 사용할 수 있습니다

즉, 기준은 “무조건 적게 쓰기”가 아니라  
“지금 필요한 것을 이유 있게 고르기”입니다.

### 이 저장소가 도와주는 일

- 한 세션 안에서 작업을 정리해서 진행하기
- `/sub`가 정말 필요한 경우에만 내부 작업자를 붙이기
- 계획, 구현, 확인, 검토를 나눠서 보기
- 문제를 찾았을 때 전부 다시 하기보다 필요한 범위만 고치고 다시 확인하기
- 계획, 상태, 결과, 승인 기록을 파일로 남기기
- Agent Skills를 작업에 맞게 골라 쓰기

### 저장소 구조

```text
.
|-- AGENTS.md
|-- README.md
|-- skills/
|   |-- agent-skills-integration/
|   |   `-- agent-skill-routing.md
|   |-- codex-parent-session-orchestrator/
|   |   |-- SKILL.md
|   |   |-- assets/run-templates/
|   |   `-- references/
|   `-- codex-subagent-orchestrator/
|       |-- SKILL.md
|       |-- agents/openai.yaml
|       |-- assets/run-templates/
|       `-- references/
`-- vendor/
    `-- agent-skills/
```

### 먼저 읽을 문서

기본 한 세션 경로:

- `skills/codex-parent-session-orchestrator/SKILL.md`
- `skills/codex-parent-session-orchestrator/references/parent-session-workflow.md`
- `skills/codex-parent-session-orchestrator/references/phase-spec-format.md`

`/sub` 경로:

- `skills/codex-subagent-orchestrator/SKILL.md`
- `skills/codex-subagent-orchestrator/references/orchestration-workflow.md`
- `skills/codex-subagent-orchestrator/references/sub-command-protocol.md`
- `skills/codex-subagent-orchestrator/references/testing-playbook.md`

Agent Skills 연결 규칙:

- `skills/agent-skills-integration/agent-skill-routing.md`

### 핵심 원칙

- 기본은 한 세션 작업
- `/sub` 또는 명시적 서브에이전트 요청은 필요할 때만 사용
- 구현자마다 검토자를 붙이지 않음
- 검토에서 문제를 찾으면 필요한 범위만 고친 뒤 다시 확인
- Agent Skills를 습관처럼 전부 붙이지 않음
- 현재 작업의 행동, 검증, 승인 기준을 바꾸는 규칙만 선택해서 사용
