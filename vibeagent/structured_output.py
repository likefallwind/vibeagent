from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError

from .agent_model import complete_with_retries
from .agent_runtime_utils import (
    append_session_event,
    content_blocks_to_text,
    normalize_assistant_content,
    to_jsonable,
)
from .agent_observation_utils import summarize
from .types import AgentLogger, ChatClient, ChatMessage


MAX_SCHEMA_CHARS = 100_000
MAX_SCHEMA_DEPTH = 64
MAX_SCHEMA_NODES = 10_000
MAX_VALIDATION_ERRORS = 5
MAX_STRUCTURED_OUTPUT_ATTEMPTS = 3
DRAFT7_SCHEMA_URIS = frozenset(
    {
        "http://json-schema.org/draft-07/schema#",
        "https://json-schema.org/draft-07/schema#",
    }
)


@dataclass(frozen=True)
class StructuredOutputResult:
    value: Any | None
    error: str | None
    attempts: int

    @property
    def success(self) -> bool:
        return self.error is None


def parse_structured_output_schema(raw: str) -> dict[str, Any]:
    if len(raw) > MAX_SCHEMA_CHARS:
        raise ValueError(f"--json-schema must be at most {MAX_SCHEMA_CHARS} characters.")
    try:
        schema = json.loads(raw, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, ValueError) as error:
        message = error.msg if isinstance(error, json.JSONDecodeError) else str(error)
        raise ValueError(f"Invalid --json-schema JSON: {message}.") from error
    if not isinstance(schema, dict):
        raise ValueError("--json-schema must contain a JSON object.")
    declared_draft = schema.get("$schema")
    if declared_draft is not None and declared_draft not in DRAFT7_SCHEMA_URIS:
        raise ValueError("--json-schema supports JSON Schema Draft-07 only.")
    _validate_schema_shape(schema)
    try:
        Draft7Validator.check_schema(schema)
    except SchemaError as error:
        raise ValueError(_schema_error_message(error)) from error
    return schema


def generate_structured_output(
    client: ChatClient,
    conversation: list[ChatMessage],
    schema: dict[str, Any],
    *,
    session_dir: Path,
    max_output_tokens: int,
    model_retries: int,
    model_retry_delay_ms: int,
    model_timeout_ms: int,
    iteration: int,
    logger: AgentLogger | None = None,
    complete_func: Callable[..., tuple[Any | None, str | None]] = complete_with_retries,
) -> StructuredOutputResult:
    validator = Draft7Validator(schema)
    messages = list(conversation)
    messages.append(ChatMessage(role="user", content=_structured_output_request(schema)))
    last_errors: list[str] = []

    for attempt in range(1, MAX_STRUCTURED_OUTPUT_ATTEMPTS + 1):
        response, model_error = complete_func(
            client,
            messages,
            tools=None,
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
            iteration=iteration + attempt,
            session_dir=session_dir,
            logger=logger,
            error_event_type="structured_output_model_error",
            error_event_extra={"structured_output_attempt": attempt},
        )
        if response is None:
            error = model_error or "Structured output model request failed."
            _record_structured_output_result(session_dir, attempt, None, error)
            return StructuredOutputResult(value=None, error=error, attempts=attempt)

        content = normalize_assistant_content(response.content if hasattr(response, "content") else response)
        text = content_blocks_to_text(content).strip()
        usage = getattr(response, "usage", None)
        append_session_event(
            session_dir,
            "structured_output_model",
            {
                "attempt": attempt,
                "content": content,
                **({"usage": to_jsonable(usage)} if usage is not None else {}),
            },
        )
        messages.append(ChatMessage(role="assistant", content=content))
        value, last_errors = _parse_and_validate_output(text, validator)
        if not last_errors:
            _record_structured_output_result(session_dir, attempt, value, None)
            return StructuredOutputResult(value=value, error=None, attempts=attempt)

        append_session_event(
            session_dir,
            "structured_output_validation_failed",
            {"attempt": attempt, "errors": last_errors},
        )
        if attempt < MAX_STRUCTURED_OUTPUT_ATTEMPTS:
            messages.append(ChatMessage(role="user", content=_retry_feedback(last_errors)))

    error = (
        f"Structured output did not match the JSON Schema after {MAX_STRUCTURED_OUTPUT_ATTEMPTS} attempts: "
        + "; ".join(last_errors)
    )
    _record_structured_output_result(session_dir, MAX_STRUCTURED_OUTPUT_ATTEMPTS, None, error)
    return StructuredOutputResult(
        value=None,
        error=error,
        attempts=MAX_STRUCTURED_OUTPUT_ATTEMPTS,
    )


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value}")


def _validate_schema_shape(schema: dict[str, Any]) -> None:
    stack: list[tuple[object, int]] = [(schema, 0)]
    references: list[str] = []
    nodes = 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > MAX_SCHEMA_NODES:
            raise ValueError(f"--json-schema must contain at most {MAX_SCHEMA_NODES} values.")
        if depth > MAX_SCHEMA_DEPTH:
            raise ValueError(f"--json-schema nesting must not exceed {MAX_SCHEMA_DEPTH} levels.")
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str):
                if not reference.startswith("#"):
                    raise ValueError("--json-schema external $ref values are not supported.")
                if reference != "#" and not reference.startswith("#/"):
                    raise ValueError("--json-schema supports local JSON Pointer $ref values only.")
                references.append(reference)
            stack.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            stack.extend((item, depth + 1) for item in value)
    for reference in references:
        _resolve_local_reference(schema, reference)


def _resolve_local_reference(schema: object, reference: str) -> object:
    current = schema
    if reference == "#":
        return current
    for encoded_part in reference[2:].split("/"):
        part = encoded_part.replace("~1", "/").replace("~0", "~")
        try:
            if isinstance(current, dict):
                current = current[part]
            elif isinstance(current, list):
                current = current[int(part)]
            else:
                raise KeyError(part)
        except (KeyError, IndexError, ValueError) as error:
            raise ValueError(f"--json-schema contains an unresolved local $ref: {reference}.") from error
    return current


def _schema_error_message(error: SchemaError) -> str:
    path = ".".join(str(item) for item in error.absolute_path)
    location = f" at $.{path}" if path else ""
    return f"Invalid --json-schema{location}: {error.message}."


def _structured_output_request(schema: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Return the final result as one JSON value matching this JSON Schema.",
            "Output JSON only: no Markdown fence, commentary, or tool call.",
            "Use only facts established in the completed workflow and conversation.",
            json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        ]
    )


def _parse_and_validate_output(
    text: str,
    validator: Draft7Validator,
) -> tuple[Any | None, list[str]]:
    if not text:
        return None, ["$: response was empty"]
    try:
        value = json.loads(text, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, ValueError) as error:
        return None, [f"$: response was not one valid JSON value ({error})"]
    try:
        errors = sorted(
            validator.iter_errors(value),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        )
    except Exception as error:
        return None, [f"$: schema validation failed ({summarize(str(error), 500)})"]
    return value, [_validation_error_message(error) for error in errors[:MAX_VALIDATION_ERRORS]]


def _validation_error_message(error: object) -> str:
    path = getattr(error, "absolute_path", ())
    location = "$" + "".join(
        f"[{item}]" if isinstance(item, int) else f".{item}"
        for item in path
    )
    return f"{location}: {summarize(str(getattr(error, 'message', 'validation failed')), 500)}"


def _retry_feedback(errors: list[str]) -> str:
    return "\n".join(
        [
            "The JSON output failed validation. Return a corrected JSON value only.",
            *[f"- {error}" for error in errors],
        ]
    )


def _record_structured_output_result(
    session_dir: Path,
    attempts: int,
    value: Any | None,
    error: str | None,
) -> None:
    append_session_event(
        session_dir,
        "structured_output_result",
        {
            "success": error is None,
            "attempts": attempts,
            **({"structured_output": value} if error is None else {"error": error}),
        },
    )


__all__ = [
    "MAX_STRUCTURED_OUTPUT_ATTEMPTS",
    "StructuredOutputResult",
    "generate_structured_output",
    "parse_structured_output_schema",
]
