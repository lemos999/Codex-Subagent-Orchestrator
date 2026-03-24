You operate under the shared contract in AGENTS.md at the workspace root.

## Contract

**Task**: Create a file at tests/artifacts/evidence-test.txt containing exactly "Evidence recording test - 2026-03-16"

**Inspect first**:
- tests/artifacts/ (check if directory exists)

**Writable scope**:
- tests/artifacts/evidence-test.txt (create)

**Validation**:
1. File exists at tests/artifacts/evidence-test.txt
2. File contains exactly "Evidence recording test - 2026-03-16"
3. No other files were created or modified

**Return**:
- What changed (files, key decisions)
- Validation results (pass/fail per check)
- Assumptions made
- Remaining uncertainty

**Stop condition**: Create the single file only. Do not expand scope.
