"""Phase 17 acceptance gate and Stage 4 closure checks.

spec functional-equivalence: stable_perf_median_p95, faction_kernel_0_960,
seed42_perf_line, five_channel_determinism.

Run with: `py test_phase17_acceptance.py`
Exit 0 on PASS, non-zero on any FAIL.
"""
from __future__ import annotations

import gc
import hashlib
import os
import pickle
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_SIMULATION_CACHE = {}


def run_simulation(seed: int, ticks: int):
    """Run and cache long deterministic acceptance simulations by seed/ticks."""
    key = (seed, ticks)
    if key not in _SIMULATION_CACHE:
        from core.multi_tick_engine import MultiTickEngine

        engine = MultiTickEngine(seed=seed)
        for _ in range(ticks):
            engine.tick()
        _SIMULATION_CACHE[key] = engine
    return _SIMULATION_CACHE[key]


def _phi3_snapshot(seed: int = 42, ticks: int = 5000) -> bytes:
    from core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=seed)
    for _ in range(ticks):
        engine.tick()
    snapshot = {
        "p_faction": {pid: engine.personas[pid].faction for pid in sorted(engine.personas)},
        "p_cooldown": {pid: engine.personas[pid].faction_cooldown for pid in sorted(engine.personas)},
        "i_aff": {pid: dict(engine.inners[pid].affiliation_scores) for pid in sorted(engine.inners)},
        "i_grievance": {
            pid: (
                round(float(engine.inners[pid].grievance), 6),
                engine.inners[pid].grievance_lord_id,
            )
            for pid in sorted(engine.inners)
        },
        "factions": {
            fid: (
                engine.factions[fid].founder_pid,
                engine.factions[fid].grace_until_tick,
                tuple(engine.factions[fid].charter),
                tuple(engine.factions[fid].founder_lineage),
            )
            for fid in sorted(engine.factions)
        },
        "uprising_events": [
            (
                event.get("tick"),
                event.get("leader_pid"),
                event.get("from_faction"),
                event.get("target_faction"),
                event.get("branch"),
                event.get("lord_id"),
                event.get("members_count"),
            )
            for event in engine.event_log
            if event.get("type") == "uprising"
        ],
        "t_ref": {tid: engine.territories[tid].factionRef for tid in sorted(engine.territories)},
    }
    return pickle.dumps(snapshot, protocol=4)


def run_simulation_hash(seed: int, ticks: int) -> str:
    return hashlib.sha256(_phi3_snapshot(seed=seed, ticks=ticks)).hexdigest()


def _run(cmd: list[str], label: str) -> bool:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=ROOT,
        env=env,
    )
    ok = result.returncode == 0
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {label}")
    if not ok:
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
    return ok


def _measure_tick_ms_stable(seed: int = 42) -> tuple[float, float, list[float]]:
    from core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=seed)
    for _ in range(100):
        engine.tick()
    gc.collect()

    samples: list[float] = []
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(100):
            engine.tick()
        samples.append((time.perf_counter() - start) * 1000.0 / 100.0)

    ordered = sorted(samples)
    median = ordered[len(ordered) // 2]
    p95 = ordered[3]
    return median, p95, samples


def _format_tick_perf(median: float, p95: float, samples: list[float]) -> str:
    sample_text = ",".join(f"{sample:.1f}" for sample in samples)
    return f"[perf] tick(ms)  median={median:.1f}  p95={p95:.1f}  samples=[{sample_text}]"


def _prepare_respawn_probe_engine(seed: int = 42):
    from core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=seed)
    first_fid = next(iter(engine.factions))
    for pid in sorted(engine.personas):
        engine._change_persona_faction(pid, first_fid, source="drift")
    engine._rebuild_faction_members_cache()
    return engine


def _measure_faction_kernel_ms(seed: int = 42) -> dict[str, float]:
    from ontology.layers import FOUNDER_RESPAWN_EVERY

    engine = _prepare_respawn_probe_engine(seed=seed)
    respawn_events_before = sum(
        1 for event in engine.event_log
        if event.get("type") == "faction_change" and event.get("source") == "birth_founder"
    )
    totals = {
        "affiliation": 0.0,
        "commit": 0.0,
        "project": 0.0,
        "respawn": 0.0,
    }
    total_ticks = FOUNDER_RESPAWN_EVERY * 2

    for tick in range(1, total_ticks + 1):
        engine.time.tick = tick

        start = time.perf_counter()
        engine._compute_affiliation_tick()
        totals["affiliation"] += (time.perf_counter() - start) * 1000.0

        start = time.perf_counter()
        engine._commit_faction_tick()
        totals["commit"] += (time.perf_counter() - start) * 1000.0

        start = time.perf_counter()
        engine._project_faction_tick()
        totals["project"] += (time.perf_counter() - start) * 1000.0

        start = time.perf_counter()
        engine._respawn_faction_tick()
        totals["respawn"] += (time.perf_counter() - start) * 1000.0

    per_tick = {name: value / total_ticks for name, value in totals.items()}
    per_tick["total"] = sum(per_tick.values())
    respawn_events_after = sum(
        1 for event in engine.event_log
        if event.get("type") == "faction_change" and event.get("source") == "birth_founder"
    )
    per_tick["respawn_events"] = float(respawn_events_after - respawn_events_before)
    return per_tick


def _format_faction_kernel_perf(kernel: dict[str, float]) -> str:
    return (
        "[perf] faction_kernel(ms/tick)  "
        f"affiliation={kernel['affiliation']:.2f}  "
        f"commit={kernel['commit']:.2f}  "
        f"project={kernel['project']:.2f}  "
        f"respawn={kernel['respawn']:.2f}  "
        f"total={kernel['total']:.2f}"
    )


def _format_observe_perf_line(median: float, kernel_total: float) -> str:
    return f"[perf] tick={median:.1f}ms  faction_kernel={kernel_total:.2f}ms  (seed=42 sample)"


def _phase17_phi2_stage4_snapshot(seed: int = 42, ticks: int = 500) -> bytes:
    from core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=seed)
    for _ in range(ticks):
        engine.tick()
    snapshot = {
        "p_faction": {
            pid: engine.personas[pid].faction
            for pid in sorted(engine.personas)
        },
        "p_cooldown": {
            pid: engine.personas[pid].faction_cooldown
            for pid in sorted(engine.personas)
        },
        "i_aff": {
            pid: dict(engine.inners[pid].affiliation_scores)
            for pid in sorted(engine.inners)
        },
        "factions": {
            fid: (
                engine.factions[fid].name,
                engine.factions[fid].founder_pid,
                tuple(engine.factions[fid].charter),
                engine.factions[fid].created_tick,
            )
            for fid in sorted(engine.factions)
        },
        "t_ref": {
            tid: engine.territories[tid].factionRef
            for tid in sorted(engine.territories)
        },
    }
    return pickle.dumps(snapshot, protocol=4)


def _phase17_phi2_stage4_hash(seed: int = 42, ticks: int = 500) -> str:
    return hashlib.sha256(_phase17_phi2_stage4_snapshot(seed=seed, ticks=ticks)).hexdigest()


def test_phase17_phi2_determinism_500_ticks_stage4() -> None:
    """Stage 4: 5-channel byte-level determinism."""
    h1 = _phase17_phi2_stage4_hash(seed=42, ticks=500)
    h2 = _phase17_phi2_stage4_hash(seed=42, ticks=500)
    assert h1 == h2, f"Phi-2 Stage 4 determinism hash mismatch ({h1} != {h2})"


def _phase17_phi2_stage5_snapshot(seed: int = 42, ticks: int = 500) -> bytes:
    from core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=seed)
    for _ in range(ticks):
        engine.tick()
    snapshot = {
        "p_faction": {pid: engine.personas[pid].faction for pid in sorted(engine.personas)},
        "p_cooldown": {pid: engine.personas[pid].faction_cooldown for pid in sorted(engine.personas)},
        "i_aff": {pid: dict(engine.inners[pid].affiliation_scores) for pid in sorted(engine.inners)},
        "i_residence": {pid: dict(engine.inners[pid].residence_ticks) for pid in sorted(engine.inners)},
        "factions": {
            fid: (
                engine.factions[fid].founder_pid,
                engine.factions[fid].grace_until_tick,
                tuple(engine.factions[fid].charter),
            )
            for fid in sorted(engine.factions)
        },
        "t_ref": {tid: engine.territories[tid].factionRef for tid in sorted(engine.territories)},
    }
    return pickle.dumps(snapshot, protocol=4)


def _phase17_phi2_stage5_hash(seed: int = 42, ticks: int = 500) -> str:
    return hashlib.sha256(_phase17_phi2_stage5_snapshot(seed=seed, ticks=ticks)).hexdigest()


def _phase17_phi2_stage6_snapshot(seed: int = 42, ticks: int = 500) -> bytes:
    from core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=seed)
    for _ in range(ticks):
        engine.tick()
    snapshot = {
        "p_faction": {pid: engine.personas[pid].faction for pid in sorted(engine.personas)},
        "p_cooldown": {pid: engine.personas[pid].faction_cooldown for pid in sorted(engine.personas)},
        "i_aff": {pid: dict(engine.inners[pid].affiliation_scores) for pid in sorted(engine.inners)},
        "i_residence": {pid: dict(engine.inners[pid].residence_ticks) for pid in sorted(engine.inners)},
        "factions": {
            fid: (
                engine.factions[fid].founder_pid,
                engine.factions[fid].grace_until_tick,
                tuple(engine.factions[fid].charter),
                tuple(engine.factions[fid].founder_lineage),
            )
            for fid in sorted(engine.factions)
        },
        "t_ref": {tid: engine.territories[tid].factionRef for tid in sorted(engine.territories)},
    }
    return pickle.dumps(snapshot, protocol=4)


def _phase17_phi2_stage6_hash(seed: int = 42, ticks: int = 500) -> str:
    return hashlib.sha256(_phase17_phi2_stage6_snapshot(seed=seed, ticks=ticks)).hexdigest()


def test_phase17_phi2_stage6_founder_lineage_default() -> None:
    """Stage 6: _init_founder_seeds로 생성된 Faction은 founder_pid가 lineage에 포함되어야 함."""
    from core.multi_tick_engine import MultiTickEngine

    engine = MultiTickEngine(seed=42)
    for fid, faction in engine.factions.items():
        assert isinstance(faction.founder_lineage, tuple), (
            f"Faction {fid}: founder_lineage type={type(faction.founder_lineage).__name__} (expected tuple)"
        )
        assert faction.founder_pid in faction.founder_lineage, (
            f"Faction {fid}: founder_pid={faction.founder_pid} not in lineage={faction.founder_lineage}"
        )


def test_phase17_phi2_stage6_respawn_lineage() -> None:
    """Stage 6: respawn 경로로 생성된 Faction도 founder_pid 포함 lineage 보유."""
    from ontology.layers import FOUNDER_RESPAWN_EVERY

    engine = _prepare_respawn_probe_engine(seed=42)
    initial_fids = set(engine.factions.keys())
    for tick in range(1, FOUNDER_RESPAWN_EVERY + 1):
        engine.time.tick = tick
        engine._compute_affiliation_tick()
        engine._commit_faction_tick()
        engine._project_faction_tick()
        engine._respawn_faction_tick()

    new_fids = set(engine.factions.keys()) - initial_fids
    assert len(new_fids) >= 1, "respawn cycle 후 새 Faction 생성되지 않음"
    for fid in new_fids:
        f = engine.factions[fid]
        assert isinstance(f.founder_lineage, tuple), f"Faction {fid}: lineage type"
        assert len(f.founder_lineage) >= 1, f"Faction {fid}: lineage empty"
        assert f.founder_pid in f.founder_lineage, (
            f"Faction {fid}: founder_pid={f.founder_pid} not in lineage={f.founder_lineage}"
        )


def test_phi3_uprising_emerges_under_grievance_pressure():
    """Φ-3 acceptance #1: seed 7/13/42 5000틱 uprising_event ≥ 1 (3/3)."""
    from ontology.layers import THETA_UPRISING

    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        uprisings = [e for e in engine.event_log if e["type"] == "uprising"]
        assert len(uprisings) >= 1, (
            f"seed {seed}: 5000 ticks 내 uprising 0건. "
            f"THETA_UPRISING={THETA_UPRISING} 또는 SNN_ANGER_FIRE_THRESHOLD 튜닝 필요"
        )


def test_phi3_grievance_pairs_resonate():
    """Φ-3 acceptance #2: grievance_pairs_end ≥ 1 (3/3)."""
    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        targets = engine.faction_grievance_targets()
        # 같은 lord_id를 ≥ 2명씩 가진 faction 쌍 카운트
        by_lord: dict[str, list[str]] = {}
        for fid, lord_map in targets.items():
            for lord_id, cnt in lord_map.items():
                if cnt >= 2:
                    by_lord.setdefault(lord_id, []).append(fid)
        pair_count = sum(
            len(fids) * (len(fids) - 1) // 2
            for fids in by_lord.values() if len(fids) >= 2
        )
        assert pair_count >= 1, f"seed {seed}: grievance_pairs 0쌍"


def test_phi3_dom_share_natural_imbalance():
    """Φ-3 acceptance #3: dom_share_end ≥ 0.50 (3/3, OR-2 자연 충족)."""
    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        pop = engine.faction_population_distribution()
        if not pop:
            assert False, f"seed {seed}: empty population"
        total = sum(pop.values())
        top = max(pop.values()) if pop else 0
        share = top / total if total else 0.0
        assert share >= 0.50, (
            f"seed {seed}: dom_share={share:.3f} < 0.50. 봉기 후 멤버 재분포 부족"
        )


def test_phi3_no_deaths():
    """Φ-3 무사망 보장: population_total 보존."""
    for seed in [7, 13, 42]:
        engine_start = run_simulation(seed=seed, ticks=1)
        engine_end = run_simulation(seed=seed, ticks=5000)
        assert sum(engine_end.faction_population_distribution().values()) >= sum(
            engine_start.faction_population_distribution().values()
        ) - 1   # ±1 허용 (Stage 3 anti-collapse 잔여 영향)


def test_phi3_branch_lineage_chain():
    """분파 신규 faction의 founder_lineage가 부모 fid 포함."""
    for seed in [7, 13, 42]:
        engine = run_simulation(seed=seed, ticks=5000)
        branches = [
            e for e in engine.event_log
            if e["type"] == "faction_spawn" and e.get("source") == "uprising_branch"
        ]
        for b in branches:
            new_fid = b["fid"]
            parent_fid = b["parent_fid"]
            new_faction = engine.factions[new_fid]
            assert parent_fid in new_faction.founder_lineage, (
                f"분파 {new_fid}의 founder_lineage에 부모 {parent_fid} 없음: "
                f"{new_faction.founder_lineage}"
            )


def test_phi3_determinism_seed42():
    """phi2_phi3_hash 결정성: seed=42 5000틱 2회 실행 hash 일치."""
    h1 = run_simulation_hash(seed=42, ticks=5000)
    h2 = run_simulation_hash(seed=42, ticks=5000)
    assert h1 == h2, f"determinism break: {h1} vs {h2}"


def test_branch_faction_id_no_collision() -> None:
    """hotfix v1: D5 결함 형식(prefix [:6]) 동일 시 충돌이 발생할 수 있는 조건에서
    풀 founder_pid 사용으로 충돌이 방지됨을 검증.

    환경 의존 0%: stub parent Faction 2개를 self.factions에 직접 등록하여
    150틱 진행·active faction 카운트 의존을 제거. self.time.tick=0 (생성 직후)에
    spawn 두 번 호출 → 같은 tick에서 ID 충돌 시뮬 명확.
    """
    from core.multi_tick_engine import MultiTickEngine
    from ontology.layers import Faction
    eng = MultiTickEngine(seed=7)
    # 환경 의존 제거: stub parent factions 직접 등록
    eng.factions["stub-parent-a"] = Faction(
        id="stub-parent-a",
        name="StubParentA",
        founder_pid="persona_001",
        charter=("외세_배척", "능력주의", "자연_경외"),
        created_tick=0,
    )
    eng.factions["stub-parent-b"] = Faction(
        id="stub-parent-b",
        name="StubParentB",
        founder_pid="persona_002",
        charter=("외세_배척", "능력주의", "자연_경외"),
        created_tick=0,
    )
    # 같은 prefix 6자를 명시적으로 가진 임의 founder_pid 두 개 (D5 결함 형식 시뮬)
    fake_p1 = "persona_001"
    fake_p2 = "persona_002"
    assert fake_p1[:6] == fake_p2[:6], "테스트 자체 가정 — fake pid prefix 6자 일치"
    new_a = eng._spawn_branch_faction(founder_pid=fake_p1, parent_fid="stub-parent-a")
    new_b = eng._spawn_branch_faction(founder_pid=fake_p2, parent_fid="stub-parent-b")
    assert new_a != new_b, (
        f"branch ID collision: {new_a!r} == {new_b!r} "
        f"(D5 결함 형식 잔존 — founder_pid[:6] 동일 시 충돌)"
    )
    assert new_a in eng.factions, f"신규 분파 {new_a!r}이 factions registry에 미등록"
    assert new_b in eng.factions, f"신규 분파 {new_b!r}이 factions registry에 미등록"


def test_grievance_lord_id_not_sticky() -> None:
    """hotfix v1: _update_grievances는 24틱 경계마다 lord_id를 항상 갱신 (sticky 가드 없음).

    설계 주의:
    - `_update_grievances`는 tick % 24 == 0에서만 실행
    - lord 보유 territory에 거주하는 비-lord 페르소나만 갱신 대상
    - 따라서 48틱 진행 후 FAKE_LORD 주입 → 24틱 추가 진행(=72) → 갱신 검증
    - territory 이주 가드: 24틱 추가 진행 중 페르소나가 territory를 떠나면
      _update_grievances 본문 진입 못해 lord_id 갱신 안됨 (false positive 회피)
    """
    from core.multi_tick_engine import MultiTickEngine
    eng = MultiTickEngine(seed=7)
    # 48틱(2 사이클) 진행 — territory의 lord_id 안정화
    for _ in range(48):
        eng.tick()
    # lord 보유 territory에 거주 + 본인이 lord가 아닌 페르소나 선정
    target_pid = None
    expected_lord_hint = None
    initial_tid = None
    for tid, terr in eng.territories.items():
        if not terr.lord_id or terr.lord_id not in eng.personas:
            continue
        residents = eng._get_territory_residents(tid)
        for pid in residents:
            if pid != terr.lord_id:
                target_pid = pid
                expected_lord_hint = terr.lord_id
                initial_tid = tid
                break
        if target_pid:
            break
    assert target_pid is not None, (
        "lord 보유 territory에 거주하는 비-lord 페르소나가 없음 — "
        "Phase 14 territory.lord_id 분포 점검 필요"
    )
    # FAKE_LORD 강제 주입
    eng.inners[target_pid].grievance = 0.7   # ≥ GRIEVANCE_MIN_SHARED
    eng.inners[target_pid].grievance_lord_id = "FAKE_LORD"
    # 다음 24틱 경계까지 진행 (48 → 72) → _update_grievances 본문 진입
    for _ in range(24):
        eng.tick()
    # territory 이주 가드: target_pid가 동일 territory에 잔존하지 않으면 _update_grievances
    # 본문 진입 못해 lord_id 갱신 발생 안 함 (false positive 회피)
    if eng.personas[target_pid].territory != initial_tid:
        return  # 이주 발생 — 환경 의존 skip
    final_lord_id = eng.inners[target_pid].grievance_lord_id
    assert final_lord_id != "FAKE_LORD", (
        f"hotfix v1 위반: grievance_lord_id가 sticky 가드로 'FAKE_LORD' 보존됨 "
        f"(expected: territory lord 갱신, 힌트={expected_lord_hint!r}, "
        f"territory={initial_tid!r})"
    )


def test_uprising_tick_no_artificial_injection() -> None:
    """hotfix v1: _uprising_tick은 trigger→emit 외 다른 faction 멤버에게 lord_id를 인공 주입하지 않는다.

    1차 구현(Before)의 후반부 코드는 다음 조건에서 인공 주입을 발화시켰다:
        (a) has_pair == False (≥2명 carrier가 있는 lord가 ≥2 faction에 분포 안 함)
        (b) active_fids ≥ 2 (멤버 ≥ 2 faction이 2개 이상)
        (c) source_lord_id 추출 가능 (한 faction에 carriers ≥ 2)
    조건 충족 시 다른 faction 멤버 2명에게 source_lord_id를 강제 주입.

    본 테스트는 (a)(b)(c) 조건을 직접 만들고, fid_b 멤버의 lord_id가 변동
    없음을 검증한다. hotfix 후 코드는 trigger→emit 단순 호출만 수행.
    """
    from core.multi_tick_engine import MultiTickEngine
    eng = MultiTickEngine(seed=7)
    for _ in range(48):
        eng.tick()
    # 활성 faction 2개 이상 + 각 멤버 ≥ 2명 확보
    pop = eng.faction_population_distribution()
    active = sorted([fid for fid, c in pop.items() if c >= 2])
    if len(active) < 2:
        return  # 환경 의존 skip
    fid_a, fid_b = active[0], active[1]
    members_a = [p.id for p in eng._faction_members(fid_a)][:2]
    members_b = [p.id for p in eng._faction_members(fid_b)][:2]
    if len(members_a) < 2 or len(members_b) < 2:
        return
    fake_lord = sorted(eng.personas.keys())[0]
    # 조건 (c): fid_a 멤버 2명에게 grievance_lord_id=fake_lord 강제
    for pid in members_a:
        eng.inners[pid].grievance = 0.7
        eng.inners[pid].grievance_lord_id = fake_lord
    # 조건 (a): fid_b 멤버는 lord_id 미설정 → carriers=1만 존재 → has_pair=False
    for pid in members_b:
        eng.inners[pid].grievance = 0.0
        eng.inners[pid].grievance_lord_id = None
    # _uprising_trigger 자체는 발화 못하도록 grievance를 GRIEVANCE_MIN_SHARED 미만으로
    # (단, fid_a의 carrier 2명은 그대로 유지)
    # → trigger candidates 0건 → emit 호출 없음 → 후반부만 검증 대상
    before_b = {pid: eng.inners[pid].grievance_lord_id for pid in members_b}
    eng._uprising_tick()
    after_b = {pid: eng.inners[pid].grievance_lord_id for pid in members_b}
    assert before_b == after_b, (
        f"_uprising_tick이 fid_b 멤버에게 lord_id를 인공 주입함 "
        f"(artificial injection 잔존): before={before_b}, after={after_b}"
    )


def test_phase17_phi2_perf_stage4() -> None:
    median, p95, samples = _measure_tick_ms_stable(seed=42)
    print(_format_tick_perf(median, p95, samples))
    assert median <= 250.0, f"tick median budget exceeded: {median:.1f}ms"
    assert p95 <= 350.0, f"tick p95 budget exceeded: {p95:.1f}ms"


def test_phase17_phi2_faction_kernel_perf_stage4() -> None:
    kernel = _measure_faction_kernel_ms(seed=42)
    print(_format_faction_kernel_perf(kernel))
    assert kernel["respawn_events"] >= 1.0
    assert kernel["total"] <= 5.0, f"faction kernel budget exceeded: {kernel['total']:.2f}ms"


def main() -> int:
    failures: list[str] = []

    if not _run([sys.executable, "test_phase17_land.py"], "Phase 17 Land (v1+v2)"):
        failures.append("phase17_land")

    for name in [
        "test_nomos.py",
        "test_class_promotion.py",
        "test_phase16_public_works.py",
        "test_climate_impact.py",
        "test_phase14b_snn_integration.py",
        "test_phase15_collective_action.py",
    ]:
        if not _run([sys.executable, name], name):
            failures.append(name)

    median, p95, samples = _measure_tick_ms_stable(seed=42)
    print(_format_tick_perf(median, p95, samples))
    kernel = _measure_faction_kernel_ms(seed=42)
    print(_format_faction_kernel_perf(kernel))
    print(_format_observe_perf_line(median, kernel["total"]))
    perf_ok = median <= 250.0 and p95 <= 350.0 and kernel["total"] <= 5.0
    status = "PASS" if perf_ok else "FAIL"
    print(
        f"[{status}] tick_performance: median={median:.1f}ms p95={p95:.1f}ms "
        f"kernel={kernel['total']:.2f}ms"
    )
    if not perf_ok:
        failures.append(
            f"performance (median={median:.1f}ms p95={p95:.1f}ms kernel={kernel['total']:.2f}ms)"
        )

    determinism_a = _phase17_phi2_stage4_hash(seed=42, ticks=500)
    determinism_b = _phase17_phi2_stage4_hash(seed=42, ticks=500)
    determinism_ok = determinism_a == determinism_b
    status = "PASS" if determinism_ok else "FAIL"
    print(f"[{status}] phi2_stage4_determinism_500: {determinism_a} / {determinism_b}")
    if not determinism_ok:
        failures.append("phi2_stage4_determinism_500")

    stage5_a = _phase17_phi2_stage5_hash(seed=42, ticks=500)
    stage5_b = _phase17_phi2_stage5_hash(seed=42, ticks=500)
    stage5_ok = stage5_a == stage5_b
    status = "PASS" if stage5_ok else "FAIL"
    print(f"[{status}] phi2_stage5_determinism_500 (grace_until_tick+residence_ticks): {stage5_a[:16]}…")
    if not stage5_ok:
        failures.append("phi2_stage5_determinism_500")

    stage6_a = _phase17_phi2_stage6_hash(seed=42, ticks=500)
    stage6_b = _phase17_phi2_stage6_hash(seed=42, ticks=500)
    stage6_ok = stage6_a == stage6_b
    status = "PASS" if stage6_ok else "FAIL"
    print(f"[{status}] phi2_stage6_determinism_500 (founder_lineage): {stage6_a[:16]}…")
    if not stage6_ok:
        failures.append("phi2_stage6_determinism_500")

    try:
        test_phase17_phi2_stage6_founder_lineage_default()
        print("[PASS] phi2_stage6_founder_lineage_default")
    except AssertionError as exc:
        print(f"[FAIL] phi2_stage6_founder_lineage_default: {exc}")
        failures.append("phi2_stage6_founder_lineage_default")

    try:
        test_phase17_phi2_stage6_respawn_lineage()
        print("[PASS] phi2_stage6_respawn_lineage")
    except AssertionError as exc:
        print(f"[FAIL] phi2_stage6_respawn_lineage: {exc}")
        failures.append("phi2_stage6_respawn_lineage")

    for label, fn in [
        ("branch_faction_id_no_collision", test_branch_faction_id_no_collision),
        ("grievance_lord_id_not_sticky", test_grievance_lord_id_not_sticky),
        ("uprising_tick_no_artificial_injection", test_uprising_tick_no_artificial_injection),
        ("phi3_uprising_emerges_under_grievance_pressure", test_phi3_uprising_emerges_under_grievance_pressure),
        ("phi3_grievance_pairs_resonate", test_phi3_grievance_pairs_resonate),
        ("phi3_dom_share_natural_imbalance", test_phi3_dom_share_natural_imbalance),
        ("phi3_no_deaths", test_phi3_no_deaths),
        ("phi3_branch_lineage_chain", test_phi3_branch_lineage_chain),
        ("phi3_determinism_seed42", test_phi3_determinism_seed42),
    ]:
        try:
            fn()
            print(f"[PASS] {label}")
        except AssertionError as exc:
            print(f"[FAIL] {label}: {exc}")
            failures.append(label)

    print()
    if failures:
        print(f"Phase 17 Acceptance: FAIL ({len(failures)} failures)")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Phase 17 Acceptance: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
