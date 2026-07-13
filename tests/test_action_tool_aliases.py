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
    SearchAction,
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

    def test_claude_grep_i_maps_to_case_insensitive_search(self) -> None:
        action = parse_tool_action("Grep", {"pattern": "needle", "-i": True})

        self.assertIsInstance(action, SearchAction)
        self.assertFalse(action.case_sensitive)

    def test_claude_grep_glob_maps_to_file_glob(self) -> None:
        action = parse_tool_action("Grep", {"pattern": "needle", "glob": "*.py"})

        self.assertIsInstance(action, SearchAction)
        self.assertEqual(action.file_glob, "*.py")

    def test_claude_grep_type_maps_to_file_glob(self) -> None:
        action = parse_tool_action("Grep", {"pattern": "needle", "type": "python"})
        explicit_glob = parse_tool_action("Grep", {"pattern": "needle", "type": "py", "glob": "*.pyi"})

        self.assertIsInstance(action, SearchAction)
        self.assertEqual(action.file_glob, "*.py")
        self.assertIsInstance(explicit_glob, SearchAction)
        self.assertEqual(explicit_glob.file_glob, "*.pyi")

    def test_claude_grep_files_with_matches_preserves_output_mode(self) -> None:
        action = parse_tool_action("Grep", {"pattern": "needle", "output_mode": "files_with_matches"})

        self.assertIsInstance(action, SearchAction)
        self.assertEqual(action.output_mode, "files_with_matches")

    def test_claude_grep_count_preserves_output_mode(self) -> None:
        action = parse_tool_action("Grep", {"pattern": "needle", "output_mode": "count"})

        self.assertIsInstance(action, SearchAction)
        self.assertEqual(action.output_mode, "count")

    def test_claude_grep_context_flag_maps_to_context_lines(self) -> None:
        action = parse_tool_action("Grep", {"pattern": "needle", "-C": 3})

        self.assertIsInstance(action, SearchAction)
        self.assertEqual(action.context_lines, 3)

    def test_claude_grep_i_executes_case_insensitive_search(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-alias-") as base:
            root = Path(base)
            (root / "app.py").write_text("Needle\n", encoding="utf-8")
            action = parse_tool_action("Grep", {"pattern": "needle", "-i": True})

            observation = execute_action(create_run_workspace(root), action)

        self.assertEqual(observation.kind, "search")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.total, 1)
        self.assertFalse(observation.case_sensitive)

    def test_claude_grep_glob_executes_filtered_search(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-alias-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("needle\n", encoding="utf-8")
            (root / "src" / "notes.txt").write_text("needle\n", encoding="utf-8")
            action = parse_tool_action("Grep", {"pattern": "needle", "path": "src", "glob": "*.py"})

            observation = execute_action(create_run_workspace(root), action)

        self.assertEqual(observation.kind, "search")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.file_glob, "*.py")
        self.assertEqual(observation.total, 1)
        self.assertEqual(observation.matches, ["src/app.py:1: needle"])
        self.assertIn("fileGlob=*.py", format_observations([observation]))

    def test_claude_grep_type_executes_filtered_search(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-alias-") as base:
            root = Path(base)
            (root / "app.py").write_text("needle\n", encoding="utf-8")
            (root / "notes.md").write_text("needle\n", encoding="utf-8")
            action = parse_tool_action("Grep", {"pattern": "needle", "type": "py"})

            observation = execute_action(create_run_workspace(root), action)

        self.assertEqual(observation.kind, "search")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.file_glob, "*.py")
        self.assertEqual(observation.total, 1)
        self.assertEqual(observation.matches, ["app.py:1: needle"])

    def test_claude_grep_files_with_matches_executes_file_only_search(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-alias-") as base:
            root = Path(base)
            (root / "app.py").write_text("needle\nneedle again\n", encoding="utf-8")
            (root / "notes.md").write_text("needle\n", encoding="utf-8")
            action = parse_tool_action("Grep", {"pattern": "needle", "output_mode": "files_with_matches"})

            observation = execute_action(create_run_workspace(root), action)

        self.assertEqual(observation.kind, "search")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.output_mode, "files_with_matches")
        self.assertEqual(observation.total, 2)
        self.assertEqual(observation.matches, ["app.py", "notes.md"])
        self.assertIn("outputMode=files_with_matches", format_observations([observation]))

    def test_claude_grep_count_executes_per_file_count_search(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-alias-") as base:
            root = Path(base)
            (root / "app.py").write_text("needle\nneedle again\n", encoding="utf-8")
            (root / "notes.md").write_text("needle\n", encoding="utf-8")
            action = parse_tool_action("Grep", {"pattern": "needle", "output_mode": "count"})

            observation = execute_action(create_run_workspace(root), action)

        self.assertEqual(observation.kind, "search")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.output_mode, "count")
        self.assertEqual(observation.total, 2)
        self.assertEqual(observation.matches, ["app.py: 2", "notes.md: 1"])
        self.assertIn("Found matches in 2 file(s).", observation.message)
        self.assertIn("outputMode=count", format_observations([observation]))

    def test_claude_grep_directional_context_flags_execute_with_symmetric_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-alias-") as base:
            root = Path(base)
            (root / "app.py").write_text("before 1\nbefore 2\nneedle\nafter 1\nafter 2\n", encoding="utf-8")
            action = parse_tool_action("Grep", {"pattern": "needle", "-A": 2, "-B": 1})

            observation = execute_action(create_run_workspace(root), action)

        self.assertEqual(observation.kind, "search")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.context_lines, 2)
        self.assertEqual(
            observation.matches,
            ["app.py:1:  before 1\napp.py:2:  before 2\napp.py:3:> needle\napp.py:4:  after 1\napp.py:5:  after 2"],
        )


if __name__ == "__main__":
    unittest.main()
