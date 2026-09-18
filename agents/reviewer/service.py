from typing import Protocol

from agents.implementer.context.models import ImplementationContext
from agents.implementer.models import ImplementationResult
from agents.reviewer.llm_reviewer import LLMReviewer
from agents.reviewer.models import ReviewDecision, ReviewResult, ReviewSeverity


class ReviewerProtocol(Protocol):
    """Protocol for an object capable of generating code reviews."""

    async def review(
        self,
        *,
        context: ImplementationContext,
        implementation: ImplementationResult,
    ) -> ReviewResult:
        """Generate a structured code review."""
        ...


class ReviewerService:
    """Coordinate code review and enforce reviewer safety policy."""

    def __init__(
        self,
        reviewer: ReviewerProtocol | LLMReviewer,
    ) -> None:
        self._reviewer = reviewer

    async def review(
        self,
        *,
        context: ImplementationContext,
        implementation: ImplementationResult,
    ) -> ReviewResult:
        """Review an implementation and enforce blocking-findings policy."""
        result = await self._reviewer.review(
            context=context,
            implementation=implementation,
        )

        return self._enforce_policy(result)

    @staticmethod
    def _enforce_policy(result: ReviewResult) -> ReviewResult:
        """Ensure blocking findings always produce request_changes."""
        has_blocking_finding = any(
            finding.severity
            in {ReviewSeverity.HIGH, ReviewSeverity.CRITICAL}
            for finding in result.findings
        )

        if not has_blocking_finding:
            return result

        if result.decision == ReviewDecision.REQUEST_CHANGES:
            return result

        return ReviewResult(
            decision=ReviewDecision.REQUEST_CHANGES,
            summary=result.summary,
            findings=result.findings,
        )
