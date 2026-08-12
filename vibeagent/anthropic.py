from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .anthropic_betas import anthropic_beta_header, normalize_anthropic_betas
from .anthropic_streaming import accumulate_anthropic_stream
from .minimax import build_request_body, extract_content, extract_usage, summarize
from .model_streaming import ProviderStreamHandler
from .types import AssistantResponse, ChatClient, ChatMessage


ANTHROPIC_API_VERSION = "2023-06-01"


class MissingAnthropicApiKeyError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Missing Anthropic API key. Set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN.")


class AnthropicHttpError(RuntimeError):
    def __init__(self, status: int, response_text: str) -> None:
        self.status = status
        self.response_text = response_text
        super().__init__(f"Anthropic API returned HTTP {status}: {summarize(response_text)}")


class AnthropicResponseError(RuntimeError):
    pass


class AnthropicClient(ChatClient):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        model: str = "claude-sonnet-5",
        *,
        use_auth_token: bool = False,
        effort: str | None = None,
        betas: tuple[str, ...] = (),
    ) -> None:
        if not api_key:
            raise MissingAnthropicApiKeyError()
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.use_auth_token = use_auth_token
        self.effort = effort
        self.betas = normalize_anthropic_betas(betas)

    def with_agent_profile(
        self,
        *,
        model: str | None,
        effort: str | None,
    ) -> "AnthropicClient":
        return AnthropicClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=model or self.model,
            use_auth_token=self.use_auth_token,
            effort=self.effort if effort is None else effort,
            betas=self.betas,
        )

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
    ) -> AssistantResponse:
        body = build_request_body(
            self.model,
            messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if self.model.startswith(("claude-sonnet-5", "claude-opus-5", "claude-fable-5")):
            body.pop("temperature", None)
        if self.effort is not None:
            body["output_config"] = {"effort": self.effort}
        request = Request(
            f"{self.base_url}/v1/messages",
            data=json.dumps(body).encode("utf-8"),
            headers=self._request_headers(),
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_ms / 1000) as response:
                text = response.read().decode("utf-8")
        except HTTPError as error:
            text = error.read().decode("utf-8", errors="replace")
            raise AnthropicHttpError(error.code, text) from error
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise AnthropicResponseError(f"Anthropic response was not JSON: {error}") from error
        content = extract_content(data)
        if not content:
            raise AnthropicResponseError(f"Anthropic response did not include structured content: {summarize(text)}")
        return AssistantResponse(content=content, raw=data, usage=extract_usage(data))

    def complete_stream(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
        *,
        on_event: ProviderStreamHandler,
    ) -> AssistantResponse:
        body = build_request_body(
            self.model,
            messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if self.model.startswith(("claude-sonnet-5", "claude-opus-5", "claude-fable-5")):
            body.pop("temperature", None)
        if self.effort is not None:
            body["output_config"] = {"effort": self.effort}
        body["stream"] = True
        request = Request(
            f"{self.base_url}/v1/messages",
            data=json.dumps(body).encode("utf-8"),
            headers=self._request_headers(stream=True),
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_ms / 1000) as response:
                data = accumulate_anthropic_stream(
                    response,
                    on_event=on_event,
                    response_error=AnthropicResponseError,
                )
        except HTTPError as error:
            text = error.read().decode("utf-8", errors="replace")
            raise AnthropicHttpError(error.code, text) from error
        content = extract_content(data)
        if not content:
            raise AnthropicResponseError("Anthropic streaming response did not include structured content.")
        return AssistantResponse(content=content, raw=data, usage=extract_usage(data))

    def _request_headers(self, *, stream: bool = False) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": ANTHROPIC_API_VERSION,
        }
        if stream:
            headers["Accept"] = "text/event-stream"
        beta_header = anthropic_beta_header(self.betas)
        if beta_header is not None:
            headers["anthropic-beta"] = beta_header
        if self.use_auth_token:
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            headers["x-api-key"] = self.api_key
        return headers
