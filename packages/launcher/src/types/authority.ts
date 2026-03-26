/**
 * Authority Profile types — C2.
 *
 * Defines the 4-level authority system with attenuation rules.
 * Based on C2 confirmed spec: authority_level, writable_scope,
 * redelegation control, depth limits.
 */

// ============================================================
// Authority levels
// ============================================================

export type AuthorityLevel = 1 | 2 | 3 | 4;

export const AUTHORITY_NAMES: Record<AuthorityLevel, string> = {
  1: 'read',
  2: 'write',
  3: 'delete',
  4: 'execute',
} as const;

export const AUTHORITY_VALUES: Record<AuthorityLevel, number> = {
  1: 0.25,
  2: 0.50,
  3: 0.75,
  4: 1.00,
} as const;

// ============================================================
// Authority profile
// ============================================================

export interface AuthorityProfile {
  /** Authority level 1-4 */
  authority_level: AuthorityLevel;
  /** Allowed writable file/directory paths */
  writable_scope: string[];
  /** Whether this agent can re-delegate to sub-agents */
  redelegation_allowed: boolean;
  /** Maximum delegation depth allowed */
  max_depth: number;
  /** Current depth in delegation chain */
  current_depth?: number;
  /** Risk level tag (e.g., 'L1', 'L2') */
  risk_level?: string;
}

// ============================================================
// Default constants
// ============================================================

/** Default maximum delegation depth */
export const DEFAULT_MAX_DEPTH = 2;

/** Absolute maximum delegation depth */
export const ABSOLUTE_MAX_DEPTH = 3;

/** Attenuation factor per delegation level (80% cap) */
export const ATTENUATION_FACTOR = 0.80;
