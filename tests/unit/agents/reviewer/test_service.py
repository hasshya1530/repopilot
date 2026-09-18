from uuid import UUID

import pytest

from agents.implementer.context.models import ImplementationContext
from agents.implementer.models import ImplementationResult
from agents.reviewer.models import (
    ReviewCategory,
    ReviewDecision,
    ReviewFinding,
    ReviewResult,
    ReviewSeverity,
)
from agents.reviewer.service import ReviewerService


class FakeReviewer:
    """Deterministic reviewer for service tests."""

    def __init__(self, result: ReviewResult) -> None:
        self.result = result
        self.calls = 0

    async def review(
        self,
        *,
        context: ImplementationContext,
        implementation: ImplementationResult,
    ) -> ReviewResult:
        self.calls += 1
        return self.result


def make_context() -> ImplementationContext:
    return ImplementationContext(
        repository_id=UUID("00000000-0000-0000-0000-000000000001"),
        task_description="Fix the broken addition function.",
        files=(),
        symbols=(),
        dependencies=(),
    )


def make_implementation() -> ImplementationResult:
    return ImplementationResult(
        summary="Fix addition logic.",
        changes=(),
    )


def make_finding(
    *,
    severity: ReviewSeverity = ReviewSeverity.MEDIUM,
) -> ReviewFinding:
    return ReviewFinding(
        severity=severity,
        category=ReviewCategory.CORRECTNESS,
        file_path="app.py",
        line=2,
        title="Example finding",
        description="Example review finding.",
        recommendation="Fix the identified issue.",
    )


@pytest.mark.asyncio
async def test_service_preserves_approved_review_without_blocking_findings() -> None:
    result = ReviewResult(
        decision=ReviewDecision.APPROVE,
        summary="Implementation looks correct.",
        findings=(),
    )
    reviewer = FakeReviewer(result)
    service = ReviewerService(reviewer)

    reviewed = await service.review(
        context=make_context(),
        implementation=make_implementation(),
    )

    assert reviewed == result
    assert reviewed.approved is True
    assert reviewer.calls == 1


@pytest.mark.asyncio
async def test_service_preserves_request_changes_review() -> None:
    result = ReviewResult(
        decision=ReviewDecision.REQUEST_CHANGES,
        summary="Changes are required.",
        findings=(make_finding(),),
    )
    reviewer = FakeReviewer(result)
    service = ReviewerService(reviewer)

    reviewed = await service.review(
        context=make_context(),
        implementation=make_implementation(),
    )

    assert reviewed == result
    assert reviewed.decision == ReviewDecision.REQUEST_CHANGES
    assert reviewer.calls == 1


@pytest.mark.asyncio
async def test_service_allows_medium_finding_with_approve_decision() -> None:
    result = ReviewResult(
        decision=ReviewDecision.APPROVE,
        summary="Implementation is acceptable with a minor observation.",
        findings=(make_finding(severity=ReviewSeverity.MEDIUM),),
    )
    reviewer = FakeReviewer(result)
    service = ReviewerService(reviewer)

    reviewed = await service.review(
        context=make_context(),
        implementation=make_implementation(),
    )

    assert reviewed.decision == ReviewDecision.APPROVE
    assert reviewed.findings == result.findings


@pytest.mark.asyncio
async def test_service_forces_request_changes_for_high_finding() -> None:
    result = ReviewResult(
        decision=ReviewDecision.APPROVE,
        summary="The implementation appears correct.",
        findings=(make_finding(severity=ReviewSeverity.HIGH),),
    )
    reviewer = FakeReviewer(result)
    service = ReviewerService(reviewer)

    reviewed = await service.review(
        context=make_context(),
        implementation=make_implementation(),
    )

    assert reviewed.decision == ReviewDecision.REQUEST_CHANGES
    assert reviewed.approved is False
    assert reviewed.summary == result.summary
    assert reviewed.findings == result.findings


@pytest.mark.asyncio
async def test_service_forces_request_changes_for_critical_finding() -> None:
    result = ReviewResult(
        decision=ReviewDecision.APPROVE,
        summary="The implementation appears correct.",
        findings=(make_finding(severity=ReviewSeverity.CRITICAL),),
    )
    reviewer = FakeReviewer(result)
    service = ReviewerService(reviewer)

    reviewed = await service.review(
        context=make_context(),
        implementation=make_implementation(),
    )

    assert reviewed.decision == ReviewDecision.REQUEST_CHANGES
    assert reviewed.approved is False
    assert reviewed.findings == result.findings


@pytest.mark.asyncio
async def test_service_passes_context_and_implementation_to_reviewer() -> None:
    result = ReviewResult(
        decision=ReviewDecision.APPROVE,
        summary="Looks good.",
        findings=(),
    )
    reviewer = FakeReviewer(result)
    service = ReviewerService(reviewer)

    context = make_context()
    implementation = make_implementation()

    reviewed = await service.review(
        context=context,
        implementation=implementation,
    )

    assert reviewed == result
    assert reviewer.calls == 1
