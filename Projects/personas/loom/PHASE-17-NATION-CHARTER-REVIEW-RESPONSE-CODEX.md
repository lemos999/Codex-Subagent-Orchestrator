# Phi-4 Nation Charter Draft Review Response - Codex

Date: 2026-05-04
Reviewer: Codex (GPT)
Reviewed Material: Phase 0-3 outputs (Intake / Charter / Component Map / Decision Cards)
Verdict: APPROVE_WITH_NOTES

## Checklist Results

- C1. Three-layer goal alignment: PASS
  The Phase 1 Charter connects the loom ultimate goal, Phase 17 Land -> Faction -> Struggle -> Nation chain, and Phi-4's specific role as a nation-emergence measurement/definition layer. The Nation STUB also frames nation emergence as a threshold phenomenon from distribution asymmetry and social stability, not a top-down declaration.

- C2. SNN emergence priority: PASS
  The first-wave Decision Cards (SIS, CPCM, P5R) are read-only telemetry / API-surface work. Core mechanisms (FMR, NDP, LRT) are separated as user-approval items. This preserves the "observe and measure first" direction.

- C3. Axis C guardrails: PASS_WITH_NOTE
  The STUB OQ 7-a~e and the V3 report explicitly guard against axis-C false correction. FMR/NDP/LRT are not smuggled in as non-core work. Note: the review request references `PHASE-14B-A-AXIS-A-REJECTION-CASE-C-DIAGNOSIS-SPEC.md`, but that file was not found in the current workspace.

- C4. LOOM-DIRECTION section 3.7 six-step chain: PASS
  SIS and CPCM cite natural measurement, distribution analysis, coupling candidates, quantile candidates, cross-check, and closure reporting. Each implementation spec should still restate this chain as acceptance criteria.

- C5. Core gate classification: PASS
  SIS/CPCM/P5R are correctly classified as non-core. FMR/NDP/LRT are correctly treated as core because they can alter state, acceptance, or social mechanism behavior.

- C6. Preservation constraints: PASS
  The draft preserves destructive-nine, the five safety constants, BOOST=0.20, and the regression-gate contract. No Decision Card proposes changing those constraints.

- C7. Downstream compatibility: PASS
  P5R is read-only and one-way from later phases back to earlier layers. Rejecting or deferring read-write API behavior is the correct safety posture.

- C8. OQ 1-6 to six components mapping: PASS
  OQ1=SIS, OQ2=FMR, OQ3=NDP, OQ4=CPCM, OQ5=LRT, and OQ6=P5R. The mapping is complete and not meaningfully duplicated.

- C9. V3 data usability: WARN
  The V3 report provides usable figures: cross_faction_lord_pair_emerged=22/23/19, conflict_pair_at_20000=1/1/1, and active_factions_end=2/2/2. Raw JSON is present. However, `SUMMARY.md` and seed summary files still have mojibake, and the SIS `dom_share window=720 >= 0.55` claim should be re-derived from raw data in the SIS spec.

- C10. False-correction loop avoidance: PASS
  The plan avoids changing mechanisms to force acceptance. The V3 result is interpreted as a measurement-definition dimensional difference, not a mechanism defect. Territory cross-propagation strengthening is treated as a rejected axis-C style move.

## Findings

### Finding 1: Missing Axis A rejection source path

- Location: Review Request section 4, input material item 5
- Symptom: `PHASE-14B-A-AXIS-A-REJECTION-CASE-C-DIAGNOSIS-SPEC.md` was not found under `Projects/personas/loom`.
- Evidence: `rg --files | rg "AXIS|REJECTION"` did not return that file. The axis A/B rejection rationale is still reviewable through `PHASE-17-STRUGGLE-CLOSURE-REPORT-V2.md` and `PHASE-17-NATION-CHARTER-STUB.md`.
- Recommendation: Correct the file path, or add a stable source document for the axis A rejection evidence and update the review request input list.
- Severity: MINOR

### Finding 2: V3 SUMMARY mojibake weakens human review traceability

- Location: `data/phase17_probe_phi3-case-c-diagnosis-v3/SUMMARY.md` and seed `summary.md` files
- Symptom: Human-readable Markdown summaries are garbled. The raw JSON and V3 report are usable, but external reviewers cannot rely on the summary files directly.
- Evidence: `PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md` section 9 also records the mojibake issue.
- Recommendation: Either run a separate summary encoding hotfix before Nation implementation specs, or make raw JSON / `case_c_events.json` the canonical input for SIS and CPCM specs.
- Severity: MINOR

### Finding 3: Do not freeze the SIS threshold during first implementation

- Location: DC-1 SIS, entry trigger `dom_share window=720 >= 0.55`
- Symptom: The threshold is acceptable as a phase-entry signal, but freezing it as a mechanism or final sovereignty score too early would resemble an axis-C false-correction route.
- Evidence: LOOM-DIRECTION section 3.7 requires natural measurement -> distribution analysis -> coupling candidate -> quantile candidate -> three-engine cross-check -> closure report. The review request itself rejects a fixed `0.6*dom_share + 0.4*member_share` formula as top-down.
- Recommendation: The first SIS spec should be a read-only distribution extractor. Treat `sovereignty_score` as a candidate diagnostic field only. Do not freeze thresholds until P50/P67/P75 are re-derived from raw V3 data and cross-checked.
- Severity: MINOR

## Overall Assessment

The Phi-4 Nation Charter draft is aligned with loom's three-layer goal and the natural-emergence principle. The safest next step is to proceed with the three non-core specs first: SIS, CPCM, and P5R.

The three core cards, FMR/NDP/LRT, should remain blocked behind explicit user approval and later spec-review or three-engine cross-check. They are valid design questions, but they are mechanism-bearing and should not be implemented as part of the first non-core wave.

## Optional Recommendations

- SIS should first output a windowed distribution table for dom_share, member_share, conflict_pair, and cross_faction_lord_count.
- CPCM should read PersonaBrain / charter primitive state only. It must not inject or converge primitives.
- P5R should freeze interface shape only; body semantics should be revisited after SIS/CPCM/NDP/LRT/FMR are more stable.
- FMR/NDP/LRT should go through `/spec-review` or a three-engine cross-check before implementation.

