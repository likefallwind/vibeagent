import unittest

from vibeagent.commands import LocalCommand, get_model_text, is_exit_command, parse_local_command


class CommandTests(unittest.TestCase):
    def test_is_exit_command_only_treats_exit_as_the_exit_command(self) -> None:
        self.assertTrue(is_exit_command("/exit"))
        self.assertTrue(is_exit_command("  /exit  "))
        self.assertFalse(is_exit_command("exit"))
        self.assertFalse(is_exit_command("/quit"))
        self.assertFalse(is_exit_command("/exit now"))

    def test_parse_local_command_recognizes_local_commands(self) -> None:
        self.assertEqual(parse_local_command("/help"), LocalCommand(type="help"))
        self.assertEqual(parse_local_command("  /model  "), LocalCommand(type="model"))
        self.assertEqual(parse_local_command("/exit"), LocalCommand(type="exit"))
        self.assertIsNone(parse_local_command("write a script"))

    def test_get_model_text_reports_model_configuration_without_exposing_the_key(self) -> None:
        text = get_model_text(
            {
                "MINIMAX_API_KEY": "secret-key",
                "MINIMAX_MODEL": "custom-model",
                "MINIMAX_BASE_URL": "https://example.com/v1/",
            }
        )

        self.assertIn("model: custom-model", text)
        self.assertIn("baseUrl: https://example.com/v1", text)
        self.assertIn("apiKey: configured via MINIMAX_API_KEY", text)
        self.assertNotIn("secret-key", text)


if __name__ == "__main__":
    unittest.main()
