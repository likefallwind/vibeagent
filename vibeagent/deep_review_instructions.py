from __future__ import annotations

from dataclasses import dataclass

from .workspace_core import RunWorkspace
from .workspace_metadata_files import read_regular_file_bytes


MAX_REVIEW_INSTRUCTION_BYTES = 20_000


@dataclass(frozen=True)
class ReviewInstructions:
    path: str | None = None
    content: str = ""
    error: str | None = None


def read_review_instructions(workspace: RunWorkspace) -> ReviewInstructions:
    path = workspace.root / "REVIEW.md"
    if not path.exists() and not path.is_symlink():
        return ReviewInstructions()
    if path.is_symlink():
        return ReviewInstructions(path="REVIEW.md", error="REVIEW.md must be a regular file.")
    try:
        data = read_regular_file_bytes(
            path,
            max_bytes=MAX_REVIEW_INSTRUCTION_BYTES,
            label="REVIEW.md",
        )
    except (OSError, ValueError) as error:
        return ReviewInstructions(path="REVIEW.md", error=f"Could not read REVIEW.md: {error}")
    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        return ReviewInstructions(path="REVIEW.md", error="REVIEW.md must be valid UTF-8.")
    return ReviewInstructions(path="REVIEW.md", content=content.strip())


__all__ = [
    "MAX_REVIEW_INSTRUCTION_BYTES",
    "ReviewInstructions",
    "read_review_instructions",
]
