import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { LineParser } from '../../src/parsers/line-parser.js';

describe('LineParser', () => {
  let parser: LineParser;

  beforeEach(() => {
    parser = new LineParser();
  });

  afterEach(() => {
    parser = new LineParser();
  });

  it('returns a single chunk for files shorter than 200 lines', () => {
    const content = makeLines(199);

    const chunks = parser.parse('/virtual/short.txt', content);

    expect(chunks).toHaveLength(1);
    expect(chunks[0]).toMatchObject({
      chunkType: 'line-block',
      startLine: 1,
      endLine: 199,
    });
    expect(chunks[0]?.content.split('\n')).toHaveLength(199);
  });

  it('splits long files with a 50-line overlap by default', () => {
    const content = makeLines(260);

    const chunks = parser.parse('/virtual/long.txt', content);

    expect(chunks).toHaveLength(2);
    expect(chunks.map((chunk) => [chunk.startLine, chunk.endLine])).toEqual([
      [1, 200],
      [151, 260],
    ]);
    expect(chunks[1]?.content.split('\n')[0]).toBe('line 151');
  });

  it('returns no chunks for an empty file', () => {
    const chunks = parser.parse('/virtual/empty.txt', '');

    expect(chunks).toEqual([]);
  });

  it('supports custom maxLines and overlapLines settings', () => {
    const customParser = new LineParser(3, 1);
    const content = makeLines(7);

    const chunks = customParser.parse('/virtual/custom.txt', content);

    expect(chunks).toHaveLength(3);
    expect(chunks.map((chunk) => [chunk.startLine, chunk.endLine])).toEqual([
      [1, 3],
      [3, 5],
      [5, 7],
    ]);
    expect(chunks[1]?.content).toBe(['line 3', 'line 4', 'line 5'].join('\n'));
  });

  function makeLines(count: number): string {
    return Array.from({ length: count }, (_, index) => `line ${index + 1}`).join('\n');
  }
});
