from __future__ import annotations

import hashlib
import json

from .agent_observation_utils import summarize
from .agent_preview_paths import preview_cwd_value, preview_path_attr


def summarize_preview_observation(observation: object) -> str:
    message = getattr(observation, "message", "")
    parts = [summarize(message, 160) if isinstance(message, str) and message.strip() else "Matching preview completed."]
    diff = getattr(observation, "diff", None)
    if isinstance(diff, str) and diff:
        parts.append(f"diffChars={len(diff)}")
        parts.append(f"diffSha256={preview_digest(diff)}")
    checks = getattr(observation, "checks", None)
    if isinstance(checks, list):
        parts.append(f"commands={len(checks)}")
        if checks:
            parts.append(f"commandsSha256={preview_digest(command_check_fingerprint_payload(checks))}")
    file_diffs = preview_file_diffs(getattr(observation, "files", None))
    if file_diffs:
        parts.append(f"fileDiffs={len(file_diffs)}")
        parts.append(f"fileDiffsSha256={preview_digest(file_diff_fingerprint_payload(file_diffs))}")
    return "; ".join(parts)


def preview_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def command_check_fingerprint_payload(checks: list[object]) -> str:
    payload = [
        {
            "command": str(getattr(check, "command", "") or ""),
            "cwd": str(preview_cwd_value(getattr(check, "cwd", None))),
            "ok": bool(getattr(check, "ok", False)),
            "blocked": bool(getattr(check, "blocked", False)),
            "missing_tool": getattr(check, "missing_tool", None),
        }
        for check in checks
    ]
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def preview_file_diffs(files: object) -> list[object]:
    if not isinstance(files, list):
        return []
    return [file for file in files if isinstance(getattr(file, "diff", None), str) and getattr(file, "diff")]


def file_diff_fingerprint_payload(files: list[object]) -> str:
    payload = [
        {
            "path": str(preview_path_attr(file)),
            "diff": str(getattr(file, "diff", "") or ""),
            "truncated": bool(getattr(file, "truncated", False)),
        }
        for file in files
    ]
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
