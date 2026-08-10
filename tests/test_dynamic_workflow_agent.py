from __future__ import annotations

from pathlib import Path
from threading import Event
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.config_execution import ExecutionConfig
from vibeagent.dynamic_workflow_agent import background_workflow_approval_handler, execute_workflow_agent_request
from vibeagent.dynamic_workflow_types import WorkflowAgentRequest
from vibeagent.types import ApprovalDecision, ApprovalRequest, DelegateTaskObservation
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_hooks import ProjectHooks
from vibeagent.workspace_permissions import ProjectPermissions


class DynamicWorkflowAgentTests(unittest.TestCase):
    def test_ask_policy_denies_background_prompt_but_allow_policy_is_preserved(self) -> None:
        original = lambda _request: ApprovalDecision(approved=True, message="approved")
        request = ApprovalRequest(action_type="write_file", target="src/app.py", risk="write")

        ask_handler = background_workflow_approval_handler("ask", original)
        self.assertIsNotNone(ask_handler)
        decision = ask_handler(request)  # type: ignore[misc]
        self.assertFalse(decision.approved)
        self.assertIn("cannot open an interactive approval prompt", decision.message or "")
        self.assertIs(background_workflow_approval_handler("allow", original), original)

    def test_request_uses_existing_delegate_runtime_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workflow-agent-") as base:
            workspace = create_run_workspace(Path(base), run_id="run-1")
            request = WorkflowAgentRequest(
                call_id="call-0007",
                workflow_id="workflow-123456789abc",
                task="implement the parser",
                context="focus on src/parser.py",
                mode="code",
                agent="reviewer",
                max_iterations=6,
                isolation="worktree",
            )
            observation = DelegateTaskObservation(
                kind="delegate_task",
                ok=True,
                task=request.task,
                summary="done",
                iterations=2,
                tool_calls=["Read"],
                message="completed",
                mode="code",
                agent="reviewer",
                isolation="worktree",
            )
            cancel_event = Event()

            with patch(
                "vibeagent.dynamic_workflow_agent.execute_delegate_task_action",
                return_value=observation,
            ) as execute:
                result = execute_workflow_agent_request(
                    workspace,
                    request,
                    object(),
                    execution_config=ExecutionConfig(),
                    approval_handler=None,
                    approval_policy="ask",
                    hooks=ProjectHooks(),
                    permissions=ProjectPermissions(),
                    cancel_requested=cancel_event.is_set,
                )

            action = execute.call_args.args[1]
            self.assertEqual(action.task, request.task)
            self.assertEqual(action.context, request.context)
            self.assertEqual(action.mode, "code")
            self.assertEqual(action.isolation, "worktree")
            self.assertEqual(execute.call_args.kwargs["subagent_id"], "wf-123456789abc-call-0007")
            self.assertEqual(execute.call_args.kwargs["approval_policy"], "ask")
            self.assertEqual(result["summary"], "done")


if __name__ == "__main__":
    unittest.main()
