/**
 * Discussion spec — separate from LauncherSpec.
 * Defines topic, participants, rounds, and output configuration.
 */

export interface DiscussionParticipant {
  engine: 'claude' | 'codex' | 'gemini';
  model?: string;
  role?: string;     // 분석 관점 (e.g., "보안 관점으로 검토")
  persona?: string;  // 캐릭터 (e.g., "30년차 내과 교수, 보수적이고 근거중심")
}

export interface DiscussionSpec {
  type: 'discussion';
  topic: string;
  max_rounds: number;
  participants: DiscussionParticipant[];
  output_dir?: string;
  response_max_lines?: number;
  wki_context_topk?: number;
  auto_persona?: boolean;  // 토픽 기반 자동 페르소나 생성 (기본: true)
}

/** 기본 페르소나 — 자동 생성 실패 시 폴백 */
export const DEFAULT_PERSONAS: Record<string, string> = {
  claude: '신중한 학자 — 근거와 논리 중심, 양면을 고려하며 정밀하게 분석',
  codex: '실용주의자 — 현실 적용 가능성과 비용 효율을 중시하는 현장 전문가',
  gemini: '혁신가 — 최신 트렌드와 대담한 시각으로 새로운 관점을 제시',
};

const DEFAULT_PARTICIPANTS: DiscussionParticipant[] = [
  { engine: 'claude', model: 'sonnet' },
  { engine: 'codex', model: 'gpt-5.4' },
  { engine: 'gemini', model: 'gemini-2.5-flash' },
];

/**
 * Parse a discussion spec from JSON or create from topic string.
 */
export function parseDiscussionSpec(input: string | Record<string, unknown>): DiscussionSpec {
  if (typeof input === 'string') {
    // Simple topic string
    const today = new Date().toISOString().slice(0, 10);
    const slug = input.toLowerCase().replace(/[^a-z0-9가-힣]+/g, '-').replace(/^-|-$/g, '').slice(0, 50);
    return {
      type: 'discussion',
      topic: input,
      max_rounds: 3,
      participants: DEFAULT_PARTICIPANTS,
      output_dir: `discussions/${slug}-${today}`,
      response_max_lines: 30,
      wki_context_topk: 5,
    };
  }

  // JSON spec
  const spec = input as Record<string, unknown>;
  if (!spec.topic || typeof spec.topic !== 'string') {
    throw new Error('Discussion spec must have a "topic" string');
  }

  const today = new Date().toISOString().slice(0, 10);
  const slug = (spec.topic as string).toLowerCase().replace(/[^a-z0-9가-힣]+/g, '-').replace(/^-|-$/g, '').slice(0, 50);

  return {
    type: 'discussion',
    topic: spec.topic as string,
    max_rounds: (spec.max_rounds as number) ?? 3,
    participants: (spec.participants as DiscussionParticipant[]) ?? DEFAULT_PARTICIPANTS,
    output_dir: (spec.output_dir as string) ?? `discussions/${slug}-${today}`,
    response_max_lines: (spec.response_max_lines as number) ?? 30,
    wki_context_topk: (spec.wki_context_topk as number) ?? 5,
  };
}
