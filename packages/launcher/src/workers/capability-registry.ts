/**
 * Capability Registry — C1 implementation.
 *
 * Loads per-engine capability profiles from YAML config,
 * matches engines to tasks via constraint filtering + weighted scoring,
 * and supports EMA-based score updates from C5 metrics.
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import yaml from 'js-yaml';

import type { Engine, Model } from '../types/engine.js';
import type {
  CapabilityProfile,
  Constraint,
  DimensionKey,
  DimensionScore,
  MatchResult,
  TaskScorecard,
} from '../types/capability.js';
import { ALL_DIMENSIONS } from '../types/capability.js';

// ============================================================
// EMA constants
// ============================================================

const EMA_ALPHA = 0.2;
const EMA_MIN_SAMPLES = 3;

// ============================================================
// YAML schema for a single engine file
// ============================================================

interface YamlDimension {
  declaredScore: number;
  evidence: string;
}

interface YamlModelProfile {
  model: string;
  dimensions: Record<string, YamlDimension>;
  roleAffinity: Record<string, number>;
  constraints: string[];
}

interface YamlEngineFile {
  engine: string;
  profiles: YamlModelProfile[];
}

// ============================================================
// Internal tracking for EMA
// ============================================================

interface ScoreTracker {
  sampleCount: number;
  currentMeasured: number;
}

export class CapabilityRegistry {
  private profiles: CapabilityProfile[] = [];
  private scoreTrackers: Map<string, Map<DimensionKey, ScoreTracker>> = new Map();

  /** Key for score tracker map: "engine:model" */
  private profileKey(engine: Engine, model: Model): string {
    return `${engine}:${model}`;
  }

  /**
   * Load capability profiles from YAML files in the given directory.
   * Expects files like claude.yaml, codex.yaml, gemini.yaml.
   */
  loadProfiles(configDir: string): void {
    this.profiles = [];
    this.scoreTrackers.clear();

    const files = fs.readdirSync(configDir).filter(
      (f) => f.endsWith('.yaml') || f.endsWith('.yml'),
    );

    for (const file of files) {
      if (file.startsWith('_')) continue; // skip _schema.yaml etc.
      const filePath = path.join(configDir, file);
      const content = fs.readFileSync(filePath, 'utf8');
      const parsed = yaml.load(content) as YamlEngineFile;

      if (!parsed?.engine || !Array.isArray(parsed.profiles)) continue;

      for (const mp of parsed.profiles) {
        const dimensions = {} as Record<DimensionKey, DimensionScore>;
        for (const dim of ALL_DIMENSIONS) {
          const raw = mp.dimensions?.[dim];
          dimensions[dim] = {
            declaredScore: raw?.declaredScore ?? 0,
            evidence: raw?.evidence ?? '',
          };
        }

        const profile: CapabilityProfile = {
          engine: parsed.engine as Engine,
          model: mp.model as Model,
          dimensions,
          roleAffinity: mp.roleAffinity ?? {},
          constraints: mp.constraints ?? [],
        };
        this.profiles.push(profile);
      }
    }
  }

  /** Get all loaded profiles. */
  getProfiles(): readonly CapabilityProfile[] {
    return this.profiles;
  }

  /**
   * Match the best engine for a given task scorecard.
   *
   * Algorithm:
   * 1. Filter by constraints (min_dimension, required_tag, excluded_engine)
   * 2. Score = roleAffinity + dimension weighted dot product
   * 3. Apply trust score weighting if provided
   * 4. Select highest score
   */
  matchEngine(
    scorecard: TaskScorecard,
    trustScores?: Record<string, number>,
  ): MatchResult | null {
    const eliminated: MatchResult['eliminatedCandidates'] = [];
    const candidates: Array<{ profile: CapabilityProfile; score: number; reasoning: string[] }> = [];

    for (const profile of this.profiles) {
      const eliminationReason = this.checkConstraints(profile, scorecard.constraints);
      if (eliminationReason) {
        eliminated.push({
          engine: profile.engine,
          model: profile.model,
          reason: eliminationReason,
        });
        continue;
      }

      const { score, reasoning } = this.computeScore(profile, scorecard, trustScores);
      candidates.push({ profile, score, reasoning });
    }

    if (candidates.length === 0) {
      return null; // escalation: no candidates
    }

    // Sort descending by score
    candidates.sort((a, b) => b.score - a.score);
    const best = candidates[0]!;

    return {
      engine: best.profile.engine,
      model: best.profile.model,
      score: Math.round(best.score * 1000) / 1000,
      reasoning: best.reasoning,
      eliminatedCandidates: eliminated,
    };
  }

  /**
   * Update a measured dimension score using EMA.
   * Only applies after EMA_MIN_SAMPLES observations.
   */
  updateScore(
    engine: Engine,
    model: Model,
    dimension: DimensionKey,
    measured: number,
  ): void {
    const key = this.profileKey(engine, model);
    const profile = this.profiles.find(
      (p) => p.engine === engine && p.model === model,
    );
    if (!profile) return;

    if (!this.scoreTrackers.has(key)) {
      this.scoreTrackers.set(key, new Map());
    }
    const trackers = this.scoreTrackers.get(key)!;

    if (!trackers.has(dimension)) {
      trackers.set(dimension, {
        sampleCount: 0,
        currentMeasured: profile.dimensions[dimension].declaredScore,
      });
    }
    const tracker = trackers.get(dimension)!;
    tracker.sampleCount++;

    if (tracker.sampleCount >= EMA_MIN_SAMPLES) {
      // EMA: new = alpha * measured + (1 - alpha) * old
      tracker.currentMeasured =
        EMA_ALPHA * measured + (1 - EMA_ALPHA) * tracker.currentMeasured;
      profile.dimensions[dimension].measuredScore =
        Math.round(tracker.currentMeasured * 100) / 100;
    }
  }

  /**
   * Generate a routing decision summary (JSON + MD).
   */
  getRoutingDecision(result: MatchResult): { json: string; markdown: string } {
    const json = JSON.stringify(result, null, 2);

    const lines: string[] = [
      `## Routing Decision`,
      ``,
      `**Selected**: ${result.engine} / ${result.model} (score: ${result.score})`,
      ``,
      `### Reasoning`,
      ...result.reasoning.map((r) => `- ${r}`),
    ];

    if (result.eliminatedCandidates.length > 0) {
      lines.push(``, `### Eliminated Candidates`);
      for (const c of result.eliminatedCandidates) {
        lines.push(`- ${c.engine}/${c.model}: ${c.reason}`);
      }
    }

    return { json, markdown: lines.join('\n') };
  }

  // ============================================================
  // Private helpers
  // ============================================================

  private checkConstraints(
    profile: CapabilityProfile,
    constraints: Constraint[],
  ): string | null {
    for (const c of constraints) {
      switch (c.type) {
        case 'excluded_engine':
          if (profile.engine === c.engine) {
            return `Excluded engine: ${c.engine}`;
          }
          break;
        case 'min_dimension': {
          const effective = this.getEffectiveScore(profile, c.dimension);
          if (effective < c.minValue) {
            return `${c.dimension} score ${effective} < required ${c.minValue}`;
          }
          break;
        }
        case 'required_tag':
          if (!profile.constraints.includes(c.tag)) {
            return `Missing required tag: ${c.tag}`;
          }
          break;
      }
    }
    return null;
  }

  private getEffectiveScore(
    profile: CapabilityProfile,
    dimension: DimensionKey,
  ): number {
    const ds = profile.dimensions[dimension];
    return ds.measuredScore ?? ds.declaredScore;
  }

  private computeScore(
    profile: CapabilityProfile,
    scorecard: TaskScorecard,
    trustScores?: Record<string, number>,
  ): { score: number; reasoning: string[] } {
    const reasoning: string[] = [];
    let score = 0;
    let totalWeight = 0;

    // 1. roleAffinity contribution
    const affinity = profile.roleAffinity[scorecard.role] ?? 0;
    reasoning.push(`roleAffinity[${scorecard.role}] = ${affinity}`);

    // 2. Dimension weighted dot product
    for (const [dim, req] of Object.entries(scorecard.requiredDimensions)) {
      if (!req) continue;
      const dimKey = dim as DimensionKey;
      const effective = this.getEffectiveScore(profile, dimKey);
      score += effective * req.weight;
      totalWeight += req.weight;
      reasoning.push(`${dimKey}: ${effective} * weight ${req.weight} = ${(effective * req.weight).toFixed(3)}`);
    }

    // Normalize dimension score to 0-1 range if weights exist
    if (totalWeight > 0) {
      score = score / totalWeight;
    }

    // Blend: 40% affinity + 60% dimension score
    score = 0.4 * affinity + 0.6 * score;
    reasoning.push(`Blended score (40% affinity + 60% dimensions) = ${score.toFixed(3)}`);

    // 3. Trust score weighting
    if (trustScores) {
      const trust = trustScores[profile.engine] ?? 0.5;
      const adjusted = score * (0.5 + 0.5 * trust);
      reasoning.push(`Trust adjustment: ${score.toFixed(3)} * (0.5 + 0.5 * ${trust}) = ${adjusted.toFixed(3)}`);
      score = adjusted;
    }

    return { score, reasoning };
  }
}
