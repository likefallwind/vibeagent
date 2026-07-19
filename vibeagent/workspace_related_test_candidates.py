from __future__ import annotations

from pathlib import Path

from .workspace_core import JS_TEST_SUFFIXES, TEST_FILE_SUFFIXES


def is_project_test_file(path: str) -> bool:
    relative = Path(path)
    name = relative.name
    lower_name = name.lower()
    if relative.suffix.lower() not in TEST_FILE_SUFFIXES:
        return False
    if lower_name.startswith("test_") or lower_name.endswith("_test.py"):
        return True
    if any(part in {"tests", "test", "__tests__"} for part in relative.parts):
        return True
    stem = relative.with_suffix("").name.lower()
    return stem.endswith(JS_TEST_SUFFIXES)


def related_test_candidates_for_target(
    target: str,
    test_files: list[str],
) -> list[tuple[str, str, int]]:
    if is_project_test_file(target):
        return [(target, "Target path is itself a test file.", 100)] if target in test_files else []

    target_path = Path(target)
    source_stem = source_module_stem(target_path)
    if not source_stem:
        return []

    candidates: list[tuple[str, str, int]] = []
    expected_names = expected_test_names(target_path, source_stem)
    expected_paths = expected_test_paths(target_path, source_stem)
    source_parts = set(target_path.with_suffix("").parts)
    for test_file in test_files:
        test_path = Path(test_file)
        test_name = test_path.name
        test_stem = normalized_test_stem(test_path)
        if test_file in expected_paths:
            candidates.append((test_file, "Test path mirrors the source path.", 95))
        elif test_name in expected_names:
            candidates.append(
                (test_file, f"Test filename matches {target_path.name}.", 90)
            )
        elif test_stem == source_stem:
            candidates.append(
                (test_file, f"Test stem matches source stem {source_stem}.", 80)
            )
        elif source_stem in test_stem.split("_"):
            candidates.append((test_file, f"Test stem contains source stem {source_stem}.", 65))
        elif source_stem and source_stem in test_stem:
            candidates.append((test_file, f"Test name contains source stem {source_stem}.", 55))
        elif source_parts and source_parts.intersection(test_path.with_suffix("").parts):
            candidates.append((test_file, "Test path shares a source path component.", 35))
    return candidates


def source_module_stem(path: Path) -> str:
    if path.stem == "__init__":
        return path.parent.name
    return path.stem


def normalized_test_stem(path: Path) -> str:
    stem = path.with_suffix("").name
    for suffix in JS_TEST_SUFFIXES:
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    if stem.startswith("test_"):
        stem = stem[5:]
    if stem.endswith("_test"):
        stem = stem[:-5]
    return stem


def expected_test_names(path: Path, source_stem: str) -> set[str]:
    suffix = path.suffix
    if suffix == ".py":
        return {f"test_{source_stem}.py", f"{source_stem}_test.py"}
    if suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        return {f"{source_stem}.test{suffix}", f"{source_stem}.spec{suffix}"}
    return {f"test_{source_stem}{suffix}", f"{source_stem}_test{suffix}"}


def expected_test_paths(path: Path, source_stem: str) -> set[str]:
    expected: set[str] = set()
    parent = path.parent
    for name in expected_test_names(path, source_stem):
        expected.add((parent / name).as_posix())
        expected.add((parent / "__tests__" / name).as_posix())
        expected.add((Path("tests") / name).as_posix())
        if len(path.parts) > 1:
            expected.add((Path("tests") / Path(*path.parts[1:]).parent / name).as_posix())
    return expected


def related_test_candidate_sort_key(item: dict[str, object]) -> tuple[str, int, str]:
    return (str(item["source_path"]), -int(item["score"]), str(item["test_path"]))
