WKI 자동 인덱싱이 이 프로젝트에서 어떻게 작동하는지 설명해 드리겠습니다. 먼저 WKI 관련 파일들을 조사하여 전반적인 구현 방식을 파악하겠습니다. 특히 `workspace-knowledge-index` 디렉토리와 `packages/launcher/src/supervisor/wki-context.ts` 파일을 중점적으로 살펴보겠습니다.

먼저 `workspace-knowledge-index` 디렉토리 내에서 "index" 및 "WKI" 키워드로 검색을 시작하겠습니다.
`grep_search` 결과 중요한 단서들을 얻었습니다.

1.  **`wki.config.json`**: 이 파일은 WKI 구성을 정의하는 것으로 보이며, `index_root: ".knowledge"` 및 `indexing` 섹션이 포함되어 있습니다. 이는 자동 인덱싱 동작이 구성되는 곳일 가능성이 높습니다.
2.  **`tests/core/indexer-incremental.test.ts`**: 이 파일은 "Indexer incremental"을 명시적으로 언급하고 `indexer.indexFull()` 및 `indexer.indexIncremental()`에 대한 테스트를 포함합니다. 이는 증분 인덱싱 메커니즘이 있음을 강력히 시사합니다.
3.  **`tests/mcp/server.test.ts`**: 이 파일도 `index_root: '.knowledge'` 및 `indexed_at`를 참조하며, 이는 마지막 인덱싱 타임스탬프를 나타냅니다. 또한 인덱스가 없을 때의 상태 확인에 대한 테스트도 포함되어 있어 관리형 인덱싱 프로세스를 더욱 명확히 합니다.
4.  **`.knowledge` 디렉토리**: 이 디렉토리는 `index_root`로 일관되게 참조되며, 이는 WKI가 인덱싱된 데이터(예: FTS.db)를 저장하는 곳임을 의미합니다.
5.  **`src/core/indexer.ts`**: 테스트 파일은 `src/core/indexer.ts`를 인덱싱의 주요 구성 요소로 지적합니다.

이를 바탕으로 다음과 같은 계획을 세울 수 있습니다.
1.  주요 구성을 이해하기 위해 `workspace-knowledge-index/wki.config.json`을 읽습니다.
2.  인덱싱(전체 및 증분)이 어떻게 구현되는지 이해하기 위해 `workspace-knowledge-index/src/core/indexer.ts`를 읽습니다.
3.  컨텍스트 삽입을 위해 WKI가 감독자에 어떻게 통합되는지 확인하기 위해 `packages/launcher/src/supervisor/wki-context.ts`를 읽습니다.

`wki.config.json`을 먼저 읽겠습니다.
`wki.config.json`에서 WKI 자동 인덱싱에 대한 다음과 같은 주요 정보를 얻을 수 있습니다:

*   **`projects`**: 지식 기반에 포함될 디렉토리를 정의합니다. 여기서는 `root: "."`인 `my-project`가 프로젝트 디렉토리 전체를 인덱싱한다는 의미입니다. 또한 인덱싱 중에 특정 파일/폴더를 무시하도록 `exclude` 패턴(`node_modules`, `dist`, `.next`, `dev.db`)을 지정합니다.
*   **`storage`**:
    *   `index_root: ".knowledge"`: 인덱싱된 데이터(FTS 데이터베이스, 벡터 저장소)가 프로젝트 루트 내의 `.knowledge` 디렉토리에 저장됨을 확인합니다.
    *   `vector_backend`: `lancedb`로 구성되어 있으며, 벡터 임베딩을 저장하기 위한 `vectors.lance` 경로를 가리킵니다. 이는 시맨틱 검색을 위해 콘텐츠가 임베딩됨을 나타냅니다.
*   **`embedding`**: 임베딩 제공자(이 구성에서는 `local`)와 벡터 임베딩 생성에 사용되는 모델(예: `Xenova/paraphrase-multilingual-MiniLM-L12-v2`)을 지정합니다.
*   **`chunking`**: 파일을 더 작고 관리하기 쉬운 "청크"로 분할하는 방법(`max_lines`, `overlap_lines`, `max_tokens`)을 정의합니다. 이는 효율적인 검색에 매우 중요합니다.
*   **`indexing`**:
    *   `concurrency`: 4로, 인덱싱 중에 4개의 파일을 동시에 처리할 수 있음을 의미합니다.
    *   `max_file_size_mb`: 10MB보다 큰 파일은 건너뜁니다.
    *   `follow_gitignore`: `true`로, `.gitignore` 규칙을 준수하여 무시된 파일의 불필요한 인덱싱을 방지합니다.
    *   `timeout_ms`: 파일당 30초 타임아웃.
    *   `retry`: 인덱싱 실패에 대해 2번 재시도.
*   **`search`**: FTS(Full-Text Search) 데이터베이스(`fts.db`) 경로와 FTS 및 벡터 검색 결과를 결합하는 `fusion` 전략을 지정합니다.

이제 인덱싱 로직, 특히 증분 인덱싱을 이해하기 위해 `workspace-knowledge-index/src/core/indexer.ts`를 살펴보겠습니다.
`workspace-knowledge-index/src/core/indexer.ts`의 `Indexer` 클래스는 WKI 자동 인덱싱 프로세스의 핵심입니다. 전체 인덱싱 및 증분 인덱싱과 관련된 기능은 다음과 같습니다.

**핵심 구성 요소:**

*   **`Indexer` 클래스**: 전체 인덱싱 프로세스를 오케스트레이션합니다. 구성(프로젝트 ID, 루트, 지식 디렉토리, 제외 패턴), 선택적 임베딩 공급자, 벡터 저장소 및 FTS 데이터베이스 경로를 받습니다.
*   **파서**:
    *   `Scanner`: `excludePatterns` 및 구성된 경우 `.gitignore`(`wki.config.json`의 `follow_gitignore: true`)를 준수하며 인덱싱할 파일을 찾기 위해 파일 시스템을 스캔합니다. `max_file_size_mb`를 초과하는 파일은 건너뜁니다.
    *   `TsParser`: TypeScript/JavaScript 파일용으로 특별히 설계되었으며, 프로그램 수준 정보(심볼, 임포트, 청크)를 파싱할 수 있습니다. 먼저 TS/JS 파일을 파싱하려고 시도합니다. `TsParser`가 실패하면 `LineParser`로 대체합니다.
    *   `MdParser`: Markdown 파일용.
    *   `LineParser`: 파일을 줄 단위로 청크하는 일반 파서입니다. `TsParser` 또는 `MdParser`로 처리되지 않는 파일에 사용됩니다.
*   **저장소**:
    *   `FtsStore`: FTS(Full-Text Search) 데이터베이스(`fts.db`)를 관리하고 청크 메타데이터를 저장합니다.
    *   `VectorBackend`(예: LanceDB, Qdrant): 청크의 벡터 임베딩을 저장하여 시맨틱 검색을 가능하게 합니다.
*   **`EmbeddingProvider`**: 구성된 모델(예: `Xenova/paraphrase-multilingual-MiniLM-L12-v2`)을 사용하여 청크 콘텐츠에서 벡터 임베딩을 생성합니다.
*   **`DepsGraphImpl`**: 코드에서 찾은 임포트를 기반으로 종속성 그래프(`deps.graph`)를 빌드하고 관리합니다.
*   **`symbols.idx`**: JSONL 형식으로 코드에서 추출된 심볼을 저장하는 파일.

**전체 인덱싱 (`indexFull()`):**

1.  **파일 스캔**: `Scanner`는 `projectRoot` 내의 모든 파일을 식별하고, 제외 패턴과 `.gitignore`를 준수합니다. `max_file_size_mb`를 초과하는 파일은 건너뜁니다.
2.  **파싱**:
    *   TypeScript/JavaScript 파일은 `TsParser`를 사용하여 먼저 파싱되어 프로그램 수준에서 청크, 심볼 및 임포트를 추출합니다.
    *   Markdown 파일은 `MdParser`로 파싱됩니다.
    *   다른 파일은 `LineParser`를 사용하여 파싱됩니다.
    *   파일은 `chunking` 구성(`max_lines`, `overlap_lines`, `max_tokens`)에 따라 청크됩니다.
3.  **FTS 저장소(원자적 스왑)**:
    *   청크는 *스테이징* FTS 데이터베이스(`.wki-staging-fts.db`)에 삽입됩니다.
    *   성공적인 삽입 후, 스테이징 데이터베이스는 라이브 FTS 데이터베이스(`fts.db`)와 *원자적으로 스왑*됩니다. 이는 FTS 인덱스가 항상 일관된 상태를 유지하고 전체 재인덱스 중에 다운타임 또는 손상된 검색 결과를 방지합니다.
4.  **임베딩 및 벡터 저장소**:
    *   `embeddingProvider` 및 `vectorStore`가 구성된 경우, 프로젝트의 기존 벡터가 지워지고 모든 청크에 대해 새로운 임베딩이 생성됩니다.
    *   이러한 임베딩과 해당 청크는 `vectorStore`(예: LanceDB)에 삽입됩니다.
5.  **심볼 및 종속성 그래프 저장소**: 추출된 심볼은 `symbols.idx`에 저장되고, 종속성 그래프는 빌드되어 `deps.graph`에 저장됩니다.

**증분 인덱싱 (`indexIncremental()`):**

이것은 파일 변경 사항만 처리하여 지식 기반을 효율적으로 최신 상태로 유지하는 "자동 인덱싱" 측면입니다.

1.  **입력**: `added`, `modified`, `deleted`, `renamed` 파일 목록을 포함하는 `ChangedFiles` 객체를 받습니다.
2.  **기존 데이터 로드**: `symbols.idx`에서 기존 심볼을 로드하고 `deps.graph`에서 종속성 그래프를 로드합니다.
3.  **삭제된 파일 처리**:
    *   삭제된 파일과 관련된 청크는 FTS 데이터베이스에서 제거됩니다.
    *   `vectorStore`가 구성된 경우, 해당 벡터 임베딩도 삭제됩니다.
    *   삭제된 파일과 관련된 심볼은 `existingSymbols`에서 필터링됩니다.
4.  **추가/수정/이름 변경된 파일 처리**:
    *   이름이 변경된 파일의 경우, 이전 파일 경로의 청크 및 벡터는 먼저 삭제됩니다.
    *   추가, 수정 및 이름이 변경된 파일(`to` 경로)은 모두 처리됩니다.
    *   이러한 파일의 기존 청크는 FTS 데이터베이스에서 제거됩니다.
    *   파일은 파싱(TsParser, MdParser 또는 LineParser 사용)되어 새로운 청크, 심볼 및 임포트를 생성합니다.
    *   이러한 새로운 청크는 일관성을 유지하기 위해 단일 트랜잭션 내에서 FTS 데이터베이스에 삽입됩니다.
    *   `vectorStore`가 구성된 경우, 새/수정된 청크에 대해 새로운 임베딩이 생성되어 `vectorStore`에 삽입됩니다.
5.  **메타데이터 업데이트**:
    *   `symbols.idx` 파일은 새로운 심볼 세트(기존 유지된 심볼 + 처리된 파일의 새 심볼)로 업데이트됩니다.
    *   `deps.graph`는 새로운 임포트 정보로 업데이트됩니다.
6.  **효율성**: FTS 업데이트에 트랜잭션을 사용하고 변경된 파일만 처리함으로써 증분 인덱싱은 WKI를 최신 상태로 유지하는 데 필요한 리소스와 시간을 최소화합니다.

**자동 인덱싱 흐름 요약:**

WKI는 `Indexer`를 사용하여 지식 기반을 유지합니다. 전체 프로젝트를 완전히 인덱싱하거나 파일 변경을 기반으로 증분 인덱싱을 수행할 수 있습니다. 증분 인덱싱은 파일 시스템 변경을 감지하여 트리거됩니다. 변경이 발생하면:

1.  **파일 시스템 모니터링(암시적)**: `Indexer.ts`에 명시적으로 없지만, 상위 수준 프로세스(아마도 `launcher` 패키지 또는 지속적인 통합 시스템 내)는 파일 시스템 변경을 모니터링합니다.
2.  **변경 감지**: 추가, 수정, 삭제 또는 이름이 변경된 파일을 식별합니다.
3.  **증분 인덱스 호출**: `indexIncremental` 메서드가 이러한 `ChangedFiles`와 함께 호출됩니다.
4.  **저장소 업데이트**: `Indexer`는 오래된 정보를 제거하고 새/수정된 데이터를 추가하여 FTS 데이터베이스, 벡터 저장소, 심볼 인덱스 및 종속성 그래프를 효율적으로 업데이트합니다.

마지막으로, `packages/launcher/src/supervisor/wki-context.ts`를 검토하여 이 인덱싱 메커니즘이 컨텍스트 주입에 어떻게 통합되고 사용되는지 확인하겠습니다.
`packages/launcher/src/supervisor/wki-context.ts` 파일을 읽었습니다. 이 프로젝트에서 WKI 자동 인덱싱 및 컨텍스트 주입이 어떻게 작동하는지에 대한 내용은 다음과 같습니다.

**`packages/launcher/src/supervisor/wki-context.ts` - WKI 컨텍스트 주입**

이 파일은 시스템(특히 에이전트 상호 작용을 조율할 가능성이 있는 `launcher` 패키지)이 WKI를 *사용하는 방법*을 이해하는 데 중요합니다. 이 파일은 작업자 프롬프트에 WKI 컨텍스트를 주입하는 흐름을 설명합니다.

**WKI 컨텍스트 주입의 전반적인 흐름:**

1.  **자동 증분 인덱싱(최신 상태가 아닌 경우)**: 검색을 시작하기 전에 시스템은 WKI가 최신 상태인지 먼저 확인합니다.
2.  **작업자 작업/프롬프트 → 검색 쿼리 추출**: 작업자의 작업 또는 프롬프트에서 검색 쿼리가 추출됩니다.
3.  **WKI 검색 → 상위 K개의 관련 코드/문서 청크**: 검색 쿼리를 기반으로 WKI에서 관련 코드/문서 청크를 쿼리합니다.
4.  **"## Relevant Context (auto-injected)" 마크다운 형식으로 지정**: 검색된 청크는 마크다운 블록으로 서식 지정됩니다.
5.  **작업자 프롬프트 앞에 추가**: 이 마크다운 컨텍스트는 AI 엔진(Claude, Codex, Gemini 등)으로 전송되기 전에 작업자 프롬프트 앞에 추가됩니다.

**주요 기능 및 메커니즘:**

*   **`detectWkiConfig(workspaceRoot: string)`**:
    *   이 함수는 WKI가 작업 공간에 설정되었는지 자동으로 감지합니다.
    *   `.knowledge` 디렉토리와 FTS 데이터베이스 파일(`.db` 또는 `fts.db`)의 존재 여부를 확인합니다.
    *   또한 `wki.config.json`에서 `projectId`를 로드하려고 시도합니다.
    *   WKI가 감지되면 `WkiContextConfig` 객체를 반환하고, 그렇지 않으면 `null`을 반환합니다. 이 구성에는 `knowledgeDir`, `projectId` 및 `topK`(검색할 관련 청크 수) 및 `maxContentLines`(주입된 컨텍스트의 청크당 최대 줄 수)에 대한 기본값이 포함됩니다.
*   **`ensureIndexFresh(config: WkiContextConfig)`**:
    *   이것은 **자동 인덱싱** 메커니즘의 핵심입니다.
    *   *런처 호출당 한 번*, *검색 전에* 호출됩니다.
    *   자식 프로세스에서 WKI CLI 명령(`node workspace-knowledge-index/dist/index.js index`)을 실행합니다.
    *   결정적으로, 이 `wki index` 명령은 내부적으로 `freshness.lock`을 확인합니다. 인덱스가 이미 최신 상태인 경우 즉시 반환됩니다. 변경 사항이 있는 경우, ( `Indexer.ts`에 설명된 대로) *증분 인덱스*를 수행하여 모델을 로드하고 변경된 파일만 다시 임베딩합니다.
    *   이 프로세스는 치명적이지 않도록 설계되었습니다. 자동 인덱싱이 실패하더라도 컨텍스트 주입은 건너뛰지만 주 작업은 계속 진행됩니다.
*   **`expandQuery(query: string)`**:
    *   다국어 검색, 특히 한국어-영어 키워드 확장을 처리합니다.
    *   쿼리에 한글 문자가 포함된 경우, 문서가 영어로 되어 있을 때 검색 관련성을 향상시키기 위해 `KO_EN_KEYWORDS` 매핑에서 영어 키워드를 추가하려고 시도합니다.
*   **`generateContext(query: string, config: WkiContextConfig)`**:
    *   이 함수는 WKI에서 실제 검색을 수행하고 컨텍스트 마크다운을 생성합니다.
    *   `workspace-knowledge-index/dist/context/sub-hook.js`에서 `generateAgentContext` 함수를 동적으로 가져옵니다. 이는 엄격한 종속성을 피하고 유연한 로드를 허용합니다.
    *   확장된 쿼리와 WKI 구성( `ftsDbPath`, `embeddingConfig`, `storageConfig`, `searchConfig`, `contextOptions` 포함)을 `generateAgentContext` 함수에 전달합니다.
    *   특정 관련성 점수(`minScore`) 이상의 검색된 청크만 필터링하여 관련 없는 컨텍스트 주입을 방지합니다. 이는 임베딩 모델이 어려움을 겪을 수 있는 교차 언어 검색에 특히 중요합니다.
    *   그런 다음 파일 경로, 줄 범위 및 청크 콘텐츠를 포함하여 관련 컨텍스트에 대한 마크다운 문자열을 구성합니다.
*   **`injectContextIntoPrompt(prompt: string, context: WkiContextResult)`**:
    *   생성된 컨텍스트 마크다운을 원래 작업자 프롬프트 앞에 간단히 추가합니다.

**이 프로젝트에서 WKI 자동 인덱싱이 작동하는 방식:**

1.  **구성**: `wki.config.json` 파일은 프로젝트의 인덱싱 동작(포함/제외할 파일, 청크 전략, 임베딩 모델, `.knowledge` 디렉토리와 같은 저장 위치 등)을 정의합니다.
2.  **감지**: `launcher` (또는 `wki-context.ts`를 사용하는 모든 구성 요소)가 시작되면 `detectWkiConfig`가 호출되어 WKI가 현재 작업 공간에 구성되고 활성화되어 있는지 확인합니다.
3.  **최신 상태 확인 및 증분 인덱싱**: WKI가 활성화되면 `ensureIndexFresh`가 호출됩니다. 이 함수는 `wki index` CLI 명령을 실행합니다. 이 명령은 `Indexer` 클래스(`workspace-knowledge-index/src/core/indexer.ts`)에 의해 구동되며 다음을 수행합니다.
    *   `freshness.lock`(이 코드에서는 명시적으로 보이지 않지만 `Indexer`의 증분 논리와 CLI 설명에 의해 암시됨)을 참조하여 마지막 인덱싱 이후 변경된 파일이 있는지 확인합니다.
    *   변경 사항이 감지되면(추가, 수정, 삭제, 이름 변경된 파일), *증분 인덱스*를 효율적으로 수행합니다. 여기에는 변경된 파일만 파싱하고, FTS 데이터베이스를 업데이트하고, 새/수정된 청크에 대한 벡터 임베딩을 생성 및 업데이트하고, 심볼 및 종속성 그래프를 업데이트하는 작업이 포함됩니다.
    *   변경 사항이 감지되지 않으면 아무것도 하지 않고 빠르게 반환됩니다.
4.  **컨텍스트 생성**: 작업자가 프롬프트를 처리해야 할 때 `generateContext`가 호출됩니다.
    *   쿼리에 한글 문자가 포함된 경우 사용자 쿼리에 영어 키워드를 추가할 수 있습니다.
    *   그런 다음 WKI의 `generateAgentContext` 함수를 사용하여 검색( `wki.config.json`에 구성된 대로 FTS 및 벡터 검색 결합)을 수행합니다.
    *   특정 관련성 점수(`minScore`) 이상의 청크만 선택됩니다.
5.  **컨텍스트 주입**: 선택된 관련 청크는 마크다운 블록으로 서식 지정되고 `injectContextIntoPrompt`는 이 블록을 작업자 프롬프트 앞에 추가합니다. 이는 AI 작업자가 작업을 시작하기 전에 프로젝트의 특정 컨텍스트를 더 효과적으로 이해하고 작동할 수 있도록 관련성 높고 최신 컨텍스트 스니펫을 제공합니다.

본질적으로 WKI는 프로젝트의 코드 및 문서에 대한 지속적으로 업데이트되는 지식 기반을 제공합니다. 자동 인덱싱은 이 지식이 최신 상태임을 보장하며, 컨텍스트 주입 메커니즘은 AI 작업자에게 관련 스니펫을 자동으로 제공하여 프로젝트의 특정 컨텍스트 내에서 더 효과적으로 이해하고 작동할 수 있도록 합니다.

WKI 자동 인덱싱에 대한 설명을 마쳤습니다.