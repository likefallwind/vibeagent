from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.actions import execute_action
from vibeagent.command_sandbox import prepare_command_launch
from vibeagent.sandbox_commands import format_sandbox_report_text, get_sandbox_report
from vibeagent.sandbox_seccomp_filter import (
    SECCOMP_FD_TOKEN,
    unix_socket_filter_available,
)
from vibeagent.types import RunCommandAction
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_sandbox import SandboxConfig, read_workspace_sandbox


def _write_sandbox(root: Path, sandbox: dict[str, object]) -> None:
    path = root / ".vibeagent/sandbox.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sandbox), encoding="utf-8")


def _sandbox_available() -> bool:
    bwrap = shutil.which("bwrap")
    if bwrap is None or not unix_socket_filter_available():
        return False
    with tempfile.TemporaryDirectory(prefix="vibeagent-unix-socket-probe-") as base:
        root = Path(base)
        _write_sandbox(root, {"enabled": True, "failIfUnavailable": True})
        config = read_workspace_sandbox(create_run_workspace(root))
        return config.available and config.unix_socket_filter_available


class UnixSocketSandboxConfigTests(unittest.TestCase):
    def test_project_allow_all_requires_trust(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-unix-socket-") as base:
            root = Path(base)
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "network": {"allowAllUnixSockets": True},
                },
            )
            workspace = create_run_workspace(root)
            untrusted = read_workspace_sandbox(workspace)
            trusted = read_workspace_sandbox(
                replace(workspace, project_config_trusted=True)
            )

        self.assertIn("requires explicit project configuration trust", untrusted.error or "")
        self.assertIsNone(trusted.error)
        self.assertTrue(trusted.allow_all_unix_sockets)
        self.assertFalse(trusted.unix_socket_filter_active)

    def test_allow_unix_socket_paths_are_reported_but_do_not_disable_filter(self) -> None:
        config = SandboxConfig(
            enabled=True,
            available=True,
            bwrap_path="/usr/bin/bwrap",
            allowed_unix_sockets=("~/.ssh/agent.sock",),
            unix_socket_filter_available=True,
            unix_socket_filter_active=True,
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-unix-socket-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            with patch(
                "vibeagent.sandbox_commands.read_workspace_sandbox",
                return_value=config,
            ):
                report = get_sandbox_report(root)
            with patch(
                "vibeagent.command_sandbox.read_workspace_sandbox",
                return_value=config,
            ):
                launch = prepare_command_launch(workspace, "true", root)

        network = report["network"]
        self.assertIsInstance(network, dict)
        assert isinstance(network, dict)
        self.assertEqual(network["allowUnixSockets"], ["~/.ssh/agent.sock"])
        self.assertTrue(network["unixSocketFilterActive"])
        self.assertIn("allowUnixSockets:", format_sandbox_report_text(report))
        self.assertEqual(
            launch.argv[:5],
            (
                sys.executable,
                "-m",
                "vibeagent.sandbox_seccomp_launcher",
                "--",
                "/usr/bin/bwrap",
            ),
        )
        self.assertIn(SECCOMP_FD_TOKEN, launch.argv)

    def test_domain_proxy_installs_filter_only_for_user_command(self) -> None:
        config = SandboxConfig(
            enabled=True,
            available=True,
            bwrap_path="/usr/bin/bwrap",
            network_disabled=True,
            network_available=True,
            allowed_domains=("example.com",),
            unix_socket_filter_available=True,
            unix_socket_filter_active=True,
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-unix-socket-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            with patch(
                "vibeagent.command_sandbox.read_workspace_sandbox",
                return_value=config,
            ):
                launch = prepare_command_launch(workspace, "true", root)

        self.assertNotIn("--seccomp", launch.argv)
        self.assertIn("vibeagent.sandbox_network_launcher", launch.argv)
        self.assertIn("vibeagent.sandbox_seccomp_launcher", launch.argv)
        self.assertIn("--install", launch.argv)

    def test_invalid_unix_socket_settings_fail_closed(self) -> None:
        cases = (
            ({"allowAllUnixSockets": "yes"}, "must be a boolean"),
            ({"allowUnixSockets": "agent.sock"}, "must be a list"),
            ({"allowUnixSockets": [""]}, "must contain"),
        )
        for network, expected in cases:
            with self.subTest(network=network), tempfile.TemporaryDirectory(
                prefix="vibeagent-unix-socket-"
            ) as base:
                root = Path(base)
                _write_sandbox(root, {"enabled": True, "network": network})
                config = read_workspace_sandbox(create_run_workspace(root))
            self.assertIn(expected, config.error or "")


@unittest.skipUnless(_sandbox_available(), "Bubblewrap seccomp filtering is unavailable")
class UnixSocketSandboxExecutionTests(unittest.TestCase):
    def test_default_blocks_and_trusted_allow_all_permits_unix_socket(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-unix-socket-") as base:
            root = Path(base)
            socket_path = root / "host.sock"
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(socket_path.as_posix())
            listener.listen(1)
            listener.settimeout(0.2)
            try:
                _write_sandbox(
                    root,
                    {"enabled": True, "failIfUnavailable": True},
                )
                workspace = create_run_workspace(root)
                command = (
                    "python3 -c \"import socket; "
                    "s=socket.socket(socket.AF_UNIX); "
                    f"s.connect('{socket_path.as_posix()}'); s.sendall(b'ok')\""
                )
                blocked = execute_action(
                    workspace,
                    RunCommandAction(type="run_command", command=command),
                )
                _write_sandbox(
                    root,
                    {
                        "enabled": True,
                        "failIfUnavailable": True,
                        "network": {"allowAllUnixSockets": True},
                    },
                )
                trusted_workspace = replace(
                    workspace,
                    project_config_trusted=True,
                )
                allowed = execute_action(
                    trusted_workspace,
                    RunCommandAction(type="run_command", command=command),
                )
                connection, _address = listener.accept()
                with connection:
                    received = connection.recv(2)
            finally:
                listener.close()

        self.assertNotEqual(blocked.result.exit_code, 0)
        self.assertIn("Operation not permitted", blocked.result.stderr)
        self.assertEqual(allowed.result.exit_code, 0)
        self.assertEqual(received, b"ok")


if __name__ == "__main__":
    unittest.main()
