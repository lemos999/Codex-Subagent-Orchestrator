# Phase Checklist

## Ordered Phases

- [ ] scan
- [ ] plan
- [ ] implement
- [ ] verify
- [ ] review

## Pause Points

- none

## Known Return Edges

- verify -> fix when an approved bounded repair loop opens
- review -> fix when an approved bounded repair loop opens
- verify/review -> plan when the next safe step causes a material plan change
- verify/review -> scan when the task boundary was misunderstood

## Optional Repair Loop

- add `fix`, `re-verify`, and `re-review` only when a bounded repair loop is actually opened
