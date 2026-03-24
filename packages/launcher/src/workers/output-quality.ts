/**
 * DTR-inspired output quality checker.
 * Detects overthinking signals in worker output text.
 *
 * Based on Deep-Thinking Tokens research:
 * - Length ≠ quality (r = -0.594)
 * - Repetition, uniform length, hedging = overthinking
 * - Decision + evidence = deep thinking
 */

export interface QualitySignals {
  /** Number of overthinking warning signals detected (0 = good) */
  warningCount: number;
  /** Specific warnings */
  warnings: string[];
}

/**
 * Check worker output for overthinking signals.
 * Returns warnings (not errors) — informational only.
 */
export function checkOutputQuality(text: string): QualitySignals {
  const warnings: string[] = [];
  if (!text || text.length < 100) return { warningCount: 0, warnings };

  const lines = text.split('\n');
  const sentences = text.split(/[.!?。]\s+/).filter(s => s.length > 10);

  // 1. Repetition: same phrase appears 3+ times
  const phrases = new Map<string, number>();
  for (const s of sentences) {
    const normalized = s.toLowerCase().trim().slice(0, 60);
    if (normalized.length > 20) {
      phrases.set(normalized, (phrases.get(normalized) ?? 0) + 1);
    }
  }
  for (const [phrase, count] of phrases) {
    if (count >= 3) {
      warnings.push(`repetition: "${phrase.slice(0, 40)}..." repeated ${count} times`);
      break;
    }
  }

  // 2. Hedging without decision: too many possibility markers without conclusion
  const hedgePatterns = /~일 수 있|~도 고려|could be|might be|it depends|상황에 따라|on the other hand/gi;
  const hedgeCount = (text.match(hedgePatterns) ?? []).length;
  const hasDecision = /선택|choose|select|recommend|결론|conclusion|verdict/i.test(text);
  if (hedgeCount >= 4 && !hasDecision) {
    warnings.push(`hedging: ${hedgeCount} possibility markers without clear decision`);
  }

  // 3. Self-reference loops: "as mentioned", "as I said"
  const selfRefPatterns = /앞서 말했듯|다시 정리하면|as mentioned|as I said|to summarize again/gi;
  const selfRefCount = (text.match(selfRefPatterns) ?? []).length;
  if (selfRefCount >= 3) {
    warnings.push(`self-reference: ${selfRefCount} meta-references ("as mentioned...")`);
  }

  return { warningCount: warnings.length, warnings };
}
