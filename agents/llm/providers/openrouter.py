from typing import Any

import httpx

from agents.llm.errors import (
    LLMConfigurationError,
    LLMRequestError,
    LLMResponseError,
)
from agents.llm.models import LLMRequest, LLMResponse
from agents.llm.provider import LLMProvider


class OpenRouterProvider(LLMProvider):
    """LLM provider backed by OpenRouter."""

    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        site_url: str | None = None,
        app_name: str = "RepoPilot",
    ) -> None:
        if not model_name.strip():
            raise LLMConfigurationError("OpenRouter model name cannot be empty.")

        if not api_key.strip():
            raise LLMConfigurationError("OpenRouter API key cannot be empty.")

        if not base_url.strip():
            raise LLMConfigurationError("OpenRouter base URL cannot be empty.")

        self._model_name = model_name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._site_url = site_url
        self._app_name = app_name

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not request.messages:
            raise LLMRequestError(
                "LLM request must contain at least one message."
            )

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        if self._site_url:
            headers["HTTP-Referer"] = self._site_url

        if self._app_name:
            headers["X-Title"] = self._app_name

        payload: dict[str, Any] = {
            "model": self._model_name,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in request.messages
            ],
            "temperature": request.temperature,
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        if request.reasoning_enabled is not None:
            payload["reasoning"] = {
                "enabled": request.reasoning_enabled,
            }

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=120.0,
            ) as client:
                response = await client.post(
                    "/chat/completions",
                    headers=headers,
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise LLMRequestError("OpenRouter request failed.") from exc

        if response.status_code >= 400:
            raise LLMRequestError(
                "OpenRouter returned HTTP "
                f"{response.status_code}: {response.text[:500]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMResponseError(
                "OpenRouter returned invalid JSON."
            ) from exc

        choices = data.get("choices")

        if not isinstance(choices, list) or not choices:
            raise LLMResponseError(
                "OpenRouter response contains no choices."
            )

        message = choices[0].get("message")

        if not isinstance(message, dict):
            raise LLMResponseError(
                "OpenRouter response contains an invalid message."
            )

        content = message.get("content")

        if not isinstance(content, str) or not content:
            raise LLMResponseError(
                "OpenRouter returned an empty response."
            )

        usage = data.get("usage")

        prompt_tokens: int | None = None
        completion_tokens: int | None = None
        total_tokens: int | None = None

        if isinstance(usage, dict):
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            total_tokens = usage.get("total_tokens")

        model = data.get("model")

        if not isinstance(model, str) or not model:
            model = self._model_name

        return LLMResponse(
            content=content,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
