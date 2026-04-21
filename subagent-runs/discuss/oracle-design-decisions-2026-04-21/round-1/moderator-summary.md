# Round 1 — Moderator 요약 및 수렴 판정

**Date**: 2026-04-21
**Participants**: Claude opus, Codex gpt-5.4, Gemini 2.5-pro

---

## 응답 요약 표

| 엔진 | Topic 1 | Topic 2 |
|------|---------|---------|
| Claude opus | **제외** | **A** (v2_ablation.py 포크) |
| Codex gpt-5.4 | **제외** | **D** (v2.py import + subclass/no-op override, 파일명 `oracle_rule2_ablation.py` 권고) |
| Gemini 2.5-pro | **제외** | **A** (v2_ablation.py 포크) |

---

## Topic 1: BollRev 편입 여부 — 판정 **AGREE (제외)**

3엔진 모두 "제외" 결론. 추론 경로 독립성 확인:

- **Claude opus**: Charter "Differentiation Thesis" 레이어 분리 원칙 + context 벡터 기계적 하드코딩 + variants 체계 축 불일치 (risk tolerance vs strategy type)
- **Codex gpt-5.4**: 공수 정량 분석 (BollRev 신설 20-35h vs feature reuse 4-10h) + 현 repo 기준 BollRev는 "variant가 아닌 별도 엔진급"
- **Gemini 2.5-pro**: 계층 분리 원칙(무엇/어떻게) + 피처 중복 부채화 + 초기 모델 일반화 능력 보호

**서로 다른 추론 경로로 동일 결론** — 강한 합의.

**공통 제안**: `bb_pos` 등 feature는 Oracle 입력으로 활용하되, **variant 수준의 BollRev는 V3 영역** 또는 Phase 6 별도 엔진 승격 경로로 분리.

**Claude/Codex 추가 제안**: BollRev 재요청 발생 시 Charter 재개정 절차 거칠 것. Phase 3 전 `bb_pos + bb_width + dist_to_mid + rsi14` feature ablation 1회 (low-vol/range regime uplift 검증).

---

## Topic 2: Ablation 파일 구조 — 판정 **PARTIAL (A vs D)**

### 공통 합의 (3/3)
- **B 탈락**: Oracle 골격 선구현은 미확정 파라미터 4+ 개가 교란 변수로 유입. Rule 2 순수 검증 명제 오염.
- **C 탈락**: v2.py 직접 수정은 "live 수술 금지" 결정 위반.

### 핵심 이견: A vs D

**A (포크) — Claude opus + Gemini**:
- 장점: 변수 분리 정확도 최고. 문언 위배지만 **입법 취지(live 환경 보호)는 충족**. 외부 종속성 없음.
- 단점: v2.py 변경이 자동 반영 안 됨 → 포크 시점 commit hash 고정 필요. archive 규칙 미정의 시 파일 영구 잔존.

**D (import + subclass/no-op override) — Codex**:
- 장점: **v2.py 무수정 + 동일 코드경로 재사용**. 공수 6-10h / 리스크 2 (A는 8-12h / 리스크 3). ML의 "isolated experiment harness" 정석 패턴. 파일명 `oracle_rule2_ablation.py`로 두면 Charter 문언 일치.
- 단점: `LOG_PATH / STATE_PATH / DASH_PORT` variant별 재바인딩 필수. predictor 주입 방식은 smoke test로 먼저 잠궈야 함.

### 쟁점 요약
- **코드 중복 vs 결합도**: A는 v2.py와 decoupled (v2.py 수정 시 ablation도 재작업 위험), D는 coupled (v2.py 수정이 ablation에 즉시 영향)
- **"Rule 2만" 검증 순수성**: A는 포크로 인한 drift 가능성, D는 동일 경로라 drift 불가
- **Charter 문언 vs 입법 취지**: A는 "oracle.py" 명칭 위배이나 입법 취지 충족, D는 파일명으로 명칭 만족 가능
- **공수/리스크**: Codex 정량 D(6-10h/2) < A(8-12h/3)

---

## 수렴 판정

| Topic | 판정 | 근거 |
|-------|------|------|
| T1 BollRev | **AGREE (제외)** | 3엔진 독립 추론 동일 결론 + 공통 후속 경로(feature reuse) 제안 |
| T2 Ablation | **PARTIAL (A 2 / D 1)** | 핵심 쟁점 명확 — Round 2에서 A vs D 집중 논의 필요 |

---

## Round 2 집중 쟁점 (Topic 2만)

**Q1**: v2.py 런타임 동작 재현성 — 포크(A)는 미래 v2.py 버그 픽스가 반영 안 됨. Ablation 48h 동안 v2.py 수정 가능성 낮으나, 포크 시점 commit hash 고정만으로 충분한가?

**Q2**: D의 subclass 주입 — `V2Engine`이 predictor를 외부 주입 가능한 구조인가? (현재 v2.py:604 `class V2Engine`, predictor는 내부에서 `self.predictors` dict로 생성). 주입을 위해 `V2Engine.__init__`에 predictor_factory 파라미터를 추가해야 한다면 v2.py 수정 필요 → D의 장점이 무너짐.

**Q3**: 만약 D가 v2.py 수정 없이 불가능하면 A가 유일한 실용 안. Codex가 구체 구현 경로를 제시할 수 있는가?

**Q4**: "D의 파일명만 `oracle_rule2_ablation.py`로 변경" 타협안은 Charter 문언 만족 + A의 포크 방식을 유지한 하이브리드 가능한가?

---

## Evidence

- 참여자 응답: `round-1/claude_opus.md`, `round-1/codex.md`, `round-1/gemini.md`
- Raw logs: `round-1/_codex_raw.log` (3126 LOC 포함 reasoning), `round-1/_gemini_raw.log`
- 맥락: `context.md`, `phase1-charter.md`, `phase2-component-map.md`, `48h-ablation-plan.md`
