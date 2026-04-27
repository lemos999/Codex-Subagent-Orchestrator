# Findings

## Scope
- Added reverse-spike pulse diagnostics to existing State2 telemetry.
- Updated `parity_reports/sol_diff_entry15.md` to show CVD delta, reverse threshold, reverse ratio, and reverse margin for matched exit timing residuals.
- Regenerated SOL artifact and Core5 reports.
- Did not change replay semantics, `strategy.py`, `strategy.pine`, or BTC artifact.

## SOL Reverse-Spike Residuals
The seven Python-early State2 residual rows are all reverse-spike sourced.

Unique early reverse-spike pulses:
- `2026-04-20T14:45:00Z` long: trades `64/65`, delta `-121376.0080`, threshold `121189.8383`, ratio `1.0015`, margin `-186.1697`, exit `1305m` early.
- `2026-04-13T06:15:00Z` short: trades `56/57`, delta `68821.0200`, threshold `52390.8597`, ratio `1.3136`, margin `16430.1603`, exit `390m` early.
- `2026-03-25T14:00:00Z` long: trades `29/30`, delta `-197422.1980`, threshold `178994.1598`, ratio `1.1030`, margin `-18428.0382`, exit `60m` early.
- `2026-04-23T17:00:00Z` long: trade `69`, delta `-123314.6250`, threshold `115195.3905`, ratio `1.0705`, margin `-8119.2345`, exit `30m` early.

## Interpretation
- The largest drift pair (`64/65`, `1305m` early) is a threshold-edge reverse spike at ratio `1.0015`.
- Two rows are same-bar/order candidates and one is entry-cycle drift, but the long-drift rows are not explained by same-bar ordering.
- HTF cross remains exonerated for the matched State2 residual subset.
- The next semantic experiment should test one reverse-spike pulse rule at a time: threshold slack/rounding, bar-close confirmation, or previous-bar pulse use.

## Semantic Equivalence
- Old and new SOL artifacts match exactly after stripping `state2_*` fields:
  - `old_rows=254 new_rows=254 stripped_equal=True`

## Gate Evidence
- Core5 baseline gate passed.
- BTC baseline remains unchanged:
  - entries `64/64`
  - exit timestamps `64/64`
  - exit price <= `0.15`: `62/64`
  - exit price <= `1.0`: `64/64`
  - SHA256 `BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D`
- SOL artifact SHA changed to `2E70E938E97C19E42D63F3464DCE913A7068D3F91999D3C0FF109A9639E3F559` because additional telemetry fields were added.

## Recommended Next Task
SOL reverse-spike threshold/confirmation experiment.

Run exactly one replay experiment first, preferably a threshold-edge guard or one-bar confirmation, then regenerate BTC/SOL/XRP Core5 reports and compare BTC baseline before considering promotion.

No ETH/BNB expansion and no live-ready claim.
