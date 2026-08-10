import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.action_parsing import parse_tool_action
from vibeagent.agent_approval import build_approval_request
from vibeagent.agent_background_notifications import inject_background_delegate_notifications
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.agent_delegate_tools import code_delegate_initial_tool_names, delegate_tool_definitions
from vibeagent.agent_special_tools import execute_special_tool_action
from vibeagent.agent_team_runtime import (
    clear_team_runtime,
    execute_teammate_coordination_action,
    teammate_spawn_error,
)
from vibeagent.nested_delegate_runtime import NestedDelegateRuntime
from vibeagent.background_delegate_runtime import start_background_delegate_task
from vibeagent.background_delegate_runtime import execute_background_task_action
from vibeagent.session_tasks import create_session_task, get_session_task, update_session_task
from vibeagent.subagent_listing import list_session_agents
from vibeagent.types import (
    AssistantResponse,
    ApprovalDecision,
    ChatMessage,
    DelegateTaskAction,
    DelegateTaskObservation,
    SendMessageAction,
    TaskCreateAction,
    TaskOutputAction,
)
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import ProjectHooks
from vibeagent.workspace_permissions import ProjectPermissions


class TeamClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0
        self.tool_names = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.tool_names.append([str(tool["name"]) for tool in tools or []])
        content = self.responses[self.calls]
        self.calls += 1
        return AssistantResponse(content=content, raw={"content": content})


class AgentTeamTests(unittest.TestCase):
    def test_agent_alias_parses_named_teammate_and_requires_spawn_approval(self) -> None:
        action = parse_tool_action(
            "Agent",
            {
                "prompt": "Review authentication",
                "name": "reviewer",
                "team_name": "ignored-name",
                "mode": "code",
            },
        )
        approval = build_approval_request(action)

        self.assertEqual(action.teammate_name, "reviewer")
        self.assertTrue(action.run_in_background)
        self.assertEqual(approval.action_type, "spawn_teammate")
        self.assertEqual(approval.target, "reviewer")
        with self.assertRaises(ValueError):
            parse_tool_action("Agent", {"prompt": "Invalid", "name": "lead"})

    def test_disabled_team_fails_before_model_request(self) -> None:
        client = TeamClient([])
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action(
                "Agent",
                {"prompt": "Review authentication", "name": "reviewer"},
            )
            with patch.dict("os.environ", {}, clear=True):
                result = execute_delegate_task_action(
                    workspace,
                    action,
                    client,
                    parent_iteration=1,
                    subagent_id="reviewer",
                    max_output_tokens=1024,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                )

        self.assertFalse(result.ok)
        self.assertIn("EXPERIMENTAL_AGENT_TEAMS", result.message)
        self.assertEqual(client.calls, 0)

    def test_teammate_identity_must_match_stable_task_id(self) -> None:
        client = TeamClient([])
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action(
                "Agent",
                {"prompt": "Review authentication", "name": "reviewer"},
            )
            with patch.dict("os.environ", {"VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS": "1"}, clear=True):
                result = execute_delegate_task_action(
                    workspace,
                    action,
                    client,
                    parent_iteration=1,
                    subagent_id="different-id",
                    max_output_tokens=1024,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                )

        self.assertFalse(result.ok)
        self.assertIn("stable background task ID", result.message)
        self.assertEqual(client.calls, 0)

    def test_teammate_spawn_denial_prevents_background_worker(self) -> None:
        client = TeamClient([])
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action(
                "Agent",
                {"prompt": "Review authentication", "name": "reviewer"},
            )
            with patch.dict("os.environ", {"VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS": "1"}, clear=True):
                wrapped = execute_special_tool_action(
                    workspace,
                    action,
                    client,
                    steps=[],
                    observations=[],
                    iteration=1,
                    tool_name="Agent",
                    max_output_tokens=1024,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                    approval_handler=lambda _request: ApprovalDecision(
                        approved=False,
                        message="team spawn denied",
                    ),
                    approval_policy="ask",
                    user_input_handler=None,
                    hooks=ProjectHooks(),
                    permissions=ProjectPermissions(),
                    execute_action_safely_func=lambda *_args: self.fail(
                        "denied spawn must not execute"
                    ),
                )

        self.assertEqual(wrapped.observation.kind, "approval_denied")
        self.assertEqual(wrapped.observation.message, "team spawn denied")
        self.assertEqual(client.calls, 0)

    def test_approved_teammate_spawn_uses_stable_name_and_persists_identity(self) -> None:
        approvals = []
        client = TeamClient([[{"type": "text", "text": "Review completed."}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action(
                "Agent",
                {"prompt": "Review authentication", "name": "reviewer", "mode": "code"},
            )
            with patch.dict("os.environ", {"VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS": "1"}, clear=True):
                wrapped = execute_special_tool_action(
                    workspace,
                    action,
                    client,
                    steps=[],
                    observations=[],
                    iteration=1,
                    tool_name="Agent",
                    max_output_tokens=1024,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                    approval_handler=lambda request: (
                        approvals.append(request.action_type)
                        or ApprovalDecision(approved=True, message="approved")
                    ),
                    approval_policy="ask",
                    user_input_handler=None,
                    hooks=ProjectHooks(),
                    permissions=ProjectPermissions(),
                    execute_action_safely_func=lambda *_args: self.fail(
                        "spawn should use special execution"
                    ),
                )
                completed = execute_background_task_action(
                    workspace,
                    TaskOutputAction(
                        type="task_output",
                        task_id="reviewer",
                        block=True,
                        timeout_ms=1_000,
                    ),
                )
                listed = list_session_agents(workspace)
                duplicate = teammate_spawn_error(workspace, "reviewer", depth=1)

        self.assertEqual(approvals, ["spawn_teammate"])
        self.assertEqual(wrapped.observation.task_id, "reviewer")
        self.assertEqual(wrapped.observation.teammate_name, "reviewer")
        self.assertTrue(completed.completed)
        self.assertEqual(completed.result.teammate_name, "reviewer")
        self.assertEqual(listed.agents[0].teammate_name, "reviewer")
        self.assertIn("already used", duplicate)

    def test_teammate_claims_shared_task_and_keeps_coordination_tools(self) -> None:
        client = TeamClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "claim-1",
                        "name": "TaskUpdate",
                        "input": {"taskId": "1", "status": "in_progress"},
                    }
                ],
                [{"type": "text", "text": "Claimed the shared review task."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            workspace = create_run_workspace(Path(base))
            create_session_task(
                workspace,
                TaskCreateAction(
                    type="task_create",
                    subject="Review auth",
                    description="Inspect authentication risks",
                ),
            )
            action = parse_tool_action(
                "Agent",
                {
                    "prompt": "Claim and review the auth task",
                    "name": "reviewer",
                    "mode": "code",
                    "max_iterations": 2,
                },
            )
            with patch.dict("os.environ", {"VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS": "1"}, clear=True):
                result = execute_delegate_task_action(
                    workspace,
                    action,
                    client,
                    parent_iteration=1,
                    subagent_id="reviewer",
                    max_output_tokens=1024,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                )
            task, _store = get_session_task(workspace, "1")
            listed = list_session_agents(workspace)

        self.assertTrue(result.ok)
        self.assertEqual(result.teammate_name, "reviewer")
        self.assertEqual(task.owner, "reviewer")
        self.assertEqual(task.status, "in_progress")
        self.assertEqual(listed.agents[0].teammate_name, "reviewer")
        for name in ("SendMessage", "TaskCreate", "TaskGet", "TaskList", "TaskUpdate"):
            self.assertIn(name, client.tool_names[0])

    def test_profile_allowlist_does_not_remove_team_coordination_tools(self) -> None:
        allowed = frozenset({"Read"})
        active = code_delegate_initial_tool_names("ask", allowed)
        names = {
            str(tool["name"])
            for tool in delegate_tool_definitions(
                "code",
                active,
                "ask",
                allowed_tool_names=allowed,
                nested_delegation_allowed=True,
                team_member=True,
            )
        }

        self.assertIn("Read", names)
        for name in ("SendMessage", "TaskCreate", "TaskGet", "TaskList", "TaskUpdate"):
            self.assertIn(name, names)

    def test_teammate_cannot_spawn_another_teammate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            workspace = create_run_workspace(Path(base))
            runtime = NestedDelegateRuntime(
                workspace=workspace,
                subagent_id="reviewer",
                depth=1,
                mode="code",
                cancel_requested=None,
                execute_child=lambda *_args: self.fail("nested teammate must not start"),
                team_member_name="reviewer",
            )
            denied = runtime.execute(
                DelegateTaskAction(
                    type="delegate_task",
                    task="Start peer",
                    run_in_background=True,
                    teammate_name="researcher",
                ),
                child_iteration=1,
            )

        self.assertEqual(denied.kind, "tool_error")
        self.assertIn("Only the lead", denied.message)

    def test_teammate_cannot_run_background_subagent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            workspace = create_run_workspace(Path(base))
            runtime = NestedDelegateRuntime(
                workspace=workspace,
                subagent_id="reviewer",
                depth=1,
                mode="code",
                cancel_requested=None,
                execute_child=lambda *_args: self.fail("background child must not start"),
                team_member_name="reviewer",
            )
            denied = runtime.execute(
                DelegateTaskAction(
                    type="delegate_task",
                    task="Background research",
                    run_in_background=True,
                ),
                child_iteration=1,
            )

        self.assertEqual(denied.kind, "tool_error")
        self.assertIn("foreground", denied.message)

    def test_teammate_can_message_running_peer(self) -> None:
        received = []
        delivered = threading.Event()

        def runner(task_id, _cancel, inbox):
            while not delivered.wait(0.01):
                received.extend(inbox(False))
                if received:
                    delivered.set()
            return DelegateTaskObservation(
                kind="delegate_task",
                ok=True,
                task="Review",
                summary="done",
                iterations=1,
                tool_calls=[],
                message="done",
                task_id=task_id,
                teammate_name="reviewer",
            )

        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            workspace = create_run_workspace(Path(base))
            peer_action = DelegateTaskAction(
                type="delegate_task",
                task="Review",
                run_in_background=True,
                teammate_name="reviewer",
            )
            start_background_delegate_task(workspace, peer_action, runner, task_id="reviewer")
            result = execute_teammate_coordination_action(
                workspace,
                SendMessageAction(
                    type="send_message",
                    to="reviewer",
                    message="Challenge the token validation assumption.",
                ),
                "researcher",
            )
            self.assertTrue(delivered.wait(1))

        self.assertTrue(result.ok)
        self.assertIn("Message from teammate researcher", received[0])
        self.assertIn("token validation", received[0])

    def test_teammate_message_to_lead_is_injected_once_as_untrusted_input(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            workspace = create_run_workspace(Path(base))
            sent = execute_teammate_coordination_action(
                workspace,
                SendMessageAction(
                    type="send_message",
                    to="lead",
                    message="I found a possible authorization bypass.",
                ),
                "reviewer",
            )
            messages: list[ChatMessage] = []
            first = inject_background_delegate_notifications(
                workspace,
                messages,
                [],
                iteration=2,
                logger=None,
            )
            second = inject_background_delegate_notifications(
                workspace,
                messages,
                [],
                iteration=3,
                logger=None,
            )

        self.assertTrue(sent.ok)
        self.assertEqual(first, 1)
        self.assertEqual(second, 0)
        self.assertEqual(len(messages), 1)
        self.assertIn("Untrusted teammate", messages[0].content)
        self.assertIn("authorization bypass", messages[0].content)

    def test_team_cleanup_discards_undelivered_lead_messages(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            workspace = create_run_workspace(Path(base))
            execute_teammate_coordination_action(
                workspace,
                SendMessageAction(
                    type="send_message",
                    to="lead",
                    message="This should be cleared at teardown.",
                ),
                "reviewer",
            )
            clear_team_runtime(workspace)
            messages: list[ChatMessage] = []
            delivered = inject_background_delegate_notifications(
                workspace,
                messages,
                [],
                iteration=2,
                logger=None,
            )

        self.assertEqual(delivered, 0)
        self.assertEqual(messages, [])

    def test_teammate_cannot_take_task_owned_by_peer(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            workspace = create_run_workspace(Path(base))
            task, _store = create_session_task(
                workspace,
                TaskCreateAction(
                    type="task_create",
                    subject="Review auth",
                    description="Inspect authentication risks",
                ),
            )
            update_session_task(
                workspace,
                parse_tool_action("TaskUpdate", {"taskId": task.id, "owner": "reviewer"}),
            )
            denied = execute_teammate_coordination_action(
                workspace,
                parse_tool_action("TaskUpdate", {"taskId": task.id, "status": "in_progress"}),
                "researcher",
            )

        self.assertEqual(denied.kind, "tool_error")
        self.assertIn("owned by teammate reviewer", denied.message)


if __name__ == "__main__":
    unittest.main()
