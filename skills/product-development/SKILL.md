# Product Development — 소프트웨어 제품 개발 오케스트레이터

> **목적:** 소프트웨어 제품의 전체 수명주기(기획→구현→검증→배포→운영)를 3개 AI 엔진으로 자동화.
> **범위:** 웹 서비스, API, CLI, 모바일 앱, 데스크톱 앱, 유틸리티 — 모든 소프트웨어 유형.
> **원칙:** DEVELOPMENT-BIBLE.md가 구현 기준. `/design`이 기획 기준. `/submix`가 실행 기준.

---

## 엔진별 역할 (고정)

| 엔진 | 핵심 역할 | 근거 |
|------|----------|------|
| **Codex (GPT)** | 플래너 + 구현자 | plan mode, 코드 생성 속도, 멀티 파일 |
| **Claude** | 아키텍트 + 검증자 | 구조 설계, 정밀 추론, 보안 판단 |
| **Gemini** | UX 감사자 + 문서 분석 | 사용자 관점, 긴 컨텍스트, 접근성 |

---

## 개발 공정 8단계 (Stage)

```
Stage 1: Design      — /design으로 기획/설계
Stage 2: Plan        — Codex가 구현 계획 수립
Stage 3: Foundation  — 인프라 기반 구축 (DB, Auth, 배포)
Stage 4: Implement   — 기능 구현
Stage 5: Verify      — 테스트 + 코드 리뷰 + 보안 감사
Stage 6: Deploy      — 스테이징 → 프로덕션
Stage 7: Validate    — 베타 + 사용자 피드백 + UX 검증
Stage 8: Iterate     — 피드백 반영 → Stage 4로 순환
```

### 게이트 (사람 승인 필요)

| 게이트 | 위치 | 승인 내용 |
|--------|------|----------|
| G1: Design Approval | Stage 1 → 2 | Charter + 와이어프레임 확정 |
| G2: Plan Approval | Stage 2 → 3 | 구현 계획 + 태스크 목록 확정 |
| G3: Foundation Check | Stage 3 → 4 | DB+Auth+배포 기본 동작 확인 |
| G4: Review Pass | Stage 5 → 6 | 코드 리뷰 + 테스트 + 보안 통과 |
| G5: Deploy Approval | Stage 6 prod | 프로덕션 배포 승인 |
| G6: Beta Decision | Stage 7 → 8 | 다음 이터레이션 방향 결정 |

게이트 미통과 → 해당 Stage 반복. 다음 Stage 진행 금지.

---

## 분야별 에이전트 페르소나

### 기획/설계 분야

| 분야 | 페르소나 | 엔진 | BIBLE § | 역할 |
|------|---------|------|---------|------|
| 프로젝트 기획 | Design Director | Claude (opus) | — | `/design` Phase 0~5 실행 |
| 요구사항 분석 | Requirements Analyst | Gemini (pro) | — | 사용자 관점 요구사항 검증 |

### 계획 수립 분야

| 분야 | 페르소나 | 엔진 | BIBLE § | 역할 |
|------|---------|------|---------|------|
| 구현 계획 | Implementation Planner | Codex (plan) | §12 | 태스크 분해, 의존성 정렬, 일정 추정 |
| 아키텍처 설계 | System Architect | Claude (opus) | §1, §2, §24 | 기술 스택, 디렉터리 구조, 12-Factor |
| 아키텍처 리뷰 | Architecture Reviewer | Gemini (pro) | — | 확장성/UX 관점 아키텍처 검증 |

### 데이터 분야

| 분야 | 페르소나 | 엔진 | BIBLE § | 역할 |
|------|---------|------|---------|------|
| DB 스키마 설계 | Data Architect | Codex | §3 | Prisma 스키마, 인덱스, 관계 |
| DB 리뷰 | Data Reviewer | Claude (sonnet) | §3, §26 | 정규화, 성능, 보안 검증 |
| 마이그레이션 | Migration Engineer | Codex | §3 | 마이그레이션 스크립트, 롤백 |

### API 분야

| 분야 | 페르소나 | 엔진 | BIBLE § | 역할 |
|------|---------|------|---------|------|
| API 설계 | API Designer | Claude (sonnet) | §4, §22 | 엔드포인트 구조, 버전관리 |
| API 구현 | API Builder | Codex | §4 | 핸들러 코드 생성 |
| API 테스트 | API Tester | Codex | §10 | 엔드포인트별 테스트 코드 |

### 인증/보안 분야

| 분야 | 페르소나 | 엔진 | BIBLE § | 역할 |
|------|---------|------|---------|------|
| 인증 설계 | Auth Architect | Claude (opus) | §5 | 세션, JWT, OAuth 설계 |
| 보안 감사 | Security Auditor | Claude (opus) | §6, §7 | 입력 검증, OWASP, 취약점 |
| 권한 설계 | Permission Designer | Claude (sonnet) | §21 | RBAC, 권한 경계 |

### 프론트엔드 분야

| 분야 | 페르소나 | 엔진 | BIBLE § | 역할 |
|------|---------|------|---------|------|
| UI 구현 | Frontend Builder | Codex | §15 | 컴포넌트, 페이지, 스타일 |
| UX 리뷰 | UX Reviewer | Gemini (pro) | §15 | 사용자 흐름, 접근성, 모바일 |
| 상태관리 | State Architect | Claude (sonnet) | §15 | React Query, Zustand, URL 상태 |

### 테스트 분야

| 분야 | 페르소나 | 엔진 | BIBLE § | 역할 |
|------|---------|------|---------|------|
| 단위 테스트 | Unit Tester | Codex | §10 | 함수/컴포넌트 단위 테스트 |
| 통합 테스트 | Integration Tester | Codex | §10 | DB/API 통합 테스트 |
| E2E 테스트 | E2E Tester | Codex | §10 | 사용자 흐름 E2E |
| 테스트 리뷰 | Test Reviewer | Claude (sonnet) | §10 | 테스트 커버리지, 엣지 케이스 |

### 인프라/배포 분야

| 분야 | 페르소나 | 엔진 | BIBLE § | 역할 |
|------|---------|------|---------|------|
| CI/CD 설정 | DevOps Engineer | Codex | §18 | GitHub Actions, Vercel, 파이프라인 |
| 인프라 설계 | Infra Architect | Claude (sonnet) | §13, §24 | 환경 분리, 스케일링, 12-Factor |
| 배포 검증 | Deploy Verifier | Gemini (flash) | §28 | 런칭 체크리스트 대조 |

### 운영/관측 분야

| 분야 | 페르소나 | 엔진 | BIBLE § | 역할 |
|------|---------|------|---------|------|
| 로깅/모니터링 | Observability Engineer | Claude (sonnet) | §17 | 구조화 로그, 메트릭, 알림 |
| 에러 처리 | Error Handler | Codex | §11 | 에러 바운더리, 복구 로직 |
| 성능 최적화 | Performance Tuner | Codex → Claude 리뷰 | §16, §26 | 캐싱, 쿼리 최적화, 번들 |

### 콘텐츠/정책 분야

| 분야 | 페르소나 | 엔진 | BIBLE § | 역할 |
|------|---------|------|---------|------|
| UGC 관리 | Content Moderator | Claude (sonnet) | §27 | 모더레이션, 신고/제재 |
| 정책 문서 | Policy Writer | Claude (opus) | §28 | 이용약관, 개인정보처리방침 |
| 정책 UX 리뷰 | Policy UX Reviewer | Gemini (pro) | — | 사용자 관점 정책 검토 |

---

## Stage별 상세

### Stage 1: Design (기획/설계)

**실행:** `/design <프로젝트 설명>`
**담당:** Claude (opus) — Design Director
**산출물:** `_confirmed/` 설계 문서 전체
**게이트 G1:** Charter + 와이어프레임 + 기술 스택 확정

이 Stage는 `/design` 스킬에 완전히 위임. `/design`의 Phase 0~5를 실행.

### Stage 2: Plan (구현 계획)

**실행:** Codex plan mode
**담당:**
- Implementation Planner (Codex) — 태스크 분해
- System Architect (Claude) — 아키텍처 검증
- Architecture Reviewer (Gemini) — UX/확장성 검증

**절차:**
1. Codex가 `_confirmed/` + BIBLE을 읽고 구현 계획 수립
2. Claude가 아키텍처 검증 (디렉터리 구조, 모듈 분리, 의존성)
3. Gemini가 사용자 관점 검증 (UX 흐름이 설계와 정합하는가)

**산출물:** `docs/IMPLEMENTATION-PLAN.md`
- 태스크 목록 (의존성 순)
- 파일별 생성/수정 계획
- 예상 구현 순서

**게이트 G2:** 구현 계획 승인

### Stage 3: Foundation (기반 구축)

**실행:** `/submix`
**담당:**
- Data Architect (Codex) — DB 스키마 + migration + seed
- Auth Architect (Claude) — 인증 설계 + 보안 검증
- DevOps Engineer (Codex) — CI/CD 초기 설정
- Infra Architect (Claude) — 환경 분리, 12-Factor 검증

**절차:**
1. DB 스키마 → migration → seed (Codex 구현, Claude 리뷰)
2. 인증 구조 (Claude 설계, Codex 구현)
3. 배포 파이프라인 초안 (Codex 설정, Claude 검증)
4. 기본 에러 로깅 설정

**산출물:** 동작하는 기반 인프라 (DB + Auth + 배포)
**게이트 G3:** `npm run build` + 로그인 + DB 연결 확인

### Stage 4: Implement (기능 구현)

**실행:** `/submix` (반복)
**담당:** 분야별 페르소나 자동 배정

**절차 (기능 단위 반복):**
1. Codex가 기능 코드 생성 (Frontend Builder / API Builder)
2. Claude가 코드 리뷰 (해당 분야 Reviewer)
3. Codex가 테스트 코드 생성 (Unit/Integration Tester)
4. FAIL 시 Codex가 수정 → Claude 재리뷰

**기능 단위:** Stage 2의 태스크 목록 순서대로 진행
**산출물:** 기능별 코드 + 테스트

### Stage 5: Verify (검증)

**실행:** `/submix`
**담당:**
- Security Auditor (Claude opus) — 보안 감사
- Test Reviewer (Claude sonnet) — 테스트 커버리지 검증
- UX Reviewer (Gemini) — 사용자 관점 전체 검증
- Deploy Verifier (Gemini) — BIBLE §28 런칭 체크리스트 대조

**절차:**
1. Claude 보안 감사 (OWASP Top 10, 입력 검증, 권한)
2. Claude 테스트 리뷰 (커버리지, 엣지 케이스)
3. Gemini UX 리뷰 (접근성, 모바일, 사용자 흐름)
4. Gemini 런칭 체크리스트 대조

**산출물:** 검증 보고서
**게이트 G4:** 보안 PASS + 테스트 PASS + UX PASS

### Stage 6: Deploy (배포)

**실행:** CI/CD 자동 + 수동 승인
**담당:**
- DevOps Engineer (Codex) — 배포 스크립트
- Infra Architect (Claude) — 환경 검증

**절차:**
1. 스테이징 배포 (자동)
2. 스테이징 검증 (자동 테스트 + 수동 확인)
3. 프로덕션 배포 (수동 승인)

**게이트 G5:** 프로덕션 배포 승인

### Stage 7: Validate (검증/베타)

**실행:** 수동 + AI 분석
**담당:**
- UX Reviewer (Gemini) — 사용자 피드백 분석
- Content Moderator (Claude) — 운영 이슈 분석
- Performance Tuner (Codex → Claude) — 성능 이슈

**절차:**
1. 소규모 베타 운영
2. Gemini가 사용자 피드백 분석
3. Claude가 운영/보안 이슈 분석
4. 우선순위 재판단

**산출물:** 베타 보고서 + 다음 이터레이션 태스크 목록
**게이트 G6:** 다음 이터레이션 방향 결정 (또는 정식 오픈)

### Stage 8: Iterate (반복)

Stage 7 결과를 기반으로 Stage 4 → 5 → 6 → 7 순환.
정식 오픈 결정 시 순환 종료.

---

## 소프트웨어 유형별 엣지 케이스

범용 공정(Stage 1~8)은 동일. 유형별로 **강조/생략 항목**만 다름:

### 웹 서비스 (커뮤니티, SaaS 등)

| Stage | 강조 | 생략 가능 |
|-------|------|----------|
| 3 Foundation | OAuth, 파일 업로드, CDN | — |
| 4 Implement | SSR/SSG, 반응형, SEO | — |
| 5 Verify | UGC 모더레이션 (§27), 접근성 | — |
| 7 Validate | 리텐션, 온보딩 흐름 | — |

BIBLE 추가 참조: §9 (WebSocket), §20 (파일 업로드), §27 (UGC)

### API 서비스

| Stage | 강조 | 생략 가능 |
|-------|------|----------|
| 3 Foundation | API 문서화 (OpenAPI), 버전관리 | 프론트엔드 |
| 4 Implement | 엔드포인트, 미들웨어, 직렬화 | UI 컴포넌트 |
| 5 Verify | API 계약 테스트, 부하 테스트 | UX 리뷰 |

BIBLE 추가 참조: §4 (API), §22 (버전관리)

### CLI / 유틸리티

| Stage | 강조 | 생략 가능 |
|-------|------|----------|
| 2 Plan | 명령어 구조, 옵션 파서 | 와이어프레임 |
| 3 Foundation | 패키지 배포 (npm publish) | DB, Auth, CDN |
| 5 Verify | CLI 사용성 테스트 | UX 리뷰, 접근성 |

BIBLE 추가 참조: §23 (CLI 확장)

### 모바일 앱 (React Native / Flutter)

| Stage | 강조 | 생략 가능 |
|-------|------|----------|
| 3 Foundation | 앱 스토어 설정, 푸시 알림 | 서버 SSR |
| 4 Implement | 네이티브 UI, 오프라인 지원 | SEO |
| 6 Deploy | 앱 스토어 심사, OTA 업데이트 | CDN |

BIBLE 추가 참조: §23 (모바일), §5 (JWT + refresh token)

### 데스크톱 앱 (Electron / Tauri)

| Stage | 강조 | 생략 가능 |
|-------|------|----------|
| 3 Foundation | IPC, 로컬 DB (SQLite) | 서버 Auth, CDN |
| 4 Implement | 시스템 트레이, 파일 시스템 | API 엔드포인트 |
| 6 Deploy | 자동 업데이트, 코드 서명 | CI/CD 웹 배포 |

BIBLE 추가 참조: §23 (데스크톱)

---

## 실행 방법

### 전체 공정 시작
```
/product <프로젝트 설명>
```
→ Stage 1(Design)부터 순차 진행. 각 게이트에서 사용자 승인.

### 특정 Stage부터 시작
```
/product Stage 4부터    → 기존 설계 기반으로 구현부터
/product Stage 7부터    → 이미 배포된 서비스의 베타 검증
```

### 특정 분야만 실행
```
/product 보안 감사      → Security Auditor (Claude) 단독 실행
/product DB 설계        → Data Architect (Codex) + Data Reviewer (Claude)
/product UX 리뷰       → UX Reviewer (Gemini) 단독 실행
```

---

## 에이전트 자동 배정 규칙

사용자가 태스크를 주면, 오케스트레이터(Claude)가 자동으로:

1. **분야 식별** — 태스크가 어느 분야에 해당하는지 (DB? API? 프론트엔드?)
2. **페르소나 배정** — 해당 분야의 에이전트 페르소나 선택
3. **엔진 배정** — 페르소나에 매핑된 엔진으로 실행
4. **리뷰어 배정** — 구현자와 다른 엔진의 리뷰어 자동 배정
5. **교차 검증** — 필요 시 3엔진 교차 검증 (/submix)

### 핵심 제약

- **파일 수정은 반드시 Claude** — Codex/Gemini는 stdout만 반환
- **보안 판단은 반드시 Claude** — 인증, 권한, 입력 검증
- **사용자 관점은 반드시 Gemini** — UX, 접근성, 사용자 피드백
- **코드 대량 생성은 Codex 우선** — 속도 + 패턴 기반
- **Orchestrator는 항상 Claude** — 전체 공정 감독

---

## 품질 원칙 — 실험과 논문에서 얻은 교훈

### 깊이가 길이보다 중요하다 (DTR 논문)

> 출처: "Think Deep, Not Just Long" (arXiv:2602.13517, Google & UVa, 2026)

- 토큰 길이와 정확도: **r = -0.594** (길수록 틀림)
- 적용: 에이전트에게 "길게 설명"이 아닌 **"핵심 판단에 집중"** 요구
- 모든 에이전트에 `max_response_lines` 제한
- 리뷰어/워치독은 "발견 N건 + Verdict"만 반환. 장문 금지

### 파이프라인은 복잡계다 (WKI 양자화 교훈)

> 출처: WKI 양자화 실험 교훈록 (2026-03-23)

- 이미 최적화된 시스템에 추가 조정 → 기존 균형 파괴 (교훈 8)
- 나쁜 입력을 후처리로 보정 불가 (교훈 6)
- 적용:
  - Stage 4 중간에 아키텍처 변경 금지. 아키텍처는 Stage 2에서 확정
  - 문제 발견 시 **해당 계층에서 수정** (보안→보안, UX→UI)
  - 복수 계층 동시 수정 금지. 한 계층 → 테스트 → 다음

### 도메인 불일치는 역효과 (WKI cross-encoder 교훈)

> 출처: WKI cross-encoder 실험 — ms-marco가 코드 도메인에서 역효과 (교훈 5)

- 적용: 에이전트 페르소나는 **분야 전문성 기반** 배정
- 보안 → Security Auditor (Claude, OWASP), UX → UX Reviewer (Gemini, 사용자), DB → Data Reviewer (Claude, 정규화)
- "아무 AI나 리뷰" → 도메인 불일치로 올바른 판단 무너뜨림

### 일관성을 깨지 마라 (WKI 임베딩 공간 교훈)

> 출처: WKI 양자화 교훈 1 — dtype 불일치 시 정확도 급락

- 적용: 설계 문서-코드-테스트의 **용어/구조 공간 일치**
- `_confirmed/` 컴포넌트명 = 코드 모듈명 = 테스트 대상명
- Stage 1 아키텍처를 Stage 4에서 임의 변경 → 설계-구현 공간 불일치
- 변경 시 Stage 1로 돌아가 설계 문서부터 수정

### 지능형 위임 (Intelligent AI Delegation 논문)

> 출처: "Intelligent AI Delegation" (arXiv:2602.11865, Google DeepMind, 2026)

1. **Adaptive Coordination** — 합의 빠르면 조기 종료. 만장일치 PASS → 추가 리뷰 불필요
2. **Verifiable Completion** — 모든 Stage에 Settlement Record. "누가, 무엇을, 어떤 기준으로"
3. **Privilege Attenuation** — 외부 엔진 최소 권한. 리뷰어 read-only, 구현자 지정 파일만
4. **Trust & Reputation** — 에이전트 Trust Score 누적. 고신뢰→중요 작업, 저신뢰→watchdog 추가
5. **Human-in-the-Loop** — 6개 게이트 사람 승인. 완전 자동은 Stage 내부만

### 출력 품질 자동 감지

> 참조: `packages/launcher/src/workers/output-quality.ts`

- **반복 감지**: 동일 문장/구조 반복 → 추론 실패
- **양비론 감지**: "한편으로는 A, 다른 한편으로는 B" → 결정 회피
- **자기참조 감지**: "앞서 언급했듯이" → 새 정보 없음
- 감지 시: 출력 폐기 → 다른 엔진 재실행 또는 프롬프트 재구성

---

## 불변 원칙

1. **DEVELOPMENT-BIBLE이 구현 기준** — 모든 코드는 BIBLE 원칙 준수
2. **게이트 미통과 시 다음 Stage 금지**
3. **교차 검증 필수** — 최소 2엔진
4. **Evidence 필수** — 모든 Stage 산출물 기록
5. **베타 먼저** — 최소 기반에서 빠르게 검증
6. **깊이 > 길이** — 핵심 판단 요구, 장문 억제
7. **도메인 일치** — 페르소나는 분야 전문성 기반
8. **일관성 보존** — 설계-구현-테스트 공간 일치
9. **한 계층씩** — 복수 계층 동시 수정 금지
