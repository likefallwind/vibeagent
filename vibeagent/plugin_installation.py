from __future__ import annotations

from pathlib import Path
import shutil


MAX_PLUGIN_FILES = 5_000
MAX_PLUGIN_TOTAL_BYTES = 100_000_000
EXCLUDED_CACHE_DIRECTORY_NAMES = frozenset({".git", ".vibeagent", "__pycache__"})


def copy_plugin_tree(source: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Plugin staging path already exists: {destination.name}")
    destination.mkdir(mode=0o700)
    file_count = 0
    total_bytes = 0
    try:
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source)
            if any(part in EXCLUDED_CACHE_DIRECTORY_NAMES for part in relative.parts):
                continue
            if path.is_symlink():
                raise ValueError(f"Plugin install source contains a symbolic link: {relative.as_posix()}")
            target = destination / relative
            if path.is_dir():
                target.mkdir(mode=path.stat().st_mode & 0o777, exist_ok=True)
                continue
            if not path.is_file():
                raise ValueError(f"Plugin install source contains a non-regular file: {relative.as_posix()}")
            file_count += 1
            total_bytes += path.stat().st_size
            if file_count > MAX_PLUGIN_FILES:
                raise ValueError(f"Plugin contains more than {MAX_PLUGIN_FILES} files.")
            if total_bytes > MAX_PLUGIN_TOTAL_BYTES:
                raise ValueError(f"Plugin exceeds {MAX_PLUGIN_TOTAL_BYTES} bytes.")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target, follow_symlinks=False)
    except Exception:
        remove_plugin_tree(destination)
        raise


def remove_plugin_tree(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"Refusing to remove unsafe plugin directory: {path}")
    shutil.rmtree(path)


__all__ = ["copy_plugin_tree", "remove_plugin_tree"]
