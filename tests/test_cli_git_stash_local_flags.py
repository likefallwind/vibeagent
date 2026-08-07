from __future__ import annotations

import argparse
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent import cli_git_local_flags, cli_git_stash_local_flags


class CliGitStashLocalFlagModuleTests(unittest.TestCase):
    def test_git_local_flags_delegates_stash_flags_after_read_and_remote_flags(self) -> None:
        args = argparse.Namespace(git_stash="")
        commands: dict[str, object] = {}
        result = ("Stash:\n  ok: yes", {"gitStash": {"ok": True}})

        with (
            patch("vibeagent.cli_git_local_flags.run_git_read_local_flag", return_value=None) as read_flags,
            patch("vibeagent.cli_git_local_flags.run_git_remote_local_flag", return_value=None) as remote_flags,
            patch("vibeagent.cli_git_local_flags.run_git_stash_local_flag", return_value=result) as stash_flags,
        ):
            self.assertIs(cli_git_local_flags.run_git_local_flag(args, Path("."), commands), result)

        read_flags.assert_called_once_with(args, Path("."), commands)
        remote_flags.assert_called_once_with(args, Path("."), commands)
        stash_flags.assert_called_once_with(args, Path("."), commands)

    def test_git_local_flags_reexports_stash_delegate(self) -> None:
        self.assertIs(
            cli_git_local_flags.run_git_stash_local_flag,
            cli_git_stash_local_flags.run_git_stash_local_flag,
        )


if __name__ == "__main__":
    unittest.main()
