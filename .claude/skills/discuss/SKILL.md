---
name: discuss
description: 3개 AI 엔진(Claude + Codex/GPT + Gemini)이 하나의 주제에 대해 다중 라운드 토론. 교차 검증으로 답변 품질 극대화.
---

# /discuss

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
