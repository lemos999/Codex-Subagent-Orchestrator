from strategy import (
    FiboAnchor,
    TradeSide,
    VolumeProfile,
    build_layered_entry_prices,
    validate_fibo_anchor_temporal,
)


def _profile() -> VolumeProfile:
    return VolumeProfile(
        poc=105.0,
        vah=112.0,
        val=98.0,
        window_low=90.0,
        window_high=120.0,
        bin_size=0.6,
    )


def _anchor(
    *,
    pivot_low_ts: int | None,
    pivot_high_ts: int | None,
) -> FiboAnchor:
    return FiboAnchor(
        pivot_low=90.0,
        pivot_high=120.0,
        low_index=0 if pivot_low_ts is None else pivot_low_ts,
        high_index=99 if pivot_high_ts is None else pivot_high_ts,
        pivot_low_ts=pivot_low_ts,
        pivot_high_ts=pivot_high_ts,
    )


def test_temporal_order_long_valid() -> None:
    assert validate_fibo_anchor_temporal(
        pivot_high_ts=30,
        pivot_low_ts=10,
        side=TradeSide.LONG,
    )

    prices = build_layered_entry_prices(
        profile=_profile(),
        anchor=_anchor(pivot_low_ts=10, pivot_high_ts=30),
        kijun_value=104.0,
        atr_value=2.0,
        side=TradeSide.LONG,
    )

    assert prices is not None
    assert prices.l1 == 105.1


def test_temporal_order_long_inverted() -> None:
    assert not validate_fibo_anchor_temporal(
        pivot_high_ts=10,
        pivot_low_ts=30,
        side=TradeSide.LONG,
    )

    prices = build_layered_entry_prices(
        profile=_profile(),
        anchor=_anchor(pivot_low_ts=30, pivot_high_ts=10),
        kijun_value=104.0,
        atr_value=2.0,
        side=TradeSide.LONG,
    )

    assert prices is None


def test_temporal_order_short_valid() -> None:
    assert validate_fibo_anchor_temporal(
        pivot_high_ts=10,
        pivot_low_ts=30,
        side=TradeSide.SHORT,
    )


def test_temporal_order_short_inverted() -> None:
    assert not validate_fibo_anchor_temporal(
        pivot_high_ts=30,
        pivot_low_ts=10,
        side=TradeSide.SHORT,
    )


def test_temporal_order_fallback() -> None:
    assert validate_fibo_anchor_temporal(
        pivot_high_ts=None,
        pivot_low_ts=30,
        side=TradeSide.LONG,
    )

    prices = build_layered_entry_prices(
        profile=_profile(),
        anchor=_anchor(pivot_low_ts=30, pivot_high_ts=None),
        kijun_value=104.0,
        atr_value=2.0,
        side=TradeSide.LONG,
    )

    assert prices is not None
