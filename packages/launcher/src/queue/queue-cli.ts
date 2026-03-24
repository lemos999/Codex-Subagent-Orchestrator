#!/usr/bin/env node
/**
 * Queue runner CLI entry point.
 *
 * Usage:
 *   node queue-cli.js --config queue.json
 *   node queue-cli.js --config queue.json --max-polls 10
 *   node queue-cli.js --config queue.json --json
 */

import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { normalizeQueueConfig } from './queue-compat.js';
import { runQueue } from './queue-runner.js';

// ============================================================
// Argument parsing
// ============================================================

function parseArgs(argv: string[]): {
  configPath: string;
  maxPolls?: number;
  jsonOutput: boolean;
} {
  const args = argv.slice(2);
  let configPath: string | null = null;
  let maxPolls: number | undefined;
  let jsonOutput = false;

  for (let i = 0; i < args.length; i++) {
    if ((args[i] === '--config' || args[i] === '-c') && i + 1 < args.length) {
      configPath = args[++i]!;
    } else if (args[i] === '--max-polls' && i + 1 < args.length) {
      maxPolls = parseInt(args[++i]!, 10);
    } else if (args[i] === '--json') {
      jsonOutput = true;
    } else if (args[i] === '--help' || args[i] === '-h') {
      console.log(`
Usage:
  node queue-cli.js --config <path>

Options:
  --config, -c <path>   Queue config JSON file (required)
  --max-polls <n>       Override max poll count (0 = unlimited)
  --json                Output final state as JSON
  --help                Show this help
`);
      process.exit(0);
    }
  }

  if (!configPath) {
    console.error('Error: --config <path> is required');
    console.error('Usage: node queue-cli.js --config queue.json');
    process.exit(1);
  }

  return { configPath, maxPolls, jsonOutput };
}

// ============================================================
// Main
// ============================================================

async function main(): Promise<void> {
  const { configPath, maxPolls, jsonOutput } = parseArgs(process.argv);
  const absoluteConfigPath = path.resolve(configPath);

  // Load and normalize config
  const rawConfig = JSON.parse(await fs.readFile(absoluteConfigPath, 'utf8')) as Record<string, unknown>;
  const config = normalizeQueueConfig(rawConfig, absoluteConfigPath);

  console.log(`
${'='.repeat(60)}
  Queue Runner
${'='.repeat(60)}

  Config:       ${absoluteConfigPath}
  Tracker:      ${config.tracker.kind}
  Max polls:    ${maxPolls ?? (config.polling.max_polls || 'unlimited')}
  Interval:     ${config.polling.interval_seconds}s
  Max workers:  ${config.launcher.max_concurrent_issues}
  Output:       ${config.output.root}
  Drain on exit: ${config.polling.drain_on_exit}
`);

  const finalState = await runQueue(
    config,
    {
      onStatus: (msg) => console.log(`  [queue] ${msg}`),
      onIssueDispatched: (key) => console.log(`  [queue] ✓ ${key} 디스패치됨`),
      onIssueCompleted: (key, code) => console.log(`  [queue] ✓ ${key} 완료 (exit ${code})`),
      onIssueFailed: (key, code) => console.log(`  [queue] ✗ ${key} 실패 (exit ${code})`),
    },
    maxPolls,
  );

  // Final summary
  const records = Object.values(finalState.issues);
  const completed = records.filter((r) => r.status === 'completed').length;
  const failed = records.filter((r) => r.status === 'failed').length;
  const running = records.filter((r) => r.status === 'running').length;

  if (jsonOutput) {
    console.log(JSON.stringify(finalState, null, 2));
  } else {
    console.log(`
${'='.repeat(60)}
  Queue 완료
${'='.repeat(60)}

  Total:     ${records.length}
  Completed: ${completed}
  Failed:    ${failed}
  Running:   ${running}
`);
  }

  process.exit(failed > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error('FATAL:', err instanceof Error ? err.message : String(err));
  process.exit(1);
});
