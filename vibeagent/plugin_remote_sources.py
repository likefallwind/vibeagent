from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit

from .bounded_subprocess import run_bounded_subprocess
from .network_url_safety import UrlSafetyError, open_scoped_url, validate_scoped_url
from .plugin_installation import remove_plugin_tree


MAX_REMOTE_MANIFEST_BYTES = 1_000_000
DEFAULT_GIT_TIMEOUT_MS = 120_000
MAX_GIT_TIMEOUT_MS = 600_000
GITHUB_REPOSITORY_PATTERN = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,99})/[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,99})$"
)
GIT_REVISION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@+~-]{0,199}$")
GIT_SHA_PATTERN = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")
SSH_SCP_GIT_PATTERN = re.compile(
    r"^(?P<user>[A-Za-z0-9][A-Za-z0-9._-]{0,63})@"
    r"(?P<host>[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?):"
    r"(?P<path>[A-Za-z0-9._~+/-]{1,500})$"
)
SSH_PATH_PATTERN = re.compile(r"^/[A-Za-z0-9._~+/-]{1,500}$")


def github_repository_url(repository: str) -> str:
    if not GITHUB_REPOSITORY_PATTERN.fullmatch(repository):
        raise ValueError("GitHub repository must use owner/repository without spaces.")
    normalized = repository[:-4] if repository.endswith(".git") else repository
    return f"https://github.com/{normalized}.git"


def normalize_public_https_url(value: str, *, label: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"{label} must use HTTPS and include a host.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{label} credentials are not allowed.")
    if parsed.fragment:
        raise ValueError(f"{label} must not contain a URL fragment.")
    try:
        parsed.port
    except ValueError as error:
        raise ValueError(f"{label} has an invalid port: {error}.") from error
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))


def normalize_git_url(value: str, *, label: str = "Git URL") -> str:
    if value.startswith("https://"):
        return normalize_public_https_url(value, label=label)
    scp_match = SSH_SCP_GIT_PATTERN.fullmatch(value)
    if scp_match is not None:
        _validate_ssh_path(scp_match.group("path"), label=label)
        return value
    parsed = urlsplit(value)
    if parsed.scheme != "ssh" or not parsed.hostname:
        raise ValueError(f"{label} must use credential-free HTTPS or SSH Git syntax.")
    if parsed.username is None or parsed.password is not None:
        raise ValueError(f"{label} SSH URLs require a username and must not include a password.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", parsed.username):
        raise ValueError(f"{label} SSH username contains unsupported characters.")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{label} SSH URLs must not contain a query or fragment.")
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError(f"{label} has an invalid port: {error}.") from error
    if port is not None and (port < 1 or port > 65_535):
        raise ValueError(f"{label} SSH port must be between 1 and 65535.")
    _validate_ssh_path(parsed.path, label=label)
    return urlunsplit(("ssh", parsed.netloc, parsed.path, "", ""))


def _validate_ssh_path(value: str, *, label: str) -> None:
    selected = value[1:] if value.startswith("/") else value
    if (
        not selected
        or not SSH_PATH_PATTERN.fullmatch("/" + selected)
        or any(part in {".", ".."} for part in Path(selected).parts)
        or "//" in value
    ):
        raise ValueError(f"{label} SSH repository path contains unsupported components.")


def validate_git_revision(value: str | None, *, label: str = "Git ref") -> str | None:
    if value is None:
        return None
    if not GIT_REVISION_PATTERN.fullmatch(value) or value.startswith("-") or ".." in value:
        raise ValueError(f"{label} contains unsupported characters.")
    return value


def validate_git_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if not GIT_SHA_PATTERN.fullmatch(value):
        raise ValueError("Git SHA must contain exactly 40 or 64 hexadecimal characters.")
    return value.lower()


def clone_remote_git(
    url: str,
    destination: Path,
    *,
    ref: str | None = None,
    sha: str | None = None,
) -> None:
    normalized_url = normalize_git_url(url)
    if ref is not None and sha is not None:
        raise ValueError("Git plugin source must not specify both ref and sha.")
    revision = validate_git_sha(sha) or validate_git_revision(ref) or "HEAD"
    ssh = _is_ssh_git_url(normalized_url)
    _validate_git_host(normalized_url, ssh=ssh)
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Git destination already exists: {destination}")
    if shutil.which("git") is None:
        raise ValueError("Git executable is required for remote plugin sources.")
    if ssh and shutil.which("ssh") is None:
        raise ValueError("SSH executable is required for SSH plugin sources.")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        _run_git(["init", "--quiet", str(destination)], ssh=ssh)
        _run_git(["-C", str(destination), "remote", "add", "origin", normalized_url], ssh=ssh)
        fetch_args = ["-C", str(destination)]
        if not ssh:
            fetch_args.extend(["-c", "http.followRedirects=false"])
        fetch_args.extend(["fetch", "--depth", "1", "origin", revision])
        _run_git(fetch_args, ssh=ssh)
        _run_git(
            ["-C", str(destination), "checkout", "--quiet", "--detach", "FETCH_HEAD"],
            ssh=ssh,
        )
    except Exception:
        if destination.exists():
            remove_plugin_tree(destination)
        raise


def clone_public_git(
    url: str,
    destination: Path,
    *,
    ref: str | None = None,
    sha: str | None = None,
) -> None:
    clone_remote_git(url, destination, ref=ref, sha=sha)


def _is_ssh_git_url(value: str) -> bool:
    return value.startswith("ssh://") or SSH_SCP_GIT_PATTERN.fullmatch(value) is not None


def _validate_git_host(value: str, *, ssh: bool) -> None:
    if not ssh:
        validate_scoped_url(value, "public", require_https=True)
        return
    if value.startswith("ssh://"):
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        port = parsed.port or 22
    else:
        match = SSH_SCP_GIT_PATTERN.fullmatch(value)
        if match is None:
            raise ValueError("SSH Git URL is invalid.")
        host = match.group("host")
        port = 22
    rendered_host = f"[{host}]" if ":" in host else host
    validate_scoped_url(f"https://{rendered_host}:{port}/", "public", require_https=True)


def download_public_json(url: str, destination: Path) -> str:
    normalized_url = normalize_public_https_url(url, label="Marketplace URL")
    request = urllib.request.Request(
        normalized_url,
        headers={"Accept": "application/json", "User-Agent": "vibeagent-plugin-marketplace/1.0"},
    )
    try:
        with open_scoped_url(request, timeout=30, scope="public", require_https=True) as response:
            raw = response.read(MAX_REMOTE_MANIFEST_BYTES + 1)
            final_url = str(response.geturl())
    except (UrlSafetyError, urllib.error.URLError, TimeoutError, socket.timeout, OSError) as error:
        raise ValueError(f"Could not download marketplace manifest: {error}") from error
    if len(raw) > MAX_REMOTE_MANIFEST_BYTES:
        raise ValueError(f"Remote marketplace manifest exceeds {MAX_REMOTE_MANIFEST_BYTES} bytes.")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Remote marketplace manifest is not valid UTF-8 JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("Remote marketplace manifest must contain a JSON object.")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination.write_bytes(raw)
    return final_url


def remote_git_timeout_ms() -> int:
    raw = os.environ.get("VIBEAGENT_PLUGIN_GIT_TIMEOUT_MS", str(DEFAULT_GIT_TIMEOUT_MS))
    try:
        timeout = int(raw)
    except ValueError as error:
        raise ValueError("VIBEAGENT_PLUGIN_GIT_TIMEOUT_MS must be an integer.") from error
    if timeout < 1_000 or timeout > MAX_GIT_TIMEOUT_MS:
        raise ValueError(
            f"VIBEAGENT_PLUGIN_GIT_TIMEOUT_MS must be between 1000 and {MAX_GIT_TIMEOUT_MS}."
        )
    return timeout


def _run_git(args: list[str], *, ssh: bool = False) -> None:
    environment = _sanitized_git_environment()
    environment.update(
        {
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_LFS_SKIP_SMUDGE": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    if ssh:
        executable = shutil.which("ssh")
        if executable is None:
            raise ValueError("SSH executable is required for SSH plugin sources.")
        environment["GIT_SSH_COMMAND"] = " ".join(
            (
                shlex.quote(executable),
                f"-F {shlex.quote(os.devnull)}",
                "-oBatchMode=yes",
                "-oStrictHostKeyChecking=yes",
                "-oPasswordAuthentication=no",
                "-oKbdInteractiveAuthentication=no",
                "-oNumberOfPasswordPrompts=0",
                "-oPermitLocalCommand=no",
                "-oProxyCommand=none",
                "-oProxyJump=none",
            )
        )
        environment["GIT_SSH_VARIANT"] = "ssh"
    try:
        result = run_bounded_subprocess(
            ["git", *args],
            env=environment,
            timeout_ms=remote_git_timeout_ms(),
            max_output_chars=4_000,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"Remote Git operation failed: {error}") from error
    if result.returncode != 0:
        output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
        raise ValueError(f"Remote Git operation failed: {output[:4_000] or f'exit {result.returncode}'}")


def _sanitized_git_environment() -> dict[str, str]:
    blocked = {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_ASKPASS",
        "GIT_COMMON_DIR",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_PARAMETERS",
        "GIT_DIR",
        "GIT_EXEC_PATH",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_PROXY_COMMAND",
        "GIT_SSH",
        "GIT_SSH_COMMAND",
        "GIT_SSH_VARIANT",
        "GIT_TEMPLATE_DIR",
        "GIT_WORK_TREE",
        "SSH_ASKPASS",
    }
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in blocked
        and not key.startswith("GIT_CONFIG_KEY_")
        and not key.startswith("GIT_CONFIG_VALUE_")
    }
    askpass = shutil.which("false")
    if askpass:
        environment["GIT_ASKPASS"] = askpass
        environment["SSH_ASKPASS"] = askpass
    return environment


__all__ = [
    "clone_public_git",
    "clone_remote_git",
    "download_public_json",
    "github_repository_url",
    "normalize_public_https_url",
    "normalize_git_url",
    "validate_git_revision",
    "validate_git_sha",
]
