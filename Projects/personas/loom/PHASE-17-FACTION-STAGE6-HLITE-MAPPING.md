# Phase 17 Φ-2 Stage 6 — H-lite founder_lineage FactionChangeSource 4종 매핑 증명

> 작성: 2026-04-26  
> 목적: H-lite 구현 전 SSoT 무파괴 증명. Codex Stage 6 지시서 입력용.  
> 결론: **founder_lineage는 score 계산 인자. FactionChangeSource 4종 불변.**

---

## 1. 현재 SSoT 구조 확인

### FactionChangeSource (multi_tick_engine.py:88)

```python
FactionChangeSource = Literal["birth_founder", "affiliation", "drift", "conflict"]
```

### 유일 쓰기 경로 (multi_tick_engine.py:1049~1078)

```python
def _change_persona_faction(self, pid, new_faction_id, *, source: FactionChangeSource):
    if source not in ("birth_founder", "affiliation", "drift", "conflict"):
        raise ValueError(...)
    ...
    persona.faction = new_faction_id  # noqa: PHASE17_FACTION_SSOT_WRITE
```

### 현재 소환 지점 3곳

| source | 호출 위치 | 설명 |
|--------|-----------|------|
| `"affiliation"` | L1276 `_commit_faction_tick` | 미소속 → 최고score faction 가입 |
| `"drift"` | L1287 `_commit_faction_tick` | 소속 → 더 높은score faction 이탈 |
| `"birth_founder"` | L1357/1408/1459 `_respawn_faction_tick` | 신규 faction 창설 시 founder 등록 |
| `"conflict"` | (미구현, Φ-3 예약) | — |

---

## 2. H-lite 설계

### 목표

`founder_lineage` identity affinity를 `affiliation_score` 계산에 추가.  
같은 founder 계보를 공유하는 faction과의 결속력을 높여 drift 방향성에 계보 선호 반영.

### founder_lineage 정의

```python
@dataclass(slots=True)
class Faction:
    ...
    founder_lineage: tuple[str, ...] = field(default_factory=tuple)
    # founder_pid들의 체인 — (현재 창설자, 이전 faction 창설자, ...)
    # birth_founder respawn 시: 기존 faction이 있으면 그 founder_pid를 lineage에 추가
```

### score 계산 추가 항목 (W_LINEAGE)

```
affiliation_score(pid, faction) +=
    W_LINEAGE × lineage_overlap(pid.faction.founder_lineage, faction.founder_lineage)

lineage_overlap = len(set(A) ∩ set(B)) / max(len(A), len(B), 1)
```

상수 제안: `W_LINEAGE = 0.2` (W_TRUST=W_TERRITORY_SAME=0.5의 40% 수준)

---

## 3. 4종 매핑 증명

founder_lineage 변화로 인한 faction 이동이 기존 4종 source 중 어디로 분류되는가:

| 시나리오 | 실제 발생 경로 | FactionChangeSource | 증명 |
|---------|--------------|:-------------------:|------|
| 같은 계보 faction으로 신규 가입 | lineage_overlap 보정 → affiliation_score 상승 → THETA_JOIN 초과 | **`"affiliation"`** | score 계산 인자일 뿐, 가입 경로는 동일 |
| 같은 계보 faction으로 이탈 | lineage_overlap 보정 → best_score gap 확대 → dynamic_margin 초과 | **`"drift"`** | 기존 drift 경로, score 산출 수치만 변경 |
| founder 계보 생성 (respawn) | `_respawn_faction_tick`: lineage에 이전 founder_pid 추가 | **`"birth_founder"`** | respawn 경로 그대로, lineage 필드만 추가 |
| 갈등으로 계보 단절 | (Φ-3 미구현) | `"conflict"` 예약 | 미해당 |

**결론: founder_lineage는 `_update_affiliation_scores` 내부 계산 인자.**  
`_change_persona_faction` 호출 source는 기존 4종 그대로. **SSoT 무파괴 증명 완료.**

---

## 4. Charter v2 무파괴 체크리스트

| 보장 항목 | H-lite 영향 | 상태 |
|-----------|------------|:----:|
| FactionChangeSource 4종 | 추가 없음 | ✅ |
| AST whitelist (`PHASE17_FACTION_SSOT_WRITE`) 5건 | persona.faction 쓰기 경로 불변 | ✅ |
| D10 5채널 (birth_founder/affiliation/drift/conflict/territory) | 신규 채널 없음 | ✅ |
| SNN 뉴런 300~349 동결 | affiliation_score 계산 변경은 SNN 미침 | ✅ |
| Faction.grace_until_tick (Stage 5) | 무수정 | ✅ |
| InnerWorld.residence_ticks (Stage 5 D) | 무수정 | ✅ |

---

## 5. 구현 범위 (Stage 6)

### 변경 파일: layers.py + multi_tick_engine.py

**layers.py 변경 (3항목)**
1. `Faction.founder_lineage: tuple[str, ...] = field(default_factory=tuple)` 추가 (slots=True 호환)
2. `W_LINEAGE = 0.2` 상수 추가 (Phase 17 Stage 6 블록)
3. export: `__init__.py`에 `W_LINEAGE` 추가

**multi_tick_engine.py 변경 (2항목)**
1. `_update_affiliation_scores`에 lineage_overlap 계산 + W_LINEAGE 가산
2. `_respawn_faction_tick`에서 신규 faction 생성 시 founder_lineage 체인 추가  
   (이전 소멸 faction의 founder_pid → new_faction.founder_lineage에 포함)

### 변경 없음 (금지)
- `_change_persona_faction` 시그니처·로직
- FactionChangeSource 정의
- AST whitelist 마커 5건
- Faction.grace_until_tick, InnerWorld.residence_ticks

---

## 6. 검증 기준 (Stage 6 acceptance)

| 기준 | 값 |
|------|---|
| seed 7/13/42 `active_factions_end >= 2` | 3/3 PASS |
| seed 7/13/42 `last_500_active_min >= 2` | 3/3 PASS |
| drift_ratio (seed 7 기준) | <= 70% (현재 61%, H-lite 후 재측정) |
| gini 상한 초과 없음 | per-faction gini < 0.75 |
| AST 마커 5건 유지 | grep count 5 |
| `five_channel_determinism` | PASS |
