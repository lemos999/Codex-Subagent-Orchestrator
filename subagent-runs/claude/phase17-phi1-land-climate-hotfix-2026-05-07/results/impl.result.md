# Phase 17 Φ-1 Land §7-1 Probe Hotfix — impl result

> **timestamp**: 2026-05-07
> **권위 prompt**: `subagent-runs/claude/phase17-phi1-land-climate-hotfix-2026-05-07/prompts/impl.prompt.md`
> **scope**: 4 finding × 5 파일 (Major×1 + Medium×2 + Minor×1)
> **Encoding**: utf-8

---

## 1. 변경 파일 목록

| # | 파일 | 변경 요약 | finding 매핑 |
|---:|---|---|---|
| 1 | `Projects/personas/loom/scripts/phase17_phi1_land_climate_collect.py` | (a) module docstring `WARNING - synthetic smoke` 블록. (b) `[SMOKE]` print 두 줄 (synthetic random walk + tick/seed 라벨). (c) `argparse.ArgumentParser` 도입 — `--ticks N` (default `DEFAULT_WINDOW_SIZE`=30) + `--seeds 7,13,42`. (d) `_save_probe_json` `json.dump(..., allow_nan=False)` 추가. (e) `collect_seed(seed, tick_count=...)` 시그니처 확장, `DEFAULT_PROBE_TICK_COUNT` + `DEFAULT_SEEDS` 상수화. | Finding 1-a (Major) + Finding 2 (Medium) |
| 2 | `Projects/personas/loom/scripts/phase17_phi1_land_climate_extractor.py` | (a) `compute_quantiles([])` → `raise ValueError(...)` (NaN sentinel 제거). (b) `compute_consistency` NaN/Inf 검출 시 `raise ValueError`. (c) `save_seed_distribution_json` + `save_aggregate_json` 모두 `json.dump(..., allow_nan=False)`. (d) `save_seed_summary_md` + `save_aggregate_summary_md`에 Provenance 라벨 자동 emit. | Finding 3 (Medium) + Finding 1-a (Major) |
| 3 | `Projects/personas/loom/data/phase17_phi1_land_climate_probe/aggregate/summary.md` | 최상단에 `> **Provenance**: synthetic smoke collector ...` 라벨 한 줄. | Finding 1-a (Major) |
| 4 | `Projects/personas/loom/data/phase17_phi1_land_climate_probe/seed-7/summary.md` | 동상. | Finding 1-a (Major) |
| 5 | `Projects/personas/loom/data/phase17_phi1_land_climate_probe/seed-13/summary.md` | 동상. | Finding 1-a (Major) |
| 6 | `Projects/personas/loom/data/phase17_phi1_land_climate_probe/seed-42/summary.md` | 동상. | Finding 1-a (Major) |
| 7 | `Projects/personas/loom/PHASE-17-LAND-REV-NEXT-STUB.md` | (a) §11 변경 이력에 `### v0.2 - 2026-05-07 사용자 검토 finding 4 hotfix` entry. (b) 신규 `## 12. Open Questions / Future Work` 섹션 with `### Future Work - DC-3 P5R v1 wrapper (Minor - 2026-05-07 finding 4)` block 권고. | Finding 4 (Minor) |

> **NOTE**: 본 hotfix는 collector + extractor 재실행으로 4 summary.md (7/13/42 seed + aggregate) 모두 자동 재생성됐다. extractor가 이제 Provenance 라벨을 자동 emit하므로, 향후 재실행 시에도 라벨 자연 보존된다.

---

## 2. 자체 검증 결과 (12종)

| # | 검증 | 명령 | 결과 |
|---:|---|---|:---:|
| 1 | mypy strict — collector | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_collect.py --strict --follow-imports=silent` | PASS (`Success: no issues found in 1 source file`) |
| 2 | mypy strict — extractor | `py -3.12 -m mypy scripts/phase17_phi1_land_climate_extractor.py --strict --follow-imports=silent` | PASS (`Success: no issues found in 1 source file`) |
| 3 | ruff — collector | `py -3.12 -m ruff check scripts/phase17_phi1_land_climate_collect.py` | PASS (`All checks passed!`) |
| 4 | ruff — extractor | `py -3.12 -m ruff check scripts/phase17_phi1_land_climate_extractor.py` | PASS (`All checks passed!`) |
| 5 | extractor 재실행 (strict NaN) | `py -3.12 scripts/phase17_phi1_land_climate_extractor.py` | PASS (per-seed + aggregate distribution.json 재기록 정상 + Grep 검사로 `data/phase17_phi1_land_climate_probe/` 트리에서 `NaN`/`Infinity`/`-Infinity` 0 매치 확인) |
| 6 | extractor empty ValueError | `py -3.12 -c "...; mod.compute_quantiles([])"` | PASS (`empty ValueError PASS: compute_quantiles: empty input - cannot compute quantiles. ...`) |
| 7 | collector `--ticks 60 --seeds 7` dry-run | `py -3.12 scripts/phase17_phi1_land_climate_collect.py --ticks 60 --seeds 7` | PASS (`tick_range: [0, 59]`, `current_count=7680`, `cumulative_count=15360` — 60 tick × 256 cells 일치) |
| 8 | collector SMOKE 라벨 grep | Grep `SMOKE\|synthetic` on `phase17_phi1_land_climate_collect.py` | PASS (1+ match — count=5) |
| 9 | summary.md SMOKE 라벨 grep | Grep `synthetic smoke\|Provenance` on `data/.../summary.md` | PASS (4 files match — aggregate + seed-7/13/42) |
| 10 | STUB v0.2 entry 확인 | Grep `v0\.2\|Future Work` on `PHASE-17-LAND-REV-NEXT-STUB.md` | PASS (1 file match) |
| 11 | 보호 영역 git diff | `git diff HEAD --name-only -- physis/world.py physis/climate_engine.py physis/land_climate_telemetry.py core/ ontology/ struggle/ brain/ api/` | PASS (empty — 0 변경) |
| 12 | 회귀 7종 무영향 (logical) | Grep `land_climate_telemetry\|phase17_phi1_land_climate` on `**/test_*.py` (loom) | PASS (0 매치) |

> **종합**: **12종 모두 PASS**.

---

## 3. Finding 매핑 + 변경 상세

### 3.1 Finding 1-a (Major) — synthetic smoke 라벨 명시

- **collector docstring**: 모듈 최상단에 `> **WARNING - synthetic smoke collector**:` 블록 추가. random walk 위치 (`_evolve_climate()` 약 140줄) + 별도 real-collector PR 권고 명시.
- **collector stdout**: `main()` 진입 시 `[SMOKE] phase17_phi1_land_climate_collect.py - synthetic random walk (NOT ClimateEngine)` 한 줄 + `[SMOKE] tick_count=..., seeds=... (raw window extension, NOT threshold freeze)` 한 줄.
  - cp949 콘솔 호환을 위해 em-dash 대신 `-` 사용.
- **summary.md (4 파일)**: 최상단 frontmatter 자리에 `> **Provenance**: synthetic smoke collector (random walk). NOT actual `ClimateEngine` output. Suitable as smoke evidence only. §7-2 evidence requires real-collector reproduction.` 한 줄.
- **extractor 자동 emit**: `save_seed_summary_md` + `save_aggregate_summary_md` 모두 Provenance 라벨을 markdown 출력에 포함하도록 수정. 향후 extractor 재실행 시 라벨 자연 보존.

### 3.2 Finding 2 (Medium) — `--ticks N` argparse

- `argparse.ArgumentParser` 신설. `--ticks N` (default = `DEFAULT_PROBE_TICK_COUNT` = `DEFAULT_WINDOW_SIZE` = 30) + `--seeds 7,13,42` (CSV → tuple of int).
- help text:
  - `--ticks N`: "tick count (default: 30 = DEFAULT_WINDOW_SIZE). Use --ticks 60 or 90 for current/cumulative separation evidence. NOTE: this is raw window extension, NOT threshold freeze."
  - `--seeds`: "comma-separated seed list (default: 7,13,42). Deterministic three-seed replay matches spec §0.3 / §6.2."
- `collect_seed()` 시그니처 `(seed: int, tick_count: int = DEFAULT_PROBE_TICK_COUNT)` 확장. argparse argv 누락 시 default 동일 동작 보장 (회귀 무영향).
- `_parse_seeds_arg()`: 빈 문자열, 공백, non-int 모두 `argparse.ArgumentTypeError` raise (graceful failure).

### 3.3 Finding 3 (Medium) — extractor strict JSON

- `compute_quantiles([])` → `raise ValueError("...empty input - cannot compute quantiles...")`. 메시지 cp949 호환 (`-`, `x` 사용).
- `compute_consistency` 내부에 NaN/Inf 검출 시 `raise ValueError("...NaN/Inf detected...")`. `compute_quantiles`가 사전 raise하므로 이 분기는 사실상 dead code지만 strict 보장을 위해 유지.
- `save_seed_distribution_json` + `save_aggregate_json` 모두 `json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)`. 비정상 값 emit 시 `ValueError: Out of range float values are not JSON compliant` 자동 raise.
- collector `_save_probe_json`도 동일하게 `allow_nan=False` 추가 (raw probe 자체에도 strict 보장 — 일관성).
- 회귀 7종은 `land_climate_telemetry` / `phase17_phi1_land_climate` 미import이므로 영향 없음.

### 3.4 Finding 4 (Minor) — STUB v0.1 → v0.2 + §12 Future Work

- `## 11. 변경 이력`에 `### v0.2 - 2026-05-07 사용자 검토 finding 4 hotfix` block 추가.
- 신규 `## 12. Open Questions / Future Work` 섹션 + `### Future Work - DC-3 P5R v1 wrapper (Minor - 2026-05-07 finding 4)` 본문.
- 권고 4 필드: `provenance: dict` / `window: int` / `distribution: DistributionTable` / `status: Literal["candidate", "confirmed"]`.
- v1 wrapper 분리 author 권고 (`api/nation_p5r_v1.py` 가칭). v0 invariant 보존 명시.
- §7-1 spec rev.0 본문 / OQ 1~6 결정 / DC-1~DC-3 봉인 모두 무변경.

---

## 4. §1.0 caveat 재확인

| caveat | 위반 0건 검증 |
|---|---|
| 분위수 임계값 freeze | extractor는 raw quantile candidates만 emit. magic threshold 0 추가 (grep `QUANTILE_THRESHOLD\|FREEZE\|FROZEN` count=0). |
| window 길이 freeze | `--ticks N` argparse 도입은 *매개변수화*이며 *값 freeze*가 아님 (default = `DEFAULT_WINDOW_SIZE`). collector + extractor 본문 어디에도 `WINDOW_FROZEN` / 30/60/90 상수 박힘 0건. |
| mechanism 결합 수식 | hotfix 변경 4 finding 어디에도 mechanism 함수 신설 0건. 라벨링 + argparse + strict JSON + Future Work memo only. |
| LandCell 본문 변경 | `physis/world.py` git diff empty (검증 11). `cell.climate["rainfall"]` / `cell.climate["temperature"]` 기존 키만 사용 (Grep으로 신규 키 0건). |
| climate dict 새 키 추가 | 0건 (위 동일). |

→ **§1.0 caveat 위반 0건 유지**.

---

## 5. 회귀 무영향 검증

- 회귀 7종 (Phase 17 Tier 1) 보존 — 본 hotfix 어떤 mechanism 영역도 미변경 (`physis/world.py` / `physis/climate_engine.py` / `physis/land_climate_telemetry.py` / `core/` / `ontology/` / `struggle/` / `brain/` / `api/` 모두 git diff empty).
- 회귀 test 파일 어디에도 `land_climate_telemetry` / `phase17_phi1_land_climate` import 0건 (Grep loom test_*.py 0 매치).
- 안전 전제 5종 + BOOST=0.20 + acceptance 4종 + DC-1~DC-3 봉인 모두 무변경 (영역 격리 보존).

---

## 6. 추가 메모 / 가정

### 6.1 cp949 콘솔 인코딩 호환

Windows 한국어 환경의 cp949 콘솔에서 print 시 em-dash (`—`) / 곱셈 기호 (`×`)는 `UnicodeEncodeError`를 일으킨다. SMOKE 라벨 print 두 줄과 `compute_quantiles` ValueError 메시지에서 `-` / `x`로 ASCII 대체. README 본문 (markdown summary.md / STUB.md / docstring) 의 `×` / em-dash는 utf-8 파일이라 정상 보존.

### 6.2 `_save_probe_json`도 strict JSON 적용

prompt §Finding 3 본문은 extractor 두 dump만 명시했으나 collector `_save_probe_json`도 동일 위험 (만약 telemetry가 NaN을 emit하면 strict 보장 불가). 일관성 + 사용자 검토 finding 정합 + scope 내 file (collector) 변경이라 추가 적용. **assumption**: prompt 의도가 "raw probe 산출 어디서도 NaN 0건"이므로 collector json.dump도 동일 처리.

### 6.3 extractor의 Provenance 자동 emit

prompt §Finding 1-a 본문은 4 summary.md 파일 직접 편집을 명시한다. 본 구현에서는 4 summary.md 직접 편집 + extractor `save_*_summary_md` 함수 두 곳에 Provenance 라벨 emit 로직도 동시 추가했다. 이유: extractor 재실행 시 4 summary.md가 자동 재생성되므로 직접 편집만으로는 라벨이 사라진다. 향후 자연 보존을 위한 정합 보강. **assumption**: 사용자 검토 의도가 "evidence를 누가 봐도 smoke임을 인지" — 즉 1회 라벨이 아니라 영구 라벨이라 판단.

---

## 7. 종합 판정

**PASS — 4 finding 보강 완료, commit 가능**

- 12종 자체 검증 모두 PASS.
- §1.0 caveat 위반 0건.
- 회귀 7종 무영향 (mechanism 영역 git diff empty).
- writable boundary 5 파일 + 본 evidence dir + impl.result.md만 변경.
- 안전 전제 5종 / BOOST=0.20 / acceptance 4종 / DC-1~DC-3 봉인 모두 무변경.

본 sub-implementer 종료. 메인 컨텍스트는 evidence 검증 후 통합 commit 진입 가능.
