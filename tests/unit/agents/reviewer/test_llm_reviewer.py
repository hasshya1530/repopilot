from uuid import UUID

import pytest

from agents.implementer.context.models import (
    ImplementationContext,
)
from agents.implementer.models import (
    ChangeOperation,
    CodeChange,
    ImplementationResult,
)
from agents.llm.models import LLMRequest, LLMResponse
from agents.llm.provider import LLMProvider
from agents.reviewer.errors import ReviewGenerationError
from agents.reviewer.llm_reviewer import LLMReviewer
from agents.reviewer.models import (
    ReviewCategory,
    ReviewDecision,
    ReviewSeverity,
)


class FakeLLMProvider(LLMProvider):
    """Deterministic provider for reviewer unit tests."""

    @property
    def model_name(self) -> str:
        return "fake-review-model"

    def __init__(
        self,
        *,
        content: str = "",
        error: Exception | None = None,
    ) -> None:
        self.content = content
        self.error = error
        self.requests: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)

        if self.error is not None:
            raise self.error

        return LLMResponse(
            content=self.content,
            model=self.model_name,
        )


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
        changes=(
            CodeChange(
                file_path="app.py",
                operation=ChangeOperation.MODIFY,
                content="def add(a, b):\n    return a + b\n",
                reason="Use addition instead of subtraction.",
            ),
        ),
    )


APPROVED_RESPONSE = """\
{
  "decision": "approve",
  "summary": "The implementation correctly fixes the addition logic.",
  "findings": []
}
"""


REQUEST_CHANGES_RESPONSE = """\
{
  "decision": "request_changes",
  "summary": "The implementation contains a correctness issue.",
  "findings": [
    {
      "severity": "high",
      "category": "correctness",
      "file_path": "app.py",
      "line": 2,
      "title": "Incorrect calculation",
      "description": "The function still produces an incorrect result.",
      "recommendation": "Correct the arithmetic operation."
    }
  ]
}
"""


async def test_reviewer_generates_and_parses_approved_review_async() -> None:
    provider = FakeLLMProvider(content=APPROVED_RESPONSE)
    reviewer = LLMReviewer(provider)

    result = await reviewer.review(
        context=make_context(),
        implementation=make_implementation(),
    )

    assert result.decision == ReviewDecision.APPROVE
    assert result.approved is True
    assert result.summary == "The implementation correctly fixes the addition logic."
    assert result.findings == ()

    assert len(provider.requests) == 1
    request = provider.requests[0]

    assert request.temperature == 0.0
    assert request.max_tokens == 4096
    assert len(request.messages) == 2
    assert request.messages[0].role == "system"
    assert request.messages[1].role == "user"

    assert "Fix the broken addition function." in request.messages[1].content
    assert "app.py" in request.messages[1].content


async def test_reviewer_generates_and_parses_request_changes() -> None:
    provider = FakeLLMProvider(content=REQUEST_CHANGES_RESPONSE)
    reviewer = LLMReviewer(provider)

    result = await reviewer.review(
        context=make_context(),
        implementation=make_implementation(),
    )

    assert result.decision == ReviewDecision.REQUEST_CHANGES
    assert result.approved is False
    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.severity == ReviewSeverity.HIGH
    assert finding.category == ReviewCategory.CORRECTNESS
    assert finding.file_path == "app.py"
    assert finding.line == 2
    assert finding.title == "Incorrect calculation"


async def test_reviewer_wraps_provider_errors() -> None:
    provider = FakeLLMProvider(
        error=RuntimeError("provider unavailable"),
    )
    reviewer = LLMReviewer(provider)

    with pytest.raises(
        ReviewGenerationError,
        match="Failed to generate code review",
    ):
        await reviewer.review(
            context=make_context(),
            implementation=make_implementation(),
        )


async def test_reviewer_wraps_parse_errors() -> None:
    provider = FakeLLMProvider(
        content="not valid JSON",
    )
    reviewer = LLMReviewer(provider)

    with pytest.raises(
        ReviewGenerationError,
        match="Failed to parse generated code review",
    ):
        await reviewer.review(
            context=make_context(),
            implementation=make_implementation(),
        )


def test_reviewer_rejects_invalid_temperature() -> None:
    provider = FakeLLMProvider(content=APPROVED_RESPONSE)

    with pytest.raises(
        ValueError,
        match="temperature must be between",
    ):
        LLMReviewer(provider, temperature=-0.1)

    with pytest.raises(
        ValueError,
        match="temperature must be between",
    ):
        LLMReviewer(provider, temperature=2.1)


def test_reviewer_rejects_invalid_max_tokens() -> None:
    provider = FakeLLMProvider(content=APPROVED_RESPONSE)

    with pytest.raises(
        ValueError,
        match="max_tokens must be at least 1",
    ):
        LLMReviewer(provider, max_tokens=0)
