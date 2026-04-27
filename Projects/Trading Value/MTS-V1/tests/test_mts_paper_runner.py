from __future__ import annotations

from pathlib import Path

import strategy
from mts_paper_runner import (
    ACCEPTED_RSM,
    ACCEPTED_SYMBOLS,
    DEFAULT_PORT,
    MtsPaperRunner,
    accepted_rsm_arg,
)
from offline_replay import ReplayResult


def test_accepted_rsm_arg_matches_pass_profile() -> None:
    assert accepted_rsm_arg() == "BTC=6.3,ETH=6.8,SOL=5.5,XRP=6.3,BNB=2.5"


def test_paper_runner_uses_accepted_profile_without_exchange(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    calls = []

    def fake_run_replay(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        output_path = Path(kwargs["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("", encoding="utf-8")
        return ReplayResult(output_path=output_path, events=2, exits=1, symbols=kwargs["symbols"])

    monkeypatch.setattr("mts_paper_runner.run_replay", fake_run_replay)
    runner = MtsPaperRunner(paper_dir=tmp_path)

    payload = runner.run_once(days=7)

    assert calls[0]["symbols"] == ACCEPTED_SYMBOLS
    assert calls[0]["entry_timeframe"] == "15m"
    assert calls[0]["execution_timeframe"] == "15m"
    assert calls[0]["symbol_reverse_spike_multipliers"] == ACCEPTED_RSM
    assert calls[0]["l3_max_distance_atr"] is None
    assert payload["paper_only"] is True
    assert payload["blocked"] is False
    assert payload["risk_gate"]["allows_new_signals"] is True
    assert Path(payload["artifacts"]["summary_json"]).exists()


def test_paper_runner_can_fail_closed_before_replay(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    calls = []

    def fake_run_replay(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        output_path = Path(kwargs["output_path"])
        return ReplayResult(output_path=output_path, events=2, exits=1, symbols=kwargs["symbols"])

    monkeypatch.setattr("mts_paper_runner.run_replay", fake_run_replay)
    runner = MtsPaperRunner(paper_dir=tmp_path, require_risk_ready=True)

    payload = runner.run_once(days=7)

    assert calls == []
    assert payload["blocked"] is True
    assert payload["block_reason"] == "risk_gate"
    assert payload["events"] == 0
    assert payload["risk_gate"]["allows_new_signals"] is False
    assert "missing maintenance margin rate" in payload["risk_gate"]["failures"][0]
    assert Path(payload["artifacts"]["summary_json"]).exists()


def test_mts_paper_default_port_does_not_conflict_with_meta() -> None:
    assert DEFAULT_PORT == 8904


def test_strategy_paper_default_uses_accepted_profile(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    calls = []

    def fake_run_replay(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        output_path = Path(kwargs["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("", encoding="utf-8")
        return ReplayResult(output_path=output_path, events=2, exits=1, symbols=kwargs["symbols"])

    monkeypatch.setattr("mts_paper_runner.run_replay", fake_run_replay)

    assert (
        strategy.main(
            [
                "--mode",
                "paper",
                "--state-dir",
                str(tmp_path / "state"),
                "--cache-dir",
                str(tmp_path / "cache"),
            ]
        )
        == 0
    )

    assert calls[0]["symbols"] == ACCEPTED_SYMBOLS
    assert calls[0]["symbol_reverse_spike_multipliers"] == ACCEPTED_RSM


def test_strategy_backtest_default_uses_accepted_profile(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    calls = []

    def fake_run_replay(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        output_path = Path(kwargs["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("", encoding="utf-8")
        return ReplayResult(output_path=output_path, events=2, exits=1, symbols=kwargs["symbols"])

    monkeypatch.setattr("offline_replay.run_replay", fake_run_replay)

    assert (
        strategy.main(
            [
                "--mode",
                "backtest",
                "--cache-dir",
                str(tmp_path / "cache"),
                "--output",
                str(tmp_path / "trades.jsonl"),
            ]
        )
        == 0
    )

    assert calls[0]["symbols"] == ACCEPTED_SYMBOLS
    assert calls[0]["entry_timeframe"] == "15m"
    assert calls[0]["execution_timeframe"] == "15m"
    assert calls[0]["htf_timeframe"] == "4h"
    assert calls[0]["symbol_reverse_spike_multipliers"] == ACCEPTED_RSM
