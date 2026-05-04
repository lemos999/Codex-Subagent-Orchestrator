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
- Stage 3 anti-collapse 상수 (`MINORITY_PERSISTENCE_BOOST=0.20` [Phase 17 Case-C v2 2026-04-30 데이터 정당화: closure-v2 §7], `FOUNDER_RESPAWN_EVERY=480`, `FOUNDER_RESPAWN_TARGET_ACTIVE=2`)
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

#### 3.3.1 spec 외부 자율 제안 처리 (Codex 코드 분석 능력 활용)

`§3.3 [REQUEST_REVIEW]`는 spec **본문**의 acceptance/원칙 해석이 모호할 때의 절차다. 이와 별개로 **spec 외부 (helper 코드 잠재 결함, stale 코드, 데이터 오염 위험 등)에서 Codex가 버그·개선을 발견하면** 다음 절차를 따른다.

본 절차는 `CLAUDE.md Rule 3 SENIOR DEV OVERRIDE` 디폴트("범위 밖 변경은 사전 승인")의 **예외** — Codex의 코드 분석 능력을 활용하여 진단 사이클을 단축하기 위함. (사용자 명시 정책 2026-05-03)

**자율 행동 허용**:
- spec 외부 결함은 **자율 정정 가능**. 자율 제거·수정 자체는 막지 않는다.
- 단 다음 절차 [필수]:
  1. **분리 커밋** (CLAUDE.md Rule 3 분리 원칙) — spec 메인 작업과 다른 커밋으로.
  2. **변경 사유 명시 보고** — 4항목:
     - 발견 위치 (파일:줄)
     - 문제 (코드 인용 + 영향 분석)
     - 변경 (적용된 코드 인용)
     - 부합 근거 (LOOM-DIRECTION §3.7 / §2.2 / Φ-4 STUB OQ 7-a~e / 안전 전제 / 데이터 오염 방지 등 인용)
  3. **사후 인정 절차** — 사용자가 보고 받은 후 부합 판정 시 수용, 미부합 시 revert.

**자율 행동 절대 금지** (위 허용에서 명시 제외):
- spec [금지] 항목(안전 전제 5종, BOOST, mechanism 메서드, `brain/**`, D10 SNN API 등)의 자율 변경.
- "조용히" 자율 변경 후 메인 커밋에 섞기 — 사용자 검토 기회를 박탈하면 정책 위반.

**판정 기준** (사용자 사후 인정 시):
1. 변경 사유 분석 — 코드 인용 + Codex 정당화 확인.
2. 프로젝트 3계층 목표 부합성 (§1) — 자율 사회 시뮬 + SNN 창발 + 논문 출판.
3. 방향성 부합성 — 데이터 정당화 사슬 6단 (§3.7), 거짓 PASS 절대 금지 (§2.2), 무파괴 9 + 안전 전제 5종 (§2.4), axis C 안티패턴 가드레일 (Φ-4 STUB OQ 7-a~e).
4. 부합 시 수용·회고 인정. 미부합 시 명시 거부 + revert.

**적용 사례** (2026-05-03 사용자 결정 — Phase 17 Case C v2):
- spec helper 자율 정정 (set comprehension 단일 누적 버그 → `territory.factionRef` 변경) — 버그 인지·정정 가치 인정. 정의가 PROBE와 불일치였으나 자율 행동이 진단 사이클을 1회 단축. 정의 정정은 v3에서 PROBE 기반으로 재정정.
- stale 코드 5종 자율 제거 (`FOUNDER_LOYALTY_BONUS` 등) — 데이터 오염 방지 정당화 수용.

**위치 정합성**: 본 §3.3.1은 §3.3의 보완 — 워크플로우는 "Claude=설계/리뷰, Codex=코딩"이지만 Codex가 설계 결함을 잡으면 그 신호를 Claude가 흡수해 다음 spec에 반영. 일방향(Claude→Codex)이 아닌 상호 검증.

**자주 발생하는 오역 (재발 방지)**:
1. **디폴트 회귀** — 본 §3.3.1은 CLAUDE.md Rule 3 디폴트의 **예외**. 정책 적용 시 "이 정책이 어떤 디폴트를 어떻게 뒤집는가"를 먼저 점검해야 디폴트(사전 승인)로 무의식 회귀하지 않음.
2. **사후→사전 시점 오역** — 위 4단 판정 기준은 자율 행동이 **일어난 후** 사용자가 판단하는 절차. "절차를 거치려면 자율 행동을 사전 차단해야 한다"로 추론하면 정책 본의 뒤집힘.
3. **이분법 사고 (CLAUDE.md Rule 15)** — "허용 vs 금지"가 아닌 "허용 + 분리 커밋 + 사후 판정"의 3축 균형. 두 축 중 하나로 압축 금지.

**영역별 자율 매트릭스** (디폴트 정책 — 사용자 명시 변경 없는 한 본 매트릭스 적용):

| 영역 | 자율 폭 | 사유 |
|------|---------|------|
| 진단 helper (`_record_*`, telemetry 함수) | 결함 **자율 정정** | spec 작성자(Claude) 결함 보완 — Claude는 자기 결함 잡기 어려움 |
| 테스트 계약 (`test_*.py`) — spec [필수] 회귀 게이트인 경우 | **자율 X** (사용자 보고만) | spec 본문 일부, 자율 변경 시 spec 위반 |
| 테스트 계약 (`test_*.py`) — spec 외부 인 경우 | 결함 **자율 정정** | mechanism 외 영역 |
| 분석 스크립트 (`Tools/scripts/*`, `analyze_*.py`) | 결함 **자율 정정** | 측정 도구이지 mechanism 아님 |
| stale 코드 (이전 실험 잔재 상수/함수, 데이터 오염 위험) | **자율 제거** | v2 `FOUNDER_LOYALTY_BONUS` 등 5종 자율 제거 사례 |
| 다른 spec 사이 정합성 결함 (cross-spec) | **자율 X** (사용자 보고만) | 단일 spec 위임 범위 초과 — Claude의 다음 spec 작성에 통합 흡수 |
| **mechanism 본문** (`core/multi_tick_engine.py` 메서드 logic) | **자율 절대 X** | 거짓 PASS 위험. 본 영역 자율 = §3.3.1 절대 금지 |
| **안전 전제 5종 + `BOOST=0.20`** | **자율 절대 X** | Φ-3/4 charter 핵심. 영향 평가는 Claude 책임 |
| **acceptance 정의** | **자율 절대 X** | top-down 위험. axis A 기각 사유 동형 |
| **`brain/**`, D10 SNN API** | **자율 절대 X** | SNN 무수정 절대 원칙 (§2.4) |

**5항목 보고로 확장** (피드백 루프 강화):

자율 정정 영역에서 행동 시 위 4항목(발견 위치, 문제, 변경, 부합 근거) + 다음 **5번째 항목 [필수]**:

5. **spec rev 갱신 권고** — 자율 발견을 다음 spec 작성에 흡수해야 할 항목. 형식:
   - 현재 spec rev 결함: `<Claude가 spec rev N에 빠뜨린 항목 1줄>`
   - 다음 spec rev 갱신 권고: `<spec rev N+1에 추가할 명문화 항목 1줄>`

본 항목은 Codex 자율 발견을 Claude의 다음 spec rev에 **강제 흡수**시키는 피드백 루프. 5항목 없이 자율 행동 인정 시 Claude가 같은 결함을 다음 spec에서 또 빠뜨릴 위험. (Codex는 메모리가 없어 매 위임마다 spec에서 LOOM 방향성을 새로 흡수하므로, 학습 영속성은 Claude의 spec rev 갱신을 통해서만 확보된다.)

**적용 사례 (Phase 17 v3 RNG, 2026-05-03)**:
- Codex가 `test_economy_balance.py`의 stale `np.random.random` monkeypatch 발견 → 매트릭스 "테스트 계약 (spec [필수] 회귀 게이트)" 행에 따라 자율 수정 X, 사용자 보고 선택 → §3.3.1 정확히 준수.
- Claude는 v3 spec 작성 시 회귀 게이트 사전 검증 누락 책임 인정 후 [`FIX-PHASE14-EXODUS-RNG-TEST-CONTRACT.md`](FIX-PHASE14-EXODUS-RNG-TEST-CONTRACT.md) hotfix spec으로 격리 정정.
- 5항목 보고 사례: 본 hotfix 회고 §"다음 spec 학습 반영"에서 "회귀 게이트 사전 점검 3종" 항목으로 명문화 — 다음 spec rev 작성 시 흡수 의무.

#### 3.3.2 코어 접근 사전 승인 게이트 (사용자 명시 정책 2026-05-03)

§3.3.1 매트릭스의 **"자율 절대 X" 4행**(mechanism 본문 / 안전 전제 5종 + BOOST / acceptance 정의 / `brain/**`+D10 SNN API)을 **코어 영역**으로 통칭한다. 코어 영역에 접근하는 spec은 **Codex 위임 전에 사용자 사전 승인 [필수]**.

**적용 흐름**:

```
Claude /spec 작성
  ↓
spec [필수] 또는 [선택] 항목이 코어 영역 변경 포함?
  ├─ NO  → /spec-review → Codex 위임 (§3.3.1 매트릭스 적용, Codex 자율성 존중)
  └─ YES → 사용자 사전 승인 게이트
              ↓
            사용자 승인 → /spec-review → Codex 위임 (코어 영역도 §3.3.1 매트릭스 적용)
            사용자 거부 → spec 재설계 (코어 회피 경로 모색) 또는 작업 보류
```

**왜 필요한가**:
- §3.3.1 자율 매트릭스는 **위임 후 Codex 행동 범위**를 정의 — Codex 자율성을 존중하면서 코어 영역만 보호.
- 그러나 **spec 자체가 코어 영역 변경을 [필수]로 지정**할 경우, 매트릭스의 "자율 절대 X" 보호가 사후 안전망일 뿐 사전 게이트가 부재.
- 본 §3.3.2 게이트는 **spec 단계**에서 코어 접근 의도를 사용자에게 사전 통지하여, 매트릭스의 "자율 절대 X" 영역이 spec 본문으로 우회되지 않도록 보장.

**코어 영역 판정 기준** (spec 작성 시 Claude 자체 점검):

| 영역 | 코어 판정 | 게이트 적용 |
|------|:---:|:---:|
| `_compute_affiliation_tick`, `_propagate_grievance_lord_id_cross_territory`, uprising/respawn/founder/exodus mechanism logic | **YES** | 사전 승인 필수 |
| `ontology/layers.py` 안전 전제 5종 (HYSTERESIS, FOUNDER_RESPAWN_EVERY, TARGET_ACTIVE, COMMIT_EVERY, MAX_MEMBERS) + BOOST=0.20 | **YES** | 사전 승인 필수 |
| `test_phase17_acceptance.py` 등 acceptance 정의 자체 | **YES** | 사전 승인 필수 |
| `brain/**`, D10 SNN 7종 read-only API | **YES** | 사전 승인 필수 |
| 진단 helper (`_record_*`, telemetry) — 코어 호출하지만 logic 무수정 | NO | 게이트 불요 (§3.3.1 매트릭스 1행) |
| `Tools/scripts/*`, `analyze_*.py` 분석 스크립트 | NO | 게이트 불요 |
| `event_log` 누적·읽기 (mechanism 부수 효과 없음) | NO | 게이트 불요 |

**모호 시 디폴트**: 코어 판정 모호하면 **코어로 간주하고 게이트 적용**. 사후 게이트 우회 발견 시 revert.

**spec 작성 시 [필수] 표기**:

코어 영역 변경 spec은 spec 본문에 다음 헤더 [필수]:

```markdown
## 코어 접근 사전 승인 (LOOM-DIRECTION §3.3.2)

- 코어 영역: <영역명 — mechanism 본문 / 안전 전제 / acceptance / brain·SNN>
- 변경 범위: <한 줄 요약>
- 정당화: <왜 코어 변경이 [필수]인지, axis C 가드레일 OQ 7-a~e 인용>
- 대안 검토: <코어 회피 경로 검토 결과 — 가능 / 불가능>
- 사용자 사전 승인 요청 일자: <YYYY-MM-DD>
- 사용자 결정: <승인 / 거부 / 재설계 요구> (사용자 응답 후 기재)
```

**Codex에게 코어 접근 spec 위임 시 추가 [필수]**:
- 위임 프롬프트에 "본 spec은 코어 접근 사전 승인 완료 (§3.3.2 헤더 명시 일자: YYYY-MM-DD)" 명시.
- Codex는 spec 본문 §3.3.2 헤더가 없으면 **코어 변경 거부** 후 사용자 보고 (§3.3.1 매트릭스 "자율 절대 X" 4행 적용).

**적용 사례 (예시 — 향후)**:
- spec rev.4 H5 dead code 정리는 telemetry helper 변경 → 코어 아님 → 게이트 불요.
- Φ-4 Nation Charter STUB은 charter 본문 작성이지 코어 logic 변경 아님 → 게이트 불요. 단 charter 결과 acceptance 추가/변경이 발생하면 그 시점에 §3.3.2 게이트 적용.
- 만약 Φ-4 진행 중 mechanism logic 변경(예: faction lifecycle hook)이 [필수]로 도출되면 → 사전 승인 게이트 적용.

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

### 3.7 데이터 정당화 사슬 표준 (안티패턴 #3 회피용)

신규 SNN gate / 결합점 / 임계값 도입 시 **6단 사슬을 모두 거친 데이터 정당화**가 있어야 한다. 한 단이라도 비면 안티패턴 #3 (SNN gate 정당화 부재)으로 즉시 거부.

| 단 | 산출물 | 검증 질문 |
|----|--------|-----------|
| 1. **자연 측정** | 본문 mechanism 무수정으로 telemetry append 후 3 seed × 5000 tick | 측정값이 mechanism 변경 없이 자연 발생했는가? |
| 2. **분포 분석** | n, avg, median, P25/P50/P75 전부 산출 | 두 그룹의 n>=5와 diff_sum>임계 충족? |
| 3. **결합점 후보** | 어떤 SNN 출력이 어떤 mechanism 변수와 결합 가능한지 명시 | 결합점이 자연 측정 PASS 가설에서 직접 유도되었는가? |
| 4. **임계 분위수** | P50/P67/P75 등 후보 + 각 후보의 PASS 비율 시뮬 | 마법 숫자가 아닌 분위수 기반인가? |
| 5. **3엔진 cross-check** | `/discuss --quick`으로 Claude + Codex + Gemini 검증 | 단일 엔진 편향이 아닌가? |
| 6. **closure 보고서** | 6단 사슬 + 산출 데이터 + verdict matrix | 다음 Phase가 본 사슬을 추적 가능한가? |

**적용 사례**: `PHASE-14B-SNN-OUTPUT-DIAGNOSIS-REPORT.md` — G1(uprising leader gate) 자연 측정 → pass_avg_anger 0.71 vs fail 0.50 (diff 0.21, 3 seed × n=44/62/99) → 결합점 후보 1순위 anger → 임계 분위수 P50≈0.55 / P67≈0.65 / P75≈0.70 도출 → 3엔진 cross-check 단계 진입 가능 상태.

**금지**: 1~6 중 하나라도 빠진 채 SNN gate 추가. 특히 1단(자연 측정)을 건너뛰고 추정값으로 임계 도입 = 즉시 거부.

---

## 4. 안티패턴 — 즉시 거부

| # | 안티패턴 | 신호 | 대응 |
|---|----------|------|------|
| 1 | acceptance 역공학 분기 | "X 미달 시 Y 조건 삽입" | 거부, 근본 추적 |
| 2 | 임계값 임의 도입 | "DAMPEN=0.6" 같은 마법 숫자 (자연 측정 회귀·실험 정당화 없이 도입) | 자연 측정에서 역산 정당화 요구 — 정당한 상수(예: `MINORITY_PERSISTENCE_BOOST=0.20`, closure-v2 데이터 사슬 §7)는 closure 보고서에 데이터 근거 명시 필수 |
| 3 | SNN gate 정당화 부재 | 어떤 창발 관측에서도 도출 안 됨 | §3.7 데이터 정당화 사슬 6단 (자연 측정 → 분포 분석 → 결합점 후보 → 임계 분위수 → 3엔진 cross-check → closure 보고서) 거친 데이터만 인정. 한 단이라도 비면 거부 |
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
- Phase 14B-d1 진단 spec: `Projects/personas/loom/PHASE-14B-SNN-OUTPUT-DIAGNOSIS-SPEC.md`
- Phase 14B-d1 진단 보고서: `Projects/personas/loom/PHASE-14B-SNN-OUTPUT-DIAGNOSIS-REPORT.md` (§3.7 사례)
- Phase 14B-d1 evidence: `subagent-runs/claude/loom-phase14b-snn-output-diagnosis-spec-2026-05-02/`
- Φ-3 hotfix v1 closure: `Projects/personas/loom/PHASE-17-STRUGGLE-CLOSURE-REPORT.md`
- Φ-2 Charter v2: `Projects/personas/loom/PHASE-17-FACTION-CHARTER.md`
- Φ-3 stub: `Projects/personas/loom/PHASE-17-STRUGGLE-CHARTER-STUB.md`
- 선행 측정: `Projects/personas/loom/data/phase17_probe_phi3-phase14-resonance/SUMMARY.md`
- Phase 14 spec: `Projects/personas/loom/PHASE-14-GRIEVANCE-RESONANCE-SPEC.md`
- (참고) 작업 에이전트 운영 시스템: `Projects/personas/registry.json` — supervisor 메타, 외부 작업자 무관

---

**핵심 한 줄**: 국가가 **자연 탄생**해야 한다. 우리가 국가를 만드는 게 아니라, 페르소나의 삶이 국가를 만들도록 설계한다. 그 외 모든 결정은 이 한 줄에서 역산한다.
