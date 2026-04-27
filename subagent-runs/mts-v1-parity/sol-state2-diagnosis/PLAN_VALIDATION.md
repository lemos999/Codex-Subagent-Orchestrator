# Plan Validation

## Validator A
Status: CONDITIONAL

Required changes:
- Add cause-axis diagnostics beyond early/late timing.
- Specify verification command cwd.
- Define evidence criteria for selecting exactly one next fix candidate.
- Record BTC metrics and SHA in final findings.

## Validator B
Status: CONDITIONAL

Required changes:
- Explicitly limit SOL diagnosis to common-window matched rows.
- Add abort trigger evidence buckets.
- Base `FINDINGS.md` candidate on trigger evidence, not early/late timing alone.
- Keep docs/status updates minimal and avoid live-ready claims.

## Watchdog
Status: CONDITIONALLY ALLOW

Implementation may proceed after both validator requirements are reflected in PLAN/spec. Prohibited changes remain:
- `offline_replay.py`
- `strategy.py`
- `strategy.pine`
- `samples/`
- `runs/`

## Resolution
PLAN/spec were updated to include common-window row selection, cause-axis buckets, cwd for verification commands, candidate-selection evidence requirements, and BTC metric/SHA evidence in final findings.
