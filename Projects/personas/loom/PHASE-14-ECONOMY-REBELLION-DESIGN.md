# Phase 14: 경제 균형 + 반란 메커니즘 + 성능 최적화 — Codex 지시서

> **작성자**: Claude (설계/리뷰)
> **구현자**: Codex (코딩/검증)
> **선행 조건**: Phase 13 ALL PASS (8/8), ~190ms/tick
> **목표**: V6(gold 소멸 방지), V4(반란/불만 시스템), V5(20K틱 성능) — 3개 축 동시 해결

---

## 왜 이것이 다음인가 — 근본 원인 추적

Phase 13 /discuss 8팀 검증 결과:

| ID | 문제 | 등급 | 근본 원인 |
|----|------|------|----------|
| V6 | 10000틱 후 gold 94% 소멸 | WARN | farmer 2명 vs 소비 9food/tick → NPC 구매 반복 → gold 영구 소멸 |
| V4 | 폭정 대항 수단 0 | WARN | 세율 극단→주민 이탈/저항 코드 없음. 영주에게 견제 없는 단방향 구조 |
| V5 | `_process_food_reserve` O(P²) | WARN | 매 영지마다 전체 주민 리스트 재구성. 20K틱에서 병목 |

**꼬리 추적**:
- "gold 소멸" → 왜? → NPC food 매입(15g/unit)이 유일한 영구 싱크
- "왜 NPC를 계속 쓰나?" → farmer가 2명뿐 → 식량 자급 불가
- "왜 farmer가 2명?" → `food_urgency > 0.1` + `"farmer" not in existing_titles` → 영지당 최대 1 farmer
- "반란이 없다" → 왜? → 세율이 아무리 올라도 주민이 할 수 있는 건 없음
- "20K 병목" → 왜? → 영지별 주민 리스트를 매 24틱마다 O(P) 재구축 × 3곳

**근본**: (1) farmer 병목 + NPC 가격 비대칭 → 경제 누수, (2) 통치 견제 부재, (3) 캐시 미사용

---

## 변경 파일 (3파일)

1. `ontology/layers.py` — NPC_PRICES 재조정, 반란 관련 상수/타입
2. `ontology/__init__.py` — export 추가
3. `core/multi_tick_engine.py` — 경제 균형 + 반란 + 캐시 최적화

---

## Part A: 경제 균형 (V6)

### A-1. NPC 가격 재조정 (`ontology/layers.py`)

**문제**: NPC food buy=15, sell=3. 매입/매도 5:1 비율이 gold 소멸을 가속.

**변경**: `NPC_PRICES` 딕셔너리 수정

```python
NPC_PRICES: dict[str, dict] = {
    "food":      {"buy": 10, "sell": 5,  "daily_stock": 50},   # was buy:15,sell:3
    "material":  {"buy": 15, "sell": 7,  "daily_stock": 30},   # was buy:20,sell:5
    "tool":      {"buy": 60, "sell": 20, "daily_stock": 5},    # was buy:80,sell:15
    "medicine":  {"buy": 30, "sell": 10, "daily_stock": 10},   # was buy:40,sell:8
    "knowledge": {"buy": 45, "sell": 15, "daily_stock": 3},    # was buy:60,sell:12
}
```

**원칙**: 매입/매도 비율을 5:1 → 2:1~3:1로 완화. P2P가 여전히 유리하되, NPC 거래로도 최소한의 gold 회수 가능.

### A-2. farmer 복수 생성 허용 (`multi_tick_engine.py`)

**문제**: `"farmer" not in existing_titles` → 영지당 farmer 1명 제한.

**변경**: line 738 조건을 수정하여 farmer는 복수 허용

```python
# Before (line 738):
if food_urgency > 0.1 and "farmer" not in existing_titles:

# After:
farmer_count = sum(1 for t in existing_titles_list if t == "farmer")
# farmer는 주민 3명당 1명까지 복수 허용
max_farmers = max(1, len(residents) // 3)
if food_urgency > 0.05 and farmer_count < max_farmers:
```

**주의**: `existing_titles`는 현재 `set`이므로, farmer 카운트용으로 `existing_titles_list`(리스트) 변수를 추가해야 한다.

```python
# line 709 직후에 추가:
existing_titles_list = [j.title for j in self.jobs.values()
                        if j.employer_id == lord_id]
```

### A-3. farmer 산출량 보정

**문제**: farmer 2명 × 2.0 = 4 food/tick. 9 페르소나 × 1 food/tick = 9 필요. 영원히 미달.

**변경**: `ontology/layers.py` `JOB_BASE_OUTPUT`에서 farmer 산출량 상향

```python
JOB_BASE_OUTPUT: dict[str, float] = {
    "farmer": 3.0,      # was 2.0 — farmer 3명이면 9food/tick 자급 가능
    "laborer": 1.5,
    "craftsman": 0.5,
    "healer": 0.3,
    "scholar": 0.2,
    "guard": 0.5,
}
```

### A-4. gold 유입 보정 — NPC 매도 gold 보너스

현재 NPC에 goods를 팔면 sell 가격(3g)만 받는다. 영지 내 잉여 goods가 외부로 나갈 때 약간의 무역 이익을 부여한다.

**변경**: `_process_npc_shop()` 내 NPC 매도 로직에서:

```python
# 기존:
gold_received = qty * sell_price

# 변경:
trade_bonus = 1.0 + territory.policy.tax_rate * 0.5  # 세금 높은 영지 = 무역 활성
gold_received = qty * sell_price * trade_bonus
```

이것은 새 gold 유입원이 아니라 기존 sell 가격에 영지 무역 계수를 곱하는 것이다.

---

## Part B: 반란 메커니즘 (V4)

### 설계 원칙

반란은 **규칙이 아니라 창발**이어야 한다. 세율이 높으면 주민이 "반란을 일으킨다"는 하드코딩 대신:
- 세금 부담 → stress 증가 → SNN 발화 패턴 변화 → 특정 임계값에서 **행동 분기**
- 영주와의 trust 하락 → 사회적 거리 증가 → 행동 선택지에 "이주" 추가

### B-1. 불만(grievance) 누적 (`ontology/layers.py`)

InnerWorld에 필드 추가 (line 714, `consecutive_hunger_ticks` 뒤):

```python
    # ── 통치 불만 (Phase 14) ────────────────────────
    grievance: float = 0.0              # 0~1, 세금/식량 불만 누적
    grievance_lord_id: Optional[str] = None  # 불만 대상 영주
```

### B-2. 불만 누적 로직 (`multi_tick_engine.py`)

새 메서드 `_update_grievances()` — 24틱마다, `_collect_taxes` 직후 호출:

```python
def _update_grievances(self) -> list[dict]:
    """주민의 통치 불만을 갱신한다. 24틱마다."""
    if self.time.tick % 24 != 0:
        return []

    events = []
    for tid, territory in self.territories.items():
        lord_id = territory.lord_id
        if not lord_id:
            continue

        tax_rate = territory.policy.tax_rate
        tax_burden = tax_rate / 0.30  # 0~1 정규화

        residents = self._get_territory_residents(tid)  # Part C 캐시 사용
        for pid in residents:
            if pid == lord_id:
                continue

            inner = self.inners[pid]
            inner.grievance_lord_id = lord_id

            # 불만 증감 요인
            food = float(inner.inventory.get("food", 0))
            hunger = float(inner.oyok[0])

            # 세금 부담 + 식량 부족 → 불만 상승
            delta = 0.0
            delta += (tax_burden - 0.5) * 0.03   # 세율 50% 초과 시 +
            if food < 10:
                delta += 0.02                      # 식량 부족
            if hunger > 0.5:
                delta += 0.03                      # 배고픔
            if food >= 20 and hunger < 0.3:
                delta -= 0.02                      # 만족 시 감소

            # 영주와의 trust가 낮으면 불만 증폭
            rel_key = f"{pid}:{lord_id}" if pid < lord_id else f"{lord_id}:{pid}"
            rel = self.relationships.get(rel_key)
            if rel and rel.trust < 0.3:
                delta *= 1.5

            inner.grievance = max(0.0, min(1.0, inner.grievance + delta))

            # 불만 임계값 이벤트
            if inner.grievance >= 0.8:
                events.append({
                    "type": "grievance_critical",
                    "territory": tid,
                    "persona": pid,
                    "lord": lord_id,
                    "grievance": round(inner.grievance, 3),
                    "tax_burden": round(tax_burden, 3),
                })

    return events
```

### B-3. 불만 → 행동 분기 — 이주(exodus)

`_update_grievances` 이벤트 자체는 불만 기록일 뿐. **행동**은 기존 행동 결정 루프에서 분기:

Stage 1 행동 선택(line ~460) 직전에 삽입:

```python
# [Phase 14] 불만 극한 시 이주 시도
if inner.grievance >= 0.9 and not inner.is_sleeping:
    # 다른 영지 중 세율이 낮은 곳 탐색
    current_tid = persona.territory
    alternatives = [
        (tid, t) for tid, t in self.territories.items()
        if tid != current_tid and t.policy.tax_rate < territory.policy.tax_rate * 0.7
    ]
    if alternatives and np.random.random() < inner.grievance * 0.3:
        # 이주 실행
        new_tid = min(alternatives, key=lambda x: x[1].policy.tax_rate)[0]
        persona.territory = new_tid
        inner.grievance *= 0.5  # 이주 후 불만 반감
        # 기존 고용 해지
        if persona.employment_id:
            job = self.jobs.get(persona.employment_id)
            if job:
                job.is_open = True
            persona.employment_id = None
        economy_events.append({
            "type": "exodus",
            "persona": pid,
            "from_territory": current_tid,
            "to_territory": new_tid,
            "grievance": round(inner.grievance, 3),
        })
        continue  # 이주 틱에는 다른 행동 안 함
```

### B-4. 영주 견제 — 인구 이탈 피드백

이주가 발생하면:
- 영지 주민 수 감소 → 세수 감소 → treasury 압박
- SNN food_scarcity/tension 뉴런에 이미 반영 (주민 수 변화 → 경제 지표 변화)
- 영주의 `_update_governance_policy`가 tension 하락 시 세율 자연 인하

**하드코딩 추가 없음** — 기존 SNN 피드백 루프가 자연스럽게 견제.

---

## Part C: 성능 최적화 (V5)

### C-1. 영지별 주민 캐시

**문제**: `_collect_taxes`, `_process_food_reserve`, `_update_governance_policy`, `_update_grievances`가 각각 `[pid for pid, p in self.personas.items() if p.territory == tid]`를 반복. O(P) × 4 × 3영지 = O(12P).

**변경**: `_auto_economy_tick()` 시작 시 캐시 구축, 전 메서드에서 재사용.

```python
def _get_territory_residents(self, tid: str) -> list[str]:
    """캐시된 영지별 주민 목록. _auto_economy_tick 시작 시 갱신."""
    if not hasattr(self, '_territory_residents_cache') or self._territory_residents_cache is None:
        self._territory_residents_cache = {}
        for pid, p in self.personas.items():
            self._territory_residents_cache.setdefault(p.territory, []).append(pid)
    return self._territory_residents_cache.get(tid, [])
```

**호출 변경** (4개 메서드):
```python
# Before:
residents = [pid for pid, p in self.personas.items() if p.territory == tid]

# After:
residents = self._get_territory_residents(tid)
```

**캐시 무효화**: `_auto_economy_tick` 시작 시 `self._territory_residents_cache = None`, 종료 시 동일.

### C-2. `_process_food_reserve` NPC 가격 캐시

```python
# Before (매 영지마다):
npc_food_price = float(NPC_PRICES["food"]["buy"])

# After (_auto_economy_tick 시작 시 1회):
# 이미 self._pricing_cache 존재하므로 여기에 추가
self._npc_food_price = float(NPC_PRICES["food"]["buy"])
```

이 변경은 미미하지만, _pricing_cache 패턴과 일관성 유지.

---

## tick() 통합

```
Stage 1 (각 페르소나):
  _process_survival_consume(pid)
  [NEW] grievance >= 0.9 → exodus 체크
  eat/work/explore/socialize
  _process_economy(pid, action)
  _wear_tool(pid) if work

Stage 4 (24틱마다, _auto_economy_tick 내):
  [NEW] self._territory_residents_cache = None  (캐시 리셋)
  _update_governance_policy()     (48틱)
  _collect_taxes()
  [NEW] _update_grievances()      (세금 직후)
  _process_food_reserve()
  _process_market()
  _process_npc_shop()
  _auto_tool_management()
  [NEW] self._territory_residents_cache = None  (캐시 클리어)
```

---

## 검증

### 새 테스트: `test_economy_balance.py`

```
T1: 1000틱 후 총 gold 잔존율 > 70% (현재 87% @ 500틱 → 1000틱에서 70%+ 목표)
T2: farmer 복수 생성 — 500틱 후 farmer job >= 2
T3: NPC 매도 gold > 0 — 잉여 goods 매도로 gold 유입 확인
T4: 불만 누적 — 세율 0.30 강제 시 200틱 후 grievance > 0.5 주민 1명+
T5: 이주(exodus) — 세율 0.30 + 대안 영지 세율 0.05 → 200틱 내 exodus 이벤트 1건+
T6: 이주 후 영지 인구 변화 — from_territory 주민 수 감소 확인
```

### 기존 테스트 회귀

```bash
cd Projects/personas/loom
py test_economy_balance.py    # Phase 14 전용
py test_governance.py          # Phase 13 (8/8)
py test_economy.py             # goods/trade/gold
py test_nomos.py               # stress/사회규범
py test_class_promotion.py     # 승급/drive
py test_snn_economy.py         # SNN 경제 연결
```

**모든 기존 테스트 ALL PASS 필수.**

---

## SNN 창발 경계 요약

| 변경 | 레이블 | 근거 |
|------|--------|------|
| grievance 누적 (세금+hunger+trust) | **[SNN 간접]** | stress→SNN 발화 변화→행동 분기 |
| exodus 행동 (grievance >= 0.9) | **[Guide]** | 임계값은 가이드. 실제 이주 확률은 grievance×0.3 |
| 인구 이탈 → 세수 감소 → 세율 인하 | **[SNN]** | 기존 피드백 루프 자연 활용 |
| NPC 가격 비율 2:1~3:1 | **[Guide]** | 경제 파라미터 |
| farmer 복수 허용 | **[Guide]** | 직업 생성 제한 완화 |
| farmer 산출 3.0 | **[Guide]** | 자급 균형점 조정 |
| 영지별 주민 캐시 | **[Infra]** | 순수 성능. 로직 변경 없음 |

---

## 금지 사항

1. PersonaBrain에 새 뉴런 영역(350+)을 추가하지 마라
2. 반란을 "이벤트 시스템"으로 만들지 마라 — 기존 행동 루프 내 분기로 구현
3. grievance를 매 틱 갱신하지 마라 — 24틱 주기 (세금 주기와 동기)
4. 영지 간 이주 시 기존 관계(Relationship) 삭제하지 마라 — 유지
5. 기존 테스트(T1~T8)를 수정하지 마라 — 새 테스트만 추가
6. `_process_market`/`_process_npc_shop` 내부 로직을 변경하지 마라 — 가격 상수만 조정
7. territory.tax_rate와 territory.policy.tax_rate 동기화를 깨지 마라

---

## Codex용 기존 인터페이스 레퍼런스

Phase 14에서 호출할 기존 API (Phase 13 기반):

```python
# GovernancePolicy (ontology/layers.py)
territory.policy.tax_rate              # float 0.05~0.30
territory.policy.food_priority         # float 0~1
territory.policy.stockpile_target      # float 0~1
territory.policy.treasury_spending_cap # float 0.1~0.5

# Relationship (ontology/layers.py)
rel = self.relationships[key]          # Relationship
rel.trust                               # float 0~1
rel.familiarity                         # float 0~1

# 영지 주민 조회 (기존 패턴 — Part C에서 캐시로 교체)
residents = [pid for pid, p in self.personas.items() if p.territory == tid]

# InnerWorld 추가 필드 (Phase 14)
inner.grievance                        # float 0~1 (NEW)
inner.grievance_lord_id                # Optional[str] (NEW)
```

---

## 리뷰 요청서 템플릿

```
## Phase 14 리뷰 요청

### 변경 요약
- [ ] A-1: NPC 가격 재조정 (buy/sell 비율 2:1~3:1)
- [ ] A-2: farmer 복수 생성 (영지당 주민/3명까지)
- [ ] A-3: farmer 산출 2.0→3.0
- [ ] A-4: NPC 매도 무역 보너스
- [ ] B-1: grievance 필드
- [ ] B-2: _update_grievances (24틱)
- [ ] B-3: exodus 행동 분기
- [ ] C-1: 영지별 주민 캐시
- [ ] C-2: NPC 가격 캐시

### 테스트 결과
- test_economy_balance: _/6
- test_governance: _/8
- test_economy: _/6
- test_nomos: _/5
- test_class_promotion: _/6
- test_snn_economy: _/6

### 경제 관측 (1000틱)
- Gold 잔존율: ___% 
- Farmer 수: ___
- Exodus 이벤트: ___건
- Grievance > 0.5 주민: ___명
- ms/tick: ___

### 이슈/우려
```
