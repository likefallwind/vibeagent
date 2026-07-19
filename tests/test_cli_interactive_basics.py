import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliInteractiveBasicsTests(unittest.TestCase):
    def test_main_interactive_uses_requested_cwd_and_restores_original_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            original_cwd = Path.cwd()
            seen_cwds: list[Path] = []

            def fake_git_status_text() -> str:
                seen_cwds.append(Path.cwd())
                return "Git status:\n  ok: yes"

            with (
                patch("builtins.input", side_effect=["/git-status", "/exit"]),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_git_status_text", side_effect=fake_git_status_text),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base])

        self.assertEqual(exit_code, 0)
        self.assertIn("Git status:", stdout.getvalue())
        self.assertEqual(seen_cwds, [Path(base).resolve()])
        self.assertEqual(Path.cwd(), original_cwd)
        create_chat_client.assert_not_called()

    def test_main_interactive_tool_search_reports_invalid_option_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("builtins.input", side_effect=["/tool-search --category missing verification", "/exit"]),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tool_search_text") as get_tool_search_text,
            redirect_stdout(stdout),
        ):
            exit_code = main([])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /tool-search", output)
        self.assertIn("--category must be one of:", output)
        get_tool_search_text.assert_not_called()
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
