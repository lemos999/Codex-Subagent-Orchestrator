## 페르소나 국가 세계관 최종 검증 — 10에이전트

11개 Charter 전체를 읽고, 설계/구조/아키텍처의 일관성과 확장성을 빈틈 없이 검증하라.

### Charter 목록 (Projects/personas/docs/ 하위)
1. world-ontology.md — SOT, Layer 0~8, Executor, Registry
2. constitution.md — 헌법 8장 27조
3. economy-whitepaper.md — WILL 경제
4. physis-charter-v2.md — 기후 물리
5. tick-daemon-charter.md — 틱 데몬
6. humanity-charter.md — H1~H6
7. death-reincarnation-charter.md — 죽음/윤회
8. order-charter.md — 법/사법
9. society-charter-draft.md — 영지/투표/직업
10. secret-rumor-evidence-charter.md — 비밀/소문/증거
11. personabrain-snn-charter.md — PersonaBrain SNN v2.0

### 10명의 검증자 (각자 FAIL/WARN/PASS)

## 1. 서하린 — Layer 참조 정합
모든 Charter에서 언급하는 Layer 번호가 world-ontology와 일치하는가?
- 각 Charter의 "Ontology 연결" 섹션에서 선언한 Layer가 실제로 ontology에 존재하는가?
- Layer 0.5(자연법)가 참조하는 모든 문서에서 인식되고 있는가?
- Layer 간 단방향 참조 규칙(N은 0~N만 참조)이 모든 Charter에서 지켜지는가?

## 2. Rex Baek — Executor 파이프라인 정합
4개 Executor(Physis/Lachesis/Anima/Nomos)의 읽기/쓰기 범위가 모든 문서에서 일치하는가?
- Stage 1(Lachesis→Physis 반동기)이 tick-daemon과 ontology에서 동일한가?
- Anima의 L2 쓰기(PersonaBrain grow/prune)가 ontology §3.4와 §2.3 양쪽에 반영되었는가?
- Nomos의 피드백 → 다음 틱 STDP 경로가 tick-daemon과 personabrain-snn에서 일관되는가?

## 3. Elara Voss — 철학적 일관성
"뼈대만 설계, 살은 페르소나가" 원칙이 모든 Charter에 관철되는가?
- 어떤 Charter가 페르소나의 자율 영역을 침범하지 않는가?
- "비밀=두려움", "거짓말=연속체", "신뢰=수신자 상태"가 personabrain-snn과 정합하는가?
- 절대 수치가 남아있지 않은가? (구조만 확정, 수치는 시뮬 데이터에서)

## 4. Mira Chen — 신경과학 ↔ 세계관 정합
PersonaBrain의 12클러스터가 다른 Charter의 행동/감정과 정합하는가?
- humanity-charter H1~H6이 12클러스터 중 어느 것에 매핑되는지 명확한가?
- 오욕칠정(life-simulation-design)이 12클러스터로 표현 가능한가?
- 죽음(death-charter)의 "직감" 메커니즘이 PersonaBrain에서 구현 가능한가?

## 5. Teo Kang — 수치 교차 대조
11개 문서에 산재된 수치가 서로 모순되지 않는가?
- WILL 총량 20,260,406이 모든 문서에서 동일한가?
- 세율(10/3/0.5/5%)이 경제백서와 사회Charter에서 일치하는가?
- 뉴런 50M, energy 0.01~0.25/틱, 캐시 히트율 분포가 일관되는가?
- 틱 = 게임 1시간 = 현실 30분이 모든 문서에서 동일한가?

## 6. Dana Jeong — 행동 흐름 추적
하나의 행동(예: "양심 딜레마")이 시작부터 끝까지 여러 Charter를 거치는 경로를 추적:
- 자극(Physis 날씨/이벤트) → PersonaBrain(12클러스터) → Action_Proposal → Nomos 검증 → 피드백 → STDP
- 이 경로에서 끊기는 곳, 문서 간 인터페이스가 정의 안 된 곳은?
- 비밀 폭로 행동: secret-charter → personabrain(B클러스터) → order-charter(법) 경로가 완전한가?

## 7. Kael Arden — 확장성 스트레스 테스트
현재 아키텍처가 미래 확장에 열려있는가?
- 새 Charter 추가(외교/종교/기술) 시 기존 Layer 구조가 깨지지 않는가?
- 20K→50K→100K 인구 확장 시 PersonaBrain 10ms가 유지되는가?
- 새 Executor 추가(예: 외교 데몬) 시 Registry 확장이 가능한가?
- 12클러스터 → 16클러스터 확장 시 tone 포맷이 호환되는가?

## 8. Dr. Yuna Kang — 미토콘드리아 ↔ 경제 정합
Mitotype/energy_pool이 경제 시스템과 정합하는가?
- 식사(gold 지출) → energy_pool 회복 → 작업 능력 → WILL 채굴 경로가 닫혀있는가?
- 수면 → ATP 회복과 틱 데몬의 수면 스케줄러가 동기화되는가?
- Mitotype 32종의 Base 격차(±15%)가 경제적 불평등을 만드는가?

## 9. Riel Voss — 꿈/수면 ↔ 학습 정합
수면 시스템이 PersonaBrain 학습과 정합하는가?
- NREM SHY(가지치기) = Phase 2 prune과 동일한가, 별개인가?
- REM replay가 Phase 3과 어떻게 연결되는가?
- 수면 Layer 전환 규칙(§9.2.1)이 틱 데몬의 sleep lane(§11.6)과 일치하는가?
- 꿈 3이론 혼합이 12클러스터 체계와 정합하는가?

## 10. Jin Harada — 장애 복구 완전성
시스템 장애 시 복구 경로가 모든 Charter에서 정의되어 있는가?
- Executor 다운 → heartbeat 60초 → 재시작 (tick-daemon §D2)
- WAL 30초 → 최대 1틱 손실 (tick-daemon §D3)
- PersonaBrain 학습 발산 → ? (경로 미정의?)
- 캐시 전체 손상 → ? (에포크 전환은 부분 무효화이지만 완전 손상은?)
- Fallback A/B/C 이후에도 복구 안 되면? (최종 안전망?)

각 검증자별 FAIL/WARN/PASS + 구체적 근거. 한글.
