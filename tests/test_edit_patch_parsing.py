import io
import unittest
from unittest.mock import patch

from vibeagent import edit_command_parsing
from vibeagent import edit_patch_parsing


class EditPatchParsingTests(unittest.TestCase):
    def test_edit_command_parsing_reexports_patch_parsers(self) -> None:
        self.assertIs(edit_command_parsing.parse_patch_argument, edit_patch_parsing.parse_patch_argument)
        self.assertIs(edit_command_parsing.parse_patches_argument, edit_patch_parsing.parse_patches_argument)
        self.assertIs(edit_command_parsing.read_patch_argument_value, edit_patch_parsing.read_patch_argument_value)

    def test_patch_parsers_keep_existing_behavior(self) -> None:
        self.assertEqual(
            edit_patch_parsing.parse_patch_argument('src/app.py "hello\\n"', usage="/patch <path> <patch>"),
            ("src/app.py", "hello\n"),
        )
        self.assertEqual(
            edit_patch_parsing.parse_patches_argument('"diff --git a/a b/a\\n"', usage="/patches <patch>"),
            "diff --git a/a b/a\n",
        )

    def test_patch_stdin_uses_the_shared_byte_limit(self) -> None:
        with (
            patch("vibeagent.edit_patch_parsing.MAX_STDIN_INPUT_BYTES", 4),
            patch("sys.stdin", io.StringIO("12345")),
            self.assertRaisesRegex(ValueError, "stdin input exceeds the 4 bytes limit"),
        ):
            edit_patch_parsing.read_patch_argument_value("-")


if __name__ == "__main__":
    unittest.main()
