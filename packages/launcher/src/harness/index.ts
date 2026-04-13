/**
 * Harness mode — barrel export.
 */

export { HarnessEventBus } from './event-bus.js';
export { SessionManager, generateSessionId } from './session-manager.js';
export { ToolTracker } from './tool-tracker.js';
export { EventLogWriter } from './event-log-writer.js';
export { getParser } from './engine-parsers.js';
export { loadAgentDefinition, listAgentIds } from './agent-registry.js';
export {
  detectConvergence,
  extractFeedback,
  createStagnationState,
  recordFailure,
  recordSuccess,
  suggestAlternative,
  DEFAULT_EVOLVE_CONFIG,
} from './convergence.js';

export type {
  ConvergenceVerdict,
  StagnationState,
  EvolveConfig,
} from './convergence.js';

export type {
  HarnessEvent,
  SessionState,
  ToolUsageSummary,
  AgentDefinition,
  WorkerSpawnedEvent,
  WorkerChunkEvent,
  WorkerToolUseEvent,
  WorkerMessageEvent,
  WorkerCompletedEvent,
  WorkerErrorEvent,
  SessionStateChangedEvent,
  StageStartedEvent,
  StageCompletedEvent,
} from './types.js';

export type { ParserContext, ChunkParser } from './engine-parsers.js';
