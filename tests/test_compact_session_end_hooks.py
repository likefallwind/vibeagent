from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from typing import cast
from unittest.mock import Mock, patch

from vibeagent.agent_hook_results import HookRunResult
from vibeagent.agent_lifecycle_runtime import AgentLifecycleRuntime
from vibeagent.agent_runtime_utils import compact_agent_message_history
from vibeagent.agent import run_agent
from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.cli_session_local_flags import run_interactive_resume_command
from vibeagent.session_lifecycle_hooks import run_session_end_hooks
from vibeagent.types import AssistantResponse, ChatMessage
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hook_types import HookEvent, ProjectHook, ProjectHooks
from vibeagent.workspace_hooks import read_project_hooks
from vibeagent.workspace_permissions import ProjectPermissions


def _hook_result(event: str) -> HookRunResult:
    return HookRunResult(
        event=event,
        command="hook",
        source="test",
        status="passed",
        ok=True,
        exit_code=0,
        timed_out=False,
        stdout="",
        stderr="",
        message="passed",
    )


def _hook(event: str, matcher: str = ".*") -> ProjectHook:
    return ProjectHook(
        event=cast(HookEvent, event),
        matcher=matcher,
        command="hook",
        timeout_ms=10_000,
        source="test",
    )


def _write_hooks(root: Path, payload: dict[str, object]) -> None:
    path = root / ".vibeagent" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class CompactSessionEndHookConfigTests(unittest.TestCase):
    def test_loads_events_and_uses_session_end_default_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-lifecycle-hook-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "PreCompact": [
                        {"matcher": "auto", "hooks": [{"type": "command", "command": "true"}]}
                    ],
                    "PostCompact": [
                        {"matcher": "manual", "hooks": [{"type": "command", "command": "true"}]}
                    ],
                    "SessionEnd": [
                        {"matcher": "other", "hooks": [{"type": "command", "command": "true"}]}
                    ],
                },
            )
            config = read_project_hooks(create_run_workspace(root))

        self.assertIsNone(config.error)
        self.assertEqual(
            {hook.event for hook in config.hooks},
            {"PreCompact", "PostCompact", "SessionEnd"},
        )
        session_end = next(hook for hook in config.hooks if hook.event == "SessionEnd")
        self.assertEqual(session_end.timeout_ms, 1_500)
        self.assertTrue(config.requires_sequential_tools)

    def test_model_handlers_are_rejected_for_non_decision_lifecycle_events(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-lifecycle-hook-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "SessionEnd": [
                        {
                            "hooks": [
                                {"type": "prompt", "prompt": "Review $ARGUMENTS"}
                            ]
                        }
                    ]
                },
            )
            config = read_project_hooks(create_run_workspace(root))

        self.assertIn("do not support prompt handlers", config.error or "")

    def test_invalid_manual_compact_does_not_fire_lifecycle_callbacks(self) -> None:
        before = Mock()
        after = Mock()
        getter = Mock()
        result = run_interactive_resume_command(
            SimpleNamespace(type="compact", argument="--bad"),
            {
                "parse_interactive_session_detail_argument": lambda *args: (
                    None,
                    {},
                    "invalid compact arguments",
                ),
                "get_compact_context": getter,
            },
            before_compact=before,
            after_compact=after,
        )

        self.assertEqual(result, (None, None, "invalid compact arguments"))
        before.assert_not_called()
        after.assert_not_called()
        getter.assert_not_called()


class CompactSessionEndHookRuntimeTests(unittest.TestCase):
    def test_auto_compaction_runs_pre_and_post_with_summary(self) -> None:
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
                side_effect=(_hook_result("PreCompact"), _hook_result("PostCompact")),
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

        self.assertIsNot(compacted, messages)
        self.assertEqual(run_hook.call_count, 2)
        pre_input = run_hook.call_args_list[0].kwargs["hook_input"]
        post_input = run_hook.call_args_list[1].kwargs["hook_input"]
        self.assertEqual(pre_input["hook_event_name"], "PreCompact")
        self.assertEqual(pre_input["trigger"], "auto")
        self.assertEqual(pre_input["custom_instructions"], "")
        self.assertEqual(post_input["hook_event_name"], "PostCompact")
        self.assertEqual(post_input["trigger"], "auto")
        self.assertIn("Compacted current-run context", post_input["compact_summary"])

    def test_main_agent_auto_compaction_runs_configured_hooks(self) -> None:
        client = Mock()
        client.complete.return_value = AssistantResponse(
            content=[{"type": "text", "text": "done"}],
            raw={},
        )
        prior_messages = [
            ChatMessage(
                role="user" if index % 2 == 0 else "assistant",
                content=f"history {index}",
            )
            for index in range(20)
        ]
        with tempfile.TemporaryDirectory(prefix="vibeagent-lifecycle-hook-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "PreCompact": [
                        {"matcher": "auto", "hooks": [{"type": "command", "command": "true"}]}
                    ],
                    "PostCompact": [
                        {"matcher": "auto", "hooks": [{"type": "command", "command": "true"}]}
                    ],
                },
            )
            with patch(
                "vibeagent.agent_lifecycle_hooks.run_project_hook",
                side_effect=(_hook_result("PreCompact"), _hook_result("PostCompact")),
            ) as run_hook:
                result = run_agent(
                    "continue",
                    base_dir=root,
                    client=client,
                    prior_messages=prior_messages,
                    max_iterations=1,
                )

        self.assertTrue(result.success)
        self.assertEqual(
            [call.kwargs["hook_input"]["hook_event_name"] for call in run_hook.call_args_list],
            ["PreCompact", "PostCompact"],
        )

    def test_session_end_matches_reason_and_exposes_reason_input(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-lifecycle-hook-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "SessionEnd": [
                        {
                            "matcher": "other",
                            "hooks": [{"type": "command", "command": "true"}],
                        }
                    ]
                },
            )
            workspace = create_run_workspace(root)
            with patch(
                "vibeagent.agent_lifecycle_hooks.run_project_hook",
                return_value=_hook_result("SessionEnd"),
            ) as run_hook:
                results = run_session_end_hooks(
                    workspace,
                    "other",
                    command_timeout_ms=30_000,
                    approval_handler=None,
                    approval_policy="ask",
                )

        self.assertEqual(len(results), 1)
        hook = run_hook.call_args.args[1]
        hook_input = run_hook.call_args.kwargs["hook_input"]
        self.assertEqual(hook.timeout_ms, 1_500)
        self.assertEqual(hook_input["hook_event_name"], "SessionEnd")
        self.assertEqual(hook_input["reason"], "other")

    def test_session_end_handlers_share_budget_and_honor_bounded_override(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-lifecycle-hook-") as base:
            workspace = create_run_workspace(base)
            runtime = AgentLifecycleRuntime(
                hooks=ProjectHooks(
                    hooks=(_hook("SessionEnd", "other"), _hook("SessionEnd", "other"))
                ),
                permissions=ProjectPermissions(),
                command_timeout_ms=30_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                execute_action_safely=Mock(),
            )
            with (
                patch(
                    "vibeagent.agent_lifecycle_hooks.time.monotonic",
                    side_effect=(0.0, 0.0, 11.0),
                ),
                patch(
                    "vibeagent.agent_lifecycle_hooks.run_project_hook",
                    return_value=_hook_result("SessionEnd"),
                ) as run_hook,
            ):
                runtime.end(workspace, "other")

            self.assertEqual(run_hook.call_count, 1)

            runtime = AgentLifecycleRuntime(
                hooks=ProjectHooks(hooks=(_hook("SessionEnd", "other"),)),
                permissions=ProjectPermissions(),
                command_timeout_ms=30_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                execute_action_safely=Mock(),
            )
            with (
                patch.dict(
                    "os.environ",
                    {"CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS": "5000"},
                ),
                patch(
                    "vibeagent.agent_lifecycle_hooks.time.monotonic",
                    side_effect=(0.0, 0.0),
                ),
                patch(
                    "vibeagent.agent_lifecycle_hooks.run_project_hook",
                    return_value=_hook_result("SessionEnd"),
                ) as run_hook,
            ):
                runtime.end(workspace, "other")

        self.assertEqual(run_hook.call_args.args[1].timeout_ms, 5_000)

    def test_interactive_manual_compact_and_clear_fire_lifecycle_hooks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-lifecycle-hook-") as base:
            root = Path(base)
            with (
                patch(
                    "vibeagent.cli_interactive.input_with_idle_callback",
                    side_effect=["/compact run-1", "/clear", "/exit"],
                ),
                patch(
                    "vibeagent.session_lifecycle_hooks.run_compact_hooks"
                ) as compact_hooks,
                patch(
                    "vibeagent.session_lifecycle_hooks.run_session_end_hooks"
                ) as session_end,
                patch(
                    "vibeagent.cli_interactive.prompt_project_permission_trust",
                    return_value=False,
                ),
                patch("vibeagent.cli_interactive.Path.cwd", return_value=root),
                patch("sys.stdout", new_callable=StringIO),
            ):
                exit_code = run_interactive_loop(
                    command_namespace={
                        "parse_interactive_session_detail_argument": (
                            lambda *args, **kwargs: ("run-1", {}, None)
                        ),
                        "get_compact_context": lambda *args, **kwargs: (
                            "run-1",
                            "compact summary",
                            "Compacted.",
                        ),
                    },
                    create_chat_client_func=Mock(return_value=object()),
                    initial_resume_run_id="run-1",
                    initial_resume_context="source context",
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            [call.args[1] for call in compact_hooks.call_args_list],
            ["pre", "post"],
        )
        self.assertEqual(compact_hooks.call_args_list[0].kwargs["trigger"], "manual")
        self.assertEqual(
            compact_hooks.call_args_list[1].kwargs["summary"], "compact summary"
        )
        self.assertEqual(session_end.call_count, 1)
        self.assertEqual(session_end.call_args.args[1], "clear")

    def test_interactive_exit_and_session_switch_report_end_reasons(self) -> None:
        cases = (
            (["/exit"], None, ["prompt_input_exit"]),
            (
                ["/resume run-2", "/exit"],
                ("run-2", "next context", "Resumed."),
                ["resume", "prompt_input_exit"],
            ),
        )
        for inputs, resume_result, expected in cases:
            with self.subTest(inputs=inputs):
                with tempfile.TemporaryDirectory(
                    prefix="vibeagent-lifecycle-hook-"
                ) as base:
                    root = Path(base)
                    with (
                        patch(
                            "vibeagent.cli_interactive.input_with_idle_callback",
                            side_effect=inputs,
                        ),
                        patch(
                            "vibeagent.cli_interactive.run_interactive_resume_command",
                            return_value=resume_result,
                        ),
                        patch(
                            "vibeagent.session_lifecycle_hooks.run_session_end_hooks"
                        ) as session_end,
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
                            initial_resume_run_id="run-1",
                            initial_resume_context="source context",
                        )

                self.assertEqual(exit_code, 0)
                self.assertEqual(
                    [call.args[1] for call in session_end.call_args_list], expected
                )


if __name__ == "__main__":
    unittest.main()
