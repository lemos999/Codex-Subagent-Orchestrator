/**
 * Capability Registry types — C1.
 *
 * Defines the 8-dimension capability vector, scoring, constraints,
 * and routing result types used by CapabilityRegistry.
 */

import type { Engine, Model } from './engine.js';

// ============================================================
// Dimension keys (8-dimensional capability vector)
// ============================================================

export type DimensionKey =
  | 'tool-access'
  | 'code-gen'
  | 'long-context'
  | 'korean-quality'
  | 'reasoning'
  | 'speed'
  | 'cost-efficiency'
  | 'multimodal';

export const ALL_DIMENSIONS: readonly DimensionKey[] = [
  'tool-access',
  'code-gen',
  'long-context',
  'korean-quality',
  'reasoning',
  'speed',
  'cost-efficiency',
  'multimodal',
] as const;

// ============================================================
// Dimension score
// ============================================================

export interface DimensionScore {
  /** Declared score from YAML config. 0.00-1.00 */
  declaredScore: number;
  /** Measured score, updated via C5 EMA. 0.00-1.00 */
  measuredScore?: number;
  /** Evidence string explaining the score basis. */
  evidence: string;
}

// ============================================================
// Capability profile (per engine-model pair)
// ============================================================

export interface CapabilityProfile {
  engine: Engine;
  model: Model;
  dimensions: Record<DimensionKey, DimensionScore>;
  /** Role name -> affinity score 0.00-1.00 */
  roleAffinity: Record<string, number>;
  /** Free-form constraint tags (e.g., "file-write-capable") */
  constraints: string[];
}

// ============================================================
// Task constraints
// ============================================================

export type Constraint =
  | { type: 'min_dimension'; dimension: DimensionKey; minValue: number }
  | { type: 'required_tag'; tag: string }
  | { type: 'excluded_engine'; engine: Engine };

// ============================================================
// Task scorecard (input to routing)
// ============================================================

export interface TaskScorecard {
  role: string;
  requiredDimensions: Partial<Record<DimensionKey, { minScore: number; weight: number }>>;
  constraints: Constraint[];
}

// ============================================================
// Match result (output of routing)
// ============================================================

export interface MatchResult {
  engine: Engine;
  model: Model;
  score: number;
  reasoning: string[];
  eliminatedCandidates: Array<{ engine: Engine; model: Model; reason: string }>;
}
