# sub-implementer prompt — Phase 17 Φ-1 §7-1 Probe Hotfix

## 권위 출처

- spec: `Projects/personas/loom/PHASE-17-LAND-REV-NEXT-DC-1-LAND-CLIMATE-PROBE-SPEC.md` rev.0
- STUB: `Projects/personas/loom/PHASE-17-LAND-REV-NEXT-STUB.md` v0.1
- review (본 prompt 직전 사용자 검토): finding 4종 (Major×1 + Medium×2 + Minor×1)

## 목표

§7-1 Probe 산출물의 evidence 안정성 보강. 최소 4종 변경 (Finding 1-b는 본 hotfix 범위 외 — 별도 PR로 분리).

## 작업 범위 (4 finding × 5 파일)

### Finding 1-a — Major: collector `synthetic smoke` 명시

**위치**: `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect.py`

- module docstring 최상단에 다음 경고를 명시 (예시):
  ```
  > **WARNING — synthetic smoke collector**: This collector uses a *random walk* in
  > `_evolve_climate()` (line ~113), NOT the actual `ClimateEngine`. The output JSON is
  > suitable as **smoke / sample evidence only**, not as raw evidence for §7-2 Resource/
  > Fertility decisions. A separate `phase17_phi1_land_climate_collect_real.py` (using
  > `physis.climate_engine.ClimateEngine`) is to be added in a follow-up PR before §7-2
  > evidence base is finalized.
  ```
- print 시작 헤더에도 한 줄 SMOKE 경고 추가 (실행 시 stdout 표시):
  ```
  [SMOKE] phase17_phi1_land_climate_collect.py — synthetic random walk (NOT ClimateEngine)
  ```

**위치**: `Projects/personas/loom/data/phase17_phi1_land_climate_probe/aggregate/summary.md`

- 최상단 또는 frontmatter에 다음 한 줄 명시:
  ```
  > **Provenance**: synthetic smoke collector (random walk). NOT actual `ClimateEngine` output.
  > Suitable as smoke evidence only. §7-2 evidence requires real-collector reproduction.
  ```

**위치**: `Projects/personas/loom/data/phase17_phi1_land_climate_probe/seed-{7,13,42}/summary.md`

- 동일한 Provenance 라벨 추가 (3 파일 동일 한 줄)

### Finding 2 — Medium: collector `--ticks N` argparse

**위치**: `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect.py`

- `argparse.ArgumentParser`로 `--ticks` 인자 추가
- 기본값은 `DEFAULT_WINDOW_SIZE` (= 30) — spec §1.0 caveat "window 길이 freeze 금지"는 *값*에 대한 것이지 *매개변수화 자체*는 허용
- `--seeds` 인자도 함께 추가 (기본 `7,13,42`) — extractor와 동일 패턴
- argparse help text에 다음 명시:
  ```
  --ticks N      tick count (default: 30 = DEFAULT_WINDOW_SIZE).
                 Use --ticks 60 or 90 for current/cumulative separation evidence.
                 NOTE: this is raw window extension, NOT threshold freeze.
  ```
- argparse 구현 후 `if __name__ == "__main__"` 진입에서 args 사용

### Finding 3 — Medium: extractor strict JSON

**위치**: `Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py`

두 가지 변경:

1. **빈 입력 → `ValueError`**: 현재 코드(line ~135 추정)에서 `if not values: return float("nan")` 이런 분기가 있다면, `float("nan")` 반환 대신 `raise ValueError(f"empty input: cannot compute quantiles for metric={metric}, window={window}")` 로 교체. 단, 호출부에서 빈 metric을 명시적으로 skip하거나 별도 표지(예: `null`)를 넣는 흐름이 있다면 호출부에서 try/except 처리. 결과 JSON에는 NaN이 절대 들어가지 않도록 보장.
2. **`json.dump(..., allow_nan=False)`**: line ~317, ~386 (per-seed + aggregate) 모든 `json.dump()` 호출에 `allow_nan=False` 추가. 호출 후 NaN/Infinity가 이미 없음을 보장하므로 정상 흐름에서 raise 안 됨.

자체 단위 검증 (`results/impl.result.md`에 명시):
```python
# empty input ValueError
import importlib.util
spec = importlib.util.spec_from_file_location("ext", "scripts/phase17_phi1_land_climate_extractor.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
try:
    mod._compute_quantiles([], "soil_moisture", "current")
except ValueError:
    print("empty ValueError PASS")
```
(함수명·시그니처는 실제 코드에 맞게 조정)

### Finding 4 — Minor: STUB v0.1 → v0.2 + v1 wrapper future-work

**위치**: `Projects/personas/loom/PHASE-17-LAND-REV-NEXT-STUB.md`

- §10 Actionable Next 또는 §11 변경 이력 다음에 새 sub-section 추가 (예: §12 Open Questions / Future Work):
  ```markdown
  ### Future Work — DC-3 P5R v1 wrapper (Minor — 2026-05-07 finding 4)

  현재 P5R rev.2 v0 baseline의 `NationSovereignty.dom_share` / `conflict_pair_count` 등은 단일
  scalar property이다. consumer가 "국가 주권 *상태*"로 오해할 위험을 v0 단계에서는 §1.0 caveat
  명문화로 차단한다. v1 단계 (실제 consumer 진입 직전)에서는 wrapper 확장 권고:

  - `provenance: dict` (어떤 metric/window에서 도출됐는지)
  - `window: int` (몇 tick 관측한 결과인지)
  - `distribution: DistributionTable` (분위수 컨텍스트)
  - `status: Literal["candidate", "confirmed"]` (자연 발생 검증 상태)

  v1 wrapper는 v0과 별도 모듈(예: `api/nation_p5r_v1.py`)로 author하여 v0 invariant 유지.
  ```
- `## 변경 이력` 섹션에 새 entry 추가:
  ```markdown
  ### v0.2 — 2026-05-07 사용자 검토 finding 4 hotfix
  - **추가**: §12 Future Work — DC-3 P5R v1 wrapper 권고 (Finding 4 / Minor)
  - **무관**: OQ 1~6 결정 / §7-1 spec rev.0 본문 모두 변경 없음
  - **trigger**: §7-1 collector/extractor hotfix 동시 commit (synthetic smoke 라벨 + strict JSON + `--ticks` argparse + Future Work memo)
  ```

## 자체 검증 (보고 의무)

`results/impl.result.md`에 다음 검증 결과 표 작성:

| # | 검증 | 명령 | 결과 |
|---:|---|---|:---:|
| 1 | mypy strict — collector | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_collect.py --strict --follow-imports=silent` | PASS / FAIL |
| 2 | mypy strict — extractor | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_extractor.py --strict --follow-imports=silent` | PASS / FAIL |
| 3 | ruff — collector | `py -3.12 -m ruff check scripts/phase17_phi1_land_climate_collect.py` | PASS / FAIL |
| 4 | ruff — extractor | `py -3.12 -m ruff check scripts/phase17_phi1_land_climate_extractor.py` | PASS / FAIL |
| 5 | extractor 재실행 (strict NaN) | `py -3.12 scripts/phase17_phi1_land_climate_extractor.py` | seed-{N}/distribution.json + aggregate/distribution.json 재기록, NaN 0건 (PASS) |
| 6 | extractor empty ValueError | python 단위 확인 (위 prompt 참조) | "empty ValueError PASS" |
| 7 | collector `--ticks 60` dry-run | `py -3.12 scripts/phase17_phi1_land_climate_collect.py --ticks 60 --seeds 7` | 60 tick 수집 + probe.json 생성 (PASS) |
| 8 | collector SMOKE 라벨 grep | `grep -l "SMOKE\|synthetic" scripts/phase17_phi1_land_climate_collect.py` | match 1건 이상 |
| 9 | summary.md SMOKE 라벨 grep | `grep -l "synthetic smoke\|Provenance" data/phase17_phi1_land_climate_probe/aggregate/summary.md data/phase17_phi1_land_climate_probe/seed-*/summary.md` | match 4 파일 |
| 10 | STUB v0.2 entry 확인 | `grep -l "v0.2\|Future Work" Projects/personas/loom/PHASE-17-LAND-REV-NEXT-STUB.md` | match |
| 11 | 보호 영역 git diff | `git diff HEAD -- physis/world.py physis/climate_engine.py physis/land_climate_telemetry.py core/ ontology/ struggle/ brain/ api/ test_*.py` | empty |
| 12 | 회귀 7종 무영향 (logical) | grep `land_climate` test 파일 import | 0 매치 |

12종 모두 PASS 시 `results/impl.result.md` 종합란에 "PASS — 4 finding 보강 완료, commit 가능" 표기. 실패 항목이 있으면 STOP_FOR_USER + 원인 분석 보고.

## §1.0 caveat 재확인

본 hotfix 4종 변경에서:
- 분위수 임계값 freeze: 본 hotfix는 *값*을 freeze하지 않음 (collector parameters / window 길이는 매개변수화)
- mechanism 결합 수식: 본 hotfix에 mechanism 함수 0건 (raw probe 산출 + raw NaN 차단 + 라벨링 only)
- LandCell 본문 변경: 0건 (`physis/world.py` 무수정)
- climate dict 새 키 추가: 0건

→ §1.0 caveat 위반 0건 유지.

## Output 위치

- `subagent-runs/claude/phase17-phi1-land-climate-hotfix-2026-05-07/results/impl.result.md` (변경 파일 + 검증 결과 + finding 매핑)
- 변경된 파일은 working tree에 직접 (gitignore 영역 외)

## 안전 한계

- writable boundary 내 5 파일 + 본 evidence dir 외 수정 금지
- LandCell / `physis/world.py` 무수정 (본 hotfix 범위 외)
- `physis/land_climate_telemetry.py` 무수정 (spec §5 본문 동결)
- 기존 산출 `probe.json` / `distribution.json` 재기록은 OK (collector + extractor 재실행 결과)
- 12종 검증 전부 PASS 못하면 STOP_FOR_USER 보고

## 완료 신호

`results/impl.result.md` 작성 완료 + 12 검증 PASS 시 본 sub-implementer 종료. 메인 컨텍스트는 evidence 검증 후 통합 commit 진입.
