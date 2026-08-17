from __future__ import annotations

from dataclasses import dataclass, field
import re


MAX_GIT_DIFF_HUNK_LINE_CHARS = 4_000
MAX_GIT_DIFF_PARSE_LINE_CHARS = 16_384
MAX_GIT_DIFF_HUNK_RETAINED_CHARS = 1_000_000


@dataclass
class StreamingGitDiffHunkParser:
    max_hunks: int = 80
    max_lines_per_hunk: int = 80
    max_line_chars: int = MAX_GIT_DIFF_HUNK_LINE_CHARS
    max_parse_line_chars: int = MAX_GIT_DIFF_PARSE_LINE_CHARS
    max_retained_chars: int = MAX_GIT_DIFF_HUNK_RETAINED_CHARS
    hunks: list[dict[str, object]] = field(default_factory=list, init=False)
    total_hunks: int = field(default=0, init=False)
    _current_file: str = field(default="", init=False, repr=False)
    _current_hunk: dict[str, object] | None = field(default=None, init=False, repr=False)
    _current_lines: list[str] = field(default_factory=list, init=False, repr=False)
    _current_lines_truncated: bool = field(default=False, init=False, repr=False)
    _retained_chars: int = field(default=0, init=False, repr=False)
    _line_buffer: str = field(default="", init=False, repr=False)
    _line_overflow: bool = field(default=False, init=False, repr=False)
    _structure_truncated: bool = field(default=False, init=False, repr=False)
    _finished: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.max_hunks < 1 or self.max_lines_per_hunk < 1:
            raise ValueError("Git diff hunk limits must be positive.")
        if self.max_line_chars < 1 or self.max_parse_line_chars < 1 or self.max_retained_chars < 1:
            raise ValueError("Git diff character limits must be positive.")

    def append(self, chunk: str) -> None:
        if self._finished:
            raise RuntimeError("Cannot append to a finished Git diff parser.")
        offset = 0
        while offset < len(chunk):
            newline = chunk.find("\n", offset)
            end = len(chunk) if newline < 0 else newline
            self._append_line_fragment(chunk[offset:end])
            if newline < 0:
                return
            self._finish_line()
            offset = newline + 1

    def finish(self) -> dict[str, object]:
        if not self._finished:
            if self._line_buffer or self._line_overflow:
                self._finish_line()
            self._finish_hunk()
            self._finished = True
        return {
            "hunks": self.hunks,
            "total_hunks": self.total_hunks,
            "truncated": self._structure_truncated
            or self.total_hunks > len(self.hunks)
            or any(bool(hunk["lines_truncated"]) for hunk in self.hunks),
        }

    def _append_line_fragment(self, fragment: str) -> None:
        remaining = self.max_parse_line_chars - len(self._line_buffer)
        if remaining > 0:
            self._line_buffer += fragment[:remaining]
        if len(fragment) > remaining:
            self._line_overflow = True

    def _finish_line(self) -> None:
        line = self._line_buffer[:-1] if self._line_buffer.endswith("\r") else self._line_buffer
        line_truncated = self._line_overflow
        self._line_buffer = ""
        self._line_overflow = False
        self._consume_line(line, line_truncated=line_truncated)

    def _consume_line(self, line: str, *, line_truncated: bool) -> None:
        if line.startswith("diff --git "):
            self._finish_hunk()
            self._current_file = parse_git_diff_file_path(line)
            self._structure_truncated = self._structure_truncated or line_truncated
            return

        hunk_match = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if hunk_match:
            self._finish_hunk()
            self.total_hunks += 1
            if self.total_hunks > self.max_hunks:
                return
            self._current_hunk = {
                "file": self._current_file,
                "old_start": int(hunk_match.group(1)),
                "old_count": int(hunk_match.group(2) or "1"),
                "new_start": int(hunk_match.group(3)),
                "new_count": int(hunk_match.group(4) or "1"),
                "added": 0,
                "deleted": 0,
                "context": 0,
                "header": line,
            }
            self._current_lines = []
            self._current_lines_truncated = line_truncated
            return

        if self._current_hunk is None:
            return
        if line.startswith("+") and not line.startswith("+++"):
            self._current_hunk["added"] = int(self._current_hunk["added"]) + 1
        elif line.startswith("-") and not line.startswith("---"):
            self._current_hunk["deleted"] = int(self._current_hunk["deleted"]) + 1
        elif line.startswith(" "):
            self._current_hunk["context"] = int(self._current_hunk["context"]) + 1
        self._retain_line(line, line_truncated=line_truncated)

    def _retain_line(self, line: str, *, line_truncated: bool) -> None:
        if len(self._current_lines) >= self.max_lines_per_hunk:
            self._current_lines_truncated = True
            return
        remaining = self.max_retained_chars - self._retained_chars
        if remaining <= 0:
            self._current_lines_truncated = True
            return
        retained = line[: min(remaining, self.max_line_chars)]
        self._current_lines.append(retained)
        self._retained_chars += len(retained)
        if line_truncated or len(retained) < len(line):
            self._current_lines_truncated = True

    def _finish_hunk(self) -> None:
        if self._current_hunk is None:
            return
        self._current_hunk["lines"] = self._current_lines
        self._current_hunk["lines_truncated"] = self._current_lines_truncated
        self.hunks.append(self._current_hunk)
        self._current_hunk = None
        self._current_lines = []
        self._current_lines_truncated = False


def parse_git_diff_hunks(
    diff: str,
    max_hunks: int = 80,
    max_lines_per_hunk: int = 80,
) -> dict[str, object]:
    parser = StreamingGitDiffHunkParser(
        max_hunks=max_hunks,
        max_lines_per_hunk=max_lines_per_hunk,
    )
    parser.append(diff)
    return parser.finish()


def parse_git_diff_file_path(line: str) -> str:
    match = re.match(r"^diff --git a/(.*?) b/(.*)$", line)
    if not match:
        return ""
    return match.group(2)


__all__ = [
    "MAX_GIT_DIFF_HUNK_LINE_CHARS",
    "MAX_GIT_DIFF_HUNK_RETAINED_CHARS",
    "MAX_GIT_DIFF_PARSE_LINE_CHARS",
    "StreamingGitDiffHunkParser",
    "parse_git_diff_file_path",
    "parse_git_diff_hunks",
]
