from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.actions import execute_action
from vibeagent.agent_permissions import authorize_tool_action
from vibeagent.command_sandbox import CommandLaunch, sandbox_auto_approval_reason
from vibeagent.runtime_types import ApprovalDecision, ApprovalRequest
from vibeagent.session_timeline_reports import format_session_event_timeline_item
from vibeagent.session_types import SessionEvent
from vibeagent.types import RunCommandAction, RunCommandItem, RunCommandsAction, StartCommandAction
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_permissions import ProjectPermissionRule, ProjectPermissions
from vibeagent.workspace_sandbox import SandboxConfig


def _active_config(*, auto_allow: bool = True) -> SandboxConfig:
    return SandboxConfig(
        enabled=True,
        fail_if_unavailable=True,
        auto_allow_bash_if_sandboxed=auto_allow,
        network_disabled=True,
        bwrap_path="/usr/bin/bwrap",
        available=True,
        network_available=True,
    )


def _launch(config: SandboxConfig, *, sandboxed: bool = True, warning: str | None = None) -> CommandLaunch:
    return CommandLaunch(("/bin/true",), sandboxed, config, warning=warning)


class SandboxAutoApprovalQualificationTests(unittest.TestCase):
    def test_single_start_and_batch_commands_qualify_only_when_all_launches_are_complete(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-auto-") as base:
            workspace = create_run_workspace(base)
            config = _active_config()
            actions = [
                RunCommandAction(type="run_command", command="npm test"),
                StartCommandAction(type="start_command", command="npm run dev"),
                RunCommandsAction(
                    type="run_commands",
                    commands=[RunCommandItem(command="npm test"), RunCommandItem(command="npm run build")],
                ),
            ]
            with (
                patch("vibeagent.command_sandbox.read_workspace_sandbox", return_value=config),
                patch("vibeagent.command_sandbox.prepare_command_launch", return_value=_launch(config)) as prepare,
            ):
                reasons = [sandbox_auto_approval_reason(workspace, action) for action in actions]

            with (
                patch("vibeagent.command_sandbox.read_workspace_sandbox", return_value=config),
                patch(
                    "vibeagent.command_sandbox.prepare_command_launch",
                    side_effect=[_launch(config), _launch(config, warning="network fallback")],
                ),
            ):
                incomplete_batch = sandbox_auto_approval_reason(workspace, actions[-1])

        self.assertTrue(all(reason and "Approved automatically" in reason for reason in reasons))
        self.assertEqual(prepare.call_count, 4)
        self.assertIsNone(incomplete_batch)

    def test_disabled_auto_allow_or_incomplete_network_isolation_does_not_qualify(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-auto-") as base:
            workspace = create_run_workspace(base)
            action = RunCommandAction(type="run_command", command="npm test")
            disabled = _active_config(auto_allow=False)
            incomplete = SandboxConfig(
                enabled=True,
                auto_allow_bash_if_sandboxed=True,
                network_disabled=False,
                bwrap_path="/usr/bin/bwrap",
                available=True,
            )
            with patch("vibeagent.command_sandbox.read_workspace_sandbox", return_value=disabled):
                disabled_reason = sandbox_auto_approval_reason(workspace, action)
            with patch("vibeagent.command_sandbox.read_workspace_sandbox", return_value=incomplete):
                incomplete_reason = sandbox_auto_approval_reason(workspace, action)

        self.assertIsNone(disabled_reason)
        self.assertIsNone(incomplete_reason)

    def test_hard_blocked_command_never_qualifies(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-auto-") as base:
            workspace = create_run_workspace(base)
            config = _active_config()
            with (
                patch("vibeagent.command_sandbox.read_workspace_sandbox", return_value=config),
                patch("vibeagent.command_sandbox.prepare_command_launch", return_value=_launch(config)) as prepare,
            ):
                reason = sandbox_auto_approval_reason(
                    workspace,
                    RunCommandAction(type="run_command", command="sudo reboot"),
                )

        self.assertIsNone(reason)
        prepare.assert_not_called()


class SandboxAutoApprovalDecisionTests(unittest.TestCase):
    def test_complete_sandbox_auto_approves_without_handler_and_records_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-auto-") as base:
            workspace = create_run_workspace(base)
            action = RunCommandAction(type="run_command", command="npm test")
            request = ApprovalRequest(action_type="run_command", target="npm test", risk="run command")
            with patch("vibeagent.agent_permissions.sandbox_auto_approval_reason", return_value="sandboxed"):
                authorization = authorize_tool_action(
                    workspace,
                    ProjectPermissions(),
                    "run_command",
                    action,
                    1,
                    None,
                    "ask",
                    None,
                    default_request=request,
                )
            events = [json.loads(line) for line in workspace.session_dir.joinpath("events.jsonl").read_text().splitlines()]

        self.assertTrue(authorization.allowed)
        self.assertEqual(authorization.decision.message, "sandboxed")
        self.assertEqual([event["type"] for event in events], ["sandbox_auto_approved"])

    def test_explicit_ask_rule_still_prompts(self) -> None:
        handler = Mock(return_value=ApprovalDecision(approved=True, message="user approved"))
        permissions = ProjectPermissions(
            rules=(
                ProjectPermissionRule(
                    effect="ask",
                    tool="Bash",
                    specifier=None,
                    raw="Bash",
                    source=".vibeagent/permissions.json",
                ),
            )
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-auto-") as base:
            workspace = create_run_workspace(base)
            action = RunCommandAction(type="run_command", command="npm test")
            request = ApprovalRequest(action_type="run_command", target="npm test", risk="run command")
            with patch("vibeagent.agent_permissions.sandbox_auto_approval_reason", return_value="sandboxed"):
                authorization = authorize_tool_action(
                    workspace,
                    permissions,
                    "run_command",
                    action,
                    1,
                    handler,
                    "ask",
                    None,
                    default_request=request,
                )

        self.assertTrue(authorization.allowed)
        handler.assert_called_once_with(request)

    def test_session_deny_and_plan_override_sandbox_auto_approval(self) -> None:
        for policy in ("deny", "plan"):
            with self.subTest(policy=policy), tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-auto-") as base:
                workspace = create_run_workspace(base)
                action = RunCommandAction(type="run_command", command="npm test")
                request = ApprovalRequest(action_type="run_command", target="npm test", risk="run command")
                with patch("vibeagent.agent_permissions.sandbox_auto_approval_reason", return_value="sandboxed"):
                    authorization = authorize_tool_action(
                        workspace,
                        ProjectPermissions(),
                        "run_command",
                        action,
                        1,
                        None,
                        policy,
                        None,
                        default_request=request,
                    )
            self.assertFalse(authorization.allowed)
            self.assertIn("Denied", authorization.denial.message)

    def test_auto_approval_cannot_bypass_command_hard_blocks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-auto-") as base:
            workspace = create_run_workspace(base)
            action = RunCommandAction(type="run_command", command="sudo reboot")
            request = ApprovalRequest(action_type="run_command", target="sudo reboot", risk="run command")
            with patch("vibeagent.agent_permissions.sandbox_auto_approval_reason", return_value="sandboxed"):
                authorization = authorize_tool_action(
                    workspace,
                    ProjectPermissions(),
                    "run_command",
                    action,
                    1,
                    None,
                    "ask",
                    None,
                    default_request=request,
                )
            observation = execute_action(workspace, action)

        self.assertTrue(authorization.allowed)
        self.assertIsNone(observation.result.exit_code)
        self.assertIn("Command blocked", observation.result.stderr)

    def test_timeline_formats_sandbox_auto_approval(self) -> None:
        event = SessionEvent(
            line_number=2,
            type="sandbox_auto_approved",
            payload={"tool": "run_command", "request": {"target": "npm test"}},
        )

        summary = format_session_event_timeline_item(event)

        self.assertIn("run_command", summary)
        self.assertIn("target=npm test", summary)


if __name__ == "__main__":
    unittest.main()
