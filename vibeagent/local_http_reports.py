from __future__ import annotations

from pathlib import Path


def indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def yes_no(value: object) -> str:
    return "yes" if bool(value) else "no"


def report_int(report: dict[str, object], key: str) -> int:
    return int(report.get(key, 0) or 0)


def port_failure_report(
    root: Path,
    message: str,
    *,
    port: int | None,
    host: str,
    timeout_ms: int,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "host": host,
        "port": port,
        "reachable": False,
        "timeoutMs": timeout_ms,
        "error": None,
        "message": message,
    }


def http_failure_report(
    root: Path,
    message: str,
    *,
    url: str,
    contains: str | None,
    timeout_ms: int,
    max_body_chars: int,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "url": url,
        "finalUrl": None,
        "status": None,
        "reason": None,
        "reachable": False,
        "matched": False,
        "matchedPattern": contains,
        "timeoutMs": timeout_ms,
        "maxBodyChars": max_body_chars,
        "body": "",
        "bodyTruncated": False,
        "error": None,
        "message": message,
    }


def http_fetch_failure_report(
    root: Path,
    message: str,
    *,
    url: str,
    timeout_ms: int,
    max_body_chars: int,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "url": url,
        "finalUrl": None,
        "status": None,
        "reason": None,
        "contentType": None,
        "reachable": False,
        "timeoutMs": timeout_ms,
        "maxBodyChars": max_body_chars,
        "body": "",
        "bodyTruncated": False,
        "error": None,
        "message": message,
    }


def serialize_http_response_fields(
    observation: object,
    *,
    before_reachable: dict[str, object] | None = None,
    after_reachable: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "ok": bool(getattr(observation, "ok", False)),
        "url": str(getattr(observation, "url", "") or ""),
        "finalUrl": getattr(observation, "final_url", None),
        "status": getattr(observation, "status", None),
        "reason": getattr(observation, "reason", None),
        **(before_reachable or {}),
        "reachable": bool(getattr(observation, "reachable", False)),
        **(after_reachable or {}),
        "timeoutMs": int(getattr(observation, "timeout_ms", 0) or 0),
        "maxBodyChars": int(getattr(observation, "max_body_chars", 0) or 0),
        "body": str(getattr(observation, "body", "") or ""),
        "bodyTruncated": bool(getattr(observation, "body_truncated", False)),
        "error": getattr(observation, "error", None),
        "message": str(getattr(observation, "message", "") or ""),
    }


def serialize_http_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        **serialize_http_response_fields(
            observation,
            after_reachable={
                "matched": bool(getattr(observation, "matched", False)),
                "matchedPattern": getattr(observation, "matched_pattern", None),
            },
        ),
    }


def format_http_response_report_text(
    title: str,
    report: dict[str, object],
    detail_lines: list[str],
) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {yes_no(report.get('ok'))}",
        f"  url: {report.get('url') or ''}",
        f"  finalUrl: {report.get('finalUrl') or '.'}",
        f"  status: {report.get('status') if report.get('status') is not None else '.'}",
        f"  reason: {report.get('reason') or '.'}",
        *detail_lines,
        f"  timeoutMs: {report_int(report, 'timeoutMs')}",
        f"  maxBodyChars: {report_int(report, 'maxBodyChars')}",
        f"  bodyTruncated: {yes_no(report.get('bodyTruncated'))}",
    ]
    if report.get("error"):
        lines.append(f"  error: {report.get('error')}")
    lines.append(f"  message: {message}")
    body = str(report.get("body") or "")
    if body:
        lines.append("  body:")
        lines.append(indent_block(body.rstrip(), spaces=4))
    else:
        lines.append("  body: none")
    return "\n".join(lines)


def format_port_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        "Port:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {yes_no(report.get('ok'))}",
        f"  host: {report.get('host') or ''}",
        f"  port: {report.get('port') if report.get('port') is not None else '.'}",
        f"  reachable: {yes_no(report.get('reachable'))}",
        f"  timeoutMs: {report_int(report, 'timeoutMs')}",
    ]
    if report.get("error"):
        lines.append(f"  error: {report.get('error')}")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_http_report_text(report: dict[str, object]) -> str:
    return format_http_response_report_text(
        "HTTP",
        report,
        [
            f"  reachable: {yes_no(report.get('reachable'))}",
            f"  matched: {yes_no(report.get('matched'))}",
            f"  matchedPattern: {report.get('matchedPattern') or '.'}",
        ],
    )


def format_http_fetch_report_text(report: dict[str, object]) -> str:
    return format_http_response_report_text(
        "HTTP fetch",
        report,
        [
            f"  contentType: {report.get('contentType') or '.'}",
            f"  reachable: {yes_no(report.get('reachable'))}",
        ],
    )
