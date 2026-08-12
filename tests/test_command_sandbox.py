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
from vibeagent.cli_args import parse_args
from vibeagent.command_parsing import parse_local_command
from vibeagent.command_sandbox import prepare_command_launch
from vibeagent.local_run_commands import get_run_report
from vibeagent.project_trust import TRUST_FILE_ENV, trust_project_permissions
from vibeagent.prompts import build_messages
from vibeagent.sandbox_commands import format_sandbox_report_text, get_sandbox_report
from vibeagent.session_timeline_reports import format_session_event_timeline_item
from vibeagent.session_types import SessionEvent
from vibeagent.types import (
    ReadProcessAction,
    RunCommandAction,
    StartCommandAction,
    StopProcessAction,
    WaitProcessAction,
)
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_sandbox import SandboxConfig, read_workspace_sandbox


def _write_sandbox(root: Path, sandbox: dict[str, object], source: str = ".vibeagent/sandbox.json") -> Path:
    path = root / source
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"sandbox": sandbox} if source.startswith(".claude/") else sandbox
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _sandbox_available() -> bool:
    bwrap = shutil.which("bwrap")
    if bwrap is None:
        return False
    with tempfile.TemporaryDirectory(prefix="vibeagent-bwrap-probe-") as base:
        root = Path(base)
        _write_sandbox(root, {"enabled": True, "failIfUnavailable": True})
        return read_workspace_sandbox(create_run_workspace(root)).available


class SandboxConfigTests(unittest.TestCase):
    def test_command_sandbox_binds_additional_working_directories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
            parent = Path(base)
            root = parent / "main"
            shared = parent / "shared"
            root.mkdir()
            shared.mkdir()
            workspace = create_run_workspace(root, additional_roots=(shared,))
            config = SandboxConfig(enabled=True, available=True, bwrap_path="/usr/bin/bwrap")

            with patch("vibeagent.command_sandbox.read_workspace_sandbox", return_value=config):
                launch = prepare_command_launch(workspace, "pwd", shared)

        bind_pairs = [
            launch.argv[index + 1 : index + 3]
            for index, value in enumerate(launch.argv)
            if value == "--bind"
        ]
        self.assertIn((str(root.resolve()), str(root.resolve())), bind_pairs)
        self.assertIn((str(shared.resolve()), str(shared.resolve())), bind_pairs)
        self.assertIn(("--chdir", str(shared.resolve())), zip(launch.argv, launch.argv[1:]))

    def test_cli_prompt_and_timeline_report_sandbox_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
            root = Path(base)
            _write_sandbox(root, {"enabled": True, "failIfUnavailable": False})
            report = get_sandbox_report(root)
            text = format_sandbox_report_text(report)
            prompt = "\n".join(str(item.content) for item in build_messages("Inspect", create_run_workspace(root)))

        self.assertTrue(parse_args(["--sandbox-status"]).sandbox_status)
        self.assertEqual(parse_local_command("/sandbox").type, "sandbox")
        self.assertTrue(report["enabled"])
        self.assertTrue(report["autoAllowBashIfSandboxed"])
        self.assertFalse(report["autoApprovalReady"])
        self.assertIn("Command sandbox:", text)
        self.assertIn("autoAllowBashIfSandboxed: yes", text)
        self.assertIn("autoApprovalReady: no", text)
        self.assertIn("Command sandbox enabled", prompt)

        event = SessionEvent(
            line_number=3,
            type="sandbox_loaded",
            payload={
                "enabled": True,
                "active": True,
                "available": True,
                "network_disabled": False,
                "auto_allow_bash_if_sandboxed": True,
                "sources": [".vibeagent/sandbox.json"],
                "error": None,
            },
        )
        summary = format_session_event_timeline_item(event)
        self.assertIn("enabled=yes", summary)
        self.assertIn("active=yes", summary)
        self.assertIn("autoAllow=yes", summary)

    def test_merges_sources_with_specific_scalar_precedence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
            root = Path(base)
            (root / "cache").mkdir()
            (root / "secret.txt").write_text("secret", encoding="utf-8")
            _write_sandbox(
                root,
                {
                    "enabled": False,
                    "filesystem": {"denyRead": ["secret.txt"]},
                },
                ".claude/settings.json",
            )
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "failIfUnavailable": True,
                    "network": {"allowedDomains": []},
                    "filesystem": {"allowWrite": ["cache"]},
                },
            )
            config = read_workspace_sandbox(create_run_workspace(root))

        self.assertTrue(config.enabled)
        self.assertTrue(config.fail_if_unavailable)
        self.assertTrue(config.auto_allow_bash_if_sandboxed)
        self.assertTrue(config.network_disabled)
        self.assertEqual([path.name for path in config.allow_write], ["cache"])
        self.assertEqual([path.name for path in config.deny_read], ["secret.txt"])
        self.assertEqual(config.sources, (".claude/settings.json", ".vibeagent/sandbox.json"))

    def test_external_expansions_and_exclusions_require_project_trust(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
            parent = Path(base)
            root = parent / "project"
            external = parent / "external"
            root.mkdir()
            external.mkdir()
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "excludedCommands": ["docker *"],
                    "filesystem": {"allowWrite": [external.as_posix()]},
                },
            )
            workspace = create_run_workspace(root)
            untrusted = read_workspace_sandbox(workspace)
            trusted = read_workspace_sandbox(replace(workspace, project_config_trusted=True))

        self.assertIn("requires explicit project configuration trust", untrusted.error or "")
        self.assertIsNone(trusted.error)
        self.assertEqual(trusted.allow_write, (external.resolve(),))
        self.assertEqual(trusted.excluded_commands, ("docker *",))

    def test_invalid_or_partially_supported_security_settings_fail_closed(self) -> None:
        cases = [
            ({"enabled": "yes"}, "must be a boolean"),
            ({"enabled": True, "autoAllowBashIfSandboxed": "yes"}, "must be a boolean"),
            (
                {"enabled": True, "network": {"allowedDomains": ["https://example.com"]}},
                "invalid domain",
            ),
            (
                {"enabled": True, "network": {"strictAllowlist": False}},
                "subprocess network prompts are unavailable",
            ),
            ({"enabled": True, "filesystem": {"allowRead": ["."]}}, "allowRead is not supported"),
            ({"enabled": True, "filesystem": {"denyRead": ["**/.env"]}}, "does not support glob"),
        ]
        for payload, expected in cases:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
                root = Path(base)
                _write_sandbox(root, payload)
                config = read_workspace_sandbox(create_run_workspace(root))
            self.assertIn(expected, config.error or "")

    def test_domain_allowlist_requires_trust_and_denies_override_wildcards(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
            root = Path(base)
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "network": {
                        "allowedDomains": ["*.example.com", "api.example.com"],
                        "deniedDomains": ["private.example.com"],
                        "strictAllowlist": True,
                    },
                },
            )
            workspace = create_run_workspace(root)
            untrusted = read_workspace_sandbox(workspace)
            trusted = read_workspace_sandbox(
                replace(workspace, project_config_trusted=True)
            )

        self.assertIn("requires explicit project configuration trust", untrusted.error or "")
        self.assertIsNone(trusted.error)
        self.assertEqual(
            trusted.allowed_domains,
            ("*.example.com", "api.example.com"),
        )
        self.assertEqual(trusted.denied_domains, ("private.example.com",))
        self.assertTrue(trusted.network_disabled)

    def test_symlinked_config_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
            root = Path(base)
            external = root / "external.json"
            external.write_text("{}", encoding="utf-8")
            config_path = root / ".vibeagent/sandbox.json"
            config_path.parent.mkdir()
            config_path.symlink_to(external)
            config = read_workspace_sandbox(create_run_workspace(root))

        self.assertIn("symbolic link", config.error or "")

    def test_trusted_excluded_command_uses_explicit_unsandboxed_launch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
            root = Path(base)
            _write_sandbox(root, {"enabled": True, "excludedCommands": ["docker *"]})
            workspace = replace(create_run_workspace(root), project_config_trusted=True)
            launch = prepare_command_launch(workspace, "docker ps", root)

        self.assertFalse(launch.sandboxed)
        self.assertIn("excluded", launch.warning or "")


@unittest.skipUnless(_sandbox_available(), "bubblewrap sandbox is unavailable")
class SandboxExecutionTests(unittest.TestCase):
    def test_local_run_command_inherits_persistent_project_trust(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
            parent = Path(base)
            root = parent / "project"
            external = parent / "external"
            root.mkdir()
            external.mkdir()
            trust_file = parent / "trust.json"
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "failIfUnavailable": True,
                    "filesystem": {"allowWrite": [external.as_posix()]},
                },
            )
            with patch.dict(os.environ, {TRUST_FILE_ENV: trust_file.as_posix()}):
                trust_project_permissions(root)
                report = get_run_report(root, f"printf local > {external.as_posix()}/local.txt")
            content = external.joinpath("local.txt").read_text(encoding="utf-8")

        self.assertTrue(report["sandboxed"])
        self.assertEqual(report["exitCode"], 0)
        self.assertEqual(content, "local")

    def test_project_write_succeeds_and_outside_write_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
            parent = Path(base)
            root = parent / "project"
            root.mkdir()
            outside = parent / "outside.txt"
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "failIfUnavailable": True,
                    "filesystem": {"allowWrite": ["build-cache"]},
                },
            )
            workspace = create_run_workspace(root)

            inside_result = execute_action(
                workspace,
                RunCommandAction(type="run_command", command="printf inside > result.txt"),
            )
            outside_result = execute_action(
                workspace,
                RunCommandAction(type="run_command", command=f"printf outside > {outside.as_posix()}"),
            )
            inside_content = root.joinpath("result.txt").read_text(encoding="utf-8")
            outside_exists = outside.exists()

        self.assertTrue(inside_result.result.sandboxed)
        self.assertEqual(inside_result.result.exit_code, 0)
        self.assertEqual(inside_content, "inside")
        self.assertFalse(outside_exists)

    def test_tmp_is_ephemeral_and_network_namespace_can_be_isolated(self) -> None:
        host_tmp = Path("/tmp/vibeagent-sandbox-host-marker")
        host_tmp.unlink(missing_ok=True)
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
            root = Path(base)
            _write_sandbox(root, {"enabled": True, "failIfUnavailable": True})
            workspace = create_run_workspace(root)
            tmp_result = execute_action(
                workspace,
                RunCommandAction(
                    type="run_command",
                    command=(
                        "python3 -c \"import pathlib; "
                        "pathlib.Path('/tmp/vibeagent-sandbox-host-marker').write_text('inside'); "
                        "print('tmp-ok')\""
                    ),
                ),
            )
            _write_sandbox(
                root,
                {"enabled": True, "failIfUnavailable": True, "network": {"allowedDomains": []}},
            )
            network_config = read_workspace_sandbox(workspace)
            network_result = execute_action(
                workspace,
                RunCommandAction(
                    type="run_command",
                    command="python3 -c \"import json,socket; print(json.dumps(socket.if_nameindex()))\"",
                ),
            )

        self.assertEqual(tmp_result.result.exit_code, 0)
        self.assertIn("tmp-ok", tmp_result.result.stdout)
        self.assertFalse(host_tmp.exists())
        if network_config.network_available:
            interfaces = json.loads(network_result.result.stdout)
            self.assertEqual(network_result.result.exit_code, 0)
            self.assertTrue(all(name == "lo" for _index, name in interfaces))
        else:
            self.assertIsNone(network_result.result.exit_code)
            self.assertIn("network isolation is unavailable", network_result.result.stderr)

    def test_deny_read_and_deny_write_mounts_override_project_write_mount(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
            root = Path(base)
            secret = root / "secret.txt"
            protected = root / "protected"
            secret.write_text("top-secret", encoding="utf-8")
            protected.mkdir()
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "failIfUnavailable": True,
                    "filesystem": {"denyRead": ["secret.txt"], "denyWrite": ["protected"]},
                },
            )
            workspace = create_run_workspace(root)
            read_result = execute_action(workspace, RunCommandAction(type="run_command", command="cat secret.txt"))
            write_result = execute_action(
                workspace,
                RunCommandAction(type="run_command", command="printf bad > protected/file.txt"),
            )
            protected_exists = protected.joinpath("file.txt").exists()

        self.assertNotEqual(read_result.result.exit_code, 0)
        self.assertEqual(read_result.result.stdout, "")
        self.assertNotEqual(write_result.result.exit_code, 0)
        self.assertFalse(protected_exists)

    def test_trusted_allow_write_mount_grants_only_explicit_external_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
            parent = Path(base)
            root = parent / "project"
            allowed = parent / "allowed"
            blocked = parent / "blocked"
            root.mkdir()
            allowed.mkdir()
            blocked.mkdir()
            _write_sandbox(
                root,
                {
                    "enabled": True,
                    "failIfUnavailable": True,
                    "filesystem": {"allowWrite": [allowed.as_posix()]},
                },
            )
            workspace = replace(create_run_workspace(root), project_config_trusted=True)
            allowed_result = execute_action(
                workspace,
                RunCommandAction(type="run_command", command=f"printf ok > {allowed.as_posix()}/result.txt"),
            )
            blocked_result = execute_action(
                workspace,
                RunCommandAction(type="run_command", command=f"printf no > {blocked.as_posix()}/result.txt"),
            )
            allowed_content = allowed.joinpath("result.txt").read_text(encoding="utf-8")
            blocked_exists = blocked.joinpath("result.txt").exists()

        self.assertEqual(allowed_result.result.exit_code, 0)
        self.assertEqual(allowed_content, "ok")
        self.assertNotEqual(blocked_result.result.exit_code, 0)
        self.assertFalse(blocked_exists)

    def test_background_commands_use_the_same_sandbox(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
            parent = Path(base)
            root = parent / "project"
            root.mkdir()
            outside = parent / "background-outside.txt"
            _write_sandbox(root, {"enabled": True, "failIfUnavailable": True})
            workspace = create_run_workspace(root)
            start = execute_action(
                workspace,
                StartCommandAction(type="start_command", command=f"printf blocked > {outside.as_posix()}"),
            )
            try:
                wait = execute_action(
                    workspace,
                    WaitProcessAction(type="wait_process", process_id=start.process_id, timeout_ms=5_000),
                )
                read = execute_action(workspace, ReadProcessAction(type="read_process", process_id=start.process_id))
            finally:
                if start.process_id:
                    execute_action(workspace, StopProcessAction(type="stop_process", process_id=start.process_id))
            outside_exists = outside.exists()

        self.assertTrue(start.ok)
        self.assertTrue(start.sandboxed)
        self.assertTrue(wait.ok)
        self.assertFalse(outside_exists)

    def test_allowed_domain_proxy_reaches_host_and_blocks_other_hosts(self) -> None:
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from threading import Thread

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                body = b"sandbox-network-ok"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
                root = Path(base)
                _write_sandbox(
                    root,
                    {
                        "enabled": True,
                        "failIfUnavailable": True,
                        "network": {"allowedDomains": ["127.0.0.1"]},
                    },
                )
                workspace = replace(
                    create_run_workspace(root), project_config_trusted=True
                )
                allowed = execute_action(
                    workspace,
                    RunCommandAction(
                        type="run_command",
                        command=(
                            "python3 -c \"import urllib.request; "
                            f"print(urllib.request.urlopen('http://127.0.0.1:{port}/').read().decode())\""
                        ),
                    ),
                )
                background = execute_action(
                    workspace,
                    StartCommandAction(
                        type="start_command",
                        command=(
                            "python3 -c \"import urllib.request; "
                            f"print(urllib.request.urlopen('http://127.0.0.1:{port}/').read().decode())\""
                        ),
                    ),
                )
                try:
                    execute_action(
                        workspace,
                        WaitProcessAction(
                            type="wait_process",
                            process_id=background.process_id,
                            timeout_ms=5_000,
                        ),
                    )
                    background_output = execute_action(
                        workspace,
                        ReadProcessAction(
                            type="read_process",
                            process_id=background.process_id,
                        ),
                    )
                finally:
                    if background.process_id:
                        execute_action(
                            workspace,
                            StopProcessAction(
                                type="stop_process",
                                process_id=background.process_id,
                            ),
                        )
                _write_sandbox(
                    root,
                    {
                        "enabled": True,
                        "failIfUnavailable": True,
                        "network": {"allowedDomains": ["example.com"]},
                    },
                )
                blocked = execute_action(
                    workspace,
                    RunCommandAction(
                        type="run_command",
                        command=(
                            "python3 -c \"import urllib.request; "
                            f"urllib.request.urlopen('http://127.0.0.1:{port}/')\""
                        ),
                    ),
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertEqual(allowed.result.exit_code, 0)
        self.assertEqual(allowed.result.stdout.strip(), "sandbox-network-ok")
        self.assertTrue(background.ok)
        self.assertTrue(background.sandboxed)
        self.assertIn("sandbox-network-ok", background_output.stdout)
        self.assertNotEqual(blocked.result.exit_code, 0)
        self.assertIn("403", blocked.result.stderr)


class SandboxUnavailableTests(unittest.TestCase):
    def test_fail_if_unavailable_blocks_or_warns_before_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-") as base:
            root = Path(base)
            _write_sandbox(root, {"enabled": True, "failIfUnavailable": True})
            workspace = create_run_workspace(root)
            with patch("vibeagent.workspace_sandbox.shutil.which", return_value=None):
                blocked = prepare_command_launch(workspace, "printf ok", root)
            _write_sandbox(root, {"enabled": True, "failIfUnavailable": False})
            with patch("vibeagent.workspace_sandbox.shutil.which", return_value=None):
                fallback = prepare_command_launch(workspace, "printf ok", root)

        self.assertIn("unavailable", blocked.error or "")
        self.assertIsNone(fallback.error)
        self.assertIn("Running unsandboxed", fallback.warning or "")
        self.assertFalse(fallback.sandboxed)


if __name__ == "__main__":
    unittest.main()
