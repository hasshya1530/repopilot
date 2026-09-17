import pytest

from agents.llm.factory import create_llm_provider
from agents.llm.models import LLMMessage, LLMRequest
from apps.api.app.core.config import get_settings


@pytest.mark.integration
@pytest.mark.openrouter
async def test_openrouter_generation() -> None:
    settings = get_settings()

    if settings.model_provider != "openrouter":
        pytest.skip("OpenRouter is not the configured LLM provider.")

    if not settings.openrouter_api_key:
        pytest.skip("OPENROUTER_API_KEY is not configured.")

    provider = create_llm_provider(
        provider=settings.model_provider,
        model_name=settings.model_name,
        ollama_base_url=settings.ollama_base_url,
        openrouter_base_url=settings.openrouter_base_url,
        openrouter_api_key=settings.openrouter_api_key,
        openrouter_site_url=settings.openrouter_site_url,
        openrouter_app_name=settings.openrouter_app_name,
    )

    response = await provider.generate(
        LLMRequest(
            messages=(
                LLMMessage(
                    role="user",
                    content="Reply with exactly: RepoPilot works",
                ),
            ),
            temperature=0.0,
            max_tokens=32,
        )
    )

    assert response.content.strip()
    assert response.model
