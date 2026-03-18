/**
 * Summary writer — produces orchestration-summary.md matching PS launcher format.
 * Format is derived from the real example in subagent-runs/gemini/evidence-verify-2026-03-17/.
 */

import * as path from 'node:path';

import type { Manifest } from '../types/manifest.js';
import { writeFileSafe } from '../common/fs-helpers.js';

/**
 * Format a value for summary display.
 * null/undefined -> "n/a", numbers/booleans as-is, strings in backticks if path-like.
 */
function fmt(val: unknown): string {
  if (val === null || val === undefined) return 'n/a';
  if (typeof val === 'number') return String(val);
  if (typeof val === 'boolean') return val ? 'True' : 'False';
  return String(val);
}

function fmtPath(val: string | null): string {
  if (!val) return 'n/a';
  return '`' + val + '`';
}

/**
 * Write the orchestration summary as Markdown.
 * Format matches the PS launcher's orchestration-summary.md exactly.
 */
export async function writeSummary(
  filePath: string,
  manifest: Manifest,
): Promise<void> {

  const e = manifest.efficiency_signals;
  const p = manifest.policy;

  const lines: string[] = [
    '# Orchestration Summary',
    '',
    `- workspace_root: ${fmtPath(manifest.workspace_root)}`,
    `- execution_mode: ${manifest.execution_mode}`,
    `- workers_succeeded: ${e.succeeded_workers}/${e.total_workers}`,
    `- shared_directive_mode: ${manifest.shared_directive.effective_mode}`,
    `- shared_directive_chars: ${manifest.shared_directive.original_char_count} -> ${manifest.shared_directive.effective_char_count}`,
    `- live_usage_enabled: ${fmt(manifest.live_usage.enabled)}`,
  ];

  if (manifest.live_usage.enabled) {
    lines.push(
      `- live_usage_display_mode: ${manifest.live_usage.display_mode}`,
      `- live_usage_poll_interval_ms: ${manifest.live_usage.poll_interval_ms}`,
    );
    if (manifest.live_usage.status_file) {
      lines.push(
        `- live_usage_status_file: ${fmtPath(manifest.live_usage.status_file)}`,
      );
    }
  }

  if (manifest.workflow.enabled) {
    lines.push(
      `- workflow_file: ${fmtPath(manifest.workflow.source)}`,
      `- workflow_prompt_mode: ${manifest.workflow.prompt_mode}`,
    );
  }

  if (manifest.hooks.after_create.enabled) {
    lines.push(
      `- workspace_bootstrap_ran: ${fmt(manifest.hooks.after_create.ran)}`,
    );
    if (manifest.hooks.after_create.ran) {
      lines.push(
        `- workspace_bootstrap_exit_code: ${fmt(manifest.hooks.after_create.exit_code)}`,
        `- workspace_bootstrap_trigger: ${manifest.hooks.after_create.trigger}`,
      );
    }
  }

  lines.push(
    `- total_prompt_chars: ${e.total_prompt_chars}`,
    `- total_footer_tokens: ${e.total_footer_tokens}`,
    `- supervisor_only: ${fmt(p.supervisor_only)}`,
    `- require_final_read_only_review: ${fmt(p.require_final_read_only_review)}`,
    `- material_issue_strategy: ${p.material_issue_strategy}`,
    `- final_read_only_review_present: ${fmt(e.final_read_only_review_present)}`,
    `- efficiency_measurement: ${e.measurement_mode}`,
    `- requested_deliverable_count: ${e.requested_deliverable_count}`,
    `- workers_per_deliverable: ${e.workers_per_deliverable !== null ? fmt(e.workers_per_deliverable) : 'n/a'}`,
    `- writable_workers_per_deliverable: ${e.writable_workers_per_deliverable !== null ? fmt(e.writable_workers_per_deliverable) : 'n/a'}`,
    `- worker_shape: writable=${e.writable_workers}, read_only=${e.read_only_workers}, implementer=${e.implementer_workers}, reviewer=${e.reviewer_workers}, validator=${e.validator_workers}, fixer=${e.fixer_workers}`,
    `- full_auto_split: writable=${e.full_auto_writable_workers}, read_only=${e.full_auto_read_only_workers}`,
    `- stage_shape: total=${e.stage_count}, parallel_stages=${e.parallel_stage_count}, max_parallel_workers_in_stage=${e.max_parallel_workers_in_stage}`,
    `- efficiency_note: ${e.note}`,
    `- manifest: ${fmtPath(manifest.output_dir + path.sep + 'orchestration-manifest.json')}`,
  );

  // Archive info (only if enabled)
  if (manifest.archive.enabled && manifest.archive.run_directory) {
    lines.push(
      `- archive_run_directory: ${fmtPath(manifest.archive.run_directory)}`,
    );
    if (manifest.archive.workers_directory) {
      lines.push(
        `- archive_workers_directory: ${fmtPath(manifest.archive.workers_directory)}`,
      );
    }
  }

  if (p.requested_deliverables.length > 0) {
    lines.push(
      `- requested_deliverables: ${p.requested_deliverables.join(', ')}`,
    );
  }

  lines.push('');
  lines.push('## Workers');
  lines.push('');

  for (const r of manifest.results) {
    const status = r.succeeded ? 'ok' : 'failed';
    const sandbox = r.actual_sandbox ?? '';
    const reasoning = r.actual_reasoning_effort ?? '';
    const footerTokens =
      r.footer_tokens_used !== null ? String(r.footer_tokens_used) : 'n/a';

    lines.push(
      `- \`${r.name}\`: ${status}; engine=${r.engine}; stage=${r.stage}; kind=${r.worker_kind}; read_only=${fmt(r.is_read_only)}; full_auto=${fmt(r.requested_full_auto)}; model=${r.actual_model}; sandbox=${sandbox}; reasoning=${reasoning}; prompt_chars=${r.prompt_chars}; footer_tokens=${footerTokens}; workflow_mode=${r.workflow_prompt_mode}`,
    );
    lines.push(`  preview: ${r.last_message_preview}`);
  }

  lines.push('');

  await writeFileSafe(filePath, lines.join('\n'));
}
