# Project Status — Current

> 이 파일은 모든 AI 엔진(Claude, Codex/GPT, Gemini)이 참조합니다.
> 이 폴더에서 작업하는 AI는 이 파일을 읽고 현재 상태를 파악하세요.
> 완료된 작업은 분기별 아카이브로 이동합니다.

## Project: Subagent Orchestrator

멀티 AI 엔진(Claude, Codex/GPT, Gemini)을 조율하는 오케스트레이션 시스템.

## 핵심 구성 요소

| 구성 요소 | 상태 | 경로 |
|---|---|---|
| TS 런처 (primary) | 완료 | `packages/launcher/` |
| PS 런처 (legacy fallback) | 유지 | `skills/codex-subagent-orchestrator/scripts/` |
| WKI (Workspace Knowledge Index) | 완료 | `workspace-knowledge-index/` |
| Claude 오케스트레이터 (/sub) | 완료 | `skills/claude-subagent-orchestrator/` |
| 멀티엔진 오케스트레이터 (/submix) | 완료 | `.claude/skills/submix/` |
| Gemini 오케스트레이터 | 완료 | `skills/gemini-subagent-orchestrator/` |
| Codex 오케스트레이터 | 완료 | `skills/codex-subagent-orchestrator/` |
| **토론 시스템 (/discuss)** | **Phase 1~3 완료** | `packages/launcher/src/discussion/` |
| **큐 러너 TS** | **Phase 1~2 완료** | `packages/launcher/src/queue/` |

## 다음 작업 (우선순위 순)

1. **WKI 도메인 특화 임베딩** — 현재 범용 모델의 한계 (evidence/workflow 쿼리 약함, Mean nDCG 0.686)

## 최근 완료 (2026-03-17~22)

- TS 런처 Phase 0~4 (PS 런처 대체)
- WKI 로컬 임베딩 (paraphrase-multilingual-MiniLM-L12-v2)
- WKI 맥락 자동 주입 (모든 엔진 동일 적용)
- WKI 한글 Query Expansion
- WKI Eval 시스템 (Mean nDCG 0.686, Median 0.714 — 평가기 dedupe 수정 후 정상화)
- WKI 자동 증분 인덱싱
- WKI 토론 이력 인덱싱 (노이즈 파일 제외)
- Evidence 기록 강화
- 골든 테스트 4/4 PASS
- 토론 시스템 Phase 1~3 완료:
  - 3자 토론 (Claude + Codex/GPT + Gemini) 교차 검증
  - 실시간 상태 표시 (엔진별 응답 시간)
  - 페르소나 시스템 (토픽 기반 자동 생성 + 수동 지정 + 기본 프리셋)
  - 역할(role) 커스터마이징
  - 실전 테스트 3회 완료
- 큐 러너 TS 전환 Phase 1 완료:
  - PS 큐 러너(1,700줄) → TS(1,514줄, 10개 모듈)
  - local-json, local-files, mock-json(별칭) 트래커
  - PS 설정 호환 계층 (queue-compat)
  - 핑거프린트/blocked_by/백오프 PS 동작 일치
  - TS CLI --json 모드 추가
  - /submix 검증(3엔진) + GPT 5.4 watchdog 리뷰 2회
  - PS 호환성 수정 4건 (priority, blocked_by, isEligibleNow, hooks)
  - 골든 테스트 36/36 PASS
  - Phase 2: Linear GraphQL 트래커 (/submix 검증 완료)
- WKI 검색 개선 추가:
  - Negative sampling (노이즈 경로 패널티)
  - Multi-vector search (fail-soft)
  - Re-ranking 강화 (heading/filePath + stop word 필터링)
  - 평가기 dedupe 수정 (nDCG > 1 방지)

## 주요 명령어

```bash
# TS 런처 실행
node packages/launcher/dist/cli.js --spec <spec.json>

# WKI 인덱싱
node workspace-knowledge-index/dist/index.js index

# WKI 검색
node workspace-knowledge-index/dist/index.js search "<query>" --top 5

# WKI 상태 확인
node workspace-knowledge-index/dist/index.js status

# WKI 검색 품질 평가
node workspace-knowledge-index/dist/index.js eval workspace-knowledge-index/eval/gold-set-v2.json

# 큐 러너 실행
node packages/launcher/dist/queue/queue-cli.js --config <queue.json>
node packages/launcher/dist/queue/queue-cli.js --config <queue.json> --max-polls 10

# 토론 실행
node packages/launcher/dist/discussion/discuss-cli.js "주제"
node packages/launcher/dist/discussion/discuss-cli.js --auto "주제"

# WKI lock 문제 시
rm .knowledge/.wki.lock
```

## 문제 해결

문제 발생 시 `problem-resolution-log.md`를 먼저 확인하세요. 8건의 해결 사례가 기록되어 있습니다.

## 규칙

- **세션 시작 시 WKI 인덱싱 필수** — 첫 작업 전에 `node workspace-knowledge-index/dist/index.js index` 를 1회 실행. 다른 AI/세션의 변경사항이 반영됨. 변경 없으면 즉시 반환 (0초).
- 파일 삭제 시 반드시 사용자에게 확인 후 진행
- 이 폴더에는 별도 프로젝트 폴더가 존재할 수 있음 (game-design-director, trading-quest 등)
- Evidence 기록은 필수 — 결과 보고 전에 반드시 기록
