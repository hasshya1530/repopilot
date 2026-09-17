import pytest

from agents.llm.models import LLMMessage, LLMRequest
from agents.llm.providers.ollama import OllamaProvider


@pytest.mark.integration
async def test_ollama_generation() -> None:
    provider = OllamaProvider(
        model_name="qwen2.5-coder:3b",
        base_url="http://localhost:11434",
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

    assert response.model == "qwen2.5-coder:3b"
    assert response.content.strip()
    assert response.prompt_tokens is not None
    assert response.completion_tokens is not None
