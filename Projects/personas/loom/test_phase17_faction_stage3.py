"""Phase 17 Stage 3: anti-collapse (B+C) 수학적 backstop + 통합 behavior."""
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from Projects.personas.loom.ontology.layers import (
    DRIFT_MARGIN_MIN,
    FACTION_COMMIT_EVERY,
    FOUNDER_RESPAWN_EVERY,
    FOUNDER_RESPAWN_TARGET_ACTIVE,
    HOMEOSTASIS_DRIFT_MARGIN_SCALE,
    HOMEOSTASIS_LOW_THRESHOLD,
    MINORITY_PERSISTENCE_BOOST,
    MINORITY_PERSISTENCE_MAX_MEMBERS,
)
from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine


def test_stage3_minority_boost_constants_bounded() -> None:
    """MAX_MEMBERS와 HOMEOSTASIS_LOW_THRESHOLD는 정합. BOOST는 DRIFT_MARGIN과 동일 규모."""
    assert MINORITY_PERSISTENCE_MAX_MEMBERS == HOMEOSTASIS_LOW_THRESHOLD, (
        "boost 적용 범위와 homeostasis trigger 범위는 정합해야 한다"
    )
    assert 0 < MINORITY_PERSISTENCE_BOOST < 1.0, "boost는 score 스케일 내"
    # Case-C v2 strengthened the boost above the relaxed drift margin.
    relaxed = DRIFT_MARGIN_MIN * HOMEOSTASIS_DRIFT_MARGIN_SCALE
    assert MINORITY_PERSISTENCE_BOOST >= relaxed, (
        f"boost={MINORITY_PERSISTENCE_BOOST}는 relaxed margin={relaxed} 이상이어야 한다"
    )
    assert abs(MINORITY_PERSISTENCE_BOOST - 0.20) < 1e-9, (
        f"boost={MINORITY_PERSISTENCE_BOOST}는 Case-C v2 계약값 0.20이어야 한다"
    )


def test_stage3_respawn_constants_sane() -> None:
    """respawn은 commit 주기의 정수배, target은 minimum active 수."""
    assert FOUNDER_RESPAWN_EVERY % FACTION_COMMIT_EVERY == 0, (
        f"respawn 주기는 commit 주기의 정수배: every={FOUNDER_RESPAWN_EVERY}, commit={FACTION_COMMIT_EVERY}"
    )
    assert FOUNDER_RESPAWN_EVERY >= FACTION_COMMIT_EVERY * 5, (
        "respawn 주기가 너무 빈번하면 churn 위험"
    )
    assert FOUNDER_RESPAWN_TARGET_ACTIVE >= 2, "목표 active 수는 최소 2 (다수 공존)"


def test_stage3_respawn_rng_determinism() -> None:
    """같은 seed + _derive_rng('faction_respawn', ...) 결과 동일."""
    engine1 = MultiTickEngine(seed=7)
    engine2 = MultiTickEngine(seed=7)
    rng1 = engine1._derive_rng("faction_respawn", "T0", 500)
    rng2 = engine2._derive_rng("faction_respawn", "T0", 500)
    a = rng1.bytes(16)
    b = rng2.bytes(16)
    assert a == b, "격리된 respawn RNG는 동일 seed에서 재현 가능해야 한다"


def test_stage3_respawn_rng_isolation() -> None:
    """다른 tag 는 다른 RNG 스트림(기존 seed 스트림과 격리)."""
    engine = MultiTickEngine(seed=7)
    rng_respawn = engine._derive_rng("faction_respawn", "T0", 500)
    rng_seed = engine._derive_rng("faction_seed", "T0")
    a = rng_respawn.bytes(16)
    b = rng_seed.bytes(16)
    assert a != b, "tag가 다르면 독립 스트림"


def test_stage3_respawn_skips_tick_zero() -> None:
    """tick=0에서는 _init_founder_seeds가 담당, respawn 발동 금지."""
    engine = MultiTickEngine(seed=7)
    # tick=0 상태에서 respawn 메서드 직접 호출 → no-op
    before = len(engine.factions)
    engine._respawn_faction_tick()
    after = len(engine.factions)
    assert before == after, "tick=0에서 respawn은 no-op"


def test_stage3_respawn_skips_when_active_sufficient() -> None:
    """active >= TARGET이면 respawn no-op."""
    engine = MultiTickEngine(seed=7)
    # 초기화 실행 후 faction 생성
    # tick을 FOUNDER_RESPAWN_EVERY로 강제 이동
    # active_count 조작 불가능하면 integration 테스트에서 검증
    # 여기서는 함수가 early-return 분기 있음만 smoke check
    engine.time.tick = FOUNDER_RESPAWN_EVERY
    # 정상 호출로 예외 미발생 확인 (integration은 probe에서)
    engine._respawn_faction_tick()


def test_stage3_respawn_recovers_when_no_free_residents() -> None:
    """collapse 후 faction 없는 주민이 없어도 기존 주민에서 founder를 분리해 active>=2로 회복."""
    engine = MultiTickEngine(seed=7)
    fid = sorted(engine.factions)[0]
    for pid in sorted(engine.personas):
        engine._change_persona_faction(pid, fid, source="drift")
        engine.personas[pid].faction_cooldown = 0  # noqa: PHASE17_FACTION_SSOT_WRITE
    engine._rebuild_faction_members_cache()
    assert sum(1 for members in engine._faction_members_cache.values() if members) == 1
    assert all(persona.faction is not None for persona in engine.personas.values())

    engine.time.tick = FOUNDER_RESPAWN_EVERY
    before = len(engine.factions)
    engine._respawn_faction_tick()

    engine._rebuild_faction_members_cache()
    active = sum(1 for members in engine._faction_members_cache.values() if members)
    birth_events = [
        event for event in engine.event_log
        if event.get("type") == "faction_change"
        and event.get("source") == "birth_founder"
        and event.get("tick") == FOUNDER_RESPAWN_EVERY
    ]
    assert len(engine.factions) == before + 1
    assert active >= FOUNDER_RESPAWN_TARGET_ACTIVE
    assert birth_events
    founder_pid = str(birth_events[-1]["pid"])
    assert engine.personas[founder_pid].faction_cooldown == FOUNDER_RESPAWN_EVERY
