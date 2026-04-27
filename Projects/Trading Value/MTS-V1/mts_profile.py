from __future__ import annotations


ACCEPTED_SYMBOLS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",
    "XRP/USDT:USDT",
    "BNB/USDT:USDT",
]
ACCEPTED_RSM = {"BTC": 6.3, "ETH": 6.8, "SOL": 5.5, "XRP": 6.3, "BNB": 2.5}
ACCEPTED_ENTRY_TIMEFRAME = "15m"
ACCEPTED_EXECUTION_TIMEFRAME = "15m"
ACCEPTED_HTF_TIMEFRAME = "4h"
ACCEPTED_CVD_ENTRY_MODE = "pine-ltf"


def accepted_rsm_arg() -> str:
    return ",".join(f"{asset}={value}" for asset, value in ACCEPTED_RSM.items())


def accepted_replay_kwargs() -> dict[str, object]:
    return {
        "entry_timeframe": ACCEPTED_ENTRY_TIMEFRAME,
        "execution_timeframe": ACCEPTED_EXECUTION_TIMEFRAME,
        "htf_timeframe": ACCEPTED_HTF_TIMEFRAME,
        "state2_exit_mode": "all",
        "state2_signal_mode": "any",
        "state2_profit_hold_r": None,
        "l3_max_distance_atr": None,
        "reverse_spike_multiplier": 3.0,
        "symbol_reverse_spike_multipliers": dict(ACCEPTED_RSM),
        "reverse_spike_min_ratio": 1.0,
        "reverse_spike_confirm_bars": 1,
        "tp_intrabar_touch": False,
        "cvd_entry_mode": ACCEPTED_CVD_ENTRY_MODE,
    }
