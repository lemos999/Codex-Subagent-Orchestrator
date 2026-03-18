import type { SearchService } from '../search/search-service.js';
import type { SearchResult } from '../types/index.js';

// ============================================================
// Context Block Builder
// ============================================================

export interface ContextBlockOptions {
  topK?: number;           // default 10
  maxContentLines?: number; // max lines per chunk snippet, default 5
  includeScore?: boolean;   // show score in output, default false
}

export interface ContextBlock {
  markdown: string;       // formatted "## Relevant Context" block
  chunks: SearchResult[]; // raw results for programmatic use
  query: string;
  durationMs: number;
}

/**
 * Build a formatted context block from search results.
 * Groups chunks by file path, truncates content, and formats
 * code chunks with code fences and markdown chunks with blockquotes.
 */
export async function buildContextBlock(
  searchService: SearchService,
  query: string,
  options?: ContextBlockOptions,
): Promise<ContextBlock> {
  const topK = options?.topK ?? 10;
  const maxContentLines = options?.maxContentLines ?? 5;
  const includeScore = options?.includeScore ?? false;

  const startTime = Date.now();

  const results = await searchService.search(query, {
    topK,
    includeContent: true,
  });

  const durationMs = Date.now() - startTime;

  if (results.length === 0) {
    return {
      markdown: '## Relevant Context (auto-injected)\n\nNo relevant context found.\n',
      chunks: [],
      query,
      durationMs,
    };
  }

  // Group by file path, preserving insertion order
  const grouped = new Map<string, SearchResult[]>();
  for (const result of results) {
    const filePath = result.chunk.filePath;
    let group = grouped.get(filePath);
    if (!group) {
      group = [];
      grouped.set(filePath, group);
    }
    group.push(result);
  }

  const sections: string[] = ['## Relevant Context (auto-injected)\n'];

  for (const [filePath, fileResults] of grouped) {
    for (const result of fileResults) {
      const { chunk, score } = result;
      const lineRange = `lines ${chunk.startLine}-${chunk.endLine}`;
      const heading = chunk.heading ?? chunk.chunkType;
      const scoreSuffix = includeScore ? ` (score: ${score.toFixed(3)})` : '';

      sections.push(`### ${filePath} (${lineRange})`);
      sections.push(`**${heading}** \u2014 ${chunk.chunkType}${scoreSuffix}`);

      const contentLines = chunk.content.split('\n');
      const truncatedLines = contentLines.slice(0, maxContentLines);
      const truncatedContent = truncatedLines.join('\n');

      if (isMarkdownChunk(chunk.chunkType)) {
        // Use blockquotes for markdown chunks
        const quoted = truncatedLines.map((line) => `> ${line}`).join('\n');
        sections.push(quoted);
      } else {
        // Use code fences for code chunks
        const lang = detectCodeLanguage(filePath);
        sections.push(`\`\`\`${lang}\n${truncatedContent}\n\`\`\``);
      }

      sections.push('');
    }
  }

  return {
    markdown: sections.join('\n'),
    chunks: results,
    query,
    durationMs,
  };
}

function isMarkdownChunk(chunkType: string): boolean {
  return chunkType === 'markdown-section';
}

function detectCodeLanguage(filePath: string): string {
  const ext = filePath.split('.').pop()?.toLowerCase() ?? '';
  const langMap: Record<string, string> = {
    ts: 'typescript',
    tsx: 'typescript',
    js: 'javascript',
    jsx: 'javascript',
    py: 'python',
    rs: 'rust',
    go: 'go',
    java: 'java',
    rb: 'ruby',
    cs: 'csharp',
    cpp: 'cpp',
    c: 'c',
    sh: 'bash',
    yaml: 'yaml',
    yml: 'yaml',
    json: 'json',
    toml: 'toml',
    sql: 'sql',
  };
  return langMap[ext] ?? '';
}
