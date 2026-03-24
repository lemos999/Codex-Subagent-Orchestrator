# Subagent Orchestrator — Claude Instructions

## Project Status

세션 시작 시 반드시 `project-status/current.md`를 읽는다. 프로젝트 현황, 핵심 구성 요소, 다음 작업, 주요 명령어, 운영 규칙이 정리되어 있다.

작업 완료 후 프로젝트 상태가 변경되면 `project-status/current.md`를 갱신한다.

## WKI (Workspace Knowledge Index)

- `/sub`, `/submix` 실행 시 TS 런처가 자동으로 증분 인덱싱 + 맥락 주입을 수행한다.
- 그 외 경로(`/design`, `/gdd`, `/discuss`, 일반 대화)에서는 필요 시 직접 검색: `node workspace-knowledge-index/dist/index.js search "<query>" --top 5`

## Rules

- 파일 삭제 시 반드시 사용자에게 확인 후 진행
- Evidence 기록은 필수 — 결과 보고 전에 반드시 기록
- 문제 발생 시 `problem-resolution-log.md`를 먼저 확인
