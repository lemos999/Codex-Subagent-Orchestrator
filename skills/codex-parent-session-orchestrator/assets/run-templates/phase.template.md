# Phase

- phase:
- role:
- mode: read-only | write

## Goal

- 

## Read First

- AGENTS.md
- session-summary.md when this phase continues an existing run
- plan/<active-plan-file>.md when this phase depends on or advances an approved coding run after plan approval
- skills/agent-skills-integration/agent-skill-routing.md when this phase belongs to a coding run and needs the shared plan-first gate or vendored routing authority
- skills/plan-mode-default/SKILL.md when this phase belongs to a coding run and either creates or refines the plan, or depends on the approved plan-first gate
- skills/plan-mode-default/references/coding-plan-prompt-en.md when this phase belongs to a coding run and needs the detailed planning contract text; treat it as the default planning contract unless the user explicitly overrides its format while preserving the gate
- 

## Writable Scope

- 

## Selected Imported Skills

- 

## Imported Skill Rationale

- 

## Outputs To Update

- plan/<active-plan-file>.md when this phase refreshes the current approved plan record or its progress state
- plan/<timestamp>--<plan-type>--<slug>--vNN.md when this phase creates or versions a new approved plan record
- 

## Success Criteria

- 

## Validation

- 

## Stop Condition

- 
