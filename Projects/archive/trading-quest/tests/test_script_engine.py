"""Tests for script engine."""
import os
import tempfile
import unittest
from pathlib import Path

from tq.strategy.script_engine import create_script_template, load_all_scripts


class TestScriptEngine(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_create_script_template(self):
        path = create_script_template("my_strat", Path(self.tmp_dir))
        self.assertTrue(path.exists())
        content = path.read_text()
        self.assertIn("class MyStratStrategy", content)
        self.assertIn("def decide", content)

    def test_load_all_scripts_empty_dir(self):
        scripts = load_all_scripts(Path(self.tmp_dir))
        self.assertEqual(len(scripts), 0)

    def test_load_scripts_from_nonexistent_dir(self):
        scripts = load_all_scripts(Path("/nonexistent/path"))
        self.assertEqual(len(scripts), 0)


if __name__ == "__main__":
    unittest.main()
