from __future__ import annotations

from pathlib import Path
from io import StringIO
from contextlib import redirect_stderr, redirect_stdout
import ipaddress
import json
import os
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

from websockets.exceptions import ConnectionClosedOK
from websockets.frames import Close

from vibeagent.action_dispatcher import execute_action
from vibeagent.action_parsing import ActionParseError, parse_tool_action
from vibeagent.agent_approval import build_approval_request
from vibeagent.agent_permissions import authorize_tool_action
from vibeagent.agent_monitor_notifications import inject_monitor_notifications
from vibeagent.background_delegate_runtime import stop_background_delegate_task
from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.monitor_runtime import collect_monitor_notifications, start_monitor_command
from vibeagent.process_registry import (
    PersistentProcessRecord,
    read_persistent_process_record,
    read_process_start_ticks,
    write_persistent_process_record,
)
from vibeagent.types import (
    ApprovalDecision,
    ChatMessage,
    MonitorAction,
    MonitorWebSocketSource,
    StartCommandObservation,
    TaskStopAction,
)
from vibeagent.websocket_monitor_safety import resolve_public_websocket_endpoint
from vibeagent.websocket_monitor_worker import (
    MAX_WEBSOCKET_MESSAGE_BYTES,
    stream_websocket_events,
)
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_permissions import (
    ProjectPermissionRule,
    ProjectPermissions,
    match_project_permission,
)


class MonitorTests(unittest.TestCase):
    def test_parser_supports_claude_alias_defaults_and_persistent_mode(self) -> None:
        positional = MonitorAction("monitor", "python3 watcher.py", "Watch build output")
        action = parse_tool_action(
            "Monitor",
            {"command": "python3 watcher.py", "description": "Watch build output"},
        )
        persistent = parse_tool_action(
            "Monitor",
            {
                "command": "python3 watcher.py",
                "description": "Watch continuously",
                "persistent": True,
                "timeout_ms": 3_600_000,
            },
        )

        self.assertEqual(
            action,
            MonitorAction(
                type="monitor",
                command="python3 watcher.py",
                description="Watch build output",
            ),
        )
        self.assertEqual(positional, action)
        self.assertTrue(persistent.persistent)
        self.assertEqual(persistent.timeout_ms, 0)
        with self.assertRaisesRegex(ActionParseError, "requires a description"):
            parse_tool_action("Monitor", {"command": "python3 watcher.py"})
        with self.assertRaisesRegex(ActionParseError, "at most 3600000"):
            parse_tool_action(
                "Monitor",
                {
                    "command": "python3 watcher.py",
                    "description": "Watch",
                    "timeout_ms": 3_600_001,
                },
            )

    def test_monitor_requires_command_approval(self) -> None:
        request = build_approval_request(
            MonitorAction(
                type="monitor",
                command="python3 watcher.py",
                description="Watch build output",
            )
        )

        self.assertIsNotNone(request)
        assert request is not None
        self.assertEqual(request.action_type, "monitor")
        self.assertIn("python3 watcher.py", request.target)
        self.assertIn("Watch build output", request.risk)

    def test_parser_accepts_websocket_source_and_rejects_ambiguous_inputs(self) -> None:
        action = parse_tool_action(
            "Monitor",
            {
                "ws": {
                    "url": "wss://events.example.com/feed?topic=build",
                    "protocols": ["events.v1", "json"],
                },
                "description": "Watch deployment events",
            },
        )

        self.assertEqual(
            action.ws,
            MonitorWebSocketSource(
                url="wss://events.example.com/feed?topic=build",
                protocols=("events.v1", "json"),
            ),
        )
        self.assertIsNone(action.command)
        for payload in (
            {"description": "missing source"},
            {
                "command": "echo event",
                "ws": {"url": "wss://events.example.com"},
                "description": "two sources",
            },
        ):
            with self.subTest(payload=payload), self.assertRaisesRegex(
                ActionParseError, "exactly one of command or ws"
            ):
                parse_tool_action("Monitor", payload)
        with self.assertRaisesRegex(ActionParseError, "must not contain duplicates"):
            parse_tool_action(
                "Monitor",
                {
                    "ws": {
                        "url": "wss://events.example.com",
                        "protocols": ["json", "json"],
                    },
                    "description": "duplicates",
                },
            )
        with self.assertRaisesRegex(ActionParseError, "subprotocol tokens"):
            parse_tool_action(
                "Monitor",
                {
                    "ws": {
                        "url": "wss://events.example.com",
                        "protocols": ["not valid"],
                    },
                    "description": "invalid protocol",
                },
            )

    def test_websocket_monitor_rejects_credentials_and_private_addresses(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "credentials are not allowed"):
            parse_tool_action(
                "Monitor",
                {
                    "ws": {"url": "wss://user:secret@example.com/events"},
                    "description": "unsafe credentials",
                },
            )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = create_run_workspace(Path(tmp), run_id="monitor-private-ws")
            observation = execute_action(
                workspace,
                MonitorAction(
                    type="monitor",
                    command=None,
                    description="Private socket",
                    ws=MonitorWebSocketSource(url="ws://127.0.0.1:8765/events"),
                ),
            )

        self.assertFalse(observation.ok)
        self.assertIn("public addresses", observation.message)
        self.assertIsNone(observation.pid)

    def test_websocket_resolution_requires_every_address_to_be_public(self) -> None:
        source = MonitorWebSocketSource(url="wss://events.example.com/feed")
        public = (None, None, None, None, ("93.184.216.34", 443))
        private = (None, None, None, None, ("10.0.0.4", 443))
        multicast = (None, None, None, None, ("224.0.0.1", 443))

        with patch("vibeagent.websocket_monitor_safety.socket.getaddrinfo", return_value=[public]):
            parsed, addresses = resolve_public_websocket_endpoint(source)
        self.assertEqual(parsed.hostname, "events.example.com")
        self.assertEqual(addresses, (ipaddress.ip_address("93.184.216.34"),))

        with (
            patch(
                "vibeagent.websocket_monitor_safety.socket.getaddrinfo",
                return_value=[public, private],
            ),
            self.assertRaisesRegex(ValueError, "public addresses"),
        ):
            resolve_public_websocket_endpoint(source)
        with (
            patch(
                "vibeagent.websocket_monitor_safety.socket.getaddrinfo",
                return_value=[multicast],
            ),
            self.assertRaisesRegex(ValueError, "public addresses"),
        ):
            resolve_public_websocket_endpoint(source)

    def test_websocket_worker_preserves_text_frames_and_hides_binary_payloads(self) -> None:
        closed = ConnectionClosedOK(Close(1000, "done"), Close(1000, "done"), True)

        class FakeSocket:
            def close(self) -> None:
                return None

        class FakeConnection:
            def __init__(self) -> None:
                self.messages = ["line one\nline two", b"secret bytes", closed]

            def __enter__(self):
                return self

            def __exit__(self, *_args) -> None:
                return None

            def recv(self):
                value = self.messages.pop(0)
                if isinstance(value, BaseException):
                    raise value
                return value

        connect_calls: list[dict[str, object]] = []

        def fake_connect(_url, **kwargs):
            connect_calls.append(kwargs)
            return FakeConnection()

        output = StringIO()
        source = MonitorWebSocketSource(
            url="wss://events.example.com/feed",
            protocols=("events.v1",),
        )
        with (
            patch(
                "vibeagent.websocket_monitor_worker.resolve_public_websocket_endpoint",
                return_value=(
                    urlsplit(source.url),
                    (ipaddress.ip_address("93.184.216.34"),),
                ),
            ),
            patch(
                "vibeagent.websocket_monitor_worker._connect_public_address",
                return_value=FakeSocket(),
            ),
            redirect_stdout(output),
        ):
            exit_code = stream_websocket_events(source, connect_func=fake_connect)

        events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(exit_code, 0)
        self.assertEqual([event["kind"] for event in events], ["text", "binary", "close"])
        self.assertEqual(events[0]["message"], "line one\nline two")
        self.assertEqual(events[1]["message"], "[binary frame, 12 bytes]")
        self.assertNotIn("secret bytes", output.getvalue())
        self.assertEqual(events[2]["closeCode"], 1000)
        self.assertEqual(connect_calls[0]["subprotocols"], ["events.v1"])
        self.assertIsNone(connect_calls[0]["proxy"])

    def test_websocket_worker_stops_on_oversized_text_message(self) -> None:
        class FakeSocket:
            def close(self) -> None:
                return None

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, *_args) -> None:
                return None

            def recv(self):
                return "x" * (MAX_WEBSOCKET_MESSAGE_BYTES + 1)

        error_output = StringIO()
        source = MonitorWebSocketSource(url="wss://events.example.com/feed")
        with (
            patch(
                "vibeagent.websocket_monitor_worker.resolve_public_websocket_endpoint",
                return_value=(
                    urlsplit(source.url),
                    (ipaddress.ip_address("93.184.216.34"),),
                ),
            ),
            patch(
                "vibeagent.websocket_monitor_worker._connect_public_address",
                return_value=FakeSocket(),
            ),
            redirect_stderr(error_output),
        ):
            exit_code = stream_websocket_events(
                source,
                connect_func=lambda *_args, **_kwargs: FakeConnection(),
            )

        self.assertEqual(exit_code, 1)
        self.assertIn("exceeded 1048576 bytes", error_output.getvalue())

    def test_websocket_envelope_is_delivered_as_one_multiline_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = create_run_workspace(Path(tmp), run_id="monitor-ws-envelope")
            stdout_path = workspace.session_dir / "ws.stdout.log"
            stderr_path = workspace.session_dir / "ws.stderr.log"
            stdout_path.write_text(
                json.dumps({"kind": "text", "message": "first\nsecond"}) + "\n",
                encoding="utf-8",
            )
            stderr_path.write_text("", encoding="utf-8")
            record = PersistentProcessRecord(
                id="ws-envelope",
                command="internal websocket worker",
                cwd=".",
                pid=os.getpid(),
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                start_ticks=read_process_start_ticks(os.getpid()),
                monitor_description="Envelope",
                monitor_timeout_ms=0,
                monitor_started_at=time.time(),
                monitor_session_id=workspace.run_id,
                monitor_source="websocket",
                monitor_target="wss://events.example.com/feed",
            )
            write_persistent_process_record(workspace, record)

            notifications = collect_monitor_notifications(workspace)

        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].message, "first\nsecond")

    def test_websocket_monitor_always_prompts_and_ignores_bash_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = create_run_workspace(Path(tmp), run_id="monitor-ws-approval")
            action = MonitorAction(
                type="monitor",
                command=None,
                description="External events",
                ws=MonitorWebSocketSource(url="wss://events.example.com/feed"),
            )
            allow_rule = ProjectPermissionRule(
                effect="allow",
                tool="Monitor",
                specifier=None,
                raw="Monitor",
                source="trusted",
            )
            approvals: list[str] = []
            request = build_approval_request(action)
            assert request is not None

            authorization = authorize_tool_action(
                workspace,
                ProjectPermissions(
                    rules=(allow_rule,),
                    allow_rules_trusted=True,
                    trusted_allow_sources=("trusted",),
                ),
                "Monitor",
                action,
                1,
                lambda approval: (
                    approvals.append(approval.target)
                    or ApprovalDecision(approved=True, message="approved once")
                ),
                "ask",
                None,
                default_request=request,
            )

        self.assertTrue(authorization.allowed)
        self.assertEqual(approvals, ["wss://events.example.com/feed"])
        bash_deny = ProjectPermissions(
            rules=(
                ProjectPermissionRule(
                    effect="deny",
                    tool="Bash",
                    specifier=None,
                    raw="Bash",
                    source="test",
                ),
            )
        )
        self.assertIsNone(match_project_permission(bash_deny, "Monitor", action))

    def test_websocket_start_records_source_without_exposing_worker_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = create_run_workspace(Path(tmp), run_id="monitor-ws-start")
            action = MonitorAction(
                type="monitor",
                command=None,
                description="Public feed",
                ws=MonitorWebSocketSource(
                    url="wss://events.example.com/feed",
                    protocols=("events.v1",),
                ),
            )

            def fake_start(_workspace, _source):
                stdout_path = workspace.session_dir / "ws-start.stdout.log"
                stderr_path = workspace.session_dir / "ws-start.stderr.log"
                stdout_path.write_text("", encoding="utf-8")
                stderr_path.write_text("", encoding="utf-8")
                write_persistent_process_record(
                    workspace,
                    PersistentProcessRecord(
                        id="ws-start",
                        command="internal worker command",
                        cwd=".",
                        pid=os.getpid(),
                        stdout_path=stdout_path,
                        stderr_path=stderr_path,
                        start_ticks=read_process_start_ticks(os.getpid()),
                    ),
                )
                return StartCommandObservation(
                    kind="start_command",
                    process_id="ws-start",
                    pid=os.getpid(),
                    command="internal worker command",
                    cwd=".",
                    ok=True,
                    message="started",
                    stdout_path=stdout_path.as_posix(),
                    stderr_path=stderr_path.as_posix(),
                )

            with patch(
                "vibeagent.monitor_runtime.start_websocket_monitor_process",
                side_effect=fake_start,
            ):
                observation = start_monitor_command(workspace, action)
            record = read_persistent_process_record(workspace.root, "ws-start")

        self.assertTrue(observation.ok)
        self.assertIsNone(observation.command)
        self.assertEqual(observation.ws_url, "wss://events.example.com/feed")
        self.assertEqual(observation.protocols, ("events.v1",))
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.monitor_source, "websocket")
        self.assertEqual(record.monitor_target, "wss://events.example.com/feed")

    def test_stdout_lines_and_exit_are_delivered_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = create_run_workspace(Path(tmp), run_id="monitor-lines")
            observation = execute_action(
                workspace,
                MonitorAction(
                    type="monitor",
                    command="python3 -u -c \"print('alpha'); print('beta')\"",
                    description="Capture two lines",
                    timeout_ms=5_000,
                ),
            )
            self.assertTrue(observation.ok)

            notifications = self._collect_until_exit(workspace)
            self.assertEqual(
                [item.message for item in notifications if item.status == "output"],
                ["alpha", "beta"],
            )
            self.assertEqual(len([item for item in notifications if item.status == "exited"]), 1)
            self.assertEqual(collect_monitor_notifications(workspace), [])

    def test_timeout_terminates_monitor_and_reports_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = create_run_workspace(Path(tmp), run_id="monitor-timeout")
            observation = execute_action(
                workspace,
                MonitorAction(
                    type="monitor",
                    command="python3 -u -c \"import time; time.sleep(30)\"",
                    description="Timeout sleeper",
                    timeout_ms=100,
                ),
            )
            self.assertTrue(observation.ok)
            record = read_persistent_process_record(workspace.root, observation.task_id)
            self.assertIsNotNone(record)
            assert record is not None and record.monitor_started_at is not None

            notifications = collect_monitor_notifications(
                workspace,
                now=record.monitor_started_at + 1,
            )
            self.assertEqual([item.status for item in notifications], ["timed_out"])
            self.assertEqual(collect_monitor_notifications(workspace), [])

    def test_task_stop_stops_persistent_monitor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = create_run_workspace(Path(tmp), run_id="monitor-stop")
            observation = execute_action(
                workspace,
                MonitorAction(
                    type="monitor",
                    command="python3 -u -c \"import time; print('ready'); time.sleep(30)\"",
                    description="Persistent sleeper",
                    persistent=True,
                    timeout_ms=0,
                ),
            )
            self.assertTrue(observation.ok)

            stopped = stop_background_delegate_task(
                workspace,
                TaskStopAction(type="task_stop", task_id=observation.task_id),
            )
            self.assertTrue(stopped.ok)
            self.assertTrue(stopped.stopped)
            self.assertIn("Stopped monitor", stopped.message)

    def test_agent_notification_is_untrusted_and_consumed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = create_run_workspace(Path(tmp), run_id="monitor-inject")
            observation = execute_action(
                workspace,
                MonitorAction(
                    type="monitor",
                    command="python3 -u -c \"print('event line')\"",
                    description="Inject output",
                    timeout_ms=5_000,
                ),
            )
            self.assertTrue(observation.ok)
            self._collect_until_output_available(workspace)
            messages: list[ChatMessage] = []

            delivered = inject_monitor_notifications(
                workspace,
                messages,
                iteration=2,
                logger=None,
            )

            self.assertGreater(delivered, 0)
            self.assertEqual(messages[-1].role, "user")
            self.assertIn("Untrusted background Monitor", messages[-1].content)
            self.assertIn("event line", messages[-1].content)

    def test_idle_interactive_session_wakes_for_monitor_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-monitor-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, run_id="source-run")
            observation = execute_action(
                workspace,
                MonitorAction(
                    type="monitor",
                    command="python3 -u -c \"import time; print('idle event'); time.sleep(30)\"",
                    description="Wake idle agent",
                    persistent=True,
                    timeout_ms=0,
                ),
            )
            self.assertTrue(observation.ok)
            self._collect_until_output_available(workspace)
            run_agent = Mock(return_value=SimpleNamespace(run_id="monitor-run"))

            def trigger_idle(_prompt, callback, *, input_func, interval_seconds=1.0):
                callback()
                return "/exit"

            with (
                patch("vibeagent.cli_interactive.input_with_idle_callback", side_effect=trigger_idle),
                patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                patch("vibeagent.cli_interactive.print_agent_result"),
                patch("vibeagent.cli_interactive.Path.cwd", return_value=root),
                patch("sys.stdout", new_callable=StringIO) as stdout,
            ):
                exit_code = run_interactive_loop(
                    command_namespace={},
                    create_chat_client_func=Mock(return_value=object()),
                    run_agent_func=run_agent,
                    get_resume_context_func=Mock(
                        return_value=("monitor-run", "next context", "loaded")
                    ),
                    initial_resume_run_id="source-run",
                    initial_resume_context="source context",
                )
            self.assertIsNone(
                read_persistent_process_record(workspace.root, observation.task_id)
            )

        self.assertEqual(exit_code, 0)
        prompt = run_agent.call_args.args[0]
        self.assertIn("Untrusted background Monitor", prompt)
        self.assertIn("idle event", prompt)
        self.assertEqual(run_agent.call_args.kwargs["task_metadata"]["source"], "monitor")
        self.assertIn("Monitor event received", stdout.getvalue())

    @staticmethod
    def _collect_until_exit(workspace) -> list:
        collected = []
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            collected.extend(collect_monitor_notifications(workspace))
            if any(item.status in {"exited", "timed_out"} for item in collected):
                return collected
            time.sleep(0.02)
        raise AssertionError("monitor did not exit")

    @staticmethod
    def _collect_until_output_available(workspace) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            records = list((workspace.root / ".vibeagent" / "processes").glob("*.json"))
            if records:
                record = read_persistent_process_record(workspace.root, records[0].stem)
                if record is not None and record.stdout_path.exists() and record.stdout_path.stat().st_size:
                    return
            time.sleep(0.02)
        raise AssertionError("monitor produced no output")


if __name__ == "__main__":
    unittest.main()
