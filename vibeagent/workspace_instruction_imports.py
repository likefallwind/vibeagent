from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable

from .workspace_paths import is_protected_project_path


MAX_INSTRUCTION_IMPORT_DEPTH = 5
MAX_INSTRUCTION_IMPORTS = 50
MAX_TOTAL_INSTRUCTION_IMPORT_BYTES = 4_000_000
MAX_TOTAL_INSTRUCTION_IMPORTS = 100
_IMPORT_PATTERN = re.compile(r"(?<![\w@])@([^\s`<>(){}\[\],;:\"']+)")
_FENCE_PATTERN = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


@dataclass(frozen=True)
class InstructionImportSource:
    path: str
    parent_path: str
    content: str
    bytes: int
    chars: int
    error: str | None = None


@dataclass(frozen=True)
class InstructionImportResolution:
    content: str
    sources: tuple[InstructionImportSource, ...]


@dataclass
class InstructionImportBudget:
    remaining_files: int = MAX_TOTAL_INSTRUCTION_IMPORTS
    remaining_bytes: int = MAX_TOTAL_INSTRUCTION_IMPORT_BYTES

    def reserve(self, size: int) -> None:
        if self.remaining_files < 1:
            raise ValueError(f"Instruction discovery may import at most {MAX_TOTAL_INSTRUCTION_IMPORTS} files.")
        if size > self.remaining_bytes:
            raise ValueError(
                f"Instruction discovery imports may contain at most {MAX_TOTAL_INSTRUCTION_IMPORT_BYTES} bytes."
            )
        self.remaining_files -= 1
        self.remaining_bytes -= size


def resolve_instruction_imports(
    root: Path,
    source_path: Path,
    content: str,
    *,
    max_file_bytes: int,
    budget: InstructionImportBudget | None = None,
) -> InstructionImportResolution:
    resolver = _InstructionImportResolver(
        root=root.resolve(),
        max_file_bytes=max_file_bytes,
        budget=budget or InstructionImportBudget(),
    )
    expanded = resolver.expand(content, source_path.resolve(), depth=0, chain=(source_path.resolve(),))
    return InstructionImportResolution(content=expanded, sources=tuple(resolver.sources))


class _InstructionImportResolver:
    def __init__(self, *, root: Path, max_file_bytes: int, budget: InstructionImportBudget) -> None:
        self.root = root
        self.max_file_bytes = max_file_bytes
        self.budget = budget
        self.sources: list[InstructionImportSource] = []
        self._loaded: set[Path] = set()
        self._attempts = 0
        self._limit_reported = False
        self._seen_references: set[tuple[str, str]] = set()

    def expand(self, content: str, source_path: Path, *, depth: int, chain: tuple[Path, ...]) -> str:
        parent_path = self._display_path(source_path)

        def replace(reference: str) -> str:
            return self._load(reference, parent_path=parent_path, source_path=source_path, depth=depth + 1, chain=chain)

        return _transform_prose(content, replace)

    def _load(
        self,
        reference: str,
        *,
        parent_path: str,
        source_path: Path,
        depth: int,
        chain: tuple[Path, ...],
    ) -> str:
        requested = reference.rstrip(".!?")
        suffix = reference[len(requested):]
        if not requested:
            return "@" + reference
        reference_key = (parent_path, requested)
        if reference_key not in self._seen_references:
            if self._attempts >= MAX_INSTRUCTION_IMPORTS:
                error = ValueError(f"One instruction entrypoint may import at most {MAX_INSTRUCTION_IMPORTS} files.")
                if not self._limit_reported:
                    display_path = self._requested_display_path(requested, source_path)
                    self._record_error(display_path, parent_path, error)
                    self._limit_reported = True
                return f"[Instruction import skipped: @{requested} ({error})]{suffix}"
            self._seen_references.add(reference_key)
            self._attempts += 1
        try:
            target = self._resolve_target(requested, source_path)
            display_path = target.relative_to(self.root).as_posix()
            if depth > MAX_INSTRUCTION_IMPORT_DEPTH:
                raise ValueError(f"Instruction imports may be nested at most {MAX_INSTRUCTION_IMPORT_DEPTH} levels.")
            if target in chain:
                chain_text = " -> ".join(self._display_path(path) for path in (*chain, target))
                raise ValueError(f"Instruction import cycle detected: {chain_text}")
            if target in self._loaded:
                return suffix
            size = target.stat().st_size
            if size > self.max_file_bytes:
                raise ValueError(f"Instruction import exceeds {self.max_file_bytes} bytes.")
            self.budget.reserve(size)
            raw = target.read_text(encoding="utf-8")
            self._loaded.add(target)
            expanded = self.expand(raw, target, depth=depth, chain=(*chain, target))
            self.sources.append(
                InstructionImportSource(
                    path=display_path,
                    parent_path=parent_path,
                    content=expanded,
                    bytes=size,
                    chars=len(expanded),
                )
            )
            return f"\n[Imported instructions from {display_path}]\n{expanded}\n[End imported instructions]\n{suffix}"
        except (OSError, UnicodeError, ValueError) as error:
            display_path = self._requested_display_path(requested, source_path)
            self._record_error(display_path, parent_path, error)
            return f"[Instruction import skipped: @{requested} ({error})]{suffix}"

    def _record_error(self, display_path: str, parent_path: str, error: Exception) -> None:
        if any(source.path == display_path and source.parent_path == parent_path for source in self.sources):
            return
        self.sources.append(
            InstructionImportSource(
                path=display_path,
                parent_path=parent_path,
                content="",
                bytes=0,
                chars=0,
                error=str(error),
            )
        )

    def _resolve_target(self, reference: str, source_path: Path) -> Path:
        expanded = Path(reference).expanduser()
        candidate = expanded if expanded.is_absolute() else source_path.parent / expanded
        weak_target = candidate.resolve(strict=False)
        try:
            weak_target.relative_to(self.root)
        except ValueError as error:
            raise ValueError("Instruction import must stay within the project root.") from error
        target = candidate.resolve(strict=True)
        try:
            target.relative_to(self.root)
        except ValueError as error:
            raise ValueError("Instruction import must stay within the project root.") from error
        if is_protected_project_path(self.root, target):
            raise ValueError("Instruction import target is a protected project path.")
        if not target.is_file():
            raise ValueError("Instruction import target is not a regular file.")
        return target

    def _requested_display_path(self, reference: str, source_path: Path) -> str:
        candidate = Path(reference).expanduser()
        if not candidate.is_absolute():
            candidate = source_path.parent / candidate
        try:
            return candidate.resolve(strict=False).relative_to(self.root).as_posix()
        except ValueError:
            return reference

    def _display_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return str(path)


def _transform_prose(content: str, replace: Callable[[str], str]) -> str:
    output: list[str] = []
    in_fence: tuple[str, int] | None = None
    in_comment = False
    for line in content.splitlines(keepends=True):
        fence = _FENCE_PATTERN.match(line)
        if in_fence is not None:
            output.append(line)
            if fence is not None and fence.group(1)[0] == in_fence[0] and len(fence.group(1)) >= in_fence[1]:
                in_fence = None
            continue
        if fence is not None:
            marker = fence.group(1)
            in_fence = (marker[0], len(marker))
            output.append(line)
            continue
        uncommented, in_comment = _strip_html_comments(line, in_comment)
        output.append(_replace_outside_inline_code(uncommented, replace))
    return "".join(output)


def _strip_html_comments(line: str, in_comment: bool) -> tuple[str, bool]:
    output: list[str] = []
    index = 0
    while index < len(line):
        if in_comment:
            end = line.find("-->", index)
            if end < 0:
                return "".join(output), True
            index = end + 3
            in_comment = False
            continue
        start = line.find("<!--", index)
        if start < 0:
            output.append(line[index:])
            break
        output.append(line[index:start])
        index = start + 4
        in_comment = True
    return "".join(output), in_comment


def _replace_outside_inline_code(line: str, replace: Callable[[str], str]) -> str:
    output: list[str] = []
    prose_start = 0
    index = 0
    while index < len(line):
        if line[index] != "`":
            index += 1
            continue
        ticks = 1
        while index + ticks < len(line) and line[index + ticks] == "`":
            ticks += 1
        delimiter = "`" * ticks
        end = line.find(delimiter, index + ticks)
        if end < 0:
            break
        output.append(_replace_imports(line[prose_start:index], replace))
        output.append(line[index:end + ticks])
        index = end + ticks
        prose_start = index
    output.append(_replace_imports(line[prose_start:], replace))
    return "".join(output)


def _replace_imports(content: str, replace: Callable[[str], str]) -> str:
    return _IMPORT_PATTERN.sub(lambda match: replace(match.group(1)), content)


__all__ = [
    "InstructionImportResolution",
    "InstructionImportSource",
    "InstructionImportBudget",
    "MAX_INSTRUCTION_IMPORT_DEPTH",
    "MAX_INSTRUCTION_IMPORTS",
    "MAX_TOTAL_INSTRUCTION_IMPORT_BYTES",
    "MAX_TOTAL_INSTRUCTION_IMPORTS",
    "resolve_instruction_imports",
]
