from __future__ import annotations

from strategy import AppConfig, RiskConfig, TimeframeConfig
from risk_gate import effective_leverage, evaluate_risk_gate, risk_gate_payload


def _config(*, mmr: dict[str, float | None], daily_max_loss_pct: float = 5.0) -> AppConfig:
    return AppConfig(
        strategy="MTS-V1",
        version="v5.2",
        exchange="binanceusdm",
        quote_asset="USDT",
        contract_type="perpetual",
        symbols=list(mmr),
        timeframes=TimeframeConfig(htf="4h", entry_tf="15m", ltf="15m"),
        risk=RiskConfig(daily_max_loss_pct=daily_max_loss_pct, symbol_cooldown_hours=24),
        user_leverage=10,
        use_runner=True,
        mmr=mmr,
    )


def test_effective_leverage_caps_user_leverage_with_mmr_buffer() -> None:
    assert effective_leverage(user_leverage=10, mmr=0.0) == 4
    assert effective_leverage(user_leverage=3, mmr=0.0) == 3
    assert effective_leverage(user_leverage=10, mmr=0.05) == 3


def test_risk_gate_fails_closed_when_mmr_is_missing() -> None:
    decision = evaluate_risk_gate(
        config=_config(mmr={"BTC/USDT:USDT": None}),
        symbols=["BTC/USDT:USDT"],
        require_mmr=True,
    )

    assert decision.allows_new_signals is False
    assert decision.failures == ("BTC/USDT:USDT: missing maintenance margin rate",)
    assert risk_gate_payload(decision)["allows_new_signals"] is False


def test_risk_gate_fails_closed_at_daily_max_loss() -> None:
    decision = evaluate_risk_gate(
        config=_config(mmr={"BTC/USDT:USDT": 0.005}),
        symbols=["BTC/USDT:USDT"],
        daily_pnl_pct=-5.0,
        require_mmr=True,
    )

    assert decision.allows_new_signals is False
    assert decision.failures == ("daily max-loss reached: -5.0000% <= -5.0000%",)


def test_risk_gate_allows_signals_when_inputs_are_ready() -> None:
    decision = evaluate_risk_gate(
        config=_config(mmr={"BTC/USDT:USDT": 0.005}),
        symbols=["BTC/USDT:USDT"],
        daily_pnl_pct=-4.99,
        require_mmr=True,
    )

    assert decision.allows_new_signals is True
    assert decision.leverage_caps[0].effective_leverage == 4
