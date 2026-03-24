import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { TsParser } from '../../src/parsers/ts-parser.js';
import { normalizePath } from '../../src/utils/path.js';

describe('TsParser', () => {
  let tempDir: string;
  let parser: TsParser;

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));
    parser = new TsParser();
  });

  afterEach(() => {
    parser.dispose();

    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  it('extracts function symbols with signature and docstring metadata', () => {
    const filePath = writeTsFile(
      'functions.ts',
      [
        '/** Adds two numbers. */',
        'export async function add(a: number, b: number): number {',
        '  return a + b;',
        '}',
      ].join('\n'),
    );

    parser.initProgram(tempDir);
    const result = parser.parseFile(filePath);

    expect(result.symbols).toHaveLength(1);
    expect(result.symbols[0]).toMatchObject({
      name: 'add',
      kind: 'function',
      filePath: normalizePath(filePath),
      startLine: 2,
      endLine: 4,
      signature: '(a: number, b: number): number',
      exported: true,
      modifiers: ['async'],
    });
    expect(result.symbols[0]?.docstring).toContain('Adds two numbers');
    // TS 파서는 심볼 청크 + 미포함 코드("기타") 청크를 생성할 수 있음
    expect(result.chunks.length).toBeGreaterThanOrEqual(1);
    const funcChunk = result.chunks.find(c => c.chunkType === 'function');
    expect(funcChunk).toMatchObject({
      heading: 'add',
      chunkType: 'function',
    });
  });

  it('parses classes as top-level symbols and keeps methods in the class chunk', () => {
    const filePath = writeTsFile(
      'greeter.ts',
      [
        'export class Greeter {',
        '  greet(name: string): string {',
        '    return `Hello ${name}`;',
        '  }',
        '',
        '  static version(): string {',
        '    return "1.0.0";',
        '  }',
        '}',
      ].join('\n'),
    );

    parser.initProgram(tempDir);
    const result = parser.parseFile(filePath);

    expect(result.symbols).toHaveLength(1);
    expect(result.symbols[0]).toMatchObject({
      name: 'Greeter',
      kind: 'class',
      exported: true,
      startLine: 1,
      endLine: 9,
    });
    expect(result.chunks[0]?.content).toContain('greet(name: string)');
    expect(result.chunks[0]?.content).toContain('static version()');
  });

  it('extracts interface and type declarations', () => {
    const filePath = writeTsFile(
      'contracts.ts',
      [
        'export interface User {',
        '  id: string;',
        '}',
        '',
        'export type UserId = User["id"];',
      ].join('\n'),
    );

    parser.initProgram(tempDir);
    const result = parser.parseFile(filePath);

    expect(result.symbols).toHaveLength(2);
    expect(result.symbols.map((symbol) => [symbol.name, symbol.kind, symbol.exported])).toEqual([
      ['User', 'interface', true],
      ['UserId', 'type', true],
    ]);
    expect(result.chunks.map((chunk) => chunk.chunkType)).toEqual(['interface', 'type']);
  });

  it('marks exported and non-exported declarations correctly', () => {
    const filePath = writeTsFile(
      'exports.ts',
      [
        'export const publicValue = 1;',
        'const privateValue = 2;',
        'export default function main(): number {',
        '  return publicValue + privateValue;',
        '}',
      ].join('\n'),
    );

    parser.initProgram(tempDir);
    const result = parser.parseFile(filePath);

    const publicValue = result.symbols.find((symbol) => symbol.name === 'publicValue');
    const privateValue = result.symbols.find((symbol) => symbol.name === 'privateValue');
    const main = result.symbols.find((symbol) => symbol.name === 'main');

    expect(publicValue?.exported).toBe(true);
    expect(privateValue?.exported).toBe(false);
    expect(main?.exported).toBe(true);
    expect(main?.modifiers).toContain('default');
  });

  it('extracts default, named, namespace, and type-only imports', () => {
    writeTsFile('types.ts', 'export interface Payload { id: string; }');
    writeTsFile('helpers.ts', 'export const renamed = 1;');
    const filePath = writeTsFile(
      'imports.ts',
      [
        "import fs from 'node:fs';",
        "import type { Payload } from './types.js';",
        "import { renamed as helper } from './helpers.js';",
        "import * as pathModule from 'node:path';",
        '',
        'export const value = fs.existsSync(pathModule.sep) ? helper : 0;',
      ].join('\n'),
    );

    parser.initProgram(tempDir);
    const result = parser.parseFile(filePath);

    expect(result.imports).toEqual([
      {
        source: normalizePath(filePath),
        target: 'node:fs',
        specifiers: ['fs'],
        isTypeOnly: false,
      },
      {
        source: normalizePath(filePath),
        target: './types.js',
        specifiers: ['Payload'],
        isTypeOnly: true,
      },
      {
        source: normalizePath(filePath),
        target: './helpers.js',
        specifiers: ['helper'],
        isTypeOnly: false,
      },
      {
        source: normalizePath(filePath),
        target: 'node:path',
        specifiers: ['* as pathModule'],
        isTypeOnly: false,
      },
    ]);
  });

  it('returns empty results for an empty file', () => {
    const filePath = writeTsFile('empty.ts', '');

    parser.initProgram(tempDir);
    const result = parser.parseFile(filePath);

    expect(result.symbols).toEqual([]);
    expect(result.imports).toEqual([]);
    expect(result.chunks).toEqual([]);
  });

  it('handles TypeScript syntax errors without throwing', () => {
    const filePath = writeTsFile(
      'broken.ts',
      [
        'function broken(',
        'const value = 1;',
      ].join('\n'),
    );

    parser.initProgram(tempDir);

    expect(() => parser.parseFile(filePath)).not.toThrow();

    const result = parser.parseFile(filePath);
    expect(result.symbols[0]).toMatchObject({
      name: 'broken',
      kind: 'function',
    });
    expect(result.chunks[0]?.content).toContain('const value = 1;');
  });

  function writeTsFile(relativePath: string, content: string): string {
    const filePath = path.join(tempDir, relativePath);
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, content, 'utf8');
    return filePath;
  }
});
