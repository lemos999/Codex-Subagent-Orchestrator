/**
 * WKI context injection — queries the Workspace Knowledge Index
 * and injects relevant context into worker prompts.
 *
 * This runs at prompt composition time, BEFORE the prompt is sent
 * to any engine. Therefore it works identically for Claude, Codex,
 * and Gemini workers.
 *
 * Flow:
 *   0. Auto incremental indexing (if stale)
 *   1. Worker task/prompt → extract search query
 *   2. WKI search → top-K relevant code/doc chunks
 *   3. Format as "## Relevant Context (auto-injected)" markdown
 *   4. Prepend to worker prompt
 */

import { execFileSync } from 'node:child_process';
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
  minScore?: number;          // minimum relevance score to include (default 0.3)
  /** Restrict context to chunks from these file paths (scope-aware injection for sub-agents). */
  filePaths?: string[];
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
// Query expansion for multilingual search
// ============================================================

/**
 * Domain-specific Korean→English keyword map.
 * Helps bridge the gap when documents are in English but queries are in Korean.
 */
const KO_EN_KEYWORDS: Record<string, string[]> = {
  '증거': ['evidence'],
  '기록': ['recording', 'log', 'manifest'],
  '규칙': ['rules', 'policy'],
  '워커': ['worker', 'agent'],
  '실행': ['execution', 'run', 'launch'],
  '검증': ['validation', 'review', 'verify'],
  '오케스트레이션': ['orchestration', 'orchestrator'],
  '파일': ['file', 'path'],
  '디렉터리': ['directory', 'folder'],
  '구조': ['structure', 'architecture'],
  '설정': ['config', 'settings'],
  '스펙': ['spec', 'specification'],
  '매니페스트': ['manifest'],
  '프롬프트': ['prompt', 'contract'],
  '에이전트': ['agent', 'worker'],
  '리뷰': ['review', 'reviewer'],
  '수정': ['fix', 'fixer', 'repair'],
  '계획': ['plan', 'planner'],
  '단계': ['stage', 'phase'],
  '엔진': ['engine', 'codex', 'claude', 'gemini'],
  '런처': ['launcher'],
  '아카이브': ['archive'],
  '인덱스': ['index', 'indexing'],
  '검색': ['search', 'query'],
  '맥락': ['context'],
  '임베딩': ['embedding'],
  '토큰': ['token'],
  '배치': ['batch'],
};

/**
 * Expand a query by appending English keywords for Korean terms.
 * Returns the original query + English expansion.
 */
function expandQuery(query: string): string {
  const hasKorean = /[\uAC00-\uD7AF]/.test(query);
  if (!hasKorean) return query;

  const englishTerms: string[] = [];
  for (const [ko, enList] of Object.entries(KO_EN_KEYWORDS)) {
    if (query.includes(ko)) {
      englishTerms.push(...enList);
    }
  }

  if (englishTerms.length === 0) return query;

  return `${query} ${englishTerms.join(' ')}`;
}

// ============================================================
// Auto incremental indexing
// ============================================================

/**
 * Run incremental indexing if the index is stale.
 * Uses the WKI CLI (wki index) which checks freshness.lock internally
 * and only re-indexes changed files.
 *
 * This is called once per launcher invocation, before any search.
 * If WKI CLI is not available or indexing fails, it degrades gracefully.
 */
export function ensureIndexFresh(config: WkiContextConfig): void {
  if (!config.enabled) return;

  const wkiCliPath = path.resolve(
    config.knowledgeDir,
    '..',
    'workspace-knowledge-index',
    'dist',
    'index.js',
  );

  if (!fsSync.existsSync(wkiCliPath)) return;

  const workspaceRoot = path.resolve(config.knowledgeDir, '..');

  const lockPath = path.resolve(config.knowledgeDir, '.wki.lock');

  try {
    // Run incremental index — checks freshness.lock internally
    // If no changes: prints "Index is up to date" and returns instantly (no model loading)
    // If changes: loads model, re-embeds changed files only
    const result = execFileSync('node', [wkiCliPath, 'index'], {
      cwd: workspaceRoot,
      stdio: 'pipe',
      timeout: 300000, // 5 minutes max for model load + embedding
    });
    const output = result.toString().trim();
    if (output && !output.includes('up to date')) {
      process.stderr.write(`[wki] ${output}\n`);
    }
  } catch (err) {
    // Clean up stale lock if timeout killed the child process
    if (fsSync.existsSync(lockPath)) {
      try {
        const lockData = JSON.parse(fsSync.readFileSync(lockPath, 'utf8'));
        // Check if the PID is still alive
        try { process.kill(lockData.pid, 0); } catch {
          // PID is dead — remove stale lock
          fsSync.unlinkSync(lockPath);
          process.stderr.write('[wki] Cleaned up stale lock from timed-out indexing.\n');
        }
      } catch { /* ignore lock parse errors */ }
    }

    const msg = err instanceof Error ? err.message : String(err);
    if (!msg.includes('ETIMEDOUT')) {
      process.stderr.write(`[wki] Auto-indexing skipped: ${msg}\n`);
    }
  }
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

    // Resolve LanceDB path — same pattern as FTS to avoid .knowledge/.knowledge nesting
    const storageCfg = (wkiConfig['storage'] ?? { index_root: '.knowledge', vector_backend: 'lancedb' }) as Record<string, unknown>;
    const lanceCfg = (storageCfg['lancedb'] ?? {}) as Record<string, unknown>;
    const lanceTemplate = (lanceCfg['path'] as string) ?? 'vectors.lance';
    const lanceResolved = lanceTemplate.replace('{project}', config.projectId);
    const lanceDbPath = path.resolve(config.knowledgeDir, '..', lanceResolved);

    // Expand Korean queries with English keywords for better cross-lingual search
    const expandedQuery = expandQuery(query);

    const contextBlock = await subHookModule.generateAgentContext(expandedQuery, {
      knowledgeDir: config.knowledgeDir,
      projectId: config.projectId,
      ftsDbPath,
      lanceDbPath,
      embeddingConfig: wkiConfig['embedding'] ?? { provider: 'local' },
      storageConfig: storageCfg,
      searchConfig: searchCfg,
      contextOptions: {
        topK: config.topK ?? 5,
        maxContentLines: config.maxContentLines ?? 5,
      },
      filePaths: config.filePaths,
    });

    // Filter low-score results to prevent irrelevant context injection
    // (especially important for non-English queries with English-only embedding model)
    const minScore = config.minScore ?? 0.3;
    type ChunkResult = { score?: number; chunk: { filePath: string; startLine: number; endLine: number; chunkType: string; heading?: string; content: string } };
    const allChunks = contextBlock.chunks as ChunkResult[];
    const relevantChunks = allChunks.filter(
      (c) => (c.score ?? 0) >= minScore,
    );

    if (relevantChunks.length === 0) {
      return emptyResult;
    }

    // Rebuild markdown with only relevant chunks
    const filteredMarkdown = relevantChunks.length === allChunks.length
      ? contextBlock.markdown
      : buildFilteredMarkdown(relevantChunks);

    return {
      injected: filteredMarkdown.length > 0,
      query,
      chunksFound: relevantChunks.length,
      durationMs: contextBlock.durationMs,
      markdown: filteredMarkdown,
    };
  } catch (err) {
    // WKI not available or search failed — degrade gracefully
    const msg = err instanceof Error ? err.message : String(err);
    process.stderr.write(`[wki] Context injection skipped: ${msg}\n`);
    return emptyResult;
  }
}

/**
 * Rebuild context markdown from filtered chunks.
 */
function buildFilteredMarkdown(
  chunks: Array<{ score?: number; chunk: { filePath: string; startLine: number; endLine: number; chunkType: string; heading?: string; content: string } }>,
): string {
  if (chunks.length === 0) return '';

  const sections: string[] = ['## Relevant Context (auto-injected)\n'];
  for (const { chunk } of chunks) {
    const lineRange = `lines ${chunk.startLine}-${chunk.endLine}`;
    const heading = chunk.heading ?? chunk.chunkType;
    sections.push(`### ${chunk.filePath} (${lineRange})`);
    sections.push(`**${heading}** — ${chunk.chunkType}`);

    const lines = chunk.content.split('\n').slice(0, 5);
    if (chunk.chunkType === 'markdown-section') {
      sections.push(lines.map((l: string) => `> ${l}`).join('\n'));
    } else {
      sections.push(`\`\`\`\n${lines.join('\n')}\n\`\`\``);
    }
    sections.push('');
  }
  return sections.join('\n');
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
