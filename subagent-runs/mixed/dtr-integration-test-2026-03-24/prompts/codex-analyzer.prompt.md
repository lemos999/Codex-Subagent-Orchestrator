분석만 수행. 코드 수정 금지.

## Relevant Context (auto-injected)

### C:/Users/haj/projects/subagent-orchestrator/packages/launcher/src/workers/output-quality.ts (lines 1-10)
**other** — other
```typescript
/**
 * DTR-inspired output quality checker.
 * Detects overthinking signals in worker output text.
 *
 * Based on Deep-Thinking Tokens research:
```

### skills/codex-subagent-orchestrator/references/orchestration-workflow.md (lines 317-331)
**Pattern E: Implementer -> Reviewer -> Fixer -> Reviewer** — markdown-section
> ## Pattern E: Implementer -> Reviewer -> Fixer -> Reviewer
> 
> Use when:
> 
> - the reviewer finds a bounded, repairable issue

### skills/codex-subagent-orchestrator/references/orchestration-workflow.md (lines 236-247)
**7. Validate results** — markdown-section
> ### 7. Validate results
> 
> The parent should check:
> 
> - expected files exist

### C:/Users/haj/projects/subagent-orchestrator/packages/launcher/src/types/state.ts (lines 61-68)
**FixingState** — interface
```typescript
interface FixingState {
  phase: 'fixing';
  spec: LauncherSpec;
  resolvedPaths: ResolvedPaths;
  previousResults: WorkerResult[];
```

### .gemini/skills/gemini-subagent-orchestrator/references/sub-command-protocol.md (lines 28-32)
**Validation** — markdown-section
> ## Validation
> 
> - Always trust the read-only reviewer over the implementer.
> - If a reviewer finds a material issue, launch a bounded fixer spec instead of patching the deliverable directly.

packages/launcher/src/workers/output-quality.ts 파일을 읽고 checkOutputQuality 함수가 어떤 패턴을 감지하는지 한글로 설명하라. 코드를 수정하지 마라.