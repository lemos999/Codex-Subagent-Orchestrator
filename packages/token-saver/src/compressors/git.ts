import type { Compressor } from '../registry.js';

/**
 * Git Compressor — git 서브커맨드별 압축
 * DC-4: 최근 3개 full + 나머지 oneline (log), short format (status)
 */
export const gitCompressor: Compressor = (stdout, _stderr, cmd) => {
  if (!stdout) return stdout;

  const subcommand = extractGitSubcommand(cmd);

  switch (subcommand) {
    case 'status': return compressStatus(stdout);
    case 'log': return compressLog(stdout);
    case 'diff': return compressDiff(stdout);
    case 'show': return compressShow(stdout);
    case 'push': return compressPushPull(stdout, 'push');
    case 'pull': return compressPushPull(stdout, 'pull');
    case 'commit': return compressCommit(stdout);
    default: return stdout; // 알 수 없는 서브커맨드 → passthrough
  }
};

function extractGitSubcommand(cmd: string): string {
  const tokens = cmd.trim().split(/\s+/);
  const gitIdx = tokens.indexOf('git');
  if (gitIdx === -1 || gitIdx + 1 >= tokens.length) return '';
  const sub = tokens[gitIdx + 1];
  // skip flags like -C
  if (sub.startsWith('-')) return '';
  return sub;
}

// ─── compressStatus ───

function compressStatus(stdout: string): string {
  const lines = stdout.split('\n');
  const result: string[] = [];
  let modified = 0;
  let deleted = 0;
  let untracked = 0;
  let added = 0;

  let inUntracked = false;

  for (const line of lines) {
    // Branch info lines — keep
    if (line.startsWith('On branch ') || line.startsWith('Your branch ')) {
      result.push(line);
      inUntracked = false;
      continue;
    }

    // Section headers
    if (line.startsWith('Changes to be committed:')) {
      inUntracked = false;
      continue;
    }
    if (line.startsWith('Changes not staged for commit:')) {
      inUntracked = false;
      continue;
    }
    if (line.startsWith('Untracked files:')) {
      inUntracked = true;
      continue;
    }

    // Hint lines
    if (line.match(/^\s*\(use "git /)) continue;

    // Empty lines
    if (line.trim() === '') continue;

    // "nothing to commit" line — keep
    if (line.includes('nothing to commit')) {
      result.push(line.trim());
      continue;
    }

    // File entries
    const stagedNew = line.match(/^\s+new file:\s+(.+)/);
    if (stagedNew) {
      result.push(`A  ${stagedNew[1].trim()}`);
      added++;
      continue;
    }

    const stagedModified = line.match(/^\s+modified:\s+(.+)/);
    if (stagedModified) {
      result.push(` M ${stagedModified[1].trim()}`);
      modified++;
      continue;
    }

    const stagedDeleted = line.match(/^\s+deleted:\s+(.+)/);
    if (stagedDeleted) {
      result.push(` D ${stagedDeleted[1].trim()}`);
      deleted++;
      continue;
    }

    const stagedRenamed = line.match(/^\s+renamed:\s+(.+)/);
    if (stagedRenamed) {
      result.push(` R ${stagedRenamed[1].trim()}`);
      continue;
    }

    // Untracked file entries (just indented filenames)
    if (inUntracked && line.match(/^\s+\S/)) {
      result.push(`?? ${line.trim()}`);
      untracked++;
      continue;
    }
  }

  // Summary line
  const parts: string[] = [];
  if (added > 0) parts.push(`${added} added`);
  if (modified > 0) parts.push(`${modified} modified`);
  if (deleted > 0) parts.push(`${deleted} deleted`);
  if (untracked > 0) parts.push(`${untracked} untracked`);

  // If too many files, group by top-level directory
  const MAX_FILES = 20;
  const fileLines = result.filter(l => l.match(/^[ MADR?]{1,2}\s/));
  const nonFileLines = result.filter(l => !l.match(/^[ MADR?]{1,2}\s/));

  if (fileLines.length > MAX_FILES) {
    // Group by directory
    const dirs = new Map<string, string[]>();
    for (const line of fileLines) {
      const path = line.substring(3).trim().replace(/^"/, '').replace(/"$/, '');
      const dir = path.includes('/') ? path.split('/').slice(0, 2).join('/') : '.';
      if (!dirs.has(dir)) dirs.set(dir, []);
      dirs.get(dir)!.push(line);
    }

    const grouped: string[] = [...nonFileLines];
    for (const [dir, files] of [...dirs.entries()].sort((a, b) => b[1].length - a[1].length)) {
      if (files.length <= 5) {
        grouped.push(...files);
      } else {
        grouped.push(...files.slice(0, 4));
        grouped.push(`   ... +${files.length - 4} more in ${dir}/`);
      }
    }
    if (parts.length > 0) {
      grouped.push(`(${parts.join(', ')}, ${fileLines.length} files total)`);
    }
    grouped.push(`(run 'git status -s' for full file list)`);
    return grouped.join('\n');
  }

  if (parts.length > 0) {
    result.push(`(${parts.join(', ')})`);
  }

  return result.join('\n');
}

// ─── compressLog ───

function compressLog(stdout: string): string {
  // Split into individual commits by "commit " at start of line
  const commits = splitCommits(stdout);
  if (commits.length === 0) return stdout;

  const result: string[] = [];

  for (let i = 0; i < commits.length; i++) {
    if (i < 3) {
      // Full format for first 3
      result.push(commits[i].trimEnd());
    } else {
      // Oneline for the rest
      const oneline = commitToOneline(commits[i]);
      if (oneline) result.push(oneline);
    }
  }

  return result.join('\n');
}

function splitCommits(stdout: string): string[] {
  const commits: string[] = [];
  const lines = stdout.split('\n');
  let current: string[] = [];

  for (const line of lines) {
    if (line.match(/^commit [0-9a-f]{7,40}/) && current.length > 0) {
      commits.push(current.join('\n'));
      current = [line];
    } else {
      current.push(line);
    }
  }
  if (current.length > 0 && current.some(l => l.trim() !== '')) {
    commits.push(current.join('\n'));
  }

  return commits;
}

function commitToOneline(block: string): string | null {
  const lines = block.split('\n');
  let hash = '';
  let title = '';

  for (const line of lines) {
    const hashMatch = line.match(/^commit ([0-9a-f]{7,40})/);
    if (hashMatch) {
      hash = hashMatch[1].substring(0, 7);
      continue;
    }
    // Skip Author:, Date:, Merge: lines
    if (line.match(/^(Author|Date|Merge):/)) continue;
    // First non-empty indented line is the title
    const trimmed = line.trim();
    if (trimmed && !title) {
      title = trimmed;
    }
  }

  if (!hash) return null;
  return `${hash} ${title}`;
}

// ─── compressDiff ───

const DIFF_PASSTHROUGH_THRESHOLD = 200;
const DIFF_PREVIEW_LINES = 100;

function compressDiff(stdout: string): string {
  // If --stat output is already present, passthrough
  if (isStatOutput(stdout)) return stdout;

  const lines = stdout.split('\n');

  // Principle 2: small output → passthrough
  if (lines.length <= DIFF_PASSTHROUGH_THRESHOLD) return stdout;

  // Large diff: stat summary + first N lines of code preserved
  const statSummary = compressDiffContent(stdout);
  const preview = lines.slice(0, DIFF_PREVIEW_LINES).join('\n');

  return `${statSummary}\n\n${preview}\n(... ${lines.length - DIFF_PREVIEW_LINES} more lines, use tee for full output)`;
}

function isStatOutput(stdout: string): boolean {
  const lines = stdout.split('\n').filter(l => l.trim() !== '');
  if (lines.length === 0) return false;

  // stat output has lines like " file.ts | 5 ++---"
  // AND does NOT contain "diff --git" (which is raw diff output)
  if (lines.some(l => l.startsWith('diff --git'))) return false;

  let statLineCount = 0;
  for (const line of lines) {
    if (line.match(/^\s+\S.*\|\s+\d+\s+[+-]+/)) statLineCount++;
  }
  // At least 50% of non-empty lines must match stat pattern
  return statLineCount > 0 && (statLineCount / lines.length) > 0.3;
}

function compressDiffContent(stdout: string): string {
  const lines = stdout.split('\n');
  const files: Map<string, { additions: number; deletions: number }> = new Map();
  let currentFile = '';

  for (const line of lines) {
    const diffMatch = line.match(/^diff --git a\/.+ b\/(.+)/);
    if (diffMatch) {
      currentFile = diffMatch[1];
      if (!files.has(currentFile)) {
        files.set(currentFile, { additions: 0, deletions: 0 });
      }
      continue;
    }

    if (!currentFile) continue;

    // Count additions/deletions (skip --- and +++ header lines)
    if (line.startsWith('+++') || line.startsWith('---')) continue;

    const entry = files.get(currentFile);
    if (!entry) continue;

    if (line.startsWith('+')) {
      entry.additions++;
    } else if (line.startsWith('-')) {
      entry.deletions++;
    }
  }

  if (files.size === 0) return stdout; // parse failed → passthrough

  const result: string[] = [];
  let totalAdd = 0;
  let totalDel = 0;

  for (const [file, stats] of files) {
    const total = stats.additions + stats.deletions;
    const plus = '+'.repeat(Math.min(stats.additions, 20));
    const minus = '-'.repeat(Math.min(stats.deletions, 20));
    result.push(` ${file} | ${total} ${plus}${minus}`);
    totalAdd += stats.additions;
    totalDel += stats.deletions;
  }

  result.push(`${files.size} file(s) changed, ${totalAdd} insertion(s), ${totalDel} deletion(s)`);

  // If original was very large, note truncation
  if (lines.length > 50) {
    result.push(`... (${lines.length} lines in full output)`);
  }

  return result.join('\n');
}

// ─── compressShow ───

function compressShow(stdout: string): string {
  const diffIdx = stdout.indexOf('diff --git');
  if (diffIdx === -1) return stdout; // no diff part

  const meta = stdout.substring(0, diffIdx).trimEnd();
  const diffPart = stdout.substring(diffIdx);
  const diffLines = diffPart.split('\n');

  // Principle 2: small diff → passthrough
  if (diffLines.length <= DIFF_PASSTHROUGH_THRESHOLD) return stdout;

  // Large diff: meta + stat summary + first N lines preserved
  const statSummary = compressDiffContent(diffPart);
  const preview = diffLines.slice(0, DIFF_PREVIEW_LINES).join('\n');

  return `${meta}\n\n${statSummary}\n\n${preview}\n(... ${diffLines.length - DIFF_PREVIEW_LINES} more lines, use tee for full output)`;
}

// ─── compressPushPull ───

function compressPushPull(stdout: string, type: 'push' | 'pull'): string {
  if (type === 'push') {
    // Extract branch from output like "To <remote>\n   abc123..def456  main -> main"
    const branchMatch = stdout.match(/\s+\S+\.\.\S+\s+(\S+)\s+->\s+(\S+)/);
    if (branchMatch) {
      return `ok ${branchMatch[2]}`;
    }
    // Simple fallback
    return `ok push`;
  }

  // pull
  if (stdout.match(/already up.to.date/i)) {
    return 'already up to date';
  }

  const commitCount = stdout.match(/(\d+)\s+commits?/i);
  if (commitCount) {
    return `ok, ${commitCount[1]} commits`;
  }

  // Fast-forward with file changes
  const ffMatch = stdout.match(/(\d+)\s+files?\s+changed/);
  if (ffMatch) {
    return `ok, ${ffMatch[1]} files changed`;
  }

  return stdout; // fail-safe
}

// ─── compressCommit ───

function compressCommit(stdout: string): string {
  // git commit output: "[branch hash] message"
  const match = stdout.match(/\[(\S+)\s+([0-9a-f]+)\]\s+(.+)/);
  if (match) {
    return `ok ${match[2]} ${match[3]}`;
  }
  return stdout; // fail-safe
}
