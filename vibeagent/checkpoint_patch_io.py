from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import tempfile
import time

from .process_termination import terminate_process


CHECKPOINT_GIT_TIMEOUT_MS = 120_000
MAX_CHECKPOINT_PATCH_BYTES = 1_073_741_824
MAX_CHECKPOINT_DIAGNOSTIC_BYTES = 1_048_576
MAX_CHECKPOINT_DIAGNOSTIC_CHARS = 64_000
MAX_CHECKPOINT_STATUS_CHARS = 8_000_000
PATCH_IO_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class CheckpointPatchResult:
    ok: bool
    chars: int
    stderr: str
    exit_code: int | None


@dataclass(frozen=True)
class CheckpointPatchSetResult:
    ok: bool
    staged_chars: int
    unstaged_chars: int
    error: str


@dataclass(frozen=True)
class CheckpointPatchComparison:
    ok: bool
    staged_matches: bool
    unstaged_matches: bool
    staged_chars: int
    unstaged_chars: int
    error: str


def capture_checkpoint_diff(root: Path, destination: Path, *, staged: bool) -> CheckpointPatchResult:
    args = ["git", "diff", "--binary"]
    if staged:
        args.append("--cached")
    return capture_git_stdout_file(root, args, destination)


def capture_checkpoint_patches(root: Path, destination: Path) -> CheckpointPatchSetResult:
    staged = capture_checkpoint_diff(root, destination / "staged.patch", staged=True)
    if not staged.ok:
        return CheckpointPatchSetResult(False, 0, 0, staged.stderr or "git diff --staged failed.")
    unstaged = capture_checkpoint_diff(root, destination / "unstaged.patch", staged=False)
    if not unstaged.ok:
        return CheckpointPatchSetResult(False, 0, 0, unstaged.stderr or "git diff failed.")
    return CheckpointPatchSetResult(True, staged.chars, unstaged.chars, "")


def compare_checkpoint_patches(
    root: Path,
    saved_staged: Path | None,
    saved_unstaged: Path | None,
) -> CheckpointPatchComparison:
    with tempfile.TemporaryDirectory(prefix="vibeagent-checkpoint-status-") as temporary:
        temporary_root = Path(temporary)
        patches = capture_checkpoint_patches(root, temporary_root)
        if not patches.ok:
            return CheckpointPatchComparison(False, False, False, 0, 0, patches.error)
        return CheckpointPatchComparison(
            ok=True,
            staged_matches=checkpoint_patch_files_equal(temporary_root / "staged.patch", saved_staged),
            unstaged_matches=checkpoint_patch_files_equal(temporary_root / "unstaged.patch", saved_unstaged),
            staged_chars=patches.staged_chars,
            unstaged_chars=patches.unstaged_chars,
            error="",
        )


def capture_git_stdout_file(root: Path, args: list[str], destination: Path) -> CheckpointPatchResult:
    destination.parent.mkdir(parents=True, exist_ok=True)
    output_path: Path | None = None
    error_path: Path | None = None
    process: subprocess.Popen[bytes] | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.name}.",
            dir=destination.parent,
            delete=False,
        ) as output:
            output_path = Path(output.name)
        with tempfile.NamedTemporaryFile(prefix=".git-stderr.", dir=destination.parent, delete=False) as error:
            error_path = Path(error.name)
        with output_path.open("wb") as output, error_path.open("wb") as error:
            process = subprocess.Popen(
                args,
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=error,
                start_new_session=os.name != "nt",
            )
            failure = _wait_for_file_capture(process, output_path, error_path)
        if failure:
            return CheckpointPatchResult(False, 0, failure, process.returncode)
        stderr = _read_bounded_text(error_path, MAX_CHECKPOINT_DIAGNOSTIC_CHARS)
        if process.returncode != 0:
            return CheckpointPatchResult(False, 0, stderr or "git command failed.", process.returncode)
        try:
            chars = count_utf8_file_chars(output_path)
        except UnicodeDecodeError:
            return CheckpointPatchResult(False, 0, "git output was not valid UTF-8.", process.returncode)
        os.replace(output_path, destination)
        output_path = None
        return CheckpointPatchResult(True, chars, stderr, process.returncode)
    except FileNotFoundError:
        return CheckpointPatchResult(False, 0, "git executable was not found.", None)
    except OSError as error:
        return CheckpointPatchResult(False, 0, f"Failed to capture git output: {error}", None)
    finally:
        if process is not None and process.poll() is None:
            terminate_process(process)
        for path in (output_path, error_path):
            if path is not None:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass


def checkpoint_patch_files_equal(first: Path | None, second: Path | None) -> bool:
    if first is None:
        return second is None or _file_size(second) == 0
    if second is None:
        return _file_size(first) == 0
    try:
        if first.stat().st_size != second.stat().st_size:
            return False
        with first.open("rb") as left, second.open("rb") as right:
            while True:
                left_chunk = left.read(PATCH_IO_CHUNK_SIZE)
                right_chunk = right.read(PATCH_IO_CHUNK_SIZE)
                if left_chunk != right_chunk:
                    return False
                if not left_chunk:
                    return True
    except OSError:
        return False


def read_checkpoint_patch_excerpt(path: Path | None, max_chars: int) -> tuple[str, int, bool]:
    if path is None:
        return "", 0, False
    total = 0
    shown_parts: list[str] = []
    shown_chars = 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            while True:
                chunk = handle.read(PATCH_IO_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if shown_chars < max_chars:
                    retained = chunk[: max_chars - shown_chars]
                    shown_parts.append(retained)
                    shown_chars += len(retained)
    except (OSError, UnicodeDecodeError):
        return "", 0, False
    return "".join(shown_parts), total, total > max_chars


def count_utf8_file_chars(path: Path) -> int:
    total = 0
    with path.open("r", encoding="utf-8") as handle:
        while True:
            chunk = handle.read(PATCH_IO_CHUNK_SIZE)
            if not chunk:
                return total
            total += len(chunk)


def _wait_for_file_capture(process: subprocess.Popen[bytes], output_path: Path, error_path: Path) -> str | None:
    deadline = time.monotonic() + CHECKPOINT_GIT_TIMEOUT_MS / 1000
    while process.poll() is None:
        if time.monotonic() >= deadline:
            terminate_process(process)
            return "git command timed out."
        if _file_size(output_path) > MAX_CHECKPOINT_PATCH_BYTES:
            terminate_process(process)
            return f"git patch output exceeded {MAX_CHECKPOINT_PATCH_BYTES} bytes."
        if _file_size(error_path) > MAX_CHECKPOINT_DIAGNOSTIC_BYTES:
            terminate_process(process)
            return f"git diagnostic output exceeded {MAX_CHECKPOINT_DIAGNOSTIC_BYTES} bytes."
        time.sleep(0.01)
    if _file_size(output_path) > MAX_CHECKPOINT_PATCH_BYTES:
        return f"git patch output exceeded {MAX_CHECKPOINT_PATCH_BYTES} bytes."
    if _file_size(error_path) > MAX_CHECKPOINT_DIAGNOSTIC_BYTES:
        return f"git diagnostic output exceeded {MAX_CHECKPOINT_DIAGNOSTIC_BYTES} bytes."
    return None


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _read_bounded_text(path: Path, max_chars: int) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(max_chars)
    except OSError:
        return ""


__all__ = [
    "CHECKPOINT_GIT_TIMEOUT_MS",
    "MAX_CHECKPOINT_DIAGNOSTIC_BYTES",
    "MAX_CHECKPOINT_DIAGNOSTIC_CHARS",
    "MAX_CHECKPOINT_PATCH_BYTES",
    "MAX_CHECKPOINT_STATUS_CHARS",
    "CheckpointPatchResult",
    "CheckpointPatchSetResult",
    "CheckpointPatchComparison",
    "capture_checkpoint_diff",
    "capture_checkpoint_patches",
    "capture_git_stdout_file",
    "checkpoint_patch_files_equal",
    "compare_checkpoint_patches",
    "count_utf8_file_chars",
    "read_checkpoint_patch_excerpt",
]
