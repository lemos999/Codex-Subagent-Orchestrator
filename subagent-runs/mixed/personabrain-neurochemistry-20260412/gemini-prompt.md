## 역할: 기능적 클러스터 압축 설계자 (cluster-compressor)

뇌의 50종+ 신경화학물질을 PersonaBrain에서 사용 가능한 "대표 변수"로 압축하라.

### 배경
현재 PersonaBrain은 6종(DA, 5-HT, NE, ACh, GABA, Glu)만 사용하지만 실제 뇌는 50종+.
모든 종을 개별 시뮬하면 메모리/연산 비용이 폭증한다.
해결: 기능이 유사한 물질을 클러스터로 묶어 "대표 변수"로 표현.

### 50종+ 목록 (Agent 1이 상세 분석하지만, 당신은 압축에 집중)

카테고리별:
- 모노아민 (6): DA, 5-HT, NE, Epinephrine, Histamine, Melatonin
- 아미노산 (4): GABA, Glutamate, Glycine, D-serine
- 콜린 (1): ACh
- 펩타이드 (15+): Oxytocin, Vasopressin, Endorphin(β-endorphin), Enkephalin, Dynorphin, Substance P, NPY, CRH, Orexin, CCK, VIP, CGRP, Galanin, Somatostatin, TRH
- 호르몬 (10+): Cortisol, Testosterone, Estrogen, Progesterone, Melatonin, Insulin, Leptin, Ghrelin, Thyroid(T3/T4), GH
- 가스형 (3): NO, CO, H2S
- 지질 (2): Anandamide, 2-AG (endocannabinoids)
- 퓨린 (2): Adenosine, ATP
- 기타 (3+): Taurine, Agmatine, Phenethylamine

### 당신의 질문

1. **기능적 클러스터링**: 위 50종+을 기능적 유사성으로 묶어라.
   예시 가설:
   - "보상/동기" 클러스터: DA + Endorphin + Endocannabinoid + Dynorphin
   - "스트레스/각성" 클러스터: NE + Cortisol + CRH + Epinephrine
   - "사회적 유대" 클러스터: Oxytocin + Vasopressin + 5-HT(일부)
   - "수면/일주기" 클러스터: Melatonin + Adenosine + Orexin + GABA(일부)
   이런 식으로, 그러나 당신의 분석으로 더 정확하게.

2. **대표 변수 설계**: 각 클러스터를 단일 float16 변수로 표현할 수 있는가?
   - 클러스터 내 개별 물질의 비율은 고정(Mitotype에서)하고, 전체 수준만 변동?
   - 아니면 2~3개 주축(PCA?)으로 표현?

3. **최적 클러스터 수**: 6종(현재)은 부족, 50종은 과다. 몇 개의 클러스터가 최적인가?
   - 행동 품질 vs 계산 비용의 최적점

4. **클러스터 × 20영역 매트릭스**: 각 클러스터가 20개 뇌 영역에서 동일하게 작용하는가, 영역별 차이가 있는가?

5. **Mitotype 연결**: 클러스터 내 개별 물질의 비율이 Mitotype(체질)에 따라 다른가?

출력: 클러스터 목록 + 대표 변수 설계 + 최적 N 제안. 한글.
