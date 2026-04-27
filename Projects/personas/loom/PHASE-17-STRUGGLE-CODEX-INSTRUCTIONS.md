# [기능] Phase 17 Φ-3 Struggle — grievance 응결 + uprising 발화

> 긴급도: 중간
> 선행 조건: Φ-2 Stage 6 H-lite 완료 (founder_lineage W_LINEAGE=0.2), 3 seed × 5000틱 `active_factions_end >= 2` 3/3 PASS
> 작업 유형: 기능 (백엔드 — 시뮬레이션 로직)
> DB migration: 없음
> 외부 의존: 없음

---

## 배경

Charter v2 Φ-3 진입 OR 측정([CHARTER-V2-ENTRY-CHECK.md](data/phase17_probe_stage6/CHARTER-V2-ENTRY-CHECK.md)) 결과 3 seed 전부 OR-1만 단독 충족(1/3) → Φ-3가 **OR-2 imbalance + OR-3 grievance를 자연 발생시킬 mechanism**을 도입해야 함. 본 지시서는 Phase 14 grievance 인프라 + Phase 14-B SNN 발화 + Φ-2 faction 응결의 3중 중첩에서 봉기를 자연 trigger하여 멤버 재분포로 OR-2/OR-3를 자연 충족시킨다.

근거 문서:
- [PHASE-17-STRUGGLE-CHARTER.md](PHASE-17-STRUGGLE-CHARTER.md) (Phase 1 Charter)
- [PHASE-17-STRUGGLE-DECISIONS.md](PHASE-17-STRUGGLE-DECISIONS.md) (Phase 3 Decision Card — 12 보류 항목 초기값 + 수식 확정)

---

## 작업 범위

### [필수]
1. `layers.py`: 신규 상수 5종 추가 (Phase 17 Φ-3 블록)
2. `multi_tick_engine.py`: 신규 메서드 7종 구현
   - `faction_grievance_resonance(faction_id)` (Φ-3 내부 read-only)
   - `_snn_uprising_signal_active(pid)`
   - `_pick_uprising_target(leader_pid, contacts)`
   - `_select_uprising_followers(candidate)`
   - `_spawn_branch_faction(*, founder_pid, parent_fid)`
   - `_uprising_trigger()`
   - `_emit_uprising(candidate)`
   - `_uprising_tick()` (래퍼, tick() 통합용)
3. `multi_tick_engine.py`: `tick()` 내 `_respawn_faction_tick()` 직후 `_uprising_tick()` 1줄 추가
4. `multi_tick_engine.py`: 신규 상수 5종 import
5. `ontology/__init__.py`: 신규 상수 5종 export
6. metrics 텔레메트리: `event_log`에 `"uprising"` type 추가 (probe 시 metrics.jsonl로 자동 추출)
7. 회귀 검증: `py test_phase17_acceptance.py` 전부 PASS + 신규 acceptance 3종 추가
8. probe 측정: `py observe_phase17_emergence.py --label phi3` seed 7/13/42 5000틱 → SUMMARY 자동 생성

### [선택]
- `THETA_UPRISING` 0.40 ↔ 0.30~0.50 범위 튜닝 (probe 결과 acceptance #1 FAIL 시)
- `UPRISING_FOLLOWER_MAX` 2 ↔ 1~3 범위 튜닝

### [금지]
- `_change_persona_faction` 시그니처·로직 수정
- `FactionChangeSource` Literal 변경 (4종 그대로: `birth_founder`/`affiliation`/`drift`/`conflict`)
- AST whitelist 마커 `# noqa: PHASE17_FACTION_SSOT_WRITE` 5건 추가/제거/이동
- `Faction.grace_until_tick` 수정
- `Faction.founder_lineage` (Stage 6) 수정
- `InnerWorld.grievance` 누적 수식 (`_update_grievances`) 수정 — Φ-3는 관찰자, Phase 14가 누적 책임
- `InnerWorld.residence_ticks` 수정
- SNN 뉴런 300~349 구간 변경, n_neurons 변경
- D10 7종 read-only API 추가/수정 (population/territory/charter/contact/wealth/social/grievance distribution 외형 freeze)
- `test_class_promotion.py`, `test_nomos.py`, `test_economy.py`, `test_phase17_faction_handoff_contract.py` 수정

---

## 구체 사양

### 1. `layers.py` — 신규 상수 5종

**위치**: Stage 6 H-lite 블록 (line 240~242 근처) 직후, `# 하위 호환` 블록 직전.

**추가 코드 (그대로 복사):**

```python
# ── Phase 17 Φ-3 Struggle: 봉기 발화 (uprising) (2026-04-27) ──
# 근거: Charter v2 Φ-3 진입 OR 측정에서 OR-3 grievance 0쌍 → Φ-3가 자연 발생시킬
# faction-level 응결 + SNN 발화 + 멤버 재분포 mechanism. 신규 SNN 뉴런 0건.
THETA_UPRISING = 0.40                # resonance_score 임계치 (max_lord_share × grievance_mean)
UPRISING_CHECK_INTERVAL = 48         # 봉기 검사 주기 (FACTION_COOLDOWN_TICKS와 동일)
UPRISING_GRIEVANCE_DECAY = 0.5       # 봉기 후 leader+followers grievance 감쇠 (try_exodus와 정합)
UPRISING_FOLLOWER_MAX = 2            # 동조 멤버 최대 수 (leader + 2 = 최대 3명 이동)
SNN_ANGER_FIRE_THRESHOLD = 0.6       # chiljeong[1] anger 발화 판정 (Phase 14-B 인프라)
```

### 2. `ontology/__init__.py` — export 5종 추가

기존 export 블록에서 Phase 17 상수 그룹 (`W_LINEAGE` 근처)에 추가:

```python
# ... 기존 export ...
W_LINEAGE,
# Phase 17 Φ-3 Struggle (2026-04-27)
THETA_UPRISING,
UPRISING_CHECK_INTERVAL,
UPRISING_GRIEVANCE_DECAY,
UPRISING_FOLLOWER_MAX,
SNN_ANGER_FIRE_THRESHOLD,
```

`__all__` 리스트에도 동일 5종 문자열 추가.

### 3. `multi_tick_engine.py` — 신규 상수 import

기존 상수 import 라인에서 (W_LINEAGE 근처):

```python
from ..ontology.layers import (
    # ... 기존 ...
    W_LINEAGE,
    # Phase 17 Φ-3 신규
    THETA_UPRISING,
    UPRISING_CHECK_INTERVAL,
    UPRISING_GRIEVANCE_DECAY,
    UPRISING_FOLLOWER_MAX,
    SNN_ANGER_FIRE_THRESHOLD,
    GRIEVANCE_MIN_SHARED,
    NORM_PRIMITIVE_CATALOG,
    RESPAWN_GRACE_TICKS,
    FACTION_COOLDOWN_TICKS,
    Faction,
)
```

(이미 import된 항목은 중복 제거. 신규는 `THETA_UPRISING`, `UPRISING_CHECK_INTERVAL`, `UPRISING_GRIEVANCE_DECAY`, `UPRISING_FOLLOWER_MAX`, `SNN_ANGER_FIRE_THRESHOLD` 5종.)

### 4. `multi_tick_engine.py` — 메서드 7종 구현

**위치**: 기존 `faction_grievance_targets()` 메서드 직후 (현재 line 1687 근처).

**추가 코드 (그대로 복사):**

```python
    # ─── Phase 17 Φ-3 Struggle ───────────────────────────────────────

    def faction_grievance_resonance(self, faction_id: str) -> dict:
        """faction 멤버의 lord별 grievance 응결 측정 (Φ-3 내부 read-only).

        반환: {
            "lord_counts": {lord_id: count},   # ≥ GRIEVANCE_MIN_SHARED 멤버만
            "grievance_mean": float,
            "max_lord_share": float,
            "resonance_score": float,           # max_lord_share × grievance_mean
            "top_lord_id": Optional[str],       # 최다 카운트 lord_id (tie-break sorted)
        }
        공허 faction → 모든 값 0, top_lord_id None.
        """
        if faction_id not in self.factions:
            raise ValueError(f"unknown faction_id: {faction_id!r}")
        members = self._faction_members(faction_id)
        if not members:
            return {
                "lord_counts": {},
                "grievance_mean": 0.0,
                "max_lord_share": 0.0,
                "resonance_score": 0.0,
                "top_lord_id": None,
            }
        # grievance ≥ 임계치 멤버의 lord 카운트
        lord_counts: dict[str, int] = {}
        grievance_sum = 0.0
        eligible_count = 0
        total_grievance_holders = 0
        for pid in members:
            inner = self.inners.get(pid)
            if inner is None:
                continue
            grievance_sum += float(inner.grievance)
            if (
                inner.grievance >= GRIEVANCE_MIN_SHARED
                and inner.grievance_lord_id is not None
            ):
                lord_counts[inner.grievance_lord_id] = (
                    lord_counts.get(inner.grievance_lord_id, 0) + 1
                )
                eligible_count += 1
            if inner.grievance >= GRIEVANCE_MIN_SHARED:
                total_grievance_holders += 1
        grievance_mean = grievance_sum / len(members) if members else 0.0
        if not lord_counts or total_grievance_holders == 0:
            return {
                "lord_counts": dict(lord_counts),
                "grievance_mean": grievance_mean,
                "max_lord_share": 0.0,
                "resonance_score": 0.0,
                "top_lord_id": None,
            }
        # tie-break: 카운트 동률 시 sorted(lord_id) 첫 번째
        sorted_lords = sorted(
            lord_counts.items(), key=lambda kv: (-kv[1], kv[0])
        )
        top_lord_id, top_count = sorted_lords[0]
        max_lord_share = top_count / total_grievance_holders
        resonance_score = max_lord_share * grievance_mean
        return {
            "lord_counts": dict(lord_counts),
            "grievance_mean": grievance_mean,
            "max_lord_share": max_lord_share,
            "resonance_score": resonance_score,
            "top_lord_id": top_lord_id,
        }

    def _snn_uprising_signal_active(self, pid: str) -> bool:
        """Phase 14-B chiljeong/oyok 기반 SNN 발화 검사. 신규 SNN 뉴런 0건."""
        inner = self.inners.get(pid)
        if inner is None:
            return False
        anger = float(inner.chiljeong[1])
        fear = float(inner.chiljeong[3])
        dignity = float(inner.oyok[4])
        return (
            anger >= SNN_ANGER_FIRE_THRESHOLD
            and fear < anger
            and dignity >= 0.5
        )

    def _pick_uprising_target(
        self, leader_pid: str, contacts: list[tuple[str, str]]
    ) -> str | None:
        """봉기 leader가 가입할 인접 faction 선택. None → 분파 신규 생성 의도."""
        from_fid = self.personas[leader_pid].faction
        if from_fid is None:
            return None
        candidates = sorted({
            other for pair in contacts for other in pair if other != from_fid
        })
        if not candidates:
            return None
        leader_tid = self.personas[leader_pid].territory
        if leader_tid is None:
            return candidates[0]
        # _get_neighbor_territories는 Φ-1 인프라. 미존재 시 graceful fallback.
        neighbor_tids: list[str] = []
        try:
            neighbor_tids = list(self._get_neighbor_territories(leader_tid))
        except (AttributeError, TypeError):
            neighbor_tids = []
        territory_dist = self.faction_territory_distribution()
        for fid in candidates:
            fid_territories = territory_dist.get(fid, [])
            if any(t in fid_territories for t in neighbor_tids):
                return fid
        return candidates[0]

    def _select_uprising_followers(self, candidate: dict) -> list[str]:
        """봉기 동조 멤버 선정. 최대 UPRISING_FOLLOWER_MAX명. 결정성 sort."""
        from_fid = candidate["from_faction"]
        lord_id = candidate["lord_id"]
        leader_pid = candidate["leader_pid"]
        members = self._faction_members(from_fid)
        eligible = [
            pid for pid in members
            if pid != leader_pid
            and self.inners[pid].grievance_lord_id == lord_id
            and self.inners[pid].grievance >= GRIEVANCE_MIN_SHARED
            and self.personas[pid].faction_cooldown == 0
        ]
        eligible.sort(key=lambda p: (-float(self.inners[p].grievance), p))
        return eligible[:UPRISING_FOLLOWER_MAX]

    def _spawn_branch_faction(
        self, *, founder_pid: str, parent_fid: str
    ) -> str:
        """분파 신규 faction 생성. founder_lineage 체인 계승 (Stage 6 H-lite 패턴)."""
        parent = self.factions[parent_fid]
        parent_charter = list(parent.charter)
        used = set(parent_charter)
        replacements = sorted(p for p in NORM_PRIMITIVE_CATALOG if p not in used)
        if replacements and parent_charter:
            replace_idx = self.time.tick % len(parent_charter)
            parent_charter[replace_idx] = replacements[0]
        new_charter = tuple(parent_charter) if parent_charter else ("외세_배척", "능력주의", "자연_경외")
        new_lineage = (*parent.founder_lineage, parent_fid)
        new_id = f"f-r-{founder_pid[:6]}-{self.time.tick}"
        self.factions[new_id] = Faction(
            id=new_id,
            name=f"Rebels of {parent.name}",
            founder_pid=founder_pid,
            charter=new_charter,
            created_tick=self.time.tick,
            grace_until_tick=self.time.tick + RESPAWN_GRACE_TICKS,
            founder_lineage=new_lineage,
        )
        self._faction_members_cache = {}
        self.event_log.append({
            "type": "faction_spawn",
            "tick": self.time.tick,
            "fid": new_id,
            "source": "uprising_branch",
            "parent_fid": parent_fid,
            "founder_pid": founder_pid,
        })
        return new_id

    def _uprising_trigger(self) -> list[dict]:
        """24/48틱 주기. 응결 + SNN + 인접 조건 동시 충족 시 봉기 후보 산출."""
        if self.time.tick % UPRISING_CHECK_INTERVAL != 0:
            return []
        contacts = self.factions_in_contact(radius=1)
        candidates: list[dict] = []
        for fid in sorted(self.factions):
            reso = self.faction_grievance_resonance(fid)
            if reso["resonance_score"] < THETA_UPRISING:
                continue
            top_lord = reso["top_lord_id"]
            if top_lord is None:
                continue
            # 인접 faction 검사 (분파 신규 생성도 인접 조건 충족 시에만 발화)
            fid_in_contact = any(fid in pair for pair in contacts)
            if not fid_in_contact:
                continue
            # 봉기 leader 선정: 동일 lord_id grievance 보유 + cooldown 0 + grievance 최고치
            members = self._faction_members(fid)
            eligible = [
                pid for pid in sorted(members)
                if self.inners[pid].grievance >= GRIEVANCE_MIN_SHARED
                and self.inners[pid].grievance_lord_id == top_lord
                and self.personas[pid].faction_cooldown == 0
            ]
            if not eligible:
                continue
            # tie-break: grievance 내림차순, sorted(pid)
            eligible.sort(key=lambda p: (-float(self.inners[p].grievance), p))
            leader_pid = eligible[0]
            if not self._snn_uprising_signal_active(leader_pid):
                continue
            target_fid = self._pick_uprising_target(leader_pid, contacts)
            candidates.append({
                "leader_pid": leader_pid,
                "from_faction": fid,
                "lord_id": top_lord,
                "target_faction": target_fid,
                "grievance_mean": reso["grievance_mean"],
                "resonance_score": reso["resonance_score"],
            })
        return candidates

    def _emit_uprising(self, candidate: dict) -> None:
        """봉기 발화. _change_persona_faction(source="conflict") 단일 경로."""
        leader_pid = candidate["leader_pid"]
        from_fid = candidate["from_faction"]
        target_fid = candidate["target_faction"]
        is_branch = target_fid is None
        if is_branch:
            target_fid = self._spawn_branch_faction(
                founder_pid=leader_pid, parent_fid=from_fid
            )
        followers = self._select_uprising_followers(candidate)
        # leader 먼저 이동 (faction_id 무결성)
        self._change_persona_faction(leader_pid, target_fid, source="conflict")
        for pid in followers:   # 이미 sorted된 결과
            self._change_persona_faction(pid, target_fid, source="conflict")
        # grievance 감쇠 (봉기 = 분노 해소)
        for pid in [leader_pid, *followers]:
            old_g = float(self.inners[pid].grievance)
            self.inners[pid].grievance = max(
                0.0, old_g * UPRISING_GRIEVANCE_DECAY
            )
        # 텔레메트리
        self.event_log.append({
            "type": "uprising",
            "tick": self.time.tick,
            "leader_pid": leader_pid,
            "from_faction": from_fid,
            "target_faction": target_fid,
            "branch": is_branch,
            "lord_id": candidate["lord_id"],
            "members_count": 1 + len(followers),
            "grievance_mean": round(float(candidate["grievance_mean"]), 3),
            "resonance_score": round(float(candidate["resonance_score"]), 3),
        })

    def _uprising_tick(self) -> None:
        """tick() 통합용 래퍼. trigger → emit 일괄."""
        candidates = self._uprising_trigger()
        for c in candidates:
            self._emit_uprising(c)
```

### 5. `multi_tick_engine.py` — `tick()` 통합 (1줄 추가)

**현재 코드 (line 2175 근처):**

```python
        self._respawn_faction_tick()  # Stage 3 C: absorbing state 탈출
```

**변경 후 (1줄 추가):**

```python
        self._respawn_faction_tick()  # Stage 3 C: absorbing state 탈출
        self._uprising_tick()         # Phase 17 Φ-3: grievance 응결 → 봉기 발화
```

---

## API 계약 — `faction_grievance_resonance(faction_id)`

**호출 가능 범위**: Φ-3 내부 (`_uprising_trigger`만). D10 7종 외부 API에는 추가 금지.

**입력**:
- `faction_id: str` (필수)

**반환 (read-only dict, 신규 객체)**:
```python
{
    "lord_counts": {lord_id: count, ...},       # ≥ GRIEVANCE_MIN_SHARED 멤버만 카운트
    "grievance_mean": float,                    # 전체 멤버 grievance 평균
    "max_lord_share": float,                    # top lord 카운트 / 전체 grievance 보유 멤버
    "resonance_score": float,                   # max_lord_share × grievance_mean
    "top_lord_id": Optional[str],               # 최다 카운트 lord (tie-break sorted)
}
```

**에러 케이스**:

| 상황 | 결과 | 사이드 이펙트 |
|------|------|--------------|
| `faction_id` 미존재 | `ValueError(f"unknown faction_id: {faction_id!r}")` | 없음 |
| 공허 faction (멤버 0) | 모든 값 0, `top_lord_id=None` | 없음 |
| 멤버 있으나 grievance 임계 미달 | `lord_counts={}`, `resonance_score=0.0` | 없음 |
| `inner.grievance_lord_id is None` 멤버 | lord_counts에서 제외, grievance_mean에는 포함 | 없음 |

**caller mutation 차단**: 반환 dict는 `dict(...)` 신규 객체. 외부에서 mutate해도 내부 state 무영향.

---

## tick() 통합 비즈니스 로직

`_uprising_tick()`은 **24/48틱 주기 read-only 단계 호출 + 단일 SSoT write**:

1. `_uprising_trigger()` → 후보 list 산출 (read-only)
   - tick % 48 == 0 검사
   - `factions_in_contact(radius=1)` 호출 (D10 #4)
   - 각 faction에 대해 `faction_grievance_resonance` (Φ-3 내부)
   - resonance ≥ THETA_UPRISING + 인접 + leader eligible + SNN 발화 동시 충족
2. `_emit_uprising(c)` → 단일 변경 경로
   - 분파면 `_spawn_branch_faction` (Faction 등록 + event)
   - `_change_persona_faction(source="conflict")` 호출 (AST whitelist 통과)
   - `inner.grievance` 감쇠 (Phase 14 인프라 필드 직접 갱신, AST whitelist 영향 없음)
   - `event_log.append({"type": "uprising", ...})`

**무파괴 9 보장 자체 점검**:
- D10 7종: 호출만, mutation 0건 ✓
- AST whitelist 5건: 신규 마커 0건, 기존 5건 무수정 ✓
- FactionChangeSource 4종: `"conflict"` 재사용 ✓
- SNN n_neurons=1000: chiljeong/oyok 읽기만 ✓
- grace_until_tick: 분파 신규 시 `tick + RESPAWN_GRACE_TICKS` 설정 ✓
- residence_ticks: 무수정 ✓
- 공허 정합: factionRef None 유지 (24틱 commit이 갱신) ✓
- Kernel SSoT: affiliation_scores 직접 mutation 0건 ✓
- Double-buffer commit: 무수정 ✓

---

## 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/ontology/layers.py` | 상수 5종 추가 (Phase 17 Φ-3 블록) | 수정 |
| `Projects/personas/loom/ontology/__init__.py` | export 5종 추가 | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | 신규 import 5종 + 메서드 7종 + tick() 1줄 | 수정 |
| `Projects/personas/loom/test_phase17_acceptance.py` | acceptance 3종 추가 (uprising/grievance_pairs/dom_share) | 수정 |

**변경 없음 (금지)**:
- `Projects/personas/loom/test_phase17_faction_handoff_contract.py` (D10 7종 freeze 검증)
- `Projects/personas/loom/test_class_promotion.py`, `test_nomos.py`, `test_economy.py`
- `Projects/personas/loom/PHASE-17-FACTION-CHARTER.md` (Φ-2 closed)
- `Projects/personas/loom/scripts/phase17_charter_v2_entry_check.py` (read-only 측정)
- `Projects/personas/loom/data/phase17_probe_v6/`, `data/phase17_probe_stage6/` (보존 데이터)
- AST whitelist 마커 5건 모든 line

---

## 검증

### 기계 검증 (필수)

```bash
cd Projects/personas/loom
py -m pytest test_phase17_acceptance.py -v
py -m pytest test_phase17_faction_handoff_contract.py -v   # 12/12 PASS 유지
py -m pytest test_class_promotion.py test_nomos.py test_economy.py -v
```

### 기능 테스트 시나리오 (필수)

`test_phase17_acceptance.py`에 추가:

```python
def test_phi3_uprising_emerges_under_grievance_pressure():
    """Φ-3 acceptance #1: seed 7/13/42 5000틱 uprising_event ≥ 1 (3/3)."""
    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        uprisings = [e for e in engine.event_log if e["type"] == "uprising"]
        assert len(uprisings) >= 1, (
            f"seed {seed}: 5000 ticks 내 uprising 0건. "
            f"THETA_UPRISING={THETA_UPRISING} 또는 SNN_ANGER_FIRE_THRESHOLD 튜닝 필요"
        )

def test_phi3_grievance_pairs_resonate():
    """Φ-3 acceptance #2: grievance_pairs_end ≥ 1 (3/3)."""
    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        targets = engine.faction_grievance_targets()
        # 같은 lord_id를 ≥ 2명씩 가진 faction 쌍 카운트
        by_lord: dict[str, list[str]] = {}
        for fid, lord_map in targets.items():
            for lord_id, cnt in lord_map.items():
                if cnt >= 2:
                    by_lord.setdefault(lord_id, []).append(fid)
        pair_count = sum(
            len(fids) * (len(fids) - 1) // 2
            for fids in by_lord.values() if len(fids) >= 2
        )
        assert pair_count >= 1, f"seed {seed}: grievance_pairs 0쌍"

def test_phi3_dom_share_natural_imbalance():
    """Φ-3 acceptance #3: dom_share_end ≥ 0.50 (3/3, OR-2 자연 충족)."""
    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        pop = engine.faction_population_distribution()
        if not pop:
            assert False, f"seed {seed}: empty population"
        total = sum(pop.values())
        top = max(pop.values()) if pop else 0
        share = top / total if total else 0.0
        assert share >= 0.50, (
            f"seed {seed}: dom_share={share:.3f} < 0.50. 봉기 후 멤버 재분포 부족"
        )

def test_phi3_no_deaths():
    """Φ-3 무사망 보장: population_total 보존."""
    for seed in [7, 13, 42]:
        engine_start = run_simulation(seed=seed, ticks=1)
        engine_end = run_simulation(seed=seed, ticks=5000)
        assert sum(engine_end.faction_population_distribution().values()) >= sum(
            engine_start.faction_population_distribution().values()
        ) - 1   # ±1 허용 (Stage 3 anti-collapse 잔여 영향)

def test_phi3_branch_lineage_chain():
    """분파 신규 faction의 founder_lineage가 부모 fid 포함."""
    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        branches = [
            e for e in engine.event_log
            if e["type"] == "faction_spawn" and e.get("source") == "uprising_branch"
        ]
        for b in branches:
            new_fid = b["fid"]
            parent_fid = b["parent_fid"]
            new_faction = engine.factions[new_fid]
            assert parent_fid in new_faction.founder_lineage, (
                f"분파 {new_fid}의 founder_lineage에 부모 {parent_fid} 없음: "
                f"{new_faction.founder_lineage}"
            )

def test_phi3_determinism_seed42():
    """phi2_phi3_hash 결정성: seed=42 5000틱 2회 실행 hash 일치."""
    h1 = run_simulation_hash(seed=42, ticks=5000)
    h2 = run_simulation_hash(seed=42, ticks=5000)
    assert h1 == h2, f"determinism break: {h1} vs {h2}"
```

(`run_simulation` / `run_simulation_hash` 헬퍼는 기존 `test_phase17_acceptance.py` 패턴 계승.)

### 계약 검증 (필수)

기존 `test_phase17_faction_handoff_contract.py` **12/12 PASS 유지**:
- D10 7종 read-only freeze (population/territory/charter/contact/wealth/social/grievance distribution)
- `_change_persona_faction` SSoT 단일 경로
- `FactionChangeSource` 4종 freeze
- AST whitelist 5건 무수정

### Probe 측정 (필수)

```bash
cd Projects/personas/loom
py observe_phase17_emergence.py --label phi3 --seeds 7 13 42 --ticks 5000
py scripts/phase17_charter_v2_entry_check.py   # 1.6 측정 도구 재사용
```

생성 산출물:
- `data/phase17_probe_phi3/seed-7/metrics.jsonl` (3 seed)
- `data/phase17_probe_phi3/seed-7/summary.md`
- `data/phase17_probe_phi3/SUMMARY.md` (3 seed 통합)

SUMMARY 형식: [PHASE-17-STRUGGLE-DECISIONS.md §D8](PHASE-17-STRUGGLE-DECISIONS.md) 참조.

### 결정성 검증 (필수)

```bash
py -m pytest test_phase17_acceptance.py::test_phi3_determinism_seed42 -v
py -m pytest test_phase17_acceptance.py::test_five_channel_determinism -v
```

기존 `test_five_channel_determinism`이 PASS 유지하면서 신규 `test_phi3_determinism_seed42` PASS.

### 성능 검증 (필수)

```bash
py observe_phase17_emergence.py --label phi3-perf --seeds 42 --ticks 1000 --measure-tick-time
```

평균 tick time ≤ 250ms (현 154.4ms, Φ-3 예산 ≤ 5ms).

---

## Rollback

신규 코드 1 commit으로 진행 → `git revert <hash>` 1회로 완전 복구.

신규 추가 항목만 변경:
- 상수 5종 (layers.py 추가 라인)
- export 5종 (__init__.py 추가 라인)
- 메서드 7종 + tick() 1줄 (multi_tick_engine.py 추가 라인)
- acceptance 6종 추가 (test_phase17_acceptance.py 추가 라인)

기존 코드 라인 수정 0건. 데이터 영향 0 (probe 디렉토리는 신규 생성).

---

## 자체 검증 체크리스트

### 공통 ✅
- [x] 메타 (긴급도/선행/유형/migration/의존)
- [x] 배경 (Charter v2 측정 결과 + Phase 14/14-B 인프라 위치)
- [x] [필수/선택/금지] 태그
- [x] 변경 파일 표 + "변경 없음" 명시
- [x] 기계 검증 (pytest 3 파일)
- [x] Rollback (1 commit revert)

### 기능 작업 ✅
- [x] API 계약 (`faction_grievance_resonance` JSON shape)
- [x] 에러 케이스 테이블 (4종)
- [x] 비즈니스 로직 의사코드 (tick() 통합 단계)
- [x] 기능 테스트 시나리오 6종 (acceptance 3 + 무사망 + lineage + 결정성)

### 금기 패턴 ✅
- [x] "참고", "적절히", "알아서" 등 모호 표현 없음
- [x] 코드 블록 동반 (모든 신규 코드 그대로 복사 가능)
- [x] 단일 작업 유형 (기능 백엔드)

---

## GPT/Codex 전달 프롬프트 템플릿

```
당신은 loom persona life simulator의 시니어 백엔드 개발자입니다.

## 프로젝트 경로
c:\Users\haj\projects\subagent-orchestrator

## 기술 스택
Python 3.x, NumPy, dataclass(slots=True), pytest. SNN 통합(Phase 14-B), faction registry(Phase 17 Φ-2).

## 작업 지시서
Projects/personas/loom/PHASE-17-STRUGGLE-CODEX-INSTRUCTIONS.md 파일을 그대로 따라 구현하세요.

## 규칙 (절대 준수)
1. 지시서의 [필수] 항목 100% 구현. [금지] 항목 절대 건드리지 말 것.
2. 지시서에 포함된 코드 블록은 직접 복사해서 반영. "해석"하지 말 것.
3. 무파괴 9 보장 점검: D10 7종 read-only / AST whitelist 5건 / FactionChangeSource 4종.
4. 검증 순서:
   a. py -m pytest test_phase17_faction_handoff_contract.py -v   (12/12 PASS 필수)
   b. py -m pytest test_phase17_acceptance.py -v
   c. py -m pytest test_class_promotion.py test_nomos.py test_economy.py -v
   d. py observe_phase17_emergence.py --label phi3 --seeds 7 13 42 --ticks 5000
   e. py scripts/phase17_charter_v2_entry_check.py   (재측정)
5. 검증 실패 시 재작업, 통과할 때까지 반복.
6. acceptance #1 FAIL (uprising 0건) 시 THETA_UPRISING 0.05 단계씩 하향 (0.40→0.35→0.30) 후 재측정.
7. 보고 내용:
   - 변경 파일 목록 (4파일)
   - 각 검증 단계 통과 여부
   - probe SUMMARY (acceptance 3종 PASS/FAIL)
   - 튜닝 시 최종 THETA_UPRISING 값
```
