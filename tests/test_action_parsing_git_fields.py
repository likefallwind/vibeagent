from __future__ import annotations

import unittest

from vibeagent import action_parsing_git
from vibeagent import action_parsing_git_fields
from vibeagent.action_parsing_helpers import ActionParseError


class ActionParsingGitFieldsTests(unittest.TestCase):
    def test_git_parser_reexports_field_helpers(self) -> None:
        self.assertIs(action_parsing_git.parse_git_path_list, action_parsing_git_fields.parse_git_path_list)
        self.assertIs(action_parsing_git.parse_optional_git_remote, action_parsing_git_fields.parse_optional_git_remote)
        self.assertIs(action_parsing_git.parse_git_branch_create, action_parsing_git_fields.parse_git_branch_create)
        self.assertIs(action_parsing_git.parse_git_stash_options, action_parsing_git_fields.parse_git_stash_options)
        self.assertIs(action_parsing_git.parse_git_stash_ref, action_parsing_git_fields.parse_git_stash_ref)
        self.assertIs(action_parsing_git.parse_git_commit_message, action_parsing_git_fields.parse_git_commit_message)

    def test_git_field_helpers_normalize_valid_inputs(self) -> None:
        self.assertEqual(action_parsing_git_fields.parse_optional_git_remote({"remote": " origin "}, "{}", "git_fetch"), "origin")
        self.assertEqual(action_parsing_git_fields.parse_git_branch_create({"branch": " main ", "create": True}, "{}", "git_switch"), ("main", True))
        self.assertEqual(action_parsing_git_fields.parse_git_stash_ref({"stash_ref": " stash@{0} "}, "{}", "git_stash_apply"), "stash@{0}")
        self.assertEqual(action_parsing_git_fields.parse_git_commit_message({"message": " fix "}, "{}", "git_commit"), "fix")

    def test_git_field_helpers_keep_error_messages_action_specific(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "git_fetch action remote must be non-empty"):
            action_parsing_git_fields.parse_optional_git_remote({"remote": ""}, "{}", "git_fetch")
        with self.assertRaisesRegex(ActionParseError, "git_switch action create must be a boolean"):
            action_parsing_git_fields.parse_git_branch_create({"branch": "main", "create": "yes"}, "{}", "git_switch")
        with self.assertRaisesRegex(ActionParseError, "git_stash action include_untracked must be a boolean"):
            action_parsing_git_fields.parse_git_stash_options({"include_untracked": "yes"}, "{}", "git_stash")
        with self.assertRaisesRegex(ActionParseError, "git_commit action requires a non-empty string message"):
            action_parsing_git_fields.parse_git_commit_message({"message": ""}, "{}", "git_commit")


if __name__ == "__main__":
    unittest.main()
