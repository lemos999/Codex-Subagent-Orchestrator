#!/usr/bin/env node

/**
 * WKI CLI entry point.
 * Parses process.argv for subcommands.
 */

import fs from 'node:fs';
import path from 'node:path';
import { loadConfig, resolveFtsDbPath } from './config/schema.js';
import type { EmbeddingProvider } from './interfaces/embedding.js';
import type { VectorBackend } from './interfaces/vector-backend.js';
import { FileMap } from './core/file-map.js';
import { FreshnessManager } from './core/freshness.js';
import { IndexLock } from './core/index-lock.js';
import { Indexer } from './core/indexer.js';
import { FtsStore } from './store/fts-store.js';
import { ChunkStore } from './store/chunk-store.js';
import { LanceVectorStore } from './store/vector-store.js';
import { SearchService } from './search/search-service.js';
import { createEmbeddingProvider } from './embedding/factory.js';

const COMMANDS = ['init', 'scan', 'index', 'search', 'status', 'rebuild', 'eval', 'mcp'] as const;
type Command = (typeof COMMANDS)[number];

function printUsage(): void {
  console.log(`
Usage: wki <command> [options]

Commands:
  init      Initialize .knowledge/ directory and perform first scan
  scan      Scan files and update file-map.json
  index     Build or update the search index
  search    Search the knowledge index
  status    Show index health and freshness
  rebuild   Rebuild index from scratch
  eval      Evaluate search quality against a gold set
  mcp       Start MCP server (long-running, communicates via stdio)

Run "wki <command> --help" for more information on a command.
`);
}

function cmdInit(args: string[]): void {
  const projectRoot = args[0] ? path.resolve(args[0]) : process.cwd();

  // 1. Load config
  const config = loadConfig(projectRoot);
  const indexRoot = config.storage.index_root; // default: '.knowledge'
  const knowledgeDir = path.resolve(projectRoot, indexRoot);

  // 2. Create .knowledge/ directory
  if (!fs.existsSync(knowledgeDir)) {
    fs.mkdirSync(knowledgeDir, { recursive: true });
  }

  // 3. Determine exclude patterns from config
  const excludePatterns: string[] = [];
  for (const proj of config.projects) {
    if (proj.exclude) {
      excludePatterns.push(...proj.exclude);
    }
  }

  // 4. Generate file map
  const fileMap = new FileMap();
  fileMap.generate(projectRoot, excludePatterns);

  // 5. Save file-map.json
  const fileMapPath = path.join(knowledgeDir, 'file-map.json');
  fileMap.save(fileMapPath);

  // 6. Capture and save freshness state
  const freshness = new FreshnessManager();
  const state = freshness.captureState(projectRoot);
  const freshnessPath = path.join(knowledgeDir, 'freshness.lock');
  freshness.save(freshnessPath, state);

  console.log(`Initialized ${indexRoot}/ with ${fileMap.size} files`);
}

function cmdScan(args: string[]): void {
  const projectRoot = args[0] ? path.resolve(args[0]) : process.cwd();

  // 1. Load config
  const config = loadConfig(projectRoot);
  const indexRoot = config.storage.index_root;
  const knowledgeDir = path.resolve(projectRoot, indexRoot);

  if (!fs.existsSync(knowledgeDir)) {
    console.error(`Error: ${indexRoot}/ does not exist. Run "wki init" first.`);
    process.exit(1);
  }

  const lock = new IndexLock(knowledgeDir);
  lock.acquire('scan');
  try {
    // 2. Load existing freshness state
    const freshness = new FreshnessManager();
    const freshnessPath = path.join(knowledgeDir, 'freshness.lock');
    const prevState = freshness.load(freshnessPath);

    // Determine exclude patterns
    const excludePatterns: string[] = [];
    for (const proj of config.projects) {
      if (proj.exclude) {
        excludePatterns.push(...proj.exclude);
      }
    }

    // 3. Load existing file map
    const fileMap = new FileMap();
    const fileMapPath = path.join(knowledgeDir, 'file-map.json');
    fileMap.load(fileMapPath);

    if (prevState) {
      // Incremental: detect changes and update
      const changes = freshness.detectChanges(prevState, projectRoot);
      const allChanged = [
        ...changes.added,
        ...changes.modified,
        ...changes.deleted,
        ...changes.renamed.map((r) => r.to),
      ];

      // Also remove old paths for renamed files
      for (const r of changes.renamed) {
        allChanged.push(r.from);
      }

      fileMap.update(projectRoot, allChanged, excludePatterns);

      console.log(
        `Scanned: ${changes.added.length} added, ${changes.modified.length} modified, ${changes.deleted.length} deleted`,
      );
    } else {
      // No previous state: full regeneration
      fileMap.generate(projectRoot, excludePatterns);
      console.log(`Full scan: ${fileMap.size} files`);
    }

    // 4. Save updated file map
    fileMap.save(fileMapPath);

    // 5. Save new freshness state
    const newState = freshness.captureState(projectRoot);
    freshness.save(freshnessPath, newState);
  } finally {
    lock.release();
  }
}

async function cmdIndex(args: string[]): Promise<void> {
  const isFullReindex = args.includes('--full');
  const projectRoot = args.find(a => !a.startsWith('--'))
    ? path.resolve(args.find(a => !a.startsWith('--'))!)
    : process.cwd();

  // 1. Load config
  const config = loadConfig(projectRoot);
  const indexRoot = config.storage.index_root;
  const knowledgeDir = path.resolve(projectRoot, indexRoot);

  // 2. Check .knowledge/ exists
  if (!fs.existsSync(knowledgeDir)) {
    console.error(`Error: ${indexRoot}/ does not exist. Run "wki init" first.`);
    process.exit(1);
  }

  const lock = new IndexLock(knowledgeDir);
  lock.acquire('index');
  try {
    // Determine project ID and exclude patterns
    const projectId = config.projects.length > 0 ? config.projects[0].name : path.basename(projectRoot);
    const excludePatterns: string[] = [];
    for (const proj of config.projects) {
      if (proj.exclude) {
        excludePatterns.push(...proj.exclude);
      }
    }

    // OPTIMIZATION: Check for changes BEFORE loading embedding model
    // If no changes and not full reindex, exit immediately (no model loading)
    if (!isFullReindex) {
      const freshness = new FreshnessManager();
      const freshnessPath = path.join(knowledgeDir, 'freshness.lock');
      const prevState = freshness.load(freshnessPath);
      if (prevState) {
        const changedFiles = freshness.detectChanges(prevState, projectRoot);
        const totalChanges =
          changedFiles.added.length +
          changedFiles.modified.length +
          changedFiles.deleted.length +
          changedFiles.renamed.length;

        if (totalChanges === 0) {
          console.log('Index is up to date. No changes detected.');
          return;
        }
        // Changes found — proceed with model loading below
      }
    }

    // Conditionally create embedding provider and vector store
    // Only loaded when changes are detected (optimization: skip for no-change case above)
    let embeddingProvider: EmbeddingProvider | undefined;
    let vectorStore: VectorBackend | undefined;

    if (config.storage.vector_backend !== 'none') {
      try {
        embeddingProvider = await createEmbeddingProvider(config.embedding);
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.warn(`[wki] Embedding provider (${config.embedding.provider}) failed: ${msg}`);
        console.warn('[wki] Running FTS-only mode.');
      }

      if (embeddingProvider && config.storage.vector_backend === 'lancedb') {
        const dims = embeddingProvider.dimensions;
        const lanceDbPath = config.storage.lancedb?.path
          ? path.resolve(knowledgeDir, config.storage.lancedb.path.replace('{project}', projectId))
          : path.join(knowledgeDir, 'vectors.lance');
        const lanceStore = new LanceVectorStore(lanceDbPath, dims);
        await lanceStore.init();
        vectorStore = lanceStore;
      }
    }

    const ftsDbPath = resolveFtsDbPath(config, knowledgeDir, projectId);
    const indexer = new Indexer(projectId, projectRoot, knowledgeDir, excludePatterns, {
      chunking: config.chunking,
      indexing: config.indexing,
    }, embeddingProvider, vectorStore, ftsDbPath);
    const freshness = new FreshnessManager();
    const freshnessPath = path.join(knowledgeDir, 'freshness.lock');

    let indexResult;

    if (isFullReindex) {
      // 3. Full reindex
      indexResult = await indexer.indexFull();
    } else {
      // 4. Incremental: detect changes
      const prevState = freshness.load(freshnessPath);
      if (!prevState) {
        // No previous state — do full index
        indexResult = await indexer.indexFull();
      } else {
        const changedFiles = freshness.detectChanges(prevState, projectRoot);
        const totalChanges =
          changedFiles.added.length +
          changedFiles.modified.length +
          changedFiles.deleted.length +
          changedFiles.renamed.length;

        if (totalChanges === 0) {
          console.log('Index is up to date. No changes detected.');
          if (vectorStore) await vectorStore.close();
          return;
        }

        indexResult = await indexer.indexIncremental(changedFiles);
      }
    }

    // Close vector store
    if (vectorStore) await vectorStore.close();

    // 5. Update freshness.lock
    const newState = freshness.captureState(projectRoot);
    freshness.save(freshnessPath, newState);

    // 6. Print result
    const embSuffix = indexResult.embeddingsGenerated > 0 ? `, ${indexResult.embeddingsGenerated} embeddings` : '';
    const errSuffix = indexResult.errors.length > 0 ? `, ${indexResult.errors.length} errors` : '';
    console.log(
      `Indexed: ${indexResult.filesProcessed} files, ${indexResult.chunksAdded} chunks, ${indexResult.symbolsExtracted} symbols${embSuffix}${errSuffix} (${indexResult.durationMs}ms)`,
    );

    // Print errors if any
    for (const err of indexResult.errors) {
      console.error(`  Error: ${err.filePath}: ${err.error}`);
    }
  } finally {
    lock.release();
  }
}

function parseFlag(args: string[], flag: string, defaultValue: string): string {
  // Supports --flag value and --flag=value
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === flag && i + 1 < args.length) {
      return args[i + 1]!;
    }
    if (arg?.startsWith(`${flag}=`)) {
      return arg.slice(flag.length + 1);
    }
  }
  return defaultValue;
}

/** Collect the set of indices that are flag names or flag values. */
function flagIndices(args: string[], flags: string[]): Set<number> {
  const skip = new Set<number>();
  for (let i = 0; i < args.length; i++) {
    const arg = args[i]!;
    for (const flag of flags) {
      if (arg === flag && i + 1 < args.length) {
        skip.add(i);
        skip.add(i + 1);
      } else if (arg.startsWith(`${flag}=`)) {
        skip.add(i);
      }
    }
  }
  return skip;
}

/** Return the first positional argument (not a flag name/value). */
function firstPositional(args: string[], flags: string[]): string | undefined {
  const skip = flagIndices(args, flags);
  for (let i = 0; i < args.length; i++) {
    if (!skip.has(i) && !args[i]!.startsWith('--')) {
      return args[i];
    }
  }
  return undefined;
}

async function cmdSearch(args: string[]): Promise<void> {
  const searchFlags = ['--top', '--mode', '--project', '--output'];
  const query = firstPositional(args, searchFlags);
  if (!query) {
    console.error('Usage: wki search "query" [--top N] [--mode auto|fts|vector|hybrid] [--project NAME] [--output json|text]');
    process.exit(1);
  }

  const topK = parseInt(parseFlag(args, '--top', '10'), 10) || 10;
  const mode = parseFlag(args, '--mode', 'auto') as 'auto' | 'fts' | 'vector' | 'hybrid';
  const projectName = parseFlag(args, '--project', '');
  const outputFormat = parseFlag(args, '--output', 'text') as 'json' | 'text';

  const projectRoot = process.cwd();
  const config = loadConfig(projectRoot);
  const indexRoot = config.storage.index_root;
  const knowledgeDir = path.resolve(projectRoot, indexRoot);

  if (!fs.existsSync(knowledgeDir)) {
    console.error(`Error: ${indexRoot}/ does not exist. Run "wki init" first.`);
    process.exit(1);
  }

  const projectId = projectName || (config.projects.length > 0 ? config.projects[0].name : path.basename(projectRoot));

  // Open FTS store
  const ftsDbPath = resolveFtsDbPath(config, knowledgeDir, projectId);
  const ftsStore = new FtsStore(ftsDbPath);
  const chunkStore = new ChunkStore(ftsStore.getDatabase());

  // Open vector store if configured
  let vectorStore: LanceVectorStore | null = null;
  let embeddingProvider: EmbeddingProvider | null = null;

  if (config.storage.vector_backend !== 'none' && mode !== 'fts') {
    try {
      embeddingProvider = await createEmbeddingProvider(config.embedding);
    } catch {
      if (mode === 'vector') {
        console.error('Error: Vector search requested but no embedding API key found.');
        await ftsStore.close();
        process.exit(1);
      }
      console.warn('[wki] No embedding API key found. Falling back to FTS-only mode.');
    }

    if (embeddingProvider && config.storage.vector_backend === 'lancedb') {
      const dims = embeddingProvider.dimensions;
      const lanceDbPath = config.storage.lancedb?.path
        ? path.resolve(knowledgeDir, config.storage.lancedb.path.replace('{project}', projectId))
        : path.join(knowledgeDir, 'vectors.lance');
      if (fs.existsSync(lanceDbPath)) {
        vectorStore = new LanceVectorStore(lanceDbPath, dims);
        await vectorStore.init();
      }
    }
  }

  const searchService = new SearchService(ftsStore, vectorStore, chunkStore, embeddingProvider, config.search);

  const startTime = Date.now();
  const results = await searchService.search(query, {
    topK,
    mode,
    filter: projectName ? { projectId: projectName } : undefined,
    includeContent: true,
  });
  const durationMs = Date.now() - startTime;

  if (outputFormat === 'json') {
    const jsonResults = results.map(r => ({
      filePath: r.chunk.filePath,
      startLine: r.chunk.startLine,
      endLine: r.chunk.endLine,
      chunkType: r.chunk.chunkType,
      score: r.score,
      matchType: r.matchType,
      content: r.chunk.content,
      heading: r.chunk.heading,
    }));
    console.log(JSON.stringify(jsonResults, null, 2));
  } else {
    console.log(`\nResults for "${query}" (${results.length} results, ${durationMs}ms):\n`);
    for (let i = 0; i < results.length; i++) {
      const r = results[i];
      const lineRange = `${r.chunk.startLine}-${r.chunk.endLine}`;
      const snippet = r.chunk.content.split('\n')[0].slice(0, 80);
      console.log(`${i + 1}. [${r.score.toFixed(2)}] ${r.chunk.filePath}:${lineRange} (${r.chunk.chunkType})`);
      console.log(`   ${snippet}${r.chunk.content.split('\n')[0].length > 80 ? '...' : ''}`);
      console.log();
    }
  }

  // Cleanup
  if (vectorStore) await vectorStore.close();
  await ftsStore.close();
}

async function cmdStatus(_args: string[]): Promise<void> {
  const projectRoot = process.cwd();
  const config = loadConfig(projectRoot);
  const indexRoot = config.storage.index_root;
  const knowledgeDir = path.resolve(projectRoot, indexRoot);

  if (!fs.existsSync(knowledgeDir)) {
    console.log(`Status: NOT INITIALIZED (${indexRoot}/ does not exist)`);
    return;
  }

  const projectId = config.projects.length > 0 ? config.projects[0].name : path.basename(projectRoot);

  // file-map.json
  const fileMapPath = path.join(knowledgeDir, 'file-map.json');
  let fileCount = 0;
  if (fs.existsSync(fileMapPath)) {
    try {
      const data = JSON.parse(fs.readFileSync(fileMapPath, 'utf-8')) as Record<string, unknown>;
      fileCount = Object.keys(data).length;
    } catch { /* ignore */ }
  }

  // fts.db: chunk count
  const ftsDbPath = resolveFtsDbPath(config, knowledgeDir, projectId);
  let chunkCount = 0;
  if (fs.existsSync(ftsDbPath)) {
    try {
      const ftsStore = new FtsStore(ftsDbPath);
      const chunkStore = new ChunkStore(ftsStore.getDatabase());
      chunkCount = chunkStore.count();
      await ftsStore.close();
    } catch { /* ignore */ }
  }

  // vectors.lance: existence + vector count
  let vectorStatus = 'none';
  if (config.storage.vector_backend === 'lancedb') {
    const lanceDbPath = config.storage.lancedb?.path
      ? path.resolve(knowledgeDir, config.storage.lancedb.path.replace('{project}', projectId))
      : path.join(knowledgeDir, 'vectors.lance');
    if (fs.existsSync(lanceDbPath)) {
      vectorStatus = 'present';
    } else {
      vectorStatus = 'not created';
    }
  }

  // symbols.idx
  const symbolsPath = path.join(knowledgeDir, 'symbols.idx');
  let symbolCount = 0;
  if (fs.existsSync(symbolsPath)) {
    try {
      const content = fs.readFileSync(symbolsPath, 'utf-8');
      symbolCount = content.split('\n').filter(line => line.trim().length > 0).length;
    } catch { /* ignore */ }
  }

  // freshness.lock
  const freshnessPath = path.join(knowledgeDir, 'freshness.lock');
  let lastIndexed = 'never';
  let isDirty = false;
  if (fs.existsSync(freshnessPath)) {
    try {
      const freshData = JSON.parse(fs.readFileSync(freshnessPath, 'utf-8')) as Record<string, unknown>;
      lastIndexed = (freshData['indexed_at'] as string) ?? 'unknown';
      isDirty = (freshData['dirty'] as boolean) ?? false;
    } catch { /* ignore */ }
  }

  // Overall health
  let health = 'healthy';
  if (chunkCount === 0 && fileCount > 0) {
    health = 'degraded';
  }
  if (!fs.existsSync(ftsDbPath)) {
    health = 'stale';
  }
  if (isDirty) {
    health = health === 'healthy' ? 'degraded' : health;
  }

  console.log(`\nWKI Status: ${health.toUpperCase()}`);
  console.log(`  Index root:    ${indexRoot}/`);
  console.log(`  Files mapped:  ${fileCount}`);
  console.log(`  Chunks:        ${chunkCount}`);
  console.log(`  Symbols:       ${symbolCount}`);
  console.log(`  Vectors:       ${vectorStatus}`);
  console.log(`  Last indexed:  ${lastIndexed}`);
  console.log(`  Dirty:         ${isDirty ? 'yes' : 'no'}`);
  console.log();
}

async function cmdRebuild(args: string[]): Promise<void> {
  const projectRoot = args.find((a) => !a.startsWith('--'))
    ? path.resolve(args.find((a) => !a.startsWith('--'))!)
    : process.cwd();

  const config = loadConfig(projectRoot);
  const indexRoot = config.storage.index_root;
  const knowledgeDir = path.resolve(projectRoot, indexRoot);

  if (!fs.existsSync(knowledgeDir)) {
    console.error(`Error: ${indexRoot}/ does not exist. Run "wki init" first.`);
    process.exit(1);
  }

  const lock = new IndexLock(knowledgeDir);
  lock.acquire('rebuild');
  try {
    const rebuildVectors = args.includes('--vectors');
    const projectId =
      config.projects.length > 0
        ? config.projects[0].name
        : path.basename(projectRoot);

    // 1. Delete FTS DB
    const ftsDbPath = resolveFtsDbPath(config, knowledgeDir, projectId);
    if (fs.existsSync(ftsDbPath)) {
      fs.unlinkSync(ftsDbPath);
      console.log('Deleted fts.db');
    }
    // Also delete WAL/SHM files
    for (const suffix of ['-wal', '-shm']) {
      const walPath = ftsDbPath + suffix;
      if (fs.existsSync(walPath)) {
        fs.unlinkSync(walPath);
      }
    }

    // 2. Delete vector store if requested or doing full rebuild
    if (rebuildVectors || !args.includes('--fts-only')) {
      if (config.storage.vector_backend === 'lancedb') {
        const lanceDbPath = config.storage.lancedb?.path
          ? path.resolve(
              knowledgeDir,
              config.storage.lancedb.path.replace('{project}', projectId),
            )
          : path.join(knowledgeDir, 'vectors.lance');
        if (fs.existsSync(lanceDbPath)) {
          fs.rmSync(lanceDbPath, { recursive: true, force: true });
          console.log('Deleted vectors.lance/');
        }
      }
    }

    // 3. Run full reindex under the same lock (IndexLock is reentrant)
    console.log('Rebuilding index...');
    await cmdIndex(['--full', projectRoot]);
  } finally {
    lock.release();
  }
}

async function cmdEval(args: string[]): Promise<void> {
  const evalFlags = ['--top'];
  const goldSetPath = firstPositional(args, evalFlags);
  if (!goldSetPath) {
    console.error('Usage: wki eval <gold-set-path> [--top N]');
    process.exit(1);
  }

  const topK = parseInt(parseFlag(args, '--top', '10'), 10) || 10;
  const projectRoot = process.cwd();
  const config = loadConfig(projectRoot);
  const indexRoot = config.storage.index_root;
  const knowledgeDir = path.resolve(projectRoot, indexRoot);

  if (!fs.existsSync(knowledgeDir)) {
    console.error(`Error: ${indexRoot}/ does not exist. Run "wki init && wki index" first.`);
    process.exit(1);
  }

  // Load gold set
  const goldSetRaw = fs.readFileSync(path.resolve(goldSetPath), 'utf-8');
  const goldSet = JSON.parse(goldSetRaw) as import('./eval/types.js').GoldSet;

  const projectId =
    config.projects.length > 0
      ? config.projects[0].name
      : path.basename(projectRoot);

  // Set up search service
  const ftsStore = new FtsStore(resolveFtsDbPath(config, knowledgeDir, projectId));
  const chunkStore = new ChunkStore(ftsStore.getDatabase());

  let vectorStore: LanceVectorStore | null = null;
  let embeddingProvider: EmbeddingProvider | null = null;

  if (config.storage.vector_backend !== 'none') {
    try {
      embeddingProvider = await createEmbeddingProvider(config.embedding);
    } catch {
      console.warn('[wki] No embedding API key. Evaluating FTS-only.');
    }

    if (embeddingProvider && config.storage.vector_backend === 'lancedb') {
      const dims = embeddingProvider.dimensions;
      const lanceDbPath = config.storage.lancedb?.path
        ? path.resolve(
            knowledgeDir,
            config.storage.lancedb.path.replace('{project}', projectId),
          )
        : path.join(knowledgeDir, 'vectors.lance');
      if (fs.existsSync(lanceDbPath)) {
        vectorStore = new LanceVectorStore(lanceDbPath, dims);
        await vectorStore.init();
      }
    }
  }

  const searchService = new SearchService(
    ftsStore,
    vectorStore,
    chunkStore,
    embeddingProvider,
    config.search,
  );

  // Run evaluation
  const { evaluate } = await import('./eval/evaluator.js');
  const summary = await evaluate(searchService, goldSet, topK);

  // Print results
  console.log(`\nEvaluation: ${summary.goldSetName}`);
  console.log(`Queries: ${summary.queryCount}  |  nDCG@${topK}\n`);

  for (const result of summary.results) {
    const typeInfo = result.expectedType
      ? ` [${result.expectedType}→${result.actualType ?? '?'}]`
      : '';
    console.log(
      `  ${(result.queryIndex + 1).toString().padStart(2)}. [${result.ndcg.toFixed(3)}] "${result.query}"${typeInfo}  (${result.resultsCount} hits)`,
    );
  }

  console.log(`\n  Mean:   ${summary.meanNdcg.toFixed(3)}`);
  console.log(`  Median: ${summary.medianNdcg.toFixed(3)}`);
  console.log(`  Min:    ${summary.minNdcg.toFixed(3)}`);
  console.log(`  Max:    ${summary.maxNdcg.toFixed(3)}`);

  // Cleanup
  if (vectorStore) await vectorStore.close();
  await ftsStore.close();
}

async function cmdMcp(args: string[]): Promise<void> {
  const projectRoot = args[0] ? path.resolve(args[0]) : process.cwd();
  const { startServer } = await import('./mcp/server.js');
  await startServer(projectRoot);
}

async function handleCommand(command: Command, args: string[]): Promise<void> {
  switch (command) {
    case 'init':
      cmdInit(args);
      break;
    case 'scan':
      cmdScan(args);
      break;
    case 'index':
      await cmdIndex(args);
      break;
    case 'search':
      await cmdSearch(args);
      break;
    case 'status':
      await cmdStatus(args);
      break;
    case 'rebuild':
      await cmdRebuild(args);
      break;
    case 'eval':
      await cmdEval(args);
      break;
    case 'mcp':
      await cmdMcp(args);
      break;
  }
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const commandArg = args[0];

  if (!commandArg || commandArg === '--help' || commandArg === '-h') {
    printUsage();
    process.exit(0);
  }

  if (!COMMANDS.includes(commandArg as Command)) {
    console.error(`Unknown command: "${commandArg}"\n`);
    printUsage();
    process.exit(1);
  }

  await handleCommand(commandArg as Command, args.slice(1));
}

main().catch((err) => {
  console.error('Fatal error:', err instanceof Error ? err.message : String(err));
  process.exit(1);
});
