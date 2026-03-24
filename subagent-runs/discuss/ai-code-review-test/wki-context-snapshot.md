## Relevant Context (auto-injected)

### project-status/current.md (lines 23-29)
**다음 작업 (우선순위 순)** — markdown-section
> ## 다음 작업 (우선순위 순)
> 
> 1. **토론 시스템 (Claude + Codex + Gemini 3자 moderator)** — 하나의 주제에 대해 3개 AI가 다중 라운드 토론하고 결과를 저장하는 시스템
> 2. **WKI 다중 프로젝트 자동 지원** — 이 폴더에 새 프로젝트 폴더를 복사하면 자동 인덱싱
> 3. **WKI 검색 알고리즘 개선** — 8건의 개선 후보 (re-ranking, query expansion 강화 등)

### skills/codex-subagent-orchestrator/SKILL.md (lines 14-31)
**Overview** — markdown-section
> ## Overview
> 
> Use this skill when the parent Codex instance should supervise execution rather than perform the whole task directly.
> 
> The parent should:

### skills/codex-subagent-orchestrator/references/orchestration-workflow.md (lines 289-300)
**Pattern B: Parallel independent workers** — markdown-section
> ## Pattern B: Parallel independent workers
> 
> Use for independent tasks such as:
> 
> - one worker per file

### skills/gemini-subagent-orchestrator/references/orchestration-workflow.md (lines 9-19)
**1. Classify the Request & Choose Pattern** — markdown-section
> ### 1. Classify the Request & Choose Pattern
> 
> When the user requests `/sub <task>`, decide the smallest useful team:
> - **Pattern A (Solo):** one worker for a narrow artifact
> - **Pattern B (Implement-Review):** default for bounded implementation

### skills/codex-subagent-orchestrator/references/sub-command-protocol.md (lines 114-125)
**Parallel Rule** — markdown-section
> ## Parallel Rule
> 
> Run workers in parallel only when:
> 
> - they are independent
