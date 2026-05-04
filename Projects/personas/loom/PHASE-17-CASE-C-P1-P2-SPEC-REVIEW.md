# PHASE-17-CASE-C-P1-P2-SPEC.md 자체 검토 리포트

**검토자**: Claude (자체 /spec-review)
**검토 일자**: 2026-04-30
**검토 대상**: `Projects/personas/loom/PHASE-17-CASE-C-P1-P2-SPEC.md`
**대조 코드**: `core/multi_tick_engine.py` (HEAD), `ontology/layers.py` (HEAD), `test_phase17_acceptance.py` (HEAD)

---

## 종합 판정

**조건부 승인** — CRITICAL 0건, MAJOR 4건, MINOR 4건, TRIVIA 2건.

MAJOR 4건은 구현 전 spec 자체에서 해소해야 하지만, mechanism 설계 자체는 정합. CRITICAL 부재로 사용자 보고는 가능.

---

## CRITICAL — 0건

(구현 자체 차단·자기모순·금지 위반은 발견되지 않음.)

---

## MAJOR — 4건 (구현 전 spec 보강 권고)

### M1. §B-2 인용 라인 부정확 — `_compute_affiliation_tick` 실제 위치 갱신 필요

- **위치**: `PHASE-17-CASE-C-P1-P2-SPEC.md` §B-2 "위치 식별 필요"
- **현재 인용**: "line 1207~1256 근방"
- **실제 코드 위치**: `multi_tick_engine.py:1217` 함수 시작, `:1274` 종료. line 1207~1216은 **앞 함수 `_spatial_proximity` 본문**.
- **문제**: 인용 라인이 잘못된 함수 영역을 가리킴 → 구현자가 다른 함수에 boost를 삽입할 위험.
- **권고 수정안**:
  - "위치 식별 필요" → "위치 확정: `_compute_affiliation_tick` (line 1217~1274), 특히 W_LINEAGE 가산 라인(line 1261~1269) 직후"
  - 의사코드의 `faction_territories(faction.id)` → `self._same_territory(persona, fid) > 0.5` (실제 함수 line 1124, kernel 내부 일관 사용)
  - 의사코드의 `faction.grace_until_tick` 접근 → kernel 함수에서 이미 `cand_faction = self.factions.get(fid)` 변수가 있으므로 `cand_faction.grace_until_tick` 재사용

### M2. test_phase17_acceptance.py 변경 명세 누락 — Section E 신설 필요

- **위치**: §변경 파일 표 마지막 행에만 명시, 구체 사양 §A·§B·§C·§D 어디에도 테스트 변경 명세 없음.
- **현재 명세**: "acceptance #2 자연 측정 검증(`grievance_pairs_end >= 1`)을 자연 통과로 변경. test_phi3_branch_lineage_chain의 skip-when-zero 패턴 제거 (R5 H2c 대응)"
- **실제 코드 확인** (test_phase17_acceptance.py:447~462):
  ```python
  def test_phi3_branch_lineage_chain():
      """분파 신규 faction의 founder_lineage가 부모 fid 포함."""
      for seed in [7, 13, 42]:
          engine = run_simulation(seed=seed, ticks=5000)
          branches = [e for e in engine.event_log if ... source == "uprising_branch"]
          for b in branches:        # ← branches 빈 list면 assertion 0건 = 자동 PASS
              ...
              assert parent_fid in new_faction.founder_lineage
  ```
- **문제**: skip-when-zero가 명시적 `if x == 0: skip`이 아니라 **빈 list iteration 자동 통과** 패턴. 단순 "skip 패턴 제거"로는 구현자가 무엇을 고쳐야 할지 불명확.
- **권고 수정안**: §E 신설.
  ```markdown
  ### Section E — 테스트 자연 측정 강화

  #### E-1. test_phi3_branch_lineage_chain 강화 (skip-when-zero 차단)
  현재 (line 447-462): branches=0일 때 inner for-loop 미실행 → 자동 PASS.
  변경: 3 seed 합계 branches >= 1 명시 assertion.

  ```python
  def test_phi3_branch_lineage_chain():
      total_branches = 0
      for seed in [7, 13, 42]:
          engine = run_simulation(seed=seed, ticks=5000)
          branches = [e for e in engine.event_log
                      if e["type"] == "faction_spawn"
                      and e.get("source") == "uprising_branch"]
          total_branches += len(branches)
          for b in branches:
              new_faction = engine.factions[b["fid"]]
              assert b["parent_fid"] in new_faction.founder_lineage, ...
      assert total_branches >= 1, (
          "3 seed 합계 uprising_branch 0건 = mechanism 단절 (skip-when-zero 차단)"
      )
  ```

  #### E-2. test_phi3_grievance_pairs_resonate (line 360-365) 무수정
  현재 이미 자연 측정 (>=1 assertion). 변경 불필요 — spec [필수] 3번 통과 후 자연 PASS.
  ```

### M3. P1+P2 → contact graph 회복 인과 사슬 증명 약함

- **위치**: §D "_uprising_trigger 및 _emit_uprising 무수정" 섹션, §"진단" 섹션.
- **문제**: 스펙은 "두 곳을 자연 보강하면 trigger·emit이 자동으로 통과"라고 단정하지만, 인과 메커니즘이 명시적으로 추적되지 않음. 구체적으로:
  - P1은 founder의 same-territory 거주자에게 가입 → minority faction의 멤버는 모두 같은 territory에 거주
  - 그러나 `factions_in_contact(radius=1)`는 **다른 territory**의 멤버 사이 거리 측정 → minority 멤버 모두 같은 territory에 있으면 contact 형성 못함
  - **즉 P1만으로는 contact graph 회복 인과 불충분**할 가능성. P2 grace boost가 dominant faction 멤버 일부를 minority territory로 이동시키는지(또는 그 반대)에 따라 contact 형성 여부가 결정됨.
- **권고 수정안**: §배경에 인과 사슬 명시.
  ```markdown
  ### 인과 사슬 (P1+P2 → contact graph 회복)

  1. 현재 (collapse): active=1, minority faction 0개. _pick_uprising_target의 contacts 빈 list → uprising_skip_no_contact 이벤트만 발생.
  2. P1 + P2 적용 후:
     - P1: respawn 시 founder + seed group 2-3명이 territory T₁의 신생 faction A에 동시 가입.
     - P2 grace 200틱: faction A 멤버는 dominant faction B(territory T₂ 기반)로의 affiliation 흡수에 자연 저항.
     - 동시에 territory T₁의 일부 거주자는 dominant faction B의 territory T₂ 멤버와 spatial radius=1 내에 있을 수 있음 (LandCell 인접).
     - 따라서 faction A(T₁) ↔ faction B(T₂) 사이 contact 형성 가능 → factions_in_contact ≥ 1.
  3. contact 형성 후: _uprising_trigger의 fid_in_contact 통과 → _emit_uprising → conflict source change → grievance pair 사슬.

  **잔존 위험**: territory 인접도(LandCell adjacency)가 낮으면 P1+P2만으로 contact 회복 불충분. 이 경우 한계 대응 프로토콜 §"Premise B" 발동 → P3·P4 차원 전환.
  ```

### M4. `score += GRACE_AFFILIATION_BOOST`의 임계 우회 효과 검증 부재

- **위치**: §B-1 "임계 정당화" + §B-2 의사코드.
- **현재 주장**: "boost는 임계 직접 우회가 아니라 같은 territory 거주자가 dominant faction과 신생 faction 사이 score 비교에서 신생 쪽이 인근 trust 정합 시 자연 우위에 서게 함."
- **문제**: 이 주장의 검증 메커니즘이 spec 본문에 부재.
  - `_commit_faction_tick` (line 1276~)에서 commit 결정은 score 기반. boost 0.12가 score 비교에 가산되면 **commit 결정 자체에 영향**을 미침.
  - 즉 "임계 우회 아니라 자연 score 가산"이 주장이 되려면, **임계 통과 자체가 boost 없이는 불가능했던 케이스가 boost로 통과**하는 시나리오에서 무엇을 자연 vs 우회로 볼지 구분 기준 필요.
  - 현재 grace 기간 200틱 내 boost가 적용되므로, 이 기간 내에서만 신생 faction이 commit 받을 가능성이 인공적으로 높아짐 → 이는 "면역"이 아니라 "선호 가산"에 가까움.
- **권고 수정안**: §B-1 임계 정당화 강화.
  ```markdown
  **임계 우회와 자연 가산의 경계**:
  - GRACE_AFFILIATION_BOOST는 다음 조건을 모두 만족해야 자연 가산:
    1. boost는 동일 territory 거주자에게만 적용 (territory 자연 인접 가산과 정합).
    2. boost는 grace_until_tick 종료 후 정확히 0으로 사라짐 (top-down 영구 보호 금지).
    3. boost 적용 후에도 W_TERRITORY_SAME(0.5) + W_TRUST*1.0 + W_PROXIMITY*1.0 (이론 최대 약 1.5) 대비 0.12는 8% 가산 = 절대 우위 형성 불가.
    4. boost는 score 사칙연산 중 가산만 사용 (score *= multiplier 형태 금지 — 임계 스케일 우회 효과).
  - 검증 hook: 결정성 검증 단계에서 grace 종료 직후 (created_tick + 200) snapshot에서 boost가 0임을 직접 확인.
  ```

---

## MINOR — 4건 (개선 권장)

### m1. `_pick_seed_group` 시그니처 `territory` 인자 미사용

- **위치**: §A-1 helper 시그니처 `territory: Territory`.
- **문제**: 함수 본문에서 `territory` 사용 없음 (호출자가 이미 territory별 candidates 필터링).
- **권고**: `territory: Territory` 인자 제거하거나, helper 내부에서 `persona.territory == territory.id` 검증 추가하여 인자 사용. 후자가 helper 단독 안전성 ↑.

### m2. `_get_community_members` 인용 라인 모호

- **위치**: §A-1 자연성 검증 "(multi_tick_engine.py:2167)".
- **실제**: 정의는 line 858, 호출 위치는 다수 (2167은 호출 위치 중 하나로 추정).
- **권고**: "(_get_community_members 정의 line 858, min_trust 기본값 0.4)"로 명시.

### m3. GRACE_AFFILIATION_BOOST 값 표현 불일치

- **위치**: §[필수] 2번 "예상 0.10~0.15, Decision Card에서 확정" vs §B-1 `GRACE_AFFILIATION_BOOST = 0.12`.
- **문제**: 한 곳은 범위, 다른 곳은 확정값. Decision Card 절차 명시 부재.
- **권고**: §[필수] 2번을 "신규 상수 1개: `GRACE_AFFILIATION_BOOST = 0.12` (W_LINEAGE 60% 수준)"으로 통일하거나, §B-1에 "Decision Card 결과: 0.12 채택" 명시.

### m4. §B-2 의사코드의 미실재 함수명

- **위치**: §B-2 의사코드 `faction_territories(faction.id)`.
- **문제**: 실재하지 않는 함수. 실제 kernel은 `self._same_territory(persona, fid) > 0.5` 패턴 사용.
- **권고**: M1과 통합 수정.

---

## TRIVIA — 2건

### t1. `_pick_seed_group` 정렬 트릭 명시

- **위치**: §A-1 helper 본문 `scored.append((-trust, persona.id))`.
- **권고**: 주석 추가 "# trust 내림차순 + pid 오름차순 tie-break (음수 트릭으로 단일 sort)" — 선택사항.

### t2. observe_phase17_emergence.py --label과 출력 디렉토리 매핑

- **위치**: §"결정성 검증" diff 명령의 디렉토리 경로.
- **권고**: --label 인자가 `data/phase17_probe_<label>/` 형태로 매핑됨을 §검증 모두에 1줄 명시 — 선택사항.

---

## 10 카테고리 체크리스트 결과

| # | 카테고리 | 결과 | 비고 |
|--:|---|:--:|---|
| 1 | 목적 부합성 | △ | M3 (인과 사슬 증명) |
| 2 | 완전성 | △ | M2 (테스트 변경 명세 누락) |
| 3 | 정확성 | △ | M1 (라인 인용 부정확), m2 (인용 라인 모호) |
| 4 | 테스트 유효성 | △ | M2 (skip-when-zero 구체 명세) |
| 5 | 모호성 | △ | m3 (값 표현 불일치), m4 (미실재 함수) |
| 6 | 금지 경계 | △ | M4 (boost 임계 우회 검증 부재) |
| 7 | 방향성 | ✅ | loom 3계층 목표 정렬, 자연성 보존 |
| 8 | 구현 가능성 | ✅ | helper·임계·결정성 모두 명시 |
| 9 | Rollback | ✅ | 6단계 명확, 데이터 영향 0 |
| 10 | 회귀 보호 | ✅ | 무파괴 9 + Phase 11~16 회귀 명시 |

---

## 다음 단계 권고

### 옵션 X: spec 보강 후 구현 (권장)
사용자에게 본 검토 리포트 + spec 동시 제시 → MAJOR 4건 보강 승인 → spec 수정 → 구현 분기 결정.

### 옵션 Y: spec 그대로 구현 + 보강은 구현 중 처리
MAJOR 4건이 구현 차단 수준은 아니므로 구현자(Claude/Codex)가 코드 작성 중 인과·테스트·임계·인용 라인을 보강. 위험: 구현자 해석 여지 ↑.

### 옵션 Z: 사용자 결정 대기
본 리포트 + spec을 사용자에게 제시하고 옵션 X·Y·Z 중 선택 받기.

---

## 자체 검증 체크리스트 (검토자 자기 점검)

- [x] 지시서가 인용한 모든 파일을 실제 Read로 확인 (layers.py, multi_tick_engine.py 1200대·1360대·grep, test_phase17_acceptance.py 360대·440대)
- [x] 인용 줄 번호 샘플링 일치 확인 (layers.py 230, 232, 233, 238, 242, 247-251, 256-257 / multi_tick_engine.py 1217, 1392-1395, 1448-1452, 1457, 1819, 1833, 1911, 1963)
- [x] 모든 신규 테스트를 머릿속 시뮬 1회 수행 (skip-when-zero 자동 PASS 메커니즘 발견 → M2)
- [x] Severity 태깅: CRITICAL=구현 불가, MAJOR=품질 하락, MINOR=개선, TRIVIA=선택 — 정의 일치
- [x] 각 이슈에 구체 줄 번호·수정안 부착
- [x] 종합 판정이 CRITICAL 수에 일관 (CRITICAL 0 → 조건부 승인)
- [x] 모호한 지적 없음 (각 finding에 정확한 line 또는 §섹션)
