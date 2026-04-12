# Discussion Summary

**Topic**: 페르소나 기억 시스템 심층 설계 — ★★★★ 수준으로 끌어올리기

## 핵심 참조 (하사비스 관점)

데미스 하사비스의 기억에 대한 핵심 진단:
- 큰 컨텍스트 윈도 ≠ 에피소드 기억. 오히려 작업기억에 가깝다
- 인간은 대부분을 버리고 정말 중요한 것만 남긴다
- 정서(감정)가 기억의 필터: 정서적으로 강한 사건을 더 잘 기억
- AI에게 빠진 것은 더 많은 기억이 아니라 '망각(forgetting)' = garbage collection
- 저장 비용 + 검색 비용 = 기억의 진짜 비용
- 기억을 기록하는 시점에 '미래에 얼마나 유용할지' 평가하는 가치 판단 장치 필요

이 관점을 참조하되 매몰되지 말고, PersonaBrain SNN의 맥락에서 독자적으로 설계.

## 현재 상태: ★★ (개념 정의만)

기억 5유형 정의 + 에피소드 미구현 식별 + Layer 위치(L3d). 끝.

## 목표: ★★★★ (다른 Charter 수준)

다른 Charter가 가진 것: 생애주기, 메커니즘 상세, 데이터 구조 개요, 위기 시나리오, 성공 기준, Ontology 연결.

## 설계해야 할 것

### 1. 기억의 생애주기
인코딩(encoding) → 저장(storage) → 인출(retrieval) → 재통합(reconsolidation) → 망각(forgetting)
- 인코딩: 어떤 경험이 기억이 되는가? 전부가 아니라 '선택'된다
- 저장: 어디에, 어떤 형태로?
- 인출: 무엇이 인출을 트리거하는가? (단서, 맥락, 감정)
- 재통합: 인출된 기억은 변한다 (기억은 고정이 아니라 재구성)
- 망각: 왜 잊는가? (에너지 절감? 간섭? 시간? 의도적 억압?)

### 2. 망각의 경제학 (하사비스 핵심)
- 무엇을 남기고 무엇을 버릴지의 '선택의 경제성'
- 감정이 필터: 정서적으로 강한 사건 = 높은 salience → 보존
- 중립적 사건 = 낮은 salience → 자연 소멸
- 반복 인출 = salience 상승 → 보존
- '가치 판단 장치': 미래 유용성 평가 — PersonaBrain에서 이것은 무엇인가?

### 3. 기억 간 간섭과 왜곡
- 순행 간섭: 새 기억이 옛 기억 인출을 방해
- 역행 간섭: 옛 기억이 새 기억 저장을 방해
- 기억 재통합: 인출할 때마다 기억이 조금씩 변한다
- 거짓 기억: 기억했다고 믿지만 실제로는 없었던 일
- 특정 단어/냄새/장소가 전혀 다른 연상을 일으키는 현상 (연상 네트워크)

### 4. 기억과 12클러스터의 구체적 관계
- C(Cognition/ACh): 인코딩과 학습
- B(Bonding/OXT): 사회적 기억 강화
- T(Tension/CORT): 스트레스가 기억 형성을 방해/강화
- F(Fatigue/ADO): 피로가 기억 인출을 저하
- I(Inhibition/GABA): 수면 중 기억 정리
- L(Liking/β-END): 쾌감 기억의 선택적 보존
- A(Acute/NE): 각성 상태에서 섬광 기억(flashbulb memory) 형성

### 5. 기억의 틱 파이프라인 경로
- Step 1: 인출 트리거 (현재 자극 + 연상 단서)
- Step 2: Layer 0에서 기억 관련 context 반영
- Step 4: 인출된 기억이 행동 선택에 영향
- Step 6: 이번 틱의 경험을 새 기억으로 인코딩
- 수면: 기억 정리 (NREM 정리 + REM 재조합)

### 6. 위기 시나리오 (위기 내장)
- 기억 조작: 누군가의 기억을 의도적으로 왜곡 (세뇌, 선전)
- 집단 기억: 사회 전체가 잘못된 기억을 공유 (역사 왜곡)
- 기억 과부하: 트라우마가 너무 많아 일상 기능 마비
- 기억 상실: 뇌 손상/극심한 스트레스로 기억 소실
- 거짓 기억 재판: 법정에서 거짓 기억이 증거로 채택

### 7. 어린 시절의 섬광 같은 회상 (하사비스 언급)
- flashbulb memory: 극도로 감정적인 순간의 생생한 기억
- PersonaBrain에서: NE(A)↑↑ + 감정(전체)↑↑ → salience 최대 → 영구 보존?
- 이것과 트라우마(H1)의 관계
**Rounds**: 3/3
**Converged**: no

## Conclusion

# 최종 결론: 페르소나 기억 시스템 설계

---

## 1. Consensus (합의점)

### A. Salience 기반 선택적 인코딩
- 모든 경험을 저장하지 않는다. **Salience 임계값(θ_enc)**을 초과한 경험만 에피소드 기억으로 진입
- Salience = f(정서강도, 인출빈도, 미래유용성) — 3차원 벡터로 정량화
- 12클러스터에서: **A(NE)**는 gain modulator(각성 시 인코딩 강화), **B(OXT)**는 사회적 기억 가중치 증폭

### B. 능동적 망각의 경제성 (하사비스 핵심 수용)
- 저장 비용 + 검색 비용 = 기억의 진짜 비용 → 아키텍처에 명시적 반영 필수
- **I(GABA)**가 망각 트리거 역할, 수면 틱에서 consolidation + pruning 처리
- 망각은 버그가 아니라 **가비지 컬렉션(GC)** — 설계된 기능

### C. 구조: Append-only + Maintenance 분리
- 원본 기억 로그는 불변(append-only) → 감사 추적 + 메타 분석 가능
- Foreground 틱: 읽기/인출만 (행동 선택 경로에 영향)
- **Maintenance tick(수면)**: 재통합·망각·통합 배치 처리 — 틱 시간 분리

### D. 기억 상태의 이산적 변화
- 기억은 연속적 값 변화가 아닌 **상태기계 전이**로 모델링
- CONSOLIDATED → LABILE(재활성화 윈도) → RECONSOLIDATED / EXTINCT

---

## 2. Disputed (미합의점)

| 쟁점 | Claude 입장 | Codex 입장 | 판정 |
|------|-------------|------------|------|
| **재활성화 대상 선택** | 맥락-패턴 중첩에 의한 **자발적** 재활성화 | Salience 순위 기반 **우선순위 큐** | 미결: 능동적 vs 수동적 |
| **유용성 갱신 주기** | 재활성화 윈도 한정 (온라인, 재활성화 시) | Epoch 기반 배치 (오프라인, 주기적) | 미결: 실시간 vs 배치 |
| **상태기계 명시화** | 3상태 FSM 명시 | 암묵적 view 상태 | Codex가 명시 안 함 |
| **망각 이중 경로** | decay(비가역) + suppression(가역, PFC억제) 분리 필수 | 단일 GC 예산으로 처리 | 미결: 단일 vs 이중 |

---

## 3. Recommendation (권고)

### 핵심 아키텍처 결정

**두 입장은 대립이 아닌 레이어 분리로 통합 가능:**

```
[원본 로그]  append-only Event Store
     ↓
[View 레이어] epoch-based salience/utility 재평가 (Codex)
     ↓
[상태기계]   CONSOLIDATED → LABILE → RECONSOLIDATED/EXTINCT (Claude)
     ↓
[GC 예산]    budgeted maintenance tick에서 EXTINCT 제거
```

### 망각 이중 경로 채택 권고

Claude의 이중 경로가 위기 시나리오(트라우마, 세뇌)를 더 정밀하게 모델링:

| 경로 | 메커니즘 | 가역성 | PersonaBrain 매핑 |
|------|----------|--------|-------------------|
| **Intrinsic decay** | 시간 + 낮은 salience → 자연 소멸 | 비가역 | I(GABA)↑ + C(ACh)↓ (수면) |
| **Motivated suppression** | PFC top-down 억제 | 가역 | H1(트라우마 고착) + L4(PFC Layer) |

### Salience 계산식 (초안)

```
salience(m, t) = α·E(m) + β·R(m,t) + γ·U(m,t)

E = 정서강도  [A(NE) × 감정클러스터 최대값]
R = 인출빈도  [최근 N틱 내 활성화 횟수]
U = 미래유용성 [L5 목표 벡터와의 코사인 유사도]
α+β+γ = 1, 초기값: α=0.5, β=0.3, γ=0.2
```

---

## 4. Open Questions (미결 과제)

| 질문 | 영향도 | 비고 |
|------|--------|------|
| "자발적 재활성화"의 연산 정의 — 맥락 벡터 × 기억 벡터 → 활성 임계값 계산식 | ★★★★★ | 틱 파이프라인 핵심 |
| LABILE 윈도 지속시간과 GC epoch 빈도의 동기화 (수면 사이클 단위?) | ★★★★ | 수면 틱 설계 시 결정 |
| U(미래유용성)의 prospective coding — 목표 미존재 시 fallback 경로 | ★★★★ | L5 미설계 상태에서 임시 처리 방법 |
| Suppression 상태의 append-only 로그 표현 방식 (`{state: "suppressed", by: "PFC"}`) | ★★★ | 스키마 설계 시 결정 |
| 거짓 기억(pattern completion) 생성 비율 제어 — 인간 수준 vs 억제 | ★★★ | 위기 시나리오 설계 연동 |
| Gemini 부재로 3자 신경과학 문헌 검증 미완 (Nader 2000, Anderson think/no-think) | ★★ | 다음 토론에서 재호출 |

---

## 5. Actionable Tasks

- `/sub PersonaBrain Charter L3d(에피소드 기억) 문서 작성: 생애주기(인코딩→저장→인출→재통합→망각), 3상태 FSM(CONSOLIDATED/LABILE/EXTINCT), salience 3차원 벡터 계산식, append-only + maintenance 분리 구조, 12클러스터 역할 매핑(A/B/I/T/F/L), 수면 틱 파이프라인 포함`

- `/sub 망각 이중 경로(intrinsic decay vs. motivated suppression) 설계: PFC top-down 억제의 Layer 위치, 트라우마 고착(H1) 해제 메커니즘, suppression 상태의 데이터 스키마 정의`

- `/sub 위기 시나리오 6종 상세화: 기억 조작/집단 기억/과부하/상실/거짓 기억 재판/flashbulb memory — PersonaBrain SNN에서 각 시나리오의 발생 경로 + 해제 조건 명시`

- `/sub salience 계산식 검증: E(NE×감정)/R(인출빈도)/U(L5 코사인 유사도) 초기 가중치 α=0.5/β=0.3/γ=0.2의 시뮬레이션 케이스 테스트 (flashbulb memory, 중립 사건, 트라우마 3케이스)`

- `/submix 자발적 재활성화 연산 정의 토론: 맥락 벡터 × 기억 벡터 → 활성 임계값 계산식 설계 (Claude + Codex, Gemini 재호출 포함), Nader 2000 reconsolidation 문헌 검증`