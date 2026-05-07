Phase 17 Φ-1 Land rev.next §7-1 Land-Climate Closure Probe 구현.

# Spec (그대로 따를 것 — rev.0 [확정] 2026-05-07)

`Projects/personas/loom/PHASE-17-LAND-REV-NEXT-DC-1-LAND-CLIMATE-PROBE-SPEC.md`

먼저 이 spec 전문 Read. 특히:
- §0.3 보존 invariant 7종
- §1.3 [필수]/[선택]/[금지]
- §2.2 LandClimateMeasurement + LandClimateTelemetry 시그니처
- §2.3 extractor DistributionTable + SeedConsistencyTable 시그니처
- §3 측정 대상 8 후보 필드 (FREEZE 금지 영역 명시)
- §4 모듈 구조
- §5 변경 영역 + 무수정 영역
- §6 검증

또한 기존 코드베이스 컨텍스트:
- `Projects/personas/loom/physis/world.py:23` LandCell 정의 (변경 0건 — read-only observer 패턴)
- `Projects/personas/loom/PHASE-17-NATION-DC-1-SIS-SPEC.md` extractor 시그니처 참조 (windowed distribution table 형태)

# 작업 — 신규 파일 3개 author

1. **`Projects/personas/loom/physis/land_climate_telemetry.py`** (필수)
   - `LandClimateMeasurement` dataclass — 8 후보 필드 (soil_moisture / fertility / rainfall_30d / temperature_30d / drought_days / depletion / recovery_rate / hazard_damage)
   - `LandClimateTelemetry` dataclass — read-only observer + measurements_current (rolling 30일) + measurements_cumulative (전체 누적)
   - `observe(tick, world)` — LandCell 읽기만, LandCell 변경 0건
   - `trim_window(tick)` — current bucket window_size 초과 측정 제거

2. **`Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py`** (필수)
   - LandClimateTelemetry → DistributionTable (3 seed × 8 metric × 2 window × P25/P50/P67/P75/P90)
   - SeedConsistencyTable (P50/P67/P75 × 8 metric × 2 window 일관성 boolean ±10%)
   - DC-1 SIS extractor와 동일 인터페이스 형태 (`PHASE-17-NATION-DC-1-SIS-SPEC.md` 참조)
   - 출력 → JSON 파일 (data/phase17_phi1_land_climate_probe/)

3. **`Projects/personas/loom/scripts/phase17_phi1_land_climate_collect.py`** (optional)
   - 30일 probe 데이터 수집 (3 seed: 7/13/42)
   - core 변경 0건 — 외부 hook 또는 시뮬 실행 wrapper로 호출

# 절대 준수 (위반 시 거부)

- **§0.1 단방향 계약**: `core/` `ontology/` `struggle/` `brain/` `api/` 변경 0건
- **§0.2 §1.0 caveat**: type signature freeze, body freeze 금지 (§3 표 우측 ❌ 컬럼)
  - 분위수 임계값 freeze 금지 → spec body 내 magic number 0건
  - 추가 window 길이 freeze 금지 → 30일만 명시, 다른 window 변수화
  - mechanism 결합 수식 (depletion / recovery / fertility 정확한 함수) 0건 — 측정 대상으로만 정의
- **§1.3 [금지]**: LandCell 클래스 본문 변경 + climate dict 키 추가 + mechanism 결합 + acceptance 변경 등 모두 0건
- **§5.2 변경 없음 영역**: physis/world.py 본문 + core/ + ontology/ + struggle/ + api/ + brain/ + test_*.py 모두 변경 0건

# 검증 명령 (구현 후 모두 실행)

```bash
cd Projects/personas/loom

# (1) LandCell 무수정 3중
git diff HEAD -- physis/world.py                                      # 기대: empty
git diff HEAD -- core/ ontology/ struggle/ brain/ api/                # 기대: empty

# (2) 회귀 7종 (Tier 1)
py -m pytest test_phase17_acceptance.py test_phase17_faction.py test_phase17_faction_stage3.py test_phase17_faction_regression.py test_phase17_faction_handoff_contract.py test_phase14b_snn_integration.py test_phase17_land.py -q
# 기대: 89 passed / 4 failed (V-3 2026-05-07 동일 — closure-v2 §2.1/§2.2 잔재). 새 FAIL 발생 시 거부.

# (3) mypy + ruff
py -m mypy physis/land_climate_telemetry.py --strict
py -m ruff check physis/land_climate_telemetry.py
py -m mypy scripts/phase17_phi1_land_climate_extractor.py --strict
py -m ruff check scripts/phase17_phi1_land_climate_extractor.py
```

회귀 7종 실행이 1시간 이상 (V-3 1:01:23) 걸리므로 background 실행 후 폴링 가능. 그 외 검증은 즉시 실행.

# Evidence (필수)

`subagent-runs/claude/phase17-phi1-land-climate-impl-2026-05-07/`
- `run-manifest.md` — 작업 메타
- `run-summary.md` — 결과 요약
- `prompts/impl.prompt.md` — 본 prompt 그대로 보존
- `results/impl.result.md` — 변경 파일 목록 + 검증 명령 결과 표 + 발견 issue (있으면)

# 보고 형식

작업 완료 후 사용자 보고용 요약 (200 단어 이내):
1. 변경 파일 목록 (3개 신규)
2. 검증 명령 결과 표 (LandCell 무수정 / 회귀 7종 / mypy / ruff)
3. spec §1.0 caveat 위반 0건 확인
4. 발견 issue (있으면) 또는 "issue 0건"

회귀 7종이 1시간 걸리므로 background 실행 + 폴링 + 결과 도착까지 다른 검증 먼저 진행 권장.
