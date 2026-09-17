import httpx
import pytest

from agents.llm.errors import LLMConfigurationError, LLMRequestError
from agents.llm.models import LLMMessage, LLMRequest
from agents.llm.providers.openrouter import OpenRouterProvider


def test_openrouter_requires_model() -> None:
    with pytest.raises(LLMConfigurationError):
        OpenRouterProvider(
            model_name="",
            api_key="test-key",
        )


def test_openrouter_requires_api_key() -> None:
    with pytest.raises(LLMConfigurationError):
        OpenRouterProvider(
            model_name="nvidia/nemotron-3-ultra-550b-a55b:free",
            api_key="",
        )


def test_openrouter_exposes_model_name() -> None:
    provider = OpenRouterProvider(
        model_name="nvidia/nemotron-3-ultra-550b-a55b:free",
        api_key="test-key",
    )

    assert provider.model_name == "nvidia/nemotron-3-ultra-550b-a55b:free"


async def test_openrouter_rejects_empty_messages() -> None:
    provider = OpenRouterProvider(
        model_name="nvidia/nemotron-3-ultra-550b-a55b:free",
        api_key="test-key",
    )

    with pytest.raises(LLMRequestError):
        await provider.generate(LLMRequest(messages=()))


async def test_openrouter_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_post(
        self: httpx.AsyncClient,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs["json"]

        return httpx.Response(
            200,
            json={
                "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "RepoPilot works",
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    provider = OpenRouterProvider(
        model_name="nvidia/nemotron-3-ultra-550b-a55b:free",
        api_key="test-key",
    )

    response = await provider.generate(
        LLMRequest(
            messages=(
                LLMMessage(
                    role="user",
                    content="Say hello",
                ),
            ),
        )
    )

    assert response.content == "RepoPilot works"
    assert response.model == "nvidia/nemotron-3-ultra-550b-a55b:free"
    assert response.total_tokens == 15
    assert captured["url"] == "/chat/completions"
