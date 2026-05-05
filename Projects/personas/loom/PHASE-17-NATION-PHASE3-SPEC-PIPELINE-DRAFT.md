# Φ-4 Nation — Phase 3 잔여 spec 파이프라인 (검토 DRAFT rev.2)

**일자**: 2026-05-04
**rev**: rev.2 (rev.1 사용자 검토 REQUEST_CHANGES 반영)
**상태**: **재검토 요청 단계** (spec 본문 미작성 — 본 문서는 spec 작성 전 메타 인덱스)
**검토자 후보**: Claude(self-review) + Codex + Gemini(`gemini-3.1-pro`) 또는 `/spec-review`

---

## rev.1 → rev.2 변경 사유 (사용자 검토 finding 6종 반영)

| Finding | severity | rev.2 처리 |
|---|---|---|
| **F1** DC-2 CPCM 경계 — PersonaBrain primitive 가정 오류. repo에는 `faction_charter_primitives()` (faction 단위 기존 경로) 존재 | CRITICAL | DC-2 Canonical Input · 출력 단위 · helper 시그니처 모두 **faction 단위**로 정정. PersonaBrain/brain·SNN touching 시 즉시 **코어 escalate** 룰 명시. |
| **F2** DC-3 P5R 5 슬롯 조기 freeze 위험 — 미승인 코어 슬롯을 typed body로 박으면 "국가가 이미 있는 것처럼" 구조 굳음 | CRITICAL | P5R **v0 = 2 슬롯 (sovereignty, charter_overlap)만 [확정]**. 나머지 3 (dissolution_history / lord_replacement_history / federation_state)는 **reserved/provisional 문서 수준**으로 격하. typed body slot 금지. |
| **F3** 작업 순서 내부 충돌 — §0 표 우선순위와 §3 권장 순서 불일치 | MAJOR | canonical order 단일화: ③acceptance → ①DC-2 R1~R3 검증 → ①DC-2 spec → ④mojibake → ②P5R v0 또는 보류 결정 → ⑤사용자 사전 승인. §0 표·§3 그래프·§5 다음 단계 모두 동일 순서. |
| **F4** DC-1 결과 caveat 누락 — SIS aggregate 12 셀 중 2 셀만 ±10% 통과 (`dom_share P75 = 1.0` 동률, `cross_faction_lord_count P67 = 1.0` 동률). | CRITICAL | §1.0 신설 — "DC-1 SIS 결과는 exploratory telemetry. 국가 주권 점수 / branch rule / P5R body semantics로 **바로 승격 금지**"를 모든 후속 spec [금지]에 반복 명시. |
| **F5** acceptance split 범위 모호 — "테스트 본문 변경 금지" 강도가 marker 부여까지 차단 | MAJOR | rev.2 표현 정정: **"assertion / tick count / acceptance definition / expected-fail semantics 변경 금지. slow marker 부여 / 파일 분리 / conftest 등록은 infra 작업으로 허용."** 현재 mark 적용 1/11 사실 인용. |
| **F6** mojibake hotfix 검증 부족 — `encoding='utf-8'` 명시만으로 부족 | MAJOR | rev.2 [필수] 보강: **한국어 expected token check** (`분위수`, `주의`, `검증` 등). raw JSON에서 summary 재합성 우선 (probe 재실행 후순). |

**사용자 검토 좋은 점 4종 보존**:
1. 비코어 우선 + 코어 후순위 구조
2. FMR/NDP/LRT 사용자 사전 승인 차단
3. acceptance split + mojibake hotfix infra 분리
4. "측정 → 분포 → 후보 → cross-check → closure" 흐름

---

## 0. 요약

DC-1 SIS spec(rev.2)은 작성·구현·commit 완료 (`9f129f8`). 단 **DC-1 결과는 exploratory telemetry** (12 셀 중 2 셀만 ±10% 통과 — §1.0 caveat). 다음 단계는 잔여 4종 spec + 코어 3종 사전 승인.

| 순서 | 식별자 | 유형 | 코어 영역 | 사용자 사전 승인 | 진행 가능 시점 |
|:---:|---|---|---|---|---|
| **1** | **acceptance long-run 분리** | 인프라 (test 분리 + marker) | 비코어 | 불요 | **즉시** (가장 가벼움, infra 정합성 회복) |
| **2** | **DC-2 R1~R3 사전 검증** | 메타 (코드·데이터 확인) | 비코어 | 불요 | acceptance 진행 중 병행 가능 |
| **3** | **DC-2 CPCM** spec | 기능 (분석 스크립트) | 비코어 (단 brain·SNN touching 시 즉시 escalate) | 불요 (escalate 시 필요) | R1~R3 검증 통과 후 |
| **4** | **V3 mojibake hotfix** spec | 인프라 (인코딩 정정 / 재합성) | 비코어 | 불요 | DC-2 본 흐름과 독립 (병행 가능) |
| **5** | **DC-3 P5R v0 결정** (2 슬롯 freeze 또는 보류) | 문서 (interface shape) | 비코어 | 불요 | DC-2 [확정] 후 |
| **6** | **FMR / NDP / LRT 사용자 사전 승인** | 메타 (사용자 결정) | 코어 | **필수** | 비코어 4종 [확정] + Phase 4 Verify 통과 후 권고 |

본 DRAFT 통과 후: 1~5는 `/spec` 작성 → `/spec-review` → Codex 자율 위임. 6은 사용자 결정 받은 항목만 spec 작성 단계로 진입.

---

## 1.0 DC-1 결과 caveat (rev.2 신설, 모든 후속 spec [금지]에 반복 명시)

DC-1 SIS rev.2 1차 추출 결과 (V3 raw 3 seed × 28 windows, [data/phase17_phi4_sis/aggregate/distribution.json](data/phase17_phi4_sis/aggregate/distribution.json)):

| 메트릭 | P50 ±10% | P67 ±10% | P75 ±10% | 비고 |
|---|:---:|:---:|:---:|---|
| `dom_share` | ❌ (0.90/0.74/0.68) | ❌ (1.0/1.0/0.81) | ✅ (1.0/1.0/1.0) | P75만 동률로 통과 |
| `member_share` | ❌ | ❌ | ❌ | 일관성 부재 |
| `conflict_pair_count` | ❌ | ❌ | ❌ | 일관성 부재 |
| `cross_faction_lord_count` | ❌ | ✅ (1.0/1.0/1.0) | ❌ | P67만 동률로 통과 |

**요약**: 12 셀 중 **2 셀만** ±10% 통과 (`dom_share P75`, `cross_faction_lord_count P67`). 둘 다 동률(1.0)로 인한 통과 — 통계적 안정성이라기보다 ceiling effect.

**결론 (rev.2 모든 후속 spec [금지]에 반복 의무)**:
1. **SIS 결과는 exploratory telemetry**. 국가 주권 점수(`sovereignty_score`)로 **바로 승격 금지**.
2. **branch rule** (merge / federation / none)에 SIS 분위수를 **threshold freeze로 사용 금지**.
3. **P5R `nation.sovereignty` body semantics**에 SIS 분위수 값을 **고정 값으로 박지 말 것**. shape (type signature)만 [확정], body는 §3.7 5단(3엔진 cross-check) + 6단(closure) 통과 후.
4. DC-1 본 spec rev.2의 [금지] 조항 (magic threshold freeze, sovereignty_score를 mechanism trigger로 사용)을 **DC-2 / DC-3 / 후속 spec 모두 계승**.

---

## 1. 검토 요청 범위 (5개 항목)

### ① DC-2 CPCM — Charter Primitives Convergence Meter (rev.2 경계 정정)

| 항목 | 내용 |
|---|---|
| **OQ** | 4 (charter primitives 수렴 측정) |
| **유형** | 기능 (분석 스크립트, 1회성 데이터 추출) |
| **단위** | **faction** (rev.2 정정 — F1 반영) |
| **코어 영역** | **비코어** (read-only telemetry). **단**: PersonaBrain / `persona/persona_brain.py` / SNN API / `brain/*` 모듈을 touching 해야 할 상황이 발생하면 **즉시 코어 escalate** (사용자 사전 승인 필수, §3.3.2). |
| **§3.7 사슬** | 1단(자연 측정) + 2단(분포) + 4단(P50/P67/P75 후보) — DC-1 SIS와 동일 패턴. **3단(결합점)·5단(cross-check)·6단(closure)은 별도 spec**. |
| **선행** | DC-1 SIS rev.2 [확정] · `faction_charter_primitives()` (loom 내 기존 경로) 시그니처 검증 (R1) · V3 raw 3 seed 데이터 [확정] |
| **후행** | (a) SIS sovereignty와 결합 검토 (3단) — 별도 spec (b) Φ-5 P5R `nation.charter_overlap` 슬롯 type signature 출처 |

**Canonical Input** (rev.2 정정):
- **`faction_charter_primitives()` 함수** (loom repo 내 기존 경로 — `core/multi_tick_engine.py` 등 13개 파일에 등장 확인). spec 작성 전 R1에서 시그니처·반환 타입 확정.
- V3 raw `Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-{7,13,42}/` (faction state snapshot 출처)
- mojibake `summary.md` **사용 금지** (Codex Finding #2 B-2)

**[필수] (rev.2 정정)**:
1. **faction 단위** charter primitive 추출: `faction_charter_primitives(faction_id)` (read-only API) 호출. PersonaBrain·SNN touching **금지** (touching 발생 시 코어 escalate).
2. window 단위(720 ticks, DC-1과 동일) **active faction pair-wise** overlap 계산:
   - 1차 산출: **Jaccard** (set-based primitive 가정) — F1 사용자 권고 우선
   - 보조 산출: **cosine** (vector-based primitive일 경우) — R2 데이터 형태 확인 후 결정
3. window 단위 overlap 분포 도출 (per active faction pair × per window)
4. P25/P50/P67/P75/P90 분위수 후보 (per seed × aggregate, DC-1과 동일 양식)
5. seed 간 일관성 ±10% 자동 판정 (DC-1과 동일 양식). **DC-1 결과 caveat (§1.0) 정신 계승** — 일관성 셀 수치를 그대로 보고하되 threshold freeze 금지.
6. SIS sovereignty와 동일 window 결합점 후보 (3단 helper — separate function only, threshold freeze 금지)
7. 출력 파일 인코딩 `utf-8` 명시 (V3 mojibake 재발 방지)
8. V3 anchor 검증 — R3에서 anchor 확정 (후보 A: active faction count per seed / 후보 B: faction_charter_primitives 호출 가능성 / 후보 C: anchor 불요)

**[선택]**:
- pair overlap heatmap (matplotlib)
- charter primitive set 분포 분석

**[금지] (rev.2 강화)**:
- **brain·SNN API touching** (PersonaBrain / persona_brain.py / brain/* / snn/*) — 발생 시 즉시 코어 escalate
- charter primitive **주입·수렴 강제 mechanism** (top-down) — Codex Optional #2
- magic threshold freeze (예: `overlap >= 0.7` 결정 — Phase 17 STUB Entry Trigger 3번 인용 금지, charter 본문 변경 금지)
- **DC-1 SIS 결과를 sovereignty_score로 승격하여 trigger로 사용** (§1.0 caveat 계승)
- mojibake summary 사용
- mechanism 변경 (axis C)
- 무파괴 9 / 안전 전제 5종 / BOOST=0.20 / 회귀 7종 변경

**출력 파일** (예상):
```
Projects/personas/loom/scripts/phase17_phi4_cpcm_extractor.py        (신규)
Projects/personas/loom/data/phase17_phi4_cpcm/seed-{7,13,42}/        (신규)
  ├── overlap_distribution.json
  └── summary.md (utf-8 명시)
Projects/personas/loom/data/phase17_phi4_cpcm/aggregate/              (신규)
  ├── overlap_distribution.json
  └── summary.md (utf-8 명시)
```

**검증 핵심**:
- 회귀 7종 PASS (DC-1과 동일 목록)
- `git diff core/multi_tick_engine.py persona/ ontology/ snn/ brain/` = empty (코어 escalate 미발생 증명)
- Anti-pattern: magic threshold·primitive 주입·SNN API 변경 없음
- 한국어 토큰 (`분위수`, `주의`, `검증`) 출력 깨짐 없음

**위험·우려 (rev.2 갱신)**:
- **R1 (rev.2 갱신)**: `faction_charter_primitives()`의 정확한 위치(`core/multi_tick_engine.py` 또는 다른 모듈), 시그니처, 반환 타입 (set / dict / vector). spec 작성 전 R1 검증 의무.
- **R2 (rev.2 갱신)**: Jaccard 1차, cosine 보조. 데이터 형태가 set이면 cosine 불요. R1 검증 후 결정.
- **R3 (rev.2 갱신)**: V3 anchor — DC-1처럼 `cross_faction_lord_count delta 합 = 22/23/19` 같은 강한 anchor가 필요한가, 또는 active_factions_end = 2/2/2 같은 약한 anchor로 충분한가? R1 검증 결과로 결정.
- **R10 (신규)**: `faction_charter_primitives()`가 **PersonaBrain 내부 호출을 의존**하면 read-only이어도 brain · SNN 코드 영향 가능성. 함수 내부 구현 확인 후 escalate 여부 결정.

---

### ② DC-3 P5R — Φ-5 Read-only API Surface (rev.2: v0 2 슬롯만 freeze)

| 항목 | 내용 |
|---|---|
| **OQ** | 6 (Φ-5 인계) |
| **유형** | 문서 (interface shape declaration — Python `Protocol` 또는 `TypedDict`) |
| **코어 영역** | **비코어** (read-only API surface, body semantics 보류) |
| **§3.7 사슬** | 본 spec은 사슬 적용 대상 아님 (interface freeze는 측정·분석이 아니라 계약). 단 5 슬롯 body 정의는 향후 SIS/CPCM/NDP/LRT/FMR 안정화 후 별도 §3.7 6단 통과 필요. |
| **선행** | DC-1 SIS [확정 + 1차 추출 완료, §1.0 caveat 인지] · DC-2 CPCM [확정 후] · NDP/LRT/FMR [사용자 사전 승인 대기] |
| **후행** | 5 슬롯 body 정의 (단계적, 컴포넌트별 안정화 후) |

**rev.2 핵심 변경 (F2 반영)**:
- v0 = **2 슬롯만 [확정]**:
  - `nation.sovereignty` (← SIS rev.2 type signature)
  - `nation.charter_overlap` (← CPCM 확정 후 type signature)
- 나머지 3 슬롯은 **reserved/provisional 문서 수준**으로 격하 (typed body slot 금지):
  - `nation.dissolution_history` — **NDP 사용자 사전 승인 후** body 정의
  - `nation.lord_replacement_history` — **LRT 사용자 사전 승인 후** body 정의
  - `nation.federation_state` — **FMR 사용자 사전 승인 후** body 정의

**[필수] (rev.2 정정)**:
1. Python `typing.Protocol` 또는 `TypedDict`로 **2 슬롯만** shape 선언
2. 2 슬롯 type signature는 SIS rev.2 / CPCM 확정 출력 구조 기반 (§1.0 caveat — body 값 고정 금지, type 만)
3. **나머지 3 슬롯은 코드에 박지 않음**. README.md (또는 본 모듈의 module-level docstring)에 텍스트로만 다음 표기:
   ```
   Reserved (provisional, awaiting user pre-approval and §3.7 closure):
   - nation.dissolution_history (← NDP)
   - nation.lord_replacement_history (← LRT)
   - nation.federation_state (← FMR)
   ```
4. 방향성 명시: Φ-5 → Φ-4 → Φ-3 → Φ-2 → Φ-1 (단방향, 역방향 mutate 금지)
5. 본 파일은 코드 import 가능 (실행 가능한 Python module)
6. 파일 인코딩 utf-8 명시
7. **§1.0 DC-1 caveat 계승**: `nation.sovereignty` body semantics에 SIS 분위수 값을 고정으로 박지 말 것 — type signature만.

**[선택]**:
- 단위 테스트 (typing 검증, 실제 동작은 body 정의 후이므로 shape only 테스트만)
- 사용 예시 docstring (단, **placeholder 값** 사용 + 실제 값 freeze 금지)

**[금지] (rev.2 강화)**:
- **NDP / LRT / FMR 슬롯을 typed body로 박기** (구조 굳음 위험 — F2)
- read-write API (mutate 금지) — 안전 위반
- event-stream subscription (보류 — 1차 read-only 충분)
- body semantics 정의 (5 컴포넌트 안정화 전)
- DC-1 SIS 분위수 값을 body fixed value로 박기 (§1.0 caveat)
- charter 본문 변경
- mechanism / acceptance / brain·SNN API 변경

**출력 파일** (예상):
```
Projects/personas/loom/api/__init__.py                (신규)
Projects/personas/loom/api/nation_p5r.py              (신규, 2 슬롯 Protocol/TypedDict + reserved 텍스트)
Projects/personas/loom/api/README.md                  (신규, 보류 항목 + 단방향 계약 + §1.0 caveat 계승)
```

**검증 핵심**:
- `python -c "from Projects.personas.loom.api.nation_p5r import NationReadOnly"` import 성공
- mypy strict 통과 (또는 fallback 명시)
- 회귀 7종 PASS — interface declaration이므로 mechanism 영향 없어야 함
- **`nation_p5r.py`에 `dissolution_history` / `lord_replacement_history` / `federation_state` typed field 부재 확인** (텍스트 reserved만)

**위험·우려 (rev.2 갱신)**:
- **R4 (rev.2 갱신)**: P5R v0 = 2 슬롯이 의미 충분한가, 아니면 spec 자체를 보류하고 SIS+CPCM 양쪽 본 spec에 type signature를 export하는 방식으로 충분한가? **DRAFT 검토 결정 항목**.
- **R5 (rev.2 유지)**: module 경로 `loom/api/` vs `loom/ontology/` vs 신설 — 코드 구조 확인 후 결정.

---

### ③ acceptance long-run 분리 spec (rev.2 범위 명확화)

| 항목 | 내용 |
|---|---|
| **유형** | 인프라 (테스트 suite 분리, conftest mark 등록, slow marker 부여) |
| **코어 영역** | **비코어** (테스트 메타데이터 + marker 부여, mechanism 무수정) |
| **§3.7 사슬** | 본 spec은 사슬 적용 대상 아님 (테스트 인프라). |
| **선행** | Commit B-3 (`9175397`) acceptance 신규 4 테스트 + 일부 `@pytest.mark.slow` 추가 [확정] |
| **후행** | Phase 4 Verify 3엔진 cross-check 시 long-run 별도 stage로 실행 가능 |

**배경 (rev.2 보강 — F5 반영)**:
- Commit B-3에서 `test_phase17_acceptance.py`에 long-run 테스트(`ticks=5000`) 다수 + `@pytest.mark.slow` 추가.
- 그러나 **현재 mark 적용은 1/11** 만 ([test_phase17_acceptance.py:407-408](test_phase17_acceptance.py#L407) `test_grievance_propagate_natural_emergence`만). 다른 ticks=5000 테스트(line 347/360/422/437/447/473/487 등)는 marker 미적용.
- `conftest.py`에 `slow` mark 등록 누락 → `PytestUnknownMarkWarning` + `-m "not slow"` 필터 무효.
- 핵심 회귀(Stage 3 + Faction + 14B SNN 27 passed)는 검증 완료. acceptance long-run은 분리 suite로 운영 필요.

**[필수] (rev.2 정정)**:
1. `Projects/personas/loom/conftest.py`(존재 확인 후, 미존재면 신규)에 `slow` marker 등록:
   ```python
   def pytest_configure(config):
       config.addinivalue_line("markers", "slow: long-running tests (>= 1000 ticks)")
   ```
2. `pytest.ini` 또는 `pyproject.toml`에 동등 등록(둘 중 하나만 — 중복 금지)
3. **slow marker 부여 작업 (rev.2 명시 허용 범위)**: ticks ≥ 1000인 acceptance 테스트 전부에 `@pytest.mark.slow` 부여. 현재 1/11 → 11/11.
   - 부여 기준: tick 수 ≥ 1000 (acceptance suite 전체 검토)
   - 적용 대상 후보: line 347/360/422/437/447/473/487 등 (R6 검증 시 정확 목록 확정)
4. CI/검증 명령 분리:
   - 기본 회귀: `pytest -m "not slow"` (분 단위 실행 보장)
   - long-run: `pytest -m slow --timeout=600` (별도 stage)
5. 회귀 7종 + acceptance non-slow 모두 분 단위 PASS 보장
6. spec 본문에 명령 예시·timeout 값 명시

**[선택]**:
- pytest plugin `pytest-timeout` 의존성 명시
- GitHub Actions / 로컬 harness 양쪽 명령 가이드
- 별도 파일 분리 (`test_phase17_acceptance_longrun.py`) — marker만으로 부족할 시

**[금지] (rev.2 표현 정정 — F5 반영)**:
- **assertion 변경 금지**
- **tick count 변경 금지** (예: ticks=5000 → 1000으로 줄이기 금지)
- **acceptance definition 변경 금지** (테스트가 검증하는 acceptance criteria 자체)
- **expected-fail semantics 변경 금지** (`@pytest.mark.xfail` 등 기존 정책)
- mechanism / acceptance criteria / brain·SNN API 변경
- 회귀 7종 파일 touching (acceptance 외)
- charter 본문 변경

**rev.2 명시 허용**: slow marker 부여, 파일 분리, conftest 등록, pytest.ini 등록 — **infra 작업으로 허용**.

**출력 파일** (예상):
```
Projects/personas/loom/conftest.py                    (신규 또는 수정)
Projects/personas/loom/pytest.ini OR pyproject.toml   (수정 — 단 1개만)
Projects/personas/loom/test_phase17_acceptance.py     (수정 — slow marker 부여만)
Projects/personas/loom/PHASE-17-ACCEPTANCE-LONGRUN-RUNBOOK.md  (신규, 명령 가이드)
```

**검증 핵심**:
- `pytest -m "not slow"` 분 단위 PASS (acceptance long-run 제외)
- `pytest -m slow --timeout=600` 별도 stage PASS (또는 EXPECTED_FAIL 유지 — 기존 정책 그대로)
- 회귀 7종 PASS
- `git diff` — assertion / tick count / acceptance definition / expected-fail semantics **무변경 확인**

**위험·우려 (rev.2 갱신)**:
- **R6 (rev.2 갱신)**: `conftest.py` 존재 여부 + fixture 충돌. 존재하면 marker만 추가, 미존재면 신규.
- **R7 (rev.2 유지)**: Codex 위임 시 timeout 명시 (`feedback_codex_timeout` 정합).
- **R11 (신규)**: slow marker 부여 대상 정확 목록 — R6 검증 시 ticks ≥ 1000 테스트 전수 조사 의무. 누락 시 본 spec 효과 반감.

---

### ④ V3 SUMMARY mojibake hotfix spec (rev.2 검증 강화)

| 항목 | 내용 |
|---|---|
| **유형** | 인프라 (인코딩 정정 / **raw JSON에서 summary 재합성 우선**) |
| **코어 영역** | **비코어** (출력 파일 재생성, mechanism 무수정) |
| **§3.7 사슬** | 적용 외 (출력 인코딩 정정) |
| **선행** | V3 raw `case_c_events.json` + `metrics.jsonl` (3 seed) — **이미 utf-8 + 영문/JSON, 재실행 불요** |
| **후행** | DC-2 CPCM이 raw JSON 사용으로 우회하므로 본 hotfix는 차순 (Codex Finding #2 B-2 이미 채택). **Phase 3 본 흐름 차단 안 함**. |

**배경**:
- Codex Finding #2 (MINOR): `data/phase17_probe_phi3-case-c-diagnosis-v3/SUMMARY.md` + seed `summary.md`가 mojibake.
- Decision Cards에서 채택한 대응은 **B-2** (raw JSON canonical input). SIS/CPCM은 mojibake summary를 우회.
- 본 hotfix는 별도 작업 (Codex 권장 순서 2번).

**[필수] (rev.2 정정 — F6 반영)**:
1. **raw JSON에서 summary 재합성 우선** (probe 재실행 불요):
   - `case_c_events.json` + `metrics.jsonl`을 직접 파싱하여 summary.md 재생성
   - 별도 재합성 스크립트 신규 (`Projects/personas/loom/scripts/phase17_v3_summary_resynthesize.py`)
2. **probe 재실행은 차순 / 옵션** — 재합성으로 충분하면 probe 자체 touching 불요
3. 모든 file open `encoding='utf-8'` 명시
4. **한국어 expected token check (rev.2 신규)**:
   - 재생성 후 `summary.md`에 다음 토큰이 정확히 포함되는지 자동 검증:
     - `분위수`, `주의`, `검증`, `seed`, `tick`
   - assertion: 토큰 누락 / mojibake (cp949 변환 시 깨지는 패턴 — 예: `遺꾩쐞`, `二쇱쓽`) 발견 시 `AssertionError`
5. raw JSON (`case_c_events.json` / `metrics.jsonl`) 무변경 — `git diff data/phase17_probe_phi3-case-c-diagnosis-v3/seed-*/case_c_events.json` = empty
6. V3 진단 보고서 `PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md` §9 mojibake 항목 갱신 (해결됨 표기)

**[선택]**:
- mojibake 검증 helper (`def assert_no_mojibake(path)`) 추가 — 향후 모든 probe 출력에 적용 가능
- probe 스크립트 자체 정정 (재실행 불요지만 향후 재실행 시 mojibake 재발 방지)

**[금지]**:
- raw 데이터 (case_c_events.json / metrics.jsonl) 변경
- probe mechanism (V3 진단 자체) 변경
- DC-1 SIS rev.2 출력(`data/phase17_phi4_sis/`) touching — 이미 utf-8
- charter / mechanism / acceptance 변경
- 무파괴 9 / 안전 전제 5종 / BOOST=0.20 / 회귀 7종 변경

**출력 파일** (예상):
```
Projects/personas/loom/scripts/phase17_v3_summary_resynthesize.py     (신규, raw → summary 재합성)
Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-{7,13,42}/summary.md  (재생성)
Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/SUMMARY.md                 (재생성)
```

**검증 핵심**:
- 재생성 후 모든 summary가 utf-8 (한글 정상 출력)
- **expected token check 통과** (`분위수`/`주의`/`검증` 등 자동 assertion)
- raw JSON 무변경 (`git diff` empty)
- 회귀 7종 PASS

**위험·우려 (rev.2 갱신)**:
- **R8 (rev.2 갱신)**: V3 probe 스크립트 위치·이름 — **rev.2에서는 probe 재실행 불요로 격하**, 따라서 본 R 우선순위 낮음. 단, 정정 시 향후 재실행 안전.
- **R9 (rev.2 결정)**: probe 재실행 vs raw JSON에서 재합성 — **rev.2는 raw JSON 재합성 우선** (F6 반영). 재합성으로 충분하면 probe 무수정.

---

### ⑤ FMR / NDP / LRT 사전 승인 (코어, 사용자 결정 대기)

DECISION-CARDS Phase 3 2차 항목. **spec 작성 전에 사용자 결정 필수** (LOOM-DIRECTION §3.3.2 코어 게이트).

| 항목 | OQ | 코어 영역 | axis C 검증 핵심 |
|---|---|---|---|
| **FMR** Federation/Merge Resolver | 2 | mechanism logic | merge/federation/none 분기 함수 신설. 측정만으로는 환원 불가한 결정 함수. |
| **NDP** Nation Dissolution Path | 3 | mechanism + acceptance | dissolution event + Φ-3 재진입 신호. acceptance 정의 필요. |
| **LRT** Lord Replacement Trigger | 5 | mechanism logic | grievance + sovereignty 결합 → lord_replacement event. state 변경 mechanism. |

**사용자 결정 대기 양식** (DECISION-CARDS §사전 승인 요청 #1~#3):

```
사용자 결정: [ 승인 / 조건부 승인 / 거부 ]
조건부 승인 시 추가 요건:
  - /spec-review 또는 3엔진 cross-check 필수 (Codex Optional #4)
  - axis C 가드레일 OQ 7-a~e 자체 검증
  - §3.7 6단 사슬 처음부터 (1단 자연 측정 → 6단 closure)
  - DC-1 §1.0 caveat 계승: SIS 결과를 acceptance / threshold로 직접 사용 금지
거부 시 비코어 우회 방안 재검토 필요
```

**현 단계 결정 가이드 (rev.2)**:
- 비코어 4종(①~④) 작업 동안 사용자 결정 대기 가능
- 비코어 4종 모두 [확정] + Phase 4 Verify 3엔진 cross-check 통과 후 사전 승인 결정 권고 (`feedback_design_breadth_first` 정합)
- DC-3 P5R v0 (2 슬롯)에서 NDP/LRT/FMR 슬롯이 reserved/provisional이므로 사용자 사전 승인 결정이 P5R body 정의의 잠금 해제 키

---

## 2. 정합성 매트릭스

### 2-A. 사용자 행동 규칙 (메모리 5종) × 4 spec

| 메모리 | DC-2 CPCM | DC-3 P5R | acceptance 분리 | mojibake hotfix |
|---|---|---|---|---|
| `feedback_loom_goal_first` (3계층 목표) | ✅ Φ-4 charter 수렴 측정 | ✅ Φ-5 인계 read-only API | ✅ 회귀 인프라 | ✅ 검토자 신뢰 회복 |
| `feedback_snn_emergence_first` (SNN 창발 우선) | ✅ read-only telemetry, brain touching 시 escalate | ✅ shape only, mutate 금지 | ✅ mechanism 무수정 | ✅ raw 무수정 |
| `feedback_root_cause_first` (근본 원인 우선) | ⚠ R1·R3·R10 (faction_charter_primitives 시그니처·내부 brain 의존 검증) | ⚠ R4 (v0 2 슬롯 의미 검토) | ✅ slow mark 미등록 + 1/11 부여 = 근본 원인 | ✅ encoding 누락 = 근본 원인 |
| `feedback_design_breadth_first` (넓이 우선) | ✅ Phase 3 1차 비코어 동시 진행 | ✅ shape 동시 freeze (단 2 슬롯만) | ✅ 회귀 인프라 정합 | ✅ Phase 3 본 흐름 차단 안 함 |
| `feedback_design_verify_checklist` (4중 정합성) | DRAFT 본 문서 통과 필수 | DRAFT 본 문서 통과 필수 | DRAFT 본 문서 통과 필수 | DRAFT 본 문서 통과 필수 |

### 2-B. Codex Finding 3종 × 4 spec

| Finding | DC-2 CPCM | DC-3 P5R | acceptance 분리 | mojibake hotfix |
|---|---|---|---|---|
| #1 axis A spec 경로 | N/A | N/A | N/A | N/A (이미 DECISION-CARDS §Finding 처리) |
| #2 V3 SUMMARY mojibake | ✅ B-2 채택 (raw JSON canonical) | ✅ N/A (interface) | ✅ N/A | ⭐ **본 hotfix가 처리** |
| #3 SIS 임계 freeze 금지 | ✅ overlap 임계 freeze 금지 (동형 적용) + §1.0 caveat 계승 | ✅ shape only, body 보류, §1.0 caveat 계승 (sovereignty body 값 고정 금지) | N/A | N/A |

### 2-C. DECISION-CARDS [확정] 요건 × 4 spec

| Decision Card | 1차 spec 작성 가능? | 차단 항목 |
|---|---|---|
| DC-1 SIS | ✅ rev.2 [확정] · 구현 commit 완료. **단 §1.0 caveat 적용 — exploratory telemetry** | — |
| DC-2 CPCM | ⚠ DRAFT 통과 필요 | R1 (faction_charter_primitives 시그니처) · R2 (Jaccard/cosine) · R3 (V3 anchor) · R10 (brain 의존 escalate) |
| DC-3 P5R | ⚠ DRAFT 통과 필요 | R4 (v0 2 슬롯 vs 보류) · R5 (module 경로) |
| DC-4 NDP | 🛑 사용자 사전 승인 대기 (코어) | 사용자 결정 |
| DC-5 LRT | 🛑 사용자 사전 승인 대기 (코어) | 사용자 결정 |
| DC-6 FMR | 🛑 사용자 사전 승인 대기 (코어) | 사용자 결정 |

### 2-D. 무파괴 9 / 안전 전제 5종 / BOOST=0.20 / 회귀 7종 × 4 spec

전부 **무변경 [금지]**. spec 본문 [금지] 섹션에 반복 명시 필수. Codex 위임 시 회귀 7종 PASS 검증 의무.

### 2-E. DC-1 §1.0 caveat 계승 × 4 spec (rev.2 신설)

| Spec | §1.0 caveat 적용 방식 |
|---|---|
| DC-2 CPCM | overlap 분위수 결과를 trigger / threshold freeze로 사용 금지 |
| DC-3 P5R | sovereignty / charter_overlap body 값을 고정 값으로 박지 말 것 (type signature만) |
| acceptance 분리 | N/A (테스트 인프라이므로 caveat 무관) |
| mojibake hotfix | N/A (인코딩 정정이므로 caveat 무관) |

---

## 3. 의존 시퀀스 그래프 (rev.2 canonical order)

```
[V3 raw 3 seed × 20,000틱]      ← Φ-3 closure-v2 + V3 진단 (확정)
        │
        ├── DC-1 SIS rev.2 ──────────────────── [확정] 완료 (9f129f8)
        │       └── §1.0 caveat: 12 셀 중 2 셀만 ±10% 통과 — exploratory telemetry
        │
        ▼ canonical order (rev.2):

  [1] acceptance long-run 분리 ─────── 즉시 (가장 가벼움, infra 정합성 회복)
        │   slow marker 1/11 → 11/11 부여 + conftest 등록
        ▼
  [2] DC-2 R1~R3 사전 검증 ──────────── 코드·데이터 확인
        │   R1 faction_charter_primitives 시그니처
        │   R2 Jaccard vs cosine 데이터 형태
        │   R3 V3 anchor 후보
        │   R10 brain 내부 의존 (escalate 여부)
        ▼
  [3] DC-2 CPCM spec ─────────────────── R1~R3 통과 후
        │   faction 단위 read-only telemetry
        │   §1.0 caveat 계승
        │
        ├──── 병행 가능 (독립) ────►  [4] V3 mojibake hotfix spec
        │                                raw JSON 재합성 우선
        │                                expected token check
        ▼
  [5] DC-3 P5R v0 결정 ──────────────── DC-2 [확정] 후
        │   2 슬롯 freeze vs 본 spec 보류 (R4)
        │
        ├──── 비코어 4종 [확정] 후 ─►  [Phase 3 1차 closure 보고서]
        │
        ▼
  [6] FMR / NDP / LRT 사용자 사전 승인 ─ 사용자 결정
        │   승인 시 → /spec-review 또는 3엔진 cross-check → spec
        ▼
  [Phase 4 Verify 3엔진 cross-check (Gemini=gemini-3.1-pro)]
        ▼
  [Phase 5 Package — Charter 본문 + DC 6 + Φ-5 P5R body (단계적)]
```

---

## 4. 검토자 가이드 (외부 검토 시 확인할 것)

### 4-A. 정합성 (rev.2 갱신)
1. 4 spec이 사용자 행동 규칙 5종(메모리)과 충돌하지 않는가?
2. 4 spec이 Codex Finding 3종을 모두 반영하는가?
3. 4 spec이 DECISION-CARDS [확정] 본문과 일치하는가?
4. 4 spec이 무파괴 9 / 안전 전제 5종 / BOOST=0.20 / 회귀 7종을 모두 [금지]에 명시하는가?
5. 4 spec이 §3.3.2 코어 게이트를 정확히 판정(비코어)하는가?
6. **4 spec이 DC-1 §1.0 caveat을 계승하는가?** (rev.2 신설)
7. **DC-2가 PersonaBrain·SNN touching 시 코어 escalate 룰을 명시하는가?** (rev.2 F1)
8. **DC-3 P5R이 NDP/LRT/FMR을 typed body로 박지 않는가?** (rev.2 F2)
9. **acceptance 분리가 assertion / tick count / acceptance definition / expected-fail 변경을 차단하는가?** (rev.2 F5)
10. **mojibake hotfix가 한국어 expected token check를 의무화하는가?** (rev.2 F6)

### 4-B. 미해결·결정 요청 항목 (R1~R11)
- **R1** (DC-2): `faction_charter_primitives()` 정확한 위치·시그니처·반환 타입
- **R2** (DC-2): Jaccard 1차 / cosine 보조 결정 (R1 결과 의존)
- **R3** (DC-2): V3 anchor 후보 — active_factions_end vs 별도 anchor
- **R4** (DC-3): v0 2 슬롯 freeze vs spec 보류
- **R5** (DC-3): module 경로 `loom/api/` vs `loom/ontology/` vs 신설
- **R6** (acceptance): `conftest.py` 존재 + fixture 충돌
- **R7** (acceptance): Codex 위임 시 timeout 명시
- **R8** (mojibake): probe 스크립트 위치 (rev.2: 우선순위 낮음)
- **R9** (mojibake): rev.2 결정 — raw JSON 재합성 우선
- **R10** (DC-2 신규): `faction_charter_primitives()`가 brain 내부 호출 의존 시 escalate 판정
- **R11** (acceptance 신규): slow marker 부여 대상 정확 목록 (ticks ≥ 1000 전수)

### 4-C. 의존 시퀀스 합리성 (rev.2)
- canonical order 단일화 — §0 표 / §3 그래프 / §5 다음 단계 모두 동일?
- acceptance가 1번 (가장 가벼움) → DC-2 검증 (2번) → DC-2 spec (3번) → mojibake (4번 병행) → DC-3 결정 (5번) 순서 합리적?

### 4-D. 위험 평가
- DC-2의 R1·R10 (PersonaBrain 의존) 발생 시 escalate 판정 기준이 명확한가?
- DC-3의 R4 (v0 2 슬롯) 발생 시 P5R 본 spec을 작성 자체 보류로 전환할지 판단 기준이 명확한가?
- acceptance R11 (marker 부여 대상 누락) 발생 시 본 spec 효과 반감을 방지할 수 있는가?

---

## 5. 검토 후 다음 단계 (rev.2 canonical order)

본 DRAFT rev.2 통과 시 (canonical order):

1. `Projects/personas/loom/PHASE-17-ACCEPTANCE-LONGRUN-SPEC.md` 작성 → Codex 위임 (가장 가벼움)
2. **DC-2 R1~R3·R10 사전 검증** (코드 read + V3 raw 검증) — 본 DRAFT rev.3 또는 별도 검증 보고서
3. `Projects/personas/loom/PHASE-17-NATION-DC-2-CPCM-SPEC.md` 작성 → `/spec-review` → Codex 위임
4. `Projects/personas/loom/PHASE-17-V3-MOJIBAKE-HOTFIX-SPEC.md` 작성 → Codex 위임 (3과 병행 가능)
5. **DC-3 P5R v0 결정** — 2 슬롯 freeze 진행 vs spec 보류
   - 진행 시: `Projects/personas/loom/PHASE-17-NATION-DC-3-P5R-SPEC.md` 작성 → Codex 위임
   - 보류 시: 보류 사유 문서화 + DC-2 본 spec에 type signature export 보강
6. Phase 3 1차 closure 보고서 (DC-1, DC-2, DC-3 결정 모두 [확정])
7. 사용자 FMR/NDP/LRT 사전 승인 결정
8. Phase 4 Verify
9. Phase 5 Package

본 DRAFT rev.2가 REQUEST_CHANGES 받을 시:
- finding별 보강 → DRAFT rev.3

---

## 6. 메타

- 작성자: Claude (loom 설계 담당, 2026-05-04)
- rev.1 → rev.2: 사용자 검토 REQUEST_CHANGES (F1~F6) 반영
- rev.2 [확정] 조건: 외부 검토자(사용자 / Codex / `/spec-review` / 3엔진 cross-check) 1개 이상 APPROVE 또는 APPROVE_WITH_NOTES
- 본 DRAFT 인코딩: utf-8 (mojibake 방지)
- 참고:
  - [PHASE-17-NATION-CHARTER-DECISION-CARDS.md](PHASE-17-NATION-CHARTER-DECISION-CARDS.md) (DC 본문)
  - [PHASE-17-NATION-CHARTER-REVIEW-RESPONSE-CODEX.md](PHASE-17-NATION-CHARTER-REVIEW-RESPONSE-CODEX.md) (Codex Finding)
  - [PHASE-17-NATION-DC-1-SIS-SPEC.md](PHASE-17-NATION-DC-1-SIS-SPEC.md) (rev.2 template)
  - [data/phase17_phi4_sis/aggregate/distribution.json](data/phase17_phi4_sis/aggregate/distribution.json) (§1.0 DC-1 결과 caveat 출처)
  - [LOOM-DIRECTION.md](LOOM-DIRECTION.md) (§3.3.1/§3.3.2/§3.7)
  - [PHASE-17-NATION-CHARTER-STUB.md](PHASE-17-NATION-CHARTER-STUB.md) (Φ-4 STUB OQ 1~6 + 7-a~e)
