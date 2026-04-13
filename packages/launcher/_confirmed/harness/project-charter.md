# Launcher Harness Mode — Project Charter

> 최종 갱신: 2026-04-13
> 버전: v2 (하네스식 검증 반영)

## Primary Outcome

워커 실행의 블랙박스를 투명한 구조화된 이벤트 스트림으로 전환하고, 에이전트 정의와 태스크를 분리하여 오케스트레이션의 관측 가능성·재사용성을 극대화한다.

## Operating Loop

- **마이크로**: 워커 spawn → stdout/stderr 청크 수신 → 엔진별 파서로 이벤트 추출(도구/메시지/상태) → 세션 상태 업데이트 → 이벤트 방출
- **미들**: spec 로드 → 에이전트 레지스트리 해석(system + task 분리) → 스테이지 실행 → 세션별 이벤트 수집 → manifest + 이벤트 로그 기록
- **매크로**: 이벤트 로그 축적 → 워커별 도구 사용 패턴 분석 → 에이전트 레지스트리 최적화 → 신뢰도 레지스트리 연동

## Baseline Expectations

### 포함
1. 기존 spec JSON으로 실행하면 현재와 동일하게 작동 (하위 호환)
2. CTS hook 파이프라인 간섭 없음 (레이어 분리 검증 완료)
3. WKI 컨텍스트 주입, AGENTS.md, 스킬 등 기존 인프라 그대로 사용
4. TypeScript, npm workspaces 모노레포 구조 유지
5. 추가 API 비용 없음 (로컬 파싱만)
6. manifest 포맷 하위 호환 (필드 추가만, 삭제/변경 없음)

### 의도적 제외
- 실행 중 조향 — CLI `--print` 모드와 근본 충돌
- `agent.thinking` 이벤트 — CLI가 thinking을 출력하지 않음
- `span.*` 이벤트 — CLI가 내부 모델 호출 시점을 노출하지 않음
- Claude 워커의 정확한 토큰 수 — `--print`가 usage 미출력, duration으로 대체
- GUI/웹 대시보드

### 설계 제약
- 이벤트 시스템은 CLI stdout에서 파싱 가능한 이벤트만 지원
- 도구 가시성은 best-effort, 엔진별 파서 플러그인 구조
- 토큰 추적: Codex = 정확(JSON 이벤트), Claude/Gemini = duration만 정확

## Differentiation Thesis

> "서브에이전트 오케스트레이터인데, Managed Agents 하네스 패턴의 이벤트 시스템·세션 상태·에이전트 레지스트리(system/task 분리)를 로컬에 이식했기 때문에, 클라우드 비용 없이 워커 실행의 완전한 관측 가능성과 재사용성을 확보한다."

## Target Audience

- 대상: 이 워크스페이스의 유일한 사용자 (1인)
- 환경: Windows 11 + bash, Claude Code CLI, packages/launcher
- 허용 복잡도: 중간 — `--harness` 플래그 하나로 활성화
- 사용 빈도: spec 실행 시마다 (일 수회~수십회)
- 제약: CTS hook과 공존, 기존 spec 무수정 실행 필수
