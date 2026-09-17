from agents.llm.models import LLMMessage, LLMRequest, LLMResponse
from agents.llm.provider import LLMProvider


class FakeLLMProvider(LLMProvider):
    @property
    def model_name(self) -> str:
        return "fake-model"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content=request.messages[-1].content,
            model=self.model_name,
        )


async def test_provider_contract() -> None:
    provider = FakeLLMProvider()

    request = LLMRequest(messages=(LLMMessage(role="user", content="hello"),))

    response = await provider.generate(request)

    assert provider.model_name == "fake-model"
    assert response.content == "hello"
