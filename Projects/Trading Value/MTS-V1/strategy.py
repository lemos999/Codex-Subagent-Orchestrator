from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    yaml = None  # type: ignore[assignment]


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT_DIR / "config.yaml"
DEFAULT_STATE_DIR = ROOT_DIR / "state"


class StrategyMode(str, Enum):
    BACKTEST = "backtest"
    PAPER = "paper"


class StateCode(IntEnum):
    FLAT = 0
    L1_FILLED = 1
    L2_FILLED = 2
    L3_FILLED = 3
    RUNNER = 4
    EVASION = 5


class SubState(str, Enum):
    A = "A"
    AB = "AB"


@dataclass(slots=True)
class TimeframeConfig:
    htf: str
    entry_tf: str
    ltf: str


@dataclass(slots=True)
class RiskConfig:
    daily_max_loss_pct: float
    symbol_cooldown_hours: int


@dataclass(slots=True)
class AppConfig:
    strategy: str
    version: str
    exchange: str
    quote_asset: str
    contract_type: str
    symbols: list[str]
    timeframes: TimeframeConfig
    risk: RiskConfig
    user_leverage: int
    use_runner: bool
    mmr: dict[str, float | None]

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "AppConfig":
        timeframes_raw = _as_mapping(raw.get("timeframes"), field_name="timeframes")
        risk_raw = _as_mapping(raw.get("risk"), field_name="risk")
        mmr_raw = _as_mapping(raw.get("mmr"), field_name="mmr")

        return cls(
            strategy=str(raw.get("strategy", "MTS-V1")),
            version=str(raw.get("version", "v5.1")),
            exchange=str(raw.get("exchange", "binanceusdm")),
            quote_asset=str(raw.get("quote_asset", "USDT")),
            contract_type=str(raw.get("contract_type", "perpetual")),
            symbols=[str(symbol) for symbol in raw.get("symbols", [])],
            timeframes=TimeframeConfig(
                htf=str(timeframes_raw.get("htf", "4h")),
                entry_tf=str(timeframes_raw.get("entry_tf", "1h")),
                ltf=str(timeframes_raw.get("ltf", "15m")),
            ),
            risk=RiskConfig(
                daily_max_loss_pct=float(risk_raw.get("daily_max_loss_pct", 5)),
                symbol_cooldown_hours=int(risk_raw.get("symbol_cooldown_hours", 24)),
            ),
            user_leverage=int(raw.get("user_leverage", 10)),
            use_runner=bool(raw.get("use_runner", True)),
            mmr={
                str(symbol): None if value is None else float(value)
                for symbol, value in mmr_raw.items()
            },
        )


@dataclass(slots=True)
class StrategyStateSnapshot:
    strategy: str = "MTS-V1"
    version: str = "v5.1"
    symbol: str = ""
    state: int = int(StateCode.FLAT)
    sub_state: str | None = None
    avg_entry: float = 0.0
    hard_sl: float = 0.0
    entry_prices: dict[str, float | None] = field(
        default_factory=lambda: {"L1": 0.0, "L2": 0.0, "L3": None}
    )
    fill_qtys: dict[str, float] = field(
        default_factory=lambda: {"L1": 0.0, "L2": 0.0, "L3": 0.0}
    )
    triple_confluence: bool = False
    sizing_frame: float = 0.10
    client_order_ids: dict[str, str | None] = field(
        default_factory=lambda: {"L1": None, "L2": None, "L3": None}
    )
    cvd_daily_start: str = ""
    created_ts: str = ""
    updated_ts: str = ""

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)


def _as_mapping(value: Any, *, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping.")
    return value


def load_config(path: Path) -> AppConfig:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load config.yaml.")

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if not isinstance(raw, dict):
        raise ValueError("config.yaml must contain a top-level mapping.")

    config = AppConfig.from_mapping(raw)
    validate_config(config)
    return config


def validate_config(config: AppConfig) -> None:
    if config.strategy != "MTS-V1":
        raise ValueError("strategy must remain MTS-V1.")
    if not config.symbols:
        raise ValueError("At least one symbol must be configured.")
    missing_mmr = [symbol for symbol in config.symbols if symbol not in config.mmr]
    if missing_mmr:
        raise ValueError(f"Missing mmr entries for symbols: {', '.join(missing_mmr)}")


def symbol_to_state_path(symbol: str, state_dir: Path) -> Path:
    slug = symbol.lower().replace("/", "_").replace(":", "_")
    return state_dir / f"state_{slug}.json"


def default_state(symbol: str, now_iso: str) -> StrategyStateSnapshot:
    return StrategyStateSnapshot(
        symbol=symbol,
        cvd_daily_start=now_iso,
        created_ts=now_iso,
        updated_ts=now_iso,
    )


def load_state(path: Path) -> StrategyStateSnapshot | None:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if not isinstance(raw, dict):
        raise ValueError(f"State file {path} must contain a JSON object.")

    snapshot = StrategyStateSnapshot()
    for field_name in snapshot.to_mapping():
        if field_name in raw:
            setattr(snapshot, field_name, raw[field_name])
    return snapshot


def save_state(path: Path, snapshot: StrategyStateSnapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(snapshot.to_mapping(), handle, indent=2)
        handle.write("\n")


def collect_market_snapshot(symbol: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "entry_trigger_ready": False,
        "triple_confluence": False,
        "runner_triggered": False,
    }


def evaluate_entry_trigger(market_snapshot: dict[str, Any]) -> bool:
    return bool(market_snapshot.get("entry_trigger_ready", False))


def advance_state_machine(
    snapshot: StrategyStateSnapshot,
    event_name: str,
) -> StrategyStateSnapshot:
    logging.debug("State machine placeholder received event=%s for %s", event_name, snapshot.symbol)
    return snapshot


def evaluate_exit_logic(
    snapshot: StrategyStateSnapshot,
    market_snapshot: dict[str, Any],
) -> str | None:
    if snapshot.state == int(StateCode.RUNNER) and market_snapshot.get("runner_triggered"):
        return "runner_exit_pending"
    return None


def enforce_ops_guards(config: AppConfig, symbol: str) -> list[str]:
    warnings: list[str] = []
    if config.mmr.get(symbol) is None:
        warnings.append(
            f"{symbol}: mmr is unset. Fill exchange-published values before paper/live execution."
        )
    return warnings


def run_backtest(config: AppConfig, symbols: list[str], state_dir: Path) -> int:
    logging.info("Phase 1 scaffold: backtest loop is not implemented yet.")
    for symbol in symbols:
        state_path = symbol_to_state_path(symbol, state_dir)
        snapshot = load_state(state_path)
        if snapshot is None:
            logging.info("No persisted state for %s at %s", symbol, state_path)
        else:
            logging.info("Loaded persisted state for %s (state=%s)", symbol, snapshot.state)
    logging.info(
        "Configured TFs: htf=%s entry_tf=%s ltf=%s",
        config.timeframes.htf,
        config.timeframes.entry_tf,
        config.timeframes.ltf,
    )
    return 0


def run_paper(config: AppConfig, symbols: list[str], state_dir: Path) -> int:
    logging.info("Phase 1 scaffold: paper loop is not implemented yet.")
    for symbol in symbols:
        market_snapshot = collect_market_snapshot(symbol)
        logging.info(
            "Symbol=%s entry_trigger_ready=%s triple_confluence=%s state_path=%s",
            symbol,
            evaluate_entry_trigger(market_snapshot),
            market_snapshot["triple_confluence"],
            symbol_to_state_path(symbol, state_dir),
        )
    return 0


def parse_symbol_override(raw: str | None) -> list[str] | None:
    if raw is None or not raw.strip():
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MTS-V1 Phase 1 strategy scaffold")
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in StrategyMode],
        default=StrategyMode.PAPER.value,
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--symbols", help="Comma-separated symbol override.")
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(levelname)s %(message)s",
    )

    config = load_config(args.config)
    symbols = parse_symbol_override(args.symbols) or config.symbols

    for symbol in symbols:
        for warning in enforce_ops_guards(config, symbol):
            logging.warning(warning)

    if args.mode == StrategyMode.BACKTEST.value:
        return run_backtest(config, symbols, args.state_dir)
    return run_paper(config, symbols, args.state_dir)


if __name__ == "__main__":
    raise SystemExit(main())
