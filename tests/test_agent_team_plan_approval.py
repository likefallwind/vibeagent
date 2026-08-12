import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from vibeagent.action_parsing import ActionParseError, parse_tool_action
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.agent_delegate_tools import delegate_tool_definitions
from vibeagent.agent_execution_support import execute_action_safely
from vibeagent.agent_plan_approval import PlanApprovalError, prepare_plan_approval
from vibeagent.agent_special_tools import execute_special_tool_action
from vibeagent.agent_team_runtime import execute_teammate_coordination_action
from vibeagent.background_delegate_runtime import (
    execute_background_task_action,
    start_background_delegate_task,
)
from vibeagent.subagent_transcripts import read_subagent_transcript
from vibeagent.types import (
    ApprovalDecision,
    AssistantResponse,
    DelegateTaskObservation,
    SendMessageAction,
    TaskOutputAction,
)
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import ProjectHooks
from vibeagent.workspace_permissions import ProjectPermissions


class PlanTeamClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0
        self.messages = []
        self.tool_names = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        self.tool_names.append({str(tool["name"]) for tool in tools or []})
        content = self.responses[self.calls]
        self.calls += 1
        return AssistantResponse(content=content, raw={"content": content})


class AgentTeamPlanApprovalTests(unittest.TestCase):
    def _run_delegate(self, workspace, action, client):
        return execute_delegate_task_action(
            workspace,
            action,
            client,
            parent_iteration=1,
            subagent_id="planner",
            max_output_tokens=1024,
            model_retries=0,
            model_retry_delay_ms=0,
            model_timeout_ms=10_000,
            command_timeout_ms=10_000,
            logger=None,
            approval_handler=lambda _request: ApprovalDecision(True, "approved"),
        )

    def _send(self, workspace, action, client):
        return execute_special_tool_action(
            workspace,
            action,
            client,
            steps=[],
            observations=[],
            iteration=2,
            tool_name="SendMessage",
            max_output_tokens=1024,
            model_retries=0,
            model_retry_delay_ms=0,
            model_timeout_ms=10_000,
            command_timeout_ms=10_000,
            logger=None,
            approval_handler=lambda _request: ApprovalDecision(True, "approved"),
            approval_policy="ask",
            user_input_handler=None,
            hooks=ProjectHooks(),
            permissions=ProjectPermissions(),
            execute_action_safely_func=execute_action_safely,
        ).observation

    def _wait(self, workspace):
        return execute_background_task_action(
            workspace,
            TaskOutputAction(
                type="task_output",
                task_id="planner",
                block=True,
                timeout_ms=2_000,
            ),
        )

    def test_agent_plan_and_structured_approval_parse_strictly(self) -> None:
        action = parse_tool_action(
            "Agent",
            {"prompt": "Plan the change", "name": "planner", "mode": "plan"},
        )
        approval = parse_tool_action(
            "SendMessage",
            {"to": "planner", "message": "Approved as written.", "approve_plan": True},
        )

        self.assertEqual(action.mode, "plan")
        self.assertTrue(action.run_in_background)
        self.assertTrue(approval.approve_plan)
        with self.assertRaises(ActionParseError):
            parse_tool_action("Agent", {"prompt": "Plan", "mode": "plan"})
        with self.assertRaises(ActionParseError):
            parse_tool_action(
                "SendMessage",
                {"to": "planner", "message": "Approve", "approve_plan": "yes"},
            )

    def test_plan_mode_exposes_no_repository_mutation_tools(self) -> None:
        names = {
            str(tool["name"])
            for tool in delegate_tool_definitions(
                "plan",
                set(),
                "ask",
                nested_delegation_allowed=True,
                team_member=True,
            )
        }

        self.assertIn("Read", names)
        self.assertIn("SendMessage", names)
        self.assertNotIn("Write", names)
        self.assertNotIn("write_file", names)
        self.assertNotIn("Bash", names)
        self.assertNotIn("run_command", names)

    def test_plan_mode_rejects_hallucinated_write_call(self) -> None:
        client = PlanTeamClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-early",
                        "name": "write_file",
                        "input": {"path": "too-early.txt", "content": "no\n"},
                    }
                ],
                [{"type": "text", "text": "Plan only; no file was changed."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-plan-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            action = parse_tool_action(
                "Agent",
                {
                    "prompt": "Plan a file change",
                    "name": "planner",
                    "mode": "plan",
                    "max_iterations": 2,
                },
            )
            with patch.dict("os.environ", {"VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS": "1"}, clear=True):
                result = self._run_delegate(workspace, action, client)
            file_created = root.joinpath("too-early.txt").exists()

        self.assertTrue(result.ok)
        self.assertFalse(file_created)
        self.assertIn("not allowed in read-only delegation mode", str(client.messages[1]))

    def test_lead_approval_resumes_same_transcript_in_code_mode(self) -> None:
        client = PlanTeamClient(
            [
                [{"type": "text", "text": "Plan: create approved.txt, then verify it."}],
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "approved.txt", "content": "implemented\n"},
                    }
                ],
                [{"type": "text", "text": "Implemented and verified approved.txt."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-plan-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            action = parse_tool_action(
                "Agent",
                {"prompt": "Add approved.txt", "name": "planner", "mode": "plan", "max_iterations": 3},
            )
            with patch.dict("os.environ", {"VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS": "1"}, clear=True):
                planned = self._run_delegate(workspace, action, client)
                started = self._send(
                    workspace,
                    SendMessageAction(
                        type="send_message",
                        to="planner",
                        message="Approved as written.",
                        approve_plan=True,
                    ),
                    client,
                )
                completed = self._wait(workspace)
                transcript = read_subagent_transcript(workspace, "planner")

            self.assertTrue(planned.ok)
            self.assertIn("submitted a plan", planned.message)
            self.assertTrue(started.running)
            self.assertTrue(completed.completed)
            self.assertEqual(root.joinpath("approved.txt").read_text(encoding="utf-8"), "implemented\n")
            self.assertEqual(transcript.runs, 2)
            self.assertEqual(transcript.status, "completed")
            self.assertEqual(transcript.action.mode, "code")
            self.assertNotIn("write_file", client.tool_names[0])
            self.assertIn("write_file", client.tool_names[1])
            self.assertIn("lead approved your plan", str(client.messages[1]).lower())
            self.assertIn("focused coding subagent", str(client.messages[1][0].content))
            self.assertNotIn("read-only planning teammate", str(client.messages[1][0].content))

    def test_feedback_resumes_completed_plan_without_enabling_writes(self) -> None:
        client = PlanTeamClient(
            [
                [{"type": "text", "text": "Plan v1."}],
                [{"type": "text", "text": "Plan v2 includes rollback verification."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-plan-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action(
                "Agent",
                {"prompt": "Plan a migration", "name": "planner", "mode": "plan"},
            )
            with patch.dict("os.environ", {"VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS": "1"}, clear=True):
                self._run_delegate(workspace, action, client)
                started = self._send(
                    workspace,
                    SendMessageAction(
                        type="send_message",
                        to="planner",
                        message="Revise the plan to include rollback verification.",
                    ),
                    client,
                )
                completed = self._wait(workspace)
                transcript = read_subagent_transcript(workspace, "planner")

        self.assertTrue(started.running)
        self.assertTrue(completed.completed)
        self.assertEqual(transcript.runs, 2)
        self.assertEqual(transcript.action.mode, "plan")
        self.assertNotIn("write_file", client.tool_names[1])
        self.assertIn("rollback verification", str(client.messages[1]))

    def test_plan_approval_requires_completed_plan_teammate_and_lead(self) -> None:
        client = PlanTeamClient([[{"type": "text", "text": "Plan."}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-plan-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action(
                "Agent",
                {"prompt": "Plan", "name": "planner", "mode": "plan"},
            )
            with patch.dict("os.environ", {"VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS": "1"}, clear=True):
                self._run_delegate(workspace, action, client)
                transcript = read_subagent_transcript(workspace, "planner")
                with self.assertRaises(PlanApprovalError):
                    prepare_plan_approval(replace(transcript, status="running"), "Approve")
                with self.assertRaises(PlanApprovalError):
                    prepare_plan_approval(
                        replace(transcript, action=replace(transcript.action, mode="code")),
                        "Approve",
                    )
                denied = execute_teammate_coordination_action(
                    workspace,
                    SendMessageAction(
                        type="send_message",
                        to="planner",
                        message="Approve",
                        approve_plan=True,
                    ),
                    "reviewer",
                )

        self.assertEqual(denied.kind, "tool_error")
        self.assertIn("Only the lead", denied.message)

    def test_lead_cannot_approve_plan_while_teammate_is_running(self) -> None:
        client = PlanTeamClient([[{"type": "text", "text": "Plan."}]])
        release = threading.Event()

        def runner(task_id, _cancel_requested, _inbound_messages):
            release.wait(1)
            return DelegateTaskObservation(
                kind="delegate_task",
                ok=True,
                task="Plan",
                summary="Revised plan.",
                iterations=1,
                tool_calls=[],
                message="done",
                mode="plan",
                task_id=task_id,
                teammate_name="planner",
            )

        with tempfile.TemporaryDirectory(prefix="vibeagent-team-plan-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action(
                "Agent",
                {"prompt": "Plan", "name": "planner", "mode": "plan"},
            )
            with patch.dict("os.environ", {"VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS": "1"}, clear=True):
                self._run_delegate(workspace, action, client)
                start_background_delegate_task(
                    workspace,
                    action,
                    runner,
                    task_id="planner",
                    resumed=True,
                )
                denied = self._send(
                    workspace,
                    SendMessageAction(
                        type="send_message",
                        to="planner",
                        message="Approve",
                        approve_plan=True,
                    ),
                    client,
                )
                release.set()
                self._wait(workspace)

        self.assertEqual(denied.kind, "tool_error")
        self.assertIn("status is running", denied.message)


if __name__ == "__main__":
    unittest.main()
