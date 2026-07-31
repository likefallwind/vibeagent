from __future__ import annotations

import socket
import urllib.error
import urllib.request

from .command_safety import get_blocked_command_reason
from .network_url_safety import UrlSafetyError, open_scoped_url
from .runtime_http_builders import (
    build_http_check_observation,
    build_http_fetch_observation,
    response_content_type,
)
from .types import (
    CommandCheckObservation,
    HttpCheckObservation,
    HttpFetchObservation,
    PortCheckObservation,
)
from .workspace_core import RunWorkspace
from .workspace_resolve import resolve_command_cwd
from .workspace import missing_command_tool


def build_command_preflight(workspace: RunWorkspace, command: str, cwd: str | None) -> dict[str, object]:
    cwd_label = cwd or "."
    try:
        resolve_command_cwd(workspace, cwd)
        cwd_ok = True
        cwd_message = ""
    except ValueError as error:
        cwd_ok = False
        cwd_message = str(error)

    block_reason = get_blocked_command_reason(command)
    missing_tool = missing_command_tool(command)
    ok = cwd_ok and block_reason is None and missing_tool is None
    if ok:
        message = "Command preflight passed."
    else:
        issues: list[str] = []
        if not cwd_ok:
            issues.append(cwd_message)
        if block_reason:
            issues.append(f"Command blocked: {block_reason}")
        if missing_tool:
            issues.append(f"Missing executable on PATH: {missing_tool}")
        message = "Command preflight failed: " + "; ".join(issues) + "."
    return {
        "ok": ok,
        "cwd": cwd_label,
        "cwd_ok": cwd_ok,
        "blocked": block_reason is not None,
        "block_reason": block_reason,
        "executable_available": missing_tool is None,
        "missing_tool": missing_tool,
        "message": message,
    }


def build_command_check_observation(workspace: RunWorkspace, command: str, cwd: str | None) -> CommandCheckObservation:
    result = build_command_preflight(workspace, command, cwd)
    return CommandCheckObservation(
        kind="command_check",
        ok=bool(result["ok"]),
        command=command,
        cwd=str(result["cwd"]),
        cwd_ok=bool(result["cwd_ok"]),
        blocked=bool(result["blocked"]),
        block_reason=result["block_reason"] if isinstance(result["block_reason"], str) else None,
        executable_available=bool(result["executable_available"]),
        missing_tool=result["missing_tool"] if isinstance(result["missing_tool"], str) else None,
        message=str(result["message"]),
    )


def check_tcp_port(host: str, port: int, timeout_ms: int = 1_000) -> PortCheckObservation:
    try:
        with socket.create_connection((host, port), timeout=timeout_ms / 1000):
            return PortCheckObservation(
                kind="port_check",
                ok=True,
                host=host,
                port=port,
                timeout_ms=timeout_ms,
                reachable=True,
                error=None,
                message=f"{host}:{port} is reachable.",
            )
    except ConnectionRefusedError as error:
        return PortCheckObservation(
            kind="port_check",
            ok=True,
            host=host,
            port=port,
            timeout_ms=timeout_ms,
            reachable=False,
            error=str(error),
            message=f"{host}:{port} is not accepting TCP connections.",
        )
    except TimeoutError as error:
        return PortCheckObservation(
            kind="port_check",
            ok=True,
            host=host,
            port=port,
            timeout_ms=timeout_ms,
            reachable=False,
            error=str(error),
            message=f"{host}:{port} did not respond before timeout.",
        )
    except OSError as error:
        return PortCheckObservation(
            kind="port_check",
            ok=False,
            host=host,
            port=port,
            timeout_ms=timeout_ms,
            reachable=False,
            error=str(error),
            message=f"Could not check {host}:{port}: {error}.",
        )


def check_http_url(
    url: str,
    timeout_ms: int = 2_000,
    max_body_chars: int = 2_000,
    contains: str | None = None,
    regex: bool = False,
) -> HttpCheckObservation:
    request = urllib.request.Request(url, headers={"User-Agent": "vibeagent-http-check/0.1"})
    try:
        with open_scoped_url(request, timeout=timeout_ms / 1000, scope="local") as response:
            status = int(response.getcode())
            final_url = str(response.geturl())
            reason = str(getattr(response, "reason", "") or "") or None
            return build_http_check_observation(
                url=url,
                final_url=final_url,
                status=status,
                reason=reason,
                timeout_ms=timeout_ms,
                max_body_chars=max_body_chars,
                contains=contains,
                regex=regex,
                body_reader=response.read,
                error=None,
            )
    except urllib.error.HTTPError as error:
        return build_http_check_observation(
            url=url,
            final_url=str(error.geturl() or url),
            status=int(error.code),
            reason=str(error.reason or "") or None,
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
            contains=contains,
            regex=regex,
            body_reader=error.read,
            error=None,
        )
    except (UrlSafetyError, urllib.error.URLError, TimeoutError, socket.timeout) as error:
        return HttpCheckObservation(
            kind="http_check",
            ok=True,
            url=url,
            final_url=None,
            status=None,
            reason=None,
            timeout_ms=timeout_ms,
            reachable=False,
            matched=False,
            matched_pattern=contains,
            body="",
            body_truncated=False,
            max_body_chars=max_body_chars,
            error=str(error),
            message=f"{url} is not reachable over HTTP: {error}.",
        )
    except OSError as error:
        return HttpCheckObservation(
            kind="http_check",
            ok=False,
            url=url,
            final_url=None,
            status=None,
            reason=None,
            timeout_ms=timeout_ms,
            reachable=False,
            matched=False,
            matched_pattern=contains,
            body="",
            body_truncated=False,
            max_body_chars=max_body_chars,
            error=str(error),
            message=f"Could not check {url}: {error}.",
        )


def fetch_http_url(url: str, timeout_ms: int = 5_000, max_body_chars: int = 12_000) -> HttpFetchObservation:
    request = urllib.request.Request(url, headers={"User-Agent": "vibeagent-http-fetch/0.1"})
    try:
        with open_scoped_url(request, timeout=timeout_ms / 1000, scope="local") as response:
            return build_http_fetch_observation(
                url=url,
                final_url=str(response.geturl()),
                status=int(response.getcode()),
                reason=str(getattr(response, "reason", "") or "") or None,
                content_type=response_content_type(response),
                timeout_ms=timeout_ms,
                max_body_chars=max_body_chars,
                body_reader=response.read,
                error=None,
            )
    except urllib.error.HTTPError as error:
        return build_http_fetch_observation(
            url=url,
            final_url=str(error.geturl() or url),
            status=int(error.code),
            reason=str(error.reason or "") or None,
            content_type=response_content_type(error),
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
            body_reader=error.read,
            error=None,
        )
    except (UrlSafetyError, urllib.error.URLError, TimeoutError, socket.timeout) as error:
        return HttpFetchObservation(
            kind="http_fetch",
            ok=True,
            url=url,
            final_url=None,
            status=None,
            reason=None,
            content_type=None,
            timeout_ms=timeout_ms,
            reachable=False,
            body="",
            body_truncated=False,
            max_body_chars=max_body_chars,
            error=str(error),
            message=f"{url} is not reachable over HTTP: {error}.",
        )
    except OSError as error:
        return HttpFetchObservation(
            kind="http_fetch",
            ok=False,
            url=url,
            final_url=None,
            status=None,
            reason=None,
            content_type=None,
            timeout_ms=timeout_ms,
            reachable=False,
            body="",
            body_truncated=False,
            max_body_chars=max_body_chars,
            error=str(error),
            message=f"Could not fetch {url}: {error}.",
        )
