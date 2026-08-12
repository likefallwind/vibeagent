from __future__ import annotations

import json
import tempfile
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from tests.test_plugins import write_demo_plugin
from tests.user_home_test_case import IsolatedUserHomeTestCase
from vibeagent.agent_delegate_profile import load_delegate_profile_runtime
from vibeagent.agent_profile_mcp import with_agent_mcp_servers
from vibeagent.managed_customization import read_managed_customization_policy
from vibeagent.managed_settings import read_file_managed_settings
from vibeagent.mcp_config import McpServerConfig, mcp_config_paths, read_mcp_server_configs
from vibeagent.user_paths import user_home
from vibeagent.types import DelegateTaskAction
from vibeagent.workspace_agents import read_project_agent, read_project_agents
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks
from vibeagent.workspace_skills import read_project_skill, read_project_skills


def _write_skill(root: Path, base: str, name: str, body: str) -> None:
    path = root / base / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {name} instructions\n---\n\n{body}\n",
        encoding="utf-8",
    )


def _write_agent(root: Path, base: str, name: str, body: str) -> None:
    path = root / base / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {name} profile\nmode: explore\n---\n\n{body}\n",
        encoding="utf-8",
    )


def _write_agent_with_hook(root: Path, base: str, name: str, command: str) -> None:
    path = root / base / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
name: {name}
description: {name} profile
mode: explore
hooks:
  PreToolUse:
    - matcher: Read
      hooks:
        - type: command
          command: {command}
---

PROFILE
""",
        encoding="utf-8",
    )


def _write_project_settings(root: Path, payload: dict[str, object]) -> None:
    path = root / ".claude/settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_mcp(path: Path, name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    name: {
                        "command": "/bin/echo",
                        "args": [name],
                    }
                }
            }
        ),
        encoding="utf-8",
    )


class ManagedCustomizationTests(IsolatedUserHomeTestCase):
    def _managed_patches(self, managed: Path) -> ExitStack:
        stack = ExitStack()
        stack.enter_context(
            patch(
                "vibeagent.workspace_settings_sources.read_file_managed_settings",
                lambda: read_file_managed_settings(managed),
            )
        )
        stack.enter_context(
            patch(
                "vibeagent.managed_customization.managed_settings_directory",
                lambda: managed,
            )
        )
        return stack

    def test_selective_policy_ignores_future_surface_names(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                (managed / "managed-settings.json").write_text(
                    json.dumps(
                        {
                            "strictPluginOnlyCustomization": [
                                "skills",
                                "future-surface",
                                42,
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                with self._managed_patches(managed):
                    policy = read_managed_customization_policy(
                        create_run_workspace(project_base, "managed-selective")
                    )

        self.assertEqual(policy.strict_surfaces, frozenset({"skills"}))
        self.assertTrue(policy.sources[0].startswith("managed settings:"))

    def test_strict_policy_keeps_only_plugin_and_managed_sources(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                project = Path(project_base)
                home = user_home()
                plugin = write_demo_plugin(project)
                _write_skill(project, ".claude/skills", "project-skill", "PROJECT_SKILL")
                _write_skill(home, ".claude/skills", "user-skill", "USER_SKILL")
                _write_skill(managed, ".claude/skills", "managed-skill", "MANAGED_SKILL")
                _write_agent(project, ".claude/agents", "project-agent", "PROJECT_AGENT")
                _write_agent(home, ".claude/agents", "user-agent", "USER_AGENT")
                _write_agent(managed, ".claude/agents", "managed-agent", "MANAGED_AGENT")
                _write_mcp(project / ".mcp.json", "project-mcp")
                _write_project_settings(
                    project,
                    {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Read",
                                    "hooks": [
                                        {"type": "command", "command": "project-hook"}
                                    ],
                                }
                            ]
                        }
                    },
                )
                (managed / "managed-settings.json").write_text(
                    json.dumps(
                        {
                            "strictPluginOnlyCustomization": True,
                            "hooks": {
                                "PreToolUse": [
                                    {
                                        "matcher": "Read",
                                        "hooks": [
                                            {"type": "command", "command": "managed-hook"}
                                        ],
                                    }
                                ]
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                workspace = create_run_workspace(
                    project,
                    "managed-all",
                    invocation_plugin_dirs=(plugin,),
                )
                with self._managed_patches(managed):
                    skills = read_project_skills(workspace)
                    agents = read_project_agents(workspace)
                    hooks = read_project_hooks(workspace)
                    servers = read_mcp_server_configs(workspace)
                    strict_cli_servers = read_mcp_server_configs(
                        replace(workspace, strict_mcp_config=True)
                    )
                    managed_skill = read_project_skill(workspace, "managed-skill")
                    managed_agent = read_project_agent(workspace, "managed-agent")

        self.assertEqual(
            {item["name"] for item in skills["skills"]},
            {"demo-plugin:review", "managed-skill"},
        )
        self.assertEqual(
            {item["name"] for item in agents["agents"]},
            {"demo-plugin:reviewer", "managed-agent"},
        )
        self.assertEqual(
            {hook.command for hook in hooks.hooks},
            {"managed-hook", f"{plugin.as_posix()}/bin/check"},
        )
        self.assertEqual([server.name for server in servers], ["demo-plugin.echo"])
        self.assertEqual(strict_cli_servers, [])
        self.assertEqual(managed_skill["source"], "managed")
        self.assertIn("MANAGED_SKILL", managed_skill["content"])
        self.assertEqual(managed_agent["source"], "managed")
        self.assertEqual(managed_agent["prompt"], "MANAGED_AGENT")

    def test_selective_lock_leaves_other_project_surfaces_enabled(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                project = Path(project_base)
                _write_skill(project, ".claude/skills", "project-skill", "PROJECT_SKILL")
                _write_agent(project, ".claude/agents", "project-agent", "PROJECT_AGENT")
                _write_mcp(project / ".mcp.json", "project-mcp")
                _write_project_settings(
                    project,
                    {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Read",
                                    "hooks": [
                                        {"type": "command", "command": "project-hook"}
                                    ],
                                }
                            ]
                        }
                    },
                )
                (managed / "managed-settings.json").write_text(
                    json.dumps({"strictPluginOnlyCustomization": ["skills"]}),
                    encoding="utf-8",
                )
                workspace = create_run_workspace(project, "managed-one")
                with self._managed_patches(managed):
                    skills = read_project_skills(workspace)
                    agents = read_project_agents(workspace)
                    hooks = read_project_hooks(workspace)
                    servers = read_mcp_server_configs(workspace)

        self.assertEqual(skills["skills"], [])
        self.assertEqual([item["name"] for item in agents["agents"]], ["project-agent"])
        self.assertEqual([hook.command for hook in hooks.hooks], ["project-hook"])
        self.assertEqual([server.name for server in servers], ["project-mcp"])

    def test_safe_mode_loads_managed_components_but_not_plugins(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                project = Path(project_base)
                plugin = write_demo_plugin(project)
                _write_skill(managed, ".claude/skills", "managed-skill", "MANAGED_SKILL")
                _write_agent(managed, ".claude/agents", "managed-agent", "MANAGED_AGENT")
                (managed / "managed-settings.json").write_text(
                    json.dumps(
                        {
                            "hooks": {
                                "PreToolUse": [
                                    {
                                        "matcher": "Read",
                                        "hooks": [
                                            {"type": "command", "command": "managed-hook"}
                                        ],
                                    }
                                ]
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                workspace = create_run_workspace(
                    project,
                    "managed-safe",
                    safe_mode=True,
                    invocation_plugin_dirs=(plugin,),
                )
                with self._managed_patches(managed):
                    skills = read_project_skills(workspace)
                    agents = read_project_agents(workspace)
                    hooks = read_project_hooks(workspace)

        self.assertEqual([item["name"] for item in skills["skills"]], ["managed-skill"])
        self.assertEqual([item["name"] for item in agents["agents"]], ["managed-agent"])
        self.assertEqual([hook.command for hook in hooks.hooks], ["managed-hook"])

    def test_strict_mcp_rejects_project_profile_inline_server(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                project = Path(project_base)
                (managed / "managed-settings.json").write_text(
                    json.dumps({"strictPluginOnlyCustomization": ["mcp"]}),
                    encoding="utf-8",
                )
                workspace = create_run_workspace(project, "managed-profile-mcp")
                entry = ({"inline": {"command": "/bin/echo"}},)
                with self._managed_patches(managed):
                    with self.assertRaisesRegex(
                        ValueError,
                        "strictPluginOnlyCustomization",
                    ):
                        with_agent_mcp_servers(
                            workspace,
                            entry,
                            source="claude:reviewer#mcpServers",
                        )
                    managed_workspace = with_agent_mcp_servers(
                        workspace,
                        entry,
                        source="managed:reviewer#mcpServers",
                    )

        self.assertEqual(
            [config.name for config in managed_workspace.profile_mcp_server_configs],
            ["inline"],
        )

    def test_strict_hooks_accepts_only_managed_agent_profile_hooks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                project = Path(project_base)
                (managed / "managed-settings.json").write_text(
                    json.dumps({"strictPluginOnlyCustomization": ["hooks"]}),
                    encoding="utf-8",
                )
                _write_agent_with_hook(
                    project,
                    ".claude/agents",
                    "project-agent",
                    "project-hook",
                )
                _write_agent_with_hook(
                    managed,
                    ".claude/agents",
                    "managed-agent",
                    "managed-hook",
                )
                workspace = create_run_workspace(project, "managed-profile-hooks")
                with self._managed_patches(managed):
                    project_runtime = load_delegate_profile_runtime(
                        workspace,
                        DelegateTaskAction(
                            type="delegate_task",
                            task="Inspect",
                            agent="project-agent",
                            mode="explore",
                        ),
                    )
                    managed_runtime = load_delegate_profile_runtime(
                        workspace,
                        DelegateTaskAction(
                            type="delegate_task",
                            task="Inspect",
                            agent="managed-agent",
                            mode="explore",
                        ),
                    )

        self.assertIsNone(project_runtime.error)
        self.assertIsNone(project_runtime.hooks)
        self.assertIsNone(managed_runtime.error)
        assert managed_runtime.hooks is not None
        self.assertEqual(
            [hook.command for hook in managed_runtime.hooks.hooks],
            ["managed-hook"],
        )

    def test_managed_mcp_file_has_exclusive_control_and_can_disable_mcp(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                project = Path(project_base)
                plugin = write_demo_plugin(project)
                managed_path = managed / "managed-mcp.json"
                _write_mcp(managed_path, "managed-mcp")
                _write_mcp(project / ".mcp.json", "project-mcp")
                workspace = create_run_workspace(
                    project,
                    "managed-mcp",
                    mcp_config_paths=(project / ".mcp.json",),
                    invocation_plugin_dirs=(plugin,),
                )
                with self._managed_patches(managed):
                    workspace = replace(
                        workspace,
                        profile_mcp_server_configs=(
                            McpServerConfig(
                                name="profile-mcp",
                                command="/bin/echo",
                                args=[],
                                cwd=project.as_posix(),
                                env={},
                            ),
                        ),
                    )
                    servers = read_mcp_server_configs(workspace)
                    paths = mcp_config_paths(workspace)
                    with self.assertRaisesRegex(ValueError, "managed-mcp.json"):
                        with_agent_mcp_servers(
                            workspace,
                            ({"inline": {"command": "/bin/echo"}},),
                            source="agent#inline",
                        )
                    managed_path.write_text(
                        json.dumps({"mcpServers": {}}),
                        encoding="utf-8",
                    )
                    disabled = read_mcp_server_configs(workspace)

        self.assertEqual([server.name for server in servers], ["managed-mcp"])
        self.assertEqual(paths, [managed_path])
        self.assertEqual(disabled, [])

    def test_managed_component_wins_same_name_without_strict_lock(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                project = Path(project_base)
                (managed / "managed-settings.json").write_text("{}", encoding="utf-8")
                _write_skill(project, ".claude/skills", "review", "PROJECT_SKILL")
                _write_skill(managed, ".claude/skills", "review", "MANAGED_SKILL")
                _write_agent(project, ".claude/agents", "reviewer", "PROJECT_AGENT")
                _write_agent(managed, ".claude/agents", "reviewer", "MANAGED_AGENT")
                workspace = create_run_workspace(project, "managed-precedence")
                with self._managed_patches(managed):
                    skill = read_project_skill(workspace, "review")
                    agent = read_project_agent(workspace, "reviewer")

        self.assertEqual(skill["source"], "managed")
        self.assertIn("MANAGED_SKILL", skill["content"])
        self.assertEqual(agent["source"], "managed")
        self.assertEqual(agent["prompt"], "MANAGED_AGENT")
