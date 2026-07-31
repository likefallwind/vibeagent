from __future__ import annotations

import unittest

import vibeagent.agent_approval_preview_stale as stale


class ApprovalPreviewStaleTests(unittest.TestCase):
    def test_workspace_restore_invalidates_workspace_previews(self) -> None:
        self.assertTrue(stale.preview_invalidated_by_workspace_restore("check_edit_file", "checkpoint_restore"))
        self.assertTrue(stale.preview_invalidated_by_workspace_restore("check_git_push", "checkpoint_restore"))
        self.assertFalse(stale.preview_invalidated_by_workspace_restore("check_write_process", "checkpoint_restore"))

    def test_checkpoint_restore_preview_invalidated_by_any_workspace_mutation(self) -> None:
        for mutation_kind in stale.WORKSPACE_MUTATION_OBSERVATION_KINDS:
            with self.subTest(mutation_kind=mutation_kind):
                self.assertTrue(
                    stale.checkpoint_restore_preview_invalidated_by_workspace_mutation(
                        "check_checkpoint_restore",
                        mutation_kind,
                    )
                )

    def test_git_preview_invalidated_by_workspace_mutations(self) -> None:
        mutation_kinds = (
            stale.GIT_MUTATION_OBSERVATION_KINDS
            | stale.FILE_MUTATION_OBSERVATION_KINDS
            | stale.COMMAND_MUTATION_OBSERVATION_KINDS
        )
        for mutation_kind in mutation_kinds:
            with self.subTest(mutation_kind=mutation_kind):
                self.assertTrue(stale.git_preview_invalidated_by_workspace_mutation("check_git_push", mutation_kind))
        self.assertFalse(stale.git_preview_invalidated_by_workspace_mutation("check_write_file", "git_stage"))

    def test_file_preview_invalidated_by_broad_workspace_mutations(self) -> None:
        mutation_kinds = stale.GIT_MUTATION_OBSERVATION_KINDS | stale.COMMAND_MUTATION_OBSERVATION_KINDS
        for mutation_kind in mutation_kinds:
            with self.subTest(mutation_kind=mutation_kind):
                self.assertTrue(
                    stale.file_preview_invalidated_by_broad_workspace_mutation("check_edit_file", mutation_kind)
                )
        self.assertFalse(stale.file_preview_invalidated_by_broad_workspace_mutation("check_edit_file", "write_file"))

    def test_command_execution_approval_actions_are_workspace_mutation_tracked(self) -> None:
        command_execution_actions = {
            "run_command",
            "run_commands",
            "run_suggested_checks",
            "run_focused_test_commands",
            "run_session_verification",
            "start_command",
            "write_process",
        }
        self.assertEqual(sorted(command_execution_actions - stale.COMMAND_MUTATION_OBSERVATION_KINDS), [])

    def test_command_execution_previews_are_workspace_stale_tracked(self) -> None:
        command_execution_previews = {
            "command_check",
            "check_run_commands",
            "check_suggested_checks",
            "check_focused_test_commands",
            "session_verification",
            "check_start_command",
        }
        self.assertEqual(sorted(command_execution_previews - stale.COMMAND_PREVIEW_KINDS), [])

    def test_process_control_previews_are_process_stale_tracked(self) -> None:
        process_control_previews = {
            "check_write_process",
            "check_stop_process",
            "check_stop_all_processes",
        }
        self.assertEqual(sorted(process_control_previews - stale.PROCESS_PREVIEW_KINDS), [])

    def test_process_preview_invalidated_by_process_state(self) -> None:
        for observation_kind in stale.PROCESS_STATE_OBSERVATION_KINDS:
            with self.subTest(observation_kind=observation_kind):
                self.assertTrue(stale.process_preview_invalidated_by_process_state("check_stop_process", observation_kind))
        self.assertFalse(stale.process_preview_invalidated_by_process_state("check_stop_process", "write_file"))


if __name__ == "__main__":
    unittest.main()
