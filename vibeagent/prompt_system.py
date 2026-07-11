from __future__ import annotations


def build_effective_system_prompt(
    default_prompt: str,
    *,
    system_prompt: str | None = None,
    append_system_prompt: str | None = None,
) -> str:
    base_prompt = system_prompt.strip() if system_prompt and system_prompt.strip() else default_prompt
    extra_prompt = append_system_prompt.strip() if append_system_prompt and append_system_prompt.strip() else ""
    if not extra_prompt:
        return base_prompt
    if not base_prompt:
        return f"Additional system instructions:\n{extra_prompt}"
    return f"{base_prompt}\n\nAdditional system instructions:\n{extra_prompt}"
