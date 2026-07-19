import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from vibeagent.cli import main


class CliDiffLimitErrorTests(unittest.TestCase):
    def test_main_reports_diff_max_chars_without_diff_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--diff-max-chars", "2000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--diff-max-chars can only be used with --diff.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_changes_max_files_without_changes_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--changes-max-files", "1", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--changes-max-files can only be used with --changes.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_review_limits_without_review_as_local_flag_errors(self) -> None:
        cases = [
            (["--review-max-files", "1", "fix", "tests"], "--review-max-files can only be used with --review.\n"),
            (["--review-max-checks", "1", "fix", "tests"], "--review-max-checks can only be used with --review.\n"),
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
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_handoff_limits_without_handoff_as_local_flag_errors(self) -> None:
        cases = [
            (["--handoff-max-files", "1", "fix", "tests"], "--handoff-max-files can only be used with --handoff.\n"),
            (["--handoff-max-checks", "1", "fix", "tests"], "--handoff-max-checks can only be used with --handoff.\n"),
            (["--handoff-max-status-chars", "1000", "fix", "tests"], "--handoff-max-status-chars can only be used with --handoff.\n"),
            (["--handoff-max-plan-chars", "1000", "fix", "tests"], "--handoff-max-plan-chars can only be used with --handoff.\n"),
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
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_structured_diff_limits_without_matching_diff_flag_as_local_flag_errors(self) -> None:
        cases = [
            (["--diff-hunks-max-hunks", "2", "fix"], "--diff-hunks-max-hunks can only be used with --diff-hunks.\n"),
            (["--diff-hunks-max-lines", "2", "fix"], "--diff-hunks-max-lines can only be used with --diff-hunks.\n"),
            (["--diff-context-lines", "2", "fix"], "--diff-context-lines can only be used with --diff-contexts.\n"),
            (["--diff-contexts-max-hunks", "2", "fix"], "--diff-contexts-max-hunks can only be used with --diff-contexts.\n"),
            (["--diff-contexts-max-bytes", "1000", "fix"], "--diff-contexts-max-bytes can only be used with --diff-contexts.\n"),
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
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()
