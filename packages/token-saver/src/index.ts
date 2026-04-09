#!/usr/bin/env node

// CTS CLI entry point
// Usage: node dist/index.js exec <command...>
// Usage: node dist/index.js stats

import { execSync } from 'node:child_process';
import { isExempt } from './exempt.js';
import { route } from './router.js';
import { saveTee } from './tee.js';
import { recordStat, printStats } from './stats.js';

function main(): void {
  const args = process.argv.slice(2);
  const subcommand = args[0];

  if (subcommand === 'exec') {
    const cmd = args.slice(1).join(' ');
    if (!cmd) {
      process.stderr.write('Usage: cts exec <command>\n');
      process.exit(1);
    }
    execCommand(cmd);
  } else if (subcommand === 'stats') {
    printStats();
  } else {
    printUsage();
  }
}

function execCommand(cmd: string): void {
  // 1. Exempt check
  if (isExempt(cmd)) {
    // Execute original command, pass through unchanged
    try {
      const output = execSync(cmd, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] });
      process.stdout.write(output);
    } catch (err: any) {
      if (err.stdout) process.stdout.write(err.stdout);
      if (err.stderr) process.stderr.write(err.stderr);
      process.exit(err.status ?? 1);
    }
    return;
  }

  // 2. Execute command
  let stdout = '';
  let stderr = '';
  let exitCode = 0;
  try {
    stdout = execSync(cmd, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] });
  } catch (err: any) {
    stdout = err.stdout ?? '';
    stderr = err.stderr ?? '';
    exitCode = err.status ?? 1;
  }

  // 3. Tee: 원본 보존
  saveTee(cmd, stdout);

  // 4. Route to compressor
  const compressor = route(cmd);

  // 5. Compress (fallback: raw output)
  let compressed: string;
  try {
    compressed = compressor(stdout, stderr, cmd);
  } catch {
    // Fail-safe: return raw output
    compressed = stdout;
  }

  // 6. Record stats
  recordStat(cmd, stdout.length, compressed.length);

  // 7. Output
  process.stdout.write(compressed);
  if (stderr && exitCode !== 0) {
    process.stderr.write(stderr);
  }

  process.exit(exitCode);
}

function printUsage(): void {
  console.log(`Claude Token Saver (CTS) v0.1.0

Usage:
  cts exec <command>    Execute command with output compression
  cts stats             Show token savings statistics
  cts --help            Show this help`);
}

main();
