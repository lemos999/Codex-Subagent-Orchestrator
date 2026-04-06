import path from 'node:path';
import type { EmbeddingConfig, StorageConfig, SearchConfig } from '../config/schema.js';
import type { EmbeddingProvider } from '../interfaces/embedding.js';
import { FreshnessManager, type ChangedFiles } from '../core/freshness.js';
import { IndexLock } from '../core/index-lock.js';
import { FtsStore } from '../store/fts-store.js';
import { ChunkStore } from '../store/chunk-store.js';
import { LanceVectorStore } from '../store/vector-store.js';
import { SearchService } from '../search/search-service.js';
import { buildContextBlock, type ContextBlock, type ContextBlockOptions } from './context-builder.js';

// ============================================================
// Sub-Agent Hook
// ============================================================

export interface SubHookConfig {
  knowledgeDir: string;      // path to .knowledge/
  projectId: string;
  ftsDbPath?: string;        // resolved FTS DB path (from resolveFtsDbPath). Falls back to knowledgeDir/fts.db
  embeddingConfig: EmbeddingConfig;
  storageConfig: StorageConfig;
  searchConfig: SearchConfig;
  contextOptions?: ContextBlockOptions;
  /** Restrict context to chunks from these file paths (scope-aware injection). */
  filePaths?: string[];
}

/**
 * Generate a context block for a sub-agent task description.
 * Called by the orchestrator before spawning a worker.
 */
export async function generateAgentContext(
  taskDescription: string,
  config: SubHookConfig,
): Promise<ContextBlock> {
  // Read-only operation — no lock needed, but warn if index is being written
  const lock = new IndexLock(config.knowledgeDir);
  if (lock.isLocked()) {
    const info = lock.getLockInfo();
    if (info) {
      console.warn(
        `[wki] Warning: index may be stale — a write operation is in progress ` +
        `(PID ${info.pid}, operation: ${info.operation}, started ${info.timestamp}).`,
      );
    }
  }

  const ftsDbPath = config.ftsDbPath ?? path.join(config.knowledgeDir, 'fts.db');
  const ftsStore = new FtsStore(ftsDbPath, { readonly: true });
  const chunkStore = new ChunkStore(ftsStore.getDatabase());

  let vectorStore: LanceVectorStore | null = null;
  let embeddingProvider: EmbeddingProvider | null = null;

  if (config.storageConfig.vector_backend !== 'none') {
    try {
      const { createEmbeddingProvider } = await import('../embedding/factory.js');
      embeddingProvider = await createEmbeddingProvider(config.embeddingConfig, 'search');
    } catch {
      console.warn('[wki] No embedding provider available. Using FTS-only mode.');
    }

    if (embeddingProvider && config.storageConfig.vector_backend === 'lancedb') {
      const dims = embeddingProvider.dimensions;
      const lanceDbPath = config.storageConfig.lancedb?.path
        ? path.resolve(
            config.knowledgeDir,
            config.storageConfig.lancedb.path.replace('{project}', config.projectId),
          )
        : path.join(config.knowledgeDir, 'vectors.lance');

      try {
        vectorStore = new LanceVectorStore(lanceDbPath, dims);
        await vectorStore.init();
      } catch {
        vectorStore = null;
      }
    }
  }

  const symbolsIdxPath = path.join(config.knowledgeDir, 'symbols.idx');
  const depsGraphPath = path.join(config.knowledgeDir, 'deps.graph');
  const searchService = new SearchService(
    ftsStore,
    vectorStore,
    chunkStore,
    embeddingProvider,
    config.searchConfig,
    symbolsIdxPath,
    depsGraphPath,
  );

  try {
    return await buildContextBlock(searchService, taskDescription, config.contextOptions, config.filePaths);
  } finally {
    if (vectorStore) {
      await vectorStore.close();
    }
    await ftsStore.close().catch(() => {});
  }
}

/**
 * Inject context block into an agent prompt/contract.
 * Appends the context markdown before the first "## " heading or at the end.
 */
export function injectContext(prompt: string, contextBlock: ContextBlock): string {
  // Don't inject empty context
  if (contextBlock.chunks.length === 0) {
    return prompt;
  }

  const contextMarkdown = contextBlock.markdown;

  // Find the first "## " heading (also check start of prompt)
  if (prompt.startsWith('## ')) {
    return `${contextMarkdown}\n${prompt}`;
  }

  const headingIndex = prompt.indexOf('\n## ');
  if (headingIndex !== -1) {
    const before = prompt.slice(0, headingIndex);
    const after = prompt.slice(headingIndex);
    return `${before}\n\n${contextMarkdown}${after}`;
  }

  // No headings found -- append at the end
  return `${prompt}\n\n${contextMarkdown}`;
}

// ============================================================
// Refresh API (Rule #6: Context Decay Awareness)
// ============================================================

export interface RefreshResult {
  /** Whether refresh context was generated (false if index is fresh). */
  refreshed: boolean;
  /** Files that changed since last indexing. */
  changedFiles: ChangedFiles;
  /** Context block scoped to changed files (if any). */
  contextBlock?: ContextBlock;
}

/**
 * Generate refreshed context for changed files only.
 * Call this mid-conversation to re-inject context for files that changed
 * since the last indexing. Supports Rule #6 (Context Decay Awareness).
 *
 * @param taskDescription - Current task context for search relevance
 * @param config - Same SubHookConfig used for initial context
 * @returns RefreshResult with changed files and optional scoped context
 */
export async function refreshContext(
  taskDescription: string,
  config: SubHookConfig,
): Promise<RefreshResult> {
  const freshnessPath = path.join(config.knowledgeDir, 'freshness.lock');
  const freshness = new FreshnessManager();
  const prevState = freshness.load(freshnessPath);

  if (!prevState) {
    return { refreshed: false, changedFiles: { added: [], modified: [], deleted: [], renamed: [] } };
  }

  // Detect what changed
  const projectRoot = path.resolve(config.knowledgeDir, '..');
  const changedFiles = freshness.detectChanges(prevState, projectRoot);
  const totalChanges =
    changedFiles.added.length +
    changedFiles.modified.length +
    changedFiles.deleted.length +
    changedFiles.renamed.length;

  if (totalChanges === 0) {
    return { refreshed: false, changedFiles };
  }

  // Collect changed file paths for scoped context injection
  const scopedPaths = [
    ...changedFiles.added,
    ...changedFiles.modified,
    ...changedFiles.renamed.map(r => r.to),
  ];

  // Generate context scoped to changed files
  const scopedConfig: SubHookConfig = {
    ...config,
    filePaths: scopedPaths,
  };

  const contextBlock = await generateAgentContext(taskDescription, scopedConfig);

  return {
    refreshed: contextBlock.chunks.length > 0,
    changedFiles,
    contextBlock,
  };
}

export type { ContextBlock, ContextBlockOptions } from './context-builder.js';
