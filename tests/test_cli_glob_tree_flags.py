import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliGlobTreeFlagTests(unittest.TestCase):
    def test_main_runs_glob_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_glob_text", return_value="Glob:\n  matches: 1/1") as get_glob_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--glob", "**/*.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Glob:", stdout.getvalue())
        get_glob_text.assert_called_once_with(Path(base).resolve(), "**/*.py")
        create_chat_client.assert_not_called()

    def test_main_runs_glob_local_flag_with_max_matches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_glob_text", return_value="Glob:\n  matches: 1/1") as get_glob_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--glob", "**/*.py", "--glob-max-matches", "4"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Glob:", stdout.getvalue())
        get_glob_text.assert_called_once_with(Path(base).resolve(), "**/*.py", max_matches=4)
        create_chat_client.assert_not_called()

    def test_main_runs_glob_local_flag_with_include_dirs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_glob_text", return_value="Glob:\n  matches: 1/1") as get_glob_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--glob", "src*", "--glob-include-dirs"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Glob:", stdout.getvalue())
        get_glob_text.assert_called_once_with(Path(base).resolve(), "src*", include_dirs=True)
        create_chat_client.assert_not_called()

    def test_main_runs_tree_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_tree_text", return_value="Tree:\n  entries: 1/1") as get_tree_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--tree", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Tree:", stdout.getvalue())
        get_tree_text.assert_called_once_with(Path(base).resolve(), "src")
        create_chat_client.assert_not_called()

    def test_main_runs_tree_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_tree_text", return_value="Tree:\n  entries: 1/1") as get_tree_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--tree", "src", "--tree-max-depth", "2", "--tree-max-entries", "30"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Tree:", stdout.getvalue())
        get_tree_text.assert_called_once_with(Path(base).resolve(), "src", max_depth=2, max_entries=30)
        create_chat_client.assert_not_called()

    def test_main_rejects_glob_tree_bounds_without_matching_local_flag(self) -> None:
        cases = [
            (["--glob-max-matches", "4"], "--glob-max-matches can only be used with --glob."),
            (["--glob-include-dirs"], "--glob-include-dirs can only be used with --glob."),
            (["--tree-max-depth", "2"], "--tree-max-depth can only be used with --tree."),
            (["--tree-max-entries", "30"], "--tree-max-entries can only be used with --tree."),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), f"{expected}\n")
                create_chat_client.assert_not_called()
