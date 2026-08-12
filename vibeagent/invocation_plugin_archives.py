from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from uuid import uuid4
import zipfile

from .plugin_installation import MAX_PLUGIN_FILES, MAX_PLUGIN_TOTAL_BYTES, remove_plugin_tree
from .plugin_manifest import PLUGIN_NAME_PATTERN, read_plugin_manifest
from .user_paths import user_home


MAX_PLUGIN_ARCHIVE_BYTES = 100_000_000
MAX_PLUGIN_ARCHIVE_ENTRIES = MAX_PLUGIN_FILES * 2
MAX_PLUGIN_ARCHIVE_PATH_CHARS = 1_000
MAX_PLUGIN_ARCHIVE_PATH_DEPTH = 32
_KNOWN_PLUGIN_ROOT_NAMES = frozenset(
    {
        ".claude-plugin",
        ".mcp.json",
        ".lsp.json",
        "SKILL.md",
        "agents",
        "bin",
        "commands",
        "hooks",
        "monitors",
        "settings.json",
        "skills",
    }
)


def materialize_invocation_plugin_archive(
    archive_path: Path,
    *,
    manifestless_name: str | None = None,
) -> Path:
    archive = archive_path.resolve()
    try:
        with archive.open("rb") as stream:
            size = os.fstat(stream.fileno()).st_size
            if size > MAX_PLUGIN_ARCHIVE_BYTES:
                raise ValueError(
                    f"Plugin ZIP archive exceeds {MAX_PLUGIN_ARCHIVE_BYTES} bytes: {archive_path}"
                )
            digest = _stream_sha256(stream)
            stream.seek(0)
            entries, prefix, root_name = _inspect_archive(
                stream,
                archive,
                manifestless_name=manifestless_name,
            )
            cache_root = _invocation_archive_cache_root()
            cache_key = hashlib.sha256(f"{digest}\0{root_name}".encode("utf-8")).hexdigest()
            slot = cache_root / cache_key
            plugin_root = slot / root_name
            if slot.exists() or slot.is_symlink():
                _validate_cached_plugin(slot, plugin_root)
                _validate_cache_matches_archive(stream, entries, prefix, plugin_root)
                return plugin_root.resolve()

            staging = cache_root / f".{cache_key}.extract-{uuid4().hex[:8]}"
            staging_root = staging / root_name
            staging.mkdir(mode=0o700)
            staging_root.mkdir(mode=0o700)
            try:
                _extract_archive(stream, entries, prefix, staging_root)
                read_plugin_manifest(staging_root)
                try:
                    staging.replace(slot)
                except OSError:
                    if not slot.is_dir() or slot.is_symlink():
                        raise
                    remove_plugin_tree(staging)
                _validate_cached_plugin(slot, plugin_root)
                _validate_cache_matches_archive(stream, entries, prefix, plugin_root)
            except Exception:
                if staging.exists():
                    remove_plugin_tree(staging)
                raise
            return plugin_root.resolve()
    except zipfile.BadZipFile as error:
        raise ValueError(f"Plugin ZIP archive is invalid: {archive_path}: {error}") from error
    except OSError as error:
        raise ValueError(f"Could not read plugin ZIP archive {archive_path}: {error}") from error


def _stream_sha256(stream) -> str:
    digest = hashlib.sha256()
    while chunk := stream.read(64 * 1024):
        digest.update(chunk)
    return digest.hexdigest()


def _inspect_archive(
    stream,
    archive_path: Path,
    *,
    manifestless_name: str | None = None,
) -> tuple[tuple[tuple[zipfile.ZipInfo, PurePosixPath], ...], str | None, str]:
    entries: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
    seen: set[PurePosixPath] = set()
    with zipfile.ZipFile(stream) as archive:
        for index, info in enumerate(archive.infolist(), start=1):
            if index > MAX_PLUGIN_ARCHIVE_ENTRIES:
                raise ValueError(
                    f"Plugin ZIP archive contains more than {MAX_PLUGIN_ARCHIVE_ENTRIES} entries."
                )
            path = _safe_archive_path(info.filename)
            if path in seen:
                raise ValueError(f"Plugin ZIP archive contains duplicate path: {path.as_posix()}")
            seen.add(path)
            _validate_archive_entry(info, path)
            entries.append((info, path))
    file_paths = [path for info, path in entries if not info.is_dir()]
    if not file_paths:
        raise ValueError(f"Plugin ZIP archive is empty: {archive_path}")
    prefix = _wrapper_prefix(file_paths)
    stripped = [_strip_prefix(path, prefix) for path in file_paths]
    if any(not path.parts for path in stripped):
        raise ValueError("Plugin ZIP archive wrapper cannot contain a file at its root path.")
    manifest_path = PurePosixPath(".claude-plugin/plugin.json")
    if manifest_path in stripped:
        root_name = "plugin"
    else:
        root_name = prefix or manifestless_name or archive_path.stem
        if not PLUGIN_NAME_PATTERN.fullmatch(root_name):
            raise ValueError(
                "Manifestless plugin ZIP name must use 1-64 lowercase letters, digits, or hyphens."
            )
    return tuple(entries), prefix, root_name


def _safe_archive_path(value: str) -> PurePosixPath:
    if (
        not value
        or "\x00" in value
        or "\\" in value
        or value.startswith("/")
        or len(value) > MAX_PLUGIN_ARCHIVE_PATH_CHARS
    ):
        raise ValueError(f"Plugin ZIP archive path is unsafe: {value!r}")
    path = PurePosixPath(value)
    if (
        not path.parts
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or len(path.parts) > MAX_PLUGIN_ARCHIVE_PATH_DEPTH
        or (path.parts[0].endswith(":") and len(path.parts[0]) == 2)
    ):
        raise ValueError(f"Plugin ZIP archive path is unsafe: {value!r}")
    return path


def _validate_archive_entry(info: zipfile.ZipInfo, path: PurePosixPath) -> None:
    if info.flag_bits & 0x1:
        raise ValueError(f"Plugin ZIP archive contains encrypted entry: {path.as_posix()}")
    unix_mode = info.external_attr >> 16
    file_type = stat.S_IFMT(unix_mode)
    if info.is_dir():
        if file_type not in {0, stat.S_IFDIR}:
            raise ValueError(f"Plugin ZIP archive contains unsupported entry: {path.as_posix()}")
        return
    if file_type not in {0, stat.S_IFREG}:
        raise ValueError(f"Plugin ZIP archive contains unsupported entry: {path.as_posix()}")


def _wrapper_prefix(paths: list[PurePosixPath]) -> str | None:
    first_parts = {path.parts[0] for path in paths}
    if len(first_parts) != 1 or any(len(path.parts) < 2 for path in paths):
        return None
    first = next(iter(first_parts))
    wrapped_manifest = PurePosixPath(first, ".claude-plugin", "plugin.json")
    if wrapped_manifest in paths or first not in _KNOWN_PLUGIN_ROOT_NAMES:
        return first
    return None


def _strip_prefix(path: PurePosixPath, prefix: str | None) -> PurePosixPath:
    return PurePosixPath(*path.parts[1:]) if prefix is not None else path


def _extract_archive(
    stream,
    entries: tuple[tuple[zipfile.ZipInfo, PurePosixPath], ...],
    prefix: str | None,
    destination: Path,
) -> None:
    file_count = 0
    total_bytes = 0
    stream.seek(0)
    try:
        with zipfile.ZipFile(stream) as archive:
            for info, original_path in entries:
                relative = _strip_prefix(original_path, prefix)
                if not relative.parts:
                    continue
                target = destination.joinpath(*relative.parts)
                if info.is_dir():
                    target.mkdir(mode=_entry_mode(info, directory=True), parents=True, exist_ok=True)
                    continue
                file_count += 1
                total_bytes += info.file_size
                if file_count > MAX_PLUGIN_FILES:
                    raise ValueError(f"Plugin ZIP contains more than {MAX_PLUGIN_FILES} files.")
                if total_bytes > MAX_PLUGIN_TOTAL_BYTES:
                    raise ValueError(f"Plugin ZIP exceeds {MAX_PLUGIN_TOTAL_BYTES} expanded bytes.")
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with archive.open(info, "r") as source, target.open("xb") as output:
                    copied = 0
                    while chunk := source.read(64 * 1024):
                        copied += len(chunk)
                        if copied > info.file_size:
                            raise ValueError(
                                f"Plugin ZIP entry exceeds its declared size: {original_path.as_posix()}"
                            )
                        output.write(chunk)
                if copied != info.file_size:
                    raise ValueError(f"Plugin ZIP entry is truncated: {original_path.as_posix()}")
                target.chmod(_entry_mode(info, directory=False))
    except (OSError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as error:
        raise ValueError(f"Could not extract plugin ZIP archive: {error}") from error


def _entry_mode(info: zipfile.ZipInfo, *, directory: bool) -> int:
    mode = (info.external_attr >> 16) & 0o777
    return mode or (0o755 if directory else 0o644)


def _invocation_archive_cache_root() -> Path:
    runtime = user_home() / ".vibeagent"
    root = runtime / "invocation-plugin-cache"
    for path in (runtime, root):
        if path.is_symlink():
            raise ValueError(f"Invocation plugin cache must not be a symbolic link: {path}")
        path.mkdir(mode=0o700, exist_ok=True)
        if not path.is_dir():
            raise ValueError(f"Invocation plugin cache must be a directory: {path}")
        os.chmod(path, 0o700)
    return root


def _validate_cached_plugin(slot: Path, plugin_root: Path) -> None:
    if slot.is_symlink() or not slot.is_dir():
        raise ValueError(f"Invocation plugin cache entry is unsafe: {slot.name}")
    if plugin_root.is_symlink() or not plugin_root.is_dir():
        raise ValueError(f"Invocation plugin cache root is unsafe: {plugin_root}")
    file_count = 0
    total_bytes = 0
    for path in plugin_root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Invocation plugin cache contains a symbolic link: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"Invocation plugin cache contains a non-regular file: {path}")
        file_count += 1
        total_bytes += path.stat().st_size
        if file_count > MAX_PLUGIN_FILES or total_bytes > MAX_PLUGIN_TOTAL_BYTES:
            raise ValueError("Invocation plugin cache exceeds plugin safety limits.")
    if set(slot.iterdir()) != {plugin_root}:
        raise ValueError(f"Invocation plugin cache entry has unexpected contents: {slot.name}")
    read_plugin_manifest(plugin_root)


def _validate_cache_matches_archive(
    stream,
    entries: tuple[tuple[zipfile.ZipInfo, PurePosixPath], ...],
    prefix: str | None,
    plugin_root: Path,
) -> None:
    expected: set[Path] = set()
    stream.seek(0)
    try:
        with zipfile.ZipFile(stream) as archive:
            for info, original_path in entries:
                if info.is_dir():
                    continue
                relative = _strip_prefix(original_path, prefix)
                target = plugin_root.joinpath(*relative.parts)
                expected.add(target)
                if (target.stat().st_mode & 0o777) != _entry_mode(info, directory=False):
                    raise ValueError(
                        f"Invocation plugin cache mode does not match archive: {relative.as_posix()}"
                    )
                with archive.open(info, "r") as source, target.open("rb") as cached:
                    while True:
                        source_chunk = source.read(64 * 1024)
                        cached_chunk = cached.read(64 * 1024)
                        if source_chunk != cached_chunk:
                            raise ValueError(
                                f"Invocation plugin cache content does not match archive: {relative.as_posix()}"
                            )
                        if not source_chunk:
                            break
    except (OSError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as error:
        raise ValueError(f"Could not verify invocation plugin cache: {error}") from error
    actual = {path for path in plugin_root.rglob("*") if path.is_file()}
    if actual != expected:
        raise ValueError("Invocation plugin cache file set does not match archive.")


__all__ = [
    "MAX_PLUGIN_ARCHIVE_BYTES",
    "MAX_PLUGIN_ARCHIVE_ENTRIES",
    "MAX_PLUGIN_ARCHIVE_PATH_CHARS",
    "MAX_PLUGIN_ARCHIVE_PATH_DEPTH",
    "materialize_invocation_plugin_archive",
]
