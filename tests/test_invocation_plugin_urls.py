from __future__ import annotations

from contextlib import redirect_stdout
import io
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
import urllib.error
import zipfile

from tests.test_invocation_plugin_archives import write_plugin_zip
from tests.test_plugins import write_demo_plugin
from tests.user_home_test_case import IsolatedUserHomeTestCase
from vibeagent.agent_result import AgentResult
from vibeagent.cli import main
from vibeagent.invocation_plugin_urls import (
    materialize_invocation_plugin_url,
    parse_invocation_plugin_urls,
)
from vibeagent.invocation_plugins import resolve_invocation_plugin_dirs
from vibeagent.plugin_manifest import read_plugin_manifest


class _Response:
    def __init__(self, body: bytes, *, headers: dict[str, str] | None = None) -> None:
        self._stream = BytesIO(body)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, size: int) -> bytes:
        return self._stream.read(size)


def _plugin_zip_bytes(root: Path) -> bytes:
    plugin = write_demo_plugin(root)
    archive = write_plugin_zip(plugin, root / "demo-plugin.zip", wrapped=True)
    return archive.read_bytes()


class InvocationPluginUrlTests(IsolatedUserHomeTestCase):
    def test_cli_materializes_url_before_persistent_one_shot(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-plugin-url-") as temporary:
            root = Path(temporary)
            plugin = write_demo_plugin(root)
            result = AgentResult(True, "done", root, "run-url", 1, [], [])
            run_agent = Mock(return_value=result)
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                patch(
                    "vibeagent.invocation_plugins.materialize_invocation_plugin_url",
                    return_value=plugin,
                ) as materialize,
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        root.as_posix(),
                        "--plugin-url",
                        "https://plugins.example.com/demo-plugin.zip",
                        "inspect",
                    ]
                )

        self.assertEqual(exit_code, 0)
        materialize.assert_called_once_with(
            "https://plugins.example.com/demo-plugin.zip"
        )
        self.assertEqual(
            run_agent.call_args.kwargs["invocation_plugin_dirs"],
            (plugin.resolve(),),
        )

    def test_cli_url_failure_stops_before_provider_creation(self) -> None:
        client = Mock()
        with (
            patch("vibeagent.cli.create_chat_client", client),
            patch(
                "vibeagent.invocation_plugins.materialize_invocation_plugin_url",
                side_effect=ValueError("remote archive invalid"),
            ),
            redirect_stdout(io.StringIO()),
        ):
            exit_code = main(
                [
                    "--plugin-url",
                    "https://plugins.example.com/demo-plugin.zip",
                    "inspect",
                ]
            )

        self.assertEqual(exit_code, 2)
        client.assert_not_called()

    def test_parses_repeated_and_space_separated_url_values(self) -> None:
        self.assertEqual(
            parse_invocation_plugin_urls(
                [
                    "https://one.example/a.zip https://two.example/b.zip",
                    "https://three.example/c.zip",
                ]
            ),
            (
                "https://one.example/a.zip",
                "https://two.example/b.zip",
                "https://three.example/c.zip",
            ),
        )
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            parse_invocation_plugin_urls(["  "])

    def test_downloads_public_https_without_proxy_and_removes_temporary_archive(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-plugin-url-") as temporary:
            root = Path(temporary)
            body = _plugin_zip_bytes(root)
            response = _Response(body, headers={"Content-Length": str(len(body))})
            with patch(
                "vibeagent.invocation_plugin_urls.open_scoped_url",
                return_value=response,
            ) as open_url:
                plugin_root = materialize_invocation_plugin_url(
                    "https://plugins.example.com/demo-plugin.zip?build=42"
                )

        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, "https://plugins.example.com/demo-plugin.zip?build=42")
        self.assertEqual(open_url.call_args.kwargs["scope"], "public")
        self.assertTrue(open_url.call_args.kwargs["require_https"])
        self.assertFalse(open_url.call_args.kwargs["use_environment_proxy"])
        self.assertEqual(read_plugin_manifest(plugin_root).name, "demo-plugin")
        downloads = Path(self._user_home.name) / ".vibeagent/invocation-plugin-downloads"
        self.assertEqual(list(downloads.iterdir()), [])

    def test_remote_manifestless_root_uses_url_zip_filename(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-plugin-url-") as temporary:
            root = Path(temporary)
            archive = root / "source.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr(
                    "SKILL.md",
                    "---\ndescription: Remote bare skill\n---\nInspect files.\n",
                )
            with patch(
                "vibeagent.invocation_plugin_urls.open_scoped_url",
                return_value=_Response(archive.read_bytes()),
            ):
                plugin_root = materialize_invocation_plugin_url(
                    "https://plugins.example.com/bare-plugin.zip"
                )

        self.assertEqual(read_plugin_manifest(plugin_root).name, "bare-plugin")

    def test_rejects_unsafe_urls_before_network_access(self) -> None:
        invalid = (
            "http://plugins.example.com/demo-plugin.zip",
            "https://user:secret@plugins.example.com/demo-plugin.zip",
            "https://plugins.example.com/demo-plugin.tar.gz",
            "https://plugins.example.com/Bad_Name.zip",
            "https://plugins.example.com/demo-plugin.zip#fragment",
        )
        with patch("vibeagent.invocation_plugin_urls.open_scoped_url") as open_url:
            for value in invalid:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    materialize_invocation_plugin_url(value)
        open_url.assert_not_called()

    def test_rejects_encoded_oversized_and_failed_downloads_without_residue(self) -> None:
        cases = (
            (_Response(b"bad", headers={"Content-Encoding": "gzip"}), None, "content encoding"),
            (_Response(b"01234567890"), 10, "exceeds 10 bytes"),
            (urllib.error.URLError("offline"), None, "Could not download"),
        )
        for response, byte_limit, expected in cases:
            with self.subTest(expected=expected):
                patches = [
                    patch(
                        "vibeagent.invocation_plugin_urls.open_scoped_url",
                        side_effect=response if isinstance(response, Exception) else None,
                        return_value=None if isinstance(response, Exception) else response,
                    )
                ]
                if byte_limit is not None:
                    patches.append(
                        patch(
                            "vibeagent.invocation_plugin_urls.MAX_PLUGIN_ARCHIVE_BYTES",
                            byte_limit,
                        )
                    )
                with patches[0]:
                    if len(patches) == 1:
                        with self.assertRaisesRegex(ValueError, expected):
                            materialize_invocation_plugin_url(
                                "https://plugins.example.com/demo-plugin.zip"
                            )
                    else:
                        with patches[1], self.assertRaisesRegex(ValueError, expected):
                            materialize_invocation_plugin_url(
                                "https://plugins.example.com/demo-plugin.zip"
                            )
        downloads = Path(self._user_home.name) / ".vibeagent/invocation-plugin-downloads"
        self.assertEqual(list(downloads.iterdir()), [])

    def test_resolver_combines_local_and_remote_plugins_and_rejects_name_conflicts(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-plugin-url-") as temporary:
            root = Path(temporary)
            local = write_demo_plugin(root)
            remote = root / "remote-plugin"
            remote.mkdir()
            (remote / ".claude-plugin").mkdir()
            (remote / ".claude-plugin/plugin.json").write_text(
                '{"name":"remote-plugin"}',
                encoding="utf-8",
            )
            with patch(
                "vibeagent.invocation_plugins.materialize_invocation_plugin_url",
                return_value=remote,
            ) as materialize:
                resolved = resolve_invocation_plugin_dirs(
                    [str(local)],
                    invocation_root=root,
                    plugin_urls=[
                        "https://plugins.example.com/remote-plugin.zip "
                        "https://plugins.example.com/remote-plugin.zip"
                    ],
                )
                resolved_names = [read_plugin_manifest(path).name for path in resolved]

            conflict = root / "conflict"
            conflict.mkdir()
            (conflict / ".claude-plugin").mkdir()
            (conflict / ".claude-plugin/plugin.json").write_text(
                '{"name":"demo-plugin"}',
                encoding="utf-8",
            )
            with (
                patch(
                    "vibeagent.invocation_plugins.materialize_invocation_plugin_url",
                    return_value=conflict,
                ),
                self.assertRaisesRegex(ValueError, "duplicate plugin name demo-plugin"),
            ):
                resolve_invocation_plugin_dirs(
                    [str(local)],
                    invocation_root=root,
                    plugin_urls=["https://plugins.example.com/demo-plugin.zip"],
                )

        self.assertEqual(resolved_names, ["demo-plugin", "remote-plugin"])
        materialize.assert_called_once_with(
            "https://plugins.example.com/remote-plugin.zip"
        )

    def test_combined_plugin_limit_fails_before_download(self) -> None:
        urls = [f"https://plugins.example.com/plugin-{index}.zip" for index in range(21)]
        with patch("vibeagent.invocation_plugins.materialize_invocation_plugin_url") as materialize:
            with self.assertRaisesRegex(ValueError, "at most 20 plugins combined"):
                resolve_invocation_plugin_dirs(None, invocation_root=Path.cwd(), plugin_urls=urls)
        materialize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
