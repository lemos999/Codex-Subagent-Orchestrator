/**
 * Engine and role type definitions.
 * Encodes the engine-role compatibility matrix at the type level.
 */

// ============================================================
// Engine identifiers
// ============================================================

export type Engine = 'codex' | 'claude' | 'gemini';

export type CodexModel = 'gpt-5.4' | 'o3' | 'o4-mini';
export type ClaudeModel = 'haiku' | 'sonnet' | 'opus';
export type GeminiModel = 'gemini-2.5-pro' | 'gemini-2.5-flash';

export type Model = CodexModel | ClaudeModel | GeminiModel;

// ============================================================
// Worker roles
// ============================================================

export type WorkerKind =
  | 'implementer'
  | 'reviewer'
  | 'validator'
  | 'fixer'
  | 'planner'
  | 'custom';

// ============================================================
// Engine-model mapping (runtime validation)
// ============================================================

export const ENGINE_MODELS: Record<Engine, readonly string[]> = {
  codex: ['gpt-5.4', 'o3', 'o4-mini'],
  claude: ['haiku', 'sonnet', 'opus'],
  gemini: ['gemini-2.5-pro', 'gemini-2.5-flash'],
} as const;

export const ENGINE_DEFAULTS: Record<Engine, string> = {
  codex: 'gpt-5.4',
  claude: 'sonnet',
  gemini: 'gemini-2.5-pro',
} as const;

// ============================================================
// Sandbox
// ============================================================

export type Sandbox = 'workspace-write' | 'read-only';

// ============================================================
// Reasoning effort
// ============================================================

export type ReasoningEffort = 'low' | 'medium' | 'high';

// ============================================================
// Execution mode
// ============================================================

export type ExecutionMode = 'parallel' | 'sequential';
