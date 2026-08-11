from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any
from urllib.parse import urlparse

from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError

from .types import UserInputHandler, UserInputRequest
from .user_input_runtime import normalize_user_input_answer


MAX_ELICITATION_MESSAGE_CHARS = 4_000
MAX_ELICITATION_FIELDS = 32
MAX_ELICITATION_SCHEMA_CHARS = 50_000
ELICITATION_ACTIONS = frozenset({"accept", "decline", "cancel"})
SENSITIVE_FIELD_PATTERN = re.compile(
    r"(?:^|[_\W])(password|passwd|secret|token|api[_-]?key|access[_-]?key|credit[_-]?card|cvv)(?:$|[_\W])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ElicitationRequest:
    server_name: str
    message: str
    mode: str
    schema: dict[str, Any] | None = None
    url: str | None = None
    elicitation_id: str | None = None

    @property
    def hook_fields(self) -> dict[str, object]:
        fields: dict[str, object] = {
            "mcp_server_name": self.server_name,
            "message": self.message,
            "mode": self.mode,
        }
        if self.schema is not None:
            fields["requested_schema"] = self.schema
        if self.url is not None:
            fields["url"] = self.url
        if self.elicitation_id is not None:
            fields["elicitation_id"] = self.elicitation_id
        return fields


def normalize_elicitation_request(server_name: str, params: dict[str, Any]) -> ElicitationRequest:
    if not server_name or len(server_name) > 64:
        raise ValueError("MCP elicitation server name is invalid.")
    message = params.get("message")
    if not isinstance(message, str) or not message.strip() or len(message) > MAX_ELICITATION_MESSAGE_CHARS:
        raise ValueError("MCP elicitation message must contain 1-4000 characters.")
    mode = params.get("mode", "form")
    if mode not in {"form", "url"}:
        raise ValueError("MCP elicitation mode must be form or url.")
    elicitation_id = params.get("elicitationId")
    if elicitation_id is not None and (
        not isinstance(elicitation_id, str) or not elicitation_id or len(elicitation_id) > 500
    ):
        raise ValueError("MCP elicitationId is invalid.")
    if mode == "url":
        url = params.get("url")
        if not isinstance(url, str) or not _safe_elicitation_url(url):
            raise ValueError("MCP URL elicitation requires a valid HTTPS URL.")
        if not isinstance(elicitation_id, str):
            raise ValueError("MCP URL elicitation requires elicitationId.")
        return ElicitationRequest(server_name, message.strip(), mode, url=url, elicitation_id=elicitation_id)
    schema = params.get("requestedSchema")
    if not isinstance(schema, dict):
        raise ValueError("MCP form elicitation requires requestedSchema.")
    _validate_form_schema(schema)
    return ElicitationRequest(server_name, message.strip(), mode, schema=schema, elicitation_id=elicitation_id)


def prompt_for_elicitation_response(
    request: ElicitationRequest,
    handler: UserInputHandler | None,
) -> dict[str, Any]:
    if handler is None:
        return {"action": "cancel"}
    consent = handler(
        UserInputRequest(
            question=f"{request.server_name}: {request.message}",
            options=["Accept", "Decline"],
            allow_free_text=False,
            header="MCP request",
        )
    )
    if consent is None:
        return {"action": "cancel"}
    normalized, error = normalize_user_input_answer(
        UserInputRequest("", ["Accept", "Decline"], allow_free_text=False),
        consent,
    )
    if error is not None or normalized != "Accept":
        return {"action": "decline"}
    if request.mode == "url":
        completed = handler(
            UserInputRequest(
                question=f"Complete the request at {request.url}, then confirm.",
                options=["Completed", "Decline"],
                allow_free_text=False,
                header="External MCP request",
            )
        )
        return {"action": "accept"} if completed == "Completed" else {"action": "decline"}
    assert request.schema is not None
    content: dict[str, Any] = {}
    properties = request.schema.get("properties", {})
    required = set(request.schema.get("required", []))
    for name, definition in properties.items():
        answer = _prompt_for_field(handler, name, definition, name in required)
        if answer is _CANCELLED:
            return {"action": "cancel"}
        if answer is not _OMITTED:
            content[name] = answer
    return normalize_elicitation_response(request, "accept", content)


def normalize_elicitation_response(
    request: ElicitationRequest,
    action: str,
    content: object,
) -> dict[str, Any]:
    if action not in ELICITATION_ACTIONS:
        raise ValueError("MCP elicitation action is invalid.")
    if action != "accept":
        return {"action": action}
    if request.mode == "url":
        return {"action": "accept"}
    if not isinstance(content, dict):
        raise ValueError("Accepted MCP form elicitation requires object content.")
    assert request.schema is not None
    properties = request.schema.get("properties", {})
    if any(key not in properties for key in content):
        raise ValueError("MCP elicitation response contains an unknown field.")
    errors = sorted(Draft7Validator(request.schema).iter_errors(content), key=lambda item: list(item.path))
    if errors:
        raise ValueError(f"MCP elicitation response does not match requestedSchema: {errors[0].message}")
    return {"action": "accept", "content": dict(content)}


def _validate_form_schema(schema: dict[str, Any]) -> None:
    if len(str(schema)) > MAX_ELICITATION_SCHEMA_CHARS or schema.get("type") != "object":
        raise ValueError("MCP elicitation schema must be a bounded object schema.")
    properties = schema.get("properties")
    if not isinstance(properties, dict) or len(properties) > MAX_ELICITATION_FIELDS:
        raise ValueError(f"MCP elicitation schema must define at most {MAX_ELICITATION_FIELDS} fields.")
    required = schema.get("required", [])
    if not isinstance(required, list) or any(not isinstance(name, str) for name in required):
        raise ValueError("MCP elicitation schema required must be a string array.")
    if any(name not in properties for name in required):
        raise ValueError("MCP elicitation schema requires an unknown field.")
    if set(schema) - {"type", "properties", "required"}:
        raise ValueError("MCP elicitation object schema contains unsupported keywords.")
    for name, definition in properties.items():
        _validate_field_schema(name, definition)
    try:
        Draft7Validator.check_schema(schema)
    except SchemaError as error:
        raise ValueError(f"MCP elicitation schema is invalid: {error.message}") from error


def _validate_field_schema(name: object, definition: object) -> None:
    if not isinstance(name, str) or not name or not isinstance(definition, dict):
        raise ValueError("MCP elicitation fields must have valid names and schemas.")
    if SENSITIVE_FIELD_PATTERN.search(name) or SENSITIVE_FIELD_PATTERN.search(str(definition.get("title", ""))):
        raise ValueError("MCP form elicitation must not request secrets or payment credentials.")
    allowed_types = {"string", "number", "integer", "boolean"}
    if definition.get("type") not in allowed_types:
        raise ValueError("MCP elicitation fields must use primitive schema types.")
    common_keywords = {"type", "title", "description", "default", "enum", "enumNames"}
    type_keywords = {
        "string": {"minLength", "maxLength", "pattern", "format"},
        "number": {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"},
        "integer": {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"},
        "boolean": set(),
    }
    if set(definition) - (common_keywords | type_keywords[str(definition["type"])]):
        raise ValueError("MCP elicitation field schema contains unsupported keywords.")
    if definition.get("format") not in {None, "email", "uri", "date", "date-time"}:
        raise ValueError("MCP elicitation string format is unsupported.")
    enum = definition.get("enum")
    if enum is not None and (
        not isinstance(enum, list)
        or not enum
        or len(enum) > 100
        or any(not isinstance(value, (str, int, float, bool)) for value in enum)
    ):
        raise ValueError("MCP elicitation enum is invalid.")


_CANCELLED = object()
_OMITTED = object()


def _prompt_for_field(handler: UserInputHandler, name: str, definition: dict[str, Any], required: bool) -> object:
    title = str(definition.get("title") or name)
    description = str(definition.get("description") or "")
    enum = definition.get("enum")
    options = [str(value) for value in enum] if isinstance(enum, list) else []
    answer = handler(
        UserInputRequest(
            question=description or title,
            options=options,
            allow_free_text=not options,
            header=title[:64],
        )
    )
    if answer is None:
        return _CANCELLED if required else _OMITTED
    if isinstance(answer, list):
        if len(answer) != 1:
            return _CANCELLED
        answer = answer[0]
    return _coerce_field_value(str(answer), definition)


def _coerce_field_value(value: str, definition: dict[str, Any]) -> Any:
    enum = definition.get("enum")
    if isinstance(enum, list):
        for item in enum:
            if str(item) == value:
                return item
        raise ValueError("MCP elicitation response is not an allowed enum value.")
    value_type = definition.get("type")
    if value_type == "boolean":
        if value.lower() in {"true", "yes", "1"}:
            return True
        if value.lower() in {"false", "no", "0"}:
            return False
        raise ValueError("MCP elicitation boolean response is invalid.")
    if value_type == "integer":
        return int(value)
    if value_type == "number":
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("MCP elicitation number must be finite.")
        return number
    return value


def _safe_elicitation_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.hostname) and parsed.username is None and parsed.password is None


__all__ = [
    "ElicitationRequest",
    "MAX_ELICITATION_MESSAGE_CHARS",
    "normalize_elicitation_request",
    "normalize_elicitation_response",
    "prompt_for_elicitation_response",
]
