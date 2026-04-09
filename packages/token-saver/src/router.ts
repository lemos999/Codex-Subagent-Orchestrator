// Command Router: 첫 토큰으로 압축기 선택
// DC-2: 첫 토큰 매칭 방식

import { getCompressor, type Compressor } from './registry.js';

/**
 * Route a bash command to the appropriate compressor.
 * Extracts the first token (command name) and looks up the registry.
 * For compound commands (cd X && cmd), tries each segment.
 * Falls back to passthrough if no compressor matches.
 */
export function route(cmd: string): Compressor {
  // Pipe commands: user already controls output → passthrough (원칙 1)
  if (cmd.includes('|')) {
    return (stdout: string) => stdout;
  }

  // Handle compound commands: "cd dir && git status" → try each segment
  const segments = cmd.split(/\s*&&\s*|\s*;\s*/);
  for (const segment of segments) {
    const token = extractFirstToken(segment.trim());
    // Skip cd, export, and other shell builtins that aren't real commands
    if (['cd', 'export', 'source', 'echo', 'set', 'unset', 'pushd', 'popd'].includes(token)) continue;
    const compressor = getCompressor(token);
    if (compressor !== getCompressor('__nonexistent__')) return compressor;
  }
  // Fallback: use first segment's token
  const firstToken = extractFirstToken(cmd);
  return getCompressor(firstToken);
}

/**
 * Extract the first meaningful token from a command string.
 * Handles: env vars (FOO=bar cmd), sudo, npx/bunx prefixes.
 */
function extractFirstToken(cmd: string): string {
  const tokens = cmd.trim().split(/\s+/);

  for (const token of tokens) {
    // Skip env var assignments (KEY=VALUE)
    if (token.includes('=') && !token.startsWith('-')) continue;
    // Skip common prefixes
    if (['sudo', 'npx', 'bunx', 'pnpm', 'yarn'].includes(token)) continue;
    // Return the actual command
    return token;
  }

  return tokens[0] ?? '';
}
