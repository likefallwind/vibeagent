import tempfile
import threading
import unittest
from pathlib import Path

from vibeagent.actions import AGENT_TOOL_DEFINITIONS, execute_action, parse_tool_action
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.agent_core_tools import CORE_AGENT_TOOL_NAMES
from vibeagent.background_delegate_runtime import start_background_delegate_task
from vibeagent.types import AssistantResponse, DelegateTaskAction, DelegateTaskObservation
from vibeagent.workspace import create_run_workspace


class OneResponseClient:
    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        content = [{"type": "text", "text": "Completed session agent work."}]
        return AssistantResponse(content=content, raw={"content": content})


class ListAgentsTests(unittest.TestCase):
    def test_list_agents_tool_parser_schema_and_core_registration(self) -> None:
        action = parse_tool_action("ListAgents", {"max_agents": 25})
        schema = next(tool for tool in AGENT_TOOL_DEFINITIONS if tool["name"] == "ListAgents")["input_schema"]

        self.assertEqual(action.type, "list_agents")
        self.assertEqual(action.max_agents, 25)
        self.assertEqual(schema["properties"]["max_agents"]["maximum"], 500)
        self.assertIn("ListAgents", CORE_AGENT_TOOL_NAMES)
        for value in (0, 501, True, "10"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_tool_action("ListAgents", {"max_agents": value})

    def test_list_agents_combines_running_runtime_and_completed_transcript(self) -> None:
        release = threading.Event()
        started = threading.Event()

        def runner(task_id, _cancel, _inbox):
            started.set()
            if not release.wait(5):
                raise RuntimeError("test runner was not released")
            return DelegateTaskObservation(
                kind="delegate_task",
                ok=True,
                task="Background check",
                summary="done",
                iterations=1,
                tool_calls=[],
                message="done",
                task_id=task_id,
                background=True,
            )

        with tempfile.TemporaryDirectory(prefix="vibeagent-list-agents-") as base:
            workspace = create_run_workspace(Path(base))
            foreground = parse_tool_action("delegate_task", {"task": "Foreground check"})
            execute_delegate_task_action(
                workspace,
                foreground,
                OneResponseClient(),
                parent_iteration=1,
                subagent_id="delegate-1-1",
                max_output_tokens=1024,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
            )
            background = DelegateTaskAction(
                type="delegate_task",
                task="Background check",
                run_in_background=True,
            )
            running = start_background_delegate_task(workspace, background, runner)
            self.assertTrue(started.wait(1))

            listed = execute_action(workspace, parse_tool_action("ListAgents", {}))
            release.set()

        by_id = {agent.id: agent for agent in listed.agents}
        self.assertEqual(listed.total, 2)
        self.assertEqual(by_id["delegate-1-1"].status, "completed")
        self.assertFalse(by_id["delegate-1-1"].background)
        self.assertTrue(by_id["delegate-1-1"].resumable)
        self.assertEqual(by_id[running.task_id or ""].status, "running")
        self.assertTrue(by_id[running.task_id or ""].background)
        self.assertFalse(by_id[running.task_id or ""].resumable)

    def test_list_agents_survives_runtime_absence_and_counts_invalid_transcripts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-list-agents-") as base:
            workspace = create_run_workspace(Path(base), run_id="persisted")
            action = parse_tool_action("delegate_task", {"task": "Persisted check"})
            execute_delegate_task_action(
                workspace,
                action,
                OneResponseClient(),
                parent_iteration=1,
                subagent_id="delegate-1-1",
                max_output_tokens=1024,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
            )
            transcript_root = workspace.session_dir / "subagents"
            transcript_root.joinpath("broken.json").write_text("{", encoding="utf-8")
            transcript_root.joinpath(".write.json.123.tmp").write_text("partial", encoding="utf-8")

            restored_workspace = create_run_workspace(Path(base), run_id="persisted")
            listed = execute_action(restored_workspace, parse_tool_action("ListAgents", {}))
            missing = execute_action(
                restored_workspace,
                parse_tool_action("TaskOutput", {"task_id": "missing-agent"}),
            )

        self.assertTrue(listed.ok)
        self.assertEqual(listed.total, 1)
        self.assertEqual(listed.invalid, 1)
        self.assertEqual(listed.agents[0].id, "delegate-1-1")
        self.assertIn("delegate-1-1 (completed)", missing.message)

    def test_list_agents_applies_limit_and_rejects_symlink_transcript_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-list-agents-") as base:
            workspace = create_run_workspace(Path(base), run_id="limited")
            for index in range(2):
                execute_delegate_task_action(
                    workspace,
                    parse_tool_action("delegate_task", {"task": f"Check {index}"}),
                    OneResponseClient(),
                    parent_iteration=1,
                    subagent_id=f"delegate-1-{index + 1}",
                    max_output_tokens=1024,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                )
            limited = execute_action(workspace, parse_tool_action("ListAgents", {"max_agents": 1}))

            other_workspace = create_run_workspace(Path(base), run_id="symlinked")
            transcript_root = other_workspace.session_dir / "subagents"
            transcript_root.symlink_to(workspace.session_dir / "subagents", target_is_directory=True)
            rejected = execute_action(other_workspace, parse_tool_action("ListAgents", {}))

        self.assertEqual(len(limited.agents), 1)
        self.assertEqual(limited.total, 2)
        self.assertTrue(limited.truncated)
        self.assertFalse(rejected.ok)
        self.assertEqual(rejected.agents, [])


if __name__ == "__main__":
    unittest.main()
