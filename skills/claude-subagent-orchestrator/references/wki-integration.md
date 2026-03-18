# WKI Integration Guide

## 목적

워커에게 작업을 위임하기 전에 WKI(Workspace Knowledge Index)에서 관련 맥락을 검색하여 워커 프롬프트에 주입한다. 이를 통해 워커가 올바른 맥락으로 작업을 시작할 수 있다.

## 사용 조건

- `.knowledge/` 디렉터리가 워크스페이스 루트에 존재
- WKI가 인덱싱된 상태 (최소 1회 `wki index` 실행)

## TS 런처 사용 시 (자동)

TS 런처(`packages/launcher/dist/cli.js`)를 통해 워커를 실행하면 **자동으로**:
1. 증분 인덱싱 실행 (변경 없으면 스킵)
2. 워커 태스크로 WKI 검색
3. 관련 맥락을 `## Relevant Context (auto-injected)` 블록으로 프롬프트에 주입

모든 엔진(Claude, Codex, Gemini)에 동일하게 적용된다.

## Claude 네이티브 /sub 사용 시 (수동)

Claude Task tool로 직접 워커를 실행할 때는 WKI가 자동 연동되지 않는다. 대신 오케스트레이터가 직접 맥락을 검색하여 워커 계약에 포함해야 한다.

### 방법

워커 계약을 작성하기 전에:

```bash
node workspace-knowledge-index/dist/index.js search "<워커 태스크 요약>" --top 5 --output json
```

검색 결과를 워커 계약의 **Inspect first** 또는 **Context** 섹션에 포함:

```markdown
## Context (WKI auto-search results)

- `skills/claude-subagent-orchestrator/references/orchestration-workflow.md` (lines 228-261): Stage 9 evidence recording
- `.claude/agents/codex-subagent-orchestrator.md` (lines 47-62): MANDATORY Evidence Checkpoint

## Contract

**Task**: ...
```

## Codex/Gemini 네이티브 /sub 사용 시

PS 런처(`start-codex-subagent-team.ps1`)를 사용하는 경우, WKI 연동은 아직 자동화되지 않았다. TS 런처로 전환하면 자동 연동된다.

임시 방법: 스펙 생성 전에 CLI로 맥락을 검색하여 워커 `task` 필드에 포함한다.
