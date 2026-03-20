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
import { runDiscussion, fetchWkiContext, type RoundResult } from './discussion-runner.js';

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
    const failed = round.failedEngines.includes(engine);
    const position = response.match(/\[POSITION:(.+?)\]/)?.[1]?.trim() ?? '(미명시)';
    const label = failed ? '[FAILED]' : '';
    console.log(`\n  ${engine.toUpperCase()} ${label}: ${position}`);
    const preview = response.split('\n').slice(0, 3).join('\n  ');
    console.log(`  ${preview}...`);
  }

  if (round.convergence) {
    console.log(`\n  수렴 상태: ${round.convergence.toUpperCase()}`);
  }

  if (round.failedEngines.length > 0) {
    console.log(`  실패 엔진: ${round.failedEngines.join(', ')} (2-of-3으로 계속)`);
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

  // #4 fix: fetch WKI context BEFORE showing approval plan
  console.log('  [discuss] WKI 맥락 검색 중...');
  const wkiContext = await fetchWkiContext(spec.topic);
  const wkiPreview = wkiContext
    ? wkiContext.split('\n').slice(0, 5).join('\n    ')
    : '(WKI 맥락 없음)';

  // Display execution plan (with WKI context preview)
  console.log(`
${'='.repeat(60)}
  /discuss Execution Plan
${'='.repeat(60)}

  Topic:        ${spec.topic}
  Max rounds:   ${spec.max_rounds}
  Participants: ${spec.participants.map((p) => `${p.engine} (${p.model ?? 'default'})`).join(', ')}
  Moderator:    Claude (separate, judgment only)
  Output:       ${spec.output_dir}
  WKI context:
    ${wkiPreview}
`);

  const rl = createReadline();
  // #3 fix: removed 'modify' from options (not implemented)
  const approval = await askUser(rl, '  > yes — 토론 시작 / no — 취소: ');

  if (approval.toLowerCase() !== 'yes' && approval.toLowerCase() !== 'y') {
    console.log('  취소되었습니다.');
    rl.close();
    process.exit(0);
  }

  // Run discussion (pass pre-fetched WKI context)
  const result = await runDiscussion(spec, wkiContext, {
    onRoundComplete: async (round: RoundResult) => {
      displayRoundResult(round);

      // #3 fix: only show implemented options, validate input
      const answer = await askUser(rl, '  > continue — 다음 라운드 / stop — 종료 / guide "지시" — 방향 추가: ');
      const lower = answer.toLowerCase();

      if (lower === 'stop' || lower === 's') {
        return { action: 'stop' as const };
      }

      if (lower.startsWith('guide ')) {
        return {
          action: 'guide' as const,
          guidance: answer.slice(6).trim(),
        };
      }

      if (lower === 'continue' || lower === 'c' || lower === '') {
        return { action: 'continue' as const };
      }

      // Unrecognized input → ask again
      console.log('  인식할 수 없는 입력입니다. continue로 진행합니다.');
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

  // #3 fix: exit 0 on user stop (not failure), exit 1 only on actual errors
  process.exit(0);
}

main().catch((err) => {
  console.error('FATAL:', err instanceof Error ? err.message : String(err));
  process.exit(1);
});
