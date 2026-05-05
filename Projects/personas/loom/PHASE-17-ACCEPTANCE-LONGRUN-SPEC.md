# Phase 17 Acceptance Long-run 분리 — `@pytest.mark.slow` 부여 + `conftest.py` 신규

> **긴급도**: 중간 (default run 5분+ 즉시 회복, 회귀 위험 0)
> **선행 조건**: PHASE-17-NATION-PHASE3-SPEC-PIPELINE-DRAFT.md rev.2 APPROVE WITH NOTES (R10/R11 closed)
> **작업 유형**: **인프라** (test 분리 + marker 등록만. 본문·assertion·ticks·acceptance 정의 무수정)
> **DB migration**: 없음
> **외부 의존**: 없음 (pytest 기존 사용 중)
> **canonical order**: rev.2 §0 표 1번 (가장 가벼움, 즉시 진행)

---

## 배경

DRAFT rev.2 사용자 검토 (APPROVE WITH NOTES) 결과 R11 산출:
- `test_phase17_acceptance.py` 내 `ticks ≥ 5000` long-run 함수 **8개** 중 `@pytest.mark.slow` 적용 **1개** (1/8 = 12.5%).
- 현재 default `pytest -m "not slow"` 실행 시 8 함수 중 7개가 그대로 실행 → 약 **5~6분 소요** (3 seed × 5000틱 첫 cache fill ~3분 + `test_phi3_determinism_seed42`의 cache 미사용 5000틱 ×2회 ~2분).
- F5 정신: **assertion / tick count / acceptance definition / expected-fail semantics 변경 금지**. **slow marker 부여 / `conftest.py` 등록은 infra 작업으로 허용**.
- 또한 loom 루트에 `pytest.ini` / `pyproject.toml` / `setup.cfg` / `conftest.py` 어느 것도 **부재** → marker 등록할 파일 신규 생성 필요. 기존 fixture 충돌 위험 0.

---

## 작업 범위

### [필수]

1. `Projects/personas/loom/conftest.py` 신규 생성. `pytest_configure(config)`에서 `slow` marker 등록만 수행 (fixture 추가 금지).
2. `Projects/personas/loom/test_phase17_acceptance.py`의 다음 **7 함수**에 `@pytest.mark.slow` 데코레이터 부여 (이미 적용된 1개 함수는 재부여 금지):

| # | line (현재) | 함수명 | seeds × ticks |
|:-:|:-:|---|:-:|
| 1 | 347 | `test_phi3_uprising_emerges_under_grievance_pressure` | 3 × 5000 |
| 2 | 360 | `test_phi3_grievance_pairs_resonate` | 3 × 5000 |
| 3 | 422 | `test_phi3_dom_share_natural_imbalance` | 3 × 5000 |
| 4 | 437 | `test_phi3_no_deaths` | 3 × (5000 + 1) |
| 5 | 447 | `test_phi3_branch_lineage_chain` | 3 × 5000 |
| 6 | 473 | `test_phi3_determinism_seed42` | 1 × 5000 ×2 (hash) |
| 7 | 480 | `test_respawn_seed_group_emitted` | 3 × 5000 |

**이미 적용된 함수 (재부여 금지)**:
- line 408 `test_grievance_propagate_natural_emergence` — `@pytest.mark.slow` 보존.

3. 데코레이터 위치: `def test_*` 직전 한 줄. 기존 데코레이터(`@pytest.mark.parametrize` 등)와 충돌 없음 (사전 확인됨 — 7 함수 모두 데코레이터 없음).

### [선택]

- `test_rumor.py` (n_ticks=3000) / `test_climate_impact.py` (n_ticks=2000)는 **pytest 함수가 아닌 모듈 레벨 스크립트** (`def test_*()` 없음, import 시점 즉시 실행). pytest collect되지 않으므로 본 spec 범위 외. 별도 spec(스크립트→pytest 통합)에서 다룰 것 권고.

### [금지]

- **assertion / tick count / acceptance definition / expected-fail semantics 변경 금지** (F5 핵심).
- 함수 본문(`run_simulation` 호출 인자, `assert` 식, error message, snapshot 비교 로직) 변경 금지.
- mechanism 코드 (`core/`, `ontology/`, `brain/`, `persona/`) 변경 금지.
- **무파괴 9 / 안전 전제 5종 / BOOST=0.20 / 회귀 7종** 변경 금지.
- **DC-1 SIS 결과를 sovereignty / branch rule / P5R body로 승격 금지** (DC-1 §1.0 caveat 계승 — 본 spec과 무관하지만 후속 spec 일관성 위해 명시).
- `conftest.py`에 fixture / autouse / hook 추가 금지 (marker 등록만).
- 새 import 추가 금지 (test_phase17_acceptance.py는 이미 `import pytest` 보유 — line 20).

---

## 구체 사양

### 1. `conftest.py` 신규 생성

**경로**: `Projects/personas/loom/conftest.py`

**내용** (그대로 복사 — 해석하지 말 것):

```python
"""pytest configuration for Projects/personas/loom.

Registers project-level markers. No fixtures, no autouse hooks.
"""
from __future__ import annotations


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: long-running tests (ticks >= 5000) excluded from default run; "
        "use `-m slow` to include only slow, or omit `-m` filter to run all.",
    )
```

**금지 사항**:
- fixture 정의 추가 금지.
- `pytest_collection_modifyitems` 등 collect 훅 추가 금지 (marker 등록만).
- 다른 marker (`integration`, `unit` 등) 등록 금지 (본 spec은 `slow` 1개만).

### 2. `test_phase17_acceptance.py` 7 함수 데코레이터 부여

각 함수의 `def test_*` 직전에 `@pytest.mark.slow`를 한 줄 추가.

**예시 (line 347 함수)**:

Before:
```python
def test_phi3_uprising_emerges_under_grievance_pressure():
    """Φ-3 acceptance #1: seed 7/13/42 5000틱 uprising_event ≥ 1 (3/3)."""
    from ontology.layers import THETA_UPRISING

    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        # ... (이하 기존 함수 본문 보존 — 변경 금지)
```

After:
```python
@pytest.mark.slow
def test_phi3_uprising_emerges_under_grievance_pressure():
    """Φ-3 acceptance #1: seed 7/13/42 5000틱 uprising_event ≥ 1 (3/3)."""
    from ontology.layers import THETA_UPRISING

    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        # ... (이하 기존 함수 본문 보존 — 변경 금지)
```

**같은 패턴을 다음 6 함수에 동일 적용**:
- line 360 `test_phi3_grievance_pairs_resonate`
- line 422 `test_phi3_dom_share_natural_imbalance`
- line 437 `test_phi3_no_deaths`
- line 447 `test_phi3_branch_lineage_chain`
- line 473 `test_phi3_determinism_seed42`
- line 480 `test_respawn_seed_group_emitted`

**주의**:
- 데코레이터 부여 후 line 번호가 함수당 +1씩 밀림 — 이는 정상이며 본문은 변경되지 않음.
- 들여쓰기는 0 (모듈 레벨 함수). 함수 docstring · for 루프 · assertion 내부 들여쓰기는 그대로 유지.
- `pytest`는 이미 line 20에서 `import pytest`로 가져온 상태 — 추가 import 금지.
- 위 Before/After 코드 블록의 `# ... (이하 기존 함수 본문 보존 — 변경 금지)` 주석은 **markdown 표기 목적의 placeholder**. 실제 파일에 이 주석을 새로 추가하지 말 것. **변경분은 오직 데코레이터 1줄만**. (Python `...` Ellipsis 리터럴 오해 차단)

### 3. 변경 후 파일 line 번호 (예측)

7 함수에 데코레이터 1줄씩 추가 → 누적 7줄 증가.

| 함수 | Before line | After line |
|---|:-:|:-:|
| `test_phi3_uprising_emerges_under_grievance_pressure` | 347 | 348 |
| `test_phi3_grievance_pairs_resonate` | 360 | 362 |
| `test_grievance_propagate_natural_emergence` (이미 mark) | 408 | 411 |
| `test_phi3_dom_share_natural_imbalance` | 422 | 426 |
| `test_phi3_no_deaths` | 437 | 442 |
| `test_phi3_branch_lineage_chain` | 447 | 453 |
| `test_phi3_determinism_seed42` | 473 | 480 |
| `test_respawn_seed_group_emitted` | 480 | 488 |

(이 표는 검증 시 line 매핑 참고용. 실제 line 번호는 들여쓰기·공백에 따라 ±1 가능)

---

## 변경 파일

| 파일 | 작업 | 유형 |
|---|---|:-:|
| `Projects/personas/loom/conftest.py` | 신규 생성 (marker 등록) | 추가 |
| `Projects/personas/loom/test_phase17_acceptance.py` | 7 함수 `@pytest.mark.slow` 데코레이터 추가 | 수정 |

**변경 없음 (금지)**:
- `Projects/personas/loom/core/` 전체 (mechanism 영역).
- `Projects/personas/loom/ontology/` 전체 (안전 전제 / BOOST / 회귀 7종 영역).
- `Projects/personas/loom/brain/` 전체 (코어 영역 §3.3.2).
- `Projects/personas/loom/persona/` 전체 (코어 영역 §3.3.2).
- `Projects/personas/loom/test_*.py` 중 `test_phase17_acceptance.py` 외 모든 파일.
- `Projects/personas/loom/Tools/` / `data/` 전체 (DC-1 SIS 산출물 보존).
- 기존 `@pytest.mark.slow`가 이미 적용된 line 408 `test_grievance_propagate_natural_emergence` 함수 본문·데코레이터.

---

## 검증

### 기계 검증 (필수, 순서대로)

1. **collect-only — 전체**:
   ```
   py -m pytest test_phase17_acceptance.py --collect-only -q
   ```
   기대: `19 tests collected` (변경 전과 동일).

2. **collect-only — slow 제외 (default run)**:
   ```
   py -m pytest test_phase17_acceptance.py -m "not slow" --collect-only -q
   ```
   기대: `11 selected / 8 deselected` (변경 전 `18 selected / 1 deselected` → 변경 후 `11 selected / 8 deselected`).

3. **collect-only — slow 만**:
   ```
   py -m pytest test_phase17_acceptance.py -m "slow" --collect-only -q
   ```
   기대: `8 selected / 11 deselected`.

4. **default run 시간 회복**:
   ```
   py -m pytest test_phase17_acceptance.py -m "not slow"
   ```
   기대: 11 PASS, 모두 short-run (ticks=500 / 200 / 1 / 100 등). 시간 ~30~60s (변경 전 5~6분).

5. **전체 run (slow 포함, 회귀 검증)**:
   ```
   py -m pytest test_phase17_acceptance.py
   ```
   기대: 19 PASS (변경 전과 동일). 시간 ~5~6분.

6. **marker 인식 검증** (PytestUnknownMarkWarning 부재):
   ```
   py -m pytest test_phase17_acceptance.py -m "slow" -W error::pytest.PytestUnknownMarkWarning --collect-only -q
   ```
   기대: PytestUnknownMarkWarning 없이 `8 selected`. (conftest.py marker 등록 확인)

### 인프라 검증 (필수)

- [ ] `Projects/personas/loom/conftest.py` 파일 존재 + UTF-8 인코딩 (BOM 없음).
- [ ] `conftest.py`에 `pytest_configure` 외 함수 / 클래스 / fixture 0건.
- [ ] `test_phase17_acceptance.py` 파일 변경분이 데코레이터 추가 7줄만 (assertion / ticks / 본문 변경 0건) — `git diff --stat` 라인 추가만 표시.
- [ ] `git diff` 본문 검사: `+@pytest.mark.slow` 7건 + 다른 변경 0건.

### 회귀 검증 (필수)

- [ ] **무파괴 9** 보존: `core/` 전체 무수정 (`git diff core/` 빈 출력).
- [ ] **안전 전제 5종 + BOOST=0.20 + 회귀 7종** 보존: `ontology/layers.py` 무수정.
- [ ] **brain·SNN API** 보존: `brain/`, `persona/` 무수정 (코어 영역 §3.3.2 비변경 확인).
- [ ] DC-1 SIS 산출물 무수정: `Tools/dc1_sis/`, `data/phase17_phi4_sis/` 빈 diff.
- [ ] 기존 PASS 테스트 전부 PASS 유지 (전체 run에서 19 PASS).

---

## Rollback

```bash
# 1. conftest.py 삭제
rm Projects/personas/loom/conftest.py

# 2. test_phase17_acceptance.py에서 7개 데코레이터 제거 (수동 또는 git revert)
git checkout HEAD -- Projects/personas/loom/test_phase17_acceptance.py

# 3. 회귀 확인
py -m pytest test_phase17_acceptance.py --collect-only -q
# 기대: 19 collected (1 has @slow, 18 default)
```

**데이터 영향**: 없음. 본 spec은 test 메타데이터(marker)만 변경.

---

## 작성자 노트

- 본 spec은 LOOM-DIRECTION §3.3.1 자율성 매트릭스 기준 **인프라 자율 영역**: marker 등록 + 데코레이터 부여는 mechanism / acceptance / brain·SNN 비변경. **§3.3.2 코어 게이트 발동 안 함**.
- 구현 시간 예상: 5~10분 (Codex 위임 기준). 검증 포함 시 15~20분.
- 본 spec 통과 후 canonical order 2번 (DC-2 R1~R3·R10 사전 검증) 진입.

---

## GPT 전달 프롬프트 템플릿

```
당신은 loom (Projects/personas/loom/) 의 시니어 풀스택 개발자입니다.

## 프로젝트 경로
c:\Users\haj\projects\subagent-orchestrator\Projects\personas\loom\

## 기술 스택
- Python 3.14
- pytest 9.0.2
- mechanism: numpy, dataclasses, custom MultiTickEngine
- 테스트: test_phase17_acceptance.py (19 tests, 8 long-run)

## 작업 지시서
PHASE-17-ACCEPTANCE-LONGRUN-SPEC.md 파일을 그대로 따라 구현하세요.

## 규칙 (절대 준수)
1. [필수] 항목 100% 구현. [금지] 항목 절대 건드리지 말 것.
2. 지시서의 코드 블록은 직접 복사. 해석하지 말 것.
3. 7 함수 데코레이터 위치는 line 번호 기준으로 정확히 지정된 함수만.
4. 검증 순서:
   a. py -m pytest test_phase17_acceptance.py --collect-only -q (19 collected)
   b. py -m pytest test_phase17_acceptance.py -m "not slow" --collect-only -q (11 selected / 8 deselected)
   c. py -m pytest test_phase17_acceptance.py -m "slow" --collect-only -q (8 selected)
   d. py -m pytest test_phase17_acceptance.py -m "not slow" (11 PASS, ~30-60s)
   e. py -m pytest test_phase17_acceptance.py (19 PASS, ~5-6분)
   f. py -m pytest test_phase17_acceptance.py -m "slow" -W error::pytest.PytestUnknownMarkWarning --collect-only -q (8 selected, no warning)
   g. git diff --stat → conftest.py + test_phase17_acceptance.py만 변경
5. 검증 실패 시 재작업, 통과할 때까지 반복.
6. 보고 내용:
   - 변경 파일 목록 (2개)
   - git diff 본문 (8줄 추가만 — conftest.py 신규 + 7개 @pytest.mark.slow)
   - 각 검증 단계 통과 여부
   - 전체 run 시간 (slow 제외 vs 포함)
```

---

## Self-Verification Checklist

- [x] 메타 (긴급도/선행/유형/migration/외부 의존) 포함.
- [x] 배경 1-3문장 설명 (R11 산출 결과 + F5 정신 + conftest 부재).
- [x] [필수/선택/금지] 태그로 범위 분류.
- [x] 변경 파일 표 + "변경 없음 (금지)" 명시.
- [x] 기계 검증 6단계 (collect / default / slow-only / time / 회귀 / marker warning).
- [x] 인프라 검증 4 항목 (파일 존재 / fixture 0 / diff 라인만 / 본문 검사).
- [x] 회귀 검증 5 항목 (무파괴 9 / 안전 전제 / brain·SNN / DC-1 / 기존 PASS).
- [x] Rollback 섹션 (3 명령 + 데이터 영향 없음).
- [x] [금지]에 무파괴 9 / 안전 전제 5종 / BOOST=0.20 / 회귀 7종 / brain·SNN / DC-1 §1.0 caveat 모두 명시.
- [x] 모호 표현 없음 ("적절히" / "깔끔하게" / "잘" / "알아서" 0건).
- [x] line 번호 / 코드 블록 / 함수명 모두 구체적.
- [x] DC-1 §1.0 caveat 계승 ([금지]에 SIS 승격 금지 명시).
