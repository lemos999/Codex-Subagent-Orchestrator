# 토론 시스템 기획 계획서

> **목적**: 하나의 주제에 대해 Claude + Codex/GPT + Gemini가 다중 라운드 토론하고, 교차 검증으로 답변 품질을 극대화하며, 결과를 저장하는 시스템.
>
> **작성일**: 2026-03-20
> **상태**: Draft v1

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

```
사용자: /discuss "주제"
  ↓
Moderator (Claude)
  ↓
┌─────────────────────────────────────────┐
│              Round 1                     │
│  Claude 의견 → GPT 의견 → Gemini 의견   │
└─────────────────────────────────────────┘
  ↓ (각 의견을 다음 라운드에 전달)
┌─────────────────────────────────────────┐
│              Round 2                     │
│  Claude 반론 → GPT 반론 → Gemini 반론   │
│  (Round 1의 다른 AI 의견을 참조)         │
└─────────────────────────────────────────┘
  ↓ (수렴 확인)
┌─────────────────────────────────────────┐
│              Final                       │
│  Moderator가 합의안 + 쟁점 요약 작성     │
└─────────────────────────────────────────┘
  ↓
결과 저장: discussions/<topic>-<date>/
```

---

## 3. 핵심 구성 요소

### 3.1 Moderator (사회자)

- **역할**: 주제 전달, 라운드 관리, 합의 판정, 결과 정리
- **엔진**: Claude (항상) — 도구 접근 + 파일 저장 필요
- **판단 기준**:
  - 3개 AI가 **같은 결론** → 합의 도출, 토론 종료
  - **의견 분기** → 추가 라운드 (최대 3라운드)
  - 3라운드 후에도 합의 안 됨 → 쟁점 요약 + 각 입장 정리

### 3.2 Participant (토론 참가자)

| 참가자 | 엔진 | 호출 방식 | 강점 |
|---|---|---|---|
| Claude | Task tool | 네이티브 | 정밀한 추론, 한글 |
| GPT (Codex) | `codex exec --full-auto` | Bash | 폭넓은 지식, 코드 생성 |
| Gemini | `npx @google/gemini-cli --yolo` | Bash | 긴 컨텍스트, 멀티모달 |

### 3.3 WKI 연동

- 토론 시작 전 WKI로 **주제 관련 맥락 검색**
- 검색 결과를 3개 AI 모두에게 동일하게 제공
- → 동일한 맥락 위에서 토론하므로 **허공 논쟁 방지**

---

## 4. 토론 프로토콜

### 4.1 Entry

```
/discuss <주제>
```

또는 spec 파일:

```json
{
  "topic": "TypeScript vs Rust for CLI tools",
  "max_rounds": 3,
  "participants": ["claude", "codex", "gemini"],
  "moderator": "claude",
  "output_dir": "discussions/ts-vs-rust-2026-03-20"
}
```

### 4.2 라운드 구조

**Round 1: 초기 의견**
- 각 AI에게 동일한 주제 + WKI 맥락 전달
- 각자 독립적으로 의견 제시
- Moderator가 3개 의견 수집

**Round 2+: 교차 검증**
- 각 AI에게 **다른 2개 AI의 의견**을 전달
- "동의/반론/보완"으로 응답
- Moderator가 수렴도 판정

**Final: 합의 도출**
- Moderator가 합의점 + 쟁점 정리
- 결과 파일 저장

### 4.3 프롬프트 템플릿

**Round 1 (각 참가자에게)**:
```
## Discussion Topic
{topic}

## Context (WKI auto-injected)
{wki_context}

## Your Task
Provide your analysis on this topic. Structure your response:
1. Position: your main argument
2. Reasoning: supporting evidence
3. Concerns: potential risks or downsides
4. Recommendation: your suggested approach
```

**Round 2+ (각 참가자에게)**:
```
## Discussion Topic
{topic}

## Previous Round
### Claude said:
{claude_round1}

### GPT said:
{gpt_round1}

### Gemini said:
{gemini_round1}

## Your Task
Review the other participants' arguments. Respond with:
1. Agree: points you agree with and why
2. Disagree: points you disagree with and why
3. New insight: anything missed by others
4. Updated position: has your view changed?
```

---

## 5. 결과 저장

```
discussions/
└── <topic-slug>-<YYYY-MM-DD>/
    ├── discussion-manifest.md    ← 토론 요약 (주제, 참가자, 라운드 수, 합의 여부)
    ├── round-1/
    │   ├── claude.md             ← Claude 의견
    │   ├── codex.md              ← GPT 의견
    │   └── gemini.md             ← Gemini 의견
    ├── round-2/
    │   ├── claude.md
    │   ├── codex.md
    │   └── gemini.md
    └── conclusion.md             ← 합의안 + 쟁점 요약
```

---

## 6. 구현 계획

### Phase 1: MVP (최소 기능)
- `/discuss` 스킬 정의
- 1라운드 토론 (3개 AI 의견 수집 + 합의안)
- 결과 파일 저장
- WKI 맥락 주입

### Phase 2: 다중 라운드
- 라운드 2~3 교차 검증
- 수렴 판정 로직
- 라운드별 결과 저장

### Phase 3: 고도화
- spec 파일 기반 토론 설정
- 토론 이력 검색 (WKI 인덱싱)
- 특정 AI 모델/역할 커스터마이징
- 토론 결과 기반 자동 작업 생성

---

## 7. 기술 결정 사항

| 결정 | 선택 | 근거 |
|---|---|---|
| Moderator 엔진 | Claude | 도구 접근 (파일 저장) + 판단력 |
| 호출 방식 | TS 런처 or 직접 Bash | 기존 인프라 활용 |
| 저장 형식 | Markdown | 사람이 읽기 쉬움, WKI 인덱싱 가능 |
| 최대 라운드 | 3 | 비용 효율 (3라운드 이상은 수렴 어려움) |
| WKI 연동 | 필수 | 동일 맥락 보장 |

---

## 8. 비용 추정

| 라운드 | AI 호출 | 예상 토큰 |
|---|---|---|
| Round 1 | 3회 (각 AI) | ~3,000 토큰 |
| Round 2 | 3회 (각 AI + 이전 라운드 컨텍스트) | ~6,000 토큰 |
| Round 3 | 3회 | ~9,000 토큰 |
| 합의안 | 1회 (Moderator) | ~2,000 토큰 |
| **합계** | **10회** | **~20,000 토큰** |

로컬 CLI 사용 시 **추가 API 비용 없음** (구독 요금 내).

---

## 9. `/submix`와의 통합

토론 시스템은 `/submix`와 별개 명령이지만, 내부적으로 동일한 인프라를 사용:

- 엔진 호출: TS 런처의 spawn 로직 재사용
- WKI 맥락: wki-context.ts 재사용
- 결과 저장: evidence 패턴 참조

```
/sub     → 분업 (Claude 단독)
/submix  → 분업 (3개 AI 혼합)
/discuss → 토론 (3개 AI 교차 검증)  ← NEW
```
