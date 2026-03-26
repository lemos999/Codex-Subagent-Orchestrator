# WKI 맥락 전달 품질 개선 계획

> 작성: 2026-03-26
> 개정: 2026-03-26 (3엔진 검증 + /discuss 결과 반영)
> 목표: AI 간 맥락 공유 품질 향상 (nDCG는 회귀 방지 보조 지표)
> 제약: CPU 전용, Node.js/TypeScript, 115 청크 규모

---

## WKI의 목적 (3엔진 합의)

WKI는 **검색 시스템이 아니라 다중 AI용 맥락 전달 시스템**이다.

- **핵심 질문:** "3개 AI(Claude/Codex/Gemini)가 같은 맥락을 보고 더 나은 결정을 내리는가?"
- **nDCG는 목표가 아니다** — 회귀 방지 보조 지표로만 유지
- **진짜 평가:** AI 작업 결과 품질 (맥락 주입 전/후 비교)

---

## 기각된 전략: 계층적 2단계 검색

### 기각 이유 (3엔진 검증 합의)

1. **115개 청크에서 계층화 ROI 낮음** — brute-force가 밀리초 단위. 계층화 이점 미미 (Gemini)
2. **Stage 1 hard filter에서 탈락하면 복구 불가** — recall 손실 위험 > 정밀도 이득 (Codex)
3. **진짜 병목은 계층 부재가 아니라 FTS sparse recall** — 긴 자연어 쿼리의 AND 매칭 실패 (Codex)
4. **파일 요약 품질이 검색을 좌우** — 자연어/의도 질의에 심볼 목록 나열은 약함 (Codex)

---

## 채택된 전략: Contextual Flat Indexing

**원리:** 요약을 만들되, 검색은 평면으로. 평면 검색의 높은 재현율을 유지하면서 계층적 맥락을 청크에 내장.

> 학술 근거: Anthropic Contextual Retrieval, RAPTOR (Sauri et al., 2024)

### Step 1: 파일 요약 접두사 (Context Injection)

**변경:** 기존 Level 2 청크(함수/클래스/섹션)의 내용 앞에 파일 요약을 텍스트로 삽입한 후 재임베딩.

```
Before: "function spawnWorker(spec) { ... }"
After:  "[File: spawn.ts | Worker spawner | Exports: spawnWorker, toWorkerResult]
         function spawnWorker(spec) { ... }"
```

**접두사 내용:**
- TS 파일: `[File: 경로 | 파일 역할(첫 JSDoc) | 주요 export 심볼]`
- MD 파일: `[File: 경로 | H1 제목 | H2 목록]`
- 기타: `[File: 경로]`

**구현:** `src/core/indexer.ts`의 임베딩 텍스트 빌드 부분 수정. 현재 이미 `filePath + heading` prefix가 있으므로 확장.

**예상 효과:** 파일 맥락이 벡터에 내장되어 "spawn 관련 코드" 같은 파일 수준 쿼리에서 정밀도 향상.
**예상 코드량:** ~30줄
**리스크:** 낮음. 기존 검색 로직 변경 없음.

### Step 2: FTS soft OR

**변경:** 현재 FTS AND 매칭을 OR + 가중으로 변경. 긴 자연어 쿼리에서 모든 토큰이 일치하지 않아도 결과 반환.

```
Before: "orchestration workflow stages" → AND(orchestration, workflow, stages) → 0 results
After:  "orchestration workflow stages" → OR(orchestration, workflow, stages) → ranked results
```

**구현:** `src/store/fts-store.ts`의 FTS 쿼리 빌더 수정. FTS5의 OR 연산자 + `bm25()` 함수로 관련도 정렬.

**예상 효과:** tail 쿼리(0.506 engine-adapters, 0.527 workflow) 개선 → nDCG 상승.
**예상 코드량:** ~40줄
**리스크:** 중간. OR로 변경 시 노이즈 증가 가능 → 벡터 점수와의 fusion 가중치 재조정 필요.

### Step 3: BM25F Fielded Search (선택적)

**변경:** FTS 검색에서 file_path, heading, symbols, body를 분리 가중.

```
file_path 매칭: 가중치 2.0
heading 매칭: 가중치 1.5
body 매칭: 가중치 1.0
```

**구현:** FTS5의 `bm25()` 또는 별도 score 계산으로 필드별 가중치 적용.

**예상 효과:** 파일명/heading에 포함된 키워드가 body보다 높은 점수 → 정밀도 향상.
**예상 코드량:** ~50줄
**리스크:** 중간. 기존 fusion 가중치(FTS 0.4 + vector 0.6) 재조정 필요.

### Step 4: Gold Set 분리 평가

**변경:** 현재 gold-set-v2.json을 file-only / line-scoped로 분리하여 별도 평가.

**이유:** gold의 76%가 file-only 관련도 → 파일 localization 개선만으로 nDCG가 올라갈 수 있으나, 이는 "검색이 정밀해진 것"이 아니라 "파일 찾기가 좋아진 것". 진짜 검색 개선은 line-scoped 쿼리에서 확인.

**구현:** `src/eval/evaluator.ts` 수정. 평가 결과에 file-only nDCG / line-scoped nDCG 분리 보고.

**예상 코드량:** ~20줄

### Step 5: AI 작업 품질 평가 (장기)

**변경:** nDCG 외에 "AI가 맥락을 받고 더 나은 결과를 냈는가" 측정.

**방법:**
- 동일 작업을 WKI 맥락 주입 vs 미주입으로 실행
- 결과 비교: 정확도, 코드 품질, 결정 일관성

**이 Step은 코드 변경이 아닌 평가 프로세스 변경.** 구현 시점: Step 1~3 완료 후.

---

## 구현 순서

```
Step 1 (Context Injection) → 즉시 착수, 독립
    ↓ nDCG 평가 (회귀 없는지 확인)
Step 2 (FTS soft OR) → Step 1과 독립, 병렬 가능
    ↓ nDCG 평가 (tail 쿼리 개선 확인)
Step 3 (BM25F) → Step 2 이후 (필드 검색 기반)
    ↓ nDCG 평가
Step 4 (Gold Set 분리) → 언제든 (평가 도구)
Step 5 (AI 품질 평가) → Step 1~3 이후 (장기)
```

각 Step 완료 후 nDCG 평가 → 회귀 시 롤백.

---

## 예상 코드량 및 영향

| Step | 코드량 | 난이도 | nDCG 기대 |
|------|--------|--------|----------|
| 1. Context Injection | ~30줄 | 낮음 | +0.01~0.03 |
| 2. FTS soft OR | ~40줄 | 중간 | +0.02~0.05 (tail 개선) |
| 3. BM25F | ~50줄 | 중간 | +0.01~0.02 |
| 4. Gold Set 분리 | ~20줄 | 낮음 | 측정 개선 |
| 5. AI 품질 평가 | 프로세스 | — | 진짜 지표 |
| **총** | **~140줄** | | **+0.04~0.10** |

vs 기각된 계층적 계획: ~320줄, 높은 리스크

---

## 성공 기준

1. **nDCG 회귀 없음** (0.744 이상 유지)
2. **tail 쿼리 개선** (0.506 → 0.6+)
3. **인덱싱 시간** (13초 → 15초 이내)
4. **기존 테스트 통과**
5. **(장기) AI 작업 품질 측정 가능한 프레임워크**

---

## 검증 이력

- 2026-03-26 초안: 계층적 3-Level 임베딩 + 2단계 검색
- 2026-03-26 /submix 3엔진 검증: 2단계 hard filter 기각, Contextual Flat Indexing 권고
- 2026-03-26 /discuss 3엔진 토론: nDCG는 목표 아님, 맥락 전달 품질이 진짜 목표
