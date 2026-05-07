# Phase 17 Φ-1 Land §7-1 Probe — Hotfix Run Manifest

## Run metadata

- **Run name**: `phase17-phi1-land-climate-hotfix-2026-05-07`
- **Trigger**: 사용자 검토 finding 4종 보강 (Finding 1-a SMOKE 라벨 + Finding 2 `--ticks` + Finding 3 strict NaN + Finding 4 wrapper memo)
- **Date**: 2026-05-07
- **Engine**: Claude (sub-implementer)
- **Model**: sonnet
- **Stage**: 단일 sub-implementer + 자체 검증
- **Source spec**: `Projects/personas/loom/PHASE-17-LAND-REV-NEXT-DC-1-LAND-CLIMATE-PROBE-SPEC.md` rev.0
- **Source review**: 본 conversation 사용자 finding 4종 (2026-05-07)

## Goal

§7-1 Probe 산출물 evidence 안정성 보강:

1. **Finding 1-a (Major)** — collector `synthetic smoke` 명시 (header docstring + summary.md 라벨)
2. **Finding 2 (Medium)** — collector `--ticks N` argparse (raw window extension, freeze 아님)
3. **Finding 3 (Medium)** — extractor `allow_nan=False` + empty input `ValueError` (DC-2 hotfix 사례 동형)
4. **Finding 4 (Minor)** — STUB v0.1 §10 (또는 §11 변경 이력)에 v1 wrapper future-work 메모

**범위 외 (Finding 1-b)**: 실제 `ClimateEngine` 기반 collector 신규 author는 별도 PR로 분리 (사용자 승인 게이트 후 진행).

## Writable boundary

| 경로 | 작업 |
|---|---|
| `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect.py` | 수정 (header docstring + argparse) |
| `Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py` | 수정 (allow_nan=False + empty ValueError) |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe/aggregate/summary.md` | 수정 (SMOKE 명시 + Finding 1-a 라벨) |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe/seed-{7,13,42}/summary.md` | 수정 (SMOKE 라벨) |
| `Projects/personas/loom/PHASE-17-LAND-REV-NEXT-STUB.md` | 수정 (§10 또는 §11에 v1 wrapper future-work 메모 추가) |
| `subagent-runs/claude/phase17-phi1-land-climate-hotfix-2026-05-07/results/impl.result.md` | 작성 |

## Forbidden zone

| 경로 | 사유 |
|---|---|
| `Projects/personas/loom/physis/` | spec rev.0 §5 "신규 파일 외 모두 무수정" |
| `Projects/personas/loom/physis/land_climate_telemetry.py` | spec rev.0 본문 동결 (FREEZE 영역 아니지만 본 hotfix 범위 외) |
| `Projects/personas/loom/core/` `ontology/` `struggle/` `brain/` `api/` | 단방향 계약 |
| `Projects/personas/loom/test_*.py` | acceptance 변경 0건 invariant |
| 기존 산출 JSON (`probe.json` / `distribution.json`) | re-extract 시 자동 재기록 OK, 수동 편집 X |

## Validation

sub-implementer 자체 검증 (보고 의무):

1. `py -3.12 -m mypy --strict --follow-imports=silent` — 신규 modify 2 파일 PASS
2. `py -3.12 -m ruff check` — 신규 modify 2 파일 PASS
3. extractor 재실행 — `--allow-nan=False` strict JSON 산출 (기존 산출과 동일 raw 값 + RFC 호환성 검증)
4. extractor empty input 시 `ValueError` raise 단위 테스트 (1 line `python -c` 검증)
5. collector `--ticks 60` 옵션 dry-run (실제 60 tick 수집 fast path)
6. collector header + summary.md SMOKE 라벨 grep 검증
7. STUB v0.1 → v0.2 변경 이력 entry 확인

## Evidence required

- `prompts/impl.prompt.md` — 본 hotfix prompt
- `results/impl.result.md` — 변경 파일 목록 + 검증 명령 결과 표 + finding 4종 매핑

## Run timestamp

- Manifest 작성: 2026-05-07
- sub-implementer launch: (in progress)
- 완료: TBD
