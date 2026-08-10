from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from vibeagent.agent import run_agent
from vibeagent.agent_delegate_tools import execute_delegate_tool_call
from vibeagent.agent_team_runtime import execute_teammate_coordination_action
from vibeagent.session_tasks import read_task_store
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks


class ScriptedClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.calls = 0

    def complete(self, messages: list[ChatMessage], tools=None, **_kwargs) -> AssistantResponse:
        content = self.responses[self.calls]
        self.calls += 1
        return AssistantResponse(content=content, raw={"content": content})


def tool_call(call_id: str, name: str, tool_input: dict[str, object]) -> ContentBlock:
    return {"type": "tool_call", "id": call_id, "name": name, "input": tool_input}


def approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


def write_hook(root: Path, event: str, command: str, *, matcher: str = "ignored") -> None:
    path = root / ".vibeagent" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                event: [
                    {
                        "matcher": matcher,
                        "hooks": [{"type": "command", "command": command}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def blocking_command(event: str, expected_subject: str, teammate: str | None = None) -> str:
    teammate_assertion = (
        f"assert d['teammate_name']=='{teammate}'; " if teammate is not None else ""
    )
    return (
        'python3 -c "import json,sys; d=json.load(sys.stdin); '
        f"assert d['hook_event_name']=='{event}'; "
        f"assert d['task_subject']=='{expected_subject}'; "
        "assert d['task_id']=='1'; "
        f"{teammate_assertion}"
        "print('Task policy rejected the transition.', file=sys.stderr); raise SystemExit(2)\""
    )


class TaskLifecycleHookTests(unittest.TestCase):
    def test_config_loads_task_events_without_matcher_support(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-task-hooks-") as base:
            root = Path(base)
            write_hook(root, "TaskCreated", "python3 -V", matcher="never-match")
            config = read_project_hooks(create_run_workspace(root))

        self.assertIsNone(config.error)
        self.assertEqual(config.hooks[0].matcher, ".*")
        self.assertTrue(config.requires_sequential_tools)

    def test_task_created_exit_two_prevents_persistence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-task-hooks-") as base:
            root = Path(base)
            write_hook(root, "TaskCreated", blocking_command("TaskCreated", "Blocked create"))
            client = ScriptedClient(
                [
                    [tool_call("create", "TaskCreate", {"subject": "Blocked create", "description": "Must not persist"})],
                    [{"type": "text", "text": "Creation was blocked."}],
                ]
            )
            result = run_agent(
                "Create a task", client, base_dir=root, max_iterations=2, approval_handler=approve
            )
            store = read_task_store(create_run_workspace(root, result.run_id))

        self.assertEqual(store.next_id, 1)
        self.assertEqual(store.tasks, ())
        self.assertTrue(any("Task policy rejected" in item.message for item in result.observations))

    def test_task_completed_exit_two_keeps_pending_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-task-hooks-") as base:
            root = Path(base)
            write_hook(root, "TaskCompleted", blocking_command("TaskCompleted", "Verify tests"))
            client = ScriptedClient(
                [
                    [tool_call("create", "TaskCreate", {"subject": "Verify tests", "description": "Run tests"})],
                    [tool_call("done", "TaskUpdate", {"taskId": "1", "status": "completed"})],
                    [{"type": "text", "text": "Completion was blocked."}],
                ]
            )
            result = run_agent(
                "Track completion", client, base_dir=root, max_iterations=3, approval_handler=approve
            )
            store = read_task_store(create_run_workspace(root, result.run_id))

        self.assertEqual(store.tasks[0].status, "pending")
        self.assertTrue(any("Task policy rejected" in item.message for item in result.observations))

    def test_continue_false_blocks_and_halts_the_turn(self) -> None:
        command = (
            "python3 -c \"import json; print(json.dumps("
            "{'continue':False,'stopReason':'Stop this teammate.'}))\""
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-task-hooks-") as base:
            root = Path(base)
            write_hook(root, "TaskCreated", command)
            client = ScriptedClient(
                [[tool_call("create", "TaskCreate", {"subject": "Halt", "description": "Stop"})]]
            )
            result = run_agent(
                "Create a task", client, base_dir=root, max_iterations=2, approval_handler=approve
            )
            store = read_task_store(create_run_workspace(root, result.run_id))

        self.assertEqual(client.calls, 1)
        self.assertFalse(result.success)
        self.assertEqual(store.tasks, ())
        self.assertIn("Stop this teammate.", result.message)

    def test_teammate_task_creation_uses_the_same_blocking_hook(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-task-hooks-") as base:
            root = Path(base)
            write_hook(
                root,
                "TaskCreated",
                blocking_command("TaskCreated", "Shared task", teammate="worker"),
            )
            workspace = create_run_workspace(root, "team-run")
            hooks = read_project_hooks(workspace)
            observations = []
            execution = execute_delegate_tool_call(
                workspace,
                mode="code",
                tool_name="TaskCreate",
                tool_input={"subject": "Shared task", "description": "Coordinate"},
                active_tool_names=set(),
                observations=observations,
                steps=[],
                iteration=1,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=approve,
                approval_policy="ask",
                auto_checkpoint_attempted=False,
                hooks=hooks,
                special_action_handler=lambda action: execute_teammate_coordination_action(
                    workspace, action, "worker"
                ),
                coordination_tool_names=frozenset({"TaskCreate"}),
                teammate_name="worker",
            )
            store = read_task_store(workspace)

        self.assertEqual(store.tasks, ())
        self.assertEqual(execution.hook_results[0].event, "TaskCreated")
        self.assertIn("Task policy rejected", execution.observation.message)


if __name__ == "__main__":
    unittest.main()
