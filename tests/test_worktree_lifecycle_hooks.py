from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from vibeagent.actions import parse_tool_action
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.cli_worktree import create_cli_worktree
from vibeagent.types import ApprovalDecision, AssistantResponse
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks
from vibeagent.workspace_permissions import ProjectPermissions
from vibeagent.worktree_hooks import WorktreeHookContext


class TextClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, messages, tools=None, **_kwargs):
        self.calls += 1
        content = [{"type": "text", "text": "Isolated inspection complete."}]
        return AssistantResponse(content=content, raw={"content": content})


def approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


def write_hooks(root: Path, create_command: str, remove_command: str) -> None:
    path = root / ".vibeagent" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "WorktreeCreate": [{"matcher": "ignored", "hooks": [{"type": "command", "command": create_command}]}],
                "WorktreeRemove": [{"matcher": "ignored", "hooks": [{"type": "command", "command": remove_command}]}],
            }
        ),
        encoding="utf-8",
    )


def commands(storage: Path) -> tuple[str, str]:
    create = (
        'python3 -c "import json,sys,pathlib; d=json.load(sys.stdin); '
        f"p=pathlib.Path({str(storage)!r})/d['name']; p.mkdir(parents=True); print(p)\""
    )
    remove = (
        'python3 -c "import json,sys,shutil; d=json.load(sys.stdin); '
        "shutil.rmtree(d['worktree_path'])\""
    )
    return create, remove


def context(workspace):
    return WorktreeHookContext(
        read_project_hooks(workspace), ProjectPermissions(), "ask", approve, 10_000
    )


class WorktreeLifecycleHookTests(unittest.TestCase):
    def test_cli_worktree_create_hook_replaces_git_backend(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-worktree-hook-") as base:
            root = Path(base)
            storage = root / "custom"
            create, remove = commands(storage)
            write_hooks(root, create, remove)
            workspace = create_run_workspace(root, "cli-worktree")
            result = create_cli_worktree(root, "feature", hook_context=context(workspace))

        self.assertEqual(result.root, storage / "feature")
        self.assertEqual(result.branch, "hook/feature")

    def test_subagent_create_and_remove_hooks_wrap_isolated_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-worktree-hook-") as base:
            root = Path(base)
            storage = root / "custom"
            create, remove = commands(storage)
            write_hooks(root, create, remove)
            workspace = create_run_workspace(root, "hook-isolation")
            client = TextClient()
            result = execute_delegate_task_action(
                workspace,
                parse_tool_action("Agent", {"prompt": "Inspect", "isolation": "worktree"}),
                client,
                parent_iteration=1,
                subagent_id="delegate-1-1",
                max_output_tokens=1024,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=approve,
                hooks=read_project_hooks(workspace),
            )

        self.assertTrue(result.ok)
        self.assertFalse(result.worktree_preserved)
        self.assertFalse(Path(result.worktree_path or "missing").exists())
        self.assertEqual(client.calls, 1)

    def test_create_hook_without_path_fails_before_model_call(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-worktree-hook-") as base:
            root = Path(base)
            write_hooks(root, "python3 -c 'print()'", "python3 -V")
            workspace = create_run_workspace(root, "hook-failure")
            client = TextClient()
            result = execute_delegate_task_action(
                workspace,
                parse_tool_action("Agent", {"prompt": "Inspect", "isolation": "worktree"}),
                client,
                parent_iteration=1,
                subagent_id="delegate-1-1",
                max_output_tokens=1024,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=approve,
                hooks=read_project_hooks(workspace),
            )

        self.assertFalse(result.ok)
        self.assertIn("did not return", result.message)
        self.assertEqual(client.calls, 0)


if __name__ == "__main__":
    unittest.main()
