from __future__ import annotations

import argparse
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent import cli_git_local_flags, cli_git_worktree_local_flags


class CliGitWorktreeLocalFlagModuleTests(unittest.TestCase):
    def test_git_local_flags_delegates_worktree_flags_after_prior_git_groups(self) -> None:
        args = argparse.Namespace(git_stage=["app.py"])
        commands: dict[str, object] = {}
        result = ("Stage:\n  ok: yes", {"gitStage": {"ok": True}})

        with (
            patch("vibeagent.cli_git_local_flags.run_git_read_local_flag", return_value=None) as read_flags,
            patch("vibeagent.cli_git_local_flags.run_git_remote_local_flag", return_value=None) as remote_flags,
            patch("vibeagent.cli_git_local_flags.run_git_stash_local_flag", return_value=None) as stash_flags,
            patch("vibeagent.cli_git_local_flags.run_git_worktree_local_flag", return_value=result) as worktree_flags,
        ):
            self.assertIs(cli_git_local_flags.run_git_local_flag(args, Path("."), commands), result)

        read_flags.assert_called_once_with(args, Path("."), commands)
        remote_flags.assert_called_once_with(args, Path("."), commands)
        stash_flags.assert_called_once_with(args, Path("."), commands)
        worktree_flags.assert_called_once_with(args, Path("."), commands)

    def test_git_local_flags_reexports_worktree_delegate(self) -> None:
        self.assertIs(
            cli_git_local_flags.run_git_worktree_local_flag,
            cli_git_worktree_local_flags.run_git_worktree_local_flag,
        )


if __name__ == "__main__":
    unittest.main()
