## 역할: 메모리/연산 최적화 분석가 (memory-optimizer)

PersonaBrain의 neuromodulator_tone을 N종 × 20영역으로 확장할 때의 메모리/연산 비용을 분석하라.

### 현재 설계
- neuromodulator_tone: 6종 × 20영역 × float16 = 240B + 16B 메타 = 256B/페르소나
- 20K 페르소나 × 256B = 5.12MB (무시 가능)

### 확장 시나리오별 비용 계산

N종 × 20영역 × float16 = N × 40 bytes

| N | bytes/persona | 20K명 총 | 비고 |
|---|---|---|---|
| 6 (현재) | 240B | 4.8MB | 현행 |
| 10 | 400B | 8MB | |
| 15 | 600B | 12MB | |
| 20 | 800B | 16MB | |
| 25 | 1000B | 20MB | ~1KB/persona |
| 30 | 1200B | 24MB | |
| 50 | 2000B | 40MB | 전수 |

### 질문

1. **메모리 영향**: 위 테이블 검증 + 총 64GB RAM 예산에서 차지하는 비율
   - 현재 PersonaBrain 메모리 구성: Graphon 16MB(공유) + moment 40MB(개인) + tone 5MB + bias 20MB + L2 40MB = ~121MB
   - tone을 1KB로 확장하면 총 141MB → 여전히 64GB의 0.2%

2. **연산 영향**: Step 2(Layer 0 배치)에서 tone 변조의 추가 비용
   - 현재: 1K명 × 6종 × 20영역 = 120K multiply-add
   - N=25: 1K명 × 25종 × 20영역 = 500K multiply-add
   - AVX-512로 한 번에 32개 float16 처리 → 추가 ~0.1ms?

3. **캐시 라인 적합성**: tone 데이터가 CPU L1(32~64KB)에 들어가는가?
   - 현재: 1K명 × 256B = 256KB → L2 적합
   - N=25: 1K명 × 1KB = 1MB → L2 경계
   - N=50: 1K명 × 2KB = 2MB → L2 초과 → L3

4. **최적 N**: 메모리/연산/캐시를 종합하여 성능 저하 없이 확장 가능한 최대 N은?

5. **대안**: N종을 전부 float16으로 저장하는 대신, 클러스터 대표 변수 K개(K<N) × 영역별로 저장하면?
   - K=12 클러스터 × 20영역 = 480B → 256B~1KB 범위

출력: 비용 테이블 + 최적 N 또는 K + 캐시 적합성 분석. 한글.
