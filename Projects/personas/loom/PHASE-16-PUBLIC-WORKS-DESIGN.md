# Phase 16: Public Works — 영지 공공 고용으로 Gold 순환 복원

## 배경

Phase 15-F 관측 (2000틱, 2026-04-18):
- total persona gold: 20000 → 2151 (**-89.2%**)
- total treasury: 9000 → 1553 (-83%)
- 사망 0건, 창발 정상 (strike 12, policy 88, chronicle cap 100)

파라미터 튜닝 3회 비교 (GOLD_DIRECT_PAY_RATIO 0.3/0.15/0.0, NPC 매도 완화):
| 버전 | DIRECT_PAY | Gold 감소 |
|---|---|---|
| 15-D | 0.3 | -91.7% |
| 15-E | 0.15 | -89.3% |
| 15-F | 0.0 | -89.2% |

**근본 원인 확정**: 자영노동 gold 경로는 영향 없음. 실제는 **무역수지 적자** — `food_stockpile` 매수 69건 등으로 페르소나/영지 → NPC 일방향 gold 유출. 외부 유입(NPC 매도)은 surplus goods 부족으로 활성화 실패.

**원칙 (SNN 창발 최우선)**:
- 새 뉴런 추가 금지 — 기존 SNN 6축 (growth/stability/tension) 활용
- 영지가 능동적 gold 순환 주체가 되도록 공공 지출 경로 추가
- 부작용(인플레이션·재정 적자) 자동 제어: 금고 비율 상한 + 실업자만 대상

---

## 해결 방향: Public Works

현실 경제의 정부 공공 지출 역할. 영지가 SNN 신호에 따라 실업 페르소나를 임시 공공 고용 → 영지 금고 → 페르소나 wallet으로 gold 순환 복원.

**핵심 메커니즘 (창발적 케인스주의)**:
- `growth` 상승 → 공공 투자 확대 → 실업 감소 → `stability` 상승 → 다음 policy `growth` 증폭 (양성 피드백)
- `tension` 상승 → 긴급 구휼 확대 → grievance 완화 → strike 감소 (자기 조정)
- `treasury < MIN_TREASURY` → 자동 보류 (재정 건전성)

---

## 변경 파일 (3개)

1. `Projects/personas/loom/ontology/layers.py` — 상수 + `GovernancePolicy.public_works_rate` 필드 + `Territory.last_snn_signals`
2. `Projects/personas/loom/core/multi_tick_engine.py`
   - `_process_public_works(territory_id)` 메서드 신규
   - `_auto_economy_tick`에서 호출
   - `_update_governance_policy` — `snn_signals`를 `territory.last_snn_signals`에 저장
3. `Projects/personas/loom/observe_phase15_stack.py` — `public_works` 이벤트 집계 추가 (검증용)

---

## 구현 순서

### Step 1: 상수 + dataclass 필드 (`layers.py`)

`GOLD_DIRECT_PAY_RATIO` 뒤에 추가:

```python
# ── Phase 16: Public Works 상수 ──
PUBLIC_WORKS_WAGE_PER_TICK: float = 5.0     # 공공 고용 틱당 임금
PUBLIC_WORKS_DURATION: int = 24             # 1회 고용 틱 수 (1 cycle)
PUBLIC_WORKS_INTERVAL: int = 24             # 체크 주기 (_auto_economy_tick과 동기)
PUBLIC_WORKS_MIN_TREASURY: float = 500.0    # 이 미만이면 전면 보류
PUBLIC_WORKS_MAX_TREASURY_RATIO: float = 0.5  # 금고의 이 비율 초과 지출 금지
```

`GovernancePolicy` dataclass (기존):
```python
    public_works_rate: float = 0.0   # SNN 신호 기반 자동 설정 (0.0~0.8)
```

`Territory` dataclass (기존, `chronicle` 옆):
```python
    last_snn_signals: dict = field(default_factory=dict)   # policy_update가 저장
```

### Step 2: `_process_public_works()` 신규 메서드 (`multi_tick_engine.py`)

클래스 내부, `_process_market` 근처에 추가:

```python
def _process_public_works(self, territory_id: str) -> list[dict]:
    """Phase 16: SNN 신호 기반 공공 고용. 실업자에게 1 cycle 임금 즉시 선지급."""
    territory = self.territories.get(territory_id)
    if not territory or territory.treasury_gold < PUBLIC_WORKS_MIN_TREASURY:
        return []

    snn = territory.last_snn_signals or {}
    growth = float(snn.get("growth", 0.0))
    tension = float(snn.get("tension", 0.0))

    # rate = growth 주도 + tension 긴급 가산, 상한 0.8
    rate = min(0.8, max(0.0, growth * 0.5 + tension * 0.3))
    territory.policy.public_works_rate = rate

    if rate < 0.1:
        return []

    unemployed = [
        pid for pid, p in self.personas.items()
        if p.territory == territory_id
        and p.employment_id is None
        and float(self.inners[pid].vitality) > 0
        and not self.inners[pid].is_sleeping
    ]
    if not unemployed:
        return []

    n_hire = max(1, int(rate * len(unemployed)))
    wage_per_person = PUBLIC_WORKS_WAGE_PER_TICK * PUBLIC_WORKS_DURATION  # 120 gold
    budget_cap = territory.treasury_gold * PUBLIC_WORKS_MAX_TREASURY_RATIO
    max_affordable = int(budget_cap // wage_per_person)
    n_hire = min(n_hire, max_affordable, len(unemployed))

    if n_hire <= 0:
        return []

    # 공정성: 무작위 선택 (seed는 엔진의 rng 사용)
    chosen = self.rng.sample(unemployed, n_hire) if hasattr(self, "rng") else unemployed[:n_hire]

    events = []
    for pid in chosen:
        if territory.treasury_gold < wage_per_person:
            break
        territory.treasury_gold -= wage_per_person
        self.wallets[pid].receive(wage_per_person)
        events.append({
            "type": "public_works",
            "territory": territory_id,
            "persona": pid,
            "wage": wage_per_person,
            "duration": PUBLIC_WORKS_DURATION,
            "rate": round(rate, 3),
            "snn_growth": round(growth, 3),
            "snn_tension": round(tension, 3),
            "treasury_after": round(territory.treasury_gold, 1),
        })
    return events
```

### Step 3: `_auto_economy_tick`에서 호출

기존 `_process_market()` / `_process_npc_shop()` 호출 루프 근처에 추가 (`PUBLIC_WORKS_INTERVAL == 24`이므로 기존 auto tick 타이밍과 자연 동기):

```python
# Phase 16: Public Works — SNN 기반 공공 고용
for tid in self.territories:
    pw_events = self._process_public_works(tid)
    events.extend(pw_events)
```

### Step 4: `_update_governance_policy` — SNN 저장

기존 `_update_governance_policy` 메서드 말미에 (policy_update 이벤트 append 직전):

```python
territory.last_snn_signals = {
    "growth": float(growth),
    "stability": float(stability),
    "tension": float(tension),
    # 다른 신호도 그대로 — Phase 16이 필요 시 활용
}
```

> 기존 `snn_signals` dict가 policy_update 이벤트에 이미 담기므로, 동일 dict를 `last_snn_signals`로 참조 저장해도 OK.

### Step 5: 관측 스크립트 확장 (`observe_phase15_stack.py`)

event 집계 루프에 추가:
```python
elif et == "public_works":
    public_works_events.append((tick_idx, ev))
```

리포트 섹션 (Phase 15-C 뒤, Economy Snapshot 앞):
```
  Phase 16: Public Works
─────────────────────────
  public_works events        : {len(public_works_events)}
  total public wage paid     : {sum(ev.get("wage",0) for _,ev in public_works_events):.0f}
  avg rate                    : {sum(ev.get("rate",0) for _,ev in public_works_events)/max(1,len(public_works_events)):.3f}
```

---

## 검증 (2000틱)

합격 조건:
1. `public_works` 이벤트 발생 > 0 (기본 동작)
2. total persona gold 감소율 **-89% → -70% 이하** (순환 복원 증거)
3. treasury 총합 안정화 (공공지출 ≈ 세수로 수렴, 장기 평균 기준)
4. 사망 0건 유지
5. `strike` 빈도가 이전과 비슷하거나 낮음 (tension 완화 효과)
6. 기존 테스트 PASS:
   ```bash
   cd Projects/personas/loom && py test_nomos.py
   cd Projects/personas/loom && py test_class_promotion.py
   ```

불합격 시 fallback:
- 공공지출이 너무 커서 금고 빠르게 고갈 → `PUBLIC_WORKS_MAX_TREASURY_RATIO` 0.5 → 0.3
- 공공지출이 거의 안 일어남 → `rate` 공식 가중치 상향 (growth 0.5 → 0.7)
- 인플레이션 (persona gold 급증) → `PUBLIC_WORKS_WAGE_PER_TICK` 5.0 → 3.0

---

## SNN 창발 포인트 (요약)

| 신호 상승 | 공공 고용 rate | 결과 | 피드백 |
|---|---|---|---|
| `growth` ↑ | ↑ | 실업↓, 소득↑ | `stability` ↑ → 다음 `growth` ↑ (양성) |
| `tension` ↑ | ↑ (긴급) | gold 배급, grievance 완화 | strike↓ → `tension` ↓ (자기조정) |
| `treasury` 낮음 | 자동 보류 | 재정 건전성 유지 | 세수 재축적 대기 |

**핵심**: 규칙은 SNN 신호를 읽는 공식뿐. "언제 얼마나 공공 고용을 할지"는 SNN이 동적으로 결정 → 창발적 재정 정책.
