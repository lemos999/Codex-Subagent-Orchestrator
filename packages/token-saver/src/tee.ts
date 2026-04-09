/**
 * Tee Store — 압축 전 원본 출력을 임시 파일로 보존
 * - Charter Baseline 4: 원본 복구 가능
 * - 최근 50개 유지, 오래된 것 자동 삭제
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';

const TEE_DIR = path.join(os.tmpdir(), 'cts-tee');
const MAX_FILES = 50;

export function saveTee(cmd: string, originalOutput: string): string {
  // tee 디렉토리 생성
  if (!fs.existsSync(TEE_DIR)) {
    fs.mkdirSync(TEE_DIR, { recursive: true });
  }

  // 파일명: timestamp-command.txt
  const timestamp = Date.now();
  const safeCmdName = cmd.split(/\s+/).slice(0, 3).join('_').replace(/[^a-zA-Z0-9_-]/g, '');
  const fileName = `${timestamp}-${safeCmdName}.txt`;
  const filePath = path.join(TEE_DIR, fileName);

  // 동기적으로 저장 (오버헤드 최소화)
  try {
    fs.writeFileSync(filePath, originalOutput);
  } catch {
    // 저장 실패해도 메인 파이프라인 중단하지 않음
  }

  // 오래된 파일 정리 (50개 초과 시)
  cleanupOldFiles();

  return filePath;
}

function cleanupOldFiles(): void {
  try {
    const files = fs.readdirSync(TEE_DIR)
      .map(f => ({ name: f, time: parseInt(f.split('-')[0]) || 0 }))
      .sort((a, b) => b.time - a.time);

    if (files.length > MAX_FILES) {
      for (const file of files.slice(MAX_FILES)) {
        fs.unlinkSync(path.join(TEE_DIR, file.name));
      }
    }
  } catch {
    // cleanup 실패해도 무시
  }
}
