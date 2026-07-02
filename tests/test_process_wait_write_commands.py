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


if __name__ == "__main__":
    unittest.main()
