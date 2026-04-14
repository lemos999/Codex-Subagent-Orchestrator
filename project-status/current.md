# Project Status — Current

> 이 파일은 모든 AI 엔진(Claude, Codex/GPT, Gemini)이 참조합니다.
> 이 폴더에서 작업하는 AI는 이 파일을 읽고 현재 상태를 파악하세요.
> 완료 기록은 project-status/2026-Q2.md에 직접 추가한다.
> current.md에는 완료 이력을 기록하지 않는다.
> → 완료 이력: project-status/2026-Q2.md

---

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
| **범용 설계 디렉터 (/design)** | **완료** | `skills/design-director/` + `.claude/skills/design/` |
| **게임 기획 디렉터 (/gdd)** | **완료** | `skills/game-design-director/` + `.claude/skills/gdd/` |
| **Intelligent Delegation 프레임워크** | **완료** | `packages/launcher/src/` + `config/capabilities/` + 기획서 `Projects/intelligent-delegation/` |

## 다음 작업 (우선순위 순)

1. **페르소나 국가 — 구현 단계 진입** (설계 전부 완료)
   - Phase C: constants-charter 신설, 극한 SLA 정의, PersonaBrain 학습 발산 복구
   - 구현 순서: Physis → 틱 데몬 → 사회 시스템 → PersonaBrain SNN → 자율 생활
2. **WKI 추가 개선** — Mean nDCG 0.819, Line-scoped 0.655 (Min 0.630)
3. **/design domains/software/ 실전 사용**

## 페르소나 국가 설계 현황 (2026-04-12 완료)

| Charter | 버전 | 상태 |
|---------|------|:----:|
| world-ontology | Phase A 수정 완료 | ✅ |
| constitution | 8장 27조 | ✅ |
| economy-whitepaper | 11장 | ✅ |
| physis-charter-v2 | v2.4 | ✅ |
| tick-daemon-charter | v1.1 | ✅ |
| humanity-charter | H1~H6 | ✅ |
| death-reincarnation-charter | v1 | ✅ |
| order-charter | v1 | ✅ |
| society-charter-draft | v1.1 | ✅ |
| secret-rumor-evidence-charter | v1.1 | ✅ |
| **personabrain-snn-charter** | **v3.1** | ✅ |

PersonaBrain SNN: 50M 뉴런, 12클러��터(V-L-S-B-A-T-C-G-F-I-D-P), 기억 5유형+망각 경제학, 20K명 CPU 10ms

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
---

## Mostria (vibe-web) 완료 이력

→ `project-status/2026-Q2.md` 참조. `git log --oneline Projects/vibe-web/` 로도 확인 가능.
