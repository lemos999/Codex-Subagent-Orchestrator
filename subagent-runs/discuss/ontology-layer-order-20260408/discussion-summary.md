# Discussion Summary — Ontology Layer Order

**Date**: 2026-04-08
**Topic**: World Ontology Layer 순서: Physics와 Space-Time의 관계
**Rounds**: 2
**Result**: AGREE (3:0)

## 참가자
- Rex Baek (Claude Opus) — 구현/아키텍처
- Teo Kang (Codex GPT-5.4) — 게임 설계
- Elara Voss (Gemini 2.5 Pro) — 존재론/철학

## Round 1
- Rex: 안 B (교환). 데이터 의존성 — 데몬이 시공간 데이터를 읽으므로 시공간이 먼저.
- Teo: 제3안. 존재론은 B, 데몬은 "횡단 실행자". ECS 패턴 근거.
- Elara: 안 A (유지). 법칙이 장소를 규정. 능동적 동인이 수동적 연장보다 근본적.
- 판정: PARTIAL (2:1)

## Round 2 (가이드: 세계관 완성과 확장성)
- Rex: 횡단 실행자형이 OCP 만족. 확장 시 기존 구조 수정 불필요.
- Teo: 횡단형. 시스템 추가 = 상태·규칙·입출력 설계 + 데몬 구독. 데몬 스키마 = 메타 실행 계약.
- Elara: 안 A + 제3안 통합. 데몬 = 데미우르고스. 법칙의 선행성 + 실행의 횡단성 동시 확보.
- 판정: AGREE (3:0)

## 합의안

Substrate(데이터 레이어) + Cross-cutting Executors(횡단 실행자) + Daemon Registry(메타 계약)

- Layer = 데이터(What), Executor = 프로세스(How), Registry = 계약(Contract)
- Layer 1은 Substrate (지형, 시계, 권역, 영지, 시설)
- 데몬은 레이어에 속하지 않고 레이어 간을 관통하는 실행자
- 새 시스템 추가 = Layer에 데이터 추가 + Executor 구독 선언
- 5번째 데몬 추가 = Registry 항목 1개 추가
