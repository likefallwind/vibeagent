from __future__ import annotations

from collections.abc import Sequence
import re


MAX_ANTHROPIC_BETAS = 16
_BETA_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def normalize_anthropic_betas(values: Sequence[str] | str | None) -> tuple[str, ...]:
    if values is None:
        return ()
    raw_values = (values,) if isinstance(values, str) else values
    normalized: list[str] = []
    for raw_value in raw_values:
        for part in raw_value.split(","):
            value = part.strip()
            if not value or _BETA_NAME.fullmatch(value) is None:
                raise ValueError(
                    "--betas values must be non-empty API beta names containing only letters, numbers, '.', '_', or '-'."
                )
            if value not in normalized:
                normalized.append(value)
            if len(normalized) > MAX_ANTHROPIC_BETAS:
                raise ValueError(f"--betas accepts at most {MAX_ANTHROPIC_BETAS} unique values.")
    return tuple(normalized)


def anthropic_beta_header(values: Sequence[str] | str | None) -> str | None:
    normalized = normalize_anthropic_betas(values)
    return ",".join(normalized) if normalized else None


__all__ = [
    "MAX_ANTHROPIC_BETAS",
    "anthropic_beta_header",
    "normalize_anthropic_betas",
]
