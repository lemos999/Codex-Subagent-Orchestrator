# [기능·분석 스크립트] DC-1 SIS — Sovereignty Intensity Sensor (windowed faction-level distribution extractor, rev.2)

> 긴급도: 보통
> 선행 조건: Φ-3 closure-v2 + V3 진단 완료 (2026-05-03), Φ-4 Charter design Phase 0~3 [확정] (2026-05-04, Codex APPROVE_WITH_NOTES), DC-1 spec rev.1 /spec-review 보류 → rev.2 (2026-05-04)
> 작업 유형: 기능 (분석 스크립트, 1회성 데이터 추출)
> DB migration: 없음
> 외부 의존: numpy (loom 환경 기설치). pandas는 사용 가능하나 표준 라이브러리만으로 충분.
> **코어 영역 판정**: **비코어** (telemetry helper, read-only). 게이트 §3.3.2 **불요**

---

## 배경

LOOM Phase 17 Φ-4 Nation Charter design Phase 3 Decision Card DC-1 (Sovereignty Intensity Sensor) 1차 spec rev.2.

### rev.1 → rev.2 변경 사유 (/spec-review 보류 사유 반영)

| Finding | severity | rev.2 처리 |
|---|---|---|
| 메트릭 정의가 territory 단위인데 V3 raw에 territory_id 부재 | CRITICAL | **faction 단위로 1차 재정의**. territory 단위 분석은 **별도 spec으로 분리** (선행조건: 영지↔faction 매핑 helper). |
| `conflict_pair_emerged` 이벤트 raw 0건 | CRITICAL | 메트릭 #3 출처를 `metrics.jsonl`의 `contact` 이벤트 합계로 정정 |
| `event_type` vs `type` 필드 오기 | CRITICAL | 모든 인용을 `type`으로 일괄 정정 |
| `cross_faction_lord_count` window delta vs snapshot 누적 모호 | CRITICAL | "window 내 신규 emerge event 카운트(delta)"로 명시. 검증 합계 = 전체 delta 합 |
| placeholder `...` 다수 | MAJOR | explicit dict literal로 전부 치환 |
| helper 함수 시그니처 부재 | MAJOR | 5개 helper 모두 시그니처 + 1줄 가이드 명시 |
| `metrics.jsonl` 입력 누락 | MAJOR | Canonical Input 트리에 명시 |
| 회귀 7종 파일명 부재 | MAJOR | spec 본문에 직접 인용 |

### Codex 검토 (2026-05-04, APPROVE_WITH_NOTES) Finding #3 반영 (변경 없음)
- 1차 SIS spec = "windowed distribution table extractor" only
- mechanism 무수정, 임계 freeze 절대 금지
- `sovereignty_score`는 후보 진단 필드 (P50/P67/P75 분위수 후보 도출까지만 허용)
- §3.7 사슬 1단(자연 측정) + 2단(분포 분석) + 4단(분위수 후보) 범위. 5단(3엔진 cross-check)·6단(closure)은 별도 spec.

### 영지 단위 분석 분리 사유 (rev.2 결정)

V3 raw `case_c_events.json`의 핵심 메트릭 이벤트 (`active_factions_snapshot`, `cross_faction_lord_pair_emerged`)에는 territory_id가 없고 faction_id 중심으로 자연 발생됨. 영지↔faction 매핑은 별도 helper로 derive해야 하며, 그 작업은 SIS 본질 측정과 분리. **§3.7 1단 "자연 측정" 정신에 따라 raw 데이터의 자연 단위(faction)를 1차로 채택**. 영지 단위는 후속 spec(`PHASE-17-NATION-DC-1B-TERRITORY-MAP-SPEC.md` 등)에서 별도 진행.

---

## 작업 범위

### [필수]
1. V3 raw 데이터 파싱: `case_c_events.json` (events 리스트) + `metrics.jsonl` (100틱 snapshot)
2. 4 메트릭 (faction 단위 + window 단위):
   - `dom_share` (window 단위, scalar)
   - `member_share_per_faction` (window 단위, dict[fid → float])
   - `conflict_pair_count` (window 단위, scalar)
   - `cross_faction_lord_count` (window 단위, scalar — **delta**)
3. window 단위: **720 ticks** (Φ-3 entry trigger와 동일)
4. 마지막 partial window (`[19440, 20000)`, 560 ticks) 그대로 유지 + `partial=true` 플래그
5. 출력 파일: `Projects/personas/loom/data/phase17_phi4_sis/seed-{7,13,42}/{distribution.json, summary.md}` + `aggregate/{distribution.json, summary.md}`
6. 분위수 후보 P25/P50/P67/P75/P90 — 4 메트릭 각각 도출 (per seed + aggregate). `member_share_per_faction`은 per-faction 값들을 flatten한 분포에서 산출.
7. seed 간 분위수 일관성 자동 판정 (`P50/P67/P75` ±10% 이내 boolean per metric)
8. summary.md 출력 시 **`open(path, 'w', encoding='utf-8')` 명시** (V3 mojibake 재발 방지)
9. V3 일치 검증 (둘 다 통과 필수):
   - **9-a**: `cross_faction_lord_count` per seed window delta **합계** = 22 (seed 7), 23 (seed 13), 19 (seed 42)
   - **9-b**: `metrics.jsonl`에서 `tick <= 20000` 마지막 `contact` snapshot의 `count` = 1 (3 seed 모두)

### [선택]
- 시각화 스크립트: matplotlib 분포 히스토그램 (출력: `data/phase17_phi4_sis/plots/<seed>_<metric>.png`, 4 metric × 3 seed = 12 PNG)
- window 시계열 line plot

### [금지]
- mechanism 변경 — `multi_tick_engine.py` / `persona/*` / `ontology/*` 코드 수정 절대 금지
- `sovereignty_score`를 mechanism으로 사용 (telemetry로만 추가, 의사결정 trigger 사용 금지)
- 임계 분위수 magic threshold freeze (예: `>= 0.55` 결정 금지 — 분위수 후보 **도출만**)
- mojibake `summary.md` 사용 (raw JSON / `case_c_events.json` + `metrics.jsonl`만)
- 무파괴 9 / 안전 전제 5종 (HYSTERESIS=2, FOUNDER_RESPAWN_EVERY=480, TARGET_ACTIVE=2, COMMIT_EVERY=48, MAX_MEMBERS=2) / BOOST=0.20 / 회귀 7종 변경
- charter 본문 (`PHASE-17-NATION-CHARTER-*.md`) 변경
- territory 단위 분석 (별도 spec — rev.2 분리 결정). 영지 매핑이 필요하면 본 spec 외 helper 작성 후 합류.

---

## 구체 사양

### 입력 데이터 (Canonical)

```
Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/
├── seed-7/
│   ├── case_c_events.json   # JSON list — 모든 이벤트, `type` 필드 보유
│   ├── metrics.jsonl        # JSONL — 100틱 단위 snapshot (population/contact/wealth/grievance_targets/source_cumulative)
│   ├── chain.json           # 사용 안 함 (1차 spec 범위 외)
│   ├── snn_output_events.json # 사용 안 함 (1차 spec 범위 외)
│   └── summary.md           # **사용 금지** (mojibake)
├── seed-13/...
└── seed-42/...
```

**raw 사용 원칙** (Codex Finding #2 B-2):
- `case_c_events.json`만 `cross_faction_lord_pair_emerged` event 추출에 사용
- `metrics.jsonl`만 `population`(faction sizes 시점 snapshot) + `contact`(conflict_pair_count) 추출에 사용
- mojibake `summary.md` / `SUMMARY.md` **사용 절대 금지**

### 메트릭 정의 (faction 단위, per window 720 ticks)

| # | 메트릭 | 타입 | 정의 | 출처 |
|---|---|---|---|---|
| 1 | `dom_share` | float `[0, 1]` | window 마지막 시점 가장 큰 faction 점유율 = `max(faction_sizes) / sum(faction_sizes)` | `metrics.jsonl` `population` |
| 2 | `member_share_per_faction` | dict[fid → float] | window 마지막 시점 각 active faction의 인구 비율 = `size / total_size` | `metrics.jsonl` `population` |
| 3 | `conflict_pair_count` | int | window 내 모든 `contact` snapshot의 `count` 합계 (snapshot은 100틱 단위로 ~7개) | `metrics.jsonl` `contact` |
| 4 | `cross_faction_lord_count` | int | window 내 신규 발생한 `cross_faction_lord_pair_emerged` 이벤트 카운트 (**delta**, 누적 아님) | `case_c_events.json` `type=="cross_faction_lord_pair_emerged"` |

**중요**:
- 메트릭 #4는 **delta**. 전체 합계가 V3 §1.2 `emerged: 22/23/19`와 일치해야 함 ([필수] 9-a 검증).
- `active_factions_snapshot.cross_faction_lord_count`는 누적 카운트로 본 spec에서 **사용하지 않음** (혼동 방지).
- 메트릭 #1/#2의 "window 마지막 시점"은 `metrics.jsonl`에서 `tick <= w_end-1` 마지막 `population` snapshot 사용.

### Helper 함수 시그니처

```python
from pathlib import Path
import json
from typing import TypedDict

class WindowMetrics(TypedDict):
    window_start: int
    window_end: int
    partial: bool
    dom_share: float
    member_share_per_faction: dict[str, float]
    conflict_pair_count: int
    cross_faction_lord_count: int

def load_case_c_events(path: Path) -> list[dict]:
    """case_c_events.json — JSON 리스트 로드. 각 event는 'type' + 'tick' 필수."""
    with path.open(encoding='utf-8') as f:
        return json.load(f)

def load_metrics_jsonl(path: Path) -> list[dict]:
    """metrics.jsonl — 한 줄 = 한 JSON event. 'tick' + 'type' 필수."""
    with path.open(encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]

def faction_sizes_at(metrics: list[dict], t: int) -> dict[str, int]:
    """t 시점에 가장 가까운 prior population snapshot에서 fid → size 추출.
    snapshot 부재 시 빈 dict."""
    pops = [m for m in metrics if m['type'] == 'population' and m['tick'] <= t]
    return dict(pops[-1]['data']) if pops else {}

def contact_count_in_window(metrics: list[dict], w_start: int, w_end: int) -> int:
    """window [w_start, w_end) 내 모든 contact snapshot의 count 합계."""
    return sum(m['count'] for m in metrics
               if m['type'] == 'contact' and w_start <= m['tick'] < w_end)

def cfl_emerged_in_window(events: list[dict], w_start: int, w_end: int) -> int:
    """window [w_start, w_end) 내 cross_faction_lord_pair_emerged event 카운트 (delta)."""
    return sum(1 for e in events
               if e['type'] == 'cross_faction_lord_pair_emerged' and w_start <= e['tick'] < w_end)
```

### 비즈니스 로직 (구체 의사코드)

```python
import numpy as np
from pathlib import Path

DATA_ROOT = Path("Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3")
OUT_ROOT = Path("Projects/personas/loom/data/phase17_phi4_sis")
WINDOW_SIZE = 720
TOTAL_TICKS = 20000  # V3 probe contract
SEEDS = [7, 13, 42]
QUANTILES = [25, 50, 67, 75, 90]
EXPECTED_CFL_TOTAL = {7: 22, 13: 23, 42: 19}  # V3 §1.2
EXPECTED_CONTACT_AT_END = 1                    # V3 §1.1 conflict_pair@20000

def compute_window(events, metrics, w_start, w_end) -> WindowMetrics:
    sizes_end = faction_sizes_at(metrics, w_end - 1)
    total = sum(sizes_end.values())
    if total == 0:
        dom_share = 0.0
        ms_per_faction = {}
    else:
        dom_share = max(sizes_end.values()) / total
        ms_per_faction = {fid: size / total for fid, size in sizes_end.items()}
    return {
        "window_start": w_start,
        "window_end": w_end,
        "partial": (w_end - w_start) < WINDOW_SIZE,
        "dom_share": dom_share,
        "member_share_per_faction": ms_per_faction,
        "conflict_pair_count": contact_count_in_window(metrics, w_start, w_end),
        "cross_faction_lord_count": cfl_emerged_in_window(events, w_start, w_end),
    }

def compute_quantiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {f"P{q}": float('nan') for q in QUANTILES}
    return {f"P{q}": float(np.percentile(values, q)) for q in QUANTILES}

def process_seed(seed: int):
    events = load_case_c_events(DATA_ROOT / f"seed-{seed}" / "case_c_events.json")
    metrics = load_metrics_jsonl(DATA_ROOT / f"seed-{seed}" / "metrics.jsonl")

    windows: list[WindowMetrics] = []
    for w_start in range(0, TOTAL_TICKS, WINDOW_SIZE):
        w_end = min(w_start + WINDOW_SIZE, TOTAL_TICKS)
        windows.append(compute_window(events, metrics, w_start, w_end))

    # 분위수 산출
    quantiles_per_metric = {
        "dom_share":                compute_quantiles([w["dom_share"] for w in windows]),
        "member_share":             compute_quantiles(
            [v for w in windows for v in w["member_share_per_faction"].values()]
        ),
        "conflict_pair_count":      compute_quantiles([w["conflict_pair_count"] for w in windows]),
        "cross_faction_lord_count": compute_quantiles([w["cross_faction_lord_count"] for w in windows]),
    }

    # V3 일치 검증 (assertion 강제)
    cfl_total = sum(w["cross_faction_lord_count"] for w in windows)
    assert cfl_total == EXPECTED_CFL_TOTAL[seed], \
        f"seed {seed}: cfl_total={cfl_total}, expected={EXPECTED_CFL_TOTAL[seed]}"
    last_contact = [m for m in metrics if m['type'] == 'contact' and m['tick'] <= TOTAL_TICKS]
    assert last_contact, f"seed {seed}: no contact snapshot"
    assert last_contact[-1]['count'] == EXPECTED_CONTACT_AT_END, \
        f"seed {seed}: last contact count={last_contact[-1]['count']}, expected=1"

    # 출력
    out_dir = OUT_ROOT / f"seed-{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_distribution_json(out_dir / "distribution.json", seed, windows, quantiles_per_metric)
    save_summary_md_utf8(out_dir / "summary.md", seed, windows, quantiles_per_metric, cfl_total, last_contact[-1]['count'])
    return {"seed": seed, "windows": windows, "quantiles": quantiles_per_metric}

def aggregate_and_consistency(per_seed: list[dict]):
    # 3 seed 분위수 일관성 (±10% per metric × per quantile)
    consistency = {}
    for metric in ["dom_share", "member_share", "conflict_pair_count", "cross_faction_lord_count"]:
        consistency[metric] = {}
        for q in ["P50", "P67", "P75"]:
            vals = [s["quantiles"][metric][q] for s in per_seed]
            mean_v = sum(vals) / len(vals)
            if mean_v == 0:
                consistency[metric][q] = all(v == 0 for v in vals)
            else:
                consistency[metric][q] = all(abs(v - mean_v) / abs(mean_v) <= 0.10 for v in vals)

    # aggregate 분위수: 3 seed 데이터를 모두 flatten 후 재계산
    all_dom = [w["dom_share"] for s in per_seed for w in s["windows"]]
    all_ms = [v for s in per_seed for w in s["windows"] for v in w["member_share_per_faction"].values()]
    all_cpc = [w["conflict_pair_count"] for s in per_seed for w in s["windows"]]
    all_cfl = [w["cross_faction_lord_count"] for s in per_seed for w in s["windows"]]
    aggregate_q = {
        "dom_share":                compute_quantiles(all_dom),
        "member_share":             compute_quantiles(all_ms),
        "conflict_pair_count":      compute_quantiles(all_cpc),
        "cross_faction_lord_count": compute_quantiles(all_cfl),
    }

    out_dir = OUT_ROOT / "aggregate"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_aggregate_json(out_dir / "distribution.json", aggregate_q, consistency)
    save_aggregate_summary_utf8(out_dir / "summary.md", aggregate_q, consistency)

def main():
    per_seed = [process_seed(s) for s in SEEDS]
    aggregate_and_consistency(per_seed)

if __name__ == "__main__":
    main()
```

**모든 file open은 `encoding='utf-8'` 명시** (V3 mojibake 재발 방지).

### 출력 형식

#### `seed-{N}/distribution.json`

```json
{
  "seed": 7,
  "total_ticks": 20000,
  "window_size": 720,
  "windows": [
    {
      "window_start": 0,
      "window_end": 720,
      "partial": false,
      "dom_share": 0.42,
      "member_share_per_faction": {"<fid>": 0.40, "<fid>": 0.30, "<fid>": 0.30},
      "conflict_pair_count": 0,
      "cross_faction_lord_count": 0
    }
  ],
  "quantiles_per_metric": {
    "dom_share":                {"P25": 0.30, "P50": 0.45, "P67": 0.55, "P75": 0.60, "P90": 0.78},
    "member_share":             {"P25": 0.10, "P50": 0.30, "P67": 0.40, "P75": 0.45, "P90": 0.60},
    "conflict_pair_count":      {"P25": 0.0, "P50": 0.0, "P67": 1.0, "P75": 2.0, "P90": 4.0},
    "cross_faction_lord_count": {"P25": 0.0, "P50": 0.0, "P67": 1.0, "P75": 1.0, "P90": 2.0}
  },
  "v3_validation": {
    "cfl_total": 22,
    "expected_cfl_total": 22,
    "last_contact_count_at_20000": 1,
    "expected_last_contact": 1,
    "passed": true
  }
}
```

#### `seed-{N}/summary.md` (UTF-8 명시)

```markdown
# DC-1 SIS distribution — seed {N}

- total_ticks: 20000
- windows: 28 (window_size=720, 마지막 1개 partial=true, len=560)
- factions observed: {fid count}

## 분위수 (4 메트릭 × 5 분위수)

| 메트릭 | P25 | P50 | P67 | P75 | P90 |
|---|---|---|---|---|---|
| dom_share | ... | ... | ... | ... | ... |
| member_share | ... | ... | ... | ... | ... |
| conflict_pair_count | ... | ... | ... | ... | ... |
| cross_faction_lord_count | ... | ... | ... | ... | ... |

## V3 일치 검증

- cross_faction_lord_count delta 합계: {N} (V3 보고서 expected = 22/23/19 중 seed-{N})
- last contact.count @ tick<=20000: {N} (V3 보고서 expected = 1)
- passed: {true|false}

## 주의

`sovereignty_score`는 후보 진단 필드. 임계 freeze 금지 — §3.7 5단 cross-check 통과 후에만 가능.
이 spec은 1차 분포 추출만 수행 (§3.7 1단/2단/4단 후보). 결합점 분석(3단), 3엔진 cross-check(5단), closure(6단)은 별도 spec.
```

#### `aggregate/distribution.json` + `aggregate/summary.md`

3 seed 합산 분위수 + seed 간 일관성 boolean (`P50/P67/P75 × 4 metric` = 12 셀):

```json
{
  "seeds_combined": [7, 13, 42],
  "aggregate_quantiles": { /* dom_share/member_share/conflict_pair_count/cross_faction_lord_count */ },
  "consistency_within_10pct": {
    "dom_share":                {"P50": true, "P67": true, "P75": true},
    "member_share":             {"P50": true, "P67": true, "P75": true},
    "conflict_pair_count":      {"P50": true, "P67": false, "P75": true},
    "cross_faction_lord_count": {"P50": true, "P67": true, "P75": true}
  }
}
```

### 에러 케이스

| 상황 | 처리 |
|---|---|
| `case_c_events.json` 또는 `metrics.jsonl` 부재 | `FileNotFoundError` + 어떤 seed/파일 누락 명시 |
| `type` 또는 `tick` 필드 누락 | `KeyError` + 어떤 event index인지 명시 |
| population snapshot 부재 (faction_sizes_at 빈 dict) | `dom_share=0.0`, `member_share_per_faction={}`, partial 플래그 유지 (skip 아님) |
| 분위수 계산 NaN (빈 배열) | `float('nan')` 출력 (값 위조 금지) |
| V3 검증 불일치 | `AssertionError` + 어느 seed/검증 항목 실패 명시 + spec rev.2 검증 [필수] 9-a/9-b 인용 |
| UTF-8 인코딩 실패 | 명시적 에러 + 출력 파일 부분 작성 방지 (atomic write 권장: `Path.write_text(..., encoding='utf-8')` 또는 임시 파일 후 `replace`) |

---

## 변경 파일

| 파일 | 작업 | 유형 |
|---|---|:---:|
| `Projects/personas/loom/scripts/phase17_phi4_sis_extractor.py` | 신규 | 분석 스크립트 |
| `Projects/personas/loom/data/phase17_phi4_sis/seed-{7,13,42}/distribution.json` | 신규 | 출력 |
| `Projects/personas/loom/data/phase17_phi4_sis/seed-{7,13,42}/summary.md` | 신규 | 출력 (UTF-8) |
| `Projects/personas/loom/data/phase17_phi4_sis/aggregate/distribution.json` | 신규 | 통합 출력 |
| `Projects/personas/loom/data/phase17_phi4_sis/aggregate/summary.md` | 신규 | 통합 출력 (UTF-8) |
| `Projects/personas/loom/data/phase17_phi4_sis/plots/*.png` | (선택) 신규 | 시각화 |

**변경 없음 (금지)**:
- `Projects/personas/loom/core/multi_tick_engine.py`
- `Projects/personas/loom/persona/*`
- `Projects/personas/loom/ontology/*`
- `Projects/personas/loom/PHASE-17-NATION-CHARTER-*.md` (charter 본문)
- 회귀 7종 테스트 파일 (목록 아래 명시)

---

## 검증

### 기계 검증
1. **타입 체크**: `python -m mypy scripts/phase17_phi4_sis_extractor.py --strict` (loom mypy 설정 사용)
   - mypy 미설정 시 fallback: `python -c "import ast; ast.parse(open('scripts/phase17_phi4_sis_extractor.py', encoding='utf-8').read())"` (최소 syntax check) + 그 사실을 보고에 명시
2. **린트**: `python -m ruff check scripts/phase17_phi4_sis_extractor.py` (ruff 미설정 시 동일하게 명시)
3. **실행**: `python scripts/phase17_phi4_sis_extractor.py` → 8 출력 파일 생성 확인 (3 seed × 2 + aggregate × 2)

### 기능 검증
- [ ] V3 seed-7/13/42 raw JSON + JSONL 파싱 성공 (mojibake 무관)
- [ ] window 720 단위 분할 (총 28 windows: 27 full + 1 partial)
- [ ] 마지막 partial window: `partial=true`, `[19440, 20000)`, len=560
- [ ] 4 메트릭 × 5 분위수 도출 (per seed × aggregate)
- [ ] 3 seed 분위수 일관성 (±10% 이내) 자동 판정 결과 출력 (`consistency_within_10pct` boolean per metric × per quantile)
- [ ] summary.md 인코딩 UTF-8 명시 + 한글 깨짐 없음 (실제 텍스트 헤더 "분위수", "주의" 등으로 검증)

### 회귀 검증 (필수)
- [ ] 회귀 7종 테스트 PASS:
  1. `tests/test_phase14b_snn_integration.py`
  2. `tests/test_phase17_faction_handoff_contract.py`
  3. `tests/test_phase17_faction_stage3.py`
  4. `tests/test_phase17_acceptance.py` (3 known phi-3 EXPECTED FAIL 유지)
  5. `tests/test_economy.py` + `tests/test_economy_balance.py`
  6. `tests/test_persistence.py`
  7. `tests/test_class_promotion.py` + `tests/test_nomos.py`
- [ ] `git diff core/multi_tick_engine.py persona/ ontology/` = empty 확인

### V3 데이터 일치 검증 (필수)
- [ ] **9-a**: per-seed `cross_faction_lord_count` window delta **합계** = V3 보고서 22 (seed 7), 23 (seed 13), 19 (seed 42) — `AssertionError`로 강제
- [ ] **9-b**: per-seed `metrics.jsonl`의 `tick <= 20000` 마지막 `contact` snapshot의 `count` = 1 (3 seed 모두) — `AssertionError`로 강제

### Anti-pattern 검증 (Finding #3 반영)
- [ ] 코드 어디에도 magic threshold (예: `>= 0.55`, `> 0.6`, `0.6 * dom_share + 0.4 * member_share`) 없음 — 분위수 도출까지만
- [ ] `sovereignty_score` 변수가 의사결정 trigger로 사용되지 않음 — telemetry 출력만

---

## Rollback

**bash/Linux**:
```bash
rm -rf Projects/personas/loom/data/phase17_phi4_sis/
rm Projects/personas/loom/scripts/phase17_phi4_sis_extractor.py
```

**PowerShell (Windows)**:
```powershell
Remove-Item -Recurse -Force Projects/personas/loom/data/phase17_phi4_sis/
Remove-Item Projects/personas/loom/scripts/phase17_phi4_sis_extractor.py
```

데이터 영향: 분석 산출물만 생성, mechanism 무변경 → rollback 안전. 회귀 7종 재실행 후 PASS 확인 권장.

---

## 코어 영역 게이트 헤더 (§3.3.2)

```
- 코어 영역: 비코어 (telemetry helper, read-only 분석 스크립트)
- 변경 범위: 분석 스크립트 신규 + 출력 데이터. mechanism / acceptance / brain·SNN API 무변경.
- 정당화: SIS Decision Card §3.7 1단(자연 측정) + 2단(분포 분석) + 4단(분위수 후보)
- 대안 검토: N/A (비코어이므로 우회안 검토 불요)
- 사용자 사전 승인: 불요 (비코어)
- Codex 자율 구현 가능 (자율성 존중, 안전장치는 [금지] 경계)
```

---

## 참고 사항

- DC-1 본문: [PHASE-17-NATION-CHARTER-DECISION-CARDS.md](PHASE-17-NATION-CHARTER-DECISION-CARDS.md)
- Codex 회신: [PHASE-17-NATION-CHARTER-REVIEW-RESPONSE-CODEX.md](PHASE-17-NATION-CHARTER-REVIEW-RESPONSE-CODEX.md) — Finding #3 (임계 freeze 금지) 반드시 준수
- §3.7 6단 사슬: [LOOM-DIRECTION.md](LOOM-DIRECTION.md)
- Φ-4 STUB: [PHASE-17-NATION-CHARTER-STUB.md](PHASE-17-NATION-CHARTER-STUB.md)
- V3 진단 보고서: [PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md](PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md) — §1.1 contact, §1.2 CFL emerged 인용 출처
- 본 spec rev.2 범위: §3.7 1단 + 2단 + 4단 후보 (faction 단위). 영지 단위는 별도 spec, 3단·5단·6단도 별도.

---

## GPT/Codex 전달 프롬프트 템플릿

```
당신은 loom 프로젝트(페르소나 자율 사회 시뮬 + SNN 창발)의 시니어 Python 개발자입니다.

## 프로젝트 경로
c:\Users\haj\projects\subagent-orchestrator\Projects\personas\loom

## 기술 스택
Python 3.11+, numpy (이미 설치). Phase 17 Φ-3 closure 완료, Φ-4 Nation Charter design 진행 중.

## 작업 지시서
`Projects/personas/loom/PHASE-17-NATION-DC-1-SIS-SPEC.md` (rev.2) 파일을 그대로 따라 구현하세요.

## 규칙 (절대 준수)
1. 지시서의 [필수] 항목 100% 구현. [금지] 항목 절대 건드리지 말 것.
2. 본 spec은 비코어 분석 스크립트. 코어(mechanism/acceptance/brain·SNN) 변경 절대 금지.
3. 메트릭 단위는 **faction**. territory 단위 분석은 별도 spec (본 spec 범위 외).
4. 입력은 `case_c_events.json` (events `type` 필드) + `metrics.jsonl` (100틱 snapshot). mojibake `summary.md` 사용 금지.
5. 모든 file open은 `encoding='utf-8'` 명시.
6. V3 일치 검증은 `assert`로 강제 — `cross_faction_lord_count` delta 합 = 22/23/19, last contact count@20000 = 1.
7. 임계 분위수 magic threshold freeze 금지 — P25/P50/P67/P75/P90 분위수 후보 **도출만**.
8. 검증 순서:
   a. mypy + ruff (프로젝트 설정 사용, 미설정 시 ast.parse fallback + 그 사실 명시)
   b. 스크립트 실행 → 출력 파일 8개 확인 (3 seed × 2 + aggregate × 2)
   c. V3 일치 검증 (assert 통과)
   d. 회귀 7종 테스트 PASS
   e. Anti-pattern 검증 (magic threshold 없음 + sovereignty_score telemetry only)
9. 보고 내용:
   - 변경 파일 목록
   - 분위수 도출 결과 (per seed + aggregate, 4 metric × 5 quantile)
   - 3 seed 일관성 자동 판정 결과 (P50/P67/P75 × 4 metric × seed)
   - V3 일치 검증 결과 (cfl_total, last_contact_count)
   - 회귀 7종 PASS 확인
   - Anti-pattern 검증 결과
10. **Codex 자율성 존중** — [필수]/[금지] 경계 안에서 구현 방식(데이터 구조, 함수 분해, 타입 어노테이션 스타일 등) 자유.
```

---

**작성자**: Claude (loom 설계 담당, 2026-05-04, rev.2)
**rev.2 통과 조건**: /spec-review 재검토에서 CRITICAL 0건 → Codex 자율 구현 위임. 본 spec은 비코어이므로 사용자 사전 승인 불요.
