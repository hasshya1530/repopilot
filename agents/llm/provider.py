from abc import ABC, abstractmethod

from agents.llm.models import LLMRequest, LLMResponse


class LLMProvider(ABC):
    """Provider-agnostic interface for LLM generation."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the configured model name."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response for an LLM request."""
