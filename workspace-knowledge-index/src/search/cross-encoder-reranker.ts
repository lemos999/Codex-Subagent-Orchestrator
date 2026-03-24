/**
 * Cross-encoder re-ranker using ONNX Runtime directly.
 *
 * Uses Xenova/ms-marco-MiniLM-L-6-v2 (~90MB) to re-score query-document
 * pairs. Cross-encoders see query + document together, producing much
 * more accurate relevance scores than bi-encoder cosine similarity.
 *
 * Uses ONNX Runtime + transformers.js tokenizer directly (avoiding
 * pipeline API which has issues on Windows).
 */

import type { SearchResult } from '../types/index.js';

let sessionPromise: Promise<RerankerSession | null> | null = null;
let loadFailed = false;

const RERANKER_MODEL = 'Xenova/ms-marco-MiniLM-L-6-v2';
const MAX_DOC_CHARS = 512;

interface RerankerSession {
  session: import('onnxruntime-node').InferenceSession;
  tokenizer: unknown;  // transformers.js PreTrainedTokenizer
}

async function getRerankerSession(): Promise<RerankerSession | null> {
  if (loadFailed) return null;

  if (!sessionPromise) {
    sessionPromise = (async () => {
      try {
        const os = await import('node:os');
        const pathMod = await import('node:path');
        const fsMod = await import('node:fs');

        // Find model path — check HF cache first, then download via transformers.js
        const cacheDir = pathMod.join(os.homedir(), '.cache', 'huggingface', 'transformers');
        const modelDir = pathMod.join(cacheDir, 'Xenova', 'ms-marco-MiniLM-L-6-v2');
        const onnxPath = pathMod.join(modelDir, 'onnx', 'model.onnx');

        if (!fsMod.existsSync(onnxPath)) {
          // Trigger download via transformers.js AutoTokenizer (downloads model files)
          const { AutoTokenizer, env } = await import('@huggingface/transformers');
          env.allowLocalModels = true;
          env.cacheDir = cacheDir;
          console.warn(`[wki] Downloading cross-encoder model: ${RERANKER_MODEL} ...`);
          await AutoTokenizer.from_pretrained(RERANKER_MODEL);
        }

        if (!fsMod.existsSync(onnxPath)) {
          throw new Error(`ONNX model not found at ${onnxPath}`);
        }

        console.warn(`[wki] Loading cross-encoder reranker: ${RERANKER_MODEL} ...`);
        const startMs = Date.now();

        // Load ONNX session directly
        const ort = await import('onnxruntime-node');
        const session = await ort.InferenceSession.create(onnxPath);

        // Load tokenizer via transformers.js
        const { AutoTokenizer, env } = await import('@huggingface/transformers');
        env.allowLocalModels = true;
        env.cacheDir = cacheDir;
        const tokenizer = await AutoTokenizer.from_pretrained(RERANKER_MODEL);

        console.warn(`[wki] Reranker loaded in ${Date.now() - startMs}ms`);
        return { session, tokenizer } as unknown as RerankerSession;
      } catch (err) {
        loadFailed = true;
        console.warn(`[wki] Cross-encoder load failed, falling back to rule-based: ${err instanceof Error ? err.message : String(err)}`);
        return null;
      }
    })();
  }
  return sessionPromise;
}

/**
 * Score a single query-document pair using the cross-encoder.
 */
async function scoreQueryDoc(
  reranker: RerankerSession,
  query: string,
  document: string,
): Promise<number> {
  const ort = await import('onnxruntime-node');

  // transformers.js tokenizer returns Tensor objects with ort_tensor.cpuData (BigInt64Array)
  const tok = reranker.tokenizer as (text: string, options: { text_pair: string; padding: boolean; truncation: boolean }) => {
    input_ids: { ort_tensor: { cpuData: BigInt64Array; dims: number[] } };
    attention_mask: { ort_tensor: { cpuData: BigInt64Array; dims: number[] } };
    token_type_ids: { ort_tensor: { cpuData: BigInt64Array; dims: number[] } };
  };
  const encoded = tok(query, { text_pair: document, padding: true, truncation: true });

  const seqLen = encoded.input_ids.ort_tensor.cpuData.length;
  const inputIds = new ort.Tensor('int64', encoded.input_ids.ort_tensor.cpuData, [1, seqLen]);
  const attentionMask = new ort.Tensor('int64', encoded.attention_mask.ort_tensor.cpuData, [1, seqLen]);
  const tokenTypeIds = new ort.Tensor('int64', encoded.token_type_ids.ort_tensor.cpuData, [1, seqLen]);

  const output = await reranker.session.run({
    input_ids: inputIds,
    attention_mask: attentionMask,
    token_type_ids: tokenTypeIds,
  });

  // ms-marco model outputs logits — single value for relevance
  const logits = output['logits'] ?? output[Object.keys(output)[0]!];
  return (logits as { data: Float32Array }).data[0] ?? 0;
}

/**
 * Re-rank search results using cross-encoder model.
 * Falls back gracefully if model is unavailable.
 */
const HANGUL_RE = /[\uAC00-\uD7AF]/;

export async function crossEncoderRerank(
  results: SearchResult[],
  query: string,
  topN: number = 20,
  expandedQuery?: string,
): Promise<SearchResult[] | null> {
  if (results.length <= 1) return null;

  // Skip cross-encoder for Korean queries (ms-marco is English-only)
  if (HANGUL_RE.test(query)) return null;

  const reranker = await getRerankerSession();
  if (!reranker) return null;

  const ceQuery = query;

  const toRerank = results.slice(0, topN);
  const rest = results.slice(topN);

  try {
    const scored: Array<{ result: SearchResult; ceScore: number }> = [];

    for (const r of toRerank) {
      const docText = r.chunk.content.slice(0, MAX_DOC_CHARS);
      const ceScore = await scoreQueryDoc(reranker, ceQuery, docText);
      scored.push({ result: r, ceScore });
    }

    // Normalize CE scores to 0-1 range
    const maxCe = Math.max(...scored.map(s => s.ceScore));
    const minCe = Math.min(...scored.map(s => s.ceScore));
    const ceRange = maxCe - minCe || 1;

    const reranked = scored.map(({ result, ceScore }) => ({
      ...result,
      // Blend: 45% original + 55% cross-encoder
      score: result.score * 0.45 + ((ceScore - minCe) / ceRange) * 0.55,
    }));

    reranked.sort((a, b) => b.score - a.score);

    // Append rest with slightly reduced scores
    const lowestReranked = reranked.length > 0 ? reranked[reranked.length - 1]!.score : 0;
    const withRest = [
      ...reranked,
      ...rest.map((r, i) => ({ ...r, score: lowestReranked * (0.9 - i * 0.01) })),
    ];

    return withRest;
  } catch (err) {
    console.warn(`[wki] Cross-encoder rerank failed: ${err instanceof Error ? err.message : String(err)}`);
    return null;
  }
}
