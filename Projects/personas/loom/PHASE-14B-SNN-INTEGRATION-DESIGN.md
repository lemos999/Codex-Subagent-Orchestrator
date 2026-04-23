# Phase 14-B — SNN 정치 통합 (Grievance 창발 회로)

> **배경**: Phase 14는 `grievance` 필드와 `_try_exodus` 경로를 추가했지만, `/discuss` 8팀 교차검증(`output/harness-runs/phase14-emergence-20260418/results/V1,V2,V6,V8`)에서 **FAIL**로 판정됨. grievance는 SNN에 한 번도 도달하지 않는 dead-end 변수이고, farmer 수는 `max(1, residents//3)` 하드코딩이다. 이 지시서는 창발 회로의 끊긴 4개 연결을 복구한다.
> **원칙**: 뉴런 총 수(n_neurons ≥ 350)는 건드리지 않는다. 기존 `300~349` 경제 뉴런 공간만 재사용한다.

---

## 판정 요약 (이 지시서의 근거)

| ID | 결과 | 핵심 문제 |
|---|---|---|
| V1 | WARN | 직접 구현 4/4가 Rule. SNN downstream 피드백만 존재 |
| V2 | FAIL | `grievance → chronic_stress / oyok / SNN 입력` 경로 전부 없음 |
| V6 | FAIL | `max_farmers = residents//3` 고정 공식. SNN은 urgency scalar에만 관여 |
| V8 | FAIL | 고립 영지에서 `alternatives=[]` → grievance 1.0 도달 → SNN 무반응 → 정체 |

**목표**: 위 4개 연결을 만들면 Phase 14의 통치 회로가 SNN 기반이 된다.

---

## 변경 범위 (3파일 + 테스트 1개)

1. `Projects/personas/loom/core/multi_tick_engine.py` — grievance → economic_state / chronic_stress / oyok / farmer 계산 변경
2. `Projects/personas/loom/brain/persona_brain.py` — 경제 뉴런 영역에 정치 스트레스 자극 추가 (뉴런 공간 재사용)
3. `Projects/personas/loom/ontology/layers.py` — `economic_state` dict 확장 필드 문서화 주석만 (코드 변경 없음 가능)
4. `Projects/personas/loom/test_phase14b_snn_integration.py` — 신규 검증 테스트 5개

---

## 연결 1: grievance → `_build_economic_state` dict

**현재** (`multi_tick_engine.py:1283~1290`):
```python
return {
    "food_ratio": ...,
    "tool_ratio": ...,
    "wealth_ratio": ...,
    "job_satisfaction": ...,
    "relative_wealth": ...,
    "tax_burden": tax_burden,   # ← 이미 dict에 있으나 persona_brain.py가 소비 안 함 (dead)
}
```

**수정**: 같은 dict에 `grievance`, `trust_to_lord` 추가. `tax_burden`은 유지.

```python
# (_build_economic_state 내부, tax_burden 계산 다음)
grievance = float(inner.grievance)

trust_to_lord = 0.5
lord_id = territory.lord_id if territory else None
if lord_id and lord_id != pid:
    rel_key = Relationship(persona_a=pid, persona_b=lord_id).key()
    rel = self.relationships.get(rel_key)
    if rel:
        trust_to_lord = float(rel.trust)

return {
    "food_ratio": inner.inventory.get("food", 0) / 30.0,
    "tool_ratio": (inner.equipped_tool_durability or 0) / TOOL_MAX_DURABILITY,
    "wealth_ratio": (gold / 2000.0) if wallet else 0.5,
    "job_satisfaction": job_satisfaction,
    "relative_wealth": (gold / max(1.0, avg_gold)) if wallet else 1.0,
    "tax_burden": tax_burden,
    "grievance": grievance,
    "trust_to_lord": trust_to_lord,
}
```

---

## 연결 2: `persona_brain.py` 정치 스트레스 뉴런 자극

**제약**: `self.n_neurons >= 350` 유지. 새 뉴런 추가 금지. 기존 `300~349` 영역을 재사용한다.

**현재** (`persona_brain.py:100~139`): 5채널 (food_scarcity / tool_lack / wealth_ratio / job_satisfaction / relative_wealth) 각 10뉴런 width.

**수정**: 채널 3 (wealth_ratio, `eco_base+20`)과 **같은 뉴런 영역**에 정치 스트레스를 가산. 의미: 경제 불안 뉴런과 정치 불만 뉴런은 동일한 "생존 위협 반응" 회로를 공유한다 (편도체 유비).

line 138 (`self._last_economic_input = ...`) **직전**에 추가:

```python
# ── 채널 6: 정치 스트레스 (Phase 14-B) ─────────────────
# 뉴런 공간 재사용 — wealth_ratio(+20)과 job_satisfaction(+30) 영역을 공유.
# grievance(불만)와 tax_burden(세금 압박)은 같은 스트레스 회로에 주입된다.
grievance = float(eco.get("grievance", 0.0))
tax_burden = float(eco.get("tax_burden", 0.0))
trust_to_lord = float(eco.get("trust_to_lord", 0.5))

# political_stress: 0~1.5 (trust 낮으면 증폭)
political_stress = grievance + max(0.0, tax_burden - 0.5) * 0.5
if trust_to_lord < 0.3:
    political_stress *= 1.3

# wealth 영역(+20)에 가산 — 경제 생존 위협으로 인식
if political_stress > 0.1:
    stimulate(eco_base + 20, min(0.6, political_stress * 0.35))

# job_satisfaction 영역(+30)에 가산 — 직업/체제 불만족
if grievance > 0.3:
    stimulate(eco_base + 30, grievance * 0.4)
```

`_last_economic_input` 슬라이스 범위는 그대로 `[eco_base:eco_base+50]` 유지 (정치 자극도 같은 범위에 포함).

---

## 연결 3: `_update_grievances` → `chronic_stress` + `oyok` 피드백

**현재** (`multi_tick_engine.py:757~805`): grievance만 누적. inner state의 다른 축으로는 전파 없음.

**수정**: grievance 업데이트 직후, 임계값 넘으면 `chronic_stress`와 `oyok[분노/두려움]`을 동반 상승.

오욕 배열: `[식욕, 수면욕, 색욕, 재욕, 명예욕]` (line 700). 정치 스트레스는 명예욕(oyok[4])을 자극한다 — 체제에 대한 자기 위치/존엄의 욕구. 또한 chiljeong(7감정) 배열에서 `chiljeong[1]=노(분노)`, `chiljeong[3]=구(두려움)`을 높인다.

`_update_grievances` 내부 `inner.grievance = max(0.0, min(1.0, inner.grievance + delta))` **직후**:

```python
                # ── Phase 14-B: SNN 피드백 ──
                if inner.grievance > 0.3:
                    # 만성 스트레스 가산 (grievance 0.3→0.001/틱, 1.0→0.005/틱)
                    stress_gain = (inner.grievance - 0.3) * 0.007
                    inner.chronic_stress = min(1.0, inner.chronic_stress + stress_gain)

                if inner.grievance > 0.5:
                    # 명예욕(oyok[4]) 상승 — 체제 부당함에 대한 자기 존엄 욕구
                    dignity_drive = min(1.0, float(inner.oyok[4]) + (inner.grievance - 0.5) * 0.3)
                    inner.oyok[4] = np.float16(dignity_drive)

                    # 분노(chiljeong[1]) + 두려움(chiljeong[3]) 가산
                    anger = min(1.0, float(inner.chiljeong[1]) + (inner.grievance - 0.5) * 0.2)
                    fear = min(1.0, float(inner.chiljeong[3]) + (inner.grievance - 0.5) * 0.1)
                    inner.chiljeong[1] = np.float16(anger)
                    inner.chiljeong[3] = np.float16(fear)
```

주의: `inner.oyok`과 `inner.chiljeong`은 `np.float16` 배열이므로 반드시 `np.float16(...)` 캐스팅. 인덱스 범위 체크 불필요 (고정 길이 5/7).

---

## 연결 4: 영주 `_update_governance_policy` → 주민 grievance 평균 반영

**현재** (`multi_tick_engine.py:1164~1252`): `tension`, `drive`, `stability` 등은 영주 자신의 뇌 발화율에서만 도출. 주민 불만은 입력 없음.

**수정**: 영주의 `tension` 신호에 주민 평균 grievance 가산. 영주 SNN은 "신민의 고통"을 스스로 인지하게 됨.

`_update_governance_policy` 내부, `tension = cluster_signal(5)` **직후**:

```python
            # ── Phase 14-B: 주민 불만 평균을 tension에 병합 ──
            residents = self._get_territory_residents(tid)
            resident_grievances = [
                float(self.inners[p].grievance)
                for p in residents
                if p != lord_id
            ]
            avg_grievance = (
                float(np.mean(resident_grievances))
                if resident_grievances else 0.0
            )
            # tension은 영주 자신의 뇌 + 주민 고통의 가중합
            tension = float(np.clip(tension + avg_grievance * 0.5, 0.0, 1.0))
```

이 한 줄로 영주 SNN이 `tension` 높으면 `tax_target`을 올리고 `food_priority`를 올린다. 주민 고통 → 영주 지각 → 세율/식량정책 자동 반응.

---

## 연결 5: farmer 상한 = SNN 신호 기반 동적 계산

**현재** (`multi_tick_engine.py:893~897`):
```python
farmer_count = sum(1 for title in existing_titles_list if title == "farmer")
max_farmers = max(1, len(residents) // 3)
if food_urgency > 0.05 and farmer_count < max_farmers:
    needs.append(("farmer", food_urgency, "작물 재배 및 식량 공급", 6.0))
```

`max_farmers`가 주민 수 고정 1/3 = Rule.

**수정**: `food_priority` (영주 SNN 기반 정책)와 주민 평균 hunger에 따라 동적으로 배정. 하한 1, 상한은 `residents`의 60% (굶주릴 때 영주가 더 많이 고용 가능).

```python
farmer_count = sum(1 for title in existing_titles_list if title == "farmer")

# ── Phase 14-B: SNN 기반 동적 max_farmers ──
# food_priority(영주 SNN) + 주민 hunger(주민 oyok) 가중합
hunger_pressure = min(1.0, avg_hunger * 1.2)
policy_pressure = food_policy
dynamic_ratio = 0.15 + policy_pressure * 0.30 + hunger_pressure * 0.20
# 최소 1명, 최대 주민의 60%까지
max_farmers = max(1, int(round(len(residents) * dynamic_ratio)))
max_farmers = min(max_farmers, max(1, int(len(residents) * 0.6)))

if food_urgency > 0.05 and farmer_count < max_farmers:
    needs.append(("farmer", food_urgency, "작물 재배 및 식량 공급", 6.0))
```

의미: 영주 SNN의 food_priority가 낮고 주민이 배부르면 farmer 1~2명만 유지. 위기 시(food_priority 0.8+ & avg_hunger 0.7+) 주민 60%까지 확대. **상한 자체가 SNN 신호로 계산됨**.

---

## 연결 6: 고립 영지 탈출구 — grievance → 스트레스 주입 (dead-end 제거)

**현재** (`multi_tick_engine.py:719~755`): `alternatives=[]` 이면 `_try_exodus`가 `None` 반환. 그 이후 fallback 없음 — grievance 1.0 도달 후 SNN은 아무것도 감지 못 함.

**수정**: `_try_exodus`가 `alternatives=[]`로 실패할 때, **시도 자체는 기록**하고 grievance 초과분을 `chronic_stress`로 전환한다. 연결 3이 이미 grievance → chronic_stress를 만들었기 때문에, V8 고립 시나리오에서도 이제 영주 SNN의 tension이 자연히 상승한다 (chronic_stress는 LIF tone network → 기분/각성에 영향). 추가 보강으로 명시적 좌절 이벤트를 발화.

`_try_exodus` 내부:
```python
def _try_exodus(self, pid: str) -> Optional[dict]:
    inner = self.inners[pid]
    if inner.grievance < 0.9 or inner.is_sleeping:
        return None
    # ... current_territory, alternatives 계산 ...

    # ── Phase 14-B: 대안 없음 = 고립 → 좌절 이벤트 + 추가 스트레스 ──
    if not alternatives:
        # grievance가 이미 1.0에 가까우면 추가 chronic_stress로 전환
        if inner.grievance >= 0.9:
            inner.chronic_stress = min(1.0, inner.chronic_stress + 0.005)
            # 분노/두려움 추가 가산 (탈출 막힘 특별 반응)
            inner.chiljeong[1] = np.float16(min(1.0, float(inner.chiljeong[1]) + 0.05))
            inner.chiljeong[3] = np.float16(min(1.0, float(inner.chiljeong[3]) + 0.05))
            return {
                "type": "exodus_blocked",
                "persona": pid,
                "territory": self.personas[pid].territory,
                "reason": "no_alternatives",
                "grievance": round(float(inner.grievance), 3),
            }
        return None

    # (이하 기존 확률/선택 로직 유지)
```

주의: `_try_exodus`의 반환값은 기존 호출부에서 이벤트로 수집된다. 기존 `success_event` 형식과 호환되게 `type` 필드만 구분한다.

---

## 연결 7 (선택, 안전장치): `_update_grievances` clamp 폭주 방지

**현재**: 0.8 이상이면 매 24틱마다 `grievance_critical` 이벤트 발화 → 로그 폭탄.

**수정**: 이벤트는 0.8 **교차 시점**에만 발화. 다음 틱엔 `grievance_announced` 플래그 체크.

```python
# InnerWorld에 필드 추가 (ontology/layers.py 근처 grievance 옆)
# grievance_announced: bool = False
```

`_update_grievances` 내부:
```python
                if inner.grievance >= 0.8 and not inner.grievance_announced:
                    inner.grievance_announced = True
                    events.append({...})  # 기존 형식 유지
                elif inner.grievance < 0.6:
                    inner.grievance_announced = False
```

이벤트 스팸을 막고, 재발화는 0.6으로 내려갔다가 다시 0.8 넘을 때만. **옵션**이지만 V2가 로그 폭탄을 지적했으므로 포함 권장.

---

## 검증 테스트 (`test_phase14b_snn_integration.py` 신규)

```python
# Projects/personas/loom/test_phase14b_snn_integration.py
import numpy as np
from core.multi_tick_engine import MultiTickEngine
from ontology.layers import InnerWorld

def test_t1_grievance_in_economic_state():
    """grievance가 _build_economic_state dict에 포함되는가"""
    eng = MultiTickEngine(n_personas=5)
    pid = list(eng.personas.keys())[0]
    eng.inners[pid].grievance = 0.7
    eco = eng._build_economic_state(pid)
    assert "grievance" in eco
    assert abs(eco["grievance"] - 0.7) < 0.01
    assert "trust_to_lord" in eco

def test_t2_grievance_stimulates_snn_neurons():
    """grievance가 SNN 경제 입력 영역(300~349)을 자극하는가"""
    eng = MultiTickEngine(n_personas=5)
    pid = [p for p in eng.personas if p != eng.territories[list(eng.territories.keys())[0]].lord_id][0]
    brain = eng.brains[pid]
    # 시나리오 A: grievance=0.0
    eng.inners[pid].grievance = 0.0
    eng.tick()
    input_low = brain._last_economic_input.copy()
    # 시나리오 B: grievance=0.9
    eng.inners[pid].grievance = 0.9
    eng.tick()
    input_high = brain._last_economic_input.copy()
    # wealth 영역(offset 20~29)에 차이가 있어야 함
    assert input_high[20:30].sum() > input_low[20:30].sum() + 0.1

def test_t3_grievance_raises_chronic_stress():
    """grievance>0.3 누적 → chronic_stress 상승"""
    eng = MultiTickEngine(n_personas=5)
    pid = list(eng.personas.keys())[1]
    eng.inners[pid].grievance = 0.8
    eng.inners[pid].chronic_stress = 0.0
    # 24틱 강제 — _update_grievances가 한 번은 실행되어야 함
    for _ in range(25):
        eng.tick()
    assert eng.inners[pid].chronic_stress > 0.0

def test_t4_lord_responds_to_resident_grievance():
    """영주의 tax_rate/food_priority가 주민 평균 grievance 상승에 반응"""
    eng = MultiTickEngine(n_personas=8)
    tid = list(eng.territories.keys())[0]
    territory = eng.territories[tid]
    lord_id = territory.lord_id
    residents = eng._get_territory_residents(tid)
    # 영주 외 주민의 grievance를 0.9로 고정
    for p in residents:
        if p != lord_id:
            eng.inners[p].grievance = 0.9
    old_food_priority = territory.policy.food_priority
    # 48틱 = 1회 이상 _update_governance_policy
    for _ in range(50):
        eng.tick()
    # food_priority는 tension 보강으로 상승해야 함
    assert territory.policy.food_priority >= old_food_priority

def test_t5_max_farmers_is_dynamic():
    """max_farmers 상한이 food_priority에 따라 변한다"""
    eng = MultiTickEngine(n_personas=10)
    tid = list(eng.territories.keys())[0]
    territory = eng.territories[tid]
    # 시나리오 A: food_priority=0.1
    territory.policy.food_priority = 0.1
    for _ in range(50):
        eng.tick()
    farmers_low = sum(
        1 for j in eng.jobs.values()
        if j.employer_id == territory.lord_id and j.title == "farmer"
    )
    # 시나리오 B: food_priority=0.9
    territory.policy.food_priority = 0.9
    # 기존 farmer 해고 처리 필요 시 여기서
    for p in eng._get_territory_residents(tid):
        eng.inners[p].oyok[0] = np.float16(0.8)  # hunger 강제
    for _ in range(100):
        eng.tick()
    farmers_high = sum(
        1 for j in eng.jobs.values()
        if j.employer_id == territory.lord_id and j.title == "farmer"
    )
    assert farmers_high >= farmers_low

def test_t6_exodus_blocked_yields_stress():
    """고립 영지에서 exodus 불가 + grievance>=0.9 → exodus_blocked 이벤트 + chronic_stress 상승"""
    eng = MultiTickEngine(n_personas=4)  # 영지 1개만 생기도록
    # 모든 페르소나를 한 영지에 몰기
    tid = list(eng.territories.keys())[0]
    for p in eng.personas.values():
        p.territory = tid
    pid = [p for p in eng.personas if p != eng.territories[tid].lord_id][0]
    eng.inners[pid].grievance = 0.95
    stress_before = eng.inners[pid].chronic_stress
    event = eng._try_exodus(pid)
    assert event is not None
    assert event["type"] == "exodus_blocked"
    assert eng.inners[pid].chronic_stress > stress_before
```

실행:
```bash
cd Projects/personas/loom && py test_phase14b_snn_integration.py
```

---

## 회귀 테스트 (기존 통과 테스트 깨짐 없음 확인)

```bash
cd Projects/personas/loom && py test_governance.py       # Phase 13 8/8 유지
cd Projects/personas/loom && py test_economy_balance.py  # Phase 14 T1~T6 유지
cd Projects/personas/loom && py test_phase12b_perf_npc.py
cd Projects/personas/loom && py test_snn_economy.py
cd Projects/personas/loom && py test_nomos.py
cd Projects/personas/loom && py test_class_promotion.py
```

---

## 완료 기준 (APPROVE 조건)

1. `test_phase14b_snn_integration.py` T1~T6 전부 PASS
2. 위 회귀 테스트 전부 PASS
3. **창발 회복**: V2/V6/V8 검증 질문 재실행 시 FAIL → Mixed 이상으로 상승해야 함
   - V2: grievance → SNN 경로 **존재**
   - V6: max_farmers는 food_priority로 변함 **가능**
   - V8: 고립 시나리오에서도 chronic_stress/oyok/chiljeong 에 고통이 **남음**
4. 뉴런 수(`n_neurons`) 변경 금지 — 300~349 영역만 재사용

---

## 참고: 창발 구조 정리 (리뷰어용)

```
이전(Phase 14):
  tax_rate → grievance (Rule 공식)
  grievance → exodus (Rule 임계)
  grievance → [dead-end, SNN 미도달]
  max_farmers = residents//3 (Rule)
  고립 영지 → None → [dead-end]

이후(Phase 14-B):
  tax_rate → grievance (Rule 공식, 유지)
  grievance → economic_state dict → SNN 뉴런 300-349 자극
  grievance → chronic_stress (몸이 기억)
  grievance → oyok[명예욕] / chiljeong[분노,두려움] (감정 전이)
  grievance (주민 평균) → 영주 tension → food_priority/tax_rate 자동 조정
  food_priority → max_farmers 동적 상한
  고립 영지 → exodus_blocked + chronic_stress 전환 (dead-end 제거)

결과: 규칙 계산으로 시작된 grievance가 SNN 5개 통로를 통해 창발 회로에 합류.
      영주-주민 양방향 피드백 루프 완성.
```
