from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterator
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from .plugin_installation import remove_plugin_tree
from .plugin_remote_sources import (
    GITHUB_REPOSITORY_PATTERN,
    clone_remote_git,
    download_public_json,
    github_repository_url,
    normalize_git_url,
    normalize_public_https_url,
    validate_git_revision,
)
from .plugin_state import ensure_directory, plugins_root
from .workspace_resolve import resolve_mutation_path


@dataclass(frozen=True)
class AcquiredMarketplace:
    root: Path
    source: str
    source_kind: str
    source_ref: str | None


@contextmanager
def acquire_marketplace(
    project_root: Path,
    source: str,
    *,
    source_kind: str | None = None,
    source_ref: str | None = None,
    storage_root: Path | None = None,
) -> Iterator[AcquiredMarketplace]:
    project = project_root.resolve()
    store = (storage_root or project).resolve()
    kind, normalized_source, ref = _classify_source(source, source_kind, source_ref)
    if kind == "local":
        if store == project or not Path(normalized_source).is_absolute():
            path = resolve_mutation_path(project, normalized_source)
        else:
            path = Path(normalized_source).resolve()
            if not path.is_dir():
                raise ValueError(f"Marketplace directory does not exist: {path}")
        yield AcquiredMarketplace(
            root=path,
            source=(
                path.relative_to(project).as_posix()
                if store == project
                else path.as_posix()
            ),
            source_kind=kind,
            source_ref=None,
        )
        return

    fetch_root = plugins_root(store, create=True) / "fetches"
    ensure_directory(fetch_root, create=True)
    temporary = fetch_root / f".marketplace-{uuid4().hex[:12]}"
    try:
        if kind in {"github", "git"}:
            url = github_repository_url(normalized_source) if kind == "github" else normalized_source
            clone_remote_git(url, temporary, ref=ref)
        elif kind == "http":
            manifest_path = temporary / ".claude-plugin" / "marketplace.json"
            download_public_json(normalized_source, manifest_path)
        else:
            raise ValueError(f"Unsupported marketplace source kind: {kind}")
        yield AcquiredMarketplace(
            root=temporary,
            source=normalized_source,
            source_kind=kind,
            source_ref=ref,
        )
    finally:
        if temporary.exists():
            remove_plugin_tree(temporary)


def _classify_source(
    source: str,
    source_kind: str | None,
    source_ref: str | None,
) -> tuple[str, str, str | None]:
    normalized = source.strip()
    if not normalized:
        raise ValueError("Marketplace source must not be empty.")
    if source_kind == "local":
        return "local", normalized, None
    if source_kind == "github":
        if not GITHUB_REPOSITORY_PATTERN.fullmatch(normalized):
            raise ValueError("Stored GitHub marketplace source is invalid.")
        return "github", normalized, validate_git_revision(source_ref)
    if source_kind in {"git", "http"}:
        url = (
            normalize_git_url(normalized, label="Marketplace source")
            if source_kind == "git"
            else normalize_public_https_url(normalized, label="Marketplace source")
        )
        return source_kind, url, validate_git_revision(source_ref) if source_kind == "git" else None
    if source_kind is not None:
        raise ValueError(f"Unsupported marketplace source kind: {source_kind}")

    github_source, github_ref = _split_github_source(normalized)
    if github_source is not None:
        return "github", github_source, validate_git_revision(github_ref)
    ssh_source, ssh_ref = _split_ssh_source(normalized)
    if ssh_source is not None:
        return "git", ssh_source, validate_git_revision(ssh_ref)
    parsed = urlsplit(normalized)
    if parsed.scheme:
        fragment = parsed.fragment or None
        url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
        url = (
            normalize_git_url(url, label="Marketplace source")
            if parsed.scheme == "ssh"
            else normalize_public_https_url(url, label="Marketplace source")
        )
        if parsed.path.lower().endswith(".json"):
            if fragment:
                raise ValueError("Direct marketplace JSON URLs must not include a Git ref fragment.")
            return "http", url, None
        return "git", url, validate_git_revision(fragment)
    return "local", normalized, None


def _split_github_source(value: str) -> tuple[str | None, str | None]:
    repository, marker, ref = value.partition("#")
    if not GITHUB_REPOSITORY_PATTERN.fullmatch(repository):
        return None, None
    if marker and not ref:
        raise ValueError("GitHub marketplace ref must not be empty.")
    return repository[:-4] if repository.endswith(".git") else repository, ref or None


def _split_ssh_source(value: str) -> tuple[str | None, str | None]:
    source, marker, ref = value.partition("#")
    if source.startswith("ssh://") or re.match(r"^[^/@\s]+@[^/:\s]+:", source) is None:
        return None, None
    normalized = normalize_git_url(source, label="Marketplace source")
    if marker and not ref:
        raise ValueError("SSH marketplace ref must not be empty.")
    return normalized, ref or None


__all__ = ["AcquiredMarketplace", "acquire_marketplace"]
