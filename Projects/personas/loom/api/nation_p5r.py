# -*- coding: utf-8 -*-
"""Phi-5 Read-only API Surface for Nation entity (v0: 2 slot freeze).

Direction: Phi-5 -> Phi-4 -> Phi-3 -> Phi-2 -> Phi-1 (read-only, no reverse mutation)

v0 frozen slots (2):
- nation.sovereignty       (<- DC-1 SIS rev.2 distribution.json shape)
- nation.charter_overlap   (<- DC-2 CPCM rev.3 SnapshotMetrics keys mirror)

Reserved (provisional, awaiting Section 3.7 closure for each component):
- nation.dissolution_history       (<- NDP) -- body defined after NDP Section 3.7 6-stage closure
- nation.lord_replacement_history  (<- LRT) -- body defined after LRT Section 3.7 6-stage closure
- nation.federation_state          (<- FMR) -- body defined after FMR Section 3.7 6-stage closure

These reserved slots are pre-approved (2026-05-07) but their typed bodies are
NOT exposed here -- only after each component passes Section 3.7 closure.

Section 1.0 DC-1 caveat: sovereignty body semantics MUST NOT freeze SIS quantile
values (P50/P67/P75) as fixed types. Only the structural type is contracted
here; runtime values are dynamic and may shift across Section 3.7 closure cycles.

DC-2 caveat (rev.2 mirror): NationCharterOverlap field names mirror CPCM rev.3
SnapshotMetrics JSON keys (mean_jaccard / pair_count) to keep the producer ->
consumer truth surface intact (Step 3.5 Finding 1).

Step 3.5 Finding 2 reference: regression contract authority is
PHASE-17-NATION-PHASE3-REGRESSION-CONTRACT.md (single source of truth).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class NationSovereignty(Protocol):
    """Sovereignty intensity surface (<- SIS rev.2 distribution.json shape).

    Body semantics deferred per Section 1.0 caveat. Structural shape only.
    Runtime values are dynamic -- type signature only, no fixed values baked.
    """

    @property
    def dom_share(self) -> float: ...

    @property
    def member_share_per_faction(self) -> dict[str, float]: ...

    @property
    def conflict_pair_count(self) -> int: ...

    @property
    def cross_faction_lord_count(self) -> int: ...


@runtime_checkable
class NationCharterOverlap(Protocol):
    """Charter primitive overlap surface (<- CPCM rev.3 output JSON keys mirror).

    Body semantics deferred per Section 1.0 caveat. Structural shape only.
    Field names MIRROR DC-2 CPCM rev.3 SnapshotMetrics keys (no rename, no
    aggregate) to keep producer -> consumer truth surface intact
    (Step 3.5 Finding 1).
    Runtime values are dynamic -- type signature only, no fixed values baked.
    """

    @property
    def mean_jaccard(self) -> float: ...

    @property
    def pair_count(self) -> int: ...


@runtime_checkable
class NationReadOnly(Protocol):
    """Phi-5 read-only consumer surface for a nation entity.

    v0: 2 slots frozen (sovereignty + charter_overlap).
    Reserved 3 slots (dissolution_history / lord_replacement_history /
    federation_state) are NOT exposed as typed fields until each component
    passes Section 3.7 6-stage closure -- see module docstring.
    """

    @property
    def sovereignty(self) -> NationSovereignty: ...

    @property
    def charter_overlap(self) -> NationCharterOverlap: ...
