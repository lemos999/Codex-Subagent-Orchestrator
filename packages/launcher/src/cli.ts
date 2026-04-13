#!/usr/bin/env node

/**
 * CLI entry point: subagent-launch --spec <path>
 * Parses arguments, loads spec JSON, runs orchestrator, prints summary table.
 */

import * as path from 'node:path';
import { orchestrate } from './orchestrator.js';

// ============================================================
// Argument parsing
// ============================================================

function parseArgs(argv: string[]): { specPath: string; jsonOutput: boolean; harnessMode: boolean } {
  const args = argv.slice(2); // skip node and script path
  let specPath: string | null = null;
  let jsonOutput = false;
  let harnessMode = false;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--spec' && i + 1 < args.length) {
      specPath = args[i + 1];
      i++;
    } else if (args[i] === '--json') {
      jsonOutput = true;
    } else if (args[i] === '--harness') {
      harnessMode = true;
    }
  }

  if (!specPath) {
    console.error('Usage: subagent-launch --spec <path> [--json] [--harness]');
    process.exit(1);
  }

  return { specPath, jsonOutput, harnessMode };
}

// ============================================================
// Summary table printer
// ============================================================

function printSummaryTable(result: Awaited<ReturnType<typeof orchestrate>>): void {
  const { manifest, results } = result;

  console.log('');
  console.log('='.repeat(72));
  console.log('  Orchestration Complete');
  console.log('='.repeat(72));
  console.log('');

  // Summary stats
  const succeeded = results.filter((r) => r.succeeded).length;
  const failed = results.length - succeeded;
  console.log(`  Workers: ${results.length} total, ${succeeded} succeeded, ${failed} failed`);
  console.log(`  Mode: ${manifest.execution_mode}`);
  console.log(`  Output: ${manifest.output_dir}`);
  console.log('');

  // Worker table
  console.log(
    '  ' +
      'Name'.padEnd(24) +
      'Engine'.padEnd(10) +
      'Stage'.padEnd(8) +
      'Kind'.padEnd(14) +
      'Status'.padEnd(8) +
      'Preview',
  );
  console.log('  ' + '-'.repeat(70));

  for (const r of results) {
    const status = r.succeeded ? 'OK' : 'FAIL';
    const preview =
      r.last_message_preview.length > 30
        ? r.last_message_preview.slice(0, 30) + '...'
        : r.last_message_preview;
    console.log(
      '  ' +
        r.name.padEnd(24) +
        r.engine.padEnd(10) +
        String(r.stage).padEnd(8) +
        r.worker_kind.padEnd(14) +
        status.padEnd(8) +
        preview,
    );
  }

  console.log('');
  console.log(`  Manifest: ${result.manifestPath}`);
  if (result.summaryPath) {
    console.log(`  Summary:  ${result.summaryPath}`);
  }
  console.log('');
}

// ============================================================
// Main
// ============================================================

async function main(): Promise<void> {
  const { specPath, jsonOutput, harnessMode } = parseArgs(process.argv);
  const absoluteSpecPath = path.resolve(process.cwd(), specPath);
  const invocationCwd = process.cwd();

  try {
    const result = await orchestrate(absoluteSpecPath, invocationCwd, { harnessMode });

    if (jsonOutput) {
      // JSON output mode for queue runner integration
      const jsonResult = {
        manifest: result.manifestPath,
        summary: result.summaryPath ?? null,
        success: result.success,
        workers: result.results.length,
        succeeded: result.results.filter((r) => r.succeeded).length,
        failed: result.results.filter((r) => !r.succeeded).length,
      };
      console.log(JSON.stringify(jsonResult));
    } else {
      printSummaryTable(result);
    }

    if (!result.success) {
      if (!jsonOutput) {
        const failedNames = result.results
          .filter((r) => !r.succeeded)
          .map((r) => r.name);
        console.error(`ERROR: Workers failed: ${failedNames.join(', ')}`);
      }
      process.exit(1);
    }

    process.exit(0);
  } catch (err) {
    if (jsonOutput) {
      console.log(JSON.stringify({ manifest: null, summary: null, success: false, error: err instanceof Error ? err.message : String(err) }));
    } else {
      console.error(
        'FATAL:',
        err instanceof Error ? err.message : String(err),
      );
    }
    process.exit(1);
  }
}

main();
