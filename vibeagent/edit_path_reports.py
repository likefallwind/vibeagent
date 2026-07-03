from __future__ import annotations

from pathlib import Path


def format_path_action_observation(title: str, root: Path, observation: object) -> str:
    return format_path_action_report_text(title, serialize_path_action_report(root, observation))


def serialize_path_action_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "path": str(getattr(observation, "path", "") or ""),
        "message": str(getattr(observation, "message", "") or ""),
    }


def format_path_action_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    return "\n".join(
        [
            title,
            f"  projectRoot: {report.get('projectRoot') or '.'}",
            f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
            f"  path: {report.get('path') or ''}",
            f"  message: {message}",
        ]
    )


def format_path_list_observation(title: str, root: Path, observation: object, *, include_diff: bool = False) -> str:
    return format_path_list_report_text(title, serialize_path_list_report(root, observation), include_diff=include_diff)


def serialize_path_list_report(root: Path, observation: object) -> dict[str, object]:
    paths = [str(path) for path in list(getattr(observation, "paths", []))]
    diff = str(getattr(observation, "diff", "") or "")
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "paths": {"total": len(paths), "items": paths},
        "message": str(getattr(observation, "message", "") or ""),
        "diff": {"text": diff, "lines": diff.splitlines(), "lineCount": len(diff.splitlines())},
    }


def format_path_list_report_text(title: str, report: dict[str, object], *, include_diff: bool = False) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    paths_report = report.get("paths") if isinstance(report.get("paths"), dict) else {}
    paths = [str(path) for path in paths_report.get("items", [])] if isinstance(paths_report.get("items"), list) else []
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  paths: {int(paths_report.get('total', len(paths)) or 0)}",
        f"  message: {message}",
    ]
    if paths:
        lines.append("  items:")
        for path in paths:
            lines.append(f"    - {path}")
    if include_diff:
        diff_report = report.get("diff") if isinstance(report.get("diff"), dict) else {}
        diff = str(diff_report.get("text") or "")
        if diff:
            lines.append("  diff:")
            for diff_line in diff.splitlines():
                lines.append(f"    {diff_line}")
    return "\n".join(lines)


def format_file_transfer_observation(title: str, root: Path, observation: object) -> str:
    return format_file_transfer_report_text(title, serialize_file_transfer_report(root, observation))


def serialize_file_transfer_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "source": str(getattr(observation, "source", "") or ""),
        "destination": str(getattr(observation, "destination", "") or ""),
        "message": str(getattr(observation, "message", "") or ""),
    }


def format_file_transfer_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    return "\n".join(
        [
            title,
            f"  projectRoot: {report.get('projectRoot') or '.'}",
            f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
            f"  source: {report.get('source') or ''}",
            f"  destination: {report.get('destination') or ''}",
            f"  message: {message}",
        ]
    )


def format_file_transfer_list_observation(title: str, root: Path, observation: object) -> str:
    return format_file_transfer_list_report_text(title, serialize_file_transfer_list_report(root, observation))


def serialize_file_transfer_list_report(root: Path, observation: object) -> dict[str, object]:
    transfer_items: list[dict[str, object]] = []
    for transfer in list(getattr(observation, "transfers", [])):
        transfer_items.append(
            {
                "source": str(getattr(transfer, "source", "") or ""),
                "destination": str(getattr(transfer, "destination", "") or ""),
            }
        )
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "transfers": {"total": len(transfer_items), "items": transfer_items},
        "message": str(getattr(observation, "message", "") or ""),
    }


def format_file_transfer_list_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    transfers_report = report.get("transfers") if isinstance(report.get("transfers"), dict) else {}
    transfers = [item for item in transfers_report.get("items", []) if isinstance(item, dict)] if isinstance(transfers_report.get("items"), list) else []
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  transfers: {int(transfers_report.get('total', len(transfers)) or 0)}",
        f"  message: {message}",
    ]
    if transfers:
        lines.append("  items:")
        for transfer in transfers:
            lines.append(f"    - {transfer.get('source') or ''} -> {transfer.get('destination') or ''}")
    return "\n".join(lines)
