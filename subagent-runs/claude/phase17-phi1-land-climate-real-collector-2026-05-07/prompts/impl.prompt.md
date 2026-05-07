# sub-implementer prompt — Phase 17 Φ-1 §7-1 DC-1B ClimateEngine Real Collector

## 권위 출처

- **DC-1B spec rev.1**: `Projects/personas/loom/PHASE-17-LAND-REV-NEXT-DC-1B-CLIMATEENGINE-COLLECTOR-SPEC.md` (rev.1 / 2026-05-07)
- **DC-1 §7-1 SPEC rev.0**: `Projects/personas/loom/PHASE-17-LAND-REV-NEXT-DC-1-LAND-CLIMATE-PROBE-SPEC.md` (선행 봉인 commit `6197f8e`)
- **STUB v0.3**: `Projects/personas/loom/PHASE-17-LAND-REV-NEXT-STUB.md` (cross-reference 반영)
- **synthetic baseline 참조**: `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect.py` (구조 참고만, **무수정**)
- **observer (재사용)**: `Projects/personas/loom/physis/land_climate_telemetry.py` (**무수정**)
- **driver (public tick만 호출)**: `Projects/personas/loom/physis/climate_engine.py` (line 30~69 public interface, **본문 무수정**)
- **LandCell**: `Projects/personas/loom/physis/world.py:23` (**본문 무수정**)
- **extractor (재사용)**: `Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py` (**무수정**)

## 목표

DC-1B spec rev.1 [확정] 영역 기반 ClimateEngine driver 신규 author. synthetic smoke
baseline 봉인 보존 + real driver 분리 author. paper §7-1 evidence value의 raw 기반 산출.

## 작업 범위

### 신규 파일 author (단일)

`Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_real.py`

#### 모듈 헤더 (필수 명시)

```python
"""
Phase 17 Φ-1 §7-1 DC-1B Real Collector — ClimateEngine driver

WARNING — real evolution collector (NOT synthetic random walk):
This collector uses physis.climate_engine.ClimateEngine for natural
climate evolution. Output JSON is paper §7-1 raw evidence base
(complementary to synthetic smoke baseline at
scripts/phase17_phi1_land_climate_collect.py).

direct mapping (DC-1B rev.1 OQ 1B-1 [확정]):
  cell.climate["rainfall"]    = weather["precipitation_mm"]
  cell.climate["temperature"] = weather["temperature_c"]

CLI default: --ticks 90 (current/cumulative separation; DC-1B rev.1 OQ 1B-3 [확정])
"""
```

#### print 시작 라인 (실행 시 stdout)

```
[REAL] phase17_phi1_land_climate_collect_real.py — ClimateEngine driver (NOT synthetic random walk)
```

#### CLI argparse

| 인자 | 기본값 | 설명 |
|---|---|---|
| `--ticks N` | **90** | tick count (90 = current/cumulative 분리 검증 기본값. 30=smoke 최소; 120/180=raw 분석 후 결정) |
| `--seeds 7,13,42` | `7,13,42` | DC-1 §7-1 동일 seed set |
| `--planet-config <path>` | None | 옵션 — None이면 `NovaPlanet()` default |

#### evolution loop (의사코드 기반 실 구현)

```python
import argparse
from pathlib import Path
from physis.climate_engine import ClimateEngine
from physis.world import World, LandCell
from physis.land_climate_telemetry import LandClimateTelemetry, DEFAULT_WINDOW_SIZE

# 1. parse args
# 2. 출력 dir: data/phase17_phi1_land_climate_probe_real/seed-{seed}/

for seed in seeds:
    engine = ClimateEngine(seed=seed)
    world = World(width=8, height=8)  # DC-1 §7-1과 동일 8x8
    observer = LandClimateTelemetry(window_size=DEFAULT_WINDOW_SIZE)

    for t in range(args.ticks):
        day_of_year = t // 24
        hour = t % 24
        weather_by_region = engine.tick(day_of_year, hour)  # dict[str, dict]

        for cell in world.iter_cells():
            region_id = _assign_region(cell)  # 8x8 grid 3등분 결정론
            weather = weather_by_region[region_id]

            # direct mapping (rev.1 OQ 1B-1 [확정]) + legacy fallback (collector 내부 한정)
            cell.climate["rainfall"] = weather.get(
                "precipitation_mm", weather.get("rainfall", 0.0)
            )
            cell.climate["temperature"] = weather.get(
                "temperature_c", weather.get("temperature", 20.0)
            )

            observer.observe(cell, t)

    # probe.json 저장 (synthetic collector와 동일 schema)
    _save_probe_json(observer, output_path, seed=seed, ticks=args.ticks)
```

#### `_assign_region` helper (collector 내부 — LandCell.region_id 필드 추가 0건)

```python
def _assign_region(cell: LandCell) -> str:
    """8x8 grid 3등분 결정론 region 매핑.

    LandCell이 region_id 필드를 보유하지 않으므로 (physis/world.py:23 dataclass slots=True
    invariant), collector 내부에서 cell.y 기반 결정론 할당.

    OQ-1B-2 sub-impl 진입 시 검증 (rev.2 결정).
    """
    if cell.y < 3:        # y=[0,1,2] = 3 rows = 24 cells
        return "claude"
    elif cell.y < 6:      # y=[3,4,5] = 3 rows = 24 cells
        return "codex"
    else:                 # y=[6,7]   = 2 rows = 16 cells
        return "gemini"
```

#### probe.json schema (synthetic collector와 호환 강제)

기존 `scripts/phase17_phi1_land_climate_collect.py`의 `_save_probe_json()` 출력 schema와
**완전 동일**. extractor가 재사용 가능해야 함. NaN/Infinity strict (`json.dump(allow_nan=False)`).

### probe data 자동 생성 (collector 실행 산출)

```
Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/
├── seed-7/probe.json
├── seed-13/probe.json
├── seed-42/probe.json
```

### extractor 재실행 (synthetic 무영향, real dir 대상)

기존 `scripts/phase17_phi1_land_climate_extractor.py`를 **무수정** 재실행. 입력 dir
`data/phase17_phi1_land_climate_probe_real/`로 동작 가능해야 함. 만약 extractor가 dir 인자를
미지원하고 hard-coded path만 read한다면:

- 우선책: extractor를 `--probe-dir <path>` 옵션으로 호출 (이미 지원하면 사용)
- 차선책: collector_real.py가 명시적으로 extractor 모듈 import + main() 호출 + 환경변수/CLI argv 조작
- 최후: extractor 무수정 invariant 위반 없이 임시 래퍼 스크립트 author (extractor 본문은 0건 변경)

extractor 인터페이스를 먼저 Read로 확인하고, 위 셋 중 가장 깔끔한 경로 채택. 결정 근거를
`results/impl.result.md`에 명시.

산출:
```
data/phase17_phi1_land_climate_probe_real/
├── seed-{7,13,42}/distribution.json
├── seed-{7,13,42}/summary.md
├── aggregate/distribution.json
└── aggregate/summary.md
```

### summary.md Provenance 라벨

extractor가 자동 emit하는 summary.md 헤더에 다음 명시 (synthetic의 "synthetic smoke"와 구별):

```
> **Provenance**: ClimateEngine real evolution (90 tick, 3 seed × 64 cell).
> NOT synthetic random walk. paper §7-1 raw evidence base.
```

extractor가 source provenance를 자동 추론하지 않으면 collector_real.py가 산출 후 summary.md
post-process 또는 extractor 호출 시 provenance 인자 전달.

## 자체 검증 12종 (보고 의무)

`results/impl.result.md`에 다음 검증 결과 표 작성:

| # | 검증 | 명령 | 기대 |
|---:|---|---|:---:|
| 1 | mypy strict — collector_real | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_collect_real.py --strict --follow-imports=silent` | PASS |
| 2 | ruff — collector_real | `py -3.12 -m ruff check scripts/phase17_phi1_land_climate_collect_real.py` | PASS |
| 3 | collector_real 실행 (3 seed × 90 tick) | `py -3.12 scripts/phase17_phi1_land_climate_collect_real.py` | seed-{N}/probe.json 3 파일 생성 in `_probe_real/` |
| 4 | extractor 재실행 (real dir 대상) | (extractor 인터페이스 검증 후) | distribution.json + summary.md 생성 (4 파일 전체), NaN 0건 |
| 5 | `[REAL]` 라벨 grep — collector | `grep -l "REAL\|ClimateEngine driver" scripts/phase17_phi1_land_climate_collect_real.py` | match |
| 6 | Provenance 라벨 grep — summary.md | `grep -l "ClimateEngine real evolution" data/phase17_phi1_land_climate_probe_real/**/summary.md` | match 4 파일 (3 seed + aggregate) |
| 7 | synthetic baseline 무수정 | `git diff HEAD -- scripts/phase17_phi1_land_climate_collect.py data/phase17_phi1_land_climate_probe/` | empty |
| 8 | ClimateEngine 본문 무수정 | `git diff HEAD -- physis/climate_engine.py` | empty |
| 9 | telemetry / extractor 본문 무수정 | `git diff HEAD -- physis/land_climate_telemetry.py scripts/phase17_phi1_land_climate_extractor.py` | empty |
| 10 | 보호 영역 git diff | `git diff HEAD -- physis/world.py core/ ontology/ struggle/ brain/ api/ test_*.py` | empty |
| 11 | 회귀 test 파일 import 0건 | `grep -l "land_climate_collect_real\|phase17_phi1_land_climate_collect_real" test_*.py` | 0 |
| 12 | current vs cumulative 분리 검증 | 90 tick 결과의 `measurements_current` 길이 (rolling 30) ≠ `measurements_cumulative` 길이 (= 90 × 64) | logical proof + numeric 인용 |

12종 모두 PASS 시 `results/impl.result.md` 종합란에 "PASS — DC-1B real collector 신규 author 완료, rev.2 봉인 진입 가능" 표기. 실패 항목 1건 이상 시 STOP_FOR_USER + 원인 분석 보고.

## §1.0 caveat 재확인

본 spec 작업에서:
- 분위수 임계값 freeze: 본 spec은 *값*을 freeze 0건 (분위수는 도출 대상)
- window/tick 길이 freeze: 90 default 매개변수화 (`--ticks N`)
- mechanism 결합 수식: 본 spec mechanism 함수 0건 (raw probe + driver wiring only)
- LandCell 본문 변경: 0건 (`physis/world.py` 무수정)
- climate dict 새 키 추가: 0건 (rainfall + temperature 기존 키만 갱신)

→ §1.0 caveat 위반 0건 유지.

## synthetic vs real 분포 비교 (OQ 1B-5 sub-impl 결정)

`impl.result.md`에 inline 비교 sub-section 추가 (권고):

| metric | synthetic baseline (`_probe/`) P50 | real evolution (`_probe_real/`) P50 | 차이 |
|---|---:|---:|---:|
| rainfall (cumulative, aggregate) | (synthetic 산출 인용) | (real 산출 인용) | abs/relative |
| temperature (cumulative, aggregate) | ... | ... | ... |
| ... (8 metric 전체) | ... | ... | ... |

→ "차이 유의미 → paper §7-1 evidence value 봉인 진입 권고" 또는 "차이 미미 → planet-config
다양화 검토 (rev.next OQ 1B-4)" 결론 1줄.

## 안전 한계

- **writable boundary** 내 1 신규 파일 + 본 evidence dir + `_probe_real/` 산출만. 그 외 수정 금지.
- **synthetic baseline 봉인 무수정** (`collect.py` + `_probe/`) — 이는 `6197f8e` commit으로 봉인됨.
- **ClimateEngine / telemetry / extractor / LandCell / world** 본문 0건 변경 (driver wiring only).
- **회귀 test 영역** 0건 import / 0건 변경.
- 12종 검증 전부 PASS 못하면 STOP_FOR_USER 보고 + 원인 분석.

## Output 위치

- `subagent-runs/claude/phase17-phi1-land-climate-real-collector-2026-05-07/results/impl.result.md`
  (변경 파일 + 12 검증 결과 + synthetic vs real 비교 + OQ 1B-2 / 1B-5 sub-impl 결정 명시)
- `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_real.py` (신규)
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/**` (자동 산출)

## 완료 신호

`results/impl.result.md` 작성 완료 + 12종 검증 PASS + synthetic vs real 비교 sub-section 포함
시 sub-implementer 종료. 메인 컨텍스트는 evidence 검증 후 분리 commit 진입 (DC-1B rev.2
봉인 + collector_real + probe data + impl evidence를 단일 commit으로 묶음).
