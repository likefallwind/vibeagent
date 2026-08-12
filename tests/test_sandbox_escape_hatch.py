from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.agent_approval import build_approval_request
from vibeagent.command_sandbox import (
    prepare_command_launch,
    sandbox_auto_approval_reason,
)
from vibeagent.runtime_action_executor import execute_runtime_action
from vibeagent.tool_definitions import AGENT_TOOL_DEFINITIONS
from vibeagent.types import (
    RunCommandAction,
    RunCommandItem,
    RunCommandsAction,
    StartCommandAction,
)
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_permissions import (
    ProjectPermissions,
    match_project_permission,
    permission_rules_from_values,
)
from vibeagent.workspace_sandbox import SandboxConfig, read_workspace_sandbox


def _write_sandbox(root: Path, sandbox: dict[str, object]) -> None:
    path = root / ".vibeagent/sandbox.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sandbox), encoding="utf-8")


def _sandbox_available() -> bool:
    if shutil.which("bwrap") is None:
        return False
    with tempfile.TemporaryDirectory(prefix="vibeagent-bwrap-probe-") as base:
        root = Path(base)
        _write_sandbox(root, {"enabled": True, "failIfUnavailable": True})
        return read_workspace_sandbox(create_run_workspace(root)).available


def _tool_schema(name: str) -> dict[str, object]:
    return next(tool["input_schema"] for tool in AGENT_TOOL_DEFINITIONS if tool["name"] == name)


class SandboxEscapeContractTests(unittest.TestCase):
    def test_parses_escape_for_finite_batch_and_background_commands(self) -> None:
        finite = parse_tool_action(
            "Bash",
            {"command": "echo ok", "dangerouslyDisableSandbox": True},
        )
        batch = parse_tool_action(
            "run_commands",
            {
                "commands": [
                    {"command": "echo ok", "dangerouslyDisableSandbox": True}
                ]
            },
        )
        background = parse_tool_action(
            "start_command",
            {"command": "echo ok", "dangerouslyDisableSandbox": True},
        )

        self.assertTrue(finite.dangerously_disable_sandbox)
        self.assertTrue(batch.commands[0].dangerously_disable_sandbox)
        self.assertTrue(background.dangerously_disable_sandbox)
        for tool_name in ("run_command", "run_commands", "start_command"):
            self.assertIn("dangerouslyDisableSandbox", json.dumps(_tool_schema(tool_name)))
        with self.assertRaisesRegex(ValueError, "must be a boolean"):
            parse_tool_action(
                "run_command",
                {"command": "echo bad", "dangerouslyDisableSandbox": "yes"},
            )

    def test_escape_request_has_explicit_approval_risk(self) -> None:
        request = build_approval_request(
            RunCommandAction(
                type="run_command",
                command="make install",
                dangerously_disable_sandbox=True,
            )
        )

        assert request is not None
        self.assertIn("outside the command sandbox", request.risk)
        self.assertIn("host filesystem and network", request.risk)

    def test_special_bash_permission_rule_matches_escape_only(self) -> None:
        escaped = RunCommandAction(
            type="run_command",
            command="make install",
            dangerously_disable_sandbox=True,
        )
        sandboxed = replace(escaped, dangerously_disable_sandbox=False)
        ask = ProjectPermissions(
            rules=permission_rules_from_values(
                "ask",
                ("Bash(dangerouslyDisableSandbox:true)",),
                "test",
            )
        )
        allow = ProjectPermissions(
            rules=permission_rules_from_values(
                "allow",
                ("Bash(dangerouslyDisableSandbox:true)",),
                "test",
            )
        )
        mixed_batch = RunCommandsAction(
            type="run_commands",
            commands=[
                RunCommandItem(command="one", dangerously_disable_sandbox=True),
                RunCommandItem(command="two"),
            ],
        )

        self.assertEqual(
            match_project_permission(ask, "run_command", escaped).effect,
            "ask",
        )
        self.assertIsNone(match_project_permission(ask, "run_command", sandboxed))
        self.assertIsNone(match_project_permission(allow, "run_commands", mixed_batch))
        self.assertEqual(
            match_project_permission(ask, "run_commands", mixed_batch).effect,
            "ask",
        )

    def test_escape_never_receives_sandbox_auto_approval(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-escape-") as base:
            workspace = create_run_workspace(base)
            config = SandboxConfig(
                enabled=True,
                available=True,
                network_disabled=True,
                network_available=True,
                bwrap_path="/usr/bin/bwrap",
            )
            action = RunCommandAction(
                type="run_command",
                command="echo host",
                dangerously_disable_sandbox=True,
            )
            with patch(
                "vibeagent.command_sandbox.read_workspace_sandbox",
                return_value=config,
            ):
                reason = sandbox_auto_approval_reason(workspace, action)
            with patch(
                "vibeagent.command_sandbox.read_workspace_sandbox",
                return_value=replace(config, allow_unsandboxed_commands=False),
            ):
                strict_reason = sandbox_auto_approval_reason(workspace, action)

        self.assertIsNone(reason)
        self.assertIn("sandbox isolation", strict_reason or "")

    def test_background_execution_forwards_escape_request(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-escape-") as base:
            workspace = create_run_workspace(base)
            action = StartCommandAction(
                type="start_command",
                command="long-job",
                dangerously_disable_sandbox=True,
            )
            sentinel = object()
            with patch(
                "vibeagent.runtime_action_executor.start_background_command",
                return_value=sentinel,
            ) as start:
                observation = execute_runtime_action(workspace, action, 30_000)

        self.assertIs(observation, sentinel)
        self.assertTrue(start.call_args.kwargs["dangerously_disable_sandbox"])

    def test_strict_trusted_setting_cannot_be_reenabled_by_untrusted_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-escape-") as base:
            root = Path(base)
            _write_sandbox(
                root,
                {"enabled": True, "allowUnsandboxedCommands": True},
            )
            workspace = replace(
                create_run_workspace(root),
                setting_sources=(),
                settings_override_json=json.dumps(
                    {
                        "sandbox": {
                            "enabled": True,
                            "allowUnsandboxedCommands": False,
                        }
                    }
                ),
            )
            untrusted = read_workspace_sandbox(workspace)
            trusted = read_workspace_sandbox(
                replace(workspace, project_config_trusted=True)
            )

        self.assertIn("requires explicit project configuration trust", untrusted.error or "")
        self.assertIsNone(trusted.error)
        self.assertTrue(trusted.allow_unsandboxed_commands)

    def test_escape_keeps_unsandboxed_environment_and_warning(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-escape-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            config = SandboxConfig(
                enabled=True,
                available=True,
                bwrap_path="/usr/bin/bwrap",
                denied_environment_variables=("VIBEAGENT_ESCAPE_SECRET",),
            )
            with patch.dict(os.environ, {"VIBEAGENT_ESCAPE_SECRET": "visible"}):
                with patch(
                    "vibeagent.command_sandbox.read_workspace_sandbox",
                    return_value=config,
                ):
                    launch = prepare_command_launch(
                        workspace,
                        "echo host",
                        root,
                        dangerously_disable_sandbox=True,
                    )

        self.assertFalse(launch.sandboxed)
        self.assertEqual(
            (launch.environment or {}).get("VIBEAGENT_ESCAPE_SECRET"),
            "visible",
        )
        self.assertIn("normal permission approval still applies", launch.warning or "")


@unittest.skipUnless(_sandbox_available(), "bubblewrap sandbox is unavailable")
class SandboxEscapeExecutionTests(unittest.TestCase):
    def test_escape_can_write_outside_project_after_explicit_request(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-escape-") as base:
            parent = Path(base)
            root = parent / "project"
            outside = parent / "outside.txt"
            root.mkdir()
            _write_sandbox(
                root,
                {"enabled": True, "failIfUnavailable": True},
            )
            result = execute_action(
                create_run_workspace(root),
                RunCommandAction(
                    type="run_command",
                    command=f"printf host > {outside.as_posix()}",
                    dangerously_disable_sandbox=True,
                ),
            )
            outside_content = outside.read_text(encoding="utf-8")

        self.assertEqual(result.result.exit_code, 0)
        self.assertFalse(result.result.sandboxed)
        self.assertEqual(outside_content, "host")
        self.assertIn("dangerouslyDisableSandbox", result.result.stderr)

    def test_strict_mode_ignores_escape_and_keeps_command_sandboxed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-escape-") as base:
            parent = Path(base)
            root = parent / "project"
            outside = parent / "outside.txt"
            root.mkdir()
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "failIfUnavailable": True,
                    "allowUnsandboxedCommands": False,
                },
            )
            result = execute_action(
                create_run_workspace(root),
                RunCommandAction(
                    type="run_command",
                    command=f"printf blocked > {outside.as_posix()}",
                    dangerously_disable_sandbox=True,
                ),
            )
            outside_exists = outside.exists()

        self.assertTrue(result.result.sandboxed)
        self.assertFalse(outside_exists)


if __name__ == "__main__":
    unittest.main()
