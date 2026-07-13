from __future__ import annotations

import unittest

from vibeagent import edit_command_parsing, edit_json_parsing


class EditJsonParsingTests(unittest.TestCase):
    def test_edit_command_parsing_reexports_json_parsers(self) -> None:
        self.assertIs(edit_command_parsing.parse_json_set_argument, edit_json_parsing.parse_json_set_argument)
        self.assertIs(edit_command_parsing.parse_json_remove_argument, edit_json_parsing.parse_json_remove_argument)
        self.assertIs(edit_command_parsing.parse_json_patch_argument, edit_json_parsing.parse_json_patch_argument)
        self.assertIs(edit_command_parsing.parse_json_patch_operations, edit_json_parsing.parse_json_patch_operations)


if __name__ == "__main__":
    unittest.main()
