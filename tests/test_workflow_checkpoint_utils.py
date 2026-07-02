import unittest

from vibeagent import workflow_checkpoint_utils
from vibeagent import workflow_checkpoint_formatting
from vibeagent import workflow_checkpoint_commands
from vibeagent import workflow_commands


class WorkflowCheckpointUtilsTests(unittest.TestCase):
    def test_workflow_commands_reexports_checkpoint_utils(self) -> None:
        self.assertIs(workflow_commands.checkpoint_root, workflow_checkpoint_utils.checkpoint_root)
        self.assertIs(workflow_commands.resolve_checkpoint_dir, workflow_checkpoint_utils.resolve_checkpoint_dir)
        self.assertIs(workflow_commands.read_checkpoints, workflow_checkpoint_utils.read_checkpoints)
        self.assertIs(workflow_commands.read_checkpoint_patch, workflow_checkpoint_utils.read_checkpoint_patch)
        self.assertIs(workflow_commands.short_head, workflow_checkpoint_utils.short_head)
        self.assertIs(workflow_commands.count_status_kinds, workflow_checkpoint_utils.count_status_kinds)
        self.assertIs(
            workflow_commands.is_safe_checkpoint_relative_path,
            workflow_checkpoint_utils.is_safe_checkpoint_relative_path,
        )
        self.assertEqual(
            workflow_commands.CHECKPOINT_UNTRACKED_SHOW_LIMIT,
            workflow_checkpoint_utils.CHECKPOINT_UNTRACKED_SHOW_LIMIT,
        )

    def test_workflow_commands_reexports_checkpoint_formatters(self) -> None:
        self.assertIs(
            workflow_commands.format_checkpoint_create_report_text,
            workflow_checkpoint_formatting.format_checkpoint_create_report_text,
        )
        self.assertIs(
            workflow_commands.format_checkpoint_show_report_text,
            workflow_checkpoint_formatting.format_checkpoint_show_report_text,
        )
        self.assertIs(
            workflow_commands.format_checkpoint_status_report_text,
            workflow_checkpoint_formatting.format_checkpoint_status_report_text,
        )
        self.assertIs(
            workflow_commands.format_check_checkpoint_restore_report_text,
            workflow_checkpoint_formatting.format_check_checkpoint_restore_report_text,
        )
        self.assertIs(
            workflow_commands.format_checkpoint_prune_report_text,
            workflow_checkpoint_formatting.format_checkpoint_prune_report_text,
        )

    def test_workflow_commands_reexports_checkpoint_commands(self) -> None:
        self.assertIs(workflow_commands.get_checkpoint_report, workflow_checkpoint_commands.get_checkpoint_report)
        self.assertIs(workflow_commands.get_checkpoint_text, workflow_checkpoint_commands.get_checkpoint_text)
        self.assertIs(workflow_commands.get_checkpoints_report, workflow_checkpoint_commands.get_checkpoints_report)
        self.assertIs(workflow_commands.get_checkpoint_show_report, workflow_checkpoint_commands.get_checkpoint_show_report)
        self.assertIs(workflow_commands.get_checkpoint_diff_report, workflow_checkpoint_commands.get_checkpoint_diff_report)
        self.assertIs(workflow_commands.get_checkpoint_status_report, workflow_checkpoint_commands.get_checkpoint_status_report)
        self.assertIs(workflow_commands.get_check_checkpoint_restore_report, workflow_checkpoint_commands.get_check_checkpoint_restore_report)
        self.assertIs(workflow_commands.get_checkpoint_restore_report, workflow_checkpoint_commands.get_checkpoint_restore_report)
        self.assertIs(workflow_commands.get_check_checkpoint_delete_report, workflow_checkpoint_commands.get_check_checkpoint_delete_report)
        self.assertIs(workflow_commands.get_checkpoint_delete_report, workflow_checkpoint_commands.get_checkpoint_delete_report)
        self.assertIs(workflow_commands.get_check_checkpoint_prune_report, workflow_checkpoint_commands.get_check_checkpoint_prune_report)
        self.assertIs(workflow_commands.get_checkpoint_prune_report, workflow_checkpoint_commands.get_checkpoint_prune_report)
        self.assertIs(workflow_commands.serialize_checkpoint_metadata, workflow_checkpoint_commands.serialize_checkpoint_metadata)
        self.assertIs(workflow_commands.serialize_checkpoint_info, workflow_checkpoint_commands.serialize_checkpoint_info)
        self.assertEqual(workflow_commands.get_checkpoint_restore_text.__module__, "vibeagent.workflow_commands")
        self.assertEqual(workflow_commands.get_checkpoint_prune_text.__module__, "vibeagent.workflow_commands")


if __name__ == "__main__":
    unittest.main()
