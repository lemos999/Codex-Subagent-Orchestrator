"""Smoke test for v2_ablation.py.

v2_ablation 모듈을 import하여 enable_rule2=False로 V2Engine을 생성했을 때 predictor 주입이 올바른지 검증. 실제 네트워크 fetch는 수행하지 않음.

실행: python scripts/v2_ablation_smoke.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v2_ablation as v2a  # noqa: E402


def test_flag_propagation():
    """V2Engine(enable_rule2=False) 시 모든 predictor.enable_rule2 == False."""
    np.random.seed(42)
    engine = v2a.V2Engine(assets=["BTC", "ETH", "SOL"], port=18902, enable_rule2=False)

    for asset in ["BTC", "ETH", "SOL"]:
        assert engine.predictors[asset].enable_rule2 is False, (
            f"{asset} predictor enable_rule2 expected False, got {engine.predictors[asset].enable_rule2}"
        )

    assert engine.enable_rule2 is False
    print("[OK] V2Engine.enable_rule2=False propagates to all predictors")


def test_rule2_noop():
    """enable_rule2=False인 predictor는 update()가 _rebalance_memory를 호출하지 않음."""
    from v2_ablation import N_FEATURES, OnlinePredictor

    pred = OnlinePredictor(enable_rule2=False)

    call_count = {"n": 0}
    original = pred._rebalance_memory

    def counting_wrapper():
        call_count["n"] += 1
        return original()

    pred._rebalance_memory = counting_wrapper

    x = np.random.randn(N_FEATURES)
    for _ in range(10):
        pred.update(x, 0.001)

    assert call_count["n"] == 0, (
        f"enable_rule2=False with 10 updates: _rebalance_memory called {call_count['n']} times (expected 0)"
    )
    print("[OK] update() with enable_rule2=False does NOT call _rebalance_memory (0/10)")


def test_rule2_on_default():
    """enable_rule2=True(default)인 predictor는 update()가 _rebalance_memory를 호출함."""
    from v2_ablation import N_FEATURES, OnlinePredictor

    pred = OnlinePredictor()
    assert pred.enable_rule2 is True

    call_count = {"n": 0}
    original = pred._rebalance_memory

    def counting_wrapper():
        call_count["n"] += 1
        return original()

    pred._rebalance_memory = counting_wrapper

    x = np.random.randn(N_FEATURES)
    for _ in range(10):
        pred.update(x, 0.001)

    assert call_count["n"] == 10, (
        f"enable_rule2=True with 10 updates: _rebalance_memory called {call_count['n']} times (expected 10)"
    )
    print("[OK] update() with enable_rule2=True calls _rebalance_memory (10/10)")


def test_log_path_isolation():
    """모듈 상수 기본값이 v2.jsonl이 아닌 v2_ablation_*.jsonl 패턴인지 확인."""
    from v2_ablation import LOG_PATH, STATE_PATH

    assert "v2_ablation" in STATE_PATH.name, f"STATE_PATH leaked: {STATE_PATH}"
    assert "v2_ablation" in LOG_PATH.name, f"LOG_PATH leaked: {LOG_PATH}"
    assert STATE_PATH.name != "v2_state.npz"
    assert LOG_PATH.name != "v2.jsonl"
    print(f"[OK] STATE_PATH/LOG_PATH isolated: {STATE_PATH.name}, {LOG_PATH.name}")


if __name__ == "__main__":
    test_flag_propagation()
    test_rule2_noop()
    test_rule2_on_default()
    test_log_path_isolation()
    print("\n[PASS] All smoke tests passed.")
