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
from vibeagent.sandbox_commands import get_sandbox_report
from vibeagent.command_output_artifacts import resolve_command_output_artifact
from vibeagent.command_output_observers import observe_command_output
from vibeagent.types import (
    RunCommandAction,
    StartCommandAction,
    StopProcessAction,
    WaitProcessAction,
)
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

    def test_credential_masks_are_resolved_and_deny_takes_precedence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-credential-") as base:
            root = Path(base)
            secret = root / "secret.txt"
            secret.write_text("secret", encoding="utf-8")
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "credentials": {
                        "files": [
                            {"path": "secret.txt", "mode": "mask"},
                            {"path": "secret.txt", "mode": "deny"},
                        ],
                        "envVars": [
                            {"name": "MASK_ONLY", "mode": "mask"},
                            {"name": "DENY_WINS", "mode": "mask"},
                            {"name": "DENY_WINS", "mode": "deny"},
                        ],
                    },
                },
            )
            config = read_workspace_sandbox(create_run_workspace(root))

        self.assertIsNone(config.error)
        self.assertEqual(config.deny_read, (secret.resolve(),))
        self.assertEqual(config.masked_credential_files, ())
        self.assertEqual(config.denied_environment_variables, ("DENY_WINS",))
        self.assertEqual(config.masked_environment_variables, ("MASK_ONLY",))

    def test_sandbox_report_exposes_mask_sources_without_values(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-credential-") as base:
            root = Path(base)
            secret = root / "secret.txt"
            secret.write_text("report-secret-value", encoding="utf-8")
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "credentials": {
                        "files": [{"path": "secret.txt", "mode": "mask"}],
                        "envVars": [{"name": "MASKED_NAME", "mode": "mask"}],
                    },
                },
            )
            with patch.dict(os.environ, {"MASKED_NAME": "environment-report-secret"}):
                report = get_sandbox_report(root)
            serialized = json.dumps(report)

        credentials = report["credentials"]
        self.assertIsInstance(credentials, dict)
        assert isinstance(credentials, dict)
        self.assertEqual(credentials["maskedEnvVars"], ["MASKED_NAME"])
        self.assertEqual(credentials["maskedFiles"], [secret.resolve().as_posix()])
        self.assertNotIn("report-secret-value", serialized)
        self.assertNotIn("environment-report-secret", serialized)

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

    def test_mask_wrapper_remains_active_for_fallback_and_escape_launches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-mask-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            base_config = SandboxConfig(
                enabled=True,
                masked_environment_variables=("VIBEAGENT_TEST_SECRET",),
            )
            with patch(
                "vibeagent.command_sandbox.read_workspace_sandbox",
                return_value=base_config,
            ):
                fallback = prepare_command_launch(workspace, "true", root)
            with patch(
                "vibeagent.command_sandbox.read_workspace_sandbox",
                return_value=replace(
                    base_config,
                    available=True,
                    bwrap_path="/usr/bin/bwrap",
                    allow_unsandboxed_commands=True,
                ),
            ):
                escape = prepare_command_launch(
                    workspace,
                    "true",
                    root,
                    dangerously_disable_sandbox=True,
                )

        for launch in (fallback, escape):
            self.assertIn("vibeagent.sandbox_credential_launcher", launch.argv)
            serialized = " ".join(launch.argv)
            self.assertIn("VIBEAGENT_TEST_SECRET", serialized)
            self.assertNotIn("host-secret", serialized)
        self.assertFalse(fallback.sandboxed)
        self.assertIn("unavailable", fallback.warning or "")
        self.assertFalse(escape.sandboxed)
        self.assertIn("dangerouslyDisableSandbox", escape.warning or "")


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

    def test_masked_credentials_never_reach_results_or_truncated_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-mask-") as base:
            root = Path(base)
            secret_file = root / "secret.txt"
            secret_file.write_text("file-secret-value\n", encoding="utf-8")
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "failIfUnavailable": True,
                    "credentials": {
                        "files": [{"path": "secret.txt", "mode": "mask"}],
                        "envVars": [
                            {"name": "VIBEAGENT_TEST_SECRET", "mode": "mask"}
                        ],
                    },
                },
            )
            workspace = create_run_workspace(root)
            command = (
                "python3 -c \"import os,pathlib; "
                "value=os.environ['VIBEAGENT_TEST_SECRET']+'|'+"
                "pathlib.Path('secret.txt').read_text().strip(); "
                "print((value+'\\n')*100)\""
            )
            streamed: list[str] = []
            with patch.dict(
                os.environ,
                {"VIBEAGENT_TEST_SECRET": "environment-secret-value"},
            ), observe_command_output(
                lambda stdout, stderr: streamed.append(stdout + stderr)
            ):
                result = execute_action(
                    workspace,
                    RunCommandAction(
                        type="run_command",
                        command=command,
                        max_output_chars=1_000,
                    ),
                )
            artifact = resolve_command_output_artifact(
                workspace,
                result.result.stdout_path or "",
            )
            artifact_text = artifact.read_text(encoding="utf-8") if artifact else ""

        self.assertEqual(result.result.exit_code, 0)
        self.assertTrue(result.result.stdout_truncated)
        self.assertIn("[MASKED_CREDENTIAL]", result.result.stdout)
        self.assertNotIn("environment-secret-value", result.result.stdout)
        self.assertNotIn("file-secret-value", result.result.stdout)
        self.assertNotIn("environment-secret-value", "".join(streamed))
        self.assertNotIn("file-secret-value", "".join(streamed))
        self.assertIsNotNone(artifact)
        self.assertNotIn("environment-secret-value", artifact_text)
        self.assertNotIn("file-secret-value", artifact_text)

    def test_background_logs_are_masked_before_persistence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-mask-bg-") as base:
            root = Path(base)
            secret_file = root / "secret.txt"
            secret_file.write_text("background-file-secret", encoding="utf-8")
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "failIfUnavailable": True,
                    "credentials": {
                        "files": [{"path": "secret.txt", "mode": "mask"}],
                        "envVars": [
                            {"name": "VIBEAGENT_TEST_SECRET", "mode": "mask"}
                        ],
                    },
                },
            )
            workspace = create_run_workspace(root)
            command = (
                "python3 -c \"import os,pathlib,sys; "
                "sys.stdout.write(os.environ['VIBEAGENT_TEST_SECRET']); "
                "sys.stderr.write(pathlib.Path('secret.txt').read_text())\""
            )
            with patch.dict(
                os.environ,
                {"VIBEAGENT_TEST_SECRET": "background-env-secret"},
            ):
                started = execute_action(
                    workspace,
                    StartCommandAction(type="start_command", command=command),
                )
                try:
                    waited = execute_action(
                        workspace,
                        WaitProcessAction(
                            type="wait_process",
                            process_id=started.process_id,
                            timeout_ms=5_000,
                        ),
                    )
                finally:
                    if started.process_id:
                        execute_action(
                            workspace,
                            StopProcessAction(
                                type="stop_process",
                                process_id=started.process_id,
                            ),
                        )
            stdout_log = Path(started.stdout_path).read_text(encoding="utf-8")
            stderr_log = Path(started.stderr_path).read_text(encoding="utf-8")

        self.assertTrue(started.ok)
        self.assertEqual(waited.exit_code, 0)
        self.assertEqual(waited.stdout, "[MASKED_CREDENTIAL]")
        self.assertEqual(waited.stderr, "[MASKED_CREDENTIAL]")
        self.assertEqual(stdout_log, "[MASKED_CREDENTIAL]")
        self.assertEqual(stderr_log, "[MASKED_CREDENTIAL]")


if __name__ == "__main__":
    unittest.main()
