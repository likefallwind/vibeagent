from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent.cli_interactive_directories import (
    InteractiveAddDirectoryRequest,
    InteractiveDirectorySwitchRequest,
    apply_interactive_add_directory,
    switch_interactive_directory,
)


class InteractiveDirectoryCommandTests(unittest.TestCase):
    def test_add_directory_updates_runtime_workspace_and_schedules_hook(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-interactive-directories-") as base:
            project = Path(base) / "project"
            shared = Path(base) / "shared"
            project.mkdir()
            shared.mkdir()
            runtime = Mock()
            with patch(
                "vibeagent.cli_interactive_directories.schedule_directory_added_hooks"
            ) as schedule:
                result = apply_interactive_add_directory(
                    InteractiveAddDirectoryRequest(
                        project_root=project,
                        argument="../shared",
                        additional_directories=(),
                        pending_workspace=None,
                        resume_run_id=None,
                        project_runtime=runtime,
                        approval_policy="ask",
                        approval_handler=None,
                        safe_mode=False,
                        bare_mode=False,
                        setting_sources=("user", "project", "local"),
                        settings_override_json=None,
                        invocation_plugin_dirs=(),
                    )
                )

        self.assertEqual(result.additional_directories, (shared.resolve(),))
        self.assertIsNotNone(result.pending_workspace)
        assert result.pending_workspace is not None
        self.assertEqual(result.pending_workspace.additional_roots, (shared.resolve(),))
        self.assertEqual(result.messages, (f"Added working directory: {shared.resolve()}",))
        runtime.close_workflow.assert_called_once_with()
        schedule.assert_called_once()
        self.assertEqual(schedule.call_args.args[0], result.pending_workspace)
        self.assertEqual(schedule.call_args.args[1:3], (shared.resolve(), "slash_command"))

    def test_add_directory_noop_does_not_change_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-interactive-directories-") as base:
            project = Path(base)
            runtime = Mock()
            result = apply_interactive_add_directory(
                InteractiveAddDirectoryRequest(
                    project_root=project,
                    argument=None,
                    additional_directories=(),
                    pending_workspace=None,
                    resume_run_id=None,
                    project_runtime=runtime,
                    approval_policy="ask",
                    approval_handler=None,
                    safe_mode=False,
                    bare_mode=False,
                    setting_sources=("user", "project", "local"),
                    settings_override_json=None,
                    invocation_plugin_dirs=(),
                )
            )

        self.assertFalse(result.additional_directories)
        self.assertIn("Additional working directories: none", result.messages[0])
        runtime.close_workflow.assert_not_called()

    def test_switch_directory_replaces_project_runtime_and_preserves_session_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-interactive-cd-runtime-") as base:
            first = Path(base) / "first"
            second = Path(base) / "second"
            first.mkdir()
            second.mkdir()
            old_runtime = Mock()
            new_runtime = Mock()
            session_end = Mock()
            previous_cwd = Path.cwd()
            os.chdir(first)
            try:
                with patch(
                    "vibeagent.cli_interactive_directories.InteractiveProjectRuntime",
                    return_value=new_runtime,
                ) as create_runtime:
                    result = switch_interactive_directory(
                        InteractiveDirectorySwitchRequest(
                            project_root=first,
                            argument="../second",
                            additional_directories=(),
                            pending_workspace=None,
                            pending_branch_source_run_id=None,
                            resume_run_id="source-run",
                            project_permissions_trusted=True,
                            project_runtime=old_runtime,
                            goal_state=None,
                            approval_policy="ask",
                            safe_mode=False,
                            bare_mode=False,
                            setting_sources=("user", "project", "local"),
                            settings_override_json=None,
                            invocation_plugin_dirs=(),
                        ),
                        run_session_end_hook=session_end,
                        prompt_project_permission_trust=lambda _target: False,
                    )
            finally:
                os.chdir(previous_cwd)

        self.assertTrue(result.changed)
        self.assertIs(result.project_runtime, new_runtime)
        self.assertFalse(result.project_permissions_trusted)
        self.assertEqual(result.pending_branch_source_run_id, "source-run")
        self.assertIsNotNone(result.pending_workspace)
        assert result.pending_workspace is not None
        self.assertEqual(result.resume_run_id, result.pending_workspace.run_id)
        self.assertIn("Changed project directory", result.messages[0])
        self.assertIn("Conversation preserved", result.messages[1])
        session_end.assert_called_once_with()
        old_runtime.close.assert_called_once_with((), close_lsp=True)
        create_runtime.assert_called_once_with(
            second.resolve(),
            "ask",
            initial_session_id=result.resume_run_id,
            safe_mode=False,
            bare_mode=False,
            setting_sources=("user", "project", "local"),
            settings_override_json=None,
            invocation_plugin_dirs=(),
        )

    def test_switch_directory_validation_failure_preserves_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-interactive-cd-runtime-") as base:
            project = Path(base)
            runtime = Mock()
            session_end = Mock()
            result = switch_interactive_directory(
                InteractiveDirectorySwitchRequest(
                    project_root=project,
                    argument="missing",
                    additional_directories=(),
                    pending_workspace=None,
                    pending_branch_source_run_id="branch-source",
                    resume_run_id="run-1",
                    project_permissions_trusted=True,
                    project_runtime=runtime,
                    goal_state=None,
                    approval_policy="ask",
                    safe_mode=False,
                    bare_mode=False,
                    setting_sources=("user", "project", "local"),
                    settings_override_json=None,
                    invocation_plugin_dirs=(),
                ),
                run_session_end_hook=session_end,
                prompt_project_permission_trust=lambda _target: False,
            )

        self.assertFalse(result.changed)
        self.assertIs(result.project_runtime, runtime)
        self.assertEqual(result.pending_branch_source_run_id, "branch-source")
        self.assertIn("Cannot change directory", result.messages[0])
        runtime.close.assert_not_called()
        session_end.assert_not_called()


if __name__ == "__main__":
    unittest.main()
