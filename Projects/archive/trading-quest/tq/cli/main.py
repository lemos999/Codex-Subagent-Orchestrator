"""Trading Quest CLI -- command-line interface."""
from __future__ import annotations

import logging
import sys

import click

from tq import config

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _build_alert_manager():
    """Build AlertManager from env vars. Returns None if not configured."""
    from tq.alert.manager import AlertManager

    mgr = AlertManager()
    mgr.add_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
    if not mgr.channels:
        logger.warning("No alert channels configured; alerts disabled")
        return None
    return mgr


# ======================================================================
# Root CLI group
# ======================================================================

@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def cli(verbose: bool) -> None:
    """Trading Quest -- gamified algorithmic trading."""
    _setup_logging(verbose)


# ======================================================================
# Data commands
# ======================================================================

@cli.group()
def data() -> None:
    """Data management commands."""


@data.command("fetch")
@click.option("--market", default="US", help="Market (US, KRX, CRYPTO)")
@click.option("--symbols", default="AAPL,MSFT", help="Comma-separated symbols")
@click.option("--start", default="2024-01-01", help="Start date")
@click.option("--end", default="2024-12-31", help="End date")
@click.option("--interval", default="1d", help="Interval (1d, 1h, 5m, 1m)")
def data_fetch(market: str, symbols: str, start: str, end: str, interval: str) -> None:
    """Fetch market data and cache it."""
    from tq.data.fetcher import get_fetcher
    from tq.data.cache import DataCache

    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    fetcher = get_fetcher(market)
    cache = DataCache()

    for symbol in symbol_list:
        click.echo(f"Fetching {symbol} ({market}, {interval})...")
        try:
            df = fetcher.fetch_timeframe(symbol, start, end, interval)
            if df.empty:
                click.echo(f"  No data returned for {symbol}")
                continue
            if interval == "1d":
                rows = cache.save_daily(symbol, market.upper(), df)
            else:
                rows = cache.save_minute(symbol, market.upper(), df)
            click.echo(f"  Cached {rows} rows")
        except Exception as e:
            click.echo(f"  Error: {e}", err=True)


@data.command("status")
def data_status() -> None:
    """Show data cache status."""
    from tq.data.cache import DataCache

    cache = DataCache()
    status = cache.get_status()
    click.echo("Data Cache Status:")
    click.echo(f"  Daily OHLCV rows:   {status['daily_rows']:,}")
    click.echo(f"  Minute OHLCV rows:  {status['minute_rows']:,}")
    click.echo(f"  Daily symbols:      {status['daily_symbols']}")
    click.echo(f"  Minute symbols:     {status['minute_symbols']}")
    click.echo(f"  Universe symbols:   {status['universe_count']}")


@data.command("timeframe")
@click.option("--market", default="US", help="Market")
@click.option("--symbol", default="AAPL", help="Symbol")
@click.option("--start", default="2024-01-01", help="Start date")
@click.option("--end", default="2024-03-01", help="End date")
@click.option("--granularity", default="1d", help="Granularity (1m, 5m, 15m, 1h, 4h, 1d)")
def data_timeframe(market: str, symbol: str, start: str, end: str,
                   granularity: str) -> None:
    """Fetch data at a specific granularity."""
    from tq.data.fetcher import fetch_timeframe

    click.echo(f"Fetching {symbol} at {granularity} [{start} ~ {end}]...")
    df = fetch_timeframe(symbol, start, end, granularity, market)
    if df.empty:
        click.echo("No data returned.")
    else:
        click.echo(f"Fetched {len(df)} rows")
        click.echo(df.tail(5).to_string())


# ======================================================================
# Quest commands
# ======================================================================

@cli.group()
def quest() -> None:
    """Quest simulation commands."""


@quest.command("start")
@click.option("--quest-id", required=True, help="Quest identifier")
@click.option("--market", default="US", help="Market")
@click.option("--symbols", default="AAPL,MSFT", help="Comma-separated symbols")
@click.option("--start-date", default="2024-01-01", help="Visible start date")
@click.option("--capital", type=float, default=0, help="Initial capital (0=market default)")
@click.option("--strategy", "strategy_name", default="ma_crossover", help="Strategy name")
def quest_start(quest_id: str, market: str, symbols: str, start_date: str,
                capital: float, strategy_name: str) -> None:
    """Start a new quest."""
    from tq.quest.engine import QuestEngine

    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if capital <= 0:
        capital = config.DEFAULT_CAPITAL.get(market.upper(), 100_000)

    engine = QuestEngine(
        quest_id=quest_id, market=market, symbols=symbol_list,
        initial_capital=capital,
    )
    state = engine.start_quest(start_date, strategy_name)
    click.echo(f"Quest {quest_id} started. Phase 1, date={state.current_date}")


@quest.command("run")
@click.option("--quest-id", required=True, help="Quest identifier")
@click.option("--market", default="US", help="Market (US, KRX, CRYPTO)")
@click.option("--symbols", default="AAPL,MSFT", help="Comma-separated symbols")
@click.option("--days", type=int, default=10, help="Number of trading days")
@click.option("--start-date", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--capital", type=float, default=100_000.0, help="Initial capital")
@click.option("--strategy", "strategy_name", default="default", help="Strategy name")
@click.option("--alerts/--no-alerts", default=False, help="Enable Telegram alerts")
def quest_run(quest_id: str, market: str, symbols: str, days: int,
              start_date: str | None, capital: float, strategy_name: str,
              alerts: bool) -> None:
    """Run a trading quest simulation."""
    from tq.quest.engine import QuestEngine

    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]

    alert_manager = None
    if alerts:
        alert_manager = _build_alert_manager()

    engine = QuestEngine(
        quest_id=quest_id, market=market, symbols=symbol_list,
        initial_capital=capital, alert_manager=alert_manager,
    )
    try:
        state = engine.resume_quest(quest_id)
    except FileNotFoundError:
        state = None

    if start_date is None:
        start_date = state.current_date if state else "2024-01-15"

    active_strategy = strategy_name
    if active_strategy == "default" and state and state.strategy_name:
        active_strategy = state.strategy_name

    click.echo(
        f"Running quest {quest_id}: {days} days, {len(engine.symbols)} symbols, "
        f"strategy={active_strategy}"
    )
    result = engine.run(start_date, days, strategy_name)
    click.echo(f"Done. Score: {result['total_score']:.0f}, Trades: {result['total_trades']}, "
               f"Return: {result.get('return_pct', 0):.2f}%")


@quest.command("status")
@click.option("--quest-id", required=True, help="Quest identifier")
def quest_status(quest_id: str) -> None:
    """Show quest status."""
    from tq.quest.state import QuestState

    try:
        state = QuestState.load(quest_id)
        click.echo(f"Quest: {state.quest_id}")
        click.echo(f"  Market: {state.market}")
        click.echo(f"  Phase: {state.phase}")
        click.echo(f"  Day: {state.current_day}")
        click.echo(f"  Capital: {state.current_capital:,.0f}")
        click.echo(f"  Score: {state.total_score:,.0f}")
        click.echo(f"  Strategy: {state.strategy_name}")
        click.echo(f"  Trades: {len(state.trade_log)}")
    except FileNotFoundError:
        click.echo(f"Quest {quest_id} not found.", err=True)
        sys.exit(1)


@quest.command("backtest")
@click.option("--market", default="US", help="Market")
@click.option("--symbols", default="AAPL,MSFT", help="Comma-separated symbols")
@click.option("--strategy", "strategy_name", default="ma_crossover", help="Strategy name")
@click.option("--start-date", default="2024-01-01", help="Start date")
@click.option("--days", type=int, default=30, help="Trading days")
@click.option("--capital", type=float, default=100_000, help="Initial capital")
def quest_backtest(market: str, symbols: str, strategy_name: str,
                   start_date: str, days: int, capital: float) -> None:
    """Backtest a strategy."""
    from tq.quest.engine import QuestEngine

    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    quest_id = f"backtest-{strategy_name}"

    engine = QuestEngine(
        quest_id=quest_id, market=market, symbols=symbol_list,
        initial_capital=capital,
    )
    click.echo(f"Backtesting {strategy_name} on {market} ({days} days)...")
    result = engine.run(start_date, days, strategy_name)

    click.echo(f"\nResults:")
    click.echo(f"  Days: {result['days']}")
    click.echo(f"  Trades: {result['total_trades']}")
    click.echo(f"  Score: {result['total_score']:.0f}")
    click.echo(f"  Return: {result.get('return_pct', 0):.2f}%")
    click.echo(f"  Max Drawdown: {result.get('max_drawdown', 0):.2%}")


@quest.command("optimize")
@click.option("--market", default="US", help="Market")
@click.option("--symbols", default="AAPL,MSFT", help="Symbols")
@click.option("--strategy", "strategy_name", default="ma_crossover", help="Strategy")
@click.option("--days", type=int, default=60, help="Days")
@click.option("--generations", type=int, default=5, help="Evolution generations")
def quest_optimize(market: str, symbols: str, strategy_name: str,
                   days: int, generations: int) -> None:
    """Optimize strategy parameters using genetic algorithm."""
    from tq.quest.evolver import StrategyEvolver

    click.echo(f"Optimizing {strategy_name} ({generations} generations)...")

    # Default param ranges per strategy
    param_ranges = {
        "fast_period": (5, 25),
        "slow_period": (20, 60),
    }

    evolver = StrategyEvolver(param_ranges, population_size=10)

    def fitness_fn(params):
        # Simple fitness: score from a quick backtest
        from tq.quest.engine import QuestEngine
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        engine = QuestEngine(
            quest_id="opt-tmp", market=market, symbols=symbol_list,
            initial_capital=100_000,
        )
        try:
            engine.set_strategy(strategy_name)
            if engine.strategy:
                engine.strategy.configure(params)
            result = engine.run("2024-01-01", min(days, 20), strategy_name)
            return result.get("total_score", 0)
        except Exception:
            return -1000

    best = evolver.run(fitness_fn, generations)
    click.echo(f"\nBest params: {best.params}")
    click.echo(f"Best fitness: {best.fitness:.2f}")


@quest.command("run-full")
@click.option("--quest-id", required=True, help="Quest ID")
@click.option("--market", default="US", help="Market")
@click.option("--symbols", default="AAPL,MSFT", help="Symbols")
@click.option("--strategy", "strategy_name", default="ma_crossover", help="Strategy")
@click.option("--target-phase", type=int, default=3, help="Target phase")
@click.option("--max-days", type=int, default=100, help="Max trading days")
def quest_run_full(quest_id: str, market: str, symbols: str,
                   strategy_name: str, target_phase: int, max_days: int) -> None:
    """Run quest to a target phase."""
    from tq.quest.engine import QuestEngine

    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    capital = config.DEFAULT_CAPITAL.get(market.upper(), 100_000)

    engine = QuestEngine(
        quest_id=quest_id, market=market, symbols=symbol_list,
        initial_capital=capital,
    )
    engine.start_quest("2024-01-01", strategy_name)
    click.echo(f"Running quest to phase {target_phase}...")
    result = engine.run_to_phase(target_phase, max_days)
    click.echo(f"Done. Final phase: {result['final_phase']}, Score: {result['total_score']:.0f}")


@quest.command("compare")
@click.option("--market", default="US", help="Market")
@click.option("--strategies", default="ma_crossover,rsi,macd", help="Comma-separated strategies")
@click.option("--symbols", default="AAPL,MSFT", help="Symbols")
@click.option("--days", type=int, default=30, help="Trading days")
@click.option("--start-date", default="2024-01-01", help="Start date")
def quest_compare(market: str, strategies: str, symbols: str,
                  days: int, start_date: str) -> None:
    """Compare multiple strategies."""
    from tq.quest.engine import QuestEngine
    from tq.quest.ranking import StrategyRanker, StrategyResult

    strategy_list = [s.strip() for s in strategies.split(",") if s.strip()]
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    capital = config.DEFAULT_CAPITAL.get(market.upper(), 100_000)

    ranker = StrategyRanker()

    for strat in strategy_list:
        click.echo(f"Running {strat}...")
        engine = QuestEngine(
            quest_id=f"compare-{strat}", market=market, symbols=symbol_list,
            initial_capital=capital,
        )
        result = engine.run(start_date, days, strat)

        ranker.add_result(StrategyResult(
            strategy_name=strat,
            total_return_pct=result.get("return_pct", 0),
            total_trades=result.get("total_trades", 0),
            composite_score=result.get("total_score", 0),
            max_drawdown=result.get("max_drawdown", 0),
            days=result.get("days", 0),
        ))

    click.echo("\n" + ranker.format_leaderboard())


@quest.command("report")
@click.option("--quest-id", required=True, help="Quest identifier")
@click.option("--output", default=None, help="Save to file path")
def quest_report(quest_id: str, output: str | None) -> None:
    """Generate a text report for a quest."""
    from tq.quest.report import QuestReport

    reporter = QuestReport()
    try:
        text = reporter.generate(quest_id)
    except FileNotFoundError:
        click.echo(f"Quest {quest_id} not found.", err=True)
        import sys; sys.exit(1)

    if output:
        from pathlib import Path
        Path(output).write_text(text, encoding="utf-8")
        click.echo(f"Report saved to {output}")
    else:
        click.echo(text)


@quest.command("report-compare")
@click.option("--market", default="US", help="Market (US, KRX, CRYPTO)")
@click.option("--strategies", required=True, help="Comma-separated strategies")
@click.option("--symbols", required=True, help="Comma-separated symbols")
@click.option("--days", type=int, default=50, help="Number of trading days")
def quest_report_compare(market: str, strategies: str, symbols: str, days: int) -> None:
    """Generate a comparison text report."""
    from tq.quest.report import QuestReport

    reporter = QuestReport()
    text = reporter.compare_report(market, strategies, symbols, days)
    click.echo(text)


@quest.command("evolve")
@click.option("--market", default="US", help="Market")
@click.option("--symbols", default="AAPL,MSFT", help="Symbols")
@click.option("--strategy", "strategy_name", default="ma_crossover", help="Strategy")
@click.option("--generations", type=int, default=10, help="Generations")
@click.option("--population", type=int, default=20, help="Population size")
@click.option("--alerts/--no-alerts", default=False, help="Enable alerts")
def quest_evolve(market: str, symbols: str, strategy_name: str,
                 generations: int, population: int, alerts: bool) -> None:
    """Evolve strategy parameters using genetic algorithm."""
    from tq.quest.evolver import StrategyEvolver

    alert_manager = None
    if alerts:
        alert_manager = _build_alert_manager()

    click.echo(f"Evolving {strategy_name} ({generations} gens, pop={population})...")
    param_ranges = {"fast_period": (5, 25), "slow_period": (20, 60)}

    evolver = StrategyEvolver(param_ranges, population_size=population)

    def fitness_fn(params):
        from tq.quest.engine import QuestEngine
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        engine = QuestEngine(
            quest_id="evo-tmp", market=market, symbols=symbol_list,
        )
        try:
            engine.set_strategy(strategy_name)
            if engine.strategy:
                engine.strategy.configure(params)
            result = engine.run("2024-01-01", 20, strategy_name)
            return result.get("total_score", 0)
        except Exception:
            return -1000

    best = evolver.run(fitness_fn, generations)
    click.echo(f"\nBest: {best.params} (fitness={best.fitness:.2f})")

    if alert_manager:
        try:
            alert_manager.notify_evolution({
                "generation": evolver.generation,
                "best_strategy": strategy_name,
                "best_score": best.fitness,
                "population_size": population,
            })
        except Exception:
            pass


# ======================================================================
# Journal commands
# ======================================================================

@cli.group()
def journal() -> None:
    """Trading journal and analysis."""


@journal.command("stats")
def journal_stats() -> None:
    """Show trading journal statistics (return-weighted scoring)."""
    from tq.journal.journal import TradingJournal

    j = TradingJournal()
    stats = j.get_statistics()
    click.echo("Trading Journal Statistics (return-weighted scoring):")
    click.echo(f"  Total Trades:    {stats['total_trades']}")
    click.echo(f"  Wins:            {stats['wins']}")
    click.echo(f"  Losses:          {stats['losses']}")
    click.echo(f"  Win Rate:        {stats['win_rate']:.1%}")
    click.echo(f"  Avg Win:         {stats['avg_win']:,.2f}")
    click.echo(f"  Avg Loss:        {stats['avg_loss']:,.2f}")
    click.echo(f"  Profit Factor:   {stats['profit_factor']:.2f}")
    click.echo(f"  Total Score:     {stats['total_score']:+.1f} (return-weighted)")
    click.echo(f"  Total PnL:       {stats['total_pnl']:,.2f}")
    click.echo(f"  Best Strategy:   {stats['best_strategy'] or 'N/A'}")
    click.echo(f"  Worst Strategy:  {stats['worst_strategy'] or 'N/A'}")
    click.echo(f"  Current Streak:  {stats['current_streak']}")
    click.echo(f"  Max Drawdown:    {stats['max_drawdown']:,.2f}")
    click.echo("")
    click.echo("  Scoring: Win = +0.1 + (return% x 10), Loss = -0.2 - (|return%| x 10)")
    click.echo("  Break-even win rate: 67%+")


@journal.command("analyze")
@click.option("--days", type=int, default=10, help="Days to analyze")
def journal_analyze(days: int) -> None:
    """Analyze recent trades and show insights."""
    from tq.journal.journal import TradingJournal
    from tq.journal.analyzer import TradeAnalyzer

    j = TradingJournal()
    analyzer = TradeAnalyzer(j)
    report = analyzer.analyze_recent(days=days)
    click.echo(report.format())


@journal.command("rules")
def journal_rules() -> None:
    """Show current learned trading rules."""
    from tq.journal.rules import TradingRules

    rules = TradingRules()
    click.echo(rules.format_rules())


@journal.command("benchmark")
@click.option("--quick", is_flag=True, help="Quick mode: 3 periods only (3d, 30d, 1yr)")
def journal_benchmark(quick: bool) -> None:
    """Run full strategy benchmark across all time periods.

    10 strategies x 7 periods = 70 tests (or 30 in quick mode).
    """
    from tq.journal.benchmark import StrategyBenchmark

    benchmark = StrategyBenchmark()
    mode = "Quick (3 periods)" if quick else "Full (7 periods)"
    total = 30 if quick else 70
    click.echo(f"=== 전략 벤치마크 시작 ({mode}, {total} tests) ===")
    click.echo("")

    def progress(msg: str) -> None:
        click.echo(f"  {msg}")

    result = benchmark.run_full_benchmark(callback=progress, quick=quick)
    click.echo("")
    click.echo(benchmark.format_results(result, quick=quick))


@journal.command("memory")
def journal_memory() -> None:
    """AI 트레이딩 메모리 상태를 표시합니다."""
    from tq.journal.memory import TradingMemory

    memory = TradingMemory()
    summary = memory.get_summary()

    click.echo("=== AI 트레이딩 메모리 ===")
    click.echo(f"  학습 세션:        {summary['sessions_count']}회")
    click.echo(f"  시도한 조합:      {summary['total_tried']}개")
    click.echo(f"  학습한 실수:      {summary['mistakes_count']}건")
    click.echo(f"  발견한 인사이트:  {summary['insights_count']}건")
    click.echo(f"  최초 점수:        {summary['first_score']:.1f}")
    click.echo(f"  최고 점수:        {summary['best_score']:.1f}")
    click.echo("")

    if summary["strategies_with_best"]:
        click.echo("  전략별 최적 파라미터:")
        for strat in summary["strategies_with_best"]:
            best = memory.get_best_params(strat)
            improvement = memory.get_cumulative_improvement(strat)
            click.echo(f"    {strat}: {best}")
            click.echo(
                f"      세션 {improvement['sessions_count']}회, "
                f"개선 {improvement['improvement_pct']:+.0f}%"
            )
        click.echo("")


@journal.command("forget")
@click.option("--strategy", default=None, help="특정 전략만 초기화 (없으면 전체)")
@click.confirmation_option(prompt="정말 메모리를 초기화하시겠습니까?")
def journal_forget(strategy: str | None) -> None:
    """AI 트레이딩 메모리를 초기화합니다."""
    from tq.journal.memory import TradingMemory

    memory = TradingMemory()
    if strategy:
        memory.forget(strategy)
        click.echo(f"'{strategy}' 전략의 메모리를 초기화했습니다.")
    else:
        memory.forget()
        click.echo("전체 메모리를 초기화했습니다.")


@journal.command("pipeline")
@click.option("--markets", default="US", help="Comma-separated markets")
@click.option("--symbols-per-market", type=int, default=10)
@click.option("--days", type=int, default=100, help="Days per backtest window")
@click.option("--quick", is_flag=True, help="Quick mode: fewer combinations")
def journal_pipeline(markets: str, symbols_per_market: int, days: int,
                     quick: bool) -> None:
    """Run automated strategy discovery pipeline."""
    from tq.journal.pipeline import StrategyPipeline

    market_list = [m.strip().upper() for m in markets.split(",") if m.strip()]

    click.echo("=== Strategy Discovery Pipeline ===")
    click.echo("")

    def progress(stage: str, msg: str) -> None:
        stage_upper = stage.upper()
        click.echo(f"  [{stage_upper}] {msg}")

    pipeline = StrategyPipeline(
        markets=market_list,
        symbols_per_market=symbols_per_market,
        quick=quick,
    )

    result = pipeline.run_full_pipeline(days_per_test=days, callback=progress)

    click.echo("")
    click.echo(f"Stage 1: SCAN")
    click.echo(f"  Combinations tested: {result.scan_count}")
    click.echo(f"  Total trades: {result.total_trades:,}")
    click.echo("")
    click.echo(f"Stage 2: ANALYZE")
    click.echo(f"  Winning combos (67%+ WR & score > 0): {result.winning_combos}")
    click.echo("")
    click.echo(f"Stage 3: FILTER")
    click.echo(f"  After significance filter: {result.filtered_combos} combos")
    click.echo("")
    click.echo(f"Stage 4: OPTIMIZE")
    click.echo(f"  Optimized combos: {result.optimized_combos}")
    click.echo("")
    click.echo(f"Stage 5: COMBINE")
    click.echo(f"  Fusion strategies tested: {result.fusion_combos}")
    click.echo("")
    click.echo(f"Stage 6: VALIDATE")
    click.echo(f"  Validated: {result.validated_combos}")
    click.echo("")
    click.echo(f"Stage 7: DEPLOY")
    if result.config_path:
        click.echo(f"  Saved best config to {result.config_path}")
    click.echo("")

    if result.top_strategies:
        click.echo("  TOP STRATEGIES:")
        for s in result.top_strategies:
            params_str = ""
            if s.get("params"):
                params_str = f" {s['params']}"
            click.echo(
                f"  {s['rank']}. {s['strategy']}{params_str} on {s['symbol']}"
                f"     -> WR:{s['win_rate']:.0%}, "
                f"{s['score']:+.1f}pts, "
                f"{s['return_pct']:+.1f}% return"
            )
        click.echo("")

    achievable = "YES" if result.target_achievable else "NO (need more optimization)"
    click.echo(f"  Target +4%/5d achievable: {achievable}")


# ======================================================================
# Strategy commands
# ======================================================================

@cli.group()
def strategy() -> None:
    """Strategy management commands."""


@strategy.command("list")
def strategy_list() -> None:
    """List available strategies."""
    from tq.strategy.registry import list_all

    strategies = list_all()
    click.echo(f"Available strategies ({len(strategies)}):")
    for name in strategies:
        click.echo(f"  - {name}")


@strategy.command("create")
@click.option("--name", required=True, help="Strategy name")
def strategy_create(name: str) -> None:
    """Create a new strategy script from template."""
    from tq.strategy.script_engine import create_script_template

    path = create_script_template(name)
    click.echo(f"Created strategy template: {path}")
    click.echo("Edit the file and implement your decide() method.")


@strategy.command("train")
@click.option("--model", type=click.Choice(["lstm", "dqn"]), required=True,
              help="ML model to train")
@click.option("--symbol", default="AAPL", help="Symbol to train on")
@click.option("--market", default="US", help="Market (US, KRX, CRYPTO)")
@click.option("--start", default="2024-01-01", help="Training data start date")
@click.option("--end", default="2024-12-31", help="Training data end date")
@click.option("--episodes", type=int, default=100,
              help="Training episodes (DQN only)")
@click.option("--epochs", type=int, default=30,
              help="Training epochs (LSTM only)")
def strategy_train(model: str, symbol: str, market: str, start: str,
                   end: str, episodes: int, epochs: int) -> None:
    """Pre-train an ML model on historical data."""
    from pathlib import Path
    from tq.data.fetcher import get_fetcher
    from tq.strategy.ml.features import FeatureEngineering

    click.echo(f"Fetching {symbol} data ({start} to {end})...")
    fetcher = get_fetcher(market)
    try:
        data = fetcher.fetch_timeframe(symbol, start, end, "1d")
    except Exception as e:
        click.echo(f"Error fetching data: {e}", err=True)
        sys.exit(1)

    if data.empty or len(data) < 80:
        click.echo(f"Insufficient data ({len(data)} rows, need >= 80)", err=True)
        sys.exit(1)

    feat_eng = FeatureEngineering()
    feat_df = feat_eng.build_features(data)
    click.echo(f"Built {feat_df.shape[1]} features from {len(feat_df)} rows")

    if model == "lstm":
        from tq.strategy.ml.lstm_model import LSTMPredictor

        labels = feat_eng.build_labels(data)
        X, y = feat_eng.prepare_sequences(feat_df, labels, seq_length=30)
        if len(X) < 10:
            click.echo("Not enough sequences for training", err=True)
            sys.exit(1)

        click.echo(f"Training LSTM ({epochs} epochs, {len(X)} sequences)...")
        predictor = LSTMPredictor(seq_length=30, hidden_size=64, epochs=epochs)
        metrics = predictor.train(X, y)

        model_dir = Path("models") / "lstm" / symbol
        predictor.save(model_dir)
        click.echo(
            f"Done. Accuracy: {metrics['final_accuracy']:.3f}, "
            f"Loss: {metrics['loss_history'][-1]:.4f}"
        )
        click.echo(f"Model saved to {model_dir}")

    elif model == "dqn":
        from tq.strategy.ml.dqn_agent import DQNAgent, TradingEnvironment

        env = TradingEnvironment(data, feat_df, initial_cash=100_000.0)
        agent = DQNAgent(state_size=env.state_size, hidden_size=64)

        click.echo(f"Training DQN ({episodes} episodes)...")
        rewards = agent.train(env, episodes=episodes)
        agent.epsilon = agent.epsilon_min

        model_dir = Path("models") / "dqn" / symbol
        agent.save(model_dir)
        avg = sum(rewards[-10:]) / max(len(rewards[-10:]), 1)
        click.echo(
            f"Done. Avg reward (last 10): {avg:.4f}, "
            f"Final epsilon: {agent.epsilon:.4f}"
        )
        click.echo(f"Model saved to {model_dir}")


# ======================================================================
# Serve command
# ======================================================================

@cli.command()
@click.option("--host", default="0.0.0.0", help="Host")
@click.option("--port", type=int, default=5000, help="Port")
@click.option("--debug/--no-debug", default=True, help="Debug mode")
def serve(host: str, port: int, debug: bool) -> None:
    """Start the web dashboard."""
    from tq.web.app import run_server

    click.echo(f"Starting web dashboard at http://{host}:{port}")
    run_server(host=host, port=port, debug=debug)


# ======================================================================
# Live trading commands
# ======================================================================

@cli.group()
def live() -> None:
    """Live/paper trading."""


@live.command("paper")
@click.option("--market", default="us", help="Market (us, kr, crypto)")
@click.option("--strategy", "strategy_name", default="ma_crossover", help="Strategy name")
@click.option("--symbols", default="AAPL", help="Comma-separated symbols")
@click.option("--capital", type=float, default=100_000.0, help="Initial capital")
@click.option("--interval", type=int, default=60, help="Check interval in seconds")
@click.option("--alerts/--no-alerts", default=True, help="Enable Telegram alerts")
def live_paper(market: str, strategy_name: str, symbols: str, capital: float,
               interval: int, alerts: bool) -> None:
    """Start paper trading with real-time data."""
    from tq.live.paper_broker import PaperBroker
    from tq.live.runner import LiveRunner
    from tq.strategy.registry import get_strategy

    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]

    alert_manager = None
    if alerts:
        alert_manager = _build_alert_manager()

    broker = PaperBroker(market=market, initial_capital=capital)
    broker.connect()

    try:
        strat = get_strategy(strategy_name)
    except KeyError:
        click.echo(f"Error: unknown strategy '{strategy_name}'", err=True)
        sys.exit(1)

    runner = LiveRunner(
        broker=broker, strategy=strat, market=market,
        symbols=symbol_list, alert_manager=alert_manager,
    )

    click.echo(f"Paper trading: {len(symbol_list)} symbols, interval={interval}s, capital={capital:,.0f}")
    runner.start_loop(interval_seconds=interval)


@live.command("binance")
@click.option("--testnet/--mainnet", default=True, help="Use Binance testnet")
@click.option("--strategy", "strategy_name", default="ma_crossover", help="Strategy name")
@click.option("--symbols", default="BTCUSDT", help="Comma-separated symbols")
@click.option("--interval", type=int, default=60, help="Check interval in seconds")
@click.option("--alerts/--no-alerts", default=True, help="Enable Telegram alerts")
def live_binance(testnet: bool, strategy_name: str, symbols: str,
                 interval: int, alerts: bool) -> None:
    """Start live trading via Binance."""
    from tq.live.binance_broker import BinanceBroker
    from tq.live.runner import LiveRunner
    from tq.strategy.registry import get_strategy

    if not testnet:
        click.echo("WARNING: This will use REAL money. Continue? [y/N]", err=True)
        confirm = input().strip().lower()
        if confirm != "y":
            click.echo("Aborted.")
            sys.exit(0)

    api_key = config.BINANCE_API_KEY
    api_secret = config.BINANCE_API_SECRET
    if not api_key or not api_secret:
        click.echo("Error: TQ_BINANCE_API_KEY and TQ_BINANCE_API_SECRET must be set", err=True)
        sys.exit(1)

    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]

    alert_manager = None
    if alerts:
        alert_manager = _build_alert_manager()

    broker = BinanceBroker(api_key=api_key, api_secret=api_secret, testnet=testnet)
    if not broker.connect():
        click.echo("Error: failed to connect to Binance", err=True)
        sys.exit(1)

    try:
        strat = get_strategy(strategy_name)
    except KeyError:
        click.echo(f"Error: unknown strategy '{strategy_name}'", err=True)
        sys.exit(1)

    runner = LiveRunner(
        broker=broker, strategy=strat, market="crypto",
        symbols=symbol_list, alert_manager=alert_manager,
    )

    mode_str = "TESTNET" if testnet else "MAINNET"
    click.echo(f"Binance {mode_str}: {len(symbol_list)} symbols, interval={interval}s")
    runner.start_loop(interval_seconds=interval)


# ======================================================================
# Entry point
# ======================================================================

if __name__ == "__main__":
    cli()
