/**
 * Authority enforcement — C2 implementation.
 *
 * Validates parent->child authority delegation,
 * applies 80% attenuation per depth level,
 * and maps risk levels to authority caps.
 */

import type { PolicyViolation } from './policy.js';
import type { RiskLevel } from './risk-matrix.js';
import type { AuthorityLevel, AuthorityProfile } from '../types/authority.js';
import {
  ATTENUATION_FACTOR,
  AUTHORITY_VALUES,
  ABSOLUTE_MAX_DEPTH,
} from '../types/authority.js';

// ============================================================
// Risk -> Authority mapping
// ============================================================

/**
 * Risk level -> maximum authority cap.
 * Per C6 D6: L1/L2 unrestricted, L3 capped at delete, L4 capped at write.
 * L4 tasks require human approval even for write (see risk-matrix.ts).
 */
const RISK_TO_MAX_AUTHORITY: Record<RiskLevel, AuthorityLevel> = {
  L1: 4, // execute — no restriction
  L2: 4, // execute — no restriction
  L3: 3, // delete
  L4: 2, // write — human approval required
};

// ============================================================
// Public API
// ============================================================

/**
 * Validate that a child authority profile does not exceed
 * the parent's authority. Returns policy violations if any.
 */
export function validateAuthority(
  parent: AuthorityProfile,
  child: AuthorityProfile,
): PolicyViolation[] {
  const violations: PolicyViolation[] = [];

  // Rule 1: Child authority level must not exceed parent
  if (child.authority_level > parent.authority_level) {
    violations.push({
      rule: 'authority_escalation',
      message:
        `Child authority level ${child.authority_level} exceeds parent level ${parent.authority_level}. ` +
        `Authority can only be equal or lower.`,
      severity: 'error',
    });
  }

  // Rule 2: 80% attenuation check
  const parentValue = AUTHORITY_VALUES[parent.authority_level];
  const childValue = AUTHORITY_VALUES[child.authority_level];
  const maxChildValue = parentValue * ATTENUATION_FACTOR;
  if (childValue > maxChildValue) {
    violations.push({
      rule: 'authority_attenuation',
      message:
        `Child authority value ${childValue} exceeds 80% of parent value ${parentValue} ` +
        `(max allowed: ${maxChildValue}).`,
      severity: 'error',
    });
  }

  // Rule 3: Depth limit
  const currentDepth = child.current_depth ?? 0;
  if (currentDepth > parent.max_depth) {
    violations.push({
      rule: 'depth_exceeded',
      message:
        `Current depth ${currentDepth} exceeds parent max_depth ${parent.max_depth}. ` +
        `Delegation must be refused.`,
      severity: 'error',
    });
  }

  if (currentDepth > ABSOLUTE_MAX_DEPTH) {
    violations.push({
      rule: 'absolute_depth_exceeded',
      message:
        `Current depth ${currentDepth} exceeds absolute maximum depth ${ABSOLUTE_MAX_DEPTH}.`,
      severity: 'error',
    });
  }

  // Rule 4: Redelegation check
  if (!parent.redelegation_allowed) {
    violations.push({
      rule: 'redelegation_denied',
      message: `Parent does not allow redelegation.`,
      severity: 'error',
    });
  }

  // Rule 5: Writable scope containment
  for (const childPath of child.writable_scope) {
    const isContained = parent.writable_scope.some(
      (parentPath) => childPath === parentPath || childPath.startsWith(parentPath + '/'),
    );
    if (!isContained) {
      violations.push({
        rule: 'scope_violation',
        message:
          `Child writable path "${childPath}" is not within parent's writable scope ` +
          `[${parent.writable_scope.join(', ')}].`,
        severity: 'error',
      });
    }
  }

  // Rule 6: Level 4 (execute) always blocked without human approval
  if (child.authority_level === 4) {
    violations.push({
      rule: 'execute_requires_human',
      message:
        `Authority level 4 (execute) requires human approval. ` +
        `Automated delegation to level 4 is always blocked.`,
      severity: 'error',
    });
  }

  // Rule 7: Risk level mismatch
  if (child.risk_level) {
    const maxAuth = getMaxAuthorityForRisk(child.risk_level as RiskLevel);
    if (child.authority_level > maxAuth) {
      violations.push({
        rule: 'risk_authority_mismatch',
        message:
          `Child authority level ${child.authority_level} exceeds max allowed ` +
          `for risk level ${child.risk_level} (max: ${maxAuth}).`,
        severity: 'warning',
      });
    }
  }

  return violations;
}

/**
 * Compute an attenuated authority profile for a given depth.
 * Each level of depth reduces authority by ATTENUATION_FACTOR (80%).
 */
export function attenuateAuthority(
  parent: AuthorityProfile,
  depth: number,
): AuthorityProfile {
  const parentValue = AUTHORITY_VALUES[parent.authority_level];
  const attenuatedValue = parentValue * Math.pow(ATTENUATION_FACTOR, depth);

  // Map attenuated value back to nearest authority level (round down)
  let resultLevel: AuthorityLevel = 1;
  if (attenuatedValue >= AUTHORITY_VALUES[4]) {
    resultLevel = 4;
  } else if (attenuatedValue >= AUTHORITY_VALUES[3]) {
    resultLevel = 3;
  } else if (attenuatedValue >= AUTHORITY_VALUES[2]) {
    resultLevel = 2;
  } else {
    resultLevel = 1;
  }

  // Cap max_depth at remaining depth
  const remainingDepth = Math.max(0, parent.max_depth - depth);

  return {
    authority_level: resultLevel,
    writable_scope: [...parent.writable_scope],
    redelegation_allowed: parent.redelegation_allowed && remainingDepth > 0,
    max_depth: Math.min(remainingDepth, ABSOLUTE_MAX_DEPTH),
    current_depth: depth,
    risk_level: parent.risk_level,
  };
}

/**
 * Get the maximum authority level allowed for a given risk level.
 */
export function getMaxAuthorityForRisk(riskLevel: RiskLevel): AuthorityLevel {
  return RISK_TO_MAX_AUTHORITY[riskLevel] ?? 1;
}
