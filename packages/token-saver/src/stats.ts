/**
 * Stats Tracker — 세션별/명령별 토큰 절감 기록
 * - SQLite는 v2에서 검토. v1은 JSON 파일.
 * - 파일: ~/.cts/stats.json
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';

const STATS_DIR = path.join(os.homedir(), '.cts');
const STATS_FILE = path.join(STATS_DIR, 'stats.json');

interface CommandStats {
  command: string;      // 첫 토큰 (git, vitest 등)
  originalBytes: number;
  compressedBytes: number;
  savedBytes: number;
  timestamp: string;     // ISO 8601
}

interface StatsData {
  version: 1;
  totalSaved: number;
  totalCalls: number;
  history: CommandStats[];  // 최근 200개
}

function loadStats(): StatsData {
  try {
    if (fs.existsSync(STATS_FILE)) {
      return JSON.parse(fs.readFileSync(STATS_FILE, 'utf-8'));
    }
  } catch { /* corrupted file */ }
  return { version: 1, totalSaved: 0, totalCalls: 0, history: [] };
}

function saveStats(data: StatsData): void {
  try {
    if (!fs.existsSync(STATS_DIR)) {
      fs.mkdirSync(STATS_DIR, { recursive: true });
    }
    // 최근 200개만 유지
    if (data.history.length > 200) {
      data.history = data.history.slice(-200);
    }
    fs.writeFileSync(STATS_FILE, JSON.stringify(data, null, 2));
  } catch { /* 저장 실패해도 무시 */ }
}

export function recordStat(cmd: string, originalBytes: number, compressedBytes: number): void {
  const data = loadStats();
  const saved = originalBytes - compressedBytes;

  data.totalSaved += Math.max(0, saved);
  data.totalCalls++;
  data.history.push({
    command: cmd.split(/\s+/)[0] ?? cmd,
    originalBytes,
    compressedBytes,
    savedBytes: saved,
    timestamp: new Date().toISOString(),
  });

  saveStats(data);
}

export function printStats(): void {
  const data = loadStats();

  console.log(`CTS Token Savings Statistics`);
  console.log(`============================`);
  console.log(`Total calls:  ${data.totalCalls}`);
  console.log(`Total saved:  ${formatBytes(data.totalSaved)} (~${Math.round(data.totalSaved / 4)} tokens)`);
  console.log();

  // 명령별 집계
  const byCmd = new Map<string, { calls: number; saved: number }>();
  for (const h of data.history) {
    const entry = byCmd.get(h.command) ?? { calls: 0, saved: 0 };
    entry.calls++;
    entry.saved += h.savedBytes;
    byCmd.set(h.command, entry);
  }

  console.log(`By command:`);
  for (const [cmd, stats] of [...byCmd.entries()].sort((a, b) => b[1].saved - a[1].saved)) {
    console.log(`  ${cmd.padEnd(15)} ${stats.calls} calls, ${formatBytes(stats.saved)} saved`);
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}
