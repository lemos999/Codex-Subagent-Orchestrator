# Claude Subagent Orchestrator

Supervise one or more Claude Code subagents for delegated implementation, review, analysis, or generation work — using Claude Code's native Task tool and built-in agent types.

## Trigger

Activate when the user message starts with `/sub`, or asks for subagents, delegated execution, or supervised multi-agent workflows.

## Execution Engine

This orchestrator uses **Claude Code's native Task tool** with these parameters:

| Parameter | Values | Purpose |
|---|---|---|
| `subagent_type` | `sub-implementer`, `sub-reviewer`, `sub-fixer` | Worker role |
| `model` | `haiku`, `sonnet`, `opus` | Match capability to task complexity |
| `isolation` | `"worktree"` | Isolated git worktree for parallel writers |
| `run_in_background` | `true` / `false` | Non-blocking for independent long tasks |
| `resume` | agent ID string | Continue a previous agent's work |
| `prompt` | contract text | Worker's complete bounded contract |
| `description` | short label | 3-5 word task summary |

## External Engine Support

이 오케스트레이터는 Claude Task tool 외에도 외부 CLI 엔진을 워커로 사용할 수 있다.

| Engine | Invocation | Use When |
|---|---|---|
| `claude` (기본) | Task tool 네이티브 | 대부분의 작업 -- 도구 접근 필요 시 |
| `codex` | Bash -> `codex exec` | 사용자가 GPT 모델 지정 시, 또는 Codex 전용 기능 필요 시 |
| `gemini` | Bash -> `npx @google/gemini-cli --prompt` | 사용자가 Gemini 모델 지정 시 |

상세 사양은 `./references/engine-adapters.md` 참조.

## Reading Order

**Quick start** (Pattern B, most runs): Read #1 and #2 only.
**Full read** (first run or complex patterns): Read all five in order.

1. `./references/orchestration-workflow.md` — stages, patterns, shared directive injection, fallback
2. `./references/sub-command-protocol.md` — routing, sizing, model allocation (single source of truth)
3. `./references/agent-contract.md` — contract structure, agent behaviors, tool guidance
4. `./references/evidence-format.md` — manifest, summary, per-worker evidence
5. `./references/testing-playbook.md` — test scenarios, validation checklist
6. `./references/engine-adapters.md` — 엔진별 CLI 사양, 호환성 매트릭스, 에러 처리 (혼합 엔진 사용 시)

Prompt templates for each pattern: `./assets/prompt-templates/pattern-{a,b,c,d,e}-*.md`

All paths are relative to `./skills/claude-subagent-orchestrator/`.

## Core Principles

1. **Supervisor stays supervisor.** Never edit deliverable files directly.
2. **Single source of truth.** Each concept lives in one reference file — do not duplicate rules across prompts.
3. **Explicit contracts.** Every worker gets a structured contract (see `agent-contract.md`).
4. **Review gate.** Persistent deliverables require read-only `sub-reviewer` before acceptance.
5. **Bounded recovery.** Material issues → `sub-fixer` (scoped) → `sub-reviewer` re-validation. Max 2 cycles.
6. **Evidence.** Every run writes manifest + summary to `subagent-runs/<engine>/<run-name>/` (single engine) or `subagent-runs/mixed/<run-name>/` (mixed engines).
7. **Shared directive.** Inject the AGENTS.md operating contract into every worker prompt (see `orchestration-workflow.md`).
8. **Economy.** Use the cheapest model that satisfies the task. Haiku for routine, sonnet default, opus for complex.
9. **Watchdog hooks.** Optional goal-alignment agents that monitor worker output against the original goal. On shortfall, the orchestrator applies the 3-choice protocol: Accept (fix), Reject (log and proceed), or Escalate (ask user). See `orchestration-workflow.md` Stage 7.5.

## Anti-Patterns

| Anti-Pattern | Correct Approach |
|---|---|
| Parent editing deliverables | Delegate to `sub-implementer` |
| Skipping review | Always use `sub-reviewer` for persistent output |
| Full team rerun for one issue | Launch scoped `sub-fixer` |
| Opus for boilerplate | Use haiku or sonnet |
| 4+ agents for simple task | Default is 2 (implementer + reviewer) |
| Duplicating rules in prompt | Reference the contract format, don't restate it |
| Phantom evidence | Only claim artifacts actually produced |
| Watchdog on every trivial task | Enable watchdog only when goal drift risk is high |
| Watchdog replacing reviewer | Watchdog checks goal alignment; reviewer checks correctness. Both needed. |
| Always accepting watchdog feedback | Leader must evaluate — reject unrealistic feedback |

## Known Limitations

| Capability | Status |
|---|---|
| Unattended queue polling | Not supported — use Codex queue runner |
| Per-worker sandbox enforcement | Not enforced by runtime — relies on prompt discipline |
| Live token monitoring | Not available — estimate from model selection |
| Worker process isolation | Workers share the workspace unless `isolation: "worktree"` |
| Streaming worker output | Not available — results returned on completion |
| Watchdog goal interpretation | Relies on prompt fidelity — watchdog may misinterpret ambiguous goals |
| External engine tool access | `codex` and `gemini` workers use CLI — no Claude Code tool integration |
| Engine-role compatibility | `claude --print` cannot run implementer/fixer roles (no tool access) |
| Mixed engine evidence | Mixed runs store evidence in `subagent-runs/mixed/` |
