from __future__ import annotations

from hashlib import sha256
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
from urllib.parse import urlsplit

from .action_browser_types import BrowserAction
from .observation_browser_types import BrowserObservation
from .workspace_core import RunWorkspace
from .workspace_resolve import display_workspace_path, resolve_mutation_path


MAX_BROWSER_OUTPUT_CHARS = 30_000
MAX_BROWSER_SCREENSHOT_BYTES = 25 * 1024 * 1024
BROWSER_TIMEOUT_SECONDS = 35
_PASSTHROUGH_ENVIRONMENT = {
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "SSL_CERT_DIR",
    "SSL_CERT_FILE",
    "TMPDIR",
}


def browser_runtime_available() -> bool:
    return shutil.which("agent-browser") is not None


def execute_browser_action(workspace: RunWorkspace, action: BrowserAction) -> BrowserObservation:
    executable = shutil.which("agent-browser")
    session = _browser_session(workspace)
    if executable is None:
        return _observation(action, session, ok=False, error="agent-browser is not installed or not available on PATH.")
    try:
        runtime_dir = _prepare_runtime_dir(workspace)
        allowed_domains = _read_allowed_domains(runtime_dir)
        command_domains = _validated_navigation_domains(action) or allowed_domains
        if action.operation == "screenshot":
            return _capture_screenshot(workspace, action, executable, session, runtime_dir, command_domains)
        command = _base_command(executable, session, runtime_dir, command_domains)
        command.extend(_operation_arguments(action))
        result = _run_browser(command, workspace.root, runtime_dir)
        if result.returncode == 0 and action.operation == "open":
            _write_allowed_domains(runtime_dir, command_domains)
        return _result_observation(action, session, result)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return _observation(action, session, ok=False, error=str(error), path=action.path)


def _capture_screenshot(
    workspace: RunWorkspace,
    action: BrowserAction,
    executable: str,
    session: str,
    runtime_dir: Path,
    allowed_domains: tuple[str, ...],
) -> BrowserObservation:
    if action.path is None:
        raise ValueError("Browser screenshot path is missing.")
    target = resolve_mutation_path(workspace, action.path)
    if target.exists() and (target.is_symlink() or not target.is_file()):
        raise ValueError(f"Browser screenshot target is not a regular file: {action.path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix.lower() or ".png"
    descriptor, temporary_name = tempfile.mkstemp(prefix=".vibeagent-browser-", suffix=suffix, dir=target.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    temporary.unlink()
    try:
        command = _base_command(executable, session, runtime_dir, allowed_domains)
        command.extend(["screenshot"])
        if action.full:
            command.append("--full")
        if action.annotate:
            command.append("--annotate")
        command.append(temporary.as_posix())
        result = _run_browser(command, workspace.root, runtime_dir)
        if result.returncode != 0:
            return _result_observation(action, session, result, path=action.path)
        if temporary.is_symlink() or not temporary.is_file():
            raise ValueError("Browser did not create a regular screenshot file.")
        size = temporary.stat().st_size
        if size <= 0 or size > MAX_BROWSER_SCREENSHOT_BYTES:
            raise ValueError(
                f"Browser screenshot must contain 1 to {MAX_BROWSER_SCREENSHOT_BYTES} bytes; got {size}."
            )
        os.replace(temporary, target)
        display_path = display_workspace_path(workspace, target)
        output = f"Saved screenshot to {display_path}."
        if result.stderr.strip():
            output += f"\n[stderr]\n{result.stderr.strip()}"
        output, truncated = _truncate(output)
        return _observation(
            action,
            session,
            ok=True,
            output=output,
            output_truncated=truncated,
            path=display_path,
        )
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _base_command(
    executable: str,
    session: str,
    runtime_dir: Path,
    allowed_domains: tuple[str, ...],
) -> list[str]:
    command = [
        executable,
        "--session",
        session,
        "--config",
        (runtime_dir / "config.json").as_posix(),
        "--max-output",
        str(MAX_BROWSER_OUTPUT_CHARS),
    ]
    if allowed_domains:
        command.extend(["--allowed-domains", ",".join(allowed_domains)])
    return command


def _operation_arguments(action: BrowserAction) -> list[str]:
    operation = action.operation
    if operation == "open":
        return ["open", action.url or ""]
    if operation == "snapshot":
        arguments = ["snapshot"]
        if action.interactive:
            arguments.append("--interactive")
        if action.compact:
            arguments.append("--compact")
        if action.depth is not None:
            arguments.extend(["--depth", str(action.depth)])
        return arguments
    if operation in {"reload", "back", "forward"}:
        return [operation]
    if operation in {"click", "dblclick", "hover", "focus", "check", "uncheck"}:
        return [operation, action.selector or ""]
    if operation in {"fill", "type"}:
        return [operation, action.selector or "", action.text or ""]
    if operation == "press":
        return ["press", action.text or ""]
    if operation == "select":
        return ["select", action.selector or "", *action.values]
    if operation == "scroll":
        arguments = ["scroll", action.direction or ""]
        if action.pixels is not None:
            arguments.append(str(action.pixels))
        return arguments
    if operation == "scroll_into_view":
        return ["scrollintoview", action.selector or ""]
    if operation == "wait":
        return ["wait", action.selector or str(action.milliseconds)]
    if operation.startswith("get_"):
        kind = operation.removeprefix("get_")
        if kind == "attribute":
            kind = "attr"
        arguments = ["get", kind]
        if action.selector is not None:
            arguments.append(action.selector)
        if action.attribute is not None:
            arguments.append(action.attribute)
        return arguments
    if operation.startswith("is_"):
        return ["is", operation.removeprefix("is_"), action.selector or ""]
    if operation in {"console", "errors", "close"}:
        return [operation]
    raise ValueError(f"Unsupported browser operation: {operation}")


def _run_browser(command: list[str], cwd: Path, runtime_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=_browser_environment(runtime_dir),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        timeout=BROWSER_TIMEOUT_SECONDS,
        check=False,
    )


def _browser_environment(runtime_dir: Path) -> dict[str, str]:
    environment = {name: os.environ[name] for name in _PASSTHROUGH_ENVIRONMENT if name in os.environ}
    environment["AGENT_BROWSER_CONFIG"] = (runtime_dir / "config.json").as_posix()
    environment["AGENT_BROWSER_MAX_OUTPUT"] = str(MAX_BROWSER_OUTPUT_CHARS)
    environment["AGENT_BROWSER_HEADED"] = "false"
    environment["AGENT_BROWSER_SOCKET_DIR"] = _browser_socket_dir(runtime_dir).as_posix()
    environment["XDG_CACHE_HOME"] = (runtime_dir / "cache").as_posix()
    environment["XDG_RUNTIME_DIR"] = (runtime_dir / "runtime").as_posix()
    return environment


def _prepare_runtime_dir(workspace: RunWorkspace) -> Path:
    runtime_dir = workspace.session_dir / "browser"
    for path in (workspace.session_dir, runtime_dir):
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise ValueError(f"Browser runtime path is not a regular directory: {path}")
    for path in (runtime_dir, runtime_dir / "cache", runtime_dir / "runtime"):
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.chmod(0o700)
    socket_dir = _browser_socket_dir(runtime_dir)
    if socket_dir.is_symlink() or (socket_dir.exists() and not socket_dir.is_dir()):
        raise ValueError(f"Browser socket path is not a regular directory: {socket_dir}")
    socket_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    socket_dir.chmod(0o700)
    config = runtime_dir / "config.json"
    if config.is_symlink() or (config.exists() and not config.is_file()):
        raise ValueError(f"Browser config path is not a regular file: {config}")
    _write_private_json(config, {})
    return runtime_dir


def _browser_socket_dir(runtime_dir: Path) -> Path:
    digest = sha256(str(runtime_dir).encode("utf-8")).hexdigest()[:12]
    user_id = getattr(os, "getuid", lambda: 0)()
    return Path(tempfile.gettempdir()) / f"vab-{user_id}-{digest}"


def _validated_navigation_domains(action: BrowserAction) -> tuple[str, ...]:
    if action.operation != "open" or action.url is None:
        return ()
    parsed = urlsplit(action.url)
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Browser URL has no hostname.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addresses = {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        }
    except (socket.gaierror, ValueError) as error:
        raise ValueError(f"Could not resolve browser host {hostname!r}: {error}.") from error
    if not addresses:
        raise ValueError(f"Browser host {hostname!r} did not resolve to an IP address.")
    unsafe = sorted(
        (
            address
            for address in addresses
            if address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ),
        key=str,
    )
    local = {address for address in addresses if address.is_loopback or address.is_private}
    public = {address for address in addresses if address.is_global}
    if unsafe or (local and public) or len(local | public) != len(addresses):
        rendered = ", ".join(str(address) for address in sorted(addresses, key=str))
        raise ValueError(
            "Browser host must resolve consistently to public or local/private addresses and must not "
            f"use link-local, multicast, reserved, or unspecified addresses; rejected: {rendered}."
        )
    ascii_hostname = hostname.encode("idna").decode("ascii").lower()
    return (ascii_hostname,)


def _read_allowed_domains(runtime_dir: Path) -> tuple[str, ...]:
    path = runtime_dir / "domains.json"
    if not path.exists():
        return ()
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8_192:
        raise ValueError("Browser allowed-domain state is not a bounded regular file.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) > 1:
        raise ValueError("Browser allowed-domain state is invalid.")
    try:
        return tuple(_normalize_allowed_domain(item) for item in payload)
    except (TypeError, UnicodeError, ValueError) as error:
        raise ValueError("Browser allowed-domain state is invalid.") from error


def _normalize_allowed_domain(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 253:
        raise ValueError("Invalid browser domain.")
    try:
        return ipaddress.ip_address(value).compressed.lower()
    except ValueError:
        domain = value.encode("idna").decode("ascii").lower().rstrip(".")
    labels = domain.split(".")
    if not labels or any(
        not label
        or len(label) > 63
        or label.startswith("-")
        or label.endswith("-")
        or any(not (character.isascii() and (character.isalnum() or character == "-")) for character in label)
        for label in labels
    ):
        raise ValueError("Invalid browser domain.")
    return domain


def _write_allowed_domains(runtime_dir: Path, domains: tuple[str, ...]) -> None:
    _write_private_json(runtime_dir / "domains.json", list(domains))


def _write_private_json(path: Path, payload: object) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _browser_session(workspace: RunWorkspace) -> str:
    digest = sha256(f"{workspace.root}\0{workspace.run_id}".encode("utf-8")).hexdigest()[:24]
    return f"vibeagent-{digest}"


def _result_observation(
    action: BrowserAction,
    session: str,
    result: subprocess.CompletedProcess[str],
    *,
    path: str | None = None,
) -> BrowserObservation:
    output = result.stdout.strip()
    stderr = result.stderr.strip()
    if stderr:
        output = f"{output}\n[stderr]\n{stderr}".strip()
    output, truncated = _truncate(output)
    error = None if result.returncode == 0 else (stderr or output or f"agent-browser exited with {result.returncode}")
    return _observation(
        action,
        session,
        ok=result.returncode == 0,
        output=output,
        output_truncated=truncated,
        path=path,
        error=error,
    )


def _observation(
    action: BrowserAction,
    session: str,
    *,
    ok: bool,
    output: str = "",
    output_truncated: bool = False,
    path: str | None = None,
    error: str | None = None,
) -> BrowserObservation:
    state = "completed" if ok else "failed"
    return BrowserObservation(
        kind="browser",
        ok=ok,
        operation=action.operation,
        session=session,
        output=output,
        output_truncated=output_truncated,
        path=path,
        error=error,
        message=f"Browser {action.operation} {state}.",
    )


def _truncate(value: str) -> tuple[str, bool]:
    if len(value) <= MAX_BROWSER_OUTPUT_CHARS:
        return value, False
    return value[:MAX_BROWSER_OUTPUT_CHARS] + "\n...[browser output truncated]", True


__all__ = [
    "BROWSER_TIMEOUT_SECONDS",
    "MAX_BROWSER_OUTPUT_CHARS",
    "MAX_BROWSER_SCREENSHOT_BYTES",
    "browser_runtime_available",
    "execute_browser_action",
]
