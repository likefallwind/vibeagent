from __future__ import annotations

import re

from .workspace_core import RunWorkspace
from .workspace_git_utils import run_readonly_git


FINAL_REVIEW_SECRET_SCAN_BYTES = 1024 * 1024
SECRET_LIKE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key block", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    (
        "credential assignment",
        re.compile(
            r"\b(?P<name>[A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|ACCESS[_-]?KEY)[A-Z0-9_]*)"
            r"\s*[:=]\s*[\"']?(?P<value>[A-Za-z0-9_./+=:-]{24,})",
            re.IGNORECASE,
        ),
    ),
    ("OpenAI API key", re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
)


def find_secret_like_changed_files(
    workspace: RunWorkspace,
    files: list[dict[str, object]],
    max_bytes: int | None = None,
    max_findings: int = 10,
) -> tuple[list[dict[str, object]], int, bool]:
    byte_limit = FINAL_REVIEW_SECRET_SCAN_BYTES if max_bytes is None else max_bytes
    root = workspace.root.resolve()
    findings: list[dict[str, object]] = []
    total = 0
    truncated = False
    for item in files:
        raw_path = item.get("path") if isinstance(item, dict) else None
        if not isinstance(raw_path, str) or not raw_path:
            continue
        try:
            path = (root / raw_path).resolve()
            if path != root and root not in path.parents:
                continue
            if not path.is_file():
                continue
            with path.open("rb") as handle:
                content = handle.read(byte_limit + 1)
        except OSError:
            continue
        if b"\x00" in content:
            continue
        if len(content) > byte_limit:
            truncated = True
            content = content[:byte_limit]
        text = content.decode("utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            label = secret_like_line_label(line)
            if not label:
                continue
            total += 1
            if len(findings) < max_findings:
                findings.append({"path": raw_path, "line": line_number, "label": label})
    return findings, total, truncated


def find_secret_like_git_diff_additions(
    workspace: RunWorkspace,
    max_bytes: int | None = None,
    max_findings: int = 10,
) -> tuple[list[dict[str, object]], int, bool, list[str]]:
    byte_limit = FINAL_REVIEW_SECRET_SCAN_BYTES if max_bytes is None else max_bytes
    findings: list[dict[str, object]] = []
    total = 0
    truncated = False
    warnings: list[str] = []
    for diff_args, source in (
        (["diff", "--unified=0", "--no-ext-diff"], "worktree"),
        (["diff", "--cached", "--unified=0", "--no-ext-diff"], "index"),
    ):
        result = run_readonly_git(workspace.root, diff_args)
        if not result.ok:
            warnings.append(result.stderr.strip() or f"git {' '.join(diff_args)} failed")
            continue
        output = result.stdout
        output_bytes = output.encode("utf-8", errors="ignore")
        if len(output_bytes) > byte_limit:
            truncated = True
            output = output_bytes[:byte_limit].decode("utf-8", errors="ignore")
        diff_findings, diff_total = secret_like_git_diff_addition_findings(
            output,
            source,
            max_findings=max(0, max_findings - len(findings)),
        )
        total += diff_total
        findings.extend(diff_findings)
    return findings, total, truncated, warnings


def secret_like_git_diff_addition_findings(
    diff_text: str,
    source: str,
    max_findings: int = 10,
) -> tuple[list[dict[str, object]], int]:
    findings: list[dict[str, object]] = []
    total = 0
    current_file = ""
    new_line: int | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            current_file = normalize_diff_new_file_path(line[4:].strip())
            continue
        if line.startswith("@@ "):
            new_line = parse_diff_hunk_new_start(line)
            continue
        if line.startswith("+") and not line.startswith("+++"):
            label = secret_like_line_label(line[1:])
            if label:
                total += 1
                if len(findings) < max_findings:
                    findings.append(
                        {
                            "path": current_file or "<unknown>",
                            "line": new_line or 0,
                            "label": label,
                            "source": source,
                        }
                    )
            if new_line is not None:
                new_line += 1
            continue
        if line.startswith("-") and not line.startswith("---"):
            continue
        if new_line is not None:
            new_line += 1
    return findings, total


def normalize_diff_new_file_path(path: str) -> str:
    if path == "/dev/null":
        return path
    if path.startswith("b/"):
        return path[2:]
    return path


def parse_diff_hunk_new_start(header: str) -> int | None:
    match = re.search(r"\+(\d+)(?:,\d+)?", header)
    if not match:
        return None
    return int(match.group(1))


def secret_like_line_label(line: str) -> str | None:
    for label, pattern in SECRET_LIKE_PATTERNS:
        match = pattern.search(line)
        if not match:
            continue
        if label == "credential assignment":
            name = match.groupdict().get("name")
            value = match.groupdict().get("value")
            if not secret_like_assignment_is_high_confidence(name, value):
                continue
            return name.upper() if isinstance(name, str) and name else label
        return label
    return None


def secret_like_assignment_is_high_confidence(name: object, value: object) -> bool:
    if not isinstance(name, str) or not isinstance(value, str):
        return True
    normalized_name = name.upper().replace("-", "_")
    normalized_value = value.lower()
    if normalized_name.endswith(("_PATH", "_TRUNCATED", "_WARNINGS", "_TOKENS")):
        return False
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        return False
    if any(marker in normalized_value for marker in ("testsecret", "placeholder", "dummy", "example", "redacted")):
        return False
    if value.startswith(("src/", "tests/", "test/")) or value.endswith((".py", ".txt", ".json", ".md")):
        return False
    return True
