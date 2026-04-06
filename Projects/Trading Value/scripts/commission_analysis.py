"""Commission impact analysis for F Fortress vs G Gladiator vs C Castle."""

comm_per_trade = 18.67  # $10K balance, ETH ~$2000, 0.04% taker round-trip
notional_per_trade = 23333

models = [
    ("C Castle",    38,  9219),
    ("F Fortress",  109, 23017),
    ("G Gladiator", 153, 183313),
]

print("=== Trading Volume Analysis (per quarter, $10K fixed capital) ===")
print()
print(f"{'Model':<16s} {'Entries':>8s} {'Volume':>12s} {'Comm':>10s} {'PnL':>12s} {'PnL/Ent':>10s} {'Comm/PnL':>10s}")
print("-" * 80)

for name, entries, pnl in models:
    vol = entries * notional_per_trade
    comm = vol * 0.0008
    pnl_per_ent = pnl / entries if entries > 0 else 0
    comm_pnl = comm / max(pnl, 1) * 100
    print(f"{name:<16s} {entries:>8d} ${vol:>11,} ${comm:>9,.0f} ${pnl:>+11,} ${pnl_per_ent:>9,.0f} {comm_pnl:>9.1f}%")

print()
print("Note: Commission is already included in backtest PnL.")
print("Above shows commission PORTION, not additional cost.")
print()

# Practical limits
print("=== Practical Limits ===")
print()
print("At $10K capital with 10x leverage:")
print(f"  Max notional per trade: ~$23K")
print(f"  Round-trip commission: ~$19")
print()

for name, entries, pnl in models:
    daily_trades = entries / 90  # ~90 days per quarter
    daily_comm = daily_trades * comm_per_trade
    print(f"  {name}:")
    print(f"    Trades/day: {daily_trades:.1f}")
    print(f"    Commission/day: ${daily_comm:.0f}")
    print(f"    Need ${daily_comm:.0f}/day profit just to break even on commission")
    print(f"    Actual profit/day: ${pnl/90:,.0f}")
    print()
