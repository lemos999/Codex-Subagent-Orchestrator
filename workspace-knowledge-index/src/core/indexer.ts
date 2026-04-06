import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import type { RawChunk, Chunk, ChunkWithEmbedding, SymbolInfo, ImportInfo } from '../types/index.js';
import type { TsParserResult } from '../interfaces/parser.js';
import type { EmbeddingProvider } from '../interfaces/embedding.js';
import type { VectorBackend } from '../interfaces/vector-backend.js';
import { Scanner } from './scanner.js';
import { TsParser } from '../parsers/ts-parser.js';
import { MdParser } from '../parsers/md-parser.js';
import { LineParser } from '../parsers/line-parser.js';
import { FtsStore, CHUNK_META_UPSERT_SQL, toChunkMetaParams } from '../store/fts-store.js';
import { DepsGraphImpl } from './deps-graph.js';
import { normalizePath, toRelativePosix } from '../utils/path.js';
import type { ChangedFiles } from './freshness.js';
import type { ChunkingConfig, IndexingConfig } from '../config/schema.js';

export interface IndexerConfig {
  chunking: ChunkingConfig;
  indexing: IndexingConfig;
}

export interface IndexResult {
  chunksAdded: number;
  chunksUpdated: number;
  chunksDeleted: number;
  symbolsExtracted: number;
  filesProcessed: number;
  embeddingsGenerated: number;
  errors: Array<{ filePath: string; error: string }>;
  durationMs: number;
}

export class Indexer {
  private maxFileSizeBytes: number;

  constructor(
    private projectId: string,
    private projectRoot: string,
    private knowledgeDir: string,
    private excludePatterns: string[],
    private config?: IndexerConfig,
    private embeddingProvider?: EmbeddingProvider,
    private vectorStore?: VectorBackend,
    private ftsDbPath?: string,
  ) {
    this.maxFileSizeBytes = (config?.indexing.max_file_size_mb ?? 10) * 1024 * 1024;
  }

  /** Resolve the FTS database path, using provided path or falling back to default. */
  private resolveFtsDbPath(): string {
    return this.ftsDbPath ?? path.join(this.knowledgeDir, 'fts.db');
  }

  /** Full indexing: scan all files, parse, store. */
  async indexFull(): Promise<IndexResult> {
    const startTime = Date.now();
    const result: IndexResult = {
      chunksAdded: 0,
      chunksUpdated: 0,
      chunksDeleted: 0,
      symbolsExtracted: 0,
      filesProcessed: 0,
      embeddingsGenerated: 0,
      errors: [],
      durationMs: 0,
    };

    // 1. Scan files
    const scanner = new Scanner(this.excludePatterns);
    const fileEntries = scanner.scan(this.projectRoot);

    // 2. Parse files by type
    const allChunks: Chunk[] = [];
    const allSymbols: SymbolInfo[] = [];
    const allImports: ImportInfo[] = [];

    // Separate TS files for program-level parsing
    const tsFiles: string[] = [];
    const otherFiles: Array<{ relativePath: string; fullPath: string; type: 'md' | 'line' }> = [];

    for (const entry of fileEntries) {
      // #5: Skip files exceeding max_file_size_mb
      if (entry.size > this.maxFileSizeBytes) {
        console.warn(`[indexer] Skipping large file (${(entry.size / 1024 / 1024).toFixed(1)}MB > ${this.maxFileSizeBytes / 1024 / 1024}MB): ${entry.path}`); // TODO: Phase 1B+ -- Logger 인터페이스 도입 후 교체
        continue;
      }

      const fullPath = path.resolve(this.projectRoot, entry.path);
      const parserType = this.selectParser(entry.path);

      if (parserType === 'ts') {
        tsFiles.push(fullPath);
      } else {
        otherFiles.push({
          relativePath: entry.path,
          fullPath,
          type: parserType,
        });
      }
    }

    // 2a. Parse TS files with TsParser (program-level)
    if (tsFiles.length > 0) {
      try {
        const tsParser = new TsParser();
        tsParser.initProgram(this.projectRoot);
        const tsResults = tsParser.parseProgram();

        for (const [filePath, tsResult] of tsResults) {
          const relativePath = toRelativePosix(this.projectRoot, filePath);
          try {
            this.processParserResult(tsResult, allChunks, allSymbols, allImports);
            result.filesProcessed++;
          } catch (err) {
            result.errors.push({
              filePath: relativePath,
              error: err instanceof Error ? err.message : String(err),
            });
          }
        }

        tsParser.dispose();
      } catch {
        // TsParser init failed -- fallback all TS files to LineParser
        const fallbackParser = new LineParser(
          this.config?.chunking.max_lines,
          this.config?.chunking.overlap_lines,
        );
        for (const fullPath of tsFiles) {
          const relativePath = toRelativePosix(this.projectRoot, fullPath);
          try {
            const content = fs.readFileSync(fullPath, 'utf-8');
            const rawChunks = fallbackParser.parse(relativePath, content);
            for (const raw of rawChunks) {
              allChunks.push(this.enrichChunk(raw, this.projectId));
            }
            result.filesProcessed++;
          } catch (fileErr) {
            result.errors.push({
              filePath: relativePath,
              error: fileErr instanceof Error ? fileErr.message : String(fileErr),
            });
          }
        }
      }
    }

    // 2b. Parse MD and other files
    const mdParser = new MdParser();
    const lineParser = new LineParser(
      this.config?.chunking.max_lines,
      this.config?.chunking.overlap_lines,
    );

    for (const file of otherFiles) {
      try {
        const content = fs.readFileSync(file.fullPath, 'utf-8');
        const parser = file.type === 'md' ? mdParser : lineParser;
        const rawChunks = parser.parse(file.relativePath, content);

        for (const raw of rawChunks) {
          allChunks.push(this.enrichChunk(raw, this.projectId));
        }
        result.filesProcessed++;
      } catch (err) {
        result.errors.push({
          filePath: file.relativePath,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }

    result.chunksAdded = allChunks.length;
    result.symbolsExtracted = allSymbols.length;

    // 3. Store chunks in FTS DB (full: build in staging, then swap atomically)
    const ftsDbPath = this.resolveFtsDbPath();
    const stagingPath = path.join(path.dirname(ftsDbPath), '.wki-staging-' + path.basename(ftsDbPath));
    if (stagingPath === ftsDbPath) {
      throw new Error(`Staging path must differ from live path: ${ftsDbPath}`);
    }

    // Clean up any leftover staging file
    if (fs.existsSync(stagingPath)) {
      fs.unlinkSync(stagingPath);
    }
    // Also clean up WAL/SHM for staging
    for (const suffix of ['-wal', '-shm']) {
      const walPath = stagingPath + suffix;
      if (fs.existsSync(walPath)) {
        fs.unlinkSync(walPath);
      }
    }

    let ftsStore: FtsStore;
    try {
      ftsStore = new FtsStore(stagingPath);
      const db = ftsStore.getDatabase();

      // Insert all new chunks into staging DB
      if (allChunks.length > 0) {
        const upsert = db.prepare(CHUNK_META_UPSERT_SQL);
        const transaction = db.transaction((items: Chunk[]) => {
          for (const chunk of items) {
            upsert.run(toChunkMetaParams(chunk));
          }
        });
        transaction(allChunks);
      }

      // Close staging DB before rename
      await ftsStore.close();

      // Atomically swap staging -> live
      // Remove WAL/SHM files for the live DB first
      for (const suffix of ['-wal', '-shm']) {
        const walPath = ftsDbPath + suffix;
        if (fs.existsSync(walPath)) {
          fs.unlinkSync(walPath);
        }
      }
      fs.renameSync(stagingPath, ftsDbPath);
    } catch (stagingErr) {
      // Clean up staging on failure — live DB stays untouched
      try { fs.unlinkSync(stagingPath); } catch { /* ignore */ }
      for (const suffix of ['-wal', '-shm']) {
        try { fs.unlinkSync(stagingPath + suffix); } catch { /* ignore */ }
      }
      throw stagingErr;
    }

    // 4. Embedding generation + vector storage (optional)
    if (this.embeddingProvider && this.vectorStore) {
      try {
        // Clear existing vectors for this project before re-inserting
        await this.vectorStore.rebuild();

        // Build file-level summaries for Contextual Flat Indexing
        const fileSummaryMap = new Map<string, string>();
        const chunksByFile = new Map<string, Chunk[]>();
        for (const c of allChunks) {
          const existing = chunksByFile.get(c.filePath) ?? [];
          existing.push(c);
          chunksByFile.set(c.filePath, existing);
        }
        for (const [fp, fileChunks] of chunksByFile) {
          fileSummaryMap.set(fp, buildFileSummary(fileChunks));
        }

        const contents = allChunks.map(c => buildEmbeddingText(c, fileSummaryMap.get(c.filePath)));
        const embeddings = await this.embeddingProvider.batchEmbed(contents);

        const chunksWithEmbedding: ChunkWithEmbedding[] = allChunks.map((chunk, i) => ({
          ...chunk,
          embedding: embeddings[i],
        }));

        await this.vectorStore.insert(chunksWithEmbedding);
        result.embeddingsGenerated = embeddings.length;
      } catch (err) {
        console.warn(`[indexer] Embedding generation failed: ${err instanceof Error ? err.message : String(err)}`);
      }
    }

    // 5. Save symbols.idx (JSONL)
    const symbolsPath = path.join(this.knowledgeDir, 'symbols.idx');
    this.saveSymbolsIdx(allSymbols, symbolsPath);

    // 6. Build and save deps.graph (JSON)
    const depsGraph = new DepsGraphImpl();
    for (const imp of allImports) {
      depsGraph.addFromImports([imp], path.resolve(this.projectRoot, imp.source));
    }
    const depsPath = path.join(this.knowledgeDir, 'deps.graph');
    depsGraph.save(depsPath);

    result.durationMs = Date.now() - startTime;
    return result;
  }

  /** Incremental indexing: process only changed files. */
  async indexIncremental(changedFiles: ChangedFiles): Promise<IndexResult> {
    const startTime = Date.now();
    const result: IndexResult = {
      chunksAdded: 0,
      chunksUpdated: 0,
      chunksDeleted: 0,
      symbolsExtracted: 0,
      filesProcessed: 0,
      embeddingsGenerated: 0,
      errors: [],
      durationMs: 0,
    };

    const ftsDbPath = this.resolveFtsDbPath();
    const ftsStore = new FtsStore(ftsDbPath);
    const db = ftsStore.getDatabase();

    // Detect files present on disk but missing from FTS index (gap repair).
    // This happens when previous incremental runs didn't cover all scanner output
    // (e.g., first-time full index was incomplete or FTS was rebuilt from partial state).
    const scanner = new Scanner(this.excludePatterns);
    const allDiskFiles = scanner.scan(this.projectRoot);
    const indexedFilesRows = db.prepare(
      'SELECT DISTINCT file_path FROM chunks_meta WHERE project_id = ?',
    ).all(this.projectId) as Array<{ file_path: string }>;
    const indexedFileSet = new Set(indexedFilesRows.map(r => r.file_path));

    const missingFiles: string[] = [];
    for (const entry of allDiskFiles) {
      const normalized = normalizePath(entry.path);
      if (!indexedFileSet.has(normalized)) {
        missingFiles.push(entry.path);
      }
    }

    if (missingFiles.length > 0) {
      // Merge missing files into changedFiles.added (dedupe)
      const addedSet = new Set(changedFiles.added);
      for (const f of missingFiles) {
        if (!addedSet.has(f)) {
          changedFiles.added.push(f);
          addedSet.add(f);
        }
      }
      console.log(`[indexer] Gap repair: ${missingFiles.length} files on disk but missing from index — adding to incremental batch.`);
    }

    // Load existing symbols and deps
    const symbolsPath = path.join(this.knowledgeDir, 'symbols.idx');
    const existingSymbols = this.loadSymbolsIdx(symbolsPath);
    const depsPath = path.join(this.knowledgeDir, 'deps.graph');
    const depsGraph = new DepsGraphImpl();
    if (fs.existsSync(depsPath)) {
      try {
        const depsData = fs.readFileSync(depsPath, 'utf-8');
        depsGraph.load(depsData);
      } catch {
        // Corrupted deps graph -- will be rebuilt from available data
      }
    }

    // Helper: query chunk IDs from FTS for a given file path (before deleting FTS rows)
    const getChunkIdsForFile = (filePath: string): string[] => {
      const rows = db.prepare(`
        SELECT
          CASE WHEN content_hash IS NOT NULL AND content_hash != ''
            THEN file_path || '::' || content_hash
            ELSE file_path || ':' || ordinal
          END AS chunk_id
        FROM chunks_meta
        WHERE file_path = ? AND project_id = ?
      `).all(filePath, this.projectId) as Array<{ chunk_id: string }>;
      return rows.map(r => r.chunk_id);
    };

    // 1. Handle deleted files
    for (const deletedFile of changedFiles.deleted) {
      const normalized = normalizePath(deletedFile);

      // Collect old chunk IDs for vector store deletion before removing FTS rows
      if (this.vectorStore) {
        const oldChunkIds = getChunkIdsForFile(normalized);
        if (oldChunkIds.length > 0) {
          await this.vectorStore.delete(oldChunkIds);
        }
      }

      const info = db.prepare('DELETE FROM chunks_meta WHERE file_path = ? AND project_id = ?')
        .run(normalized, this.projectId);
      result.chunksDeleted += info.changes;
    }

    // Remove symbols for deleted files
    const deletedSet = new Set(changedFiles.deleted.map(f => normalizePath(f)));
    const filteredSymbols = existingSymbols.filter(s => !deletedSet.has(normalizePath(s.filePath)));

    // 2. Handle added + modified + renamed files
    const filesToProcess = [
      ...changedFiles.added,
      ...changedFiles.modified,
      ...changedFiles.renamed.map(r => r.to),
    ];

    // Delete old paths for renamed files (including vector store cleanup)
    for (const renamed of changedFiles.renamed) {
      const normalized = normalizePath(renamed.from);

      if (this.vectorStore) {
        const oldChunkIds = getChunkIdsForFile(normalized);
        if (oldChunkIds.length > 0) {
          await this.vectorStore.delete(oldChunkIds);
        }
      }

      db.prepare('DELETE FROM chunks_meta WHERE file_path = ? AND project_id = ?')
        .run(normalized, this.projectId);
    }

    const mdParser = new MdParser();
    const lineParser = new LineParser(
      this.config?.chunking.max_lines,
      this.config?.chunking.overlap_lines,
    );
    const newSymbols: SymbolInfo[] = [];
    const newImports: ImportInfo[] = [];

    // Remove existing symbols for files being re-processed
    const processSet = new Set(filesToProcess.map(f => normalizePath(f)));
    const keptSymbols = filteredSymbols.filter(s => !processSet.has(normalizePath(s.filePath)));

    // #3: Separate TS files and create TsParser once outside the loop
    const tsFilesToProcess: Array<{ filePath: string; normalized: string; fullPath: string }> = [];
    const nonTsFilesToProcess: Array<{ filePath: string; normalized: string; fullPath: string; parserType: 'md' | 'line' }> = [];

    for (const filePath of filesToProcess) {
      const normalized = normalizePath(filePath);
      const fullPath = path.resolve(this.projectRoot, filePath);
      if (!fs.existsSync(fullPath)) continue;

      // #5: Skip files exceeding max_file_size_mb
      try {
        const stat = fs.statSync(fullPath);
        if (stat.size > this.maxFileSizeBytes) {
          console.warn(`[indexer] Skipping large file (${(stat.size / 1024 / 1024).toFixed(1)}MB > ${this.maxFileSizeBytes / 1024 / 1024}MB): ${filePath}`); // TODO: Phase 1B+ -- Logger 인터페이스 도입 후 교체
          continue;
        }
      } catch {
        continue;
      }

      const parserType = this.selectParser(filePath);
      if (parserType === 'ts') {
        tsFilesToProcess.push({ filePath, normalized, fullPath });
      } else {
        nonTsFilesToProcess.push({ filePath, normalized, fullPath, parserType });
      }
    }

    // Delete old vectors for modified files before re-processing
    if (this.vectorStore) {
      for (const modifiedFile of changedFiles.modified) {
        const normalized = normalizePath(modifiedFile);
        const oldChunkIds = getChunkIdsForFile(normalized);
        if (oldChunkIds.length > 0) {
          await this.vectorStore.delete(oldChunkIds);
        }
      }
    }

    // #7: Prepare statement once and wrap all inserts in a single transaction
    const deleteByFile = db.prepare('DELETE FROM chunks_meta WHERE file_path = ? AND project_id = ?');
    const upsert = db.prepare(CHUNK_META_UPSERT_SQL);

    const allNewChunks: Chunk[] = [];
    const filesToDelete: Array<{ normalized: string }> = [];

    // #3: Parse TS files with a single TsParser instance
    if (tsFilesToProcess.length > 0) {
      let tsParser: TsParser | null = null;
      let tsInitFailed = false;
      try {
        tsParser = new TsParser();
        tsParser.initProgram(this.projectRoot);
      } catch {
        tsInitFailed = true;
      }

      for (const { filePath, normalized, fullPath } of tsFilesToProcess) {
        try {
          filesToDelete.push({ normalized });
          const content = fs.readFileSync(fullPath, 'utf-8');

          let rawChunks: RawChunk[];
          let fileSymbols: SymbolInfo[] = [];
          let fileImports: ImportInfo[] = [];

          if (!tsInitFailed && tsParser) {
            try {
              const tsResult = tsParser.parseFile(fullPath);
              rawChunks = tsResult.chunks;
              fileSymbols = tsResult.symbols;
              fileImports = tsResult.imports;
            } catch {
              // Fallback to LineParser on TS parse failure
              rawChunks = lineParser.parse(normalized, content);
            }
          } else {
            rawChunks = lineParser.parse(normalized, content);
          }

          const chunks = rawChunks.map(raw => this.enrichChunk(raw, this.projectId));
          allNewChunks.push(...chunks);

          result.chunksAdded += chunks.length;
          result.filesProcessed++;
          newSymbols.push(...fileSymbols);
          newImports.push(...fileImports);
        } catch (err) {
          result.errors.push({
            filePath: normalized,
            error: err instanceof Error ? err.message : String(err),
          });
        }
      }

      tsParser?.dispose();
    }

    // Parse non-TS files
    for (const { filePath, normalized, fullPath, parserType } of nonTsFilesToProcess) {
      try {
        filesToDelete.push({ normalized });
        const content = fs.readFileSync(fullPath, 'utf-8');
        const parser = parserType === 'md' ? mdParser : lineParser;
        const rawChunks = parser.parse(normalized, content);
        const chunks = rawChunks.map(raw => this.enrichChunk(raw, this.projectId));
        allNewChunks.push(...chunks);

        result.chunksAdded += chunks.length;
        result.filesProcessed++;
      } catch (err) {
        result.errors.push({
          filePath: normalized,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }

    // #7: Execute all deletes + inserts in a single transaction
    const runTransaction = db.transaction(() => {
      for (const { normalized } of filesToDelete) {
        deleteByFile.run(normalized, this.projectId);
      }
      for (const chunk of allNewChunks) {
        upsert.run(toChunkMetaParams(chunk));
      }
    });
    runTransaction();

    // Embedding generation + vector storage (optional)
    if (this.embeddingProvider && this.vectorStore && allNewChunks.length > 0) {
      try {
        // Build file summaries for new chunks
        const incFileSummaryMap = new Map<string, string>();
        const incChunksByFile = new Map<string, Chunk[]>();
        for (const c of allNewChunks) {
          const existing = incChunksByFile.get(c.filePath) ?? [];
          existing.push(c);
          incChunksByFile.set(c.filePath, existing);
        }
        for (const [fp, fileChunks] of incChunksByFile) {
          incFileSummaryMap.set(fp, buildFileSummary(fileChunks));
        }

        const contents = allNewChunks.map(c => buildEmbeddingText(c, incFileSummaryMap.get(c.filePath)));
        const embeddings = await this.embeddingProvider.batchEmbed(contents);

        const chunksWithEmbedding: ChunkWithEmbedding[] = allNewChunks.map((chunk, i) => ({
          ...chunk,
          embedding: embeddings[i],
        }));

        await this.vectorStore.insert(chunksWithEmbedding);
        result.embeddingsGenerated = embeddings.length;
      } catch (err) {
        console.warn(`[indexer] Embedding generation failed: ${err instanceof Error ? err.message : String(err)}`);
      }
    }

    // 3. Update symbols.idx
    const allSymbols = [...keptSymbols, ...newSymbols];
    result.symbolsExtracted = newSymbols.length;
    this.saveSymbolsIdx(allSymbols, symbolsPath);

    // 4. Update deps.graph with new imports
    for (const imp of newImports) {
      depsGraph.addFromImports([imp], path.resolve(this.projectRoot, imp.source));
    }
    depsGraph.save(depsPath);

    // Close store
    await ftsStore.close();

    result.durationMs = Date.now() - startTime;
    return result;
  }

  /** Select parser type based on file extension. */
  private selectParser(filePath: string): 'ts' | 'md' | 'line' {
    const ext = path.extname(filePath).toLowerCase();
    if (['.ts', '.tsx', '.js', '.jsx'].includes(ext)) return 'ts';
    if (['.md', '.mdx'].includes(ext)) return 'md';
    return 'line';
  }

  /** Convert RawChunk to enriched Chunk. */
  private enrichChunk(raw: RawChunk, projectId: string): Chunk {
    return {
      ...raw,
      id: `${projectId}:${raw.filePath}:${raw.ordinal}`,
      projectId,
      tokenCount: Math.ceil(raw.content.length / 4),
      contentHash: createHash('sha256').update(raw.content).digest('hex'),
    };
  }

  /** Process TsParserResult into accumulated arrays. */
  private processParserResult(
    tsResult: TsParserResult,
    allChunks: Chunk[],
    allSymbols: SymbolInfo[],
    allImports: ImportInfo[],
  ): void {
    for (const raw of tsResult.chunks) {
      // Normalize TS parser absolute paths to relative
      raw.filePath = toRelativePosix(this.projectRoot, raw.filePath);
      allChunks.push(this.enrichChunk(raw, this.projectId));
    }
    // Also normalize symbol/import paths
    for (const sym of tsResult.symbols) {
      sym.filePath = toRelativePosix(this.projectRoot, sym.filePath);
    }
    for (const imp of tsResult.imports) {
      imp.source = toRelativePosix(this.projectRoot, imp.source);
    }
    allSymbols.push(...tsResult.symbols);
    allImports.push(...tsResult.imports);
  }

  /** Save SymbolInfo[] as JSONL. */
  private saveSymbolsIdx(symbols: SymbolInfo[], filePath: string): void {
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    if (symbols.length === 0) {
      fs.writeFileSync(filePath, '', 'utf-8');
      return;
    }
    const lines = symbols.map(s => JSON.stringify(s));
    fs.writeFileSync(filePath, lines.join('\n') + '\n', 'utf-8');
  }

  /** Load SymbolInfo[] from JSONL. */
  private loadSymbolsIdx(filePath: string): SymbolInfo[] {
    if (!fs.existsSync(filePath)) return [];
    try {
      const content = fs.readFileSync(filePath, 'utf-8');
      return content
        .split('\n')
        .filter(line => line.trim().length > 0)
        .map(line => JSON.parse(line) as SymbolInfo);
    } catch {
      return [];
    }
  }
}

/**
 * Build embedding text with structural context prepended.
 * Contextual Flat Indexing: enrich each chunk with file-level summary
 * so the embedding captures both file context and chunk content.
 */
function buildEmbeddingText(chunk: Chunk, fileSummary?: string): string {
  const parts: string[] = [];
  if (chunk.filePath) parts.push(`file: ${chunk.filePath}`);
  if (fileSummary) parts.push(fileSummary);
  if (chunk.heading) parts.push(`section: ${chunk.heading}`);
  const prefix = parts.length > 0 ? parts.join(' | ') + '\n' : '';
  return prefix + chunk.content;
}

/**
 * Build a file-level summary string from chunks belonging to the same file.
 * Used as context prefix for Contextual Flat Indexing.
 */
function buildFileSummary(chunks: Chunk[]): string {
  if (chunks.length === 0) return '';

  const exports: string[] = [];
  const headings: string[] = [];

  for (const c of chunks) {
    if (c.chunkType === 'function' || c.chunkType === 'class' ||
        c.chunkType === 'interface' || c.chunkType === 'type' ||
        c.chunkType === 'enum') {
      if (c.heading && c.heading !== '<anonymous>') {
        exports.push(c.heading);
      }
    }
    if (c.chunkType === 'markdown-section' && c.heading) {
      headings.push(c.heading);
    }
  }

  // Keep summaries short to avoid diluting chunk content in embedding
  if (exports.length > 0) {
    return `exports: ${exports.slice(0, 4).join(', ')}`;
  }
  if (headings.length > 0) {
    return `topic: ${headings[0]}`;
  }
  return '';
}
