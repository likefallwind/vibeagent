from __future__ import annotations

import json
from pathlib import Path
import sys
from threading import Lock
from typing import Any, TextIO

from .cli_machine_output import machine_runtime_fields
from .cli_result_payloads import (
    CODE_RESULT_SNAKE_CASE_ALIAS_KEYS,
    build_chat_result_payload,
    build_code_result_payload,
    code_result_exit_code,
    code_result_has_pending_user_input,
    code_result_snake_case_aliases,
    code_result_stop_reason,
    code_result_user_input_requests,
    error_result_payload,
)


class JsonEventStream:
    def __init__(self, output: TextIO | None = None) -> None:
        self.output = output if output is not None else sys.stdout
        self.sequence = 0
        self._lock = Lock()

    def session_event(self, session_dir: Path, event: dict[str, Any]) -> None:
        self.emit(
            {
                "type": "event",
                "runId": session_dir.name,
                "sessionId": session_dir.name,
                "session_id": session_dir.name,
                "event": event,
            }
        )

    def result(self, payload: dict[str, object]) -> None:
        self.emit({"type": "result", **payload})

    def user_message(self, session_dir: Path, text: str) -> None:
        self.emit(
            {
                "type": "user",
                "runId": session_dir.name,
                "sessionId": session_dir.name,
                "session_id": session_dir.name,
                "message": {"role": "user", "content": text},
            }
        )

    def subagent_message(
        self,
        session_dir: Path,
        *,
        role: str,
        content: list[dict[str, object]],
        subagent_id: str,
        parent_tool_use_id: str,
    ) -> None:
        self.emit(
            {
                "type": role,
                "runId": session_dir.name,
                "sessionId": session_dir.name,
                "session_id": session_dir.name,
                "subagentId": subagent_id,
                "subagent_id": subagent_id,
                "parent_tool_use_id": parent_tool_use_id,
                "message": {"role": role, "content": content},
            }
        )

    def model_stream_event(
        self,
        session_dir: Path,
        iteration: int,
        attempt: int,
        event: dict[str, Any],
    ) -> None:
        self.emit(
            {
                "type": "stream_event",
                "runId": session_dir.name,
                "sessionId": session_dir.name,
                "session_id": session_dir.name,
                "iteration": iteration,
                "attempt": attempt,
                "event": event,
            }
        )

    def chat_stream_event(self, attempt: int, event: dict[str, Any]) -> None:
        self.emit(
            {
                "type": "stream_event",
                "iteration": 1,
                "attempt": attempt,
                "event": event,
            }
        )

    def emit(self, payload: dict[str, object]) -> None:
        with self._lock:
            self.sequence += 1
            record = {
                "sequence": self.sequence,
                **machine_runtime_fields(),
                **payload,
            }
            self.output.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            self.output.flush()

__all__ = [
    "CODE_RESULT_SNAKE_CASE_ALIAS_KEYS",
    "JsonEventStream",
    "build_chat_result_payload",
    "build_code_result_payload",
    "code_result_exit_code",
    "code_result_snake_case_aliases",
    "code_result_has_pending_user_input",
    "code_result_stop_reason",
    "code_result_user_input_requests",
    "error_result_payload",
]
