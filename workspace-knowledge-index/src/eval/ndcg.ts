/**
 * Discounted Cumulative Gain at position k.
 * DCG@k = sum(i=0..k-1) rel_i / log2(i + 2)
 */
export function dcg(relevanceScores: number[], k: number): number {
  const limit = Math.min(k, relevanceScores.length);
  let sum = 0;

  for (let i = 0; i < limit; i++) {
    const rel = relevanceScores[i]!;
    if (rel > 0) {
      sum += rel / Math.log2(i + 2);
    }
  }

  return sum;
}

/**
 * Ideal DCG at position k.
 * Sort relevance scores descending, then compute DCG.
 */
export function idcg(relevanceScores: number[], k: number): number {
  const sorted = [...relevanceScores].sort((a, b) => b - a);
  return dcg(sorted, k);
}

/**
 * Normalized Discounted Cumulative Gain at position k.
 * nDCG@k = DCG@k / IDCG@k
 * Returns 0 if IDCG is 0 (no relevant results exist).
 */
export function ndcg(relevanceScores: number[], k: number): number {
  const idealDcg = idcg(relevanceScores, k);

  if (idealDcg === 0) {
    return 0;
  }

  return dcg(relevanceScores, k) / idealDcg;
}
