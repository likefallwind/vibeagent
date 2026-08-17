from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from vibeagent.cli_interactive_local_dispatch import (
    InteractiveLocalCommandContext,
    dispatch_interactive_local_command,
)
from vibeagent.command_types import LocalCommand


def _context() -> InteractiveLocalCommandContext:
    return InteractiveLocalCommandContext(
        project_root=Path("/workspace"),
        mode="chat",
        approval_policy="ask",
        resume_run_id="run-1",
        resume_context="context",
        chat_turns=3,
        effort="high",
        autocompact="12000",
        system_prompt_set=True,
        append_system_prompt_set=False,
        permission_mode="default",
        safe_mode=True,
    )


class InteractiveLocalCommandDispatchTests(unittest.TestCase):
    def test_returns_first_matching_handler_without_running_later_handlers(self) -> None:
        command = LocalCommand(type="project_commands")
        namespace: dict[str, object] = {}
        project_namespace: dict[str, object] = {}
        with (
            patch(
                "vibeagent.cli_interactive_local_dispatch.run_interactive_project_command",
                return_value="project result",
            ) as project,
            patch(
                "vibeagent.cli_interactive_local_dispatch.run_interactive_background_agent_command"
            ) as background,
            patch(
                "vibeagent.cli_interactive_local_dispatch.run_interactive_project_state_command"
            ) as state,
        ):
            result = dispatch_interactive_local_command(
                command,
                namespace,
                _context(),
                project_command_namespace=project_namespace,
            )

        self.assertEqual(result, "project result")
        project.assert_called_once_with(
            command,
            project_namespace,
            "ask",
            Path("/workspace"),
            safe_mode=True,
        )
        background.assert_not_called()
        state.assert_not_called()

    def test_passes_interactive_state_to_state_command(self) -> None:
        command = LocalCommand(type="status")
        namespace: dict[str, object] = {}
        context = _context()
        handlers = (
            "run_interactive_project_command",
            "run_interactive_background_agent_command",
            "run_interactive_command_execution",
            "run_interactive_read_command",
            "run_interactive_code_intel_command",
            "run_interactive_json_command",
            "run_interactive_text_edit_command",
            "run_interactive_edit_command",
            "run_interactive_patch_command",
            "run_interactive_git_command",
            "run_interactive_runtime_command",
        )
        patches = [
            patch(f"vibeagent.cli_interactive_local_dispatch.{name}", return_value=None)
            for name in handlers
        ]
        entered = [item.start() for item in patches]
        self.addCleanup(lambda: [item.stop() for item in reversed(patches)])
        with (
            patch(
                "vibeagent.cli_interactive_local_dispatch.run_interactive_project_state_command",
                return_value="state result",
            ) as state,
            patch(
                "vibeagent.cli_interactive_local_dispatch.run_interactive_review_command"
            ) as review,
        ):
            result = dispatch_interactive_local_command(command, namespace, context)

        self.assertTrue(all(mock.call_count == 1 for mock in entered))
        self.assertEqual(result, "state result")
        state.assert_called_once_with(
            command,
            namespace,
            mode="chat",
            approval_policy="ask",
            resume_run_id="run-1",
            resume_context="context",
            chat_turns=3,
            effort="high",
            autocompact="12000",
            system_prompt_set=True,
            append_system_prompt_set=False,
            permission_mode="default",
        )
        review.assert_not_called()

    def test_falls_back_to_review_after_other_handlers_decline(self) -> None:
        command = LocalCommand(type="review")
        namespace: dict[str, object] = {}
        handlers = (
            "run_interactive_project_command",
            "run_interactive_background_agent_command",
            "run_interactive_command_execution",
            "run_interactive_read_command",
            "run_interactive_code_intel_command",
            "run_interactive_json_command",
            "run_interactive_text_edit_command",
            "run_interactive_edit_command",
            "run_interactive_patch_command",
            "run_interactive_git_command",
            "run_interactive_runtime_command",
            "run_interactive_project_state_command",
        )
        patches = [
            patch(f"vibeagent.cli_interactive_local_dispatch.{name}", return_value=None)
            for name in handlers
        ]
        entered = [item.start() for item in patches]
        self.addCleanup(lambda: [item.stop() for item in reversed(patches)])
        with patch(
            "vibeagent.cli_interactive_local_dispatch.run_interactive_review_command",
            return_value="review result",
        ) as review:
            result = dispatch_interactive_local_command(command, namespace, _context())

        self.assertTrue(all(mock.call_count == 1 for mock in entered))
        self.assertEqual(result, "review result")
        review.assert_called_once_with(command, namespace)


if __name__ == "__main__":
    unittest.main()
