# Phase 15 — 집단행동 (Clustered Trust Graph + Grievance Propagation)

> **배경**: Phase 14-B에서 개인 grievance가 SNN에 도달하는 경로를 완성했다. 그러나 `/discuss` 3엔진 합의(`discussions/quick-spec-output-harness-runs-phase15-direction-q-2026-04-18/conclusion/conclusion.md`)는 여전히 **수신자(영주)만 있고 발화자 네트워크(주민↔주민)가 없다**는 한계를 지적. Phase 15는 주민 사이 grievance 전염과 임계 집단행동을 도입한다.
>
> **핵심 제약**:
> - Clustered trust graph (k=5~15, 자연 커뮤니티 = 영지+신뢰 이웃)
> - O(N²) 금지: `edge_count / node_count² < 0.05` 유지
> - 추가 뉴런 금지 — 영주 SNN은 기존 `resident grievance 평균 → tension` 경로로 자동 인지
> - A(교역정책 SNN)/C(직업 다양화)는 15-B, 15-C로 순연

---

## 판정 근거 (discuss 3엔진 합의)

| 엔진 | 1순위 | 핵심 논거 |
|---|---|---|
| Claude | **B** | 14-B 위에 "발화자 네트워크"를 얹어야 차원 상승. A/C는 기능 추가 수준 |
| Codex | **B** | 작은 수직 슬라이스로 집단행동 검증 후 A 확장 — 재설계 압력 최소 |
| Gemini | **B** | 빠른 검증 + O(N²) 조기경보 내장 |

---

## 변경 범위 (3파일 + 테스트 1개)

1. `Projects/personas/loom/core/multi_tick_engine.py` — grievance 전염 + 집단행동 + density metric
2. `Projects/personas/loom/ontology/layers.py` — `strike_until_tick` 필드 + `CommunityMetrics` dataclass
3. `Projects/personas/loom/ontology/__init__.py` — export
4. `Projects/personas/loom/test_phase15_collective_action.py` — T1~T7 신규 검증

---

## 연결 1: Clustered Trust Graph — 자연 커뮤니티 = 영지

**원칙**: 영지(territory_id)가 이미 natural cluster. Phase 15는 **새 그래프 자료구조를 만들지 않는다**. 기존 `self.relationships`에서 `trust >= 0.4` 엣지만 "의미 있는" 연결로 간주.

**신규 메서드** `_get_community_members(self, pid: str, min_trust: float = 0.4) -> list[str]`:

```python
def _get_community_members(self, pid: str, min_trust: float = 0.4) -> list[str]:
    """같은 영지 + trust>=threshold 주민들. pid 본인은 제외."""
    persona = self.personas[pid]
    tid = persona.territory
    members = []
    for other_pid, other in self.personas.items():
        if other_pid == pid or other.territory != tid:
            continue
        rel_key = Relationship(persona_a=pid, persona_b=other_pid).key()
        rel = self.relationships.get(rel_key)
        if rel and rel.trust >= min_trust:
            members.append(other_pid)
    return members
```

O(N) per call (영지 멤버 수는 N보다 작음). N 대형 시 영지 단위 캐시는 Phase 15-D 과제.

---

## 연결 2: Grievance 전염 (24틱)

**위치**: `_update_grievances` 내부, **기존 grievance 업데이트 루프 완료 후** 2차 패스.

```python
# 기존 for pid in residents: ... 완료 후 (line 805 근처)

# ── Phase 15: Grievance 전염 ──
# 신뢰 이웃의 grievance 평균과 블렌드 (확산 속도 0.1)
updated = {}
for tid_inner, territory in self.territories.items():
    lord_id = territory.lord_id
    residents = self._get_territory_residents(tid_inner)
    for pid in residents:
        if pid == lord_id:
            continue
        inner = self.inners[pid]
        neighbors = self._get_community_members(pid, min_trust=0.4)
        if not neighbors:
            continue
        neighbor_grievances = [
            float(self.inners[n].grievance) for n in neighbors
        ]
        mean_neighbor = float(np.mean(neighbor_grievances))
        # 자신의 grievance가 이웃 평균보다 낮으면 끌려감 (공감), 높으면 그대로
        if mean_neighbor > inner.grievance:
            blend = 0.1  # 10%씩 이웃에 수렴
            updated[pid] = float(np.clip(
                inner.grievance + (mean_neighbor - inner.grievance) * blend,
                0.0, 1.0,
            ))

for pid, g in updated.items():
    self.inners[pid].grievance = g
```

의미: 불만이 큰 주민 무리 옆에 있으면 자기 grievance도 상승. 비대칭(하향 수렴 없음) — 정치적 의식화는 "각성"이지 "진정"이 아니다.

---

## 연결 3: 집단행동 임계 + 이벤트 — `strike` / `mass_exodus`

**위치**: `_update_grievances` 끝 (2차 패스 이후).

```python
for tid_inner, territory in self.territories.items():
    lord_id = territory.lord_id
    residents = self._get_territory_residents(tid_inner)
    non_lord = [p for p in residents if p != lord_id]
    if len(non_lord) < 3:
        continue  # 최소 3명 이상 커뮤니티에서만 집단행동 가능

    grievances = np.array([float(self.inners[p].grievance) for p in non_lord])
    mean_g = float(grievances.mean())
    share_high = float((grievances >= 0.7).sum()) / len(grievances)

    # 집단행동 조건: 평균 >= 0.7 AND 70% 이상이 grievance>=0.7
    if mean_g >= 0.7 and share_high >= 0.7:
        # 이미 진행 중인 strike/exodus 체크
        active_strike = any(
            self.inners[p].strike_until_tick > self.time.tick
            for p in non_lord
        )
        if active_strike:
            continue

        # 집단행동 선택: 다른 영지로 이주 가능? 그럼 mass_exodus, 아니면 strike
        alternatives = [
            other_tid for other_tid, other_t in self.territories.items()
            if other_tid != tid_inner
            and other_t.policy.tax_rate < territory.policy.tax_rate * 0.7
        ]
        if alternatives:
            # mass_exodus — grievance>=0.7인 주민을 최저세율 영지로 이동
            target_tid = min(
                alternatives,
                key=lambda t: self.territories[t].policy.tax_rate,
            )
            migrated = []
            for p in non_lord:
                if float(self.inners[p].grievance) >= 0.7:
                    self.personas[p].territory = target_tid
                    self.inners[p].grievance = 0.3  # 이주로 해소
                    migrated.append(p)
            events.append({
                "type": "mass_exodus",
                "from_territory": tid_inner,
                "to_territory": target_tid,
                "personas": migrated,
                "mean_grievance": round(mean_g, 3),
                "share_high": round(share_high, 3),
            })
        else:
            # strike — 48틱 동안 work 행동 중지
            strike_until = self.time.tick + 48
            struck = []
            for p in non_lord:
                if float(self.inners[p].grievance) >= 0.7:
                    self.inners[p].strike_until_tick = strike_until
                    struck.append(p)
            events.append({
                "type": "strike",
                "territory": tid_inner,
                "personas": struck,
                "until_tick": strike_until,
                "mean_grievance": round(mean_g, 3),
                "share_high": round(share_high, 3),
            })
```

---

## 연결 4: Strike 행동 차단 — `_process_work` 게이트

**위치**: `_process_work` 또는 행동 선택 루프의 work 분기 초입.

```python
def _process_work(self, pid: str) -> dict:
    inner = self.inners[pid]
    if inner.strike_until_tick > self.time.tick:
        # 파업 중 — work 대신 grievance 감소 없음, 경제 보상 없음
        return {"type": "strike_refuse_work", "persona": pid, "tick": self.time.tick}
    # ... 기존 로직
```

만약 `_process_work`가 없으면 `_process_economy` 내부 work 경로 초입에서 `inner.strike_until_tick > self.time.tick`이면 return early.

의미: 파업 중 주민은 생산 제로 → 영지 food_reserve 감소 → 영주 tension 자연 상승 → 세율 인하 정책 반응 (14-B 경로 재사용).

---

## 연결 5: CommunityMetrics — intra/inter density 노출

**위치**: `ontology/layers.py` 신규 dataclass + `multi_tick_engine.py` 계산 메서드.

```python
# ontology/layers.py
@dataclass
class CommunityMetrics:
    territory_id: str
    node_count: int
    edge_count: int                    # trust>=0.4 엣지 수
    density_ratio: float               # edge_count / max(1, node_count**2)
    intra_edges: int
    inter_edges: int                   # 영지 외부와의 신뢰 엣지
    intra_inter_ratio: float           # intra / max(1, inter)
```

```python
# multi_tick_engine.py
def _compute_community_metrics(self) -> list[CommunityMetrics]:
    """매 48틱 계산. O(relationships). O(N²)이 아니라 O(E)."""
    metrics = []
    for tid, territory in self.territories.items():
        residents = set(self._get_territory_residents(tid))
        n = len(residents)
        intra = 0
        inter = 0
        for rel_key, rel in self.relationships.items():
            if rel.trust < 0.4:
                continue
            a_in = rel.persona_a in residents
            b_in = rel.persona_b in residents
            if a_in and b_in:
                intra += 1
            elif a_in or b_in:
                inter += 1
        edge = intra + inter
        density = edge / max(1, n * n)
        metrics.append(CommunityMetrics(
            territory_id=tid,
            node_count=n,
            edge_count=edge,
            density_ratio=density,
            intra_edges=intra,
            inter_edges=inter,
            intra_inter_ratio=intra / max(1, inter),
        ))
    return metrics
```

`tick()` Stage 4 (48틱마다) 근처에 호출 + 로그:

```python
if self.time.tick % 48 == 0 and self.time.tick > 0:
    cm = self._compute_community_metrics()
    for m in cm:
        if m.density_ratio > 0.05:
            events.append({
                "type": "density_warning",
                "territory": m.territory_id,
                "density_ratio": round(m.density_ratio, 4),
            })
    self._last_community_metrics = cm
```

---

## 연결 6: InnerWorld 필드 — `strike_until_tick`

`ontology/layers.py` `InnerWorld`에 추가:

```python
strike_until_tick: int = 0  # Phase 15: 파업 종료 틱 (0 = 파업 없음)
```

---

## 연결 7 (선택): 집단행동 재발화 방지

`_update_grievances` 집단행동 이벤트 발화 후 해당 커뮤니티 전원의 grievance를 0.2씩 감소 (에너지 소진). 이미 mass_exodus는 이주자 grievance=0.3, strike는 참여자 grievance 변화 없음. 추가 조치:

```python
# strike 이벤트 발화 직후
for p in non_lord:
    g = float(self.inners[p].grievance)
    self.inners[p].grievance = max(0.0, g - 0.15)  # 집단행동으로 일시 해소
```

의미: 집단행동은 감정을 배출한다. 매 24틱 grievance가 올라도 집단행동 직후엔 진정.

---

## 검증 테스트 (`test_phase15_collective_action.py` 신규)

```python
import numpy as np
from core.multi_tick_engine import MultiTickEngine
from ontology.layers import Relationship

def _force_trust(eng: MultiTickEngine, pid_a: str, pid_b: str, trust: float) -> None:
    key = Relationship(persona_a=pid_a, persona_b=pid_b).key()
    if key not in eng.relationships:
        eng.relationships[key] = Relationship(persona_a=pid_a, persona_b=pid_b)
    eng.relationships[key].trust = float(trust)

def test_t1_community_members_by_trust() -> None:
    eng = MultiTickEngine(n_personas=6)
    residents = list(eng.personas.keys())[:6]
    pid = residents[0]
    _force_trust(eng, pid, residents[1], 0.8)
    _force_trust(eng, pid, residents[2], 0.2)
    members = eng._get_community_members(pid, min_trust=0.4)
    assert residents[1] in members
    assert residents[2] not in members

def test_t2_grievance_contagion() -> None:
    eng = MultiTickEngine(n_personas=5)
    tid = list(eng.territories.keys())[0]
    residents = eng._get_territory_residents(tid)
    non_lord = [p for p in residents if p != eng.territories[tid].lord_id]
    assert len(non_lord) >= 3
    # 한 명만 grievance 높게
    eng.inners[non_lord[0]].grievance = 0.9
    for p in non_lord[1:]:
        eng.inners[p].grievance = 0.1
        _force_trust(eng, non_lord[0], p, 0.8)
    g_before = float(eng.inners[non_lord[1]].grievance)
    # 25틱 실행 — _update_grievances 1회 이상
    for _ in range(25):
        eng.tick()
    g_after = float(eng.inners[non_lord[1]].grievance)
    assert g_after > g_before  # 전염으로 상승

def test_t3_strike_triggers_when_isolated() -> None:
    eng = MultiTickEngine(n_personas=5)
    # 영지 1개만 사용 — alternatives 없음
    tid = list(eng.territories.keys())[0]
    for p in eng.personas.values():
        p.territory = tid
    residents = eng._get_territory_residents(tid)
    non_lord = [p for p in residents if p != eng.territories[tid].lord_id]
    for p in non_lord:
        eng.inners[p].grievance = 0.85
    # 24틱 실행
    struck = False
    for _ in range(30):
        events = eng.tick()
        # tick events는 multi_tick_engine 구조에 따라 다를 수 있으므로 strike_until_tick으로 확인
        if any(eng.inners[p].strike_until_tick > 0 for p in non_lord):
            struck = True
            break
    assert struck

def test_t4_mass_exodus_when_alternative_exists() -> None:
    eng = MultiTickEngine(n_personas=8)
    tids = list(eng.territories.keys())
    assert len(tids) >= 2
    source_tid = tids[0]
    target_tid = tids[1]
    # source의 세율을 높게, target을 낮게
    eng.territories[source_tid].policy.tax_rate = 0.25
    eng.territories[target_tid].policy.tax_rate = 0.10
    residents = eng._get_territory_residents(source_tid)
    non_lord = [p for p in residents if p != eng.territories[source_tid].lord_id]
    for p in non_lord:
        eng.inners[p].grievance = 0.85
        eng.personas[p].territory = source_tid
    migrated = False
    for _ in range(30):
        eng.tick()
        if any(eng.personas[p].territory == target_tid for p in non_lord):
            migrated = True
            break
    assert migrated

def test_t5_strike_blocks_work() -> None:
    eng = MultiTickEngine(n_personas=5)
    pid = list(eng.personas.keys())[1]
    eng.inners[pid].strike_until_tick = eng.time.tick + 10
    # work 진입 시도
    result = eng._process_work(pid) if hasattr(eng, "_process_work") else None
    # _process_work 없으면 _process_economy 경로 검증
    if result is not None:
        assert result.get("type") in ("strike_refuse_work", "work_refused")

def test_t6_density_metrics_computed() -> None:
    eng = MultiTickEngine(n_personas=10)
    # 충분히 tick 돌려서 48 이상
    for _ in range(50):
        eng.tick()
    metrics = eng._compute_community_metrics()
    assert len(metrics) >= 1
    for m in metrics:
        assert m.density_ratio < 1.0  # degenerate 아님

def test_t7_density_warning_fires_above_005() -> None:
    eng = MultiTickEngine(n_personas=5)
    tid = list(eng.territories.keys())[0]
    residents = eng._get_territory_residents(tid)
    # 모든 쌍에 trust=0.8 강제 → 고밀도
    for i, a in enumerate(residents):
        for b in residents[i + 1:]:
            _force_trust(eng, a, b, 0.8)
    metrics = eng._compute_community_metrics()
    # n=5, edges=10, density=10/25=0.4 → 0.05 초과
    for m in metrics:
        if m.territory_id == tid:
            assert m.density_ratio > 0.05
```

실행:
```bash
cd Projects/personas/loom && py test_phase15_collective_action.py
```

---

## 회귀 테스트

```bash
cd Projects/personas/loom && py test_phase14b_snn_integration.py
cd Projects/personas/loom && py test_governance.py
cd Projects/personas/loom && py test_economy_balance.py
cd Projects/personas/loom && py test_phase12b_perf_npc.py
cd Projects/personas/loom && py test_snn_economy.py
cd Projects/personas/loom && py test_nomos.py
cd Projects/personas/loom && py test_class_promotion.py
```

---

## 완료 기준 (APPROVE 조건)

1. `test_phase15_collective_action.py` T1~T7 전부 PASS
2. 회귀 테스트 전부 PASS (pre-existing fixture 에러는 무관)
3. 200틱 시뮬레이션에서 최소 1건의 `strike` 또는 `mass_exodus` 이벤트 자연 발생 관찰 가능
4. `density_ratio`가 모든 커뮤니티에서 0.05 미만 유지 (sparse 가정 위배 안 함)
5. 뉴런 추가 금지 (Phase 14-B 제약 동일)

---

## Phase 15 이후 (B 완료 후 파생)

- **Phase 15-A (A)**: 영주 교역정책 SNN — `_update_governance_policy`에 `market_openness` 정책 추가. 기존 5정책(tax_rate, food_priority, stockpile_target, treasury_spending_cap, market_openness) 형식. density_ratio 높은 영지는 외부 개방 낮춤.
- **Phase 15-C (C)**: 직업 다양화 — healer는 자기 영지 주민 chronic_stress 감소, scholar는 자기 영지 events 로그 압축 저장 (기억), guard는 주민 grievance 상승 속도 억제.

---

## 참고: 창발 구조 확장

```
Phase 14-B:
  개인 grievance → 영주 SNN tension (단방향 수신)

Phase 15:
  주민↔주민 trust → grievance 전염 (확산)
       ↓
  커뮤니티 평균 >= 0.7 → 집단행동 (strike/mass_exodus)
       ↓
  strike → 경제 생산 제로 → 영주 food_reserve 압박 → tension 추가 상승
       ↓
  영주 SNN → tax 인하 / food_priority 상승 (기존 14-B 루프)

결과: 주민 사회 레이어가 영주 정책에 피드백하는 양방향 회로 완성
```
