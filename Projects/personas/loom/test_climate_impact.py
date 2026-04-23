# -*- coding: utf-8 -*-
"""Climate impact verification: emotions, action costs, disasters."""
import sys, time
sys.path.insert(0, '.')
from core.multi_tick_engine import MultiTickEngine
import numpy as np
from collections import Counter

print("Running 2000 ticks with dynamic climate...", flush=True)
engine = MultiTickEngine()
t0 = time.time()
log = engine.run(n_ticks=2000, verbose=False)
dt = time.time() - t0
print(f"Done in {dt:.1f}s ({dt/2000*1000:.1f}ms/tick)\n", flush=True)

# 1. Emotion diversity per persona (climate should add sadness, etc.)
print("=== Emotion Check (climate→emotion active?) ===")
for pid in engine.personas:
    name = engine.personas[pid].name
    region = engine.personas[pid].region
    inner = engine.inners[pid]
    emo = inner.emotion_dict()
    active = sum(1 for v in emo.values() if abs(v) > 0.01)
    print(f"  {name} [{region}]: {active}/7 active — {emo}")

# 2. sadness check (only climate generates sadness via rain)
print("\n=== Sadness/Love from Climate ===")
for pid in engine.personas:
    name = engine.personas[pid].name
    inner = engine.inners[pid]
    sad = float(inner.chiljeong[2])
    print(f"  {name}: sadness={sad:.3f} (should be >0 from rain)")

# 3. Weather narrative distribution
print("\n=== Weather Narratives (sample) ===")
tags = Counter()
for e in log[:500]:
    for rid, w in e.get("weather", {}).items():
        for tag in w.get("narrative_tag", "").split(", "):
            if tag:
                tags[(rid, tag)] += 1
for (rid, tag), count in sorted(tags.items(), key=lambda x: (-x[1], x[0]))[:15]:
    print(f"  {rid:8s} {tag:25s} {count:4d}")

# 4. Action cost multiplier effect
print("\n=== Energy Consumption by Region ===")
for pid in engine.personas:
    name = engine.personas[pid].name
    region = engine.personas[pid].region
    awake = [e["personas"][pid] for e in log
             if pid in e["personas"] and not e["personas"][pid].get("sleeping", False)]
    if awake:
        avg_energy = np.mean([e["energy"] for e in awake])
        work_count = sum(1 for e in awake if e["action"] == "work")
        print(f"  {name} [{region}]: avg_energy={avg_energy:.3f} work={work_count}")

# 5. Disasters
print("\n=== Disaster Events ===")
disaster_events = []
for e in log:
    if e.get("disasters"):
        for d in e["disasters"]:
            disaster_events.append(d)
            print(f"  tick {d['tick']:4d}: {d['region']} {d['type']} Lv.{d['level']} (signal={d['signal']})")
if not disaster_events:
    print("  None (2000 ticks may be too short for disasters)")

# 6. Season-dependent behavior
print("\n=== Season-Action Distribution ===")
season_actions = {}
for e in log:
    season = e.get("season", "?")
    for pid, p in e.get("personas", {}).items():
        if not p.get("sleeping", False):
            key = (engine.personas[pid].region, season)
            if key not in season_actions:
                season_actions[key] = Counter()
            season_actions[key][p["action"]] += 1

for (region, season), actions in sorted(season_actions.items()):
    total = sum(actions.values())
    work_pct = actions.get("work", 0) / total * 100 if total else 0
    sleep_entry = actions.get("sleep", 0) / total * 100 if total else 0
    print(f"  {region:8s} {season:8s}: work={work_pct:4.0f}% sleep_entry={sleep_entry:4.0f}% (n={total})")
