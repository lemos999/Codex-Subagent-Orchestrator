# Q5 설계 탐색 — SNN Readout × affiliation_score 결합

> 상태: [탐색] — 확정 전 단계
> 선행: PHASE-17-AFFILIATION-TUNE-SPEC.md (Stage 1, 파라미터 튜닝)
> 후속: Stage 2 또는 v6 튜닝 지시서의 입력
> 제약: brain/** 수정 금지 (Phase 14-B 불변)

---

## 문제 정의

`/discuss --quick` (2026-04-23) Q5 "SNN readout을 score에 어떻게 결합하나"가 3엔진 전원 미처리로 남았다. 토론에서 제안된 "창발 동역학"(Gemini) 방향이 수식화되지 않았고, affiliation_score는 여전히 결정론적 · 관측 불변 구조.

**궁극 질문**: affiliation_score가 "페르소나의 SNN 내부 상태"를 반영해야 하는가? 그렇다면 어떻게?

---

## 현재 SNN readout 인터페이스 (불변)

`PersonaBrain` ([Projects/personas/loom/brain/persona_brain.py](Projects/personas/loom/brain/persona_brain.py)) 공개 신호:

| 신호 | 위치 | 차원 | 성격 |
|------|------|------|------|
| `_last_firing_rate` | persona_brain.py:198 | (n_neurons=1000,) | 매 틱 업데이트, 외부 read 가능 |
| `action_logits` | persona_brain.py:204 | (6,) = [idle, work, eat, sleep, explore, socialize] | tick() 내부에서만 계산, 재계산 필요 |
| `readout_weights` | persona_brain.py:32-47 | (6, 1000) | adapt_readout으로만 변경 |
| `get_stats()` | persona_brain.py:327 | dict | firing_rate, exc_rate, inh_rate |
| `personality` (input) | persona_brain.py:55 | (5,) float32 | 외부 주입, static |
| `drive` | persona_brain.py:227-241 | scalar | tick 내부 계산 (mastery+aptitude+flow+da) |

**외부(multi_tick_engine.py)에서 접근 가능한 것 (read-only)**:
- `persona.brain._last_firing_rate` → numpy (1000,)
- `persona.brain.readout_weights` → (6, 1000)
- `persona.personality` → (5,) — 이미 외부 객체 필드

**접근 불가 (brain 수정 필요)**:
- tick 중 계산된 `drive` 값 (외부 캐시 없음)
- 각 input channel별 자극량 (tone/skill/economic 신호 분리)

---

## 제약 정리

1. **brain/** 수정 금지 — 기존 테스트 8/8 유지
2. SSoT `_change_persona_faction` 경로만 허용
3. 재현성 — seed 고정 시 결정론적 동작 유지 (연구자 요구)
4. 계산 비용 — 매 페르소나 × 매 틱 × 각 faction 조합에 O(n_neurons) 연산 금지
5. Stage 1 튜닝(W_TERRITORY_SAME/DIFF + 동적 margin)과 독립 적용 가능해야 함

---

## 후보안 4종

### 방안 A — Social Logit 기반 W_TRUST 스케일링

**개념**: `action_logits["socialize"]` 값이 높은 페르소나는 faction 내 trust 기반 점수를 증폭. "사교적이면 동료 소속감이 더 강하다"는 자연 해석.

**수식**:
```python
# multi_tick_engine.py 내부, _compute_affiliation_tick
brain = persona.brain
fr = brain._last_firing_rate  # (1000,)
socialize_idx = 5  # ACTIONS.index("socialize")
social_logit = float(brain.readout_weights[socialize_idx] @ fr)
# 정규화: tanh로 [-1, 1] → [0.5, 1.5] 스케일 계수
trust_scale = 1.0 + 0.5 * math.tanh(social_logit * 0.1)

score = (
    territory_weight
    + W_TRUST * trust_scale * self._trust_density(persona, fid)
    + W_GRIEVANCE * self._shared_grievance(persona, fid)
    + W_PROXIMITY * self._spatial_proximity(persona, fid)
)
```

**효과 분석**:
- 외향 페르소나: trust 영향 1.5x → 가까운 faction 고속 흡수
- 내향 페르소나: trust 영향 0.5x → trust 기반 drift 약함
- 결정론: 동일 seed에서 동일 firing_rate → 동일 scale (재현성 유지)

**비용**: 페르소나당 `readout_weights[5] @ firing_rate` = 1000 곱셈. 12페르소나 × 5000틱 = 6천만 연산. 허용.

**장점**: 직관적, 수학적 명쾌, 개체차 명시화
**단점**: 6개 action logit 중 1개만 활용. 다른 5개 성향(work/explore 등) 무시

**drift ratio 예측 기여**: +2~4% (Stage 1 단독 대비 추가)

---

### 방안 B — Firing Rate Entropy → Chaos Drift Force

**개념**: `firing_rate`의 Shannon entropy가 높을수록 (발화 패턴이 분산) "혼란·탐색" 상태. 이때 drift 확률이 증가. Gemini가 주장하려 했던 "stochastic force" 형태.

**수식**:
```python
# _compute_affiliation_tick 내
fr = persona.brain._last_firing_rate
fr_norm = fr / (fr.sum() + 1e-9)  # (1000,), sum=1
entropy = -float(np.sum(fr_norm * np.log(fr_norm + 1e-9)))  # nats
max_entropy = math.log(1000)  # ≈ 6.91
chaos = entropy / max_entropy  # [0, 1]

# 매 faction에 chaos 비례 gaussian noise (결정론 유지: 페르소나별 고정 rng)
persona_rng = self.rng_per_persona[pid]  # engine이 관리하는 페르소나별 seed
for fid in self.factions:
    noise = persona_rng.gauss(0, chaos * CHAOS_DRIFT_SCALE)  # CHAOS_DRIFT_SCALE = 0.3
    scored[fid] += noise
```

**효과 분석**:
- 고엔트로피 (혼란/탐색): noise σ ≈ 0.3 → 가끔 rival score가 current보다 높아짐 → drift
- 저엔트로피 (고정 패턴): noise σ ≈ 0.05 → 안정 유지
- 노이즈가 결정론 유지: `rng_per_persona[pid]`가 매 시뮬에서 동일 sequence

**비용**: `entropy` = 1000번 로그 연산 / 페르소나 / 틱 = 12 × 5000 × 1000 = 6천만. 약간 부담. 최적화 가능: firing_rate 정규화 캐시 재사용.

**장점**: Gemini "창발 동역학" 관점 구현, 진짜 non-deterministic 힘 도입
**단점**: 
- 재현성을 위해 `rng_per_persona` 인프라 신설 필요 (엔진 구조 변경)
- 해석 난이도 (entropy가 왜 drift와 관련? 직관 약함)
- 노이즈가 너무 강하면 faction이 flicker (매 48틱 바뀜)

**drift ratio 예측 기여**: +5~8% (Stage 1 단독 대비 추가), 단 "의미 있는 drift"인지 별도 검증 필요

---

### 방안 C — Personality 직접 결합 (SNN 부분 우회)

**개념**: `personality[5]` 벡터를 W_TRUST/W_PROXIMITY 가중치 계수로 사용. SNN 우회하지만 외부 input인 personality가 이미 brain 내부에서 logit에 녹아 있으므로 "간접 SNN 결합"으로 간주 가능.

**수식**:
```python
# persona.personality: float32[5]
# [0] 내향(-) ↔ 외향(+): trust 선호
# [3] 독립(-) ↔ 협조(+): proximity 선호
p = persona.personality
extrovert = max(0, float(p[0]))  # 외향만 양수 추출, 내향은 0
cooperative = max(0, float(p[3]))

trust_scale = 1.0 + 0.4 * extrovert  # [1.0, 1.4]
proximity_scale = 1.0 + 0.3 * cooperative  # [1.0, 1.3]

score = (
    territory_weight
    + W_TRUST * trust_scale * self._trust_density(persona, fid)
    + W_GRIEVANCE * self._shared_grievance(persona, fid)
    + W_PROXIMITY * proximity_scale * self._spatial_proximity(persona, fid)
)
```

**효과 분석**:
- 개체차 static 반영 (SNN의 dynamic 상태는 반영 안 됨)
- 페르소나 고유 성향 유지 → faction 소속 다양화

**비용**: O(1) per persona × faction. 거의 무료.

**장점**: 가장 안전, 구현 즉시, 이미 존재하는 데이터 활용
**단점**: "SNN readout 결합"이라는 질문 정신에 부합하지 않음. Static personality는 창발 동역학 아님

**drift ratio 예측 기여**: +1~2% (Stage 1 단독 대비 추가)

---

### 방안 D — action_logits 전체 벡터 × faction charter 정합성

**개념**: 페르소나의 행동 성향 벡터 (6차원 action_logits)와 faction charter의 primitive 기대치가 얼마나 맞는지로 친화도 추가. Charter "장자_상속 + 능력주의" faction에는 work 로짓 높은 페르소나가 끌림.

**수식**:
```python
# faction.charter → expected_action_bias (수작업 매핑)
CHARTER_ACTION_AFFINITY: dict[str, dict[str, float]] = {
    "토지_공유": {"work": 0.0, "socialize": 0.3, "explore": 0.1, "idle": -0.1},
    "능력주의": {"work": 0.5, "explore": 0.2, "idle": -0.3},
    # ... 12개 primitive 각각
}

# compute
fr = persona.brain._last_firing_rate
action_logits = persona.brain.readout_weights @ fr  # (6,)
action_norm = (action_logits - action_logits.mean()) / (action_logits.std() + 1e-9)

charter_affinity = 0.0
for primitive in faction.charter:
    expected = CHARTER_ACTION_AFFINITY.get(primitive, {})
    for action_name, bonus in expected.items():
        idx = ACTIONS.index(action_name)
        charter_affinity += action_norm[idx] * bonus
charter_affinity /= len(faction.charter)

score = (
    territory_weight
    + W_TRUST * self._trust_density(persona, fid)
    + W_GRIEVANCE * self._shared_grievance(persona, fid)
    + W_PROXIMITY * self._spatial_proximity(persona, fid)
    + W_CHARTER * charter_affinity  # 신규 항, W_CHARTER = 0.5 가정
)
```

**효과 분석**:
- Charter 기반 자연적 분화: "work 지향 페르소나는 능력주의 faction 선호"
- SNN readout 전 벡터 활용 (A는 1차원만)
- drift 경로 다변화: territory, trust, grievance, proximity + **charter 정합성**

**비용**: `readout_weights @ firing_rate` per persona = 6 × 1000 = 6000 연산. 페르소나 12명 × 5000틱 = 3.6억. 부담. faction 매 commit에서만 계산하면 12 × (5000/48) × 6000 = 750만 → 허용.

**장점**: 창발 다변화, charter 시스템과 유기적 결합, 다른 방안과 직교 (A+B와 함께 적용 가능)
**단점**: CHARTER_ACTION_AFFINITY 테이블 수작업 작성 필요 (bias 주입 우려), 정합성 매핑이 과도한 가정

**drift ratio 예측 기여**: +3~5%, 단 "의미 있는 정착" (charter-fit faction으로 수렴)

---

## 비교 표

| 방안 | brain 수정 | 비용 | 창발성 | 구현 난이도 | drift+ 예상 | Stage 1과 직교? |
|------|:--:|:--:|:--:|:--:|:--:|:--:|
| A social_logit | 없음 | 중간 | 중 | 낮음 | +2~4% | 예 |
| B chaos entropy | 없음 | 중상 | **상** | 중 (rng 인프라) | +5~8% | 예 |
| C personality | 없음 | 무료 | 하 | 매우 낮음 | +1~2% | 예 |
| D charter × action | 없음 | 낮음(commit만) | 중상 | 중 (매핑 테이블) | +3~5% | 예 |

---

## 조합 권고

Stage 1 단독은 drift 0% → 5~10% 예상. 창발 궁극 목표(Φ-2 → Φ-3 전이 재료 축적)까지 doubling 필요.

**Tier 1 조합 — 안전 최적 (Stage 1 + C)**:
Stage 1 파라미터 튜닝 + Personality 직접 결합. 비용 최소, brain 미수정, 즉시 적용.
drift 예상: 6~12%. 창발성 약함.

**Tier 2 조합 — 창발 최적 (Stage 1 + A + B)**:
Stage 1 + Social Logit 스케일 + Chaos Entropy Noise. brain 미수정, rng 인프라 신설.
drift 예상: 12~22%. 창발성 강함.

**Tier 3 조합 — 완전 (Stage 1 + A + B + D)**:
위 + charter × action 결합. 매핑 테이블 작성 필요.
drift 예상: 15~30%. 창발성 최강. 리스크: flicker 가능, 튜닝 복잡.

---

## 권고 로드맵

1. **Stage 1 구현 + probe v5 검증** (PHASE-17-AFFILIATION-TUNE-SPEC.md) — 베이스라인 확립
2. Stage 1 결과 `drift ≥ 5%` 면: **Tier 1 추가**(Personality 결합) → Stage 1.5 지시서
3. Stage 1 결과 `drift < 5%` 면: **Tier 2 추가**(Social Logit + Chaos) → Stage 2 재설계
4. Stage 2 후에도 `active_factions` 분화 미발생: **Tier 3**(Charter × Action) 검토
5. 각 단계 사이 Phase 14-B 8/8 회귀 테스트 필수

---

## [확정]
- SNN readout 결합은 **brain/ 수정 없이** 외부에서 `_last_firing_rate` 읽는 방식으로 구현
- 재현성 유지가 non-negotiable (연구·논문 목적)
- Stage 1 완료 전까지 본 설계는 **대기** — 베이스라인 측정 후 결정

## [보류]
- 구체 Tier 선택 (Stage 1 결과 후 결정)
- `CHARTER_ACTION_AFFINITY` 테이블 (12 primitive × 6 action 수작업 bias)
- `rng_per_persona` 인프라 신설 설계 (Tier 2 이상 시)

## [미결]
- brain readout이 personality 5축을 이미 logit에 녹이므로 방안 A/C 일부 중복 우려 — Stage 1 후 ablation 필요
- Chaos noise가 "의미 있는 drift" vs "flicker"를 만드는지 판정 기준
- action_logits 전체를 매 affiliation tick 재계산하는 비용 감당 가능한지 5000틱 실측 필요
