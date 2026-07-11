import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.prompts import build_messages
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock, ProjectAgentsAction
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
) -> Path:
    path = root / base / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    tool_line = f"tools: {tools}\n" if tools is not None else ""
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\nmode: {mode}\n{tool_line}---\n\n{body}\n",
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


class ProjectAgentProfileTests(unittest.TestCase):
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
        self.assertEqual(catalog["agents"][0]["tools"], ["read_file", "write_file"])
        self.assertNotIn("prompt", catalog["agents"][0])
        self.assertIn("test-writer: Writes focused tests", formatted or "")
        self.assertNotIn("PRIVATE_AGENT_PROMPT", str(initial_messages[1].content))
        self.assertEqual(loaded["prompt"], "PRIVATE_AGENT_PROMPT")

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
        self.assertIn("forbidden tool", messages["recursive"])
        self.assertIn("symbolic link", messages["linked"])
        self.assertEqual(catalog["invalid"], 6)

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
        self.assertEqual(set(client.tool_names[0]), {"finish", "write_file"})
        self.assertIn("PROFILE_SPECIAL_INSTRUCTION", str(client.messages[0][0].content))

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
        self.assertEqual(set(client.tool_names[0]), {"finish", "read_file"})
        result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(result["kind"], "read_file")
        self.assertEqual(result["path"], "README.md")

    def test_code_profile_bash_alias_allows_background_bash(self) -> None:
        approvals: list[str] = []
        client = ProfileClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "bash-1",
                        "name": "Bash",
                        "input": {"command": "python3 -c \"print('ready')\"", "run_in_background": True},
                    }
                ],
                [{"type": "text", "text": "Started the command."}],
            ]
        )
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

        self.assertEqual(loaded["tools"], ["run_command", "start_command"])
        self.assertTrue(observation.ok)
        self.assertEqual(set(client.tool_names[0]), {"finish", "run_command", "start_command"})
        result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(result["kind"], "start_command")
        self.assertEqual(approvals, ["start_command"])

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

        self.assertEqual(loaded["tools"], ["session_plan"])
        self.assertTrue(observation.ok)
        self.assertEqual(set(client.tool_names[0]), {"finish", "session_plan"})
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
        self.assertIn("allowlist", result["message"])
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
        self.assertIn("cannot ask the user, update the parent plan, or delegate again", result["message"])
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
