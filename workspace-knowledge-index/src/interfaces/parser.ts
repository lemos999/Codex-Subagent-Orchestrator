import type { RawChunk, SymbolInfo, ImportInfo } from '../types/index.js';

/**
 * FileParser — MD/라인 청킹용 (단일 파일, 동기).
 * Implementations: remark (MD), line-based (generic).
 */
export interface FileParser {
  parse(filePath: string, content: string): RawChunk[];
  readonly supportedExtensions: string[];
}

/**
 * ProgramParser — TS Compiler API용 (프로그램 단위).
 * Operates on an entire program/project for cross-file analysis.
 */
export interface ProgramParser {
  initProgram(rootDir: string, tsConfigPath?: string): void;
  parseProgram(): Map<string, TsParserResult>;
  parseFile(filePath: string): TsParserResult;
  dispose(): void;
}

/** Result from ProgramParser containing chunks, symbols, and imports. */
export interface TsParserResult {
  chunks: RawChunk[];
  symbols: SymbolInfo[];
  imports: ImportInfo[];
}
