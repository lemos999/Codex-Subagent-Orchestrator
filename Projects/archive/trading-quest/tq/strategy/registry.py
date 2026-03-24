"""Strategy registry -- maps names to strategy classes."""
from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Optional

from tq.strategy.base import BaseStrategy

logger = logging.getLogger(__name__)

_registry: dict[str, type[BaseStrategy]] = {}


def strategy(name: str):
    """Decorator to register a strategy class."""
    def decorator(cls: type[BaseStrategy]):
        register(name, cls)
        return cls
    return decorator


def register(name: str, cls: type[BaseStrategy]) -> None:
    """Register a strategy class by name."""
    _registry[name] = cls
    logger.debug("Registered strategy: %s -> %s", name, cls.__name__)


def get(name: str) -> type[BaseStrategy]:
    """Get a strategy class by name."""
    if name not in _registry:
        auto_discover()
    if name not in _registry:
        raise KeyError(f"Unknown strategy: {name}")
    return _registry[name]


def get_strategy(name: str) -> BaseStrategy:
    """Get an instantiated strategy by name."""
    cls = get(name)
    return cls()


def list_all() -> list[str]:
    """List all registered strategy names."""
    auto_discover()
    return sorted(_registry.keys())


def get_all() -> dict[str, type[BaseStrategy]]:
    """Get all registered strategies."""
    auto_discover()
    return dict(_registry)


def auto_discover() -> None:
    """Auto-discover and import all strategy modules in tq.strategy.builtin."""
    try:
        import tq.strategy.builtin as builtin_pkg
        for importer, modname, ispkg in pkgutil.iter_modules(builtin_pkg.__path__):
            try:
                importlib.import_module(f"tq.strategy.builtin.{modname}")
            except Exception as e:
                logger.warning("Failed to import strategy %s: %s", modname, e)
    except ImportError:
        logger.debug("No builtin strategies package found")

    # Also discover journal-based strategies (adaptive)
    try:
        importlib.import_module("tq.journal.adaptive")
    except Exception as e:
        logger.debug("Failed to import journal adaptive strategy: %s", e)
