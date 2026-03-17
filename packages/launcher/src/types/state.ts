/**
 * Orchestrator state machine — OTP Supervisor pattern (selective adoption).
 * Each phase is a discriminated union member.
 * The orchestrator transitions through these phases sequentially.
 */

import type { LauncherSpec } from './spec.js';
import type { Manifest, WorkerResult, StagePlan } from './manifest.js';
import type { Engine } from './engine.js';

// ============================================================
// Orchestrator state (discriminated union)
// ============================================================

export type OrchestratorState =
  | ParsingState
  | ValidatingState
  | BootstrappingState
  | ExecutingState
  | ReviewingState
  | FixingState
  | WritingEvidenceState
  | CompletedState
  | FailedState;

interface ParsingState {
  phase: 'parsing';
  specPath: string;
}

interface ValidatingState {
  phase: 'validating';
  spec: LauncherSpec;
  resolvedPaths: ResolvedPaths;
}

interface BootstrappingState {
  phase: 'bootstrapping';
  spec: LauncherSpec;
  resolvedPaths: ResolvedPaths;
  sharedDirective: string | null;
}

interface ExecutingState {
  phase: 'executing';
  spec: LauncherSpec;
  resolvedPaths: ResolvedPaths;
  currentStage: number;
  stagePlan: StagePlan[];
  completedResults: WorkerResult[];
  activeWorkers: WorkerHandle[];
}

interface ReviewingState {
  phase: 'reviewing';
  spec: LauncherSpec;
  resolvedPaths: ResolvedPaths;
  results: WorkerResult[];
}

interface FixingState {
  phase: 'fixing';
  spec: LauncherSpec;
  resolvedPaths: ResolvedPaths;
  previousResults: WorkerResult[];
  fixAttempt: number;
  maxAttempts: number;
}

interface WritingEvidenceState {
  phase: 'writing-evidence';
  spec: LauncherSpec;
  resolvedPaths: ResolvedPaths;
  results: WorkerResult[];
  manifest: Partial<Manifest>;
}

interface CompletedState {
  phase: 'completed';
  manifest: Manifest;
  summaryPath: string | null;
}

interface FailedState {
  phase: 'failed';
  error: OrchestratorError;
  partialResults: WorkerResult[];
  partialManifest: Partial<Manifest> | null;
}

// ============================================================
// Supporting types
// ============================================================

export interface ResolvedPaths {
  workspaceRoot: string;
  outputDir: string;
  manifestFile: string;
  summaryFile: string | null;
  debugLogFile: string | null;
  archiveRoot: string | null;
  specPath: string;
  specDirectory: string;
  invocationCwd: string;
}

export interface WorkerHandle {
  name: string;
  engine: Engine;
  stage: number;
  pid: number | null;
  startedAt: Date;
  stdoutPath: string;
  stderrPath: string;
  promptPath: string | null;
  lastPath: string;
}

export interface OrchestratorError {
  code: string;
  message: string;
  phase: string;
  workerName?: string;
  cause?: Error;
}

// ============================================================
// Supervisor strategy (OTP-inspired)
// ============================================================

export type RestartStrategy =
  | { kind: 'one_for_one' }
  | { kind: 'rest_for_one' };

export interface SupervisorPolicy {
  strategy: RestartStrategy;
  maxRestarts: number;
  withinMs: number;
}
