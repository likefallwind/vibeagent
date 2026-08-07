import unittest

from vibeagent import edit_command_parsing
from vibeagent import edit_line_parsing


class EditLineParsingTests(unittest.TestCase):
    def test_edit_command_parsing_reexports_line_parsers(self) -> None:
        names = [
            "parse_replace_lines_argument",
            "parse_insert_lines_argument",
            "parse_append_file_argument",
            "parse_line_number",
            "validate_line_number",
            "validate_line_range",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(edit_command_parsing, name), getattr(edit_line_parsing, name))

    def test_line_parsers_keep_existing_behavior(self) -> None:
        self.assertEqual(
            edit_line_parsing.parse_replace_lines_argument(
                'src/app.py 2 3 "hello\\n"',
                usage="/replace-lines <path> <start> <end> <text>",
            ),
            ("src/app.py", 2, 3, "hello\n"),
        )
        self.assertEqual(
            edit_line_parsing.parse_insert_lines_argument(
                'src/app.py 4 "inserted\\n"',
                usage="/insert-lines <path> <line> <text>",
            ),
            ("src/app.py", 4, "inserted\n"),
        )
        self.assertEqual(
            edit_line_parsing.parse_append_file_argument(
                'src/app.py "tail\\n"',
                usage="/append <path> <text>",
            ),
            ("src/app.py", "tail\n"),
        )


if __name__ == "__main__":
    unittest.main()
