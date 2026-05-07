

## 한국어

이 저장소는 Codex 작업을 두 가지 방식으로 정리해서 쓰기 위한 로컬 워크플로 모음입니다.

- 기본은 현재 대화 세션 하나 안에서 작업하기
- 작업을 나누는 편이 실제로 도움이 될 때만 `/sub`로 내부 서브에이전트 붙이기

현재 버전은 내부 대화 세션 기준으로 정리된 구조입니다. 예전처럼 외부 실행 경로나 런처를 기본 경로로 두지 않습니다.

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

코딩 작업은 구현 전에 plan-first 게이트를 먼저 거칩니다.

1. 짧은 이해 보고를 한다
2. 명시적인 승인을 받는다
3. 승인된 계획을 `plan/` 아래에 작성하거나 갱신한다
4. 그다음 구현을 시작한다

코딩 작업에는 `skills/karpathy-guidelines/SKILL.md`가 기본 로컬 anti-overengineering overlay로 적용됩니다. 이 규칙은 설계를 작게 유지하고, 변경 범위를 수술적으로 좁히고, 가정을 드러내게 하지만, plan-first 흐름을 약화시키지는 않습니다.

추적되는 코딩 작업이라면 `plan/` 아래의 활성 계획 파일이 진행 상태와 점수 추적의 기준점이 됩니다. 사용자가 점수를 주면 그 점수를 우선 기록하고, 아직 점수를 주지 않았다면 `50` 이하의 보수적인 임시 점수를 유지한 채 계속 진행합니다.

나중에 들어온 작은 후속 코딩 작업이 이미 활성 승인 계획에 명시적으로 포함되어 있고 승인된 방향을 materially 바꾸지 않는다면, 새 승인 게이트를 다시 열지 않고 같은 계획 파일을 갱신하면서 계속 진행합니다.

중간에 문제가 보이면 그냥 멈추지 않습니다. 필요한 단계로 돌아가서 정해진 범위 안에서 고친 뒤, 활성 on-disk 기록을 필요하면 갱신하고 다시 확인합니다.

#### 2. `/sub` 방식: 내부 서브에이전트 사용

작업을 나눠 처리하는 편이 더 낫다고 판단되면 `/sub`를 사용해 내부 서브에이전트를 붙입니다.

실행 전에 부모 세션은 아래를 먼저 정합니다.

- 위임이 정당한지
- 한 명으로 충분한지
- 순차, 병렬, 혼합 중 어떤 방식이 맞는지
- 검토를 어디에 둘지
- 각 작업자가 어떤 파일이나 범위를 맡을지
- 어떤 스킬이 실제로 필요한지

부모 세션은 코딩 작업인지 비코딩 작업인지도 먼저 분류하고, 그 다음에야 코딩 전용 overlay나 planning 규칙을 읽습니다.

코딩 `/sub` 작업은 writable worker를 띄우기 전에 같은 plan-first 게이트를 그대로 따릅니다. 코딩 `/sub`에서는 승인 전에 잡는 팀 구성은 provisional일 뿐이고, 부모 세션이 활성 계획 파일과 점수 기록을 계속 책임집니다.

비코딩 `/sub` 작업은 코딩용 승인 게이트를 쓰지 않으며, 기본적으로 approval pause를 건너뜁니다.

나중에 들어온 작은 후속 코딩 단계가 이미 활성 승인 계획에 명시적으로 포함되어 있고 승인된 방향을 materially 바꾸지 않는다면, `/sub`도 새 승인 게이트를 다시 열지 않고 기존 계획 기록을 갱신하면서 계속 진행합니다.

### Agent Skills 통합

이 저장소는 Agent Skills 규칙 묶음도 함께 가져와 메인 워크플로와 연결해 둔 상태입니다.

중요한 점은 이 규칙들을 무조건 한꺼번에 붙이지 않는다는 것입니다.

부모 세션이나 내부 서브에이전트는:

1. 먼저 지금 작업에 무엇이 필요한지 판단하고
2. 그다음 관련 있는 스킬만 고르고
3. 필요 없는 스킬은 붙이지 않으며
4. 작업상 정말 필요하면 여러 스킬을 함께 사용할 수 있습니다

즉 기준은 "무조건 적게 쓰기"가 아니라 "지금 필요한 것을 이유 있게 고르기"입니다.

코딩 작업에서는 `skills/karpathy-guidelines/SKILL.md`가 기본 local overlay이고, vendored Agent Skills는 현재 작업의 계획, 구현, 검증, 승인 기준을 실제로 sharpen할 때만 추가합니다.

### 이 저장소가 도와주는 일

- 한 세션 안에서 작업을 정리해서 진행하기
- `/sub`가 정당할 때만 내부 작업자를 붙이기
- 코딩 작업에 plan-first 흐름 적용하기
- 코딩 작업에 기본 anti-overengineering overlay 적용하기
- 승인된 계획과 진행 기록을 `plan/` 아래에 유지하기
- 활성 계획 기록 안에서 점수와 만족도 상태를 추적하기
- 계획, 구현, 확인, 검토를 나눠서 보기
- 문제를 찾았을 때 전부 다시 하기보다 필요한 범위만 고치고 다시 확인하기
- 계획, 상태, 결과, 승인 기록을 파일로 남기기
- Agent Skills를 작업에 맞게 골라 쓰기

### 저장소 구조

```text
.
|-- AGENTS.md
|-- README.md
|-- plan/
|   |-- README.md
|   `-- *.md
|-- skills/
|   |-- agent-skills-integration/
|   |   `-- agent-skill-routing.md
|   |-- codex-parent-session-orchestrator/
|   |   |-- SKILL.md
|   |   |-- assets/run-templates/
|   |   `-- references/
|   |-- codex-subagent-orchestrator/
|   |   |-- SKILL.md
|   |   |-- agents/openai.yaml
|   |   |-- assets/run-templates/
|   |   `-- references/
|   |-- karpathy-guidelines/
|   |   `-- SKILL.md
|   `-- plan-mode-default/
|       |-- SKILL.md
|       `-- references/
`-- vendor/
    `-- agent-skills/
```

### 먼저 읽을 문서

공통 plan-first 및 score-tracking 계약:

- `AGENTS.md`
- `plan/README.md`
- `skills/agent-skills-integration/agent-skill-routing.md`
- `skills/plan-mode-default/SKILL.md`
- `skills/plan-mode-default/references/coding-plan-prompt-en.md`

기본 coding overlay:

- `skills/karpathy-guidelines/SKILL.md`

기본 한 세션 경로:

- `skills/codex-parent-session-orchestrator/SKILL.md`
- `skills/codex-parent-session-orchestrator/references/parent-session-workflow.md`
- `skills/codex-parent-session-orchestrator/references/phase-spec-format.md`

`/sub` 경로:

- `skills/codex-subagent-orchestrator/SKILL.md`
- `skills/codex-subagent-orchestrator/references/orchestration-workflow.md`
- `skills/codex-subagent-orchestrator/references/sub-command-protocol.md`
- `skills/codex-subagent-orchestrator/references/testing-playbook.md`
- `skills/codex-subagent-orchestrator/references/spec-format.md`

Agent Skills 연결 규칙:

- `skills/agent-skills-integration/agent-skill-routing.md`

### 핵심 원칙

- 기본은 한 세션 작업
- `/sub` 또는 다른 명시적 서브에이전트 요청은 위임이 정당할 때만 사용
- 코딩 작업은 구현 전에 plan-first 흐름을 먼저 따른다
- 코딩 작업에는 `skills/karpathy-guidelines/SKILL.md`를 기본 local anti-overengineering overlay로 적용한다
- 승인된 활성 계획은 `plan/` 아래에 두고 작업이 진행될수록 계속 갱신한다
- 진행 상태와 점수 추적은 활성 계획 파일 안에서 유지한다
- 나중에 들어온 작은 후속 코딩 단계가 이미 활성 승인 계획에 명시적으로 포함되어 있고 승인된 방향을 materially 바꾸지 않는다면, 새 승인 게이트를 다시 열지 않고 같은 계획을 갱신하면서 계속 진행한다
- 비코딩 `/sub` 작업은 기본적으로 approval pause를 건너뛴다
- 구현자마다 검토자를 붙이지 않는다
- 검토에서 문제를 찾으면 필요한 범위만 고친 뒤 다시 확인한다
- Agent Skills를 습관처럼 전부 붙이지 않는다
- 현재 작업의 행동, 검증, 승인 기준을 실제로 바꾸는 스킬만 선택해서 사용한다

- ---
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

For coding work, the repository also uses a plan-first gate before implementation begins:

1. give a short understanding report
2. get explicit approval
3. write or update the approved plan under `plan/`
4. only then begin implementation

For coding work, `skills/karpathy-guidelines/SKILL.md` is the default local anti-overengineering overlay. It is there to keep the design small, keep edits surgical, and keep assumptions explicit without weakening the plan-first workflow.

For tracked coding work, the active plan under `plan/` is also the place where progress and score tracking live. If the user gives a score, record it there as authoritative. If the user has not scored the work yet, keep a conservative provisional score at `50` or below and continue working.

If a later tiny follow-up coding change is already explicitly covered by the active approved plan and does not materially change the approved direction, continue under that same plan and refresh the plan record instead of reopening a fresh approval gate.

If a problem is found, the workflow does not just stop there. It goes back to the necessary step, applies a bounded fix, updates the active on-disk record when needed, and checks again.

#### 2. `/sub` mode: internal subagents

If the task is better handled by splitting work, `/sub` can be used to supervise internal subagents.

Before launch, the parent session decides:

- whether delegation is justified
- whether one worker is enough
- whether the run should be serial, parallel, or mixed
- where review belongs
- which files or scopes each worker owns
- which skills are actually needed

The parent also classifies the run as coding or non-coding before it loads coding-only overlays or planning rules.

For coding runs, `/sub` still follows the same plan-first gate before any writable worker launch. For coding runs, any team shape decided before approval is provisional only, and the parent remains responsible for keeping the active plan file and its score record current.

For non-coding runs, `/sub` does not use the coding approval gate and skips the approval pause by default.

If a later tiny follow-up coding step is already explicitly covered by the active approved plan and does not materially change the approved direction, `/sub` continues under that same approved plan and refreshes the active plan record instead of reopening a fresh approval gate.

### Agent Skills integration

This repository also includes the Agent Skills pack and connects it to the main workflow.

The important part is that those skills are not loaded blindly.

The parent session or internal subagents:

1. first decide what the current task needs
2. then select only the relevant skills
3. avoid attaching unnecessary skills
4. can use multiple skills when the task truly requires them

In short, the rule is not "always use fewer skills." The rule is "use what is needed, and explain why."

For coding work, the local default overlay is `skills/karpathy-guidelines/SKILL.md`. Vendored Agent Skills are added only when they materially improve planning, implementation, validation, or acceptance for the current task.

### What this repository helps with

- keeping work organized inside one Codex session
- using internal `/sub` workers only when they are justified
- applying a plan-first flow for coding work
- applying a default anti-overengineering overlay for coding work
- keeping approved plans and progress records under `plan/`
- tracking score and satisfaction state in the active plan record
- separating planning, implementation, verification, and review
- running bounded fix-and-recheck loops instead of broad reruns
- keeping plan, status, results, and acceptance notes on disk
- selecting Agent Skills dynamically based on the task

### Repository layout

```text
.
|-- AGENTS.md
|-- README.md
|-- plan/
|   |-- README.md
|   `-- *.md
|-- skills/
|   |-- agent-skills-integration/
|   |   `-- agent-skill-routing.md
|   |-- codex-parent-session-orchestrator/
|   |   |-- SKILL.md
|   |   |-- assets/run-templates/
|   |   `-- references/
|   |-- codex-subagent-orchestrator/
|   |   |-- SKILL.md
|   |   |-- agents/openai.yaml
|   |   |-- assets/run-templates/
|   |   `-- references/
|   |-- karpathy-guidelines/
|   |   `-- SKILL.md
|   `-- plan-mode-default/
|       |-- SKILL.md
|       `-- references/
`-- vendor/
    `-- agent-skills/
```

### Read this first

For the shared plan-first and score-tracking contract:

- `AGENTS.md`
- `plan/README.md`
- `skills/agent-skills-integration/agent-skill-routing.md`
- `skills/plan-mode-default/SKILL.md`
- `skills/plan-mode-default/references/coding-plan-prompt-en.md`

For the default coding overlay:

- `skills/karpathy-guidelines/SKILL.md`

For the default one-session path:

- `skills/codex-parent-session-orchestrator/SKILL.md`
- `skills/codex-parent-session-orchestrator/references/parent-session-workflow.md`
- `skills/codex-parent-session-orchestrator/references/phase-spec-format.md`

For `/sub`:

- `skills/codex-subagent-orchestrator/SKILL.md`
- `skills/codex-subagent-orchestrator/references/orchestration-workflow.md`
- `skills/codex-subagent-orchestrator/references/sub-command-protocol.md`
- `skills/codex-subagent-orchestrator/references/testing-playbook.md`
- `skills/codex-subagent-orchestrator/references/spec-format.md`

For Agent Skills routing:

- `skills/agent-skills-integration/agent-skill-routing.md`

### Core rules

- default to one-session work
- use `/sub` or another explicit subagent request only when delegation is justified
- for coding work, follow the plan-first flow before implementation
- for coding work, apply `skills/karpathy-guidelines/SKILL.md` as the default local anti-overengineering overlay
- keep the approved active plan under `plan/` and keep it updated as work moves
- keep progress and score tracking in the active plan under `plan/`
- if a later tiny follow-up coding step is already explicitly covered by the active approved plan and does not materially change the approved direction, continue under that plan and refresh the plan record instead of reopening a fresh approval gate
- for non-coding `/sub` runs, skip the approval pause by default
- do not attach a reviewer after every writer
- use bounded repairs when review finds a problem
- do not load all Agent Skills by habit
- select only the skills that change behavior, validation, or acceptance for the current task


