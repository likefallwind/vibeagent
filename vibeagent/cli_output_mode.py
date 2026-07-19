from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CliOutputMode:
    format: str
    machine: bool
    stream_json: bool


def resolve_cli_output_mode(output_json: bool, output_format: str | None) -> CliOutputMode:
    effective_format = output_format or ("json" if output_json else "text")
    return CliOutputMode(
        format=effective_format,
        machine=effective_format in {"json", "stream-json"},
        stream_json=effective_format == "stream-json",
    )
