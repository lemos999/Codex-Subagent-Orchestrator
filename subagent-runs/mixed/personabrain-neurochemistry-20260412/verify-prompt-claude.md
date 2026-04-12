## 검증 대상: PersonaBrain 신경화학물질 통합 권장안

### 권장안 요약

Phase 1: 6종 → 10종 (MUST 4종 추가: OXT, CORT, β-END, ADO)
Phase 2: 10종 → 12 클러스터 (50종을 기능 클러스터로 압축)

최종 구조:
  tone[K=12][20영역] × float16 = 480B + 32B 메타 = 512B/페르소나
  + Mitotype에 클러스터 내 물질 비율 벡터 저장 (정적, 30B)

12 클러스터:
  V-Drive (DA + Endorphin + Endocannabinoid + Ghrelin) — 보상/동기
  S-Stability (5-HT + OXT + AVP + Progesterone) — 유대/안정
  A-Alertness (NE + Cortisol + EPI + CRH + Histamine) — 각성/스트레스
  C-Cognition (ACh + Glu + D-serine) — 학습/기억
  R-Restoration (GABA + ADO + MEL + Glycine) — 수면/억제
  M-Metabolism (Insulin + Leptin + Thyroid + GH) — 에너지 대사
  P-Pain (Substance P + NPY + ENK + DYN) — 통증/감각
  + 5개 추가 세분화 클러스터 (미정)

### 검증 관점 (4명)

## 검증자 1: Mira Chen — 신경과학 정확성

기존 10가지 행동 회로에 대해:
1. OXT가 S-Stability 클러스터에 들어가면, "대상 특이적 신뢰"(이 특정 상대를 신뢰)가 "범용 안정감"(기분이 좋으면 신뢰)과 구분되는가?
   - OXT의 핵심은 target-specific. 5-HT와 같은 클러스터에 넣으면 이 특이성이 소실되지 않는가?
2. CORT가 A-Alertness에 들어가면, NE(급성 초단위)와 CORT(만성 시간~일단위)의 시간 스케일 차이가 보존되는가?
3. β-END가 V-Drive에 들어가면, wanting(DA)과 liking(β-END)의 분리가 유지되는가?
4. ADO가 R-Restoration에 들어가면, "수면 압력 축적"(깨어있을 때)과 "수면 중 억제"(GABA)가 구분되는가?
5. 7클러스터로 묶으면 잃어버리는 행동 해상도가 있는가? 구체적으로 어떤 행동이 품질 저하되는가?

## 검증자 2: Dana Jeong — 행동 회로 영향

기존 10가지 행동 회로 매핑(Charter §7)이 12클러스터로 전환 시:
1. 각 행동의 "핵심 경쟁" 구조가 유지되는가?
   예: 양심 딜레마 = DA(이득) vs 5-HT(도덕) → V-Drive vs S-Stability로 바뀌면 의미가 변하는가?
2. 클러스터 간 경쟁이 클러스터 내부 경쟁을 대체하는 문제는 없는가?
   예: V-Drive 내에서 DA vs β-END의 경쟁(wanting vs liking)이 사라지는가?
3. 10가지 행동 × 12클러스터 매핑 테이블을 작성하라. 기존 6종 매핑 대비 개선/손실 분석.

## 검증자 3: Teo Kang — 계산 비용 검증

Codex가 "K=12, 512B/persona, L2 안정"이라 했다. 이를 검증:
1. 512B × 20K명 = 10.24MB. 이것이 기존 121MB 총 메모리에 추가되어 131MB. 64GB 대비 0.2%. → 맞는가?
2. Step 2에서 tone 변조: 1K명 × 12클러스터 × 20영역 = 240K MAC. AVX-512 fp16 32-lane → 7.5K 그룹. 추가 ~0.05ms. → 현실적인가?
3. 클러스터 내 물질 비율을 Mitotype에서 정적 저장하면 런타임 비용 0. → 맞는가?
4. 12→7로 줄이면 어떤 이득이 있는가? 7로 충분한가 12가 필요한가?

## 검증자 4: Kael Arden — 아키텍처 정합성

1. 기존 Charter §6(6종 × 20영역)을 12클러스터 × 20영역으로 교체할 때, 다른 섹션(§7 행동, §8 학습, §9 꿈, §10 틱 통합)에 영향을 주는 부분은?
2. Phase 1(10종)에서 Phase 2(12클러스터)로 전환 시 데이터 마이그레이션 경로는?
3. Mitotype 5 클레이드의 기저선 프로필이 12클러스터로 확장되어야 함. 기존 테이블과의 호환성은?
4. 12클러스터 중 7개만 Gemini가 정의했고 5개는 "미정". 이 5개가 채워지지 않으면 시스템이 동작하는가?
