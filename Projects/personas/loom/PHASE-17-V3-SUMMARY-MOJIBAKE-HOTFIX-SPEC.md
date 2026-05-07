# Phase 17 V3 SUMMARY mojibake hotfix — raw 재합성 + 한국어 expected token check

> **긴급도**: 중간 (보고서 가독성 이슈, V3 anchor 무영향, 회귀 위험 0)
> **선행 조건**: 980df43 (DC-2 rev.3 hotfix) + 6b7800e (잔여 spec 정합)
> **작업 유형**: **인프라** (인코딩 정정 / raw 재합성. raw 데이터 / mechanism / charter 본문 / acceptance 무수정)
> **DB migration**: 없음
> **외부 의존**: 없음 (Python 표준 라이브러리만 — `json`, `pathlib`, `hashlib`)
> **canonical order**: [PHASE-17-NATION-PHASE3-SPEC-PIPELINE-DRAFT.md](PHASE-17-NATION-PHASE3-SPEC-PIPELINE-DRAFT.md) §0 표 4번 (DC-2 본 흐름과 독립 병행 가능)
> **rev**: **rev.2** (1차 spec-review MAJOR-1 + MINOR-1 반영 — mojibake 검증 일반 패턴 격상 + raw byte hash git diff 통합)

---

## 변경 이력

- **rev.2** (2026-05-05): 1차 spec-review (supervisor 단독, opus, A1+B1) 검토 결과 반영:
  1. **MAJOR-1**: mojibake 8 시그니처 중 3개 (`理쒕`, `寃걚`, `�`) 실제 파일 0건 vacuous, 5개도 16 CJK ideograph 중 일부만 커버 → §4 + §8-3을 **일반 패턴**으로 격상 — `[一-鿿豈-﫿]` (CJK + Compatibility) 0건 + `\?[가-힣]` (?+한글) 0건. 8 시그니처 표는 §배경 illustrative examples로만 유지.
  2. **MINOR-1**: §8-4 raw byte hash 검증 절차 혼재 ("실행 전후" vs "git HEAD 비교") → `git diff --stat HEAD -- <raw 12 파일>` 1줄로 통합. §8-5와 일관.
- **rev.1** (2026-05-05): 정리안 v2 기반 spec 본문 신규 작성. Codex 사전 리뷰 6 권고 모두 반영:
  1. `metrics.jsonl` 필수 입력 승격 (canonical: population/contact/uprising/wealth/grievance_targets/source_cumulative)
  2. 검증 이중 trick — "raw 재계산 가능 수치는 raw 기준" + "raw 미존재(경과 시간)는 원본 mojibake 보존 또는 N/A"
  3. 분위수 토큰 자연 삽입 1문장 (강제 표 X)
  4. mojibake grep 시그니처 구체화 (`?` 단독 X, 8 구체 조각)
  5. `.mojibake.bak.md` 보존 [선택] → [필수] 승격
  6. 회귀 6종 [필수] → [선택] 격하, 정적 무영향 검증을 [필수]로 승격

---

## 배경

V3 probe 산출물 [data/phase17_probe_phi3-case-c-diagnosis-v3/](data/phase17_probe_phi3-case-c-diagnosis-v3/) 내 **Markdown 4 파일**의 한글 본문이 mojibake (CP949 ↔ UTF-8 디코딩 오류) 상태:

| 파일 | mojibake 영향 |
|---|---|
| [SUMMARY.md](data/phase17_probe_phi3-case-c-diagnosis-v3/SUMMARY.md) | top-level 종합 보고서, 한글 본문 깨짐 |
| [seed-7/summary.md](data/phase17_probe_phi3-case-c-diagnosis-v3/seed-7/summary.md) | seed별 보고, 한글 라벨 깨짐 |
| [seed-13/summary.md](data/phase17_probe_phi3-case-c-diagnosis-v3/seed-13/summary.md) | 동일 |
| [seed-42/summary.md](data/phase17_probe_phi3-case-c-diagnosis-v3/seed-42/summary.md) | 동일 |

**mojibake 패턴 실증 (examples — illustrative. 정확한 검증은 §8-3 일반 패턴 사용)**:

| 깨진 형태 (예시) | 원래 한글 |
|---|---|
| `過-3` | `Φ-3` |
| `?ㅽ뻾 ?붿빟` | `실행 요약` |
| `?쒖옉 faction` | `시작 faction` |
| `理쒕? ?뚯냽 ?몄썝` | `최대 소속 인원` (실제 파일 `理`는 U+F9E4 호환 ideograph) |
| `洹좊벑??` | `균등도` |
| `湲곗?` | `기준` |
| `寃곌낵` / `寃쏀` / `寃쎄` | `결과` 등 다양 (`寃`+여러 한글 syllable) |
| `?`+한글 일반 | CP949↔UTF-8 round-trip 손실 패턴 |

> **NOTE**: 본 표는 examples이며, 검증 §8-3는 8 시그니처 hard-list가 아닌 **일반 패턴** (`[一-鿿豈-﫿]` CJK + `\?[가-힣]` ?+한글) 0건을 사용한다. 1차 spec-review에서 8 시그니처 hard-list 5/8 vacuous + 미커버 CJK ideograph 12종 발견.

**raw 데이터 안전 (mojibake 0건)** — 영문 키만:

| 파일 | 상태 | 본 spec 사용 |
|---|---|:---:|
| `seed-{7,13,42}/case_c_events.json` | ✅ ASCII only (영문 키) | ✅ |
| `seed-{7,13,42}/chain.json` | ✅ ASCII only | ✅ (보조) |
| `seed-{7,13,42}/snn_output_events.json` | ✅ ASCII only | ✅ |
| `seed-{7,13,42}/metrics.jsonl` | ✅ ASCII only | ✅ **canonical** (Codex 권고) |

**채택 옵션**: A (raw 재합성). 근거 — V3 anchor 무영향 + 결정적 + probe 재실행 봉인 (V3 anchor 깨짐 위험 회피).

---

## 작업 범위

### [필수] 8종

1. **`Projects/personas/loom/scripts/phase17_v3_summary_regen.py` 신규 작성**
   - 입력: 4 raw 카테고리 (case_c_events.json + chain.json + snn_output_events.json + **metrics.jsonl**) × 3 seed
   - 입력 보조: 원본 mojibake SUMMARY 4개 (raw 미존재 수치 — 경과 시간 — 인용용)
   - 출력: 4 새 SUMMARY (UTF-8) + 4 `.mojibake.bak.md` (원본 보존)
   - 결정적 (idempotent): 동일 raw → 동일 SUMMARY (2회 실행 시 byte-level diff 0)
   - 단일 진입점: `python scripts/phase17_v3_summary_regen.py`

2. **`.mojibake.bak.md` 4개 보존 contract**
   - 위치: 원본 SUMMARY와 같은 디렉토리, 이름은 `<원본 stem>.mojibake.bak.md`
     - `data/phase17_probe_phi3-case-c-diagnosis-v3/SUMMARY.mojibake.bak.md`
     - `data/phase17_probe_phi3-case-c-diagnosis-v3/seed-{7,13,42}/summary.mojibake.bak.md`
   - 내용: 원본 mojibake bytes 그대로 (디코딩 시도 0). 어떤 인코딩이든 byte-for-byte 보존.
   - 목적: 형사 증거 — 나중에 "수치가 어디서 왔는가" 추적 시 원본 대조 가능.

3. **새 SUMMARY 한국어 expected token check (10 토큰 + 분위수 자연 삽입 1문장)**

   각 새 SUMMARY 4개에 다음 토큰 **모두 등장** 검증:
   - `Φ-3`
   - `실행 요약`
   - `시작 faction 수`
   - `활성 faction 수`
   - `결과`
   - `기준`
   - `균등도`
   - `최대 소속 인원`
   - `Source 비율` (또는 `소스 비율`)
   - `종합 판정`

   분위수 자연 삽입 (강제 표 X) — top-level `SUMMARY.md`에만 1회 등장:
   > 주의: 본 V3 SUMMARY는 분위수 산출물이 아니며, DC-1/DC-2 분위수 산출물의 입력 raw 상태를 설명한다.

   누락 시 즉시 FAIL.

4. **mojibake 일반 패턴 grep 0건 검증 (regex 2 종)**

   새 SUMMARY 4개 (`.mojibake.bak.md` 제외)에서 다음 2 일반 패턴 **0건**:
   - **CJK ideographs**: `[一-鿿豈-﫿]` (CJK Unified + Compatibility Ideographs). 한국어 보고서는 한자 미사용 가정 — 단 `Φ-3`(Greek phi)·`%`·`≥` 등은 한글/ASCII 범위라 OK.
   - **? + 한글**: `\?[가-힣]` (CP949↔UTF-8 round-trip 손실의 가장 일반적 표지).

   (NOTE: 본 일반 패턴은 1차 spec-review에서 8 시그니처 hard-list 5/8 vacuous 발견 후 격상. 8 시그니처는 §배경 illustrative만.)

5. **raw 4 카테고리 byte hash 0 diff (정적 무영향)**

   스크립트 실행 전후 다음 12 파일의 SHA-256 hash 동일 검증:
   - `data/phase17_probe_phi3-case-c-diagnosis-v3/seed-{7,13,42}/case_c_events.json`
   - `data/phase17_probe_phi3-case-c-diagnosis-v3/seed-{7,13,42}/chain.json`
   - `data/phase17_probe_phi3-case-c-diagnosis-v3/seed-{7,13,42}/snn_output_events.json`
   - `data/phase17_probe_phi3-case-c-diagnosis-v3/seed-{7,13,42}/metrics.jsonl`

   1 byte라도 변경 시 즉시 FAIL.

6. **core/persona/ontology/brain/snn/acceptance/charter diff 0 (정적 무영향)**

   `git diff --stat` 기준 다음 경로 변경 0:
   - `Projects/personas/loom/core/`
   - `Projects/personas/loom/persona/`
   - `Projects/personas/loom/ontology/`
   - `Projects/personas/loom/brain/`
   - `Projects/personas/loom/snn/`
   - `Projects/personas/loom/test_phase17_acceptance.py`
   - `Projects/personas/loom/conftest.py`
   - 모든 `PHASE-17-*-CHARTER*.md`, `PHASE-17-NATION-DC-{1,2}-*-SPEC.md`

7. **summary idempotence — 2회 실행 byte-level diff 0**

   ```bash
   py scripts/phase17_v3_summary_regen.py
   sha256sum data/phase17_probe_phi3-case-c-diagnosis-v3/SUMMARY.md \
            data/phase17_probe_phi3-case-c-diagnosis-v3/seed-*/summary.md > hashes_run1.txt
   py scripts/phase17_v3_summary_regen.py
   sha256sum data/phase17_probe_phi3-case-c-diagnosis-v3/SUMMARY.md \
            data/phase17_probe_phi3-case-c-diagnosis-v3/seed-*/summary.md > hashes_run2.txt
   diff hashes_run1.txt hashes_run2.txt  # 무 출력 = PASS
   ```

8. **raw 재계산 수치 검증 (이중 trick)**

   - **8-a (raw 재계산 가능 수치)**: 새 SUMMARY의 다음 항목들을 raw에서 직접 재계산하여 일관성 확인:
     - 시작/종료 faction 수 ← `case_c_events.active_factions_snapshot[0/-1].active_count`
     - 분포 진화 (1000틱 간격) ← `metrics.jsonl` type=`population` 또는 `case_c_events.active_factions_snapshot`
     - Source 비율 ← `metrics.jsonl` type=`source_cumulative` (last record)
     - Wealth gini 추이 ← `metrics.jsonl` type=`wealth.gini`
     - Grievance shared_pairs ← `metrics.jsonl` type=`grievance_targets.shared_pairs`
     - Active Factions Trace ← `case_c_events.active_factions_snapshot` 직접
     - SNN G1~G4 ← `snn_output_events.json`
     - 종합 판정 ← 위 메트릭 결정적 조합
   - **8-b (raw 미존재 수치 — 경과 시간만)**: 원본 mojibake SUMMARY에서 수치만 추출하여 새 SUMMARY에 인용. 추출 불가 시 `N/A (raw 미존재)` 명시.
     - 대상: `경과: 2389.9s (119.5ms/tick)` 같은 wall-clock — 3 seed 각각.
   - 이외 raw에 없는 항목 발견 시: 본 spec [선택] 또는 N/A 처리. 새로운 raw 의존 추가 금지.

### [선택]

- **회귀 6종**: 본 hotfix는 raw / core 무영향이므로 회귀 6종은 [선택]. 최종 통합 시 1회만 권장.
  ```bash
  py -m pytest test_branch.py test_climate.py test_grievance_propagation.py \
                test_nomos.py test_class_promotion.py test_phase14_grievance_propagation.py
  ```
- **py_compile / ruff / mypy** — 신규 스크립트 정적 검사. 환경 미설정 시 누락 보고 허용.

### [금지] 8종

1. **raw 4 카테고리 JSON/JSONL 수정** (byte hash 0 contract)
   - case_c_events.json / chain.json / snn_output_events.json / metrics.jsonl 어떤 byte도 변경 금지
2. **core / persona / ontology / brain / snn / mechanism 코드 변경**
3. **acceptance / charter 본문 수정**
   - `PHASE-17-*-CHARTER*.md`, `PHASE-17-NATION-DC-{1,2}-*-SPEC.md`, `test_phase17_acceptance.py`, `conftest.py`
4. **무파괴 9 / 안전 전제 5종 / BOOST=0.20 / 회귀 6종 정의 변경**
5. **probe 재실행 (옵션 C 봉인)** — raw 재합성 실패 시에만 사용자 명시 승인 후 escalate. 자율 escalate 금지.
6. **DC-1 SIS / DC-2 CPCM 산출물 영향**
   - `data/phase17_phi4_sis/`, `data/phase17_phi4_cpcm/` 무수정
7. **새 raw 의존 추가** — case_c_events / chain / snn_output_events / metrics.jsonl 외 신규 raw 입력 도입 금지. 메모리 매개 변수, 환경변수 입력 금지.
8. **`.mojibake.bak.md` 디코딩 시도** — bytes 그대로 보존. UTF-8 / CP949 / latin1 등 어떤 디코딩도 적용 금지.

---

## 구체 사양

### 1. 입력 raw 4 카테고리 — 구조 + canonical 출처

#### 1-1. `case_c_events.json` (event list)

- 형식: top-level JSON array
- 각 event shape: `{"type": str, "tick": int, ...payload}`
- 본 spec 사용 type:
  - `active_factions_snapshot` (40 per seed, 500틱 간격) — `{tick, active_count, active_fids, faction_sizes}`
  - `cross_faction_lord_pair_emerged` — H5 카운트
  - `respawn_fallback_attempt` / `respawn_fallback_founder_created` — H2c
  - `uprising_skip_no_contact` / `uprising_skip_snn_inactive` — H1
  - `minority_boost_applied` — H3
  - `drift_recovery_to_minority` — H4

#### 1-2. `metrics.jsonl` (line-delimited records) — **canonical for Source/Wealth/Grievance**

- 형식: each line = `{"tick": int, "type": str, "data": {...}}`
- 본 spec 사용 type:
  - `population` (≥200 records) — `data: {fid: count}` per tick
  - `contact` — contact pair distribution
  - `uprising` — per-tick uprising state
  - `wealth` — `data: {gini: float, ...}` per tick
  - `grievance_targets` — `data: {shared_pairs: int, ...}`
  - `source_cumulative` (≥20 records) — `data: {birth_founder, affiliation, drift, conflict}` cumulative

- **Codex 권고**: source / wealth gini / grievance는 **chain.json보다 metrics.jsonl이 canonical**. 본 spec은 metrics.jsonl을 single source of truth로 사용.

#### 1-3. `snn_output_events.json` (event list)

- 형식: top-level JSON array
- 본 spec 사용 type:
  - `uprising_leader_snn_snapshot` — G1 진단
  - `territory_snn_distribution` — G4 진단
  - `small_faction_snn_snapshot` — G3 진단
  - `founder_absorbed_snn_snapshot` — G2 진단

#### 1-4. `chain.json` (선택, 보조 — metrics.jsonl로 부족할 때만)

- 형식: top-level JSON array (≥14000 entries per seed)
- 본 spec 우선순위: **metrics.jsonl 우선, chain.json은 보조**. metrics.jsonl로 충분하면 chain.json 미사용 허용.

### 2. SUMMARY 본문 항목 ↔ raw 매핑 (canonical)

| SUMMARY 항목 | canonical 출처 | 재계산 가능 |
|---|---|:---:|
| 시작/종료 faction 수 | `case_c_events.active_factions_snapshot[0/-1]` | ✅ |
| Total faction_change events | `metrics.jsonl` `population` 차분 또는 `chain.json` (보조) | ✅ |
| 경과 시간 (e.g. `2389.9s`) | **N/A — raw 미존재**. 원본 mojibake에서 인용 또는 `N/A` | ⚠️ 8-b |
| 분포 진화 (1000틱 간격) | `metrics.jsonl` type=`population` (1000으로 나눠 떨어지는 tick만 추출) | ✅ |
| Source 비율 | `metrics.jsonl` type=`source_cumulative` (last record) | ✅ |
| Wealth gini 추이 | `metrics.jsonl` type=`wealth` (`data.gini` per tick) | ✅ |
| Grievance shared_pairs | `metrics.jsonl` type=`grievance_targets` (`data.shared_pairs` per tick) | ✅ |
| Active Factions Trace | `case_c_events.active_factions_snapshot` (40 entries) | ✅ |
| Case C Diagnosis (H1~H5) | `case_c_events.json` 카운트 | ✅ |
| Phase 14B SNN G1~G4 | `snn_output_events.json` 분석 | ✅ |
| 종합 판정 (PASS/FAIL) | 위 메트릭의 결정적 조합 | ✅ |

### 3. `.mojibake.bak.md` 보존 contract

```python
# Pseudo-code
SOURCE = Path("data/phase17_probe_phi3-case-c-diagnosis-v3")
TARGETS = [
    SOURCE / "SUMMARY.md",
    SOURCE / "seed-7" / "summary.md",
    SOURCE / "seed-13" / "summary.md",
    SOURCE / "seed-42" / "summary.md",
]
for path in TARGETS:
    bak_path = path.with_suffix(".mojibake.bak.md")
    # bytes 그대로 복사 — 디코딩 시도 0
    bak_path.write_bytes(path.read_bytes())
    # 새 SUMMARY 작성 후 기존 파일 덮어쓰기
```

- bak 파일이 이미 존재하면 덮어쓰기 금지 (idempotent — 첫 실행만 백업 생성)
- bak bytes 무결성 검증: `sha256(bak) == sha256(원본 첫 실행 시점)`

### 4. 한국어 expected token check (10 토큰 + 분위수 1문장)

```python
EXPECTED_TOKENS = [
    "Φ-3", "실행 요약", "시작 faction 수", "활성 faction 수",
    "결과", "기준", "균등도", "최대 소속 인원",
    "Source 비율", "종합 판정",
]
QUANTILE_NOTE = "본 V3 SUMMARY는 분위수 산출물이 아니며"  # SUMMARY.md 1회 등장 검증
```

검증:
- 각 새 SUMMARY 4개에서 `EXPECTED_TOKENS` 모두 `>= 1회` 등장
- top-level `SUMMARY.md`에서 `QUANTILE_NOTE` 정확히 `>= 1회` 등장 (seed별 summary는 미요구)

### 5. mojibake 일반 패턴 grep — regex 2 종

```python
import re

# CJK Unified (U+4E00-U+9FFF) + CJK Compatibility (U+F900-U+FAFF)
# 한국어 보고서는 한자 미사용 가정. Φ-3(Greek phi U+03A6) / %/ ≥ 등은 별도 범위라 OK.
CJK_RE = re.compile(r"[一-鿿豈-﫿]")

# '?' (U+003F) + 한글 syllable (U+AC00-U+D7AF) = CP949↔UTF-8 round-trip 손실 표지
QMARK_HANGUL_RE = re.compile(r"\?[가-힣]")

SCAN_TARGETS = [
    SOURCE / "SUMMARY.md",
    SOURCE / "seed-7" / "summary.md",
    SOURCE / "seed-13" / "summary.md",
    SOURCE / "seed-42" / "summary.md",
]
# .mojibake.bak.md는 byte-for-byte 보존 대상이므로 grep 제외

for path in SCAN_TARGETS:
    text = path.read_text(encoding="utf-8")
    cjk_hits = CJK_RE.findall(text)
    qh_hits = QMARK_HANGUL_RE.findall(text)
    assert not cjk_hits, f"residual CJK ideograph in {path}: {sorted(set(cjk_hits))}"
    assert not qh_hits, f"residual '?+Hangul' mojibake in {path}: {sorted(set(qh_hits))[:5]}"
```

**근거**: 일반 패턴은 시그니처 hard-list보다 robust. 1차 spec-review byte-level 검증에서 8 시그니처 5/8만 실효(3 vacuous), 미커버 CJK 12종 발견. 일반 패턴은 모든 한자 + 모든 ?+한글을 커버.

**한자 허용 예외 검토**: 새 SUMMARY 본문은 `Φ-3`(Greek), `%`, `≥`, `≤` 등 비-Hangul 특수문자만 사용. CJK ideograph (U+4E00-U+9FFF, U+F900-U+FAFF)는 의도된 사용이 없으므로 0건이 정상. 만약 영어/숫자/한글/특수문자 외 의도된 한자가 필요하면 spec rev로 화이트리스트 추가.

### 6. Codex 자율성 정책 (DC-2 rev.3 패턴 계승)

#### 자율 영역 (Codex 자율 결정 가능)

- helper 함수 시그니처 / 모듈 분할
- JSON / JSONL 파싱 방식 (라인 단위 vs 일괄 vs streaming)
- 새 SUMMARY 본문 구체 표기 (예: 표 형식 디테일, 셀 정렬, 소수점 자릿수)
- mojibake 패턴 처리 알고리즘 (단순 string in vs regex 등)
- typing — TypedDict / Protocol / dataclass 자유
- 임시 변수명 / 함수명 / 모듈 분할

#### 근간 (사용자 승인 없이 수정 금지)

1. raw 4 카테고리 JSON/JSONL byte hash 무결성
2. core / persona / ontology / brain / snn / mechanism / acceptance / charter 본문
3. 무파괴 9 / 안전 전제 5종 / BOOST=0.20
4. 회귀 6종 정의 (test_branch / test_climate / test_grievance_propagation / test_nomos / test_class_promotion / test_phase14_grievance_propagation)
5. V3 anchor (active_factions_snapshot 산출물 영향)
6. DC-1 SIS / DC-2 CPCM 산출물
7. 본 spec 검증 contract 8종 (idempotence / token / mojibake 0 / raw byte hash / core diff 0 / 2회 실행 일관성 / raw 재계산 검증 / raw 미존재 처리)
8. probe 재실행 (옵션 C 봉인)

#### 승인 절차 (근간 수정 필요 시)

- 본 spec [금지] 위반 가능성 발견 → 즉시 작업 중단 → 사용자 보고 → 사용자 명시 승인 후 spec rev.2 작성 → 재진입

### 7. Helper 시그니처 (권장 가이드 — Codex 자율 영역)

```python
# 권장 (강제 아님)
def load_metrics_jsonl(path: Path) -> list[dict]: ...
def aggregate_source_cumulative(records: list[dict]) -> dict[str, int]: ...
def aggregate_wealth_gini(records: list[dict]) -> list[tuple[int, float]]: ...
def aggregate_grievance_pairs(records: list[dict]) -> list[tuple[int, int]]: ...
def render_seed_summary(seed: int, raw: ...) -> str: ...
def render_top_summary(per_seed: list[...]) -> str: ...
def backup_mojibake_if_first_run(path: Path) -> None: ...
def verify_token_check(text: str, tokens: list[str]) -> None: ...
def verify_mojibake_clean(text: str, patterns: list[str]) -> None: ...
```

Codex가 더 좋은 분할이 있다고 판단하면 변경 가능. signature는 권장 가이드.

---

## 변경 파일

| 파일 | 작업 | 유형 |
|---|---|:---:|
| `Projects/personas/loom/scripts/phase17_v3_summary_regen.py` | 신규 작성 | 추가 |
| `Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/SUMMARY.md` | 새 한글로 재dump | 수정 (덮어쓰기) |
| `.../seed-7/summary.md` | 동일 | 수정 |
| `.../seed-13/summary.md` | 동일 | 수정 |
| `.../seed-42/summary.md` | 동일 | 수정 |
| `.../SUMMARY.mojibake.bak.md` | 원본 byte 보존 | 추가 |
| `.../seed-7/summary.mojibake.bak.md` | 동일 | 추가 |
| `.../seed-13/summary.mojibake.bak.md` | 동일 | 추가 |
| `.../seed-42/summary.mojibake.bak.md` | 동일 | 추가 |

총 9 파일 (1 신규 스크립트 + 4 수정 + 4 신규 backup).

**변경 없음 (금지) — byte hash 0 검증 의무**:
- `Projects/personas/loom/core/`
- `Projects/personas/loom/persona/`
- `Projects/personas/loom/ontology/`
- `Projects/personas/loom/brain/`
- `Projects/personas/loom/snn/`
- `Projects/personas/loom/test_phase17_acceptance.py`
- `Projects/personas/loom/conftest.py`
- 모든 `PHASE-17-*-CHARTER*.md`
- `PHASE-17-NATION-DC-1-SIS-SPEC.md` / `PHASE-17-NATION-DC-2-CPCM-SPEC.md`
- `Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-{7,13,42}/case_c_events.json`
- `Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-{7,13,42}/chain.json`
- `Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-{7,13,42}/snn_output_events.json`
- `Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-{7,13,42}/metrics.jsonl`
- `Projects/personas/loom/data/phase17_phi4_sis/`
- `Projects/personas/loom/data/phase17_phi4_cpcm/`

---

## 검증 contract (8종)

### 8-1. 결정성 (idempotent — Codex 자체 검증 의무)

```bash
cd Projects/personas/loom
py scripts/phase17_v3_summary_regen.py
py -c "
import hashlib
from pathlib import Path
files = [
    'data/phase17_probe_phi3-case-c-diagnosis-v3/SUMMARY.md',
    'data/phase17_probe_phi3-case-c-diagnosis-v3/seed-7/summary.md',
    'data/phase17_probe_phi3-case-c-diagnosis-v3/seed-13/summary.md',
    'data/phase17_probe_phi3-case-c-diagnosis-v3/seed-42/summary.md',
]
hashes_1 = [hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files]
import subprocess; subprocess.check_call(['py', 'scripts/phase17_v3_summary_regen.py'])
hashes_2 = [hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files]
assert hashes_1 == hashes_2, 'idempotence FAIL'
print('idempotence PASS')
"
```

### 8-2. 한국어 token check (10 토큰 + 분위수 1문장)

```bash
py -c "
from pathlib import Path
TOKENS = ['Φ-3', '실행 요약', '시작 faction 수', '활성 faction 수',
          '결과', '기준', '균등도', '최대 소속 인원',
          'Source 비율', '종합 판정']
QUANTILE_NOTE = '본 V3 SUMMARY는 분위수 산출물이 아니며'
SOURCE = Path('data/phase17_probe_phi3-case-c-diagnosis-v3')
files_4 = [SOURCE / 'SUMMARY.md',
           SOURCE / 'seed-7/summary.md',
           SOURCE / 'seed-13/summary.md',
           SOURCE / 'seed-42/summary.md']
for path in files_4:
    text = path.read_text(encoding='utf-8')
    for tok in TOKENS:
        assert tok in text, f'token missing: {tok!r} in {path}'
top = (SOURCE / 'SUMMARY.md').read_text(encoding='utf-8')
assert QUANTILE_NOTE in top, 'quantile note missing in top SUMMARY.md'
print('token check PASS')
"
```

### 8-3. mojibake 일반 패턴 grep 0건 (regex 2 종)

```bash
py -c "
import re
from pathlib import Path
CJK_RE = re.compile(r'[一-鿿豈-﫿]')
QMARK_HANGUL_RE = re.compile(r'\?[가-힣]')
SOURCE = Path('data/phase17_probe_phi3-case-c-diagnosis-v3')
files_4 = [SOURCE / 'SUMMARY.md',
           SOURCE / 'seed-7/summary.md',
           SOURCE / 'seed-13/summary.md',
           SOURCE / 'seed-42/summary.md']
for path in files_4:
    text = path.read_text(encoding='utf-8')
    cjk = CJK_RE.findall(text)
    qh = QMARK_HANGUL_RE.findall(text)
    assert not cjk, f'residual CJK in {path}: {sorted(set(cjk))}'
    assert not qh, f'residual ?+Hangul in {path}: {sorted(set(qh))[:5]}'
print('mojibake general-pattern grep PASS (CJK 0 + ?+Hangul 0)')
"
```

**근거 (1차 spec-review 결과)**: 8 시그니처 hard-list 5/8 vacuous (`理쒕`, `寃걚`, `�` 0건). 일반 패턴은 모든 CJK ideograph + 모든 ?+한글을 커버하여 robust.

### 8-4. raw byte hash 0 diff (12 파일) — git diff 1줄

```bash
git diff --stat HEAD -- \
  Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-7/case_c_events.json \
  Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-7/chain.json \
  Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-7/snn_output_events.json \
  Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-7/metrics.jsonl \
  Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-13/case_c_events.json \
  Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-13/chain.json \
  Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-13/snn_output_events.json \
  Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-13/metrics.jsonl \
  Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-42/case_c_events.json \
  Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-42/chain.json \
  Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-42/snn_output_events.json \
  Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-42/metrics.jsonl
# 출력 무 = PASS (byte hash 0 diff 자동 보장. git이 SHA-1 기준으로 추적)
```

**근거 (1차 spec-review MINOR-1)**: rev.1의 `git stash` / `git show HEAD:<path>` 절차 모호성 (실행 전후 vs commit 비교 혼재) 해결. `git diff --stat HEAD --`는 워크트리 vs HEAD 비교 = byte 변경 시 stat 출력, 무 변경 시 무 출력. §8-5와 일관된 패턴.

### 8-5. core/persona/etc diff 0

```bash
git diff --stat HEAD -- \
  Projects/personas/loom/core/ \
  Projects/personas/loom/persona/ \
  Projects/personas/loom/ontology/ \
  Projects/personas/loom/brain/ \
  Projects/personas/loom/snn/ \
  Projects/personas/loom/test_phase17_acceptance.py \
  Projects/personas/loom/conftest.py \
  Projects/personas/loom/PHASE-17-NATION-DC-1-SIS-SPEC.md \
  Projects/personas/loom/PHASE-17-NATION-DC-2-CPCM-SPEC.md \
  Projects/personas/loom/data/phase17_phi4_sis/ \
  Projects/personas/loom/data/phase17_phi4_cpcm/
# 출력 무 = PASS
```

### 8-6. summary idempotence (8-1과 동일, 명시 분리)

### 8-7. raw 재계산 가능 수치 일관성 (스폿 체크 — 3 메트릭 × 3 seed = 9 스폿)

새 SUMMARY의 다음 3 메트릭이 metrics.jsonl과 일치 (스폿 체크):
- `Source 비율` cumulative — `metrics.jsonl` `source_cumulative` last record와 일치
- `Wealth gini` first/last — `metrics.jsonl` `wealth` first/last record와 일치
- `Grievance shared_pairs` last — `metrics.jsonl` `grievance_targets` last record `shared_pairs`와 일치

### 8-8. raw 미존재 항목 처리 (경과 시간)

- 새 SUMMARY 4개에서 `경과` 또는 `wall-clock` 항목 존재 시:
  - 원본 mojibake에서 추출한 수치 인용 (예: `경과: 2389.9s (원본 보존, raw 미존재)`)
  - 또는 항목 자체 제거 + `종합 판정` 섹션에 영향 없음 명시
  - 또는 `경과: N/A (raw 미존재)` 명시
- 셋 중 하나만 채택. 임의의 새 수치 생성 금지.

---

## 회귀 영향 평가 — 정적 무영향

| 회귀 위험 | 평가 | 검증 방식 |
|---|---|---|
| raw 4 카테고리 영향 | **0** | byte hash 12 파일 비교 (8-4) |
| core / persona / ontology / brain / snn 영향 | **0** | git diff --stat (8-5) |
| acceptance / charter / DC-1 / DC-2 영향 | **0** | git diff --stat (8-5) |
| 무파괴 9 / 안전 전제 5종 / BOOST=0.20 | **0** | 위 8-5와 동일 (mechanism 무수정) |
| 회귀 6종 결과 변경 | **0** | 코드 변경 0이므로 결과 동일 — [선택] 검증 |
| V3 anchor (active_factions_snapshot) | **0** | raw byte hash 0 → anchor 보존 (8-4) |

→ **회귀 6종은 [선택]**. 정적 무영향 검증 8-4 + 8-5 + 8-7만으로 회귀 위험 0 증명 가능.

---

## Rollback

```bash
# 1. 새 SUMMARY 4개 → 원본 mojibake로 복구
cd Projects/personas/loom
mv data/phase17_probe_phi3-case-c-diagnosis-v3/SUMMARY.mojibake.bak.md \
   data/phase17_probe_phi3-case-c-diagnosis-v3/SUMMARY.md
for seed in 7 13 42; do
  mv "data/phase17_probe_phi3-case-c-diagnosis-v3/seed-${seed}/summary.mojibake.bak.md" \
     "data/phase17_probe_phi3-case-c-diagnosis-v3/seed-${seed}/summary.md"
done

# 2. 신규 스크립트 삭제
rm scripts/phase17_v3_summary_regen.py

# 3. git checkout으로 원복 (대안)
git checkout HEAD -- data/phase17_probe_phi3-case-c-diagnosis-v3/
git clean -f scripts/phase17_v3_summary_regen.py
```

데이터 영향: 새 SUMMARY 손실 (재실행 가능). raw / core 영향 0. mechanism 영향 0.

---

## Codex 위임 프롬프트

본 spec의 [필수] 8종을 그대로 구현하세요. 자율 영역과 근간 분리는 §6에 명시.

### 절대 준수 — 8 [금지]

1. raw 4 카테고리 JSON/JSONL **1 byte도 변경 금지** (case_c_events / chain / snn_output_events / metrics.jsonl)
2. core / persona / ontology / brain / snn / mechanism 코드 변경 금지
3. acceptance / charter / DC-1 / DC-2 spec 본문 변경 금지
4. 무파괴 9 / 안전 전제 5종 / BOOST=0.20 / 회귀 6종 정의 변경 금지
5. probe 재실행 시도 금지 (옵션 C 봉인)
6. DC-1 SIS / DC-2 CPCM 산출물 영향 금지
7. 새 raw 의존 추가 금지 (4 카테고리 외)
8. `.mojibake.bak.md` 디코딩 시도 금지 (bytes 그대로 보존)

### 자율 영역 (자유 결정)

- helper signature / 모듈 분할
- JSON/JSONL 파싱 방식
- 새 SUMMARY 본문 표기 디테일 (표/셀 정렬/소수점)
- mojibake 패턴 처리 알고리즘
- typing 스타일 (TypedDict / Protocol / dataclass)

### 근간 수정 필요 시 즉시 사용자 보고

§6 근간 8항 중 어느 하나라도 수정 필요하다고 판단되면 **즉시 작업 중단 → 사용자 보고**. 자율 escalate 금지.

### 검증 시퀀스 (보고 전 자체 실행)

1. `py scripts/phase17_v3_summary_regen.py` (1차)
2. `py scripts/phase17_v3_summary_regen.py` (2차)
3. SHA-256 비교 → idempotence (§8-1)
4. token check (§8-2) — 10 토큰 + 분위수 1문장
5. mojibake 일반 패턴 grep 0건 (§8-3) — CJK ideograph 0 + ?+한글 0
6. raw byte hash 0 diff (§8-4) — `git diff --stat HEAD -- <12 raw 파일>` 무 출력
7. core/persona/etc git diff --stat 무 출력 (§8-5)
8. raw 재계산 스폿 체크 (§8-7) — 3 메트릭 × 3 seed
9. raw 미존재 항목 처리 (§8-8)
10. py_compile / ruff / mypy 정적 검사 (선택, 환경 미설정 시 명시 보고)

### 보고 양식

1. 변경 파일 목록 (9 파일 — 1 스크립트 + 4 수정 + 4 신규 backup)
2. 8 검증 항목 PASS/FAIL
3. 자율 결정 사항 (helper signature / 분할 / 알고리즘)
4. 근간 침범 가능성 평가 (8항 각각)
5. raw 미존재 처리 채택 옵션 (인용 / 제거 / N/A)
6. 회귀 6종 — 본 spec [선택]이므로 미실행 권장. 실행 시 결과 첨부 (옵션)
7. 최종 판정: APPROVE / APPROVE WITH NOTES / REQUEST_CHANGES

### 실패 시

- [필수] 1~8 중 하나라도 FAIL → 즉시 작업 중단, 사용자 보고
- [금지] 위반 가능성 발견 → 즉시 작업 중단, 사용자 보고

---

## 다음 단계 후보 (본 spec 통과 후)

1. DC-3 P5R v0 결정 (2 슬롯 freeze vs 보류)
2. FMR/NDP/LRT 사용자 사전 승인
3. Phase 4 Verify 3엔진 cross-check (Gemini=`gemini-3.1-pro`)
4. Phase 5 Package — Charter + Decision Cards + Φ-5 read-only API
