from __future__ import annotations

import shlex


CHECK_SUGGESTED_CHECKS_USAGE = "Usage: /check-suggested-checks [max|--max-checks N]"
RUN_SUGGESTED_CHECKS_USAGE = "Usage: /run-suggested-checks [max|--max-checks N]"


def parse_suggested_checks_limit(argument: str | None = None, default: int = 10) -> int:
    if argument and argument.strip():
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        named_max: int | None = None
        positional: list[str] = []
        index = 0
        while index < len(parts):
            part = parts[index]
            if part == "--":
                positional.extend(parts[index + 1 :])
                break
            if part.startswith("--max-checks="):
                raw_value = part.split("=", 1)[1]
                index += 1
            elif part == "--max-checks":
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            elif part.startswith("--"):
                raise ValueError(f"Unknown option: {part}")
            else:
                positional.append(part)
                index += 1
                continue
            if named_max is not None:
                raise ValueError("provide --max-checks at most once.")
            if raw_value is None:
                raise ValueError("--max-checks requires a value.")
            try:
                named_max = int(raw_value)
            except ValueError as error:
                raise ValueError("--max-checks must be an integer.") from error
        if named_max is not None:
            if positional:
                raise ValueError("provide either --max-checks or trailing max, not both.")
            selected = named_max
        elif positional:
            if len(positional) != 1:
                raise ValueError("expected at most one max command count.")
            try:
                selected = int(positional[0])
            except ValueError as error:
                raise ValueError("max must be an integer.") from error
        else:
            selected = default
    else:
        selected = default
    if selected < 1:
        raise ValueError("max must be at least 1.")
    if selected > 10:
        raise ValueError("max must be at most 10.")
    return selected
