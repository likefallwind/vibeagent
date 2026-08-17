from __future__ import annotations

import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.command_parsing import parse_local_command


class CliInteractiveAutocompactTests(unittest.TestCase):
    def test_parser_recognizes_command_and_argument(self) -> None:
        shown = parse_local_command("/autocompact")
        changed = parse_local_command("/autocompact 300k")

        self.assertIsNotNone(shown)
        self.assertEqual(shown.type, "autocompact")
        self.assertIsNone(shown.argument)
        self.assertIsNotNone(changed)
        self.assertEqual(changed.type, "autocompact")
        self.assertEqual(changed.argument, "300k")

    def test_interactive_command_updates_current_setting_and_user_settings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-interactive-autocompact-") as base:
            root = Path(base) / "project"
            home = Path(base) / "home"
            root.mkdir(parents=True)
            output = io.StringIO()
            previous = Path.cwd()
            try:
                with (
                    patch("builtins.input", side_effect=["/autocompact 300k", "/autocompact", "/exit"]),
                    patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                    patch("vibeagent.autocompact_settings.user_home", return_value=home),
                    redirect_stdout(output),
                ):
                    os.chdir(root)
                    code = run_interactive_loop(command_namespace={})
            finally:
                os.chdir(previous)
            saved = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(saved["autoCompactWindow"], 300_000)
        self.assertIn("Auto-compact configuration updated", output.getvalue())
        self.assertIn("window: 300k", output.getvalue())
        self.assertIn("source: ~/.claude/settings.json", output.getvalue())

    def test_interactive_command_rejects_invalid_value_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-interactive-autocompact-error-") as base:
            root = Path(base) / "project"
            home = Path(base) / "home"
            root.mkdir(parents=True)
            output = io.StringIO()
            previous = Path.cwd()
            try:
                with (
                    patch("builtins.input", side_effect=["/autocompact 2m", "/exit"]),
                    patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                    patch("vibeagent.autocompact_settings.user_home", return_value=home),
                    redirect_stdout(output),
                ):
                    os.chdir(root)
                    code = run_interactive_loop(command_namespace={})
            finally:
                os.chdir(previous)

        self.assertEqual(code, 0)
        self.assertFalse((home / ".claude/settings.json").exists())
        self.assertIn("Usage: /autocompact [auto|TOKENS]", output.getvalue())


if __name__ == "__main__":
    unittest.main()
