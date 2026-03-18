import type { RawChunk } from '../types/index.js';
import type { FileParser } from '../interfaces/parser.js';

/**
 * Line-based fallback parser.
 * Splits content into fixed-size chunks with overlap.
 */
export class LineParser implements FileParser {
  readonly supportedExtensions = ['*'];

  constructor(
    private maxLines: number = 200,
    private overlapLines: number = 50,
  ) {}

  parse(filePath: string, content: string): RawChunk[] {
    const lines = content.split('\n');
    const totalLines = lines.length;

    if (totalLines === 0) return [];

    const chunks: RawChunk[] = [];
    let ordinal = 0;
    let start = 0;

    while (start < totalLines) {
      const end = Math.min(start + this.maxLines, totalLines);
      const chunkContent = lines.slice(start, end).join('\n');

      if (chunkContent.trim().length > 0) {
        chunks.push({
          filePath,
          ordinal: ordinal++,
          content: chunkContent,
          chunkType: 'line-block',
          startLine: start + 1,
          endLine: end,
        });
      }

      if (end >= totalLines) break;

      // Advance by (maxLines - overlapLines) to create overlap
      const step = this.maxLines - this.overlapLines;
      start += step > 0 ? step : this.maxLines;
    }

    return chunks;
  }
}
