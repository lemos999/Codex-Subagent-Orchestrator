/**
 * C4: AgentRegistry — loads reusable agent definitions from YAML files.
 * Directory-based: config/agents/{id}.yaml
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import yaml from 'js-yaml';
import type { AgentDefinition } from './types.js';

const AGENTS_DIR = 'config/agents';

/**
 * Load an agent definition by ID from the registry directory.
 * Throws on missing file or invalid YAML — no silent fallback.
 */
export function loadAgentDefinition(agentId: string, workspaceRoot: string): AgentDefinition {
  const agentsDir = path.resolve(workspaceRoot, AGENTS_DIR);
  const filePath = path.join(agentsDir, `${agentId}.yaml`);

  if (!fs.existsSync(filePath)) {
    throw new Error(
      `Agent '${agentId}' not found in ${AGENTS_DIR}/. Expected: ${filePath}`,
    );
  }

  const raw = fs.readFileSync(filePath, 'utf8');

  let parsed: Record<string, unknown>;
  try {
    parsed = yaml.load(raw) as Record<string, unknown>;
  } catch (err) {
    throw new Error(
      `Failed to parse agent file ${filePath}: ${err instanceof Error ? err.message : String(err)}`,
    );
  }

  if (!parsed || typeof parsed !== 'object') {
    throw new Error(`Agent file ${filePath} does not contain a valid YAML object`);
  }

  return validateAgentDefinition(parsed, filePath);
}

/**
 * List all available agent IDs in the registry.
 */
export function listAgentIds(workspaceRoot: string): string[] {
  const agentsDir = path.resolve(workspaceRoot, AGENTS_DIR);

  if (!fs.existsSync(agentsDir)) {
    return [];
  }

  return fs.readdirSync(agentsDir)
    .filter((f) => f.endsWith('.yaml') || f.endsWith('.yml'))
    .map((f) => path.basename(f, path.extname(f)));
}

// ============================================================
// Validation
// ============================================================

function validateAgentDefinition(
  raw: Record<string, unknown>,
  filePath: string,
): AgentDefinition {
  const required = ['id', 'version', 'name', 'engine', 'model', 'system'] as const;

  for (const field of required) {
    if (raw[field] == null) {
      throw new Error(`Agent file ${filePath} is missing required field '${field}'`);
    }
  }

  const version = Number(raw['version']);
  if (!Number.isInteger(version) || version < 1) {
    throw new Error(`Agent file ${filePath}: 'version' must be a positive integer, got '${raw['version']}'`);
  }

  const definition: AgentDefinition = {
    id: String(raw['id']),
    version,
    name: String(raw['name']),
    engine: String(raw['engine']) as AgentDefinition['engine'],
    model: String(raw['model']),
    system: String(raw['system']),
  };

  if (raw['defaults'] && typeof raw['defaults'] === 'object') {
    const d = raw['defaults'] as Record<string, unknown>;
    definition.defaults = {};
    if (d['sandbox']) definition.defaults.sandbox = String(d['sandbox']) as 'workspace-write' | 'read-only';
    if (d['kind']) definition.defaults.kind = String(d['kind']);
    if (d['reasoning_effort']) definition.defaults.reasoning_effort = String(d['reasoning_effort']) as 'low' | 'medium' | 'high';
    if (d['extra_args'] && Array.isArray(d['extra_args'])) {
      definition.defaults.extra_args = d['extra_args'].map(String);
    }
  }

  if (raw['metadata'] && typeof raw['metadata'] === 'object') {
    definition.metadata = raw['metadata'] as Record<string, unknown>;
  }

  return definition;
}
