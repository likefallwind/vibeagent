from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat
from tempfile import NamedTemporaryFile
from typing import Mapping

from .context_compaction import (
    format_autocompact_setting,
    parse_autocompact_tokens,
    resolve_autocompact_tokens,
)
from .user_paths import user_home
from .workspace_core import RunWorkspace, create_local_workspace
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes
from .workspace_settings_sources import (
    claude_settings_files,
    read_settings_payload,
    settings_file_exists,
)


AUTOCOMPACT_ENV = "CLAUDE_CODE_AUTO_COMPACT_WINDOW"
AUTOCOMPACT_SETTINGS_KEY = "autoCompactWindow"
MAX_AUTOCOMPACT_SETTINGS_BYTES = 512_000


@dataclass(frozen=True)
class AutocompactSetting:
    tokens: int | None = None
    source: str = "auto"
    locked: bool = False


@dataclass(frozen=True)
class AutocompactCommandResult:
    setting: AutocompactSetting
    text: str


def resolve_autocompact_setting(
    workspace: RunWorkspace,
    *,
    cli_value: int | None = None,
    cli_provided: bool = False,
    environment: Mapping[str, str] | None = None,
) -> AutocompactSetting:
    source_environment = os.environ if environment is None else environment
    if AUTOCOMPACT_ENV in source_environment:
        return AutocompactSetting(
            tokens=_parse_environment_tokens(source_environment[AUTOCOMPACT_ENV]),
            source=AUTOCOMPACT_ENV,
            locked=True,
        )
    if cli_provided:
        return AutocompactSetting(
            tokens=resolve_autocompact_tokens(cli_value),
            source="CLI --autocompact",
        )
    return _resolve_settings_value(workspace)


def resolve_autocompact_from_root(
    root: str | Path,
    *,
    cli_value: int | None = None,
    cli_provided: bool = False,
    environment: Mapping[str, str] | None = None,
    setting_sources: tuple[str, ...] = ("user", "project", "local"),
    settings_override_json: str | None = None,
    bare_mode: bool = False,
) -> AutocompactSetting:
    workspace = create_local_workspace(
        root,
        "autocompact-settings",
        setting_sources=setting_sources,
        settings_override_json=settings_override_json,
        bare_mode=bare_mode,
    )
    return resolve_autocompact_setting(
        workspace,
        cli_value=cli_value,
        cli_provided=cli_provided,
        environment=environment,
    )


def run_autocompact_command(
    workspace: RunWorkspace,
    argument: str | None,
    *,
    current: AutocompactSetting,
    environment: Mapping[str, str] | None = None,
) -> AutocompactCommandResult:
    if argument is None:
        return AutocompactCommandResult(current, _format_command_text(current, changed=False))
    try:
        parsed = parse_autocompact_tokens(argument)
    except argparse.ArgumentTypeError as error:
        raise ValueError(f"Usage: /autocompact [auto|TOKENS]\n{error}") from error
    requested_tokens = resolve_autocompact_tokens(parsed)
    _write_user_setting(requested_tokens)

    source_environment = os.environ if environment is None else environment
    if AUTOCOMPACT_ENV in source_environment:
        effective = AutocompactSetting(
            tokens=_parse_environment_tokens(source_environment[AUTOCOMPACT_ENV]),
            source=AUTOCOMPACT_ENV,
            locked=True,
        )
    else:
        effective = _resolve_settings_value(workspace, skip_user=True)
        if effective.source == "auto":
            effective = AutocompactSetting(
                tokens=requested_tokens,
                source="~/.claude/settings.json",
            )
    return AutocompactCommandResult(
        effective,
        _format_command_text(
            effective,
            changed=True,
            saved_tokens=requested_tokens,
        ),
    )


def _resolve_settings_value(
    workspace: RunWorkspace,
    *,
    skip_user: bool = False,
) -> AutocompactSetting:
    for config in reversed(claude_settings_files(workspace)):
        if skip_user and config.source == "~/.claude/settings.json":
            continue
        if not settings_file_exists(config):
            continue
        payload = read_settings_payload(config, max_bytes=MAX_AUTOCOMPACT_SETTINGS_BYTES)
        if AUTOCOMPACT_SETTINGS_KEY not in payload:
            continue
        return AutocompactSetting(
            tokens=_parse_settings_tokens(payload[AUTOCOMPACT_SETTINGS_KEY], config.source),
            source=config.source,
        )
    return AutocompactSetting()


def _parse_environment_tokens(value: str) -> int:
    normalized = value.strip()
    if not normalized.isdecimal():
        raise ValueError(
            f"{AUTOCOMPACT_ENV} must be a plain token count between 100000 and 1000000."
        )
    try:
        parsed = parse_autocompact_tokens(normalized)
    except argparse.ArgumentTypeError as error:
        raise ValueError(
            f"{AUTOCOMPACT_ENV} must be a plain token count between 100000 and 1000000."
        ) from error
    return parsed


def _parse_settings_tokens(value: object, source: str) -> int | None:
    if value is None or (isinstance(value, str) and value.strip().lower() == "auto"):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(
            f"{source} {AUTOCOMPACT_SETTINGS_KEY} must be auto or a 100k-1M token window."
        )
    try:
        return resolve_autocompact_tokens(parse_autocompact_tokens(str(value)))
    except argparse.ArgumentTypeError as error:
        raise ValueError(
            f"{source} {AUTOCOMPACT_SETTINGS_KEY} must be auto or a 100k-1M token window."
        ) from error


def _write_user_setting(tokens: int | None) -> None:
    home = user_home().resolve()
    path = home / ".claude/settings.json"
    payload: dict[str, object] = {}
    mode = 0o600
    if path.exists() or path.is_symlink():
        if has_symlink_component(home, path) or not path.is_file():
            raise ValueError("~/.claude/settings.json must be a regular non-symlink file.")
        raw = read_regular_file_bytes(
            path,
            max_bytes=MAX_AUTOCOMPACT_SETTINGS_BYTES,
            label="~/.claude/settings.json",
        )
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Could not parse ~/.claude/settings.json: {error}") from error
        if not isinstance(decoded, dict):
            raise ValueError("~/.claude/settings.json must contain a JSON object.")
        payload = dict(decoded)
        mode = stat.S_IMODE(path.stat().st_mode)
    if tokens is None:
        payload.pop(AUTOCOMPACT_SETTINGS_KEY, None)
    else:
        payload[AUTOCOMPACT_SETTINGS_KEY] = tokens
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(encoded.encode("utf-8")) > MAX_AUTOCOMPACT_SETTINGS_BYTES:
        raise ValueError(f"User settings exceed {MAX_AUTOCOMPACT_SETTINGS_BYTES} bytes.")
    if path.parent.is_symlink():
        raise ValueError("~/.claude must not be a symbolic link.")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    try:
        os.chmod(temporary, mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _format_command_text(
    setting: AutocompactSetting,
    *,
    changed: bool,
    saved_tokens: int | None = None,
) -> str:
    lines = [
        "Auto-compact configuration" if not changed else "Auto-compact configuration updated",
        f"  window: {format_autocompact_setting(setting.tokens)}",
        f"  source: {setting.source}",
    ]
    if changed:
        lines.append(
            "  saved: " + format_autocompact_setting(saved_tokens)
            + " in ~/.claude/settings.json"
        )
    if setting.locked:
        lines.append(f"  override: {AUTOCOMPACT_ENV} controls this session")
    elif changed and setting.source != "~/.claude/settings.json":
        lines.append("  override: a higher-priority settings scope controls this session")
    return "\n".join(lines)


__all__ = [
    "AUTOCOMPACT_ENV",
    "AUTOCOMPACT_SETTINGS_KEY",
    "AutocompactCommandResult",
    "AutocompactSetting",
    "resolve_autocompact_from_root",
    "resolve_autocompact_setting",
    "run_autocompact_command",
]
