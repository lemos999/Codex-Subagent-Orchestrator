# Phase 17 Φ-1 Land §7-1 — DC-1B Real Collector Run Manifest

## Run metadata

- **Run name**: `phase17-phi1-land-climate-real-collector-2026-05-07`
- **Trigger**: DC-1B spec rev.1 [확정] (사용자 결정 2026-05-07) — finding 1-b 응답
- **Date**: 2026-05-07
- **Engine**: Claude (sub-implementer)
- **Model**: sonnet
- **Stage**: 단일 sub-implementer + 자체 검증 12종
- **권위 spec**: [`PHASE-17-LAND-REV-NEXT-DC-1B-CLIMATEENGINE-COLLECTOR-SPEC.md`](../../../Projects/personas/loom/PHASE-17-LAND-REV-NEXT-DC-1B-CLIMATEENGINE-COLLECTOR-SPEC.md) rev.1
- **STUB**: [`PHASE-17-LAND-REV-NEXT-STUB.md`](../../../Projects/personas/loom/PHASE-17-LAND-REV-NEXT-STUB.md) v0.3
- **선행 commit**: `658ee29` (DC-1B rev.1 cross-reference) → `6197f8e` (synthetic baseline 봉인)

## Goal

DC-1B spec rev.1 [확정] 영역 기반 ClimateEngine driver 신규 author. synthetic smoke
baseline 무수정 보존 + real driver 분리 author. paper §7-1 evidence value의 raw 기반.

## Writable boundary

| 경로 | 작업 |
|---|---|
| `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_real.py` | 신규 author (단일) |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/seed-{7,13,42}/probe.json` | 자동 생성 (collector 실행) |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/seed-{7,13,42}/distribution.json` | 자동 생성 (extractor 재실행) |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/seed-{7,13,42}/summary.md` | 자동 생성 (extractor 재실행) |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/aggregate/distribution.json` | 자동 생성 |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/aggregate/summary.md` | 자동 생성 |
| `subagent-runs/claude/phase17-phi1-land-climate-real-collector-2026-05-07/results/impl.result.md` | 작성 |

## Forbidden zone (영원 무수정)

| 경로 | 사유 |
|---|---|
| `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect.py` | synthetic baseline 봉인 (commit `6197f8e`) |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe/` | synthetic 산출 봉인 |
| `Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py` | 인터페이스 호환 강제 (재사용만) |
| `Projects/personas/loom/physis/land_climate_telemetry.py` | observer 무수정 (DC-1 §7-1 spec) |
| `Projects/personas/loom/physis/climate_engine.py` | driver는 public `tick()` 호출만 |
| `Projects/personas/loom/physis/world.py` | LandCell 본문 무수정 (climate dict 키 추가 0건) |
| `Projects/personas/loom/core/` `ontology/` `struggle/` `brain/` `api/` | 단방향 계약 |
| `test_*.py` | acceptance 변경 0건 invariant |

## Validation (sub-implementer 자체 검증 의무 — 12종)

DC-1B spec rev.1 §3.3 검증 표를 그대로 수행. 12종 모두 PASS 시 sub-impl 종료.

## rev.1 [확정] 결정 사항 (sub-impl 진입 시 적용)

- **OQ 1B-1 [확정]**: direct mapping
  - `cell.climate["rainfall"]    = weather["precipitation_mm"]`
  - `cell.climate["temperature"] = weather["temperature_c"]`
  - legacy fallback은 collector 내부에 한정
- **OQ 1B-3 [확정]**: `--ticks` default = 90 (current/cumulative 분리 검증 기본값)

## sub-impl 진입 시 검증 영역 (rev.2 결정 보류)

- **OQ 1B-2**: LandCell region tag 부재 → collector 내부 8x8 grid 3등분 결정론적 할당
  (LandCell.region_id 필드 추가 0건; `physis/world.py` 본문 무수정)
- **OQ 1B-5**: synthetic vs real 분포 비교 보고서 위치 — `impl.result.md` inline 권고

## Evidence required

- `prompts/impl.prompt.md` — sub-implementer 본 prompt
- `results/impl.result.md` — 변경 파일 목록 + 검증 명령 결과 표 (12종) + synthetic vs real 분포 비교

## Run timestamp

- Manifest 작성: 2026-05-07
- sub-implementer launch: in progress
- 완료: TBD
