"""Strategy evolver -- genetic algorithm for strategy optimization."""
from __future__ import annotations

import copy
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class Individual:
    """An individual in the population."""
    params: dict
    fitness: float = 0.0
    strategy_name: str = ""
    generation: int = 0

    def to_dict(self) -> dict:
        return {
            "params": self.params,
            "fitness": self.fitness,
            "strategy_name": self.strategy_name,
            "generation": self.generation,
        }


class StrategyEvolver:
    """Genetic algorithm for strategy parameter evolution."""

    def __init__(self, param_ranges: dict[str, tuple],
                 population_size: int = 20,
                 mutation_rate: float = 0.1,
                 crossover_rate: float = 0.7,
                 elite_count: int = 2):
        """
        Args:
            param_ranges: Dict of param_name -> (min_val, max_val).
            population_size: Number of individuals per generation.
            mutation_rate: Probability of mutation per parameter.
            crossover_rate: Probability of crossover.
            elite_count: Number of elite individuals preserved each generation.
        """
        self.param_ranges = param_ranges
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_count = elite_count
        self.population: list[Individual] = []
        self.generation: int = 0
        self.best_individual: Optional[Individual] = None
        self.history: list[dict] = []

    def initialize(self) -> list[Individual]:
        """Create initial random population."""
        self.population = []
        for _ in range(self.population_size):
            params = {}
            for name, (lo, hi) in self.param_ranges.items():
                if isinstance(lo, int) and isinstance(hi, int):
                    params[name] = random.randint(lo, hi)
                else:
                    params[name] = random.uniform(lo, hi)
            self.population.append(Individual(params=params, generation=0))
        return self.population

    def evaluate(self, fitness_fn: Callable[[dict], float]) -> list[Individual]:
        """Evaluate fitness for all individuals."""
        for ind in self.population:
            try:
                ind.fitness = fitness_fn(ind.params)
            except Exception as e:
                logger.warning("Fitness evaluation failed: %s", e)
                ind.fitness = -float("inf")

        self.population.sort(key=lambda x: x.fitness, reverse=True)

        if self.population:
            if (self.best_individual is None or
                    self.population[0].fitness > self.best_individual.fitness):
                self.best_individual = copy.deepcopy(self.population[0])

        return self.population

    def evolve(self, fitness_fn: Callable[[dict], float]) -> list[Individual]:
        """Run one generation of evolution."""
        self.evaluate(fitness_fn)

        # Record history
        self.history.append({
            "generation": self.generation,
            "best_fitness": self.population[0].fitness if self.population else 0,
            "avg_fitness": sum(i.fitness for i in self.population) / max(len(self.population), 1),
            "best_params": self.population[0].params if self.population else {},
        })

        # Elite preservation
        new_population = [copy.deepcopy(ind) for ind in self.population[:self.elite_count]]

        # Fill rest with crossover + mutation
        while len(new_population) < self.population_size:
            parent1 = self._tournament_select()
            parent2 = self._tournament_select()

            if random.random() < self.crossover_rate:
                child_params = self._crossover(parent1.params, parent2.params)
            else:
                child_params = copy.deepcopy(parent1.params)

            child_params = self._mutate(child_params)
            child = Individual(
                params=child_params,
                generation=self.generation + 1,
            )
            new_population.append(child)

        self.population = new_population
        self.generation += 1
        return self.population

    def run(self, fitness_fn: Callable[[dict], float],
            generations: int = 10) -> Individual:
        """Run multiple generations and return best individual."""
        if not self.population:
            self.initialize()

        for _ in range(generations):
            self.evolve(fitness_fn)
            logger.info(
                "Gen %d: best=%.2f, avg=%.2f",
                self.generation - 1,
                self.history[-1]["best_fitness"],
                self.history[-1]["avg_fitness"],
            )

        return self.best_individual or self.population[0]

    def _tournament_select(self, k: int = 3) -> Individual:
        """Tournament selection."""
        candidates = random.sample(
            self.population, min(k, len(self.population))
        )
        return max(candidates, key=lambda x: x.fitness)

    def _crossover(self, params1: dict, params2: dict) -> dict:
        """Uniform crossover."""
        child = {}
        for key in params1:
            if random.random() < 0.5:
                child[key] = params1[key]
            else:
                child[key] = params2.get(key, params1[key])
        return child

    def _mutate(self, params: dict) -> dict:
        """Mutate parameters."""
        for name, (lo, hi) in self.param_ranges.items():
            if name in params and random.random() < self.mutation_rate:
                if isinstance(lo, int) and isinstance(hi, int):
                    params[name] = random.randint(lo, hi)
                else:
                    # Gaussian mutation
                    range_size = hi - lo
                    params[name] += random.gauss(0, range_size * 0.1)
                    params[name] = max(lo, min(hi, params[name]))
        return params

    def to_dict(self) -> dict:
        return {
            "generation": self.generation,
            "population_size": self.population_size,
            "best_individual": self.best_individual.to_dict() if self.best_individual else None,
            "history": self.history,
        }
