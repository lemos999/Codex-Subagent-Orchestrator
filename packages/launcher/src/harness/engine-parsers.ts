/**
 * C2: EngineOutputParser — engine-specific stdout parsers.
 * Each parser converts raw chunks into HarnessEvent[].
 */

import type { Engine } from '../types/engine.js';
import type { HarnessEvent } from './types.js';

export interface ParserContext {
  sessionId: string;
  workerName: string;
  engine: Engine;
  buffer: string;
}

export type ChunkParser = (chunk: string, ctx: ParserContext) => HarnessEvent[];

// ============================================================
// Codex parser — structured JSON event lines
// ============================================================

function parseCodexChunk(chunk: string, ctx: ParserContext): HarnessEvent[] {
  const events: HarnessEvent[] = [];
  const combined = ctx.buffer + chunk;
  const lines = combined.split('\n');

  // Last element may be incomplete — keep in buffer
  ctx.buffer = lines.pop() ?? '';

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    try {
      const entry = JSON.parse(trimmed) as Record<string, unknown>;
      const ts = now();

      // Function call → tool_use
      if (entry['type'] === 'function_call' || entry['function_call']) {
        const name = String(
          (entry['function_call'] as Record<string, unknown>)?.['name'] ??
          entry['name'] ??
          'unknown',
        );
        events.push({
          type: 'worker.tool_use',
          sessionId: ctx.sessionId,
          name: ctx.workerName,
          tool: name,
          timestamp: ts,
        });
      }

      // Message/text content → message
      const content = entry['content'] ?? entry['text'] ?? entry['message'];
      if (typeof content === 'string' && content.trim()) {
        events.push({
          type: 'worker.message',
          sessionId: ctx.sessionId,
          name: ctx.workerName,
          text: content.trim(),
          timestamp: ts,
        });
      }
    } catch {
      // Not JSON — emit as raw message
      if (trimmed.length > 0) {
        events.push({
          type: 'worker.message',
          sessionId: ctx.sessionId,
          name: ctx.workerName,
          text: trimmed,
          timestamp: now(),
        });
      }
    }
  }

  return events;
}

// ============================================================
// Claude parser — free text, best-effort tool detection
// ============================================================

function parseClaudeChunk(chunk: string, ctx: ParserContext): HarnessEvent[] {
  const events: HarnessEvent[] = [];
  const combined = ctx.buffer + chunk;
  const lines = combined.split('\n');

  ctx.buffer = lines.pop() ?? '';

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    events.push({
      type: 'worker.message',
      sessionId: ctx.sessionId,
      name: ctx.workerName,
      text: trimmed,
      timestamp: now(),
    });
  }

  return events;
}

// ============================================================
// Gemini parser — same as Claude (free text)
// ============================================================

function parseGeminiChunk(chunk: string, ctx: ParserContext): HarnessEvent[] {
  return parseClaudeChunk(chunk, ctx);
}

// ============================================================
// Parser registry
// ============================================================

export const ENGINE_PARSERS: Record<Engine, ChunkParser> = {
  codex: parseCodexChunk,
  'codex-mcp': parseCodexChunk,
  claude: parseClaudeChunk,
  gemini: parseGeminiChunk,
};

export function getParser(engine: Engine): ChunkParser {
  return ENGINE_PARSERS[engine] ?? parseClaudeChunk;
}

function now(): string {
  return new Date().toISOString();
}
