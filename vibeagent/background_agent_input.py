from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import time
from uuid import uuid4

from .background_agent_config import BackgroundAgentConfig
from .background_agent_lock import background_agent_transition_lock
from .background_agent_store import (
    background_agent_runtime_root,
    ensure_background_agent_runtime_root,
    ensure_private_directory,
    write_private_json,
    write_private_json_atomic,
)
from .background_agent_types import BACKGROUND_AGENT_ID_PATTERN
from .types import UserInputAnswer, UserInputRequest
from .user_input_runtime import normalize_user_input_answer, parse_user_input_text


INPUT_VERSION = 1
MAX_INPUT_BYTES = 32_768
MAX_INPUT_TEXT = 8_000


@dataclass(frozen=True)
class BackgroundUserInput:
    agent_id: str
    request_id: str
    request: UserInputRequest
    created_at: str


class BackgroundUserInputPrompt:
    def __init__(self, config: BackgroundAgentConfig, *, poll_interval: float = 0.1) -> None:
        self.config = config
        self.poll_interval = poll_interval

    def __call__(self, request: UserInputRequest) -> UserInputAnswer | None:
        root = self.config.project_root
        agent_id = self.config.agent_id
        interaction = BackgroundUserInput(
            agent_id=agent_id,
            request_id=uuid4().hex,
            request=_bounded_request(request),
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        request_path = background_user_input_request_path(root, agent_id)
        response_path = background_user_input_response_path(root, agent_id)
        ensure_background_agent_runtime_root(root)
        ensure_private_directory(background_user_input_root(root))
        with background_agent_transition_lock(root, agent_id):
            response_path.unlink(missing_ok=True)
            write_private_json_atomic(request_path, _request_payload(interaction))
        try:
            while True:
                answer = _read_answer(response_path, interaction)
                if answer is not None:
                    return answer
                time.sleep(self.poll_interval)
        finally:
            with background_agent_transition_lock(root, agent_id):
                current = read_background_user_input(root, agent_id)
                if current is not None and current.request_id == interaction.request_id:
                    request_path.unlink(missing_ok=True)
                response_path.unlink(missing_ok=True)


def read_background_user_input(
    project_root: Path,
    agent_id: str,
) -> BackgroundUserInput | None:
    payload = _read_payload(
        background_user_input_request_path(project_root.resolve(), agent_id),
        label="user input request",
        agent_id=agent_id,
    )
    return None if payload is None else _parse_request(payload, agent_id)


def answer_background_user_input(
    project_root: Path,
    agent_id: str,
    raw_answer: str,
    *,
    request_id: str | None = None,
) -> BackgroundUserInput:
    root = project_root.resolve()
    with background_agent_transition_lock(root, agent_id):
        interaction = read_background_user_input(root, agent_id)
        if interaction is None:
            raise ValueError(f"Background agent is not waiting for user input: {agent_id}")
        if request_id is not None and interaction.request_id != request_id:
            raise ValueError(f"Background user input request is stale: {agent_id}")
        answer = parse_user_input_text(raw_answer, interaction.request)
        normalized, error = normalize_user_input_answer(interaction.request, answer)
        if normalized is None:
            raise ValueError(error or "User response is empty.")
        try:
            write_private_json(
                background_user_input_response_path(root, agent_id),
                {
                    "schemaVersion": INPUT_VERSION,
                    "agentId": agent_id,
                    "requestId": interaction.request_id,
                    "answer": answer,
                },
                exclusive=True,
            )
        except FileExistsError as error:
            raise ValueError(f"Background user input was already answered: {agent_id}") from error
    return interaction


def remove_background_user_input(project_root: Path, agent_id: str) -> None:
    background_user_input_request_path(project_root, agent_id).unlink(missing_ok=True)
    background_user_input_response_path(project_root, agent_id).unlink(missing_ok=True)


def background_user_input_root(project_root: Path) -> Path:
    return background_agent_runtime_root(project_root) / "user-input"


def background_user_input_request_path(project_root: Path, agent_id: str) -> Path:
    _require_agent_id(agent_id)
    return background_user_input_root(project_root.resolve()) / f"{agent_id}.request.json"


def background_user_input_response_path(project_root: Path, agent_id: str) -> Path:
    _require_agent_id(agent_id)
    return background_user_input_root(project_root.resolve()) / f"{agent_id}.response.json"


def _request_payload(interaction: BackgroundUserInput) -> dict[str, object]:
    request = interaction.request
    return {
        "schemaVersion": INPUT_VERSION,
        "agentId": interaction.agent_id,
        "requestId": interaction.request_id,
        "question": request.question,
        "options": request.options,
        "allowFreeText": request.allow_free_text,
        "header": request.header,
        "optionDescriptions": request.option_descriptions,
        "multiSelect": request.multi_select,
        "createdAt": interaction.created_at,
    }


def _parse_request(payload: object, agent_id: str) -> BackgroundUserInput:
    if not isinstance(payload, dict) or payload.get("schemaVersion") != INPUT_VERSION:
        raise ValueError(f"Invalid background user input request: {agent_id}")
    request_id = payload.get("requestId")
    question = payload.get("question")
    options = payload.get("options")
    allow_free_text = payload.get("allowFreeText")
    header = payload.get("header")
    descriptions = payload.get("optionDescriptions")
    multi_select = payload.get("multiSelect")
    created_at = payload.get("createdAt")
    if (
        payload.get("agentId") != agent_id
        or not _valid_request_id(request_id)
        or not _valid_text(question)
        or not isinstance(options, list)
        or len(options) > 4
        or any(not _valid_text(option) for option in options)
        or len(set(options)) != len(options)
        or not isinstance(allow_free_text, bool)
        or (header is not None and not _valid_text(header))
        or not _valid_descriptions(descriptions, options)
        or not isinstance(multi_select, bool)
        or not _valid_text(created_at)
    ):
        raise ValueError(f"Invalid background user input request: {agent_id}")
    return BackgroundUserInput(
        agent_id=agent_id,
        request_id=request_id,
        request=UserInputRequest(
            question=question,
            options=options,
            allow_free_text=allow_free_text,
            header=header,
            option_descriptions=descriptions,
            multi_select=multi_select,
        ),
        created_at=created_at,
    )


def _read_answer(path: Path, interaction: BackgroundUserInput) -> UserInputAnswer | None:
    payload = _read_payload(path, label="user input response", agent_id=interaction.agent_id)
    if payload is None:
        return None
    answer = payload.get("answer") if isinstance(payload, dict) else None
    if (
        not isinstance(payload, dict)
        or payload.get("schemaVersion") != INPUT_VERSION
        or payload.get("agentId") != interaction.agent_id
        or payload.get("requestId") != interaction.request_id
        or not _valid_answer(answer)
    ):
        raise ValueError(f"Invalid background user input response: {interaction.agent_id}")
    normalized, error = normalize_user_input_answer(interaction.request, answer)
    if normalized is None:
        raise ValueError(error or f"Invalid background user input response: {interaction.agent_id}")
    return answer


def _read_payload(path: Path, *, label: str, agent_id: str) -> object | None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Background {label} is not a regular file: {path}")
    if not path.is_file():
        return None
    try:
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError(f"Background {label} is too large: {agent_id}")
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid background {label}: {agent_id}") from error


def _bounded_request(request: UserInputRequest) -> UserInputRequest:
    return UserInputRequest(
        question=request.question[:MAX_INPUT_TEXT],
        options=[option[:MAX_INPUT_TEXT] for option in request.options[:4]],
        allow_free_text=request.allow_free_text,
        header=request.header[:MAX_INPUT_TEXT] if request.header is not None else None,
        option_descriptions={
            option[:MAX_INPUT_TEXT]: description[:MAX_INPUT_TEXT]
            for option, description in (request.option_descriptions or {}).items()
            if option in request.options[:4]
        }
        or None,
        multi_select=request.multi_select,
    )


def _valid_request_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 32
        and all(character in "0123456789abcdef" for character in value)
    )


def _valid_text(value: object) -> bool:
    return isinstance(value, str) and bool(value) and len(value) <= MAX_INPUT_TEXT


def _valid_descriptions(value: object, options: list[object]) -> bool:
    return value is None or (
        isinstance(value, dict)
        and all(
            key in options
            and _valid_text(key)
            and isinstance(description, str)
            and len(description) <= MAX_INPUT_TEXT
            for key, description in value.items()
        )
    )


def _valid_answer(value: object) -> bool:
    values = value if isinstance(value, list) else [value]
    return bool(values) and all(
        isinstance(item, str) and 0 < len(item) <= MAX_INPUT_TEXT
        for item in values
    )


def _require_agent_id(agent_id: str) -> None:
    if BACKGROUND_AGENT_ID_PATTERN.fullmatch(agent_id) is None:
        raise ValueError(f"Invalid background agent id: {agent_id}")


__all__ = [
    "BackgroundUserInput",
    "BackgroundUserInputPrompt",
    "answer_background_user_input",
    "read_background_user_input",
    "remove_background_user_input",
]
