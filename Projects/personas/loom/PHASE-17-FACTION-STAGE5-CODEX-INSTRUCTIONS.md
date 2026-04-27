# [기능] Phase 17 Φ-2 Faction Stage 5 — Anti-Collapse 통합안 (I+G+D 관찰) 구현 지시서

> 긴급도: 높음
> 선행 조건: Phase 17 Stage 4 closure addendum-v2 완료. Stage 4 acceptance(`active_factions_end >= 2`) v6 결과 3 seed 전원 FAIL ([data/phase17_probe_v6/SUMMARY.md](data/phase17_probe_v6/SUMMARY.md)). 본 지시서는 그 second-collapse 패턴 종결.
> 작업 유형: 기능 (백엔드, Python 시뮬)
> DB migration: 없음
> 외부 의존: 없음 (신규 패키지 없음)
> 기준 SSoT: [PHASE-17-FACTION-STAGE5-DECISIONS.md](PHASE-17-FACTION-STAGE5-DECISIONS.md) — 결정/근거 전부 그쪽에. 본 지시서는 *코딩 사양만*.
> 변경 규모: ~17 LOC (layers.py 신규/수정 ~10 LOC + multi_tick_engine.py 신규 ~7 LOC). 단일 커밋 권장.
> 작업 시간 추정: 30~60분 (재현 검증 포함). probe 5000틱 × 3 seed 별도 ~3~6분.
> 사전 준비: WKI 인덱싱(`node workspace-knowledge-index/dist/index.js index`) 권장. 본 지시서·DECISIONS·CHARTER 3 파일이 핵심 컨텍스트.

## 헌장적 보장 (Charter v2 무파괴 9개 — 본 Stage 5 전부 보존)

본 작업은 다음을 *건드리지 않는다*. 변경 후 grep으로 흔적 비교 시 *전부* 동일해야 함:

1. **`FactionChangeSource = Literal["birth_founder", "affiliation", "drift", "conflict"]`** ([core/multi_tick_engine.py:87](core/multi_tick_engine.py#L87)) — 4종 동결.
2. **`_change_persona_faction` 시그니처** ([core/multi_tick_engine.py:1046~1051](core/multi_tick_engine.py#L1046)) — 단일 SSoT 쓰기 경로.
3. **AST whitelist 마커** (`# noqa: PHASE17_FACTION_SSOT_WRITE`) — 기존 4개 라인(L1064, L1065, L1082, L1351, L1401) 그대로. 본 Stage 5 변경 라인에 마커 추가 *불요* (faction 필드 직접 쓰기 없음).
4. **D10 5채널** (`faction_demographics`, `faction_economic_pressure`, `faction_relational_field`, `faction_territorial_overlap`, `faction_collective_charter`) — 시그니처 동결.
5. **질적 동기 3종** (`faction_wealth_distribution`, `faction_social_matrix`, `faction_grievance_targets`) — 동결.
6. **Charter primitive 12종 + (3,5) 길이 제약** ([ontology/layers.py:237~247](ontology/layers.py#L237)) — 무수정.
7. **`_derive_rng` 단일 RNG 경로** — 무수정.
8. **SNN 코드 / readout_weights_v1.npy / 뉴런 300~349** — kernel과 SNN 분리 동결.
9. **THETA_JOIN, FACTION_COMMIT_EVERY, FACTION_COOLDOWN_TICKS, FACTION_HYSTERESIS, FACTION_PROJECT_EVERY** — 무변경.

---

## 배경

Stage 1~3 anti-collapse(size tax + homeostasis + minority boost + founder respawn) 적용 후에도 v6 probe 3 seed 전원 `active_factions_end=1`로 흡수. 근본 원인은 `drift_score` 가중치 비대칭 (`W_TRUST=0.8 ≫ W_TERRITORY_SAME=0.3`) — trust 누적성이 territory 동시성을 누르고 단일 faction 흡수를 자연 평형으로 만든다.

본 작업은 **3가지 처방 통합**:
- **I (가중치 재균형)** — 근본 처치. `W_TRUST 0.8→0.5`, `W_TERRITORY_SAME 0.3→0.5` 동률화
- **G (respawn grace)** — 보조 안전판. founder respawn 직후 200틱 동안 새 faction 멤버 drift 면역
- **D (residence 관찰)** — fallback 입력. read-only 누적, Stage 5.5에서 affiliation 입력 격상 검토용

---

## 사전 준비

### 1. 컨텍스트 확보

작업 시작 전 다음 파일들을 *순서대로* 읽기:

1. [PHASE-17-FACTION-STAGE5-DECISIONS.md](PHASE-17-FACTION-STAGE5-DECISIONS.md) — 본 Stage 5 SSoT (왜 이 처방인가).
2. 본 지시서 — 무엇을·어떻게 (전체 1회 통독 후 섹션별 재참조).
3. [PHASE-17-FACTION-CHARTER.md](PHASE-17-FACTION-CHARTER.md) — Charter v2 무파괴 9 보장 (헌장적 제약 인지).
4. [data/phase17_probe_v6/SUMMARY.md](data/phase17_probe_v6/SUMMARY.md) — Stage 5 진입 baseline (가시화: "이 결과를 PASS로 바꾸는 게 목표").

**WKI 검색 권장** (선택): `node workspace-knowledge-index/dist/index.js search "Phase 17 faction grace" --top 5` — 관련 다른 SSoT 파일 발견에 도움.

### 2. 코드 위치 확인

```bash
cd Projects/personas/loom

# Faction dataclass (변경 대상)
rtk proxy "py -c \"import subprocess; subprocess.run(['rg', '-n', '@dataclass.slots=True.', 'ontology/layers.py', '-A', '10'])\""
# 기대: line 167~ Faction 정의

# 가중치 상수 v5 블록 (변경 대상)
rtk proxy "py -c \"import subprocess; subprocess.run(['rg', '-n', 'W_TERRITORY_SAME = 0.3|W_TRUST = 0.8', 'ontology/layers.py'])\""
# 기대: line 197 / 199

# _commit_faction_tick (drift 면역 분기 추가 위치)
rtk proxy "py -c \"import subprocess; subprocess.run(['rg', '-n', 'def _commit_faction_tick', 'core/multi_tick_engine.py'])\""

# _respawn_faction_tick (1차/2차 grace 설정 위치)
rtk proxy "py -c \"import subprocess; subprocess.run(['rg', '-n', 'def _respawn_faction_tick', 'core/multi_tick_engine.py'])\""
```

라인 번호가 본 지시서와 다르면 작업 환경의 git 상태가 본 지시서 작성 시점(2026-04-25 v6 baseline)과 다른 것. 그 경우 사용자에게 보고 후 진행.

### 3. baseline 시뮬 1회 실행 (선택, 권장)

```bash
rtk proxy "py observe_phase17_emergence.py --quick --out data/phase17_baseline_quick"
```

`--quick`은 seed 42 × 500틱 — 1분 이내. v6 collapse 패턴 재현 확인 후 변경 시작하면 *변화* 측정이 명확.

### 4. 작업 단계 (권장 순서)

**원칙**: 작은 변경 → 즉시 검증. 한 번에 다 만들고 마지막에 검증하면 회귀 원인 추적 곤란.

**Step 1 — layers.py 가중치만** (가장 단순, 1라인 가치):
- L195~196 주석 v5→v6 갱신
- L197 `W_TERRITORY_SAME = 0.5`로 변경
- L199 `W_TRUST = 0.5`로 변경
- 즉시 검증: `py test_phase17_acceptance.py` 실행 → PASS 확인 (가중치 변경만으로 회귀 발생 시 문제는 가중치 자체 — 다음 단계 진행 위험).

**Step 2 — layers.py 신규 필드/상수**:
- Faction dataclass에 `grace_until_tick: int = 0` 추가 (line 174 다음)
- L233 직후에 `RESPAWN_GRACE_TICKS = 200` + 주석 4줄 추가
- InnerWorld dataclass에 `residence_ticks: dict[str, int] = field(default_factory=dict)` 추가 (line 905 다음)
- 즉시 검증: `py -c "from ontology.layers import RESPAWN_GRACE_TICKS, Faction; f = Faction('a','b','c',('토지_공유','무역_개방','재산_개인'),0); print(f.grace_until_tick, RESPAWN_GRACE_TICKS)"` → `0 200`

**Step 3 — multi_tick_engine.py import**:
- L63 import 라인에 `RESPAWN_GRACE_TICKS,` 추가
- 즉시 검증: `py -c "from core.multi_tick_engine import MultiTickEngine"` → 에러 없음

**Step 4 — multi_tick_engine.py drift 면역 분기**:
- L1281 직전에 grace check 3 라인 삽입
- 즉시 검증: `py test_phase17_acceptance.py` (회귀 없음 확인 — 아직 grace 설정하는 코드 없으므로 모든 faction의 grace_until_tick=0 → 면역 분기 항상 거짓 → 기존 동작과 동일)

**Step 5 — multi_tick_engine.py respawn grace 설정 (1차)**:
- L1342~1351 1차 respawn `Faction(...)` 생성자에 `grace_until_tick=self.time.tick + RESPAWN_GRACE_TICKS,` 추가

**Step 6 — multi_tick_engine.py respawn grace 설정 (2차 fallback)**:
- L1392~1401 2차 fallback `Faction(...)` 생성자에 동일 라인 추가

**Step 7 — multi_tick_engine.py residence 누적**:
- L348~349 사이 (Stage 1 페르소나 루프, sleep 분기 진입 전) 2 라인 삽입:
  ```python
              # Stage 5: territory residence read-only accumulation (D 관찰)
              persona = self.personas[pid]
              inner.residence_ticks[persona.territory] = inner.residence_ticks.get(persona.territory, 0) + 1
  ```
- 단, 이미 `persona = self.personas[pid]` 선언이 있으면 그 변수 재사용.
- 즉시 검증: `py test_phase17_acceptance.py` → `five_channel_determinism` PASS 확인.

**Step 8 — 회귀 + acceptance**:
- 전체 회귀 테스트 5종 실행
- emergence probe 5000틱 × 3 seed 실행
- SUMMARY 검증

각 Step 완료 시 `git diff --stat`으로 변경량 추적. 의도치 않은 라인 변경 발견 시 즉시 revert.

---

## 작업 범위

### [필수]
1. `layers.py` 가중치 상수 2개 변경 (`W_TERRITORY_SAME` / `W_TRUST`).
2. `layers.py` 신규 상수 1개 추가 (`RESPAWN_GRACE_TICKS = 200`).
3. `layers.py` `Faction` dataclass에 `grace_until_tick: int = 0` 필드 추가 (`slots=True` 호환).
4. `layers.py` `InnerWorld` dataclass에 `residence_ticks: dict[str, int] = field(default_factory=dict)` 필드 추가.
5. `multi_tick_engine.py` `_respawn_faction_tick` 두 군데(1차 + 2차 fallback) faction 생성 직후 `grace_until_tick = self.time.tick + RESPAWN_GRACE_TICKS` 설정.
6. `multi_tick_engine.py` `_commit_faction_tick` drift 평가 분기에 grace 면역 분기 1개 삽입 (현재 faction이 grace 기간이면 `continue`).
7. `multi_tick_engine.py` Stage 1 페르소나 루프에서 매 틱 1회 `inner.residence_ticks[persona.territory] += 1` 누적.
8. `multi_tick_engine.py` import 라인에 `RESPAWN_GRACE_TICKS` 추가.
9. 회귀 테스트(`test_phase17_acceptance.py`, `test_economy.py`, `test_nomos.py`, `test_class_promotion.py`) 100% 통과 + emergence probe(seed 7/13/42 5000틱) `active_factions_end >= 2` 3/3 PASS.

### [선택]
- `observe_phase17_emergence.py` SUMMARY 출력에 secondary 지표 추가:
  - `last_500_active>=2` ratio
  - `gini` (현재 `gini_mean_end`로 일부 있음)
  - `drift_source_distribution_entropy` (`source="drift"` 빈도 분포 엔트로피)
  - `residence_ticks` 분포 통계 (Stage 5.5 입력용)
- `PHASE-17-AFFILIATION-TUNE-SPEC.md`에 v6 (2026-04-25) 항목 추가 (이력 보존). 본 Stage 5 PASS 시.

### [금지]
- **Charter 본문 수정** (`PHASE-17-FACTION-CHARTER.md` — 가중치는 Decision Card 권한, Charter 본문 무수정).
- **기존 Decision 본문 수정** (`PHASE-17-FACTION-DECISIONS.md` Decision 4 v3 등 — historic 보존, 본 Stage 5 SSoT는 별도 파일).
- **보류 항목 구현** — H-lite (`founder_lineage`) / F (이탈 비대칭 cost). 흔적도 남기지 말 것.
- **D residence_ticks를 affiliation_kernel 입력에 진입**. 본 Stage 5는 *read-only 관찰만*. `_compute_affiliation_tick` 내부 또는 affiliation_score 계산식에 `residence_ticks` 사용 금지.
- **다른 가중치 변경** — `W_TERRITORY_DIFF`, `W_GRIEVANCE`, `W_PROXIMITY`, `DECAY`, `GRIEVANCE_MIN_SHARED`, `PROXIMITY_DECAY_SCALE`, `THETA_JOIN`, `DRIFT_MARGIN_MIN`, `DRIFT_MARGIN_RATIO`, `FACTION_COOLDOWN_TICKS`, `FACTION_COMMIT_EVERY`, `FACTION_SIZE_TAX_*`, `HOMEOSTASIS_*`, `MINORITY_PERSISTENCE_*`, `FOUNDER_RESPAWN_*` — 일절 변경 금지.
- **`faction_cooldown` 채널 재사용**. 신규 `grace_until_tick`은 별도 필드 (시맨틱 분리: cooldown=재가입 락, grace=drift 면역). `Persona.faction_cooldown`을 grace 용도로 덮어쓰지 말 것.
- **`FactionChangeSource` 변경/추가** — `("birth_founder", "affiliation", "drift", "conflict")` 4종 동결. 신규 source 신설 금지.
- **`_change_persona_faction` 외 `persona.faction` 쓰기 경로 신설** — AST whitelist 규칙(noqa: PHASE17_FACTION_SSOT_WRITE) 위반 금지.
- **`_derive_rng` 외 RNG 경로 신설** — 결정성 RNG 단일 경로 동결.
- **D10 5채널 시그니처 변경** (`faction_demographics`, `faction_economic_pressure`, `faction_relational_field`, `faction_territorial_overlap`, `faction_collective_charter` + 질적 동기 3종 `faction_wealth_distribution`, `faction_social_matrix`, `faction_grievance_targets`).
- **SNN 코드 / readout_weights_v1.npy / 뉴런 300~349** — kernel과 SNN 분리 동결.

---

## 구체 사양

### 1. layers.py — 가중치 상수 변경 (Change I)

**변경 위치: `Projects/personas/loom/ontology/layers.py` line 195~204 영역.**

#### Before (현재 v5, 2026-04-23)

```python
# ── Phase 17 affiliation_score (v5: drift 봉쇄 해소 패치 2026-04-23) ──
# 고정점 분석 근거: PHASE-17-AFFILIATION-TUNE-SPEC.md 참조
W_TERRITORY_SAME = 0.3   # 같은 territory 거주 시 (v4: 1.0 → v5: 0.3, 비대칭 완화)
W_TERRITORY_DIFF = 0.1   # 다른 territory 거주 시 (v4: 0.0 → v5: 0.1, 완전 차단 제거)
W_TRUST = 0.8
W_GRIEVANCE = 0.6
W_PROXIMITY = 0.4
DECAY = 0.92
GRIEVANCE_MIN_SHARED = 0.3
PROXIMITY_DECAY_SCALE = 10.0
```

#### After (v6, 2026-04-25, Stage 5 통합안)

```python
# ── Phase 17 affiliation_score (v6: Stage 5 Anti-Collapse 가중치 재균형 2026-04-25) ──
# 근거: v5 probe 3 seed 전원 active_end=1 흡수 (PHASE-17-FACTION-STAGE5-DECISIONS.md S5-1).
# trust 누적 우위 vs territory 동시성 비대칭이 single-attractor 평형의 근본 원인.
# trust=territory=0.5 동률로 다극(multi-polar) 평형 유도.
W_TERRITORY_SAME = 0.5   # 같은 territory 거주 시 (v5: 0.3 → v6: 0.5, trust와 동률)
W_TERRITORY_DIFF = 0.1   # 다른 territory 거주 시 (유지)
W_TRUST = 0.5            # (v3~v5: 0.8 → v6: 0.5, 누적 우위 비대칭 해소)
W_GRIEVANCE = 0.6
W_PROXIMITY = 0.4
DECAY = 0.92
GRIEVANCE_MIN_SHARED = 0.3
PROXIMITY_DECAY_SCALE = 10.0
```

**라인별 변경**:
- L195~196 주석 2줄 위 블록으로 교체
- L197 `W_TERRITORY_SAME = 0.3 ...` → `W_TERRITORY_SAME = 0.5 ... (v5: 0.3 → v6: 0.5, trust와 동률)`
- L199 `W_TRUST = 0.8` → `W_TRUST = 0.5            # (v3~v5: 0.8 → v6: 0.5, 누적 우위 비대칭 해소)`
- L198, L200~204 변경 없음

**부수 효과**:
- L235 `W_TERRITORY = W_TERRITORY_SAME` 별칭 — 자동으로 0.5로 갱신 (deprecated 경로 호환). **추가 수정 불필요**.

---

### 2. layers.py — Faction 신규 필드 + 신규 상수 (Change G 일부)

#### 2-A. `Faction` dataclass에 `grace_until_tick` 추가

**위치: `Projects/personas/loom/ontology/layers.py` line 167~182**

#### Before

```python
@dataclass(slots=True)
class Faction:
    """Phase 17 faction registry entry."""
    id: str
    name: str
    founder_pid: str
    charter: tuple[str, ...]
    created_tick: int

    def __post_init__(self) -> None:
        charter = tuple(self.charter)
        if not (3 <= len(charter) <= 5):
            raise ValueError(f"charter length {len(charter)} out of [3, 5]")
        if len(set(charter)) != len(charter):
            raise ValueError(f"charter has duplicates: {charter!r}")
        self.charter = charter
```

#### After

```python
@dataclass(slots=True)
class Faction:
    """Phase 17 faction registry entry."""
    id: str
    name: str
    founder_pid: str
    charter: tuple[str, ...]
    created_tick: int
    grace_until_tick: int = 0    # Stage 5: respawn 직후 drift 면역 종료 시각 (절대 tick). 0 = 면역 없음.

    def __post_init__(self) -> None:
        charter = tuple(self.charter)
        if not (3 <= len(charter) <= 5):
            raise ValueError(f"charter length {len(charter)} out of [3, 5]")
        if len(set(charter)) != len(charter):
            raise ValueError(f"charter has duplicates: {charter!r}")
        self.charter = charter
```

**제약**: `slots=True`이므로 신규 필드는 dataclass 정의 내에 명시 필수. 기본값 `0`은 *면역 없음* 시맨틱 (기존 faction 호환 — Stage 1~3에서 생성된 faction은 grace 미적용).

#### 2-B. 신규 상수 `RESPAWN_GRACE_TICKS`

**위치: `Projects/personas/loom/ontology/layers.py` line 232 직후 (Stage 3 anti-collapse 섹션 끝).**

#### Before (line 224~234)

```python
# ── Phase 17 Stage 3: anti-collapse (minority persistence + founder respawn, 2026-04-24) ──
# 근거: v6 probe 3 seed 전원 active_end=1 붕괴 (absorbing state). B+C 조합으로 예방+치료.
# B. Minority persistence: 소규모 faction의 territory 동거 가산을 줘서 멸종 직전 유지
MINORITY_PERSISTENCE_MAX_MEMBERS = 2      # members <= 2일 때 boost 적용
MINORITY_PERSISTENCE_BOOST = 0.15         # score 가산값 (= DRIFT_MARGIN_MIN * HOMEOSTASIS_DRIFT_MARGIN_SCALE 와 동일 규모)
# C. Founder respawn: active < target이면 K틱 주기로 territory lord 기반 신규 faction 생성
FOUNDER_RESPAWN_EVERY = 480               # FACTION_COMMIT_EVERY * 10 (48 * 10). commit 주기와 정합
FOUNDER_RESPAWN_TARGET_ACTIVE = 2         # active 가 2 미만일 때만 발동 (overspawn 방지)

# 하위 호환 (기존 import 유지용, 실제 경로는 동적 계산이 우선)
DRIFT_MARGIN = DRIFT_MARGIN_MIN  # deprecated: 동적 계산 사용
W_TERRITORY = W_TERRITORY_SAME   # deprecated: same territory weight alias
```

#### After (line 224~232 다음에 새 블록 삽입, 233~ 기존 유지)

```python
# ── Phase 17 Stage 3: anti-collapse (minority persistence + founder respawn, 2026-04-24) ──
# (기존 블록 유지 — 변경 없음)
MINORITY_PERSISTENCE_MAX_MEMBERS = 2
MINORITY_PERSISTENCE_BOOST = 0.15
FOUNDER_RESPAWN_EVERY = 480
FOUNDER_RESPAWN_TARGET_ACTIVE = 2

# ── Phase 17 Stage 5: Respawn grace period (G, 2026-04-25) ──
# 근거: Stage 3 founder_respawn 직후 신생 faction이 trust 누적 우위에 즉시 흡수되는
# second-collapse pattern. 200틱 동안 drift 입력 단계에서 면역.
# faction_cooldown(재가입 락) 채널 재사용 금지 — 시맨틱 분리.
RESPAWN_GRACE_TICKS = 200

# 하위 호환 (기존 import 유지용, 실제 경로는 동적 계산이 우선)
DRIFT_MARGIN = DRIFT_MARGIN_MIN  # deprecated: 동적 계산 사용
W_TERRITORY = W_TERRITORY_SAME   # deprecated: same territory weight alias
```

---

### 3. layers.py — InnerWorld 신규 필드 (Change D)

**위치: `Projects/personas/loom/ontology/layers.py` line 901~ `InnerWorld` dataclass.**

#### Before (line 901~906 영역)

```python
@dataclass
class InnerWorld:
    """페르소나의 내면 상태."""
    persona_id: str
    affiliation_scores: dict[str, float] = field(default_factory=dict)

    # 12클러스터 neuromodulator_tone (Phase 0: 기본값 1.0)
```

#### After

```python
@dataclass
class InnerWorld:
    """페르소나의 내면 상태."""
    persona_id: str
    affiliation_scores: dict[str, float] = field(default_factory=dict)
    residence_ticks: dict[str, int] = field(default_factory=dict)   # Stage 5: territory_id → 누적 거주 ticks (read-only 관찰)

    # 12클러스터 neuromodulator_tone (Phase 0: 기본값 1.0)
```

**제약**: `InnerWorld`는 `@dataclass` (slots 없음) — 신규 필드 자유 추가 가능. 기본값 빈 dict로 기존 InnerWorld 인스턴스 호환.

---

### 4. multi_tick_engine.py — import 라인 갱신

**위치: `Projects/personas/loom/core/multi_tick_engine.py` line 63.**

#### Before

```python
    FOUNDER_RESPAWN_EVERY, FOUNDER_RESPAWN_TARGET_ACTIVE,
```

#### After

```python
    FOUNDER_RESPAWN_EVERY, FOUNDER_RESPAWN_TARGET_ACTIVE,
    RESPAWN_GRACE_TICKS,
```

(같은 import 블록 끝부분 위치. 다른 import 항목에는 손대지 말 것.)

---

### 5. multi_tick_engine.py — drift 면역 분기 (Change G)

**위치: `Projects/personas/loom/core/multi_tick_engine.py` `_commit_faction_tick` 함수, line 1265~1281 영역.**

#### Before (line 1265~1281)

```python
        for pid in sorted(snapshot):
            cur_fid, cooldown, scores = snapshot[pid]
            if cooldown > 0 or not scores:
                continue
            sorted_items = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
            best_fid, best_score = sorted_items[0]
            if cur_fid is None:
                if best_score >= THETA_JOIN:
                    self._change_persona_faction(pid, best_fid, source="affiliation")
            else:
                if best_fid == cur_fid:
                    continue
                current_score = scores.get(cur_fid, 0.0)
                gap = best_score - current_score
                dynamic_margin = max(margin_floor, gap * DRIFT_MARGIN_RATIO)  # v6
                if gap >= dynamic_margin:
                    self._change_persona_faction(pid, best_fid, source="drift")
        self._rebuild_faction_members_cache()
```

#### After (line 1274 `else:` 분기 안, `if best_fid == cur_fid:` 직전에 grace check 삽입)

```python
        for pid in sorted(snapshot):
            cur_fid, cooldown, scores = snapshot[pid]
            if cooldown > 0 or not scores:
                continue
            sorted_items = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
            best_fid, best_score = sorted_items[0]
            if cur_fid is None:
                if best_score >= THETA_JOIN:
                    self._change_persona_faction(pid, best_fid, source="affiliation")
            else:
                # Stage 5: respawn grace 기간 동안 drift 면역 (현 faction이 grace 중이면 멤버 이탈 차단)
                current_faction = self.factions.get(cur_fid)
                if current_faction is not None and current_faction.grace_until_tick > self.time.tick:
                    continue
                if best_fid == cur_fid:
                    continue
                current_score = scores.get(cur_fid, 0.0)
                gap = best_score - current_score
                dynamic_margin = max(margin_floor, gap * DRIFT_MARGIN_RATIO)  # v6
                if gap >= dynamic_margin:
                    self._change_persona_faction(pid, best_fid, source="drift")
        self._rebuild_faction_members_cache()
```

**시맨틱**:
- 면역은 *cur_fid grace check*. 즉 현재 페르소나가 속한 faction이 grace 기간이면 그 페르소나는 drift로 빠져나가지 않는다.
- 가입(`cur_fid is None` 분기)에는 영향 없음 — 가입은 자유.
- best_fid가 grace인지는 검사 불필요 — 가입 차단 의도 없음.

---

### 6. multi_tick_engine.py — Respawn grace 설정 (Change G)

**위치: `Projects/personas/loom/core/multi_tick_engine.py` `_respawn_faction_tick` 함수, line 1342~1351 (1차) + line 1392~1401 (2차 fallback).**

#### 1차 respawn (line 1342~1351)

#### Before

```python
            faction = Faction(
                id=faction_id,
                name=faction_name,
                founder_pid=founder.id,
                charter=charter,
                created_tick=self.time.tick,
            )
            self.factions[faction.id] = faction
            self._change_persona_faction(founder.id, faction.id, source="birth_founder")
            self.personas[founder.id].faction_cooldown = FOUNDER_RESPAWN_EVERY  # noqa: PHASE17_FACTION_SSOT_WRITE
            active_count += 1
```

#### After

```python
            faction = Faction(
                id=faction_id,
                name=faction_name,
                founder_pid=founder.id,
                charter=charter,
                created_tick=self.time.tick,
                grace_until_tick=self.time.tick + RESPAWN_GRACE_TICKS,  # Stage 5
            )
            self.factions[faction.id] = faction
            self._change_persona_faction(founder.id, faction.id, source="birth_founder")
            self.personas[founder.id].faction_cooldown = FOUNDER_RESPAWN_EVERY  # noqa: PHASE17_FACTION_SSOT_WRITE
            active_count += 1
```

#### 2차 fallback (line 1392~1401)

**동일 변경**. `Faction(...)` 생성자 호출에 `grace_until_tick=self.time.tick + RESPAWN_GRACE_TICKS,` 라인 추가.

#### Before

```python
            faction = Faction(
                id=faction_id,
                name=faction_name,
                founder_pid=founder.id,
                charter=charter,
                created_tick=self.time.tick,
            )
            self.factions[faction.id] = faction
            self._change_persona_faction(founder.id, faction.id, source="birth_founder")
            self.personas[founder.id].faction_cooldown = FOUNDER_RESPAWN_EVERY  # noqa: PHASE17_FACTION_SSOT_WRITE
            active_count += 1
```

#### After

```python
            faction = Faction(
                id=faction_id,
                name=faction_name,
                founder_pid=founder.id,
                charter=charter,
                created_tick=self.time.tick,
                grace_until_tick=self.time.tick + RESPAWN_GRACE_TICKS,  # Stage 5
            )
            self.factions[faction.id] = faction
            self._change_persona_faction(founder.id, faction.id, source="birth_founder")
            self.personas[founder.id].faction_cooldown = FOUNDER_RESPAWN_EVERY  # noqa: PHASE17_FACTION_SSOT_WRITE
            active_count += 1
```

**중요**: 1차/2차 *모두* 변경 필수. 한 군데만 변경하면 fallback 경로에서 grace 미적용 → 부분 fix.

#### 1차 respawn에서 `_init_founder_seeds`(tick=0)는?
[multi_tick_engine.py:1284~1296](Projects/personas/loom/core/multi_tick_engine.py): `_respawn_faction_tick`은 `if self.time.tick == 0: return`으로 tick=0 진입을 명시 차단. tick=0 초기 founder 생성은 별도 함수 `_init_founder_seeds`(line ~1410 근처)에서 처리. **`_init_founder_seeds`는 grace 미적용** — 초기 faction은 자연 시작 (Stage 5 grace는 *재생성 보호* 의도, 초기 생성은 보호 불요). `_init_founder_seeds` 본문 수정 금지.

---

### 7. multi_tick_engine.py — Residence 매 틱 누적 (Change D)

**위치: `Projects/personas/loom/core/multi_tick_engine.py` Stage 1 페르소나 루프, line 344~349 영역.**

#### Before (line 344~349)

```python
        actions: dict[str, str] = {}
        for pid in self.personas:
            inner = self.inners[pid]
            brain = self.brains[pid]
            self._tick_faction_cooldown(pid)

            if inner.is_sleeping:
```

#### After (line 348~349 사이에 누적 한 줄 + persona reference)

```python
        actions: dict[str, str] = {}
        for pid in self.personas:
            inner = self.inners[pid]
            brain = self.brains[pid]
            self._tick_faction_cooldown(pid)

            # Stage 5: territory residence read-only accumulation (D 관찰)
            persona = self.personas[pid]
            inner.residence_ticks[persona.territory] = inner.residence_ticks.get(persona.territory, 0) + 1

            if inner.is_sleeping:
```

**시맨틱**:
- sleep 분기 *진입 전* 누적 — 거주는 sleep과 무관. sleep 중에도 territory에 있다.
- exodus(`_try_exodus`로 territory 변경)도 이 시점 *이후*에 발생 → 본 누적은 이번 틱 시작 시점의 territory 기준 (의도 정확).
- read-only — `residence_ticks`를 다른 곳에서 *읽기* 위해 사용하는 코드는 본 Stage 5에서 추가 금지 ([금지] 항목).

---

## 처리 로직 (의사코드)

### 호출 순서 (tick() 본체, [core/multi_tick_engine.py:2153~2155](core/multi_tick_engine.py#L2153))

**중요**: 본 Stage 5 변경의 정합성은 *호출 순서*에 달려있다. commit이 respawn보다 먼저 호출되므로, 같은 틱(예: 480)에서:

```python
# core/multi_tick_engine.py:2153~2155
self._commit_faction_tick()       # ① 먼저: 기존 faction 멤버의 drift 평가
self._respawn_faction_tick()      # ② 나중: 신규 faction 생성 (grace 200 설정)
self._project_faction_tick()
```

따라서 시간축 시퀀스:

| tick | commit 발동 | respawn 발동 | 신규 faction grace 적용 시점 |
|------|---|---|---|
| 432 | ✅ | (480 미만 → return) | — |
| 480 | ✅ (기존 faction 평가) | ✅ (신규 X 생성, X.grace_until_tick = 680) | 신규 X는 commit 이후 생성 → 480 commit에 영향 없음 |
| 528 | ✅ (X 멤버 drift 평가 → grace 면역: 680 > 528 → continue) | (480 미만 후속 480 배수 아님) | grace 작동 ✅ |
| 576, 624, 672 | ✅ (계속 면역) | — | grace 작동 ✅ |
| 720 | ✅ (grace 종료: 680 > 720 거짓 → 정상 drift 평가) | — | 면역 만료 ✅ |

### Stage 1 페르소나 루프 (각 pid)

```
1. _tick_faction_cooldown(pid)                        ← 기존
2. [신규] persona = self.personas[pid]
   inner.residence_ticks[persona.territory] += 1     ← read-only 누적
3. if sleeping: sleep_tick → continue                  ← 기존
4. _process_movement(pid)                              ← 기존 (territory 변경 가능)
5. _try_exodus(pid)                                    ← 기존
6. ... (행동 결정·경제·도구 등 기존 로직)
```

**시맨틱 중요**: residence 누적은 `_tick_faction_cooldown` 직후, sleep 분기 *진입 전*. 즉:
- 이번 틱에서 *시작 시점의* territory 기준으로 1 누적
- sleep 중에도 누적 (territory에 거주 중이므로)
- `_process_movement`로 territory가 바뀌어도 *이번 틱은 이전 territory에 기록* (의도)

### _commit_faction_tick (매 48틱)

```
each pid의 affiliation scores snapshot
for pid in sorted(snapshot):
  if cur_fid is None:
    가입 (best_score >= THETA_JOIN 통과 시 source="affiliation")
  else:
    [신규] current_faction = self.factions.get(cur_fid)
    [신규] if current_faction is not None and current_faction.grace_until_tick > tick:
    [신규]     continue   # drift 면역 — 멤버 이탈 차단
    if best_fid == cur_fid: continue
    if gap >= dynamic_margin:
        drift (source="drift")
```

### _respawn_faction_tick (매 480틱)

```
if tick == 0: return
if tick % 480 != 0: return
if active_count >= 2: return

1차 — free_residents 우선 (faction 미가입 거주자 ≥ 3):
  Faction(
    id=...,
    name=...,
    founder_pid=...,
    charter=...,
    created_tick=tick,
    grace_until_tick=tick + 200,     ← [신규] Stage 5
  )
  → 신규 faction 등록 + founder 가입(source="birth_founder") + 200 grace

active_count >= 2 도달 시 return.

2차 fallback — 전체 residents (faction 가입 무관, ≥ 3):
  Faction(... grace_until_tick=tick + 200)   ← [신규] 동일
```

### _init_founder_seeds (tick=0, 무수정)

[core/multi_tick_engine.py:1430~1452](core/multi_tick_engine.py#L1430):

```python
def _init_founder_seeds(self) -> None:
    if self.factions:
        return
    for territory in sorted(self.territories.values(), key=lambda item: item.id):
        ...
        faction = Faction(
            id=faction_id,
            name=f"{territory.name}_F1",
            founder_pid=founder.id,
            charter=charter,
            created_tick=0,
            # grace_until_tick 미설정 → default 0 → 면역 없음 (의도)
        )
        ...
```

**무수정**. tick=0 초기 founder는 grace 미적용 — Stage 5 grace는 *재생성 보호*이지 *초기 보호*가 아니다. 본 함수에 `grace_until_tick=...` 추가 시 Stage 4 acceptance baseline을 변경하므로 회귀.

---

## 에러 케이스 (시뮬 결정성/회귀)

| 상황 | 증상 | 검출 |
|------|-----|------|
| `grace_until_tick` 신규 필드 추가 누락 | `AttributeError: 'Faction' object has no attribute 'grace_until_tick'` | 첫 commit_tick에서 즉시 발생 |
| 1차 respawn만 grace 설정 / 2차 fallback 누락 | 일부 seed에서 second-collapse 잔존 (acceptance partial fail) | seed 7/13/42 acceptance |
| `residence_ticks` field_factory가 `dict` 아닌 `lambda: {}` | dataclass 인스턴스 간 dict 공유 → seed 간 상태 누설 → 결정성 깨짐 | `test_phase17_acceptance.py` `five_channel_determinism` |
| `_compute_affiliation_tick`에 residence_ticks 진입 (금지 위반) | affiliation_score 변경으로 stage 4 회귀 fail | acceptance + Phase 11~16 5지표 |
| W_TRUST를 0.5 외 다른 값으로 잘못 변경 (예: 0.6) | acceptance 미달 (0.6은 v1 fallback 안 — 본 Stage 5 채택 안 아님) | seed 7/13/42 active_end |
| `faction_cooldown` 채널 재사용으로 grace 구현 | 기존 cooldown(재가입 락) 시맨틱 충돌 → 재가입 동작 깨짐 | `test_phase17_acceptance.py` cooldown 관련 케이스 |
| import 라인에 `RESPAWN_GRACE_TICKS` 누락 | `NameError: name 'RESPAWN_GRACE_TICKS' is not defined` | 첫 respawn에서 즉시 발생 |
| `_init_founder_seeds`에 grace 잘못 추가 (금지 위반) | 초기 faction이 200틱 grace → Stage 4 acceptance baseline 변경 → 회귀 | Stage 4 acceptance |

---

## 프레임워크 제약

### Python `@dataclass(slots=True)`
- `Faction`은 `slots=True` — 신규 필드는 dataclass 정의 *내부*에 선언 필수. 런타임 동적 속성 추가 불가.
- 신규 필드 `grace_until_tick: int = 0`는 기존 5 필드(`id, name, founder_pid, charter, created_tick`) *뒤에* 배치 — 기존 positional 호출 호환.
- `__post_init__` 검증은 `charter`만 대상. `grace_until_tick` 검증 추가 *불필요*.

### Python `@dataclass` (slots 없음)
- `InnerWorld`는 slots 없음 — 신규 필드 추가 자유.
- `field(default_factory=dict)` 필수 — `default_factory=lambda: {}` 또는 `default={}` 사용 시 모든 인스턴스 dict 공유로 결정성 깨짐.

### NumPy RNG / 결정성
- `_derive_rng("faction_respawn", territory.id, self.time.tick)` 경로 — 변경 금지.
- grace check는 결정적 비교 (`int > int`) — RNG 경로 무영향.
- residence_ticks 누적도 결정적 (단조 증가) — RNG 무영향.

### 단일 쓰기 경로
- `persona.faction` 쓰기는 `_change_persona_faction` 유일 경로. 본 Stage 5는 이 경로 *무수정*.
- `Faction.grace_until_tick`은 신규 필드 — `_respawn_faction_tick`에서 *생성자로 초기 설정* (사후 수정 없음). 사후 수정 경로 신설 금지 ([금지] 항목 외 추가 금지).

### 변경 후 max kernel score 검증
- v6 가중치(territory 0.5, trust 0.5)에서 `max_single_tick ≈ 0.5 + 0.5*0.5 + 0.4*0.5 = 0.95`. DECAY 0.92 누적 시 ~2.4 도달.
- `THETA_JOIN=2.5`는 *살짝 보수적* — 가입 문턱이 1틱 더 길게 작동 (자연 탄생 원칙 부합).
- **THETA_JOIN 변경 금지** ([금지] 항목).

---

## 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/ontology/layers.py` | 가중치 상수 2개 변경 + 신규 상수 1개 + Faction 필드 1개 + InnerWorld 필드 1개 | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | import 1라인 + drift 면역 분기 1개 + respawn grace 2곳 + residence 누적 1곳 | 수정 |

**변경 없음 (금지)**:
- `Projects/personas/loom/PHASE-17-FACTION-CHARTER.md` (Charter 본문)
- `Projects/personas/loom/PHASE-17-FACTION-DECISIONS.md` (Decision 4 v3 본문 historic 보존)
- `Projects/personas/loom/PHASE-17-FACTION-STAGE5-DECISIONS.md` (본 Stage 5 SSoT — 본 지시서가 *읽기* 대상이지 *수정* 대상 아님)
- `Projects/personas/loom/PHASE-17-AFFILIATION-TUNE-SPEC.md` (선택 항목, 본 [필수] 작업에서 제외)
- `Projects/personas/loom/ontology/__init__.py` (export 변경 불요 — Faction/InnerWorld는 이미 export됨)
- `Projects/personas/loom/core/*.py` (multi_tick_engine.py 외)
- `Projects/personas/loom/test_*.py` (회귀 테스트 변경 금지 — 통과만)
- `Projects/personas/loom/observe_phase17_emergence.py` ([필수]에서 제외, [선택]에서만 secondary 지표 추가 가능)
- `Projects/personas/loom/data/**` (probe 결과 디렉토리 — 자동 생성)
- `readout_weights_v1.npy` 및 SNN 관련 모든 파일

---

## 검증

### 기계 검증 (Python)

작업 디렉토리: `Projects/personas/loom` (모든 명령은 이 cwd 기준)

#### 1. 문법/스타일 (ruff)

```bash
cd Projects/personas/loom
rtk proxy "py -m ruff check ontology/layers.py core/multi_tick_engine.py"
```

기대: 통과. 위반 발생 시 자동 수정 가능 항목은 `--fix` 적용 권장 (단 본 [필수] 변경 라인의 의미 보존 우선).

#### 2. 정적 타입 (mypy, optional)

```bash
rtk proxy "py -m mypy ontology/layers.py core/multi_tick_engine.py"
```

mypy 미설정 시 통과 처리. 본 변경에 신규 import만 추가 (RESPAWN_GRACE_TICKS) — 타입 변경 없음.

#### 3. 단위 테스트 — Phase 17 acceptance + 회귀 4종

**중요**: 본 프로젝트는 pytest 미사용. 각 테스트 파일은 `py <파일>` 직접 실행. [test_phase17_acceptance.py:6](test_phase17_acceptance.py#L6) "Run with: `py test_phase17_acceptance.py`" 명시.

```bash
# Phase 17 acceptance — 4 항목 자체 검증 (subprocess 기반)
rtk proxy "py test_phase17_acceptance.py"
# 기대 출력: [PASS] stable_perf_median_p95 / [PASS] faction_kernel_0_960 / [PASS] seed42_perf_line / [PASS] five_channel_determinism

# Phase 11 (경제) 회귀
rtk proxy "py test_economy.py"

# Phase 12~13 (norm/계급) 회귀
rtk proxy "py test_nomos.py"

# Phase 14 (계급 승급) — 알려진 KeyError 있음, 본 작업과 무관. *본 Stage 5에서 추가 회귀 없음*만 확인
rtk proxy "py test_class_promotion.py"

# Phase 17 handoff 계약 (Stage 4 산출물)
rtk proxy "py test_phase17_faction_handoff_contract.py"
```

각 명령은 exit 0 (PASS) 시 성공. 비제로면 stdout/stderr 마지막 2KB가 출력되므로 그것 보고.

검증 도구 미설정 시 그 사실을 명시하고 통과한 검증만 보고.

### 기능 검증 — Acceptance Gate (Stage 5 핵심)

**emergence probe 실행** (5000틱 × 3 seed):

```bash
cd Projects/personas/loom
rtk proxy "py observe_phase17_emergence.py --seeds 7,13,42 --ticks 5000 --out data/phase17_probe_stage5"
```

추정 소요: 약 3~6분 (seed당 1~2분).

**결과 위치**:
- 메인 요약: `data/phase17_probe_stage5/SUMMARY.md`
- seed별 상세: `data/phase17_probe_stage5/seed_<n>/summary.md`, `events.jsonl`

#### Primary Acceptance (필수 — 미달 시 Stage 5 미수렴)

| seed | active_factions_end | 본 Stage 5 verdict |
|------|---|---|
| 7 | **>= 2** | PASS 필수 |
| 13 | **>= 2** | PASS 필수 |
| 42 | **>= 2** | PASS 필수 |

3 seed 중 단 1건이라도 `active_factions_end < 2`면 **본 Stage 5 FAIL**.

> **주의**: probe 자체의 verdict 라벨(`PASS`/`FAIL`)은 4종 조건(`pass_diversified`, `pass_contact`, `pass_drift`, `pass_gini`)을 본다 ([observe_phase17_emergence.py:259~263](observe_phase17_emergence.py#L259)). 그 라벨과 본 Stage 5 Primary는 *다르다*. 본 Stage 5 verdict는 *오직 `final_active >= 2`*만 본다 (active_factions_end == final_active). probe의 자체 verdict는 참고용.

#### Secondary 지표 (성공 품질 — 참고용, 미달 시 Stage 5.5 격상 검토)

probe SUMMARY에서 추가 확인 (현재 형식 + [선택] 보강 시):
- `gini_mean_end >= 0.40` (현 SUMMARY 형식에 이미 포함)
- `last_500_active>=2 ratio >= 0.95` ([선택] 항목 구현 시 신규)
- `drift_source_distribution_entropy >= 0.6` ([선택] 항목 구현 시 신규)
- `residence_ticks` 분포 통계 ([선택] 항목 구현 시 신규)

### 회귀 검증 (Phase 11~16 Hard 5지표)

[test_phase17_acceptance.py](test_phase17_acceptance.py)의 다음 4 항목이 모두 PASS:
- `stable_perf_median_p95` — 틱 perf 회귀 없음
- `faction_kernel_0_960` — kernel perf 5ms 예산 내
- `seed42_perf_line` — seed 42 perf 라인
- `five_channel_determinism` — 5 채널 결정성 (InnerWorld 신규 필드가 결정성 깨뜨리지 않음을 검증)

가장 위험한 항목은 `five_channel_determinism` — `residence_ticks` field_factory 실수(`lambda: {}` 사용 등)로 인스턴스 dict 공유 발생 시 즉시 FAIL.

### 기능 테스트 시나리오 (자체 점검 — 코드 작성 시 머릿속 시뮬)

- [ ] **시나리오 A — 첫 respawn 후 grace 형성 (tick=480)**:
  - tick=480 시점에 [tick L2153](core/multi_tick_engine.py#L2153) `_commit_faction_tick()` 먼저 호출 → 그 시점에는 신규 faction 미존재 → 480 commit은 신규 grace 영향 받지 않음.
  - 직후 [tick L2154](core/multi_tick_engine.py#L2154) `_respawn_faction_tick()` 호출 → free_residents ≥ 3인 territory에서 신규 Faction X 생성, `X.grace_until_tick == 480 + 200 == 680`.
  - X.founder는 `_change_persona_faction(..., source="birth_founder")` 경유로 X 가입 + `faction_cooldown = FOUNDER_RESPAWN_EVERY(480)` 설정.
  - **단, 480 시점에 commit이 X 멤버의 drift를 평가하는 일은 *없음*** — commit이 *먼저* 호출되므로 X는 아직 존재하지 않음.

- [ ] **시나리오 B — grace 작동 (tick=528 = 480 + 48 = 다음 commit)**:
  - tick=528 commit. snapshot에 X 멤버 founder의 cur_fid=X.id 포함.
  - drift 평가 분기 진입: `current_faction = self.factions.get(X.id)` → X 객체 획득 → `X.grace_until_tick(680) > 528` 참 → `continue` → founder는 X에서 drift로 빠지지 않음. ✅
  - 단, founder는 `faction_cooldown=480` 설정되어 있어 line `if cooldown > 0 or not scores: continue`에서 일찌감치 차단됨 (이 케이스는 grace check까지 도달하지 않음). 이는 *founder*에 한정. 가입 후 다른 페르소나가 affiliation으로 X에 합류하면 그 멤버는 cooldown 짧아 grace check 도달.

- [ ] **시나리오 C — grace 종료 (tick=720 = 480 + 240)**:
  - 720 시점 commit. `X.grace_until_tick(680) > 720` 거짓 → grace 면역 분기 통과 → 정상 drift 평가. ✅

- [ ] **시나리오 D — residence 누적 정합성**:
  - 시뮬 N 페르소나, T=5000틱.
  - 각 페르소나의 `sum(inner.residence_ticks.values()) == 5000` (territory 변경 여부 무관, 매 틱 1 누적이 *어딘가에는* 기록됨).
  - 만약 합 < 5000 → 누적 누락(예: sleep 분기 내부에서만 호출). 합 > 5000 → 중복 호출(예: movement 후 다시 누적).
  - **단** 새로 spawn되는 페르소나(birth)나 사망 페르소나가 있으면 페르소나별 합은 그 페르소나의 생존 tick과 일치. 본 시뮬은 birth/death 빈도 낮으므로 100% 5000 케이스가 대다수.

- [ ] **시나리오 E — read-only 보장**:
  - 변경 후 `residence_ticks` 사용처 grep 결과는 정확히 *2건*:
    - (a) `ontology/layers.py`: `residence_ticks: dict[str, int] = field(default_factory=dict)` (필드 정의)
    - (b) `core/multi_tick_engine.py`: `inner.residence_ticks[persona.territory] = inner.residence_ticks.get(persona.territory, 0) + 1` (누적, 1 라인이지만 표현 2회 → grep -n 1건)
  - 이외 위치에 `residence_ticks` 사용처가 있다면 → [금지] 위반 (affiliation 경로 진입 의심).

- [ ] **시나리오 F — Charter v2 무파괴 보장 자체 점검**:
  - `FactionChangeSource` 정의 grep → `Literal["birth_founder", "affiliation", "drift", "conflict"]` 4종 그대로.
  - `_change_persona_faction` 시그니처 grep → 변경 없음 (인자 추가/제거 없음).
  - `# noqa: PHASE17_FACTION_SSOT_WRITE` 마커 카운트 → 변경 전후 동일 (5건 그대로: L1064, L1065, L1082, L1351, L1401).
  - SNN 코드 (`brain/`, `readout_weights_v1.npy`, 뉴런 300~349) 무수정.

---

## Rollback

### Git 기반 (권장)

```bash
# 본 Stage 5 단일 커밋이라면
git revert <stage5-commit-sha>

# 또는 두 파일만 직전 상태로
git checkout HEAD~1 -- Projects/personas/loom/ontology/layers.py Projects/personas/loom/core/multi_tick_engine.py
```

### 라인별 수동 복원 (git 사용 불가 시)

`Projects/personas/loom/ontology/layers.py`:
- L197 `W_TERRITORY_SAME = 0.5` → `W_TERRITORY_SAME = 0.3`
- L199 `W_TRUST = 0.5` → `W_TRUST = 0.8`
- L195~196 주석 v6 → v5 복원
- `Faction` dataclass에서 `grace_until_tick: int = 0` 라인 제거 (line 175 근처)
- `RESPAWN_GRACE_TICKS = 200` 상수 + 주석 블록 제거 (line 233 근처)
- `InnerWorld` dataclass에서 `residence_ticks: dict[str, int] = field(default_factory=dict)` 라인 제거 (line 906 근처)

`Projects/personas/loom/core/multi_tick_engine.py`:
- import 라인에서 `RESPAWN_GRACE_TICKS,` 제거 (L64 근처)
- L1281 `_commit_faction_tick`의 grace 면역 분기 3줄 제거
- L1342~1351 1차 respawn `Faction(...)` 생성자에서 `grace_until_tick=...` 라인 제거
- L1392~1401 2차 fallback respawn `Faction(...)` 생성자에서 `grace_until_tick=...` 라인 제거
- L348 근처 residence 누적 2줄 제거

**데이터 영향**: 시뮬 상태 영향 없음. 본 변경은 *상태 갱신 로직*이므로 git revert로 즉시 복원 가능. 기존 시뮬 결과 데이터(`data/phase17_probe_v6/` 등) 손상 없음. 단 v6 시점 acceptance baseline은 baseline 그대로 유지 (Stage 5 PASS 결과는 별도 디렉토리 `data/phase17_probe_stage5/`).

---

## 자체 점검 (작업 완료 직전, 보고 *전*)

### 1. grep 카운트 검증 (변경 흔적 정확화)

작업 디렉토리: `Projects/personas/loom`

```bash
cd Projects/personas/loom

# (a) grace_until_tick — 정확히 4건 매치 기대
rtk proxy "py -c \"import subprocess; subprocess.run(['rg', '-n', 'grace_until_tick', 'ontology/layers.py', 'core/multi_tick_engine.py'])\""
```

**기대 매치 (총 4건)**:
- `ontology/layers.py`: 1건 — Faction dataclass 필드 정의 (line 175 근처)
- `core/multi_tick_engine.py`: 3건 —
  - drift 면역 분기 1건 (line 1281 근처: `if current_faction is not None and current_faction.grace_until_tick > self.time.tick`)
  - 1차 respawn 1건 (line 1349 근처: `grace_until_tick=self.time.tick + RESPAWN_GRACE_TICKS,`)
  - 2차 respawn 1건 (line 1399 근처: 동일)

```bash
# (b) RESPAWN_GRACE_TICKS — 정확히 3건 매치 기대
rtk proxy "py -c \"import subprocess; subprocess.run(['rg', '-n', 'RESPAWN_GRACE_TICKS', 'ontology/layers.py', 'core/multi_tick_engine.py'])\""
```

**기대 매치 (총 3건)**:
- `ontology/layers.py`: 1건 — 상수 정의 (line 233~234 근처)
- `core/multi_tick_engine.py`: 3건? *No* — 실제는 import 1건 + 사용 2건(1차/2차 respawn) = 3건
  - 합계: layers.py 1 + multi_tick_engine.py 3 = **4건**. (위 카운트 정정)

```bash
# (c) residence_ticks — 정확히 2건 매치 기대
rtk proxy "py -c \"import subprocess; subprocess.run(['rg', '-n', 'residence_ticks', 'ontology/layers.py', 'core/multi_tick_engine.py'])\""
```

**기대 매치 (총 2건)**:
- `ontology/layers.py`: 1건 — InnerWorld 필드 정의 (line 906 근처)
- `core/multi_tick_engine.py`: 1건 — Stage 1 페르소나 루프 누적 (line 348 근처)
- *그 외 위치 매치 = 0건* — 만약 `_compute_affiliation_tick`이나 affiliation 계산 영역에 매치가 있다면 [금지] 위반.

### 2. Charter v2 무파괴 보장 검증

```bash
cd Projects/personas/loom

# FactionChangeSource 4종 동결 확인
rtk proxy "py -c \"import subprocess; subprocess.run(['rg', '-n', 'FactionChangeSource = Literal', 'core/multi_tick_engine.py'])\""
# 기대: 1건 매치, "Literal[\"birth_founder\", \"affiliation\", \"drift\", \"conflict\"]" 그대로

# AST whitelist 마커 카운트 (변경 전후 동일해야 함)
rtk proxy "py -c \"import subprocess; subprocess.run(['rg', '-c', 'PHASE17_FACTION_SSOT_WRITE', 'core/multi_tick_engine.py'])\""
# 기대: 5 (변경 전과 동일)
```

### 3. 변경 라인 카운트 자체 추적

```bash
rtk proxy "git diff --stat ontology/layers.py core/multi_tick_engine.py"
```

기대치 (대략):
- `ontology/layers.py`: ~10 라인 추가/수정 (가중치 2 변경 + 신규 상수 + 주석 ~4 + Faction 필드 1 + InnerWorld 필드 1)
- `core/multi_tick_engine.py`: ~8 라인 추가 (import 1 + drift 면역 3 + 1차 respawn 1 + 2차 respawn 1 + residence 2)
- 합계: ~18 LOC 변경. 30 LOC 초과 시 *스코프 이탈 의심*.

---

## 디버깅/진단 가이드 (검증 실패 시)

### Primary Acceptance FAIL — 일부 seed `active_factions_end < 2`

**1차 진단** (가장 흔함):
1. `data/phase17_probe_stage5/seed_<n>/events.jsonl`에서 `type=population` 라인의 마지막 row 확인. `active = [count for count in dist.values() if count > 0]`로 분포 확인.
2. drift 면역 분기 누락 의심. [core/multi_tick_engine.py:1281 근처](core/multi_tick_engine.py#L1281) `current_faction.grace_until_tick > self.time.tick` 분기 *3 라인*이 존재하는지 확인.
3. 1차 또는 2차 respawn에서 `grace_until_tick=` 인자 누락 의심. 두 군데 *모두* 설정되었는지 확인.

**2차 진단**:
1. `events.jsonl`에서 `type=source_cumulative`의 마지막 row 확인. drift count가 비정상적으로 높으면 면역 미작동 (drift 입력에 grace 적용 누락).
2. drift count가 0이고 흡수 발생 시 → affiliation 가입이 단일 faction에 집중. 가중치 변경이 적용되지 않았을 가능성. `W_TRUST`, `W_TERRITORY_SAME` 값 grep으로 0.5 확인.

**해결 절차**:
```bash
cd Projects/personas/loom
# 가중치 적용 여부 확인
rtk proxy "py -c \"from ontology.layers import W_TRUST, W_TERRITORY_SAME; print('W_TRUST=', W_TRUST, 'W_TERRITORY_SAME=', W_TERRITORY_SAME)\""
# 기대: W_TRUST= 0.5 W_TERRITORY_SAME= 0.5
```

### `five_channel_determinism` FAIL

가장 흔한 원인: `residence_ticks: dict[str, int] = field(default_factory=dict)`를 잘못 작성.

- ❌ `residence_ticks: dict = field(default_factory=lambda: {})` — 결정성 가능하지만 비표준
- ❌ `residence_ticks: dict = {}` — **모든 인스턴스가 같은 dict 공유 → 결정성 깨짐**
- ✅ `residence_ticks: dict[str, int] = field(default_factory=dict)` — 정답

해결:
```bash
rtk proxy "py -c \"import subprocess; subprocess.run(['rg', '-n', 'residence_ticks: dict', 'ontology/layers.py'])\""
# 기대: residence_ticks: dict[str, int] = field(default_factory=dict)
```

### `faction_kernel_0_960` FAIL (perf 회귀)

본 Stage 5 변경은 *상수 비교 1개 + dict 누적 1개* — 정상 perf 영향 무.

원인 후보:
1. drift 면역 분기에 `dict()` 또는 `list()` 같은 무거운 호출 잘못 추가.
2. residence 누적이 sleep 분기 *내부*에서 호출되어 sleep 페르소나에서 skip, 그 결과 누적 검증 시 깨짐 → 회귀 테스트가 누적 검증 포함 시 fail.

해결: 변경 라인 수 확인 (총 ~8 LOC). 그 이상이면 의도하지 않은 변경 추가 의심.

### `AttributeError: 'Faction' object has no attribute 'grace_until_tick'`

[ontology/layers.py:174 근처](ontology/layers.py#L174) Faction dataclass 정의에 신규 필드 추가 누락. `slots=True`이므로 *반드시* 정의 내부에 선언 필수.

해결:
```bash
rtk proxy "py -c \"from ontology.layers import Faction; f = Faction('a', 'b', 'c', ('토지_공유','무역_개방','재산_개인'), 0); print('grace_until_tick=', f.grace_until_tick)\""
# 기대: grace_until_tick= 0
```

### `NameError: name 'RESPAWN_GRACE_TICKS' is not defined`

[core/multi_tick_engine.py:63 근처](core/multi_tick_engine.py#L63) import 누락.

해결: import 블록에 `RESPAWN_GRACE_TICKS,` 추가 후 재실행.

---

## 보고 형식

작업 완료 시 다음 항목을 보고:

1. **변경 파일 목록** — 절대 경로 + 변경 라인 카운트 요약 (`git diff --stat` 출력 인용).
2. **기계 검증 결과** — 각 명령(ruff, mypy, py test_phase17_acceptance.py, py test_economy.py, py test_nomos.py, py test_class_promotion.py, py test_phase17_faction_handoff_contract.py) PASS/FAIL.
3. **Acceptance Gate 결과** — `data/phase17_probe_stage5/SUMMARY.md` 인용:
   - 3 seed × `active_factions_end` 값 표
   - probe 자체 verdict 라벨 (PASS/FAIL — 참고용)
   - 본 Stage 5 verdict (Primary `active_factions_end >= 2` 기준)
4. **Secondary 지표** — gini_mean_end / drift_ratio / [선택] 구현 시 last_500_active 비율 등.
5. **회귀 검증 결과** — `test_phase17_acceptance.py` 4 항목 + `test_economy.py` + `test_nomos.py` + `test_class_promotion.py`.
6. **자체 점검 결과** — grep 카운트 (grace_until_tick 4건, RESPAWN_GRACE_TICKS 4건, residence_ticks 2건) + AST 마커 5건 동일 + 변경 LOC 약 18.
7. **[선택] 항목 구현 여부** — 구현했으면 명시, 생략했으면 이유 ("선택이라 생략" 또는 "Primary PASS 후 Stage 5.5 단계에서 추가 검토 권장").
8. **이상 신호** — 검증 중 발견한 의외의 결과(예: gini 분포 평탄화, 일부 territory의 residence 편중 등) — 본 Stage 5 acceptance와 무관하더라도 Stage 5.5 입력으로 보고.

---

## 참조 자료 (구현자 — 읽기만 / 수정 금지)

| 파일 | 용도 |
|------|-----|
| [PHASE-17-FACTION-STAGE5-DECISIONS.md](PHASE-17-FACTION-STAGE5-DECISIONS.md) | 본 Stage 5 SSoT — 결정/근거 |
| [PHASE-17-FACTION-CHARTER.md](PHASE-17-FACTION-CHARTER.md) | Charter v2 — 무파괴 제약 9종 |
| [PHASE-17-FACTION-DECISIONS.md](PHASE-17-FACTION-DECISIONS.md) | Decision 4 v3 historic + R7 안건 |
| [PHASE-17-FACTION-STAGE4-CLOSURE-SPEC-addendum-v2.md](PHASE-17-FACTION-STAGE4-CLOSURE-SPEC-addendum-v2.md) | Stage 4 closure (선행) |
| [data/phase17_probe_v6/SUMMARY.md](data/phase17_probe_v6/SUMMARY.md) | Stage 5 진입 baseline (v6 collapse 결과) |
| [PHASE-17-AFFILIATION-TUNE-SPEC.md](PHASE-17-AFFILIATION-TUNE-SPEC.md) | v5 가중치 분석 (참고) |
