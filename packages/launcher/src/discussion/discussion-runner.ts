/**
 * Discussion runner — orchestrates multi-round AI debates.
 *
 * Flow:
 * 1. WKI context snapshot
 * 2. Round 1: 3 AI parallel opinions
 * 3. User intervention (continue/stop/guide/modify)
 * 4. Moderator summary
 * 5. Round 2+: cross-verification with labels
 * 6. Final: consensus + issues summary
 * 7. Evidence storage
 */

import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { spawnWorker, type ResolvedWorkerSpec } from '../workers/spawn.js';
import { detectWkiConfig, generateContext } from '../supervisor/wki-context.js';
import { writeFileSafe } from '../common/fs-helpers.js';
import type { DiscussionSpec, DiscussionParticipant } from './discussion-spec.js';
import { ENGINE_DEFAULTS } from '../types/engine.js';

// ============================================================
// Types
// ============================================================

export interface RoundResult {
  round: number;
  responses: Map<string, string>; // engine → response text
  moderatorSummary?: string;
  convergence?: 'agree' | 'partial' | 'disagree';
  userGuidance?: string;
}

export interface DiscussionResult {
  topic: string;
  rounds: RoundResult[];
  conclusion: string;
  converged: boolean;
  totalRounds: number;
}

// ============================================================
// Prompt builders
// ============================================================

function buildRound1Prompt(
  topic: string,
  wkiContext: string,
  maxLines: number,
): string {
  return `## Discussion Topic
${topic}

${wkiContext ? `## Context (WKI snapshot)\n${wkiContext}\n` : ''}
## Instructions
Provide your analysis. Structure your response:
1. **Position**: your main argument
2. **Reasoning**: supporting evidence
3. **Concerns**: potential risks or downsides
4. **Recommendation**: your suggested approach

End with: [POSITION: one-line summary of your stance]
Keep response under ${maxLines} lines.`;
}

function buildRound2Prompt(
  topic: string,
  moderatorSummary: string,
  maxLines: number,
  userGuidance?: string,
): string {
  const guidanceSection = userGuidance
    ? `\n## User Guidance\n${userGuidance}\n`
    : '';

  return `## Discussion Topic
${topic}

## Previous Round Summary (by Moderator)
${moderatorSummary}
${guidanceSection}
## Instructions
Review the other participants' arguments. Respond with:
1. **[AGREE/PARTIAL/DISAGREE]**: your verdict on the overall direction
2. **Reasoning**: why you agree or disagree
3. **New insight**: anything missed by others
4. **Updated position**: has your view changed?

End with: [POSITION: one-line summary of your updated stance]
Keep response under ${maxLines} lines.`;
}

function buildModeratorSummaryPrompt(
  topic: string,
  responses: Map<string, string>,
): string {
  let participantSection = '';
  for (const [engine, response] of responses) {
    participantSection += `### ${engine} said:\n${response}\n\n`;
  }

  return `## Round Summary Task

**Topic**: ${topic}

${participantSection}
## Instructions
Summarize each participant's position in 3 lines max each.
Identify: areas of agreement, areas of disagreement, open questions.
Do NOT inject your own opinion. Be neutral.`;
}

function buildConclusionPrompt(
  topic: string,
  rounds: RoundResult[],
): string {
  let roundSummaries = '';
  for (const round of rounds) {
    roundSummaries += `### Round ${round.round}\n`;
    if (round.moderatorSummary) {
      roundSummaries += `${round.moderatorSummary}\n\n`;
    } else {
      for (const [engine, response] of round.responses) {
        const firstLines = response.split('\n').slice(0, 5).join('\n');
        roundSummaries += `**${engine}**: ${firstLines}\n\n`;
      }
    }
  }

  return `## Final Conclusion Task

**Topic**: ${topic}

${roundSummaries}
## Instructions
Write the final conclusion:
1. **Consensus**: points all participants agreed on
2. **Disputed**: points where disagreement remains
3. **Recommendation**: the best course of action based on the discussion
4. **Open questions**: unresolved items for future consideration

Be comprehensive but concise.`;
}

// ============================================================
// Convergence detection
// ============================================================

function detectConvergence(responses: Map<string, string>): 'agree' | 'partial' | 'disagree' {
  let agreeCount = 0;
  let disagreeCount = 0;

  for (const response of responses.values()) {
    const upper = response.toUpperCase();
    if (upper.includes('[AGREE]')) agreeCount++;
    else if (upper.includes('[DISAGREE]')) disagreeCount++;
  }

  if (agreeCount === responses.size) return 'agree';
  if (disagreeCount > 0) return 'disagree';
  return 'partial';
}

// ============================================================
// Worker spawning
// ============================================================

function buildWorkerSpec(
  participant: DiscussionParticipant,
  prompt: string,
  outputDir: string,
  round: number,
): ResolvedWorkerSpec {
  const name = `${participant.engine}-round${round}`;
  const model = participant.model ?? ENGINE_DEFAULTS[participant.engine] ?? 'sonnet';

  return {
    name,
    engine: participant.engine,
    model,
    prompt,
    taskText: prompt,
    cwd: process.cwd(),
    outputDir: path.resolve(outputDir, `round-${round}`),
    sandbox: 'read-only',
    kind: 'reviewer',
    stage: 1,
    isReadOnly: true,
    reasoningEffort: null,
    promptProfile: 'compact',
    responseStyle: 'compact',
    maxResponseLines: 30,
    json: false,
    outputSchema: null,
    writePromptFile: true,
    requiredPaths: [],
    requiredNonEmptyPaths: [],
    extraArgs: [],
    timeoutMs: 300000,
  };
}

async function spawnParticipant(
  participant: DiscussionParticipant,
  prompt: string,
  outputDir: string,
  round: number,
): Promise<{ engine: string; response: string; success: boolean }> {
  const spec = buildWorkerSpec(participant, prompt, outputDir, round);

  try {
    await fs.mkdir(spec.outputDir, { recursive: true });
    const output = await spawnWorker(spec);

    // Save response as markdown
    const responsePath = path.resolve(spec.outputDir, `${participant.engine}.md`);
    await writeFileSafe(responsePath, output.lastMessage || '');

    return {
      engine: participant.engine,
      response: output.lastMessage || '[NO RESPONSE]',
      success: output.exitCode === 0,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return {
      engine: participant.engine,
      response: `[UNAVAILABLE: ${msg}]`,
      success: false,
    };
  }
}

// ============================================================
// Main discussion runner
// ============================================================

export async function runDiscussion(
  spec: DiscussionSpec,
  callbacks: {
    onRoundComplete: (round: RoundResult) => Promise<{
      action: 'continue' | 'stop' | 'guide' | 'modify';
      guidance?: string;
    }>;
    onStatus: (message: string) => void;
  },
): Promise<DiscussionResult> {
  const outputDir = path.resolve(spec.output_dir ?? 'subagent-runs/discuss/discussion');
  await fs.mkdir(outputDir, { recursive: true });

  // 1. WKI context snapshot
  callbacks.onStatus('WKI 맥락 검색 중...');
  let wkiContext = '';
  const wkiConfig = detectWkiConfig(process.cwd());
  if (wkiConfig) {
    try {
      const ctx = await generateContext(spec.topic, wkiConfig);
      if (ctx.injected) {
        wkiContext = ctx.markdown;
        // Save snapshot for reproducibility
        await writeFileSafe(path.join(outputDir, 'wki-context-snapshot.md'), wkiContext);
      }
    } catch { /* WKI failure is non-fatal */ }
  }

  const rounds: RoundResult[] = [];
  let userGuidance: string | undefined;
  let stopped = false;

  for (let roundNum = 1; roundNum <= spec.max_rounds; roundNum++) {
    callbacks.onStatus(`Round ${roundNum}/${spec.max_rounds} 실행 중...`);

    // 2. Build prompts
    const isFirstRound = roundNum === 1;
    const previousSummary = rounds.length > 0
      ? rounds[rounds.length - 1].moderatorSummary ?? ''
      : '';

    // 3. Spawn all participants in parallel
    const promises = spec.participants.map((p) => {
      const prompt = isFirstRound
        ? buildRound1Prompt(spec.topic, wkiContext, spec.response_max_lines ?? 30)
        : buildRound2Prompt(spec.topic, previousSummary, spec.response_max_lines ?? 30, userGuidance);
      return spawnParticipant(p, prompt, outputDir, roundNum);
    });

    const results = await Promise.allSettled(promises);
    const responses = new Map<string, string>();

    for (const result of results) {
      if (result.status === 'fulfilled') {
        responses.set(result.value.engine, result.value.response);
      }
    }

    // 4. Moderator summary (Claude as neutral judge)
    callbacks.onStatus(`Round ${roundNum} Moderator 요약 중...`);
    const moderatorPrompt = buildModeratorSummaryPrompt(spec.topic, responses);
    const moderatorResult = await spawnParticipant(
      { engine: 'claude', model: 'haiku' },
      moderatorPrompt,
      outputDir,
      roundNum,
    );

    const moderatorSummary = moderatorResult.response;
    await writeFileSafe(
      path.resolve(outputDir, `round-${roundNum}`, 'moderator-summary.md'),
      moderatorSummary,
    );

    // 5. Detect convergence (Round 2+)
    const convergence = isFirstRound ? undefined : detectConvergence(responses);

    const roundResult: RoundResult = {
      round: roundNum,
      responses,
      moderatorSummary,
      convergence,
      userGuidance,
    };
    rounds.push(roundResult);

    // 6. User intervention
    if (convergence === 'agree') {
      callbacks.onStatus('모든 참가자가 합의했습니다.');
      break;
    }

    if (roundNum < spec.max_rounds) {
      const decision = await callbacks.onRoundComplete(roundResult);

      if (decision.action === 'stop') {
        stopped = true;
        break;
      }

      if (decision.action === 'guide') {
        userGuidance = decision.guidance;
      } else {
        userGuidance = undefined;
      }
    }
  }

  // 7. Generate conclusion
  callbacks.onStatus('합의안 작성 중...');
  const conclusionPrompt = buildConclusionPrompt(spec.topic, rounds);
  const conclusionResult = await spawnParticipant(
    { engine: 'claude', model: 'sonnet' },
    conclusionPrompt,
    outputDir,
    0, // special round 0 for conclusion
  );

  const conclusion = conclusionResult.response;
  await writeFileSafe(path.join(outputDir, 'conclusion.md'), conclusion);

  // 8. Write manifest
  const converged = rounds.some((r) => r.convergence === 'agree');
  const manifest = buildManifest(spec, rounds, converged, stopped);
  await writeFileSafe(path.join(outputDir, 'discussion-manifest.md'), manifest);

  // 9. Write summary
  const summary = buildSummary(spec, rounds, conclusion, converged);
  await writeFileSafe(path.join(outputDir, 'discussion-summary.md'), summary);

  return {
    topic: spec.topic,
    rounds,
    conclusion,
    converged,
    totalRounds: rounds.length,
  };
}

// ============================================================
// Evidence builders
// ============================================================

function buildManifest(
  spec: DiscussionSpec,
  rounds: RoundResult[],
  converged: boolean,
  stopped: boolean,
): string {
  const lines = [
    `# Discussion Manifest`,
    ``,
    `- **Topic**: ${spec.topic}`,
    `- **Participants**: ${spec.participants.map((p) => `${p.engine} (${p.model ?? 'default'})`).join(', ')}`,
    `- **Max rounds**: ${spec.max_rounds}`,
    `- **Actual rounds**: ${rounds.length}`,
    `- **Converged**: ${converged ? 'yes' : 'no'}`,
    `- **Stopped by user**: ${stopped ? 'yes' : 'no'}`,
    `- **Timestamp**: ${new Date().toISOString()}`,
    ``,
  ];

  for (const round of rounds) {
    lines.push(`## Round ${round.round}`);
    if (round.convergence) {
      lines.push(`- Convergence: ${round.convergence}`);
    }
    if (round.userGuidance) {
      lines.push(`- User guidance: ${round.userGuidance}`);
    }
    for (const [engine] of round.responses) {
      lines.push(`- ${engine}: responded`);
    }
    lines.push('');
  }

  return lines.join('\n');
}

function buildSummary(
  spec: DiscussionSpec,
  rounds: RoundResult[],
  conclusion: string,
  converged: boolean,
): string {
  return [
    `# Discussion Summary`,
    ``,
    `**Topic**: ${spec.topic}`,
    `**Rounds**: ${rounds.length}/${spec.max_rounds}`,
    `**Converged**: ${converged ? 'yes' : 'no'}`,
    ``,
    `## Conclusion`,
    ``,
    conclusion,
  ].join('\n');
}
