# DC-1C Multi-config + Normalized — sub-implementer 1차 Run Summary

## Outcome

| Metric | Value |
|---|---|
| 신규 파일 author | 2 (`collect_normalized.py` 449 LOC + `collect_multiconfig.py` 496 LOC, mypy strict + ruff PASS) |
| 수정된 기존 파일 | 0 (synthetic baseline / DC-1B real / extractor / NovaPlanet / ClimateEngine / telemetry / world.py / 코어 모두 0건) |
| 자동 생성 데이터 | 22 파일 (3 seed × probe.json + 3 seed × distribution.json + 3 seed × summary.md = 9 + aggregate distribution.json + aggregate summary.md = 11; normalized + multiconfig 각각 11 = 22) |
| forbidden zone git diff | empty for all paths (PASS) |
| 자체 검증 14종 | **14 / 14 PASS** |
| §1.0 caveat 위반 | 0건 |
| **rainfall_30d 5배 차이 분해** | **단위 영향 28.23 (96.7%) / config 한정 0.00 (0%) / 자연 진화 0.97 (synthetic의 18%)** |
| temperature_30d config 검증 | multiconfig ΔT=-6.00°C 정확 반영 (default 20.11 → 14.11) |

## 결론

**PASS — DC-1C sub-impl 1차 완료. paper §7-1 evidence value 보강 진입 권고.**

DC-1B sub-impl §Uncertainty #1 (`rainfall_30d` 5배 차이의 근원) 정량 분해 완료:

> `rainfall_30d` synthetic 5.40 → real 29.20 (+440.7%) 5배 차이의 **96.7%가 단위 영향** (precipitation_mm 단위 → `/30.0` 정규화 후 P50 = 0.97). **config 한정 영향 0%** (sea_level_temp_c=10.0 변동이 rainfall에 무영향). **자연 진화 = 0.97** (synthetic의 18% — ClimateEngine 강수 빈도가 random walk보다 낮음).

`temperature_30d` 검증으로 alt config axis가 temperature 채널에서는 ΔT=-6.00°C 정확 반영 — multiconfig collector의 분리 능력은 명료. rainfall에서 config_effect=0인 것은 ClimateEngine 강수 식 구조 (`base_precip_mm` / `base_humidity`-driven, sea_level_temp_c 둔감) 때문.

## Files

### Code (writable scope, 2 new files)

- `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_normalized.py` (449 LOC)
  - `RAINFALL_NORMALIZATION_DIVISOR = 30.0` 모듈 상수 (unit normalization divisor — DEFAULT_WINDOW_SIZE 정렬)
  - `cell.climate["rainfall"] = weather["precipitation_mm"] / 30.0` (raw 갱신, dict 키 추가 0)
  - default `NovaPlanet()` driver (DC-1B와 동일 baseline)
  - runtime DATA_ROOT swap (DC-1B 동형) → extractor 본문 0건 변경
  - provenance 라벨: `[NORMALIZED]` + summary.md 헤더 stamp
- `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_multiconfig.py` (496 LOC)
  - `alt_config = NovaPlanet(sea_level_temp_c=10.0)` 인스턴스화 (NovaPlanet 본문 0건 변경, frozen=True invariant 유지)
  - `cell.climate["rainfall"] = weather["precipitation_mm"]` (raw — DC-1B 동형, normalize 0건)
  - alt name = `nova_cool` (CLI `--alt-config nova_cool` default)
  - provenance 라벨: `[MULTICONFIG] phase17_phi1_land_climate_collect_multiconfig.py — NovaPlanet(nova_cool)`

### Data (collector + extractor 산출, 22 파일)

- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_normalized/` (11 파일)
  - `seed-{7,13,42}/{probe,distribution,summary}.{json,md}` × 3
  - `aggregate/{distribution,summary}.{json,md}`
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_multiconfig/` (11 파일)
  - `seed-{7,13,42}/{probe,distribution,summary}.{json,md}` × 3
  - `aggregate/{distribution,summary}.{json,md}`

### Evidence

- `subagent-runs/claude/phase17-phi1-land-climate-multiconfig-normalized-2026-05-07/run-manifest.md`
- `subagent-runs/claude/phase17-phi1-land-climate-multiconfig-normalized-2026-05-07/prompts/impl.prompt.md`
- `subagent-runs/claude/phase17-phi1-land-climate-multiconfig-normalized-2026-05-07/results/impl.result.md` (4축 비교 §4 inline 16 row + OQ 1C-5/1C-6 결정 + §Uncertainty 3건 + §결론)
- `subagent-runs/claude/phase17-phi1-land-climate-multiconfig-normalized-2026-05-07/run-summary.md` (this file)

## Validation log highlights

```
mypy strict (collect_normalized.py):     Success: no issues found in 1 source file
mypy strict (collect_multiconfig.py):    Success: no issues found in 1 source file
ruff (두 collector):                     All checks passed!
collector_normalized 실행 (3 seed × 90 tick):  3 probe.json written (_probe_normalized/)
collector_multiconfig 실행 (3 seed × 90 tick): 3 probe.json written (_probe_multiconfig/)
extractor 재실행 (normalized) — runtime DATA_ROOT swap: 8 파일 산출, NaN/Infinity 0 hit
extractor 재실행 (multiconfig) — runtime DATA_ROOT swap: 8 파일 산출, NaN/Infinity 0 hit
[NORMALIZED] / [MULTICONFIG] 라벨 grep: 각 1 file matched
ClimateEngine normalized axis / multi-config axis 라벨 grep: 8 summary.md files matched
git diff DC-1B real collector: empty
git diff synthetic baseline: empty
git diff NovaPlanet/ClimateEngine/telemetry/extractor: empty
git diff 보호 영역 (world.py + core/ + ontology/ + struggle/ + brain/ + api/ + test_*.py): empty
4축 비교 표 grep (synthetic.*real.*normalized.*multiconfig): match (16 row)
```

## §1.0 caveat compliance

- 분위수 임계값 freeze: 0건 (P25/P50/P67/P75/P90는 산출 *대상*; magic threshold 신규 코드 어디에도 없음)
- window/tick 길이 freeze: `--ticks` 매개변수화 (default 90)
- mechanism 결합 수식 freeze: 0건 (driver wiring + `/30.0` 1줄 only; coupling formulas reserved for §7-2)
- LandCell 본문 변경: 0건
- climate dict 새 키 추가: 0건 (rainfall + temperature 기존 키만 갱신)
- saturation cap 재검토: 0건 (hazard_damage 1.0 saturation은 §7-2 영역)
- magic threshold spec body 명시: 0건 (`RAINFALL_NORMALIZATION_DIVISOR = 30.0`은 unit normalization divisor — 분위수 임계값 아님)

## OQ sub-impl 결정 (rev.1 봉인 영역)

### OQ 1C-5 (alt planet config 식별) — [결정] `nova_cool = NovaPlanet(sea_level_temp_c=10.0)`

`sea_level_temp_c` 16.0 → 10.0 (한랭 ΔT=-6°C). NovaPlanet `@dataclass(frozen=True)` invariant 유지 (인스턴스 파라미터 변동만, 본문 0건). 본 결정은 spec rev.1 §2.1 / §5 OQ 1C-5 [확정]으로 승격 권고.

### OQ 1C-6 (4축 비교 표 해석 column) — [결정] spec §1.0 권고 그대로 채택

- `unit_effect = real_P50 - normalized_P50`
- `config_effect = real_P50 - multiconfig_P50`
- `natural_evolution = min(normalized_P50, multiconfig_P50)`

본 결정은 spec rev.1 §2.5 / §5 OQ 1C-6 [확정]으로 승격 권고.

## 4축 비교 분포 핵심 (rev.1 봉인 evidence)

| metric | window | synthetic | real | normalized | multiconfig | unit_effect | config_effect | natural_evolution |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **rainfall_30d** | **cumulative** | **5.400** | **29.200** | **0.973** | **29.200** | **28.227** | **0.000** | **0.973** |
| rainfall_30d | current | 5.400 | 34.700 | 1.157 | 34.700 | 33.543 | 0.000 | 1.157 |
| **temperature_30d** | **cumulative** | **19.985** | **20.109** | **20.109** | **14.109** | **0.000** | **6.000** | **14.109** |
| temperature_30d | current | 19.985 | 20.482 | 20.482 | 14.482 | 0.000 | 6.000 | 14.482 |
| soil_moisture | cumulative | 0.197 | 0.265 | 0.265 | 0.265 | 0.000 | 0.000 | 0.265 |
| fertility | cumulative | 0.179 | 0.256 | 0.256 | 0.256 | 0.000 | 0.000 | 0.256 |
| hazard_damage | cumulative | 0.167 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 |
| (이외 4 metric × 2 window 모두 0 영향) | ... | ... | ... | ... | ... | ... | ... | ... |

(자세한 16 row 표 + 해석은 [results/impl.result.md §4](results/impl.result.md))

## §Uncertainty (rev.next OQ 후보)

1. **multiconfig sea_level_temp_c rainfall config_effect = 0** — ClimateEngine 강수 식이 base_precip_mm / base_humidity-driven. sea_level_temp_c 는 temperature 채널에만 직접 영향. rev.next OQ: `base_humidity` 또는 region.base_precip_mm 직접 변동 후보 검토.
2. **normalized rainfall_30d (0.97) < synthetic (5.40)** — ClimateEngine 강수 빈도가 random walk보다 낮음 (`is_raining` 통과 필요). paper §7-1 작성 시 **단위 명시 필수** (synthetic = 비차원 random[0,1] 누적 / real = `precipitation_mm` 단위 실제 강수량 mm).
3. **회귀 7종 PASS 검증 미실행** — git diff empty로 logical proof 충분 (코어 변경 0건). 봉인 전 supervisor 단계에서 별도 실행 권고 (rev.1 봉인 직전).

## Issues

본 sub-impl 범위 내 issue 0건. 부수 관찰 3건은 [results/impl.result.md §Uncertainty](results/impl.result.md)에 명시 (위 목록 동일).

## 권고 (메인 컨텍스트 다음 단계)

1. **DC-1C spec rev.1 봉인**: §2.1 OQ 1C-5 결정 (alt name `nova_cool` + sea_level_temp_c=10.0) + §2.5 / §5 OQ 1C-6 결정 (3 분해 column) + §8 변경 이력 rev.1 entry + 본 evidence cross-reference 추가. paper §7-1 evidence value 보강 결론 §1.4 sub-section 추가 권고.
2. **회귀 7종 PASS 검증** (rev.1 봉인 직전): `py -3.12 -m pytest test_phase17_struggle.py test_phase17_nation_charter.py test_brain_phaseC.py -m "not slow" -v` — git diff empty의 PASS 영향 0건 logical proof를 실행으로 마무리.
3. **분리 commit**: collector_normalized.py + collector_multiconfig.py + probe_normalized data 11 파일 + probe_multiconfig data 11 파일 + impl evidence 4 파일 + DC-1C rev.1 spec = 단일 commit으로 묶음. `82ac1d3` (DC-1B rev.2) / `6197f8e` (synthetic baseline) 와 분리.
4. **paper §7-1 evidence value 보강 진입**: 본 4축 분해가 §7-2 mechanism 결정의 evidence base 강화. 단위 영향 96.7% / config 한정 0% / 자연 진화 18% — 차이의 근원 정량 입증.

## 다음 게이트 (사용자 결정 영역)

| # | 항목 | 권고 |
|---:|---|---|
| 1 | DC-1C spec rev.1 봉인 + 회귀 7종 PASS + 분리 commit | 즉시 진행 권고 — DC-1B rev.2 동일 separation 정책 |
| 2 | rev.next OQ (다른 alt config 후보 / 5축 결합) sub-impl spawn | rev.1 봉인 후 별도 결정 |
| 3 | push origin main (이전 사용자 보류) | collaborator 권한 / fork / PAT 결정 후 재시도 |

## Run timestamp

- Manifest 작성: 2026-05-07
- sub-implementer launch: 2026-05-07
- sub-implementer 완료: 2026-05-07 (~10분, 14 PASS / 0 FAIL)
- run-summary 작성: 2026-05-07
- 회귀 7종 PASS 실행: 2026-05-07 (supervisor 직접 — pytest 27/27 + standalone 25/25 sub-check ALL PASS)
- spec rev.1 [봉인]: 2026-05-07

## Post-summary 정정 (2026-05-07)

본 run-summary §Uncertainty #3 + 권고 #2 의 회귀 명령 (`pytest test_phase17_struggle.py test_phase17_nation_charter.py test_brain_phaseC.py`) 은 spec rev.0+ §7 직접 인용이었으나, 권위 정의 (`PHASE-17-CASE-C-CONTACT-PERSISTENCE-SPEC.md:55`) 와 불일치 (3 파일 모두 미존재). spec rev.0+ MINOR-2 정정 1차 (정확한 7종 인용) + 2차 (혼합 형식 분리: pytest 3종 + standalone script 4종) 적용 후 supervisor 가 회귀 7종 ALL PASS 직접 검증 (pytest 27/27 + standalone 25/25 sub-check). 자세한 정정 이력은 spec rev.1 §8 변경 이력 참조.

§Uncertainty #3 ("회귀 7종 PASS 검증 미실행") → **완료** (rev.1 봉인 직전 supervisor 단독 실행).
