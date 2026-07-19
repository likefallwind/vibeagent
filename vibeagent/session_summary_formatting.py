from __future__ import annotations


def clip(value: str, max_length: int) -> str:
    compacted = value.strip()
    if len(compacted) <= max_length:
        return compacted
    if max_length <= 3:
        return compacted[:max_length]
    return compacted[: max_length - 3] + "..."


def format_name_counts(values: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return [f"{name} x{count}" if count > 1 else name for name, count in counts.items()]


def format_session_report_failure_lines(report: dict[str, object], indent: str = "  ", max_text: int = 160) -> list[str]:
    python_failures = report.get("pythonFailures") if isinstance(report.get("pythonFailures"), list) else []
    config_failures = report.get("configFailures") if isinstance(report.get("configFailures"), list) else []
    failures = [
        ("python", item)
        for item in python_failures
        if isinstance(item, str)
    ] + [
        ("config", item)
        for item in config_failures
        if isinstance(item, str)
    ]
    if not failures:
        return []
    lines = [f"{indent}finalReviewFailures:"]
    lines.extend(f"{indent}  - {kind}: {clip(item, max_text)}" for kind, item in failures[:20])
    if len(failures) > 20:
        lines.append(f"{indent}  - ... {len(failures) - 20} more")
    return lines


def format_final_review_changed_file_lines(report: dict[str, object], indent: str = "  ", max_text: int = 160) -> list[str]:
    changed_files = report.get("changedFiles") if isinstance(report.get("changedFiles"), list) else []
    labels = [item for item in changed_files if isinstance(item, str) and item.strip()]
    if not labels:
        return []
    lines = [f"{indent}finalReviewChangedFiles:"]
    lines.extend(f"{indent}  - {clip(item, max_text)}" for item in labels[:20])
    if len(labels) > 20:
        lines.append(f"{indent}  - ... {len(labels) - 20} more")
    return lines


def append_completion_detail_lines(
    lines: list[str],
    completion: dict[str, object],
    indent: str = "    ",
    max_text: int = 160,
) -> None:
    fields = (
        ("latestPendingVerificationChecks", "latestCompletionPendingChecks"),
        ("latestFailedVerificationChecks", "latestCompletionFailedChecks"),
        ("latestFinalReviewBlockingIssues", "latestCompletionFinalReviewIssues"),
        ("latestFinalReviewChangedFiles", "latestCompletionFinalReviewChangedFiles"),
        ("latestToolErrors", "latestCompletionToolErrors"),
        ("latestCheckpointFailures", "latestCompletionCheckpointFailures"),
        ("latestActiveBackgroundProcesses", "latestCompletionActiveProcesses"),
        ("latestDeniedApprovals", "latestCompletionDeniedApprovals"),
        ("latestNextActions", "latestCompletionNextActions"),
    )
    for key, label in fields:
        values = completion.get(key)
        items = [item for item in values if isinstance(item, str) and item.strip()] if isinstance(values, list) else []
        append_limited_bullets(lines, label, items, indent=indent, max_text=max_text, limit=10)


def append_limited_bullets(
    lines: list[str],
    label: str,
    items: list[str],
    *,
    indent: str,
    max_text: int,
    limit: int,
) -> None:
    if not items:
        return
    lines.append(f"{indent}{label}:")
    lines.extend(f"{indent}  - {clip(item, max_text)}" for item in items[:limit])
    if len(items) > limit:
        lines.append(f"{indent}  - ... {len(items) - limit} more")
