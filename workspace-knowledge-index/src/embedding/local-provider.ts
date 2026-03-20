import { BaseEmbeddingProvider } from './base-provider.js';

/**
 * Local embedding provider using @huggingface/transformers (ONNX Runtime).
 *
 * Runs entirely offline after the first model download.
 * Default model: Xenova/bge-small-en-v1.5 (384d, ~33MB, MTEB avg 62.2)
 *
 * Supported models (all auto-downloaded from HuggingFace Hub):
 *   - Xenova/bge-small-en-v1.5   (384d,  ~33MB)  — fast, good quality
 *   - Xenova/bge-base-en-v1.5    (768d,  ~110MB) — balanced
 *   - Xenova/bge-m3              (1024d, ~570MB) — multilingual, best quality
 *   - Xenova/all-MiniLM-L6-v2   (384d,  ~23MB)  — fastest, decent quality
 *   - Xenova/multilingual-e5-base (768d, ~280MB) — multilingual, good quality
 *
 * Quality reference (MTEB Retrieval avg):
 *   - text-embedding-3-large (OpenAI): ~64.6
 *   - bge-base-en-v1.5:                ~63.5
 *   - bge-small-en-v1.5:               ~62.2
 *   - all-MiniLM-L6-v2:                ~58.8
 */

// Model presets with known dimensions
const MODEL_PRESETS: Record<string, number> = {
  'Xenova/bge-small-en-v1.5': 384,
  'Xenova/bge-base-en-v1.5': 768,
  'Xenova/bge-m3': 1024,
  'Xenova/all-MiniLM-L6-v2': 384,
  'Xenova/multilingual-e5-base': 768,
  'BAAI/bge-small-en-v1.5': 384,
  'BAAI/bge-base-en-v1.5': 768,
  'BAAI/bge-m3': 1024,
  'Xenova/multilingual-e5-small': 384,
  'Xenova/multilingual-e5-base': 768,
};

// Models that benefit from query instruction prefixes
const INSTRUCTION_MODELS = new Set([
  'Xenova/bge-small-en-v1.5',
  'Xenova/bge-base-en-v1.5',
  'Xenova/bge-m3',
  'BAAI/bge-small-en-v1.5',
  'BAAI/bge-base-en-v1.5',
  'BAAI/bge-m3',
  'Xenova/multilingual-e5-small',
  'Xenova/multilingual-e5-base',
  'intfloat/multilingual-e5-small',
  'intfloat/multilingual-e5-base',
]);

// E5 models use "query: " prefix instead of BGE's longer instruction
const E5_MODELS = new Set([
  'Xenova/multilingual-e5-small',
  'Xenova/multilingual-e5-base',
  'intfloat/multilingual-e5-small',
  'intfloat/multilingual-e5-base',
]);

export class LocalEmbeddingProvider extends BaseEmbeddingProvider {
  readonly dimensions: number;
  readonly modelName: string;
  readonly maxBatchSize = 16;  // Safe now that node_modules excluded (no 4MB+ texts)
  readonly maxTokensPerText = 256; // Truncate long texts to prevent tokenizer stack overflow

  private pipelinePromise: Promise<unknown> | null = null;
  private readonly useInstruction: boolean;
  private readonly isE5: boolean;

  constructor(options?: { model?: string; dimensions?: number }) {
    super();
    this.modelName = options?.model || 'Xenova/bge-small-en-v1.5';
    this.dimensions = options?.dimensions || MODEL_PRESETS[this.modelName] || 384;
    this.useInstruction = INSTRUCTION_MODELS.has(this.modelName);
    this.isE5 = E5_MODELS.has(this.modelName);
  }

  /**
   * Lazy-load the feature extraction pipeline.
   * Model is downloaded on first use and cached locally.
   */
  private async getPipeline(): Promise<unknown> {
    if (!this.pipelinePromise) {
      this.pipelinePromise = (async () => {
        console.warn(`[wki] Loading local embedding model: ${this.modelName} ...`);
        const startMs = Date.now();

        const { pipeline, env } = await import('@huggingface/transformers');

        // Use default cache dir (~/.cache/huggingface), disable remote model fetch check warnings
        env.allowLocalModels = true;

        const pipe = await pipeline('feature-extraction', this.modelName, {
          dtype: 'fp32',
        });

        const elapsedMs = Date.now() - startMs;
        console.warn(`[wki] Model loaded in ${elapsedMs}ms (dims=${this.dimensions})`);

        return pipe;
      })();
    }
    return this.pipelinePromise;
  }

  protected async embedBatch(texts: string[]): Promise<number[][]> {
    const pipe = (await this.getPipeline()) as (
      texts: string[],
      options: { pooling: string; normalize: boolean },
    ) => Promise<{ tolist(): number[][] }>;

    // Truncate texts to maxTokensPerText (approximate: 1 token ≈ 4 chars)
    // This prevents stack overflow in the tokenizer for very long texts
    const maxChars = this.maxTokensPerText * 4;
    const truncatedTexts = texts.map((t) =>
      t.length > maxChars ? t.slice(0, maxChars) : t,
    );

    // Model-specific query prefixes for better retrieval
    const preparedTexts = this.isE5
      ? truncatedTexts.map((t) => `query: ${t}`)
      : this.useInstruction
        ? truncatedTexts.map((t) => `Represent this sentence for searching relevant passages: ${t}`)
        : truncatedTexts;

    const output = await pipe(preparedTexts, {
      pooling: 'mean',
      normalize: true,
    });

    const embeddings = output.tolist();

    // Truncate or validate dimensions
    return embeddings.map((emb) => {
      if (emb.length === this.dimensions) {
        return emb;
      }
      // If model outputs more dims than configured, truncate (Matryoshka support)
      if (emb.length > this.dimensions) {
        const truncated = emb.slice(0, this.dimensions);
        // Re-normalize after truncation
        const norm = Math.sqrt(truncated.reduce((sum, v) => sum + v * v, 0));
        return norm > 0 ? truncated.map((v) => v / norm) : truncated;
      }
      return emb;
    });
  }
}
