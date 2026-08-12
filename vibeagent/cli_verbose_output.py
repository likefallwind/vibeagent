from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from threading import Lock
from typing import Any, TextIO

from .redaction import redact_jsonable_payload, redact_sensitive_text


MAX_VERBOSE_DETAIL_CHARS = 4_000


class VerboseTranscriptRenderer:
    def __init__(
        self,
        output: TextIO | None = None,
        *,
        show_model_text: bool = False,
        on_display_start: Callable[[], None] | None = None,
        on_display_end: Callable[[], None] | None = None,
    ) -> None:
        self.output = output if output is not None else sys.stdout
        self.show_model_text = show_model_text
        self._lock = Lock()
        self._on_display_start = on_display_start
        self._on_display_end = on_display_end

    def observe(self, _session_dir: Path, event: dict[str, Any]) -> None:
        event_type = str(event.get("type") or "")
        lines: list[str] = []
        if event_type == "model":
            lines = self._model_lines(event)
        elif event_type == "tool_call":
            lines = self._tool_call_lines(event)
        elif event_type == "tool_result":
            lines = self._tool_result_lines(event)
        if not lines:
            return
        with self._lock:
            if self._on_display_start is not None:
                self._on_display_start()
            try:
                for line in lines:
                    print(line, file=self.output, flush=True)
            finally:
                if self._on_display_end is not None:
                    self._on_display_end()

    def _model_lines(self, event: dict[str, Any]) -> list[str]:
        if not self.show_model_text:
            return []
        content = event.get("content")
        if not isinstance(content, list):
            return []
        text = "".join(
            str(block.get("text") or "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
        if not text:
            return []
        iteration = event.get("iteration", "?")
        return [f"[verbose] turn {iteration} assistant", _bounded_text(text)]

    def _tool_call_lines(self, event: dict[str, Any]) -> list[str]:
        iteration = event.get("iteration", "?")
        name = _safe_label(event.get("name"), "unknown")
        detail = _bounded_json(event.get("input"))
        return [f"[verbose] turn {iteration} tool {name}", f"  input: {detail}"]

    def _tool_result_lines(self, event: dict[str, Any]) -> list[str]:
        iteration = event.get("iteration", "?")
        name = _safe_label(event.get("name"), "unknown")
        detail = _bounded_json(event.get("result"))
        return [f"[verbose] turn {iteration} result {name}", f"  output: {detail}"]


def _bounded_json(value: object) -> str:
    safe = redact_jsonable_payload(value)
    encoded = json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _bounded_text(encoded)


def _bounded_text(value: str) -> str:
    safe = redact_sensitive_text(value)
    safe = "".join(character if character in "\n\t" or ord(character) >= 32 else " " for character in safe)
    if len(safe) <= MAX_VERBOSE_DETAIL_CHARS:
        return safe
    return f"{safe[:MAX_VERBOSE_DETAIL_CHARS]}... [truncated {len(safe) - MAX_VERBOSE_DETAIL_CHARS} chars]"


def _safe_label(value: object, fallback: str) -> str:
    label = str(value or fallback)
    return "".join(character for character in label if character.isalnum() or character in "._:-")[:128] or fallback


__all__ = ["MAX_VERBOSE_DETAIL_CHARS", "VerboseTranscriptRenderer"]
