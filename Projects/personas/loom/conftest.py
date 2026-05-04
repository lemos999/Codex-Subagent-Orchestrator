"""pytest configuration for Projects/personas/loom.

Registers project-level markers. No fixtures, no autouse hooks.
"""
from __future__ import annotations


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: long-running or performance-heavy tests excluded from default run; "
        "use `-m slow` to include only slow, or omit `-m` filter to run all.",
    )
