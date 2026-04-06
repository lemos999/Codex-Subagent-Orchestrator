/**
 * Symbol Search Service.
 * Loads symbols.idx (JSONL) and provides fast in-memory search
 * by name, kind, file path, and export status.
 */

import fs from 'node:fs';
import type { SymbolInfo, SymbolSearchOptions, SymbolSearchResult } from '../types/index.js';

export class SymbolSearch {
  private symbols: SymbolInfo[] = [];

  constructor(symbolsIdxPath: string) {
    if (!fs.existsSync(symbolsIdxPath)) {
      return;
    }
    const content = fs.readFileSync(symbolsIdxPath, 'utf-8');
    const seen = new Set<string>();
    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const sym = JSON.parse(trimmed) as SymbolInfo;
        // Deduplicate by name+kind+filePath+startLine
        const key = `${sym.name}:${sym.kind}:${sym.filePath}:${sym.startLine}`;
        if (seen.has(key)) continue;
        seen.add(key);
        this.symbols.push(sym);
      } catch {
        // skip malformed lines
      }
    }
  }

  get count(): number {
    return this.symbols.length;
  }

  /**
   * Search symbols with flexible filtering and scoring.
   */
  search(options: SymbolSearchOptions): SymbolSearchResult[] {
    const {
      name,
      nameMode = 'contains',
      kind,
      exportedOnly = false,
      filePath,
      topK = 20,
    } = options;

    let nameRegex: RegExp | null = null;
    if (name) {
      switch (nameMode) {
        case 'exact':
          nameRegex = new RegExp(`^${escapeRegex(name)}$`, 'i');
          break;
        case 'prefix':
          nameRegex = new RegExp(`^${escapeRegex(name)}`, 'i');
          break;
        case 'contains':
          nameRegex = new RegExp(escapeRegex(name), 'i');
          break;
        case 'regex':
          try {
            nameRegex = new RegExp(name, 'i');
          } catch {
            nameRegex = new RegExp(escapeRegex(name), 'i');
          }
          break;
      }
    }

    const results: SymbolSearchResult[] = [];

    for (const sym of this.symbols) {
      // Filter: kind
      if (kind && sym.kind !== kind) continue;

      // Filter: exported only
      if (exportedOnly && !sym.exported) continue;

      // Filter: file path substring
      if (filePath && !sym.filePath.includes(filePath)) continue;

      // Filter + score: name
      let score = 0.5; // base score for non-name queries
      if (nameRegex) {
        if (!nameRegex.test(sym.name)) continue;

        // Score by match quality
        if (name) {
          if (sym.name === name) {
            score = 1.0; // exact match
          } else if (sym.name.toLowerCase() === name.toLowerCase()) {
            score = 0.95; // case-insensitive exact
          } else if (sym.name.startsWith(name)) {
            score = 0.8; // prefix match
          } else if (sym.name.toLowerCase().startsWith(name.toLowerCase())) {
            score = 0.75;
          } else {
            score = 0.5; // contains/regex match
          }
        }
      }

      // Boost exported symbols slightly
      if (sym.exported) {
        score = Math.min(1.0, score + 0.05);
      }

      results.push({ symbol: sym, score });
    }

    // Sort by score descending, then by name alphabetically
    results.sort((a, b) => b.score - a.score || a.symbol.name.localeCompare(b.symbol.name));

    return results.slice(0, topK);
  }

  /**
   * Find all references to a symbol name across the index.
   * Useful for rename operations (Rule #10: No Semantic Search).
   * Returns symbols that match by name in any position (callers, types, re-exports).
   */
  findReferences(symbolName: string): SymbolSearchResult[] {
    return this.search({
      name: symbolName,
      nameMode: 'exact',
      topK: 100,
    });
  }

  /**
   * List all exported symbols from a specific file.
   */
  listExports(filePath: string): SymbolInfo[] {
    return this.symbols.filter(s => s.exported && s.filePath.includes(filePath));
  }

  /**
   * Get all unique symbol kinds in the index.
   */
  getKinds(): string[] {
    return [...new Set(this.symbols.map(s => s.kind))].sort();
  }
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
