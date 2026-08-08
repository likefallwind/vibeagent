import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent import run_agent
from vibeagent.agent_core_tools import (
    CORE_COMMAND_TOOL_NAMES,
    CORE_EDIT_TOOL_NAMES,
    CORE_PROJECT_TOOL_NAMES,
    CORE_READ_TOOL_NAMES,
    CORE_SESSION_TOOL_NAMES,
)
from vibeagent.agent_tool_registry import (
    CORE_AGENT_TOOL_NAMES,
    ToolVisibilityPolicy,
    activate_agent_tool_names,
    background_task_activation_names,
    activate_tools_for_run,
    clear_dynamic_tool_definitions,
    mcp_tools_activation_names,
    agent_tool_definitions,
    initialize_agent_tools,
    initial_agent_tool_names,
    tool_search_activation_names,
    validate_core_agent_tools,
)
from vibeagent.session_timeline_reports import format_session_event_timeline_item
from vibeagent.session_types import SessionEvent
from vibeagent.tool_definitions import AGENT_TOOL_DEFINITIONS
from vibeagent.tool_catalog_core import APPROVAL_REQUIRED_TOOL_NAMES
from vibeagent.types import AssistantResponse, ChatMessage, ContentBlock, DelegateTaskObservation, McpToolInfo, McpToolsObservation, ToolSearchObservation
from vibeagent.workspace import create_run_workspace


class ToolLoadingClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []
        self.tools: list[list[dict]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        self.tools.append(list(tools or []))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


class AgentToolRegistryTests(unittest.TestCase):
    def test_core_tool_groups_compose_the_exported_core_set(self) -> None:
        grouped = (
            CORE_SESSION_TOOL_NAMES
            | CORE_READ_TOOL_NAMES
            | CORE_EDIT_TOOL_NAMES
            | CORE_COMMAND_TOOL_NAMES
            | CORE_PROJECT_TOOL_NAMES
        )

        self.assertEqual(CORE_AGENT_TOOL_NAMES, grouped)
        self.assertTrue(CORE_SESSION_TOOL_NAMES.isdisjoint(CORE_COMMAND_TOOL_NAMES))
        self.assertTrue(CORE_READ_TOOL_NAMES.isdisjoint(CORE_EDIT_TOOL_NAMES))
        self.assertIn("final_review", CORE_PROJECT_TOOL_NAMES)

    def test_core_registry_is_valid_unique_and_materially_smaller(self) -> None:
        initial = agent_tool_definitions(initial_agent_tool_names())
        initial_names = [str(tool["name"]) for tool in initial]
        initial_chars = len(json.dumps(initial, separators=(",", ":")))
        full_chars = len(json.dumps(AGENT_TOOL_DEFINITIONS, separators=(",", ":")))

        self.assertEqual(validate_core_agent_tools(), [])
        self.assertEqual(len(initial_names), len(set(initial_names)))
        self.assertEqual(set(initial_names), set(CORE_AGENT_TOOL_NAMES))
        self.assertLess(len(initial), len(AGENT_TOOL_DEFINITIONS) // 4)
        self.assertLess(initial_chars, full_chars // 4)

    def test_activation_adds_known_tools_once_and_ignores_unknown_names(self) -> None:
        active = initial_agent_tool_names()

        first = activate_agent_tool_names(active, ["python_dependencies", "missing_tool", "python_dependencies"])
        second = activate_agent_tool_names(active, ["python_dependencies"])

        self.assertEqual(first, ["python_dependencies"])
        self.assertEqual(second, [])
        self.assertIn("python_dependencies", active)
        self.assertNotIn("missing_tool", active)

    def test_background_task_activates_output_and_stop_tools(self) -> None:
        observation = DelegateTaskObservation(
            kind="delegate_task",
            ok=True,
            task="inspect auth",
            summary="",
            iterations=0,
            tool_calls=[],
            message="started",
            task_id="task-123456789abc",
            background=True,
            running=True,
        )

        self.assertEqual(background_task_activation_names(observation), ["TaskOutput", "TaskStop"])

    def test_plan_policy_exposes_and_activates_read_only_tools_only(self) -> None:
        active = initial_agent_tool_names()
        definitions = agent_tool_definitions(active, "plan")
        names = {str(tool["name"]) for tool in definitions}

        self.assertIn("read_file", names)
        self.assertIn("AskUserQuestion", names)
        self.assertIn("Read", names)
        self.assertIn("LS", names)
        self.assertIn("Glob", names)
        self.assertIn("Grep", names)
        self.assertIn("update_plan", names)
        self.assertIn("TodoRead", names)
        self.assertIn("TodoWrite", names)
        self.assertIn("ExitPlanMode", names)
        self.assertIn("Task", names)
        self.assertIn("BashOutput", names)
        self.assertNotIn("Bash", names)
        self.assertNotIn("Edit", names)
        self.assertNotIn("KillBash", names)
        self.assertNotIn("MultiEdit", names)
        self.assertNotIn("web_fetch", names)
        self.assertNotIn("WebFetch", names)
        self.assertNotIn("Write", names)
        self.assertTrue(names.isdisjoint(APPROVAL_REQUIRED_TOOL_NAMES))
        self.assertEqual(
            activate_agent_tool_names(
                active,
                ["Bash", "Edit", "Read", "WebFetch", "Write", "git_push", "python_dependencies"],
                "plan",
            ),
            ["python_dependencies"],
        )
        self.assertIn("BashOutput", active)
        self.assertIn("Read", active)
        self.assertEqual(
            activate_agent_tool_names(active, ["git_push"], "plan"),
            [],
        )
        self.assertNotIn("git_push", active)

    def test_initial_tools_expose_claude_aliases_in_ask_mode(self) -> None:
        definitions = agent_tool_definitions(initial_agent_tool_names())
        names = {str(tool["name"]) for tool in definitions}

        for name in [
            "Bash",
            "BashOutput",
            "KillBash",
            "Read",
            "LS",
            "Glob",
            "Grep",
            "Write",
            "Edit",
            "MultiEdit",
            "TodoRead",
            "TodoWrite",
            "ExitPlanMode",
            "AskUserQuestion",
            "Task",
            "ToolSearch",
            "WebFetch",
            "WebSearch",
        ]:
            self.assertIn(name, names)

    def test_visibility_policy_excludes_tools_from_schema_and_activation(self) -> None:
        active = initial_agent_tool_names()
        excluded = frozenset({"python_dependencies", "write_file"})
        definitions = agent_tool_definitions(active | {"python_dependencies"}, excluded_names=excluded)
        names = {str(tool["name"]) for tool in definitions}

        self.assertFalse(ToolVisibilityPolicy(excluded_names=excluded).allows("write_file"))
        self.assertNotIn("write_file", names)
        self.assertNotIn("python_dependencies", names)
        self.assertEqual(
            activate_agent_tool_names(active, ["python_dependencies", "code_dependencies"], excluded_names=excluded),
            ["code_dependencies"],
        )

    def test_run_level_activation_honors_excluded_tools(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-tools-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            active = initial_agent_tool_names()
            activated = activate_tools_for_run(
                workspace,
                active,
                ["python_dependencies"],
                1,
                source="model_call",
                excluded_names=frozenset({"python_dependencies"}),
            )
            events_path = root / ".vibeagent" / "sessions" / workspace.run_id / "events.jsonl"
            event_written = events_path.exists()

        self.assertEqual(activated, [])
        self.assertNotIn("python_dependencies", active)
        self.assertFalse(event_written)

    def test_tool_search_activation_uses_only_returned_matches(self) -> None:
        observation = ToolSearchObservation(
            kind="tool_search",
            ok=True,
            query="python deps",
            matches=[{"name": "python_dependencies"}, {"name": "code_dependencies"}],
            total=2,
            shown=2,
            truncated=False,
            category=None,
            approval_required=None,
            suggestions=["python_references"],
            message="Found tools.",
        )

        self.assertEqual(
            tool_search_activation_names(observation),
            ["python_dependencies", "code_dependencies"],
        )

    def test_mcp_tools_observation_registers_claude_style_dynamic_tools(self) -> None:
        observation = McpToolsObservation(
            kind="mcp_tools",
            ok=True,
            server="docs",
            tools=[
                McpToolInfo(
                    name="search",
                    title="Search",
                    description="Search documentation.",
                    input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                )
            ],
            total=1,
            truncated=False,
            timeout_ms=1000,
            error=None,
            message="Listed tools.",
        )
        active = initial_agent_tool_names()

        self.assertEqual(mcp_tools_activation_names(observation), ["mcp__docs__search"])
        self.assertEqual(
            activate_agent_tool_names(active, ["mcp__docs__search"], "plan"),
            [],
        )
        self.assertEqual(
            activate_agent_tool_names(active, ["mcp__docs__search"]),
            ["mcp__docs__search"],
        )

        definitions = {str(tool["name"]): tool for tool in agent_tool_definitions(active)}
        self.assertEqual(definitions["mcp__docs__search"]["description"], "Search documentation.")
        self.assertEqual(
            definitions["mcp__docs__search"]["input_schema"],
            {"type": "object", "properties": {"query": {"type": "string"}}},
        )

    def test_mcp_tools_observation_skips_invalid_claude_style_dynamic_names(self) -> None:
        observation = McpToolsObservation(
            kind="mcp_tools",
            ok=True,
            server="docs",
            tools=[
                McpToolInfo(
                    name="search",
                    title="Search",
                    description="Search documentation.",
                    input_schema={"type": "object"},
                ),
                McpToolInfo(
                    name="bad name",
                    title=None,
                    description="Invalid because tool names cannot contain spaces.",
                    input_schema={"type": "object"},
                ),
                McpToolInfo(
                    name="a" * 65,
                    title=None,
                    description="Invalid because tool names are capped at 64 characters.",
                    input_schema={"type": "object"},
                ),
            ],
            total=3,
            truncated=False,
            timeout_ms=1000,
            error=None,
            message="Listed tools.",
        )
        invalid_server_observation = McpToolsObservation(
            kind="mcp_tools",
            ok=True,
            server="bad server",
            tools=[
                McpToolInfo(
                    name="search",
                    title="Search",
                    description="Search documentation.",
                    input_schema={"type": "object"},
                )
            ],
            total=1,
            truncated=False,
            timeout_ms=1000,
            error=None,
            message="Listed tools.",
        )

        try:
            self.assertEqual(mcp_tools_activation_names(observation), ["mcp__docs__search"])
            self.assertEqual(mcp_tools_activation_names(invalid_server_observation), [])
            definitions = {
                str(tool["name"]): tool
                for tool in agent_tool_definitions(
                    {
                        "mcp__docs__search",
                        "mcp__docs__bad name",
                        f"mcp__docs__{'a' * 65}",
                        "mcp__bad server__search",
                    }
                )
            }

            self.assertEqual(set(definitions), {"mcp__docs__search"})
        finally:
            clear_dynamic_tool_definitions()

    def test_new_agent_run_clears_dynamic_mcp_tool_definitions(self) -> None:
        observation = McpToolsObservation(
            kind="mcp_tools",
            ok=True,
            server="docs",
            tools=[
                McpToolInfo(
                    name="search",
                    title="Search",
                    description="Search documentation.",
                    input_schema={"type": "object"},
                )
            ],
            total=1,
            truncated=False,
            timeout_ms=1000,
            error=None,
            message="Listed tools.",
        )

        try:
            self.assertEqual(mcp_tools_activation_names(observation), ["mcp__docs__search"])
            active = {"mcp__docs__search"}
            self.assertIn("mcp__docs__search", {str(tool["name"]) for tool in agent_tool_definitions(active)})

            with tempfile.TemporaryDirectory(prefix="vibeagent-tools-") as base:
                initialize_agent_tools(create_run_workspace(Path(base)))

            self.assertEqual(agent_tool_definitions(active), [])
        finally:
            clear_dynamic_tool_definitions()

    def test_tool_search_activates_matching_schemas_on_next_model_turn(self) -> None:
        client = ToolLoadingClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "search-1",
                        "name": "tool_search",
                        "input": {"query": "session_verification", "max_matches": 3},
                    },
                    {"type": "tool_call", "id": "list-1", "name": "list_files", "input": {}},
                ],
                [{"type": "text", "text": "Found the verification tools."}],
            ]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-tools-") as base:
            root = Path(base)
            result = run_agent("Find session verification tools", base_dir=root, client=client, max_iterations=2)
            events = [
                json.loads(line)
                for line in (root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        first_names = {str(tool["name"]) for tool in client.tools[0]}
        second_names = {str(tool["name"]) for tool in client.tools[1]}
        matched_names = {
            str(match["name"])
            for observation in result.observations
            if observation.kind == "tool_search"
            for match in observation.matches
        }
        self.assertNotIn("session_verification", first_names)
        self.assertIn("session_verification", matched_names)
        self.assertTrue(matched_names.issubset(second_names))
        self.assertTrue(first_names.issubset(second_names))
        activated = [event for event in events if event["type"] == "tools_activated"]
        self.assertTrue(any(event["source"] == "tool_search" for event in activated))

    def test_direct_hidden_tool_call_remains_compatible_and_stays_active(self) -> None:
        client = ToolLoadingClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "deps-1",
                        "name": "python_dependencies",
                        "input": {},
                    }
                ],
                [{"type": "text", "text": "Dependencies inspected."}],
            ]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-tools-") as base:
            result = run_agent("Inspect dependencies", base_dir=Path(base), client=client, max_iterations=2)

        first_names = {str(tool["name"]) for tool in client.tools[0]}
        second_names = {str(tool["name"]) for tool in client.tools[1]}
        self.assertTrue(result.success)
        self.assertNotIn("python_dependencies", first_names)
        self.assertIn("python_dependencies", second_names)
        self.assertEqual(result.observations[0].kind, "python_dependencies")

    def test_session_timeline_formats_tool_catalog_events(self) -> None:
        initialized = SessionEvent(
            line_number=1,
            type="tool_catalog_initialized",
            payload={"active": 33, "total": 192},
        )
        activated = SessionEvent(
            line_number=2,
            type="tools_activated",
            payload={"activated": ["python_dependencies"], "source": "tool_search"},
        )

        self.assertIn("active=33 total=192", format_session_event_timeline_item(initialized))
        self.assertIn("python_dependencies", format_session_event_timeline_item(activated))
        self.assertIn("source=tool_search", format_session_event_timeline_item(activated))


if __name__ == "__main__":
    unittest.main()
