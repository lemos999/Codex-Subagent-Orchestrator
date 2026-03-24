/**
 * local-files tracker.
 *
 * Reads a directory of per-issue files (*.json, *.md, *.txt).
 * Markdown files support optional YAML front matter.
 */

import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import type { RawIssue } from '../queue-types.js';
import type { Tracker } from './tracker.js';

export class LocalFilesTracker implements Tracker {
  constructor(
    private sourceDir: string,
    private configDir: string,
    private includeGlobs: string[] = ['*.md', '*.json'],
    private recurse: boolean = true,
  ) {}

  async fetchRawIssues(): Promise<RawIssue[]> {
    const dirPath = path.resolve(this.configDir, this.sourceDir);

    let entries: string[];
    try {
      entries = await this.listFiles(dirPath);
    } catch {
      return [];
    }

    const issues: RawIssue[] = [];
    for (const filePath of entries) {
      try {
        const issue = await this.parseFile(filePath);
        if (issue) issues.push(issue);
      } catch {
        // Skip unparseable files
      }
    }
    return issues;
  }

  private async listFiles(dir: string): Promise<string[]> {
    const results: string[] = [];
    const dirents = await fs.readdir(dir, { withFileTypes: true });

    for (const dirent of dirents) {
      const fullPath = path.join(dir, dirent.name);
      if (dirent.isDirectory() && this.recurse) {
        const sub = await this.listFiles(fullPath);
        results.push(...sub);
      } else if (dirent.isFile() && this.matchesGlob(dirent.name)) {
        results.push(fullPath);
      }
    }
    return results;
  }

  private matchesGlob(filename: string): boolean {
    const ext = path.extname(filename).toLowerCase();
    return this.includeGlobs.some((glob) => {
      if (glob.startsWith('*.')) return ext === glob.slice(1);
      return filename === glob;
    });
  }

  private async parseFile(filePath: string): Promise<RawIssue | null> {
    const content = await fs.readFile(filePath, 'utf8');
    const ext = path.extname(filePath).toLowerCase();

    if (ext === '.json') {
      return this.parseJsonFile(content, filePath);
    }
    if (ext === '.md' || ext === '.txt') {
      return this.parseMarkdownFile(content, filePath);
    }
    return null;
  }

  private parseJsonFile(content: string, filePath: string): RawIssue | null {
    const parsed = JSON.parse(content) as unknown;
    if (typeof parsed !== 'object' || parsed === null) return null;

    const issue = parsed as RawIssue;
    // Set source_path for tracking
    issue.source_path = filePath;
    issue.source_kind = 'local-file-json';

    // Derive identifier from filename if not present
    if (!issue.identifier && !issue.id && !issue.key) {
      issue.identifier = path.basename(filePath, path.extname(filePath));
    }
    return issue;
  }

  private parseMarkdownFile(content: string, filePath: string): RawIssue {
    const issue: RawIssue = {
      source_path: filePath,
      source_kind: 'local-file-md',
    };

    // Parse optional YAML front matter
    const frontMatterMatch = content.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
    if (frontMatterMatch) {
      const frontMatter = frontMatterMatch[1]!;
      const body = frontMatterMatch[2]!.trim();

      // Simple YAML parser for key: value pairs
      for (const line of frontMatter.split('\n')) {
        const match = line.match(/^(\w+):\s*(.+)$/);
        if (match) {
          const [, key, value] = match;
          if (key === 'priority') {
            issue[key!] = parseInt(value!, 10);
          } else if (key === 'blocked_by' || key === 'requested_deliverables' || key === 'labels') {
            // Handle inline array: [a, b, c]
            const arrayMatch = value!.match(/^\[(.+)\]$/);
            if (arrayMatch) {
              issue[key!] = arrayMatch[1]!.split(',').map((s) => s.trim().replace(/^['"]|['"]$/g, ''));
            }
          } else {
            issue[key!] = value!.trim();
          }
        }
        // Handle YAML list items (  - value)
        const listMatch = line.match(/^\s+-\s+(.+)$/);
        if (listMatch) {
          // Attach to last key that expects an array
          const lastArrayKey = ['blocked_by', 'requested_deliverables', 'labels'].find(
            (k) => Array.isArray(issue[k]),
          );
          if (lastArrayKey) {
            (issue[lastArrayKey] as string[]).push(listMatch[1]!.trim());
          }
        }
      }

      // Title from first heading in body
      const headingMatch = body.match(/^#\s+(.+)$/m);
      if (headingMatch && !issue.title) {
        issue.title = headingMatch[1]!.trim();
      }
      if (!issue.description) {
        issue.description = body;
      }
    } else {
      // No front matter — title from first heading, rest is description
      const headingMatch = content.match(/^#\s+(.+)$/m);
      if (headingMatch) {
        issue.title = headingMatch[1]!.trim();
      }
      issue.description = content;
      issue.state = 'Todo'; // Default state for plain markdown
    }

    // Derive identifier from filename if not present
    if (!issue.identifier && !issue.id && !issue.key) {
      issue.identifier = path.basename(filePath, path.extname(filePath));
    }

    return issue;
  }
}
