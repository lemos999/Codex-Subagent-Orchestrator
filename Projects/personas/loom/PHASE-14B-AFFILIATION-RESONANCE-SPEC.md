> ## ⛔ REJECTED — DO NOT IMPLEMENT (2026-04-29)
>
> **본 spec은 외부 엔진 cross-check (`/discuss --quick`, 2/3 응답) 결과 기각되었습니다.**
>
> - **합의**: axis A는 Phase 17 hotfix v1에서 제거된 거짓 보정 5건과 **구조적 동형**. acceptance #2 PASS를 목적으로 설계된 **역공학 조건**.
> - **근본 원인**: Case C의 진짜 병목은 **후기 tick에서 active_factions=1로 수렴하는 collapse 자체**. affiliation dampen이 아니라 collapse 트리거 진단이 선행되어야 함.
> - **다음 작업**: `PHASE-17-CASE-C-COLLAPSE-DIAGNOSIS-SPEC.md`로 이관. 진단 결과 후 territory cross-propagation 강화 또는 다른 차원 검토.
> - **Evidence**: [subagent-runs/discuss/phase14b-a-cross-check-2026-04-28-quick/](../../subagent-runs/discuss/phase14b-a-cross-check-2026-04-28-quick/run-summary.md)
> - **위반 위험 원칙 (commit 시)**: `feedback_snn_emergence_first.md`("규칙 < 창발") + `feedback_root_cause_first.md`("표면 해결 금지") 양쪽
>
> **본 문서는 의사결정 기록 보존 목적으로 유지되며, 향후 Codex 또는 구현자가 이 spec을 따르면 안 됩니다.**

---

# Phase 14B-A — Affiliation Drift Lord-Faction Dampen Spec (axis A only) [REJECTED]

> 긴급도: ~~높음~~ → 기각
> 선행 조건: Phase 14 propagation 구현 (commit f48cfd0 이후 Phase 14 Codex 결과) + Φ-3 hotfix v1 (a8d61e7 → 8a00768 → 6a29d2e)
> 작업 유형: ~~기능 (loom core mechanism — affiliation drift score 단일 메서드 보강)~~ → 기각된 설계 기록
> DB migration: 없음
> 외부 의존: 없음
> 분리 정책: **axis A 단독 적용**. axis B (uprising target grievance 분기) / axis C (uprising trigger 인접 완화)는 본 spec **범위 외**, axis A 자연 측정 결과에 따라 후속 검토 (§11)

---

## 1. 배경

### 1.1 3계층 목표 (loom 정신 명시)

본 spec은 다음 3계층 목표 안에서 작동한다 (`feedback_loom_goal_first.md`):

- **궁극 목표**: 자율 사회 시뮬 + **SNN 창발**(규칙 < 창발) + **PersonaBrain 논문 출판**
- **Phase 17 목적**: 사회 **자연 발생** (top-down 선언 금지). Φ-1 Land → Φ-2 Faction → Φ-3 Struggle → Φ-4 Nation 인과 사슬
- **본 spec 고유 역할**: Phase 14 propagation이 lord_id를 cross-territory로 전파한 후, 그 lord_id가 affiliation 결정에 자연 반영되는 의미론 결합 채널을 추가. **SNN anger 뉴런(chiljeong[1])을 자연 게이트로 활용**하여 "규칙으로 차단" 아닌 "분노가 충분할 때만 자연 활성"하는 mechanism. SNN 창발 정신 직접 적용.

### 1.2 측정된 결손

Phase 14 propagation 구현 후 자연 측정 (`data/phase17_probe_phi3-phase14-resonance/SUMMARY.md`):

| # | acceptance | seed 7 | seed 13 | seed 42 | 결과 |
|---|------------|:------:|:-------:|:-------:|:----:|
| 1 | uprising_event ≥ 1 | 13 | 11 | 16 | PASS |
| 2 | grievance_pairs_end ≥ 1 | 0 | 0 | 0 | **FAIL** |
| 3 | dom_share_end ≥ 0.50 | 100% | 100% | 50% | PASS |

진단 (Phase 14 Codex 보고 §5):
- 중간 tick 500/1000/2000에서 `pairs=1` 발생 (propagation 작동)
- tick 3000~5000에서 `active_factions_end=1`로 collapse → 모든 pair 소멸

### 1.3 근본 원인 추적 (꼬리에 꼬리, `feedback_root_cause_first.md`)

```
표면: pair=0
↓ 왜?
active_factions_end=1 (단일 faction 수렴)
↓ 왜?
모든 페르소나가 한 faction에 흡수됨
↓ 왜?
affiliation drift score 계산이 grievance signal을 일부만 반영
  (`_shared_grievance` 동조 클러스터 bonus는 있으나,
   "내가 원망하는 lord의 faction에 대한 dampen"은 없음)
↓ 왜?
grievance ↔ affiliation 의미론 결합이 단방향 (동조 bonus만 있고 적대 dampen 없음)
↓ 근본
**grievance ↔ affiliation 의미론 결합 부재** (적대 dampen 누락)
```

### 1.4 본 spec의 인과 가설 (acceptance #2 자연 PASS 정당화)

axis A (lord faction dampen) 단독 적용 시 기대 인과 사슬:

```
SNN anger fire ≥ gate인 페르소나
  → 자기 grievance 대상 lord의 faction에 대한 affiliation score 자연 dampen (≤1.0 곱셈)
  → 그 페르소나가 lord faction으로 흡수될 확률 감소
  → active_factions_end > 1 자연 유지 (단일 수렴 회피)
  → cross-faction lord_id 분포 자연 발생 (Phase 14 propagation 산출물 보존)
  → grievance_pairs_end ≥ 1 자연 응결
```

**본 가설은 dampen 강도(0.6)와 SNN gate(0.5)의 자연 측정 결과로 검증된다**. 측정 실패 시 §6 case 분기 정책 그대로 적용 (거짓 보정 절대 금지).

### 1.5 본 spec 범위 = axis A only

이전 PHASE-14B 통합안은 axis A·B·C 3축이었으나 sub-reviewer 검증 (`subagent-runs/claude/loom-phase14b-spec-validation-2026-04-28/`)에서 다음 risk가 식별되었다:

- axis B: leader↔target faction 멤버 grievance 비대칭 미처리 (Φ-4 무한 진동 risk)
- axis C: 검증 형식 거짓 FAIL + secondary metric strict assertion → commit 봉쇄 risk

**근본 원인 우선 원칙** (`feedback_root_cause_first.md`): axis A가 의미론 결합의 가장 깊은 빈틈 → **A부터 풀면 B·C 결손이 자동 해결될 가능성**. 측정 후 결정. axis B·C는 §11에서 후속 trigger 명시.

---

## 2. 작업 범위

### [필수]
1. `_compute_affiliation_tick`의 score 계산에 lord faction 자연 dampen 추가 (SNN anger gate, 곱셈 가중치)
2. `_faction_lord_ids` helper 신규 메서드 (≤ 15줄)
3. acceptance #2 자연 PASS 검증 (3 seed × 5000 tick, `grievance_pairs_end ≥ 1`)
4. 무파괴 9 보장 계승 (hotfix v1 + Phase 14)
5. 회귀 테스트 1건 추가 (axis A dampen 자연 작동 + anger gate 검증)
6. SSoT helper (`shared_grievance_pairs_count`) 그대로 사용 (수정 금지)

### [선택]
- Phase 14 상수 (`GRIEVANCE_PROPAGATE_TRUST_MIN=0.6`, `GRIEVANCE_DONOR_MIN=0.5`) 값 조정 (이번 spec 본문은 0.6/0.5 보존)

### [금지]
- `_change_persona_faction` 시그니처 수정
- `FactionChangeSource = Literal["birth_founder", "affiliation", "drift", "conflict"]` 4종 변경 (신규 source 금지)
- `PHASE17_FACTION_SSOT_WRITE` whitelist 5건 수정
- `_pick_uprising_target`, `_uprising_trigger`, `_emit_uprising`, `_uprising_tick`, `_spawn_branch_faction`, `_select_uprising_followers`, `_snn_uprising_signal_active` 직접 수정 (axis B·C는 본 spec 범위 외)
- SNN 뉴런 인덱스 300~349, `n_neurons` 변경
- `brain/**`, `ontology/snn**`, `ontology/persona_brain**` 수정
- Φ-3 신규 상수 5종 (`THETA_UPRISING`, `UPRISING_CHECK_INTERVAL`, `UPRISING_GRIEVANCE_DECAY`, `UPRISING_FOLLOWER_MAX`, `SNN_ANGER_FIRE_THRESHOLD`) **값** 변경
- Phase 14 상수 `GRIEVANCE_PROPAGATE_TRUST_MIN`, `GRIEVANCE_DONOR_MIN` **값** 변경
- `_propagate_grievance_lord_id_cross_territory` 본문 수정 (Phase 14 산출물 보존)
- `shared_grievance_pairs_count` 본문 수정 (SSoT 통합 보존)
- 다음 키워드 신규 도입: `sticky`, `_floor`, `_cache`, `previous_lord`, `prev_lord`, `hold_lord`, `_force_*`, `_artificial_*`, `collapse_branch_pressure`, `active_count_pressure`
- artificial injection / hard override / 결과 강제 (점수 직접 부여, 후보 강제 제거 등)
- 회귀 테스트 (`test_phase17_faction_handoff_contract.py`, Phase 14 신규 테스트 4건) 수정

---

## 3. 구체 사양

### 3.1 신규 상수 (`ontology/layers.py`, line 257 뒤 — Phase 14 상수 다음)

**현재 line 253~257 (참고용 인용):**
```python
# ── Phase 14 grievance resonance 보강 (2026-04-28) ──────────────────────
# Φ-3 hotfix v1 closure §6 주 finding 대응: cross-territory lord_id 자연 전파.
# 자기 territory grievance가 강하면 자기 lord 유지 (자연 가중치 비교).
GRIEVANCE_PROPAGATE_TRUST_MIN = 0.6
GRIEVANCE_DONOR_MIN = 0.5
```

**삽입 (line 258 빈 줄 다음, line 259 위치):**
```python

# ── Phase 14B-A affiliation drift dampen (2026-04-28) ─────────────────
# Φ-3 acceptance #2 자연 PASS — grievance ↔ affiliation 의미론 결합.
# 자기 grievance 대상 lord의 faction에 대한 score 자연 dampen.
# SNN anger fire가 gate 임계 이상일 때만 자연 활성화 (창발 채널, hard 차단 아님).
# 직접 점수 강제 / 후보 강제 제거 / sticky / cache 패턴 절대 금지.
GRIEVANCE_LORD_FACTION_DAMPEN = 0.6   # score 곱셈 (≤1.0). 0이면 제거 의미라 금지
SNN_ANGER_AFFILIATION_GATE = 0.5      # chiljeong[1] anger fire rate 임계 (gate 활성화 조건)
```

**상수 값 정당화** (sub-reviewer MAJOR-A-1 대응):
- `GRIEVANCE_LORD_FACTION_DAMPEN=0.6`: Phase 14 `GRIEVANCE_PROPAGATE_TRUST_MIN=0.6`과 같은 값을 의도적으로 채택 (의미론적 일관성 — "신뢰 0.6 미만이면 lord_id propagation, score 0.6 곱셈으로 dampen"). 0.5 미만이면 거의 제거 효과 → hard 차단 risk. 0.7 초과면 dampen이 너무 약해 흡수 회피 못함. 측정 후 §6 Case C 발생 시 0.5로 tune 후보
- `SNN_ANGER_AFFILIATION_GATE=0.5`: `SNN_ANGER_FIRE_THRESHOLD=0.6`보다 낮게 설정 — 봉기 발화에는 강한 anger(0.6) 필요하지만 affiliation drift에는 약한 anger(0.5)도 자연 반영. 점진적 채널

**금지 키워드 정적 검증** (Phase 14 §9.6 패턴 계승):
- 새 상수 본문 / 새 메서드 본문에 다음 단어 0건:
  ```bash
  grep -nE '\b(sticky|_floor|_cache|previous_lord|prev_lord|hold_lord|_force_branch|_force_dampen|collapse_branch_pressure|active_count_pressure)\b' \
      ontology/layers.py core/multi_tick_engine.py
  ```
  → 신규 추가 라인에 0 hits (기존 hits는 무관)

### 3.2 axis A — affiliation drift lord faction dampen (`core/multi_tick_engine.py`)

#### 3.2.1 신규 helper `_faction_lord_ids` (line 1175 빈 줄 자리)

**위치**: `_shared_grievance` 정의 (line 1176) **직전** 빈 줄(line 1175)에 삽입.

**삽입 코드** (정확히 이대로 추가):
```python

    def _faction_lord_ids(self, faction_id: str) -> set[str]:
        """Phase 14B-A: faction이 점유한 territory의 lord_id 집합. 의미론 결합용."""
        members = self._faction_members(faction_id)
        lord_ids: set[str] = set()
        for member in members:
            tid = member.territory
            if tid is None:
                continue
            territory = self.territories.get(tid)
            if territory is None or territory.lord_id is None:
                continue
            lord_ids.add(territory.lord_id)
        return lord_ids
```

**본문 길이**: 11줄 (헤더·docstring·return 포함, ≤ 15줄 충족).

#### 3.2.2 dampen 블록 삽입 (`_compute_affiliation_tick` 내)

**대상 메서드**: `_compute_affiliation_tick(self) -> None` (line 1207~1256)

**현재 line 1219~1252 (수정 대상 부분 발췌):**
```python
            for fid in sorted(self.factions):
                territory_weight = (
                    W_TERRITORY_SAME
                    if self._same_territory(persona, fid) > 0.5
                    else W_TERRITORY_DIFF
                )
                score = (
                    territory_weight
                    + W_TRUST * self._trust_density(persona, fid)
                    + W_GRIEVANCE * self._shared_grievance(persona, fid)
                    + W_PROXIMITY * self._spatial_proximity(persona, fid)
                )
                # v6: 규모 tax — 이번 틱 가산분에만 적용 (누적 decay 결과는 불변)
                size_ratio = len(self._faction_members_cache.get(fid, ())) / total_active
                if size_ratio > FACTION_SIZE_TAX_START:
                    excess = size_ratio - FACTION_SIZE_TAX_START
                    span = 1.0 - FACTION_SIZE_TAX_START
                    tax = max(FACTION_SIZE_TAX_MIN, 1.0 - excess / span)
                    score *= tax
                # Stage 3 B: minority persistence boost (2026-04-24)
                member_count = len(self._faction_members_cache.get(fid, ()))
                if 0 < member_count <= MINORITY_PERSISTENCE_MAX_MEMBERS:
                    if self._same_territory(persona, fid) > 0.5:
                        score += MINORITY_PERSISTENCE_BOOST
                # Stage 6 H-lite: founder lineage identity affinity (2026-04-26)
                if W_LINEAGE > 0 and persona.faction:
                    cur_faction = self.factions.get(persona.faction)
                    cand_faction = self.factions.get(fid)
                    if cur_faction and cand_faction:
                        lineage_a = set(cur_faction.founder_lineage) | {cur_faction.founder_pid}
                        lineage_b = set(cand_faction.founder_lineage) | {cand_faction.founder_pid}
                        overlap = len(lineage_a & lineage_b) / max(len(lineage_a), len(lineage_b), 1)
                        score += W_LINEAGE * overlap
                scored[fid] = DECAY * prev_scores.get(fid, 0.0) + score
```

**삽입 위치**: line 1251 (`scored[fid] = DECAY * prev_scores.get(fid, 0.0) + score`) **직전**.

**삽입 코드** (이전 Stage 6 H-lite 블록 다음 + scored[fid] 라인 직전):
```python
                # Phase 14B-A: grievance ↔ affiliation 의미론 결합 (2026-04-28)
                # 자기 grievance 대상 lord가 fid의 lord와 일치하면 score 자연 dampen.
                # SNN anger fire rate가 gate 임계 이상일 때만 활성화 (자연 채널, hard 차단 아님).
                p_inner = self.inners[pid]
                if p_inner.grievance_lord_id is not None and p_inner.grievance >= GRIEVANCE_MIN_SHARED:
                    anger_active = float(p_inner.chiljeong[1]) >= SNN_ANGER_AFFILIATION_GATE
                    if anger_active:
                        cand_lord_ids = self._faction_lord_ids(fid)
                        if p_inner.grievance_lord_id in cand_lord_ids:
                            score *= GRIEVANCE_LORD_FACTION_DAMPEN
```

**삽입 후 본문 길이**: `_compute_affiliation_tick` 50줄 → 60줄 (헤더·docstring 포함). 단일 메서드 ≤ 80 권장.

#### 3.2.3 자연 메커니즘 정당화

| 자연성 보장 | 구현 |
|-----------|------|
| dampen은 곱셈 (≤1.0). score를 0으로 만들지 않음 | `score *= GRIEVANCE_LORD_FACTION_DAMPEN` (0.6) |
| SNN anger fire rate < gate면 dampen 자연 비활성화 (창발 채널) | `if anger_active:` 게이트 |
| grievance_lord_id 미존재 시 graceful fallback (기존 동작) | `if p_inner.grievance_lord_id is not None` 가드 |
| 약한 grievance(< MIN_SHARED)는 dampen 회피 (강한 분노만 채널 활성화) | `and p_inner.grievance >= GRIEVANCE_MIN_SHARED` |
| artificial guard / hard 차단 아님 | 후보 제거 없음, 가산 없음, 곱셈만 |
| Phase 14 propagation 산출물(grievance_lord_id) 자연 활용 | `p_inner.grievance_lord_id` 직접 read (수정 없음) |

### 3.3 회귀 테스트 보강 (`test_phase17_acceptance.py`)

**기존 테스트 4건 (Phase 14 추가) 보존**:
- `test_grievance_pair_helper_ssot`
- `test_grievance_propagation_no_artificial_sticky`
- `test_grievance_propagate_natural_emergence`
- `test_phi3_grievance_pairs_resonate` (자연 측정 — 본 spec 적용 후 PASS 기대)

**추가 신규 테스트 1건** — `test_affiliation_lord_faction_dampen_natural`:

```python
def test_affiliation_lord_faction_dampen_natural() -> None:
    """Phase 14B-A axis A 검증.

    grievance_lord_id가 candidate faction의 lord와 일치 + SNN anger fire rate
    ≥ gate 임계일 때 affiliation score가 자연 dampen.

    artificial guard 아님 검증: anger < gate면 dampen 비활성화 (자연 채널).
    """
    from ontology.layers import (
        GRIEVANCE_LORD_FACTION_DAMPEN,
        SNN_ANGER_AFFILIATION_GATE,
        GRIEVANCE_MIN_SHARED,
    )

    # 헬퍼 _seed_persona_with_grievance_match는 페르소나 1·territory 1·lord 1 구성
    # 후 그 lord_id를 페르소나의 grievance_lord_id로 설정. faction 1개가 그
    # territory를 점유하도록 setup. 모두 정상 mechanism setup 범위 (artificial 아님).
    engine, pid, target_fid = _seed_persona_with_grievance_match(seed=7)

    # Case 1: anger high → dampen 자연 활성화
    engine.inners[pid].chiljeong[1] = SNN_ANGER_AFFILIATION_GATE + 0.1
    engine.inners[pid].grievance = GRIEVANCE_MIN_SHARED + 0.1
    engine._compute_affiliation_tick()
    score_high = engine.inners[pid].affiliation_scores.get(target_fid, 0.0)

    # Case 2: anger low → dampen 자연 비활성화 (gate)
    engine.inners[pid].chiljeong[1] = SNN_ANGER_AFFILIATION_GATE - 0.1
    engine._compute_affiliation_tick()
    score_low = engine.inners[pid].affiliation_scores.get(target_fid, 0.0)

    assert score_high < score_low, (
        f"anger ≥ gate 시 lord faction score 자연 dampen 필요. "
        f"high_anger={score_high:.4f}, low_anger={score_low:.4f}, "
        f"dampen_factor={GRIEVANCE_LORD_FACTION_DAMPEN}"
    )

    # Case 3: grievance < MIN_SHARED → dampen 자연 비활성화 (약한 분노 channel off)
    engine.inners[pid].chiljeong[1] = SNN_ANGER_AFFILIATION_GATE + 0.1
    engine.inners[pid].grievance = GRIEVANCE_MIN_SHARED - 0.05
    engine._compute_affiliation_tick()
    score_weak_grievance = engine.inners[pid].affiliation_scores.get(target_fid, 0.0)

    assert score_weak_grievance >= score_low * 0.99, (
        f"grievance < MIN_SHARED 시 dampen 비활성화 필요. "
        f"weak_grievance={score_weak_grievance:.4f}, low_anger={score_low:.4f}"
    )
```

**헬퍼 `_seed_persona_with_grievance_match(seed)`**:
- 위치: 같은 파일 상단 helper 영역
- 역할: 테스트용 minimal engine setup. 페르소나 1·territory 1·lord 1·faction 1 구성. 페르소나의 `grievance_lord_id = territory.lord_id` 설정. faction은 그 territory에 멤버 보유
- 모든 설정은 정상 engine API 호출 (artificial state injection 아님)
- ≤ 30줄 권장

---

## 4. 변경 파일

| # | 파일 | 작업 | 줄 변동 (대략) |
|---|------|------|:--:|
| 1 | `Projects/personas/loom/ontology/layers.py` | line 257 뒤 신규 상수 2개 + 코멘트 | +9 |
| 2 | `Projects/personas/loom/core/multi_tick_engine.py` | line 1175 helper + line 1251 직전 dampen 블록 | +20 |
| 3 | `Projects/personas/loom/test_phase17_acceptance.py` | 신규 테스트 1건 + 헬퍼 | +50 |

### 변경 없음 ([금지] 영역 — diff 0줄 보장 필수)

- `Projects/personas/loom/core/multi_tick_engine.py`:
  - `_change_persona_faction` (line 1053~)
  - `_pick_uprising_target` (line 1805~1831) ← axis B 범위 외
  - `_uprising_trigger` (line 1883~1925) ← axis C 범위 외
  - `_emit_uprising` (line 1928~1962)
  - `_uprising_tick` (line 1964~)
  - `_spawn_branch_faction` (line 1849~1881)
  - `_select_uprising_followers` (line 1833~1847)
  - `_snn_uprising_signal_active` (line 1791~1803)
  - `_propagate_grievance_lord_id_cross_territory` (line 2220~)
  - `shared_grievance_pairs_count` (line 1705~)
- `Projects/personas/loom/ontology/layers.py`:
  - `FactionChangeSource` Literal (line 92)
  - Phase 14 상수 (line 256~257) 값 변경 금지 (위치 보존)
  - Φ-3 상수 (line 247~251) 값 변경 금지
- `Projects/personas/loom/observe_phase17_emergence.py` (Phase 14에서 정리 완료. SSoT helper 호출 그대로)
- `Projects/personas/loom/test_phase17_faction_handoff_contract.py` (12건 회귀)
- `Projects/personas/loom/brain/**`, `ontology/snn**`, `ontology/persona_brain**` (SNN/PersonaBrain 무수정)

---

## 5. 검증

### 5.1 기계 검증 (필수, 모두 PASS)

```bash
cd Projects/personas/loom
py -m py_compile ontology/layers.py core/multi_tick_engine.py test_phase17_acceptance.py
py -m py_compile observe_phase17_emergence.py
```

### 5.2 정적 계약 검증 (필수, grep 0 hits)

```bash
cd Projects/personas/loom
# Phase 14B-A 신규 코드에 거짓 PASS 키워드 0건
grep -nE '\b(sticky|_floor|_cache|previous_lord|prev_lord|hold_lord|_force_branch|_force_dampen|collapse_branch_pressure|active_count_pressure)\b' \
    ontology/layers.py core/multi_tick_engine.py
# 결과: 신규 추가 라인에 0 hits

# 본문 길이 — Python AST로 검증 (awk 비정형 종결자 회피)
py -c "
import ast
src = open('core/multi_tick_engine.py', encoding='utf-8').read()
tree = ast.parse(src)
target = {'_faction_lord_ids', '_compute_affiliation_tick'}
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name in target:
        body_lines = node.end_lineno - node.lineno + 1
        print(f'{node.name}: {body_lines} lines')
"
# 결과:
# _faction_lord_ids: ≤ 15
# _compute_affiliation_tick: ≤ 80
```

(주: 이전 spec의 awk 명령은 `^    def [^_]` 종결 패턴이 언더스코어 시작 메서드에 매칭 실패하는 자기모순 risk. 본 spec은 Python AST로 정확 측정.)

### 5.3 무파괴 9 보장 검증

| # | 항목 | 검증 명령 |
|---|------|----------|
| 1 | `_change_persona_faction` 시그니처 | `git diff core/multi_tick_engine.py` 에서 line 1053~1066 변경 없음 |
| 2 | `FactionChangeSource` Literal 4종 | `grep -n 'FactionChangeSource = Literal' ontology/layers.py` 결과 변경 없음 |
| 3 | `# noqa: PHASE17_FACTION_SSOT_WRITE` 5건 | `grep -c 'PHASE17_FACTION_SSOT_WRITE' core/multi_tick_engine.py` → 5 |
| 4 | `Faction.grace_until_tick` | diff 없음 |
| 5 | `Faction.founder_lineage` | diff 없음 |
| 6 | `InnerWorld.residence_ticks` | diff 없음 |
| 7 | SNN 뉴런 300~349 / `n_neurons` | `git diff brain/ ontology/snn` 없음 |
| 8 | D10 7종 read-only API | diff 없음 |
| 9 | Φ-3 신규 상수 5종 **값** | `grep -E '(THETA_UPRISING\|UPRISING_CHECK_INTERVAL\|UPRISING_GRIEVANCE_DECAY\|UPRISING_FOLLOWER_MAX\|SNN_ANGER_FIRE_THRESHOLD)' ontology/layers.py` 값 변경 없음 |

### 5.4 회귀 테스트 (필수, 모두 PASS)

```bash
cd Projects/personas/loom
py test_phase17_faction_handoff_contract.py
# 12건 PASS

py -m pytest test_phase17_acceptance.py -v
# 기존 4건 + 신규 1건 = 5건 PASS
# test_phi3_grievance_pairs_resonate (자연 측정 acceptance) — 본 spec 적용 후 PASS 기대
```

### 5.5 자연 측정 (acceptance 본 검증)

```bash
cd Projects/personas/loom
py observe_phase17_emergence.py --label phi3-phase14b-a --seeds 7,13,42 --ticks 5000
```

**산출**: `data/phase17_probe_phi3-phase14b-a/SUMMARY.md`

**기대 결과 (Case A)**:

| # | 기준 | seed 7 | seed 13 | seed 42 | 결과 |
|---|------|:------:|:-------:|:-------:|:----:|
| 1 | uprising_event ≥ 1 | ≥ 1 | ≥ 1 | ≥ 1 | PASS |
| 2 | grievance_pairs_end ≥ 1 | ≥ 1 | ≥ 1 | ≥ 1 | **PASS** |
| 3 | dom_share_end ≥ 0.50 | ≥ 50% | ≥ 50% | ≥ 50% | PASS |

**Secondary metric (보고만, acceptance 아님)**:
- `active_factions_end` (≥ 2 기대, 1이면 collapse 잔존)
- `branch_factions_total`, `uprising_branch_share` (axis A 단독이라 0건이어도 무관)
- `contact_pairs_end`

---

## 6. 결과 분기 정책

자연 측정 결과는 다음 3 case 중 하나로 분류한다. 거짓 PASS는 절대 허용하지 않는다.

### Case A — acceptance 3종 모두 자연 PASS (목표)
- `grievance_pairs_end ≥ 1` 모든 seed
- 다음 단계: Φ-3 closure 2차 보고서 작성 → Φ-4 Nation Charter 진입
- axis B·C는 §11에 따라 Φ-4 진입 시점에 별도 trigger 검토 (필요 시)

### Case B — acceptance #1, #3 PASS, #2 FAIL + active_factions ≥ 2
- dampen은 작동했으나 grievance pair 응결 미달
- finding: 시간 축 부족 또는 propagation 강도 부족
- **다음 단계**: Phase 14 상수 (`GRIEVANCE_PROPAGATE_TRUST_MIN`, `GRIEVANCE_DONOR_MIN`) tune 검토 또는 10000틱 확장 (사용자 결정)

### Case C — acceptance #2 FAIL + active_factions_end=1 잔존 (collapse 패턴 잔존)
- dampen 강도 부족 또는 다른 collapse 경로 존재
- **다음 단계 옵션**:
  1. `GRIEVANCE_LORD_FACTION_DAMPEN` 0.5로 tune (강도 ↑)
  2. axis B·C 진입 spec 재작성 (sub-reviewer finding 정정 후)
  3. 10000틱 확장 측정
- **거짓 보정 절대 금지**

각 case별 산출 파일 보존:
- `data/phase17_probe_phi3-phase14b-a/SUMMARY.md`
- `data/phase17_probe_phi3-phase14b-a/seeds/seed_*.json`

---

## 7. Rollback

본 spec 적용 commit을 단일 commit으로 만든 후 `git revert <commit-hash>`로 완전 되돌림.

데이터 영향:
- `data/phase17_probe_phi3-phase14b-a/` 삭제 (probe 산출물)
- 기존 Phase 14 산출물 (`data/phase17_probe_phi3-phase14-resonance/`) 영향 없음

코드 영향:
- 신규 상수 2개 제거 (ontology/layers.py)
- `_faction_lord_ids` helper 메서드 제거
- `_compute_affiliation_tick` line 1251 직전 dampen 블록 제거
- 회귀 테스트 신규 1건 제거

Rollback 후 회귀 검증:
```bash
cd Projects/personas/loom
py test_phase17_faction_handoff_contract.py
py -m pytest test_phase17_acceptance.py -v
# Phase 14 상태로 복귀 (acceptance #2 FAIL 재현, Case C)
```

---

## 8. 자체 검증 체크리스트 (구현자 용)

구현 완료 보고 직전 모두 통과해야 함:

- [ ] §3.1 신규 상수 2개 추가 (line 257 뒤, 코멘트 포함 9줄)
- [ ] §3.2.1 `_faction_lord_ids` helper 추가 (line 1175 직전, ≤15줄)
- [ ] §3.2.2 dampen 블록 삽입 (line 1251 직전, 8줄)
- [ ] §3.3 회귀 테스트 1건 + 헬퍼 추가
- [ ] §5.1 py_compile 4개 파일 PASS
- [ ] §5.2 grep 거짓 PASS 키워드 0 hits (신규 라인) + Python AST 본문 길이 검증 PASS
- [ ] §5.3 무파괴 9 보장 9건 모두 충족
- [ ] §5.4 회귀 테스트 (handoff 12건 + acceptance 신규 5건) PASS
- [ ] §5.5 자연 측정 probe 실행 + SUMMARY 생성
- [ ] §6 case 분기 결과 보고 (A/B/C 중 하나)
- [ ] artificial injection / hard override / 결과 강제 0건 (코드 리뷰 자체 확인)
- [ ] [금지] 영역 diff 0줄 (axis B·C 메서드 무수정 확인)

---

## 9. 자연 메커니즘 vs 거짓 PASS 패턴 대비표

| # | 본 spec 자연 메커니즘 | 거짓 PASS 패턴 (금지) |
|---|----------------------|--------------------|
| 1 | dampen은 **곱셈** (0.6). score를 0으로 만들지 않음 | 점수 직접 부여 / 후보 강제 제거 / score=0 강제 |
| 2 | SNN anger fire rate < gate면 **자연 비활성화** (창발 채널) | sticky / cache / floor로 결과 강제 유지 |
| 3 | grievance < MIN_SHARED면 dampen 자연 비활성화 | 약한 분노에도 강제 dampen → artificial guard |
| 4 | grievance_lord_id 미존재 시 **graceful fallback** (기존 동작) | 인공 보정으로 결과 강제 |
| 5 | Phase 14 propagation 산출물 자연 활용 (read-only) | propagation 결과 직접 수정 / sticky 유지 |

---

## 10. 외부 엔진 cross-check 권고 (sub-reviewer 검증 반영)

본 spec은 Claude 단독 작성이며, 작성 직전 모사된 가상 3엔진 합의는 외부 엔진 호출 없이 Claude의 사고로 생성됨 (`feedback_model_comparison_independence.md` 잠재 위반).

**권고**: 본 spec commit 직전 또는 Codex 구현 발주 직전 **실제 외부 엔진 cross-check 1회** 수행:

```bash
# 권장 명령 (subagent-orchestrator 작업 디렉토리에서)
node packages/launcher/dist/discussion/discuss-cli.js --quick \
  "Phase 14B-A axis A spec — affiliation drift dampen + SNN anger gate가 SNN 창발 정신과 정합? 거짓 PASS 패턴 잠복 위험?"
```

또는 `/discuss --quick` 호출. cross-check 결과는 `subagent-runs/discuss/phase14b-a-cross-check-2026-04-28-quick/` 에 보존.

cross-check 결과에 mechanism 수준 거짓 PASS 패턴 신호가 없으면 commit 진입. 신호 발견 시 spec §3.2 / §9 보강 후 재검토.

---

## 11. 후속 — axis B·C 미해결 시 trigger

본 spec은 axis A 단독. axis B (uprising target grievance 분기) / axis C (uprising trigger 인접 완화)는 **§6 자연 측정 결과에 따라** 다음 trigger 시 별도 spec 진입:

### Trigger 조건

| Case | axis B·C 진입 여부 | 근거 |
|------|:---:|------|
| A (3종 자연 PASS) | **불필요** | 근본(axis A)부터 풀려 상위 결손 자동 해결 |
| B (#2 FAIL + active_factions ≥ 2) | 시간/임계 tune 우선 | dampen 작동했으나 propagation 약함 |
| C (collapse 잔존) | dampen tune 후에도 잔존 시 axis B·C 진입 | 단일 채널 한계 |

### axis B·C 진입 시 보강 항목 (sub-reviewer finding 반영)

axis B·C가 후속 spec으로 진입하게 되면 다음을 명시 필수:

- **MAJOR-B-1**: leader↔target faction 멤버 grievance 비대칭 (Φ-4 무한 진동 risk) [범위 외] 또는 별도 처리
- **MAJOR-C-2**: branch → grievance_pairs 인과 사슬 §1 본문에 명시
- **MAJOR-C-3**: secondary metric strict assertion 회피 (`xfail(strict=False)` 또는 `>= 0`)
- **CRITICAL-C-1**: awk 검증 명령 → Python AST로 교체 (본 spec §5.2 패턴 그대로 계승)

---

거짓 PASS는 절대 허용하지 않는다. 어느 case든 자연 측정 그대로 보고한다 (`feedback_snn_emergence_first.md` + `feedback_root_cause_first.md`).
