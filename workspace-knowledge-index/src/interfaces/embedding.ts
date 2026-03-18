/**
 * Provider adapter for text embedding.
 * Implementations: OpenAI, Voyage, Local (ONNX).
 */
export interface EmbeddingProvider {
  embed(text: string): Promise<number[]>;
  batchEmbed(texts: string[]): Promise<number[][]>;
  readonly dimensions: number;
  readonly modelName: string;
}
