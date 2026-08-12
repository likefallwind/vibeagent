from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from vibeagent.actions import execute_action
from vibeagent.command_sandbox import prepare_command_launch
from vibeagent.types import RunCommandAction
from vibeagent.workspace import create_run_workspace
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


class SandboxReadCredentialConfigTests(unittest.TestCase):
    def test_project_allow_read_requires_explicit_trust(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-read-") as base:
            root = Path(base)
            (root / "public").mkdir()
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "filesystem": {"allowRead": ["public"]},
                },
            )
            workspace = create_run_workspace(root)
            untrusted = read_workspace_sandbox(workspace)
            trusted = read_workspace_sandbox(
                replace(workspace, project_config_trusted=True)
            )

        self.assertIn("requires explicit project configuration trust", untrusted.error or "")
        self.assertIsNone(trusted.error)
        self.assertEqual(trusted.allow_read, ((root / "public").resolve(),))

    def test_credential_denies_merge_into_read_and_command_environment(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-credential-") as base:
            root = Path(base)
            secret = root / "secret.txt"
            secret.write_text("secret", encoding="utf-8")
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "credentials": {
                        "files": [{"path": "secret.txt", "mode": "deny"}],
                        "envVars": [{"name": "VIBEAGENT_TEST_SECRET", "mode": "deny"}],
                    },
                },
            )
            config = read_workspace_sandbox(create_run_workspace(root))

        self.assertIsNone(config.error)
        self.assertEqual(config.deny_read, (secret.resolve(),))
        self.assertEqual(
            config.denied_environment_variables,
            ("VIBEAGENT_TEST_SECRET",),
        )

    def test_environment_is_scrubbed_only_for_sandboxed_launches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-env-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            base_config = SandboxConfig(
                enabled=True,
                denied_environment_variables=("VIBEAGENT_TEST_SECRET",),
            )
            with patch.dict(os.environ, {"VIBEAGENT_TEST_SECRET": "host-secret"}):
                with patch(
                    "vibeagent.command_sandbox.read_workspace_sandbox",
                    return_value=replace(
                        base_config,
                        available=True,
                        bwrap_path="/usr/bin/bwrap",
                    ),
                ):
                    sandboxed = prepare_command_launch(workspace, "true", root)
                with patch(
                    "vibeagent.command_sandbox.read_workspace_sandbox",
                    return_value=base_config,
                ):
                    fallback = prepare_command_launch(workspace, "true", root)

        self.assertTrue(sandboxed.sandboxed)
        self.assertNotIn("VIBEAGENT_TEST_SECRET", sandboxed.environment or {})
        self.assertFalse(fallback.sandboxed)
        self.assertEqual(
            (fallback.environment or {}).get("VIBEAGENT_TEST_SECRET"),
            "host-secret",
        )


@unittest.skipUnless(_sandbox_available(), "bubblewrap sandbox is unavailable")
class SandboxReadCredentialExecutionTests(unittest.TestCase):
    def test_specific_allow_read_reopens_broader_denied_parent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-read-") as base:
            parent = Path(base)
            root = parent / "project"
            sibling = parent / "sibling.txt"
            root.mkdir()
            sibling.write_text("hidden", encoding="utf-8")
            (root / "visible.txt").write_text("visible", encoding="utf-8")
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "failIfUnavailable": True,
                    "filesystem": {
                        "denyRead": [parent.as_posix()],
                        "allowRead": [root.as_posix()],
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
                    command=(
                        "cat visible.txt && "
                        f"if cat {sibling.as_posix()}; then exit 9; else exit 0; fi"
                    ),
                ),
            )

        self.assertEqual(result.result.exit_code, 0)
        self.assertEqual(result.result.stdout, "visible")

    def test_specific_deny_read_overrides_broader_allow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-read-") as base:
            root = Path(base)
            secret = root / "secret.txt"
            secret.write_text("hidden", encoding="utf-8")
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "failIfUnavailable": True,
                    "filesystem": {
                        "allowRead": [root.as_posix()],
                        "denyRead": [secret.as_posix()],
                    },
                },
            )
            workspace = replace(
                create_run_workspace(root),
                project_config_trusted=True,
            )
            result = execute_action(
                workspace,
                RunCommandAction(type="run_command", command="cat secret.txt"),
            )

        self.assertNotEqual(result.result.exit_code, 0)
        self.assertEqual(result.result.stdout, "")

    def test_credential_file_and_environment_are_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-credential-") as base:
            root = Path(base)
            secret = root / "secret.txt"
            secret.write_text("hidden", encoding="utf-8")
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "failIfUnavailable": True,
                    "credentials": {
                        "files": [{"path": "secret.txt", "mode": "deny"}],
                        "envVars": [{"name": "VIBEAGENT_TEST_SECRET", "mode": "deny"}],
                    },
                },
            )
            workspace = create_run_workspace(root)
            with patch.dict(
                os.environ,
                {
                    "VIBEAGENT_TEST_SECRET": "host-secret",
                    "VIBEAGENT_TEST_VISIBLE": "visible",
                },
            ):
                result = execute_action(
                    workspace,
                    RunCommandAction(
                        type="run_command",
                        command=(
                            "test ! -s secret.txt && "
                            "test -z \"$VIBEAGENT_TEST_SECRET\" && "
                            "test \"$VIBEAGENT_TEST_VISIBLE\" = visible"
                        ),
                    ),
                )

        self.assertEqual(result.result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
