## 검증: PersonaBrain 12클러스터 메모리/연산 실현 가능성

### 검증 시나리오

당신이 "K=12, 512B/persona"를 권장했다. 이제 7클러스터와 12클러스터를 정밀 비교하라.

### 시나리오 A: 7클러스터 (Gemini 원안)
- tone[7][20] × float16 = 280B + 32B 메타 = 312B/persona
- 20K명: 6.24MB
- 1K batch: 312KB → L2 안정

### 시나리오 B: 12클러스터 (세분화)
- tone[12][20] × float16 = 480B + 32B 메타 = 512B/persona
- 20K명: 10.24MB
- 1K batch: 512KB → L2 안정

### 시나리오 C: MUST 4종만 추가 (10종 독립)
- tone[10][20] × float16 = 400B + 16B 메타 = 416B/persona
- 20K명: 8.32MB
- 1K batch: 416KB → L2 안정

### 질문

1. A/B/C 각각의 Step 2 tone 변조 추가 비용을 정밀 비교 (MAC, AVX-512 그룹, ms)
2. A/B/C 각각이 Step 4(캐시 미스 시 moment closure)에 미치는 추가 영향
   - moment state에 tone 정보가 포함되는가? 그러면 moment 크기도 증가?
3. Mitotype에 "클러스터 내 물질 비율 벡터"를 저장하면:
   - 7클러스터: 7 × ~5물질 × float16 = 70B 추가/Mitotype
   - 12클러스터: 12 × ~4물질 × float16 = 96B 추가/Mitotype
   - 총 Mitotype 테이블: 32종 × 96B = 3KB. 무시 가능?
4. 결론: 7, 10, 12 중 성능/표현력 최적 트레이드오프는?

한글로 작성.
