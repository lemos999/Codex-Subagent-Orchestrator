# Pattern A: Solo Agent

The simplest pattern. One agent handles the entire task.

## When to Use

- **Solo implementer**: Single bounded task, low risk, no review needed (ephemeral output)
- **Solo reviewer**: Validation-only request (`"review this file"`)
- **Solo explorer**: Research or analysis request (`"investigate this module"`)

## Discriminator: 0 Agents vs Pattern A

| Parent handles directly (0 agents) | Pattern A (1 agent) |
|---|---|
| Single-line change with exact edit known | Multi-line generation or file creation |
| Parent already has the file content in context | Task requires file inspection first |
| No tool calls needed beyond a quick Edit | Requires Read, Write, Glob, or Grep |
| Confidence is 100% without inspection | Some exploration or verification needed |

**Rule of thumb**: If you can complete it with one Edit tool call and no Read, skip the subagent.

## Solo Implementer Prompt

```
You operate under the shared contract in AGENTS.md at the workspace root. Read it before starting.

## Contract

**Task**: {{TASK_DESCRIPTION}}

**Inspect first**:
{{#each INSPECT_FILES}}
- {{this}}
{{/each}}

**Writable scope**:
{{#each WRITABLE_PATHS}}
- {{this.path}} ({{this.mode}})
{{/each}}

**Validation**:
1. Output file(s) exist and are non-empty
2. {{SPECIFIC_CHECK}}
3. No files outside writable scope modified

**Return**: files changed, key decision if material, validation results, assumptions, blocking or correctness-relevant uncertainty only
**Stop condition**: Complete the stated task. Do not expand scope. Stop once the result is sufficiently supported.
```

### Task Invocation

```python
Task(
    subagent_type="sub-implementer",
    model="haiku",  # solo tasks are typically simple; upgrade if needed
    description="{{SHORT_DESCRIPTION}}",
    prompt=IMPLEMENTER_PROMPT
)
```

## Solo Reviewer Prompt

```
You operate under the shared contract in AGENTS.md at the workspace root. Read it before starting.

## Review Contract

**Task**: Review {{TARGET_DESCRIPTION}}

**Files to review**:
{{#each TARGET_FILES}}
- {{this}}
{{/each}}

**Review criteria**:
1. {{CRITERION_1}}
2. {{CRITERION_2}}
3. {{CRITERION_3}}

**Return**: verdict, material evidence-backed findings with one fix direction (if any), files checked
**Stop condition**: Review only. Do not edit files. Converge on the verdict instead of listing open-ended possibilities.
```

### Task Invocation

```python
Task(
    subagent_type="sub-reviewer",
    model="haiku",
    description="Review {{SHORT_DESCRIPTION}}",
    prompt=REVIEWER_PROMPT
)
```

## Solo Explorer Prompt

```
You operate under the shared contract in AGENTS.md at the workspace root. Read it before starting.

## Exploration Contract

**Task**: {{RESEARCH_QUESTION}}

**Starting points**:
{{#each ENTRY_FILES}}
- {{this}}
{{/each}}

**Return**: findings, key files discovered, patterns identified, recommended next step or conclusion
**Stop condition**: Converge when possible; otherwise return the smallest justified set of remaining uncertainties or next-step branches. Do not modify any files.
```

### Task Invocation

```python
Task(
    subagent_type="Explore",
    model="haiku",
    description="Explore {{SHORT_DESCRIPTION}}",
    prompt=EXPLORER_PROMPT
)
```
