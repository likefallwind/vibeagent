from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent.cli_interactive_session_navigation import (
    InteractiveSessionNavigationRequest,
    InteractiveSessionNavigationState,
    navigate_interactive_session,
)
from vibeagent.command_types import LocalCommand
from vibeagent.types import ChatMessage
from vibeagent.workspace_core import create_run_workspace


def _state() -> InteractiveSessionNavigationState:
    return InteractiveSessionNavigationState(
        resume_run_id="run-1",
        resume_context="context",
        pending_workspace=None,
        pending_branch_source_run_id="branch-source",
        additional_directories=(),
        conversation_messages=(ChatMessage(role="assistant", content="prior"),),
        goal_state=None,
    )


def _request(
    project_root: Path,
    command: LocalCommand,
    runtime: Mock,
) -> InteractiveSessionNavigationRequest:
    return InteractiveSessionNavigationRequest(
        project_root=project_root,
        command=command,
        command_namespace={},
        state=_state(),
        project_runtime=runtime,
        safe_mode=False,
        bare_mode=False,
        disable_slash_commands=False,
        setting_sources=("user", "project", "local"),
        settings_override_json=None,
        invocation_plugin_dirs=(),
    )


class InteractiveSessionNavigationTests(unittest.TestCase):
    def test_declines_non_session_command_without_changing_state(self) -> None:
        runtime = Mock()
        handlers = (
            "run_interactive_session_management",
            "run_interactive_session_command",
            "run_interactive_rewind_command",
            "run_interactive_checkpoint_command",
            "run_interactive_resume_command",
        )
        patches = [
            patch(
                f"vibeagent.cli_interactive_session_navigation.{name}",
                return_value=None,
            )
            for name in handlers
        ]
        entered = [item.start() for item in patches]
        self.addCleanup(lambda: [item.stop() for item in reversed(patches)])

        result = navigate_interactive_session(
            _request(Path.cwd(), LocalCommand(type="chat"), runtime),
            get_resume_context=Mock(),
            run_lifecycle_hook=Mock(),
        )

        self.assertTrue(all(handler.call_count == 1 for handler in entered))
        self.assertFalse(result.handled)
        self.assertEqual(result.state, _state())
        runtime.close_workflow.assert_not_called()

    def test_rewind_replaces_session_state_and_resets_conversation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-navigation-rewind-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "rewound-run")
            runtime = Mock()
            with (
                patch(
                    "vibeagent.cli_interactive_session_navigation.run_interactive_session_management",
                    return_value=None,
                ),
                patch(
                    "vibeagent.cli_interactive_session_navigation.run_interactive_session_command",
                    return_value=None,
                ),
                patch(
                    "vibeagent.cli_interactive_session_navigation.run_interactive_rewind_command",
                    return_value=SimpleNamespace(
                        workspace=workspace,
                        context="rewound context",
                        text="Rewound.",
                    ),
                ),
            ):
                result = navigate_interactive_session(
                    _request(root, LocalCommand(type="rewind", argument="1"), runtime),
                    get_resume_context=Mock(),
                    run_lifecycle_hook=Mock(),
                )

        self.assertTrue(result.handled)
        self.assertTrue(result.reset_code_recap)
        self.assertEqual(result.messages, ("Rewound.",))
        self.assertEqual(result.state.resume_run_id, "rewound-run")
        self.assertEqual(result.state.resume_context, "rewound context")
        self.assertEqual(result.state.pending_workspace, workspace)
        self.assertIsNone(result.state.pending_branch_source_run_id)
        self.assertEqual(result.state.conversation_messages, ())
        runtime.close_workflow.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
