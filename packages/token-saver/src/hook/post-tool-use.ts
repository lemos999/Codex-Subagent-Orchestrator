#!/usr/bin/env node

interface HookInput {
  hook_event_name: string;
  tool_name: string;
  tool_input: Record<string, unknown>;
  tool_output?: string;
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
  switch (input.tool_name) {
    case 'Read': return handleRead(input);
    case 'Grep': return handleGrep(input);
    default: return {};
  }
}

function handleRead(input: HookInput): Record<string, unknown> {
  const limit = input.tool_input.limit as number | undefined;

  // No limit specified → full file read, suggest using offset/limit
  if (!limit) {
    return {
      additionalContext:
        `⚡ CTS: 파일을 limit 없이 읽었습니다. 필요한 부분만 offset/limit으로 재읽기하면 토큰을 절약할 수 있습니다.`,
    };
  }

  // limit >= 1000 → still a large read
  if (limit >= 1000) {
    return {
      additionalContext:
        `⚡ CTS: ${limit}줄 읽음. 목적에 필요한 범위만 읽으면 토큰 절약 가능.`,
    };
  }

  return {};
}

function handleGrep(input: HookInput): Record<string, unknown> {
  // tool_output may not be provided in PostToolUse; only hint if available
  if (input.tool_output) {
    const lines = input.tool_output.split('\n').length;
    if (lines > 100) {
      return {
        additionalContext:
          `⚡ CTS: ${lines}건 결과. head_limit 사용 권장.`,
      };
    }
  }
  return {};
}

main();
