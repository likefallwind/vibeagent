from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent import run_agent
from vibeagent.agent_hook_results import HookRunResult
from vibeagent.agent_permission_request_hooks import (
    PermissionRequestHookOutcome,
    PermissionRequestHookOutputError,
    parse_permission_request_hook_output,
)
from vibeagent.agent_permission_request_authorization import resolve_permission_request
from vibeagent.permission_update_runtime import apply_permission_updates
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_permissions import (
    ProjectPermissions,
    match_project_permission,
)
from vibeagent.types import ApprovalDecision, ApprovalRequest, AssistantResponse, RunCommandAction


class PermissionClient:
    def __init__(self, tool_name: str, tool_input: dict[str, object]) -> None:
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.calls = 0

    def complete(self, messages, tools=None, **kwargs):
        self.calls += 1
        content = (
            [{"type": "tool_call", "id": "tool-1", "name": self.tool_name, "input": self.tool_input}]
            if self.calls == 1
            else [{"type": "text", "text": "done"}]
        )
        return AssistantResponse(content=content, raw={"content": content})


def _result(decision: dict[str, object]) -> HookRunResult:
    return HookRunResult(
        event="PermissionRequest",
        command="hook",
        source="test",
        status="passed",
        ok=True,
        exit_code=0,
        timed_out=False,
        stdout=json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PermissionRequest",
                    "decision": decision,
                }
            }
        ),
        stderr="",
        message="passed",
    )


class PermissionUpdateOutputTests(unittest.TestCase):
    def test_parses_updated_input_and_every_permission_update_type(self) -> None:
        entries = [
            {
                "type": entry_type,
                "rules": [{"toolName": "Bash", "ruleContent": "npm test"}],
                "behavior": "allow",
                "destination": "session",
            }
            for entry_type in ("addRules", "replaceRules", "removeRules")
        ]
        entries.extend(
            [
                {
                    "type": "setMode",
                    "mode": "acceptEdits",
                    "destination": "localSettings",
                },
                {
                    "type": "addDirectories",
                    "directories": ["../shared"],
                    "destination": "projectSettings",
                },
                {
                    "type": "removeDirectories",
                    "directories": ["../old"],
                    "destination": "userSettings",
                },
            ]
        )

        parsed = parse_permission_request_hook_output(
            _result(
                {
                    "behavior": "allow",
                    "updatedInput": {"command": "npm test"},
                    "updatedPermissions": entries,
                }
            )
        )

        self.assertEqual(parsed.updated_input, {"command": "npm test"})
        self.assertEqual(parsed.updated_permissions, tuple(entries))
        self.assertFalse(parsed.interrupt)

    def test_parses_deny_interrupt_and_rejects_behavior_specific_fields(self) -> None:
        denied = parse_permission_request_hook_output(
            _result(
                {
                    "behavior": "deny",
                    "message": "stop now",
                    "interrupt": True,
                }
            )
        )
        self.assertTrue(denied.interrupt)

        invalid = (
            {"behavior": "allow", "interrupt": False},
            {"behavior": "deny", "message": "no", "updatedInput": {}},
            {"behavior": "allow", "updatedInput": []},
            {"behavior": "allow", "updatedPermissions": {}},
            {
                "behavior": "allow",
                "updatedPermissions": [
                    {"type": "setMode", "mode": "root", "destination": "session"}
                ],
            },
            {
                "behavior": "allow",
                "updatedPermissions": [
                    {
                        "type": "addRules",
                        "rules": [{"toolName": "Bash"}],
                        "behavior": "approve",
                        "destination": "session",
                    }
                ],
            },
        )
        for decision in invalid:
            with self.subTest(decision=decision), self.assertRaises(
                PermissionRequestHookOutputError
            ):
                parse_permission_request_hook_output(_result(decision))


class PermissionUpdateRuntimeTests(unittest.TestCase):
    def test_session_rules_apply_replace_and_remove_without_losing_other_sources(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-update-") as base:
            workspace = create_run_workspace(base)
            action = RunCommandAction(type="run_command", command="npm test")
            added = apply_permission_updates(
                workspace,
                ProjectPermissions(),
                "ask",
                (
                    {
                        "type": "addRules",
                        "rules": [{"toolName": "Bash", "ruleContent": "npm test"}],
                        "behavior": "allow",
                        "destination": "session",
                    },
                ),
                bypass_available=False,
            )
            replaced = apply_permission_updates(
                added.workspace,
                added.permissions,
                added.approval_policy,
                (
                    {
                        "type": "replaceRules",
                        "rules": [{"toolName": "Bash", "ruleContent": "npm run lint"}],
                        "behavior": "allow",
                        "destination": "session",
                    },
                ),
                bypass_available=False,
            )
            removed = apply_permission_updates(
                replaced.workspace,
                replaced.permissions,
                replaced.approval_policy,
                (
                    {
                        "type": "removeRules",
                        "rules": [{"toolName": "Bash", "ruleContent": "npm run lint"}],
                        "behavior": "allow",
                        "destination": "session",
                    },
                ),
                bypass_available=False,
            )

        self.assertEqual(match_project_permission(added.permissions, "Bash", action).effect, "allow")
        self.assertIsNone(match_project_permission(replaced.permissions, "Bash", action))
        self.assertEqual([rule.raw for rule in replaced.permissions.rules], ["Bash(npm run lint)"])
        self.assertEqual(removed.permissions.rules, ())

    def test_modes_and_directories_update_current_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-update-") as base:
            root = Path(base)
            project = root / "project"
            shared = root / "shared"
            project.mkdir()
            shared.mkdir()
            workspace = create_run_workspace(project)
            updated = apply_permission_updates(
                workspace,
                ProjectPermissions(),
                "ask",
                (
                    {
                        "type": "setMode",
                        "mode": "acceptEdits",
                        "destination": "session",
                    },
                    {
                        "type": "addDirectories",
                        "directories": [str(shared)],
                        "destination": "session",
                    },
                ),
                bypass_available=False,
            )
            removed = apply_permission_updates(
                updated.workspace,
                updated.permissions,
                updated.approval_policy,
                (
                    {
                        "type": "removeDirectories",
                        "directories": [str(shared)],
                        "destination": "session",
                    },
                ),
                bypass_available=False,
            )

        self.assertEqual(updated.approval_policy, "ask")
        self.assertEqual(updated.workspace.additional_roots, (shared.resolve(),))
        self.assertIn("Write", [rule.raw for rule in updated.permissions.rules])
        self.assertEqual(removed.workspace.additional_roots, ())

    def test_persistent_destinations_preserve_settings_and_use_expected_modes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-update-") as base:
            root = Path(base)
            project = root / "project"
            home = root / "home"
            project.mkdir()
            home.mkdir()
            local_path = project / ".claude" / "settings.local.json"
            local_path.parent.mkdir()
            local_path.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")
            workspace = create_run_workspace(project)
            with patch("vibeagent.permission_update_runtime.user_home", return_value=home):
                updated = apply_permission_updates(
                    workspace,
                    ProjectPermissions(),
                    "ask",
                    (
                        {
                            "type": "addRules",
                            "rules": [{"toolName": "Bash", "ruleContent": "npm test"}],
                            "behavior": "allow",
                            "destination": "localSettings",
                        },
                        {
                            "type": "setMode",
                            "mode": "dontAsk",
                            "destination": "projectSettings",
                        },
                        {
                            "type": "addRules",
                            "rules": [{"toolName": "Read"}],
                            "behavior": "deny",
                            "destination": "userSettings",
                        },
                    ),
                    bypass_available=False,
                )
            local = json.loads(local_path.read_text(encoding="utf-8"))
            project_settings = json.loads(
                project.joinpath(".claude/settings.json").read_text(encoding="utf-8")
            )
            user_settings = json.loads(
                home.joinpath(".claude/settings.json").read_text(encoding="utf-8")
            )

        self.assertEqual(updated.approval_policy, "dontAsk")
        self.assertEqual(local["theme"], "dark")
        self.assertEqual(local["permissions"]["allow"], ["Bash(npm test)"])
        self.assertEqual(project_settings["permissions"]["defaultMode"], "dontAsk")
        self.assertEqual(user_settings["permissions"]["deny"], ["Read"])

    def test_unavailable_bypass_is_ignored_without_persisting_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-update-") as base:
            workspace = create_run_workspace(base)
            updated = apply_permission_updates(
                workspace,
                ProjectPermissions(),
                "ask",
                (
                    {
                        "type": "setMode",
                        "mode": "bypassPermissions",
                        "destination": "session",
                    },
                ),
                bypass_available=False,
            )

        self.assertEqual(updated.approval_policy, "ask")
        self.assertEqual(updated.applied, ())
        self.assertIn("did not start", updated.warnings[0])

    def test_startup_unlock_allows_permission_hook_to_enter_bypass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-update-") as base:
            workspace = create_run_workspace(base, bypass_permissions_available=True)
            action = RunCommandAction(type="run_command", command="git status")
            resolution = resolve_permission_request(
                workspace,
                ProjectPermissions(),
                "ask",
                "run_command",
                action,
                ApprovalRequest("run_command", "git status", "command"),
                None,
                1,
                lambda: PermissionRequestHookOutcome(
                    behavior="allow",
                    updated_permissions=(
                        {
                            "type": "setMode",
                            "mode": "bypassPermissions",
                            "destination": "session",
                        },
                    ),
                ),
                None,
                None,
            )

        self.assertTrue(resolution.terminal_allowed)
        self.assertEqual(resolution.approval_policy, "allow")
        self.assertEqual(resolution.application.applied[0]["mode"], "bypassPermissions")

    def test_persisted_mode_and_directory_apply_to_next_agent_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-update-") as base:
            root = Path(base)
            project = root / "project"
            shared = root / "shared"
            project.mkdir()
            shared.mkdir()
            shared.joinpath("context.txt").write_text("shared context", encoding="utf-8")
            workspace = create_run_workspace(project)
            apply_permission_updates(
                workspace,
                ProjectPermissions(),
                "ask",
                (
                    {
                        "type": "setMode",
                        "mode": "dontAsk",
                        "destination": "localSettings",
                    },
                    {
                        "type": "addDirectories",
                        "directories": [str(shared)],
                        "destination": "localSettings",
                    },
                ),
                bypass_available=False,
            )
            approval = Mock(
                return_value=ApprovalDecision(True, "approved")
            )
            write_result = run_agent(
                "Write a file",
                base_dir=project,
                client=PermissionClient(
                    "write_file", {"path": "blocked.py", "content": "blocked = True\n"}
                ),
                max_iterations=2,
                approval_handler=approval,
            )
            read_result = run_agent(
                "Read shared context",
                base_dir=project,
                client=PermissionClient("read_file", {"path": str(shared / "context.txt")}),
                max_iterations=2,
                approval_handler=approval,
            )

            self.assertFalse(project.joinpath("blocked.py").exists())

        self.assertEqual(write_result.approval_policy, "dontAsk")
        self.assertEqual(write_result.observations[0].kind, "approval_denied")
        self.assertEqual(read_result.observations[0].kind, "read_file")
        approval.assert_not_called()

    def test_invalid_persisted_directory_fails_closed_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-update-") as base:
            root = Path(base)
            settings = root / ".claude" / "settings.local.json"
            settings.parent.mkdir()
            settings.write_text(
                json.dumps(
                    {
                        "permissions": {
                            "additionalDirectories": ["../missing-directory"]
                        }
                    }
                ),
                encoding="utf-8",
            )
            result = run_agent(
                "Write a file",
                base_dir=root,
                client=PermissionClient(
                    "write_file", {"path": "blocked.py", "content": "blocked = True\n"}
                ),
                max_iterations=2,
                approval_handler=Mock(return_value=ApprovalDecision(True, "approved")),
            )

            self.assertFalse(root.joinpath("blocked.py").exists())

        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertIn("Permission configuration is invalid", result.observations[0].message)

    def test_symlink_destination_is_rejected_before_any_settings_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-permission-update-") as base:
            root = Path(base)
            project = root / "project"
            project.mkdir()
            external = root / "external.json"
            external.write_text("{}", encoding="utf-8")
            settings = project / ".claude" / "settings.json"
            settings.parent.mkdir()
            settings.symlink_to(external)
            workspace = create_run_workspace(project)

            with self.assertRaisesRegex(ValueError, "regular file"):
                apply_permission_updates(
                    workspace,
                    ProjectPermissions(),
                    "ask",
                    (
                        {
                            "type": "addRules",
                            "rules": [{"toolName": "Bash"}],
                            "behavior": "allow",
                            "destination": "projectSettings",
                        },
                    ),
                    bypass_available=False,
                )
            self.assertEqual(external.read_text(encoding="utf-8"), "{}")


if __name__ == "__main__":
    unittest.main()
