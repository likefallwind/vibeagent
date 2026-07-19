from __future__ import annotations

import re
import shlex
from pathlib import Path

from .workspace_core import JS_TEST_SUFFIXES
from .workspace_file_read import read_utf8_text_file
from .workspace_project_info import missing_command_tool, read_package_json_scripts


def add_focused_test_commands_for_file(
    commands: list[dict[str, object]],
    root: Path,
    files: list[str],
    test_path: str,
    source: str,
    candidate_reason: str,
    pytest_evidence: bool,
) -> None:
    path = Path(test_path)
    suffix = path.suffix.lower()
    quoted_test_path = shlex.quote(test_path)
    if suffix == ".py":
        if pytest_evidence:
            add_focused_test_command(
                commands,
                command=f"python -m pytest {quoted_test_path}",
                cwd=".",
                test_path=test_path,
                source=source,
                reason=f"{candidate_reason} Pytest project evidence was found.",
            )
        test_dir = path.parent.as_posix()
        pattern = path.name
        if test_dir and test_dir != ".":
            command = (
                f"python -m unittest discover -s {shlex.quote(test_dir)} "
                f"-p {shlex.quote(pattern)}"
            )
        else:
            command = f"python -m unittest {path.with_suffix('').as_posix().replace('/', '.')}"
        add_focused_test_command(
            commands,
            command=command,
            cwd=".",
            test_path=test_path,
            source=source,
            reason=f"{candidate_reason} Python test file can be run through unittest discovery.",
        )
        return

    if suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        package_command = focused_npm_test_command(root, files, test_path)
        if package_command is not None:
            command, cwd = package_command
            add_focused_test_command(
                commands,
                command=command,
                cwd=cwd,
                test_path=test_path,
                source=source,
                reason=f"{candidate_reason} package.json defines a test script near this test file.",
            )


def add_focused_test_command(
    commands: list[dict[str, object]],
    command: str,
    cwd: str,
    test_path: str,
    source: str,
    reason: str,
) -> None:
    if any(item["command"] == command and item["cwd"] == cwd for item in commands):
        return
    missing_tool = missing_command_tool(command)
    commands.append(
        {
            "command": command,
            "cwd": cwd,
            "test_path": test_path,
            "source": source,
            "reason": reason,
            "available": missing_tool is None,
            "missing_tool": missing_tool,
        }
    )


def focused_npm_test_command(root: Path, files: list[str], test_path: str) -> tuple[str, str] | None:
    package_path = nearest_package_json(files, test_path)
    if package_path is None:
        return ("npm test -- " + shlex.quote(test_path), ".")
    package_file = root / package_path
    script_name = preferred_test_script_name(package_file)
    if script_name is None:
        return None
    cwd = package_path.parent.as_posix()
    if cwd == ".":
        cwd = "."
    relative_test = Path(test_path)
    if cwd != ".":
        try:
            relative_test = Path(test_path).relative_to(cwd)
        except ValueError:
            relative_test = Path(test_path)
    test_arg = shlex.quote(relative_test.as_posix())
    if script_name == "test":
        return (f"npm test -- {test_arg}", cwd)
    return (f"npm run {shlex.quote(script_name)} -- {test_arg}", cwd)


def nearest_package_json(files: list[str], test_path: str) -> Path | None:
    file_set = set(files)
    current = Path(test_path).parent
    for parent in [current, *current.parents]:
        package_path = parent / "package.json"
        package_text = package_path.as_posix()
        if package_text in file_set:
            return package_path
        if parent == Path("."):
            break
    return Path("package.json") if "package.json" in file_set else None


def preferred_test_script_name(package_json_path: Path) -> str | None:
    scripts = read_package_json_scripts(package_json_path)
    if any(name == "test" for name, _script in scripts):
        return "test"
    for name, _script in scripts:
        if name.startswith("test:") or name in {"tests", "unit", "unit-test"}:
            return name
    return None


def project_has_pytest_evidence(root: Path, files: list[str]) -> bool:
    evidence_names = {"pytest.ini", ".pytest.ini"}
    if any(Path(path).name in evidence_names for path in files):
        return True
    for relative in files:
        name = Path(relative).name.lower()
        if name not in {
            "pyproject.toml",
            "setup.cfg",
            "tox.ini",
            "requirements.txt",
            "requirements-dev.txt",
        }:
            continue
        try:
            content = read_utf8_text_file(root / relative, relative)
        except ValueError:
            continue
        if re.search(r"(^|[^A-Za-z0-9_-])pytest([^A-Za-z0-9_-]|$)", content):
            return True
    return False
