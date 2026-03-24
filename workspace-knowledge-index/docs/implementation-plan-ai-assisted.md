# Workspace Knowledge Index — AI 활용 구축 계획서

> **작성일**: 2026-03-16
> **기반**: plan-workspace-index.md (전략 설계서) + 4엔진 교차 검증 결과 (C1~C5 반영)
> **구축 방식**: 1인 개발자 + AI 에이전트 협업 (Claude opus/sonnet + Codex gpt-5.4 + Gemini 2.5-pro)
> **총 일정**: 12~14주 (4엔진 합의 재추정)

---

## 1. 구축 전략 — AI 역할 분담

### 1.1 AI 엔진별 구축 역할

| 역할 | 담당 AI | 근거 |
|------|---------|------|
| **아키텍처 설계 / 인터페이스 정의** | Claude opus | 정밀 추론, 긴 컨텍스트 이해 |
| **코드 구현 (scaffolding, 보일러플레이트)** | Codex gpt-5.4 + Claude sonnet | Codex=코드 생성 속도, Claude=도구 접근 |
| **코드 리뷰 / 대규모 분석** | Gemini 2.5-pro | 긴 컨텍스트 윈도우, 전체 코드베이스 리뷰 |
| **테스트 코드 생성** | Codex gpt-5.4 | 패턴 기반 대량 생성 |
| **검색 품질 평가** | Claude opus + Gemini | 평가셋 설계(opus) + 대량 평가 실행(Gemini) |
| **문서 작성** | Claude sonnet | 한글 품질 |

### 1.2 /sub · /submix 활용 패턴

각 Phase의 핵심 태스크는 `/sub` 또는 `/submix`로 실행한다.

```
일반 패턴: /submix <요청>
├── Codex → implementer (코드 생성, 읽기 전용 산출물)
├── Claude → implementer (파일 수정/생성, 도구 접근 필수)
├── Gemini → reviewer (전체 코드 리뷰, 긴 컨텍스트)
└── Claude haiku → watchdog (경량 검증)
```

### 1.3 품질 게이트

모든 Phase 완료 시 다음 검증을 실행한다:

| 게이트 | 방법 | 기준 |
|--------|------|------|
| 코드 리뷰 | `/submix review` (3엔진) | 3엔진 중 2개 이상 승인 |
| 테스트 통과 | `npm test` | 커버리지 80%+ |
| 검색 품질 | 골드셋 nDCG@10 | Phase 1B 이후 0.7+ |
| 보안 스캔 | prepared statement, env 검증 | SQL injection 0건 |

---

## 2. Phase 0 — 프로젝트 초기화 + 파일 맵 (1~1.5주)

### 2.0 사전 조치: 설계서 C1~C5 수정

Phase 0 시작 전, 4엔진 검증에서 발견된 Critical 항목을 설계서에 반영한다.

| # | 수정 사항 | AI 활용 |
|---|----------|---------|
| C1 | `chunks_meta.content TEXT NOT NULL` 추가, path 검색 B-tree 분리 | Claude sonnet: DDL 재작성 |
| C2 | `git diff --name-status -M` + untracked 조합, freshness.lock 확장 | Claude sonnet: 변경 감지 로직 설계 |
| C3 | 비용표 3단계(낙관/중간/보수) 재작성 | Claude haiku: 산술 검증 |
| C4 | 로드맵 12~14주로 조정 | 수동 |
| C5 | 성능 추정 단위 ms/chunk로 변경 | 수동 |

### 2.1 프로젝트 스캐폴딩

**산출물**: Node.js + TypeScript 프로젝트 골격

```
workspace-knowledge-index/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts              ← CLI 엔트리포인트 (wki)
│   ├── config/
│   │   └── schema.ts         ← wki.config.json 스키마 + 검증
│   ├── core/
│   │   ├── file-map.ts       ← file-map.json 생성/갱신
│   │   ├── freshness.ts      ← freshness.lock 관리
│   │   └── scanner.ts        ← 파일 트리 스캔 + gitignore 연동
│   ├── interfaces/           ← Phase 1A 대비 인터페이스 사전 정의
│   │   ├── vector-backend.ts ← VectorBackend { insert, search, delete, rebuild }
│   │   ├── embedding.ts      ← EmbeddingProvider { embed, batchEmbed }
│   │   └── parser.ts         ← Parser { parse(file): Chunk[] }
│   └── types/
│       └── index.ts          ← Chunk, SearchResult, FreshnessState 등
├── tests/
│   └── core/
│       ├── file-map.test.ts
│       ├── freshness.test.ts
│       └── scanner.test.ts
├── wki.config.json           ← 기본 설정 템플릿
└── docs/                     ← 기존 문서
```

**AI 활용**:
```
/submix 프로젝트 스캐폴딩
├── Codex → package.json, tsconfig.json, 디렉토리 구조 생성
├── Claude opus → 인터페이스 정의 (VectorBackend, EmbeddingProvider, Parser)
└── Claude sonnet → wki.config.json 스키마 + 검증 로직
```

### 2.2 파일 맵 + 변경 감지

**산출물**: `wki init`, `wki scan` CLI 명령

| 기능 | 설명 | 구현 난이도 |
|------|------|:-----------:|
| `wki init` | `.knowledge/` 초기화, 최초 스캔 | 낮음 |
| `wki scan` | file-map.json 갱신 | 낮음 |
| freshness.lock | `head_commit + branch/ref + dirty flag + file_hashes` (C2 반영) | 중간 |
| gitignore 연동 | `.gitignore` + 기본 exclude 패턴 적용 | 낮음 |

**file-map.json 확장성 대응 (I4 반영)**:
- 30K 파일 미만: 현행 JSON 형식 유지
- 30K 파일 이상: NDJSON(newline-delimited JSON) 또는 SQLite manifest 테이블로 자동 전환
- `wki scan`이 파일 수를 카운트하여 임계값 초과 시 경고 + 전환 제안

**AI 활용**:
```
/sub file-map + freshness 구현
├── Claude sonnet → implementer (scanner.ts, file-map.ts, freshness.ts)
├── Codex → test 코드 생성 (file-map.test.ts, freshness.test.ts)
└── Claude haiku → reviewer (코드 리뷰)
```

**변경 감지 (C2 반영)**:
```typescript
// freshness.lock 구조
interface FreshnessState {
  head_commit: string;
  branch: string;
  dirty: boolean;
  staged_fingerprint: string;     // staged 파일 해시
  untracked_fingerprint: string;  // untracked 파일 해시
  file_hashes: Record<string, string>;  // path → sha256
  indexed_at: string;             // ISO 8601
}

// 변경 파일 감지
function detectChanges(prev: FreshnessState): ChangedFiles {
  // git diff --name-status -M <prev.head_commit> HEAD
  // git diff --name-status -M HEAD (unstaged)
  // git diff --cached --name-status -M (staged)
  // git ls-files --others --exclude-standard (untracked)
}
```

### 2.3 Phase 0 완료 기준

- [ ] `wki init` 실행 → `.knowledge/file-map.json` + `freshness.lock` 생성
- [ ] `wki scan` 실행 → 변경된 파일만 갱신
- [ ] 테스트 통과 (커버리지 80%+)
- [ ] VectorBackend / EmbeddingProvider / Parser 인터페이스 확정

---

## 3. Phase 1A — 심볼 인덱스 + 정확 검색 (3주)

### 3.1 TS Compiler API 심볼 추출

**산출물**: `symbols.idx` (JSONL), `deps.graph` (JSON)

| 기능 | 설명 | AI 활용 |
|------|------|---------|
| TS 파서 | incremental Program, 심볼 단위 추출 | Codex: 보일러플레이트, Claude opus: 엣지 케이스 |
| 비-TS 파서 | 줄 기반 청킹 (200줄/50줄 오버랩) | Codex: 단순 구현 |
| MD 파서 | remark AST → 헤딩 단위 청킹 | Codex: remark 파이프라인 |
| deps.graph | import/require 추적 → adjacency list | Claude sonnet: 의존관계 해석 |

**TS Compiler API 주의사항 (I3 반영)**:
- 프로젝트 단위 Program 재사용 (메모리 절약)
- 메모리 상한 설정 (`--max-old-space-size=2048`)
- 대형 파일(>5000줄) 감지 시 경고 로그

**AI 활용**:
```
/submix TS 심볼 추출기 구현
├── Codex → implementer (ts-parser.ts 골격, remark 파이프라인)
├── Claude opus → implementer (incremental Program 설정, 엣지 케이스 처리)
├── Gemini → reviewer (전체 파서 코드 리뷰)
└── Codex → test 생성 (다양한 TS 패턴: HOC, Decorator, Namespace, re-export)
```

### 3.2 SQLite FTS5 정확 검색

**산출물**: `fts.db` (SQLite)

**수정된 DDL (C1 반영)**:
```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE chunks_meta (
  id          INTEGER PRIMARY KEY,
  file_path   TEXT NOT NULL,
  ordinal     INTEGER NOT NULL,
  heading     TEXT,
  content     TEXT NOT NULL,      -- ← C1: 누락 수정
  chunk_type  TEXT,
  start_line  INTEGER,
  end_line    INTEGER,
  token_count INTEGER,
  content_hash TEXT,
  UNIQUE(file_path, ordinal)
);

-- path 검색용 B-tree 인덱스 (C1: FTS5에서 분리)
CREATE INDEX idx_chunks_meta_path ON chunks_meta(file_path);
CREATE INDEX idx_chunks_meta_type ON chunks_meta(chunk_type);
CREATE INDEX idx_chunks_meta_hash ON chunks_meta(content_hash);

-- FTS5 (내용 + 제목 전용, 경로는 제외)
CREATE VIRTUAL TABLE chunks_fts USING fts5(
  content,
  heading,
  content='chunks_meta',
  content_rowid='id',
  tokenize='unicode61'
);

-- 동기화 트리거
CREATE TRIGGER chunks_meta_ai AFTER INSERT ON chunks_meta BEGIN
  INSERT INTO chunks_fts(rowid, content, heading)
  VALUES (new.id, new.content, new.heading);
END;
-- (DELETE, UPDATE 트리거 동일 패턴)
```

**AI 활용**:
```
/sub FTS5 구현 + 테스트
├── Claude sonnet → implementer (fts.ts: DDL, CRUD, 검색)
├── Codex → test 생성 (20K 청크 벤치마크, identifier/NL 질의)
└── Claude haiku → reviewer
```

### 3.3 CLI: `wki index`

**산출물**: 전체/증분 인덱싱 CLI

```
wki index                    # 증분 (변경 파일만)
wki index --full             # 전체 재인덱싱
wki index --project <name>   # 특정 프로젝트만
```

### 3.4 Phase 1A 완료 기준

- [ ] `wki index` 실행 → `symbols.idx` + `deps.graph` + `fts.db` 생성
- [ ] FTS5 식별자 검색 p50 < 5ms (20K 청크)
- [ ] TS 심볼 추출: 함수, 클래스, 인터페이스, 타입, export 커버
- [ ] 테스트 통과 (커버리지 80%+)

---

## 4. Phase 1B — 벡터 검색 + 하이브리드 (2.5~3주)

### 4.1 임베딩 파이프라인

**산출물**: `vectors.lance/` (LanceDB)

| 컴포넌트 | 구현 | AI 활용 |
|----------|------|---------|
| EmbeddingProvider (OpenAI) | text-embedding-3-large, 768d | Codex: API 래핑 |
| EmbeddingProvider (Voyage) | voyage-4-lite, 1024d | Codex: API 래핑 |
| EmbeddingProvider (Local) | onnxruntime-node + BGE-M3 | Claude opus: ONNX 통합 |
| VectorBackend (LanceDB) | insert, search, delete, rebuild | Codex: LanceDB API 래핑 |
| 배치 처리 | concurrency 4, retry 2, exponential backoff | Claude sonnet |

**비용 추정 (C3 반영)**:

| 시나리오 | 청크 수 | 토큰 | 비용 |
|----------|---------|------|------|
| 초기 (낙관) | 15K | 3M | $0.39 |
| 초기 (중간) | 20K | 6M | $0.78 |
| 초기 (보수) | 25K | 10M | $1.30 |
| 월간 증분 | 4K~6K | 1.2M~3M | $0.16~$0.39 |

### 4.2 하이브리드 검색 (I1 반영)

**점수 정규화**:
```typescript
// FTS5: bm25()는 좋을수록 더 낮은(음수) 값
function normalizeFTS(bm25Score: number): number {
  const raw = -bm25Score;  // 양수로 변환
  return minmax(Math.log1p(raw));  // top-50 후보 내에서 0~1 정규화
}

// Vector: cosine similarity (-1 ~ 1)
function normalizeVector(similarity: number): number {
  return (similarity + 1) / 2;  // 0~1 정규화
}
```

**동적 가중치 (Query Router 연동)**:
```typescript
function getWeights(queryType: QueryType): { fts: number; vector: number } {
  switch (queryType) {
    case 'identifier':   return { fts: 0.7, vector: 0.3 };  // handlePayment
    case 'path':         return { fts: 0.8, vector: 0.2 };  // src/services/
    case 'natural':      return { fts: 0.3, vector: 0.7 };  // "결제 관련 로직"
    case 'mixed':        return { fts: 0.5, vector: 0.5 };
  }
}
```

### 4.3 CLI: `wki search`

```
wki search "결제 로직" --project shortlive --top 5
wki search "handlePayment" --mode exact
wki search "인증 관련" --output json
```

**AI 활용**:
```
/submix 하이브리드 검색 구현
├── Codex → implementer (LanceDB 연동, 임베딩 파이프라인)
├── Claude opus → implementer (Query Router, 점수 정규화, 동적 가중치)
├── Gemini → reviewer (전체 검색 파이프라인 리뷰)
└── Codex → test + 벤치마크 (검색 품질 eval, 지연 측정)
```

### 4.4 검색 품질 평가 체계

| 항목 | 방법 | 목표 |
|------|------|------|
| 골드셋 | 50~100개 (query, expected_results) 쌍 | — |
| 지표 | nDCG@10, Precision@5, MRR | nDCG@10 > 0.7 |
| 벤치마크 | FTS-only / Vector-only / Hybrid 비교 | Hybrid > 단일 |

**AI 활용**: Claude opus가 골드셋 설계, Gemini가 대량 평가 실행

### 4.5 Phase 1B 완료 기준

- [ ] `wki search` 실행 → 하이브리드 검색 결과 반환
- [ ] 검색 지연: FTS-only < 15ms, Vector-only < 50ms, Hybrid < 100ms (DB 조회)
- [ ] 증분 인덱싱: ≤20 청크 변경 시 < 5초 (FTS-only), < 15초 (Hybrid)
- [ ] 골드셋 nDCG@10 > 0.7
- [ ] 임베딩 provider 전환 시 `wki rebuild --vectors` 정상 동작

---

## 5. Phase 2 — /sub 통합 + Query Router (3~4주)

### 5.1 Query Router

**산출물**: 질의 유형별 검색 경로 분기

```typescript
interface QueryRouter {
  classify(query: string): QueryType;  // identifier | path | natural | deps | mixed
  route(query: string, type: QueryType): SearchPlan;
}

// 규칙 기반 분류 (LLM 미사용)
function classify(query: string): QueryType {
  if (isCamelCase(query) || isSnakeCase(query)) return 'identifier';
  if (hasPathSeparator(query)) return 'path';
  if (isDepsQuery(query)) return 'deps';  // "누가 호출", "영향받는 파일"
  if (hasKorean(query) || isNaturalLanguage(query)) return 'natural';
  return 'mixed';
}
```

### 5.2 Lean RAG 패턴 구현

| 패턴 | 구현 | AI 활용 |
|------|------|---------|
| **Adaptive Retrieval** | Query Router — 위 5.1 | Claude opus |
| **Query Expansion** | 한/영 용어 맵 + camelCase 분해 + 정규화 | Codex: 용어 맵, Claude: 분해 로직 |
| **Multi-hop** | deps.graph 연쇄 검색 (depth ≤ 3, visited 상한 100) | Claude sonnet |

### 5.3 Context Block 생성기 (/sub 통합)

**산출물**: 오케스트레이터가 하위 에이전트 계약에 맥락 자동 주입

```typescript
interface ContextBlock {
  generate(taskDescription: string, options?: {
    topK?: number;       // 기본 10
    project?: string;
    tokenBudget?: number; // Gemini용 토큰 예산
  }): ContextResult;
}

interface ContextResult {
  markdown: string;      // Claude/일반: ## Relevant Context 블록
  filePaths: string[];   // Codex: --file 플래그용
  chunks: Chunk[];       // Gemini: 프롬프트 직접 주입용
}
```

**엔진별 주입 방식**:
```
/submix 작업 실행 시:
├── Claude → ContextResult.markdown를 계약에 삽입
├── Codex → ContextResult.filePaths를 --file 플래그로 전달
│           (대형 파일은 관련 청크만 발췌한 .context.md 생성)
└── Gemini → ContextResult.chunks를 프롬프트에 직접 주입
             (토큰 예산 상한 적용)
```

### 5.4 /sub · /submix 통합 훅

기존 오케스트레이터 워크플로우에 Knowledge Index를 자연스럽게 삽입:

```
[기존] /sub 실행 → 에이전트 생성 → 작업 실행
[변경] /sub 실행 → Knowledge Index 검색 → Context Block 생성 → 에이전트 계약에 삽입 → 작업 실행
```

**AI 활용**:
```
/submix Phase 2 통합 구현
├── Claude opus → Context Block 생성기 + /sub 훅 설계/구현
├── Codex → Query Router + Query Expansion 구현
├── Gemini → 전체 통합 리뷰 (기존 /sub 스킬과의 호환성)
└── Claude sonnet → Multi-hop 구현 + 통합 테스트
```

### 5.5 Phase 2 완료 기준

- [ ] `/sub` 실행 시 하위 에이전트 계약에 Context Block 자동 삽입
- [ ] `/submix` 실행 시 엔진별 맥락 주입 방식 분기 동작
- [ ] Query Router: 5가지 유형 분류 정확도 > 90% (수동 테스트 50건)
- [ ] Context Block 생성: < 1초

---

## 6. Phase 3 — MCP 도구 + 운영 안정화 (2.5~3주)

### 6.1 MCP Tool

기존 `mcp-server/` 구현 계획과 통합. Knowledge Index 도구를 MCP 서버에 추가.

```typescript
// knowledge_search
{
  name: "knowledge_search",
  inputSchema: {
    query: string,
    project_id?: string,
    file_type?: string,
    symbol_kind?: string,   // I: MCP 스키마에 추가
    search_mode?: "auto" | "exact" | "semantic" | "hybrid",
    top_k?: number,
  },
  outputSchema: {           // I: output 정의 추가
    results: Array<{
      file_path: string,
      start_line: number,
      end_line: number,
      content: string,
      score: number,
      match_type: string,
    }>,
    query_type: string,
    search_time_ms: number,
  }
}

// knowledge_status
// knowledge_index (수동 인덱싱 트리거 — 추가)
```

### 6.2 운영 안정화 (I6, I7 반영)

| 항목 | 구현 | AI 활용 |
|------|------|---------|
| atomic staging | `.knowledge/staging/ → atomic rename` | Claude sonnet |
| integrity check | `PRAGMA integrity_check` + manifest 검증 | Claude sonnet |
| stale lock 감지 | PID + 타임스탬프, 자동 해제 | Codex |
| 인덱스 상태 | `status=healthy/degraded/stale` | Codex |
| pre-commit hook | `.knowledge/` 실수 커밋 방지 | Codex |
| 로그 마스킹 | 검색 쿼리 내 민감 키워드 필터링 | Claude sonnet |
| prepared statement | FTS5 SQL injection 방어 | 전 Phase 적용 |
| 검색 캐싱 | LRU 캐시 (동일/유사 쿼리 임베딩 + 결과 캐싱, TTL 5분) | Codex |
| 모니터링 메트릭 | 인덱스 크기, 청크 수, 검색 지연 P50/P95, stale 청크 비율 로깅 | Claude sonnet |

### 6.3 크로스 프로젝트 검색 방향 (I5 반영 — 향후 확장)

Phase 3 범위에서는 단일 프로젝트 검색에 집중한다. 크로스 프로젝트 검색은 Phase 3 이후 별도 확장으로 진행하며, 방향은 다음과 같다:

- **전략**: 전략 설계서의 `workspace-meta/` 중앙 인덱스 대신, **federated search** 채택 (4엔진 합의)
- **방식**: 후보 프로젝트 선택 → 프로젝트별 top-k 병렬 검색 → RRF 병합
- **근거**: 중앙 JSON 인덱스는 규모 확장 시 parse/merge hotspot이 됨 (Codex #2 지적)
- **구현 시점**: Phase 3 완료 후, 멀티 프로젝트 사용 사례가 실제로 발생할 때

### 6.4 change-journal.jsonl (범위 결정)

전략 설계서 Phase 3 산출물에 포함된 `change-journal.jsonl`(변경 이력 스트림)은 **본 구축 계획의 범위에서 제외**한다.

- **제외 사유**: MVP에서는 `freshness.lock` + `git log`로 변경 이력 추적이 충분. 별도 저널은 운영 복잡도 대비 효용이 낮음.
- **재검토 시점**: Phase 3 완료 후, 에이전트가 "최근 어떤 파일이 변경되었는가?" 질의를 빈번히 사용하는 패턴이 확인될 때 도입 검토.

### 6.5 Phase 3 완료 기준

- [ ] MCP 클라이언트에서 `knowledge_search` 호출 → 결과 반환
- [ ] `wki status` → healthy/degraded/stale 표시
- [ ] stale lock 자동 해제 동작
- [ ] pre-commit hook 설치 가이드

---

## 7. 일정 총괄

```
주차  1    2    3    4    5    6    7    8    9   10   11   12   13   14
     ├─P0─┤
     C1~C5 수정
     스캐폴딩
     file-map
          ├───── Phase 1A ─────┤
          TS파서 + FTS5 + CLI
               인터페이스 확정
                              ├──── Phase 1B ────┤
                              임베딩 + 벡터
                              하이브리드 검색
                              품질 평가
                                                 ├────── Phase 2 ──────┤
                                                 Query Router
                                                 Context Block
                                                 /sub·/submix 통합
                                                                      ├── P3 ──┤
                                                                      MCP
                                                                      운영 안정화
```

| Phase | 기간 | 핵심 산출물 | AI 비중 |
|-------|:----:|-----------|:-------:|
| 0 | 1~1.5주 | 스캐폴딩, file-map, freshness, 인터페이스 | 70% |
| 1A | 3주 | symbols.idx, deps.graph, fts.db, `wki index` | 80% |
| 1B | 2.5~3주 | vectors.lance, 하이브리드 검색, `wki search` | 75% |
| 2 | 3~4주 | Query Router, Context Block, /sub·/submix 통합 | 70% |
| 3 | 2.5~3주 | MCP tools, 운영 안정화 | 65% |

**AI 비중**: 전체 구현의 약 **70~80%를 AI가 생성**하고, 사람은 설계 결정/리뷰/품질 게이트에 집중한다.

---

## 8. 비용 추정 (C3 반영)

### 8.1 임베딩 비용 (text-embedding-3-large, 768d)

| 시나리오 | 초기 | 월간 | 연간 |
|----------|:----:|:----:|:----:|
| **낙관** (15K 청크) | $0.39 | $0.16 | $2.31 |
| **중간** (20K 청크) | $0.78 | $0.25 | $3.78 |
| **보수** (25K 청크) | $1.30 | $0.39 | $6.00 |

### 8.2 AI 에이전트 구축 비용

| 엔진 | 예상 토큰 사용 | 추정 비용 |
|------|:-------------:|:---------:|
| Claude opus | ~2M tokens | 구독 포함 |
| Codex gpt-5.4 | ~5M tokens | 구독 포함 |
| Gemini 2.5-pro | ~3M tokens | 무료 티어 |
| **합계** | — | **$0** (구독 기반) |

### 8.3 인프라 비용

| 항목 | Phase 1~2 | Phase 3+ |
|------|:---------:|:--------:|
| 서버 | $0 (로컬) | $0 (로컬) |
| Qdrant (선택) | — | $12~24/mo (필요 시) |
| **합계** | **$0** | **$0~24/mo** |

---

## 9. 에러 처리 전략 (전략 설계서 섹션 11 매핑)

| 실패 유형 | 대응 | 구현 Phase |
|----------|------|:----------:|
| 임베딩 API 호출 실패 | 2회 재시도 (exponential backoff) → 실패 청크 건너뛰기 + 경고 로그 | 1B |
| LanceDB/Qdrant 쓰기 실패 | 트랜잭션 롤백 → 마지막 유효 인덱스 유지 | 1B |
| 파싱 오류 (TS/MD) | 해당 파일 건너뛰기 + 경고 로그 (인덱스 전체 실패 방지) | 1A |
| 인덱싱 중단 (크래시) | freshness.lock 미갱신 → 다음 scan 시 전체 재인덱싱 | 0 |
| 인덱스 DB 손상 | `wki rebuild` 명령으로 전체 재구축 (파생 데이터이므로 복구 가능) | 3 |
| FTS5 DB 손상 | 동일 — `wki rebuild`로 재구축 | 3 |
| 디스크 용량 부족 | 인덱싱 전 여유 공간 확인 + 경고 | 0 |
| 네트워크 타임아웃 (임베딩) | 배치 크기 축소 + 재시도. 3회 실패 시 로컬 임베딩 폴백 제안 | 1B |

**CLI 명령**: `wki rebuild [--vectors] [--fts] [--all]` — Phase 3에서 구현.

---

## 10. 리스크 관리

| 리스크 | 확률 | 영향 | 대응 |
|--------|:----:|:----:|------|
| TS Compiler API 메모리 초과 | 중 | 높 | `--max-old-space-size` 제한 + 대형 프로젝트 분할 |
| LanceDB breaking change | 중 | 중 | VectorBackend adapter 격리 + `wki rebuild --vectors` |
| 검색 품질 미달 (nDCG < 0.7) | 낮 | 높 | 골드셋 기반 반복 튜닝, RRF 조기 전환 검토 |
| Phase 2 통합 복잡도 초과 | 중 | 중 | "search API 먼저, orchestrator hook 나중"으로 분할 |
| 임베딩 API rate limit | 낮 | 낮 | 배치 크기 조절 + exponential backoff |

---

## 11. 성공 지표

| 지표 | 목표 | 측정 시점 |
|------|------|----------|
| 에이전트 맥락 탐색 시간 | **< 2초** (현재 수십 초~수 분) | Phase 2 완료 |
| 검색 정확도 (nDCG@10) | **> 0.7** | Phase 1B 이후 |
| 하이브리드 검색 지연 | **< 100ms** (DB 조회) | Phase 1B 완료 |
| Context Block 생성 | **< 1초** | Phase 2 완료 |
| 인덱스 갱신 (소규모) | **< 15초** (≤20 청크) | Phase 1B 완료 |
| 코드 테스트 커버리지 | **> 80%** | 전 Phase |

---

*이 계획서는 plan-workspace-index.md 전략 설계서와 4엔진 교차 검증(Claude opus + Codex gpt-5.4 xhigh x2 + Gemini 2.5-pro)의 C1~C5 수정 사항 및 I1~I7 개선 사항을 반영하여 작성되었다.*
