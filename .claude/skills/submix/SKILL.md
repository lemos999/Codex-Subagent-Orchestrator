---
name: submix
description: "[폐기됨] /discuss --quick 또는 /harness로 통합. 3엔진 토론은 /discuss, 3엔진 구현은 /harness 사용."
---

# /submix — 폐기됨

> **이 스킬은 `/discuss`와 `/harness`로 통합되었습니다.**

## 마이그레이션 가이드

| 기존 사용법 | 새 사용법 |
|------------|----------|
| `/submix 이 설계 괜찮은가?` (의견 수집) | `/discuss --quick 이 설계 괜찮은가?` |
| `/submix 이 문제를 토론해줘` (토론) | `/discuss 이 문제를 토론해줘` |
| `/submix 구현해줘` (3엔진 구현) | `/harness 구현해줘` |

## 왜 통합했나?

- `/submix` 토론 기능 → `/discuss`가 더 강력 (수렴 감지, 모더레이터, WKI, 퀵 모드)
- `/submix` 구현 기능 → `/harness`가 더 강력 (이벤트 추적, 세션 관리, 에이전트 레지스트리)
- 3개 스킬이면 충분: `/sub` (빠른 위임) + `/discuss` (토론) + `/harness` (실행+추적)
