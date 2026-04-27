"""Paper-only MTS-V1 runner.

This wrapper replays the accepted MTS-V1 profile against local OHLCV cache and
emits paper artifacts. It never creates an exchange client and never submits
orders.
"""
from __future__ import annotations

import argparse
import http.server
import json
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mts_profile import (
    ACCEPTED_CVD_ENTRY_MODE,
    ACCEPTED_ENTRY_TIMEFRAME,
    ACCEPTED_EXECUTION_TIMEFRAME,
    ACCEPTED_HTF_TIMEFRAME,
    ACCEPTED_RSM,
    ACCEPTED_SYMBOLS,
    accepted_replay_kwargs,
    accepted_rsm_arg as _accepted_rsm_arg,
)
from offline_replay import DEFAULT_CACHE_DIR, ReplayResult, run_replay
from risk_gate import RiskGateDecision, evaluate_risk_gate, risk_gate_payload
from strategy import DEFAULT_CONFIG_PATH, load_config, parse_symbol_override


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_PAPER_DIR = ROOT_DIR / "paper_logs"
DEFAULT_PORT = 8904


def now_utc_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def accepted_rsm_arg() -> str:
    return _accepted_rsm_arg()


@dataclass(slots=True, frozen=True)
class PaperArtifacts:
    trades_jsonl: Path
    summary_json: Path


class MtsPaperRunner:
    def __init__(
        self,
        *,
        config_path: Path = DEFAULT_CONFIG_PATH,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        paper_dir: Path = DEFAULT_PAPER_DIR,
        symbols: list[str] | None = None,
        port: int = DEFAULT_PORT,
        require_risk_ready: bool = False,
        daily_pnl_pct: float = 0.0,
    ) -> None:
        self.config_path = config_path
        self.cache_dir = cache_dir
        self.paper_dir = paper_dir
        self.symbols = symbols or list(ACCEPTED_SYMBOLS)
        self.port = port
        self.require_risk_ready = require_risk_ready
        self.daily_pnl_pct = daily_pnl_pct
        self.session_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        self.last_payload: dict[str, Any] = {}

    def run_once(self, *, days: int = 90) -> dict[str, Any]:
        artifacts = self._artifacts()
        config = load_config(self.config_path)
        risk_decision = evaluate_risk_gate(
            config=config,
            symbols=self.symbols,
            daily_pnl_pct=self.daily_pnl_pct,
            require_mmr=self.require_risk_ready,
        )
        if self.require_risk_ready and not risk_decision.allows_new_signals:
            payload = self._blocked_payload(artifacts, risk_decision)
            artifacts.summary_json.parent.mkdir(parents=True, exist_ok=True)
            artifacts.summary_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            self.last_payload = payload
            return payload

        result = run_replay(
            config_path=self.config_path,
            cache_dir=self.cache_dir,
            days=days,
            output_path=artifacts.trades_jsonl,
            symbols=self.symbols,
            **accepted_replay_kwargs(),
        )
        payload = self._payload(result, artifacts, risk_decision)
        artifacts.summary_json.parent.mkdir(parents=True, exist_ok=True)
        artifacts.summary_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        self.last_payload = payload
        return payload

    def serve(self, *, tick_sec: float = 3600.0, days: int = 90) -> None:
        PaperStateHandler.runner = self
        server = http.server.HTTPServer(("127.0.0.1", self.port), PaperStateHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(f"[MTS Paper] State API: http://127.0.0.1:{self.port}/api/state")
        try:
            while True:
                self.run_once(days=days)
                time.sleep(tick_sec)
        except KeyboardInterrupt:
            server.shutdown()
            server.server_close()
            print("\n[MTS Paper] Stopped.")

    def _artifacts(self) -> PaperArtifacts:
        run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        session_dir = self.paper_dir / self.session_id / run_id
        return PaperArtifacts(
            trades_jsonl=session_dir / "trades.jsonl",
            summary_json=session_dir / "summary.json",
        )

    def _blocked_payload(
        self,
        artifacts: PaperArtifacts,
        risk_decision: RiskGateDecision,
    ) -> dict[str, Any]:
        return {
            "mode": "paper",
            "paper_only": True,
            "strategy": "MTS-V1",
            "session_id": self.session_id,
            "generated_at": now_utc_iso(),
            "symbols": self.symbols,
            "events": 0,
            "exits": 0,
            "blocked": True,
            "block_reason": "risk_gate",
            "risk_gate": risk_gate_payload(risk_decision),
            "artifacts": {
                "trades_jsonl": str(artifacts.trades_jsonl),
                "summary_json": str(artifacts.summary_json),
            },
        }

    def _payload(
        self,
        result: ReplayResult,
        artifacts: PaperArtifacts,
        risk_decision: RiskGateDecision,
    ) -> dict[str, Any]:
        return {
            "mode": "paper",
            "paper_only": True,
            "strategy": "MTS-V1",
            "session_id": self.session_id,
            "generated_at": now_utc_iso(),
            "symbols": result.symbols,
            "events": result.events,
            "exits": result.exits,
            "profile": {
                "entry_timeframe": ACCEPTED_ENTRY_TIMEFRAME,
                "execution_timeframe": ACCEPTED_EXECUTION_TIMEFRAME,
                "htf_timeframe": ACCEPTED_HTF_TIMEFRAME,
                "symbol_reverse_spike_multipliers": ACCEPTED_RSM,
                "cvd_entry_mode": ACCEPTED_CVD_ENTRY_MODE,
                "l3_max_distance_atr": None,
            },
            "blocked": False,
            "risk_gate": risk_gate_payload(risk_decision),
            "artifacts": {
                "trades_jsonl": str(artifacts.trades_jsonl),
                "summary_json": str(artifacts.summary_json),
            },
        }


class PaperStateHandler(http.server.BaseHTTPRequestHandler):
    runner: MtsPaperRunner | None = None

    def log_message(self, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path not in ("/", "/api/state", "/api/snapshot"):
            self.send_error(404)
            return
        payload = self.runner.last_payload if self.runner is not None else {}
        body = json.dumps(payload or {"status": "starting"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MTS-V1 paper-only runner")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--paper-dir", type=Path, default=DEFAULT_PAPER_DIR)
    parser.add_argument("--symbols", default=",".join(ACCEPTED_SYMBOLS))
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--tick-sec", type=float, default=3600.0)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--require-risk-ready",
        action="store_true",
        help="Fail closed before replay when MMR or daily max-loss risk gates block new signals.",
    )
    parser.add_argument(
        "--daily-pnl-pct",
        type=float,
        default=0.0,
        help="Current UTC-day realized PnL percent for daily max-loss gating.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runner = MtsPaperRunner(
        config_path=args.config,
        cache_dir=args.cache_dir,
        paper_dir=args.paper_dir,
        symbols=parse_symbol_override(args.symbols) or ACCEPTED_SYMBOLS,
        port=args.port,
        require_risk_ready=args.require_risk_ready,
        daily_pnl_pct=args.daily_pnl_pct,
    )
    if args.serve:
        runner.serve(tick_sec=args.tick_sec, days=args.days)
        return 0
    payload = runner.run_once(days=args.days)
    print(
        "[MTS Paper] "
        f"symbols={len(payload['symbols'])} events={payload['events']} exits={payload['exits']} "
        f"summary={payload['artifacts']['summary_json']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
