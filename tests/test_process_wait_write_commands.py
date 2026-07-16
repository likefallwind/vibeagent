from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent import process_commands
from vibeagent.process_wait_write_commands import (
    decode_stdin_escapes,
    format_check_write_process_report_text,
    format_wait_process_report_text,
    format_write_process_report_text,
    get_check_write_process_report,
    get_check_write_process_text,
    get_wait_process_report,
    get_wait_process_text,
    get_write_process_report,
    get_write_process_text,
    parse_wait_process_request,
    parse_write_process_request,
    serialize_write_process_report,
)


class ProcessWaitWriteCommandModuleTests(unittest.TestCase):
    def test_process_commands_reexports_wait_write_helpers(self) -> None:
        self.assertIs(process_commands.get_wait_process_report, get_wait_process_report)
        self.assertIs(process_commands.get_wait_process_text, get_wait_process_text)
        self.assertIs(process_commands.format_wait_process_report_text, format_wait_process_report_text)
        self.assertIs(process_commands.get_write_process_report, get_write_process_report)
        self.assertIs(process_commands.get_write_process_text, get_write_process_text)
        self.assertIs(process_commands.format_write_process_report_text, format_write_process_report_text)
        self.assertIs(process_commands.get_check_write_process_report, get_check_write_process_report)
        self.assertIs(process_commands.get_check_write_process_text, get_check_write_process_text)
        self.assertIs(process_commands.format_check_write_process_report_text, format_check_write_process_report_text)
        self.assertIs(process_commands.parse_wait_process_request, parse_wait_process_request)
        self.assertIs(process_commands.parse_write_process_request, parse_write_process_request)
        self.assertIs(process_commands.serialize_write_process_report, serialize_write_process_report)
        self.assertIs(process_commands.decode_stdin_escapes, decode_stdin_escapes)

    def test_decode_stdin_escapes_decodes_process_and_edit_command_content(self) -> None:
        self.assertEqual(decode_stdin_escapes("a\\nb\\tc\\r"), "a\nb\tc\r")

    def test_text_helpers_resolve_compatibility_patch_targets(self) -> None:
        root = Path(".").resolve()
        write_report = {"ok": True, "message": "write"}
        check_report = {"ok": True, "message": "check"}
        with (
            patch("vibeagent.process_commands.get_write_process_report", return_value=write_report) as get_write,
            patch("vibeagent.process_commands.format_write_process_report_text", return_value="write rendered") as format_write,
            patch("vibeagent.process_commands.get_check_write_process_report", return_value=check_report) as get_check,
            patch("vibeagent.process_commands.format_check_write_process_report_text", return_value="check rendered") as format_check,
        ):
            self.assertEqual(get_write_process_text(root, "bg-1 hello\\n"), "write rendered")
            self.assertEqual(get_check_write_process_text(root, "bg-1 hello\\n"), "check rendered")

        get_write.assert_called_once_with(root, "bg-1 hello\\n", None, None)
        format_write.assert_called_once_with(write_report)
        get_check.assert_called_once_with(root, "bg-1 hello\\n", None, None)
        format_check.assert_called_once_with(check_report)

    def test_parse_wait_process_request_preserves_unspecified_max_chars(self) -> None:
        self.assertEqual(parse_wait_process_request("bg-1"), ("bg-1", 5_000, None))
        self.assertEqual(parse_wait_process_request("bg-1 2000 3000"), ("bg-1", 2_000, 3_000))
        self.assertEqual(
            parse_wait_process_request(process_id="bg-1", timeout_ms=1500, max_output_chars=2500),
            ("bg-1", 1_500, 2_500),
        )

    def test_parse_wait_process_request_reports_argument_conflict_before_argument_shape(self) -> None:
        with self.assertRaisesRegex(ValueError, "wait-process argument cannot be combined with explicit process_id"):
            parse_wait_process_request("bg-1 2000 3000 extra", process_id="bg-2")

    def test_parse_write_process_request_unquotes_single_stdin_argument(self) -> None:
        self.assertEqual(parse_write_process_request("bg-1 'hello world\\n'"), ("bg-1", "hello world\n"))
        self.assertEqual(parse_write_process_request("bg-1 hello  world\\n"), ("bg-1", "hello  world\n"))
        self.assertEqual(parse_write_process_request("bg-1 'unterminated"), ("bg-1", "'unterminated"))


if __name__ == "__main__":
    unittest.main()
