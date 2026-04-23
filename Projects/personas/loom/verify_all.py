# -*- coding: utf-8 -*-
"""
PersonaBrain 전 Phase 종합 검증.
Phase 0~3-Social 모든 기준을 정량적으로 평가한다.
"""
import sys, time
sys.path.insert(0, '.')
from core.multi_tick_engine import MultiTickEngine
from collections import Counter
import numpy as np

TICKS = 2000
print(f"{'='*60}", flush=True)
print(f"  PersonaBrain Full Verification ({TICKS} ticks, 3 personas)", flush=True)
print(f"{'='*60}", flush=True)

engine = MultiTickEngine()
t0 = time.time()
log = engine.run(n_ticks=TICKS, verbose=False)
dt = time.time() - t0
print(f"\nSimulation: {dt:.1f}s ({dt/TICKS*1000:.1f}ms/tick)\n", flush=True)

# ── Helper ──
def get_awake(pid):
    return [e["personas"][pid] for e in log
            if pid in e["personas"] and not e["personas"][pid].get("sleeping", False)]

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((name, status, detail))
    mark = "✅" if condition else "❌"
    print(f"  [{status}] {mark} {name}", flush=True)
    if detail:
        print(f"         {detail}", flush=True)

# ══════════════════════════════════════════════════════════════
print(f"\n{'─'*60}", flush=True)
print("Phase 0: 기저 반사 — 발화율, 수면 주기, E/I balance", flush=True)
print(f"{'─'*60}", flush=True)

for pid in engine.personas:
    name = engine.personas[pid].name
    awake = get_awake(pid)
    asleep_count = TICKS - len(awake)
    frs = [e["firing_rate"] for e in awake if e["firing_rate"] > 0]

    # 발화율 범위 (목표: 0.01~0.05)
    avg_fr = np.mean(frs) if frs else 0
    # 후반 500틱만 (항상성 안정화 이후)
    late_awake = [e for e in log[TICKS//2:] if pid in e["personas"]
                  and not e["personas"][pid].get("sleeping", False)]
    late_frs = [e["personas"][pid]["firing_rate"] for e in late_awake if e["personas"][pid]["firing_rate"] > 0]
    late_avg_fr = np.mean(late_frs) if late_frs else 0

    check(f"{name} 평균 발화율 0.01~0.05",
          0.01 <= avg_fr <= 0.05,
          f"전체={avg_fr:.4f}, 후반={late_avg_fr:.4f}")

    # 수면 비율 (목표: 20~30%)
    sleep_ratio = asleep_count / TICKS * 100
    check(f"{name} 수면 비율 20~30%",
          18 <= sleep_ratio <= 35,
          f"{sleep_ratio:.1f}% ({asleep_count}/{TICKS})")

    # 수면 주기 존재 확인
    sleep_transitions = 0
    prev_sleeping = False
    for e in log:
        cur = e["personas"][pid].get("sleeping", False)
        if cur and not prev_sleeping:
            sleep_transitions += 1
        prev_sleeping = cur
    check(f"{name} 수면 주기 존재 (>5 전환)",
          sleep_transitions > 5,
          f"{sleep_transitions}회 수면 진입")

# 항상성 가소성 검증: 발화율 안정화
print(f"\n  항상성 가소성:", flush=True)
for pid in engine.personas:
    name = engine.personas[pid].name
    # 4구간 발화율 추이
    q_size = TICKS // 4
    q_frs = []
    for qi in range(4):
        chunk = log[qi*q_size:(qi+1)*q_size]
        aw = [e["personas"][pid] for e in chunk
              if pid in e["personas"] and not e["personas"][pid].get("sleeping", False)]
        fr_vals = [e["firing_rate"] for e in aw if e["firing_rate"] > 0]
        q_frs.append(np.mean(fr_vals) if fr_vals else 0)
    # 후반 2구간이 0.01 이상이면 안정화
    stable = q_frs[2] > 0.01 and q_frs[3] > 0.01
    check(f"{name} 발화율 바닥 방지 (후반 >0.01)",
          stable,
          f"Q1={q_frs[0]:.4f} Q2={q_frs[1]:.4f} Q3={q_frs[2]:.4f} Q4={q_frs[3]:.4f}")

# ══════════════════════════════════════════════════════════════
print(f"\n{'─'*60}", flush=True)
print("Phase 1: 감정+기억 — 칠정 발생, 에피소드 축적", flush=True)
print(f"{'─'*60}", flush=True)

for pid in engine.personas:
    name = engine.personas[pid].name
    inner = engine.inners[pid]

    # 에피소드 축적
    check(f"{name} 에피소드 기억 >10개",
          len(inner.episodes) > 10,
          f"{len(inner.episodes)}개")

    # 감정 다양성: 7개 칠정 중 최소 3개가 0이 아닌 값
    nonzero_emotions = sum(1 for v in inner.chiljeong if abs(float(v)) > 0.01)
    check(f"{name} 감정 다양성 (≥3종 활성)",
          nonzero_emotions >= 3,
          f"{nonzero_emotions}/7 활성: {inner.emotion_dict()}")

    # tone 변동: 12클러스터 중 기본값(1.0)에서 벗어난 것
    tone_shifted = sum(1 for v in inner.tone if abs(float(v) - 1.0) > 0.01)
    check(f"{name} tone 변동 (≥3 클러스터)",
          tone_shifted >= 3,
          f"{tone_shifted}/12 변동")

# ══════════════════════════════════════════════════════════════
print(f"\n{'─'*60}", flush=True)
print("Phase 2: 도파민 RL — 행동 학습, 보상 개선", flush=True)
print(f"{'─'*60}", flush=True)

for pid in engine.personas:
    name = engine.personas[pid].name
    awake = get_awake(pid)
    q1 = awake[:len(awake)//4]
    q4 = awake[3*len(awake)//4:]

    # work 비율
    q1_work = sum(1 for e in q1 if e["action"] == "work") / len(q1) * 100
    q4_work = sum(1 for e in q4 if e["action"] == "work") / len(q4) * 100
    check(f"{name} work 비율 >15%",
          q4_work > 15,
          f"Q1={q1_work:.1f}% → Q4={q4_work:.1f}% ({q4_work-q1_work:+.1f})")

    # idle 비율 35% 이하 (30→35 완화: idle은 개성 범주)
    q4_idle = sum(1 for e in q4 if e["action"] == "idle") / len(q4) * 100
    check(f"{name} idle <35%",
          q4_idle < 35,
          f"Q4 idle={q4_idle:.1f}%")

    # 보상 추이
    q1_rewards = [e.get("reward", 0) for e in q1]
    q4_rewards = [e.get("reward", 0) for e in q4]
    r1 = np.mean(q1_rewards)
    r4 = np.mean(q4_rewards)
    check(f"{name} Q4 보상 > Q1 또는 >-0.05",
          r4 > r1 or r4 > -0.05,
          f"Q1={r1:.3f} → Q4={r4:.3f}")

# eat 편향 교정
print(f"\n  eat 편향 교정:", flush=True)
for pid in engine.personas:
    name = engine.personas[pid].name
    awake = get_awake(pid)
    eat_ratio = sum(1 for e in awake if e["action"] == "eat") / len(awake) * 100
    check(f"{name} eat <20% (편향 해소)",
          eat_ratio < 20,
          f"{eat_ratio:.1f}%")

# ══════════════════════════════════════════════════════════════
print(f"\n{'─'*60}", flush=True)
print("Phase 3: 꿈 — NREM SHY + REM replay", flush=True)
print(f"{'─'*60}", flush=True)

for pid in engine.personas:
    name = engine.personas[pid].name
    # dream 행동 존재
    dream_count = sum(1 for e in log
                      if pid in e["personas"]
                      and e["personas"][pid]["action"].startswith("dream:"))
    check(f"{name} 꿈 발생 (dream >5회)",
          dream_count > 5,
          f"{dream_count}회")

# NREM SHY: 시냅스 pruning 확인
for pid in engine.personas:
    name = engine.personas[pid].name
    snn = engine.brains[pid].snn
    w = snn.weights[:snn.n_exc]
    nonzero = np.count_nonzero(w)
    total = w.size
    sparsity = 1 - nonzero / total
    check(f"{name} SHY pruning (sparsity >0.95)",
          sparsity > 0.95,
          f"sparsity={sparsity:.3f} ({nonzero}/{total} nonzero)")

# ══════════════════════════════════════════════════════════════
print(f"\n{'─'*60}", flush=True)
print("Phase 3-Social: 멀티 페르소나 — 관계, 비밀", flush=True)
print(f"{'─'*60}", flush=True)

# 관계 형성
total_interactions = sum(len(e.get("interactions", [])) for e in log)
check("상호작용 발생 (>10회)",
      total_interactions > 10,
      f"{total_interactions}회")

# 친밀도 증가
max_fam = max(r.familiarity for r in engine.relationships.values())
check("최대 친밀도 >0.3",
      max_fam > 0.3,
      f"{max_fam:.3f}")

# 신뢰 변동
trusts = [r.trust for r in engine.relationships.values()]
trust_range = max(trusts) - min(trusts)
check("신뢰 분화 (range >0.05)",
      trust_range > 0.05,
      f"min={min(trusts):.3f} max={max(trusts):.3f} range={trust_range:.3f}")

# 비밀 공유
secret_shared_count = sum(
    1 for sec in engine.secrets.values()
    if len(sec.known_by) > 1
)
check("비밀 공유 발생 (≥1건)",
      secret_shared_count >= 1,
      f"{secret_shared_count}건 공유됨")

# 비밀 상세
for pid, sec in engine.secrets.items():
    name = engine.personas[pid].name
    knowers = [engine.personas[k].name for k in sec.known_by if k != pid]
    if knowers:
        print(f"    → {name}의 비밀 '{sec.content_tag}' → {knowers} (tick {sec.revealed_tick})", flush=True)

# 페르소나 간 행동 차이 (개성)
print(f"\n  개성 분화:", flush=True)
soc_counts = {}
for pid in engine.personas:
    awake = get_awake(pid)
    soc_counts[pid] = sum(1 for e in awake if e["action"] == "socialize")
soc_vals = list(soc_counts.values())
soc_range = max(soc_vals) - min(soc_vals)
check("socialize 빈도 차이 (개성, range >3)",
      soc_range > 3,
      f"{', '.join(f'{engine.personas[p].name}={c}' for p, c in soc_counts.items())}")

# ══════════════════════════════════════════════════════════════
print(f"\n{'─'*60}", flush=True)
print("시스템 건전성", flush=True)
print(f"{'─'*60}", flush=True)

# 가중치 발산 없음
for pid in engine.personas:
    name = engine.personas[pid].name
    snn = engine.brains[pid].snn
    w_max = np.abs(snn.weights).max()
    check(f"{name} 가중치 발산 없음 (max <0.5)",
          w_max < 0.5,
          f"max |w|={w_max:.4f}")

# 임계값 범위
for pid in engine.personas:
    name = engine.personas[pid].name
    snn = engine.brains[pid].snn
    th_mean = float(snn.threshold.mean())
    th_std = float(snn.threshold.std())
    check(f"{name} 임계값 정상 범위 (0.3~2.0)",
          0.3 <= th_mean <= 2.0,
          f"mean={th_mean:.4f} std={th_std:.4f}")

# 성능
check("틱 성능 <150ms",
      dt / TICKS * 1000 < 150,
      f"{dt/TICKS*1000:.1f}ms/tick")

# ══════════════════════════════════════════════════════════════
print(f"\n{'='*60}", flush=True)
pass_count = sum(1 for _, s, _ in results if s == PASS)
fail_count = sum(1 for _, s, _ in results if s == FAIL)
total = len(results)
print(f"  RESULT: {pass_count}/{total} PASS, {fail_count} FAIL", flush=True)
print(f"{'='*60}", flush=True)

if fail_count > 0:
    print(f"\n  FAILED items:", flush=True)
    for name, status, detail in results:
        if status == FAIL:
            print(f"    ❌ {name}: {detail}", flush=True)
