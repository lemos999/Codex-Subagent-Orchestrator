import { readFileSync } from 'node:fs';
import path from 'node:path';
import { resolve } from 'node:path';

// ============================================================
// wki.config.json Type Definitions
// ============================================================

export interface WkiConfig {
  projects: ProjectConfig[];
  storage: StorageConfig;
  embedding: EmbeddingConfig;
  chunking: ChunkingConfig;
  indexing: IndexingConfig;
  logging: LoggingConfig;
  search: SearchConfig;
  schema_version: number;
}

export interface ProjectConfig {
  name: string;
  root: string;
  exclude?: string[];
}

export interface StorageConfig {
  index_root: string;
  vector_backend: 'lancedb' | 'qdrant' | 'none';
  lancedb?: {
    path: string;
  };
  qdrant?: {
    url: string;
    api_key: string | null;
  };
}

export interface EmbeddingConfig {
  provider: 'openai' | 'voyage' | 'local';
  openai?: {
    model: string;
    dimensions: number;
  };
  voyage?: {
    model: string;
    dimensions: number;
  };
  local?: {
    runtime: string;
    model: string;
    dimensions: number;
    dtype?: string;       // default dtype for both indexing and search
    indexDtype?: string;   // override for indexing (e.g., 'q8' for faster rebuild)
    searchDtype?: string;  // override for search (e.g., 'fp32' for accuracy)
  };
}

export interface ChunkingConfig {
  max_lines: number;
  overlap_lines: number;
  max_tokens: number;
}

export interface IndexingConfig {
  concurrency: number;        // Reserved for Phase 3 — not yet wired to runtime
  max_file_size_mb: number;   // Active — files exceeding this size are skipped
  follow_gitignore: boolean;  // Reserved for Phase 3 — not yet wired to runtime
  timeout_ms: number;         // Reserved for Phase 3 — not yet wired to runtime
  retry: number;              // Reserved for Phase 3 — not yet wired to runtime
}

export interface LoggingConfig {
  level: 'debug' | 'info' | 'warn' | 'error';
}

export interface SearchConfig {
  fts_db: string;
  fusion: {
    strategy: 'weighted_sum' | 'rrf';
    weights: {
      fts: number;
      vector: number;
    };
  };
  indexDtype?: string;  // dtype used for indexing — enables q8-aware search adjustments
}

// ============================================================
// Defaults
// ============================================================

export const DEFAULT_CONFIG: WkiConfig = {
  projects: [],
  storage: {
    index_root: '.knowledge',
    vector_backend: 'lancedb',
    lancedb: {
      path: '.knowledge/{project}/vectors.lance',
    },
  },
  embedding: {
    provider: 'openai',
    openai: {
      model: 'text-embedding-3-large',
      dimensions: 768,
    },
  },
  chunking: {
    max_lines: 200,
    overlap_lines: 50,
    max_tokens: 1000,
  },
  indexing: {
    concurrency: 4,
    max_file_size_mb: 10,
    follow_gitignore: true,
    timeout_ms: 30000,
    retry: 2,
  },
  logging: {
    level: 'info',
  },
  search: {
    fts_db: '.knowledge/{project}/fts.db',
    fusion: {
      strategy: 'weighted_sum',
      weights: { fts: 0.4, vector: 0.6 },
    },
  },
  schema_version: 1,
};

// ============================================================
// Load & Validate
// ============================================================

/**
 * Load wki.config.json from the given directory.
 * Falls back to defaults for missing fields.
 */
export function loadConfig(dir: string): WkiConfig {
  const configPath = resolve(dir, 'wki.config.json');
  let raw: Record<string, unknown>;

  try {
    const content = readFileSync(configPath, 'utf-8');
    raw = JSON.parse(content) as Record<string, unknown>;
  } catch {
    // If no config file exists, return defaults
    return { ...DEFAULT_CONFIG };
  }

  return validateConfig(raw);
}

/**
 * Validate a raw config object and merge with defaults.
 * Throws on invalid structure.
 */
/** Deep merge two optional sub-objects; returns undefined if both are absent. */
function mergeOptional<T>(
  defaults: T | undefined,
  override: Record<string, unknown> | undefined,
): T | undefined {
  if (!defaults && !override) return undefined;
  return { ...defaults, ...override } as T;
}

export function validateConfig(raw: Record<string, unknown>): WkiConfig {
  const rawStorage = raw['storage'] as Record<string, unknown> | undefined;
  const rawEmbedding = raw['embedding'] as Record<string, unknown> | undefined;
  const rawSearch = raw['search'] as Record<string, unknown> | undefined;
  const rawFusion = rawSearch?.['fusion'] as Record<string, unknown> | undefined;

  const config: WkiConfig = {
    ...DEFAULT_CONFIG,
    ...raw,
    storage: {
      ...DEFAULT_CONFIG.storage,
      ...rawStorage,
      lancedb: mergeOptional(
        DEFAULT_CONFIG.storage.lancedb,
        rawStorage?.['lancedb'] as Record<string, unknown> | undefined,
      ),
      qdrant: mergeOptional(
        DEFAULT_CONFIG.storage.qdrant,
        rawStorage?.['qdrant'] as Record<string, unknown> | undefined,
      ),
    },
    embedding: {
      ...DEFAULT_CONFIG.embedding,
      ...rawEmbedding,
      openai: mergeOptional(
        DEFAULT_CONFIG.embedding.openai,
        rawEmbedding?.['openai'] as Record<string, unknown> | undefined,
      ),
      voyage: mergeOptional(
        DEFAULT_CONFIG.embedding.voyage,
        rawEmbedding?.['voyage'] as Record<string, unknown> | undefined,
      ),
      local: mergeOptional(
        DEFAULT_CONFIG.embedding.local,
        rawEmbedding?.['local'] as Record<string, unknown> | undefined,
      ),
    },
    chunking: {
      ...DEFAULT_CONFIG.chunking,
      ...(raw['chunking'] as Record<string, unknown> | undefined),
    },
    indexing: {
      ...DEFAULT_CONFIG.indexing,
      ...(raw['indexing'] as Record<string, unknown> | undefined),
    },
    logging: {
      ...DEFAULT_CONFIG.logging,
      ...(raw['logging'] as Record<string, unknown> | undefined),
    },
    search: {
      ...DEFAULT_CONFIG.search,
      ...rawSearch,
      fusion: {
        ...DEFAULT_CONFIG.search.fusion,
        ...rawFusion,
        weights: {
          ...DEFAULT_CONFIG.search.fusion.weights,
          ...(rawFusion?.['weights'] as Record<string, unknown> | undefined),
        },
      },
    },
  };

  // Basic validation
  if (!Array.isArray(config.projects)) {
    throw new Error('wki.config.json: "projects" must be an array');
  }

  for (const project of config.projects) {
    if (!project.name || typeof project.name !== 'string') {
      throw new Error('wki.config.json: each project must have a "name" string');
    }
    if (!project.root || typeof project.root !== 'string') {
      throw new Error(`wki.config.json: project "${project.name}" must have a "root" string`);
    }
  }

  const validBackends = ['lancedb', 'qdrant', 'none'];
  if (!validBackends.includes(config.storage.vector_backend)) {
    throw new Error(`wki.config.json: invalid vector_backend "${config.storage.vector_backend}"`);
  }

  const validProviders = ['openai', 'voyage', 'local'];
  if (!validProviders.includes(config.embedding.provider)) {
    throw new Error(`wki.config.json: invalid embedding provider "${config.embedding.provider}"`);
  }

  return config;
}

/**
 * Resolve the FTS database path from config, replacing {project} placeholder.
 */
export function resolveFtsDbPath(config: WkiConfig, knowledgeDir: string, projectId: string): string {
  const template = config.search.fts_db;
  const resolved = template.replace('{project}', projectId);

  // Normalize separators for cross-platform prefix comparison
  const normalizedResolved = resolved.replace(/\\/g, '/');
  const normalizedRoot = config.storage.index_root.replace(/\\/g, '/');

  // If the template starts with the index_root prefix, strip it and resolve from knowledgeDir
  if (normalizedResolved.startsWith(normalizedRoot)) {
    const relative = normalizedResolved.slice(normalizedRoot.length).replace(/^\/+/, '');
    return path.resolve(knowledgeDir, relative);
  }

  // Otherwise resolve relative to knowledgeDir
  return path.resolve(knowledgeDir, resolved);
}
