from __future__ import annotations

from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_project_metadata import read_package_json_manifest, read_pyproject_manifest
from .workspace_search_files import list_files


def read_project_manifests(workspace: RunWorkspace, max_files: int = 30, max_items: int = 500) -> dict[str, object]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 200:
        raise ValueError("max_files must be at most 200.")
    if max_items < 1:
        raise ValueError("max_items must be at least 1.")
    if max_items > 2000:
        raise ValueError("max_items must be at most 2000.")

    manifest_files = [
        file
        for file in list_files(workspace.root)
        if Path(file).name in {"package.json", "pyproject.toml"}
    ]
    manifests: list[dict[str, object]] = []
    remaining_items = max_items
    for relative_path in manifest_files[:max_files]:
        path = workspace.root / relative_path
        if Path(relative_path).name == "package.json":
            manifest = read_package_json_manifest(path, relative_path, remaining_items)
        else:
            manifest = read_pyproject_manifest(path, relative_path, remaining_items)
        manifests.append(manifest)
        remaining_items = max(0, remaining_items - int(manifest["item_count"]))

    total_items = sum(int(manifest["item_count"]) for manifest in manifests)
    truncated = len(manifest_files) > max_files or any(bool(manifest["truncated"]) for manifest in manifests)
    return {
        "ok": all(bool(manifest["ok"]) for manifest in manifests),
        "manifests": manifests,
        "total_files": len(manifest_files),
        "scanned_files": min(len(manifest_files), max_files),
        "total_items": total_items,
        "truncated": truncated,
        "message": f"Read {min(len(manifest_files), max_files)}/{len(manifest_files)} project manifest file(s).",
    }
