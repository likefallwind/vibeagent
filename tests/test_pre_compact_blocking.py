from __future__ import annotations

from dataclasses import replace
from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from typing import cast
from unittest.mock import Mock, patch

from vibeagent.agent_delegate_context import compact_delegate_message_history
from vibeagent.agent_delegate_hooks import DelegateLifecycleHooks
from vibeagent.agent_hook_results import HookRunResult
from vibeagent.agent_lifecycle_runtime import AgentLifecycleRuntime
from vibeagent.agent_runtime_utils import compact_agent_message_history
from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.cli_session_local_flags import CompactBlocked, run_interactive_resume_command
from vibeagent.types import ChatMessage, DelegateTaskAction
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hook_types import HookEvent, ProjectHook, ProjectHooks
from vibeagent.workspace_permissions import ProjectPermissions


def _hook(event: str, matcher: str = ".*") -> ProjectHook:
    return ProjectHook(
        event=cast(HookEvent, event),
        matcher=matcher,
        command="hook",
        timeout_ms=10_000,
        source="test",
    )


def _hook_result(event: str, stdout: str = "") -> HookRunResult:
    return HookRunResult(
        event=event,
        command="hook",
        source="test",
        status="passed",
        ok=True,
        exit_code=0,
        timed_out=False,
        stdout=stdout,
        stderr="",
        message="passed",
    )


def _blocking_hook_result(
    event: str,
    reason: str,
    *,
    structured: bool = False,
) -> HookRunResult:
    return HookRunResult(
        event=event,
        command="hook",
        source="test",
        status="passed" if structured else "blocked",
        ok=structured,
        exit_code=0 if structured else 2,
        timed_out=False,
        stdout=json.dumps({"decision": "block", "reason": reason}) if structured else "",
        stderr="" if structured else reason,
        message=reason,
    )


def _events(workspace) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (workspace.session_dir / "events.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]


class PreCompactBlockingTests(unittest.TestCase):
    def test_blocked_manual_compact_does_not_build_summary(self) -> None:
        getter = Mock()
        after = Mock()

        result = run_interactive_resume_command(
            SimpleNamespace(type="compact", argument=None),
            {
                "parse_interactive_session_detail_argument": lambda *args: (
                    None,
                    {},
                    None,
                ),
                "get_compact_context": getter,
            },
            before_compact=lambda: "Preserve the current context.",
            after_compact=after,
        )

        self.assertEqual(result, CompactBlocked("Preserve the current context."))
        getter.assert_not_called()
        after.assert_not_called()

    def test_exit_two_preserves_main_history_and_skips_post_hook(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-lifecycle-hook-") as base:
            workspace = create_run_workspace(base)
            runtime = AgentLifecycleRuntime(
                hooks=ProjectHooks(
                    hooks=(_hook("PreCompact", "auto"), _hook("PostCompact", "auto"))
                ),
                permissions=ProjectPermissions(),
                command_timeout_ms=30_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                execute_action_safely=Mock(),
            )
            messages = [
                ChatMessage(role="system", content="system"),
                ChatMessage(role="user", content="task"),
                ChatMessage(role="assistant", content="old response"),
            ]
            with patch(
                "vibeagent.agent_lifecycle_hooks.run_project_hook",
                return_value=_blocking_hook_result(
                    "PreCompact", "Keep the full debugging transcript."
                ),
            ) as run_hook:
                compacted = compact_agent_message_history(
                    "task",
                    workspace,
                    messages,
                    [],
                    [],
                    None,
                    3,
                    threshold=1,
                    compact_hook_runner=lambda phase, trigger, summary: runtime.compact(
                        workspace,
                        phase,
                        trigger,
                        summary,
                        iteration=3,
                    ),
                )
            events = _events(workspace)

        self.assertIs(compacted, messages)
        self.assertEqual(run_hook.call_count, 1)
        self.assertEqual(run_hook.call_args.kwargs["hook_input"]["trigger"], "auto")
        blocked = next(event for event in events if event["type"] == "context_compaction_blocked")
        self.assertEqual(blocked["reason"], "Keep the full debugging transcript.")
        self.assertNotIn("context_compacted", {event["type"] for event in events})

    def test_universal_stop_uses_stop_reason(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-lifecycle-hook-") as base:
            workspace = create_run_workspace(base)
            runtime = AgentLifecycleRuntime(
                hooks=ProjectHooks(hooks=(_hook("PreCompact", "auto"),)),
                permissions=ProjectPermissions(),
                command_timeout_ms=30_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                execute_action_safely=Mock(),
            )
            result = replace(
                _hook_result("PreCompact"),
                stdout=json.dumps(
                    {
                        "continue": False,
                        "stopReason": "Compaction is disabled during incident response.",
                    }
                ),
            )
            with patch(
                "vibeagent.agent_lifecycle_hooks.run_project_hook",
                return_value=result,
            ):
                reason = runtime.compact(
                    workspace,
                    "pre",
                    "auto",
                    None,
                    iteration=4,
                )

        self.assertEqual(reason, "Compaction is disabled during incident response.")

    def test_structured_block_reaches_subagent_and_preserves_history(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-lifecycle-hook-") as base:
            workspace = create_run_workspace(base)
            action = DelegateTaskAction(
                type="delegate_task",
                task="Investigate",
                mode="explore",
                max_iterations=3,
            )
            lifecycle = DelegateLifecycleHooks(
                workspace=workspace,
                action=action,
                subagent_id="delegate-1-1",
                hooks=ProjectHooks(
                    hooks=(_hook("PreCompact", "auto"), _hook("PostCompact", "auto"))
                ),
                command_timeout_ms=30_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                permissions=ProjectPermissions(),
            )
            messages = [
                ChatMessage(role="system", content="system"),
                ChatMessage(role="user", content="task"),
                ChatMessage(role="assistant", content="evidence"),
            ]
            with patch(
                "vibeagent.agent_lifecycle_hooks.run_project_hook",
                return_value=_blocking_hook_result(
                    "PreCompact", "Subagent evidence is still needed.", structured=True
                ),
            ) as run_hook:
                compacted = compact_delegate_message_history(
                    workspace,
                    action,
                    messages,
                    [],
                    parent_iteration=1,
                    child_iteration=2,
                    subagent_id="delegate-1-1",
                    threshold=1,
                    compact_hook_runner=lambda phase, trigger, summary: lifecycle.compact(
                        phase,
                        trigger,
                        summary,
                        iteration=2,
                    ),
                )
            hook_input = run_hook.call_args.kwargs["hook_input"]
            events = _events(workspace)

        self.assertIs(compacted, messages)
        self.assertEqual(run_hook.call_count, 1)
        self.assertEqual(run_hook.call_args.kwargs["target"], "auto")
        self.assertEqual(hook_input["agent_id"], "delegate-1-1")
        self.assertEqual(hook_input["agent_type"], "Explore")
        self.assertEqual(hook_input["trigger"], "auto")
        blocked = next(
            event for event in events if event["type"] == "subagent_context_compaction_blocked"
        )
        self.assertEqual(blocked["reason"], "Subagent evidence is still needed.")
        self.assertNotIn("subagent_context_compacted", {event["type"] for event in events})

    def test_interactive_block_keeps_active_session(self) -> None:
        compact_context = Mock()
        with tempfile.TemporaryDirectory(prefix="vibeagent-lifecycle-hook-") as base:
            root = Path(base)
            with (
                patch(
                    "vibeagent.cli_interactive.input_with_idle_callback",
                    side_effect=["/compact run-1", "/exit"],
                ),
                patch(
                    "vibeagent.session_lifecycle_hooks.run_compact_hooks",
                    return_value="Keep the active investigation context.",
                ) as compact_hooks,
                patch(
                    "vibeagent.session_lifecycle_hooks.run_session_end_hooks"
                ) as session_end,
                patch(
                    "vibeagent.cli_interactive.prompt_project_permission_trust",
                    return_value=False,
                ),
                patch("vibeagent.cli_interactive.Path.cwd", return_value=root),
                patch("sys.stdout", new_callable=StringIO) as stdout,
            ):
                exit_code = run_interactive_loop(
                    command_namespace={
                        "parse_interactive_session_detail_argument": (
                            lambda *args, **kwargs: ("run-1", {}, None)
                        ),
                        "get_compact_context": compact_context,
                    },
                    create_chat_client_func=Mock(return_value=object()),
                    initial_resume_run_id="run-1",
                    initial_resume_context="source context",
                )

        self.assertEqual(exit_code, 0)
        compact_context.assert_not_called()
        self.assertEqual([call.args[1] for call in compact_hooks.call_args_list], ["pre"])
        self.assertIn(
            "Compaction blocked by PreCompact hook: Keep the active investigation context.",
            stdout.getvalue(),
        )
        self.assertEqual(session_end.call_count, 1)
        self.assertEqual(session_end.call_args.args[1], "prompt_input_exit")


if __name__ == "__main__":
    unittest.main()
