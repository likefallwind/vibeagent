import unittest

from vibeagent import edit_command_parsing
from vibeagent import edit_regex_parsing


class EditRegexParsingTests(unittest.TestCase):
    def test_edit_command_parsing_reexports_regex_parsers(self) -> None:
        self.assertIs(edit_command_parsing.parse_regex_replace_argument, edit_regex_parsing.parse_regex_replace_argument)
        self.assertIs(edit_command_parsing.validate_nonnegative_int, edit_regex_parsing.validate_nonnegative_int)
        self.assertIs(edit_command_parsing.validate_positive_int, edit_regex_parsing.validate_positive_int)

    def test_regex_parser_keeps_existing_behavior(self) -> None:
        self.assertEqual(
            edit_regex_parsing.parse_regex_replace_argument(
                'src/app.py "old" "new\\n" --ignore-case --multiline --count 2 --max-replacements 5',
                usage="/regex <path> <pattern> <replacement>",
            ),
            {
                "path": "src/app.py",
                "pattern": "old",
                "replacement": "new\n",
                "count": 2,
                "case_sensitive": False,
                "multiline": True,
                "max_replacements": 5,
            },
        )


if __name__ == "__main__":
    unittest.main()
