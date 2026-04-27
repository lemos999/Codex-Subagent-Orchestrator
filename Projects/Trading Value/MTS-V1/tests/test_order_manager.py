from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from strategy import MakerOrderRejected, OrderManager, TradeSide


def _fixed_now() -> datetime:
    return datetime(2026, 4, 24, 0, 0, 1, tzinfo=UTC)


def test_client_order_id_contract() -> None:
    manager = OrderManager(now_fn=_fixed_now)

    client_order_id = manager.client_order_id(
        symbol="BTC/USDT:USDT",
        state_from=1,
        state_to=2,
    )

    assert client_order_id == "mtsv1_BTC_USDT_USDT_12_1776988801000"


def test_maker_rejection_retry_3x() -> None:
    manager = OrderManager(now_fn=_fixed_now)
    attempts: list[dict[str, Any]] = []

    def create_order(request: dict[str, Any]) -> dict[str, Any]:
        attempts.append(request)
        raise MakerOrderRejected("post-only would be taker")

    with pytest.raises(MakerOrderRejected):
        manager.place_post_only_with_retry(
            create_order,
            symbol="BTC/USDT:USDT",
            side=TradeSide.LONG,
            amount=1.0,
            price=100.0,
            tick_size=0.5,
            state_from=1,
            state_to=2,
        )

    assert [attempt["attempt"] for attempt in attempts] == [1, 2, 3]
    assert [attempt["price"] for attempt in attempts] == [100.0, 99.5, 99.0]


def test_maker_rejection_retry_short_moves_price_up() -> None:
    manager = OrderManager(now_fn=_fixed_now)
    attempts: list[dict[str, Any]] = []

    def create_order(request: dict[str, Any]) -> dict[str, Any]:
        attempts.append(request)
        if len(attempts) == 1:
            raise RuntimeError("post only maker reject")
        return {"id": "accepted", "price": request["price"]}

    result = manager.place_post_only_with_retry(
        create_order,
        symbol="ETH/USDT:USDT",
        side=TradeSide.SHORT,
        amount=2.0,
        price=100.0,
        tick_size=0.25,
        state_from=1,
        state_to=2,
    )

    assert result == {"id": "accepted", "price": 100.25}
    assert [attempt["price"] for attempt in attempts] == [100.0, 100.25]
