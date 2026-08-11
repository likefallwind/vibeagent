from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .agent_profile_client import configure_agent_profile_client
from .types import AssistantResponse, ChatClient, ChatMessage, ToolSpec


MODEL_EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
EFFORT_ENVIRONMENT_VARIABLE = "CLAUDE_CODE_EFFORT_LEVEL"


@dataclass(frozen=True)
class ModelEffortSetting:
    level: str | None
    locked: bool = False


def normalize_model_effort(value: str, *, usage: str) -> str | None:
    normalized = value.strip().lower()
    if normalized in {"auto", "default"}:
        return None
    if normalized not in MODEL_EFFORT_LEVELS:
        choices = "|".join(("auto", *MODEL_EFFORT_LEVELS))
        raise ValueError(f"{usage} [{choices}]")
    return normalized


def resolve_model_effort_setting(
    cli_value: str | None,
    environment: Mapping[str, str] | None = None,
) -> ModelEffortSetting:
    source = environment or {}
    environment_value = source.get(EFFORT_ENVIRONMENT_VARIABLE)
    if environment_value is not None and environment_value.strip():
        return ModelEffortSetting(
            normalize_model_effort(
                environment_value,
                usage=f"Invalid {EFFORT_ENVIRONMENT_VARIABLE}; expected",
            ),
            locked=True,
        )
    if cli_value is None:
        return ModelEffortSetting(None)
    return ModelEffortSetting(normalize_model_effort(cli_value, usage="Invalid --effort; expected"))


def configure_model_effort(
    client: ChatClient,
    setting: ModelEffortSetting,
) -> ChatClient:
    configured = (
        configure_agent_profile_client(client, model=None, effort=setting.level)
        if setting.level is not None
        else client
    )
    if setting.locked:
        return EnvironmentEffortChatClient(configured, setting.level)
    return configured


class EnvironmentEffortChatClient:
    def __init__(self, client: ChatClient, effort: str | None) -> None:
        self.client = client
        self.effort = effort

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
    ) -> AssistantResponse:
        return self.client.complete(
            messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_ms=timeout_ms,
        )

    def with_agent_profile(
        self,
        *,
        model: str | None,
        effort: str | None,
    ) -> EnvironmentEffortChatClient:
        configured = configure_agent_profile_client(
            self.client,
            model=model,
            effort=self.effort,
        )
        return EnvironmentEffortChatClient(configured, self.effort)


__all__ = [
    "EFFORT_ENVIRONMENT_VARIABLE",
    "MODEL_EFFORT_LEVELS",
    "EnvironmentEffortChatClient",
    "ModelEffortSetting",
    "configure_model_effort",
    "normalize_model_effort",
    "resolve_model_effort_setting",
]
