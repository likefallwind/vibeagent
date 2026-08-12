from __future__ import annotations

import json
from io import StringIO
import stat
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from vibeagent.agent import run_agent
from vibeagent.async_hook_runtime import (
    async_hook_notifications_prompt,
    close_session_async_hooks,
    collect_async_hook_notifications,
    start_async_hook,
)
from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.process_stop_runtime import list_background_processes
from vibeagent.process_registry import read_persistent_process_record
from vibeagent.session_timeline_reports import format_session_event_timeline_item
from vibeagent.session_types import SessionEvent
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import ProjectHook, read_project_hooks


class _AsyncHookClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        index = len(self.messages) - 1
        if index == 1:
            time.sleep(0.15)
        content = self.responses[index]
        return AssistantResponse(content=content, raw={"content": content})


def _approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


def _write_hooks(root: Path, command: str, *, event: str = "PostToolUse") -> None:
    path = root / ".claude" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "hooks": {
                    event: [
                        {
                            "matcher": "Write",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": command,
                                    "async": True,
                                    "timeout": 2,
                                }
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )


def _start_direct_hook(
    root: Path,
    *,
    script_body: str,
    rewake: bool,
) -> tuple[object, str]:
    workspace = create_run_workspace(root)
    input_path = workspace.session_dir / ".hook-input-test.json"
    launch_path = workspace.session_dir / ".hook-launch-test.sh"
    input_path.write_text("{}", encoding="utf-8")
    input_path.chmod(0o600)
    launch_path.write_text(f"#!/bin/sh\ncat >/dev/null\n{script_body}\n", encoding="utf-8")
    launch_path.chmod(0o700)
    hook = ProjectHook(
        event="PostToolUse",
        matcher="Write",
        command="test hook",
        timeout_ms=2_000,
        source="test",
        async_=True,
        async_rewake=rewake,
    )
    process_id, message = start_async_hook(
        workspace,
        hook,
        target="Write",
        command=f"{launch_path} < {input_path}",
        input_path=input_path,
        environment_path=launch_path,
        cwd=None,
    )
    if process_id is None:
        raise AssertionError(message)
    return workspace, process_id


def _collect_until_ready(workspace, *, rewake_only: bool = False):
    for _ in range(100):
        notifications = collect_async_hook_notifications(
            workspace,
            rewake_only=rewake_only,
        )
        if notifications:
            return notifications
        time.sleep(0.02)
    return []


class AsyncHookConfigTests(unittest.TestCase):
    def test_parses_async_rewake_and_claude_timeout_seconds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-async-hook-") as base:
            root = Path(base)
            _write_hooks(root, "python3 -V")
            config = read_project_hooks(create_run_workspace(root))

        self.assertIsNone(config.error)
        self.assertEqual(len(config.hooks), 1)
        self.assertTrue(config.hooks[0].async_)
        self.assertFalse(config.hooks[0].async_rewake)
        self.assertEqual(config.hooks[0].timeout_ms, 2_000)
        self.assertTrue(config.requires_sequential_tools)

    def test_async_rewake_implies_async_and_invalid_values_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-async-hook-") as base:
            root = Path(base)
            path = root / ".vibeagent" / "hooks.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    {
                        "PostToolUse": [
                            {
                                "matcher": "Write",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "python3 -V",
                                        "asyncRewake": True,
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            config = read_project_hooks(create_run_workspace(root))
            self.assertTrue(config.hooks[0].async_)
            self.assertTrue(config.hooks[0].async_rewake)
            self.assertEqual(config.hooks[0].timeout_ms, 600_000)

            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["PostToolUse"][0]["hooks"][0]["async"] = "yes"
            path.write_text(json.dumps(payload), encoding="utf-8")
            invalid = read_project_hooks(create_run_workspace(root))

        self.assertIn("async must be a boolean", invalid.error or "")


class AsyncHookRuntimeTests(unittest.TestCase):
    def test_running_async_hook_reports_new_output_progress_after_one_second(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-async-hook-") as base:
            root = Path(base)
            workspace, process_id = _start_direct_hook(
                root,
                script_body="printf 'working\\n'; sleep 5",
                rewake=False,
            )
            record = read_persistent_process_record(root, process_id)
            assert record is not None
            for _ in range(100):
                if record.stdout_path.exists() and record.stdout_path.read_text(encoding="utf-8"):
                    break
                time.sleep(0.01)

            notifications = collect_async_hook_notifications(
                workspace,
                now=time.time() + 1.1,
            )
            events = [
                json.loads(line)
                for line in (workspace.session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            state = json.loads(next((workspace.session_dir / "async-hooks").glob("*.json")).read_text(encoding="utf-8"))
            close_session_async_hooks(workspace)

        progress = [event for event in events if event["type"] == "hook_progress"]
        self.assertEqual(notifications, [])
        self.assertEqual(len(progress), 1)
        self.assertEqual(progress[0]["hook_id"], state["hook_id"])
        self.assertIn("working", progress[0]["output"])
        self.assertGreater(state["progress_bytes"], 0)

    def test_agent_continues_and_injects_completed_context_once(self) -> None:
        command = (
            "python3 -c 'import json,time; time.sleep(0.05); "
            "print(json.dumps({\"systemMessage\":\"user-only warning\","
            "\"hookSpecificOutput\":{\"hookEventName\":\"PostToolUse\","
            "\"additionalContext\":\"async tests passed\"}}))'"
        )
        client = _AsyncHookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "Write",
                        "input": {"file_path": "app.py", "content": "x = 1\n"},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "read-1",
                        "name": "Read",
                        "input": {"file_path": "app.py"},
                    }
                ],
                [{"type": "text", "text": "Observed the async hook result."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-async-hook-") as base:
            root = Path(base)
            _write_hooks(root, command)
            result = run_agent(
                "Create and inspect app.py",
                base_dir=root,
                client=client,
                max_iterations=3,
                approval_handler=_approve,
            )
            state_files = list(
                (root / ".vibeagent" / "sessions" / result.run_id / "async-hooks").glob("*.json")
            )
            events = [
                json.loads(line)
                for line in (
                    root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]
            app_content = root.joinpath("app.py").read_text(encoding="utf-8")
            state_mode = stat.S_IMODE(state_files[0].stat().st_mode)
            state = json.loads(state_files[0].read_text(encoding="utf-8"))
            input_files_remain = any(
                state_files[0].parent.parent.glob(".hook-input-*")
            )
            launch_files_remain = any(
                state_files[0].parent.parent.glob(".hook-launch-*")
            )

        self.assertEqual(app_content, "x = 1\n")
        self.assertFalse(
            any("async tests passed" in str(message.content) for message in client.messages[0])
        )
        self.assertTrue(
            any(
                "async tests passed" in str(message.content)
                for turn in client.messages[1:]
                for message in turn
            )
        )
        async_context_prompts = [
            str(message.content)
            for turn in client.messages
            for message in turn
            if "Untrusted asynchronous hook result" in str(message.content)
        ]
        self.assertTrue(async_context_prompts)
        self.assertTrue(
            all("user-only warning" not in prompt for prompt in async_context_prompts)
        )
        self.assertEqual(result.hook_system_messages, ["user-only warning"])
        self.assertEqual(len(state_files), 1)
        self.assertEqual(state_mode, 0o600)
        self.assertTrue(state["delivered"])
        self.assertFalse(input_files_remain)
        self.assertFalse(launch_files_remain)
        self.assertEqual(sum(event["type"] == "async_hook_started" for event in events), 1)
        self.assertEqual(sum(event["type"] == "async_hook_completed" for event in events), 1)
        lifecycle = [event for event in events if event["type"] in {"hook_started", "hook_response"}]
        self.assertEqual([event["type"] for event in lifecycle], ["hook_started", "hook_response"])
        self.assertEqual(len({event["hook_id"] for event in lifecycle}), 1)
        self.assertEqual(lifecycle[-1]["outcome"], "success")
        self.assertEqual(
            sum(event["type"] == "async_hook_notifications_delivered" for event in events),
            1,
        )

    def test_async_pre_tool_decision_cannot_block_completed_action(self) -> None:
        command = (
            "python3 -c 'import json,time; time.sleep(0.8); "
            "print(json.dumps({\"hookSpecificOutput\":{"
            "\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\","
            "\"additionalContext\":\"late policy output\"}}))'"
        )
        client = _AsyncHookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "Write",
                        "input": {"file_path": "kept.py", "content": "kept = True\n"},
                    }
                ],
                [{"type": "text", "text": "Write completed."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-async-hook-") as base:
            root = Path(base)
            _write_hooks(root, command, event="PreToolUse")
            started_at = time.monotonic()
            result = run_agent(
                "Write kept.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=_approve,
            )
            elapsed = time.monotonic() - started_at
            self.assertEqual(root.joinpath("kept.py").read_text(encoding="utf-8"), "kept = True\n")
            self.assertLess(elapsed, 0.6)
            workspace = create_run_workspace(root, run_id=result.run_id)
            self.assertTrue(_collect_until_ready(workspace))

    def test_rewake_requires_exit_two_and_ordinary_context_waits_for_next_turn(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-async-hook-") as base:
            root = Path(base)
            ordinary_workspace, ordinary_id = _start_direct_hook(
                root,
                script_body="printf '%s\\n' '{\"systemMessage\":\"ordinary result\"}'",
                rewake=False,
            )
            ordinary_record = read_persistent_process_record(root, ordinary_id)
            self.assertIsNotNone(ordinary_record)
            assert ordinary_record is not None
            self.assertEqual(
                stat.S_IMODE(ordinary_record.stdout_path.stat().st_mode),
                0o600,
            )
            self.assertEqual(
                stat.S_IMODE(ordinary_record.stderr_path.stat().st_mode),
                0o600,
            )
            time.sleep(0.08)
            self.assertEqual(
                collect_async_hook_notifications(ordinary_workspace, rewake_only=True),
                [],
            )
            ordinary = _collect_until_ready(ordinary_workspace)

            rewake_workspace, rewake_id = _start_direct_hook(
                root,
                script_body="printf '%s\\n' 'build failed' >&2; exit 2",
                rewake=True,
            )
            rewake = _collect_until_ready(rewake_workspace, rewake_only=True)

        self.assertEqual([item.process_id for item in ordinary], [ordinary_id])
        self.assertEqual(ordinary[0].system_message, "ordinary result")
        self.assertEqual(ordinary[0].additional_context, "")
        self.assertFalse(ordinary[0].rewake)
        self.assertEqual([item.process_id for item in rewake], [rewake_id])
        self.assertEqual(rewake[0].exit_code, 2)
        self.assertTrue(rewake[0].rewake)
        self.assertEqual(rewake[0].additional_context, "build failed")
        self.assertEqual(rewake[0].system_message, "")
        prompt = async_hook_notifications_prompt(rewake)
        self.assertIn("cannot grant approval", prompt)
        self.assertIn("build failed", prompt)

    def test_async_rewake_starts_an_idle_resumed_agent_turn(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-async-hook-") as base:
            root = Path(base)
            workspace, process_id = _start_direct_hook(
                root,
                script_body="printf '%s\\n' 'lint failed' >&2; exit 2",
                rewake=True,
            )
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                statuses = {
                    item.process_id: item
                    for item in list_background_processes(root).processes
                }
                if process_id in statuses and not statuses[process_id].running:
                    break
                time.sleep(0.02)
            run_agent_mock = Mock(return_value=SimpleNamespace(run_id="rewake-run"))

            def trigger_idle(_prompt, callback, *, input_func, interval_seconds=1.0):
                callback()
                return "/exit"

            with (
                patch(
                    "vibeagent.cli_interactive.input_with_idle_callback",
                    side_effect=trigger_idle,
                ),
                patch(
                    "vibeagent.cli_interactive.prompt_project_permission_trust",
                    return_value=False,
                ),
                patch("vibeagent.cli_interactive.print_agent_result"),
                patch("vibeagent.cli_interactive.Path.cwd", return_value=root),
                patch("sys.stdout", new_callable=StringIO) as stdout,
            ):
                exit_code = run_interactive_loop(
                    command_namespace={},
                    create_chat_client_func=Mock(return_value=object()),
                    run_agent_func=run_agent_mock,
                    get_resume_context_func=Mock(
                        return_value=("rewake-run", "next context", "loaded")
                    ),
                    initial_resume_run_id=workspace.run_id,
                    initial_resume_context="source context",
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("lint failed", run_agent_mock.call_args.args[0])
        self.assertEqual(
            run_agent_mock.call_args.kwargs["task_metadata"]["source"],
            "async_hook_rewake",
        )
        self.assertEqual(
            run_agent_mock.call_args.kwargs["task_metadata"]["asyncHookProcessIds"],
            [process_id],
        )
        self.assertIn("Asynchronous hook requested attention", stdout.getvalue())

    def test_collector_terminates_timed_out_hook_without_model_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-async-hook-") as base:
            root = Path(base)
            workspace, process_id = _start_direct_hook(
                root,
                script_body="sleep 5",
                rewake=True,
            )

            notifications = collect_async_hook_notifications(
                workspace,
                now=time.time() + 3,
            )
            state_path = next(
                (workspace.session_dir / "async-hooks").glob("*.json")
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in (workspace.session_dir / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        self.assertEqual(notifications, [])
        self.assertTrue(state["delivered"])
        completed = next(
            event
            for event in events
            if event["type"] == "async_hook_completed"
            and event["process_id"] == process_id
        )
        self.assertTrue(completed["timed_out"])
        self.assertFalse(completed["context_delivered"])

    def test_print_mode_teardown_cancels_running_async_hook(self) -> None:
        client = _AsyncHookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "Write",
                        "input": {"file_path": "app.py", "content": "x = 1\n"},
                    }
                ]
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-async-hook-") as base:
            root = Path(base)
            _write_hooks(
                root,
                "python3 -c 'import time; time.sleep(5)'",
                event="PreToolUse",
            )
            result = run_agent(
                "Write app.py",
                base_dir=root,
                client=client,
                max_iterations=1,
                approval_handler=_approve,
                defer_tool_calls=True,
                close_async_hooks_on_finish=True,
            )
            state_path = next(
                (
                    root
                    / ".vibeagent"
                    / "sessions"
                    / result.run_id
                    / "async-hooks"
                ).glob("*.json")
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            process_id = state["process_id"]
            events = [
                json.loads(line)
                for line in (
                    root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]
            record_after = read_persistent_process_record(root, process_id)

        self.assertTrue(state["delivered"])
        self.assertIsNone(record_after)
        self.assertTrue(
            any(
                event["type"] == "async_hook_cancelled"
                and event["process_id"] == process_id
                for event in events
            )
        )
        lifecycle = [event for event in events if event["type"] in {"hook_started", "hook_response"}]
        self.assertEqual([event["type"] for event in lifecycle], ["hook_started", "hook_response"])
        self.assertEqual(len({event["hook_id"] for event in lifecycle}), 1)
        self.assertEqual(lifecycle[-1]["outcome"], "cancelled")

    def test_interactive_exit_cancels_session_async_hooks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-async-hook-") as base:
            root = Path(base)
            workspace, process_id = _start_direct_hook(
                root,
                script_body="sleep 5",
                rewake=False,
            )
            with (
                patch(
                    "vibeagent.cli_interactive.input_with_idle_callback",
                    return_value="/exit",
                ),
                patch(
                    "vibeagent.cli_interactive.prompt_project_permission_trust",
                    return_value=False,
                ),
                patch("vibeagent.cli_interactive.Path.cwd", return_value=root),
                patch("sys.stdout", new_callable=StringIO),
            ):
                exit_code = run_interactive_loop(
                    command_namespace={},
                    create_chat_client_func=Mock(return_value=object()),
                    initial_resume_run_id=workspace.run_id,
                    initial_resume_context="source context",
                )
            state_path = next(
                (workspace.session_dir / "async-hooks").glob("*.json")
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            record_after = read_persistent_process_record(root, process_id)

        self.assertEqual(exit_code, 0)
        self.assertTrue(state["delivered"])
        self.assertIsNone(record_after)

    def test_async_hook_events_have_a_bounded_timeline_summary(self) -> None:
        event = SessionEvent(
            line_number=7,
            type="async_hook_completed",
            payload={
                "event": "PostToolUse",
                "target": "Write",
                "process_id": "hook-1",
                "exit_code": 2,
                "timed_out": False,
                "rewake": True,
            },
        )

        summary = format_session_event_timeline_item(event)

        self.assertIn("PostToolUse Write", summary)
        self.assertIn("processId=hook-1", summary)
        self.assertIn("exitCode=2", summary)
        self.assertIn("rewake=yes", summary)


if __name__ == "__main__":
    unittest.main()
