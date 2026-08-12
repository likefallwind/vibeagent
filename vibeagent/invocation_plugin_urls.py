from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import socket
import urllib.error
import urllib.request
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from .invocation_plugin_archives import (
    MAX_PLUGIN_ARCHIVE_BYTES,
    materialize_invocation_plugin_archive,
)
from .network_url_safety import UrlSafetyError, open_scoped_url
from .plugin_manifest import PLUGIN_NAME_PATTERN
from .plugin_remote_sources import normalize_public_https_url
from .user_paths import user_home


MAX_INVOCATION_PLUGIN_URL_CHARS = 4_096
PLUGIN_URL_TIMEOUT_SECONDS = 60


def parse_invocation_plugin_urls(values: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    urls: list[str] = []
    for value in values or ():
        selected = value.split()
        if not selected:
            raise ValueError("--plugin-url cannot be empty.")
        urls.extend(selected)
    return tuple(urls)


def materialize_invocation_plugin_url(value: str) -> Path:
    url, plugin_name = _normalize_plugin_url(value)
    download_root = _invocation_download_root()
    archive_path = download_root / f".{plugin_name}.download-{uuid4().hex[:8]}.zip"
    created = False
    try:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/zip, application/octet-stream",
                "Accept-Encoding": "identity",
                "User-Agent": "vibeagent-invocation-plugin/1.0",
            },
        )
        try:
            with open_scoped_url(
                request,
                timeout=PLUGIN_URL_TIMEOUT_SECONDS,
                scope="public",
                require_https=True,
                use_environment_proxy=False,
            ) as response:
                _validate_response_headers(response)
                with archive_path.open("xb") as output:
                    created = True
                    os.chmod(archive_path, 0o600)
                    total = 0
                    while chunk := response.read(64 * 1024):
                        total += len(chunk)
                        if total > MAX_PLUGIN_ARCHIVE_BYTES:
                            raise ValueError(
                                f"Remote plugin ZIP exceeds {MAX_PLUGIN_ARCHIVE_BYTES} bytes."
                            )
                        output.write(chunk)
        except (
            UrlSafetyError,
            urllib.error.URLError,
            TimeoutError,
            socket.timeout,
            OSError,
        ) as error:
            raise ValueError(f"Could not download plugin URL: {error}") from error
        if not created or archive_path.stat().st_size == 0:
            raise ValueError("Remote plugin ZIP is empty.")
        return materialize_invocation_plugin_archive(
            archive_path,
            manifestless_name=plugin_name,
        )
    finally:
        if created:
            archive_path.unlink(missing_ok=True)


def _normalize_plugin_url(value: str) -> tuple[str, str]:
    if not value or len(value) > MAX_INVOCATION_PLUGIN_URL_CHARS or any(char.isspace() for char in value):
        raise ValueError(
            f"--plugin-url must contain 1-{MAX_INVOCATION_PLUGIN_URL_CHARS} non-whitespace characters."
        )
    url = normalize_public_https_url(value, label="Plugin URL")
    name = PurePosixPath(unquote(urlsplit(url).path)).name
    if not name.lower().endswith(".zip"):
        raise ValueError("--plugin-url must reference a .zip archive path.")
    plugin_name = name[:-4]
    if not PLUGIN_NAME_PATTERN.fullmatch(plugin_name):
        raise ValueError(
            "--plugin-url ZIP filename must use 1-64 lowercase letters, digits, or hyphens."
        )
    return url, plugin_name


def _validate_response_headers(response: object) -> None:
    headers = getattr(response, "headers", None)
    if headers is None:
        return
    encoding = str(headers.get("Content-Encoding") or "").strip().lower()
    if encoding not in {"", "identity"}:
        raise ValueError(f"Remote plugin ZIP uses unsupported content encoding: {encoding}")
    raw_length = headers.get("Content-Length")
    if raw_length is None:
        return
    try:
        length = int(raw_length)
    except (TypeError, ValueError) as error:
        raise ValueError("Remote plugin ZIP has an invalid Content-Length header.") from error
    if length < 0 or length > MAX_PLUGIN_ARCHIVE_BYTES:
        raise ValueError(
            f"Remote plugin ZIP Content-Length exceeds {MAX_PLUGIN_ARCHIVE_BYTES} bytes."
        )


def _invocation_download_root() -> Path:
    runtime = user_home() / ".vibeagent"
    root = runtime / "invocation-plugin-downloads"
    for path in (runtime, root):
        if path.is_symlink():
            raise ValueError(f"Invocation plugin download path must not be a symbolic link: {path}")
        path.mkdir(mode=0o700, exist_ok=True)
        if not path.is_dir():
            raise ValueError(f"Invocation plugin download path must be a directory: {path}")
        os.chmod(path, 0o700)
    return root


__all__ = [
    "MAX_INVOCATION_PLUGIN_URL_CHARS",
    "PLUGIN_URL_TIMEOUT_SECONDS",
    "materialize_invocation_plugin_url",
    "parse_invocation_plugin_urls",
]
