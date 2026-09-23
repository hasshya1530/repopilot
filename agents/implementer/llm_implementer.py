from agents.implementer.change_parser import parse_implementation_result
from agents.implementer.context.models import ImplementationContext
from agents.implementer.errors import ImplementationGenerationError
from agents.implementer.models import ImplementationResult
from agents.implementer.prompts import (
    build_implementation_prompt,
    get_system_prompt,
)
from agents.implementer.validator import ImplementationValidator
from agents.llm.models import LLMMessage, LLMRequest
from agents.llm.provider import LLMProvider
from agents.planner.plan_models import ImplementationPlan


class LLMImplementer:
    """Generate and validate structured code changes from an implementation plan."""

    DEFAULT_CONTEXT_WINDOW = 16_384

    def __init__(
        self,
        provider: LLMProvider,
        validator: ImplementationValidator | None = None,
    ) -> None:
        self._provider = provider
        self._validator = validator or ImplementationValidator()

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
            context_window=self.DEFAULT_CONTEXT_WINDOW,
            response_format="json",
            reasoning_enabled=False,
        )

        try:
            response = await self._provider.generate(request)
        except Exception as exc:
            raise ImplementationGenerationError(
                f"LLM implementation generation failed: {exc}"
            ) from exc

        try:
            implementation = parse_implementation_result(response.content)
        except Exception as exc:
            raise ImplementationGenerationError(
                f"LLM returned an invalid implementation result: {exc}"
            ) from exc

        validation = self._validator.validate(
            plan=plan,
            implementation=implementation,
        )

        if not validation.valid:
            errors = "; ".join(validation.errors)

            raise ImplementationGenerationError(
                "LLM implementation violated the approved implementation plan: "
                f"{errors}"
            )

        return implementation
