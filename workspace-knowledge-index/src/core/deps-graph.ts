import fs from 'node:fs';
import path from 'node:path';
import { normalizePath, toIndexPath } from '../utils/path.js';
import type { ImportInfo } from '../types/index.js';

const TS_EXTENSIONS = ['.ts', '.tsx', '.js', '.jsx'];

/**
 * Directed dependency graph based on import relationships.
 * Tracks forward (imports) and reverse (importers) edges.
 */
export class DepsGraphImpl {
  private edges: Map<string, Set<string>> = new Map();
  private reverseEdges: Map<string, Set<string>> = new Map();

  constructor(private projectRoot?: string) {}

  /** Add a directed edge: `from` imports `to`. */
  addEdge(from: string, to: string): void {
    const f = this.normalizeGraphPath(from);
    const t = this.normalizeGraphPath(to);

    if (!this.edges.has(f)) {
      this.edges.set(f, new Set());
    }
    this.edges.get(f)!.add(t);

    if (!this.reverseEdges.has(t)) {
      this.reverseEdges.set(t, new Set());
    }
    this.reverseEdges.get(t)!.add(f);
  }

  /** Files that `filePath` imports. */
  getImports(filePath: string): string[] {
    const key = this.normalizeGraphPath(filePath);
    const set = this.edges.get(key);
    return set ? [...set] : [];
  }

  /** Files that import `filePath`. */
  getImporters(filePath: string): string[] {
    const key = this.normalizeGraphPath(filePath);
    const set = this.reverseEdges.get(key);
    return set ? [...set] : [];
  }

  /** BFS walk from startFile up to maxDepth. Returns at most 100 nodes. */
  walk(startFile: string, maxDepth: number): string[] {
    const start = this.normalizeGraphPath(startFile);
    const visited = new Set<string>();
    const result: string[] = [];
    const queue: Array<{ file: string; depth: number }> = [{ file: start, depth: 0 }];
    const MAX_NODES = 100;

    visited.add(start);

    while (queue.length > 0 && result.length < MAX_NODES) {
      const current = queue.shift()!;

      if (current.file !== start) {
        result.push(current.file);
      }

      if (current.depth >= maxDepth) continue;

      const neighbors = this.edges.get(current.file);
      if (!neighbors) continue;

      for (const neighbor of neighbors) {
        if (visited.has(neighbor)) continue;
        if (result.length >= MAX_NODES) break;
        visited.add(neighbor);
        queue.push({ file: neighbor, depth: current.depth + 1 });
      }
    }

    return result;
  }

  /** Serialize to JSON adjacency list. */
  serialize(): string {
    const obj: Record<string, string[]> = {};
    for (const [key, set] of this.edges) {
      obj[key] = [...set];
    }
    return JSON.stringify(obj, null, 2);
  }

  /** Load from a JSON adjacency list string. */
  load(data: string): void {
    this.edges.clear();
    this.reverseEdges.clear();

    const obj = JSON.parse(data) as Record<string, string[]>;
    for (const [from, targets] of Object.entries(obj)) {
      for (const to of targets) {
        this.addEdge(from, to);
      }
    }
  }

  /** Save the graph to a file. */
  save(filePath: string): void {
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(filePath, this.serialize(), 'utf-8');
  }

  /** Total number of edges. */
  get size(): number {
    let count = 0;
    for (const set of this.edges.values()) {
      count += set.size;
    }
    return count;
  }

  private normalizeGraphPath(filePath: string): string {
    return this.projectRoot ? toIndexPath(this.projectRoot, filePath) : normalizePath(filePath);
  }

  // ----------------------------------------------------------------
  // Static helper: resolve import specifier to file path
  // ----------------------------------------------------------------

  /**
   * Resolve a module specifier to an absolute file path.
   * Returns null for non-relative (node_modules) imports.
   */
  static resolveImportPath(importSpecifier: string, fromFile: string): string | null {
    // Only resolve relative imports
    if (!importSpecifier.startsWith('.')) {
      return null;
    }

    const fromDir = path.dirname(fromFile);
    const resolved = path.resolve(fromDir, importSpecifier);
    const normalized = normalizePath(resolved);

    // Try exact path first
    if (fs.existsSync(resolved) && fs.statSync(resolved).isFile()) {
      return normalized;
    }

    // Try with TS extensions
    for (const ext of TS_EXTENSIONS) {
      const withExt = resolved + ext;
      if (fs.existsSync(withExt)) {
        return normalizePath(withExt);
      }
    }

    // Try /index with extensions
    for (const ext of TS_EXTENSIONS) {
      const indexPath = path.join(resolved, 'index' + ext);
      if (fs.existsSync(indexPath)) {
        return normalizePath(indexPath);
      }
    }

    return null;
  }

  /**
   * Build edges from a list of ImportInfo entries.
   * Resolves relative import specifiers to absolute file paths.
   */
  addFromImports(imports: ImportInfo[], sourceFilePath: string): void {
    for (const imp of imports) {
      const resolved = DepsGraphImpl.resolveImportPath(imp.target, sourceFilePath);
      if (resolved) {
        this.addEdge(normalizePath(sourceFilePath), resolved);
      }
    }
  }
}
