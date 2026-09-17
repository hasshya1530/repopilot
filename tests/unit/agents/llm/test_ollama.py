import pytest

from agents.llm.errors import LLMConfigurationError, LLMRequestError
from agents.llm.models import LLMRequest
from agents.llm.providers.ollama import OllamaProvider


def test_ollama_provider_requires_model() -> None:
    with pytest.raises(LLMConfigurationError):
        OllamaProvider(model_name="")


def test_ollama_provider_exposes_model_name() -> None:
    provider = OllamaProvider(model_name="qwen2.5-coder:3b")

    assert provider.model_name == "qwen2.5-coder:3b"


async def test_ollama_provider_rejects_empty_messages() -> None:
    provider = OllamaProvider(model_name="qwen2.5-coder:3b")

    with pytest.raises(LLMRequestError):
        await provider.generate(LLMRequest(messages=()))
