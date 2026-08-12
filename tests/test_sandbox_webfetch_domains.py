from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch

from vibeagent.actions import execute_action
from vibeagent.agent_run_setup import prepare_agent_run
from vibeagent.managed_settings import read_file_managed_settings
from vibeagent.permission_update_runtime import apply_permission_updates
from vibeagent.sandbox_commands import get_sandbox_report
from vibeagent.sandbox_permission_domains import sandbox_webfetch_allow_domains
from vibeagent.types import RunCommandAction
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_core import create_local_workspace
from vibeagent.workspace_permissions import (
    ProjectPermissions,
    permission_rules_from_values,
)
from vibeagent.workspace_sandbox import read_workspace_sandbox


def _write_claude_settings(root: Path, payload: dict[str, object]) -> None:
    path = root / ".claude/settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _sandbox_available() -> bool:
    if shutil.which("bwrap") is None:
        return False
    with tempfile.TemporaryDirectory(prefix="vibeagent-bwrap-probe-") as base:
        root = Path(base)
        _write_claude_settings(
            root,
            {"sandbox": {"enabled": True, "failIfUnavailable": True}},
        )
        return read_workspace_sandbox(create_run_workspace(root)).available


class SandboxWebFetchDomainTests(unittest.TestCase):
    def test_only_trusted_domain_scoped_webfetch_allows_are_merged(self) -> None:
        permissions = ProjectPermissions(
            rules=permission_rules_from_values(
                "allow",
                (
                    "WebFetch(domain:docs.example.com)",
                    "web_fetch(domain:*.python.org)",
                    "WebFetch(https://unsafe.example.com)",
                    "Read(domain:ignored.example.com)",
                ),
                "project",
            ),
            trusted_allow_sources=("user",),
        )

        untrusted = sandbox_webfetch_allow_domains(
            permissions,
            project_config_trusted=False,
            managed_only=False,
        )
        trusted = sandbox_webfetch_allow_domains(
            permissions,
            project_config_trusted=True,
            managed_only=False,
        )

        self.assertEqual(untrusted, ())
        self.assertEqual(trusted, ("docs.example.com", "*.python.org"))

    def test_static_project_rule_requires_trust_and_is_visible_in_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-webfetch-") as base:
            root = Path(base)
            _write_claude_settings(
                root,
                {
                    "sandbox": {
                        "enabled": True,
                        "network": {"allowedDomains": []},
                    },
                    "permissions": {
                        "allow": ["WebFetch(domain:docs.example.com)"]
                    },
                },
            )
            workspace = create_run_workspace(root)
            untrusted = read_workspace_sandbox(workspace)
            trusted_workspace = replace(workspace, project_config_trusted=True)
            trusted = read_workspace_sandbox(trusted_workspace)
            with patch(
                "vibeagent.sandbox_commands.is_project_permissions_trusted",
                return_value=True,
            ):
                report = get_sandbox_report(root)

        self.assertEqual(untrusted.allowed_domains, ())
        self.assertEqual(trusted.allowed_domains, ("docs.example.com",))
        self.assertEqual(trusted.permission_allowed_domains, ("docs.example.com",))
        network = report["network"]
        assert isinstance(network, dict)
        self.assertEqual(network["webFetchAllowedDomains"], ["docs.example.com"])

    def test_runtime_permission_update_refreshes_workspace_domains(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-webfetch-") as base:
            root = Path(base)
            _write_claude_settings(
                root,
                {"sandbox": {"enabled": True, "network": {"allowedDomains": []}}},
            )
            workspace = create_run_workspace(root)
            updated = apply_permission_updates(
                workspace,
                ProjectPermissions(),
                "ask",
                (
                    {
                        "type": "addRules",
                        "rules": [
                            {
                                "toolName": "WebFetch",
                                "ruleContent": "domain:session.example.com",
                            }
                        ],
                        "behavior": "allow",
                        "destination": "session",
                    },
                ),
                bypass_available=False,
            )
            config = read_workspace_sandbox(updated.workspace)

        self.assertEqual(
            updated.workspace.sandbox_permission_domains,
            ("session.example.com",),
        )
        self.assertEqual(config.allowed_domains, ("session.example.com",))

    def test_agent_setup_merges_trusted_cli_permission_domains(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-webfetch-") as base:
            root = Path(base)
            _write_claude_settings(
                root,
                {"sandbox": {"enabled": True, "network": {"allowedDomains": []}}},
            )
            source = "<cli --allowed-tools>"
            overrides = ProjectPermissions(
                rules=permission_rules_from_values(
                    "allow",
                    ("WebFetch(domain:cli.example.com)",),
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
            setup.workspace.sandbox_permission_domains,
            ("cli.example.com",),
        )
        self.assertEqual(setup.sandbox_config.allowed_domains, ("cli.example.com",))

    def test_managed_domain_lock_keeps_only_managed_webfetch_rules(self) -> None:
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
                                "network": {"allowedDomains": []},
                            },
                            "permissions": {
                                "allow": ["WebFetch(domain:managed.example.com)"]
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                _write_claude_settings(
                    project,
                    {
                        "permissions": {
                            "allow": ["WebFetch(domain:project.example.com)"]
                        }
                    },
                )
                workspace = replace(
                    create_local_workspace(project, "managed-webfetch"),
                    project_config_trusted=True,
                    sandbox_permission_domains=("session.example.com",),
                )
                with patch(
                    "vibeagent.workspace_settings_sources.read_file_managed_settings",
                    lambda: read_file_managed_settings(managed),
                ):
                    config = read_workspace_sandbox(workspace)

        self.assertIsNone(config.error)
        self.assertTrue(config.managed_domains_only)
        self.assertEqual(config.allowed_domains, ("managed.example.com",))
        self.assertEqual(
            config.permission_allowed_domains,
            ("managed.example.com",),
        )


@unittest.skipUnless(_sandbox_available(), "bubblewrap sandbox is unavailable")
class SandboxWebFetchDomainExecutionTests(unittest.TestCase):
    def test_webfetch_allow_rule_reaches_host_through_sandbox_proxy(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                body = b"webfetch-domain-ok"
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
            with tempfile.TemporaryDirectory(prefix="vibeagent-sandbox-webfetch-") as base:
                root = Path(base)
                _write_claude_settings(
                    root,
                    {
                        "sandbox": {
                            "enabled": True,
                            "failIfUnavailable": True,
                            "network": {"allowedDomains": []},
                        },
                        "permissions": {
                            "allow": ["WebFetch(domain:127.0.0.1)"]
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
                            "python3 -c \"import urllib.request; "
                            f"print(urllib.request.urlopen('http://127.0.0.1:{port}/')"
                            ".read().decode())\""
                        ),
                    ),
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertEqual(result.result.exit_code, 0)
        self.assertEqual(result.result.stdout.strip(), "webfetch-domain-ok")


if __name__ == "__main__":
    unittest.main()
