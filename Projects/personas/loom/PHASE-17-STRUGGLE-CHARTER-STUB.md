# Phase 17 / Phi-3 Struggle - Charter STUB

> This file is a stub, not the full Phi-3 Charter.
> It records only the handoff contract produced by Phi-2 Stage 4.
> Full Phi-3 design must be written in a separate `/design` cycle after a Phi-2 closure decision.

## Metadata

| item | value |
|---|---|
| Project | loom persona life simulator |
| Phase | 17 / Phi-3 Struggle |
| Roadmap | Phi-1 Land -> Phi-2 Faction -> Phi-3 Struggle -> Phi-4 Nation |
| Precondition | Phi-2 Stage 4 Closure Report |
| Current status | STUB |

## Purpose

The purpose of Phi-3 is to let conflict and alliance dynamics emerge between existing factions. Phi-3 must not declare enemies top-down. It should read the faction distribution, territory contact, charter primitives, wealth pressure, social trust, and shared grievances produced by Phi-2, then decide whether a struggle dynamic is warranted.

## Primary Outcome

Faction-to-faction tension, alignment, or rivalry emerges from:

- contact between different faction-controlled territories
- population imbalance
- shared grievance targets
- wealth inequality
- social trust or distrust between faction members
- charter primitive overlap or incompatibility

## Operating Loop

Micro:
- observe faction contact and member-level social/economic pressure
- accumulate faction-pair tension or affinity candidates

Middle:
- form alliance or opposition tendencies
- surface struggle triggers without mutating Phi-2 state directly

Macro:
- produce sufficiently stable faction blocs or rivalries for Phi-4 Nation to interpret

## Phi-2 Handoff Inputs

Phi-3 may read Phi-2 only through these seven read-only APIs:

| API | Phi-3 use |
|---|---|
| `faction_population_distribution()` | faction size, imbalance, dominance pressure |
| `faction_territory_distribution()` | territorial footprint and spatial power |
| `faction_charter_primitives(faction_id)` | norm primitive comparison |
| `factions_in_contact(radius=1)` | adjacent faction contact pairs |
| `faction_wealth_distribution()` | economic inequality and resource pressure |
| `faction_social_matrix()` | inter-faction trust or distance |
| `faction_grievance_targets()` | shared enemy or shared grievance coalitions |

No additional Phi-2 internal state is part of the handoff contract.

## Entry Trigger Candidates

Phi-3 design may begin when at least one of these read-only conditions is true:

1. `len(factions_in_contact(radius=1)) >= 1`
2. `max(faction_population_distribution().values()) / sum(...) >= 0.55`
3. At least two factions have two or more members sharing the same `lord_id` in `faction_grievance_targets()`

If none of these conditions is true, Phi-3 entry is deferred and Phi-2 continues to run.

## Included Scope Candidates

- faction-pair hostility or affinity
- alliance formation
- opposition formation
- contact-based tension
- shared-grievance coalitions
- wealth-pressure conflict candidates

## Excluded From This Stub

- combat
- punishment systems
- explicit state or nation formation
- new SNN neurons
- direct writes to `persona.faction`
- changes to Phi-2 constants

## Open Questions

- How should charter primitive conflict be scored?
- What threshold distinguishes disagreement from struggle?
- Should wealth inequality create opposition directly, or only amplify existing contact/grievance?
- How should Phi-3 events feed Phi-4 Nation without declaring sovereignty top-down?
- Does hostility require a new guide-layer state, or can it be inferred each tick?

## Next Steps

1. Resolve Phi-2 Stage 5 or declare Phi-2 closed if future probe acceptance passes.
2. Run `/design` for full Phi-3 Charter.
3. Use `/discuss` to settle the open question catalog.
4. Produce `PHASE-17-STRUGGLE-CODEX-INSTRUCTIONS.md` only after full Charter approval.
