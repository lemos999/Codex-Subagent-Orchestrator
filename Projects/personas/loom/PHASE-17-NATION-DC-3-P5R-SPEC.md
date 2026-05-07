# [문서·인터페이스] DC-3 P5R — Φ-5 Read-only API Surface (v0: 2 슬롯 freeze)

> 긴급도: 보통
> 선행 조건: DC-1 SIS [확정 + 1차 추출 완료, §1.0 caveat 인지] · DC-2 CPCM [확정 후] · NDP/LRT/FMR [사용자 사전 승인 완료, 2026-05-07]
> 작업 유형: **문서 (interface shape declaration — Python `Protocol` + `TypedDict`)**
> DB migration: 없음
> 외부 의존: 없음 (Python 표준 라이브러리 `typing`만)
> **코어 영역 판정**: **비코어** (read-only API surface, body semantics 보류). 게이트 §3.3.2 **불요**
> **canonical order**: [PHASE-17-NATION-PHASE3-SPEC-PIPELINE-DRAFT.md](PHASE-17-NATION-PHASE3-SPEC-PIPELINE-DRAFT.md) §0 표 5번 (DC-2 [확정] 후)
> **rev**: rev.2 (Step 3.5 검증 후속 — Finding 1/2 정정)

---

## 변경 이력

- **rev.1** (2026-05-07): PIPELINE-DRAFT.md F2 권고 채택 + 사용자 명시 결정 (2026-05-07 "권고대로") 반영. P5R v0 = 2 슬롯 freeze 진행 (옵션 A). NDP/LRT/FMR 사전 승인 완료 (3종 모두 [승인]).
- **rev.2** (2026-05-07): Step 3.5 검증 (3 reviewer 만장일치 Finding 1 — `NationCharterOverlap` hidden coupling, Finding 2 — 회귀 4-way 불일치, Option C Hybrid 채택) 후속 정정.
  - (a) `NationCharterOverlap.overlap_score` / `primitive_count` → `mean_jaccard` / `pair_count` (CPCM rev.3 출력 JSON key mirror — hidden coupling 제거, producer truth surface 정합)
  - (b) V-3 회귀 절 → 신규 `PHASE-17-NATION-PHASE3-REGRESSION-CONTRACT.md` Tier 1 reference로 교체 (workspace 실재 7종, 4-way 불일치 해소)
  - (c) DC-1 / DC-2 [확정] spec 본문 무변경 (본 spec [금지] 6/7 + 회귀 contract 위계 분리 준수)
  - (d) Gemini 무응답으로 §3.7 5단 부분 충족 부족 (Option C 후반부 평가 결과). closure 보고서에 명시 — 본 spec 자체에는 영향 없음 (interface 정합·회귀 단일화는 3엔진 만장일치 영역).

---

## 배경

LOOM Phase 17 Φ-4 Nation Charter Phase 3 Decision Card DC-3 — Φ-5 Read-only API Surface 1차안.

### 정책 결정 (2026-05-07)

| 결정 | 채택안 | 근거 |
|---|---|---|
| **P5R v0 범위** | 옵션 A — 2 슬롯 freeze | F2 권고 + Charter STUB 일관 + Φ-5 인계 interface 보존 |
| **NDP/LRT/FMR 사전 승인** | 3종 모두 [승인] | DC-3 3 슬롯 잠금 해제 키. mechanism은 별도 cross-check 통과 후 신설 |

### v0 핵심 원칙

1. **interface freeze는 측정·분석 아닌 계약** — §3.7 6단 사슬 적용 외
2. **2 슬롯만 type signature [확정]** — `nation.sovereignty` (← SIS rev.2) + `nation.charter_overlap` (← CPCM 확정 후)
3. **3 슬롯 reserved/provisional** — `dissolution_history` (← NDP) / `lord_replacement_history` (← LRT) / `federation_state` (← FMR). **typed body slot 금지** (구조 굳음 회피)
4. **§1.0 DC-1 caveat 계승** — body 값 고정 금지, type signature만
5. **단방향 계약** — Φ-5 → Φ-4 → Φ-3 → Φ-2 → Φ-1 (역방향 mutate 금지)

---

## 작업 범위

### [필수] 7종

1. **`Projects/personas/loom/api/__init__.py` 신규**
   - 빈 파일 또는 `from .nation_p5r import NationReadOnly, NationSovereignty, NationCharterOverlap` re-export
   - encoding utf-8 명시 (또는 ASCII only)

2. **`Projects/personas/loom/api/nation_p5r.py` 신규 — 2 슬롯 type signature**
   - Python `typing.Protocol` 또는 `TypedDict` 사용 (Codex 자율 — 둘 중 선택)
   - 2 슬롯 declaration:
     - `nation.sovereignty` shape — SIS rev.2 출력(`distribution.json` aggregate) 구조 기반
     - `nation.charter_overlap` shape — CPCM 확정 후 출력 구조 기반
   - 파일 인코딩 utf-8 명시 (`# -*- coding: utf-8 -*-` 또는 자동)

3. **3 슬롯 reserved 텍스트 표기 — typed field 부재 강제**
   - `nation_p5r.py` module-level docstring 또는 별도 README.md에 다음 텍스트 (정확히):
     ```
     Reserved (provisional, awaiting §3.7 closure for each component):
     - nation.dissolution_history (← NDP) — body defined after NDP §3.7 6단 closure
     - nation.lord_replacement_history (← LRT) — body defined after LRT §3.7 6단 closure
     - nation.federation_state (← FMR) — body defined after FMR §3.7 6단 closure
     ```
   - **`dissolution_history` / `lord_replacement_history` / `federation_state` 어느 것도 typed field로 박지 않음** (검증 §V-4)

4. **단방향 계약 명시** — module docstring 또는 README에:
   ```
   Direction: Φ-5 → Φ-4 → Φ-3 → Φ-2 → Φ-1 (read-only, no reverse mutation)
   ```

5. **`Projects/personas/loom/api/README.md` 신규**
   - 보류 항목 (3 슬롯 reserved) 목록
   - 단방향 계약 명시
   - §1.0 DC-1 caveat 계승 명시 ("sovereignty body semantics는 SIS 분위수 값을 고정으로 박지 말 것 — type signature만")
   - encoding utf-8 명시

6. **`nation.sovereignty` body semantics 고정 금지 (§1.0 caveat)**
   - 2 슬롯의 type signature는 SIS rev.2 / CPCM 출력 **구조**만 기반
   - SIS의 P50/P67/P75 분위수 값은 **type 내부에 fixed value로 박지 않음**
   - body semantics는 `nation.sovereignty: dict[...]` 같은 generic shape만 (실제 value는 runtime 시점)

7. **모든 파일 utf-8 인코딩 + 한국어 토큰 0 (영문/ASCII only)**
   - API surface는 외부 인계용이라 영문 일관 권장
   - 단 README.md에는 한국어 보충 설명 허용 (utf-8 명시 시)

### [선택]

- 단위 테스트 (`tests/test_nation_p5r_shape.py`) — typing 검증만, body 검증 금지
- 사용 예시 docstring — **placeholder 값** 사용 (실제 값 freeze 금지)
- mypy strict 통과

### [금지] 8종

1. **NDP / LRT / FMR 슬롯을 typed body로 박기** (구조 굳음 회피 — F2)
2. **read-write API 신설** — mutate 금지, 안전 위반
3. **event-stream subscription** — 보류 (1차 read-only 충분)
4. **body semantics 정의** — 5 컴포넌트 안정화 전 fixed value 박기 금지
5. **DC-1 SIS 분위수 값을 body fixed value로 박기** (§1.0 caveat)
6. **charter / mechanism / acceptance / brain·SNN API 변경**
7. **무파괴 9 / 안전 전제 5종 / BOOST=0.20 / 회귀 7종 변경**
8. **외부 의존성 추가** (Python 표준 `typing`만 사용)

---

## 구체 사양

### 1. nation_p5r.py 권장 구조 (Codex 자율 — Protocol vs TypedDict)

#### 옵션 A — Protocol (structural typing, 권장)

```python
"""Φ-5 Read-only API Surface for Nation entity (v0: 2 slot freeze).

Direction: Φ-5 → Φ-4 → Φ-3 → Φ-2 → Φ-1 (read-only, no reverse mutation)

Reserved (provisional, awaiting §3.7 closure for each component):
- nation.dissolution_history (← NDP) — body defined after NDP §3.7 6단 closure
- nation.lord_replacement_history (← LRT) — body defined after LRT §3.7 6단 closure
- nation.federation_state (← FMR) — body defined after FMR §3.7 6단 closure

§1.0 DC-1 caveat: sovereignty body semantics must NOT freeze SIS quantile values.
Only the structural type is contracted here; runtime values are dynamic.
"""

from __future__ import annotations
from typing import Protocol, runtime_checkable, Any


@runtime_checkable
class NationSovereignty(Protocol):
    """Sovereignty intensity surface (← SIS rev.2 distribution.json shape).

    Body semantics deferred per §1.0 caveat. Structural shape only.
    """
    @property
    def dom_share(self) -> float: ...
    @property
    def member_share_per_faction(self) -> dict[str, float]: ...
    @property
    def conflict_pair_count(self) -> int: ...
    @property
    def cross_faction_lord_count(self) -> int: ...


@runtime_checkable
class NationCharterOverlap(Protocol):
    """Charter primitive overlap surface (← CPCM rev.3 출력 JSON keys mirror).

    Body semantics deferred per §1.0 caveat. Structural shape only.
    Field names MIRROR DC-2 CPCM rev.3 SnapshotMetrics keys (no rename, no aggregate)
    to keep producer→consumer truth surface intact (Step 3.5 Finding 1 정정).
    Runtime values are dynamic — type signature only, no fixed values baked.
    """
    @property
    def mean_jaccard(self) -> float: ...   # ← CPCM SnapshotMetrics.mean_jaccard (per snapshot)
    @property
    def pair_count(self) -> int: ...        # ← CPCM SnapshotMetrics.pair_count (per snapshot)


@runtime_checkable
class NationReadOnly(Protocol):
    """Φ-5 read-only consumer surface for a nation entity.

    v0: 2 slots frozen (sovereignty + charter_overlap).
    Reserved 3 slots (dissolution_history / lord_replacement_history /
    federation_state) are NOT exposed as typed fields until each component
    passes §3.7 6단 closure.
    """
    @property
    def sovereignty(self) -> NationSovereignty: ...
    @property
    def charter_overlap(self) -> NationCharterOverlap: ...
```

#### 옵션 B — TypedDict (nominal, 대안)

Codex 판단으로 TypedDict가 더 적합하면 채택 가능. 단:
- `total=False` 사용 권장 (선택 필드)
- `dissolution_history` / `lord_replacement_history` / `federation_state` 키 부재 강제

### 2. README.md 권장 구조

```markdown
# Loom API — Φ-5 Read-only Surface (v0)

## v0 frozen slots (2)

- `nation.sovereignty` (← DC-1 SIS rev.2 type signature)
- `nation.charter_overlap` (← DC-2 CPCM 확정 후 type signature)

## Reserved (provisional, awaiting §3.7 closure)

- `nation.dissolution_history` (← NDP) — pre-approved 2026-05-07, awaiting mechanism spec + cross-check
- `nation.lord_replacement_history` (← LRT) — pre-approved 2026-05-07, awaiting mechanism spec + cross-check
- `nation.federation_state` (← FMR) — pre-approved 2026-05-07, awaiting mechanism spec + cross-check

## Direction contract

Φ-5 → Φ-4 → Φ-3 → Φ-2 → Φ-1 (read-only, no reverse mutation).

## §1.0 DC-1 caveat inheritance

`nation.sovereignty` body semantics MUST NOT bake SIS quantile values
(P50/P67/P75) as fixed types. Type signature only — runtime values are dynamic
and may shift across §3.7 closure cycles.
```

### 3. Codex 자율성 정책

#### 자율 영역 (Codex 자율 결정 가능)

- Protocol vs TypedDict 선택
- 2 슬롯 type signature 세부 구조 (SIS rev.2 / CPCM 출력 shape에 충실하면 OK)
- module-level docstring vs README.md 분리 비중
- import re-export 방식 (`__init__.py` 재노출 여부)
- mypy strict pragma
- 단위 테스트 추가 여부 (선택)

#### 근간 (사용자 승인 없이 수정 금지)

1. 2 슬롯 freeze 범위 (sovereignty + charter_overlap만 — 추가 금지)
2. 3 슬롯 reserved 텍스트만 표기 (typed field로 격상 금지)
3. body semantics 고정 (DC-1 §1.0 caveat 위반 금지)
4. read-write 또는 mutate API 신설 금지
5. mechanism / acceptance / charter / brain·SNN 변경 금지
6. 외부 의존성 추가 금지 (typing 표준만)
7. 회귀 7종 / 무파괴 9 / 안전 전제 5종 / BOOST=0.20 변경 금지
8. SIS 분위수 값을 body fixed value로 박기 금지

#### 승인 절차 (근간 수정 필요 시)

본 spec [금지] 위반 가능성 발견 → 즉시 작업 중단 → 사용자 보고 → 사용자 명시 승인 후 spec rev.2 작성 → 재진입

---

## 변경 파일

| 파일 | 작업 | 유형 |
|---|---|:---:|
| `Projects/personas/loom/api/__init__.py` | 신규 작성 | 추가 |
| `Projects/personas/loom/api/nation_p5r.py` | 신규 작성 (2 슬롯 Protocol/TypedDict + reserved 텍스트) | 추가 |
| `Projects/personas/loom/api/README.md` | 신규 작성 (보류 항목 + 단방향 계약 + caveat 계승) | 추가 |

총 3 파일 (모두 신규 추가).

**변경 없음 (금지) — git diff --stat 무 출력 검증 의무**:
- `Projects/personas/loom/core/`
- `Projects/personas/loom/persona/`
- `Projects/personas/loom/ontology/`
- `Projects/personas/loom/brain/`
- `Projects/personas/loom/snn/`
- `Projects/personas/loom/physis/`
- `Projects/personas/loom/test_phase17_acceptance.py`
- `Projects/personas/loom/conftest.py`
- 모든 `PHASE-17-*-CHARTER*.md`
- `PHASE-17-NATION-DC-1-SIS-SPEC.md`
- `PHASE-17-NATION-DC-2-CPCM-SPEC.md`
- 모든 `data/phase17_*` 산출물

---

## 검증 contract (5종)

### V-1. import 성공

```bash
cd Projects/personas/loom
py -c "from api.nation_p5r import NationReadOnly, NationSovereignty, NationCharterOverlap"
# 무 에러 = PASS
```

### V-2. mypy strict 통과 (또는 fallback 명시)

```bash
py -3.12 -m mypy --strict Projects/personas/loom/api/nation_p5r.py
# 무 에러 = PASS, 또는 환경 미설정 명시 보고
```

### V-3. 회귀 7종 PASS — `PHASE-17-NATION-PHASE3-REGRESSION-CONTRACT.md` Tier 1 reference

회귀 목록 단일 권위는 본 spec이 아닌 별도 contract 문서. 본 spec은 reference만 (Step 3.5 Finding 2 정정 — single source of truth 부재 해소).

**reference**: [PHASE-17-NATION-PHASE3-REGRESSION-CONTRACT.md](PHASE-17-NATION-PHASE3-REGRESSION-CONTRACT.md) §Tier 1 (workspace 실재 7종)

```bash
cd Projects/personas/loom
py -m pytest \
  test_phase17_acceptance.py \
  test_phase17_faction.py \
  test_phase17_faction_stage3.py \
  test_phase17_faction_regression.py \
  test_phase17_faction_handoff_contract.py \
  test_phase14b_snn_integration.py \
  test_phase17_land.py \
  -q
```

interface declaration이므로 mechanism 무영향 = 회귀 0 기대.

**rev.2 변경 사유**: rev.1의 V-3 7종 (`test_branch.py` / `test_climate.py` / `test_grievance_propagation.py` / `test_phase14_grievance_propagation.py` 4종 workspace 부재 — Step 3.5 Finding 2) → workspace 실재 7종으로 교체. 단일 권위는 신규 contract 문서. Tier 2 신규 4종 (`test_dc1_sis_smoke` / `test_dc2_cpcm_smoke` / `test_p5r_import_grep` / `test_p5r_handoff_freeze`)은 Phase 5 Package 진입 시 contract 문서 §Tier 2 절 reference로 신규 author.

### V-4. reserved 3 슬롯 typed field 부재 — grep 검증

```bash
py -c "
from pathlib import Path
src = Path('Projects/personas/loom/api/nation_p5r.py').read_text(encoding='utf-8')

# typed field 명시 패턴 (Protocol property 또는 TypedDict 키)
import re
forbidden_patterns = [
    r'def\s+dissolution_history',
    r'def\s+lord_replacement_history',
    r'def\s+federation_state',
    r'dissolution_history\s*:\s*\w',  # TypedDict typed field
    r'lord_replacement_history\s*:\s*\w',
    r'federation_state\s*:\s*\w',
]
for pat in forbidden_patterns:
    matches = re.findall(pat, src)
    assert not matches, f'reserved slot typed as field: {pat}'
print('reserved 3 slots NOT typed — PASS')
"
```

reserved 3 슬롯이 typed field로 박혀있으면 즉시 FAIL.

### V-5. core/persona/etc git diff 무 출력

```bash
git diff --stat HEAD -- \
  Projects/personas/loom/core/ \
  Projects/personas/loom/persona/ \
  Projects/personas/loom/ontology/ \
  Projects/personas/loom/brain/ \
  Projects/personas/loom/snn/ \
  Projects/personas/loom/physis/ \
  Projects/personas/loom/test_phase17_acceptance.py \
  Projects/personas/loom/conftest.py \
  Projects/personas/loom/PHASE-17-NATION-DC-1-SIS-SPEC.md \
  Projects/personas/loom/PHASE-17-NATION-DC-2-CPCM-SPEC.md
# 출력 무 = PASS
```

---

## 회귀 영향 평가 — 정적 무영향

| 회귀 위험 | 평가 | 검증 방식 |
|---|---|---|
| core / persona / ontology / brain / snn 영향 | **0** | git diff --stat (V-5) |
| acceptance / charter / DC-1 / DC-2 영향 | **0** | git diff --stat (V-5) |
| 무파괴 9 / 안전 전제 5종 / BOOST=0.20 | **0** | mechanism 무수정 |
| 회귀 7종 결과 변경 | **0** | 코드 변경 0 → 결과 동일 (V-3로 명시 검증) |
| import cycle / 순환 의존 | **0** | 신규 module이므로 기존 import 영향 없음 |
| Φ-5 인계 surface 호환성 | **+** | v0 2 슬롯 + 3 reserved 명시로 단계적 확장 가능 |

---

## Rollback

```bash
cd Projects/personas/loom
rm -f api/__init__.py api/nation_p5r.py api/README.md
rmdir api  # 디렉토리 비어있으면 제거
```

또는:

```bash
git clean -f Projects/personas/loom/api/
```

데이터 영향: 없음. 코드 영향: 없음 (신규 module만 제거).

---

## Codex 위임 프롬프트

본 spec의 [필수] 7종을 그대로 구현하세요. 자율 영역과 근간 분리는 §3에 명시.

### 절대 준수 — 8 [금지]

1. NDP / LRT / FMR 슬롯을 typed body로 박지 마라 (3 슬롯 reserved 텍스트만)
2. read-write API mutate 금지
3. event-stream subscription 금지
4. body semantics 고정 금지 (§1.0 caveat)
5. SIS 분위수 값을 body fixed value로 박지 마라
6. charter / mechanism / acceptance / brain·SNN 변경 금지
7. 무파괴 9 / 안전 전제 5종 / BOOST=0.20 / 회귀 7종 변경 금지
8. 외부 의존성 추가 금지 (typing 표준만)

### 자율 영역 (자유 결정)

- Protocol vs TypedDict 선택
- 2 슬롯 type signature 세부 구조
- docstring vs README.md 분리 비중
- mypy strict pragma 채택 여부
- 단위 테스트 추가 (선택)

### 근간 수정 필요 시 즉시 사용자 보고

§3 근간 8항 중 어느 하나라도 수정 필요하다고 판단되면 **즉시 작업 중단 → 사용자 보고**. 자율 escalate 금지.

### 검증 시퀀스 (보고 전 자체 실행)

1. `py -c "from Projects.personas.loom.api.nation_p5r import NationReadOnly"` import (§V-1)
2. mypy strict 통과 (§V-2, 환경 미설정 시 명시 보고)
3. 회귀 7종 PASS (§V-3)
4. reserved 3 슬롯 typed field 부재 검증 (§V-4)
5. core/persona/etc git diff 무 출력 (§V-5)

### 보고 양식

1. 변경 파일 목록 (3 파일 — `__init__.py` + `nation_p5r.py` + `README.md`)
2. 5 검증 항목 PASS/FAIL
3. 자율 결정 사항 (Protocol vs TypedDict / docstring 위치 / 테스트 추가 여부)
4. 근간 침범 가능성 평가 (8항 각각)
5. 최종 판정: APPROVE / APPROVE WITH NOTES / REQUEST_CHANGES

### 실패 시

- [필수] 1~7 중 하나라도 FAIL → 즉시 작업 중단, 사용자 보고
- [금지] 위반 가능성 발견 → 즉시 작업 중단, 사용자 보고

---

## 다음 단계 (본 spec 통과 후)

1. **Phase 4 Verify 3엔진 cross-check** — DC-1 SIS [확정] + DC-2 CPCM [확정] + DC-3 P5R v0 [확정] 통합 검증
   - `/discuss --quick` (Claude + Codex + Gemini=`gemini-3.1-pro`)
   - validation summary
2. **Phase 4.5 — Codex 교차 검증 (사용자 신규 추가)**
   - 1~3번 결과 타당성을 Codex에 별도 검토 요청
   - Claude도 독립 검토 → 양측 결과 비교
3. **Phase 5 Package** — Charter 본문 + Decision Card 6 + Φ-5 read-only API 1차안 commit
