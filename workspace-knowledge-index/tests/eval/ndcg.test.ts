import { describe, expect, it } from 'vitest';
import { dcg, idcg, ndcg } from '../../src/eval/ndcg.js';

describe('nDCG metrics', () => {
  it('computes DCG@k correctly', () => {
    // rel = [3, 2, 1] → 3/log2(2) + 2/log2(3) + 1/log2(4)
    const result = dcg([3, 2, 1], 3);
    const expected = 3 / Math.log2(2) + 2 / Math.log2(3) + 1 / Math.log2(4);
    expect(result).toBeCloseTo(expected);
  });

  it('returns nDCG = 1.0 for perfect ranking', () => {
    // Already in ideal order
    expect(ndcg([3, 2, 1, 0], 4)).toBeCloseTo(1.0);
    expect(ndcg([3, 2, 1], 3)).toBeCloseTo(1.0);
    expect(ndcg([5], 1)).toBeCloseTo(1.0);
  });

  it('returns nDCG < 1.0 for reversed ranking', () => {
    const result = ndcg([0, 1, 2, 3], 4);
    expect(result).toBeLessThan(1.0);
    expect(result).toBeGreaterThan(0);
  });

  it('returns nDCG = 0 for empty results', () => {
    expect(ndcg([], 10)).toBe(0);
  });

  it('returns nDCG = 0 when all relevance scores are 0', () => {
    expect(ndcg([0, 0, 0], 3)).toBe(0);
  });

  it('handles k larger than results gracefully', () => {
    const result = ndcg([3, 2], 10);
    expect(result).toBeCloseTo(1.0);
  });

  it('handles single result', () => {
    expect(ndcg([3], 1)).toBeCloseTo(1.0);
    expect(ndcg([0], 1)).toBe(0);
  });

  it('truncates at k', () => {
    // [3, 0, 0, 2] with k=2: only considers [3, 0]
    // DCG@2 = 3/log2(2) + 0 = 3
    // IDCG@2 = 3/log2(2) + 2/log2(3) (ideal is [3, 2])
    // So nDCG@2 < 1.0 because the ideal has the 2 at position 2
    const atK2 = ndcg([3, 0, 0, 2], 2);
    const atK4 = ndcg([3, 0, 0, 2], 4);
    // Both should be less than 1.0 since ranking is not ideal
    expect(atK2).toBeLessThan(1.0);
    expect(atK4).toBeLessThan(1.0);
    // k=2 and k=4 produce different scores
    expect(atK2).not.toBeCloseTo(atK4);
  });

  it('IDCG sorts scores in descending order', () => {
    const ideal = idcg([1, 3, 2], 3);
    const perfectDcg = dcg([3, 2, 1], 3);
    expect(ideal).toBeCloseTo(perfectDcg);
  });
});
