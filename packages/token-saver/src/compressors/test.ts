import type { Compressor } from '../registry.js';

/**
 * Strip ANSI escape codes from a string.
 */
function stripAnsi(text: string): string {
  // eslint-disable-next-line no-control-regex
  return text.replace(/\x1B\[[0-9;]*[a-zA-Z]/g, '');
}

/**
 * Compress vitest/jest output: summary + failure details.
 */
function compressVitest(stdout: string, stderr: string): string {
  const raw = stripAnsi(stdout + '\n' + stderr);
  const lines = raw.split('\n');

  // --- Extract summary ---
  // vitest: "Tests  3 passed (3)" or "Tests  135 passed | 2 failed (3 suites)"
  // jest:   "Test Suites: 1 passed, 1 total" / "Tests:       5 passed, 5 total"
  let summary = '';
  for (const line of lines) {
    const trimmed = line.trim();
    if (/^Tests?\s+/i.test(trimmed) && /passed/i.test(trimmed)) {
      summary = trimmed;
      // Keep scanning — last match is typically the most complete summary
    }
    if (/^Test Suites:/i.test(trimmed)) {
      summary = trimmed;
    }
  }

  // --- Extract failure blocks ---
  const failures: string[] = [];
  let inFailBlock = false;
  let currentBlock: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();

    // Detect start of a failure block
    // vitest uses ❯, ×, ✕ for failures; also catch AssertionError/Error: lines
    if (/^(FAIL|✗|×|✕|❯)\s/.test(trimmed) || /^\s*FAIL\s/.test(line) || /^(AssertionError|Error):\s/.test(trimmed)) {
      if (inFailBlock && currentBlock.length > 0) {
        failures.push(currentBlock.join('\n'));
      }
      currentBlock = [trimmed];
      inFailBlock = true;
      continue;
    }

    if (inFailBlock) {
      // End block on blank line or new test file header
      if (trimmed === '' && currentBlock.length > 3) {
        failures.push(currentBlock.join('\n'));
        currentBlock = [];
        inFailBlock = false;
      } else if (trimmed !== '') {
        currentBlock.push(trimmed);
      }
    }
  }
  // Flush last block
  if (inFailBlock && currentBlock.length > 0) {
    failures.push(currentBlock.join('\n'));
  }

  // --- Build output ---
  if (!summary && failures.length === 0) {
    // Parsing failed → return last 10 lines as fallback
    const last10 = lines.slice(-10).join('\n').trim();
    return last10 || stdout;
  }

  const parts: string[] = [];
  if (summary) {
    parts.push(`[vitest] ${summary}`);
  }
  if (failures.length > 0) {
    parts.push('');
    parts.push(...failures);
  }

  return parts.join('\n').trim() || stdout;
}

/**
 * Compress pytest output: summary + failure details.
 */
function compressPytest(stdout: string, stderr: string): string {
  const raw = stripAnsi(stdout + '\n' + stderr);
  const lines = raw.split('\n');

  // --- Extract summary ---
  // "=== 3 passed ===" or "=== 1 failed, 2 passed ==="
  // or "3 passed, 1 failed" at end
  let summary = '';
  for (const line of lines) {
    const trimmed = line.trim();
    if (/={2,}\s.*passed.*={2,}/.test(trimmed) || /\d+\s+passed/.test(trimmed)) {
      summary = trimmed.replace(/^=+\s*/, '').replace(/\s*=+$/, '');
    }
  }

  // --- Extract failure blocks ---
  const failures: string[] = [];
  let inFailBlock = false;
  let currentBlock: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();

    // "FAILED tests/test_foo.py::test_bar - ..."
    if (/^FAILED\s/.test(trimmed)) {
      if (inFailBlock && currentBlock.length > 0) {
        failures.push(currentBlock.join('\n'));
      }
      currentBlock = [trimmed];
      inFailBlock = true;
      continue;
    }

    // "E   AssertionError: ..."
    if (/^E\s{3}/.test(line) || /^>\s/.test(trimmed)) {
      if (!inFailBlock) {
        inFailBlock = true;
        currentBlock = [];
      }
      currentBlock.push(trimmed);
      continue;
    }

    if (inFailBlock) {
      if (/^={2,}/.test(trimmed) || /^-{2,}/.test(trimmed)) {
        failures.push(currentBlock.join('\n'));
        currentBlock = [];
        inFailBlock = false;
      } else if (trimmed !== '') {
        currentBlock.push(trimmed);
      }
    }
  }
  if (inFailBlock && currentBlock.length > 0) {
    failures.push(currentBlock.join('\n'));
  }

  // --- Build output ---
  if (!summary && failures.length === 0) {
    const last10 = lines.slice(-10).join('\n').trim();
    return last10 || stdout;
  }

  const parts: string[] = [];
  if (summary) {
    parts.push(`[pytest] ${summary}`);
  }
  if (failures.length > 0) {
    parts.push('');
    parts.push(...failures);
  }

  return parts.join('\n').trim() || stdout;
}

/**
 * Test Compressor — vitest/jest/pytest summary + failure details.
 * DC-5: preserve pass count + failure details.
 */
export const testCompressor: Compressor = (stdout, stderr, cmd) => {
  if (cmd.includes('vitest') || cmd.includes('jest')) {
    return compressVitest(stdout, stderr);
  }
  if (cmd.includes('pytest')) {
    return compressPytest(stdout, stderr);
  }
  // Unknown test runner -> passthrough
  return stdout;
};
