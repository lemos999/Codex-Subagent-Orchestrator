# Phase 17 Case C 진단 v3 spec — Helper 정의 정정 + 측정 윈도우 확장 (rev.3)

> 긴급도: 높음 (closure-v2 §7.2 Finding A "P75=4·3·3 자연 발생" 검증 실패 → Φ-4 Trigger 1번 보류 상태)
> 선행 조건: Phase 17 Case C 진단 v2 (`PHASE-17-CASE-C-DIAGNOSIS-REPORT.md`, label `phi3-case-c-diagnosis-v2`)
> 작업 유형: 진단 spec (mechanism 무수정, 측정 helper 정정만)
> rev.2 — spec-review CRITICAL 4건 + MAJOR 4건 반영 (2026-05-03)
> rev.3 — spec-review (rev.2) MINOR 2건 보강 (2026-05-03)
> DB migration: 없음
> 외부 의존: 없음

---

## 메타 — 3계층 목적 (역산)

- **궁극 목적**: 자율 사회 시뮬 + SNN 창발 + PersonaBrain 논문 출판
- **Phase 목적**: Φ-3 Struggle closure-v2 Finding A 검증을 위한 cross_faction_lord 자연 발생·collapse 정확 측정
- **본 spec 고유 역할**: v2 helper 정의 오류(territory 소유자 정의) 정정 + 측정 윈도우 확장 + v2 풍부 상태(H5a/b/c 분류) 유지. **mechanism 무변경**.

---

## rev.2 변경 사유 (spec-review 반영)

| # | 결함 | rev.1 → rev.2 |
|---|------|--------------|
| C1 | `self._record_event(kind=, payload=)` 미존재 메서드 | `self.event_log.append({"type": ..., "tick": ...})` 패턴으로 정정 (실제 코드 패턴 일치) |
| C2 | `self._events` 미존재 attribute | `self.event_log` 사용 (Grep count=22 확인) |
| C3 | `event.kind` / `event.payload` (dict인데 attribute 접근) | `event.get("type")` / `event.get("top_lord_id")` 등 dict key 접근 |
| C4 | v2 collapse 이유 분석(H5a/b/c) + 풍부 상태 제거 | v2 `_cfl_pair_state` + `first_seen_tick` + `collapse_reason` 3종 유지 |
| M5 | PROBE vs v3 임계 T 차이 미명시 | §1.1에 정의 차이 명시 (PROBE는 임계 T post-processing, v3는 자연 측정) |
| M6 | observe runner schema 호환 검증 누락 | §변경 파일 + §검증 6.7에 schema 호환 항목 추가 |
| M7 | 회귀 7종 누락 (4종만 명시) | §검증 5.3에 회귀 7종 정확히 열거 |
| M8 | AST 검증 사양 추상적 | §3.2에 의사코드 추가 |

---

## rev.3 변경 사유 (spec-review rev.2 MINOR 반영)

| # | 결함 | rev.2 → rev.3 |
|---|------|--------------|
| MINOR-1 | `lord_id_replaced` 판정의 `event_log` 전체 O(N) 순회 — 매 tick 호출 시 잠재 비용 (20,000틱 × N 누적) | §2 실행 시간 측정 [선택 권고] → **[필수] 격상**, §검증 6.8에 v2 5000틱 × 4(선형) 대비 비율 항목 추가 (5배 초과 시 issue) |
| MINOR-2 | §3.2 AST 검증 1번 + guard rg 책임 분담 — 다른 메서드(`_collect_contact_pairs`, `faction_wealth_distribution` 등)의 `territories.values()` false positive 가능 | §3.2에 **AST 항목 1.5 추가** — `ast.walk(node)` 기반 helper body 안에서만 `self.territories.values()` 호출 부재 정확 검증. 기존 grep guard는 추가 안전망으로 보존 |

---

## 배경

### 문제

v2 진단 결과 `cross_faction_lord_pair_emerged/collapsed = 0/0/0` (3 seed 모두 영구 미발화). 그러나 PROBE 시뮬 (`data/phase14b_b_threshold_simulation.md` §3) `cross_faction_lord_count` P75=4·3·3 (seed-7/13/42).

### 근본 원인 (Claude 검토 2026-05-03)

1. **spec rev.0 §3.1 Event 6 helper 작성자 오류** (Claude 책임)
   - 원 코드: `factions = {inners[lord_id].factionRef for lord_id in lords}`
   - 문제: set comprehension이 lord persona의 단일 factionRef만 누적 → set 항상 1개 → emerged 영구 미발화
2. **Codex v2 자율 정정도 PROBE 정의와 불일치** ([core/multi_tick_engine.py:1771-1781](Projects/personas/loom/core/multi_tick_engine.py#L1771))
   - Codex는 v2 구현에서 `territory.lord_id` + `territory.factionRef` 페어 — 소유자 정의
   - PROBE는 [analyze_phase14b_b_anger_quantiles.py:73-78](Projects/personas/loom/Tools/scripts/analyze_phase14b_b_anger_quantiles.py#L73): `event["top_lord_id"]` + `event["fid"]` 페어 — grievance 대상 정의
   - 두 정의는 **서로 다른 현상**
3. **측정 윈도우 5000틱 부족**
   - `FOUNDER_RESPAWN_EVERY=480` → 5000틱 = 약 10 사이클
   - seed 7 oscillation 1회만, seed 13 collapse 시점만(4500틱), seed 42 미collapse
   - §3.7 1단(자연 측정) 충실성 미달

---

## 작업 범위

### [필수]
1. `_record_cross_faction_lord_pair_events()` 재작성 — **PROBE 정의 채택** (`uprising_leader_snn_snapshot.top_lord_id` 누적 페어)
2. v2의 H5a/b/c 분류 + `_cfl_pair_state` + `first_seen_tick` + `duration_ticks` + `collapse_reason` **유지** (퇴보 금지)
3. 측정 윈도우 5000 → **20,000** (약 40 사이클)
4. spec 본문(`PHASE-17-CASE-C-COLLAPSE-DIAGNOSIS-SPEC.md`) §3.1 Event 6 정의 명문화 + axis C 가드레일 부합 명시
5. v3 진단 보고서(`PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md`) 작성
6. 회귀 7종 PASS 유지 (§검증 5.3 정확 열거)

### [선택]
- helper 단위 테스트 추가 (3 케이스: 페어 0/1/2, collapse_reason 3종)
- snapshot 추이 시각화 (matplotlib)
- v2와 v3 결과 정량 비교 표 (보고서 §4)

### [금지]
- **mechanism 변경** — axis C 안티패턴 (Φ-4 STUB OQ 7-d 위반)
- acceptance 변경 — closure-v2 §0 vL.1 위반
- 안전 전제 5종 변경 (HYSTERESIS=2, FOUNDER_RESPAWN_EVERY=480, TARGET_ACTIVE=2, COMMIT_EVERY=48, MAX_MEMBERS=2)
- BOOST=0.20 변경
- 무파괴 9 (Charter v2) 위반
- D10 SNN 7종 read-only API mutation
- `brain/**` 또는 SNN 뉴런 구조 변경
- v2 진단 보고서 삭제·수정 (역사 보존)
- v2 helper의 H5a/b/c 분류 단순화 (퇴보 금지)

---

## 구체 사양

### 1. Helper 재작성 (PROBE 정의 + v2 풍부 상태 유지)

#### 1.1 정의 차이 명문화

| 측정 | 데이터 출처 | 임계 T 적용 | 사용 위치 |
|------|------------|:----------:|----------|
| v2 helper (폐기) | `self.territories` 매 tick 상태 (소유자 정의) | ❌ | core/multi_tick_engine.py:1766 |
| **v3 helper rev.2 (적용)** | `self.event_log` 누적 (`uprising_leader_snn_snapshot` 이벤트, grievance 대상 정의) | ❌ (자연 측정) | core/multi_tick_engine.py:1766 (rewrite) |
| PROBE 시뮬 | `event_log` 누적 (post-processing, 같은 이벤트) | ✅ (anger ≥ T 필터) | Tools/scripts/analyze_phase14b_b_anger_quantiles.py:71 |

**v3 vs PROBE 차이**: PROBE는 임계 T 통과 이벤트만 필터해 사후 추산, v3는 임계 미적용 자연 누적. **자연 측정이 §3.7 1단 충실성에 정합**. PROBE P75=4·3·3과 정량 일치 불요 (다른 데이터 셋), **잠재력 비교 자료**로만 활용.

#### 1.2 현재 코드 (v2, Codex 구현 — 폐기 대상)

[core/multi_tick_engine.py:1766-1823](Projects/personas/loom/core/multi_tick_engine.py#L1766) (실제 v2 코드 발췌):
```python
def _record_cross_faction_lord_pair_events(self) -> None:
    """v2: trace cross-faction lord pair emergence/collapse without mechanism changes."""
    if not hasattr(self, "_cfl_pair_state"):
        self._cfl_pair_state = {}

    lord_to_factions: dict[str, set[str]] = {}
    for territory in self.territories.values():     # ← v2: territory iteration (폐기)
        lord_id = getattr(territory, "lord_id", None)
        tfid = getattr(territory, "factionRef", None)
        if lord_id is not None and tfid is not None:
            lord_to_factions.setdefault(lord_id, set()).add(tfid)
    # ... (이하 H5a/b/c 분류, first_seen_tick, duration_ticks 추적 — 유지)
```

#### 1.3 v3 정정 코드 (rev.2 — PROBE 정의 + v2 풍부 상태 유지)

```python
def _record_cross_faction_lord_pair_events(self) -> None:
    """
    v3 (rev.2): PROBE 정의(grievance 대상 lord) 채택 + v2 풍부 상태(H5a/b/c) 유지.

    PROBE 시뮬과의 차이:
    - PROBE: anger >= T 임계 통과 이벤트만 필터 (post-processing simulation)
    - v3:    임계 미적용 자연 누적 (§3.7 1단 충실성)

    v2 territory.factionRef(소유자 정의)는 폐기. closure-v2 §7.2 Finding A 가설은
    PROBE 정의(grievance 대상 lord)임.

    호출 빈도: tick() 내 기존 호출 위치 유지 (line 804).
    """
    if not hasattr(self, "_cfl_pair_state"):
        self._cfl_pair_state = {}

    # PROBE 정의: uprising_leader_snn_snapshot 이벤트 누적 -> top_lord_id별 fid set
    lord_to_factions: dict[str, set[str]] = {}
    for event in self.event_log:
        if event.get("type") != "uprising_leader_snn_snapshot":
            continue
        lid = event.get("top_lord_id")
        fid = event.get("fid")
        if lid is not None and fid is not None:
            lord_to_factions.setdefault(lid, set()).add(fid)

    current_pairs = {
        lord_id: frozenset(fids)
        for lord_id, fids in lord_to_factions.items()
        if len(fids) >= 2
    }
    prev_pairs = {
        lord_id: state["factions"]
        for lord_id, state in self._cfl_pair_state.items()
    }

    # emerged
    for lord_id, fids in current_pairs.items():
        if lord_id not in prev_pairs:
            self.event_log.append({
                "type": "cross_faction_lord_pair_emerged",
                "tick": self.time.tick,
                "lord_id": lord_id,
                "factions": sorted(fids),
                "definition": "probe_top_lord_id_accumulated",
            })
            self._cfl_pair_state[lord_id] = {
                "factions": fids,
                "first_seen_tick": self.time.tick,
            }

    # collapsed (v2 H5a/b/c 분류 유지, 정의는 PROBE 기반)
    for lord_id, prev_fids in prev_pairs.items():
        if lord_id in current_pairs:
            continue
        # H5c: lord persona 사라짐
        if lord_id not in self.personas or lord_id not in self.inners:
            reason = "lord_persona_missing"
        # H5b: lord_id가 더 이상 어떤 fid의 grievance 대상도 아님
        #      (PROBE 정의: event_log의 어떤 uprising_leader_snn_snapshot에서도 top_lord_id로 등장 안 함)
        elif not any(
            event.get("type") == "uprising_leader_snn_snapshot"
            and event.get("top_lord_id") == lord_id
            for event in self.event_log
        ):
            reason = "lord_id_replaced"
        # H5a: faction 통합 (이벤트 누적상으로는 fid가 1개로 collapse)
        else:
            reason = "faction_consolidated"
        first_seen_tick = int(self._cfl_pair_state[lord_id]["first_seen_tick"])
        self.event_log.append({
            "type": "cross_faction_lord_pair_collapsed",
            "tick": self.time.tick,
            "lord_id": lord_id,
            "prev_factions": sorted(prev_fids),
            "first_seen_tick": first_seen_tick,
            "duration_ticks": self.time.tick - first_seen_tick,
            "collapse_reason": reason,
            "definition": "probe_top_lord_id_accumulated",
        })
        del self._cfl_pair_state[lord_id]

    # 기존 페어 업데이트
    for lord_id, fids in current_pairs.items():
        if lord_id in prev_pairs and prev_pairs[lord_id] != fids:
            self._cfl_pair_state[lord_id]["factions"] = fids
```

#### 1.4 핵심 변경 요약

| 항목 | v2 (폐기) | v3 rev.2 (적용) |
|------|----------|----------------|
| 데이터 출처 | `self.territories.values()` 매 tick 상태 | `self.event_log` 누적 (`uprising_leader_snn_snapshot`) |
| 측정 대상 | territory의 owning faction lord | uprising leader가 grievance 표시한 lord |
| H5 분류 (3종) | ✅ | ✅ 유지 (정의만 PROBE 기반으로 변경) |
| `first_seen_tick` / `duration_ticks` | ✅ | ✅ 유지 |
| `_cfl_pair_state` 풍부 상태 | ✅ | ✅ 유지 |
| 정의 명칭 | (없음) | `probe_top_lord_id_accumulated` (payload 명시) |
| PROBE 시뮬 정의 일치 | ❌ | ✅ (임계 T 차이는 자연 측정 정당화) |
| event 패턴 | `self.event_log.append({"type": ..., ...})` | 동일 (변경 없음, dict 기반) |

### 2. 측정 윈도우 20,000

`observe_phase17_emergence.py` 호출 시 명령 라인 인자만 변경:

```bash
py observe_phase17_emergence.py \
    --label phi3-case-c-diagnosis-v3 \
    --seeds 7,13,42 \
    --ticks 20000
```

기본값 변경 불필요. observer/runner 코드 수정 없음.

**예상 실행 시간**: v2 5000틱 실측 시간을 Codex가 인용한 후, 20000틱 = 4×선형 추정. 병렬 실행 시 단축.

**[필수] 실행 시간 측정 (rev.3 격상, MINOR-1 대응)**: Codex는 v3 실행 시간을 측정하여 보고서(`PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md`)에 명시한다. v2 5000틱 실행 시간을 분모, v3 20000틱을 분자로 비율 계산. **4×(선형) 대비 5배 이상 초과** 시 helper 성능 이슈(MINOR-1 잠재 위험 실현)로 보고서에 명시 + closure-v2 검토 시 입력값으로 활용. 비율이 5배 이내라면 helper의 `event_log` 전체 순회 비용이 실측상 수용 가능 — 정상.

측정 형식 (보고서 §시간 측정 또는 §부록):
```
v2 5000틱 실행 시간:    <초>  (선행 보고서 또는 재실행 인용)
v3 20000틱 실행 시간:   <초>
선형 추정 (v2 × 4):    <초>
실측/추정 비율:         <배수>  → [정상 5배 이내 / 이슈 5배 초과]
```

### 3. spec 본문 정의 명문화 + AST 검증 사양

#### 3.1 `PHASE-17-CASE-C-COLLAPSE-DIAGNOSIS-SPEC.md` §3.1 Event 6 갱신

다음 내용으로 교체:
```markdown
### Event 6: cross_faction_lord_pair_emerged/collapsed

**정의 (v3 rev.2, PROBE 채택)**: `uprising_leader_snn_snapshot` 이벤트의 `top_lord_id`를 누적해, 같은 lord를 grievance 대상으로 가진 다른 fid가 ≥ 2인 lord를 카운트한 것의 변화. **임계 T 미적용** (자연 측정).

**v2 폐기**: `territory.lord_id` + `territory.factionRef` 매 tick 상태(소유자 정의)는 PROBE 시뮬 가설(grievance 대상)과 불일치하여 폐기. v2 진단 보고서(`PHASE-17-CASE-C-DIAGNOSIS-REPORT.md`)는 역사 보존.

**Payload 필수 필드 (rev.2)**:
- emerged: `type`, `tick`, `lord_id`, `factions` (sorted list), `definition` (= `"probe_top_lord_id_accumulated"`)
- collapsed: emerged 필드 + `prev_factions`, `first_seen_tick`, `duration_ticks`, `collapse_reason` (3종: `lord_persona_missing` / `lord_id_replaced` / `faction_consolidated`)

**axis C 가드레일 부합** (Φ-4 STUB OQ 7-a~e):
- (7-a) §3.7 6단 사슬 재진입: 본 정정은 **측정 정의 정정**, mechanism 추가 ❌
- (7-b) axis A/B 거부 사유 동형 검증: helper는 affiliation 가중치/anger 임계 mechanism 미포함 — 단순 카운트 측정만
- (7-c) 차별 정당화: axis A/B는 mechanism 추가 시도, v3는 helper 정의 정정 — 구조 비동형
- (7-d) 거짓 PASS 금지: 자연 발생 페어를 정확히 측정만 함, 임계 강제 없음
- (7-e) Case C v2 결과 인용: territory 정의 0/0/0 + PROBE 정의 P75=4·3·3 → 정의 분기가 결과 차이 원인 (회귀 추적 가능)
```

#### 3.2 `verify_phase17_case_c_diagnosis.py` AST 검증 갱신 의사코드

기존 `_record_cross_faction_lord_pair_events` 검증에 다음 항목 추가:

```python
# AST 검증: helper body에 다음 노드/문자열 모두 존재해야 함
def _verify_v3_helper(node: ast.FunctionDef) -> None:
    body_str = ast.unparse(node.body)

    # 1. event_log iteration (territories iteration 폐기 확인)
    assert "self.event_log" in body_str, "v3 helper는 self.event_log iterate 필수"
    # v2 territory.values() iteration은 lord_to_factions 빌드 단계에서 제거되어야 함
    # (collapsed 분기에서 territories 사용 가능 — 단, lord_to_factions 빌드는 event_log 기반)

    # 1.5 (rev.3 보강, MINOR-2 대응): helper body 안에 self.territories.values() 호출 부재
    # — string grep은 다른 메서드(_collect_contact_pairs, faction_wealth_distribution 등)의
    #   territories.values()도 매칭하므로 false positive 가능. AST 노드 검사로 helper body
    #   범위 안에서만 호출 부재를 정확히 검증.
    for call_node in ast.walk(node):
        if (
            isinstance(call_node, ast.Call)
            and isinstance(call_node.func, ast.Attribute)
            and call_node.func.attr == "values"
            and isinstance(call_node.func.value, ast.Attribute)
            and call_node.func.value.attr == "territories"
            and isinstance(call_node.func.value.value, ast.Name)
            and call_node.func.value.value.id == "self"
        ):
            raise AssertionError(
                "v3 helper body 안에 self.territories.values() 호출 잔존 — "
                "v2 정의(territory 소유자) 폐기 필수, lord_to_factions 빌드는 event_log 기반"
            )

    # 2. uprising_leader_snn_snapshot 이벤트 필터
    assert "uprising_leader_snn_snapshot" in body_str, (
        "v3 helper는 uprising_leader_snn_snapshot 이벤트 필터 필수"
    )

    # 3. top_lord_id / fid 키 사용
    assert "top_lord_id" in body_str, "PROBE 정의 핵심 필드 누락"

    # 4. definition payload 필드 명문화 (rev.2)
    assert '"probe_top_lord_id_accumulated"' in body_str, (
        "정의 명문화 필드 누락"
    )

    # 5. v2 풍부 상태 유지 검증 (퇴보 금지)
    assert "_cfl_pair_state" in body_str, "v2 상태 추적 제거 — 퇴보"
    assert "first_seen_tick" in body_str, "v2 first_seen_tick 추적 제거 — 퇴보"
    assert "duration_ticks" in body_str, "v2 duration_ticks 추적 제거 — 퇴보"
    assert "collapse_reason" in body_str, "v2 H5a/b/c 분류 제거 — 퇴보"
    assert "lord_persona_missing" in body_str, "H5c 분류 누락"
    assert "lord_id_replaced" in body_str, "H5b 분류 누락"
    assert "faction_consolidated" in body_str, "H5a 분류 누락"

    # 6. dict 기반 emit 패턴 확인 (rev.0 잘못된 패턴 잔존 금지)
    assert "_record_event(" not in body_str, "rev.0 잘못된 _record_event 메서드 잔존"
    assert "self._events" not in body_str, "rev.0 잘못된 self._events attribute 잔존"
```

---

## 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `core/multi_tick_engine.py` | `_record_cross_faction_lord_pair_events()` 재작성 (PROBE 정의 + v2 풍부 상태 유지) | 수정 |
| `Tools/scripts/verify_phase17_case_c_diagnosis.py` | helper AST 검증 갱신 (§3.2 의사코드 적용) | 수정 |
| `PHASE-17-CASE-C-COLLAPSE-DIAGNOSIS-SPEC.md` | §3.1 Event 6 정의 명문화 + axis C 가드레일 부합 명시 | 수정 |
| `PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md` | v3 진단 결과 보고서 | 추가 |

**schema 호환 검증 (rev.2 추가)**:
- v3 emit은 v2 schema **superset** — 기존 필드(`lord_id`, `factions`, `prev_factions`, `first_seen_tick`, `duration_ticks`, `collapse_reason`) 모두 유지하고 `definition` 필드만 추가.
- `observe_phase17_emergence.py` 또는 후처리 스크립트가 v2 schema 가정하면 그대로 동작.
- 후처리 스크립트가 schema mismatch로 실패하면 spec 위반 → reject.

**변경 없음 (금지)**:
- `brain/**` — SNN 뉴런 구조 무수정
- `ontology/layers.py` — 안전 전제 5종 + BOOST 무수정
- `core/multi_tick_engine.py`의 mechanism 메서드 (`_compute_affiliation_tick`, `_propagate_grievance_lord_id_cross_territory`, uprising/respawn 로직 등) — 측정 helper 외 무변경
- `observe_phase17_emergence.py` 코드 — 명령 라인 인자만 사용
- `PHASE-17-CASE-C-DIAGNOSIS-REPORT.md` (v2) — 역사 보존
- `test_phase*.py` 회귀 테스트 — 무수정

---

## 검증

### 기계 검증 (필수)

| step | command | 기댓값 |
|---|---|---|
| 5.1 | `py -m py_compile core/multi_tick_engine.py` | PASS |
| 5.1 | `py -m py_compile observe_phase17_emergence.py` | PASS |
| 5.2 | `py Tools/scripts/verify_phase17_case_c_diagnosis.py` | PASS (§3.2 의사코드 항목 모두 통과) |
| 5.3 | 회귀 7종 — `Projects/personas/loom/test_*.py` 실행 (아래 7개 카테고리, 실제 파일명은 Codex가 ls로 확인 후 정확 지목) | 모두 PASS |
| guard | `rg "self\.territories\.values\(\)" core/multi_tick_engine.py` (lord_to_factions 빌드부에 잔존 검사) | helper의 lord_to_factions 빌드부 NO_MATCH (다른 메서드 사용은 OK) |
| guard | `rg "self\._record_event\|self\._events" core/multi_tick_engine.py` (rev.0 잘못된 패턴 잔존) | NO_MATCH |

**회귀 7종 카테고리 (Charter v2 무파괴 + Φ-2/Φ-3 누적)**:

| # | 테스트 카테고리 | 검증 대상 |
|:-:|----------------|----------|
| 1 | SNN integration (Phase 14B) | `test_phase14b_snn_integration.py` (8/8 PASS 기대) |
| 2 | Faction handoff contract | `test_phase17_faction_handoff_contract.py` |
| 3 | Faction stage 3 | `test_phase17_faction_stage3.py` |
| 4 | Phase 17 acceptance | `test_phase17_acceptance.py` (EXPECTED FAIL: 3 known Phi-3 — acceptance 변경 금지로 그대로 유지) |
| 5 | Phase 11~16 경제 | `test_economy.py` 또는 해당 |
| 6 | Persistence (Charter v2 무파괴 7번) | `test_persistence.py` 또는 해당 |
| 7 | Class promotion / nomos 등 Phase 11 보존 | `test_class_promotion.py`, `test_nomos.py` 등 |

(Codex는 `ls Projects/personas/loom/test_*.py`로 실재 파일명 확인 후 정확 지목하여 실행)

### 데이터 검증 (필수)

| step | command | 기댓값 |
|---|---|---|
| 6.1 | `py observe_phase17_emergence.py --label phi3-case-c-diagnosis-v3 --seeds 7,13,42 --ticks 20000` | PASS, data 생성 |
| 6.2 | `data/phase17_probe_phi3-case-c-diagnosis-v3/SUMMARY.md` 생성 확인 | 존재 |
| 6.3 | seed별 `case_c_events.json` 생성 확인 | 3 파일 존재 |
| 6.4 | 새 `cross_faction_lord_pair_emerged/collapsed` 이벤트 발화 확인 | ≥ 1 이벤트 (3 seed 합산) |
| 6.5 | 모든 emerged/collapsed 이벤트 payload에 `"definition": "probe_top_lord_id_accumulated"` 포함 | 100% |
| 6.6 | collapsed 이벤트의 `collapse_reason` 분포 (H5a/b/c) | 3종 모두 ≥ 1 OR 분포 명시 (어느 reason이 dominant인지) |
| 6.7 | observe runner / case_c_events 후처리 schema mismatch 없음 (v3 emit이 v2 schema superset 검증) | error 0건 |
| 6.8 | v3 실행 시간 측정 (rev.3 보강, MINOR-1 대응) — v2 5000틱 시간 × 4(선형) 대비 비율 계산 | 5배 이내 정상 / 5배 이상 초과 시 helper 성능 이슈로 보고서 §시간 측정에 명시 |

### 가설 검증 (필수)

| step | 검증 항목 | 기댓값 |
|---|---|---|
| 7.1 | v3 emerged peak count vs PROBE P75 (잠재력 비교) | seed별 emerged peak ≥ 2 (PROBE 임계 차이 인정, 정량 일치 불요) |
| 7.2 | oscillation 다회 관찰 | seed당 emerged + collapsed 이벤트 합계 ≥ 3 (회복 동역학 관찰) |
| 7.3 | H5a/b/c 분포 | 3종 중 dominant 결정 → Φ-4 charter 1번 작업 우선순위 정렬 입력값 |
| 7.4 | Φ-4 Trigger 1번 충족 여부 판정 | closure-v2 §7.2 Finding A 검증 PASS/FAIL 명시 |

**결과 사례 분류**:
- **(A)** emerged ≥ 2 + collapsed 동역학 관찰 + H5 분류 dominant 명확 → Finding A 검증 PASS, Φ-4 charter 1번 작업 입력값 확보
- **(B)** emerged ≥ 1 but collapse 동역학 부재 → 윈도우 더 확장 (40,000틱) 또는 추가 분석 spec 필요
- **(C)** emerged = 0 → 여전히 정의 문제 OR uprising_leader_snn_snapshot 이벤트 자체 미발화 → §3.7 1~3단 재진단

### 회귀 보호 (필수)

| step | 항목 | 기댓값 |
|---|---|---|
| 8.1 | v2 진단 보고서(`PHASE-17-CASE-C-DIAGNOSIS-REPORT.md`) 보존 | 무수정 (역사 보존) |
| 8.2 | v3 보고서 §4에 v2와 v3 결과 차이 표 작성 | 표 존재 |
| 8.3 | mechanism 메서드 diff 검사 (`_compute_affiliation_tick`, `_propagate_grievance_lord_id_cross_territory`, uprising/respawn 로직) | 변경 없음 |
| 8.4 | acceptance 정의 검사 | 변경 없음 |
| 8.5 | helper의 v2 풍부 상태 (`_cfl_pair_state`, `first_seen_tick`, `collapse_reason` 3종) 유지 | 모두 존재 |

---

## Rollback

v3 정정에 회귀 발생 시:

```bash
git revert <v3 commit hash>
```

영향:
- `_record_cross_faction_lord_pair_events()` 가 v2 정의(territory.factionRef)로 복귀
- v2 진단 보고서 보존되어 있음 (참조 가능)
- `data/phase17_probe_phi3-case-c-diagnosis-v3/` 디렉토리 삭제 가능
- spec §3.1 Event 6 정의 명문화는 **유지 권고** (다음 시도에 동일 함정 방지)

데이터 영향: v3 실행 데이터(`phi3-case-c-diagnosis-v3` 라벨)만 손실. v2 데이터·보고서 영향 없음.

---

## 회고 인정 (Codex 자율 제안 정책 — LOOM-DIRECTION §3.3.1)

본 spec은 [`LOOM-DIRECTION.md §3.3.1` spec 외부 자율 제안 처리](LOOM-DIRECTION.md) 정책의 첫 적용 사례.

### v2 회고

| 항목 | 책임 | 평가 |
|------|------|------|
| spec rev.0 helper 버그 (set comprehension 단일 누적) | Claude (spec 작성자) | **CRITICAL 오류 인정** — set comprehension 동작 잘못 가정. spec-review에서 잡지 못함. |
| Codex 자율 정정 (territory.factionRef로 변경) | Codex 자율 판단 | **부분 가치 + 방향 오류** — 버그 인지·정정 가치는 인정. 정의는 PROBE와 불일치. v2 helper의 H5a/b/c 분류는 가치 산출. |
| stale 코드 제거 (FOUNDER_LOYALTY_BONUS 등 5종) | Codex 자율 판단 | **수용** — 사용자 결정 2026-05-03. |

### v3 rev.1 → rev.2 회고

rev.1 spec 작성자(Claude) 추가 오류:
- `_record_event(kind=, payload=)` 미존재 메서드 사용 (실제 패턴은 `event_log.append({"type": ...})`)
- `self._events` 미존재 attribute 사용 (실제는 `self.event_log`)
- `event.kind` / `event.payload` (dict인데 attribute 접근)
- v2의 H5a/b/c 분류 + 풍부 상태를 단순 카운트로 단순화 — 진단 정보 손실 시도

**원인**: rev.1 작성 시 실제 `multi_tick_engine.py` line 1766-1823 v2 helper 코드를 직접 읽지 않고 spec 머릿속 모델로 helper 작성.

### v3 학습 반영

1. **정의 명문화 의무**: 모든 측정 helper의 payload에 `definition` 필드 추가
2. **PROBE 시뮬과 helper 정의 일치 검증**: spec 작성 시 PROBE 분석 스크립트와 helper 정의 명시 대조 (analyze_phase14b_b_anger_quantiles.py:73-78 인용)
3. **axis C 가드레일 명시 인용**: Φ-4 STUB OQ 7-a~e 항목별 부합 근거를 spec 본문에 명시
4. **set comprehension 함정**: `{obj.field for obj in single_collection}` 에서 collection이 자연 페어를 보장하지 않으면 set 1개로 collapse
5. **spec 작성 전 실제 코드 read 의무**: helper 재작성 시 v2 패턴(`event_log.append` + dict)을 직접 인용하여 작성. 머릿속 모델 금지.
6. **퇴보 금지 원칙**: 정의 정정은 정의만, 풍부한 진단 상태(H5a/b/c, first_seen_tick, duration_ticks, collapse_reason)는 유지

---

## 다음 단계

1. **rev.2 재검토** — 본 spec rev.2를 `/spec-review`로 재검토 (CRITICAL/MAJOR 미발견 확인)
2. **Codex 위임** — review PASS 후 `feedback_claude_codex_workflow` 따라 Codex에게 구현 위임
3. **20,000틱 실행** — 실행 완료 후 `data/phase17_probe_phi3-case-c-diagnosis-v3/` 결과 수집
4. **v3 보고서 작성** — `PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md` 작성, 가설 검증 결과 명시
5. **closure-v2 Finding A 재판정**:
   - PASS → Φ-4 Trigger 1번 충족, Φ-4 charter design 진입 가능
   - FAIL → 추가 진단 spec 또는 closure-v2 갱신
