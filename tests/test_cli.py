import unittest

from vibeagent.cli import format_error


class Http401Error(Exception):
    status = 401


class CliTests(unittest.TestCase):
    def test_format_error_uses_provider_neutral_401_guidance(self) -> None:
        text = format_error(Http401Error("unauthorized"))

        self.assertIn("unauthorized", text)
        self.assertIn("configured model provider rejected the API key", text)
        self.assertIn("Check /model", text)
        self.assertNotIn("MiniMax rejected", text)
        self.assertNotIn("DEEPSEEK_API_KEY", text)

    def test_format_error_returns_plain_error_for_other_errors(self) -> None:
        self.assertEqual(format_error(ValueError("bad")), "bad")


if __name__ == "__main__":
    unittest.main()
