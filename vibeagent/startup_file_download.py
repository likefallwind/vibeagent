from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener


FILES_API_BETA = "files-api-2025-04-14"
MAX_FILE_BYTES = 500 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 64 * 1024
DOWNLOAD_TIMEOUT_SECONDS = 120.0


class StartupFileResourceError(ValueError):
    pass


@dataclass(frozen=True)
class StartupFileResource:
    file_id: str
    relative_path: str
    target: Path


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OpenRequest = Callable[[Request, float], BinaryIO]


def stage_file_resource(
    resource: StartupFileResource,
    *,
    base_url: str,
    api_key: str,
    remaining_bytes: int,
    open_request: OpenRequest | None = None,
) -> tuple[Path, int]:
    if remaining_bytes < 0:
        raise StartupFileResourceError("--file downloads exceed the 1 GiB startup total limit.")
    request = Request(
        f"{base_url.rstrip('/')}/v1/files/{quote(resource.file_id, safe='')}/content",
        headers={
            "Accept": "application/octet-stream",
            "anthropic-beta": FILES_API_BETA,
            "anthropic-version": "2023-06-01",
            "x-api-key": api_key,
        },
        method="GET",
    )
    fd, temporary_name = tempfile.mkstemp(
        prefix=".vibeagent-file-",
        dir=resource.target.parent,
    )
    temporary_path = Path(temporary_name)
    limit = min(MAX_FILE_BYTES, remaining_bytes)
    try:
        with os.fdopen(fd, "wb") as destination:
            try:
                response = (open_request or _open_request)(request, DOWNLOAD_TIMEOUT_SECONDS)
                with response:
                    _validate_content_length(response, resource, limit, remaining_bytes)
                    size_bytes = _copy_bounded(response, destination, resource, limit, remaining_bytes)
            except HTTPError as error:
                raise StartupFileResourceError(
                    _format_http_error(error, resource.file_id, api_key)
                ) from error
            except URLError as error:
                detail = _redact_error_detail(str(error.reason), api_key)
                raise StartupFileResourceError(
                    f"Could not download Anthropic file {resource.file_id}: {detail}"
                ) from error
            destination.flush()
            os.fsync(destination.fileno())
        return temporary_path, size_bytes
    except BaseException:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _validate_content_length(response, resource: StartupFileResource, limit: int, remaining: int) -> None:
    raw_length = response.headers.get("Content-Length")
    if raw_length is None:
        return
    try:
        length = int(raw_length)
    except (TypeError, ValueError) as error:
        raise StartupFileResourceError(
            f"Anthropic file {resource.file_id} returned an invalid Content-Length."
        ) from error
    if length < 0:
        raise StartupFileResourceError(
            f"Anthropic file {resource.file_id} returned an invalid Content-Length."
        )
    _raise_if_too_large(resource.file_id, length, limit, remaining)


def _copy_bounded(
    source: BinaryIO,
    destination: BinaryIO,
    resource: StartupFileResource,
    limit: int,
    remaining: int,
) -> int:
    size_bytes = 0
    while True:
        chunk = source.read(min(DOWNLOAD_CHUNK_BYTES, limit - size_bytes + 1))
        if not chunk:
            return size_bytes
        size_bytes += len(chunk)
        _raise_if_too_large(resource.file_id, size_bytes, limit, remaining)
        destination.write(chunk)


def _raise_if_too_large(file_id: str, size: int, limit: int, remaining: int) -> None:
    if size <= limit:
        return
    if remaining < MAX_FILE_BYTES:
        raise StartupFileResourceError(
            f"Anthropic file {file_id} would exceed the 1 GiB startup total limit."
        )
    raise StartupFileResourceError(
        f"Anthropic file {file_id} exceeds the 500 MiB per-file limit."
    )


def _open_request(request: Request, timeout: float):
    return build_opener(_NoRedirectHandler()).open(request, timeout=timeout)


def _format_http_error(error: HTTPError, file_id: str, api_key: str) -> str:
    detail = ""
    try:
        raw = error.read(1024)
        detail = _redact_error_detail(
            " ".join(raw.decode("utf-8", errors="replace").split()),
            api_key,
        )
    except OSError:
        pass
    finally:
        error.close()
    suffix = f": {detail}" if detail else ""
    return f"Could not download Anthropic file {file_id}: HTTP {error.code}{suffix}"


def _redact_error_detail(detail: str, api_key: str) -> str:
    return detail.replace(api_key, "[REDACTED]")[:300]


__all__ = [
    "DOWNLOAD_CHUNK_BYTES",
    "OpenRequest",
    "StartupFileResource",
    "StartupFileResourceError",
    "stage_file_resource",
]
