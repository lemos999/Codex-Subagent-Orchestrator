WKI 자동 인덱싱은 **3단계 흐름**으로 작동합니다:

## 1️⃣ **런처 시작 시 자동 감지 & 인덱싱** (`orchestrator.ts` 라인 298-301)

```
런처 실행
  ↓
detectWkiConfig() → .knowledge 디렉토리 감지
  ↓
ensureIndexFresh() → 증분 인덱싱 실행
  ↓
컨텍스트 주입 시작
```

## 2️⃣ **변경사항 감지** (`freshness.ts`)

**`FreshnessManager`**가 git을 쿼리해서 변경된 파일을 찾음:

```typescript
// 4가지 변경사항 감지
- Committed changes (마지막 인덱싱 이후 커밋)
- Unstaged changes (작업 중인 파일)
- Staged changes (스테이징 영역)
- Untracked files (새 파일)
```

마지막 인덱싱 상태는 `freshness.lock`에 저장됨 (commit hash, branch, staged/untracked fingerprint)

## 3️⃣ **증분 인덱싱** (`indexer.ts` 라인 271-534)

변경된 파일만 처리:

| 작업 | 상세 |
|------|------|
| **Deleted** | 벡터 스토어 + FTS DB에서 제거 |
| **Modified** | 기존 청크 삭제 후 재파싱, 임베딩 재생성 |
| **Added** | 새 파일 파싱, 청크 생성, 임베딩 생성 |
| **Renamed** | 기존 경로 삭제 + 새 경로 인덱싱 |

변경 없으면 → **0초** (프로세스 스킵)  
변경 있으면 → **수초~수십초** (모델 로드 + 임베딩)

## 🔍 **컨텍스트 주입 흐름**

```
Worker 태스크 텍스트
  ↓
expandQuery() → 한글→영문 키워드 확장
  ↓
WKI 검색 (FTS + 벡터) → top-K 청크 조회
  ↓
점수 필터링 (minScore 0.3) → 관련성 낮은 것 제외
  ↓
마크다운 포맷팅 → 워커 프롬프트 앞에 주입
```

---

**현재 상태** (메모리 기준):
- ✅ 멀티링구얼 모델 전환
- ✅ 런처 WKI 통합 & 증분 인덱싱 구현
- ⏳ 세션 종료 시 1회 실행 (아직 구현 안 됨)
- ⏳ Codex/Gemini 네이티브 오케스트레이터 연동 (아직)