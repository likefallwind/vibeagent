from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.actions import AGENT_TOOL_DEFINITIONS, execute_action, parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.agent_observation_utils import observation_failed
from vibeagent.session import summarize_session
from vibeagent.session_tasks import inherit_task_store, read_task_store
from vibeagent.types import AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace


class ScriptedClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.index = 0
        self.tool_names: list[set[str]] = []

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
    ) -> AssistantResponse:
        self.tool_names.append({str(tool["name"]) for tool in tools or []})
        content = self.responses[self.index]
        self.index += 1
        return AssistantResponse(content=content, raw={"content": content})


def tool_call(call_id: str, name: str, tool_input: dict[str, object]) -> ContentBlock:
    return {"type": "tool_call", "id": call_id, "name": name, "input": tool_input}


class SessionTaskTests(unittest.TestCase):
    def test_task_tool_schemas_and_inputs_match_claude_contract(self) -> None:
        definitions = {str(tool["name"]): tool for tool in AGENT_TOOL_DEFINITIONS}

        for name in ("TaskCreate", "TaskGet", "TaskList", "TaskUpdate"):
            self.assertIn(name, definitions)
        create = parse_tool_action(
            "TaskCreate",
            {
                "subject": "Implement auth",
                "description": "Add login flow",
                "activeForm": "Implementing auth",
                "metadata": {"ticket": 42},
            },
        )
        update = parse_tool_action(
            "TaskUpdate",
            {
                "taskId": "1",
                "status": "in_progress",
                "addBlocks": ["2"],
                "addBlockedBy": ["3"],
                "owner": "implementer",
            },
        )

        self.assertEqual(create.type, "task_create")
        self.assertEqual(create.active_form, "Implementing auth")
        self.assertEqual(create.metadata, {"ticket": 42})
        self.assertEqual(update.type, "task_update")
        self.assertEqual(update.task_id, "1")
        self.assertEqual(update.add_blocks, ("2",))
        self.assertEqual(update.add_blocked_by, ("3",))

    def test_create_get_list_and_update_persist_stable_ids(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-tasks-") as base:
            workspace = create_run_workspace(base, "task-run")
            first = execute_action(
                workspace,
                parse_tool_action(
                    "TaskCreate",
                    {"subject": "Inspect", "description": "Read implementation"},
                ),
            )
            second = execute_action(
                workspace,
                parse_tool_action(
                    "TaskCreate",
                    {
                        "subject": "Implement",
                        "description": "Apply the change",
                        "activeForm": "Implementing",
                        "metadata": {"api_key": "must-not-persist", "ticket": 7},
                    },
                ),
            )
            updated = execute_action(
                workspace,
                parse_tool_action(
                    "TaskUpdate",
                    {"taskId": "1", "status": "in_progress", "owner": "main"},
                ),
            )
            fetched = execute_action(workspace, parse_tool_action("TaskGet", {"taskId": "1"}))
            listed = execute_action(workspace, parse_tool_action("TaskList", {}))
            persisted = read_task_store(workspace)
            payload = json.loads((workspace.session_dir / "tasks.json").read_text(encoding="utf-8"))

        self.assertEqual(first.task.id, "1")
        self.assertEqual(second.task.id, "2")
        self.assertTrue(updated.success)
        self.assertEqual(updated.statusChange, {"from": "pending", "to": "in_progress"})
        self.assertEqual(fetched.task.owner, "main")
        self.assertEqual([task.id for task in listed.tasks], ["1", "2"])
        self.assertEqual([task.id for task in persisted.tasks], ["1", "2"])
        self.assertNotIn("must-not-persist", json.dumps(payload))
        self.assertEqual(persisted.tasks[1].metadata["ticket"], 7)
        self.assertEqual(payload["nextId"], 3)

    def test_dependencies_block_progress_reject_cycles_and_clean_up_on_delete(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-tasks-") as base:
            workspace = create_run_workspace(base, "dependency-run")
            for subject in ("Foundation", "Feature", "Review"):
                execute_action(
                    workspace,
                    parse_tool_action("TaskCreate", {"subject": subject, "description": subject}),
                )
            dependency = execute_action(
                workspace,
                parse_tool_action("TaskUpdate", {"taskId": "2", "addBlockedBy": ["1"]}),
            )
            blocked = execute_action(
                workspace,
                parse_tool_action("TaskUpdate", {"taskId": "2", "status": "in_progress"}),
            )
            cycle = execute_action(
                workspace,
                parse_tool_action("TaskUpdate", {"taskId": "1", "addBlockedBy": ["2"]}),
            )
            execute_action(
                workspace,
                parse_tool_action("TaskUpdate", {"taskId": "1", "status": "completed"}),
            )
            unblocked = execute_action(
                workspace,
                parse_tool_action("TaskUpdate", {"taskId": "2", "status": "in_progress"}),
            )
            deleted = execute_action(
                workspace,
                parse_tool_action("TaskUpdate", {"taskId": "1", "status": "deleted"}),
            )
            feature = execute_action(workspace, parse_tool_action("TaskGet", {"taskId": "2"}))

        self.assertTrue(dependency.success)
        self.assertFalse(blocked.success)
        self.assertTrue(observation_failed(blocked))
        self.assertIn("blocked by unfinished", blocked.error)
        self.assertFalse(cycle.success)
        self.assertIn("cycle", cycle.error)
        self.assertTrue(unblocked.success)
        self.assertEqual(deleted.statusChange, {"from": "completed", "to": "deleted"})
        self.assertEqual(feature.task.blockedBy, [])

    def test_missing_and_corrupt_task_store_return_structured_results(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-tasks-") as base:
            workspace = create_run_workspace(base, "failure-run")
            missing = execute_action(workspace, parse_tool_action("TaskGet", {"taskId": "404"}))
            unknown_update = execute_action(
                workspace,
                parse_tool_action("TaskUpdate", {"taskId": "404", "status": "completed"}),
            )
            (workspace.session_dir / "tasks.json").write_text("{bad", encoding="utf-8")
            corrupt = execute_action(workspace, parse_tool_action("TaskList", {}))

        self.assertTrue(missing.ok)
        self.assertIsNone(missing.task)
        self.assertFalse(unknown_update.success)
        self.assertEqual(unknown_update.error, "Task not found: 404")
        self.assertFalse(corrupt.ok)
        self.assertTrue(observation_failed(corrupt))
        self.assertIn("Invalid session task store", corrupt.message)

    def test_task_restore_rejects_parent_directory_session_id(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-tasks-") as base:
            workspace = create_run_workspace(base, "target-run")
            inherited, error = inherit_task_store(workspace, "..")

        self.assertFalse(inherited)
        self.assertEqual(error, "Invalid source session id for task restore: ..")

    def test_agent_uses_structured_tasks_as_completion_plan_and_session_evidence(self) -> None:
        responses = [
            [
                tool_call("create-1", "TaskCreate", {"subject": "Inspect", "description": "Inspect code"}),
                tool_call("create-2", "TaskCreate", {"subject": "Verify", "description": "Verify result"}),
            ],
            [
                tool_call("done-1", "TaskUpdate", {"taskId": "1", "status": "completed"}),
                tool_call("done-2", "TaskUpdate", {"taskId": "2", "status": "completed"}),
            ],
            [tool_call("finish", "finish", {"message": "Task graph complete."})],
        ]
        with tempfile.TemporaryDirectory(prefix="vibeagent-tasks-") as base:
            client = ScriptedClient(responses)
            result = run_agent("Track and finish a two-step task", client, base_dir=base, max_iterations=3)
            summary = summarize_session(base, result.run_id)

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual([item.status for item in result.plan], ["completed", "completed"])
        self.assertEqual([item.step for item in summary.latest_plan], ["Inspect", "Verify"])
        self.assertEqual([item.status for item in summary.latest_plan], ["completed", "completed"])
        for name in ("TaskCreate", "TaskGet", "TaskList", "TaskUpdate"):
            self.assertIn(name, client.tool_names[0])

    def test_resumed_agent_inherits_task_ids_and_statuses(self) -> None:
        source_responses = [
            [tool_call("create", "TaskCreate", {"subject": "Persist", "description": "Persist across runs"})],
            [tool_call("complete", "TaskUpdate", {"taskId": "1", "status": "completed"})],
            [tool_call("finish", "finish", {"message": "Source complete."})],
        ]
        resumed_responses = [
            [tool_call("list", "TaskList", {})],
            [tool_call("finish", "finish", {"message": "Resume complete."})],
        ]
        with tempfile.TemporaryDirectory(prefix="vibeagent-tasks-") as base:
            source = run_agent(
                "Create a durable task",
                ScriptedClient(source_responses),
                base_dir=base,
                max_iterations=3,
            )
            resumed = run_agent(
                "Resume the durable task",
                ScriptedClient(resumed_responses),
                base_dir=base,
                max_iterations=2,
                task_source_run_id=source.run_id,
            )
            restored_events = [
                json.loads(line)
                for line in (
                    Path(base) / ".vibeagent" / "sessions" / resumed.run_id / "events.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]

        listed = next(observation for observation in resumed.observations if observation.kind == "task_list")
        self.assertTrue(resumed.success)
        self.assertEqual([(task.id, task.status) for task in listed.tasks], [("1", "completed")])
        restored = next(event for event in restored_events if event["type"] == "tasks_restored")
        self.assertEqual(restored["source_run_id"], source.run_id)
        self.assertTrue(restored["inherited"])


if __name__ == "__main__":
    unittest.main()
