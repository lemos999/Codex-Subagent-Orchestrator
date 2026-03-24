"""Tests for strategy evolver."""
import unittest

from tq.quest.evolver import StrategyEvolver, Individual


class TestIndividual(unittest.TestCase):

    def test_to_dict(self):
        ind = Individual(params={"a": 1, "b": 2}, fitness=10.0)
        d = ind.to_dict()
        self.assertEqual(d["fitness"], 10.0)
        self.assertIn("params", d)


class TestStrategyEvolver(unittest.TestCase):

    def setUp(self):
        self.param_ranges = {
            "fast": (5, 20),
            "slow": (20, 50),
        }
        self.evolver = StrategyEvolver(
            self.param_ranges, population_size=10,
            mutation_rate=0.2, crossover_rate=0.7,
        )

    def test_initialize(self):
        pop = self.evolver.initialize()
        self.assertEqual(len(pop), 10)

    def test_evaluate(self):
        self.evolver.initialize()
        self.evolver.evaluate(lambda p: p.get("fast", 0) + p.get("slow", 0))
        self.assertIsNotNone(self.evolver.best_individual)

    def test_evolve(self):
        self.evolver.initialize()
        self.evolver.evolve(lambda p: p.get("fast", 0) * 2)
        self.assertEqual(self.evolver.generation, 1)

    def test_run(self):
        best = self.evolver.run(
            lambda p: -(p.get("fast", 10) - 12) ** 2,
            generations=5,
        )
        self.assertIsNotNone(best)
        self.assertGreater(best.fitness, -1000)

    def test_history_recorded(self):
        self.evolver.run(lambda p: 0, generations=3)
        self.assertEqual(len(self.evolver.history), 3)

    def test_to_dict(self):
        self.evolver.run(lambda p: 0, generations=2)
        d = self.evolver.to_dict()
        self.assertIn("generation", d)
        self.assertIn("history", d)

    def test_param_ranges_respected(self):
        self.evolver.initialize()
        for ind in self.evolver.population:
            self.assertGreaterEqual(ind.params["fast"], 5)
            self.assertLessEqual(ind.params["fast"], 20)
            self.assertGreaterEqual(ind.params["slow"], 20)
            self.assertLessEqual(ind.params["slow"], 50)


if __name__ == "__main__":
    unittest.main()
