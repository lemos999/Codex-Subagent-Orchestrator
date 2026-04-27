# Phase 17 Phi-2 Faction Stage 4 Closure Report

> Measured: 2026-04-25  
> Baseline: Stage 3 anti-collapse + Stage 4 contract/docs + addendum v2 validation/report corrections  
> Verdict: **Stage 5 escalation. Phi-2 is not CLOSED.**  
> User decision: pending.

---

## 1. Probe Summary

Command:

```bash
py observe_phase17_emergence.py --seeds 7,13,42 --ticks 5000 --out data/phase17_probe/stage4
```

| seed | active_factions_end | drift_ratio | gini | faction_change_count | min_faction_size_p50 | respawn_event_count | last_500_ticks_active_ge_2_ratio | probe verdict | Stage 4 verdict |
|:---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 7 | 2 | 86.24% | 0.8014 | 298 | 3 | 8 | 1.0000 | FAIL | PASS |
| 13 | 1 | 81.78% | 0.6742 | 225 | 4 | 7 | 0.8333 | FAIL | FAIL |
| 42 | 1 | 78.61% | 0.7300 | 187 | 4 | 6 | 0.6667 | FAIL | FAIL |

Primary acceptance `active_factions_end >= 2` for all three seeds: **FAIL (1/3)**.

Interpretation:
- Stage 3 respawn fires and drift remains active.
- Final multi-faction persistence is still not stable across seeds.
- The previous absorbing-state problem is softened, not solved.

---

## 2. Addendum v2 Corrections

| item | result | evidence |
|---|---:|---|
| A. Functional-equivalence marker | PASS | `test_phase17_faction_handoff_contract.py`, `test_phase17_acceptance.py` include `spec functional-equivalence:` docstrings. |
| B. `test_class_promotion` separate diagnosis | PASS | Diagnostic written to `data/phase17_probe/stage4_addendum/class_promotion_diag.txt`. |
| C. Stable tick perf median/p95 | PASS | Warmup 100, then 5x100 ticks on one seed=42 engine. |
| D. Faction kernel 0~960 measurement | PASS | Measures affiliation/commit/project/respawn across two respawn periods. |
| E. Main runner perf line | PASS | `observe_phase17_emergence.py` prints the seed=42 perf line. |
| F. D10 read-only definition | PASS | Charter and handoff test now exclude lazy cache refresh from domain mutation. |

---

## 3. Determinism

- 5-channel byte-level hash, seed=42, 500 ticks, run A:  
  `7745ef32924d8a008fc48ca449cd183bfc3acad7f8037ac4d96707942ada7206`
- 5-channel byte-level hash, seed=42, 500 ticks, run B:  
  `7745ef32924d8a008fc48ca449cd183bfc3acad7f8037ac4d96707942ada7206`
- Result: **PASS**

Channels:
- `persona.faction`
- `persona.faction_cooldown`
- `inner.affiliation_scores`
- `engine.factions` registry
- `territory.factionRef`

---

## 4. Performance

Acceptance perf sample:

```text
[perf] tick(ms)  median=135.0  p95=139.7  samples=[158.7,139.7,135.0,130.1,127.0]
[perf] faction_kernel(ms/tick)  affiliation=0.16  commit=0.00  project=0.00  respawn=0.00  total=0.16
```

Probe runner final perf line:

```text
[perf] tick=191.6ms  faction_kernel=0.25ms  (seed=42 sample)
```

Budgets:
- tick median `<=250 ms/tick`: **PASS**
- tick p95 `<=350 ms/tick`: **PASS**
- faction kernel `<=5.0 ms/tick`: **PASS**
- respawn branch included in kernel window: **PASS** (`birth_founder` delta >= 1 during the 0~960 probe)

---

## 5. Hard Invariants

- D10 read-only handoff contract: **PASS** (`12/12`)
- Stage 4 deterministic/performance pytest targets: **PASS** (`3/3`)
- `test_class_promotion.py`: **known baseline KeyError reproduced**, not timeout.
  - branch: addendum B(a)
  - line: `test_class_promotion.py:102`
  - error: `KeyError: 'persona_020'`
  - runtime before collection error: `386.71s`
- `brain/**`: unchanged
- `core/multi_tick_engine.py`: unchanged by addendum v2
- `ontology/layers.py`: unchanged by addendum v2
- Stage 1/2/3 constants: unchanged
- No new faction mechanism added
- `FactionChangeSource`: unchanged (`birth_founder`, `affiliation`, `drift`, `conflict`)

Static tooling:
- `py -m mypy Projects/personas/loom/`: unavailable, `No module named mypy`
- `py -m ruff check Projects/personas/loom/`: unavailable, `No module named ruff`

---

## 6. Source Distribution

| source | seed 7 | seed 13 | seed 42 |
|---|---:|---:|---:|
| birth_founder | 11 | 10 | 9 |
| affiliation | 30 | 31 | 31 |
| drift | 257 | 184 | 147 |
| conflict | 0 | 0 | 0 |

Notes:
- `birth_founder` includes the initial founder seed events plus Stage 3 respawn events.
- Derived respawn estimates after subtracting initial active founders: seed 7 = 8, seed 13 = 7, seed 42 = 6.
- `conflict` remains reserved for Phi-3 and is correctly zero.

---

## 7. Verdict

**FAIL: Stage 5 escalation required.**

Phi-2 cannot be declared CLOSED because only 1 of 3 seeds finishes with `active_factions_end >= 2`.

Candidate Stage 5 analysis tracks, without applying them in Stage 4:
- D. Territory locking or territorial retention pressure
- E. Contact correction so surviving factions stay geographically adjacent enough to matter
- F. Join/leave asymmetry to prevent late total absorption
- Additional review of respawn timing versus affiliation drift dominance

No parameter tuning, production mechanism change, SNN change, or Stage 1/2/3 constant change was applied in Stage 4 addendum v2.
