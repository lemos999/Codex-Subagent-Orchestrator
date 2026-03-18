import ts from 'typescript';
import path from 'node:path';
import { normalizePath } from '../utils/path.js';
import type { RawChunk, SymbolInfo, ImportInfo, ChunkType } from '../types/index.js';
import type { ProgramParser, TsParserResult } from '../interfaces/parser.js';

/** Map symbol kind to ChunkType; unknown kinds fall back to 'other'. */
const CHUNK_TYPE_MAP: Record<string, ChunkType> = {
  function: 'function',
  class: 'class',
  interface: 'interface',
  type: 'type',
  enum: 'enum',
  variable: 'variable',
};

function toChunkType(kind: string): ChunkType {
  return CHUNK_TYPE_MAP[kind] ?? 'other';
}

/**
 * TypeScript Compiler API-based program parser.
 * Extracts symbols, imports, and produces RawChunks per top-level declaration.
 */
export class TsParser implements ProgramParser {
  private program: ts.Program | null = null;
  private compilerOptions: ts.CompilerOptions = {};
  private rootDir = '';

  /** Initialize TS program from rootDir with optional tsconfig path. */
  initProgram(rootDir: string, tsConfigPath?: string): void {
    this.rootDir = rootDir;
    let fileNames: string[] = [];

    if (tsConfigPath) {
      const configResult = this.readTsConfig(tsConfigPath);
      fileNames = configResult.fileNames;
      this.compilerOptions = configResult.options;
    } else {
      const found = ts.findConfigFile(rootDir, ts.sys.fileExists, 'tsconfig.json');
      if (found) {
        const configResult = this.readTsConfig(found);
        fileNames = configResult.fileNames;
        this.compilerOptions = configResult.options;
      } else {
        this.compilerOptions = {
          target: ts.ScriptTarget.ES2022,
          module: ts.ModuleKind.Node16,
          moduleResolution: ts.ModuleResolutionKind.Node16,
          strict: true,
          esModuleInterop: true,
          allowJs: true,
        };
        fileNames = this.findSourceFiles(rootDir);
      }
    }

    this.program = ts.createProgram(fileNames, this.compilerOptions);
  }

  /** Parse all project files (excluding node_modules/external). */
  parseProgram(): Map<string, TsParserResult> {
    if (!this.program) {
      throw new Error('TsParser: program not initialized. Call initProgram() first.');
    }

    const results = new Map<string, TsParserResult>();
    const sourceFiles = this.program.getSourceFiles();

    for (const sf of sourceFiles) {
      const normalized = normalizePath(sf.fileName);
      if (normalized.includes('node_modules')) continue;
      if (sf.isDeclarationFile) continue;

      try {
        const result = this.parseSourceFile(sf);
        results.set(normalized, result);
      } catch (err) {
        console.warn(`TsParser: failed to parse ${sf.fileName}:`, err); // TODO: Phase 1B+ -- Logger 인터페이스 도입 후 교체
      }
    }

    return results;
  }

  /** Parse a single file within the program context. */
  parseFile(filePath: string): TsParserResult {
    if (!this.program) {
      throw new Error('TsParser: program not initialized. Call initProgram() first.');
    }

    const sourceFile = this.program.getSourceFile(filePath);
    if (!sourceFile) {
      throw new Error(`TsParser: source file not found in program: ${filePath}`);
    }

    return this.parseSourceFile(sourceFile);
  }

  dispose(): void {
    this.program = null;
  }

  // ----------------------------------------------------------------
  // Private helpers
  // ----------------------------------------------------------------

  private readTsConfig(configPath: string): ts.ParsedCommandLine {
    const configFile = ts.readConfigFile(configPath, ts.sys.readFile);
    if (configFile.error) {
      throw new Error(`Failed to read tsconfig: ${ts.flattenDiagnosticMessageText(configFile.error.messageText, '\n')}`);
    }
    return ts.parseJsonConfigFileContent(
      configFile.config,
      ts.sys,
      path.dirname(configPath),
    );
  }

  private findSourceFiles(dir: string): string[] {
    const files: string[] = [];
    const entries = ts.sys.readDirectory(dir, ['.ts', '.tsx'], ['node_modules', 'dist'], undefined);
    files.push(...entries);
    return files;
  }

  private parseSourceFile(sourceFile: ts.SourceFile): TsParserResult {
    const filePath = normalizePath(sourceFile.fileName);
    const chunks: RawChunk[] = [];
    const symbols: SymbolInfo[] = [];
    const imports: ImportInfo[] = [];
    let ordinal = 0;

    // #10: Cache split result to avoid repeated sourceFile.text.split('\n')
    const lines = sourceFile.text.split('\n');
    const totalLines = lines.length;

    // Track which line ranges are covered by symbol chunks
    const coveredRanges: Array<{ start: number; end: number }> = [];

    ts.forEachChild(sourceFile, (node) => {
      // Extract imports
      if (ts.isImportDeclaration(node)) {
        const importInfo = this.extractImport(node, filePath, sourceFile);
        if (importInfo) {
          imports.push(importInfo);
        }
        return;
      }

      // Extract symbols and create chunks
      const symbolInfo = this.extractSymbol(node, filePath, sourceFile);
      if (symbolInfo) {
        symbols.push(symbolInfo);

        const startLine = symbolInfo.startLine;
        const endLine = symbolInfo.endLine;
        const content = lines.slice(startLine - 1, endLine).join('\n');

        chunks.push({
          filePath,
          ordinal: ordinal++,
          content,
          heading: symbolInfo.name,
          chunkType: toChunkType(symbolInfo.kind),
          startLine,
          endLine,
        });

        coveredRanges.push({ start: startLine, end: endLine });
      }
    });

    // Collect uncovered lines into "other" chunks
    const otherChunks = this.collectUncoveredLinesFromCache(filePath, lines, coveredRanges, totalLines, ordinal);
    chunks.push(...otherChunks);

    // Sort chunks by startLine for consistent ordering
    chunks.sort((a, b) => a.startLine - b.startLine);
    // Re-assign ordinals after sorting
    for (let i = 0; i < chunks.length; i++) {
      chunks[i].ordinal = i;
    }

    return { chunks, symbols, imports };
  }

  private extractSymbol(node: ts.Node, filePath: string, sourceFile: ts.SourceFile): SymbolInfo | null {
    let name: string | undefined;
    let kind: string;
    let signature: string | undefined;
    const modifiers: string[] = [];

    if (ts.isFunctionDeclaration(node)) {
      name = node.name?.getText(sourceFile);
      kind = 'function';
      signature = this.extractFunctionSignature(node, sourceFile);
    } else if (ts.isClassDeclaration(node)) {
      name = node.name?.getText(sourceFile);
      kind = 'class';
    } else if (ts.isInterfaceDeclaration(node)) {
      name = node.name?.getText(sourceFile);
      kind = 'interface';
    } else if (ts.isTypeAliasDeclaration(node)) {
      name = node.name?.getText(sourceFile);
      kind = 'type';
    } else if (ts.isEnumDeclaration(node)) {
      name = node.name?.getText(sourceFile);
      kind = 'enum';
    } else if (ts.isVariableStatement(node)) {
      kind = 'variable';
      const decls = node.declarationList.declarations;
      if (decls.length > 0 && decls[0].name) {
        name = decls[0].name.getText(sourceFile);
      }
      const flags = node.declarationList.flags;
      if (flags & ts.NodeFlags.Const) modifiers.push('const');
      else if (flags & ts.NodeFlags.Let) modifiers.push('let');
      else modifiers.push('var');
    } else if (ts.isModuleDeclaration(node)) {
      name = node.name?.getText(sourceFile);
      kind = 'namespace';
    } else if (ts.isExportDeclaration(node)) {
      // Re-export without name — skip as symbol but still part of code
      return null;
    } else {
      return null;
    }

    if (!name) {
      // Anonymous declarations (e.g., `export default function()`) get a fallback name
      name = '<anonymous>';
    }

    // Check exported status
    const nodeModifiers = ts.canHaveModifiers(node) ? ts.getModifiers(node) : undefined;
    let exported = false;
    if (nodeModifiers) {
      for (const mod of nodeModifiers) {
        if (mod.kind === ts.SyntaxKind.ExportKeyword) exported = true;
        if (mod.kind === ts.SyntaxKind.AsyncKeyword) modifiers.push('async');
        if (mod.kind === ts.SyntaxKind.AbstractKeyword) modifiers.push('abstract');
        if (mod.kind === ts.SyntaxKind.ReadonlyKeyword) modifiers.push('readonly');
        if (mod.kind === ts.SyntaxKind.StaticKeyword) modifiers.push('static');
        if (mod.kind === ts.SyntaxKind.DefaultKeyword) modifiers.push('default');
      }
    }

    // Extract docstring from leading comments
    const docstring = this.extractDocstring(node, sourceFile);

    // Line positions (1-based)
    const startPos = sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile));
    const endPos = sourceFile.getLineAndCharacterOfPosition(node.getEnd());

    return {
      name,
      kind,
      filePath,
      startLine: startPos.line + 1,
      endLine: endPos.line + 1,
      signature,
      docstring,
      exported,
      modifiers: modifiers.length > 0 ? modifiers : undefined,
    };
  }

  private extractFunctionSignature(node: ts.FunctionDeclaration, sourceFile: ts.SourceFile): string {
    const params = node.parameters.map((p) => p.getText(sourceFile)).join(', ');
    const returnType = node.type ? `: ${node.type.getText(sourceFile)}` : '';
    return `(${params})${returnType}`;
  }

  private extractDocstring(node: ts.Node, sourceFile: ts.SourceFile): string | undefined {
    const fullText = sourceFile.getFullText();
    const ranges = ts.getLeadingCommentRanges(fullText, node.getFullStart());
    if (!ranges || ranges.length === 0) return undefined;

    // Take the last comment block before the node (likely JSDoc)
    const lastRange = ranges[ranges.length - 1];
    const comment = fullText.slice(lastRange.pos, lastRange.end).trim();

    // Only return if it looks like a doc comment
    if (comment.startsWith('/**') || comment.startsWith('///')) {
      return comment;
    }
    return undefined;
  }

  private extractImport(node: ts.ImportDeclaration, filePath: string, sourceFile: ts.SourceFile): ImportInfo | null {
    const moduleSpecifier = node.moduleSpecifier;
    if (!ts.isStringLiteral(moduleSpecifier)) return null;

    const source = moduleSpecifier.text; // already unquoted
    const specifiers: string[] = [];
    let isTypeOnly = false;

    const clause = node.importClause;
    if (clause) {
      isTypeOnly = clause.isTypeOnly;

      // Default import
      if (clause.name) {
        specifiers.push(clause.name.getText(sourceFile));
      }

      // Named bindings
      if (clause.namedBindings) {
        if (ts.isNamedImports(clause.namedBindings)) {
          for (const element of clause.namedBindings.elements) {
            specifiers.push(element.name.getText(sourceFile));
          }
        } else if (ts.isNamespaceImport(clause.namedBindings)) {
          specifiers.push(`* as ${clause.namedBindings.name.getText(sourceFile)}`);
        }
      }
    }

    return {
      source: filePath,
      target: source,
      specifiers,
      isTypeOnly,
    };
  }

  /** Collect uncovered lines using pre-split lines array (avoids repeated split). */
  private collectUncoveredLinesFromCache(
    filePath: string,
    lines: string[],
    coveredRanges: Array<{ start: number; end: number }>,
    totalLines: number,
    startOrdinal: number,
  ): RawChunk[] {
    if (totalLines === 0) return [];

    const covered = new Set<number>();
    for (const r of coveredRanges) {
      for (let i = r.start; i <= r.end; i++) {
        covered.add(i);
      }
    }

    const chunks: RawChunk[] = [];
    let ordinal = startOrdinal;
    let blockStart: number | null = null;

    for (let line = 1; line <= totalLines; line++) {
      if (!covered.has(line)) {
        if (blockStart === null) blockStart = line;
      } else {
        if (blockStart !== null) {
          const content = lines.slice(blockStart - 1, line - 1).join('\n').trim();
          if (content.length > 0) {
            chunks.push({
              filePath,
              ordinal: ordinal++,
              content,
              chunkType: 'other',
              startLine: blockStart,
              endLine: line - 1,
            });
          }
          blockStart = null;
        }
      }
    }

    if (blockStart !== null) {
      const content = lines.slice(blockStart - 1, totalLines).join('\n').trim();
      if (content.length > 0) {
        chunks.push({
          filePath,
          ordinal: ordinal++,
          content,
          chunkType: 'other',
          startLine: blockStart,
          endLine: totalLines,
        });
      }
    }

    return chunks;
  }

  // NOTE: collectUncoveredLines removed -- replaced by collectUncoveredLinesFromCache (#10 fix)
}
