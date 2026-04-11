# Worker Brief

- shared contract: AGENTS.md
- worker:
- role:
- mode: read-only | write

## Mission

- 

## Concrete Task

- 

## Read First

- AGENTS.md
- skills/plan-mode-default/SKILL.md when this worker is planner-like or performs plan refinement and the file exists
- skills/plan-mode-default/references/coding-plan-prompt-en.md when this worker is planner-like or performs plan refinement and the file exists; treat it as the detailed planning contract unless the user explicitly overrides it
- 

## Writable Scope

- 

## Selected Imported Skills

- 

## Imported Skill Rationale

- 

## Validation

- 

## Return Contract

- 
- if this is a write task, summarize the proposed change so the parent can land it in the primary workspace
- if this is a planner-like task for coding work, identify the approved plan file path the parent should write or update under `plan/`, plus the plan type, version decision, and any progress fields the parent must refresh

## Stop Condition

- 
