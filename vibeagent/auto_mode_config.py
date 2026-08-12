from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .workspace_core import RunWorkspace, create_local_workspace
from .workspace_settings_sources import (
    claude_settings_files,
    read_settings_payload,
    settings_file_exists,
)


MAX_AUTO_MODE_SETTINGS_BYTES = 100_000
MAX_AUTO_MODE_RULES = 100
MAX_AUTO_MODE_RULE_CHARS = 2_000
DEFAULT_MARKER = "$defaults"

DEFAULT_AUTO_MODE_ENVIRONMENT = (
    "workspace: The active project and its configured repository are trusted development context.",
    "external: Destinations outside the active workspace, remote services, and shared infrastructure are external.",
    "sensitive: Production systems, credentials, account controls, and broad infrastructure are sensitive.",
)
DEFAULT_AUTO_MODE_ALLOW = (
    "local-development: Routine reads, builds, tests, and reversible changes scoped to the active workspace.",
    "repository: Normal inspection and non-destructive work in the active repository.",
)
DEFAULT_AUTO_MODE_SOFT_DENY = (
    "destructive: Broad deletion, destructive Git/history changes, or changes that are difficult to reverse.",
    "remote-effects: Deploying, publishing, sending data, or modifying remote and production systems.",
    "execution-chain: Downloading and immediately executing code, or running opaque generated commands.",
    "security-controls: Changing credentials, access controls, trust settings, or security configuration.",
)
DEFAULT_AUTO_MODE_HARD_DENY = (
    "exfiltration: Disclosing credentials, secrets, private data, or protected repository content.",
    "bypass: Disabling, evading, or weakening permission, sandbox, or auto-mode safety controls.",
    "catastrophic: Commands that can broadly destroy the host, filesystem, repository, or user data.",
)


@dataclass(frozen=True)
class AutoModeConfig:
    environment: tuple[str, ...] = DEFAULT_AUTO_MODE_ENVIRONMENT
    allow: tuple[str, ...] = DEFAULT_AUTO_MODE_ALLOW
    soft_deny: tuple[str, ...] = DEFAULT_AUTO_MODE_SOFT_DENY
    hard_deny: tuple[str, ...] = DEFAULT_AUTO_MODE_HARD_DENY
    classify_all_shell: bool = False
    sources: tuple[str, ...] = ()
    customized: bool = False


def default_auto_mode_config() -> AutoModeConfig:
    return AutoModeConfig()


def resolve_auto_mode_config(workspace: RunWorkspace) -> AutoModeConfig:
    collected: dict[str, list[str] | None] = {
        "environment": None,
        "allow": None,
        "soft_deny": None,
        "hard_deny": None,
    }
    classify_all_shell = False
    sources: list[str] = []
    for settings in claude_settings_files(workspace):
        if not settings.trusted or not settings_file_exists(settings):
            continue
        payload = read_settings_payload(settings, max_bytes=MAX_AUTO_MODE_SETTINGS_BYTES)
        if "autoMode" not in payload:
            continue
        auto_mode = _parse_auto_mode_object(payload["autoMode"], settings.source)
        sources.append(settings.source)
        for field in collected:
            if field in auto_mode:
                if collected[field] is None:
                    collected[field] = []
                collected[field].extend(cast(list[str], auto_mode[field]))
                if len(collected[field]) > MAX_AUTO_MODE_RULES:
                    raise ValueError(
                        f"Trusted autoMode.{field} settings exceed "
                        f"{MAX_AUTO_MODE_RULES} combined rules."
                    )
        if "classifyAllShell" in auto_mode:
            classify_all_shell = cast(bool, auto_mode["classifyAllShell"])

    defaults = {
        "environment": DEFAULT_AUTO_MODE_ENVIRONMENT,
        "allow": DEFAULT_AUTO_MODE_ALLOW,
        "soft_deny": DEFAULT_AUTO_MODE_SOFT_DENY,
        "hard_deny": DEFAULT_AUTO_MODE_HARD_DENY,
    }
    effective = {
        field: _resolve_rule_section(values, defaults[field])
        for field, values in collected.items()
    }
    return AutoModeConfig(
        environment=effective["environment"],
        allow=effective["allow"],
        soft_deny=effective["soft_deny"],
        hard_deny=effective["hard_deny"],
        classify_all_shell=classify_all_shell,
        sources=tuple(sources),
        customized=bool(sources),
    )


def get_auto_mode_defaults_report(*, label: str | None = None) -> dict[str, object]:
    return auto_mode_config_report(default_auto_mode_config(), label=label, include_sources=False)


def get_auto_mode_config_report(
    root: str | Path,
    *,
    setting_sources: tuple[str, ...] = ("user", "project", "local"),
    settings_override_json: str | None = None,
    bare_mode: bool = False,
    label: str | None = None,
) -> dict[str, object]:
    workspace = create_local_workspace(
        root,
        "local-auto-mode-config",
        setting_sources=setting_sources,
        settings_override_json=settings_override_json,
        bare_mode=bare_mode,
    )
    report = auto_mode_config_report(resolve_auto_mode_config(workspace), label=label)
    report["workspace"] = workspace.root.as_posix()
    return report


def auto_mode_config_report(
    config: AutoModeConfig,
    *,
    label: str | None = None,
    include_sources: bool = True,
) -> dict[str, object]:
    report: dict[str, object] = {
        "environment": list(_filter_rules(config.environment, label)),
        "allow": list(_filter_rules(config.allow, label)),
        "soft_deny": list(_filter_rules(config.soft_deny, label)),
        "hard_deny": list(_filter_rules(config.hard_deny, label)),
        "classifyAllShell": config.classify_all_shell,
        "customized": config.customized,
    }
    if include_sources:
        report["sources"] = list(config.sources)
    if label is not None:
        report["label"] = label
    return report


def format_auto_mode_report_text(report: dict[str, object]) -> str:
    lines = ["Auto mode configuration"]
    workspace = report.get("workspace")
    if isinstance(workspace, str):
        lines.append(f"Workspace: {workspace}")
    sources = report.get("sources")
    if isinstance(sources, list):
        lines.append("Sources: " + (", ".join(str(item) for item in sources) or "built-in defaults"))
    lines.append(f"Classify all shell: {'yes' if report.get('classifyAllShell') else 'no'}")
    for field, title in (
        ("environment", "Environment"),
        ("allow", "Allow"),
        ("soft_deny", "Soft deny"),
        ("hard_deny", "Hard deny"),
    ):
        lines.append(f"{title}:")
        values = report.get(field)
        if isinstance(values, list) and values:
            lines.extend(f"  - {value}" for value in values)
        else:
            lines.append("  (none)")
    return "\n".join(lines)


def _parse_auto_mode_object(value: object, source: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{source} autoMode must be a JSON object.")
    allowed_fields = {"environment", "allow", "soft_deny", "hard_deny", "classifyAllShell"}
    unknown = sorted(set(value) - allowed_fields)
    if unknown:
        raise ValueError(f"{source} autoMode contains unknown fields: {', '.join(unknown)}.")
    parsed: dict[str, object] = {}
    for field in ("environment", "allow", "soft_deny", "hard_deny"):
        if field not in value:
            continue
        rules = value[field]
        if not isinstance(rules, list):
            raise ValueError(f"{source} autoMode.{field} must be an array of strings.")
        if len(rules) > MAX_AUTO_MODE_RULES:
            raise ValueError(f"{source} autoMode.{field} exceeds {MAX_AUTO_MODE_RULES} rules.")
        normalized: list[str] = []
        for rule in rules:
            if not isinstance(rule, str) or not rule.strip():
                raise ValueError(f"{source} autoMode.{field} rules must be non-empty strings.")
            text = rule.strip()
            if len(text) > MAX_AUTO_MODE_RULE_CHARS:
                raise ValueError(
                    f"{source} autoMode.{field} rule exceeds {MAX_AUTO_MODE_RULE_CHARS} characters."
                )
            if any(ord(char) < 32 and char not in "\t\n\r" for char in text):
                raise ValueError(f"{source} autoMode.{field} rule contains control characters.")
            normalized.append(text)
        parsed[field] = normalized
    if "classifyAllShell" in value:
        if not isinstance(value["classifyAllShell"], bool):
            raise ValueError(f"{source} autoMode.classifyAllShell must be a boolean.")
        parsed["classifyAllShell"] = value["classifyAllShell"]
    return parsed


def _resolve_rule_section(
    values: list[str] | None,
    defaults: tuple[str, ...],
) -> tuple[str, ...]:
    if values is None:
        return defaults
    resolved: list[str] = []
    for value in values:
        candidates = defaults if value == DEFAULT_MARKER else (value,)
        for candidate in candidates:
            if candidate not in resolved:
                resolved.append(candidate)
    return tuple(resolved)


def _filter_rules(rules: tuple[str, ...], label: str | None) -> tuple[str, ...]:
    if label is None:
        return rules
    prefix = label.strip().casefold()
    if not prefix:
        raise ValueError("--label must be a non-empty prefix.")
    return tuple(rule for rule in rules if rule.casefold().startswith(prefix))


__all__ = [
    "AutoModeConfig",
    "DEFAULT_AUTO_MODE_ALLOW",
    "DEFAULT_AUTO_MODE_ENVIRONMENT",
    "DEFAULT_AUTO_MODE_HARD_DENY",
    "DEFAULT_AUTO_MODE_SOFT_DENY",
    "auto_mode_config_report",
    "default_auto_mode_config",
    "format_auto_mode_report_text",
    "get_auto_mode_config_report",
    "get_auto_mode_defaults_report",
    "resolve_auto_mode_config",
]
