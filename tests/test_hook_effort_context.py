from __future__ import annotations

import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent.actions import parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.agent_execution_support import execute_action_safely
from vibeagent.agent_hook_prompt import HookModelRuntime
from vibeagent.agent_hook_results import HookRunResult
from vibeagent.agent_lifecycle_hooks import run_lifecycle_hooks
from vibeagent.agent_tool_hook_runtime import run_tool_hook_handler
from vibeagent.model_effort import active_model_effort
from vibeagent.types import ApprovalDecision, AssistantResponse
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hook_types import ProjectHook, ProjectHooks
from vibeagent.workspace_permissions import ProjectPermissions


HOOK_COMMAND = "python3 -c " + shlex.quote(
    "import json,os,sys; d=json.load(sys.stdin); "
    "print(json.dumps({'input':d.get('effort'),'env':os.getenv('CLAUDE_EFFORT')}))"
)


class EffortClient:
    def __init__(
        self,
        responses: list[list[dict[str, object]]],
        *,
        root: "EffortClient | None" = None,
        effort: str | None = None,
    ) -> None:
        self.responses = responses
        self.root = root or self
        self.effort = effort
        if root is None:
            self.calls = 0

    def with_agent_profile(self, *, model: str | None, effort: str | None):
        return EffortClient(
            self.responses,
            root=self.root,
            effort=self.effort if effort is None else effort,
        )

    def complete(self, messages, tools=None, **kwargs):
        index = self.root.calls
        self.root.calls += 1
        content = self.responses[index]
        return AssistantResponse(content=content, raw={"content": content})


def _model_runtime(effort: str | None) -> HookModelRuntime:
    return HookModelRuntime(
        client=Mock(),
        complete_with_retries=Mock(),
        max_output_tokens=1024,
        model_retries=0,
        model_retry_delay_ms=0,
        effort=effort,
    )


def _hook(event: str, matcher: str = ".*") -> ProjectHook:
    return ProjectHook(
        event=event,  # type: ignore[arg-type]
        matcher=matcher,
        command=HOOK_COMMAND,
        timeout_ms=10_000,
        source="test",
    )


def _write_hooks(root: Path, event: str, matcher: str = ".*") -> None:
    path = root / ".vibeagent" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                event: [
                    {
                        "matcher": matcher,
                        "hooks": [{"type": "command", "command": HOOK_COMMAND}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def _hook_response(root: Path, run_id: str, event: str) -> dict[str, object]:
    events = [
        json.loads(line)
        for line in root.joinpath(
            ".vibeagent", "sessions", run_id, "events.jsonl"
        ).read_text(encoding="utf-8").splitlines()
    ]
    return next(
        item
        for item in events
        if item.get("type") == "hook_response" and item.get("event") == event
    )


def _passed_hook_result(event: str) -> HookRunResult:
    return HookRunResult(
        event=event,  # type: ignore[arg-type]
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


def _approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


class HookEffortContextTests(unittest.TestCase):
    def test_resolves_effort_through_client_wrappers_and_cycles(self) -> None:
        leaf = EffortClient([], effort="xhigh")
        wrapped = type("BudgetWrapper", (), {"client": leaf})()
        fallback = type("FallbackWrapper", (), {"primary": wrapped})()
        cycle = type("CycleWrapper", (), {})()
        cycle.client = cycle
        dynamic = Mock()

        self.assertEqual(active_model_effort(fallback), "xhigh")
        self.assertIsNone(active_model_effort(EffortClient([])))
        self.assertIsNone(active_model_effort(cycle))
        self.assertIsNone(active_model_effort(dynamic))
        self.assertEqual(dynamic._mock_children, {})

    def test_tool_hook_command_receives_effort_input_and_environment(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-hook-effort-") as base:
            workspace = create_run_workspace(base)
            action = parse_tool_action("Read", {"file_path": "README.md"})
            result = run_tool_hook_handler(
                workspace,
                _hook("PreToolUse", "Read"),
                "Read",
                action,
                {"file_path": "README.md"},
                "tool-1",
                1,
                1,
                10_000,
                None,
                _approve,
                "allow",
                execute_action_safely,
                ProjectPermissions(),
                _model_runtime("high"),
            )

        self.assertTrue(result.ok)
        self.assertEqual(
            json.loads(result.stdout),
            {"input": {"level": "high"}, "env": "high"},
        )

    def test_tool_and_non_stop_lifecycle_hooks_omit_unknown_effort(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-hook-effort-") as base:
            workspace = create_run_workspace(base)
            action = parse_tool_action("Read", {"file_path": "README.md"})
            with patch(
                "vibeagent.agent_tool_hook_runtime.run_project_hook",
                return_value=_passed_hook_result("PreToolUse"),
            ) as run_tool_hook:
                run_tool_hook_handler(
                    workspace,
                    _hook("PreToolUse", "Read"),
                    "Read",
                    action,
                    {"file_path": "README.md"},
                    None,
                    1,
                    1,
                    10_000,
                    None,
                    None,
                    "ask",
                    Mock(),
                    ProjectPermissions(),
                    _model_runtime(None),
                )
            with patch(
                "vibeagent.agent_lifecycle_hooks.run_project_hook",
                return_value=_passed_hook_result("SessionStart"),
            ) as run_lifecycle:
                run_lifecycle_hooks(
                    workspace,
                    ProjectHooks(hooks=(_hook("SessionStart", "startup"),)),
                    "SessionStart",
                    "startup",
                    {"source": "startup"},
                    iteration=0,
                    command_timeout_ms=10_000,
                    logger=None,
                    approval_handler=None,
                    approval_policy="ask",
                    execute_action_safely_func=Mock(),
                    permissions=ProjectPermissions(),
                    hook_model_runtime=_model_runtime("max"),
                )

        self.assertNotIn("effort", run_tool_hook.call_args.kwargs["hook_input"])
        self.assertNotIn("CLAUDE_EFFORT", run_tool_hook.call_args.kwargs["environment"])
        self.assertNotIn("effort", run_lifecycle.call_args.kwargs["hook_input"])
        self.assertNotIn("CLAUDE_EFFORT", run_lifecycle.call_args.kwargs["environment"])

    def test_main_stop_hook_receives_active_effort(self) -> None:
        client = EffortClient(
            [[{"type": "text", "text": "Completed."}]],
            effort="medium",
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-hook-effort-") as base:
            root = Path(base)
            _write_hooks(root, "Stop")
            result = run_agent(
                "Inspect",
                client,
                base_dir=root,
                approval_policy="allow",
                approval_handler=_approve,
                max_iterations=1,
                model_retries=0,
            )
            response = _hook_response(root, result.run_id, "Stop")

        self.assertTrue(result.success)
        self.assertEqual(
            json.loads(str(response["stdout"])),
            {"input": {"level": "medium"}, "env": "medium"},
        )

    def test_subagent_stop_hook_receives_profile_effort(self) -> None:
        client = EffortClient([[{"type": "text", "text": "Evidence collected."}]], effort="low")
        with tempfile.TemporaryDirectory(prefix="vibeagent-hook-effort-") as base:
            root = Path(base)
            profile = root / ".claude" / "agents" / "reviewer.md"
            profile.parent.mkdir(parents=True, exist_ok=True)
            profile.write_text(
                "---\nname: reviewer\ndescription: Review code\nmode: explore\n"
                "effort: high\n---\n\nReview carefully.\n",
                encoding="utf-8",
            )
            _write_hooks(root, "SubagentStop", "reviewer")
            workspace = create_run_workspace(root, run_id="delegate-effort")
            action = parse_tool_action(
                "delegate_task",
                {"task": "Inspect", "agent": "reviewer", "max_iterations": 1},
            )
            observation = execute_delegate_task_action(
                workspace,
                action,
                client,
                parent_iteration=1,
                subagent_id="delegate-1-1",
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=_approve,
                approval_policy="allow",
                hooks=ProjectHooks(hooks=(_hook("SubagentStop", "reviewer"),)),
            )
            response = _hook_response(root, workspace.run_id, "SubagentStop")

        self.assertTrue(observation.ok)
        self.assertEqual(
            json.loads(str(response["stdout"])),
            {"input": {"level": "high"}, "env": "high"},
        )


if __name__ == "__main__":
    unittest.main()
