import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkFrontmatter from 'remark-frontmatter';
import type { Root, Heading } from 'mdast';
import type { Node } from 'unist';
import type { RawChunk } from '../types/index.js';
import type { FileParser } from '../interfaces/parser.js';

// remark-frontmatter extends mdast with yaml/toml node types.
// We use unist Node for iteration to avoid missing augmentation issues.

/**
 * Markdown parser using remark.
 * Chunks content by heading boundaries.
 */
export class MdParser implements FileParser {
  readonly supportedExtensions = ['.md', '.mdx'];

  parse(filePath: string, content: string): RawChunk[] {
    const tree = unified()
      .use(remarkParse)
      .use(remarkGfm)
      .use(remarkFrontmatter, ['yaml', 'toml'])
      .parse(content) as Root;

    const lines = content.split('\n');
    const totalLines = lines.length;
    const chunks: RawChunk[] = [];
    let ordinal = 0;

    interface Section {
      heading: string | undefined;
      startLine: number;
      endLine: number;
    }

    const sections: Section[] = [];
    let currentSection: Section | null = null;

    const children = tree.children as Node[];

    for (const node of children) {
      const nodeType = node.type;

      if (nodeType === 'yaml' || nodeType === 'toml') {
        // Frontmatter as separate section
        if (node.position) {
          sections.push({
            heading: 'frontmatter',
            startLine: node.position.start.line,
            endLine: node.position.end.line,
          });
        }
        continue;
      }

      if (nodeType === 'heading' && node.position) {
        // Close previous section
        if (currentSection) {
          currentSection.endLine = node.position.start.line - 1;
          if (currentSection.endLine >= currentSection.startLine) {
            sections.push(currentSection);
          }
        }
        // Start new section from this heading
        const headingText = this.extractHeadingText(node as Heading);
        currentSection = {
          heading: headingText,
          startLine: node.position.start.line,
          endLine: totalLines,
        };
        continue;
      }

      // Non-heading node: if no current section, start one (content before first heading)
      if (!currentSection && node.position) {
        currentSection = {
          heading: undefined,
          startLine: node.position.start.line,
          endLine: totalLines,
        };
      }
    }

    // Close the last section
    if (currentSection) {
      currentSection.endLine = totalLines;
      sections.push(currentSection);
    }

    // If no sections at all and content is non-empty, make one chunk
    if (sections.length === 0 && content.trim().length > 0) {
      chunks.push({
        filePath,
        ordinal: 0,
        content: content,
        chunkType: 'markdown-section',
        startLine: 1,
        endLine: totalLines,
      });
      return chunks;
    }

    // Convert sections to RawChunks
    for (const section of sections) {
      const sectionContent = lines.slice(section.startLine - 1, section.endLine).join('\n').trim();
      if (sectionContent.length === 0) continue;

      chunks.push({
        filePath,
        ordinal: ordinal++,
        content: sectionContent,
        heading: section.heading,
        chunkType: 'markdown-section',
        startLine: section.startLine,
        endLine: section.endLine,
      });
    }

    return chunks;
  }

  private extractHeadingText(heading: Heading): string {
    const parts: string[] = [];
    for (const child of heading.children) {
      if ('value' in child) {
        parts.push(child.value);
      } else if ('children' in child) {
        // Recurse into nested inline nodes (e.g., emphasis, strong)
        const nested = child as unknown as { children: Array<{ value?: string }> };
        for (const grandchild of nested.children) {
          if (grandchild.value) parts.push(grandchild.value);
        }
      }
    }
    return parts.join('');
  }
}
