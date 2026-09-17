from agents.llm.models import LLMMessage, LLMRequest, LLMResponse


def test_llm_message_is_immutable() -> None:
    message = LLMMessage(role="user", content="Hello")

    assert message.role == "user"
    assert message.content == "Hello"


def test_llm_request_defaults() -> None:
    request = LLMRequest(messages=(LLMMessage(role="user", content="Hello"),))

    assert request.temperature == 0.0
    assert request.max_tokens is None


def test_llm_response_stores_usage() -> None:
    response = LLMResponse(
        content="Hello",
        model="test-model",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )

    assert response.content == "Hello"
    assert response.model == "test-model"
    assert response.total_tokens == 15
