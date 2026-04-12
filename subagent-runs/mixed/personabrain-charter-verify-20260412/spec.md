# PersonaBrain SNN Charter 12에이전트 검증 — 실행 계획

## 에이전트 배정 (12명)

| # | 페르소나 | 권역 | 검증 관점 | 엔진 |
|---|---------|------|----------|------|
| 1 | Mira Chen | 미배정 | 신경과학 정확성 — LIF/STDP/E-I balance/refractory가 생물학적으로 올바른가 | Claude opus |
| 2 | Elara Voss | Gemini | 철학 정합 — 근본 정의(비밀=두려움, 거짓말=연속체, 꿈=미지)가 아키텍처에 반영되었는가 | Claude opus |
| 3 | Rex Baek | Claude | 시스템 엔지니어링 — 10ms SLA, 메모리 64GB, 배치 처리가 실현 가능한가 | Codex gpt-5.4 |
| 4 | Teo Kang | Codex | 계산 최적화 — moment closure, 캐시 히트율, SIMD 벡터화 수치가 정확한가 | Codex gpt-5.4 |
| 5 | Kael Arden | Gemini | 아키텍처 감사 — Layer 0/1/2 간 결합도, 인터페이스 누락, 경합 조건 | Claude sonnet |
| 6 | Sora Lee | Claude | 학습 파이프라인 — Phase 0~3이 논리적으로 연결되는가, 수렴 조건이 명확한가 | Gemini pro |
| 7 | Dana Jeong | Claude | 행동 회로 — 10가지 행동의 SNN 회로 매핑이 일관되는가, 빠진 연결이 있는가 | Claude opus |
| 8 | Ivy Sato | Codex | 게임 밸런스 — Mitotype 격차, 성장 속도, 에너지 모델이 공평한가 | Gemini pro |
| 9 | Sia Yun | Gemini | 에너지 모델 — 4단계 강도, 미토콘드리아, 영역별 취약성의 내적 일관성 | Claude sonnet |
| 10 | Dr. Yuna Kang (신규) | Claude | 미토콘드리아/유전학 — Mitotype, energy_pool, 노화 모델의 생물학적 정확성 | Claude opus |
| 11 | Riel Voss (신규) | Gemini | 꿈/수면 — NREM/REM 위상, 3이론 혼합, 수면 트리거의 신경과학적 정확성 | Gemini pro |
| 12 | Jin Harada (신규) | Codex | Worst-case/안전 — Fallback 3단계, Admission Control, 대규모 이벤트 처리의 견고성 | Codex gpt-5.4 |

## 엔진 분배: Claude 6 (opus 4 + sonnet 2) / Gemini 3 / Codex 3
