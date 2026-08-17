from __future__ import annotations

import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from vibeagent.git_read_action_executor import execute_git_read_action
from vibeagent.types import GitBlameAction, GitDiffAction, GitShowAction
from vibeagent.workspace import GitCommandResult, create_run_workspace
from vibeagent.workspace_git_utils import run_readonly_git


class GitReadOutputBoundsTests(unittest.TestCase):
    def test_bounded_git_runner_drains_large_stdout_and_stderr(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-git-output-") as base:
            root = Path(base)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            fake_git = bin_dir / "git"
            fake_git.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "sys.stdout.write('o' * 2_000_000)\n"
                "sys.stderr.write('e' * 1_000_000)\n",
                encoding="utf-8",
            )
            fake_git.chmod(0o755)
            environment = {"PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}

            with patch.dict(os.environ, environment):
                result = run_readonly_git(root, ["large-output"], max_output_chars=1_000)

        self.assertTrue(result.ok)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(len(result.stdout), 1_000)
        self.assertEqual(len(result.stderr), 1_000)
        self.assertTrue(result.stdout_truncated)
        self.assertTrue(result.stderr_truncated)
        self.assertEqual(result.stdout_total_chars, 2_000_000)
        self.assertEqual(result.stderr_total_chars, 1_000_000)
        self.assertIn("[truncated to 1000 chars", result.stdout)
        self.assertIn("[truncated to 1000 chars", result.stderr)

    def test_git_actions_push_their_output_limit_into_git_capture(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-git-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            bounded = GitCommandResult(
                ok=True,
                stdout="bounded output",
                stderr="",
                exit_code=0,
                stdout_truncated=True,
                stdout_total_chars=2_000_000,
            )
            with (
                patch("vibeagent.git_read_action_executor.read_git_diff", return_value=bounded) as read_diff,
                patch("vibeagent.git_read_action_executor.read_git_show", return_value=bounded) as read_show,
                patch("vibeagent.git_read_action_executor.read_git_blame", return_value=bounded) as read_blame,
            ):
                diff = execute_git_read_action(
                    workspace,
                    GitDiffAction(type="git_diff", path="app.py", max_output_chars=1_000),
                )
                show = execute_git_read_action(
                    workspace,
                    GitShowAction(type="git_show", rev="HEAD", path="app.py", max_output_chars=2_000),
                )
                blame = execute_git_read_action(
                    workspace,
                    GitBlameAction(type="git_blame", path="app.py", max_output_chars=3_000),
                )

        read_diff.assert_called_once_with(workspace, "app.py", False, max_output_chars=1_000)
        read_show.assert_called_once_with(workspace, "HEAD", "app.py", max_output_chars=2_000)
        read_blame.assert_called_once_with(workspace, "app.py", None, None, max_output_chars=3_000)
        self.assertTrue(diff.truncated)
        self.assertTrue(show.truncated)
        self.assertTrue(blame.truncated)

    def test_bounded_git_runner_terminates_on_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-git-timeout-") as base:
            root = Path(base)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            fake_git = bin_dir / "git"
            fake_git.write_text(
                "#!/usr/bin/env python3\n"
                "import time\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )
            fake_git.chmod(0o755)
            environment = {"PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}
            started = time.monotonic()

            with (
                patch.dict(os.environ, environment),
                patch("vibeagent.workspace_git_utils.READONLY_GIT_TIMEOUT_MS", 50),
            ):
                result = run_readonly_git(root, ["hang"], max_output_chars=1_000)

        self.assertLess(time.monotonic() - started, 2)
        self.assertFalse(result.ok)
        self.assertIsNone(result.exit_code)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "git command timed out.")


if __name__ == "__main__":
    unittest.main()
