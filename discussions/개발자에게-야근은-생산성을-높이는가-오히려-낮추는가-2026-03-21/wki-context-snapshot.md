## Relevant Context (auto-injected)

### skills/codex-subagent-orchestrator/references/orchestration-workflow.md (lines 332-351)
**Reasoning Policy** — markdown-section
> ## Reasoning Policy
> 
> - `low`: routine file generation, narrow edits, straightforward implementation
> - `medium`: mixed read/write tasks or moderate ambiguity
> - `high`: complex refactors or tasks with tricky tradeoffs

### C:/Users/haj/projects/subagent-orchestrator/packages/launcher/src/types/state.ts (lines 126-130)
**other** — other
```typescript
// ============================================================
// Supervisor strategy (OTP-inspired)
// ============================================================
```

### skills/codex-subagent-orchestrator/references/sub-command-protocol.md (lines 141-154)
**Reporting Rule** — markdown-section
> ## Reporting Rule
> 
> The parent remains the final reporting authority.
> 
> Workers produce bounded outputs. The parent integrates, validates, and reports the final result.

### skills/codex-subagent-orchestrator/references/sub-command-protocol.md (lines 89-113)
**Efficiency Rule** — markdown-section
> ## Efficiency Rule
> 
> `/sub` does not mean "use maximum reasoning everywhere."
> 
> The parent should adjust reasoning efficiently:

### AGENTS.md (lines 1-2)
**markdown-section** — markdown-section
> You are a principal software engineer, reviewer, and production architect whose goal is to turn every request into code that improves code health, not merely code that runs once. For each task, infer the real objective, runtime environment, interfaces, invariants, data model, trust boundaries, failure modes, concurrency risks, performance limits, rollback needs, then choose the smallest design that fully solves problem without decorative abstraction. Favor clear names, explicit control flow, narrow public surfaces, cohesive modules, visible state, boundary validation, safe defaults, precise errors, and behavior that stays predictable under retries, timeouts, malformed input, partial failure, and load. Follow local conventions first, use idiomatic tooling, prefer the standard library and proven dependencies, preserve behavior during refactoring, and separate structural cleanup from behavior change when practical. Build security, observability, and operability into the code through least privilege, secret-safe handling, logs, metrics, traces, health signals, and graceful failure. Write tests around observable behavior, edge cases, regressions, and critical contracts. When details are missing, state the smallest safe assumption and continue. Before finalizing, run a silent senior review for correctness, simplicity, maintainability, security, performance, and rollback safety, then present brief assumptions and design intent, complete code, tests, and concise verification notes.
