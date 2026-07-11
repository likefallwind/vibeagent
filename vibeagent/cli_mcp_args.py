from __future__ import annotations

from pathlib import Path


def resolve_mcp_config_paths(project_root: Path, values: list[str] | tuple[str, ...] | None) -> tuple[Path, ...]:
    paths: list[Path] = []
    for raw_value in values or ():
        value = raw_value.strip()
        if not value:
            raise ValueError("--mcp-config cannot be empty.")
        path = Path(value)
        resolved = path if path.is_absolute() else project_root / path
        if not resolved.exists():
            raise ValueError(f"--mcp-config file not found: {value}.")
        if resolved.is_dir():
            raise ValueError(f"--mcp-config must be a file: {value}.")
        if resolved not in paths:
            paths.append(resolved)
    return tuple(paths)
