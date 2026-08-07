from __future__ import annotations

import argparse
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent import cli_session_local_flags, cli_session_summary_local_flags


class CliSessionSummaryLocalFlagModuleTests(unittest.TestCase):
    def test_session_local_flags_delegates_summary_flags(self) -> None:
        args = argparse.Namespace(sessions=True)
        commands: dict[str, object] = {}
        result = ("Sessions:\n  total: 1", {"sessions": {"ok": True}})

        with patch("vibeagent.cli_session_local_flags.run_session_summary_local_flag", return_value=result) as summary:
            self.assertIs(cli_session_local_flags.run_session_local_flag(args, Path("."), commands), result)

        summary.assert_called_once_with(args, Path("."), commands)

    def test_session_local_flags_reexports_summary_delegate_and_query_normalizer(self) -> None:
        self.assertIs(
            cli_session_local_flags.run_session_summary_local_flag,
            cli_session_summary_local_flags.run_session_summary_local_flag,
        )
        self.assertIs(
            cli_session_local_flags._normalize_session_search_query,
            cli_session_summary_local_flags.normalize_session_search_query,
        )


if __name__ == "__main__":
    unittest.main()
