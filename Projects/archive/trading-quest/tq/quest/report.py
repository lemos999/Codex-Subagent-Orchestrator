"""Quest report generator — produces concise text reports for backtesting results."""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


class QuestReport:
    """Generate concise text reports for backtesting results."""

    BORDER = "=" * 39

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, quest_id: str) -> str:
        """Load quest state and produce a formatted text report."""
        from tq.quest.state import QuestState

        state = QuestState.load(quest_id)
        return self._format_state_report(state)

    def compare_report(self, market: str, strategies: str, symbols: str, days: int) -> str:
        """Run comparison and produce a text report."""
        from tq.quest.engine import QuestEngine
        from tq.quest.ranking import StrategyRanker, StrategyResult
        from tq import config

        strategy_list = [s.strip() for s in strategies.split(",") if s.strip()]
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        capital = config.DEFAULT_CAPITAL.get(market.upper(), 100_000)

        ranker = StrategyRanker()
        results: list[dict] = []

        for strat in strategy_list:
            engine = QuestEngine(
                quest_id=f"compare-{strat}", market=market,
                symbols=symbol_list, initial_capital=capital,
            )
            result = engine.run("2024-01-01", days, strat)
            ranker.add_result(StrategyResult(
                strategy_name=strat,
                total_return_pct=result.get("return_pct", 0),
                total_trades=result.get("total_trades", 0),
                composite_score=result.get("total_score", 0),
                max_drawdown=result.get("max_drawdown", 0),
                days=result.get("days", 0),
            ))
            results.append({"strategy": strat, **result})

        lines: list[str] = [
            self.BORDER,
            "  Trading Quest — Strategy Comparison",
            f"  Market: {market.upper()} | Days: {days}",
            f"  Symbols: {', '.join(symbol_list)}",
            self.BORDER,
            "",
            ranker.format_leaderboard(),
            "",
            self.BORDER,
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _format_state_report(self, state) -> str:  # state: QuestState
        """Build the formatted text report from a QuestState."""
        trades = state.trade_log or []
        daily_results = state.daily_results or []

        # --- Performance metrics ---
        total_return_pct = self._calc_return_pct(
            state.initial_capital, state.current_capital
        )
        total_trades = len(trades)
        wins, losses = self._count_wins_losses(trades)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
        avg_win, avg_loss = self._avg_win_loss(trades)
        best_trade, worst_trade = self._best_worst(trades)
        max_drawdown = self._calc_max_drawdown(daily_results)
        profit_factor = self._calc_profit_factor(trades)
        sharpe = self._calc_sharpe(daily_results)
        score = state.total_score

        # --- Header ---
        period_start = state.start_date
        period_end = state.current_date
        lines: list[str] = [
            self.BORDER,
            "  Trading Quest Report",
            f"  Quest: {state.quest_id} | {state.strategy_name.upper()} | {state.market}",
            f"  Period: {period_start} ~ {period_end}",
            self.BORDER,
            "",
            "PERFORMANCE",
            f"  Total Return:    {total_return_pct:+.2f}%",
            f"  Total Trades:    {total_trades}",
            f"  Win Rate:        {win_rate:.1f}%",
            f"  Profit Factor:   {profit_factor:.2f}",
            f"  Max Drawdown:    {max_drawdown:.1f}%",
            f"  Sharpe Ratio:    {sharpe:.2f}",
            f"  Score:           {score:,.0f} pts",
            "",
            "TRADE SUMMARY",
            f"  Wins: {wins} | Losses: {losses}",
            f"  Avg Win:  {avg_win:+.2f}% | Avg Loss: {avg_loss:+.2f}%",
            f"  Best:     {best_trade:+.1f}%  | Worst:    {worst_trade:+.1f}%",
        ]

        # --- Top trades ---
        top_trades = self._top_trades(trades)
        if top_trades:
            lines.append("")
            lines.append("TOP TRADES")
            for t in top_trades:
                lines.append(f"  {t}")

        # --- Daily returns (last 10) ---
        last_days = daily_results[-10:] if daily_results else []
        if last_days:
            lines.append("")
            lines.append("DAILY RETURNS (last 10)")
            row = ""
            for i, day in enumerate(last_days):
                d = day.get("date", "??-??")
                # Shorten date to MM-DD if possible
                if len(d) >= 10:
                    d = d[5:10]  # "YYYY-MM-DD" -> "MM-DD"
                ret = day.get("return_pct", 0)
                sign = "+" if ret >= 0 else ""
                entry = f"  {d}: {sign}{ret:.2f}%"
                if i % 3 == 0 and i > 0:
                    lines.append(row)
                    row = entry
                else:
                    row = (row + "  " + entry).strip() if row else entry
            if row:
                lines.append(row)

        lines.append("")
        lines.append(self.BORDER)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Calculation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_return_pct(initial: float, current: float) -> float:
        if initial <= 0:
            return 0.0
        return (current - initial) / initial * 100

    @staticmethod
    def _count_wins_losses(trades: list[dict]) -> tuple[int, int]:
        wins = sum(1 for t in trades if t.get("pnl", t.get("return_pct", 0)) > 0)
        losses = sum(1 for t in trades if t.get("pnl", t.get("return_pct", 0)) <= 0)
        return wins, losses

    @staticmethod
    def _avg_win_loss(trades: list[dict]) -> tuple[float, float]:
        win_rets = [t.get("return_pct", 0) for t in trades
                    if t.get("pnl", t.get("return_pct", 0)) > 0]
        loss_rets = [t.get("return_pct", 0) for t in trades
                     if t.get("pnl", t.get("return_pct", 0)) <= 0]
        avg_win = sum(win_rets) / len(win_rets) if win_rets else 0.0
        avg_loss = sum(loss_rets) / len(loss_rets) if loss_rets else 0.0
        return avg_win, avg_loss

    @staticmethod
    def _best_worst(trades: list[dict]) -> tuple[float, float]:
        if not trades:
            return 0.0, 0.0
        rets = [t.get("return_pct", 0) for t in trades]
        return max(rets), min(rets)

    @staticmethod
    def _calc_max_drawdown(daily_results: list[dict]) -> float:
        """Return max drawdown as a positive percentage."""
        equity = []
        for d in daily_results:
            cap = d.get("capital", d.get("current_capital"))
            if cap is not None:
                equity.append(float(cap))
        if not equity:
            return 0.0
        peak = equity[0]
        max_dd = 0.0
        for val in equity:
            if val > peak:
                peak = val
            if peak > 0:
                dd = (peak - val) / peak * 100
                if dd > max_dd:
                    max_dd = dd
        return max_dd

    @staticmethod
    def _calc_profit_factor(trades: list[dict]) -> float:
        gross_win = sum(
            t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0
        )
        gross_loss = abs(sum(
            t.get("pnl", 0) for t in trades if t.get("pnl", 0) < 0
        ))
        if gross_loss == 0:
            return float("inf") if gross_win > 0 else 1.0
        return gross_win / gross_loss

    @staticmethod
    def _calc_sharpe(daily_results: list[dict], risk_free: float = 0.0) -> float:
        rets = [d.get("return_pct", 0) for d in daily_results]
        if len(rets) < 2:
            return 0.0
        mean = sum(rets) / len(rets)
        variance = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        std = variance ** 0.5
        if std == 0:
            return 0.0
        # Annualise (approx 252 trading days)
        return (mean - risk_free) / std * (252 ** 0.5)

    @staticmethod
    def _top_trades(trades: list[dict], n: int = 5) -> list[str]:
        """Return formatted strings for the top-n trades by absolute return."""
        if not trades:
            return []
        sorted_trades = sorted(
            trades,
            key=lambda t: abs(t.get("return_pct", 0)),
            reverse=True,
        )[:n]

        rows = []
        for t in sorted_trades:
            trade_date = t.get("date", t.get("entry_date", "????-??-??"))
            side = t.get("side", "?").upper()
            symbol = t.get("symbol", "???")
            entry = t.get("entry_price", t.get("price", 0))
            exit_price = t.get("exit_price", 0)
            ret = t.get("return_pct", 0)
            sign = "+" if ret >= 0 else ""
            if exit_price:
                rows.append(
                    f"  {trade_date}  {side}  {symbol}  @{entry:.2f}"
                    f"  -> SELL @{exit_price:.2f}  {sign}{ret:.2f}%"
                )
            else:
                rows.append(
                    f"  {trade_date}  {side}  {symbol}  @{entry:.2f}"
                    f"  {sign}{ret:.2f}%"
                )
        return rows
