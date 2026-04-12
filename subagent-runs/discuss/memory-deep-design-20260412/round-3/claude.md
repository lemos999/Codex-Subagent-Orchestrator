[PARTIAL]

**Reasoning**: append-only + maintenance tick 분리는 신경과학적으로 건전하다. 수면 중 SWR(sharp-wave ripple)이 정확히 이 "오프라인 배치 처리"다. 그러나 **재통합의 핵심 메커니즘이 여전히 추상적**이다. Nader(2000)가 보인 것은 재활성화 시 기억이 단백질 합성 의존 상태로 돌아간다는 것—이것은 단순한 "유용성 재평가"가 아니라 **기억의 존재론적 상태 전환**(안정→불안정→재안정)이다. 현재 설계는 이 상태 전환을 값의 갱신으로 축소하고 있다.

**New insight — 재통합은 값 갱신이 아니라 상태 기계(state machine)다:**

기억 노드에 3상태가 필요하다: `CONSOLIDATED → LABILE → RECONSOLIDATED/EXTINCT`
- **CONSOLIDATED**: 안정 상태, 인출 가능하나 변경 불가
- **LABILE**: 재활성화 시 진입, 이 창(reconsolidation window) 안에서만 수정·강화·소거 가능
- **RECONSOLIDATED**: 창이 닫히면 새 맥락이 통합된 채 재안정화

이것이 중요한 이유: maintenance tick에서 모든 기억을 동등하게 재평가하면 **간섭(interference)**이 폭발한다. 실제 뇌는 **재활성화된 기억만** labile 상태로 전환한다. 따라서 tick에서 처리할 대상 선택 기준이 "salience 순위"가 아니라 **"현재 맥락과의 패턴 중첩도에 의한 자발적 재활성화 여부"**여야 한다.

**망각 이중경로에 대한 구체화:**
- **Intrinsic decay**: CONSOLIDATED 상태에서 인출 없이 시간 경과 → salience 감쇠 (수동적, RAC5/Rac1 기반 능동적 망각의 생물학적 대응)
- **Motivated suppression**: PFC→해마 top-down 억제, 기억은 존재하나 인출 차단 (Anderson의 think/no-think 패러다임) → I(GABA)의 진짜 역할은 이것

두 경로의 차이: decay는 **되돌릴 수 없고**, suppression은 **맥락 변화 시 해제 가능**하다. 트라우마 시나리오에서 suppression된 기억이 위기 맥락에서 갑자기 labile로 전환되는 것이 flashback의 메커니즘이다.

**Updated position**: 이전 라운드의 "미래유용성 소급 재평가"를 수정한다. 재통합은 값의 연속적 갱신이 아니라 **이산적 상태 전환**이며, 이 전환의 게이트가 설계의 핵심이다.

[POSITION: 재통합은 3상태 기계(consolidated→labile→reconsolidated)로 구현하고, maintenance tick의 대상 선택은 salience가 아닌 맥락-패턴 중첩에 의한 자발적 재활성화로 게이트해야 한다]