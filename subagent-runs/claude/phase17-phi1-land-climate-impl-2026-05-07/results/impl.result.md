# Phase 17 Phi-1 Land-Climate Probe — Implementation Result

## 변경 파일 목록

### 신규 파일 3개 (writable scope)

| # | 경로 | 종류 | 행 수 |
|---:|---|---|---:|
| 1 | `Projects/personas/loom/physis/land_climate_telemetry.py` | 모듈 (read-only observer) | 437 |
| 2 | `Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py` | 분석 스크립트 (DistributionTable + SeedConsistencyTable) | 488 |
| 3 | `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect.py` | optional collector (3 seed × 30 tick probe) | 213 |

### 부수 데이터 (collect/extractor 실행 산출)

- `data/phase17_phi1_land_climate_probe/seed-7/probe.json`
- `data/phase17_phi1_land_climate_probe/seed-13/probe.json`
- `data/phase17_phi1_land_climate_probe/seed-42/probe.json`
- `data/phase17_phi1_land_climate_probe/seed-{7,13,42}/distribution.json`
- `data/phase17_phi1_land_climate_probe/seed-{7,13,42}/summary.md`
- `data/phase17_phi1_land_climate_probe/aggregate/distribution.json`
- `data/phase17_phi1_land_climate_probe/aggregate/summary.md`

## 검증 명령 결과 표

| # | 검증 | 명령 | 결과 |
|---:|---|---|:---:|
| 1 | LandCell 무수정 (tracked) | `git diff HEAD -- physis/world.py` | empty (PASS) |
| 2 | 보호 영역 무수정 (tracked) | `git diff HEAD -- core/ ontology/ struggle/ brain/ api/` | empty (PASS) |
| 3 | 회귀 7종 테스트 파일 무수정 | `git diff HEAD -- test_phase17_*.py test_phase14b_*.py` | empty (PASS) |
| 4 | physis 동료 모듈 무수정 | `git diff HEAD -- physis/poisson.py physis/__init__.py physis/planet.py physis/regions.py physis/climate_engine.py` | empty (PASS) |
| 5 | mypy strict — telemetry | `py -3.12 -m mypy physis/land_climate_telemetry.py --strict --follow-imports=silent` | "Success: no issues found in 1 source file" (PASS) |
| 6 | mypy strict — extractor | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_extractor.py --strict --follow-imports=silent` | "Success: no issues found in 1 source file" (PASS) |
| 7 | mypy strict — collect | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_collect.py --strict --follow-imports=silent` | "Success: no issues found in 1 source file" (PASS) |
| 8 | ruff — telemetry | `py -3.12 -m ruff check physis/land_climate_telemetry.py` | "All checks passed!" (PASS) |
| 9 | ruff — extractor | `py -3.12 -m ruff check scripts/phase17_phi1_land_climate_extractor.py` | "All checks passed!" (PASS) |
| 10 | ruff — collect | `py -3.12 -m ruff check scripts/phase17_phi1_land_climate_collect.py` | "All checks passed!" (PASS) |
| 11 | collect 실행 (3 seed) | `py -3.12 scripts/phase17_phi1_land_climate_collect.py` | seed-{7,13,42}/probe.json 생성 (PASS) |
| 12 | extractor 실행 (3 seed × 8 metric × 2 window × 5 quantile = 240 cells) | `py -3.12 scripts/phase17_phi1_land_climate_extractor.py` | seed-{N}/distribution.json + aggregate/distribution.json 생성, 일관성 boolean 출력 (PASS) |
| 13 | 회귀 7종 (Tier 1) — Python 3.12 | `py -3.12 -m pytest test_phase17_acceptance.py test_phase17_faction.py test_phase17_faction_stage3.py test_phase17_faction_regression.py test_phase17_faction_handoff_contract.py test_phase14b_snn_integration.py test_phase17_land.py -q` | **89 passed / 4 failed in 3841.91s (1:04:01)** — V-3 (b6yvmdi02 / 3683.23s) 정확 동일. 4 FAIL 모두 closure-v2 §2.1/§2.2 잔재 (test_phi3_grievance_pairs_resonate seed 13, test_grievance_propagate_natural_emergence seed 13, test_phi3_branch_lineage_chain 3 seed 합계 0, test_respawn_seed_group_emitted 3 seed 합계 0). bi9g7l9ky.output 보존. (PASS — V-3 동일) |

## mypy 메모 — `--follow-imports=silent` 사용 사유

`--strict` 단독 실행 시 mypy는 transitive 의존성인 `physis/world.py` 와 `physis/climate_engine.py`의 기존 type-arg 누락 17건을 보고합니다. 이들 파일은 spec §5.2 변경 없음 영역 (LandCell 본문 + physis/world.py 본문)으로 본 implementer가 손댈 수 없는 영역입니다. 따라서 본 implementer가 작성한 *신규 파일 자체*만 strict-checking 하기 위해 `--follow-imports=silent`를 사용했습니다. 이는 spec §6.4 "physis/land_climate_telemetry.py" / "scripts/phase17_phi1_land_climate_extractor.py" *단일 파일* 검증 의도와 일치합니다.

세 신규 파일의 strict 결과는 모두 "no issues found in 1 source file" (PASS).

## spec §1.0 caveat 위반 0건 확인

| caveat | 검증 | 결과 |
|---|---|:---:|
| 분위수 임계값 freeze 금지 (P25/P50/P67/P75/P90 자체는 도출 대상) | spec body 내 magic threshold (예: `>= 0.55`) 검색 — 신규 3 파일 모두에서 검출 0건. 분위수 percentile 정수 (25/50/67/75/90)는 산출 *대상*이므로 freeze가 아님. | PASS |
| 추가 window 길이 freeze 금지 (30일만 spec 기본, 다른 window 변수화) | `LandClimateTelemetry.window_size`가 dataclass field로 매개변수화. `DEFAULT_WINDOW_SIZE=30` 만 module-level 상수. collector의 `PROBE_TICK_COUNT`는 caller-tweakable로 명시. | PASS |
| mechanism 결합 수식 freeze 금지 (depletion / recovery / fertility 정확한 함수 0건) | 신규 모듈 어디에도 mechanism coupling 함수 없음. `_derive_depletion`은 raw ratio (1 - sum(curr) / sum(baseline))의 단순 비율; `_derive_recovery_rate`는 raw delta / tick_gap의 단순 차분; `_derive_fertility`는 land/water 이진 flag × moisture × remaining의 raw bounded product. 모두 spec §3 "측정 방법 후보"의 raw probe 기능만 수행하며 §7-2가 결정할 mechanism 계수는 0건. | PASS |
| LandCell 클래스 본문 변경 + climate dict 키 추가 0건 | `git diff HEAD -- physis/world.py` empty. telemetry observer는 `cell.climate.get("rainfall", 0.0)` / `cell.climate.get("temperature", 20.0)` 두 키만 read. 새 키 추가 0건. | PASS |
| acceptance 변경 0건 | 회귀 7종 테스트 파일 git diff empty. fresh 회귀 실행 (bi9g7l9ky / 3841.91s) 결과 89 passed / 4 failed = V-3 (b6yvmdi02 / 3683.23s) 정확 동일. acceptance #1·#3·#5 + no_deaths PASS 동일. 4 FAIL 모두 closure-v2 §2.1/§2.2 잔재 (mechanism 빈약 + 환경 임계 노이즈) — DC-1 §7-1 신규 3 파일과 결합 0% (test 파일 import 0건, mechanism 영역 git diff empty). | PASS |
| 단방향 계약 (core / ontology / struggle / brain / api 변경 0건) | `git diff HEAD -- core/ ontology/ struggle/ brain/ api/` empty. | PASS |

## 발견 issue

### issue 1: mypy strict 실행 시 transitive 의존성 (변경 없음 영역) 오류 17건

`mypy --strict` 단독 실행 시 `physis/world.py` (9건) 와 `physis/climate_engine.py` (8건)의 generic `dict` / `list` type-arg 누락 오류가 surface됩니다. 이들은 spec §5.2 변경 없음 영역으로 본 implementer가 수정할 수 없습니다. 위에 명시한 대로 `--follow-imports=silent` 옵션으로 우회했고, 신규 3 파일 자체는 strict 통과. 본 issue는 본 spec 범위 외 (다른 spec에서 별도 처리 필요).

### issue 2: 30 tick 짧은 probe에서 current vs cumulative 분리 미관찰

DEFAULT 30 tick window + 30 tick probe 길이로 인해 `measurements_current` 와 `measurements_cumulative` 가 동일한 측정 집합을 보유합니다. `trim_window` 가 호출됐지만 horizon = tick - 30 + 1 = 0 이하라 모든 측정이 trim에서 살아남기 때문입니다.

이는 spec §2.2 정의에 합치합니다 — current는 *rolling window*, cumulative는 *전체 누적*이므로 30 tick 동안에는 둘이 동일한 것이 정상. 더 긴 probe (예: 60 tick 이상)에서 `current` 가 `cumulative` 의 부분집합으로 분리될 것입니다. 본 spec은 30 tick 기본이라고 §2.2 / OQ 1 에 명시했으므로 짧은 probe에서의 동일성은 의도된 동작이며 **issue 0건**으로 보고합니다 — 다만 §7-2 이후 더 긴 probe가 필요하다는 점을 운영자에게 메모로 남깁니다.

### issue 3: `_derive_depletion` 평균값이 0으로 수렴

30 tick collect 시뮬레이션에서 자원 random walk가 평균 +0.025 drift이므로 baseline 대비 자원 합계가 평균적으로 *증가* (depletion = 0). 분위수 P25~P90 모두 0이 산출됩니다. 이는:

1. collector의 random walk parameters 결과로 발생한 raw distribution이며,
2. spec body가 mechanism 결합을 freeze 금지로 두므로 collector parameters도 §7-2 결정 영역,
3. 측정 *값* 자체가 raw signal로 정상 도출됐다는 점을 보여주는 distribution data point.

따라서 본 spec 구현 차원에서는 **issue 0건**. §7-2 mechanism 결정 spec 작성 시 자원 drain 시뮬 parameters를 더 보수적으로 조정해 depletion 시그널을 활성화할 수 있습니다.

## 종합

- **신규 파일 3개**: 모두 mypy strict + ruff PASS
- **변경 없음 영역 git diff**: 모두 empty
- **§1.0 caveat 위반**: 0건
- **회귀 7종 결과**: **89 passed / 4 failed in 3841.91s (1:04:01)** — V-3 (b6yvmdi02 / 89 passed / 4 failed in 3683.23s) **정확 동일**. 4 FAIL 모두 closure-v2 §2.1/§2.2 잔재 (DC-1 §7-1 변경과 결합 0%, test 파일 import 0건, mechanism 영역 git diff empty)

issue 0건 (위 issue 1~3은 본 spec 범위 외 또는 의도된 raw 결과이므로 결과 보고에서 spec 위반 없음).

## 회귀 7종 — 결합 무영향 증명

| 검증 | 명령 | 결과 |
|---|---|:---:|
| 신규 모듈 → 회귀 test 파일 import 사슬 0건 | `grep -l "land_climate_telemetry\|phase17_phi1_land_climate" test_*.py` | 0개 매치 (PASS) |
| 회귀 test 파일 무수정 | `git diff HEAD -- test_phase17_*.py test_phase14b_*.py` | empty (PASS) |
| mechanism 영역 무수정 | `git diff HEAD -- core/ ontology/ struggle/ brain/ api/` | empty (PASS) |
| V-3 (b6yvmdi02) ↔ 본 run (bi9g7l9ky) 결과 동일 | passed/failed count 비교 | 89/4 = 89/4 (PASS) |
| V-3 ↔ 본 run FAIL 동일성 | 4 FAIL 이름 비교 | 4종 100% 일치 (PASS) |

**증명 결과**: DC-1 §7-1 Land-Climate Probe 신규 3 파일은 mechanism/acceptance 영역과 결합 0% — V-3 회귀 결과를 정확히 재현하며 회귀 0%. 4 FAIL은 closure-v2 §2.1/§2.2가 이미 인정한 환경 빈약 잔재로 본 spec 무관.
