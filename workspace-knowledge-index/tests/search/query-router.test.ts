import { describe, expect, it } from 'vitest';
import { QueryRouter } from '../../src/search/query-router.js';

describe('QueryRouter', () => {
  const router = new QueryRouter();

  it('classifies camelCase identifiers as identifier queries', () => {
    expect(router.classify('handlePayment')).toBe('identifier');
  });

  it('classifies PascalCase identifiers as identifier queries', () => {
    expect(router.classify('PaymentService')).toBe('identifier');
  });

  it('classifies file paths as path queries', () => {
    expect(router.classify('src/payments/handle-payment.ts')).toBe('path');
  });

  it('classifies Korean natural language as natural queries', () => {
    expect(router.classify('결제 재시도 로직이 어디에 있나요')).toBe('natural');
  });

  it('classifies English natural language sentences as natural queries', () => {
    expect(router.classify('how does the payment retry workflow work')).toBe('natural');
  });

  it('classifies dependency questions as deps queries', () => {
    expect(router.classify('payment service dependency graph')).toBe('deps');
  });

  it('classifies short unmatched queries as mixed', () => {
    expect(router.classify('payment retry')).toBe('mixed');
  });

  it('returns the configured weights for each query type', () => {
    expect(router.getWeights('identifier')).toEqual({ fts: 0.7, vector: 0.3 });
    expect(router.getWeights('path')).toEqual({ fts: 0.8, vector: 0.2 });
    expect(router.getWeights('natural')).toEqual({ fts: 0.3, vector: 0.7 });
    expect(router.getWeights('deps')).toEqual({ fts: 0.5, vector: 0.5 });
    expect(router.getWeights('mixed')).toEqual({ fts: 0.5, vector: 0.5 });
  });

  it('expands camelCase identifiers into lowercase parts', () => {
    expect(router.expand('handlePayment')).toEqual(
      expect.arrayContaining(['handlePayment', 'handle', 'payment']),
    );
  });

  it('expands snake_case identifiers into lowercase parts', () => {
    expect(router.expand('payment_retry_handler')).toEqual(
      expect.arrayContaining(['payment_retry_handler', 'payment', 'retry', 'handler']),
    );
  });
});
