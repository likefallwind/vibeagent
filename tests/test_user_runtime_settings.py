from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.actions import parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.agent_permissions import authorize_tool_action
from vibeagent.types import ApprovalRequest, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_hooks import matching_project_hooks, read_project_hooks
from vibeagent.workspace_permissions import match_project_permission, read_project_permissions
from vibeagent.workspace_sandbox import read_workspace_sandbox


class RuntimeSettingsClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


def _write_settings(home_or_project: Path, payload: dict[str, object]) -> Path:
    path = home_or_project / ".claude/settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class UserRuntimeSettingsTests(unittest.TestCase):
    def test_user_permissions_are_cross_project_trusted_and_merge_with_project_denies(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-settings-") as base:
            root = Path(base)
            home = root / "home"
            project_a = root / "project-a"
            project_b = root / "project-b"
            home.mkdir()
            project_a.mkdir()
            project_b.mkdir()
            _write_settings(
                home,
                {
                    "permissions": {
                        "allow": [
                            "Bash(python3 -m unittest *)",
                            "Bash(printf 'first\nsecond' > report.txt)",
                        ]
                    }
                },
            )
            _write_settings(
                project_b,
                {"permissions": {"deny": ["Bash(python3 -m unittest discover *)"]}},
            )
            action = parse_tool_action(
                "Bash",
                {"command": "python3 -m unittest tests.test_app"},
            )
            denied_action = parse_tool_action(
                "Bash",
                {"command": "python3 -m unittest discover -s tests"},
            )
            multiline_action = parse_tool_action(
                "Bash",
                {"command": "printf 'first\nsecond' > report.txt"},
            )

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                workspace_a = create_run_workspace(project_a, "user-permissions-a")
                permissions_a = read_project_permissions(workspace_a)
                authorization = authorize_tool_action(
                    workspace_a,
                    permissions_a,
                    "Bash",
                    action,
                    1,
                    None,
                    "ask",
                    None,
                    default_request=ApprovalRequest(
                        action_type="run_command",
                        target="python3 -m unittest tests.test_app",
                        risk="Runs project tests.",
                    ),
                )
                permissions_b = read_project_permissions(
                    create_run_workspace(project_b, "user-permissions-b")
                )

        self.assertTrue(authorization.allowed)
        self.assertEqual(permissions_a.sources, ("~/.claude/settings.json",))
        self.assertEqual(
            permissions_a.trusted_allow_sources,
            ("~/.claude/settings.json",),
        )
        self.assertEqual(
            match_project_permission(permissions_b, "Bash", denied_action).effect,
            "deny",
        )
        self.assertEqual(
            match_project_permission(permissions_a, "Bash", multiline_action).effect,
            "allow",
        )

    def test_user_hook_runs_in_another_project_with_project_directory_environment(self) -> None:
        hook_command = (
            "python3 -c \"import os,pathlib; "
            "pathlib.Path(os.environ['CLAUDE_PROJECT_DIR'], 'user-hook.log').write_text('ran')\""
        )
        client = RuntimeSettingsClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "read-1",
                        "name": "Read",
                        "input": {"file_path": "app.py"},
                    }
                ],
                [{"type": "text", "text": "Read app.py."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-settings-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            project.joinpath("app.py").write_text("value = 1\n", encoding="utf-8")
            _write_settings(
                home,
                {
                    "permissions": {"allow": ["Bash"]},
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Read",
                                "hooks": [
                                    {"type": "command", "command": hook_command}
                                ],
                            }
                        ]
                    },
                },
            )

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                workspace = create_run_workspace(project, "user-hook-catalog")
                hooks = read_project_hooks(workspace)
                result = run_agent(
                    "Read app.py",
                    base_dir=project,
                    client=client,
                    max_iterations=2,
                )
                hook_output = project.joinpath("user-hook.log").read_text(encoding="utf-8")

        self.assertIsNone(hooks.error)
        self.assertEqual(hooks.sources, ("~/.claude/settings.json",))
        self.assertEqual(len(matching_project_hooks(hooks, "PreToolUse", "Read")), 1)
        self.assertTrue(result.success)
        self.assertEqual(hook_output, "ran")

    def test_user_sandbox_trusts_user_exceptions_but_not_project_additions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-settings-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            user_cache = root / "user-cache"
            project_cache = root / "project-cache"
            home.mkdir()
            project.mkdir()
            user_cache.mkdir()
            project_cache.mkdir()
            _write_settings(
                home,
                {
                    "sandbox": {
                        "enabled": True,
                        "excludedCommands": ["docker *"],
                        "filesystem": {"allowWrite": [str(user_cache)]},
                    }
                },
            )

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                workspace = create_run_workspace(project, "user-sandbox")
                user_config = read_workspace_sandbox(workspace)
                _write_settings(
                    project,
                    {
                        "sandbox": {
                            "enabled": False,
                            "excludedCommands": ["podman *"],
                            "filesystem": {"allowWrite": [str(project_cache)]},
                        }
                    },
                )
                untrusted = read_workspace_sandbox(workspace)
                trusted = read_workspace_sandbox(
                    replace(workspace, project_config_trusted=True)
                )

        self.assertIsNone(user_config.error)
        self.assertEqual(user_config.sources, ("~/.claude/settings.json",))
        self.assertEqual(user_config.allow_write, (user_cache.resolve(),))
        self.assertEqual(user_config.excluded_commands, ("docker *",))
        self.assertIn("requires explicit project configuration trust", untrusted.error or "")
        self.assertIsNone(trusted.error)
        self.assertFalse(trusted.enabled)
        self.assertEqual(
            trusted.allow_write,
            (user_cache.resolve(), project_cache.resolve()),
        )
        self.assertEqual(trusted.excluded_commands, ("docker *", "podman *"))

    def test_untrusted_project_cannot_disable_user_sandbox_floor(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-settings-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            _write_settings(
                home,
                {
                    "sandbox": {
                        "enabled": True,
                        "failIfUnavailable": True,
                        "network": {"allowedDomains": []},
                    }
                },
            )
            _write_settings(
                project,
                {
                    "sandbox": {
                        "enabled": False,
                        "failIfUnavailable": False,
                        "network": True,
                    }
                },
            )

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                workspace = create_run_workspace(project, "sandbox-floor")
                untrusted = read_workspace_sandbox(workspace)
                trusted = read_workspace_sandbox(
                    replace(workspace, project_config_trusted=True)
                )

        self.assertIn("requires explicit project configuration trust", untrusted.error or "")
        self.assertIsNone(trusted.error)
        self.assertFalse(trusted.enabled)
        self.assertFalse(trusted.fail_if_unavailable)
        self.assertFalse(trusted.network_disabled)

    def test_symlinked_user_settings_fail_closed_for_all_runtime_policies(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-settings-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            outside = root / "settings.json"
            outside.write_text("{}", encoding="utf-8")
            settings = home / ".claude/settings.json"
            settings.parent.mkdir(parents=True)
            settings.symlink_to(outside)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                workspace = create_run_workspace(project, "linked-user-settings")
                permissions = read_project_permissions(workspace)
                hooks = read_project_hooks(workspace)
                sandbox = read_workspace_sandbox(workspace)

        self.assertIn("symbolic link", permissions.error or "")
        self.assertIn("symbolic link", hooks.error or "")
        self.assertIn("symbolic link", sandbox.error or "")


if __name__ == "__main__":
    unittest.main()
