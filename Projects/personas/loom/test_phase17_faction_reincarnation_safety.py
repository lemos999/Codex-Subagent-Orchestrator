"""Phase 17 faction reincarnation safety regression."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from ontology import Relationship
from test_phase17_faction import _fresh_engine


def test_phase17_faction_reincarnation_safety() -> None:
    """리인카네이션 이후 faction API와 pid-key SSoT가 유지된다."""
    engine = _fresh_engine(seed=42)
    engine._init_founder_seeds()
    assert engine.factions, "precondition: factions exist"

    secret_candidates = sorted(set(engine.personas) & set(engine.secrets))
    assert secret_candidates, "precondition: secret-backed persona exists"
    pid = secret_candidates[0]
    fid = sorted(engine.factions)[0]
    engine._change_persona_faction(pid, fid, source="affiliation")

    worker_pid = next(
        candidate
        for candidate in sorted(engine.personas)
        if candidate != pid and engine.personas[candidate].employment_id is None
    )
    job = engine.create_job(pid, "farmer", 5.0)
    assert job is not None, "precondition: employer can create job"
    employment = engine.hire(job.id, worker_pid)
    assert employment is not None, "precondition: worker can be hired"

    old_wallet = engine.wallets.get(pid)
    assert old_wallet is not None, "precondition: wallet exists"
    assert pid in engine.personas
    assert pid in engine.inners
    assert pid in engine.brains
    assert pid in engine.secrets

    engine.time.tick = 999
    inner = engine.inners[pid]
    inner.vitality = 0.0
    inner.oyok[0] = np.float16(1.0)

    deaths = engine._check_deaths()
    death = next((event for event in deaths if event.get("pid") == pid), None)
    assert death is not None, "expected reincarnation death event"

    new_pid = f"{pid}_r{engine.time.tick}"
    assert pid not in engine.personas
    assert pid not in engine.inners
    assert pid not in engine.brains
    assert pid not in engine.wallets
    assert pid not in engine.secrets
    assert new_pid in engine.personas
    assert new_pid in engine.inners
    assert new_pid in engine.brains
    assert new_pid in engine.wallets
    assert new_pid in engine.secrets
    assert engine.personas[new_pid].id == new_pid
    assert engine.inners[new_pid].persona_id == new_pid
    assert engine.wallets[new_pid].persona_id == new_pid
    assert engine.secrets[new_pid].owner_id == new_pid
    assert engine.secrets[new_pid].known_by == {new_pid}
    assert engine._faction_members_cache == {}

    other_pid = next(candidate for candidate in sorted(engine.personas) if candidate != new_pid)
    old_rel_key = Relationship(persona_a=pid, persona_b=other_pid).key()
    new_rel_key = Relationship(persona_a=new_pid, persona_b=other_pid).key()
    assert old_rel_key not in engine.relationships
    assert new_rel_key in engine.relationships
    rekeyed_rel = engine.relationships[new_rel_key]
    assert {rekeyed_rel.persona_a, rekeyed_rel.persona_b} == set(new_rel_key)

    before_count = rekeyed_rel.interaction_count
    interaction = engine._process_interaction(new_pid, other_pid, mutual=False)
    assert isinstance(interaction, dict)
    assert engine.relationships[new_rel_key].interaction_count == before_count + 1

    assert job.employer_id == new_pid
    assert employment.employer_id == new_pid
    assert employment.employee_id == worker_pid
    assert all(emp.employer_id != pid for emp in engine.employments.values())
    assert all(job_row.employer_id != pid for job_row in engine.jobs.values())

    pop = engine.faction_population_distribution()
    assert isinstance(pop, dict)
    terr = engine.faction_territory_distribution()
    assert isinstance(terr, dict)
    contact = engine.factions_in_contact(radius=1)
    assert isinstance(contact, list)
    wealth = engine.faction_wealth_distribution()
    assert isinstance(wealth, dict)
    social = engine.faction_social_matrix()
    assert isinstance(social, dict)
    grievance = engine.faction_grievance_targets()
    assert isinstance(grievance, dict)

    for key_pid, persona in engine.personas.items():
        assert key_pid == persona.id, f"identity mismatch: key={key_pid} obj.id={persona.id}"
