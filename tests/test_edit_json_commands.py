from __future__ import annotations

import unittest

from vibeagent import edit_json_commands, edit_json_patch_commands


class EditJsonCommandsTests(unittest.TestCase):
    def test_json_commands_reexports_patch_helpers(self) -> None:
        self.assertIs(edit_json_commands.get_check_json_patch_text, edit_json_patch_commands.get_check_json_patch_text)
        self.assertIs(edit_json_commands.get_json_patch_report, edit_json_patch_commands.get_json_patch_report)
        self.assertIs(
            edit_json_commands.serialize_json_patch_report,
            edit_json_patch_commands.serialize_json_patch_report,
        )
        self.assertIs(
            edit_json_commands.format_json_patch_report_text,
            edit_json_patch_commands.format_json_patch_report_text,
        )


if __name__ == "__main__":
    unittest.main()
