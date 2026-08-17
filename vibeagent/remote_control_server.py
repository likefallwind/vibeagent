from __future__ import annotations

from dataclasses import dataclass
from hmac import compare_digest
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
from secrets import token_urlsafe
import ssl
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .agent_view_backend import AgentViewBackend, ProjectAgentViewBackend
from .background_agent_approval import BackgroundApproval
from .background_agent_changes import BackgroundAgentChanges
from .background_agent_input import BackgroundUserInput
from .background_agent_integration import BackgroundAgentIntegration
from .background_agent_types import BACKGROUND_AGENT_ID_PATTERN, BackgroundAgentView
from .remote_control_assets import (
    REMOTE_CONTROL_CSS,
    REMOTE_CONTROL_HTML,
    REMOTE_CONTROL_JS,
)
from .session_names import normalize_session_name


MAX_REMOTE_CONTROL_BODY_BYTES = 64 * 1024
MAX_REMOTE_CONTROL_TEXT_CHARS = 8_000


@dataclass
class RemoteControlServer:
    httpd: ThreadingHTTPServer
    token: str
    url: str
    name: str | None = None

    def serve_forever(self) -> None:
        self.httpd.serve_forever(poll_interval=0.2)

    def close(self) -> None:
        self.httpd.server_close()


def create_remote_control_server(
    project_root: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    name: str | None = None,
    cert_path: Path | None = None,
    key_path: Path | None = None,
    backend: AgentViewBackend | None = None,
    token: str | None = None,
) -> RemoteControlServer:
    root = project_root.resolve()
    if not root.is_dir():
        raise ValueError(f"Remote Control project directory not found: {project_root}")
    address = _normalize_host(host)
    if not 0 <= port <= 65_535:
        raise ValueError("Remote Control port must be between 0 and 65535.")
    tls = _resolve_tls(address, cert_path, key_path)
    access_token = token or token_urlsafe(32)
    if len(access_token) < 32 or len(access_token) > 256:
        raise ValueError("Remote Control token must contain 32 to 256 characters.")
    normalized_name = normalize_session_name(name) if name is not None else None
    active_backend = backend or ProjectAgentViewBackend(root, root)
    handler = _handler_factory(root, active_backend, access_token, normalized_name)
    httpd = ThreadingHTTPServer((address, port), handler)
    httpd.daemon_threads = True
    if tls is not None:
        httpd.socket = tls.wrap_socket(httpd.socket, server_side=True)
    bound_host, bound_port = httpd.server_address[:2]
    display_host = "127.0.0.1" if bound_host == "0.0.0.0" else str(bound_host)
    scheme = "https" if tls is not None else "http"
    return RemoteControlServer(
        httpd=httpd,
        token=access_token,
        url=f"{scheme}://{display_host}:{bound_port}/#token={access_token}",
        name=normalized_name,
    )


def _handler_factory(
    project_root: Path,
    backend: AgentViewBackend,
    token: str,
    name: str | None,
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "VibeAgentRemoteControl/1.0"
        sys_version = ""

        def do_GET(self) -> None:
            request = urlsplit(self.path)
            path = request.path
            if path == "/":
                self._asset("text/html; charset=utf-8", REMOTE_CONTROL_HTML)
                return
            if path == "/styles.css":
                self._asset("text/css; charset=utf-8", REMOTE_CONTROL_CSS)
                return
            if path == "/app.js":
                self._asset("text/javascript; charset=utf-8", REMOTE_CONTROL_JS)
                return
            if not self._authorized():
                return
            try:
                if path == "/api/state":
                    self._json(HTTPStatus.OK, _state_payload(project_root, backend, name))
                    return
                parts = _agent_route(path, suffix="logs")
                if parts is not None:
                    stdout, stderr = backend.logs(parts)
                    self._json(HTTPStatus.OK, {"stdout": stdout, "stderr": stderr})
                    return
                agent_id = _agent_route(path, suffix="changes")
                if agent_id is not None:
                    self._json(HTTPStatus.OK, _changes_payload(backend.changes(agent_id)))
                    return
                agent_id = _agent_route(path, suffix="change")
                if agent_id is not None:
                    query = parse_qs(request.query, keep_blank_values=True)
                    changed_path = _single_query_value(query, "path")
                    side = _single_query_value(query, "side")
                    content = backend.change_content(agent_id, changed_path, side)
                    self._json(
                        HTTPStatus.OK,
                        {"path": changed_path, "side": side, "content": content},
                    )
                    return
                self._json(HTTPStatus.NOT_FOUND, {"error": "Remote Control route not found."})
            except ValueError as error:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            except OSError as error:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})

        def do_POST(self) -> None:
            if not self._authorized():
                return
            path = urlsplit(self.path).path
            try:
                payload = self._read_json()
                if path == "/api/agents":
                    task = _required_text(payload, "task")
                    view = backend.dispatch(task)
                    self._json(
                        HTTPStatus.CREATED,
                        {"message": f"Dispatched background agent {view.record.id}.", "id": view.record.id},
                    )
                    return
                agent_id = _agent_route(path, suffix="integrate")
                if agent_id is not None:
                    result = backend.integrate(agent_id, _required_snapshot_id(payload))
                    self._json(HTTPStatus.OK, _integration_payload(result))
                    return
                for suffix, action in (
                    ("messages", self._message),
                    ("approval", self._approval),
                    ("answer", self._answer),
                    ("stop", self._stop),
                    ("respawn", self._respawn),
                    ("remove", self._remove),
                ):
                    agent_id = _agent_route(path, suffix=suffix)
                    if agent_id is not None:
                        self._json(HTTPStatus.OK, {"message": action(agent_id, payload)})
                        return
                self._json(HTTPStatus.NOT_FOUND, {"error": "Remote Control route not found."})
            except ValueError as error:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            except OSError as error:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})

        def _message(self, agent_id: str, payload: dict[str, object]) -> str:
            return backend.reply(agent_id, _required_text(payload, "message"))

        def _approval(self, agent_id: str, payload: dict[str, object]) -> str:
            approved = payload.get("approved")
            scope = payload.get("scope", "once")
            if not isinstance(approved, bool) or scope not in {"once", "session"}:
                raise ValueError("Approval requires boolean approved and scope once or session.")
            request_id = _required_request_id(payload)
            return backend.decide_approval(  # type: ignore[arg-type]
                agent_id,
                approved,
                scope,
                request_id,
            )

        def _answer(self, agent_id: str, payload: dict[str, object]) -> str:
            return backend.answer_user_input(
                agent_id,
                _required_text(payload, "answer"),
                _required_request_id(payload),
            )

        def _stop(self, agent_id: str, _payload: dict[str, object]) -> str:
            return backend.stop(agent_id)

        def _respawn(self, agent_id: str, _payload: dict[str, object]) -> str:
            return backend.respawn(agent_id)

        def _remove(self, agent_id: str, _payload: dict[str, object]) -> str:
            return backend.remove(agent_id)

        def _authorized(self) -> bool:
            header = self.headers.get("Authorization", "")
            supplied = header[7:] if header.startswith("Bearer ") else ""
            if supplied and compare_digest(supplied, token):
                return True
            self._json(
                HTTPStatus.UNAUTHORIZED,
                {"error": "Remote Control bearer token is missing or invalid."},
                extra_headers={"WWW-Authenticate": "Bearer"},
            )
            return False

        def _read_json(self) -> dict[str, object]:
            raw_length = self.headers.get("Content-Length")
            try:
                length = int(raw_length or "0")
            except ValueError as error:
                raise ValueError("Remote Control Content-Length is invalid.") from error
            if length < 0 or length > MAX_REMOTE_CONTROL_BODY_BYTES:
                raise ValueError(
                    f"Remote Control request body must not exceed {MAX_REMOTE_CONTROL_BODY_BYTES} bytes."
                )
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("Remote Control request body must be a JSON object.") from error
            if not isinstance(payload, dict):
                raise ValueError("Remote Control request body must be a JSON object.")
            return payload

        def _asset(self, content_type: str, value: str) -> None:
            body = value.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self._security_headers(content_type, len(body))
            self.end_headers()
            self.wfile.write(body)

        def _json(
            self,
            status: HTTPStatus,
            payload: dict[str, Any],
            *,
            extra_headers: dict[str, str] | None = None,
        ) -> None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self._security_headers("application/json; charset=utf-8", len(body))
            for name, value in (extra_headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def _security_headers(self, content_type: str, length: int) -> None:
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'",
            )

        def log_message(self, _format: str, *_args: object) -> None:
            return

    return Handler


def _state_payload(
    project_root: Path,
    backend: AgentViewBackend,
    name: str | None,
) -> dict[str, object]:
    return {
        "remoteControlName": name,
        "projectRoot": project_root.as_posix(),
        "agents": [_agent_payload(backend, view) for view in backend.list()],
    }


def _agent_payload(backend: AgentViewBackend, view: BackgroundAgentView) -> dict[str, object]:
    record = view.record
    approval = backend.approval(record.id)
    question = backend.user_input(record.id)
    return {
        "id": record.id,
        "status": view.status,
        "exitCode": view.exit_code,
        "pid": record.pid,
        "startedAt": record.started_at,
        "task": record.task_summary,
        "sessionName": record.session_name,
        "pending": backend.pending(record.id),
        "approval": _approval_payload(approval),
        "question": _question_payload(question),
    }


def _approval_payload(value: BackgroundApproval | None) -> dict[str, object] | None:
    if value is None:
        return None
    return {
        "requestId": value.request_id,
        "actionType": value.action_type,
        "target": value.target,
        "risk": value.risk,
        "preview": value.preview,
        "createdAt": value.created_at,
    }


def _question_payload(value: BackgroundUserInput | None) -> dict[str, object] | None:
    if value is None:
        return None
    request = value.request
    return {
        "requestId": value.request_id,
        "question": request.question,
        "options": request.options,
        "optionDescriptions": request.option_descriptions,
        "allowFreeText": request.allow_free_text,
        "multiSelect": request.multi_select,
        "header": request.header,
        "createdAt": value.created_at,
    }


def _changes_payload(value: BackgroundAgentChanges) -> dict[str, object]:
    return {
        "agentId": value.agent_id,
        "sessionRoot": value.session_root.as_posix(),
        "isolated": value.isolated,
        "branch": value.branch,
        "baseCommit": value.base_commit,
        "headCommit": value.head_commit,
        "snapshotId": value.snapshot_id,
        "omittedFiles": value.omitted_files,
        "files": [
            {
                "path": item.path,
                "committed": item.committed,
                "staged": item.staged,
                "unstaged": item.unstaged,
                "untracked": item.untracked,
                "deleted": item.deleted,
            }
            for item in value.files
        ],
    }


def _integration_payload(value: BackgroundAgentIntegration) -> dict[str, object]:
    applied = len(value.applied_files)
    skipped = len(value.skipped_files)
    return {
        "message": f"Applied {applied} background agent file(s); {skipped} already matched.",
        "agentId": value.agent_id,
        "snapshotId": value.snapshot_id,
        "appliedFiles": list(value.applied_files),
        "skippedFiles": list(value.skipped_files),
    }


def _agent_route(path: str, *, suffix: str) -> str | None:
    parts = path.strip("/").split("/")
    if (
        len(parts) == 4
        and parts[0:2] == ["api", "agents"]
        and parts[3] == suffix
        and BACKGROUND_AGENT_ID_PATTERN.fullmatch(parts[2]) is not None
    ):
        return parts[2]
    return None


def _required_text(payload: dict[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str):
        raise ValueError(f"Remote Control field {field} must be text.")
    normalized = value.strip()
    if not normalized or len(normalized) > MAX_REMOTE_CONTROL_TEXT_CHARS:
        raise ValueError(
            f"Remote Control field {field} must contain 1 to {MAX_REMOTE_CONTROL_TEXT_CHARS} characters."
        )
    return normalized


def _required_request_id(payload: dict[str, object]) -> str:
    value = payload.get("requestId")
    if (
        not isinstance(value, str)
        or len(value) != 32
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError("Remote Control field requestId must be 32 lowercase hexadecimal characters.")
    return value


def _required_snapshot_id(payload: dict[str, object]) -> str:
    value = payload.get("snapshotId")
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError("Remote Control field snapshotId must be 64 lowercase hexadecimal characters.")
    return value


def _single_query_value(query: dict[str, list[str]], field: str) -> str:
    values = query.get(field)
    if not isinstance(values, list) or len(values) != 1 or not values[0]:
        raise ValueError(f"Remote Control query field {field} must be provided exactly once.")
    if len(values[0]) > MAX_REMOTE_CONTROL_TEXT_CHARS:
        raise ValueError(f"Remote Control query field {field} is too long.")
    return values[0]


def _normalize_host(value: str) -> str:
    normalized = value.strip()
    if normalized == "localhost":
        return "127.0.0.1"
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError as error:
        raise ValueError("Remote Control host must be an explicit IPv4 address or localhost.") from error
    if address.version != 4:
        raise ValueError("Remote Control currently supports IPv4 addresses only.")
    return str(address)


def _resolve_tls(
    host: str,
    cert_path: Path | None,
    key_path: Path | None,
) -> ssl.SSLContext | None:
    if (cert_path is None) != (key_path is None):
        raise ValueError("Remote Control TLS certificate and key must be provided together.")
    if cert_path is None or key_path is None:
        if not ipaddress.ip_address(host).is_loopback:
            raise ValueError("Non-loopback Remote Control requires a TLS certificate and private key.")
        return None
    cert = _regular_file(cert_path, "certificate")
    key = _regular_file(key_path, "private key")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        context.load_cert_chain(cert, key)
    except (OSError, ssl.SSLError) as error:
        raise ValueError(f"Could not load Remote Control TLS credentials: {error}") from error
    return context


def _regular_file(path: Path, label: str) -> str:
    expanded = path.expanduser().absolute()
    if expanded.is_symlink() or not expanded.is_file():
        raise ValueError(f"Remote Control TLS {label} is not a regular file: {path}")
    return expanded.as_posix()


__all__ = [
    "MAX_REMOTE_CONTROL_BODY_BYTES",
    "RemoteControlServer",
    "create_remote_control_server",
]
