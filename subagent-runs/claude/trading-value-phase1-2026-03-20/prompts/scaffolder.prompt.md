# Scaffolder Prompt

Create project scaffolding for Trading Value under `Projects/Trading Value/`:
- pyproject.toml (Python 3.12+, hatchling, pydantic/pandas/ccxt/numpy + pytest/hypothesis dev deps)
- Directory structure: src/trading_value/{core,adapters,infra}/, tests/
- config/default.toml with all strategy parameters from spec v2
- __init__.py files (root with version, others with comment)
