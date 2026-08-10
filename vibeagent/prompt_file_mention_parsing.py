from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .workspace_core import RunWorkspace
from .workspace_resolve import resolve_inside_run


MAX_PROMPT_FILE_MENTIONS = 10
MAX_PROMPT_FILE_RANGE_LINES = 1_000
MENTION_RE = re.compile(
    r"(?<![\w@])@(?:\"(?P<double>[^\"\r\n]+)\"|'(?P<single>[^'\r\n]+)'|(?P<plain>[^\s]+))"
    r"(?P<suffix>#[^\s]+)?"
)
LINE_SELECTOR_RE = re.compile(r"#L?(?P<start>\d+)(?:-L?(?P<end>\d+))?", re.IGNORECASE)


@dataclass(frozen=True)
class PromptFileMention:
    path: str
    start_line: int | None = None
    end_line: int | None = None

    @property
    def reference(self) -> str:
        if self.start_line is None or self.end_line is None:
            return self.path
        return f"{self.path}#{self.start_line}-{self.end_line}"


def find_prompt_file_mentions(task: str, workspace: RunWorkspace) -> tuple[str, ...]:
    return tuple(mention.reference for mention in parse_prompt_file_mentions(task, workspace))


def parse_prompt_file_mentions(task: str, workspace: RunWorkspace) -> tuple[PromptFileMention, ...]:
    selected: list[PromptFileMention] = []
    seen: set[tuple[str, int | None, int | None]] = set()
    for match in MENTION_RE.finditer(task):
        quoted = match.group("double") is not None or match.group("single") is not None
        raw = match.group("double") or match.group("single") or match.group("plain") or ""
        suffix = _clean_selector_suffix(match.group("suffix") or "") if quoted else ""
        candidate = raw.strip() if quoted else _clean_plain_mention(raw)
        candidate = f"{candidate}{suffix}"
        if not candidate or "://" in candidate:
            continue
        normalized = _normalize_mention(candidate)
        mention = _parse_file_mention(normalized, workspace, quoted=quoted)
        if not _looks_like_file_mention(mention.path, workspace.root, quoted=quoted):
            continue
        key = (mention.path, mention.start_line, mention.end_line)
        if key in seen:
            continue
        seen.add(key)
        selected.append(mention)
    if len(selected) > MAX_PROMPT_FILE_MENTIONS:
        raise ValueError(
            f"Too many @file mentions ({len(selected)} > {MAX_PROMPT_FILE_MENTIONS})."
        )
    return tuple(selected)


def _parse_file_mention(value: str, workspace: RunWorkspace, *, quoted: bool) -> PromptFileMention:
    root = workspace.root
    if _safe_candidate_exists(workspace, value):
        return PromptFileMention(value)
    path, separator, selector = value.rpartition("#")
    if not separator:
        return PromptFileMention(value)
    match = LINE_SELECTOR_RE.fullmatch(f"#{selector}")
    if match is None:
        if _looks_like_file_mention(path, root, quoted=quoted):
            raise ValueError(f"Invalid line selector in @{value}.")
        return PromptFileMention(value)

    start_line = int(match.group("start"))
    end_line = int(match.group("end") or match.group("start"))
    if start_line < 1:
        raise ValueError("Prompt file line range must start at line 1 or later.")
    if end_line < start_line:
        raise ValueError("Prompt file line range end must be greater than or equal to its start.")
    if end_line - start_line + 1 > MAX_PROMPT_FILE_RANGE_LINES:
        raise ValueError(
            f"Prompt file line range must contain at most {MAX_PROMPT_FILE_RANGE_LINES} lines."
        )
    return PromptFileMention(path=path, start_line=start_line, end_line=end_line)


def _safe_candidate_exists(workspace: RunWorkspace, value: str) -> bool:
    try:
        return resolve_inside_run(workspace, value).exists()
    except (OSError, ValueError):
        return False


def _clean_selector_suffix(value: str) -> str:
    return value.rstrip(".,;:!?)]}")


def _clean_plain_mention(value: str) -> str:
    return value.strip().strip("`").rstrip(".,;:!?)]}")


def _normalize_mention(value: str) -> str:
    normalized = value.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _looks_like_file_mention(value: str, root: Path, *, quoted: bool) -> bool:
    if quoted or value.startswith(("/", ".")):
        return True
    candidate = root / value
    if candidate.exists() or candidate.is_symlink():
        return True
    path = Path(value)
    if path.suffix:
        return True
    if len(path.parts) > 1 and (root / path.parts[0]).exists():
        return True
    return False


__all__ = [
    "MAX_PROMPT_FILE_MENTIONS",
    "MAX_PROMPT_FILE_RANGE_LINES",
    "PromptFileMention",
    "find_prompt_file_mentions",
    "parse_prompt_file_mentions",
]
