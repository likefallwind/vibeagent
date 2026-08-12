from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from vibeagent.actions import execute_action
from vibeagent.agent_run_setup import prepare_agent_run
from vibeagent.managed_settings import read_file_managed_settings
from vibeagent.permission_update_runtime import apply_permission_updates
from vibeagent.sandbox_permission_paths import sandbox_permission_paths
from vibeagent.types import RunCommandAction
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_core import create_local_workspace
from vibeagent.workspace_permissions import (
    ProjectPermissions,
    permission_rules_from_values,
)
from vibeagent.workspace_sandbox import read_workspace_sandbox


def _write_settings(root: Path, payload: dict[str, object]) -> None:
    path = root / ".claude/settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _absolute_permission_path(path: Path) -> str:
    return f"/{path.as_posix()}"


def _sandbox_available() -> bool:
    if shutil.which("bwrap") is None:
        return False
    with tempfile.TemporaryDirectory(prefix="vibeagent-bwrap-probe-") as base:
        root = Path(base)
        _write_settings(
            root,
            {"sandbox": {"enabled": True, "failIfUnavailable": True}},
        )
        return read_workspace_sandbox(create_run_workspace(root)).available


class SandboxPermissionPathTests(unittest.TestCase):
    def test_resolves_permission_prefixes_globs_and_recursive_directories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-paths-") as base:
            parent = Path(base)
            root = parent / "project"
            external = parent / "cache"
            protected = root / "protected"
            secrets = root / "secrets"
            root.mkdir()
            external.mkdir()
            protected.mkdir()
            secrets.mkdir()
            first_secret = secrets / "first.key"
            second_secret = secrets / "second.key"
            first_secret.write_text("one", encoding="utf-8")
            second_secret.write_text("two", encoding="utf-8")
            source = "trusted"
            permissions = ProjectPermissions(
                rules=(
                    *permission_rules_from_values(
                        "allow",
                        (f"Edit({_absolute_permission_path(external)})",),
                        source,
                    ),
                    *permission_rules_from_values(
                        "deny",
                        ("Edit(/protected/**)", "Read(/secrets/*.key)"),
                        "project",
                    ),
                ),
                trusted_allow_sources=(source,),
            )
            paths = sandbox_permission_paths(
                create_run_workspace(root),
                permissions,
            )

        self.assertEqual(paths.allow_write, (external.resolve(),))
        self.assertEqual(paths.deny_write, (protected.resolve(),))
        self.assertCountEqual(
            paths.deny_read,
            (first_secret.resolve(), second_secret.resolve()),
        )

    def test_untrusted_allow_is_ignored_while_denies_always_merge(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-paths-") as base:
            parent = Path(base)
            root = parent / "project"
            external = parent / "cache"
            secret = root / ".env.local"
            protected = root / "protected"
            root.mkdir()
            external.mkdir()
            protected.mkdir()
            secret.write_text("secret", encoding="utf-8")
            _write_settings(
                root,
                {
                    "sandbox": {"enabled": True},
                    "permissions": {
                        "allow": [
                            f"Edit({_absolute_permission_path(external)})"
                        ],
                        "deny": ["Read(/.env.*)", "Edit(/protected/**)"],
                    },
                },
            )
            workspace = create_run_workspace(root)
            untrusted = read_workspace_sandbox(workspace)
            trusted = read_workspace_sandbox(
                replace(workspace, project_config_trusted=True)
            )

        self.assertNotIn(external.resolve(), untrusted.allow_write)
        self.assertIn(secret.resolve(), untrusted.deny_read)
        self.assertIn(protected.resolve(), untrusted.deny_write)
        self.assertIn(external.resolve(), trusted.allow_write)
        self.assertEqual(trusted.permission_allow_write, (external.resolve(),))

    def test_symlinked_deny_resolves_to_and_protects_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-paths-") as base:
            parent = Path(base)
            root = parent / "project"
            root.mkdir()
            target = parent / "secret.txt"
            target.write_text("secret", encoding="utf-8")
            (root / "linked-secret").symlink_to(target)
            permissions = ProjectPermissions(
                rules=permission_rules_from_values(
                    "deny",
                    ("Read(/linked-secret)",),
                    "project",
                )
            )
            paths = sandbox_permission_paths(
                create_run_workspace(root),
                permissions,
            )

        self.assertEqual(paths.deny_read, (target.resolve(),))

    def test_symlinked_allow_does_not_widen_to_unmatched_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-paths-") as base:
            parent = Path(base)
            root = parent / "project"
            root.mkdir()
            target = parent / "external"
            target.mkdir()
            (root / "linked-cache").symlink_to(target, target_is_directory=True)
            source = "trusted"
            permissions = ProjectPermissions(
                rules=permission_rules_from_values(
                    "allow",
                    ("Edit(/linked-cache)",),
                    source,
                ),
                trusted_allow_sources=(source,),
            )
            paths = sandbox_permission_paths(
                create_run_workspace(root),
                permissions,
            )

        self.assertEqual(paths.allow_write, ())

    def test_session_permission_updates_refresh_runtime_mount_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-paths-") as base:
            parent = Path(base)
            root = parent / "project"
            external = parent / "cache"
            secret = root / "secret.txt"
            root.mkdir()
            external.mkdir()
            secret.write_text("secret", encoding="utf-8")
            _write_settings(
                root,
                {"sandbox": {"enabled": True}},
            )
            updated = apply_permission_updates(
                create_run_workspace(root),
                ProjectPermissions(),
                "ask",
                (
                    {
                        "type": "addRules",
                        "rules": [
                            {
                                "toolName": "Edit",
                                "ruleContent": _absolute_permission_path(external),
                            }
                        ],
                        "behavior": "allow",
                        "destination": "session",
                    },
                    {
                        "type": "addRules",
                        "rules": [
                            {"toolName": "Read", "ruleContent": "/secret.txt"}
                        ],
                        "behavior": "deny",
                        "destination": "session",
                    },
                ),
                bypass_available=False,
            )
            config = read_workspace_sandbox(updated.workspace)

        self.assertEqual(
            updated.workspace.sandbox_permission_allow_write,
            (external.resolve(),),
        )
        self.assertEqual(
            updated.workspace.sandbox_permission_deny_read,
            (secret.resolve(),),
        )
        self.assertIn(external.resolve(), config.allow_write)
        self.assertIn(secret.resolve(), config.deny_read)

    def test_agent_setup_merges_trusted_cli_edit_allow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-paths-") as base:
            parent = Path(base)
            root = parent / "project"
            external = parent / "cache"
            root.mkdir()
            external.mkdir()
            _write_settings(root, {"sandbox": {"enabled": True}})
            source = "<cli --allowed-tools>"
            overrides = ProjectPermissions(
                rules=permission_rules_from_values(
                    "allow",
                    (f"Edit({_absolute_permission_path(external)})",),
                    source,
                ),
                trusted_allow_sources=(source,),
            )
            setup = prepare_agent_run(
                "Inspect",
                base_dir=root,
                workspace=None,
                prior_context=None,
                approval_policy="ask",
                task_metadata=None,
                trust_project_permissions=False,
                permission_overrides=overrides,
                mcp_config_paths=(),
                strict_mcp_config=False,
                setting_sources=("project",),
                system_prompt=None,
                append_system_prompt=None,
            )

        self.assertEqual(
            setup.workspace.sandbox_permission_allow_write,
            (external.resolve(),),
        )
        self.assertIn(external.resolve(), setup.sandbox_config.allow_write)

    def test_managed_only_permissions_filter_project_sandbox_denies(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-managed-") as managed_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-project-") as project_base:
                managed = Path(managed_base)
                project = Path(project_base)
                managed_secret = project / "managed-secret.txt"
                project_secret = project / "project-secret.txt"
                managed_secret.write_text("managed", encoding="utf-8")
                project_secret.write_text("project", encoding="utf-8")
                (managed / "managed-settings.json").write_text(
                    json.dumps(
                        {
                            "allowManagedPermissionRulesOnly": True,
                            "sandbox": {"enabled": True},
                            "permissions": {
                                "deny": ["Read(/managed-secret.txt)"]
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                _write_settings(
                    project,
                    {
                        "permissions": {
                            "deny": ["Read(/project-secret.txt)"]
                        }
                    },
                )
                workspace = replace(
                    create_local_workspace(project, "managed-paths"),
                    project_config_trusted=True,
                )
                with patch(
                    "vibeagent.workspace_settings_sources.read_file_managed_settings",
                    lambda: read_file_managed_settings(managed),
                ):
                    config = read_workspace_sandbox(workspace)

        self.assertEqual(config.permission_deny_read, (managed_secret.resolve(),))
        self.assertNotIn(project_secret.resolve(), config.deny_read)

    def test_excessive_glob_expansion_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-paths-") as base:
            root = Path(base)
            for index in range(501):
                (root / f"secret-{index:03d}.key").write_text("x", encoding="utf-8")
            _write_settings(
                root,
                {
                    "sandbox": {"enabled": True},
                    "permissions": {"deny": ["Read(/secret-*.key)"]},
                },
            )
            config = read_workspace_sandbox(create_run_workspace(root))

        self.assertIn("expansion exceeds 500 entries", config.error or "")


@unittest.skipUnless(_sandbox_available(), "bubblewrap sandbox is unavailable")
class SandboxPermissionPathExecutionTests(unittest.TestCase):
    def test_read_and_edit_denies_apply_to_bash_subprocess(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-paths-") as base:
            root = Path(base)
            secret = root / ".env.local"
            protected = root / "protected"
            secret.write_text("host-secret", encoding="utf-8")
            protected.mkdir()
            _write_settings(
                root,
                {
                    "sandbox": {"enabled": True, "failIfUnavailable": True},
                    "permissions": {
                        "deny": ["Read(/.env.*)", "Edit(/protected/**)"]
                    },
                },
            )
            workspace = create_run_workspace(root)
            read_result = execute_action(
                workspace,
                RunCommandAction(type="run_command", command="cat .env.local"),
            )
            write_result = execute_action(
                workspace,
                RunCommandAction(
                    type="run_command",
                    command="printf changed > protected/output.txt",
                ),
            )
            protected_exists = (protected / "output.txt").exists()

        self.assertTrue(read_result.result.sandboxed)
        self.assertEqual(read_result.result.stdout, "")
        self.assertNotEqual(write_result.result.exit_code, 0)
        self.assertFalse(protected_exists)

    def test_trusted_edit_allow_grants_external_subprocess_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-paths-") as base:
            parent = Path(base)
            root = parent / "project"
            external = parent / "cache"
            root.mkdir()
            external.mkdir()
            _write_settings(
                root,
                {
                    "sandbox": {"enabled": True, "failIfUnavailable": True},
                    "permissions": {
                        "allow": [
                            f"Edit({_absolute_permission_path(external)})"
                        ]
                    },
                },
            )
            workspace = replace(
                create_run_workspace(root),
                project_config_trusted=True,
            )
            result = execute_action(
                workspace,
                RunCommandAction(
                    type="run_command",
                    command=f"printf cache > {external.as_posix()}/output.txt",
                ),
            )
            content = (external / "output.txt").read_text(encoding="utf-8")

        self.assertTrue(result.result.sandboxed)
        self.assertEqual(result.result.exit_code, 0)
        self.assertEqual(content, "cache")


if __name__ == "__main__":
    unittest.main()
