import type { Compressor } from '../registry.js';

/**
 * Generic Compressor — ls/find/cat etc. output truncation.
 * Lines over MAX_LINES are compressed: head + summary + tail.
 */
export const genericCompressor: Compressor = (stdout, _stderr, _cmd) => {
  const lines = stdout.split('\n');
  const MAX_LINES = 50;

  if (lines.length <= MAX_LINES) return stdout;

  const head = lines.slice(0, 40);
  const tail = lines.slice(-5);
  const omitted = lines.length - 45;

  return [
    ...head,
    `\n... (${omitted} lines omitted, ${lines.length} total)\n`,
    ...tail,
  ].join('\n');
};
