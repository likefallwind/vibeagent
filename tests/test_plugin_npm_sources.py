from __future__ import annotations

import base64
from io import BytesIO
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tests.user_home_test_case import IsolatedUserHomeTestCase
from tests.test_plugin_remote_sources import write_remote_marketplace
from tests.test_plugins import write_demo_plugin
from vibeagent.marketplace_manifest import read_marketplace_manifest
from vibeagent.marketplace_store import (
    add_marketplace,
    install_marketplace_plugin,
    remove_marketplace,
)
from vibeagent.plugin_commands import handle_plugin_command
from vibeagent.plugin_installation import copy_plugin_tree
from vibeagent.plugin_npm_sources import (
    download_npm_plugin,
    normalize_npm_registry,
    validate_npm_package_name,
    validate_npm_version_selector,
)
from vibeagent.plugin_store import list_installed_plugins, update_installed_plugin
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_skills import read_project_skills


class _Response:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, limit: int) -> bytes:
        chunk = self.body[self.offset : self.offset + limit]
        self.offset += len(chunk)
        return chunk


def npm_tarball(files: dict[str, bytes], *, symlink: tuple[str, str] | None = None) -> bytes:
    stream = BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            info.mode = 0o755 if name.endswith("/check") else 0o644
            archive.addfile(info, BytesIO(content))
        if symlink is not None:
            info = tarfile.TarInfo(symlink[0])
            info.type = tarfile.SYMTYPE
            info.linkname = symlink[1]
            archive.addfile(info)
    return stream.getvalue()


def npm_metadata(package: str, version: str, tarball: bytes) -> bytes:
    integrity = base64.b64encode(hashlib.sha512(tarball).digest()).decode("ascii")
    return json.dumps(
        {
            "name": package,
            "dist-tags": {"latest": version},
            "versions": {
                version: {
                    "name": package,
                    "version": version,
                    "dist": {
                        "tarball": f"https://registry.example.com/{package}/-/{version}.tgz",
                        "integrity": f"sha512-{integrity}",
                    },
                }
            },
        }
    ).encode("utf-8")


class NpmSourceSafetyTests(IsolatedUserHomeTestCase):
    def test_npm_source_identifiers_and_registry_are_bounded(self) -> None:
        self.assertEqual(validate_npm_package_name("@acme/review-plugin"), "@acme/review-plugin")
        self.assertEqual(validate_npm_version_selector(None), "latest")
        self.assertEqual(
            normalize_npm_registry("https://registry.example.com/npm"),
            "https://registry.example.com/npm/",
        )
        for package in ("../plugin", "@scope", "UPPER", "name with spaces"):
            with self.subTest(package=package), self.assertRaises(ValueError):
                validate_npm_package_name(package)
        with self.assertRaisesRegex(ValueError, "exact version or dist-tag"):
            validate_npm_version_selector("latest/../../private")
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            normalize_npm_registry("http://registry.example.com")

    def test_download_verifies_integrity_and_extracts_package_root(self) -> None:
        tarball = npm_tarball(
            {
                "package/.claude-plugin/plugin.json": b'{"name":"demo-plugin"}',
                "package/skills/review/SKILL.md": b"---\ndescription: Review code\n---\n",
                "package/bin/check": b"#!/bin/sh\nexit 0\n",
            }
        )
        metadata = npm_metadata("@acme/demo-plugin", "1.2.3", tarball)
        with tempfile.TemporaryDirectory(prefix="vibeagent-npm-source-") as base:
            destination = Path(base) / "plugin"
            with patch(
                "vibeagent.plugin_npm_sources.open_scoped_url",
                side_effect=[_Response(metadata), _Response(tarball)],
            ) as open_url:
                version = download_npm_plugin(
                    "@acme/demo-plugin",
                    destination,
                    registry="https://registry.example.com/npm/",
                )

            self.assertEqual(version, "1.2.3")
            self.assertTrue(destination.joinpath(".claude-plugin/plugin.json").is_file())
            self.assertTrue(destination.joinpath("bin/check").stat().st_mode & 0o111)
            self.assertFalse(destination.joinpath("package").exists())
            self.assertIn("@acme%2Fdemo-plugin", open_url.call_args_list[0].args[0].full_url)
            self.assertTrue(open_url.call_args_list[1].kwargs["require_https"])

    def test_integrity_failure_and_unsafe_archive_leave_no_plugin_tree(self) -> None:
        safe_tarball = npm_tarball({"package/plugin.json": b"{}"})
        bad_metadata = json.loads(npm_metadata("demo-plugin", "1.0.0", safe_tarball))
        bad_metadata["versions"]["1.0.0"]["dist"]["integrity"] = "sha512-" + base64.b64encode(
            b"x" * 64
        ).decode("ascii")
        unsafe_tarball = npm_tarball(
            {"package/plugin.json": b"{}"},
            symlink=("package/escape", "../../outside"),
        )
        unsafe_metadata = npm_metadata("demo-plugin", "1.0.0", unsafe_tarball)

        with tempfile.TemporaryDirectory(prefix="vibeagent-npm-source-") as base:
            root = Path(base)
            destination = root / "integrity-plugin"
            with patch(
                "vibeagent.plugin_npm_sources.open_scoped_url",
                side_effect=[_Response(json.dumps(bad_metadata).encode()), _Response(safe_tarball)],
            ):
                with self.assertRaisesRegex(ValueError, "integrity verification failed"):
                    download_npm_plugin("demo-plugin", destination)
            self.assertFalse(destination.exists())

            destination = root / "unsafe-plugin"
            with patch(
                "vibeagent.plugin_npm_sources.open_scoped_url",
                side_effect=[_Response(unsafe_metadata), _Response(unsafe_tarball)],
            ):
                with self.assertRaisesRegex(ValueError, "unsupported entry"):
                    download_npm_plugin("demo-plugin", destination)
            self.assertFalse(destination.exists())
            self.assertFalse((root / "outside").exists())

    def test_registry_metadata_must_match_requested_package(self) -> None:
        tarball = npm_tarball({"package/plugin.json": b"{}"})
        metadata = json.loads(npm_metadata("other-plugin", "1.0.0", tarball))
        with tempfile.TemporaryDirectory(prefix="vibeagent-npm-source-") as base:
            with patch(
                "vibeagent.plugin_npm_sources.open_scoped_url",
                return_value=_Response(json.dumps(metadata).encode()),
            ):
                with self.assertRaisesRegex(ValueError, "identity does not match"):
                    download_npm_plugin("demo-plugin", Path(base) / "plugin")


class NpmMarketplaceTests(IsolatedUserHomeTestCase):
    def test_npm_marketplace_plugin_installs_into_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-npm-market-") as base:
            root = Path(base)
            catalog = write_remote_marketplace(
                root,
                {
                    "source": "npm",
                    "package": "@acme/demo-plugin",
                    "version": "stable",
                    "registry": "https://registry.example.com/npm",
                },
            )
            marketplace = add_marketplace(root, "remote-catalog")
            plugin = read_marketplace_manifest(catalog).plugins[0]
            self.assertEqual(marketplace.source_kind, "local")
            self.assertEqual(plugin.source_kind, "npm")
            self.assertEqual(plugin.npm_package, "@acme/demo-plugin")
            self.assertEqual(plugin.npm_version, "stable")
            self.assertEqual(plugin.npm_registry, "https://registry.example.com/npm/")
            remote_plugin = write_demo_plugin(root / "npm-package-source")

            def download(
                package: str,
                destination: Path,
                **kwargs: object,
            ) -> str:
                self.assertEqual(package, "@acme/demo-plugin")
                self.assertEqual(kwargs["version"], "stable")
                copy_plugin_tree(remote_plugin, destination)
                return "1.2.3"

            with patch(
                "vibeagent.marketplace_plugin_fetch.download_npm_plugin",
                side_effect=download,
            ):
                result = handle_plugin_command(root, "install demo-plugin@remote-tools")

            self.assertTrue(result.changed)
            self.assertIn("Installed plugin demo-plugin 1.2.3", result.text)
            installed = list_installed_plugins(root)[0]
            self.assertEqual(installed.marketplace, "remote-tools")
            workspace = create_run_workspace(root, "npm-plugin")
            self.assertIn(
                "demo-plugin:review",
                [item["name"] for item in read_project_skills(workspace)["skills"]],
            )

    def test_npm_marketplace_plugin_uses_atomic_update_flow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-npm-market-") as base:
            root = Path(base)
            catalog = write_remote_marketplace(
                root,
                {"source": "npm", "package": "demo-plugin", "version": "latest"},
            )
            add_marketplace(root, "remote-catalog")
            package_root = root / "npm-package-source"
            remote_plugin = write_demo_plugin(package_root)

            def download(_package: str, destination: Path, **_kwargs: object) -> str:
                copy_plugin_tree(remote_plugin, destination)
                return "1.2.4"

            with patch(
                "vibeagent.marketplace_plugin_fetch.download_npm_plugin",
                side_effect=download,
            ):
                installed = install_marketplace_plugin(root, "demo-plugin@remote-tools")

            manifest_path = remote_plugin / ".claude-plugin/plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["version"] = "1.2.4"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            skill_path = remote_plugin / "skills/review/SKILL.md"
            skill_path.write_text(
                "---\nname: review\ndescription: Updated review\n---\n\nUpdated npm content.\n",
                encoding="utf-8",
            )
            catalog_path = catalog / ".claude-plugin/marketplace.json"
            catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog_payload["plugins"][0]["version"] = "1.2.4"
            catalog_path.write_text(json.dumps(catalog_payload), encoding="utf-8")

            with patch(
                "vibeagent.marketplace_plugin_fetch.download_npm_plugin",
                side_effect=download,
            ):
                updated = update_installed_plugin(root, "demo-plugin")

            self.assertEqual(installed.version, "1.2.3")
            self.assertTrue(updated.updated)
            self.assertEqual(updated.plugin.version, "1.2.4")
            cached_skill = root / ".vibeagent/plugins/cache/demo-plugin/skills/review/SKILL.md"
            self.assertIn("Updated npm content", cached_skill.read_text(encoding="utf-8"))

    def test_marketplace_removal_during_npm_fetch_rolls_back_install(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-npm-market-") as base:
            root = Path(base)
            write_remote_marketplace(
                root,
                {"source": "npm", "package": "demo-plugin"},
            )
            add_marketplace(root, "remote-catalog")
            remote_plugin = write_demo_plugin(root / "npm-package-source")

            def download(_package: str, destination: Path, **_kwargs: object) -> str:
                remove_marketplace(root, "remote-tools")
                copy_plugin_tree(remote_plugin, destination)
                return "1.2.3"

            with patch(
                "vibeagent.marketplace_plugin_fetch.download_npm_plugin",
                side_effect=download,
            ):
                with self.assertRaisesRegex(ValueError, "removed during plugin installation"):
                    install_marketplace_plugin(root, "demo-plugin@remote-tools")

            self.assertEqual(list_installed_plugins(root), [])
            self.assertEqual(list(root.joinpath(".vibeagent/plugins/fetches").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
