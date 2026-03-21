from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone

from ..core.models import EngineState, SymbolState, TradingState, TradeLifecycleState


# ---------------------------------------------------------------------------
# StateSnapshot
# ---------------------------------------------------------------------------

@dataclass
class StateSnapshot:
    version: int
    timestamp: str  # ISO 8601
    state: TradingState


# ---------------------------------------------------------------------------
# StateStore — JSON file-based persistence
# ---------------------------------------------------------------------------

class StateStore:
    """File-based state persistence using Pydantic JSON serialization.

    Saves TradingState as JSON. Supports versioned snapshots for recovery.
    """

    def __init__(self, base_dir: str = ".trading_state") -> None:
        """Create state store. base_dir is the directory for state files."""
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    # -- helpers -------------------------------------------------------------

    def _snapshot_path(self, version: int) -> str:
        return os.path.join(self.base_dir, f"snapshot_{version}.json")

    def _latest_path(self) -> str:
        return os.path.join(self.base_dir, "latest.json")

    def _next_version(self) -> int:
        versions = self.list_versions()
        return (max(versions) + 1) if versions else 1

    # -- public API ----------------------------------------------------------

    def save(self, state: TradingState) -> int:
        """Save state snapshot. Returns version number.

        Writes to: {base_dir}/snapshot_{version}.json
        Also writes: {base_dir}/latest.json (copy)
        """
        version = self._next_version()
        ts = datetime.now(timezone.utc).isoformat()

        payload = {
            "version": version,
            "timestamp": ts,
            "state": json.loads(state.model_dump_json()),
        }

        snapshot_file = self._snapshot_path(version)
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        # latest.json — always a plain copy (symlinks unreliable on Windows)
        shutil.copy2(snapshot_file, self._latest_path())

        return version

    def load_latest(self) -> StateSnapshot | None:
        """Load most recent snapshot. Returns None if no snapshots exist."""
        latest = self._latest_path()
        if not os.path.exists(latest):
            return None
        return self._read_snapshot(latest)

    def load_version(self, version: int) -> StateSnapshot | None:
        """Load specific version."""
        path = self._snapshot_path(version)
        if not os.path.exists(path):
            return None
        return self._read_snapshot(path)

    def list_versions(self) -> list[int]:
        """List all available snapshot versions."""
        versions: list[int] = []
        if not os.path.isdir(self.base_dir):
            return versions
        for name in os.listdir(self.base_dir):
            if name.startswith("snapshot_") and name.endswith(".json"):
                try:
                    v = int(name.removeprefix("snapshot_").removesuffix(".json"))
                    versions.append(v)
                except ValueError:
                    continue
        versions.sort()
        return versions

    # -- internal ------------------------------------------------------------

    def _read_snapshot(self, path: str) -> StateSnapshot:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        state = TradingState.model_validate(data["state"])
        return StateSnapshot(
            version=data["version"],
            timestamp=data["timestamp"],
            state=state,
        )


# ---------------------------------------------------------------------------
# Recovery helpers (spec v2 §14)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RecoveryResult:
    success: bool
    engine_state: EngineState  # READY, DEGRADED, or HALTED
    mismatches: list[str]  # descriptions of state differences
    actions_taken: list[str]  # recovery actions


def check_state_consistency(
    local_state: TradingState,
    exchange_positions: dict[str, dict],  # {symbol: {side, qty, entry_price}}
    exchange_orders: dict[str, list[dict]],  # {symbol: [orders]}
) -> RecoveryResult:
    """§14.1 재기동 절차 step 4-7:

    Compare local state with exchange reality:
    - Local FLAT but exchange has position -> HALTED
    - Local OPEN but exchange has no position -> HALTED
    - Local has stop but exchange doesn't -> HALTED (missing protection)
    - Qty mismatch -> DEGRADED
    - States match -> READY
    """
    mismatches: list[str] = []
    actions: list[str] = []
    worst = EngineState.READY

    all_symbols = set(local_state.symbols.keys()) | set(exchange_positions.keys())

    for symbol in sorted(all_symbols):
        local_sym: SymbolState | None = local_state.symbols.get(symbol)
        ex_pos = exchange_positions.get(symbol)
        ex_orders = exchange_orders.get(symbol, [])

        local_is_flat = (
            local_sym is None
            or local_sym.lifecycle == TradeLifecycleState.FLAT
            or local_sym.lifecycle == TradeLifecycleState.COOLDOWN
        )
        local_is_open = not local_is_flat

        exchange_has_position = (
            ex_pos is not None and float(ex_pos.get("qty", 0)) != 0.0
        )

        # Case 1: Local FLAT but exchange has position
        if local_is_flat and exchange_has_position:
            msg = (
                f"{symbol}: local state is FLAT but exchange has position "
                f"(side={ex_pos.get('side')}, qty={ex_pos.get('qty')})"
            )
            mismatches.append(msg)
            worst = EngineState.HALTED

        # Case 2: Local OPEN but exchange has no position
        elif local_is_open and not exchange_has_position:
            msg = (
                f"{symbol}: local state is OPEN "
                f"(lifecycle={local_sym.lifecycle}) but exchange has no position"
            )
            mismatches.append(msg)
            worst = EngineState.HALTED

        # Cases that only apply when both sides agree a position exists
        elif local_is_open and exchange_has_position and local_sym is not None:
            # Case 3a: Local OPEN state is missing stop_price entirely
            open_stages = (
                TradeLifecycleState.OPEN_STAGE0,
                TradeLifecycleState.OPEN_STAGE1,
                TradeLifecycleState.OPEN_STAGE2,
            )
            if local_sym.lifecycle in open_stages and local_sym.stop_price is None:
                msg = (
                    f"{symbol}: local OPEN state missing stop_price "
                    f"(lifecycle={local_sym.lifecycle}) — missing protection"
                )
                mismatches.append(msg)
                worst = EngineState.HALTED

            # Case 3b: Local has stop but exchange doesn't have a stop order
            elif local_sym.stop_price is not None:
                has_stop_order = any(
                    o.get("type", "").upper() in ("STOP_MARKET", "STOP", "STOP_LOSS")
                    for o in ex_orders
                )
                if not has_stop_order:
                    msg = (
                        f"{symbol}: local has stop_price={local_sym.stop_price} "
                        f"but exchange has no stop order — missing protection"
                    )
                    mismatches.append(msg)
                    worst = EngineState.HALTED

            # Case 4: Qty mismatch
            ex_qty = float(ex_pos.get("qty", 0))
            local_qty = float(local_sym.filled_qty or 0)
            if local_qty != 0.0 and abs(local_qty - abs(ex_qty)) > 1e-9:
                msg = (
                    f"{symbol}: qty mismatch — "
                    f"local={local_qty}, exchange={abs(ex_qty)}"
                )
                mismatches.append(msg)
                if worst != EngineState.HALTED:
                    worst = EngineState.DEGRADED
                actions.append(f"{symbol}: flagged qty mismatch for manual review")

    if not mismatches:
        actions.append("all symbols consistent — engine READY")

    return RecoveryResult(
        success=(worst == EngineState.READY),
        engine_state=worst,
        mismatches=mismatches,
        actions_taken=actions,
    )
