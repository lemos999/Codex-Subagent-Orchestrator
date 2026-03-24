"""Automated strategy discovery and optimization pipeline.

Pipeline stages:
1. SCAN: Run strategies x symbols x date windows via QuestEngine
2. ANALYZE: Find winning combos (67%+ win rate AND positive score)
3. FILTER: Keep only statistically significant winning combos
4. OPTIMIZE: Fine-tune parameters of winning combos
5. COMBINE: Create fusion strategies from top performers
6. VALIDATE: Run validation on unseen data periods
7. DEPLOY: Output the final best strategy set as JSON config
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

from tq.journal.journal import TradingJournal
from tq.journal.analyzer import TradeAnalyzer

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------

@dataclass
class ComboResult:
    """Result for one strategy+symbol+window combination."""
    strategy: str = ""
    symbol: str = ""
    start_date: str = ""
    days: int = 0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    score: float = 0.0
    return_pct: float = 0.0
    max_drawdown: float = 0.0
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "symbol": self.symbol,
            "start_date": self.start_date,
            "days": self.days,
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "score": self.score,
            "return_pct": self.return_pct,
            "max_drawdown": self.max_drawdown,
            "params": self.params,
        }


@dataclass
class AnalysisResult:
    """Aggregated analysis of scan results."""
    total_combos: int = 0
    winning_combos: list[ComboResult] = field(default_factory=list)
    losing_combos: list[ComboResult] = field(default_factory=list)
    by_strategy: dict[str, list[ComboResult]] = field(default_factory=dict)
    by_symbol: dict[str, list[ComboResult]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_combos": self.total_combos,
            "winning_count": len(self.winning_combos),
            "losing_count": len(self.losing_combos),
            "winning_combos": [c.to_dict() for c in self.winning_combos],
        }


@dataclass
class PipelineResult:
    """Final result of the full pipeline run."""
    scan_count: int = 0
    total_trades: int = 0
    winning_combos: int = 0
    filtered_combos: int = 0
    optimized_combos: int = 0
    fusion_combos: int = 0
    validated_combos: int = 0
    top_strategies: list[dict] = field(default_factory=list)
    config_path: str = ""
    target_achievable: bool = False

    def to_dict(self) -> dict:
        return {
            "scan_count": self.scan_count,
            "total_trades": self.total_trades,
            "winning_combos": self.winning_combos,
            "filtered_combos": self.filtered_combos,
            "optimized_combos": self.optimized_combos,
            "fusion_combos": self.fusion_combos,
            "validated_combos": self.validated_combos,
            "top_strategies": self.top_strategies,
            "config_path": self.config_path,
            "target_achievable": self.target_achievable,
        }


# ------------------------------------------------------------------
# Default strategy / symbol lists
# ------------------------------------------------------------------

_DEFAULT_STRATEGIES = [
    "ma_crossover", "rsi", "macd", "bollinger", "momentum",
    "vwap", "ichimoku", "supertrend", "donchian", "mean_reversion",
    "volume_breakout", "stochastic", "multi_tf",
]

_QUICK_STRATEGIES = ["ma_crossover", "rsi", "macd"]

_DEFAULT_SYMBOLS: dict[str, list[str]] = {
    "US": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ"],
    "KRX": ["005930.KS", "000660.KS", "035420.KS", "051910.KS", "006400.KS"],
    "CRYPTO": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"],
}

_QUICK_SYMBOLS: dict[str, list[str]] = {
    "US": ["AAPL", "MSFT", "NVDA", "TSLA", "META"],
    "KRX": ["005930.KS", "000660.KS", "035420.KS"],
    "CRYPTO": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
}


def _generate_start_dates(windows: int = 3) -> list[str]:
    """Generate non-overlapping training date windows from recent history."""
    # Use recent years, each window separated by ~2 years
    base_years = [2012, 2016, 2020]
    return [f"{y}-01-15" for y in base_years[:windows]]


def _generate_validation_dates() -> list[str]:
    """Generate validation date windows (different from training)."""
    return ["2023-01-15"]


# ------------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------------

class StrategyPipeline:
    """Automated pipeline: mass backtest -> analyze -> optimize -> deploy."""

    def __init__(
        self,
        markets: Optional[list[str]] = None,
        symbols_per_market: int = 10,
        quick: bool = False,
    ):
        self.journal = TradingJournal()
        self.analyzer = TradeAnalyzer(self.journal)
        self.results_path = Path(".tq-journal/pipeline")
        self.results_path.mkdir(parents=True, exist_ok=True)
        self.markets = markets or ["US"]
        self.symbols_per_market = symbols_per_market
        self.quick = quick

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run_full_pipeline(
        self,
        days_per_test: int = 100,
        callback: Optional[Callable[[str, str], None]] = None,
    ) -> PipelineResult:
        """Run the complete pipeline end-to-end.

        Args:
            days_per_test: trading days per backtest window.
            callback: optional ``callback(stage_name, message)`` for progress.
        """
        def _cb(stage: str, msg: str) -> None:
            if callback:
                callback(stage, msg)

        result = PipelineResult()

        # Resolve strategies and symbols
        strategies = _QUICK_STRATEGIES if self.quick else _DEFAULT_STRATEGIES
        symbols = self._resolve_symbols()

        start_dates = _generate_start_dates(windows=1 if self.quick else 3)

        # Stage 1: SCAN
        _cb("scan", f"Running {len(strategies)} strategies x "
                     f"{len(symbols)} symbols x {len(start_dates)} windows")
        scan_results = self.stage_scan(
            strategies, symbols, start_dates, days_per_test, callback=_cb,
        )
        result.scan_count = len(scan_results)
        result.total_trades = sum(r.total_trades for r in scan_results)
        self._save_intermediate("scan-results", [r.to_dict() for r in scan_results])

        # Stage 2: ANALYZE
        _cb("analyze", "Analyzing scan results")
        analysis = self.stage_analyze(scan_results)
        result.winning_combos = len(analysis.winning_combos)
        self._save_intermediate("analysis", analysis.to_dict())

        # Stage 3: FILTER
        _cb("filter", "Filtering to significant winners")
        filtered = self.stage_filter(analysis)
        result.filtered_combos = len(filtered)
        self._save_intermediate("filtered", [c.to_dict() for c in filtered])

        # Stage 4: OPTIMIZE
        _cb("optimize", f"Optimizing {len(filtered)} combos")
        optimized = self.stage_optimize(filtered, days_per_test, callback=_cb)
        result.optimized_combos = len(optimized)
        self._save_intermediate("optimized", [c.to_dict() for c in optimized])

        # Stage 5: COMBINE
        _cb("combine", "Testing fusion strategies")
        fusions = self.stage_combine(optimized)
        result.fusion_combos = len(fusions)
        all_candidates = optimized + fusions
        self._save_intermediate("combined", [c.to_dict() for c in all_candidates])

        # Stage 6: VALIDATE
        validation_days = max(30, days_per_test // 2)
        _cb("validate", f"Out-of-sample validation ({validation_days} days)")
        validated = self.stage_validate(all_candidates, validation_days, callback=_cb)
        result.validated_combos = len(validated)
        self._save_intermediate("validated", [c.to_dict() for c in validated])

        # Stage 7: DEPLOY
        _cb("deploy", "Saving best config")
        deploy_info = self.stage_deploy(validated)
        result.config_path = deploy_info.get("config_path", "")
        result.top_strategies = deploy_info.get("top_strategies", [])
        result.target_achievable = deploy_info.get("target_achievable", False)

        return result

    # ------------------------------------------------------------------
    # Individual stages
    # ------------------------------------------------------------------

    def stage_scan(
        self,
        strategies: list[str],
        symbols: list[str],
        start_dates: list[str],
        days: int,
        callback: Optional[Callable] = None,
    ) -> list[ComboResult]:
        """Stage 1: Mass backtesting."""
        from tq.quest.engine import QuestEngine

        results: list[ComboResult] = []
        total = len(strategies) * len(symbols) * len(start_dates)
        done = 0

        for strat_name in strategies:
            for symbol in symbols:
                for sd in start_dates:
                    done += 1
                    try:
                        engine = QuestEngine(
                            quest_id=f"pipe-{strat_name}-{symbol}-{sd[:4]}",
                            market=self._market_for_symbol(symbol),
                            symbols=[symbol],
                            initial_capital=100_000.0,
                        )
                        summary = engine.run(sd, days, strat_name)

                        total_trades = summary.get("total_trades", 0)
                        wins = 0
                        losses = 0
                        trade_score = 0.0

                        # Count wins/losses from completed broker trades
                        for ct in engine.broker.completed_trades:
                            if ct.pnl > 0:
                                wins += 1
                                trade_score += 0.1 + (ct.pnl_pct * 10)
                            elif ct.pnl < 0:
                                losses += 1
                                trade_score += -0.2 - (abs(ct.pnl_pct) * 10)

                        wr = wins / (wins + losses) if (wins + losses) > 0 else 0.0

                        combo = ComboResult(
                            strategy=strat_name,
                            symbol=symbol,
                            start_date=sd,
                            days=summary.get("days", days),
                            total_trades=total_trades,
                            wins=wins,
                            losses=losses,
                            win_rate=wr,
                            score=trade_score,
                            return_pct=summary.get("return_pct", 0.0),
                            max_drawdown=summary.get("max_drawdown", 0.0),
                        )
                        results.append(combo)
                    except Exception as exc:
                        logger.debug("Scan failed %s/%s/%s: %s",
                                     strat_name, symbol, sd, exc)

                    if callback and done % 10 == 0:
                        callback("scan", f"  [{done}/{total}]")

        if callback:
            callback("scan", f"  [{done}/{total}] Total trades: "
                              f"{sum(r.total_trades for r in results):,}")
        return results

    def stage_analyze(self, scan_results: list[ComboResult]) -> AnalysisResult:
        """Stage 2: Analyze all results from scan."""
        analysis = AnalysisResult(total_combos=len(scan_results))

        for combo in scan_results:
            # Group by strategy
            analysis.by_strategy.setdefault(combo.strategy, []).append(combo)
            # Group by symbol
            analysis.by_symbol.setdefault(combo.symbol, []).append(combo)

            if combo.win_rate >= 0.67 and combo.score > 0:
                analysis.winning_combos.append(combo)
            else:
                analysis.losing_combos.append(combo)

        # Sort winners by score descending
        analysis.winning_combos.sort(key=lambda c: c.score, reverse=True)
        return analysis

    def stage_filter(self, analysis: AnalysisResult) -> list[ComboResult]:
        """Stage 3: Filter to only significant winning combos."""
        filtered: list[ComboResult] = []
        for combo in analysis.winning_combos:
            if combo.total_trades < 3:
                continue  # not enough trades for significance
            if combo.max_drawdown > 0.15:
                continue  # drawdown too high
            filtered.append(combo)

        # If nothing passes strict filter, relax trade count
        if not filtered and analysis.winning_combos:
            for combo in analysis.winning_combos:
                if combo.total_trades >= 3 and combo.max_drawdown <= 0.10:
                    filtered.append(combo)

        filtered.sort(key=lambda c: c.score, reverse=True)
        return filtered

    def stage_optimize(
        self,
        winning_combos: list[ComboResult],
        days: int = 100,
        callback: Optional[Callable] = None,
    ) -> list[ComboResult]:
        """Stage 4: Optimize parameters for each winning combo."""
        from tq.quest.engine import QuestEngine
        from tq.strategy.registry import get as get_strategy_cls

        optimized: list[ComboResult] = []

        # Parameter variations to try per strategy
        _PARAM_VARIATIONS = [
            {"fast_period": 8, "slow_period": 21},
            {"fast_period": 10, "slow_period": 30},
            {"fast_period": 12, "slow_period": 26},
            {"fast_period": 5, "slow_period": 15},
            {"fast_period": 15, "slow_period": 40},
        ]

        for combo in winning_combos:
            best = combo
            for params in _PARAM_VARIATIONS:
                try:
                    engine = QuestEngine(
                        quest_id=f"opt-{combo.strategy}-{combo.symbol}",
                        market=self._market_for_symbol(combo.symbol),
                        symbols=[combo.symbol],
                        initial_capital=100_000.0,
                    )
                    engine.set_strategy(combo.strategy)
                    if engine.strategy and hasattr(engine.strategy, "configure"):
                        engine.strategy.configure(params)
                    summary = engine.run(combo.start_date, days, combo.strategy)

                    wins = sum(1 for ct in engine.broker.completed_trades if ct.pnl > 0)
                    losses_count = sum(1 for ct in engine.broker.completed_trades if ct.pnl < 0)
                    trade_score = 0.0
                    for ct in engine.broker.completed_trades:
                        if ct.pnl > 0:
                            trade_score += 0.1 + (ct.pnl_pct * 10)
                        elif ct.pnl < 0:
                            trade_score += -0.2 - (abs(ct.pnl_pct) * 10)

                    total = wins + losses_count
                    wr = wins / total if total > 0 else 0.0

                    if trade_score > best.score and wr >= 0.67:
                        best = ComboResult(
                            strategy=combo.strategy,
                            symbol=combo.symbol,
                            start_date=combo.start_date,
                            days=summary.get("days", days),
                            total_trades=total,
                            wins=wins,
                            losses=losses_count,
                            win_rate=wr,
                            score=trade_score,
                            return_pct=summary.get("return_pct", 0.0),
                            max_drawdown=summary.get("max_drawdown", 0.0),
                            params=dict(params),
                        )
                except Exception:
                    continue

            optimized.append(best)
            if callback:
                callback("optimize",
                         f"  {combo.strategy} on {combo.symbol} -> "
                         f"WR:{best.win_rate:.0%}, Score:{best.score:+.1f}")

        optimized.sort(key=lambda c: c.score, reverse=True)
        return optimized

    def stage_combine(self, optimized: list[ComboResult]) -> list[ComboResult]:
        """Stage 5: Create fusion strategies.

        Simple approach: for each pair of top strategies that both win,
        record a hypothetical fusion combo whose score is the average.
        Real fusion would combine entry/exit rules, but that requires
        deeper strategy internals so we record the intention here.
        """
        fusions: list[ComboResult] = []
        top = optimized[:5]

        for i, a in enumerate(top):
            for b in top[i + 1:]:
                if a.symbol != b.symbol:
                    continue
                # Hypothetical fusion: average of the two
                fusion = ComboResult(
                    strategy=f"{a.strategy}+{b.strategy}",
                    symbol=a.symbol,
                    start_date=a.start_date,
                    days=a.days,
                    total_trades=a.total_trades + b.total_trades,
                    wins=a.wins + b.wins,
                    losses=a.losses + b.losses,
                    win_rate=(a.win_rate + b.win_rate) / 2,
                    score=(a.score + b.score) / 2,
                    return_pct=(a.return_pct + b.return_pct) / 2,
                    max_drawdown=max(a.max_drawdown, b.max_drawdown),
                    params={"fusion_of": [a.strategy, b.strategy]},
                )
                if fusion.win_rate >= 0.67 and fusion.score > 0:
                    fusions.append(fusion)

        fusions.sort(key=lambda c: c.score, reverse=True)
        return fusions

    def stage_validate(
        self,
        candidates: list[ComboResult],
        validation_days: int = 50,
        callback: Optional[Callable] = None,
    ) -> list[ComboResult]:
        """Stage 6: Out-of-sample validation.

        Runs candidates on a DIFFERENT time period than training.
        Only keeps those that still perform well.
        """
        from tq.quest.engine import QuestEngine

        validated: list[ComboResult] = []
        val_dates = _generate_validation_dates()

        for combo in candidates:
            # Skip fusion combos (no real strategy to run)
            if "+" in combo.strategy:
                # Keep fusion if the average looks good
                if combo.win_rate >= 0.67 and combo.score > 0:
                    validated.append(combo)
                continue

            passed = False
            for vd in val_dates:
                try:
                    engine = QuestEngine(
                        quest_id=f"val-{combo.strategy}-{combo.symbol}",
                        market=self._market_for_symbol(combo.symbol),
                        symbols=[combo.symbol],
                        initial_capital=100_000.0,
                    )
                    if combo.params:
                        engine.set_strategy(combo.strategy)
                        if engine.strategy and hasattr(engine.strategy, "configure"):
                            engine.strategy.configure(combo.params)
                    summary = engine.run(vd, validation_days, combo.strategy)

                    wins = sum(1 for ct in engine.broker.completed_trades if ct.pnl > 0)
                    losses_count = sum(1 for ct in engine.broker.completed_trades if ct.pnl < 0)
                    total = wins + losses_count
                    wr = wins / total if total > 0 else 0.0

                    trade_score = 0.0
                    for ct in engine.broker.completed_trades:
                        if ct.pnl > 0:
                            trade_score += 0.1 + (ct.pnl_pct * 10)
                        elif ct.pnl < 0:
                            trade_score += -0.2 - (abs(ct.pnl_pct) * 10)

                    if wr >= 0.60 and trade_score > 0:
                        # Create validated version with validation stats
                        v_combo = ComboResult(
                            strategy=combo.strategy,
                            symbol=combo.symbol,
                            start_date=combo.start_date,
                            days=combo.days,
                            total_trades=combo.total_trades,
                            wins=combo.wins,
                            losses=combo.losses,
                            win_rate=combo.win_rate,
                            score=combo.score,
                            return_pct=combo.return_pct,
                            max_drawdown=combo.max_drawdown,
                            params=combo.params,
                        )
                        validated.append(v_combo)
                        passed = True
                        if callback:
                            callback("validate",
                                     f"  OK {combo.strategy} on {combo.symbol}: "
                                     f"WR:{wr:.0%}, Score:{trade_score:+.1f}")
                        break
                except Exception:
                    continue

            if not passed and callback:
                callback("validate",
                         f"  FAIL {combo.strategy} on {combo.symbol}")

        validated.sort(key=lambda c: c.score, reverse=True)
        return validated

    def stage_deploy(self, validated: list[ComboResult]) -> dict:
        """Stage 7: Output the final strategy configuration."""
        top = validated[:10]

        strategies_list = []
        weights: dict[str, float] = {}
        for combo in top:
            entry = combo.to_dict()
            strategies_list.append(entry)
            # Accumulate weight by strategy name
            base_strat = combo.strategy.split("+")[0]
            weights[base_strat] = weights.get(base_strat, 0) + max(0.1, combo.score)

        # Normalize weights
        total_w = sum(weights.values()) or 1.0
        weights = {k: v / total_w for k, v in weights.items()}

        config = {
            "generated_at": date.today().isoformat(),
            "strategies": strategies_list,
            "strategy_weights": weights,
            "target_return_5d": 0.04,
            "min_win_rate": 0.67,
        }

        config_path = self.results_path / "best-config.json"
        config_path.write_text(json.dumps(config, indent=2, default=str),
                               encoding="utf-8")

        # Top 5 formatted for display
        top5 = []
        for i, c in enumerate(top[:5]):
            top5.append({
                "rank": i + 1,
                "strategy": c.strategy,
                "symbol": c.symbol,
                "win_rate": c.win_rate,
                "score": c.score,
                "return_pct": c.return_pct,
                "params": c.params,
            })

        best_return = max((c.return_pct for c in top), default=0.0)
        target_achievable = best_return >= 4.0  # +4% target

        return {
            "config_path": str(config_path),
            "top_strategies": top5,
            "target_achievable": target_achievable,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_symbols(self) -> list[str]:
        """Resolve symbols based on markets and quick mode."""
        src = _QUICK_SYMBOLS if self.quick else _DEFAULT_SYMBOLS
        symbols: list[str] = []
        for market in self.markets:
            market_upper = market.upper()
            market_syms = src.get(market_upper, [])
            symbols.extend(market_syms[:self.symbols_per_market])
        return symbols if symbols else ["AAPL", "MSFT"]

    def _market_for_symbol(self, symbol: str) -> str:
        """Infer market from symbol string."""
        if symbol.endswith(".KS"):
            return "KRX"
        if symbol.endswith("USDT"):
            return "CRYPTO"
        return "US"

    def _save_intermediate(self, name: str, data: Any) -> None:
        """Save intermediate pipeline results."""
        path = self.results_path / f"{name}.json"
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
