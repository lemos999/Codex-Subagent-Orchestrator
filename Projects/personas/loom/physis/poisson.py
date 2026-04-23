"""Bridson Poisson-disk sampling on a discrete 2D grid."""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np


def bridson_poisson_disk(
    width: int,
    height: int,
    r: int,
    rng: np.random.Generator,
    is_allowed: Optional[Callable[[int, int], bool]] = None,
    k: int = 30,
) -> list[tuple[int, int]]:
    """Return deterministically sorted Poisson-disk samples on an integer grid."""
    if width <= 0 or height <= 0 or r <= 0:
        return []

    allowed = [
        (x, y)
        for y in range(height)
        for x in range(width)
        if is_allowed is None or is_allowed(x, y)
    ]
    if not allowed:
        return []

    cell_size = r
    grid_w = (width + cell_size - 1) // cell_size
    grid_h = (height + cell_size - 1) // cell_size
    grid: list[list[tuple[int, int] | None]] = [
        [None for _ in range(grid_w)] for _ in range(grid_h)
    ]

    def in_bounds(x: int, y: int) -> bool:
        return 0 <= x < width and 0 <= y < height

    def is_valid(x: int, y: int) -> bool:
        if not in_bounds(x, y):
            return False
        if is_allowed is not None and not is_allowed(x, y):
            return False
        gx = x // cell_size
        gy = y // cell_size
        for ny in range(max(0, gy - 2), min(grid_h, gy + 3)):
            for nx in range(max(0, gx - 2), min(grid_w, gx + 3)):
                other = grid[ny][nx]
                if other is None:
                    continue
                if max(abs(other[0] - x), abs(other[1] - y)) < r:
                    return False
        return True

    def add_point(point: tuple[int, int], samples: list[tuple[int, int]], active: list[int]) -> None:
        samples.append(point)
        active.append(len(samples) - 1)
        gx = point[0] // cell_size
        gy = point[1] // cell_size
        grid[gy][gx] = point

    samples: list[tuple[int, int]] = []
    active: list[int] = []
    first = allowed[int(rng.integers(len(allowed)))]
    add_point(first, samples, active)

    while active:
        active_idx = int(rng.integers(len(active)))
        base = samples[active[active_idx]]
        found = False
        for _ in range(k):
            dx = int(rng.integers(-2 * r, 2 * r + 1))
            dy = int(rng.integers(-2 * r, 2 * r + 1))
            dist = max(abs(dx), abs(dy))
            if dist < r or dist > 2 * r:
                continue
            cand = (base[0] + dx, base[1] + dy)
            if not is_valid(cand[0], cand[1]):
                continue
            add_point(cand, samples, active)
            found = True
            break
        if not found:
            active.pop(active_idx)

    return sorted(samples)
