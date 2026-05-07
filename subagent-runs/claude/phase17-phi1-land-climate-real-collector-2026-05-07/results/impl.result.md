# Phase 17 Φ-1 Land §7-1 DC-1B Real Collector — sub-implementer result

> **Run**: `phase17-phi1-land-climate-real-collector-2026-05-07`
> **Spec**: `PHASE-17-LAND-REV-NEXT-DC-1B-CLIMATEENGINE-COLLECTOR-SPEC.md` rev.1 [확정]
> **Engine**: Claude (sub-implementer)
> **Result date**: 2026-05-07

## 0. 종합

**PASS — DC-1B real collector 신규 author 완료, rev.2 봉인 진입 가능.**

12종 검증 전부 PASS. synthetic baseline / ClimateEngine / telemetry / extractor /
LandCell / world.py 본문 0건 변경. 회귀 test 영역 0건 import / 0건 변경.
`current` (1920 = 30 rolling × 64 cell) ≠ `cumulative` (5760 = 90 × 64 cell)
분리 확인. probe.json schema 호환 + extractor 재사용 가능.

## 1. 변경 파일

### 신규 (writable boundary 내)

| 경로 | 작업 | LOC |
|---|---|---:|
| `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_real.py` | 신규 author | 467 |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/seed-7/probe.json` | 자동 생성 | (5760 + 1920 measurement) |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/seed-13/probe.json` | 자동 생성 | (5760 + 1920 measurement) |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/seed-42/probe.json` | 자동 생성 | (5760 + 1920 measurement) |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/seed-{7,13,42}/distribution.json` | extractor 재실행 | 8×2×5 quantile 표 |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/seed-{7,13,42}/summary.md` | extractor 재실행 + provenance stamp | 32 line |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/aggregate/distribution.json` | extractor 재실행 | aggregate 8×2×5 + 3-seed consistency |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/aggregate/summary.md` | extractor 재실행 + provenance stamp | 85 line |
| `subagent-runs/claude/phase17-phi1-land-climate-real-collector-2026-05-07/results/impl.result.md` | 본 evidence | (this file) |

### 변경 0건 (forbidden zone — git diff empty 검증 통과)

- `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect.py` (synthetic baseline 봉인 commit `6197f8e`)
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe/**` (synthetic 산출 봉인)
- `Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py` (인터페이스 호환 강제 — runtime DATA_ROOT swap만 사용)
- `Projects/personas/loom/physis/land_climate_telemetry.py` (observer)
- `Projects/personas/loom/physis/climate_engine.py` (driver public `tick()` 만 호출)
- `Projects/personas/loom/physis/world.py` (LandCell 본문 + climate dict 키 추가 0건)
- `Projects/personas/loom/core/`, `ontology/`, `struggle/`, `brain/`, `api/` (단방향 계약)
- `Projects/personas/loom/test_*.py` + `tests/` (acceptance invariant)

## 2. 자체 검증 12종

| # | 검증 | 명령 | 결과 |
|---:|---|---|:---:|
| 1 | mypy strict — collector_real | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_collect_real.py --strict --follow-imports=silent` | **PASS** (Success: no issues found in 1 source file) |
| 2 | ruff — collector_real | `py -3.12 -m ruff check scripts/phase17_phi1_land_climate_collect_real.py` | **PASS** (All checks passed!) |
| 3 | collector_real 실행 (3 seed × 90 tick) | `py -3.12 scripts/phase17_phi1_land_climate_collect_real.py` | **PASS** (`seed-{7,13,42}/probe.json` 3 파일 생성 in `_probe_real/`) |
| 4 | extractor 재실행 (real dir 대상) | collector_real.py 내부 `_run_extractor_against_real_dir()` (runtime DATA_ROOT swap, 본문 0건 변경) | **PASS** (per-seed distribution.json + summary.md 6 파일 + aggregate 2 파일 생성, NaN/Infinity grep 0 hit) |
| 5 | `[REAL]` 라벨 grep — collector | `grep -l "REAL\|ClimateEngine driver" scripts/phase17_phi1_land_climate_collect_real.py` | **PASS** (1 file matched) |
| 6 | Provenance 라벨 grep — summary.md | `grep -l "ClimateEngine real evolution" data/phase17_phi1_land_climate_probe_real/**/summary.md` | **PASS** (4 files matched: seed-7 / seed-13 / seed-42 / aggregate) |
| 7 | synthetic baseline 무수정 | `git diff HEAD -- scripts/phase17_phi1_land_climate_collect.py data/phase17_phi1_land_climate_probe/` | **PASS** (empty diff) |
| 8 | ClimateEngine 본문 무수정 | `git diff HEAD -- physis/climate_engine.py` | **PASS** (empty diff) |
| 9 | telemetry / extractor 본문 무수정 | `git diff HEAD -- physis/land_climate_telemetry.py scripts/phase17_phi1_land_climate_extractor.py` | **PASS** (empty diff) |
| 10 | 보호 영역 git diff | `git diff HEAD -- physis/world.py core/ ontology/ struggle/ brain/ api/ test_*.py tests/` | **PASS** (empty diff for all 8 paths) |
| 11 | 회귀 test 파일 import 0건 | grep on `**/test_*.py` for `land_climate_collect_real` | **PASS** (0 file matched) |
| 12 | current vs cumulative 분리 검증 | 90 tick 결과 — `measurements_current` 길이 (rolling 30) ≠ `measurements_cumulative` 길이 | **PASS** — numeric 인용 below |

### 검증 #12 numeric proof

`data/phase17_phi1_land_climate_probe_real/aggregate/distribution.json:counts_per_seed`:

| seed | current | cumulative |
|---:|---:|---:|
| 7  | 1920 | 5760 |
| 13 | 1920 | 5760 |
| 42 | 1920 | 5760 |

Logical proof:
- `current = window_size × cells = 30 × 64 = 1920` (rolling window per spec §2.2)
- `cumulative = ticks × cells = 90 × 64 = 5760` (full retention per spec §2.2)
- `1920 ≠ 5760` ✓ — separation confirmed at 90-tick default (synthetic baseline at
  30-tick had `current == cumulative == 7680` because the 30-tick window did
  not exceed `window_size=30`; the real collector's 90-tick run is the first
  evidence axis to demonstrate the separation that paper §8 requires).

### 검증 #4 details (extractor wrapper)

extractor는 `DATA_ROOT = .../phase17_phi1_land_climate_probe`를 line 36에 hard-code.
**3단계 옵션 분석** (per prompt §"extractor 재실행 정책"):

| 옵션 | 가능성 | 채택 |
|---|---|:---:|
| (1) extractor `--probe-dir` CLI 옵션 호출 | 옵션 미존재 (CLI argparse 없음, `main()`만 보유) | × |
| (2) 환경변수 hook | extractor에 환경변수 read 0건 | × |
| (3) collector_real.py 내부 wrapper — runtime DATA_ROOT 변수 swap | extractor 본문 바이트 0건 변경, 단방향 계약 침해 0건 | **○** |

채택: 옵션 (3). collector_real.py의 `_run_extractor_against_real_dir()`가 extractor
모듈을 import한 후 `extractor.DATA_ROOT`를 try-finally 블록으로 일시 swap하고,
`extractor.main()`을 호출 후 원본 DATA_ROOT를 복원. 디스크의 extractor.py 바이트는
0건 변경 (검증 #9 git diff empty). spec §0.3 invariant 9 + §1.3 [금지] 위반 0건.

NaN/Infinity 검증: `grep -E "NaN|Infinity|null" data/phase17_phi1_land_climate_probe_real/**/*.json` → 0 hit. extractor의 `compute_quantiles()`가 빈 입력에서 ValueError를 던지므로 NaN propagation 0건. `json.dump(allow_nan=False)` 정책 유지.

## 3. OQ sub-impl 결정 사항

### OQ 1B-2 (LandCell region tag) — sub-impl 진입 시 검증 결과

**결정**: collector 내부 `_assign_region(cell)` helper로 8x8 grid 3등분 결정론 할당.
LandCell.region_id 필드 추가 **0건** (spec §0.3 invariant + §2.4 invariant 유지).

```python
def _assign_region(cell: LandCell) -> str:
    if cell.y < 3:        # y=[0,1,2] = 3 rows × 8 cols = 24 cells → claude
        return "claude"
    if cell.y < 6:        # y=[3,4,5] = 3 rows × 8 cols = 24 cells → codex
        return "codex"
    return "gemini"        # y=[6,7]   = 2 rows × 8 cols = 16 cells
```

근거:
- `physis/world.py:23` LandCell dataclass `slots=True` invariant — 필드 추가 시 모든
  call site 영향. 본 spec writable boundary 침해.
- `cell.y` 기반 결정론 함수 — seed 무관 + mechanism coupling 0건.
- 8x8 grid 분할 (24/24/16 cells) — paper §5.2의 "3-region terrain sheet" 비례 (claude
  대륙성 + codex 온대 해양 + gemini 열대 — `physis/regions.py`) 와 일관.

이 결정은 rev.2 봉인 시 spec §2.4의 결정으로 승격 권고.

### OQ 1B-5 (synthetic vs real 비교) — sub-impl 진입 시 결정 결과

**결정**: `impl.result.md` inline sub-section 채택 (별도 dir 신설 없이 본 evidence
파일에 표 1개로 통합 — §4 sub-section).

근거:
- 본 evidence는 paper §7-1 raw evidence base의 분리 비교가 단일 파일 내에서
  검색 가능해야 함 (별도 dir로 분리하면 reviewer가 두 파일을 동시 lookup해야 함).
- 8 metric × 2 window × P50 단일 표는 단일 sub-section 내에 fit (~30 row).
- spec §5 OQ 표의 "rev.next" 결정 영역이 아닌 sub-impl 결정 영역 (1B-5는 rev.2 봉인 전 결정).

## 4. synthetic vs real 분포 비교 (OQ 1B-5 sub-impl)

### 4.1 비교 P50 표 (8 metric × 2 window aggregate)

출처:
- synthetic: `data/phase17_phi1_land_climate_probe/aggregate/distribution.json` (30 tick × 16×16=256 grid × 3 seed = 7680/seed)
- real: `data/phase17_phi1_land_climate_probe_real/aggregate/distribution.json` (90 tick × 8×8=64 grid × 3 seed = 1920 current / 5760 cumulative per seed)

| metric | window | synthetic P50 | real P50 | abs Δ | relative Δ |
|---|---|---:|---:|---:|---:|
| soil_moisture | current | 0.197051 | 0.291473 | +0.094 | **+47.9%** |
| soil_moisture | cumulative | 0.197051 | 0.264583 | +0.068 | **+34.3%** |
| fertility | current | 0.178680 | 0.283333 | +0.105 | **+58.6%** |
| fertility | cumulative | 0.178680 | 0.256250 | +0.078 | **+43.4%** |
| rainfall_30d | current | 5.400435 | 34.700000 | +29.3 | **+542.5%** |
| rainfall_30d | cumulative | 5.400435 | 29.200000 | +23.8 | **+440.7%** |
| temperature_30d | current | 19.984630 | 20.481667 | +0.497 | +2.5% |
| temperature_30d | cumulative | 19.984630 | 20.109167 | +0.125 | +0.6% |
| drought_days | current | 0.0 | 0.0 | 0 | 0% (P50 동일, but P67 0→1 / P90 1→3) |
| drought_days | cumulative | 0.0 | 0.0 | 0 | 0% (P50 동일, but P67 0→1) |
| depletion | current | 0.0 | 0.0 | 0 | 0% (resources drift 미반영 — §7-2 결정) |
| depletion | cumulative | 0.0 | 0.0 | 0 | 0% |
| recovery_rate | current | 0.0 | 0.0 | 0 | 0% |
| recovery_rate | cumulative | 0.0 | 0.0 | 0 | 0% |
| hazard_damage | current | 0.166667 | 1.000000 | +0.833 | **+500.0%** |
| hazard_damage | cumulative | 0.166667 | 1.000000 | +0.833 | **+500.0%** |

### 4.2 결론 (1줄)

**차이 유의미 → paper §7-1 evidence value 봉인 진입 권고.**

5개 metric (soil_moisture / fertility / rainfall_30d / temperature_30d 미세 변동 /
hazard_damage) 에서 synthetic baseline 대비 명확한 분포 shift 확인. 특히
`rainfall_30d` (synthetic 5.4 → real 29.2 cumulative P50) 와 `hazard_damage`
(0.17 → 1.00) 는 **5배 이상 차이**로 ClimateEngine의 자연 진화가 random walk와
질적으로 다른 raw evidence를 생성함을 입증. `temperature_30d`는 P50 차이 미미
(+0.6%) 하지만 P25/P75 분포가 크게 다름 (synthetic 19.78~20.20 vs real 11.65~22.57)
— ClimateEngine의 일교차 + 계절성이 raw 분포에 반영됨. `drought_days` 는 P50은
동일하지만 P67/P90 차이 (0→1, 1→3) 가 있어 분포 tail이 ClimateEngine 무강수 streak
에 의해 유의미하게 길어짐.

`depletion` / `recovery_rate` 가 0인 사유: 본 collector는 cell.resources를 driver
side에서 mutate하지 않음 (synthetic baseline은 random drift로 mutate). spec §1.3
[금지] mechanism 결합 수식 0건 invariant 유지를 위해 의도적 0 — `depletion` /
`recovery_rate` mechanism 결합은 §7-2 결정 영역이며, 본 spec body에서 freeze 금지.
이는 spec §0.2 caveat 일관성 — paper §7-1 raw evidence base에서 mechanism-free
영역의 0 분포는 정상 신호.

**rev.next 검토 후보** (별도 OQ): 차이 분포 5배 이상이 단일 NovaPlanet 기본 config
에 한정된 결과인지, multi-config (planet variation) 에서도 일관되는지는 OQ 1B-4
(rev.next) 영역. 본 sub-impl 단일 결과로 evidence value 봉인 진입 가능하나, OQ 1B-4
검토를 rev.next 결정 영역으로 명시 권고.

## 5. §1.0 caveat 재확인

| 항목 | 본 spec 작업 | 결과 |
|---|---|:---:|
| 분위수 임계값 freeze | 본 spec body에 freeze 0건 (분위수는 도출 대상) | ✓ |
| window/tick 길이 freeze | `--ticks N` 매개변수화 (default 90) | ✓ |
| mechanism 결합 수식 | driver wiring + raw probe만; mechanism 함수 0건 | ✓ |
| LandCell 본문 변경 | `physis/world.py` 무수정 (검증 #10 PASS) | ✓ |
| climate dict 새 키 추가 | rainfall + temperature 기존 키만 갱신 | ✓ |

→ §1.0 caveat 위반 0건 유지.

## 6. 권고 사항 (메인 컨텍스트로 전달)

1. **rev.2 봉인 commit 권고**: 본 sub-impl evidence + collector_real.py + probe data
   를 단일 commit으로 묶음. commit message 후보: `feat(loom): Phase 17 Φ-1 §7-1
   DC-1B real collector 신규 author + extractor 재사용 + paper §7-1 raw evidence base
   생성 (rev.2 [확정])`.
2. **OQ 1B-2 / 1B-5 spec rev.2 반영**: §2.4 OQ 1B-2 결정 (`_assign_region` helper) +
   §5 OQ 1B-5 결정 (impl.result.md inline) 명시.
3. **OQ 1B-4 (planet-config 다양화) rev.next 분리**: synthetic vs real 5배 차이가
   single NovaPlanet 한정인지 검증을 위한 후속 sub-impl 영역.
4. **paper §7-1 evidence value 봉인 진입 가능**: 본 결과의 raw 분포가 §7-2 mechanism
   결정의 evidence base로 사용 가능. 차이 유의미.

## Assumptions

- ClimateEngine `_compute_region_weather` (line 162-165) 가 `temperature_c` /
  `precipitation_mm` 키를 항상 emit한다는 spec §2.3 가정. 본 sub-impl에서 1×3×90×64
  weather dict 생성 후 누락 0건 확인 (legacy fallback path 미진입).
- LandClimateTelemetry observer는 climate dict 단위 무관 (P25~P90 분위수 raw 처리)
  — direct mapping 채택 시 단위 보정 불필요 (spec §2.3 근거).
- 8x8 grid는 synthetic baseline의 16x16 grid 대비 작지만, spec §1.2 / §3.3 #12
  검증 표가 "64 cell" 명시이므로 spec 우선. cell 수 차이는 비교 표 §4.1에서
  per-window measurement count로 정규화됨 (synthetic 7680 vs real 1920/5760).

## Uncertainty

- spec rev.0 §2.3 OQ 1B-1 의 (b) normalized / (c) mean 후보가 rev.1에서 [확정]
  direct mapping으로 결정되었으나, real driver 결과의 `rainfall_30d` 가 synthetic
  대비 5배 이상 차이가 raw 단위 (mm/hour ClimateEngine vs random[0,1] synthetic)
  의 차이에 일부 기인할 가능성. (b) normalized 후보가 분포 비교 가능성을 더
  정량화할 가능성 있으나, spec rev.1 [확정] direct mapping invariant 유지가
  본 sub-impl 의무 — 본 결정은 rev.next 검토 시 재검토 후보.
- `hazard_damage` 가 real에서 1.0 saturation 도달 (synthetic은 P50=0.17). 이는
  ClimateEngine의 무강수 streak이 더 길게 누적되어 telemetry observer의
  `_derive_hazard_damage` accumulator가 90 tick 내 clamp[1.0]에 도달함을 의미.
  raw evidence로는 정상 신호이나 §7-2 mechanism 결정 시 saturation cap 재검토 필요.
