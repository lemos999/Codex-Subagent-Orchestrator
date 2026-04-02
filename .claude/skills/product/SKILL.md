---
name: product
description: "소프트웨어 제품 개발 오케스트레이터 — 기획→구현→검증→배포→운영 전체 수명주기 자동화"
---

# /product — Software Product Development

> 실행 전 워크스페이스 루트의 `project-status/current.md`를 읽어 현재 프로젝트 상태를 파악한다.
> 실행 전 WKI 인덱싱: `node workspace-knowledge-index/dist/index.js index`

소프트웨어 제품의 전체 수명주기를 3개 AI 엔진(Claude+Codex+Gemini)으로 자동화하는 오케스트레이터.

## 인수 없이 호출 시 — 도움말 출력

```
/product — 소프트웨어 제품 개발 오케스트레이터

사용법:
  /product <요청>

■ 전체 공정 시작
  /product 새 프로젝트를 만들고 싶다     → Stage 1(Design)부터
  /product 커뮤니티 웹사이트 개발         → 유형 자동 감지
  /product CLI 도구 개발                  → 엣지 케이스 자동 적용

■ 특정 Stage부터
  /product Stage 4부터                    → 기존 설계 기반 구현
  /product Stage 7부터                    → 배포된 서비스 베타 검증

■ 특정 분야만
  /product 보안 감사                      → Security Auditor 실행
  /product DB 설계                        → Data Architect + Reviewer
  /product UX 리뷰                        → UX Reviewer 실행

■ 엔진 역할
  Codex (GPT): 플래너 + 코드 생성 (stdout 산출물, 파일 수정은 Claude)
  Claude: 아키텍트 + 검증자
  Gemini: UX 감사자 + 사용자 관점

■ 8단계 공정
  Stage 0: Preflight  → 엔진/환경/의존성 확인 (자동)
  Stage 1: Design     → /design 호출
  Stage 2: Plan       → 사용자가 Codex 앱 plan mode로 수동 수립
  Stage 3: Foundation → DB + Auth + 배포 기반
  Stage 4: Implement  → 기능 구현 (BIBLE § 확인 후 착수)
  Stage 5: Verify     → 테스트 + 보안 + UX (Settlement Record)
  Stage 6: Deploy     → 스테이징 → 프로덕션
  Stage 7: Validate   → 베타 + 피드백
  Stage 8: Iterate    → 피드백 반영 → Stage 4 순환

■ Solo Lite (1인 개발, 컴포넌트 5개 이하)
  4단계: Design+Plan → Build → Verify → Release
  6 페르소나 / 3 게이트

■ 게이트 (사람 승인)
  G1: 설계 승인  G2: 플랜 승인  G3: 기반 확인
  G4: 리뷰 통과  G5: 배포 승인  G6: 베타 결정

■ 참조
  프레임워크: skills/product-development/SKILL.md
  설계 스킬: skills/design-director/SKILL.md
  개발 원칙: Projects/DEVELOPMENT-BIBLE.md
```

## Entry Protocol

1. Strip the `/product` prefix
2. 프레임워크 로드: `skills/product-development/SKILL.md`
3. 요청 분석 → Stage 분기 또는 분야별 실행

## 실행 방식

### 전체 공정
Stage 0~8 순차 진행. 각 게이트에서 사용자 승인. Solo Lite는 4단계.

### Stage별 하위 스킬 호출
- Stage 1: `/design` 호출
- Stage 0: Preflight (자동 — 엔진/환경 확인)
- Stage 2: 사용자 수동 (Codex 앱 plan mode)
- Stage 3~5: `/submix` (분야별 페르소나 자동 배정)
- Stage 6: CI/CD 자동 + 수동 승인
- Stage 7: 수동 + AI 분석
- Stage 8: Stage 4로 순환

### 분야별 단독 실행
요청이 특정 분야면 해당 페르소나만 실행 (전체 공정 불필요).

## 핵심 참조

| 파일 | 용도 |
|------|------|
| `skills/product-development/SKILL.md` | 전체 공정 + 페르소나 매트릭스 |
| `skills/design-director/SKILL.md` | Stage 1 (기획/설계) |
| `Projects/DEVELOPMENT-BIBLE.md` | 구현 원칙 29개 섹션 |
| `.claude/skills/submix/SKILL.md` | 멀티엔진 실행 |

## 불변 원칙

1. DEVELOPMENT-BIBLE이 구현 기준
2. 게이트 미통과 → 다음 Stage 금지
3. 교차 검증 필수 — 최소 2엔진
4. 베타 먼저 — 최소 기반에서 빠르게 검증
5. Codex 결과는 반드시 `git diff` 검증
6. 깊이 > 길이 — 핵심 판단, 장문 억제
7. Evidence 필수

## Production Engineering Discipline

The standard is not "does it run?" but **"is it production-ready?"** Every worker and every Stage operates under this bar.

### Pre-Work: Clean the Foundation

- When building on existing code, **remove dead code from files >300 LOC in a separate commit first**. Stacking features on tech debt means returning from Stage 5 (Verify).
- Within each Stage, break implementation into **phases of ≤5 files**. Complete a phase → verify → approve → next phase. Stages are already phased, so resist the temptation to do everything at once within a Stage.

### Quality: The Gate Is the Verification

- DEVELOPMENT-BIBLE compliance is not optional. Architectural flaws, duplicated state, inconsistent patterns — **code that a senior reviewer would reject does not pass the Gate**.
- Run `tsc --noEmit` + `eslint` before reporting any implementation complete. Gate G4 (review pass) presupposes this verification. If no type-checker is configured, state that fact in Stage 0 (Preflight).
- Codex-generated code gets no exemption — always `git diff` + type/lint verify.

### Context: Memory Fades Across Stages

- On Stage transitions or after 10+ messages, **re-read target files before editing**. Do not assume a file read in Stage 3 is unchanged in Stage 4.
- Chunk-read files >500 LOC. Re-run searches with narrower scope when results look suspiciously sparse.
- Distribute implementations across **parallel workers** when >5 files — `/submix` handles this automatically, but never overload a single worker.

### Edit Safety: No Silent Failures in Shipped Code

- **Re-read after every edit** to confirm it applied. Verification read every 3 edits. "I thought the edit landed" is a production incident.
- When renaming, search 6 patterns separately: direct calls, type references, string literals, dynamic imports, re-exports, tests/mocks. Missing even one means a runtime crash.

### Breakthrough Protocol: When a Stage Is Stuck

In production software, "this can't be done" is the most expensive sentence. The moment it appears is where real engineering begins.

- **Gate failure is data**: If a Gate fails, record **"This Gate tells us:"** instead of "FAIL." The failing check points precisely to the weakness in the design.
- **Stage repetition is a limit signal**: If the same Stage fails 3+ times, do not retry the implementation — **re-examine the previous Stage's design**. Repeated failures in Stage 4 mean suspecting Stage 1's design. Shift one level up.
- **Invert your tech-choice premises**: If "this library can't do it" appears 3 times, list 3 premises behind the library choice and try the opposite of each. The framework may be the constraint.
- **"Impossible" is a forbidden word**: In production there is no impossible — only **"not yet solved with this architecture/stack/approach."** Propose the next dimension and execute.
- **Partial deploy beats no deploy**: Waiting for 100% completion and never reaching Stage 6 is worse than beta-deploying core features only — this aligns with invariant #4 (beta first).
