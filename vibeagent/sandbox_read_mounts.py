from __future__ import annotations

from pathlib import Path


def append_sandbox_read_mounts(
    argv: list[str],
    *,
    allow_read: tuple[Path, ...],
    deny_read: tuple[Path, ...],
    writable_roots: tuple[Path, ...],
    deny_write: tuple[Path, ...],
) -> None:
    rules = [
        *((path, "allow") for path in allow_read),
        *((path, "deny") for path in deny_read),
    ]
    rules.sort(key=lambda item: (len(item[0].parts), item[1] == "deny"))
    for path, effect in rules:
        if effect == "deny":
            _append_denied_read_mount(argv, path)
            continue
        _append_allowed_read_mount(
            argv,
            path,
            writable_roots=writable_roots,
            deny_write=deny_write,
        )


def _append_denied_read_mount(argv: list[str], path: Path) -> None:
    if path.is_dir():
        argv.extend(("--tmpfs", path.as_posix()))
    else:
        argv.extend(("--ro-bind", "/dev/null", path.as_posix()))


def _append_allowed_read_mount(
    argv: list[str],
    path: Path,
    *,
    writable_roots: tuple[Path, ...],
    deny_write: tuple[Path, ...],
) -> None:
    writable = any(_contains(root, path) for root in writable_roots) and not any(
        _contains(blocked, path) for blocked in deny_write
    )
    argv.extend(
        (
            "--bind" if writable else "--ro-bind",
            path.as_posix(),
            path.as_posix(),
        )
    )
    for root in sorted(
        (root for root in writable_roots if _contains(path, root)),
        key=lambda item: len(item.parts),
    ):
        argv.extend(("--bind", root.as_posix(), root.as_posix()))
    for blocked in sorted(
        (blocked for blocked in deny_write if _contains(path, blocked)),
        key=lambda item: len(item.parts),
    ):
        argv.extend(("--ro-bind", blocked.as_posix(), blocked.as_posix()))


def _contains(parent: Path, child: Path) -> bool:
    return parent == child or child.is_relative_to(parent)


__all__ = ["append_sandbox_read_mounts"]
