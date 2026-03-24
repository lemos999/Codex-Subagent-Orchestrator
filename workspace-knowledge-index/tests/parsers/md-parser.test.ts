import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { MdParser } from '../../src/parsers/md-parser.js';

describe('MdParser', () => {
  let parser: MdParser;

  beforeEach(() => {
    parser = new MdParser();
  });

  afterEach(() => {
    parser = new MdParser();
  });

  it('chunks markdown by h1, h2, and h3 heading boundaries', () => {
    const content = [
      '# Overview',
      'Intro paragraph.',
      '## Details',
      'More detail.',
      '### Deep Dive',
      'Nested section body.',
    ].join('\n');

    const chunks = parser.parse('/virtual/guide.md', content);

    expect(chunks).toHaveLength(3);
    expect(chunks.map((chunk) => [chunk.heading, chunk.startLine, chunk.endLine])).toEqual([
      ['Overview', 1, 2],
      ['Details', 3, 4],
      ['Deep Dive', 5, 6],
    ]);
  });

  it('emits frontmatter as a separate chunk', () => {
    const content = [
      '---',
      'title: Sample Doc',
      'owner: tests',
      '---',
      '',
      '# Heading',
      'Body text.',
    ].join('\n');

    const chunks = parser.parse('/virtual/frontmatter.md', content);

    expect(chunks).toHaveLength(2);
    expect(chunks[0]).toMatchObject({
      heading: 'frontmatter',
      startLine: 1,
      endLine: 4,
    });
    expect(chunks[0]?.content).toContain('title: Sample Doc');
    expect(chunks[1]).toMatchObject({
      heading: 'Heading',
      startLine: 6,
      endLine: 7,
    });
  });

  it('returns a single chunk when the markdown has no headings', () => {
    const content = [
      'Plain paragraph.',
      '',
      'Another paragraph without headings.',
    ].join('\n');

    const chunks = parser.parse('/virtual/plain.md', content);

    expect(chunks).toHaveLength(1);
    expect(chunks[0]).toMatchObject({
      heading: undefined,
      chunkType: 'markdown-section',
      startLine: 1,
      endLine: 3,
    });
    expect(chunks[0]?.content).toContain('Another paragraph without headings.');
  });

  it('keeps GFM tables and task lists inside the heading section', () => {
    const content = [
      '# Release Plan',
      '',
      '| Task | Status |',
      '| ---- | ------ |',
      '| Ship | Done |',
      '',
      '- [x] build',
      '- [ ] deploy',
    ].join('\n');

    const chunks = parser.parse('/virtual/gfm.md', content);

    expect(chunks).toHaveLength(1);
    expect(chunks[0]?.heading).toBe('Release Plan');
    expect(chunks[0]?.content).toContain('| Task | Status |');
    expect(chunks[0]?.content).toContain('- [ ] deploy');
  });

  it('returns no chunks for an empty file', () => {
    const chunks = parser.parse('/virtual/empty.md', '');

    expect(chunks).toEqual([]);
  });
});
