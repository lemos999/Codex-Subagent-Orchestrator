# loom 프로젝트 방향성 — 작업자 브리핑

> 모든 Codex/외부 에이전트가 본 프로젝트 작업을 시작하기 전 1회 정독.
> 작업 중 의사결정이 모호할 때 **본 문서의 원칙으로 역산**한다.
> (개정 2026-04-29)

---

## 1. 3계층 목표 (모든 결정의 출발점)

### 1.1 궁극 목표
**자율 사회 시뮬 + SNN 창발 + PersonaBrain 논문 출판** — 페르소나가 살아가는 과정에서 **국가가 자연 탄생**한다. Top-down으로 "여기 국가 있음" 선언하지 않는다. **삶 → 유대 → 갈등 → 주권 선언**이라는 인과 사슬로만 국가가 생겨나야 한다.

### 1.2 Phase 17 목적
자연 탄생의 4단계 인과 사슬 구축. 각 단계는 **다음 단계의 재료**를 만든다.

| Φ | 단계 | 핵심 질문 | 산출물 |
|---|------|-----------|--------|
| Φ-1 | Land | 페르소나가 '어디에' 있는가 | 공간 + territory |
| Φ-2 | Faction | 페르소나가 '누구와' 뜻이 같은가 | charter 기반 정치 결사 |
| **Φ-3** | **Struggle** | 다른 누구와 충돌/동맹하는가 | grievance·봉기·분파 동역학 ← **현재 단계** |
| Φ-4 | Nation | 충분히 큰 결집이 주권을 선언하는가 | 자연 탄생 국가 |

### 1.3 현재 위치 (2026-04-29)
- Φ-1 Land ✅ + Φ-2 Faction ✅ + Φ-3 Struggle 진행 중
- Phase 14 grievance propagation 구현 완료 (cross-territory lord_id 전파)
- **Case C 진단 단계** — Φ-3 acceptance #2 (`grievance_pairs_end ≥ 1`)가 자연 측정에서 0/0/0 FAIL. 후기 active_factions=1 collapse가 cross-faction pair를 소멸시킴.
- 측정 출처: [data/phase17_probe_phi3-phase14-resonance/SUMMARY.md](data/phase17_probe_phi3-phase14-resonance/SUMMARY.md), [PHASE-17-STRUGGLE-CLOSURE-REPORT.md §2](PHASE-17-STRUGGLE-CLOSURE-REPORT.md)

---

## 2. 절대 원칙 (5조항)

### 2.1 SNN 창발 최우선 (`feedback_snn_emergence_first.md`)

본 프로젝트의 근본 철학은 **"뉴런·시냅스·STDP에 의한 자연스러운 창발"**. 규칙 기반은 창발이 실패할 때만 보완적 가이드.

- 새 기능 설계 시 **"이것이 SNN에서 나올 수 있는가?"** 먼저 질문
- 가능하면: SNN 신호 → 행동
- 불가능하면: SNN 신호를 읽되 규칙으로 보완 (하이브리드)
- 순수 규칙은 최후의 수단 (인프라/물리 법칙 수준만)
- **계층별 정합성**:
  - Layer 2~4 (뇌/감정/행동): 순수 창발
  - Layer 5~6 (사회/경제): SNN 연결 필수
  - Layer 7 (통치): 창발적 욕구 위에 제도적 가이드

### 2.2 거짓 PASS 절대 금지 (`feedback_root_cause_first.md`)

acceptance 기준을 PASS시키기 위해 **역공학 조건을 삽입하지 않는다.** Phase 17 hotfix v1에서 이미 5건의 거짓 보정이 제거됨:
- `collapse_branch_pressure`
- `follower_reserve` sticky
- `resonance_carrier_sticky`
- artificial grievance pair injection
- sticky lord_id guard

**거짓 보정 안티패턴 (이 형태가 보이면 거부)**:
1. acceptance 미달 상태 식별 → (2) 그 상태를 막는 조건 삽입 → (3) 자연 현상처럼 포장

가장 최근 사례: Phase 14B-A axis A (affiliation drift dampen + SNN anger gate). 3엔진 cross-check (2026-04-28)에서 거짓 보정 5건과 **구조 동형**으로 식별되어 기각됨.

### 2.3 근본 원인 우선

문제 발견 시 즉시 해결하지 말고 **"왜?" 연쇄**를 먼저:
1. 이 문제는 왜 생겼는가?
2. 그 원인은 왜 생겼는가?
3. (반복) 더 이상 "왜"가 없을 때까지

근본 원인이 나오면 거기서부터 설계. 표면 수정은 또 다른 구멍을 낳는다.

**예시 (실제 사례)**:
- 증상: "active_factions=1로 수렴, grievance_pairs=0"
- 표면 패치 시도(거부됨): affiliation drift dampen으로 분리 강제
- 근본 추적: collapse 시점 → respawn 미작동 → free_residents=0 → 모두 dominant 흡수 → 흡수 자체가 자연인지 검증 필요
- **결론**: 진단 단계로 회귀하여 데이터로 root cause 확정 후 자연 mechanism 설계

### 2.4 무파괴 보장

Phase 11~16 경제 시스템 + Phase 14 propagation + Stage 1~6 anti-collapse 모두 머지됨. 다음을 **무수정**:

- Phase 11 경제 시스템 (`territoryRef` 앵커 기반)
- SSoT 단일 경로 (`_change_persona_faction(..., source=...)` — 4종 source 고정)
- Phase 14 grievance propagation (`_propagate_grievance_lord_id_cross_territory`)
- Stage 3 anti-collapse 상수 (`MINORITY_PERSISTENCE_BOOST=0.15`, `FOUNDER_RESPAWN_EVERY=480`, `FOUNDER_RESPAWN_TARGET_ACTIVE=2`)
- 결정성 RNG 격리 (`_derive_rng(...)` — 신규 RNG 도입 금지)
- **재현성 표준**: `seed=42` 재현 가능. 진단 측정은 `seeds 7, 13, 42 × 5000 tick` 표준.

**상수 변경은 진단 보고서가 데이터로 정당화한 경우에만 허용** (cross-check 경유).

### 2.5 외부 cross-check 의무

acceptance를 풀려고 mechanism을 추가하기 전 **3엔진 cross-check 통과**를 거친다.

- `/discuss --quick` (Claude + Codex + Gemini) 1라운드
- 거짓 PASS 패턴 잠복 검사
- SNN 창발 정합성 검사
- 인과 사슬 자연성 검사

진단 단계는 cross-check 불필요 (데이터 수집만). 패치 단계는 필수.

**거짓 PASS 검출 이중 안전장치**: 본 문서가 Codex 작업자에 전달되어도 거짓 PASS 회피 책임은 양측 모두에 있다.
- (a) Codex 측: §2.2 안티패턴(거짓 보정 5건 동형) 자체 검증을 수행. 의심 시 commit 보류.
- (b) Supervisor 측: 본 문서를 사전 주입하지 않은 별도 cross-check(원 요구사항만 전달)를 병행하여 "본 문서가 만든 공유 바닥 위 변주" 위험을 차단.

본 문서가 명확히 명시한 방향성·목적·acceptance·5조항을 Codex가 따르는 것은 OK. 그러나 **본 문서가 cross-check의 답을 미리 정해 주는 도구로 변질되면 안 된다.**

---

## 3. 작업 원칙 (실행 디테일)

### 3.1 모든 작업은 3계층 명시로 시작

매 작업의 첫 출력 블록에:
```
- 궁극 목적: <어떻게 기여하는가>
- Phase 목적: <어느 Φ 단계의 어떤 재료를 만드는가>
- 현재 작업의 고유 역할: <이번 spec/구현이 하는 일>
```

### 3.2 step 분해 시 인계 계약 검증

각 Step이 **다음 Phase의 재료로 기능하는지** 명시. 예:
- Φ-3 Struggle의 `grievance_pairs_end` 측정값 → Φ-4 Nation의 "주권 선언 트리거" 재료
- Φ-3 봉기에서 발생한 `branch faction` → Φ-4의 "결집 후보"

### 3.3 spec 작성 → 구현 → 검증 사이클

**역할 분담** (사용자 확정 워크플로우 2026-04-16):
- **Claude**: 설계, 아키텍처, spec 작성, 구현 리뷰
- **Codex (GPT)**: 지시서(spec) 수령 → 플랜 모드로 구현 계획 → 코딩 → 검증 → 리뷰 요청서 작성
- **Gemini**: 토론 cross-check 보조 (3엔진 토론 시)

본 문서를 받은 Codex 에이전트는 **spec 재설계자가 아니라 구현자**다. acceptance·근본 원칙은 해석 대상이 아니라 준수 대상이다.

**재해석/재설계가 필요하다고 판단되는 경우** Codex는 **직접 결정하지 않는다**. 대신 보고서·주석에 다음 형식으로 사용자·Claude에게 문의 요청을 남긴다:
```
[REQUEST_REVIEW]
재설계 사유: <왜 본 spec/원칙 그대로 진행 불가한지 근거>
근거: <코드 인용 / 측정 데이터 / 인과 추적>
대안 후보: <옵션 A / 옵션 B>
판단 요청: 사용자 + Claude
```

```
/spec → /spec-review → 수정 → commit → 외부 엔진 전달 → 검증 → 보고
                  ↑
        CRITICAL 발견 시 재작성
```

진단 결과는 별도 보고서 (예: `PHASE-17-CASE-C-DIAGNOSIS-REPORT.md`)로 분리.

### 3.4 검증 의무

완료 보고 전 **반드시**:
1. `py -m py_compile <변경 파일>` (문법)
2. AST 본문 길이 검증 (logic 변경 vs 텔레메트리 추가 분리)
3. 기존 테스트 모두 PASS (회귀 보호) — `test_phase17_*.py`, `test_phase14b_*.py`
4. 진단/실험 측정 (3 seed × 5000 tick)

검증 실패 시 재작업. 결과를 임의 해석으로 통과시키지 않는다.

**SSoT 정합성 4중 체크** (새 mechanism/상수 추가 시 필수):
1. **spec** 본문에 mechanism 정의 + line 인용
2. **`ontology/layers.py`** (또는 config) 상수 추가
3. **acceptance 테스트**(`test_phase17_*.py` 등) 갱신
4. **closure/diagnosis 보고서** 결과 표 반영

4종 중 하나라도 빠지면 watchdog이 검출 못한 채 동기화가 깨진다 (Stage 6 lineage affinity 같은 사례에서 노출 가능했던 패턴).

### 3.5 결과 해석은 "This tells us:"로

`acceptance #2 = 0/0/0 FAIL`은 끝이 아님. 다음 형식으로 해석 동반:
> This tells us: cross-faction grievance pair는 active_factions ≥ 2를 전제. collapse가 차단하면 후속 모든 mechanism이 실효. **다음 탐색 차원: collapse 진행 코드 경로 직접 추적.**

기술 용어 "FAIL"(테스트 상태, 로그 레벨 등)은 정상 사용.

### 3.6 설계 순서: 넓이 우선 (Breadth First)

새 Phase/새 가지 진입 시 **모든 가지의 Charter(뼈대)를 먼저** 잡는다. 한 가지를 깊이 파기 전에:

1. 모든 가지 Charter 수준 작성
2. 전체 정합성 검증
3. 상세 설계
4. 구조화 아키텍처

Phase 17이 `Φ-1 Land Charter → Φ-2 Faction Charter v2 → Φ-3 Struggle STUB`로 진행한 것이 본 원칙의 적용 사례. **Φ-4 Nation도 동일** — 깊이 우선으로 한 가지(예: 주권 선언 트리거 수식)만 먼저 파지 않는다.

---

## 4. 안티패턴 — 즉시 거부

| # | 안티패턴 | 신호 | 대응 |
|---|----------|------|------|
| 1 | acceptance 역공학 분기 | "X 미달 시 Y 조건 삽입" | 거부, 근본 추적 |
| 2 | 임계값 임의 도입 | "DAMPEN=0.6" 같은 마법 숫자 (자연 측정 회귀·실험 정당화 없이 도입) | 자연 측정에서 역산 정당화 요구 — 정당한 상수(예: `MINORITY_PERSISTENCE_BOOST=0.15`)는 closure 보고서에 데이터 근거 명시 필수 |
| 3 | SNN gate 정당화 부재 | 어떤 창발 관측에서도 도출 안 됨 | 거부 |
| 4 | mechanism 본문 silent 변경 | "텔레메트리만"이라며 logic 분기 추가 | AST 본문 길이 검증으로 차단 |
| 5 | 회귀 테스트 우회 | "이 테스트는 더 이상 의미 없음" | 회귀 PASS 유지 의무 |
| 6 | "불가능" 단정 | "이 접근으로는 안 됩니다" | "아직 미해결" + 차원 전환 제안 |
| 7 | 신규 source/RNG 추가 | `FactionChangeSource` 5번째, 신규 `_derive_rng` | SSoT 위반, 거부 |

---

## 5. 현재 작업 (Codex 진단 단계)

### 5.1 입력
- `PHASE-17-CASE-C-COLLAPSE-DIAGNOSIS-SPEC.md` (자기완결 지시서)
- `data/phase17_probe_phi3-phase14-resonance/SUMMARY.md` (선행 측정 — 0/0/0 FAIL)
- 본 문서 (방향성)

### 5.2 산출물
1. `core/multi_tick_engine.py`: 텔레메트리 5종 (mechanism 무수정)
2. `observe_phase17_emergence.py`: Case C Diagnosis 섹션
3. `data/phase17_probe_phi3-case-c-diagnosis/`: 측정 결과 (3 seed × 5000 tick)
4. `PHASE-17-CASE-C-DIAGNOSIS-REPORT.md`: 6 가설 (H1, H2a, H2b, H2c, H3, H4) PASS/FAIL + root cause + 패치 후보 P1~P4 권고
5. `Tools/scripts/verify_phase17_case_c_diagnosis.py`: AST 본문 길이 검증

### 5.3 절대 금지
- mechanism 본문 logic 변경 (텔레메트리 append만)
- 상수 변경
- acceptance 기준 손대기
- 인라인 `sorted(self.personas)[0]` 호출 (외부 1회 계산 필수)

### 5.4 다음 단계 (진단 후)
1. 진단 보고서 → root cause 확정
2. 패치 spec 작성 (P1~P4 중 권고 방향)
3. `/discuss --quick` cross-check (Claude + Codex + Gemini)
4. 패치 구현 → Φ-3 closure 2차
5. Φ-4 Nation Charter 작성

---

## 6. 의문 발생 시 의사결정 흐름

```
의문 발생
   ↓
1) 본 문서의 3계층 목표에서 역산 — 이 결정이 국가 자연 탄생에 어떻게 기여하는가?
   ↓
2) 5조항 원칙 점검 — SNN 창발? 거짓 PASS 아님? 근본 원인? 무파괴? cross-check?
   ↓
3) 안티패턴 7종 검사 — 하나라도 매칭되면 즉시 거부
   ↓
4) 모호하면 작업 중단하고 사용자에게 명시 확인
```

**침묵 금지**: 결정이 모호한 상태로 코드를 진행시키지 않는다. 보고서·주석에 "Why:" 명시.

---

## 7. 참조 문서 (현재 시점)

- 본 문서: `Projects/personas/loom/LOOM-DIRECTION.md`
- 진단 spec: `Projects/personas/loom/PHASE-17-CASE-C-COLLAPSE-DIAGNOSIS-SPEC.md`
- 14B-A 기각 evidence: `subagent-runs/discuss/phase14b-a-cross-check-2026-04-28-quick/`
- Φ-3 hotfix v1 closure: `Projects/personas/loom/PHASE-17-STRUGGLE-CLOSURE-REPORT.md`
- Φ-2 Charter v2: `Projects/personas/loom/PHASE-17-FACTION-CHARTER.md`
- Φ-3 stub: `Projects/personas/loom/PHASE-17-STRUGGLE-CHARTER-STUB.md`
- 선행 측정: `Projects/personas/loom/data/phase17_probe_phi3-phase14-resonance/SUMMARY.md`
- Phase 14 spec: `Projects/personas/loom/PHASE-14-GRIEVANCE-RESONANCE-SPEC.md`
- (참고) 작업 에이전트 운영 시스템: `Projects/personas/registry.json` — supervisor 메타, 외부 작업자 무관

---

**핵심 한 줄**: 국가가 **자연 탄생**해야 한다. 우리가 국가를 만드는 게 아니라, 페르소나의 삶이 국가를 만들도록 설계한다. 그 외 모든 결정은 이 한 줄에서 역산한다.
