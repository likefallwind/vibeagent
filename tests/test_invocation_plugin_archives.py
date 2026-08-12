from __future__ import annotations

from pathlib import Path
import stat
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import warnings
import zipfile

from tests.test_plugins import write_demo_plugin
from tests.user_home_test_case import IsolatedUserHomeTestCase
from vibeagent.invocation_plugins import resolve_invocation_plugin_dirs
from vibeagent.plugin_manifest import read_plugin_manifest


def write_plugin_zip(plugin: Path, archive: Path, *, wrapped: bool) -> Path:
    prefix = plugin.name if wrapped else ""
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(plugin.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(plugin).as_posix()
            output.write(path, f"{prefix}/{relative}" if prefix else relative)
    return archive


class InvocationPluginArchiveTests(IsolatedUserHomeTestCase):
    def test_loads_root_and_wrapped_plugins_from_private_cache(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)
            plugin = write_demo_plugin(root)
            root_zip = write_plugin_zip(plugin, root / "root-plugin.zip", wrapped=False)
            wrapped_zip = write_plugin_zip(plugin, root / "wrapped-plugin.zip", wrapped=True)

            root_resolved = resolve_invocation_plugin_dirs(
                [root_zip.name, root_zip.name],
                invocation_root=root,
            )
            wrapped_resolved = resolve_invocation_plugin_dirs(
                [wrapped_zip.as_posix()],
                invocation_root=root,
            )

        self.assertEqual(len(root_resolved), 1)
        self.assertEqual(root_resolved[0].name, "plugin")
        self.assertEqual(wrapped_resolved[0].name, "plugin")
        self.assertIn("invocation-plugin-cache", wrapped_resolved[0].as_posix())

    def test_manifestless_wrapped_zip_preserves_plugin_name(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)
            plugin = root / "bare-plugin"
            plugin.mkdir()
            (plugin / "SKILL.md").write_text(
                "---\ndescription: Bare archive skill\n---\nInspect files.\n",
                encoding="utf-8",
            )
            archive = write_plugin_zip(plugin, root / "renamed.zip", wrapped=True)

            resolved = resolve_invocation_plugin_dirs([str(archive)], invocation_root=root)
            manifest = read_plugin_manifest(resolved[0])

        self.assertEqual(manifest.name, "bare-plugin")
        self.assertEqual(resolved[0].name, "bare-plugin")

    def test_preserves_executable_mode_and_content_snapshots(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)
            plugin = write_demo_plugin(root)
            executable = plugin / "bin/check"
            executable.chmod(0o755)
            archive = write_plugin_zip(plugin, root / "demo-plugin.zip", wrapped=False)

            first = resolve_invocation_plugin_dirs([str(archive)], invocation_root=root)[0]
            first_digest_root = first.parent
            self.assertTrue((first / "bin/check").stat().st_mode & stat.S_IXUSR)
            (plugin / "commands/fix.md").write_text(
                "---\ndescription: Changed\n---\nCHANGED $ARGUMENTS\n",
                encoding="utf-8",
            )
            write_plugin_zip(plugin, archive, wrapped=False)
            second = resolve_invocation_plugin_dirs([str(archive)], invocation_root=root)[0]

        self.assertNotEqual(first_digest_root, second.parent)
        self.assertIn("CHANGED", (second / "commands/fix.md").read_text(encoding="utf-8"))

    def test_rejects_traversal_duplicates_symlinks_and_limits(self) -> None:
        cases: list[tuple[str, int | None, str]] = []
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)

            traversal = root / "traversal.zip"
            with zipfile.ZipFile(traversal, "w") as archive:
                archive.writestr("../escape", "bad")
            cases.append((str(traversal), None, "path is unsafe"))

            duplicate = root / "duplicate.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(duplicate, "w") as archive:
                    archive.writestr("demo-plugin/SKILL.md", "one")
                    archive.writestr("demo-plugin/SKILL.md", "two")
            cases.append((str(duplicate), None, "duplicate path"))

            linked = root / "linked.zip"
            link_info = zipfile.ZipInfo("demo-plugin/SKILL.md")
            link_info.create_system = 3
            link_info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(linked, "w") as archive:
                archive.writestr(link_info, "../outside")
            cases.append((str(linked), None, "unsupported entry"))

            oversized_plugin = write_demo_plugin(root)
            oversized = write_plugin_zip(
                oversized_plugin,
                root / "oversized.zip",
                wrapped=False,
            )
            cases.append((str(oversized), 1, "expanded bytes"))

            for archive_path, byte_limit, expected in cases:
                with self.subTest(archive=Path(archive_path).name):
                    limit = byte_limit if byte_limit is not None else 100_000_000
                    with (
                        patch(
                            "vibeagent.invocation_plugin_archives.MAX_PLUGIN_TOTAL_BYTES",
                            limit,
                        ),
                        self.assertRaisesRegex(ValueError, expected),
                    ):
                        resolve_invocation_plugin_dirs([archive_path], invocation_root=root)

    def test_rejects_tampered_cache_symlink(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)
            plugin = write_demo_plugin(root)
            archive = write_plugin_zip(plugin, root / "demo-plugin.zip", wrapped=False)
            resolved = resolve_invocation_plugin_dirs([str(archive)], invocation_root=root)[0]
            (resolved / "tampered").symlink_to(root)

            with self.assertRaisesRegex(ValueError, "cache contains a symbolic link"):
                resolve_invocation_plugin_dirs([str(archive)], invocation_root=root)

    def test_rejects_tampered_cache_content_and_mode(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)
            plugin = write_demo_plugin(root)
            archive = write_plugin_zip(plugin, root / "demo-plugin.zip", wrapped=False)
            resolved = resolve_invocation_plugin_dirs([str(archive)], invocation_root=root)[0]
            command = resolved / "commands/fix.md"
            command.write_text("tampered", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "content does not match archive"):
                resolve_invocation_plugin_dirs([str(archive)], invocation_root=root)

            command.write_bytes((plugin / "commands/fix.md").read_bytes())
            command.chmod(0o600 if command.stat().st_mode & 0o777 != 0o600 else 0o644)
            with self.assertRaisesRegex(ValueError, "mode does not match archive"):
                resolve_invocation_plugin_dirs([str(archive)], invocation_root=root)


if __name__ == "__main__":
    unittest.main()
