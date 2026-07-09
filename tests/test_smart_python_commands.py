from __future__ import annotations

import unittest
from unittest.mock import patch

from vibeagent import smart_code_commands, smart_python_call_commands, smart_python_check_commands, smart_python_commands, smart_python_edit_commands, smart_python_symbols


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

    def test_smart_python_symbols_reexports_call_commands(self) -> None:
        names = [
            "get_python_calls_report",
            "format_python_calls_report_text",
            "get_python_calls_text",
            "get_python_call_graph_report",
            "format_python_call_graph_report_text",
            "get_python_call_graph_text",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(smart_python_symbols, name), getattr(smart_python_call_commands, name))

    def test_smart_python_commands_reexports_check_commands(self) -> None:
        names = [
            "get_python_check_report",
            "format_python_check_report_text",
            "get_python_check_text",
            "get_python_deps_report",
            "format_python_deps_report_text",
            "get_python_deps_text",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(smart_python_commands, name), getattr(smart_python_check_commands, name))

    def test_smart_python_commands_reexports_edit_commands(self) -> None:
        names = [
            "get_python_rename_preview_text",
            "get_python_rename_preview_report",
            "get_python_rename_text",
            "get_python_rename_report",
            "get_check_replace_python_definition_text",
            "get_check_replace_python_definition_report",
            "get_replace_python_definition_text",
            "get_replace_python_definition_report",
            "format_replace_python_definition_report_text",
            "format_replace_python_definition_observation",
            "format_python_rename_report_text",
            "format_python_rename_observation",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(smart_python_commands, name), getattr(smart_python_edit_commands, name))

    def test_smart_python_check_text_helpers_resolve_compatibility_patch_targets(self) -> None:
        check_report = {"message": "patched check"}
        deps_report = {"message": "patched deps"}
        root = "/tmp/project"
        with (
            patch("vibeagent.commands.get_python_check_report", return_value=check_report) as get_check,
            patch("vibeagent.commands.format_python_check_report_text", return_value="check text") as format_check,
            patch("vibeagent.commands.get_python_deps_report", return_value=deps_report) as get_deps,
            patch("vibeagent.commands.format_python_deps_report_text", return_value="deps text") as format_deps,
        ):
            self.assertEqual(smart_python_check_commands.get_python_check_text(root, "src", max_files=7), "check text")
            self.assertEqual(
                smart_python_check_commands.get_python_deps_text(root, "pkg", max_files=11, max_imports=13),
                "deps text",
            )
        get_check.assert_called_once_with(root, "src", max_files=7)
        format_check.assert_called_once_with(check_report)
        get_deps.assert_called_once_with(root, "pkg", max_files=11, max_imports=13)
        format_deps.assert_called_once_with(deps_report)

    def test_smart_python_call_text_helpers_resolve_compatibility_patch_targets(self) -> None:
        calls_report = {"message": "patched calls"}
        graph_report = {"message": "patched graph"}
        root = "/tmp/project"
        with (
            patch("vibeagent.commands.get_python_calls_report", return_value=calls_report) as get_calls,
            patch("vibeagent.commands.format_python_calls_report_text", return_value="calls text") as format_calls,
            patch("vibeagent.commands.get_python_call_graph_report", return_value=graph_report) as get_graph,
            patch("vibeagent.commands.format_python_call_graph_report_text", return_value="graph text") as format_graph,
        ):
            self.assertEqual(smart_python_call_commands.get_python_calls_text(root, "run src", max_matches=7), "calls text")
            self.assertEqual(smart_python_call_commands.get_python_call_graph_text(root, "src", max_files=11, max_edges=13), "graph text")
        get_calls.assert_called_once_with(root, argument="run src", symbol=None, path=None, max_matches=7)
        format_calls.assert_called_once_with(calls_report)
        get_graph.assert_called_once_with(root, "src", max_files=11, max_edges=13)
        format_graph.assert_called_once_with(graph_report)


if __name__ == "__main__":
    unittest.main()
