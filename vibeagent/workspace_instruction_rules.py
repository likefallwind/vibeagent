from __future__ import annotations

from dataclasses import dataclass
import ast
from pathlib import Path, PurePosixPath
import re

from .workspace_core import PROJECT_INSTRUCTION_FILE_NAMES, RunWorkspace
from .workspace_search_files import list_files


RULES_RELATIVE_ROOT = Path(".claude") / "rules"
ROOT_INSTRUCTION_PATHS = (
    Path("AGENTS.md"),
    Path("CLAUDE.md"),
    Path(".claude") / "CLAUDE.md",
    Path("CLAUDE.local.md"),
)
MAX_INSTRUCTION_FILE_BYTES = 256_000
MAX_RULE_FILES = 200


@dataclass(frozen=True)
class InstructionDocument:
    path: str
    scope: str
    content: str
    bytes: int
    chars: int
    patterns: tuple[str, ...] = ()
    reason: str = "session_start"
    error: str | None = None

    @property
    def empty(self) -> bool:
        return not self.content.strip()


def discover_instruction_documents(workspace: RunWorkspace) -> list[InstructionDocument]:
    relative_paths: list[Path] = []
    seen: set[str] = set()
    for path in ROOT_INSTRUCTION_PATHS:
        _append_unique_path(relative_paths, seen, path)
    for path in _rule_paths(workspace.root):
        _append_unique_path(relative_paths, seen, path)
    for value in list_files(workspace.root):
        path = Path(value)
        if path.name in PROJECT_INSTRUCTION_FILE_NAMES and path not in ROOT_INSTRUCTION_PATHS:
            _append_unique_path(relative_paths, seen, path)

    documents: list[InstructionDocument] = []
    for relative in relative_paths:
        absolute = workspace.root / relative
        if not absolute.exists() and not absolute.is_symlink():
            continue
        documents.append(_read_instruction_document(workspace.root, relative))
    return sorted(documents, key=instruction_document_sort_key)


def discover_path_instruction_documents(
    workspace: RunWorkspace,
    relative_paths: list[str],
) -> list[InstructionDocument]:
    candidates: list[Path] = []
    seen: set[str] = set()
    for rule_path in _rule_paths(workspace.root):
        _append_unique_path(candidates, seen, rule_path)
    for value in relative_paths:
        normalized = PurePosixPath(_normalize_target_path(value))
        current = PurePosixPath()
        for part in normalized.parent.parts:
            current = current / part
            if current == PurePosixPath("."):
                continue
            for name in PROJECT_INSTRUCTION_FILE_NAMES:
                candidate = Path(current.as_posix()) / name
                absolute = workspace.root / candidate
                if absolute.exists() or absolute.is_symlink():
                    _append_unique_path(candidates, seen, candidate)
    documents = [_read_instruction_document(workspace.root, path) for path in candidates]
    return sorted(documents, key=instruction_document_sort_key)


def startup_instruction_documents(documents: list[InstructionDocument]) -> list[InstructionDocument]:
    return [document for document in documents if _is_startup_document(document)]


def matching_instruction_documents(
    documents: list[InstructionDocument],
    relative_paths: list[str],
) -> list[InstructionDocument]:
    normalized = [_normalize_target_path(path) for path in relative_paths]
    matches: list[InstructionDocument] = []
    for document in documents:
        if document.error is not None or document.empty or _is_startup_document(document):
            continue
        if document.patterns:
            if any(rule_pattern_matches(pattern, path) for pattern in document.patterns for path in normalized):
                matches.append(document)
            continue
        if document.scope != "." and any(path_is_in_scope(path, document.scope) for path in normalized):
            matches.append(document)
    return matches


def instruction_document_sort_key(document: InstructionDocument) -> tuple[int, int, str]:
    path = PurePosixPath(document.path)
    root_order = {item.as_posix(): index for index, item in enumerate(ROOT_INSTRUCTION_PATHS)}
    if document.path in root_order:
        return 0, root_order[document.path], document.path
    if document.path.startswith(f"{RULES_RELATIVE_ROOT.as_posix()}/"):
        return 1, len(path.parts), document.path
    return 2, len(path.parts), document.path


def path_is_in_scope(relative_path: str, scope: str) -> bool:
    return relative_path == scope or relative_path.startswith(f"{scope}/")


def rule_pattern_matches(pattern: str, relative_path: str) -> bool:
    return any(re.fullmatch(_glob_regex(expanded), relative_path) is not None for expanded in _expand_braces(pattern))


def _read_instruction_document(root: Path, relative: Path) -> InstructionDocument:
    path_text = relative.as_posix()
    scope = _instruction_scope(relative)
    absolute = root / relative
    try:
        resolved = absolute.resolve(strict=True)
        resolved.relative_to(root.resolve())
        if not resolved.is_file():
            raise ValueError("Instruction path is not a regular file.")
        size = resolved.stat().st_size
        if size > MAX_INSTRUCTION_FILE_BYTES:
            raise ValueError(f"Instruction file exceeds {MAX_INSTRUCTION_FILE_BYTES} bytes.")
        raw = resolved.read_text(encoding="utf-8")
        patterns, content = parse_rule_frontmatter(raw) if _is_rule_path(relative) else ((), raw)
        reason = "path_glob_match" if patterns else "session_start" if _is_root_or_rule(relative) else "nested_traversal"
        return InstructionDocument(
            path=path_text,
            scope=scope,
            content=content,
            bytes=size,
            chars=len(content),
            patterns=patterns,
            reason=reason,
        )
    except (OSError, UnicodeError, ValueError) as error:
        return InstructionDocument(
            path=path_text,
            scope=scope,
            content="",
            bytes=absolute.lstat().st_size if absolute.exists() or absolute.is_symlink() else 0,
            chars=0,
            reason="path_glob_match" if _is_rule_path(relative) else "nested_traversal",
            error=str(error),
        )


def parse_rule_frontmatter(content: str) -> tuple[tuple[str, ...], str]:
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return (), content
    closing = next((index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
    if closing is None:
        raise ValueError("Rule frontmatter is missing its closing --- delimiter.")
    metadata_lines = lines[1:closing]
    paths: list[str] = []
    in_paths = False
    for raw_line in metadata_lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("paths:"):
            in_paths = True
            inline = stripped.removeprefix("paths:").strip()
            if inline:
                paths.extend(_parse_inline_paths(inline))
            continue
        if in_paths and stripped.startswith("-"):
            paths.append(_unquote_scalar(stripped[1:].strip()))
            continue
        in_paths = False
    normalized = tuple(_validate_rule_pattern(path) for path in paths)
    return tuple(dict.fromkeys(normalized)), "".join(lines[closing + 1:])


def _parse_inline_paths(value: str) -> list[str]:
    if value.startswith("["):
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError) as error:
            raise ValueError("Rule paths inline list is invalid.") from error
        if not isinstance(parsed, (list, tuple)) or not all(isinstance(item, str) for item in parsed):
            raise ValueError("Rule paths must be a list of strings.")
        return list(parsed)
    return [_unquote_scalar(value)]


def _unquote_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _validate_rule_pattern(value: str) -> str:
    pattern = value.strip().replace("\\", "/")
    if not pattern or pattern.startswith("/") or ".." in PurePosixPath(pattern).parts:
        raise ValueError(f"Rule path pattern must stay project-relative: {value}")
    if len(pattern) > 500:
        raise ValueError("Rule path pattern must contain at most 500 characters.")
    return pattern


def _glob_regex(pattern: str) -> str:
    pieces: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            pieces.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            pieces.append(".*")
            index += 2
        elif pattern[index] == "*":
            pieces.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            pieces.append("[^/]")
            index += 1
        else:
            pieces.append(re.escape(pattern[index]))
            index += 1
    return "".join(pieces)


def _expand_braces(pattern: str) -> tuple[str, ...]:
    match = re.search(r"\{([^{}]+)\}", pattern)
    if match is None:
        return (pattern,)
    values: list[str] = []
    for option in match.group(1).split(","):
        replacement = pattern[:match.start()] + option + pattern[match.end():]
        values.extend(_expand_braces(replacement))
    return tuple(values)


def _normalize_target_path(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Instruction target path must stay project-relative: {value}")
    return path.as_posix().removeprefix("./")


def _rule_paths(root: Path) -> list[Path]:
    rules_root = root / RULES_RELATIVE_ROOT
    if not rules_root.exists() or not rules_root.is_dir() or rules_root.is_symlink():
        return []
    paths: list[Path] = []
    for path in rules_root.rglob("*.md"):
        if len(paths) >= MAX_RULE_FILES:
            break
        paths.append(path.relative_to(root))
    return sorted(paths, key=lambda item: item.as_posix())


def _append_unique_path(paths: list[Path], seen: set[str], path: Path) -> None:
    key = path.as_posix()
    if key not in seen:
        paths.append(path)
        seen.add(key)


def _instruction_scope(path: Path) -> str:
    if _is_rule_path(path) or path == Path(".claude") / "CLAUDE.md":
        return "."
    parent = path.parent.as_posix()
    return "." if parent == "." else parent


def _is_rule_path(path: Path) -> bool:
    return path.parts[:2] == RULES_RELATIVE_ROOT.parts


def _is_root_or_rule(path: Path) -> bool:
    return path in ROOT_INSTRUCTION_PATHS or _is_rule_path(path)


def _is_startup_document(document: InstructionDocument) -> bool:
    return document.error is None and not document.empty and document.reason == "session_start"
