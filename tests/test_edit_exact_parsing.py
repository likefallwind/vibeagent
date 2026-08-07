import unittest

from vibeagent import edit_command_parsing
from vibeagent import edit_exact_parsing


class EditExactParsingTests(unittest.TestCase):
    def test_edit_command_parsing_reexports_exact_parsers(self) -> None:
        self.assertIs(edit_command_parsing.parse_edit_file_argument, edit_exact_parsing.parse_edit_file_argument)
        self.assertIs(edit_command_parsing.parse_multi_edit_file_argument, edit_exact_parsing.parse_multi_edit_file_argument)

    def test_exact_parsers_keep_existing_behavior(self) -> None:
        self.assertEqual(
            edit_exact_parsing.parse_edit_file_argument(
                'src/app.py "old\\n" "new\\n"',
                usage="/edit <path> <old> <new>",
            ),
            ("src/app.py", "old\n", "new\n"),
        )
        parsed_path, edits = edit_exact_parsing.parse_multi_edit_file_argument(
            'src/app.py "one" "two" "three" "four"',
            usage="/multi-edit <path> <old> <new>...",
        )
        self.assertEqual(parsed_path, "src/app.py")
        self.assertEqual([(edit.old, edit.new) for edit in edits], [("one", "two"), ("three", "four")])


if __name__ == "__main__":
    unittest.main()
