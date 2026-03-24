# Workspace Knowledge Index — 전략 설계서

> **비전**: 어떤 에이전트든, 어떤 프로젝트든, 필요한 맥락을 즉시 찾아서 정확히 이해한 상태로 작업을 시작한다.
>
> **작성일**: 2026-03-15
>
> **상태**: Draft v2 — 4AI 교차 검증 완료
>
> **검증 상태**: 4AI 교차 검증 완료 (Claude opus x3 + Codex GPT-5.4 xhigh x1 + Watchdog opus x2)
> - 목표 부합도: 진행 승인
> - Lean RAG: 3패턴 확정 (Adaptive + Query Expansion + Multi-hop)
> - DB 구조: JSONL + JSON + LanceDB + FTS5(SQLite) — 확정
> - 잔여 개선 4건: 향후 Phase에서 해결

---

## 1. 비전 선언

현재 AI 에이전트 워크플로우의 가장 큰 병목은 **맥락 탐색**이다. 프로젝트가 커질수록 에이전트는 파일을 하나씩 열어보며 구조를 파악하는 데 시간을 낭비하고, 잘못된 맥락으로 작업을 시작해 결과물의 품질이 떨어진다.

Workspace Knowledge Index는 이 문제를 근본적으로 해결한다.

- **즉시성**: 질의 하나로 관련 코드, 문서, 의존관계를 1초 이내에 반환한다.
- **정확성**: 키워드 매칭이 아닌 의미 기반 검색으로 진짜 관련 있는 맥락을 찾는다.
- **투명성**: 인덱스는 사람이 읽을 수 있는 형식으로 저장되고, git으로 추적 가능하다.
- **비침습성**: 기존 프로젝트 구조를 변경하지 않고, `.knowledge/` 디렉토리 하나로 동작한다.
- **자연스러운 소멸**: 프로젝트가 끝나면 디렉토리를 삭제하는 것만으로 완전히 제거된다.

---

## 2. 시스템 아키텍처

```
                     ┌─────────────────────────────────────────────┐
                     │              ACCESS LAYER                   │
                     │  ┌──────────┐ ┌──────────┐ ┌─────────────┐ │
                     │  │ MCP Tool │ │ CLI Query│ │ /sub Context│ │
                     │  │ (Claude) │ │ (Codex)  │ │  Injection  │ │
                     │  └────┬─────┘ └────┬─────┘ └──────┬──────┘ │
                     └───────┼────────────┼───────────────┼────────┘
                             │            │               │
                     ┌───────▼────────────▼───────────────▼────────┐
                     │             SEARCH LAYER                    │
                     │  ┌──────────────────────────────────────┐   │
                     │  │          Query Router                │   │
                     │  │  exact? ──→ FTS5        ──┐         │   │
                     │  │  fuzzy? ──→ Vector Search ─┤ Merge   │   │
                     │  │  deps?  ──→ Graph Walk   ──┘         │   │
                     │  └──────────────────────────────────────┘   │
                     └─────────────────────┬───────────────────────┘
                                           │
                     ┌─────────────────────▼───────────────────────┐
                     │             INDEX LAYER                     │
                     │  ┌──────────┐ ┌──────────┐ ┌────────────┐  │
                     │  │ FTS5 DB  │ │ Vector DB│ │ Deps Graph │  │
                     │  │ (SQLite) │ │(LanceDB) │ │   (JSON)   │  │
                     │  └────┬─────┘ └────┬─────┘ └─────┬──────┘  │
                     └───────┼────────────┼─────────────┼──────────┘
                             │            │             │
                     ┌───────▼────────────▼─────────────▼──────────┐
                     │              DATA LAYER                     │
                     │  ┌──────────────────────────────────────┐   │
                     │  │           Parser Pipeline             │   │
                     │  │  .ts/.tsx → TS Compiler API           │   │
                     │  │  .md      → remark (GFM+frontmatter) │   │
                     │  │  기타      → 단순 청킹 (줄 기반)       │   │
                     │  └──────────────┬───────────────────────┘   │
                     │  ┌──────────────▼───────────────────────┐   │
                     │  │  file-map.json + freshness.lock      │   │
                     │  │  (git commit hash 기반 변경 감지)      │   │
                     │  └──────────────────────────────────────┘   │
                     └─────────────────────────────────────────────┘
```

4-레이어 구조: **Data → Index → Search → Access**. 각 레이어는 독립적으로 교체 가능하며, 아래에서 위로 의존한다.

---

## 3. 기술 스택

| 영역 | 선택 | 버전/사양 | 근거 |
|------|------|-----------|------|
| **임베딩 (클라우드)** | OpenAI `text-embedding-3-large` | 768d 축소 설정 (기본 3072d에서 축소), 1024d 선택 | $0.13/1M 토큰, 프로덕션 안정 |
| **임베딩 (로컬)** | `onnxruntime-node` + BGE-M3 | ONNX Runtime | 오프라인/비용 절감 시 대체 |
| **임베딩 (한글 특화)** | Voyage `voyage-4-lite` | 1024d | $0.02/1M 토큰, 한글 retrieval 우수 |
| **벡터 DB (Phase 1)** | **LanceDB** | v0.27+ (beta, v1 미달) | 서버 불필요, 프로젝트별 분리 적합. 0.x pin 필수, backend adapter 분리로 Qdrant 전환 대비 |
| **벡터 DB (Phase 2+)** | **Qdrant** v1.15 GA | Docker 로컬 | 서버화 시 전환, 프로덕션 검증 |
| **정확 검색** | SQLite FTS5 | 보조 인덱스 | 정확한 식별자/경로 검색 |
| **MD 파싱** | `remark-parse` + `remark-gfm` + `remark-frontmatter` | — | AST 기반 구조 파싱 |
| **TS/TSX 파싱** | TypeScript Compiler API | incremental Program | 대규모 코드베이스 최적화, 정확한 심볼 추출 |
| **기타 파일 파싱** | 줄 기반 단순 청킹 | — | tree-sitter 없이도 충분한 범용 처리 |
| **MCP 연동** | `@modelcontextprotocol/sdk` | v1.25.1 pinned | spec revision 동시 고정 |
| **변경 감지** | git commit hash | freshness.lock | 증분 인덱싱 트리거 |

### 스토리지 설정 (`wki.config.json`)

사용자가 환경에 맞게 벡터 DB와 임베딩 모델을 선택할 수 있다:

```json
{
  "projects": [
    {
      "name": "shortlive-shop-helper",
      "root": "C:/Users/haj/projects/shortlive-shop-helper",
      "exclude": ["node_modules", ".next", "dist", "dev.db"]
    },
    {
      "name": "subagent-orchestrator",
      "root": ".",
      "exclude": [".npm-cache", "subagent-records"]
    }
  ],

  "storage": {
    "index_root": ".knowledge",

    "vector_backend": "lancedb",
    "_vector_backend_options": ["lancedb", "qdrant", "none"],

    "lancedb": {
      "path": ".knowledge/{project}/vectors.lance"
    },
    "qdrant": {
      "url": "http://localhost:6333",
      "api_key": null
    }
  },

  "embedding": {
    "provider": "openai",
    "_provider_options": ["openai", "voyage", "local"],

    "openai": {
      "model": "text-embedding-3-large",
      "dimensions": 768
    },
    "voyage": {
      "model": "voyage-4-lite",
      "dimensions": 1024
    },
    "local": {
      "runtime": "onnxruntime-node",
      "model": "BGE-M3",
      "dimensions": 1024
    }
  },

  "schema_version": 1,

  "chunking": {
    "max_lines": 200,
    "overlap_lines": 50,
    "max_tokens": 1000
  },

  "indexing": {
    "concurrency": 4,
    "max_file_size_mb": 10,
    "follow_gitignore": true,
    "timeout_ms": 30000,
    "retry": 2
  },

  "logging": {
    "level": "info"
  },

  "search": {
    "fts_db": ".knowledge/{project}/fts.db",
    "fusion": {
      "strategy": "weighted_sum",
      "_strategy_options": ["weighted_sum", "rrf"],
      "weights": { "fts": 0.4, "vector": 0.6 }
    }
  }
}
```

**선택 가이드:**

| 환경 | 벡터 DB | 임베딩 | 이유 |
|------|---------|--------|------|
| **로컬 개발 (기본)** | `lancedb` | `openai` | Docker 불필요, 파일 기반, 삭제 쉬움 |
| **오프라인/비용 절감** | `lancedb` | `local` | API 없이 완전 로컬 동작 |
| **서버/팀 공유** | `qdrant` | `openai` | 원격 접근, 멀티 클라이언트, 프로덕션 안정 |
| **벡터 검색 없이 시작** | `none` | — | FTS5만으로 키워드 검색 (Phase 0) |

> **주의**: 임베딩 provider를 전환하면 차원(dimension)이 달라질 수 있다 (OpenAI 768d vs Voyage 1024d vs BGE-M3 1024d). provider 전환 시 해당 프로젝트의 벡터 인덱스 전체를 재생성해야 한다. `wki rebuild --vectors` 명령으로 처리.

> **LanceDB 마이그레이션 전략**: LanceDB가 v1 GA 도달 시 breaking change가 예상된다. backend adapter 인터페이스를 통해 LanceDB 내부 구현을 격리하며, v1 전환 시 `wki rebuild --vectors`로 벡터 데이터를 재생성한다. 벡터 데이터는 파생 데이터이므로 언제든 원본 청크에서 재구축 가능.

### 명시적 제외 목록

| 패키지 | 제외 사유 |
|--------|-----------|
| `sqlite-vec` | alpha 단계, breaking change 예상 |
| `fastembed` | 2026-01-15 archived |
| Prisma graph | 선택적 확장으로 격하 (MVP 범위 밖) |

---

## 4. 인덱싱 전략

### 4.1 파싱 이원화 (Watchdog #1)

파싱은 언어 특성에 따라 두 경로로 분기한다.

**정밀 경로 (TypeScript/TSX)**
- TypeScript Compiler API의 incremental Program을 사용
- 함수, 클래스, 인터페이스, 타입, export 등 심볼 단위 추출
- `symbols.idx` (JSONL 형식)로 저장: `{file, symbol, kind, line, signature, docstring}`
- 의존 관계를 `deps.graph` (JSON adjacency list)로 기록

> **참고**: deps.graph는 프로젝트 내부 파일 간 의존관계만 추적한다. node_modules 등 외부 패키지 의존성은 `package.json`/`package-lock.json`에서 별도 추출하며, Phase 2 이후 필요 시 `external_deps` 인덱스로 확장한다.

**범용 경로 (Markdown, JSON, 기타)**
- Markdown: remark AST → 헤딩 단위 청킹, frontmatter 메타데이터 보존
- 기타: 줄 기반 단순 청킹 (기본 200줄, 50줄 오버랩)

> **향후 확장**: Phase 1A 이후 검색 품질 평가에서 "이 심볼을 어디서 사용하는가?" 쿼리의 precision이 부족하면, `symbol_references` 인덱스(심볼명 → 사용 파일/줄 매핑)를 추가한다. 현재는 deps.graph + FTS5 조합으로 대체.

### 4.2 청킹 규모 추정

| 항목 | 수치 |
|------|------|
| 전체 워크스페이스 | ~900MB |
| node_modules 제외 후 순수 소스 | 50~80MB |
| 추정 청크 수 | 15,000~20,000개 |
| 청크 크기 | 200~500 토큰 (심볼 단위는 가변) |

### 4.3 증분 인덱싱

**변경 감지 메커니즘**
```
freshness.lock
├── commit: "abc1234"          ← 마지막 인덱싱 시점의 git HEAD
├── indexed_at: "2026-03-15T..."
└── file_hashes: { "src/a.ts": "sha256:..." }
```

- `git diff --name-only <last-commit> HEAD`로 변경 파일 목록 획득
- 변경된 파일만 재파싱 → 해당 청크만 벡터 DB에서 교체
- **성능 보정 (Watchdog #6)**: 파일당 약 100ms, 대규모 변경(리팩토링 등) 시 수십 초 소요 가능

### 4.4 file-map.json

프로젝트 전체 파일 트리의 경량 스냅샷. 에이전트가 인덱스 없이도 구조를 파악할 수 있는 폴백.

```jsonc
{
  "version": 1,
  "root": "shortlive-shop-helper",
  "files": [
    { "path": "src/index.ts", "size": 2048, "type": "typescript", "symbols": 12 },
    { "path": "docs/API.md", "size": 4096, "type": "markdown", "headings": 8 }
  ]
}
```

---

## 5. 검색 전략

### 5.1 하이브리드 검색

두 가지 검색 엔진을 병행하고 결과를 합산한다.

| 검색 유형 | 엔진 | 용도 |
|-----------|------|------|
| **의미 검색** | LanceDB (벡터) | "인증 관련 로직", "상품 목록 필터링" 등 자연어 질의 |
| **정확 검색** | SQLite FTS5 | `handlePayment`, `UserService`, 파일 경로 등 정확한 식별자 |

### 5.2 질의 라우팅

Query Router가 질의 특성을 분석하여 경로를 결정한다.

```
질의 → Router
  ├── 정확한 식별자 패턴 (camelCase, path) → FTS5 우선
  ├── 자연어/개념 질의 → Vector 우선
  ├── 의존관계 질의 ("이 함수를 누가 호출?") → Graph Walk
  └── 복합 질의 → FTS5 + Vector 병합
```

### 5.3 랭킹

**MVP 단계 (Watchdog #4)**: FTS5 점수와 벡터 유사도를 단순 가중 합산으로 병합한다.
- `final_score = 0.4 * fts5_score_normalized + 0.6 * vector_similarity`

**향후 확장**: RRF(Reciprocal Rank Fusion) 도입은 실증 데이터 확보 후 결정한다. 단순 합산 대비 개선이 유의미한 경우에만 전환. Phase 2에서 Qdrant 도입 시 RRF(v1.17+)로 전환 권장.

### 5.4 Lean RAG (DB 위 검색 강화)

4AI(Claude opus, Codex GPT-5.4 x2, Gemini 2.5-pro) 합의에 따라, 별도 RAG 파이프라인을 두지 않고 기존 검색 레이어 위에 3가지 패턴만 추가한다.

**원칙**: LLM을 검색 경로에 넣지 않는다. 모든 패턴은 규칙 기반 + DB 쿼리로 동작한다.

| 패턴 | 방식 | 지연 | 비용 | 시기 |
|------|------|------|------|------|
| **Adaptive Retrieval** | Query Router — 질의 유형(심볼명/자연어/경로)을 규칙으로 분류하여 FTS/벡터/그래프 중 최적 경로 선택 | +1~5ms | $0 | Phase 1B |
| **Query Expansion** | 한/영 용어 맵 + camelCase/snake_case 분해 + 식별자 정규화. LLM 미사용. | +1~10ms | $0 | Phase 1B |
| **Multi-hop** | deps.graph를 따라 연쇄 검색. 수정 파일 → 영향받는 파일 자동 식별. depth 제한(기본 3). | +30~200ms | $0 | Phase 2 |

**도입하지 않는 기법** (4AI 전원 합의):
- HyDE: 코드 검색에서 가짜 심볼 생성 → precision 파괴
- LLM Re-ranking: <500ms 목표 깨뜨림, 투명성 훼손
- Contextual Compression: 청킹이 올바르면 불필요
- Adaptive (LLM 라우터): 규칙 기반으로 충분

> **핵심**: "RAG 시간의 70%를 청킹 품질에 투자하라" (4AI 공통 합의)

### 5.5 필터링

검색 결과에 메타데이터 필터를 적용한다.
- `project_id`: 멀티 워크스페이스 시 프로젝트 격리
- `file_type`: typescript, markdown, json 등
- `symbol_kind`: function, class, interface, type
- `freshness`: 최근 변경 파일 우선

---

## 6. AI 에이전트 통합

### 6.1 /sub 통합 (Context Block 자동 주입)

`/sub` 오케스트레이터가 하위 에이전트를 생성할 때, 해당 작업과 관련된 맥락을 자동으로 주입한다.

```
[오케스트레이터]
  │
  ├── 작업 설명에서 키워드 추출
  ├── Knowledge Index 검색 (상위 10건)
  ├── Context Block 생성
  │     ## Relevant Context (auto-injected)
  │     - src/services/PaymentService.ts: handlePayment() lines 45-80
  │     - docs/payment-flow.md: "결제 프로세스" 섹션
  │     - src/types/Payment.d.ts: PaymentRequest interface
  │
  └── 하위 에이전트 계약에 Context Block 삽입
```

이를 통해 하위 에이전트는 파일 탐색 없이 즉시 작업을 시작할 수 있다.

### 6.2 /submix 통합 (멀티엔진)

`/submix`에서 외부 엔진(Codex, Gemini)을 호출할 때 맥락 주입 방식이 달라진다.

| 엔진 | 주입 방식 |
|------|-----------|
| **Claude** | MCP tool 호출 → 실시간 검색 결과 반환 |
| **Codex (GPT)** | CLI 인자로 관련 파일 경로 전달, `--file` 플래그 활용 |
| **Gemini** | 대량 청크를 프롬프트에 직접 주입 (긴 컨텍스트 윈도우 활용) |

### 6.3 MCP Tool 인터페이스

Phase 2 이후 MCP 서버에 다음 도구를 노출한다.

```typescript
// MCP Tool: knowledge_search
{
  name: "knowledge_search",
  description: "워크스페이스 지식 인덱스에서 관련 코드/문서를 검색한다",
  inputSchema: {
    query: string,          // 검색 질의
    project_id?: string,    // 프로젝트 필터
    file_type?: string,     // 파일 타입 필터
    top_k?: number,         // 반환 개수 (기본 10)
  }
}

// MCP Tool: knowledge_status
{
  name: "knowledge_status",
  description: "인덱스 상태 및 신선도를 확인한다",
  inputSchema: {
    project_id?: string
  }
}
```

### 6.4 CLI Query 인터페이스

Codex 등 CLI 기반 에이전트를 위한 명령행 도구.

```bash
# 검색
npx wki search "결제 로직" --project shortlive --top 5

# 인덱스 상태
npx wki status

# 수동 인덱싱 트리거
npx wki index --incremental
```

---

## 7. 멀티 워크스페이스 설계

### Phase 1: 프로젝트별 완전 분리 (Watchdog #3)

```
workspace-root/
├── project-a/
│   └── .knowledge/
│       ├── file-map.json
│       ├── freshness.lock
│       ├── symbols.idx        (JSONL)
│       ├── deps.graph          (JSON)
│       ├── vectors.lance/      (LanceDB)
│       └── fts.db              (SQLite FTS5)
├── project-b/
│   └── .knowledge/
│       └── ...
└── .knowledge/
    └── workspace-meta/
        ├── cross-project-refs.json   ← 프로젝트 간 참조
        └── shared-types.idx          ← 공유 타입 인덱스
```

**핵심 원칙**: 각 프로젝트의 `.knowledge/`는 자립적이다. 해당 디렉토리를 삭제하면 그 프로젝트의 인덱스가 완전히 제거되고, 다른 프로젝트에 영향이 없다.

### Phase 2+: 서버화 시 단일 DB 전환

Qdrant 서버화 시점에 `project_id` 기반 컬렉션 분리로 전환한다. 프로젝트별 파일 시스템 분리는 유지하되, 벡터 검색은 중앙 서버를 통한다.

```
Qdrant Server
├── collection: project-a (768d vectors)
├── collection: project-b (768d vectors)
└── collection: shared    (크로스 프로젝트 참조)
```

---

## 8. 기존 시스템과의 관계

### MEMORY.md

MEMORY.md는 **의지와 방향성의 기록**이다. Knowledge Index는 **현실과 사실의 인덱스**이다. 두 시스템은 역할이 다르며 공존한다.

| 구분 | MEMORY.md | Knowledge Index |
|------|-----------|-----------------|
| 내용 | 사용자 선호, 프로젝트 방향, 결정 사항 | 코드 구조, 심볼, 의존관계 |
| 갱신 | 사용자/에이전트가 명시적으로 기록 | git 변경 시 자동 갱신 |
| 형식 | 자유 형식 Markdown | 구조화된 JSON/JSONL/DB |
| 수명 | 프로젝트 전체 수명 | 인덱싱 시점의 스냅샷 |

**통합 지점**: 에이전트는 작업 시작 시 MEMORY.md를 먼저 읽어 방향을 잡고, Knowledge Index로 구체적 맥락을 조회한다.

### MCP 서버 (mcp-server/)

기존 MCP 서버 구현 계획(`mcp-server/IMPLEMENTATION-PLAN.md`)과 Knowledge Index의 MCP Tool은 같은 서버에 통합된다. Knowledge Index는 MCP 서버의 **도구 중 하나**로 노출되며, 별도 서버를 띄우지 않는다.

### AGENTS.md

AGENTS.md의 역할(에이전트 행동 규약)은 변하지 않는다. Knowledge Index는 AGENTS.md가 참조하는 **인프라**로서, 에이전트가 규약을 지키면서 더 나은 맥락을 확보하도록 돕는다.

---

## 9. 구현 로드맵

### Phase 0 — 파일 맵 + 변경 감지 (1주)

**목표**: 인덱스 없이도 에이전트가 프로젝트 구조를 빠르게 파악할 수 있는 기반 마련.

| 산출물 | 설명 |
|--------|------|
| `file-map.json` | 전체 파일 트리 + 메타데이터 스냅샷 |
| `freshness.lock` | git commit hash 기반 변경 감지 |
| CLI: `wki init` | `.knowledge/` 초기화 및 최초 스캔 |
| CLI: `wki scan` | file-map 갱신 |

**완료 기준**: `wki init` 실행 후 `.knowledge/file-map.json` 생성, 구조 정보 확인 가능.

### Phase 1A — 심볼 인덱스 + 정확 검색 (2주)

**목표**: 코드 심볼을 추출하고 정확 검색(FTS5)으로 식별자를 찾을 수 있는 기반 구축.

| 산출물 | 설명 |
|--------|------|
| `symbols.idx` | JSONL 심볼 인덱스 (TS Compiler API) |
| `deps.graph` | JSON adjacency list 의존관계 |
| `fts.db` | SQLite FTS5 정확 검색 DB |
| CLI: `wki index` | 전체/증분 인덱싱 (FTS 한정) |

**기술 결정**:
- 파싱: TS → Compiler API, 비-TS → 단순 청킹 (Watchdog #1).
- 벡터 DB: 이 단계에서는 구축하지 않음. FTS5만으로 정확 검색 제공.

**fts.db 내부 스키마** (SQLite, better-sqlite3):

```sql
-- fts.db (SQLite, better-sqlite3)
-- FTS5 전문 검색 + 메타데이터

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- 청크 메타데이터 (FTS5 외부 content 소스)
CREATE TABLE chunks_meta (
  id          INTEGER PRIMARY KEY,
  file_path   TEXT NOT NULL,
  ordinal     INTEGER NOT NULL,
  heading     TEXT,
  chunk_type  TEXT,          -- "function" | "class" | "section" | "model"
  start_line  INTEGER,
  end_line    INTEGER,
  token_count INTEGER,
  content_hash TEXT,          -- SHA-256, 벡터 DB 동기화용
  UNIQUE(file_path, ordinal)
);

-- FTS5 전문 검색 (external content)
CREATE VIRTUAL TABLE chunks_fts USING fts5(
  content,
  heading,
  content='chunks_meta',
  content_rowid='id',
  tokenize='unicode61'
);

-- FTS5 동기화 트리거
CREATE TRIGGER chunks_meta_ai AFTER INSERT ON chunks_meta BEGIN
  INSERT INTO chunks_fts(rowid, content, heading)
  VALUES (new.id, new.content, new.heading);
END;

CREATE TRIGGER chunks_meta_ad AFTER DELETE ON chunks_meta BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, content, heading)
  VALUES ('delete', old.id, old.content, old.heading);
END;

CREATE TRIGGER chunks_meta_au AFTER UPDATE ON chunks_meta BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, content, heading)
  VALUES ('delete', old.id, old.content, old.heading);
  INSERT INTO chunks_fts(rowid, content, heading)
  VALUES (new.id, new.content, new.heading);
END;

-- 인덱스
CREATE INDEX idx_chunks_meta_path ON chunks_meta(file_path);
CREATE INDEX idx_chunks_meta_type ON chunks_meta(chunk_type);
CREATE INDEX idx_chunks_meta_hash ON chunks_meta(content_hash);
```

> 참고: `chunks_meta.content_hash`는 LanceDB/Qdrant의 벡터 레코드와 동기화하는 안정적 식별자 역할. SQLite rowid 재사용 문제를 방지.

**완료 기준**: `wki index` 실행 후 `symbols.idx`, `deps.graph`, `fts.db` 생성. 식별자 검색 동작 확인.

### Phase 1B — 벡터 검색 + 하이브리드 (2주)

**목표**: 임베딩 파이프라인을 구축하고 FTS5와 벡터 검색을 결합한 하이브리드 검색 제공.

| 산출물 | 설명 |
|--------|------|
| `vectors.lance/` | LanceDB 임베디드 벡터 저장소 |
| 임베딩 파이프라인 | 청크 → 임베딩 → LanceDB 저장 |
| CLI: `wki search` | 하이브리드 검색 (FTS5 + 벡터) |

**기술 결정**:
- 벡터 차원: 768d 기본 (Watchdog #2). 성능 부족 시 1024d 전환.
- 벡터 DB: LanceDB 임베디드 (Watchdog #5). 서버 불필요.
- 랭킹: FTS5 + 벡터 단순 가중 합산 (Watchdog #4).

**완료 기준**: `wki search "결제"` 실행 시 관련 코드/문서 반환, 증분 인덱싱 동작 확인.

### Phase 2 — /sub 통합 + Query Router (2주)

**목표**: AI 에이전트 워크플로우에 Knowledge Index를 자연스럽게 통합.

| 산출물 | 설명 |
|--------|------|
| Query Router | 질의 유형별 검색 경로 분기 |
| Context Block 생성기 | /sub 하위 에이전트용 맥락 자동 구성 |
| /sub 통합 훅 | 오케스트레이터가 에이전트 생성 시 자동 호출 |
| /submix 어댑터 | Codex(CLI), Gemini(청크 주입) 별 맥락 전달 |

**완료 기준**: `/sub` 실행 시 하위 에이전트 계약에 Context Block이 자동 삽입되고, 에이전트가 추가 탐색 없이 작업 수행.

### Phase 3 — MCP 도구 + 변경 저널 (2주)

**목표**: 실시간 맥락 접근과 변경 이력 추적.

| 산출물 | 설명 |
|--------|------|
| MCP `knowledge_search` tool | 실시간 의미 검색 |
| MCP `knowledge_status` tool | 인덱스 신선도 확인 |
| `change-journal.jsonl` | 변경 이력 스트림 (시간순) |
| 크로스 프로젝트 참조 | `workspace-meta/` 공유 인덱스 |

**완료 기준**: MCP 클라이언트에서 `knowledge_search` 호출 시 결과 반환, change-journal에 최근 변경 기록 확인.

---

## 10. 저장 공간 + 성능 추정

### 저장 공간

| 구성 요소 | 추정 크기 | 산출 근거 |
|-----------|-----------|-----------|
| file-map.json | ~500KB | 파일 메타데이터, 수천 개 엔트리 |
| symbols.idx | 2~5MB | JSONL, 심볼당 ~200바이트 x 수만 개 |
| deps.graph | 500KB~1MB | JSON adjacency list |
| LanceDB 벡터 | 30~60MB | 20,000 청크 x 768d x 4바이트 = ~58MB |
| FTS5 DB | 5~15MB | 전체 텍스트 + 역인덱스 |
| 로컬 임베딩 모델 (BGE-M3 ONNX) | ~2.3GB | 최초 다운로드, 이후 캐시 |
| **합계 (클라우드 임베딩)** | **40~80MB** | 프로젝트 소스(50~80MB) 대비 동급 |
| **합계 (로컬 임베딩)** | **~2.4GB** | BGE-M3 모델 포함 |

### 성능 추정

| 작업 | 소요 시간 | 비고 |
|------|-----------|------|
| 최초 전체 인덱싱 | 2~5분 | 파싱 + 임베딩 + 저장 |
| 증분 인덱싱 (소규모) | 1~5초 | 변경 파일 10개 미만, 파일당 ~100ms |
| 증분 인덱싱 (대규모) | 10~60초 | 리팩토링 등 100개 이상 변경 (Watchdog #6) |
| 검색 질의 | <500ms | 벡터 + FTS5 병합 기준 |
| Context Block 생성 | <1초 | 검색 + 포맷팅 |

### 비용 추정 (클라우드 임베딩 사용 시)

| 항목 | 비용 |
|------|------|
| 최초 인덱싱 (20,000 청크) | ~$0.05 (text-embedding-3-large, 768d) |
| 일일 증분 (평균 200 청크) | ~$0.001 |
| 월간 운영 | ~$0.05 |

로컬 임베딩(onnxruntime-node + BGE-M3) 사용 시 비용은 $0이며, 속도는 클라우드 대비 2~3배 느리나 오프라인 동작이 가능하다.

---

---

## 11. 에러 처리 및 복구

| 실패 유형 | 대응 |
|----------|------|
| 임베딩 API 호출 실패 | 2회 재시도 (exponential backoff) → 실패 청크 건너뛰기 + 경고 로그 |
| LanceDB/Qdrant 쓰기 실패 | 트랜잭션 롤백 → 마지막 유효 인덱스 유지 |
| 파싱 오류 (TS/MD) | 해당 파일 건너뛰기 + 경고 로그 (인덱스 전체 실패 방지) |
| 인덱싱 중단 (크래시) | freshness.lock 미갱신 → 다음 scan 시 전체 재인덱싱 |
| 인덱스 DB 손상 | `wki rebuild` 명령으로 전체 재구축 (파생 데이터이므로 복구 가능) |
| FTS5 DB 손상 | 동일 — `wki rebuild`로 재구축 |

### 동시성 제어

- SQLite FTS5: WAL 모드 활성화 (`PRAGMA journal_mode=WAL`)
- LanceDB: 단일 writer 보장 (file lock)
- 동시 인덱싱 방지: `.knowledge/.lock` 파일로 mutex
- 동시 검색: 읽기 전용이므로 제한 없음

---

## 12. 보안 고려사항

- **API 키**: 환경변수(`WKI_OPENAI_KEY`, `WKI_VOYAGE_KEY`)로 관리. config 파일에 직접 기재 금지
- **`.knowledge/` gitignore**: 벡터 데이터에 소스 코드 청크가 포함되므로, 공개 저장소에서는 `.gitignore`에 추가 권장
- **민감 파일 제외**: `.env`, `credentials.json`, `*.key` 등은 기본 exclude 패턴에 포함
- **외부 엔진 프롬프트**: /submix에서 Codex/Gemini에 검색 결과를 전달할 때 시크릿 포함 금지

---

*이 문서는 Claude opus(비전 아키텍처), Codex GPT-5.4(안정 스택), Gemini 2.5-pro(규모 전략)의 독립 분석 결과를 Watchdog 조정 사항에 따라 통합한 전략 설계서이다.*
