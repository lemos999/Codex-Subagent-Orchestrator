"""Analyze loss trades in sim_log JSONL files by failure stage."""
import json, glob, os
from datetime import datetime
from collections import defaultdict

DATA_DIR = "C:/Users/haj/projects/subagent-orchestrator/Projects/Trading Value/data"
files = sorted(glob.glob(os.path.join(DATA_DIR, "sim_log_*.jsonl")))

all_trades = []

for fpath in files:
    fname = os.path.basename(fpath)
    events = []
    with open(fpath) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    current_open = None
    current_cycles = []
    current_trails = []

    for ev in events:
        etype = ev.get("event")

        if etype == "OPEN":
            current_open = ev
            current_cycles = []
            current_trails = []
        elif etype == "CYCLE" and current_open:
            current_cycles.append(ev)
        elif etype == "TRAIL" and current_open:
            current_trails.append(ev)
        elif etype == "CLOSE" and current_open:
            open_price = current_open["price"]
            close_price = ev["price"]
            side = current_open.get("side", "LONG")
            pnl = ev["pnl"]
            open_time = datetime.fromisoformat(current_open["time"])
            close_time = datetime.fromisoformat(ev["time"])
            hold_duration = (close_time - open_time).total_seconds()
            hold_minutes = hold_duration / 60

            qty = current_open.get("qty", 0)
            commission = current_open.get("commission", 0)

            cycle_pnls = []
            for c in current_cycles:
                cp = c["price"]
                if side == "LONG":
                    unrealized = (cp - open_price) * qty - commission * 2
                else:
                    unrealized = (open_price - cp) * qty - commission * 2
                cycle_pnls.append(unrealized)

            peak_unrealized = max(cycle_pnls) if cycle_pnls else 0.0

            trade = {
                "file": fname,
                "side": side,
                "open_time": current_open["time"],
                "close_time": ev["time"],
                "open_price": open_price,
                "close_price": close_price,
                "pnl": pnl,
                "hold_minutes": hold_minutes,
                "close_reason": ev.get("reason", "unknown"),
                "peak_unrealized": peak_unrealized,
                "had_trailing": len(current_trails) > 0,
                "n_cycles": len(current_cycles),
                "cycle_pnls": cycle_pnls,
                "qty": qty,
                "commission": commission,
            }
            all_trades.append(trade)
            current_open = None

losses = [t for t in all_trades if t["pnl"] < 0]
wins = [t for t in all_trades if t["pnl"] >= 0]

print("=" * 60)
print("TRADE OVERVIEW")
print("=" * 60)
print(f"Total files analyzed: {len(files)}")
print(f"Total trades: {len(all_trades)}")
print(f"Wins: {len(wins)}  Losses: {len(losses)}")
if all_trades:
    print(f"Win rate: {len(wins)/len(all_trades)*100:.1f}%")
if wins:
    print(f"Avg win: ${sum(t['pnl'] for t in wins)/len(wins):.2f}")
if losses:
    print(f"Avg loss: ${sum(t['pnl'] for t in losses)/len(losses):.2f}")
print()

# Classify losses
entry_failures = []
hold_failures = []
exit_failures = []

for t in losses:
    peak = t["peak_unrealized"]
    loss_size = abs(t["pnl"])

    if peak <= 0:
        entry_failures.append(t)
    elif peak > 0 and peak >= loss_size * 0.3:
        hold_failures.append(t)
    else:
        exit_failures.append(t)

total_loss_pnl = sum(abs(t["pnl"]) for t in losses)
entry_loss_pnl = sum(abs(t["pnl"]) for t in entry_failures)
hold_loss_pnl = sum(abs(t["pnl"]) for t in hold_failures)
exit_loss_pnl = sum(abs(t["pnl"]) for t in exit_failures)

print("=" * 60)
print("LOSS CLASSIFICATION")
print("=" * 60)
print(f"Total losses: {len(losses)} trades, ${total_loss_pnl:.2f} total loss amount")
print()

cats = [
    ("ENTRY FAILURE", entry_failures, entry_loss_pnl,
     "Never profitable - immediate reversal after entry"),
    ("HOLD FAILURE", hold_failures, hold_loss_pnl,
     "Was profitable (peak >= 30% of loss) then reversed"),
    ("EXIT FAILURE", exit_failures, exit_loss_pnl,
     "Marginal profit, poor stop/exit timing"),
]

for name, trades, loss_amt, desc in cats:
    pct_count = len(trades) / len(losses) * 100 if losses else 0
    pct_pnl = loss_amt / total_loss_pnl * 100 if total_loss_pnl else 0
    print(f"  {name}: {len(trades)} trades ({pct_count:.1f}%)  |  "
          f"${loss_amt:.2f} ({pct_pnl:.1f}% of loss $)")
    print(f"    {desc}")
    if trades:
        avg_loss = sum(t["pnl"] for t in trades) / len(trades)
        avg_hold = sum(t["hold_minutes"] for t in trades) / len(trades)
        reasons = defaultdict(int)
        for t in trades:
            reasons[t["close_reason"]] += 1
        print(f"    Avg PnL: ${avg_loss:.2f}  |  Avg hold: {avg_hold:.1f} min  |  "
              f"Reasons: {dict(reasons)}")
        if name == "HOLD FAILURE":
            avg_peak = sum(t["peak_unrealized"] for t in trades) / len(trades)
            print(f"    Avg peak unrealized before reversal: ${avg_peak:.2f}")
    print()

print("=" * 60)
print("DOMINANT FAILURE STAGE")
print("=" * 60)
dominant_found = False
for name, trades, loss_amt, desc in cats:
    pct_pnl = loss_amt / total_loss_pnl * 100 if total_loss_pnl else 0
    pct_count = len(trades) / len(losses) * 100 if losses else 0
    if pct_pnl >= 50:
        print(f"  >>> {name} accounts for {pct_pnl:.1f}% of total loss dollars <<<")
        dominant_found = True
    if pct_count >= 50:
        print(f"  >>> {name} accounts for {pct_count:.1f}% of loss trade count <<<")
        dominant_found = True
if not dominant_found:
    print("  No single category exceeds 50%")
    for name, trades, loss_amt, desc in cats:
        pct_pnl = loss_amt / total_loss_pnl * 100 if total_loss_pnl else 0
        print(f"    {name}: {pct_pnl:.1f}% of loss $")

print()
print("=" * 60)
print("LOSS BY CLOSE REASON")
print("=" * 60)
reason_stats = defaultdict(lambda: {"count": 0, "pnl": 0})
for t in losses:
    r = t["close_reason"]
    reason_stats[r]["count"] += 1
    reason_stats[r]["pnl"] += t["pnl"]
for r, s in sorted(reason_stats.items(), key=lambda x: x[1]["pnl"]):
    print(f"  {r:20s}: {s['count']:4d} trades  |  ${s['pnl']:.2f}")

print()
print("=" * 60)
print("LOSS BY ASSET")
print("=" * 60)

def get_asset(fname):
    parts = fname.replace("sim_log_", "").replace(".jsonl", "")
    if "_" in parts:
        return parts.rsplit("_", 1)[0]
    return "ETH"

asset_stats = defaultdict(lambda: {
    "total": 0, "losses": 0, "loss_pnl": 0,
    "entry": 0, "hold": 0, "exit": 0
})
for t in all_trades:
    asset = get_asset(t["file"])
    asset_stats[asset]["total"] += 1
    if t["pnl"] < 0:
        asset_stats[asset]["losses"] += 1
        asset_stats[asset]["loss_pnl"] += t["pnl"]

for t in entry_failures:
    asset_stats[get_asset(t["file"])]["entry"] += 1
for t in hold_failures:
    asset_stats[get_asset(t["file"])]["hold"] += 1
for t in exit_failures:
    asset_stats[get_asset(t["file"])]["exit"] += 1

for asset, s in sorted(asset_stats.items()):
    wr = (s["total"] - s["losses"]) / s["total"] * 100 if s["total"] else 0
    print(f"  {asset:5s}: {s['total']:4d} trades, {s['losses']:4d} losses "
          f"(WR {wr:.0f}%)  |  Loss ${s['loss_pnl']:.2f}  |  "
          f"Entry:{s['entry']}  Hold:{s['hold']}  Exit:{s['exit']}")

print()
print("=" * 60)
print("LOSS HOLD DURATION DISTRIBUTION")
print("=" * 60)
bins = [
    (0, 5, "0-5 min"), (5, 15, "5-15 min"), (15, 30, "15-30 min"),
    (30, 60, "30-60 min"), (60, 120, "1-2 hr"), (120, 999999, "2+ hr")
]
for lo, hi, label in bins:
    in_bin = [t for t in losses if lo <= t["hold_minutes"] < hi]
    if in_bin:
        pnl_sum = sum(t["pnl"] for t in in_bin)
        print(f"  {label:10s}: {len(in_bin):4d} trades  |  ${pnl_sum:.2f}")

# Entry failure deep-dive: how quickly do they fail?
print()
print("=" * 60)
print("ENTRY FAILURE DEEP-DIVE")
print("=" * 60)
if entry_failures:
    # How many had zero cycles (closed before first cycle)?
    zero_cycle = [t for t in entry_failures if t["n_cycles"] == 0]
    print(f"  Zero cycles (closed before 1st 30-min check): "
          f"{len(zero_cycle)}/{len(entry_failures)}")
    # All cycle prices were below entry for LONG
    all_negative = [t for t in entry_failures if all(p < 0 for p in t["cycle_pnls"])]
    print(f"  Never positive at any cycle: {len(all_negative)}/{len(entry_failures)}")
    # Duration breakdown
    quick = [t for t in entry_failures if t["hold_minutes"] <= 10]
    medium = [t for t in entry_failures if 10 < t["hold_minutes"] <= 30]
    slow = [t for t in entry_failures if t["hold_minutes"] > 30]
    print(f"  <= 10 min: {len(quick)}  |  10-30 min: {len(medium)}  |  > 30 min: {len(slow)}")

print()
print("=" * 60)
print("HOLD FAILURE DEEP-DIVE")
print("=" * 60)
if hold_failures:
    for t in hold_failures[:10]:
        asset = get_asset(t["file"])
        peak_r = t["peak_unrealized"] / abs(t["pnl"]) if t["pnl"] != 0 else 0
        print(f"  {asset} {t['side']} | peak ${t['peak_unrealized']:.0f} -> "
              f"loss ${t['pnl']:.0f} ({peak_r:.1f}x) | "
              f"hold {t['hold_minutes']:.0f}min | {t['close_reason']} | "
              f"trail={'Y' if t['had_trailing'] else 'N'}")
