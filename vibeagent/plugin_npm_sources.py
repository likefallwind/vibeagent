from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from pathlib import Path, PurePosixPath
import re
import socket
import tarfile
import urllib.error
import urllib.request
from urllib.parse import quote, urlsplit, urlunsplit

from .network_url_safety import UrlSafetyError, open_scoped_url
from .plugin_installation import (
    MAX_PLUGIN_FILES,
    MAX_PLUGIN_TOTAL_BYTES,
    remove_plugin_tree,
)
from .plugin_remote_sources import normalize_public_https_url


DEFAULT_NPM_REGISTRY = "https://registry.npmjs.org/"
MAX_NPM_METADATA_BYTES = 2_000_000
MAX_NPM_TARBALL_BYTES = 100_000_000
NPM_DOWNLOAD_TIMEOUT_SECONDS = 60
MAX_NPM_ARCHIVE_ENTRIES = MAX_PLUGIN_FILES * 2
MAX_NPM_ARCHIVE_PATH_CHARS = 1_000
MAX_NPM_ARCHIVE_PATH_DEPTH = 32
NPM_PACKAGE_PART_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9._~-]{0,213})$")
NPM_VERSION_SELECTOR_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._+~-]{0,127})$")


def validate_npm_package_name(value: str) -> str:
    parts = value.split("/")
    if value.startswith("@"):
        if len(parts) != 2 or not NPM_PACKAGE_PART_PATTERN.fullmatch(parts[0][1:]):
            raise ValueError("Scoped npm package must use @scope/name with lowercase safe characters.")
        package_name = parts[1]
    elif len(parts) == 1:
        package_name = parts[0]
    else:
        raise ValueError("npm package must use name or @scope/name.")
    if not NPM_PACKAGE_PART_PATTERN.fullmatch(package_name):
        raise ValueError("npm package name must use lowercase safe characters.")
    if len(value) > 214:
        raise ValueError("npm package name must be at most 214 characters.")
    return value


def validate_npm_version_selector(value: str | None) -> str:
    selected = value or "latest"
    if not NPM_VERSION_SELECTOR_PATTERN.fullmatch(selected):
        raise ValueError("npm package version must be an exact version or dist-tag using safe characters.")
    return selected


def normalize_npm_registry(value: str | None) -> str:
    normalized = normalize_public_https_url(value or DEFAULT_NPM_REGISTRY, label="npm registry")
    parsed = urlsplit(normalized)
    if parsed.query:
        raise ValueError("npm registry must not contain a query string.")
    path = parsed.path.rstrip("/") + "/"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def download_npm_plugin(
    package: str,
    destination: Path,
    *,
    version: str | None = None,
    registry: str | None = None,
) -> str:
    package = validate_npm_package_name(package)
    selector = validate_npm_version_selector(version)
    registry_url = normalize_npm_registry(registry)
    metadata_url = registry_url + quote(package, safe="@")
    metadata = _download_json(metadata_url, label=f"npm package metadata for {package}")
    resolved_version, tarball_url, integrity = _resolve_package_version(
        metadata,
        package=package,
        selector=selector,
    )
    archive_path = destination.parent / f".{destination.name}-{resolved_version}.tgz"
    archive_downloaded = False
    try:
        _download_tarball(tarball_url, archive_path, integrity)
        archive_downloaded = True
        _extract_npm_tarball(archive_path, destination)
    finally:
        if archive_downloaded:
            archive_path.unlink(missing_ok=True)
    return resolved_version


def _download_json(url: str, *, label: str) -> dict[str, object]:
    request = urllib.request.Request(
        normalize_public_https_url(url, label=label),
        headers={"Accept": "application/json", "User-Agent": "vibeagent-plugin-npm/1.0"},
    )
    try:
        with open_scoped_url(
            request,
            timeout=NPM_DOWNLOAD_TIMEOUT_SECONDS,
            scope="public",
            require_https=True,
        ) as response:
            raw = response.read(MAX_NPM_METADATA_BYTES + 1)
    except (UrlSafetyError, urllib.error.URLError, TimeoutError, socket.timeout, OSError) as error:
        raise ValueError(f"Could not download {label}: {error}") from error
    if len(raw) > MAX_NPM_METADATA_BYTES:
        raise ValueError(f"{label} exceeds {MAX_NPM_METADATA_BYTES} bytes.")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not valid UTF-8 JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object.")
    return payload


def _resolve_package_version(
    metadata: dict[str, object],
    *,
    package: str,
    selector: str,
) -> tuple[str, str, tuple[str, bytes]]:
    if metadata.get("name") != package:
        raise ValueError(f"npm metadata identity does not match requested package {package}.")
    versions = metadata.get("versions")
    tags = metadata.get("dist-tags", {})
    if not isinstance(versions, dict) or not isinstance(tags, dict):
        raise ValueError(f"npm metadata for {package} is missing versions or dist-tags.")
    selected = tags.get(selector, selector)
    if not isinstance(selected, str) or selected not in versions:
        raise ValueError(f"npm package {package} does not provide version or dist-tag {selector!r}.")
    version_payload = versions[selected]
    if (
        not isinstance(version_payload, dict)
        or version_payload.get("name") != package
        or version_payload.get("version") != selected
    ):
        raise ValueError(f"npm package {package} version metadata is inconsistent for {selected!r}.")
    dist = version_payload.get("dist")
    if not isinstance(dist, dict):
        raise ValueError(f"npm package {package}@{selected} is missing dist metadata.")
    tarball = dist.get("tarball")
    if not isinstance(tarball, str):
        raise ValueError(f"npm package {package}@{selected} is missing a tarball URL.")
    tarball = normalize_public_https_url(tarball, label="npm tarball URL")
    return selected, tarball, _parse_integrity(dist, package, selected)


def _parse_integrity(
    dist: dict[object, object],
    package: str,
    version: str,
) -> tuple[str, bytes]:
    integrity = dist.get("integrity")
    if isinstance(integrity, str):
        for token in integrity.split():
            algorithm, marker, encoded = token.partition("-")
            if marker and algorithm == "sha512":
                try:
                    expected = base64.b64decode(encoded, validate=True)
                except (binascii.Error, ValueError) as error:
                    raise ValueError(f"npm package {package}@{version} has invalid integrity metadata.") from error
                if len(expected) != hashlib.sha512().digest_size:
                    raise ValueError(f"npm package {package}@{version} has invalid integrity metadata.")
                return algorithm, expected
    shasum = dist.get("shasum")
    if isinstance(shasum, str) and re.fullmatch(r"[0-9a-fA-F]{40}", shasum):
        return "sha1", bytes.fromhex(shasum)
    raise ValueError(f"npm package {package}@{version} requires sha512 integrity or a SHA-1 shasum.")


def _download_tarball(url: str, destination: Path, integrity: tuple[str, bytes]) -> None:
    algorithm, expected = integrity
    digest = hashlib.new(algorithm)
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/octet-stream", "User-Agent": "vibeagent-plugin-npm/1.0"},
    )
    total = 0
    created = False
    try:
        with open_scoped_url(
            request,
            timeout=NPM_DOWNLOAD_TIMEOUT_SECONDS,
            scope="public",
            require_https=True,
        ) as response:
            stream = destination.open("xb")
            created = True
            with stream:
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_NPM_TARBALL_BYTES:
                        raise ValueError(f"npm tarball exceeds {MAX_NPM_TARBALL_BYTES} bytes.")
                    digest.update(chunk)
                    stream.write(chunk)
    except (UrlSafetyError, urllib.error.URLError, TimeoutError, socket.timeout, OSError) as error:
        if created:
            destination.unlink(missing_ok=True)
        raise ValueError(f"Could not download npm tarball: {error}") from error
    except Exception:
        if created:
            destination.unlink(missing_ok=True)
        raise
    if not hmac.compare_digest(digest.digest(), expected):
        destination.unlink(missing_ok=True)
        raise ValueError("npm tarball integrity verification failed.")


def _extract_npm_tarball(archive_path: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"npm extraction destination already exists: {destination}")
    destination.mkdir(mode=0o700, parents=True)
    file_count = 0
    entry_count = 0
    total_bytes = 0
    seen: set[Path] = set()
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            for member in archive:
                entry_count += 1
                if entry_count > MAX_NPM_ARCHIVE_ENTRIES:
                    raise ValueError(
                        f"npm tarball contains more than {MAX_NPM_ARCHIVE_ENTRIES} entries."
                    )
                relative = _npm_member_path(member.name)
                if relative is None:
                    continue
                target = destination.joinpath(*relative.parts)
                if target in seen:
                    raise ValueError(f"npm tarball contains duplicate path: {relative.as_posix()}")
                seen.add(target)
                if member.isdir():
                    target.mkdir(mode=member.mode & 0o777, parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    raise ValueError(f"npm tarball contains unsupported entry: {member.name}")
                file_count += 1
                total_bytes += member.size
                if file_count > MAX_PLUGIN_FILES:
                    raise ValueError(f"npm plugin contains more than {MAX_PLUGIN_FILES} files.")
                if total_bytes > MAX_PLUGIN_TOTAL_BYTES:
                    raise ValueError(f"npm plugin exceeds {MAX_PLUGIN_TOTAL_BYTES} bytes.")
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError(f"Could not read npm tarball entry: {member.name}")
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with source, target.open("xb") as stream:
                    remaining = member.size
                    while remaining:
                        chunk = source.read(min(64 * 1024, remaining))
                        if not chunk:
                            raise ValueError(f"npm tarball entry is truncated: {member.name}")
                        stream.write(chunk)
                        remaining -= len(chunk)
                target.chmod(member.mode & 0o777)
    except (OSError, tarfile.TarError, ValueError) as error:
        if destination.exists():
            remove_plugin_tree(destination)
        if isinstance(error, ValueError):
            raise
        raise ValueError(f"Could not extract npm tarball: {error}") from error


def _npm_member_path(name: str) -> PurePosixPath | None:
    if "\\" in name or name.startswith("/") or len(name) > MAX_NPM_ARCHIVE_PATH_CHARS:
        raise ValueError(f"npm tarball path is unsafe: {name}")
    path = PurePosixPath(name)
    if (
        not path.parts
        or path.parts[0] != "package"
        or ".." in path.parts
        or len(path.parts) > MAX_NPM_ARCHIVE_PATH_DEPTH + 1
    ):
        raise ValueError(f"npm tarball entries must stay under package/: {name}")
    relative = PurePosixPath(*path.parts[1:])
    return relative if relative.parts else None


__all__ = [
    "DEFAULT_NPM_REGISTRY",
    "download_npm_plugin",
    "normalize_npm_registry",
    "validate_npm_package_name",
    "validate_npm_version_selector",
]
