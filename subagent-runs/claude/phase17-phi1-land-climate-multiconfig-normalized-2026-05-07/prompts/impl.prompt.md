# sub-implementer prompt — DC-1C Multi-config + Normalized Probe

## 작업

DC-1C spec rev.0+ ([봉인], spec-review 1차 [승인] + MINOR 2건 보강 2026-05-07) 따라 신규 collector 2종 author + extractor 재실행 + 4축 비교 보고서 작성.

권위 spec (자기완결적 — 직접 Read):
**`Projects/personas/loom/PHASE-17-LAND-REV-NEXT-DC-1C-MULTICONFIG-NORMALIZED-PROBE-SPEC.md`** (rev.0+ 봉인, ~470 line)

## 선행 컨텍스트

DC-1B sub-impl §Uncertainty 2건 응답:
1. `rainfall_30d` synthetic 5.40 → real 29.20 (+440.7%) 의 5배 차이 — 단위 영향(precipitation_mm/hour vs random[0,1]) vs config 한정 vs 자연 진화 구분 필요
2. `hazard_damage` real saturation 1.0 — §7-2 영역 (본 작업 범위 외)

본 작업은 #1 응답 — normalized axis (`precipitation_mm / 30.0`) + multi-config axis (alt NovaPlanet) 두 collector author로 5배 차이의 근원 정량화.

DC-1B 동형 패턴 (`scripts/phase17_phi1_land_climate_collect_real.py` 467 LOC) 참고 — runtime DATA_ROOT swap + provenance 라벨 stamp + `_assign_region` helper 등 동일.

## Writable boundary (이 외 git diff empty 강제)

- `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_normalized.py` (신규)
- `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_multiconfig.py` (신규)
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_normalized/**` (자동 생성)
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_multiconfig/**` (자동 생성)
- `subagent-runs/claude/phase17-phi1-land-climate-multiconfig-normalized-2026-05-07/results/impl.result.md` (본 결과 보고서)

## 금지 영역 (writable boundary 외, git diff empty 강제)

- `scripts/phase17_phi1_land_climate_collect.py` (synthetic baseline 봉인)
- `scripts/phase17_phi1_land_climate_collect_real.py` (DC-1B real collector 봉인)
- `data/phase17_phi1_land_climate_probe/` (synthetic 산출 봉인)
- `data/phase17_phi1_land_climate_probe_real/` (DC-1B real 산출 봉인)
- `scripts/phase17_phi1_land_climate_extractor.py` (본문 무수정 — runtime DATA_ROOT swap 호출만)
- `physis/land_climate_telemetry.py` / `physis/climate_engine.py` / `physis/planet.py` / `physis/world.py` (모두 본문 무수정)
- `core/` `ontology/` `struggle/` `brain/` `api/` `test_*.py` (단방향 계약 — 회귀 7종 보호)

## sub-impl 결정 영역 (OQ 1C-5 / 1C-6)

### OQ 1C-5: alt planet config 식별 (multiconfig collector)

NovaPlanet `@dataclass(frozen=True)` invariant 유지 + 한 가지 의미 있는 변동.

권고 후보 (자율 선택):
- `axial_tilt_deg=15.0` (default 25.0 → 약한 계절성, 자전축 기울기 변동)
- `sea_level_temp_c=10.0` (default 16.0 → 한랭 기후)
- `eccentricity=0.05` (default 0.02 → 타원 궤도, 계절성 강화 + 일사 변동)
- `solar_constant=1200.0` (default 1361.0 → 약한 일사 → 한랭)

**한 가지** 선택 (rev.next OQ로 다중 후보 보류). 선택 + 명명 + 근거를 `impl.result.md` §1.1 에 명시 (예: "alt name = `nova_cool` — sea_level_temp_c=10.0 채택. 한랭 기후 변동이 rainfall 단위 영향 vs config 한정 영향을 가장 깔끔하게 분리").

### OQ 1C-6: 4축 비교 표 해석 column

권고 분해:
- `unit_effect` = real_P50 - normalized_P50 (단위 영향 — `precipitation_mm/hour` 단위 → `/30.0` 정규화 차이)
- `config_effect` = real_P50 - multiconfig_P50 (config 한정 — default config 기준 alt config 차이)
- `natural_evolution` = min(normalized_P50, multiconfig_P50) — config-agnostic + unit-normalized 잔존분

선택 + 근거를 `impl.result.md` §4 표 위에 명시.

## 구현 절차 (DC-1B 동형)

### Step 1: collect_normalized.py author

spec §2.4 의사코드 그대로 구현. 핵심:
- `RAINFALL_NORMALIZATION_DIVISOR = 30.0` 모듈 상수
- `cell.climate["rainfall"] = weather["precipitation_mm"] / 30.0` (raw 갱신; LandCell.climate dict 키 추가 0)
- `cell.climate["temperature"] = weather["temperature_c"]` (단위 변환 없음)
- `_assign_region(cell)` helper (DC-1B 동형 8x8 grid 3등분)
- argparse: `--ticks 90` (default) / `--seeds 7,13,42` (default)
- 출력: `data/phase17_phi1_land_climate_probe_normalized/seed-{N}/probe.json`
- 모듈 docstring 시작: `WARNING — normalized axis collector (precipitation_mm / 30.0 unit normalization, NOT raw)`
- print 시작 라인: `[NORMALIZED] phase17_phi1_land_climate_collect_normalized.py — precipitation_mm / 30.0`
- json.dump strict: `allow_nan=False`
- mypy strict + ruff PASS

### Step 2: collect_multiconfig.py author

`collect_normalized.py` 이후 동형 author. 핵심:
- `RAINFALL_NORMALIZATION_DIVISOR` 사용 0건 — raw mapping 그대로 (DC-1B 동형)
- `alt_config = NovaPlanet(<sub-impl 결정 파라미터>)` 인스턴스화
- `engine = ClimateEngine(planet=alt_config, seed=seed)` (default 대신 alt)
- `cell.climate["rainfall"] = weather["precipitation_mm"]` (raw — DC-1B 동형 — normalize 0건)
- argparse 추가: `--alt-config <name>` (default 한 가지 — sub-impl 결정)
- 출력: `data/phase17_phi1_land_climate_probe_multiconfig/seed-{N}/probe.json`
- 모듈 docstring 시작: `WARNING — alt planet config axis collector (NovaPlanet alt instance, NOT default config)`
- print 시작 라인: `[MULTICONFIG] phase17_phi1_land_climate_collect_multiconfig.py — NovaPlanet(<alt name>)`

### Step 3: 두 collector 실행 (각 3 seed × 90 tick)

```bash
py -3.12 scripts/phase17_phi1_land_climate_collect_normalized.py
py -3.12 scripts/phase17_phi1_land_climate_collect_multiconfig.py
```

각 3 probe.json 생성 확인.

### Step 4: extractor 재실행 (runtime DATA_ROOT swap, DC-1B 동형)

`collect_real.py` 의 `_run_extractor_against_real_dir` 패턴 (line 324-351 참고) 재사용 — extractor 본문 0건 변경, runtime swap만:

```python
# collect_normalized.py + collect_multiconfig.py 각각 내부
import importlib
extractor = importlib.import_module("scripts.phase17_phi1_land_climate_extractor")
original_data_root = extractor.DATA_ROOT
extractor.DATA_ROOT = Path("data/phase17_phi1_land_climate_probe_normalized")  # or _multiconfig
try:
    extractor.main()
finally:
    extractor.DATA_ROOT = original_data_root
```

각 dir 에 `seed-{N}/distribution.json + summary.md` + `aggregate/distribution.json + summary.md` 생성.

### Step 5: provenance 라벨 stamp (summary.md post-process)

DC-1B `_post_process_summary_provenance` 패턴 재사용. 4 normalized + 4 multiconfig = 8 summary.md 헤더에 stamp:

- normalized: `Provenance: ClimateEngine normalized axis (precipitation_mm / 30.0). NOT raw or synthetic. paper §7-1 unit-normalized evidence base.`
- multiconfig: `Provenance: ClimateEngine multi-config axis (NovaPlanet alt instance: <alt name>). paper §7-1 planet-variation evidence base.`

### Step 6: 4축 비교 표 작성 (impl.result.md §4 inline)

DC-1B `_probe_real/aggregate/distribution.json` (synthetic + real) + 본 작업 `_probe_normalized/aggregate/distribution.json` + `_probe_multiconfig/aggregate/distribution.json` aggregate 4 dir 의 distribution.json 읽고 8 metric × 2 window 16 row 표 생성:

```
| metric | window | synthetic | real | normalized | multiconfig | unit_effect | config_effect | natural_evolution | 해석 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| rainfall_30d | cumulative | 5.40 | 29.20 | <X> | <Y> | <real-X> | <real-Y> | min(X,Y) | 5배 차이의 단위 영향=Z, config=W |
| ... |
```

(synthetic + real 값은 DC-1B `_probe_real/aggregate/distribution.json` 또는 `_probe/aggregate/distribution.json` 에서 직접 읽기)

### Step 7: self-validation 14종 (spec rev.0+ §3.3 그대로)

| # | 검증 | 명령 | 기대 |
|---:|---|---|:---:|
| 1 | mypy strict — collect_normalized | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_collect_normalized.py --strict --follow-imports=silent` | PASS |
| 2 | mypy strict — collect_multiconfig | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_collect_multiconfig.py --strict --follow-imports=silent` | PASS |
| 3 | ruff — 두 collector | `py -3.12 -m ruff check scripts/phase17_phi1_land_climate_collect_normalized.py scripts/phase17_phi1_land_climate_collect_multiconfig.py` | PASS |
| 4 | collect_normalized 실행 (3 seed × 90 tick) | `py -3.12 scripts/phase17_phi1_land_climate_collect_normalized.py` | seed-{N}/probe.json 3개 (`_probe_normalized/`) |
| 5 | collect_multiconfig 실행 (3 seed × 90 tick) | `py -3.12 scripts/phase17_phi1_land_climate_collect_multiconfig.py` | seed-{N}/probe.json 3개 (`_probe_multiconfig/`) |
| 6 | extractor 재실행 (normalized) — runtime DATA_ROOT swap | (collector 내부) | distribution.json + summary.md, NaN 0건 |
| 7 | extractor 재실행 (multiconfig) — runtime DATA_ROOT swap | (collector 내부) | distribution.json + summary.md, NaN 0건 |
| 8 | `[NORMALIZED]` / `[MULTICONFIG]` 라벨 grep | `grep -l "\\[NORMALIZED\\]\|\\[MULTICONFIG\\]"` 두 collector | 각 1 file matched |
| 9 | provenance 라벨 grep — summary.md (8 파일) | `grep -l "ClimateEngine normalized axis\|ClimateEngine multi-config axis"` | 8 file matched |
| 10 | DC-1B real collector / 산출 무수정 | `git diff HEAD -- scripts/phase17_phi1_land_climate_collect_real.py data/phase17_phi1_land_climate_probe_real/` | empty |
| 11 | synthetic baseline 무수정 | `git diff HEAD -- scripts/phase17_phi1_land_climate_collect.py data/phase17_phi1_land_climate_probe/` | empty |
| 12 | NovaPlanet/ClimateEngine/telemetry/extractor 본문 무수정 | `git diff HEAD -- physis/planet.py physis/climate_engine.py physis/land_climate_telemetry.py scripts/phase17_phi1_land_climate_extractor.py` | empty |
| 13 | 보호 영역 git diff | `git diff HEAD -- physis/world.py core/ ontology/ struggle/ brain/ api/ test_*.py` | empty |
| 14 | 4축 비교 표 작성 — impl.result.md §4 inline | `grep -l "synthetic.*real.*normalized.*multiconfig" results/impl.result.md` | match (16 row) |

14종 모두 PASS 시 종료. 1건이라도 실패 시 `STOP_FOR_USER` + 원인 분석 보고.

### Step 8: impl.result.md 작성

`subagent-runs/claude/phase17-phi1-land-climate-multiconfig-normalized-2026-05-07/results/impl.result.md` 작성:

- §1: 신규 author 파일 + LOC + design summary
  - §1.1: OQ 1C-5 결정 — alt config 식별 + 근거
  - §1.2: OQ 1C-6 결정 — 해석 column 분해 + 근거
- §2: 자동 생성 데이터 (probe + distribution + summary 11+11=22 파일)
- §3: 14종 자체 검증 결과 (각 PASS/FAIL + 명령 출력 발췌)
- §4: 4축 비교 분포 표 (8 metric × 2 window = 16 row, synthetic + real + normalized + multiconfig + 해석 column)
  - §4.1: 표 본문
  - §4.2: 해석 — 5배 차이의 단위 영향 / config 한정 / 자연 진화 분해 결론
- §5: §1.0 caveat 위반 0건 재확인 (분위수 freeze 0 / window freeze 30 default / mechanism 0 / LandCell 0 / climate dict 키 0 / saturation 0)
- §Uncertainty: 부수 관찰 (있으면) — multiconfig alt config 의 unintended 영향 등
- §결론: paper §7-1 evidence value 보강 평가 — 단위 영향 분리 가능 vs config-한정 vs 자연 진화 명확화

## §1.0 caveat 준수 (rev.0+ 강제)

- 분위수 임계값 freeze: 0건 (P25/P50/...는 산출 대상)
- window 길이 freeze: 30 default 유지, --ticks N 매개변수화
- mechanism 결합 수식: 0건 (driver wiring + normalize 식 only)
- LandCell 본문 변경: 0건
- climate dict 새 키 추가: 0건 (rainfall + temperature only)
- saturation cap: 0건 (§7-2 영역)
- magic threshold: 0건 (분위수 spec body 명시 금지)

## 마무리 보고 (impl.result.md 외 console)

- 신규 author 파일 LOC + mypy/ruff 결과
- 14종 self-validation 표 (PASS/FAIL)
- 4축 비교 표의 핵심 1줄 ("rainfall_30d 5배 차이의 단위 영향=X, config 한정=Y, 자연 진화=Z")
- §1.0 caveat 위반 0 재확인
- (PASS 시) "DC-1C sub-impl 1차 완료 — paper §7-1 evidence value 보강 진입 권고"
- (FAIL 시) `STOP_FOR_USER` + 실패 라인 + 원인 분석

## 자율성 정책

- writable boundary 내 자율 결정 (특히 OQ 1C-5 / 1C-6)
- writable boundary 외 변경 발견 시 즉시 보고 (자율 수정 금지)
- 14종 self-validation 1건이라도 실패 시 즉시 `STOP_FOR_USER` (자가 보정 루프 금지)
- spec rev.0+ 본문 자가 수정 금지 (rev.1 봉인은 supervisor 영역)
