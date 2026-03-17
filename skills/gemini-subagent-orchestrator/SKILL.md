---
name: gemini-subagent-orchestrator
description: Orchestrate launcher-backed subagent teams for `/sub` requests. Gemini acts as supervisor, writes a JSON spec, and invokes `start-codex-subagent-team.ps1`. Supports single-engine Gemini teams and mixed-engine teams via per-agent `engine` fields.
---

# Gemini Subagent Orchestrator

## Overview

Use this skill when Gemini should act as a supervisor and delegate execution to a bounded worker team rather than performing the task directly.

For `/sub`, use the project's **External Pipeline Launcher** for every run. Do not bypass the launcher by calling native tools such as `generalist` or `codebase_investigator` as a shortcut.

## Read In This Order

- Read `references/orchestration-workflow.md` for team patterns, launch flow, and recovery.
- Read `references/sub-command-protocol.md` for `/sub` routing and evidence rules.
- Read `assets/spec-templates/gemini-native-team.template.json` to see how an external spec looks when `engine: "gemini"` is used.

## Core Principles

1.  **Strict Pipeline Execution:** Every `/sub` command writes a `.spec.json` file and invokes `start-codex-subagent-team.ps1`.
2.  **Supervisor Stays Supervisor:** Never edit requested deliverables directly when a bounded worker can do it.
3.  **Mixed Engines Are Allowed Through the Launcher:** A Gemini-led run may still use child workers with `engine: "gemini"`, `engine: "codex"`, or `engine: "claude"` when the role split justifies it.
4.  **Strict Review Gates:** Persistent deliverables require a read-only reviewer before acceptance. Material issues should trigger a scoped fixer and re-review.
5.  **Evidence & Traceability (필수, 생략 불가):** Single-engine Gemini runs write evidence to `subagent-runs/gemini/<run-name>/`. Mixed-engine runs write evidence to `subagent-runs/mixed/<run-name>/`. 사용자에게 결과를 보고하기 전에 반드시 evidence를 기록해야 한다. 실패/중단 run도 기록한다.

## Pipeline Spec Structure (External Mode)

Every `/sub` run uses the External Pipeline Launcher. Define `"engine": "gemini"` in `defaults` for Gemini-led runs, and override per-agent `engine` only when a mixed team is needed.

```json
{
  "cwd": ".",
  "output_dir": "subagent-runs/gemini/example-run",
  "defaults": {
    "engine": "gemini",
    "model": "gemini-2.5-pro",
    "sandbox": "workspace-write"
  },
  "agents": [
    {
      "name": "implementer",
      "task": "Build the feature."
    },
    {
      "name": "reviewer",
      "sandbox": "read-only",
      "task": "Review the feature."
    }
  ]
}
```
