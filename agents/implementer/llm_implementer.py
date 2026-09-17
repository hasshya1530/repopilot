from agents.implementer.change_parser import parse_implementation_result
from agents.implementer.context.models import ImplementationContext
from agents.implementer.errors import ImplementationGenerationError
from agents.implementer.models import ImplementationResult
from agents.implementer.prompts import (
    build_implementation_prompt,
    get_system_prompt,
)
from agents.llm.models import LLMMessage, LLMRequest
from agents.llm.provider import LLMProvider
from agents.planner.plan_models import ImplementationPlan


class LLMImplementer:
    """Generate structured code changes from an implementation context."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def implement(
        self,
        context: ImplementationContext,
        plan: ImplementationPlan,
        *,
        max_tokens: int = 8192,
    ) -> ImplementationResult:
        request = LLMRequest(
            messages=(
                LLMMessage(
                    role="system",
                    content=get_system_prompt(),
                ),
                LLMMessage(
                    role="user",
                    content=build_implementation_prompt(
                        context=context,
                        plan=plan,
                    ),
                ),
            ),
            temperature=0.0,
            max_tokens=max_tokens,
        )

        try:
            response = await self._provider.generate(request)
        except Exception as exc:
            raise ImplementationGenerationError(
                f"LLM implementation generation failed: {exc}"
            ) from exc

        try:
            return parse_implementation_result(response.content)
        except Exception as exc:
            raise ImplementationGenerationError(
                f"LLM returned an invalid implementation result: {exc}"
            ) from exc
