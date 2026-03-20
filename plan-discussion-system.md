# 토론 시스템 기획 계획서

> **목적**: 하나의 주제에 대해 Claude + Codex/GPT + Gemini가 다중 라운드 토론하고, 교차 검증으로 답변 품질을 극대화하며, 결과를 저장하는 시스템.
>
> **작성일**: 2026-03-20
> **상태**: Draft v2 — 3AI 교차 검증 반영 (Claude opus + Codex gpt-5.4 + Gemini pro)

---

## 1. 왜 필요한가

### 현재 `/submix`와의 차이

| | `/submix` (분업) | 토론 시스템 |
|---|---|---|
| 구조 | 각 AI가 **다른 역할** (구현/리뷰/검증) | 같은 주제를 **3개 AI가 검토** |
| 목적 | 작업 효율 (병렬 처리) | 답변 품질 (교차 검증) |
| 라운드 | 1회 (각자 실행 후 종료) | **다중 라운드** (상대 의견 참조 후 보완) |
| 결과 | 각 워커의 개별 산출물 | **합의안 + 쟁점 요약** |

### 활용 시나리오

- 아키텍처 설계 결정 — 3개 AI의 다른 관점을 비교
- 코드 리뷰 — 놓칠 수 있는 버그를 교차 검증
- 기획 검토 — 다각도 분석
- 기술 선택 — 언어/프레임워크/도구 비교

---

## 2. 시스템 아키텍처

### 실행 주체: 별도 `discussion-runner` (TS)

> **CRITICAL 결정**: 기존 TS 런처(`packages/launcher`)는 단일 spec 실행이며, 이전 stage 결과를 다음 stage 프롬프트에 반영하는 루프 구조가 없다. 따라서 `/discuss`는 **별도 discussion-runner**가 필요하다. 기존 인프라(`spawn.ts`, `wki-context.ts`, evidence writer)를 재사용하되, 라운드 루프는 새로 구현한다.

```
사용자: /discuss "주제"
  ↓
Discussion Runner (새 TS 모듈)
  ↓
1. WKI 맥락 검색 (1회, 스냅샷으로 고정)
  ↓
2. 실행 계획 표시 → 사용자 승인 (yes/no/modify)
  ↓
┌─────────────────────────────────────────┐
│              Round 1 (병렬)              │
│  Claude 의견 ∥ GPT 의견 ∥ Gemini 의견   │
└─────────────────────────────────────────┘
  ↓ Moderator: 수렴 판정
┌─────────────────────────────────────────┐
│              Round 2 (병렬)              │
│  각 AI에게 다른 2개 의견 전달 → 반론     │
└─────────────────────────────────────────┘
  ↓ Moderator: 수렴 판정
┌─────────────────────────────────────────┐
│              Final                       │
│  Moderator가 합의안 + 쟁점 요약 작성     │
└─────────────────────────────────────────┘
  ↓
Evidence 저장: subagent-runs/discuss/<topic>-<date>/
```

---

## 3. 핵심 구성 요소

### 3.1 Moderator (사회자)

- **역할**: 주제 전달, 라운드 관리, 합의 판정, 결과 정리
- **엔진**: Claude (항상) — 도구 접근 + 파일 저장 필요
- **Participant와 분리**: Moderator용 Claude 호출과 Participant용 Claude 호출은 **별도 Task**로 분리. Moderator는 토론에 참여하지 않고 판정만 수행.
- **수렴 판정 기준**:
  - 각 참가자가 응답에 **명시적 라벨** 포함: `[AGREE]`, `[PARTIAL]`, `[DISAGREE]`
  - 3인 모두 `[AGREE]` → 합의 도출, 토론 종료
  - `[DISAGREE]` 1개 이상 → 추가 라운드 (최대 3라운드)
  - 3라운드 후에도 `[DISAGREE]` 존재 → 쟁점 요약 + 각 입장 정리

### 3.2 Participant (토론 참가자)

| 참가자 | 엔진 | 호출 방식 | 강점 |
|---|---|---|---|
| Claude | `spawn.ts` (stdin) | Bash → `claude --print` | 정밀한 추론, 한글 |
| GPT (Codex) | `spawn.ts` (stdin) | Bash → `codex exec --full-auto` | 폭넓은 지식, 코드 생성 |
| Gemini | `spawn.ts` (stdin) | Bash → `npx @google/gemini-cli --yolo` | 긴 컨텍스트, 멀티모달 |

### 3.3 WKI 연동

- 토론 시작 전 WKI로 **주제 관련 맥락 1회 검색**
- 검색 결과를 **스냅샷으로 고정** — 모든 라운드에서 동일한 맥락 사용
- → 라운드마다 다른 맥락이 주입되는 문제 방지

---

## 4. 토론 프로토콜

### 4.1 Entry + 승인

```
/discuss <주제>
```

사용자에게 실행 계획 표시 후 승인 대기 (/submix와 동일):

```markdown
## /discuss Execution Plan

**Topic**: [주제]
**Max rounds**: 3
**Participants**: Claude (sonnet), Codex (gpt-5.4), Gemini (gemini-2.5-flash)
**Moderator**: Claude (separate, judgment only)
**WKI context**: [검색된 맥락 요약]

> **yes** — 토론 시작
> **no** — 취소
> **modify** — 참가자/라운드 수 변경
```

### 4.2 Discussion Spec (선택적)

`/discuss`는 기존 런처 spec과 **별도 포맷** 사용:

```json
{
  "type": "discussion",
  "topic": "TypeScript vs Rust for CLI tools",
  "max_rounds": 3,
  "participants": [
    { "engine": "claude", "model": "sonnet" },
    { "engine": "codex", "model": "gpt-5.4" },
    { "engine": "gemini", "model": "gemini-2.5-flash" }
  ],
  "output_dir": "subagent-runs/discuss/ts-vs-rust-2026-03-20",
  "response_max_lines": 30,
  "wki_context_topk": 5
}
```

> 이 포맷은 TS 런처의 `LauncherSpec`과 호환되지 않음 — discussion-runner가 자체적으로 파싱.

### 4.3 라운드 구조

**Round 1: 초기 의견 (3 AI 병렬)**
- 각 AI에게 동일한 주제 + WKI 맥락(스냅샷) 전달
- 각자 독립적으로 의견 제시
- 응답 끝에 반드시 `[POSITION: 한 줄 요약]` 포함

**라운드 사이: 사용자 개입 (interactive mode)**
- 각 라운드 완료 후 결과를 표시하고 사용자에게 선택지 제공:
```
> **continue** — 다음 라운드 진행
> **stop** — 여기서 종료, 합의안 생성
> **guide "지시"** — "이 관점도 고려해줘" 등 추가 지시를 다음 라운드에 반영
> **modify** — 참가자/모델 변경
```
- `guide` 지시는 다음 라운드 프롬프트에 `## User Guidance` 섹션으로 주입

**Round 2+: 교차 검증 (3 AI 병렬)**
- 각 AI에게 **Moderator가 요약한 이전 라운드 요약** 전달 (원문이 아닌 요약 — 토큰 절감)
- 사용자 guide가 있으면 `## User Guidance` 섹션 포함
- 응답에 반드시 `[AGREE]`, `[PARTIAL]`, `[DISAGREE]` 라벨 포함
- Moderator가 라벨 기반으로 수렴 판정

**Final: 합의 도출**
- Moderator가 합의점 + 쟁점 정리
- Evidence 파일 저장

### 4.4 프롬프트 템플릿

**Round 1 (각 참가자에게)**:
```
## Discussion Topic
{topic}

## Context (WKI snapshot)
{wki_context}

## Instructions
Provide your analysis. Structure your response:
1. **Position**: your main argument
2. **Reasoning**: supporting evidence
3. **Concerns**: potential risks or downsides
4. **Recommendation**: your suggested approach

End with: [POSITION: one-line summary of your stance]
Keep response under {response_max_lines} lines.
```

**Round 2+ (각 참가자에게)**:
```
## Discussion Topic
{topic}

## Previous Round Summary (by Moderator)
{moderator_summary}

## Instructions
Review the other participants' arguments. Respond with:
1. **[AGREE/PARTIAL/DISAGREE]**: your verdict on the overall direction
2. **Reasoning**: why you agree or disagree
3. **New insight**: anything missed by others
4. **Updated position**: has your view changed?

End with: [POSITION: one-line summary of your updated stance]
Keep response under {response_max_lines} lines.
```

**Moderator 요약 (라운드 간)**:
```
## Round {n} Summary Task

Summarize each participant's position in 3 lines max each.
Identify: areas of agreement, areas of disagreement, open questions.
Do NOT inject your own opinion. Be neutral.
```

---

## 5. Evidence 저장

> Evidence 정책: `/sub`, `/submix`와 동일하게 **필수이며 생략 불가**.

```
subagent-runs/discuss/
└── <topic-slug>-<YYYY-MM-DD>/
    ├── discussion-manifest.md    ← 토론 메타 (주제, 참가자, 라운드 수, 합의 여부)
    ├── discussion-summary.md     ← 최종 합의안 + 쟁점
    ├── round-1/
    │   ├── claude.md
    │   ├── codex.md
    │   ├── gemini.md
    │   └── moderator-summary.md  ← Moderator의 라운드 요약
    ├── round-2/
    │   ├── claude.md
    │   ├── codex.md
    │   ├── gemini.md
    │   └── moderator-summary.md
    └── wki-context-snapshot.md   ← 토론에 사용된 WKI 맥락 (재현용)
```

---

## 6. 에러 처리

| 실패 유형 | 대응 |
|----------|------|
| 특정 AI 엔진 실패 (exit != 0) | 1회 재시도. 재실패 시 **2-of-3으로 토론 계속** (해당 AI 의견 "[UNAVAILABLE]"로 표시) |
| 특정 AI 타임아웃 | 동일 — 2-of-3으로 계속 |
| 인증 만료 | 사용자에게 에스컬레이션 |
| Moderator 실패 | 토론 중단, 현재까지의 evidence 저장 |
| 사용자 중간 취소 | 현재까지의 라운드 결과 저장 + 부분 conclusion 생성 |

---

## 7. 구현 계획

### Phase 1: MVP (최소 기능)
- `.claude/skills/discuss/SKILL.md` 작성
- AGENTS.md에 `/discuss` 라우팅 규칙 추가
- `packages/launcher/src/discussion/` 디렉터리 생성
  - `discussion-runner.ts` — 라운드 루프 + 수렴 판정
  - `discussion-spec.ts` — spec 파싱 (별도 포맷)
- 1라운드 토론 (3개 AI 병렬 의견 수집 + Moderator 합의안)
- **사용자 개입 (interactive mode)**: 라운드 사이에 continue/stop/guide/modify 선택
- Evidence 저장 (`subagent-runs/discuss/`)
- WKI 맥락 스냅샷 주입
- spawn.ts 재사용 (엔진 호출)

### Phase 2: 다중 라운드
- 라운드 2~3 교차 검증
- Moderator 라운드 요약 (원문 대신 요약 전달 — 토큰 절감)
- `[AGREE/PARTIAL/DISAGREE]` 라벨 기반 수렴 판정
- 라운드별 evidence 저장

### Phase 3: 고도화
- 토론 이력 WKI 인덱싱 (과거 토론 결과 검색)
- AI 모델/역할 커스터마이징
- 토론 결과 기반 자동 작업 생성 (`/discuss` → 결론에서 `/sub` 자동 발행)

---

## 8. 기술 결정 사항

| 결정 | 선택 | 근거 |
|---|---|---|
| 실행 주체 | 별도 discussion-runner (TS) | TS 런처는 단일 spec 실행 — 라운드 루프 불가 |
| Moderator 엔진 | Claude (별도 Task) | 도구 접근 + 판단력. Participant와 분리하여 편향 방지 |
| Spec 포맷 | 별도 DiscussionSpec | 런처 LauncherSpec과 호환 불가 (topic, max_rounds 등) |
| 저장 경로 | `subagent-runs/discuss/` | 기존 evidence 체계와 통합 |
| 저장 형식 | Markdown | 사람이 읽기 쉬움, WKI 인덱싱 가능 |
| 최대 라운드 | 3 | 비용 효율 (3라운드 이상은 수렴 어려움) |
| WKI 연동 | 1회 스냅샷 고정 | 라운드마다 다른 맥락 주입 방지 |
| 수렴 판정 | 명시적 라벨 기반 | 자연어 판단보다 신뢰성 높음 |
| 라운드 간 전달 | Moderator 요약 (원문 X) | 토큰 누적 방지 |
| 엔진 호출 | spawn.ts 재사용 | 기존 인프라 활용, .cmd 처리 등 해결됨 |
| 사용자 승인 | /submix와 동일 프로토콜 | 일관된 UX |

---

## 9. 비용 추정

### 운영 비용 (토론 1회당)

| 라운드 | AI 호출 | 입력 토큰 | 출력 토큰 | 합계 |
|---|---|---|---|---|
| Round 1 | 3회 (병렬) | ~1,500 (주제+WKI) × 3 | ~1,000 × 3 | ~7,500 |
| Moderator 요약 | 1회 | ~3,000 (3개 의견) | ~500 | ~3,500 |
| Round 2 | 3회 (병렬) | ~2,000 (주제+요약) × 3 | ~1,000 × 3 | ~9,000 |
| Moderator 요약 | 1회 | ~3,000 | ~500 | ~3,500 |
| Round 3 | 3회 (병렬) | ~2,000 × 3 | ~1,000 × 3 | ~9,000 |
| 합의안 | 1회 | ~4,000 (전체 요약) | ~1,000 | ~5,000 |
| **합계** | **12회** | | | **~37,500 토큰** |

> 이전 추정 ~20,000은 입력 토큰을 미포함한 낙관적 수치였음.
> 현재 추정 ~37,500은 입출력 합산. 실제로는 응답 길이에 따라 변동.
> 로컬 CLI 사용 시 **추가 API 비용 없음** (구독 요금 내).

### 개발 비용 예측

| Phase | 내용 | 예상 시간 | Claude 토큰 | 외부 엔진 토큰 |
|---|---|---|---|---|
| Phase 1 (MVP) | /discuss 스킬 + 1라운드 + 결과 저장 | 1~2시간 | ~15,000 | 0 |
| Phase 2 (다중 라운드) | 교차 검증 + 수렴 판정 | 1~2시간 | ~15,000 | 0 |
| Phase 3 (고도화) | spec, 이력 검색, 커스터마이징 | 2~3시간 | ~20,000 | 0 |
| 리뷰/테스트 | 코드 리뷰 + 실제 토론 실행 | 1시간 | ~30,000 | ~50,000 |
| **합계** | | **5~8시간** | **~80,000** | **~50,000** |

---

## 10. 인프라 재사용

| 기존 모듈 | 재사용 방식 |
|---|---|
| `spawn.ts` | 3개 엔진 CLI 호출 (stdin 방식) |
| `wki-context.ts` | WKI 맥락 검색 (generateContext) |
| `evidence-format.md` | 저장 형식 참조 |
| `common/platform.ts` | Windows .cmd 처리 |
| `common/fs-helpers.ts` | writeFileSafe, sha256 |

### 새로 구현할 모듈

| 모듈 | 역할 |
|---|---|
| `discussion-runner.ts` | 라운드 루프 + 수렴 판정 + evidence 저장 |
| `discussion-spec.ts` | DiscussionSpec 파싱 |
| `.claude/skills/discuss/SKILL.md` | 스킬 정의 |
| AGENTS.md 업데이트 | `/discuss` 라우팅 규칙 |

---

## 11. `/sub`, `/submix`, `/discuss` 통합

```
/sub     → 분업 (Claude 단독)        → subagent-runs/claude/
/submix  → 분업 (3개 AI 혼합)        → subagent-runs/mixed/
/discuss → 토론 (3개 AI 교차 검증)    → subagent-runs/discuss/  ← NEW
```

세 명령 모두:
- Evidence 필수
- WKI 맥락 주입
- 사용자 승인 프로토콜
- `spawn.ts` 기반 엔진 호출
