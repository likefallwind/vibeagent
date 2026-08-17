from __future__ import annotations

import argparse


INCOMPLETE_COUNT_FAILURES = (
    ("around_many", "contexts"),
    ("read_files", "files"),
    ("read_ranges", "ranges"),
    ("image_info", "images"),
    ("file_info", "paths"),
    ("output_contexts", "contexts"),
    ("output_diagnostics", "contexts"),
    ("python_traceback", "contexts"),
    ("process_output_contexts", "contexts"),
    ("process_output_diagnostics", "contexts"),
    ("session_output_contexts", "contexts"),
    ("session_output_diagnostics", "contexts"),
    ("symbols", "files"),
    ("python_deps", "files"),
    ("code_deps", "files"),
)


def local_result_arg_selected(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return value is not None


def has_top_level_ok(text: str, value: str) -> bool:
    return any(line == f"  ok: {value}" for line in text.splitlines())


def has_top_level_field(text: str, name: str, value: str) -> bool:
    return any(line == f"  {name}: {value}" for line in text.splitlines())


def has_top_level_error(text: str) -> bool:
    return any(line.startswith("  error: ") for line in text.splitlines())


def has_positive_top_level_count(text: str, name: str) -> bool:
    prefix = f"  {name}: "
    for line in text.splitlines():
        if not line.startswith(prefix):
            continue
        try:
            return int(line[len(prefix) :].strip()) > 0
        except ValueError:
            return False
    return False


def has_incomplete_count_failure(args: argparse.Namespace, text: str) -> bool:
    return any(
        getattr(args, arg_name, None) is not None and has_incomplete_top_level_count(text, count_name)
        for arg_name, count_name in INCOMPLETE_COUNT_FAILURES
    )


def has_bad_session_summary_status(text: str) -> bool:
    return any(
        has_top_level_field(text, "status", status)
        for status in ("failed", "blocked", "incomplete")
    )


def has_local_diagnostic_error(text: str) -> bool:
    if text.startswith("Unsupported VIBEAGENT_PROVIDER:"):
        return True
    return any(
        line.startswith("  provider: Unsupported VIBEAGENT_PROVIDER:")
        or line.startswith("  projectConfigError: ")
        or line == "  costRates: invalid"
        or line == "  memoryLimits: invalid"
        or line == "  memoryLimits: unavailable"
        for line in text.splitlines()
    )


def has_session_verification_issue(text: str) -> bool:
    active_section: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("pendingChecks:") or stripped.startswith("failedChecks:"):
            active_section = stripped.split(":", 1)[0]
            continue
        if stripped.endswith(":"):
            active_section = None
            continue
        if active_section and stripped.startswith("- "):
            return True
    return False


def has_process_status_failure(text: str) -> bool:
    if has_top_level_field(text, "timedOut", "yes"):
        return True
    for line in text.splitlines():
        if line.startswith("  status: ") and process_status_value_failed(line[len("  status: ") :]):
            return True
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        for field in stripped.split(";"):
            field = field.strip()
            if field.startswith("status=") and process_status_value_failed(field[len("status=") :]):
                return True
    return False


def process_status_value_failed(value: str) -> bool:
    if value == "signaled(.)":
        return False
    if value.startswith("signaled(") and value.endswith(")"):
        return True
    if value.startswith("exited(") and value.endswith(")"):
        try:
            return int(value[len("exited(") : -1]) != 0
        except ValueError:
            return True
    return False


def has_incomplete_top_level_count(text: str, name: str) -> bool:
    prefix = f"  {name}: "
    for line in text.splitlines():
        if not line.startswith(prefix):
            continue
        value = line[len(prefix) :]
        parts = value.split("/", 1)
        if len(parts) != 2:
            continue
        try:
            actual = int(parts[0])
            expected = int(parts[1])
        except ValueError:
            continue
        return actual < expected
    return False
