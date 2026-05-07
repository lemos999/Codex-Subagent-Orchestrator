# DC-1C multi-config + normalized sub-implementer 1차 — Run Manifest

## 메타

| 항목 | 값 |
|---|---|
| 작업 spec | `Projects/personas/loom/PHASE-17-LAND-REV-NEXT-DC-1C-MULTICONFIG-NORMALIZED-PROBE-SPEC.md` (rev.0+ 봉인) |
| 차수 | 1차 (sub-implementer 초회) |
| 모드 | spec rev.0+ 직접 따라 신규 author (DC-1B 동형 패턴) |
| 동시성 | 단일 sub-implementer (sonnet, ~30분 추정) |
| Supervisor | Claude (sonnet) — 본 메인 컨텍스트 |
| 워커 | sub-implementer (sonnet) |
| Watchdog | 없음 (1차 자동 진행) |
| 진입 시각 | 2026-05-07 |

## 선행 봉인

- DC-1 §7-1 SPEC rev.0 — commit `6197f8e` (synthetic baseline 봉인)
- DC-1B SPEC rev.2 + collector_real.py + `_probe_real/` data — commit `82ac1d3` (real collector 봉인)
- DC-1C SPEC rev.0+ — spec-review 1차 [승인] (CRITICAL 0 / MAJOR 0 / MINOR 2 보강 / TRIVIA 1)
  - evidence: `subagent-runs/claude/phase17-dc1c-spec-review-1차-2026-05-07/`

## 작업 범위 (writable boundary)

### 신규 파일 (2종)

- `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_normalized.py` — normalized axis collector
- `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_multiconfig.py` — alt planet config axis collector

### 자동 생성 데이터 (extractor runtime DATA_ROOT swap)

- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_normalized/seed-{7,13,42}/{probe,distribution,summary}.{json,md}`
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_normalized/aggregate/{distribution,summary}.{json,md}`
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_multiconfig/seed-{7,13,42}/{probe,distribution,summary}.{json,md}`
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe_multiconfig/aggregate/{distribution,summary}.{json,md}`

### Evidence

- `subagent-runs/claude/phase17-phi1-land-climate-multiconfig-normalized-2026-05-07/run-manifest.md` (this file)
- `subagent-runs/claude/phase17-phi1-land-climate-multiconfig-normalized-2026-05-07/prompts/impl.prompt.md`
- `subagent-runs/claude/phase17-phi1-land-climate-multiconfig-normalized-2026-05-07/results/impl.result.md` (sub-impl 작성 — 4축 비교 §4 inline 포함)
- `subagent-runs/claude/phase17-phi1-land-climate-multiconfig-normalized-2026-05-07/run-summary.md` (supervisor 작성 — 사용자 보고 후)

## 금지 영역 (writable boundary 외, git diff empty 강제)

- `scripts/phase17_phi1_land_climate_collect.py` (synthetic baseline 봉인)
- `scripts/phase17_phi1_land_climate_collect_real.py` (DC-1B real collector 봉인)
- `data/phase17_phi1_land_climate_probe/` (synthetic 산출 봉인)
- `data/phase17_phi1_land_climate_probe_real/` (DC-1B real 산출 봉인)
- `scripts/phase17_phi1_land_climate_extractor.py` (인터페이스 호환 강제 — runtime DATA_ROOT swap만)
- `physis/land_climate_telemetry.py` (observer 무수정)
- `physis/climate_engine.py` (driver는 public `tick()` 호출만)
- `physis/planet.py` (NovaPlanet은 인스턴스 파라미터만 변경; 본문 무수정)
- `physis/world.py` (LandCell 본문 무수정 + climate dict 키 추가 0)
- `core/` `ontology/` `struggle/` `brain/` `api/` `test_*.py` (단방향 계약)

## OQ 1C-5 / 1C-6 — sub-impl 결정 영역 (rev.0+ 봉인 명시)

### OQ 1C-5: alt planet config 식별 (이름 + 파라미터)

NovaPlanet `@dataclass(frozen=True)` invariant 유지 + 한 가지 의미 있는 변동.
권고 후보 (sub-impl 자율 결정):
- `axial_tilt_deg=15.0` (default 25.0 → 더 작은 자전축 기울기, 계절성 약화)
- `sea_level_temp_c=10.0` (default 16.0 → 더 한랭 기후)
- `eccentricity=0.05` (default 0.02 → 타원 궤도 강조)
- `solar_constant=1200.0` (default 1361.0 → 약한 일사)

선택 + 명명 + 근거를 `impl.result.md` §1.1에 명시 의무.

### OQ 1C-6: 4축 비교 표 해석 column

권고 (rev.0+ §5):
- 단위 영향 = `real - normalized` (P50 기준)
- config 한정 = `real - multiconfig` (P50 기준, default config baseline)
- 자연 진화 = `min(normalized, multiconfig)` 또는 다른 합리적 분해

선택 + 근거를 `impl.result.md` §4 표 위에 명시 의무.

## self-validation 14종 (sub-implementer 보고 의무)

spec rev.0+ §3.3 14 row 표 그대로. 14종 모두 PASS 시 sub-implementer 종료, 실패 시 `STOP_FOR_USER` + 원인 분석.

## Run timestamp

- Manifest 작성: 2026-05-07
- sub-implementer launch: 2026-05-07 (즉시)
- 사용자 결정: DC-1C sub-implementer spawn 즉시 진행 — 권고 #1 채택
