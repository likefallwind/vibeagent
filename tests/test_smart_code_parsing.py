from __future__ import annotations

import unittest

from vibeagent import smart_code_commands
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
