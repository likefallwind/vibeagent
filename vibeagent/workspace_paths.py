from __future__ import annotations

from pathlib import Path


def should_ignore_path(root: Path, path: Path) -> bool:
    relative_path = path.resolve().relative_to(root)
    relative_parts = relative_path.parts
    hard_ignored = {
        ".agents",
        ".codex",
        ".git",
        ".pytest_cache",
        ".venv",
        ".vibeagent",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
    if any(part in hard_ignored or part.endswith(".egg-info") for part in relative_parts):
        return True
    if is_sensitive_project_path(relative_path, path.is_dir()):
        return True
    return path_matches_gitignore(root, relative_path, path.is_dir())


def path_matches_gitignore(root: Path, relative_path: Path, is_dir: bool) -> bool:
    for base, pattern in read_gitignore_patterns(root, relative_path):
        scoped_path = gitignore_scoped_path(relative_path, base)
        if scoped_path is not None and gitignore_pattern_matches(pattern, scoped_path, is_dir):
            return True
    return False


def read_gitignore_patterns(root: Path, relative_path: Path) -> list[tuple[Path, str]]:
    rules: list[tuple[Path, str]] = []
    for base in gitignore_rule_bases(relative_path):
        path = root / base / ".gitignore"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("!"):
                continue
            rules.append((base, stripped))
    return rules


def gitignore_rule_bases(relative_path: Path) -> list[Path]:
    parent = relative_path.parent
    bases = [Path(".")]
    current = Path(".")
    for part in parent.parts:
        current = current / part
        bases.append(current)
    return bases


def gitignore_scoped_path(relative_path: Path, base: Path) -> Path | None:
    if base == Path("."):
        return relative_path
    try:
        return relative_path.relative_to(base)
    except ValueError:
        return None


def gitignore_pattern_matches(pattern: str, relative_path: Path, is_dir: bool) -> bool:
    normalized = pattern.replace("\\", "/").strip()
    if not normalized:
        return False
    normalized = normalized.lstrip("/")
    directory_only = normalized.endswith("/")
    normalized = normalized.rstrip("/")
    if not normalized:
        return False
    if directory_only and not path_has_directory(relative_path, normalized, is_dir):
        return False

    relative = relative_path.as_posix()
    if "/" in normalized:
        return relative == normalized or relative.startswith(f"{normalized}/") or relative_path.match(normalized)
    return any(part == normalized for part in relative_path.parts) or relative_path.match(normalized)


def path_has_directory(relative_path: Path, directory: str, is_dir: bool) -> bool:
    parts = relative_path.parts if is_dir else relative_path.parts[:-1]
    if "/" in directory:
        relative = "/".join(parts)
        return relative == directory or relative.startswith(f"{directory}/")
    return directory in parts


def is_protected_project_path(root: Path, path: Path) -> bool:
    try:
        relative_path = path.relative_to(root)
    except ValueError:
        return True
    parts = relative_path.parts
    if is_sensitive_project_path(relative_path, path.is_dir()):
        return True
    return bool(parts and parts[0] in {".git", ".vibeagent"})


def is_sensitive_project_path(relative_path: Path, is_dir: bool = False) -> bool:
    if is_dir:
        return False
    parts = relative_path.parts
    if not parts:
        return False
    name = parts[-1]
    lower_name = name.lower()
    lower_path = relative_path.as_posix().lower()
    sensitive_names = {
        ".env",
        ".envrc",
        ".netrc",
        ".npmrc",
        ".pypirc",
        ".yarnrc",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "id_rsa",
        "known_hosts",
    }
    sensitive_suffixes = (
        ".env",
        ".env.local",
        ".env.development",
        ".env.development.local",
        ".env.localhost",
        ".env.production",
        ".env.production.local",
        ".env.test",
        ".env.test.local",
        ".key",
        ".pem",
        ".p12",
        ".pfx",
        ".crt",
        ".cer",
        ".asc",
        ".gpg",
        ".kube/config",
    )
    if lower_name in sensitive_names:
        return True
    if lower_name.endswith(sensitive_suffixes):
        return True
    if lower_path.endswith("/.kube/config"):
        return True
    return False

