/**
 * Workflow template renderer — processes WORKFLOW.md-style templates.
 *
 * Supports:
 * - Auto-detection of WORKFLOW.md in workspace root
 * - {{variable}} template substitution from workflow_context
 * - Strict mode: fails on missing variables
 * - Prompt modes: prepend (before worker prompt) or replace (entire prompt)
 */

import * as fs from 'node:fs/promises';
import * as fsSync from 'node:fs';
import * as path from 'node:path';

import type { LauncherSpec, AgentSpec } from '../types/spec.js';
import { sha256 as computeSha256 } from '../common/fs-helpers.js';

export interface WorkflowInfo {
  enabled: boolean;
  source: string | null;
  promptMode: string;
  strictRender: boolean;
  autoDetected: boolean;
  templateText: string | null;
  templateSha256: string | null;
  templateChars: number;
  context: Record<string, unknown>;
}

/**
 * Load and resolve workflow template configuration.
 */
export async function loadWorkflow(
  spec: LauncherSpec,
  workspaceRoot: string,
  specDirectory?: string,
): Promise<WorkflowInfo> {
  const mode = spec.workflow_prompt_mode ?? 'disabled';

  if (mode === 'disabled') {
    return {
      enabled: false,
      source: null,
      promptMode: 'disabled',
      strictRender: spec.workflow_render_strict ?? true,
      autoDetected: false,
      templateText: null,
      templateSha256: null,
      templateChars: 0,
      context: {},
    };
  }

  // Determine template source
  let source: string | null = spec.workflow_file ?? null;
  let autoDetected = false;

  if (!source && (spec.workflow_auto_detect !== false)) {
    // Auto-detect WORKFLOW.md in workspace root
    const candidate = path.resolve(workspaceRoot, 'WORKFLOW.md');
    if (fsSync.existsSync(candidate)) {
      source = candidate;
      autoDetected = true;
    }
  }

  if (source && !path.isAbsolute(source)) {
    // PS resolves workflow_file relative to specDirectory, not workspaceRoot
    source = path.resolve(specDirectory ?? workspaceRoot, source);
  }

  let templateText: string | null = null;
  if (source && fsSync.existsSync(source)) {
    templateText = await fs.readFile(source, 'utf8');
  }

  // Merge context: top-level + context file
  let context: Record<string, unknown> = { ...(spec.workflow_context ?? {}) };
  if (spec.workflow_context_file) {
    // PS resolves workflow_context_file relative to specDirectory
    const ctxPath = path.resolve(specDirectory ?? workspaceRoot, spec.workflow_context_file);
    if (fsSync.existsSync(ctxPath)) {
      const ctxJson = await fs.readFile(ctxPath, 'utf8');
      const parsed = JSON.parse(ctxJson) as Record<string, unknown>;
      context = { ...context, ...parsed };
    }
  }

  // Compute SHA256
  const templateSha256 = templateText ? computeSha256(templateText) : null;

  return {
    enabled: templateText !== null,
    source,
    promptMode: mode,
    strictRender: spec.workflow_render_strict ?? true,
    autoDetected,
    templateText,
    templateSha256,
    templateChars: templateText?.length ?? 0,
    context,
  };
}

/**
 * Render workflow template with context variables.
 * {{variable}} patterns are replaced with context values.
 */
export function renderTemplate(
  template: string,
  context: Record<string, unknown>,
  strict: boolean,
): string {
  return template.replace(/\{\{(\w+(?:\.\w+)*)\}\}/g, (_match, key: string) => {
    const value = resolveNestedKey(context, key);
    if (value === undefined) {
      if (strict) {
        throw new Error(`Workflow template variable "{{${key}}}" not found in context`);
      }
      return `{{${key}}}`;
    }
    return String(value);
  });
}

function resolveNestedKey(obj: Record<string, unknown>, key: string): unknown {
  const parts = key.split('.');
  let current: unknown = obj;
  for (const part of parts) {
    if (current === null || current === undefined || typeof current !== 'object') {
      return undefined;
    }
    current = (current as Record<string, unknown>)[part];
  }
  return current;
}

/**
 * Apply workflow to a worker prompt.
 * Returns the modified prompt text.
 */
export function applyWorkflow(
  workerPrompt: string,
  workflow: WorkflowInfo,
  agentContext: Record<string, unknown>,
  agentSpec: AgentSpec,
): string {
  if (!workflow.enabled || !workflow.templateText) return workerPrompt;

  // Agent-level override
  const mode = agentSpec.workflow_prompt_mode ?? workflow.promptMode;
  if (mode === 'disabled') return workerPrompt;

  // Merge agent-level context
  const fullContext = {
    ...workflow.context,
    ...agentContext,
    agent: { name: agentSpec.name, stage: agentSpec.stage ?? 1, kind: agentSpec.kind ?? 'custom' },
    run: { worker_name: agentSpec.name },
  };

  const rendered = renderTemplate(
    workflow.templateText,
    fullContext,
    workflow.strictRender,
  );

  switch (mode) {
    case 'prepend':
      return `${rendered}\n\n${workerPrompt}`;
    case 'replace':
      return rendered;
    default:
      return workerPrompt;
  }
}
