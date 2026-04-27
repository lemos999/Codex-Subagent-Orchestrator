from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from strategy import TradeLogger


def test_null_policy(tmp_path: Path) -> None:
    logger = TradeLogger(
        tmp_path,
        now_fn=lambda: datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
    )

    path = logger.append(
        {
            "ts": "2026-04-24T01:00:00+00:00",
            "symbol": "BTC/USDT:USDT",
            "event": "TP_B",
            "runner_exit_price": "",
        }
    )

    raw = path.read_text(encoding="utf-8").strip()
    event = json.loads(raw)
    assert path.name == "trades_2026-04-24.jsonl"
    assert event["runner_exit_price"] is None
    assert event["runner_exit_ts"] is None
    assert event["evasion_reason"] is None
    assert event["hard_sl_price"] is None


def test_append_uses_current_date_when_ts_missing(tmp_path: Path) -> None:
    logger = TradeLogger(
        tmp_path,
        now_fn=lambda: datetime(2026, 4, 25, 0, 30, tzinfo=UTC),
    )

    path = logger.append({"symbol": "ETH/USDT:USDT", "event": "ENTRY_L1"})

    event = json.loads(path.read_text(encoding="utf-8"))
    assert path.name == "trades_2026-04-25.jsonl"
    assert event["ts"] == "2026-04-25T00:30:00+00:00"
