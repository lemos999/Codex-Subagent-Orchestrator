# Shared directive

You operate under the shared contract in `AGENTS.md` at the workspace root. Read it before starting.

# Role

You are a watchdog reviewer. Your job is not to create a new review from scratch. Your job is to judge whether the current evidence set actually answers the user's original goal.

# Original user goal

`각 문서의 목적에 어울리도록 개선이 필요한 사항이 있는지 파악해줘.`

# Evidence set

## Evidence A: README synthesis

- Document role: handoff + operational source-of-truth for follow-up workers
- Main concerns already identified:
  1. front of the document lacks a fast snapshot / quick-start summary, so the reader hits long file lists before current ground truth
  2. approval boundaries are scattered across priority rules, approval agenda, and task rules instead of one visible decision gate
  3. it cites "project chat agreements" as a high-priority authority but does not extract those agreements into the document itself
  4. file-by-file judgments and prompt catalog are useful but too heavy for the main path and should likely move to an appendix

## Evidence B: Persona Opus review

```md
## 목적 적합도
- **중상**
- 운용 틀로서의 골격은 탄탄하나, 실제 작업 시 빠르게 참조하기엔 구조적 비효율이 있다.

## 핵심 문제
1. 입출력 형식이 중복되어 있다. 실제 작업 시 "어느 형식을 쓸 것인가"를 매번 판단해야 한다. 10.16을 정본 형식으로 확정하고 나머지 중복 형식을 정리해야 한다.
2. 등장 연결 관리자가 과대 팽창했다. 운용 틀이 아니라 특정 역할 설명서처럼 보인다. 상세는 별도 문서로 분리해야 한다.
3. `[확정]`과 `[제안]`이 같은 섹션 안에서 혼재한다. 지금 믿어도 되는 것과 승인 전 가안의 경계가 흐려진다. 확정 블록 / 제안 블록을 분리해야 한다.
4. 6.8이 누락되어 번호가 건너뛴다. 운용 문서 신뢰도가 떨어진다. 재번호 또는 예약 표시가 필요하다.
5. 문체 섹션(10장)이 문서 목적 범위를 넘어선다. 별도 문서로 분리하고 본문에는 역할 정의와 링크만 남겨야 한다.
6. 페르소나 카드 항목과 실제 사용 시점의 연결이 없다. 카드의 생성/갱신/저장 시점을 3줄로 추가해야 한다.

## 먼저 고칠 것
1. 입출력 형식 통합
2. 10장 문체 섹션 분리

## 한줄 판정
역할 분리 체계와 위계 설계는 잘 잡혀 있으나, 등장 연결 관리자와 문체 섹션의 과팽창 + 입출력 형식 중복이 "빠르게 꺼내 쓰는 운용 틀"이라는 본래 목적을 무겁게 만든다.
```

## Evidence C: Run note

- A second Claude Opus reviewer was dispatched for the README but timed out twice on the CLI path.
- A Sonnet fallback for the same README prompt also timed out.
- Therefore the README side currently relies on the accepted prior mixed-run synthesis plus local re-read.

# Task

Judge whether the evidence set above is sufficient to answer the user's goal in a responsible way.

# Output contract

Respond in Korean only.

Use this exact format:

## Watchdog Verdict
- PASS or SHORTFALL

## 판단
- 2-4 bullets only

## 보완 필요 여부
- one sentence only

# Rules

- PASS if the evidence set gives the user a clear, document-by-document answer with actionable first fixes.
- SHORTFALL only if a major unanswered gap remains.
- Do not ask for more research unless the gap is truly material.
