# Phase 17 / Φ-2 Faction — Project Charter

> `/design` Phase 1 산출물. GPT/Codex가 이 Charter만 읽고 Phase 2 Component Map 또는 `/spec` 단계로 넘길 수 있는 수준으로 작성.
> 선행: Φ-1 Land CLOSED 2026-04-22 (23/23 PASS, 154.4ms/tick) / `/discuss` 7명 토론 2026-04-22 (Claude 1 + Codex 3 valid + Gemini 3 UNAVAILABLE)

---

## 목표·목적 3계층 (역산 기준)

**궁극 목적 (loom 전체)**
페르소나가 살아가는 과정에서 국가가 자연 탄생한다. Top-down "여기 국가 있음" 선언 금지. 삶 → 유대 → 갈등 → 주권 선언의 인과 사슬로만 국가 생성.

**Phase 17 목적**
자연 탄생의 4단계 인과 사슬 구축. 각 단계는 다음 단계의 재료를 만든다.
- Φ-1 Land: '어디에' 있는가 (공간 기반) — CLOSED
- **Φ-2 Faction**: '누구와' 뜻이 같은가 (정치 기반) — **본 Charter**
- Φ-3 Struggle: 다른 '누구'와 충돌/동맹 (분화 동역학)
- Φ-4 Nation: 충분히 큰 결집이 주권 선언 (자연 탄생)

**Φ-2 고유 역할**
"우리" 감각의 최초 등장. Territory(공간 집합) 위에 살던 페르소나가 **정치적 집합체(Faction)**로 묶이기 시작. Faction은 top-down 선언이 아니라 **페르소나의 유대에서 자라나야** 함.

---

## 메타

| 항목 | 값 |
|------|-----|
| 프로젝트 | loom 페르소나 국가 시뮬 |
| Phase | 17 (Φ-2 Faction) |
| 로드맵 위치 | Φ-1 Land → **Φ-2 Faction** → Φ-3 Struggle → Φ-4 Nation |
| 선행 합의 | Φ-1 CLOSED (2026-04-22) / SSoT+단일 함수+AST whitelist / Phase 11-17 무파괴 |
| 선행 토론 | `subagent-runs/discuss/phase17-phi2-step-chain-2026-04-22/` — Round 3/3 PARTIAL, 쟁점 3개 사용자 결정 완료 |
| 날짜 | v1 2026-04-22 / **v2 2026-04-23 (S6 API 4→7 확장)** |

---

## 변경 로그

### v2 (2026-04-23) — S6 Φ-3 인계 API 질적 동기 3종 확장

v2 Decision Cards 재검증(5엔진 `subagent-runs/discuss/phase17-phi2-decisions-v2-verify-2026-04-23-quick/`)에서 Gemini-B 단독 포착: v1 Charter S6 4종(외형)만으로는 Φ-3 갈등 동역학이 "왜 싸우는가" 재료 부재. Decision Cards v3 V7에서 wealth/social/grievance 3종 신규 추가 → Charter 범위 확장 필요.

| 변경 | 항목 | 이유 |
|------|------|------|
| S6 API 수 | 4종 → **7종** (외형 4 + 질적 동기 3) | Φ-3 대립 씨앗에 경제 불평등·상호 불신·공동 분노 대상 필요 |
| Baseline #5 | "population/territory distribution, charter primitives" → "외형 4 + 질적 동기(wealth/social/grievance) 3" | 상동 |
| G-HERITAGE | "부분 해소" → "질적 동기 3종 추가로 확대 해소" | Gemini 관점 공백 추가 메움 |
| [확정] #8 (v2 신규) | S6 API 7종 계약 명시 | Phase 3 Decision Cards v3 V7 승격 |

v1 원안 유지: 대립 동역학은 Φ-3 범위 불변. API는 read-only (state mutation 경로 없음).

---

## Primary Outcome

페르소나가 유대를 기반으로 **자발적 집합체(Faction)에 가입·이적**하며, top-down 선언 없이 Territory 위에 "우리" 감각의 분포가 떠오른다. Φ-3 Struggle이 필요로 하는 **갈등의 재료**(구분 가능한 다수/소수, charter 대립의 씨앗)를 Φ-2 동역학이 자연 생성한다.

**핵심 시나리오**: Territory A에서 founder X가 Charter(norm primitive 3~5개)로 Faction F1 시작 → 같은 Territory 거주자 중 일부가 affiliation kernel(공간+신뢰+공유불만+근접성) 임계치 돌파 시 **자발적 가입** → Territory A 내 F1 지배 분포 형성 → 다른 Territory의 Faction F2와 charter 대립 씨앗 생성 → **Φ-3 진입 조건 충족**.

---

## Operating Loop

- **마이크로 (틱 단위)**: persona 주변의 affiliation score 누적 — 같은 Territory 이웃의 faction 분포 관찰, `affiliation_scores[faction_id]` 증가. faction_cooldown 감쇠.
- **미들 (24~48틱)**: 임계치+히스테리시스 돌파 시 `_change_persona_faction(source="affiliation"|"drift")` commit. double-buffer로 snapshot→compute→commit. Territory.factionRef 재계산.
- **매크로 (수백~수천틱, 목표 지향형)**: 지리적 집중·Charter 대립·다수/소수 구도 형성 → **Φ-3 Struggle 진입 조건 충족**.

---

## Baseline Expectations

**포함**:
1. `persona.faction: Optional[str]` SSoT 필드 + `_change_persona_faction()` 단일 변경 함수
2. Faction 데이터 구조 (id stable, name, founder_pid, charter tuple, created_tick)
3. Affiliation kernel — 4신호 가중합 + 24/48틱 누적 + 임계치 + 히스테리시스
4. `Territory.factionRef` 파생 투영 (double-buffer, 24틱 Counter+히스테리시스)
5. S6 Φ-3 인계 API **7종** — 외형 4종(population/territory distribution, charter primitives, contact pairs) + **질적 동기 3종(wealth distribution, social matrix, grievance targets)** (v2 확장)
6. AST whitelist 확장 — `persona.faction = ...` 직접 대입 금지 테스트
7. SNN 300~349 뉴런 재사용 — faction telemetry를 경제 perception에 co-fire

**제외 (Φ-2 비범위)**:
- Faction 간 전투·약탈·배척 → Φ-3
- 동맹·연맹 구조 → Φ-3
- 대립 상태의 charter 개정 → Φ-3 (reform 메커니즘)
- Charter 내용의 이념·문화·언어적 풍부화 → Φ-4 또는 별도 Charter
- Faction 소멸(founder 사망 시) 규칙 → Φ-2 말기 백로그
- Founder 외 charter 수정 → 불가 (Φ-2는 immutable charter)
- **대체**: Φ-2는 "창시·가입·이적·지배 분포"만. 대립 동역학은 전부 Φ-3.

**거부 결정 (2026-04-22 /discuss 기반)**:
- ❌ **S1 전용 뉴런 350~369 (+20 neurons)**: Phase 14-B `n_neurons=1000` freeze 위반, `readout_weights_v1.npy` 1000폭 고정 — 거부. 300~349 재사용으로 대체.
- ❌ **S3 전원 자동 seed**: "태어나자마자 Territory seed faction 소속" = top-down 선언 — 거부. founder+charter only로 대체.

---

## Differentiation Thesis

**"페르소나 국가 시뮬인데, 파벌을 설계자가 정의하지 않고 affiliation kernel의 창발적 분포로 생성하기 때문에, Faction이 찰흙처럼 빚어지지 않고 유대 밀도의 등고선으로 드러난다."**

- 기존 civ·4X 게임: faction/파벌이 시나리오 레벨에서 미리 정의 (Red team vs Blue team)
- loom Φ-2: **founder 1명 + Charter 3~5 norm primitive만 정의**, 멤버십은 kernel 동역학의 창발적 산출
- 그 결과 Faction의 크기·경계·대립 구도가 시뮬 시작 시점에 존재하지 않고, 유대의 흐름에 따라 떠오름

---

## Target Audience

| 항목 | 결정 |
|------|------|
| 대상 사용자 | loom 시뮬 개발자(본인), 향후 social graph 시각화 통합자 |
| 사용 환경 | `MultiTickEngine` (Python 3.x), 500~수천 틱 단위 시뮬 |
| 허용 복잡도 | 중간 — kernel 수식·double-buffer 도입, **기존 SNN 뉴런 구조 무변경** |
| 기대 사용 빈도 | 매 틱 affiliation score 갱신 / 24~48틱 주기 commit / 24틱 주기 Territory 투영 |
| 핵심 제약 | Phase 11-17 Φ-1 무파괴, 결정성(seed=42 재현), SNN n_neurons=1000 절대 고정, 성능 ≤250ms/tick (faction 예산 ≤5ms) |

---

## Charter 일관성 검증

- [x] Primary Outcome 1가지 확정
- [x] 3레이어 Operating Loop 한 문장씩
- [x] Baseline 포함/제외/거부 결정
- [x] Differentiation Thesis 한 문장
- [x] Target Audience 환경/제약 확정
- [x] Primary Outcome ↔ Operating Loop 양립? — 마이크로 kernel이 미들 가입에 피드, 미들 분포가 매크로 Φ-3 재료로 수렴
- [x] Differentiation ↔ Baseline 모순 없음? — "창발 지향 vs 무파괴 원칙" 잠재 상충 → 해소: **Faction은 신규 레이어**, Territory는 **새 파생 필드만**, SNN은 **기존 뉴런 재사용** (구조 파괴 아님)
- [x] Target 허용 복잡도 ↔ Primary Outcome 일치? — 중간 복잡도로 social agency만 도입, 대립 동역학은 Φ-3
- [x] 3레이어 모두 Primary Outcome 강화? — 마이크로(kernel) → 미들(가입/이적) → 매크로(분포 편향 + Φ-3 재료) 전부 같은 방향
- [x] 마이크로 → 미들 → 매크로 피드 연결? — `affiliation_scores` 누적 → 임계치 commit → 지배 분포 형성
- [x] 매크로가 순환형? — **목표 지향형** (Φ-3 진입 조건이 최종 goal)
- [x] 궁극 목적 정렬? — founder+charter only + kernel 기반 가입으로 **top-down 선언 금지 원칙** 준수

**결과**: **PASS**

---

## [확정 선행 결정] — Phase 2/3 스텁

다음 Phase(Component Map, Decision Card)에서 확장되지만 Charter 단계에서 이미 결정된 사항.

### 1. Faction 스키마 (최소 필드)

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass(slots=True)
class Faction:
    id: str                                 # stable UUID, 이름과 분리 (Codex X-DETERM 계약)
    name: str                               # 표시명, 중복 허용 (같은 이름 다른 Faction 가능)
    founder_pid: str                        # 최초 창시자, 사망해도 id는 유지 (소멸 규칙은 Φ-2 말기 백로그)
    charter: tuple[str, ...]                # norm primitive 3~5개, immutable (tuple로 강제)
    created_tick: int
```

### 2. Persona 필드 추가 (InnerWorld)

```python
faction: Optional[str] = None                              # faction.id, 미소속 허용
faction_cooldown: int = 0                                  # 이적 후 쿨다운 잔여 틱
affiliation_scores: dict[str, float] = field(
    default_factory=dict
)                                                          # {faction_id: accumulated_kernel_score}
```

- `faction = None`: 미소속 상태 정합. 초기 모든 non-founder는 None.
- `affiliation_scores`: 매 틱 누적, 24/48틱 commit 직후 decay.

### 3. Territory 재정의 — factionRef 파생 투영

기존 `Territory` ([layers.py:118](Projects/personas/loom/ontology/layers.py#L118))에 필드 추가:

```python
factionRef: Optional[str] = None            # dominant faction id, None 허용 (공허 허용)
```

- 초기값 None. 24틱마다 double-buffer Counter+히스테리시스로 갱신.
- Φ-1 `territoryRef` 패턴 그대로 계승 (dominance projection).
- None의 정합성: 초기 멤버십 없는 Territory, 균형 분포 Territory 전부 None 유지. **공허를 인정해야 "우리"가 창발일 수 있다**.

### 4. 단일 변경 함수 계약

```python
def _change_persona_faction(
    self, pid: str, new_faction_id: Optional[str],
    *, source: str   # "birth_founder" | "affiliation" | "drift" | "conflict" (Φ-3 예약)
) -> None:
    """persona.faction 쓰기 유일 경로. source 태그 필수."""
    persona = self._personas[pid]
    # noqa: PHASE17_FACTION_SSOT_WRITE  ← 이 마커가 있는 라인만 AST whitelist 통과
    persona.faction = new_faction_id
    persona.faction_cooldown = FACTION_COOLDOWN_TICKS if new_faction_id else 0
    self._emit_event("faction_change", pid=pid, to=new_faction_id, source=source)
```

- Φ-1 [`_change_persona_territory()`](Projects/personas/loom/core/multi_tick_engine.py) 패턴 계승.
- AST whitelist 확장 (test_phase17_land.py 기반): `persona.faction = ...` 라인이 `PHASE17_FACTION_SSOT_WRITE` 마커 없이 존재하면 FAIL.
- `source` 값 4종 고정, 미승인 값은 런타임 ValueError.

### 5. Affiliation Kernel (Φ-2 핵심 동역학)

```python
# 매 틱 누적 (snapshot → compute → commit)
for pid, persona in snapshot.personas.items():
    for faction_id in active_factions:
        score = (
            W_TERRITORY  * same_territory_indicator(persona, faction_id)
          + W_TRUST      * trust_density(persona, faction_members[faction_id])
          + W_GRIEVANCE  * shared_grievance(persona, faction_members[faction_id])
          + W_PROXIMITY  * spatial_proximity_score(persona, faction_members[faction_id])
        )
        persona.affiliation_scores[faction_id] = (
            DECAY * persona.affiliation_scores.get(faction_id, 0.0) + score
        )

# 24/48틱 commit 루프 (sorted(pid) 순서)
for pid in sorted(personas):
    persona = personas[pid]
    if persona.faction_cooldown > 0:
        continue
    best_fid = argmax(persona.affiliation_scores)
    best_score = persona.affiliation_scores[best_fid]
    if persona.faction is None and best_score >= THETA_JOIN:
        _change_persona_faction(pid, best_fid, source="affiliation")
    elif persona.faction is not None and best_fid != persona.faction:
        current_score = persona.affiliation_scores[persona.faction]
        if best_score - current_score >= DRIFT_MARGIN:
            _change_persona_faction(pid, best_fid, source="drift")
```

- 모든 RNG 사용 시 `_derive_rng("faction_kernel", pid, tick)` 경유 — Phase 17 Φ-1 중앙 RNG 정책 준수.
- 가중치 `W_*`, 임계치 `THETA_JOIN`, `DRIFT_MARGIN`, `DECAY`, `FACTION_COOLDOWN_TICKS` 초기값은 **Phase 3 Decision Card**에서 확정.
- tie-break: `sorted(faction_id)` 사전순.

### 6. Territory.factionRef 투영 (double-buffer)

```python
# 24틱마다, 모든 S4 commit 완료 직후
# 이전 tick snapshot 읽기 → 새 buffer에 쓰기 → atomic swap
new_buffer: dict[str, Optional[str]] = {}
for territory in world.territories:
    members = [p for p in snapshot.personas if p.territory == territory.id and p.faction]
    counter = Counter(p.faction for p in members)
    if not counter:
        new_buffer[territory.id] = None  # 공허 허용
        continue
    dominant_fid, dominant_count = counter.most_common(1)[0]
    prev_fid = prev_buffer.get(territory.id)
    # 히스테리시스: 현 지배 유지 불리해도 margin 이상 차이날 때만 교체
    if prev_fid and prev_fid in counter:
        prev_count = counter[prev_fid]
        if dominant_count - prev_count < FACTION_HYSTERESIS:
            new_buffer[territory.id] = prev_fid
            continue
    new_buffer[territory.id] = dominant_fid
# atomic swap
for territory in world.territories:
    territory.factionRef = new_buffer[territory.id]
```

- Φ-1 territory dominance projection 패턴 그대로.
- 공허(None) 정합성 유지 — "모두 미소속인 Territory"는 `None`.

### 7. SNN 통합 — 300~349 재사용 (S1 거부안의 대안)

- **전용 뉴런 350~369 추가 거부**: Phase 14-B `n_neurons=1000` freeze, `readout_weights_v1.npy` 1000폭 고정.
- **기존 경제 perception 뉴런 300~349에 faction telemetry co-fire**:
  - 자기 faction 존재 여부 → 경제 pressure 맥락 뉴런에 추가 자극
  - 이웃 faction 분포 편향 → 거래 상대 편향 뉴런에 추가 자극
  - "경제 맥락과 faction 소속은 같은 뉴런 공간에서 혼합 관찰" (창발 친화적)
- Charter `personabrain-snn-charter v3.1`은 **변경 없음**. F-cluster 확장 없음. 경제 뉴런의 입력 신호 소스만 확장.

### 8. S6 Φ-3 인계 계약 (API 7종, v2 확장)

**원칙**: 전 7종 read-only. Φ-2 내부 state 변경 경로 없음. 반환은 dict/list/set 신규 객체 (caller mutation이 내부 state 오염 불가).

**외형 4종 (v1, 구조·지리)**

```python
def faction_population_distribution(self) -> dict[str, int]:
    """{faction_id: member_count} — Φ-3 진입 조건 판정용. 공허 faction(멤버 0)도 엔트리 포함."""

def faction_territory_distribution(self) -> dict[str, list[str]]:
    """{faction_id: [territory_id, ...]} — 지리적 집중도 측정용 (Territory.factionRef 기반)."""

def faction_charter_primitives(self, faction_id: str) -> tuple[str, ...]:
    """Faction의 norm primitive 반환 — Φ-3 charter 대립 판정용. unknown id → KeyError."""

def factions_in_contact(self, radius: int = 1) -> list[tuple[str, str]]:
    """근접 Territory 간 다른 faction 쌍 — Φ-3 갈등 씨앗 후보. sorted pair (a<b) + 전체 sorted."""
```

**질적 동기 3종 (v2 신규, "왜 싸우는가" 재료)**

```python
def faction_wealth_distribution(self) -> dict[str, dict[str, float]]:
    """{faction_id: {total, mean, gini, top_decile_share}} — 경제 불평등·계급 갈등 씨앗.
    Wallet.gold 기반. 공허 faction은 모든 값 0."""

def faction_social_matrix(self) -> dict[tuple[str, str], float]:
    """{(fid_a, fid_b): avg_trust} — 서로 다른 faction 간 평균 trust (sorted pair, a<b).
    Φ-3 연합(high trust)·대립(low trust) 구도 씨앗. 동일 faction 쌍 제외."""

def faction_grievance_targets(self) -> dict[str, dict[str, int]]:
    """{faction_id: {lord_id: member_count}} — 공유 분노 대상 카운트.
    InnerWorld.grievance + grievance_lord_id 기반. Φ-3 공동 적 기반 연합 재료."""
```

**질적 동기 3종 도입 근거 (v2)**:
- 외형만 전달하면 Φ-3가 "왜 특정 faction 조합이 충돌하는가" 판단 불가 (단순 인접 + 인구수로는 계급·불신·공동 분노 구분 못함)
- Φ-3 갈등 동역학의 1차 입력으로 wealth(경제)·social(관계)·grievance(정치) 3채널 필요
- 전부 기존 Phase 16 Wallet / Phase 14-B InnerWorld / Phase 17 kernel cache 재사용 → 신규 state 0건

### 9. 검증 계약 (Hard 불변)

Phase 17 Φ-2 구현 후 반드시 통과:
- [ ] Phase 16 Hard 5지표 전부 유지 (persona gold, public_works, food_stockpile, total_wealth, deaths)
- [ ] Phase 17 Φ-1 전체 23/23 테스트 PASS 유지
- [ ] `test_class_promotion.py`, `test_nomos.py`, `test_phase16_public_works.py`, `test_phase14b_snn_integration.py` ALL PASS
- [ ] SNN n_neurons=1000 고정 (readout_weights_v1.npy 호환)
- [ ] 결정성: seed=42, 500틱 2회 실행 snapshot 일치 (비교 대상에 `persona.faction`, `faction_cooldown`, `affiliation_scores`, `Faction registry`, `Territory.factionRef` 포함)
- [ ] AST whitelist: `persona.faction =` 직접 대입 라인이 `PHASE17_FACTION_SSOT_WRITE` 마커 없이 존재하면 FAIL
- [ ] 성능 회귀: ≤ 250ms/tick (현 154.4ms, faction kernel 예산 ≤ 5ms)
- [ ] Bottom-up seed 검증: 500틱 시점에 `founder_count < total_member_count` (즉, 초기 founder만의 자기 가입이 아닌 진짜 유대 기반 성장 발생)

---

## [보류 해소 현황] — Phase 3 Decision Card 대기

| 항목 | 해소 위치 |
|------|-----------|
| kernel 가중치 `W_TERRITORY`, `W_TRUST`, `W_GRIEVANCE`, `W_PROXIMITY` | Phase 3 Decision Card |
| 임계치 `THETA_JOIN`, `DRIFT_MARGIN` | Phase 3 |
| `DECAY` 계수 (affiliation score 감쇠) | Phase 3 |
| `FACTION_COOLDOWN_TICKS` 기본값 | Phase 3 (Phase 11 `consecutive_*` 관례 참고) |
| `FACTION_HYSTERESIS` margin | Phase 3 |
| Founder 선정 규칙 (sorted(pid) tie-break + `_derive_rng("faction_seed", territory_id)`) | Phase 3 |
| 초기 norm primitive 카탈로그 (예: "토지_공유" / "장자_상속" / "외세_배척" 등 3~5개 카테고리) | Phase 3 |
| `trust_density()` 구체 수식 (Φ-1 spatial 데이터 기반) | Phase 3 |
| `shared_grievance()` 감지 신호 소스 (경제 지표? public_works 지연?) | Phase 3 |
| `spatial_proximity_score()` 수식 (Chebyshev 거리 기반) | Phase 3 |
| Charter 충돌 검증 (Gemini G-WORLDVIEW 공백 해소) | **Phase 3.5** (`/sub p-charter-consistency`) |
| Faction 소멸 규칙 (founder 사망 시) | **Φ-2 말기 백로그** 또는 Φ-3 초입 |

---

## [확정] — 사용자 결정 완료 (2026-04-22 `/discuss` 후)

1. **S1 +20 뉴런안 거부** — Phase 14-B `n_neurons` freeze 준수. 300~349 재사용 + faction telemetry co-fire로 대체.
2. **S3 초기화는 founder+charter only** — 전원 자동 seed는 위장된 top-down 선언으로 판정. 멤버십은 S4 affiliation kernel로 자연 성장.
3. **Gemini 관점 공백(G-EMERGE, G-HERITAGE, G-WORLDVIEW)**:
   - G-EMERGE: 쟁점 2 founder+charter 결정으로 사실상 해소
   - G-HERITAGE: S6 Φ-3 인계 계약 7종(외형 4 + 질적 동기 3: wealth/social/grievance)으로 확대 해소 (v2 2026-04-23)
   - G-WORLDVIEW: **Phase 3.5 Cross-Impact에서 `/sub p-charter-consistency`로 별도 검증**
4. **실행 순서 확정**: **S2 → S3 → S4 → S5 → S6** (S1 제거)
5. **결정성 세부 계약** (Codex X-DETERM 기여):
   - `faction_id`는 이름과 분리된 stable ID
   - 모든 RNG `_derive_rng("faction_*", key_parts)` 경유
   - S4 commit 순서 `sorted(pid)`
   - tie-break `sorted(faction_id)`
6. **Gap 4 방어** (Claude C-STRUCT 기여): S4·S5 내부에서 `_change_persona_faction()` 외 경로로 `persona.faction`·`faction_cooldown` 변경 금지 — AST whitelist로 강제.
7. **source 태그 4종 고정**: `"birth_founder"` | `"affiliation"` | `"drift"` | `"conflict"`(Φ-3 예약).
8. **(v2 2026-04-23) S6 API 7종 계약** — Φ-3 인계 API를 외형 4(population/territory distribution, charter primitives, adjacency pairs) + 질적 동기 3(wealth/social/grievance)으로 확정. Φ-3 갈등 동역학의 1차 입력에 필요한 경제·관계·정치 3채널 확보. 신규 state 0건 (기존 Wallet/InnerWorld/kernel cache 재사용).

---

## Stage 4 - Phi-3 Handoff (2026-04-25)

Stage 4 measured the Stage 3 anti-collapse implementation without adding a new faction mechanism.

Closure Report: `PHASE-17-FACTION-STAGE4-CLOSURE-REPORT.md`

### Phi-3 Entry Trigger Candidates

These triggers must be computed only through the D10 seven read-only APIs. They are OR conditions; any one condition can justify a future Phi-3 design cycle.

1. **Geographic differentiation**: `len(factions_in_contact(radius=1)) >= 1`.
   - Meaning: two different dominant factions are adjacent and can become a conflict/alliance substrate.

2. **Population imbalance**: `max(faction_population_distribution().values()) / sum(...) >= 0.55`.
   - Meaning: one faction owns at least 55% of faction population and the remainder becomes a meaningful opposition surface.

3. **Shared grievance**: at least two factions have two or more members sharing the same `lord_id` in `faction_grievance_targets()`.
   - Meaning: a common target exists and can produce coalition pressure.

If none of these conditions is true, Phi-3 entry is deferred and Phi-2 continues operating.

### Phi-3 Handoff Inputs

| API | Purpose |
|---|---|
| `faction_population_distribution()` | faction scale, imbalance, strong/weak side ecology |
| `faction_territory_distribution()` | territorial footprint and movement path substrate |
| `faction_charter_primitives(faction_id)` | norm and charter comparison |
| `factions_in_contact(radius=1)` | first-order contact and conflict candidates |
| `faction_wealth_distribution()` | economic inequality and class pressure |
| `faction_social_matrix()` | trust-based alliance or distance graph |
| `faction_grievance_targets()` | shared-enemy coalition substrate |

The Stage 4 freeze test `test_phase17_faction_handoff_contract.py` locks these APIs as read-only handoff surfaces.

**D10 read-only definition**: domain mutation is forbidden for `persona.faction`, `persona.faction_cooldown`, `inner.affiliation_scores`, the `engine.factions` registry (`id`, `name`, `founder_pid`, `charter`, `created_tick`), and `territory.factionRef`. Internal cache refresh is allowed for `_faction_members_cache`, memoization dictionaries, and lazy lookup tables because these are invisible implementation details. Every returned `dict`, `list`, or `tuple` must be a fresh object; caller mutation must not affect internal state.

### Stage 4 Decision

The 2026-04-25 Stage 4 probe did not close Phi-2:

- seed 7: `active_factions_end=2`
- seed 13: `active_factions_end=1`
- seed 42: `active_factions_end=1`

Primary acceptance `active_factions_end >= 2` for all three seeds failed at 1/3. Therefore this section defines the handoff contract, but Phi-3 full Charter work remains deferred until Stage 5 or a later probe resolves faction persistence.

---

## 다음 단계

1. **사용자 Charter 검증** — 본 문서 수정 요청 or 확정
2. **Phase 2 Component Map 진입** — Faction 레지스트리 + kernel 모듈 + projection 모듈 + SNN telemetry hook 분해
3. Phase 3 Decision Card — `[보류 해소 현황]` 항목들 초기값·수식 구체 결정
4. Phase 3.5 Cross-Impact — **`/sub p-charter-consistency`로 society/secret-rumor/humanity/constitution charter 충돌 검증** (Gemini G-WORLDVIEW 공백 메우기)
5. Phase 4 Verify — 결정성·성능·무파괴·bottom-up 검증 계약 모두 통과
6. Phase 5 Package — `/spec`으로 Codex 전달용 PHASE-17-FACTION-CODEX-INSTRUCTIONS.md 작성
