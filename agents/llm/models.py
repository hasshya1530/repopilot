from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LLMMessage:
    """A message sent to an LLM."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """A provider-agnostic LLM generation request."""

    messages: tuple[LLMMessage, ...]
    temperature: float = 0.0
    max_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """A provider-agnostic LLM generation response."""

    content: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
