import unittest

from vibeagent import edit_command_parsing, edit_write_parsing


class EditWriteParsingTests(unittest.TestCase):
    def test_edit_command_parsing_reexports_write_parsers(self) -> None:
        self.assertIs(edit_command_parsing.parse_write_file_argument, edit_write_parsing.parse_write_file_argument)
        self.assertIs(edit_command_parsing.parse_write_file_list_argument, edit_write_parsing.parse_write_file_list_argument)

    def test_write_parsers_keep_existing_behavior(self) -> None:
        self.assertEqual(
            edit_write_parsing.parse_write_file_argument('src/app.py "hello\\n"', usage="/write <path> <text>"),
            ("src/app.py", "hello\n"),
        )
        files = edit_write_parsing.parse_write_file_list_argument(
            'a.txt "one" b.txt "two\\n"',
            usage="/write-files <path> <text>...",
        )
        self.assertEqual([(file.path, file.content) for file in files], [("a.txt", "one"), ("b.txt", "two\n")])


if __name__ == "__main__":
    unittest.main()
