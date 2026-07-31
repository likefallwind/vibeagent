from __future__ import annotations


def normalize_preview_path(path: str) -> str:
    parts: list[str] = []
    for part in path.replace("\\", "/").split("/"):
        if not part or part == ".":
            continue
        if part == ".." and parts and parts[-1] != "..":
            parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def paths_overlap_or_nested(left: frozenset[str], right: frozenset[str]) -> bool:
    for left_path in left:
        normalized_left = normalize_preview_path(left_path)
        if not normalized_left:
            continue
        for right_path in right:
            normalized_right = normalize_preview_path(right_path)
            if not normalized_right:
                continue
            if (
                normalized_left == normalized_right
                or normalized_left.startswith(f"{normalized_right}/")
                or normalized_right.startswith(f"{normalized_left}/")
            ):
                return True
    return False


def preview_path_value(path: object, default: object = "") -> object:
    if not isinstance(path, str):
        return default
    normalized = normalize_preview_path(path)
    return normalized if normalized else "."


def preview_path_attr(value: object, attr: str = "path") -> object:
    return preview_path_value(getattr(value, attr, ""))


def preview_optional_path_attr(value: object, attr: str = "path") -> object:
    raw_path = getattr(value, attr, None)
    if raw_path is None:
        return None
    return preview_path_value(raw_path, None)


def preview_path_tuple(paths: object) -> tuple[object, ...]:
    return tuple(preview_path_value(path, path) for path in paths or [])


def preview_cwd_value(cwd: object) -> object:
    return preview_path_value(cwd or ".", ".")
