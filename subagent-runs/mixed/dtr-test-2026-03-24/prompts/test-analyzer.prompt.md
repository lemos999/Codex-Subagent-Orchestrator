Analysis only. Do NOT modify any files.

## Relevant Context (auto-injected)

### subagent-runs/mixed/dtr-test-2026-03-24/test-spec.json (lines 1-16)
**line-block** — line-block
```json
{
  "cwd": "C:/Users/haj/projects/subagent-orchestrator",
  "agents": [
    {
      "name": "test-analyzer",
```

### C:/Users/haj/projects/subagent-orchestrator/packages/launcher/src/workers/spawn.ts (lines 1-18)
**other** — other
```typescript
/**
 * Worker spawner — runs CLI commands via child_process.spawn.
 * Handles codex, claude, and gemini engines.
 */

```

### C:/Users/haj/projects/subagent-orchestrator/packages/launcher/src/workers/spawn.ts (lines 314-318)
**other** — other
```typescript
// ============================================================
// Convert WorkerOutput to WorkerResult
// ============================================================
```

### C:/Users/haj/projects/subagent-orchestrator/packages/launcher/src/workers/spawn.ts (lines 75-79)
**SpawnCommand** — interface
```typescript
interface SpawnCommand {
  cmd: string;
  args: string[];
  stdin?: string;
}
```

### C:/Users/haj/projects/subagent-orchestrator/packages/launcher/src/workers/spawn.ts (lines 194-206)
**other** — other
```typescript
// ============================================================
// Main spawn function
// ============================================================

/**
```

Read packages/launcher/src/workers/spawn.ts and explain the spawnWorker function in one sentence.