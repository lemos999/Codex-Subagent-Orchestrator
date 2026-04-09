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

  // Flags that take a value argument: -C <path>, -c <config>, --git-dir <path>, etc.
  const FLAGS_WITH_VALUE = new Set(['-C', '-c', '--git-dir', '--work-tree', '--namespace']);

  for (let i = gitIdx + 1; i < tokens.length; i++) {
    const t = tokens[i];
    if (FLAGS_WITH_VALUE.has(t)) {
      i++; // skip the flag's value
      continue;
    }
    if (t.startsWith('-')) continue; // skip other flags (--no-pager, etc.)
    return t; // first non-flag token = subcommand
  }
  return '';
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

  // Split into tracked (modified/deleted/added) vs untracked
  const trackedLines = result.filter(l => l.match(/^[ MADR]\s/));
  const untrackedLines = result.filter(l => l.startsWith('??'));
  const nonFileLines = result.filter(l => !l.match(/^[ MADR?]{1,2}\s/));

  // Strategy: show ALL tracked files (AI needs them for work)
  //           truncate untracked to 10 (rarely needed, biggest size contributor)
  const MAX_UNTRACKED = 10;
  const output: string[] = [...nonFileLines];

  // Tracked files: show all (modified, deleted, added, renamed)
  if (trackedLines.length > 0) {
    output.push(`~ Modified/Staged: ${trackedLines.length} files`);
    output.push(...trackedLines);
  }

  // Untracked files: show first 10, summarize rest
  if (untrackedLines.length > 0) {
    output.push(`? Untracked: ${untracked} files`);
    if (untrackedLines.length <= MAX_UNTRACKED) {
      output.push(...untrackedLines);
    } else {
      output.push(...untrackedLines.slice(0, MAX_UNTRACKED));
      output.push(`   ... +${untrackedLines.length - MAX_UNTRACKED} more`);
    }
  }

  // Summary
  const parts: string[] = [];
  if (added > 0) parts.push(`${added} added`);
  if (modified > 0) parts.push(`${modified} modified`);
  if (deleted > 0) parts.push(`${deleted} deleted`);
  if (untracked > 0) parts.push(`${untracked} untracked`);
  if (parts.length > 0) {
    output.push(`(${parts.join(', ')})`);
  }

  return output.join('\n');
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
