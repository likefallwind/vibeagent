import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.user_home_test_case import IsolatedUserHomeTestCase
from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.prompts import build_messages
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock, ProjectAgentsAction, ReadFileObservation
from vibeagent.workspace import (
    create_run_workspace,
    format_project_agent_catalog,
    read_project_agent,
    read_project_agents,
)


def _write_agent(
    root: Path,
    base: str,
    name: str,
    description: str,
    body: str,
    *,
    mode: str = "explore",
    tools: str | None = None,
    disallowed_tools: str | None = None,
    max_turns: int | None = None,
    skills: str | None = None,
    memory: str | None = None,
    isolation: str | None = None,
) -> Path:
    path = root / base / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    tool_line = f"tools: {tools}\n" if tools is not None else ""
    disallowed_line = f"disallowedTools: {disallowed_tools}\n" if disallowed_tools is not None else ""
    max_turns_line = f"maxTurns: {max_turns}\n" if max_turns is not None else ""
    skills_line = f"skills: {skills}\n" if skills is not None else ""
    memory_line = f"memory: {memory}\n" if memory is not None else ""
    isolation_line = f"isolation: {isolation}\n" if isolation is not None else ""
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\nmode: {mode}\n"
        f"{tool_line}{disallowed_line}{max_turns_line}{skills_line}{memory_line}{isolation_line}---\n\n{body}\n",
        encoding="utf-8",
    )
    return path


def _write_skill(root: Path, name: str, body: str) -> Path:
    path = root / ".claude/skills" / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {name} instructions\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return path


class ProfileClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []
        self.tool_names: list[list[str]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        self.tool_names.append([str(tool["name"]) for tool in tools or []])
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


class ProjectAgentProfileTests(IsolatedUserHomeTestCase):
    def test_catalog_exposes_metadata_but_loads_prompt_only_on_demand(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_agent(
                root,
                ".claude/agents",
                "test-writer",
                "Writes focused tests",
                "PRIVATE_AGENT_PROMPT",
                mode="code",
                tools="[Read, Write]",
            )
            workspace = create_run_workspace(root, "run-1")

            catalog = read_project_agents(workspace)
            formatted = format_project_agent_catalog(workspace)
            initial_messages = build_messages("Add tests", workspace)
            loaded = read_project_agent(workspace, "test-writer")

        self.assertEqual(catalog["total"], 1)
        self.assertEqual(catalog["invalid"], 0)
        self.assertEqual(catalog["agents"][0]["mode"], "code")
        self.assertEqual(catalog["agents"][0]["tools"], ["Read", "Write", "read_file", "write_file"])
        self.assertNotIn("prompt", catalog["agents"][0])
        self.assertIn("test-writer: Writes focused tests", formatted or "")
        self.assertNotIn("PRIVATE_AGENT_PROMPT", str(initial_messages[1].content))
        self.assertEqual(loaded["prompt"], "PRIVATE_AGENT_PROMPT")

    def test_catalog_reports_execution_controls_and_rejects_missing_skills(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_skill(root, "focused-tests", "Run only the focused tests.")
            _write_agent(
                root,
                ".claude/agents",
                "controlled",
                "Uses bounded controls",
                "CONTROLLED_PROMPT",
                mode="code",
                tools="[Read, Write]",
                disallowed_tools="Write",
                max_turns=12,
                skills="focused-tests",
                isolation="worktree",
            )
            _write_agent(
                root,
                ".claude/agents",
                "missing-skill",
                "References a missing skill",
                "MISSING_SKILL_PROMPT",
                skills="does-not-exist",
            )
            workspace = create_run_workspace(root, "run-1")

            catalog = read_project_agents(workspace)
            formatted = format_project_agent_catalog(workspace)
            loaded = read_project_agent(workspace, "controlled")

        agents = {str(agent["name"]): agent for agent in catalog["agents"]}
        self.assertEqual(agents["controlled"]["disallowed_tools"], ["Write", "write_file"])
        self.assertEqual(agents["controlled"]["max_turns"], 12)
        self.assertEqual(agents["controlled"]["skills"], ["focused-tests"])
        self.assertEqual(agents["controlled"]["isolation"], "worktree")
        self.assertFalse(agents["missing-skill"]["available"])
        self.assertIn("unavailable skill", str(agents["missing-skill"]["message"]))
        self.assertIn("disallowedTools=Write,write_file", formatted or "")
        self.assertIn("isolation=worktree", formatted or "")
        self.assertEqual(loaded["max_turns"], 12)
        self.assertEqual(loaded["isolation"], "worktree")

    def test_invalid_profile_execution_controls_are_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_agent(
                root,
                ".claude/agents",
                "too-many-turns",
                "Has an invalid turn bound",
                "INVALID_TURNS",
                max_turns=51,
            )
            _write_agent(
                root,
                ".claude/agents",
                "unknown-deny",
                "Has an unknown denied tool",
                "INVALID_DENYLIST",
                disallowed_tools="not_a_real_tool",
            )
            _write_agent(
                root,
                ".claude/agents",
                "empty-deny",
                "Has an empty denylist",
                "VALID_EMPTY_DENYLIST",
                disallowed_tools="[]",
            )
            _write_agent(
                root,
                ".claude/agents",
                "bad-isolation",
                "Has unsupported isolation",
                "INVALID_ISOLATION",
                isolation="container",
            )
            workspace = create_run_workspace(root, "run-1")

            catalog = read_project_agents(workspace)

        agents = {str(agent["name"]): agent for agent in catalog["agents"]}
        self.assertFalse(agents["too-many-turns"]["available"])
        self.assertIn("between 1 and 50", str(agents["too-many-turns"]["message"]))
        self.assertFalse(agents["unknown-deny"]["available"])
        self.assertIn("disallowedTools references unknown", str(agents["unknown-deny"]["message"]))
        self.assertTrue(agents["empty-deny"]["available"])
        self.assertFalse(agents["bad-isolation"]["available"])
        self.assertIn("isolation must be worktree", str(agents["bad-isolation"]["message"]))

    def test_profile_memory_metadata_accepts_user_and_rejects_unknown_scopes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_agent(
                root,
                ".claude/agents",
                "project-memory",
                "Uses project memory",
                "PROJECT_MEMORY_PROMPT",
                mode="code",
                memory="project",
            )
            _write_agent(
                root,
                ".claude/agents",
                "user-memory",
                "Requests external memory",
                "USER_MEMORY_PROMPT",
                memory="user",
            )
            _write_agent(
                root,
                ".claude/agents",
                "invalid-memory",
                "Requests invalid memory",
                "INVALID_MEMORY_PROMPT",
                memory="shared",
            )
            workspace = create_run_workspace(root, "run-1")

            catalog = read_project_agents(workspace)
            formatted = format_project_agent_catalog(workspace)

        agents = {str(agent["name"]): agent for agent in catalog["agents"]}
        self.assertEqual(agents["project-memory"]["memory"], "project")
        self.assertTrue(agents["project-memory"]["available"])
        self.assertTrue(agents["user-memory"]["available"])
        self.assertEqual(agents["user-memory"]["memory"], "user")
        self.assertFalse(agents["invalid-memory"]["available"])
        self.assertIn("must be user, project, or local", str(agents["invalid-memory"]["message"]))
        self.assertIn("memory=project", formatted or "")
        self.assertIn("memory=user", formatted or "")

    def test_project_agents_tool_lists_metadata_without_prompt_body(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_agent(root, ".claude/agents", "reviewer", "Reviews code", "PRIVATE_REVIEW_PROMPT")
            workspace = create_run_workspace(root, "run-1")
            action = parse_tool_action("project_agents", {"max_agents": 5})
            observation = execute_action(workspace, action)

        self.assertIsInstance(action, ProjectAgentsAction)
        self.assertEqual(observation.kind, "project_agents")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.agents[0].name, "reviewer")
        self.assertFalse(hasattr(observation.agents[0], "prompt"))

    def test_duplicate_symlink_and_unsafe_profiles_are_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_agent(root, ".claude/agents", "duplicate", "First", "First prompt")
            _write_agent(root, ".agents/agents", "duplicate", "Second", "Second prompt")
            _write_agent(
                root,
                ".claude/agents",
                "unsafe-explore",
                "Unsafe",
                "Unsafe prompt",
                tools="write_file",
            )
            _write_agent(
                root,
                ".claude/agents",
                "todo-writer",
                "Todo writer",
                "Todo prompt",
                mode="code",
                tools="TodoWrite",
            )
            _write_agent(
                root,
                ".claude/agents",
                "recursive",
                "Recursive",
                "Recursive prompt",
                mode="code",
                tools="delegate_task",
            )
            external = root / "outside.md"
            external.write_text("---\nname: linked\ndescription: Linked\n---\nPrompt\n", encoding="utf-8")
            linked = root / ".claude/agents/linked.md"
            linked.symlink_to(external)
            workspace = create_run_workspace(root, "run-1")

            catalog = read_project_agents(workspace)

        messages = {str(agent["name"]): str(agent["message"]) for agent in catalog["agents"]}
        self.assertIn("Duplicate agent profile", messages["duplicate"])
        self.assertIn("non-read-only", messages["unsafe-explore"])
        self.assertIn("forbidden tool", messages["todo-writer"])
        self.assertEqual(messages["recursive"], "Available.")
        self.assertIn("symbolic link", messages["linked"])
        self.assertEqual(catalog["invalid"], 5)

    def test_profile_controls_mode_prompt_and_visible_tools(self) -> None:
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "Write",
                        "input": {"file_path": "profiled.py", "content": "profiled = True\n"},
                    }
                ],
                [{"type": "text", "text": "Completed the profiled implementation."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_agent(
                root,
                ".claude/agents",
                "focused-writer",
                "Writes one focused file",
                "PROFILE_SPECIAL_INSTRUCTION",
                mode="code",
                tools="Write",
            )
            workspace = create_run_workspace(root, "run-1")
            action = parse_tool_action(
                "delegate_task",
                {"task": "Create profiled.py", "agent": "focused-writer", "mode": "explore", "max_iterations": 2},
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
                approval_handler=lambda request: ApprovalDecision(approved=True, message="approved"),
            )

            self.assertEqual(root.joinpath("profiled.py").read_text(encoding="utf-8"), "profiled = True\n")

        self.assertTrue(observation.ok)
        self.assertEqual(observation.mode, "code")
        self.assertEqual(observation.agent, "focused-writer")
        self.assertEqual(set(client.tool_names[0]), {"Write", "finish", "write_file"})
        self.assertIn("PROFILE_SPECIAL_INSTRUCTION", str(client.messages[0][0].content))

    def test_profile_preloads_skills_only_for_selected_subagent_and_applies_max_turns(self) -> None:
        client = ProfileClient(
            [
                [{"type": "tool_call", "id": "read-1", "name": "Read", "input": {"file_path": "README.md"}}],
                [{"type": "text", "text": "Used the preloaded skill."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            root.joinpath("README.md").write_text("# Demo\n", encoding="utf-8")
            _write_skill(root, "focused-read", "PRIVATE_SKILL_INSTRUCTION")
            _write_agent(
                root,
                ".claude/agents",
                "skill-reader",
                "Reads with a project skill",
                "PROFILE_PROMPT",
                tools="Read",
                max_turns=2,
                skills="focused-read",
            )
            workspace = create_run_workspace(root, "run-1")
            initial_messages = build_messages("Read the project", workspace)
            action = parse_tool_action(
                "delegate_task",
                {"task": "Read README", "agent": "skill-reader", "max_iterations": 1},
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
            )
            events = [
                json.loads(line)
                for line in (root / ".vibeagent/sessions/run-1/events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
        self.assertTrue(observation.ok)
        self.assertEqual(observation.iterations, 2)
        self.assertNotIn("PRIVATE_SKILL_INSTRUCTION", str(initial_messages))
        self.assertIn("PROFILE_PROMPT", str(client.messages[0][0].content))
        self.assertIn("PRIVATE_SKILL_INSTRUCTION", str(client.messages[0][0].content))
        started = next(event for event in events if event["type"] == "subagent_started")
        self.assertEqual(started["max_iterations"], 2)
        self.assertEqual(started["profile_skills"], ["focused-read"])

    def test_profile_memory_is_injected_and_written_in_agent_scope_after_approval(self) -> None:
        approvals: list[str] = []
        content = "Prefer focused unittest commands.\n"
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "check-memory-1",
                        "name": "check_memory_write",
                        "input": {"path": "MEMORY.md", "content": content},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "write-memory-1",
                        "name": "memory_write",
                        "input": {"path": "MEMORY.md", "content": content},
                    }
                ],
                [{"type": "text", "text": "Updated reviewer memory."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            memory_path = root / ".claude/agent-memory/reviewer/MEMORY.md"
            memory_path.parent.mkdir(parents=True)
            memory_path.write_text("Prior reviewer convention.\n", encoding="utf-8")
            _write_agent(
                root,
                ".claude/agents",
                "reviewer",
                "Reviews with persistent project knowledge",
                "REVIEWER_PROMPT",
                mode="code",
                tools="Read",
                memory="project",
            )
            workspace = create_run_workspace(root, "run-1")
            initial_messages = build_messages("Review changes", workspace)
            action = parse_tool_action(
                "delegate_task",
                {"task": "Review changes", "agent": "reviewer", "max_iterations": 3},
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
                approval_handler=lambda request: (
                    approvals.append(request.action_type)
                    or ApprovalDecision(approved=True, message="approved")
                ),
            )
            events = [
                json.loads(line)
                for line in (root / ".vibeagent/sessions/run-1/events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            stored_memory = memory_path.read_text(encoding="utf-8")
            parent_memory_exists = root.joinpath(".vibeagent/memory/MEMORY.md").exists()

        self.assertTrue(observation.ok)
        self.assertNotIn("Prior reviewer convention.", str(initial_messages))
        self.assertIn("Persistent agent memory is enabled", str(client.messages[0][0].content))
        self.assertIn("Prior reviewer convention.", str(client.messages[0][0].content))
        self.assertIn("check_memory_write", client.tool_names[0])
        self.assertIn("memory_write", client.tool_names[0])
        self.assertEqual(stored_memory, content)
        self.assertFalse(parent_memory_exists)
        self.assertEqual(approvals, ["memory_write"])
        started = next(event for event in events if event["type"] == "subagent_started")
        self.assertEqual(started["profile_memory_scope"], "project")

    def test_subagent_without_memory_cannot_escape_into_parent_memory(self) -> None:
        approvals: list[str] = []
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "memory-1",
                        "name": "memory_write",
                        "input": {"path": "MEMORY.md", "content": "must not persist\n"},
                    }
                ],
                [{"type": "text", "text": "The hidden memory call was blocked."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_agent(
                root,
                ".agents/agents",
                "stateless",
                "Has no persistent memory",
                "Do not retain state.",
                mode="code",
            )
            workspace = create_run_workspace(root, "run-1")
            action = parse_tool_action("delegate_task", {"task": "Stay stateless", "agent": "stateless"})
            execute_delegate_task_action(
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
                approval_handler=lambda request: (
                    approvals.append(request.action_type)
                    or ApprovalDecision(approved=True, message="approved")
                ),
            )
            parent_memory_exists = root.joinpath(".vibeagent/memory/MEMORY.md").exists()

        result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(result["kind"], "tool_error")
        self.assertIn("blocked by the selected project agent profile", result["message"])
        self.assertFalse(parent_memory_exists)
        self.assertEqual(approvals, [])

    def test_disabled_or_unsafe_profile_memory_fails_closed(self) -> None:
        disabled_client = ProfileClient([[{"type": "text", "text": "Memory stayed disabled."}]])
        unsafe_client = ProfileClient([])
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_agent(
                root,
                ".claude/agents",
                "disabled-memory",
                "Has disabled project memory",
                "DISABLED_MEMORY_PROMPT",
                mode="code",
                memory="project",
            )
            _write_agent(
                root,
                ".claude/agents",
                "unsafe-memory",
                "Has an unsafe memory path",
                "UNSAFE_MEMORY_PROMPT",
                mode="code",
                memory="project",
            )
            outside = root / "outside-memory"
            outside.mkdir()
            unsafe_root = root / ".claude/agent-memory/unsafe-memory"
            unsafe_root.parent.mkdir(parents=True)
            unsafe_root.symlink_to(outside, target_is_directory=True)
            workspace = create_run_workspace(root, "run-1")

            with patch.dict("os.environ", {"VIBEAGENT_DISABLE_AUTO_MEMORY": "1"}):
                disabled = execute_delegate_task_action(
                    workspace,
                    parse_tool_action(
                        "delegate_task",
                        {"task": "Run without memory", "agent": "disabled-memory"},
                    ),
                    disabled_client,
                    parent_iteration=1,
                    subagent_id="delegate-1-1",
                    max_output_tokens=2048,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                )
            unsafe = execute_delegate_task_action(
                workspace,
                parse_tool_action(
                    "delegate_task",
                    {"task": "Load unsafe memory", "agent": "unsafe-memory"},
                ),
                unsafe_client,
                parent_iteration=1,
                subagent_id="delegate-1-2",
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
            )

        self.assertTrue(disabled.ok)
        self.assertNotIn("memory_write", disabled_client.tool_names[0])
        self.assertNotIn("Persistent agent memory is enabled", str(disabled_client.messages[0][0].content))
        self.assertFalse(unsafe.ok)
        self.assertIn("must not be a symlink", unsafe.message)
        self.assertEqual(unsafe_client.messages, [])

    def test_profile_denylist_filters_schema_and_blocks_hidden_alias_call(self) -> None:
        approvals: list[str] = []
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "Write",
                        "input": {"file_path": "blocked.py", "content": "blocked = False\n"},
                    }
                ],
                [{"type": "text", "text": "The denied tool stayed blocked."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_agent(
                root,
                ".agents/agents",
                "reader-only",
                "Allows reads but denies writes",
                "Do not write files.",
                mode="code",
                tools="[Read, Write]",
                disallowed_tools="Write",
            )
            workspace = create_run_workspace(root, "run-1")
            action = parse_tool_action("delegate_task", {"task": "Stay read-only", "agent": "reader-only"})
            execute_delegate_task_action(
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
                approval_handler=lambda request: (
                    approvals.append(request.action_type)
                    or ApprovalDecision(approved=True, message="approved")
                ),
            )

            self.assertFalse(root.joinpath("blocked.py").exists())

        self.assertEqual(set(client.tool_names[0]), {"Read", "finish", "read_file"})
        result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(result["kind"], "tool_error")
        self.assertIn("blocked by the selected project agent profile", result["message"])
        self.assertEqual(approvals, [])

    def test_profile_denylist_blocks_tool_search_activation(self) -> None:
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "search-1",
                        "name": "tool_search",
                        "input": {"query": "python_dependencies", "max_matches": 5},
                    }
                ],
                [{"type": "text", "text": "The denied discovered tool was not activated."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_agent(
                root,
                ".claude/agents",
                "bounded-searcher",
                "Searches tools with a denylist",
                "Search for tools without activating denied entries.",
                mode="code",
                disallowed_tools="python_dependencies",
            )
            workspace = create_run_workspace(root, "run-1")
            action = parse_tool_action("delegate_task", {"task": "Search tools", "agent": "bounded-searcher"})
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
            )

        self.assertTrue(observation.ok)
        self.assertIn("tool_search", client.tool_names[0])
        self.assertNotIn("python_dependencies", client.tool_names[1])

    def test_code_profile_edit_alias_allows_replace_all_regex_path(self) -> None:
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "edit-1",
                        "name": "Edit",
                        "input": {
                            "file_path": "app.py",
                            "old_string": "old",
                            "new_string": "new",
                            "replace_all": True,
                        },
                    }
                ],
                [{"type": "text", "text": "Replaced all matches."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            root.joinpath("app.py").write_text("old old\n", encoding="utf-8")
            _write_agent(
                root,
                ".claude/agents",
                "editor",
                "Edits files",
                "Use the declared edit tool.",
                mode="code",
                tools="Edit",
            )
            workspace = create_run_workspace(root, "run-1")
            loaded = read_project_agent(workspace, "editor")
            action = parse_tool_action("delegate_task", {"task": "Replace text", "agent": "editor", "max_iterations": 2})
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
                approval_handler=lambda request: ApprovalDecision(approved=True, message="approved"),
            )

            self.assertEqual(root.joinpath("app.py").read_text(encoding="utf-8"), "new new\n")

        self.assertEqual(loaded["tools"], ["Edit", "edit_file", "regex_replace"])
        self.assertTrue(observation.ok)
        self.assertEqual(set(client.tool_names[0]), {"Edit", "finish", "edit_file", "regex_replace"})
        result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(result["kind"], "regex_replace")
        self.assertEqual(result["replacements"], 2)

    def test_explore_profile_accepts_claude_read_tool_alias(self) -> None:
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "read-1",
                        "name": "Read",
                        "input": {"file_path": "README.md", "limit": 2},
                    }
                ],
                [{"type": "text", "text": "Read the file."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            root.joinpath("README.md").write_text("# Demo\nBody\n", encoding="utf-8")
            _write_agent(
                root,
                ".claude/agents",
                "reader",
                "Reads files",
                "Use read-only evidence.",
                tools="Read",
            )
            workspace = create_run_workspace(root, "run-1")
            action = parse_tool_action("delegate_task", {"task": "Read README", "agent": "reader", "max_iterations": 2})
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
            )

        self.assertTrue(observation.ok)
        self.assertEqual(set(client.tool_names[0]), {"Read", "finish", "read_file"})
        result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(result["kind"], "read_file")
        self.assertEqual(result["path"], "README.md")

    def test_explore_subagent_guards_repeated_list_files(self) -> None:
        client = ProfileClient(
            [
                [{"type": "tool_call", "id": "list-1", "name": "list_files", "input": {"path": "."}}],
                [{"type": "tool_call", "id": "list-2", "name": "list_files", "input": {"path": "."}}],
                [{"type": "text", "text": "Listed once and stopped repeating."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            root.joinpath("app.py").write_text("print('ok')\n", encoding="utf-8")
            workspace = create_run_workspace(root, "run-1")
            action = parse_tool_action("delegate_task", {"task": "List project files", "max_iterations": 3})
            list_calls: list[str] = []

            def fake_execute_action_safely(workspace, action, command_timeout_ms, tool_name):
                if getattr(action, "type", "") == "list_files":
                    list_calls.append(str(getattr(action, "path", None) or "."))
                return execute_action(workspace, action, command_timeout_ms)

            with patch("vibeagent.agent_delegate_tools.execute_action_safely", side_effect=fake_execute_action_safely):
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
                )

        self.assertTrue(observation.ok)
        self.assertEqual(list_calls, ["."])
        result = json.loads(client.messages[2][-1].content[0]["content"])
        self.assertEqual(result["kind"], "list_files")
        self.assertIn("Already listed", result["message"])

    def test_explore_subagent_compacts_long_message_history(self) -> None:
        responses = [
            [{"type": "tool_call", "id": f"read-{index}", "name": "read_file", "input": {"path": "README.md"}}]
            for index in range(6)
        ]
        responses.append([{"type": "text", "text": "Read enough context."}])
        client = ProfileClient(responses)
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            root.joinpath("README.md").write_text("# Demo\nBody\n", encoding="utf-8")
            workspace = create_run_workspace(root, "run-1")
            action = parse_tool_action(
                "delegate_task",
                {
                    "task": "Read project context",
                    "context": "Keep the README evidence.",
                    "max_iterations": 7,
                },
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
            )
            events_path = root / ".vibeagent" / "sessions" / "run-1" / "events.jsonl"
            rows = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

        compacted_user = client.messages[6][1].content
        compaction_rows = [row for row in rows if row["type"] == "subagent_context_compacted"]
        self.assertTrue(observation.ok)
        self.assertEqual(len(client.messages[6]), 2)
        self.assertIsInstance(compacted_user, str)
        self.assertIn("Compacted delegated-task context:", compacted_user)
        self.assertIn("Total subagent observations so far: 6.", compacted_user)
        self.assertIn("Original delegated context:", compacted_user)
        self.assertIn("Keep the README evidence.", compacted_user)
        self.assertIn("Compacted subagent observations:", compacted_user)
        self.assertIn("read_file README.md", compacted_user)
        self.assertEqual(len(compaction_rows), 1)
        self.assertEqual(compaction_rows[0]["previous_messages"], 14)
        self.assertEqual(compaction_rows[0]["new_messages"], 2)
        self.assertEqual(compaction_rows[0]["observations"], 6)

    def test_code_subagent_compaction_excludes_parent_observations(self) -> None:
        responses = [
            [{"type": "tool_call", "id": f"read-{index}", "name": "read_file", "input": {"path": "README.md"}}]
            for index in range(6)
        ]
        responses.append([{"type": "text", "text": "Read enough code context."}])
        client = ProfileClient(responses)
        parent_observations = [
            ReadFileObservation(
                kind="read_file",
                path="parent.txt",
                content="parent evidence\n",
                message="Read parent.txt.",
            )
        ]
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            root.joinpath("README.md").write_text("# Demo\nBody\n", encoding="utf-8")
            _write_agent(
                root,
                ".claude/agents",
                "context-reader",
                "Reads code context",
                "PROFILE_COMPACTION_INSTRUCTION",
                mode="code",
                tools="read_file",
            )
            workspace = create_run_workspace(root, "run-1")
            action = parse_tool_action(
                "delegate_task",
                {"task": "Read project context", "agent": "context-reader", "max_iterations": 7},
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
                parent_observations=parent_observations,
            )
            events_path = root / ".vibeagent" / "sessions" / "run-1" / "events.jsonl"
            rows = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

        compacted_user = client.messages[6][1].content
        compacted_system = client.messages[6][0].content
        compaction_rows = [row for row in rows if row["type"] == "subagent_context_compacted"]
        self.assertTrue(observation.ok)
        self.assertIsInstance(compacted_user, str)
        self.assertIsInstance(compacted_system, str)
        self.assertIn("PROFILE_COMPACTION_INSTRUCTION", compacted_system)
        self.assertIn("Total subagent observations so far: 6.", compacted_user)
        self.assertIn("read_file README.md", compacted_user)
        self.assertNotIn("parent.txt", compacted_user)
        self.assertEqual(len(parent_observations), 7)
        self.assertEqual(compaction_rows[0]["mode"], "code")
        self.assertEqual(compaction_rows[0]["agent"], "context-reader")

    def test_code_profile_bash_alias_allows_background_bash(self) -> None:
        approvals: list[str] = []

        class BackgroundBashClient(ProfileClient):
            def __init__(self) -> None:
                super().__init__([])

            def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
                self.messages.append(list(messages))
                self.tool_names.append([str(tool["name"]) for tool in tools or []])
                if len(self.messages) == 1:
                    content = [
                        {
                            "type": "tool_call",
                            "id": "bash-1",
                            "name": "Bash",
                            "input": {"command": "python3 -c \"print('ready')\"", "run_in_background": True},
                        }
                    ]
                elif len(self.messages) == 2:
                    process_id = json.loads(self.messages[-1][-1].content[0]["content"])["process_id"]
                    content = [{"type": "tool_call", "id": "output-1", "name": "BashOutput", "input": {"bash_id": process_id}}]
                elif len(self.messages) == 3:
                    process_id = json.loads(self.messages[-2][-1].content[0]["content"])["process_id"]
                    content = [{"type": "tool_call", "id": "kill-1", "name": "KillBash", "input": {"bash_id": process_id}}]
                else:
                    content = [{"type": "text", "text": "Checked and stopped the command."}]
                return AssistantResponse(content=content, raw={"content": content})

        client = BackgroundBashClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_agent(
                root,
                ".claude/agents",
                "runner",
                "Runs commands",
                "Use the declared command tool.",
                mode="code",
                tools="Bash",
            )
            workspace = create_run_workspace(root, "run-1")
            loaded = read_project_agent(workspace, "runner")
            action = parse_tool_action("delegate_task", {"task": "Start a command", "agent": "runner"})
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
                approval_handler=lambda request: (
                    approvals.append(request.action_type)
                    or ApprovalDecision(approved=True, message="approved")
                ),
            )

        self.assertEqual(
            loaded["tools"],
            [
                "Bash",
                "BashOutput",
                "KillBash",
                "process_output_contexts",
                "process_output_diagnostics",
                "read_process",
                "run_command",
                "start_command",
                "stop_process",
            ],
        )
        self.assertTrue(observation.ok)
        self.assertEqual(
            set(client.tool_names[0]),
            {
                "Bash",
                "BashOutput",
                "KillBash",
                "finish",
                "process_output_contexts",
                "process_output_diagnostics",
                "read_process",
                "run_command",
                "start_command",
                "stop_process",
            },
        )
        result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(result["kind"], "start_command")
        output_result = json.loads(client.messages[2][-1].content[0]["content"])
        self.assertEqual(output_result["kind"], "read_process")
        stop_result = json.loads(client.messages[3][-1].content[0]["content"])
        self.assertEqual(stop_result["kind"], "stop_process")
        self.assertEqual(approvals, ["start_command", "stop_process"])

    def test_code_profile_webfetch_alias_reaches_approval_boundary(self) -> None:
        approvals: list[str] = []
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "fetch-1",
                        "name": "WebFetch",
                        "input": {"url": "https://docs.python.org/3/"},
                    }
                ],
                [{"type": "text", "text": "WebFetch was sent to approval."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_agent(
                root,
                ".claude/agents",
                "fetcher",
                "Fetches public docs",
                "Use only approved public documentation.",
                mode="code",
                tools="WebFetch",
            )
            workspace = create_run_workspace(root, "run-1")
            loaded = read_project_agent(workspace, "fetcher")
            action = parse_tool_action("delegate_task", {"task": "Fetch docs", "agent": "fetcher"})
            execute_delegate_task_action(
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
                approval_handler=lambda request: (
                    approvals.append(request.action_type)
                    or ApprovalDecision(approved=False, message="not approved")
                ),
            )

        self.assertEqual(loaded["tools"], ["WebFetch", "web_fetch"])
        self.assertEqual(set(client.tool_names[0]), {"WebFetch", "finish", "web_fetch"})
        result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(result["kind"], "approval_denied")
        self.assertEqual(result["action_type"], "web_fetch")
        self.assertEqual(approvals, ["web_fetch"])

    def test_code_profile_accepts_claude_mcp_tool_alias_allowlist(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_agent(
                root,
                ".claude/agents",
                "docs-searcher",
                "Searches docs MCP",
                "Use the docs MCP search tool.",
                mode="code",
                tools="mcp__docs__search",
            )
            _write_agent(
                root,
                ".claude/agents",
                "bad-mcp",
                "Bad MCP",
                "Bad profile.",
                mode="code",
                tools="mcp__docs",
            )
            workspace = create_run_workspace(root, "run-1")

            catalog = read_project_agents(workspace)
            loaded = read_project_agent(workspace, "docs-searcher")

        messages = {str(agent["name"]): str(agent["message"]) for agent in catalog["agents"]}
        self.assertEqual(loaded["tools"], ["mcp__docs__search", "mcp_tools"])
        self.assertEqual(messages["docs-searcher"], "Available.")
        self.assertIn("unknown tool", messages["bad-mcp"])

    def test_explore_profile_todoread_alias_allows_claude_tool_call(self) -> None:
        client = ProfileClient(
            [
                [{"type": "tool_call", "id": "todo-1", "name": "TodoRead", "input": {}}],
                [{"type": "text", "text": "Read the plan."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            root.joinpath(".vibeagent/sessions/run-1").mkdir(parents=True)
            root.joinpath(".vibeagent/sessions/run-1/events.jsonl").write_text(
                '{"type":"tool_result","iteration":1,"name":"update_plan","result":{"kind":"update_plan","plan":[{"step":"Inspect","status":"completed"}],"message":"Plan updated."}}\n',
                encoding="utf-8",
            )
            _write_agent(
                root,
                ".claude/agents",
                "planner",
                "Reads plans",
                "Read the current task plan.",
                tools="TodoRead",
            )
            workspace = create_run_workspace(root, "run-1")
            loaded = read_project_agent(workspace, "planner")
            action = parse_tool_action("delegate_task", {"task": "Read plan", "agent": "planner", "max_iterations": 2})
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
            )

        self.assertEqual(loaded["tools"], ["TodoRead", "session_plan"])
        self.assertTrue(observation.ok)
        self.assertEqual(set(client.tool_names[0]), {"TodoRead", "finish", "session_plan"})
        result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(result["kind"], "session_plan")
        self.assertIn("completed: Inspect", result["plan"])

    def test_hidden_tool_call_cannot_escape_profile_allowlist(self) -> None:
        approvals: list[str] = []
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "command-1",
                        "name": "run_command",
                        "input": {"command": "python3 -c 'print(1)'"},
                    }
                ],
                [{"type": "text", "text": "The command was outside the profile scope."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            root = Path(base)
            _write_agent(
                root,
                ".agents/agents",
                "file-only",
                "Writes files only",
                "Only use the declared file tool.",
                mode="code",
                tools="write_file",
            )
            workspace = create_run_workspace(root, "run-1")
            action = parse_tool_action("delegate_task", {"task": "Stay scoped", "agent": "file-only"})
            execute_delegate_task_action(
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
                approval_handler=lambda request: (
                    approvals.append(request.action_type)
                    or ApprovalDecision(approved=True, message="approved")
                ),
            )

        result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(result["kind"], "tool_error")
        self.assertIn("selected project agent profile", result["message"])
        self.assertEqual(approvals, [])

    def test_code_subagent_cannot_update_parent_plan_through_todo_alias(self) -> None:
        approvals: list[str] = []
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "todo-1",
                        "name": "TodoWrite",
                        "input": {"todos": [{"content": "Change parent plan", "status": "completed"}]},
                    }
                ],
                [{"type": "text", "text": "TodoWrite was blocked."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            workspace = create_run_workspace(Path(base), "run-1")
            action = parse_tool_action("delegate_task", {"task": "Stay scoped", "mode": "code"})
            execute_delegate_task_action(
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
                approval_handler=lambda request: (
                    approvals.append(request.action_type)
                    or ApprovalDecision(approved=True, message="approved")
                ),
            )

        result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(result["kind"], "tool_error")
        self.assertIn("cannot ask the user, update the parent plan", result["message"])
        self.assertEqual(approvals, [])

    def test_missing_profile_fails_before_model_request(self) -> None:
        client = ProfileClient([])
        with tempfile.TemporaryDirectory(prefix="vibeagent-agents-") as base:
            workspace = create_run_workspace(Path(base), "run-1")
            action = parse_tool_action("delegate_task", {"task": "Use profile", "agent": "missing"})
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
            )

        self.assertFalse(observation.ok)
        self.assertIn("could not be loaded", observation.message)
        self.assertEqual(client.messages, [])


if __name__ == "__main__":
    unittest.main()
