from dataclasses import dataclass
from typing import Literal

OllamaResponseFormat = Literal["", "json"]


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LLMRequest:
    messages: tuple[LLMMessage, ...]
    temperature: float = 0.0
    max_tokens: int | None = None
    context_window: int | None = None
    response_format: OllamaResponseFormat | dict[str, object] | None = None
    reasoning_enabled: bool | None = None


@dataclass(frozen=True, slots=True)
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
