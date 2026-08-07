from __future__ import annotations

import argparse
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent import cli_git_local_flags, cli_git_remote_local_flags


class CliGitRemoteLocalFlagModuleTests(unittest.TestCase):
    def test_git_local_flags_delegates_remote_git_flags_after_read_flags(self) -> None:
        args = argparse.Namespace(check_git_fetch="origin")
        commands: dict[str, object] = {}
        result = ("Check fetch:\n  ok: yes", {"checkGitFetch": {"ok": True}})

        with (
            patch("vibeagent.cli_git_local_flags.run_git_read_local_flag", return_value=None) as read_flags,
            patch("vibeagent.cli_git_local_flags.run_git_remote_local_flag", return_value=result) as remote_flags,
        ):
            self.assertIs(cli_git_local_flags.run_git_local_flag(args, Path("."), commands), result)

        read_flags.assert_called_once_with(args, Path("."), commands)
        remote_flags.assert_called_once_with(args, Path("."), commands)

    def test_git_local_flags_reexports_remote_delegate(self) -> None:
        self.assertIs(
            cli_git_local_flags.run_git_remote_local_flag,
            cli_git_remote_local_flags.run_git_remote_local_flag,
        )


if __name__ == "__main__":
    unittest.main()
