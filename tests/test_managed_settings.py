from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.auto_mode_config import resolve_auto_mode_config
from vibeagent.agent_run_setup import _validate_managed_permission_modes
from vibeagent.managed_settings import read_file_managed_settings
from vibeagent.permission_update_runtime import apply_permission_updates
from vibeagent.tool_catalog import get_permissions_report
from vibeagent.types import RunCommandAction
from vibeagent.workspace_core import create_local_workspace
from vibeagent.workspace_environment import read_workspace_environment
from vibeagent.workspace_hooks import read_project_hooks
from vibeagent.workspace_permissions import match_project_permission, read_project_permissions
from vibeagent.workspace_sandbox import read_workspace_sandbox
from vibeagent.workspace_settings_sources import claude_settings_files, read_settings_payload


def _managed_reader(directory: Path):
    return lambda: read_file_managed_settings(directory)


class ManagedSettingsMergeTests(unittest.TestCase):
    def test_base_and_sorted_drop_ins_deep_merge_with_array_deduplication(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as base:
            root = Path(base)
            (root / "managed-settings.d").mkdir()
            (root / "managed-settings.json").write_text(
                json.dumps(
                    {
                        "scalar": "base",
                        "permissions": {"deny": ["Bash(curl *)"]},
                        "items": [{"name": "same"}],
                    }
                ),
                encoding="utf-8",
            )
            (root / "managed-settings.d/20-later.json").write_text(
                json.dumps(
                    {
                        "scalar": "later",
                        "permissions": {"deny": ["Bash(rm *)"]},
                        "items": [{"name": "later"}],
                    }
                ),
                encoding="utf-8",
            )
            (root / "managed-settings.d/10-first.json").write_text(
                json.dumps(
                    {
                        "scalar": "first",
                        "permissions": {"deny": ["Bash(curl *)", "Bash(git push *)"]},
                        "items": [{"name": "same"}],
                    }
                ),
                encoding="utf-8",
            )
            (root / "managed-settings.d/.ignored.json").write_text("not json", encoding="utf-8")
            (root / "managed-settings.d/ignored.txt").write_text("not json", encoding="utf-8")
            payload, sources = read_file_managed_settings(root)

        assert payload is not None
        self.assertEqual(payload["scalar"], "later")
        self.assertEqual(
            payload["permissions"]["deny"],
            ["Bash(curl *)", "Bash(git push *)", "Bash(rm *)"],
        )
        self.assertEqual(payload["items"], [{"name": "same"}, {"name": "later"}])
        self.assertTrue(sources[1].endswith("10-first.json"))
        self.assertTrue(sources[2].endswith("20-later.json"))

    def test_rejects_symlinked_drop_in(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as base:
            root = Path(base)
            drop_ins = root / "managed-settings.d"
            drop_ins.mkdir()
            target = root / "target.json"
            target.write_text("{}", encoding="utf-8")
            (drop_ins / "10-policy.json").symlink_to(target)
            with self.assertRaisesRegex(ValueError, "regular non-symlink"):
                read_file_managed_settings(root)

    def test_rejects_symlinked_managed_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as base:
            parent = Path(base)
            real = parent / "real"
            real.mkdir()
            (real / "managed-settings.json").write_text("{}", encoding="utf-8")
            linked = parent / "linked"
            linked.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "directory must not be a symbolic link"):
                read_file_managed_settings(linked)

    def test_invalid_drop_in_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as base:
            root = Path(base)
            (root / "managed-settings.d").mkdir()
            (root / "managed-settings.json").write_text(
                json.dumps({"permissions": {"deny": ["Bash(curl *)"]}}),
                encoding="utf-8",
            )
            (root / "managed-settings.d/10-invalid.json").write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Could not parse managed settings"):
                read_file_managed_settings(root)


class ManagedSettingsIntegrationTests(unittest.TestCase):
    def test_managed_source_loads_last_even_in_bare_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                (managed / "managed-settings.json").write_text(
                    json.dumps({"viewMode": "focus"}), encoding="utf-8"
                )
                workspace = create_local_workspace(project_base, "managed-test", bare_mode=True)
                with patch(
                    "vibeagent.workspace_settings_sources.read_file_managed_settings",
                    _managed_reader(managed),
                ):
                    configs = claude_settings_files(workspace)
                    payload = read_settings_payload(configs[-1], max_bytes=10_000)

        self.assertEqual(len(configs), 1)
        self.assertTrue(configs[0].managed)
        self.assertTrue(configs[0].trusted)
        self.assertEqual(payload["viewMode"], "focus")

    def test_managed_environment_overrides_explicit_invocation_settings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                (managed / "managed-settings.json").write_text(
                    json.dumps({"env": {"POLICY_VALUE": "managed"}}), encoding="utf-8"
                )
                workspace = create_local_workspace(
                    project_base,
                    "managed-env",
                    setting_sources=(),
                    settings_override_json=json.dumps(
                        {"env": {"POLICY_VALUE": "cli", "CLI_ONLY": "yes"}}
                    ),
                )
                with patch(
                    "vibeagent.workspace_settings_sources.read_file_managed_settings",
                    _managed_reader(managed),
                ):
                    environment = read_workspace_environment(workspace)

        self.assertIsNone(environment.error)
        self.assertEqual(environment.variables["POLICY_VALUE"], "managed")
        self.assertEqual(environment.variables["CLI_ONLY"], "yes")

    def test_managed_permissions_and_sandbox_beat_project_specific_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                project = Path(project_base)
                (managed / "managed-settings.json").write_text(
                    json.dumps(
                        {
                            "permissions": {
                                "deny": ["Bash(git push *)"],
                                "defaultMode": "dontAsk",
                                "disableBypassPermissionsMode": "disable",
                                "disableAutoMode": "disable",
                            },
                            "allowManagedPermissionRulesOnly": True,
                            "sandbox": {"enabled": True, "failIfUnavailable": True},
                        }
                    ),
                    encoding="utf-8",
                )
                (project / ".vibeagent").mkdir()
                (project / ".vibeagent/permissions.json").write_text(
                    json.dumps({"defaultMode": "bypassPermissions"}), encoding="utf-8"
                )
                (project / ".vibeagent/sandbox.json").write_text(
                    json.dumps({"enabled": False, "failIfUnavailable": False}), encoding="utf-8"
                )
                workspace = create_local_workspace(project, "managed-security")
                with patch(
                    "vibeagent.workspace_settings_sources.read_file_managed_settings",
                    _managed_reader(managed),
                ):
                    permissions = read_project_permissions(workspace)
                    sandbox = read_workspace_sandbox(workspace)

        action = RunCommandAction(type="run_command", command="git push origin main")
        match = match_project_permission(permissions, "Bash", action)
        self.assertIsNotNone(match)
        self.assertEqual(match.effect, "deny")
        self.assertEqual(permissions.default_mode, "dontAsk")
        self.assertTrue(permissions.managed_rules_only)
        self.assertTrue(permissions.bypass_permissions_disabled)
        self.assertTrue(permissions.auto_mode_disabled)
        self.assertTrue(sandbox.enabled)
        self.assertTrue(sandbox.fail_if_unavailable)

    def test_managed_domain_lock_filters_project_allows_but_keeps_denies(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                project = Path(project_base)
                (managed / "managed-settings.json").write_text(
                    json.dumps(
                        {
                            "allowManagedDomainsOnly": True,
                            "sandbox": {
                                "enabled": True,
                                "network": {
                                    "allowedDomains": ["api.example.com"],
                                },
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                (project / ".vibeagent").mkdir()
                (project / ".vibeagent/sandbox.json").write_text(
                    json.dumps(
                        {
                            "network": {
                                "allowedDomains": ["upload.example.com"],
                                "deniedDomains": ["private.example.com"],
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                workspace = replace(
                    create_local_workspace(project, "managed-domain-lock"),
                    project_config_trusted=True,
                )
                with patch(
                    "vibeagent.workspace_settings_sources.read_file_managed_settings",
                    _managed_reader(managed),
                ):
                    sandbox = read_workspace_sandbox(workspace)

        self.assertIsNone(sandbox.error)
        self.assertTrue(sandbox.managed_domains_only)
        self.assertEqual(sandbox.allowed_domains, ("api.example.com",))
        self.assertEqual(sandbox.denied_domains, ("private.example.com",))

    def test_managed_domain_lock_applies_without_a_managed_sandbox_block(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                project = Path(project_base)
                (managed / "managed-settings.json").write_text(
                    json.dumps({"allowManagedDomainsOnly": True}),
                    encoding="utf-8",
                )
                (project / ".vibeagent").mkdir()
                (project / ".vibeagent/sandbox.json").write_text(
                    json.dumps(
                        {
                            "enabled": True,
                            "network": True,
                        }
                    ),
                    encoding="utf-8",
                )
                workspace = replace(
                    create_local_workspace(project, "managed-lock-only"),
                    project_config_trusted=True,
                )
                with patch(
                    "vibeagent.workspace_settings_sources.read_file_managed_settings",
                    _managed_reader(managed),
                ):
                    sandbox = read_workspace_sandbox(workspace)

        self.assertIsNone(sandbox.error)
        self.assertTrue(sandbox.managed_domains_only)
        self.assertEqual(sandbox.allowed_domains, ())
        self.assertEqual(sandbox.denied_domains, ())
        self.assertTrue(sandbox.network_disabled)
        self.assertTrue(any(source.startswith("managed settings:") for source in sandbox.sources))

    def test_managed_only_permissions_filter_cli_and_project_rules(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                project = Path(project_base)
                (managed / "managed-settings.json").write_text(
                    json.dumps(
                        {
                            "allowManagedPermissionRulesOnly": True,
                            "permissions": {"deny": ["Bash(git push *)"]},
                        }
                    ),
                    encoding="utf-8",
                )
                (project / ".claude").mkdir()
                (project / ".claude/settings.json").write_text(
                    json.dumps({"permissions": {"allow": ["Bash(git push *)"]}}),
                    encoding="utf-8",
                )
                workspace = create_local_workspace(
                    project,
                    "managed-rules-only",
                    settings_override_json=json.dumps(
                        {"permissions": {"ask": ["Bash(git status)"]}}
                    ),
                )
                with patch(
                    "vibeagent.workspace_settings_sources.read_file_managed_settings",
                    _managed_reader(managed),
                ):
                    permissions = read_project_permissions(workspace)

        self.assertEqual(len(permissions.rules), 1)
        self.assertEqual(permissions.rules[0].effect, "deny")
        self.assertTrue(permissions.rules[0].source.startswith("managed settings:"))

    def test_managed_mode_disables_bypass_and_auto_before_model_execution(self) -> None:
        from vibeagent.workspace_permissions import ProjectPermissions

        permissions = ProjectPermissions(
            bypass_permissions_disabled=True,
            auto_mode_disabled=True,
        )
        for policy, profile in (("allow", None), ("ask", "bypassPermissions"), ("auto", None)):
            with self.subTest(policy=policy, profile=profile):
                with self.assertRaisesRegex(ValueError, "disabled by managed"):
                    _validate_managed_permission_modes(policy, permissions, profile)

    def test_permission_updates_cannot_add_rules_or_disabled_modes(self) -> None:
        from vibeagent.workspace_permissions import ProjectPermissions

        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-updates-") as base:
            workspace = create_local_workspace(base, "managed-updates")
            permissions = ProjectPermissions(
                managed_rules_only=True,
                bypass_permissions_disabled=True,
                auto_mode_disabled=True,
            )
            result = apply_permission_updates(
                workspace,
                permissions,
                "ask",
                (
                    {
                        "type": "addRules",
                        "rules": [{"toolName": "Bash", "ruleContent": "git push *"}],
                        "behavior": "allow",
                        "destination": "session",
                    },
                    {
                        "type": "setMode",
                        "mode": "acceptEdits",
                        "destination": "session",
                    },
                    {
                        "type": "setMode",
                        "mode": "auto",
                        "destination": "session",
                    },
                    {
                        "type": "setMode",
                        "mode": "bypassPermissions",
                        "destination": "session",
                    },
                ),
                bypass_available=True,
            )

        self.assertEqual(result.applied, ())
        self.assertEqual(result.approval_policy, "ask")
        self.assertEqual(result.permissions.rules, ())
        self.assertEqual(len(result.warnings), 4)

    def test_permissions_report_exposes_managed_locks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                (managed / "managed-settings.json").write_text(
                    json.dumps(
                        {
                            "allowManagedPermissionRulesOnly": True,
                            "permissions": {
                                "disableBypassPermissionsMode": "disable",
                                "disableAutoMode": "disable",
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                with patch(
                    "vibeagent.workspace_settings_sources.read_file_managed_settings",
                    _managed_reader(managed),
                ):
                    report = get_permissions_report(root=project_base)

        policy = report["projectPermissions"]
        self.assertTrue(policy["managedRulesOnly"])
        self.assertTrue(policy["bypassPermissionsDisabled"])
        self.assertTrue(policy["autoModeDisabled"])
        self.assertIn("managed settings:", policy["sources"][0])

    def test_managed_only_hooks_survive_safe_mode_and_exclude_project_hooks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                project = Path(project_base)
                managed_hook = {
                    "matcher": "Write",
                    "hooks": [{"type": "command", "command": "managed-audit"}],
                }
                project_hook = {
                    "matcher": "Write",
                    "hooks": [{"type": "command", "command": "project-audit"}],
                }
                (managed / "managed-settings.json").write_text(
                    json.dumps(
                        {
                            "allowManagedHooksOnly": True,
                            "hooks": {"PreToolUse": [managed_hook]},
                        }
                    ),
                    encoding="utf-8",
                )
                (project / ".claude").mkdir()
                (project / ".claude/settings.json").write_text(
                    json.dumps({"hooks": {"PreToolUse": [project_hook]}}),
                    encoding="utf-8",
                )
                workspace = create_local_workspace(project, "managed-hooks", safe_mode=True)
                with patch(
                    "vibeagent.workspace_settings_sources.read_file_managed_settings",
                    _managed_reader(managed),
                ):
                    hooks = read_project_hooks(workspace)

        self.assertIsNone(hooks.error)
        self.assertTrue(hooks.managed_only)
        self.assertEqual([hook.command for hook in hooks.hooks], ["managed-audit"])

    def test_auto_mode_adds_managed_rules_without_project_injection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                project = Path(project_base)
                (managed / "managed-settings.json").write_text(
                    json.dumps(
                        {
                            "autoMode": {
                                "hard_deny": ["managed: never publish private source"],
                                "classifyAllShell": True,
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                (project / ".claude").mkdir()
                (project / ".claude/settings.json").write_text(
                    json.dumps({"autoMode": {"hard_deny": ["project: injected"]}}),
                    encoding="utf-8",
                )
                workspace = create_local_workspace(project, "managed-auto")
                with patch(
                    "vibeagent.workspace_settings_sources.read_file_managed_settings",
                    _managed_reader(managed),
                ):
                    config = resolve_auto_mode_config(workspace)

        self.assertEqual(config.hard_deny, ("managed: never publish private source",))
        self.assertTrue(config.classify_all_shell)
        self.assertNotIn("project: injected", config.hard_deny)
        self.assertTrue(config.sources[-1].startswith("managed settings:"))


if __name__ == "__main__":
    unittest.main()
