# 문제-해결 기록

---

## #1. local-provider.ts 스텁 미구현

- **발생일**: 2026-03-16
- **상황**: `wki.config.json`에서 `provider: "local"`로 설정해도 임베딩이 생성되지 않음
- **원인**: `local-provider.ts`가 `throw Error`만 있는 빈 스텁이었음. 실제 ONNX 모델 로딩/추론 코드가 없었음
- **해결**: `@huggingface/transformers` 패키지 설치 후 `feature-extraction` 파이프라인 + mean pooling + normalize 구현. 모델: `Xenova/bge-small-en-v1.5` (384d, ~33MB)
- **수정 파일**: `workspace-knowledge-index/src/embedding/local-provider.ts`

---

## #2. wki.config.json 위치 불일치

- **발생일**: 2026-03-16
- **상황**: config를 `local`로 변경해도 CLI가 여전히 `openai` provider를 사용
- **원인**: `wki.config.json`이 `workspace-knowledge-index/` 하위에만 존재. CLI는 `process.cwd()`(프로젝트 루트)에서 `loadConfig('.')`로 config를 탐색하므로, 루트에 파일이 없으면 `DEFAULT_CONFIG(provider: "openai")`로 폴백
- **해결**: `wki.config.json`을 프로젝트 루트에 복사
- **수정 파일**: `wki.config.json` (프로젝트 루트에 추가)

---

## #3. 임베딩 provider 에러 메시지 불명확

- **발생일**: 2026-03-16
- **상황**: 임베딩 provider 초기화 실패 시 항상 "No embedding API key found"만 출력되어 실제 원인 파악 불가
- **원인**: `catch { }` 블록에서 에러 객체를 무시하고 고정 메시지만 출력
- **해결**: `catch (err)`로 변경하여 provider 이름과 실제 에러 메시지를 출력하도록 수정
- **수정 파일**: `workspace-knowledge-index/src/index.ts` (cmdIndex, cmdSearch 내 catch 블록 2곳)

---

## #4. Gemini 런처 실행 실패 — npx가 Windows Start-Process에서 동작하지 않음

- **발생일**: 2026-03-17
- **상황**: `start-codex-subagent-team.ps1`로 Gemini 엔진 에이전트 실행 시 `exit_code: -1`, `%1 is not a valid Win32 application` 에러
- **원인**: `GeminiExecutable` 기본값이 `"npx"`인데, Windows에서 `npx`는 `npx.cmd` 배치 래퍼. `Start-Process`의 `FilePath`에 `.cmd` 확장자 없이 전달하면 Win32 바이너리로 인식하지 못함
- **해결**: `GeminiExecutable` 기본값을 `"npx.cmd"`로 변경
- **수정 파일**: `skills/codex-subagent-orchestrator/scripts/start-codex-subagent-team.ps1` (파라미터 기본값)

---

## #5. Codex CLI `--reasoning` 플래그 미지원

- **발생일**: 2026-03-17
- **상황**: `/submix`에서 Codex 워커를 `gpt-5.4 --reasoning xhigh`로 실행 시 `unexpected argument '--reasoning'` 에러
- **원인**: `codex exec` CLI가 `--reasoning` 플래그를 지원하지 않음. reasoning effort는 런처의 PowerShell 스크립트 내부에서 처리되는 별도 파라미터이며, `codex exec` 직접 호출 시에는 사용 불가
- **해결**: `--reasoning` 플래그 없이 `codex exec --full-auto -m gpt-5.4`로 재실행. 향후 `/submix`에서 Codex 직접 호출 시 reasoning 파라미터 처리 방법을 명확히 문서화 필요
- **수정 파일**: 없음 (런타임 대응)
