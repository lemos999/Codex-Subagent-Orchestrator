/**
 * Queue report — generates human-readable queue-report.md.
 */

import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import type { QueueState, CanonicalQueueConfig } from './queue-types.js';

export async function writeReport(
  config: CanonicalQueueConfig,
  state: QueueState,
  pollCount: number,
): Promise<void> {
  const reportPath = path.resolve(
    config.config_directory,
    config.output.report_file ?? `${config.output.root}/queue-report.md`,
  );
  await fs.mkdir(path.dirname(reportPath), { recursive: true });

  const records = Object.values(state.issues);
  const completed = records.filter((r) => r.status === 'completed').length;
  const running = records.filter((r) => r.status === 'running').length;
  const failed = records.filter((r) => r.status === 'failed').length;
  const totalDispatches = records.reduce((sum, r) => sum + r.dispatch_count, 0);

  const lines: string[] = [
    '# Queue Report',
    '',
    `- Updated: ${state.updated_at_utc}`,
    `- Tracker kind: ${config.tracker.kind}`,
    `- Poll count: ${pollCount}`,
    `- Dispatch count: ${totalDispatches}`,
    `- Completed: ${completed}`,
    `- Running: ${running}`,
    `- Failed: ${failed}`,
    '',
    '## Issues',
    '',
  ];

  for (const record of records) {
    const parts = [
      `- **${record.issue_key}**: status=${record.status}`,
      `tracker_state=${record.last_state ?? 'unknown'}`,
      `dispatches=${record.dispatch_count}`,
      `failures=${record.consecutive_failures}`,
    ];

    if (record.workspace_path) {
      parts.push(`workspace=${record.workspace_path}`);
    }
    if (record.stop_reason) {
      parts.push(`stop_reason=${record.stop_reason}`);
    }

    lines.push(parts.join(', '));
  }

  lines.push('');
  await fs.writeFile(reportPath, lines.join('\n'), 'utf8');
}
