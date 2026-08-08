import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from vibeagent.actions import AGENT_TOOL_DEFINITIONS, ActionParseError, execute_action, parse_tool_action
from vibeagent.action_tool_aliases import profile_tool_names, tool_name_candidates
from vibeagent.agent import run_agent
from vibeagent.agent_approval import build_approval_request
from vibeagent.agent_workspace_transition import apply_workspace_transition
from vibeagent.agent_delegate_tools import code_delegate_initial_tool_names, delegate_tool_definitions
from vibeagent.tool_catalog_core import tool_category, tool_name_requires_approval
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace import create_run_workspace


class WorktreeAgentClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []
        self.tools: list[list[dict]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        self.tools.append(list(tools or []))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


def init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
    (root / "app.py").write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)


class WorktreeToolTests(unittest.TestCase):
    def test_aliases_schema_category_and_approval_are_registered(self) -> None:
        enter = parse_tool_action("EnterWorktree", {"name": "feature"})
        exit_action = parse_tool_action("ExitWorktree", {})

        self.assertEqual((enter.type, enter.name, enter.path), ("enter_worktree", "feature", None))
        self.assertEqual(exit_action.type, "exit_worktree")
        self.assertIn("EnterWorktree", tool_name_candidates("enter_worktree", enter))
        self.assertEqual(profile_tool_names("EnterWorktree"), frozenset({"EnterWorktree", "enter_worktree"}))
        self.assertEqual(profile_tool_names("ExitWorktree"), frozenset({"ExitWorktree", "exit_worktree"}))
        self.assertTrue(tool_name_requires_approval("EnterWorktree"))
        self.assertFalse(tool_name_requires_approval("ExitWorktree"))
        self.assertEqual(tool_category("EnterWorktree"), "git")
        self.assertEqual(tool_category("ExitWorktree"), "git")
        self.assertEqual(build_approval_request(enter).action_type, "enter_worktree")
        names = {str(tool["name"]) for tool in AGENT_TOOL_DEFINITIONS}
        self.assertIn("EnterWorktree", names)
        self.assertIn("ExitWorktree", names)
        with self.assertRaises(ActionParseError):
            parse_tool_action("EnterWorktree", {"name": "feature", "path": "/tmp/feature"})

    def test_subagents_do_not_receive_parent_workspace_transition_tools(self) -> None:
        active = code_delegate_initial_tool_names("ask")
        definitions = delegate_tool_definitions("code", active, "ask")
        names = {str(tool["name"]) for tool in definitions}

        self.assertNotIn("EnterWorktree", active)
        self.assertNotIn("ExitWorktree", active)
        self.assertNotIn("EnterWorktree", names)
        self.assertNotIn("ExitWorktree", names)

    def test_create_isolates_files_and_exit_preserves_linked_worktree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-worktree-") as base:
            root = Path(base)
            init_git_repo(root)
            main_workspace = create_run_workspace(root, "run-1")
            entered = execute_action(main_workspace, parse_tool_action("EnterWorktree", {"name": "feature"}))
            linked_root = Path(entered.path)
            linked_workspace = create_run_workspace(linked_root, "run-2")
            (linked_root / "app.py").write_text("value = 2\n", encoding="utf-8")
            exited = execute_action(linked_workspace, parse_tool_action("ExitWorktree", {}))

            self.assertTrue(entered.ok)
            self.assertTrue(entered.created)
            self.assertEqual(entered.branch, "vibeagent/feature")
            self.assertEqual((root / "app.py").read_text(encoding="utf-8"), "value = 1\n")
            self.assertEqual((linked_root / "app.py").read_text(encoding="utf-8"), "value = 2\n")
            self.assertTrue(exited.ok)
            self.assertEqual(Path(exited.path), root)
            self.assertEqual(Path(exited.preserved_worktree), linked_root)
            self.assertTrue(linked_root.is_dir())

    def test_enter_existing_registered_worktree_and_reject_unregistered_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-worktree-") as base:
            root = Path(base)
            init_git_repo(root)
            existing = root.parent / f"{root.name}-existing"
            subprocess.run(["git", "worktree", "add", "--quiet", "-b", "existing", str(existing), "HEAD"], cwd=root, check=True)
            try:
                workspace = create_run_workspace(root, "run-1")
                entered = execute_action(workspace, parse_tool_action("EnterWorktree", {"path": str(existing)}))
                rejected = execute_action(workspace, parse_tool_action("EnterWorktree", {"path": str(root.parent)}))
            finally:
                subprocess.run(["git", "worktree", "remove", "--force", str(existing)], cwd=root, check=False)

        self.assertTrue(entered.ok)
        self.assertFalse(entered.created)
        self.assertEqual(Path(entered.path), existing)
        self.assertFalse(rejected.ok)
        self.assertIn("not a registered worktree", rejected.message)

    def test_new_worktree_rejects_symlink_storage_and_untracked_project_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-worktree-") as base, tempfile.TemporaryDirectory(
            prefix="vibeagent-worktree-outside-"
        ) as outside:
            root = Path(base)
            init_git_repo(root)
            workspace = create_run_workspace(root, "run-1")
            (root / ".vibeagent" / "worktrees").symlink_to(Path(outside), target_is_directory=True)
            symlinked = execute_action(workspace, parse_tool_action("EnterWorktree", {"name": "unsafe"}))
            (root / ".vibeagent" / "worktrees").unlink()
            (root / "scratch").mkdir()
            subdirectory_workspace = create_run_workspace(root / "scratch", "run-2")
            untracked = execute_action(
                subdirectory_workspace,
                parse_tool_action("EnterWorktree", {"name": "missing-subdir"}),
            )
            outside_entries = list(Path(outside).iterdir())

        self.assertFalse(symlinked.ok)
        self.assertIn("must not be a symlink", symlinked.message)
        self.assertEqual(outside_entries, [])
        self.assertFalse(untracked.ok)
        self.assertIn("not present in HEAD", untracked.message)

    def test_agent_changes_execution_root_and_returns_to_main_worktree(self) -> None:
        client = WorktreeAgentClient(
            [
                [{"type": "tool_call", "id": "enter-1", "name": "EnterWorktree", "input": {"name": "agent-loop"}}],
                [{"type": "tool_call", "id": "git-1", "name": "git_info", "input": {}}],
                [{"type": "tool_call", "id": "exit-1", "name": "ExitWorktree", "input": {}}],
                [{"type": "tool_call", "id": "git-2", "name": "git_info", "input": {}}],
                [{"type": "text", "text": "The isolated and main roots were verified."}],
            ]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-worktree-agent-") as base:
            root = Path(base)
            init_git_repo(root)
            result = run_agent(
                "Verify isolated worktree execution",
                base_dir=root,
                client=client,
                max_iterations=5,
                approval_handler=lambda _request: ApprovalDecision(approved=True, message="approved"),
            )
            events = [
                json.loads(line)
                for line in (root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        self.assertTrue(result.success)
        first_tools = {str(tool["name"]) for tool in client.tools[0]}
        second_tools = {str(tool["name"]) for tool in client.tools[1]}
        self.assertIn("EnterWorktree", first_tools)
        self.assertNotIn("ExitWorktree", first_tools)
        self.assertIn("ExitWorktree", second_tools)
        self.assertEqual(
            [observation.kind for observation in result.observations],
            ["enter_worktree", "git_info", "exit_worktree", "git_info"],
        )
        linked_root = Path(result.observations[0].path)
        self.assertEqual(result.observations[1].branch, "vibeagent/agent-loop")
        self.assertNotEqual(result.observations[3].branch, "vibeagent/agent-loop")
        self.assertEqual(Path(result.observations[2].preserved_worktree), linked_root)
        transitions = [event for event in events if event["type"] == "workspace_changed"]
        self.assertEqual([event["kind"] for event in transitions], ["enter_worktree", "exit_worktree"])
        self.assertEqual(Path(transitions[-1]["root"]), root)

    def test_nested_worktree_transitions_return_to_each_previous_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-worktree-nested-") as base:
            root = Path(base)
            init_git_repo(root)
            main = create_run_workspace(root, "run-1")
            first_observation = execute_action(main, parse_tool_action("EnterWorktree", {"name": "first"}))
            first = apply_workspace_transition(main, first_observation, iteration=1)
            second_observation = execute_action(first, parse_tool_action("EnterWorktree", {"name": "second"}))
            second = apply_workspace_transition(first, second_observation, iteration=2)
            exit_second_observation = execute_action(second, parse_tool_action("ExitWorktree", {}))
            returned_first = apply_workspace_transition(second, exit_second_observation, iteration=3)
            exit_first_observation = execute_action(returned_first, parse_tool_action("ExitWorktree", {}))
            returned_main = apply_workspace_transition(returned_first, exit_first_observation, iteration=4)

        self.assertEqual(returned_first.root, first.root)
        self.assertEqual(returned_first.root_history, (root,))
        self.assertEqual(returned_main.root, root)
        self.assertEqual(returned_main.root_history, ())


if __name__ == "__main__":
    unittest.main()
