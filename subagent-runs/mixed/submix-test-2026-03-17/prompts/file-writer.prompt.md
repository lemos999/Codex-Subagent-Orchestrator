You operate under the shared contract in AGENTS.md at the workspace root.

## Contract

**Task**: Create a file at tests/artifacts/submix-test.txt containing exactly "Submix mixed engine test - 2026-03-17"

**Inspect first**:
- tests/artifacts/ (check if directory exists)

**Writable scope**:
- tests/artifacts/submix-test.txt (create)

**Validation**:
1. File exists at tests/artifacts/submix-test.txt
2. File contains exactly "Submix mixed engine test - 2026-03-17"
3. No other files were created or modified

**Return**:
- What changed (files, key decisions)
- Validation results (pass/fail per check)
- Assumptions made
- Remaining uncertainty

**Stop condition**: Create the single file only. Do not expand scope.
