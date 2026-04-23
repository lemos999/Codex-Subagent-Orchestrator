"""Phase 16-B: Productive Public Works verification."""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from core.multi_tick_engine import MultiTickEngine
from ontology.layers import (
    PUBLIC_WORKS_WAGE_PER_TICK,
    PUBLIC_WORKS_DURATION,
    PUBLIC_WORKS_MIN_TREASURY,
    PUBLIC_WORKS_IN_KIND_RATIO,
    STALE_SIGNAL_TICKS,
    JOB_BASE_OUTPUT,
)


def _setup_engine(seed: int = 42) -> MultiTickEngine:
    engine = MultiTickEngine(seed=seed)
    for pid, inner in engine.inners.items():
        inner.is_sleeping = False
        inner.vitality = 1.0
        engine.personas[pid].employment_id = None
    return engine


def _inject_signals(
    engine: MultiTickEngine,
    territory_id: str,
    *,
    tick: int | None = None,
    growth: float = 0.0,
    tension: float = 0.0,
    stability: float = 0.0,
) -> None:
    territory = engine.territories[territory_id]
    territory.last_snn_signals = {
        "growth": growth,
        "tension": tension,
        "stability": stability,
    }
    territory.last_snn_signals_tick = engine.time.tick if tick is None else tick


def _ready_territory(
    engine: MultiTickEngine,
    territory_id: str = "seorim",
    *,
    treasury: float = 3000.0,
    tax_income: float = 500.0,
    growth: float = 0.8,
    tension: float = 0.0,
    stability: float = 0.0,
) -> str:
    territory = engine.territories[territory_id]
    territory.treasury_gold = treasury
    territory.quarter_tax_income = tax_income
    territory.quarter_public_spend = 0.0
    _inject_signals(
        engine,
        territory_id,
        growth=growth,
        tension=tension,
        stability=stability,
    )
    return territory_id


def test_snn_triggers_public_works() -> None:
    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)

    events = engine._process_public_works(tid)

    assert len(events) >= 1, events
    assert events[0]["type"] == "public_works"


def test_base_activation_floor() -> None:
    """Phase 16-E: BASE_ACTIVATION keeps zero-signal public works open."""
    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.0, tension=0.0, stability=0.0)

    events = engine._process_public_works(tid)

    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events, f"BASE_ACTIVATION floor should allow public works: {events}"


def test_treasury_min_guard() -> None:
    engine = _setup_engine()
    tid = _ready_territory(
        engine,
        treasury=PUBLIC_WORKS_MIN_TREASURY - 1,
        growth=0.8,
    )

    events = engine._process_public_works(tid)

    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events == []
    skip_reasons = [ev for ev in events if ev.get("type") == "public_works_skip_reason"]
    assert len(skip_reasons) == 1
    assert skip_reasons[0].get("reason") == "budget_insufficient"
    assert skip_reasons[0].get("detail") == "below_min_treasury"


def test_budget_cap_enforced() -> None:
    """Phase 16-F treasury floor still respects budget_cap < wage."""
    engine = _setup_engine()
    tid = _ready_territory(engine, treasury=550.0, tax_income=50.0, growth=0.8)

    events = engine._process_public_works(tid)

    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events == []
    skip_reasons = [ev for ev in events if ev.get("type") == "public_works_skip_reason"]
    assert any(ev.get("reason") == "budget_insufficient" for ev in skip_reasons), events


def test_unemployed_only_and_lord_excluded() -> None:
    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)
    territory = engine.territories[tid]
    employed_pid = next(
        pid for pid, persona in engine.personas.items()
        if persona.territory == tid and pid != territory.lord_id
    )
    engine.personas[employed_pid].employment_id = "existing_emp"

    events = engine._process_public_works(tid)
    chosen_pids = {ev["persona"] for ev in events}

    assert territory.lord_id not in chosen_pids
    assert employed_pid not in chosen_pids
    assert events, events


def test_wallet_and_treasury_transfer() -> None:
    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)
    territory = engine.territories[tid]
    treasury_before = territory.treasury_gold
    wallets_before = {pid: wallet.gold for pid, wallet in engine.wallets.items()}

    events = engine._process_public_works(tid)

    wage = PUBLIC_WORKS_WAGE_PER_TICK * PUBLIC_WORKS_DURATION
    assert territory.treasury_gold == treasury_before - wage * len(events)
    assert territory.quarter_public_spend == wage * len(events)
    for ev in events:
        pid = ev["persona"]
        assert engine.wallets[pid].gold == wallets_before[pid] + wage


def test_productive_in_kind_credit() -> None:
    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)
    territory = engine.territories[tid]
    food_before = territory.food_reserve
    territory_inventory_before = dict(territory.inventory)
    persona_inventory_before = {
        pid: dict(inner.inventory)
        for pid, inner in engine.inners.items()
    }

    events = engine._process_public_works(tid)

    assert events, events

    territory_expected = {}
    persona_expected = {}
    for ev in events:
        pid = ev["persona"]
        goods_type = ev["produced_type"]
        produced_total = ev["produced_total"]
        in_kind = ev["in_kind_to_territory"]
        to_persona = ev["to_persona"]

        assert goods_type in {"food", "material", "tool", "medicine", "knowledge"}
        assert abs(in_kind - round(produced_total * PUBLIC_WORKS_IN_KIND_RATIO, 2)) < 1e-6
        assert abs(to_persona - round(produced_total * (1.0 - PUBLIC_WORKS_IN_KIND_RATIO), 2)) < 1e-6
        assert abs((in_kind + to_persona) - produced_total) < 1e-6

        territory_expected[goods_type] = territory_expected.get(goods_type, 0.0) + in_kind
        persona_expected[(pid, goods_type)] = persona_expected.get((pid, goods_type), 0.0) + to_persona

    for goods_type, expected in territory_expected.items():
        if goods_type == "food":
            actual = territory.food_reserve - food_before
        else:
            actual = territory.inventory.get(goods_type, 0.0) - territory_inventory_before.get(goods_type, 0.0)
        assert abs(actual - expected) < 1e-6

    for (pid, goods_type), expected in persona_expected.items():
        actual = engine.inners[pid].inventory.get(goods_type, 0.0) - persona_inventory_before[pid].get(goods_type, 0.0)
        assert abs(actual - expected) < 1e-6


def test_stale_signal_suppressed() -> None:
    from ontology.layers import PUBLIC_WORKS_STALE_MAX_AGE

    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)
    engine.time.tick = PUBLIC_WORKS_STALE_MAX_AGE + 100
    _inject_signals(
        engine,
        tid,
        tick=engine.time.tick - PUBLIC_WORKS_STALE_MAX_AGE - 1,
        growth=0.8,
    )

    events = engine._process_public_works(tid)

    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events == []
    skip_reasons = [ev for ev in events if ev.get("type") == "public_works_skip_reason"]
    assert any(
        ev.get("reason") == "signal_stale"
        and "max_exceeded" in str(ev.get("detail", ""))
        for ev in skip_reasons
    ), events


def test_signal_decay_inactive_when_fresh() -> None:
    """Phase 16-H: sig_age <= STALE_SIGNAL_TICKS means no decay."""
    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)

    events = engine._process_public_works(tid)
    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events, events
    for ev in work_events:
        assert abs(ev["signal_decay"] - 1.0) < 1e-6, ev


def test_signal_decay_active_when_stale() -> None:
    """Phase 16-H: STALE_SIGNAL_TICKS < sig_age < MAX_AGE uses linear decay."""
    from ontology.layers import (
        PUBLIC_WORKS_STALE_DECAY_WINDOW,
        PUBLIC_WORKS_STALE_DECAY_FLOOR,
    )

    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)
    target_sig_age = 120
    engine.time.tick = 500
    engine.territories[tid].last_snn_signals_tick = (
        engine.time.tick - target_sig_age
    )

    events = engine._process_public_works(tid)
    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events, f"decay fallback should proceed: {events}"

    expected_decay = max(
        PUBLIC_WORKS_STALE_DECAY_FLOOR,
        1.0 - (target_sig_age - STALE_SIGNAL_TICKS) / PUBLIC_WORKS_STALE_DECAY_WINDOW,
    )
    expected_decay = round(expected_decay, 3)
    for ev in work_events:
        assert abs(ev["signal_decay"] - expected_decay) < 1e-6, ev


def test_signal_decay_floor_applied() -> None:
    """Phase 16-H: sig_age beyond the window is clamped to DECAY_FLOOR."""
    from ontology.layers import PUBLIC_WORKS_STALE_DECAY_FLOOR

    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)
    engine.time.tick = 500
    engine.territories[tid].last_snn_signals_tick = engine.time.tick - 400

    events = engine._process_public_works(tid)
    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events, f"floor-range decay should proceed: {events}"
    for ev in work_events:
        assert abs(ev["signal_decay"] - PUBLIC_WORKS_STALE_DECAY_FLOOR) < 1e-6, ev


def test_signal_decay_max_age_skip() -> None:
    """Phase 16-H: sig_age > MAX_AGE still skips completely."""
    from ontology.layers import PUBLIC_WORKS_STALE_MAX_AGE

    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)
    engine.time.tick = PUBLIC_WORKS_STALE_MAX_AGE + 100
    engine.territories[tid].last_snn_signals_tick = (
        engine.time.tick - (PUBLIC_WORKS_STALE_MAX_AGE + 10)
    )

    events = engine._process_public_works(tid)
    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events == []
    skip_reasons = [ev for ev in events if ev.get("type") == "public_works_skip_reason"]
    assert any(
        ev.get("reason") == "signal_stale"
        and "max_exceeded" in str(ev.get("detail", ""))
        for ev in skip_reasons
    ), events


def test_stable_random_selection() -> None:
    def run() -> list[str]:
        engine = _setup_engine(seed=42)
        tid = _ready_territory(engine, growth=1.0, tension=1.0)
        return [ev["persona"] for ev in engine._process_public_works(tid)]

    assert run() == run()


def test_parttime_enabled_by_high_tension() -> None:
    """Phase 16-G: tension >= THRESHOLD ??employed persona ??part-time ?꾨낫濡??ы븿."""
    from ontology.layers import PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD

    engine = _setup_engine()
    tid = _ready_territory(engine, treasury=3000.0, tax_income=500.0)
    territory = engine.territories[tid]

    # 紐⑤뱺 non-lord persona ??employment 遺?????먮옒?濡쒕㈃ ?꾨낫 = 怨듭쭛??    for pid, persona in engine.personas.items():
    for pid, persona in engine.personas.items():
        if persona.territory == tid and pid != territory.lord_id:
            persona.employment_id = "fake_emp"
            engine.wallets[pid].gold = 1000.0  # low_gold_hungry 寃쎈줈 李⑤떒
            engine.inners[pid].consecutive_hunger_ticks = 0

    # high tension 二쇱엯 ??part-time 寃쎈줈 ?쒖꽦??    _inject_signals(
    _inject_signals(
        engine, tid,
        growth=0.0, tension=PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD + 0.1,
        stability=0.0,
    )
    events = engine._process_public_works(tid)

    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events, f"part-time ?꾨낫媛 ?쒖꽦?붾릺???ㅼ젣 吏묓뻾?섏뼱???? {events}"
    # ?ㅼ젣 吏묓뻾???대깽?멸? ?꾨? part-time ?몄? 寃利?    assert all(ev.get("parttime") is True for ev in work_events), work_events
    assert all(ev.get("parttime") is True for ev in work_events), work_events


def test_parttime_wage_and_output_ratio() -> None:
    """Phase 16-G: part-time 吏묓뻾 ???꾧툑/?앹궛??full-time ?鍮??뺥빐吏?鍮꾩쑉."""
    from ontology.layers import (
        PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD,
        PUBLIC_WORKS_PARTTIME_WAGE_RATIO,
        PUBLIC_WORKS_PARTTIME_OUTPUT_RATIO,
    )

    engine = _setup_engine()
    tid = _ready_territory(engine, treasury=5000.0, tax_income=500.0)
    territory = engine.territories[tid]
    full_wage = PUBLIC_WORKS_WAGE_PER_TICK * PUBLIC_WORKS_DURATION

    # 紐⑤뱺 non-lord persona employed, high tension ???꾩썝 part-time
    for pid, persona in engine.personas.items():
        if persona.territory == tid and pid != territory.lord_id:
            persona.employment_id = "fake_emp"
            engine.wallets[pid].gold = 1000.0
            engine.inners[pid].consecutive_hunger_ticks = 0

    _inject_signals(
        engine, tid,
        growth=0.0, tension=PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD + 0.1,
        stability=0.0,
    )
    events = engine._process_public_works(tid)
    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events, events

    expected_wage = full_wage * PUBLIC_WORKS_PARTTIME_WAGE_RATIO
    for ev in work_events:
        assert ev.get("parttime") is True
        assert abs(ev["wage"] - expected_wage) < 1e-6, ev
        # produced_total ? full-time ?鍮?OUTPUT_RATIO 諛?(짹 farm_multiplier ??蹂?숈? ?놁쓬)
        # ?뺥솗 寃利앹? base_output * DURATION * OUTPUT_RATIO
        # base_output ? job蹂꾨줈 ?ㅻⅤ誘濡?媛꾩젒 寃利? produced_total > 0 and in_kind + to_persona == produced_total
        assert ev["produced_total"] > 0.0
        assert abs(ev["in_kind_to_territory"] + ev["to_persona"] - ev["produced_total"]) < 1e-6


def test_signal_bootstrap_within_stale_window() -> None:
    """Phase 16-G: tick < STALE_SIGNAL_TICKS ??SNN ?좏샇 ?놁쑝硫?bootstrap ?쇰줈 吏꾪뻾."""
    from ontology.layers import (
        PUBLIC_WORKS_BOOTSTRAP_GROWTH,
        PUBLIC_WORKS_BOOTSTRAP_TENSION,
    )

    engine = _setup_engine()
    tid = "seorim"
    territory = engine.territories[tid]
    territory.treasury_gold = 3000.0
    territory.quarter_tax_income = 500.0
    territory.quarter_public_spend = 0.0
    # SNN ?좏샇 ?놁쓬 ?곹깭 紐낆떆
    territory.last_snn_signals = None
    territory.last_snn_signals_tick = -1
    engine.time.tick = 10  # < STALE_SIGNAL_TICKS(72)

    events = engine._process_public_works(tid)

    # bootstrap ?뺣텇??skip ?섏? ?딄퀬 吏꾪뻾 ??skip_reason never_computed 媛 ?놁뼱????    never_computed = [
    never_computed = [
        ev for ev in events
        if ev.get("type") == "public_works_skip_reason"
        and ev.get("detail") == "never_computed"
    ]
    assert never_computed == [], events


def test_signal_bootstrap_expires_after_stale_window() -> None:
    """Phase 16-G: tick >= STALE_SIGNAL_TICKS ?댄썑?먮뒗 ?ъ쟾??signal_stale skip."""
    engine = _setup_engine()
    tid = "seorim"
    territory = engine.territories[tid]
    territory.treasury_gold = 3000.0
    territory.quarter_tax_income = 500.0
    territory.last_snn_signals = None
    territory.last_snn_signals_tick = -1
    engine.time.tick = STALE_SIGNAL_TICKS + 1

    events = engine._process_public_works(tid)

    skip_reasons = [ev for ev in events if ev.get("type") == "public_works_skip_reason"]
    assert any(
        ev.get("reason") == "signal_stale" and ev.get("detail") == "never_computed"
        for ev in skip_reasons
    ), events


def test_fulltime_wage_unchanged_for_unemployed() -> None:
    """Phase 16-G: unemployed ?꾨낫??湲곗〈泥섎읆 full-time ?쇰줈 吏묓뻾 (parttime=False)."""
    engine = _setup_engine()
    tid = _ready_territory(engine, growth=0.8)

    events = engine._process_public_works(tid)
    work_events = [ev for ev in events if ev.get("type") == "public_works"]
    assert work_events, events

    # 湲곕낯 ?쒕굹由ъ삤: 紐⑤몢 unemployed ??parttime=False, full wage
    full_wage = PUBLIC_WORKS_WAGE_PER_TICK * PUBLIC_WORKS_DURATION
    for ev in work_events:
        assert ev.get("parttime") is False, ev
        assert abs(ev["wage"] - full_wage) < 1e-6, ev


def run_all() -> None:
    tests = [
        test_snn_triggers_public_works,
        test_base_activation_floor,
        test_treasury_min_guard,
        test_budget_cap_enforced,
        test_unemployed_only_and_lord_excluded,
        test_wallet_and_treasury_transfer,
        test_productive_in_kind_credit,
        test_stale_signal_suppressed,
        test_signal_decay_inactive_when_fresh,
        test_signal_decay_active_when_stale,
        test_signal_decay_floor_applied,
        test_signal_decay_max_age_skip,
        test_stable_random_selection,
        test_parttime_enabled_by_high_tension,
        test_parttime_wage_and_output_ratio,
        test_signal_bootstrap_within_stale_window,
        test_signal_bootstrap_expires_after_stale_window,
        test_fulltime_wage_unchanged_for_unemployed,
    ]
    passed = 0
    for test in tests:
        test()
        print(f"  PASS  {test.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} passed")


if __name__ == "__main__":
    run_all()
