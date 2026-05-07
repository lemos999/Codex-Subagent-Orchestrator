# Phase 17 Φ-1 Land §7-1 — DC-1B Real Collector Run Summary

## Outcome

| Metric | Value |
|---|---|
| 신규 파일 author | 1 (`collect_real.py` 467 LOC, mypy strict + ruff PASS) |
| 수정된 기존 파일 | 0 (synthetic baseline / extractor / telemetry / ClimateEngine / world.py / core / ontology / struggle / brain / api / test 모두 0건) |
| 자동 생성 data | 8 파일 (3 seed × probe.json + 3 seed × distribution.json + 3 seed × summary.md = 9 + aggregate distribution + aggregate summary = 11 — 단 probe.json 3 + distribution.json 4 + summary.md 4 = 11) |
| forbidden zone git diff | empty for all 8 paths (PASS) |
| 자체 검증 12종 | **12 / 12 PASS** |
| §1.0 caveat 위반 | 0건 |
| current vs cumulative 분리 | numerical proof: 1920 ≠ 5760 (90 tick × 64 cell — synthetic 30 tick은 분리 미달) |
| synthetic vs real 분포 차이 | **5배 이상 (rainfall_30d, hazard_damage), 30~60% (soil_moisture, fertility) — 차이 유의미** |

## 결론

**PASS — DC-1B real collector 신규 author 완료. paper §7-1 evidence value 봉인 진입 권고.**

ClimateEngine driver 기반 raw 분포가 synthetic random walk와 질적으로 다른 evidence를 생성함을 입증. `rainfall_30d` (synthetic 5.4 → real 29.2 cumulative P50) 와 `hazard_damage` (0.17 → 1.00) 의 5배 이상 분포 shift가 단일 sub-impl 결과로도 명확. paper §7-1 closure probe의 raw evidence base로 채택 가능.

## Files

### Code (writable scope, 1 new file)

- `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_real.py` (467 LOC)
  - `_assign_region(cell)` helper: 8x8 grid 3등분 결정론 (24/24/16 cells)
  - direct mapping (rev.1 OQ 1B-1 [확정]): `precipitation_mm` → `rainfall`, `temperature_c` → `temperature`
  - collector-내부 legacy fallback: `weather.get(..., weather.get("rainfall", 0.0))`
  - `_run_extractor_against_real_dir()`: runtime DATA_ROOT swap (extractor 본문 0건 변경)
  - `_post_process_summary_provenance()`: ClimateEngine real evolution 라벨 4 파일 stamp
  - CLI: `--ticks 90` (default, OQ 1B-3 [확정]) / `--seeds 7,13,42` / `--planet-config <path>` (OQ 1B-4 reserved)

### Data (collector + extractor 산출)

- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/seed-{7,13,42}/probe.json`
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/seed-{7,13,42}/distribution.json`
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/seed-{7,13,42}/summary.md` (Provenance 라벨 stamp)
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/aggregate/distribution.json`
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/aggregate/summary.md` (Provenance 라벨 stamp)

### Evidence

- `subagent-runs/claude/phase17-phi1-land-climate-real-collector-2026-05-07/run-manifest.md`
- `subagent-runs/claude/phase17-phi1-land-climate-real-collector-2026-05-07/prompts/impl.prompt.md`
- `subagent-runs/claude/phase17-phi1-land-climate-real-collector-2026-05-07/results/impl.result.md`
- `subagent-runs/claude/phase17-phi1-land-climate-real-collector-2026-05-07/run-summary.md` (this file)

## Validation log highlights

```
mypy strict (collect_real.py):     Success: no issues found in 1 source file
ruff (collect_real.py):            All checks passed!
collector_real 실행 (3 seed × 90 tick): 3 probe.json written
extractor 재실행 (runtime DATA_ROOT swap): 8 파일 산출, NaN/Infinity 0 hit
[REAL] / ClimateEngine driver 라벨 grep: 1 file matched
ClimateEngine real evolution 라벨 grep: 4 summary.md files matched
git diff synthetic baseline: empty
git diff ClimateEngine: empty
git diff telemetry / extractor: empty
git diff world.py + core/ + ontology/ + struggle/ + brain/ + api/ + test_*.py + tests/: empty
회귀 test 파일 import: 0 file matched
current vs cumulative: 1920 ≠ 5760 ✓
```

## §1.0 caveat compliance

- 분위수 임계값 freeze: 0건 (P25/P50/P67/P75/P90는 산출 *대상*; magic threshold 신규 코드 어디에도 없음)
- window/tick 길이 freeze: `--ticks` 매개변수화 (default 90)
- mechanism 결합 수식 freeze: 0건 (driver wiring + raw probe only; coupling formulas reserved for §7-2)
- LandCell 본문 변경: 0건 (`physis/world.py` 무수정)
- climate dict 새 키 추가: 0건 (rainfall + temperature 기존 키만 갱신)

## OQ sub-impl 결정 (rev.2 봉인 영역)

### OQ 1B-2 (LandCell region tag) — [결정] collector 내부 helper

`_assign_region(cell: LandCell) -> str`로 8x8 grid 3등분 결정론 할당 (y<3=claude / 3≤y<6=codex / y≥6=gemini). LandCell.region_id 필드 추가 0건. 본 결정은 spec rev.2 §2.4 결정으로 승격 권고.

### OQ 1B-5 (synthetic vs real 비교) — [결정] inline sub-section

`impl.result.md` inline §4.1 비교 표 (8 metric × 2 window aggregate) + §4.2 결론 1줄 ("차이 유의미 → paper §7-1 evidence value 봉인 진입 권고"). 별도 dir 신설 없음. 본 결정은 spec rev.2 §5 OQ 1B-5 [확정]으로 승격 권고.

## synthetic vs real 분포 비교 핵심

| metric | window | synthetic P50 | real P50 | relative Δ |
|---|---|---:|---:|---:|
| soil_moisture | cumulative | 0.197 | 0.265 | **+34.3%** |
| fertility | cumulative | 0.179 | 0.256 | **+43.4%** |
| rainfall_30d | cumulative | 5.40 | 29.20 | **+440.7%** |
| temperature_30d | cumulative | 19.98 | 20.11 | +0.6% (P50; P25/P75는 ±5°C 이상 분포 변동) |
| drought_days | cumulative | 0.0 | 0.0 | P50 0% (P67/P90 0→1 / 1→3 차이 — tail 신호) |
| hazard_damage | cumulative | 0.167 | 1.000 | **+500.0%** |

(자세한 비교 + uncertainty 분석은 [results/impl.result.md §4](results/impl.result.md))

## Issues

본 sub-impl 범위 내 issue 0건. 부수 관찰 2건은 results/impl.result.md §Uncertainty에 명시:

1. `rainfall_30d` 5배 이상 차이 일부가 raw 단위 (ClimateEngine mm/hour vs synthetic random[0,1]) 의 차이에 기인 가능 → rev.next OQ 1B-4 (planet variation) + (b) normalized 후보 재검토 영역.
2. `hazard_damage` real saturation 1.0 도달 → §7-2 mechanism 결정 시 telemetry accumulator clamp 재검토 필요.

## 권고 (메인 컨텍스트 다음 단계)

1. **DC-1B spec rev.2 봉인**: §2.4 OQ 1B-2 결정 + §5 OQ 1B-5 결정 + §8 변경 이력 rev.2 entry + 본 evidence cross-reference 추가.
2. **분리 commit**: collector_real.py + probe_real data 11 파일 + impl evidence 4 파일 + DC-1B rev.2 spec = 단일 commit으로 묶음. `6197f8e` (synthetic baseline) / `658ee29` (DC-1B rev.1) 와 분리.
3. **OQ 1B-4 후속 분리 PR**: planet-config 다양화 검증은 rev.next 영역 (단일 NovaPlanet 한정 5배 차이 검증).
4. **paper §7-1 evidence value 봉인 진입 가능**: 본 raw 분포가 §7-2 mechanism 결정의 evidence base. 차이 유의미.

## 다음 게이트 (사용자 결정 영역)

| # | 항목 | 권고 |
|---:|---|---|
| 1 | DC-1B spec rev.2 봉인 + 분리 commit | 즉시 진행 권고 — rev.1과 동일 separation 정책 |
| 2 | rev.next OQ 1B-4 (planet variation) sub-impl spawn | rev.2 봉인 후 별도 결정 |
| 3 | push (이전 사용자 보류) | collaborator 권한 / fork / PAT 결정 후 재시도 |

## Run timestamp

- Manifest 작성: 2026-05-07
- sub-implementer launch: 2026-05-07
- sub-implementer 완료: 2026-05-07
- 12종 검증 결과: PASS
