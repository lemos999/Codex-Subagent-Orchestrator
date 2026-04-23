# Phase 17 Φ-2 Faction — 창발 관찰 Probe 지시서

> 긴급도: 중간
> 선행 조건: Phase 17 Φ-2 Faction 구현 완료 (v3 지시서 이행, `PHASE-17-FACTION-DECISIONS.md` v4 메모까지 반영)
> 작업 유형: 혼합 (관측 스크립트 신규 + 회귀 테스트 1건 추가)
> DB migration: 없음
> 외부 의존: 없음 (기존 loom 런타임 재사용)

---

## 0. 목표 3계층 (loom 불변 원칙)

- **궁극 목적 (loom 전체)**: 페르소나의 삶 → 유대 → 갈등 → 주권 선언이라는 인과 사슬로 국가가 자연 탄생. Top-down 선언 금지.
- **Phase 17 목적**: 자연 탄생의 4단계 인과 사슬. Φ-1 Land → **Φ-2 Faction** → Φ-3 Struggle → Φ-4 Nation.
- **현재 작업의 고유 역할**: Φ-2 Faction 구현이 "규칙으로 선언"이 아니라 "창발을 만들어냈는가"를 데이터로 확증 + D9 SNN 주입 적응안이 Phase 14-B 경제 readout을 훼손하지 않음을 회귀 테스트로 잠금. Φ-3 Struggle 진입을 위한 재료(`factions_in_contact`, wealth gini, grievance 공유) 충분성 측정.

---

## 1. 배경

Phase 17 Φ-2 Faction 구현(v3 지시서 기준)이 완료됐다. Codex 적용 후 Claude 리뷰에서 확증된 항목:

- D1~D11 계약 전부 이행 (`test_phase17_faction.py` 12 테스트 통과)
- SSoT `_change_persona_faction` + AST whitelist 통과 (core/ontology/physis/brain 전수 스캔)
- Handoff API 7종 구현 (`faction_population_distribution`, `factions_in_contact`, `faction_wealth_distribution`, `faction_social_matrix`, `faction_grievance_targets`, `faction_charter_primitives`, `faction_territory_distribution`)
- D9 적응 (`multi_tick_engine.py:419-424`): `brain.snn.v[faction_idx] += faction_input[faction_idx]` — brain 수정 금지 제약 하에 engine-side pre-bias로 구현. 계약 수준 test_d9 통과, 그러나 end-to-end SNN readout 회귀는 아직 미검증.

**검증되지 않은 것**:
1. 실제로 창발이 발생하는가? founder+charter만으로 faction 분화·접촉·grievance 공유가 일어나는가?
2. D9 적응(bias 0.05/0.03, 300~349 뉴런 co-fire)이 Phase 14-B 경제 readout을 침범하지 않는가?

이 두 물음에 답하지 않으면 Φ-3 Struggle로 진입할 수 없다 (SNN 창발 최우선 원칙).

---

## 2. 작업 범위

### [필수]
1. `Projects/personas/loom/observe_phase17_emergence.py` 신규 — seed 3개 × 5000틱 실행, 5개 지표 수집, JSONL 로그 + 요약 마크다운 생성
2. `Projects/personas/loom/test_phase14b_snn_integration.py` 기존 파일에 `test_phase14b_faction_bias_noise_bound` 테스트 함수 1건 추가
3. 출력 디렉토리 `Projects/personas/loom/data/phase17_probe/seed-{N}/` 자동 생성 — `metrics.jsonl`, `summary.md` 두 파일 생성

### [선택]
- matplotlib 그래프 출력 (summary.md 안에 ASCII 스파크라인이면 충분)
- `--quick` 플래그 (틱 500 스모크 모드)

### [금지]
- `multi_tick_engine.py` 수정 (관측만 목적)
- `ontology/layers.py` 수정
- `brain/*` 수정 (특히 `lif_network.py`, `persona_brain.py`)
- `readout_weights_v1.npy` 수정
- 기존 test_phase14b_snn_integration.py 테스트 케이스 변경 (신규 `test_phase14b_faction_bias_noise_bound` 추가만 허용)
- 기존 observe_phase15_stack.py 수정
- 지시서 범위 밖 faction 구현 "개선"/"리팩터링" 시도 (문제 발견 시 보고만)

---

## 3. 구체 사양

### 3.1 관측 스크립트: `observe_phase17_emergence.py`

#### 파일 위치
`Projects/personas/loom/observe_phase17_emergence.py`

(loom 루트 — `observe_phase15_stack.py`와 동일 convention)

#### CLI 인터페이스
```python
# 기본 실행 (seed 7, 13, 42 × 5000틱)
py observe_phase17_emergence.py

# 커스텀 seed
py observe_phase17_emergence.py --seeds 7,13,42

# 커스텀 tick
py observe_phase17_emergence.py --ticks 5000

# 스모크 (선택)
py observe_phase17_emergence.py --quick  # seed 42만, 500틱
```

`argparse` 사용. 기본값: `seeds=[7, 13, 42]`, `ticks=5000`.

#### 실행 뼈대 (참고 구조)
```python
import argparse, json, sys, time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.multi_tick_engine import MultiTickEngine

OUT_ROOT = Path(__file__).resolve().parent / "data" / "phase17_probe"

def run_seed(seed: int, ticks: int) -> dict:
    engine = MultiTickEngine(seed=seed)
    out_dir = OUT_ROOT / f"seed-{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "metrics.jsonl"
    summary_path = out_dir / "summary.md"

    with jsonl_path.open("w", encoding="utf-8") as jf:
        # tick-0 snapshot
        _dump_snapshot(jf, engine, tick=0)

        t0 = time.time()
        for t in range(1, ticks + 1):
            engine.tick()  # 또는 engine.run(n_ticks=1)
            _maybe_dump(jf, engine, tick=t)
        elapsed = time.time() - t0

    summary = _build_summary(engine, ticks, elapsed, jsonl_path)
    summary_path.write_text(summary, encoding="utf-8")
    return {"seed": seed, "elapsed": elapsed, "summary_path": str(summary_path)}
```

> **주의**: `engine.tick()`이 공개 API가 아니면 `engine.run(n_ticks=1, verbose=False)` 사용. 실제 시그니처는 구현 확인 후 결정.

#### 3.1.1 수집 지표 5종 (전부 JSONL 한 줄씩 기록)

##### M1. faction_population_distribution (분포 고착 vs 분화)
- **주기**: 매 100틱 (tick=0 포함)
- **데이터**: `engine.faction_population_distribution()` 반환값 그대로
- **JSONL 레코드**:
  ```json
  {"tick": 100, "type": "population", "data": {"F_001": 12, "F_002": 7, "F_003": 3}}
  ```
- **판정 근거**: 시간 경과에 따라 faction 수 증가 여부 + Gini-like concentration 변화

##### M2. factions_in_contact (Φ-3 진입 재료 충분성)
- **주기**: 매 100틱
- **데이터**: `engine.factions_in_contact(radius=1)` 반환값 (list[(fid_a, fid_b)])
- **JSONL 레코드**:
  ```json
  {"tick": 100, "type": "contact", "pairs": [["F_001", "F_002"]], "count": 1}
  ```

##### M3. faction_change source 비율 (drift 실제 발생 증거)
- **주기**: 매 1000틱마다 cumulative snapshot + 최종 전체 집계
- **데이터**: `engine.event_log` 에서 `type=="faction_change"` 필터링, `source` 필드별 카운트
  - `source` 값: `birth_founder`, `affiliation`, `drift`, `conflict` (4종, DECISIONS.md D2/D3 기준)
- **JSONL 레코드**:
  ```json
  {"tick": 1000, "type": "source_cumulative", "data": {"birth_founder": 3, "affiliation": 8, "drift": 2, "conflict": 0}}
  ```

##### M4. faction_wealth_distribution gini (계급 갈등 재료)
- **주기**: 매 500틱
- **데이터**: `engine.faction_wealth_distribution()` → faction별 `{total, mean, gini, top_decile_share}`
- **JSONL 레코드**:
  ```json
  {"tick": 500, "type": "wealth", "data": {"F_001": {"total": 1250.0, "gini": 0.34, "top_decile_share": 0.28}}}
  ```

##### M5. faction_grievance_targets 공유도 (봉기 재료)
- **주기**: 매 500틱
- **데이터**: `engine.faction_grievance_targets()` → `{fid: {lord_id: count}}`
- 추가 집계: **"같은 lord에 grievance를 가진 faction 쌍 수"** (cross-faction shared target count)
- **JSONL 레코드**:
  ```json
  {"tick": 500, "type": "grievance_targets", "raw": {"F_001": {"L_003": 5}}, "shared_pairs": 2}
  ```

#### 3.1.2 summary.md 포맷 (seed마다 1개)

```markdown
# Phase 17 Emergence Probe — seed {N}

## 실행 요약
- 틱: {TICKS}
- 시작 faction 수: {initial_count}
- 종료 faction 수: {final_count}
- 총 faction_change 이벤트: {total_events}
- 경과: {elapsed:.1f}s ({ms_per_tick:.1f}ms/tick)

## 분포 진화 (100틱 간격 샘플)
| tick | 활성 faction 수 | 최대 소속 인원 | 균등도 (H/Hmax) |
|------|----------------|----------------|------------------|
| 0    | 3              | 12             | 0.89             |
| 1000 | 4              | 10             | 0.92             |
| 5000 | 5              | 8              | 0.95             |

## Φ-3 재료: 접촉 쌍 추이
- tick 0: 0쌍
- tick 1000: 2쌍
- tick 5000: 4쌍
- **판정**: [PASS] if ≥1쌍 at tick 5000 else [FAIL]

## Source 비율 (누적)
| source | count | pct |
|--------|-------|-----|
| birth_founder | 3  | 14% |
| affiliation   | 15 | 68% |
| drift         | 4  | 18% |
| conflict      | 0  | 0%  |

**판정**: drift ≥ 5% → [PASS/FAIL]

## Wealth gini 추이
- tick 500: avg gini 0.24
- tick 2500: avg gini 0.31
- tick 5000: avg gini 0.37
- **경향**: [증가/정체/감소]

## Grievance 공유 (봉기 재료)
- tick 5000 기준: {shared_pairs} 쌍의 faction이 같은 lord를 grievance 대상으로 공유
- **판정**: [PASS] if ≥1쌍 else [N/A]

## 종합 판정
- [PASS/FAIL] 분화 발생 (최종 active faction 수 > 초기)
- [PASS/FAIL] 접촉 쌍 ≥ 1 (Φ-3 진입 가능)
- [PASS/FAIL] drift source ≥ 5% (bottom-up 재배치 실제 발생)
- [PASS/FAIL] wealth gini 증가 경향 (계급 재료 축적)

## 이상 징후 (있을 경우)
- 특정 tick에서 faction 수 급락 → event_log 스냅샷 첨부
```

#### 3.1.3 전체 스크립트 종료 시 — 최상위 summary

`Projects/personas/loom/data/phase17_probe/SUMMARY.md` 추가 생성 (모든 seed 통합):

```markdown
# Phase 17 Emergence Probe — 전체 요약

| seed | active_factions_end | contact_pairs_end | drift_ratio | gini_mean_end | verdict |
|------|---------------------|-------------------|-------------|---------------|---------|
| 7    | 5                   | 3                 | 18%         | 0.37          | PASS    |
| 13   | 4                   | 2                 | 12%         | 0.31          | PASS    |
| 42   | 6                   | 4                 | 22%         | 0.42          | PASS    |

**3 seed 전원 PASS 시 Φ-3 Struggle 진입 가능.**
```

#### 3.1.4 성능 제약
- 5000틱 × 3 seed 총 실행 < 30분 (기존 observe_phase15_stack.py 2000틱 기준 선형 스케일)
- 메모리: JSONL streaming write, 전체 metrics dict 누적 금지

### 3.2 회귀 테스트 추가: `test_phase14b_snn_integration.py`

#### 추가 위치
파일 말미에 함수 1개 추가 (기존 test 함수 변경 금지).

#### 테스트 목적
D9 적응 경로 `brain.snn.v[300:349] += FACTION_TELEMETRY_BIAS_OWN (0.05)` 및 `[325:349] += FACTION_TELEMETRY_BIAS_NEIGHBOR (0.03)` 가 **경제 readout** (Phase 14-B의 tax_burden/grievance 뉴런 readout)을 침범하지 않음을 확증.

#### 구현 골자

```python
def test_phase14b_faction_bias_noise_bound() -> None:
    """D9 faction bias가 경제 readout의 tax/grievance 신호를 오염시키지 않음 확증.

    계약:
    - faction 미활성 vs 활성 동일 경제 입력 하에서,
      brain._last_economic_input 의 뉴런 20~40 (tax/grievance) 영역 차이 < 0.01
    - 뉴런 300~349 영역은 bias만큼 차이 (정상 주입)
    """
    import copy
    from core.multi_tick_engine import MultiTickEngine
    from ontology.layers import Relationship, FACTION_TELEMETRY_BIAS_OWN

    # 기준: faction 없음
    engine_baseline = MultiTickEngine(seed=42)
    _, pid, lord_id = _first_resident(engine_baseline)
    rel = engine_baseline.relationships[Relationship(persona_a=pid, persona_b=lord_id).key()]
    rel.trust = 0.25
    engine_baseline.inners[pid].grievance = 0.7
    eco_baseline = _economic_input(engine_baseline, pid, grievance=0.7)

    # 실험: 같은 seed, 같은 pid에 faction 할당 (founder 경로)
    engine_faction = MultiTickEngine(seed=42)
    # faction 초기화가 일어나는 경로는 engine 생성자 호출만으로 _init_founder_seeds 결과 반영됨.
    # 확실성 위해 명시 호출:
    if hasattr(engine_faction, "_init_founder_seeds"):
        engine_faction._init_founder_seeds()
    # 동일 pid에 faction 강제 부여 (SSoT 우회 금지 → 공식 경로 사용):
    fid = next(iter(engine_faction.factions)) if engine_faction.factions else None
    if fid is None:
        # faction 없으면 테스트 무의미 — 스킵이 아닌 PASS (bias 자체가 없음)
        return
    engine_faction._change_persona_faction(pid, fid, source="affiliation")
    rel2 = engine_faction.relationships[Relationship(persona_a=pid, persona_b=lord_id).key()]
    rel2.trust = 0.25
    engine_faction.inners[pid].grievance = 0.7
    eco_faction = _economic_input(engine_faction, pid, grievance=0.7)

    # 1. 경제 뉴런 영역 (20~40: grievance/tax_burden) 차이 < 0.01
    eco_diff = float(np.abs(eco_baseline[20:40] - eco_faction[20:40]).max())
    assert eco_diff < 0.01, f"economic neurons contaminated by faction bias: diff={eco_diff}"

    # 2. faction 뉴런 영역 (300~324: own bias) 차이 ≈ FACTION_TELEMETRY_BIAS_OWN
    own_diff = float((eco_faction[300:325] - eco_baseline[300:325]).mean())
    assert own_diff >= FACTION_TELEMETRY_BIAS_OWN * 0.5, \
        f"own bias not applied: diff={own_diff}"
```

#### 실행 검증
```bash
cd Projects/personas/loom && py -m pytest test_phase14b_snn_integration.py::test_phase14b_faction_bias_noise_bound -v
# 기존 테스트 회귀 확인:
cd Projects/personas/loom && py -m pytest test_phase14b_snn_integration.py -v
```

**기존 테스트 T1~T5 전원 PASS + 신규 T6 PASS가 승인 조건**.

### 3.3 에러/예외 케이스

| 상황 | 스크립트 동작 |
|------|-------------|
| `data/phase17_probe/seed-7/` 디렉토리 이미 존재 | 덮어쓰기 (overwrite, `mkdir(parents=True, exist_ok=True)`) |
| engine.tick()/run() 도중 예외 | 예외 그대로 raise + 부분 metrics.jsonl 보존 (flush 보장) |
| faction 생성 안 됨 (factions 빈 채로 5000틱) | summary.md에 `[WARN] no factions emerged` 기록 + verdict = FAIL |
| 한 seed 실행 실패 | 다음 seed 실행 계속 (isolate), 최상위 SUMMARY.md에 seed별 성공/실패 기록 |

---

## 4. 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/observe_phase17_emergence.py` | 신규 | 추가 |
| `Projects/personas/loom/test_phase14b_snn_integration.py` | `test_phase14b_faction_bias_noise_bound` 함수 1건 추가 (말미) | 수정 |
| `Projects/personas/loom/data/phase17_probe/seed-{7,13,42}/metrics.jsonl` | 실행 결과물 | 생성 |
| `Projects/personas/loom/data/phase17_probe/seed-{7,13,42}/summary.md` | 실행 결과물 | 생성 |
| `Projects/personas/loom/data/phase17_probe/SUMMARY.md` | 실행 결과물 | 생성 |

**변경 없음 (금지)**:
- `Projects/personas/loom/core/multi_tick_engine.py`
- `Projects/personas/loom/ontology/layers.py`
- `Projects/personas/loom/brain/**`
- `Projects/personas/loom/physis/**`
- `Projects/personas/loom/data/models/readout_weights_v1.npy`
- 기존 `test_phase14b_snn_integration.py`의 T1~T5 테스트 함수 (신규 추가만 허용)

---

## 5. 검증

### 5.1 기계 검증 (항상)
```bash
# Python 구문/타입 (loom은 mypy가 선택)
cd Projects/personas/loom && py -m ruff check observe_phase17_emergence.py
cd Projects/personas/loom && py -m py_compile observe_phase17_emergence.py

# 기존 테스트 회귀
cd Projects/personas/loom && py -m pytest test_phase14b_snn_integration.py -v
cd Projects/personas/loom && py -m pytest test_phase17_faction.py -v

# 신규 테스트 단독
cd Projects/personas/loom && py -m pytest test_phase14b_snn_integration.py::test_phase14b_faction_bias_noise_bound -v
```

### 5.2 기능 검증 (창발 관찰)
```bash
# 스모크: seed 42, 500틱 (< 3분)
cd Projects/personas/loom && py observe_phase17_emergence.py --quick

# 정식: seed 7, 13, 42 × 5000틱 (< 30분)
cd Projects/personas/loom && py observe_phase17_emergence.py
```

체크리스트:
- [ ] 3 seed 전부 완주 (예외 없이)
- [ ] 각 seed별 `metrics.jsonl` 존재 + 라인 수 > 100 (100틱 간격 샘플링 × 5000틱 = 약 250줄)
- [ ] 각 seed별 `summary.md` 존재 + 종합 판정 4개 명시
- [ ] 최상위 `SUMMARY.md` 존재 + 3 seed 집계 표
- [ ] 3 seed 중 최소 2개에서 "분화 발생" PASS
- [ ] 3 seed 중 최소 1개에서 "접촉 쌍 ≥ 1" PASS

### 5.3 계약 검증 (D9 회귀 안전)
- [ ] `test_phase14b_faction_bias_noise_bound` PASS (경제 뉴런 20~40 차이 < 0.01)
- [ ] 기존 Phase 14-B T1~T5 전원 PASS (회귀 없음)
- [ ] 기존 Phase 17 faction 12 테스트 전원 PASS

### 5.4 보고 형식

Codex는 실행 완료 후 다음 내용을 **한 번에** 사용자에게 보고:

```markdown
## Phase 17 Emergence Probe — 실행 결과

### 파일 변경
- observe_phase17_emergence.py: 신규 (N LOC)
- test_phase14b_snn_integration.py: +1 함수 (M LOC)

### 검증 통과
- [x] ruff check pass
- [x] py_compile pass
- [x] test_phase14b 기존 T1~T5 PASS
- [x] test_phase14b_faction_bias_noise_bound PASS (신규)
- [x] test_phase17_faction 12 PASS

### 창발 관찰 요약
| seed | active_factions_end | contact_pairs_end | drift_ratio | gini_mean_end | verdict |
|------|---------------------|-------------------|-------------|---------------|---------|
| 7    | ...                 | ...               | ...         | ...           | ...     |
| 13   | ...                 | ...               | ...         | ...           | ...     |
| 42   | ...                 | ...               | ...         | ...           | ...     |

### 판정
- Φ-3 진입 가능 여부: [YES/NO] — 근거: ...
- D9 readout 회귀 안전: [YES/NO] — eco_diff 최대치: ...

### 이상 징후 (있을 경우)
- ...
```

---

## 6. Rollback

```bash
# 스크립트 삭제
rm Projects/personas/loom/observe_phase17_emergence.py

# 테스트 회복 — 신규 함수만 제거 (T1~T5 유지)
# Edit: test_phase14b_snn_integration.py 에서 test_phase14b_faction_bias_noise_bound 함수 제거

# 데이터 디렉토리 삭제 (선택)
rm -rf Projects/personas/loom/data/phase17_probe/
```

**Rollback 영향**: 없음 (Phase 17 구현 자체는 손대지 않으므로 기능 롤백 불필요).

---

## 7. Invariants (구현 에이전트가 **반드시** 지킬 것)

1. **Engine 내부 SSoT 우회 금지**: 테스트에서 persona faction 할당 시 `persona.faction = X` 직접 쓰기 대신 `engine._change_persona_faction(pid, fid, source="affiliation")` 사용
2. **readout_weights_v1.npy 불변**: 어떤 경우에도 이 파일을 읽기 전용 이상으로 취급 금지
3. **brain/** 수정 금지**: Phase 14-B 계약이 이 벽에 의존 ("PersonaBrain.tick(economic_state=...)" signature 불변)
4. **JSONL streaming**: 5000틱 × 3 seed = metrics를 메모리에 전부 올리지 말 것. 각 sample 즉시 write + flush
5. **Seed 결정성**: 같은 seed로 재실행하면 summary.md의 숫자가 동일해야 함 (시간 기반 난수 사용 금지 — `random.seed(seed)`, `np.random.seed(seed)` 등은 `MultiTickEngine(seed=...)` 내부에서 처리되므로 스크립트는 그 밖 난수 호출 금지)
6. **범위 엄수**: 스크립트가 faction 구현의 버그를 발견해도 **수정 금지, 보고만**. 이 지시서는 관측/회귀 테스트 한정
7. **Windows 경로**: Path(__file__).resolve() 기반 상대 경로만 사용. 하드코딩 `C:\...` 금지

---

## 8. 의도적 비결정

- `engine.tick()` 1틱 단위 외부 호출 API가 없다면: `engine.run(n_ticks=1, verbose=False)` 또는 `engine.run(n_ticks=100, verbose=False)` 반복 사용 — Codex 판단
- 스파크라인/그래프 형식 세부 (ASCII, JSON 등) — Codex 판단
- `--quick` 모드 유무 — 선택. 있으면 seed=42, ticks=500

---

## 9. GPT/Codex 전달용 한 문장

> loom 워크스페이스 `Projects/personas/loom/` 에서 `PHASE-17-FACTION-EMERGENCE-PROBE-SPEC.md` 를 **그대로** 따라 `observe_phase17_emergence.py` 스크립트를 신규 작성하고 `test_phase14b_snn_integration.py` 에 regression case 1건 추가한 뒤, 3 seed × 5000틱 실행 결과물과 pytest 통과 여부를 리포트로 제출한다. multi_tick_engine/ontology/brain 수정 금지.
