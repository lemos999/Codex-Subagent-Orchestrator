# Phase 17 Case-C Collapse Diagnosis Report

## Purpose

- Ultimate purpose: keep Loom on the path toward autonomous society emergence, where faction and struggle behavior is measured before it is repaired.
- Phase purpose: produce Phi-3 Struggle evidence for why uprising, grievance resonance, and branch faction emergence still collapse or fail.
- This diagnostic role: add read-only telemetry only, run the 3-seed probe, and identify the likely root cause without changing acceptance or mechanism rules.

## Changed Files

- `core/multi_tick_engine.py`
  - Added read-only telemetry for `uprising_skip_no_contact`, respawn skip/fallback reasons, `minority_boost_applied`, `drift_recovery_to_minority`, `active_factions_snapshot`, and H5 cross-faction-lord pair events.
  - Moved `active_factions_snapshot` and H5 pair tracking into `tick()` so snapshots occur every 500 ticks instead of only on economy ticks.
  - Removed stale Contact Persistence experiment mechanics from this diagnostic scope: founder-loyalty bonus use, respawn seed-group assignment, and persona-relationship contact path.
  - Extracted prior Phase14B telemetry payload construction into helper methods so the AST guard can verify mechanism body size.
- `observe_phase17_emergence.py`
  - Added Case-C H1-H5 diagnosis fields to `SUMMARY.md`.
  - Writes `case_c_events.json` with the H5 telemetry events.
- `Tools/scripts/verify_phase17_case_c_diagnosis.py`
  - Updated AST verification to require `_record_cross_faction_lord_pair_events`.
- `ontology/layers.py`
  - Removed stale `FOUNDER_LOYALTY_BONUS` from the previous tuning attempt.
- `PHASE-17-CASE-C-DIAGNOSIS-REPORT.md`
  - This report.

## Verification

| step | command | result |
|---|---|---|
| 5.1 | `py -m py_compile core/multi_tick_engine.py` | PASS |
| 5.1 | `py -m py_compile observe_phase17_emergence.py` | PASS |
| 5.2 | `py Tools/scripts/verify_phase17_case_c_diagnosis.py` | PASS (`OK`) |
| 5.3 | `py test_phase17_faction_handoff_contract.py` | PASS |
| 5.3 | `py test_phase14b_snn_integration.py` | PASS (`8/8 PASS`) |
| 5.3 | `py test_phase17_faction_stage3.py` | PASS |
| 5.3 | `py test_phase17_acceptance.py` | EXPECTED FAIL: 3 known Phi-3 failures |
| 5.4 | `py observe_phase17_emergence.py --label phi3-case-c-diagnosis-v2 --seeds 7,13,42 --ticks 5000` | PASS, data generated |
| guard | `rg "sorted\\(self\\.personas\\)\\[0\\]|FOUNDER_LOYALTY_BONUS|founder_loyalty_applied|contact_via_persona_relationship|respawn_seed_group|_pick_seed_group"` | PASS (`NO_MATCH`) |

Acceptance failures observed:

- `phi3_grievance_pairs_resonate`: seed 13 ended with `grievance_pairs=0`.
- `grievance_propagate_natural_emergence`: seed 13 propagation lens remained `pairs=0`.
- `phi3_branch_lineage_chain`: total `uprising_branch=0` across all 3 seeds.

Probe output:

- `data/phase17_probe_phi3-case-c-diagnosis-v2/SUMMARY.md`
- `data/phase17_probe_phi3-case-c-diagnosis-v2/seed-*/chain.json`
- `data/phase17_probe_phi3-case-c-diagnosis-v2/seed-*/case_c_events.json`

## Primary Results

| metric | seed 7 | seed 13 | seed 42 | verdict |
|---|---:|---:|---:|---|
| uprising_event >= 1 | 17 | 11 | 13 | PASS |
| grievance_pairs_end >= 1 | 1 | 0 | 1 | FAIL |
| dom_share_end >= 0.50 | 60% | 100% | 67% | PASS |
| active_factions_end | 2 | 1 | 2 | FAIL overall |
| contact_pairs_end | 1 | 0 | 0 | FAIL overall |
| drift_ratio | 55% | 52% | 48% | active but insufficient |
| branch_factions_total | 0 | 0 | 0 | FAIL |

## H1-H5 Diagnosis

| hypothesis | seed 7 | seed 13 | seed 42 | diagnosis |
|---|---:|---:|---:|---|
| H1 no-contact uprising gate | 91 | 158 | 127 | PASS: no-contact blocks are frequent |
| H2a Phase A respawn blocked | 6/6 | 1/1 | 0/0 | PASS/N/A: all attempted Phase A respawns were blocked by free-resident shortage |
| H2b Phase B population shortage | 0 | 0 | 0 | FAIL: Phase B was not blocked by resident count |
| H2c fallback founder absorbed | 6/4 | 1/0 | 0/0 | PARTIAL: fallback creates founders, but survival is inconsistent and branch remains 0 |
| H3 minority boost active | 775 | 373 | 458 | PASS as signal: boost fires often, but does not produce branch/contact stability |
| H4 drift recovery active | 96 | 71 | 49 | PASS as signal: drift recovery occurs, but does not preserve resonance |
| H5 cross-faction lord emerged/collapsed | 0/0 | 0/0 | 0/0 | FAIL/NO DATA: this path did not naturally occur |
| H5a faction consolidated collapse | 0 | 0 | 0 | FAIL/NO DATA |
| H5b lord_id replaced collapse | 0 | 0 | 0 | FAIL/NO DATA |
| H5c lord persona missing collapse | 0 | 0 | 0 | FAIL/NO DATA |
| H5d delayed emergence | 0/0.00 | 0/0.00 | 0/0.00 | FAIL/NO DATA |

Active-faction snapshots are now correctly emitted every 500 ticks:

- seed 7: `500:3`, `1000:3`, `1500:3`, `2000:2`, `2500:1`, `3000:1`, `3500:1`, `4000:1`, `4500:1`, `5000:2`
- seed 13: `500:3`, `1000:3`, `1500:3`, `2000:3`, `2500:3`, `3000:3`, `3500:3`, `4000:3`, `4500:1`, `5000:1`
- seed 42: `500:3`, `1000:3`, `1500:3`, `2000:3`, `2500:2`, `3000:2`, `3500:2`, `4000:2`, `4500:2`, `5000:2`

All snapshots reported `cross_faction_lord_count=0`.

## Root Cause

The strongest root cause is not H5 cross-faction-lord collapse. H5 did not emerge at all in the current implementation/data path.

The dominant failure is a contact/resonance topology break:

- Uprisings naturally occur in all seeds, so the anger/grievance side is alive.
- No-contact skips are high (`91/158/127`), so many potential uprisings cannot branch or engage.
- Actual uprising outcomes remain `join_share=100%` and `branch_share=0%`, so the struggle path is being absorbed into existing factions.
- Respawn fallback can create founders, but it does not reliably create persistent contact-bearing minority structures.
- Drift recovery fires frequently, but it is not enough to maintain cross-faction grievance pairs or branch lineage.

In short: the system has pressure, drift, and respawn attempts, but it lacks a natural bridge that turns pressure into stable cross-faction contact and branch-producing conflict.

## Patch Candidates

Priority recommendation:

1. P1: Diagnose or design a natural contact persistence mechanism. It should be guide-layer/social topology, not SNN or hardcoded acceptance repair.
2. P2: Revisit branch path gating. A high-resonance faction with no contact currently records `uprising_skip_no_contact`; the next design should decide whether isolation can naturally become schism rather than silence.
3. P3: Rework respawn ecology only if P1/P2 are insufficient. Phase A free-resident shortage is real, but Phase B creation alone does not solve branch lineage.
4. P4: Deprioritize H5 for now. Cross-faction-lord pair telemetry is in place, but the current run produced zero emerged/collapsed events, so H5 is not the observed collapse path.

Constraints for any follow-up patch:

- Do not change `brain/**` or SNN neuron structure.
- Do not add sticky/floor/artificial propagation.
- Do not loosen acceptance.
- Preserve `FactionChangeSource` four-value contract.
- Keep all future fixes measurable through event telemetry before claiming PASS.
