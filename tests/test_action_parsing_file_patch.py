import unittest

from vibeagent.action_parsing_file_patch import parse_file_patch_action
from vibeagent.action_parsing_helpers import ActionParseError
from vibeagent.types import CheckPatchAction, CheckPatchesAction, CheckRegexReplaceAction, PatchFileAction, PatchFilesAction, RegexReplaceAction


class ActionParsingFilePatchTests(unittest.TestCase):
    def test_parse_file_patch_action_parses_regex_actions(self) -> None:
        value = {"path": "app.py", "pattern": "old", "replacement": "new", "count": 2, "case_sensitive": False, "multiline": True}

        checked = parse_file_patch_action("check_regex_replace", value, "{}")
        replaced = parse_file_patch_action("regex_replace", value, "{}")

        self.assertEqual(
            checked,
            CheckRegexReplaceAction(
                type="check_regex_replace",
                path="app.py",
                pattern="old",
                replacement="new",
                count=2,
                case_sensitive=False,
                multiline=True,
            ),
        )
        self.assertEqual(replaced.type, "regex_replace")
        self.assertIsInstance(replaced, RegexReplaceAction)

    def test_parse_file_patch_action_parses_patch_actions(self) -> None:
        patch = "@@ -1 +1 @@\n-old\n+new\n"

        checked = parse_file_patch_action("check_patch", {"path": "app.py", "patch": patch}, "{}")
        checked_files = parse_file_patch_action("check_patches", {"patch": patch}, "{}")
        patched = parse_file_patch_action("patch_file", {"path": "app.py", "patch": patch}, "{}")
        patched_files = parse_file_patch_action("patch_files", {"patch": patch}, "{}")

        self.assertEqual(checked, CheckPatchAction(type="check_patch", path="app.py", patch=patch))
        self.assertEqual(checked_files, CheckPatchesAction(type="check_patches", patch=patch))
        self.assertEqual(patched, PatchFileAction(type="patch_file", path="app.py", patch=patch))
        self.assertEqual(patched_files, PatchFilesAction(type="patch_files", patch=patch))

    def test_parse_file_patch_action_returns_none_for_other_actions(self) -> None:
        self.assertIsNone(parse_file_patch_action("write_file", {"path": "app.py"}, "{}"))

    def test_parse_file_patch_action_preserves_validation_errors(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "regex_replace action requires a non-empty string pattern"):
            parse_file_patch_action("regex_replace", {"path": "app.py", "pattern": "", "replacement": "new"}, "{}")

        with self.assertRaisesRegex(ActionParseError, "check_patch action requires a string path"):
            parse_file_patch_action("check_patch", {"patch": "@@ -1 +1 @@\n-a\n+b\n"}, "{}")

        with self.assertRaisesRegex(ActionParseError, "patch_files action requires string patch"):
            parse_file_patch_action("patch_files", {}, "{}")


if __name__ == "__main__":
    unittest.main()
