# [분석 스크립트] DC-1C Multi-config + Normalized Probe — Φ-1 Land rev.next §7-1 evidence value 보강

> **상태**: **rev.1 [봉인]** (2026-05-07) — OQ 1C-1~1C-6 [확정] + spec-review 1차 [승인] + MINOR 2건 보강(정정 1차/2차 적용) + sub-impl 14/14 PASS + 회귀 7종 PASS (pytest 3종 27/27 + standalone 4종 ALL PASS) + paper §7-1 evidence value 보강 결론 (rainfall_30d 5배 차이의 96.7% 단위 영향 정량 분해)
> **긴급도**: 중간 (DC-1B 1차 5배 차이의 근원 정량화 — §7-2 mechanism 진입 전 필수)
> **선행 조건**:
> - DC-1B spec rev.2 [봉인] (commit `82ac1d3`, 2026-05-07)
> - DC-1B sub-impl §Uncertainty 2건 (rainfall_30d 5배 / hazard_damage P50=1.0)
> - DC-1 §7-1 SPEC rev.0 [봉인] (commit `6197f8e`, 2026-05-07)
> **작업 유형**: 분석 스크립트 (collector 2종 분리 신규 author — DC-1B real collector 봉인 보존)
> **DB migration**: 없음
> **외부 의존**: 없음 (`physis.climate_engine.ClimateEngine` + `physis.planet.NovaPlanet` 기존 모듈)
> **권위 문서**:
> - `PHASE-17-LAND-REV-NEXT-DC-1B-CLIMATEENGINE-COLLECTOR-SPEC.md` rev.2 [확정]
> - `PHASE-17-LAND-REV-NEXT-DC-1-LAND-CLIMATE-PROBE-SPEC.md` rev.0
> - `PHASE-17-LAND-REV-NEXT-STUB.md` v0.3 §12
> - paper(2026-05-07) §7-1 / §5.2 / §8

---

## §0. 권위 / 단방향 계약 / 보존 invariant

### 0.1 단방향 계약 (Φ-5 ← Φ-4 ← Φ-3 ← Φ-2 ← **Φ-1**)

DC-1B spec rev.2 §0.1과 동일. 본 spec은 Φ-1 Land 영역 driver wiring **only**. 다음 영역에 변경 0건:

- Φ-2 Faction (`faction.py`)
- Φ-3 Struggle (`struggle/faction_*.py`, uprising 본문)
- Φ-4 Nation (Phase 3 통합 봉인 본문)
- Φ-5 read-only API (`api/__init__.py`, `api/nation_p5r.py`)
- brain·SNN (Phase 14B-d / PersonaBrain)
- core (`core/multi_tick_engine.py`)
- ontology (Phase 11~16 무파괴)

### 0.2 §1.0 body 고정 금지 caveat

DC-1B spec rev.2 §0.2와 동일. 본 spec은 **driver wiring + normalization 식**만 freeze. 다음은 freeze **금지**:

- 8 후보 필드의 임계 분위수 (P25/P50/P67/P75/P90 자체는 도출 대상)
- 추가 window/tick 길이 (90 tick 기본만 freeze, DC-1B와 동일)
- mechanism 결합 후보 (§7-2 이후 단계 결정 영역)
- saturation cap 재검토 (DC-1B uncertainty 2번 — §7-2 영역)

본 spec rev.0에서 freeze **확정** 영역:

- alt planet config 인스턴스화 식 (§2.1 — NovaPlanet 본문 무수정 + dataclass 인스턴스 파라미터 변경만)
- normalization 식 = `precipitation_mm / 30.0` (§2.2 — type signature freeze; 다른 식 후보는 [선택])
- collector 분리 정책 (§2.3 — DC-1B `collect_real.py` 본문 0건 변경; flag 확장 금지)
- 비교 보고서 위치 = `impl.result.md` inline §4 (§2.5 — 4축 비교 표 1개)

### 0.3 보존 invariant 7+3+5종

DC-1 §7-1 spec rev.0 §0.3 (7종) **모두 유지** + DC-1B §0.3 (3종) **모두 유지** + 본 spec 추가:

11. **DC-1B real collector 산출 영구 봉인** —
    `scripts/phase17_phi1_land_climate_collect_real.py` /
    `data/phase17_phi1_land_climate_probe_real/**` 본 spec에서 **무수정 (영원)**.
    real raw evidence는 paper §7-1 raw evidence base — 본 spec의 normalized / multiconfig
    axis는 DC-1B real raw axis와 별도 비교 축. 같은 변경 단위에 섞지 않음.
12. **`physis/planet.py` 본문 무수정** — NovaPlanet은 `@dataclass(frozen=True)`
    invariant. alt config는 NovaPlanet 인스턴스의 다른 파라미터 값으로만 생성 (본문 0건 변경).
13. **`physis/climate_engine.py` 본문 무수정** — driver는 `__init__(planet=alt_config, seed=...)`
    public interface 호출만. `_compute_region_weather` 내부 mechanism 0건 변경.
14. **collector 분리 invariant** — `collect_real.py`에 `--normalize` / `--planet-config` flag
    추가 **금지**. 신규 collector 2종 분리 author (`_normalized.py` + `_multiconfig.py`).
    DC-1B 봉인 영구 보존.
15. **LandCell.climate dict 새 키 추가 금지** —
    `_normalized.py`는 LandCell.climate["rainfall"]에 normalized scalar 저장 (raw 대체),
    `_multiconfig.py`는 raw mapping 그대로 (DC-1B 동형). 둘 다 climate dict 키 추가 0건.

---

## §1. 목적 + 범위

### 1.1 trigger — DC-1B sub-impl §Uncertainty 2건 (2026-05-07)

DC-1B 1차 결과 분포 비교 표 (sub-impl §4.1):

> - `rainfall_30d` cumulative: synthetic 5.40 → real 29.20 (**+440.7%**)
> - `hazard_damage` cumulative: synthetic 0.167 → real 1.000 (**+500.0%**)

**§Uncertainty 분석**:

> 1. `rainfall_30d` 5배 차이 일부가 raw 단위 (ClimateEngine `precipitation_mm/hour` vs synthetic `random[0,1]`) 의 차이에 기인 가능 → rev.next OQ 1B-4 (planet variation) + (b) normalized 후보 재검토 영역.
> 2. `hazard_damage` real saturation 1.0 도달 → §7-2 mechanism 결정 시 telemetry accumulator clamp 재검토 필요.

본 spec은 §Uncertainty #1 응답 (단위 차이 + planet config 한정 검증). #2는 §7-2 결정 영역 (본 spec 범위 외).

### 1.2 본 spec 범위 (axis 분리)

| 항목 | 본 spec | §7-2 이후 |
|---|:---:|:---:|
| alt planet config 신규 collector — `collect_multiconfig.py` | ○ | - |
| normalization 식 신규 collector — `collect_normalized.py` (`precipitation_mm / 30.0`) | ○ | - |
| 4축 비교 분포 표 (synthetic / real / normalized / multiconfig) | ○ | - |
| `LandClimateTelemetry` **무수정** 재사용 | ○ | - |
| extractor **무수정** 재사용 (DC-1B runtime DATA_ROOT swap 동형) | ○ | - |
| 분리 출력 dir `_probe_normalized/` + `_probe_multiconfig/` | ○ | - |
| `[NORMALIZED]` / `[MULTICONFIG]` provenance 라벨 | ○ | - |
| **DC-1B real collector / `_probe_real/` 변경** | **금지** | 영원 |
| **synthetic baseline 변경** | **금지** | 영원 |
| **mechanism 결합 (depletion / fertility 수식)** | **금지** | §7-2 |
| **saturation cap 재검토** | **금지** | §7-2 |
| **LandCell 본문 + climate dict 키 추가** | **금지** | §7-2 + 사용자 사전 승인 |
| **NovaPlanet / ClimateEngine 본문 변경** | **금지** | 영원 |
| **5축 결합 (multiconfig + normalized 동시 적용)** | **금지** | rev.next |

### 1.3 [필수] / [선택] / [금지]

#### [필수]

1. 신규 collector 2종 분리 author:
   - `scripts/phase17_phi1_land_climate_collect_normalized.py` (normalized axis)
   - `scripts/phase17_phi1_land_climate_collect_multiconfig.py` (multi-config axis)
2. argparse (둘 다 동일):
   - `--ticks N` (default **90** — DC-1B와 동일 invariant)
   - `--seeds 7,13,42` (DC-1 §7-1 동일 seed set)
3. `collect_multiconfig.py` 추가 인자: `--alt-config <name>` (default 하나 — sub-impl 결정 영역, OQ 1C-5)
4. probe.json 인터페이스 호환 — 기존 `phase17_phi1_land_climate_extractor.py` 재사용 가능 (DC-1B와 동일 runtime DATA_ROOT swap)
5. provenance 라벨 명시:
   - `_normalized.py` module docstring "WARNING — normalized axis collector (precipitation_mm / 30.0 unit normalization, NOT raw)"
   - `_multiconfig.py` module docstring "WARNING — alt planet config axis collector (NovaPlanet alt instance, NOT default config)"
   - print 시작 라인: `[NORMALIZED]` / `[MULTICONFIG]` prefix
6. NaN/Infinity strict (`json.dump(allow_nan=False)`) — DC-1B 동일 정책
7. 출력 dir 분리: `data/phase17_phi1_land_climate_probe_normalized/` + `_probe_multiconfig/` — DC-1B `_probe_real/` 무영향
8. mypy strict (`--follow-imports=silent`) + ruff PASS — DC-1B 동일 정책
9. 회귀 7종 (Tier 1) 무영향 logical proof (test 파일 import 0건 + mechanism 영역 git diff empty)
10. **4축 비교 보고서** (`impl.result.md` inline §4): synthetic / real / normalized / multiconfig 8 metric × 2 window aggregate P50 표

#### [선택]

- normalization 후보 추가 (Z-score / log scale / percentile rank) — rev.next OQ
- alt planet config 후보 추가 (3+ multi-config grid) — rev.next OQ 1B-4
- 5축 결합 분포 (multiconfig + normalized 동시) — rev.next
- summary.md provenance label post-process (DC-1B `_post_process_summary_provenance` 패턴 재사용)

#### [금지]

- DC-1B real collector 변경 (`collect_real.py`, `_probe_real/` 데이터)
- synthetic baseline collector / `_probe/` 데이터 변경
- extractor 본문 변경 (인터페이스 호환 강제 — runtime DATA_ROOT swap만)
- `LandClimateTelemetry` 본문 변경
- `physis.climate_engine.ClimateEngine` 본문 변경
- `physis.planet.NovaPlanet` 본문 변경 (alt config는 인스턴스 파라미터 변경만)
- `LandCell` 본문 / `climate` dict 새 키 추가 / mechanism / acceptance 변경
- core / ontology / struggle / Φ-2 / Φ-3 / Φ-4 / Φ-5 / brain·SNN 영역 변경
- 기존 회귀 7종 변경
- magic threshold freeze (분위수 임계값 spec body 명시)
- saturation cap 재검토 (§7-2 영역)

---

## §2. 설계 (multi-config + normalized)

### 2.1 alt planet config 인스턴스화 (§Uncertainty #1 multi-config axis)

`physis/planet.py:14` NovaPlanet `@dataclass(frozen=True)` 인용:

```python
@dataclass(frozen=True)
class NovaPlanet:
    rotation_period_h: float = 24.0
    orbital_period_d: int = 360
    axial_tilt_deg: float = 25.0
    eccentricity: float = 0.02
    sea_level_temp_c: float = 16.0
    lapse_rate_per_km: float = 6.5
    gravity_ms2: float = 9.81
    season_length_d: int = 90
    solar_constant: float = 1361.0
```

alt config는 NovaPlanet 본문 무수정 — 다른 파라미터로 인스턴스화만:

```python
# collect_multiconfig.py 내부
default_config = NovaPlanet()  # DC-1B와 동일 baseline (비교 기준)
alt_config = NovaPlanet(
    axial_tilt_deg=<sub-impl 결정>,
    sea_level_temp_c=<sub-impl 결정>,
    # 기타 파라미터는 sub-impl OQ 1C-5 결정 영역
)
```

본 spec body는 alt config의 *값*을 freeze 금지. 식별/이름/수치는 sub-impl 진입 시 결정 (OQ 1C-5).

### 2.2 normalization 식 [확정 — rev.0 / 2026-05-07]

`precipitation_mm / 30.0` 채택 (rev.0 (b) 후보 — §Uncertainty #1 normalized axis).

```python
# collect_normalized.py 내부
RAINFALL_NORMALIZATION_DIVISOR = 30.0

cell.climate["rainfall"] = (
    weather.get("precipitation_mm", weather.get("rainfall", 0.0))
    / RAINFALL_NORMALIZATION_DIVISOR
)
cell.climate["temperature"] = weather.get("temperature_c", weather.get("temperature", 20.0))
```

근거 (사용자 결정 2026-05-07):

- `30.0`은 DEFAULT_WINDOW_SIZE (LandClimateTelemetry rolling window) 와 일치 — 30일 window 평균 rate로 해석 가능
- temperature는 unit 변환 없음 (`temperature_c`는 SI standard, normalize 의미 없음)
- normalized 분포의 P50가 synthetic random[0,1] 분포의 P50과 직접 비교 가능 → 5배 차이의 단위 영향 정량화

> **명확화 (spec-review 1차 MINOR-1, 2026-05-07)**: `RAINFALL_NORMALIZATION_DIVISOR = 30.0` 은 **unit normalization divisor** (LandClimateTelemetry `DEFAULT_WINDOW_SIZE = 30 tick` 과 의미상 정렬) — **분위수 임계값(P25/P50/P67/P75/P90) 이 아님**. §1.0 caveat의 "magic threshold freeze 금지"는 분포 분석 임계값 (분위수) 에 한정되며, 본 unit normalization 식은 §0.2 "freeze 확정 영역"에 해당. 즉 sub-impl 진입 후 자가 조정 금지 (식 변경은 rev.next OQ 영역).

#### rev.0의 (a)/(c)/(d) 제외 사유

| 후보 | 제외 사유 |
|---|---|
| (a) `precipitation_mm / window_size` (variable) | window_size는 매개변수 — magic threshold freeze 위험 |
| (c) Z-score | mean/std 분포 가정이 mechanism 진입 신호 |
| (d) percentile rank | 분포 비교 자체 변환 — raw 단계 의미 상실 |

#### normalized 분포의 의미

`_probe_normalized/` 산출은 `cell.climate["rainfall"]` = `precipitation_mm / 30.0`. LandCell.climate dict 새 키 추가 0건 (raw `rainfall` 키만 갱신, normalized 값으로). `_probe_real/` raw 봉인 영구 무영향.

### 2.3 collector 2종 분리 [확정 — rev.0 / 2026-05-07]

#### `collect_normalized.py`

- ClimateEngine driver: `NovaPlanet()` (default) + `seed=<seed>` (DC-1B와 동일)
- LandCell.climate["rainfall"] = `weather["precipitation_mm"] / 30.0` (normalized scalar 저장)
- 출력 dir: `data/phase17_phi1_land_climate_probe_normalized/seed-{N}/probe.json`
- provenance 라벨: `[NORMALIZED] phase17_phi1_land_climate_collect_normalized.py — precipitation_mm / 30.0`
- summary.md 헤더 stamp: `Provenance: ClimateEngine normalized axis (precipitation_mm / 30.0). NOT raw or synthetic. paper §7-1 unit-normalized evidence base.`

#### `collect_multiconfig.py`

- ClimateEngine driver: `NovaPlanet(<alt parameters>)` + `seed=<seed>` (alt config — OQ 1C-5)
- LandCell.climate["rainfall"] = `weather["precipitation_mm"]` (raw — DC-1B 동형)
- 출력 dir: `data/phase17_phi1_land_climate_probe_multiconfig/seed-{N}/probe.json`
- provenance 라벨: `[MULTICONFIG] phase17_phi1_land_climate_collect_multiconfig.py — NovaPlanet(<alt name>)`
- summary.md 헤더 stamp: `Provenance: ClimateEngine multi-config axis (NovaPlanet alt instance: <alt name>). paper §7-1 planet-variation evidence base.`

### 2.4 evolution loop (의사코드 — `_normalized.py` 예시)

```python
import argparse
from pathlib import Path
from physis.climate_engine import ClimateEngine
from physis.planet import NovaPlanet
from physis.world import World, LandCell
from physis.land_climate_telemetry import LandClimateTelemetry, DEFAULT_WINDOW_SIZE

RAINFALL_NORMALIZATION_DIVISOR = 30.0

# 1. parse args
# 2. 출력 dir: data/phase17_phi1_land_climate_probe_normalized/seed-{seed}/

for seed in seeds:
    engine = ClimateEngine(planet=NovaPlanet(), seed=seed)  # default config (DC-1B와 동일 baseline)
    world = World(width=8, height=8)
    observer = LandClimateTelemetry(window_size=DEFAULT_WINDOW_SIZE)

    for t in range(args.ticks):
        day_of_year = t // 24
        hour = t % 24
        weather_by_region = engine.tick(day_of_year, hour)

        for cell in world.iter_cells():
            region_id = _assign_region(cell)  # DC-1B와 동형 8x8 grid 3등분
            weather = weather_by_region[region_id]

            # normalization 적용 (rev.0 [확정])
            cell.climate["rainfall"] = (
                weather.get("precipitation_mm", weather.get("rainfall", 0.0))
                / RAINFALL_NORMALIZATION_DIVISOR
            )
            cell.climate["temperature"] = weather.get(
                "temperature_c", weather.get("temperature", 20.0)
            )

            observer.observe(cell, t)

    _save_probe_json(observer, output_path, seed=seed, ticks=args.ticks)
```

`collect_multiconfig.py`는 위 루프에서 `NovaPlanet()` → `NovaPlanet(<alt parameters>)` + normalization 0건 + 출력 dir만 변경.

### 2.5 4축 비교 분포 표 [확정 — rev.0 / 2026-05-07]

`impl.result.md` inline §4 sub-section. 단일 보고서:

```
| metric | window | synthetic | real | normalized | multiconfig | 해석 |
|---|---|---:|---:|---:|---:|---|
| rainfall_30d | cumulative | 5.40 | 29.20 | <X> | <Y> | 단위 영향=<29.20-X> / config 한정=<29.20-Y> / 자연 진화=<min(X,Y)> |
| ... (8 metric × 2 window) |
```

8 metric × 2 window = 16 row. 단일 표로 4축 비교 가능 (DC-1B §4 동형 + 2 column 추가).

### 2.6 LandCell region tag (DC-1B §2.4와 동일)

DC-1B [확정] 결정 (`_assign_region(cell)` helper, 8x8 grid 3등분 24/24/16) **재사용**. 본 spec에서 신규 결정 0건.

---

## §3. 검증

### 3.1 mechanism 결합 무영향 — logical proof

DC-1B 동형:

| 검증 | 명령 | 기대 |
|---|---|:---:|
| collector 2종 신규 author 외 변경 0 | `git diff HEAD -- physis/ core/ ontology/ struggle/ brain/ api/ test_*.py` | empty |
| extractor 무수정 | `git diff HEAD -- scripts/phase17_phi1_land_climate_extractor.py` | empty |
| DC-1B real collector / 산출 무수정 | `git diff HEAD -- scripts/phase17_phi1_land_climate_collect_real.py data/phase17_phi1_land_climate_probe_real/` | empty |
| synthetic baseline 무수정 | `git diff HEAD -- scripts/phase17_phi1_land_climate_collect.py data/phase17_phi1_land_climate_probe/` | empty |
| LandClimateTelemetry 무수정 | `git diff HEAD -- physis/land_climate_telemetry.py` | empty |
| ClimateEngine 무수정 | `git diff HEAD -- physis/climate_engine.py` | empty |
| NovaPlanet 무수정 | `git diff HEAD -- physis/planet.py` | empty |
| 회귀 test 파일 import 0건 | `grep -l "land_climate_collect_normalized\|land_climate_collect_multiconfig" test_*.py` | 0 |

### 3.2 evidence 분리 (4축)

| 축 | 출력 dir | 라벨 | 용도 |
|---|---|---|---|
| smoke baseline (봉인) | `data/phase17_phi1_land_climate_probe/` | `synthetic smoke` | 인터페이스 검증 |
| real raw (봉인 — DC-1B) | `data/phase17_phi1_land_climate_probe_real/` | `ClimateEngine real evolution` | paper §7-1 raw evidence base |
| normalized (본 spec) | `data/phase17_phi1_land_climate_probe_normalized/` | `ClimateEngine normalized axis` | 단위 영향 분리 |
| multiconfig (본 spec) | `data/phase17_phi1_land_climate_probe_multiconfig/` | `ClimateEngine multi-config axis` | planet config 한정 검증 |

4축 모두 **독립 dir** — 본 spec 작업이 다른 3축의 산출을 덮어쓰는 흐름 영원히 금지.

### 3.3 self-validation 14종 (sub-implementer 보고 의무)

| # | 검증 | 명령 | 기대 |
|---:|---|---|:---:|
| 1 | mypy strict — collect_normalized | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_collect_normalized.py --strict --follow-imports=silent` | PASS |
| 2 | mypy strict — collect_multiconfig | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_collect_multiconfig.py --strict --follow-imports=silent` | PASS |
| 3 | ruff — 두 collector | `py -3.12 -m ruff check scripts/phase17_phi1_land_climate_collect_normalized.py scripts/phase17_phi1_land_climate_collect_multiconfig.py` | PASS |
| 4 | collect_normalized 실행 (3 seed × 90 tick) | `py -3.12 scripts/phase17_phi1_land_climate_collect_normalized.py` | seed-{N}/probe.json 3개 생성 (`_probe_normalized/`) |
| 5 | collect_multiconfig 실행 (3 seed × 90 tick) | `py -3.12 scripts/phase17_phi1_land_climate_collect_multiconfig.py` | seed-{N}/probe.json 3개 생성 (`_probe_multiconfig/`) |
| 6 | extractor 재실행 (normalized) | runtime DATA_ROOT swap (DC-1B 동형) | distribution.json + summary.md 생성, NaN 0건 |
| 7 | extractor 재실행 (multiconfig) | runtime DATA_ROOT swap (DC-1B 동형) | distribution.json + summary.md 생성, NaN 0건 |
| 8 | `[NORMALIZED]` / `[MULTICONFIG]` 라벨 grep — collector | `grep -l` 두 패턴 | 각 1 file matched |
| 9 | provenance 라벨 grep — summary.md | `grep -l "ClimateEngine normalized axis\|ClimateEngine multi-config axis"` 8 파일 (4 normalized + 4 multiconfig) | 8 file matched |
| 10 | DC-1B real collector / 산출 무수정 | `git diff HEAD -- scripts/phase17_phi1_land_climate_collect_real.py data/phase17_phi1_land_climate_probe_real/` | empty |
| 11 | synthetic baseline 무수정 | `git diff HEAD -- scripts/phase17_phi1_land_climate_collect.py data/phase17_phi1_land_climate_probe/` | empty |
| 12 | NovaPlanet / ClimateEngine / telemetry / extractor 본문 무수정 | `git diff HEAD -- physis/planet.py physis/climate_engine.py physis/land_climate_telemetry.py scripts/phase17_phi1_land_climate_extractor.py` | empty |
| 13 | 보호 영역 git diff | `git diff HEAD -- physis/world.py core/ ontology/ struggle/ brain/ api/ test_*.py` | empty |
| 14 | 4축 비교 표 작성 — `impl.result.md` §4 inline | `grep -l "synthetic.*real.*normalized.*multiconfig" results/impl.result.md` | match (8 metric × 2 window 16 row) |

14종 모두 PASS 시 sub-implementer 종료. 실패 시 `STOP_FOR_USER` + 원인 분석 보고.

### 3.4 §1.0 caveat 재확인

- 분위수 임계값 freeze: 본 spec은 *값*을 freeze 0건 (분위수는 도출 대상)
- window 길이 freeze: 30 default 유지, --ticks N 매개변수화 (DC-1B 동일)
- mechanism 결합 수식: 본 spec mechanism 함수 0건 (driver wiring + normalize 식 only)
- LandCell 본문 변경: 0건
- climate dict 새 키 추가: 0건 (rainfall + temperature only, normalize는 raw 갱신만)
- saturation cap: 본 spec body 결정 0건 (§7-2 영역)

→ §1.0 caveat 위반 0건 유지.

---

## §4. 변경 파일

| 경로 | 작업 | 비고 |
|---|---|---|
| `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_normalized.py` | 신규 author | normalized axis collector |
| `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_multiconfig.py` | 신규 author | alt planet config axis collector |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_normalized/seed-{7,13,42}/probe.json` | 자동 생성 | 90 tick × 64 cell × 2 metric (normalized rainfall) |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_normalized/seed-{7,13,42}/distribution.json` + `summary.md` | 자동 생성 (extractor) | per-seed |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_normalized/aggregate/distribution.json` + `summary.md` | 자동 생성 (extractor) | aggregate |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_multiconfig/{seed-{7,13,42},aggregate}/{probe,distribution,summary}.{json,md}` | 자동 생성 | multiconfig 동형 |
| `Projects/personas/loom/PHASE-17-LAND-REV-NEXT-DC-1C-MULTICONFIG-NORMALIZED-PROBE-SPEC.md` | 신규 author (rev.0) | 본 spec |
| `subagent-runs/claude/phase17-phi1-land-climate-multiconfig-normalized-<date>/` | 신규 author (sub-impl evidence) | run-manifest + run-summary + prompts/ + results/ |

**변경 없음 (금지):**

- `scripts/phase17_phi1_land_climate_collect.py` (synthetic baseline 봉인)
- `scripts/phase17_phi1_land_climate_collect_real.py` (DC-1B real collector 봉인)
- `data/phase17_phi1_land_climate_probe/` (synthetic 산출 봉인)
- `data/phase17_phi1_land_climate_probe_real/` (DC-1B real 산출 봉인)
- `scripts/phase17_phi1_land_climate_extractor.py` (인터페이스 호환 강제)
- `physis/land_climate_telemetry.py` (observer 무수정)
- `physis/climate_engine.py` (driver는 public `tick()` 호출만)
- `physis/planet.py` (NovaPlanet은 인스턴스 파라미터만 변경; 본문 무수정)
- `physis/world.py` (LandCell 본문 무수정)
- `core/` `ontology/` `struggle/` `brain/` `api/` `test_*.py` (단방향 계약)

---

## §5. Open Questions

| # | 질문 | 결정 / 권고 | 상태 |
|---:|---|---|:---:|
| 1C-1 | planet config 후보 수 | single NovaPlanet baseline + alt config 1개 | **[확정 — rev.0 / 2026-05-07]** |
| 1C-2 | normalization 식 | `precipitation_mm / 30.0` (window-aligned divisor) | **[확정 — rev.0 / 2026-05-07]** |
| 1C-3 | collector 구조 | 신규 collector 2개 분리 (DC-1B 봉인 보존; flag 확장 금지) | **[확정 — rev.0 / 2026-05-07]** |
| 1C-4 | 비교 보고서 위치 | `impl.result.md` inline §4 (4축 단일 표) | **[확정 — rev.0 / 2026-05-07]** |
| 1C-5 | alt planet config 식별 (이름/파라미터) — `axial_tilt_deg` / `sea_level_temp_c` 등 어느 파라미터를 어떤 값으로? | sub-impl 진입 시 결정 (NovaPlanet `frozen=True` invariant 유지 + 한 가지 의미 있는 변동) | sub-impl 결정 |
| 1C-6 | 4축 비교 표 해석 column | 권고: "단위 영향 / config 한정 / 자연 진화" 3 분해 (real-normalized / real-multiconfig / min) | sub-impl 진입 시 결정 |

---

## §6. Future Work

- DC-1C 결과의 4축 비교 분포가 §7-2 mechanism 결정의 **evidence base 강화**
- 5축 결합 (multiconfig + normalized 동시 적용) — rev.next 또는 §7-2 결정 후
- saturation cap 재검토 (real `hazard_damage` P50=1.0 도달) — §7-2 spec 영역 (DC-1C 범위 외)
- 추가 alt planet config 다양화 (3+ multi-config grid) — rev.next OQ
- 추가 normalization 식 후보 (Z-score / log scale / percentile rank) — rev.next OQ

---

## §7. Rollback

본 spec 작업물은 분리 dir + 신규 단일 파일 2개. Rollback:

```bash
git rm scripts/phase17_phi1_land_climate_collect_normalized.py
git rm scripts/phase17_phi1_land_climate_collect_multiconfig.py
git rm -r data/phase17_phi1_land_climate_probe_normalized/
git rm -r data/phase17_phi1_land_climate_probe_multiconfig/
git rm PHASE-17-LAND-REV-NEXT-DC-1C-MULTICONFIG-NORMALIZED-PROBE-SPEC.md
git rm -r subagent-runs/claude/phase17-phi1-land-climate-multiconfig-normalized-<date>/
```

DC-1B real collector / synthetic baseline / extractor / NovaPlanet / ClimateEngine / LandCell / world.py 모두 무영향 — Rollback은 단순.

#### Rollback 후 회귀 검증 (Tier 1 7종, spec-review 1차 MINOR-2 보강 2026-05-07 → MINOR-2 정정 1차 2026-05-07 → MINOR-2 정정 2차 2026-05-07)

권위 정의 단일 소스: `PHASE-17-CASE-C-CONTACT-PERSISTENCE-SPEC.md:55` (회귀 7종 freeze 정의).

**중요: 회귀 7종은 형식이 혼합** — pytest 호환 3종 + standalone Python script 4종 (def test_ 없음, module-level 500틱 시뮬 + sys.exit(1) on FAIL). 따라서 단일 pytest 명령으로 검증 불가능. 두 그룹 분리 실행 의무.

```bash
# (1) pytest 호환 3종 — 27 tests
py -3.12 -m pytest \
  test_phase17_faction_handoff_contract.py \
  test_phase14b_snn_integration.py \
  test_phase17_faction_stage3.py \
  -m "not slow" -v

# (2) standalone script 4종 — 각 500틱 시뮬, sys.exit(1) on FAIL
py -3.12 test_economy.py && \
py -3.12 test_governance.py && \
py -3.12 test_class_promotion.py && \
py -3.12 test_nomos.py
```

(1) PASS + (2) PASS 모두 확인 시 회귀 7종 PASS. 신규 파일 only이므로 Rollback은 단순하지만, "코어 무영향" 의 *증명*은 회귀 7종 PASS 로 마무리 권고.

---

## §8. 변경 이력

### rev.0 — 2026-05-07 초안 (사용자 권고 채택)

- DC-1B sub-impl §Uncertainty #1 응답 (rainfall_30d 5배 차이의 단위 영향 + planet config 한정 검증)
- DC-1B real collector / `_probe_real/` 봉인 영구 보존 + 본 spec collector 2종 분리 author
- OQ 1C-1 ~ 1C-4 [확정] (사용자 권고 채택 2026-05-07):
  - 1C-1: single NovaPlanet baseline + alt config 1개
  - 1C-2: `precipitation_mm / 30.0`
  - 1C-3: 신규 collector 2종 분리 (DC-1B 봉인 보존)
  - 1C-4: `impl.result.md` inline §4
- OQ 1C-5 (alt config 식별) / 1C-6 (해석 column) — sub-impl 결정 영역
- 본 spec 자체 봉인 status: **rev.0 초안 — sub-implementer 사용자 승인 대기**

### rev.0+ — 2026-05-07 spec-review 1차 [승인] + MINOR 2건 보강

- `/spec-review` 1차 (supervisor 단독 sonnet, 자동 진행 옵션 A1+B1) 진입
- 종합 판정: **[승인]** — CRITICAL 0 / MAJOR 0 / MINOR 2 / TRIVIA 1 — 구현 차단 사유 없음
- 인용 파일 5건 직접 Read 대조 — planet.py / climate_engine.py / land_climate_telemetry.py / world.py / collect_real.py / extractor.py 모두 일치
- MINOR-1 보강: §2.2 RAINFALL_NORMALIZATION_DIVISOR 명확화 박스 추가 — unit normalization divisor (NOT 분위수 임계값) 명시 → §1.0 caveat 명목 모순 해소
- MINOR-2 보강: §7 Rollback 끝에 회귀 7종 검증 명령 추가 — "코어 무영향" logical proof 의 실행 마무리
- **MINOR-2 정정 1차** (2026-05-07, sub-impl 14/14 PASS 후 회귀 실행 진입 시 발견): 보강 시 명시한 회귀 명령(`test_phase17_struggle.py / test_phase17_nation_charter.py / test_brain_phaseC.py`) 3 파일 모두 미존재 — 권위 정의(`PHASE-17-CASE-C-CONTACT-PERSISTENCE-SPEC.md:55`) 직접 인용으로 교체 (`test_economy.py / test_governance.py / test_class_promotion.py / test_nomos.py / test_phase17_faction_handoff_contract.py / test_phase14b_snn_integration.py / test_phase17_faction_stage3.py`). **근본 원인**: spec 작성 시 권위 정의를 인용하지 않고 추측 — Rule 17~20 (근본 원인 우선) 적용으로 즉시 정정.
- **MINOR-2 정정 2차** (2026-05-07, 정정 1차 명령 실행 후 발견): 권위 정의 7종이 **혼합 형식** — pytest 호환 3종 (`test_phase17_faction_handoff_contract.py / test_phase14b_snn_integration.py / test_phase17_faction_stage3.py`, 27 tests) + standalone Python script 4종 (`test_economy.py / test_governance.py / test_class_promotion.py / test_nomos.py`, def test_ 없음, module-level 500틱 시뮬 + sys.exit(1) on FAIL). 단일 `pytest` 명령으로 7종 모두 호출 시 4 standalone는 pytest module import로 silently 실행되며 stdout이 capture되어 PASS/FAIL 명시 검증 불가능. 따라서 §7 명령을 두 그룹 분리 형식으로 재정정 (pytest 3종 + standalone 4종 sequential `&&`). **근본 원인**: 권위 정의가 파일명만 freeze하고 실행 방식을 명시 안 함 + spec MINOR-2 보강 시 7종 형식 동질성을 가정 — Rule 17~20 (근본 원인 우선) 적용으로 즉시 정정. 실행은 분리 형식으로만 수행.
- TRIVIA-1 (§3.3 #14 grep 패턴 강화) — 선택적 개선 영역, 미적용 (현 형식으로도 검증 가능)
- evidence cross-reference: `subagent-runs/claude/phase17-dc1c-spec-review-1차-2026-05-07/` (run-manifest.md / results/review.result.md / run-summary.md)
- 본 spec 자체 봉인 status: **rev.0+ 초안 — sub-implementer 사용자 승인 대기 (CRITICAL/MAJOR 0건 — 구현 가능 상태)**

### rev.1 — 2026-05-07 [봉인] (sub-impl 14/14 PASS + 회귀 7종 PASS + paper §7-1 evidence 보강 결론)

#### OQ 1C-5 [확정] — alt planet config 식별

`alt name = "nova_cool"`, `NovaPlanet(sea_level_temp_c=10.0)` (default 16.0 → ΔT=-6°C 한랭).

근거 (impl.result.md §1.1):
- `sea_level_temp_c`는 ClimateEngine `_compute_region_weather` Stage 2 (계절 기온) + Stage 4 (바람) + cum buffer (heatwave/coldsnap 임계) 에 cascading 영향 → 단일 파라미터 변동으로 rainfall 분포 변화를 추적 가능한 가장 직관적 후보.
- 다른 후보 (`axial_tilt_deg` / `eccentricity` / `solar_constant`) 는 P50 위주 분포에서 효과 미약.
- NovaPlanet `@dataclass(frozen=True)` invariant 유지 (인스턴스 파라미터 변동만, 본문 0건).

#### OQ 1C-6 [확정] — 4축 비교 표 해석 column 분해

spec §1.0 권고 그대로 채택 (sub-impl 단계에서 새 분석 차원 추가 0건):
- `unit_effect = real_P50 - normalized_P50` — 단위 영향 (`precipitation_mm` 원시 단위 vs `/30.0` 정규화 차이)
- `config_effect = real_P50 - multiconfig_P50` — config 한정 (default vs alt config 차이)
- `natural_evolution = min(normalized_P50, multiconfig_P50)` — config-agnostic + unit-normalized 잔존분 (보수적 추정)

#### sub-impl 14/14 self-validation PASS

mypy strict 2종 / ruff / collect 실행 2종 / extractor 재실행 2종 / 라벨 grep 2종 / git diff empty 4종 / 4축 비교 표 inline 16 row — 모두 PASS. `STOP_FOR_USER` 미발생.

#### 회귀 7종 PASS (혼합 형식 분리 실행)

- pytest 호환 3종: 27/27 PASS (`test_phase17_faction_handoff_contract.py` 12 + `test_phase14b_snn_integration.py` 8 + `test_phase17_faction_stage3.py` 7) — 819.39s
- standalone script 4종 ALL PASS: `test_economy.py` 6/6 + `test_governance.py` 8/8 + `test_class_promotion.py` 6/6 + `test_nomos.py` 5/5 — 합계 25/25 sub-check, 모든 script `ALL PASS` print + exit code 0

→ "코어 무영향" logical proof 의 *실행* 마무리 완료. 신규 파일 only이므로 회귀 영역 0 영향 입증.

#### paper §7-1 evidence value 보강 결론

> **`rainfall_30d` cumulative 5배 차이 (synthetic 5.40 → real 29.20, +440.7%) 의 96.7% 가 단위 영향**
> (`precipitation_mm` 원시 단위 → `/30.0` 정규화 후 P50 = **0.97**, synthetic 의 약 18% 수준)
> **config 한정 영향 0%** (sea_level_temp_c=10.0 한랭 변동에도 multiconfig P50 = 29.20 = default).
> **temperature_30d** 는 alt config axis 가 정확히 ΔT=-6.00°C 반영 (channel 분리 검증).

paper §7-1 evidence value boost 3가지:
1. **단위 정렬 강화**: synthetic 5.40 vs real 29.20 직접 비교 대신, **정규화-후 P50 = 0.97** 을 random[0,1] 단위와 동등 비교 기준으로 보고.
2. **config 한정 영향 분리**: sea_level_temp_c 변동이 rainfall 에 영향 0 / temperature 에 정확 ΔT 반영 → ClimateEngine 채널 분리 입증 (credibility 가산).
3. **rev.next OQ 권고**: rainfall 분포 변경에는 `base_precip_mm` 또는 `base_humidity` 직접 변동이 효과적 (rev.next OQ 1C-7 / 1C-8 영역으로 위임).

#### §Uncertainty 3건 (sub-impl impl.result.md §Uncertainty 참조)

- **U1**: multiconfig sea_level_temp_c=10.0 의 rainfall 영향이 0 인 이유 — `precip_mm = base_precip_mm/30.0 * intensity * season_precip_mult` 식이 sea_level_temp_c 에 둔감 (간접 channel 인 humidity 통한 precip_threshold 조정도 P50 분포 무영향).
- **U2**: normalized P50 = 0.97 < synthetic 5.40 의 의미 — ClimateEngine 강수 빈도 "비-항상" (synthetic random[0,1] 은 모든 tick 양수 / ClimateEngine 은 `is_raining` 통과 시에만). paper §7-1 작성 시 synthetic baseline 의 단위 모호성 명시 의무.
- **U3**: 회귀 7종 PASS 실행이 sub-impl writable boundary 외 → supervisor 단계 직접 실행 (본 rev.1 봉인 시 완료).

#### evidence cross-reference

- `subagent-runs/claude/phase17-phi1-land-climate-multiconfig-normalized-2026-05-07/`
  - `run-manifest.md` (메타 + writable boundary + OQ sub-impl 결정 영역)
  - `prompts/impl.prompt.md` (sub-impl 자기완결적 prompt)
  - `results/impl.result.md` (sub-impl 작성, 286 LOC, 14/14 PASS + §4 16 row 비교 표 + §결론 paper §7-1 boost)
  - `run-summary.md` (supervisor 작성, 사용자 보고용)

#### 신규 산출 파일 (자동 생성)

- `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_normalized.py` (449 LOC)
- `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_multiconfig.py` (496 LOC)
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_normalized/` (11 파일: 3 seed × {probe,distribution,summary} + aggregate × {distribution,summary})
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_multiconfig/` (11 파일, 동일 구조)

#### spec 자체 봉인 status: **rev.1 [봉인]** (2026-05-07)

본 collector 2종 + probe data 2 dir + impl evidence + 회귀 7종 PASS 로 §7-2 mechanism 진입 전 evidence base 강화 완료. paper §7-1 보강 결론은 `rainfall_30d` 5배 차이의 정량 분해 (96.7% 단위 영향 / 0% config / 3.3% 자연 진화) 로 봉인.
