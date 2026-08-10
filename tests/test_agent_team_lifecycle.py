import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.action_dispatcher import execute_action
from vibeagent.action_parsing import parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.agent_team_runtime import teammate_spawn_error
from vibeagent.agent_tool_registry import (
    agent_tool_definitions,
    initial_agent_tool_names,
    prepare_action_for_visibility,
)
from vibeagent.background_delegate_runtime import (
    execute_background_task_action,
    start_background_delegate_task,
)
from vibeagent.team_state import IMPLICIT_TEAM_NAME, read_team_state, team_state_path
from vibeagent.tool_definition_team import TEAM_TOOL_DEFINITIONS
from vibeagent.types import (
    AssistantResponse,
    DelegateTaskAction,
    DelegateTaskObservation,
    TaskOutputAction,
    TaskStopAction,
)
from vibeagent.workspace import create_run_workspace


class TeamLifecycleClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0
        self.tool_names = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.tool_names.append([str(tool["name"]) for tool in tools or []])
        content = self.responses[self.calls]
        self.calls += 1
        return AssistantResponse(content=content, raw={"content": content})


class AgentTeamLifecycleTests(unittest.TestCase):
    def test_agent_runs_explicit_team_lifecycle_through_model_tools(self) -> None:
        client = TeamLifecycleClient(
            [
                [{"type": "tool_call", "id": "create-1", "name": "TeamCreate", "input": {
                    "team_name": "review-team", "description": "Coordinate review work"
                }}],
                [{"type": "tool_call", "id": "delete-1", "name": "TeamDelete", "input": {}}],
                [{"type": "text", "text": "Team lifecycle completed."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            project = Path(base)
            with patch.dict("os.environ", {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}, clear=True):
                result = run_agent(
                    "Create and clean up a review team", client, base_dir=project, max_iterations=3
                )
            team_files = list((project / ".vibeagent" / "sessions").glob("*/team.json"))

        self.assertTrue(result.success)
        self.assertEqual([item.kind for item in result.observations], ["team_create", "team_delete"])
        self.assertTrue({"TeamCreate", "TeamDelete"}.issubset(client.tool_names[0]))
        self.assertEqual(team_files, [])

    def test_team_tools_match_claude_protocol_and_follow_feature_flag(self) -> None:
        create = parse_tool_action(
            "TeamCreate", {"team_name": "review-team", "description": "Coordinate review work"}
        )
        delete = parse_tool_action("TeamDelete", {})

        self.assertEqual(create.type, "team_create")
        self.assertEqual(create.team_name, "review-team")
        self.assertEqual(delete.type, "team_delete")
        self.assertEqual([tool["name"] for tool in TEAM_TOOL_DEFINITIONS], ["TeamCreate", "TeamDelete"])
        self.assertEqual(
            TEAM_TOOL_DEFINITIONS[0]["input_schema"]["required"], ["team_name", "description"]
        )
        with patch.dict("os.environ", {}, clear=True):
            disabled = {tool["name"] for tool in agent_tool_definitions(initial_agent_tool_names())}
            prepared = prepare_action_for_visibility(
                parse_tool_action("ToolSearch", {"query": "TeamCreate", "max_results": 5})
            )
            with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
                searched = execute_action(create_run_workspace(Path(base)), prepared)
        with patch.dict("os.environ", {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}, clear=True):
            enabled = {tool["name"] for tool in agent_tool_definitions(initial_agent_tool_names())}

        self.assertTrue({"TeamCreate", "TeamDelete"}.isdisjoint(disabled))
        self.assertFalse(any(match["name"] in {"TeamCreate", "TeamDelete"} for match in searched.matches))
        self.assertTrue({"TeamCreate", "TeamDelete"}.issubset(enabled))

    def test_explicit_team_lifecycle_is_persisted_and_one_per_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            workspace = create_run_workspace(Path(base))
            with patch.dict("os.environ", {"VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS": "1"}, clear=True):
                created = execute_action(workspace, parse_tool_action("TeamCreate", {
                    "team_name": "review-team", "description": "Coordinate review work"
                }))
                duplicate = execute_action(workspace, parse_tool_action("TeamCreate", {
                    "team_name": "other-team", "description": "Must not replace the team"
                }))
                state = read_team_state(workspace)
                mode = team_state_path(workspace).stat().st_mode & 0o777
                deleted = execute_action(workspace, parse_tool_action("TeamDelete", {}))
                missing = execute_action(workspace, parse_tool_action("TeamDelete", {}))
            events = (workspace.session_dir / "events.jsonl").read_text(encoding="utf-8")

        self.assertTrue(created.ok)
        self.assertEqual(created.team_name, "review-team")
        self.assertFalse(duplicate.ok)
        self.assertIn("already has team review-team", duplicate.message)
        self.assertEqual(state.name, "review-team")
        self.assertTrue(state.explicit)
        self.assertEqual(mode, 0o600)
        self.assertTrue(deleted.ok)
        self.assertFalse(missing.ok)
        self.assertIn('"type": "team_created"', events)
        self.assertIn('"type": "team_deleted"', events)

    def test_team_delete_rejects_running_teammate_then_cleans_after_stop(self) -> None:
        started = threading.Event()

        def runner(task_id, cancelled, _inbox):
            started.set()
            while not cancelled():
                threading.Event().wait(0.01)
            return DelegateTaskObservation(
                kind="delegate_task", ok=False, task="Review", summary="", iterations=0,
                tool_calls=[], message="cancelled", task_id=task_id, teammate_name="reviewer",
                cancelled=True,
            )

        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            workspace = create_run_workspace(Path(base))
            with patch.dict("os.environ", {"VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS": "1"}, clear=True):
                execute_action(workspace, parse_tool_action("TeamCreate", {
                    "team_name": "review-team", "description": "Coordinate review work"
                }))
                start_background_delegate_task(
                    workspace,
                    DelegateTaskAction(
                        type="delegate_task", task="Review", run_in_background=True,
                        teammate_name="reviewer",
                    ),
                    runner,
                    task_id="reviewer",
                )
                self.assertTrue(started.wait(1))
                active = execute_action(workspace, parse_tool_action("TeamDelete", {}))
                execute_background_task_action(
                    workspace, TaskStopAction(type="task_stop", task_id="reviewer")
                )
                execute_background_task_action(
                    workspace,
                    TaskOutputAction(
                        type="task_output", task_id="reviewer", block=True, timeout_ms=1_000
                    ),
                )
                deleted = execute_action(workspace, parse_tool_action("TeamDelete", {}))

        self.assertFalse(active.ok)
        self.assertEqual(active.active_teammates, ["reviewer"])
        self.assertIn("are running", active.message)
        self.assertTrue(deleted.ok)

    def test_named_agent_compatibility_creates_implicit_team_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-team-") as base:
            workspace = create_run_workspace(Path(base))
            with patch.dict("os.environ", {"VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS": "1"}, clear=True):
                error = teammate_spawn_error(workspace, "reviewer", depth=1)
                state = read_team_state(workspace)

        self.assertIsNone(error)
        self.assertEqual(state.name, IMPLICIT_TEAM_NAME)
        self.assertFalse(state.explicit)


if __name__ == "__main__":
    unittest.main()
