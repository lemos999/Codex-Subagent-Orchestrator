from __future__ import annotations

from dataclasses import dataclass
from math import floor

from strategy import AppConfig


DEFAULT_LIQUIDATION_BUFFER = 0.20
DEFAULT_FEES_SLIPPAGE = 0.01


@dataclass(slots=True, frozen=True)
class SymbolLeverageCap:
    symbol: str
    mmr: float | None
    raw_cap: int | None
    effective_leverage: int | None


@dataclass(slots=True, frozen=True)
class RiskGateDecision:
    allows_new_signals: bool
    failures: tuple[str, ...]
    leverage_caps: tuple[SymbolLeverageCap, ...]
    daily_pnl_pct: float
    daily_max_loss_pct: float


def effective_leverage(
    *,
    user_leverage: int,
    mmr: float,
    buffer: float = DEFAULT_LIQUIDATION_BUFFER,
    fees_slippage: float = DEFAULT_FEES_SLIPPAGE,
) -> int:
    if user_leverage < 1:
        raise ValueError("user_leverage must be >= 1")
    if mmr < 0.0:
        raise ValueError("mmr must be >= 0")
    denominator = buffer + fees_slippage + mmr
    if denominator <= 0.0:
        raise ValueError("buffer + fees_slippage + mmr must be positive")
    raw_cap = floor(1.0 / denominator)
    return max(1, min(user_leverage, raw_cap))


def evaluate_risk_gate(
    *,
    config: AppConfig,
    symbols: list[str],
    daily_pnl_pct: float = 0.0,
    require_mmr: bool = True,
) -> RiskGateDecision:
    failures: list[str] = []
    leverage_caps: list[SymbolLeverageCap] = []
    daily_loss_floor = -abs(config.risk.daily_max_loss_pct)
    if daily_pnl_pct <= daily_loss_floor:
        failures.append(
            f"daily max-loss reached: {daily_pnl_pct:.4f}% <= {daily_loss_floor:.4f}%"
        )

    for symbol in symbols:
        mmr = config.mmr.get(symbol)
        if mmr is None:
            leverage_caps.append(
                SymbolLeverageCap(
                    symbol=symbol,
                    mmr=None,
                    raw_cap=None,
                    effective_leverage=None,
                )
            )
            if require_mmr:
                failures.append(f"{symbol}: missing maintenance margin rate")
            continue
        if mmr < 0.0:
            failures.append(f"{symbol}: negative maintenance margin rate {mmr}")
            leverage_caps.append(
                SymbolLeverageCap(
                    symbol=symbol,
                    mmr=mmr,
                    raw_cap=None,
                    effective_leverage=None,
                )
            )
            continue
        raw_cap = floor(1.0 / (DEFAULT_LIQUIDATION_BUFFER + DEFAULT_FEES_SLIPPAGE + mmr))
        leverage_caps.append(
            SymbolLeverageCap(
                symbol=symbol,
                mmr=mmr,
                raw_cap=raw_cap,
                effective_leverage=effective_leverage(
                    user_leverage=config.user_leverage,
                    mmr=mmr,
                ),
            )
        )

    return RiskGateDecision(
        allows_new_signals=not failures,
        failures=tuple(failures),
        leverage_caps=tuple(leverage_caps),
        daily_pnl_pct=daily_pnl_pct,
        daily_max_loss_pct=config.risk.daily_max_loss_pct,
    )


def risk_gate_payload(decision: RiskGateDecision) -> dict[str, object]:
    return {
        "allows_new_signals": decision.allows_new_signals,
        "failures": list(decision.failures),
        "daily_pnl_pct": decision.daily_pnl_pct,
        "daily_max_loss_pct": decision.daily_max_loss_pct,
        "leverage_caps": [
            {
                "symbol": item.symbol,
                "mmr": item.mmr,
                "raw_cap": item.raw_cap,
                "effective_leverage": item.effective_leverage,
            }
            for item in decision.leverage_caps
        ],
    }
