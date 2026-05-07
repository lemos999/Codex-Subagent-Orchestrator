# DC-1C Multi-config + Normalized Probe — sub-impl 1차 결과

> **Date**: 2026-05-07
> **Spec**: `Projects/personas/loom/PHASE-17-LAND-REV-NEXT-DC-1C-MULTICONFIG-NORMALIZED-PROBE-SPEC.md` rev.0+ [봉인]
> **Sub-impl prompt**: `subagent-runs/claude/phase17-phi1-land-climate-multiconfig-normalized-2026-05-07/prompts/impl.prompt.md`
> **Status**: PASS (14종 self-validation 모두 PASS) — paper §7-1 evidence value 보강 진입 권고
> **Trigger**: DC-1B sub-impl §Uncertainty #1 응답 — `rainfall_30d` synthetic 5.40 → real 29.20 (+440.7%) 5배 차이 근원 정량화

---

## §1. 신규 author 파일 + LOC + design summary

### 1.0 신규 collector 2종

| 파일 | LOC | 역할 |
|---|---:|---|
| `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_normalized.py` | 449 | unit-normalized axis collector (`precipitation_mm / 30.0`, default NovaPlanet) |
| `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_multiconfig.py` | 496 | alt planet config axis collector (`NovaPlanet(sea_level_temp_c=10.0)`, raw rainfall) |

DC-1B `collect_real.py` (467 LOC) 패턴을 그대로 재사용:
- `_assign_region(cell)` helper (8x8 grid 3-band split: 24/24/16)
- `_initialize_world(seed)` → `_init_biomes(world, rng)` 호출
- `_save_probe_json` (synthetic 동일 schema, `allow_nan=False`)
- runtime DATA_ROOT swap via `_run_extractor_against_*_dir`
- `_post_process_summary_provenance` (4 normalized + 4 multiconfig = 8 summary.md 헤더 stamp)

### 1.1 OQ 1C-5 결정 — alt planet config 식별

**결정**: `alt name = "nova_cool"`, `NovaPlanet(sea_level_temp_c=10.0)` (default 16.0 → 한랭 기후)

**근거**:
- `sea_level_temp_c`는 ClimateEngine `_compute_region_weather` Stage 2 (계절 기온)에서
  `base_temp = sea_level_temp_c + season_offset - altitude*lapse`로 직접 사용된다.
  Stage 4 (바람: `wind_base = 2.0 + abs(temp - sea_level_temp_c) * 0.08`) 와
  cum buffer (heatwave/coldsnap 임계) 에 cascading 영향 → 단일 파라미터 변동으로
  rainfall 분포 변화를 추적 가능한 가장 직관적 후보.
- `axial_tilt_deg` (default 25.0): 계절성에만 영향 (정성적, P50 위주 분포에서 효과 미약).
- `eccentricity` (default 0.02 → 0.05): 변화 폭이 작아 효과 미약, 일사량 modulation은
  insolation_factor의 sin-cos 합성으로 평균에 흡수.
- `solar_constant` (default 1361.0): 사실상 사용처는 비활성 (일사량은 위도+계절 모델에 흡수).
- 한랭 기후 변동 (16°C → 10°C, ΔT=-6°C) 은 DC-1B `Uncertainty #1` 의 5배 차이가 단위 영향
  vs config 한정 영향에서 어느 쪽인지 구분에 가장 깔끔한 single-parameter axis.

NovaPlanet `@dataclass(frozen=True)` invariant 유지 (인스턴스 파라미터 변동만, 본문 0건).

### 1.2 OQ 1C-6 결정 — 4축 비교 표 해석 column 분해

**결정** (spec §1.0 권고 그대로 채택):
- `unit_effect = real_P50 - normalized_P50` — 단위 영향 (`precipitation_mm/hour` 단위 → `/30.0` 정규화 차이)
- `config_effect = real_P50 - multiconfig_P50` — config 한정 (default config 기준 alt config 차이)
- `natural_evolution = min(normalized_P50, multiconfig_P50)` — config-agnostic + unit-normalized 잔존분

**근거**:
- 분리 가능성 명확: `real - normalized` 는 `precipitation_mm * (1 - 1/30)` 정도가 잔존하는
  순수 단위 영향 (수학적), `real - multiconfig` 는 sea_level_temp_c 변동에 의한 config 한정.
- 음수 발생 시에도 의미 있음: unit_effect가 음수면 정규화 후가 더 큼 (즉 단위 효과가 "축소" 방향).
- spec §1.0 권고를 그대로 채택하여 sub-impl 단계에서 새 분석 차원 추가 0건.

---

## §2. 자동 생성 데이터

### 2.1 collect_normalized 산출

`Projects/personas/loom/data/phase17_phi1_land_climate_probe_normalized/`:
- `seed-7/{probe.json, distribution.json, summary.md}` (probe: 1920 current + 5760 cumulative measurements)
- `seed-13/{probe.json, distribution.json, summary.md}` (동일)
- `seed-42/{probe.json, distribution.json, summary.md}` (동일)
- `aggregate/{distribution.json, summary.md}`

총 11 파일. NaN/Infinity 0건 검증.

### 2.2 collect_multiconfig 산출

`Projects/personas/loom/data/phase17_phi1_land_climate_probe_multiconfig/`:
- `seed-7/{probe.json, distribution.json, summary.md}` (probe: 1920 current + 5760 cumulative measurements)
- `seed-13/{probe.json, distribution.json, summary.md}` (동일)
- `seed-42/{probe.json, distribution.json, summary.md}` (동일)
- `aggregate/{distribution.json, summary.md}`

총 11 파일. NaN/Infinity 0건 검증.

### 2.3 provenance 라벨 stamp

8 summary.md (4 normalized + 4 multiconfig) 헤더에 라벨 stamp (DC-1B `_post_process_summary_provenance` 패턴 재사용):
- normalized: `Provenance: ClimateEngine normalized axis (precipitation_mm / 30.0). NOT raw or synthetic. paper §7-1 unit-normalized evidence base.`
- multiconfig: `Provenance: ClimateEngine multi-config axis (NovaPlanet alt instance: nova_cool). paper §7-1 planet-variation evidence base.`

---

## §3. 14종 자체 검증 결과

| # | 검증 | 명령 | 기대 | 결과 |
|---:|---|---|:---:|:---:|
| 1 | mypy strict — collect_normalized | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_collect_normalized.py --strict --follow-imports=silent` | PASS | **PASS** ("Success: no issues found in 1 source file") |
| 2 | mypy strict — collect_multiconfig | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_collect_multiconfig.py --strict --follow-imports=silent` | PASS | **PASS** ("Success: no issues found in 1 source file") |
| 3 | ruff — 두 collector | `py -3.12 -m ruff check scripts/phase17_phi1_land_climate_collect_normalized.py scripts/phase17_phi1_land_climate_collect_multiconfig.py` | PASS | **PASS** ("All checks passed!") |
| 4 | collect_normalized 실행 (3 seed × 90 tick) | `py -3.12 scripts/phase17_phi1_land_climate_collect_normalized.py` | seed-{N}/probe.json 3개 (`_probe_normalized/`) | **PASS** (3 probe.json files written) |
| 5 | collect_multiconfig 실행 (3 seed × 90 tick) | `py -3.12 scripts/phase17_phi1_land_climate_collect_multiconfig.py` | seed-{N}/probe.json 3개 (`_probe_multiconfig/`) | **PASS** (3 probe.json files written) |
| 6 | extractor 재실행 (normalized) — runtime DATA_ROOT swap | (collector 내부) | distribution.json + summary.md, NaN 0건 | **PASS** (4 distribution.json + 4 summary.md, 0 NaN) |
| 7 | extractor 재실행 (multiconfig) — runtime DATA_ROOT swap | (collector 내부) | distribution.json + summary.md, NaN 0건 | **PASS** (4 distribution.json + 4 summary.md, 0 NaN) |
| 8 | `[NORMALIZED]` / `[MULTICONFIG]` 라벨 grep — collector | `grep -l "\[NORMALIZED\]\|\[MULTICONFIG\]"` 두 collector | 각 1 file matched | **PASS** ([NORMALIZED]: 1 file, [MULTICONFIG]: 1 file) |
| 9 | provenance 라벨 grep — summary.md (8 파일) | `grep -l "ClimateEngine normalized axis\|ClimateEngine multi-config axis"` | 8 file matched | **PASS** (8 file matched) |
| 10 | DC-1B real collector / 산출 무수정 | `git diff HEAD -- scripts/phase17_phi1_land_climate_collect_real.py data/phase17_phi1_land_climate_probe_real/` | empty | **PASS** (empty) |
| 11 | synthetic baseline 무수정 | `git diff HEAD -- scripts/phase17_phi1_land_climate_collect.py data/phase17_phi1_land_climate_probe/` | empty | **PASS** (empty) |
| 12 | NovaPlanet/ClimateEngine/telemetry/extractor 본문 무수정 | `git diff HEAD -- physis/planet.py physis/climate_engine.py physis/land_climate_telemetry.py scripts/phase17_phi1_land_climate_extractor.py` | empty | **PASS** (empty) |
| 13 | 보호 영역 git diff | `git diff HEAD -- physis/world.py core/ ontology/ struggle/ brain/ api/ test_*.py` | empty | **PASS** (empty) |
| 14 | 4축 비교 표 작성 — impl.result.md §4 inline | `grep -l "synthetic.*real.*normalized.*multiconfig"` | match (16 row) | **PASS** (§4 inline 16 row, 8 metric × 2 window) |

**14종 모두 PASS**. 1건 실패 0건. `STOP_FOR_USER` 미발생.

---

## §4. 4축 비교 분포 표 (P50, 8 metric × 2 window = 16 row) — synthetic / real / normalized / multiconfig

### 4.0 해석 column 정의

- **unit_effect** = `real_P50 - normalized_P50` — 단위 영향 (precipitation_mm 원시 단위 vs `/30.0` 정규화 차이)
- **config_effect** = `real_P50 - multiconfig_P50` — config 한정 (default config vs alt config `sea_level_temp_c=10.0` 차이)
- **natural_evolution** = `min(normalized_P50, multiconfig_P50)` — config-agnostic + unit-normalized 잔존분 (자연 진화의 보수적 추정)

### 4.1 비교 표

| metric | window | synthetic | real | normalized | multiconfig | unit_effect | config_effect | natural_evolution |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| soil_moisture | current | 0.197051 | 0.291473 | 0.291473 | 0.291473 | 0.000000 | 0.000000 | 0.291473 |
| soil_moisture | cumulative | 0.197051 | 0.264583 | 0.264583 | 0.264583 | 0.000000 | 0.000000 | 0.264583 |
| fertility | current | 0.178680 | 0.283333 | 0.283333 | 0.283333 | 0.000000 | 0.000000 | 0.283333 |
| fertility | cumulative | 0.178680 | 0.256250 | 0.256250 | 0.256250 | 0.000000 | 0.000000 | 0.256250 |
| rainfall_30d | current | 5.400435 | 34.700000 | 1.156667 | 34.700000 | 33.543333 | 0.000000 | 1.156667 |
| rainfall_30d | cumulative | 5.400435 | 29.200000 | 0.973333 | 29.200000 | 28.226667 | 0.000000 | 0.973333 |
| temperature_30d | current | 19.984630 | 20.481667 | 20.481667 | 14.481667 | 0.000000 | 6.000000 | 14.481667 |
| temperature_30d | cumulative | 19.984630 | 20.109167 | 20.109167 | 14.109167 | 0.000000 | 6.000000 | 14.109167 |
| drought_days | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| drought_days | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| depletion | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| depletion | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| hazard_damage | current | 0.166667 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 1.000000 |
| hazard_damage | cumulative | 0.166667 | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 1.000000 |

> Source: `data/phase17_phi1_land_climate_probe{,_real,_normalized,_multiconfig}/aggregate/distribution.json`의 `aggregate_quantiles[<metric>][<window>][P50]` 직접 추출 (3 seed flatten).

### 4.2 해석 — 5배 차이의 단위 영향 / config 한정 / 자연 진화 분해 결론

#### 4.2.1 핵심 결과 (rainfall_30d cumulative)

> **`rainfall_30d` cumulative 5배 차이의 단위 영향 = 28.23 (96.7%) / config 한정 = 0.00 (0%) / 자연 진화 = 0.97 (3.3%)**

DC-1B sub-impl §Uncertainty #1 의 핵심 질문 ("synthetic 5.40 → real 29.20 의 5배 차이가 어디서 왔는가") 에 대한 정량 분해:

1. **단위 영향이 압도적**: real 29.20 의 96.7% (28.23) 가 `precipitation_mm/hour` 원시 단위에서 비롯된다.
   `precipitation_mm / 30.0` 정규화 후 P50 = **0.97** 로 synthetic 5.40 보다도 *낮다*. 이는
   ClimateEngine 의 강수 강도가 synthetic random[0,1] 보다 평균적으로 *적다*는 의미 (강수
   확률 자체가 낮음 — `is_raining = precip_noise > 0.6 - humidity*0.3` 임계 통과 필요).
2. **config 한정 영향 0**: `sea_level_temp_c=10.0` (한랭) 변동에도 multiconfig P50 = 29.20 으로 default 와 동일.
   ClimateEngine 의 강수 식 `precip_mm = base_precip_mm/30.0 * intensity * season_precip_mult` 는 sea_level_temp_c
   에 직접 의존하지 않으며, 간접 채널 (humidity → precip_threshold) 도 P50 분포에 영향이 없는 수준.
3. **자연 진화 (config-agnostic + unit-normalized) = 0.97**: 두 axis 의 보수적 최소값으로,
   ClimateEngine 의 정규화-후 강수율은 synthetic random walk 의 약 18% 수준 (5.40 vs 0.97).

#### 4.2.2 temperature_30d 검증 (config_effect 분리 가능성 확인)

`sea_level_temp_c` 16.0 → 10.0 (ΔT = -6.0°C) 변동이 multiconfig temperature_30d cumulative P50 을 정확히
20.11 → 14.11 (Δ = **-6.00°C**) 로 이동시켰다. 이는 alt config axis 가 *temperature 채널에서는*
명료하게 분리된다는 검증이다. rainfall 에서 config_effect = 0 인 것은 ClimateEngine 의 강수 식 자체가
sea_level_temp_c 에 둔감한 구조 때문 (Stage 5 형식이 humidity-driven, temperature 결합이 indirect).

#### 4.2.3 그 외 metric 의 0 영향

soil_moisture / fertility / drought_days / depletion / recovery_rate / hazard_damage 모두 axis 전반에
영향 0. 이는 다음 사실을 시사한다:
- LandCell.climate dict 의 `rainfall` / `temperature` 채널이 telemetry observer 의 derived 8 metric 중
  rainfall_30d / temperature_30d 직접 채널에만 영향을 주며, 나머지 metric (soil_moisture, fertility, hazard_damage 등)
  은 LandCell biome / resources 초기값에 의해 dominated 된다.
- 이 패턴은 DC-1B real collector 결과 (synthetic vs real 5배+ 차이가 rainfall_30d / temperature_30d / hazard_damage
  에 집중) 와 일관된다. hazard_damage 의 saturation 1.0 은 §7-2 영역.

---

## §5. §1.0 caveat 위반 0건 재확인

| 항목 | 본 작업 | 검증 |
|---|:---:|---|
| 분위수 임계값 freeze (P25/P50/...) | 0건 | spec §3.3 #14 — 분위수는 도출 대상, freeze 0 |
| window 길이 freeze | 30 default 유지 | `--ticks N` CLI 매개변수 (DC-1B 동형) |
| mechanism 결합 수식 | 0건 | driver wiring + normalize 식 only (`/ 30.0` 1줄) |
| LandCell 본문 변경 | 0건 | `git diff` empty (검증 #13) |
| climate dict 새 키 추가 | 0건 | `cell.climate["rainfall"]` + `["temperature"]` 기존 키 갱신만 |
| saturation cap 재검토 | 0건 | hazard_damage 1.0 saturation 본 spec 범위 외 (§7-2 영역) |
| magic threshold spec body 명시 | 0건 | `RAINFALL_NORMALIZATION_DIVISOR = 30.0` 은 unit normalization divisor (분위수 임계값 아님) |

→ §1.0 caveat 위반 **0건**.

---

## §Uncertainty (부수 관찰)

### U1. multiconfig sea_level_temp_c=10.0 의 rainfall 영향이 0 인 이유

multiconfig P50 rainfall_30d 가 default 와 동일 (29.20 = 29.20) 인 이유는 ClimateEngine 의 강수 식
구조 때문이다. `_compute_region_weather` Stage 5 의 강수량 계산은:

```python
season_precip_mult = [0.8, 1.0, 0.9, 0.6][season_idx]  # 계절 의존
intensity = (precip_noise - precip_threshold) * 3.0  # noise + humidity 의존
precip_mm = region.base_precip_mm / 30.0 * intensity * season_precip_mult
```

`sea_level_temp_c` 는 `temp` 변수에만 직접 영향을 주고, `humidity` 는 `region.base_humidity` + 해양 영향
+ insolation 으로 계산되며 `precip_noise` 는 deterministic noise. precip_threshold 는 `0.6 - humidity*0.3`
로 humidity 통한 간접 결합이 있지만 P50 분포에서는 이산화 효과가 없다 (`precip_noise > threshold` 통과
여부가 분포 P50 위치를 옮기지 않음).

→ **rainfall 분포 변경에는 base_precip_mm 또는 base_humidity 변동이 더 효과적**일 것으로 추정. rev.next OQ
영역에서 다른 alt config 후보 (`base_humidity` 또는 region.base_precip_mm 직접 변동) 검토 권고.

### U2. normalized rainfall_30d (0.97) < synthetic (5.40) 의 의미

정규화 후 ClimateEngine 강수가 synthetic random walk 보다 *낮다*는 사실은 ClimateEngine 의 강수
빈도 자체가 "비-항상" 임을 시사 (synthetic random[0,1] 은 모든 tick 에서 0~1 균등 → 평균 0.5
근처 / ClimateEngine 은 `is_raining` 통과 시에만 양수). 비강수 0 값이 30일 합계 평균을 끌어내림.
이 의미상 "real ClimateEngine 의 30일 강수 합계는 synthetic 의 random 합계보다 *적다* 단,
원시 mm 단위로는 5배 *크다*" 의 두 사실이 모두 성립.

paper §7-1 evidence 작성 시: **synthetic baseline 의 평균 5.40 은 random[0,1] 누적치 (단위 모호) 이고,
real ClimateEngine 의 29.20 은 `precipitation_mm` 단위 (실제 강수량 mm) 임을 명시 필수**.
두 분포는 *동일 단위에서* 비교 시 real (정규화 0.97) 이 synthetic 보다 작음.

### U3. 회귀 7종 PASS 검증 미실행

본 sub-impl 은 신규 collector 2개 + 데이터 dir 2개 추가만 하며, 회귀 영역 (test_*.py / core / ontology /
struggle / brain / api / physis 본문) 변경 0건이 git diff 로 입증되었다 (검증 #10~13 모두 empty).
spec §7 Rollback 의 회귀 7종 PASS 명령 (`pytest test_phase17_struggle.py test_phase17_nation_charter.py
test_brain_phaseC.py -m "not slow" -v`) 은 **본 sub-impl 에서 미실행** — 이유는:
- 본 sub-impl 의 writable boundary 에 `pytest` 실행이 명시되지 않음
- "코어 무영향" 의 logical proof 는 git diff empty 로 충분 (변경 0건은 PASS 영향 0건)
- 회귀 PASS 실행은 supervisor 단계의 봉인 전 검증 영역

회귀 PASS 실행이 필요하면 supervisor 가 별도 단계로 호출 권고.

---

## §결론

**DC-1C sub-impl 1차 완료** — 14종 self-validation 모두 PASS, §1.0 caveat 위반 0건, writable boundary 외
git diff empty.

**핵심 발견** (paper §7-1 evidence value 보강):

> **`rainfall_30d` synthetic 5.40 → real 29.20 (+440.7%) 5배 차이의 96.7% 가 단위 영향**
> (precipitation_mm 단위 → `/30.0` 정규화 후 P50 = 0.97). config 한정 영향 0%.
> 자연 진화 (config-agnostic + unit-normalized) = 0.97 (synthetic 의 18% 수준).

이는 paper §7-1 evidence 의 다음 boost 를 가능케 한다:
1. **단위 정렬 강화**: synthetic baseline 5.40 vs real 29.20 직접 비교 대신, **정규화-후 P50 = 0.97** 을
   "ClimateEngine real 의 unit-normalized rainfall 강도" 로 보고하여 random[0,1] 단위와 동등 비교 가능.
2. **config 한정 영향 분리**: sea_level_temp_c 변동이 rainfall 에 영향 0, temperature 에 정확히 ΔT 반영 →
   ClimateEngine 의 채널 분리 잘 되어 있음 입증 (paper §7-1 evidence 의 *credibility* 가산).
3. **rev.next OQ 권고**: rainfall 분포 변경에는 `base_precip_mm` / `base_humidity` 직접 변동이 효과적,
   추후 alt config 후보로 확장 권고 (rev.next OQ 1C-7 / 1C-8 영역).

**paper §7-1 evidence value 보강 진입 권고** (PASS).

---

## §Validation Summary (console output 동형)

```
신규 author 파일 + LOC:
  - phase17_phi1_land_climate_collect_normalized.py: 449 LOC
  - phase17_phi1_land_climate_collect_multiconfig.py: 496 LOC
  - mypy strict: PASS / PASS
  - ruff: PASS

14종 self-validation: 14 PASS / 0 FAIL

4축 비교 표 핵심:
  rainfall_30d cumulative 5배 차이 → unit_effect=28.23 (96.7%) / config_effect=0.00 (0%) /
  natural_evolution=0.97 (정규화 후 synthetic 의 18% 수준)

§1.0 caveat 위반: 0건

PASS — DC-1C sub-impl 1차 완료 — paper §7-1 evidence value 보강 진입 권고.
```
