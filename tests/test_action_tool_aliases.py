from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.actions import execute_action
from vibeagent.action_parsing import parse_tool_action
from vibeagent.prompts import format_observations
from vibeagent.types import (
    ReadFileAction,
    RegexReplaceAction,
    RunCommandAction,
    StartCommandAction,
    WebFetchObservation,
)
from vibeagent.workspace import create_run_workspace


class ActionToolAliasTests(unittest.TestCase):
    def test_claude_read_zero_offset_maps_to_first_line(self) -> None:
        action = parse_tool_action("Read", {"file_path": "app.py", "offset": 0, "limit": 5})
        notebook_action = parse_tool_action(
            "NotebookRead",
            {"notebook_path": "analysis.ipynb", "offset": 0, "limit": 3},
        )

        self.assertIsInstance(action, ReadFileAction)
        self.assertEqual(action.start_line, 1)
        self.assertEqual(action.line_count, 5)
        self.assertIsInstance(notebook_action, ReadFileAction)
        self.assertEqual(notebook_action.start_line, 1)
        self.assertEqual(notebook_action.line_count, 3)

    def test_claude_edit_replace_all_maps_to_literal_regex_replace(self) -> None:
        action = parse_tool_action(
            "Edit",
            {
                "file_path": "app.py",
                "old_string": "a.b",
                "new_string": r"C:\tmp",
                "replace_all": True,
            },
        )
        notebook_action = parse_tool_action(
            "NotebookEdit",
            {
                "notebook_path": "analysis.ipynb",
                "old_string": "x+y",
                "new_string": "z",
                "replace_all": True,
            },
        )

        self.assertIsInstance(action, RegexReplaceAction)
        self.assertEqual(action.path, "app.py")
        self.assertEqual(action.pattern, r"a\.b")
        self.assertEqual(action.replacement, r"C:\\tmp")
        self.assertEqual(action.count, 0)
        self.assertIsInstance(notebook_action, RegexReplaceAction)
        self.assertEqual(notebook_action.path, "analysis.ipynb")
        self.assertEqual(notebook_action.pattern, r"x\+y")

    def test_claude_edit_replace_all_executes_literal_global_replacement(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-alias-") as base:
            root = Path(base)
            (root / "app.py").write_text("a.b aab a.b\n", encoding="utf-8")
            action = parse_tool_action(
                "Edit",
                {
                    "file_path": "app.py",
                    "old_string": "a.b",
                    "new_string": "x",
                    "replace_all": True,
                },
            )

            observation = execute_action(create_run_workspace(root), action)

            self.assertEqual((root / "app.py").read_text(encoding="utf-8"), "x aab x\n")

        self.assertEqual(observation.kind, "regex_replace")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.replacements, 2)

    def test_claude_bash_timeout_maps_to_run_command_timeout_ms(self) -> None:
        action = parse_tool_action(
            "Bash",
            {
                "command": "python -m unittest",
                "timeout": 10_000,
                "max_output_chars": 4_000,
            },
        )

        self.assertIsInstance(action, RunCommandAction)
        self.assertEqual(action.timeout_ms, 10_000)
        self.assertEqual(action.max_output_chars, 4_000)

    def test_claude_bash_background_ignores_sync_only_options(self) -> None:
        action = parse_tool_action(
            "Bash",
            {
                "command": "python -m http.server",
                "run_in_background": True,
                "timeout": 10_000,
                "timeout_ms": 20_000,
                "max_output_chars": 4_000,
            },
        )

        self.assertIsInstance(action, StartCommandAction)
        self.assertEqual(action.command, "python -m http.server")

    def test_claude_web_fetch_preserves_prompt_intent(self) -> None:
        action = parse_tool_action(
            "WebFetch",
            {"url": "https://docs.python.org/3/", "prompt": "Extract install commands."},
        )

        self.assertEqual(action.type, "web_fetch")
        self.assertEqual(action.prompt, "Extract install commands.")

    def test_web_fetch_observation_includes_prompt_for_next_model_step(self) -> None:
        fetched = WebFetchObservation(
            kind="web_fetch",
            ok=True,
            url="https://docs.python.org/3/",
            final_url="https://docs.python.org/3/",
            status=200,
            content_type="text/html",
            title="Python docs",
            text="Install Python.",
            text_truncated=False,
            max_text_chars=20_000,
            error=None,
            message="Fetched public document.",
        )
        action = parse_tool_action(
            "WebFetch",
            {"url": "https://docs.python.org/3/", "prompt": "Extract install commands."},
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-alias-") as base, patch(
            "vibeagent.runtime_action_executor.fetch_public_document",
            return_value=fetched,
        ):
            observation = execute_action(create_run_workspace(Path(base)), action)

        self.assertEqual(observation.prompt, "Extract install commands.")
        formatted = format_observations([observation])
        self.assertIn("prompt: Extract install commands.", formatted)
        self.assertIn("Install Python.", formatted)


if __name__ == "__main__":
    unittest.main()
