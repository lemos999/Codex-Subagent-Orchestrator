---
name: harness
description: 하네스 모드 오케스트레이션. `/harness <요청>`으로 에이전트 레지스트리 기반 워커를 자동 구성·실행. 이벤트 스트리밍 + 세션 추적.
---

# /harness

에이전트 레지스트리 + 이벤트 스트리밍 기반 오케스트레이션.
사용자가 요청만 하면 적절한 에이전트를 자동 선택하고 spec을 생성하여 실행한다.

## 인수 없이 호출 시 — 도움말

```
/harness — 하네스 모드 오케스트레이션

사용법:
  /harness <요청>

■ 자동 구성
  /harness 이 파일 리팩토링해줘         → impl + reviewer 자동 구성
  /harness spawn.ts 버그 수정          → impl(fixer) + reviewer 자동 구성
  /harness 이 코드 리뷰해줘             → reviewer 단독

■ 에이전트 지정
  /harness impl-codex로 구현해줘       → 특정 에이전트 지정
  /harness reviewer + impl-claude      → 다중 에이전트 명시

■ 레지스트리 관리
  /harness agents                      → 등록된 에이전트 목록
  /harness agent:new <id>              → 새 에이전트 YAML 생성

■ 참조
  에이전트: config/agents/*.yaml
  설계 문서: packages/launcher/_confirmed/harness/
```

## Entry Protocol

1. Strip `/harness` prefix
2. 요청 분석 → 모드 분기

## 모드 분기

| 요청 | 모드 | 동작 |
|------|------|------|
| `agents` | 목록 | `config/agents/` 스캔하여 에이전트 목록 출력 |
| `agent:new <id>` | 생성 | 인터랙티브 에이전트 YAML 생성 |
| 그 외 | 실행 | 요청 분석 → spec 자동 생성 → 실행 |

## 실행 모드 상세

### Step 1: 요청 분석

사용자 요청에서 추출:
- **작업 유형**: 구현(impl), 리뷰(review), 수정(fix), 기획(plan), 기타(custom)
- **대상 파일/범위**: 언급된 파일, 디렉토리
- **명시된 에이전트**: `impl-codex로`, `reviewer +` 등의 패턴

### Step 2: 에이전트 자동 선택

명시적 에이전트 지정이 없으면 작업 유형에 따라 자동 선택:

| 작업 유형 | 기본 구성 | 에이전트 |
|-----------|---------|---------|
| 구현 | impl → reviewer (2-stage) | `impl-codex` → `reviewer` |
| 리뷰 | reviewer 단독 | `reviewer` |
| 수정(버그) | fixer → reviewer (2-stage) | `fixer` → `reviewer` |
| 기획 | planner 단독 | `planner` |
| 기타 | custom 단독 | 인라인 prompt |

`config/agents/`에 해당 에이전트가 없으면 인라인 방식으로 폴백 (레지스트리 없이).

### Step 3: spec 자동 생성

임시 spec JSON을 생성하여 `output/harness-runs/` 아래에 저장.

```json
{
  "cwd": ".",
  "execution_mode": "sequential",
  "output_dir": "output/harness-runs/{timestamp}",
  "write_summary_file": true,
  "agents": [
    {
      "name": "impl",
      "agent_id": "impl-codex",
      "task": "사용자 요청 텍스트"
    },
    {
      "name": "review",
      "agent_id": "reviewer",
      "stage": 2,
      "task": "impl의 변경사항을 리뷰해줘"
    }
  ]
}
```

### Step 4: 실행

```bash
node packages/launcher/dist/cli.js --spec {생성된 spec} --harness
```

### Step 5: 결과 보고

실행 완료 후:
1. manifest에서 결과 요약
2. 이벤트 로그에서 도구 사용 통계
3. 사용자에게 간결한 결과 보고

## 에이전트 목록 모드

`/harness agents` 실행 시:

```bash
node -e "
const {listAgentIds} = require('./packages/launcher/dist/harness/index.js');
const ids = listAgentIds(process.cwd());
if (ids.length === 0) { console.log('등록된 에이전트 없음. /harness agent:new <id>로 생성하세요.'); }
else { ids.forEach(id => console.log('  ' + id)); }
"
```

또는 `config/agents/` 디렉토리를 직접 읽어서 YAML 파일 목록을 출력.

## 에이전트 생성 모드

`/harness agent:new <id>` 실행 시:

1. id 확인 (영숫자, 하이픈, 언더스코어만)
2. `config/agents/{id}.yaml` 경로에 템플릿 생성
3. 사용자에게 engine/model/system prompt 질문 (또는 기본값 사용)

기본 템플릿:

```yaml
id: {id}
version: 1
name: "{id}"
engine: claude
model: sonnet
system: |
  # 여기에 에이전트 역할을 정의하세요.
defaults:
  sandbox: workspace-write
  kind: custom
```

## Invariants

- 기존 `/sub` 워크플로우와 독립 — 하네스는 TS launcher 기반, /sub는 Claude Task tool 기반
- 에이전트 레지스트리는 `config/agents/`에 영속 — spec은 임시
- `--harness` 플래그 항상 활성화
- 이벤트 로그는 `output/harness-runs/{timestamp}/`에 보관
