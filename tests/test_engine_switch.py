"""Unit tests for explicit engine-switch command parsing.

Load engine_manager as a standalone module so these unit tests do not import
core/__init__.py or initialize the desktop audio stack.
"""
import importlib.util
from pathlib import Path
import unittest

ENGINE_PATH = Path(__file__).resolve().parents[1] / "core" / "engine_manager.py"
SPEC = importlib.util.spec_from_file_location("lumen_engine_manager_test_module", ENGINE_PATH)
ENGINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENGINE)


class EngineSwitchCommandTests(unittest.TestCase):
    def test_local_phrases(self):
        for phrase in ("Switch to local", "go offline", "use the local engine", "move to local mode"):
            with self.subTest(phrase=phrase):
                self.assertEqual(ENGINE.parse_engine_command(phrase), ENGINE.MODE_LOCAL)

    def test_gemini_phrases(self):
        for phrase in ("Switch to Gemini", "use cloud mode", "go online", "change to remote"):
            with self.subTest(phrase=phrase):
                self.assertEqual(ENGINE.parse_engine_command(phrase), ENGINE.MODE_GEMINI)

    def test_unrelated_phrases_are_not_switches(self):
        for phrase in ("Turn on the local lights", "Tell me about Gemini", "hello Lumen"):
            with self.subTest(phrase=phrase):
                self.assertIsNone(ENGINE.parse_engine_command(phrase))


if __name__ == "__main__":
    unittest.main()
