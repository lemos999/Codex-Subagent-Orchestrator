from __future__ import annotations

from pathlib import Path


PINE_PATH = Path(__file__).resolve().parents[1] / "strategy.pine"


def _pine_source() -> str:
    return PINE_PATH.read_text(encoding="utf-8")


def test_pine_strategy_declaration_avoids_v5_continuation_indent_risk() -> None:
    source = _pine_source()

    assert 'strategy(title="MTS-V1 v5.2"' in source
    assert "strategy(\n    title=" not in source


def test_pine_step5_6_indicators_use_entry_timeframe() -> None:
    source = _pine_source()

    assert 'entry_tf = input.timeframe("15", "Entry TF"' in source
    assert "atr_14 = request.security(syminfo.tickerid, entry_tf" in source
    assert "rsi_14 = request.security(syminfo.tickerid, entry_tf" in source
    assert "volume_sma_20 = request.security(syminfo.tickerid, entry_tf" in source
    assert "entry_close_prev = request.security(syminfo.tickerid, entry_tf" in source
    assert "tp_a_hit = state == 3" in source
    assert "kijun_sen_prev2" in source
    assert "runner_kijun_break = state == 4" in source
    assert "entry_open < kijun_sen" in source


def test_pine_contract_qty_is_derived_from_equity_fraction() -> None:
    source = _pine_source()

    assert "f_qty_at_price(equity_fraction, price)" in source
    assert "f_effective_leverage()" in source
    assert "strategy.equity * equity_fraction * f_effective_leverage() / price" in source
    assert "base_l2_fraction = base_sizing_frame * l2_weight" in source
    assert "promoted_l2_delta_fraction" in source
    assert "phase3_layer_qty" not in source
    assert "promoted_l2_delta_qty" not in source


def test_pine_effective_leverage_uses_mmr_cap_formula() -> None:
    source = _pine_source()

    assert "f_mmr_for_symbol()" in source
    assert "math.floor(1.0 / (0.20 + 0.01 + mmr))" in source
    assert "math.max(1.0, math.min(float(user_leverage), raw_cap))" in source


def test_pine_hard_sl_priority_runs_before_tp_state_logic() -> None:
    source = _pine_source()

    assert "hard_sl_priority_hit = hard_sl_filled or hard_sl_touched" in source
    assert 'strategy.close_all(comment="HARD_SL_PRIORITY")' in source
    assert "new_l2_hard_sl_touched" in source
    assert 'strategy.close_all(comment="HARD_SL_PRIORITY_AFTER_L2")' in source
    assert "new_l3_hard_sl_touched" in source
    assert 'strategy.close_all(comment="HARD_SL_PRIORITY_AFTER_L3")' in source
    assert source.index("if hard_sl_priority_hit") < source.index(
        "else if state == 3 and barstate.isconfirmed"
    )


def test_pine_l3_fill_threshold_includes_pending_l2_promo() -> None:
    source = _pine_source()

    assert "pending_promo_qty = nz(l2_promo_target_qty, 0.0)" in source
    assert "l3_position_threshold := position_abs + pending_promo_qty + l3_target_qty * 0.999" in source


def test_pine_uses_symbol_specific_reverse_spike_multipliers() -> None:
    source = _pine_source()

    assert 'groupRsm = "Reverse Spike Multipliers"' in source
    assert 'rsm_btc = input.float(6.3, "BTC RSM"' in source
    assert 'rsm_eth = input.float(6.8, "ETH RSM"' in source
    assert 'rsm_sol = input.float(5.5, "SOL RSM"' in source
    assert 'rsm_xrp = input.float(6.3, "XRP RSM"' in source
    assert 'rsm_bnb = input.float(2.5, "BNB RSM"' in source
    assert "active_rsm = f_active_rsm()" in source
    assert "delta_bar < -active_rsm * cvd_abs_sma_20" in source
    assert "delta_bar > active_rsm * cvd_abs_sma_20" in source
