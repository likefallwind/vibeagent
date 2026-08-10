from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from .plugin_installation import remove_plugin_tree
from .plugin_remote_sources import (
    GITHUB_REPOSITORY_PATTERN,
    clone_public_git,
    download_public_json,
    github_repository_url,
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
) -> Iterator[AcquiredMarketplace]:
    kind, normalized_source, ref = _classify_source(source, source_kind, source_ref)
    if kind == "local":
        path = resolve_mutation_path(project_root, normalized_source)
        yield AcquiredMarketplace(
            root=path,
            source=path.relative_to(project_root.resolve()).as_posix(),
            source_kind=kind,
            source_ref=None,
        )
        return

    fetch_root = plugins_root(project_root, create=True) / "fetches"
    ensure_directory(fetch_root, create=True)
    temporary = fetch_root / f".marketplace-{uuid4().hex[:12]}"
    try:
        if kind in {"github", "git"}:
            url = github_repository_url(normalized_source) if kind == "github" else normalized_source
            clone_public_git(url, temporary, ref=ref)
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
        url = normalize_public_https_url(normalized, label="Marketplace source")
        return source_kind, url, validate_git_revision(source_ref) if source_kind == "git" else None
    if source_kind is not None:
        raise ValueError(f"Unsupported marketplace source kind: {source_kind}")

    github_source, github_ref = _split_github_source(normalized)
    if github_source is not None:
        return "github", github_source, validate_git_revision(github_ref)
    parsed = urlsplit(normalized)
    if parsed.scheme:
        fragment = parsed.fragment or None
        url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
        url = normalize_public_https_url(url, label="Marketplace source")
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


__all__ = ["AcquiredMarketplace", "acquire_marketplace"]
