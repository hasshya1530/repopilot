from __future__ import annotations

from agents.debugger.analyzer import FailureAnalysis
from agents.debugger.errors import RepairGenerationError
from agents.debugger.repair_models import RepairProposal
from agents.debugger.repair_prompts import build_repair_prompt
from agents.implementer.change_parser import parse_implementation_result
from agents.implementer.context.models import ImplementationContext
from agents.llm.models import LLMMessage, LLMRequest
from agents.llm.provider import LLMProvider


class RepairGenerator:
    """Generate a targeted code repair from a test failure."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def generate(
        self,
        analysis: FailureAnalysis,
        context: ImplementationContext,
        *,
        max_tokens: int = 8192,
    ) -> RepairProposal:
        if analysis.failure_type == "none":
            raise RepairGenerationError(
                "Cannot generate a repair for a successful test run."
            )

        request = LLMRequest(
            messages=(
                LLMMessage(
                    role="system",
                    content=(
                        "You are a software debugging agent. "
                        "Diagnose test failures and produce the smallest "
                        "safe code change that fixes the underlying issue."
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=build_repair_prompt(
                        analysis=analysis,
                        context=context,
                    ),
                ),
            ),
            temperature=0.0,
            max_tokens=max_tokens,
        )

        try:
            response = await self._provider.generate(request)
        except Exception as exc:
            raise RepairGenerationError(
                f"LLM repair generation failed: {exc}"
            ) from exc

        try:
            implementation = parse_implementation_result(
                response.content,
            )
        except Exception as exc:
            raise RepairGenerationError(
                f"LLM returned an invalid repair result: {exc}"
            ) from exc

        return RepairProposal(
            diagnosis=implementation.summary,
            changes=implementation.changes,
        )
