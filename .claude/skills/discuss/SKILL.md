---
name: discuss
description: 3개 AI 엔진(Claude + Codex/GPT + Gemini)이 하나의 주제에 대해 다중 라운드 토론. 교차 검증으로 답변 품질 극대화.
---

# /discuss

> 실행 전 WKI 인덱싱: `node workspace-knowledge-index/dist/index.js index`

3개 AI가 **같은 주제를 교차 검증**하는 토론 시스템.

## 스킬 체계

| | `/sub` | `/discuss` | `/harness` |
|---|---|---|---|
| 구조 | Claude 단독 위임 | **3엔진 교차 검증** | 에이전트 레지스트리 기반 실행+추적 |
| 목적 | 빠른 위임 | **답변 품질 (토론)** | 실행 관측+재사용 |
| 라운드 | 1회 | 다중 (또는 --quick 1회) | 스테이지 기반 |
| 결과 | 개별 산출물 | **합의안 + 쟁점** | manifest + 이벤트 로그 |

> **참고**: `/submix`는 `/discuss --quick` + `/harness`로 통합되었습니다.

## 모드 분기

| 사용법 | 모드 | 동작 |
|--------|------|------|
| `/discuss <주제>` | 기본 (다중 라운드) | 수렴까지 최대 3라운드, 모더레이터 요약, WKI 주입 |
| `/discuss --quick <주제>` | 퀵 (1회) | 3엔진 독립 의견 1회 수집 → 비교 테이블 → 끝 |
| `/discuss --quick --role "관점" <주제>` | 퀵 + 역할 | 엔진별 관점 지정하여 1회 수집 |

## Entry Protocol

1. Strip `/discuss` prefix
2. `--quick` 플래그 확인 → 모드 결정
3. 주제를 discussion-runner에 전달
4. 실행 계획 표시 → 사용자 승인 (yes/no/modify)
5. 라운드 실행 → 사용자 개입 (continue/stop/guide)
6. 합의안 생성 → Evidence 저장
7. **합의안 자동 검증** → `/sub` 위임 (opus 1 + sonnet 1, 프로젝트 목표·방향성 부합 검증). 자세한 내용 [토론 후 검증](#토론-후-검증-필수) 섹션 참조

## 기본 모드 (다중 라운드)

### 실행

```bash
node packages/launcher/dist/discussion/discuss-cli.js "토론 주제"
node packages/launcher/dist/discussion/discuss-cli.js --spec discussion.json
node packages/launcher/dist/discussion/discuss-cli.js --auto "토론 주제"  # 자동 모드
```

### 라운드 흐름

```
라운드 1: 3엔진 독립 응답 → 모더레이터(haiku) 요약 → 수렴 판정
  ↓ [PARTIAL 또는 DISAGREE]
라운드 2: 이견 집중 + WKI 마이크로 컨텍스트 → 재논의 → 수렴 판정
  ↓ [PARTIAL 또는 DISAGREE]
라운드 3: 최종 라운드 → 결론 도출 (부분 합의도 기록)
```

### 사용자 개입

매 라운드 완료 후:
- **continue** — 다음 라운드 진행
- **stop** — 여기서 종료, 합의안 생성
- **guide "지시"** — 다음 라운드에 추가 관점 주입

## 퀵 모드 (`--quick`, 구 `/submix` 토론 기능)

3엔진 독립 의견을 **1회** 수집하고 비교. 모더레이터 없음, 수렴 없음.

### 실행 예시

```
/discuss --quick PersonaBrain 클러스터 12→8 줄여도 되는가?
```

### 출력 형식

```markdown
## 3엔진 독립 의견

### Claude (sonnet)
[의견]

### Codex/GPT (gpt-5.4)
[의견]

### Gemini (gemini-2.5-pro)
[의견]

## 비교
| 관점 | Claude | GPT | Gemini |
|------|--------|-----|--------|
| 결론 | ... | ... | ... |
| 핵심 근거 | ... | ... | ... |
| 이견 | ... | ... | ... |

## 합의/이견 요약
[합의점과 이견 정리]
```

### 퀵 모드에서 역할 지정

```
/discuss --quick --role "Claude=보안, GPT=성능, Gemini=확장성" 이 아키텍처 괜찮은가?
```

## 역할 커스터마이징 (공통)

```json
{
  "participants": [
    { "engine": "claude", "model": "opus", "role": "보안 관점으로 검토" },
    { "engine": "codex", "model": "gpt-5.4", "role": "비용 효율 관점" },
    { "engine": "gemini", "model": "gemini-2.5-pro", "role": "확장성 관점" }
  ]
}
```

## 엔진별 특성 레퍼런스

### Claude
| 강점 | 적합 관점 |
|------|----------|
| 도구 접근 (파일/검색) | 코드 기반 검증, 현재 상태 확인 |
| 긴 컨텍스트 이해 | 복잡한 아키텍처 분석 |
| 한글 품질 | 한글 기획/문서 토론 |
| 정밀한 지시 따르기 | 정밀 검증 관점 |

**모델**: haiku (경량) / sonnet (기본) / opus (고급)

### Codex — GPT
| 강점 | 적합 관점 |
|------|----------|
| 코드 생성/분석 | 코드 구현 가능성 판단 |
| 폭넓은 라이브러리 지식 | 기술 대안 제시 |
| 구조적 분석 | 비용/효율 관점 |

**모델**: gpt-5.4 (기본) / o3 (추론) / o4-mini (경량)
**호출**: `codex exec --full-auto` (긴 프롬프트는 stdin pipe)

### Gemini
| 강점 | 적합 관점 |
|------|----------|
| 긴 컨텍스트 (1M+) | 대규모 문서/코드 전체 분석 |
| 멀티모달 | UI/디자인 토론 |
| Google 생태계 | GCP/Firebase 관련 |

**모델**: gemini-2.5-pro (기본) / gemini-2.5-flash (경량)
**호출**: `echo "<prompt>" | npx @google/gemini-cli --yolo` (긴 프롬프트는 cat pipe)

## 외부 엔진 호출 원칙

- **긴 프롬프트는 반드시 stdin pipe** — `$(cat file)` 인자 방식은 "Argument list too long" 에러
- 프롬프트에 **시크릿/자격 증명 절대 금지**
- 외부 엔진 실패 시 **Claude(sonnet)로 폴백**
- 타임아웃: Codex 300초, Gemini 120초

## 자동 작업 생성

합의안에서 구체적 실행 항목이 도출되면:
- 구현 필요 → `/harness`로 추천
- Claude 단독 가능 → `/sub`로 추천

## 토론 후 검증 (필수)

토론 합의안은 외관상 그럴듯해도 **프로젝트 궁극 목표·방향성과 어긋날 수 있다**. 따라서 모든 토론 종료 후 합의안을 자동으로 `/sub`에 위임하여 독립 검증한다. 검증 생략 금지 — 합의안이 곧장 `/spec` / `/harness` / 코드 변경으로 넘어가는 경우 더더욱 검증 필수.

### 검증 트리거

| 모드 | 검증 대상 |
|------|-----------|
| 기본 (다중 라운드) | `discussion-summary.md` 합의안 + `conclusion.md` |
| 퀵 (`--quick`) | 비교 테이블 + 합의/이견 요약 |

### 검증자 구성

`subagent-orchestrator` → sub-reviewer **2명 병렬** (read-only):

| 검증자 | 모델 | 역할 |
|--------|------|------|
| 시니어 검토자 | **opus** | 궁극 목표·전략적 정합성 (큰 그림) |
| 광역 검토자 | **sonnet** | 단계 간 연속성·실행 가능성·사실 정확성 (실행 디테일) |

두 모델을 병렬로 돌려 관점 차이가 finding이 되도록 한다 (echo chamber 방지).

### 검증 기준

reviewer는 `project-status/current.md` + `MEMORY.md`(프로젝트 목표·고유 역할 + 사용자 행동 규칙) + Charter/STUB 등 1차 자료를 직접 읽어 다음을 판정:

1. **궁극 목표 부합** — 토론 합의가 프로젝트 최상위 목적과 정렬되는가? (예: loom의 "자율 사회 시뮬 + SNN 창발 + 논문 출판")
2. **뿌리 연속성** — 합의의 산출물이 다음 단계의 입력으로 자연 이어지는가? top-down 점프·단절 없는가?
3. **사용자 명시 제약 보존** — 메모리에 저장된 행동 규칙(예: SNN 창발 우선, 표면 해결 금지)을 위반하지 않는가?
4. **사실 정확성** — 인용된 데이터·코드 위치·freeze 테스트가 현재 상태와 일치하는가?

### 검증 결론

| 결론 | 처리 |
|------|------|
| `APPROVE` (양쪽 동의) | 합의안 확정, 다음 skill 위임 가능 |
| `APPROVE` 1 + `REQUEST_CHANGES` 1 | finding 사용자 보고 + 수용/반려/조정 결정 요청 |
| `REQUEST_CHANGES` (양쪽) | 합의안 재검토 강제 + finding 사용자 보고 |

### Evidence 위치

`subagent-runs/discuss/<topic>-<date>/validation/`:
- `validation-manifest.md` — 검증 메타 (검증자·기준·시각)
- `validation-summary.md` — 종합 결론 (APPROVE / REQUEST_CHANGES + finding 통합)
- `reviewer-opus.result.md` — 시니어 검토 결과
- `reviewer-sonnet.result.md` — 광역 검토 결과
- `validation-prompts/*.prompt.md` — 각 reviewer 프롬프트

---

## Evidence

`subagent-runs/discuss/<topic>-<date>/`에 필수 저장:
- `discussion-manifest.md` — 토론 메타
- `discussion-summary.md` — 합의안
- `conclusion.md` — 최종 결론
- `round-N/` — 라운드별 각 AI 응답 + Moderator 요약
- `wki-context-snapshot.md` — 사용된 WKI 맥락

퀵 모드는 `subagent-runs/discuss/<topic>-<date>-quick/`에 저장.

## Invariants

- Moderator(Claude)는 판정만 — 토론에 참여하지 않음 (기본 모드)
- 퀵 모드에는 모더레이터 없음 — 비교 테이블만 생성
- 수렴 판정: `[AGREE/PARTIAL/DISAGREE]` 라벨 기반
- 최대 3라운드 (기본 모드)
- WKI 맥락은 1회 스냅샷 고정
- Evidence는 필수이며 생략 불가
- 외부 엔진(Codex/Gemini)은 반드시 non-interactive 모드 (--full-auto/--yolo)
- 합의안은 토론 종료 후 **`/sub` 검증 필수** (opus 1 + sonnet 1, 프로젝트 목표·방향성 부합) — 검증 생략 시 다음 skill 위임 금지

## Intellectual Rigor Discipline

`/discuss` produces **quality of judgment**, not code. For cross-validation across three engines to be meaningful, each round must be **verified argumentation**, not superficial agreement.

### Before Debate: Clarify the Question First

- If the topic involves code or documents, **verify the current state first**. Code read last week may have changed today. Chunk-read files >500 LOC.
- If the topic is vague, do not start the debate — "a vague question is not a question." The Moderator refines the question to precision first.

### Argument Quality: Shallow Consensus Is No Consensus

- "All three engines agreed" is not evidence. Strong consensus requires each engine to **arrive at the same conclusion via different reasoning paths**.
- The Moderator guards against superficial AGREE. Distinguish whether the grounds differ or whether an engine is merely echoing the prior response — **analysis shallow enough for a senior reviewer to reject does not pass the round**.
- Technical claims in the consensus MUST be **verifiable against code, documents, or data**. Unverifiable claims are labeled "unverified."

### Context: Memory Fades Across Rounds

- External engines (Codex/Gemini) **cannot retain previous round context**. Explicitly include prior consensus and open issues in the next round's prompt.
- WKI context snapshot is fixed once, but if new file/code references emerge mid-debate, **read the current state at that moment** and pass it.
- Re-run searches with narrower scope when results look sparse. Never build arguments on truncated evidence.

### Deliverable: Is the Consensus Actionable?

- When a debate leads to `/harness` execution, verify that the consensus's technical decisions **are feasible in the current codebase**.

### Breakthrough Protocol: When a Debate Is Stuck

- **Repetition detection**: If all three engines repeat the same argument in different words, **change the question itself**.
- **DISAGREE is the most valuable data**: Treat disagreement as a source of information.
- **Premise inversion**: Extract shared premises → invert the premise itself.
- **"Inconclusive" is not a valid conclusion**: State **why** consensus was not reached and what would resolve it.
- **Honor partial consensus**: Lock confirmed points, keep only open items.
- **Engine swap is a dimension shift**: If one engine fails, try a different engine or restructure the task.
- **Compose partial successes**: Selectively combine successful parts from each engine.
