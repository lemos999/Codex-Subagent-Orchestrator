# 체계논리가 — 세계관 아키텍트 관점 정합성 검증

## 1. Position
11개 Charter의 뼈대는 견고하나, **Stage 1 실행 순서에 근본적 모순**이 있고, **Layer 0.5라는 미등록 계층**과 **상속세 미정의** 등 참조 구멍 5건이 시스템 작동을 위협한다.

## 2. Reasoning — 발견된 불일치

**A. Stage 1 모순 (가장 심각)**
- `world-ontology.md` §3.1: `[Physis ∥ Lachesis] ← 병렬 (서로 무관)`
- `tick-daemon-charter.md` §3: `Lachesis 선행 → Physis 후행 (반동기)` — "Lachesis가 틱 번호를 먼저 확정해야 Physis가 '지금'을 알 수 있음"
- SOT(단일 진실 원천)인 ontology와 하위 Charter가 정반대. 파이프라인 물리 법칙 위반.

**B. Layer 0.5 유령 계층**
- `order-charter.md` §2가 "Layer 0.5: 자연법 3조"를 도입했으나, `world-ontology.md`의 Layer 구조(L0~L8)에 등록되지 않음. SOT 미반영.

**C. 상속세 참조 단절**
- `death-reincarnation-charter.md` §4: "상속세 납부 (세율은 경제 Charter에서)" → `economy-whitepaper.md`에 상속세 정의 없음. 소득세/거래세/자산세/돌파세 4종만 존재.

**D. 헌법 조문 수 불일치**
- 검증 대상 제목: "8장 28조" → 실제 헌법 본문: 제1조~제27조 = **27조**. 1조 누락 또는 카운트 오류.

**E. Anima 쓰기 범위 — SNN Charter와 Ontology 미세 차이**
- Ontology §3.4: Anima writes L3, L4, L5. PersonaBrain SNN charter의 STDP 학습은 L2(Entity/PersonaBrain 가중치)를 갱신하는데, L2는 Anima 쓰기 금지 영역.

## 3. Concerns
- Stage 1 모순이 해소 안 되면 틱 데몬 구현 시 어느 문서를 따를지 결정 불가.
- Layer 0.5는 편의적 삽입이나, Ontology에 미등록이면 Nomos가 "어느 Layer에서 자연법을 읽는가"가 불명확.
- 상속세 부재로 죽음 이후 경제 흐름에 구멍. 사회적 모델 채택 시 상속 분쟁 해결 근거 없음.

## 4. Recommendation
1. **Stage 1**: tick-daemon-charter의 "반동기"가 논리적으로 옳음(Physis가 틱 번호를 알아야 함). **world-ontology를 수정**하여 "Lachesis 선행 → Physis 후행 (반동기)"로 통일.
2. **Layer 0.5**: world-ontology §1에 L0.5 Natural Law 서브레이어를 공식 등록.
3. **상속세**: economy-whitepaper §3에 5번째 세금으로 상속세 추가, 또는 death charter에서 "미래 입법 사항"으로 명시.
4. **헌법 조수**: 27조인지 28조인지 확인 후 통일.
5. **Anima L2 쓰기**: PersonaBrain 가중치 갱신을 L3c(심층)로 귀속시키거나, Ontology에서 Anima의 L2 제한적 쓰기(brain_weights 필드 한정)를 명시.

[POSITION: SOT인 world-ontology에 Stage 1 반동기·Layer 0.5·상속세·Anima L2 쓰기 4건을 반영해야 11개 Charter가 정합한다]