# Orchestration Workflow (Gemini)

## Purpose

This workflow defines how the Gemini Orchestrator breaks down work, writes launcher specs, runs the worker team, and evaluates the results.

## Workflow Stages

### 1. Classify the Request & Choose Pattern

When the user requests `/sub <task>`, decide the smallest useful team:
- **Pattern A (Solo):** one worker for a narrow artifact
- **Pattern B (Implement-Review):** default for bounded implementation
- **Pattern C (Parallel):** independent workers feeding a final reviewer
- **Pattern D (Plan-Implement-Review):** architecture or ambiguous work
- **Pattern E (Full Loop):** implementation with planned repair cycles

Choose a mixed-engine team only when a role clearly benefits from `codex` or `claude`. Otherwise keep the team Gemini-only.

### 2. Generate the JSON Spec

Write a JSON spec file for the launcher.

For single-engine Gemini runs:
- Set `defaults.engine` to `"gemini"`.
- Set `output_dir` to `subagent-runs/gemini/<run-name>`.

For mixed-engine runs:
- Keep Gemini as the supervisor.
- Override `engine` per worker as needed.
- Set `output_dir` to `subagent-runs/mixed/<run-name>`.

Prefer these policy fields when a deliverable matters:
- `supervisor_only: true`
- `require_final_read_only_review: true`
- `material_issue_strategy: "fixer_then_rereview"`

### 3. Execute the Launcher

Run the launcher with the generated spec.

**Primary — TS launcher:**

```bash
node packages/launcher/dist/cli.js --spec ./<task-name>.spec.json
```

**Fallback — PS launcher (legacy):**

```powershell
& ".\skills\codex-subagent-orchestrator\scripts\start-codex-subagent-team.ps1" -SpecPath ".\<task-name>.spec.json" -AsJson
```

### 4. Validate & Write Evidence & Report

> ⚠️ **BLOCKING STAGE**: Evidence 작성 완료 전에는 사용자에게 결과를 보고할 수 없다.

1. Wait for the launcher to finish.
2. Read `orchestration-summary.md` and `orchestration-manifest.json`.
3. Accept the run only if the reviewer outcome and required artifacts are sound.
4. **Evidence 확인**: `subagent-runs/gemini/<run-name>/` (또는 `mixed/`) 에 `run-manifest.md`, `run-summary.md`, `prompts/`, `results/` 가 존재하는지 확인. 런처가 생성하지 않았다면 직접 작성.
5. Report the result to the user with the evidence path.

### 5. Bounded Recovery Loop

If the reviewer rejects or a worker fails:
- Do not rerun the full team unless the entire decomposition was wrong.
- Create a recovery spec containing only the bounded `fixer` and the final read-only reviewer.
- Pass the prior findings into the recovery spec as explicit context.
