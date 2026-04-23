"""Phase 14-B/15/15-A/15-C 통합 시뮬 — 창발 현상 관측.

500틱 시뮬 후 주요 이벤트 집계:
- Phase 14-B: grievance_announced, policy_update SNN 신호
- Phase 15: strike_executed, mass_exodus, density_warning
- Phase 15-A: policy_update with market_openness, trade inter_territory
- Phase 15-C: chronicle 축적, guard count, healer chronic_stress 감소
"""
import sys, time
from collections import Counter, defaultdict

sys.path.insert(0, ".")
from core.multi_tick_engine import MultiTickEngine

TICKS = 2000
GOODS_VALUE = {
    "food": 10, "material": 15, "tool": 60, "medicine": 30, "knowledge": 45,
}

def main():
    print("=" * 70)
    print(f"  Phase 14-B ~ 15-C Integrated Observation ({TICKS} ticks)")
    print("=" * 70, flush=True)

    engine = MultiTickEngine()

    # 초기 상태 스냅샷
    initial_gold = {pid: engine.wallets[pid].gold for pid in engine.personas}
    initial_chronic = {pid: float(engine.inners[pid].chronic_stress) for pid in engine.personas}
    initial_treasury = {tid: t.treasury_gold for tid, t in engine.territories.items()}
    initial_persona_goods = sum(
        inner.inventory.get(goods, 0) * value
        for inner in engine.inners.values()
        for goods, value in GOODS_VALUE.items()
    )
    initial_territory_goods = sum(
        territory.inventory.get(goods, 0) * value
        for territory in engine.territories.values()
        for goods, value in GOODS_VALUE.items()
    ) + sum(
        getattr(territory, "food_reserve", 0) * GOODS_VALUE["food"]
        for territory in engine.territories.values()
    )

    t0 = time.time()
    log = engine.run(n_ticks=TICKS, verbose=False)
    elapsed = time.time() - t0
    print(f"\n[runtime] {elapsed:.1f}s ({elapsed / TICKS * 1000:.1f}ms/tick)\n", flush=True)

    # ── 이벤트 집계 ──
    event_count = Counter()
    policy_updates = []
    trade_events = []
    strike_events = []
    exodus_events = []
    density_warnings = []
    public_works_events = []
    internal_food_events = []
    npc_food_stockpile_events = []
    market_food_trade_events = []
    npc_food_cooldown_skips = []
    public_works_skip_events = []
    farm_expansion_events = []
    farm_expansion_skip_events = []
    chronicle_samples = {tid: [] for tid in engine.territories}

    for tick_idx, tick_result in enumerate(log):
        for ev in tick_result.get("economy_events", []):
            et = ev.get("type", "unknown")
            event_count[et] += 1
            if et == "policy_update":
                policy_updates.append((tick_idx, ev))
            elif et == "trade":
                trade_events.append((tick_idx, ev))
                if ev.get("goods") == "food":
                    market_food_trade_events.append((tick_idx, ev))
            elif et in ("strike_executed", "strike"):
                strike_events.append((tick_idx, ev))
            elif et in ("mass_exodus", "exodus"):
                exodus_events.append((tick_idx, ev))
            elif et == "density_warning":
                density_warnings.append((tick_idx, ev))
            elif et == "public_works":
                public_works_events.append((tick_idx, ev))
            elif et == "internal_food_procurement":
                internal_food_events.append((tick_idx, ev))
            elif et == "food_stockpile" and ev.get("source") == "treasury_purchase":
                npc_food_stockpile_events.append((tick_idx, ev))
            elif et == "npc_food_purchase_cooldown_skip":
                npc_food_cooldown_skips.append((tick_idx, ev))
            elif et == "public_works_skip_reason":
                public_works_skip_events.append((tick_idx, ev))
            elif et == "farm_expansion":
                farm_expansion_events.append((tick_idx, ev))
            elif et == "farm_expansion_skip":
                farm_expansion_skip_events.append((tick_idx, ev))

    # ── 리포트 ──
    print("─" * 70)
    print("  Event Counts")
    print("─" * 70)
    for et, count in event_count.most_common():
        print(f"  {et:30s} {count:6d}")

    # Phase 14-B: grievance_announced + SNN policy
    print("\n" + "-" * 70)
    print("  Phase 14-B: SNN Political Integration")
    print("─" * 70)
    print(f"  grievance_announced events : {event_count.get('grievance_announced', 0)}")
    print(f"  exodus_blocked events      : {event_count.get('exodus_blocked', 0)}")
    print(f"  policy_update events       : {len(policy_updates)}")
    if policy_updates:
        last = policy_updates[-1][1]
        snn = last.get("snn_signals", {})
        print(f"  last policy (territory={last.get('territory')}):")
        print(f"    tax_rate={last.get('tax_rate')} food_priority={last.get('food_priority')}")
        print(f"    stockpile={last.get('stockpile_target')} spending_cap={last.get('spending_cap')}")
        print(f"    market_openness={last.get('market_openness')} density_ratio={last.get('density_ratio')}")
        print(f"    snn: tension={snn.get('tension')} stability={snn.get('stability')} growth={snn.get('growth')}")

    # Phase 15: 집단행동
    print("\n" + "-" * 70)
    print("  Phase 15: Collective Action")
    print("-" * 70)
    print(f"  strike_executed events     : {len(strike_events)}")
    print(f"  mass_exodus events         : {len(exodus_events)}")
    print(f"  density_warning events     : {len(density_warnings)}")
    if strike_events:
        print(f"  first strike at tick {strike_events[0][0]}, last at tick {strike_events[-1][0]}")

    # Phase 15-A: market_openness + inter-territory trade
    print("\n" + "─" * 70)
    print("  Phase 15-A: Market Openness")
    print("─" * 70)
    inter_trades = [ev for _, ev in trade_events if ev.get("inter_territory")]
    intra_trades = [ev for _, ev in trade_events if not ev.get("inter_territory")]
    print(f"  total trade events         : {len(trade_events)}")
    print(f"  inter-territory trades     : {len(inter_trades)}")
    print(f"  intra-territory trades     : {len(intra_trades)}")
    print("  territory market_openness (final):")
    for tid, territory in engine.territories.items():
        print(f"    {tid:15s} openness={territory.policy.market_openness:.3f} tax={territory.policy.tax_rate:.3f}")

    # Phase 15-C: chronicle + healer/guard
    print("\n" + "─" * 70)
    print("  Phase 15-C: Job Diversity")
    print("─" * 70)
    job_counts = Counter()
    for pid, persona in engine.personas.items():
        title = engine._get_persona_job_title(pid) or "unemployed"
        job_counts[title] += 1
    print("  final job distribution:")
    for title, n in job_counts.most_common():
        print(f"    {title:12s} {n}")

    print("  territory.chronicle counts:")
    for tid, territory in engine.territories.items():
        ch = getattr(territory, "chronicle", [])
        print(f"    {tid:15s} chronicle_len={len(ch)}")
        if ch:
            last = ch[-1]
            print(f"      last: tick={last.get('tick')} type={last.get('type')} summary={last.get('summary')}")

    # chronic_stress 변화 (healer 효과 간접 확인)
    print("  chronic_stress change (final - initial):")
    stress_changes = []
    for pid in engine.personas:
        delta = float(engine.inners[pid].chronic_stress) - initial_chronic[pid]
        stress_changes.append((pid, delta))
    stress_changes.sort(key=lambda x: x[1])
    for pid, delta in stress_changes[:5]:
        job = engine._get_persona_job_title(pid) or "-"
        print(f"    {pid:20s} job={job:10s} delta={delta:+.3f}")

    # Phase 16-B: Productive Public Works
    print("\n" + "-" * 70)
    print("  Phase 16-B: Productive Public Works")
    print("-" * 70)
    total_public_wage = sum(ev.get("wage", 0) for _, ev in public_works_events)
    avg_public_rate = (
        sum(ev.get("rate", 0) for _, ev in public_works_events)
        / max(1, len(public_works_events))
    )
    in_kind_total = defaultdict(float)
    for _, ev in public_works_events:
        in_kind_total[ev.get("produced_type", "?")] += float(
            ev.get("in_kind_to_territory", 0)
        )
    print(f"  public_works events        : {len(public_works_events)}")
    print(f"  total public wage paid     : {total_public_wage:.0f}")
    print(f"  avg rate                   : {avg_public_rate:.3f}")
    print("  in-kind goods to territory :")
    for goods, amount in sorted(in_kind_total.items()):
        print(f"    {goods:12s} {amount:.1f}")

    # Phase 16-C: Internal Food Market
    print("\n" + "-" * 70)
    print("  Phase 16-C: Internal Food Market")
    print("-" * 70)
    total_internal_food = sum(float(ev.get("qty", 0)) for _, ev in internal_food_events)
    total_internal_gold = sum(float(ev.get("cost", 0)) for _, ev in internal_food_events)
    total_market_food = sum(float(ev.get("qty", 0)) for _, ev in market_food_trade_events)
    total_npc_food = sum(
        float(ev.get("amount", ev.get("buy_qty", 0)) or 0)
        for _, ev in npc_food_stockpile_events
    )
    print(f"  internal_food_procurement events : {len(internal_food_events)}")
    print(f"  total food procured internally   : {total_internal_food:.1f}")
    print(f"  total gold to farmers (internal) : {total_internal_gold:.0f}")
    print(f"  food_stockpile events (NPC)      : {len(npc_food_stockpile_events)}")
    print("  food supply chain breakdown:")
    print(f"    internal (persona->territory) : {total_internal_food:.1f}")
    print(f"    market   (P2P order)         : {total_market_food:.1f}")
    print(f"    NPC      (treasury purchase) : {total_npc_food:.1f}")

    # Phase 16-D: Dynamic Reserve + Base Activation
    print("\n" + "-" * 70)
    print("  Phase 16-D: Dynamic Reserve + Base Activation")
    print("-" * 70)
    base_ratios = [
        float(ev.get("base_component", 0.0))
        / max(1e-9, float(ev.get("base_component", 0.0)) + float(ev.get("signal_component", 0.0)))
        for _, ev in public_works_events
        if "base_component" in ev and "signal_component" in ev
    ]
    reserve_targets = [
        float(ev.get("reserve_target", 0.0))
        for _, ev in npc_food_stockpile_events
        if ev.get("reserve_target")
    ]
    trigger_ratios = [
        float(ev.get("trigger_ratio", 0.0))
        for _, ev in npc_food_stockpile_events
        if ev.get("trigger_ratio") is not None
    ]
    print(f"  npc_food_purchase cooldown skips : {len(npc_food_cooldown_skips)}")
    if base_ratios:
        print(f"  public_works base ratio avg      : {sum(base_ratios) / len(base_ratios):.3f}")
    else:
        print("  public_works base ratio avg      : N/A")
    if reserve_targets:
        print(f"  reserve_target at NPC buys avg   : {sum(reserve_targets) / len(reserve_targets):.1f}")
    else:
        print("  reserve_target at NPC buys avg   : N/A")
    if trigger_ratios:
        print(f"  NPC buy trigger_ratio avg        : {sum(trigger_ratios) / len(trigger_ratios):.3f}")
    else:
        print("  NPC buy trigger_ratio avg        : N/A")

    # Phase 16-E: 후보 확장 + Food Crisis + Farm Expansion
    print("\n=== Phase 16-E observations ===")

    skip_counts = Counter()
    for _, ev in public_works_skip_events:
        skip_counts[ev.get("reason", "unknown")] += 1
    print(f"public_works skip reasons: {dict(sorted(skip_counts.items()))}")

    food_crisis_pw = [
        ev for _, ev in public_works_events
        if ev.get("food_crisis_active")
    ]
    print(f"public_works in food_crisis_active mode: {len(food_crisis_pw)}")

    pool_counts = Counter()
    for _, ev in public_works_events:
        pool_counts[ev.get("from_pool", "unknown")] += 1
    print(f"public_works from_pool: {dict(sorted(pool_counts.items()))}")

    print(f"farm_expansion events: {len(farm_expansion_events)}")
    for _, ev in farm_expansion_events:
        print(
            f"  tick={ev.get('tick', '?')} territory={ev['territory']} "
            f"farms={ev['communal_farms_after']}"
        )
    print(f"farm_expansion_skip events: {len(farm_expansion_skip_events)}")
    if farm_expansion_events:
        print("farm_expansion timeline:")
        for _, ev in farm_expansion_events:
            print(
                f"  | tick {ev.get('tick', '?'):>4} | {ev['territory']:<12s} "
                f"| farms {ev['communal_farms_after']} |"
            )
    else:
        print("farm_expansion timeline: (none)")

    final_farms = {
        tid: getattr(territory, "communal_farms", 1)
        for tid, territory in engine.territories.items()
    }
    print(f"final communal_farms per territory: {final_farms}")

    persona_gold = sum(w.gold for w in engine.wallets.values())
    treasury_total = sum(t.treasury_gold for t in engine.territories.values())
    persona_goods = sum(
        inner.inventory.get(goods, 0) * value
        for inner in engine.inners.values()
        for goods, value in GOODS_VALUE.items()
    )
    territory_goods = sum(
        territory.inventory.get(goods, 0) * value
        for territory in engine.territories.values()
        for goods, value in GOODS_VALUE.items()
    ) + sum(
        getattr(territory, "food_reserve", 0) * GOODS_VALUE["food"]
        for territory in engine.territories.values()
    )
    total_wealth = persona_gold + treasury_total + persona_goods + territory_goods
    initial_wealth = (
        sum(initial_gold.values()) + sum(initial_treasury.values())
        + initial_persona_goods + initial_territory_goods
    )
    wealth_delta_pct = (
        (total_wealth - initial_wealth) / initial_wealth * 100
        if initial_wealth > 0 else 0.0
    )
    print("\n  Total Wealth = gold + treasury + goods value")
    print(f"    initial         : {initial_wealth:.0f}")
    print(f"    persona gold    : {persona_gold:.0f}")
    print(f"    treasury total  : {treasury_total:.0f}")
    print(f"    persona goods   : {persona_goods:.0f}")
    print(f"    territory goods : {territory_goods:.0f}")
    print(f"    TOTAL           : {total_wealth:.0f} ({wealth_delta_pct:+.1f}%)")

    print("\n" + "-" * 70)
    print("  Economy Snapshot")
    print("-" * 70)
    total_final = sum(w.gold for w in engine.wallets.values())
    total_initial = sum(initial_gold.values())
    print(f"  total persona gold: {total_initial:.0f} → {total_final:.0f} (delta={total_final - total_initial:+.0f})")
    for tid, territory in engine.territories.items():
        delta = territory.treasury_gold - initial_treasury[tid]
        print(f"  {tid:15s} treasury: {initial_treasury[tid]:.0f} → {territory.treasury_gold:.0f} (delta={delta:+.0f})")

    # 사망
    dead = [pid for pid in engine.personas if float(engine.inners[pid].vitality) <= 0]
    print(f"\n  deaths: {len(dead)}/{len(engine.personas)}")
    if dead:
        for pid in dead:
            print(f"    {pid}")

    print("\n" + "=" * 70)
    print("  Observation Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
