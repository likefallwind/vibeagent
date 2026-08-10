from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tests.user_home_test_case import IsolatedUserHomeTestCase
from tests.test_plugins import write_demo_marketplace, write_demo_plugin
from vibeagent.marketplace_manifest import read_marketplace_manifest
from vibeagent.marketplace_store import (
    add_marketplace,
    install_marketplace_plugin,
    list_installed_marketplaces,
    read_installed_marketplace_manifest,
    remove_marketplace,
    update_marketplace,
)
from vibeagent.network_url_safety import UrlSafetyError
from vibeagent.plugin_installation import copy_plugin_tree
from vibeagent.plugin_remote_sources import (
    clone_public_git,
    clone_remote_git,
    download_public_json,
    normalize_git_url,
    normalize_public_https_url,
    validate_git_sha,
)
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_skills import read_project_skills


class _Response:
    def __init__(self, body: bytes, url: str = "https://cdn.example.com/marketplace.json") -> None:
        self.body = body
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, limit: int) -> bytes:
        return self.body[:limit]

    def geturl(self) -> str:
        return self.url


def write_remote_marketplace(root: Path, source: dict[str, str]) -> Path:
    marketplace = root / "remote-catalog"
    (marketplace / ".claude-plugin").mkdir(parents=True)
    (marketplace / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps(
            {
                "name": "remote-tools",
                "description": "Remote coding extensions",
                "owner": {"name": "Remote Team"},
                "plugins": [
                    {
                        "name": "demo-plugin",
                        "source": source,
                        "description": "Remote demo plugin",
                        "version": "1.2.3",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return marketplace


class RemoteSourceSafetyTests(IsolatedUserHomeTestCase):
    def test_remote_urls_require_public_credential_free_https(self) -> None:
        self.assertEqual(
            normalize_public_https_url("https://example.com/catalog.git", label="source"),
            "https://example.com/catalog.git",
        )
        for value in (
            "http://example.com/catalog.git",
            "https://user:secret@example.com/catalog.git",
            "file:///tmp/catalog",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_public_https_url(value, label="source")
        with self.assertRaisesRegex(ValueError, "40 or 64"):
            validate_git_sha("deadbee")

    def test_git_urls_accept_bounded_ssh_syntax(self) -> None:
        self.assertEqual(
            normalize_git_url("git@gitlab.example.com:team/plugins.git"),
            "git@gitlab.example.com:team/plugins.git",
        )
        self.assertEqual(
            normalize_git_url("ssh://git@gitlab.example.com:2222/team/plugins.git"),
            "ssh://git@gitlab.example.com:2222/team/plugins.git",
        )
        for value in (
            "ssh://git:secret@gitlab.example.com/team/plugins.git",
            "ssh://git@gitlab.example.com/team/../private.git",
            "git@gitlab.example.com:team/../../private.git",
            "ssh://git@gitlab.example.com//team/plugins.git",
            "-oProxyCommand=bad@gitlab.example.com:team/plugins.git",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_git_url(value)

    def test_git_fetch_is_noninteractive_bounded_and_disables_redirects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-remote-git-") as base:
            destination = Path(base) / "checkout"
            calls: list[tuple[list[str], dict[str, str]]] = []

            def run(command, **kwargs):  # type: ignore[no-untyped-def]
                calls.append((list(command), dict(kwargs["env"])))
                if command[1:3] == ["init", "--quiet"]:
                    Path(command[-1]).mkdir()
                return subprocess.CompletedProcess(command, 0, "", "")

            with (
                patch("vibeagent.plugin_remote_sources.validate_scoped_url"),
                patch(
                    "vibeagent.plugin_remote_sources.shutil.which",
                    side_effect=lambda name: f"/usr/bin/{name}",
                ),
                patch("vibeagent.plugin_remote_sources.subprocess.run", side_effect=run),
                patch.dict(
                    "vibeagent.plugin_remote_sources.os.environ",
                    {
                        "GIT_CONFIG_COUNT": "1",
                        "GIT_CONFIG_KEY_0": "core.hooksPath",
                        "GIT_CONFIG_VALUE_0": "/tmp/hooks",
                        "GIT_ASKPASS": "/tmp/untrusted-askpass",
                    },
                    clear=False,
                ),
            ):
                clone_public_git(
                    "https://git.example.com/team/tools.git",
                    destination,
                    ref="v1.2.3",
                )

            self.assertEqual(len(calls), 4)
            fetch = calls[2][0]
            self.assertIn("http.followRedirects=false", fetch)
            self.assertEqual(fetch[-1], "v1.2.3")
            self.assertEqual(calls[0][1]["GIT_TERMINAL_PROMPT"], "0")
            self.assertEqual(calls[0][1]["GIT_LFS_SKIP_SMUDGE"], "1")
            self.assertNotIn("GIT_CONFIG_COUNT", calls[0][1])
            self.assertNotIn("GIT_CONFIG_KEY_0", calls[0][1])
            self.assertEqual(calls[0][1]["GIT_ASKPASS"], "/usr/bin/false")

    def test_git_fetch_rejects_nonpublic_resolution_before_starting_git(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-remote-git-") as base:
            with (
                patch(
                    "vibeagent.plugin_remote_sources.validate_scoped_url",
                    side_effect=UrlSafetyError("private address"),
                ),
                patch("vibeagent.plugin_remote_sources.subprocess.run") as run,
            ):
                with self.assertRaisesRegex(UrlSafetyError, "private address"):
                    clone_public_git(
                        "https://example.com/tools.git",
                        Path(base) / "checkout",
                    )
            run.assert_not_called()

    def test_ssh_fetch_requires_public_host_and_strict_noninteractive_auth(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-remote-ssh-") as base:
            destination = Path(base) / "checkout"
            calls: list[tuple[list[str], dict[str, str]]] = []

            def run(command, **kwargs):  # type: ignore[no-untyped-def]
                calls.append((list(command), dict(kwargs["env"])))
                if command[1:3] == ["init", "--quiet"]:
                    Path(command[-1]).mkdir()
                return subprocess.CompletedProcess(command, 0, "", "")

            with (
                patch("vibeagent.plugin_remote_sources.validate_scoped_url") as validate,
                patch(
                    "vibeagent.plugin_remote_sources.shutil.which",
                    side_effect=lambda name: f"/usr/bin/{name}",
                ),
                patch("vibeagent.plugin_remote_sources.subprocess.run", side_effect=run),
                patch.dict(
                    "vibeagent.plugin_remote_sources.os.environ",
                    {
                        "GIT_SSH_COMMAND": "ssh -oProxyCommand=evil",
                        "SSH_AUTH_SOCK": "/run/user/1000/ssh-agent.sock",
                    },
                    clear=False,
                ),
            ):
                clone_remote_git(
                    "git@gitlab.example.com:team/plugins.git",
                    destination,
                    ref="release-1",
                )

            validate.assert_called_once_with(
                "https://gitlab.example.com:22/",
                "public",
                require_https=True,
            )
            self.assertEqual(len(calls), 4)
            fetch = calls[2][0]
            self.assertNotIn("http.followRedirects=false", fetch)
            ssh_command = calls[0][1]["GIT_SSH_COMMAND"]
            self.assertIn("-oBatchMode=yes", ssh_command)
            self.assertIn("-oStrictHostKeyChecking=yes", ssh_command)
            self.assertIn("-oPasswordAuthentication=no", ssh_command)
            self.assertIn("-F /dev/null", ssh_command)
            self.assertIn("-oProxyCommand=none", ssh_command)
            self.assertIn("-oPermitLocalCommand=no", ssh_command)
            self.assertNotIn("ProxyCommand=evil", ssh_command)
            self.assertEqual(calls[0][1]["GIT_SSH_VARIANT"], "ssh")
            self.assertEqual(calls[0][1]["SSH_AUTH_SOCK"], "/run/user/1000/ssh-agent.sock")

    def test_ssh_fetch_rejects_nonpublic_resolution_before_starting_git(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-remote-ssh-") as base:
            with (
                patch(
                    "vibeagent.plugin_remote_sources.validate_scoped_url",
                    side_effect=UrlSafetyError("private address"),
                ),
                patch("vibeagent.plugin_remote_sources.subprocess.run") as run,
            ):
                with self.assertRaisesRegex(UrlSafetyError, "private address"):
                    clone_remote_git(
                        "git@internal.example.com:team/plugins.git",
                        Path(base) / "checkout",
                    )
            run.assert_not_called()

    def test_ssh_host_key_failure_removes_partial_checkout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-remote-ssh-") as base:
            destination = Path(base) / "checkout"
            call_count = 0

            def run(command, **_kwargs):  # type: ignore[no-untyped-def]
                nonlocal call_count
                call_count += 1
                if command[1:3] == ["init", "--quiet"]:
                    destination.mkdir()
                if "fetch" in command:
                    return subprocess.CompletedProcess(
                        command,
                        128,
                        "",
                        "Host key verification failed.",
                    )
                return subprocess.CompletedProcess(command, 0, "", "")

            with (
                patch("vibeagent.plugin_remote_sources.validate_scoped_url"),
                patch(
                    "vibeagent.plugin_remote_sources.shutil.which",
                    side_effect=lambda name: f"/usr/bin/{name}",
                ),
                patch("vibeagent.plugin_remote_sources.subprocess.run", side_effect=run),
            ):
                with self.assertRaisesRegex(ValueError, "Host key verification failed"):
                    clone_remote_git(
                        "git@gitlab.example.com:team/plugins.git",
                        destination,
                    )

            self.assertEqual(call_count, 3)
            self.assertFalse(destination.exists())

    def test_json_download_is_bounded_and_validated_before_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-remote-json-") as base:
            destination = Path(base) / "marketplace.json"
            response = _Response(b'{"name":"catalog"}')
            with patch(
                "vibeagent.plugin_remote_sources.open_scoped_url",
                return_value=response,
            ) as open_url:
                final_url = download_public_json(
                    "https://example.com/marketplace.json",
                    destination,
                )
            self.assertEqual(final_url, "https://cdn.example.com/marketplace.json")
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8"))["name"], "catalog")
            self.assertTrue(open_url.call_args.kwargs["require_https"])


class RemoteMarketplaceTests(IsolatedUserHomeTestCase):
    def test_ssh_marketplace_add_and_update_preserve_source_and_ref(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-remote-market-") as base:
            root = Path(base)
            catalog = write_demo_marketplace(root)

            def clone(_url: str, destination: Path, **_kwargs: object) -> None:
                copy_plugin_tree(catalog, destination)

            with patch(
                "vibeagent.marketplace_acquisition.clone_remote_git",
                side_effect=clone,
            ) as fetch:
                added = add_marketplace(
                    root,
                    "git@gitlab.example.com:team/catalog.git#release-1",
                )
                updated = update_marketplace(root, "team-tools")

            self.assertEqual(added.source_kind, "git")
            self.assertEqual(added.source, "git@gitlab.example.com:team/catalog.git")
            self.assertEqual(added.source_ref, "release-1")
            self.assertEqual(updated.source, added.source)
            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(fetch.call_args.kwargs["ref"], "release-1")

            with self.assertRaisesRegex(ValueError, "unsupported components"):
                add_marketplace(root, "git@gitlab.example.com:../private.git")

    def test_ssh_plugin_source_installs_through_existing_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-remote-market-") as base:
            root = Path(base)
            catalog = write_remote_marketplace(
                root,
                {
                    "source": "url",
                    "url": "ssh://git@gitlab.example.com:2222/team/demo-plugin.git",
                    "ref": "v1.2.3",
                },
            )
            add_marketplace(root, "remote-catalog")
            parsed = read_marketplace_manifest(catalog).plugins[0]
            self.assertEqual(
                parsed.url,
                "ssh://git@gitlab.example.com:2222/team/demo-plugin.git",
            )
            remote_plugin = write_demo_plugin(root / "remote-plugin-source")

            def clone(url: str, destination: Path, **kwargs: object) -> None:
                self.assertEqual(url, parsed.url)
                self.assertEqual(kwargs["ref"], "v1.2.3")
                copy_plugin_tree(remote_plugin, destination)

            with patch(
                "vibeagent.marketplace_plugin_fetch.clone_remote_git",
                side_effect=clone,
            ):
                installed = install_marketplace_plugin(root, "demo-plugin@remote-tools")

            self.assertEqual(installed.name, "demo-plugin")
            workspace = create_run_workspace(root, "ssh-plugin")
            self.assertIn(
                "demo-plugin:review",
                [item["name"] for item in read_project_skills(workspace)["skills"]],
            )

    def test_github_marketplace_add_and_update_preserve_remote_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-remote-market-") as base:
            root = Path(base)
            catalog = write_demo_marketplace(root)

            def clone(_url: str, destination: Path, **_kwargs: object) -> None:
                copy_plugin_tree(catalog, destination)

            with patch("vibeagent.marketplace_acquisition.clone_remote_git", side_effect=clone) as fetch:
                added = add_marketplace(root, "acme/team-catalog#v1")
                self.assertEqual(added.source_kind, "github")
                self.assertEqual(added.source, "acme/team-catalog")
                self.assertEqual(added.source_ref, "v1")

                manifest_path = catalog / ".claude-plugin" / "marketplace.json"
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                payload["description"] = "Refreshed remote catalog"
                manifest_path.write_text(json.dumps(payload), encoding="utf-8")
                updated = update_marketplace(root, "team-tools")

            self.assertEqual(updated.description, "Refreshed remote catalog")
            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(list_installed_marketplaces(root)[0].source_kind, "github")

    def test_direct_https_catalog_installs_github_plugin_into_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-remote-market-") as base:
            root = Path(base)
            catalog = write_remote_marketplace(
                root,
                {"source": "github", "repo": "acme/demo-plugin", "ref": "v1.2.3"},
            )
            remote_plugin = write_demo_plugin(root / "remote-plugin-source")
            manifest_bytes = (catalog / ".claude-plugin" / "marketplace.json").read_bytes()

            def download(_url: str, destination: Path) -> str:
                destination.parent.mkdir(parents=True)
                destination.write_bytes(manifest_bytes)
                return "https://cdn.example.com/marketplace.json"

            def clone(_url: str, destination: Path, **_kwargs: object) -> None:
                copy_plugin_tree(remote_plugin, destination)

            with patch("vibeagent.marketplace_acquisition.download_public_json", side_effect=download):
                marketplace = add_marketplace(root, "https://example.com/marketplace.json")
            self.assertEqual(marketplace.source_kind, "http")
            cached = read_installed_marketplace_manifest(root, "remote-tools")
            self.assertEqual(cached.plugins[0].source_kind, "github")
            self.assertIsNone(cached.plugins[0].path)

            with patch("vibeagent.marketplace_plugin_fetch.clone_remote_git", side_effect=clone) as fetch:
                installed = install_marketplace_plugin(root, "demo-plugin@remote-tools")

            self.assertEqual(installed.marketplace, "remote-tools")
            self.assertEqual(fetch.call_args.kwargs["ref"], "v1.2.3")
            workspace = create_run_workspace(root, run_id="remote-plugin")
            self.assertIn(
                "demo-plugin:review",
                [item["name"] for item in read_project_skills(workspace)["skills"]],
            )

    def test_git_subdir_source_is_bounded_and_selected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-remote-market-") as base:
            root = Path(base)
            catalog = write_remote_marketplace(
                root,
                {
                    "source": "git-subdir",
                    "url": "https://git.example.com/mono.git",
                    "path": "packages/demo",
                    "sha": "0123456789abcdef0123456789abcdef01234567",
                },
            )
            add_local = add_marketplace(root, "remote-catalog")
            self.assertEqual(add_local.source_kind, "local")
            remote_plugin = write_demo_plugin(root / "monorepo-source")

            def clone(_url: str, destination: Path, **_kwargs: object) -> None:
                (destination / "packages").mkdir(parents=True)
                copy_plugin_tree(remote_plugin, destination / "packages" / "demo")

            with patch("vibeagent.marketplace_plugin_fetch.clone_remote_git", side_effect=clone) as fetch:
                installed = install_marketplace_plugin(root, "demo-plugin@remote-tools")

            self.assertEqual(installed.name, "demo-plugin")
            self.assertEqual(
                fetch.call_args.kwargs["sha"],
                "0123456789abcdef0123456789abcdef01234567",
            )

    def test_remote_manifest_rejects_insecure_and_escaping_sources(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-remote-market-") as base:
            root = Path(base)
            catalog = write_remote_marketplace(
                root,
                {"source": "url", "url": "http://example.com/plugin.git"},
            )
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                read_marketplace_manifest(catalog)

            manifest_path = catalog / ".claude-plugin" / "marketplace.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["plugins"][0]["source"] = {
                "source": "git-subdir",
                "url": "https://example.com/plugin.git",
                "path": "../secret",
            }
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stay inside"):
                read_marketplace_manifest(catalog)

            payload["plugins"][0]["source"] = {
                "source": "url",
                "url": "ssh://git:secret@gitlab.example.com/team/plugin.git",
            }
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must not include a password"):
                read_marketplace_manifest(catalog)

    def test_marketplace_removed_during_fetch_cannot_leave_orphan_plugin(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-remote-market-") as base:
            root = Path(base)
            write_remote_marketplace(
                root,
                {"source": "github", "repo": "acme/demo-plugin"},
            )
            add_marketplace(root, "remote-catalog")
            remote_plugin = write_demo_plugin(root / "remote-plugin-source")

            def clone(_url: str, destination: Path, **_kwargs: object) -> None:
                remove_marketplace(root, "remote-tools")
                copy_plugin_tree(remote_plugin, destination)

            with patch("vibeagent.marketplace_plugin_fetch.clone_remote_git", side_effect=clone):
                with self.assertRaisesRegex(ValueError, "removed during plugin installation"):
                    install_marketplace_plugin(root, "demo-plugin@remote-tools")

            self.assertEqual(list_installed_marketplaces(root), [])
            self.assertFalse((root / ".vibeagent/plugins/cache/demo-plugin").exists())
            fetch_root = root / ".vibeagent/plugins/fetches"
            self.assertEqual(list(fetch_root.iterdir()), [])

    def test_remote_plugin_manifest_identity_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-remote-market-") as base:
            root = Path(base)
            write_remote_marketplace(
                root,
                {"source": "github", "repo": "acme/demo-plugin"},
            )
            add_marketplace(root, "remote-catalog")
            remote_plugin = write_demo_plugin(root / "remote-plugin-source")
            plugin_manifest = remote_plugin / ".claude-plugin" / "plugin.json"
            payload = json.loads(plugin_manifest.read_text(encoding="utf-8"))
            payload["name"] = "different-plugin"
            plugin_manifest.write_text(json.dumps(payload), encoding="utf-8")

            def clone(_url: str, destination: Path, **_kwargs: object) -> None:
                copy_plugin_tree(remote_plugin, destination)

            with patch("vibeagent.marketplace_plugin_fetch.clone_remote_git", side_effect=clone):
                with self.assertRaisesRegex(ValueError, "does not match marketplace entry"):
                    install_marketplace_plugin(root, "demo-plugin@remote-tools")

            self.assertFalse((root / ".vibeagent/plugins/cache/demo-plugin").exists())


if __name__ == "__main__":
    unittest.main()
