## 페르소나 국가 세계관 최종 검증 — Gemini 담당 3명

11개 Charter 전체를 읽고 FAIL/WARN/PASS로 판정하라.

### Charter 목록 (모든 문서를 아래에 첨부)

## 검증자 7: Kael Arden — 확장성 스트레스 테스트
- 새 Charter 추가(외교/종교/기술) 시 기존 Layer 0~8 구조가 깨지지 않는가?
- 20K→100K 인구 확장 시 PersonaBrain 10ms 유지 가능한가?
- 새 Executor 추가 시 Registry §3.6 확장 규약이 충분한가?
- 12클러스터 → 16클러스터 확장 시 tone 512B 포맷이 호환되는가?

## 검증자 8: Dr. Yuna Kang — 미토콘드리아 ↔ 경제 정합
- 식사(gold) → energy_pool → 작업 능력 → WILL 채굴 경로가 닫혀있는가?
- 수면 → ATP 회복과 틱 데몬 sleep lane이 동기화되는가?
- Mitotype 32종 Base ±15% 격차가 경제적 불평등을 과도하게 만드는가?

## 검증자 9: Riel Voss — 꿈/수면 ↔ 학습 정합
- NREM SHY = personabrain-snn Phase 2 prune과 동일한가?
- REM replay = Phase 3 consolidate와 연결되는가?
- 수면 Layer 전환(§9.2.1)과 틱 데몬 sleep lane(§11.6)이 일치하는가?
- 꿈 3이론이 12클러스터와 정합하는가?

각 검증자별 FAIL/WARN/PASS. 한글.

--- 이하 주요 Charter 발췌 ---

[PersonaBrain SNN Charter 핵심]
- 3계층: Layer 0(공유 아키텍처) → Layer 1(Moment State 5M~50M) → Layer 2(Decision Readout)
- 12클러스터: V(DA) L(β-END) S(5-HT) B(OXT) A(NE) T(CORT) C(ACh) G(Glu) F(ADO) I(GABA) D(T) P(SP)
- tone 512B/persona, effective_tone[20] 전달, cache key에 tone_version만
- 4단계 에너지: 강도1(0.01) 2(0.05) 3(0.10) 4(0.25) /틱
- 미토콘드리아: energy_pool(0~1) + 영역 취약성 6개 + Mitotype 32종(±40%)
- 50M 동적 성장: grow-prune-consolidate 3상
- 꿈: NREM 75%(SHY) / REM 25%(anti-replay), 3이론 혼합
- 학습: Phase 0(STDP) → 1(Teacher Net) → 2(3-factor STDP+RL) → 3(꿈 replay)
- 틱 파이프라인: Step 1~6, 총 8.5ms
- Fallback: A(유사상황) > B(직전반복 2틱) > C(no-op)
- sleep lane: 수면 페르소나는 L0/L2 건너뜀, NREM/REM consolidation만

[Tick Daemon Charter 핵심]
- Stage 1: Lachesis(선행) → Physis(후행), 반동기
- Stage 2: Anima (PersonaBrain)
- Stage 3: Nomos (승인/거부, 경제 정산)
- Heartbeat 4×4 상호 감시, 10초 주기
- WAL 30초, 원자적 쓰기, 최대 1틱 손실
- 수면 스케줄러: active batch → sleep lane 전환

[Economy Whitepaper 핵심]
- WILL 총 20,260,406, 반감기 8 에포크
- 세율: 소득세 10%, 거래세 3%, 자산세 0.5%/분기, 돌파세 5%
- 생활비: 일 10 gold(최소), 월 300~1500 gold
- 영지 국고: 아카데미 25% / 인프라 20% / 사회기금 10% / 영주 15% / 상납 30%
