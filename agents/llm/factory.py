from agents.llm.errors import LLMConfigurationError
from agents.llm.policy import (
    UnsupportedModelError,
    UnsupportedProviderError,
    get_model_definition,
)
from agents.llm.provider import LLMProvider
from agents.llm.providers.ollama import OllamaProvider
from agents.llm.providers.openrouter import OpenRouterProvider


def create_llm_provider(
    *,
    provider: str,
    model_name: str,
    ollama_base_url: str = "http://localhost:11434",
    openrouter_base_url: str = "https://openrouter.ai/api/v1",
    openrouter_api_key: str | None = None,
    openrouter_site_url: str | None = None,
    openrouter_app_name: str = "RepoPilot",
) -> LLMProvider:
    """Create an approved LLM provider from explicit configuration."""

    provider = provider.strip().lower()
    model_name = model_name.strip()

    if not provider:
        raise LLMConfigurationError("LLM provider cannot be empty.")

    if not model_name:
        raise LLMConfigurationError("LLM model name cannot be empty.")

    if provider not in {"ollama", "openrouter"}:
        raise UnsupportedProviderError(f"Unsupported LLM provider: {provider}")

    definition = get_model_definition(provider, model_name)

    if definition is None:
        raise UnsupportedModelError(
            f"Model '{model_name}' is not approved for provider '{provider}'."
        )

    if provider == "ollama":
        return OllamaProvider(
            model_name=model_name,
            base_url=ollama_base_url,
        )

    if openrouter_api_key is None or not openrouter_api_key.strip():
        raise LLMConfigurationError("OpenRouter API key is required for the OpenRouter provider.")

    return OpenRouterProvider(
        model_name=model_name,
        api_key=openrouter_api_key,
        base_url=openrouter_base_url,
        site_url=openrouter_site_url,
        app_name=openrouter_app_name,
    )
