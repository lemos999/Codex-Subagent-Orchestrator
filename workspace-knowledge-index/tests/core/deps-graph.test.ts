import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { DepsGraphImpl } from '../../src/core/deps-graph.js';

describe('DepsGraphImpl', () => {
  let graph: DepsGraphImpl;
  let tempDir: string;

  beforeEach(() => {
    graph = new DepsGraphImpl();
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));
  });

  afterEach(() => {
    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  it('tracks imports and importers for directed edges', () => {
    graph.addEdge('/repo/src/a.ts', '/repo/src/b.ts');
    graph.addEdge('/repo/src/a.ts', '/repo/src/c.ts');
    graph.addEdge('/repo/src/d.ts', '/repo/src/b.ts');

    expect(graph.getImports('/repo/src/a.ts')).toEqual(['/repo/src/b.ts', '/repo/src/c.ts']);
    expect(graph.getImporters('/repo/src/b.ts')).toEqual(['/repo/src/a.ts', '/repo/src/d.ts']);
  });

  it('walks dependencies breadth-first up to the requested depth', () => {
    graph.addEdge('/repo/src/a.ts', '/repo/src/b.ts');
    graph.addEdge('/repo/src/a.ts', '/repo/src/c.ts');
    graph.addEdge('/repo/src/b.ts', '/repo/src/d.ts');
    graph.addEdge('/repo/src/c.ts', '/repo/src/e.ts');

    expect(graph.walk('/repo/src/a.ts', 1)).toEqual(['/repo/src/b.ts', '/repo/src/c.ts']);
    expect(graph.walk('/repo/src/a.ts', 2)).toEqual([
      '/repo/src/b.ts',
      '/repo/src/c.ts',
      '/repo/src/d.ts',
      '/repo/src/e.ts',
    ]);
  });

  it('round-trips through serialize and load', () => {
    graph.addEdge('/repo/src/a.ts', '/repo/src/b.ts');
    graph.addEdge('/repo/src/b.ts', '/repo/src/c.ts');

    const serialized = graph.serialize();
    const loadedGraph = new DepsGraphImpl();
    loadedGraph.load(serialized);

    expect(loadedGraph.getImports('/repo/src/a.ts')).toEqual(['/repo/src/b.ts']);
    expect(loadedGraph.getImports('/repo/src/b.ts')).toEqual(['/repo/src/c.ts']);
    expect(loadedGraph.getImporters('/repo/src/c.ts')).toEqual(['/repo/src/b.ts']);
  });

  it('stores project-relative paths when a project root is provided', () => {
    const rootedGraph = new DepsGraphImpl(tempDir);
    const source = path.join(tempDir, 'src/a.ts');
    const target = path.join(tempDir, 'src/b.ts');

    rootedGraph.addEdge(source, target);

    expect(rootedGraph.getImports('src/a.ts')).toEqual(['src/b.ts']);
    expect(rootedGraph.serialize()).not.toContain(tempDir.replace(/\\/g, '/'));
  });

  it('returns empty results for an empty graph', () => {
    expect(graph.getImports('/repo/src/missing.ts')).toEqual([]);
    expect(graph.getImporters('/repo/src/missing.ts')).toEqual([]);
    expect(graph.walk('/repo/src/missing.ts', 3)).toEqual([]);
    expect(graph.serialize()).toBe('{}');
  });

  it('caps bfs traversal results at 100 nodes', () => {
    for (let index = 0; index < 150; index += 1) {
      graph.addEdge('/repo/src/root.ts', `/repo/src/node-${index}.ts`);
    }

    const walked = graph.walk('/repo/src/root.ts', 1);

    expect(walked).toHaveLength(100);
    expect(walked[0]).toBe('/repo/src/node-0.ts');
    expect(walked[99]).toBe('/repo/src/node-99.ts');
  });
});
