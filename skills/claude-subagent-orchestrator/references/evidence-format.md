# Evidence Format

## Purpose

Evidence enables auditability, debugging, and learning from past runs.

## Directory Structure

```
subagent-runs/
├── claude/          # engine=claude, Task tool 네이티브 실행
├── codex/           # engine=codex, codex exec 실행
├── gemini/          # engine=gemini, gemini-cli 실행
└── mixed/           # 혼합 엔진 실행
    └── <run-name>/
        ├── run-manifest.md
        ├── run-summary.md
        ├── prompts/
        ├── results/
        └── engines/         # 엔진별 raw 증거
            ├── claude/
            ├── codex/
            └── gemini/
```

### 저장 경로 정책

- **단일 엔진 실행**: 해당 엔진 디렉토리 (예: `subagent-runs/claude/<run-name>/`) -- 기존과 동일
- **혼합 엔진 실행**: `subagent-runs/mixed/<run-name>/` -- `engines/` 하위에 엔진별 raw 증거 분리

### 단일 엔진 디렉토리 구조

```
subagent-runs/<engine>/
└── <run-name>/
    ├── run-manifest.md          # Structured run record (authoritative)
    ├── run-summary.md           # Compact one-liner-per-agent summary
    ├── prompts/                 # Per-worker prompt preservation
    │   ├── <agent-1-role>.prompt.md
    │   └── <agent-2-role>.prompt.md
    └── results/                 # Per-worker return preservation
        ├── <agent-1-role>.result.md
        └── <agent-2-role>.result.md
```

### Run Naming

Format: `<task-slug>-<YYYY-MM-DD>`

Examples: `auth-middleware-2026-03-11`, `fix-login-bug-2026-03-11`

Collision: append sequence number (`-2`, `-3`).

## Run Manifest

The authoritative record. Written by the orchestrator after run completion.

```markdown
# Run Manifest: <run-name>

## Request
- **Original**: [full /sub request text]
- **Classification**: [create | fix | refactor | review | analyze]
- **Complexity**: [low | medium | high]

## Team
- **Pattern**: [A | B | C | D | E] — [pattern name]
- **Agent count**: [number]
- **Shared directive**: [reference | inline]

## Agents

### Agent 1: <role>
- **Engine**: claude | codex | gemini
- **Type**: sub-implementer | sub-reviewer | sub-fixer
- **Model**: [engine-specific model name]
- **Stage**: [1 | 2 | 3]
- **Status**: completed | failed | timeout
- **Agent ID**: [for resume capability]
- **Contract summary**: [one-line task description]
- **Result summary**: [one-line outcome]
- **Prompt file**: prompts/<role>.prompt.md
- **Result file**: results/<role>.result.md

### Agent 2: <role>
[same structure]

## Deliverables
- [path/to/file1]: [created | modified] — [description]

## Review
- **Verdict**: ACCEPTED | MINOR_ISSUES | MATERIAL_ISSUES
- **Fix cycles**: [0 | 1 | 2]
- **Final reviewer**: [agent role and model]

### Watchdog (if enabled)

| Field | Value |
|-------|-------|
| Enabled | yes / no |
| Stages watched | [list of stage names] |

| Stage | Verdict | Findings | Leader Decision | Reason |
|-------|---------|----------|-----------------|--------|
| {{stage}} | PASS / SHORTFALL | {{findings}} | Accept / Reject / Escalate | {{reason}} |

## Metrics
- **Agents used**: [count]
- **Deliverables / agents**: [ratio]
- **Fix cycles**: [count]
- **Model cost profile**: [e.g., "1x sonnet + 1x haiku"]
- **Final read-only review**: [yes | no]

## Timeline
- **Started**: [ISO 8601]
- **Completed**: [ISO 8601]

## Errors / Notes
- [any errors, warnings, or orchestrator notes]
```

## Per-Worker Prompt File

Preserved in `prompts/<role>.prompt.md`. Contains the **exact text** sent as the `prompt` parameter to the Task tool.

This enables:
- **Replay**: Re-run the same prompt to reproduce results
- **Debugging**: Understand what the worker was told
- **Improvement**: Refine prompts based on outcomes

## Per-Worker Result File

Preserved in `results/<role>.result.md`. Contains the **full text** returned by the worker agent.

This enables:
- **Audit**: Verify what the worker claimed vs. what actually happened
- **Debugging**: Understand why a reviewer accepted or rejected
- **Learning**: Identify patterns in successful vs. failed runs

When watchdog is enabled, also write:
- `subagent-runs/<engine>/<run-name>/prompts/watchdog-<stage>.prompt.md` (single engine) or `subagent-runs/mixed/<run-name>/prompts/watchdog-<stage>.prompt.md` (mixed engines)
- `subagent-runs/<engine>/<run-name>/results/watchdog-<stage>.result.md` (single engine) or `subagent-runs/mixed/<run-name>/results/watchdog-<stage>.result.md` (mixed engines)

## Run Summary

Compact format for quick scanning.

```markdown
# Run Summary: <run-name>

| # | Role | Engine | Model | Stage | Status | Result |
|---|---|---|---|---|---|---|
| 1 | implementer | claude | sonnet | 1 | completed | Created src/middleware/auth.ts |
| 2 | reviewer | claude | haiku | 2 | completed | ACCEPTED |

When watchdog is enabled, add Watchdog columns to the summary table:

| # | Role | Engine | Model | Stage | Status | Result | Watchdog | WD Verdict |
|---|---|---|---|---|---|---|---|---|

**Verdict**: ACCEPTED
**Deliverables**: src/middleware/auth.ts (created)
**Cost profile**: 1x claude/sonnet + 1x claude/haiku
**Evidence**: subagent-runs/<engine>/<run-name>/ 또는 subagent-runs/mixed/<run-name>/
```

## When to Create Evidence

| Scenario | Evidence Level |
|---|---|
| `/sub` with implementation + review | Full: manifest + summary + prompts + results |
| `/sub` with solo implementer | Standard: manifest + summary + prompts |
| `/sub` with solo reviewer | Light: summary only |
| Trivial task, parent handles | None |
| Research/exploration | None |
| `/sub` with watchdog | Full + watchdog files (manifest + summary + prompts + results + watchdog prompts/results) |
| Failed/aborted run | Full: manifest documents what failed and why |

## Error Evidence

When a run fails partially:

```markdown
## Errors / Notes
- Agent 1 (implementer) completed successfully
- Agent 2 (reviewer) reported MATERIAL_ISSUES
- Agent 3 (fixer) launched but timed out after max_turns
- Run aborted: escalated to user after 2 failed fix cycles
- Partial deliverables may exist at stated paths — NOT reviewed/accepted
```

Failed runs still get full evidence. The manifest documents exactly what happened for debugging.

### Hash-Chain Fields (C4)

Run manifest에 다음 optional 필드가 포함될 수 있다:

```json
{
  "evidence": {
    "chain_index": 5,
    "prev_hash": "<64-char hex>",
    "current_hash": "<64-char hex>",
    "salt": "<32-char hex>",
    "spec_sha256": "<64-char hex>"
  }
}
```

- `chain_index`: 이 run의 체인 내 순번
- `prev_hash`: 직전 run의 hash ("0"x64 if genesis)
- `current_hash`: 이 run의 결정적 해시
- `salt`: 세션 랜덤 salt (재검증에 필요)
- `spec_sha256`: spec 파일 해시

전체 체인 검증: `--verify-chain` CLI 옵션으로 실행.
