// Compressor Registry: 명령→압축기 하드코딩 Map
// DC-3: v1은 하드코딩, v2에서 플러그인화

import { gitCompressor } from './compressors/git.js';
import { testCompressor } from './compressors/test.js';
import { genericCompressor } from './compressors/generic.js';

export type Compressor = (stdout: string, stderr: string, cmd: string) => string;

/**
 * Passthrough compressor: returns output unchanged.
 */
const passthrough: Compressor = (stdout) => stdout;

/**
 * Command → Compressor mapping.
 * Key: first token of the command (after prefix stripping).
 */
const REGISTRY: Record<string, Compressor> = {
  // Git commands → Git Compressor
  git: gitCompressor,
  gh: gitCompressor,

  // Test runners → Test Compressor
  vitest: testCompressor,
  jest: testCompressor,
  pytest: testCompressor,
  mocha: testCompressor,

  // Generic commands → Generic Compressor
  ls: genericCompressor,
  find: genericCompressor,
  cat: genericCompressor,
  head: genericCompressor,
  tail: genericCompressor,
  wc: genericCompressor,
};

/**
 * Get the compressor for a given command name.
 * Returns passthrough if no match.
 */
export function getCompressor(commandName: string): Compressor {
  return REGISTRY[commandName] ?? passthrough;
}
