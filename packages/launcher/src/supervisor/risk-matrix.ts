/**
 * Risk matrix and security gate helpers for supervisor-side decisions.
 */

export type Reversibility = 'reversible' | 'irreversible';
export type Impact = 'low' | 'medium' | 'high' | 'critical';
export type RiskLevel = 'L1' | 'L2' | 'L3' | 'L4';
export type TaskType =
  | 'file_read'
  | 'file_create'
  | 'file_modify'
  | 'file_delete'
  | 'git_commit'
  | 'git_push'
  | 'git_force_push'
  | 'external_api_read'
  | 'external_api_write'
  | 'package_install'
  | 'system_exec'
  | 'db_change'
  | 'deploy';

const RISK_MATRIX: Record<Reversibility, Record<Impact, RiskLevel>> = {
  reversible: { low: 'L1', medium: 'L2', high: 'L2', critical: 'L3' },
  irreversible: { low: 'L2', medium: 'L3', high: 'L3', critical: 'L4' },
};

const DEFAULT_TASK_RISK: Record<TaskType, RiskLevel> = {
  file_read: 'L1',
  file_create: 'L1',
  file_modify: 'L2',
  file_delete: 'L3',
  git_commit: 'L2',
  git_push: 'L3',
  git_force_push: 'L4',
  external_api_read: 'L2',
  external_api_write: 'L3',
  package_install: 'L2',
  system_exec: 'L4',
  db_change: 'L3',
  deploy: 'L4',
};

const RISK_ORDER: Record<RiskLevel, number> = {
  L1: 1,
  L2: 2,
  L3: 3,
  L4: 4,
};

export interface SecurityGate {
  skipGate: boolean;
  singleEngineVerify: boolean;
  crossConsensus: boolean;
  hashRecord: boolean;
  dryRunFirst: boolean;
  requireHumanApproval: boolean;
}

/**
 * Assess a risk level from the reversibility/impact matrix.
 */
export function assessRisk(
  reversibility: Reversibility,
  impact: Impact,
): RiskLevel {
  return RISK_MATRIX[reversibility][impact];
}

/**
 * Get the default risk level for a known task type.
 */
export function getDefaultRisk(taskType: TaskType): RiskLevel {
  return DEFAULT_TASK_RISK[taskType];
}

/**
 * Raise a risk level when an explicit override requests stricter handling.
 * Downward overrides are ignored.
 */
export function overrideRisk(
  current: RiskLevel,
  requested: RiskLevel,
): RiskLevel {
  return RISK_ORDER[requested] > RISK_ORDER[current] ? requested : current;
}

/**
 * Map a risk level to the required security gates.
 * Higher levels inherit lower-level protections.
 */
export function getSecurityGate(level: RiskLevel): SecurityGate {
  switch (level) {
    case 'L1':
      return {
        skipGate: true,
        singleEngineVerify: false,
        crossConsensus: false,
        hashRecord: false,
        dryRunFirst: false,
        requireHumanApproval: false,
      };
    case 'L2':
      return {
        skipGate: false,
        singleEngineVerify: true,
        crossConsensus: false,
        hashRecord: false,
        dryRunFirst: false,
        requireHumanApproval: false,
      };
    case 'L3':
      return {
        skipGate: false,
        singleEngineVerify: true,
        crossConsensus: true,
        hashRecord: true,
        dryRunFirst: false,
        requireHumanApproval: false,
      };
    case 'L4':
      return {
        skipGate: false,
        singleEngineVerify: true,
        crossConsensus: true,
        hashRecord: true,
        dryRunFirst: true,
        requireHumanApproval: true,
      };
  }
}
