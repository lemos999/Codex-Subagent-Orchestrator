# WKI 전략 설계서 — 4엔진 교차 검증 종합 보고서

> **실행일**: 2026-03-16
> **패턴**: parallel-reviewers (4엔진 독립 분석 → orchestrator 종합)
> **엔진**: Claude opus + Codex gpt-5.4 xhigh x2 + Gemini 2.5-pro

---

## 1. 엔진별 판정 교차 대조표

| 항목 | Claude opus | Codex #1 (스택) | Gemini (확장성) | Codex #2 (교차) | **합의** |
|------|:-----------:|:---------------:|:---------------:|:---------------:|:--------:|
| **4레이어 아키텍처** | ✅ | — | — | — | ✅ |
| **LanceDB beta** | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ |
| **SQLite FTS5** | ✅ | ✅ (실측) | ✅ | ✅ | ✅ |
| **TS Compiler API** | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ |
| **하이브리드 검색 가중치** | ⚠️ | ⚠️ | — | — | ⚠️ |
| **FTS5 스키마 (content 누락)** | — | ❌ | — | ❌ | **❌** |
| **증분 인덱싱 (git diff)** | ⚠️ | ❌ | — | ⚠️ | **❌** |
| **파일당 100ms 추정** | — | ❌ | — | — | **❌** |
| **비용 추정 ($0.05)** | — | — | ❌ | ❌ | **❌** |
| **Lean RAG 전략** | ✅ | — | ✅ | ✅ | ✅ |
| **크로스 프로젝트 설계** | ⚠️ | — | ⚠️ | ❌ | ⚠️~❌ |
| **로드맵 10주** | — | — | ⚠️ | ❌ | **❌** |
| **보안/운영** | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |

---

## 2. 4엔진 전원 합의: 즉시 수정 필요 항목 (Critical)

### C1. fts.db 스키마 — `chunks_meta.content` 컬럼 누락
- **Codex #1, #2 동시 발견**: 트리거가 `new.content`를 참조하나 DDL에 content 컬럼 없음
- **수정**: `chunks_meta`에 `content TEXT NOT NULL` 추가, 또는 단순 FTS5 테이블로 시작
- **추가**: FTS5 bareword 규칙 때문에 `src/services/payment.ts` 같은 경로 검색 깨짐 → path 검색은 B-tree 인덱스로 분리

### C2. 증분 인덱싱 — `git diff --name-only` 불충분
- **Codex #1 발견, Claude/Codex #2 보강**: rename 감지 불가, untracked/staged 변경 누락
- **수정**: `git diff --name-status -M` + `--cached` + `ls-files --others --exclude-standard` 조합
- **freshness.lock**: `head_commit + branch/ref + dirty flag + file hash fingerprint`로 확장

### C3. 비용 추정 과소평가
- **Gemini + Codex #2 동시 발견**: $0.05 → 실제 $0.39~$1.30 (초기), $0.16~$0.39/월
- **수정**: 낙관/중간/보수 3단계 비용표로 재작성
- **산출**: 20K 청크 × 300 tokens/chunk = 6M tokens × $0.13/1M = ~$0.78

### C4. 로드맵 일정 낙관
- **Gemini + Codex #2 합의**: 10주 → **12~14주**가 현실적
- Phase 1A: 2주 → 3주 (TS Compiler API + FTS 스키마 수정 + 테스트)
- Phase 2: 2주 → 3~4주 (/sub·/submix·query router·context packer)

### C5. 파일당 100ms 추정 부적절
- **Codex #1 발견**: 임베딩 포함 시 "청크 수"가 비용 결정. 1파일 5청크 → 수백ms
- **수정**: 추정 단위를 `ms/chunk + batch size`로 변경, FTS-only와 hybrid 분리

---

## 3. 다수 합의: 주의 필요 항목 (Important)

### I1. 하이브리드 검색 점수 정규화 미정의
- **Claude + Codex #1**: FTS5 bm25()는 "좋을수록 낮은 값", 벡터는 cosine similarity → raw 합산 왜곡
- **Codex 제안**: `fts_norm = minmax(log1p(-bm25))`, `vec_norm = (sim+1)/2`, top-50 union에서만 정규화
- **가중치**: query router 연동 동적 가중치 (identifier=0.7/0.3, NL=0.3/0.7)

### I2. LanceDB beta 리스크 관리
- **4엔진 합의**: 현재 선택은 적절하나 "production-stable"이 아닌 "embedded MVP backend"로 재정의
- **Codex**: GitHub ~9.5k stars, 공식 가이드는 50 QPS 이하 단일 머신 권장
- **제안**: backend adapter 인터페이스(`VectorBackend { insert, search, delete, rebuild }`)를 Phase 1A에서 확정

### I3. TS Compiler API 메모리/성능
- **Codex 실측 인용**: 694 files/751K lines → 4.32~4.47s, 633~810MB, tsserver 2GB+ 사례
- **제안**: 프로젝트 단위 Program 재사용, 메모리 상한, 대형 워크스페이스 분할 전략 문서화

### I4. file-map.json 확장성
- **Gemini + Codex #2**: 수만 파일에서 멀티-MB JSON → V8 힙 압박
- **제안**: 30K 파일 전후부터 NDJSON 또는 SQLite manifest로 전환

### I5. 크로스 프로젝트 검색
- **Codex #2**: workspace-meta/ JSON 중심 → parse/merge/update hotspot
- **Claude**: 내부 구조 미정의
- **제안**: federated search (프로젝트별 top-k 병렬 → RRF 병합)이 더 안전

### I6. 보안 보완
- **Claude**: SQL injection 방어(prepared statement), 로그 마스킹, 임베딩 벡터 유출 리스크
- **Codex #2**: subprocess env allowlist, FTS5 secure-delete 미설정 시 삭제 텍스트 잔류
- **Gemini**: pre-commit hook으로 .knowledge/ 실수 커밋 방지

### I7. 누락된 설계 요소
- **Claude**: 캐싱 전략, 테스트/품질 측정 프레임워크, 모니터링 메트릭
- **Codex #2**: atomic staging(`.knowledge/staging → atomic rename`), manifest 검증, integrity check, `status=healthy/degraded/stale`
- **Claude**: `.lock` 파일에 PID+타임스탬프, stale lock 자동 감지

---

## 4. 4엔진 전원 합의: 강점 (Strengths)

### S1. Lean RAG — 전원 ✅
- HyDE/LLM Re-ranking 배제는 코드 검색 도메인에서 **올바른 결정**
- "RAG 시간의 70%를 청킹 품질에 투자" 원칙 타당
- Query Expansion (camelCase 분해 + 한/영 용어 맵)은 FTS5 한계 보완에 실효적

### S2. 임베디드 우선 아키텍처 — 전원 ✅
- Docker/서버 없이 SQLite + LanceDB 파일만으로 즉시 시작
- `.knowledge/` 삭제로 완전 제거 — 비침습성 원칙 구현
- 1인 개발자 + AI 에이전트 워크플로우에 최적

### S3. 하이브리드 검색 설계 방향 — 전원 ✅
- FTS5(정확) + Vector(의미) 병행은 코드 검색의 양면을 커버
- Query Router 기반 경로 분기 설계 적절
- (가중치/정규화는 보완 필요하나 방향 자체는 합의)

### S4. TS Compiler API 선택 — 전원 ✅
- 심볼/타입/export/import 정확도에서 tree-sitter 대비 우위
- TS-heavy 워크스페이스에서 최적 선택
- 비-TS는 줄 기반 폴백으로 합리적 이원화

---

## 5. 실측 데이터 (Codex gpt-5.4 xhigh)

### SQLite FTS5 벤치마크 (Node 24.13.1, 20,000 docs)
| Query Type | p50 (ms) | p95 (ms) |
|------------|----------|----------|
| Identifier (`handlePayment`) | **1.0** | 1.0 |
| Multi-token (`auth token session`) | **9.9** | 10.1 |
| Insert 20,000 rows | **235ms** | — |

### 벡터 선형 스캔 (Pure JS, 20,000 × 768d)
| p50 (ms) | p95 (ms) |
|----------|----------|
| **16.2** | 20.0 |

**결론**: DB 조회만이면 검색 <500ms는 **충분히 달성 가능**. 클라우드 query embedding 포함 시 빡빡할 수 있으므로 SLO 분리 권장.

---

## 6. 로드맵 재추정 (4엔진 합의)

| Phase | 원래 | 재추정 | 핵심 근거 |
|-------|:----:|:------:|-----------|
| 0 | 1주 | **1~1.5주** | dirty worktree, path normalization, ignore rules |
| 1A | 2주 | **3주** | TS Compiler API + FTS 스키마 수정 + 테스트 |
| 1B | 2주 | **2.5~3주** | 임베딩 adapter, 배치/재시도, fusion tuning |
| 2 | 2주 | **3~4주** | /sub·/submix·query router·context packer |
| 3 | 2주 | **2.5~3주** | MCP 먼저, journal/workspace-meta 후속 분리 |
| **총합** | **10주** | **12~14주** | 1인 + AI 보조 기준 |

---

## 7. 최종 판정

> **방향은 올바르고 아키텍처는 견고하다. 수치·일정·운영 가정을 보수적으로 재조정하면 즉시 Phase 0 구현을 시작할 수 있는 수준이다.**

### 즉시 조치 (Phase 0 시작 전)
1. `chunks_meta.content TEXT NOT NULL` 추가 (DDL 수정)
2. `git diff` → `--name-status -M` + untracked 조합으로 변경
3. 비용표를 3단계(낙관/중간/보수)로 재작성
4. 성능 추정 단위를 ms/chunk로 변경
5. 로드맵 10주 → 12~14주로 조정

### Phase 1A 시작 전
6. `VectorBackend` / `EmbeddingProvider` 인터페이스 확정
7. FTS5 경로 검색 → B-tree 인덱스 분리
8. 하이브리드 검색 점수 정규화 방법 확정
9. 테스트/품질 평가 프레임워크 설계

---

## 엔진별 토큰 사용량

| Engine | Model | Tokens |
|--------|-------|--------|
| Claude | opus | ~39,922 |
| Codex #1 (stack) | gpt-5.4 xhigh | 456,723 |
| Gemini | 2.5-pro | — |
| Codex #2 (scale) | gpt-5.4 xhigh | 354,358 |
