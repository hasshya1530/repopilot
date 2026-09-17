import pytest

from agents.llm.errors import LLMConfigurationError
from agents.llm.factory import create_llm_provider
from agents.llm.policy import UnsupportedModelError
from agents.llm.providers.ollama import OllamaProvider


def test_factory_creates_ollama_provider() -> None:
    provider = create_llm_provider(
        provider="ollama",
        model_name="qwen2.5-coder:3b",
    )

    assert isinstance(provider, OllamaProvider)
    assert provider.model_name == "qwen2.5-coder:3b"


def test_factory_rejects_unknown_model() -> None:
    with pytest.raises(UnsupportedModelError):
        create_llm_provider(
            provider="ollama",
            model_name="unknown-model",
        )


def test_factory_requires_provider() -> None:
    with pytest.raises(LLMConfigurationError):
        create_llm_provider(
            provider="",
            model_name="qwen2.5-coder:3b",
        )


def test_factory_requires_model() -> None:
    with pytest.raises(LLMConfigurationError):
        create_llm_provider(
            provider="ollama",
            model_name="",
        )


def test_factory_requires_openrouter_key() -> None:
    with pytest.raises(UnsupportedModelError):
        create_llm_provider(
            provider="openrouter",
            model_name="some-model:free",
        )
