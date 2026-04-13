/**
 * Harness mode shared types.
 * Single source of truth for HarnessEvent, SessionState, and related types.
 */

import type { Engine } from '../types/engine.js';

// ============================================================
// Session state
// ============================================================

export type SessionState = 'created' | 'running' | 'idle' | 'terminated';

// ============================================================
// Harness events — CLI-realizable subset of Managed Agents pattern
// ============================================================

export type HarnessEvent =
  | WorkerSpawnedEvent
  | WorkerChunkEvent
  | WorkerToolUseEvent
  | WorkerMessageEvent
  | WorkerCompletedEvent
  | WorkerErrorEvent
  | SessionStateChangedEvent
  | StageStartedEvent
  | StageCompletedEvent;

export interface WorkerSpawnedEvent {
  type: 'worker.spawned';
  sessionId: string;
  name: string;
  engine: Engine;
  model: string;
  timestamp: string;
}

export interface WorkerChunkEvent {
  type: 'worker.chunk';
  sessionId: string;
  name: string;
  stream: 'stdout' | 'stderr';
  text: string;
  timestamp: string;
}

export interface WorkerToolUseEvent {
  type: 'worker.tool_use';
  sessionId: string;
  name: string;
  tool: string;
  timestamp: string;
}

export interface WorkerMessageEvent {
  type: 'worker.message';
  sessionId: string;
  name: string;
  text: string;
  timestamp: string;
}

export interface WorkerCompletedEvent {
  type: 'worker.completed';
  sessionId: string;
  name: string;
  exitCode: number;
  durationMs: number;
  timestamp: string;
}

export interface WorkerErrorEvent {
  type: 'worker.error';
  sessionId: string;
  name: string;
  error: string;
  timestamp: string;
}

export interface SessionStateChangedEvent {
  type: 'session.state_changed';
  sessionId: string;
  from: SessionState;
  to: SessionState;
  timestamp: string;
}

export interface StageStartedEvent {
  type: 'stage.started';
  stageNum: number;
  workerCount: number;
  timestamp: string;
}

export interface StageCompletedEvent {
  type: 'stage.completed';
  stageNum: number;
  succeeded: number;
  failed: number;
  timestamp: string;
}

// ============================================================
// Tool usage summary
// ============================================================

export interface ToolUsageSummary {
  name: string;
  calls: number;
}

// ============================================================
// Agent definition (from YAML registry)
// ============================================================

export interface AgentDefinition {
  id: string;
  version: number;
  name: string;
  engine: Engine;
  model: string;
  system: string;
  defaults?: {
    sandbox?: 'workspace-write' | 'read-only';
    kind?: string;
    reasoning_effort?: 'low' | 'medium' | 'high';
    extra_args?: string[];
  };
  metadata?: Record<string, unknown>;
}
