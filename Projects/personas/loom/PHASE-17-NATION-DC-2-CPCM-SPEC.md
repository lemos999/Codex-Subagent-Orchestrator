# [기능·분석 스크립트] DC-2 CPCM — Charter Primitives Convergence Meter (faction-level pair-wise Jaccard, rev.3)

> 긴급도: 보통
> 선행 조건: Φ-3 closure-v2 + V3 진단 완료 (2026-05-03), DC-1 SIS rev.2 spec [확정] + 1차 추출 완료 (2026-05-04, commit 9f129f8), Phase 3 잔여 spec DRAFT rev.2 APPROVE WITH NOTES (2026-05-04), acceptance long-run 분리 commit b53c87a (2026-05-04), **DC-2 spec rev.2 Codex 1차 구현 APPROVE WITH NOTES (2026-05-04 — Q1 NaN literal RFC 8259 비호환 / Q2 회귀 부재 항목 발견)**
> 작업 유형: 기능 (분석 스크립트, 1회성 데이터 추출)
> DB migration: 없음
> 외부 의존: numpy (loom 환경 기설치). 표준 라이브러리만으로 충분.
> **코어 영역 판정**: **비코어** (telemetry helper, read-only). 게이트 §3.3.2 **불요**. **단**: 본 spec 구현 중 brain·SNN·PersonaBrain **모듈 import / 인스턴스 생성** 시도가 발생하면 **즉시 작업 중단 + 사용자 escalate** (engine 내부 brain 사용은 무관 — 아래 §"R10 closed" 범위 정의 참조).

## 변경 이력

- **rev.3 (2026-05-04)**: Codex 1차 구현 APPROVE WITH NOTES 2건 정정 + Codex 자율성 정책 명문화
  - Q1: **NaN literal → JSON `null` 직렬화 강제** (근간). JSON 출력 시 `NaN`/`Infinity` literal 절대 금지 (RFC 8259 strict 비호환). 검증 contract: `json.dump(..., allow_nan=False)` 사용 + strict JSON parser 무에러 통과. **구현 디테일은 구현자 자율** (None 치환 helper 이름·위치 / numpy 처리 / atomic write 등). 메트릭 정의 / 출력 형식 / 에러 케이스 일괄 반영.
  - Q2: **회귀 7종 → 6종 정정**. `tests/test_persistence.py` 항목 제거 (해당 파일 부재 — DC-1 SIS spec 결함 소급 정정). git diff 명령은 변경 없음 (persistence path 미인용).
  - **Codex 자율성 정책 명문화 (근간 정의 + 승인 절차)**:
    - **근간 (loom 설계 뼈대 — 수정 시 사용자 승인 필수)**:
      1. 코어 영역 (§3.3.2): brain · SNN · PersonaBrain · 코어 ontology · 코어 acceptance — script-level touching 0건 보존
      2. mechanism 무수정: `multi_tick_engine.py` / `persona/*` / `ontology/*` / `brain/*` / `snn/*` 코드 1줄도 변경 금지
      3. acceptance criteria 무변경: `test_phase17_acceptance.py` assertion / tick / EXPECTED FAIL semantics
      4. charter 본문 무변경: `PHASE-17-NATION-CHARTER-*.md`
      5. 무파괴 9 / 안전 전제 5종 (HYSTERESIS=2, FOUNDER_RESPAWN_EVERY=480, TARGET_ACTIVE=2, COMMIT_EVERY=48, MAX_MEMBERS=2) / BOOST=0.20 / 회귀 6종 보존
      6. §3.7 6단 사슬 정합성 (1단 자연 측정 → 2단 분포 → 3단 결합점 → 4단 분위수 → 5단 cross-check → 6단 closure)
      7. axis A/B/C 가드레일 + V3 raw anchor (9-a/9-b/9-c)
      8. 검증 contract: strict JSON RFC 8259 / brain·SNN import 0건 / git diff empty / 회귀 6종 PASS / V3 anchor PASS
    - **근간 수정 필요시**: **즉시 작업 중단 + 사용자 escalate**. 근간 수정 사유·영향·대안을 명시하여 사용자 명시 승인 후 진행. 자가 판단으로 근간 수정 절대 금지.
    - **자율 영역 (구현자 재량)**:
      - 함수 이름·시그니처 변형·분할·통합 (Helper 시그니처 §는 "권장" 가이드)
      - 내부 흐름·중간 변수·예외 메시지 세부
      - atomic write 절차·임시 파일 처리 방식
      - 로그 포맷·진행 상황 출력
      - JSON 직렬화 시 NaN 변환 helper 이름·위치 (검증 contract `allow_nan=False` 보존만 의무)
      - 1차 구현 결과 같은 [필수] 항목 / 검증 contract을 만족하는 임의 구현
- **rev.2 (2026-05-04)**: 1차 /spec-review 조건부 승인 반영
  - MAJOR #1: R10 범위를 **script-level import 0건**으로 명확화. engine 내부 brain 사용은 R10 trigger 아님 (engine은 black box).
  - MINOR #1: `ontology/layers.py` 인용 line 정정 (171-175 → 167-184 Faction class 전체, charter 필드 line 173 명시).
  - MINOR #3: `numpy.percentile`에 `method='linear'` 명시 (numpy 1.22+ 기본, 결정성 보강).
  - MINOR #4: `mypy --strict` → 프로젝트 기본 설정 따르기로 완화.
- **rev.1 (2026-05-04)**: 초기 작성 (A→B 통합 — R1·R2·R3·R10 검증 본문 포함).

---

## 배경

LOOM Phase 17 Φ-4 Nation Charter design Phase 3 Decision Card DC-2 (Charter Primitives Convergence Meter) 1차 spec rev.2.

본 spec은 **OQ 4** (charter primitives 수렴 측정)에 답하기 위한 **read-only 측정 스크립트**. faction 단위 pair-wise charter overlap을 V3 raw anchor 기반으로 산출하고 분위수 후보를 도출. **mechanism 무수정**, **acceptance 무변경**, **script-level brain·SNN API touching 0건** (engine 내부 brain 사용은 무관 — §"R10 closed" 범위 정의 참조)을 절대 보존.

### 본 spec 위치 (canonical order)

Phase 3 잔여 spec 파이프라인 DRAFT rev.2 §3 canonical order 중 **3번** (R1~R3·R10 검증 완료 후 spec 본문 작성).

```
[1] acceptance long-run 분리 ─────── 완료 (commit b53c87a, 2026-05-04)
[2] DC-2 R1~R3·R10 사전 검증 ──────── 본 spec §"선행 검증"에 통합 (별도 보고서 없이 본문 인용)
[3] DC-2 CPCM spec ─────────────────── 본 문서  ← 현재 위치
[4] V3 mojibake hotfix spec ────────── 후속 (병행 가능)
[5] DC-3 P5R v0 결정 ────────────────── DC-2 [확정] 후
[6] FMR/NDP/LRT 사용자 사전 승인 ────── 사용자 결정
```

### Phase 3 잔여 DRAFT rev.2 R1~R3·R10 통합 (별도 보고서 없이 spec 본문에 포함)

DRAFT rev.2 §1 [DC-2] §"위험·우려"의 R1·R2·R3·R10 4 항목은 본 spec §"선행 검증" 섹션에서 **직접 코드/데이터 인용 + 검증 결과**로 closure. 별도 사전 검증 보고서 작성 없이 spec 본문 1회로 통합 처리 (사용자 권고 — A→B 통합 패턴).

### DC-1 §1.0 caveat 계승 (rev.2 의무)

DC-1 SIS rev.2 1차 추출 결과 12 셀 중 2 셀만 ±10% 통과 (`dom_share P75`, `cross_faction_lord_count P67` — 둘 다 동률 ceiling 효과). 본 spec은 §1.0 caveat을 무조건 계승:

1. CPCM 분위수 결과는 **exploratory telemetry**. trigger / threshold freeze로 사용 금지.
2. P5R `nation.charter_overlap` body semantics에 본 spec 분위수 값을 **고정 값으로 박지 말 것** — type signature만.
3. CPCM × SIS 결합점(§3.7 3단)은 별도 spec. 본 spec은 1단(자연 측정) + 2단(분포 분석) + 4단(분위수 후보) 범위.

---

## 선행 검증 (R1·R2·R3·R10) — DRAFT rev.2 통합 closure

### R1 closed: `faction_charter_primitives()` 시그니처·반환 타입

**검증 일자**: 2026-05-04
**검증 대상**: [core/multi_tick_engine.py:1733-1737](core/multi_tick_engine.py#L1733-L1737)

```python
def faction_charter_primitives(self, faction_id: str) -> tuple[str, ...]:
    """Faction의 norm primitive."""
    if faction_id not in self.factions:
        raise KeyError(f"unknown faction_id: {faction_id!r}")
    return self.factions[faction_id].charter
```

- **시그니처**: `(self, faction_id: str) -> tuple[str, ...]`
- **반환 타입**: `tuple[str, ...]` — 문자열 시퀀스 (set-like)
- **구현**: 5줄 pure accessor — `self.factions[fid].charter` 단순 반환
- **데이터 출처**: [ontology/layers.py:167-184](ontology/layers.py#L167-L184) `Faction` dataclass (charter 필드는 line 173 `charter: tuple[str, ...]`). `__post_init__`에서 길이 [3,5] + 중복 금지 검증, faction 생성 후 charter mutate 없음 — 회귀 6종 freeze 검증과 정합 (rev.3 Q2 정정).
- **결론**: F1 (DRAFT rev.2 CRITICAL) 정정 확인 — DC-2는 **faction 단위**가 정확. PersonaBrain primitive 가정은 잘못. R1 closed.

### R2 closed: Jaccard 1차 단일 (cosine 부적합)

**검증 일자**: 2026-05-04
**검증 근거**: R1 결과 — charter 데이터 형태가 `tuple[str, ...]` (string sequence, set-like)

| 알고리즘 | 적합성 | 이유 |
|---|:---:|---|
| **Jaccard** `|A ∩ B| / |A ∪ B|` | ✅ 1차 단일 | string set의 자연 거리. 반환 타입과 정합. 결과 `[0, 1]` |
| **cosine** `(A · B) / (\|A\| \|B\|)` | ❌ 보조 부적합 | `tuple[str, ...]`는 vector가 아닌 nominal categorical. 인덱스 일치 가정이 의미 손실 (예: `("equality", "growth")` vs `("growth", "equality")` 동일 의미인데 cosine은 0 처리). string→vector embedding은 brain·SNN touching 위험 (R10 위반). |

- **결론**: 본 spec은 **Jaccard 단일** 알고리즘. cosine은 사용 금지 (R10과 충돌). R2 closed.

### R3 closed: V3 anchor — `active_factions_snapshot` 직접 매칭

**검증 일자**: 2026-05-04
**검증 대상**: [core/multi_tick_engine.py:805-824](core/multi_tick_engine.py#L805-L824) `active_factions_snapshot` event 발행 로직 + V3 raw 3 seed × 40 snapshot

**Event 구조** (multi_tick_engine.py:805-824):
```python
if self.time.tick > 0 and self.time.tick % 500 == 0:
    self.event_log.append({
        "type": "active_factions_snapshot",
        "tick": self.time.tick,
        "active_count": <active faction count>,
        "faction_sizes": {fid: size, ...},  # only active
        "cross_faction_lord_count": <cumulative>,
        "cross_faction_lord_pairs": {lord_id: sorted([fid, fid, ...])},
    })
```

**V3 raw 검증**:
- 발행 주기: `tick > 0 and tick % 500 == 0` → 정확히 ticks 500, 1000, ..., 20000 (총 **40 snapshot/seed**, 3 seed 모두)
- 본 spec anchor 3종 (engine 재실행 후보 검증):
  - **9-a**: per-seed snapshot 발행 횟수 = **40** (3 seed 모두)
  - **9-b**: per-snapshot `faction_sizes` keys (active fids) = engine 재실행 결과의 active faction set와 **bijection** (재실행 결정성 검증)
  - **9-c**: per-snapshot `active_count` = `len(faction_sizes)` (자기 정합)
- **결론**: V3 raw `active_factions_snapshot` 자체가 **강한 anchor**. DC-1의 `cross_faction_lord_count delta 합 = 22/23/19`처럼 단일 정수 anchor는 아니지만, snapshot 단위 결정성 검증으로 충분. R3 closed.

### R10 closed: brain·SNN·PersonaBrain 의존성 0건 (script-level)

**검증 일자**: 2026-05-04
**검증 대상**: `faction_charter_primitives()` ([multi_tick_engine.py:1733-1737](core/multi_tick_engine.py#L1733-L1737)) 함수 본문 + `Faction.charter` 데이터 출처 ([ontology/layers.py:167-184](ontology/layers.py#L167-L184), charter는 line 173)

**R10 범위 정의 (rev.2 명확화)**:

R10은 **본 spec script(`phase17_phi4_cpcm_extractor.py`) 자체의 import / 인스턴스 생성** 0건을 의미. engine 내부에서 brain·SNN을 사용하는 것은 **R10 trigger 아님** — engine은 black box, public API(`MultiTickEngine(seed=...)`, `engine.tick()`, `engine.faction_charter_primitives(fid)`)만 호출.

| 영역 | R10 적용 | 예시 |
|---|:---:|---|
| **script-level (본 spec 영역)** | ✅ 0건 강제 | `import brain`, `from snn import ...`, `from persona.persona_brain import ...`, `PersonaBrain(...)` 인스턴스 생성, `sentence_transformers` / `gensim` 등 vector embedding 라이브러리 |
| **engine internal (black box)** | ❌ 무관 | `engine.tick()`이 내부적으로 `self.brains[pid]`를 호출하는 것 ([multi_tick_engine.py:351-353](core/multi_tick_engine.py#L351-L353) 등). engine 자체는 brain을 사용하지만 spec script는 engine만 호출 |

**검증 방식**:
1. 함수 본문 직접 검사: 5줄 pure accessor. 외부 모듈 호출 0건.
2. `Faction.charter`는 `Faction` 데이터클래스 필드 (불변 tuple). brain·SNN 모듈 무관.
3. 함수가 의존하는 외부 상태: `self.factions: dict[str, Faction]` (engine 내부 dict). brain·SNN 인스턴스 무관.

**결론**:
- `faction_charter_primitives()` 호출만 사용하는 한 script-level brain·SNN·PersonaBrain touching 0건 보장.
- engine 재실행(`MultiTickEngine(seed=seed)` × 20,000 ticks)은 허용 — engine internal 사용은 R10 무관.
- §3.3.2 코어 게이트 **비발동**. R10 closed.
- **escalate 트리거**: 본 spec script 본문 안에 `import brain`, `from snn import ...`, `from persona.persona_brain import ...`, `PersonaBrain(...)` 인스턴스 생성, vector embedding 라이브러리 import 등이 **필요해지는 상황** 발생 시 즉시 작업 중단 + 사용자 보고 (코어 게이트로 전환). engine.tick() 호출은 trigger 아님.

---

## 작업 범위

### [필수]
1. **engine 결정성 재실행**: V3 seed (7, 13, 42) 각각에 대해 `MultiTickEngine(seed=seed)` 인스턴스 생성 후 20,000 ticks 실행.
   - V3 probe([observe_phase17_emergence.py:741-742](observe_phase17_emergence.py#L741-L742)) 사용 진입점과 동일한 seed/ticks 설정 → 결정성 재현 확인.
2. **snapshot 단위 charter 추출**: 매 500 tick (active_factions_snapshot 발행 시점)마다 `engine.faction_charter_primitives(fid)`를 모든 active fid에 대해 호출하여 `dict[fid → tuple[str, ...]]` 적재.
3. **V3 raw anchor 매칭** (필수 검증, AssertionError 강제):
   - **9-a**: per-seed snapshot 발행 횟수 = **40** (engine 재실행 시 동일)
   - **9-b**: 매 snapshot tick의 active fid set = V3 raw `active_factions_snapshot.faction_sizes` keys (3 seed × 40 snapshot 모두)
   - **9-c**: 매 snapshot의 `active_count` = `len(faction_sizes)` (V3 raw 자기 정합 확인)
4. **pair-wise Jaccard 산출**: 매 snapshot마다 active faction pair 모두에 대해 Jaccard 계산:
   - `pairs = combinations(sorted(active_fids), 2)` (결정적 순서)
   - `J(A, B) = |set(A) ∩ set(B)| / |set(A) ∪ set(B)|` (둘 다 빈 set이면 `nan`)
   - 자체 쌍(`fid == fid`) 제외
5. **분위수 후보 도출**: per-seed + aggregate에서 **모든 (snapshot, pair) Jaccard 값**을 flatten한 분포의 P25/P50/P67/P75/P90 계산.
6. **3 seed 일관성 자동 판정**: P50/P67/P75 ±10% 이내 boolean (DC-1과 동일 양식). aggregate consistency table 출력.
7. **출력 파일**:
   - `Projects/personas/loom/data/phase17_phi4_cpcm/seed-{7,13,42}/{overlap_distribution.json, summary.md}` (per seed)
   - `Projects/personas/loom/data/phase17_phi4_cpcm/aggregate/{overlap_distribution.json, summary.md}` (3 seed 통합)
8. **인코딩 utf-8 명시**: 모든 file open `encoding='utf-8'` 명시 (V3 mojibake 재발 방지). summary.md에 한국어 토큰 (`분위수`, `주의`, `검증`, `seed`) 포함.
9. **회귀 6종 PASS** (DC-1과 동일 목록 — rev.3 Q2 정정: test_persistence.py 부재로 7종 → 6종): mechanism 무수정 증명.

### [선택]
- pair overlap heatmap (matplotlib): per snapshot × per seed pair 매트릭스 PNG 출력 (`data/phase17_phi4_cpcm/plots/seed_{N}_snapshot_{tick}.png`)
- charter primitive set 빈도 분석 (가장 자주 등장하는 primitive top-10)
- charter overlap 시계열 line plot (per seed mean Jaccard over time)

### [금지]
- **script-level brain·SNN·PersonaBrain API touching** (본 spec script `phase17_phi4_cpcm_extractor.py` 본문 안에서 `from persona.persona_brain`, `import brain`, `import snn`, `*.snn_*`, `PersonaBrain(...)` 인스턴스 생성, `sentence_transformers` / `gensim` 등 vector embedding 라이브러리 — 모든 형태) — 발생 시 **즉시 작업 중단 + 사용자 escalate** (코어 게이트로 전환).
  - **engine 재실행(`MultiTickEngine(seed=...)` + `engine.tick()`)은 허용** — engine 내부에서 brain을 사용하는 것은 R10 trigger 아님. engine은 black box, public API만 호출. 자세한 정의는 §"R10 closed" 범위 정의 표 참조.
- charter primitive **주입·수렴 강제 mechanism** (top-down, axis C 위반)
- magic threshold freeze (예: `overlap >= 0.7` 결정 — Phase 17 STUB Entry Trigger 인용 금지, charter 본문 변경 금지). **DC-1 §1.0 caveat 계승**: CPCM 분위수 값을 sovereignty / branch rule / P5R body semantics로 **승격 금지**.
- mechanism 변경 — `multi_tick_engine.py` / `persona/*` / `ontology/*` / `brain/*` / `snn/*` 코드 수정 절대 금지 (단 1줄도 금지).
- **acceptance criteria 변경** — `test_phase17_acceptance.py` assertion / tick count / expected-fail semantics 변경 금지 (acceptance long-run 분리 spec과 정합)
- mojibake `summary.md` / `SUMMARY.md` 사용 (raw JSON / `case_c_events.json` + `metrics.jsonl`만 — Codex Finding #2 B-2 계승)
- 무파괴 9 / 안전 전제 5종 (HYSTERESIS=2, FOUNDER_RESPAWN_EVERY=480, TARGET_ACTIVE=2, COMMIT_EVERY=48, MAX_MEMBERS=2) / BOOST=0.20 / 회귀 6종 변경 (rev.3 Q2: test_persistence.py 부재 정정)
- charter 본문 (`PHASE-17-NATION-CHARTER-*.md`) 변경
- cosine similarity (R2 closed — string sequence에 부적합 + R10 위험)
- vector embedding (brain·SNN touching 우회 금지)

---

## 구체 사양

### 입력 데이터 (Canonical)

```
Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/
├── seed-7/
│   ├── case_c_events.json      # active_factions_snapshot anchor 매칭 (필수)
│   ├── metrics.jsonl           # (선택) 추가 검증
│   └── summary.md              # 사용 금지 (mojibake)
├── seed-13/...
└── seed-42/...
```

**raw 사용 원칙** (Codex Finding #2 B-2 + DRAFT rev.2 §1.0):
- `case_c_events.json`만 `active_factions_snapshot` event 추출에 사용 (9-a/9-b/9-c anchor)
- mojibake `summary.md` / `SUMMARY.md` **사용 절대 금지**

**engine 재실행** (charter primitive 추출 전용 — V3 raw에 charter 정보 부재이므로 결정성 재실행 필수):
- 진입점: `MultiTickEngine(seed=seed)` ([core/multi_tick_engine.py](core/multi_tick_engine.py)) 직접 사용
- V3 probe runner와 동일 seed (7, 13, 42), 동일 ticks (20,000)
- 매 500 tick 종료 후 engine 상태에서 `faction_charter_primitives(fid)` 호출 (read-only)

### 메트릭 정의 (snapshot 단위, per active faction pair)

| # | 메트릭 | Python 메모리 타입 | JSON 직렬화 타입 | 정의 | 출처 |
|---|---|---|---|---|---|
| 1 | `pair_jaccard` | `float [0, 1]` 또는 `float('nan')` | `number [0, 1]` 또는 `null` | 한 snapshot의 active faction pair (A, B)에 대해 `J(A.charter, B.charter)` | engine 재실행 → `faction_charter_primitives(fid)` |
| 2 | `snapshot_mean_jaccard` | `float [0, 1]` 또는 `float('nan')` | `number [0, 1]` 또는 `null` | 한 snapshot의 모든 pair Jaccard 평균 | 1로부터 derive |
| 3 | `snapshot_max_jaccard` | `float [0, 1]` 또는 `float('nan')` | `number [0, 1]` 또는 `null` | 한 snapshot의 pair Jaccard 최댓값 (≥ 0.7 = 수렴 후보, freeze 금지) | 1로부터 derive |
| 4 | `snapshot_min_jaccard` | `float [0, 1]` 또는 `float('nan')` | `number [0, 1]` 또는 `null` | 한 snapshot의 pair Jaccard 최솟값 | 1로부터 derive |
| 5 | `snapshot_pair_count` | `int` | `number` | 한 snapshot의 pair 수 = `C(active_count, 2)` | 1로부터 derive |

**중요**:
- 메트릭 #1은 **모든 (snapshot, pair) flatten 분포**가 분위수 계산의 base. snapshot 단위 평균(#2)이 아님.
- **NaN 직렬화 정책 (rev.3 — Q1 정정, 근간)**: Python 메모리에서는 `float('nan')` 유지 가능 (numpy 호환). JSON 직렬화 시 **`null` 강제**, `NaN` / `Infinity` literal 출력 **금지** (RFC 8259 strict 비호환). 검증 contract: **`json.dump(..., allow_nan=False)` 의무** + strict JSON parser(`json.loads(open(...).read())` 한 번만으로 무에러 통과)로 검증 가능. **구현 디테일** (None 치환 시점 / helper 함수 이름 / numpy 처리 방식 / atomic write 절차 등)은 **구현자 자율** — 위 contract 보존이라면 어떤 구현이든 허용.
- `null`은 빈 charter pair에서만 발생 (둘 다 빈 set일 경우). 정상 운영에서는 0건이어야 함 (Faction 생성 시 charter 비어 있으면 acceptance 결함 — 별도 escalate).
- `snapshot_max_jaccard ≥ 0.7`은 **분위수 candidate**일 뿐. trigger/threshold로 사용 금지 (§1.0 caveat).
- `active_count < 2`인 snapshot은 pair 0개 → `snapshot_pair_count = 0` + `snapshot_mean/max/min = null` (JSON 직렬화 시, 정보 손실 명시).

### Helper 함수 시그니처 (권장 가이드 — 구현자 자율)

> **rev.3 자율성 정책**: 아래 시그니처·내부 구현은 **권장 가이드**. [필수] 항목과 검증 contract(strict JSON / 9-a/9-b/9-c anchor / brain·SNN 0건)만 보존되면 함수 분할·이름·내부 흐름은 **구현자 자율**.

```python
from pathlib import Path
import json
import sys
from typing import TypedDict
from itertools import combinations

# loom 모듈 경로 추가
LOOM_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LOOM_ROOT))

from core.multi_tick_engine import MultiTickEngine

class SnapshotMetrics(TypedDict):
    tick: int
    active_count: int
    active_fids: list[str]            # sorted, 결정적
    pair_count: int
    pairs: list[dict]                 # [{"a": fid, "b": fid, "jaccard": float}, ...]
    mean_jaccard: float               # nan if pair_count == 0
    max_jaccard: float                # nan if pair_count == 0
    min_jaccard: float                # nan if pair_count == 0

def load_v3_active_snapshots(events_path: Path) -> list[dict]:
    """case_c_events.json에서 active_factions_snapshot event 추출 (시간순 정렬)."""
    with events_path.open(encoding='utf-8') as f:
        events = json.load(f)
    snapshots = [e for e in events if e.get('type') == 'active_factions_snapshot']
    snapshots.sort(key=lambda e: e['tick'])
    return snapshots

def jaccard(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    """tuple[str, ...] pair Jaccard. 빈 set 둘 다 → nan, 한쪽 빈 set → 0.0."""
    set_a, set_b = set(a), set(b)
    union = set_a | set_b
    if not union:
        return float('nan')
    return len(set_a & set_b) / len(union)

def run_engine_and_capture_charters(seed: int, ticks: int) -> list[dict]:
    """engine 결정성 재실행 + 매 500 tick에서 active fid의 charter 추출.
    반환: [{"tick": int, "active_fids": list[str], "charters": dict[fid, tuple[str, ...]]}, ...]"""
    engine = MultiTickEngine(seed=seed)
    captured: list[dict] = []
    while engine.time.tick < ticks:
        engine.tick()
        if engine.time.tick > 0 and engine.time.tick % 500 == 0:
            active_fids = sorted([
                fid for fid in engine.factions
                if len(engine._faction_members_cache.get(fid, ())) > 0
            ])
            captured.append({
                "tick": engine.time.tick,
                "active_fids": active_fids,
                "charters": {fid: engine.faction_charter_primitives(fid) for fid in active_fids},
            })
    return captured

def compute_snapshot_metrics(captured_entry: dict) -> SnapshotMetrics:
    """단일 snapshot tick → SnapshotMetrics."""
    fids = captured_entry["active_fids"]
    charters = captured_entry["charters"]
    pairs_list: list[dict] = []
    for a, b in combinations(fids, 2):
        j = jaccard(charters[a], charters[b])
        pairs_list.append({"a": a, "b": b, "jaccard": j})
    if pairs_list:
        jaccards = [p["jaccard"] for p in pairs_list if p["jaccard"] == p["jaccard"]]  # nan 제외
        mean_j = sum(jaccards) / len(jaccards) if jaccards else float('nan')
        max_j = max(jaccards) if jaccards else float('nan')
        min_j = min(jaccards) if jaccards else float('nan')
    else:
        mean_j = max_j = min_j = float('nan')
    return {
        "tick": captured_entry["tick"],
        "active_count": len(fids),
        "active_fids": fids,
        "pair_count": len(pairs_list),
        "pairs": pairs_list,
        "mean_jaccard": mean_j,
        "max_jaccard": max_j,
        "min_jaccard": min_j,
    }
```

### 비즈니스 로직 (구체 의사코드)

```python
import numpy as np
from pathlib import Path

DATA_ROOT = Path("Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3")
OUT_ROOT = Path("Projects/personas/loom/data/phase17_phi4_cpcm")
TOTAL_TICKS = 20000          # V3 probe contract
SEEDS = [7, 13, 42]
QUANTILES = [25, 50, 67, 75, 90]
EXPECTED_SNAPSHOT_COUNT = 40  # ticks 500..20000 step 500

def compute_quantiles(values: list[float]) -> dict[str, float]:
    """nan 제외 후 분위수. 빈 배열 → 모두 nan.

    보간 방식은 numpy 1.22+ 기본 'linear' 명시 (rev.2 결정성 보강).
    """
    clean = [v for v in values if v == v]  # nan 제외
    if not clean:
        return {f"P{q}": float('nan') for q in QUANTILES}
    return {f"P{q}": float(np.percentile(clean, q, method='linear')) for q in QUANTILES}

def assert_v3_anchor_match(seed: int, captured: list[dict], v3_snapshots: list[dict]) -> None:
    """9-a/9-b/9-c V3 anchor 검증 — AssertionError 강제."""
    # 9-a: snapshot 발행 횟수
    assert len(captured) == EXPECTED_SNAPSHOT_COUNT, \
        f"seed {seed}: re-run snapshot count={len(captured)}, expected={EXPECTED_SNAPSHOT_COUNT}"
    assert len(v3_snapshots) == EXPECTED_SNAPSHOT_COUNT, \
        f"seed {seed}: V3 raw snapshot count={len(v3_snapshots)}, expected={EXPECTED_SNAPSHOT_COUNT}"
    # 9-b: 매 snapshot tick의 active fid set 일치
    for cap, v3 in zip(captured, v3_snapshots):
        assert cap["tick"] == v3["tick"], \
            f"seed {seed}: tick mismatch re-run={cap['tick']} vs V3={v3['tick']}"
        v3_fids = sorted(v3.get("faction_sizes", {}).keys())
        assert cap["active_fids"] == v3_fids, \
            f"seed {seed} tick {cap['tick']}: active fid mismatch re-run={cap['active_fids']} vs V3={v3_fids}"
    # 9-c: 자기 정합 (V3 raw 검증)
    for v3 in v3_snapshots:
        assert v3["active_count"] == len(v3["faction_sizes"]), \
            f"seed {seed} tick {v3['tick']}: active_count={v3['active_count']} vs faction_sizes len={len(v3['faction_sizes'])}"

def process_seed(seed: int) -> dict:
    # 1. V3 raw anchor 로드
    v3_snapshots = load_v3_active_snapshots(DATA_ROOT / f"seed-{seed}" / "case_c_events.json")
    # 2. engine 결정성 재실행 + charter 추출
    captured = run_engine_and_capture_charters(seed, TOTAL_TICKS)
    # 3. anchor 매칭 검증 (강제)
    assert_v3_anchor_match(seed, captured, v3_snapshots)
    # 4. snapshot 단위 metric
    snapshots: list[SnapshotMetrics] = [compute_snapshot_metrics(c) for c in captured]
    # 5. 분위수: 모든 (snapshot, pair) Jaccard flatten
    all_pair_jaccards = [p["jaccard"] for s in snapshots for p in s["pairs"]]
    quantiles = compute_quantiles(all_pair_jaccards)
    # 6. 출력
    out_dir = OUT_ROOT / f"seed-{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_distribution_json(out_dir / "overlap_distribution.json", seed, snapshots, quantiles)
    save_summary_md_utf8(out_dir / "summary.md", seed, snapshots, quantiles)
    return {"seed": seed, "snapshots": snapshots, "quantiles": quantiles, "all_jaccards": all_pair_jaccards}

def aggregate_and_consistency(per_seed: list[dict]) -> None:
    # seed 간 분위수 일관성 (P50/P67/P75 × ±10%)
    consistency = {}
    for q_label in ["P50", "P67", "P75"]:
        vals = [s["quantiles"][q_label] for s in per_seed if s["quantiles"][q_label] == s["quantiles"][q_label]]
        if not vals:
            consistency[q_label] = False
            continue
        mean_v = sum(vals) / len(vals)
        if mean_v == 0:
            consistency[q_label] = all(v == 0 for v in vals)
        else:
            consistency[q_label] = all(abs(v - mean_v) / abs(mean_v) <= 0.10 for v in vals)
    # aggregate 분위수: 3 seed 데이터 모두 flatten
    all_jaccards = [j for s in per_seed for j in s["all_jaccards"]]
    aggregate_q = compute_quantiles(all_jaccards)
    out_dir = OUT_ROOT / "aggregate"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_aggregate_json(out_dir / "overlap_distribution.json", aggregate_q, consistency, per_seed)
    save_aggregate_summary_utf8(out_dir / "summary.md", aggregate_q, consistency, per_seed)

def main() -> None:
    per_seed = [process_seed(s) for s in SEEDS]
    aggregate_and_consistency(per_seed)

if __name__ == "__main__":
    main()
```

**모든 file open은 `encoding='utf-8'` 명시** (V3 mojibake 재발 방지).
**모든 import는 `core.multi_tick_engine.MultiTickEngine`만** — brain·SNN·PersonaBrain 모듈 import 0건 (R10 보존).

### 출력 형식

#### `seed-{N}/overlap_distribution.json`

```json
{
  "seed": 7,
  "total_ticks": 20000,
  "snapshot_interval": 500,
  "snapshot_count": 40,
  "algorithm": "jaccard",
  "snapshots": [
    {
      "tick": 500,
      "active_count": 3,
      "active_fids": ["F1", "F2", "F3"],
      "pair_count": 3,
      "pairs": [
        {"a": "F1", "b": "F2", "jaccard": 0.40},
        {"a": "F1", "b": "F3", "jaccard": 0.20},
        {"a": "F2", "b": "F3", "jaccard": 0.50}
      ],
      "mean_jaccard": 0.367,
      "max_jaccard": 0.50,
      "min_jaccard": 0.20
    }
  ],
  "all_pair_jaccard_distribution": {
    "n": 117,
    "quantiles": {"P25": 0.10, "P50": 0.30, "P67": 0.45, "P75": 0.55, "P90": 0.75}
  },
  "v3_anchor_validation": {
    "snapshot_count_match": true,
    "fid_set_match_per_snapshot": true,
    "active_count_self_consistency": true,
    "passed": true
  }
}
```

#### `seed-{N}/summary.md` (UTF-8 명시)

```markdown
# DC-2 CPCM overlap distribution — seed {N}

- total_ticks: 20000
- snapshot_count: 40 (interval=500)
- algorithm: Jaccard (set-based)
- 활성 faction pair 총 개수: {N}
- 빈 charter pair (JSON `null` / Python `nan`): {N}건 (정상 운영 시 0)

## 분위수 후보 (모든 (snapshot, pair) Jaccard flatten)

| 분위수 | 값 |
|---|---:|
| P25 | ... |
| P50 | ... |
| P67 | ... |
| P75 | ... |
| P90 | ... |

## V3 anchor 검증

- snapshot 발행 횟수: 40 (V3 raw 동일)
- 매 snapshot tick의 active fid set: V3 raw와 일치
- active_count 자기 정합: V3 raw 무결성
- passed: {true|false}

## 주의

본 분위수 결과는 exploratory telemetry. trigger / threshold freeze 금지 (DC-1 §1.0 caveat 계승).
P5R `nation.charter_overlap` body semantics에 본 값을 고정으로 박지 말 것 — type signature만.
§3.7 사슬 1단(자연 측정) + 2단(분포) + 4단(분위수 후보) 범위. 3단(결합점)·5단(cross-check)·6단(closure)은 별도 spec.
```

#### `aggregate/overlap_distribution.json` + `aggregate/summary.md`

3 seed 합산 분위수 + seed 간 일관성 boolean (P50/P67/P75 × ±10%):

```json
{
  "seeds_combined": [7, 13, 42],
  "snapshot_count_per_seed": 40,
  "total_pair_observations": 351,
  "algorithm": "jaccard",
  "aggregate_quantiles": {"P25": 0.12, "P50": 0.32, "P67": 0.46, "P75": 0.55, "P90": 0.78},
  "consistency_within_10pct": {
    "P50": true,
    "P67": false,
    "P75": false
  },
  "per_seed_summary": [
    {"seed": 7, "quantiles": {"P25": 0.10, "P50": 0.30, "P67": 0.45, "P75": 0.55, "P90": 0.75}, "n": 117},
    {"seed": 13, "quantiles": {"P25": 0.12, "P50": 0.33, "P67": 0.47, "P75": 0.56, "P90": 0.80}, "n": 121},
    {"seed": 42, "quantiles": {"P25": 0.13, "P50": 0.34, "P67": 0.48, "P75": 0.55, "P90": 0.78}, "n": 113}
  ],
  "v3_anchor_validation_all_seeds": true
}
```

### 에러 케이스

| 상황 | 처리 |
|---|---|
| `case_c_events.json` 부재 | `FileNotFoundError` + 어떤 seed/파일 누락 명시 |
| `active_factions_snapshot` event 0건 (V3 raw 또는 재실행) | `AssertionError` + 9-a 검증 실패 명시 |
| V3 raw vs 재실행 fid set 불일치 (9-b 실패) | `AssertionError` + 어떤 seed/tick/diff 명시 + engine 결정성 재현 실패 가능성 보고 |
| `faction_charter_primitives(unknown_fid)` 호출 (faction 사라짐) | `KeyError` (engine 자체 raise) — 호출 전 active_fids 체크로 예방 의무 |
| 빈 charter pair (둘 다 빈 set) | JSON `null` 출력 (값 위조 금지). Python 메모리 표현은 `float('nan')` 유지 가능. summary에 카운트 보고. |
| 분위수 계산 nan-only | JSON `null` 출력 (`json.dump(..., allow_nan=False)` 호환). summary에 명시. |
| UTF-8 인코딩 실패 | 명시적 에러 + 출력 파일 부분 작성 방지 (atomic write 권장: 임시 파일 후 `replace`) |
| **brain·SNN·PersonaBrain import 시도** | **즉시 작업 중단 + 사용자 escalate** (R10 위반, 코어 게이트로 전환) — 본 spec 자체를 보류 처리 |

---

## 변경 파일

| 파일 | 작업 | 유형 |
|---|---|:---:|
| `Projects/personas/loom/scripts/phase17_phi4_cpcm_extractor.py` | 신규 | 분석 스크립트 |
| `Projects/personas/loom/data/phase17_phi4_cpcm/seed-{7,13,42}/overlap_distribution.json` | 신규 | 출력 |
| `Projects/personas/loom/data/phase17_phi4_cpcm/seed-{7,13,42}/summary.md` | 신규 | 출력 (UTF-8) |
| `Projects/personas/loom/data/phase17_phi4_cpcm/aggregate/overlap_distribution.json` | 신규 | 통합 출력 |
| `Projects/personas/loom/data/phase17_phi4_cpcm/aggregate/summary.md` | 신규 | 통합 출력 (UTF-8) |
| `Projects/personas/loom/data/phase17_phi4_cpcm/plots/*.png` | (선택) 신규 | 시각화 |

**변경 없음 (금지)**:
- `Projects/personas/loom/core/multi_tick_engine.py` (read-only API 호출만)
- `Projects/personas/loom/persona/*` (전체 디렉토리)
- `Projects/personas/loom/ontology/*` (전체 디렉토리)
- `Projects/personas/loom/brain/*` (존재 시 — touching 0건 보장)
- `Projects/personas/loom/snn/*` (존재 시 — touching 0건 보장)
- `Projects/personas/loom/test_phase17_acceptance.py` (acceptance 분리 spec과 정합)
- `Projects/personas/loom/PHASE-17-NATION-CHARTER-*.md` (charter 본문)
- `Projects/personas/loom/data/phase17_phi4_sis/*` (DC-1 출력 — touching 금지)
- 회귀 6종 테스트 파일 (rev.3 Q2 정정 — 목록 아래 명시)

---

## 검증

### 기계 검증
1. **타입 체크**: `python -m mypy scripts/phase17_phi4_cpcm_extractor.py` (프로젝트 기본 설정 따르기 — `pyproject.toml` / `mypy.ini` 의 [mypy] 섹션 기준)
   - 프로젝트 mypy 설정 미존재 시 fallback: `python -c "import ast; ast.parse(open('scripts/phase17_phi4_cpcm_extractor.py', encoding='utf-8').read())"` (최소 syntax check) + 그 사실을 보고에 명시
   - 프로젝트가 strict 미설정이면 본 신규 스크립트만 자체 strict 통과 보장 (모든 함수에 type annotation, `Any` 사용 0건). dependency 모듈(`multi_tick_engine` 등) 의 strict 검사는 시도하지 않음.
2. **린트**: `python -m ruff check scripts/phase17_phi4_cpcm_extractor.py` (ruff 미설정 시 동일하게 명시)
3. **실행**: `python scripts/phase17_phi4_cpcm_extractor.py` → 8 출력 파일 생성 확인 (3 seed × 2 + aggregate × 2)
4. **brain·SNN import 0건 확인**: `python -c "import ast; tree = ast.parse(open('scripts/phase17_phi4_cpcm_extractor.py', encoding='utf-8').read()); imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]; bad = [n for n in imports if any(b in (getattr(n, 'module', '') or '') or any(b in a.name for a in getattr(n, 'names', [])) for b in ['brain', 'snn', 'persona_brain', 'PersonaBrain'])]; assert not bad, bad"` — 어떤 형태의 brain/snn 모듈 import도 0건 확인.

### 기능 검증
- [ ] V3 seed-7/13/42 raw `case_c_events.json` 파싱 성공 (mojibake 무관)
- [ ] engine 결정성 재실행 (`MultiTickEngine(seed=seed)` × 20,000 ticks × 3 seed) 성공
- [ ] 매 500 tick에서 charter 추출 성공 (40 snapshot/seed)
- [ ] V3 anchor 매칭 (9-a/9-b/9-c) 모두 PASS — `AssertionError` 무발생
- [ ] pair-wise Jaccard 산출 (모든 active pair) — 빈 charter pair는 JSON `null`로 출력 (Python 내부 `float('nan')` 허용)
- [ ] **strict JSON parser 검증**: 8 출력 JSON 파일 모두 `json.loads(open(p, encoding='utf-8').read())`로 무에러 파싱 통과 (NaN literal 부재)
- [ ] `json.dump(..., allow_nan=False)` 사용 확인 (strict JSON contract — rev.3 Q1 정정)
- [ ] 분위수 P25/P50/P67/P75/P90 도출 (per seed × aggregate)
- [ ] 3 seed 분위수 일관성 ±10% boolean 출력 (P50/P67/P75 × 1 metric = 3 cells)
- [ ] summary.md 인코딩 UTF-8 명시 + 한글 깨짐 없음 (실제 텍스트 헤더 "분위수", "주의", "검증" 등으로 검증)

### 회귀 검증 (필수, DC-1과 동일 목록 — rev.3 Q2 정정: 7종 → 6종)
- [ ] 회귀 6종 테스트 PASS:
  1. `tests/test_phase14b_snn_integration.py`
  2. `tests/test_phase17_faction_handoff_contract.py`
  3. `tests/test_phase17_faction_stage3.py`
  4. `tests/test_phase17_acceptance.py` (3 known phi-3 EXPECTED FAIL 유지 + acceptance long-run 분리 spec b53c87a 정합 — `pytest -m "not slow"` 분 단위 PASS)
  5. `tests/test_economy.py` + `tests/test_economy_balance.py`
  6. `tests/test_class_promotion.py` + `tests/test_nomos.py`
- [ ] `git diff core/multi_tick_engine.py persona/ ontology/ brain/ snn/ test_phase17_acceptance.py` = empty 확인

> **rev.3 Q2 정정 근거**: `tests/test_persistence.py` (또는 동등 파일) 부재 확인 — `find Projects/personas/loom -name "test_persist*.py"` glob 매치 0건. DC-1 SIS rev.2 spec(line 406)에서 잘못 인용된 항목을 본 spec이 계승했던 결함을 소급 정정. DC-1 SIS spec도 별도 정정.

### V3 데이터 일치 검증 (필수, AssertionError 강제)
- [ ] **9-a**: per-seed engine 재실행 snapshot 발행 횟수 = **40** (V3 raw 동일)
- [ ] **9-b**: per-snapshot active fid set = V3 raw `active_factions_snapshot.faction_sizes` keys 일치 (3 seed × 40 snapshot 모두)
- [ ] **9-c**: per-snapshot V3 raw `active_count` = `len(faction_sizes)` (자기 정합)

### Anti-pattern 검증 (Codex Finding #3 + DC-1 §1.0 caveat 계승)
- [ ] 코드 어디에도 magic threshold (예: `>= 0.7`, `> 0.5`, `0.6 * jaccard + 0.4 * sovereignty`) 없음 — 분위수 도출까지만
- [ ] `charter_overlap_score` 또는 유사 변수가 의사결정 trigger로 사용되지 않음 — telemetry 출력만
- [ ] cosine similarity 사용 0건 (R2 closed)
- [ ] vector embedding / brain·SNN API touching 0건 (R10 closed) — `import` 정적 분석으로 확인
- [ ] DC-1 SIS `sovereignty_score`를 본 spec 입력으로 사용 0건 (§1.0 caveat — 결합점 분석은 별도 spec)

---

## Rollback

**bash/Linux**:
```bash
rm -rf Projects/personas/loom/data/phase17_phi4_cpcm/
rm Projects/personas/loom/scripts/phase17_phi4_cpcm_extractor.py
```

**PowerShell (Windows)**:
```powershell
Remove-Item -Recurse -Force Projects/personas/loom/data/phase17_phi4_cpcm/
Remove-Item Projects/personas/loom/scripts/phase17_phi4_cpcm_extractor.py
```

데이터 영향: 분석 산출물만 생성, mechanism / acceptance / brain·SNN 무변경 → rollback 안전. 회귀 6종 재실행 후 PASS 확인 권장 (rev.3 Q2 정정).

---

## 코어 영역 게이트 헤더 (§3.3.2)

```
- 코어 영역: 비코어 (telemetry helper, read-only 분석 스크립트)
- 변경 범위: 분석 스크립트 신규 + 출력 데이터. mechanism / acceptance / brain·SNN API 무변경.
- 정당화: CPCM Decision Card §3.7 1단(자연 측정) + 2단(분포 분석) + 4단(분위수 후보)
- R10 검증: faction_charter_primitives()는 5줄 pure accessor (multi_tick_engine.py:1733-1737). brain·SNN·PersonaBrain 호출 0건 확인 (2026-05-04).
- 대안 검토: N/A (비코어이므로 우회안 검토 불요)
- 사용자 사전 승인: 불요 (비코어)
- Codex 자율 구현 가능 (자율성 존중, 안전장치는 [금지] 경계)
- escalate 트리거: 본 spec 구현 도중 brain·SNN·PersonaBrain 모듈 touching 시도 발생 시 즉시 작업 중단 + 사용자 보고
```

---

## 참고 사항

- DC-2 본문: [PHASE-17-NATION-CHARTER-DECISION-CARDS.md](PHASE-17-NATION-CHARTER-DECISION-CARDS.md) §1차 비코어 DC-2
- Phase 3 잔여 spec DRAFT: [PHASE-17-NATION-PHASE3-SPEC-PIPELINE-DRAFT.md](PHASE-17-NATION-PHASE3-SPEC-PIPELINE-DRAFT.md) §1 ① DC-2 (rev.2 R1·R2·R3·R10)
- DC-1 SIS spec (rev.2 패턴 template): [PHASE-17-NATION-DC-1-SIS-SPEC.md](PHASE-17-NATION-DC-1-SIS-SPEC.md)
- DC-1 §1.0 caveat 출처: [data/phase17_phi4_sis/aggregate/distribution.json](data/phase17_phi4_sis/aggregate/distribution.json)
- acceptance long-run 분리 spec (commit b53c87a): [PHASE-17-ACCEPTANCE-LONGRUN-SPEC.md](PHASE-17-ACCEPTANCE-LONGRUN-SPEC.md)
- Codex 회신: [PHASE-17-NATION-CHARTER-REVIEW-RESPONSE-CODEX.md](PHASE-17-NATION-CHARTER-REVIEW-RESPONSE-CODEX.md) — Finding #2 B-2 (raw JSON canonical) + Finding #3 (임계 freeze 금지) 모두 준수
- §3.7 6단 사슬 + §3.3.2 코어 게이트: [LOOM-DIRECTION.md](LOOM-DIRECTION.md)
- Φ-4 STUB: [PHASE-17-NATION-CHARTER-STUB.md](PHASE-17-NATION-CHARTER-STUB.md) (OQ 4)
- V3 진단 보고서: [PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md](PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md)
- engine 진입점: [core/multi_tick_engine.py:1733-1737](core/multi_tick_engine.py#L1733-L1737) `faction_charter_primitives()`, [core/multi_tick_engine.py:805-824](core/multi_tick_engine.py#L805-L824) `active_factions_snapshot` 발행
- V3 probe runner 진입점 (참고): [observe_phase17_emergence.py:741-742](observe_phase17_emergence.py#L741-L742) `run_seed`
- 본 spec rev.1 범위: §3.7 1단 + 2단 + 4단 후보 (faction 단위 pair-wise Jaccard). 3단(SIS×CPCM 결합)·5단(3엔진 cross-check)·6단(closure)은 별도 spec.

---

## GPT/Codex 전달 프롬프트 템플릿

```
당신은 loom 프로젝트(페르소나 자율 사회 시뮬 + SNN 창발)의 시니어 Python 개발자입니다.

## 프로젝트 경로
c:\Users\haj\projects\subagent-orchestrator\Projects\personas\loom

## 기술 스택
Python 3.11+, numpy (이미 설치). Phase 17 Φ-3 closure 완료, Φ-4 Nation Charter design Phase 3 진행 중. DC-1 SIS [확정] 완료, DC-2 CPCM 본 spec.

## 작업 지시서
`Projects/personas/loom/PHASE-17-NATION-DC-2-CPCM-SPEC.md` (rev.2) 파일을 그대로 따라 구현하세요.

## 규칙 (절대 준수)
1. 지시서의 [필수] 항목 100% 구현. [금지] 항목 절대 건드리지 말 것.
2. 본 spec은 비코어 분석 스크립트. 코어(mechanism/acceptance/brain·SNN/persona/ontology) 변경 절대 금지 (단 1줄도 금지).
3. **script-level brain·SNN·PersonaBrain 모듈 import 0건** — 본 spec script 자체 안에서 `from persona.persona_brain`, `import brain`, `import snn`, vector embedding 라이브러리(`sentence_transformers`, `gensim` 등) 모두 금지. import 시도가 필요해지면 즉시 작업 중단하고 사용자에게 보고 (R10 escalate). **engine 재실행(`MultiTickEngine(seed=...)` + `engine.tick()`)은 허용** — engine 내부 brain 사용은 R10 trigger 아님 (engine은 black box). 자세한 정의는 spec §"R10 closed" 범위 정의 참조.
4. 메트릭 단위는 **faction**. persona / territory / vector 단위 분석은 본 spec 범위 외.
5. 알고리즘은 **Jaccard 단일** (set-based). cosine 사용 금지 (string sequence 부적합 + R10 위험).
6. 입력은 V3 raw `case_c_events.json` (anchor) + engine 결정성 재실행 (charter 추출). mojibake `summary.md` 사용 금지.
7. 모든 file open은 `encoding='utf-8'` 명시.
8. V3 anchor 검증은 `assert`로 강제 — 9-a/9-b/9-c 모두 PASS 필수. 실패 시 어떤 seed/tick/diff인지 명시.
9. 임계 분위수 magic threshold freeze 금지 — P25/P50/P67/P75/P90 분위수 후보 **도출만**. DC-1 §1.0 caveat 계승.
10. acceptance 테스트 파일(`test_phase17_acceptance.py`) 변경 절대 금지 (acceptance long-run 분리 spec b53c87a 정합).
11. 검증 순서:
    a. mypy + ruff (프로젝트 설정 사용, 미설정 시 ast.parse fallback + 그 사실 명시)
    b. brain·snn import 0건 정적 분석 통과
    c. 스크립트 실행 → 출력 파일 8개 확인 (3 seed × 2 + aggregate × 2)
    d. V3 anchor 검증 (9-a/9-b/9-c assert 통과)
    e. 회귀 6종 테스트 PASS (acceptance는 `pytest -m "not slow"`로 실행 — rev.3 Q2 정정)
    f. Anti-pattern 검증 (magic threshold 없음 + cosine 0건 + brain·SNN touching 0건)
12. 보고 내용:
    - 변경 파일 목록
    - 분위수 도출 결과 (per seed + aggregate, P25~P90)
    - 3 seed 일관성 자동 판정 결과 (P50/P67/P75 × ±10%)
    - V3 anchor 검증 결과 (snapshot count / fid set match / active_count self-consistency)
    - 회귀 6종 PASS 확인 (acceptance non-slow — rev.3 Q2 정정: test_persistence.py 부재로 7종 → 6종)
    - Anti-pattern 검증 결과 (4종)
    - **brain·SNN·PersonaBrain import 0건 정적 분석 결과**
    - **strict JSON parser 검증 결과**: 8 출력 JSON 모두 `json.loads`로 무에러 통과 (NaN literal 부재 — rev.3 Q1)
13. **Codex 자율성 존중 (rev.3 강화 — 근간 정의 + 승인 절차)**:
    - **자율 영역**: 함수 이름·시그니처·분할/통합·내부 흐름·중간 변수·예외 메시지 세부·atomic write 절차·로그 포맷·NaN→null 변환 helper 위치·numpy 처리 방식 등 — 자유
    - **근간 (수정 시 사용자 승인 필수)**: 코어 영역 / mechanism 무수정 / acceptance 무변경 / charter 본문 무변경 / 무파괴 9·안전 전제 5종·BOOST=0.20·회귀 6종 / §3.7 6단 사슬 / axis A/B/C 가드레일 + V3 anchor / 검증 contract (strict JSON / brain 0건 / git diff empty)
    - **근간 수정 필요시**: 즉시 작업 중단 + 사유·영향·대안 명시하여 사용자 escalate. 자가 판단으로 근간 수정 절대 금지.
    - R10 escalate 트리거 (brain·SNN touching 필요성 발생) 시 즉시 사용자 보고.
```

---

## rev.3 Hotfix Codex 위임 (NaN→null 정정 — engine 재실행 회피)

> **목적**: rev.2 Codex 1차 구현(스크립트 + 8 산출물)을 살리되, JSON 출력의 RFC 8259 비호환 NaN literal만 정정. 9388초 engine 재실행 회피.

### 위임 범위 (자율성 부여 — 근간 외 자율)

#### [근간 — 수정 시 사용자 승인 필수]

본 hotfix는 근간 무수정. 다음을 절대 보존:
1. mechanism / acceptance / charter 본문 / 코어 영역 (brain·SNN·PersonaBrain) 무touching
2. V3 anchor 9-a/9-b/9-c 검증 결과 (재실행하지 않으므로 변경 없음)
3. 분위수 결과(P25/P50/P67/P75/P90) 수치 보존 — 정정은 **표현(NaN→null)만**, 수치 보정 0건
4. consistency_within_10pct boolean 결과 보존
5. 무파괴 9 / 안전 전제 5종 / BOOST=0.20 / 회귀 6종

#### [필수]

1. **scripts/phase17_phi4_cpcm_extractor.py 정정**
   - `json.dump` 호출 시 `allow_nan=False` 명시
   - NaN 값을 `None`으로 변환하는 직렬화 helper 추가 (이름·위치 자율 — 예: `_nan_to_none`, `_serialize_metric`, dict comprehension inline 등)
   - per_snapshot dict 생성 시 `mean_jaccard / max_jaccard / min_jaccard`가 NaN인 경우 직렬화 단계에서 `null` 출력
   - aggregate은 이미 NaN 0건이므로 코드 경로 자체는 변경 없어도 무방 (`allow_nan=False`만 추가)
   - 수정 후 strict JSON parser로 자체 검증

2. **per-seed JSON 산출물 3개 NaN→null 치환**
   - `Projects/personas/loom/data/phase17_phi4_cpcm/seed-7/overlap_distribution.json` (NaN 57건)
   - `Projects/personas/loom/data/phase17_phi4_cpcm/seed-13/overlap_distribution.json` (NaN 39건)
   - `Projects/personas/loom/data/phase17_phi4_cpcm/seed-42/overlap_distribution.json` (NaN 36건)
   - 치환 방식: **자율** (sed in-place / Python 재직렬화 / 신규 스크립트 등 — 결과만 일치하면 됨)
   - aggregate JSON (`aggregate/overlap_distribution.json`)은 NaN 0건이므로 변경 불필요 (그러나 strict JSON 재검증은 수행)

3. **strict JSON 검증 (8 파일 모두)**
   ```python
   import json
   from pathlib import Path
   for p in Path("Projects/personas/loom/data/phase17_phi4_cpcm").rglob("*.json"):
       with p.open(encoding='utf-8') as f:
           json.loads(f.read())  # NaN literal 있으면 ValueError
   ```
   8 파일 모두 무에러 통과 확인.

4. **재실행 검증 (선택, 권장)**
   - 정정된 스크립트 1회 실행하여 결과 재현 일치 확인
   - 9388초 부담이지만 spec contract 100% 보장
   - 시간 부족 시 생략 가능 (위 1~3만으로도 hotfix 목적 달성)

#### [금지]

- engine 코드 변경 (`multi_tick_engine.py`, `persona/*`, `ontology/*` 1줄도 금지)
- 분위수 수치 변경 (rev.2 결과 보존 — JSON 표현만 정정)
- v3_anchor_validation 결과 변경
- per-seed `summary.md` 본문 변경 (NaN 표시 부분만 텍스트 정정 가능)
- brain·SNN·PersonaBrain script-level import 추가 (R10 trigger)

### 자율 영역 (Codex 재량)

- helper 함수 이름·위치·시그니처
- per-seed JSON 치환 방식 (sed / Python 재직렬화 / 신규 스크립트)
- 임시 파일 처리 절차 (atomic write 권장이지만 강제 아님)
- 변경 이력 주석·로그 메시지 포맷
- 1차 구현 vs hotfix 분할 commit 여부 (단일 commit이라도 무방 — 사용자 결정에 위임)

### 검증 (필수)

1. **타입 체크**: `python -m mypy scripts/phase17_phi4_cpcm_extractor.py` (프로젝트 설정 따르기)
2. **린트**: `python -m ruff check scripts/phase17_phi4_cpcm_extractor.py`
3. **strict JSON 검증**: 8 파일 모두 `json.loads` 무에러 통과
4. **NaN literal 정적 검색**: `grep -rn 'NaN\|: nan\b' Projects/personas/loom/data/phase17_phi4_cpcm/*.json` → 0건
5. **수치 보존 검증**: aggregate `aggregate_quantiles.P50` 값 변경 0건 (rev.2 = 0.5 보존)
6. **brain·SNN import 0건**: 기존 정적 분석 재실행
7. **회귀 6종 PASS** (rev.3 Q2 정정: test_persistence.py 제외)
8. **git diff 검증**: `git diff core/multi_tick_engine.py persona/ ontology/ brain/ snn/ test_phase17_acceptance.py` = empty

### 보고 내용

- 정정된 스크립트 변경 라인 (helper 추가 위치)
- 정정된 산출물 NaN literal 0건 확인 (grep 결과)
- strict JSON parser 8 파일 통과 확인
- 분위수 수치 보존 확인 (rev.2 결과 vs hotfix 결과 비교)
- 회귀 6종 PASS 확인
- (선택) 재실행 검증 결과
- 자율 결정 항목 명시 (helper 이름·치환 방식 등 어떻게 결정했는지 1줄)

### 위임 프롬프트 본문

```
당신은 loom 프로젝트의 시니어 Python 개발자입니다. DC-2 CPCM rev.2 1차 구현이 완료되었으나 (스크립트 + 8 산출물), JSON 출력에 RFC 8259 비호환 NaN literal 132건이 포함되어 있어 rev.3 hotfix 정정이 필요합니다.

## 프로젝트 경로
c:\Users\haj\projects\subagent-orchestrator\Projects\personas\loom

## 작업 지시서
`Projects/personas/loom/PHASE-17-NATION-DC-2-CPCM-SPEC.md` rev.3 §"rev.3 Hotfix Codex 위임 (NaN→null 정정)" 섹션을 따라 구현하세요.

## 핵심 규칙
1. **근간 무수정**: mechanism / acceptance / charter / 코어 영역 / 분위수 수치 / V3 anchor 결과 보존
2. **NaN→null 표현 정정만**: rev.2 결과 수치 변경 0건. JSON 직렬화 표현만 RFC 8259 호환으로
3. **자율 영역**: helper 이름·치환 방식·atomic write 절차 등 [필수]/[금지] 경계 안 모든 디테일 자유
4. **근간 수정 필요시**: 즉시 작업 중단 + 사용자 escalate
5. **검증 contract 의무**: `json.dump(..., allow_nan=False)` + 8 파일 strict JSON parser 무에러 + 분위수 수치 보존

## 검증 순서
spec §"검증 (필수)" 1~8 모두 PASS. 9388초 engine 재실행은 [선택] (시간 부족 시 생략 가능).

## 보고
spec §"보고 내용" 항목 모두 포함.
```
