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
  --auto          Auto mode: skip approval, run all rounds without user input
  --help          Show this help
`);
    process.exit(0);
  }

  // Check for --auto flag
  const autoMode = args.includes('--auto');
  const filteredArgs = args.filter((a) => a !== '--auto');

  // Parse spec
  let spec;
  if (filteredArgs[0] === '--spec' && filteredArgs[1]) {
    const specPath = path.resolve(filteredArgs[1]);
    const raw = JSON.parse(await fs.readFile(specPath, 'utf8'));
    spec = parseDiscussionSpec(raw);
  } else {
    spec = parseDiscussionSpec(filteredArgs.join(' '));
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

  const rl = autoMode ? null : createReadline();

  if (!autoMode) {
    const approval = await askUser(rl!, '  > yes — 토론 시작 / no — 취소: ');
    if (approval.toLowerCase() !== 'yes' && approval.toLowerCase() !== 'y') {
      console.log('  취소되었습니다.');
      rl!.close();
      process.exit(0);
    }
  } else {
    console.log('  [auto] 자동 모드 — 승인 스킵, 전체 라운드 실행');
  }

  // Run discussion (pass pre-fetched WKI context)
  const result = await runDiscussion(spec, wkiContext, {
    onRoundComplete: async (round: RoundResult) => {
      displayRoundResult(round);

      if (autoMode) {
        console.log('  [auto] 자동으로 다음 라운드 진행');
        return { action: 'continue' as const };
      }

      const answer = await askUser(rl!, '  > continue — 다음 라운드 / stop — 종료 / guide "지시" — 방향 추가: ');
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

      console.log('  인식할 수 없는 입력입니다. continue로 진행합니다.');
      return { action: 'continue' as const };
    },
    onStatus: (message: string) => {
      console.log(`  [discuss] ${message}`);
    },
  });

  if (rl) rl.close();

  // Display final result
  const personaDisplay = [...result.personas.entries()]
    .map(([engine, persona]) => `    ${engine}: ${persona}`)
    .join('\n');

  console.log(`
${'='.repeat(60)}
  토론 완료
${'='.repeat(60)}

  Topic:      ${result.topic}
  Rounds:     ${result.totalRounds}
  Converged:  ${result.converged ? '합의 도출' : '쟁점 남음'}
  Personas:
${personaDisplay}
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
