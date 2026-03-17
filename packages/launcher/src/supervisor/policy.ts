/**
 * Policy enforcement — validates spec team shape before execution.
 *
 * Checks:
 * 1. require_final_read_only_review: last stage must have a read-only reviewer
 * 2. supervisor_only: at least one writable worker must exist (parent doesn't edit)
 * 3. material_issue_strategy validation
 */

import type { LauncherSpec, AgentSpec } from '../types/spec.js';
import type { StagePlan } from '../types/manifest.js';

export interface PolicyViolation {
  rule: string;
  message: string;
  severity: 'error' | 'warning';
}

/**
 * Classify whether an agent is read-only based on kind and sandbox.
 */
function isReadOnly(agent: AgentSpec): boolean {
  if (agent.sandbox === 'read-only') return true;
  if (agent.kind === 'reviewer' || agent.kind === 'validator') return true;
  return false;
}

/**
 * Validate spec policies before execution.
 * Returns violations — empty array means all policies pass.
 */
export function validatePolicies(
  spec: LauncherSpec,
  stagePlan: StagePlan[],
): PolicyViolation[] {
  const violations: PolicyViolation[] = [];

  // Policy 1: require_final_read_only_review
  if (spec.require_final_read_only_review) {
    const lastStage = stagePlan[stagePlan.length - 1];
    if (lastStage) {
      const lastStageAgents = spec.agents.filter(
        (a) => (a.stage ?? 1) === lastStage.stage,
      );
      const hasReadOnlyReviewer = lastStageAgents.some((a) => isReadOnly(a));

      if (!hasReadOnlyReviewer) {
        violations.push({
          rule: 'require_final_read_only_review',
          message: `Last stage (${lastStage.stage}) has no read-only reviewer. ` +
            `Workers in last stage: ${lastStageAgents.map((a) => a.name).join(', ')}`,
          severity: 'error',
        });
      }
    }
  }

  // Policy 2: supervisor_only
  if (spec.supervisor_only) {
    const hasWritableWorker = spec.agents.some((a) => !isReadOnly(a));
    if (!hasWritableWorker) {
      violations.push({
        rule: 'supervisor_only',
        message: 'supervisor_only is true but no writable workers found. ' +
          'The supervisor cannot edit deliverables directly — at least one implementer/fixer is required.',
        severity: 'warning',
      });
    }
  }

  // Policy 3: material_issue_strategy validation
  if (spec.material_issue_strategy === 'fixer_then_rereview') {
    const hasReviewer = spec.agents.some(
      (a) => a.kind === 'reviewer' || a.kind === 'validator',
    );
    if (!hasReviewer) {
      violations.push({
        rule: 'material_issue_strategy',
        message: 'material_issue_strategy is "fixer_then_rereview" but no reviewer/validator found in team. ' +
          'This strategy requires a reviewer to detect material issues.',
        severity: 'warning',
      });
    }
  }

  return violations;
}

/**
 * Build policy section for the manifest.
 */
export function buildPolicyInfo(
  spec: LauncherSpec,
  stagePlan: StagePlan[],
  results: { name: string; is_read_only: boolean; stage: number }[],
) {
  const writableWorkerNames = results
    .filter((r) => !r.is_read_only)
    .map((r) => r.name);
  const readOnlyReviewerNames = results
    .filter((r) => r.is_read_only)
    .map((r) => r.name);

  // Final read-only reviewers: read-only workers in the last stage
  const lastStageNum = stagePlan.length > 0
    ? stagePlan[stagePlan.length - 1].stage
    : 0;
  const finalReadOnlyReviewerNames = results
    .filter((r) => r.is_read_only && r.stage === lastStageNum)
    .map((r) => r.name);

  const lastWritableStage = Math.max(
    ...results.filter((r) => !r.is_read_only).map((r) => r.stage),
    0,
  );

  return {
    execution_mode: spec.execution_mode ?? 'sequential',
    supervisor_only: spec.supervisor_only ?? false,
    require_final_read_only_review: spec.require_final_read_only_review ?? false,
    material_issue_strategy: spec.material_issue_strategy ?? 'none',
    requested_deliverables: spec.requested_deliverables ?? [],
    writable_worker_names: writableWorkerNames,
    read_only_reviewer_names: readOnlyReviewerNames,
    final_read_only_reviewer_names: finalReadOnlyReviewerNames,
    final_read_only_review_present: finalReadOnlyReviewerNames.length > 0,
    last_writable_stage: lastWritableStage,
  };
}
