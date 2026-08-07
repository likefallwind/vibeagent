import unittest

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


if __name__ == "__main__":
    unittest.main()
