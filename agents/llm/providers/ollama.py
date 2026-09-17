from ollama import AsyncClient

from agents.llm.errors import (
    LLMConfigurationError,
    LLMRequestError,
    LLMResponseError,
)
from agents.llm.models import LLMRequest, LLMResponse
from agents.llm.provider import LLMProvider


class OllamaProvider(LLMProvider):
    """LLM provider backed by a local Ollama server."""

    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:11434",
    ) -> None:
        if not model_name.strip():
            raise LLMConfigurationError("Ollama model name cannot be empty.")

        if not base_url.strip():
            raise LLMConfigurationError("Ollama base URL cannot be empty.")

        self._model_name = model_name
        self._client = AsyncClient(host=base_url)

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not request.messages:
            raise LLMRequestError("LLM request must contain at least one message.")

        try:
            response = await self._client.chat(
                model=self._model_name,
                messages=[
                    {
                        "role": message.role,
                        "content": message.content,
                    }
                    for message in request.messages
                ],
                options={
                    "temperature": request.temperature,
                    **(
                        {"num_predict": request.max_tokens}
                        if request.max_tokens is not None
                        else {}
                    ),
                },
            )
        except Exception as exc:
            raise LLMRequestError(f"Ollama request failed for model '{self._model_name}'.") from exc

        content = response.message.content

        if not content:
            raise LLMResponseError(
                f"Ollama returned an empty response for model '{self._model_name}'."
            )

        prompt_tokens = getattr(response, "prompt_eval_count", None)
        completion_tokens = getattr(response, "eval_count", None)

        total_tokens: int | None = None
        if prompt_tokens is not None and completion_tokens is not None:
            total_tokens = prompt_tokens + completion_tokens

        return LLMResponse(
            content=content,
            model=self._model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
