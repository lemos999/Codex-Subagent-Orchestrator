# Launcher Contract v1 — Frozen

이 문서는 PowerShell 런처(`start-codex-subagent-team.ps1`)의 입출력 계약을 동결한 것이다.
TypeScript 런처는 이 계약을 정확히 재현해야 한다.

## 입력 계약

- **스펙 파일**: JSON, `-SpecPath`로 전달
- **필수 필드**: `cwd`, `agents` (비어있지 않은 배열)
- **타입 정의**: `src/types/spec.ts`

## 출력 계약

### 파일 구조

```
{output_dir}/
├── orchestration-manifest.json    (항상)
├── orchestration-summary.md       (write_summary_file=true 시)
├── launcher-debug.log             (debug_log_file 설정 시)
├── orchestration-usage.json       (live_usage.enabled=true 시)
├── {name}.stdout.log              (항상)
├── {name}.stderr.log              (항상)
├── {name}.prompt.txt              (write_prompt_files=true 시)
└── {name}.last.txt                (항상)
```

### 파일명 규칙

- 워커 파일: `{agent.name}.{type}.{ext}`
- Manifest: 항상 `orchestration-manifest.json`
- Summary: 항상 `orchestration-summary.md`
- 인코딩: 모든 파일 UTF-8

### Manifest 구조

- **타입 정의**: `src/types/manifest.ts`
- **모든 경로**: 절대 경로, Windows 호환
- **타임스탬프**: ISO 8601 UTC
- **해시**: SHA256 hex

### 아카이브 구조

```
{archive_root}/{YYYYMMDD}-{HHMMSS}-{label}/
├── launcher/      (spec, manifest, summary, debug log 복사)
├── deliverables/  (requested_deliverables 복사)
├── workers/       ({kind}__{name}/ 하위에 metadata, prompt, stdout, stderr, last, session)
└── supervisor/    (AGENTS.md 등 복사)
```

## 호환성 규칙

1. TS 런처가 미지원 스펙 필드를 만나면 **명시적으로 실패**한다 (조용히 무시 금지)
2. Manifest JSON의 필드명, 타입, 중첩 구조는 PS 출력과 **동일**해야 한다
3. Summary Markdown의 형식은 PS 출력과 **동일**해야 한다
4. 경로 해석은 `cwd_resolution` 모드에 따라 PS와 **동일**하게 동작해야 한다
5. 엔진별 CLI 호출 명령은 PS와 **동일**해야 한다

## 검증 방법

동일한 스펙 파일을 PS와 TS 런처에 각각 실행한 후:
1. Manifest JSON의 구조적 동치성 비교 (타임스탬프, 경로 제외)
2. 워커 파일명과 디렉터리 구조 동치성 비교
3. Summary Markdown 형식 동치성 비교
4. 종료 코드 동치성 비교

## 골든 테스트 스펙

| 스펙 | 엔진 | 모드 | 용도 |
|------|------|------|------|
| `tests/test-6d-default-engine.json` | codex 단일 | sequential | 기본 동작 |
| `tests/test-6a-mixed-engine.json` | codex+claude 혼합 | parallel | 혼합 엔진 |
| `tests/test-6c-three-way.json` | gemini+codex+claude | parallel | 3엔진 |
| `tests/gemini-evidence-test.spec.json` | gemini 단일 | sequential | Gemini 엔진 |
