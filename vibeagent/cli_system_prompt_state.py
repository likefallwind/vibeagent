from __future__ import annotations


CLEAR_SYSTEM_PROMPT_VALUES = {"clear", "off", "none", "default"}


def update_system_prompt_state(current: str | None, argument: str | None, *, label: str) -> tuple[str | None, str]:
    if argument is None or not argument.strip():
        return current, f"{label}: {_format_system_prompt_value(current)}"
    value = argument.strip()
    if value.lower() in CLEAR_SYSTEM_PROMPT_VALUES:
        return None, f"{label} cleared."
    return value, f"{label} set ({len(value)} chars)."


def _format_system_prompt_value(value: str | None) -> str:
    if not value:
        return "default"
    compact = " ".join(value.split())
    if len(compact) > 120:
        compact = f"{compact[:120]}..."
    return f"custom ({len(value)} chars): {compact}"
