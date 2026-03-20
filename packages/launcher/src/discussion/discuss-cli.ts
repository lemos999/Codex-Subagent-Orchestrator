#!/usr/bin/env node
/**
 * /discuss CLI entry point.
 * Usage: node discuss-cli.js "topic"
 *        node discuss-cli.js --spec discussion.json
 */

import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import * as readline from 'node:readline';
import { parseDiscussionSpec } from './discussion-spec.js';
import { runDiscussion, type RoundResult } from './discussion-runner.js';

// ============================================================
// User interaction
// ============================================================

function createReadline(): readline.Interface {
  return readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
}

async function askUser(rl: readline.Interface, prompt: string): Promise<string> {
  return new Promise((resolve) => {
    rl.question(prompt, (answer) => resolve(answer.trim()));
  });
}

function displayRoundResult(round: RoundResult): void {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`  Round ${round.round} 완료`);
  console.log('='.repeat(60));

  for (const [engine, response] of round.responses) {
    const preview = response.split('\n').slice(0, 3).join('\n  ');
    const position = response.match(/\[POSITION:(.+?)\]/)?.[1]?.trim() ?? '(미명시)';
    console.log(`\n  ${engine.toUpperCase()}: ${position}`);
    console.log(`  ${preview}...`);
  }

  if (round.convergence) {
    console.log(`\n  수렴 상태: ${round.convergence.toUpperCase()}`);
  }

  console.log('');
}

// ============================================================
// Main
// ============================================================

async function main(): Promise<void> {
  const args = process.argv.slice(2);

  if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
    console.log(`
Usage:
  node discuss-cli.js "토론 주제"
  node discuss-cli.js --spec discussion.json

Options:
  --spec <path>   JSON spec file for advanced configuration
  --help          Show this help
`);
    process.exit(0);
  }

  // Parse spec
  let spec;
  if (args[0] === '--spec' && args[1]) {
    const specPath = path.resolve(args[1]);
    const raw = JSON.parse(await fs.readFile(specPath, 'utf8'));
    spec = parseDiscussionSpec(raw);
  } else {
    spec = parseDiscussionSpec(args.join(' '));
  }

  // Display execution plan
  console.log(`
${'='.repeat(60)}
  /discuss Execution Plan
${'='.repeat(60)}

  Topic:        ${spec.topic}
  Max rounds:   ${spec.max_rounds}
  Participants: ${spec.participants.map((p) => `${p.engine} (${p.model ?? 'default'})`).join(', ')}
  Moderator:    Claude (separate, judgment only)
  Output:       ${spec.output_dir}
`);

  const rl = createReadline();
  const approval = await askUser(rl, '  > yes — 토론 시작 / no — 취소 / modify — 변경: ');

  if (approval.toLowerCase() === 'no' || approval.toLowerCase() === 'n') {
    console.log('  취소되었습니다.');
    rl.close();
    process.exit(0);
  }

  if (approval.toLowerCase() !== 'yes' && approval.toLowerCase() !== 'y') {
    console.log('  현재 modify는 미지원입니다. yes 또는 no를 입력해주세요.');
    rl.close();
    process.exit(1);
  }

  // Run discussion
  const result = await runDiscussion(spec, {
    onRoundComplete: async (round: RoundResult) => {
      displayRoundResult(round);

      const answer = await askUser(rl, '  > continue — 다음 라운드 / stop — 종료 / guide "지시" — 방향 추가: ');

      if (answer.toLowerCase() === 'stop' || answer.toLowerCase() === 's') {
        return { action: 'stop' as const };
      }

      if (answer.toLowerCase().startsWith('guide ')) {
        return {
          action: 'guide' as const,
          guidance: answer.slice(6).trim(),
        };
      }

      return { action: 'continue' as const };
    },
    onStatus: (message: string) => {
      console.log(`  [discuss] ${message}`);
    },
  });

  rl.close();

  // Display final result
  console.log(`
${'='.repeat(60)}
  토론 완료
${'='.repeat(60)}

  Topic:      ${result.topic}
  Rounds:     ${result.totalRounds}
  Converged:  ${result.converged ? '합의 도출' : '쟁점 남음'}
  Evidence:   ${spec.output_dir}

  결론 미리보기:
  ${result.conclusion.split('\n').slice(0, 5).join('\n  ')}
`);

  process.exit(result.converged ? 0 : 1);
}

main().catch((err) => {
  console.error('FATAL:', err instanceof Error ? err.message : String(err));
  process.exit(1);
});
