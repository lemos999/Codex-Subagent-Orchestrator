from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass, fields
from datetime import datetime


# ---------------------------------------------------------------------------
# JournalEntry — every field from §15 + §13 log design
# ---------------------------------------------------------------------------

@dataclass
class JournalEntry:
    timestamp: datetime
    symbol: str
    event_type: str
    engine_state: str
    risk_gate: str
    regime_state: str
    mode_state: str
    setup_state: str
    trade_lifecycle_state: str
    setup_version: int
    transition_from: str
    transition_to: str
    transition_reason: str
    entry_price: float | None = None
    stop_price: float | None = None
    tp_prices: list[float] | None = None
    active_zone: str | None = None
    risk_pct: float | None = None
    rr_to_tp1: float | None = None
    volume_condition: str | None = None
    exchange_position_qty: float | None = None
    exchange_open_order_count: int | None = None
    pnl_realized: float | None = None
    pnl_unrealized: float | None = None
    reason_enter: str | None = None
    reason_skip: str | None = None
    reason_exit: str | None = None
    allowed_setups: list[str] | None = None
    position_state: str | None = None  # maps to trade_lifecycle_state but with §15 naming


# ---------------------------------------------------------------------------
# DecisionJournal — append-only journal with query + export
# ---------------------------------------------------------------------------

class DecisionJournal:
    """Append-only decision journal. Records every state transition and decision.

    Supports both in-memory buffer and file-based persistence.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        self.entries: list[JournalEntry] = []
        self.output_dir = output_dir
        if self.output_dir is not None:
            os.makedirs(self.output_dir, exist_ok=True)

    # -- core ----------------------------------------------------------------

    def log(self, entry: JournalEntry) -> None:
        """Append entry to journal. If output_dir set, also write to file."""
        self.entries.append(entry)

        if self.output_dir is not None:
            self._persist(entry)

    # -- query ---------------------------------------------------------------

    def query(
        self,
        symbol: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[JournalEntry]:
        """Query journal entries with filters."""
        results = self.entries

        if symbol is not None:
            results = [e for e in results if e.symbol == symbol]
        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]

        # Return the *last* `limit` entries (most recent first when sliced)
        return results[-limit:]

    # -- export --------------------------------------------------------------

    def export_csv(self, path: str) -> None:
        """Export all entries to CSV."""
        fieldnames = [f.name for f in fields(JournalEntry)]
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for entry in self.entries:
                row = self._entry_to_flat_dict(entry)
                writer.writerow(row)

    def export_jsonl(self, path: str) -> None:
        """Export all entries as JSONL (one JSON object per line)."""
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            for entry in self.entries:
                line = json.dumps(
                    self._entry_to_serializable(entry),
                    ensure_ascii=False,
                    default=str,
                )
                f.write(line + "\n")

    # -- internal helpers ----------------------------------------------------

    @staticmethod
    def _entry_to_serializable(entry: JournalEntry) -> dict:
        """Convert entry to a JSON-safe dict."""
        d = asdict(entry)
        # datetime -> ISO string
        if isinstance(d.get("timestamp"), datetime):
            d["timestamp"] = d["timestamp"].isoformat()
        return d

    @staticmethod
    def _entry_to_flat_dict(entry: JournalEntry) -> dict:
        """Convert entry to a flat dict suitable for CSV (lists -> JSON strings)."""
        d = asdict(entry)
        if isinstance(d.get("timestamp"), datetime):
            d["timestamp"] = d["timestamp"].isoformat()
        # Flatten list fields to JSON strings for CSV
        if d.get("tp_prices") is not None:
            d["tp_prices"] = json.dumps(d["tp_prices"])
        return d

    def _persist(self, entry: JournalEntry) -> None:
        """Append a single entry to the daily JSONL file."""
        assert self.output_dir is not None
        date_str = entry.timestamp.strftime("%Y-%m-%d")
        path = os.path.join(self.output_dir, f"journal_{date_str}.jsonl")
        line = json.dumps(
            self._entry_to_serializable(entry),
            ensure_ascii=False,
            default=str,
        )
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
