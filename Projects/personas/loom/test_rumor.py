# -*- coding: utf-8 -*-
"""Rumor system test — 3000 ticks, watch for rumor spread + telephone effect."""
import sys, time
sys.path.insert(0, '.')
from core.multi_tick_engine import MultiTickEngine

print("Running 3000 ticks...", flush=True)
engine = MultiTickEngine()
t0 = time.time()
log = engine.run(n_ticks=3000, verbose=False)
print(f"Done in {time.time()-t0:.1f}s", flush=True)

# Rumor events
events = []
for entry in log:
    for inter in entry.get("interactions", []):
        if inter.get("secret_shared"):
            s = inter["secret_shared"]
            events.append((entry["tick"], "SECRET",
                           engine.personas[s["owner"]].name,
                           engine.personas[s["revealed_to"]].name,
                           s["tag"], 1.0, 0))
        if inter.get("rumor_spread"):
            rs = inter["rumor_spread"]
            events.append((entry["tick"], "RUMOR",
                           engine.personas[rs["from"]].name,
                           engine.personas[rs["to"]].name,
                           rs["tag"], rs["accuracy"], rs["spread_count"]))

print(f"\n=== Information Flow ({len(events)} events) ===")
for tick, typ, frm, to, tag, acc, sc in events:
    if typ == "SECRET":
        print(f"  tick {tick:4d}: SECRET {frm} -> {to} ({tag})")
    else:
        print(f"  tick {tick:4d}: RUMOR  {frm} -> {to} ({tag}) acc={acc:.0%} spread#{sc}")

# Final state
print(f"\n=== Relationships ===")
for key, rel in engine.relationships.items():
    a = engine.personas[rel.persona_a].name
    b = engine.personas[rel.persona_b].name
    print(f"  {a} <-> {b}: fam={rel.familiarity:.3f} trust={rel.trust:.3f}")

print(f"\n=== Rumors ({len(engine.rumors)}) ===")
for r in engine.rumors:
    about = engine.personas[r.about_id].name
    knowers = [engine.personas[k].name for k in r.known_by if k in engine.personas]
    print(f"  [{about}'s {r.content_tag}] accuracy={r.accuracy:.0%} spread={r.spread_count} "
          f"known_by={knowers}")
