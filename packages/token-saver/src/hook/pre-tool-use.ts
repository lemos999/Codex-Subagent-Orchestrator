#!/usr/bin/env node

import { isExempt } from '../exempt.js';
import * as path from 'node:path';

interface HookInput {
  hook_event_name: string;
  tool_name: string;
  tool_input: {
    command?: string;
    [key: string]: unknown;
  };
}

function main(): void {
  let input = '';

  process.stdin.setEncoding('utf-8');
  process.stdin.on('data', (chunk) => { input += chunk; });
  process.stdin.on('end', () => {
    try {
      const hookInput: HookInput = JSON.parse(input);
      const result = processHook(hookInput);
      process.stdout.write(JSON.stringify(result));
    } catch {
      // Parse failure → pass through (don't break Claude Code)
      process.stdout.write('{}');
    }
  });
}

function processHook(input: HookInput): Record<string, unknown> {
  // Only intercept Bash tool
  if (input.tool_name !== 'Bash') return {};

  const cmd = input.tool_input.command;
  if (!cmd || typeof cmd !== 'string') return {};

  // Prevent recursion
  if (cmd.includes('token-saver') || cmd.includes('cts exec')) return {};

  // Check exempt
  if (isExempt(cmd)) return {};

  // Rewrite command
  // Use absolute path to avoid PATH issues on Windows
  const ctsPath = path.resolve(__dirname, '..', 'index.js');

  // Shell-escape the original command for safe wrapping
  const escapedCmd = cmd.replace(/'/g, "'\\''");

  return {
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'allow',
      updatedInput: {
        command: `node "${ctsPath}" exec $'${escapedCmd}'`,
      },
    },
  };
}

main();
