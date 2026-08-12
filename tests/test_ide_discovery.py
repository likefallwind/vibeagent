from __future__ import annotations

import io
import json
import os
from pathlib import Path
import tempfile
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from vibeagent.cli_args import parse_args
from vibeagent.cli import main
from vibeagent.cli_ide import prepare_ide_connection
from vibeagent.ide_context import IDE_CONTEXT_FILE_ENV, IDE_CONTEXT_TOKEN_ENV
from vibeagent.ide_discovery import IdeConnection, discover_ide_connection


class IdeDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="vibeagent-ide-discovery-")
        self.base = Path(self.temp.name)
        self.root = self.base / "project"
        self.root.mkdir()
        self.registry = self.base / "registry"
        self.registry.mkdir(mode=0o700)
        self.token = "a" * 64
        self.context_file = self.base / "context.json"
        self._write_context(self.context_file, self.root, self.token)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_discovers_one_fresh_matching_private_connection(self) -> None:
        descriptor = self._write_connection("one", self.root, self.context_file, self.token)
        now = descriptor.stat().st_mtime

        connection = discover_ide_connection(self.root, registry_root=self.registry, now=now)

        self.assertEqual(connection.workspace_root, self.root.resolve())
        self.assertEqual(connection.context_file, self.context_file)
        self.assertEqual(connection.environment[IDE_CONTEXT_TOKEN_ENV], self.token)

    def test_ignores_stale_invalid_and_other_workspace_connections(self) -> None:
        stale = self._write_connection("stale", self.root, self.context_file, self.token)
        other_root = self.base / "other"
        other_root.mkdir()
        other_context = self.base / "other-context.json"
        self._write_context(other_context, other_root, "b" * 64)
        fresh = self._write_connection("other", other_root, other_context, "b" * 64)
        invalid = self.registry / "invalid.json"
        invalid.write_text("{}", encoding="utf-8")
        invalid.chmod(0o600)
        now = max(fresh.stat().st_mtime, invalid.stat().st_mtime) + 121

        with self.assertRaisesRegex(ValueError, "No VibeAgent IDE connection"):
            discover_ide_connection(self.root, registry_root=self.registry, now=now)

        self.assertTrue(stale.exists())

    def test_rejects_ambiguous_connections_and_public_registry(self) -> None:
        first = self._write_connection("one", self.root, self.context_file, self.token)
        second_context = self.base / "second-context.json"
        self._write_context(second_context, self.root, "b" * 64)
        self._write_connection("two", self.root, second_context, "b" * 64)

        with self.assertRaisesRegex(ValueError, "Multiple VibeAgent IDE connections"):
            discover_ide_connection(self.root, registry_root=self.registry, now=first.stat().st_mtime)

        if os.name != "nt":
            self.registry.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "must not grant"):
                discover_ide_connection(self.root, registry_root=self.registry)

    def test_ignores_descriptor_when_context_identity_does_not_match(self) -> None:
        descriptor = self._write_connection("one", self.root, self.context_file, "b" * 64)
        with self.assertRaisesRegex(ValueError, "No VibeAgent IDE connection"):
            discover_ide_connection(
                self.root,
                registry_root=self.registry,
                now=descriptor.stat().st_mtime,
            )

    def test_cli_preparer_exports_discovered_credentials(self) -> None:
        args = parse_args(["--cwd", str(self.root), "--ide"])
        connection = IdeConnection(self.context_file, self.token, self.root.resolve())
        with (
            patch("vibeagent.cli_ide.discover_ide_connection", return_value=connection),
            patch.dict(os.environ, {}, clear=True),
        ):
            prepare_ide_connection(args)
            self.assertEqual(os.environ[IDE_CONTEXT_FILE_ENV], str(self.context_file))
            self.assertEqual(os.environ[IDE_CONTEXT_TOKEN_ENV], self.token)

    def test_cli_missing_ide_fails_before_provider_creation(self) -> None:
        stdout = io.StringIO()
        with (
            patch(
                "vibeagent.cli_ide.discover_ide_connection",
                side_effect=ValueError("No VibeAgent IDE connection is available for this project."),
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--cwd", str(self.root), "--ide"])

        self.assertEqual(exit_code, 2)
        self.assertIn("No VibeAgent IDE connection", stdout.getvalue())
        create_chat_client.assert_not_called()

    def test_node_published_connection_is_discovered_by_python(self) -> None:
        script = """
const { IdeContextBridge } = require('./extensions/vscode/src/context');
const bridge = new IdeContextBridge(process.argv[1], { registryRoot: process.argv[2] });
process.stdout.write(JSON.stringify(bridge.environment()));
"""
        result = subprocess.run(
            ["node", "-e", script, str(self.root), str(self.registry)],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        environment = json.loads(result.stdout)
        connection = discover_ide_connection(self.root, registry_root=self.registry)
        self.assertEqual(str(connection.context_file), environment[IDE_CONTEXT_FILE_ENV])
        self.assertEqual(connection.token, environment[IDE_CONTEXT_TOKEN_ENV])

    def _write_context(self, path: Path, root: Path, token: str) -> None:
        path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "token": token,
                    "workspaceRoot": str(root.resolve()),
                    "file": None,
                    "dirty": False,
                    "selection": None,
                    "diagnostics": [],
                }
            ),
            encoding="utf-8",
        )
        path.chmod(0o600)

    def _write_connection(self, name: str, root: Path, context: Path, token: str) -> Path:
        path = self.registry / f"{name}.json"
        path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "workspaceRoot": str(root.resolve()),
                    "contextFile": str(context),
                    "token": token,
                }
            ),
            encoding="utf-8",
        )
        path.chmod(0o600)
        return path


if __name__ == "__main__":
    unittest.main()
