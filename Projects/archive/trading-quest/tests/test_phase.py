"""Tests for quest phases."""
import unittest
from datetime import date

from tq.quest.phase import QuestPhase, PhaseConfig, PhaseManager


class TestQuestPhase(unittest.TestCase):

    def test_phase_values(self):
        self.assertEqual(QuestPhase.PHASE_1.value, 1)
        self.assertEqual(QuestPhase.PHASE_2.value, 2)
        self.assertEqual(QuestPhase.PHASE_3.value, 3)

    def test_phase_labels(self):
        self.assertEqual(QuestPhase.PHASE_1.label, "Exploration")
        self.assertEqual(QuestPhase.PHASE_2.label, "Expansion")
        self.assertEqual(QuestPhase.PHASE_3.label, "Mastery")


class TestPhaseConfig(unittest.TestCase):

    def test_default_configs(self):
        configs = PhaseConfig.default_configs()
        self.assertIn(QuestPhase.PHASE_1, configs)
        self.assertIn(QuestPhase.PHASE_2, configs)
        self.assertIn(QuestPhase.PHASE_3, configs)

    def test_phase1_no_auto_batch(self):
        configs = PhaseConfig.default_configs()
        self.assertFalse(configs[QuestPhase.PHASE_1].auto_batch)

    def test_phase2_auto_batch(self):
        configs = PhaseConfig.default_configs()
        self.assertTrue(configs[QuestPhase.PHASE_2].auto_batch)


class TestPhaseManager(unittest.TestCase):

    def test_initial_phase(self):
        pm = PhaseManager(date(2024, 1, 1))
        self.assertEqual(pm.current_phase, QuestPhase.PHASE_1)

    def test_record_day_stays_phase1(self):
        pm = PhaseManager(date(2024, 1, 1))
        for _ in range(5):
            pm.record_day(5, 0.01)
        self.assertEqual(pm.current_phase, QuestPhase.PHASE_1)

    def test_transition_to_phase2(self):
        pm = PhaseManager(date(2024, 1, 1))
        for _ in range(10):
            pm.record_day(0, 0.01)
        self.assertEqual(pm.current_phase, QuestPhase.PHASE_2)

    def test_no_transition_on_high_drawdown(self):
        pm = PhaseManager(date(2024, 1, 1))
        for _ in range(15):
            pm.record_day(20, 0.18)  # high drawdown
        self.assertEqual(pm.current_phase, QuestPhase.PHASE_1)

    def test_get_config(self):
        pm = PhaseManager(date(2024, 1, 1))
        config = pm.get_config()
        self.assertEqual(config.phase, QuestPhase.PHASE_1)

    def test_to_dict(self):
        pm = PhaseManager(date(2024, 1, 1))
        d = pm.to_dict()
        self.assertIn("current_phase", d)
        self.assertIn("phase_label", d)

    def test_transition_log(self):
        pm = PhaseManager(date(2024, 1, 1))
        for _ in range(10):
            pm.record_day(0, 0.01)
        self.assertGreater(len(pm.transition_log), 0)


if __name__ == "__main__":
    unittest.main()
