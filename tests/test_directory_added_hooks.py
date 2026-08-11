import json
import tempfile
import time
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import Mock, patch

from vibeagent.agent_hook_results import HookRunResult
from vibeagent.directory_added_hooks import (
    collect_directory_added_notifications,
    register_repo_root,
    schedule_directory_added_hooks,
)
from vibeagent.session_store import read_session_events
from vibeagent.types import ApprovalDecision
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_hooks import ProjectHook, ProjectHooks, parse_inline_hooks
from vibeagent.workspace_permissions import ProjectPermissions


def _hook(matcher: str = ".*", command: str = "hook-command") -> ProjectHook:
    return ProjectHook(
        event="DirectoryAdded",
        matcher=matcher,
        command=command,
        timeout_ms=600_000,
        source="test",
    )


def _result(*, ok: bool = True, stdout: str = "", message: str = "passed") -> HookRunResult:
    return HookRunResult(
        event="DirectoryAdded",
        command="hook-command",
        source="test",
        status="passed" if ok else "failed",
        ok=ok,
        exit_code=0 if ok else 1,
        timed_out=False,
        stdout=stdout,
        stderr="",
        message=message,
    )


class DirectoryAddedHookTests(unittest.TestCase):
    def test_schedule_returns_before_background_hook_finishes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-directory-hook-") as base:
            root = Path(base) / "project"
            added = Path(base) / "shared"
            root.mkdir()
            added.mkdir()
            workspace = create_run_workspace(root, run_id="run-1")
            release = Event()
            finished = Event()

            def run_hook(*args, **kwargs):
                release.wait(2)
                finished.set()
                return _result()

            with patch("vibeagent.directory_added_hooks.run_project_hook", side_effect=run_hook):
                started = time.monotonic()
                count = schedule_directory_added_hooks(
                    workspace,
                    added,
                    "slash_command",
                    hooks=ProjectHooks(hooks=(_hook(),)),
                    permissions=ProjectPermissions(),
                    approval_policy="allow",
                    approval_handler=None,
                )
                elapsed = time.monotonic() - started
                self.assertEqual(count, 1)
                self.assertLess(elapsed, 0.5)
                self.assertFalse(finished.is_set())
                release.set()
                self.assertTrue(finished.wait(2))

    def test_slash_command_receives_input_and_delivers_system_message(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-directory-hook-") as base:
            root = Path(base) / "project"
            added = Path(base) / "shared"
            root.mkdir()
            added.mkdir()
            workspace = create_run_workspace(root, run_id="run-2")
            finished = Event()

            def run_hook(*args, **kwargs):
                self.assertEqual(kwargs["target"], "slash_command")
                self.assertEqual(kwargs["hook_input"]["directory"], str(added.resolve()))
                self.assertEqual(kwargs["hook_input"]["source"], "slash_command")
                finished.set()
                return _result(stdout=json.dumps({"systemMessage": "Prepared repository context"}))

            with patch("vibeagent.directory_added_hooks.run_project_hook", side_effect=run_hook):
                schedule_directory_added_hooks(
                    workspace,
                    added,
                    "slash_command",
                    hooks=ProjectHooks(hooks=(_hook("slash_command"),)),
                    permissions=ProjectPermissions(),
                    approval_policy="allow",
                    approval_handler=None,
                )
                self.assertTrue(finished.wait(2))

            notifications = collect_directory_added_notifications(workspace)
            self.assertEqual([item.context for item in notifications], ["Prepared repository context"])
            self.assertEqual(collect_directory_added_notifications(workspace), [])

    def test_matcher_and_denied_approval_skip_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-directory-hook-") as base:
            root = Path(base) / "project"
            added = Path(base) / "shared"
            root.mkdir()
            added.mkdir()
            workspace = create_run_workspace(root, run_id="run-3")
            handler = Mock(return_value=ApprovalDecision(approved=False, message="no"))

            count = schedule_directory_added_hooks(
                workspace,
                added,
                "slash_command",
                hooks=ProjectHooks(
                    hooks=(_hook("register_repo_root"), _hook("slash_command", "denied"))
                ),
                permissions=ProjectPermissions(),
                approval_policy="ask",
                approval_handler=handler,
            )

            self.assertEqual(count, 0)
            handler.assert_called_once()
            event_types = [event.type for event in read_session_events(root, "run-3")]
            self.assertIn("directory_added_hook_denied", event_types)

    def test_failure_is_reported_without_removing_registered_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-directory-hook-") as base:
            root = Path(base) / "project"
            added = Path(base) / "shared"
            root.mkdir()
            added.mkdir()
            workspace = create_run_workspace(root, run_id="run-4")
            finished = Event()

            def run_hook(*args, **kwargs):
                finished.set()
                return _result(ok=False, message="hook failed")

            with patch("vibeagent.directory_added_hooks.run_project_hook", side_effect=run_hook):
                registered = register_repo_root(
                    workspace,
                    added,
                    hooks=ProjectHooks(hooks=(_hook("register_repo_root"),)),
                    permissions=ProjectPermissions(),
                    approval_policy="allow",
                    approval_handler=None,
                )
                self.assertTrue(finished.wait(2))

            self.assertEqual(registered.additional_roots, (added.resolve(),))
            notifications = collect_directory_added_notifications(registered)
            self.assertEqual(notifications, [])
            events = read_session_events(root, "run-4")
            self.assertTrue(any(event.type == "additional_directories_updated" for event in events))

    def test_duplicate_registration_fails_without_scheduling(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-directory-hook-") as base:
            root = Path(base) / "project"
            added = Path(base) / "shared"
            root.mkdir()
            added.mkdir()
            workspace = create_run_workspace(root, run_id="run-5", additional_roots=(added,))

            with patch("vibeagent.directory_added_hooks.schedule_directory_added_hooks") as schedule:
                with self.assertRaisesRegex(ValueError, "already available"):
                    register_repo_root(workspace, added)
            schedule.assert_not_called()

    def test_directory_added_rejects_model_and_explicit_async_handlers(self) -> None:
        prompt = parse_inline_hooks(
            {
                "DirectoryAdded": [
                    {"hooks": [{"type": "prompt", "prompt": "inspect"}]}
                ]
            },
            "test",
        )
        asynchronous = parse_inline_hooks(
            {
                "DirectoryAdded": [
                    {"hooks": [{"type": "command", "command": "true", "async": True}]}
                ]
            },
            "test",
        )
        self.assertIn("support only command, http, or mcp_tool", prompt.error or "")
        self.assertIn("do not support async", asynchronous.error or "")


if __name__ == "__main__":
    unittest.main()
