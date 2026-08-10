from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from tests.test_project_agents import _write_agent
from vibeagent.agent_delegate_profile import load_delegate_profile_runtime
from vibeagent.agent_run_setup import prepare_agent_run
from vibeagent.main_agent_settings import resolve_main_agent_selection
from vibeagent.types import DelegateTaskAction
from vibeagent.workspace_agents import read_project_agent, read_project_agents
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_memory import (
    MemoryStoreError,
    project_memory_root,
    read_auto_memory,
    read_memory_file,
    with_agent_memory,
    write_memory_file,
)


class UserAgentProfileTests(unittest.TestCase):
    def test_user_agent_is_recursively_discovered_across_projects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-agent-") as base:
            root = Path(base)
            home = root / "home"
            project_a = root / "project-a"
            project_b = root / "project-b"
            home.mkdir()
            project_a.mkdir()
            project_b.mkdir()
            _write_agent(
                home,
                ".claude/agents/reviewers",
                "cross-project-reviewer",
                "Reviews every project",
                "USER_REVIEW_PROMPT",
                mode="code",
                tools="[Read, Write]",
                memory="user",
            )

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                catalog_a = read_project_agents(create_run_workspace(project_a, "user-a"))
                workspace_b = create_run_workspace(project_b, "user-b")
                loaded_b = read_project_agent(workspace_b, "cross-project-reviewer")

            self.assertEqual(catalog_a["total"], 1)
            self.assertEqual(catalog_a["agents"][0]["source"], "user")
            self.assertTrue(str(catalog_a["agents"][0]["path"]).startswith(str(home)))
            self.assertEqual(loaded_b["prompt"], "USER_REVIEW_PROMPT")
            self.assertEqual(loaded_b["memory"], "user")

    def test_project_agent_overrides_user_agent_with_the_same_name(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-agent-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            _write_agent(
                home,
                ".claude/agents",
                "reviewer",
                "User reviewer",
                "USER_PROMPT",
            )
            _write_agent(
                project,
                ".claude/agents",
                "reviewer",
                "Project reviewer",
                "PROJECT_PROMPT",
            )

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                workspace = create_run_workspace(project, "precedence")
                catalog = read_project_agents(workspace)
                loaded = read_project_agent(workspace, "reviewer")

            self.assertEqual(catalog["total"], 1)
            self.assertEqual(catalog["agents"][0]["source"], "claude")
            self.assertEqual(loaded["prompt"], "PROJECT_PROMPT")

    def test_user_default_agent_is_below_project_settings_and_above_plugin_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-agent-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            _write_agent(
                home,
                ".claude/agents",
                "user-default",
                "User default",
                "USER_DEFAULT_PROMPT",
            )
            user_settings = home / ".claude/settings.json"
            user_settings.parent.mkdir(parents=True, exist_ok=True)
            user_settings.write_text(
                json.dumps({"agent": "user-default"}),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                workspace = create_run_workspace(project, "user-default")
                selected_user = resolve_main_agent_selection(workspace, None)
                project_settings = project / ".claude/settings.json"
                project_settings.parent.mkdir(parents=True)
                project_settings.write_text(
                    json.dumps({"agent": "project-default"}),
                    encoding="utf-8",
                )
                selected_project = resolve_main_agent_selection(workspace, None)

            self.assertEqual(
                (selected_user.name, selected_user.source),
                ("user-default", "~/.claude/settings.json"),
            )
            self.assertEqual(
                (selected_project.name, selected_project.source),
                ("project-default", ".claude/settings.json"),
            )

    def test_user_agent_settings_symlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-agent-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            outside = root / "settings.json"
            outside.write_text(json.dumps({"agent": "reviewer"}), encoding="utf-8")
            settings = home / ".claude/settings.json"
            settings.parent.mkdir(parents=True)
            settings.symlink_to(outside)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                workspace = create_run_workspace(project, "user-settings-link")
                with self.assertRaisesRegex(ValueError, "non-symlink"):
                    resolve_main_agent_selection(workspace, None)

    def test_user_memory_is_shared_across_projects_and_uses_private_modes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-agent-") as base:
            root = Path(base)
            home = root / "home"
            project_a = root / "project-a"
            project_b = root / "project-b"
            home.mkdir()
            project_a.mkdir()
            project_b.mkdir()

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                memory_a = with_agent_memory(
                    create_run_workspace(project_a, "memory-a"),
                    "reviewer",
                    "user",
                )
                memory_b = with_agent_memory(
                    create_run_workspace(project_b, "memory-b"),
                    "reviewer",
                    "user",
                )
                write_memory_file(memory_a, "MEMORY.md", "Cross-project pattern.\n")
                content, _truncated = read_memory_file(memory_b)
                memory_root = project_memory_root(memory_a)

            self.assertEqual(content, "Cross-project pattern.\n")
            self.assertEqual(memory_root, home / ".claude/agent-memory/reviewer")
            self.assertEqual(stat.S_IMODE(memory_root.stat().st_mode), 0o700)
            self.assertEqual(
                stat.S_IMODE(memory_root.joinpath("MEMORY.md").stat().st_mode),
                0o600,
            )

    def test_user_profile_loads_memory_for_main_and_delegated_agents(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-agent-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            _write_agent(
                home,
                ".claude/agents",
                "remembering",
                "Remembers patterns",
                "USER_MEMORY_PROFILE",
                mode="code",
                tools="Read",
                memory="user",
            )
            memory_path = home / ".claude/agent-memory/remembering/MEMORY.md"
            memory_path.parent.mkdir(parents=True)
            memory_path.write_text("GLOBAL_AGENT_MEMORY\n", encoding="utf-8")

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                workspace = create_run_workspace(project, "delegate-user-memory")
                delegated = load_delegate_profile_runtime(
                    workspace,
                    DelegateTaskAction(
                        type="delegate_task",
                        task="Review",
                        agent="remembering",
                        mode="code",
                    ),
                )
                main = prepare_agent_run(
                    "Recall patterns",
                    base_dir=project,
                    workspace=None,
                    prior_context=None,
                    approval_policy="ask",
                    task_metadata=None,
                    trust_project_permissions=False,
                    permission_overrides=None,
                    mcp_config_paths=(),
                    strict_mcp_config=False,
                    system_prompt=None,
                    append_system_prompt=None,
                    agent="remembering",
                )

            self.assertIsNone(delegated.error)
            self.assertEqual(delegated.memory_scope, "user")
            self.assertIn("GLOBAL_AGENT_MEMORY", delegated.prompt or "")
            self.assertEqual(main.workspace.memory_scope, "user")
            self.assertIn("GLOBAL_AGENT_MEMORY", str(main.messages))

    def test_user_memory_rejects_symlinked_store(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-agent-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            outside = root / "outside"
            home.mkdir()
            project.mkdir()
            outside.mkdir()
            memory_parent = home / ".claude/agent-memory"
            memory_parent.parent.mkdir(parents=True)
            memory_parent.symlink_to(outside, target_is_directory=True)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                workspace = with_agent_memory(
                    create_run_workspace(project, "unsafe-user-memory"),
                    "reviewer",
                    "user",
                )
                snapshot = read_auto_memory(workspace)
                with self.assertRaises(MemoryStoreError):
                    write_memory_file(workspace, "MEMORY.md", "blocked\n")

            self.assertIsNotNone(snapshot.error)
            self.assertIn("symlink", snapshot.error or "")
            self.assertFalse(outside.joinpath("reviewer/MEMORY.md").exists())

    def test_user_agent_symlink_is_reported_as_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-agent-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            outside = root / "linked.md"
            outside.write_text(
                "---\nname: linked\ndescription: Linked agent\n---\n\nDo work.\n",
                encoding="utf-8",
            )
            agents = home / ".claude/agents"
            agents.mkdir(parents=True)
            agents.joinpath("linked.md").symlink_to(outside)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                catalog = read_project_agents(create_run_workspace(project, "linked-user"))

            self.assertEqual(catalog["total"], 1)
            self.assertFalse(catalog["agents"][0]["available"])
            self.assertIn("symbolic link", str(catalog["agents"][0]["message"]))


if __name__ == "__main__":
    unittest.main()
