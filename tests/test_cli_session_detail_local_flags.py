from __future__ import annotations

import argparse
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent import cli_session_detail_local_flags, cli_session_local_flags


class CliSessionDetailLocalFlagModuleTests(unittest.TestCase):
    def test_session_local_flags_delegates_detail_flags(self) -> None:
        args = argparse.Namespace(sessions=False, session_commands="run-1")
        commands: dict[str, object] = {}
        result = ("Command results:\n  session: run-1", {"sessionCommands": {"ok": True}})

        with (
            patch("vibeagent.cli_session_local_flags.run_session_summary_local_flag", return_value=None),
            patch("vibeagent.cli_session_local_flags.run_session_detail_local_flag", return_value=result) as detail,
        ):
            self.assertIs(cli_session_local_flags.run_session_local_flag(args, Path("."), commands), result)

        detail.assert_called_once_with(args, Path("."), commands)

    def test_session_local_flags_reexports_detail_specs_and_helper(self) -> None:
        self.assertIs(
            cli_session_local_flags.SESSION_DETAIL_COMMAND_SPECS,
            cli_session_detail_local_flags.SESSION_DETAIL_COMMAND_SPECS,
        )
        self.assertIs(
            cli_session_local_flags._interactive_session_detail_text,
            cli_session_detail_local_flags.interactive_session_detail_text,
        )


if __name__ == "__main__":
    unittest.main()
