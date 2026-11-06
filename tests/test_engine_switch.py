import unittest

from core.engine_manager import MODE_GEMINI, MODE_LOCAL, parse_engine_command


class EngineSwitchCommandTests(unittest.TestCase):
    def test_local_phrases(self):
        for phrase in ("Switch to local", "go offline", "use the local engine", "move to local mode"):
            with self.subTest(phrase=phrase):
                self.assertEqual(parse_engine_command(phrase), MODE_LOCAL)

    def test_gemini_phrases(self):
        for phrase in ("Switch to Gemini", "use cloud mode", "go online", "change to remote"):
            with self.subTest(phrase=phrase):
                self.assertEqual(parse_engine_command(phrase), MODE_GEMINI)

    def test_unrelated_phrases_are_not_switches(self):
        for phrase in ("Turn on the local lights", "Tell me about Gemini", "hello Lumen"):
            with self.subTest(phrase=phrase):
                self.assertIsNone(parse_engine_command(phrase))


if __name__ == "__main__":
    unittest.main()
