/**
 * Unused Exports Analyzer.
 * Combines symbols.idx (exported symbols) with deps.graph (import relationships)
 * to find exported symbols that are never imported by other files.
 *
 * Supports Rule #1 (Step 0): identify dead exports before refactoring.
 *
 * Limitations:
 * - deps.graph tracks file-level edges only (no specifier-level tracking yet)
 * - Only detects files with zero importers (file-level unused)
 * - Dynamic imports, re-exports via barrel files, and runtime usage are not tracked
 */

import fs from 'node:fs';
import type { SymbolInfo } from '../types/index.js';
import { DepsGraphImpl } from '../core/deps-graph.js';

export interface UnusedExportEntry {
  symbol: SymbolInfo;
  /** Why this export is flagged. */
  reason: 'no-importers' | 'zero-reverse-edges';
}

export interface UnusedExportReport {
  /** Total exported symbols analyzed. */
  totalExported: number;
  /** Files with no importers at all. */
  orphanFiles: string[];
  /** Individual unused export entries. */
  unused: UnusedExportEntry[];
  /** Analysis duration in ms. */
  durationMs: number;
}

export interface AnalyzeOptions {
  /** Only analyze files matching this path substring. */
  filePath?: string;
  /** Only flag files with more than this many LOC (default: 0 = all files). */
  minLoc?: number;
}

/**
 * Analyze exported symbols to find those with no importers.
 */
export function analyzeUnusedExports(
  symbolsIdxPath: string,
  depsGraphPath: string,
  options: AnalyzeOptions = {},
): UnusedExportReport {
  const startTime = Date.now();

  // Load symbols
  const symbols: SymbolInfo[] = [];
  if (fs.existsSync(symbolsIdxPath)) {
    const seen = new Set<string>();
    const content = fs.readFileSync(symbolsIdxPath, 'utf-8');
    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const sym = JSON.parse(trimmed) as SymbolInfo;
        const key = `${sym.name}:${sym.kind}:${sym.filePath}:${sym.startLine}`;
        if (seen.has(key)) continue;
        seen.add(key);
        symbols.push(sym);
      } catch { /* skip */ }
    }
  }

  // Load deps graph
  const graph = new DepsGraphImpl();
  if (fs.existsSync(depsGraphPath)) {
    const data = fs.readFileSync(depsGraphPath, 'utf-8');
    graph.load(data);
  }

  // Filter to exported symbols only
  let exported = symbols.filter(s => s.exported);

  // Apply file path filter
  if (options.filePath) {
    exported = exported.filter(s => s.filePath.includes(options.filePath!));
  }

  // Apply min LOC filter (use endLine of last symbol in file as proxy)
  if (options.minLoc && options.minLoc > 0) {
    const fileLoc = new Map<string, number>();
    for (const sym of symbols) {
      const current = fileLoc.get(sym.filePath) ?? 0;
      if (sym.endLine > current) {
        fileLoc.set(sym.filePath, sym.endLine);
      }
    }
    exported = exported.filter(s => (fileLoc.get(s.filePath) ?? 0) >= options.minLoc!);
  }

  // Find orphan files: files with exported symbols but no importers
  const exportedFileSet = new Set(exported.map(s => s.filePath));
  const orphanFiles: string[] = [];

  for (const filePath of exportedFileSet) {
    const importers = graph.getImporters(filePath);
    if (importers.length === 0) {
      orphanFiles.push(filePath);
    }
  }

  // Build unused entries: all exported symbols from orphan files
  const orphanSet = new Set(orphanFiles);
  const unused: UnusedExportEntry[] = exported
    .filter(s => orphanSet.has(s.filePath))
    .map(s => ({ symbol: s, reason: 'no-importers' as const }));

  return {
    totalExported: exported.length,
    orphanFiles,
    unused,
    durationMs: Date.now() - startTime,
  };
}
