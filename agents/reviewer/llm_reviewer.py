from agents.implementer.context.models import ImplementationContext
from agents.implementer.models import ImplementationResult
from agents.llm.models import LLMMessage, LLMRequest
from agents.llm.provider import LLMProvider
from agents.reviewer.errors import ReviewGenerationError
from agents.reviewer.models import ReviewResult
from agents.reviewer.parser import parse_review_result
from agents.reviewer.prompts import SYSTEM_REVIEW_PROMPT, build_review_prompt


class LLMReviewer:
    """Generate structured code reviews using an LLM provider."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> None:
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0.")

        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1.")

        self._provider = provider
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def review(
        self,
        *,
        context: ImplementationContext,
        implementation: ImplementationResult,
    ) -> ReviewResult:
        """Generate and parse a structured review for an implementation."""
        prompt = build_review_prompt(
            context=context,
            implementation=implementation,
        )

        request = LLMRequest(
            messages=(
                LLMMessage(
                    role="system",
                    content=SYSTEM_REVIEW_PROMPT,
                ),
                LLMMessage(
                    role="user",
                    content=prompt,
                ),
            ),
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )

        try:
            response = await self._provider.generate(request)
        except Exception as exc:
            raise ReviewGenerationError(
                f"Failed to generate code review: {exc}"
            ) from exc

        try:
            return parse_review_result(response.content)
        except Exception as exc:
            raise ReviewGenerationError(
                f"Failed to parse generated code review: {exc}"
            ) from exc
