# Phase 17 / Φ-2 Faction — Stage 5 Anti-Collapse Decisions

> Stage 4 Closure addendum-v2 ([PHASE-17-FACTION-STAGE4-CLOSURE-SPEC-addendum-v2.md](PHASE-17-FACTION-STAGE4-CLOSURE-SPEC-addendum-v2.md)) 후속. Stage 1~3 anti-collapse(size tax + homeostasis + minority boost + founder respawn)가 잔존시킨 *second-collapse pattern* (respawn 직후 신생 faction이 trust 누적 우위에 즉시 흡수)을 종결한다.
> Charter([PHASE-17-FACTION-CHARTER.md](PHASE-17-FACTION-CHARTER.md)) `[보류 해소 현황]` 가중치 항목은 Phase 3 Decision Card 권한 — 본 문서가 갱신 권한자. **Charter 본문 무수정**.
> 본 결정은 v1·v2 두 토론(`subagent-runs/discuss/phase17-stage5-anticollapse-2026-04-25*/`) + Solo Verifier 검증(`subagent-runs/claude/stage5-conclusion-verification-2026-04-25/results/verifier.result.md`)의 **통합안**.

---

## 목표·목적 3계층 (역산 기준)

**궁극 목적**: 국가 자연 탄생 — 선언 없이 삶·유대·갈등·주권의 인과 사슬로만.
**Stage 5 목적**: Φ-2가 single-attractor 평형(absorbing state)으로 무너지지 않고 **2개 이상 활성 faction**이 5000틱 이상 공존하는 다극(multi-polar) 안정성 확보. 가입은 자율적·창발적이어야 하며 어떤 처방도 top-down 강제 배치를 도입하지 않음.
**Stage 5 고유 역할**: 표면 처방(타이머·가산점·강제 분리)이 아닌 **drift_score 가중치의 SSoT 비대칭** 자체를 근본 원인으로 지목·해소한다. 표면이 풀어주는 시간 지연(Stage 1~3의 grace, minority boost)은 유지하되 보조 안전판으로만 작동.

---

## 메타

| 항목 | 값 |
|------|-----|
| 프로젝트 | loom 페르소나 국가 시뮬 |
| Phase | 17 / Φ-2 Faction / Stage 5 |
| 선행 | Stage 4 Closure addendum-v2 (2026-04-24) / v1 토론 (4엔진, 2026-04-25) / v2 토론 (6엔진, 2026-04-25) / Solo Verifier 검증 (2026-04-25) |
| 채택안 | **통합안 (I + G + D-관찰)** — verifier 1순위 추천 |
| Decision 수 | 3 신규 (S5-1 / S5-2 / S5-3) + 보류 2 (H-lite / F) |
| 검증 방식 | Charter v2 [확정 선행 결정] 무파괴 + R7 (Tier 3 보류 안건) 정합성 + Phase 5 5000틱 × 3 seed acceptance |
| 작성일 | 2026-04-25 |

---

## 채택 근거 (3 토론 자료 통합)

### v1 토론 결론 (D + G, 2026-04-25)
- 4엔진: Claude opus + Codex × 2 + Gemini (Gemini FAILED — auth 만료)
- 합의: D (Territory locking via residence_ticks → affiliation_kernel 입력) + G (respawn 200틱 grace), F 영구 제외, fallback `W_TRUST 0.8→0.6`

### v2 토론 결론 (I + G, 2026-04-25)
- 6엔진: Claude opus + Codex × 5 (gpt-5.5 xhigh)
- 합의: I (W_TRUST 0.8→0.5, W_TERRITORY_SAME 0.3→0.5) + G (200틱 grace), H-lite Stage 6 이월
- Disputed: H-lite 시점 (Claude=Stage 6 / Codex=Stage 5), 우선순위 (Claude=G+F+I / Codex=H-lite+I)

### Solo Verifier 메타 분석 결과
- v2 conclusion §1 "I 암묵 합의" — shallow consensus로 격상. **Codex는 R1~R3 끝까지 F+G 일관**, I는 R3 Claude opus 단독 도입. v2 신뢰도 MEDIUM.
- v1 fallback "W_TRUST 0.8→0.6"은 v1 본인이 v2 차원(가중치 재균형)을 fallback으로 인정한 증거 → I는 두 토론에서 **독립 도출**된 강한 신호.
- 두 토론 모두 사실상 *Claude opus + Codex 1쌍* 수렴 (v1: Gemini FAILED, v2: 5 codex 슬롯이 단일 디스크 파일로 압축 — discuss 인프라 한계, [별도 백로그](#discuss-infrastructure)).
- 자연 탄생 원칙(top-down 금지) vs Rule 17~20(근본 원인 우선) 충돌 — Stage 5 단일 차원에서 완전 해소 불가. **통합안은 부분 충족**.

### 통합안의 정합성
| 측면 | I (가중치 재균형) | G (grace) | D (관찰) |
|------|----|----|----|
| 근본 원인 처치 | ✅ 본질 (Rule 17 충족) | ⚠️ 보조 안전판 | ❌ 관찰만 |
| 자연 탄생 원칙 | ✅ 가중치는 SSoT 상수 | ✅ 신생 보호 (top-down 아님) | ✅ read-only |
| 무파괴 (Charter v2 #1~#9) | ✅ Decision Card 권한 | ✅ 신규 필드 (시맨틱 분리) | ✅ read-only |
| 변경 표면적 | 2라인 | ~20 LOC | ~10 LOC |
| 미달 시 fallback 차원 | (자체 fallback 없음) | (자체 fallback 없음) | **D 입력 격상 (Stage 5.5)** |

**통합 결정**: I = 근본 처치 / G = 신생 보호 / D = 미달 시 차원 전환 입력 확보. 셋이 합쳐져 v2의 shallow consensus 위험을 해소(D가 R1 v1 합의를 이어받아 검증축 분리), v1의 fallback 인정을 본 처치로 격상(I), Stage 1~3 보조 처방은 유지(G가 Stage 3 founder_respawn 자연 귀결).

---

## 불변 원칙 (모든 Stage 5 Decision이 준수)

Charter v2 [확정 선행 결정] 9종 + Phase 17 Decision 1~11 불변 원칙 7종을 모두 계승한다. 본 Stage 5 변경은 다음 8 무파괴 제약 어느 것도 위반하지 **않는다**.

1. **Charter v2 #1~#9** — kernel/HandoffAPI/SNN 시그니처 동결: 본 Stage 5는 가중치 *상수*만 변경 (수식·시그니처 무수정)
2. **D10 read-only 5채널 freeze** — `faction_demographics / faction_economic_pressure / faction_relational_field / faction_territorial_overlap / faction_collective_charter` 시그니처: 무영향
3. **Phase 11~16 Hard 5지표** — 경제/사회 회귀 테스트: kernel 레이어 변경, 무영향
4. **SNN n_neurons=1000 freeze** — `readout_weights_v1.npy`: kernel과 SNN은 분리, 무영향
5. **FactionChangeSource 4종 freeze** — `birth_founder | drift | affiliation | conflict`: 본 Decision은 신호 분류 무변경 (가중치 상수만)
6. **CHARTER_PRIMITIVE_COUNT=(3,5)** — `(min, max)` faction charter 길이: 무영향
7. **결정성 RNG 단일 경로** — `_derive_rng("faction_*", key_parts)`: 가중치 변경은 RNG 경로 무영향
8. **단방향 SSoT** — `persona.faction` 주, `Territory.factionRef` 파생: 무영향

추가로 Φ-2 자연 탄생 3원칙도 준수: (a) Founder+Charter만 정의, (b) 멤버십은 kernel 창발, (c) 어떤 처방도 강제 배치 도입 금지.

---

## Decision S5-1 — Affiliation Kernel 가중치 재균형 (I) [확정]

### 변경 사양

`Projects/personas/loom/ontology/layers.py:197~199`:

```python
# Before (v5 2026-04-23)
W_TERRITORY_SAME = 0.3   # 같은 territory 거주 시
W_TERRITORY_DIFF = 0.1   # 다른 territory 거주 시
W_TRUST = 0.8

# After (v6 2026-04-25 — Stage 5)
W_TERRITORY_SAME = 0.5   # 같은 territory 거주 시 (v5: 0.3 → v6: 0.5, trust와 동률)
W_TERRITORY_DIFF = 0.1   # 유지 (다른 territory에 강한 cost 의도 없음)
W_TRUST = 0.5            # (v3~v5: 0.8 → v6: 0.5, 누적 우위 비대칭 해소)
```

`W_GRIEVANCE = 0.6` / `W_PROXIMITY = 0.4` / `DECAY = 0.92` 등 다른 가중치는 **변경 없음**.

### 근거: 근본 원인 = 가중치 비대칭 자체

| 가중치 분포 | trust 누적 효과 | territory 동거 효과 | 합산 결과 |
|---|---|---|---|
| v5: trust 0.8, territory 0.3 | DECAY 0.92로 누적되면 단일 faction 우위 자연 형성 | 동거 효과 약함 | **absorbing state** |
| v6: trust 0.5, territory 0.5 | 누적 가능하지만 territory와 동률 | 동거 효과 trust와 동률 | **다극 평형** |

trust는 시간 누적성이 강하고 territory는 공간 동시성이 강하다. 두 신호가 비대칭이면 누적성 강한 trust가 시간이 갈수록 우위 → 단일 faction 흡수. 동률(0.5/0.5)이면 신생 faction의 territory 동거 효과가 trust 누적 효과를 상쇄.

### Tier 3 R7 안건 정합성

[PHASE-17-FACTION-DECISIONS.md:63 (R7)](PHASE-17-FACTION-DECISIONS.md): `D4 W_TERRITORY=1.0 동적 감소 (시뮬 중반 이후 W_TRUST 점진 증가)`.

R7은 Tier 3(Phase 5 실측 판단)으로 보류된 안건이며, **Phase 17 Decision 4 본문은 v3 시점**(W_TERRITORY=1.0)이고 [layers.py:235](Projects/personas/loom/ontology/layers.py)의 `W_TERRITORY = W_TERRITORY_SAME` 별칭으로 v5 시점에 이미 0.3으로 정적 감소함. 본 Stage 5 변경은:

- **방향**: R7은 territory 동적 감소 + trust 점진 증가를 제안. v6는 그 반대 — trust 감소(0.8→0.5) + territory 증가(0.3→0.5). v5 실측 데이터(probe 3 seed 전원 active_end=1)가 R7 가설을 *반증*함 — trust 우위가 흡수의 원인이지 territory 결정론이 원인이 아님.
- **정신**: R7의 의도(trust ↔ territory 균형 탐색)는 계승. 동적이 아닌 정적 재균형으로 해소.
- **종결 조건**: Stage 5 acceptance 통과 시 R7 안건은 *자연 종결* (정적 균형으로 충분). 미달 시 D 입력 격상(Stage 5.5)이 R7의 동적 측면을 부분 계승.

### 변경 표면적

- 코드 수정: 2라인 ([layers.py:197](Projects/personas/loom/ontology/layers.py), [layers.py:199](Projects/personas/loom/ontology/layers.py))
- 부수 효과: `W_TERRITORY = W_TERRITORY_SAME` 별칭 ([layers.py:235](Projects/personas/loom/ontology/layers.py)) → 자동으로 0.5로 갱신 (deprecated 경로 유지, Decision 4 v3 본문 호환)
- 주석 갱신: layers.py 195~196 라인 v6 주석으로 갱신 + `PHASE-17-AFFILIATION-TUNE-SPEC.md` 참조 갱신 (별도 spec 갱신 항목)

### THETA_JOIN·DRIFT_MARGIN 영향

[PHASE-17-FACTION-DECISIONS.md:450](PHASE-17-FACTION-DECISIONS.md): `THETA_JOIN=2.5는 단일 틱 max kernel score ≈ W_TERRITORY(1.0) + W_TRUST(0.8)*0.5 + W_PROXIMITY(0.4)*0.5 ≈ 1.6` 근거가 v3 시점. v6 가중치(territory 0.5, trust 0.5)에서는:

```
max_single_tick ≈ 0.5 + 0.5*0.5 + 0.4*0.5 = 0.95
```

DECAY 0.92로 2~3틱 누적 시 ~2.4 도달. THETA_JOIN=2.5는 *살짝 보수적* — 가입 문턱이 1틱 더 길게 작동하는 효과(자연 탄생 원칙에 부합). **THETA_JOIN 변경 없음** (가입 임계는 안정성 우선, Stage 5에서는 가중치만 단일 차원 변경).

DRIFT_MARGIN_MIN(0.3) / DRIFT_MARGIN_RATIO(0.15)는 동적 계산이라 가중치 비례. 무변경.

### Acceptance 검증 항목
- 가중치 변경 후 Stage 4 acceptance(`active_end >= 2`) seed 7/13/42 재실행 시 3/3 PASS

---

## Decision S5-2 — Founder Respawn Grace Period (G) [확정]

### 변경 사양

#### 1) 신규 필드 (Faction dataclass)

`Projects/personas/loom/ontology/layers.py` Faction:

```python
@dataclass(slots=True)
class Faction:
    # ... 기존 필드 ...
    grace_until_tick: int = 0    # Stage 5: respawn 직후 drift 면역 종료 시각 (절대 tick)
```

#### 2) 신규 상수

```python
# ── Phase 17 Stage 5: Respawn grace period (G, 2026-04-25) ──
# 근거: Stage 3 founder_respawn 직후 신생 faction이 trust 누적 우위에 즉시 흡수되는
# second-collapse pattern. 200틱 동안 drift 입력 단계에서 면역.
RESPAWN_GRACE_TICKS = 200
```

#### 3) 발동 위치

`multi_tick_engine.py` founder_respawn 직후 (faction 생성 시점):
```python
new_faction.grace_until_tick = self.time.tick + RESPAWN_GRACE_TICKS
```

#### 4) 면역 적용 위치

`multi_tick_engine.py` drift 평가 단계 — 멤버 페르소나의 drift_score 계산 시:
```python
faction = self.factions.get(persona.faction)
if faction and faction.grace_until_tick > self.time.tick:
    continue  # grace 기간 동안 drift 평가 면제 (면역)
```

### faction_cooldown 채널 재사용 금지 (시맨틱 분리)

**Verifier 권고 반영**. 기존 `FACTION_COOLDOWN_TICKS=48` ([layers.py:206](Projects/personas/loom/ontology/layers.py))는 *재가입 락*(reform/dissolve 직후 재진입 방지) 시맨틱이며, Stage 5 grace는 *drift 면역* 시맨틱이다. 두 의미가 다르므로:

- 신규 필드 `grace_until_tick` 단독 추가 (faction_cooldown 채널 미사용)
- `_tick_faction_cooldown` helper ([Decision Card R1](PHASE-17-FACTION-DECISIONS.md)) 무수정
- 결과적으로 Stage 5 G는 **Stage 3 founder_respawn의 자연 귀결**이며 *기존 안전 메커니즘과 독립*

### 변경 표면적
- 신규 필드 1개 (Faction)
- 신규 상수 1개 (RESPAWN_GRACE_TICKS)
- 신규 호출 2곳 (respawn 시 set / drift 평가 시 check)
- 총 ~20 LOC

### Charter v2 무파괴
- D10 read-only 5채널: 무영향 (drift 면역은 *입력 게이팅*, 5채널 *시그니처/내용* 무수정)
- FactionChangeSource 4종: drift source 자체는 그대로, 면역은 평가 진입 차단일 뿐
- 결정성: 면역 분기는 결정적 비교 (`faction.grace_until_tick > self.time.tick`)

---

## Decision S5-3 — Territory Residence Read-only Observation (D-관찰) [확정 — 관찰만]

### 변경 사양

#### 1) 신규 필드 (InnerWorld)

`Projects/personas/loom/ontology/layers.py` InnerWorld:

```python
@dataclass(slots=True)
class InnerWorld:
    # ... 기존 필드 ...
    residence_ticks: dict[str, int] = field(default_factory=dict)  # territory_id → 누적 거주 ticks
```

#### 2) 누적 위치

`multi_tick_engine.py` 매 틱 territory 거주 갱신 단계 (Stage 1 economy/movement loop 내):
```python
inner.residence_ticks[persona.territory] = inner.residence_ticks.get(persona.territory, 0) + 1
```

#### 3) read-only 보장

본 Decision에서는 `residence_ticks` 가 **affiliation_kernel 입력으로 진입하지 않는다**. 단순 누적 + 측정/로깅 용.

### Stage 5.5 격상 조건 (보류)

다음 조건 *모두* 충족 시 Stage 5.5에서 affiliation_kernel 입력 격상 결정 (별도 Decision Card):
1. Stage 5 acceptance secondary 미달 (`gini < 0.40` 또는 `last_500_active>=2 < 0.95`)
2. residence_ticks 분포에서 **territory별 거주 편차가 trust 효과와 정량적으로 분리 가능**한 구조 신호 발견
3. 격상 시 가산 형태(`W_RESIDENCE * residence_density(persona, faction_members)`) — **새 source 신설이 아니라 territory source 강화**로 분류 (FactionChangeSource 4종 무위반)

### 변경 표면적
- 신규 필드 1개 (InnerWorld)
- 신규 호출 1곳 (매 틱 누적)
- 총 ~10 LOC

### Charter v2 무파괴
- read-only 누적은 D10 5채널과 분리된 InnerWorld 필드 (D10 시그니처 무영향)
- affiliation_kernel 입력 미진입 → kernel 시그니처 무영향
- Stage 5.5 격상 시 별도 Decision으로 처리 (본 Decision에서는 관찰만)

---

## 보류 — Stage 6 또는 Φ-3 이월

### H-lite (founder_lineage) — Stage 6 이월

| 항목 | 결정 |
|---|---|
| 위상 | Stage 6 후보 |
| 진입 조건 | `founder_lineage` 변화의 **FactionChangeSource 4종 매핑 증명** 동반 (Codex측 derivation trace + source 분류표) |
| 거부 사유 | 매핑 모호 시 5번째 source 신설 압력 → Charter v2 #5 위반 |
| 검증 위임 | [/sub p-charter-consistency](skills/sub) 분류표 검증 후 본 Decisions에 흡수 |

### F (이탈 비대칭 cost) — Stage 6 또는 Φ-3 이월

| 항목 | 결정 |
|---|---|
| 위상 | Stage 6 또는 Φ-3 후보 |
| 진입 조건 | Stage 5 통합안(I+G+D-관찰) 5000틱 acceptance **미달**일 때만 검토 |
| 거부 사유(현 시점) | 가입은 자연 임계(THETA_JOIN), 이탈은 강제 비대칭이면 자연 탄생 원칙(top-down 금지) 회색지대 |
| 회색지대 해소 조건 | 이탈 cost가 *상태 의존*(grievance 낮음 시 자연 약화) 형태로 표현 가능하면 자연 처방으로 재분류 가능 |

---

## Acceptance Gate

### 5000-tick × 3 seed (7 / 13 / 42) 실행

#### Primary (필수 — 미달 시 Stage 5 미수렴)
| 지표 | 임계 | 의미 |
|---|---|---|
| `active_factions_end` (3 seed 평균이 아닌 **개별**) | `>= 2` for ALL 3 seeds | 다극 평형 도달 |

#### Secondary (성공 품질 — 미달 시 Stage 5.5 격상 검토)
| 지표 | 임계 | 의미 |
|---|---|---|
| `last_500_active>=2` ratio | `>= 0.95` | 종료 직전 안정성 (스파이크 아님) |
| `gini` (faction 인구 분포) | `>= 0.40` | 적절한 비대칭 (단일 우위도, 균등 파편화도 아님) |
| `drift_source_distribution_entropy` | `>= 0.6` | Charter/Trust/Territory/Drift 4종 균형 (단일 source 독점 차단) |
| `residence_ticks 분포` | 기록 (임계 없음) | Stage 5.5 입력용 |

#### 추가 Hard 무파괴 (Phase 11~16 회귀)
- 기존 5지표 (Charter v2 #4) 100% PASS — `test_class_promotion`, `test_economy`, `test_nomos`, `test_handover`, Charter test 5종

### 미달 시 Fallback 차원

```
1. Stage 5 Primary FAIL
   → 통합안 미수렴. Stage 5 재설계 (D 입력 격상 + 신규 차원 탐색)

2. Primary PASS / Secondary FAIL
   → Stage 5.5 결정 진입
       → 2-A: D affiliation_kernel 입력 격상 (`W_RESIDENCE` 가산)
       → 2-B: H-lite 4-source 매핑 증명 검토 후 Stage 6 진입

3. Primary + Secondary 모두 PASS
   → Stage 5 종결. R7 자연 종결. Φ-3 (Struggle) 진입 준비.
```

---

## Charter / 기존 Decision 정합성 검토

| 무파괴 제약 | 본 Decision 영향 | 검증 |
|---|---|---|
| Charter v2 #1 (kernel 시그니처) | 무영향 (가중치 *상수*만 변경) | ✅ |
| Charter v2 #2 (HandoffAPI 7종) | 무영향 | ✅ |
| Charter v2 #3 (SNN co-fire 300~349) | 무영향 (kernel과 SNN 분리) | ✅ |
| Charter v2 #4 (Phase 11~16 Hard 5지표) | 무영향 (회귀 테스트 통과 필수) | ⏳ Phase 5 검증 |
| Charter v2 #5 (FactionChangeSource 4종) | 무영향 (가중치만 변경, source 미신설) | ✅ |
| Charter v2 #6 (CHARTER_PRIMITIVE_COUNT=(3,5)) | 무영향 | ✅ |
| Charter v2 #7 (결정성 RNG) | 무영향 (RNG 경로 무수정) | ✅ |
| Charter v2 #8 (단방향 SSoT) | 무영향 | ✅ |
| Charter v2 #9 (D10 read-only 5채널) | 무영향 (시그니처/내용 무수정) | ✅ |
| Decision 4 v3 본문 (W_TERRITORY=1.0) | **갱신 권한** (본 Decision이 최신 SSoT) | 본 문서 SSoT |
| Tier 3 R7 (W_TERRITORY 동적 감소) | **자연 종결 후보** — Stage 5 acceptance 통과 시 R7 종결 | ⏳ Phase 5 검증 |
| Stage 1~3 보조 처방 (size tax/homeostasis/minority/founder_respawn) | 유지 (G는 founder_respawn의 자연 귀결) | ✅ |

### Charter 본문 갱신 필요성 — **불필요**

[PHASE-17-FACTION-CHARTER.md:233](PHASE-17-FACTION-CHARTER.md): `가중치 W_*, 임계치 THETA_JOIN, DRIFT_MARGIN, DECAY, FACTION_COOLDOWN_TICKS 초기값은 Phase 3 Decision Card에서 확정`. 즉 Charter 본문은 가중치를 *Decision Card 권한* 항목으로 명시했고, Stage 5 가중치 갱신은 Decision Card 갱신 권한 행사 — **Charter 본문 무수정**.

[PHASE-17-FACTION-CHARTER.md:329~333](PHASE-17-FACTION-CHARTER.md) [보류 해소 현황] 섹션에 Stage 5 갱신 흔적 추가는 *선택* (현황 보존 의미만). 본 Stage 5 진입에서는 추가하지 않으며, Φ-3 진입 시 Phase 17 종결 보고에서 일괄 갱신.

### Decision 4 본문 갱신

[PHASE-17-FACTION-DECISIONS.md](PHASE-17-FACTION-DECISIONS.md) Decision 4 본문은 v3 시점 `W_TERRITORY=1.0` 표기. 본 Stage 5 결정으로:
- v6 항목을 Decision 4 변경 로그에 **추가** (덮어쓰기 아님 — 시간 흐름 보존)
- 또는 본 PHASE-17-FACTION-STAGE5-DECISIONS.md를 **신규 SSoT**로 두고 Decision 4 v3을 historic으로 유지

권장: **후자**(Decision 4 historic, Stage 5 신규 SSoT). 이유:
1. Phase 3 Decision Card는 *Decision 시점 합의*의 기록이고, Stage 5는 *Stage 4 closure 후 새 단계*
2. Decision 4 v3을 갱신하면 R7 안건이 Decision 4 본문에서 사라져 추적성 손실
3. /spec 진입자(Codex)는 본 STAGE5-DECISIONS.md만 읽으면 Stage 5 사양 완결

따라서 Decision 4는 *historic* 보존, 본 문서가 Stage 5 SSoT.

---

## 다음 단계

1. **/spec PHASE-17-FACTION-STAGE5-CODEX-INSTRUCTIONS.md 생성** — 본 Decisions를 Codex 구현 지시서로 번역. CTS 기본값 적용. /spec 자체 체크리스트 통과 후 Codex 발주.
2. **Phase 5 5000틱 × 3 seed 실행** — acceptance Gate (Primary + Secondary).
3. **Phase 5 결과 보고** — `subagent-runs/claude/stage5-acceptance-2026-04-XX/` 에 evidence 기록 (Primary PASS/FAIL + Secondary 5지표 + residence_ticks 분포).
4. **분기 결정**:
   - 전부 PASS → Stage 5 종결 + R7 자연 종결 + Φ-3 (Struggle) 진입 준비
   - Primary PASS / Secondary FAIL → Stage 5.5 (D 격상 또는 H-lite Stage 6 검토)
   - Primary FAIL → Stage 5 재설계

---

## 메타: 토론 인프라 백로그 {#discuss-infrastructure}

본 결정의 v2 토론(6엔진)에서 5 Codex 슬롯이 **단일 디스크 파일**(`participant-codex-r1.last.txt` / `codex.md`)로 압축 저장됨. 모더레이터는 5명 응답 모두 받았으므로 결과 자체는 영향 없음. 단:
- *재현성*: 5 codex 응답 개별 추적 불가
- *shallow consensus 차단 메커니즘*: 슬롯별 role 분기(구현/수치/회귀/근본/대안)가 디스크에서 검증 불가
- *후속 토론* 발주 시 동일 모델 다중 슬롯 사용 시 슬롯별 파일 분리 필요

**별도 백로그**: discuss-runner participant 인스턴스 ID 기반 파일 분리 (`participant-codex-1.r1.txt`, `participant-codex-2.r1.txt`, ...). 본 Stage 5에서는 결정 영향 없음 (verifier 메타 분석으로 보완).
