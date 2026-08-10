from __future__ import annotations

from contextlib import redirect_stdout
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from vibeagent import __version__
from vibeagent.cli_completion import (
    InteractivePromptCompleter,
    interactive_prompt_completion,
    list_safe_completion_paths,
)
from vibeagent.cli_interactive import run_interactive_loop


class _FakeReadline:
    __doc__ = "GNU readline test double"

    def __init__(self) -> None:
        self.completer = object()
        self.delimiters = "original"
        self.bindings: list[str] = []

    def get_completer(self):
        return self.completer

    def set_completer(self, completer) -> None:
        self.completer = completer

    def get_completer_delims(self) -> str:
        return self.delimiters

    def set_completer_delims(self, delimiters: str) -> None:
        self.delimiters = delimiters

    def parse_and_bind(self, binding: str) -> None:
        self.bindings.append(binding)


class CliCompletionTests(unittest.TestCase):
    def test_safe_path_index_excludes_ignored_sensitive_and_symlinked_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-completion-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("x\n", encoding="utf-8")
            (root / "empty").mkdir()
            (root / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
            (root / "ignored").mkdir()
            (root / "ignored" / "hidden.py").write_text("x\n", encoding="utf-8")
            (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
            (root / "linked.py").symlink_to(root / "src" / "app.py")

            paths = list_safe_completion_paths(root)

        self.assertIn("src/", paths)
        self.assertIn("src/app.py", paths)
        self.assertIn("empty/", paths)
        self.assertIn(".gitignore", paths)
        self.assertNotIn(".env", paths)
        self.assertFalse(any(path.startswith("ignored/") for path in paths))
        self.assertNotIn("linked.py", paths)

    def test_path_completion_ranks_prefixes_quotes_spaces_and_bounds_results(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-completion-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("x\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "design notes.md").write_text("x\n", encoding="utf-8")
            for index in range(120):
                (root / f"file-{index:03}.py").write_text("x\n", encoding="utf-8")
            completer = InteractivePromptCompleter(root)

            src_matches = completer.matches("@src")
            fuzzy_matches = completer.matches("@app")
            quoted_matches = completer.matches("@design")
            bounded_matches = completer.matches("@file")

        self.assertEqual(src_matches[:2], ("@src/", "@src/app.py"))
        self.assertEqual(fuzzy_matches, ("@src/app.py",))
        self.assertEqual(quoted_matches, ('@"docs/design notes.md"',))
        self.assertEqual(len(bounded_matches), 100)
        self.assertEqual(completer("@src", 0), "@src/")
        self.assertIsNone(completer("@src", len(src_matches)))

    def test_completes_slash_commands_without_treating_ordinary_text_as_special(self) -> None:
        completer = InteractivePromptCompleter(Path.cwd())

        self.assertIn("/session", completer.matches("/sess"))
        self.assertIn("/session-audit", completer.matches("/sess"))
        self.assertEqual(completer.matches("email@example.com"), ())

    def test_added_root_paths_complete_as_absolute_mentions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-completion-") as base:
            root = Path(base) / "project"
            shared = Path(base) / "shared"
            root.mkdir()
            shared.mkdir()
            (shared / "outside.py").write_text("x\n", encoding="utf-8")
            completer = InteractivePromptCompleter(root, (shared,))

            matches = completer.matches("@outside")

        self.assertEqual(matches, (f"@{shared.resolve().as_posix()}/outside.py",))

    def test_completion_context_restores_readline_state(self) -> None:
        fake = _FakeReadline()
        previous_completer = fake.completer
        with patch("vibeagent.cli_completion._terminal_readline", return_value=fake):
            with interactive_prompt_completion(Path.cwd()):
                self.assertIsInstance(fake.completer, InteractivePromptCompleter)
                self.assertEqual(fake.delimiters, " \t\n")
                self.assertEqual(fake.bindings, ["tab: complete"])

        self.assertIs(fake.completer, previous_completer)
        self.assertEqual(fake.delimiters, "original")

    def test_non_terminal_completion_context_is_a_noop(self) -> None:
        with patch("vibeagent.cli_completion._terminal_readline", return_value=None):
            with interactive_prompt_completion(Path.cwd()):
                pass

    def test_path_index_honors_explicit_scan_and_result_limits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-completion-") as base:
            root = Path(base)
            for index in range(10):
                (root / f"file-{index}.py").write_text("x\n", encoding="utf-8")

            result_limited = list_safe_completion_paths(root, max_paths=3)
            scan_limited = list_safe_completion_paths(root, max_scan_entries=2)

        self.assertLessEqual(len(result_limited), 3)
        self.assertLessEqual(len(scan_limited), 2)

    def test_interactive_loop_installs_completion_for_each_prompt(self) -> None:
        completion_context = MagicMock()
        plugin_updates = MagicMock()
        stdout = io.StringIO()
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory(prefix="vibeagent-completion-") as base:
            root = Path(base).resolve()
            try:
                os.chdir(root)
                with (
                    patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                    patch("vibeagent.cli_interactive.create_peer_runtime", return_value=None),
                    patch("vibeagent.cli_interactive.PluginAutoUpdateRuntime", return_value=plugin_updates),
                    patch("vibeagent.cli_interactive.input_with_idle_callback", return_value="/exit"),
                    patch(
                        "vibeagent.cli_interactive.interactive_prompt_completion",
                        return_value=completion_context,
                    ) as install_completion,
                    redirect_stdout(stdout),
                ):
                    exit_code = run_interactive_loop(command_namespace={})
            finally:
                os.chdir(old_cwd)

        self.assertEqual(exit_code, 0)
        self.assertIn(f"VibeAgent {__version__}", stdout.getvalue())
        install_completion.assert_called_once_with(root, ())
        completion_context.__enter__.assert_called_once_with()
        completion_context.__exit__.assert_called_once()
        plugin_updates.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
