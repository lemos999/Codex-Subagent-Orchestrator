/**
 * Convergence detector — parses reviewer output for APPROVE/REQUEST_CHANGES.
 * Stagnation detector — tracks repeated failures and triggers agent swap.
 *
 * Absorbed from Ouroboros: auto-convergence loop + stagnation detection.
 */

export type ConvergenceVerdict = 'approve' | 'request_changes' | 'unknown';

/**
 * Parse reviewer output for convergence signals.
 * Reviewers are expected to start with [APPROVE] or [REQUEST_CHANGES].
 */
export function detectConvergence(reviewerOutput: string): ConvergenceVerdict {
  const trimmed = reviewerOutput.trim();
  const firstLine = trimmed.split('\n')[0] ?? '';
  const upper = firstLine.toUpperCase();

  if (upper.includes('[APPROVE]') || upper.includes('[LGTM]')) {
    return 'approve';
  }
  if (upper.includes('[REQUEST_CHANGES]') || upper.includes('[REJECT]') || upper.includes('[CHANGES_REQUESTED]')) {
    return 'request_changes';
  }

  // Fallback: scan first 500 chars for signals
  const head = trimmed.slice(0, 500).toUpperCase();
  if (head.includes('APPROVE') && !head.includes('NOT APPROVE') && !head.includes("DON'T APPROVE")) {
    return 'approve';
  }
  if (head.includes('REQUEST_CHANGES') || head.includes('CHANGES REQUESTED') || head.includes('수정 필요') || head.includes('수정이 필요')) {
    return 'request_changes';
  }

  return 'unknown';
}

/**
 * Extract actionable feedback from reviewer output for the fixer.
 */
export function extractFeedback(reviewerOutput: string): string {
  const lines = reviewerOutput.trim().split('\n');

  // Skip the verdict line, return the rest as feedback
  const feedbackLines = lines.slice(1).filter(l => l.trim().length > 0);
  if (feedbackLines.length === 0) return reviewerOutput;

  return feedbackLines.join('\n');
}

// ============================================================
// Stagnation detection
// ============================================================

export interface StagnationState {
  errorSignatures: string[];
  consecutiveFailures: number;
  agentSwaps: number;
}

/**
 * Create a fresh stagnation tracker.
 */
export function createStagnationState(): StagnationState {
  return { errorSignatures: [], consecutiveFailures: 0, agentSwaps: 0 };
}

/**
 * Extract a short signature from an error/failure message.
 */
function errorSignature(message: string): string {
  // Normalize: lowercase, collapse whitespace, take first 100 chars
  return message.toLowerCase().replace(/\s+/g, ' ').trim().slice(0, 100);
}

/**
 * Record a failure and check for stagnation.
 * Returns true if stagnation is detected (same error 3+ times).
 */
export function recordFailure(state: StagnationState, failureMessage: string): boolean {
  const sig = errorSignature(failureMessage);
  state.errorSignatures.push(sig);
  state.consecutiveFailures++;

  // Count occurrences of this signature
  const count = state.errorSignatures.filter(s => s === sig).length;
  return count >= 3;
}

/**
 * Record a success — resets consecutive failure counter.
 */
export function recordSuccess(state: StagnationState): void {
  state.consecutiveFailures = 0;
}

/**
 * Suggest an alternative agent when stagnation is detected.
 */
export function suggestAlternative(
  currentEngine: string,
  currentAgentId: string | undefined,
  availableAgents: string[],
): string | null {
  // Strategy: swap engine first, then swap agent within same engine
  const engineAlternatives: Record<string, string> = {
    codex: 'claude',
    claude: 'codex',
    gemini: 'claude',
  };

  // Find an agent on a different engine
  const altEngine = engineAlternatives[currentEngine] ?? 'claude';

  // Look for a similar-role agent on the alternative engine
  const candidates = availableAgents.filter(id => {
    if (id === currentAgentId) return false;
    // Prefer agents with 'impl' or 'fixer' in name for implementation tasks
    return id.includes('impl') || id.includes('fixer');
  });

  return candidates[0] ?? null;
}

// ============================================================
// Evolve loop configuration
// ============================================================

export interface EvolveConfig {
  maxIterations: number;
  convergenceThreshold: ConvergenceVerdict;
}

export const DEFAULT_EVOLVE_CONFIG: EvolveConfig = {
  maxIterations: 3,
  convergenceThreshold: 'approve',
};
