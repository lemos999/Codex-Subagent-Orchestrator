/**
 * Zod-based spec JSON validation — Phase 1.
 * Converts the TypeScript interfaces in types/spec.ts to runtime Zod schemas.
 * Unsupported Phase 2 fields cause explicit errors.
 */

import { z } from 'zod';
import type { LauncherSpec } from '../types/spec.js';

// ============================================================
// Reusable enums
// ============================================================

const EngineSchema = z.enum(['codex', 'claude', 'gemini']);
const SandboxSchema = z.enum(['workspace-write', 'read-only']);
const ReasoningEffortSchema = z.enum(['low', 'medium', 'high']);
const ExecutionModeSchema = z.enum(['parallel', 'sequential']);
const WorkerKindSchema = z.enum([
  'implementer',
  'reviewer',
  'validator',
  'fixer',
  'planner',
  'custom',
]);

// ============================================================
// Phase 2 field guard — explicit rejection
// ============================================================

const UNSUPPORTED_TOP_LEVEL_FIELDS = [
  'write_run_archive',
  'archive_root',
  'archive_run_label',
] as const;

const UNSUPPORTED_AGENT_FIELDS = [
  'workflow_prompt_mode',
  'workflow_context',
  'workflow_context_file',
  'stop_when',
  'resume_last',
  'session_id',
  'mode',
] as const;

function rejectUnsupportedFields(
  obj: Record<string, unknown>,
  fieldList: readonly string[],
  context: string,
): void {
  for (const field of fieldList) {
    if (field in obj && obj[field] !== undefined && obj[field] !== null) {
      // For booleans, only reject if true (false = disabled = OK)
      if (typeof obj[field] === 'boolean' && obj[field] === false) continue;
      throw new Error(
        `Field "${field}" in ${context} is not yet supported in TS launcher Phase 1`,
      );
    }
  }
}

// ============================================================
// DefaultsSpec schema
// ============================================================

const DefaultsSpecSchema = z.object({
  engine: EngineSchema.optional(),
  model: z.string().optional(),
  sandbox: SandboxSchema.optional(),
  reasoning_effort: ReasoningEffortSchema.optional(),
  json: z.boolean().optional(),
  output_schema: z.record(z.string(), z.unknown()).nullable().optional(),
  ephemeral: z.boolean().optional(),
  prompt_profile: z.enum(['full', 'compact']).optional(),
  response_style: z.enum(['standard', 'compact']).optional(),
  max_response_lines: z.number().optional(),
});

// ============================================================
// AgentSpec schema
// ============================================================

const AgentSpecSchema = z.object({
  // Required
  name: z.string().min(1),

  // Prompt (one of these)
  prompt: z.string().optional(),
  task: z.string().optional(),

  // Optional
  engine: EngineSchema.optional(),
  mode: z.enum(['exec', 'resume']).optional(),
  kind: WorkerKindSchema.optional(),
  stage: z.number().optional(),
  resume_last: z.boolean().optional(),
  session_id: z.string().nullable().optional(),
  cwd: z.string().optional(),
  role: z.string().optional(),
  mission: z.string().optional(),
  success_criteria: z.array(z.string()).optional(),
  coordination_notes: z.string().nullable().optional(),
  skills: z.array(z.string()).optional(),
  read_first: z.array(z.string()).optional(),
  writable_scope: z.array(z.string()).optional(),
  requirements: z.array(z.string()).optional(),
  validation: z.array(z.string()).optional(),
  return_contract: z.array(z.string()).optional(),
  required_paths: z.array(z.string()).optional(),
  required_non_empty_paths: z.array(z.string()).optional(),
  sandbox: SandboxSchema.optional(),
  model: z.string().optional(),
  reasoning_effort: ReasoningEffortSchema.optional(),
  json: z.boolean().optional(),
  output_schema: z.record(z.string(), z.unknown()).nullable().optional(),
  ephemeral: z.boolean().optional(),
  prompt_profile: z.enum(['full', 'compact']).optional(),
  response_style: z.enum(['standard', 'compact']).optional(),
  max_response_lines: z.number().optional(),
  output_last_message_file: z.string().optional(),
  extra_args: z.array(z.string()).optional(),

  // Phase 2 fields — parsed but rejected at runtime
  workflow_prompt_mode: z.enum(['prepend', 'replace', 'disabled']).optional(),
  workflow_context: z.record(z.string(), z.unknown()).optional(),
  workflow_context_file: z.string().nullable().optional(),
  stop_when: z.string().nullable().optional(),
});

// ============================================================
// Top-level LauncherSpec schema
// ============================================================

const LauncherSpecSchema = z.object({
  // Required
  cwd: z.string().min(1),
  agents: z.array(AgentSpecSchema).min(1),

  // Optional
  cwd_resolution: z.enum(['invocation', 'spec']).optional(),
  output_dir: z.string().optional(),
  manifest_file: z.string().optional(),
  debug_log_file: z.string().nullable().optional(),
  summary_file: z.string().optional(),
  archive_root: z.string().optional(),
  write_run_archive: z.boolean().optional(),
  archive_run_label: z.string().nullable().optional(),
  skip_git_repo_check: z.boolean().optional(),
  execution_mode: ExecutionModeSchema.optional(),
  timeout_seconds: z.number().optional(),
  write_prompt_files: z.boolean().optional(),
  write_summary_file: z.boolean().optional(),
  requested_deliverables: z.array(z.string()).optional(),
  supervisor_only: z.boolean().optional(),
  require_final_read_only_review: z.boolean().optional(),
  material_issue_strategy: z.enum(['none', 'fixer_then_rereview']).optional(),
  shared_directive_file: z.string().nullable().optional(),
  shared_directive_text: z.string().nullable().optional(),
  inject_shared_directive: z.boolean().optional(),
  shared_directive_mode: z
    .enum(['full', 'compact', 'reference', 'disabled'])
    .optional(),

  // Phase 2 fields — parsed but rejected at runtime
  workflow_file: z.string().nullable().optional(),
  workflow_auto_detect: z.boolean().optional(),
  workflow_prompt_mode: z.enum(['prepend', 'replace', 'disabled']).optional(),
  workflow_context: z.record(z.string(), z.unknown()).optional(),
  workflow_context_file: z.string().nullable().optional(),
  workflow_render_strict: z.boolean().optional(),
  hooks: z.any().optional(),
  live_usage: z.any().optional(),

  // Defaults
  defaults: DefaultsSpecSchema.optional(),
});

// ============================================================
// Public API
// ============================================================

/**
 * Parse and validate a spec JSON object.
 * Throws on invalid input or unsupported Phase 2 fields.
 */
export function parseSpec(json: unknown): LauncherSpec {
  // Step 1: Zod structural validation
  const parsed = LauncherSpecSchema.parse(json);

  // Step 2: Reject unsupported Phase 2 fields at top level
  const rawObj = json as Record<string, unknown>;
  rejectUnsupportedFields(rawObj, UNSUPPORTED_TOP_LEVEL_FIELDS, 'spec');

  // Step 3: Reject unsupported Phase 2 fields in each agent
  if (Array.isArray(rawObj.agents)) {
    for (const agent of rawObj.agents) {
      if (typeof agent === 'object' && agent !== null) {
        rejectUnsupportedFields(
          agent as Record<string, unknown>,
          UNSUPPORTED_AGENT_FIELDS,
          `agent "${(agent as Record<string, unknown>).name}"`,
        );
      }
    }
  }

  // execution_mode: both 'sequential' and 'parallel' are supported

  return parsed as LauncherSpec;
}

export { LauncherSpecSchema };
