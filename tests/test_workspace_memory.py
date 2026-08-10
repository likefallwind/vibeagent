from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from vibeagent.action_memory_types import MemoryWriteAction
from vibeagent.action_parsing import ActionParseError, parse_tool_action
from vibeagent.actions import execute_action
from vibeagent.agent_approval import build_approval_request
from vibeagent.agent_approval_preview import attach_approval_preview
from vibeagent.prompts import build_messages
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_memory import (
    MEMORY_STARTUP_MAX_BYTES,
    MEMORY_STARTUP_MAX_LINES,
    MemoryStoreError,
    auto_memory_enabled,
    list_memory_files,
    project_memory_root,
    read_auto_memory,
    read_memory_file,
    with_agent_memory,
    write_memory_file,
)


class WorkspaceMemoryTests(unittest.TestCase):
    def test_memory_write_read_list_and_secret_redaction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = create_run_workspace(temp_dir, run_id="memory-basic")

            result = write_memory_file(
                workspace,
                "MEMORY.md",
                "# Notes\nAPI_KEY=sk-verysecretvalue\n",
            )

            content, truncated = read_memory_file(workspace)
            self.assertFalse(truncated)
            self.assertTrue(result.redacted)
            self.assertIn("API_KEY=[REDACTED]", content)
            self.assertNotIn("verysecretvalue", content)
            self.assertEqual([item.path for item in list_memory_files(workspace)], ["MEMORY.md"])

    def test_append_is_atomic_and_preserves_existing_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = create_run_workspace(temp_dir, run_id="memory-append")
            write_memory_file(workspace, "debugging.md", "first\n")

            write_memory_file(workspace, "debugging.md", "second\n", mode="append")

            self.assertEqual(read_memory_file(workspace, "debugging.md")[0], "first\nsecond\n")
            self.assertEqual(list(project_memory_root(workspace).glob("*.tmp")), [])

    def test_startup_memory_is_limited_by_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = create_run_workspace(temp_dir, run_id="memory-lines")
            content = "".join(f"line {index}\n" for index in range(MEMORY_STARTUP_MAX_LINES + 5))
            write_memory_file(workspace, "MEMORY.md", content)

            snapshot = read_auto_memory(workspace)

            self.assertTrue(snapshot.truncated)
            self.assertEqual(len(snapshot.content.splitlines()), MEMORY_STARTUP_MAX_LINES)
            self.assertNotIn(f"line {MEMORY_STARTUP_MAX_LINES}", snapshot.content)

    def test_startup_memory_is_limited_by_utf8_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = create_run_workspace(temp_dir, run_id="memory-bytes")
            write_memory_file(workspace, "MEMORY.md", "x" * (MEMORY_STARTUP_MAX_BYTES + 20))

            snapshot = read_auto_memory(workspace)

            self.assertTrue(snapshot.truncated)
            self.assertLessEqual(len(snapshot.content.encode("utf-8")), MEMORY_STARTUP_MAX_BYTES)

    def test_auto_memory_can_be_disabled_by_environment_or_project_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = create_run_workspace(temp_dir, run_id="memory-disabled")
            self.assertFalse(auto_memory_enabled(workspace, {"VIBEAGENT_DISABLE_AUTO_MEMORY": "1"}))
            config_path = Path(temp_dir) / ".vibeagent" / "config.json"
            config_path.write_text(json.dumps({"auto_memory_enabled": False}), encoding="utf-8")
            self.assertFalse(auto_memory_enabled(workspace, {}))

    def test_prompt_loads_memory_as_historical_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = create_run_workspace(temp_dir, run_id="memory-prompt")
            write_memory_file(workspace, "MEMORY.md", "Use unittest for focused tests.\n")

            prompt = str(build_messages("Inspect tests", workspace)[1].content)

            self.assertIn("Auto memory from prior sessions:", prompt)
            self.assertIn("historical context", prompt)
            self.assertIn("Use unittest for focused tests.", prompt)

    def test_memory_paths_reject_traversal_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = create_run_workspace(temp_dir, run_id="memory-paths")
            with self.assertRaises(MemoryStoreError):
                write_memory_file(workspace, "../outside.md", "blocked")
            root = project_memory_root(workspace)
            root.mkdir(parents=True)
            outside = Path(temp_dir) / "outside.md"
            outside.write_text("outside", encoding="utf-8")
            (root / "MEMORY.md").symlink_to(outside)
            with self.assertRaises(MemoryStoreError):
                read_memory_file(workspace)

    def test_git_worktrees_share_main_worktree_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            main = Path(temp_dir) / "main"
            linked = Path(temp_dir) / "linked"
            main.mkdir()
            self._git(main, "init", "-q")
            self._git(main, "config", "user.name", "Test User")
            self._git(main, "config", "user.email", "test@example.com")
            (main / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            self._git(main, "add", "tracked.txt")
            self._git(main, "commit", "-qm", "initial")
            self._git(main, "worktree", "add", "-q", "-b", "linked", str(linked))
            main_workspace = create_run_workspace(main, run_id="memory-main")
            linked_workspace = create_run_workspace(linked, run_id="memory-linked")

            write_memory_file(linked_workspace, "MEMORY.md", "shared\n")

            self.assertEqual(project_memory_root(main_workspace), project_memory_root(linked_workspace))
            self.assertEqual(read_memory_file(main_workspace)[0], "shared\n")

    def test_agent_memory_scopes_are_isolated_and_reject_symlink_components(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="agent-memory")
            project_agent = with_agent_memory(workspace, "reviewer", "project")
            local_agent = with_agent_memory(workspace, "reviewer", "local")
            other_agent = with_agent_memory(workspace, "debugger", "project")

            write_memory_file(project_agent, "MEMORY.md", "project reviewer\n")
            write_memory_file(local_agent, "MEMORY.md", "local reviewer\n")
            write_memory_file(other_agent, "MEMORY.md", "project debugger\n")

            self.assertEqual(
                project_memory_root(project_agent),
                root / ".claude/agent-memory/reviewer",
            )
            self.assertEqual(
                project_memory_root(local_agent),
                root / ".claude/agent-memory-local/reviewer",
            )
            self.assertEqual(read_memory_file(project_agent)[0], "project reviewer\n")
            self.assertEqual(read_memory_file(local_agent)[0], "local reviewer\n")
            self.assertEqual(read_memory_file(other_agent)[0], "project debugger\n")
            self.assertEqual(read_memory_file(workspace)[0], "")

            unsafe = root / ".claude/agent-memory/unsafe"
            outside = root / "outside-memory"
            outside.mkdir()
            unsafe.symlink_to(outside, target_is_directory=True)
            unsafe_workspace = with_agent_memory(workspace, "unsafe", "project")
            with self.assertRaises(MemoryStoreError):
                write_memory_file(unsafe_workspace, "MEMORY.md", "blocked\n")

    def test_memory_tools_parse_execute_and_require_write_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = create_run_workspace(temp_dir, run_id="memory-tools")
            action = parse_tool_action(
                "memory_write",
                {"path": "MEMORY.md", "content": "# Index\n", "mode": "replace"},
            )
            self.assertIsInstance(action, MemoryWriteAction)
            request = build_approval_request(action)
            self.assertIsNotNone(request)
            self.assertEqual(request.action_type, "memory_write")
            preview = execute_action(
                workspace,
                parse_tool_action(
                    "check_memory_write",
                    {"path": "MEMORY.md", "content": "# Index\n", "mode": "replace"},
                ),
            )
            self.assertTrue(preview.ok)
            self.assertIn("+# Index", preview.diff)
            self.assertFalse((project_memory_root(workspace) / "MEMORY.md").exists())
            request = attach_approval_preview(request, action, [preview])
            self.assertIn("diffSha256=", request.preview)
            written = execute_action(workspace, action)
            self.assertTrue(written.ok)
            read = execute_action(workspace, parse_tool_action("memory_read", {}))
            self.assertTrue(read.ok)
            self.assertEqual(read.content, "# Index\n")
            listed = execute_action(workspace, parse_tool_action("memory_list", {}))
            self.assertEqual([item.path for item in listed.files], ["MEMORY.md"])

    def test_memory_tool_parser_rejects_invalid_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = create_run_workspace(temp_dir, run_id="memory-invalid-tool")
            observation = execute_action(
                workspace,
                parse_tool_action("memory_write", {"path": "notes.txt", "content": "x"}),
            )
            self.assertFalse(observation.ok)
            self.assertIn("Markdown filename", observation.message)
        with self.assertRaises(ActionParseError):
            parse_tool_action("memory_write", {"path": "MEMORY.md", "content": "x", "mode": "merge"})

    @staticmethod
    def _git(root: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


if __name__ == "__main__":
    unittest.main()
