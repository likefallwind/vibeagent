from __future__ import annotations

import unittest
from unittest.mock import patch

from vibeagent import smart_code_commands, smart_code_symbol_commands
from vibeagent.smart_code_formatting import (
    format_code_defs_report_text,
    format_code_deps_report_text,
    format_code_ref_contexts_report_text,
    format_code_refs_report_text,
)
from vibeagent.smart_code_parsing import (
    parse_rename_argument,
    parse_replace_python_definition_argument,
    parse_symbol_path_argument,
)


class SmartCodeParsingTests(unittest.TestCase):
    def test_smart_code_commands_reexports_parsers(self) -> None:
        self.assertIs(smart_code_commands.parse_symbol_path_argument, parse_symbol_path_argument)
        self.assertIs(smart_code_commands.parse_rename_argument, parse_rename_argument)
        self.assertIs(smart_code_commands.parse_replace_python_definition_argument, parse_replace_python_definition_argument)

    def test_smart_code_commands_reexports_code_formatters(self) -> None:
        self.assertIs(smart_code_commands.format_code_deps_report_text, format_code_deps_report_text)
        self.assertIs(smart_code_commands.format_code_refs_report_text, format_code_refs_report_text)
        self.assertIs(smart_code_commands.format_code_ref_contexts_report_text, format_code_ref_contexts_report_text)
        self.assertIs(smart_code_commands.format_code_defs_report_text, format_code_defs_report_text)

    def test_smart_code_commands_reexports_symbol_commands(self) -> None:
        names = [
            "get_code_deps_report",
            "get_code_deps_text",
            "get_code_refs_report",
            "get_code_refs_text",
            "get_code_ref_contexts_report",
            "get_code_ref_contexts_text",
            "get_code_defs_report",
            "get_code_defs_text",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(smart_code_commands, name), getattr(smart_code_symbol_commands, name))

    def test_smart_code_symbol_text_helpers_resolve_compatibility_patch_targets(self) -> None:
        deps_report = {"message": "patched deps"}
        refs_report = {"message": "patched refs"}
        contexts_report = {"message": "patched contexts"}
        defs_report = {"message": "patched defs"}
        root = "/tmp/project"
        with (
            patch("vibeagent.commands.get_code_deps_report", return_value=deps_report) as get_deps,
            patch("vibeagent.commands.format_code_deps_report_text", return_value="deps text") as format_deps,
            patch("vibeagent.commands.get_code_refs_report", return_value=refs_report) as get_refs,
            patch("vibeagent.commands.format_code_refs_report_text", return_value="refs text") as format_refs,
            patch("vibeagent.commands.get_code_ref_contexts_report", return_value=contexts_report) as get_contexts,
            patch("vibeagent.commands.format_code_ref_contexts_report_text", return_value="contexts text") as format_contexts,
            patch("vibeagent.commands.get_code_defs_report", return_value=defs_report) as get_defs,
            patch("vibeagent.commands.format_code_defs_report_text", return_value="defs text") as format_defs,
        ):
            self.assertEqual(smart_code_symbol_commands.get_code_deps_text(root, "web", max_files=7, max_imports=11), "deps text")
            self.assertEqual(smart_code_symbol_commands.get_code_refs_text(root, "run web", max_matches=13), "refs text")
            self.assertEqual(
                smart_code_symbol_commands.get_code_ref_contexts_text(root, "run web", max_matches=17, context_lines=2, max_bytes_per_context=19),
                "contexts text",
            )
            self.assertEqual(smart_code_symbol_commands.get_code_defs_text(root, "run web", max_matches=23, max_lines=29), "defs text")

        get_deps.assert_called_once_with(root, "web", max_files=7, max_imports=11)
        format_deps.assert_called_once_with(deps_report)
        get_refs.assert_called_once_with(root, argument="run web", symbol=None, path=None, max_matches=13)
        format_refs.assert_called_once_with(refs_report)
        get_contexts.assert_called_once_with(
            root,
            argument="run web",
            symbol=None,
            path=None,
            max_matches=17,
            context_lines=2,
            max_bytes_per_context=19,
        )
        format_contexts.assert_called_once_with(contexts_report)
        get_defs.assert_called_once_with(root, argument="run web", symbol=None, path=None, max_matches=23, max_lines=29)
        format_defs.assert_called_once_with(defs_report)

    def test_parse_symbol_path_argument_accepts_flags_and_shell_text(self) -> None:
        self.assertEqual(
            parse_symbol_path_argument("runAgent web/src", usage="/code-refs <symbol> [path]"),
            ("runAgent", "web/src"),
        )
        self.assertEqual(
            parse_symbol_path_argument(None, symbol=" runAgent ", path=" web/src ", usage="/code-refs <symbol> [path]"),
            ("runAgent", "web/src"),
        )

    def test_parse_rename_argument_validates_required_pairs(self) -> None:
        self.assertEqual(
            parse_rename_argument("runAgent executeAgent web", usage="/code-rename <symbol> <new_name> [path]"),
            ("runAgent", "executeAgent", "web"),
        )
        with self.assertRaisesRegex(ValueError, "requires both symbol and new_name"):
            parse_rename_argument(None, symbol="runAgent", usage="/code-rename <symbol> <new_name> [path]")

    def test_parse_replace_python_definition_decodes_escaped_content(self) -> None:
        self.assertEqual(
            parse_replace_python_definition_argument(
                "Runner.run '    def run(self):\\n        return 2\\n' src",
                usage="/replace-python-def <symbol> <content> [path]",
            ),
            ("Runner.run", "    def run(self):\n        return 2\n", "src"),
        )
        with self.assertRaisesRegex(ValueError, "requires non-empty content"):
            parse_replace_python_definition_argument(
                None,
                symbol="Runner.run",
                content="   ",
                usage="/replace-python-def <symbol> <content> [path]",
            )


if __name__ == "__main__":
    unittest.main()
