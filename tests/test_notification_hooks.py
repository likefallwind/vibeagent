from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent.agent import run_agent
from vibeagent.agent_lifecycle_hooks import LifecycleHookResult
from vibeagent.agent_notification_hooks import wrap_approval_handler_with_notification
from vibeagent.cli_idle_notification import IdleNotificationTimer
from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.session_lifecycle_hooks import run_interactive_notification_hooks
from vibeagent.session_approval import SessionApprovalHandler
from vibeagent.types import (
    ApprovalDecision,
    ApprovalRequest,
    AssistantResponse,
    ChatMessage,
    ContentBlock,
)
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks


class NotificationClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


def _write_notification_hook(root: Path, command: str, matcher: str = ".*") -> None:
    path = root / ".vibeagent" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "Notification": [
                    {
                        "matcher": matcher,
                        "hooks": [
                            {
                                "type": "command",
                                "command": command,
                                "timeout_ms": 10_000,
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def _approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


class NotificationHookConfigTests(unittest.TestCase):
    def test_loads_notification_without_forcing_sequential_tools(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-notification-") as base:
            root = Path(base)
            _write_notification_hook(root, "true", "permission_prompt|idle_prompt")

            config = read_project_hooks(create_run_workspace(root))

        self.assertIsNone(config.error)
        self.assertEqual(config.hooks[0].event, "Notification")
        self.assertFalse(config.requires_sequential_tools)

    def test_rejects_model_notification_handlers(self) -> None:
        for handler_type in ("prompt", "agent"):
            with self.subTest(handler_type=handler_type), tempfile.TemporaryDirectory(
                prefix="vibeagent-notification-"
            ) as base:
                root = Path(base)
                path = root / ".vibeagent" / "hooks.json"
                path.parent.mkdir(parents=True)
                path.write_text(
                    json.dumps(
                        {
                            "Notification": [
                                {
                                    "hooks": [
                                        {
                                            "type": handler_type,
                                            "prompt": "inspect notification",
                                        }
                                    ]
                                }
                            ]
                        }
                    ),
                    encoding="utf-8",
                )

                config = read_project_hooks(create_run_workspace(root))

            self.assertIn(f"do not support {handler_type} handlers", config.error or "")


class NotificationHookRuntimeTests(unittest.TestCase):
    def test_remembered_session_approval_does_not_repeat_notification(self) -> None:
        request = ApprovalRequest(
            action_type="write_file",
            target="note.txt",
            risk="writes a file",
        )
        prompt = Mock(
            return_value=ApprovalDecision(
                approved=True,
                message="remember",
                scope="session",
            )
        )
        notify = Mock(return_value=LifecycleHookResult())
        handler = wrap_approval_handler_with_notification(
            SessionApprovalHandler(prompt),
            notify,
            [],
        )
        assert handler is not None

        first = handler(request)
        second = handler(request)

        self.assertTrue(first.approved)
        self.assertTrue(second.remembered)
        self.assertEqual(prompt.call_count, 1)
        self.assertEqual(notify.call_count, 1)

    def test_permission_prompt_notification_is_nonblocking_and_user_only(self) -> None:
        command = (
            'python3 -c "import json,sys; d=json.load(sys.stdin); '
            "print(json.dumps({'decision':'block','reason':'ignored','systemMessage':"
            "json.dumps({k:d[k] for k in ['notification_type','message','title']},sort_keys=True)}))\""
        )
        client = NotificationClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "note.txt", "content": "ready\n"},
                    }
                ],
                [{"type": "text", "text": "done"}],
            ]
        )
        requests = []

        def approve(request):
            requests.append(request)
            return ApprovalDecision(approved=True, message="approved")

        with tempfile.TemporaryDirectory(prefix="vibeagent-notification-") as base:
            root = Path(base)
            _write_notification_hook(root, command, "^permission_prompt$")

            result = run_agent(
                "write the note",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=approve,
            )

            note = root.joinpath("note.txt").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(note, "ready\n")
        self.assertEqual([request.action_type for request in requests], ["run_command", "write_file"])
        self.assertEqual(len(result.hook_system_messages), 1)
        payload = json.loads(result.hook_system_messages[0])
        self.assertEqual(
            payload,
            {
                "message": "VibeAgent needs your permission to use write_file.",
                "notification_type": "permission_prompt",
                "title": "Permission needed",
            },
        )
        self.assertNotIn(result.hook_system_messages[0], str(client.messages))

    def test_permission_notification_does_not_fire_without_user_approval_boundary(self) -> None:
        client = NotificationClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "note.txt", "content": "ready\n"},
                    }
                ],
                [{"type": "text", "text": "done"}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-notification-") as base:
            root = Path(base)
            _write_notification_hook(root, "true", "^permission_prompt$")

            result = run_agent(
                "write the note",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_policy="allow",
            )
            events = root.joinpath(
                ".vibeagent", "sessions", result.run_id, "events.jsonl"
            ).read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertNotIn('"event":"Notification"', events.replace(" ", ""))

    def test_notification_exit_two_cannot_deny_original_action(self) -> None:
        command = (
            'python3 -c "import sys; print(\'notification failed\', file=sys.stderr); '
            "raise SystemExit(2)\""
        )
        client = NotificationClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "note.txt", "content": "ready\n"},
                    }
                ],
                [{"type": "text", "text": "done"}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-notification-") as base:
            root = Path(base)
            _write_notification_hook(root, command, "^permission_prompt$")

            result = run_agent(
                "write the note",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=_approve,
            )
            note = root.joinpath("note.txt").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(note, "ready\n")

    def test_idle_notification_uses_existing_session_and_returns_system_message(self) -> None:
        command = (
            'python3 -c "import json,sys; d=json.load(sys.stdin); '
            "print(json.dumps({'systemMessage':d['notification_type'] + ':' + d['message']}))\""
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-notification-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, run_id="idle-run")
            _write_notification_hook(root, command, "^idle_prompt$")

            result = run_interactive_notification_hooks(
                root,
                workspace.run_id,
                workspace,
                (),
                "idle_prompt",
                "VibeAgent is waiting for your input.",
                title="VibeAgent is waiting",
                command_timeout_ms=30_000,
                approval_handler=_approve,
                approval_policy="ask",
            )

        self.assertEqual(
            result.system_messages,
            ("idle_prompt:VibeAgent is waiting for your input.",),
        )


class IdleNotificationTests(unittest.TestCase):
    def test_timer_fires_once_after_delay(self) -> None:
        timer = IdleNotificationTimer(delay_seconds=60, started_at=100)

        self.assertFalse(timer.due(159.9))
        self.assertTrue(timer.due(160))
        self.assertFalse(timer.due(1_000))

    def test_interactive_idle_callback_dispatches_and_prints_notification(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-notification-") as base:
            root = Path(base)
            create_run_workspace(root, run_id="idle-run")
            notifier = Mock(return_value=LifecycleHookResult(system_messages=("attention",)))
            timer = Mock()
            timer.due.return_value = True
            updater = Mock()
            updater.collect_notifications.return_value = []
            stdout = io.StringIO()

            def idle_input(_prompt, callback, *, input_func):
                callback()
                return "/exit"

            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                with (
                    patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                    patch("vibeagent.cli_interactive.create_peer_runtime", return_value=None),
                    patch("vibeagent.cli_interactive.PluginAutoUpdateRuntime", return_value=updater),
                    patch("vibeagent.cli_interactive.IdleNotificationTimer", return_value=timer),
                    patch("vibeagent.cli_interactive.run_interactive_notification_hooks", notifier),
                    patch("vibeagent.cli_interactive.input_with_idle_callback", side_effect=idle_input),
                    redirect_stdout(stdout),
                ):
                    exit_code = run_interactive_loop(
                        command_namespace={},
                        initial_resume_run_id="idle-run",
                    )
            finally:
                os.chdir(old_cwd)

        self.assertEqual(exit_code, 0)
        notifier.assert_called_once()
        self.assertEqual(notifier.call_args.args[4], "idle_prompt")
        self.assertIn("attention", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
