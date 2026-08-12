from __future__ import annotations

import re


MAX_SANDBOX_CREDENTIAL_ENTRIES = 200
_ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")


def parse_sandbox_credential_denies(
    value: object,
    *,
    source: str,
) -> tuple[list[str], list[str]]:
    if not isinstance(value, dict):
        raise ValueError(f"{source} sandbox.credentials must be an object.")
    unsupported = set(value) - {"files", "envVars"}
    if unsupported:
        names = ", ".join(sorted(str(key) for key in unsupported))
        raise ValueError(f"Unsupported {source} sandbox.credentials setting(s): {names}.")
    files = _credential_entries(
        value.get("files", []),
        source=source,
        field="files",
        key="path",
    )
    environment = _credential_entries(
        value.get("envVars", []),
        source=source,
        field="envVars",
        key="name",
    )
    if len(files) + len(environment) > MAX_SANDBOX_CREDENTIAL_ENTRIES:
        raise ValueError(
            f"{source} sandbox.credentials exceeds "
            f"{MAX_SANDBOX_CREDENTIAL_ENTRIES} entries."
        )
    for name in environment:
        if _ENVIRONMENT_NAME.fullmatch(name) is None:
            raise ValueError(
                f"{source} sandbox.credentials.envVars contains an invalid variable name."
            )
    return files, environment


def _credential_entries(
    value: object,
    *,
    source: str,
    field: str,
    key: str,
) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{source} sandbox.credentials.{field} must be a list.")
    parsed: list[str] = []
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {key, "mode"}:
            raise ValueError(
                f"{source} sandbox.credentials.{field} entries require only "
                f"{key} and mode."
            )
        item = entry.get(key)
        mode = entry.get("mode")
        if not isinstance(item, str) or not item.strip() or len(item) > 1_000:
            raise ValueError(
                f"{source} sandbox.credentials.{field}.{key} must contain "
                "1-1000 characters."
            )
        if mode != "deny":
            raise ValueError(
                f"{source} sandbox.credentials.{field} mode {mode!r} is not "
                "supported; only deny is enforced."
            )
        parsed.append(item.strip())
    return parsed


__all__ = ["MAX_SANDBOX_CREDENTIAL_ENTRIES", "parse_sandbox_credential_denies"]
