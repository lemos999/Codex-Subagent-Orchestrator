"""Script engine -- load and run user-defined strategy scripts."""
from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from tq.config import SCRIPTS_DIR
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import register

logger = logging.getLogger(__name__)

SCRIPT_TEMPLATE = '''"""Custom strategy: {name}

Auto-generated template. Modify decide() to implement your logic.
"""
import pandas as pd
from tq.strategy.base import BaseStrategy


class {class_name}(BaseStrategy):
    name = "{name}"
    description = "Custom strategy: {name}"

    def decide(self, data: pd.DataFrame, portfolio) -> list[dict]:
        """Return a list of signal dicts.

        Each signal: {{"symbol": str, "side": "BUY"|"SELL", "qty": float, ...}}
        """
        signals = []
        # Your logic here
        # close = data["close"]
        # if some_condition:
        #     signals.append({{"symbol": "AAPL", "side": "BUY", "qty": 1}})
        return signals
'''


class ScriptStrategy(BaseStrategy):
    """Wraps a user-defined strategy script."""

    def __init__(self, name: str, module: Any):
        self.name = name
        self._module = module
        self._strategy: Optional[BaseStrategy] = None

        # Find the strategy class in the module
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if (isinstance(obj, type) and issubclass(obj, BaseStrategy)
                    and obj is not BaseStrategy):
                self._strategy = obj()
                break

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if self._strategy:
            return self._strategy.decide(data, portfolio)
        return []

    def on_candle(self, candle: dict, portfolio: Any) -> list[dict]:
        if self._strategy and hasattr(self._strategy, "on_candle"):
            return self._strategy.on_candle(candle, portfolio)
        return []


def load_all_scripts(scripts_dir: Optional[Path] = None) -> list[ScriptStrategy]:
    """Load all .py scripts from the scripts directory."""
    path = scripts_dir or SCRIPTS_DIR
    if not path.exists():
        logger.debug("Scripts directory does not exist: %s", path)
        return []

    loaded = []
    for script_file in sorted(path.glob("*.py")):
        if script_file.name.startswith("_"):
            continue
        try:
            name = script_file.stem
            spec = importlib.util.spec_from_file_location(
                f"tq.strategy.scripts.{name}", script_file
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                strategy = ScriptStrategy(name, module)
                register(name, type(strategy))
                loaded.append(strategy)
                logger.info("Loaded script strategy: %s", name)
        except Exception as e:
            logger.warning("Failed to load script %s: %s", script_file.name, e)

    return loaded


def create_script_template(name: str, scripts_dir: Optional[Path] = None) -> Path:
    """Create a new strategy script from template."""
    path = scripts_dir or SCRIPTS_DIR
    path.mkdir(parents=True, exist_ok=True)

    class_name = "".join(word.capitalize() for word in name.split("_")) + "Strategy"
    content = SCRIPT_TEMPLATE.format(name=name, class_name=class_name)

    script_path = path / f"{name}.py"
    script_path.write_text(content, encoding="utf-8")
    logger.info("Created strategy template: %s", script_path)
    return script_path
