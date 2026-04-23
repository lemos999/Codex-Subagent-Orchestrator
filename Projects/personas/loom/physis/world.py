"""World grid and Phase 17 land initialization helpers."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Iterator, Optional
import warnings

import numpy as np

from .poisson import bridson_poisson_disk


ALLOWED_BIOMES = frozenset({"plain", "forest", "mountain", "water", "desert", "tundra"})
DOMINANCE_RECALC_EVERY = 24
DOMINANCE_RADIUS_K = 3
DOMINANCE_VOTE_MARGIN = 2
INIT_POISSON_FALLBACK = [5, 4, 3]
ALLOWED_INIT_BIOMES = frozenset({"plain", "forest", "desert", "tundra"})


@dataclass(slots=True)
class LandCell:
    x: int
    y: int
    biome: str
    elevation: int = 0
    resources: dict = field(default_factory=dict)
    path_cost: float = 1.0
    building: Optional[dict] = None
    territoryRef: Optional[str] = None
    climate: dict = field(default_factory=lambda: {"rainfall": 0.0, "temperature": 20.0})


def set_biome_initial(cell: LandCell, biome: str) -> None:
    """Only valid entry point for initial biome assignment."""
    assert biome in ALLOWED_BIOMES, f"Unknown biome: {biome}"
    cell.biome = biome


class World:
    """Dense 2D tile grid for Phase 17 land."""

    def __init__(self, width: int = 50, height: int = 50):
        self.width = width
        self.height = height
        self._land: list[list[LandCell]] = [
            [LandCell(x=x, y=y, biome="plain") for x in range(width)]
            for y in range(height)
        ]

    def get_cell(self, x: int, y: int) -> LandCell:
        return self._land[y][x]

    def iter_cells(self) -> Iterator[LandCell]:
        for row in self._land:
            yield from row

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height


def chebyshev(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def project_territory(world: World, personas: list) -> None:
    """Project persona territory dominance onto the land grid.

    Rule (Decision 6 — 2-vote hysteresis):
        - No residents within Chebyshev K → cell.territoryRef = None
        - Clear winner (top_count - second_count >= DOMINANCE_VOTE_MARGIN)
          → cell.territoryRef = winner_territory_id
        - Contested (margin < DOMINANCE_VOTE_MARGIN) → cell.territoryRef
          is left **unchanged** (previous value retained).

    The "left unchanged" branch is intentional hysteresis: it prevents
    flip-flop when two territories contest a border cell with roughly
    equal density. Φ-2 faction logic may replace this with explicit
    CONTESTED state; until then, stale retention is the contract.
    """
    snapshot = {
        p.id: (p.pos, p.territory)
        for p in sorted(personas, key=lambda persona: persona.id)
    }
    updates: dict[tuple[int, int], Optional[str]] = {}
    for cell in world.iter_cells():
        residents = [
            (pid, terr)
            for pid, (pos, terr) in snapshot.items()
            if terr and chebyshev(pos, (cell.x, cell.y)) <= DOMINANCE_RADIUS_K
        ]
        if not residents:
            updates[(cell.x, cell.y)] = None
            continue

        counts = Counter(terr for _, terr in residents)
        top, top_count = counts.most_common(1)[0]
        second_count = counts.most_common(2)[1][1] if len(counts) > 1 else 0
        if top_count - second_count >= DOMINANCE_VOTE_MARGIN:
            updates[(cell.x, cell.y)] = top

    for (x, y), ref in updates.items():
        world.get_cell(x, y).territoryRef = ref


def initialize_world(
    world: World,
    personas: list,
    territories: Optional[dict],
    rng: np.random.Generator,
) -> None:
    """Initialize Phase 17 world state using engine RNG only."""
    _init_biomes(world, rng)
    _init_territories(world, territories)
    positions = _place_poisson(world, n=len(personas), rng=rng)
    _assign_personas(personas, positions, rng)
    project_territory(world, personas)


def _init_biomes(world: World, rng: np.random.Generator) -> None:
    distribution = [
        ("water", 0.10),
        ("mountain", 0.10),
        ("plain", 0.40),
        ("forest", 0.25),
        ("desert", 0.10),
        ("tundra", 0.05),
    ]
    biomes, weights = zip(*distribution)
    for cell in world.iter_cells():
        biome = str(rng.choice(biomes, p=weights))
        set_biome_initial(cell, biome)
        cell.resources = _default_resources(biome)
        cell.path_cost = _default_path_cost(biome)
        cell.elevation = _default_elevation(biome, rng)


def _init_territories(world: World, territories: Optional[dict]) -> None:
    _ = world
    _ = territories


def _default_resources(biome: str) -> dict:
    return {
        "plain": {"food": 2.0, "material": 1.0},
        "forest": {"food": 1.5, "material": 2.5},
        "desert": {"food": 0.3, "material": 0.5},
        "tundra": {"food": 0.2, "material": 0.4},
        "water": {"food": 1.0, "material": 0.0},
        "mountain": {"food": 0.1, "material": 3.0},
    }[biome]


def _default_path_cost(biome: str) -> float:
    return {
        "plain": 1.0,
        "forest": 1.2,
        "desert": 1.5,
        "tundra": 1.6,
        "water": 3.0,
        "mountain": 2.5,
    }[biome]


def _default_elevation(biome: str, rng: np.random.Generator) -> int:
    ranges = {
        "water": (0, 1),
        "plain": (1, 3),
        "forest": (2, 5),
        "desert": (1, 4),
        "tundra": (2, 6),
        "mountain": (6, 10),
    }
    low, high = ranges[biome]
    return int(rng.integers(low, high + 1))


def _place_poisson(world: World, n: int, rng: np.random.Generator) -> list[tuple[int, int]]:
    for r in INIT_POISSON_FALLBACK:
        positions = bridson_poisson_disk(
            world.width,
            world.height,
            r=r,
            rng=rng,
            is_allowed=lambda x, y: world.get_cell(x, y).biome in ALLOWED_INIT_BIOMES,
        )
        if len(positions) >= n:
            return positions[:n]
        warnings.warn(f"Poisson r={r} failed ({len(positions)}/{n}); trying next radius.")
    raise RuntimeError(
        f"Initial placement failed for {n} personas on {world.width}x{world.height} grid."
    )


def _assign_personas(
    personas: list,
    positions: list[tuple[int, int]],
    rng: np.random.Generator,
) -> None:
    if len(positions) != len(personas):
        raise ValueError(f"positions/personas mismatch: {len(positions)} != {len(personas)}")

    sorted_personas = sorted(personas, key=lambda persona: persona.id)
    indices = np.arange(len(positions))
    rng.shuffle(indices)
    for persona, idx in zip(sorted_personas, indices):
        persona.pos = positions[int(idx)]
