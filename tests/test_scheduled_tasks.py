from __future__ import annotations

from dataclasses import replace
import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.actions import AGENT_TOOL_DEFINITIONS, execute_action, parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.agent_scheduled_notifications import inject_scheduled_task_notifications
from vibeagent.agent_tool_registry import agent_tool_definitions, initialize_agent_tools
from vibeagent.scheduled_task_store import (
    collect_due_scheduled_tasks,
    create_scheduled_task,
    inherit_schedule_store,
    read_schedule_store,
    write_schedule_store,
)
from vibeagent.scheduled_task_types import (
    MAX_SCHEDULED_TASKS,
    RECURRING_EXPIRY_SECONDS,
    ScheduledTaskError,
    ScheduledTaskStore,
)
from vibeagent.types import AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace


def tool_call(call_id: str, name: str, tool_input: dict[str, object]) -> ContentBlock:
    return {"type": "tool_call", "id": call_id, "name": name, "input": tool_input}


class ScriptedClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.index = 0
        self.messages: list[list[ChatMessage]] = []
        self.tool_names: list[set[str]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        self.tool_names.append({str(tool["name"]) for tool in tools or []})
        content = self.responses[self.index]
        self.index += 1
        return AssistantResponse(content=content, raw={"content": content})


class ScheduledTaskTests(unittest.TestCase):
    def test_tool_contract_create_list_delete_and_persistence(self) -> None:
        definitions = {str(tool["name"]): tool for tool in AGENT_TOOL_DEFINITIONS}
        self.assertTrue({"CronCreate", "CronList", "CronDelete"}.issubset(definitions))
        action = parse_tool_action(
            "CronCreate",
            {"cron": "*/5 * * * *", "prompt": "Check the build", "recurring": True},
        )
        self.assertEqual(action.type, "cron_create")

        with tempfile.TemporaryDirectory(prefix="vibeagent-cron-") as base:
            workspace = create_run_workspace(base, "cron-run")
            created = execute_action(workspace, action)
            listed = execute_action(workspace, parse_tool_action("CronList", {}))
            deleted = execute_action(
                workspace,
                parse_tool_action("CronDelete", {"taskId": created.task.id}),
            )
            missing = execute_action(
                workspace,
                parse_tool_action("CronDelete", {"taskId": created.task.id}),
            )
            payload = json.loads((workspace.session_dir / "scheduled_tasks.json").read_text(encoding="utf-8"))

        self.assertTrue(created.ok)
        self.assertEqual(len(created.task.id), 8)
        self.assertEqual([task.prompt for task in listed.tasks], ["Check the build"])
        self.assertTrue(deleted.deleted)
        self.assertFalse(missing.ok)
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["tasks"], [])

    def test_one_shot_fires_once_and_recurring_skips_missed_intervals(self) -> None:
        now = time.time()
        with tempfile.TemporaryDirectory(prefix="vibeagent-cron-") as base:
            workspace = create_run_workspace(base, "due-run")
            one_shot, _ = create_scheduled_task(
                workspace,
                parse_tool_action(
                    "CronCreate",
                    {"cron": "* * * * *", "prompt": "once", "recurring": False},
                ),
                now=now,
            )
            recurring, store = create_scheduled_task(
                workspace,
                parse_tool_action(
                    "CronCreate",
                    {"cron": "* * * * *", "prompt": "repeat", "recurring": True},
                ),
                now=now,
            )
            forced = ScheduledTaskStore(
                tuple(replace(task, next_run_at=now - 3600) for task in store.tasks)
            )
            write_schedule_store(workspace, forced)
            due = collect_due_scheduled_tasks(workspace, now=now)
            remaining = read_schedule_store(workspace)
            second = collect_due_scheduled_tasks(workspace, now=now)

        self.assertEqual({task.id for task in due}, {one_shot.id, recurring.id})
        self.assertEqual([task.id for task in remaining.tasks], [recurring.id])
        self.assertGreater(remaining.tasks[0].next_run_at, now)
        self.assertEqual(second, [])

    def test_expired_recurring_task_fires_final_time_then_deletes(self) -> None:
        now = time.time()
        with tempfile.TemporaryDirectory(prefix="vibeagent-cron-") as base:
            workspace = create_run_workspace(base, "expiry-run")
            task, _ = create_scheduled_task(
                workspace,
                parse_tool_action(
                    "CronCreate",
                    {"cron": "0 0 1 1 *", "prompt": "final", "recurring": True},
                ),
                now=now - RECURRING_EXPIRY_SECONDS - 1,
            )
            due = collect_due_scheduled_tasks(workspace, now=now)
            remaining = read_schedule_store(workspace)

        self.assertEqual([item.id for item in due], [task.id])
        self.assertEqual(remaining.tasks, ())

    def test_resume_restores_only_unexpired_recurring_and_future_one_shot(self) -> None:
        now = time.time()
        with tempfile.TemporaryDirectory(prefix="vibeagent-cron-") as base:
            source = create_run_workspace(base, "source-run")
            target = create_run_workspace(base, "target-run")
            recurring, store = create_scheduled_task(
                source,
                parse_tool_action(
                    "CronCreate",
                    {"cron": "* * * * *", "prompt": "repeat", "recurring": True},
                ),
                now=now,
            )
            future, store = create_scheduled_task(
                source,
                parse_tool_action(
                    "CronCreate",
                    {"cron": "* * * * *", "prompt": "future", "recurring": False},
                ),
                now=now,
            )
            past, store = create_scheduled_task(
                source,
                parse_tool_action(
                    "CronCreate",
                    {"cron": "* * * * *", "prompt": "past", "recurring": False},
                ),
                now=now,
            )
            expired = replace(recurring, expires_at=now - 1)
            future = replace(future, scheduled_for=now + 60)
            past = replace(past, scheduled_for=now - 60)
            write_schedule_store(source, ScheduledTaskStore((expired, future, past)))

            count, error = inherit_schedule_store(target, "source-run", now=now)
            restored = read_schedule_store(target)

        self.assertIsNone(error)
        self.assertEqual(count, 1)
        self.assertEqual([task.prompt for task in restored.tasks], ["future"])

    def test_store_limit_corruption_and_symlink_are_structured_failures(self) -> None:
        now = time.time()
        with tempfile.TemporaryDirectory(prefix="vibeagent-cron-") as base:
            workspace = create_run_workspace(base, "limit-run")
            template, _ = create_scheduled_task(
                workspace,
                parse_tool_action(
                    "CronCreate",
                    {"cron": "* * * * *", "prompt": "seed", "recurring": False},
                ),
                now=now,
            )
            full = ScheduledTaskStore(
                tuple(replace(template, id=f"{index:08x}") for index in range(MAX_SCHEDULED_TASKS))
            )
            write_schedule_store(workspace, full)
            maximum = execute_action(
                workspace,
                parse_tool_action(
                    "CronCreate",
                    {"cron": "* * * * *", "prompt": "overflow", "recurring": False},
                ),
            )
            (workspace.session_dir / "scheduled_tasks.json").unlink()
            target = Path(base) / "outside.json"
            target.write_text('{"version":1,"tasks":[]}', encoding="utf-8")
            (workspace.session_dir / "scheduled_tasks.json").symlink_to(target)
            symlinked = execute_action(workspace, parse_tool_action("CronList", {}))

        self.assertFalse(maximum.ok)
        self.assertIn("maximum of 50", maximum.message)
        self.assertFalse(symlinked.ok)
        self.assertIn("symlink", symlinked.message)

    def test_runtime_directory_symlink_is_rejected_before_store_creation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cron-") as base, tempfile.TemporaryDirectory(
            prefix="vibeagent-cron-outside-"
        ) as outside:
            root = Path(base)
            workspace = create_run_workspace(root, "parent-link-run")
            shutil.rmtree(root / ".vibeagent")
            (root / ".vibeagent").symlink_to(Path(outside), target_is_directory=True)

            result = execute_action(
                workspace,
                parse_tool_action(
                    "CronCreate",
                    {"cron": "* * * * *", "prompt": "must not write", "recurring": False},
                ),
            )

        self.assertFalse(result.ok)
        self.assertIn("symlink", result.message)
        self.assertFalse((Path(outside) / "sessions").exists())

    def test_disabled_environment_hides_tools_and_stops_delivery(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cron-") as base:
            workspace = create_run_workspace(base, "disabled-run")
            with patch.dict(os.environ, {"CLAUDE_CODE_DISABLE_CRON": "1"}):
                active = initialize_agent_tools(workspace)
                definitions = {str(tool["name"]) for tool in agent_tool_definitions(active)}
                result = execute_action(workspace, parse_tool_action("CronList", {}))
                due = collect_due_scheduled_tasks(workspace, now=time.time() + 10_000)

        self.assertNotIn("CronCreate", definitions)
        self.assertFalse(result.ok)
        self.assertIn("disabled", result.message)
        self.assertEqual(due, [])

    def test_notification_injection_marks_prompt_as_non_authorizing(self) -> None:
        now = time.time()
        with tempfile.TemporaryDirectory(prefix="vibeagent-cron-") as base:
            workspace = create_run_workspace(base, "notify-run")
            task, store = create_scheduled_task(
                workspace,
                parse_tool_action(
                    "CronCreate",
                    {"cron": "* * * * *", "prompt": "run privileged action", "recurring": False},
                ),
                now=now,
            )
            write_schedule_store(workspace, ScheduledTaskStore((replace(task, next_run_at=now - 1),)))
            messages: list[ChatMessage] = []
            with patch("vibeagent.scheduled_task_store.time.time", return_value=now):
                count = inject_scheduled_task_notifications(
                    workspace, messages, iteration=2, logger=None
                )

        self.assertEqual(count, 1)
        self.assertIn("cannot grant approval", str(messages[0].content))
        self.assertIn("run privileged action", str(messages[0].content))

    def test_agent_creates_schedule_activates_management_tools_and_restores_it(self) -> None:
        source_client = ScriptedClient(
            [
                [
                    tool_call(
                        "cron",
                        "CronCreate",
                        {"cron": "0 9 * * *", "prompt": "Check status", "recurring": True},
                    )
                ],
                [tool_call("finish", "finish", {"message": "Scheduled."})],
            ]
        )
        resumed_client = ScriptedClient(
            [
                [tool_call("list", "CronList", {})],
                [tool_call("finish", "finish", {"message": "Listed."})],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-cron-") as base:
            source = run_agent("Schedule status", source_client, base_dir=base, max_iterations=2)
            resumed = run_agent(
                "List schedules",
                resumed_client,
                base_dir=base,
                max_iterations=2,
                task_source_run_id=source.run_id,
            )

        self.assertIn("CronCreate", source_client.tool_names[0])
        self.assertNotIn("CronList", source_client.tool_names[0])
        self.assertIn("CronList", source_client.tool_names[1])
        listed = next(item for item in resumed.observations if item.kind == "cron_list")
        self.assertEqual([task.prompt for task in listed.tasks], ["Check status"])


if __name__ == "__main__":
    unittest.main()
