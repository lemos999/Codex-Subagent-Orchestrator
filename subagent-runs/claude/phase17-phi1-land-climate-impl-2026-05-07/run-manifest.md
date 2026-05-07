# Phase 17 Phi-1 Land rev.next §7-1 Land-Climate Closure Probe — Implementation Run Manifest

## 작업 메타

- **일자**: 2026-05-07
- **워커**: Claude Sub Implementer (단일 leaf)
- **권위 spec**: `Projects/personas/loom/PHASE-17-LAND-REV-NEXT-DC-1-LAND-CLIMATE-PROBE-SPEC.md` rev.0 [확정]
- **작업 유형**: 신규 파일 author (telemetry observer 모듈 + extractor 스크립트 + optional collector)
- **DB migration**: 없음
- **외부 의존**: 없음 (numpy 기존 환경)

## 산출 (writable scope)

신규 파일 3개:
1. `Projects/personas/loom/physis/land_climate_telemetry.py` (필수)
2. `Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py` (필수)
3. `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect.py` (optional)

부수적 데이터 산출:
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe/seed-{7,13,42}/probe.json`
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe/seed-{7,13,42}/distribution.json`
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe/seed-{7,13,42}/summary.md`
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe/aggregate/distribution.json`
- `Projects/personas/loom/data/phase17_phi1_land_climate_probe/aggregate/summary.md`

## 변경 없음 영역 (spec §5.2)

- `Projects/personas/loom/physis/world.py` (LandCell 본문 무수정)
- `Projects/personas/loom/physis/poisson.py`
- `Projects/personas/loom/physis/planet.py`
- `Projects/personas/loom/physis/regions.py`
- `Projects/personas/loom/physis/climate_engine.py`
- `Projects/personas/loom/physis/__init__.py`
- `Projects/personas/loom/core/`
- `Projects/personas/loom/ontology/`
- `Projects/personas/loom/struggle/`
- `Projects/personas/loom/api/`
- `Projects/personas/loom/brain/`
- `Projects/personas/loom/test_*.py` (회귀 7종 + acceptance + 기타)

## 보존 invariant 7종 (spec §0.3)

| Invariant | 보존 |
|---|---|
| 무파괴 9 (Phase 11~16 mechanism) | ✓ — physis/world.py 무수정, mechanism 결합 0건 |
| 안전 전제 5종 | ✓ — 변경 없음 |
| BOOST=0.20 | ✓ — 변경 없음 |
| 회귀 7종 (Tier 1) | 실행 중 (background, 약 1시간) |
| acceptance 4종 | 회귀 7종에 포함 검증 |
| brain·SNN API 무수정 | ✓ — brain/ 변경 0건 |
| DC-1 SIS / DC-2 CPCM rev.3 / DC-3 P5R rev.2 봉인 | ✓ — 본문 변경 0건 |

## §1.0 caveat 위반 0건 확인

- 분위수 임계값 magic number: 0건 (spec body 어디에도 P25/P50/P67/P75/P90 외 magic threshold 없음)
- 추가 window 길이 freeze: window_size는 매개변수화, DEFAULT=30
- mechanism 결합 수식 freeze: 0건 (raw 측정만; coupling 함수는 §7-2 위임)
