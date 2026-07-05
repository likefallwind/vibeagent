from __future__ import annotations

from typing import Callable


CommandItemSerializer = Callable[[object, int | None], dict[str, object]]


def serialize_not_run_commands(
    items: list[object],
    *,
    ran_count: int,
    stopped_early: bool,
    item_key: str,
    serialize_item: CommandItemSerializer,
) -> dict[str, object]:
    not_run = (
        [
            serialize_item(item, index)
            for index, item in enumerate(
                items[max(0, ran_count) :],
                start=max(0, ran_count) + 1,
            )
        ]
        if stopped_early
        else []
    )
    return {"count": len(not_run), item_key: not_run}


def selected_not_run_command_items(
    report: dict[str, object],
    *,
    item_key: str,
    fallback_items: list[dict[str, object]],
    results: list[dict[str, object]],
) -> list[dict[str, object]]:
    selected_not_run = (
        report.get("selectedCommandsNotRun")
        if isinstance(report.get("selectedCommandsNotRun"), dict)
        else {}
    )
    if isinstance(selected_not_run.get(item_key), list):
        return [item for item in selected_not_run.get(item_key, []) if isinstance(item, dict)]
    return fallback_items[len(results) :] if bool(report.get("stoppedEarly")) else []


def format_selected_not_run_command_lines(items: list[dict[str, object]]) -> list[str]:
    if not items:
        return []
    lines = [f"  selectedCommandsNotRun: {len(items)}"]
    for item in items:
        lines.append(f"    - command: {item.get('command') or ''}")
        lines.append(f"      cwd: {item.get('cwd') or '.'}")
    return lines
