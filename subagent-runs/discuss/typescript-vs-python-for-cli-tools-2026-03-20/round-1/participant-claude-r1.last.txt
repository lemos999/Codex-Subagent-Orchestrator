## TypeScript vs Python for CLI tools

**Position**: TypeScript is the better choice when the CLI is part of a Node.js ecosystem; Python wins for standalone tools with heavy data/system dependencies.

**Reasoning**:
- If the CLI drives or wraps Node-based tooling (bundlers, linters, SDK wrappers), TypeScript shares the runtime, types, and package graph — no language boundary to cross
- TypeScript's static types catch argument-parsing bugs and option-shape mismatches at compile time, which matters for CLI contracts
- Python's stdlib (`argparse`, `pathlib`, `subprocess`) is richer out of the box for system scripting; `pip` installs are simpler than `npx`/global `npm` for non-JS users
- Startup latency: Python is generally faster to first-byte for small scripts; Node.js has higher cold-start overhead

**Concerns**:
- TypeScript CLI distribution is painful — users need Node installed, `ts-node` or a build step, or a bundled `.js` file; Python ships a single `.py` or a wheel
- Windows path resolution adds friction in both (`.cmd` suffix for npm tools, `py` vs `python3` for Python)
- Python's lack of types-by-default leads to fragile large CLIs unless you adopt `mypy` consistently

**Recommendation**: Use TypeScript if the CLI is consumed by developers already in a Node/JS project. Use Python for general-purpose sysadmin/data tools targeting a broader or non-JS audience. For this project specifically (a Node-based subagent orchestrator), TypeScript is the obvious fit — the launcher is already TypeScript and sharing types across the boundary would be costly to give up.

[POSITION: TypeScript for Node-ecosystem CLIs; Python for standalone system/data tools — match the runtime to the consumer, not personal preference]