from __future__ import annotations

import argparse
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent import cli_git_local_flags, cli_git_read_local_flags


class CliGitReadLocalFlagModuleTests(unittest.TestCase):
    def test_git_local_flags_delegates_read_only_git_flags(self) -> None:
        args = argparse.Namespace(git_status=True)
        commands: dict[str, object] = {}
        result = ("Git status:\n  ok: yes", {"gitStatus": {"ok": True}})

        with patch("vibeagent.cli_git_local_flags.run_git_read_local_flag", return_value=result) as read_flags:
            self.assertIs(cli_git_local_flags.run_git_local_flag(args, Path("."), commands), result)

        read_flags.assert_called_once_with(args, Path("."), commands)

    def test_git_read_local_flags_exports_delegate(self) -> None:
        self.assertIs(cli_git_local_flags.run_git_read_local_flag, cli_git_read_local_flags.run_git_read_local_flag)


if __name__ == "__main__":
    unittest.main()
