from __future__ import annotations

import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from vibeagent.startup_file_download import DOWNLOAD_CHUNK_BYTES
from vibeagent import startup_file_download as download_module
from vibeagent.startup_file_resources import (
    DownloadedFileResource,
    StartupFileResourceError,
    download_startup_file_resources,
    parse_startup_file_resources,
)


class FakeResponse:
    def __init__(self, content: bytes, headers: dict[str, str] | None = None) -> None:
        self._content = io.BytesIO(content)
        self.headers = headers or {}
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return self._content.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        self._content.close()


def anthropic_env(**updates: str) -> dict[str, str]:
    env = {
        "VIBEAGENT_PROVIDER": "anthropic",
        "ANTHROPIC_API_KEY": "test-secret",
        "ANTHROPIC_BASE_URL": "https://api.example.test",
    }
    env.update(updates)
    return env


class StartupFileResourceTests(unittest.TestCase):
    def test_parses_bounded_project_relative_destinations(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            resources = parse_startup_file_resources(
                ["file_alpha:fixtures/input.bin", "file_beta:notes.txt"],
                root,
            )

        self.assertEqual(
            [(item.file_id, item.relative_path) for item in resources],
            [("file_alpha", "fixtures/input.bin"), ("file_beta", "notes.txt")],
        )

    def test_rejects_malformed_escaping_protected_duplicate_and_existing_destinations(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            (root / "existing.txt").write_text("kept", encoding="utf-8")
            invalid = (
                ["missing-separator"],
                ["bad-id:file.txt"],
                ["file_alpha:../outside.txt"],
                ["file_alpha:.git/config"],
                ["file_alpha:.env"],
                ["file_alpha:same.txt", "file_beta:same.txt"],
                ["file_alpha:existing.txt"],
            )
            for specs in invalid:
                with self.subTest(specs=specs), self.assertRaises(StartupFileResourceError):
                    parse_startup_file_resources(specs, root)

    def test_rejects_symbolic_link_components(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symbolic links are unavailable")
        with tempfile.TemporaryDirectory() as base, tempfile.TemporaryDirectory() as outside:
            root = Path(base)
            (root / "linked").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(StartupFileResourceError, "escapes|symbolic link"):
                parse_startup_file_resources(["file_alpha:linked/input.bin"], root)

    def test_streams_with_files_api_headers_and_private_atomic_output(self) -> None:
        content = b"a" * (DOWNLOAD_CHUNK_BYTES * 2 + 17)
        response = FakeResponse(content, {"Content-Length": str(len(content))})
        calls = []

        def open_request(request, timeout):
            calls.append((request, timeout))
            return response

        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            downloaded = download_startup_file_resources(
                ["file_alpha:fixtures/input.bin"],
                root,
                anthropic_env(),
                open_request=open_request,
            )
            target = root / "fixtures" / "input.bin"
            output = target.read_bytes()
            mode = target.stat().st_mode & 0o777
            leftovers = list(root.rglob(".vibeagent-file-*"))

        self.assertEqual(output, content)
        self.assertEqual(mode, 0o600)
        self.assertEqual(leftovers, [])
        self.assertEqual(downloaded[0].size_bytes, len(content))
        request, timeout = calls[0]
        self.assertEqual(request.full_url, "https://api.example.test/v1/files/file_alpha/content")
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("X-api-key"), "test-secret")
        self.assertEqual(request.get_header("Anthropic-beta"), "files-api-2025-04-14")
        self.assertEqual(request.get_header("Anthropic-version"), "2023-06-01")
        self.assertEqual(timeout, 120.0)
        self.assertLessEqual(max(response.read_sizes), DOWNLOAD_CHUNK_BYTES)

    def test_default_transport_installs_no_redirect_handler(self) -> None:
        handlers = []

        class Opener:
            def open(self, _request, *, timeout):
                self.timeout = timeout
                return FakeResponse(b"content")

        opener = Opener()

        def build_opener(*values):
            handlers.extend(values)
            return opener

        with tempfile.TemporaryDirectory() as base, patch.object(
            download_module, "build_opener", side_effect=build_opener
        ):
            download_startup_file_resources(
                ["file_alpha:input.bin"], base, anthropic_env()
            )

        self.assertEqual(len(handlers), 1)
        self.assertIsNone(
            handlers[0].redirect_request(None, None, 302, "Found", {}, "https://other.test")
        )
        self.assertEqual(opener.timeout, 120.0)

    def test_rejects_other_providers_missing_keys_and_auth_tokens_before_network(self) -> None:
        called = False

        def open_request(_request, _timeout):
            nonlocal called
            called = True
            return FakeResponse(b"")

        environments = (
            {"VIBEAGENT_PROVIDER": "minimax", "MINIMAX_API_KEY": "key"},
            {"VIBEAGENT_PROVIDER": "anthropic"},
            {"VIBEAGENT_PROVIDER": "anthropic", "ANTHROPIC_AUTH_TOKEN": "token"},
        )
        with tempfile.TemporaryDirectory() as base:
            for env in environments:
                with self.subTest(env=env), self.assertRaises(StartupFileResourceError):
                    download_startup_file_resources(
                        ["file_alpha:input.bin"], base, env, open_request=open_request
                    )
        self.assertFalse(called)

    def test_enforces_declared_and_streamed_size_without_retaining_partial_files(self) -> None:
        with tempfile.TemporaryDirectory() as base, patch(
            "vibeagent.startup_file_download.MAX_FILE_BYTES", 5
        ), patch("vibeagent.startup_file_resources.MAX_TOTAL_BYTES", 10):
            for response in (
                FakeResponse(b"", {"Content-Length": "6"}),
                FakeResponse(b"123456"),
            ):
                with self.subTest(headers=response.headers), self.assertRaisesRegex(
                    StartupFileResourceError, "per-file limit"
                ):
                    download_startup_file_resources(
                        ["file_alpha:nested/input.bin"],
                        base,
                        anthropic_env(),
                        open_request=lambda _request, _timeout, value=response: value,
                    )
                self.assertFalse((Path(base) / "nested" / "input.bin").exists())
                self.assertEqual(list(Path(base).rglob(".vibeagent-file-*")), [])

    def test_second_download_failure_rolls_back_staging_and_created_directories(self) -> None:
        calls = 0

        def open_request(request, _timeout):
            nonlocal calls
            calls += 1
            if calls == 1:
                return FakeResponse(b"first")
            raise HTTPError(
                request.full_url,
                403,
                "Forbidden",
                {},
                io.BytesIO(b"test-secret denied"),
            )

        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            with self.assertRaisesRegex(StartupFileResourceError, "HTTP 403") as raised:
                download_startup_file_resources(
                    ["file_alpha:generated/one.bin", "file_beta:generated/two.bin"],
                    root,
                    anthropic_env(),
                    open_request=open_request,
                )
            self.assertNotIn("test-secret", str(raised.exception))
            self.assertFalse((root / "generated").exists())
            self.assertEqual(list(root.rglob(".vibeagent-file-*")), [])

    def test_publish_failure_removes_only_outputs_linked_by_this_operation(self) -> None:
        real_link = os.link
        calls = 0

        def failing_link(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated publish failure")
            return real_link(source, target)

        with tempfile.TemporaryDirectory() as base, patch(
            "vibeagent.startup_file_resources.os.link", side_effect=failing_link
        ):
            root = Path(base)
            with self.assertRaisesRegex(StartupFileResourceError, "publish"):
                download_startup_file_resources(
                    ["file_alpha:one.bin", "file_beta:two.bin"],
                    root,
                    anthropic_env(),
                    open_request=lambda _request, _timeout: FakeResponse(b"content"),
                )
            self.assertFalse((root / "one.bin").exists())
            self.assertFalse((root / "two.bin").exists())
            self.assertEqual(list(root.glob(".vibeagent-file-*")), [])

    def test_cleanup_failure_after_publish_still_rolls_back_linked_output(self) -> None:
        real_unlink = Path.unlink
        injected = False

        def failing_unlink(path, *args, **kwargs):
            nonlocal injected
            if not injected and path.name.startswith(".vibeagent-file-"):
                injected = True
                real_unlink(path, *args, **kwargs)
                raise OSError("simulated cleanup failure")
            return real_unlink(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as base, patch.object(
            Path, "unlink", autospec=True, side_effect=failing_unlink
        ):
            root = Path(base)
            with self.assertRaisesRegex(StartupFileResourceError, "publish"):
                download_startup_file_resources(
                    ["file_alpha:input.bin"],
                    root,
                    anthropic_env(),
                    open_request=lambda _request, _timeout: FakeResponse(b"content"),
                )
            self.assertFalse((root / "input.bin").exists())
            self.assertEqual(list(root.glob(".vibeagent-file-*")), [])


if __name__ == "__main__":
    unittest.main()
