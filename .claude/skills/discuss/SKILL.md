---
name: discuss
description: 3개 AI 엔진(Claude + Codex/GPT + Gemini)이 하나의 주제에 대해 다중 라운드 토론. 교차 검증으로 답변 품질 극대화.
---

# /discuss

> 실행 전 WKI 인덱싱: `node workspace-knowledge-index/dist/index.js index`

3개 AI가 **같은 주제를 교차 검증**하는 토론 시스템.

## `/sub` vs `/submix` vs `/discuss` 차이

| | `/sub` | `/submix` | `/discuss` |
|---|---|---|---|
| 구조 | Claude 단독 분업 | 3개 AI 혼합 분업 | **3개 AI 교차 검증** |
| 목적 | 작업 효율 | 작업 효율 (멀티엔진) | **답변 품질** |
| 라운드 | 1회 | 1회 | **다중 라운드** |
| 결과 | 개별 산출물 | 개별 산출물 | **합의안 + 쟁점** |

## Entry Protocol

1. Strip the `/discuss` prefix
2. 주제를 discussion-runner에 전달
3. 실행 계획 표시 → 사용자 승인 (yes/no/modify)
4. 라운드 실행 → 사용자 개입 (continue/stop/guide)
5. 합의안 생성 → Evidence 저장

## 실행

```bash
node packages/launcher/dist/discussion/discuss-cli.js "토론 주제"
node packages/launcher/dist/discussion/discuss-cli.js --spec discussion.json
node packages/launcher/dist/discussion/discuss-cli.js --auto "토론 주제"  # 자동 모드
```

## 역할 커스터마이징

참가자에 역할을 부여하여 특정 관점에서 분석하도록 지시:

```json
{
  "participants": [
    { "engine": "claude", "model": "opus", "role": "보안 관점으로 검토" },
    { "engine": "codex", "model": "gpt-5.4", "role": "비용 효율 관점" },
    { "engine": "gemini", "model": "gemini-2.5-pro", "role": "확장성 관점" }
  ]
}
```

## 사용자 개입

매 라운드 완료 후:
- **continue** — 다음 라운드 진행
- **stop** — 여기서 종료, 합의안 생성
- **guide "지시"** — 다음 라운드에 추가 관점 주입

## 자동 작업 생성

합의안에서 구체적 실행 항목이 도출되면 `/sub` 또는 `/submix` 명령으로 자동 추천됩니다.

## Evidence

`subagent-runs/discuss/<topic>-<date>/`에 필수 저장:
- `discussion-manifest.md` — 토론 메타
- `discussion-summary.md` — 합의안
- `conclusion.md` — 최종 결론
- `round-N/` — 라운드별 각 AI 응답 + Moderator 요약
- `wki-context-snapshot.md` — 사용된 WKI 맥락

## Invariants

- Moderator(Claude)는 판정만 — 토론에 참여하지 않음
- 수렴 판정: `[AGREE/PARTIAL/DISAGREE]` 라벨 기반
- 최대 3라운드
- WKI 맥락은 1회 스냅샷 고정
- Evidence는 필수이며 생략 불가

## Intellectual Rigor Discipline

`/discuss`는 코드가 아니라 **판단의 품질**을 만든다. 세 엔진의 교차 검증이 의미 있으려면, 각 라운드가 피상적 동의가 아닌 **검증된 논증**이어야 한다.

### 토론 전: 질문을 먼저 정리하라

- 토론 주제에 코드/문서가 연관되면, **현재 상태를 먼저 확인**한다. 지난주 읽은 코드가 오늘도 같다고 가정하지 않는다. 500LOC 초과 파일은 분할 읽기.
- 주제가 모호하면 토론을 시작하지 않는다 — "모호한 질문은 질문이 아니다." Moderator가 먼저 질문을 명확히 정제한다.

### 논증 품질: 얕은 합의는 합의가 아니다

- "세 엔진이 동의했다"는 증거가 아니다. 각 엔진이 **다른 경로로 같은 결론에 도달**했을 때만 강한 합의다.
- Moderator는 피상적 AGREE를 경계한다. 동의의 근거가 다른지, 단순히 앞 응답을 반복하는 것인지 판별한다 — **시니어 리뷰어가 리젝트할 수준의 얕은 분석은 라운드를 통과시키지 않는다**.
- 합의안에 포함된 기술적 주장은 **코드/문서/데이터로 검증 가능해야** 한다. 검증 불가한 주장은 "미검증"으로 표기한다.

### 맥락: 라운드를 넘으면 기억이 흐려진다

- 외부 엔진(Codex/Gemini)은 **이전 라운드의 맥락을 유지하지 못한다**. 다음 라운드 프롬프트에 이전 합의/쟁점을 명시적으로 포함한다.
- WKI 맥락 스냅샷은 1회 고정이지만, 토론 중 새로운 파일/코드 참조가 필요하면 **해당 시점의 최신 상태를 읽어** 전달한다.
- 검색 결과가 의심스럽게 적으면 범위를 좁혀 재실행. Truncation된 근거 위에 논증을 쌓지 않는다.

### 산출물: 합의안이 실행 가능한가

- 토론이 `/sub`나 `/submix` 실행으로 이어질 경우, 합의안의 기술적 결정이 **현재 코드베이스에서 실현 가능한지** 확인한다. 존재하지 않는 함수나 삭제된 모듈을 전제한 합의안은 실행 단계에서 깨진다.
