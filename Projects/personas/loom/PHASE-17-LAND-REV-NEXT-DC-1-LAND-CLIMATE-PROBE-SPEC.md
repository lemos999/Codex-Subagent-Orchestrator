# [기능·분석 스크립트] DC-1 Land-Climate Closure Probe — Φ-1 Land rev.next §7-1

> **긴급도**: 중간 (Φ-1 rev.next 첫 단계 — paper 진로 B 진입)
> **선행 조건**:
> - PHASE3 closure 봉인 성립 (DC-1 SIS / DC-2 CPCM rev.3 / DC-3 P5R rev.2 [확정])
> - STUB v0.1 검토 완료 (2026-05-07, OQ 1~6 결정 통합)
> **작업 유형**: 기능 (telemetry observer 신규) + 분석 스크립트
> **DB migration**: 없음
> **외부 의존**: 없음 (numpy, dataclasses 기존)
> **권위 문서**: STUB v0.1 = `PHASE-17-LAND-REV-NEXT-STUB.md` §3, §4, §6, §7
> **paper 정합**: paper(2026-05-07) §7-1 / §5.2 / §8 전 항목

---

## §0. 권위 / 단방향 계약 / 보존 invariant

### 0.1 단방향 계약 (Φ-5 ← Φ-4 ← Φ-3 ← Φ-2 ← **Φ-1**)

본 spec은 Φ-1 Land 영역 **read-only telemetry**. 다음 영역에 **변경 0건**:

- Φ-2 Faction (faction.py)
- Φ-3 Struggle (struggle/faction_*.py + uprising 본문)
- Φ-4 Nation (Φ-3 closure 봉인 본문)
- Φ-5 read-only API (`api/__init__.py`, `api/nation_p5r.py`)
- brain·SNN (Phase 14B-d / PersonaBrain)
- core (`core/multi_tick_engine.py`)
- ontology (Phase 11-16 무파괴)

### 0.2 §1.0 body 고정 금지 caveat

본 spec은 **type signature + 측정 대상 + extractor 인터페이스**만 freeze. 다음은 freeze **금지**:

- 8 후보 필드의 임계 분위수 (P25/P50/P67/P75/P90 자체는 도출 대상)
- 추가 window 길이 (30일 기본만 freeze, 다른 window는 raw 분석 후 결정)
- mechanism 결합 후보 (§7-2 이후 단계 결정 영역)
- recovery/depletion 수식 (telemetry 단계에서는 측정만)

### 0.3 보존 invariant 7종 (STUB v0.1 §7)

다음을 **반드시 보존**:

- **무파괴 9** — Phase 11~16 mechanism 무영향
- **안전 전제 5종**: HYSTERESIS=2, FOUNDER_RESPAWN_EVERY=480, TARGET_ACTIVE=2, COMMIT_EVERY=48, MAX_MEMBERS=2
- **BOOST=0.20**
- **회귀 7종 (Tier 1)** — `PHASE-17-NATION-PHASE3-REGRESSION-CONTRACT.md` rev.2 권위
- **acceptance 4종** — uprising / grievance / dom_share / no_deaths
- **brain·SNN API 무수정**
- **DC-1 SIS / DC-2 CPCM rev.3 / DC-3 P5R rev.2** 본문 [확정] 봉인

---

## §1. 목적 + 범위

### 1.1 paper §7-1 인용 (line 274-277)

> 1. **Land-Climate Closure Probe**
>    - regional weather를 cell state로 투영
>    - tile별 rolling climate state 측정
>    - **raw telemetry만 생성**

### 1.2 본 spec 범위

| 항목 | 본 spec | §7-2 이후 |
|---|:---:|:---:|
| LandCell read 측정 | ○ | - |
| 30일 rolling window 누적 | ○ | - |
| extractor (P25/P50/P67/P75/P90 분위수) | ○ | - |
| 3 seed (7/13/42) 일관성 자동 판정 | ○ | - |
| current-window vs cumulative 분리 | ○ | - |
| **mechanism 결합 (resource depletion 수식 등)** | **금지** | §7-2 별도 spec |
| **LandCell 본문 변경** | **금지** | §7-2 별도 spec + 사용자 사전 승인 |
| **acceptance 변경** | **금지** | 영원 |

### 1.3 [필수] / [선택] / [금지]

#### [필수]
1. 신규 모듈 `physis/land_climate_telemetry.py` author (read-only observer)
2. paper §5.2 8 후보 필드 측정 (telemetry 모듈 내 별도 객체)
3. 30일 rolling window + cumulative 누적 분리 (paper §8)
4. extractor 신규 스크립트 (DC-1 SIS 동일 인터페이스)
5. LandCell 본문 무수정 3중 검증 (OQ 3)
6. 회귀 7종 (Tier 1) 동일 결과 (89 passed)
7. acceptance 4종 (#1·#3·#5 + no_deaths) PASS 동일

#### [선택]
- 추가 window 길이 (예: 90일, 365일) — raw 분석 후 결정
- 추가 측정 시그널 (paper §5.2 외) — STUB rev.next §6 OQ 7+ 추가 후 결정

#### [금지]
- LandCell 클래스 본문 변경 (필드 추가 / 삭제 / 시그니처 변경)
- climate dict 키 추가 (현재: rainfall, temperature)
- mechanism 결합 (depletion / recovery 수식)
- magic threshold freeze (분위수 임계값 spec body 명시)
- core/ ontology/ struggle/ Φ-2 / Φ-3 / Φ-4 / Φ-5 영역 변경
- brain·SNN API 변경
- acceptance 변경
- 기존 회귀 7종 변경

---

## §2. 입력 + 출력 시그니처

### 2.1 입력 — LandCell read-only

본 spec은 [physis/world.py:23](Projects/personas/loom/physis/world.py#L23) `LandCell` 데이터클래스의 **읽기 전용 관찰**:

```python
# physis/world.py:23 (변경 금지 — 본 spec은 이 시그니처를 read-only로 관찰)
@dataclass(slots=True)
class LandCell:
    x: int
    y: int
    biome: str
    elevation: int = 0
    resources: dict = field(default_factory=dict)
    path_cost: float = 1.0
    building: Optional[dict] = None
    territoryRef: Optional[str] = None
    climate: dict = field(default_factory=lambda: {"rainfall": 0.0, "temperature": 20.0})
```

### 2.2 출력 — LandClimateTelemetry (신규, paper §5.2 8 후보 필드)

```python
# physis/land_climate_telemetry.py (신규 모듈)
from dataclasses import dataclass, field
from typing import Optional

@dataclass(slots=True)
class LandClimateMeasurement:
    """Single tile × single tick raw measurement (read-only observer of LandCell)."""
    tick: int
    x: int
    y: int
    # paper §5.2 8 후보 필드 — telemetry 측정 대상
    soil_moisture: float        # [0.0, 1.0] 후보 — climate.rainfall 누적 함수
    fertility: float            # [0.0, 1.0] 후보 — biome × soil_moisture × resources 함수
    rainfall_30d: float         # 30일 누적 강수
    temperature_30d: float      # 30일 평균 기온
    drought_days: int           # 연속 강수 < 임계 일수 후보
    depletion: float            # [0.0, 1.0] 후보 — resources 누적 사용
    recovery_rate: float        # [0.0, 1.0] 후보 — recovery 진행도
    hazard_damage: float        # [0.0, 1.0] 후보 — 재난 누적
    # 본 spec 단계에서는 위 8 필드 모두 telemetry 측정만 — 실제 mechanism 결합은 §7-2~§7-7

@dataclass(slots=True)
class LandClimateTelemetry:
    """Read-only observer. LandCell 본문에 변경 0건 — 별도 누적 객체."""
    seed: int
    window_size: int = 30                          # 30일 기본 (OQ 1)
    measurements_current: dict = field(default_factory=dict)   # (x,y) → list[LandClimateMeasurement]  rolling window
    measurements_cumulative: dict = field(default_factory=dict)  # (x,y) → list[LandClimateMeasurement]  전체 누적

    def observe(self, tick: int, world: "World") -> None:
        """Read LandCell state, derive 8 candidate fields, store in 2 buckets (current + cumulative).

        IMPORTANT: world.iter_cells() 호출만 — LandCell 변경 0건.
        """
        ...

    def trim_window(self, tick: int) -> None:
        """measurements_current에서 window_size보다 오래된 측정 제거 (cumulative는 유지)."""
        ...
```

### 2.3 출력 — extractor (DC-1 SIS 동일 인터페이스)

```python
# scripts/phase17_phi1_land_climate_extractor.py (신규)
from typing import Literal

MetricName = Literal[
    "soil_moisture", "fertility", "rainfall_30d", "temperature_30d",
    "drought_days", "depletion", "recovery_rate", "hazard_damage"
]
QuantileName = Literal["P25", "P50", "P67", "P75", "P90"]
WindowName = Literal["current", "cumulative"]   # paper §8 분리

# extractor 출력 스키마 (DC-1 SIS와 동일 형태)
DistributionTable = dict[
    MetricName,
    dict[WindowName, dict[QuantileName, float]]
]

# seed × metric × window × quantile 일관성 자동 판정 (DC-1 SIS와 동일 ±10%)
SeedConsistencyTable = dict[
    MetricName,
    dict[WindowName, dict[QuantileName, bool]]   # True = 3 seed P50/P67/P75 ±10% 이내
]
```

---

## §3. 측정 대상 — paper §5.2 8 후보 필드 (FREEZE: type만, 수식은 ❌)

| # | 필드 | 단위 | 측정 방법 후보 | 임계 freeze |
|---|---|---|---|:---:|
| 1 | `soil_moisture` | float [0.0, 1.0] | climate.rainfall × 누적 함수 (수식은 §7-2 결정) | ❌ |
| 2 | `fertility` | float [0.0, 1.0] | biome × soil_moisture × resources 결합 (수식은 §7-2 결정) | ❌ |
| 3 | `rainfall_30d` | float | 30일 climate.rainfall 누적 | ❌ |
| 4 | `temperature_30d` | float | 30일 climate.temperature 평균 | ❌ |
| 5 | `drought_days` | int | 연속 rainfall < (raw 분석 후 결정 분위수) 일수 | ❌ |
| 6 | `depletion` | float [0.0, 1.0] | resources 누적 사용 비율 (수식은 §7-2 결정) | ❌ |
| 7 | `recovery_rate` | float [0.0, 1.0] | depletion 회복 속도 후보 (수식은 §7-2 결정) | ❌ |
| 8 | `hazard_damage` | float [0.0, 1.0] | 재난 누적 후보 (재난 mechanism은 §7-3 이후) | ❌ |

> **§7-2 이후 결정 영역**: 위 표 "측정 방법 후보" 컬럼의 정확한 수식, 실제 임계 분위수, mechanism 결합. 본 spec 단계에서는 **30일 raw 누적 측정만**.

---

## §4. 모듈 구조 (FREEZE: 위치 + 시그니처, FREEZE 금지: body)

### 4.1 신규 파일 1개

`Projects/personas/loom/physis/land_climate_telemetry.py`:
- `LandClimateMeasurement` dataclass (위 §2.2)
- `LandClimateTelemetry` dataclass + observe / trim_window 메서드 (위 §2.2)
- 본 spec body는 **시그니처만** freeze — 측정 함수 내부 구현은 구현자 자율 (단, LandCell 무수정 + paper §8 9 원칙 준수)

### 4.2 신규 분석 스크립트 1개

`Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py`:
- LandClimateTelemetry → DistributionTable + SeedConsistencyTable 변환
- 3 seed (7/13/42) × 8 metric × 2 window × 5 분위수 = 240 cell 출력
- DC-1 SIS extractor와 동일 형태 (windowed distribution table + 일관성 boolean)

### 4.3 호출 지점 — core 무수정

본 spec은 `core/multi_tick_engine.py` 변경 0건. LandClimateTelemetry는 **외부 호출자**가 매 tick observe 호출:
- 시뮬 실행 스크립트 (예: `scripts/phase17_phi1_land_climate_collect.py` — 신규, optional)
- 또는 기존 시뮬 hook이 있다면 그곳에서 호출 (단 core 무수정)

> **호출 지점은 본 spec body에서 freeze 금지** — 구현 단계에서 raw-first 정합 위치 결정.

---

## §5. 변경 영역 + 무수정 영역

### 5.1 변경 (신규 추가만, 기존 변경 0건)

| 파일 | 작업 | 유형 |
|---|---|:---:|
| `Projects/personas/loom/physis/land_climate_telemetry.py` | 신규 | 모듈 |
| `Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py` | 신규 | 분석 스크립트 |
| `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect.py` | 신규 (optional) | 수집 스크립트 |

### 5.2 변경 없음 (금지 — 위반 시 본 spec 거부)

- `Projects/personas/loom/physis/world.py` (LandCell 본문 + 클래스 + project_territory + initialize_world)
- `Projects/personas/loom/physis/poisson.py`
- `Projects/personas/loom/core/multi_tick_engine.py`
- `Projects/personas/loom/core/*.py`
- `Projects/personas/loom/ontology/*.py`
- `Projects/personas/loom/struggle/*.py`
- `Projects/personas/loom/api/*.py`
- `Projects/personas/loom/brain/*.py` (SNN / PersonaBrain)
- `Projects/personas/loom/test_*.py` (회귀 7종 + acceptance + 기타)
- 기존 모든 spec [확정] 본문 (DC-1 SIS / DC-2 CPCM rev.3 / DC-3 P5R rev.2)

---

## §6. 검증 (paper §8 9 원칙 + OQ 3 3중)

### 6.1 LandCell 무수정 3중 검증 (OQ 3 결정)

```bash
# (a) git diff physis/world.py 본문 = 0 lines
cd Projects/personas/loom
git diff HEAD -- physis/world.py
# 기대: empty (변경 0건)

# (b) 회귀 7종 (Tier 1) 동일 결과
py -m pytest \
  test_phase17_acceptance.py \
  test_phase17_faction.py \
  test_phase17_faction_stage3.py \
  test_phase17_faction_regression.py \
  test_phase17_faction_handoff_contract.py \
  test_phase14b_snn_integration.py \
  test_phase17_land.py \
  -q
# 기대: 89 passed / 4 failed (V-3 2026-05-07 동일 — closure-v2 §2.1/§2.2 잔재)
# 새 FAIL 발생 시 → 본 spec 구현 거부

# (c) acceptance #1·#3·#5 + no_deaths PASS 동일
# (b)에 포함됨 — 89 passed 안에 acceptance 본체 89/93 PASS 보존 확인
```

### 6.2 paper §8 9 원칙 자체 검증

| 원칙 | 본 spec 충족 |
|---|---|
| raw-first telemetry | ✓ — 8 후보 필드 raw 측정만, mechanism 결합 0건 |
| deterministic seed replay | ✓ — 3 seed (7/13/42) 고정 |
| no-core-diff gate | ✓ — `core/` `ontology/` `struggle/` `brain/` 변경 0건 |
| no false PASS | ✓ — 회귀 7종 V-3 결과 동일 (4 failed 보존, false PASS 없음) |
| threshold freeze 금지 | ✓ — 분위수 임계값 spec body에 freeze 0건 (§3 표 우측 컬럼 ❌) |
| current-window vs cumulative 구분 | ✓ — `measurements_current` + `measurements_cumulative` 분리 (§2.2) |
| long-run seed 7/13/42 검증 | ✓ — 3 seed extractor + 일관성 자동 판정 |
| acceptance 변경 금지 | ✓ — acceptance 4종 [금지] 명시 |
| SNN/brain 변경 시 별도 core 승인 | ✓ — brain/ 영역 [금지] 명시 |

### 6.3 분위수 후보 도출 (magic threshold freeze 금지)

```bash
py scripts/phase17_phi1_land_climate_extractor.py
# 기대 출력: 3 seed × 8 metric × 2 window × 5 분위수 = 240 cell DistributionTable
#         + 3 seed 일관성 자동 판정 SeedConsistencyTable (P50/P67/P75 ±10% boolean)
# 분위수 값은 spec body에서 freeze 금지 — 출력만 보존, §7-2 spec 작성 시 입력값
```

### 6.4 기계 검증

```bash
py -m mypy Projects/personas/loom/physis/land_climate_telemetry.py --strict
py -m ruff check Projects/personas/loom/physis/land_climate_telemetry.py
py -c "import ast; ast.parse(open('Projects/personas/loom/physis/land_climate_telemetry.py').read())"
py -m mypy Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py --strict
py -m ruff check Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py
```

---

## §7. §3.7 6단 사슬 매핑

| 단 | 본 spec 위치 | 산출물 |
|:---:|---|---|
| 1단 자연 측정 | §1.2 + §3 + §4.1 LandClimateTelemetry | 30일 rolling raw 측정 |
| 2단 분포 분석 | §4.2 extractor + §6.3 분위수 도출 | 240 cell DistributionTable |
| 3단 결합점 후보 | **§7-2 spec 작성 시점 결정 영역** | (본 spec 외부) |
| 4단 임계 분위수 | **§7-2 spec body에서 도출** | (본 spec 외부) |
| 5단 3엔진 cross-check | §7-2 spec 작성 후 별도 작업 | (본 spec 외부) |
| 6단 closure 보고서 | rev.next §7-1 단계 closure | 본 spec 구현 + 30일 probe 완료 보고서 |

---

## §8. 회귀 0% 보장 — git diff 후 확인

본 spec 구현 후 다음 git diff 명령이 `core/` `ontology/` `struggle/` `brain/` `api/` 영역에서 **empty**여야 함:

```bash
cd Projects/personas/loom
git diff HEAD -- core/ ontology/ struggle/ brain/ api/ physis/world.py physis/poisson.py
# 기대: empty (mechanism / Φ-2~Φ-5 / brain / LandCell 본문 변경 0건)
```

empty 아닌 경우 → 본 spec 구현 **거부** + 정정 후 재검증.

---

## §9. Rollback

본 spec 구현이 회귀 7종 또는 acceptance에 영향을 주는 경우 (Φ-1 무파괴 위반):

```bash
# bash
rm Projects/personas/loom/physis/land_climate_telemetry.py
rm Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py
rm -f Projects/personas/loom/scripts/phase17_phi1_land_climate_collect.py
```

```powershell
# PowerShell
Remove-Item Projects/personas/loom/physis/land_climate_telemetry.py
Remove-Item Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py
Remove-Item Projects/personas/loom/scripts/phase17_phi1_land_climate_collect.py -ErrorAction SilentlyContinue
```

신규 파일만 추가하므로 기존 파일 복원 불필요. Rollback 후 회귀 7종 V-3 결과 동일 확인.

---

## §10. 구현 후 산출물 (raw 분석 1단계 closure 입력)

| # | 산출물 | 위치 |
|:---:|---|---|
| 1 | LandClimateTelemetry 모듈 | `physis/land_climate_telemetry.py` |
| 2 | extractor 스크립트 | `scripts/phase17_phi1_land_climate_extractor.py` |
| 3 | 30일 probe 데이터 (3 seed) | `data/phase17_phi1_land_climate_probe/seed_{7,13,42}/` |
| 4 | DistributionTable (3 seed × 8 metric × 2 window × 5 분위수) | `data/phase17_phi1_land_climate_probe/distribution_table.json` |
| 5 | SeedConsistencyTable | `data/phase17_phi1_land_climate_probe/seed_consistency.json` |
| 6 | 1단계 closure 보고서 | `data/phase17_phi1_land_climate_probe/SUMMARY.md` |

산출물 5번까지 완료 후 §7-2 Resource/Fertility Dynamics Spec 작성 진입 (사용자 사전 승인 — §3.3.2 mechanism 영역).

---

## §11. 변경 이력

- **rev.0** (2026-05-07): 초안 author. STUB v0.1 OQ 1~6 결정 통합. paper §7-1 / §5.2 / §8 정합. LandCell read-only observer 패턴 (OQ 3 — `physis/world.py:23` 본문 무수정 검증 3중). DC-1 SIS extractor 동일 인터페이스 (OQ 4). DC-3 P5R v0 → v1 envelope 분리 (OQ 5). 보존 invariant 7종 명시.
