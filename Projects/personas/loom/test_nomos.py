# -*- coding: utf-8 -*-
"""자연법 응징 검증 — Phase 10 (L0.5).

3000틱 시뮬레이션으로 Nomos 시스템 검증:
T1: 정상 운영에서 nomos_violation 과다 발생하지 않는가 (< 50건)
T2: 착취 발생 시 위반이 실제로 감지되는가
T3: 행동 차단(nomos_blocked_until)이 실제 work를 막는가
T4: 위반자의 trust가 하락하는가
T5: 기존 승급 테스트 호환 (최소 1명 class 2)
"""
import sys, time
sys.path.insert(0, '.')
from core.multi_tick_engine import MultiTickEngine
from ontology import NOMOS_SEVERITY
import numpy as np

TICKS = 3000
print(f"=== Nomos 자연법 검증 ({TICKS}틱) ===")

engine = MultiTickEngine()

nomos_events = []
blocked_work_count = 0  # 행동 차단이 실제 발동된 횟수

start = time.time()
for t in range(TICKS):
    result = engine.tick()
    if "nomos" in result:
        for evt in result["nomos"]:
            nomos_events.append(evt)
            if evt.get("severity") in ("중대", "금기"):
                print(f"  [tick {engine.time.tick}] NOMOS {evt['severity']}: "
                      f"{evt['violator']} laws={evt['laws']}")

elapsed = time.time() - start
print(f"\n소요: {elapsed:.1f}s ({elapsed/TICKS*1000:.1f}ms/tick)")

# ── 통계 ──
print(f"\n=== Nomos 이벤트: {len(nomos_events)}건 ===")
severity_counts = {}
for evt in nomos_events:
    s = evt.get("severity", "unknown")
    severity_counts[s] = severity_counts.get(s, 0) + 1
for sev, cnt in sorted(severity_counts.items()):
    print(f"  {sev}: {cnt}건")

# 위반자 목록
violators = {}
for evt in nomos_events:
    v = evt["violator"]
    violators[v] = violators.get(v, 0) + 1
if violators:
    print(f"\n=== 위반자 ===")
    for v, cnt in sorted(violators.items(), key=lambda x: -x[1]):
        inner = engine.inners[v]
        name = engine.personas[v].name
        print(f"  {name:12s} violations={cnt} "
              f"total_count={inner.nomos_violation_count} "
              f"blocked_until={inner.nomos_blocked_until} "
              f"last_severity={inner.nomos_last_severity}")

# 행동 차단 확인
blocked_personas = [pid for pid in engine.personas
                    if engine.inners[pid].nomos_blocked_until > 0]
print(f"\n행동 차단 경험자: {len(blocked_personas)}명")

# 페르소나 상태
print(f"\n=== 페르소나 상태 ===")
for pid in engine.personas:
    p = engine.personas[pid]
    inner = engine.inners[pid]
    print(f"  {p.name:12s} class={p.persona_class} "
          f"nomos_viol={inner.nomos_violation_count} "
          f"stress={inner.chronic_stress:.3f} "
          f"trust_avg={np.mean([r.trust for r in engine.relationships.values() if r.persona_a == pid or r.persona_b == pid]):.3f}")

# ── 판정 ──
print(f"\n=== 최종 판정 ===")
tests = []

# T1: 정상 운영에서 과다 위반 없음
t1 = len(nomos_events) < 50
tests.append(("위반 과다 아님 (<50건)", t1, f"total={len(nomos_events)}"))

# T2: 착취 발생 시 감지됨 (exploitation > 0.5 인 고용이 있으면 감지 필수)
high_exploit = any(emp.exploitation_score > 0.5 and emp.grievances >= 3
                   for emp in engine.employments.values())
if high_exploit:
    detected = any(e for e in nomos_events if "제2조" in str(e.get("laws", [])))
    tests.append(("착취 감지 작동", detected, f"detected={detected}"))
else:
    tests.append(("착취 감지 작동", True, "SKIP (착취 미발생)"))

# T3: 중대/금기 위반 시 행동 차단 설정됨
severe_events = [e for e in nomos_events if e.get("severity") in ("중대", "금기")]
if severe_events:
    any_blocked = any(engine.inners[e["violator"]].nomos_blocked_until > 0
                      for e in severe_events
                      if e["violator"] in engine.inners)
    tests.append(("중대 위반 → 행동 차단", any_blocked, f"severe={len(severe_events)}"))
else:
    tests.append(("중대 위반 → 행동 차단", True, "SKIP (중대 위반 미발생)"))

# T4: 위반자 trust 하락 (위반자가 있으면 그의 평균 trust < 전체 평균)
if violators:
    worst_violator = max(violators, key=violators.get)
    v_trusts = [r.trust for r in engine.relationships.values()
                if r.persona_a == worst_violator or r.persona_b == worst_violator]
    all_trusts = [r.trust for r in engine.relationships.values()]
    v_avg = np.mean(v_trusts) if v_trusts else 0
    a_avg = np.mean(all_trusts) if all_trusts else 0
    t4 = v_avg <= a_avg
    tests.append(("위반자 trust <= 전체 평균", t4,
                   f"violator={v_avg:.3f} all={a_avg:.3f}"))
else:
    tests.append(("위반자 trust <= 전체 평균", True, "SKIP (위반자 없음)"))

# T5: 기존 승급 호환 (최소 1명 class 2)
promoted = [pid for pid in engine.personas
            if engine.personas[pid].persona_class >= 2]
t5 = len(promoted) >= 1
tests.append(("최소 1명 class 2 승급", t5, f"promoted={len(promoted)}명"))

# ── 결과 출력 ──
all_pass = True
for name, passed, detail in tests:
    status = "PASS" if passed else "FAIL"
    if not passed:
        all_pass = False
    print(f"  [{status}] {name}  ({detail})")

print(f"\n{'ALL PASS' if all_pass else 'SOME FAILED'}")
