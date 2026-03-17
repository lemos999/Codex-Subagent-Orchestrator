---
name: submix
description: 3개 AI 엔진(Claude + Codex/GPT + Gemini)을 혼합 활용하는 멀티엔진 서브에이전트 오케스트레이션. 각 AI 모델의 특성에 맞춰 자동 분담.
---

# /submix

3개 AI 엔진을 **자동 분담**하여 멀티엔진 서브에이전트 실행.

## `/sub` vs `/submix` 차이

| 항목 | `/sub` | `/submix` |
|------|--------|-----------|
| 엔진 | Claude 단독 (기본) | Claude + Codex(GPT) + Gemini 혼합 |
| 엔진 선택 | 사용자 지정 또는 기본 Claude | **Orchestrator가 자동 분담** |
| 엔진 지정 | 사용자가 명시적으로 지정해야 함 | Orchestrator가 자동 분담 (사용자 수동 지정도 가능) |
| 증거 저장 | `subagent-runs/claude/` | `subagent-runs/mixed/` |

## Entry Protocol

1. Strip the `/submix` prefix
2. Orchestrator(Claude)가 요청을 분석
3. 각 AI 모델의 **특성에 맞춰 에이전트 역할 자동 배정**
4. 실행 계획을 사용자에게 제시하고 **승인 대기** (yes / no / modify)
5. 승인 후 실행 — Claude orchestrator가 감독

## 엔진별 특성 및 역할 적합도

### Claude (Task tool 네이티브)

| 강점 | 적합 역할 |
|------|----------|
| 도구 접근 (파일 읽기/쓰기/검색) | implementer, fixer |
| 긴 컨텍스트 이해 | 복잡한 코드 리뷰, 아키텍처 설계 |
| 한글 품질 | 한글 문서 작성, 약관/기획서 |
| 정밀한 지시 따르기 | watchdog, 정밀 검증 |

**모델**: haiku (경량) / sonnet (기본) / opus (고급)

### Codex — GPT (Bash → `codex exec`)

| 강점 | 적합 역할 |
|------|----------|
| 코드 생성 속도 | 보일러플레이트 코드 대량 생성 |
| 멀티 파일 코드 작성 | 프로젝트 스캐폴딩, 테스트 코드 |
| 디버깅/리팩토링 | 코드 수정, 버그 수정 |
| 폭넓은 라이브러리 지식 | 외부 라이브러리 통합 |

**모델**: gpt-5.4 (기본) / o3 (추론) / o4-mini (경량)
**실행**: `codex exec --full-auto "<prompt>"`
**제약**: Claude Code 도구 접근 불가 (CLI stdout만 반환)

### Gemini (Bash → `npx @google/gemini-cli`)

| 강점 | 적합 역할 |
|------|----------|
| 긴 컨텍스트 윈도우 (1M+) | 대규모 문서 분석, 전체 코드베이스 리뷰 |
| 멀티모달 (이미지/비디오) | UI 스크린샷 분석, 디자인 검토 |
| Google 생태계 지식 | Google API, Firebase, GCP 관련 작업 |
| 빠른 응답 (Flash) | 대량 병렬 경량 작업 |

**모델**: gemini-2.5-pro (기본) / gemini-2.5-flash (경량)
**실행**: `echo "<prompt>" | npx @google/gemini-cli --yolo`
**제약**: Claude Code 도구 접근 불가 (CLI stdout만 반환)

## 자동 분담 규칙

Orchestrator(Claude)가 요청을 분석한 후 다음 매트릭스에 따라 배정:

| 작업 유형 | 1순위 엔진 | 2순위 엔진 | 사유 |
|----------|-----------|-----------|------|
| 파일 수정/생성 (implementer) | Claude | - | 도구 접근 필수 |
| 파일 수정 (fixer) | Claude | - | 도구 접근 필수 |
| 코드 리뷰/분석 | Gemini | Claude | Gemini의 긴 컨텍스트 활용 |
| 문서 분석/검증 | Gemini | Claude | 대규모 문서 처리 |
| 한글 문서 작성 | Claude | - | 한글 품질 |
| 코드 생성 (읽기 전용 산출물) | Codex | Claude | GPT 코드 생성 강점 |
| 테스트 코드 생성 | Codex | Claude | 패턴 기반 대량 생성 |
| 아키텍처/설계 | Claude (opus) | Gemini (pro) | 정밀 추론 |
| 경량 검증/watchdog | Claude (haiku) | Gemini (flash) | 비용 효율 |
| 웹 리서치 | Claude | - | WebSearch 도구 접근 |
| Google API 관련 | Gemini | Claude | 생태계 지식 |

### 핵심 제약

- **파일 수정이 필요한 역할(implementer, fixer)은 반드시 Claude** — Codex/Gemini는 CLI stdout만 반환하므로 직접 파일 수정 불가
- **Codex/Gemini 워커의 산출물은 stdout 텍스트** — Claude orchestrator가 이를 받아서 필요 시 파일에 반영
- **Orchestrator는 항상 Claude** — 다른 엔진에 위임 불가

## 실행 계획 표시 형식

```markdown
## /submix Execution Plan

**Request**: [요청 요약]
**Pattern**: [패턴명]

| # | Agent | Role | Engine | Model | Reasoning | Goal |
|---|-------|------|--------|-------|-----------|------|
| 1 | code-writer | implementer | claude | opus | 파일 수정 필요 → 도구 접근 필수 | [목표] |
| 2 | code-reviewer | reviewer | gemini | gemini-2.5-pro | 긴 컨텍스트 활용 리뷰 | [목표] |
| 3 | test-generator | reviewer | codex | gpt-5.4 | 패턴 기반 대량 코드 생성 | [목표] |

**엔진 분담 근거**: [왜 이 엔진을 이 역할에 배정했는지]
**Estimated cost**: [low / medium / high]

> **yes** — 계획대로 진행
> **no** — 취소
> **modify** — 변경 사항 지시
```

## Invariants

- Orchestrator(Claude)가 항상 감독 — 직접 산출물 편집 안 함
- 영구 산출물은 반드시 read-only review 거침
- Material issues → bounded fixer(Claude) → re-review
- **Evidence는 필수이며 생략 불가** — 사용자 보고 전에 반드시 `subagent-runs/mixed/<run-name>/`에 기록
- 외부 엔진(Codex, Gemini) 워커는 Bash tool로 호출
- 외부 엔진 프롬프트에 시크릿/자격 증명을 포함하지 않는다
- 실행 전 반드시 사용자 승인 대기 (yes / no / modify)

## Evidence Reminder

모든 `/submix` 실행 후 **결과 보고 전에** evidence를 기록해야 한다:
1. `subagent-runs/mixed/<run-name>/run-manifest.md`
2. `subagent-runs/mixed/<run-name>/run-summary.md`
3. `subagent-runs/mixed/<run-name>/prompts/*.prompt.md`
4. `subagent-runs/mixed/<run-name>/results/*.result.md`
5. `subagent-runs/mixed/<run-name>/engines/<engine>/*.raw.txt` (외부 엔진 raw stdout)

실패/중단 run도 기록한다. 상세 형식은 `evidence-format.md` 참조.

## 에러 처리

| 실패 유형 | 대응 |
|----------|------|
| 외부 엔진 exit code != 0 | 1회 재시도. 재실패 시 Claude 폴백 |
| 인증 만료 (API 키/토큰) | 사용자에게 에스컬레이션 |
| 타임아웃 | 부분 결과 확인 후 Claude 재실행 또는 사용자 보고 |
| 응답 파싱 실패 | raw stdout을 evidence에 저장, Claude가 재해석 시도 |

> 외부 엔진 실패 시 기본 폴백: **동일 작업을 Claude(sonnet)로 재실행**.
> 상세 에러 처리는 `skills/claude-subagent-orchestrator/references/engine-adapters.md` 참조.

## 타임아웃

| 엔진 | 기본 타임아웃 | 비고 |
|------|-------------|------|
| Claude (Task tool) | 제한 없음 (자체 관리) | - |
| Codex (codex exec) | 300초 (5분) | Bash tool timeout 파라미터 |
| Gemini (gemini-cli) | 120초 (2분) | Bash tool timeout 파라미터 |

타임아웃 초과 시 에러 처리 규칙 적용.

## 외부 엔진 호출 방법

### 프롬프트 전달 원칙
- **짧은 프롬프트** (< 500자): 인라인 문자열로 직접 전달
- **긴 프롬프트** (>= 500자): 임시 파일에 저장 후 `$(cat prompt-file)` 또는 stdin pipe로 전달
- 프롬프트에 **시크릿/자격 증명(API 키, 비밀번호, .env 내용)을 절대 포함하지 않는다**

### Codex (GPT)
```bash
# 짧은 프롬프트
codex exec --full-auto "respond with: OK"

# 긴 프롬프트
codex exec --full-auto "$(cat /tmp/prompt.md)"
```

### Gemini
```bash
# 기본 방식 (stdin pipe -- 테스트 확인됨)
echo "<prompt>" | npx @google/gemini-cli --yolo

# 긴 프롬프트
cat /tmp/prompt.md | npx @google/gemini-cli --yolo
```

## Evidence

혼합 엔진 실행 증거는 `subagent-runs/mixed/<run-name>/`에 저장:

```
subagent-runs/mixed/<run-name>/
├── run-manifest.md
├── run-summary.md
├── prompts/
│   ├── <agent-1>.prompt.md
│   └── <agent-2>.prompt.md
├── results/
│   ├── <agent-1>.result.md
│   └── <agent-2>.result.md
└── engines/
    ├── codex/              # Codex 워커 raw stdout
    │   └── <agent>.raw.txt
    └── gemini/             # Gemini 워커 raw stdout
        └── <agent>.raw.txt
```

## 참조

상세 워크플로우, Anti-Patterns, Known Limitations는 핵심 orchestrator 문서 참조:
- `skills/claude-subagent-orchestrator/SKILL.md`
- `skills/claude-subagent-orchestrator/references/orchestration-workflow.md`
- `skills/claude-subagent-orchestrator/references/engine-adapters.md`
