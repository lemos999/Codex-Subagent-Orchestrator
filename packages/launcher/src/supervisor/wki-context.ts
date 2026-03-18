/**
 * WKI context injection — queries the Workspace Knowledge Index
 * and injects relevant context into worker prompts.
 *
 * This runs at prompt composition time, BEFORE the prompt is sent
 * to any engine. Therefore it works identically for Claude, Codex,
 * and Gemini workers.
 *
 * Flow:
 *   1. Worker task/prompt → extract search query
 *   2. WKI search → top-K relevant code/doc chunks
 *   3. Format as "## Relevant Context (auto-injected)" markdown
 *   4. Prepend to worker prompt
 */

import * as path from 'node:path';
import * as fsSync from 'node:fs';

// ============================================================
// Types
// ============================================================

export interface WkiContextConfig {
  enabled: boolean;
  knowledgeDir: string;       // .knowledge/ path
  projectId: string;
  topK?: number;              // default 5
  maxContentLines?: number;   // default 5
}

export interface WkiContextResult {
  injected: boolean;
  query: string;
  chunksFound: number;
  durationMs: number;
  markdown: string;
}

// ============================================================
// Detection
// ============================================================

/**
 * Auto-detect WKI configuration from workspace root.
 * Returns null if WKI is not set up.
 */
export function detectWkiConfig(workspaceRoot: string): WkiContextConfig | null {
  const knowledgeDir = path.resolve(workspaceRoot, '.knowledge');

  if (!fsSync.existsSync(knowledgeDir)) return null;

  // Check if FTS database exists (minimum viable index)
  const ftsFiles = fsSync.readdirSync(knowledgeDir).filter(
    (f) => f.endsWith('.db') || f === 'fts.db',
  );
  if (ftsFiles.length === 0) {
    // Check subdirectories for project-specific DBs
    const subdirs = fsSync.readdirSync(knowledgeDir).filter((f) => {
      const full = path.join(knowledgeDir, f);
      return fsSync.statSync(full).isDirectory();
    });
    const hasDb = subdirs.some((d) => {
      const dbPath = path.join(knowledgeDir, d, 'fts.db');
      return fsSync.existsSync(dbPath);
    });
    if (!hasDb) return null;
  }

  // Load project ID from wki.config.json
  let projectId = 'my-project';
  const configPath = path.resolve(workspaceRoot, 'wki.config.json');
  if (fsSync.existsSync(configPath)) {
    try {
      const config = JSON.parse(fsSync.readFileSync(configPath, 'utf8'));
      if (config.projects?.[0]?.name) {
        projectId = config.projects[0].name;
      }
    } catch { /* use default */ }
  }

  return {
    enabled: true,
    knowledgeDir,
    projectId,
    topK: 5,
    maxContentLines: 5,
  };
}

// ============================================================
// Context generation
// ============================================================

/**
 * Generate context for a worker prompt by searching WKI.
 * Uses dynamic import to avoid hard dependency on WKI package.
 */
export async function generateContext(
  query: string,
  config: WkiContextConfig,
): Promise<WkiContextResult> {
  const emptyResult: WkiContextResult = {
    injected: false,
    query,
    chunksFound: 0,
    durationMs: 0,
    markdown: '',
  };

  if (!config.enabled) return emptyResult;

  try {
    // Dynamic import of WKI modules — avoids hard coupling
    const wkiDistPath = path.resolve(
      config.knowledgeDir,
      '..',
      'workspace-knowledge-index',
      'dist',
    );

    // Try to import sub-hook (the cleanest interface)
    const subHookPath = path.join(wkiDistPath, 'context', 'sub-hook.js');
    if (!fsSync.existsSync(subHookPath)) {
      // WKI dist not found — skip silently
      return emptyResult;
    }

    // Dynamic import — no compile-time type dependency on WKI
    const subHookModule = await import(
      /* webpackIgnore: true */ `file://${subHookPath.replace(/\\/g, '/')}`
    ) as { generateAgentContext: (query: string, cfg: unknown) => Promise<{ markdown: string; chunks: unknown[]; durationMs: number }> };

    // Load WKI config
    const configPath = path.resolve(config.knowledgeDir, '..', 'wki.config.json');
    let wkiConfig: Record<string, unknown> = {};
    if (fsSync.existsSync(configPath)) {
      wkiConfig = JSON.parse(fsSync.readFileSync(configPath, 'utf8'));
    }

    // Resolve FTS DB path — replace {project} placeholder
    const searchCfg = (wkiConfig['search'] ?? { fts_db: '.knowledge/{project}/fts.db', fusion: { strategy: 'weighted_sum', weights: { fts: 0.4, vector: 0.6 } } }) as Record<string, unknown>;
    const ftsDbTemplate = (searchCfg['fts_db'] as string) ?? '.knowledge/{project}/fts.db';
    const ftsDbResolved = ftsDbTemplate.replace('{project}', config.projectId);
    const ftsDbPath = path.resolve(config.knowledgeDir, '..', ftsDbResolved);

    const contextBlock = await subHookModule.generateAgentContext(query, {
      knowledgeDir: config.knowledgeDir,
      projectId: config.projectId,
      ftsDbPath,
      embeddingConfig: wkiConfig['embedding'] ?? { provider: 'local' },
      storageConfig: wkiConfig['storage'] ?? { index_root: '.knowledge', vector_backend: 'lancedb' },
      searchConfig: searchCfg,
      contextOptions: {
        topK: config.topK ?? 5,
        maxContentLines: config.maxContentLines ?? 5,
      },
    });

    return {
      injected: contextBlock.chunks.length > 0,
      query,
      chunksFound: contextBlock.chunks.length,
      durationMs: contextBlock.durationMs,
      markdown: contextBlock.markdown,
    };
  } catch (err) {
    // WKI not available or search failed — degrade gracefully
    const msg = err instanceof Error ? err.message : String(err);
    process.stderr.write(`[wki] Context injection skipped: ${msg}\n`);
    return emptyResult;
  }
}

/**
 * Inject WKI context into a worker prompt.
 * Prepends the context markdown before the worker's task.
 */
export function injectContextIntoPrompt(
  prompt: string,
  context: WkiContextResult,
): string {
  if (!context.injected || !context.markdown) return prompt;
  return `${context.markdown}\n\n${prompt}`;
}
