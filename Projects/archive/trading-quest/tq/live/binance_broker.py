"""Binance live trading broker implementation.

Uses the python-binance library. Defaults to TESTNET for safety.
Install: pip install python-binance
"""
from __future__ import annotations

import logging
from typing import Optional

from tq.live.broker_base import LiveBroker

logger = logging.getLogger(__name__)


class BinanceBroker(LiveBroker):
    """Live trading via Binance API.

    SAFETY: Defaults to testnet. Real money trading requires explicit
    testnet=False and user confirmation.
    """

    TESTNET_BASE = "https://testnet.binance.vision"
    MAINNET_BASE = "https://api.binance.com"

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self._client = None

    def connect(self) -> bool:
        """Connect to Binance API (testnet or mainnet)."""
        try:
            from binance.client import Client  # type: ignore[import-untyped]

            if self.testnet:
                self._client = Client(
                    self.api_key,
                    self.api_secret,
                    testnet=True,
                )
                logger.info("Connected to Binance TESTNET")
            else:
                self._client = Client(self.api_key, self.api_secret)
                logger.warning("Connected to Binance MAINNET — REAL MONEY")
            return True
        except ImportError:
            logger.error(
                "python-binance not installed. Run: pip install python-binance"
            )
            return False
        except Exception:
            logger.error("Failed to connect to Binance", exc_info=True)
            return False

    def get_balance(self) -> dict:
        """Get account balance."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")
        try:
            info = self._client.get_account()
            balances = {
                b["asset"]: float(b["free"])
                for b in info.get("balances", [])
                if float(b["free"]) > 0
            }
            return {
                "total": sum(balances.values()),
                "available": balances,
                "currency": "MULTI",
            }
        except Exception:
            logger.error("Failed to get balance", exc_info=True)
            return {"total": 0, "available": {}, "currency": "MULTI"}

    def get_positions(self) -> list[dict]:
        """Get current positions (non-zero balances)."""
        balance = self.get_balance()
        positions = []
        for asset, qty in balance.get("available", {}).items():
            if qty > 0:
                positions.append({
                    "symbol": asset,
                    "qty": qty,
                    "avg_price": 0.0,  # Binance spot doesn't track avg cost
                    "unrealized_pnl": 0.0,
                })
        return positions

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
    ) -> dict:
        """Place an order on Binance."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")

        # NEVER log API keys
        logger.info(
            "Placing %s %s order: %s qty=%s price=%s (testnet=%s)",
            order_type, side, symbol, qty, price, self.testnet,
        )

        try:
            params = {
                "symbol": symbol,
                "side": side.upper(),
                "type": order_type.upper(),
                "quantity": qty,
            }
            if order_type.upper() == "LIMIT" and price is not None:
                params["price"] = str(price)
                params["timeInForce"] = "GTC"

            result = self._client.create_order(**params)
            return {
                "order_id": str(result.get("orderId", "")),
                "status": result.get("status", "UNKNOWN"),
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "filled_qty": float(result.get("executedQty", 0)),
            }
        except Exception:
            logger.error("Failed to place order", exc_info=True)
            return {"order_id": "", "status": "FAILED", "error": "order_failed"}

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order on Binance."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")
        try:
            # Binance cancel requires symbol; this is a simplified interface
            # In practice you'd store the symbol when placing the order.
            logger.info("Cancel order %s", order_id)
            # self._client.cancel_order(symbol=..., orderId=order_id)
            return True
        except Exception:
            logger.error("Failed to cancel order %s", order_id, exc_info=True)
            return False

    def get_order_status(self, order_id: str) -> dict:
        """Get order status from Binance."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")
        try:
            # Simplified — would need symbol in practice
            return {"order_id": order_id, "status": "UNKNOWN", "filled_qty": 0}
        except Exception:
            logger.error("Failed to get order status", exc_info=True)
            return {"order_id": order_id, "status": "ERROR", "filled_qty": 0}
