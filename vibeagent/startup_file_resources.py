from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import os
from pathlib import Path
import re

from .config import ANTHROPIC_PROVIDER, resolve_provider_config
from .startup_file_download import (
    OpenRequest,
    StartupFileResource,
    StartupFileResourceError,
    stage_file_resource,
)
from .workspace_resolve import resolve_mutation_path


MAX_FILE_RESOURCES = 20
MAX_TOTAL_BYTES = 1024 * 1024 * 1024
_FILE_ID_PATTERN = re.compile(r"file_[A-Za-z0-9_-]{1,200}\Z")


@dataclass(frozen=True)
class DownloadedFileResource:
    file_id: str
    relative_path: str
    size_bytes: int


@dataclass(frozen=True)
class _StagedFile:
    resource: StartupFileResource
    temporary_path: Path
    size_bytes: int
    device: int
    inode: int


def parse_startup_file_resources(
    specs: Sequence[str],
    project_root: str | Path,
) -> tuple[StartupFileResource, ...]:
    if len(specs) > MAX_FILE_RESOURCES:
        raise StartupFileResourceError(
            f"--file accepts at most {MAX_FILE_RESOURCES} resources per startup."
        )
    root = Path(project_root).resolve()
    resources: list[StartupFileResource] = []
    targets: set[Path] = set()
    for raw_spec in specs:
        spec = raw_spec.strip()
        if ":" not in spec:
            raise StartupFileResourceError(
                f"Invalid --file spec {raw_spec!r}; expected FILE_ID:RELATIVE_PATH."
            )
        file_id, relative_path = spec.split(":", 1)
        if not _FILE_ID_PATTERN.fullmatch(file_id):
            raise StartupFileResourceError(f"Invalid Anthropic file id in --file: {file_id!r}.")
        if not relative_path or relative_path != relative_path.strip():
            raise StartupFileResourceError(
                f"Invalid destination in --file spec {raw_spec!r}."
            )
        try:
            target = resolve_mutation_path(root, relative_path)
        except ValueError as error:
            raise StartupFileResourceError(str(error)) from error
        if target == root:
            raise StartupFileResourceError("--file destination must name a file.")
        if target in targets:
            raise StartupFileResourceError(
                f"Duplicate --file destination: {relative_path}"
            )
        if target.exists() or target.is_symlink():
            raise StartupFileResourceError(
                f"--file destination already exists: {relative_path}"
            )
        targets.add(target)
        resources.append(StartupFileResource(file_id, relative_path, target))
    return tuple(resources)


def download_startup_file_resources(
    specs: Sequence[str],
    project_root: str | Path,
    provider_env: Mapping[str, str | None],
    *,
    open_request: OpenRequest | None = None,
) -> tuple[DownloadedFileResource, ...]:
    if not specs:
        return ()
    resources = parse_startup_file_resources(specs, project_root)
    config = resolve_provider_config(provider_env)
    if config.provider != ANTHROPIC_PROVIDER:
        raise StartupFileResourceError(
            "--file requires --provider anthropic because file ids belong to the Anthropic Files API."
        )
    if not config.api_key:
        raise StartupFileResourceError(
            "--file requires ANTHROPIC_API_KEY or --api-key."
        )
    if config.api_key_source != "ANTHROPIC_API_KEY":
        raise StartupFileResourceError(
            "--file requires ANTHROPIC_API_KEY authentication; ANTHROPIC_AUTH_TOKEN is not supported."
        )

    staged: list[_StagedFile] = []
    published: list[_StagedFile] = []
    created_directories: list[Path] = []
    total_bytes = 0
    try:
        for resource in resources:
            _create_parent_directories(resource.target.parent, Path(project_root), created_directories)
            _revalidate_target(resource, project_root)
            temporary_path, size_bytes = stage_file_resource(
                resource,
                base_url=config.base_url,
                api_key=config.api_key,
                remaining_bytes=MAX_TOTAL_BYTES - total_bytes,
                open_request=open_request,
            )
            identity = temporary_path.stat()
            staged.append(
                _StagedFile(
                    resource,
                    temporary_path,
                    size_bytes,
                    identity.st_dev,
                    identity.st_ino,
                )
            )
            total_bytes += size_bytes

        for item in staged:
            _revalidate_target(item.resource, project_root)
            try:
                os.link(item.temporary_path, item.resource.target)
            except FileExistsError as error:
                raise StartupFileResourceError(
                    f"--file destination appeared during download: {item.resource.relative_path}"
                ) from error
            published.append(item)
        for item in staged:
            item.temporary_path.unlink()
        return tuple(
            DownloadedFileResource(
                item.resource.file_id,
                item.resource.relative_path,
                item.size_bytes,
            )
            for item in staged
        )
    except StartupFileResourceError:
        _rollback_downloads(staged, published, created_directories)
        raise
    except OSError as error:
        _rollback_downloads(staged, published, created_directories)
        raise StartupFileResourceError(_format_download_error(error)) from error
    except BaseException:
        _rollback_downloads(staged, published, created_directories)
        raise


def format_downloaded_file_resources(
    resources: Sequence[DownloadedFileResource],
) -> str | None:
    if not resources:
        return None
    paths = ", ".join(resource.relative_path for resource in resources)
    return f"Downloaded startup file resources: {paths}"


def _create_parent_directories(parent: Path, project_root: Path, created: list[Path]) -> None:
    root = project_root.resolve()
    missing: list[Path] = []
    current = parent
    while current != root and not current.exists():
        missing.append(current)
        current = current.parent
    if current != root and root not in current.parents:
        raise StartupFileResourceError("--file destination escapes the project directory.")
    if current.exists() and not current.is_dir():
        raise StartupFileResourceError(f"--file destination parent is not a directory: {current}")
    for directory in reversed(missing):
        try:
            directory.mkdir()
            created.append(directory)
        except FileExistsError:
            if not directory.is_dir() or directory.is_symlink():
                raise StartupFileResourceError(
                    f"--file destination parent is unsafe: {directory}"
                )


def _revalidate_target(resource: StartupFileResource, project_root: str | Path) -> None:
    try:
        target = resolve_mutation_path(Path(project_root).resolve(), resource.relative_path)
    except ValueError as error:
        raise StartupFileResourceError(str(error)) from error
    if target != resource.target:
        raise StartupFileResourceError(
            f"--file destination changed during download: {resource.relative_path}"
        )
    if target.exists() or target.is_symlink():
        raise StartupFileResourceError(
            f"--file destination already exists: {resource.relative_path}"
        )


def _rollback_downloads(
    staged: Sequence[_StagedFile],
    published: Sequence[_StagedFile],
    created_directories: Sequence[Path],
) -> None:
    for item in reversed(published):
        try:
            target_identity = item.resource.target.stat()
            if (target_identity.st_dev, target_identity.st_ino) == (
                item.device,
                item.inode,
            ):
                item.resource.target.unlink()
        except (FileNotFoundError, OSError):
            pass
    for item in staged:
        try:
            item.temporary_path.unlink()
        except FileNotFoundError:
            pass
    for directory in reversed(created_directories):
        try:
            directory.rmdir()
        except OSError:
            pass


def _format_download_error(error: BaseException) -> str:
    return f"Could not publish startup file resources: {error}"


__all__ = [
    "DownloadedFileResource",
    "StartupFileResource",
    "StartupFileResourceError",
    "download_startup_file_resources",
    "format_downloaded_file_resources",
    "parse_startup_file_resources",
]
