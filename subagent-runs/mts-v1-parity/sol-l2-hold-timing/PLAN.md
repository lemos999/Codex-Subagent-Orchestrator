# Plan

## Goal

Test whether SOL's Python-early `STATE_2_ABORT` reverse-spike exits are caused by replay aborting too soon after L2 fill recognition.

## Candidate

Add a replay-only `state2_reverse_min_minutes_since_l2` option:

- Default `0.0` preserves accepted profile behavior.
- Reverse-spike State2 exits are suppressed only while the latest L2 fill is younger than the configured window.
- HTF-cross State2 exits remain active.

## Promotion Rule

Promote only if SOL common-window entry and exit timestamp metrics improve without increasing missing-cycle drift and while BTC/Core5 baseline remains unchanged.

## Verification

- Focused replay/diff tests.
- SOL probe reports for `60` and `300` minutes.
- Full MTS-V1 tests.
- Targeted `ruff` and `py_compile`.
- Core5 `--gate baseline`.
