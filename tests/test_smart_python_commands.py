from __future__ import annotations

import unittest

from vibeagent import smart_code_commands, smart_python_commands, smart_python_symbols


class SmartPythonCommandsTests(unittest.TestCase):
    def test_smart_code_commands_keeps_python_command_exports(self) -> None:
        self.assertIs(smart_code_commands.get_python_check_report, smart_python_commands.get_python_check_report)
        self.assertIs(smart_code_commands.get_python_check_text, smart_python_commands.get_python_check_text)
        self.assertIs(smart_code_commands.format_python_check_report_text, smart_python_commands.format_python_check_report_text)
        self.assertIs(smart_code_commands.get_python_deps_report, smart_python_commands.get_python_deps_report)
        self.assertIs(smart_code_commands.get_python_defs_report, smart_python_commands.get_python_defs_report)
        self.assertIs(smart_code_commands.get_python_refs_report, smart_python_commands.get_python_refs_report)
        self.assertIs(smart_code_commands.get_python_ref_contexts_report, smart_python_commands.get_python_ref_contexts_report)
        self.assertIs(smart_code_commands.get_python_calls_report, smart_python_commands.get_python_calls_report)
        self.assertIs(smart_code_commands.get_python_call_graph_report, smart_python_commands.get_python_call_graph_report)
        self.assertIs(smart_code_commands.get_python_rename_preview_report, smart_python_commands.get_python_rename_preview_report)
        self.assertIs(smart_code_commands.get_python_rename_report, smart_python_commands.get_python_rename_report)
        self.assertIs(
            smart_code_commands.get_check_replace_python_definition_report,
            smart_python_commands.get_check_replace_python_definition_report,
        )
        self.assertIs(
            smart_code_commands.get_replace_python_definition_report,
            smart_python_commands.get_replace_python_definition_report,
        )

    def test_smart_python_commands_reexports_symbol_commands(self) -> None:
        names = [
            "get_python_defs_report",
            "format_python_defs_report_text",
            "get_python_refs_report",
            "format_python_refs_report_text",
            "get_python_ref_contexts_report",
            "format_python_ref_contexts_report_text",
            "get_python_calls_report",
            "format_python_calls_report_text",
            "get_python_call_graph_report",
            "format_python_call_graph_report_text",
            "get_python_defs_text",
            "get_python_refs_text",
            "get_python_ref_contexts_text",
            "get_python_calls_text",
            "get_python_call_graph_text",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(smart_python_commands, name), getattr(smart_python_symbols, name))


if __name__ == "__main__":
    unittest.main()
