from __future__ import annotations

import unittest

from vibeagent import process_commands
from vibeagent.process_stop_commands import (
    format_check_stop_all_processes_report_text,
    format_check_stop_process_report_text,
    format_stop_all_processes_report_text,
    format_stop_process_report_text,
    get_check_stop_all_processes_report,
    get_check_stop_all_processes_text,
    get_check_stop_process_report,
    get_check_stop_process_text,
    get_stop_all_processes_report,
    get_stop_all_processes_text,
    get_stop_process_report,
    get_stop_process_text,
    serialize_stopped_process_info,
)


class ProcessStopCommandModuleTests(unittest.TestCase):
    def test_process_commands_reexports_stop_helpers(self) -> None:
        self.assertIs(process_commands.get_check_stop_process_report, get_check_stop_process_report)
        self.assertIs(process_commands.get_check_stop_process_text, get_check_stop_process_text)
        self.assertIs(process_commands.format_check_stop_process_report_text, format_check_stop_process_report_text)
        self.assertIs(process_commands.get_stop_process_report, get_stop_process_report)
        self.assertIs(process_commands.get_stop_process_text, get_stop_process_text)
        self.assertIs(process_commands.format_stop_process_report_text, format_stop_process_report_text)
        self.assertIs(process_commands.get_check_stop_all_processes_report, get_check_stop_all_processes_report)
        self.assertIs(process_commands.get_check_stop_all_processes_text, get_check_stop_all_processes_text)
        self.assertIs(process_commands.format_check_stop_all_processes_report_text, format_check_stop_all_processes_report_text)
        self.assertIs(process_commands.get_stop_all_processes_report, get_stop_all_processes_report)
        self.assertIs(process_commands.get_stop_all_processes_text, get_stop_all_processes_text)
        self.assertIs(process_commands.format_stop_all_processes_report_text, format_stop_all_processes_report_text)
        self.assertIs(process_commands.serialize_stopped_process_info, serialize_stopped_process_info)


if __name__ == "__main__":
    unittest.main()
