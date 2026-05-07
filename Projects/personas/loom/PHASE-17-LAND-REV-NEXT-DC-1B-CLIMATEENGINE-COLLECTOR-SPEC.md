# [분석 스크립트] DC-1B ClimateEngine Collector — Φ-1 Land rev.next §7-1 evidence base 보강

> **상태**: rev.1 (OQ 1B-1 + 1B-3 사용자 결정 반영 — 2026-05-07; sub-implementer spawn 가능)
> **긴급도**: 중간 (DC-1 §7-1 synthetic smoke baseline 봉인 직후 — paper §7-1 raw evidence value 보강)
> **선행 조건**:
> - DC-1 §7-1 SPEC rev.0 [봉인] (commit `6197f8e`, 2026-05-07)
> - STUB v0.2 (Future Work 통합)
> - finding 1-b (사용자 검토 2026-05-07)
> **작업 유형**: 분석 스크립트 (collector 신규 author — synthetic baseline 보존, real driver 추가)
> **DB migration**: 없음
> **외부 의존**: 없음 (`physis.climate_engine.ClimateEngine` 기존 모듈)
> **권위 문서**:
> - `PHASE-17-LAND-REV-NEXT-DC-1-LAND-CLIMATE-PROBE-SPEC.md` rev.0
> - `PHASE-17-LAND-REV-NEXT-STUB.md` v0.2 §12
> - paper(2026-05-07) §7-1 / §5.2 / §8
> - finding 1-b (2026-05-07 사용자 검토)

---

## §0. 권위 / 단방향 계약 / 보존 invariant

### 0.1 단방향 계약 (Φ-5 ← Φ-4 ← Φ-3 ← Φ-2 ← **Φ-1**)

DC-1 §7-1 spec rev.0 §0.1과 동일. 본 spec은 Φ-1 Land 영역 driver wiring **only**.
다음 영역에 변경 0건:

- Φ-2 Faction (`faction.py`)
- Φ-3 Struggle (`struggle/faction_*.py`, uprising 본문)
- Φ-4 Nation (Φ-3 closure 봉인 본문)
- Φ-5 read-only API (`api/__init__.py`, `api/nation_p5r.py`)
- brain·SNN (Phase 14B-d / PersonaBrain)
- core (`core/multi_tick_engine.py`)
- ontology (Phase 11~16 무파괴)

### 0.2 §1.0 body 고정 금지 caveat

DC-1 §7-1 spec rev.0 §0.2와 동일. 본 spec은 **driver wiring + CLI**만 freeze.
다음은 freeze **금지**:

- 8 후보 필드의 임계 분위수 (P25/P50/P67/P75/P90 자체는 도출 대상)
- 추가 window/tick 길이 (90 tick 기본만 freeze, 다른 길이는 raw 분석 후 결정)
- mechanism 결합 후보 (§7-2 이후 단계 결정 영역)

본 spec rev.1에서 freeze **확정** 영역 (rev.0의 "결정 영역"에서 승격):

- ClimateEngine `weather` dict → `LandCell.climate` direct mapping 식 (§2.3 — type signature freeze)
- `--ticks` default = 90 (current/cumulative 분리 검증 기본값; 30은 smoke 최소값으로 별도 보존)

### 0.3 보존 invariant 7종 + 본 spec 추가 3종

DC-1 §7-1 spec rev.0 §0.3 (7종) **모두 유지** + 본 spec에서 추가:

8. **DC-1 §7-1 synthetic smoke 산출 (봉인된 baseline)** —
   `scripts/phase17_phi1_land_climate_collect.py` /
   `data/phase17_phi1_land_climate_probe/**` 본 spec에서 **무수정 (영원)**.
   smoke axis와 real axis는 분리된 evidence 축 — 같은 변경 단위에 섞지 않음.
9. **`LandClimateTelemetry` 본문 무수정** — same observer, different driver.
   본 spec은 driver만 신규.
10. **`physis.climate_engine.ClimateEngine` 본문 무수정** — driver는 ClimateEngine의
    public interface(`tick(day_of_year, hour)`)만 호출. `_compute_region_weather` /
    `_update_cumulative` 등 내부 mechanism 변경 0건.

---

## §1. 목적 + 범위

### 1.1 trigger — finding 1-b (2026-05-07 사용자 검토)

> **Finding 1-b (Major, 본 spec 분리)**: 현재 `phase17_phi1_land_climate_collect.py`는
> random walk synthetic smoke. paper §7-1 evidence value의 raw 기반으로 부족.
> 실제 evidence는 `physis.climate_engine.ClimateEngine` 기반 자연 진화 결과여야 한다.

본 spec은 finding 1-b 응답:
- synthetic smoke baseline은 그대로 봉인 보존 (smoke evidence axis)
- real driver는 분리된 evidence axis로 신규 author
- 두 축은 paper §7-1의 서로 다른 evidence 단계 — synthetic은 인터페이스 검증,
  real은 mechanism 진입 전 raw 분포 확정

### 1.2 본 spec 범위

| 항목 | 본 spec | §7-2 이후 |
|---|:---:|:---:|
| 신규 collector — ClimateEngine driver wiring | ○ | - |
| LandCell.climate dict 자연 진화 driver (90 tick 기본) | ○ | - |
| `LandClimateTelemetry` **무수정** 재사용 | ○ | - |
| extractor **무수정** 재사용 (probe.json 인터페이스 동일) | ○ | - |
| 분리 출력 dir `data/.../_probe_real/` | ○ | - |
| `[REAL]` provenance 라벨 (synthetic 구별 표지) | ○ | - |
| **synthetic smoke baseline 변경** | **금지** | 영원 |
| **mechanism 결합 (depletion / fertility 수식)** | **금지** | §7-2 |
| **LandCell 본문 변경** | **금지** | §7-2 + 사용자 사전 승인 |
| **ClimateEngine 본문 변경** | **금지** | 영원 (driver only) |

### 1.3 [필수] / [선택] / [금지]

#### [필수]

1. 신규 collector `scripts/phase17_phi1_land_climate_collect_real.py` author —
   ClimateEngine 기반 LandCell.climate dict 갱신 driver
2. argparse:
   - `--ticks N` (default **90** — issue 2 해소: current vs cumulative 분리 보장,
     §7-1 impl.result.md issue 2 인용)
   - `--seeds 7,13,42` (DC-1 §7-1 동일 seed set)
   - `--planet-config <path>` (옵션, 기본은 `NovaPlanet()` 기본값)
3. probe.json 인터페이스 호환 — 기존 `phase17_phi1_land_climate_extractor.py` 재사용 가능
4. `[REAL]` provenance 명시:
   - module docstring 최상단 "WARNING — real evolution collector" 헤더
   - print 시작 라인 `[REAL] phase17_phi1_land_climate_collect_real.py — ClimateEngine driver`
5. NaN/Infinity strict (`json.dump(allow_nan=False)`) — DC-1 §7-1 hotfix 정책 동일
6. 출력 dir 분리: `data/phase17_phi1_land_climate_probe_real/seed-{7,13,42}/probe.json` —
   synthetic baseline (`_probe/`) 무영향
7. mypy strict (`--follow-imports=silent`) + ruff PASS — DC-1 §7-1 동일 정책
8. 회귀 7종 (Tier 1) 무영향 logical proof (test 파일 import 0건 + mechanism 영역 git diff empty)

#### [선택]

- 추가 ticks (예: 120 / 180) — raw 분석 결과 기반 후속 결정
- 추가 planet-config 다양화 (paper §5.2 region 다양성 보강) — STUB rev.next §13 OQ 추가
- summary.md 산출 (extractor 재실행 결과)
- `synthetic vs real` 비교 분석 보고서 — `impl.result.md`에 inline 또는 별도 dir

#### [금지]

- synthetic baseline collector 변경 (`collect.py`, `_probe/` 데이터)
- extractor 본문 변경 (인터페이스 호환 강제)
- `LandClimateTelemetry` 본문 변경
- `physis.climate_engine.ClimateEngine` 본문 변경 (driver는 public `tick()` 호출만)
- `LandCell` 본문 / `climate` dict 새 키 추가 / mechanism / acceptance 변경
- core / ontology / struggle / Φ-2 / Φ-3 / Φ-4 / Φ-5 / brain·SNN 영역 변경
- 기존 회귀 7종 변경
- magic threshold freeze (분위수 임계값 spec body 명시)

---

## §2. ClimateEngine wiring 설계 (driver only)

### 2.1 ClimateEngine public interface (인용 — 본 spec body는 freeze 금지)

`physis/climate_engine.py:30-69`에서 public interface 발췌:

```python
class ClimateEngine:
    def __init__(self, planet: NovaPlanet | None = None, seed: int = 20260406): ...
    def tick(self, day_of_year: int, hour: int) -> dict[str, dict]:
        """3권역 날씨 dict 반환. {"claude": {...}, "codex": {...}, "gemini": {...}}"""
```

본 spec body는 weather dict의 정확한 키 매핑(`temp`/`precip_mm` etc.)을
freeze 금지 — §2.3 OQ-1B-1 결정 영역.

### 2.2 evolution loop (의사코드)

```
engine = ClimateEngine(planet=<config or None>, seed=<seed>)
landcells = init_landcells(seed=<seed>)  # 8x8 = 64 cells, region tag 보유
observer = LandClimateTelemetry(window_size=30)

for t in range(--ticks):
    day_of_year = t // 24
    hour = t % 24
    weather = engine.tick(day_of_year, hour)  # ClimateEngine 본문 호출
    for cell in landcells:
        region_id = cell.region_id   # "claude" | "codex" | "gemini"
        cell.climate["rainfall"]    = <wiring §2.3 OQ-1B-1>
        cell.climate["temperature"] = <wiring §2.3 OQ-1B-1>
        observer.observe(cell, t)   # LandClimateTelemetry 무수정 재사용
```

### 2.3 weather dict → LandCell.climate direct mapping 식 [확정 — rev.1 / 2026-05-07]

ClimateEngine `_compute_region_weather` 실제 return key (검증: `physis/climate_engine.py:162-165`)
기준 **direct mapping** 채택:

```python
cell.climate["rainfall"]    = weather["precipitation_mm"]   # ClimateEngine line 165
cell.climate["temperature"] = weather["temperature_c"]      # ClimateEngine line 163
```

근거 (사용자 결정 2026-05-07):

- **direct**가 paper §7-1 raw evidence의 가장 직접적 형태 — 정규화/평균화 단계 0건
- ClimateEngine 본문 변경 0건 — public `tick()` return을 그대로 mapping
- LandClimateTelemetry observer는 단위 무관 (P25~P90 분위수만 계산) — 단위 보정 불필요

**legacy fallback** (collector 내부 한정):

ClimateEngine `tick()` 결과에서 키 누락이 발생할 가능성은 **0** (line 162-165에서 항상 `temperature_c` + `precipitation_mm` 동시 emit). 그러나 방어적 fallback 1단:

```python
# collector_real.py 내부 helper
rainfall    = weather.get("precipitation_mm", weather.get("rainfall",    0.0))
temperature = weather.get("temperature_c",    weather.get("temperature", 20.0))
```

이는 collector 내부에 한정되며, ClimateEngine 본문 / LandCell / telemetry / extractor에는 fallback 코드 0건 (단방향 계약 + observer 무수정 invariant 유지).

#### rev.0의 (b) normalized / (c) mean 제외 사유

| 후보 | 제외 사유 |
|---|---|
| (b) normalized (`precip_mm / 30.0`) | 정규화 자체가 mechanism 진입 신호. raw 단계에서 차단. |
| (c) mean of 3 region | LandCell의 region tag 부재 처리는 §2.4 OQ-1B-2로 분리. 매핑 식과 무관. |

### 2.4 LandCell region tag 확보

OQ-1B-2: LandCell이 region tag (`"claude"/"codex"/"gemini"`)를 보유하는가?

- `physis/world.py` 본 spec에서 변경 0건.
- 만약 region tag 부재 → driver는 cell index 기반 결정론적 region 할당 (8x8 grid 3등분).

이는 collector 내부 helper로 처리 — `LandCell.region_id` 필드 추가 **금지** (LandCell 본문 무수정).

---

## §3. 검증

### 3.1 mechanism 결합 무영향 — logical proof

DC-1 §7-1 hotfix 동형:

| 검증 | 명령 | 기대 |
|---|---|:---:|
| collector_real 신규 author 외 변경 0 | `git diff HEAD -- physis/ core/ ontology/ struggle/ brain/ api/ test_*.py` | empty |
| extractor 무수정 | `git diff HEAD -- scripts/phase17_phi1_land_climate_extractor.py` | empty |
| synthetic baseline 무수정 | `git diff HEAD -- scripts/phase17_phi1_land_climate_collect.py data/phase17_phi1_land_climate_probe/` | empty |
| LandClimateTelemetry 무수정 | `git diff HEAD -- physis/land_climate_telemetry.py` | empty |
| ClimateEngine 무수정 | `git diff HEAD -- physis/climate_engine.py` | empty |
| 회귀 test 파일 import 0건 | `grep -l "land_climate_collect_real" test_*.py` | 0 |

### 3.2 evidence 분리 (smoke axis ↔ real axis)

| 축 | 출력 dir | 라벨 | 용도 |
|---|---|---|---|
| smoke baseline (봉인) | `data/phase17_phi1_land_climate_probe/` | `Provenance: synthetic smoke` | 인터페이스 검증, smoke evidence |
| real (본 spec) | `data/phase17_phi1_land_climate_probe_real/` | `Provenance: ClimateEngine real evolution` | paper §7-1 raw evidence base |

두 축은 **독립 dir** — synthetic을 real로 덮어쓰는 흐름은 영원히 금지.

### 3.3 self-validation 12종 (sub-implementer 보고 의무)

| # | 검증 | 명령 | 기대 |
|---:|---|---|:---:|
| 1 | mypy strict — collector_real | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_collect_real.py --strict --follow-imports=silent` | PASS |
| 2 | ruff — collector_real | `py -3.12 -m ruff check scripts/phase17_phi1_land_climate_collect_real.py` | PASS |
| 3 | collector_real 실행 (3 seed × 90 tick) | `py -3.12 scripts/phase17_phi1_land_climate_collect_real.py` | seed-{N}/probe.json 3개 생성 (`_probe_real/`) |
| 4 | extractor 재실행 (real) | `py -3.12 scripts/phase17_phi1_land_climate_extractor.py --probe-dir data/phase17_phi1_land_climate_probe_real` | distribution.json + summary.md 생성, NaN 0건 |
| 5 | `[REAL]` 라벨 grep — collector | `grep -l "REAL\|ClimateEngine driver" scripts/phase17_phi1_land_climate_collect_real.py` | match |
| 6 | `[REAL]` 라벨 grep — summary.md | `grep -l "ClimateEngine real evolution" data/phase17_phi1_land_climate_probe_real/**/summary.md` | match 4 파일 |
| 7 | synthetic baseline 무수정 | `git diff HEAD -- scripts/phase17_phi1_land_climate_collect.py data/phase17_phi1_land_climate_probe/` | empty |
| 8 | ClimateEngine 본문 무수정 | `git diff HEAD -- physis/climate_engine.py` | empty |
| 9 | LandClimateTelemetry / extractor 무수정 | `git diff HEAD -- physis/land_climate_telemetry.py scripts/phase17_phi1_land_climate_extractor.py` | empty |
| 10 | 보호 영역 git diff | `git diff HEAD -- physis/world.py core/ ontology/ struggle/ brain/ api/ test_*.py` | empty |
| 11 | 회귀 test 파일 import 0건 | `grep -l "land_climate_collect_real" test_*.py` | 0 |
| 12 | current vs cumulative 분리 검증 | 90 tick 결과의 `measurements_current` 길이 == 30 (rolling) ≠ `measurements_cumulative` 길이 (= 90 × 64 cell) | logical proof |

12종 모두 PASS 시 sub-implementer 종료. 실패 시 `STOP_FOR_USER` + 원인 분석 보고.

### 3.4 §1.0 caveat 재확인

- 분위수 임계값 freeze: 본 spec은 *값*을 freeze 0건 (분위수는 도출 대상)
- window 길이 freeze: 30 default 유지, --ticks N 매개변수화
- mechanism 결합 수식: 본 spec mechanism 함수 0건 (raw probe + driver wiring only)
- LandCell 본문 변경: 0건
- climate dict 새 키 추가: 0건 (rainfall + temperature only — 매핑 식만 driver 결정)

→ §1.0 caveat 위반 0건 유지.

---

## §4. 변경 파일

| 경로 | 작업 | 비고 |
|---|---|---|
| `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect_real.py` | 신규 author | ClimateEngine driver collector |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/seed-{7,13,42}/probe.json` | 자동 생성 | 90 tick × 64 cell × 2 metric |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/seed-{7,13,42}/distribution.json` | 자동 생성 (extractor) | per-seed 240 cell |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/aggregate/distribution.json` | 자동 생성 (extractor) | aggregate 80 cell |
| `Projects/personas/loom/data/phase17_phi1_land_climate_probe_real/{seed-*,aggregate}/summary.md` | 자동 생성 (extractor) | `Provenance: ClimateEngine real evolution` 라벨 |
| `subagent-runs/claude/phase17-phi1-land-climate-real-collector-<date>/` | 신규 author (sub-impl evidence) | run-manifest + run-summary + prompts/ + results/ |

**변경 없음 (금지):**
- `scripts/phase17_phi1_land_climate_collect.py` (synthetic baseline 봉인)
- `data/phase17_phi1_land_climate_probe/` (synthetic 산출 봉인)
- `scripts/phase17_phi1_land_climate_extractor.py` (인터페이스 호환 강제)
- `physis/land_climate_telemetry.py` (observer 무수정)
- `physis/climate_engine.py` (driver는 public `tick()` 호출만)
- `physis/world.py` (LandCell 본문 무수정)
- `core/` `ontology/` `struggle/` `brain/` `api/` `test_*.py` (단방향 계약)

---

## §5. Open Questions

| # | 질문 | 결정 / 권고 | 상태 |
|---:|---|---|:---:|
| 1B-1 | weather dict → LandCell.climate 매핑 식 (§2.3) | **direct**: `precipitation_mm` / `temperature_c` (collector 내부 legacy fallback 1단) | **[확정 — rev.1 / 2026-05-07]** |
| 1B-2 | LandCell region tag — 부재 시 collector 내부 결정론적 할당 (§2.4) | 8x8 grid 3등분 권고 | sub-impl 진입 시 검증 |
| 1B-3 | `--ticks` default | **90** (current/cumulative 분리 검증; 30은 smoke 최소값으로 별도 보존) | **[확정 — rev.1 / 2026-05-07]** |
| 1B-4 | planet-config 다양화 — single default vs multi-region | single default (rev.1) | rev.next |
| 1B-5 | synthetic vs real 비교 보고서 위치 | `impl.result.md` inline | sub-impl 진입 시 결정 |

---

## §6. Future Work

- §7-2 mechanism spec 진입 전 본 spec 결과 raw 분포가 evidence base로 사용됨
- real driver 결과 분포가 synthetic baseline과 유의미한 차이 보유 시 paper §7-1 evidence value 봉인
- 차이 미미 시 collector 매개변수 (planet-config / ticks) 다양화 검토 (rev.next)

---

## §7. Rollback

본 spec 작업물은 분리 dir `data/phase17_phi1_land_climate_probe_real/` + 신규 단일 파일
`scripts/phase17_phi1_land_climate_collect_real.py`만 추가. Rollback:

```bash
git rm scripts/phase17_phi1_land_climate_collect_real.py
git rm -r data/phase17_phi1_land_climate_probe_real/
git rm -r subagent-runs/claude/phase17-phi1-land-climate-real-collector-<date>/
```

synthetic baseline / extractor / LandCell / ClimateEngine 모두 무영향 — Rollback은 단순.

---

## §8. 변경 이력

### rev.0 — 2026-05-07 초안

- finding 1-b (사용자 검토 2026-05-07) 응답
- DC-1 §7-1 rev.0 봉인 (commit `6197f8e`) 후속 spec 분리
- synthetic baseline 무수정 + real driver 신규 author
- OQ 1B-1 ~ 1B-5 정의 (사용자 승인 게이트 통과 후 sub-implementer spawn 진입)
- 본 spec 자체 봉인 status: **rev.0 초안 — 사용자 승인 대기**

### rev.1 — 2026-05-07 사용자 결정 반영

- **OQ 1B-1 [확정]**: weather dict → LandCell.climate **direct mapping** —
  ClimateEngine `_compute_region_weather` line 162-165 검증 기반 실제 key
  (`weather["precipitation_mm"]`, `weather["temperature_c"]`) 채택.
  legacy fallback은 collector 내부에 한정 — ClimateEngine / telemetry / extractor 본문 0건.
- **OQ 1B-3 [확정]**: `--ticks` default **90** (current/cumulative 분리 검증 기본값).
  30은 smoke 최소값으로 별도 보존. 120/180은 [선택] (raw 분석 결과 기반 후속 결정).
- §0.2 §1.0 caveat에 "freeze **확정** 영역" sub-section 추가
  (rev.0 초안의 "결정 영역"에서 승격).
- §2.3 OQ 표를 결정 명시로 교체 + ClimateEngine line 인용 + (b)/(c) 제외 사유 표.
- §5 OQ 표 1B-1 / 1B-3 status를 **[확정 — rev.1 / 2026-05-07]** 로 update.
- spec status: **rev.1 — sub-implementer spawn 가능** (1B-2 / 1B-5는 sub-impl 진입 시 검증).
- commit 분리 정책: 본 rev.1 반영 commit은 `6197f8e` (synthetic baseline 봉인) 와 섞지 않음 —
  STUB v0.3 §12 link 추가와 동일 commit으로 묶음.

### rev.2 — TBD (sub-implementer 1차 결과 후)

- OQ 1B-2 / 1B-5 결정 명시 (sub-impl 진입 시 결정 사항)
- sub-implementer 결과 evidence 인용 (run-summary + impl.result)
- synthetic vs real 분포 비교 보고서 통합
- spec status: **[확정]** (rev.2 봉인 후 본 collector_real는 §7-2 진입 전 raw evidence base)
