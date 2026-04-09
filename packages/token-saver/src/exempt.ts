// Exempt List: 압축하지 않는 명령
// DC-5 참조, Baseline 3번(검증 명령 면제)

/**
 * Commands that should NEVER be compressed.
 * These are matched against the full command string.
 */
const EXEMPT_PATTERNS: Array<string | RegExp> = [
  // Type checking / linting (CLAUDE.md Rule 4: Forced Verification)
  'tsc',
  'eslint',

  // WKI commands (우리 인프라)
  'workspace-knowledge-index',
  'wki',

  // External engine calls (Codex, Gemini)
  'codex exec',
  'codex-cli',
  'gemini-cli',
  '@google/gemini-cli',

  // Package managers (설치 로그는 중요)
  'npm install',
  'npm ci',
  'pnpm install',
  'yarn install',

  // Launcher & package scripts (내부 인프라)
  'packages/launcher',
  'node packages/',
];

/**
 * Check if a command should be exempt from compression.
 * @param cmd Full command string
 * @returns true if the command should pass through uncompressed
 */
export function isExempt(cmd: string): boolean {
  const normalized = cmd.trim().toLowerCase();

  for (const pattern of EXEMPT_PATTERNS) {
    if (typeof pattern === 'string') {
      if (normalized.includes(pattern.toLowerCase())) return true;
    } else {
      if (pattern.test(normalized)) return true;
    }
  }

  return false;
}
