from __future__ import annotations

from pathlib import Path

from .command_parsing import parse_local_path_args
from .local_command_workspace import local_command_workspace
from .project_command_utils import (
    commands_attr as _commands_attr,
    execute_action as _execute_action,
)
from .types import FileInfoAction, ImageInfoAction

FILE_INFO_USAGE = "Usage: /file-info <path...>"
IMAGE_INFO_USAGE = "Usage: /image-info <path...>"


def serialize_file_info_result(file: object) -> dict[str, object]:
    return {
        "path": str(getattr(file, "path", "")),
        "ok": bool(getattr(file, "ok", False)),
        "exists": bool(getattr(file, "exists", False)),
        "type": file_type_text(file),
        "isFile": bool(getattr(file, "is_file", False)),
        "isDirectory": bool(getattr(file, "is_dir", False)),
        "sizeBytes": getattr(file, "size_bytes", None),
        "lineCount": getattr(file, "line_count", None),
        "binary": getattr(file, "is_binary", None),
        "message": str(getattr(file, "message", "")),
    }


def _path_collection_failure_report(
    root: Path,
    collection_key: str,
    message: str,
    *,
    total: int = 0,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        collection_key: {"ok": 0, "total": total, "items": []},
        "message": message,
    }


def get_file_info_report(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=50)
    except ValueError as error:
        return _path_collection_failure_report(root, "paths", _usage_error(FILE_INFO_USAGE, error))
    if not paths:
        return _path_collection_failure_report(root, "paths", FILE_INFO_USAGE)

    workspace = local_command_workspace(root, "local-file-info")
    observation = _execute_action(
        workspace,
        FileInfoAction(
            type="file_info",
            paths=paths,
        ),
    )
    if observation.kind != "file_info":
        return _path_collection_failure_report(
            root,
            "paths",
            f"Unexpected observation: {observation.kind}",
            total=len(paths),
        )
    items = [serialize_file_info_result(file) for file in observation.files]
    ok_count = sum(1 for item in items if bool(item["ok"]))
    return {
        "projectRoot": str(root),
        "ok": ok_count == len(items),
        "paths": {"ok": ok_count, "total": len(items), "items": items},
        "message": observation.message,
    }


def format_file_info_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    paths = report.get("paths") if isinstance(report.get("paths"), dict) else {}
    items = paths.get("items") if isinstance(paths, dict) and isinstance(paths.get("items"), list) else []
    lines = [
        "File info:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  paths: {paths.get('ok', 0)}/{paths.get('total', 0)}",
    ]
    if items:
        lines.append("  items:")
        for file in items:
            if not isinstance(file, dict):
                continue
            lines.append(f"    - {file.get('path')}")
            lines.append(f"      ok: {'yes' if bool(file.get('ok')) else 'no'}")
            lines.append(f"      exists: {'yes' if bool(file.get('exists')) else 'no'}")
            lines.append(f"      type: {file.get('type') or 'missing'}")
            lines.append(f"      sizeBytes: {file.get('sizeBytes') if file.get('sizeBytes') is not None else 'unknown'}")
            lines.append(f"      lineCount: {file.get('lineCount') if file.get('lineCount') is not None else 'unknown'}")
            lines.append(f"      binary: {yes_no_unknown(file.get('binary'))}")
            lines.append(f"      message: {file.get('message') or ''}")
    else:
        lines.append("  items: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def get_file_info_text(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
) -> str:
    get_report = _commands_attr("get_file_info_report", get_file_info_report)
    formatter = _commands_attr("format_file_info_report_text", format_file_info_report_text)
    return formatter(get_report(project_root, argument))


def serialize_image_info_result(image: object) -> dict[str, object]:
    exists = bool(getattr(image, "exists", False))
    is_file = bool(getattr(image, "is_file", False))
    return {
        "path": str(getattr(image, "path", "")),
        "ok": bool(getattr(image, "ok", False)),
        "exists": exists,
        "type": "file" if is_file else "missing" if not exists else "path",
        "isFile": is_file,
        "sizeBytes": getattr(image, "size_bytes", None),
        "format": getattr(image, "format", None),
        "mimeType": getattr(image, "mime_type", None),
        "width": getattr(image, "width", None),
        "height": getattr(image, "height", None),
        "message": str(getattr(image, "message", "")),
    }


def get_image_info_report(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=20)
    except ValueError as error:
        return _path_collection_failure_report(root, "images", _usage_error(IMAGE_INFO_USAGE, error))
    if not paths:
        return _path_collection_failure_report(root, "images", IMAGE_INFO_USAGE)

    workspace = local_command_workspace(root, "local-image-info")
    observation = _execute_action(
        workspace,
        ImageInfoAction(
            type="image_info",
            paths=paths,
        ),
    )
    if observation.kind != "image_info":
        return _path_collection_failure_report(
            root,
            "images",
            f"Unexpected observation: {observation.kind}",
            total=len(paths),
        )
    items = [serialize_image_info_result(image) for image in observation.images]
    ok_count = sum(1 for item in items if bool(item["ok"]))
    return {
        "projectRoot": str(root),
        "ok": ok_count == len(items),
        "images": {"ok": ok_count, "total": len(items), "items": items},
        "message": observation.message,
    }


def format_image_info_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    images = report.get("images") if isinstance(report.get("images"), dict) else {}
    items = images.get("items") if isinstance(images, dict) and isinstance(images.get("items"), list) else []
    lines = [
        "Image info:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  images: {images.get('ok', 0)}/{images.get('total', 0)}",
    ]
    if items:
        lines.append("  items:")
        for image in items:
            if not isinstance(image, dict):
                continue
            lines.append(f"    - {image.get('path')}")
            lines.append(f"      ok: {'yes' if bool(image.get('ok')) else 'no'}")
            lines.append(f"      exists: {'yes' if bool(image.get('exists')) else 'no'}")
            lines.append(f"      type: {image.get('type') or 'missing'}")
            lines.append(f"      sizeBytes: {image.get('sizeBytes') if image.get('sizeBytes') is not None else 'unknown'}")
            lines.append(f"      format: {image.get('format') or 'unknown'}")
            lines.append(f"      mimeType: {image.get('mimeType') or 'unknown'}")
            lines.append(f"      width: {image.get('width') if image.get('width') is not None else 'unknown'}")
            lines.append(f"      height: {image.get('height') if image.get('height') is not None else 'unknown'}")
            lines.append(f"      message: {image.get('message') or ''}")
    else:
        lines.append("  items: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def get_image_info_text(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
) -> str:
    get_report = _commands_attr("get_image_info_report", get_image_info_report)
    formatter = _commands_attr("format_image_info_report_text", format_image_info_report_text)
    return formatter(get_report(project_root, argument))


def _usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def file_type_text(file: object) -> str:
    if getattr(file, "is_file", False):
        return "file"
    if getattr(file, "is_dir", False):
        return "directory"
    return "missing" if not getattr(file, "exists", False) else "path"


def yes_no_unknown(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"
