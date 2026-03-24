import { describe, it, expect, vi } from 'vitest';
import { buildContextBlock } from '../../src/context/context-builder.js';
import type { SearchService } from '../../src/search/search-service.js';
import type { SearchResult, Chunk } from '../../src/types/index.js';

function makeChunk(overrides: Partial<Chunk> = {}): Chunk {
  return {
    id: 'test:file.ts:0',
    projectId: 'test',
    filePath: 'src/services/PaymentService.ts',
    ordinal: 0,
    content: 'line1\nline2\nline3\nline4\nline5\nline6\nline7',
    heading: 'handlePayment',
    chunkType: 'function',
    startLine: 45,
    endLine: 80,
    tokenCount: 100,
    contentHash: 'abc123',
    ...overrides,
  };
}

function makeResult(overrides: Partial<SearchResult> = {}, chunkOverrides: Partial<Chunk> = {}): SearchResult {
  return {
    chunk: makeChunk(chunkOverrides),
    score: 0.85,
    matchType: 'fts',
    ...overrides,
  };
}

function mockSearchService(results: SearchResult[]): SearchService {
  return {
    search: vi.fn().mockResolvedValue(results),
  } as unknown as SearchService;
}

describe('buildContextBlock', () => {
  it('should return "No relevant context found." for empty results', async () => {
    const service = mockSearchService([]);
    const block = await buildContextBlock(service, 'test query');

    expect(block.markdown).toContain('No relevant context found.');
    expect(block.chunks).toHaveLength(0);
    expect(block.query).toBe('test query');
    expect(block.durationMs).toBeGreaterThanOrEqual(0);
  });

  it('should format a single chunk correctly with heading, type, and content', async () => {
    const result = makeResult();
    const service = mockSearchService([result]);
    const block = await buildContextBlock(service, 'payment');

    expect(block.markdown).toContain('## Relevant Context (auto-injected)');
    expect(block.markdown).toContain('### src/services/PaymentService.ts (lines 45-80)');
    expect(block.markdown).toContain('**handlePayment** \u2014 function');
    expect(block.markdown).toContain('```typescript');
    expect(block.markdown).toContain('line1');
    expect(block.chunks).toHaveLength(1);
  });

  it('should group multiple chunks from the same file', async () => {
    const r1 = makeResult({}, { ordinal: 0, startLine: 1, endLine: 10, heading: 'funcA' });
    const r2 = makeResult({}, { ordinal: 1, startLine: 20, endLine: 30, heading: 'funcB' });
    const service = mockSearchService([r1, r2]);
    const block = await buildContextBlock(service, 'test');

    // Both chunks appear under the same file path heading prefix
    const headingMatches = block.markdown.match(/### src\/services\/PaymentService\.ts/g);
    expect(headingMatches).toHaveLength(2);
    expect(block.chunks).toHaveLength(2);
  });

  it('should truncate content at maxContentLines', async () => {
    const result = makeResult({}, {
      content: 'a\nb\nc\nd\ne\nf\ng\nh',
    });
    const service = mockSearchService([result]);
    const block = await buildContextBlock(service, 'test', { maxContentLines: 3 });

    // Only first 3 lines should appear in content
    expect(block.markdown).toContain('a\nb\nc');
    expect(block.markdown).not.toContain('d\ne');
  });

  it('should show score when includeScore is true', async () => {
    const result = makeResult({ score: 0.923 });
    const service = mockSearchService([result]);
    const block = await buildContextBlock(service, 'test', { includeScore: true });

    expect(block.markdown).toContain('(score: 0.923)');
  });

  it('should not show score when includeScore is false', async () => {
    const result = makeResult({ score: 0.923 });
    const service = mockSearchService([result]);
    const block = await buildContextBlock(service, 'test', { includeScore: false });

    expect(block.markdown).not.toContain('score:');
  });

  it('should use code fences for code chunks', async () => {
    const result = makeResult({}, { chunkType: 'function', filePath: 'src/app.ts' });
    const service = mockSearchService([result]);
    const block = await buildContextBlock(service, 'test');

    expect(block.markdown).toContain('```typescript');
    expect(block.markdown).toContain('```');
  });

  it('should use blockquotes for markdown chunks', async () => {
    const result = makeResult({}, {
      chunkType: 'markdown-section',
      filePath: 'docs/guide.md',
      content: 'First line\nSecond line\nThird line',
      heading: 'Guide Section',
    });
    const service = mockSearchService([result]);
    const block = await buildContextBlock(service, 'test');

    expect(block.markdown).toContain('> First line');
    expect(block.markdown).toContain('> Second line');
    expect(block.markdown).not.toContain('```');
  });

  it('should group chunks from two different files with separate file headings', async () => {
    const r1 = makeResult({}, { filePath: 'src/alpha.ts', ordinal: 0, heading: 'funcAlpha' });
    const r2 = makeResult({}, { filePath: 'src/beta.ts', ordinal: 0, heading: 'funcBeta' });
    const service = mockSearchService([r1, r2]);
    const block = await buildContextBlock(service, 'test');

    expect(block.markdown).toContain('### src/alpha.ts');
    expect(block.markdown).toContain('### src/beta.ts');
    expect(block.chunks).toHaveLength(2);
  });

  it('should use python code fence for .py files', async () => {
    const result = makeResult({}, {
      filePath: 'scripts/run.py',
      chunkType: 'function',
      content: 'def run():\n    pass',
      heading: 'run',
    });
    const service = mockSearchService([result]);
    const block = await buildContextBlock(service, 'test');

    expect(block.markdown).toContain('```python');
  });

  it('should use bare code fence for unknown extension', async () => {
    const result = makeResult({}, {
      filePath: 'data/config.xyz',
      chunkType: 'line-block',
      content: 'key = value',
      heading: 'config',
    });
    const service = mockSearchService([result]);
    const block = await buildContextBlock(service, 'test');

    // Should have a code fence with no language identifier
    expect(block.markdown).toMatch(/```\n/);
  });

  it('should handle maxContentLines: 0 by showing no content lines', async () => {
    const result = makeResult({}, {
      content: 'line1\nline2\nline3',
    });
    const service = mockSearchService([result]);
    const block = await buildContextBlock(service, 'test', { maxContentLines: 0 });

    // With 0 max lines, content between fences should be empty
    expect(block.markdown).toContain('```typescript\n\n```');
  });
});
