/**
 * MCP Server for Workspace Knowledge Index.
 * Exposes knowledge_search and knowledge_status tools via the Model Context Protocol.
 * Read-only: never modifies the index data.
 */

import fs from 'node:fs';
import path from 'node:path';
import { z } from 'zod';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { loadConfig, resolveFtsDbPath } from '../config/schema.js';
import { FreshnessManager } from '../core/freshness.js';
import { IndexLock } from '../core/index-lock.js';
import { SearchService } from '../search/search-service.js';
import { SymbolSearch } from '../search/symbol-search.js';
import { ChunkStore } from '../store/chunk-store.js';
import { FtsStore } from '../store/fts-store.js';
import type { SymbolSearchOptions, SymbolSearchResult } from '../types/index.js';

export interface ChunkMapParams {
  file_path: string;
}

export interface ChunkMapEntry {
  filePath: string;
  ordinal: number;
  heading: string | null;
  chunkType: string;
  startLine: number;
  endLine: number;
  tokenCount: number;
}

export interface ChunkMapResponse {
  chunks: ChunkMapEntry[];
}

// ============================================================
// Types
// ============================================================

export interface SearchParams {
  query: string;
  project_id?: string;
  file_type?: string;
  top_k?: number;
  mode?: 'auto' | 'fts' | 'vector' | 'hybrid';
}

export interface SearchResponseItem {
  filePath: string;
  startLine: number;
  endLine: number;
  chunkType: string;
  score: number;
  matchType: string;
  content: string;
  heading?: string;
}

export interface SearchResponse {
  results: SearchResponseItem[];
  warning?: string;
}

export interface SymbolSearchParams {
  name?: string;
  name_mode?: 'exact' | 'prefix' | 'contains' | 'regex';
  kind?: string;
  file_path?: string;
  exported_only?: boolean;
  top_k?: number;
}

export interface SymbolSearchResponseItem {
  name: string;
  kind: string;
  filePath: string;
  startLine: number;
  endLine: number;
  exported: boolean;
  signature?: string;
  score: number;
}

export interface SymbolSearchResponse {
  results: SymbolSearchResponseItem[];
}

export interface StatusParams {
  project_id?: string;
}

export interface StatusResponse {
  health: string;
  filesCount: number;
  chunksCount: number;
  symbolsCount: number;
  vectorStatus: string;
  lastIndexed: string;
  dirty: boolean;
  locked: boolean;
  lockInfo?: { pid: number; operation: string; timestamp: string };
}

// ============================================================
// Handler functions (exported for testing)
// ============================================================

export async function handleKnowledgeSearch(
  params: SearchParams,
  projectRoot: string,
): Promise<SearchResponse> {
  const query = (params.query ?? '').trim();
  if (!query) {
    return { results: [] };
  }

  const config = loadConfig(projectRoot);
  const indexRoot = config.storage.index_root;
  const knowledgeDir = path.resolve(projectRoot, indexRoot);

  const projectId =
    params.project_id?.trim() ||
    (config.projects.length > 0 ? config.projects[0].name : path.basename(projectRoot));

  const ftsDbPath = resolveFtsDbPath(config, knowledgeDir, projectId);
  const ftsStore = new FtsStore(ftsDbPath, { readonly: true });
  const chunkStore = new ChunkStore(ftsStore.getDatabase());

  try {
    const searchService = new SearchService(
      ftsStore,
      null, // vector store -- MCP server is lightweight, FTS only
      chunkStore,
      null, // embedding provider
      config.search,
    );

    const topK = params.top_k ?? 10;
    const requestedMode = params.mode ?? 'auto';

    // Currently FTS-only (no embedding provider in MCP server).
    // Vector/hybrid modes gracefully degrade to FTS.
    const effectiveMode: 'fts' = 'fts';

    const results = await searchService.search(query, {
      topK,
      mode: effectiveMode,
      filter: {
        projectId: params.project_id?.trim() || undefined,
        fileType: params.file_type?.trim() || undefined,
      },
      includeContent: true,
    });

    const searchResults = results.map((r) => ({
      filePath: r.chunk.filePath,
      startLine: r.chunk.startLine,
      endLine: r.chunk.endLine,
      chunkType: r.chunk.chunkType,
      score: r.score,
      matchType: r.matchType,
      content: r.chunk.content,
      heading: r.chunk.heading,
    }));

    const response: SearchResponse = { results: searchResults };
    if (requestedMode !== 'fts' && requestedMode !== 'auto') {
      response.warning = `Requested mode '${requestedMode}' downgraded to 'fts' (no embedding provider configured in MCP server)`;
    }

    return response;
  } finally {
    await ftsStore.close();
  }
}

export function handleSymbolSearch(
  params: SymbolSearchParams,
  projectRoot: string,
): SymbolSearchResponse {
  const config = loadConfig(projectRoot);
  const knowledgeDir = path.resolve(projectRoot, config.storage.index_root);
  const symbolsPath = path.join(knowledgeDir, 'symbols.idx');

  const symbolSearch = new SymbolSearch(symbolsPath);

  const options: SymbolSearchOptions = {
    name: params.name?.trim() || undefined,
    nameMode: params.name_mode ?? 'contains',
    kind: params.kind?.trim() || undefined,
    exportedOnly: params.exported_only ?? false,
    filePath: params.file_path?.trim() || undefined,
    topK: params.top_k ?? 20,
  };

  const results = symbolSearch.search(options);

  return {
    results: results.map((r: SymbolSearchResult) => ({
      name: r.symbol.name,
      kind: r.symbol.kind,
      filePath: r.symbol.filePath,
      startLine: r.symbol.startLine,
      endLine: r.symbol.endLine,
      exported: r.symbol.exported,
      signature: r.symbol.signature,
      score: r.score,
    })),
  };
}

export function handleChunkMap(
  params: ChunkMapParams,
  projectRoot: string,
): ChunkMapResponse {
  const config = loadConfig(projectRoot);
  const knowledgeDir = path.resolve(projectRoot, config.storage.index_root);
  const projectId = config.projects.length > 0 ? config.projects[0].name : path.basename(projectRoot);
  const ftsDbPath = resolveFtsDbPath(config, knowledgeDir, projectId);

  const ftsStore = new FtsStore(ftsDbPath, { readonly: true });
  const chunkStore = new ChunkStore(ftsStore.getDatabase());

  try {
    const results = chunkStore.getChunkMapByPathLike(params.file_path.trim());
    return { chunks: results };
  } finally {
    ftsStore.close().catch(() => {});
  }
}

export async function handleKnowledgeStatus(
  params: StatusParams,
  projectRoot: string,
): Promise<StatusResponse> {
  const config = loadConfig(projectRoot);
  const indexRoot = config.storage.index_root;
  const knowledgeDir = path.resolve(projectRoot, indexRoot);

  const projectId =
    params.project_id?.trim() ||
    (config.projects.length > 0 ? config.projects[0].name : path.basename(projectRoot));

  // file-map.json
  const fileMapPath = path.join(knowledgeDir, 'file-map.json');
  let filesCount = 0;
  if (fs.existsSync(fileMapPath)) {
    try {
      const data = JSON.parse(fs.readFileSync(fileMapPath, 'utf-8')) as Record<string, unknown>;
      filesCount = Object.keys(data).length;
    } catch {
      /* ignore */
    }
  }

  // fts.db: chunk count
  const ftsDbPath = resolveFtsDbPath(config, knowledgeDir, projectId);
  let chunksCount = 0;
  if (fs.existsSync(ftsDbPath)) {
    try {
      const ftsStore = new FtsStore(ftsDbPath, { readonly: true });
      const chunkStore = new ChunkStore(ftsStore.getDatabase());
      chunksCount = chunkStore.count();
      await ftsStore.close();
    } catch {
      /* ignore */
    }
  }

  // symbols.idx
  const symbolsPath = path.join(knowledgeDir, 'symbols.idx');
  let symbolsCount = 0;
  if (fs.existsSync(symbolsPath)) {
    try {
      const content = fs.readFileSync(symbolsPath, 'utf-8');
      symbolsCount = content
        .split('\n')
        .filter((line) => line.trim().length > 0).length;
    } catch {
      /* ignore */
    }
  }

  // vector status
  let vectorStatus = 'none';
  if (config.storage.vector_backend === 'lancedb') {
    const lanceDbPath = config.storage.lancedb?.path
      ? path.resolve(
          knowledgeDir,
          config.storage.lancedb.path.replace('{project}', projectId),
        )
      : path.join(knowledgeDir, 'vectors.lance');
    vectorStatus = fs.existsSync(lanceDbPath) ? 'present' : 'not created';
  }

  // freshness.lock
  const freshnessPath = path.join(knowledgeDir, 'freshness.lock');
  let lastIndexed = 'never';
  let dirty = false;
  if (fs.existsSync(freshnessPath)) {
    try {
      const freshData = JSON.parse(
        fs.readFileSync(freshnessPath, 'utf-8'),
      ) as Record<string, unknown>;
      lastIndexed = (freshData['indexed_at'] as string) ?? 'unknown';
      dirty = (freshData['dirty'] as boolean) ?? false;
    } catch {
      /* ignore */
    }
  }

  // lock status
  const lock = new IndexLock(knowledgeDir);
  const locked = lock.isLocked();
  const lockInfoRaw = lock.getLockInfo();
  const lockInfo = lockInfoRaw
    ? { pid: lockInfoRaw.pid, operation: lockInfoRaw.operation, timestamp: lockInfoRaw.timestamp }
    : undefined;

  // health
  let health = 'healthy';
  if (!fs.existsSync(knowledgeDir)) {
    health = 'not_initialized';
  } else if (!fs.existsSync(ftsDbPath)) {
    health = 'stale';
  } else if (chunksCount === 0 && filesCount > 0) {
    health = 'degraded';
  } else if (dirty) {
    health = 'degraded';
  }

  return {
    health,
    filesCount,
    chunksCount,
    symbolsCount,
    vectorStatus,
    lastIndexed,
    dirty,
    locked,
    lockInfo,
  };
}

// ============================================================
// MCP Server creation
// ============================================================

export function createServer(projectRoot: string): McpServer {
  const server = new McpServer({
    name: 'workspace-knowledge-index',
    version: '0.1.0',
  });

  server.tool(
    'knowledge_search',
    'Search the workspace knowledge index for relevant code chunks',
    {
      query: z.string().describe('The search query'),
      project_id: z.string().optional().describe('Filter by project ID'),
      file_type: z.string().optional().describe('Filter by file type (e.g. "ts", "py")'),
      top_k: z.number().optional().describe('Maximum number of results to return (default: 10)'),
      mode: z
        .enum(['auto', 'fts', 'vector', 'hybrid'])
        .optional()
        .describe('Search mode (default: fts)'),
    },
    async (args) => {
      try {
        const response = await handleKnowledgeSearch(args as SearchParams, projectRoot);
        return {
          content: [
            {
              type: 'text' as const,
              text: JSON.stringify(response, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: 'text' as const,
              text: JSON.stringify({
                error: err instanceof Error ? err.message : String(err),
              }),
            },
          ],
          isError: true,
        };
      }
    },
  );

  server.tool(
    'knowledge_symbol_search',
    'Search the symbol index for functions, classes, interfaces, types, and variables. Useful for finding definitions, rename references, and understanding code structure.',
    {
      name: z.string().optional().describe('Symbol name to search for'),
      name_mode: z
        .enum(['exact', 'prefix', 'contains', 'regex'])
        .optional()
        .describe('How to match the name (default: contains)'),
      kind: z
        .string()
        .optional()
        .describe('Filter by symbol kind: function, class, interface, type, enum, variable, etc.'),
      file_path: z.string().optional().describe('Filter by file path substring'),
      exported_only: z.boolean().optional().describe('Only return exported symbols (default: false)'),
      top_k: z.number().optional().describe('Maximum results to return (default: 20)'),
    },
    async (args) => {
      try {
        const response = handleSymbolSearch(args as SymbolSearchParams, projectRoot);
        return {
          content: [
            {
              type: 'text' as const,
              text: JSON.stringify(response, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: 'text' as const,
              text: JSON.stringify({
                error: err instanceof Error ? err.message : String(err),
              }),
            },
          ],
          isError: true,
        };
      }
    },
  );

  server.tool(
    'knowledge_stale_check',
    'Check if the index is stale (files changed since last indexing). Supports Rule #9 (Edit Integrity) — warns agents when working with outdated index data.',
    {},
    async () => {
      try {
        const config = loadConfig(projectRoot);
        const knowledgeDir = path.resolve(projectRoot, config.storage.index_root);
        const freshnessPath = path.join(knowledgeDir, 'freshness.lock');

        const freshness = new FreshnessManager();
        const prevState = freshness.load(freshnessPath);

        if (!prevState) {
          return {
            content: [{ type: 'text' as const, text: JSON.stringify({ stale: true, reason: 'no freshness state found' }) }],
          };
        }

        const changes = freshness.detectChanges(prevState, projectRoot);
        const totalChanges = changes.added.length + changes.modified.length + changes.deleted.length + changes.renamed.length;

        return {
          content: [{
            type: 'text' as const,
            text: JSON.stringify({
              stale: totalChanges > 0,
              lastIndexed: prevState.indexed_at,
              totalChanges,
              added: changes.added.length,
              modified: changes.modified.length,
              deleted: changes.deleted.length,
              renamed: changes.renamed.length,
              changedFiles: [
                ...changes.added.slice(0, 10),
                ...changes.modified.slice(0, 10),
              ],
            }, null, 2),
          }],
        };
      } catch (err) {
        return {
          content: [{ type: 'text' as const, text: JSON.stringify({ error: err instanceof Error ? err.message : String(err) }) }],
          isError: true,
        };
      }
    },
  );

  server.tool(
    'knowledge_chunk_map',
    'Get chunk boundaries for a file. Helps agents plan precise offset/limit reads for large files (Rule #7: File Read Budget).',
    {
      file_path: z.string().describe('File path or substring to look up chunk boundaries for'),
    },
    async (args) => {
      try {
        const response = handleChunkMap(args as ChunkMapParams, projectRoot);
        return {
          content: [
            {
              type: 'text' as const,
              text: JSON.stringify(response, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: 'text' as const,
              text: JSON.stringify({
                error: err instanceof Error ? err.message : String(err),
              }),
            },
          ],
          isError: true,
        };
      }
    },
  );

  server.tool(
    'knowledge_status',
    'Get the status and health of the workspace knowledge index',
    {
      project_id: z.string().optional().describe('Project ID to check status for'),
    },
    async (args) => {
      try {
        const status = await handleKnowledgeStatus(args as StatusParams, projectRoot);
        return {
          content: [
            {
              type: 'text' as const,
              text: JSON.stringify(status, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: 'text' as const,
              text: JSON.stringify({
                error: err instanceof Error ? err.message : String(err),
              }),
            },
          ],
          isError: true,
        };
      }
    },
  );

  return server;
}

export async function startServer(projectRoot?: string): Promise<void> {
  const root = projectRoot ?? process.cwd();
  const server = createServer(root);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}
