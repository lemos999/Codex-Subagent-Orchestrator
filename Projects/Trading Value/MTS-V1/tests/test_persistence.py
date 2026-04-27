from __future__ import annotations

from pathlib import Path

from strategy import PersistenceManager, StartupReconciliation


class _Exchange:
    def __init__(self, *, positions: list[dict[str, object]], orders: list[dict[str, object]]) -> None:
        self.positions = positions
        self.orders = orders

    def fetch_positions(self, symbols: list[str]) -> list[dict[str, object]]:
        assert symbols == ["BTC/USDT:USDT"]
        return self.positions

    def fetch_open_orders(self, symbol: str) -> list[dict[str, object]]:
        assert symbol == "BTC/USDT:USDT"
        return self.orders


def test_persistence_save_load_round_trip_and_slug(tmp_path: Path) -> None:
    manager = PersistenceManager(tmp_path)
    state = {
        "symbol": "BTC/USDT:USDT",
        "state": 2,
        "client_order_ids": {"L1": "order_1"},
    }

    path = manager.save_state("BTC/USDT:USDT", state)
    loaded = manager.load_state("BTC/USDT:USDT")

    assert manager.symbol_slug("BTC/USDT:USDT") == "BTC_USDT_USDT"
    assert path.name == "state_BTC_USDT_USDT.json"
    assert loaded == state


def test_startup_reconciliation_returns_2_on_position_mismatch(tmp_path: Path) -> None:
    manager = PersistenceManager(tmp_path)
    manager.save_state(
        "BTC/USDT:USDT",
        {
            "symbol": "BTC/USDT:USDT",
            "state": 3,
            "client_order_ids": {},
        },
    )
    exchange = _Exchange(positions=[], orders=[])

    code = StartupReconciliation(manager, exchange).reconcile_symbol("BTC/USDT:USDT")

    assert code == 2


def test_startup_reconciliation_does_not_auto_mutate_state(tmp_path: Path) -> None:
    manager = PersistenceManager(tmp_path)
    state = {
        "symbol": "BTC/USDT:USDT",
        "state": 3,
        "client_order_ids": {"L1": "filled_l1", "HARD_SL": "missing_hsl"},
    }
    manager.save_state("BTC/USDT:USDT", state)
    exchange = _Exchange(positions=[{"contracts": 1}], orders=[])

    code = StartupReconciliation(manager, exchange).reconcile_symbol("BTC/USDT:USDT")

    assert code == 2
    assert manager.load_state("BTC/USDT:USDT") == state


def test_startup_reconciliation_flags_extra_exchange_order(tmp_path: Path) -> None:
    manager = PersistenceManager(tmp_path)
    manager.save_state(
        "BTC/USDT:USDT",
        {
            "symbol": "BTC/USDT:USDT",
            "state": 0,
            "client_order_ids": {},
        },
    )
    exchange = _Exchange(positions=[], orders=[{"clientOrderId": "stale_live_order"}])

    code = StartupReconciliation(manager, exchange).reconcile_symbol("BTC/USDT:USDT")

    assert code == 2


def test_startup_reconciliation_allows_pending_order_without_position(tmp_path: Path) -> None:
    manager = PersistenceManager(tmp_path)
    manager.save_state(
        "BTC/USDT:USDT",
        {
            "symbol": "BTC/USDT:USDT",
            "state": 1,
            "client_order_ids": {"L1": "pending_l1"},
        },
    )
    exchange = _Exchange(positions=[], orders=[{"clientOrderId": "pending_l1"}])

    code = StartupReconciliation(manager, exchange).reconcile_symbol("BTC/USDT:USDT")

    assert code == 0


def test_startup_reconciliation_does_not_require_filled_entry_orders(tmp_path: Path) -> None:
    manager = PersistenceManager(tmp_path)
    manager.save_state(
        "BTC/USDT:USDT",
        {
            "symbol": "BTC/USDT:USDT",
            "state": 3,
            "client_order_ids": {
                "L1": "filled_l1",
                "L2": "filled_l2",
                "L3": "filled_l3",
                "HARD_SL": "open_hsl",
            },
        },
    )
    exchange = _Exchange(
        positions=[{"contracts": 1}],
        orders=[{"clientOrderId": "open_hsl"}],
    )

    code = StartupReconciliation(manager, exchange).reconcile_symbol("BTC/USDT:USDT")

    assert code == 0
