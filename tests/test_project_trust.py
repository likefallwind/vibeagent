from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from vibeagent.cli import main
from vibeagent.cli_output import prompt_project_permission_trust
from vibeagent.cli_runner import run_one_shot
from vibeagent.project_trust import (
    TRUST_FILE_ENV,
    get_project_trust_report,
    is_project_permissions_trusted,
    read_project_trust_store,
    trust_project_permissions,
    untrust_project_permissions,
)
from vibeagent.workspace import create_run_workspace


class ProjectTrustStoreTests(unittest.TestCase):
    def test_trust_is_idempotent_private_and_removable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-trust-") as base:
            root = Path(base, "project")
            root.mkdir()
            store = Path(base, "config", "trusted-projects.json")

            initial = get_project_trust_report(root, store)
            trusted = trust_project_permissions(root, store)
            repeated = trust_project_permissions(root, store)
            mode = stat.S_IMODE(store.stat().st_mode)
            removed = untrust_project_permissions(root, store)
            missing = untrust_project_permissions(root, store)

        self.assertFalse(initial["trusted"])
        self.assertTrue(trusted["trusted"])
        self.assertTrue(trusted["changed"])
        self.assertFalse(repeated["changed"])
        self.assertEqual(mode, 0o600)
        self.assertFalse(removed["trusted"])
        self.assertTrue(removed["changed"])
        self.assertFalse(missing["changed"])

    def test_store_preserves_multiple_canonical_projects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-trust-") as base:
            root = Path(base)
            first = root / "first"
            second = root / "second"
            first.mkdir()
            second.mkdir()
            store_path = root / "trust.json"

            trust_project_permissions(first / ".", store_path)
            trust_project_permissions(second, store_path)
            store = read_project_trust_store(store_path)

        self.assertEqual(set(store.projects), {first.resolve().as_posix(), second.resolve().as_posix()})

    def test_environment_override_is_used(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-trust-") as base:
            root = Path(base, "project")
            root.mkdir()
            store = Path(base, "custom-trust.json")
            with patch.dict(os.environ, {TRUST_FILE_ENV: str(store)}):
                trust_project_permissions(root)
                trusted = is_project_permissions_trusted(root)
                workspace = create_run_workspace(root)

        self.assertTrue(trusted)
        self.assertTrue(workspace.project_config_trusted)

    def test_malformed_store_fails_closed_and_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-trust-") as base:
            root = Path(base, "project")
            root.mkdir()
            store = Path(base, "trust.json")
            store.write_text("{bad", encoding="utf-8")

            report = get_project_trust_report(root, store)
            mutation = trust_project_permissions(root, store)
            content = store.read_text(encoding="utf-8")

        self.assertFalse(report["trusted"])
        self.assertFalse(report["ok"])
        self.assertFalse(mutation["ok"])
        self.assertEqual(content, "{bad")

    def test_symlink_store_and_parent_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-trust-") as base:
            root = Path(base, "project")
            root.mkdir()
            external = Path(base, "external.json")
            external.write_text(json.dumps({"version": 1, "projects": {}}), encoding="utf-8")
            linked_store = Path(base, "trust.json")
            linked_store.symlink_to(external)
            store_report = get_project_trust_report(root, linked_store)

            real_parent = Path(base, "real")
            real_parent.mkdir()
            linked_parent = Path(base, "linked")
            linked_parent.symlink_to(real_parent, target_is_directory=True)
            parent_report = get_project_trust_report(root, linked_parent / "trust.json")

        self.assertIn("symbolic link", str(store_report["storeError"]))
        self.assertIn("symbolic link", str(parent_report["storeError"]))


class ProjectTrustIntegrationTests(unittest.TestCase):
    def test_cli_trust_status_and_untrust_round_trip(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-trust-") as base:
            root = Path(base, "project")
            root.mkdir()
            store = Path(base, "trust.json")
            output = StringIO()
            with patch.dict(os.environ, {TRUST_FILE_ENV: str(store)}), redirect_stdout(output):
                trust_code = main(["--trust-project", "--cwd", str(root), "--json"])
                status_code = main(["--trust-status", "--cwd", str(root), "--json"])
                untrust_code = main(["--untrust-project", "--cwd", str(root), "--json"])
            payloads = [json.loads(line) for line in output.getvalue().splitlines()]

        self.assertEqual((trust_code, status_code, untrust_code), (0, 0, 0))
        self.assertTrue(payloads[0]["projectTrust"]["trusted"])
        self.assertTrue(payloads[1]["projectTrust"]["trusted"])
        self.assertFalse(payloads[2]["projectTrust"]["trusted"])

    def test_one_shot_runner_uses_persistent_trust(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-trust-") as base:
            root = Path(base, "project")
            root.mkdir()
            store = Path(base, "trust.json")
            with patch.dict(os.environ, {TRUST_FILE_ENV: str(store)}):
                trust_project_permissions(root)
                result = MagicMock()
                result.success = True
                result.status = "completed"
                result.message = "done"
                run_agent_mock = Mock(return_value=result)
                with redirect_stdout(StringIO()):
                    code = run_one_shot(
                        "inspect",
                        "code",
                        "ask",
                        base_dir=str(root),
                        create_chat_client_func=lambda _env: object(),
                        run_agent_func=run_agent_mock,
                    )

        self.assertEqual(code, 0)
        self.assertTrue(run_agent_mock.call_args.kwargs["trust_project_permissions"])

    def test_interactive_prompt_records_or_rejects_allow_rule_trust(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-trust-") as base:
            root = Path(base, "project")
            root.mkdir()
            settings = root / ".claude/settings.json"
            settings.parent.mkdir()
            settings.write_text(json.dumps({"permissions": {"allow": ["Bash(npm test *)"]}}), encoding="utf-8")
            accepted_store = Path(base, "accepted.json")
            with (
                patch.dict(os.environ, {TRUST_FILE_ENV: str(accepted_store)}),
                patch("builtins.input", return_value="yes"),
                redirect_stdout(StringIO()),
            ):
                accepted = prompt_project_permission_trust(root)
            rejected_store = Path(base, "rejected.json")
            with (
                patch.dict(os.environ, {TRUST_FILE_ENV: str(rejected_store)}),
                patch("builtins.input", return_value="no"),
                redirect_stdout(StringIO()),
            ):
                rejected = prompt_project_permission_trust(root)

        self.assertTrue(accepted)
        self.assertFalse(rejected)
        self.assertFalse(rejected_store.exists())

    def test_interactive_prompt_is_silent_without_allow_rules(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-trust-") as base:
            root = Path(base, "project")
            root.mkdir()
            store = Path(base, "trust.json")
            with (
                patch.dict(os.environ, {TRUST_FILE_ENV: str(store)}),
                patch("builtins.input") as input_mock,
                redirect_stdout(StringIO()),
            ):
                trusted = prompt_project_permission_trust(root)

        self.assertFalse(trusted)
        input_mock.assert_not_called()

    def test_interactive_prompt_redacts_sensitive_permission_rule_values(self) -> None:
        secret = "prompt-secret-value"
        with tempfile.TemporaryDirectory(prefix="vibeagent-trust-") as base:
            root = Path(base, "project")
            root.mkdir()
            settings = root / ".claude/settings.json"
            settings.parent.mkdir()
            settings.write_text(
                json.dumps({"permissions": {"allow": [f"Bash(API_KEY={secret} python3 -V)"]}}),
                encoding="utf-8",
            )
            stdout = StringIO()
            with patch("builtins.input", return_value="no"), redirect_stdout(stdout):
                trusted = prompt_project_permission_trust(root)

        self.assertFalse(trusted)
        self.assertIn("API_KEY=[REDACTED]", stdout.getvalue())
        self.assertNotIn(secret, stdout.getvalue())

    def test_interactive_prompt_bounds_displayed_permission_rules(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-trust-") as base:
            root = Path(base, "project")
            root.mkdir()
            settings = root / ".claude/settings.json"
            settings.parent.mkdir()
            settings.write_text(
                json.dumps({"permissions": {"allow": [f"Bash(command-{index})" for index in range(25)]}}),
                encoding="utf-8",
            )
            stdout = StringIO()
            with patch("builtins.input", return_value="no"), redirect_stdout(stdout):
                trusted = prompt_project_permission_trust(root)

        output = stdout.getvalue()
        self.assertFalse(trusted)
        self.assertIn("Bash(command-19)", output)
        self.assertNotIn("Bash(command-20)", output)
        self.assertIn("5 more allow rule(s) not shown", output)


if __name__ == "__main__":
    unittest.main()
